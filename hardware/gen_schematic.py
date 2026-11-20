"""Generate hardware/kicad/focuser.kicad_sch from design.py.

Every part is placed on a grid and each connected pin gets a net label, so the schematic
is a readable, ERC-checkable record of design.NETS (labels instead of wires).
Run with system Python: python3 hardware/gen_schematic.py
"""
import re
import uuid

import design
import kicad_env

NS = uuid.UUID('6f1c2a5e-4d7b-4c38-9a61-2f0e8b7d3c11')   # stable UUIDs => stable diffs
GRID = 2.54
PWR_FLAG_NETS = ('+12V', 'GND')      # nets whose only sources are outside the schematic


def uid(*parts):
    return str(uuid.uuid5(NS, '/'.join(parts)))


def snap(v):
    return round(round(v / GRID) * GRID, 2)


def _block(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError('unbalanced')


def load_symbol(lib_id):
    """Return (lib_symbols text, {pin_number: (x, y)}) for 'Lib:Name'."""
    lib, name = lib_id.split(':')
    text = (kicad_env.SYMBOLS / (lib + '.kicad_symdir') / (name + '.kicad_sym')).read_text()
    start = text.index('(symbol "{}"'.format(name))
    body = _block(text, start)
    body = body.replace('(symbol "{}"'.format(name), '(symbol "{}"'.format(lib_id), 1)
    pins = {}
    for m in re.finditer(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) [-\d.]+\).*?\(number "([^"]+)"',
                         body, re.S):
        pins[m.group(3)] = (float(m.group(1)), float(m.group(2)))
    return body, pins


def pin_names(lib_id):
    """{pin_number: pin_name} for a library symbol."""
    lib, name = lib_id.split(':')
    text = (kicad_env.SYMBOLS / (lib + '.kicad_symdir') / (name + '.kicad_sym')).read_text()
    return {m.group(2): m.group(1) for m in re.finditer(
        r'\(pin \w+ \w+.*?\(name "([^"]*)".*?\(number "([^"]+)"', text, re.S)}


def unconnected_net_name(ref, number, name):
    """The net name eeschema gives a no-connect pin (the board must use the same)."""
    if name and name != '~':
        return 'unconnected-({}-{}-Pad{})'.format(ref, name, number)
    return 'unconnected-({}-Pad{})'.format(ref, number)


def prop(name, value, x, y, hide=False):
    return ('(property "{}" "{}" (at {} {} 0) (effects (font (size 1.27 1.27)){}))'
            .format(name, value, x, y, ' (hide yes)' if hide else ''))


def symbol_instance(ref, lib_id, value, footprint, lcsc, x, y, pins, root, in_bom=True):
    fields = [prop('Reference', ref, x, snap(y - 6)),
              prop('Value', value, x, snap(y + 6)),
              prop('Footprint', footprint, x, y, hide=True),
              prop('Datasheet', '', x, y, hide=True),
              prop('Description', '', x, y, hide=True)]
    if lcsc:
        fields.append(prop('LCSC', lcsc, x, y, hide=True))
    pin_lines = ' '.join('(pin "{}" (uuid "{}"))'.format(n, uid(ref, 'pin', n)) for n in pins)
    return ('(symbol (lib_id "{lib}") (at {x} {y} 0) (unit 1) (exclude_from_sim no) '
            '(in_bom {bom}) (on_board yes) (dnp no) (uuid "{u}") {fields} {pins} '
            '(instances (project "{proj}" (path "/{root}" (reference "{ref}") (unit 1)))))'
            .format(lib=lib_id, x=x, y=y, bom='yes' if in_bom else 'no', u=uid(ref),
                    fields=' '.join(fields), pins=pin_lines, proj=kicad_env.PROJECT,
                    root=root, ref=ref))


def label(net, x, y, key):
    # Global labels give plain net names (GND, +12V) that match the board's nets
    return ('(global_label "{}" (shape passive) (at {} {} 0) '
            '(effects (font (size 1.27 1.27)) (justify left)) (uuid "{}"))'
            .format(net, x, y, uid('label', key)))


def no_connect(x, y, key):
    return '(no_connect (at {} {}) (uuid "{}"))'.format(x, y, uid('nc', key))


def build():
    root = uid('root')
    net_of = {member: net for net, members in design.NETS.items() for member in members}
    lib_bodies, items = {}, []

    placed = [(p.ref, p.symbol, p.value, p.footprint, p.lcsc if p.assembled else None,
               p.assembled) for p in design.PARTS.values()]
    placed += [('#FLG0{}'.format(i + 1), 'power:PWR_FLAG', 'PWR_FLAG', '', None, False)
               for i in range(len(PWR_FLAG_NETS))]

    x, y, row_h = 25.4, 30.48, 0.0
    for ref, lib_id, value, footprint, lcsc, in_bom in placed:
        if lib_id not in lib_bodies:
            lib_bodies[lib_id] = load_symbol(lib_id)
        body, pins = lib_bodies[lib_id]
        xs = [px for px, _ in pins.values()] or [0]
        ys = [py for _, py in pins.values()] or [0]
        width = max(xs) - min(xs) + 30
        height = max(ys) - min(ys) + 20
        if x + width > 400:
            x, y, row_h = 25.4, snap(y + row_h + 10), 0.0
        sx, sy = snap(x - min(xs) + 10), snap(y + max(ys) + 8)
        items.append(symbol_instance(ref, lib_id, value, footprint, lcsc, sx, sy, pins, root,
                                     in_bom=in_bom))
        for number, (px, py) in pins.items():
            cx, cy = round(sx + px, 2), round(sy - py, 2)
            if ref.startswith('#FLG'):
                net = PWR_FLAG_NETS[int(ref[4:]) - 1]
            else:
                net = net_of.get((ref, number))
            if net:
                items.append(label(net, cx, cy, ref + '.' + number))
            else:
                items.append(no_connect(cx, cy, ref + '.' + number))
        x += width
        row_h = max(row_h, height)

    sch = ('(kicad_sch (version 20250610) (generator "focuser_gen") (generator_version "10.0") '
           '(uuid "{root}") (paper "A3") '
           '(title_block (title "Pico Alpaca Focuser carrier") (rev "1.0")) '
           '(lib_symbols {libs}) {items} '
           '(sheet_instances (path "/" (page "1"))) (embedded_fonts no))'
           .format(root=root, libs=' '.join(b for b, _ in lib_bodies.values()),
                   items=' '.join(items)))
    kicad_env.KICAD_DIR.mkdir(parents=True, exist_ok=True)
    kicad_env.SCH.write_text(sch + '\n')
    kicad_env.write_project()
    return kicad_env.SCH


if __name__ == '__main__':
    print(build())
