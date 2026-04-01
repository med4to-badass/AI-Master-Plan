import time
from datetime import datetime

def aura_heartbeat():
    print("--- Sistema Aura Iniciado ---")
    while True:
        agora = datetime.now()
        hora_formatada = agora.strftime("%H:%M:%S")
        
        # Noção de tempo humana
        if "08:00:00" <= hora_formatada <= "08:00:59":
            print(f"[{hora_formatada}] Aura: Bom dia, capitão! O Frank-Rio está pronto para a IsoSoluções.")
        
        if "12:00:00" <= hora_formatada <= "12:00:59":
            print(f"[{hora_formatada}] Aura: Hora do almoço. Sugiro pausar a VM do Adobe para poupar energia.")

        # Pulsação a cada 60 segundos
        time.sleep(60)

if __name__ == "__main__":
    aura_heartbeat()