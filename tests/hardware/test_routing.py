import json

import design


def test_drc_clean(kicad, board, tmp_path):
    report = tmp_path / 'drc.json'
    kicad.cli('pcb', 'drc', '--format', 'json', '--schematic-parity', '--severity-error',
              '-o', report, kicad.PCB)
    data = json.loads(report.read_text())
    assert data['violations'] == [], data['violations'][:5]
    assert data['unconnected_items'] == [], data['unconnected_items'][:5]
    assert data['schematic_parity'] == [], data['schematic_parity'][:5]


def test_power_track_widths(board):
    power = [t for t in board['tracks'] if t['net'] in design.POWER_NETS]
    assert power, 'no power tracks routed'
    thin = [t for t in power if t['width'] < 1.0 - 1e-6]
    assert thin == [], thin[:5]


def test_schematic_parity_clean_all_severities(kicad, board, tmp_path):
    report = tmp_path / 'parity.json'
    kicad.cli('pcb', 'drc', '--format', 'json', '--schematic-parity', '-o', report, kicad.PCB)
    parity = json.loads(report.read_text())['schematic_parity']
    assert parity == [], [(p['type'], p['description']) for p in parity[:5]]
