"""
s1b_regex_frequenz.py – Regex-basierte Frequenzanalyse (Methode des Professors)

Liest rohe .txt-Dateien direkt ein (NICHT das lemmatisierte Parquet) und zählt
alle Wortformen der Zielterme per Regex (\\bjude\\w*\\b usw., case-insensitive).

Ausgabe:
    ergebnisse/regex_frequenz.csv   – absolut + ppm nach Jahrgang
    Konsolenausgabe mit Vergleich zur Lemma-Zählung (s1_frequency)
"""

import re
import sys
from pathlib import Path
from collections import defaultdict

import pandas as pd

# ── Pfade ─────────────────────────────────────────────────────────────────────
BASE        = Path("/home/nghm/Dokumente/Zeitungsanalyse")
CORPUS_DIR  = (
    BASE / "daten_txt"
    / "wetransfer_pdf-stadtwachter_2026-03-03_2338"
    / "txt Stadtwächter"
)
LEMMA_CSV   = BASE / "pipeline/data/results/seedterm_frequencies.csv"
OUT_CSV     = BASE / "ergebnisse/regex_frequenz.csv"
YEARS       = [1929, 1930, 1931]

# ── Regex-Terme (Stamm → Kategorie) ──────────────────────────────────────────
# Muster: \b<stamm>\w*\b  – Wortgrenze + Stamm + beliebige Endung
TERMS: dict[str, str] = {
    "jude":              "Ethnisierung",
    "jüdisch":           "Ethnisierung",
    "judentum":          "Ethnisierung",
    "nationalsozialist": "NS-Terminologie",
    "antisemit":         "NS-Terminologie",
    "rasse":             "NS-Terminologie",
    "volksgenosse":      "NS-Terminologie",
    "bolschewismus":     "Ideologie",
    "sozialdemokrat":    "Ideologie",
    "vaterland":         "Ideologie",
    "stahlhelm":         "Ideologie",
    "schmarotzer":       "Dehumanisierung",
    "parasit":           "Dehumanisierung",
    "ungeziefer":        "Dehumanisierung",
}

# Kompiliere Muster einmalig
PATTERNS: dict[str, re.Pattern] = {
    term: re.compile(r"\b" + re.escape(term) + r"\w*\b", re.IGNORECASE)
    for term in TERMS
}

# Hilfs-Regex für Wort-Token (für ppm-Basis)
WORD_RE = re.compile(r"\b\w+\b")


# ── Dateien einlesen ──────────────────────────────────────────────────────────

def load_corpus() -> dict[int, list[tuple[str, str]]]:
    """
    Gibt {year: [(dateiname, text), ...]} zurück.
    Jahrgang wird aus dem Unterordner-Namen ermittelt (1929/1930/1931).
    Fallback: YEAR_PATTERN im Dateinamen.
    """
    year_re = re.compile(r"(192[0-9]|193[0-9])")
    corpus: dict[int, list[tuple[str, str]]] = {y: [] for y in YEARS}

    for txt_file in sorted(CORPUS_DIR.rglob("*.txt")):
        # Jahrgang aus Elternordner
        parent = txt_file.parent.name
        m = year_re.fullmatch(parent)
        if m:
            year = int(m.group(1))
        else:
            # Fallback: Jahr im Dateinamen
            m2 = year_re.search(txt_file.name)
            if not m2:
                continue
            year = int(m2.group(1))

        if year not in corpus:
            continue

        try:
            text = txt_file.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"  Warnung: {txt_file.name} – {e}", file=sys.stderr)
            continue

        corpus[year].append((txt_file.name, text))

    return corpus


# ── Zählung ───────────────────────────────────────────────────────────────────

def count_corpus(corpus: dict[int, list[tuple[str, str]]]) -> pd.DataFrame:
    records = []
    tokens_per_year: dict[int, int] = {}

    for year, docs in corpus.items():
        # Gesamttoken-Zahl für ppm-Basis
        full_text = " ".join(text for _, text in docs)
        n_tokens  = len(WORD_RE.findall(full_text))
        tokens_per_year[year] = n_tokens

        # Regex-Zählung pro Term
        for term, pattern in PATTERNS.items():
            matches = pattern.findall(full_text)
            abs_count = len(matches)
            ppm = round(abs_count / n_tokens * 1_000_000, 1) if n_tokens else 0.0

            # Die häufigsten Wortformen für Info
            form_counter: dict[str, int] = defaultdict(int)
            for m in matches:
                form_counter[m.lower()] += 1
            top_forms = sorted(form_counter, key=form_counter.__getitem__, reverse=True)[:5]

            records.append({
                "year":      year,
                "term":      term,
                "category":  TERMS[term],
                "abs":       abs_count,
                "per_million": ppm,
                "n_tokens":  n_tokens,
                "n_docs":    len(docs),
                "top_forms": ", ".join(top_forms),
            })

    df = pd.DataFrame(records).sort_values(["term", "year"]).reset_index(drop=True)
    return df


# ── Vergleich mit Lemma-Zählung ───────────────────────────────────────────────

def compare_with_lemma(regex_df: pd.DataFrame) -> None:
    if not LEMMA_CSV.exists():
        print("\n[Vergleich] Lemma-CSV nicht gefunden, übersprungen.")
        return

    lemma_df = pd.read_csv(LEMMA_CSV)

    # Mapping: Regex-Stamm → passende Lemma-Terme
    # (Lemma-CSV enthält einzelne Formen; wir aggregieren auf den Stamm)
    stem_to_lemmas: dict[str, list[str]] = {
        "jude":              ["jude", "juden"],
        "jüdisch":           ["jüdisch", "jüdische", "jüdischen", "jüdischer", "jüdisches"],
        "judentum":          ["judentum"],
        "nationalsozialist": ["nationalsozialist", "nationalsozialisten", "nationalsozialistisch"],
        "antisemit":         [],   # kein direktes Lemma in s1
        "rasse":             ["rasse"],
        "volksgenosse":      ["volksgenosse", "volksgenossen"],
        "bolschewismus":     [],
        "sozialdemokrat":    [],
        "vaterland":         [],
        "stahlhelm":         ["stahlhelm"],
        "schmarotzer":       ["schmarotzer"],
        "parasit":           ["parasit", "parasiten"],
        "ungeziefer":        ["ungeziefer"],
    }

    print("\n" + "=" * 72)
    print("VERGLEICH: Regex-Zählung  vs.  Lemma-Zählung (s1_frequency)")
    print("=" * 72)
    print(f"{'Term':<22} {'Jahr':<6} {'Regex abs':>10} {'Regex ppm':>10} "
          f"{'Lemma abs':>10} {'Lemma ppm':>10} {'Δ%':>8}")
    print("-" * 72)

    for term in TERMS:
        lemma_keys = stem_to_lemmas.get(term, [])
        for year in YEARS:
            # Regex-Wert
            r_row = regex_df[(regex_df["term"] == term) & (regex_df["year"] == year)]
            r_abs = int(r_row["abs"].values[0]) if len(r_row) else 0
            r_ppm = float(r_row["per_million"].values[0]) if len(r_row) else 0.0

            # Lemma-Wert (Summe über alle passenden Lemma-Terme)
            if lemma_keys:
                l_rows = lemma_df[
                    (lemma_df["term"].isin(lemma_keys)) & (lemma_df["year"] == year)
                ]
                l_abs = int(l_rows["abs"].sum())
                l_ppm = round(float(l_rows["per_million"].sum()), 1)
            else:
                l_abs = -1   # kein Lemma-Pendant
                l_ppm = -1.0

            if l_abs >= 0 and l_abs > 0:
                delta = round((r_abs - l_abs) / l_abs * 100, 1)
                delta_str = f"{delta:+.1f}%"
            elif l_abs == 0 and r_abs == 0:
                delta_str = "±0%"
            elif l_abs < 0:
                delta_str = "n/a"
            else:
                delta_str = "∞"

            l_abs_str = str(l_abs) if l_abs >= 0 else "—"
            l_ppm_str = f"{l_ppm:.1f}" if l_ppm >= 0 else "—"

            print(f"{term:<22} {year:<6} {r_abs:>10} {r_ppm:>10.1f} "
                  f"{l_abs_str:>10} {l_ppm_str:>10} {delta_str:>8}")
    print("=" * 72)
    print()
    print("Hinweis: Regex zählt ALLE Wortformen im Rohtext (inkl. Komposita).")
    print("Lemma-Zählung arbeitet auf normalisierten Grundformen (spaCy).")
    print("Positive Δ% = Regex findet mehr Treffer (z.B. Komposita wie 'Judenhetze').")
    print()


# ── Zusammenfassung ───────────────────────────────────────────────────────────

def print_summary(df: pd.DataFrame) -> None:
    print()
    print("=" * 68)
    print("REGEX-FREQUENZANALYSE  –  s1b_regex_frequenz")
    print("=" * 68)

    # Korpus-Statistik
    stats = df.drop_duplicates(["year"])[["year", "n_docs", "n_tokens"]]
    print(f"\n  {'Jahrgang':<10} {'Ausgaben':>8} {'Tokens (Rohtext)':>18}")
    print(f"  {'-'*10} {'-'*8} {'-'*18}")
    for _, row in stats.iterrows():
        print(f"  {int(row['year']):<10} {int(row['n_docs']):>8} {int(row['n_tokens']):>18,}")

    print()
    # Ergebnistabelle nach Term
    print(f"  {'Term':<22} {'Kat.':<16} "
          f"{'1929 abs':>9} {'ppm':>7}  "
          f"{'1930 abs':>9} {'ppm':>7}  "
          f"{'1931 abs':>9} {'ppm':>7}")
    print(f"  {'-'*22} {'-'*16} " + ("-"*9+" "+"-"*7+"  ")*3)

    for term in TERMS:
        sub = df[df["term"] == term].set_index("year")
        cat = TERMS[term][:15]
        row_parts = []
        for y in YEARS:
            if y in sub.index:
                a = int(sub.loc[y, "abs"])
                p = float(sub.loc[y, "per_million"])
                row_parts.append(f"{a:>9} {p:>7.1f}")
            else:
                row_parts.append(f"{'—':>9} {'—':>7}")
        print(f"  {term:<22} {cat:<16} " + "  ".join(row_parts))

    print()
    print(f"  CSV gespeichert: {OUT_CSV}")
    print("=" * 68)


# ── Hauptprogramm ─────────────────────────────────────────────────────────────

def main():
    print("s1b_regex_frequenz: Lade Rohtext-Korpus …")
    corpus = load_corpus()

    for year, docs in corpus.items():
        print(f"  {year}: {len(docs)} Dateien")

    print("\nZähle Regex-Treffer …")
    df = count_corpus(corpus)

    # Speichern
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8")

    # Ausgabe
    print_summary(df)
    compare_with_lemma(df)


if __name__ == "__main__":
    main()
