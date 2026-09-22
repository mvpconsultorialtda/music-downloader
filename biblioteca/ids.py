# -*- coding: utf-8 -*-
"""O id do YouTube: extrair de qualquer forma de URL, e reconhecer no nome do arquivo.

O id e a unica chave estavel. Titulo muda (o YouTube traduz por idioma do
pedido), o nome do arquivo e sanitizado, e a URL tem pelo menos cinco formas.
"""
import re

# 11 caracteres do alfabeto base64url. E o formato do id de video do YouTube.
ID = r'[0-9A-Za-z_-]{11}'

_DAS_URLS = [
    re.compile(r'(?:youtube\.com|youtube-nocookie\.com)/watch\?(?:[^&]*&)*v=(' + ID + r')'),
    re.compile(r'youtu\.be/(' + ID + r')'),
    re.compile(r'(?:youtube\.com|youtube-nocookie\.com)/embed/(' + ID + r')'),
    re.compile(r'(?:youtube\.com|youtube-nocookie\.com)/shorts/(' + ID + r')'),
    re.compile(r'(?:youtube\.com|youtube-nocookie\.com)/live/(' + ID + r')'),
    re.compile(r'(?:youtube\.com|youtube-nocookie\.com)/v/(' + ID + r')'),
]

# O nome de arquivo que esta camada escreve termina em _[<id>].<ext>.
_DO_NOME = re.compile(r'\[(' + ID + r')\]')


def da_url(texto):
    """Devolve o id do video contido na URL, ou None se nao houver.

    Aceita as formas watch?v=, youtu.be/, /embed/, /shorts/, /live/ e /v/,
    com ou sem parametros depois. Um texto que nao e URL devolve None -- e
    assim que o baixador distingue URL direta de termo de busca.
    """
    if not texto:
        return None
    for padrao in _DAS_URLS:
        achado = padrao.search(texto)
        if achado:
            return achado.group(1)
    # Um id solto, digitado sem URL nenhuma.
    if re.fullmatch(ID, texto.strip()):
        return texto.strip()
    return None


def do_nome_de_arquivo(nome):
    """Devolve o id gravado entre colchetes no nome do arquivo, ou None.

    E o que torna a varredura de disco capaz de recuperar o id -- coisa que a
    convencao antiga nao permitia, porque o id nunca era escrito.
    """
    if not nome:
        return None
    achado = _DO_NOME.search(nome)
    return achado.group(1) if achado else None


def url_canonica(video_id):
    """A forma unica de escrever a URL de um id, para o catalogo nao ter cinco."""
    return f'https://www.youtube.com/watch?v={video_id}'
