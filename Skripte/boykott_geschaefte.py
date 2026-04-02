"""
boykott_geschaefte.py
Ziel: Historische Aufarbeitung antisemitischer Geschäftsmarkierungen im Stadtwächter Osnabrück (~1929–1931).

Sucht nach:
- "ist ein Judengeschäft" / "Judenladen" / "Judengeschäft"
- "jüdische(r/s) Firma / Geschäft / Warenhaus / Kaufhaus / Laden"
- "Juden-Firmen" (Listenkopf + folgende Zeilen)
- "Boykottaufruf" im Zusammenhang mit Firmennamen
- Auch: explizite Firmen-Auflistungen in Boykott-Verzeichnissen

RAM-Strategie: Dateien einzeln öffnen, sofort schließen, gc.collect() nach jeder Datei.
spaCy-Modell wird nur EIN MAL geladen.
"""

import re
import gc
import csv
import os
import glob

import spacy

# ─── Konfiguration ───────────────────────────────────────────────────────────
DATA_DIR = "/home/nghm/Dokumente/Zeitungsanalyse/daten_txt/wetransfer_pdf-stadtwachter_2026-03-03_2338/pdf Stadtwächter/"
OUT_DIR  = "/home/nghm/Dokumente/Zeitungsanalyse/ergebnisse/"
OUT_FILE = os.path.join(OUT_DIR, "judengeschaefte_kontext.csv")

CONTEXT_WORDS = 15  # Wörter vor und nach dem Treffer

# Regex-Muster (case-insensitive)
PATTERNS = [
    # Explizite Bullet-Markierungen: "● Firmenname … ist ein Judengeschäft"
    (re.compile(r"ist\s+ein\s+Judengeschäft", re.IGNORECASE), "Judengeschäft-Marking"),
    # Judenladen / Judengeschäft als Einzelwort
    (re.compile(r"\bJudenladen\b", re.IGNORECASE), "Judenladen"),
    (re.compile(r"\bJudengeschäft\b", re.IGNORECASE), "Judengeschäft"),
    # jüdische(r/s/n) + Geschäftsbegriff
    (re.compile(r"jüdisch\w*\s+(?:Firma|Geschäft|Warenhaus|Kaufhaus|Laden|Betrieb|Handlung)\b", re.IGNORECASE), "jüdisch+Geschäftsbegriff"),
    # Juden-Firmen (Listenköpfe)
    (re.compile(r"Juden-Firmen?(?:\s+Verzeichnis)?(?:\s*\(Boykottaufruf\))?", re.IGNORECASE), "Juden-Firmen-Liste"),
    # Kauft nie / Kauft nicht beim Juden
    (re.compile(r"Kauft?\s+(?:nie|nicht)\s+(?:beim|von|bei)\s+Jude", re.IGNORECASE), "Boykottparole"),
    # "anprangern" + jüdisch
    (re.compile(r"jüdische\s+Firma\s+anprangern|anprangern.*jüdisch", re.IGNORECASE), "Anprangerung"),
]

# ─── spaCy einmalig laden ─────────────────────────────────────────────────────
print("Lade spaCy-Modell (de_core_news_sm) …")
nlp = spacy.load("de_core_news_sm", disable=["parser"])
print("Modell geladen.\n")

# ─── Hilfsfunktionen ─────────────────────────────────────────────────────────

def extract_context(text: str, match_start: int, match_end: int, n_words: int = CONTEXT_WORDS) -> str:
    """Extrahiert n_words Wörter vor und nach dem Match aus dem Volltext."""
    before = text[:match_start]
    after  = text[match_end:]
    words_before = before.split()[-n_words:]
    words_after  = after.split()[:n_words]
    snippet = " ".join(words_before) + " [TREFFER] " + text[match_start:match_end] + " [/TREFFER] " + " ".join(words_after)
    return snippet.strip()


def run_ner(snippet: str):
    """Führt spaCy-NER auf dem kurzen Kontext aus. Gibt (org_list, per_list) zurück."""
    doc = nlp(snippet[:500])   # Länge begrenzen, spart RAM
    orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
    pers = [ent.text for ent in doc.ents if ent.label_ == "PER"]
    return orgs, pers


def process_file(filepath: str, dateiname: str) -> list[dict]:
    """Liest eine Datei, sucht Treffer, gibt Ergebnisliste zurück."""
    results = []
    try:
        with open(filepath, encoding="utf-8") as fh:
            text = fh.read()
    except Exception as e:
        print(f"  FEHLER beim Lesen: {e}")
        return results

    for pattern, label in PATTERNS:
        for m in pattern.finditer(text):
            snippet   = extract_context(text, m.start(), m.end())
            orgs, pers = run_ner(snippet)

            results.append({
                "dateiname":   dateiname,
                "muster":      label,
                "treffer_text": m.group(0),
                "orgs_ner":    "; ".join(orgs) if orgs else "",
                "pers_ner":    "; ".join(pers) if pers else "",
                "kontext":     snippet,
            })

    # Text sofort freigeben
    del text
    return results


# ─── Hauptschleife ────────────────────────────────────────────────────────────
alle_dateien = sorted(glob.glob(os.path.join(DATA_DIR, "*.txt")))
print(f"Gefundene TXT-Dateien: {len(alle_dateien)}\n")

alle_ergebnisse: list[dict] = []

for i, filepath in enumerate(alle_dateien, start=1):
    dateiname = os.path.basename(filepath)
    print(f"[{i:3d}/{len(alle_dateien)}] {dateiname}")

    treffer = process_file(filepath, dateiname)
    if treffer:
        print(f"         → {len(treffer)} Treffer")
    alle_ergebnisse.extend(treffer)

    gc.collect()

print(f"\nGesamt-Treffer: {len(alle_ergebnisse)}")

# ─── Speichern ────────────────────────────────────────────────────────────────
os.makedirs(OUT_DIR, exist_ok=True)
fieldnames = ["dateiname", "muster", "treffer_text", "orgs_ner", "pers_ner", "kontext"]

with open(OUT_FILE, "w", newline="", encoding="utf-8") as csvf:
    writer = csv.DictWriter(csvf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(alle_ergebnisse)

print(f"Ergebnisse gespeichert: {OUT_FILE}")

# ─── Stichproben direkt im Terminal ausgeben ──────────────────────────────────
print("\n" + "="*70)
print("STICHPROBEN (erste 15 Treffer):")
print("="*70)
for row in alle_ergebnisse[:15]:
    print(f"\nDatei:   {row['dateiname']}")
    print(f"Muster:  {row['muster']}")
    print(f"Treffer: {row['treffer_text']}")
    if row['orgs_ner']:
        print(f"ORGs:    {row['orgs_ner']}")
    if row['pers_ner']:
        print(f"PERs:    {row['pers_ner']}")
    print(f"Kontext: {row['kontext'][:200]} …")
    print("-"*70)

# Zusammenfassung nach Muster
print("\nZUSAMMENFASSUNG NACH MUSTER:")
from collections import Counter
c = Counter(r["muster"] for r in alle_ergebnisse)
for muster, anzahl in c.most_common():
    print(f"  {muster:<35} {anzahl:>4} Treffer")

# Häufigste ORGs
print("\nHÄUFIGSTE ORG-ENTITÄTEN (NER):")
org_counter: Counter = Counter()
for r in alle_ergebnisse:
    for org in r["orgs_ner"].split("; "):
        if org.strip():
            org_counter[org.strip()] += 1
for org, cnt in org_counter.most_common(20):
    print(f"  {org:<40} {cnt:>3}x")
