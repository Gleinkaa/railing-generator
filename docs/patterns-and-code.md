# Musterkatalog → Generator: Konstruktions- und Normdaten

**Stand:** 2026-08-04 · Erhoben für Phase 14 (`docs/SPEC.md`), weil die vier Holz- und die
zwei Blech-Designs aus dem Musterkatalog Materialien einführen, für die das Modell bis
dahin keinerlei Kennwerte hatte — es kannte nur „Stab mit kg/m".

**Wie erhoben:** zwei Recherche-Agenten über die agy-Gemini-Brücke (Gemini 3.1 Pro), mit
Gegenprüfung. Die OIB-Richtlinie 4 wurde in beiden Läufen als Volltext-PDF beschafft und
**wörtlich** ausgewertet; die Erstantworten des Modells enthielten dort mehrfach falsche
Punktnummern und ein falsches Prüfkriterium. **Alle Normzitate unten stammen aus dem
Originalwortlaut, nicht aus dem Modell.** Konstruktionswerte sind mit `[Q]` (belegte
Quelle) oder `[S]` (begründete Schätzung / Fachpraxis) markiert.

---

## 1. Der wichtigste Befund: Österreich ist nicht Deutschland

**OIB-RL 4 (Ausgabe Mai 2023), Pkt. 4.2.4** — wörtlich:

> „Öffnungen in Absturzsicherungen dürfen zumindest in einer Richtung nicht größer als
> 12 cm sein."

Das ist eine **Richtungsbedingung**, keine Kugelprüfung. Ein Schlitz 40 × 700 mm ist
konform, obwohl eine 120-mm-Kugel dort nie durchginge. Für „Grain Sheet" (durchlaufende
vertikale Schlitze) ist genau das die Erlaubnisnorm.

Konsequenz im Generator: `Oeffnung-max` steht auf **120 mm**, nicht auf 100. Der
frühere Default 100 war das deutsche/schweizerische Maß.

Unterer Abschluss, gleicher Punkt: Würfel **12 cm** bei Geländer *über* der Standfläche,
**7,5 cm** plus lichter Horizontalabstand max. 3 cm bei Geländer *neben* der Standfläche.

## 2. Kletterhilfe — OIB-RL 4, Pkt. 4.2.3 (wörtlich)

> „Im Bereich von **15 cm bis 60 cm** über fertiger Stufenvorderkante oder Standfläche
> dürfen keine horizontalen oder schrägen Elemente der Absturzsicherung angeordnet sein,
> es sei denn, ein Hochklettern von Kindern wird erschwert, wie zum Beispiel durch
> – Horizontale oder schräge Elemente, die nicht um mehr als **3 cm** vorspringen,
> – Öffnungen, die in der Vertikalen nicht größer als **2 cm** sind,
> – Seilnetze mit einem Maschenumfang von höchstens **16 cm**,
> – Lochbleche mit einem Lochdurchmesser von höchstens **4 cm**,
> – eine nach innen um mindestens **15 cm** überstehende Geländeroberkante."

**Die Richtlinie nennt bewusst keinen Grenzwinkel.** Wörtlich ist *jede* Schräge in der
Zone erfasst. Deshalb ist der Winkel im Generator ein Regler
(`Kletterwinkel-Grenze`, Default 60°, konservativ 75°) und keine eingebaute Wahrheit —
bei einer Auseinandersetzung ist genau das der Angriffspunkt, und der ausführende Betrieb
muss den gewählten Wert im Datenblatt offenlegen. `[S]` für die 60°/75°-Praxiswerte.

Der Winkel wird gegen die **echte Waagrechte** gemessen, nicht gegen die Steigung: ein
Element parallel zum Treppenlauf liegt bei ~30° und ist damit eine Rampe.

**Pkt. 4.2.5** erlaubt Abweichungen von 4.2.3/4.2.4, wenn die Anwesenheit von Kindern
üblicherweise nicht zu erwarten ist. Wohnbau = Kinder erwartet, also gelten beide voll.

Weitere verifizierte Werte: Höhe ≥ **1,00 m**, ab Absturzhöhe > 12 m ≥ 1,10 m,
**Wohnungstreppen 0,90 m** (Pkt. 4.2.1; die 90-cm-Erleichterung gilt laut
OIB-Klarstellung *nur* für Wohnungstreppen, nicht für Wohnungsbalkone oder Galerien).
Absturzsicherung erforderlich ab 60 cm bei hoher Gefahr, jedenfalls ab 1,00 m (4.1.1).
Horizontale Holmlast Kategorie A (Wohnen) = **0,5 kN/m** nach ÖNORM B 1991-1-1,
Abschnitt 8.2.1, Tabelle 6 — *nicht* „EN 1991-1-1 Tabelle 6.12", das ist der deutsche NA.

**ÖNORM B 5371:2021-03-01** ist kostenpflichtig und wurde **nicht** im Volltext geprüft.
Abschnittsnummern daraus stehen bewusst nirgends im Repo. Bei Widerspruch gilt ohnehin
die OIB-RL 4, weil sie über die Bautechnikverordnungen der Länder verbindlich ist.

## 3. Bewertung der Musterfamilien

Zone A = 150–600 mm über Stufenvorderkante (4.2.3 + 4.2.4), Zone B = Rest (nur 4.2.4).

| Familie | Zone A | Zone B | Bedingung |
|---|---|---|---|
| rein vertikale Stäbe | konform | konform | lichter Abstand ≤ 120 mm |
| vertikal + wenige Diagonalen | bedingt | konform | Diagonale in Zone A nur ≥ 60° oder Vorsprung ≤ 30 mm |
| dichte Diagonalen einer Richtung ~45° | **unzulässig** | konform | 45° = Leitersprossen |
| gekreuzte Diagonalen (Raute) | bedingt | konform | Maschenumfang ≤ 160 mm oder vertikale Öffnung ≤ 20 mm |
| horizontale Flachprofile („Horizontal Flats") | **praktisch K.O.** | konform | Zone A bräuchte Spalt ≤ 20 mm — das sind keine Horizontal Flats mehr |
| Rechteckraster + Diagonalen | bedingt | konform | Zone A rein vertikal durchlaufen lassen |
| Blech mit Ausschnitten | bedingt | konform | Zone A normgedeckt nur: Ausschnitt passt in Kreis Ø ≤ 40 mm |
| Bogen-/Schleifenornamente | bedingt, hohes Risiko | konform | Bogenscheitel (waagrechte Tangente) darf nicht in Zone A liegen |

Der Generator bildet das als *Vorprüfung* ab: er zählt Stäbe, deren Tangente in Zone A
flacher als die Winkelgrenze verläuft, und schreibt das Ergebnis auf den `Norm`-Ausgang.
Er trifft **keine** Entscheidung und ersetzt keinen Nachweis.

## 4. Holz (Staggered Panels, Wide Slats, Segmented Panels, Diamond Lattice)

**Rohdichte ρ₁₂ als BOM-Rechenwert** (obere Grenze, konservativ) `[Q]` DIN 68364 /
ÖNORM B 3012 — *nicht* EN 350, die liefert nur Dauerhaftigkeit:

| Holzart | kg/m³ | Holzart | kg/m³ |
|---|---|---|---|
| Accoya | 550 | Eiche | 760 |
| Lärche europäisch | 590 | Bangkirai | 950 |
| Sib. Lärche / Thermoesche | 650 | Bongossi | 1100 |

Regler `Holz-Rohdichte` (350–900, Default 600) deckt den praxisrelevanten Bereich ab.

- Lamellen **19–28 mm** dick, **55–140 mm** breit `[Q]` (AT-Handelsmaße). Freie
  Spannweite zwischen Riegeln: **600 mm** bei 19–21 mm, **700–800 mm** bei 24–28 mm
  `[Q, abgeleitet]` — maßgebend ist **Schüsseln, nicht Statik**.
  **Bei 900 mm Füllhöhe reichen 2 Riegel für 19-mm-Lamellen nicht; ab 24 mm ja.**
- Fuge zwischen Holzteilen **8–12 mm**, Regelwert **10 mm**, absolutes Minimum 6 mm `[Q]`
  (HFA/proHolz — *nicht* ÖNORM B 3802-1, die regelt nur qualitativ).
- Bodenabstand: Holzschutz verlangt ≥ 50 mm zu wasserführenden Ebenen, die Norm erlaubt
  höchstens 120 mm → **nutzbares Fenster 50–120 mm, Zielwert 100 mm** `[Q, abgeleitet]`.
- Befestigung **von hinten durch den Stahl ins Holz** (Sichtseite schraubenfrei):
  Senkkopf A2/A4 6,0 × 30 bei 30 mm Holz auf 8 mm Flachstahl, Bohrung Ø 6,5 mm + 90°
  Senkung `[Q/S]`. Ein Loch als Festpunkt, das zweite als **Langloch ≥ 3–4 mm Übermaß
  quer zur Faser** — Rechenweg: Lärche quillt ~0,22 %/% ΔHF, ΔHF ≈ 12 % außen, Brett
  140 mm → 4,0 mm Bewegung. Accoya quillt praktisch nicht und braucht kein Übermaß.
- **Gerbsäure:** Eiche und Lärche fressen Zink. Verzinkte Verbindungsmittel sind dort
  ungeeignet, A4 (1.4401/1.4571) ist bei Eiche zwingend `[Q]`.

**Der eigentliche Konstruktionsfehler in den Holzmustern:** ein Flachstahlriegel 40 × 8
hochkant biegt sich bei 1200 mm Pfostenweite und 0,5 kN/m um **17 mm** (L/71) — die
Spannung ist unkritisch, die **Durchbiegung** ist maßgebend. Brauchbar sind
**Rechteckrohr 40 × 20 × 2** (0,65 mm) oder **Winkel L 40 × 40 × 4**. Die Holzfüllung
darf statisch nicht als mitwirkende Scheibe angesetzt werden. `[Q, eigene Rechnung]`
Der Generator modelliert die Riegel derzeit über `Diagonal-Profil`; für Holzmuster
gehört dort ein Rohr- oder Winkelprofil eingestellt, kein 40 × 8 Flachstahl.

## 5. Laserblech (Ellipse Sheet, Grain Sheet)

- Dicke für ein Feld 1100 × 900 mm, 4-seitig gefasst: S235 **2,5–3,0 mm**, 1.4301
  2,0–3,0 mm, Alu 3,0–4,0 mm. Nur 2-seitig gehalten jeweils eine Stufe mehr. `[S]`
  **Bei 30–50 % Ausschnittsanteil eine Dickenstufe aufschlagen** → für Ellipse Sheet und
  Grain Sheet in Stahl **3,0 mm**. Regler `Blech-Dicke` (2–10, Default 4) deckt das ab.
- Dichten: S235 7850, 1.4301 7900, EN AW-5754 2660 kg/m³ `[Q]`. Der Generator rechnet
  mit 7850 — für Edelstahl/Alu ist die Konstante `_rhoStahl` anzupassen.
- Abrechnung im Metallbau: **Brutto**material (der Butzen ist Verlust) + Maschinenzeit +
  Einstiche + Rüsten. Der Ausschnitt macht das Teil **teurer**, nicht billiger. `[S]`
- Steg zwischen Ausschnitten: lasertechnisch ≥ 1,0 × t, **statisch ≥ 15 mm**;
  Randabstand zur eingefassten Kante **≥ 25–30 mm** (sonst schaut ein Ausschnitt in die
  Nut). Regler `Blech-Steg` (Default 25) und `Blech-Rand` (Default 30). `[Q/S]`
- Offener Flächenanteil **> 50–60 %** → Verzug beim Schneiden. 30–50 % ist die
  Obergrenze, nicht der Komfortwert. `[S]`
- Dehnspiel: 1100 mm Stahl bei ΔT 90 K = 1,19 mm → allseitig **≥ 1,5–2,0 mm** Spiel,
  Alu ≥ 3,0 mm; gegen Klappern EPDM zwingend. `[Q, Rechnung]`
- **Feuerverzinken schließt feine Schlitze zu.** Unter ca. 8–10 mm bilden sich Zinkhäute
  `[Q]` — die feine Grain-Sheet-Variante geht dann nur in Edelstahl oder Alu.
  Zinkschichten nach EN ISO 1461 Tab. 3: 45/55 µm bei 1,5–3 mm Blech.
  Duplex außen: Zink 55–70 µm + Pulver ~80 µm. Nur pulverbeschichtet ohne Verzinkung ist
  außen fachlich mangelhaft.
- Für Außen mit Streusalz **1.4404 statt 1.4301** `[Q]` ISER-Merkblatt 821.

---

## Offene Fertigungsentscheidungen

Diese Punkte entscheidet der **ausführende Betrieb**, nicht der Generator und nicht ein
Agent. Die Nummerierung ist verbindlich: `grasshopper/patterns.py` markiert betroffene
Muster mit `status='open:shop-decision-N'`, wobei `N` die Nummer in dieser Liste ist.

1. **Winkelgrenze festschreiben** (`shop-decision-1`) — 60° oder 75° als Betriebsdefault
   für `Kletterwinkel-Grenze`? Die OIB-RL 4 gibt keinen Wert vor, der gewählte muss im
   Angebot offengelegt werden.
2. **„Horizontal Flats"** (`shop-decision-2`) ist in Zone A ohne Zusatzmaßnahme nicht
   genehmigungsfähig. Streichen, nur nach Pkt. 4.2.5 (ohne Kinderaufenthalt) anbieten,
   oder untere 600 mm geschlossen hinterlegen? Das ist ein Haftungsthema, kein
   Geometriethema.
3. **„Diamond Lattice"** (`shop-decision-3`) trifft 4.2.3 direkt (schräge Elemente +
   vorspringende Scheiben). Vorsprung auf ≤ 30 mm begrenzen, Raute erst ab 600 mm
   beginnen, oder nur nach 4.2.5?
4. **„Ellipse Sheet" in Zone A** (`shop-decision-4`) — normgedeckt sicher ist nur
   „Ausschnitt passt in Ø 40 mm". Soll der Generator dort automatisch umschalten, oder
   eine Prüferfreigabe voraussetzen?
5. **Nutzungskategorie** (`shop-decision-5`) 0,5 kN/m (Wohnen) oder 1,0 kN/m
   (Büro/öffentlich)? Verdoppelt die Riegeldurchbiegung und entscheidet über die
   Profilwahl.
6. **Riegelprofil für Holzmuster** (`shop-decision-6`) — Rechteckrohr 40 × 20 × 2 in den
   Profilkatalog aufnehmen? Aktuell steht dort für die zweite Stabfamilie nur Flachstahl
   zur Verfügung.
7. **Bundesland** (`shop-decision-7`) — die OIB-RL 4 gilt über Landesrecht, die Länder
   setzen unterschiedliche Fassungen (2015/2019/2023) in Kraft.
8. **ÖNORM B 5371:2021 beschaffen?** (`shop-decision-8`) ~260 EUR. Der ausführende Betrieb
   hat sie mit hoher Wahrscheinlichkeit im Haus (die Bundesinnung war am Normenausschuss
   beteiligt).
9. **Statik-Typprüfung** (`shop-decision-9`) für ein Blechpaneel 1100 × 900 bei 0,5 kN/m
   + Wind — einmalig nötig, wenn die Paneele als tragende Absturzsicherung verkauft
   werden. Danach ist es im Generator eine parametrische Interpolation.
10. **Bongossi** (`shop-decision-10`, 1100 kg/m³) ist im Geländerbau unüblich — in der
    Holzartenliste lassen?
