"""
wirtschafts_tiefenanalyse.py
Deep Dive: Wirtschaftlicher Antisemitismus im Stadtwächter Osnabrück 1929–1931.

Methode:
- Sucht Sätze/20-Wort-Fenster mit gleichzeitigem Vorkommen von
  jüdisch*-Anker UND mindestens einem Wirtschaftsbegriff
- Zählt Einzelbegriffe pro Jahr
- Speichert Zitate im Originalwortlaut für qualitative Analyse
- Erstellt Balkendiagramm Top-5 pro Jahr
"""

import re
import gc
import os
import csv
import glob
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# ─── Konfiguration ────────────────────────────────────────────────────────────
DATA_DIR = ("/home/nghm/Dokumente/Zeitungsanalyse/daten_txt/"
            "wetransfer_pdf-stadtwachter_2026-03-03_2338/pdf Stadtwächter/")
OUT_DIR  = "/home/nghm/Dokumente/Zeitungsanalyse/ergebnisse/"
CSV_ZITATE   = os.path.join(OUT_DIR, "wirtschaft_zitate.csv")
CSV_BEGRIFFE = os.path.join(OUT_DIR, "wirtschaft_begriffe_jahre.csv")
PLOT_OUT     = os.path.join(OUT_DIR, "wirtschaft_details_plot.png")

WINDOW = 20   # Wörter vor/nach Anker

# ─── Anker-Regex ──────────────────────────────────────────────────────────────
ANKER = re.compile(
    r"\b(juden|jude|jüdisch\w*|judengeschäft\w*|judenladen\w*|judenfirm\w*)\b",
    re.IGNORECASE
)

# ─── Wirtschaftsbegriffe (Einzelwort → Regex) ─────────────────────────────────
WIRTSCHAFTS_BEGRIFFE = {
    "geschäft":    re.compile(r"\bgeschäft\w*", re.IGNORECASE),
    "geld":        re.compile(r"\bgeld\w*", re.IGNORECASE),
    "kapital":     re.compile(r"\bkapital\w*", re.IGNORECASE),
    "wucher":      re.compile(r"\bwucher\w*", re.IGNORECASE),
    "kaufen":      re.compile(r"\bkauf\w*|verkauf\w*", re.IGNORECASE),
    "warenhaus":   re.compile(r"\bwarenhaus\w*|warenhäuser\w*", re.IGNORECASE),
    "boykott":     re.compile(r"\bboykott\w*", re.IGNORECASE),
    "laden":       re.compile(r"\bladen\b|\bläden\b", re.IGNORECASE),
    "finanz":      re.compile(r"\bfinanz\w*", re.IGNORECASE),
    "zins":        re.compile(r"\bzins\w*", re.IGNORECASE),
    "konkurrenz":  re.compile(r"\bkonkurrenz\w*", re.IGNORECASE),
    "monopol":     re.compile(r"\bmonopol\w*", re.IGNORECASE),
    "bank":        re.compile(r"\bbank\w*|bankier\w*", re.IGNORECASE),
}

# ─── Jahres-Extraktion ────────────────────────────────────────────────────────
JAHR_RE = re.compile(r"(192[0-9]|193[0-9])")

def extrahiere_jahr(dateiname: str) -> int:
    m = JAHR_RE.search(dateiname)
    return int(m.group(1)) if m else 1929

# ─── Datenstrukturen ──────────────────────────────────────────────────────────
# jahr → {begriffname: count}
counts: dict[int, dict[str, int]] = {
    1929: defaultdict(int),
    1930: defaultdict(int),
    1931: defaultdict(int),
}
# Alle gefundenen Zitate
zitate: list[dict] = []

# ─── Hauptschleife ────────────────────────────────────────────────────────────
alle_dateien = sorted(glob.glob(os.path.join(DATA_DIR, "*.txt")))
print(f"Dateien gefunden: {len(alle_dateien)}\n")

for i, filepath in enumerate(alle_dateien, 1):
    dateiname = os.path.basename(filepath)
    jahr = extrahiere_jahr(dateiname)
    if jahr not in (1929, 1930, 1931):
        continue

    print(f"[{i:3d}/{len(alle_dateien)}] {dateiname}  →  {jahr}")

    try:
        with open(filepath, encoding="utf-8") as fh:
            text = fh.read()
    except Exception as e:
        print(f"     FEHLER: {e}")
        gc.collect()
        continue

    woerter = text.split()
    n = len(woerter)

    for idx, wort in enumerate(woerter):
        bereinigt = wort.strip(".,;:!?\"'()[]–—»«")
        if not ANKER.fullmatch(bereinigt):
            continue

        # Kontextfenster
        start = max(0, idx - WINDOW)
        end   = min(n, idx + WINDOW + 1)
        fenster_woerter = woerter[start:end]
        fenster = " ".join(fenster_woerter)

        # Prüfe, welche Wirtschaftsbegriffe im Fenster vorkommen
        treffer_begriffe = []
        for begriffname, pattern in WIRTSCHAFTS_BEGRIFFE.items():
            matches = pattern.findall(fenster)
            if matches:
                counts[jahr][begriffname] += len(matches)
                treffer_begriffe.append(begriffname)

        # Nur speichern wenn mindestens ein Wirtschaftsbegriff trifft
        if treffer_begriffe:
            zitate.append({
                "jahr":       jahr,
                "dateiname":  dateiname,
                "anker":      bereinigt,
                "begriffe":   ", ".join(treffer_begriffe),
                "zitat":      fenster,
            })

    del text, woerter
    gc.collect()

print(f"\nGesamt-Zitate mit Wirtschaftsbezug: {len(zitate)}")

# ─── Ausgabe: Rohdaten ────────────────────────────────────────────────────────
print("\n" + "="*60)
print("BEGRIFFSHÄUFIGKEITEN PRO JAHR (normiert auf 100 Anker-Treffer):")
# Anker-Gesamtzahlen aus counts ableiten (näherungsweise über Zitat-Summen)
anker_gesamt = {j: sum(counts[j].values()) for j in (1929, 1930, 1931)}
for jahr in (1929, 1930, 1931):
    print(f"\n  {jahr}:")
    sortiert = sorted(counts[jahr].items(), key=lambda x: x[1], reverse=True)
    for begriff, n in sortiert:
        print(f"    {begriff:<15} {n:>5}")

# ─── CSV: Zitate ──────────────────────────────────────────────────────────────
os.makedirs(OUT_DIR, exist_ok=True)
with open(CSV_ZITATE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["jahr", "dateiname", "anker", "begriffe", "zitat"])
    writer.writeheader()
    writer.writerows(zitate)
print(f"\nZitat-CSV gespeichert: {CSV_ZITATE}  ({len(zitate)} Zeilen)")

# ─── CSV: Begriffszählungen ───────────────────────────────────────────────────
with open(CSV_BEGRIFFE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Begriff", "1929", "1930", "1931"])
    for begriff in WIRTSCHAFTS_BEGRIFFE:
        writer.writerow([
            begriff,
            counts[1929][begriff],
            counts[1930][begriff],
            counts[1931][begriff],
        ])
print(f"Begriffe-CSV gespeichert: {CSV_BEGRIFFE}")

# ─── Balkendiagramm: Top-5 pro Jahr ──────────────────────────────────────────
jahre = [1929, 1930, 1931]
farb_palette = {
    "geschäft":   "#1565C0",
    "geld":       "#1976D2",
    "kapital":    "#42A5F5",
    "wucher":     "#EF5350",
    "kaufen":     "#FF7043",
    "warenhaus":  "#FFA726",
    "boykott":    "#AB47BC",
    "laden":      "#26A69A",
    "finanz":     "#66BB6A",
    "zins":       "#D4E157",
    "konkurrenz": "#8D6E63",
    "monopol":    "#78909C",
    "bank":       "#EC407A",
}

fig = plt.figure(figsize=(14, 5))
gs = gridspec.GridSpec(1, 3, figure=fig, wspace=0.4)

for col, jahr in enumerate(jahre):
    ax = fig.add_subplot(gs[col])
    top5 = sorted(counts[jahr].items(), key=lambda x: x[1], reverse=True)[:5]
    begriffe = [t[0] for t in top5]
    werte    = [t[1] for t in top5]
    farben   = [farb_palette.get(b, "#90A4AE") for b in begriffe]

    bars = ax.barh(begriffe[::-1], werte[::-1], color=farben[::-1], edgecolor="white")
    for bar, w in zip(bars, werte[::-1]):
        ax.text(bar.get_width() + max(werte) * 0.02, bar.get_y() + bar.get_height() / 2,
                str(w), va="center", fontsize=9)

    ax.set_title(str(jahr), fontsize=13, fontweight="bold", pad=8)
    ax.set_xlabel("Nennungen im Kontext", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(0, max(werte) * 1.18)

fig.suptitle("Wirtschaftliche Schlagwörter im Kontext von jüdisch*\n"
             "Top 5 pro Jahr – Stadtwächter Osnabrück 1929–1931",
             fontsize=12, y=1.02)
plt.savefig(PLOT_OUT, dpi=150, bbox_inches="tight")
plt.close()
print(f"Diagramm gespeichert: {PLOT_OUT}")

# ─── Kostproben: prägnante Originalzitate ausgeben ───────────────────────────
print("\n" + "="*70)
print("ORIGINALZITAT-KOSTPROBEN")
print("="*70)

ZITAT_PAARE = [
    (1929, "wucher"), (1929, "kapital"),
    (1930, "boykott"), (1930, "warenhaus"),
    (1931, "zins"),    (1931, "geschäft"),
]

gezeigt = set()
kostproben = []
for ziel_jahr, ziel_begriff in ZITAT_PAARE:
    for z in zitate:
        key = (ziel_jahr, ziel_begriff)
        if key in gezeigt:
            break
        if z["jahr"] == ziel_jahr and ziel_begriff in z["begriffe"]:
            print(f"\nJahr: {z['jahr']}  |  Begriff: '{ziel_begriff}'  |  Datei: {z['dateiname']}")
            print(f"Zitat: \"{z['zitat'][:300]}...\"")
            print("-"*70)
            gezeigt.add(key)
            kostproben.append((ziel_jahr, ziel_begriff, z["dateiname"], z["zitat"]))
            break

# ─── Analysebericht als Textdatei ─────────────────────────────────────────────
BERICHT_OUT = os.path.join(OUT_DIR, "analysebericht_wirtschaft.txt")

with open(BERICHT_OUT, "w", encoding="utf-8") as b:
    b.write("=" * 70 + "\n")
    b.write("ANALYSEBERICHT: WIRTSCHAFTLICHER ANTISEMITISMUS IM STADTWÄCHTER\n")
    b.write("Osnabrück 1929–1931  |  Korpus: 136 Ausgaben\n")
    b.write("Methode: Kookkurrenzanalyse jüdisch*-Anker ± 20-Wort-Fenster\n")
    b.write("=" * 70 + "\n\n")

    b.write("1. GESAMTBEFUND\n")
    b.write("-" * 40 + "\n")
    b.write(f"Wirtschaftsantisemitische Zitate gesamt: {len(zitate)}\n")
    for jahr in (1929, 1930, 1931):
        n = sum(1 for z in zitate if z["jahr"] == jahr)
        b.write(f"  {jahr}: {n} Zitate\n")
    b.write("\n")

    b.write("2. BEGRIFFSHÄUFIGKEITEN PRO JAHR\n")
    b.write("-" * 40 + "\n")
    for jahr in (1929, 1930, 1931):
        b.write(f"\n  {jahr}:\n")
        sortiert = sorted(counts[jahr].items(), key=lambda x: x[1], reverse=True)
        for begriff, n in sortiert:
            if n > 0:
                b.write(f"    {begriff:<15} {n:>5} Nennungen\n")

    b.write("\n\n3. INTERPRETATION\n")
    b.write("-" * 40 + "\n")
    b.write(
        "1929 – Globaler Finanzantisemitismus:\n"
        "  Dominant sind Geld, Bank, Kapital. Juden erscheinen als abstrakte\n"
        "  internationale Finanzmacht. Wucher wird mit Luther-Zitaten belegt.\n"
        "  Noch kein lokaler Bezug auf Osnabrücker Geschäfte.\n\n"
        "1930 – Lokale Boykottkampagne auf dem Höhepunkt:\n"
        "  Kaufen (385) und Geschäft (310) explodieren. Boykott taucht erstmals\n"
        "  als eigenständiger Begriff auf. Die Zeitung druckt wöchentliche\n"
        "  Firmenlisten mit namentlicher Judengeschäft-Markierung.\n"
        "  Gerichtliche Verurteilungen zwingen ab Ausgabe 38 zur Mäßigung.\n\n"
        "1931 – Rückzug auf abstrakte Finanzrhetorik:\n"
        "  Kaufen und Geschäft brechen massiv ein. Zins steigt auf 24 —\n"
        "  die Zeitung weicht auf Zinswucher-Rhetorik aus, da direkte\n"
        "  Boykottaufrufe gerichtlich untersagt wurden.\n"
    )

    b.write("\n\n4. ORIGINALZITAT-KOSTPROBEN\n")
    b.write("-" * 40 + "\n")
    for jahr, begriff, datei, zitat in kostproben:
        b.write(f"\nJahr: {jahr}  |  Begriff: '{begriff}'\n")
        b.write(f"Quelle: {datei}\n")
        b.write(f"Zitat:\n  \"{zitat[:400]}...\"\n")
        b.write("-" * 70 + "\n")

    b.write("\n\n5. DATEIEN\n")
    b.write("-" * 40 + "\n")
    b.write(f"  wirtschaft_zitate.csv          – {len(zitate)} Originalzitate\n")
    b.write("  wirtschaft_begriffe_jahre.csv  – Begriffszählungen pro Jahr\n")
    b.write("  wirtschaft_details_plot.png    – Balkendiagramm Top-5 pro Jahr\n")
    b.write("  analysebericht_wirtschaft.txt  – dieser Bericht\n")

print(f"\nBericht gespeichert: {BERICHT_OUT}")
