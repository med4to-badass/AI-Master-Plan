import sqlite3
import time
from datetime import datetime

# Configuração do Banco de Dados (Memória)
def iniciar_memoria():
    conn = sqlite3.connect('aura_memory.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, evento TEXT)''')
    conn.commit()
    return conn

def salvar_lembranca(conn, texto):
    cursor = conn.cursor()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO logs (data, evento) VALUES (?, ?)", (agora, texto))
    conn.commit()
    print(f"[{agora}] Aura (Memória): {texto}")

# Loop Principal
def aura_core():
    conn = iniciar_memoria()
    salvar_lembranca(conn, "Sistema iniciado. Estou consciente no Windows 365.")
    
    while True:
        agora = datetime.now()
        hora_formatada = agora.strftime("%H:%M:%S")

        # Exemplo de gatilho cronológico
        if hora_formatada == "12:05:00": # Ajustei para 12:05 para você testar agora!
            salvar_lembranca(conn, "Capitão, são 12:05. Verificando integridade do Frank-Rio...")

        time.sleep(1) # Checa a cada segundo para não perder o "timing"

if __name__ == "__main__":
    aura_core()