"""Seleciona videos da AUVP Capital 2025 relevantes para EMPRESARIO e gera input/auvp_bateriaN.txt"""
import io, json, os, re, sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Curadoria por tema util a dono de empresa. Ordem = prioridade.
# (trecho unico do titulo, eixo tematico)
PICKS = [
    # --- BATERIA 1 (2) ---
    ("Recuperações judiciais EXPLODINDO",      "o que quebra empresas hoje"),
    ("O que mudou no IMPOSTO DE RENDA",        "tributario / carga fiscal"),
    # --- BATERIA 2 (18) ---
    ("Crédito Privado: O motor OCULTO",        "credito e custo de capital"),
    ("A QUEDA da Sadia",                       "risco financeiro / tesouraria da empresa"),
    ("GAROTO: o império familiar",             "conflito societario e sucessao"),
    ("Adidas vs. Puma",                        "sociedade que azeda"),
    ("Como a OI QUEBROU",                      "endividamento e falencia"),
    ("O que aconteceu com a General Electric",  "gestao e diversificacao errada"),
    ("Como a Red Bull GANHA DINHEIRO",         "modelo de negocio e marca"),
    ("O McDonald’s não é uma rede de lanchonetes", "modelo de negocio oculto"),
    ("Como a HERMÈS se tornou a grife",        "posicionamento e margem"),
    ("TRAMONTINA",                             "industria familiar brasileira que escalou"),
    ("Como a CHILLI BEANS virou a MAIOR marca", "empreendedorismo brasileiro"),
    ("startup de cashback do Brasil",          "startup BR / tech"),
    ("A VERDADE por trás da Smart Fit",        "escala e franquia"),
    ("A máfia PayPal",                         "ecossistema tech / fundadores"),
    ("A BOLHA DAS IAS",                        "setor de tecnologia / IA"),
    ("A GUERRA FRIA da inteligência artificial", "geopolitica da IA"),
    ("O que é IPO e como ele pode transformar", "captacao de capital"),
    ("Shopee: O app que MUDOU o e-commerce",   "estrategia de entrada em mercado"),
]

d = json.load(io.open("scripts/candidatos_auvp_2025.json", encoding="utf-8"))
by_title = d["candidatos"]

def find(frag):
    f = re.sub(r"\s+", " ", frag).lower()
    hits = [c for c in by_title if f in re.sub(r"\s+", " ", c["title"]).lower()]
    return hits[0] if hits else None

sel, faltando = [], []
for frag, tema in PICKS:
    c = find(frag)
    if c:
        sel.append({**c, "tema": tema})
    else:
        faltando.append(frag)

if faltando:
    print("!! NAO ENCONTRADOS:")
    for f in faltando: print("   -", f)

b1, b2 = sel[:2], sel[2:]
DEST = {"auvp_bateria1": "input/auvp_bateria1.txt",
        "auvp_bateria2": "scripts/staging_auvp_bateria2.txt"}
for nome, lote in (("auvp_bateria1", b1), ("auvp_bateria2", b2)):
    with io.open(DEST[nome], "w", encoding="utf-8") as fh:
        for c in lote:
            fh.write(c["url"] + "\n")
    print(f"\n=== {nome}: {len(lote)} videos -> {DEST[nome]}")
    for i, c in enumerate(lote, 1):
        print(f" {i:>2}. [{c['upload_date']}] {c['duration_min']:>4}m | {c['tema']:<38} | {c['title'][:56]}")

json.dump(sel, io.open("scripts/selecao_auvp.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(f"\ntotal selecionado: {len(sel)} | duracao somada: {round(sum(c['duration_min'] for c in sel))} min")
