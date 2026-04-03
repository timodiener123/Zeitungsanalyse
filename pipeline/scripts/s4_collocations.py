"""
s4_collocations.py – Kollokationsanalyse für Kernbegriffe

Berechnet für die Zielwörter jude, jüdisch, judentum Kollokationen
innerhalb eines Fensters von ±5 Wörtern. Als Assoziationsmaße werden
Log-Likelihood (G²) nach Dunning (1993) und PMI (Pointwise Mutual
Information) verwendet. Ergebnisse werden pro Jahrgang aufgeschlüsselt.

Ausgabedateien:
    results/collocations_ll.csv   – nach Log-Likelihood sortiert
    results/collocations_pmi.csv  – nach PMI sortiert
"""

import sys
import logging
import math
from collections import Counter, defaultdict
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
log = logging.getLogger("s4_collocations")

# Zielwörter und Fenstergröße
TARGET_WORDS = ["jude", "jüdisch", "judentum"]
WINDOW       = config.COLLOCATIONS_WINDOW   # 5
TOP_N        = config.TOP_N_COLLOCATIONS    # 20
MIN_COFREQ   = 3   # Mindest-Kookkurrenzfrequenz


# =============================================================================
# Hilfsfunktionen
# =============================================================================
def tokens_from_row(s: str) -> list[str]:
    if not isinstance(s, str) or not s.strip():
        return []
    return s.split(",")


def log_likelihood_colloc(o11: int, o12: int, o21: int, o22: int) -> float:
    """G² für Kollokations-Kontingenztafel (Dunning 1993)."""
    n = o11 + o12 + o21 + o22
    if n == 0:
        return 0.0
    e11 = (o11 + o12) * (o11 + o21) / n
    e12 = (o11 + o12) * (o12 + o22) / n
    e21 = (o21 + o22) * (o11 + o21) / n
    e22 = (o21 + o22) * (o12 + o22) / n

    def _cell(o, e):
        return o * math.log(o / e) if o > 0 and e > 0 else 0.0

    return round(2 * (_cell(o11, e11) + _cell(o12, e12) +
                      _cell(o21, e21) + _cell(o22, e22)), 4)


def pmi(o11: int, n_total: int, freq_target: int, freq_collocate: int) -> float:
    """Pointwise Mutual Information: log2( P(w,c) / P(w)*P(c) )."""
    if o11 == 0 or freq_target == 0 or freq_collocate == 0 or n_total == 0:
        return float("-inf")
    p_joint   = o11 / n_total
    p_target  = freq_target / n_total
    p_colloc  = freq_collocate / n_total
    return round(math.log2(p_joint / (p_target * p_colloc)), 4)


def extract_collocations(
    token_lists: list[list[str]],
    target: str,
    window: int,
) -> tuple[Counter, Counter, int]:
    """
    Zählt für `target` alle Kookkurrenzen im ±window-Fenster.
    Gibt (cofreq_counter, collocate_unifreq, n_total_tokens) zurück.
    cofreq_counter[w]      = Anzahl Fenster in denen target und w gemeinsam vorkommen
    collocate_unifreq[w]   = Gesamthäufigkeit von w im Korpus
    """
    cofreq: Counter    = Counter()
    unifreq: Counter   = Counter()
    n_total = 0

    for tokens in token_lists:
        n_total += len(tokens)
        unifreq.update(tokens)
        for i, tok in enumerate(tokens):
            if tok == target:
                left  = max(0, i - window)
                right = min(len(tokens), i + window + 1)
                context = tokens[left:i] + tokens[i+1:right]
                cofreq.update(context)

    return cofreq, unifreq, n_total


def build_colloc_df(
    cofreq: Counter,
    unifreq: Counter,
    n_total: int,
    freq_target: int,
    target: str,
    min_cofreq: int = MIN_COFREQ,
) -> pd.DataFrame:
    rows = []
    for collocate, o11 in cofreq.items():
        if o11 < min_cofreq or collocate == target:
            continue
        freq_c = unifreq.get(collocate, 0)
        # Kontingenztafel
        o12 = freq_target - o11          # target ohne collocate (im Fenster)
        o21 = freq_c - o11               # collocate ohne target
        o22 = n_total - o11 - o12 - o21  # weder noch
        if o12 < 0 or o21 < 0 or o22 < 0:
            continue
        ll  = log_likelihood_colloc(o11, o12, o21, o22)
        pmi_val = pmi(o11, n_total, freq_target, freq_c)
        rows.append({
            "target":    target,
            "collocate": collocate,
            "cofreq":    o11,
            "freq_target": freq_target,
            "freq_collocate": freq_c,
            "n_total":   n_total,
            "ll":        ll,
            "pmi":       pmi_val,
        })

    return pd.DataFrame(rows)


# =============================================================================
# Hauptverarbeitung
# =============================================================================
def main():
    log.info("=== s4_collocations gestartet ===")

    parquet_path = config.PROCESSED_DIR / "corpus_lemmatized.parquet"
    if not parquet_path.exists():
        log.error("Parquet nicht gefunden: %s", parquet_path)
        sys.exit(1)

    df_corpus = pd.read_parquet(parquet_path)
    log.info("Korpus geladen: %d Dokumente", len(df_corpus))

    # Token-Listen pro Jahrgang aufbauen
    token_lists_year: dict[int, list[list[str]]] = {y: [] for y in config.TIME_SLICES}
    token_lists_all: list[list[str]] = []
    for _, row in df_corpus.iterrows():
        toks = tokens_from_row(row["tokens"])
        token_lists_all.append(toks)
        if row["year"] in token_lists_year:
            token_lists_year[row["year"]].append(toks)

    scopes: dict[str, list[list[str]]] = {"gesamt": token_lists_all}
    for y in config.TIME_SLICES:
        scopes[str(y)] = token_lists_year[y]

    # --- Alle Kollokationen berechnen ---
    all_ll:  list[pd.DataFrame] = []
    all_pmi: list[pd.DataFrame] = []

    for scope_label, token_lists in scopes.items():
        for target in TARGET_WORDS:
            log.info("  Scope=%s, target=%s …", scope_label, target)
            cofreq, unifreq, n_total = extract_collocations(
                token_lists, target, WINDOW
            )
            freq_target = unifreq.get(target, 0)
            if freq_target == 0:
                log.warning("    '%s' nicht im Vokabular – übersprungen", target)
                continue

            cdf = build_colloc_df(cofreq, unifreq, n_total, freq_target, target)
            if cdf.empty:
                continue

            cdf.insert(0, "scope", scope_label)

            # Top-N nach LL
            all_ll.append(
                cdf.sort_values("ll", ascending=False).head(TOP_N).copy()
            )
            # Top-N nach PMI (nur Terme mit cofreq >= 5 für Stabilität)
            all_pmi.append(
                cdf[cdf["cofreq"] >= 5]
                .sort_values("pmi", ascending=False)
                .head(TOP_N)
                .copy()
            )

    df_ll  = pd.concat(all_ll,  ignore_index=True)
    df_pmi = pd.concat(all_pmi, ignore_index=True)

    out_ll  = config.RESULTS_DIR / "collocations_ll.csv"
    out_pmi = config.RESULTS_DIR / "collocations_pmi.csv"
    df_ll.to_csv(out_ll,   index=False, encoding="utf-8")
    df_pmi.to_csv(out_pmi, index=False, encoding="utf-8")
    log.info("Gespeichert: %s", out_ll)
    log.info("Gespeichert: %s", out_pmi)

    # ==========================================================================
    # Zusammenfassung
    # ==========================================================================
    print("\n" + "=" * 70)
    print("ZUSAMMENFASSUNG  –  s4_collocations  (Fenster ±%d)" % WINDOW)
    print("=" * 70)

    for target in TARGET_WORDS:
        print(f"\n  Zielwort: '{target}'")
        print(f"  {'─'*68}")

        for scope_label in ["gesamt"] + [str(y) for y in config.TIME_SLICES]:
            sub_ll = df_ll[(df_ll["target"] == target) & (df_ll["scope"] == scope_label)]
            if sub_ll.empty:
                continue
            label = f"Jahrgang {scope_label}" if scope_label != "gesamt" else "Gesamt"
            print(f"\n  [{label}]  Top-{min(TOP_N, len(sub_ll))} nach Log-Likelihood:")
            print(f"  {'Kollokat':<22} {'cofreq':>7}  {'G²':>9}  {'PMI':>7}")
            print(f"  {'-'*22} {'-'*7}  {'-'*9}  {'-'*7}")
            for _, row in sub_ll.head(TOP_N).iterrows():
                print(f"  {row['collocate']:<22} {int(row['cofreq']):>7}  "
                      f"{row['ll']:>9.1f}  {row['pmi']:>7.2f}")

    # Jahresvergleich für 'jude' – welche Kollokate wandern?
    print(f"\n  {'─'*68}")
    print("  JAHRESVERGLEICH 'jude' – Top-15 nach LL pro Jahrgang (kompakt):")
    header = f"  {'Kollokat':<22}"
    for y in config.TIME_SLICES:
        header += f"  {y}(G²)"
    print(header)
    print(f"  {'-'*22}" + "  " + "  ".join(["-"*10] * len(config.TIME_SLICES)))

    # Alle Kollokate sammeln die in mind. einem Jahr Top-15 sind
    top_per_year: dict[int, pd.DataFrame] = {}
    for y in config.TIME_SLICES:
        sub = df_ll[(df_ll["target"] == "jude") & (df_ll["scope"] == str(y))].head(15)
        top_per_year[y] = sub.set_index("collocate")

    all_colloc = sorted(
        set().union(*[set(v.index) for v in top_per_year.values()])
    )
    for colloc in all_colloc:
        row_str = f"  {colloc:<22}"
        for y in config.TIME_SLICES:
            val = top_per_year[y]["ll"].get(colloc, float("nan"))
            row_str += f"  {val:>10.1f}" if not math.isnan(val) else f"  {'–':>10}"
        print(row_str)

    print(f"\n  Ausgabedateien:")
    for p in [out_ll, out_pmi]:
        print(f"    {p}")
    print("=" * 70)
    log.info("=== s4_collocations abgeschlossen ===")


if __name__ == "__main__":
    main()
