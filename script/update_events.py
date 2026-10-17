#!/usr/bin/env python3
"""Update otomatis events.json:
1. Menghapus acara yang sudah lewat.
2. Membaca halaman resmi tiap organisasi (daftar SOURCES), meminta AI mengekstrak acara
   mendatang, memvalidasi ketat, lalu menambahkan yang lolos.
Acara yang meragukan tidak ditambahkan, hanya dilaporkan di laporan.md.
AI yang dipakai: Google Gemini (kunci gratis dari Google AI Studio, disimpan sebagai secret GEMINI_API_KEY).
"""
import json, os, re, time, datetime, urllib.request, urllib.parse, urllib.error

# (nama, halaman resmi, boleh ditambah otomatis?)
# True  = acara ditambah otomatis hanya bila alamat acaranya satu domain dengan halaman sumber.
# False = hanya dilaporkan untuk dicek manual (misalnya kalender gabungan).
# ARVO sengaja tidak dimasukkan: situsnya memblokir pembacaan otomatis (HTTP 403).
SOURCES = [
    ("ACS", "https://asiacorneasociety.org/", True),
    ("APACRS", "https://apacrs.org/meetings.asp?info=3", True),
    ("EURETINA", "https://euretina.org/future-meetings/", True),
    ("AAO", "https://aao.org/annual-meeting/past-and-future-meetings", True),
    ("ASRS", "https://www.asrs.org/annual-meeting/future-annual-meetings", True),
    ("AAPOS", "https://aapos.org/education-and-events/meetings-future", True),
    ("ASCRS", "https://www.ascrs.org/Meetings/Next-Year", True),
    ("PERDAMI", "https://perdami.or.id/meetings", True),
    ("SOE Ophthagenda (kalender gabungan)", "https://soevision.org/ophthagenda/list/", False),
]

# Model dicoba berurutan; kalau satu tidak tersedia atau kena batas (HTTP 400/404/429/503), lanjut ke berikutnya.
MODELS = [m for m in [os.environ.get("GEMINI_MODEL"), "gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-3-flash-preview"] if m]
API_KEY = os.environ.get("GEMINI_API_KEY", "")
PAUSE = 6  # detik jeda antar permintaan, supaya tidak melewati batas kecepatan paket gratis
TODAY = datetime.date.today()
STOP = {"annual", "meeting", "congress", "society", "european", "american", "asia", "pacific",
        "the", "and", "for", "new", "with", "international", "academy", "association"}


def describe(ex):
    """Ringkasan galat yang mudah dibaca, termasuk kode HTTP dan pesan dari server."""
    if isinstance(ex, urllib.error.HTTPError):
        try:
            body = ex.read().decode("utf-8", "ignore").replace("\n", " ")[:220]
        except Exception:
            body = ""
        return "HTTP {} {}".format(ex.code, body).strip()
    return (type(ex).__name__ + " " + str(ex))[:200]


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; EventsUpdater/1.0)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


def page_text(html, base):
    html = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", html)

    def link(m):
        href = urllib.parse.urljoin(base, m.group(1))
        label = re.sub(r"<[^>]+>", " ", m.group(2)).strip()
        return " {} ({}) ".format(label, href)

    html = re.sub(r"(?is)<a\b[^>]*?href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", link, html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    return re.sub(r"\s+", " ", text)[:20000]


def ask(name, url, text):
    prompt = (
        "Today is " + TODAY.isoformat() + ". Below is text from the official page of " + name + " (" + url + "). "
        "List every upcoming ophthalmology or medical meeting on it that has an explicit start date and end date on or after today. "
        "Return ONLY a JSON array, no prose. Each item must be an object with keys: "
        "t (official event name including the year), s (start date YYYY-MM-DD), e (end date YYYY-MM-DD), "
        "l (venue, city, country), u (absolute https URL of the event page, copied from the page text). "
        "Never guess. Omit any event whose exact dates or URL are not stated on the page. If there are none, return [].\n\n"
        "PAGE TEXT:\n" + text
    )
    last = None
    for model in MODELS:
        body = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent",
            data=body, headers={"x-goog-api-key": API_KEY, "content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read().decode("utf-8"))
            cands = data.get("candidates") or []
            parts = (cands[0].get("content") or {}).get("parts") or [] if cands else []
            return "".join(p.get("text", "") for p in parts)
        except urllib.error.HTTPError as e:
            if e.code in (400, 404, 429, 503):
                last = e
                if e.code in (429, 503):
                    time.sleep(PAUSE * 3)
                continue
            raise
    raise last


def parse_json(s):
    i, j = s.find("["), s.rfind("]")
    return json.loads(s[i:j + 1]) if 0 <= i < j else []


def valid(c):
    try:
        s = datetime.date.fromisoformat(c["s"])
        e = datetime.date.fromisoformat(c["e"])
    except Exception:
        return False
    return (isinstance(c.get("t"), str) and c["t"].strip() != ""
            and isinstance(c.get("l"), str) and c["l"].strip() != ""
            and isinstance(c.get("u"), str) and c["u"].startswith("https://")
            and s <= e and e >= TODAY
            and e <= TODAY + datetime.timedelta(days=1100)
            and (e - s).days <= 14)


def reg_domain(u):
    p = (urllib.parse.urlparse(u).hostname or "").split(".")
    if len(p) >= 3 and p[-2] in {"co", "or", "ac", "go", "com", "org", "net", "edu", "gov"} and len(p[-1]) == 2:
        return ".".join(p[-3:])
    return ".".join(p[-2:]) if len(p) >= 2 else ".".join(p)


def toks(t):
    return {w for w in re.findall(r"[a-z0-9]+", t.lower()) if len(w) >= 3 and w not in STOP and not w.isdigit()}


def is_dup(c, existing):
    for v in existing:
        if v["u"].rstrip("/") == c["u"].rstrip("/"):
            return True
        gap = abs((datetime.date.fromisoformat(v["s"]) - datetime.date.fromisoformat(c["s"])).days)
        if gap <= 3 and toks(v["t"]) & toks(c["t"]):
            return True
    return False


def write_events(path, events):
    events.sort(key=lambda v: (v["s"], v["t"]))
    with open(path, "w", encoding="utf-8") as f:
        f.write("[\n" + ",\n".join("  " + json.dumps(v, ensure_ascii=False) for v in events) + "\n]\n")


def main():
    with open("events.json", encoding="utf-8") as f:
        events = json.load(f)
    removed = [v for v in events if v["e"] < TODAY.isoformat()]
    events = [v for v in events if v["e"] >= TODAY.isoformat()]
    added, maybe, errors = [], [], []

    if not API_KEY:
        errors.append("GEMINI_API_KEY belum dipasang. Penambahan acara baru dilewati; penghapusan acara yang sudah lewat tetap berjalan.")
    else:
        for name, url, auto in SOURCES:
            try:
                html = http_get(url)
            except Exception as ex:
                errors.append("{}: gagal membuka halaman ({})".format(name, describe(ex)))
                continue
            try:
                items = parse_json(ask(name, url, page_text(html, url)))
            except Exception as ex:
                errors.append("{}: gagal dibaca AI ({})".format(name, describe(ex)))
                continue
            time.sleep(PAUSE)
            for c in items:
                if not isinstance(c, dict) or not valid(c):
                    continue
                c = {k: str(c[k]).strip() for k in ("t", "s", "e", "l", "u")}
                c["t"] = c["t"][:140]
                if is_dup(c, events) or is_dup(c, maybe):
                    continue
                if auto and reg_domain(c["u"]) == reg_domain(url):
                    c["src"] = urllib.parse.urlparse(c["u"]).hostname
                    events.append(c)
                    added.append(c)
                else:
                    maybe.append(c)

    if removed or added:
        write_events("events.json", events)

    if removed or added or maybe or errors:
        fmt = "- **{t}**, {s} s/d {e}, {l} ([situs]({u}))"
        out = "# Update seminar otomatis, " + TODAY.isoformat() + "\n\n"
        out += "## Ditambahkan otomatis\n" + ("\n".join(fmt.format(**c) for c in added) or "Tidak ada.") + "\n\n"
        out += "## Dihapus karena sudah lewat\n" + ("\n".join("- " + v["t"] for v in removed) or "Tidak ada.") + "\n\n"
        out += "## Perlu dicek manual (tidak ditambahkan)\n" + ("\n".join(fmt.format(**c) for c in maybe) or "Tidak ada.") + "\n\n"
        out += "## Masalah\n" + ("\n".join("- " + e for e in errors) or "Tidak ada.") + "\n\n"
        out += "Acara yang ditambahkan otomatis dibaca AI dari halaman resmi. Cek tanggalnya di situs resmi; kalau salah, hapus barisnya dari events.json.\n"
        with open("laporan.md", "w", encoding="utf-8") as f:
            f.write(out)
        print(out)
    else:
        print("Tidak ada perubahan.")


if __name__ == "__main__":
    main()
