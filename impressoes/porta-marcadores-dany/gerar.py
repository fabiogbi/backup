#!/usr/bin/env python3
"""Porta-marcadores de quadro branco "Dany Nogueira" (6 e 4 furos) para a Creality K2 Pro.

Gera, para cada versão: .3mf (3 cores), .stl (peça única) e uma cena de prévia.
Também gera um anel de teste para conferir o diâmetro do furo com os seus marcadores.
Requer: pip install fonttools
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", ".claude", "skills", "3d", "scripts"))
from modelo3d import (check, circle, ellipse_ring, emboss, export_3mf, export_stl, extrude,  # noqa: E402
                      heart, preview, rounded_rect, shift_shapes, text_shapes, union)

FONTE = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
NOME = "DANY NOGUEIRA"

# Medidas (mm). Pilot V-Board Master: corpo ~16 mm, tampa um pouco maior -> furo de 19 mm.
# Imprima primeiro o anel de teste e ajuste DIAMETRO_FURO se ficar justo/folgado.
DIAMETRO_FURO = 19.0
PASSO = 23.0          # distância entre centros dos furos
PROFUNDIDADE = 26.0   # largura da barra (Y)
ALTURA = 24.0         # altura da barra (Z)
FUNDO = 3.0           # fundo fechado dos furos
RAIO_CANTO = 9.0
RELEVO = 0.8

COR_CORPO, COR_NOME, COR_CORACAO = "#F4A3B9", "#9C4A5A", "#E25D7E"


def barra(n):
    comp = n * PASSO + 6.0
    contorno = rounded_rect(comp, PROFUNDIDADE, RAIO_CANTO, seg=12)
    furos = [[(x + (i - (n - 1) / 2) * PASSO, y) for x, y in circle(DIAMETRO_FURO / 2, 64)] for i in range(n)]
    base = extrude(contorno, FUNDO)
    topo = extrude(contorno, ALTURA - FUNDO, z0=FUNDO, holes=furos)
    return union(base, topo), comp


def na_frente(s, t, h):
    """Face frontal (y = -PROFUNDIDADE/2): s -> X, t -> Z, relevo -> -Y."""
    return [s, -PROFUNDIDADE / 2 - h, t]


def logo(comp):
    """Átomo + nome + coração, centralizados na parte reta da frente.
    Usa uma linha quando cabe; senão, DANY sobre NOGUEIRA (como no logo original)."""
    util = comp - 2 * RAIO_CANTO - 4          # trecho reto disponível
    tc = ALTURA / 2 + 0.6                     # um pouco acima do meio (centro óptico)
    primeiro, ultimo = NOME.split(" ", 1)
    for linhas in (1, 2):
        cap = 6.0 if linhas == 1 else 5.6
        while True:
            trk = cap * 0.28
            if linhas == 1:
                l_baixo, w = text_shapes(NOME, FONTE, cap, trk)
                l_cima, w_cima = [], 0
                atomo_r = cap * 1.25
            else:
                l_cima, w_cima = text_shapes(primeiro, FONTE, cap, trk)
                l_baixo, w = text_shapes(ultimo, FONTE, cap, trk)
                atomo_r = cap * 1.7
            cor = cap * 0.95
            total = 2 * atomo_r + 3.5 + w + 2.0 + cor
            if total <= util or cap <= 5.0:
                break
            cap -= 0.2
        if total <= util:
            break
    s0 = -total / 2
    xt = s0 + 2 * atomo_r + 3.5
    entre = cap * 1.7 if linhas == 2 else 0      # distância entre as linhas de base
    base_baixo = tc - (cap + entre) / 2
    nome = shift_shapes(l_baixo, xt, base_baixo) + shift_shapes(l_cima, xt + (w - w_cima) / 2, base_baixo + entre)
    aneis = [ellipse_ring(atomo_r - 0.7, atomo_r * 0.36, 1.2, a) for a in (0, 60, 120)]
    aneis = shift_shapes(aneis, s0 + atomo_r, tc)
    coracoes = shift_shapes([(heart(atomo_r * 0.5), [])], s0 + atomo_r, tc - 0.2) + \
        shift_shapes([(heart(cor), [])], xt + w + 2.0 + cor / 2, base_baixo + cap * 0.48)
    return (emboss(nome + aneis, RELEVO, na_frente), emboss(coracoes, RELEVO, na_frente), cap, total)


def anel_teste():
    """Três anéis baixos (18,5 / 19 / 19,5 mm) para testar o encaixe do marcador antes da peça grande."""
    pecas = []
    for i, d in enumerate((DIAMETRO_FURO - 0.5, DIAMETRO_FURO, DIAMETRO_FURO + 0.5)):
        x = (i - 1) * 30
        anel = extrude([(px + x, py) for px, py in circle(d / 2 + 2.4, 64)], 6,
                       holes=[[(px + x, py) for px, py in circle(d / 2, 64)]])
        marca = extrude([(px + x, py + d / 2 + 2.6) for px, py in circle(1.0 + i * 0.6, 16)], 6)  # 1, 2 ou 3 tamanhos
        pecas += [anel, marca]
    return union(*pecas)


def main():
    for n in (6, 4):
        corpo, comp = barra(n)
        nome, coracoes, cap, total = logo(comp)
        partes = [("corpo", corpo, COR_CORPO), ("nome", nome, COR_NOME), ("coracoes", coracoes, COR_CORACAO)]
        base = f"porta-marcadores-dany-{n}-furos"
        print(f"\n== {n} furos ==  letras de {cap:.1f} mm, logo com {total:.0f} mm")
        check(partes)
        export_3mf(partes, os.path.join(HERE, base + ".3mf"))
        export_stl(union(corpo, nome, coracoes), os.path.join(HERE, base + ".stl"), base)
        cena = os.path.join(HERE, base + ".json")
        preview(partes, cena)
        s = json.load(open(cena))
        s["background"] = "#fdf2f5"
        s["objects"][0]["color"] = "#ece3e6"
        s["camera"] = {"position": [comp * 0.15, comp * 0.5, comp * 1.25], "target": [0, 8, 0], "fov": 35}
        json.dump(s, open(cena, "w"))
    export_stl(anel_teste(), os.path.join(HERE, "teste-encaixe-marcador.stl"), "teste")
    print("\nteste-encaixe-marcador.stl gerado")


if __name__ == "__main__":
    main()
