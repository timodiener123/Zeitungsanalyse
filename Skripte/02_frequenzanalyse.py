import csv
from collections import Counter

EINGABE = "/home/nghm/Dokumente/Zeitungsanalyse/ergebnisse/tokenisierung.csv"
AUSGABE = "/home/nghm/Dokumente/Zeitungsanalyse/ergebnisse/frequenzanalyse_top50_v2.csv"

print("Lese tokenisierung.csv...")

lemma_zaehler = Counter()
gesamt_tokens = 0

with open(EINGABE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for zeile in reader:
        lemma_zaehler[zeile["lemma"]] += 1
        gesamt_tokens += 1

print(f"Tokens gelesen: {gesamt_tokens:,}")

# Normalisierung: Häufigkeit pro Million Wörter
top50 = lemma_zaehler.most_common(50)

with open(AUSGABE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Rang", "Lemma", "Häufigkeit", "Pro_Million"])
    for rang, (lemma, haeufigkeit) in enumerate(top50, start=1):
        pro_million = round(haeufigkeit / gesamt_tokens * 1_000_000, 2)
        writer.writerow([rang, lemma, haeufigkeit, pro_million])

print(f"Ergebnis gespeichert: {AUSGABE}")
print(f"\nTop 20 Lemmata:")
print(f"{'Rang':>4}  {'Lemma':<25} {'Häufigkeit':>10}  {'pro Mio.':>10}")
print("-" * 55)
for rang, (lemma, n) in enumerate(top50[:20], start=1):
    ppm = n / gesamt_tokens * 1_000_000
    print(f"{rang:>4}  {lemma:<25} {n:>10,}  {ppm:>10.1f}")

print(f"\nGesamt verarbeitete Tokens: {gesamt_tokens:,}")
