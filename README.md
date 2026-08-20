# NAS Backup — Passo a passo DETALHADO

Backup de fotos/vídeos do iPhone → NAS Ugreen, via Tailscale. Sem Mac necessário.

---

## PARTE 0 — O que já está pronto (feito por mim)

No seu NAS já existe rodando:
- Container Docker `iphonebackup` na porta **9120**
- Endpoint: `http://100.66.10.4:9120` (IP fixo do Tailscale)
- Salva em: `/home/Fabio/Fotos e vídeos/iPhoneBackup/fabio/<device>/<ano-mes>/`
- Auth: usuário `fabio`, senha `@Azul98verde`
- **Testado:** upload pela tailnet retornou 200 e salvou o arquivo ✅

Você NÃO precisa mexer no backend. Só confirmar que o container está de pé:
```bash
# no NAS (via SSH) ou pelo Hermes
docker ps --filter name=iphonebackup
```
Se estiver parado: `docker start iphonebackup`.

---

## PARTE 1 — Preparar o código no GitHub

O Flutter precisa ser compilado (build) num Mac. Como você não tem Mac, usamos o **Codemagic** (serviço na nuvem que tem Mac) pra gerar o IPA.

### 1.1 Criar conta GitHub
1. Acesse https://github.com e crie uma conta (ou use a sua).
2. Clique no **+** (canto superior direito) → **New repository**.
3. Nome: `nas-backup-iphone`
4. Deixe **Public** (ou Private, tanto faz).
5. Marque **Add a README** (opcional).
6. Clique **Create repository**.

### 1.2 Subir os arquivos
Você tem o `nas_backup_app.zip` que eu gerei. Para subir pro GitHub sem Git no computador:

**Opção A — Upload pela web (mais simples):**
1. No repo que criou, clique **Add file** → **Upload files**.
2. Extraia o ZIP no seu computador (duplo clique).
3. Arraste as pastas/arquivos: `lib/`, `pubspec.yaml`, `codemagic.yaml`, `exportOptions.plist`, `shortcut/`, `README.md`.
4. Clique **Commit changes**.

**Opção B — Via Git (se tiver Git instalado):**
```bash
git clone https://github.com/SEU_USUARIO/nas-backup-iphone.git
cd nas-backup-iphone
# copie os arquivos do ZIP extraído para cá
git add .
git commit -m "app inicial"
git push
```

---

## PARTE 2 — Build do IPA no Codemagic (sem Mac)

### 2.1 Conta Apple Developer
1. Acesse https://developer.apple.com e clique **Account** → faça login com seu Apple ID (`fabiogbi.gomes@gmail.com`).
2. Se nunca entrou, aceite o contrato gratuito. **Não precisa pagar** a taxa de US$99 para testar no seu próprio iPhone (modo "Development").
3. Anote seu **Team ID** (em Account → Membership → Team ID, ex.: `A1B2C3D4E5`).

### 2.2 App-Specific Password (senha do Codemagic)
1. Acesse https://appleid.apple.com → **Sign-In and Security** → **App-Specific Passwords** → **Generate**.
2. Nome: `codemagic`. Copie a senha gerada (`xxxx-xxxx-xxxx-xxxx`).

### 2.3 Certificado e Provisioning Profile (no Mac de alguém ou via Xcode Cloud?)
Como você não tem Mac, use o **Codemagic CLI / UI** para gerar o certificado:
1. No Codemagic, vá em **Teams** → sua conta → **Integrations** → **Apple Developer Portal**.
2. Conecte com APPLE_ID + APPLE_PASSWORD (app-specific).
3. O Codemagic pode **criar o certificado e o provisioning profile automaticamente** (opção "Automatic signing" ou "Create certificate").
   - Se preferir manual: em developer.apple.com → **Certificates** → **+** → **Apple Development** → upload do CSR que o Codemagic pede → baixe o `.cer` → exporte como `.p12` (senha qualquer).
   - **Profiles** → **+** → **iOS App Development** → selecione seu app (`com.fabiogomes.nasbackup`) → baixe o `.mobileprovision`.

### 2.4 Conectar Codemagic
1. Acesse https://codemagic.io → **Sign in with GitHub** (autorize o repo `nas-backup-iphone`).
2. Vá em **Settings** → **Integrations** → **Apple Developer Portal** (conecte com as credenciais da Parte 2.3).
3. Crie um **Codemagic YAML** (já está no repo como `codemagic.yaml`). O Codemagic lê automaticamente.
4. Defina as **Environment variables** (Settings → Environment variables → group `apple_credentials`):
   - `APPLE_ID` = `fabiogbi.gomes@gmail.com`
   - `APPLE_PASSWORD` = a app-specific password (Parte 2.2)
   - `APPLE_TEAM_ID` = seu Team ID (Parte 2.1)
   - `CERTIFICATE_P12` = conteúdo do `.p12` (codificado em base64 ou upload)
   - `CERTIFICATE_PRIVATE_KEY` = a chave privada do certificado
   - `PROVISIONING_PROFILE` = conteúdo do `.mobileprovision`

### 2.5 Rodar o build
1. No Codemagic, clique no seu app → **Start new build** → branch `main` → **Build**.
2. Aguarde ~10-15 min. O log mostra `flutter build ios` e `xcodebuild`.
3. Ao terminar: **Artifacts** → baixe o `nas_backup_app.ipa`. Ele também é enviado por email (configurado no yaml).

---

## PARTE 3 — Instalar no iPhone

### 3.1 Via TestFlight (se pagar a conta Apple)
1. No Codemagic, em vez de exportar IPA, use **publishing → TestFlight**.
2. No iPhone: App Store → TestFlight → aceite o convite → instale.

### 3.2 Via Sideload (conta gratuita) — método mais comum
O IPA da conta gratuita expira em 7 dias, mas você reinstala facilmente.
1. No computador, instale **Apple Configurator 2** (Mac) OU **Sideloadly** (Windows/Mac, https://sideloadly.io).
2. Conecte o iPhone no USB.
3. Sideloadly: selecione o IPA, digite seu Apple ID, clique **Start**.
4. No iPhone: **Ajustes** → **Geral** → **Gerenciamento de VPN e Dispositivo** → **Confiar** no seu ID.
5. Abra o app **NAS Backup**.

### 3.3 Permissões no iPhone
Ao abrir o app pela 1ª vez:
- Ele pede acesso a **Fotos** → toque **Todas as fotos**.
- Toque **Fazer backup agora** → envia as fotos novas pro NAS.

---

## PARTE 4 — Atalho iOS (gatilho 2h no mesmo local)

### 4.1 Importar o atalho
1. Envie o arquivo `NAS Backup.shortcut` para o iPhone (AirDrop do Mac, ou email, ou iCloud Drive).
2. Toque nele → **Adicionar** (app Atalhos).

### 4.2 Criar a automação "ficar 2h no mesmo local"
1. Abra o app **Atalhos** no iPhone.
2. Vá em **Automações** (aba inferior) → **+** (novo) → **Criar Automação Pessoal**.
3. Role e escolha **Tempo no local** (ou "Chegada/Saída" se preferir).
4. Toque em **Local** → escolha "Local Atual" ou um endereço fixo.
5. Em **Tempo**, escolha **2 horas** (ou "Após 2 horas").
6. Toque **Próximo** → **Adicionar Ação** → procure **Executar atalho** → selecione **NAS Backup**.
7. Toque no nome da automação (topo) e desligue **Perguntar antes de executar**.
8. **Concluído**.

Agora, quando você parar 2h num lugar, o iPhone envia as fotos pro NAS automaticamente (precisa de Tailscale ativo e WiFi/redeiros).

---

## PARTE 5 — Solução de problemas

| Sintoma | Causa provável | Solução |
|---------|---------------|---------|
| App não conecta | Tailscale desligado no iPhone | Abra o app Tailscale e ligue |
| Upload dá erro 401 | Senha errada | Confira `fabio` / `@Azul98verde` em `lib/main.dart` |
| Fotos não aparecem no NAS | Pasta errada | Confira `/home/Fabio/Fotos e vídeos/iPhoneBackup/` |
| IPA não instala | Certificado expirou (conta gratuita) | Refaça o build no Codemagic e reinstale |
| Atalho não dispara | "Perguntar antes" ligado | Desligue essa opção na automação |

---

## Resumo dos arquivos
- `lib/main.dart` — código do app
- `pubspec.yaml` — dependências
- `codemagic.yaml` — pipeline de build na nuvem
- `exportOptions.plist` — config de export do Xcode
- `shortcut/NAS Backup.shortcut` — atalho iOS
- `README.md` — resumo

Pronto. Qualquer dúvida em algum passo, me avise que eu detalho mais.
