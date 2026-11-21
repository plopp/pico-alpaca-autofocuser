"""Cheap guard: pico/ runs on MicroPython, which lacks some CPython str methods
(str.ljust once broke Save on the device)."""
import pathlib
import re

MISSING = ('ljust', 'rjust', 'removeprefix', 'removesuffix', 'casefold', 'zfill',
           'expandtabs', 'swapcase', 'title')
PICO = pathlib.Path(__file__).resolve().parent.parent / 'pico'


def test_no_cpython_only_str_methods():
    offenders = []
    for path in sorted(PICO.glob('*.py')):
        if path.name == 'microdot.py':
            continue
        for n, line in enumerate(path.read_text().splitlines(), 1):
            for name in MISSING:
                if re.search(r'\.{}\('.format(name), line):
                    offenders.append('{}:{} {}'.format(path.name, n, name))
    assert offenders == []
