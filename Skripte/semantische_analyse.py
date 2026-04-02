#!/usr/bin/env python3
"""
Semantische Feldanalyse – Stadtwächter Osnabrück (~1930)
Suchbegriffe: 'Sozialdemokratie' / 'Nationalsozialismus' (alle Flexionen)
POS-Filterung via spaCy de_core_news_sm (NOUN, VERB, ADJ).
SPEICHEREFFIZIENT: eine Datei nach der anderen, GC nach jeder Datei.
"""

import gc
import re
import csv
from pathlib import Path
from collections import Counter, defaultdict

import spacy

# ── Konfiguration ─────────────────────────────────────────────────────────────

DATA_DIR    = Path('daten_txt')
AUSGABE_DIR = Path('ergebnisse/semantische_analyse')
FENSTER     = 5          # Token vor/nach dem Treffer
MAX_KWIC    = 5          # Max. KWIC-Beispiele pro Datei pro Begriff
TOP_N       = 50         # Wie viele Kollokationen in die CSV

# Suchpräfixe (Flexions-tolerant; Lemma-Matching via spaCy wäre ideal,
# aber Präfixe sind schneller und für historisches Deutsch robuster)
SUCHPRAEFIXE = {
    'sozialdemokratie':    'sozialdemokrat',
    'nationalsozialismus': 'nationalsozialist',
}

# POS-Klassen, die als bedeutungstragende Kollokationen zählen
INHALTS_POS = {'NOUN', 'PROPN', 'VERB', 'ADJ', 'ADV'}
# Labels für CSV-Ausgabe
POS_LABEL = {
    'NOUN': 'Substantiv', 'PROPN': 'Eigenname',
    'VERB': 'Verb',        'ADJ':  'Adjektiv',
    'ADV':  'Adverb',
}

# Eigene Stopwörter (ergänzen spaCy-is_stop):
# OCR-Artefakte aus Fraktur + allgemeine Füllwörter
EXTRA_STOP = {
    'bie', 'ben', 'bet', 'bas', 'unb', 'fei', 'fich', 'foll', 'fann',
    'ber', 'bte', 'bies', 'beit', 'burd', 'benn', 'beim', 'baft',
    'daß', 'dass', 'schon', 'bereits', 'immer', 'wohl', 'auch', 'noch',
    'sehr', 'mehr', 'ganz', 'gar', 'mal', 'nun', 'doch', 'eben',
    'dabei', 'dazu', 'bisher', 'stets', 'jedoch', 'also', 'seite',
    'herr', 'herrn',          # zu generisch im Zeitungskontext
}

# ── spaCy laden (einmalig, Pipes deaktivieren die wir nicht brauchen) ─────────

print("Lade spaCy-Modell de_core_news_sm …", flush=True)
nlp = spacy.load(
    'de_core_news_sm',
    exclude=['parser', 'ner', 'senter'],   # nur POS-Tagging benötigt
)
nlp.max_length = 2_000_000   # Sicherheitspuffer für lange Dateien
print("Modell geladen.\n", flush=True)

# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

_re_nonword = re.compile(r'[^a-zäöüßA-ZÄÖÜ\-]')

def ist_stoppwort(token) -> bool:
    """True, wenn Token als Stoppwort gilt (spaCy + eigene Liste)."""
    if token.is_stop or token.is_punct or token.is_space:
        return True
    low = token.lower_
    return low in EXTRA_STOP or len(low) < 3


def token_normiert(token) -> str:
    """Lemma in Kleinbuchstaben, nur Buchstaben."""
    basis = token.lemma_ if token.lemma_ != '--' else token.text
    return re.sub(r'[^a-zäöüß]', '', basis.lower().replace('ſ', 's'))


def verarbeite_datei(pfad: Path,
                     koll_zaehler: dict,
                     pos_zaehler: dict,
                     form_zaehler: dict,
                     kwic_beispiele: dict) -> dict:
    """
    Liest EINE Datei, lässt spaCy drüberlaufen, extrahiert Kollokationen.
    Alles außer den Counter-Objekten wird sofort freigegeben.
    """
    treffer = {label: 0 for label in SUCHPRAEFIXE}

    try:
        rohtext = pfad.read_text(encoding='utf-8', errors='replace')
    except OSError as e:
        print(f"    [FEHLER] {e}", flush=True)
        return treffer

    # spaCy-Analyse
    doc = nlp(rohtext)
    rohtext = None   # Rohtext freigeben

    tokens = list(doc)   # einmalig materialisieren
    doc = None           # Doc-Objekt freigeben
    n = len(tokens)

    for i, tok in enumerate(tokens):
        norm = tok.lower_.replace('ſ', 's')

        for label, praefix in SUCHPRAEFIXE.items():
            if norm.startswith(praefix) and len(norm) >= len(praefix):
                treffer[label] += 1
                form_zaehler[label][norm] += 1

                # Kontextfenster
                lo = max(0, i - FENSTER)
                hi = min(n, i + FENSTER + 1)
                kontext = tokens[lo:i] + tokens[i + 1:hi]

                for kw in kontext:
                    if kw.pos_ not in INHALTS_POS:
                        continue
                    if ist_stoppwort(kw):
                        continue
                    kw_norm = token_normiert(kw)
                    if len(kw_norm) < 3 or kw_norm.startswith(praefix):
                        continue

                    koll_zaehler[label][kw_norm] += 1
                    pos_zaehler[label][kw_norm] = POS_LABEL.get(kw.pos_, kw.pos_)

                # KWIC-Beispiel speichern (bis MAX_KWIC pro Datei)
                if len(kwic_beispiele[label]) < MAX_KWIC:
                    ctx_lo = max(0, i - 6)
                    ctx_hi = min(n, i + 7)
                    snippet = ' '.join(t.text for t in tokens[ctx_lo:ctx_hi])
                    kwic_beispiele[label].append({
                        'Datei': pfad.name,
                        'Treffer': tok.text,
                        'Kontext': snippet,
                    })

    tokens = None
    gc.collect()
    return treffer


# ── Hauptprogramm ─────────────────────────────────────────────────────────────

def main():
    AUSGABE_DIR.mkdir(parents=True, exist_ok=True)

    # Akkumulatoren – laufen über alle Dateien
    koll_zaehler  = {label: Counter()          for label in SUCHPRAEFIXE}
    pos_zaehler   = {label: {}                 for label in SUCHPRAEFIXE}
    form_zaehler  = {label: Counter()          for label in SUCHPRAEFIXE}
    kwic_gesamt   = {label: []                 for label in SUCHPRAEFIXE}
    treffer_total = {label: 0                  for label in SUCHPRAEFIXE}
    datei_hits    = {label: 0                  for label in SUCHPRAEFIXE}

    alle_dateien = sorted(DATA_DIR.rglob('*.txt'))
    gesamt = len(alle_dateien)

    print(f"Dateien gefunden : {gesamt}")
    print(f"Suchbegriffe     : {', '.join(SUCHPRAEFIXE)}")
    print(f"Kontextfenster   : ±{FENSTER} Token")
    print(f"POS-Filter       : {', '.join(sorted(INHALTS_POS))}")
    print("─" * 65, flush=True)

    for idx, pfad in enumerate(alle_dateien, 1):
        print(f"[{idx:>3}/{gesamt}] {pfad.name}", end='', flush=True)

        kwic_diese_datei = {label: [] for label in SUCHPRAEFIXE}
        treffer = verarbeite_datei(pfad, koll_zaehler, pos_zaehler,
                                   form_zaehler, kwic_diese_datei)

        hits_str = [f"{lb}={n}" for lb, n in treffer.items() if n > 0]
        print(f"  → {', '.join(hits_str) if hits_str else '(kein Treffer)'}",
              flush=True)

        for lb, n in treffer.items():
            treffer_total[lb] += n
            if n > 0:
                datei_hits[lb] += 1
            # Nur die ersten MAX_KWIC aus dieser Datei übernehmen
            kwic_gesamt[lb].extend(kwic_diese_datei[lb])

    print("\n" + "─" * 65)
    print("Analyse abgeschlossen. Speichere Ergebnisse …\n")

    # ── Ergebnisse speichern ──────────────────────────────────────────────────

    for label in SUCHPRAEFIXE:
        top = koll_zaehler[label].most_common(TOP_N)
        gesamt_koll_tokens = sum(koll_zaehler[label].values())

        # ── 1. Kollokationen-CSV ──────────────────────────────────────────────
        csv_koll = AUSGABE_DIR / f'kollokatoren_{label}.csv'
        with open(csv_koll, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['Rang', 'Kollokator', 'Wortklasse',
                        'Häufigkeit', 'Anteil_%'])
            for rang, (wort, cnt) in enumerate(top, 1):
                anteil = round(cnt / gesamt_koll_tokens * 100, 2) \
                         if gesamt_koll_tokens else 0
                w.writerow([rang, wort,
                            pos_zaehler[label].get(wort, '?'),
                            cnt, anteil])

        # ── 2. Wortformen-CSV ─────────────────────────────────────────────────
        csv_form = AUSGABE_DIR / f'wortformen_{label}.csv'
        with open(csv_form, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['Wortform', 'Häufigkeit'])
            for form, cnt in form_zaehler[label].most_common():
                w.writerow([form, cnt])

        # ── 3. KWIC-CSV ───────────────────────────────────────────────────────
        csv_kwic = AUSGABE_DIR / f'kwic_{label}.csv'
        with open(csv_kwic, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['Nr', 'Datei', 'Treffer-Wortform', 'Kontext'])
            for nr, eintrag in enumerate(kwic_gesamt[label], 1):
                w.writerow([nr, eintrag['Datei'],
                            eintrag['Treffer'], eintrag['Kontext']])

        # ── Terminal-Ausgabe ──────────────────────────────────────────────────
        print(f"{'═'*65}")
        print(f"  SUCHBEGRIFF: '{label.upper()}'")
        print(f"  Treffer gesamt : {treffer_total[label]:,} "
              f"(in {datei_hits[label]} / {gesamt} Dateien)")
        print(f"  Koll.-Token    : {gesamt_koll_tokens:,}")

        print(f"\n  Wortformen im Korpus:")
        for form, cnt in form_zaehler[label].most_common(10):
            print(f"    {form:<35} {cnt:>4}×")

        print(f"\n  Top-25 Kollokationen (±{FENSTER} Token, nur NOUN/VERB/ADJ):")
        print(f"  {'Rang':>4}  {'Wort':<30} {'Klasse':<12} {'Häufig.':>7}  {'Anteil':>6}")
        print(f"  {'─'*4}  {'─'*30} {'─'*12} {'─'*7}  {'─'*6}")
        for rang, (wort, cnt) in enumerate(top[:25], 1):
            klasse = pos_zaehler[label].get(wort, '?')
            anteil = cnt / gesamt_koll_tokens * 100 if gesamt_koll_tokens else 0
            print(f"  {rang:>4}  {wort:<30} {klasse:<12} {cnt:>7}  {anteil:>5.1f}%")

        print(f"\n  → {csv_koll}")
        print(f"  → {csv_form}")
        print(f"  → {csv_kwic}")

    print(f"\n{'═'*65}")
    print(f"Fertig. Ergebnisse in: {AUSGABE_DIR}/")


if __name__ == '__main__':
    main()
