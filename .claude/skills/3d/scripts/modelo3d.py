#!/usr/bin/env python3
"""Modelagem 3D para impressão (Python puro): primitivas, extrusão, STL, 3MF multicolorido.

Unidades em milímetros, eixo Z para cima, mesa da impressora no plano Z=0.

    import sys; sys.path.insert(0, "<skill>/scripts")
    from modelo3d import *

    base  = rounded_box(60, 30, 3, r=4)
    texto = extrude(star(5, 8, 4), 1.2).moved(0, 0, 3)     # relevo de 1.2 mm sobre a base
    furo  = cylinder(2.5, 3).moved(-24, 0, 0)               # só para conferência: STL não faz subtração
    partes = [("base", base, "#1f2430"), ("estrela", texto, "#f2cc8f")]
    check(partes)                                            # cabe na K2 Pro? malha fechada?
    export_3mf(partes, "chaveiro.3mf")                       # 1 objeto, 1 parte por cor
    export_stl(base, "base.stl")
    preview(partes, "previa.json")                           # cena para render3d.py

Limitação: não há booleanas (furos/subtração). Para furos, monte a forma com
polígonos que já têm o recorte (extrude aceita furos via `holes=`) ou use OpenSCAD.
"""
import math
import struct
import zipfile

K2_PRO = {"nome": "Creality K2 Pro", "x": 300.0, "y": 300.0, "z": 300.0}


class Mesh:
    def __init__(self, vertices=None, faces=None):
        self.v = [list(map(float, p)) for p in (vertices or [])]
        self.f = [tuple(t) for t in (faces or [])]

    # ---- transformações (retornam nova malha) ----
    def _map(self, fn):
        return Mesh([fn(p) for p in self.v], self.f)

    def moved(self, x=0, y=0, z=0):
        return self._map(lambda p: [p[0] + x, p[1] + y, p[2] + z])

    def scaled(self, sx, sy=None, sz=None):
        sy = sx if sy is None else sy
        sz = sx if sz is None else sz
        m = self._map(lambda p: [p[0] * sx, p[1] * sy, p[2] * sz])
        if sx * sy * sz < 0:  # espelhamento inverte a orientação das faces
            m.f = [(a, c, b) for a, b, c in m.f]
        return m

    def rotated(self, rx=0, ry=0, rz=0):
        ax, ay, az = (math.radians(a) for a in (rx, ry, rz))

        def rot(p):
            x, y, z = p
            y, z = y * math.cos(ax) - z * math.sin(ax), y * math.sin(ax) + z * math.cos(ax)
            x, z = x * math.cos(ay) + z * math.sin(ay), -x * math.sin(ay) + z * math.cos(ay)
            x, y = x * math.cos(az) - y * math.sin(az), x * math.sin(az) + y * math.cos(az)
            return [x, y, z]
        return self._map(rot)

    def __add__(self, other):
        n = len(self.v)
        return Mesh(self.v + other.v, self.f + [(a + n, b + n, c + n) for a, b, c in other.f])

    def bounds(self):
        xs, ys, zs = zip(*self.v)
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def on_bed(self):
        """Apoia a peça na mesa (menor Z = 0)."""
        return self.moved(0, 0, -self.bounds()[0][2])

    def centered(self):
        (x0, y0, _), (x1, y1, _) = self.bounds()
        return self.moved(-(x0 + x1) / 2, -(y0 + y1) / 2, 0)

    def is_closed(self):
        edges = {}
        for a, b, c in self.f:
            for e in ((a, b), (b, c), (c, a)):
                edges[e] = edges.get(e, 0) + 1
        return all(n == 1 and edges.get((e[1], e[0])) == 1 for e, n in edges.items())


def union(*meshes):
    """Junta malhas num só corpo (sobreposições são resolvidas pelo fatiador)."""
    out = Mesh()
    for m in meshes:
        out = out + m
    return out

# ---------- polígonos 2D ----------

def _area(poly):
    return sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
               for i in range(len(poly))) / 2


def ccw(poly):
    return list(poly) if _area(poly) > 0 else list(poly)[::-1]


def circle(r, seg=48):
    return [(r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg)) for i in range(seg)]


def rect(w, h):
    return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]


def rounded_rect(w, h, r, seg=8):
    r = min(r, w / 2, h / 2)
    pts = []
    for cx, cy, a0 in ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0),
                       (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def star(n, r_out, r_in):
    return [((r_out if i % 2 == 0 else r_in) * math.cos(math.pi / 2 + math.pi * i / n),
             (r_out if i % 2 == 0 else r_in) * math.sin(math.pi / 2 + math.pi * i / n)) for i in range(2 * n)]


def heart(size, seg=64):
    pts = []
    for i in range(seg):
        t = 2 * math.pi * i / seg
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x * size / 32, y * size / 32))
    return pts


def _inside(p, a, b, c):
    def s(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
    d1, d2, d3 = s(p, a, b), s(p, b, c), s(p, c, a)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


def _merge_holes(outer, holes):
    """Liga cada furo ao contorno por uma 'ponte' para virar um único polígono simples."""
    poly = ccw(outer)
    for hole in sorted((ccw(h)[::-1] for h in holes), key=lambda h: -max(p[0] for p in h)):
        hi = max(range(len(hole)), key=lambda i: hole[i][0])
        hp = hole[hi]
        # vértice do contorno visível mais próximo à direita
        best = min((i for i in range(len(poly)) if poly[i][0] >= hp[0]),
                   key=lambda i: (poly[i][0] - hp[0]) ** 2 + (poly[i][1] - hp[1]) ** 2, default=0)
        ring = hole[hi:] + hole[:hi + 1]
        poly = poly[:best + 1] + ring + poly[best:]
    return poly


def triangulate(poly):
    """Ear clipping. Retorna triângulos como índices do polígono (CCW)."""
    idx = list(range(len(poly)))
    tris, guard = [], 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = poly[i0], poly[i1], poly[i2]
            if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) <= 1e-12:
                continue
            if any(_inside(poly[j], a, b, c) for j in idx if j not in (i0, i1, i2) and poly[j] not in (a, b, c)):
                continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            break
        else:
            break
    if len(idx) == 3:
        tris.append(tuple(idx))
    return tris

# ---------- sólidos ----------

def extrude(poly, h, z0=0.0, holes=None, scale_top=1.0):
    """Extruda um polígono 2D (opcionalmente com furos) de z0 até z0+h. scale_top < 1 gera chanfro/tronco."""
    poly = _merge_holes(poly, holes) if holes else ccw(poly)
    n = len(poly)
    v = [[x, y, z0] for x, y in poly] + [[x * scale_top, y * scale_top, z0 + h] for x, y in poly]
    f = []
    for a, b, c in triangulate(poly):
        f.append((n + a, n + b, n + c))
        f.append((c, b, a))
    for i in range(n):
        j = (i + 1) % n
        f += [(i, j, n + j), (i, n + j, n + i)]
    return Mesh(v, f)


def box(x, y, z):
    """Caixa centrada em XY, apoiada em Z=0."""
    return extrude(rect(x, y), z)


def rounded_box(x, y, z, r=2, seg=8):
    return extrude(rounded_rect(x, y, r, seg), z)


def cylinder(r, h, seg=64, r_top=None):
    if r_top is not None and r_top <= 1e-9:
        return cone(r, h, seg)
    return extrude(circle(r, seg), h, scale_top=1.0 if r_top is None else r_top / r)


def cone(r, h, seg=64):
    base = circle(r, seg)
    v = [[x, y, 0] for x, y in base] + [[0, 0, h], [0, 0, 0]]
    apex, center = seg, seg + 1
    f = []
    for i in range(seg):
        j = (i + 1) % seg
        f += [(i, j, apex), (j, i, center)]
    return Mesh(v, f)


def sphere(r, detail=3):
    t = (1 + 5 ** 0.5) / 2
    v = [[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t],
         [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
         (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5),
         (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    nrm = lambda p: [c / math.sqrt(sum(k * k for k in p)) for c in p]
    v = [nrm(p) for p in v]
    for _ in range(detail):
        cache, nf = {}, []

        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                v.append(nrm([(v[a][i] + v[b][i]) / 2 for i in range(3)]))
                cache[key] = len(v) - 1
            return cache[key]
        for a, b, c in f:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        f = nf
    out = []
    for a, b, c in f:  # garante normais para fora
        u = [v[b][i] - v[a][i] for i in range(3)]
        w = [v[c][i] - v[a][i] for i in range(3)]
        n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
        out.append((a, b, c) if sum(n[i] * v[a][i] for i in range(3)) > 0 else (a, c, b))
    return Mesh([[p[0] * r, p[1] * r, p[2] * r + r] for p in v], out)  # apoiada em Z=0


def heightmap(grid, cell=0.5, base=0.8, height=3.0):
    """Relevo/litofania a partir de uma grade de valores 0..1 (linhas x colunas).
    Para litofania: valor 1 = escuro = mais grosso. Base sólida em Z=0."""
    rows, cols = len(grid), len(grid[0])
    v, f = [], []
    top = lambda r, c: r * cols + c
    for r in range(rows):
        for c in range(cols):
            v.append([c * cell, (rows - 1 - r) * cell, base + grid[r][c] * height])
    off = len(v)
    for r in range(rows):
        for c in range(cols):
            v.append([c * cell, (rows - 1 - r) * cell, 0.0])
    for r in range(rows - 1):
        for c in range(cols - 1):
            a, b, d, e = top(r, c), top(r, c + 1), top(r + 1, c), top(r + 1, c + 1)
            f += [(a, d, e), (a, e, b), (off + a, off + e, off + d), (off + a, off + b, off + e)]
    ring = [top(0, c) for c in range(cols)] + [top(r, cols - 1) for r in range(1, rows)] + \
           [top(rows - 1, c) for c in range(cols - 2, -1, -1)] + [top(r, 0) for r in range(rows - 2, 0, -1)]
    for i in range(len(ring)):
        a, b = ring[i], ring[(i + 1) % len(ring)]
        f += [(a, b, off + b), (a, off + b, off + a)]
    return Mesh(v, f)

# ---------- exportação ----------

def export_stl(mesh, path, name="modelo"):
    with open(path, "wb") as fh:
        fh.write(name.encode()[:80].ljust(80, b"\0"))
        fh.write(struct.pack("<I", len(mesh.f)))
        for a, b, c in mesh.f:
            p, q, r = mesh.v[a], mesh.v[b], mesh.v[c]
            u = [q[i] - p[i] for i in range(3)]
            w = [r[i] - p[i] for i in range(3)]
            n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
            ln = math.sqrt(sum(k * k for k in n)) or 1
            fh.write(struct.pack("<12fH", *(k / ln for k in n), *p, *q, *r, 0))


def export_3mf(parts, path):
    """parts = [(nome, Mesh, "#rrggbb"), ...] -> um objeto com uma parte por cor.
    No Creality Print, cada parte aparece na lista de objetos e recebe um filamento/slot do CFS."""
    res, comps = [], []
    mats = "".join(f'<base name="{n}" displaycolor="{c.upper()}FF"/>' for n, _, c in parts)
    for i, (name, m, _) in enumerate(parts, start=1):
        verts = "".join(f'<vertex x="{p[0]:.4f}" y="{p[1]:.4f}" z="{p[2]:.4f}"/>' for p in m.v)
        tris = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.f)
        res.append(f'<object id="{i + 1}" name="{name}" type="model" pid="1" pindex="{i - 1}">'
                   f'<mesh><vertices>{verts}</vertices><triangles>{tris}</triangles></mesh></object>')
        comps.append(f'<component objectid="{i + 1}"/>')
    root = len(parts) + 2
    (x0, y0, _), (x1, y1, _) = union(*[m for _, m, _ in parts]).bounds()
    tx, ty = K2_PRO["x"] / 2 - (x0 + x1) / 2, K2_PRO["y"] / 2 - (y0 + y1) / 2  # centraliza na mesa
    model = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<resources><basematerials id="1">{mats}</basematerials>{"".join(res)}'
             f'<object id="{root}" name="modelo" type="model"><components>{"".join(comps)}</components></object>'
             f'</resources><build><item objectid="{root}" transform="1 0 0 0 1 0 0 0 1 {tx:.3f} {ty:.3f} 0"/></build></model>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr("3D/3dmodel.model", model)


def check(parts, printer=K2_PRO):
    """Confere tamanho na mesa, malha fechada e Z mínimo. Imprime um relatório e retorna True se ok."""
    ok = True
    all_mesh = union(*[m for _, m, _ in parts])
    (x0, y0, z0), (x1, y1, z1) = all_mesh.bounds()
    sx, sy, sz = x1 - x0, y1 - y0, z1 - z0
    print(f"Tamanho: {sx:.1f} x {sy:.1f} x {sz:.1f} mm  (volume {printer['nome']}: "
          f"{printer['x']:.0f} x {printer['y']:.0f} x {printer['z']:.0f})")
    if sx > printer["x"] or sy > printer["y"] or sz > printer["z"]:
        print("  ERRO: não cabe na impressora — divida a peça ou reduza a escala.")
        ok = False
    if abs(z0) > 1e-6:
        print(f"  AVISO: Z mínimo = {z0:.3f} mm (use .on_bed() para apoiar na mesa).")
    for name, m, _ in parts:
        if not m.is_closed():
            print(f"  AVISO: '{name}' não é uma malha fechada (pode ser a união de corpos sobrepostos;"
                  " o fatiador costuma resolver, mas confira no Creality Print).")
    print(f"Partes/cores: {len(parts)}  |  triângulos: {len(all_mesh.f)}")
    return ok


def preview(parts, path, width=900, height=700, background="#eef1f5"):
    """Gera uma cena JSON para scripts/render3d.py (converte Z-para-cima -> Y-para-cima)."""
    import json
    all_mesh = union(*[m for _, m, _ in parts])
    (x0, y0, z0), (x1, y1, z1) = all_mesh.bounds()
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    size = max(x1 - x0, y1 - y0, z1 - z0)
    objs = [{"type": "plane", "size": [size * 3, size * 3], "position": [0, 0, 0], "color": "#c9ced6"}]
    for name, m, color in parts:
        objs.append({"type": "mesh", "color": color, "outline": None,
                     "vertices": [[p[0] - cx, p[2], -(p[1] - cy)] for p in m.v],
                     "faces": [list(t) for t in m.f]})
    d = size * 1.5
    scene = {"width": width, "height": height, "background": background,
             "camera": {"position": [d * 0.8, d * 0.9, d * 1.1], "target": [0, (z1 - z0) / 3, 0], "fov": 35},
             "light": {"direction": [-0.4, -1, -0.6], "ambient": 0.45}, "objects": objs}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(scene, fh)


# ---------- texto e formas decorativas ----------

def _pip(pt, poly):
    x, y, c = pt[0], pt[1], False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def text_shapes(s, font_path, cap, tracking=0.0, steps=8):
    """Converte um texto em formas 2D [(contorno, [furos])] em mm (requer `pip install fonttools`).
    cap = altura das maiúsculas em mm; linha de base em y=0, começando em x=0. Retorna (formas, largura).
    Fontes do sistema: `fc-list` (ex.: /usr/share/fonts/opentype/inter/Inter-SemiBold.otf)."""
    from fontTools.pens.basePen import BasePen
    from fontTools.ttLib import TTFont

    class Pen(BasePen):
        def __init__(self, gs):
            super().__init__(gs)
            self.contours, self.cur = [], []

        def _moveTo(self, p):
            self.cur = [p]

        def _lineTo(self, p):
            self.cur.append(p)

        def _curveToOne(self, p1, p2, p3):
            p0 = self.cur[-1]
            for i in range(1, steps + 1):
                t = i / steps
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

    font = TTFont(font_path)
    gs, cmap = font.getGlyphSet(), font.getBestCmap()
    k = cap / font["OS/2"].sCapHeight
    shapes, x = [], 0.0
    for ch in s:
        g = cmap.get(ord(ch))
        if g is None:
            continue
        pen = Pen(gs)
        gs[g].draw(pen)
        cs = [[(x + px * k, py * k) for px, py in c] for c in pen.contours]
        for c in cs:
            if sum(_pip(c[0], o) for o in cs if o is not c) % 2 == 0:
                holes = [h for h in cs if h is not c and _pip(h[0], c) and abs(_area(h)) < abs(_area(c))]
                shapes.append((c, holes))
        x += gs[g].width * k + tracking
    return shapes, max(0.0, x - tracking)


def shift_shapes(shapes, dx, dy):
    return [([(p[0] + dx, p[1] + dy) for p in c], [[(p[0] + dx, p[1] + dy) for p in h] for h in hs])
            for c, hs in shapes]


def ellipse_ring(rx, ry, width, angle=0, seg=72):
    """Anel elíptico (forma 2D com furo), útil para órbitas, molduras, logos."""
    a = math.radians(angle)

    def el(ex, ey):
        return [(ex * math.cos(t) * math.cos(a) - ey * math.sin(t) * math.sin(a),
                 ex * math.cos(t) * math.sin(a) + ey * math.sin(t) * math.cos(a))
                for t in (2 * math.pi * i / seg for i in range(seg))]
    return el(rx + width / 2, ry + width / 2), [el(rx - width / 2, ry - width / 2)]


def emboss(shapes, height, to_world, sink=0.2):
    """Extruda formas 2D (s, t) em relevo e leva para uma face com `to_world(s, t, h) -> [x, y, z]`.
    `sink` afunda a base na superfície para garantir a união. A transformação deve preservar a orientação."""
    out = Mesh()
    for c, hs in shapes:
        m = extrude(c, height + sink, z0=-sink, holes=hs or None)
        out = out + Mesh([to_world(*p) for p in m.v], m.f)
    return out
