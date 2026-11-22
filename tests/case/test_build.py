"""case.build writes STLs in print orientation, a STEP assembly and two previews."""
import struct

import pytest

pytest.importorskip('build123d')

from case import params as p
from case.build import PRINTED, build


def stl_z_range(path):
    """(min z, max z) of a binary STL."""
    data = path.read_bytes()
    count = struct.unpack_from('<I', data, 80)[0]
    zs = []
    for i in range(count):
        values = struct.unpack_from('<12f', data, 84 + 50 * i)
        zs += values[5::3]          # z of the three vertices (after the normal)
    return min(zs), max(zs)


@pytest.fixture(scope='module')
def written(tmp_path_factory):
    out = tmp_path_factory.mktemp('case')
    return out, build(out)


def test_build_writes_all_files(written):
    out, paths = written
    names = sorted(path.name for path in paths)
    assert names == sorted([f'{name}.stl' for name in PRINTED]
                           + ['case.step', 'preview-iso.png', 'preview-rear.png'])
    for path in paths:
        assert path.parent == out and path.stat().st_size > 1024, path


@pytest.mark.parametrize('name', PRINTED)
def test_stl_lies_on_the_bed(written, name):
    out, _ = written
    z0, _ = stl_z_range(out / f'{name}.stl')
    assert abs(z0) < 1e-3


def test_print_orientations(written):
    out, _ = written
    assert stl_z_range(out / 'front_plate.stl')[1] == pytest.approx(5.0, abs=0.01)   # flat
    assert stl_z_range(out / 'key.stl')[1] == pytest.approx(3.0, abs=0.01)
    assert stl_z_range(out / 'lid.stl')[1] == pytest.approx(p.LID_TOP_Z - p.BOARD_STOP_Z, abs=0.01)
