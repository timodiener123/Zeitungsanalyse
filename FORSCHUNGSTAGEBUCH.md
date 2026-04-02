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

## Eintrag 5 – 02.04.2026: Topic Modeling mit impresso/MALLET
**Was:** Skript 05_impresso_topic_modeling.py erstellt und ausgeführt
**Werkzeug:** impresso-pipelines MalletPipeline (v0.4.3.24), MALLET 2.0.8, Modell tm-de-all-v2.0
**Warum:** Thematische Struktur des Korpus quantitativ erfassen,
um inhaltliche Schwerpunkte und deren Verteilung zu analysieren
**Ergebnis:** 136 Dateien, 816 Topic-Zuweisungen (ca. 6 Topics pro Datei ≥2%),
6 Kernthemen durchgängig im gesamten Korpus präsent (tp15, tp89, tp58, tp26, tp11, tp85)
**Interpretation:** Thematische Homogenität des Stadtwächters bestätigt –
dieselben Kernthemen ziehen sich durch alle Jahrgänge (1929–1931)
**Technische Entscheidung:** MalletPipeline statt LDATopicsPipeline verwendet,
da ldatopics intern das mallet-Modul nutzt (kein eigenständiges ldatopics-Modul).
Abhängigkeiten: Java 11 (OpenJDK), MALLET 2.0.8 (ältere Version nötig wegen
Serialisierungs-Inkompatibilität in MALLET 202108), python-dotenv, boto3, jpype1
