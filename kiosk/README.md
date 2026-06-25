# 🖥️ Quiosque Windows — Aura Dashboard

Transforma um PC com **Windows 10/11** em um **quiosque** que abre o Aura Dashboard
em tela cheia automaticamente, sem barras do navegador e sem deixar o usuário "sair"
do app.

A solução é um **navegador em modo `--kiosk`** (Edge ou Chrome) apontando para o
servidor Streamlit local (`http://localhost:8501`), com inicialização automática no
logon do Windows.

---

## 📦 O que tem nesta pasta

| Arquivo | Função |
|---|---|
| `INSTALAR_QUIOSQUE.bat` | **Comece por aqui.** Duplo-clique para instalar (pede admin sozinho). |
| `Install-Kiosk.ps1` | Instalador completo: Python, app, dependências, autostart e atalhos. |
| `Start-Kiosk.ps1` | Sobe o servidor e abre o navegador em tela cheia (modo quiosque). |
| `Stop-Kiosk.ps1` | Encerra o quiosque; com `-Uninstall` remove autostart e atalhos. |

---

## 🚀 Instalação (1 passo)

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
