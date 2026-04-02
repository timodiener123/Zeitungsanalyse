import csv
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF

TXT_DIR = Path("/home/nghm/Dokumente/Zeitungsanalyse/daten_txt/wetransfer_pdf-stadtwachter_2026-03-03_2338/txt Stadtwächter")
OUTPUT_KEYWORDS_CSV = Path("/home/nghm/Dokumente/Zeitungsanalyse/ergebnisse/nmf_topic_keywords.csv")
OUTPUT_DOCS_CSV = Path("/home/nghm/Dokumente/Zeitungsanalyse/ergebnisse/nmf_topic_zuordnung.csv")

N_TOPICS = 7
N_KEYWORDS = 15

STOPPWOERTER = [
    "aber", "alle", "allem", "allen", "aller", "alles", "als", "also", "am", "an",
    "ander", "andere", "anderen", "anderm", "andern", "anderr", "anders", "auch",
    "auf", "aus", "bei", "bin", "bis", "bist", "da", "damit", "dann", "das",
    "dass", "daß", "dem", "den", "der", "des", "dessen", "dich", "die", "dies",
    "diese", "diesem", "diesen", "dieser", "dieses", "dir", "doch", "dort", "du",
    "durch", "ein", "eine", "einem", "einen", "einer", "eines", "einige", "einigem",
    "einigen", "einiger", "einiges", "einmal", "er", "es", "etwas", "euer", "eure",
    "eurem", "euren", "eurer", "eures", "für", "gegen", "gewesen", "hab", "habe",
    "haben", "hat", "hatte", "hatten", "hier", "hin", "hinter", "ich", "ihm", "ihn",
    "ihnen", "ihr", "ihre", "ihrem", "ihren", "ihrer", "ihres", "im", "in", "indem",
    "ins", "ist", "jede", "jedem", "jeden", "jeder", "jedes", "jetzt", "kann",
    "kein", "keine", "keinem", "keinen", "keiner", "keines", "können", "könnte",
    "machen", "man", "manche", "manchem", "manchen", "mancher", "manches", "mein",
    "meine", "meinem", "meinen", "meiner", "meines", "mich", "mir", "mit", "muss",
    "musste", "nach", "nicht", "nichts", "noch", "nun", "nur", "ob", "oder", "ohne",
    "sehr", "sein", "seine", "seinem", "seinen", "seiner", "seines", "selbst",
    "sich", "sie", "sind", "so", "solche", "solchem", "solchen", "solcher",
    "solches", "soll", "sollte", "sondern", "sonst", "über", "um", "und", "uns",
    "unse", "unser", "unsere", "unserem", "unseren", "unserer", "unseres", "unter",
    "viel", "vom", "von", "vor", "war", "waren", "warst", "was", "weg", "weil",
    "weiter", "welche", "welchem", "welchen", "welcher", "welches", "wenn", "wer",
    "werden", "wie", "wieder", "will", "wir", "wird", "wo", "wollen", "wollte",
    "würde", "würden", "zu", "zum", "zur", "zwar", "zwischen", "seite", "herr",
    "mehr", "schon", "beim", "hat", "hatte", "sein", "worden", "wurde", "wurden",
    "gibt", "immer", "dann", "denn", "mal", "wohl", "ja", "eben", "doch", "ganz",
    "bereits", "wäre", "diesem", "diesen", "dieser", "worden", "sowie", "bzw",
    "dr", "nr", "st", "usw", "bzw", "ca", "vgl",
]

# --- 1. Texte einlesen ---
txt_files = sorted(TXT_DIR.glob("*.txt"))
print(f"{len(txt_files)} Dateien gefunden.")

dateinamen = []
texte = []
for f in txt_files:
    texte.append(f.read_text(encoding="utf-8", errors="replace"))
    dateinamen.append(f.name)

# --- 2. TF-IDF Vektorisierung ---
print("TF-IDF Vektorisierung...")
vectorizer = TfidfVectorizer(
    max_df=0.90,           # Wörter die in >90% der Dokumente vorkommen ignorieren
    min_df=3,              # Wörter die in <3 Dokumenten vorkommen ignorieren
    max_features=5000,
    stop_words=STOPPWOERTER,
    token_pattern=r"[a-zA-ZäöüÄÖÜß]{4,}",  # nur Wörter mit mind. 4 Buchstaben
    lowercase=True,
)
tfidf_matrix = vectorizer.fit_transform(texte)
feature_names = vectorizer.get_feature_names_out()
print(f"Vokabular: {len(feature_names)} Begriffe, Matrix: {tfidf_matrix.shape}")

# --- 3. NMF Topic Model trainieren ---
print(f"NMF mit {N_TOPICS} Topics trainieren...")
nmf = NMF(n_components=N_TOPICS, random_state=42, max_iter=500)
doc_topic_matrix = nmf.fit_transform(tfidf_matrix)
print("Training abgeschlossen.")

# --- 4. Keywords pro Topic ausgeben und speichern ---
print(f"\n{'='*60}")
print(f"TOP-{N_KEYWORDS} SCHLÜSSELWÖRTER PRO TOPIC")
print(f"{'='*60}")

keywords_rows = []
for topic_idx, topic_vec in enumerate(nmf.components_):
    top_indices = topic_vec.argsort()[-N_KEYWORDS:][::-1]
    top_words = [(feature_names[i], round(topic_vec[i], 4)) for i in top_indices]
    print(f"\nTopic {topic_idx + 1}:")
    print("  " + ", ".join([w for w, _ in top_words]))
    for rank, (word, score) in enumerate(top_words, 1):
        keywords_rows.append({
            "Topic_Nr": topic_idx + 1,
            "Rang": rank,
            "Schluesselwort": word,
            "Gewicht": score,
        })

# --- 5. Dominante Topic-Zuordnung pro Dokument ---
dominant_topics = np.argmax(doc_topic_matrix, axis=1)
doc_rows = []
for i, dateiname in enumerate(dateinamen):
    dominant = int(dominant_topics[i])
    gewicht = round(doc_topic_matrix[i, dominant], 4)
    doc_rows.append({
        "Dateiname": dateiname,
        "Dominant_Topic": dominant + 1,
        "Gewicht": gewicht,
    })

# --- 6. CSVs speichern ---
OUTPUT_KEYWORDS_CSV.parent.mkdir(parents=True, exist_ok=True)

with open(OUTPUT_KEYWORDS_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["Topic_Nr", "Rang", "Schluesselwort", "Gewicht"])
    writer.writeheader()
    writer.writerows(keywords_rows)

with open(OUTPUT_DOCS_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["Dateiname", "Dominant_Topic", "Gewicht"])
    writer.writeheader()
    writer.writerows(doc_rows)

# --- 7. Zusammenfassung ---
from collections import Counter
topic_verteilung = Counter(r["Dominant_Topic"] for r in doc_rows)
print(f"\n{'='*60}")
print("TOPIC-VERTEILUNG ÜBER ALLE AUSGABEN:")
for t in sorted(topic_verteilung):
    print(f"  Topic {t}: {topic_verteilung[t]} Ausgaben")

print(f"\nGespeichert:")
print(f"  {OUTPUT_KEYWORDS_CSV}")
print(f"  {OUTPUT_DOCS_CSV}")
