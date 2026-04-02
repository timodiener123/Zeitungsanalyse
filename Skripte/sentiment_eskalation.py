"""
sentiment_eskalation.py
Sentiment-Analyse der emotionalen Eskalation rund um antisemitische Begriffe
im Stadtwächter Osnabrück 1929–1931.

Methode:
- Satzweise Suche nach jüdisch*-Ankern
- TextBlobDE-Polarität pro Satz (-1.0 = stark negativ, +1.0 = stark positiv)
- Jahres-Durchschnitt + Verteilung
- Liniendiagramm + Boxplot
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
import numpy as np

from textblob_de import TextBlobDE

# ─── Konfiguration ────────────────────────────────────────────────────────────
DATA_DIR = ("/home/nghm/Dokumente/Zeitungsanalyse/daten_txt/"
            "wetransfer_pdf-stadtwachter_2026-03-03_2338/pdf Stadtwächter/")
OUT_DIR  = "/home/nghm/Dokumente/Zeitungsanalyse/ergebnisse/"
CSV_OUT  = os.path.join(OUT_DIR, "sentiment_entwicklung.csv")
PLOT_OUT = os.path.join(OUT_DIR, "sentiment_plot.png")

# ─── Anker-Regex ──────────────────────────────────────────────────────────────
ANKER = re.compile(
    r"\b(juden|jude|jüdisch\w*|judengeschäft\w*|judenladen\w*|judenfirm\w*)\b",
    re.IGNORECASE
)

# ─── Jahres-Extraktion ────────────────────────────────────────────────────────
JAHR_RE = re.compile(r"(192[0-9]|193[0-9])")

def extrahiere_jahr(dateiname: str) -> int:
    m = JAHR_RE.search(dateiname)
    return int(m.group(1)) if m else 1929

# ─── Satztrennung (einfach, kein NLTK nötig) ─────────────────────────────────
SATZ_TRENN = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])")

def split_saetze(text: str) -> list[str]:
    return [s.strip() for s in SATZ_TRENN.split(text) if len(s.strip()) > 15]

# ─── Datenstruktur ────────────────────────────────────────────────────────────
# jahr → Liste von Polaritätswerten
polaritaeten: dict[int, list[float]] = {1929: [], 1930: [], 1931: []}
# Für CSV: alle Einzelsätze mit Score
alle_saetze: list[dict] = []

# ─── Hauptschleife ────────────────────────────────────────────────────────────
alle_dateien = sorted(glob.glob(os.path.join(DATA_DIR, "*.txt")))
print(f"Dateien gefunden: {len(alle_dateien)}\n")

for i, filepath in enumerate(alle_dateien, 1):
    dateiname = os.path.basename(filepath)
    jahr = extrahiere_jahr(dateiname)
    if jahr not in (1929, 1930, 1931):
        continue

    try:
        with open(filepath, encoding="utf-8") as fh:
            text = fh.read()
    except Exception as e:
        print(f"[{i:3d}] FEHLER {dateiname}: {e}")
        gc.collect()
        continue

    saetze = split_saetze(text)
    treffer_n = 0

    for satz in saetze:
        if not ANKER.search(satz):
            continue
        # Satz auf max. 500 Zeichen kürzen (RAM + Geschwindigkeit)
        satz_kurz = satz[:500]
        try:
            blob = TextBlobDE(satz_kurz)
            pol  = blob.sentiment.polarity
        except Exception:
            continue

        polaritaeten[jahr].append(pol)
        alle_saetze.append({
            "jahr":      jahr,
            "dateiname": dateiname,
            "polaritaet": round(pol, 4),
            "satz":      satz_kurz,
        })
        treffer_n += 1

    print(f"[{i:3d}/{len(alle_dateien)}] {dateiname}  →  {jahr}  "
          f"({treffer_n} Treffersätze)")

    del text, saetze
    gc.collect()

# ─── Statistiken berechnen ───────────────────────────────────────────────────
print("\n" + "="*60)
print("SENTIMENT-STATISTIK PRO JAHR")
print("="*60)

statistik = {}
for jahr in (1929, 1930, 1931):
    werte = polaritaeten[jahr]
    if not werte:
        continue
    arr = np.array(werte)
    s = {
        "jahr":       jahr,
        "n_saetze":   len(werte),
        "mittelwert": round(float(arr.mean()), 5),
        "median":     round(float(np.median(arr)), 5),
        "std":        round(float(arr.std()), 5),
        "min":        round(float(arr.min()), 5),
        "max":        round(float(arr.max()), 5),
        "anteil_neg": round(float((arr < 0).sum() / len(arr) * 100), 1),
        "anteil_pos": round(float((arr > 0).sum() / len(arr) * 100), 1),
        "anteil_neu": round(float((arr == 0).sum() / len(arr) * 100), 1),
    }
    statistik[jahr] = s
    print(f"\n{jahr}:")
    print(f"  Sätze analysiert : {s['n_saetze']}")
    print(f"  Ø Polarität      : {s['mittelwert']:+.5f}")
    print(f"  Median           : {s['median']:+.5f}")
    print(f"  Std.abw.         : {s['std']:.5f}")
    print(f"  Min / Max        : {s['min']:+.3f} / {s['max']:+.3f}")
    print(f"  Anteil negativ   : {s['anteil_neg']}%")
    print(f"  Anteil positiv   : {s['anteil_pos']}%")
    print(f"  Anteil neutral   : {s['anteil_neu']}%")

# ─── CSV speichern ────────────────────────────────────────────────────────────
os.makedirs(OUT_DIR, exist_ok=True)

# Statistik-CSV (Hauptdatei)
with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
    felder = ["jahr", "n_saetze", "mittelwert", "median", "std",
              "min", "max", "anteil_neg", "anteil_pos", "anteil_neu"]
    writer = csv.DictWriter(f, fieldnames=felder)
    writer.writeheader()
    for jahr in (1929, 1930, 1931):
        if jahr in statistik:
            writer.writerow(statistik[jahr])
print(f"\nStatistik-CSV gespeichert: {CSV_OUT}")

# Einzelsatz-CSV (für qualitative Analyse)
csv_saetze = os.path.join(OUT_DIR, "sentiment_saetze.csv")
with open(csv_saetze, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["jahr", "dateiname", "polaritaet", "satz"])
    writer.writeheader()
    writer.writerows(alle_saetze)
print(f"Einzelsatz-CSV gespeichert: {csv_saetze}  ({len(alle_saetze)} Sätze)")

# ─── Diagramm ────────────────────────────────────────────────────────────────
jahre   = sorted(statistik.keys())
mittel  = [statistik[j]["mittelwert"]  for j in jahre]
median  = [statistik[j]["median"]      for j in jahre]
neg_ant = [statistik[j]["anteil_neg"]  for j in jahre]
std     = [statistik[j]["std"]         for j in jahre]

fig = plt.figure(figsize=(14, 9))
gs  = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)

# ── Panel 1: Mittlere Polarität mit Std-Band ──────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
ax1.axhline(0, color="gray", linewidth=0.8, linestyle="--", alpha=0.6)
ax1.fill_between(jahre,
                 [m - s for m, s in zip(mittel, std)],
                 [m + s for m, s in zip(mittel, std)],
                 alpha=0.18, color="#EF5350")
ax1.plot(jahre, mittel, marker="o", linewidth=2.5, color="#EF5350",
         markersize=9, label="Ø Polarität")
ax1.plot(jahre, median, marker="s", linewidth=1.8, color="#B71C1C",
         linestyle="--", markersize=7, label="Median")
for j, m in zip(jahre, mittel):
    ax1.annotate(f"{m:+.4f}", (j, m), textcoords="offset points",
                 xytext=(5, 8), fontsize=9, color="#EF5350")
ax1.set_title("Ø Sentiment-Polarität\n(±1 Std.abw. Band)", fontsize=11)
ax1.set_ylabel("Polarität (−1 neg. / +1 pos.)")
ax1.set_xticks(jahre)
ax1.legend(fontsize=9)
ax1.grid(axis="y", alpha=0.3)
ax1.spines[["top", "right"]].set_visible(False)

# ── Panel 2: Anteil negativer Sätze ──────────────────────────────────────────
ax2 = fig.add_subplot(gs[0, 1])
balken = ax2.bar(jahre, neg_ant, color="#5C6BC0", width=0.4, alpha=0.85)
for bar, v in zip(balken, neg_ant):
    ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
             f"{v}%", ha="center", fontsize=10, color="#1A237E")
ax2.set_title("Anteil negativer Sätze (%)", fontsize=11)
ax2.set_ylabel("Prozent")
ax2.set_xticks(jahre)
ax2.set_ylim(0, max(neg_ant) * 1.2)
ax2.grid(axis="y", alpha=0.3)
ax2.spines[["top", "right"]].set_visible(False)

# ── Panel 3: Boxplot der Verteilungen ────────────────────────────────────────
ax3 = fig.add_subplot(gs[1, 0])
box_data = [polaritaeten[j] for j in jahre]
bp = ax3.boxplot(box_data, labels=[str(j) for j in jahre],
                 patch_artist=True, notch=False,
                 medianprops=dict(color="white", linewidth=2))
farben_box = ["#5C6BC0", "#EF5350", "#26A69A"]
for patch, farbe in zip(bp["boxes"], farben_box):
    patch.set_facecolor(farbe)
    patch.set_alpha(0.75)
ax3.axhline(0, color="gray", linewidth=0.8, linestyle="--", alpha=0.6)
ax3.set_title("Verteilung der Polaritätswerte\n(Boxplot)", fontsize=11)
ax3.set_ylabel("Polarität")
ax3.grid(axis="y", alpha=0.3)
ax3.spines[["top", "right"]].set_visible(False)

# ── Panel 4: Satzanzahl ───────────────────────────────────────────────────────
ax4 = fig.add_subplot(gs[1, 1])
n_saetze = [statistik[j]["n_saetze"] for j in jahre]
balken4 = ax4.bar(jahre, n_saetze, color="#26A69A", width=0.4, alpha=0.85)
for bar, v in zip(balken4, n_saetze):
    ax4.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
             str(v), ha="center", fontsize=10, color="#004D40")
ax4.set_title("Analysierte Sätze mit\nantisemitischen Begriffen", fontsize=11)
ax4.set_ylabel("Anzahl Sätze")
ax4.set_xticks(jahre)
ax4.grid(axis="y", alpha=0.3)
ax4.spines[["top", "right"]].set_visible(False)

fig.suptitle("Sentiment-Analyse antisemitischer Sätze im Stadtwächter Osnabrück\n"
             "Emotionale Eskalation 1929–1931",
             fontsize=13, y=1.01)
plt.savefig(PLOT_OUT, dpi=150, bbox_inches="tight")
plt.close()
print(f"Diagramm gespeichert: {PLOT_OUT}")

# ─── Extreme Sätze ausgeben ───────────────────────────────────────────────────
print("\n" + "="*70)
print("DIE 3 NEGATIVSTEN SÄTZE PRO JAHR:")
print("="*70)
for jahr in (1929, 1930, 1931):
    jahr_saetze = sorted(
        [s for s in alle_saetze if s["jahr"] == jahr],
        key=lambda x: x["polaritaet"]
    )
    print(f"\n── {jahr} ──")
    for s in jahr_saetze[:3]:
        print(f"  Score {s['polaritaet']:+.4f} | {s['dateiname']}")
        print(f"  \"{s['satz'][:200]}...\"")
