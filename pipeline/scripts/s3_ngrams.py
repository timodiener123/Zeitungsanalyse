"""
s3_ngrams.py – N-Gramm-Analyse des Stadtwächter-Korpus

Berechnet Bi- und Trigramme aus den lemmatisierten Tokens, schlüsselt nach
Jahrgang auf, identifiziert antisemitische N-Gramme (enthalten Seed-Term)
und speichert alle Ergebnisse als CSV.

Ausgabedateien:
    results/ngrams_gesamt.csv          – Top-N Bi-/Trigramme über alle Jahre
    results/ngrams_nach_jahrgang.csv   – Top-N pro Jahrgang und N-Gramm-Größe
    results/ngrams_antisemitisch.csv   – N-Gramme mit mind. einem Seed-Term
"""

import sys
import logging
from collections import Counter
from itertools import islice
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

import pandas as pd

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
log = logging.getLogger("s3_ngrams")

# Seed-Term-Set für schnelle Mitgliedschaftsprüfung
SEED_SET = set(config.ALL_SEED_TERMS)


# =============================================================================
# Hilfsfunktionen
# =============================================================================
def tokens_from_row(s: str) -> list[str]:
    if not isinstance(s, str) or not s.strip():
        return []
    return s.split(",")


def ngrams(tokens: list[str], n: int):
    """Generator für n-Gramme aus einer Token-Liste."""
    it = iter(tokens)
    window = tuple(islice(it, n))
    if len(window) == n:
        yield window
    for token in it:
        window = window[1:] + (token,)
        yield window


def build_ngram_counter(token_lists: list[list[str]], n: int) -> Counter:
    counter: Counter = Counter()
    for tokens in token_lists:
        counter.update(ngrams(tokens, n))
    return counter


def counter_to_df(
    counter: Counter,
    n: int,
    total_tokens: int,
    top_n: int,
) -> pd.DataFrame:
    rows = []
    for gram, count in counter.most_common(top_n):
        rows.append({
            "ngram":      " ".join(gram),
            "n":          n,
            "abs":        count,
            "per_million": round(count / total_tokens * 1_000_000, 2) if total_tokens else 0,
            "is_antisemitic": any(t in SEED_SET for t in gram),
        })
    return pd.DataFrame(rows)


# =============================================================================
# Hauptverarbeitung
# =============================================================================
def main():
    log.info("=== s3_ngrams gestartet ===")

    parquet_path = config.PROCESSED_DIR / "corpus_lemmatized.parquet"
    if not parquet_path.exists():
        log.error("Parquet nicht gefunden: %s", parquet_path)
        sys.exit(1)

    df = pd.read_parquet(parquet_path)
    log.info("Korpus geladen: %d Dokumente", len(df))

    top_n      = config.TOP_N_NGRAMS   # aus config (default 30)
    ngram_sizes = config.NGRAM_SIZES   # [2, 3]

    # --- Gesamt-Token-Listen pro Jahrgang ---
    token_lists_all: list[list[str]] = []
    token_lists_year: dict[int, list[list[str]]] = {y: [] for y in config.TIME_SLICES}

    for _, row in df.iterrows():
        toks = tokens_from_row(row["tokens"])
        token_lists_all.append(toks)
        if row["year"] in token_lists_year:
            token_lists_year[row["year"]].append(toks)

    total_all = sum(len(t) for t in token_lists_all)

    # ------------------------------------------------------------------ Gesamt
    gesamt_parts: list[pd.DataFrame] = []
    for n in ngram_sizes:
        log.info("Berechne %d-Gramme (gesamt) …", n)
        counter = build_ngram_counter(token_lists_all, n)
        log.info("  %d distinkte %d-Gramme", len(counter), n)
        gesamt_parts.append(counter_to_df(counter, n, total_all, top_n))

    df_gesamt = pd.concat(gesamt_parts, ignore_index=True)
    out_gesamt = config.RESULTS_DIR / "ngrams_gesamt.csv"
    df_gesamt.to_csv(out_gesamt, index=False, encoding="utf-8")
    log.info("Gespeichert: %s", out_gesamt)

    # --------------------------------------------------------- Pro Jahrgang
    jg_parts: list[pd.DataFrame] = []
    for year in config.TIME_SLICES:
        total_year = sum(len(t) for t in token_lists_year[year])
        for n in ngram_sizes:
            counter = build_ngram_counter(token_lists_year[year], n)
            part = counter_to_df(counter, n, total_year, top_n)
            part.insert(0, "year", year)
            jg_parts.append(part)

    df_jg = pd.concat(jg_parts, ignore_index=True)
    out_jg = config.RESULTS_DIR / "ngrams_nach_jahrgang.csv"
    df_jg.to_csv(out_jg, index=False, encoding="utf-8")
    log.info("Gespeichert: %s", out_jg)

    # ------------------------------------------------------- Antisemitische N-Gramme
    # Alle N-Gramme (ohne top_n-Begrenzung) die mind. einen Seed-Term enthalten
    antisem_parts: list[pd.DataFrame] = []
    for year in config.TIME_SLICES:
        total_year = sum(len(t) for t in token_lists_year[year])
        for n in ngram_sizes:
            counter = build_ngram_counter(token_lists_year[year], n)
            rows = []
            for gram, count in counter.items():
                if any(t in SEED_SET for t in gram):
                    rows.append({
                        "year":        year,
                        "ngram":       " ".join(gram),
                        "n":           n,
                        "abs":         count,
                        "per_million": round(count / total_year * 1_000_000, 2) if total_year else 0,
                        "seed_terms":  ", ".join(t for t in gram if t in SEED_SET),
                        "category":    ", ".join(
                            dict.fromkeys(
                                config.SEED_CATEGORIES[t] for t in gram if t in SEED_SET
                            )
                        ),
                    })
            antisem_parts.append(
                pd.DataFrame(rows).sort_values("abs", ascending=False)
            )

    df_antisem = pd.concat(antisem_parts, ignore_index=True)
    out_antisem = config.RESULTS_DIR / "ngrams_antisemitisch.csv"
    df_antisem.to_csv(out_antisem, index=False, encoding="utf-8")
    log.info("Gespeichert: %s  (%d Einträge)", out_antisem, len(df_antisem))

    # ==========================================================================
    # Zusammenfassung
    # ==========================================================================
    print("\n" + "=" * 65)
    print("ZUSAMMENFASSUNG  –  s3_ngrams")
    print("=" * 65)

    for n in ngram_sizes:
        label = "Bigramme" if n == 2 else "Trigramme"
        sub = df_gesamt[df_gesamt["n"] == n]
        anti = sub[sub["is_antisemitic"]]
        print(f"\n  {label} (Top-{top_n} gesamt, {len(anti)} davon antisemitisch):")
        print(f"  {'N-Gramm':<35} {'abs':>6}  {'pMio':>8}  Antisemit.")
        print(f"  {'-'*35} {'-'*6}  {'-'*8}  {'-'*10}")
        for _, row in sub.iterrows():
            flag = "  [!]" if row["is_antisemitic"] else ""
            print(f"  {row['ngram']:<35} {int(row['abs']):>6}  {row['per_million']:>8.1f}{flag}")

    # Top-10 antisemitische N-Gramme pro Jahrgang
    print(f"\n  {'─'*63}")
    print("  TOP-10 ANTISEMITISCHE N-GRAMME PRO JAHRGANG:")
    for year in config.TIME_SLICES:
        sub = (
            df_antisem[df_antisem["year"] == year]
            .sort_values("abs", ascending=False)
            .head(10)
        )
        print(f"\n  {year}:")
        print(f"  {'N-Gramm':<35} {'n':>2}  {'abs':>5}  {'pMio':>8}  Seed-Terme")
        print(f"  {'-'*35} {'-'*2}  {'-'*5}  {'-'*8}  {'-'*20}")
        for _, row in sub.iterrows():
            print(f"  {row['ngram']:<35} {int(row['n']):>2}  "
                  f"{int(row['abs']):>5}  {row['per_million']:>8.1f}  {row['seed_terms']}")

    print(f"\n  Ausgabedateien:")
    for p in [out_gesamt, out_jg, out_antisem]:
        print(f"    {p}")
    print("=" * 65)
    log.info("=== s3_ngrams abgeschlossen ===")


if __name__ == "__main__":
    main()
