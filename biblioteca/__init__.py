"""Biblioteca do YouTube — a camada de organizacao em cima do baixador.

O baixador (yt-dlp + PO Token) nao se refaz: ele funciona. O que esta aqui e a
biblioteca: um catalogo chaveado pelo id do YouTube, um nome de arquivo que
carrega esse id, e uma saida organizada por acervo em vez de por batida.

Regra unica desta camada: **o id do YouTube e a chave**. Titulo nao e chave --
o YouTube traduz o titulo conforme o idioma de quem pede, e o mesmo video ja
desceu duas vezes nesta biblioteca por causa disso.
"""

__all__ = ['ids', 'catalogo', 'perfis', 'baixador', 'varredura']
