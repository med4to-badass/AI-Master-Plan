#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎮 OTIMIZADOR DE JOGOS AURA — Otimização máxima 24/7
=====================================================

Daemon que roda continuamente (24/7) e:

  • Detecta AUTOMATICAMENTE quando QUALQUER jogo é aberto (lista conhecida +
    heurística por pasta de instalação: Steam, Epic, GOG, EA, Ubisoft, Riot,
    Battle.net, Xbox, etc.).
  • Aplica otimização MÁXIMA e PERSONALIZADA por jogo (prioridade de CPU,
    afinidade de núcleos, plano de energia de alto desempenho, liberação de
    RAM, throttle de apps em segundo plano, Game Mode, preferência de GPU).
  • RESTAURA tudo automaticamente quando o jogo fecha (plano de energia,
    prioridades e estado dos apps de background).

Seguro por padrão: nunca toca em processos críticos do sistema, e tudo é
configurável via `perfis.json`.

Uso:
    python otimizador.py              # roda 24/7 (loop contínuo)
    python otimizador.py --once       # faz uma única varredura e sai (teste)
    python otimizador.py --status     # mostra jogos/processos detectados agora
    python otimizador.py --config X   # usa outro arquivo de configuração

Requer: psutil  (pip install -r requirements.txt)
Recomenda-se executar como ADMINISTRADOR para liberar todos os recursos.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import psutil
except ImportError:  # pragma: no cover
    print("ERRO: o pacote 'psutil' não está instalado.")
    print("Instale com:  pip install -r requirements.txt")
    sys.exit(1)

IS_WINDOWS = os.name == "nt"
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PADRAO = BASE_DIR / "perfis.json"
LOG_FILE = BASE_DIR / "otimizador.log"

# ---------------------------------------------------------------------------
# Processos que NUNCA devem ser alterados, independentemente da configuração.
# Mexer neles pode travar ou desestabilizar o Windows.
# ---------------------------------------------------------------------------
PROCESSOS_CRITICOS = {
    "system", "system idle process", "registry", "memory compression",
    "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe",
    "lsass.exe", "svchost.exe", "dwm.exe", "fontdrvhost.exe", "ctfmon.exe",
    "audiodg.exe", "explorer.exe", "sihost.exe", "taskhostw.exe",
    "spoolsv.exe", "conhost.exe", "wudfhost.exe", "searchindexer.exe",
    "nvcontainer.exe", "nvdisplay.container.exe",
    # o próprio otimizador / interpretador
    "python.exe", "pythonw.exe", "py.exe",
}

# Mapa de níveis de prioridade -> constantes psutil (Windows) / nice (Unix)
if IS_WINDOWS:
    NIVEIS_PRIORIDADE = {
        "tempo_real": psutil.REALTIME_PRIORITY_CLASS,
        "alta": psutil.HIGH_PRIORITY_CLASS,
        "acima_do_normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS,
        "normal": psutil.NORMAL_PRIORITY_CLASS,
        "abaixo_do_normal": psutil.BELOW_NORMAL_PRIORITY_CLASS,
        "ociosa": psutil.IDLE_PRIORITY_CLASS,
    }
else:
    # No Linux usamos 'nice': menor = mais prioridade.
    NIVEIS_PRIORIDADE = {
        "tempo_real": -20,
        "alta": -10,
        "acima_do_normal": -5,
        "normal": 0,
        "abaixo_do_normal": 10,
        "ociosa": 19,
    }

# GUIDs de planos de energia do Windows
GUID_ULTIMATE = "e9a42b02-d5df-448d-aa00-03f14749eb61"
GUID_ALTO_DESEMPENHO = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"


# ===========================================================================
# Configuração padrão (criada automaticamente se perfis.json não existir)
# ===========================================================================
CONFIG_DEFAULT = {
    "config": {
        "intervalo_varredura_segundos": 4,
        "modo_agressivo": True,
        "plano_energia_alto_desempenho": True,
        "liberar_memoria": True,
        "throttle_background": True,
        "suspender_background": False,
        "habilitar_game_mode": True,
        "preferencia_gpu_alto_desempenho": True,
        "notificacoes": True,
    },
    # Perfil aplicado a QUALQUER jogo detectado que não tenha perfil próprio.
    "perfil_padrao": {
        "auto_detectar_por_pasta": True,
        "prioridade": "alta",
        "afinidade_cpu": None,
        "liberar_memoria": True,
        "desabilitar_otimizacao_tela_cheia": False
    },
    # Perfis específicos por executável (sobrescrevem o perfil padrão).
    # Chave = nome do executável (sem diferença de maiúsculas/minúsculas).
    "jogos": {
        "cs2.exe": {
            "nome": "Counter-Strike 2",
            "prioridade": "alta",
            "afinidade_cpu": None,
            "liberar_memoria": True
        },
        "valorant.exe": {
            "nome": "VALORANT",
            "prioridade": "alta",
            "liberar_memoria": True
        },
        "valorant-win64-shipping.exe": {
            "nome": "VALORANT (jogo)",
            "prioridade": "tempo_real",
            "liberar_memoria": True
        },
        "leagueoflegends.exe": {
            "nome": "League of Legends",
            "prioridade": "alta"
        },
        "fortniteclient-win64-shipping.exe": {
            "nome": "Fortnite",
            "prioridade": "alta",
            "liberar_memoria": True
        },
        "gta5.exe": {
            "nome": "GTA V",
            "prioridade": "alta",
            "liberar_memoria": True
        },
        "rdr2.exe": {
            "nome": "Red Dead Redemption 2",
            "prioridade": "alta"
        },
        "cyberpunk2077.exe": {
            "nome": "Cyberpunk 2077",
            "prioridade": "alta"
        },
        "eldenring.exe": {
            "nome": "Elden Ring",
            "prioridade": "alta"
        },
        "r5apex.exe": {
            "nome": "Apex Legends",
            "prioridade": "alta",
            "liberar_memoria": True
        },
        "f0.exe": {
            "nome": "Apex Legends (anti-cheat)",
            "prioridade": "alta"
        },
        "minecraft.exe": {
            "nome": "Minecraft",
            "prioridade": "acima_do_normal"
        },
        "javaw.exe": {
            "nome": "Minecraft (Java)",
            "prioridade": "acima_do_normal"
        },
        "dota2.exe": {
            "nome": "Dota 2",
            "prioridade": "alta"
        },
        "overwatch.exe": {
            "nome": "Overwatch 2",
            "prioridade": "alta"
        },
        "pubg.exe": {
            "nome": "PUBG",
            "prioridade": "alta"
        },
        "tslgame.exe": {
            "nome": "PUBG (jogo)",
            "prioridade": "alta",
            "liberar_memoria": True
        },
        "warzone.exe": {
            "nome": "Call of Duty Warzone",
            "prioridade": "alta",
            "liberar_memoria": True
        },
        "cod.exe": {
            "nome": "Call of Duty",
            "prioridade": "alta",
            "liberar_memoria": True
        }
    },
    # Pastas onde jogos costumam ser instalados. Qualquer executável rodando
    # de dentro destas pastas é tratado como jogo (heurística de detecção).
    "pastas_jogos": [
        "steamapps\\common",
        "steamapps/common",
        "epic games",
        "epicgames",
        "gog galaxy\\games",
        "gog games",
        "riot games",
        "ea games",
        "electronic arts",
        "ubisoft\\ubisoft game launcher\\games",
        "battle.net",
        "battlenet",
        "xboxgames",
        "windowsapps",
        "rockstar games",
        "origin games"
    ],
    # Apps de segundo plano que podem ter prioridade reduzida durante o jogo.
    # São restaurados automaticamente quando o jogo fecha.
    "processos_background": [
        "chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "opera_gx.exe",
        "brave.exe", "vivaldi.exe",
        "discord.exe", "spotify.exe", "slack.exe", "teams.exe", "ms-teams.exe",
        "telegram.exe", "whatsapp.exe", "skype.exe",
        "onedrive.exe", "dropbox.exe", "googledrivefs.exe",
        "steamwebhelper.exe", "epicgameslauncher.exe", "origin.exe",
        "googleupdate.exe", "jusched.exe", "adobeupdateservice.exe",
        "searchapp.exe", "widgets.exe", "phonelink.exe", "yourphone.exe",
        "cortana.exe", "msteams.exe", "notion.exe", "obs64.exe"
    ]
}


# ===========================================================================
# Utilidades
# ===========================================================================
def agora() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(msg: str, tipo: str = "INFO") -> None:
    linha = f"[{agora()}] [{tipo}] {msg}"
    print(linha, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(f"[{datetime.now().isoformat(timespec='seconds')}] [{tipo}] {msg}\n")
    except OSError:
        pass


def eh_admin() -> bool:
    """Retorna True se o processo tem privilégios de administrador."""
    if IS_WINDOWS:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    return os.geteuid() == 0  # type: ignore[attr-defined]


def notificar(titulo: str, mensagem: str) -> None:
    """Notificação leve no Windows (não bloqueante). Silencioso em caso de erro."""
    if not IS_WINDOWS:
        return
    try:
        ps = (
            "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
            "ContentType=WindowsRuntime] | Out-Null; "
            f"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null"
        )
        # Fallback simples e confiável via balloon do Windows Forms seria pesado;
        # mantemos apenas o log. Notificação real é opcional.
        del ps
    except Exception:
        pass


# ===========================================================================
# Ajustes específicos do Windows
# ===========================================================================
class AjustesWindows:
    """Coleção de otimizações de baixo nível (Windows)."""

    @staticmethod
    def plano_energia_ativo() -> str | None:
        if not IS_WINDOWS:
            return None
        try:
            saida = subprocess.check_output(
                ["powercfg", "/getactivescheme"], text=True, stderr=subprocess.DEVNULL
            )
            # Formato: "GUID do Esquema de Energia: <guid>  (<nome>)"
            for parte in saida.split():
                if parte.count("-") == 4 and len(parte) == 36:
                    return parte
        except Exception:
            return None
        return None

    @staticmethod
    def _garantir_ultimate() -> str:
        """Garante que o plano 'Ultimate Performance' existe; retorna o GUID a usar."""
        try:
            lista = subprocess.check_output(
                ["powercfg", "/list"], text=True, stderr=subprocess.DEVNULL
            ).lower()
            if GUID_ULTIMATE in lista:
                return GUID_ULTIMATE
            if "ultimate" in lista:
                return GUID_ULTIMATE
            # Tenta criar o plano Ultimate Performance.
            subprocess.run(
                ["powercfg", "-duplicatescheme", GUID_ULTIMATE],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            )
            lista = subprocess.check_output(
                ["powercfg", "/list"], text=True, stderr=subprocess.DEVNULL
            ).lower()
            if GUID_ULTIMATE in lista:
                return GUID_ULTIMATE
        except Exception:
            pass
        return GUID_ALTO_DESEMPENHO

    @staticmethod
    def ativar_alto_desempenho() -> bool:
        if not IS_WINDOWS:
            return False
        guid = AjustesWindows._garantir_ultimate()
        try:
            subprocess.run(
                ["powercfg", "/setactive", guid],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            )
            return True
        except Exception:
            return False

    @staticmethod
    def restaurar_plano(guid: str | None) -> None:
        if not IS_WINDOWS or not guid:
            return
        try:
            subprocess.run(
                ["powercfg", "/setactive", guid],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            )
        except Exception:
            pass

    @staticmethod
    def liberar_working_set(pid: int) -> bool:
        """Libera o working set de um processo (devolve RAM ociosa ao sistema)."""
        if not IS_WINDOWS:
            return False
        PROCESS_SET_QUOTA = 0x0100
        PROCESS_QUERY_INFORMATION = 0x0400
        try:
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION, False, pid
            )
            if not handle:
                return False
            ok = ctypes.windll.psapi.EmptyWorkingSet(handle)
            ctypes.windll.kernel32.CloseHandle(handle)
            return bool(ok)
        except Exception:
            return False

    @staticmethod
    def limpar_standby_list() -> bool:
        """Limpa a lista 'standby' de memória (cache). Requer administrador."""
        if not IS_WINDOWS or not eh_admin():
            return False
        try:
            # SystemMemoryListInformation = 80 ; MemoryPurgeStandbyList = 4
            ntdll = ctypes.windll.ntdll
            comando = ctypes.c_int(4)
            status = ntdll.NtSetSystemInformation(
                80, ctypes.byref(comando), ctypes.sizeof(comando)
            )
            return status == 0
        except Exception:
            return False

    @staticmethod
    def habilitar_game_mode() -> None:
        if not IS_WINDOWS:
            return
        try:
            import winreg  # type: ignore
            chave = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\GameBar")
            winreg.SetValueEx(chave, "AutoGameModeEnabled", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(chave, "AllowAutoGameMode", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(chave)
        except Exception:
            pass

    @staticmethod
    def definir_preferencia_gpu(caminho_exe: str) -> None:
        """Define a preferência de GPU 'Alto desempenho' para o executável do jogo."""
        if not IS_WINDOWS or not caminho_exe:
            return
        try:
            import winreg  # type: ignore
            chave = winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\DirectX\UserGpuPreferences",
            )
            # GpuPreference=2 -> Alto desempenho (GPU dedicada)
            winreg.SetValueEx(chave, caminho_exe, 0, winreg.REG_SZ, "GpuPreference=2;")
            winreg.CloseKey(chave)
        except Exception:
            pass

    @staticmethod
    def desabilitar_otimizacao_tela_cheia(caminho_exe: str) -> None:
        """Desativa as 'otimizações de tela cheia' do Windows para o jogo."""
        if not IS_WINDOWS or not caminho_exe:
            return
        try:
            import winreg  # type: ignore
            chave = winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers",
            )
            winreg.SetValueEx(
                chave, caminho_exe, 0, winreg.REG_SZ, "~ DISABLEDXMAXIMIZEDWINDOWEDMODE"
            )
            winreg.CloseKey(chave)
        except Exception:
            pass


# ===========================================================================
# Otimizador principal
# ===========================================================================
class OtimizadorJogos:
    def __init__(self, caminho_config: Path):
        self.caminho_config = caminho_config
        self.cfg = self._carregar_config()
        self.config = self.cfg.get("config", {})
        self.perfil_padrao = self.cfg.get("perfil_padrao", {})
        self.jogos = {k.lower(): v for k, v in self.cfg.get("jogos", {}).items()}
        self.pastas_jogos = [p.lower().replace("\\", os.sep).replace("/", os.sep)
                             for p in self.cfg.get("pastas_jogos", [])]
        self.background = {p.lower() for p in self.cfg.get("processos_background", [])}

        # Estado em tempo de execução
        self.jogos_ativos: dict[int, dict] = {}        # pid -> info do jogo
        self.plano_energia_original: str | None = None
        self.background_alterados: dict[int, dict] = {}  # pid -> {prioridade, suspenso}
        self._rodando = True

        self._proprio_pid = os.getpid()

    # ---------------- Configuração ----------------
    def _carregar_config(self) -> dict:
        if not self.caminho_config.exists():
            log(f"Configuração não encontrada. Criando padrão em {self.caminho_config.name}")
            try:
                with open(self.caminho_config, "w", encoding="utf-8") as fh:
                    json.dump(CONFIG_DEFAULT, fh, ensure_ascii=False, indent=2)
            except OSError as exc:
                log(f"Não foi possível escrever a config: {exc}", "ERRO")
            return json.loads(json.dumps(CONFIG_DEFAULT))
        try:
            with open(self.caminho_config, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            log(f"Erro lendo config ({exc}). Usando padrão.", "ERRO")
            return json.loads(json.dumps(CONFIG_DEFAULT))

    # ---------------- Detecção ----------------
    def _eh_critico(self, nome: str) -> bool:
        return nome.lower() in PROCESSOS_CRITICOS

    def _eh_jogo(self, proc: "psutil.Process") -> dict | None:
        """
        Decide se o processo é um jogo e retorna o perfil a aplicar.
        Retorna None se não for jogo.
        """
        try:
            nome = (proc.info.get("name") or "").lower()
        except Exception:
            return None
        if not nome or self._eh_critico(nome):
            return None

        # 1) Jogo explicitamente cadastrado
        if nome in self.jogos:
            perfil = dict(self.perfil_padrao)
            perfil.update(self.jogos[nome])
            perfil.setdefault("nome", nome)
            return perfil

        # 2) Heurística por pasta de instalação
        if self.perfil_padrao.get("auto_detectar_por_pasta", True):
            try:
                exe = (proc.info.get("exe") or "").lower()
            except Exception:
                exe = ""
            if exe:
                exe_norm = exe.replace("\\", os.sep).replace("/", os.sep)
                for pasta in self.pastas_jogos:
                    if pasta and pasta in exe_norm:
                        perfil = dict(self.perfil_padrao)
                        perfil["nome"] = proc.info.get("name") or nome
                        perfil["_auto"] = True
                        return perfil
        return None

    # ---------------- Aplicar / restaurar prioridade ----------------
    @staticmethod
    def _definir_prioridade(proc: "psutil.Process", nivel: str) -> bool:
        valor = NIVEIS_PRIORIDADE.get(nivel)
        if valor is None:
            return False
        try:
            if IS_WINDOWS:
                proc.nice(valor)
            else:
                proc.nice(valor)
            return True
        except (psutil.AccessDenied, psutil.NoSuchProcess, Exception):
            return False

    # ---------------- Otimizar um jogo ----------------
    def _otimizar_jogo(self, proc: "psutil.Process", perfil: dict) -> None:
        pid = proc.pid
        nome_jogo = perfil.get("nome", proc.info.get("name", "jogo"))
        try:
            caminho_exe = proc.info.get("exe") or ""
        except Exception:
            caminho_exe = ""

        log(f"🎮 JOGO DETECTADO: {nome_jogo}  (pid {pid}) — aplicando otimização máxima")

        # 1) Prioridade da CPU
        nivel = perfil.get("prioridade", "alta")
        if self._definir_prioridade(proc, nivel):
            log(f"   ✔ Prioridade de CPU: {nivel}")
        else:
            log(f"   ⚠ Não foi possível definir prioridade (rode como administrador)", "AVISO")

        # 2) Afinidade de núcleos
        afinidade = perfil.get("afinidade_cpu")
        if afinidade:
            try:
                proc.cpu_affinity(list(afinidade))
                log(f"   ✔ Afinidade de CPU: núcleos {afinidade}")
            except Exception:
                log("   ⚠ Falha ao definir afinidade de CPU", "AVISO")

        # 3) Plano de energia de alto desempenho (apenas no 1º jogo ativo)
        if self.config.get("plano_energia_alto_desempenho", True) and not self.plano_energia_original:
            self.plano_energia_original = AjustesWindows.plano_energia_ativo()
            if AjustesWindows.ativar_alto_desempenho():
                log("   ✔ Plano de energia: ALTO DESEMPENHO ativado")

        # 4) Game Mode
        if self.config.get("habilitar_game_mode", True):
            AjustesWindows.habilitar_game_mode()

        # 5) Preferência de GPU dedicada
        if self.config.get("preferencia_gpu_alto_desempenho", True) and caminho_exe:
            AjustesWindows.definir_preferencia_gpu(caminho_exe)
            log("   ✔ Preferência de GPU: alto desempenho")

        # 6) Desabilitar otimização de tela cheia (opcional por perfil)
        if perfil.get("desabilitar_otimizacao_tela_cheia") and caminho_exe:
            AjustesWindows.desabilitar_otimizacao_tela_cheia(caminho_exe)
            log("   ✔ Otimizações de tela cheia desabilitadas")

        # 7) Liberar memória
        if perfil.get("liberar_memoria", self.config.get("liberar_memoria", True)):
            self._liberar_memoria(exceto_pid=pid)

        # 8) Reduzir prioridade dos apps de background
        if self.config.get("throttle_background", True):
            self._throttle_background()

        self.jogos_ativos[pid] = {"nome": nome_jogo, "perfil": perfil}
        if self.config.get("notificacoes", True):
            notificar("Otimizador Aura", f"{nome_jogo} otimizado ao máximo 🚀")

    # ---------------- Background throttle / restore ----------------
    def _throttle_background(self) -> None:
        pids_jogos = set(self.jogos_ativos.keys())
        contador = 0
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                nome = (proc.info.get("name") or "").lower()
                pid = proc.info["pid"]
            except Exception:
                continue
            if pid == self._proprio_pid or pid in pids_jogos:
                continue
            if self._eh_critico(nome) or nome not in self.background:
                continue
            if pid in self.background_alterados:
                continue
            try:
                prioridade_atual = proc.nice()
                self._definir_prioridade(proc, "ociosa")
                registro = {"prioridade": prioridade_atual, "suspenso": False}
                if self.config.get("suspender_background", False):
                    proc.suspend()
                    registro["suspenso"] = True
                self.background_alterados[pid] = registro
                contador += 1
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
            except Exception:
                continue
        if contador:
            acao = "suspensos" if self.config.get("suspender_background") else "reduzidos"
            log(f"   ✔ {contador} apps de segundo plano {acao}")

    def _restaurar_background(self) -> None:
        if not self.background_alterados:
            return
        restaurados = 0
        for pid, registro in list(self.background_alterados.items()):
            try:
                proc = psutil.Process(pid)
                if registro.get("suspenso"):
                    proc.resume()
                proc.nice(registro["prioridade"])
                restaurados += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            except Exception:
                pass
            finally:
                self.background_alterados.pop(pid, None)
        if restaurados:
            log(f"   ✔ {restaurados} apps de segundo plano restaurados")

    # ---------------- Memória ----------------
    def _liberar_memoria(self, exceto_pid: int | None = None) -> None:
        if not IS_WINDOWS:
            return
        liberados = 0
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pid = proc.info["pid"]
                nome = (proc.info.get("name") or "").lower()
            except Exception:
                continue
            if pid in (exceto_pid, self._proprio_pid):
                continue
            if self._eh_critico(nome):
                continue
            if AjustesWindows.liberar_working_set(pid):
                liberados += 1
        if AjustesWindows.limpar_standby_list():
            log("   ✔ Cache 'standby' de memória limpo")
        if liberados:
            log(f"   ✔ RAM liberada de {liberados} processos")

    # ---------------- Quando um jogo fecha ----------------
    def _jogo_finalizado(self, pid: int) -> None:
        info = self.jogos_ativos.pop(pid, None)
        if info:
            log(f"🛑 Jogo finalizado: {info['nome']} (pid {pid})")
        # Se não há mais jogos rodando, restaura o sistema.
        if not self.jogos_ativos:
            self._restaurar_sistema()

    def _restaurar_sistema(self) -> None:
        log("♻️  Restaurando estado normal do sistema…")
        if self.plano_energia_original:
            AjustesWindows.restaurar_plano(self.plano_energia_original)
            log(f"   ✔ Plano de energia restaurado")
            self.plano_energia_original = None
        self._restaurar_background()

    # ---------------- Varredura ----------------
    def varrer(self) -> None:
        vistos = set()
        for proc in psutil.process_iter(["pid", "name", "exe"]):
            try:
                pid = proc.info["pid"]
            except Exception:
                continue
            vistos.add(pid)
            if pid in self.jogos_ativos:
                continue
            perfil = self._eh_jogo(proc)
            if perfil:
                try:
                    self._otimizar_jogo(proc, perfil)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        # Detecta jogos que fecharam
        for pid in list(self.jogos_ativos.keys()):
            if pid not in vistos or not psutil.pid_exists(pid):
                self._jogo_finalizado(pid)

    # ---------------- Loop 24/7 ----------------
    def rodar(self) -> None:
        intervalo = max(1, int(self.config.get("intervalo_varredura_segundos", 4)))
        admin = eh_admin()
        log("=" * 64)
        log("🎮 OTIMIZADOR DE JOGOS AURA — iniciado (modo 24/7)")
        log(f"   Administrador: {'SIM ✔' if admin else 'NÃO ⚠ (recursos limitados)'}")
        log(f"   Jogos cadastrados: {len(self.jogos)} | Detecção por pasta: "
            f"{'ON' if self.perfil_padrao.get('auto_detectar_por_pasta') else 'OFF'}")
        log(f"   Intervalo de varredura: {intervalo}s")
        log("=" * 64)
        if not admin and IS_WINDOWS:
            log("Dica: execute como administrador para liberar 100% das otimizações.", "AVISO")

        self._instalar_handlers()
        while self._rodando:
            try:
                self.varrer()
            except Exception as exc:  # nunca deixa o daemon morrer por um erro pontual
                log(f"Erro na varredura: {exc}", "ERRO")
            for _ in range(intervalo * 2):
                if not self._rodando:
                    break
                time.sleep(0.5)
        self.encerrar()

    def varrer_uma_vez(self) -> None:
        self.varrer()

    # ---------------- Encerramento limpo ----------------
    def _instalar_handlers(self) -> None:
        def _parar(signum, frame):  # noqa: ANN001
            log(f"Sinal {signum} recebido — encerrando com segurança…")
            self._rodando = False
        for s in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(s, _parar)
            except (ValueError, OSError):
                pass

    def encerrar(self) -> None:
        log("Encerrando otimizador — restaurando tudo…")
        # Restaura o sistema independentemente de jogos ativos.
        self.jogos_ativos.clear()
        self._restaurar_sistema()
        log("✔ Otimizador encerrado. Sistema restaurado.")

    # ---------------- Status ----------------
    def status(self) -> None:
        print("\n🎮 Verificando processos no momento…\n")
        achou = False
        for proc in psutil.process_iter(["pid", "name", "exe"]):
            perfil = self._eh_jogo(proc)
            if perfil:
                achou = True
                tipo = "auto (pasta)" if perfil.get("_auto") else "cadastrado"
                print(f"  ✔ {perfil.get('nome'):<32} pid={proc.info['pid']:<7} [{tipo}]")
        if not achou:
            print("  Nenhum jogo em execução agora.")
        print()


# ===========================================================================
# Entrada
# ===========================================================================
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Otimizador de Jogos Aura — otimização máxima 24/7."
    )
    parser.add_argument("--once", action="store_true",
                        help="Executa uma única varredura e sai (teste).")
    parser.add_argument("--status", action="store_true",
                        help="Mostra jogos detectados agora e sai.")
    parser.add_argument("--config", type=str, default=str(CONFIG_PADRAO),
                        help="Caminho do arquivo de configuração (perfis.json).")
    args = parser.parse_args()

    otimizador = OtimizadorJogos(Path(args.config))

    if args.status:
        otimizador.status()
        return
    if args.once:
        otimizador.varrer_uma_vez()
        log("Varredura única concluída.")
        return

    try:
        otimizador.rodar()
    except KeyboardInterrupt:
        otimizador.encerrar()


if __name__ == "__main__":
    main()
