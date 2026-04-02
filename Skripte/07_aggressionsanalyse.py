import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

SENTIWS_NEG = Path("/home/nghm/Dokumente/Zeitungsanalyse/sentiws/SentiWS_v2.0_Negative.txt")
TXT_DIR = Path("/home/nghm/Dokumente/Zeitungsanalyse/daten_txt/wetransfer_pdf-stadtwachter_2026-03-03_2338/txt Stadtwächter")
OUTPUT_CSV = Path("/home/nghm/Dokumente/Zeitungsanalyse/ergebnisse/aggressionsanalyse.csv")

# --- 1. SentiWS Negativ-Lexikon einlesen ---
negativ_woerter = set()
with open(SENTIWS_NEG, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        # Grundform extrahieren (vor dem |)
        grundform = parts[0].split("|")[0].lower()
        negativ_woerter.add(grundform)
        # Flexionsformen hinzufügen
        if len(parts) >= 3 and parts[2]:
            for form in parts[2].split(","):
                negativ_woerter.add(form.strip().lower())

print(f"SentiWS Negativ-Lexikon: {len(negativ_woerter)} Wortformen geladen.")

# --- 2. Jahr aus Dateiname extrahieren ---
def jahr_aus_dateiname(name):
    treffer = re.findall(r"(192[0-9]|193[0-9])", name)
    return int(treffer[0]) if treffer else None

# --- 3. Texte einlesen und analysieren ---
txt_files = sorted(TXT_DIR.glob("*.txt"))
print(f"{len(txt_files)} Dateien gefunden.\n")

ergebnisse = []

for txt_file in txt_files:
    text = txt_file.read_text(encoding="utf-8", errors="replace").lower()
    # Tokenisierung: nur alphabetische Wörter (mind. 3 Buchstaben)
    woerter = re.findall(r"[a-zäöüß]{3,}", text)
    gesamt = len(woerter)
    if gesamt == 0:
        continue

    # Negative Wörter zählen
    neg_treffer = [w for w in woerter if w in negativ_woerter]
    neg_anzahl = len(neg_treffer)
    dichte = round((neg_anzahl / gesamt) * 1000, 2)

    # Häufigste negative Wörter (Top 5)
    top_neg = Counter(neg_treffer).most_common(5)
    top_str = ", ".join([f"{w}({n})" for w, n in top_neg])

    jahr = jahr_aus_dateiname(txt_file.name)

    ergebnisse.append({
        "Dateiname": txt_file.name,
        "Jahr": jahr if jahr else "unbekannt",
        "Aggressions_Dichte": dichte,
        "Negative_Woerter_Absolut": neg_anzahl,
        "Gesamtwoerter": gesamt,
        "Top_Aggressionswoerter": top_str,
    })

    print(f"{txt_file.name[:45]:<45} | Jahr: {jahr} | Dichte: {dichte:5.1f} | {top_str[:60]}")

# --- 4. CSV speichern ---
OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    felder = ["Dateiname", "Jahr", "Aggressions_Dichte", "Negative_Woerter_Absolut", "Gesamtwoerter", "Top_Aggressionswoerter"]
    writer = csv.DictWriter(f, fieldnames=felder)
    writer.writeheader()
    writer.writerows(ergebnisse)

# --- 5. Zusammenfassung nach Jahrgang ---
nach_jahr = defaultdict(list)
for r in ergebnisse:
    nach_jahr[r["Jahr"]].append(r["Aggressions_Dichte"])

print(f"\n{'='*55}")
print("ZUSAMMENFASSUNG NACH JAHRGANG")
print(f"{'='*55}")
for jahr in sorted(nach_jahr, key=lambda x: str(x)):
    werte = nach_jahr[jahr]
    durchschnitt = round(sum(werte) / len(werte), 2)
    minimum = round(min(werte), 2)
    maximum = round(max(werte), 2)
    print(f"  {jahr}: {len(werte):3} Ausgaben | Ø Dichte: {durchschnitt:5.1f} | Min: {minimum} | Max: {maximum}")

print(f"\nErgebnisse gespeichert: {OUTPUT_CSV}")
