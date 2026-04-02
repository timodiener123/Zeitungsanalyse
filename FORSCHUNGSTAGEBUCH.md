# Forschungstagebuch: Korpuslinguistische Analyse des Stadtwächters (1929–1931)

## Methodische Grundlage
Dieses Tagebuch folgt dem Prinzip von Huskey (2023):
"Committing to Reproducibility and Explainability: Using Git as a Research Journal."
Jeder Analyseschritt wird mit Datum, Entscheidung und Begründung dokumentiert.

## Eintrag 1 – 02.04.2026: Projektstruktur
**Was:** Ordnerstruktur angelegt (daten_txt, daten_pdf, Skripte, ergebnisse)
**Warum:** Klare Trennung von Rohdaten, Code und Ergebnissen
für maximale Reproduzierbarkeit
**Entscheidung:** Rohdaten (.txt-Dateien) werden nicht auf GitHub
gepusht (.gitignore), da urheberrechtlich geschützt
**Werkzeuge:** Claude Code (KI-assistiertes Programmieren), Git, GitHub

## Eintrag 2 – 02.04.2026: Tokenisierung und Lemmatisierung
**Was:** Skript 01_tokenisierung.py erstellt und ausgeführt
**Warum:** Grundlage für alle weiteren Analyseschritte
**Entscheidung:** spaCy mit de_core_news_sm verwendet,
da de_core_news_lg wegen instabiler Verbindung nicht installierbar war.
sm-Modell ist für Frequenz- und Kollokationsanalysen ausreichend.
**Ergebnis:** 538.035 Tokens verarbeitet, tokenisierung.csv (27 MB) erstellt

## Eintrag 3 – 02.04.2026: Frequenzanalyse
**Was:** Skript 02_frequenzanalyse.py erstellt und ausgeführt
**Warum:** Erste quantitative Übersicht über das Vokabular des Stadtwächters
**Entscheidung:** Normalisierung auf pro-Million-Wörter (ppm),
da die Jahrgänge unterschiedlich umfangreich sind (1930 doppelt so groß)
**Ergebnis:** Top-5-Lemmata: deutsch (6.453 ppm), Herr (5.825 ppm),
Osnabrück (5.180 ppm), Jude (3.740 ppm), Volk (3.262 ppm)
**Interpretation:** Jude auf Platz 4 der häufigsten Inhaltslexeme
bestätigt den antisemitischen Charakter der Zeitung quantitativ

## Eintrag 4 – 02.04.2026: OCR-Qualitätsprüfung mit impresso
**Was:** Skript 04_impresso_ocrqa.py erstellt und ausgeführt
**Werkzeug:** impresso-pipelines OCRQAPipeline (v0.4.3.24)
**Warum:** Wissenschaftlicher Nachweis der Textqualität als 
methodische Grundlage für alle weiteren Analyseschritte
**Ergebnis:** 136 Dateien analysiert, Durchschnitt 0.90 (sehr gut)
**Interpretation:** Hohe OCR-Qualität bestätigt die Zuverlässigkeit 
der Textgrundlage. Alle weiteren Analyseergebnisse sind damit 
auf einer soliden Datenbasis fundiert.
**Einschränkung:** Einheitliche 0.9-Werte deuten darauf hin, dass 
die Texte bereits manuell korrigiert wurden.

## Eintrag 5 – 02.04.2026: Topic Modeling mit impresso MALLET
**Was:** Skript 05_impresso_topic_modeling.py erstellt und ausgeführt
**Werkzeug:** impresso-pipelines MalletPipeline (LDA, 100 Topics)
**Ergebnis:** 136 Dateien, 61 aktive Topics, 2.177 Topic-Zuweisungen
**Top-5-Topics mit Interpretation:**
- tp12 (Religion & Politik): recht, kirche, freiheit, volk, staat
- tp46 (Weltanschauung): welt, leben, mensch, geschichte, natur
- tp22 (Kommentar): zeitung, frage, arbeit, interesse
- tp89 (Presse & Medien): zeitung, presse, artikel, blatt, leser
- tp83 (Geographie): berlin, münchen, wien, frankfurt, köln
**Interpretation:** Dominanz von politisch-religiösem Diskurs und 
Pressekritik – typisch für antisemitische Meinungspresse der Weimarer 
Republik. tp89 deutet auf bewusste Medienkritik als diskursive Strategie hin.
**Methodische Entscheidung:** impresso MALLET-Pipeline gewählt, weil sie 
speziell für historische Zeitungstexte auf Deutsch optimiert ist.

## Eintrag 6 – 02.04.2026: NMF Topic Modeling auf Stadtwächter-Korpus
**Was:** Skript 06_topic_modeling_nmf.py erstellt und ausgeführt
**Werkzeug:** scikit-learn NMF mit TF-IDF Vektorisierung, 7 Topics
**Warum NMF statt impresso MALLET:** Das impresso-Modell wurde auf 
fremden Korpora trainiert und produzierte keine validen Ergebnisse 
für antisemitische Presse. NMF wird direkt auf dem Stadtwächter 
trainiert und ist damit korpusspezifisch und wissenschaftlich valider.
**Ergebnis:** 7 Topics, davon 2 explizit antisemitisch:
- Topic 3 (28 Ausgaben): Wirtschaftspolitischer Antisemitismus
  (jude, jüdischen, nationalsozialisten, stresemann, inflation)
- Topic 4 (19 Ausgaben): Agrarischer Antisemitismus
  (jüdische, nationalsozialisten, konfektion, roggen, weizen)
**Zeitliche Entwicklung:**
- 1929: Topic 3 dominant (wirtschaftspolitischer Antisemitismus)
- 1930: Topics 2+5 (Lokalpolitik und Justiz)
- 1931: Topics 1+4+6 (agrarisch-völkischer Antisemitismus)
**Interpretation:** Die zeitliche Verschiebung der Topics bestätigt 
unabhängig die Phaseneinteilung des Analyseberichts vom 26.03.2026.
NMF als Methode ist in diesem Fall wissenschaftlich valider als 
vortrainierte Modelle, weil sie direkt auf dem Zielkorpus trainiert wird.

## Eintrag 7 – 02.04.2026: Aggressionsanalyse mit SentiWS
**Was:** Skript 07_aggressionsanalyse.py erstellt und ausgeführt
**Werkzeug:** SentiWS v2.0 Negativ-Lexikon (17.806 Wortformen), regelbasiert
**Ergebnis:** Aggressions-Dichte (negative Wörter pro 1000 Wörter) für alle 136 Ausgaben
**Zusammenfassung nach Jahrgang:**
- 1929 (35 Ausgaben): Ø 34,3 | Min 27,6 | Max 41,7
- 1930 (69 Ausgaben): Ø 33,8 | Min 25,5 | Max 68,2
- 1931 (31 Ausgaben): Ø 34,2 | Min 25,7 | Max 40,4
**Häufigste Aggressionswörter:** kampf, not, inflation, kritik, beleidigung, ende, schwer
**Interpretation:** Konstant hoher Aggressionspegel über alle Jahrgänge (~34/1000).
Ausreißer 1930 (Max 68,2) deutet auf einzelne besonders aggressive Ausgaben.
Durchgehend aggressiver Grundton bestätigt den Charakter als Kampfblatt.

## Eintrag 8 – 02.04.2026: Seedterm-Analyse (antisemitische Kernterme)
**Was:** Skript 08_seedterm_analyse.py erstellt und ausgeführt
**Werkzeug:** Regelbasierte Frequenzanalyse, 22 Seed-Terme, Normalisierung auf ppm
**Ergebnis:** Frequenzen aller 22 Terme nach Jahrgang (absolut + ppm)
**Zentrale Befunde:**
- juden: 1929=1135 ppm → 1930=1514 ppm (Peak) → 1931=960 ppm
- hitler: 1929=42 ppm → 1930=107 ppm → 1931=63 ppm
- nsdap: 1929=4 ppm → 1930=81 ppm → 1931=57 ppm
- bolschewismus: 1929=4 ppm → 1930=33 ppm → 1931=73 ppm (steigend)
- volksgenosse: 1929=4 ppm → 1930=13 ppm → 1931=44 ppm (steigend)
**Interpretation:** 1930 ist das antisemitisch intensivste Jahr (Reichstagswahl
Sept. 1930, NSDAP-Aufstieg). bolschewismus und volksgenosse steigen bis 1931
weiter – die Sprache wird zunehmend NS-ideologisch geprägt.
Zeitliche Phaseneinteilung aus NMF-Analyse unabhängig bestätigt.
