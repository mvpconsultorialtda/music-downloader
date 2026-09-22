import io, json, re, sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
d = json.load(io.open("scripts/candidatos_auvp_2025.json", encoding="utf-8"))
c = d["candidatos"]
com = [x for x in c if re.search(r"raul|sardinha", (x["title"]+" "+x["description"]).lower())]
print(f"total {len(c)} | mencionam Raul/Sardinha: {len(com)}")
for x in com[:40]:
    print(f"  [{x['upload_date']}] {x['duration_min']}m | {x['title'][:70]}")
print("\n--- amostra de descricao (video generico) ---")
print(c[5]["title"], "\n", c[5]["description"][:500])
