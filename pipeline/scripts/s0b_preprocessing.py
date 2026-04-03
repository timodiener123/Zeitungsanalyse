"""
s0b_preprocessing.py – Tokenisierung und Lemmatisierung des Stadtwächter-Korpus

Liest alle .txt-Dateien aus CORPUS_DIR, tokenisiert und lemmatisiert
mit spaCy, entfernt Stoppwörter und kurze Tokens, speichert das
Ergebnis als corpus_lemmatized.parquet in PROCESSED_DIR.

Ausgabespalten im Parquet:
    doc_id       – Dateiname ohne Endung
    year         – Jahrgang (int oder None)
    tokens       – lemmatisierte Tokens als kommagetrennte Zeichenkette
    n_tokens     – Anzahl Tokens nach Filterung
    n_raw_tokens – Anzahl Tokens vor Filterung
"""

import sys
import logging
from pathlib import Path

# config aus dem pipeline-Elternordner importieren
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

import pandas as pd
import spacy
from tqdm import tqdm

# =============================================================================
# Logging
# =============================================================================
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("s0b_preprocessing")

# =============================================================================
# spaCy-Modell laden (mit Fallback)
# =============================================================================
def load_spacy_model():
    for model in config.SPACY_MODEL_FALLBACK:
        try:
            nlp = spacy.load(model, disable=["parser", "ner"])
            log.info("spaCy-Modell geladen: %s", model)
            return nlp
        except OSError:
            log.warning("Modell nicht gefunden: %s", model)
    raise RuntimeError("Kein spaCy-Modell verfügbar. Bitte installieren.")

# =============================================================================
# Hauptverarbeitung
# =============================================================================
def process_document(text: str, nlp) -> tuple:
    """
    Tokenisiert und lemmatisiert einen Text mit spaCy.
    Gibt (gefilterte_lemmas, n_tokens_roh) zurück.
    """
    doc = nlp(text)
    raw_count = len(doc)
    lemmas = [
        token.lemma_.lower()
        for token in doc
        if not token.is_stop
        and not token.is_punct
        and not token.is_space
        and token.is_alpha
        and len(token.lemma_) >= 4
    ]
    return lemmas, raw_count


def main():
    log.info("=== s0b_preprocessing gestartet ===")

    # Texte einlesen
    txt_files = sorted(config.CORPUS_DIR.glob("*.txt"))
    if not txt_files:
        log.error("Keine .txt-Dateien in %s gefunden.", config.CORPUS_DIR)
        sys.exit(1)
    log.info("%d Dateien gefunden.", len(txt_files))

    # spaCy laden
    nlp = load_spacy_model()

    # Dokumente verarbeiten
    records = []
    for txt_file in tqdm(txt_files, desc="Vorverarbeitung", unit="Datei"):
        year = config.extract_year(txt_file.name)
        text = txt_file.read_text(encoding="utf-8", errors="replace")

        lemmas, n_raw = process_document(text, nlp)

        records.append({
            "doc_id":       txt_file.stem,
            "year":         year,
            "tokens":       ",".join(lemmas),
            "n_tokens":     len(lemmas),
            "n_raw_tokens": n_raw,
        })

    # DataFrame erstellen und speichern
    df = pd.DataFrame(records)
    out_path = config.PROCESSED_DIR / "corpus_lemmatized.parquet"
    df.to_parquet(out_path, index=False)
    log.info("Gespeichert: %s", out_path)

    # ==========================================================================
    # Zusammenfassung
    # ==========================================================================
    print("\n" + "=" * 55)
    print("ZUSAMMENFASSUNG")
    print("=" * 55)
    print(f"  Verarbeitete Dokumente : {len(df)}")
    print(f"  Tokens gesamt (gefilt.): {df['n_tokens'].sum():,}")
    print(f"  Tokens gesamt (roh)    : {df['n_raw_tokens'].sum():,}")
    print()
    print(f"  {'Jahrgang':<12} {'Dokumente':>10} {'Tokens (gefilt.)':>18} {'Ø Tokens/Dok':>14}")
    print(f"  {'-'*12} {'-'*10} {'-'*18} {'-'*14}")

    for year in config.TIME_SLICES:
        sub = df[df["year"] == year]
        if sub.empty:
            continue
        tok_sum = sub["n_tokens"].sum()
        tok_avg = int(tok_sum / len(sub))
        print(f"  {year:<12} {len(sub):>10} {tok_sum:>18,} {tok_avg:>14,}")

    unknown = df[df["year"].isna()]
    if not unknown.empty:
        print(f"  {'unbekannt':<12} {len(unknown):>10} {unknown['n_tokens'].sum():>18,}")

    print("=" * 55)
    log.info("=== s0b_preprocessing abgeschlossen ===")


if __name__ == "__main__":
    main()
