#!/usr/bin/env python3
"""
pdf_zu_txt.py
Durchsucht den Ordner 'daten_pdf' rekursiv, extrahiert den Text aus jeder
PDF-Datei und speichert ihn als gleichnamige .txt-Datei in 'daten_txt',
wobei die Unterordner-Struktur exakt gespiegelt wird.
"""

import sys
import os
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("Fehler: pdfplumber ist nicht installiert.", file=sys.stderr)
    print("Hinweis: pip install pdfplumber", file=sys.stderr)
    sys.exit(1)

# Pfade relativ zum Projektverzeichnis (zwei Ebenen über diesem Skript)
SKRIPT_DIR = Path(__file__).parent.resolve()
ROOT_DIR   = SKRIPT_DIR.parent          # /…/Zeitungsanalyse
EINGABE    = ROOT_DIR / "daten_pdf"
AUSGABE    = ROOT_DIR / "daten_txt"

AUSGABE.mkdir(exist_ok=True)

pdfs = sorted(EINGABE.rglob("*.pdf"))

if not pdfs:
    print(f"Keine PDF-Dateien in '{EINGABE}' (inkl. Unterordner) gefunden.")
    sys.exit(0)

print(f"{len(pdfs)} PDF-Datei(en) gefunden.\n")

fehler = 0
for pdf_pfad in pdfs:
    rel_pfad = pdf_pfad.relative_to(EINGABE)
    txt_pfad = AUSGABE / rel_pfad.with_suffix(".txt")
    txt_pfad.parent.mkdir(parents=True, exist_ok=True)

    print(f"  Verarbeite: {rel_pfad} ...", end=" ", flush=True)
    try:
        seiten = []
        with pdfplumber.open(pdf_pfad) as pdf:
            for seite in pdf.pages:
                text = seite.extract_text()
                if text:
                    seiten.append(text)
        inhalt = "\n\n".join(seiten)
        txt_pfad.write_text(inhalt, encoding="utf-8")
        print(f"OK  →  {txt_pfad.name}  ({len(seiten)} Seite(n), {len(inhalt):,} Zeichen)")
    except Exception as e:
        print(f"FEHLER: {e}")
        fehler += 1

print()
if fehler:
    print(f"Abgeschlossen mit {fehler} Fehler(n).")
    sys.exit(1)
else:
    print(f"Fertig! Alle {len(pdfs)} PDFs erfolgreich nach '{AUSGABE}' konvertiert.")
