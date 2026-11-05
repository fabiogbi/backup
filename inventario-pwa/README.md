# Inventário Cego (PWA)

App web instalável em **iPhone e Android** para contagem cega de estoque com leitura de código de barras pela câmera. Os operadores contam sem ver o saldo do sistema; no fim, o app compara as contagens com a base importada e gera um **relatório HTML** com os KPIs.

Não há etapa de build nem dependência de loja de aplicativos. São arquivos estáticos (HTML, CSS e JavaScript).

## Estrutura

```
inventario-pwa/
├── index.html            # telas: Configurar, Contar, Relatório
├── styles.css
├── manifest.webmanifest  # instalação como app
├── sw.js                 # service worker (funciona offline)
├── js/
│   ├── core.js           # leitura do CSV, conciliação, KPIs, relatório HTML (sem DOM)
│   ├── db.js             # armazenamento local (IndexedDB)
│   ├── scanner.js        # leitura de código de barras pela câmera
│   └── app.js            # controle da interface
├── vendor/zxing.min.js   # biblioteca de leitura (ZXing 0.21.3), incluída para uso offline
├── icons/                # ícones PWA e apple-touch-icon
├── exemplo-base.csv      # base de exemplo
└── tests/core.test.js    # testes da lógica de conciliação
```

## Como rodar

**Requisito: HTTPS.** Câmera e instalação só funcionam em conexão segura (ou em `localhost`).

Para testar no computador:

```bash
cd inventario-pwa
python3 -m http.server 8000
# abra http://localhost:8000
```

Para usar nos celulares, publique a pasta em qualquer hospedagem estática com HTTPS (GitHub Pages, Netlify, Cloudflare Pages). O app não tem backend.

Testes da lógica:

```bash
npm test
```

## Instalação nos celulares

- **iPhone:** abra o endereço no **Safari** → botão Compartilhar → **Adicionar à Tela de Início**.
- **Android:** abra no **Chrome** → menu ⋮ → **Instalar app**.

Na primeira vez, aceite o acesso à câmera. Se negou, reative:
iPhone em *Ajustes › Safari › Câmera*; Android em *Configurações do Chrome › Permissões do site*.

## Fluxo de uso

1. **Configurar:** dê um nome ao inventário e importe a base (CSV).
2. **Contar** (cada operador no próprio aparelho):
   - Informe o nome do operador.
   - Aponte a câmera para o código, ou digite o código, ou use um leitor Bluetooth/USB.
   - Cada leitura soma a *quantidade por leitura* (padrão 1). É possível desfazer ou remover leituras.
   - A tela mostra descrição e o total lido do código, **nunca o saldo do sistema**.
3. **Juntar as contagens:** cada aparelho exporta seu CSV (*Configurar › Exportar leituras*). No aparelho do supervisor, importe todos (*Configurar › Importar leituras de outro aparelho*). Leituras repetidas são ignoradas.
4. **Relatório:** gere o HTML e compartilhe ou baixe. Também é possível exportar a conciliação item a item em CSV (abre no Excel).

## Formato da base (CSV)

Primeira linha = cabeçalho. Separador `;` ou `,` (detectado automaticamente). Codificação UTF-8 ou Windows-1252 (CSV do Excel brasileiro).

| Coluna | Obrigatória | Exemplo |
|---|---|---|
| `codigo` | sim | `7891000100103` |
| `saldo` | sim | `120` |
| `descricao` | não | `Arroz tipo 1 5kg` |
| `custo` | não | `22,90` |
| `local` | não | `Corredor A` |

Nomes de colunas aceitos também sem acento e em sinônimos (ex.: `ean`, `sku`, `quantidade`, `valor_unitario`, `endereco`).

**Atenção ao Excel:** formate a coluna de código como **texto**. Senão ele remove zeros à esquerda de EANs e os códigos não batem.

## Como é calculado

Para cada item da base: `diferença = contado − saldo do sistema`.

| Status | Regra |
|---|---|
| Conforme | diferença = 0 |
| Falta | diferença < 0 e foi contado |
| Sobra | diferença > 0 |
| Não contado | item da base sem nenhuma leitura |
| Não cadastrado | código lido que não existe na base |

KPIs principais:

- **Acuracidade (itens)** = itens conformes ÷ (itens da base + códigos não cadastrados).
- **Acuracidade (quantidade)** = 1 − (faltas + sobras) ÷ saldo total da base.
- **Faltas / sobras / diferença líquida** em unidades.
- **Valores** = quantidade × custo unitário (itens sem custo entram com R$ 0,00).
- **Desempenho:** leituras, unidades e códigos por operador; leituras por hora (com ≥ 1 min de contagem).
- **Por local:** acuracidade, faltas, sobras, não contados e diferença financeira.
- **Top 10 divergências** por impacto financeiro.

## Manutenção

- **Atualizar o app nos celulares:** ao mudar arquivos, aumente `VERSAO` em `sw.js`. Sem isso, o cache offline pode continuar servindo a versão antiga.
- **Dados ficam no aparelho** (IndexedDB). Limpar os dados do site do navegador apaga as contagens. Exporte antes de encerrar o inventário.

## Limitações conhecidas

- **Sem controle de acesso.** A tela de relatório não tem senha de supervisor. Em operação real, combine com o time que o relatório é gerado só no aparelho do supervisor.
- **Recontagem / 2ª rodada** não é separada: todas as leituras somam. Para comparar duas rodadas, exporte cada uma e trate fora do app.
- **Câmera:** a leitura foi validada em Chromium headless com câmera simulada. Ainda precisa de teste em iPhone e Android reais, com a iluminação do depósito.
- **Formatos de código** lidos: EAN-13, EAN-8, UPC-A, UPC-E, Code 128, Code 39 e ITF. QR Code não está habilitado.
