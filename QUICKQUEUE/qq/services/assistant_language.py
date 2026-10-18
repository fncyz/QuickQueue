from dataclasses import dataclass
from difflib import SequenceMatcher
import re


LANGUAGE_NAMES = {
    "en": "English",
    "fil": "Filipino",
    "ceb": "Cebuano",
    "fil-en": "Filipino-English (Taglish)",
    "ceb-en": "Cebuano-English (Bisaya-English)",
}

CEBUANO = {
    "unsa", "unsaon", "pila", "bayad", "akong", "akoa", "asa", "kanus", "makakuha",
    "makuha", "kinahanglan", "mga", "naa", "wala", "ug", "kay", "pud", "pwede", "palihog", "hulat",
    "linya", "numero", "serbisyo", "dokumento", "karon", "sunod", "cancelon", "kanselahon", "ngano", "tabang",
}
FILIPINO = {
    "paano", "ano", "magkano", "bayad", "aking", "akin", "ko", "saan", "kailan", "makukuha",
    "kailangan", "mga", "may", "wala", "at", "ay", "rin", "din", "pwede", "paki", "hintay",
    "pila", "numero", "serbisyo", "dokumento", "ngayon", "susunod", "kanselahin", "bakit", "ganito", "tulong",
}
ENGLISH = {
    "what", "how", "much", "when", "where", "my", "the", "is", "are", "can", "please", "available",
    "requirements", "fee", "status", "appointment", "queue", "document", "service", "event", "book", "cancel",
}


@dataclass(frozen=True)
class LanguageResult:
    code: str
    base: str
    name: str


def _tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def _score(tokens, vocabulary):
    score = 0.0
    for token in tokens:
        if token in vocabulary:
            score += 1.0
        elif len(token) >= 4 and any(SequenceMatcher(None, token, word).ratio() >= 0.84 for word in vocabulary):
            score += 0.65
    return score


def detect_language(message, history=None):
    tokens = _tokens(message)
    normalized = " ".join(tokens)
    scores = {
        "ceb": _score(tokens, CEBUANO),
        "fil": _score(tokens, FILIPINO),
        "en": _score(tokens, ENGLISH),
    }
    if any(phrase in normalized for phrase in ("pila ang", "unsa na", "unsaon", "akong", "kanus a", "asa nga")):
        scores["ceb"] += 2.0
    if any(phrase in normalized for phrase in ("magkano", "ano na", "paano", "appointment ko", "kailan ko", "aking")):
        scores["fil"] += 2.0
    local = "ceb" if scores["ceb"] > scores["fil"] else "fil"
    local_score = scores[local]
    english_score = scores["en"]

    if local_score and english_score:
        code = f"{local}-en"
    elif local_score:
        code = local
    elif english_score:
        code = "en"
    else:
        code = _previous_language(history) or "en"
    base = "ceb" if code.startswith("ceb") else "fil" if code.startswith("fil") else "en"
    return LanguageResult(code=code, base=base, name=LANGUAGE_NAMES[code])


def _previous_language(history):
    for item in reversed(history or []):
        if item.get("role") != "resident":
            continue
        result = detect_language(item.get("text", ""), history=None)
        if result.code != "en" or _score(_tokens(item.get("text", "")), ENGLISH):
            return result.code
    return None
