"""
s2_keywords.py – Keyword-Analyse via Log-Likelihood (Dunning 1993)

Vergleicht je zwei aufeinanderfolgende Jahrgänge (1929→1930, 1930→1931)
und berechnet für jedes Lemma den Log-Likelihood-Wert (G²). Hohe positive
Werte markieren Aufsteiger (Überrepräsentation im späteren Jahrgang),
hohe negative Werte Absteiger.

Ausgabedateien:
    results/keywords_transitions.csv   – alle Terme mit G², Richtung, Rängen
"""

import sys
import logging
import math
from collections import Counter
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
log = logging.getLogger("s2_keywords")


# =============================================================================
# Log-Likelihood nach Dunning (1993)
# =============================================================================
def log_likelihood(o11: int, o12: int, o21: int, o22: int) -> float:
    """
    Berechnet G² (Log-Likelihood-Ratio) für eine 2×2-Kontingenztafel.

        |  Korpus A  |  Korpus B  |
    w   |    o11     |    o12     |
    ~w  |    o21     |    o22     |

    Gibt positiven Wert zurück, wenn w in A häufiger ist (Aufsteiger in B
    wird durch negatives Vorzeichen signalisiert – Konvention: Vorzeichen
    entspricht Richtung relativ zu A).
    """
    n = o11 + o12 + o21 + o22
    e11 = (o11 + o12) * (o11 + o21) / n
    e12 = (o11 + o12) * (o12 + o22) / n
    e21 = (o21 + o22) * (o11 + o21) / n
    e22 = (o21 + o22) * (o12 + o22) / n

    def _cell(o, e):
        if o == 0 or e == 0:
            return 0.0
        return o * math.log(o / e)

    g2 = 2 * (_cell(o11, e11) + _cell(o12, e12) +
              _cell(o21, e21) + _cell(o22, e22))

    # Vorzeichen: positiv → stärker in A (Referenz), negativ → stärker in B
    sign = 1 if (o11 / (o11 + o21 + 1e-9)) >= (o12 / (o12 + o22 + 1e-9)) else -1
    return round(sign * g2, 4)


def compare_corpora(
    counter_a: Counter,
    total_a: int,
    counter_b: Counter,
    total_b: int,
    min_abs: int = 5,
) -> pd.DataFrame:
    """
    Vergleicht zwei Korpora term-weise via Log-Likelihood.
    Gibt DataFrame mit G², Häufigkeiten und Richtung zurück.
    """
    vocab = set(counter_a.keys()) | set(counter_b.keys())
    records = []
    for term in vocab:
        o11 = counter_a.get(term, 0)   # term in A
        o12 = counter_b.get(term, 0)   # term in B
        if o11 + o12 < min_abs:
            continue
        o21 = total_a - o11            # ~term in A
        o22 = total_b - o12            # ~term in B
        g2  = log_likelihood(o11, o12, o21, o22)
        pm_a = round(o11 / total_a * 1_000_000, 2) if total_a else 0
        pm_b = round(o12 / total_b * 1_000_000, 2) if total_b else 0
        records.append({
            "term":      term,
            "abs_a":     o11,
            "abs_b":     o12,
            "pmio_a":    pm_a,
            "pmio_b":    pm_b,
            "pmio_diff": round(pm_b - pm_a, 2),
            "g2":        g2,
            "direction": "Absteiger" if g2 > 0 else "Aufsteiger",
        })

    df = pd.DataFrame(records)
    # Rang: Aufsteiger nach -G² (stärkstes Wachstum oben), Absteiger nach +G²
    df["rank_aufsteiger"] = df["g2"].rank(method="min", ascending=True).astype(int)
    df["rank_absteiger"]  = df["g2"].rank(method="min", ascending=False).astype(int)
    return df.sort_values("g2", ascending=True).reset_index(drop=True)


def tokens_from_row(s: str) -> list[str]:
    if not isinstance(s, str) or not s.strip():
        return []
    return s.split(",")


# =============================================================================
# Hauptverarbeitung
# =============================================================================
def main():
    log.info("=== s2_keywords gestartet ===")

    parquet_path = config.PROCESSED_DIR / "corpus_lemmatized.parquet"
    if not parquet_path.exists():
        log.error("Parquet nicht gefunden: %s", parquet_path)
        sys.exit(1)

    df = pd.read_parquet(parquet_path)
    log.info("Korpus geladen: %d Dokumente", len(df))

    # --- Counters pro Jahrgang ---
    counters: dict[int, Counter] = {}
    totals:   dict[int, int]     = {}
    for year in config.TIME_SLICES:
        tokens: list[str] = []
        for s in df[df["year"] == year]["tokens"]:
            tokens.extend(tokens_from_row(s))
        counters[year] = Counter(tokens)
        totals[year]   = len(tokens)
        log.info("  %d: %d Tokens, %d Typen", year, totals[year], len(counters[year]))

    # --- Übergänge berechnen ---
    transitions = [
        (1929, 1930, "1929→1930"),
        (1930, 1931, "1930→1931"),
    ]

    all_results: list[pd.DataFrame] = []
    for year_a, year_b, label in transitions:
        log.info("Berechne Übergang %s …", label)
        comp = compare_corpora(
            counters[year_a], totals[year_a],
            counters[year_b], totals[year_b],
            min_abs=5,
        )
        comp.insert(0, "transition", label)
        all_results.append(comp)
        log.info("  %d Terme analysiert", len(comp))

    result_df = pd.concat(all_results, ignore_index=True)

    out_path = config.RESULTS_DIR / "keywords_transitions.csv"
    result_df.to_csv(out_path, index=False, encoding="utf-8")
    log.info("Gespeichert: %s", out_path)

    # ==========================================================================
    # Zusammenfassung
    # ==========================================================================
    print("\n" + "=" * 68)
    print("ZUSAMMENFASSUNG  –  s2_keywords  (Log-Likelihood, Dunning 1993)")
    print("=" * 68)

    for _, label in [(0, "1929→1930"), (1, "1930→1931")]:
        sub = result_df[result_df["transition"] == label]
        aufsteiger = sub[sub["direction"] == "Aufsteiger"].sort_values("g2", ascending=True)
        absteiger  = sub[sub["direction"] == "Absteiger"].sort_values("g2", ascending=False)

        print(f"\n  Übergang {label}  ({len(sub):,} Terme analysiert)")
        print(f"  {'─'*64}")

        print(f"  TOP-10 AUFSTEIGER (stärker in {label.split('→')[1]}):")
        print(f"  {'Term':<24} {'G²':>9}  {'pMio A':>8}  {'pMio B':>8}  {'Δ pMio':>9}")
        print(f"  {'-'*24} {'-'*9}  {'-'*8}  {'-'*8}  {'-'*9}")
        for _, row in aufsteiger.head(10).iterrows():
            print(f"  {row['term']:<24} {row['g2']:>9.1f}  "
                  f"{row['pmio_a']:>8.1f}  {row['pmio_b']:>8.1f}  {row['pmio_diff']:>+9.1f}")

        print(f"\n  TOP-10 ABSTEIGER (stärker in {label.split('→')[0]}):")
        print(f"  {'Term':<24} {'G²':>9}  {'pMio A':>8}  {'pMio B':>8}  {'Δ pMio':>9}")
        print(f"  {'-'*24} {'-'*9}  {'-'*8}  {'-'*8}  {'-'*9}")
        for _, row in absteiger.head(10).iterrows():
            print(f"  {row['term']:<24} {row['g2']:>9.1f}  "
                  f"{row['pmio_a']:>8.1f}  {row['pmio_b']:>8.1f}  {row['pmio_diff']:>+9.1f}")

    # Seed-Terme im Überblick
    print(f"\n  {'─'*64}")
    print("  SEED-TERME (G²-Werte pro Übergang):")
    print(f"  {'Term':<24} {'Kategorie':<18} {'G² 29→30':>10} {'G² 30→31':>10}")
    print(f"  {'-'*24} {'-'*18} {'-'*10} {'-'*10}")

    for term in sorted(config.ALL_SEED_TERMS):
        g2_vals = {}
        for label in ["1929→1930", "1930→1931"]:
            sub = result_df[(result_df["transition"] == label) & (result_df["term"] == term)]
            g2_vals[label] = sub["g2"].values[0] if not sub.empty else float("nan")
        cat = config.SEED_CATEGORIES.get(term, "")
        g2_a = g2_vals["1929→1930"]
        g2_b = g2_vals["1930→1931"]
        a_str = f"{g2_a:>10.1f}" if not math.isnan(g2_a) else f"{'–':>10}"
        b_str = f"{g2_b:>10.1f}" if not math.isnan(g2_b) else f"{'–':>10}"
        print(f"  {term:<24} {cat:<18} {a_str} {b_str}")

    print(f"\n  Ausgabe: {out_path}")
    print("=" * 68)
    log.info("=== s2_keywords abgeschlossen ===")


if __name__ == "__main__":
    main()
