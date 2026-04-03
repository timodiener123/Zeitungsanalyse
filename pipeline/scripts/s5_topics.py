"""
s5_topics.py – NMF Topic Modeling des Stadtwächter-Korpus

Vektorisiert die lemmatisierten Tokens mit TF-IDF und berechnet
7 Topics via NMF (Non-negative Matrix Factorization). Anschließend
wird die Topic-Verteilung pro Dokument und Jahrgang ausgewertet
sowie die Anwesenheit von Seed-Termen in jedem Topic vermerkt.

Ausgabedateien:
    results/topics_keywords.csv      – Top-15-Terme pro Topic
    results/topics_doc_matrix.csv    – Topic-Gewichte pro Dokument
    results/topics_year_shares.csv   – mittlerer Topic-Anteil pro Jahrgang
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF

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
log = logging.getLogger("s5_topics")

N_TOPICS     = config.NMF_N_TOPICS        # 7
TOP_N_WORDS  = 15
SEED_SET     = set(config.ALL_SEED_TERMS)


# =============================================================================
# Hauptverarbeitung
# =============================================================================
def main():
    log.info("=== s5_topics gestartet ===")

    parquet_path = config.PROCESSED_DIR / "corpus_lemmatized.parquet"
    if not parquet_path.exists():
        log.error("Parquet nicht gefunden: %s", parquet_path)
        sys.exit(1)

    df = pd.read_parquet(parquet_path)
    log.info("Korpus geladen: %d Dokumente", len(df))

    # Tokens als Leerzeichen-getrennte Strings für TF-IDF
    # (parquet speichert sie kommagetrennt)
    docs = df["tokens"].fillna("").str.replace(",", " ")

    # ---------------------------------------------------------------- TF-IDF
    log.info("TF-IDF Vektorisierung …")
    vectorizer = TfidfVectorizer(
        max_features = config.TFIDF_MAX_FEATURES,   # 5000
        max_df       = config.TFIDF_MAX_DF,          # 0.90
        min_df       = config.TFIDF_MIN_DF,          # 3
    )
    tfidf_matrix = vectorizer.fit_transform(docs)
    vocab = vectorizer.get_feature_names_out()
    log.info("Vokabular: %d Terme, Matrix: %s", len(vocab), tfidf_matrix.shape)

    # ------------------------------------------------------------------- NMF
    log.info("NMF mit %d Topics …", N_TOPICS)
    nmf = NMF(
        n_components  = N_TOPICS,
        random_state  = config.NMF_RANDOM_STATE,
        max_iter      = 500,
    )
    W = nmf.fit_transform(tfidf_matrix)   # Dokument–Topic-Matrix (n_docs × n_topics)
    H = nmf.components_                   # Topic–Term-Matrix   (n_topics × n_terms)
    log.info("Rekonstruktionsfehler: %.4f", nmf.reconstruction_err_)

    # -------------------------------------------------- Topic-Keyword-Tabelle
    topic_rows = []
    for topic_idx in range(N_TOPICS):
        top_indices = H[topic_idx].argsort()[::-1][:TOP_N_WORDS]
        for rank, idx in enumerate(top_indices, start=1):
            term = vocab[idx]
            topic_rows.append({
                "topic":       topic_idx,
                "rank":        rank,
                "term":        term,
                "weight":      round(float(H[topic_idx, idx]), 6),
                "is_seedterm": term in SEED_SET,
            })

    df_keywords = pd.DataFrame(topic_rows)
    out_kw = config.RESULTS_DIR / "topics_keywords.csv"
    df_keywords.to_csv(out_kw, index=False, encoding="utf-8")
    log.info("Gespeichert: %s", out_kw)

    # ------------------------------------------ Dokument–Topic-Matrix als CSV
    topic_cols = [f"topic_{i}" for i in range(N_TOPICS)]
    df_W = pd.DataFrame(W, columns=topic_cols)
    df_W.insert(0, "doc_id", df["doc_id"].values)
    df_W.insert(1, "year",   df["year"].values)

    # Dominantes Topic pro Dokument
    df_W["dominant_topic"] = W.argmax(axis=1)

    out_doc = config.RESULTS_DIR / "topics_doc_matrix.csv"
    df_W.to_csv(out_doc, index=False, encoding="utf-8")
    log.info("Gespeichert: %s", out_doc)

    # ------------------------------------------ Topic-Anteile pro Jahrgang
    year_rows = []
    for year in config.TIME_SLICES:
        mask = df_W["year"] == year
        sub  = W[mask.values]
        if len(sub) == 0:
            continue
        # Normierte Anteile (Zeilen auf 1 summieren, dann Spaltenmittel)
        row_sums = sub.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1
        shares = (sub / row_sums).mean(axis=0)
        for t_idx, share in enumerate(shares):
            year_rows.append({
                "year":            year,
                "topic":           t_idx,
                "mean_share":      round(float(share), 6),
                "dominant_n_docs": int((W[mask.values].argmax(axis=1) == t_idx).sum()),
            })

    df_year = pd.DataFrame(year_rows)
    out_year = config.RESULTS_DIR / "topics_year_shares.csv"
    df_year.to_csv(out_year, index=False, encoding="utf-8")
    log.info("Gespeichert: %s", out_year)

    # ==========================================================================
    # Zusammenfassung
    # ==========================================================================

    # Kurzbezeichnung pro Topic (Top-3-Terme)
    def topic_label(t_idx: int) -> str:
        top3 = (
            df_keywords[df_keywords["topic"] == t_idx]
            .sort_values("rank")
            .head(3)["term"]
            .tolist()
        )
        return " · ".join(top3)

    print("\n" + "=" * 72)
    print("ZUSAMMENFASSUNG  –  s5_topics  (NMF, %d Topics)" % N_TOPICS)
    print("=" * 72)

    for t_idx in range(N_TOPICS):
        sub_kw = df_keywords[df_keywords["topic"] == t_idx].sort_values("rank")
        seed_in_topic = sub_kw[sub_kw["is_seedterm"]]["term"].tolist()
        top15 = sub_kw["term"].tolist()
        print(f"\n  Topic {t_idx}  [{topic_label(t_idx)}]")
        print(f"  Terme:    {', '.join(top15)}")
        if seed_in_topic:
            print(f"  Seed:     {', '.join(seed_in_topic)}")

        # Anteil pro Jahrgang
        for year in config.TIME_SLICES:
            row = df_year[(df_year["topic"] == t_idx) & (df_year["year"] == year)]
            if row.empty:
                continue
            share  = row["mean_share"].values[0]
            n_dom  = row["dominant_n_docs"].values[0]
            print(f"  {year}: {share*100:5.1f}%  ({n_dom} Dok. dominant)")

    # Jahresvergleich: welche Topics gewinnen/verlieren?
    print(f"\n  {'─'*70}")
    print("  TOPIC-ANTEILE IM JAHRESVERGLEICH (%):")
    header = f"  {'Topic (Top-3)':<30}"
    for y in config.TIME_SLICES:
        header += f"  {y:>8}"
    print(header)
    print(f"  {'-'*30}" + "  " + "  ".join(["-"*8] * len(config.TIME_SLICES)))

    for t_idx in range(N_TOPICS):
        row_str = f"  T{t_idx}: {topic_label(t_idx):<26}"
        for year in config.TIME_SLICES:
            row = df_year[(df_year["topic"] == t_idx) & (df_year["year"] == year)]
            share = row["mean_share"].values[0] * 100 if not row.empty else 0.0
            row_str += f"  {share:>7.1f}%"
        print(row_str)

    print(f"\n  Ausgabedateien:")
    for p in [out_kw, out_doc, out_year]:
        print(f"    {p}")
    print("=" * 72)
    log.info("=== s5_topics abgeschlossen ===")


if __name__ == "__main__":
    main()
