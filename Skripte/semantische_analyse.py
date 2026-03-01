#!/usr/bin/env python3
"""
Semantische Feldanalyse & Kollokationsanalyse
==============================================
Untersucht historische Schlüsselwörter im Zeitungskorpus ("Der Stadtwächter",
Osnabrück ~1930–1931) mit korpuslinguistischen Standardmethoden:

  • KWIC-Konkordanz (Key Word In Context)
  • Kollokationsmaße: PMI, t-Score, Log-Likelihood (G²), relative Häufigkeit
  • Semantisches Feld (Kontextprofile je Schlüsselwort)
  • Diachrone Analyse (Vergleich über Dokumentengruppen)
  • Kollokationsnetzwerk (Graphvisualisierung)

Zielwörter (konfigurierbar): "juden" und "boykott"

Ausgabe: ergebnisse/semantische_analyse/
"""

import re
import os
import sys
import csv
import json
import math
import warnings
from pathlib import Path
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import networkx as nx
from nltk.corpus import stopwords
import nltk

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────
# Pfade
# ─────────────────────────────────────────────────────
BASIS_DIR   = Path(__file__).resolve().parent.parent
DATEN_DIR   = BASIS_DIR / "daten_txt"
ERGEBNIS_DIR = BASIS_DIR / "ergebnisse" / "semantische_analyse"
ERGEBNIS_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────
# Konfiguration
# ─────────────────────────────────────────────────────

# Schlüsselwörter und ihre Regex-Suchmuster (Lemma-Gruppe)
# Jeder Eintrag: (Anzeigename, Regex-Muster)
SCHLUESSELWOERTER = {
    "juden": r"\b(jude[ns]?|jüd(?:in|innen|isch[a-zäöü]*)?)\b",
    "boykott": r"\b(boykott(?:ier[a-zäöü]*|s)?|boicott\w*|bojkott\w*)\b",
}

FENSTER_GROESSE  = 5     # Tokens links/rechts für Kollokationsfenster
MIN_KOLLOKATFREQ = 2     # Mindesthäufigkeit eines Kollokatels (Kookkurrenz)
MIN_PMI          = 0.0   # Mindest-PMI (0 = keine Filterung)
N_TOP_KOLLOKATOREN = 30  # Anzahl Kollokatoren in Ergebnissen/Grafiken
N_KWIC           = 50    # Max. KWIC-Zeilen pro Keyword im Bericht

# ─────────────────────────────────────────────────────
# Stoppwörter (identisch mit explorative_analyse.py)
# ─────────────────────────────────────────────────────
try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords", quiet=True)

_SW_BASIS = set(stopwords.words("german"))
_SW_EXTRA = {
    "daß","dass","aber","auch","noch","schon","immer","sehr","mehr","wenn",
    "dann","denn","sein","hat","wird","wurde","haben","hatte","waren","wäre",
    "kann","muß","muss","soll","worden","wir","sie","ihr","ihm","ihn","uns",
    "ihre","ihren","ihrem","seine","seinen","seiner","seinem","jetzt","hier",
    "dort","wohl","erst","nur","eben","so","wie","alle","allem","allen","alles",
    "beim","zur","zum","durch","nach","vor","über","unter","gegen","aus","bei",
    "mit","von","an","auf","in","im","ist","die","der","das","des","den","dem",
    "ein","eine","einer","einem","einen","nicht","und","oder","als","für","zu",
    "es","sich","man","was","war","are","the","and","that","this","ja","nein",
    "nun","mal","wer","wo","gar","doch","weil","zwei","drei","ver","ter","noc",
    "fie","tion",
    # Fraktur-OCR-Artefakte
    "ber","bie","ben","bet","bas","bes","bte","bem","bec","unb","umb","uub",
    "sinb","wirb","wirft","ift","iit","lll","iii","ooo","eee","fei","fein",
    "feiner","feinen","feines","fich","foll","fann","fehr","fchon","fowie",
    "aud","nod","boch","hab","habe","hast","habt","gab","gibt","gang",
    "red","eid","eis","lag","ies",
}
STOPWOERTER = _SW_BASIS | _SW_EXTRA


# ─────────────────────────────────────────────────────
# Text-Utilities
# ─────────────────────────────────────────────────────

def normalisiere(text: str) -> str:
    """Fraktur-Normalisierung: langes ſ, ß, OCR-Korrekturen."""
    text = text.replace("ſ", "s").replace("ß", "ss").replace("ẞ", "SS")
    return text


def tokenisiere_roh(text: str) -> list[str]:
    """
    Tokenisierung ohne Stoppwort-Filterung – notwendig, um den
    linearen Tokenindex für Kontextfenster zu erhalten.
    Gibt Tokens in Kleinschreibung zurück.
    """
    text = normalisiere(text)
    text = re.sub(r"[^a-zA-ZäöüÄÖÜ\s]", " ", text)
    return text.lower().split()


def ist_inhaltswort(token: str) -> bool:
    """True wenn Token als Kollokator in Frage kommt."""
    return (
        len(token) >= 3
        and token not in STOPWOERTER
        and not re.match(r"^[^aeiouyäöü]+$", token)   # Nur-Konsonanten → OCR-Müll
    )


# ─────────────────────────────────────────────────────
# Korpus laden
# ─────────────────────────────────────────────────────

def lade_korpus(verzeichnis: Path):
    """
    Gibt zurück:
      dokumente : list[ dict(name, gruppe, tokens_roh, text_original) ]
    """
    dokumente = []
    for pfad in sorted(verzeichnis.rglob("*.txt")):
        try:
            text = pfad.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if len(text.strip()) < 50:
            continue
        dokumente.append({
            "name":    pfad.name,
            "gruppe":  pfad.parent.name,
            "tokens":  tokenisiere_roh(text),
            "text":    text,
        })
    return dokumente


# ─────────────────────────────────────────────────────
# Kollokationsanalyse
# ─────────────────────────────────────────────────────

def suche_trefferindizes(tokens: list[str], muster: re.Pattern) -> list[int]:
    """Gibt Positionen aller Keyword-Matches im Token-Array zurück."""
    return [i for i, t in enumerate(tokens) if muster.fullmatch(t)]


def extrahiere_kontext_tokens(
    tokens: list[str], treffer_idx: int, fenster: int
) -> list[str]:
    """Liefert Inhaltswörter im Fenster [idx-fenster, idx+fenster] (ohne Keyword)."""
    links  = max(0, treffer_idx - fenster)
    rechts = min(len(tokens), treffer_idx + fenster + 1)
    return [
        t for i, t in enumerate(tokens[links:rechts], start=links)
        if i != treffer_idx and ist_inhaltswort(t)
    ]


def erstelle_kwic(tokens: list[str], treffer_idx: int, fenster: int = 8) -> tuple[str, str, str]:
    """Gibt (linker Kontext, Keyword, rechter Kontext) als Strings zurück."""
    links  = max(0, treffer_idx - fenster)
    rechts = min(len(tokens), treffer_idx + fenster + 1)
    l_str  = " ".join(tokens[links:treffer_idx])
    kw_str = tokens[treffer_idx]
    r_str  = " ".join(tokens[treffer_idx + 1:rechts])
    return l_str, kw_str, r_str


def berechne_kollokationsstatistiken(
    f_kw: int,                  # Gesamthäufigkeit des Keywords
    f_koll: Counter,            # f(Kollokator) im Gesamtkorpus
    f_kw_koll: Counter,         # f(Keyword, Kollokator) = Kookkurrenz
    N: int,                     # Gesamtzahl Tokens im Korpus
) -> pd.DataFrame:
    """
    Berechnet für jeden Kollokator:
      - Freq    : Kookkurrenz-Häufigkeit
      - PMI     : Pointwise Mutual Information (log2)
      - t-Score : Association t-test
      - G2      : Log-Likelihood (G²)
      - MI3     : Normiertes MI (MI³, robust bei seltenen Wörtern)
    """
    zeilen = []
    for koll, f12 in f_kw_koll.items():
        if f12 < MIN_KOLLOKATFREQ:
            continue
        f2 = f_koll[koll]
        if f2 == 0:
            continue

        # Erwartete Häufigkeit
        e11 = (f_kw * f2) / N
        e11 = max(e11, 1e-9)

        # PMI
        pmi = math.log2(f12 / e11) if f12 > 0 else float("-inf")

        # t-Score
        t_score = (f12 - e11) / math.sqrt(max(f12, 1))

        # Log-Likelihood G² (2×2-Kontingenztafel)
        f11 = f12
        f21 = f2 - f12       # Kollokator ohne Keyword
        f12_ = f_kw - f12    # Keyword ohne Kollokator
        f22 = N - f11 - f21 - f12_

        def ll_beitrag(o, e):
            return 2 * o * math.log(o / e) if o > 0 and e > 0 else 0

        e11_ = (f_kw * f2) / N
        e21  = ((N - f_kw) * f2) / N
        e12_ = (f_kw * (N - f2)) / N
        e22  = ((N - f_kw) * (N - f2)) / N

        g2 = (ll_beitrag(f11, max(e11_, 1e-9)) +
              ll_beitrag(f21, max(e21, 1e-9)) +
              ll_beitrag(f12_, max(e12_, 1e-9)) +
              ll_beitrag(f22, max(e22, 1e-9)))

        # MI³ (kubisches MI, robust gegen seltene Kollokationen)
        mi3 = math.log2((f12 ** 3) / max(e11_, 1e-9)) if f12 > 0 else float("-inf")

        zeilen.append({
            "Kollokator":  koll,
            "Freq":        f12,
            "Freq_Koll":   f2,
            "PMI":         round(pmi, 4),
            "t-Score":     round(t_score, 4),
            "G2":          round(g2, 4),
            "MI3":         round(mi3, 4),
        })

    df = pd.DataFrame(zeilen)
    if df.empty:
        return df
    return df.sort_values("G2", ascending=False).reset_index(drop=True)


# ─────────────────────────────────────────────────────
# Diachrone Analyse
# ─────────────────────────────────────────────────────

def diachrone_analyse(
    dokumente: list[dict],
    muster: re.Pattern,
    top_kollokatoren: list[str],
    fenster: int = FENSTER_GROESSE,
) -> pd.DataFrame:
    """
    Berechnet für jede Dokumentengruppe die relative Häufigkeit
    der Top-Kollokatoren im Kontext des Keywords.
    """
    gruppen = sorted(set(d["gruppe"] for d in dokumente))
    ergebnis = defaultdict(dict)

    for gruppe in gruppen:
        gruppe_docs = [d for d in dokumente if d["gruppe"] == gruppe]
        kookkurrenzen = Counter()
        for dok in gruppe_docs:
            for idx in suche_trefferindizes(dok["tokens"], muster):
                kookkurrenzen.update(
                    extrahiere_kontext_tokens(dok["tokens"], idx, fenster)
                )
        gesamt = sum(kookkurrenzen.values()) or 1
        for koll in top_kollokatoren:
            ergebnis[koll][gruppe] = kookkurrenzen.get(koll, 0) / gesamt * 1000

    df = pd.DataFrame(ergebnis).T
    df.columns = [g[:30] for g in gruppen]
    return df


# ─────────────────────────────────────────────────────
# Visualisierungen
# ─────────────────────────────────────────────────────

def plot_kollokatoren_balken(df: pd.DataFrame, keyword: str, pfad: Path, n: int = N_TOP_KOLLOKATOREN) -> None:
    """Horizontales Balkendiagramm mit vier Assoziationsmaßen nebeneinander."""
    df_top = df.head(n).copy()
    metriken  = ["G2", "t-Score", "PMI", "MI3"]
    farben    = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0"]
    fig, axes = plt.subplots(1, 4, figsize=(20, max(8, n * 0.38)), sharey=True)

    for ax, metrik, farbe in zip(axes, metriken, farben):
        vals = df_top[metrik]
        bars = ax.barh(range(len(df_top)), vals, color=farbe, alpha=0.85)
        ax.set_yticks(range(len(df_top)))
        ax.set_yticklabels(df_top["Kollokator"], fontsize=9)
        ax.invert_yaxis()
        ax.set_title(metrik, fontsize=12, fontweight="bold", color=farbe)
        ax.set_xlabel("Wert", fontsize=9)
        ax.axvline(0, color="gray", linewidth=0.7)
        for bar, v in zip(bars, vals):
            ax.text(max(v, 0) + abs(vals.max()) * 0.01,
                    bar.get_y() + bar.get_height() / 2,
                    f"{v:.1f}", va="center", fontsize=7)

    fig.suptitle(
        f"Kollokatoren von »{keyword}« – Assoziationsmaße\n"
        f"(Fenstergröße ±{FENSTER_GROESSE}, sortiert nach G²)",
        fontsize=13, y=1.01,
    )
    fig.tight_layout()
    fig.savefig(pfad, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → Balkendiagramm: {pfad.name}")


def plot_kollokationsnetzwerk(
    df: pd.DataFrame, keyword: str, pfad: Path, n: int = 20
) -> None:
    """Netzwerkgraph: Keyword im Zentrum, Kollokatoren als Knoten, G² als Kantengewicht."""
    df_top = df.head(n).copy()
    G = nx.Graph()
    G.add_node(keyword, typ="keyword")

    max_g2 = df_top["G2"].max() or 1
    for _, row in df_top.iterrows():
        koll = row["Kollokator"]
        G.add_node(koll, typ="kollokator")
        G.add_edge(keyword, koll, weight=row["G2"] / max_g2, g2=row["G2"])

    pos = nx.spring_layout(G, k=2.5, seed=42, weight="weight")
    pos[keyword] = np.array([0, 0])  # Keyword ins Zentrum

    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_facecolor("#f8f9fa")
    fig.patch.set_facecolor("#f8f9fa")

    # Kanten (Stärke = G²-Gewicht)
    for u, v, data in G.edges(data=True):
        x = [pos[u][0], pos[v][0]]
        y = [pos[u][1], pos[v][1]]
        ax.plot(x, y, color="#aaaaaa", linewidth=data["weight"] * 4, alpha=0.6, zorder=1)

    # Kollokator-Knoten (Größe & Farbe nach G²)
    g2_vals = np.array([G[keyword][k]["g2"] for k in df_top["Kollokator"]])
    koll_pos = np.array([pos[k] for k in df_top["Kollokator"]])
    sc = ax.scatter(
        koll_pos[:, 0], koll_pos[:, 1],
        s=80 + 600 * (g2_vals / max_g2),
        c=g2_vals, cmap="YlOrRd", zorder=3, edgecolors="white", linewidths=1.5,
    )
    plt.colorbar(sc, ax=ax, label="G² (Log-Likelihood)", shrink=0.6)

    # Keyword-Knoten
    ax.scatter(*pos[keyword], s=1200, c="#1565C0", zorder=5, edgecolors="white", linewidths=2)
    ax.text(*pos[keyword], keyword.upper(), ha="center", va="center",
            fontsize=11, fontweight="bold", color="white", zorder=6)

    # Beschriftungen
    for koll in df_top["Kollokator"]:
        x, y = pos[koll]
        ax.text(x, y + 0.06, koll, ha="center", va="bottom", fontsize=8.5,
                fontweight="bold", zorder=7,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7))

    ax.set_title(
        f"Kollokationsnetzwerk »{keyword}« (Top {n} Kollokatoren, nach G²)",
        fontsize=13, pad=12,
    )
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(pfad, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → Kollokationsnetzwerk: {pfad.name}")


def plot_diachron(df_dia: pd.DataFrame, keyword: str, pfad: Path) -> None:
    """Heatmap der Top-Kollokatoren über Dokumentengruppen (normierte Häufigkeit)."""
    if df_dia.empty:
        return
    fig, ax = plt.subplots(figsize=(max(8, len(df_dia.columns) * 2), max(6, len(df_dia) * 0.45)))
    sns.heatmap(
        df_dia,
        cmap="Blues",
        linewidths=0.4,
        ax=ax,
        annot=True,
        fmt=".1f",
        cbar_kws={"label": "Häufigkeit pro 1.000 Kontexttokens"},
    )
    ax.set_title(
        f"Kollokatoren von »{keyword}« – diachrone Verteilung\n"
        "(Häufigkeit pro 1.000 Kontexttokens, je Dokumentengruppe)",
        fontsize=12,
    )
    ax.set_xlabel("Dokumentengruppe")
    ax.set_ylabel("Kollokator")
    ax.tick_params(axis="x", rotation=20, labelsize=8)
    ax.tick_params(axis="y", labelsize=9)
    fig.tight_layout()
    fig.savefig(pfad, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → Diachrone Heatmap: {pfad.name}")


def plot_vergleich_keywords(
    koll_daten: dict,          # {keyword: DataFrame mit Kollokationsstatistiken}
    pfad: Path,
    n: int = 20,
) -> None:
    """Vergleich der Top-Kollokatoren beider Keywords als Bubble-Chart (G² vs PMI)."""
    fig, axes = plt.subplots(1, len(koll_daten), figsize=(10 * len(koll_daten), 7), squeeze=False)
    axes = axes[0]
    farben = ["#1565C0", "#C62828"]

    for ax, (keyword, df), farbe in zip(axes, koll_daten.items(), farben):
        df_top = df.head(n).copy()
        if df_top.empty:
            ax.set_title(f"»{keyword}« – keine Daten")
            continue
        sc = ax.scatter(
            df_top["PMI"], df_top["t-Score"],
            s=df_top["G2"] / df_top["G2"].max() * 800 + 50,
            c=df_top["Freq"], cmap="YlOrRd",
            alpha=0.8, edgecolors="white", linewidths=1,
        )
        plt.colorbar(sc, ax=ax, label="Kookkurrenz-Häufigkeit")
        for _, row in df_top.iterrows():
            ax.annotate(
                row["Kollokator"],
                (row["PMI"], row["t-Score"]),
                fontsize=8, ha="center", va="bottom",
                xytext=(0, 6), textcoords="offset points",
            )
        ax.axvline(0, color="gray", linewidth=0.8, linestyle="--")
        ax.axhline(0, color="gray", linewidth=0.8, linestyle="--")
        ax.set_xlabel("PMI (log₂)", fontsize=10)
        ax.set_ylabel("t-Score", fontsize=10)
        ax.set_title(
            f"»{keyword}« – Kollokationsraum\n(Größe = G², Farbe = Häufigkeit)",
            fontsize=11, color=farbe,
        )
    fig.suptitle("Semantischer Raum der Schlüsselwörter", fontsize=13)
    fig.tight_layout()
    fig.savefig(pfad, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → Keyword-Vergleich: {pfad.name}")


# ─────────────────────────────────────────────────────
# Textbericht
# ─────────────────────────────────────────────────────

def erstelle_bericht(
    keyword: str,
    muster_str: str,
    n_treffer: int,
    n_dokumente_mit_kw: int,
    n_docs: int,
    N: int,
    df_koll: pd.DataFrame,
    kwic_zeilen: list[tuple],
    bigramme: Counter,
) -> str:
    """Menschenlesbarer Analysebericht für ein Keyword."""
    zeilen = [
        "=" * 72,
        f"SEMANTISCHE FELDANALYSE: »{keyword.upper()}«",
        "=" * 72,
        "",
        "── KORPUSVORKOMMEN ─────────────────────────────────────────────────────",
        f"  Suche (Regex): {muster_str}",
        f"  Treffer gesamt          : {n_treffer:,}",
        f"  Dokumente mit Vorkommen : {n_dokumente_mit_kw} / {n_docs}",
        f"  Relative Häufigkeit     : {n_treffer / N * 10000:.2f} pro 10.000 Token",
        "",
        "── TOP KOLLOKATOREN (sortiert nach G²) ─────────────────────────────────",
        f"  Fenstergröße: ±{FENSTER_GROESSE} Tokens",
        "",
        f"  {'Rang':<5} {'Kollokator':<22} {'Freq':>6} {'G²':>9} {'t-Score':>9} {'PMI':>7} {'MI³':>7}",
        "  " + "-" * 64,
    ]
    for rang, row in df_koll.head(50).iterrows():
        zeilen.append(
            f"  {rang+1:<5} {row['Kollokator']:<22} {row['Freq']:>6} "
            f"{row['G2']:>9.2f} {row['t-Score']:>9.4f} {row['PMI']:>7.3f} {row['MI3']:>7.3f}"
        )

    zeilen += [
        "",
        "── HÄUFIGE BIGRAMME IM KONTEXT ─────────────────────────────────────────",
    ]
    for (w1, w2), h in bigramme.most_common(20):
        zeilen.append(f"  {w1} {w2:<40} {h}×")

    zeilen += [
        "",
        f"── KWIC-KONKORDANZ (max. {N_KWIC} Belege) ─────────────────────────────",
        f"  {'Dokument':<30} {'← Kontext':<35} {'KEYWORD':<12} {'Kontext →'}",
        "  " + "-" * 90,
    ]
    for dok_name, l, kw, r in kwic_zeilen[:N_KWIC]:
        zeilen.append(
            f"  {dok_name[:28]:<30} {l[-35:]:<35} [{kw.upper()}] {r[:35]}"
        )

    zeilen.append("\n" + "=" * 72)
    return "\n".join(zeilen)


# ─────────────────────────────────────────────────────
# Hauptprogramm
# ─────────────────────────────────────────────────────

def analysiere_keyword(
    keyword: str,
    muster: re.Pattern,
    dokumente: list[dict],
    freq_alle_tokens: Counter,
    N: int,
) -> dict:
    """Vollständige Kollokationsanalyse für ein Schlüsselwort."""
    print(f"\n  ── Analysiere »{keyword}« ──────────────────────────────────")

    # 1. Treffer sammeln
    f_kw_koll  = Counter()   # Kookkurrenz
    kwic_zeilen = []
    n_treffer   = 0
    docs_mit_kw = 0
    bigramme    = Counter()

    for dok in dokumente:
        trefferindizes = suche_trefferindizes(dok["tokens"], muster)
        if not trefferindizes:
            continue
        docs_mit_kw += 1
        n_treffer    += len(trefferindizes)

        for idx in trefferindizes:
            kontext = extrahiere_kontext_tokens(dok["tokens"], idx, FENSTER_GROESSE)
            f_kw_koll.update(kontext)

            # Bigramme im engeren Fenster (±2)
            nah = extrahiere_kontext_tokens(dok["tokens"], idx, 2)
            for i in range(len(nah) - 1):
                bigramme[(nah[i], nah[i+1])] += 1

            l, kw, r = erstelle_kwic(dok["tokens"], idx, fenster=8)
            kwic_zeilen.append((dok["name"], l, kw, r))

    print(f"    Treffer: {n_treffer} in {docs_mit_kw} Dokumenten")

    if n_treffer == 0:
        print(f"    [!] Keine Treffer für »{keyword}« – Analyse übersprungen.")
        return {}

    # 2. Kollokationsstatistiken
    df_koll = berechne_kollokationsstatistiken(
        f_kw=n_treffer,
        f_koll=freq_alle_tokens,
        f_kw_koll=f_kw_koll,
        N=N,
    )
    print(f"    Kollokatoren (≥{MIN_KOLLOKATFREQ}×): {len(df_koll)}")

    # 3. Diachrone Analyse
    top_kolls = df_koll["Kollokator"].head(15).tolist() if not df_koll.empty else []
    df_dia = diachrone_analyse(dokumente, muster, top_kolls, FENSTER_GROESSE)

    # 4. Ergebnisordner
    kw_dir = ERGEBNIS_DIR / keyword
    kw_dir.mkdir(exist_ok=True)

    # 5. Grafiken
    if not df_koll.empty:
        plot_kollokatoren_balken(df_koll, keyword, kw_dir / "kollokatoren_assoziationsmasse.png")
        plot_kollokationsnetzwerk(df_koll, keyword, kw_dir / "kollokationsnetzwerk.png")
    if not df_dia.empty:
        plot_diachron(df_dia, keyword, kw_dir / "diachron_heatmap.png")

    # 6. CSV-Exporte
    df_koll.to_csv(kw_dir / "kollokatoren.csv", index=False, encoding="utf-8-sig")
    print(f"    → CSV: kollokatoren.csv")

    kwic_df = pd.DataFrame(kwic_zeilen, columns=["Dokument", "Links", "Keyword", "Rechts"])
    kwic_df.to_csv(kw_dir / "kwic_konkordanz.csv", index=False, encoding="utf-8-sig")
    print(f"    → CSV: kwic_konkordanz.csv ({len(kwic_zeilen)} Belege)")

    # 7. Textbericht
    bericht = erstelle_bericht(
        keyword=keyword,
        muster_str=muster.pattern,
        n_treffer=n_treffer,
        n_dokumente_mit_kw=docs_mit_kw,
        n_docs=len(dokumente),
        N=N,
        df_koll=df_koll,
        kwic_zeilen=kwic_zeilen,
        bigramme=bigramme,
    )
    (kw_dir / "analysebericht.txt").write_text(bericht, encoding="utf-8")
    print(f"    → Bericht: analysebericht.txt")

    return {
        "keyword":    keyword,
        "n_treffer":  n_treffer,
        "n_docs":     docs_mit_kw,
        "df_koll":    df_koll,
        "df_dia":     df_dia,
        "kwic":       kwic_zeilen,
        "bigramme":   bigramme,
    }


def main():
    print("\n" + "=" * 60)
    print("  Semantische Feldanalyse – Zeitungskorpus")
    print("=" * 60)

    # Korpus laden
    print(f"\n[1/4] Lade Korpus aus: {DATEN_DIR}")
    dokumente = lade_korpus(DATEN_DIR)
    if not dokumente:
        sys.exit("Keine Dokumente gefunden.")

    alle_tokens = [t for d in dokumente for t in d["tokens"]]
    N = len(alle_tokens)
    freq_alle = Counter(alle_tokens)
    print(f"      {len(dokumente)} Dokumente | {N:,} Tokens")

    # Keyword-Analysen
    print(f"\n[2/4] Kollokationsanalyse für {len(SCHLUESSELWOERTER)} Schlüsselwörter …")
    ergebnisse = {}
    for keyword, muster_str in SCHLUESSELWOERTER.items():
        muster = re.compile(muster_str, re.IGNORECASE)
        ergebnis = analysiere_keyword(keyword, muster, dokumente, freq_alle, N)
        if ergebnis:
            ergebnisse[keyword] = ergebnis

    # Vergleichsgrafik beider Keywords
    print(f"\n[3/4] Erstelle Vergleichsgrafiken …")
    if len(ergebnisse) >= 1:
        koll_daten = {kw: res["df_koll"] for kw, res in ergebnisse.items()}
        plot_vergleich_keywords(koll_daten, ERGEBNIS_DIR / "keyword_vergleich_scatter.png")

    # Gesamt-JSON-Export
    print(f"\n[4/4] Speichere Metadaten …")
    meta = {
        kw: {
            "treffer": res["n_treffer"],
            "dokumente": res["n_docs"],
            "top20_kollokatoren_G2": res["df_koll"].head(20)[["Kollokator","G2","t-Score","PMI"]].to_dict(orient="records"),
        }
        for kw, res in ergebnisse.items()
    }
    (ERGEBNIS_DIR / "zusammenfassung.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  → zusammenfassung.json")

    # Konsolen-Zusammenfassung
    print("\n" + "=" * 60)
    print("  ERGEBNISSE")
    print("=" * 60)
    for kw, res in ergebnisse.items():
        print(f"\n»{kw}« – {res['n_treffer']} Treffer in {res['n_docs']} Dokumenten")
        print(f"  Top-15 Kollokatoren (G²):")
        for _, row in res["df_koll"].head(15).iterrows():
            print(f"    {row['Kollokator']:<22} G²={row['G2']:>8.1f}  PMI={row['PMI']:>6.3f}")

    print(f"\n  Alle Ergebnisse in: {ERGEBNIS_DIR}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
