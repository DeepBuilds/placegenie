"""Guards against invisible control characters sneaking into source files.

A stray backspace (\x08) where a regex needed `\b` once silently broke a pattern; this test makes
that kind of mistake fail loudly.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"\n", "\r", "\t"}


def test_python_sources_contain_no_control_characters():
    offenders = []
    for path in [*(ROOT / "app").rglob("*.py"), *(ROOT / "tests").rglob("*.py")]:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(keepends=True), start=1):
            if any(ord(ch) < 32 and ch not in ALLOWED for ch in line):
                offenders.append(f"{path.relative_to(ROOT)}:{number}")
    assert offenders == []
