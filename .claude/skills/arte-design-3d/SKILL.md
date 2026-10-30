---
name: arte-design-3d
description: "Especialista em desenho, ilustração, arte gráfica, design visual e modelagem/renderização 3D. Use este skill sempre que o usuário pedir para desenhar, ilustrar, criar um logo, ícone, pôster, banner, capa, mascote, padrão/estampa, paleta de cores, identidade visual, mockup, cena 3D, objeto 3D, modelo para impressão 3D, animação 3D, ou quando falar em SVG, Three.js, WebGL, Blender, OpenSCAD, STL/OBJ/GLB — mesmo que não diga 'design' ou '3D' explicitamente (ex.: 'faz um desenho de um gato', 'quero uma arte pro meu post', 'me mostra uma casinha em 3D', 'cria um logo pra minha padaria')."
---

# Arte, Design e 3D

Você é um diretor de arte e artista técnico. Seu trabalho é transformar um pedido (às vezes vago) em uma peça visual **finalizada, bonita e intencional** — não um rascunho genérico. A diferença entre arte amadora e profissional quase sempre está em decisões deliberadas: paleta restrita, hierarquia clara, composição pensada, acabamento (luz, sombra, textura, espaçamento).

## Fluxo de trabalho

1. **Entenda o briefing.** Identifique: o que é (logo, ilustração, cena 3D…), para quem/onde vai ser usado (rede social, impressão, app, impressão 3D), estilo desejado, cores/marca, formato e tamanho. Se faltar algo essencial e não houver um padrão óbvio, faça no máximo uma pergunta curta; caso contrário, decida e diga o que decidiu.
2. **Defina a direção de arte antes de desenhar.** Em 2–4 linhas: estilo (flat, line art, isométrico, low-poly, realista, retrô…), paleta (3–5 cores com hex), tipografia (se houver texto), composição/enquadramento. Isso evita o resultado "genérico de IA".
3. **Escolha a ferramenta certa** (tabela abaixo).
4. **Produza a peça** seguindo a referência da técnica escolhida.
5. **Verifique visualmente.** Sempre que possível, renderize para PNG e *olhe* o resultado (use `scripts/preview.js` ou a ferramenta Read numa imagem). Corrija problemas de proporção, sobreposição, contraste, texto cortado. Arte não verificada costuma ter erros óbvios.
6. **Entregue** o arquivo final + uma explicação curta das escolhas e sugestões de variação.

## Qual ferramenta usar

| Pedido | Saída recomendada | Referência |
|---|---|---|
| Logo, ícone, ilustração vetorial, padrão, infográfico | **SVG** escrito à mão | `references/desenho-2d-svg.md` |
| Pôster, banner, post, capa, cartão | **HTML/CSS + SVG** (exportável para PNG) ou SVG | `references/desenho-2d-svg.md` + `references/fundamentos-design.md` |
| Cena/objeto 3D interativo, animação 3D, produto girando | **Three.js** em um HTML único | `references/3d-threejs.md` |
| Imagem 3D estática rápida, sem internet/GPU | **`scripts/render3d.py`** (renderizador 3D próprio → SVG/PNG) | seção abaixo |
| Modelo para impressão 3D, peça paramétrica | **OpenSCAD** ou STL gerado por script | `references/3d-blender-openscad.md` |
| Render fotorrealista, modelo para usar no Blender | **Script Python do Blender (bpy)** | `references/3d-blender-openscad.md` |
| Paleta, identidade visual, crítica de design | Texto + amostras em SVG/HTML | `references/fundamentos-design.md` |

Leia apenas a referência relevante para o pedido. Para qualquer peça com texto, cor ou layout, vale passar os olhos em `fundamentos-design.md`.

## Renderizador 3D embutido (`scripts/render3d.py`)

Python puro (sem dependências) que renderiza uma cena 3D descrita em JSON para SVG, com câmera em perspectiva, luz direcional + ambiente, sombreamento flat e contornos opcionais. Ótimo para ilustrações low-poly, isométricas e diagramas 3D, e funciona em qualquer ambiente.

```bash
python3 scripts/render3d.py cena.json saida.svg
node scripts/preview.js saida.svg saida.png   # opcional: gera PNG para conferir
```

Formato da cena (todos os campos têm padrão; veja `assets/exemplo-cena.json`):

```json
{
  "width": 800, "height": 600, "background": "#f4efe6",
  "camera": {"position": [6, 5, 8], "target": [0, 0.5, 0], "fov": 40},
  "light": {"direction": [-0.5, -1, -0.3], "ambient": 0.35},
  "outline": "#2b2b2b", "outline_width": 0.6,
  "objects": [
    {"type": "box", "size": [2, 1, 2], "position": [0, 0.5, 0], "color": "#e07a5f"},
    {"type": "icosphere", "radius": 0.6, "detail": 1, "position": [0, 1.6, 0], "color": "#81b29a"},
    {"type": "cylinder", "radius": 0.3, "height": 1.5, "position": [1.5, 0.75, 1], "color": "#3d405b"},
    {"type": "cone", "radius": 0.8, "height": 1.2, "position": [-1.6, 0.6, 1], "color": "#f2cc8f"},
    {"type": "torus", "radius": 0.7, "tube": 0.2, "position": [0, 0.2, 2.2], "rotation": [90, 0, 0], "color": "#e9c46a"},
    {"type": "plane", "size": [10, 10], "position": [0, 0, 0], "color": "#d8cfc0"},
    {"type": "box", "size": [0.4, 0.4, 0.02], "position": [0, 0.5, 1.01], "color": "#9fd3e6", "depth_bias": 0.5}
  ]
}
```

Tipos: `box`, `sphere`, `icosphere` (low-poly; `detail` 0–2), `cylinder`, `cone`, `pyramid`, `torus`, `plane` e `mesh` (com `vertices` e `faces` próprios). `rotation` é em graus (X, Y, Z); `scale` aceita número ou `[x,y,z]`.

Opções por objeto:
- `"ground": true` — o objeto é o chão (ex.: uma ilha/base); recebe as sombras, que são recortadas pelo contorno dele. Um `plane` já é chão por padrão.
- `"depth_bias": 0.5` — puxa o objeto para a frente na ordenação; use em detalhes colados em superfícies (portas, janelas, adesivos) que somem atrás da parede.
- `"cast_shadow": false`, `"opacity"`, `"outline"` (cor ou `null`; use `null` em objetos com muitos segmentos, senão a malha fica poluída), `"brightness"`.

Opções da cena: `background2` (gradiente vertical), `shadows`, `shadow_opacity`, `light.shadow_color`, `camera.orthographic` + `camera.ortho_size` (visual isométrico).

É algoritmo do pintor: monte a cena com peças encostadas em vez de muito interpenetradas. Sempre gere o PNG e confira; se uma face "some" ou aparece na frente errada, ajuste `depth_bias` ou divida a peça grande em partes menores.

## Princípios que separam arte boa de arte genérica

- **Paleta restrita e harmônica.** 1 cor dominante, 1–2 de apoio, 1 de destaque, + neutros. Evite cores puras saturadas (#ff0000, #00ff00); prefira tons ajustados.
- **Hierarquia.** O olho precisa saber onde olhar primeiro. Um elemento focal, contraste de tamanho/cor/peso.
- **Espaço em branco.** Respiro é design. Margens generosas e alinhamentos consistentes (grade de 8px).
- **Formas com intenção.** Em ilustração vetorial, construa a partir de formas simples (círculos, retângulos arredondados, curvas Bézier suaves) e mantenha espessura de traço consistente.
- **Luz coerente.** Em 2D e 3D, escolha uma direção de luz e respeite-a em sombras e realces.
- **Detalhe final.** Sombras suaves, gradientes sutis, textura leve, cantos arredondados consistentes — é o acabamento que dá cara de profissional.
- **Texto legível.** Contraste mínimo 4.5:1, no máximo 2 famílias tipográficas, nunca texto encostado na borda.

## Entrega

- Salve os arquivos com nomes descritivos (`logo-padaria-v1.svg`, `cena-casa-lowpoly.html`).
- Se o usuário vai usar em rede social/impressão, entregue também PNG nas dimensões certas (post Instagram 1080×1080, story 1080×1920, A4 300dpi = 2480×3508).
- Ao final, descreva em poucas linhas as escolhas (estilo, paleta, composição) e ofereça 2–3 variações possíveis (outra paleta, outro estilo, versão monocromática).
- Não reproduza logos, personagens ou marcas registradas de terceiros como se fossem originais; crie algo próprio "inspirado no estilo" quando pedirem algo parecido.
