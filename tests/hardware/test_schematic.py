import json
import re
import subprocess
import sys

import pytest

import design


@pytest.fixture(scope='module')
def schematic(kicad, tmp_path_factory):
    subprocess.run([sys.executable, str(kicad.HARDWARE / 'gen_schematic.py')], check=True)
    return kicad.SCH


def test_erc_clean(kicad, schematic, tmp_path):
    report = tmp_path / 'erc.json'
    kicad.cli('sch', 'erc', '--format', 'json', '--severity-error', '-o', report, schematic)
    data = json.loads(report.read_text())
    errors = [v for sheet in data['sheets'] for v in sheet['violations']]
    assert errors == [], errors[:5]


def _netlist_nets(text):
    nets = {}
    for m in re.finditer(r'\(net \(code "?\d+"?\) \(name "([^"]*)"\)(.*?)\)\s*(?=\(net |\)\s*\)\s*$)',
                         text, re.S):
        name = m.group(1).lstrip('/')
        nodes = {(ref, pin) for ref, pin in
                 re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2))
                 if not ref.startswith('#')}          # #FLG power flags aren't parts
        nets[name] = nodes
    return nets


def test_netlist_matches_design(kicad, schematic, tmp_path):
    out = tmp_path / 'focuser.net'
    kicad.cli('sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', out, schematic)
    text = re.sub(r'\s+', ' ', out.read_text())
    nets = _netlist_nets(text)
    for name, members in design.NETS.items():
        assert name in nets, name
        assert nets[name] == set(members), name
    # every other net is an unconnected single pin
    for name, nodes in nets.items():
        if name not in design.NETS:
            assert len(nodes) <= 1, (name, nodes)
