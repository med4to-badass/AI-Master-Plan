#!/usr/bin/env python3
"""
SETUP_COMPLETO.py — AuraOS / Dashboard Parceiro Isopor
Instala ferramentas, dependências, drivers ASUS e softwares de lazer/utilidade/organização.

Execute como Administrador:
    python SETUP_COMPLETO.py
"""

import ctypes
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

# ─── Cores ANSI ─────────────────────────────────────────────────────────────────────
if sys.platform == "win32":
    os.system("color")  # habilita ANSI no cmd.exe

CY = "\033[96m"
GR = "\033[92m"
YL = "\033[93m"
RD = "\033[91m"
MG = "\033[95m"
WH = "\033[97m"
GY = "\033[90m"
RS = "\033[0m"


def step(msg): print(f"\n{CY}[►] {msg}{RS}")
def ok(msg):   print(f"  {GR}[OK] {msg}{RS}")
def warn(msg): print(f"  {YL}[!]  {msg}{RS}")
def fail(msg): print(f"  {RD}[X]  {msg}{RS}")
def info(msg): print(f"  {GY}     {msg}{RS}")


# ─── Helpers ────────────────────────────────────────────────────────────────────
def winget(app_id: str, nome: str, source: str = ""):
    """Instala um pacote via winget, tolerante a já instalado."""
    print(f"  -> {nome}...", end="", flush=True)
    cmd = [
        "winget", "install", "--id", app_id,
        "--silent", "--accept-package-agreements", "--accept-source-agreements",
    ]
    if source:
        cmd += ["--source", source]
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="ignore")
    out = (r.stdout + r.stderr).lower()
    if r.returncode == 0 or "already installed" in out or "já instalado" in out:
        ok(nome)
    else:
        warn(f"{nome} não instalado (cód {r.returncode}) — instale manualmente")


def ps(command: str) -> str:
    """Executa um comando PowerShell e retorna stdout limpo."""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, encoding="utf-8", errors="ignore",
    )
    return r.stdout.strip()


def criar_atalho(nome: str, target: str, args: str, desc: str):
    """Cria atalho .lnk no Desktop via PowerShell (here-string evita conflitos de aspas)."""
    shortcut = str(desktop / f"{nome}.lnk")
    script = (
        f"$wsh = New-Object -ComObject WScript.Shell\n"
        f"$lnk = $wsh.CreateShortcut(@'\n{shortcut}\n'@)\n"
        f"$lnk.TargetPath  = @'\n{target}\n'@\n"
        f"$lnk.Arguments   = @'\n{args}\n'@\n"
        f"$lnk.Description = @'\n{desc}\n'@\n"
        f"$lnk.Save()\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1",
                                     delete=False, encoding="utf-8") as f:
        f.write(script)
        tmp = f.name
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", tmp],
            capture_output=True,
        )
        if r.returncode == 0:
            ok(f"Atalho: {nome}")
        else:
            warn(f"Atalho '{nome}' não criado")
    finally:
        os.unlink(tmp)


# ───────────────────────────────────────────────────────────────────────
#  Banner
# ───────────────────────────────────────────────────────────────────────
os.system("cls" if sys.platform == "win32" else "clear")
print(f"""{MG}
╔══════════════════════════════════════════════════════════╗
║   SETUP COMPLETO — AuraOS                             ║
║   Dev • Lazer • Utilidades • Organização • ASUS 2x      ║
╚══════════════════════════════════════════════════════════╝
{RS}""")


# ───────────────────────────────────────────────────────────────────────
#  1. Verificações iniciais
# ───────────────────────────────────────────────────────────────────────
step("Verificações iniciais")

if sys.platform != "win32":
    fail("Este script é exclusivo para Windows.")
    sys.exit(1)

if not ctypes.windll.shell32.IsUserAnAdmin():
    fail("Execute como Administrador: clique com botão direito → Executar como administrador")
    input("Pressione Enter para sair...")
    sys.exit(1)
ok("Rodando como Administrador")

try:
    socket.getaddrinfo("one.one.one.one", 80)
    ok("Internet OK")
except OSError:
    fail("Sem conexão com a internet. Verifique e tente novamente.")
    input()
    sys.exit(1)

# Desktop real (trata OneDrive redirect)
desktop = Path(ps("[Environment]::GetFolderPath('Desktop')"))
if not desktop.exists():
    desktop = Path(os.path.expanduser("~")) / "Desktop"


# ───────────────────────────────────────────────────────────────────────
#  2. winget
# ───────────────────────────────────────────────────────────────────────
step("Verificando / atualizando winget")

if subprocess.run(["winget", "--version"], capture_output=True).returncode != 0:
    warn("winget não encontrado. Instale o App Installer pela Microsoft Store e tente novamente.")
    input()
    sys.exit(1)

subprocess.run(
    ["winget", "source", "update", "--disable-interactivity"],
    capture_output=True,
)
ok("winget pronto")


# ───────────────────────────────────────────────────────────────────────
#  3. Ferramentas de desenvolvimento
# ───────────────────────────────────────────────────────────────────────
step("Ferramentas de desenvolvimento")

winget("Git.Git",                     "Git")
winget("Python.Python.3.11",          "Python 3.11")
winget("OpenJS.NodeJS.LTS",           "Node.js LTS")
winget("Microsoft.VisualStudioCode",  "VS Code")
winget("GitHub.cli",                  "GitHub CLI (gh)")
winget("Microsoft.WindowsTerminal",   "Windows Terminal")
winget("7zip.7zip",                   "7-Zip")
winget("Cloudflare.cloudflared",      "Cloudflared (tunnel / serve.sh)")


# ───────────────────────────────────────────────────────────────────────
#  4. LAZER
# ───────────────────────────────────────────────────────────────────────
step("LAZER — Games, música, streaming e comunicação")

winget("Valve.Steam",                  "Steam")
winget("EpicGames.EpicGamesLauncher",  "Epic Games Launcher")
winget("Discord.Discord",              "Discord")
winget("Spotify.Spotify",             "Spotify")
winget("VideoLAN.VLC",                "VLC Media Player")
winget("OBSProject.OBSStudio",        "OBS Studio (streaming/gravação)")
winget("Google.Chrome",               "Google Chrome")
winget("WhatsApp.WhatsApp",           "WhatsApp")
winget("Telegram.TelegramDesktop",    "Telegram")


# ───────────────────────────────────────────────────────────────────────
#  5. UTILIDADES
# ───────────────────────────────────────────────────────────────────────
step("UTILIDADES — Sistema, hardware e produção")

winget("Microsoft.PowerToys",                 "Microsoft PowerToys")
winget("Notepad++.Notepad++",                 "Notepad++")
winget("CPUID.CPU-Z",                         "CPU-Z")
winget("HWiNFO.HWiNFO",                       "HWiNFO64")
winget("CrystalDewWorld.CrystalDiskInfo",     "CrystalDiskInfo (saúde dos SSDs/HDDs)")
winget("ALCPU.CoreTemp",                      "Core Temp")
winget("ShareX.ShareX",                       "ShareX (capturas e GIFs)")
winget("voidtools.Everything",                "Everything (busca instantânea de arquivos)")
winget("Piriform.CCleaner",                   "CCleaner")
winget("Bitwarden.Bitwarden",                 "Bitwarden (gerenciador de senhas)")
winget("qBittorrent.qBittorrent",             "qBittorrent")
winget("Adobe.Acrobat.Reader.64-bit",         "Adobe Acrobat Reader")
winget("WinSCP.WinSCP",                       "WinSCP (FTP/SFTP)")
winget("Google.GoogleDrive",                  "Google Drive")


# ───────────────────────────────────────────────────────────────────────
#  6. ORGANIZAÇÃO
# ───────────────────────────────────────────────────────────────────────
step("ORGANIZAÇÃO — Notas, tarefas e produtividade")

winget("Notion.Notion",              "Notion")
winget("Obsidian.Obsidian",          "Obsidian (segundo cérebro)")
winget("Doist.Todoist",              "Todoist")
winget("Microsoft.To-Do",            "Microsoft To Do")
winget("Atlassian.Trello",           "Trello")
winget("SlackTechnologies.Slack",    "Slack")
winget("Zoom.Zoom",                  "Zoom")
winget("Mozilla.Thunderbird",        "Thunderbird (e-mail)")
winget("Canva.Canva",               "Canva")


# ───────────────────────────────────────────────────────────────────────
#  7. Pacotes Python (requirements.txt do projeto)
# ───────────────────────────────────────────────────────────────────────
step("Pacotes Python (streamlit, plotly, pandas, Pillow, reportlab...)")

python_cmd = None
for cmd in ("python", "python3", "py"):
    try:
        r = subprocess.run([cmd, "--version"], capture_output=True,
                           text=True, encoding="utf-8", errors="ignore")
        ver_str = (r.stdout + r.stderr).strip()
        if r.returncode == 0 and "Python 3." in ver_str:
            python_cmd = cmd
            info(f"Usando: {ver_str}")
            break
    except FileNotFoundError:
        pass

PYTHON_PKGS = [
    "streamlit>=1.32",
    "plotly>=5.18",
    "pandas>=2.0",
    "openpyxl>=3.1",
    "requests>=2.31",
    "Pillow>=10.0",
    "reportlab>=4.0",
]

if python_cmd:
    for pkg in PYTHON_PKGS:
        name = pkg.split(">=")[0]
        print(f"  -> {name}...", end="", flush=True)
        r = subprocess.run(
            [python_cmd, "-m", "pip", "install", pkg, "--quiet", "--upgrade"],
            capture_output=True,
        )
        if r.returncode == 0:
            ok(name)
        else:
            warn(f"{name} (verifique manualmente)")
else:
    warn("Python não encontrado no PATH. Reinicie o terminal e rode: pip install -r requirements.txt")


# ───────────────────────────────────────────────────────────────────────
#  8. Node.js — IsoSolues-MKT
# ───────────────────────────────────────────────────────────────────────
step("Node.js — http-server para IsoSolues-MKT")

try:
    print("  -> http-server (global)...", end="", flush=True)
    r = subprocess.run(
        ["npm", "install", "-g", "http-server", "--silent"],
        capture_output=True,
    )
    if r.returncode == 0:
        ok("http-server")
    else:
        warn("http-server: falha — rode manualmente: npm install -g http-server")
except FileNotFoundError:
    warn("npm não está no PATH ainda. Reinicie o terminal e rode: npm install -g http-server")


# ───────────────────────────────────────────────────────────────────────
#  9. ASUS Dispositivo 1 — Placa-mãe (ROG / TUF / Prime)
# ───────────────────────────────────────────────────────────────────────
step("ASUS Dispositivo 1 — Placa-mãe (ROG / TUF / Prime)")

winget("ASUS.DriverHub", "ASUS DriverHub (gerenciador oficial de drivers)")

# Armoury Crate — tenta Microsoft Store, depois winget direto
print("  -> ASUS Armoury Crate...", end="", flush=True)
r = subprocess.run(
    ["winget", "install", "--id", "9PM9DSXH6Z5K", "--source", "msstore",
     "--accept-package-agreements", "--accept-source-agreements"],
    capture_output=True, text=True, encoding="utf-8", errors="ignore",
)
out = (r.stdout + r.stderr).lower()
if r.returncode == 0 or "already installed" in out:
    ok("ASUS Armoury Crate")
else:
    r2 = subprocess.run(
        ["winget", "install", "--id", "ASUS.ArmouryCrate", "--silent",
         "--accept-package-agreements", "--accept-source-agreements"],
        capture_output=True, text=True, encoding="utf-8", errors="ignore",
    )
    out2 = (r2.stdout + r2.stderr).lower()
    if r2.returncode == 0 or "already installed" in out2:
        ok("ASUS Armoury Crate")
    else:
        warn("Armoury Crate: instale manualmente em https://rog.asus.com/br/armoury-crate/")

# Chipset — detecta Intel vs AMD
print()
print(f"  {YL}Detectando CPU para drivers de chipset...{RS}")
cpu = ps("(Get-CimInstance Win32_Processor).Name")
info(f"CPU: {cpu}")

if "Intel" in cpu:
    winget("Intel.IntelDriverAndSupportAssistant",
           "Intel DSA (chipset, LAN, USB, Wi-Fi automático)")
elif "AMD" in cpu or "Ryzen" in cpu:
    winget("AMD.AMDChipsetSoftware", "AMD Chipset Software")

winget("RealtekSemiconductorCorp.RealtekAudioControl", "Realtek Audio Control")


# ───────────────────────────────────────────────────────────────────────
#  10. ASUS Dispositivo 2 — GPU (ROG Strix / TUF Gaming)
# ───────────────────────────────────────────────────────────────────────
step("ASUS Dispositivo 2 — GPU ASUS (ROG Strix / TUF Gaming)")

winget("ASUS.GPUTweakIII", "ASUS GPU Tweak III (OC, monitoramento, Aura Sync GPU)")

print()
print(f"  {YL}Detectando GPU...{RS}")
gpu = ps(
    "(Get-CimInstance Win32_VideoController "
    "| Where-Object { $_.Name -notmatch 'Microsoft Basic' } "
    "| Select-Object -First 1).Name"
)
info(f"GPU: {gpu}")

if any(k in gpu for k in ("NVIDIA", "GeForce", "RTX", "GTX")):
    winget("Nvidia.GeForceExperience", "NVIDIA GeForce Experience")
elif any(k in gpu for k in ("AMD", "Radeon", "RX ")):
    winget("AMD.AdrenalinEdition", "AMD Radeon Software Adrenalin")
else:
    warn(f"GPU '{gpu}' não reconhecida automaticamente — use o ASUS DriverHub")


# ───────────────────────────────────────────────────────────────────────
#  11. Clonar repositórios
# ───────────────────────────────────────────────────────────────────────
step("Clonando / atualizando repositórios")

REPOS = [
    (
        "https://github.com/med4to-badass/AI-Master-Plan.git",
        desktop / "AuraDashboard",
        "AI-Master-Plan (AuraDashboard)",
    ),
    (
        "https://github.com/med4to-badass/IsoSolues-MKT.git",
        desktop / "IsoSoluesMKT",
        "IsoSolues-MKT",
    ),
]

git_ok = subprocess.run(["git", "--version"], capture_output=True).returncode == 0

if git_ok:
    for url, dest, nome in REPOS:
        print(f"  -> {nome}...", end="", flush=True)
        if (dest / ".git").exists():
            subprocess.run(
                ["git", "-C", str(dest), "pull", "origin", "main", "--quiet"],
                capture_output=True,
            )
            ok(f"{nome} (atualizado)")
        elif dest.exists():
            ok(f"{nome} (pasta já existe)")
        else:
            r = subprocess.run(
                ["git", "clone", url, str(dest), "--quiet"],
                capture_output=True,
            )
            if r.returncode == 0:
                ok(f"{nome} (clonado)")
            else:
                warn(f"{nome}: falha no clone — verifique sua conexão")
else:
    warn("Git não está no PATH ainda. Reinicie o terminal e execute novamente para clonar.")


# ───────────────────────────────────────────────────────────────────────
#  12. Atalhos no Desktop
# ───────────────────────────────────────────────────────────────────────
step("Criando atalhos no Desktop")

python_exe = ps("(Get-Command python -ErrorAction SilentlyContinue)?.Source")
wt_exe     = ps("(Get-Command wt    -ErrorAction SilentlyContinue)?.Source")

aura_app = desktop / "AuraDashboard" / "app.py"
iso_html = desktop / "IsoSoluesMKT"  / "index.html"
serve_sh = desktop / "AuraDashboard" / "serve.sh"

if python_exe and aura_app.exists():
    criar_atalho(
        "AuraDashboard",
        python_exe,
        f"-m streamlit run \"{aura_app}\" --server.port 8501",
        "Inicia o Dashboard Parceiro Isopor",
    )

if iso_html.exists():
    criar_atalho(
        "IsoSolues-MKT",
        "cmd.exe",
        f"/k npx http-server \"{desktop / 'IsoSoluesMKT'}\" -p 3000 -o",
        "Inicia o site IsoSolues MKT localmente",
    )

if serve_sh.exists() and wt_exe:
    criar_atalho(
        "AuraDashboard Tunel",
        wt_exe,
        f"-d \"{desktop / 'AuraDashboard'}\" bash serve.sh",
        "Inicia o dashboard + tunel Cloudflare publico",
    )


# ───────────────────────────────────────────────────────────────────────
#  13. Resumo final
# ───────────────────────────────────────────────────────────────────────
print(f"""
{MG}╔══════════════════════════════════════════════════════════╗
║                  SETUP CONCLUIDO!                     ║
╚══════════════════════════════════════════════════════════╝{RS}

{WH} Dev Tools    : Git, Python 3.11, Node.js LTS, VS Code, gh, cloudflared{RS}
{CY} Lazer        : Steam, Epic, Discord, Spotify, VLC, OBS, Chrome, WhatsApp, Telegram{RS}
{YL} Utilidades   : PowerToys, Notepad++, CPU-Z, HWiNFO, CrystalDiskInfo, ShareX,{RS}
{YL}                Everything, CCleaner, Bitwarden, qBittorrent, WinSCP, Google Drive{RS}
{GR} Organização  : Notion, Obsidian, Todoist, To Do, Trello, Slack, Zoom, Thunderbird, Canva{RS}
{WH} Python libs  : streamlit, plotly, pandas, Pillow, reportlab{RS}
{WH} ASUS [1]     : DriverHub + Armoury Crate + Chipset + Realtek Audio{RS}
{WH} ASUS [2]     : GPU Tweak III + driver NVIDIA/AMD detectado automaticamente{RS}
{WH} Repos        : Desktop\\AuraDashboard  e  Desktop\\IsoSoluesMKT{RS}

{YL} PRÓXIMOS PASSOS:{RS}
{GY}  1. Abra o ASUS DriverHub e clique 'Instalar Todos'{RS}
{GY}  2. Reinicie o PC para aplicar todos os drivers{RS}
{GY}  3. Atalho 'AuraDashboard' no Desktop para iniciar o sistema{RS}
{GY}  4. Para o portal público: clique 'AuraDashboard Tunel' no Desktop{RS}
""")
input(" Pressione Enter para fechar...")
