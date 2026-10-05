"""Stage 2 - text cleaning.

Raw PDF text is messy: ligatures, odd bullet characters, hyphens that split words, runs of
spaces. Cleaning makes the later stages (which use simple patterns) far more reliable.
Line breaks are kept because section headings and list items depend on them.
"""
import re
import unicodedata

BULLET_CHARS = "•●▪■◦○◆►▶➢✓✔–·*"
_BULLET_RE = re.compile(rf"^\s*[{re.escape(BULLET_CHARS)}-]\s*")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPACED_LETTERS_RE = re.compile(r"^(?:[A-Za-z] ){3,}[A-Za-z]$")  # "E D U C A T I O N"


def clean_text(raw: str) -> str:
    text = unicodedata.normalize("NFKC", raw)  # also turns ligatures such as "ﬁ" into "fi"
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")  # dashes
    text = text.replace(" ", " ").replace("\t", " ")
    text = _CONTROL_RE.sub("", text)

    lines = []
    for line in text.splitlines():
        line = re.sub(r"[ ]{2,}", " ", line).strip()
        if _SPACED_LETTERS_RE.match(line):  # letter-spaced headings
            line = line.replace(" ", "")
        bullet = _BULLET_RE.match(line)
        if bullet and line[bullet.end():].strip():
            line = "- " + line[bullet.end():].strip()  # one consistent bullet marker
        lines.append(line)

    # Drop repeated blank lines and surrounding blanks.
    cleaned, blank = [], False
    for line in lines:
        if not line:
            if not blank and cleaned:
                cleaned.append("")
            blank = True
        else:
            cleaned.append(line)
            blank = False
    return "\n".join(cleaned).strip()


def is_bullet(line: str) -> bool:
    return line.startswith("- ")


def strip_bullet(line: str) -> str:
    return line[2:].strip() if is_bullet(line) else line.strip()


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9+#.'/-]*", text))
