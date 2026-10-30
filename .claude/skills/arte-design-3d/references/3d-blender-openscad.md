# 3D para Blender, OpenSCAD e impressão 3D

## OpenSCAD — peças paramétricas e impressão 3D

Ideal para objetos funcionais: suportes, caixas, porta-objetos, engrenagens, chaveiros. Modelagem por CSG (união, diferença, interseção).

```openscad
// Porta-lápis paramétrico
diametro = 70; altura = 100; parede = 2.4; lados = 6; $fn = 96;

difference() {
  cylinder(d = diametro, h = altura, $fn = lados);
  translate([0, 0, parede]) cylinder(d = diametro - 2*parede, h = altura, $fn = lados);
}
// detalhe: anel decorativo
translate([0,0,altura*0.7]) rotate_extrude() translate([diametro/2,0]) circle(r = 1.5);
```

Boas práticas para impressão FDM:
- Parede ≥ 1.2 mm (múltiplos do bico 0.4 mm), detalhes ≥ 0.8 mm.
- Evite balanços > 45° sem suporte; chanfre em vez de filete nas bases.
- Folga para encaixes: 0.2–0.3 mm. Base plana grande para aderência.
- Parâmetros no topo do arquivo, comentados, para o usuário ajustar.
- Exportar: `openscad -o peca.stl peca.scad` (se o OpenSCAD estiver instalado).

## Gerar STL/OBJ sem programas externos

Para formas simples, escreva o arquivo direto com Python (STL ASCII = lista de triângulos com normal):
```python
def write_stl(path, tris, name="obj"):
    import math
    with open(path, "w") as f:
        f.write(f"solid {name}\n")
        for a, b, c in tris:
            u = [b[i]-a[i] for i in range(3)]; v = [c[i]-a[i] for i in range(3)]
            n = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
            l = math.sqrt(sum(x*x for x in n)) or 1
            f.write(f" facet normal {n[0]/l} {n[1]/l} {n[2]/l}\n  outer loop\n")
            for p in (a, b, c): f.write(f"   vertex {p[0]} {p[1]} {p[2]}\n")
            f.write("  endloop\n endfacet\n")
        f.write(f"endsolid {name}\n")
```
Triângulos em ordem anti-horária vista de fora; malha fechada (manifold) para imprimir. O `scripts/render3d.py` também aceita `mesh` com os mesmos vértices/faces para pré-visualizar.

## Blender (bpy) — renders de alta qualidade

Entregue um script que o usuário cola em *Scripting → New → Run Script*, ou roda com `blender -b -P cena.py`.

```python
import bpy, math

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'            # ou 'BLENDER_EEVEE_NEXT' (rápido)
scene.cycles.samples = 128
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
scene.render.filepath = '//render.png'

def material(nome, cor, rough=0.5, metal=0.0):
    m = bpy.data.materials.new(nome); m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*cor, 1)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    return m

def hex2lin(h):  # hex sRGB -> RGB linear (Blender trabalha em linear)
    c = [int(h[i:i+2], 16)/255 for i in (1, 3, 5)]
    return tuple(x/12.92 if x <= 0.04045 else ((x+0.055)/1.055)**2.4 for x in c)

bpy.ops.mesh.primitive_plane_add(size=40)
bpy.context.object.data.materials.append(material('chao', hex2lin('#d8cfc0'), 0.9))

bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 1), segments=64, ring_count=32)
obj = bpy.context.object; bpy.ops.object.shade_smooth()
obj.modifiers.new('bevel', 'BEVEL')
obj.data.materials.append(material('obj', hex2lin('#e07a5f'), 0.3))

bpy.ops.object.light_add(type='AREA', location=(4, -4, 6)); luz = bpy.context.object
luz.data.energy = 1000; luz.data.size = 4
luz.rotation_euler = (math.radians(45), 0, math.radians(45))

bpy.ops.object.camera_add(location=(7, -7, 5)); cam = bpy.context.object
cam.data.lens = 50
c = cam.constraints.new('TRACK_TO'); c.target = obj
scene.camera = cam

world = bpy.data.worlds.new('mundo'); scene.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (*hex2lin('#f4efe6'), 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6

bpy.ops.render.render(write_still=True)
```

Dicas:
- Modificadores dão qualidade barata: `BEVEL` (cantos que pegam luz), `SUBSURF` (suavização), `SOLIDIFY` (espessura), `ARRAY` (repetição).
- Cores em hex precisam ser convertidas para linear (função `hex2lin`).
- Iluminação: uma Area Light grande e suave + HDRI ou World claro + uma luz de recorte atrás.
- Exportar para web/Three.js: `bpy.ops.export_scene.gltf(filepath='modelo.glb')`.
- Se o Blender não estiver disponível no ambiente, entregue o script e explique como rodar; não diga que renderizou.
