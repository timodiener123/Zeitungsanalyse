"""
wandel_antisemitismus.py
Diachrone Analyse: Wie veränderte sich das antisemitische Vokabular
im Stadtwächter Osnabrück von 1929 bis 1931?

Methode:
- Für jeden jüdisch*-Treffer: Kontextfenster ±15 Wörter
- Zählt Kookurrenz-Treffer aus drei Vokabelkategorien (Wirtschaft / Rasse / Politik)
- Normalisiert auf 100 jüdisch*-Erwähnungen pro Jahr
- Speichert CSV + Liniendiagramm
"""

import re
import gc
import os
import csv
import glob
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")          # kein Display nötig
import matplotlib.pyplot as plt

# ─── Konfiguration ────────────────────────────────────────────────────────────
DATA_DIR = ("/home/nghm/Dokumente/Zeitungsanalyse/daten_txt/"
            "wetransfer_pdf-stadtwachter_2026-03-03_2338/pdf Stadtwächter/")
OUT_DIR  = "/home/nghm/Dokumente/Zeitungsanalyse/ergebnisse/"
CSV_OUT  = os.path.join(OUT_DIR, "antisemitismus_wandel.csv")
PLOT_OUT = os.path.join(OUT_DIR, "wandel_plot.png")

WINDOW = 15   # Wörter vor/nach Treffer

# ─── Anker-Begriffe (Treffer, deren Kontext analysiert wird) ─────────────────
ANKER = re.compile(
    r"\b(juden|jude|jüdisch\w*|judengeschäft|judenladen|judenf[ia]rm\w*|antisemit\w*)\b",
    re.IGNORECASE
)

# ─── Vokabel-Kategorien ───────────────────────────────────────────────────────
KATEGORIEN = {
    "Wirtschaft": re.compile(
        r"\b(geschäft\w*|geld\w*|kapital\w*|wucher\w*|kauf\w*|verkauf\w*|"
        r"warenhaus|warenhäuser|boykott\w*|laden|läden|finanz\w*|"
        r"handel\w*|händler|profit\w*|bank\w*|kredit\w*|schuld\w*|"
        r"konkurrenz|geschäftsmann|inhaber)\b",
        re.IGNORECASE
    ),
    "Rasse_Biologie": re.compile(
        r"\b(rasse\w*|blut\w*|abstammung\w*|parasit\w*|schmarotzer\w*|"
        r"fremdvölk\w*|fremdstämmig\w*|biologisch\w*|erblich\w*|"
        r"artfremd\w*|volksfremde?\w*|volk\w*|reinheit|unrein\w*|"
        r"talmud\w*|ritual\w*|schächt\w*|rein\w*)\b",
        re.IGNORECASE
    ),
    "Politik": re.compile(
        r"\b(marx\w*|bolschewi\w*|kommunis\w*|sozialdemo\w*|sozialis\w*|"
        r"presse\w*|regierung\w*|verrat\w*|partei\w*|system\w*|"
        r"republik\w*|parlament\w*|demokrat\w*|reaktion\w*|"
        r"propaganda\w*|agitation\w*|hetze\w*|lügen\w*)\b",
        re.IGNORECASE
    ),
}

# ─── Hilfsfunktion: Jahr aus Dateiname extrahieren ───────────────────────────
JAHR_RE = re.compile(r"(192[0-9]|193[0-9])")

def extrahiere_jahr(dateiname: str) -> int:
    m = JAHR_RE.search(dateiname)
    if m:
        return int(m.group(1))
    return 1929  # OCR-Dateien ohne Jahresangabe im Namen sind aus 1929

# ─── Hauptdatenstruktur ───────────────────────────────────────────────────────
# jahr → {"Wirtschaft": int, "Rasse_Biologie": int, "Politik": int, "anker": int}
stats: dict[int, dict[str, int]] = defaultdict(
    lambda: {"Wirtschaft": 0, "Rasse_Biologie": 0, "Politik": 0, "anker": 0}
)

# ─── Schleife über Dateien ────────────────────────────────────────────────────
alle_dateien = sorted(glob.glob(os.path.join(DATA_DIR, "*.txt")))
print(f"Dateien gefunden: {len(alle_dateien)}")

for i, filepath in enumerate(alle_dateien, 1):
    dateiname = os.path.basename(filepath)
    jahr = extrahiere_jahr(dateiname)
    if jahr not in (1929, 1930, 1931):
        print(f"[{i:3d}] Übersprungen (unbekanntes Jahr): {dateiname}")
        gc.collect()
        continue

    print(f"[{i:3d}] {dateiname}  →  {jahr}")

    try:
        with open(filepath, encoding="utf-8") as fh:
            text = fh.read()
    except Exception as e:
        print(f"     FEHLER: {e}")
        gc.collect()
        continue

    # Text in Wortliste für Fensterzugriff
    woerter = text.split()
    n = len(woerter)

    # Anker-Suche im Volltext (mit Position im Wort-Array)
    # Effizienter: einmal tokenisieren, dann Wort-für-Wort prüfen
    for idx, wort in enumerate(woerter):
        if ANKER.fullmatch(wort.strip(".,;:!?\"'()[]–—»«")):
            stats[jahr]["anker"] += 1

            # Kontextfenster
            start = max(0, idx - WINDOW)
            end   = min(n, idx + WINDOW + 1)
            fenster = " ".join(woerter[start:end])

            # Kategorien zählen
            for kat, pattern in KATEGORIEN.items():
                treffer = pattern.findall(fenster)
                stats[jahr][kat] += len(treffer)

    del text, woerter
    gc.collect()

# ─── Ergebnisse ausgeben ─────────────────────────────────────────────────────
print("\n" + "="*60)
print("ROHDATEN:")
for jahr in sorted(stats):
    s = stats[jahr]
    print(f"  {jahr}: Anker={s['anker']}  "
          f"Wirtschaft={s['Wirtschaft']}  "
          f"Rasse={s['Rasse_Biologie']}  "
          f"Politik={s['Politik']}")

# ─── Normalisierung (pro 100 Anker-Erwähnungen) ──────────────────────────────
jahre_sorted = sorted(stats.keys())
kategorien   = ["Wirtschaft", "Rasse_Biologie", "Politik"]

normiert: dict[int, dict[str, float]] = {}
for jahr in jahre_sorted:
    s = stats[jahr]
    anker = s["anker"] if s["anker"] > 0 else 1
    normiert[jahr] = {
        kat: round(s[kat] / anker * 100, 2)
        for kat in kategorien
    }

print("\nNORMIERT (pro 100 jüdisch*-Erwähnungen):")
for jahr in jahre_sorted:
    print(f"  {jahr}: {normiert[jahr]}")

# ─── CSV speichern ────────────────────────────────────────────────────────────
os.makedirs(OUT_DIR, exist_ok=True)
with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Jahr", "Anker_Gesamt"] + kategorien +
                    [f"{k}_norm" for k in kategorien])
    for jahr in jahre_sorted:
        s = stats[jahr]
        row = [jahr, s["anker"]] + [s[k] for k in kategorien] + \
              [normiert[jahr][k] for k in kategorien]
        writer.writerow(row)
print(f"\nCSV gespeichert: {CSV_OUT}")

# ─── Liniendiagramm ───────────────────────────────────────────────────────────
farben = {
    "Wirtschaft":     "#2196F3",   # blau
    "Rasse_Biologie": "#F44336",   # rot
    "Politik":        "#4CAF50",   # grün
}
labels = {
    "Wirtschaft":     "Wirtschaft",
    "Rasse_Biologie": "Rasse / Biologie",
    "Politik":        "Politik",
}

fig, ax = plt.subplots(figsize=(9, 5))

for kat in kategorien:
    werte = [normiert[j][kat] for j in jahre_sorted]
    ax.plot(jahre_sorted, werte,
            marker="o", linewidth=2.5, markersize=8,
            color=farben[kat], label=labels[kat])
    # Werte annotieren
    for j, w in zip(jahre_sorted, werte):
        ax.annotate(f"{w:.1f}",
                    xy=(j, w), xytext=(4, 6),
                    textcoords="offset points",
                    fontsize=9, color=farben[kat])

ax.set_title("Wandel des antisemitischen Vokabulars im Stadtwächter\n"
             "(Kookkurrenz pro 100 jüdisch*-Erwähnungen, ±15 Wörter Fenster)",
             fontsize=12, pad=14)
ax.set_xlabel("Jahr", fontsize=11)
ax.set_ylabel("Treffer pro 100 Erwähnungen", fontsize=11)
ax.set_xticks(jahre_sorted)
ax.legend(fontsize=10)
ax.grid(axis="y", alpha=0.4)
ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
plt.savefig(PLOT_OUT, dpi=150)
plt.close()
print(f"Diagramm gespeichert: {PLOT_OUT}")
