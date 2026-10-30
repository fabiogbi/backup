# Fundamentos de Design

## Cor

**Montando uma paleta (regra 60-30-10):** 60% cor dominante (geralmente neutra/fundo), 30% secundária, 10% destaque.

Harmonias no círculo cromático (trabalhe em HSL — é mais fácil de ajustar):
- **Análoga** (matizes vizinhos, ±30°): calma, coesa. Ex.: natureza, bem-estar.
- **Complementar** (180°): contraste forte; use uma como destaque, não meio a meio.
- **Complementar dividida** (180° ±30°): contraste com mais equilíbrio.
- **Tríade** (120°): vibrante, lúdica; dessature duas delas.
- **Monocromática**: uma matiz, variando luminosidade/saturação — elegante e segura.

Truques:
- Sombras não são preto: escureça e desloque a matiz em direção ao azul/violeta. Realces: clareie e desloque para amarelo.
- Em vez de cinza puro, use neutros levemente tingidos pela cor dominante (ex.: `#1f2430` em vez de `#222`).
- Evite saturação 100% em áreas grandes.

Paletas prontas confiáveis:
- Terroso: `#264653 #2a9d8f #e9c46a #f4a261 #e76f51`
- Suave/retrô: `#3d405b #81b29a #f2cc8f #e07a5f #f4f1de`
- Noturno/tech: `#0b132b #1c2541 #3a506b #5bc0be #f0f3f5`
- Pastel: `#cdb4db #ffc8dd #ffafcc #bde0fe #a2d2ff`
- Corporativo: `#0f172a #1e40af #3b82f6 #e2e8f0 #f59e0b`

Psicologia (uso comum, não regra): azul = confiança/tecnologia; verde = natureza/saúde/finanças; vermelho = energia/urgência/comida; laranja = amigável/criativo; amarelo = otimismo; roxo = luxo/criatividade; preto = sofisticação.

## Tipografia

- No máximo 2 famílias: uma para títulos (personalidade), uma para texto (legibilidade).
- Escala modular (razão 1.25 ou 1.333): 12, 16, 20, 25, 31, 39, 49, 61…
- Altura de linha: 1.4–1.6 para texto, 1.1–1.2 para títulos grandes.
- Combinações seguras (Google Fonts): Playfair Display + Inter; Montserrat + Source Sans 3; Space Grotesk + Inter; DM Serif Display + DM Sans; Poppins + Lora.
- Em SVG standalone, a fonte pode não existir na máquina de quem abre: use pilhas com fallback (`font-family="Montserrat, Helvetica, Arial, sans-serif"`) ou converta texto de logos para paths quando a fidelidade importar.

## Composição

- **Regra dos terços**: posicione o foco nas interseções de uma grade 3×3.
- **Grade e alinhamento**: tudo alinha com algo. Use múltiplos de 8px.
- **Hierarquia**: tamanho > cor > peso > posição. Um elemento dominante por peça.
- **Proximidade**: itens relacionados juntos, grupos separados por espaço.
- **Repetição/ritmo**: reutilize formas, raios de canto, espessuras.
- **Contraste**: se dois elementos são diferentes, faça-os *bem* diferentes.
- **Caminho do olhar**: em Z (layouts com texto) ou F (leitura); oriente linhas e olhares de personagens para dentro da peça.

## Logos e identidade visual

- Deve funcionar em 16px (favicon) e em monocromático. Teste as duas coisas.
- Prefira um símbolo simples + logotipo. Evite detalhes finos, gradientes complexos e mais de 3 cores.
- Explore conceito: iniciais, metáfora visual do negócio, espaço negativo (ex.: uma letra que forma um objeto).
- Entregue: versão horizontal, versão símbolo, versão mono escura e clara, e paleta com hex.

## Estilos de ilustração (como obter cada um)

- **Flat**: formas sólidas, sem contorno ou com contorno uniforme, sombras como formas chapadas 10–15% mais escuras.
- **Line art**: só traços, `stroke-linecap="round"`, espessura única, poucas áreas preenchidas.
- **Isométrico**: eixos a 30°; em SVG use `transform="matrix(0.866,0.5,-0.866,0.5,0,0)"` para o topo, ou calcule pontos (x−y)·cos30, (x+y)·sin30 − z. Três tons por cor (topo claro, esquerda média, direita escura).
- **Low-poly**: polígonos facetados com sombreamento flat — use `scripts/render3d.py` ou Three.js com `flatShading: true`.
- **Retrô/vintage**: paleta dessaturada, textura de ruído (filtro `feTurbulence`), granulado, tipografia serifada.
- **Gradiente moderno/glassmorphism**: gradientes de malha (vários `radialGradient` borrados), cartões translúcidos com `backdrop-filter: blur()`.

## Formatos e tamanhos

| Uso | Tamanho |
|---|---|
| Post Instagram | 1080×1080 (ou 1080×1350 retrato) |
| Story/Reels | 1080×1920 |
| Capa YouTube / thumbnail | 1280×720 |
| Banner LinkedIn | 1584×396 |
| Favicon | 32×32, 180×180 (Apple), 512×512 |
| A4 impressão 300dpi | 2480×3508 |
| Cartão de visita 300dpi | 1050×600 (+3mm de sangria) |

## Checklist antes de entregar

- [ ] Paleta restrita, sem cores "default" cruas
- [ ] Um ponto focal claro
- [ ] Nada encostado nas bordas; margens consistentes
- [ ] Texto legível, contraste suficiente, sem cortes
- [ ] Luz/sombra coerentes
- [ ] Renderizado e conferido visualmente
