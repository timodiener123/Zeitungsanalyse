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

## Eintrag 6 – 02.04.2026: NMF Topic Modeling (korpuseigen)
**Was:** Skript 06_topic_modeling_nmf.py erstellt und ausgeführt
**Werkzeug:** scikit-learn TF-IDF + NMF, 7 Topics, 5000 Features
**Warum:** Ergänzung zum impresso-Modell durch ein direkt am Stadtwächter-Korpus
trainiertes Modell – ohne externe Vokabularannahmen
**Ergebnis:** 7 Topics, je 15 Schlüsselwörter, dominante Topic-Zuordnung für alle 136 Ausgaben
**Top-Topics:**
- Topic 3 (28 Ausgaben): jude, jüdischen, nationalsozialisten, inflation → Antisemitismus
- Topic 2 (25 Ausgaben): oberbürgermeister, gericht, staatsanwalt → Lokaljustiz Osnabrück
- Topic 1 (23 Ausgaben): volksbegehren, stahlhelm, arzt → Politik & Agrarwirtschaft
**Interpretation:** Topic 3 als häufigstes Topic mit direkten Termen
jude/jüdischen/nationalsozialisten belegt den antisemitischen Diskurs
quantitativ als zentrales Charakteristikum der Zeitung.
**Methodischer Vorteil gegenüber impresso-MALLET:** Korpusspezifisches Modell
erfasst Eigenheiten des Stadtwächters (Osnabrücker Lokalpolitik, Namen,
historische Schreibweisen) ohne externe Trainingsdaten.
