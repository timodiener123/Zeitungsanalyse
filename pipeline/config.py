"""
config.py – Zentrale Konfiguration für die Stadtwächter-Analyse-Pipeline
Korpus: Der Stadt-Wächter, Osnabrück, Jahrgänge 1929–1931
"""

from pathlib import Path
import re

# =============================================================================
# 1. BASISPFADE
# =============================================================================

BASE_DIR = Path(__file__).parent.resolve()

CORPUS_DIR = Path(
    "/home/nghm/Dokumente/Zeitungsanalyse/daten_txt"
    "/wetransfer_pdf-stadtwachter_2026-03-03_2338/txt Stadtwächter"
)

PROCESSED_DIR      = BASE_DIR / "data" / "processed"
RESULTS_DIR        = BASE_DIR / "data" / "results"
VISUALIZATIONS_DIR = BASE_DIR / "visualizations"
LOGS_DIR           = BASE_DIR / "logs"

# Verzeichnisse bei Bedarf anlegen
for _d in (PROCESSED_DIR, RESULTS_DIR, VISUALIZATIONS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# =============================================================================
# 2. ZEITSCHEIBEN
# =============================================================================

TIME_SLICES = [1929, 1930, 1931]

# Regulärer Ausdruck zum Extrahieren des Jahres aus Dateinamen
# Beispiele: "01. Ausgabe 1930.txt", "OCR 4 1929 komplett Stadtwächter.txt"
YEAR_PATTERN = re.compile(r"(192[0-9]|193[0-9])")

def extract_year(filename: str):
    """Extrahiert die Jahreszahl aus einem Dateinamen."""
    match = YEAR_PATTERN.search(filename)
    return int(match.group(1)) if match else None

# =============================================================================
# 3. SPACY-MODELL
# =============================================================================

# Vorerst sm-Modell; auf lg umstellen sobald Download stabil möglich
SPACY_MODEL = "de_core_news_sm"

# Fallback-Reihenfolge (erstes verfügbares wird verwendet)
SPACY_MODEL_FALLBACK = [
    "de_core_news_lg",
    "de_core_news_md",
    "de_core_news_sm",
]

# =============================================================================
# 4. SEED-TERME
# =============================================================================

# --- 4a. Direkte Ethnisierungen ---
SEED_ETHNISIERUNG = [
    "jude",
    "juden",
    "jüdisch",
    "jüdische",
    "jüdischen",
    "jüdischer",
    "jüdisches",
    "judentum",
    "judenschaft",
    "judenblatt",
    "judenpresse",
    "judenrepublik",
    "judenstern",
    "ostjude",
    "ostjuden",
    "halbjude",
]

# --- 4b. NS-Terminologie ---
SEED_NS_TERMINOLOGIE = [
    "nationalsozialist",
    "nationalsozialisten",
    "nationalsozialistisch",
    "nsdap",
    "hitler",
    "hitlerbewegung",
    "volksgenosse",
    "volksgenossen",
    "volksgemeinschaft",
    "völkisch",
    "rassisch",
    "rasse",
    "rassenreinheit",
    "arier",
    "arisch",
    "führerprinzip",
    "hakenkreuz",
    "sturmabteilung",
    "stahlhelm",
]

# --- 4c. Dehumanisierungen ---
SEED_DEHUMANISIERUNG = [
    "parasit",
    "parasiten",
    "schmarotzer",
    "ungeziefer",
    "schädling",
    "schädlinge",
    "pest",
    "gesindel",
    "pack",
    "blutsauger",
    "wucherer",
    "verbrecher",
    "volksverräter",
    "landesverräter",
    "vaterlandsverräter",
    "fremdkörper",
    "eindringling",
    "eindringlinge",
]

# Alle Seed-Terme zusammen (für schnellen Zugriff)
ALL_SEED_TERMS = (
    SEED_ETHNISIERUNG
    + SEED_NS_TERMINOLOGIE
    + SEED_DEHUMANISIERUNG
)

# Mapping: Term → Kategorie
SEED_CATEGORIES = {
    **{t: "Ethnisierung"    for t in SEED_ETHNISIERUNG},
    **{t: "NS-Terminologie" for t in SEED_NS_TERMINOLOGIE},
    **{t: "Dehumanisierung" for t in SEED_DEHUMANISIERUNG},
}

# =============================================================================
# 5. ANALYSE-PARAMETER
# =============================================================================

# Frequenzanalyse
MIN_WORD_LENGTH = 3        # Mindestwortlänge für Tokenisierung
MIN_WORD_FREQ   = 5        # Mindestzahl Vorkommen für Vokabular
TOP_N_WORDS     = 50       # Anzahl Top-Wörter in Ausgaben

# TF-IDF / NMF
TFIDF_MAX_FEATURES = 5000
TFIDF_MAX_DF       = 0.90  # Wörter in >90% der Dokumente ignorieren
TFIDF_MIN_DF       = 3     # Wörter in <3 Dokumenten ignorieren
NMF_N_TOPICS       = 7
NMF_RANDOM_STATE   = 42

# N-Gramme
NGRAM_SIZES  = [2, 3]      # Bi- und Trigramme
TOP_N_NGRAMS = 30

# Kollokationen
COLLOCATIONS_WINDOW = 5    # Fenstergröße links/rechts
TOP_N_COLLOCATIONS  = 20

# KWIC
KWIC_WINDOW = 10           # Kontextwörter links/rechts

# SentiWS
SENTIWS_DIR = Path("/home/nghm/Dokumente/Zeitungsanalyse/sentiws")
SENTIWS_NEG = SENTIWS_DIR / "SentiWS_v2.0_Negative.txt"
SENTIWS_POS = SENTIWS_DIR / "SentiWS_v2.0_Positive.txt"

# =============================================================================
# 6. LOGGING
# =============================================================================

LOG_LEVEL  = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_FILE   = LOGS_DIR / "pipeline.log"
