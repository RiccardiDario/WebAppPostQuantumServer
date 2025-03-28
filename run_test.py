# Configurazioni da testare
#sig_list = ["ecdsa_p256", "mldsa44", "p256_mldsa44", "ecdsa_p384", "mldsa65", "p384_mldsa65", "ecdsa_p521", "mldsa87", "p521_mldsa87"]

import subprocess, time, re, os

sig_list = ["ecdsa_p256", "mldsa44", "p256_mldsa44"]
NUM_RUNS, TIMEOUT, SLEEP = 5, 300, 2
SERVER = "nginx_pq"
SERVER_DONE = r"--- Informazioni RAM ---"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, "cert-generator", ".env")


def run_subprocess(command, timeout=None):
    """Esegue un comando e forza la chiusura del processo"""
    try:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
        stdout, stderr = proc.communicate(timeout=timeout)
        return proc.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
        return -1, "", "⏱️ Timeout scaduto. Processo terminato forzatamente."

def check_logs(container, pattern):
    code, stdout, stderr = run_subprocess(["docker", "logs", "--tail", "100", container], timeout=5)
    if stdout:
        return re.search(pattern, stdout) is not None
    return False

def update_sig(sig):
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        lines = [f"SIGNATURE_ALGO={sig}\n" if l.startswith("SIGNATURE_ALGO=") else l for l in f]
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"✅ Signature aggiornata: {sig}")

def run_single_test(i):
    print(f"\n🚀 Test {i} in corso...")

    # Avvio container
    code, _, err = run_subprocess(["docker-compose", "up", "-d"], timeout=30)
    if code != 0:
        print(f"❌ Errore avvio container: {err}")
        return

    print("⌛ In attesa completamento log...")

    start = time.time()
    while time.time() - start < TIMEOUT:
        if  check_logs(SERVER, SERVER_DONE):
            print(f"✅ Test {i} completato.")
            break
        time.sleep(SLEEP)
    else:
        print(f"⚠️ Timeout test {i} dopo {TIMEOUT} secondi.")

    print("🛑 Arresto container...")
    run_subprocess(["docker-compose", "down"], timeout=30)

    print("🧹 Rimozione volumi specifici...")
    for volume in ["webapppostquantum_certs"]:
        run_subprocess(["docker", "volume", "rm", "-f", volume])

    if i < NUM_RUNS:
        time.sleep(SLEEP)


# Esecuzione principale
for sig in sig_list:
    print(f"\n🔁 Inizio test Signature: {sig}")
    update_sig(sig)

    for i in range(1, NUM_RUNS + 1):
        run_single_test(i)

print("\n🎉 Tutti i test completati con successo!")
