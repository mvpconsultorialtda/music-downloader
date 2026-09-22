import json, sys, io
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import yt_dlp
for ch in ["https://www.youtube.com/@AUVPCapital/videos",
           "https://www.youtube.com/@auvpcapital/videos",
           "https://www.youtube.com/@AUVP/videos",
           "https://www.youtube.com/results?search_query=auvp+capital"]:
    try:
        with yt_dlp.YoutubeDL({"extract_flat":True,"quiet":True,"no_warnings":True,"playlistend":5}) as y:
            i = y.extract_info(ch, download=False)
        e = (i.get("entries") or [])
        print(f"OK {ch} | canal={i.get('title')} | uploader={i.get('uploader')} | n={len(e)}")
        if e: print("   campos:", sorted(e[0].keys()))
        if e: print("   ex:", {k:e[0].get(k) for k in ("title","duration","timestamp","release_timestamp","id")})
    except Exception as ex:
        print(f"FAIL {ch}: {str(ex)[:120]}")
