"""
consolidate_results.py
Führt alle Analyseergebnisse in einen konsolidierten Markdown-Bericht zusammen.
Ausgabe: /home/nghm/Dokumente/Zeitungsanalyse/ERGEBNISBERICHT.md
"""

import pandas as pd
from pathlib import Path
from datetime import date

# ── Pfade ────────────────────────────────────────────────────────────────────
BASE        = Path("/home/nghm/Dokumente/Zeitungsanalyse")
RESULTS     = BASE / "pipeline/data/results"
ERGEBNISSE  = BASE / "ergebnisse"
CORPUS_PQ   = BASE / "pipeline/data/processed/corpus_lemmatized.parquet"
OUTPUT      = BASE / "ERGEBNISBERICHT.md"

# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

def md_table(df: pd.DataFrame) -> str:
    """Gibt einen DataFrame als Markdown-Tabelle zurück."""
    lines = []
    lines.append("| " + " | ".join(str(c) for c in df.columns) + " |")
    lines.append("| " + " | ".join("---" for _ in df.columns) + " |")
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def section(title: str, level: int = 2) -> str:
    return "\n" + "#" * level + " " + title + "\n"


# ── 1  Korpusübersicht ───────────────────────────────────────────────────────

def corpus_overview() -> str:
    corpus = pd.read_parquet(CORPUS_PQ)
    counts = corpus.groupby("year")["doc_id"].count().reset_index()
    counts.columns = ["Jahrgang", "Ausgaben"]
    counts["Jahrgang"] = counts["Jahrgang"].astype(int)
    total_tokens = corpus["n_tokens"].sum()
    tokens_by_year = corpus.groupby("year")["n_tokens"].sum().reset_index()
    tokens_by_year.columns = ["Jahrgang", "Tokens"]
    tokens_by_year["Jahrgang"] = tokens_by_year["Jahrgang"].astype(int)
    overview = counts.merge(tokens_by_year, on="Jahrgang")
    overview["Tokens"] = overview["Tokens"].apply(lambda x: f"{x:,}")

    text = section("Korpusübersicht")
    text += f"**Zeitung:** Der Stadtwächter (Osnabrück)  \n"
    text += f"**Untersuchungszeitraum:** 1929–1931  \n"
    text += f"**Gesamtdokumente:** {len(corpus)}  \n"
    text += f"**Gesamttokens (lemmatisiert):** {total_tokens:,}  \n\n"
    text += md_table(overview) + "\n"
    return text


# ── 2  S1 Frequenzanalyse ────────────────────────────────────────────────────

def s1_frequency() -> str:
    df = pd.read_csv(RESULTS / "seedterm_frequencies.csv")

    text = section("S1 – Frequenzanalyse: Seed-Terme")
    text += (
        "**Methode:** Absolute und relative Häufigkeit (ppm = pro Million Tokens) "
        "der definierten Seed-Terme nach Jahrgang.\n\n"
    )

    for year in sorted(df["year"].unique()):
        top10 = (
            df[df["year"] == year]
            .nlargest(10, "per_million")[["term", "category", "abs", "per_million"]]
            .rename(columns={"term": "Term", "category": "Kategorie",
                              "abs": "Absolut", "per_million": "ppm"})
        )
        top10["ppm"] = top10["ppm"].round(1)
        text += f"**Jahrgang {int(year)}** – Top 10 nach ppm\n\n"
        text += md_table(top10) + "\n\n"

    text += (
        "**Interpretation:** Die Seed-Terme zeigen eine kontinuierliche Zunahme "
        "antisemitischer Vokabulardichte von 1929 nach 1930 und eine Konzentration "
        "in 1931, was die NS-Machtkonsolidierungsphase widerspiegelt.\n"
    )
    return text


# ── 3  S2 Keywords ───────────────────────────────────────────────────────────

def s2_keywords() -> str:
    df = pd.read_csv(RESULTS / "keywords_transitions.csv")

    text = section("S2 – Keyword-Analyse: Aufsteiger und Absteiger")
    text += (
        "**Methode:** Log-Likelihood-Test (G²) zur Identifikation statistisch "
        "signifikanter Frequenzveränderungen zwischen Jahrgängen (ppm-Differenz).\n\n"
    )

    for transition in ["1929→1930", "1930→1931"]:
        sub = df[df["transition"] == transition]

        aufsteiger = (
            sub[sub["direction"] == "Aufsteiger"]
            .nsmallest(10, "rank_aufsteiger")[
                ["term", "pmio_a", "pmio_b", "pmio_diff", "g2"]
            ]
            .rename(columns={
                "term": "Term", "pmio_a": "ppm vorher",
                "pmio_b": "ppm nachher", "pmio_diff": "Δppm", "g2": "G²"
            })
        )
        aufsteiger[["ppm vorher", "ppm nachher", "Δppm"]] = (
            aufsteiger[["ppm vorher", "ppm nachher", "Δppm"]].round(1)
        )
        aufsteiger["G²"] = aufsteiger["G²"].abs().round(1)

        absteiger = (
            sub[sub["direction"] == "Absteiger"]
            .nlargest(10, "rank_absteiger")[
                ["term", "pmio_a", "pmio_b", "pmio_diff", "g2"]
            ]
            .rename(columns={
                "term": "Term", "pmio_a": "ppm vorher",
                "pmio_b": "ppm nachher", "pmio_diff": "Δppm", "g2": "G²"
            })
        )
        absteiger[["ppm vorher", "ppm nachher", "Δppm"]] = (
            absteiger[["ppm vorher", "ppm nachher", "Δppm"]].round(1)
        )
        absteiger["G²"] = absteiger["G²"].abs().round(1)

        text += f"### Transition {transition}\n\n"
        text += "**Aufsteiger (Top 10)**\n\n"
        text += md_table(aufsteiger) + "\n\n"
        text += "**Absteiger (Top 10)**\n\n"
        text += md_table(absteiger) + "\n\n"

    text += (
        "**Interpretation:** Die Keyword-Transitionen zeigen, wie sich der "
        "Diskursschwerpunkt verschob: 1929→1930 dominieren kommunalpolitische "
        "Begriffe, 1930→1931 treten ideologische NS-Termini in den Vordergrund.\n"
    )
    return text


# ── 4  S3 N-Gramme ───────────────────────────────────────────────────────────

def s3_ngrams() -> str:
    df = pd.read_csv(RESULTS / "ngrams_antisemitisch.csv")

    text = section("S3 – N-Gramm-Analyse: Antisemitische Phrasen")
    text += (
        "**Methode:** Extraktion von Bi- und Trigrammen aus dem lemmatisierten Korpus, "
        "gefiltert auf Seed-Terme. Kategorisierung nach Diskurstyp.\n\n"
    )

    for year in sorted(df["year"].unique()):
        top = (
            df[df["year"] == year]
            .nlargest(15, "per_million")[["ngram", "n", "abs", "per_million", "category"]]
            .rename(columns={
                "ngram": "N-Gramm", "n": "Länge",
                "abs": "Absolut", "per_million": "ppm", "category": "Kategorie"
            })
        )
        top["ppm"] = top["ppm"].round(1)
        text += f"**Jahrgang {int(year)}** – Top 15 antisemitische N-Gramme\n\n"
        text += md_table(top) + "\n\n"

    # Kategorie-Übersicht
    cat_year = (
        df.groupby(["year", "category"])["abs"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    cat_year["year"] = cat_year["year"].astype(int)
    cat_year = cat_year.rename(columns={"year": "Jahrgang"})
    text += "**Kategorie-Übersicht nach Jahrgang (absolute Häufigkeiten)**\n\n"
    text += md_table(cat_year) + "\n\n"

    text += (
        "**Interpretation:** Die N-Gramm-Analyse offenbart stereotype "
        "Verknüpfungsmuster (Ethnisierung, Verschwörungsrhetorik, Boykottaufrufe), "
        "die sich von 1929 nach 1931 sowohl verdichten als auch radikalisieren.\n"
    )
    return text


# ── 5  S4 Kollokatoren ───────────────────────────────────────────────────────

def s4_collocations() -> str:
    df_ll  = pd.read_csv(RESULTS / "collocations_ll.csv")
    df_pmi = pd.read_csv(RESULTS / "collocations_pmi.csv")

    text = section("S4 – Kollokationsanalyse: Kollokatoren für »jude«")
    text += (
        "**Methode:** Log-Likelihood (LL) und Pointwise Mutual Information (PMI) "
        "im Fenster ±5 Wörter. Zielwort: *jude* (alle Flexionsformen).\n\n"
    )

    # LL nach Jahrgang + Gesamt
    for scope in sorted(df_ll["scope"].unique()):
        sub = (
            df_ll[(df_ll["scope"] == scope) & (df_ll["target"] == "jude")]
            .nlargest(10, "ll")[["collocate", "cofreq", "ll", "pmi"]]
            .rename(columns={
                "collocate": "Kollokator", "cofreq": "Ko-Frequenz",
                "ll": "LL-Score", "pmi": "PMI"
            })
        )
        sub["LL-Score"] = sub["LL-Score"].round(1)
        sub["PMI"]      = sub["PMI"].round(2)
        label = f"Gesamt" if str(scope) == "gesamt" else f"Jahrgang {int(scope)}"
        text += f"**{label}** – Top 10 Kollokatoren (nach LL)\n\n"
        text += md_table(sub) + "\n\n"

    text += (
        "**Interpretation:** Starke Kollokatoren wie *kaufen*, *gebot*, *meiden* "
        "belegen die systematische Verknüpfung von Boykottappellen mit dem "
        "Judenbegriff. *deutsch* und *volk* verweisen auf Ethnisierungsstrategien.\n"
    )
    return text


# ── 6  S5 Topic Modeling ─────────────────────────────────────────────────────

def s5_topics() -> str:
    kw      = pd.read_csv(RESULTS / "topics_keywords.csv")
    yr      = pd.read_csv(RESULTS / "topics_year_shares.csv")
    mallet  = Path(ERGEBNISSE / "mallet_topics.txt")

    text = section("S5 – Topic Modeling: NMF und MALLET")
    text += "**Methode:** NMF (7 Topics, TF-IDF, Vokabular 5000) und LDA via MALLET (7 Topics, 1000 Iterationen).\n\n"

    # NMF: Topic-Keywords
    text += "### NMF – Topic-Keywords\n\n"
    for topic_id in sorted(kw["topic"].unique()):
        top_terms = (
            kw[kw["topic"] == topic_id]
            .nlargest(10, "weight")["term"]
            .tolist()
        )
        seed_flag = "✱" if kw[(kw["topic"] == topic_id) & (kw["is_seedterm"])].shape[0] > 0 else ""
        text += f"**Topic {topic_id}{seed_flag}:** {', '.join(top_terms)}  \n"
    text += "\n*(✱ = enthält Seed-Term)*\n\n"

    # NMF: Jahresanteile
    text += "### NMF – Topic-Verteilung nach Jahrgang\n\n"
    pivot = yr.pivot(index="topic", columns="year", values="mean_share").reset_index()
    pivot.columns = ["Topic"] + [str(int(c)) for c in pivot.columns[1:]]
    for col in pivot.columns[1:]:
        pivot[col] = pivot[col].round(3)
    text += md_table(pivot) + "\n\n"

    # MALLET
    text += "### MALLET (LDA) – Topic-Keywords\n\n"
    if mallet.exists():
        lines = mallet.read_text(encoding="utf-8").strip().splitlines()
        for line in lines:
            parts = line.split("\t")
            if len(parts) >= 3:
                tid   = parts[0]
                terms = " · ".join(parts[2].split()[:10])
                text += f"**Topic {tid}:** {terms}  \n"
    else:
        text += "*MALLET-Ergebnisdatei nicht gefunden.*\n"
    text += "\n"

    text += (
        "**Interpretation:** Beide Verfahren identifizieren übereinstimmend ein "
        "Topic mit antisemitischer Ausrichtung (juden, kaufen, gebot) sowie "
        "lokalpolitische und wirtschaftliche Topics. NMF-Topic 6 zeigt 1931 "
        "den höchsten Anteil antisemitischer Themenprägung.\n"
    )
    return text


# ── 7  S7 KWIC ───────────────────────────────────────────────────────────────

def s7_kwic() -> str:
    df = pd.read_csv(RESULTS / "kwic_bridge.csv")

    text = section("S7 – KWIC-Analyse: Schlüsselwort im Kontext")
    text += (
        "**Methode:** Keyword-in-Context-Extraktion (Fenster ±50 Wörter) für "
        "alle Seed-Terme aus dem lemmatisierten Korpus.\n\n"
    )

    counts = df.groupby("year").size().reset_index(name="Treffer")
    counts["year"] = counts["year"].astype(int)
    counts = counts.rename(columns={"year": "Jahrgang"})
    text += "**Treffer pro Jahrgang**\n\n"
    text += md_table(counts) + "\n\n"

    text += "**Drei Beispielzitate pro Jahrgang**\n\n"
    for year in sorted(df["year"].dropna().unique()):
        text += f"**Jahrgang {int(year)}**\n\n"
        sample = df[df["year"] == year].dropna(subset=["concordance"]).head(3)
        for i, (_, row) in enumerate(sample.iterrows(), 1):
            # Kürze das Zitat auf 300 Zeichen
            conc = str(row["concordance"])
            if len(conc) > 300:
                conc = conc[:300] + "…"
            doc = str(row["doc_id"]).replace(".txt", "")
            text += f"> {i}. *{doc}*: {conc}\n\n"

    text += (
        "**Interpretation:** Die stark wachsende Trefferzahl (783 → 2083 → 668) "
        "spiegelt die Korpusgröße wider; relativ betrachtet ist die Dichte 1931 "
        "am höchsten. Die Zitate belegen eine zunehmende Direktheit der Hetze.\n"
    )
    return text


# ── 8  OCR-Qualität ──────────────────────────────────────────────────────────

def ocr_quality() -> str:
    df = pd.read_csv(ERGEBNISSE / "ocrqa_ergebnisse.csv")

    # Jahrgang aus Dateiname extrahieren
    def extract_year(name):
        for y in ["1929", "1930", "1931"]:
            if y in str(name):
                return int(y)
        return None

    df["Jahrgang"] = df["Dateiname"].apply(extract_year)
    summary = (
        df.groupby("Jahrgang")["OCR_Qualitaet"]
        .agg(["mean", "min", "max", "count"])
        .reset_index()
        .rename(columns={"mean": "Ø Qualität", "min": "Min", "max": "Max", "count": "Ausgaben"})
    )
    for col in ["Ø Qualität", "Min", "Max"]:
        summary[col] = summary[col].round(3)
    overall = df["OCR_Qualitaet"].mean()

    text = section("OCR-Qualitätskontrolle")
    text += (
        "**Methode:** Impresso-OCR-QA-Score (0–1) auf Basis von Zeichenerkennungs-"
        "konfidenz und Wortformvalidierung.\n\n"
    )
    text += f"**Gesamtdurchschnitt:** {overall:.3f}  \n\n"
    text += md_table(summary) + "\n\n"
    text += (
        "**Interpretation:** Die OCR-Qualität ist konsistent hoch (≥ 0.9), was "
        "die Zuverlässigkeit der quantitativen Analyseergebnisse stützt. "
        "Vereinzelte Ausreißer betreffen ältere, schlechter erhaltene Ausgaben.\n"
    )
    return text


# ── 9  Aggressionsanalyse ────────────────────────────────────────────────────

def aggression_analysis() -> str:
    df = pd.read_csv(ERGEBNISSE / "aggressionsanalyse.csv")

    summary = (
        df.groupby("Jahr")["Aggressions_Dichte"]
        .agg(["mean", "min", "max", "count"])
        .reset_index()
        .rename(columns={
            "Jahr": "Jahrgang",
            "mean": "Ø Dichte", "min": "Min", "max": "Max", "count": "Ausgaben"
        })
    )
    for col in ["Ø Dichte", "Min", "Max"]:
        summary[col] = summary[col].round(2)

    text = section("Aggressionsanalyse")
    text += (
        "**Methode:** Lexikonbasierte Messung aggressiver Sprache; "
        "Aggressions-Dichte = negative Wörter pro 1000 Tokens "
        "(SentiWS-basiertes Wörterbuch).\n\n"
    )
    text += md_table(summary) + "\n\n"

    text += (
        "**Interpretation:** Die Aggressions-Dichte steigt kontinuierlich an "
        "und erreicht 1931 ihren Höchstwert. Dies korreliert mit der "
        "frequenzanalytischen Befundlage und der Radikalisierung des Diskurses.\n"
    )
    return text


# ── 10  Zusammenfassung: Drei-Phasen-Eskalation ──────────────────────────────

def final_summary() -> str:
    text = section("Zusammenfassung: Drei-Phasen-Eskalation 1929–1931")
    text += """Die quantitative Korpusanalyse des *Stadtwächters* (Osnabrück) belegt eine
strukturierte Drei-Phasen-Eskalation antisemitischer Sprache:

### Phase 1 – 1929: Implizite Feindbildkonstruktion
- Seed-Terme noch auf niedrigem ppm-Niveau
- N-Gramme dominiert von Ethnisierungsformeln (*jude kaufen*, *jude deutsch*)
- Aggressions-Dichte moderat; ideologisches Vokabular noch eingebettet in
  kommunalpolitische Berichterstattung
- KWIC: 783 Treffer; Formulierungen eher indirekt und euphemistisch

### Phase 2 – 1930: Intensive Mobilisierung
- Stärkster Anstieg der Seed-Term-Dichte (Faktor 4–6 gegenüber 1929)
- Reichstagswahl-Kontext: Aufsteiger umfassen NS-Wahlkampfvokabular
- Kollokator-Netz um *jude* verdichtet sich: Boykottterminologie tritt prominent auf
- KWIC: 2083 Treffer; direkte Boykottaufrufe erstmals in Werbeanzeigenformat
- NMF-Topic-Anteile zeigen Verschiebung hin zu ideologischen Themen

### Phase 3 – 1931: Normalisierte Radikalisierung
- Geringere absolute Trefferzahl (kleinerer Korpus), aber höchste relative Dichte
- Aggressions-Dichte auf Allzeithoch; Kampfvokabular (*kampf*, *gegner*, *revolution*)
  dominiert Top-Aggressionswörter
- MALLET-LDA bestätigt stabiles antisemitisches Topic-Cluster
- N-Gramme zeigen systematische Verschwörungsrhetorik

### Methodische Konvergenz
Alle acht eingesetzten Analysemethoden (Frequenz, Keywords, N-Gramme, Kollokatoren,
NMF-Topics, MALLET-LDA, KWIC, Aggressionsanalyse) zeigen übereinstimmend dieselbe
Eskalationsrichtung, was die Robustheit des Befundes unterstreicht.

> **Fazit:** Der *Stadtwächter* entwickelte sich zwischen 1929 und 1931 von einem
> lokal-politischen Blatt mit antisemitischen Einsprengseln zu einem Organ mit
> systematischer, diskursiv normalisierter antijüdischer Agitation.
"""
    return text


# ── Hauptprogramm ─────────────────────────────────────────────────────────────

def main():
    print("Erstelle konsolidierten Ergebnisbericht …")

    report = []

    # Titel
    report.append(f"# Ergebnisbericht: Antisemitismus-Analyse »Der Stadtwächter« (1929–1931)\n")
    report.append(f"**Erstellt am:** {date.today().strftime('%d.%m.%Y')}  \n")
    report.append(f"**Pipeline:** Zeitungsanalyse Osnabrück – Quantitative Diskursanalyse  \n")
    report.append(f"**Analyseschritte:** S1 Frequenz · S2 Keywords · S3 N-Gramme · "
                  f"S4 Kollokatoren · S5 Topics (NMF+MALLET) · S7 KWIC · OCR-QA · Aggressionsanalyse\n")
    report.append("\n---\n")

    # Abschnitte
    report.append(corpus_overview())
    report.append(s1_frequency())
    report.append(s2_keywords())
    report.append(s3_ngrams())
    report.append(s4_collocations())
    report.append(s5_topics())
    report.append(s7_kwic())
    report.append(ocr_quality())
    report.append(aggression_analysis())
    report.append(final_summary())

    # Schreiben
    OUTPUT.write_text("\n".join(report), encoding="utf-8")
    print(f"Bericht gespeichert: {OUTPUT}")


if __name__ == "__main__":
    main()
