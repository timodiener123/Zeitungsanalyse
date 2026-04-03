"""
gui.py – Streamlit-Oberfläche für die Stadtwächter-Analyse-Pipeline

Starten:
    streamlit run gui.py
    (aus dem pipeline/-Verzeichnis oder mit absolutem Pfad)
"""

import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# config aus demselben Verzeichnis
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# =============================================================================
# Seitenlayout
# =============================================================================
st.set_page_config(
    page_title="Stadtwächter-Pipeline",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

SCRIPTS_DIR = Path(__file__).parent / "scripts"

PIPELINE_STAGES = [
    {
        "key":    "s0b",
        "label":  "s0b – Preprocessing",
        "script": SCRIPTS_DIR / "s0b_preprocessing.py",
        "desc":   "Tokenisierung & Lemmatisierung mit spaCy · Ausgabe: corpus_lemmatized.parquet",
    },
    {
        "key":    "s1",
        "label":  "s1 – Frequenzanalyse",
        "script": SCRIPTS_DIR / "s1_frequency.py",
        "desc":   "Absolute & normalisierte Häufigkeiten · Seed-Term-Trend · Ausgabe: term_frequencies_*.csv",
    },
    {
        "key":    "s2",
        "label":  "s2 – Keyword-Analyse",
        "script": SCRIPTS_DIR / "s2_keywords.py",
        "desc":   "Log-Likelihood nach Dunning (1993) · Übergänge 1929→1930, 1930→1931",
    },
    {
        "key":    "s3",
        "label":  "s3 – N-Gramme",
        "script": SCRIPTS_DIR / "s3_ngrams.py",
        "desc":   "Bi- & Trigramme · antisemitische Kollokationen · Ausgabe: ngrams_*.csv",
    },
    {
        "key":    "s4",
        "label":  "s4 – Kollokationen",
        "script": SCRIPTS_DIR / "s4_collocations.py",
        "desc":   "Log-Likelihood & PMI für jude / jüdisch / judentum · Fenster ±5",
    },
    {
        "key":    "s5",
        "label":  "s5 – Topic Modeling",
        "script": SCRIPTS_DIR / "s5_topics.py",
        "desc":   "NMF mit 7 Topics · TF-IDF · Jahresanteile · Ausgabe: topics_*.csv",
    },
    {
        "key":    "s7",
        "label":  "s7 – KWIC",
        "script": SCRIPTS_DIR / "s7_kwic_bridge.py",
        "desc":   "Keyword-in-Context · Fenster ±30 · Ausgabe: kwic_bridge.xlsx",
    },
]


# =============================================================================
# Hilfsfunktionen
# =============================================================================
@st.cache_data(show_spinner=False)
def load_csv(path: Path) -> pd.DataFrame | None:
    if path.exists():
        return pd.read_csv(path)
    return None


def run_script(script_path: Path) -> tuple[int, str]:
    """Führt ein Pipeline-Skript aus und gibt (returncode, output) zurück."""
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    return result.returncode, result.stdout + result.stderr


def result_exists(*paths: Path) -> bool:
    return all(p.exists() for p in paths)


# =============================================================================
# Sidebar – Pipeline-Steuerung
# =============================================================================
with st.sidebar:
    st.title("📰 Stadtwächter-Pipeline")
    st.caption("Osnabrück 1929–1931")
    st.divider()

    st.subheader("Pipeline-Stufen ausführen")
    for stage in PIPELINE_STAGES:
        with st.expander(stage["label"], expanded=False):
            st.caption(stage["desc"])
            if st.button(f"▶ Ausführen", key=f"run_{stage['key']}"):
                with st.spinner(f"{stage['label']} läuft …"):
                    t0 = time.time()
                    rc, out = run_script(stage["script"])
                    elapsed = time.time() - t0
                load_csv.clear()  # Cache leeren
                if rc == 0:
                    st.success(f"Fertig in {elapsed:.1f}s")
                else:
                    st.error("Fehler – siehe Ausgabe unten")
                with st.expander("Skript-Ausgabe", expanded=(rc != 0)):
                    st.code(out, language="text")

    st.divider()
    st.caption(f"Korpus: {config.CORPUS_DIR.name[:40]}")
    st.caption(f"Jahrgänge: {', '.join(str(y) for y in config.TIME_SLICES)}")


# =============================================================================
# Hauptbereich – Tabs
# =============================================================================
st.title("Stadtwächter-Analyse · Quantitative Auswertung")
st.caption("Der Stadt-Wächter, Osnabrück, Jahrgänge 1929–1931")

tab_freq, tab_kw, tab_ngram, tab_colloc, tab_topic, tab_kwic = st.tabs([
    "📊 Frequenz",
    "🔑 Keywords",
    "🔗 N-Gramme",
    "📎 Kollokationen",
    "🗂️ Topics",
    "🔍 KWIC",
])

# ─────────────────────────────────────────────────── Tab: Frequenz
with tab_freq:
    st.header("Frequenzanalyse")

    seed_path  = config.RESULTS_DIR / "seedterm_frequencies.csv"
    freq_path  = config.RESULTS_DIR / "term_frequencies_gesamt.csv"
    trend_png  = config.VISUALIZATIONS_DIR / "seedterm_trend.png"

    col1, col2 = st.columns([1.6, 1])

    with col1:
        st.subheader("Seed-Term-Trend (Top-10 pMio)")
        if trend_png.exists():
            st.image(str(trend_png), use_container_width=True)
        else:
            st.info("Noch keine Visualisierung – bitte s1 ausführen.")

    with col2:
        st.subheader("Seed-Term-Häufigkeiten nach Jahrgang")
        df_seed = load_csv(seed_path)
        if df_seed is not None:
            pivot = df_seed.pivot_table(
                index="term", columns="year", values="per_million", aggfunc="sum"
            ).fillna(0).sort_values(config.TIME_SLICES[-1], ascending=False)
            st.dataframe(
                pivot.style.background_gradient(cmap="YlOrRd", axis=None),
                use_container_width=True,
                height=420,
            )
        else:
            st.info("Noch keine Daten – bitte s1 ausführen.")

    st.subheader("Gesamtvokabular (Top-200)")
    df_freq = load_csv(freq_path)
    if df_freq is not None:
        col_a, col_b = st.columns([2, 1])
        with col_a:
            search = st.text_input("Term suchen", placeholder="z.B. jude", key="freq_search")
        with col_b:
            top_n = st.slider("Top N", 10, 200, 50, key="freq_topn")
        if search:
            display = df_freq[df_freq["lemma"].str.contains(search, case=False, na=False)]
        else:
            display = df_freq.head(top_n)
        st.dataframe(display, use_container_width=True, height=300)
    else:
        st.info("Noch keine Daten – bitte s1 ausführen.")


# ─────────────────────────────────────────────────── Tab: Keywords
with tab_kw:
    st.header("Keyword-Analyse (Log-Likelihood, Dunning 1993)")

    kw_path = config.RESULTS_DIR / "keywords_transitions.csv"
    df_kw   = load_csv(kw_path)

    if df_kw is not None:
        transition = st.radio(
            "Übergang", ["1929→1930", "1930→1931"], horizontal=True, key="kw_trans"
        )
        direction = st.radio(
            "Richtung", ["Aufsteiger", "Absteiger", "Alle"], horizontal=True, key="kw_dir"
        )
        top_n_kw = st.slider("Top N", 10, 100, 25, key="kw_topn")

        sub = df_kw[df_kw["transition"] == transition].copy()
        if direction == "Aufsteiger":
            sub = sub[sub["direction"] == "Aufsteiger"].sort_values("g2", ascending=True)
        elif direction == "Absteiger":
            sub = sub[sub["direction"] == "Absteiger"].sort_values("g2", ascending=False)
        else:
            sub = sub.sort_values("g2", ascending=True)

        sub = sub.head(top_n_kw)

        col1, col2 = st.columns([1.4, 1])
        with col1:
            st.subheader(f"Top-{top_n_kw} {direction} ({transition})")
            st.dataframe(
                sub[["term", "g2", "pmio_a", "pmio_b", "pmio_diff", "direction"]],
                use_container_width=True, height=420,
            )
        with col2:
            st.subheader("G²-Balkendiagramm")
            if not sub.empty:
                fig, ax = plt.subplots(figsize=(5, max(3, len(sub) * 0.28)))
                colors = ["#d62728" if d == "Aufsteiger" else "#1f77b4"
                          for d in sub["direction"]]
                ax.barh(sub["term"], sub["g2"].abs(), color=colors)
                ax.set_xlabel("|G²|")
                ax.invert_yaxis()
                ax.set_title(f"{direction} {transition}")
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

        # Seed-Term-Tabelle
        st.subheader("Seed-Terme im Übergang")
        seed_sub = df_kw[df_kw["term"].isin(set(config.ALL_SEED_TERMS))]
        seed_pivot = seed_sub.pivot_table(
            index="term", columns="transition", values="g2"
        ).sort_values("1929→1930")
        st.dataframe(
            seed_pivot.style.background_gradient(cmap="RdBu_r", axis=None),
            use_container_width=True, height=320,
        )
    else:
        st.info("Noch keine Daten – bitte s2 ausführen.")


# ─────────────────────────────────────────────────── Tab: N-Gramme
with tab_ngram:
    st.header("N-Gramm-Analyse")

    ng_gesamt   = load_csv(config.RESULTS_DIR / "ngrams_gesamt.csv")
    ng_antisem  = load_csv(config.RESULTS_DIR / "ngrams_antisemitisch.csv")
    ng_jg       = load_csv(config.RESULTS_DIR / "ngrams_nach_jahrgang.csv")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top-N-Gramme gesamt")
        if ng_gesamt is not None:
            n_filter = st.radio("N-Gramm-Größe", [2, 3], horizontal=True, key="ng_n")
            show = ng_gesamt[ng_gesamt["n"] == n_filter]
            st.dataframe(show, use_container_width=True, height=380)
        else:
            st.info("Noch keine Daten – bitte s3 ausführen.")

    with col2:
        st.subheader("Antisemitische N-Gramme nach Jahrgang")
        if ng_antisem is not None:
            year_filter = st.selectbox(
                "Jahrgang", config.TIME_SLICES, key="ng_year"
            )
            n_filter2 = st.radio("N-Gramm-Größe", [2, 3], horizontal=True, key="ng_n2")
            show2 = (
                ng_antisem[(ng_antisem["year"] == year_filter) & (ng_antisem["n"] == n_filter2)]
                .sort_values("abs", ascending=False)
                .head(30)
            )
            st.dataframe(show2, use_container_width=True, height=350)
        else:
            st.info("Noch keine Daten – bitte s3 ausführen.")

    # Vergleichsplot: antisemitische Bigramm-Häufigkeiten nach Jahr
    st.subheader("Antisemitische Bigramme im Jahresvergleich (Top-10 per Million)")
    if ng_antisem is not None:
        bi = ng_antisem[ng_antisem["n"] == 2].copy()
        top_ngrams = (
            bi.groupby("ngram")["abs"].sum()
            .sort_values(ascending=False)
            .head(10)
            .index.tolist()
        )
        pivot_ng = (
            bi[bi["ngram"].isin(top_ngrams)]
            .pivot_table(index="year", columns="ngram", values="per_million", aggfunc="sum")
            .reindex(config.TIME_SLICES)
        )
        fig2, ax2 = plt.subplots(figsize=(11, 4))
        markers = ["o", "s", "D", "^", "v", "P", "X", "*", "h", "p"]
        for i, ngram in enumerate(top_ngrams):
            if ngram in pivot_ng.columns:
                ax2.plot(
                    pivot_ng.index, pivot_ng[ngram],
                    marker=markers[i % len(markers)], linewidth=1.8, markersize=7,
                    label=ngram,
                )
        ax2.set_xticks(config.TIME_SLICES)
        ax2.xaxis.set_major_formatter(ticker.FormatStrFormatter("%d"))
        ax2.set_ylabel("pMio")
        ax2.set_title("Top-10 antisemitische Bigramme 1929–1931")
        ax2.legend(fontsize=8, bbox_to_anchor=(1.01, 1), loc="upper left")
        ax2.grid(axis="y", linestyle="--", alpha=0.4)
        fig2.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)


# ─────────────────────────────────────────────────── Tab: Kollokationen
with tab_colloc:
    st.header("Kollokationsanalyse  (Fenster ±5)")

    df_ll  = load_csv(config.RESULTS_DIR / "collocations_ll.csv")
    df_pmi = load_csv(config.RESULTS_DIR / "collocations_pmi.csv")

    if df_ll is not None:
        target_sel = st.selectbox("Zielwort", ["jude", "jüdisch", "judentum"], key="coll_target")
        measure    = st.radio("Assoziationsmaß", ["Log-Likelihood (G²)", "PMI"], horizontal=True)
        scope_sel  = st.selectbox(
            "Scope", ["gesamt"] + [str(y) for y in config.TIME_SLICES], key="coll_scope"
        )
        top_n_coll = st.slider("Top N", 5, 40, 20, key="coll_topn")

        df_src = df_ll if "Log-Likelihood" in measure else df_pmi
        sort_col = "ll" if "Log-Likelihood" in measure else "pmi"

        sub_c = (
            df_src[(df_src["target"] == target_sel) & (df_src["scope"] == scope_sel)]
            .sort_values(sort_col, ascending=False)
            .head(top_n_coll)
        )

        col1, col2 = st.columns([1, 1.2])
        with col1:
            st.subheader(f"Top-{top_n_coll} Kollokate für '{target_sel}' [{scope_sel}]")
            st.dataframe(
                sub_c[["collocate", "cofreq", "ll", "pmi"]],
                use_container_width=True, height=400,
            )
        with col2:
            st.subheader(f"Jahresvergleich '{target_sel}' nach {sort_col.upper()}")
            # Alle Scopes: Kollokat → Wert pro Jahr
            rows_compare = []
            for y in config.TIME_SLICES:
                sub_y = (
                    df_src[(df_src["target"] == target_sel) & (df_src["scope"] == str(y))]
                    .set_index("collocate")[sort_col]
                )
                rows_compare.append(sub_y.rename(y))
            cmp_df = pd.concat(rows_compare, axis=1).dropna(thresh=2)
            cmp_df["gesamt_sum"] = cmp_df.sum(axis=1)
            cmp_df = cmp_df.sort_values("gesamt_sum", ascending=False).drop(
                columns="gesamt_sum"
            ).head(20)
            st.dataframe(
                cmp_df.style.background_gradient(cmap="Blues", axis=None),
                use_container_width=True, height=400,
            )
    else:
        st.info("Noch keine Daten – bitte s4 ausführen.")


# ─────────────────────────────────────────────────── Tab: Topics
with tab_topic:
    st.header("NMF Topic Modeling  (7 Topics)")

    df_kws   = load_csv(config.RESULTS_DIR / "topics_keywords.csv")
    df_doc   = load_csv(config.RESULTS_DIR / "topics_doc_matrix.csv")
    df_share = load_csv(config.RESULTS_DIR / "topics_year_shares.csv")

    if df_kws is not None and df_share is not None:
        # Kurzbezeichnungen
        def topic_label(t: int) -> str:
            top3 = df_kws[df_kws["topic"] == t].sort_values("rank").head(3)["term"].tolist()
            return f"T{t}: {' · '.join(top3)}"

        # Jahresanteile als Heatmap
        st.subheader("Topic-Anteile pro Jahrgang (%)")
        share_pivot = df_share.pivot_table(
            index="topic", columns="year", values="mean_share"
        ) * 100
        share_pivot.index = [topic_label(t) for t in share_pivot.index]
        fig3, ax3 = plt.subplots(figsize=(7, 4))
        im = ax3.imshow(share_pivot.values, cmap="YlOrRd", aspect="auto")
        ax3.set_xticks(range(len(config.TIME_SLICES)))
        ax3.set_xticklabels(config.TIME_SLICES)
        ax3.set_yticks(range(len(share_pivot)))
        ax3.set_yticklabels(share_pivot.index, fontsize=9)
        for i in range(share_pivot.shape[0]):
            for j in range(share_pivot.shape[1]):
                ax3.text(j, i, f"{share_pivot.values[i,j]:.1f}%",
                         ha="center", va="center", fontsize=9,
                         color="white" if share_pivot.values[i,j] > 30 else "black")
        plt.colorbar(im, ax=ax3, label="%")
        ax3.set_title("Mittlerer Topic-Anteil pro Jahrgang")
        fig3.tight_layout()
        st.pyplot(fig3)
        plt.close(fig3)

        # Linienplot: Topic-Verlauf
        st.subheader("Topic-Verlauf 1929–1931")
        fig4, ax4 = plt.subplots(figsize=(9, 4))
        markers = ["o", "s", "D", "^", "v", "P", "X"]
        for t_idx in range(len(share_pivot)):
            ax4.plot(
                config.TIME_SLICES,
                share_pivot.values[t_idx] ,
                marker=markers[t_idx % len(markers)],
                linewidth=1.8, markersize=7,
                label=share_pivot.index[t_idx],
            )
        ax4.set_xticks(config.TIME_SLICES)
        ax4.xaxis.set_major_formatter(ticker.FormatStrFormatter("%d"))
        ax4.set_ylabel("Mittlerer Anteil (%)")
        ax4.legend(fontsize=8, bbox_to_anchor=(1.01, 1), loc="upper left")
        ax4.grid(axis="y", linestyle="--", alpha=0.4)
        fig4.tight_layout()
        st.pyplot(fig4)
        plt.close(fig4)

        # Topic-Keywords-Tabelle
        st.subheader("Topic-Keywords (Top-15 pro Topic)")
        t_sel = st.selectbox(
            "Topic auswählen",
            options=list(range(7)),
            format_func=topic_label,
            key="topic_sel",
        )
        sub_kw = df_kws[df_kws["topic"] == t_sel].sort_values("rank")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.dataframe(sub_kw[["rank", "term", "weight", "is_seedterm"]],
                         use_container_width=True)
        with col2:
            seed_terms = sub_kw[sub_kw["is_seedterm"] == True]["term"].tolist()
            if seed_terms:
                st.info(f"Seed-Terme in diesem Topic: **{', '.join(seed_terms)}**")
            else:
                st.caption("Keine Seed-Terme in den Top-15 dieses Topics.")
            # Balkendiagramm
            fig5, ax5 = plt.subplots(figsize=(5, 4))
            ax5.barh(sub_kw["term"][::-1], sub_kw["weight"][::-1],
                     color=["#d62728" if s else "#4c72b0"
                            for s in sub_kw["is_seedterm"][::-1]])
            ax5.set_xlabel("TF-IDF-Gewicht")
            ax5.set_title(topic_label(t_sel))
            fig5.tight_layout()
            st.pyplot(fig5)
            plt.close(fig5)

    else:
        st.info("Noch keine Daten – bitte s5 ausführen.")


# ─────────────────────────────────────────────────── Tab: KWIC
with tab_kwic:
    st.header("Keyword-in-Context  (KWIC · Fenster ±30 Wörter)")

    kwic_path = config.RESULTS_DIR / "kwic_bridge.csv"
    df_kwic   = load_csv(kwic_path)

    if df_kwic is not None:
        col1, col2, col3 = st.columns(3)
        with col1:
            target_kwic = st.selectbox(
                "Zielwort", ["jude", "jüdisch", "judentum", "Alle"], key="kwic_target"
            )
        with col2:
            year_kwic = st.selectbox(
                "Jahrgang", ["Alle"] + [str(y) for y in config.TIME_SLICES], key="kwic_year"
            )
        with col3:
            search_kwic = st.text_input(
                "Kontext durchsuchen", placeholder="z.B. kaufen", key="kwic_search"
            )

        sub_k = df_kwic.copy()
        if target_kwic != "Alle":
            sub_k = sub_k[sub_k["target"] == target_kwic]
        if year_kwic != "Alle":
            sub_k = sub_k[sub_k["year"] == int(year_kwic)]
        if search_kwic:
            mask = (
                sub_k["left"].str.contains(search_kwic, case=False, na=False) |
                sub_k["right"].str.contains(search_kwic, case=False, na=False)
            )
            sub_k = sub_k[mask]

        st.caption(f"{len(sub_k):,} Treffer")

        # Trefferstatistik
        stat = (
            df_kwic.groupby(["target", "year"])
            .size()
            .reset_index(name="n")
            .pivot_table(index="target", columns="year", values="n", fill_value=0)
        )
        st.dataframe(stat, use_container_width=False)

        # Konkordanz-Tabelle
        st.subheader("Konkordanz")
        max_rows = st.slider("Anzahl Zeilen", 20, 500, 100, key="kwic_rows")
        display_cols = ["year", "doc_id", "keyword", "left", "right"]
        st.dataframe(
            sub_k[display_cols].head(max_rows).reset_index(drop=True),
            use_container_width=True,
            height=500,
        )

        # Download-Button für gefilterte Ergebnisse
        csv_bytes = sub_k.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Gefilterte KWIC als CSV herunterladen",
            data=csv_bytes,
            file_name=f"kwic_{target_kwic}_{year_kwic}.csv",
            mime="text/csv",
        )
    else:
        st.info("Noch keine Daten – bitte s7 ausführen.")

# Footer
st.divider()
st.caption("Stadtwächter-Analyse-Pipeline · spaCy · sklearn · Streamlit")
