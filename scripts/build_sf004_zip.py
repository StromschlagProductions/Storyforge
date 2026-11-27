"""Baut die kleine öffentliche Windows-Testdistribution aus einer festen Dateiliste."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'downloads' / 'STORYFORGE-0.1.0-alpha.2-Windows.zip'
PREFIX = 'STORYFORGE-0.1.0-alpha.2-Windows/'


def files():
    yield ROOT / 'pyproject.toml'
    yield ROOT / 'Start_Storyforge.bat'
    yield ROOT / 'WINDOWS_KURZANLEITUNG.txt'
    yield ROOT / 'UPDATE_VON_ALPHA1.txt'
    yield ROOT / 'SF-005_PILOT_KURZANLEITUNG.md'
    source = ROOT / 'src' / 'storyforge'
    for path in sorted(source.rglob('*')):
        if path.is_file() and path.suffix in {'.py', '.js', '.css', '.html', '.png'}:
            yield path
    cards = sorted((ROOT / 'library' / 'cards').glob('*.json'))
    if len(cards) != 59:
        raise ValueError(f'59 Wissenskarten erwartet, gefunden: {len(cards)}')
    yield from cards
    cases = sorted((ROOT / 'pilot' / 'cases').glob('T*.json'))
    if len(cases) != 6:
        raise ValueError(f'6 Pilotfälle erwartet, gefunden: {len(cases)}')
    yield from cases


def main():
    selected = list(files())
    if len({p.relative_to(ROOT) for p in selected}) != len(selected):
        raise ValueError('Doppelte Datei im Archiv')
    TARGET.parent.mkdir(exist_ok=True)
    with ZipFile(TARGET, 'w', ZIP_DEFLATED, compresslevel=9) as archive:
        for path in selected:
            info = ZipInfo(PREFIX + path.relative_to(ROOT).as_posix(), (2026, 11, 27, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=9)
    print(f'{TARGET.relative_to(ROOT)}: {len(selected)} Dateien, {TARGET.stat().st_size} Bytes')


if __name__ == '__main__':
    main()
