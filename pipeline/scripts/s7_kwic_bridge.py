"""
s7_kwic_bridge.py – Keyword-in-Context für qualitative Anschlussanalyse

Liest die Rohtexte aus CORPUS_DIR sowie corpus_lemmatized.parquet.
Generiert für die Zielwörter jude, jüdisch, judentum alle KWIC-Treffer
mit einem Kontextfenster von ±30 Wörtern (Rohtext-Tokens, nicht Lemmata,
damit der Originalwortlaut erhalten bleibt).

Ausgabedateien:
    results/kwic_bridge.xlsx   – Excel mit einem Sheet pro Zielwort
    results/kwic_bridge.csv    – alle Treffer als flache CSV
"""

import sys
import logging
import re
from pathlib import Path

# Nutzer-Site-Packages explizit aufnehmen (nötig wenn user-install nicht im Pfad)
import site
sys.path.extend(site.getusersitepackages() if isinstance(site.getusersitepackages(), list)
                else [site.getusersitepackages()])

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
log = logging.getLogger("s7_kwic_bridge")

# Zielwörter (Suche auf Rohtext – alle Flexionsformen per Regex)
# Patterns matchen Groß-/Kleinschreibung und Wortgrenzen
TARGET_PATTERNS: dict[str, re.Pattern] = {
    "jude":     re.compile(r"\bjuden?\b",             re.IGNORECASE),
    "jüdisch":  re.compile(r"\bjüdisch\w*\b",         re.IGNORECASE),
    "judentum": re.compile(r"\bjudentum\b",            re.IGNORECASE),
}

WINDOW = config.KWIC_WINDOW * 3   # 10 * 3 = 30 Rohtext-Wörter links/rechts

# Tokenisierung des Rohtexts: Wörter inkl. Satzzeichen als eigene Tokens
_WORD_RE = re.compile(r"\S+")


def raw_tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text)


def kwic_from_text(
    tokens: list[str],
    pattern: re.Pattern,
    window: int,
) -> list[dict]:
    """Alle Treffer des Patterns im Token-Array mit Kontext."""
    hits = []
    for i, tok in enumerate(tokens):
        if pattern.search(tok):
            left  = tokens[max(0, i - window): i]
            right = tokens[i + 1: i + window + 1]
            hits.append({
                "keyword":    tok,
                "left":       " ".join(left),
                "right":      " ".join(right),
                "concordance": " ".join(left) + "  [" + tok + "]  " + " ".join(right),
                "pos":        i,
            })
    return hits


# =============================================================================
# Hauptverarbeitung
# =============================================================================
def main():
    log.info("=== s7_kwic_bridge gestartet ===")

    # Parquet für Metadaten (doc_id → year)
    parquet_path = config.PROCESSED_DIR / "corpus_lemmatized.parquet"
    if not parquet_path.exists():
        log.error("Parquet nicht gefunden: %s", parquet_path)
        sys.exit(1)
    meta = pd.read_parquet(parquet_path, columns=["doc_id", "year"])
    year_map = dict(zip(meta["doc_id"], meta["year"]))

    # Rohtexte einlesen
    txt_files = sorted(config.CORPUS_DIR.glob("*.txt"))
    if not txt_files:
        log.error("Keine .txt-Dateien in %s", config.CORPUS_DIR)
        sys.exit(1)
    log.info("%d Rohtextdateien gefunden", len(txt_files))

    all_records: list[dict] = []

    for txt_file in txt_files:
        doc_id = txt_file.stem
        year   = year_map.get(doc_id)
        text   = txt_file.read_text(encoding="utf-8", errors="replace")
        tokens = raw_tokenize(text)

        for target_key, pattern in TARGET_PATTERNS.items():
            hits = kwic_from_text(tokens, pattern, WINDOW)
            for hit in hits:
                all_records.append({
                    "target":      target_key,
                    "year":        year,
                    "doc_id":      doc_id,
                    "keyword":     hit["keyword"],
                    "left":        hit["left"],
                    "right":       hit["right"],
                    "concordance": hit["concordance"],
                    "pos_in_doc":  hit["pos"],
                })

    df_all = pd.DataFrame(all_records)
    log.info("Gesamt %d KWIC-Treffer", len(df_all))

    # ---------------------------------------------------------------- CSV
    out_csv = config.RESULTS_DIR / "kwic_bridge.csv"
    df_all.to_csv(out_csv, index=False, encoding="utf-8")
    log.info("Gespeichert: %s", out_csv)

    # --------------------------------------------------------------- Excel
    out_xlsx = config.RESULTS_DIR / "kwic_bridge.xlsx"
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        # Sheet 1: Übersicht alle Treffer, sortiert nach Jahr
        df_all.sort_values(["year", "target", "doc_id", "pos_in_doc"]).to_excel(
            writer, sheet_name="Alle Treffer", index=False
        )
        # Sheets 2–4: je Zielwort
        for target_key in TARGET_PATTERNS:
            sub = (
                df_all[df_all["target"] == target_key]
                .sort_values(["year", "doc_id", "pos_in_doc"])
            )
            sheet_name = target_key[:31]  # Excel-Limit: 31 Zeichen
            sub.to_excel(writer, sheet_name=sheet_name, index=False)
        # Sheet 5: Statistik
        stats = (
            df_all.groupby(["target", "year"])
            .size()
            .reset_index(name="n_hits")
            .pivot_table(index="target", columns="year", values="n_hits", fill_value=0)
        )
        stats.to_excel(writer, sheet_name="Statistik")
    log.info("Gespeichert: %s", out_xlsx)

    # ==========================================================================
    # Zusammenfassung
    # ==========================================================================
    print("\n" + "=" * 65)
    print("ZUSAMMENFASSUNG  –  s7_kwic_bridge  (Fenster ±%d Wörter)" % WINDOW)
    print("=" * 65)
    print(f"  Gesamt-Treffer: {len(df_all):,}")
    print()

    pivot = (
        df_all.groupby(["target", "year"])
        .size()
        .reset_index(name="n")
        .pivot_table(index="target", columns="year", values="n", fill_value=0)
    )
    print(f"  {'Zielwort':<14}", end="")
    for y in config.TIME_SLICES:
        print(f"  {y:>6}", end="")
    print(f"  {'Gesamt':>8}")
    print(f"  {'-'*14}", end="")
    for _ in config.TIME_SLICES:
        print(f"  {'-'*6}", end="")
    print(f"  {'-'*8}")

    for target_key in TARGET_PATTERNS:
        row = pivot.loc[target_key] if target_key in pivot.index else {}
        print(f"  {target_key:<14}", end="")
        total = 0
        for y in config.TIME_SLICES:
            n = int(row.get(y, 0))
            total += n
            print(f"  {n:>6}", end="")
        print(f"  {total:>8}")

    # Je Zielwort: 5 Beispielkontexte aus dem Jahr mit den meisten Treffern
    for target_key in TARGET_PATTERNS:
        sub = df_all[df_all["target"] == target_key]
        if sub.empty:
            continue
        peak_year = sub.groupby("year").size().idxmax()
        examples  = sub[sub["year"] == peak_year].head(5)
        print(f"\n  5 Beispielkontexte '{target_key}' (Jahrgang {peak_year}):")
        print(f"  {'─'*63}")
        for _, r in examples.iterrows():
            conc = r["concordance"]
            # Kürzen auf ~120 Zeichen für Lesbarkeit
            if len(conc) > 120:
                # Keyword-Position finden und zentriert kürzen
                kw_start = conc.find("[")
                start = max(0, kw_start - 55)
                conc = ("…" if start > 0 else "") + conc[start:start+120] + "…"
            print(f"  {r['doc_id'][:30]:<30}  {conc}")

    print(f"\n  Ausgabedateien:")
    for p in [out_csv, out_xlsx]:
        print(f"    {p}")
    print("=" * 65)
    log.info("=== s7_kwic_bridge abgeschlossen ===")


if __name__ == "__main__":
    main()
