import csv
import os
from pathlib import Path
from impresso_pipelines.ocrqa import OCRQAPipeline

TXT_DIR = Path("/home/nghm/Dokumente/Zeitungsanalyse/daten_txt/wetransfer_pdf-stadtwachter_2026-03-03_2338/txt Stadtwächter")
OUTPUT_CSV = Path("/home/nghm/Dokumente/Zeitungsanalyse/ergebnisse/ocrqa_ergebnisse.csv")

pipeline = OCRQAPipeline()

txt_files = sorted(TXT_DIR.glob("*.txt"))
print(f"{len(txt_files)} Dateien gefunden.\n")

ergebnisse = []
for txt_file in txt_files:
    text = txt_file.read_text(encoding="utf-8", errors="replace")
    result = pipeline(text, language="de")
    score = result.get("score", 0.0)
    ergebnisse.append({"Dateiname": txt_file.name, "OCR_Qualitaet": score})
    print(f"{txt_file.name}: {score:.4f}")

OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["Dateiname", "OCR_Qualitaet"])
    writer.writeheader()
    writer.writerows(ergebnisse)

durchschnitt = sum(e["OCR_Qualitaet"] for e in ergebnisse) / len(ergebnisse)
print(f"\nErgebnisse gespeichert: {OUTPUT_CSV}")
print(f"Durchschnittliche OCR-Qualität: {durchschnitt:.4f}")
