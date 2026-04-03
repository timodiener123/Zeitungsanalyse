"""
s1_frequency.py – Frequenzanalyse des lemmatisierten Stadtwächter-Korpus

Liest corpus_lemmatized.parquet, berechnet absolute und normalisierte
Häufigkeiten (per Million) für alle Lemmata und die Seed-Terme aus config.py.
Speichert CSVs in RESULTS_DIR und ein Liniendiagramm in VISUALIZATIONS_DIR.

Ausgabedateien:
    results/term_frequencies_gesamt.csv        – alle Lemmata, gesamt
    results/term_frequencies_nach_jahrgang.csv – alle Lemmata, pro Jahrgang
    results/seedterm_frequencies.csv           – Seed-Terme, pro Jahrgang
    visualizations/seedterm_trend.png          – Top-10-Seed-Terme als Linienplot
"""

import sys
import logging
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

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
log = logging.getLogger("s1_frequency")


# =============================================================================
# Hilfsfunktionen
# =============================================================================
def tokens_from_row(token_str: str) -> list[str]:
    """Kommagetrennte Token-Zeichenkette → Liste."""
    if not isinstance(token_str, str) or not token_str.strip():
        return []
    return token_str.split(",")


def freq_table(counter: Counter, total: int) -> pd.DataFrame:
    """Counter → DataFrame mit absoluter und normalisierter Häufigkeit."""
    df = pd.DataFrame(counter.most_common(), columns=["lemma", "abs"])
    df["per_million"] = (df["abs"] / total * 1_000_000).round(2)
    return df


# =============================================================================
# Hauptverarbeitung
# =============================================================================
def main():
    log.info("=== s1_frequency gestartet ===")

    # --- Daten laden ---
    parquet_path = config.PROCESSED_DIR / "corpus_lemmatized.parquet"
    if not parquet_path.exists():
        log.error("Parquet nicht gefunden: %s", parquet_path)
        sys.exit(1)

    df = pd.read_parquet(parquet_path)
    log.info("Korpus geladen: %d Dokumente", len(df))

    # --- Gesamtfrequenz ---
    all_tokens: list[str] = []
    for token_str in df["tokens"]:
        all_tokens.extend(tokens_from_row(token_str))

    counter_gesamt = Counter(all_tokens)
    total_gesamt = len(all_tokens)

    freq_gesamt = freq_table(counter_gesamt, total_gesamt)
    out_gesamt = config.RESULTS_DIR / "term_frequencies_gesamt.csv"
    freq_gesamt.to_csv(out_gesamt, index=False, encoding="utf-8")
    log.info("Gespeichert: %s  (%d Typen)", out_gesamt, len(freq_gesamt))

    # --- Frequenzen pro Jahrgang ---
    jahrgaenge: dict[int, Counter] = {}
    jahrgaenge_total: dict[int, int] = {}

    for year in config.TIME_SLICES:
        sub = df[df["year"] == year]
        tokens_year: list[str] = []
        for token_str in sub["tokens"]:
            tokens_year.extend(tokens_from_row(token_str))
        jahrgaenge[year] = Counter(tokens_year)
        jahrgaenge_total[year] = len(tokens_year)

    # DataFrame: eine Zeile pro (lemma, year)
    records_jg = []
    for year, counter in jahrgaenge.items():
        total = jahrgaenge_total[year]
        for lemma, abs_count in counter.items():
            records_jg.append({
                "year":       year,
                "lemma":      lemma,
                "abs":        abs_count,
                "per_million": round(abs_count / total * 1_000_000, 2),
            })

    freq_jg = (
        pd.DataFrame(records_jg)
        .sort_values(["year", "abs"], ascending=[True, False])
        .reset_index(drop=True)
    )
    out_jg = config.RESULTS_DIR / "term_frequencies_nach_jahrgang.csv"
    freq_jg.to_csv(out_jg, index=False, encoding="utf-8")
    log.info("Gespeichert: %s", out_jg)

    # --- Seed-Term-Frequenzen ---
    seed_records = []
    for year in config.TIME_SLICES:
        counter = jahrgaenge[year]
        total   = jahrgaenge_total[year]
        for term in config.ALL_SEED_TERMS:
            abs_count = counter.get(term, 0)
            seed_records.append({
                "year":       year,
                "term":       term,
                "category":   config.SEED_CATEGORIES.get(term, ""),
                "abs":        abs_count,
                "per_million": round(abs_count / total * 1_000_000, 2) if total else 0,
            })

    seed_df = (
        pd.DataFrame(seed_records)
        .sort_values(["term", "year"])
        .reset_index(drop=True)
    )
    out_seed = config.RESULTS_DIR / "seedterm_frequencies.csv"
    seed_df.to_csv(out_seed, index=False, encoding="utf-8")
    log.info("Gespeichert: %s", out_seed)

    # --- Visualisierung: Top-10-Seed-Terme (Liniendiagramm) ---
    # Rangfolge nach Gesamthäufigkeit über alle Jahrgänge
    seed_total = (
        seed_df.groupby("term")["abs"].sum()
        .sort_values(ascending=False)
    )
    top10_terms = seed_total.head(10).index.tolist()

    pivot = (
        seed_df[seed_df["term"].isin(top10_terms)]
        .pivot_table(index="year", columns="term", values="per_million", aggfunc="sum")
        .reindex(config.TIME_SLICES)
    )

    fig, ax = plt.subplots(figsize=(11, 6))
    markers = ["o", "s", "D", "^", "v", "P", "X", "*", "h", "p"]
    for i, term in enumerate(top10_terms):
        if term in pivot.columns:
            ax.plot(
                pivot.index,
                pivot[term],
                marker=markers[i % len(markers)],
                linewidth=1.8,
                markersize=7,
                label=term,
            )

    ax.set_title(
        "Top-10-Seed-Terme im Stadtwächter 1929–1931\n(Häufigkeit per Million Tokens)",
        fontsize=13, pad=14,
    )
    ax.set_xlabel("Jahrgang", fontsize=11)
    ax.set_ylabel("Häufigkeit per Million Tokens", fontsize=11)
    ax.set_xticks(config.TIME_SLICES)
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter("%d"))
    ax.legend(
        title="Seed-Term", fontsize=9, title_fontsize=9,
        loc="upper left", bbox_to_anchor=(1.01, 1), borderaxespad=0,
    )
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    fig.tight_layout()

    out_png = config.VISUALIZATIONS_DIR / "seedterm_trend.png"
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    log.info("Visualisierung gespeichert: %s", out_png)

    # ==========================================================================
    # Zusammenfassung
    # ==========================================================================
    print("\n" + "=" * 62)
    print("ZUSAMMENFASSUNG  –  s1_frequency")
    print("=" * 62)
    print(f"  Vokabular gesamt          : {len(freq_gesamt):>8,} Typen")
    print(f"  Tokens gesamt             : {total_gesamt:>8,}")
    print()
    print(f"  {'Jahrgang':<10} {'Tokens':>10} {'Typen':>8} {'Ø per Dok':>10}")
    print(f"  {'-'*10} {'-'*10} {'-'*8} {'-'*10}")
    for year in config.TIME_SLICES:
        n_docs = int((df["year"] == year).sum())
        tok    = jahrgaenge_total[year]
        typen  = len(jahrgaenge[year])
        avg    = int(tok / n_docs) if n_docs else 0
        print(f"  {year:<10} {tok:>10,} {typen:>8,} {avg:>10,}")
    print()

    # Top-5-Seed-Terme gesamt
    print("  Top-10-Seed-Terme (gesamt, per Million):")
    seed_pivot_total = (
        seed_df.groupby("term")[["abs", "per_million"]]
        .sum()
        .sort_values("abs", ascending=False)
        .head(10)
    )
    for term, row in seed_pivot_total.iterrows():
        cat = config.SEED_CATEGORIES.get(term, "")
        print(f"    {term:<22} abs={int(row['abs']):>5}   pMio={row['per_million']:>7.1f}   [{cat}]")

    print()
    print("  Ausgabedateien:")
    for p in [out_gesamt, out_jg, out_seed, out_png]:
        print(f"    {p}")
    print("=" * 62)
    log.info("=== s1_frequency abgeschlossen ===")


if __name__ == "__main__":
    main()
