"""Lista os videos da AUVP Capital que ainda NAO foram baixados.

Usa o flat list do canal (1 request) e cruza com history.json + os nomes dos
MP3 em output/. A normalizacao remove acentos: sem isso "esta" e "está"
contam como titulos diferentes e um video ja baixado reaparece como novo.

Saidas: scripts/auvp_flat_2026.json (cache do canal)
        scripts/auvp_novos.json     (so os que faltam)
"""
import io, json, os, re, glob, sys, unicodedata
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import yt_dlp

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHANNEL = "https://www.youtube.com/@AUVPCapital/videos"
FLAT_CACHE = "scripts/auvp_flat_2026.json"
MIN_DUR, MAX_DUR = 4 * 60, 45 * 60


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", s.lower())


# --- canal (lang=pt: sem isso o YouTube devolve os titulos traduzidos para
# ingles e a comparacao com os arquivos em portugues nunca casa) ---
if os.path.exists(FLAT_CACHE) and "--refresh" not in sys.argv:
    entries = json.load(io.open(FLAT_CACHE, encoding="utf-8"))
    print(f"flat list do cache: {len(entries)} videos (use --refresh para atualizar)")
else:
    opts = {"extract_flat": True, "quiet": True, "no_warnings": True,
            "playlistend": 1000, "extractor_args": {"youtube": {"lang": ["pt"]}}}
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info(CHANNEL, download=False)
    entries = [{"id": e.get("id"), "title": e.get("title"), "duration": e.get("duration")}
               for e in (info.get("entries") or []) if e.get("id")]
    json.dump(entries, io.open(FLAT_CACHE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"canal: {info.get('title')} | {len(entries)} videos -> cache")

# --- ja baixados ---
hist = json.load(io.open("history.json", encoding="utf-8"))["downloaded"]
hist_ids = {it.get("id") for it in hist if it.get("id")}
have = {norm(it.get("title")) for it in hist if it.get("title")}
for f in glob.glob("output/**/*.mp3", recursive=True):
    n = os.path.splitext(os.path.basename(f))[0]
    n = re.sub(r"\s*-\s*\d{2}-\d{2}-\d{4}.*$", "", n)
    have.add(norm(re.sub(r"_part\d+$", "", n)))
have.discard("")

novos = []
for e in entries:
    d = e.get("duration") or 0
    if not (MIN_DUR <= d <= MAX_DUR):   # corta shorts e lives gigantes
        continue
    if e["id"] in hist_ids:
        continue
    t = norm(e["title"])
    if t in have or any(t and (t in h or h in t) for h in have):
        continue
    novos.append(e)

json.dump(novos, io.open("scripts/auvp_novos.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"ja baixados: {len(hist_ids)} ids | NOVOS ({MIN_DUR//60}-{MAX_DUR//60}min): {len(novos)}")
for i, e in enumerate(novos, 1):
    print(f"{i:>3}. [{round(e['duration']/60):>3}m] {e['title']}")
