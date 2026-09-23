# -*- coding: utf-8 -*-
"""O catalogo: a memoria da biblioteca, chaveada pelo id do YouTube.

Substitui o `history.json`, que era uma lista e cuja trava de repeticao
comparava titulo por substring -- teste que errava nos dois sentidos e deixou
o mesmo video descer duas vezes.

Aqui `itens` e um dicionario `id -> registro`. Perguntar "ja temos?" e
consultar uma chave, nao varrer uma lista comparando texto.

`sem_id` guarda o que veio de varredura de disco antiga e nunca vai ter id,
porque o nome do arquivo daquela epoca nao gravava o id. Nao se apaga: e
memoria, ainda que fraca. Serve de aviso, nao de trava.
"""
import json
import os
import tempfile
from datetime import datetime, timezone

from . import ids as _ids

VERSAO = 1
ARQUIVO_PADRAO = 'catalogo.json'


def _agora():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')


class Catalogo:
    """Le, consulta e grava o catalogo. Uma instancia por processo."""

    def __init__(self, caminho=ARQUIVO_PADRAO):
        self.caminho = caminho
        self.itens = {}
        self.sem_id = []
        self._carregar()

    # --- disco ------------------------------------------------------------

    def _carregar(self):
        if not os.path.exists(self.caminho):
            return
        with open(self.caminho, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        self.itens = dados.get('itens') or {}
        self.sem_id = dados.get('sem_id') or []

    def gravar(self):
        """Grava de forma atomica: escreve ao lado e troca.

        Sem isto, duas threads baixando em paralelo podem truncar o arquivo --
        e o catalogo e a unica memoria que impede baixar tudo de novo.
        """
        dados = {
            'versao': VERSAO,
            'gerado': _agora(),
            'total': len(self.itens),
            'itens': self.itens,
            'sem_id': self.sem_id,
        }
        pasta = os.path.dirname(os.path.abspath(self.caminho))
        os.makedirs(pasta, exist_ok=True)
        fd, temporario = tempfile.mkstemp(dir=pasta, prefix='.catalogo-', suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
            os.replace(temporario, self.caminho)
        except BaseException:
            if os.path.exists(temporario):
                os.unlink(temporario)
            raise

    # --- consulta ---------------------------------------------------------

    def tem(self, video_id):
        """A trava de repeticao inteira. Uma chave, sem comparacao de texto."""
        return bool(video_id) and video_id in self.itens

    def registro(self, video_id):
        return self.itens.get(video_id)

    def por_acervo(self, acervo):
        return {k: v for k, v in self.itens.items() if v.get('acervo') == acervo}

    def presentes(self, video_id):
        """Os arquivos deste id que existem AGORA, neste disco.

        O catalogo viaja no git; a midia nao (sao 7,2 GB no `.gitignore`). Num
        clone novo, portanto, todo caminho anotado aponta para arquivo que nao
        esta la. Quem responde "quantos temos em disco" tem que olhar o disco,
        nao a anotacao -- senao um clone recem-feito se declara cheio.
        """
        reg = self.itens.get(video_id) or {}
        return [a for a in reg.get('arquivos', []) if os.path.exists(a)]

    def duplicatas_em_disco(self):
        """Ids com mais de um arquivo inteiro PRESENTE (cortes _part nao contam).

        E o relatorio que mostra o estrago da convencao antiga sem apagar nada:
        apagar midia e decisao do operador (duvida 4).
        """
        achados = {}
        for video_id in self.itens:
            inteiros = [a for a in self.presentes(video_id)
                        if '_part' not in os.path.basename(a)]
            if len(inteiros) > 1:
                achados[video_id] = inteiros
        return achados

    # --- escrita ----------------------------------------------------------

    def anotar(self, video_id, *, titulo=None, canal=None, publicado=None,
               acervo=None, arquivo=None, formato=None, origem='download'):
        """Cria ou completa o registro de um id. Nunca perde arquivo ja anotado."""
        if not video_id:
            raise ValueError('anotar() exige o id do YouTube')
        reg = self.itens.setdefault(video_id, {
            'id': video_id,
            'url': _ids.url_canonica(video_id),
            'arquivos': [],
            'visto_em': _agora(),
        })
        for campo, valor in (('titulo', titulo), ('canal', canal),
                             ('publicado', publicado), ('acervo', acervo),
                             ('formato', formato)):
            if valor and not reg.get(campo):
                reg[campo] = valor
        reg.setdefault('origem', origem)
        if arquivo:
            caminho = arquivo.replace('\\', '/')
            if caminho not in reg['arquivos']:
                reg['arquivos'].append(caminho)
        return reg

    def anotar_sem_id(self, titulo_arquivo, arquivo, origem='disco',
                      situacao='incerto'):
        """Registra o que nao tem id. Nao trava download nenhum.

        `situacao` separa `id-perdido` (desceu do YouTube e o id nao foi
        gravado -- isso e perda) de `nao-e-do-youtube` (sample, arquivo local --
        nunca teve id, e nao ter nao e defeito).
        """
        caminho = (arquivo or '').replace('\\', '/')
        for item in self.sem_id:
            if item.get('arquivo') == caminho:
                # `incerto` e o rotulo da primeira versao, de quando os dois
                # casos viviam num balde so. Ver de novo e chance de melhorar.
                if item.get('situacao') in (None, 'incerto'):
                    item['situacao'] = situacao
                return item
        item = {
            'titulo_arquivo': titulo_arquivo,
            'arquivo': caminho,
            'origem': origem,
            'situacao': situacao,
        }
        self.sem_id.append(item)
        return item
