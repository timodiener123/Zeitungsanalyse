#!/usr/bin/env python3
"""
s0a_regex_korrektur.py – Regelbasierte Regex-Post-OCR-Korrektur
================================================================
Stufe 0a (Variante) in der Stadtwächter-Pipeline.

Zweck:
  Systematische, wortgrenzenbasierte Ersetzungen für Texte 1929–1931:
  - ß-Wiederherstellung (moderne ss → historisches ß)
  - Fraktur-Sonderzeichen (langes ſ)
  - Umlaut-Ligaturen (Oe → Ö, Ae → Ä, Ue → Ü)
  - Schutz von Abkürzungen (RM, etc.)

Ausgabe:
  - Korrigierte Textdateien → daten_txt_regex_korrigiert/
  - Ersetzungslog           → ocr_validierung/regex_korrektur_log.csv
  - CER/WER-Vergleich       → Konsole + ocr_validierung/regex_cer_wer.csv

Verwendung:
    python3 s0a_regex_korrektur.py
    python3 s0a_regex_korrektur.py --nur-stats
"""

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

# =============================================================================
# PFADE
# =============================================================================

DATEN_TXT   = Path(
    "/home/nghm/Dokumente/Zeitungsanalyse/daten_txt"
    "/wetransfer_pdf-stadtwachter_2026-03-03_2338/txt Stadtwächter"
)
ZIEL_DIR    = Path("/home/nghm/Dokumente/Zeitungsanalyse/daten_txt_regex_korrigiert")
VALIDIERUNG = Path("/home/nghm/Dokumente/Zeitungsanalyse/ocr_validierung")
LOG_CSV     = VALIDIERUNG / "regex_korrektur_log.csv"
CER_WER_CSV = VALIDIERUNG / "regex_cer_wer.csv"

ZIEL_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# KORREKTURTABELLE
# Tupel: (label, pattern, ersatz, flags)
# Reihenfolge: spezifischere Regeln zuerst
# =============================================================================

REGELN: list[tuple[str, re.Pattern, str]] = []

def _r(label: str, muster: str, ersatz: str, flags: int = 0):
    REGELN.append((label, re.compile(muster, flags), ersatz))


# ---------------------------------------------------------------------------
# GRUPPE 0 – Schutz von Abkürzungen (vor allen anderen Regeln anwenden)
# RM, Nr., etc. – werden nicht verändert; hier nur dokumentiert
# ---------------------------------------------------------------------------
# Keine aktive Ersetzung nötig – RM enthält kein 'ss' oder 'ue'

# ---------------------------------------------------------------------------
# GRUPPE 1 – ß-Wiederherstellung
# Moderne ss-Orthographie → historisches ß (1929–1931 gilt alte Rechtschreibung)
# ---------------------------------------------------------------------------

# Eigennamen zuerst (spezifisch)
_r("G1_Eigenname_Weissmann",  r"\bWeissmann\b",  "Weißmann")
_r("G1_Eigenname_weissmann",  r"\bweissmann\b",  "weißmann")

# Konkrete Vollwörter – Groß- und Kleinschreibung je einzeln
_r("G1_dass_klein",    r"\bdass\b",    "daß")
_r("G1_Dass_gross",    r"\bDass\b",    "Daß")
_r("G1_muss_klein",    r"\bmuss\b",    "muß")
_r("G1_Muss_gross",    r"\bMuss\b",    "Muß")
_r("G1_laesst",        r"\blässt\b",   "läßt")
_r("G1_Laesst",        r"\bLässt\b",   "Läßt")
_r("G1_Prozess",       r"\bProzess\b", "Prozeß")
_r("G1_prozess_klein", r"\bprozess\b", "prozeß")
_r("G1_Schluss",       r"\bSchluß\b",  "Schluß")   # bereits korrekt – kein Effekt
_r("G1_schluss_klein", r"\bschluss\b", "schluß")
# Straße: Kleinschreibung mit 'ss' → historisch 'ß'; Großschreibung bereits korrekt lassen
_r("G1_strasse_klein", r"\bstrasse\b", "straße")
# 'Straße' (korrekt) nicht anfassen – kein Eintrag nötig

# ---------------------------------------------------------------------------
# GRUPPE 2 – Fraktur-Sonderzeichen
# ---------------------------------------------------------------------------
_r("G2_langes_s",      r"ſ",           "s")          # U+017F → U+0073

# Falsch kodierte Umlaute: NFD-Sequenzen → NFC (a + combining diaeresis → ä etc.)
# Nur aktiv wenn Quelldatei NFD-kodiert ist; in NFC-Dateien kein Effekt.
_r("G2_ä_nfd",  "a\u0308", "ä")
_r("G2_o_nfd",  "o\u0308", "ö")
_r("G2_u_nfd",  "u\u0308", "ü")
_r("G2_A_nfd",  "A\u0308", "Ä")
_r("G2_O_nfd",  "O\u0308", "Ö")
_r("G2_U_nfd",  "U\u0308", "Ü")

# ---------------------------------------------------------------------------
# GRUPPE 3 – Umlaut-Ligaturen zurückführen
# Nur am Wortanfang / nach Leerzeichen / Satzzeichen → Wortgrenze reicht
# ---------------------------------------------------------------------------
_r("G3_Oeffentlich",   r"\bOeffentlich",  "Öffentlich")
_r("G3_oeffentlich",   r"\boeffentlich",  "öffentlich")
_r("G3_Aerzte",        r"\bAerzte",       "Ärzte")
_r("G3_aerzte",        r"\baerzte",       "ärzte")
_r("G3_Aerzteschaft",  r"\bAerzteschaft", "Ärzteschaft")
_r("G3_aerzteschaft",  r"\baerzteschaft", "ärzteschaft")
_r("G3_Ueber",         r"\bUeber\b",      "Über")
_r("G3_ueber",         r"\bueber\b",      "über")
_r("G3_Ae_allg",       r"\bAe([a-zäöüß])", "Ä\\1")   # Ae... am Wortanfang → Ä...
_r("G3_Oe_allg",       r"\bOe([a-zäöüß])", "Ö\\1")
_r("G3_Ue_allg",       r"\bUe([a-zäöüß])", "Ü\\1")

# =============================================================================
# HILFSFUNKTIONEN
# =============================================================================

def korrigiere_text(text: str) -> tuple[str, dict[str, int]]:
    """Wendet alle Regeln auf `text` an. Gibt korrigierten Text + Zähldict zurück."""
    zaehler: dict[str, int] = defaultdict(int)
    for label, pat, ersatz in REGELN:
        neu, n = pat.subn(ersatz, text)
        if n:
            zaehler[label] += n
        text = neu
    return text, dict(zaehler)


def tokenize(text: str) -> list[str]:
    return re.findall(r"\S+", text.lower())


def cer(ref: str, hyp: str) -> float:
    """Zeichenfehlerrate (Levenshtein auf Zeichen)."""
    r, h = list(ref), list(hyp)
    return _edit_distance(r, h) / max(len(r), 1) * 100


def wer(ref: str, hyp: str) -> float:
    """Wortfehlerrate (Levenshtein auf Tokens)."""
    r, h = tokenize(ref), tokenize(hyp)
    return _edit_distance(r, h) / max(len(r), 1) * 100


def _edit_distance(a: list, b: list) -> int:
    m, n = len(a), len(b)
    # Speicheroptimiert: nur zwei Zeilen
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        curr = [i] + [0] * n
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1]
            else:
                curr[j] = 1 + min(prev[j], curr[j - 1], prev[j - 1])
        prev = curr
    return prev[n]


def lade_text(pfad: Path) -> str:
    """Lädt Textdatei, ignoriert Kommentarzeilen (# ...)."""
    zeilen = pfad.read_text(encoding="utf-8").splitlines()
    return "\n".join(z for z in zeilen if not z.strip().startswith("#"))


# =============================================================================
# VALIDIERUNGSSET – Mapping Ordnername → ocr_text.txt
# =============================================================================

VALIDIERUNGSSET = [
    "1929_Ausgabe_01", "1929_Ausgabe_06", "1929_Ausgabe_14", "1929_Ausgabe_29",
    "1930_Ausgabe_01", "1930_Ausgabe_09", "1930_Ausgabe_16", "1930_Ausgabe_24",
    "1930_Ausgabe_32", "1930_Ausgabe_45", "1930_Ausgabe_56",
    "1931_Ausgabe_01", "1931_Ausgabe_10", "1931_Ausgabe_20",
]


# =============================================================================
# HAUPTFUNKTIONEN
# =============================================================================

def verarbeite_korpus(zaehler_gesamt: dict[str, int]) -> int:
    """Korrigiert alle .txt-Dateien in DATEN_TXT (inkl. Unterordner) → ZIEL_DIR."""
    dateien = sorted(DATEN_TXT.rglob("*.txt"))
    if not dateien:
        print(f"[WARN] Keine .txt-Dateien in {DATEN_TXT} gefunden.", file=sys.stderr)
        return 0

    for src in dateien:
        try:
            text = src.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = src.read_text(encoding="latin-1")

        korr, zaehler = korrigiere_text(text)

        # Unterordnerstruktur (1929/, 1930/, 1931/) im Zielverzeichnis spiegeln
        relativ = src.relative_to(DATEN_TXT)
        ziel = ZIEL_DIR / relativ
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(korr, encoding="utf-8")

        for k, v in zaehler.items():
            zaehler_gesamt[k] = zaehler_gesamt.get(k, 0) + v

    print(f"  → {len(dateien)} Dateien korrigiert → {ZIEL_DIR}")
    return len(dateien)


def schreibe_log(zaehler_gesamt: dict[str, int]):
    """Schreibt regex_korrektur_log.csv."""
    zeilen = sorted(zaehler_gesamt.items(), key=lambda x: -x[1])
    with LOG_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Regel", "Anzahl_Ersetzungen"])
        for label, n in zeilen:
            w.writerow([label, n])
        w.writerow(["GESAMT", sum(zaehler_gesamt.values())])
    print(f"  → Log geschrieben: {LOG_CSV}")


def cer_wer_vergleich() -> list[dict]:
    """CER/WER vorher/nachher auf allen Validierungsordnern."""
    ergebnisse = []
    for name in VALIDIERUNGSSET:
        d = VALIDIERUNG / name
        gt_pfad  = d / "ground_truth.txt"
        ocr_pfad = d / "ocr_text.txt"
        if not (gt_pfad.exists() and ocr_pfad.exists()):
            continue

        gt_text  = lade_text(gt_pfad)
        ocr_text = lade_text(ocr_pfad)
        korr_text, _ = korrigiere_text(ocr_text)

        ergebnisse.append({
            "Ausgabe":   name,
            "CER_vor":   round(cer(gt_text, ocr_text), 2),
            "WER_vor":   round(wer(gt_text, ocr_text), 2),
            "CER_nach":  round(cer(gt_text, korr_text), 2),
            "WER_nach":  round(wer(gt_text, korr_text), 2),
        })

    # Durchschnitte
    if ergebnisse:
        n = len(ergebnisse)
        ergebnisse.append({
            "Ausgabe":  f"DURCHSCHNITT ({n})",
            "CER_vor":  round(sum(r["CER_vor"]  for r in ergebnisse) / n, 2),
            "WER_vor":  round(sum(r["WER_vor"]  for r in ergebnisse) / n, 2),
            "CER_nach": round(sum(r["CER_nach"] for r in ergebnisse) / n, 2),
            "WER_nach": round(sum(r["WER_nach"] for r in ergebnisse) / n, 2),
        })
    return ergebnisse


def drucke_cer_wer_tabelle(ergebnisse: list[dict]):
    print("\n" + "=" * 72)
    print("CER / WER – VORHER / NACHHER (Regex-Korrektur)")
    print("=" * 72)
    print(f"{'Ausgabe':<26} {'CER vor':>8} {'CER nach':>9} {'ΔCER':>7} "
          f"{'WER vor':>8} {'WER nach':>9} {'ΔWER':>7}")
    print("-" * 72)
    for r in ergebnisse:
        delta_cer = r["CER_nach"] - r["CER_vor"]
        delta_wer = r["WER_nach"] - r["WER_vor"]
        marker = "◀" if r["Ausgabe"].startswith("DURCH") else ""
        print(f"{r['Ausgabe']:<26} {r['CER_vor']:>7.2f}% {r['CER_nach']:>8.2f}% "
              f"{delta_cer:>+6.2f}% {r['WER_vor']:>7.2f}% {r['WER_nach']:>8.2f}% "
              f"{delta_wer:>+6.2f}% {marker}")


def schreibe_cer_wer_csv(ergebnisse: list[dict]):
    with CER_WER_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["Ausgabe", "CER_vor", "WER_vor", "CER_nach", "WER_nach"])
        w.writeheader()
        w.writerows(ergebnisse)
    print(f"  → CER/WER-Tabelle: {CER_WER_CSV}")


def zeige_beispiele(n: int = 5):
    """Zeigt n Vorher/Nachher-Satzpaare aus den Validierungsdateien."""
    print("\n" + "=" * 72)
    print("VORHER / NACHHER – 5 BEISPIELSÄTZE")
    print("=" * 72)

    gezeigt = 0
    for name in VALIDIERUNGSSET:
        if gezeigt >= n:
            break
        ocr_pfad = VALIDIERUNG / name / "ocr_text.txt"
        if not ocr_pfad.exists():
            continue

        ocr_text = lade_text(ocr_pfad)
        korr_text, zaehler = korrigiere_text(ocr_text)
        if not zaehler:
            continue  # keine Änderung → überspringen

        # Suche Satz mit Änderung
        saetze_vor  = re.split(r"(?<=[.!?])\s+", ocr_text)
        saetze_nach = re.split(r"(?<=[.!?])\s+", korr_text)

        for s_vor, s_nach in zip(saetze_vor, saetze_nach):
            if s_vor != s_nach and len(s_vor.split()) >= 5:
                print(f"\n[{name}]")
                print(f"  VORHER : {s_vor.strip()[:200]}")
                print(f"  NACHHER: {s_nach.strip()[:200]}")
                gezeigt += 1
                break

        if gezeigt >= n:
            break


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Regex-Post-OCR-Korrektur")
    parser.add_argument("--nur-stats", action="store_true",
                        help="Nur CER/WER-Vergleich, keine Dateiverarbeitung")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  s0a_regex_korrektur.py – Regelbasierte OCR-Nachkorrektur   ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"  Regeln aktiv: {len(REGELN)}")

    zaehler_gesamt: dict[str, int] = {}

    if not args.nur_stats:
        print("\n[1/4] Verarbeite Korpus …")
        n = verarbeite_korpus(zaehler_gesamt)

        print("\n[2/4] Schreibe Ersetzungslog …")
        schreibe_log(zaehler_gesamt)

        # Kompakte Konsolausgabe der Ersetzungsstatistik
        gesamt = sum(zaehler_gesamt.values())
        print(f"\n  Ersetzungsstatistik (Top 15, gesamt {gesamt:,} Ersetzungen):")
        print(f"  {'Regel':<35} {'Anzahl':>8}")
        print(f"  {'-'*43}")
        for label, cnt in sorted(zaehler_gesamt.items(), key=lambda x: -x[1])[:15]:
            print(f"  {label:<35} {cnt:>8,}")
    else:
        print("  [--nur-stats] Überspringe Korpus-Verarbeitung.")

    print("\n[3/4] CER/WER-Vergleich auf Validierungsset …")
    ergebnisse = cer_wer_vergleich()
    drucke_cer_wer_tabelle(ergebnisse)
    schreibe_cer_wer_csv(ergebnisse)

    print("\n[4/4] Beispielsätze …")
    zeige_beispiele(5)

    print("\n✓ Fertig.")


if __name__ == "__main__":
    main()
