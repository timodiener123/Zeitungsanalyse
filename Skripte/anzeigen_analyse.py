#!/usr/bin/env python3
"""
Anzeigen-Analyse – Stadtwächter Osnabrück (~1930)
Ziel: Identifikation von Werbekunden (Firmen/Personen) in Anzeigenabschnitten.

Zwei Extraktionsebenen:
  1. Präzise Regex-Extraktion aus der Bullet-Struktur der Anzeigenrubriken
  2. spaCy-NER auf dem ungefilterten Anzeigentext (ORG/PER) als Ergänzung

Speicher: strikt eine Datei nach der anderen, sofortiger GC nach jeder Datei.
"""

import gc
import re
import csv
from pathlib import Path
from collections import Counter

import spacy

# ── Konfiguration ─────────────────────────────────────────────────────────────

DATA_DIR    = Path('daten_txt')
AUSGABE_DIR = Path('ergebnisse')
AUSGABE_DIR.mkdir(parents=True, exist_ok=True)

# ── Sektionserkennung ─────────────────────────────────────────────────────────

# Alle im Korpus vorkommenden Header-Varianten für Anzeigensektionen
ANZEIGEN_START_RE = re.compile(
    r'^(anzeigenmarkt|weitere anzeigen|anzeigenteil|'
    r'kleiner anzeigenteil|kleine anzeigen|'
    r'anzeigen und kleinanzeigen|bekanntmachungen und anzeigen|'
    r'geschäftliches|inserate|reklame-?markt|'
    r'\[anzeige\]|● kleine anzeigen|^anzeigen$|^ANZEIGEN$)',
    re.IGNORECASE
)
# Header, der eine neue *redaktionelle* Sektion einleitet (= Anzeigen-Ende)
EDITORIAL_END_RE = re.compile(
    r'^(--- seite|kopfzeile:|impressum:|Der Stadt-Wächter –|'
    r'PAGE \d|Seite \d|Lohndruck:)',
    re.IGNORECASE
)

# ── Bullet-Erkennung und Namensextraktion ─────────────────────────────────────

BULLET_LINE_RE = re.compile(r'^[●•◆]\s*(.+)')

def extrahiere_namen_aus_bullet(inhalt: str) -> list[str]:
    """
    Zwei Muster im Stadtwächter-Anzeigenmarkt:

    Muster A – Direkteintrag (hat Komma vor erstem Doppelpunkt):
      'W. Becker, Herrenteichstr. 9: ist ein christliches Geschäft.'
      → Name vor erstem Komma: 'W. Becker'

    Muster B – Kategorie-Eintrag (kein Komma vor Doppelpunkt):
      'Möbel: Joh. Möllenkamp, Lohstr. 62; Bodden, Klingensberg 4'
      → Namen nach Doppelpunkt, getrennt durch Semikolon; jeweils vor Komma
    """
    namen = []
    colon_pos   = inhalt.find(':')
    comma_before = inhalt.find(',')

    if colon_pos == -1:
        # Kein Doppelpunkt → ganzer Eintrag ist ein Name (falls sinnvoll)
        kandidat = inhalt.split(',')[0].split('/')[0].strip()
        n = bereinige_name(kandidat)
        if n:
            namen.append(n)
        return namen

    vor_doppelpunkt = inhalt[:colon_pos]

    if comma_before != -1 and comma_before < colon_pos:
        # Muster A: Name, Adresse: Beschreibung
        kandidat = vor_doppelpunkt.split(',')[0].strip()
        n = bereinige_name(kandidat)
        if n:
            namen.append(n)
    else:
        # Muster B: Kategorie: Name1, Adr1; Name2, Adr2
        nach_doppelpunkt = inhalt[colon_pos + 1:]
        for teil in nach_doppelpunkt.split(';'):
            kandidat = teil.split(',')[0].strip()
            n = bereinige_name(kandidat)
            if n:
                namen.append(n)

    return namen

# ── Filterlisten ──────────────────────────────────────────────────────────────

# Deutsche Großstädte (häufige Falsch-Positive durch NER)
_STAEDTE = {
    'hamburg', 'berlin', 'münchen', 'köln', 'frankfurt', 'stuttgart',
    'düsseldorf', 'dortmund', 'essen', 'bremen', 'leipzig', 'dresden',
    'hannover', 'nürnberg', 'breslau', 'stettin', 'königsberg', 'magdeburg',
    'halle', 'mannheim', 'kiel', 'erfurt', 'lübeck', 'mainz', 'augsburg',
    'osnabrück', 'münster', 'bielefeld', 'kassel',
}
# Wochentage (erscheinen in Spielplänen / Kino-Bulletins)
_WOCHENTAGE = {
    'montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag',
    'sonnabend', 'samstag', 'sonntag',
}
# Generische Kategorie-/Warenbegriffe (kein Firmenname)
_KATEGORIEN = {
    'möbel', 'schuhe', 'uhren', 'lebensmittel', 'fahrräder', 'fahrrad',
    'musik', 'klaviere', 'autoruf', 'autovermietung', 'hypotheken',
    'damen', 'herren', 'kleinanzeigen', 'pelze', 'strümpfe', 'wäsche',
    'obst', 'gemüse', 'bäckerei', 'metzgerei', 'buchhandlung', 'optik',
    'photographien', 'schreibwaren', 'spielwaren',
    'elektro', 'radio', 'rundfunk', 'gaststätte', 'restaurant', 'café',
    'hotel', 'pension', 'kolonialwaren', 'eisenwaren', 'tapeten',
    'farben', 'lacke', 'papier', 'druck', 'buchdruckerei',
    'reformschuhe', 'reformhaus', 'damen-mäntel', 'damen-hüte',
    'herren-kleidung', 'herrenkleidung', 'schirme', 'besoldungsgruppe',
    'hafer', 'mehl', 'kohlen', 'holz', 'heizung', 'klempnerei',
    # Produkte/Rohstoffe aus Kleinanzeigen
    'waschfässer', 'gardinen', 'betten', 'polsterwaren', 'lumpen',
    'weizen', 'kartoffeln', 'koks', 'spiritus', 'benzin',
    'nervenstärkend', 'imprägnol',
    # Stellenanzeigen-Marker
    'arbeitsloser', 'schlosser', 'zimmermann', 'lehrling',
    # Sonstiges
    'garage', 'wohnung',
}
# Redaktionelle Entitäten (kein Werbekunde)
_REDAKTION = {
    'stadtwächter', 'stadt-wächter', 'stadt wächter',
    'drei stern verlag', 'lohndruck', 'lohndruckerei',
    'stadt-wächter-tropfen', 'osnabrücker buchdruckerei',
    'reichstag', 'reichsregierung', 'reichsbank', 'stadtrat',
    'bürgermeister', 'zentrum', 'deutschland', 'deutsches reich',
    'preußen', 'reichswehr', 'nazi', 'nationalsozialisten',
    'dr. schierbaum', 'schierbaum',
}
# Kurze Einzel-Tokens die NER fälschlicherweise als PER/ORG erkennt
_FALSCHE_TOKENS = {
    'nie', 'sohn', 'söhne', 'pfg', 'mk', 'rm', 'tel', 'nr', 'inh',
    'gmbh', 'ag', 'co', 'kg', 'ohg', 'lohndruckerei',
    'lohstr', 'johannisstr', 'großestr', 'hasestr', 'bierstr',
    'dielingerstr', 'marienstr', 'goldstr', 'klingensberg',
    'gildewart', 'krahnstr', 'wittekindstr', 'schlagvorderstr',
    'herrenteichstr', 'dielingerstraße',
    # NER-Artefakte aus Anzeigentext
    'schriftl', 'schriftleitung', 'h. schierbaum', 'schriftleiter',
    'unterstützt', 'empfiehlt',
}
# Alles zusammen
BLACKLIST = _STAEDTE | _WOCHENTAGE | _KATEGORIEN | _REDAKTION | _FALSCHE_TOKENS

_ONLY_NONWORD = re.compile(r'^[\d\s\.\-,/:()\[\]!?&|]+$')
_WHITESPACE   = re.compile(r'\s+')

_PAREN_ADDR_RE = re.compile(r'\s*\([^)]*\)\s*$')   # "(Johannisstr. 35)" am Ende

def bereinige_name(text: str) -> str:
    """Normalisiert und validiert einen Namenskandidaten."""
    # Adressangaben in Klammern am Namensende entfernen
    text = _PAREN_ADDR_RE.sub('', text)
    text = _WHITESPACE.sub(' ', text).strip(' .,-;:●•')

    # Länge (Satzfragmente > 55 Zeichen raus)
    if len(text) < 3 or len(text) > 55:
        return ''
    # Nur Zahlen/Satzzeichen
    if _ONLY_NONWORD.match(text):
        return ''
    # Enthält Ausrufe- oder Fragezeichen → Werbetext-Fragment, kein Name
    if '!' in text or '?' in text:
        return ''
    # Muss mit Großbuchstabe beginnen (deutsche Eigennamen)
    if not text[0].isupper():
        return ''
    # Blacklist (case-insensitive)
    low = text.lower()
    if low in BLACKLIST:
        return ''
    # Einzel-Stoppwörter
    if low in {'der', 'die', 'das', 'ein', 'eine', 'und', 'oder', 'für',
               'bei', 'mit', 'vom', 'von', 'zu', 'an', 'in', 'auf', 'als',
               'nach', 'seit', 'unter', 'über', 'vor', 'durch'}:
        return ''
    # Keine reinen Straßennamen (enden auf -str., -straße, -gasse)
    if re.search(r'(straße|str\.|gasse|weg|platz|allee)\s*\d*$', low):
        return ''
    # Kein reines Abkürzungs-Token (nur 1-3 Buchstaben + Punkt)
    if re.match(r'^[A-Za-z]{1,3}\.$', text):
        return ''
    return text

# ── spaCy einmalig laden ──────────────────────────────────────────────────────

print("Lade spaCy-Modell (tok2vec + ner) …", flush=True)
nlp = spacy.load(
    'de_core_news_sm',
    exclude=['tagger', 'morphologizer', 'parser', 'lemmatizer', 'attribute_ruler'],
)
nlp.max_length = 300_000
print("Modell geladen.\n", flush=True)

# ── Dateiverarbeitung ─────────────────────────────────────────────────────────

def verarbeite_datei(pfad: Path,
                     bullet_cnt: Counter,
                     ner_cnt: Counter,
                     ner_typ: dict,
                     anmerk_cnt: dict) -> tuple[int, int]:
    """
    Liest genau eine Datei, extrahiert Werbekunden aus Anzeigenabschnitten.
    Gibt (bullet_treffer, ner_treffer) zurück.
    """
    try:
        rohtext = pfad.read_text(encoding='utf-8', errors='replace')
    except OSError as e:
        print(f" [FEHLER: {e}]", flush=True)
        return 0, 0

    zeilen = rohtext.splitlines()
    rohtext = None

    # ── Anzeigenabschnitte sammeln ────────────────────────────────────────────
    anzeigen_zeilen: list[str] = []
    in_sektion = False

    for zeile in zeilen:
        stripped = zeile.strip()
        if ANZEIGEN_START_RE.match(stripped):
            in_sektion = True
            continue
        if in_sektion and EDITORIAL_END_RE.match(stripped):
            in_sektion = False
        if in_sektion:
            anzeigen_zeilen.append(stripped)

    zeilen = None

    if not anzeigen_zeilen:
        return 0, 0

    # ── Bullet-Extraktion ─────────────────────────────────────────────────────
    bullet_n = 0
    for zeile in anzeigen_zeilen:
        m = BULLET_LINE_RE.match(zeile)
        if not m:
            continue
        inhalt = m.group(1)

        # Annotation: Judengeschäft / christliches Geschäft
        anmerkung = ''
        if re.search(r'judengesch[äa]ft', inhalt, re.IGNORECASE):
            anmerkung = 'Judengeschäft'
        elif re.search(r'christliches geschäft', inhalt, re.IGNORECASE):
            anmerkung = 'christliches Geschäft'

        namen = extrahiere_namen_aus_bullet(inhalt)
        for name in namen:
            bullet_cnt[name] += 1
            if anmerkung and name not in anmerk_cnt:
                anmerk_cnt[name] = anmerkung
            bullet_n += 1

    # ── NER auf Anzeigentext ──────────────────────────────────────────────────
    anzeigen_text = '\n'.join(anzeigen_zeilen)
    anzeigen_zeilen = None

    ner_n = 0
    if len(anzeigen_text.strip()) > 20:
        if len(anzeigen_text) > nlp.max_length:
            anzeigen_text = anzeigen_text[:nlp.max_length]
        doc = nlp(anzeigen_text)
        for ent in doc.ents:
            if ent.label_ not in {'ORG', 'PER'}:
                continue
            name = bereinige_name(ent.text.strip())
            if name:
                ner_cnt[name] += 1
                ner_typ[name] = 'Organisation' if ent.label_ == 'ORG' else 'Person'
                ner_n += 1
        doc = None

    anzeigen_text = None
    gc.collect()
    return bullet_n, ner_n

# ── Hauptprogramm ─────────────────────────────────────────────────────────────

def main():
    bullet_cnt: Counter = Counter()
    ner_cnt:    Counter = Counter()
    ner_typ:    dict    = {}
    anmerk_cnt: dict    = {}   # Name → 'Judengeschäft' / 'christliches Geschäft'

    alle_dateien = sorted(DATA_DIR.rglob('*.txt'))
    gesamt = len(alle_dateien)

    print(f"Dateien gefunden: {gesamt}")
    print("─" * 65, flush=True)

    for idx, pfad in enumerate(alle_dateien, 1):
        print(f"Datei {idx:>3}/{gesamt}: {pfad.name}", end='', flush=True)
        b, n = verarbeite_datei(pfad, bullet_cnt, ner_cnt, ner_typ, anmerk_cnt)
        if b + n > 0:
            print(f"  → {b} Bullet-Namen, {n} NER-Entitäten", flush=True)
        else:
            print("  (keine Anzeigensektion gefunden)", flush=True)

    print("\n" + "─" * 65)
    print("Erstelle Auswertung …\n")

    # ── Kombinierter Score ────────────────────────────────────────────────────
    # Bullet-Treffer gelten doppelt (strukturell zuverlässiger als NER)
    kombi: Counter = Counter()
    for name, cnt in bullet_cnt.items():
        kombi[name] += cnt * 2
    for name, cnt in ner_cnt.items():
        kombi[name] += cnt

    top50 = kombi.most_common(50)

    # ── CSV 1: Top-50 kombiniert ──────────────────────────────────────────────
    csv_top50 = AUSGABE_DIR / 'werbekunden_top50.csv'
    with open(csv_top50, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['Rang', 'Name', 'Typ_(NER)', 'Anmerkung',
                    'Score', 'Bullet-Nennungen', 'NER-Nennungen'])
        for rang, (name, score) in enumerate(top50, 1):
            w.writerow([
                rang, name,
                ner_typ.get(name, '—'),
                anmerk_cnt.get(name, ''),
                score,
                bullet_cnt.get(name, 0),
                ner_cnt.get(name, 0),
            ])

    # ── CSV 2: Nur Bullet-Extraktion (alle) ───────────────────────────────────
    csv_bullet = AUSGABE_DIR / 'werbekunden_bullet_alle.csv'
    with open(csv_bullet, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['Rang', 'Name', 'Anmerkung', 'Nennungen'])
        for rang, (name, cnt) in enumerate(bullet_cnt.most_common(200), 1):
            w.writerow([rang, name, anmerk_cnt.get(name, ''), cnt])

    # ── CSV 3: Nur NER (alle) ─────────────────────────────────────────────────
    csv_ner = AUSGABE_DIR / 'werbekunden_ner_alle.csv'
    with open(csv_ner, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['Rang', 'Name', 'Typ', 'Nennungen'])
        for rang, (name, cnt) in enumerate(ner_cnt.most_common(200), 1):
            w.writerow([rang, name, ner_typ.get(name, '?'), cnt])

    # ── Terminal: Top 10 ──────────────────────────────────────────────────────
    print(f"{'═'*65}")
    print(f"  WERBEKUNDEN-ANALYSE ABGESCHLOSSEN")
    print(f"  Eindeutige Bullet-Namen  : {len(bullet_cnt)}")
    print(f"  Eindeutige NER-Entitäten : {len(ner_cnt)}")
    print()
    print(f"  TOP 10 WERBEKUNDEN (kombinierter Score, Bullet×2 + NER)")
    print()
    print(f"  {'Rg':>3}  {'Name':<35} {'Typ':<14} {'Anm.':<22}  {'Bullet':>6}  {'NER':>5}")
    print(f"  {'─'*3}  {'─'*35} {'─'*14} {'─'*22}  {'─'*6}  {'─'*5}")
    for rang, (name, score) in enumerate(top50[:10], 1):
        typ  = ner_typ.get(name, '—')
        anm  = anmerk_cnt.get(name, '')
        braw = bullet_cnt.get(name, 0)
        nraw = ner_cnt.get(name, 0)
        print(f"  {rang:>3}  {name:<35} {typ:<14} {anm:<22}  {braw:>6}  {nraw:>5}")

    print(f"\n  Gespeichert:")
    print(f"  → {csv_top50}")
    print(f"  → {csv_bullet}")
    print(f"  → {csv_ner}")
    print(f"{'═'*65}")


if __name__ == '__main__':
    main()
