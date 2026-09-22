"""Lista videos 2025 do canal Investidor Sardinha e cruza com history.json + arquivos em disco.
Imprime os candidatos ainda NAO baixados (para escolher 3)."""
import io, json, os, re, glob, sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import yt_dlp

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CHANNEL = "https://www.youtube.com/@investidorsardinha/videos"

def norm(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s

# history
hist = json.load(io.open("history.json", encoding="utf-8"))["downloaded"]
hist_ids = {it.get("id") for it in hist if it.get("id")}
hist_norm = {norm(it.get("title")) for it in hist if it.get("title")}

# arquivos em disco (todos os output/*)
disk_norm = set()
for f in glob.glob("output/**/*.mp3", recursive=True):
    name = os.path.basename(f)
    name = re.sub(r"\s*-\s*\d{2}-\d{2}-\d{4}.*$", "", os.path.splitext(name)[0])
    name = re.sub(r"_part\d+$", "", name)
    disk_norm.add(norm(name))

print(f"history: {len(hist_ids)} ids, {len(hist_norm)} titles | disk: {len(disk_norm)} nomes")

# lista o canal (flat, rapido) - fundo o suficiente para alcancar 2025
opts = {"extract_flat": True, "quiet": True, "no_warnings": True, "playlistend": 700}
with yt_dlp.YoutubeDL(opts) as ydl:
    info = ydl.extract_info(CHANNEL, download=False)
entries = info.get("entries") or []
print(f"entradas no canal (flat): {len(entries)}")

# newest-first. ~1 video/dia => 2025 comeca por volta do indice ~200. Resolve a partir de OFFSET.
OFFSET = 190
found = []
opts2 = {"quiet": True, "no_warnings": True, "skip_download": True}
with yt_dlp.YoutubeDL(opts2) as ydl:
    for idx, e in enumerate(entries):
        if idx < OFFSET:
            continue
        vid = e.get("id")
        title = e.get("title") or ""
        if not vid:
            continue
        nt = norm(title)
        already = vid in hist_ids or nt in hist_norm or nt in disk_norm
        try:
            meta = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
        except Exception as ex:
            print(f"  erro idx={idx} {vid}: {str(ex)[:60]}")
            continue
        ud = meta.get("upload_date") or ""
        year = ud[:4]
        flag = "JA-BAIXADO" if already else "NOVO"
        print(f"[{year}] {ud} | {flag:10} | {title[:55]} | {vid}")
        if year == "2025" and not already:
            found.append({"id": vid, "title": title, "upload_date": ud,
                          "url": f"https://www.youtube.com/watch?v={vid}"})
        if len(found) >= 22:
            break
        if year and year < "2025":
            break  # passou de 2025, pode parar

json.dump(found, io.open("scripts/candidatos_2025.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(f"\nSalvos {len(found)} candidatos 2025 em scripts/candidatos_2025.json")
