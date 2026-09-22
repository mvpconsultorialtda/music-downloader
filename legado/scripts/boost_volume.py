"""Aumenta o volume de todos os MP3 em output/ em 25% (1.25x = +1.94 dB).

Os picos ja estao perto de 0 dBFS, entao o ganho passa por um limiter
(alimiter, teto 0.98) para que o aumento seja audivel sem distorcer.
Os originais vao para output_backup_pre_volume/ preservando a arvore.
"""
import os, shutil, subprocess, sys, json, concurrent.futures as cf
sys.stdout.reconfigure(encoding="utf-8")
os.chdir(r"C:\Users\projf\mvp_2026\repositorios\music_downloader")

SRC = "output"
BAK = "output_backup_pre_volume"
TMP = os.path.join(os.environ["TEMP"], "boost_tmp")
os.makedirs(TMP, exist_ok=True)
AF = "volume=1.25,alimiter=level_in=1:level_out=1:limit=0.98:attack=5:release=50"

files = []
for root, _, names in os.walk(SRC):
    for n in names:
        if n.lower().endswith(".mp3"):
            files.append(os.path.join(root, n))
files.sort()
print(f"{len(files)} arquivos MP3 para processar", flush=True)

def bitrate(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=bit_rate", "-of",
             "default=nw=1:nk=1", path],
            capture_output=True, text=True, timeout=120).stdout.strip()
        b = int(out) // 1000
        return f"{min(max(b, 64), 320)}k"
    except Exception:
        return "192k"

lock_n = [0]
def process(i_path):
    i, path = i_path
    rel = os.path.relpath(path, SRC)
    bak = os.path.join(BAK, rel)
    if os.path.exists(bak):           # ja processado numa execucao anterior
        return ("skip", rel, "")
    tmp = os.path.join(TMP, f"{i:04d}.mp3")
    r = subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
         "-i", path, "-af", AF, "-c:a", "libmp3lame", "-b:a", bitrate(path),
         "-map_metadata", "0", tmp],
        capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(tmp) or os.path.getsize(tmp) < 1024:
        if os.path.exists(tmp):
            os.remove(tmp)
        return ("erro", rel, (r.stderr or "")[-300:])
    os.makedirs(os.path.dirname(bak) or ".", exist_ok=True)
    shutil.move(path, bak)            # original -> backup
    shutil.move(tmp, path)            # versao com ganho -> lugar do original
    lock_n[0] += 1
    if lock_n[0] % 20 == 0:
        print(f"  ... {lock_n[0]}/{len(files)}", flush=True)
    return ("ok", rel, "")

res = []
with cf.ThreadPoolExecutor(max_workers=6) as ex:
    for r in ex.map(process, enumerate(files)):
        res.append(r)

ok = [r for r in res if r[0] == "ok"]
sk = [r for r in res if r[0] == "skip"]
er = [r for r in res if r[0] == "erro"]
print(f"\nOK: {len(ok)} | ja feitos: {len(sk)} | ERRO: {len(er)}")
for _, rel, msg in er:
    print(f"  ERRO {rel}: {msg}")
json.dump([{"status": s, "file": f, "err": e} for s, f, e in res],
          open(os.path.join(TMP, "resultado.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
