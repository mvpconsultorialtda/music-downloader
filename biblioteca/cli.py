# -*- coding: utf-8 -*-
"""A porta de entrada: `python -m biblioteca <comando>`.

    indexar                     reconstroi o catalogo a partir do disco e do history
    conferir                    o estado da biblioteca, sem escrever nada
    duplicatas                  o mesmo id em mais de um arquivo -- relatorio, nao faxina
    reorganizar                 poe o id no nome e junta as pastas que sao o mesmo acervo
    perfis                      lista os perfis disponiveis
    baixar <perfil>             roda os alvos do perfil
    baixar <perfil> --alvo URL  roda so esse alvo, com os filtros do perfil

`--so-conferir` vale para `indexar`, `baixar` e `reorganizar`: diz o que faria e
nao faz.
"""
import argparse
import os
import sys

from . import (baixador, catalogo as _catalogo, ids as _ids, perfis as _perfis,
               reorganizacao, varredura)


def _saida_utf8():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass


def cmd_indexar(args):
    cat = _catalogo.Catalogo(args.catalogo)
    antes = len(cat.itens)
    if args.so_conferir:
        espelho = _catalogo.Catalogo(args.catalogo)
        espelho.gravar = lambda: None  # so-conferir nao escreve
        relatorio = varredura.indexar(espelho, args.raiz, args.history)
        cat = espelho
    else:
        relatorio = varredura.indexar(cat, args.raiz, args.history)

    print(f'history: {relatorio["history_com_id"]} com id, '
          f'{relatorio["history_sem_id"]} sem id')
    print(f'disco: {relatorio["arquivos_vistos"]} arquivos de midia')
    print(f'  id lido do proprio nome ........ {relatorio["por_id_no_nome"]}')
    print(f'  id recuperado pelo history ..... {relatorio["por_history"]}')
    print(f'  sem id, marcados incertos ...... {relatorio["sem_id"]}')
    print(f'catalogo: {antes} -> {len(cat.itens)} itens'
          + ('  (so-conferir: nada gravado)' if args.so_conferir else ''))
    return 0


def cmd_conferir(args):
    cat = _catalogo.Catalogo(args.catalogo)
    if not cat.itens and not cat.sem_id:
        print(f'{args.catalogo} esta vazio ou nao existe. Rode `indexar` primeiro.')
        return 1

    por_acervo = {}
    em_disco = 0
    for reg in cat.itens.values():
        por_acervo.setdefault(reg.get('acervo') or '(sem acervo)', []).append(reg)
        if reg.get('arquivos'):
            em_disco += 1

    print(f'catalogo: {len(cat.itens)} ids  |  {em_disco} com arquivo em disco  '
          f'|  {len(cat.itens) - em_disco} so na memoria')
    print(f'incertos (sem id, nunca terao): {len(cat.sem_id)}')
    print()
    print(f'{"acervo":<32} {"ids":>5} {"com arquivo":>12}')
    for acervo in sorted(por_acervo):
        regs = por_acervo[acervo]
        print(f'{acervo:<32} {len(regs):>5} {sum(1 for r in regs if r.get("arquivos")):>12}')

    dups = cat.duplicatas_em_disco()
    if dups:
        print()
        print(f'ATENCAO: {len(dups)} ids com mais de um arquivo inteiro em disco. '
              f'Rode `duplicatas` para ver quais.')
    return 0


def cmd_duplicatas(args):
    cat = _catalogo.Catalogo(args.catalogo)
    dups = cat.duplicatas_em_disco()
    if not dups:
        print('nenhum id com mais de um arquivo inteiro em disco.')
        return 0

    desperdicio = 0
    print(f'{len(dups)} ids aparecem em mais de um arquivo:\n')
    for video_id, arquivos in sorted(dups.items()):
        reg = cat.registro(video_id)
        print(f'[{video_id}] {reg.get("titulo") or "(sem titulo)"}')
        tamanhos = []
        for arquivo in arquivos:
            try:
                tamanho = os.path.getsize(arquivo)
            except OSError:
                tamanho = 0
            tamanhos.append(tamanho)
            print(f'    {tamanho/1e6:>8.1f} MB  {arquivo}')
        if tamanhos:
            desperdicio += sum(tamanhos) - max(tamanhos)
        print()
    print(f'sobra, se ficasse so o maior de cada: {desperdicio/1e6:.0f} MB')
    print('Nada foi apagado. Qual versao fica e decisao do operador.')
    return 0


def cmd_reorganizar(args):
    cat = _catalogo.Catalogo(args.catalogo)
    if not cat.itens:
        print(f'{args.catalogo} esta vazio. Rode `indexar` primeiro.')
        return 1

    plano = reorganizacao.planejar(cat, args.raiz, de=args.de, para=args.para)
    movimentos, conflitos, sem_id = plano['movimentos'], plano['conflitos'], plano['sem_id']

    print(f'{len(movimentos)} arquivos a mover/renomear  |  '
          f'{len(conflitos)} conflitos  |  {len(sem_id)} sem id no catalogo')
    print()
    for m in movimentos[:args.mostrar]:
        print(f'  {m["de"]}')
        print(f'     -> {m["para"]}')
    if len(movimentos) > args.mostrar:
        print(f'  ... e mais {len(movimentos) - args.mostrar} (use --mostrar N)')

    if conflitos:
        print(f'\nCONFLITOS -- dois arquivos disputam o mesmo destino. '
              f'Nenhum deles se move; qual versao fica e decisao do operador:')
        for c in conflitos[:args.mostrar]:
            print(f'  [{c["id"]}] {c["de"]}')
            print(f'     x  {c["para"]}')
        if len(conflitos) > args.mostrar:
            print(f'  ... e mais {len(conflitos) - args.mostrar}')

    if sem_id:
        print(f'\n{len(sem_id)} arquivos sem id no catalogo ficam onde estao '
              f'(nao da para nomea-los pela convencao nova).')

    if args.so_conferir or not movimentos:
        print('\n(so-conferir: nada foi movido)' if args.so_conferir else '')
        return 0

    print(f'\nmovendo {len(movimentos)} arquivos...')
    desfecho = reorganizacao.aplicar(plano, cat, args.raiz)
    print(f'movidos: {len(desfecho["feitos"])}  |  falhas: {len(desfecho["falhas"])}')
    for f in desfecho['falhas'][:args.mostrar]:
        print(f'  ERRO {f["de"]} -- {f["erro"]}')
    return 1 if desfecho['falhas'] else 0


def cmd_perfis(args):
    nomes = _perfis.listar(args.perfis)
    if not nomes:
        print(f'nenhum perfil em {args.perfis}/')
        return 1
    for nome in nomes:
        try:
            perfil = _perfis.carregar(nome, args.perfis)
        except _perfis.PerfilInvalido as e:
            print(f'{nome:<28} INVALIDO: {e}')
            continue
        print(f'{nome:<28} acervo={perfil["acervo"]:<28} '
              f'{perfil["formato"]:<6} {len(perfil["alvos"])} alvos')
    return 0


def cmd_baixar(args):
    try:
        perfil = _perfis.carregar(args.perfil, args.perfis)
    except _perfis.PerfilInvalido as e:
        print(f'ERRO: {e}')
        return 1

    if args.alvo:
        perfil = dict(perfil, alvos=list(args.alvo))

    cat = _catalogo.Catalogo(args.catalogo)

    if args.so_conferir:
        print(f'perfil "{perfil["acervo"]}" -> {baixador.pasta_do_acervo(perfil, args.raiz)}')
        print(f'modelo de nome: {os.path.basename(baixador.modelo_de_nome(perfil, args.raiz))}')
        print(f'canais: {perfil["canais_permitidos"] or "(qualquer)"}  '
              f'formato: {perfil["formato"]}')
        print()
        for alvo in perfil['alvos']:
            video_id = _ids.da_url(alvo)
            if video_id and cat.tem(video_id):
                print(f'  PULA     [{video_id}] ja esta no catalogo -- {alvo}')
            elif video_id:
                print(f'  BAIXARIA [{video_id}] {alvo}')
            else:
                print(f'  BUSCARIA "{alvo}" (ate {perfil["resultados_por_busca"]} resultados)')
        print('\n(so-conferir: nada foi baixado nem gravado)')
        return 0

    desfechos = baixador.baixar_perfil(perfil, cat, args.raiz,
                                       paralelos=args.paralelos)
    print('\n=== desfecho ===')
    codigo = 0
    for d in desfechos:
        if d['estado'] == 'baixado':
            for reg in d.get('registros', []):
                arquivo = (reg.get('arquivos') or ['(?)'])[-1]
                print(f'  BAIXADO  [{reg["id"]}] {reg.get("titulo")}')
                print(f'           {arquivo}')
            if not d.get('registros'):
                print(f'  BAIXADO  {d["alvo"]} -- {d.get("aviso", "")}')
        elif d['estado'] == 'ja-temos':
            print(f'  JA TEMOS [{d["id"]}] {d.get("titulo")}')
        elif d['estado'] == 'recusado':
            print(f'  RECUSADO {d["alvo"]} -- {d.get("porque")}')
        else:
            codigo = 1
            print(f'  ERRO     {d["alvo"]} -- {d.get("erro")}')
    return codigo


def montar_parser():
    p = argparse.ArgumentParser(
        prog='python -m biblioteca',
        description='Biblioteca do YouTube: baixa por perfil, cataloga por id do video.')
    p.add_argument('--catalogo', default=_catalogo.ARQUIVO_PADRAO)
    p.add_argument('--raiz', default='output', help='a pasta onde moram os acervos')
    p.add_argument('--perfis', default=_perfis.PASTA_PADRAO)

    sub = p.add_subparsers(dest='comando', required=True)

    s = sub.add_parser('indexar', help='reconstroi o catalogo a partir do disco e do history')
    s.add_argument('--history', default='history.json')
    s.add_argument('--so-conferir', action='store_true')
    s.set_defaults(func=cmd_indexar)

    s = sub.add_parser('conferir', help='o estado da biblioteca, sem escrever nada')
    s.set_defaults(func=cmd_conferir)

    s = sub.add_parser('duplicatas', help='o mesmo id em mais de um arquivo')
    s.set_defaults(func=cmd_duplicatas)

    s = sub.add_parser('reorganizar',
                       help='leva o acervo antigo para a convencao nova, movendo (nunca apagando)')
    s.add_argument('--de', action='append',
                   help='pasta de origem sob --raiz, repetivel; sem isto, todas')
    s.add_argument('--para', help='acervo de destino; sem isto, cada arquivo fica no seu')
    s.add_argument('--mostrar', type=int, default=20, help='quantas linhas listar')
    s.add_argument('--so-conferir', action='store_true')
    s.set_defaults(func=cmd_reorganizar)

    s = sub.add_parser('perfis', help='lista os perfis disponiveis')
    s.set_defaults(func=cmd_perfis)

    s = sub.add_parser('baixar', help='roda os alvos de um perfil')
    s.add_argument('perfil')
    s.add_argument('--alvo', action='append',
                   help='usa so este alvo (URL ou termo), repetivel')
    s.add_argument('--paralelos', type=int, default=1)
    s.add_argument('--so-conferir', action='store_true')
    s.set_defaults(func=cmd_baixar)

    return p


def main(argv=None):
    _saida_utf8()
    args = montar_parser().parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
