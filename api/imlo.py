"""O'zbek imlosi: o'/g' -> o‘/g‘, a' -> a’, "..." -> “...”, sarlavhada faqat birinchi so'z bosh harfda."""
import re

WORD = r"[A-Z][a-z‘’]+"
RUN = re.compile(r"(?<![\w‘’])" + WORD + r"(?:[ -]" + WORD + r")+(?![\w‘’])")


def apostrophes(t):
    t = re.sub(r"([oOgG])['`ʻʼ‘’](?=[A-Za-z])", r"\1‘", t)
    return re.sub(r"(?<=[A-Za-z])['`ʻʼ](?=[A-Za-z])", "’", t)


def quotes(t):
    return re.sub(r'"([^"\n]{1,300}?)"', r"“\1”", t)


def sentence_case(t):
    def low(m):
        parts = re.split(r"([ -])", m.group(0))
        return "".join(p if i == 0 or i % 2 else p[0].lower() + p[1:] for i, p in enumerate(parts))
    return RUN.sub(low, t)


def text(t):        # oddiy matn
    return quotes(apostrophes(t))


def title(t):       # sarlavha / nom
    return sentence_case(quotes(apostrophes(t)))


def json_text(t):   # JSON ichidagi matn — qo'shtirnoqqa tegilmaydi
    return apostrophes(t)


# /api/action ma'lumotidagi kalitlar uchun qoida. Bu yerda yo'q kalitlarga
# (username, pass, code, fileData, ...) tegilmaydi.
PAYLOAD_RULES = {
    "name": title, "title": title,
    "desc": text, "body": text, "reply": text, "comment": text,
    "text": text, "q": text, "explanation": text,
    "fname": apostrophes, "lname": apostrophes, "room": apostrophes,
    "opts": json_text, "options": json_text, "correct": json_text, "userAns": json_text,
}


def _apply(fn, v):
    if isinstance(v, str):
        return fn(v)
    if isinstance(v, list):
        return [_apply(fn, x) for x in v]
    return v


def normalize_payload(action, d):
    if not isinstance(d, dict):
        return d
    out = {}
    for k, v in d.items():
        if k in ("questions", "mistakes") and isinstance(v, list):
            out[k] = [normalize_payload(action, x) for x in v]
        elif k in PAYLOAD_RULES and not (k == "name" and action == "saveGroup"):
            out[k] = _apply(PAYLOAD_RULES[k], v)
        else:
            out[k] = v
    return out
