"""Generate hardware/kicad/focuser.kicad_sch from design.py.

The layout is drawn by hand below (one function per block), but every connection still
comes from design.NETS: build() checks that each net-connected pin was drawn and that the
rest got a no-connect flag, and tests/hardware compares the exported netlist with NETS.
Signal nets use global labels, so their names match the board's nets exactly.
Run with system Python: python3 hardware/gen_schematic.py
"""
import math
import re
import uuid
from collections import Counter

import design
import kicad_env

NS = uuid.UUID('6f1c2a5e-4d7b-4c38-9a61-2f0e8b7d3c11')   # stable UUIDs => stable diffs
G = 2.54
SUPPLY_UP = ('+12V', '+5V', '+3V3')      # drawn as arrow-up power symbols
SUPPLIES = SUPPLY_UP + ('GND',)
FONT = 1.27

# Pico 2 W pin functions, printed next to the socket pins
PICO_PINS = {
    1: 'GP0', 2: 'GP1', 3: 'GND', 4: 'GP2', 5: 'GP3', 6: 'GP4', 7: 'GP5', 8: 'GND', 9: 'GP6',
    10: 'GP7', 11: 'GP8', 12: 'GP9', 13: 'GND', 14: 'GP10', 15: 'GP11', 16: 'GP12', 17: 'GP13',
    18: 'GND', 19: 'GP14', 20: 'GP15', 21: 'GP16', 22: 'GP17', 23: 'GND', 24: 'GP18',
    25: 'GP19', 26: 'GP20', 27: 'GP21', 28: 'GND', 29: 'GP22', 30: 'RUN', 31: 'GP26',
    32: 'GP27', 33: 'GND', 34: 'GP28', 35: 'ADC_VREF', 36: '3V3(OUT)', 37: '3V3_EN', 38: 'GND',
    39: 'VSYS', 40: 'VBUS'}

# Direction vectors on the sheet (y grows downwards)
LEFT, RIGHT, UP, DOWN = (-1, 0), (1, 0), (0, -1), (0, 1)


def uid(*parts):
    return str(uuid.uuid5(NS, '/'.join(parts)))


def r2(v):
    return round(v + 0.0, 2)


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
    """Return (lib_symbols text, {pin_number: (x, y, rotation)}) for 'Lib:Name'.

    x, y are library coordinates (y up); rotation points from the pin's end to the body."""
    lib, name = lib_id.split(':')
    text = (kicad_env.SYMBOLS / (lib + '.kicad_symdir') / (name + '.kicad_sym')).read_text()
    start = text.index('(symbol "{}"'.format(name))
    body = _block(text, start)
    body = body.replace('(symbol "{}"'.format(name), '(symbol "{}"'.format(lib_id), 1)
    pins = {}
    for m in re.finditer(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\).*?\(number "([^"]+)"',
                         body, re.S):
        pins[m.group(4)] = (float(m.group(1)), float(m.group(2)), int(float(m.group(3))))
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


def _rotate(x, y, rot):
    """Rotate a sheet vector the way KiCad rotates a symbol by `rot` degrees."""
    c, s = round(math.cos(math.radians(rot))), round(math.sin(math.radians(rot)))
    return x * c + y * s, -x * s + y * c


def _effects(size=FONT, justify=None, hide=False, bold=False):
    font = '(font (size {0} {0}){1})'.format(size, ' (bold yes)' if bold else '')
    return '(effects {}{}{})'.format(font, ' (justify {})'.format(justify) if justify else '',
                                      ' (hide yes)' if hide else '')


def prop(name, value, x, y, angle=0, hide=False, justify=None):
    return '(property "{}" "{}" (at {} {} {}) {})'.format(
        name, value, r2(x), r2(y), angle, _effects(justify=justify, hide=hide))


class Sheet:
    def __init__(self):
        self.root = uid('root')
        self.libs = {}
        self.items = []
        self.ends = Counter()        # wire ends per point, for junction dots
        self.taps = set()            # pins and markers sitting on a point
        self.drawn = set()           # (ref, pin) that got a connection
        self.npwr = 0
        self.nflag = 0
        self.pins_of = {}
        self.net_of = {m: net for net, members in design.NETS.items() for m in members}

    # -- symbols ---------------------------------------------------------------------------
    def lib(self, lib_id):
        if lib_id not in self.libs:
            self.libs[lib_id] = load_symbol(lib_id)
        return self.libs[lib_id]

    def symbol(self, ref, lib_id, value, x, y, rot=0, footprint='', lcsc=None, in_bom=True,
               ref_at=None, val_at=None, show_ref=True):
        """Place a symbol; ref_at/val_at are (dx, dy[, justify]) from the symbol origin."""
        _, pins = self.lib(lib_id)
        # Field text turns with the symbol: give it the opposite angle so it stays horizontal
        fangle = (360 - rot) % 360 if rot in (90, 270) else 0

        def field(name, val, at, hide=False):
            at = at or (0, 0)
            just = at[2] if len(at) > 2 else None
            if rot == 180 and just:          # KiCad mirrors justification with the symbol
                just = {'left': 'right', 'right': 'left'}[just]
            return prop(name, val, x + at[0], y + at[1], fangle, hide=hide, justify=just)

        fields = [field('Reference', ref, ref_at, hide=not show_ref),
                  field('Value', value, val_at),
                  prop('Footprint', footprint, x, y, hide=True),
                  prop('Datasheet', '', x, y, hide=True),
                  prop('Description', '', x, y, hide=True)]
        if lcsc:
            fields.append(prop('LCSC', lcsc, x, y, hide=True))
        pin_lines = ' '.join('(pin "{}" (uuid "{}"))'.format(n, uid(ref, 'pin', n)) for n in pins)
        self.items.append(
            '(symbol (lib_id "{lib}") (at {x} {y} {rot}) (unit 1) (exclude_from_sim no) '
            '(in_bom {bom}) (on_board yes) (dnp no) (uuid "{u}") {fields} {pins} '
            '(instances (project "{proj}" (path "/{root}" (reference "{ref}") (unit 1)))))'
            .format(lib=lib_id, x=r2(x), y=r2(y), rot=rot, bom='yes' if in_bom else 'no',
                    u=uid(ref), fields=' '.join(fields), pins=pin_lines, proj=kicad_env.PROJECT,
                    root=self.root, ref=ref))
        placed = {}
        for number, (px, py, prot) in pins.items():
            dx, dy = _rotate(px, -py, rot)
            bx, by = _rotate(math.cos(math.radians(prot)), -math.sin(math.radians(prot)), rot)
            placed[number] = ((r2(x + dx), r2(y + dy)), (-round(bx), -round(by)))
        return placed

    def part(self, ref, x, y, rot=0, **kw):
        p = design.PARTS[ref]
        self.pins_of[ref] = self.symbol(ref, p.symbol, p.value, x, y, rot, p.footprint,
                                        p.lcsc if p.assembled else None, p.assembled, **kw)
        return self.pins_of[ref]

    def power(self, net, x, y, toward=None):
        """A power symbol whose pin is at (x, y). toward: UP or DOWN, where its body points
        (default: up for supplies, down for GND)."""
        natural = DOWN if net == 'GND' else UP
        toward = toward or natural
        self.npwr += 1
        self.symbol('#PWR{:02d}'.format(self.npwr), 'power:' + net, net, x, y,
                    0 if toward == natural else 180, in_bom=False, show_ref=False,
                    val_at=(0, toward[1] * 4.45))
        self.taps.add((r2(x), r2(y)))

    def flag(self, net, x, y):
        """PWR_FLAG for a net whose only source is off the board: power symbol at (x, y),
        flag 10.16 mm to its right."""
        self.power(net, x, y)
        self.wire((x, y), (x + 4 * G, y))
        self.nflag += 1
        self.symbol('#FLG{:02d}'.format(self.nflag), 'power:PWR_FLAG', 'PWR_FLAG', x + 4 * G, y,
                    in_bom=False, show_ref=False, val_at=(0, -4.45))
        self.taps.add((r2(x + 4 * G), r2(y)))

    # -- drawing ---------------------------------------------------------------------------
    def wire(self, *pts):
        for a, b in zip(pts, pts[1:]):
            a, b = (r2(a[0]), r2(a[1])), (r2(b[0]), r2(b[1]))
            self.items.append('(wire (pts (xy {} {}) (xy {} {})) (stroke (width 0) (type default)) '
                              '(uuid "{}"))'.format(a[0], a[1], b[0], b[1], uid('wire', str(a), str(b))))
            self.ends[a] += 1
            self.ends[b] += 1

    def label(self, net, x, y, toward):
        angle = {RIGHT: 0, UP: 90, LEFT: 180, DOWN: 270}[toward]
        just = 'right' if toward == LEFT else 'left'
        self.items.append('(global_label "{}" (shape passive) (at {} {} {}) {} (uuid "{}"))'
                          .format(net, r2(x), r2(y), angle, _effects(justify=just),
                                  uid('label', net, str(r2(x)), str(r2(y)))))
        self.taps.add((r2(x), r2(y)))

    def text(self, s, x, y, size=FONT, bold=False):
        self.items.append('(text "{}" (exclude_from_sim no) (at {} {} 0) {} (uuid "{}"))'
                          .format(s, r2(x), r2(y), _effects(size, 'left', bold=bold),
                                  uid('text', s, str(x), str(y))))

    def frame(self, title, x0, y0, x1, y1):
        self.items.append('(rectangle (start {} {}) (end {} {}) (stroke (width 0.15) (type dash)) '
                          '(fill (type none)) (uuid "{}"))'.format(x0, y0, x1, y1, uid('frame', title)))
        self.text(title, x0 + 2, y0 + 4, size=2, bold=True)

    def pin(self, ref, number):
        return self.pins_of[ref][number][0]

    def tap(self, ref, number):
        """Mark a pin as drawn by explicit wires; returns its point."""
        self.drawn.add((ref, number))
        self.taps.add(self.pin(ref, number))
        return self.pin(ref, number)

    def term(self, ref, number, route=(G,), label=False):
        """Connect a pin to its net: a short wire out of the pin, then a power symbol or a
        global label. `route` steps are lengths along the current direction, or
        (direction, length) to turn. label=True forces a label (dense connectors)."""
        (x, y), d = self.pins_of[ref][number]
        net = self.net_of[(ref, number)]
        self.drawn.add((ref, number))
        self.taps.add((x, y))
        pts = [(x, y)]
        for step in route:
            if isinstance(step, tuple):                 # explicit turn: (direction, length)
                d, length = step
            else:
                length = step
            x, y = r2(x + d[0] * length), r2(y + d[1] * length)
            pts.append((x, y))
        if len(pts) > 1:
            self.wire(*pts)
        if net in SUPPLIES and not label:
            natural = DOWN if net == 'GND' else UP
            self.power(net, x, y, toward=natural if d != (-natural[0], -natural[1]) else d)
        else:
            self.label(net, x, y, d)

    def no_connects(self):
        for ref, pins in self.pins_of.items():
            for number, ((x, y), _) in pins.items():
                if (ref, number) in self.net_of:
                    if (ref, number) not in self.drawn:
                        raise AssertionError('{}.{} ({}) not drawn'.format(
                            ref, number, self.net_of[(ref, number)]))
                    continue
                self.items.append('(no_connect (at {} {}) (uuid "{}"))'
                                  .format(x, y, uid('nc', ref + '.' + number)))

    def junctions(self):
        for p, n in sorted(self.ends.items()):
            if n + (1 if p in self.taps else 0) >= 3:
                self.items.append('(junction (at {} {}) (diameter 0) (color 0 0 0 0) (uuid "{}"))'
                                  .format(p[0], p[1], uid('junction', str(p))))


# -- the blocks ---------------------------------------------------------------------------------
def power_block(s):
    s.frame('12 V input, protection and 5 V supply', 20.32, 27.94, 205.74, 76.2)
    rail = 50.8
    s.part('J1', 27.94, 53.34, ref_at=(-5.08, -8.89, 'left'), val_at=(-5.08, -6.35, 'left'))
    s.part('F1', 55.88, rail, 90, ref_at=(0, 3.81), val_at=(0, 6.35))
    s.part('D1', 73.66, rail, 180, ref_at=(0, 3.81), val_at=(0, 6.35))
    j1p1, j1p3, j1p2 = s.tap('J1', '1'), s.tap('J1', '3'), s.tap('J1', '2')
    # J1 sleeve and switch pins to ground
    s.wire(j1p3, (j1p3[0] + G, j1p3[1]), (j1p3[0] + G, j1p2[1]))
    s.wire(j1p2, (j1p2[0] + G, j1p2[1]), (j1p2[0] + G, j1p2[1] + G))
    s.power('GND', j1p2[0] + G, j1p2[1] + G)
    s.flag('GND', 43.18, 68.58)
    # J1 -> fuse -> reverse-polarity diode
    tick = 43.18
    s.wire(j1p1, (tick, rail), s.tap('F1', '1'))
    s.wire((tick, rail), (tick, rail - 2 * G))
    s.label('VIN_RAW', tick, rail - 2 * G, RIGHT)
    tick = 63.5
    s.wire(s.tap('F1', '2'), (tick, rail), s.tap('D1', '2'))
    s.wire((tick, rail), (tick, rail - 2 * G))
    s.label('VIN_FUSED', tick, rail - 2 * G, RIGHT)
    # +12 V rail with its capacitors, the driver's VM and the 5 V regulator
    node = 83.82
    s.wire(s.tap('D1', '1'), (node, rail))
    s.power('+12V', node, rail)
    s.flag('+12V', 99.06, 38.1)
    x = node
    for ref, cx in (('C1', 93.98), ('C2', 109.22), ('C3', 124.46)):
        s.part(ref, cx, rail + 7.62, ref_at=(2.54, -1.27, 'left'), val_at=(2.54, 1.27, 'left'))
        s.wire((x, rail), (cx, rail))
        s.wire((cx, rail), s.tap(ref, '1'))
        s.power('GND', *s.tap(ref, '2'))
        x = cx
    s.part('U1', 147.32, rail, ref_at=(0, -7.62), val_at=(0, -5.08))
    s.wire((x, rail), s.tap('U1', '1'))
    s.power('GND', *s.tap('U1', '2'))
    # +5 V -> Schottky -> Pico VSYS
    out = s.tap('U1', '3')
    node = 160.02
    s.wire(out, (node, rail))
    s.power('+5V', node, rail)
    s.part('C4', 167.64, rail + 7.62, ref_at=(2.54, -1.27, 'left'), val_at=(2.54, 1.27, 'left'))
    s.wire((node, rail), (167.64, rail), s.tap('C4', '1'))
    s.power('GND', *s.tap('C4', '2'))
    s.part('D2', 182.88, rail, 180, ref_at=(0, -3.81), val_at=(0, -6.35))
    s.wire((167.64, rail), s.tap('D2', '2'))
    k = s.tap('D2', '1')
    s.wire(k, (k[0] + 2 * G, rail))
    s.label('VSYS', k[0] + 2 * G, rail, RIGHT)


def pico_block(s):
    s.frame('Raspberry Pi Pico 2 W (plug-in module, two 1x20 sockets)', 20.32, 86.36, 150.62, 172.72)
    s.text('Pico pin number and function shown next to each socket pin.', 25.4, 96.52)
    for ref, x, first in (('J4', 53.34, 1), ('J5', 119.38, 40)):
        s.part(ref, x, 127, ref_at=(-2.54, -25.4), val_at=(-2.54, 27.94))
        for n in range(1, 21):
            pico = n if first == 1 else 41 - n
            (px, py), _ = s.pins_of[ref][str(n)]
            s.text('{} {}'.format(pico, PICO_PINS[pico]), px + 7.62, py)
            if (ref, str(n)) in s.net_of:
                s.term(ref, str(n), label=True)


def driver_block(s):
    s.frame('TMC2209 stepper driver (BTT v1.3 plug-in module)', 160.02, 86.36, 300.99, 172.72)
    for ref, x, names in (('J6', 215.9, design.TMC_LOGIC), ('J7', 271.78, design.TMC_POWER)):
        s.part(ref, x, 116.84, ref_at=(-2.54, -10.16), val_at=(-2.54, 12.7))
        for name, n in names.items():
            (px, py), _ = s.pins_of[ref][str(n)]
            s.text(name.rstrip('12') if name.startswith('GND') else name, px + 7.62, py)
            if (ref, str(n)) in s.net_of:
                s.term(ref, str(n), label=True)
    # EN pull-up: driver stays off until the Pico drives EN low
    s.part('R1', 172.72, 116.84, 180, ref_at=(2.54, -1.27, 'left'), val_at=(2.54, 1.27, 'left'))
    s.term('R1', '2', route=())
    s.term('R1', '1', route=(G, (RIGHT, G)))
    # Microstep jumpers: open = 1/8 step
    for ref, y in (('JP1', 147.32), ('JP2', 160.02)):
        s.part(ref, 190.5, y, ref_at=(0, -3.81), val_at=(0, 3.81))
        s.term(ref, '1')
        s.term(ref, '2', route=(G,))
    s.text('MS1/MS2 jumpers open = 1/8 microstep', 172.72, 168.91)
    s.part('C5', 233.68, 152.4, ref_at=(2.54, -1.27, 'left'), val_at=(2.54, 1.27, 'left'))
    s.term('C5', '1', route=())
    s.term('C5', '2', route=())
    s.text('VIO decoupling', 228.6, 162.56)
    s.flag('+3V3', 250.19, 152.4)


def motor_block(s):
    s.frame('Motor (JST XH)', 311.15, 86.36, 400.05, 127)
    s.part('J2', 325.12, 106.68, ref_at=(0, -6.35), val_at=(0, 8.89))
    for n in '1234':
        s.term('J2', n)
    s.text('A1/A2 = one coil, B1/B2 = the other', 314.96, 121.92)


def temperature_block(s):
    s.frame('DS18B20 on a 3.5 mm jack', 311.15, 137.16, 400.05, 200.66)
    s.part('J3', 325.12, 162.56, ref_at=(0, -7.62), val_at=(0, 8.89))
    for n in ('S', 'R2', 'R1', 'T'):
        s.term('J3', n, label=True)
    for ref, x in (('R2', 360.68), ('R3', 383.54)):
        s.part(ref, x, 180.34, 180, ref_at=(2.54, -1.27, 'left'), val_at=(2.54, 1.27, 'left'))
        s.term(ref, '2', route=())
        s.term(ref, '1', route=(G, (LEFT, G)))
    s.text('Tip = data (4.7k pull-up), ring = 3.3 V via 100R, sleeve = GND', 314.96, 195.58)


def build(path=None, write_project=True):
    path = path or kicad_env.SCH
    s = Sheet()
    power_block(s)
    pico_block(s)
    driver_block(s)
    motor_block(s)
    temperature_block(s)
    s.no_connects()
    s.junctions()

    sch = ('(kicad_sch (version 20250610) (generator "focuser_gen") (generator_version "10.0") '
           '(uuid "{root}") (paper "A3") '
           '(title_block (title "Pico Alpaca Focuser carrier") (rev "1.0")) '
           '(lib_symbols {libs}) {items} '
           '(sheet_instances (path "/" (page "1"))) (embedded_fonts no))'
           .format(root=s.root, libs=' '.join(b for b, _ in s.libs.values()),
                   items=' '.join(s.items)))
    kicad_env.KICAD_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(sch + '\n')
    if write_project:
        kicad_env.write_project()
    return path


if __name__ == '__main__':
    print(build())
