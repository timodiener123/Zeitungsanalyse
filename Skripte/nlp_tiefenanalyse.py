"""
nlp_tiefenanalyse.py
Automatisierte inhaltliche Tiefenanalyse der Argumentationsmuster
im direkten Umfeld antisemitischer Begriffe, 1929–1931.

Methode:
- Kontextfenster ±20 Wörter um jüdisch*-Anker
- Bereinigung: Stoppwörter, Satzzeichen, Kurzwörter entfernen
- TF-IDF mit ngram_range=(2,3) pro Jahr → jahresspezifische Phrasen
- Top-20-Phrasen pro Jahr als CSV
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

from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

# ─── Konfiguration ────────────────────────────────────────────────────────────
DATA_DIR = ("/home/nghm/Dokumente/Zeitungsanalyse/daten_txt/"
            "wetransfer_pdf-stadtwachter_2026-03-03_2338/pdf Stadtwächter/")
OUT_DIR  = "/home/nghm/Dokumente/Zeitungsanalyse/ergebnisse/"
CSV_OUT  = os.path.join(OUT_DIR, "argumentationsmuster_jahre.csv")
PLOT_OUT = os.path.join(OUT_DIR, "argumentationsmuster_plot.png")

WINDOW   = 20
TOP_N    = 20

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

# ─── Stoppwörter (deutsch, erweitert) ────────────────────────────────────────
STOPWOERTER = {
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "einem",
    "einer", "eines", "und", "oder", "aber", "doch", "nicht", "auch", "noch",
    "als", "wie", "wenn", "weil", "dass", "ob", "an", "auf", "aus", "bei",
    "in", "mit", "nach", "seit", "von", "vor", "zu", "zum", "zur", "im",
    "ins", "am", "ist", "sind", "war", "waren", "hat", "haben", "hatte",
    "hatten", "wird", "werden", "wurde", "wurden", "kann", "können", "konnte",
    "konnten", "wird", "soll", "sollte", "muss", "müssen", "musste",
    "sich", "ihr", "ihre", "ihren", "ihrem", "ihrer", "ihres",
    "er", "sie", "es", "wir", "ihr", "ich", "du", "man",
    "sein", "seine", "seinen", "seinem", "seiner", "seines",
    "uns", "euch", "ihm", "ihn", "ihnen", "mir", "mich",
    "durch", "für", "über", "unter", "gegen", "ohne", "um",
    "so", "mehr", "nur", "schon", "nun", "denn", "ja", "nein",
    "sehr", "immer", "dann", "da", "wo", "hier", "dort",
    "dieser", "diese", "dieses", "diesem", "diesen",
    "jener", "jene", "jenes", "jenem", "jenen",
    "alle", "alles", "allem", "allen", "aller",
    "werden", "worden", "geworden", "worden",
    "dabei", "davon", "daher", "darum", "dazu",
    "jedoch", "sondern", "obwohl", "damit",
    "ihre", "unsere", "euer", "deren",
    "no", "the", "of", "and", "a", "to", "in", "is",   # OCR-Englischreste
}

SATZZEICHEN = re.compile(r"[.,;:!?\"'()\[\]–—»«\-/\\|°§@#%&*+<>=~`^{}]")
ZAHL        = re.compile(r"\b\d+\b")

def bereinige(text: str) -> str:
    """Entfernt Satzzeichen, Zahlen, Stoppwörter und Kurzwörter (<3 Zeichen)."""
    text = SATZZEICHEN.sub(" ", text)
    text = ZAHL.sub(" ", text)
    woerter = [
        w.lower() for w in text.split()
        if len(w) >= 3 and w.lower() not in STOPWOERTER
    ]
    return " ".join(woerter)

# ─── Kontexte sammeln (RAM-schonend: Datei für Datei) ────────────────────────
# jahr → Liste von bereinigten Kontextfenstern (je ein "Dokument" für TF-IDF)
kontexte: dict[int, list[str]] = {1929: [], 1930: [], 1931: []}

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
        bereinigt_wort = wort.strip(".,;:!?\"'()[]–—»«")
        if not ANKER.fullmatch(bereinigt_wort):
            continue

        start = max(0, idx - WINDOW)
        end   = min(n, idx + WINDOW + 1)
        fenster_raw = " ".join(woerter[start:end])
        fenster_clean = bereinige(fenster_raw)

        if fenster_clean.strip():
            kontexte[jahr].append(fenster_clean)

    del text, woerter
    gc.collect()

for jahr in (1929, 1930, 1931):
    print(f"\n{jahr}: {len(kontexte[jahr])} Kontextfenster gesammelt")

# ─── TF-IDF pro Jahr ─────────────────────────────────────────────────────────
# Strategie: Jedes Jahr wird als eigenes Korpus behandelt.
# Um jahres-SPEZIFISCHE Phrasen zu finden (nicht nur häufige),
# trainieren wir den Vectorizer auf allen drei Jahren gemeinsam,
# holen aber die TF-IDF-Scores jahresweise als gemittelte Zeilen.

print("\nBerechne TF-IDF …")

# Alle Kontexte zusammen für den gemeinsamen Vokabular-Aufbau
alle_kontexte = kontexte[1929] + kontexte[1930] + kontexte[1931]

vectorizer = TfidfVectorizer(
    ngram_range=(2, 3),
    min_df=3,            # Phrase muss in mind. 3 Fenstern auftauchen
    max_df=0.85,         # Nicht in >85% aller Fenster (zu generisch)
    sublinear_tf=True,   # log-Dämpfung
)
tfidf_matrix = vectorizer.fit_transform(alle_kontexte)
feature_names = np.array(vectorizer.get_feature_names_out())

# Jahresgrenzen
n29 = len(kontexte[1929])
n30 = len(kontexte[1930])
n31 = len(kontexte[1931])

# Mittlere TF-IDF pro Jahr
mean_1929 = np.asarray(tfidf_matrix[:n29].mean(axis=0)).flatten()
mean_1930 = np.asarray(tfidf_matrix[n29:n29+n30].mean(axis=0)).flatten()
mean_1931 = np.asarray(tfidf_matrix[n29+n30:].mean(axis=0)).flatten()

def top_phrasen(mean_vec, n=TOP_N):
    idx = np.argsort(mean_vec)[::-1][:n]
    return [(feature_names[i], round(float(mean_vec[i]), 5)) for i in idx]

top29 = top_phrasen(mean_1929)
top30 = top_phrasen(mean_1930)
top31 = top_phrasen(mean_1931)

# ─── Ausgabe Terminal ─────────────────────────────────────────────────────────
for jahr, top in [(1929, top29), (1930, top30), (1931, top31)]:
    print(f"\n{'='*55}")
    print(f"TOP-{TOP_N} PHRASEN {jahr}")
    print(f"{'='*55}")
    for rang, (phrase, score) in enumerate(top, 1):
        print(f"  {rang:2d}. {phrase:<40}  {score:.5f}")

# ─── CSV speichern ────────────────────────────────────────────────────────────
os.makedirs(OUT_DIR, exist_ok=True)
with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Rang", "Phrase_1929", "Score_1929",
                              "Phrase_1930", "Score_1930",
                              "Phrase_1931", "Score_1931"])
    for rang in range(TOP_N):
        writer.writerow([
            rang + 1,
            top29[rang][0], top29[rang][1],
            top30[rang][0], top30[rang][1],
            top31[rang][0], top31[rang][1],
        ])
print(f"\nCSV gespeichert: {CSV_OUT}")

# ─── Balkendiagramm ───────────────────────────────────────────────────────────
fig = plt.figure(figsize=(18, 7))
gs  = gridspec.GridSpec(1, 3, figure=fig, wspace=0.55)

farben = {1929: "#5C6BC0", 1930: "#EF5350", 1931: "#26A69A"}
TOP_VIS = 12   # Nur Top-12 im Diagramm (lesbar)

for col, (jahr, top) in enumerate([(1929, top29), (1930, top30), (1931, top31)]):
    ax = fig.add_subplot(gs[col])
    phrasen = [t[0] for t in top[:TOP_VIS]]
    scores  = [t[1] for t in top[:TOP_VIS]]
    bars = ax.barh(phrasen[::-1], scores[::-1],
                   color=farben[jahr], edgecolor="white", alpha=0.88)
    ax.set_title(str(jahr), fontsize=13, fontweight="bold", pad=8)
    ax.set_xlabel("Ø TF-IDF-Score", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="y", labelsize=8)

fig.suptitle("Argumentationsmuster im Kontext antisemitischer Begriffe\n"
             "Top-12 Bi-/Trigramme pro Jahr – Stadtwächter Osnabrück 1929–1931",
             fontsize=12, y=1.02)
plt.savefig(PLOT_OUT, dpi=150, bbox_inches="tight")
plt.close()
print(f"Diagramm gespeichert: {PLOT_OUT}")
