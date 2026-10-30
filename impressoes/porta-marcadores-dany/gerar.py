#!/usr/bin/env python3
"""Porta-marcadores Pilot V-Board Master "Dany Nogueira" (6 e 4 furos) para a Creality K2 Pro.

O nome e os símbolos ficam em BAIXO RELEVO (rebaixo) na frente da peça e são impressos à parte,
mais grossos, para serem colados no rebaixo (encaixe tipo marchetaria).

Gera para cada versão:
  porta-marcadores-dany-N-furos.stl/.3mf   corpo rosa com o rebaixo
  pecas-nome-N-furos.3mf                   nome/átomo (vinho) + corações (rosa forte), deitados na mesa
  pecas-nome-N-furos-{nome,coracoes}.stl   as mesmas peças separadas por cor
e o anel teste-encaixe-marcador.stl. Requer: pip install fonttools shapely
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", ".claude", "skills", "3d", "scripts"))
from shapely.geometry import Point, Polygon, box  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from modelo3d import (check, circle, ellipse_ring, export_3mf, export_stl, extrude, extrude_geom,  # noqa: E402
                      heart, preview, rounded_rect, shift_shapes, text_shapes, to_shapely, union)

FONTE = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
NOME = "DANY NOGUEIRA"

# Medidas (mm). Pilot V-Board Master (ficha técnica Pilot Brasil): corpo 22,6 mm, tampa 20,5 mm.
DIAMETRO_FURO = 23.4  # corpo + 0,8 mm de folga
PASSO = 27.0          # distância entre centros dos furos
PROFUNDIDADE = 30.0   # largura da barra (Y)
ALTURA = 28.0         # altura da barra (Z)
FUNDO = 3.0           # fundo fechado dos furos
RAIO_CANTO = 12.0

# Baixo relevo + peças coladas
REBAIXO = 1.5         # profundidade do rebaixo na frente
ESPESSURA_PECA = 2.0  # espessura das letras/símbolos (fica 0,5 mm saltado da frente)
ENGROSSAR = 0.25      # engrossa o traço das letras/símbolos em cada lado (traço fica ~0,5 mm mais grosso)
FOLGA = 0.15          # folga de encaixe + cola em cada lado do rebaixo

COR_CORPO, COR_NOME, COR_CORACAO = "#F4A3B9", "#9C4A5A", "#E25D7E"


def logo_2d(comp):
    """Formas 2D (s = X, t = Z) do átomo + nome e dos corações, já engrossadas."""
    util = comp - 2 * RAIO_CANTO - 6
    tc = ALTURA / 2 + 0.6
    primeiro, ultimo = NOME.split(" ", 1)
    for linhas in (1, 2):
        cap = 7.0 if linhas == 1 else 6.0
        while True:
            trk = cap * 0.3
            if linhas == 1:
                l_baixo, w = text_shapes(NOME, FONTE, cap, trk)
                l_cima, w_cima = [], 0
                atomo_r = cap * 1.25
            else:
                l_cima, w_cima = text_shapes(primeiro, FONTE, cap, trk)
                l_baixo, w = text_shapes(ultimo, FONTE, cap, trk)
                atomo_r = cap * 1.7
            cor = cap * 1.0
            total = 2 * atomo_r + 4 + w + 2.5 + cor
            if total <= util or cap <= 5.0:
                break
            cap -= 0.2
        if total <= util:
            break
    s0 = -total / 2
    xt = s0 + 2 * atomo_r + 4
    entre = cap * 1.7 if linhas == 2 else 0
    base_baixo = tc - (cap + entre) / 2
    nome = shift_shapes(l_baixo, xt, base_baixo) + shift_shapes(l_cima, xt + (w - w_cima) / 2, base_baixo + entre)
    aneis = shift_shapes([ellipse_ring(atomo_r - 0.8, atomo_r * 0.38, 1.3, a) for a in (0, 60, 120)], s0 + atomo_r, tc)
    g_nome = to_shapely(nome + aneis).buffer(ENGROSSAR, join_style="round")
    # coração do centro do átomo: o maior que não encosta nos anéis
    tam = atomo_r * 0.55
    while True:
        g_c1 = to_shapely(shift_shapes([(heart(tam), [])], s0 + atomo_r, tc - 0.2)).buffer(ENGROSSAR)
        if g_c1.distance(g_nome) >= 2 * FOLGA + 0.3 or tam < 2.5:
            break
        tam -= 0.2
    g_c2 = to_shapely(shift_shapes([(heart(cor), [])], xt + w + 2.5 + cor / 2, base_baixo + cap * 0.48)).buffer(ENGROSSAR)
    g_cor = unary_union([g_c1, g_c2]).difference(g_nome.buffer(2 * FOLGA))
    return g_nome, g_cor, cap, total


def frente(s, t, h):
    """Plano da frente: s -> X, t -> Z, h -> para fora (a partir do fundo do rebaixo)."""
    return [s, -PROFUNDIDADE / 2 + REBAIXO - h, t]


def peca(n):
    comp = n * PASSO + 6.0
    reto = comp / 2 - RAIO_CANTO                      # trecho reto da frente: -reto .. +reto
    contorno = Polygon(rounded_rect(comp, PROFUNDIDADE, RAIO_CANTO, seg=16))
    faixa = box(-reto, -PROFUNDIDADE / 2, reto, -PROFUNDIDADE / 2 + REBAIXO)  # placa frontal, feita à parte
    furos = unary_union([Point((i - (n - 1) / 2) * PASSO, 0).buffer(DIAMETRO_FURO / 2, 32) for i in range(n)])
    nucleo = contorno.difference(faixa)
    corpo = union(extrude_geom(nucleo, FUNDO), extrude_geom(nucleo.difference(furos), ALTURA - FUNDO, FUNDO))

    g_nome, g_cor, cap, total = logo_2d(comp)
    rebaixo = unary_union([g_nome, g_cor]).buffer(FOLGA, join_style="round")
    placa = box(-reto, 0, reto, ALTURA).difference(rebaixo)       # placa frontal com o rebaixo vazado
    corpo = union(corpo, extrude_geom(placa, REBAIXO, to_world=frente))

    # peças montadas (para a prévia) e peças deitadas para imprimir
    montado_nome = extrude_geom(g_nome, ESPESSURA_PECA, to_world=frente)
    montado_cor = extrude_geom(g_cor, ESPESSURA_PECA, to_world=frente)
    deitado_nome = extrude_geom(g_nome, ESPESSURA_PECA).moved(0, -ALTURA / 2, 0)
    deitado_cor = extrude_geom(g_cor, ESPESSURA_PECA).moved(0, -ALTURA / 2, 0)
    return comp, corpo, (montado_nome, montado_cor), (deitado_nome, deitado_cor), cap, total


def anel_teste():
    pecas = []
    for i, d in enumerate((DIAMETRO_FURO - 0.4, DIAMETRO_FURO, DIAMETRO_FURO + 0.4)):
        x = (i - 1) * 34
        pecas.append(extrude([(px + x, py) for px, py in circle(d / 2 + 2.4, 64)], 6,
                             holes=[[(px + x, py) for px, py in circle(d / 2, 64)]]))
        pecas.append(extrude([(px + x, py + d / 2 + 2.6) for px, py in circle(1.0 + i * 0.6, 16)], 6))
    return union(*pecas)


def main():
    import json
    for n in (6, 4):
        comp, corpo, (mn, mc), (dn, dc), cap, total = peca(n)
        base = f"porta-marcadores-dany-{n}-furos"
        print(f"\n== {n} furos ==  letras de {cap:.1f} mm, logo com {total:.0f} mm")
        check([("corpo", corpo, COR_CORPO)])
        export_stl(corpo, os.path.join(HERE, base + ".stl"), base)
        export_3mf([("corpo", corpo, COR_CORPO)], os.path.join(HERE, base + ".3mf"))
        pecas = [("nome", dn, COR_NOME), ("coracoes", dc, COR_CORACAO)]
        check(pecas)
        export_3mf(pecas, os.path.join(HERE, f"pecas-nome-{n}-furos.3mf"))
        export_stl(dn, os.path.join(HERE, f"pecas-nome-{n}-furos-nome.stl"), "nome")
        export_stl(dc, os.path.join(HERE, f"pecas-nome-{n}-furos-coracoes.stl"), "coracoes")
        # cenas de prévia: montado e só o corpo (rebaixo vazio)
        for nome_cena, partes in (("montado", [("corpo", corpo, COR_CORPO), ("nome", mn, COR_NOME),
                                               ("coracoes", mc, COR_CORACAO)]),
                                  ("rebaixo", [("corpo", corpo, COR_CORPO)])):
            cena = os.path.join(HERE, f"previa-{n}-furos-{nome_cena}.json")
            preview(partes, cena)
            s = json.load(open(cena))
            s["background"] = "#fdf2f5"
            s["objects"][0]["color"] = "#ece3e6"
            s["camera"] = {"position": [comp * 0.15, comp * 0.42, comp * 1.0], "target": [0, 10, 0], "fov": 35}
            json.dump(s, open(cena, "w"))
    export_stl(anel_teste(), os.path.join(HERE, "teste-encaixe-marcador.stl"), "teste")


if __name__ == "__main__":
    main()
