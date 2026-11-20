import csv
import zipfile

import pytest

import design


@pytest.fixture(scope='module')
def fab(kicad):
    return kicad.FAB_DIR          # the committed outputs


@pytest.fixture(scope='module')
def fresh_fab(kicad, tmp_path_factory):
    out = tmp_path_factory.mktemp('fab')
    kicad.kipython(kicad.HARDWARE / 'gen_fab.py', out, '--no-renders')
    return out


def _strip_timestamps(text):
    """Drop the lines that change on every export (creation dates, generator banners)."""
    volatile = ('CreationDate', 'Created by', 'DRILL file', 'TF.GenerationSoftware')
    return '\n'.join(l for l in text.splitlines() if not any(v in l for v in volatile))


def test_committed_fab_files_match_the_board(fab, fresh_fab):
    for name in ('focuser-bom-jlc.csv', 'focuser-cpl-jlc.csv'):
        assert (fab / name).read_text() == (fresh_fab / name).read_text(), name
    committed = zipfile.ZipFile(fab / 'focuser-gerbers.zip')
    fresh = zipfile.ZipFile(fresh_fab / 'focuser-gerbers.zip')
    assert sorted(committed.namelist()) == sorted(fresh.namelist())
    for name in committed.namelist():
        a = _strip_timestamps(committed.read(name).decode(errors='replace'))
        b = _strip_timestamps(fresh.read(name).decode(errors='replace'))
        assert a == b, name + ' is stale: run hardware/build.sh'


def test_gerber_zip_contents(fab):
    names = zipfile.ZipFile(fab / 'focuser-gerbers.zip').namelist()
    for layer in ('F_Cu', 'B_Cu', 'F_Mask', 'B_Mask', 'F_Silkscreen', 'B_Silkscreen',
                  'F_Paste', 'Edge_Cuts'):
        assert any(layer in n for n in names), layer
    assert any(n.endswith('.drl') for n in names)


def _rows(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def test_bom_has_part_number_for_every_assembled_part(fab):
    rows = _rows(fab / 'focuser-bom-jlc.csv')
    refs = {ref.strip() for row in rows for ref in row['Designator'].split(',')}
    assert refs == {p.ref for p in design.PARTS.values() if p.assembled}
    for row in rows:
        assert row['LCSC Part #'] or row['Manufacturer Part'], row
        assert design.CONFIRM not in row.values(), row
    j1 = next(r for r in rows if 'J1' in r['Designator'])
    assert j1['LCSC Part #'] == 'C720557'


def test_cpl_matches_board(fab):
    rows = _rows(fab / 'focuser-cpl-jlc.csv')
    assert {r['Designator'] for r in rows} == {p.ref for p in design.PARTS.values() if p.assembled}
    for r in rows:
        assert 0 <= float(r['Mid X']) <= 80, r
        assert 0 <= float(r['Mid Y']) <= 50, r
        assert r['Layer'] == 'Top', r
        assert r['Rotation'] != '', r


def test_cpl_y_axis_points_up(fab):
    """JLC wants y up from the bottom-left corner: the Pico (top of the board) has a large Y."""
    rows = {r['Designator']: r for r in _rows(fab / 'focuser-cpl-jlc.csv')}
    assert float(rows['J5']['Mid Y']) > float(rows['J1']['Mid Y'])


def test_schematic_pdf_and_renders(fab):
    for name in ('focuser-schematic.pdf', 'render-top.png', 'render-iso.png'):
        assert (fab / name).stat().st_size > 1000, name
