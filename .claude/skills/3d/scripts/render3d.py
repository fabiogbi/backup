#!/usr/bin/env python3
"""Renderizador 3D minimalista (Python puro) que gera SVG a partir de uma cena JSON.

Uso: python3 render3d.py cena.json saida.svg   (vetorial, algoritmo do pintor, contornos)
     python3 render3d.py cena.json saida.png   (raster com z-buffer: oclusão correta, antialias 2x)

Recursos: câmera em perspectiva, luz direcional + ambiente, sombreamento flat,
sombras projetadas no chão (primeiro objeto "plane"), contornos opcionais,
fundo com gradiente. Algoritmo do pintor (ordenação por profundidade).
"""
import json
import math
import sys

# ---------- vetores ----------

def add(a, b): return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]
def sub(a, b): return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
def mul(a, s): return [a[0] * s, a[1] * s, a[2] * s]
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]

def norm(a):
    length = math.sqrt(dot(a, a)) or 1.0
    return [a[0] / length, a[1] / length, a[2] / length]

def centroid(pts):
    n = len(pts)
    return [sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n, sum(p[2] for p in pts) / n]

def face_normal(pts):
    # Newell: robusto para polígonos com mais de 3 vértices
    n = [0.0, 0.0, 0.0]
    for i, p in enumerate(pts):
        q = pts[(i + 1) % len(pts)]
        n[0] += (p[1] - q[1]) * (p[2] + q[2])
        n[1] += (p[2] - q[2]) * (p[0] + q[0])
        n[2] += (p[0] - q[0]) * (p[1] + q[1])
    return norm(n)

# ---------- cores ----------

def hex2rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]

def rgb2hex(c):
    return "#" + "".join(f"{max(0, min(255, int(round(v)))):02x}" for v in c)

def shade(rgb, k, light_rgb, shadow_rgb):
    # Realces puxam para a cor da luz; sombras puxam para uma cor fria (não para o preto).
    base = [v * k for v in rgb]
    if k >= 1:
        return base
    t = (1 - k) * 0.15
    return [base[i] * (1 - t) + shadow_rgb[i] * k * t for i in range(3)]

# ---------- geometrias (faces = listas de vértices; ref = ponto "de dentro" para orientar) ----------

def g_box(o):
    sx, sy, sz = [v / 2 for v in o.get("size", [1, 1, 1])]
    v = [[x, y, z] for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
    idx = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return [([v[i] for i in f], [0, 0, 0]) for f in idx]

def g_sphere(o):
    r = o.get("radius", 0.5)
    seg = max(4, int(o.get("segments", 16)))
    rings = max(2, seg // 2)
    faces = []
    for i in range(rings):
        t0, t1 = math.pi * i / rings, math.pi * (i + 1) / rings
        for j in range(seg):
            p0, p1 = 2 * math.pi * j / seg, 2 * math.pi * (j + 1) / seg
            pts = [
                [r * math.sin(t0) * math.cos(p0), r * math.cos(t0), r * math.sin(t0) * math.sin(p0)],
                [r * math.sin(t0) * math.cos(p1), r * math.cos(t0), r * math.sin(t0) * math.sin(p1)],
                [r * math.sin(t1) * math.cos(p1), r * math.cos(t1), r * math.sin(t1) * math.sin(p1)],
                [r * math.sin(t1) * math.cos(p0), r * math.cos(t1), r * math.sin(t1) * math.sin(p0)],
            ]
            if i == 0:
                pts = [pts[0], pts[2], pts[3]]
            elif i == rings - 1:
                pts = [pts[0], pts[1], pts[2]]
            faces.append((pts, [0, 0, 0]))
    return faces

def g_cylinder(o, top_ratio=1.0):
    r = o.get("radius", 0.5)
    rt = o.get("radius_top", r * top_ratio)
    h = o.get("height", 1.0) / 2
    seg = max(3, int(o.get("segments", 24)))
    ang = [2 * math.pi * j / seg for j in range(seg)]
    bot = [[r * math.cos(a), -h, r * math.sin(a)] for a in ang]
    top = [[rt * math.cos(a), h, rt * math.sin(a)] for a in ang]
    faces = []
    for j in range(seg):
        k = (j + 1) % seg
        if rt > 1e-9:
            faces.append(([bot[j], bot[k], top[k], top[j]], [0, 0, 0]))
        else:
            faces.append(([bot[j], bot[k], [0, h, 0]], [0, 0, 0]))
    faces.append((bot, [0, h, 0]))
    if rt > 1e-9:
        faces.append((top, [0, -h, 0]))
    return faces

def g_cone(o):
    return g_cylinder(dict(o, radius_top=0.0))

def g_pyramid(o):
    o = dict(o)
    o.setdefault("segments", 4)
    o.setdefault("radius", o.get("size", 1) / math.sqrt(2) if not isinstance(o.get("size"), list) else 0.7)
    return g_cylinder(dict(o, radius_top=0.0))

def g_torus(o):
    R = o.get("radius", 1.0)
    rt = o.get("tube", 0.3)
    seg = max(6, int(o.get("segments", 32)))
    tseg = max(3, int(o.get("tube_segments", 12)))
    faces = []
    def pt(i, j):
        u, v = 2 * math.pi * i / seg, 2 * math.pi * j / tseg
        return [(R + rt * math.cos(v)) * math.cos(u), rt * math.sin(v), (R + rt * math.cos(v)) * math.sin(u)]
    for i in range(seg):
        for j in range(tseg):
            u = 2 * math.pi * (i + 0.5) / seg
            ref = [R * math.cos(u), 0, R * math.sin(u)]
            faces.append(([pt(i, j), pt(i + 1, j), pt(i + 1, j + 1), pt(i, j + 1)], ref))
    return faces

def g_icosphere(o):
    r = o.get("radius", 0.5)
    t = (1 + 5 ** 0.5) / 2
    v = [norm(x) for x in [[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t],
                           [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]]]
    tris = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
            (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5),
            (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    faces = [[v[a], v[b], v[c]] for a, b, c in tris]
    for _ in range(int(o.get("detail", 0))):
        nf = []
        for a, b, c in faces:
            ab, bc, ca = norm(mul(add(a, b), .5)), norm(mul(add(b, c), .5)), norm(mul(add(c, a), .5))
            nf += [[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]]
        faces = nf
    return [([mul(p, r) for p in f], [0, 0, 0]) for f in faces]

def g_plane(o):
    sx, sz = [v / 2 for v in o.get("size", [10, 10])]
    return [([[-sx, 0, -sz], [sx, 0, -sz], [sx, 0, sz], [-sx, 0, sz]], None)]

def g_mesh(o):
    verts = o["vertices"]
    return [([verts[i] for i in f], None) for f in o["faces"]]

GEOMS = {"box": g_box, "cube": g_box, "sphere": g_sphere, "cylinder": g_cylinder, "cone": g_cone,
         "pyramid": g_pyramid, "icosphere": g_icosphere, "torus": g_torus, "plane": g_plane, "mesh": g_mesh}

# ---------- transformações ----------

def make_transform(o):
    s = o.get("scale", 1)
    s = [s, s, s] if isinstance(s, (int, float)) else s
    rx, ry, rz = [math.radians(a) for a in o.get("rotation", [0, 0, 0])]
    pos = o.get("position", [0, 0, 0])
    cx, sx_, cy, sy_, cz, sz_ = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)

    def tf(p):
        x, y, z = p[0] * s[0], p[1] * s[1], p[2] * s[2]
        y, z = y * cx - z * sx_, y * sx_ + z * cx
        x, z = x * cy + z * sy_, -x * sy_ + z * cy
        x, y = x * cz - y * sz_, x * sz_ + y * cz
        return [x + pos[0], y + pos[1], z + pos[2]]
    return tf

# ---------- render ----------

def render(scene, fmt="svg"):
    W, H = scene.get("width", 800), scene.get("height", 600)
    cam = scene.get("camera", {})
    cpos = cam.get("position", [6, 5, 8])
    ctgt = cam.get("target", [0, 0, 0])
    fov = math.radians(cam.get("fov", 40))
    f = norm(sub(ctgt, cpos))
    r = norm(cross(f, [0, 1, 0]))
    u = cross(r, f)
    focal = (H / 2) / math.tan(fov / 2)
    ortho = cam.get("orthographic", False)
    ortho_scale = cam.get("ortho_size", 5)

    light = scene.get("light", {})
    ldir = norm(light.get("direction", [-0.5, -1, -0.3]))
    ambient = light.get("ambient", 0.35)
    light_rgb = hex2rgb(light.get("color", "#ffffff"))
    shadow_rgb = hex2rgb(light.get("shadow_color", "#2a3a6a"))
    outline = scene.get("outline")
    ow = scene.get("outline_width", 0.8)
    shadows = scene.get("shadows", True)
    shadow_opacity = scene.get("shadow_opacity", 0.22)

    def project(p):
        d = sub(p, cpos)
        x, y, z = dot(d, r), dot(d, u), dot(d, f)
        if ortho:
            k = (H / 2) / ortho_scale
            return W / 2 + x * k, H / 2 - y * k, z
        if z <= 0.05:
            return None
        return W / 2 + x / z * focal, H / 2 - y / z * focal, z

    ground_y = None
    ground_polys, shadow_polys, polys = [], [], []

    for o in scene.get("objects", []):
        kind = o.get("type", "box")
        gen = GEOMS.get(kind)
        if gen is None:
            print(f"aviso: tipo desconhecido '{kind}', ignorado", file=sys.stderr)
            continue
        tf = make_transform(o)
        rgb = hex2rgb(o.get("color", "#cccccc"))
        is_ground = o.get("ground", kind == "plane")
        if is_ground and ground_y is None:
            ground_y = o.get("ground_y", tf([0, 0, 0])[1] if kind == "plane" else None)
            if ground_y is None:  # chão sólido: usa o topo do objeto
                ground_y = max(tf(p)[1] for pts, _ in gen(o) for p in pts)
        bias = o.get("depth_bias", 0.0)
        obj_outline = o.get("outline", outline)
        for pts, ref in gen(o):
            wp = [tf(p) for p in pts]
            n = face_normal(wp)
            c = centroid(wp)
            if ref is not None and dot(n, sub(c, tf(ref))) < 0:
                n = mul(n, -1)
                wp = wp[::-1]
            to_cam = norm(sub(cpos, c)) if not ortho else mul(f, -1)
            if dot(n, to_cam) <= 0:
                if kind == "plane" or ref is None and o.get("double_sided", False):
                    n = mul(n, -1)
                else:
                    continue
            if not is_ground and shadows and o.get("cast_shadow", True):
                shadow_polys.append(wp)
            proj = [project(p) for p in wp]
            if any(p is None for p in proj):
                continue
            k = ambient + (1 - ambient) * max(0.0, -dot(n, ldir))
            k *= o.get("brightness", 1.0)
            col = rgb2hex(shade(rgb, k, light_rgb, shadow_rgb))
            depth = sum(p[2] for p in proj) / len(proj) - bias
            item = (depth, proj, col, obj_outline, o.get("opacity", 1))
            (ground_polys if is_ground else polys).append(item)

    shadow_proj = []
    if shadows and ground_y is not None and ldir[1] < -1e-3:
        for wp in shadow_polys:
            sp = []
            for p in wp:
                t = (ground_y - p[1]) / ldir[1]
                sp.append(project([p[0] + ldir[0] * t, ground_y + 0.001, p[2] + ldir[2] * t]))
            if all(p is not None for p in sp):
                shadow_proj.append(sp)

    if fmt == "png":
        return raster(scene, W, H, ground_polys, polys, shadow_proj, shadow_opacity)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">']
    bg, bg2 = scene.get("background", "#f4efe6"), scene.get("background2")
    if bg2:
        out.append(f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{bg}"/>'
                   f'<stop offset="1" stop-color="{bg2}"/></linearGradient></defs>')
        out.append(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')
    else:
        out.append(f'<rect width="{W}" height="{H}" fill="{bg}"/>')

    def poly_svg(proj, fill, stroke, extra=""):
        pts = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in proj)
        if stroke:
            st = f' stroke="{stroke}" stroke-width="{ow}" stroke-linejoin="round"'
        else:  # traço da mesma cor esconde frestas entre faces vizinhas
            st = f' stroke="{fill}" stroke-width="0.6" stroke-linejoin="round"'
        return f'<polygon points="{pts}" fill="{fill}"{st}{extra}/>'

    for d, proj, col, st, op in sorted(ground_polys, key=lambda t: -t[0]):
        out.append(poly_svg(proj, col, st, f' opacity="{op}"' if op != 1 else ""))

    if shadow_proj:
        # recorta as sombras pelo contorno do chão para não vazarem para o fundo
        out.append('<clipPath id="chao">' + "".join(
            '<polygon points="' + " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in proj) + '"/>'
            for _, proj, _, _, _ in ground_polys) + '</clipPath>')
        out.append(f'<g opacity="{shadow_opacity}" clip-path="url(#chao)">')
        sc = scene.get("shadow_color", "#1f2430")
        for sp in shadow_proj:
            pts = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in sp)
            out.append(f'<polygon points="{pts}" fill="{sc}" stroke="{sc}" stroke-width="0.6"/>')
        out.append("</g>")

    for d, proj, col, st, op in sorted(polys, key=lambda t: -t[0]):
        out.append(poly_svg(proj, col, st, f' opacity="{op}"' if op != 1 else ""))

    out.append("</svg>")
    return "\n".join(out)


def raster(scene, W, H, ground_polys, polys, shadow_proj, shadow_opacity, ss=2):
    """Rasterizador com z-buffer (Python puro). Retorna bytes PNG."""
    import struct
    import zlib
    w, h = W * ss, H * ss
    top = hex2rgb(scene.get("background", "#f4efe6"))
    bot = hex2rgb(scene.get("background2", scene.get("background", "#f4efe6")))
    color = [[top[i] + (bot[i] - top[i]) * (y / max(1, h - 1)) for i in range(3)] for y in range(h)]
    img = [[list(color[y]) for _ in range(w)] for y in range(h)]
    zbuf = [[float("inf")] * w for _ in range(h)]
    owner = [[0] * w for _ in range(h)]  # 0 fundo, 1 chão, 2 objeto

    def fill(poly, cb):
        pts = [(p[0] * ss, p[1] * ss, p[2]) for p in poly]
        for i in range(1, len(pts) - 1):
            a, b, c = pts[0], pts[i], pts[i + 1]
            area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if abs(area) < 1e-9:
                continue
            x0, x1 = max(0, int(min(a[0], b[0], c[0]))), min(w - 1, int(max(a[0], b[0], c[0])) + 1)
            y0, y1 = max(0, int(min(a[1], b[1], c[1]))), min(h - 1, int(max(a[1], b[1], c[1])) + 1)
            iza, izb, izc = 1 / a[2], 1 / b[2], 1 / c[2]
            for y in range(y0, y1 + 1):
                py = y + 0.5
                for x in range(x0, x1 + 1):
                    px = x + 0.5
                    w0 = ((b[0] - px) * (c[1] - py) - (b[1] - py) * (c[0] - px)) / area
                    w1 = ((c[0] - px) * (a[1] - py) - (c[1] - py) * (a[0] - px)) / area
                    w2 = 1 - w0 - w1
                    if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6:
                        continue
                    cb(x, y, 1 / (w0 * iza + w1 * izb + w2 * izc))

    def draw(items, kind):
        for _, proj, col, _, op in items:
            rgb = hex2rgb(col)

            def put(x, y, z, rgb=rgb, op=op):
                if z < zbuf[y][x]:
                    zbuf[y][x] = z
                    owner[y][x] = kind
                    px = img[y][x]
                    img[y][x] = [px[i] * (1 - op) + rgb[i] * op for i in range(3)] if op < 1 else list(rgb)
            fill(proj, put)

    draw(ground_polys, 1)
    if shadow_proj:
        mask = [[False] * w for _ in range(h)]

        def mark(x, y, z):
            mask[y][x] = True
        for sp in shadow_proj:
            fill(sp, mark)
        sc = hex2rgb(scene.get("shadow_color", "#1f2430"))
        for y in range(h):
            for x in range(w):
                if mask[y][x] and owner[y][x] == 1:
                    px = img[y][x]
                    img[y][x] = [px[i] * (1 - shadow_opacity) + sc[i] * shadow_opacity for i in range(3)]
    draw(polys, 2)

    raw = bytearray()
    for y in range(H):
        raw.append(0)
        for x in range(W):
            acc = [0.0, 0.0, 0.0]
            for dy in range(ss):
                for dx in range(ss):
                    px = img[y * ss + dy][x * ss + dx]
                    acc[0] += px[0]; acc[1] += px[1]; acc[2] += px[2]
            raw += bytes(max(0, min(255, int(c / (ss * ss) + 0.5))) for c in acc)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as fh:
        scene = json.load(fh)
    if sys.argv[2].lower().endswith(".png"):
        with open(sys.argv[2], "wb") as fh:
            fh.write(render(scene, "png"))
    else:
        with open(sys.argv[2], "w", encoding="utf-8") as fh:
            fh.write(render(scene))
    print(f"ok: {sys.argv[2]}")


if __name__ == "__main__":
    main()
