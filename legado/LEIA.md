# O que foi substituído, e por quê

Nada aqui foi apagado. Isto é o baixador anterior à reformulação de 2026-09-22
(ticket `0022-biblioteca-do-youtube`), guardado inteiro porque ele **funciona** —
busca por canal, filtro de data, PO Token e corte de áudio são dele, e a camada
nova não refez nada disso.

O que ele não tinha é biblioteca: uma memória que soubesse dizer *já temos este
vídeo?* sem errar. É isso que `biblioteca/` passou a fazer.

| Aqui | O que substituiu | Por quê |
|---|---|---|
| `download_music.py` | `biblioteca/baixador.py` + `biblioteca/cli.py` | A trava de repetição comparava título por substring, nos dois sentidos. O mesmo vídeo desceu duas vezes. |
| `config.json` | `perfis/<acervo>.json` | Havia **uma** configuração global, com um `output_dir` trocado à mão a cada rodada. É por isso que `output/` tem cinco pastas do mesmo canal. |
| `input/*.txt` | o campo `alvos` de cada perfil | A instrução vivia separada do destino. Agora as duas metades moram no mesmo arquivo. |
| `scripts/find_*.py` | `python -m biblioteca baixar <perfil>` | Eram buscas de uma vez só, com seus `.log` e seus despejos `.json` commitados ao lado. |
| `split_audio.py` | ainda não substituído | O corte por duração continua sem equivalente na camada nova. O campo `corte` do perfil está reservado para ele. |

## O `download_music.py` ainda roda?

Roda, desde a **raiz do repositório** — ele usa caminhos relativos ao diretório
de trabalho, não ao próprio arquivo:

```bash
python legado/download_music.py
```

Mas ele escreve no `history.json`, que deixou de ser a fonte da verdade, e grava
nomes de arquivo sem o id do vídeo — a causa das 144 entradas cegas. Use-o só
para conferir comportamento antigo.

## O `history.json`

Continua na raiz, e continua sendo lido: `python -m biblioteca indexar` tira
dele os 219 ids que existem, e foi com eles que 257 dos 300 arquivos em disco
recuperaram o seu. Ele é **fonte de migração**, não fonte da verdade. A fonte é
`catalogo.json`.
