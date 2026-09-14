import re
import unicodedata

_LATIN_TOKEN = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_CJK_SEQUENCE = re.compile(r"[\u3400-\u9fff]+")


def normalize_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).lower().split())


def lexical_tokens(text: str) -> list[str]:
    normalized = normalize_text(text)
    tokens = _LATIN_TOKEN.findall(normalized)
    for sequence in _CJK_SEQUENCE.findall(normalized):
        if len(sequence) == 1:
            tokens.append(sequence)
        else:
            tokens.extend(sequence[index : index + 2] for index in range(len(sequence) - 1))
            tokens.extend(sequence[index : index + 3] for index in range(len(sequence) - 2))
    return [token for token in tokens if token]


def to_fts_text(text: str) -> str:
    return " ".join(dict.fromkeys(lexical_tokens(text)))
