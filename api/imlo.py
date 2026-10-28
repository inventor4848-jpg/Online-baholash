"""O'zbek imlosi: o'/g' -> o‘/g‘, a' -> a’, "..." -> “...”, sarlavhada faqat birinchi so'z bosh harfda."""
import re

# Bosh harfli oddiy so'z (EduAssess, AI kabi aralash/katta harfli nomlar emas)
CAP_WORD = re.compile(r"(?<![\w‘’])[A-Z][a-z‘’]+(?![\w‘’])")


def apostrophes(t):
    t = re.sub(r"([oOgG])['`ʻʼ‘’](?=[A-Za-z])", r"\1‘", t)
    t = re.sub(r"(?<=[A-Za-z])([oOgG])['`ʻʼ’](?![\w‘’'])", r"\1‘", t)  # so'z oxirida: CNNO' -> CNNO‘
    return re.sub(r"(?<=[A-Za-z])['`ʻʼ](?=[A-Za-z])", "’", t)


def quotes(t):
    return re.sub(r'"([^"\n]{1,300}?)"', r"“\1”", t)


def sentence_case(t):
    # Birinchi so'z va gap (. ! ?) boshidagi so'zdan tashqari hammasi kichik harf bilan
    def low(m):
        before = t[:m.start()].rstrip()
        if not re.search(r"[A-Za-z0-9‘’]", before) or before[-1] in ".!?":
            return m.group(0)
        return m.group(0)[0].lower() + m.group(0)[1:]
    return CAP_WORD.sub(low, t)


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
        elif k == "name" and action == "saveGroup":
            out[k] = _apply(apostrophes, v)
        elif k in PAYLOAD_RULES:
            out[k] = _apply(PAYLOAD_RULES[k], v)
        else:
            out[k] = v
    return out
