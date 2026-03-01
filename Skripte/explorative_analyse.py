#!/usr/bin/env python3
"""
Explorative Textanalyse (Unsupervised Text Mining)
====================================================
Analysiert alle .txt-Dateien im Ordner daten_txt (inkl. Unterordner)
ohne vorher Suchbegriffe festzulegen. Ziel: dominante Themen und
relevanteste Wörter des Korpus entdecken.

Methoden:
  - Wortfrequenzanalyse (globale Häufigkeiten)
  - TF-IDF (dokumentenspezifische Leitwörter)
  - Bigramm-Kollokationen (häufige Wortpaare)
  - LDA Topic Modeling (latente Themenstruktur)

Ausgabe: Ordner ergebnisse/explorative_analyse/
"""

import os
import re
import sys
import json
import warnings
from pathlib import Path
from collections import Counter

import nltk
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
from wordcloud import WordCloud
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from nltk.corpus import stopwords

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# Pfade
# ─────────────────────────────────────────────
BASIS_DIR = Path(__file__).resolve().parent.parent
DATEN_DIR = BASIS_DIR / "daten_txt"
ERGEBNIS_DIR = BASIS_DIR / "ergebnisse" / "explorative_analyse"
ERGEBNIS_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────
# Parameter
# ─────────────────────────────────────────────
MIN_WORTLAENGE = 3       # Kürzere Tokens rausfiltern (OCR-Müll)
MAX_WORTLAENGE = 30      # Zu lange Tokens rausfiltern
N_TOPICS = 8             # Anzahl LDA-Themen
N_TOP_WORDS = 20         # Top-Wörter pro Thema / Visualisierung
N_FREQ_WORDS = 40        # Wörter im Frequenzdiagramm
N_BIGRAMS = 30           # Anzahl Bigramme im Bericht
LDA_ITERATIONEN = 300    # Max. LDA-Iterationen
ZUFALLSSTART = 42

# ─────────────────────────────────────────────
# Stoppwörter (Deutsch + erweiterter Satz)
# ─────────────────────────────────────────────
try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords", quiet=True)

STOPWOERTER_BASIS = set(stopwords.words("german"))

STOPWOERTER_EXTRA = {
    # häufige Zeitungswörter ohne inhaltlichen Wert
    "daß", "dass", "aber", "auch", "noch", "schon", "immer", "sehr",
    "mehr", "wenn", "dann", "denn", "sein", "hat", "wird", "wurde",
    "haben", "hatte", "waren", "wäre", "kann", "muß", "muss", "soll",
    "wird", "worden", "wir", "sie", "ihr", "ihm", "ihn", "uns", "ihre",
    "ihren", "ihrem", "seine", "seinen", "seiner", "seinem", "jetzt",
    "hier", "dort", "wohl", "erst", "nur", "eben", "so", "wie",
    "alle", "allem", "allen", "alles", "beim", "zur", "zum", "durch",
    "nach", "vor", "über", "unter", "gegen", "aus", "bei", "mit",
    "von", "an", "auf", "in", "im", "ist", "die", "der", "das",
    "des", "den", "dem", "ein", "eine", "einer", "einem", "einen",
    "nicht", "und", "oder", "als", "für", "zu", "es", "sich",
    "man", "was", "war", "are", "the", "and", "that", "this",
    "ja", "nein", "nun", "mal", "wer", "wo", "gar", "doch", "weil",
    "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn",
    "ver", "ter", "noc", "fie", "tion",
    # OCR-Artefakte der Frakturschrift (b statt d, f statt s, u statt n usw.)
    "ber", "bie", "ben", "bet", "bas", "bes", "bte", "bem", "bec",
    "unb", "umb", "uub", "sinb", "wirb", "wirft",
    "ift", "iit", "lll", "iii", "ooo", "eee",
    "fei", "fein", "feiner", "feinen", "seinem", "feines",
    "fich", "fich", "foll", "fann", "fehr", "fchon", "fowie",
    "aud", "noch", "nod", "boch", "doch", "auch",
    "hab", "habe", "hast", "hat", "habe", "habt",
    "gar", "gab", "gibt", "gab", "ganz", "gang",
    "red", "eid", "eis", "lag", "ies",
}

ALLE_STOPWOERTER = STOPWOERTER_BASIS | STOPWOERTER_EXTRA


# ─────────────────────────────────────────────
# Hilfsfunktionen
# ─────────────────────────────────────────────

def normalisiere_altdeutsch(text: str) -> str:
    """Ersetzt historische Schreibweisen und OCR-Sonderzeichen."""
    # Langes s (ſ) → s
    text = text.replace("ſ", "s")
    # Doppel-s-Varianten
    text = text.replace("ß", "ss").replace("ẞ", "SS")
    # Ligaturen und veraltete Zeichen
    text = text.replace("ae", "ä").replace("oe", "ö").replace("ue", "ü")
    # Häufige OCR-Verwechslungen: 1 → l, 0 → o (nur in Wortkontexten)
    text = re.sub(r"(?<=[a-zA-ZäöüÄÖÜ])1(?=[a-zA-ZäöüÄÖÜ])", "l", text)
    return text


def bereinige_text(text: str) -> str:
    """Grundlegende Textnormalisierung."""
    text = normalisiere_altdeutsch(text)
    # Alles außer Buchstaben und Leerzeichen entfernen
    text = re.sub(r"[^a-zA-ZäöüÄÖÜ\s]", " ", text)
    # Mehrfache Leerzeichen zusammenfassen
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenisiere(text: str) -> list[str]:
    """Tokenisiert und filtert Tokens nach Länge und Stoppwörtern."""
    text = bereinige_text(text.lower())
    tokens = text.split()
    tokens = [
        t for t in tokens
        if MIN_WORTLAENGE <= len(t) <= MAX_WORTLAENGE
        and t not in ALLE_STOPWOERTER
        and not re.match(r"^[^aeiouyäöü]+$", t)  # Nur-Konsonanten-Sequenzen (OCR-Müll)
    ]
    return tokens


def lade_txt_dateien(verzeichnis: Path) -> tuple[list[str], list[str], list[str]]:
    """Lädt alle .txt-Dateien rekursiv. Gibt Texte, Dateinamen, Gruppen zurück."""
    texte, namen, gruppen = [], [], []
    for pfad in sorted(verzeichnis.rglob("*.txt")):
        try:
            text = pfad.read_text(encoding="utf-8", errors="replace")
            if len(text.strip()) < 50:
                continue
            texte.append(text)
            namen.append(pfad.name)
            gruppen.append(pfad.parent.name)
        except Exception as e:
            print(f"  [Fehler] {pfad.name}: {e}")
    return texte, namen, gruppen


# ─────────────────────────────────────────────
# Analysefunktionen
# ─────────────────────────────────────────────

def analysiere_wortfrequenz(alle_tokens: list[str]) -> Counter:
    """Globale Worthäufigkeiten im gesamten Korpus."""
    return Counter(alle_tokens)


def erstelle_tfidf(texte_bereinigt: list[str], namen: list[str]) -> pd.DataFrame:
    """
    Berechnet TF-IDF und gibt DataFrame mit Top-Termen pro Dokument zurück.
    TF-IDF hebt Wörter hervor, die in einem Dokument besonders charakteristisch
    sind (häufig dort, aber selten im Rest des Korpus).
    """
    vektorisierer = TfidfVectorizer(
        min_df=2,
        max_df=0.85,
        max_features=5000,
        ngram_range=(1, 1),
    )
    matrix = vektorisierer.fit_transform(texte_bereinigt)
    begriffe = vektorisierer.get_feature_names_out()
    df = pd.DataFrame(matrix.toarray(), index=namen, columns=begriffe)
    return df, vektorisierer, matrix


def lda_topic_modeling(
    texte_bereinigt: list[str],
    n_topics: int = N_TOPICS,
) -> tuple:
    """LDA: Findet latente Themenstrukturen ohne Vorgabe von Suchbegriffen."""
    vektorisierer = CountVectorizer(
        min_df=3,
        max_df=0.80,
        max_features=4000,
        ngram_range=(1, 1),
    )
    dtm = vektorisierer.fit_transform(texte_bereinigt)
    begriffe = vektorisierer.get_feature_names_out()

    lda = LatentDirichletAllocation(
        n_components=n_topics,
        max_iter=LDA_ITERATIONEN,
        learning_method="online",
        learning_offset=50.0,
        random_state=ZUFALLSSTART,
        n_jobs=-1,
    )
    lda.fit(dtm)
    thema_verteilung = lda.transform(dtm)
    return lda, vektorisierer, begriffe, dtm, thema_verteilung


def extrahiere_bigramme(alle_tokens: list[str], n: int = N_BIGRAMS) -> list[tuple]:
    """Findet die häufigsten Bigramme (Zweiwortkombinationen)."""
    bigramme = [
        (alle_tokens[i], alle_tokens[i + 1])
        for i in range(len(alle_tokens) - 1)
    ]
    return Counter(bigramme).most_common(n)


# ─────────────────────────────────────────────
# Visualisierungen
# ─────────────────────────────────────────────

def speichere_wordcloud(wortfrequenz: Counter, pfad: Path) -> None:
    """Erzeugt eine Wordcloud aus den Häufigkeiten."""
    wc = WordCloud(
        width=1400,
        height=800,
        background_color="white",
        colormap="viridis",
        max_words=150,
        collocations=False,
        prefer_horizontal=0.8,
    ).generate_from_frequencies(dict(wortfrequenz.most_common(200)))
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title("Wordcloud – häufigste Wörter im Korpus", fontsize=16, pad=12)
    fig.tight_layout()
    fig.savefig(pfad, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → Wordcloud gespeichert: {pfad.name}")


def speichere_frequenzbalken(wortfrequenz: Counter, pfad: Path, n: int = N_FREQ_WORDS) -> None:
    """Balkendiagramm der häufigsten Wörter."""
    top = wortfrequenz.most_common(n)
    woerter, haeufigkeiten = zip(*top)

    palette = sns.color_palette("Blues_r", n)
    fig, ax = plt.subplots(figsize=(14, 7))
    bars = ax.barh(range(n), haeufigkeiten, color=palette)
    ax.set_yticks(range(n))
    ax.set_yticklabels(woerter, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("Absolute Häufigkeit", fontsize=11)
    ax.set_title(f"Top {n} häufigste Wörter im Gesamtkorpus", fontsize=14, pad=10)
    for bar, h in zip(bars, haeufigkeiten):
        ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height() / 2,
                str(h), va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(pfad, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → Frequenzbalken gespeichert: {pfad.name}")


def speichere_lda_visualisierung(lda, begriffe, thema_verteilung, namen, pfad_themen, pfad_heatmap) -> None:
    """Zwei Grafiken: (1) Top-Wörter pro Thema, (2) Themenverteilung über Dokumente."""
    n_topics = lda.n_components

    # ── Grafik 1: Top-Wörter pro Thema ──
    fig, axes = plt.subplots(
        nrows=(n_topics + 1) // 2, ncols=2,
        figsize=(16, n_topics * 1.8),
        constrained_layout=True,
    )
    axes = axes.flatten()
    farben = plt.cm.tab10.colors

    for idx, (thema, ax) in enumerate(zip(lda.components_, axes)):
        top_idx = thema.argsort()[: -N_TOP_WORDS - 1 : -1]
        top_woerter = [begriffe[i] for i in top_idx]
        top_gewichte = [thema[i] for i in top_idx]
        ax.barh(range(N_TOP_WORDS), top_gewichte[::-1], color=farben[idx % 10])
        ax.set_yticks(range(N_TOP_WORDS))
        ax.set_yticklabels(top_woerter[::-1], fontsize=9)
        ax.set_title(f"Thema {idx + 1}", fontsize=12, fontweight="bold")
        ax.set_xlabel("Gewicht", fontsize=9)

    # Leere Subplots ausblenden
    for ax in axes[n_topics:]:
        ax.set_visible(False)

    fig.suptitle("LDA Topic Modeling – Top-Wörter pro Thema", fontsize=15, y=1.01)
    fig.savefig(pfad_themen, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → LDA-Themen gespeichert: {pfad_themen.name}")

    # ── Grafik 2: Heatmap Themenverteilung ──
    df_heat = pd.DataFrame(
        thema_verteilung,
        index=[n[:30] for n in namen],
        columns=[f"T{i+1}" for i in range(n_topics)],
    )
    # Nur die 40 Dokumente mit der stärksten Themenausprägung zeigen
    df_heat = df_heat.loc[df_heat.max(axis=1).nlargest(min(40, len(df_heat))).index]

    fig, ax = plt.subplots(figsize=(12, max(8, len(df_heat) * 0.35)))
    sns.heatmap(
        df_heat,
        cmap="YlOrRd",
        linewidths=0.3,
        ax=ax,
        cbar_kws={"label": "Themenanteil"},
        annot=False,
    )
    ax.set_title("Themenverteilung pro Dokument (Heatmap)", fontsize=13)
    ax.set_xlabel("Thema")
    ax.set_ylabel("Dokument")
    ax.tick_params(axis="y", labelsize=7)
    fig.tight_layout()
    fig.savefig(pfad_heatmap, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → LDA-Heatmap gespeichert: {pfad_heatmap.name}")


def speichere_tfidf_visualisierung(tfidf_df: pd.DataFrame, gruppen: list[str], pfad: Path) -> None:
    """Zeigt die wichtigsten TF-IDF-Terme pro Dokumentengruppe (Unterordner)."""
    tfidf_df = tfidf_df.copy()
    tfidf_df["gruppe"] = gruppen

    gruppen_mittel = tfidf_df.groupby("gruppe").mean(numeric_only=True)
    n_gruppen = len(gruppen_mittel)
    if n_gruppen < 2:
        return  # Keine sinnvolle Darstellung bei einer einzigen Gruppe

    fig, axes = plt.subplots(1, n_gruppen, figsize=(6 * n_gruppen, 8), sharey=False)
    if n_gruppen == 1:
        axes = [axes]
    farben = plt.cm.Set2.colors

    for ax, (gruppe, row), farbe in zip(axes, gruppen_mittel.iterrows(), farben):
        top = row.nlargest(15)
        ax.barh(range(len(top)), top.values[::-1], color=farbe)
        ax.set_yticks(range(len(top)))
        ax.set_yticklabels(top.index[::-1], fontsize=9)
        ax.set_title(gruppe[:35], fontsize=10, fontweight="bold")
        ax.set_xlabel("Ø TF-IDF")

    fig.suptitle("TF-IDF-Leitwörter pro Dokumentengruppe (Unterordner)", fontsize=13)
    fig.tight_layout()
    fig.savefig(pfad, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → TF-IDF-Gruppen gespeichert: {pfad.name}")


# ─────────────────────────────────────────────
# Textbericht
# ─────────────────────────────────────────────

def erstelle_bericht(
    namen, gruppen, wortfrequenz, bigramme,
    lda, begriffe, thema_verteilung, tfidf_df,
) -> str:
    """Schreibt einen menschenlesbaren Analysebericht."""
    n_docs = len(namen)
    n_tokens_gesamt = sum(wortfrequenz.values())
    n_woerter_einzigartig = len(wortfrequenz)
    n_topics = lda.n_components

    zeilen = [
        "=" * 70,
        "EXPLORATIVE TEXTANALYSE – BERICHT",
        "=" * 70,
        "",
        "── KORPUSÜBERSICHT ─────────────────────────────────────────────────",
        f"  Dokumente analysiert    : {n_docs}",
        f"  Token (bereinigt)       : {n_tokens_gesamt:,}",
        f"  Einzigartige Wörter     : {n_woerter_einzigartig:,}",
        f"  Durchschnittliche TTR   : {n_woerter_einzigartig / n_tokens_gesamt:.4f}",
        f"  Unterordner (Gruppen)   : {sorted(set(gruppen))}",
        "",
        "── TOP 50 HÄUFIGSTE WÖRTER ─────────────────────────────────────────",
    ]
    for rang, (wort, h) in enumerate(wortfrequenz.most_common(50), 1):
        zeilen.append(f"  {rang:3}. {wort:<25} {h:>6}×")

    zeilen += [
        "",
        "── HÄUFIGSTE BIGRAMME (Wortpaare) ──────────────────────────────────",
    ]
    for (w1, w2), h in bigramme:
        zeilen.append(f"  {w1} {w2:<40} {h:>5}×")

    zeilen += [
        "",
        "── LDA THEMEN (unsupervised) ────────────────────────────────────────",
        f"  Anzahl Themen: {n_topics}",
        "",
    ]
    for idx, thema in enumerate(lda.components_):
        top_idx = thema.argsort()[: -N_TOP_WORDS - 1 : -1]
        top_woerter = [begriffe[i] for i in top_idx]
        zeilen.append(f"  Thema {idx + 1:2}: {' | '.join(top_woerter)}")

    zeilen += [
        "",
        "── DOMINANTES THEMA PRO DOKUMENT ────────────────────────────────────",
    ]
    for i, (name, verteilung) in enumerate(zip(namen, thema_verteilung)):
        dom_thema = int(np.argmax(verteilung)) + 1
        dom_anteil = verteilung.max()
        zeilen.append(f"  {name[:45]:<45} → Thema {dom_thema} ({dom_anteil:.2f})")

    zeilen += [
        "",
        "── TF-IDF: WICHTIGSTE TERME PRO GRUPPE ─────────────────────────────",
    ]
    tfidf_kopie = tfidf_df.copy()
    tfidf_kopie["gruppe"] = gruppen
    for gruppe, gdf in tfidf_kopie.groupby("gruppe"):
        mittel = gdf.drop(columns="gruppe").mean()
        top5 = mittel.nlargest(10).index.tolist()
        zeilen.append(f"  {gruppe}: {', '.join(top5)}")

    zeilen += ["", "=" * 70]
    return "\n".join(zeilen)


# ─────────────────────────────────────────────
# Hauptprogramm
# ─────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  Explorative Textanalyse – Zeitungskorpus")
    print("=" * 60)

    # 1. Texte laden
    print(f"\n[1/6] Lade .txt-Dateien aus: {DATEN_DIR}")
    texte_roh, namen, gruppen = lade_txt_dateien(DATEN_DIR)
    if not texte_roh:
        sys.exit("Keine .txt-Dateien gefunden. Bitte Pfad prüfen.")
    print(f"      {len(texte_roh)} Dokumente geladen.")

    # 2. Preprocessing
    print("\n[2/6] Bereinige und tokenisiere Texte …")
    alle_tokens = []
    texte_bereinigt = []  # Token-String pro Dokument für sklearn
    for text in texte_roh:
        tokens = tokenisiere(text)
        alle_tokens.extend(tokens)
        texte_bereinigt.append(" ".join(tokens))
    print(f"      {len(alle_tokens):,} bereinigte Token.")

    # 3. Wortfrequenz
    print("\n[3/6] Wortfrequenzanalyse …")
    wortfrequenz = analysiere_wortfrequenz(alle_tokens)
    bigramme = extrahiere_bigramme(alle_tokens, N_BIGRAMS)

    # 4. TF-IDF
    print("\n[4/6] TF-IDF-Berechnung …")
    tfidf_df, tfidf_vek, tfidf_mat = erstelle_tfidf(texte_bereinigt, namen)

    # 5. LDA
    print("\n[5/6] LDA Topic Modeling …")
    lda, lda_vek, lda_begriffe, dtm, thema_verteilung = lda_topic_modeling(
        texte_bereinigt, N_TOPICS
    )

    # 6. Ausgabe
    print(f"\n[6/6] Speichere Ergebnisse in: {ERGEBNIS_DIR}")

    speichere_wordcloud(wortfrequenz, ERGEBNIS_DIR / "wordcloud.png")
    speichere_frequenzbalken(wortfrequenz, ERGEBNIS_DIR / "wortfrequenz_top40.png")
    speichere_lda_visualisierung(
        lda, lda_begriffe, thema_verteilung, namen,
        ERGEBNIS_DIR / "lda_themen_top_woerter.png",
        ERGEBNIS_DIR / "lda_themenverteilung_heatmap.png",
    )
    speichere_tfidf_visualisierung(tfidf_df, gruppen, ERGEBNIS_DIR / "tfidf_nach_gruppe.png")

    # CSV: Wortfrequenzen
    freq_df = pd.DataFrame(wortfrequenz.most_common(), columns=["Wort", "Häufigkeit"])
    freq_df.to_csv(ERGEBNIS_DIR / "wortfrequenzen.csv", index=False, encoding="utf-8-sig")
    print(f"  → Wortfrequenzen (CSV): wortfrequenzen.csv")

    # CSV: Bigramme
    bgr_df = pd.DataFrame([(w1, w2, h) for (w1, w2), h in bigramme], columns=["Wort1", "Wort2", "Häufigkeit"])
    bgr_df.to_csv(ERGEBNIS_DIR / "bigramme.csv", index=False, encoding="utf-8-sig")
    print(f"  → Bigramme (CSV): bigramme.csv")

    # CSV: Dominant-Thema je Dokument
    dom_df = pd.DataFrame({
        "Dokument": namen,
        "Gruppe": gruppen,
        "Dominantes_Thema": np.argmax(thema_verteilung, axis=1) + 1,
        "Themenanteil": np.max(thema_verteilung, axis=1),
    })
    for i in range(N_TOPICS):
        dom_df[f"Thema_{i+1}"] = thema_verteilung[:, i]
    dom_df.to_csv(ERGEBNIS_DIR / "dokument_themen.csv", index=False, encoding="utf-8-sig")
    print(f"  → Dokument-Themen (CSV): dokument_themen.csv")

    # JSON: LDA-Themen (maschinenlesbar)
    themen_json = {}
    for idx, thema in enumerate(lda.components_):
        top_idx = thema.argsort()[: -N_TOP_WORDS - 1 : -1]
        themen_json[f"Thema_{idx+1}"] = [
            {"wort": lda_begriffe[i], "gewicht": float(thema[i])}
            for i in top_idx
        ]
    with open(ERGEBNIS_DIR / "lda_themen.json", "w", encoding="utf-8") as f:
        json.dump(themen_json, f, ensure_ascii=False, indent=2)
    print(f"  → LDA-Themen (JSON): lda_themen.json")

    # Textbericht
    bericht = erstelle_bericht(
        namen, gruppen, wortfrequenz, bigramme,
        lda, lda_begriffe, thema_verteilung, tfidf_df,
    )
    bericht_pfad = ERGEBNIS_DIR / "analysebericht.txt"
    bericht_pfad.write_text(bericht, encoding="utf-8")
    print(f"  → Textbericht: analysebericht.txt")

    print("\n" + "=" * 60)
    print(f"  Fertig! Alle Ergebnisse in:\n  {ERGEBNIS_DIR}")
    print("=" * 60 + "\n")

    # Kurzzusammenfassung auf der Konsole
    print("TOP 10 WÖRTER:", ", ".join(w for w, _ in wortfrequenz.most_common(10)))
    print("\nLDA-THEMEN (je 8 Schlüsselwörter):")
    for idx, thema in enumerate(lda.components_):
        top_idx = thema.argsort()[:-9:-1]
        print(f"  Thema {idx+1}: {' | '.join(lda_begriffe[i] for i in top_idx)}")


if __name__ == "__main__":
    main()
