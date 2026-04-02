"""
historische_eskalation.py
Regelbasiertes Eskalationsmodell für historischen Antisemitismus 1929-1931.

Eskalationsstufen (höchste zutreffende gewinnt: 3 → 2 → 1 → 0):

  Stufe 0 – Bloße Nennung (kein Eskalationsmarker)

  Stufe 1 – Wirtschaftliche Diffamierung:
    wucher, betrug, schwindel, ausbeutung, schacher, lüge, verrat, falsch ...
    (Im Auftragstext hatten Stufe 1+2 identische Listen – hier logisch getrennt)

  Stufe 2 – Aufruf / Boykott / Ausgrenzung:
    kauft nicht, meidet, boykott, raus, verbieten, schließen, forderung ...
    (Exakt die vom Nutzer angegebene Liste)

  Stufe 3 – Biologische Entmenschlichung:
    rasse, blut, parasit, schädling, schmarotzer, geschwür, fremd ...
    (Exakt die vom Nutzer angegebene Liste)
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
import numpy as np

# ─── Konfiguration ────────────────────────────────────────────────────────────
DATA_DIR = ("/home/nghm/Dokumente/Zeitungsanalyse/daten_txt/"
            "wetransfer_pdf-stadtwachter_2026-03-03_2338/pdf Stadtwächter/")
OUT_DIR  = "/home/nghm/Dokumente/Zeitungsanalyse/ergebnisse/"
CSV_OUT  = os.path.join(OUT_DIR, "eskalationsstufen_jahre.csv")
PLOT_OUT = os.path.join(OUT_DIR, "eskalation_plot.png")

# ─── Anker ────────────────────────────────────────────────────────────────────
ANKER = re.compile(
    r"\b(juden|jude|jüdisch\w*|judengeschäft\w*|judenladen\w*|judenfirm\w*)\b",
    re.IGNORECASE
)

# ─── Satztrennung ─────────────────────────────────────────────────────────────
SATZ_TRENN = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])")

def split_saetze(text: str) -> list[str]:
    return [s.strip() for s in SATZ_TRENN.split(text) if len(s.strip()) > 10]

# ─── Eskalationsstufen ────────────────────────────────────────────────────────
STUFE = {
    # Stufe 3: Biologische Entmenschlichung (exakt aus Auftragstext)
    3: re.compile(
        r"\b(rasse\w*|blut\w*|parasit\w*|schädling\w*|schmarotzer\w*|"
        r"geschwür\w*|fremd\w*|ungeziefer\w*|ausrott\w*|vernicht\w*|"
        r"artfremd\w*|volksfremde?\w*|entart\w*|untermenschen?\w*)\b",
        re.IGNORECASE
    ),
    # Stufe 2: Aufruf/Boykott (exakt aus Auftragstext)
    2: re.compile(
        r"\b(boykott\w*|meid\w*|kauft?\s+nicht|kauft?\s+nie|"
        r"raus\b|verbiet\w*|schließ\w*|forderung\w*|"
        r"verjag\w*|vertreib\w*|ausschließ\w*|heraus\s+mit|weg\s+mit)\b",
        re.IGNORECASE
    ),
    # Stufe 1: Wirtschaftliche Diffamierung (logische Ergänzung für Trennschärfe)
    1: re.compile(
        r"\b(wucher\w*|betrug\w*|betrüg\w*|schwindel\w*|ausbeutung\w*|"
        r"ausbeut\w*|schacher\w*|lüg\w*|verrat\w*|falsch\w*|"
        r"raffgier\w*|habgier\w*|hinterlist\w*|geldgier\w*|"
        r"übervorteilu\w*|profitgier\w*|monopol\w*)\b",
        re.IGNORECASE
    ),
}

# ─── Jahres-Extraktion ────────────────────────────────────────────────────────
JAHR_RE = re.compile(r"(192[0-9]|193[0-9])")

def extrahiere_jahr(dateiname: str) -> int:
    m = JAHR_RE.search(dateiname)
    return int(m.group(1)) if m else 1929

# ─── Datenstruktur ────────────────────────────────────────────────────────────
zaehler: dict[int, dict[int, int]] = {
    j: {0: 0, 1: 0, 2: 0, 3: 0} for j in (1929, 1930, 1931)
}
beispiele: dict[tuple, list[str]] = defaultdict(list)

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
        print(f"[{i:3d}] FEHLER: {e}")
        gc.collect()
        continue

    saetze = split_saetze(text)
    lokal  = {0: 0, 1: 0, 2: 0, 3: 0}

    for satz in saetze:
        if not ANKER.search(satz):
            continue

        stufe = 0
        for s in (3, 2, 1):
            if STUFE[s].search(satz):
                stufe = s
                break

        zaehler[jahr][stufe] += 1
        lokal[stufe]         += 1

        key = (jahr, stufe)
        if len(beispiele[key]) < 3:
            beispiele[key].append(satz[:280])

    gesamt = sum(lokal.values())
    print(f"[{i:3d}/{len(alle_dateien)}] {dateiname}  →  {jahr}  "
          f"({gesamt} Sätze | "
          f"S0:{lokal[0]} S1:{lokal[1]} S2:{lokal[2]} S3:{lokal[3]})")

    del text, saetze
    gc.collect()

# ─── Statistik ───────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("ESKALATIONSSTUFEN PRO JAHR")
print("="*65)

statistik = {}
for jahr in (1929, 1930, 1931):
    z = zaehler[jahr]
    g = sum(z.values()) or 1
    s = {
        "jahr":   jahr,  "gesamt": g,
        "s0": z[0], "s0_pct": round(z[0]/g*100, 1),
        "s1": z[1], "s1_pct": round(z[1]/g*100, 1),
        "s2": z[2], "s2_pct": round(z[2]/g*100, 1),
        "s3": z[3], "s3_pct": round(z[3]/g*100, 1),
    }
    statistik[jahr] = s
    print(f"\n{jahr}  (Gesamt: {g} Sätze)")
    print(f"  Stufe 0 – Nennung             : {z[0]:5d}  ({s['s0_pct']:5.1f}%)")
    print(f"  Stufe 1 – Diffamierung/Wirtsch.: {z[1]:5d}  ({s['s1_pct']:5.1f}%)")
    print(f"  Stufe 2 – Boykott/Aufruf      : {z[2]:5d}  ({s['s2_pct']:5.1f}%)")
    print(f"  Stufe 3 – Entmenschlichung    : {z[3]:5d}  ({s['s3_pct']:5.1f}%)")
    print(f"  → Schwere Eskalation (2+3)    :         "
          f"({s['s2_pct']+s['s3_pct']:.1f}%)")

# ─── CSV ─────────────────────────────────────────────────────────────────────
os.makedirs(OUT_DIR, exist_ok=True)
felder = ["jahr","gesamt","s0","s0_pct","s1","s1_pct","s2","s2_pct","s3","s3_pct"]
with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=felder)
    writer.writeheader()
    for j in (1929, 1930, 1931):
        writer.writerow(statistik[j])
print(f"\nCSV gespeichert: {CSV_OUT}")

# ─── Diagramm: Stacked Area + Gruppenbalken ───────────────────────────────────
jahre  = [1929, 1930, 1931]
s0_p   = [statistik[j]["s0_pct"] for j in jahre]
s1_p   = [statistik[j]["s1_pct"] for j in jahre]
s2_p   = [statistik[j]["s2_pct"] for j in jahre]
s3_p   = [statistik[j]["s3_pct"] for j in jahre]

FARBEN = ["#CFD8DC", "#FFA726", "#EF5350", "#7B1FA2"]
LABELS = [
    "Stufe 0 – Nennung",
    "Stufe 1 – Diffamierung",
    "Stufe 2 – Boykott/Aufruf",
    "Stufe 3 – Entmenschlichung",
]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
fig.subplots_adjust(wspace=0.38)

# Panel 1: Stacked Area
ax1.stackplot(jahre, s0_p, s1_p, s2_p, s3_p,
              labels=LABELS, colors=FARBEN, alpha=0.88)
ax1.set_xlim(1929, 1931)
ax1.set_ylim(0, 100)
ax1.set_xticks(jahre)
ax1.set_ylabel("Anteil Sätze (%)")
ax1.set_title("Stacked Area\nEskalationsstufen 0–3", fontsize=11)
ax1.legend(loc="upper left", fontsize=8.5, framealpha=0.85)
ax1.grid(axis="y", alpha=0.3)
ax1.spines[["top", "right"]].set_visible(False)

# Panel 2: Gruppenbalken Stufen 1–3
x = np.arange(len(jahre))
b = 0.22
for off, (stufe, data, farbe) in enumerate([
        (1, s1_p, FARBEN[1]),
        (2, s2_p, FARBEN[2]),
        (3, s3_p, FARBEN[3])]):
    bars = ax2.bar(x + off*b, data, b, label=LABELS[stufe],
                   color=farbe, alpha=0.88)
    for bar, v in zip(bars, data):
        ax2.text(bar.get_x() + bar.get_width()/2,
                 bar.get_height() + 0.3,
                 f"{v:.1f}%", ha="center", fontsize=8.5)

ax2.set_xticks(x + b)
ax2.set_xticklabels([str(j) for j in jahre])
ax2.set_ylabel("Anteil Sätze (%)")
ax2.set_title("Stufen 1–3 im Jahresvergleich\n(ohne Stufe 0)", fontsize=11)
ax2.legend(fontsize=8.5)
ax2.grid(axis="y", alpha=0.3)
ax2.spines[["top", "right"]].set_visible(False)

fig.suptitle(
    "Historisches Eskalationsmodell – Stadtwächter Osnabrück 1929–1931\n"
    "Diffamierung  →  Boykott/Aufruf  →  Biologische Entmenschlichung",
    fontsize=12, y=1.02)
plt.savefig(PLOT_OUT, dpi=150, bbox_inches="tight")
plt.close()
print(f"Diagramm gespeichert: {PLOT_OUT}")

# ─── Belegsätze ───────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("BELEGSÄTZE (je 1 Beispiel pro Stufe 2 und 3 pro Jahr):")
print("="*70)
stufennamen = {2: "Boykott/Aufruf", 3: "Entmenschlichung"}
for jahr in (1929, 1930, 1931):
    for stufe in (2, 3):
        belege = beispiele.get((jahr, stufe), [])
        if belege:
            print(f"\n{jahr} | Stufe {stufe} – {stufennamen[stufe]}")
            print(f"  \"{belege[0]}\"")
