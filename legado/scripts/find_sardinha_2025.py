"""Descobre videos 2025 do canal AUVP Capital, 4-30 min, novos (nao baixados).

Estrategia eficiente:
1. flat list do canal (1 request) -> cache em scripts/sardinha_flat.json
2. filtra por duracao (barato, vem no flat)
3. busca binaria para achar a faixa de indices de 2025 (lista e newest-first)
4. resolve metadados SO dentro da faixa

Salva scripts/candidatos_sardinha_2025.json
"""
import io, json, os, re, glob, sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import yt_dlp

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHANNEL = "https://www.youtube.com/@investidorsardinha/videos"
FLAT_CACHE = "scripts/sardinha_flat.json"
MAX_DUR, MIN_DUR = 30 * 60, 4 * 60


def norm(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def p(*a):
    print(*a, flush=True)


# ---------- ja baixados ----------
hist = json.load(io.open("history.json", encoding="utf-8"))["downloaded"]
hist_ids = {it.get("id") for it in hist if it.get("id")}
hist_norm = {norm(it.get("title")) for it in hist if it.get("title")}
disk_norm = set()
for f in glob.glob("output/**/*.mp3", recursive=True):
    n = os.path.splitext(os.path.basename(f))[0]
    n = re.sub(r"\s*-\s*\d{2}-\d{2}-\d{4}.*$", "", n)
    disk_norm.add(norm(re.sub(r"_part\d+$", "", n)))
p(f"ja baixados: {len(hist_ids)} ids / {len(disk_norm)} nomes em disco")

# ---------- flat list (com cache) ----------
if os.path.exists(FLAT_CACHE):
    entries = json.load(io.open(FLAT_CACHE, encoding="utf-8"))
    p(f"flat list do cache: {len(entries)} videos")
else:
    with yt_dlp.YoutubeDL({"extract_flat": True, "quiet": True,
                           "no_warnings": True, "playlistend": 800}) as y:
        info = y.extract_info(CHANNEL, download=False)
    entries = [{"id": e.get("id"), "title": e.get("title"), "duration": e.get("duration")}
               for e in (info.get("entries") or []) if e.get("id")]
    json.dump(entries, io.open(FLAT_CACHE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    p(f"canal: {info.get('title')} | {len(entries)} videos -> cache")

pre = [e for e in entries if e.get("duration") and MIN_DUR <= e["duration"] <= MAX_DUR]
p(f"apos filtro duracao {MIN_DUR//60}-{MAX_DUR//60}min: {len(pre)} (de {len(entries)})")

YDL = yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True})
_meta_cache = {}


def meta(i):
    """Metadados do item pre[i], com cache."""
    if i not in _meta_cache:
        vid = pre[i]["id"]
        _meta_cache[i] = YDL.extract_info(f"https://www.youtube.com/watch?v={vid}",
                                          download=False)
    return _meta_cache[i]


def year_at(i):
    try:
        return (meta(i).get("upload_date") or "9999")[:4]
    except Exception as ex:
        p(f"  erro idx {i}: {str(ex)[:60]}")
        return None


def bisect_year(target):
    """Primeiro indice cujo ano < target (lista newest-first => anos decrescentes)."""
    lo, hi = 0, len(pre)
    while lo < hi:
        mid = (lo + hi) // 2
        yr = year_at(mid)
        if yr is None:          # falhou: pula 1 pra frente
            yr = year_at(min(mid + 1, len(pre) - 1)) or "0000"
        if yr >= target:
            lo = mid + 1
        else:
            hi = mid
    return lo


p("busca binaria: inicio de 2025...")
start = bisect_year("2026")   # primeiro indice com ano < 2026 => primeiro de 2025
p(f"  start = {start} ({(meta(start).get('upload_date') if start < len(pre) else '?')})")
p("busca binaria: fim de 2025...")
end = bisect_year("2025")     # primeiro indice com ano < 2025
p(f"  end = {end} => faixa de {end - start} videos para resolver")

cands = []
for i in range(start, min(end, len(pre))):
    try:
        m = meta(i)
    except Exception as ex:
        p(f"  erro idx {i}: {str(ex)[:60]}")
        continue
    ud = m.get("upload_date") or ""
    if ud[:4] != "2025":
        continue
    title = m.get("title") or pre[i]["title"]
    desc = m.get("description") or ""
    dur = m.get("duration") or 0
    vid = m.get("id")
    nt = norm(title)
    already = vid in hist_ids or nt in hist_norm or nt in disk_norm
    p(f"[{ud}] {int(dur//60):>3}m {'JA  ' if already else 'NOVO'} | {title[:62]}")
    if already:
        continue
    cands.append({"id": vid, "title": title, "upload_date": ud,
                  "duration_min": round(dur / 60, 1),
                  "view_count": m.get("view_count"),
                  "description": desc[:800],
                  "url": f"https://www.youtube.com/watch?v={vid}"})

json.dump({"channel": "Investidor Sardinha", "range": [start, end], "candidatos": cands},
          io.open("scripts/candidatos_sardinha_2025.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
p(f"\ncandidatos 2025 novos ({MIN_DUR//60}-{MAX_DUR//60}min): {len(cands)}")
p("-> scripts/candidatos_sardinha_2025.json")
