import csv
import os
import site
from collections import Counter
from pathlib import Path

# Die Pipeline erwartet als CWD das site-packages-Verzeichnis
os.chdir(site.getusersitepackages())

from impresso_pipelines.mallet.mallet_pipeline import MalletPipeline

TXT_DIR = Path("/home/nghm/Dokumente/Zeitungsanalyse/daten_txt/wetransfer_pdf-stadtwachter_2026-03-03_2338/txt Stadtwächter")
OUTPUT_CSV = Path("/home/nghm/Dokumente/Zeitungsanalyse/ergebnisse/topic_modeling_ergebnisse.csv")

pipeline = MalletPipeline()

txt_files = sorted(TXT_DIR.glob("*.txt"))
print(f"{len(txt_files)} Dateien gefunden.\n")

ergebnisse = []
topic_counter = Counter()

for txt_file in txt_files:
    text = txt_file.read_text(encoding="utf-8", errors="replace")
    result = pipeline(text, language="de")

    # result ist eine Liste von Dicts mit "topics"-Feld
    if result and isinstance(result, list) and "topics" in result[0]:
        topics = result[0]["topics"]
    else:
        topics = result if isinstance(result, list) else []

    # Dominant-Topic = höchste Wahrscheinlichkeit
    if topics:
        dominant = max(topics, key=lambda x: x["p"])
        dominant_topic = dominant["t"]
        dominant_prob = dominant["p"]
    else:
        dominant_topic = "unbekannt"
        dominant_prob = 0.0

    topic_counter[dominant_topic] += 1

    # Alle Topics mit min. 2% Wahrscheinlichkeit speichern
    for topic in topics:
        ergebnisse.append({
            "Dateiname": txt_file.name,
            "Topic_ID": topic["t"],
            "Wahrscheinlichkeit": topic["p"],
        })

    print(f"{txt_file.name}: Dominant-Topic={dominant_topic} ({dominant_prob:.3f})")

OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["Dateiname", "Topic_ID", "Wahrscheinlichkeit"])
    writer.writeheader()
    writer.writerows(ergebnisse)

print(f"\nErgebnisse gespeichert: {OUTPUT_CSV}")
print(f"\nHäufigste Topics (Dominant-Topic pro Datei):")
for topic, count in topic_counter.most_common(10):
    print(f"  {topic}: {count} Dateien")
