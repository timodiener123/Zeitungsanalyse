import csv
import re
from collections import defaultdict
from pathlib import Path

TXT_DIR = Path("/home/nghm/Dokumente/Zeitungsanalyse/daten_txt/wetransfer_pdf-stadtwachter_2026-03-03_2338/txt Stadtwächter")
OUTPUT_CSV = Path("/home/nghm/Dokumente/Zeitungsanalyse/ergebnisse/seedterm_analyse.csv")

SEED_TERME = [
    "jude", "juden", "jüdisch", "jüdische", "judentum", "judenschaft",
    "antisemit", "antisemitisch", "antisemitismus",
    "rasse", "rassisch", "völkisch", "volksgenosse",
    "parasit", "schmarotzer", "ungeziefer",
    "bolschewismus", "marxismus", "kommunismus",
    "nationalsozialist", "nsdap", "hitler",
]

def jahr_aus_dateiname(name):
    treffer = re.findall(r"(192[0-9]|193[0-9])", name)
    return int(treffer[0]) if treffer else None

# --- Texte einlesen und Seed-Terme zählen ---
txt_files = sorted(TXT_DIR.glob("*.txt"))
print(f"{len(txt_files)} Dateien gefunden.\n")

# Pro Jahrgang: Gesamtwörter und Term-Häufigkeiten
jahr_woerter = defaultdict(int)
jahr_term_counts = defaultdict(lambda: defaultdict(int))

# Pro Datei für CSV
datei_ergebnisse = []

for txt_file in txt_files:
    jahr = jahr_aus_dateiname(txt_file.name)
    if jahr is None:
        continue

    text = txt_file.read_text(encoding="utf-8", errors="replace").lower()
    woerter = re.findall(r"[a-zäöüß]+", text)
    gesamt = len(woerter)
    jahr_woerter[jahr] += gesamt

    term_counts = {}
    for term in SEED_TERME:
        count = woerter.count(term)
        term_counts[term] = count
        jahr_term_counts[jahr][term] += count

    row = {"Dateiname": txt_file.name, "Jahr": jahr, "Gesamtwoerter": gesamt}
    for term in SEED_TERME:
        row[term] = term_counts[term]
        row[f"{term}_ppm"] = round((term_counts[term] / gesamt) * 1_000_000, 1) if gesamt else 0
    datei_ergebnisse.append(row)

# --- CSV speichern ---
OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
felder = ["Dateiname", "Jahr", "Gesamtwoerter"] + SEED_TERME + [f"{t}_ppm" for t in SEED_TERME]
with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=felder)
    writer.writeheader()
    writer.writerows(datei_ergebnisse)

# --- Tabelle nach Jahrgang ausgeben ---
print(f"{'='*75}")
print("SEEDTERM-ANALYSE NACH JAHRGANG (Werte in ppm = pro Million Wörter)")
print(f"{'='*75}")
print(f"{'Term':<22} {'1929':>10} {'1930':>10} {'1931':>10}")
print(f"{'-'*22} {'-'*10} {'-'*10} {'-'*10}")

for term in SEED_TERME:
    werte = []
    for jahr in [1929, 1930, 1931]:
        gesamt = jahr_woerter[jahr]
        count = jahr_term_counts[jahr][term]
        ppm = round((count / gesamt) * 1_000_000, 1) if gesamt else 0
        werte.append(f"{ppm:>9.1f}")
    print(f"{term:<22} {'  '.join(werte)}")

print(f"\nGesamtwörter pro Jahrgang:")
for jahr in [1929, 1930, 1931]:
    print(f"  {jahr}: {jahr_woerter[jahr]:,} Wörter")

print(f"\nErgebnisse gespeichert: {OUTPUT_CSV}")
