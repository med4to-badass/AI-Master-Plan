# 🖥️ Quiosque Windows — Aura Dashboard

Transforma um PC com **Windows 10/11** em um **quiosque** que abre o Aura Dashboard
em tela cheia automaticamente, sem barras do navegador e sem deixar o usuário "sair"
do app.

A solução é um **navegador em modo `--kiosk`** (Edge ou Chrome) apontando para o
servidor Streamlit local (`http://localhost:8501`), com inicialização automática no
logon do Windows.

---

Há **dois modos**:

- **A) Kiosk NATIVO do Windows (Assigned Access)** — recurso oficial do
  Windows que trava uma conta no Microsoft Edge apontando para o app. Mais
  robusto, sem watchdog. **Exige Windows Pro/Enterprise/Education** (não Home).
- **B) Kiosk de navegador** — abre Edge/Chrome em `--kiosk` com um watchdog que
  reabre se fechar. Funciona em **qualquer edição**, inclusive Home.

Em ambos, o servidor Streamlit (Python) roda localmente por trás.

## 📦 O que tem nesta pasta

| Arquivo | Função |
|---|---|
| `INSTALAR_QUIOSQUE.bat` | **Comece por aqui.** Instala pré-requisitos (Python, app, deps). |
| `Install-Kiosk.ps1` | Instalador de pré-requisitos + autostart/atalhos do modo B. |
| `Set-WindowsKiosk.ps1` | **Modo A:** configura o kiosk NATIVO (Assigned Access + Edge). |
| `Remove-WindowsKiosk.ps1` | Desfaz o kiosk nativo (modo A). |
| `Start-Server.ps1` | Sobe **apenas** o servidor (usado pelo modo A, no boot/SYSTEM). |
| `Start-Kiosk.ps1` | **Modo B:** sobe o servidor e abre o navegador em tela cheia. |
| `Stop-Kiosk.ps1` | Encerra o modo B; com `-Uninstall` remove autostart e atalhos. |
| `loading.html` | Tela de carregamento com a marca; redireciona ao app quando pronto. |

## ✨ Otimizações nativas (aplicadas automaticamente)

Para deixar a experiência o mais próxima de um app nativo:

- **Tela de carregamento** (`loading.html`): em vez do erro "não foi possível
  acessar", mostra um spinner com a marca **Aura** enquanto o servidor sobe e
  redireciona sozinho quando ele fica pronto. *(Padrão no modo B; no modo A use
  `-UseSplash`.)*
- **App sem "cara de web"**: a barra/menu do Streamlit fica em modo `minimal`
  (sem botões de deploy/rerun), via variáveis de ambiente — sem alterar o app.
- **Edge sem distrações** (modo A, via políticas de máquina): **sem
  preenchimento automático**, sem gerenciador de senhas, sem login/sync, sem
  tradução, sem recomendações e sem balões de aviso.
- **Energia**: tela e PC **nunca dormem** e **sem tela de bloqueio** — o painel
  fica sempre visível.
- **Menos consumo**: file-watcher desligado e telemetria off.

---

## 🅰️ Modo A — Kiosk NATIVO (recomendado para Pro/Enterprise/Education)

1. Instale os pré-requisitos: duplo-clique em **`INSTALAR_QUIOSQUE.bat`**
   (ou rode `Install-Kiosk.ps1`). Isso garante Python, app, venv e dependências
   em `C:\AuraKiosk`.
2. Abra o **PowerShell como Administrador** e rode:
   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass -Force
   C:\AuraKiosk\kiosk\Set-WindowsKiosk.ps1
   ```
   Isso cria a conta **`QuiosqueAura`** (sem senha), registra a tarefa
   **`AuraServer`** (sobe o servidor no boot, como SYSTEM) e aplica o
   **Assigned Access** (Edge travado em `localhost:8501`).
3. Faça **logoff** e entre como **`QuiosqueAura`** (ou reinicie). O Windows abre
   o Edge em modo kiosk, em tela cheia, travado no app.

**Remover o modo A:** `C:\AuraKiosk\kiosk\Remove-WindowsKiosk.ps1` (use
`-RemoveUser` para também apagar a conta).

Parâmetros úteis:
```powershell
.\Set-WindowsKiosk.ps1 -Port 8080
.\Set-WindowsKiosk.ps1 -KioskUser "Recepcao"
.\Set-WindowsKiosk.ps1 -Url "http://localhost:8501/"                 # dashboard
.\Set-WindowsKiosk.ps1 -Url "http://localhost:8501/?view=cliente&id=1"  # portal do cliente 1
.\Set-WindowsKiosk.ps1 -UseSplash    # mostra loading.html antes do app
```
> Por padrão o modo A abre o app **direto** (mais robusto no kiosk nativo). O
> servidor já sobe no **boot** (antes do logon), então normalmente já está
> pronto quando o Edge abre. Use `-UseSplash` se quiser a tela de carregamento.

> Se a aplicação automática falhar, dá pra fazer pela interface:
> *Configurações → Contas → Outros usuários → Configurar um quiosque →
> Microsoft Edge → URL `http://localhost:8501`* (o servidor já estará no ar
> pela tarefa `AuraServer`).

---

## 🅱️ Modo B — Kiosk de navegador (qualquer edição, inclusive Home)

1. Copie a pasta do projeto para o PC (ou deixe o instalador baixar do GitHub).
2. Entre na pasta `kiosk` e dê **duplo-clique em `INSTALAR_QUIOSQUE.bat`**.
   - Aceite o pedido de **Administrador**.
3. Aguarde: ele instala Python (se faltar), baixa o app, cria o ambiente e as
   dependências, registra a inicialização automática e cria os atalhos.
4. No final, responda **S** para iniciar o quiosque na hora.

A partir daí, **toda vez que o Windows fizer logon o quiosque abre sozinho**.

### Instalação manual (PowerShell como Admin)

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\Install-Kiosk.ps1                 # padrão: C:\AuraKiosk, branch main, porta 8501
.\Install-Kiosk.ps1 -AutoLogin      # também liga o login automático do Windows
.\Install-Kiosk.ps1 -Port 8080 -Branch main
```

---

## ▶️ Uso no dia a dia

- **Abrir agora:** atalho **“Aura Quiosque”** no Desktop / Menu Iniciar,
  ou: `powershell -ExecutionPolicy Bypass -File Start-Kiosk.ps1`
- **Sair do quiosque:** pressione **`Ctrl + Alt + K`** (encerra navegador e servidor).
- **Parar pelo script:** `powershell -ExecutionPolicy Bypass -File Stop-Kiosk.ps1`
- **Desinstalar quiosque** (mantém o app): `... Stop-Kiosk.ps1 -Uninstall`

---

## ⚙️ Como funciona

```
logon do Windows
      │
      ▼
Tarefa Agendada "AuraKiosk"  ──►  Start-Kiosk.ps1
                                      │
                                      ├─ inicia Streamlit (venv_win) em :8501
                                      ├─ aguarda /_stcore/health ficar OK
                                      └─ abre Edge/Chrome --kiosk em localhost:8501
                                             │
                                             └─ se o navegador fechar, reabre
```

- Servidor: `venv_win\Scripts\streamlit.exe run app.py --server.port 8501 --server.headless true`
- Navegador: modo `--kiosk` com perfil dedicado, sem barra de atualização, sem
  tradução, sem diálogos de erro, sem navegação por gesto.
- Watchdog: se o usuário conseguir fechar a janela, o `Start-Kiosk.ps1` a reabre.

---

## 🔒 Travamento extra (opcional, ambiente público)

Para um quiosque "de verdade" recomenda-se uma **conta de usuário dedicada** sem
privilégios e estas medidas:

1. **Login automático** dessa conta: `Install-Kiosk.ps1 -AutoLogin`
   (ou `netplwiz`). ⚠️ A senha fica no registro — use conta dedicada e sem dados.
2. **Bloquear teclas de fuga** (Win, Alt+Tab, Ctrl+Esc): instale o utilitário
   da Microsoft **Keyboard Filter** (recurso opcional do Windows Enterprise/IoT) ou
   um shell de quiosque.
3. **Assigned Access / Kiosk Mode nativo** do Windows: em *Configurações →
   Contas → Outros usuários → Configurar um quiosque* você pode amarrar a conta a
   um único app. Como aqui usamos navegador + servidor local, o método de
   navegador em `--kiosk` acima costuma ser mais flexível.
4. **Desativar gerenciador de tarefas / hotkeys** via Política de Grupo, se desejar.

---

## ❓ Problemas comuns

| Sintoma | Solução |
|---|---|
| "Python 3.9+ não encontrado" | O instalador baixa e instala sozinho; reinicie o PowerShell se pedir. |
| Tela em branco no navegador | O Streamlit ainda está subindo; aguarde alguns segundos. Veja se a porta 8501 está livre. |
| Não abre no logon | Verifique a Tarefa Agendada **AuraKiosk** em *Agendador de Tarefas*. |
| Edge/Chrome não encontrado | Instale o Microsoft Edge ou o Google Chrome. |
| Quero outra porta | Reinstale com `-Port <numero>` (atualiza a tarefa agendada). |

---

> App: **Aura Dashboard** (Streamlit). Repositório: `med4to-badass/AI-Master-Plan`.
