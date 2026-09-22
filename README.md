# music-downloader — a biblioteca do YouTube

Baixa vídeo do YouTube por instrução escrita, guarda como áudio, e **nunca baixa
o mesmo vídeo duas vezes**.

A regra que sustenta tudo: **o id do YouTube é a chave**. Título não é chave — o
YouTube devolve o título traduzido conforme o idioma de quem pede, e foi por
confiar em título que o mesmo vídeo já desceu duas vezes nesta biblioteca, sob
duas grafias, ocupando 237 MB para um vídeo só.

## Como se usa

```bash
python -m biblioteca conferir                      # o estado da biblioteca
python -m biblioteca perfis                        # que instruções existem
python -m biblioteca baixar <perfil> --so-conferir # o que ele faria
python -m biblioteca baixar <perfil>               # o que ele faz
```

Um download avulso, com os filtros de um perfil mas sem mexer nele:

```bash
python -m biblioteca baixar auvp-capital-negocios --alvo "https://youtu.be/pnVWzqttbJI"
```

`--so-conferir` vale para `indexar`, `baixar` e `reorganizar`: diz o que faria e
não faz.

## O perfil é a instrução

Um arquivo em `perfis/`, e ele junta as duas metades que antes viviam separadas
— o que buscar (`input/*.txt`) e para onde mandar (`config.json`, um
`output_dir` global trocado à mão a cada rodada).

```json
{
  "acervo": "auvp-capital-negocios",
  "descricao": "AUVP Capital, os vídeos de negócios",
  "canais_permitidos": ["AUVP Capital"],
  "formato": "audio",
  "duracao_minima_minutos": 8,
  "alvos": [
    "https://www.youtube.com/watch?v=pnVWzqttbJI",
    "história da Coca-Cola AUVP"
  ]
}
```

`alvos` aceita URL (em qualquer das seis grafias do YouTube) ou termo de busca.
Campo com nome errado é **recusado na carga** — erro de digitação silencioso num
filtro de download custa horas de banda.

| Campo | O quê |
|---|---|
| `acervo` | obrigatório; é a pasta em `output/` e o nome do acervo no catálogo |
| `formato` | `audio` (padrão) ou `video` |
| `canais_permitidos` | recusa o que vier de outro canal |
| `publicado_entre` | `["2025-01-01", "2025-12-31"]` |
| `duracao_minima_minutos` / `duracao_maxima_minutos` | corta cacos e lives longas |
| `resultados_por_busca` | quantos resultados olhar num termo de busca (padrão 10) |
| `corte` | reservado para o corte por duração; ainda em `legado/split_audio.py` |

## O nome do arquivo carrega o id

```
output/auvp-capital-negocios/2026-09-18_Como_a_BRF_voltou_a_dar_LUCRO_[pnVWzqttbJI].mp3
        └─ acervo ────────┘  └ data ──┘ └─ título ───────────────────┘ └── id ──┘
```

A data na frente ordena a pasta sozinha. O id no fim é o que permite reconstruir
o catálogo a partir do disco — coisa que a convenção antiga (`Título -
09-11-2025.mp3`) não permitia, e que é a causa direta das 144 entradas sem id no
`history.json`.

## O catálogo é a fonte

`catalogo.json`, chaveado por id:

```json
{
  "itens": {
    "pnVWzqttbJI": {
      "id": "pnVWzqttbJI",
      "titulo": "Como a BRF voltou a dar LUCRO?",
      "url": "https://www.youtube.com/watch?v=pnVWzqttbJI",
      "canal": "AUVP Capital",
      "publicado": "2026-09-18",
      "acervo": "auvp-capital-negocios",
      "arquivos": ["output/auvp-capital-negocios/2026-09-18_..._[pnVWzqttbJI].mp3"],
      "formato": "audio",
      "origem": "download"
    }
  },
  "sem_id": [ { "arquivo": "...", "situacao": "incerto" } ]
}
```

Perguntar *já temos?* é consultar uma chave. `sem_id` guarda o que veio de
varredura antiga e nunca vai ter id: é memória fraca, **não trava download
nenhum** — travar por título foi exatamente o defeito.

### O catálogo viaja; a mídia não

`catalogo.json` está no git. `output/` não está — são 7,2 GB. Num clone novo, portanto,
todo caminho anotado aponta para um arquivo que não está ali, e o repositório é o **índice**
de uma biblioteca cuja mídia mora noutra máquina.

Por isso quem pergunta *quantos temos em disco* olha o disco, não a anotação:

```
catalogo: 223 ids  |  2 com arquivo neste disco  |  221 so no catalogo
  destes, 212 tem caminho anotado cujo arquivo nao esta neste disco (midia fora do git)
```

O mesmo vale para `duplicatas`: dois caminhos anotados com só um arquivo presente não são
duplicata **neste** disco. Já a trava de download continua sendo o catálogo inteiro — não
se baixa de novo um vídeo que existe noutra máquina só porque este clone está vazio.

Para reconstruir o catálogo do zero, a partir do disco e do `history.json`:

```bash
python -m biblioteca indexar
```

É idempotente. Rodar de novo não duplica nada, porque tudo entra por id.

## O acervo antigo

```bash
python -m biblioteca duplicatas                  # o mesmo id em mais de um arquivo
python -m biblioteca reorganizar --so-conferir   # o que a arrumação faria
```

`reorganizar` põe o id no nome dos arquivos antigos e junta pastas que são o
mesmo acervo (`raul_sena`, `raul_sena_2`, `raul_sena_2025_mar`,
`raul_sena_2025_new`, `raul_sena_batch5` — cinco batidas do mesmo canal, não
cinco categorias):

```bash
python -m biblioteca reorganizar --para raul-sena \
  --de raul_sena --de raul_sena_2 --de raul_sena_2025_mar \
  --de raul_sena_2025_new --de raul_sena_batch5 --so-conferir
```

**Ele move, nunca apaga.** Quando dois arquivos disputam o mesmo destino — as
duas grafias do mesmo vídeo — nenhum se move e os dois entram no relatório de
conflito. Qual versão fica é decisão do operador.

## Setup

```bash
pip install -r requirements.txt
```

O download exige o servidor de **PO Token** no ar; sem ele o YouTube devolve
HTTP 403. A biblioteca sobe o servidor sozinha se achar o build, e avisa se não
achar. O setup está em [`docs/DOC-TECNICO.md`](docs/DOC-TECNICO.md).

## A prova

```bash
python -m unittest discover -s testes -v
```

32 testes, sem rede. Cada um existe porque um defeito medido existiu, e o nome
do teste diz qual.

## O que ficou para trás

[`legado/`](legado/LEIA.md) — o baixador anterior, inteiro e ainda executável. A
busca por canal, o filtro de data, o PO Token e o corte de áudio são dele; esta
camada não refez nada disso. O que ela acrescentou foi a biblioteca em cima.
