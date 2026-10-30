# Impressão 3D na Creality K2 Pro + Creality Print

Guia para criar peças e arte 3D que imprimem bem de primeira na K2 Pro, inclusive multicoloridas com o CFS.

> Nome do software: o fatiador oficial da Creality se chama **Creality Print** (versão 6.x para a série K2). "Creality Studio" é o nome usado para o software de gravadoras a laser da Creality. Se o usuário disser "Creality Studio" falando da K2 Pro, ele quer dizer o Creality Print. Trate isso com naturalidade, sem corrigi-lo de forma pedante.

## Índice
1. Especificações da K2 Pro
2. Fluxo de trabalho: do desenho à impressão
3. Regras de design para FDM
4. Design multicolorido (CFS)
5. Tipos de peça e receitas
6. Materiais e configurações sugeridas
7. Checklist antes de entregar

## 1. Especificações da K2 Pro

| Item | Valor |
|---|---|
| Volume de impressão | **300 × 300 × 300 mm** |
| Velocidade / aceleração máx. | 600 mm/s / 20.000 mm/s² |
| Bico | até 300 °C, padrão 0,4 mm |
| Mesa | até 110 °C |
| Câmara | aquecida ativamente até ~60 °C (bom para ABS/ASA) |
| Multicor | CFS (Creality Filament System): 4 cores por unidade, até **16 cores** com 4 CFS |
| Outros | nivelamento automático, câmeras com IA para monitorar a impressão |

Deixe uma margem: projete peças com até **~290 mm** por eixo. Se for maior, divida em partes com encaixes (pinos de 5 mm com folga de 0,2 mm, ou cauda-de-andorinha).

Confirme esses valores no perfil "K2 Pro" do Creality Print se o usuário mencionar outra versão ou outra impressora da série K2 (K2 Plus = 350 mm³, por exemplo).

## 2. Fluxo de trabalho

1. **Projeto**: gere o modelo com `scripts/modelo3d.py` (peças simples, placas, chaveiros, letreiros, litofanias, vasos), OpenSCAD (peças paramétricas/funcionais com furos e subtrações) ou Blender (formas orgânicas, esculturas).
2. **Verificação**: rode `check(partes)` para conferir se cabe na mesa e se a malha está fechada. Gere a prévia (`preview()` + `render3d.py … .png`) e **olhe a imagem**.
3. **Exportação**:
   - **1 cor** → `.stl` (ou `.3mf`).
   - **Várias cores** → `.3mf` com **uma parte por cor** (`export_3mf`). As partes ficam juntas como um único objeto, já posicionadas.
4. **No Creality Print** (o usuário faz):
   - Selecionar a impressora **Creality K2 Pro** e o bico de 0,4 mm.
   - Arquivo → **Abrir projeto/Importar** o `.3mf` ou `.stl`.
   - Sincronizar os filamentos do CFS (os slots são lidos automaticamente; confira tipo e cor).
   - Na lista de objetos, atribuir a cada **parte** o filamento/slot correto (as cores sugeridas no 3MF servem de referência visual; se não vierem, atribua manualmente).
   - Alternativa: usar a ferramenta de **pintura de cores** do Creality Print para colorir faces de um STL de uma cor só. Funciona, mas é menos preciso do que entregar partes separadas.
   - Fatiar, conferir a pré-visualização camada por camada (trocas de cor, suportes, tempo, filamento de purga) e enviar por Wi-Fi/Creality Cloud ou pendrive.
5. **Entrega**: explique em passos curtos o que o usuário precisa fazer no Creality Print (qual parte vai em qual cor, se precisa de suporte, material e tempo esperado).

Sem acesso ao Creality Print no ambiente, não diga que fatiou ou estimou tempo exato; diga que são estimativas.

## 3. Regras de design para FDM (bico 0,4 mm)

| Regra | Valor |
|---|---|
| Parede mínima | 0,8 mm (2 linhas); preferível 1,2–1,6 mm |
| Detalhe em relevo/baixo-relevo | altura ≥ 0,6 mm (3 camadas de 0,2), largura ≥ 0,8 mm |
| Texto em relevo | letras ≥ 5 mm de altura, traço ≥ 0,8 mm, fonte sem serifa e "grossa" |
| Furo para chaveiro/argola | Ø 4–5 mm, ≥ 2,5 mm de material em volta |
| Folga de encaixe | 0,2 mm (justo) a 0,3 mm (livre); print-in-place 0,4 mm |
| Furos verticais | saem ~0,1–0,2 mm menores: compense no diâmetro |
| Balanço (overhang) | até 45° sem suporte; acima disso, chanfre ou suporte em árvore |
| Pontes | até ~30–50 mm sem suporte em PLA |
| Base | face plana grande em Z=0; cantos inferiores com chanfro de 0,4–0,6 mm evitam pé de elefante |
| Pinos finos/altos | evite proporção altura/largura > 8:1 sem reforço |

Orientação: deite a peça para a maior face plana tocar a mesa. Lembre que as camadas são o ponto fraco: forças paralelas às camadas quebram a peça. Para texto e detalhes, prefira que fiquem virados **para cima**.

## 4. Design multicolorido (CFS)

Cada troca de cor exige recolher o filamento e purgar, o que gasta **tempo e filamento**. Peças multicor bem projetadas reduzem trocas:

- **Cor por altura (a mais barata)**: base de uma cor, relevo de outra em cima. Só há troca nas camadas onde as duas cores coexistem. É ideal para chaveiros, placas, letreiros, ímãs, porta-copos e logos.
- **Relevo com espessura mínima de cor**: 0,6–1,0 mm de relevo é suficiente para ler a cor. Mais alto = mais camadas com troca.
- **Cor embutida ("inlay") nivelada**: o detalhe colorido ocupa as primeiras 0,4–0,6 mm da face que fica na mesa (impressa de cabeça para baixo). A face da mesa fica lisa e brilhante. Muito usado em placas e logos.
- **Limite de cores por camada**: prefira 2–4 cores por peça. Cada cor extra na mesma camada multiplica as trocas.
- **Cores claras sobre escuras** precisam de mais purga. Ordene os slots e, se possível, desenhe a cor clara embaixo.
- **Torre de purga**: o Creality Print cria uma automaticamente. Deixe espaço livre na mesa e sugira "purgar no preenchimento" para economizar.
- **Partes separadas = precisão**: gere uma malha para cada cor, encostadas (sem vãos) e sem sobreposição nas regiões visíveis. O relevo deve começar exatamente no topo da base (`z0` = espessura da base).

## 5. Tipos de peça e receitas (com `modelo3d.py`)

```python
import sys; sys.path.insert(0, "<caminho-do-skill>/scripts")
from modelo3d import *
```

**Chaveiro / tag com relevo bicolor**
```python
base = extrude(rounded_rect(50, 30, 6), 3, holes=[[(x - 19, y) for x, y in circle(2.5, 32)]])
icone = extrude(star(5, 11, 5), 1.0).moved(4, 0, 3)            # começa no topo da base
partes = [("base", base, "#1f2430"), ("icone", icone, "#f2cc8f")]
check(partes); export_3mf(partes, "chaveiro.3mf")
```

**Placa/letreiro com borda**: base `rounded_rect` + borda (`extrude(contorno, 1, holes=[contorno_interno])`) + símbolo em relevo, cada um com sua cor.

**Logo 3D a partir de SVG**: converta os paths do SVG em polígonos (amostrando curvas Bézier em pontos; escala em mm), use `extrude` em cada forma e passe os recortes internos (ex.: o miolo de um "O") em `holes`. Para SVGs complexos, OpenSCAD é mais robusto: `linear_extrude(2) import("logo.svg");`.

**Texto**: `modelo3d.py` não tem fontes. Use OpenSCAD (`linear_extrude(1) text("Ana", size=10, font="Liberation Sans:style=Bold");`) ou a ferramenta de texto do Creality Print, se a versão do usuário tiver. Para algumas letras grandes e simples, dá para desenhar os polígonos à mão.

**Litofania** (foto que aparece contra a luz): `heightmap(grade, cell=0.25, base=0.8, height=2.2)`, com valores 0..1 em que 1 = pixel escuro (mais grosso). Imprima **em pé**, em PLA branco, com 100% de preenchimento e camada de 0,12 mm. Para converter uma imagem em grade sem bibliotecas, use PGM/PPM, ou Pillow se estiver disponível.

**Vaso/luminária**: `extrude(perfil, altura, scale_top=…)` ou `cylinder(r, h, r_top=…)`. No Creality Print, use o **modo vaso (espiral)** com uma parede só: o modelo pode ser um sólido fechado.

**Escultura/figura**: modele no Blender (ver `3d-blender-openscad.md`), exporte em STL e verifique os balanços. Sugira suporte em árvore e orientação.

**Miniaturas/dioramas low-poly**: monte com `box`, `cone`, `sphere(r, detail=1)` e `union`, cada cor como parte. O mesmo estilo do `render3d.py` serve de arte conceitual antes de imprimir.

## 6. Materiais e configurações sugeridas

| Material | Bico | Mesa | Câmara | Uso |
|---|---|---|---|---|
| PLA / PLA Silk / PLA Matte | 200–220 °C | 55–60 °C | aberta/sem aquecer | arte, decoração, multicor (melhor escolha) |
| PETG | 230–250 °C | 70–80 °C | sem aquecer | peças funcionais, resistência à umidade |
| ABS / ASA | 240–260 °C | 90–100 °C | **40–60 °C** | peças externas e com calor; aproveite a câmara aquecida |
| TPU (flexível) | 220–230 °C | 40–50 °C | – | capas, pneus; normalmente fora do CFS (carretel externo) |
| PLA-CF / PETG-CF / PA-CF | conforme fabricante | | aquecida | rigidez; bico endurecido |

Partida para arte/decoração em PLA: camada 0,16–0,2 mm, 2–3 paredes, 15% de preenchimento gyroid, camada inicial 0,2 mm. Para acabamento de topo, use "passar a ferro" (ironing) em placas e letreiros. Comece com os perfis do Creality Print para a K2 Pro e só ajuste se houver motivo.

## 7. Checklist antes de entregar

- [ ] Cabe em 300 × 300 × 300 mm (idealmente ≤ 290 mm)
- [ ] Peça apoiada em Z = 0 com face plana na mesa
- [ ] Paredes ≥ 0,8 mm, relevos ≥ 0,6 mm, textos ≥ 5 mm
- [ ] Malhas fechadas (`check`)
- [ ] Multicor: uma parte por cor, encostadas, poucas cores por camada
- [ ] Prévia renderizada e conferida visualmente
- [ ] Instruções curtas para o Creality Print (cor de cada parte, suporte, material)
