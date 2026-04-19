#!/usr/bin/env python3
"""
metadaten_extraktion.py – Automatische Metadaten-Extraktion für den Stadtwächter-Korpus
========================================================================================
Datenquellen:
  1. pipeline/data/processed/corpus_lemmatized.parquet  (autoritative Ausgabenliste)
  2. Volltext der .txt-Datei  (Datum, Wochentag, Ausgabenummer im Kopf)
  3. PDF-Datei via pdfinfo  (Seitenzahl)
  4. ocr_validierung/ergebnisse_ocr_validierung.csv  (CER/WER wo vorhanden)

Ausgabe:
  ergebnisse/metadaten_korpus.csv
"""

import csv
import re
import subprocess
import sys
from pathlib import Path

# =============================================================================
# PFADE
# =============================================================================

BASE = Path("/home/nghm/Dokumente/Zeitungsanalyse")

TXT_DIR = (
    BASE / "daten_txt"
    / "wetransfer_pdf-stadtwachter_2026-03-03_2338"
    / "txt Stadtwächter"
)
PDF_DIR = (
    BASE / "daten_pdf"
    / "wetransfer_pdf-stadtwachter_2026-03-03_2338"
    / "pdf Stadtwächter"
)
PARQUET = BASE / "pipeline" / "data" / "processed" / "corpus_lemmatized.parquet"
OCR_CSV = BASE / "ocr_validierung" / "ergebnisse_ocr_validierung.csv"
ERGEBNIS_CSV = BASE / "ergebnisse" / "metadaten_korpus.csv"

# =============================================================================
# MONATSNAMEN → Monatsnummer
# =============================================================================

MONATE = {
    "januar": 1,  "februar": 2,  "märz": 3,    "april": 4,
    "mai": 5,     "juni": 6,     "juli": 7,    "august": 8,
    "september": 9, "oktober": 10, "november": 11, "dezember": 12,
    # Abkürzungen / Tippvarianten
    "jan": 1, "feb": 2, "mär": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dez": 12,
}

WOCHENTAGE_DE = {
    "montag": "Montag",   "dienstag": "Dienstag", "mittwoch": "Mittwoch",
    "donnerstag": "Donnerstag", "freitag": "Freitag",
    "samstag": "Samstag", "sonnabend": "Samstag",   # Sonnabend = regional für Samstag
    "sonntag": "Sonntag",
}

# =============================================================================
# HILFSFUNKTIONEN: Datei-Auflösung
# =============================================================================

def finde_txt(doc_id: str, year: int | None) -> Path | None:
    """
    Sucht die .txt-Datei für einen doc_id. Strategien:
    1. TXT_DIR/{year}/{doc_id}.txt  (Normalfall)
    2. TXT_DIR/{doc_id}.txt         (root-Ebene, NaN-Year)
    3. Suffix -N abschneiden        (08. Ausgabe 1930-1 → 08. Ausgabe 1930)
    4. rglob mit normiertem Präfix  (letzter Ausweg)
    """
    # 1. Exakt in Jahresordner
    if year is not None:
        p = TXT_DIR / str(year) / f"{doc_id}.txt"
        if p.exists():
            return p

    # 2. Root-Ebene
    p = TXT_DIR / f"{doc_id}.txt"
    if p.exists():
        return p

    # 3. Suffix -N abschneiden (z.B. "08. Ausgabe 1930-1" → "08. Ausgabe 1930")
    stripped = re.sub(r"-\d+$", "", doc_id)
    if stripped != doc_id:
        if year is not None:
            p = TXT_DIR / str(year) / f"{stripped}.txt"
            if p.exists():
                return p
        p = TXT_DIR / f"{stripped}.txt"
        if p.exists():
            return p

    # 4. rglob-Suche nach Präfix (erste 15 Zeichen)
    prefix = doc_id[:15].rstrip()
    if year is not None:
        hits = sorted((TXT_DIR / str(year)).glob(f"{prefix}*.txt"))
        if hits:
            return hits[0]
    hits = sorted(TXT_DIR.rglob(f"{prefix}*.txt"))
    # .venv ausschließen
    hits = [h for h in hits if ".venv" not in h.parts]
    if hits:
        return hits[0]

    return None


def finde_pdf(doc_id: str, year: int | None) -> Path | None:
    """Sucht die passende PDF-Datei (flaches Verzeichnis)."""
    # 1. Exakte Übereinstimmung
    p = PDF_DIR / f"{doc_id}.pdf"
    if p.exists():
        return p

    # 2. Suffix abschneiden
    stripped = re.sub(r"-\d+$", "", doc_id)
    p = PDF_DIR / f"{stripped}.pdf"
    if p.exists():
        return p

    # 3. Suche nach Präfix
    prefix = doc_id[:15].rstrip()
    hits = sorted(PDF_DIR.glob(f"{prefix}*.pdf"))
    if hits:
        return hits[0]

    return None


# =============================================================================
# HILFSFUNKTIONEN: Metadaten-Extraktion
# =============================================================================

def extrahiere_ausgabe_nr(doc_id: str, year: int | None) -> int | None:
    """
    Extrahiert die Ausgabennummer aus dem doc_id (Dateinamen).
    Muster (von spezifisch nach allgemein):
      - "OCR 1. 1929 ..."   → 1
      - "OCR 10 1929 ..."   → 10
      - "01. Ausgabe 1930"  → 1
      - "6. Korrekt 1929"   → 6
    """
    # "OCR N." oder "OCR N " am Anfang
    m = re.match(r"^OCR\s+(\d+)", doc_id)
    if m:
        return int(m.group(1))

    # Führende Zahl mit optionalem Buchstaben-Suffix "N." / "Na " (z.B. "34a")
    m = re.match(r"^(\d+)[a-z]?[.\s]", doc_id, re.IGNORECASE)
    if m:
        return int(m.group(1))

    return None


_DATUM_MUSTER = [
    # "Sonntag, den 7. Juli 1929" / "Osnabrück, Sonntag, den 7. Juli 1929"
    re.compile(
        r"(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonnabend|Sonntag)"
        r",\s+den\s+(\d{1,2})\.\s+(\w+)\s+(\d{4})",
        re.IGNORECASE,
    ),
    # "Osnabrück, den 5. Januar 1930"
    re.compile(
        r"Osnabrück,\s+den\s+(\d{1,2})\.\s+(\w+)\s+(\d{4})",
        re.IGNORECASE,
    ),
    # "vom 28. April 1929" (KI-Preamble)
    re.compile(
        r"vom\s+(\d{1,2})\.\s+(\w+)\s+(\d{4})",
        re.IGNORECASE,
    ),
    # "– 16. Februar 1930" (nach Gedankenstrich)
    re.compile(
        r"[–\-]\s+(\d{1,2})\.\s+(\w+)\s+(\d{4})",
        re.IGNORECASE,
    ),
    # Numerisches Datum "16. 02. 1930" oder "16.02.1930"
    re.compile(
        r"(\d{1,2})\.\s*(\d{1,2})\.\s*(19[23]\d)",
    ),
]


def extrahiere_datum(text: str, year_hint: int | None) -> dict:
    """
    Durchsucht die ersten 3000 Zeichen auf Datumsmuster.
    Gibt {'datum': str, 'datum_iso': str, 'wochentag': str} zurück.
    """
    snippet = text[:3000]

    for pat in _DATUM_MUSTER:
        m = pat.search(snippet)
        if not m:
            continue
        groups = m.groups()

        # Muster 1: Wochentag, Tag, Monat-Name, Jahr
        if len(groups) == 4 and groups[0].lower() in WOCHENTAGE_DE:
            wt, tag, monat_str, jahr_str = groups
            monat_nr = MONATE.get(monat_str.lower())
            if monat_nr and (year_hint is None or abs(int(jahr_str) - year_hint) <= 2):
                tag_i, monat_i, jahr_i = int(tag), monat_nr, int(jahr_str)
                return {
                    "datum":     f"{tag_i}. {monat_str.capitalize()} {jahr_i}",
                    "datum_iso": f"{jahr_i:04d}-{monat_i:02d}-{tag_i:02d}",
                    "wochentag": WOCHENTAGE_DE.get(wt.lower(), wt.capitalize()),
                }

        # Muster 2/3/4: Tag, Monat-Name, Jahr (kein Wochentag in Match)
        if len(groups) == 3:
            tag_s, monat_s, jahr_s = groups
            # Numerisch?
            if monat_s.isdigit():
                tag_i, monat_i, jahr_i = int(tag_s), int(monat_s), int(jahr_s)
            else:
                monat_i = MONATE.get(monat_s.lower())
                if not monat_i:
                    continue
                tag_i, jahr_i = int(tag_s), int(jahr_s)

            if year_hint and abs(jahr_i - year_hint) > 2:
                continue  # falsches Jahr (Toleranz ±2 für Fehlzuordnungen in Dateinamen)

            # Wochentag aus Datum berechnen
            try:
                import datetime
                dt = datetime.date(jahr_i, monat_i, tag_i)
                wt = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
                      "Freitag", "Samstag", "Sonntag"][dt.weekday()]
                monat_name = [
                    "", "Januar", "Februar", "März", "April", "Mai", "Juni",
                    "Juli", "August", "September", "Oktober", "November", "Dezember"
                ][monat_i]
                return {
                    "datum":     f"{tag_i}. {monat_name} {jahr_i}",
                    "datum_iso": f"{jahr_i:04d}-{monat_i:02d}-{tag_i:02d}",
                    "wochentag": wt,
                }
            except ValueError:
                continue

    # Kein Treffer – Wochentag aus Volltext raten
    wt_gefunden = ""
    for wt_lower, wt_schoen in WOCHENTAGE_DE.items():
        if re.search(rf"\b{wt_lower}\b", snippet, re.IGNORECASE):
            wt_gefunden = wt_schoen
            break

    return {"datum": "", "datum_iso": "", "wochentag": wt_gefunden}


def seitenzahl_pdf(pdf_pfad: Path) -> int | None:
    """Ruft pdfinfo auf und liest die Seitenzahl aus."""
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_pfad)],
            capture_output=True, text=True, timeout=10,
        )
        m = re.search(r"Pages:\s+(\d+)", result.stdout)
        if m:
            return int(m.group(1))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


# =============================================================================
# OCR-QUALITÄT LADEN
# =============================================================================

def lade_ocr_qualitaet() -> dict[tuple[int, int], dict]:
    """Gibt {(jahr, ausgabe_nr): {cer, wer}} zurück."""
    result = {}
    if not OCR_CSV.exists():
        return result
    with OCR_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                j, a = int(row["Jahr"]), int(row["Ausgabe"])
                result[(j, a)] = {
                    "ocr_cer": float(row["CER_%"]),
                    "ocr_wer": float(row["WER_%"]),
                }
            except (ValueError, KeyError):
                pass
    return result


# =============================================================================
# HAUPTPROGRAMM
# =============================================================================

def main():
    try:
        import pandas as pd
    except ImportError:
        sys.exit("Fehler: pandas nicht installiert.")

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  metadaten_extraktion.py – Stadtwächter-Korpus              ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    df = pd.read_parquet(PARQUET)
    print(f"  Parquet geladen: {len(df)} Einträge\n")

    ocr_q = lade_ocr_qualitaet()

    felder = [
        "ausgabe_nr", "jahrgang", "datum", "datum_iso", "wochentag",
        "seitenzahl", "tokens_gesamt", "tokens_gefiltert",
        "dateiname_txt", "dateiname_pdf",
        "ocr_cer", "ocr_wer",
    ]
    ergebnisse = []

    stats = {"txt_gefunden": 0, "pdf_gefunden": 0, "datum_gefunden": 0, "vollstaendig": 0}

    for _, row in df.iterrows():
        doc_id = row["doc_id"]
        year   = int(row["year"]) if pd.notna(row["year"]) else None

        # ── Ausgabennummer ─────────────────────────────────────────────────
        ausgabe_nr = extrahiere_ausgabe_nr(doc_id, year)

        # ── TXT-Datei ──────────────────────────────────────────────────────
        txt_pfad = finde_txt(doc_id, year)
        dateiname_txt = txt_pfad.name if txt_pfad else ""
        if txt_pfad:
            stats["txt_gefunden"] += 1

        # ── Datum aus Volltext ─────────────────────────────────────────────
        datum_info = {"datum": "", "datum_iso": "", "wochentag": ""}
        if txt_pfad:
            try:
                text = txt_pfad.read_text(encoding="utf-8", errors="replace")
            except Exception:
                text = ""
            datum_info = extrahiere_datum(text, year)
            if datum_info["datum"]:
                stats["datum_gefunden"] += 1

        # ── PDF-Datei + Seitenzahl ─────────────────────────────────────────
        pdf_pfad = finde_pdf(doc_id, year)
        dateiname_pdf = pdf_pfad.name if pdf_pfad else ""
        seitenzahl = seitenzahl_pdf(pdf_pfad) if pdf_pfad else None
        if pdf_pfad:
            stats["pdf_gefunden"] += 1

        # ── Token-Zählungen aus Parquet ────────────────────────────────────
        tokens_gesamt   = int(row["n_raw_tokens"]) if pd.notna(row.get("n_raw_tokens")) else None
        tokens_gefiltert = int(row["n_tokens"])     if pd.notna(row.get("n_tokens"))     else None

        # ── OCR-Qualität ───────────────────────────────────────────────────
        ocr_entry = ocr_q.get((year, ausgabe_nr), {}) if (year and ausgabe_nr) else {}

        eintrag = {
            "ausgabe_nr":       ausgabe_nr,
            "jahrgang":         year,
            "datum":            datum_info["datum"],
            "datum_iso":        datum_info["datum_iso"],
            "wochentag":        datum_info["wochentag"],
            "seitenzahl":       seitenzahl,
            "tokens_gesamt":    tokens_gesamt,
            "tokens_gefiltert": tokens_gefiltert,
            "dateiname_txt":    dateiname_txt,
            "dateiname_pdf":    dateiname_pdf,
            "ocr_cer":          ocr_entry.get("ocr_cer", ""),
            "ocr_wer":          ocr_entry.get("ocr_wer", ""),
        }
        ergebnisse.append(eintrag)

        # Vollständigkeits-Check
        vollst = all([
            ausgabe_nr is not None,
            year is not None,
            datum_info["datum"],
            seitenzahl is not None,
            tokens_gesamt is not None,
        ])
        if vollst:
            stats["vollstaendig"] += 1

    # ── Sortierung ──────────────────────────────────────────────────────────
    ergebnisse.sort(key=lambda e: (
        e["jahrgang"] or 9999,
        e["ausgabe_nr"] or 9999,
        e["dateiname_txt"],
    ))

    # ── CSV speichern ────────────────────────────────────────────────────────
    ERGEBNIS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with ERGEBNIS_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=felder)
        w.writeheader()
        w.writerows(ergebnisse)
    print(f"  CSV gespeichert: {ERGEBNIS_CSV}\n")

    # ── Statistik ────────────────────────────────────────────────────────────
    n = len(ergebnisse)
    print("─" * 60)
    print(f"  Gesamt Ausgaben:         {n}")
    print(f"  TXT-Datei gefunden:      {stats['txt_gefunden']}/{n}")
    print(f"  PDF-Datei gefunden:      {stats['pdf_gefunden']}/{n}")
    print(f"  Datum extrahiert:        {stats['datum_gefunden']}/{n}")
    print(f"  OCR-Qualität vorhanden:  {len(ocr_q)}")
    print(f"  Vollständige Einträge:   {stats['vollstaendig']}/{n}  "
          f"({stats['vollstaendig']/n*100:.1f} %)")
    print("─" * 60)

    # ── Vorschau: erste 10 Zeilen ─────────────────────────────────────────────
    print("\n  VORSCHAU – erste 10 Einträge:")
    print(f"  {'Nr':>3} {'Jahr':>5} {'Datum':<20} {'Wochentag':<12} "
          f"{'Seiten':>7} {'Tokens':>8} {'TXT-Datei':<35}")
    print("  " + "─" * 95)
    for e in ergebnisse[:10]:
        print(f"  {str(e['ausgabe_nr'] or '?'):>3} "
              f"{str(e['jahrgang'] or '?'):>5} "
              f"{e['datum']:<20} "
              f"{e['wochentag']:<12} "
              f"{str(e['seitenzahl'] or '?'):>7} "
              f"{str(e['tokens_gesamt'] or '?'):>8} "
              f"{e['dateiname_txt'][:35]:<35}")

    # Fehlende Daten melden
    ohne_datum = [e for e in ergebnisse if not e["datum"]]
    if ohne_datum:
        print(f"\n  Ausgaben ohne extrahiertes Datum ({len(ohne_datum)}):")
        for e in ohne_datum:
            print(f"    [{e['jahrgang']} / Nr. {e['ausgabe_nr']}] {e['dateiname_txt']}")

    print("\n✓ Fertig.")


if __name__ == "__main__":
    main()
