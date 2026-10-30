# Desenho 2D em SVG

SVG é a melhor ferramenta para desenhar com código: vetorial, escalável, editável no Figma/Illustrator/Inkscape, e vira PNG facilmente.

## Estrutura base

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800" width="800" height="800">
  <defs>
    <!-- gradientes, filtros, clipPaths, símbolos reutilizáveis -->
  </defs>
  <rect width="100%" height="100%" fill="#f4f1de"/>   <!-- fundo -->
  <g id="cena"> ... </g>
</svg>
```

- Sempre use `viewBox`; pense numa grade (ex.: 800×800 com margens de 64).
- Organize por camadas com `<g id="...">`: fundo → sombras → corpo → detalhes → realces → texto.
- Reutilize com `<symbol>`/`<use>` e `transform`.

## Construindo formas orgânicas

O segredo de ilustrações bonitas são curvas Bézier suaves.

- `M x y` move; `L` linha; `C c1x c1y c2x c2y x y` cúbica; `Q cx cy x y` quadrática; `S`/`T` continuam a curva com tangente suave; `A rx ry rot large sweep x y` arco; `Z` fecha.
- Para continuidade suave, o ponto de controle de saída deve estar alinhado (colinear) com o de entrada do mesmo nó.
- Comece com formas primitivas (círculo, elipse, `rect` com `rx`) e só depois parta para paths.
- Para personagens: cabeça grande, corpo simples, olhos com um ponto branco de brilho, bochechas com elipse rosada de baixa opacidade — fica fofo e expressivo.

Exemplo de folha:
```svg
<path d="M0 0 C 30 -40, 90 -40, 120 0 C 90 40, 30 40, 0 0 Z" fill="#81b29a"/>
<path d="M0 0 Q 60 -4 120 0" stroke="#5a8f75" stroke-width="3" fill="none" stroke-linecap="round"/>
```

Para formas complexas e repetitivas (padrões, mandalas, estrelas, ondas, flores, cidades), **gere o SVG com um script** (Python/JS) usando trigonometria em vez de escrever coordenadas à mão:
```python
import math
pts = []
for i in range(10):
    r = 100 if i % 2 == 0 else 45
    a = math.radians(-90 + i * 36)
    pts.append(f"{400 + r*math.cos(a):.1f},{400 + r*math.sin(a):.1f}")
print(f'<polygon points="{" ".join(pts)}" fill="#e9c46a"/>')
```

## Acabamento

Gradientes:
```svg
<linearGradient id="ceu" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#1c2541"/><stop offset="1" stop-color="#5bc0be"/>
</linearGradient>
<radialGradient id="brilho" cx="0.35" cy="0.3" r="0.7">
  <stop offset="0" stop-color="#fff" stop-opacity=".6"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
</radialGradient>
```

Sombra suave:
```svg
<filter id="sombra" x="-20%" y="-20%" width="140%" height="140%">
  <feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#1f2430" flood-opacity=".25"/>
</filter>
```

Textura de granulado (estilo retrô/risografia):
```svg
<filter id="grao">
  <feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/>
  <feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 .12 0"/>
  <feComposite in2="SourceGraphic" operator="in"/>
</filter>
<rect width="100%" height="100%" filter="url(#grao)"/>
```

Sombras de forma (estilo flat): duplique a forma, escureça 15%, recorte com `clipPath` pela forma original e desloque.

Contorno uniforme: `stroke-width` constante, `stroke-linejoin="round" stroke-linecap="round"`, e `vector-effect="non-scaling-stroke"` se for escalar grupos.

## Peças com layout (pôster, post, banner)

Use HTML/CSS quando houver muito texto ou layout responsivo; SVG quando for mais ilustrativo. Em HTML:
- Container com tamanho fixo exato (`width:1080px;height:1080px`) para exportar.
- Fontes do Google Fonts via `<link>`; espere carregarem antes do screenshot.
- Exporte para PNG com `scripts/preview.js arquivo.html saida.png 1080 1080`.

## Exportação e verificação

```bash
node scripts/preview.js desenho.svg desenho.png          # usa tamanho do SVG
node scripts/preview.js poster.html poster.png 1080 1350  # largura altura
```
Depois abra o PNG com a ferramenta Read para conferir visualmente. Corrija e re-renderize até ficar bom.
