import requests
import pandas as pd
import matplotlib.pyplot as plt
from urllib.parse import quote

# ================= SCEGLI COSA CONFRONTARE =================
YEAR = 2025
GRAND_PRIX = "Italian Grand Prix"
SESSION = "Qualifying"      # Practice 1, Practice 2, Practice 3, Qualifying,
                            # Sprint Qualifying, Sprint, Race
DRIVERS = []                # vuoto = i primi due della classifica
                            # oppure scegli tu, es. ["VER", "LEC", "NOR"]
# ===========================================================

BASE = (f"https://raw.githubusercontent.com/TracingInsights/{YEAR}/main/"
        f"{quote(GRAND_PRIX)}/{quote(SESSION)}/")


def get_json(url):
    """Scarica un file di dati. Se non esiste, si ferma con un messaggio chiaro."""
    response = requests.get(url)
    if response.status_code != 200:
        raise SystemExit(f"Dati non trovati:\n{url}\n"
                         "Controlla anno, Gran Premio, sessione e sigla del pilota.")
    return response.json()


def lap_time_text(seconds):
    """Trasforma 78.792 in '1:18.792'."""
    minutes = int(seconds // 60)
    return f"{minutes}:{seconds - minutes * 60:06.3f}"


def is_valid(time, deleted):
    """Un giro conta se ha un tempo e non è stato cancellato (es. track limits)."""
    return isinstance(time, (int, float)) and not deleted


def ranking():
    """Classifica della sessione: il giro più veloce di ogni pilota, dal primo all'ultimo."""
    laps = get_json(BASE + "session_laptimes.json")
    deleted_list = laps.get("del", [False] * len(laps["time"]))
    best = {}
    for driver, time, deleted in zip(laps["drv"], laps["time"], deleted_list):
        if is_valid(time, deleted) and (driver not in best or time < best[driver]):
            best[driver] = time
    return sorted(best.items(), key=lambda item: item[1])


def fastest_lap(driver):
    """Trova il giro valido più veloce di un pilota: (numero del giro, tempo in secondi)."""
    laps = get_json(BASE + f"{driver}/laptimes.json")
    deleted_list = laps.get("del", [False] * len(laps["time"]))
    best = None
    for lap, time, deleted in zip(laps["lap"], laps["time"], deleted_list):
        if is_valid(time, deleted) and (best is None or time < best[1]):
            best = (lap, time)
    return best


def telemetry(driver, lap):
    """Scarica la telemetria di un giro e la mette in una tabella."""
    data = get_json(BASE + f"{driver}/{lap}_tel.json")
    return pd.DataFrame(data["tel"])


# ---------- 1. Classifica della sessione ----------
order = ranking()
leader_time = order[0][1]
print(f"\n{YEAR} {GRAND_PRIX} – {SESSION}: classifica per giro più veloce\n")
for position, (driver, time) in enumerate(order, start=1):
    gap = "" if position == 1 else f"+{time - leader_time:.3f}"
    print(f"{position:2}. {driver}  {lap_time_text(time)}  {gap}")
print()

drivers = DRIVERS if DRIVERS else [order[0][0], order[1][0]]

# ---------- 2. Grafici ----------
fig, ax = plt.subplots(3, 1, figsize=(14, 9), sharex=True)

for driver in drivers:
    best = fastest_lap(driver)
    if best is None:
        print(f"{driver}: nessun giro valido in questa sessione, lo salto")
        continue
    lap, time = best
    tel = telemetry(driver, lap)
    print(f"Grafico: {driver}, giro {lap}, {lap_time_text(time)}")

    ax[0].plot(tel["distance"], tel["speed"], label=f"{driver}  {lap_time_text(time)}")
    ax[1].plot(tel["distance"], tel["throttle"])
    ax[2].plot(tel["distance"], tel["brake"])

ax[0].set_title(f"{YEAR} {GRAND_PRIX} – {SESSION} – giro più veloce")
ax[0].set_ylabel("Velocità (km/h)")
ax[0].legend()
ax[1].set_ylabel("Acceleratore (%)")
ax[2].set_ylabel("Freno (on/off)")
ax[2].set_xlabel("Distanza dal traguardo (m)")
for a in ax:
    a.grid(True)

plt.show()
