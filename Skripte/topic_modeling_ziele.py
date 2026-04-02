"""
topic_modeling_ziele.py
LDA Topic Modelling: Verborgene Themen und Ziele des Stadtwächters Osnabrück.

RAM-Strategie:
- Dateien einzeln einlesen, Text bereinigen, als Strings in Liste sammeln
  (jede Datei = 1 "Dokument" für LDA)
- CountVectorizer mit max_features-Limit
- LDA mit scikit-learn
"""

import re
import gc
import os
import csv
import glob

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ─── Konfiguration ────────────────────────────────────────────────────────────
DATA_DIR = ("/home/nghm/Dokumente/Zeitungsanalyse/daten_txt/"
            "wetransfer_pdf-stadtwachter_2026-03-03_2338/pdf Stadtwächter/")
OUT_DIR  = "/home/nghm/Dokumente/Zeitungsanalyse/ergebnisse/"
CSV_OUT  = os.path.join(OUT_DIR, "themen_topic_modelling.csv")
PLOT_OUT = os.path.join(OUT_DIR, "topic_modelling_plot.png")

N_TOPICS   = 5
TOP_WORDS  = 15
MAX_FEATS  = 3000   # Vokabular-Limit für RAM-Schonung
N_ITER     = 30

# ─── Stoppwörter ──────────────────────────────────────────────────────────────
BASIS_STOP = {
    "der","die","das","den","dem","des","ein","eine","einen","einem","einer","eines",
    "und","oder","aber","doch","nicht","auch","noch","als","wie","wenn","weil",
    "dass","ob","an","auf","aus","bei","in","mit","nach","seit","von","vor",
    "zu","zum","zur","im","ins","am","ist","sind","war","waren","hat","haben",
    "hatte","hatten","wird","werden","wurde","wurden","kann","können","konnte",
    "sich","ihr","ihre","ihren","ihrem","ihrer","ihres","er","sie","es","wir",
    "ich","du","man","sein","seine","seinen","seinem","seiner","seines",
    "uns","euch","ihm","ihn","ihnen","mir","mich","durch","für","über","unter",
    "gegen","ohne","um","so","mehr","nur","schon","nun","denn","ja","nein",
    "sehr","immer","dann","da","wo","hier","dort","dieser","diese","dieses",
    "diesem","diesen","jener","jene","jenes","alle","alles","jedoch","sondern",
    "obwohl","damit","worden","geworden","dabei","davon","daher","darum","dazu",
    "beim","vom","zur","also","noch","doch","gar","wohl","bereits","wieder",
    "ganz","recht","mal","nun","bitte","bzw","usw","etc","ggf",
    # Zeitungsspezifische Füllwörter
    "seite","ausgabe","herr","wurde","dass","werden","worden","haben","hatte",
    "habe","sein","seine","seiner","seiner","wäre","hätte","sollte","könnte",
    "müsste","beim","worden","bzw","daß","gibt","gibt","gibt","wurde","worden",
    "page","ocr","stadtw","wächter","stadtwächter","stadt","osnabrück",
    "januar","februar","märz","april","mai","juni","juli","august","september",
    "oktober","november","dezember","mark","pfennig",
}

# ─── Bereinigung ──────────────────────────────────────────────────────────────
SATZZEICHEN = re.compile(r"[^a-zA-ZäöüÄÖÜß\s]")

def bereinige_dokument(text: str) -> str:
    text = SATZZEICHEN.sub(" ", text)
    woerter = [
        w.lower() for w in text.split()
        if len(w) >= 4 and w.lower() not in BASIS_STOP
    ]
    return " ".join(woerter)

# ─── Dateien einlesen (einzeln, RAM-schonend) ─────────────────────────────────
alle_dateien = sorted(glob.glob(os.path.join(DATA_DIR, "*.txt")))
print(f"Dateien gefunden: {len(alle_dateien)}\n")

dokumente   = []   # Liste bereinigter Dokument-Strings
dateinamen  = []   # Zuordnung für spätere Analyse

for i, filepath in enumerate(alle_dateien, 1):
    dateiname = os.path.basename(filepath)
    print(f"[{i:3d}/{len(alle_dateien)}] {dateiname}")
    try:
        with open(filepath, encoding="utf-8") as fh:
            text = fh.read()
    except Exception as e:
        print(f"     FEHLER: {e}")
        gc.collect()
        continue

    bereinigt = bereinige_dokument(text)
    if len(bereinigt.split()) >= 30:   # Leere/winzige Dokumente überspringen
        dokumente.append(bereinigt)
        dateinamen.append(dateiname)

    del text, bereinigt
    gc.collect()

print(f"\n{len(dokumente)} Dokumente geladen.\n")

# ─── CountVectorizer ──────────────────────────────────────────────────────────
print("Vektorisiere …")
vectorizer = CountVectorizer(
    max_features=MAX_FEATS,
    min_df=3,        # Wort muss in mind. 3 Dokumenten vorkommen
    max_df=0.90,     # Nicht in >90% aller Dokumente (zu generisch)
    ngram_range=(1, 1),
)
dtm = vectorizer.fit_transform(dokumente)
print(f"DTM-Shape: {dtm.shape}  (Dokumente × Terme)")

del dokumente   # RAM freigeben
gc.collect()

# ─── LDA ──────────────────────────────────────────────────────────────────────
print(f"\nBerechne LDA ({N_TOPICS} Themen, {N_ITER} Iterationen) …")
lda = LatentDirichletAllocation(
    n_components=N_TOPICS,
    max_iter=N_ITER,
    learning_method="batch",
    random_state=42,
    n_jobs=1,       # Kein Parallelism → stabiler RAM
)
lda.fit(dtm)
print("LDA fertig.")

feature_names = np.array(vectorizer.get_feature_names_out())

# ─── Top-Wörter extrahieren ───────────────────────────────────────────────────
themen: list[list[str]] = []
for topic_idx, topic_vec in enumerate(lda.components_):
    top_idx   = topic_vec.argsort()[::-1][:TOP_WORDS]
    top_words = list(feature_names[top_idx])
    themen.append(top_words)

# ─── Terminal-Ausgabe ─────────────────────────────────────────────────────────
print("\n" + "="*65)
print(f"TOP {TOP_WORDS} WÖRTER PRO THEMA")
print("="*65)
for t, woerter in enumerate(themen, 1):
    print(f"\nThema {t}: {' | '.join(woerter[:8])}")
    print(f"         {' | '.join(woerter[8:])}")

# ─── CSV speichern ────────────────────────────────────────────────────────────
os.makedirs(OUT_DIR, exist_ok=True)
with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([f"Thema_{t}" for t in range(1, N_TOPICS + 1)])
    for rang in range(TOP_WORDS):
        writer.writerow([themen[t][rang] for t in range(N_TOPICS)])
print(f"\nCSV gespeichert: {CSV_OUT}")

# ─── Visualisierung: Horizontale Balkencharts ─────────────────────────────────
FARBEN = ["#1565C0","#EF5350","#2E7D32","#F57F17","#6A1B9A"]

fig, axes = plt.subplots(1, N_TOPICS, figsize=(18, 7))
fig.subplots_adjust(wspace=0.5)

for t, (ax, woerter) in enumerate(zip(axes, themen)):
    # Gewichtungen für Balken (Rang-invertiert: Platz 1 = höchster Wert)
    scores = list(range(TOP_WORDS, 0, -1))
    colors = [FARBEN[t]] * TOP_WORDS

    ax.barh(woerter[::-1], scores[::-1], color=FARBEN[t], alpha=0.82)
    ax.set_title(f"Thema {t+1}", fontsize=12, fontweight="bold",
                 color=FARBEN[t], pad=8)
    ax.set_xlabel("Rang-Gewicht", fontsize=8)
    ax.tick_params(axis="y", labelsize=8.5)
    ax.spines[["top","right","bottom"]].set_visible(False)
    ax.set_xticks([])

fig.suptitle("LDA Topic Modelling – Stadtwächter Osnabrück\n"
             f"5 latente Themen | Top-{TOP_WORDS} Wörter je Thema",
             fontsize=13, y=1.02)
plt.savefig(PLOT_OUT, dpi=150, bbox_inches="tight")
plt.close()
print(f"Diagramm gespeichert: {PLOT_OUT}")
