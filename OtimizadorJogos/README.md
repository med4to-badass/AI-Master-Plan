# 🎮 Otimizador de Jogos Aura — Otimização Máxima 24/7

Daemon leve que roda **24 horas por dia** em segundo plano, **detecta
automaticamente** quando **qualquer jogo** é aberto e aplica **otimização
máxima e personalizada por jogo**. Quando o jogo fecha, **restaura tudo
sozinho** ao estado normal.

> Funciona melhor no **Windows** (onde estão as otimizações de baixo nível).
> No Linux ele ainda ajusta prioridades de processo (via `nice`).

---

## ✨ O que ele faz quando um jogo abre

| Otimização | Descrição |
|---|---|
| ⚡ **Prioridade de CPU** | Eleva o jogo para *Alta* (ou *Tempo real*) para ganhar FPS e reduzir travadas |
| 🧩 **Afinidade de núcleos** | Fixa o jogo em núcleos específicos (opcional, por jogo) |
| 🔋 **Plano de energia** | Ativa *Desempenho Máximo* (Ultimate Performance) e restaura o seu plano depois |
| 🧹 **Liberação de RAM** | Esvazia working sets e a *standby list* (cache) para liberar memória |
| 🐌 **Throttle de background** | Reduz a prioridade (ou suspende) navegadores, Discord, OneDrive, updaters etc. |
| 🎯 **Game Mode + GPU** | Liga o Game Mode do Windows e força a **GPU dedicada** para o jogo |
| 🖥️ **Tela cheia** | Opcionalmente desativa as "otimizações de tela cheia" do Windows |

Tudo é **revertido automaticamente** assim que o último jogo é fechado.

---

## 🚀 Instalação rápida (Windows)

### Opção A — Rodar quando quiser
Dê **duplo clique** em **`INICIAR_OTIMIZADOR.bat`**.
Ele pede admin, instala o `psutil` se faltar e começa a monitorar. Pronto. 🎮

### Opção B — Rodar 24/7 (recomendado)
Para iniciar **sozinho a cada login**, oculto e com reinício automático:

```powershell
powershell -ExecutionPolicy Bypass -File instalar_24-7.ps1
```

Para **desinstalar** o início automático:

```powershell
powershell -ExecutionPolicy Bypass -File instalar_24-7.ps1 -Remover
```

> 💡 Execute como **Administrador** para liberar 100% das otimizações
> (prioridade *Tempo real*, limpeza de standby list etc.). O `.bat` e o
> instalador já pedem elevação automaticamente.

---

## ⚙️ Personalização — `perfis.json`

Tudo é configurável. Edite **`perfis.json`** (criado na 1ª execução).

### Configuração global (`config`)
```json
"intervalo_varredura_segundos": 4,   // de quanto em quanto tempo procura jogos
"plano_energia_alto_desempenho": true,
"liberar_memoria": true,
"throttle_background": true,
"suspender_background": false,        // true = SUSPENDE apps de fundo (mais agressivo)
"habilitar_game_mode": true,
"preferencia_gpu_alto_desempenho": true
```

### Perfil por jogo (`jogos`)
A chave é o **nome do executável** (em minúsculas). Exemplo:
```json
"cs2.exe": {
  "nome": "Counter-Strike 2",
  "prioridade": "alta",          // ociosa | abaixo_do_normal | normal | acima_do_normal | alta | tempo_real
  "afinidade_cpu": [0,1,2,3,4,5],// núcleos a usar (opcional)
  "liberar_memoria": true,
  "desabilitar_otimizacao_tela_cheia": true
}
```

> ⚠️ **Tempo real** dá o máximo de prioridade, mas pode deixar o resto do
> sistema momentaneamente travado. Use *alta* para a maioria dos jogos.

### Detecção automática (`perfil_padrao` + `pastas_jogos`)
Qualquer executável rodando de dentro das pastas listadas em `pastas_jogos`
(Steam, Epic, GOG, EA, Ubisoft, Riot, Battle.net, Xbox, Rockstar…) é tratado
como jogo e recebe o `perfil_padrao` — **mesmo que não esteja cadastrado**.
Assim, jogos novos já são otimizados na hora.

### Apps de segundo plano (`processos_background`)
Lista dos apps que terão a prioridade reduzida durante o jogo. Adicione ou
remova o que quiser. **Processos críticos do Windows nunca são tocados.**

---

## 🧪 Comandos úteis

```bash
python otimizador.py            # roda 24/7 (loop contínuo)
python otimizador.py --status   # mostra os jogos detectados agora
python otimizador.py --once     # faz uma varredura única (teste) e sai
python otimizador.py --config caminho.json
```

---

## 🛡️ Segurança

- **Lista de proteção embutida**: processos essenciais do Windows (`csrss`,
  `lsass`, `dwm`, `explorer`, `svchost`, drivers de áudio/vídeo, etc.) **nunca**
  têm prioridade alterada nem são suspensos — mesmo que apareçam na config.
- **Reversível**: plano de energia e prioridades de background são salvos e
  restaurados quando o jogo fecha ou quando o otimizador é encerrado.
- **Sem rede**: o programa não acessa a internet nem coleta dados. Tudo é local.
- O arquivo `otimizador.log` registra cada ação realizada.

---

Feito para a galera que quer **FPS máximo sem ficar mexendo em config toda hora**. 🚀
