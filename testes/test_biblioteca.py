# -*- coding: utf-8 -*-
"""A prova da biblioteca. Roda sem rede e sem yt-dlp tocar no YouTube.

    python -m unittest discover -s testes -v

Cada teste aqui existe porque um defeito medido existiu. O nome do teste diz
qual.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from biblioteca import (catalogo as _catalogo, ids as _ids, perfis as _perfis,
                        reorganizacao, varredura)


class OIdEAChave(unittest.TestCase):
    """O id do YouTube sai de qualquer forma de URL. Era o que faltava."""

    def test_as_seis_formas_de_url_dao_o_mesmo_id(self):
        formas = [
            'https://www.youtube.com/watch?v=pnVWzqttbJI',
            'https://www.youtube.com/watch?v=pnVWzqttbJI&t=42s',
            'https://www.youtube.com/watch?list=PL123&v=pnVWzqttbJI',
            'https://youtu.be/pnVWzqttbJI',
            'https://www.youtube.com/embed/pnVWzqttbJI',
            'https://www.youtube.com/shorts/pnVWzqttbJI',
            'https://www.youtube.com/live/pnVWzqttbJI',
            'https://www.youtube-nocookie.com/embed/pnVWzqttbJI',
        ]
        for forma in formas:
            with self.subTest(forma=forma):
                self.assertEqual(_ids.da_url(forma), 'pnVWzqttbJI')

    def test_id_com_hifen_na_frente_sobrevive(self):
        # `-Lo6tt-A-aQ` existe no canal. Um regex descuidado o perde.
        self.assertEqual(_ids.da_url('https://youtu.be/-Lo6tt-A-aQ'), '-Lo6tt-A-aQ')

    def test_termo_de_busca_nao_e_url(self):
        # E assim que o baixador distingue URL direta de busca.
        self.assertIsNone(_ids.da_url('historia da Coca-Cola AUVP'))
        self.assertIsNone(_ids.da_url(''))
        self.assertIsNone(_ids.da_url(None))

    def test_o_nome_do_arquivo_devolve_o_id(self):
        # Defeito 2: o outtmpl antigo nao gravava o id, e por isso a varredura
        # de disco criou 144 entradas cegas.
        nome = '2026-09-18_Como_a_BRF_voltou_a_dar_LUCRO_[pnVWzqttbJI].mp3'
        self.assertEqual(_ids.do_nome_de_arquivo(nome), 'pnVWzqttbJI')

    def test_nome_da_convencao_antiga_nao_devolve_id(self):
        nome = 'A_Disney_brasileira_que_FALIU - 04-10-2025.mp3'
        self.assertIsNone(_ids.do_nome_de_arquivo(nome))


class ATravaDeRepeticao(unittest.TestCase):
    """Defeito 1: a trava antiga comparava titulo por substring, nos dois sentidos."""

    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.cat = _catalogo.Catalogo(os.path.join(self.pasta, 'catalogo.json'))

    def tearDown(self):
        shutil.rmtree(self.pasta, ignore_errors=True)

    def test_o_mesmo_id_em_duas_grafias_de_titulo_e_um_item_so(self):
        # O caso real: o mesmo video desceu como
        # "1 COACH VS 50 POBRES PREMIUM | Raul Sena" e como
        # "1_COACH_VS_50_POBRES_PREMIUM_Raul_Sena". Nenhum titulo contem o
        # outro, entao a trava por substring nao viu. Por id, e um so.
        self.cat.anotar('BdIfc-hvb2Y', titulo='1 COACH VS 50 POBRES PREMIUM | Raul Sena',
                        arquivo='output/a.mp3')
        self.cat.anotar('BdIfc-hvb2Y', titulo='1_COACH_VS_50_POBRES_PREMIUM_Raul_Sena',
                        arquivo='output/b.mp3')
        self.assertEqual(len(self.cat.itens), 1)
        self.assertEqual(len(self.cat.itens['BdIfc-hvb2Y']['arquivos']), 2)
        self.assertTrue(self.cat.tem('BdIfc-hvb2Y'))

    def test_titulo_contido_em_outro_nao_barra_video_diferente(self):
        # O outro sentido do mesmo defeito: "Como a BRF voltou a dar LUCRO?"
        # esta contido em "Como a BRF voltou a dar LUCRO? A analise completa".
        # A trava antiga recusaria o segundo. Por id, sao dois.
        self.cat.anotar('pnVWzqttbJI', titulo='Como a BRF voltou a dar LUCRO?')
        self.assertFalse(self.cat.tem('aaaaaaaaaaa'))
        self.cat.anotar('aaaaaaaaaaa', titulo='Como a BRF voltou a dar LUCRO? A analise completa')
        self.assertEqual(len(self.cat.itens), 2)

    def test_titulo_traduzido_nao_muda_a_chave(self):
        # O YouTube devolve o titulo no idioma pedido: o mesmo video e
        # "Como a BRF voltou a dar LUCRO?" em pt e "How did BRF become
        # PROFITABLE again?" em en. Qualquer trava por titulo quebra aqui.
        self.cat.anotar('pnVWzqttbJI', titulo='Como a BRF voltou a dar LUCRO?')
        self.assertTrue(self.cat.tem('pnVWzqttbJI'))
        self.cat.anotar('pnVWzqttbJI', titulo='How did BRF become PROFITABLE again?')
        self.assertEqual(len(self.cat.itens), 1)

    def test_o_catalogo_sobrevive_a_ida_e_volta_do_disco(self):
        self.cat.anotar('pnVWzqttbJI', titulo='BRF', arquivo='output/x.mp3')
        self.cat.gravar()
        relido = _catalogo.Catalogo(self.cat.caminho)
        self.assertTrue(relido.tem('pnVWzqttbJI'))
        self.assertEqual(relido.registro('pnVWzqttbJI')['titulo'], 'BRF')

    def test_sem_id_nao_trava_download(self):
        # As 144 entradas cegas do history nao podem barrar nada: elas sao
        # memoria fraca, nao chave.
        self.cat.anotar_sem_id('Algum_Titulo_Antigo', 'output/antigo.mp3')
        self.assertEqual(len(self.cat.sem_id), 1)
        self.assertFalse(self.cat.tem('Algum_Titulo_Antigo'))
        self.assertEqual(len(self.cat.itens), 0)

    def test_anotar_sem_id_nao_duplica_o_mesmo_arquivo(self):
        self.cat.anotar_sem_id('X', 'output/antigo.mp3')
        self.cat.anotar_sem_id('X', 'output/antigo.mp3')
        self.assertEqual(len(self.cat.sem_id), 1)

    def _arquivo(self, nome):
        caminho = os.path.join(self.pasta, nome)
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, 'wb') as f:
            f.write(b'\x00' * 16)
        return caminho

    def test_duplicatas_em_disco_ignora_os_cortes(self):
        # Um `_partNNN` ao lado do inteiro nao e duplicata: e corte.
        self.cat.anotar('BdIfc-hvb2Y', arquivo=self._arquivo('v.mp3'))
        self.cat.anotar('BdIfc-hvb2Y', arquivo=self._arquivo('v_part000.mp3'))
        self.assertEqual(self.cat.duplicatas_em_disco(), {})
        self.cat.anotar('BdIfc-hvb2Y', arquivo=self._arquivo('outra_pasta/v.mp3'))
        self.assertIn('BdIfc-hvb2Y', self.cat.duplicatas_em_disco())

    def test_presentes_olha_o_disco_e_nao_a_anotacao(self):
        # O catalogo viaja no git; a midia nao. Num clone novo todo caminho
        # anotado aponta para arquivo ausente, e o clone nao pode se declarar
        # cheio por causa disso.
        existe = self._arquivo('existe.mp3')
        self.cat.anotar('BdIfc-hvb2Y', arquivo=existe)
        self.cat.anotar('BdIfc-hvb2Y', arquivo=os.path.join(self.pasta, 'sumiu.mp3'))
        self.assertEqual(len(self.cat.registro('BdIfc-hvb2Y')['arquivos']), 2)
        # `anotar` guarda com barra normal; comparar pelo caminho normalizado.
        presentes = [os.path.normcase(os.path.normpath(a))
                     for a in self.cat.presentes('BdIfc-hvb2Y')]
        self.assertEqual(presentes, [os.path.normcase(os.path.normpath(existe))])

    def test_duplicata_so_conta_arquivo_que_existe(self):
        # Dois caminhos anotados, um so em disco: nao e duplicata neste disco.
        self.cat.anotar('BdIfc-hvb2Y', arquivo=self._arquivo('aqui.mp3'))
        self.cat.anotar('BdIfc-hvb2Y', arquivo=os.path.join(self.pasta, 'noutra_maquina.mp3'))
        self.assertEqual(self.cat.duplicatas_em_disco(), {})

    def test_presentes_de_id_desconhecido_e_lista_vazia(self):
        self.assertEqual(self.cat.presentes('naoexiste00'), [])


class OPerfilEAInstrucao(unittest.TestCase):
    """Erro de digitacao em filtro de download custa horas de banda."""

    def test_campo_desconhecido_e_recusado(self):
        with self.assertRaises(_perfis.PerfilInvalido):
            _perfis.validar({'acervo': 'x', 'canal_permitido': ['AUVP']})

    def test_acervo_e_obrigatorio(self):
        with self.assertRaises(_perfis.PerfilInvalido):
            _perfis.validar({'alvos': []})

    def test_acervo_nao_pode_escapar_da_pasta(self):
        with self.assertRaises(_perfis.PerfilInvalido):
            _perfis.validar({'acervo': '../fora'})

    def test_formato_so_aceita_audio_ou_video(self):
        with self.assertRaises(_perfis.PerfilInvalido):
            _perfis.validar({'acervo': 'x', 'formato': 'mp3'})

    def test_padroes_sao_preenchidos(self):
        perfil = _perfis.validar({'acervo': 'x'})
        self.assertEqual(perfil['formato'], 'audio')
        self.assertEqual(perfil['alvos'], [])
        self.assertFalse(perfil['corte']['ativo'])

    def test_o_perfil_do_repositorio_e_valido(self):
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pasta = os.path.join(raiz, 'perfis')
        nomes = _perfis.listar(pasta)
        self.assertTrue(nomes, 'nenhum perfil em perfis/')
        for nome in nomes:
            with self.subTest(perfil=nome):
                _perfis.carregar(nome, pasta)


class ONomeDeArquivoCarregaOId(unittest.TestCase):
    def test_o_modelo_de_nome_grava_o_id(self):
        from biblioteca import baixador
        perfil = _perfis.validar({'acervo': 'teste'})
        modelo = baixador.modelo_de_nome(perfil, 'output')
        self.assertIn('[%(id)s]', modelo)
        self.assertIn(os.path.join('output', 'teste'), modelo)


class AVarredura(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.raiz = os.path.join(self.pasta, 'output')
        os.makedirs(os.path.join(self.raiz, 'acervo-novo'))
        os.makedirs(os.path.join(self.raiz, 'acervo-velho'))
        # Convencao nova: o id esta no nome.
        self._criar('acervo-novo/2026-09-18_Como_a_BRF_voltou_[pnVWzqttbJI].mp3')
        # Convencao antiga: o id so existe no history.
        self._criar('acervo-velho/A_Disney_brasileira_que_FALIU - 04-10-2025.mp3')
        # Convencao antiga e sem history: fica incerto.
        self._criar('acervo-velho/Um_arquivo_orfao - 01-01-2020.mp3')

        self.history = os.path.join(self.pasta, 'history.json')
        with open(self.history, 'w', encoding='utf-8') as f:
            json.dump({'downloaded': [
                {'title': 'A Disney brasileira que FALIU', 'id': 'DiSnEy12345',
                 'filename': 'A_Disney_brasileira_que_FALIU - 04-10-2025.mp3'},
                {'title': 'Entrada cega sem id nenhum'},
            ]}, f)
        self.cat = _catalogo.Catalogo(os.path.join(self.pasta, 'catalogo.json'))

    def _criar(self, relativo):
        caminho = os.path.join(self.raiz, relativo)
        with open(caminho, 'wb') as f:
            f.write(b'\x00' * 16)

    def tearDown(self):
        shutil.rmtree(self.pasta, ignore_errors=True)

    def test_le_o_id_do_nome_e_recupera_o_id_pelo_history(self):
        rel = varredura.indexar(self.cat, self.raiz, self.history)
        self.assertEqual(rel['por_id_no_nome'], 1)
        self.assertEqual(rel['por_history'], 1)
        self.assertEqual(rel['sem_id'], 1)
        self.assertTrue(self.cat.tem('pnVWzqttbJI'))
        self.assertTrue(self.cat.tem('DiSnEy12345'))
        self.assertEqual(self.cat.registro('pnVWzqttbJI')['acervo'], 'acervo-novo')

    def test_indexar_duas_vezes_nao_duplica_nada(self):
        primeira = varredura.indexar(self.cat, self.raiz, self.history)
        itens, sem_id = len(self.cat.itens), len(self.cat.sem_id)
        segunda = varredura.indexar(self.cat, self.raiz, self.history)
        self.assertEqual(primeira, segunda)
        self.assertEqual(len(self.cat.itens), itens)
        self.assertEqual(len(self.cat.sem_id), sem_id)
        for reg in self.cat.itens.values():
            self.assertEqual(len(reg['arquivos']), len(set(reg['arquivos'])))

    def test_acento_e_dobrado_e_nao_jogado_fora(self):
        # docs/DOC-TECNICO.md ja avisava: sem NFKD, "está" vira "est" e nunca
        # casa com o "esta" do nome de arquivo sanitizado.
        pares = [
            ('O que está acontecendo com a NOKIA?', 'O_que_esta_acontecendo_com_a_NOKIA'),
            ('A história da TWITCH', 'A_historia_da_TWITCH'),
            ('Ação e coração', 'Acao_e_coracao'),
            ('O “lixo” da PETROBRAS', 'O_lixo_da_PETROBRAS'),
        ]
        for titulo, arquivo in pares:
            with self.subTest(titulo=titulo):
                self.assertEqual(varredura.assinatura(titulo), varredura.assinatura(arquivo))

    def test_separa_id_perdido_de_arquivo_que_nunca_foi_do_youtube(self):
        # O `outtmpl` antigo terminava em ` - DD-MM-AAAA`. Quem tem a marca
        # desceu do YouTube; quem nao tem e sample ou arquivo local.
        self.assertTrue(varredura.veio_do_baixador('A_historia - 04-10-2025.mp3'))
        self.assertTrue(varredura.veio_do_baixador('A_historia - 04-10-2025_part003.mp3'))
        self.assertFalse(varredura.veio_do_baixador('sample-arrocha-db-1.mp3'))
        self.assertFalse(varredura.veio_do_baixador('pagode-baiano-exemplo.mp3'))

    def test_indexar_classifica_o_que_nao_tem_id(self):
        self._criar('acervo-velho/Veio_do_baixador - 01-01-2025.mp3')
        self._criar('acervo-velho/sample-local.mp3')
        rel = varredura.indexar(self.cat, self.raiz, self.history)
        self.assertEqual(rel['id_perdido'], 2)      # o orfao do setUp tambem tem data
        self.assertEqual(rel['nao_e_do_youtube'], 1)
        situacoes = {x['situacao'] for x in self.cat.sem_id}
        self.assertEqual(situacoes, {'id-perdido', 'nao-e-do-youtube'})

    def test_titulo_provavel_tira_data_corte_e_id(self):
        self.assertEqual(
            varredura.titulo_provavel('2026-09-18_Como_a_BRF_[pnVWzqttbJI].mp3'),
            'Como_a_BRF')
        self.assertEqual(
            varredura.titulo_provavel('A_Disney_brasileira - 04-10-2025.mp3'),
            'A_Disney_brasileira')
        self.assertEqual(
            varredura.titulo_provavel('A_Disney_brasileira - 04-10-2025_part003.mp3'),
            'A_Disney_brasileira')


class AReorganizacao(unittest.TestCase):
    """Mover e renomear, nunca apagar. O conflito para o movimento, nao o disco."""

    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.raiz = os.path.join(self.pasta, 'output')
        for sub in ('batida_1', 'batida_2'):
            os.makedirs(os.path.join(self.raiz, sub))
        self.cat = _catalogo.Catalogo(os.path.join(self.pasta, 'catalogo.json'))

    def tearDown(self):
        shutil.rmtree(self.pasta, ignore_errors=True)

    def _criar(self, relativo, bytes_=16):
        caminho = os.path.join(self.raiz, relativo)
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, 'wb') as f:
            f.write(b'\x00' * bytes_)
        return caminho

    def test_o_nome_novo_traz_data_titulo_e_id(self):
        novo = reorganizacao.nome_novo('output/Um Titulo - 09-11-2025.mp3', 'BdIfc-hvb2Y')
        self.assertEqual(novo, '2025-11-09_Um_Titulo_[BdIfc-hvb2Y].mp3')

    def test_o_corte_continua_identificavel(self):
        novo = reorganizacao.nome_novo('output/T - 09-11-2025_part003.mp3', 'BdIfc-hvb2Y')
        self.assertEqual(novo, '2025-11-09_T_part003_[BdIfc-hvb2Y].mp3')

    def test_arquivo_que_ja_esta_na_convencao_nao_se_mexe(self):
        self.assertIsNone(
            reorganizacao.nome_novo('output/2025-11-09_T_[BdIfc-hvb2Y].mp3', 'BdIfc-hvb2Y'))

    def test_juntar_duas_batidas_num_acervo_so(self):
        a = self._criar('batida_1/Video Um - 09-11-2025.mp3')
        b = self._criar('batida_2/Video Dois - 10-11-2025.mp3')
        self.cat.anotar('aaaaaaaaaaa', titulo='Video Um', arquivo=a)
        self.cat.anotar('bbbbbbbbbbb', titulo='Video Dois', arquivo=b)

        plano = reorganizacao.planejar(self.cat, self.raiz,
                                       de=['batida_1', 'batida_2'], para='raul-sena')
        self.assertEqual(len(plano['movimentos']), 2)
        self.assertEqual(plano['conflitos'], [])

        reorganizacao.aplicar(plano, self.cat, self.raiz)
        destino = os.path.join(self.raiz, 'raul-sena')
        self.assertEqual(sorted(os.listdir(destino)), [
            '2025-11-09_Video_Um_[aaaaaaaaaaa].mp3',
            '2025-11-10_Video_Dois_[bbbbbbbbbbb].mp3',
        ])
        self.assertFalse(os.path.exists(a))

    def test_o_mesmo_video_em_duas_grafias_vira_conflito_e_nada_se_perde(self):
        # O caso real do output/: duas grafias do mesmo video, com tamanhos
        # diferentes. Renomear as duas daria o mesmo nome. Ninguem sobrescreve.
        a = self._criar('batida_1/1 COACH VS 50 POBRES - 09-11-2025.mp3', 32)
        b = self._criar('batida_1/1_COACH_VS_50_POBRES - 09-11-2025.mp3', 64)
        self.cat.anotar('BdIfc-hvb2Y', titulo='1 COACH VS 50 POBRES', arquivo=a)
        self.cat.anotar('BdIfc-hvb2Y', arquivo=b)

        plano = reorganizacao.planejar(self.cat, self.raiz)
        self.assertEqual(len(plano['movimentos']), 1)
        self.assertEqual(len(plano['conflitos']), 1)

        reorganizacao.aplicar(plano, self.cat, self.raiz)
        # Os dois arquivos continuam existindo: um renomeado, outro parado.
        sobrou = sorted(os.listdir(os.path.join(self.raiz, 'batida_1')))
        self.assertEqual(len(sobrou), 2)
        self.assertEqual(sum(os.path.getsize(os.path.join(self.raiz, 'batida_1', f))
                             for f in sobrou), 96)

    def test_arquivo_fora_do_catalogo_fica_onde_esta(self):
        self._criar('batida_1/Orfao - 01-01-2020.mp3')
        plano = reorganizacao.planejar(self.cat, self.raiz)
        self.assertEqual(plano['movimentos'], [])
        self.assertEqual(len(plano['sem_id']), 1)

    def test_o_catalogo_acompanha_o_arquivo_que_se_moveu(self):
        a = self._criar('batida_1/Video Um - 09-11-2025.mp3')
        self.cat.anotar('aaaaaaaaaaa', titulo='Video Um', arquivo=a)
        plano = reorganizacao.planejar(self.cat, self.raiz, de=['batida_1'], para='novo')
        reorganizacao.aplicar(plano, self.cat, self.raiz)
        arquivos = self.cat.registro('aaaaaaaaaaa')['arquivos']
        self.assertEqual(len(arquivos), 1)
        self.assertIn('2025-11-09_Video_Um_[aaaaaaaaaaa].mp3', arquivos[0])
        self.assertEqual(self.cat.registro('aaaaaaaaaaa')['acervo'], 'novo')


if __name__ == '__main__':
    unittest.main(verbosity=2)


class OHistoryMudouDeCasa(unittest.TestCase):
    """`history.json` e fonte de migracao, nao fonte da verdade. Mora em legado/."""

    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.anterior = os.getcwd()
        os.chdir(self.pasta)
        os.makedirs('legado')

    def tearDown(self):
        os.chdir(self.anterior)
        shutil.rmtree(self.pasta, ignore_errors=True)

    def test_prefere_legado_quando_os_dois_existem(self):
        open(os.path.join('legado', 'history.json'), 'w').close()
        open('history.json', 'w').close()
        self.assertEqual(varredura.achar_history(),
                         os.path.join('legado', 'history.json'))

    def test_aceita_o_da_raiz_de_clone_antigo(self):
        open('history.json', 'w').close()
        self.assertEqual(varredura.achar_history(), 'history.json')

    def test_caminho_pedido_a_mao_vence(self):
        open(os.path.join('legado', 'history.json'), 'w').close()
        self.assertEqual(varredura.achar_history('outro.json'), 'outro.json')

    def test_sem_nenhum_devolve_o_caminho_novo(self):
        self.assertEqual(varredura.achar_history(),
                         os.path.join('legado', 'history.json'))


class AReclassificacao(unittest.TestCase):
    """`incerto` era o rotulo unico da primeira versao. Ele nao pode ficar parado."""

    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.raiz = os.path.join(self.pasta, 'output')
        os.makedirs(self.raiz)
        self.cat = _catalogo.Catalogo(os.path.join(self.pasta, 'catalogo.json'))

    def tearDown(self):
        shutil.rmtree(self.pasta, ignore_errors=True)

    def test_classifica_entrada_antiga_pelo_nome_guardado(self):
        # O caso do clone: a midia nao esta neste disco, mas o nome esta no
        # catalogo -- e a classificacao sai do nome.
        self.cat.sem_id = [
            {'titulo_arquivo': 'A', 'arquivo': 'output/A - 04-10-2025.mp3',
             'origem': 'disco', 'situacao': 'incerto'},
            {'titulo_arquivo': 'sample', 'arquivo': 'output/musicas/sample-arrocha.mp3',
             'origem': 'disco', 'situacao': 'incerto'},
        ]
        rel = varredura.indexar(self.cat, self.raiz, os.path.join(self.pasta, 'nada.json'))
        self.assertEqual(rel['reclassificados'], 2)
        self.assertEqual([x['situacao'] for x in self.cat.sem_id],
                         ['id-perdido', 'nao-e-do-youtube'])

    def test_nao_mexe_no_que_ja_esta_classificado(self):
        self.cat.sem_id = [{'titulo_arquivo': 'A', 'arquivo': 'output/A - 04-10-2025.mp3',
                            'origem': 'disco', 'situacao': 'nao-e-do-youtube'}]
        rel = varredura.indexar(self.cat, self.raiz, os.path.join(self.pasta, 'nada.json'))
        self.assertEqual(rel['reclassificados'], 0)
        self.assertEqual(self.cat.sem_id[0]['situacao'], 'nao-e-do-youtube')
