import requests
import pandas as pd
import matplotlib.pyplot as plt
from urllib.parse import quote

DATA = "https://raw.githubusercontent.com/TracingInsights"
SESSIONS = ["Practice 1", "Practice 2", "Practice 3",
            "Sprint Qualifying", "Sprint", "Qualifying", "Race"]


# ---------- Strumenti per scaricare i dati ----------

def get_json(url):
    """Scarica un file di dati. Se non esiste, si ferma con un messaggio chiaro."""
    response = requests.get(url)
    if response.status_code != 200:
        raise SystemExit(f"Dati non trovati:\n{url}")
    return response.json()


def exists(url):
    """True se il file esiste online."""
    return requests.head(url).status_code == 200


# ---------- Strumenti per farti scegliere ----------

def choose(title, options):
    """Mostra una lista numerata e ti fa scegliere un numero."""
    print(f"\n{title}")
    for number, option in enumerate(options, start=1):
        print(f"{number:3}. {option}")
    while True:
        answer = input("Scrivi il numero e premi Invio: ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        print("Numero non valido, riprova.")


def grand_prix_list(year):
    """I Gran Premi disponibili per quell'anno (le cartelle del repository dei dati)."""
    response = requests.get(f"https://api.github.com/repos/TracingInsights/{year}/contents/")
    if response.status_code != 200:
        return []
    return [item["name"] for item in response.json()
            if item["type"] == "dir" and ("Grand Prix" in item["name"] or "Testing" in item["name"])]


# ---------- Tempi e giri ----------

def lap_time_text(seconds):
    """Trasforma 78.792 in '1:18.792'."""
    minutes = int(seconds // 60)
    return f"{minutes}:{seconds - minutes * 60:06.3f}"


def is_valid(time, deleted):
    """Un giro conta se ha un tempo e non è stato cancellato (es. track limits)."""
    return isinstance(time, (int, float)) and not deleted


def ranking(base):
    """Classifica della sessione: il giro più veloce di ogni pilota, dal primo all'ultimo."""
    laps = get_json(base + "session_laptimes.json")
    deleted_list = laps.get("del", [False] * len(laps["time"]))
    best = {}
    for driver, time, deleted in zip(laps["drv"], laps["time"], deleted_list):
        if is_valid(time, deleted) and (driver not in best or time < best[driver]):
            best[driver] = time
    return sorted(best.items(), key=lambda item: item[1])


def fastest_lap(base, driver):
    """Il giro valido più veloce di un pilota: (numero del giro, tempo in secondi)."""
    laps = get_json(base + f"{driver}/laptimes.json")
    deleted_list = laps.get("del", [False] * len(laps["time"]))
    best = None
    for lap, time, deleted in zip(laps["lap"], laps["time"], deleted_list):
        if is_valid(time, deleted) and (best is None or time < best[1]):
            best = (lap, time)
    return best


def telemetry(base, driver, lap):
    """Scarica la telemetria di un giro e la mette in una tabella."""
    data = get_json(base + f"{driver}/{lap}_tel.json")
    return pd.DataFrame(data["tel"])


# ================= 1. SCEGLI ANNO, GARA E SESSIONE =================

year = input("Anno (dal 2018 al 2026, Invio = 2026): ").strip() or "2026"

grands_prix = grand_prix_list(year)
if grands_prix:
    grand_prix = choose(f"Gran Premi {year}:", grands_prix)
else:
    print("\nNon riesco a scaricare l'elenco dei Gran Premi.")
    grand_prix = input("Scrivi il nome esatto (es. Italian Grand Prix): ").strip()

event = f"{DATA}/{year}/main/{quote(grand_prix)}/"
available = [s for s in SESSIONS if exists(event + quote(s) + "/session_laptimes.json")]
if not available:
    raise SystemExit(f"Nessun dato per {year} {grand_prix}. Controlla anno e nome.")
session = choose("Sessioni disponibili:", available)

base = event + quote(session) + "/"

# ================= 2. CLASSIFICA E SCELTA DEI PILOTI =================

order = ranking(base)
leader_time = order[0][1]
print(f"\n{year} {grand_prix} – {session}: classifica per giro più veloce\n")
for position, (driver, time) in enumerate(order, start=1):
    gap = "" if position == 1 else f"+{time - leader_time:.3f}"
    print(f"{position:2}. {driver}  {lap_time_text(time)}  {gap}")

all_drivers = [driver for driver, time in order]
while True:
    answer = input("\nPiloti da confrontare, separati da spazio "
                   "(es. VER LEC, Invio = primi due): ").upper().split()
    drivers = answer or all_drivers[:2]
    unknown = [d for d in drivers if d not in all_drivers]
    if not unknown:
        break
    print(f"Non trovo {', '.join(unknown)} in questa sessione, riprova.")

# ================= 3. GRAFICI =================

fig, ax = plt.subplots(3, 1, figsize=(14, 9), sharex=True)

for driver in drivers:
    lap, time = fastest_lap(base, driver)
    tel = telemetry(base, driver, lap)
    print(f"Grafico: {driver}, giro {lap}, {lap_time_text(time)}")

    ax[0].plot(tel["distance"], tel["speed"], label=f"{driver}  {lap_time_text(time)}")
    ax[1].plot(tel["distance"], tel["throttle"])
    ax[2].plot(tel["distance"], tel["brake"])

ax[0].set_title(f"{year} {grand_prix} – {session} – giro più veloce")
ax[0].set_ylabel("Velocità (km/h)")
ax[0].legend()
ax[1].set_ylabel("Acceleratore (%)")
ax[2].set_ylabel("Freno (on/off)")
ax[2].set_xlabel("Distanza dal traguardo (m)")
for a in ax:
    a.grid(True)

plt.show()
