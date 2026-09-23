---
tipo: documentacao
criado: 2026-04-07
atualizado: 2026-09-23
tags: [tech, music_downloader]
temas: [tech/music_downloader]
modo: tech
---

# Music Downloader — o que a maquina exige

> Como a ferramenta se usa esta no [`README.md`](../README.md). Aqui fica o que o
> **ambiente** exige para o download funcionar, que e a parte que quebra sozinha.
>
> A descricao do baixador anterior — arquitetura, `config.json`, `input/*.txt`, os
> `scripts/find_*.py` — saiu daqui em 2026-09-23 e esta em
> [`legado/DOC-ANTIGO.md`](../legado/DOC-ANTIGO.md), inteira. Ela descrevia uma camada
> de uso que nao existe mais, e um aviso colado no topo nao impede ninguem de seguir
> as instrucoes erradas logo abaixo.

## Setup do PO Token (obrigatorio desde ago/2026)

### O sintoma

Todo download morre em `HTTP Error 403: Forbidden`, mesmo com a extracao de
metadados funcionando normalmente. No log verboso aparece:

```
[pot] PO Token Providers: none
Detected experiment to bind GVS PO Token to video ID
YouTube is forcing SABR streaming for this client
[youtube] <id>: Downloading android vr player API JSON
```

### A causa

O YouTube passou a exigir um **PO Token** (Proof of Origin) nos clientes web.
Sem um provider de token o yt-dlp nao consegue formatos pelo cliente web e cai
no `android_vr`, cujas URLs de midia o CDN recusa com 403. Videos antigos (pre
2010) escapam da exigencia — por isso um teste com video velho da falso
negativo. Nada disso e culpa do repo: rodou normal ate 02/08/2026 e parou
sozinho quando o YouTube ligou o experimento.

### O setup

```bash
pip install -r requirements.txt   # ja traz yt-dlp nightly + o plugin

# servidor gerador do token (uma vez)
git clone --depth 1 --branch 1.3.1 \
  https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
  ~/bgutil-ytdlp-pot-provider
cd ~/bgutil-ytdlp-pot-provider/server && npm install && npx tsc
```

A biblioteca sobe o servidor sozinha (`biblioteca/baixador.py`, `garantir_pot()`)
e checa o `/ping` em `127.0.0.1:4416`. Para subir na mao:

```bash
node ~/bgutil-ytdlp-pot-provider/server/build/main.js
```

### Cuidados

- **Use o yt-dlp nightly.** A versao estavel nao acompanha os experimentos que
  o YouTube liga sem aviso — a estavel de fev/2026 falhava, a nightly resolveu.
- **A versao do servidor tem que casar com a do plugin pip** (hoje 1.3.1).
- **Modo script nao funciona bem no Windows:** o cold start do
  `generate_once.js` leva ~44s e estoura o timeout de 15s do plugin. Por isso
  o padrao aqui e o servidor HTTP, que fica quente entre chamadas.
- `js_runtimes` na API Python e **dict** (`{'node': {}}`), nao a lista do CLI.

### Verificar integridade apos baixar

O MP3 pode sair truncado se o processo for interrompido durante a conversao —
e o arquivo parcial ainda entra no `history.json`, mascarando a falha. Compare
a duracao real com a do metadado:

```bash
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 arquivo.mp3
```

Divergencia > 0.6 min = truncado: apague o arquivo, tire o caminho do
`catalogo.json` e baixe de novo.

**Nao meca o arquivo enquanto o processo roda.** O `ffprobe` num mp3 em escrita
nao falha: devolve um numero menor e plausivel. Em 2026-09-22 um audio foi
registrado como 20min23 quando tinha 22min41, porque a medicao rodou logo apos a
linha `[ExtractAudio] Destination: ...`, que anuncia o **inicio** da escrita.
Espere o processo terminar, e confira o numero contra a duracao que a listagem
do canal ja informava.


## Paralelismo: 3 e o teto pratico

`baixar --paralelos N` reparte os alvos entre N threads. Com N=3, em 2026-09-23,
2 de 20 downloads morreram em `HTTP Error 403: Forbidden` — o mesmo sintoma da
falta de PO Token, aqui por disputa: tres pedidos simultaneos ao servidor bgutil
e um deles nao recebe o token a tempo.

Nao e perda: o catalogo ja gravou os 18 que desceram, e rodar o mesmo perfil de
novo, sequencial, pegou exatamente os 2 que faltavam. Mas se a leva for grande,
sequencial custa pouco e nao precisa de segunda passada.
