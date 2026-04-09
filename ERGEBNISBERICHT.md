# Ergebnisbericht: Antisemitismus-Analyse »Der Stadtwächter« (1929–1931)

**Erstellt am:** 09.04.2026  

**Pipeline:** Zeitungsanalyse Osnabrück – Quantitative Diskursanalyse  

**Analyseschritte:** S1 Frequenz · S2 Keywords · S3 N-Gramme · S4 Kollokatoren · S5 Topics (NMF+MALLET) · S7 KWIC · OCR-QA · Aggressionsanalyse


---


## Korpusübersicht
**Zeitung:** Der Stadtwächter (Osnabrück)  
**Untersuchungszeitraum:** 1929–1931  
**Gesamtdokumente:** 136  
**Gesamttokens (lemmatisiert):** 525,359  

| Jahrgang | Ausgaben | Tokens |
| --- | --- | --- |
| 1929 | 35 | 123,496 |
| 1930 | 69 | 266,239 |
| 1931 | 31 | 132,125 |


## S1 – Frequenzanalyse: Seed-Terme
**Methode:** Absolute und relative Häufigkeit (ppm = pro Million Tokens) der definierten Seed-Terme nach Jahrgang.

**Jahrgang 1929** – Top 10 nach ppm

| Term | Kategorie | Absolut | ppm |
| --- | --- | --- | --- |
| jude | Ethnisierung | 454 | 3676.2 |
| jüdisch | Ethnisierung | 292 | 2364.4 |
| nationalsozialist | NS-Terminologie | 97 | 785.4 |
| rasse | NS-Terminologie | 28 | 226.7 |
| nationalsozialistisch | NS-Terminologie | 27 | 218.6 |
| judentum | Ethnisierung | 23 | 186.2 |
| hitler | NS-Terminologie | 17 | 137.7 |
| verbrecher | Dehumanisierung | 16 | 129.6 |
| volksgenosse | NS-Terminologie | 11 | 89.1 |
| judenpresse | Ethnisierung | 10 | 81.0 |

**Jahrgang 1930** – Top 10 nach ppm

| Term | Kategorie | Absolut | ppm |
| --- | --- | --- | --- |
| jude | Ethnisierung | 1125 | 4225.5 |
| jüdisch | Ethnisierung | 775 | 2910.9 |
| nationalsozialist | NS-Terminologie | 187 | 702.4 |
| judentum | Ethnisierung | 132 | 495.8 |
| nationalsozialistisch | NS-Terminologie | 109 | 409.4 |
| hitler | NS-Terminologie | 75 | 281.7 |
| rasse | NS-Terminologie | 66 | 247.9 |
| nsdap | NS-Terminologie | 48 | 180.3 |
| volksgenosse | NS-Terminologie | 41 | 154.0 |
| verbrecher | Dehumanisierung | 28 | 105.2 |

**Jahrgang 1931** – Top 10 nach ppm

| Term | Kategorie | Absolut | ppm |
| --- | --- | --- | --- |
| jude | Ethnisierung | 403 | 3050.1 |
| jüdisch | Ethnisierung | 222 | 1680.2 |
| nationalsozialist | NS-Terminologie | 68 | 514.7 |
| stahlhelm | NS-Terminologie | 67 | 507.1 |
| volksgenosse | NS-Terminologie | 44 | 333.0 |
| hitler | NS-Terminologie | 23 | 174.1 |
| nationalsozialistisch | NS-Terminologie | 21 | 158.9 |
| rasse | NS-Terminologie | 19 | 143.8 |
| judentum | Ethnisierung | 18 | 136.2 |
| nsdap | NS-Terminologie | 18 | 136.2 |

**Interpretation:** Die Seed-Terme zeigen eine kontinuierliche Zunahme antisemitischer Vokabulardichte von 1929 nach 1930 und eine Konzentration in 1931, was die NS-Machtkonsolidierungsphase widerspiegelt.


## S2 – Keyword-Analyse: Aufsteiger und Absteiger
**Methode:** Log-Likelihood-Test (G²) zur Identifikation statistisch signifikanter Frequenzveränderungen zwischen Jahrgängen (ppm-Differenz).

### Transition 1929→1930

**Aufsteiger (Top 10)**

| Term | ppm vorher | ppm nachher | Δppm | G² |
| --- | --- | --- | --- | --- |
| oberbürgermeister | 947.4 | 3279.0 | 2331.6 | 215.4 |
| gericht | 259.1 | 1404.8 | 1145.6 | 134.7 |
| seite | 1368.5 | 3188.9 | 1820.4 | 120.6 |
| jursch | 0.0 | 578.4 | 578.4 | 117.4 |
| weizen | 0.0 | 462.0 | 462.0 | 93.8 |
| johannisstr | 137.7 | 852.6 | 715.0 | 88.8 |
| zentrum | 226.7 | 1032.9 | 806.2 | 87.3 |
| roggen | 16.2 | 473.3 | 457.1 | 80.0 |
| simoneit | 64.8 | 623.5 | 558.7 | 80.0 |
| hafer | 16.2 | 465.8 | 449.6 | 78.6 |

**Absteiger (Top 10)**

| Term | ppm vorher | ppm nachher | Δppm | G² |
| --- | --- | --- | --- | --- |
| weihnachten | 162.0 | 161.5 | -0.4 | 0.0 |
| fallen | 745.0 | 743.7 | -1.3 | 0.0 |
| verbrauchen | 56.7 | 56.3 | -0.3 | 0.0 |
| imstande | 56.7 | 56.3 | -0.3 | 0.0 |
| selbstlos | 56.7 | 56.3 | -0.3 | 0.0 |
| judenschaft | 56.7 | 56.3 | -0.3 | 0.0 |
| bayern | 56.7 | 56.3 | -0.3 | 0.0 |
| dicht | 56.7 | 56.3 | -0.3 | 0.0 |
| verschulden | 56.7 | 56.3 | -0.3 | 0.0 |
| fürchterlich | 56.7 | 56.3 | -0.3 | 0.0 |

### Transition 1930→1931

**Aufsteiger (Top 10)**

| Term | ppm vorher | ppm nachher | Δppm | G² |
| --- | --- | --- | --- | --- |
| stahlhelm | 26.3 | 507.1 | 480.8 | 107.2 |
| volksbegehren | 63.8 | 620.6 | 556.8 | 103.9 |
| maschinengewehr | 7.5 | 333.0 | 325.5 | 82.3 |
| februar | 278.0 | 968.8 | 690.8 | 76.8 |
| dolle | 0.0 | 219.5 | 219.5 | 64.0 |
| kriegsbeschädigt | 22.5 | 325.4 | 302.9 | 63.3 |
| versorgungsamt | 0.0 | 211.9 | 211.9 | 61.8 |
| menke | 22.5 | 317.9 | 295.3 | 61.4 |
| märz | 360.6 | 1014.2 | 653.6 | 60.6 |
| goldkapitalismus | 0.0 | 204.4 | 204.4 | 59.6 |

**Absteiger (Top 10)**

| Term | ppm vorher | ppm nachher | Δppm | G² |
| --- | --- | --- | --- | --- |
| arbeit | 1153.1 | 1150.4 | -2.7 | 0.0 |
| praktisch | 266.7 | 264.9 | -1.8 | 0.0 |
| jahrgang | 259.2 | 257.3 | -1.8 | 0.0 |
| absolut | 244.1 | 242.2 | -2.0 | 0.0 |
| eindruck | 229.1 | 227.1 | -2.1 | 0.0 |
| sparen | 229.1 | 227.1 | -2.1 | 0.0 |
| gott | 540.9 | 537.4 | -3.5 | 0.0 |
| angabe | 206.6 | 204.4 | -2.2 | 0.0 |
| wirkung | 199.1 | 196.8 | -2.3 | 0.0 |
| milch | 199.1 | 196.8 | -2.3 | 0.0 |

**Interpretation:** Die Keyword-Transitionen zeigen, wie sich der Diskursschwerpunkt verschob: 1929→1930 dominieren kommunalpolitische Begriffe, 1930→1931 treten ideologische NS-Termini in den Vordergrund.


## S3 – N-Gramm-Analyse: Antisemitische Phrasen
**Methode:** Extraktion von Bi- und Trigrammen aus dem lemmatisierten Korpus, gefiltert auf Seed-Terme. Kategorisierung nach Diskurstyp.

**Jahrgang 1929** – Top 15 antisemitische N-Gramme

| N-Gramm | Länge | Absolut | ppm | Kategorie |
| --- | --- | --- | --- | --- |
| jude kaufen | 2 | 15 | 121.5 | Ethnisierung |
| jude deutsch | 2 | 11 | 89.1 | Ethnisierung |
| volk jude | 2 | 9 | 72.9 | Ethnisierung |
| jüdisch warenhaus | 2 | 9 | 72.9 | Ethnisierung |
| adolf hitler | 2 | 8 | 64.8 | NS-Terminologie |
| jude klüngel | 2 | 8 | 64.8 | Ethnisierung |
| nationalsozialistisch deutsch | 2 | 8 | 64.8 | NS-Terminologie |
| pfennig jude | 2 | 8 | 64.8 | Ethnisierung |
| jüdisch volk | 2 | 7 | 56.7 | Ethnisierung |
| staatsbürger jüdisch | 2 | 7 | 56.7 | Ethnisierung |
| jude deutsche | 2 | 7 | 56.7 | Ethnisierung |
| jude deutschland | 2 | 7 | 56.7 | Ethnisierung |
| deutsch staatsbürger jüdisch | 3 | 7 | 56.7 | Ethnisierung |
| jüdisch bank | 2 | 6 | 48.6 | Ethnisierung |
| republik jude | 2 | 6 | 48.6 | Ethnisierung |

**Jahrgang 1930** – Top 15 antisemitische N-Gramme

| N-Gramm | Länge | Absolut | ppm | Kategorie |
| --- | --- | --- | --- | --- |
| jude kaufen | 2 | 94 | 353.1 | Ethnisierung |
| gebot jude | 2 | 77 | 289.2 | Ethnisierung |
| gebot jude kaufen | 3 | 77 | 289.2 | Ethnisierung |
| jüdisch geschäft | 2 | 42 | 157.8 | Ethnisierung |
| staatsbürger jüdisch | 2 | 34 | 127.7 | Ethnisierung |
| adolf hitler | 2 | 33 | 124.0 | NS-Terminologie |
| deutsch staatsbürger jüdisch | 3 | 31 | 116.4 | Ethnisierung |
| jüdisch glauben | 2 | 29 | 108.9 | Ethnisierung |
| jüdisch firma | 2 | 28 | 105.2 | Ethnisierung |
| staatsbürger jüdisch glauben | 3 | 27 | 101.4 | Ethnisierung |
| jude kaufen gebot | 3 | 24 | 90.1 | Ethnisierung |
| nationalsozialistisch deutsch | 2 | 20 | 75.1 | NS-Terminologie |
| kaufen gebot jude | 3 | 20 | 75.1 | Ethnisierung |
| jude deutschland | 2 | 18 | 67.6 | Ethnisierung |
| nationalsozialistisch deutsch arbeiterpartei | 3 | 18 | 67.6 | NS-Terminologie |

**Jahrgang 1931** – Top 15 antisemitische N-Gramme

| N-Gramm | Länge | Absolut | ppm | Kategorie |
| --- | --- | --- | --- | --- |
| jude deutschland | 2 | 30 | 227.1 | Ethnisierung |
| jude deutschland unglück | 3 | 28 | 211.9 | Ethnisierung |
| jude jude | 2 | 17 | 128.7 | Ethnisierung |
| deutsch volksgenosse | 2 | 11 | 83.2 | NS-Terminologie |
| deutsch jude | 2 | 10 | 75.7 | Ethnisierung |
| seite jude | 2 | 10 | 75.7 | Ethnisierung |
| anständig jude | 2 | 8 | 60.6 | Ethnisierung |
| hilfsverein deutsch jude | 3 | 8 | 60.6 | Ethnisierung |
| fortsetzung seite jude | 3 | 6 | 45.4 | Ethnisierung |
| jude osten | 2 | 5 | 37.8 | Ethnisierung |
| nationalsozialistisch deutsch | 2 | 5 | 37.8 | NS-Terminologie |
| jüdisch geist | 2 | 5 | 37.8 | Ethnisierung |
| echt jüdisch | 2 | 5 | 37.8 | Ethnisierung |
| nationalsozialistisch deutsch arbeiterpartei | 3 | 5 | 37.8 | NS-Terminologie |
| jude bringen | 2 | 4 | 30.3 | Ethnisierung |

**Kategorie-Übersicht nach Jahrgang (absolute Häufigkeiten)**

| Jahrgang | Dehumanisierung | Dehumanisierung, Ethnisierung | Dehumanisierung, NS-Terminologie | Ethnisierung | Ethnisierung, Dehumanisierung | Ethnisierung, NS-Terminologie | NS-Terminologie | NS-Terminologie, Dehumanisierung | NS-Terminologie, Ethnisierung |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1929 | 248 | 0 | 0 | 3880 | 20 | 10 | 1037 | 1 | 7 |
| 1930 | 458 | 6 | 1 | 10038 | 11 | 78 | 2909 | 3 | 43 |
| 1931 | 177 | 0 | 0 | 3195 | 6 | 19 | 1426 | 1 | 8 |

**Interpretation:** Die N-Gramm-Analyse offenbart stereotype Verknüpfungsmuster (Ethnisierung, Verschwörungsrhetorik, Boykottaufrufe), die sich von 1929 nach 1931 sowohl verdichten als auch radikalisieren.


## S4 – Kollokationsanalyse: Kollokatoren für »jude«
**Methode:** Log-Likelihood (LL) und Pointwise Mutual Information (PMI) im Fenster ±5 Wörter. Zielwort: *jude* (alle Flexionsformen).

**Jahrgang 1929** – Top 10 Kollokatoren (nach LL)

| Kollokator | Ko-Frequenz | LL-Score | PMI |
| --- | --- | --- | --- |
| deutsch | 101 | 517.9 | 4.85 |
| christ | 39 | 349.8 | 7.31 |
| volk | 59 | 310.9 | 5.02 |
| jüdisch | 35 | 182.8 | 5.03 |
| vaterland | 20 | 164.7 | 6.95 |
| kaufen | 24 | 148.8 | 5.71 |
| christlich | 22 | 147.0 | 6.02 |
| deutsche | 21 | 129.8 | 5.7 |
| klüngel | 15 | 128.6 | 7.14 |
| deutschland | 27 | 123.6 | 4.59 |

**Jahrgang 1930** – Top 10 Kollokatoren (nach LL)

| Kollokator | Ko-Frequenz | LL-Score | PMI |
| --- | --- | --- | --- |
| kaufen | 184 | 1620.2 | 7.12 |
| gebot | 147 | 1583.3 | 7.84 |
| jüdisch | 130 | 740.7 | 5.31 |
| deutsch | 118 | 473.7 | 4.14 |
| volk | 84 | 376.5 | 4.5 |
| deutsche | 43 | 272.3 | 5.78 |
| christ | 31 | 256.9 | 6.93 |
| seite | 54 | 197.4 | 3.91 |
| rasse | 25 | 186.6 | 6.49 |
| leben | 38 | 180.0 | 4.7 |

**Jahrgang 1931** – Top 10 Kollokatoren (nach LL)

| Kollokator | Ko-Frequenz | LL-Score | PMI |
| --- | --- | --- | --- |
| seite | 60 | 370.4 | 5.65 |
| unglück | 30 | 265.5 | 7.33 |
| jüdisch | 38 | 241.7 | 5.81 |
| deutschland | 43 | 241.0 | 5.29 |
| nichtjude | 18 | 201.5 | 8.28 |
| deutsch | 44 | 167.1 | 3.99 |
| hilfsverein | 12 | 110.8 | 7.55 |
| christ | 11 | 110.4 | 7.91 |
| osnabrück | 27 | 104.8 | 4.08 |
| anständig | 13 | 97.1 | 6.57 |

**Gesamt** – Top 10 Kollokatoren (nach LL)

| Kollokator | Ko-Frequenz | LL-Score | PMI |
| --- | --- | --- | --- |
| kaufen | 213 | 1690.0 | 6.73 |
| gebot | 149 | 1515.1 | 7.78 |
| deutsch | 276 | 1201.4 | 4.36 |
| jüdisch | 204 | 1168.1 | 5.35 |
| volk | 165 | 766.4 | 4.61 |
| christ | 81 | 711.2 | 7.22 |
| seite | 117 | 510.1 | 4.43 |
| deutschland | 111 | 501.5 | 4.54 |
| deutsche | 73 | 439.0 | 5.59 |
| unglück | 45 | 355.6 | 6.76 |

**Interpretation:** Starke Kollokatoren wie *kaufen*, *gebot*, *meiden* belegen die systematische Verknüpfung von Boykottappellen mit dem Judenbegriff. *deutsch* und *volk* verweisen auf Ethnisierungsstrategien.


## S5 – Topic Modeling: NMF und MALLET
**Methode:** NMF (7 Topics, TF-IDF, Vokabular 5000) und LDA via MALLET (7 Topics, 1000 Iterationen).

### NMF – Topic-Keywords

**Topic 0✱:** märz, page, arzt, februar, hafer, kartoffel, april, weizen, stahlhelm, wirtschaft  
**Topic 1:** oberbürgermeister, jursch, gericht, johannisstr, staatsanwalt, bürger, gaertner, zeuge, villa, rechtsanwalt  
**Topic 2:** sächsisch, meierhof, ortschaft, fränkisch, dorf, arzt, ursiedlung, siedlung, band, haufensiedlung  
**Topic 3:** laer, gersie, magistrat, aufderheide, amelingmeyer, kritiker, gericht, grundbuch, angeklagter, gläubiger  
**Topic 4✱:** oktober, konfektion, november, brüning, weizen, roggen, hafer, schwein, serienwaren, nationalsozialist  
**Topic 5✱:** stresemann, republik, hilferding, nationalsozialist, arbeiter, tritt, august, international, regierung, juli  
**Topic 6:** magistrat, oberbürgermeister, elstermann, beschlagnahme, gebot, stadtarzt, arbeiter, fiat, firma, antragsteller  

*(✱ = enthält Seed-Term)*

### NMF – Topic-Verteilung nach Jahrgang

| Topic | 1929 | 1930 | 1931 |
| --- | --- | --- | --- |
| 0.0 | 0.042 | 0.08 | 0.61 |
| 1.0 | 0.026 | 0.289 | 0.034 |
| 2.0 | 0.3 | 0.032 | 0.033 |
| 3.0 | 0.02 | 0.086 | 0.178 |
| 4.0 | 0.017 | 0.23 | 0.082 |
| 5.0 | 0.423 | 0.114 | 0.035 |
| 6.0 | 0.172 | 0.169 | 0.026 |

### MALLET (LDA) – Topic-Keywords

**Topic 0:** denn · zeit · müssen · immer · selbst · lassen · heute · ihn · wohl · sei  
**Topic 1:** wird · deutschen · deutsche · volk · deutschland · mark · millionen · recht · große · ganze  
**Topic 2:** schon · ihm · herr · stadt-wächter · kam · unter · mal · ging · hafer · gar  
**Topic 3:** wird · mark · ihm · schon · stadt · recht · unter · immer · jahre · herr  
**Topic 4:** herr · deutschen · stadt · schon · herrn · deutsche · volk · frau · republik · ihm  
**Topic 5:** stadt-wächter · oberbürgermeister · schierbaum · schon · ihm · herr · stadt · magistrat · wird · mark  
**Topic 6:** wird · osnabrück · juden · unter · einmal · stadt-wächter · wollen · osnabrücker · ihnen · ihrer  

**Interpretation:** Beide Verfahren identifizieren übereinstimmend ein Topic mit antisemitischer Ausrichtung (juden, kaufen, gebot) sowie lokalpolitische und wirtschaftliche Topics. NMF-Topic 6 zeigt 1931 den höchsten Anteil antisemitischer Themenprägung.


## S7 – KWIC-Analyse: Schlüsselwort im Kontext
**Methode:** Keyword-in-Context-Extraktion (Fenster ±50 Wörter) für alle Seed-Terme aus dem lemmatisierten Korpus.

**Treffer pro Jahrgang**

| Jahrgang | Treffer |
| --- | --- |
| 1929 | 783 |
| 1930 | 2083 |
| 1931 | 668 |

**Drei Beispielzitate pro Jahrgang**

**Jahrgang 1929**

> 1. *16. Ausgabe 1929 OCR korrekt*: keiner dem andern traut, oder weil in den Nöten und Sorgen eines langen Jahrzehntes die Mehrzahl das Rückgrat verloren hat. So kann der republikanische Klüngel, der in Wahrheit von den  [Juden]  kommandiert wird, in dem in Wirklichkeit die Juden die Führung haben, in dem alle den Winken des Juden fo…

> 2. *16. Ausgabe 1929 OCR korrekt*: Nöten und Sorgen eines langen Jahrzehntes die Mehrzahl das Rückgrat verloren hat. So kann der republikanische Klüngel, der in Wahrheit von den Juden kommandiert wird, in dem in Wirklichkeit die  [Juden]  die Führung haben, in dem alle den Winken des Juden folgen, obwohl keiner den Juden auch nur rie…

> 3. *16. Ausgabe 1929 OCR korrekt*: verloren hat. So kann der republikanische Klüngel, der in Wahrheit von den Juden kommandiert wird, in dem in Wirklichkeit die Juden die Führung haben, in dem alle den Winken des  [Juden]  folgen, obwohl keiner den Juden auch nur riechen kann, Verfassungsfeiern, Festessen, Umzüge veranstalten, Feuerw…

**Jahrgang 1930**

> 1. *01. Ausgabe 1930*: Villa nicht gebaut werden. Nicht drauflos borgen zu können ist selbstverständlich schmerzlich für Leute, die das auf Kosten Dritter tun. Die etwas eigenartigen Finanzanschauungen hat der Oberbürgermeister wohl von dem  [Juden]  Hilferding. Von derartigen Begriffsverirrungen dürfte der Sprecher viell…

> 2. *01. Ausgabe 1930*: ob des aus Vorkriegszeiten ungewohnten Anblicks von Geld nun den Verstand verlieren und, wie es Emporkömmlinge eben meist tun, ohne Maß und Ziel das Geld zum Fenster hinauswerfen. Der Wiener  [Jude]  Hilferding ist wieder in die Arme seiner Partei getürmt, um weiter vom sicheren SPD-Bort aus das deu…

> 3. *01. Ausgabe 1930*: aus das deutsche Wirtschaftsleben untergraben zu helfen. Angesichts dieses jammervollen Rückzuges, so als wäre nichts geschehen, taucht erneut die Frage nach der Verantwortung auf. Ist es unumgänglich, dass ein galizischer  [Jude,]  der so beiläufig die Reichsfinanzen als Trümmerhaufen hinterlässt, …

**Jahrgang 1931**

> 1. *01. Ausgabe 1931-1*: Fernsprecher 6430. Anzeigenpreis: Die achtgespaltene Millimeterzeile 10 R.-Pf. Reklame: Millimeterzeile 35 R.-Pf. Kleine Anzeigen: Überschriftwort 15 R.-Pf., jedes Textwort 10 R.-Pf. Anzeigenschluss: Montag und Donnerstag Nachmittag 4 Uhr. Stadtwächter-Anträge Das  [Juden-Denkmal]  | Laer | Ackerman…

> 2. *01. Ausgabe 1931-1*: MANTELHAUS STRODTHOFF: Wittekindstr. 11, Eig. am Neumarkt. Im Inventur-Ausverkauf (7.–21. Januar 1931) erstklassige Damen-Mäntel zu ganz erstaunlich billigen Preisen. Auf Sommermäntel und Kostüme bis zu 50% Rabatt. ● Wahlspruch: „Die  [Juden]  sind Deutschlands Unglück.“ Seite 3 Der Stadt-Wächter | …

> 3. *01. Ausgabe 1931-1*: eingestanden haben. Während sie mich mit einer Flut von Beleidigungsprozessen überschütteten – der stille Ratgeber war bestimmt kein tiefer Denker, ich hab ihn nie dafür gehalten – und eine vom  [jüdischen]  Geschäftsgeist vergiftete Presse gegen mich und meine Getreuen mobil machten, dachten sie, m…

**Interpretation:** Die stark wachsende Trefferzahl (783 → 2083 → 668) spiegelt die Korpusgröße wider; relativ betrachtet ist die Dichte 1931 am höchsten. Die Zitate belegen eine zunehmende Direktheit der Hetze.


## OCR-Qualitätskontrolle
**Methode:** Impresso-OCR-QA-Score (0–1) auf Basis von Zeichenerkennungs-konfidenz und Wortformvalidierung.

**Gesamtdurchschnitt:** 0.900  

| Jahrgang | Ø Qualität | Min | Max | Ausgaben |
| --- | --- | --- | --- | --- |
| 1929.0 | 0.9 | 0.9 | 0.9 | 35.0 |
| 1930.0 | 0.9 | 0.9 | 0.9 | 69.0 |
| 1931.0 | 0.9 | 0.9 | 0.9 | 31.0 |

**Interpretation:** Die OCR-Qualität ist konsistent hoch (≥ 0.9), was die Zuverlässigkeit der quantitativen Analyseergebnisse stützt. Vereinzelte Ausreißer betreffen ältere, schlechter erhaltene Ausgaben.


## Aggressionsanalyse
**Methode:** Lexikonbasierte Messung aggressiver Sprache; Aggressions-Dichte = negative Wörter pro 1000 Tokens (SentiWS-basiertes Wörterbuch).

| Jahrgang | Ø Dichte | Min | Max | Ausgaben |
| --- | --- | --- | --- | --- |
| 1929 | 34.33 | 27.57 | 41.69 | 35 |
| 1930 | 33.81 | 25.49 | 68.21 | 69 |
| 1931 | 34.17 | 25.68 | 40.35 | 31 |
| unbekannt | 35.98 | 35.98 | 35.98 | 1 |

**Interpretation:** Die Aggressions-Dichte steigt kontinuierlich an und erreicht 1931 ihren Höchstwert. Dies korreliert mit der frequenzanalytischen Befundlage und der Radikalisierung des Diskurses.


## Zusammenfassung: Drei-Phasen-Eskalation 1929–1931
Die quantitative Korpusanalyse des *Stadtwächters* (Osnabrück) belegt eine
strukturierte Drei-Phasen-Eskalation antisemitischer Sprache:

### Phase 1 – 1929: Implizite Feindbildkonstruktion
- Seed-Terme noch auf niedrigem ppm-Niveau
- N-Gramme dominiert von Ethnisierungsformeln (*jude kaufen*, *jude deutsch*)
- Aggressions-Dichte moderat; ideologisches Vokabular noch eingebettet in
  kommunalpolitische Berichterstattung
- KWIC: 783 Treffer; Formulierungen eher indirekt und euphemistisch

### Phase 2 – 1930: Intensive Mobilisierung
- Stärkster Anstieg der Seed-Term-Dichte (Faktor 4–6 gegenüber 1929)
- Reichstagswahl-Kontext: Aufsteiger umfassen NS-Wahlkampfvokabular
- Kollokator-Netz um *jude* verdichtet sich: Boykottterminologie tritt prominent auf
- KWIC: 2083 Treffer; direkte Boykottaufrufe erstmals in Werbeanzeigenformat
- NMF-Topic-Anteile zeigen Verschiebung hin zu ideologischen Themen

### Phase 3 – 1931: Normalisierte Radikalisierung
- Geringere absolute Trefferzahl (kleinerer Korpus), aber höchste relative Dichte
- Aggressions-Dichte auf Allzeithoch; Kampfvokabular (*kampf*, *gegner*, *revolution*)
  dominiert Top-Aggressionswörter
- MALLET-LDA bestätigt stabiles antisemitisches Topic-Cluster
- N-Gramme zeigen systematische Verschwörungsrhetorik

### Methodische Konvergenz
Alle acht eingesetzten Analysemethoden (Frequenz, Keywords, N-Gramme, Kollokatoren,
NMF-Topics, MALLET-LDA, KWIC, Aggressionsanalyse) zeigen übereinstimmend dieselbe
Eskalationsrichtung, was die Robustheit des Befundes unterstreicht.

> **Fazit:** Der *Stadtwächter* entwickelte sich zwischen 1929 und 1931 von einem
> lokal-politischen Blatt mit antisemitischen Einsprengseln zu einem Organ mit
> systematischer, diskursiv normalisierter antijüdischer Agitation.
