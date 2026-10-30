#!/usr/bin/env python3
"""Suporte de celular "Dany Nogueira" para a Creality K2 Pro.

Gera: suporte-dany-nogueira.3mf (3 partes/cores), suporte-dany-nogueira.stl (peça única)
e previa.json (cena para o render3d.py). Requer fontTools e a fonte Inter.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", ".claude", "skills", "3d", "scripts"))
from modelo3d import Mesh, check, circle, export_3mf, export_stl, extrude, heart, preview, union  # noqa: E402

from fontTools.pens.basePen import BasePen  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402

FONTE = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
LARGURA = 110.0      # largura do suporte (X), mm
PE = 6.0             # espessura da base
RELEVO = 1.0         # altura do relevo do logo
COR_CORPO, COR_NOME, COR_CORACAO = "#F4A3B9", "#9C4A5A", "#E25D7E"

# ---------------- perfil lateral (plano Y-Z, frente = -Y) ----------------
ANG = math.radians(68)                       # inclinação do encosto
d = (math.cos(ANG), math.sin(ANG))           # direção do encosto (para cima/trás)
nb = (math.sin(ANG), -math.cos(ANG))         # normal para trás do encosto
ESP = 6.0                                    # espessura do encosto
F0 = (-14.0, PE)                             # pé da face frontal do encosto
L = 86.0
FT = (F0[0] + d[0] * L, F0[1] + d[1] * L)    # topo frontal
BT = (FT[0] + nb[0] * ESP, FT[1] + nb[1] * ESP)  # topo traseiro


def back_at(z):   # ponto da face traseira do encosto na altura z
    t = (BT[1] - z) / d[1]
    return (BT[0] - d[0] * t, z)


def front_at(z):
    t = (z - F0[1]) / d[1]
    return (F0[0] + d[0] * t, z)


PLACA0, PLACA1 = (-72.0, 4.0), (-30.0, 20.0)   # face inclinada da placa (frente)
LABIO = -26.0                                  # parede que segura o celular
FIM = 48.0                                     # fim da base (trás)
B55 = back_at(55)                              # onde o braço traseiro encontra o encosto


def perfil_lateral():
    outer = [(-72, 0), (FIM, 0), (FIM, PE), B55, BT, FT, F0, (LABIO, PE), (LABIO, PLACA1[1]),
             PLACA1, PLACA0]
    # vão triangular entre encosto, braço e base (economiza material)
    bx, by = B55[0] - FIM, B55[1] - PE
    bl = math.hypot(bx, by)
    off = (-by / bl * 6, bx / bl * 6)                       # deslocamento para dentro do braço
    off = off if off[0] < 0 else (-off[0], -off[1])
    p0 = (FIM + off[0], PE + off[1])
    u = (bx / bl, by / bl)
    # interseção da linha interna do braço com z = PE + 2
    z0 = PE + 2
    t0 = (z0 - p0[1]) / u[1]
    h_dir = (p0[0] + u[0] * t0, z0)
    # interseção da linha interna do braço com a face traseira do encosto (recuada 0,5 mm)
    best, bz = None, z0
    for i in range(2000):
        z = z0 + i * 0.05
        t = (z - p0[1]) / u[1]
        xb = p0[0] + u[0] * t
        xe = back_at(z)[0] + 0.5
        if xb <= xe:
            best, bz = (xe, z), z
            break
    furo = [(back_at(z0)[0] + 0.5, z0), h_dir, best]
    return outer, furo


def perfil_central():
    """Faixa central sem a parte de baixo do encosto: passagem para o cabo."""
    frente = [(-72, 0), (FIM, 0), (FIM, PE), (LABIO, PE), (LABIO, PLACA1[1]), PLACA1, PLACA0]
    corte = 28.0
    topo = [front_at(corte), FT, BT, back_at(corte)]
    return frente, topo


def extrude_x(poly, x0, x1, holes=None):
    """Extruda um perfil (y, z) ao longo de X."""
    m = extrude(poly, x1 - x0, holes=holes)
    return Mesh([[p[2] + x0, p[0], p[1]] for p in m.v], m.f)  # permutação cíclica: mantém orientação

# ---------------- logo na face inclinada ----------------

class _Pen(BasePen):
    def __init__(self, glyphset, steps=8):
        super().__init__(glyphset)
        self.contours, self.cur, self.steps = [], [], steps

    def _moveTo(self, p):
        self.cur = [p]

    def _lineTo(self, p):
        self.cur.append(p)

    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        for i in range(1, self.steps + 1):
            t = i / self.steps
            a = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
            self.cur.append((a[0] * p0[0] + a[1] * p1[0] + a[2] * p2[0] + a[3] * p3[0],
                             a[0] * p0[1] + a[1] * p1[1] + a[2] * p2[1] + a[3] * p3[1]))

    def _closePath(self):
        if len(self.cur) > 2:
            if self.cur[0] == self.cur[-1]:
                self.cur.pop()
            self.contours.append(self.cur)
        self.cur = []

    _endPath = _closePath


def _area(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2


def _inside(pt, poly):
    x, y, c = pt[0], pt[1], False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def texto(s, cap, tracking):
    """Retorna [(contorno, [furos])] em mm, linha de base em y=0, começando em x=0, e a largura."""
    font = TTFont(FONTE)
    gs, cmap = font.getGlyphSet(), font.getBestCmap()
    k = cap / font["OS/2"].sCapHeight
    formas, x = [], 0.0
    for ch in s:
        g = cmap[ord(ch)]
        pen = _Pen(gs)
        gs[g].draw(pen)
        cs = [[(x + px * k, py * k) for px, py in c] for c in pen.contours]
        for c in cs:
            depth = sum(_inside(c[0], o) for o in cs if o is not c)
            if depth % 2 == 0:
                furos = [h for h in cs if h is not c and _inside(h[0], c) and abs(_area(h)) < abs(_area(c))]
                formas.append((c, furos))
        x += gs[g].width * k + tracking
    return formas, x - tracking


def elipse_anel(rx, ry, w, ang, seg=72):
    a = math.radians(ang)
    def el(ex, ey):
        return [(ex * math.cos(2 * math.pi * i / seg) * math.cos(a) - ey * math.sin(2 * math.pi * i / seg) * math.sin(a),
                 ex * math.cos(2 * math.pi * i / seg) * math.sin(a) + ey * math.sin(2 * math.pi * i / seg) * math.cos(a))
                for i in range(seg)]
    return el(rx + w / 2, ry + w / 2), [el(rx - w / 2, ry - w / 2)]


def na_placa(mesh2d_list, s_off, t_off):
    """Extruda formas 2D (s=X, t=ao longo da placa) e posiciona sobre a face inclinada."""
    dy, dz = PLACA1[0] - PLACA0[0], PLACA1[1] - PLACA0[1]
    ln = math.hypot(dy, dz)
    dy, dz = dy / ln, dz / ln
    ny, nz = -dz, dy                               # normal para fora (frente/cima)
    out = Mesh()
    for poly, holes in mesh2d_list:
        m = extrude([(p[0] + s_off, p[1] + t_off) for p in poly], RELEVO + 0.2, z0=-0.2,
                    holes=[[(p[0] + s_off, p[1] + t_off) for p in h] for h in holes] or None)
        out = out + Mesh([[p[0], PLACA0[0] + p[1] * dy + p[2] * ny, PLACA0[1] + p[1] * dz + p[2] * nz]
                          for p in m.v], m.f)
    return out, ln


def main():
    meia = LARGURA / 2
    corte = 6.5   # meia-largura da passagem do cabo
    outer, furo = perfil_lateral()
    frente, topo = perfil_central()
    corpo = union(extrude_x(outer, -meia, -corte, holes=[furo]),
                  extrude_x(frente, -corte, corte), extrude_x(topo, -corte, corte),
                  extrude_x(outer, corte, meia, holes=[furo]))

    # --- logo: átomo + DANY / NOGUEIRA + coração ---
    _, comp = na_placa([], 0, 0)
    cap = 6.2
    trk = cap * 0.32
    l1, w1 = texto("DANY", cap, trk)
    l2, w2 = texto("NOGUEIRA", cap, trk)
    atomo_r = 12.5
    cor_tam = 6.5
    gap = 4.0
    bloco = w2 + 1.5 + cor_tam
    total = atomo_r * 2 + gap + bloco
    s0 = -total / 2
    tc = comp / 2 + 0.5                          # centro vertical da placa
    linha = cap * 1.75
    # texto: NOGUEIRA embaixo, DANY centralizado em cima
    xs = s0 + atomo_r * 2 + gap
    nome_formas = [(c, h) for c, h in l2]
    nome_formas += [([(p[0] + (w2 - w1) / 2, p[1] + linha) for p in c],
                     [[(p[0] + (w2 - w1) / 2, p[1] + linha) for p in hh] for hh in h]) for c, h in l1]
    nome, _ = na_placa(nome_formas, xs, tc - linha / 2 - cap / 2)
    # anéis do átomo (cor do nome) e corações (destaque)
    aneis = [elipse_anel(atomo_r - 0.8, atomo_r * 0.36, 1.3, a) for a in (0, 60, 120)]
    atomo, _ = na_placa(aneis, s0 + atomo_r, tc)
    coracao_atomo = [(heart(5.2), [])]
    c1, _ = na_placa(coracao_atomo, s0 + atomo_r, tc - 0.3)
    c2, _ = na_placa([(heart(cor_tam), [])], xs + w2 + 1.5 + cor_tam / 2, tc - linha / 2 - cap / 2 + cap * 0.48)

    partes = [("corpo", corpo, COR_CORPO), ("nome", union(nome, atomo), COR_NOME),
              ("coracoes", union(c1, c2), COR_CORACAO)]
    check(partes)
    export_3mf(partes, os.path.join(HERE, "suporte-dany-nogueira.3mf"))
    export_stl(union(*[m for _, m, _ in partes]), os.path.join(HERE, "suporte-dany-nogueira.stl"), "dany")
    preview(partes, os.path.join(HERE, "previa.json"))
    print(f"placa: {comp:.1f} mm | logo: {total:.1f} mm de largura | letras: {cap} mm")


if __name__ == "__main__":
    main()
