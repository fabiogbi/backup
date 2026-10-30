# 3D com Three.js

Para cenas 3D interativas, animações e visualização de produto. Entregue **um único arquivo HTML** que abre direto no navegador.

## Template base

```html
<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cena 3D</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#101522}canvas{display:block}</style>
<script type="importmap">
{ "imports": {
  "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
  "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
}}
</script>
</head>
<body>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color('#101522');
scene.fog = new THREE.Fog('#101522', 15, 40);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture; // reflexos realistas

const camera = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.1, 100);
camera.position.set(6, 4, 8);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.target.set(0, 1, 0);

// Iluminação de 3 pontos
const key = new THREE.DirectionalLight('#fff4e0', 2.5);
key.position.set(5, 8, 4); key.castShadow = true;
key.shadow.mapSize.set(2048, 2048); key.shadow.radius = 4;
Object.assign(key.shadow.camera, { left: -8, right: 8, top: 8, bottom: -8 });
scene.add(key);
const fill = new THREE.DirectionalLight('#a0c4ff', 0.6); fill.position.set(-6, 3, 2); scene.add(fill);
const rim = new THREE.DirectionalLight('#ffffff', 1.0); rim.position.set(0, 4, -8); scene.add(rim);
scene.add(new THREE.HemisphereLight('#bcd4ff', '#2a1f1a', 0.4));

// Chão que só recebe sombra
const ground = new THREE.Mesh(new THREE.PlaneGeometry(50, 50), new THREE.MeshStandardMaterial({ color: '#1a2133', roughness: 1 }));
ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; scene.add(ground);

// --- objetos da cena aqui ---
const mat = new THREE.MeshPhysicalMaterial({ color: '#e07a5f', roughness: 0.35, clearcoat: 0.6 });
const obj = new THREE.Mesh(new THREE.TorusKnotGeometry(0.8, 0.28, 200, 32), mat);
obj.position.y = 1.4; obj.castShadow = true; scene.add(obj);

const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const t = clock.getElapsedTime();
  obj.rotation.y = t * 0.5;
  controls.update();
  renderer.render(scene, camera);
});
addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
</script>
</body>
</html>
```

## Modelando com primitivas

Geometrias: `BoxGeometry`, `SphereGeometry`, `CylinderGeometry` (raio topo ≠ base vira cone/tronco), `ConeGeometry`, `TorusGeometry`, `CapsuleGeometry`, `IcosahedronGeometry` (detail 0–1 = low-poly), `LatheGeometry` (perfil girado: vasos, garrafas, copos), `ExtrudeGeometry` (forma 2D `THREE.Shape` extrudada, com `bevelEnabled` para cantos suaves: logos 3D, letras, peças), `TubeGeometry` (tubo ao longo de curva).

Agrupe peças em `THREE.Group` para montar objetos compostos (casa = corpo + telhado + porta + janelas) e mova o grupo inteiro.

Função utilitária útil:
```js
function part(geo, color, pos = [0,0,0], rot = [0,0,0], opts = {}) {
  const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color, roughness: 0.6, ...opts }));
  m.position.set(...pos); m.rotation.set(...rot.map(THREE.MathUtils.degToRad));
  m.castShadow = m.receiveShadow = true; return m;
}
```

## Materiais

- `MeshStandardMaterial`: padrão PBR. `roughness` (0 espelho → 1 fosco), `metalness` (0 ou 1 quase sempre).
- `MeshPhysicalMaterial`: vidro (`transmission: 1, thickness: 0.5, roughness: 0.05, ior: 1.5`), verniz (`clearcoat`), tecido (`sheen`).
- `MeshToonMaterial`: estilo cartoon/cel-shading (combine com contorno via `OutlineEffect`).
- `flatShading: true` para estética low-poly.
- Texto 3D: `TextGeometry` + `FontLoader` (fontes em `three/addons/../fonts/helvetiker_regular.typeface.json`).

## Estilos de cena

- **Low-poly fofo**: `IcosahedronGeometry(r, 0)` para árvores/pedras, `flatShading`, paleta pastel, sombras suaves, câmera ortográfica ou FOV baixo (~30).
- **Estúdio de produto**: fundo infinito (plano curvado ou cor sólida + `fog`), luz principal suave, `RoomEnvironment`, objeto girando devagar.
- **Isométrico/diorama**: `OrthographicCamera`, posição (10,10,10) olhando para a origem, base quadrada como "ilha".
- **Noturno/neon**: fundo escuro, `MeshStandardMaterial({ emissive, emissiveIntensity })` + pós-processamento `UnrealBloomPass`.

## Carregar e exportar modelos

- Importar: `GLTFLoader` (`.glb/.gltf`), `OBJLoader`, `STLLoader`.
- Exportar: `GLTFExporter` (para Blender/web), `STLExporter` (para impressão 3D). Ofereça um botão de download:
```js
import { STLExporter } from 'three/addons/exporters/STLExporter.js';
const stl = new STLExporter().parse(scene, { binary: true });
const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(new Blob([stl])), download: 'modelo.stl' }); a.click();
```

## Verificação

Se o ambiente tiver Playwright e acesso ao CDN, gere um screenshot (`node scripts/preview.js cena.html cena.png 1280 800 --wait 1500`) e confira. Sem acesso ao CDN, use o renderizador `scripts/render3d.py` para conferir a composição da cena (mesmas posições/cores) ou entregue o HTML e avise que não foi possível pré-visualizar.
