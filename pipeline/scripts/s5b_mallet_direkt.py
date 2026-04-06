"""
s5b_mallet_direkt.py – MALLET LDA Topic Modeling des Stadtwächter-Korpus

Führt MALLET direkt auf den Rohtexten aus (ohne Lemmatisierung):
  1. Kopiert alle .txt-Dateien in einen temporären Ordner
  2. Importiert den Korpus mit mallet import-dir
  3. Trainiert LDA mit 7 Topics (1000 Iterationen)
  4. Liest Ergebnisse ein und gibt sie übersichtlich aus
  5. Vergleicht mit den NMF-Ergebnissen aus s5_topics.py

Ausgabedateien:
    ergebnisse/mallet_topics.txt       – Top-Terme pro Topic (MALLET-Format)
    ergebnisse/mallet_doc_topics.txt   – Topic-Verteilung pro Dokument
    ergebnisse/mallet_vergleich.csv    – Vergleich MALLET vs. NMF (Top-Terme)

Voraussetzung: MALLET unter /opt/mallet/bin/mallet installiert
"""

import sys
import shutil
import logging
import subprocess
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

import pandas as pd

# =============================================================================
# Konfiguration
# =============================================================================

MALLET_BIN    = Path("/opt/mallet/bin/mallet")
CORPUS_DIR    = config.CORPUS_DIR          # Ordner mit den .txt-Dateien
ERGEBNISSE    = Path(__file__).resolve().parents[2] / "ergebnisse"
MALLET_FILE   = Path("/tmp/stadtwaechter.mallet")
OUT_TOPICS    = ERGEBNISSE / "mallet_topics.txt"
OUT_DOC       = ERGEBNISSE / "mallet_doc_topics.txt"
OUT_VERGLEICH = ERGEBNISSE / "mallet_vergleich.csv"

N_TOPICS      = config.NMF_N_TOPICS   # 7 – identisch mit NMF
N_ITERATIONS  = 1000
TOP_N_WORDS   = 15                    # Terme pro Topic in der Ausgabe

# Stopwörter: MALLET-eigene Liste wird durch --remove-stopwords aktiviert.
# Zusätzliche projektspezifische Stopwörter können optional angegeben werden.
EXTRA_STOPWORDS = str(Path(__file__).resolve().parents[1] / "data" / "german_stopwords.txt")

# NMF-Ergebnis aus s5_topics.py (zum Vergleich)
NMF_KEYWORDS_CSV = config.RESULTS_DIR / "topics_keywords.csv"

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
log = logging.getLogger("s5b_mallet_direkt")


# =============================================================================
# Hilfsfunktionen
# =============================================================================

def check_mallet() -> None:
    """Prüft, ob MALLET vorhanden und ausführbar ist."""
    if not MALLET_BIN.exists():
        log.error("MALLET nicht gefunden: %s", MALLET_BIN)
        log.error("Installation: https://mimno.github.io/Mallet/")
        sys.exit(1)
    log.info("MALLET gefunden: %s", MALLET_BIN)


def copy_txts_to_tmpdir(tmp_dir: Path) -> int:
    """
    Kopiert alle .txt-Dateien aus CORPUS_DIR (rekursiv) in tmp_dir.
    Benennt Dateien so um, dass Leerzeichen durch Unterstriche ersetzt werden,
    da MALLET manchmal mit Leerzeichen in Pfaden Probleme hat.
    Gibt die Anzahl kopierter Dateien zurück.
    """
    # .venv und andere Nicht-Korpus-Verzeichnisse ausschließen
    txt_files = [
        p for p in CORPUS_DIR.rglob("*.txt")
        if ".venv" not in p.parts and "__pycache__" not in p.parts
    ]
    if not txt_files:
        log.error("Keine .txt-Dateien in %s gefunden.", CORPUS_DIR)
        sys.exit(1)

    for src in txt_files:
        # Sicherer Dateiname: Leerzeichen → Unterstrich
        safe_name = src.name.replace(" ", "_")
        dst = tmp_dir / safe_name
        # Bei Namenskollisionen Elternordner voranstellen
        if dst.exists():
            safe_name = src.parent.name + "_" + safe_name
            dst = tmp_dir / safe_name
        shutil.copy2(src, dst)

    log.info("%d .txt-Dateien nach %s kopiert.", len(txt_files), tmp_dir)
    return len(txt_files)


def run(cmd: list, desc: str) -> None:
    """Führt einen Subprocess aus und prüft den Rückgabecode."""
    log.info("Starte: %s", desc)
    log.debug("Befehl: %s", " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        log.debug(result.stdout[:2000])
    if result.returncode != 0:
        log.error("Fehler bei: %s", desc)
        log.error(result.stderr[-2000:])
        sys.exit(1)
    log.info("Abgeschlossen: %s", desc)


def mallet_import(txt_dir: Path) -> None:
    """Schritt 2: MALLET import-dir"""
    cmd = [
        str(MALLET_BIN), "import-dir",
        "--input",           str(txt_dir),
        "--output",          str(MALLET_FILE),
        "--keep-sequence",
        "--remove-stopwords",
    ]
    if EXTRA_STOPWORDS and Path(EXTRA_STOPWORDS).exists():
        cmd += ["--extra-stopwords", EXTRA_STOPWORDS]
        log.info("Extra-Stopwörter: %s", EXTRA_STOPWORDS)

    run(cmd, "mallet import-dir")


def mallet_train() -> None:
    """Schritt 3: MALLET train-topics"""
    ERGEBNISSE.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(MALLET_BIN), "train-topics",
        "--input",              str(MALLET_FILE),
        "--num-topics",         str(N_TOPICS),
        "--output-topic-keys",  str(OUT_TOPICS),
        "--output-doc-topics",  str(OUT_DOC),
        "--num-iterations",     str(N_ITERATIONS),
    ]
    run(cmd, f"mallet train-topics ({N_TOPICS} Topics, {N_ITERATIONS} Iterationen)")


# =============================================================================
# Ergebnisse einlesen
# =============================================================================

def parse_topic_keys(path: Path) -> pd.DataFrame:
    """
    Liest mallet_topics.txt (--output-topic-keys).
    Format: <topic_id>\t<dirichlet_weight>\t<term1> <term2> ...
    """
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t", 2)
            if len(parts) < 3:
                continue
            topic_id = int(parts[0])
            weight   = float(parts[1].replace(",", "."))
            terms    = parts[2].split()
            rows.append({
                "topic":  topic_id,
                "weight": weight,
                "terms":  terms,
            })
    return pd.DataFrame(rows).sort_values("topic").reset_index(drop=True)


def parse_doc_topics(path: Path) -> pd.DataFrame:
    """
    Liest mallet_doc_topics.txt (--output-doc-topics).
    Format: #doc\tsource\ttopic proportion topic proportion ...
    Erste Zeile ist ein Kommentar (#doc ...).
    """
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            doc_id  = parts[0]
            source  = Path(parts[1]).name
            # MALLET --output-doc-topics: Spalten 2..N+1 sind direkt die
            # Proportionen für Topic 0, 1, 2, … (keine alternierenden IDs).
            props = {}
            for t, val in enumerate(parts[2:2 + N_TOPICS]):
                try:
                    props[f"topic_{t}"] = float(val)
                except ValueError:
                    props[f"topic_{t}"] = 0.0
            row = {"doc_id": doc_id, "source": source}
            row.update(props)
            rows.append(row)
    df = pd.DataFrame(rows)
    # Fehlende Topic-Spalten mit 0 auffüllen
    for t in range(N_TOPICS):
        col = f"topic_{t}"
        if col not in df.columns:
            df[col] = 0.0
    return df


# =============================================================================
# Ausgabe
# =============================================================================

def print_mallet_results(df_topics: pd.DataFrame, df_docs: pd.DataFrame) -> None:
    """Gibt MALLET-Ergebnisse übersichtlich aus."""
    topic_cols = [f"topic_{t}" for t in range(N_TOPICS) if f"topic_{t}" in df_docs.columns]

    print("\n" + "=" * 72)
    print(f"MALLET LDA  –  {N_TOPICS} Topics  –  {N_ITERATIONS} Iterationen")
    print("=" * 72)

    for _, row in df_topics.iterrows():
        t_idx = row["topic"]
        terms = row["terms"][:TOP_N_WORDS]
        label = " · ".join(terms[:3])

        # Mittlerer Anteil dieses Topics über alle Dokumente
        col = f"topic_{t_idx}"
        mean_share = df_docs[col].mean() * 100 if col in df_docs.columns else 0.0

        print(f"\n  Topic {t_idx}  [{label}]")
        print(f"  Terme:          {', '.join(terms)}")
        print(f"  Ø Anteil (alle Dok.): {mean_share:.1f}%")

    # Jahresvergleich anhand Dateiname (Jahreszahl im Namen)
    year_pattern = config.YEAR_PATTERN
    df_docs["year"] = df_docs["source"].apply(
        lambda s: config.extract_year(s)
    )
    df_year = df_docs.dropna(subset=["year"])

    if not df_year.empty:
        print(f"\n  {'─'*70}")
        print("  MALLET TOPIC-ANTEILE IM JAHRESVERGLEICH (%):")
        header = f"  {'Topic (Top-3)':<30}"
        for y in config.TIME_SLICES:
            header += f"  {int(y):>6}"
        print(header)
        print(f"  {'-'*30}  " + "  ".join(["-"*6] * len(config.TIME_SLICES)))

        for _, row in df_topics.iterrows():
            t_idx = row["topic"]
            col   = f"topic_{t_idx}"
            label = " · ".join(row["terms"][:3])
            row_str = f"  T{t_idx}: {label:<26}"
            for year in config.TIME_SLICES:
                sub = df_year[df_year["year"] == year]
                share = sub[col].mean() * 100 if (not sub.empty and col in sub.columns) else 0.0
                row_str += f"  {share:>5.1f}%"
            print(row_str)

    print(f"\n  Ausgabedateien:")
    print(f"    {OUT_TOPICS}")
    print(f"    {OUT_DOC}")
    print("=" * 72)


# =============================================================================
# Vergleich mit NMF
# =============================================================================

def compare_with_nmf(df_mallet: pd.DataFrame) -> None:
    """
    Vergleicht MALLET-Topics mit NMF-Topics aus s5_topics.py.
    Gibt eine Tabelle aus: pro MALLET-Topic die Top-Terme und die
    NMF-Top-Terme des ähnlichsten Topics (höchster Jaccard-Index).
    Speichert den Vergleich als CSV.
    """
    print("\n" + "=" * 72)
    print("VERGLEICH  –  MALLET LDA  vs.  NMF")
    print("=" * 72)

    if not NMF_KEYWORDS_CSV.exists():
        print(f"  NMF-Ergebnisse nicht gefunden: {NMF_KEYWORDS_CSV}")
        print("  Bitte zuerst s5_topics.py ausführen.")
        return

    df_nmf = pd.read_csv(NMF_KEYWORDS_CSV)

    # NMF-Termsets pro Topic
    nmf_termsets = {}
    for t_idx in df_nmf["topic"].unique():
        terms = df_nmf[df_nmf["topic"] == t_idx].sort_values("rank")["term"].tolist()
        nmf_termsets[t_idx] = set(terms[:TOP_N_WORDS])

    rows = []
    for _, mrow in df_mallet.iterrows():
        m_idx  = mrow["topic"]
        m_set  = set(mrow["terms"][:TOP_N_WORDS])
        m_top3 = " · ".join(mrow["terms"][:3])

        # Jaccard-Ähnlichkeit mit jedem NMF-Topic
        best_nmf   = -1
        best_jacc  = -1.0
        for n_idx, n_set in nmf_termsets.items():
            jacc = len(m_set & n_set) / len(m_set | n_set) if (m_set | n_set) else 0.0
            if jacc > best_jacc:
                best_jacc = jacc
                best_nmf  = n_idx

        nmf_terms = sorted(nmf_termsets.get(best_nmf, []))
        overlap   = sorted(m_set & nmf_termsets.get(best_nmf, set()))

        print(f"\n  MALLET T{m_idx}  [{m_top3}]")
        print(f"    Terme:         {', '.join(mrow['terms'][:TOP_N_WORDS])}")
        print(f"  → ähnlichstes NMF-Topic: T{best_nmf}  (Jaccard={best_jacc:.3f})")
        nmf_top3 = " · ".join(list(nmf_termsets.get(best_nmf, []))[:3])
        print(f"    NMF-Terme:     {', '.join(nmf_terms)}")
        if overlap:
            print(f"    Überschneidung:{', '.join(overlap)}")

        rows.append({
            "mallet_topic":   m_idx,
            "mallet_top3":    m_top3,
            "mallet_terms":   " ".join(mrow["terms"][:TOP_N_WORDS]),
            "nmf_topic":      best_nmf,
            "jaccard":        round(best_jacc, 4),
            "nmf_terms":      " ".join(nmf_terms),
            "overlap_terms":  " ".join(overlap),
        })

    df_cmp = pd.DataFrame(rows)
    df_cmp.to_csv(OUT_VERGLEICH, index=False, encoding="utf-8")
    print(f"\n  Vergleichstabelle gespeichert: {OUT_VERGLEICH}")
    print("=" * 72)


# =============================================================================
# Hauptprogramm
# =============================================================================

def main():
    log.info("=== s5b_mallet_direkt gestartet ===")

    # 1. MALLET prüfen
    check_mallet()

    # 2. Temporären Ordner anlegen und .txt-Dateien kopieren
    with tempfile.TemporaryDirectory(prefix="stadtwaechter_mallet_") as tmp_str:
        tmp_dir = Path(tmp_str)
        n_files = copy_txts_to_tmpdir(tmp_dir)
        log.info("Korpus: %d Dateien aus %s", n_files, CORPUS_DIR)

        # 3. MALLET import-dir
        mallet_import(tmp_dir)

    # (tmp_dir wird nach dem with-Block automatisch gelöscht)

    # 4. MALLET train-topics
    mallet_train()

    # 5. Ergebnisse einlesen
    log.info("Lese MALLET-Ergebnisse …")
    df_topics = parse_topic_keys(OUT_TOPICS)
    df_docs   = parse_doc_topics(OUT_DOC)
    log.info("Topics: %d  |  Dokumente: %d", len(df_topics), len(df_docs))

    # 6. Übersichtliche Ausgabe
    print_mallet_results(df_topics, df_docs)

    # 7. Vergleich mit NMF
    compare_with_nmf(df_topics)

    log.info("=== s5b_mallet_direkt abgeschlossen ===")
    log.info("Ergebnisse in %s", ERGEBNISSE)


if __name__ == "__main__":
    main()
