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
    # Zeilenumbrüche durch Leerzeichen ersetzen, damit SpaCy keine \n-Tokens erzeugt
    # (diese würden die CSV-Zeile für MALLET umbrechen und nur Textfragmente liefern)
    text = text.replace("\n", " ").replace("\r", " ")
    result = pipeline(text, language="de")

    # result ist eine Liste von Dicts mit "topics"-Feld.
    # result[0] ist die CSV-Headerzeile (id/class/text → Defaultwerte), result[1] das echte Dokument.
    actual = None
    if result and isinstance(result, list):
        for r in result:
            if isinstance(r, dict) and r.get("ci_id") not in ("id", None, ""):
                actual = r
                break
    topics = actual.get("topics", []) if actual else []

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
