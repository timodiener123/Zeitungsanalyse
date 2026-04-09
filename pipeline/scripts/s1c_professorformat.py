"""
s1c_professorformat.py – Ergebnistabelle im Format des Professorenberichts

Für jeden Term:
  - Absolute Häufigkeit pro Jahrgang
  - Dokument-Abdeckung pro Jahrgang (Format: "28/35")

Ausgabe:
    ergebnisse/regex_frequenz_professorformat.csv
    ergebnisse/regex_frequenz_professorformat.md
"""

import re
from pathlib import Path

import pandas as pd

# ── Pfade ─────────────────────────────────────────────────────────────────────
BASE       = Path("/home/nghm/Dokumente/Zeitungsanalyse")
CORPUS_DIR = (
    BASE / "daten_txt"
    / "wetransfer_pdf-stadtwachter_2026-03-03_2338"
    / "txt Stadtwächter"
)
OUT_CSV    = BASE / "ergebnisse/regex_frequenz_professorformat.csv"
OUT_MD     = BASE / "ergebnisse/regex_frequenz_professorformat.md"
YEARS      = [1929, 1930, 1931]

# ── Terme und ihre Regex-Muster ───────────────────────────────────────────────
# "jude" und "juden" sind GETRENNT:
#   jude  → r'\bjude[^n\w]' würde Komposita ausschließen; wir wählen
#            r'\bjude[^n]\w*\b|\bjude\b' → alle Formen AUSSER juden*
#   juden → r'\bjuden\w*\b'
# Sternchen-Terme: Stamm + beliebige Endung

TERMS: list[tuple[str, re.Pattern]] = [
    # Bezeichnung          , Regex-Muster (case-insensitive)
    ("jude",               re.compile(r"\bjude(?!n)\w*\b",          re.IGNORECASE)),
    ("juden",              re.compile(r"\bjuden\w*\b",               re.IGNORECASE)),
    ("antisemit*",         re.compile(r"\bantisemit\w*\b",           re.IGNORECASE)),
    ("rasse",              re.compile(r"\brasse\w*\b",               re.IGNORECASE)),
    ("volksgenosse",       re.compile(r"\bvolksgenosse\w*\b",        re.IGNORECASE)),
    ("nationalsozialist",  re.compile(r"\bnationalsozialist\w*\b",   re.IGNORECASE)),
    ("sozialdemokrat",     re.compile(r"\bsozialdemokrat\w*\b",      re.IGNORECASE)),
    ("boykott",            re.compile(r"\bboykott\w*\b",             re.IGNORECASE)),
    ("wucher",             re.compile(r"\bwucher\w*\b",              re.IGNORECASE)),
    ("hetze",              re.compile(r"\bhetze\w*\b|\bhetzen\b|\bgehetzt\b|\bhetzt\b",
                                                                      re.IGNORECASE)),
    ("propaganda",         re.compile(r"\bpropaganda\w*\b",          re.IGNORECASE)),
    ("bolschewismus",      re.compile(r"\bbolschewismus\w*\b|\bbolschewist\w*\b",
                                                                      re.IGNORECASE)),
    ("verleumdung",        re.compile(r"\bverleumdung\w*\b|\bverleumdet\w*\b|\bverleumden\b",
                                                                      re.IGNORECASE)),
    ("schmarotzer",        re.compile(r"\bschmarotzer\w*\b",         re.IGNORECASE)),
    ("vaterland",          re.compile(r"\bvaterland\w*\b",           re.IGNORECASE)),
    ("anzeige",            re.compile(r"\banzeige\w*\b",             re.IGNORECASE)),
]

YEAR_RE = re.compile(r"(192[0-9]|193[0-9])")


# ── Korpus laden ──────────────────────────────────────────────────────────────

def load_corpus() -> dict[int, list[tuple[str, str]]]:
    corpus: dict[int, list[tuple[str, str]]] = {y: [] for y in YEARS}
    for txt_file in sorted(CORPUS_DIR.rglob("*.txt")):
        parent = txt_file.parent.name
        m = YEAR_RE.fullmatch(parent)
        year = int(m.group(1)) if m else None
        if year is None:
            m2 = YEAR_RE.search(txt_file.name)
            year = int(m2.group(1)) if m2 else None
        if year not in corpus:
            continue
        text = txt_file.read_text(encoding="utf-8", errors="replace")
        corpus[year].append((txt_file.name, text))
    return corpus


# ── Zählung ───────────────────────────────────────────────────────────────────

def count_all(corpus: dict[int, list[tuple[str, str]]]) -> pd.DataFrame:
    records = []
    for label, pattern in TERMS:
        for year in YEARS:
            docs      = corpus[year]
            n_docs    = len(docs)
            abs_total = 0
            docs_hit  = 0
            for _, text in docs:
                matches = pattern.findall(text)
                abs_total += len(matches)
                if matches:
                    docs_hit += 1
            records.append({
                "term":       label,
                "year":       year,
                "abs":        abs_total,
                "docs_hit":   docs_hit,
                "docs_total": n_docs,
                "docs_fmt":   f"{docs_hit}/{n_docs}",
            })
    return pd.DataFrame(records)


# ── Pivot ins Professorenformat ───────────────────────────────────────────────

def pivot_to_professor(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, _ in TERMS:
        sub = df[df["term"] == label].set_index("year")
        row = {"Term": label}
        for y in YEARS:
            row[f"{y} (abs.)"] = int(sub.loc[y, "abs"])       if y in sub.index else 0
        for y in YEARS:
            row[f"Docs {y}"]   = sub.loc[y, "docs_fmt"]       if y in sub.index else "0/0"
        rows.append(row)
    return pd.DataFrame(rows)


# ── Markdown-Tabelle ──────────────────────────────────────────────────────────

def to_markdown(df: pd.DataFrame) -> str:
    cols = df.columns.tolist()
    lines = []
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("| " + " | ".join(
        ":---:" if "abs" in c or "Docs" in c else ":---"
        for c in cols
    ) + " |")
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join(lines)


# ── Hauptprogramm ─────────────────────────────────────────────────────────────

def main():
    print("Lade Rohtext-Korpus …")
    corpus = load_corpus()
    for y in YEARS:
        print(f"  {y}: {len(corpus[y])} Dateien")

    print("Zähle Treffer …")
    df_long = count_all(corpus)

    df_prof = pivot_to_professor(df_long)

    # ── Speichern ──
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df_prof.to_csv(OUT_CSV, index=False, encoding="utf-8")
    print(f"CSV gespeichert: {OUT_CSV}")

    md_content = (
        "# Regex-Frequenzanalyse – Professorenformat\n\n"
        "_Der Stadtwächter, Osnabrück (1929–1931)_  \n"
        "_Methode: Regex-Zählung im Rohtext, case-insensitive_\n\n"
        + to_markdown(df_prof) + "\n\n"
        "**Lesehinweis:** `Docs X/Y` = Term in X von Y Ausgaben des Jahrgangs nachgewiesen.\n"
        "Terme mit `*` erfassen alle Wortformen (z.B. antisemit → antisemitisch, Antisemitismus …).\n"
    )
    OUT_MD.write_text(md_content, encoding="utf-8")
    print(f"Markdown gespeichert: {OUT_MD}")

    # ── Konsole ──
    print()
    print("=" * 90)
    print(f"{'Term':<20} {'1929 (abs.)':>11} {'1930 (abs.)':>11} {'1931 (abs.)':>11}"
          f"  {'Docs 1929':>9} {'Docs 1930':>9} {'Docs 1931':>9}")
    print("-" * 90)
    for _, row in df_prof.iterrows():
        print(f"{row['Term']:<20} {row['1929 (abs.)']:>11} {row['1930 (abs.)']:>11}"
              f" {row['1931 (abs.)']:>11}  {row['Docs 1929']:>9} {row['Docs 1930']:>9}"
              f" {row['Docs 1931']:>9}")
    print("=" * 90)


if __name__ == "__main__":
    main()
