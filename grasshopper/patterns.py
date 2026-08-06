#! python 3
# Railing Generator - parametric railing and infill-pattern engine
# Copyright (C) 2026 Gleinkaa
#
# SPDX-License-Identifier: AGPL-3.0-only
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. It is distributed WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE. See the GNU Affero General Public License for more details.
#
# A commercial licence without the copyleft obligation is available:
# see COMMERCIAL-LICENSE.md.

# -*- coding: utf-8 -*-
"""Muster-Engine — die 34 Fuellmuster als Geometrie.

Der Mustersatz ist eine eigene Zusammenstellung dieses Projekts.
Regeln: Research/Musterkatalog_Rework_Instructions.md

Grundsatz (K1/K2/K3 aus den Rework-Instructions): JEDES Element haengt an einer
Struktur. Freie Enden gibt es nicht. Zulaessige Anschluesse sind
  t = 0    Untergurt,
  t = H    Handlauf,
  s = 0/L  Posten,
  ein Zwischenriegel, den das Muster SELBST als durchlaufenden Stab (Kanal b)
  mit ausgibt und der damit ebenfalls von Posten zu Posten spannt.
Zufallsmuster laufen ueber einen festen Seed je Feld — gleiche Eingaben,
gleiche Geometrie, kalkulierbare Stueckliste.

Lokales Feldsystem je Feld (Bay):
    O  = Startpunkt des Untergurt-Segments
    Xh = Einheitsvektor entlang des Untergurts (also MIT der Steigung geneigt)
    Yh = Einheitsvektor nach oben (lotrecht)
    Nh = Einheitsvektor nach aussen (von der Treppe weg)
    P(s, t) = O + Xh*s + Yh*t          s in [0, L],  t in [0, H]
Ein Stab bei konstantem s steht damit LOTRECHT (nicht normal zur Steigung),
und s laeuft als Bogenlaenge die Neigung entlang — beides so, wie ein Geländer
tatsaechlich gebaut wird.

Ausgabekanaele:
    a     Staebe, Profil "Fuellstab"  -> Sweep + BOM ueber kg/m
    b     Staebe, Profil "Diagonal"   -> Sweep + BOM ueber kg/m (2. Stabfamilie,
                                         Zwischenriegel, vorgesetzte Baender)
    st    Stahl-Solids (Bleche, Flachstaehle mit wechselnder Breite, tordierte
          Staebe) -> BOM ueber Volumen * Stahldichte
    hz    Holz-Solids                  -> BOM ueber Volumen * Rohdichte Holz
"""
import math
import random

import Rhino.Geometry as rg

TOL = 0.001
DEG = math.pi / 180.0

# --------------------------------------------------------------- Katalogdaten
# Pflichtfelder je Design nach Musterkatalog_Rework_Instructions.md Abschnitt 4.
#   rap    Rapport = Wiederholeinheit in mm ueber die Feldbreite. Reststueck am
#          Feldende wird nie abgeschnitten: die Einheitenzahl wird gerundet und
#          der Rapport auf die tatsaechliche Feldbreite gedehnt/gestaucht.
#   gap    True  = die Oeffnungsweite dieses Musters wird direkt vom Rapport
#                  bestimmt -> Rapport wird auf Gmax + Stabbreite gedeckelt.
#          False = die Oeffnung entsteht aus der Musterform, nicht aus dem
#                  Rapport -> Deckelung waere wirkungslos, Bewertung steht in norm.
#   norm   Bewertung nach OIB-Richtlinie 4, Ausgabe Mai 2023 (im Wortlaut
#          geprueft). Die beiden massgebenden Punkte:
#            4.2.4  Oeffnungen duerfen ZUMINDEST IN EINER RICHTUNG nicht
#                   groesser als 12 cm sein. Oesterreich prueft also KEINE
#                   120-mm-Kugel wie Deutschland, sondern eine
#                   Richtungsbedingung — ein 40 x 700 mm Schlitz ist konform.
#            4.2.3  Zwischen 15 cm und 60 cm ueber Stufenvorderkante duerfen
#                   keine horizontalen oder schraegen Elemente liegen, ausser
#                   sie springen nicht mehr als 3 cm vor, die Oeffnungen sind
#                   vertikal <= 2 cm, oder es ist ein Lochblech mit Loch
#                   Ø <= 4 cm. Einen Grenzwinkel nennt die Richtlinie NICHT —
#                   deshalb ist er hier ein Regler (Kw), Default 60 deg nach
#                   Sachverstaendigenpraxis, 75 deg als konservative Variante.
#          OENORM B 5371:2021 ist kostenpflichtig und wurde nicht im Volltext
#          geprueft; bei Widerspruch gilt ohnehin die OIB-RL 4 (verbindlich
#          ueber die Bautechnikverordnungen der Laender).
#   description
#          Kurzbeschreibung des Musters in einem Satz (max. 2 gedruckte
#          Zeilen).
#   profile
#          Ausgabekanal -> (Rollenliste in profiles.py, 0-basierter
#          Index in dieser Liste). Stab1 wird mit dem Fuellstab-Profil
#          gesweept (INFILL, Default 0), Stab2 mit dem Diagonal-Profil
#          (INFILL, Default DIAGONAL_INFILL_INDEX = 4). Stahl- und
#          Holz-Solids werden ueber Volumen x Dichte verwogen und haben
#          deshalb GAR KEINE Profilzeile — sie stehen mit None da statt mit
#          einem erfundenen Index. Eingetragen ist die Zeile, mit der die
#          Engine den Kanal in der Grundeinstellung baut; ein musterweiser
#          Vorzugsquerschnitt ist in der Engine nicht verdrahtet (die
#          Profilregler gelten global) und waere hier eine unbelegte
#          Behauptung — siehe docs/patterns-and-code.md, Abschnitt
#          "Open fabrication decisions", Punkt 6.
#   status 'done' oder 'open:<Verweis>'. Verweise "detail-X.Y" gehen auf
#          Research/Musterkatalog_Rework_Instructions.md Abschnitt X,
#          Verweise "shop-decision-N" auf docs/patterns-and-code.md,
#          Abschnitt "Open fabrication decisions", Punkt N. open heisst: die
#          KONSTRUKTIONSFRAGE ist offen und darf nicht von Agenten
#          beantwortet werden — nicht, dass das Muster unzulaessig waere.
#          Die Normbewertung steht in norm und ist davon unabhaengig.
DESIGNS = [
    # ------------------------------------------------------------- Formed
    dict(key='loop-u', name='U-Loop', fam='Formed', rap=120.0, gap=True,
         description='Paired bars joined by a U-bend that seats on the bottom rail',
         profile={'Stab1': ('INFILL', 0)},
         oben='Schenkel stumpf an den Handlauf geschweisst',
         unten='U-Bogen liegt auf dem Untergurt auf, beidseitig verschweisst',
         verb='keine Kreuzungen — jede Schlaufe ist ein Bauteil aus Rundstahl gebogen',
         sonder=None, zufall=None,
         norm='OIB 4.2.4 konform bei lichter Weite <= Gmax. 4.2.3: Bogenscheitel liegt waagrecht — Zone A pruefen (Kanal Norm).',
         status='open:detail-6.3'),
    dict(key='panel-stagger', name='Staggered Panels', fam='Formed', rap=100.0, gap=False,
         description='Offset timber blocks carried on steel rails, staggered per bay',
         profile={'Stab2': ('INFILL', 4), 'Holz': None},
         oben='Holzbloecke enden frei — Last traegt der Stahlriegel',
         unten='2 Flachstahlriegel spannen Posten zu Posten, Holz davor verschraubt',
         verb='Holz auf Riegel verschraubt (Langloch quer zur Faser)',
         sonder='Holz', zufall='seed + Feldindex, Blockhoehe 0.42..0.72*H',
         norm='OIB 4.2.3 kritisch: die versetzten Block-Oberkanten sind Trittkanten. Zulaessig nur ueber Vorsprung <= 30 mm.',
         status='open:shop-decision-5'),
    dict(key='ray-diamond', name='Ray Diamond', fam='Formed', rap=340.0, gap=False,
         description='Radiating bars inside diamond frames, fine and open',
         profile={'Stab1': ('INFILL', 0), 'Stab2': ('INFILL', 4)},
         oben='Rautenspitze am Handlauf angeschweisst',
         unten='Rautenspitze am Untergurt angeschweisst',
         verb='Strahlen an den Rautenrahmen geschweisst, Rahmen an Nachbarraute',
         sonder=None, zufall=None,
         norm='OIB 4.2.4 bedingt: Rautenfeld > 120 mm in beiden Richtungen. Strahlen unterteilen es nur teilweise.',
         status='done'),
    dict(key='bar-bead', name='Beaded Bars', fam='Formed', rap=115.0, gap=True,
         description='Vertical bars threaded with round discs at mid height',
         profile={'Stab1': ('INFILL', 0), 'Stab2': ('INFILL', 4)},
         oben='Stab am Handlauf angeschweisst',
         unten='Stab am Untergurt angeschweisst',
         verb='Ringe auf die Staebe aufgeschoben und verschweisst',
         sonder=None, zufall=None,
         norm='OIB 4.2.4 konform bei lichter Weite <= Gmax. Ringe springen vor — 4.2.3 Vorsprung <= 30 mm pruefen.',
         status='done'),
    dict(key='vee-pair', name='Vee Pairs', fam='Formed', rap=95.0, gap=True,
         description='Alternating V-shaped bar pairs, apex down on the bottom rail',
         profile={'Stab1': ('INFILL', 0)},
         oben='beide Schenkelenden am Handlauf',
         unten='Scheitel auf dem Untergurt',
         verb='Scheitel gebogen, keine Schweissnaht in der Spitze',
         sonder=None, zufall=None,
         norm='OIB 4.2.3: Schenkel praktisch lotrecht (>80 deg bei ueblichen Feldern, Horizontalprojektion max. halber Rapport) — Zone A unkritisch, solange steiler als Kw.',
         status='done'),
    dict(key='panel-slat', name='Wide Slats', fam='Formed', rap=140.0, gap=False,
         description='Broad timber lamellas held in a steel frame, narrow joints',
         profile={'Stab2': ('INFILL', 4), 'Holz': None},
         oben='Holzlamelle endet frei unter dem Handlauf',
         unten='2 Flachstahlriegel tragen, Holz davor verschraubt',
         verb='Holz auf Riegel verschraubt (Langloch quer zur Faser)',
         sonder='Holz', zufall=None,
         norm='OIB 4.2.4 konform (geschlossene Flaeche, Fuge 8-12 mm). 4.2.3 unkritisch, da durchgehend vertikal.',
         status='open:shop-decision-5'),
    dict(key='arch-stack', name='Stacked Arches', fam='Formed', rap=155.0, gap=False,
         description='Two rows of arches divided by an intermediate rail',
         profile={'Stab1': ('INFILL', 0), 'Stab2': ('INFILL', 4)},
         oben='grosse Boegen am Handlauf',
         unten='kleine Boegen auf dem Untergurt',
         verb='Zwischenriegel spannt Posten zu Posten, Boegen beidseitig angeschweisst',
         sonder=None, zufall=None,
         norm='OIB 4.2.4 bedingt: Bogenfelder > 120 mm. 4.2.3: Bogenscheitel waagrecht — Zone A pruefen.',
         status='open:detail-6.3'),
    dict(key='hook-j', name='J-Hooks', fam='Formed', rap=135.0, gap=True,
         description='Bars bent into a J, the arched foot resting on the bottom rail',
         profile={'Stab1': ('INFILL', 0), 'Stab2': ('INFILL', 4)},
         oben='langer Schenkel am Handlauf, Rueckläufer endet am Zwischenriegel',
         unten='U-Bogen liegt auf dem Untergurt auf',
         verb='J-Haken aus einem Stueck gebogen; Rueckläufer an den Zwischenriegel geschweisst',
         sonder=None, zufall=None,
         norm='OIB 4.2.4 konform bei lichter Weite <= Gmax. 4.2.3: U-Bogen unten liegt meist unter 150 mm — pruefen.',
         status='open:detail-6.3'),
    dict(key='lattice-diamond', name='Diamond Lattice', fam='Formed', rap=210.0, gap=False,
         description='Diamond grid with disc accents at the crossings',
         profile={'Stab1': ('INFILL', 0), 'Holz': None},
         oben='Rautenspitze am Handlauf',
         unten='Rautenspitze am Untergurt, Aussenspitzen an den Posten',
         verb='Rauten an den Spitzen miteinander, mit den Gurten und den Posten verschweisst — keine Stabkreuzungen',
         sonder='Holz (nur Scheiben-Akzente)', zufall=None,
         norm='OIB 4.2.3 direkter Treffer (schraege Elemente + vorspringende Scheiben). Nur mit Vorsprung <= 30 mm oder Raute erst ab 600 mm.',
         status='open:shop-decision-3'),
    dict(key='loop-drop', name='Loop and Drop', fam='Formed', rap=180.0, gap=False,
         description='Wide bottom loops carrying a teardrop stem to the handrail',
         profile={'Stab1': ('INFILL', 0), 'Stab2': ('INFILL', 4)},
         oben='Tropfen-Stiel am Handlauf',
         unten='Schlaufenschenkel auf dem Untergurt',
         verb='Tropfenspitze auf den Schlaufenbogen geschweisst — beide Teile haengen zusammen',
         sonder=None, zufall=None,
         norm='OIB 4.2.4 bedingt: der Schlaufenbogen bildet Oeffnung > 120 mm. 4.2.3: Bogenscheitel waagrecht.',
         status='open:detail-6.3'),
    # ------------------------------------------------------------ Organic
    dict(key='panel-segment', name='Segmented Panels', fam='Organic', rap=85.0, gap=False,
         description='Timber segments stacked in two or three per column on three rails',
         profile={'Stab2': ('INFILL', 4), 'Holz': None},
         oben='oberstes Segment endet frei unter dem Handlauf',
         unten='3 Flachstahlriegel (0,25/0,50/0,75 H) tragen, Holzsegmente davor '
               'verschraubt — der mittlere traegt das Mittelsegment der Dreierstapel',
         verb='je Segment 1 Schraube pro Riegel, Fuge zwischen den Segmenten',
         sonder='Holz', zufall='seed + Feldindex, 2..3 Segmente je Spalte',
         norm='OIB 4.2.3: jede Stapelfuge ist eine horizontale Trittkante. Segmentdicke <= 30 mm oder Fugen ausserhalb 150-600 mm.',
         status='open:shop-decision-5'),
    dict(key='sheet-ellipse', name='Ellipse Sheet', fam='Organic', rap=140.0, gap=False,
         description='Laser-cut sheet with elliptical voids, edges captured in channel',
         profile={'Stahl': None},
         oben='Blechkante in U-Profil am Handlauf gefasst',
         unten='Blechkante in U-Profil am Untergurt gefasst',
         verb='Blech lasergeschnitten, umlaufend eingefasst — keine Stabkreuzungen',
         sonder='Laserblech', zufall=None,
         norm='OIB 4.2.4: Nebenachse <= 120 mm. In Zone A normgedeckt nur, wenn der Ausschnitt in einen Kreis Ø 40 mm passt (Lochblech-Ausnahme).',
         status='open:shop-decision-4'),
    dict(key='rake-random', name='Random Rake', fam='Organic', rap=45.0, gap=False,
         description='Densely raked bars at irregular angles, seeded per bay',
         profile={'Stab1': ('INFILL', 0)},
         oben='jeder Halm am Handlauf angeschweisst',
         unten='jeder Halm am Untergurt angeschweisst',
         verb='Halme kreuzen sich frei, Kreuzungen nicht verbunden',
         sonder=None, zufall='seed + Feldindex, Fusspunkt und Neigung je Halm',
         norm='OIB 4.2.3: geneigte Halme. Zone A nur zulaessig, wenn steiler als die eingestellte Winkelgrenze.',
         status='open:shop-decision-1'),
    dict(key='weave-band', name='Woven Bands', fam='Organic', rap=125.0, gap=False,
         description='Curved diagonal bands crossing over and under each other',
         profile={'Stab1': ('INFILL', 0), 'Stab2': ('INFILL', 4)},
         oben='beide Bandrichtungen am Handlauf',
         unten='beide Bandrichtungen am Untergurt',
         verb='Baender kreuzen mittig, an der Kreuzung verschweisst',
         sonder=None, zufall=None,
         norm='OIB 4.2.4: Maschen zwischen den Baendern pruefen. 4.2.3: Bandtangente wird in Zone A flach.',
         status='done'),
    dict(key='sheet-grain', name='Grain Sheet', fam='Organic', rap=125.0, gap=False,
         description='Laser-cut sheet with irregular vertical strips, grain-like',
         profile={'Stahl': None},
         oben='Blechkante in U-Profil am Handlauf gefasst',
         unten='Blechkante in U-Profil am Untergurt gefasst',
         verb='Blech lasergeschnitten, umlaufend eingefasst',
         sonder='Laserblech', zufall='seed + Feldindex, Streifenbreite',
         norm='OIB 4.2.4 guenstigste Blechvariante (Richtungsbedingung, Streifen durchlaufend vertikal). 4.2.3: keine Schlitzenden zwischen 150 und 600 mm.',
         status='done'),
    dict(key='bar-cross-fine', name='Fine Crossings', fam='Organic', rap=80.0, gap=True,
         description='Slim verticals overlaid with short diagonal crossings',
         profile={'Stab1': ('INFILL', 0), 'Stab2': ('INFILL', 4)},
         oben='Staebe und Diagonalen am Handlauf',
         unten='Staebe und Diagonalen am Untergurt',
         verb='Diagonalen vor die Staebe gesetzt und an den Kreuzungen geheftet',
         sonder=None, zufall=None,
         norm='OIB 4.2.4 konform ueber das Vertikalfeld. 4.2.3: die Diagonalen liegen in Zone A — Vorsprung <= 30 mm.',
         status='done'),
    # ------------------------------------------------------------- Rhythm
    dict(key='bar-wave', name='Wave Bars', fam='Rhythm', rap=95.0, gap=True,
         description='Vertical bars displaced along a sine, one wavelength per bay',
         profile={'Stab1': ('INFILL', 0)},
         oben='Stabende am Handlauf, Tangente annaehernd lotrecht (Bezier, < 10 deg)',
         unten='Stabende am Untergurt, Tangente annaehernd lotrecht (Bezier, < 10 deg)',
         verb='keine Kreuzungen — jeder Stab ein Bauteil, kalt gebogen',
         sonder=None, zufall=None,
         norm='OIB 4.2.4 konform bei lichter Weite <= Gmax. Tangente bleibt ueberall steil.',
         status='done'),
    dict(key='chevron-h', name='Horizontal Chevron', fam='Rhythm', rap=185.0, gap=False,
         description='Stacked horizontal chevrons, apex alternating left and right',
         profile={'Stab1': ('INFILL', 0), 'Stab2': ('INFILL', 4)},
         oben='oberste Zackenreihe endet am Handlauf',
         unten='unterste Zackenreihe endet am Untergurt',
         verb='jede Reihe spannt durchlaufend von Posten zu Posten',
         sonder=None, zufall=None,
         norm='OIB 4.2.3 kritisch: Zackenreihen wirken waagrecht. In Zone A lichter Spalt <= 20 mm noetig.',
         status='done'),
    dict(key='line-density', name='Density Lines', fam='Rhythm', rap=40.0, gap=True,
         gapf=0.78,
         description='Fine verticals whose spacing tightens and opens across the bay',
         profile={'Stab1': ('INFILL', 0)},
         oben='Stab am Handlauf', unten='Stab am Untergurt',
         verb='keine Kreuzungen',
         sonder=None, zufall=None,
         norm='OIB 4.2.4: Dichte-Modulation schwankt um +-28 % — massgebend ist die WEITESTE Oeffnung; der Rapport-Deckel ist dafuer um Faktor 0.78 verschaerft (gapf).',
         status='done'),
    dict(key='bar-width-wave', name='Width Wave', fam='Rhythm', rap=70.0, gap=True,
         description='Bars whose width swells and shrinks along a wave',
         profile={'Stahl': None},
         oben='Flachstahl am Handlauf', unten='Flachstahl am Untergurt',
         verb='keine Kreuzungen — Breite variiert, Dicke konstant',
         sonder='Flachstahl mit wechselnder Breite (Laserzuschnitt)', zufall=None,
         norm='OIB 4.2.4 konform bei lichter Weite <= Gmax. Durchgehend vertikal.',
         status='done'),
    dict(key='bar-alternate', name='Alternating Bars', fam='Rhythm', rap=100.0, gap=True,
         description='Wide and narrow bars alternating in a fixed ratio',
         profile={'Stahl': None},
         oben='Flachstahl am Handlauf', unten='Flachstahl am Untergurt',
         verb='keine Kreuzungen — 2 Breiten im Wechsel',
         sonder='Flachstahl, 2 Breiten', zufall=None,
         norm='OIB 4.2.4 konform bei lichter Weite <= Gmax. Durchgehend vertikal.',
         status='done'),
    dict(key='grid-split', name='Split Grid', fam='Rhythm', rap=220.0, gap=False,
         description='Rectangular modules, each divided by one diagonal',
         profile={'Stab1': ('INFILL', 0), 'Stab2': ('INFILL', 4)},
         oben='Rasterstege am Handlauf', unten='Rasterstege am Untergurt',
         verb='Rasterknoten halb ueberblattet, Diagonalen eingeschweisst',
         sonder=None, zufall=None,
         norm='OIB 4.2.3: waagrechte Rasterstege und Diagonalen duerfen nicht in 150-600 mm liegen. Teilung entsprechend waehlen.',
         status='done'),
    dict(key='rake-cross', name='Crossed Rakes', fam='Rhythm', rap=90.0, gap=False,
         description='Two opposed rakes of bars crossing between the rails',
         profile={'Stab1': ('INFILL', 0)},
         oben='Kopf jedes Stabs am Handlauf', unten='Fuss jedes Stabs am Untergurt',
         verb='Kreuzungen nicht verbunden — Staebe liegen in einer Ebene versetzt',
         sonder=None, zufall='seed + Feldindex, Kopfversatz je Stab, +-1.6 Rapport',
         norm='OIB 4.2.3: geneigte Staebe. Zone A nur, wenn steiler als die Winkelgrenze.',
         status='open:detail-6.6, shop-decision-1'),
    dict(key='bar-scatter', name='Scattered Diagonals', fam='Rhythm', rap=100.0, gap=True,
         description='Even verticals with diagonals scattered between them',
         profile={'Stab1': ('INFILL', 0), 'Stab2': ('INFILL', 4)},
         oben='Staebe und Diagonalen am Handlauf',
         unten='Staebe und Diagonalen am Untergurt',
         verb='Diagonalen vorgesetzt, an Kreuzungen geheftet',
         sonder=None, zufall=None,
         norm='OIB 4.2.4 konform ueber das Vertikalfeld. 4.2.3: Diagonalen aus Zone A heraushalten oder Vorsprung <= 30 mm.',
         status='done'),
    dict(key='wave-overlay', name='Wave Overlay', fam='Rhythm', rap=60.0, gap=True,
         description='Straight bar field with wave bands set in front of it',
         profile={'Stab1': ('INFILL', 0), 'Stab2': ('INFILL', 4)},
         oben='Staebe am Handlauf', unten='Staebe am Untergurt',
         verb='Wellenbaender aus Flachstahl VORGESETZT (Auslage), an jedem Kreuzungsstab geheftet',
         sonder=None, zufall=None,
         norm='OIB 4.2.3 kritisch: die vorgesetzten Baender sind waagrecht UND springen um die Auslage vor. Auslage <= 30 mm halten.',
         status='done'),
    # -------------------------------------------------------------- Lines
    dict(key='bar-graded', name='Graded Bars', fam='Lines', rap=85.0, gap=True,
         description='Vertical bars stepping through several thicknesses',
         profile={'Stab1': ('INFILL', 0), 'Stab2': ('INFILL', 4)},
         oben='alle Staebe am Handlauf', unten='alle Staebe am Untergurt',
         verb='keine Kreuzungen — jeder 3. Stab im staerkeren Profil',
         sonder=None, zufall=None,
         norm='OIB 4.2.4 konform bei lichter Weite <= Gmax. Durchgehend vertikal.',
         status='open:detail-6.6'),
    dict(key='frame-u', name='U-Frames', fam='Lines', rap=140.0, gap=True,
         description='Open U-frames standing side by side on the bottom rail',
         profile={'Stab1': ('INFILL', 0)},
         oben='beide Schenkel am Handlauf',
         unten='Querstueck liegt auf dem Untergurt auf',
         verb='U aus einem Stueck gekantet, Querstueck auf den Untergurt geschweisst',
         sonder=None, zufall=None,
         norm='OIB 4.2.4 konform bei lichter Weite <= Gmax. 4.2.3: das Querstueck liegt auf dem Untergurt, meist unter 150 mm — pruefen.',
         status='done'),
    dict(key='bar-railed', name='Railed Bars', fam='Lines', rap=90.0, gap=True,
         description='Vertical bars articulated by horizontal cross rails',
         profile={'Stab1': ('INFILL', 0), 'Stab2': ('INFILL', 4)},
         oben='Staebe am Handlauf', unten='Staebe am Untergurt',
         verb='2 Querriegel durchlaufend von Posten zu Posten, Staebe daran geheftet',
         sonder=None, zufall=None,
         norm='OIB 4.2.3: die 2 Querriegel sind waagrecht. Mindestens einer liegt typisch in Zone A — Lage pruefen.',
         status='done'),
    dict(key='flat-horizontal', name='Horizontal Flats', fam='Lines', rap=175.0, gap=True,
         description='Horizontal flat sections carried by intermediate posts',
         profile={'Stab1': ('INFILL', 0), 'Stab2': ('INFILL', 4)},
         oben='oberstes Flachprofil unter dem Handlauf',
         unten='unterstes Flachprofil ueber dem Untergurt',
         verb='Flachprofile an Posten und Zwischenpfosten geschweisst',
         sonder=None, zufall=None,
         norm='OIB 4.2.3 praktisch K.O.: reine Horizontalteilung. In Zone A waere lichter Spalt <= 20 mm noetig — das sind dann keine Horizontal-Flachprofile mehr.',
         status='open:detail-6.6, shop-decision-2'),
    dict(key='hatch-45', name='45 Degree Hatch', fam='Lines', rap=70.0, gap=True,
         description='Dense uniform hatch at 45 degrees, louvre-like',
         profile={'Stab1': ('INFILL', 0)},
         oben='Schraffurenden am Handlauf oder am Posten',
         unten='Schraffurenden am Untergurt oder am Posten',
         verb='keine Kreuzungen — einseitige 45deg-Schar',
         sonder=None, zufall=None,
         norm='OIB 4.2.3: 45-deg-Schar = Leitersprossen. In Zone A unzulaessig ohne Zusatzmassnahme.',
         status='done'),
    dict(key='bar-vertical', name='Vertical Bars', fam='Lines', rap=110.0, gap=True,
         description='Evenly spaced vertical bars, the reference infill',
         profile={'Stab1': ('INFILL', 0)},
         oben='Stab am Handlauf', unten='Stab am Untergurt',
         verb='keine Kreuzungen',
         sonder=None, zufall=None,
         norm='OIB 4.2.4 konform (Referenzfall), lichte Weite <= Gmax. 4.2.3 unkritisch.',
         status='done'),
    dict(key='bar-twist', name='Twisted Bars', fam='Lines', rap=120.0, gap=True,
         description='Square bars twisted about their own axis',
         profile={'Stahl': None},
         oben='Stab am Handlauf', unten='Stab am Untergurt',
         verb='keine Kreuzungen — Vierkantstab um die eigene Achse tordiert',
         sonder='tordierter Vierkantstab (Sonderfertigung)', zufall=None,
         norm='OIB 4.2.4 konform bei lichter Weite <= Gmax. 4.2.3 unkritisch, durchgehend vertikal.',
         status='done'),
    dict(key='rake-uniform', name='Uniform Rake', fam='Lines', rap=80.0, gap=True,
         description='Fine bars raked at one constant angle',
         profile={'Stab1': ('INFILL', 0)},
         oben='Diagonalende am Handlauf oder am Posten',
         unten='Diagonalende am Untergurt oder am Posten',
         verb='keine Kreuzungen — einheitliche Neigung',
         sonder=None, zufall=None,
         norm='OIB 4.2.3: einheitliche Neigung. Zone A nur, wenn steiler als die Winkelgrenze.',
         status='open:shop-decision-1'),
    dict(key='vee-center', name='Centre Vee', fam='Lines', rap=95.0, gap=True,
         description='Vertical bars kinked into a shallow V at mid height',
         profile={'Stab1': ('INFILL', 0)},
         oben='oberer Schenkel am Handlauf', unten='unterer Schenkel am Untergurt',
         verb='Knick auf halber Hoehe, aus einem Stueck gekantet',
         sonder=None, zufall=None,
         norm='OIB 4.2.3: die Knickpunkte liegen alle auf halber Hoehe und bilden eine Reihe. Lage gegen Zone A pruefen.',
         status='open:detail-6.3'),
]


# ------------------------------------------------------------------- Kontext
class Bay(object):
    """Ein Feld zwischen zwei Posten, mit lokalem (s, t)-System."""

    def __init__(self, lo, hi, nrm, seed):
        self.O = lo.PointAtStart
        d = lo.PointAtEnd - self.O
        self.L = d.Length
        xh = rg.Vector3d(d)
        xh.Unitize()
        self.Xh = xh
        up = hi.PointAtStart - self.O
        self.H = up.Length
        yh = rg.Vector3d(up)
        yh.Unitize()
        self.Yh = yh
        n = rg.Vector3d(nrm)
        n.Unitize()
        self.Nh = n
        self.rnd = random.Random(seed)
        self.a = []   # Staebe, Profil Fuellstab
        self.b = []   # Staebe, Profil Diagonal
        self.st = []  # Stahl-Solids
        self.hz = []  # Holz-Solids

    # -- Abbildung ---------------------------------------------------------
    def P(self, s, t, off=0.0):
        return self.O + self.Xh * s + self.Yh * t + self.Nh * off

    def st_of(self, p):
        """Umkehrung von P(): Weltpunkt -> (s, t).

        Xh und Yh sind NICHT orthogonal (Xh folgt der Steigung, Yh ist lotrecht),
        deshalb ist d*Xh nicht s. Geloest wird ueber die Gram-Matrix der beiden
        Basisvektoren. Vorher stand hier das nackte Skalarprodukt — die
        Anschlusspruefung hat damit jedes einzelne Stabende als "frei" gemeldet,
        obwohl die Geometrie stimmte.
        """
        d = p - self.O
        k = self.Xh * self.Yh
        dx = d * self.Xh
        dy = d * self.Yh
        det = 1.0 - k * k
        if abs(det) < 1e-9:
            return dx, dy
        return (dx - k * dy) / det, (dy - k * dx) / det

    def units(self, rap):
        """Einheitenzahl und gedehnter Rapport — das Reststueck wird verteilt,
        nie abgeschnitten (Rework-Instructions Abschnitt 4, Feld `rapport`)."""
        n = int(round(self.L / max(rap, 1.0)))
        if n < 1:
            n = 1
        return n, self.L / n

    # -- Kurven ------------------------------------------------------------
    def seg(self, s0, t0, s1, t1, ch='a', off=0.0):
        c = rg.LineCurve(self.P(s0, t0, off), self.P(s1, t1, off))
        if c.GetLength() > TOL:
            getattr(self, ch).append(c)

    def poly(self, pts, ch='a', off=0.0):
        """Polygonzug — aber als EINZELNE Segmente.

        Ein Sweep1 ueber eine geknickte Schiene liefert je nach Knickwinkel
        mehrere Breps (Stacked Arches: 56 Schienen -> 84 Koerper) oder scheitert
        ganz (Ray Diamond, geschlossene Raute: "Sweep could not be created"). Beides
        zerstoert die Invariante Koerper == Mittellinien, die hier der einzige
        Waechter gegen stille Sweep-Fehler ist. Also wird jedes knickfreie
        Stueck als eigene Schiene ausgegeben. Fuer die Stueckliste ist das
        egal — sie rechnet ueber die Gesamtlaenge — und die Fertigung liest
        die Bauteilgrenzen ohnehin aus dem Feld `verbindungen`.
        """
        for i in range(len(pts) - 1):
            self.seg(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], ch, off)

    def arc(self, p0, pm, p1, ch='a', off=0.0):
        a = rg.Arc(self.P(p0[0], p0[1], off), self.P(pm[0], pm[1], off),
                   self.P(p1[0], p1[1], off))
        if a.IsValid:
            getattr(self, ch).append(rg.ArcCurve(a))

    def bez(self, p0, c0, c1, p1, ch='a', off=0.0):
        b = rg.BezierCurve([self.P(p0[0], p0[1], off), self.P(c0[0], c0[1], off),
                            self.P(c1[0], c1[1], off), self.P(p1[0], p1[1], off)])
        getattr(self, ch).append(b.ToNurbsCurve())

    def bow(self, p0, pm, p1, ch='a', off=0.0):
        """Bogen durch drei (s,t)-Punkte — als Bezier IM FELDSYSTEM, nicht als
        Welt-Kreis.

        Ein rg.Arc durch die drei Weltpunkte ist im geneigten Feld kein Bogen
        im Feldsystem mehr: Xh folgt der Steigung, Yh ist lotrecht, das System
        ist schiefwinklig, und der Kreis beult einseitig aus — das U von U-Loop
        tauchte im steilen Referenzfeld 49 mm unter den Untergurt, der kleine
        Bogen von Stacked Arches ragte 48 mm ueber den Posten hinaus. Ein Bezier ist
        affin-invariant (Kontrollpunkte abbilden == Kurve abbilden) und bleibt
        in der konvexen Huelle seiner Kontrollpunkte, also im Feld.
        Kontrollpunkte: Enden + (4/3)*(Scheitel - Sehnenmitte). Damit laeuft
        die Kurve bei u=0.5 exakt durch pm, und die Endtangenten sind parallel
        zu (Scheitel - Sehnenmitte) — die geraden Schenkel schliessen knickfrei
        an, der Sweep bleibt EIN Koerper je Schiene. Abweichung vom Kreisbogen
        maximal ~6 % des Bogenradius (hier < 3 mm), dafuer stimmt die Form in
        JEDER Feldneigung.
        """
        vs = (pm[0] - (p0[0] + p1[0]) / 2.0) * 4.0 / 3.0
        vt = (pm[1] - (p0[1] + p1[1]) / 2.0) * 4.0 / 3.0
        self.bez(p0, (p0[0] + vs, p0[1] + vt), (p1[0] + vs, p1[1] + vt), p1,
                 ch, off)

    def arc3(self, p0, pm, p1, ch='a', off=0.0):
        """Flacher Bogen durch drei (s,t)-Punkte — Bezier im Feldsystem.

        Wie bow(), aber fuer Boegen, deren Stichhoehe klein gegen die Sehne ist
        (Tropfen von Loop and Drop): dort muessen die Endtangenten sehnennah bleiben,
        nicht
        scheitelparallel. Kontrollpunkte p + (4/3)*(pm - p): trifft pm bei
        u=0.5, und die Kurve bleibt beweisbar im Kasten Sehne x Stichhoehe —
        der Welt-Kreisbogen ragte im steilen Feld bis 31 mm VOR den Posten.
        """
        self.bez(p0,
                 (p0[0] + (pm[0] - p0[0]) * 4.0 / 3.0,
                  p0[1] + (pm[1] - p0[1]) * 4.0 / 3.0),
                 (p1[0] + (pm[0] - p1[0]) * 4.0 / 3.0,
                  p1[1] + (pm[1] - p1[1]) * 4.0 / 3.0),
                 p1, ch, off)

    def part(self, curves, ch='a'):
        """Ein gebogenes Bauteil als seine knickfreien Stuecke ablegen.

        Bewusst NICHT gejoint: siehe poly(). Die Teile bleiben geometrisch ein
        Bauteil (sie stossen exakt aneinander), nur die Schienenliste sieht sie
        einzeln — und genau das macht den Sweep verlaesslich.
        """
        target = getattr(self, ch)
        for c in curves:
            if c and c.GetLength() > TOL:
                target.append(c)

    # -- Solids ------------------------------------------------------------
    def _loops(self, loops, off):
        out = []
        for lp in loops:
            pl = rg.Polyline([self.P(s, t, off) for s, t in lp])
            if not pl.IsClosed:
                pl.Add(pl[0])
            out.append(rg.PolylineCurve(pl))
        return out

    def plate(self, loops, thick, ch='st', off=0.0):
        """Ebene Platte (Aussenkontur + beliebig viele Aussparungen), nach aussen
        extrudiert. Traegt Bleche UND Flachstaehle mit wechselnder Breite."""
        crvs = self._loops(loops, off)
        planar = rg.Brep.CreatePlanarBreps(crvs, TOL)
        if not planar:
            return
        path = rg.LineCurve(rg.Point3d(0, 0, 0), rg.Point3d(self.Nh * thick))
        for br in planar:
            solid = br.Faces[0].CreateExtrusion(path, True)
            if solid:
                getattr(self, ch).append(solid)

    def block(self, s0, t0, s1, t1, thick, ch='hz', off=0.0):
        """Quader in der Feldebene (Holzblock, Holzlamelle)."""
        self.plate([[(s0, t0), (s1, t0), (s1, t1), (s0, t1)]], thick, ch, off)

    def twisted(self, s, t0, t1, w, half_turns=1.0, steps=9, ch='st'):
        """Tordierter Vierkantstab: gedrehte Querschnitte, gerade dazwischen
        gelooft. Ein Sweep1 mit festem Profil kann die Torsion nicht abbilden,
        deshalb faellt dieser Stab als Solid an und wird ueber sein Volumen
        verwogen statt ueber kg/m. half_turns zaehlt HALBE Umdrehungen (der
        alte Name `turns` versprach volle und lieferte halbe)."""
        secs = []
        h = w / 2.0
        # Querschnitt HORIZONTAL aufspannen, nicht entlang Xh: Xh folgt der
        # Steigung, damit kippten die Sektionen um den Steigungswinkel und der
        # Loft war ein gescherter Koerper (~16 % Querschnittsverzerrung im
        # steilen Feld) statt eines Vierkantstabs mit konstantem Querschnitt
        # senkrecht zur lotrechten Achse.
        hh = rg.Vector3d(self.Xh.X, self.Xh.Y, 0.0)
        if not hh.Unitize():
            hh = rg.Vector3d(self.Xh)
        for i in range(steps):
            f = i / float(steps - 1)
            ang = half_turns * math.pi * f
            ca, sa = math.cos(ang), math.sin(ang)
            t = t0 + (t1 - t0) * f
            pts = []
            for dx, dn in ((-h, -h), (h, -h), (h, h), (-h, h), (-h, -h)):
                rx = dx * ca - dn * sa
                rn = dx * sa + dn * ca
                pts.append(self.P(s, t) + hh * rx + self.Nh * rn)
            secs.append(rg.PolylineCurve(rg.Polyline(pts)))
        lofts = rg.Brep.CreateFromLoft(secs, rg.Point3d.Unset, rg.Point3d.Unset,
                                       rg.LoftType.Straight, False)
        for br in lofts:
            capped = br.CapPlanarHoles(TOL)
            getattr(self, ch).append(capped if capped else br)


# ------------------------------------------------------------------- Muster
def p_loop_u(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        r = st * 0.34
        s0 = i * st + st * 0.5 - r
        s1 = s0 + 2 * r
        y.seg(s0, y.H, s0, r, 'a')
        y.bow((s0, r), (s0 + r, 0.0), (s1, r), 'a')
        y.seg(s1, r, s1, y.H, 'a')


def p_panel_stagger(y, rap):
    n, st = y.units(rap)
    rails = (0.30 * y.H, 0.70 * y.H)
    for r in rails:
        y.seg(0.0, r, y.L, r, 'b')
    for i in range(n):
        bh = y.H * (0.42 + y.rnd.random() * 0.30)
        # Luftspalt wie bei Wide Slats/Segmented Panels: die Musterbeschreibung
        # sagt "Holzbloecke enden
        # frei" — ohne Klemmung stiessen Bloecke buendig an Handlauf oder
        # Untergurt (im Render sichtbar). Zufallsfolge unveraendert: weiterhin
        # genau ein random()-Zug fuer die Lage.
        span = max(0.0, y.H - bh - 2.0 * HOLZ_LUFT)
        bt = HOLZ_LUFT + span * y.rnd.random()
        # K2: jeder Block muss mindestens EINEN Riegel ueberdecken, sonst haengt
        # er in der Luft. Statt zu verwerfen wird er auf den naechsten Riegel
        # geschoben — das Muster bleibt zufaellig, die Konstruktion bleibt gueltig.
        if not any(bt <= r <= bt + bh for r in rails):
            near = min(rails, key=lambda r: abs(r - (bt + bh / 2.0)))
            bt = max(HOLZ_LUFT, min(y.H - bh - HOLZ_LUFT, near - bh / 2.0))
        y.block(i * st + st * 0.12, bt, i * st + st * 0.88, bt + bh, HOLZ_D, 'hz',
                HOLZ_OFF)


def p_ray_diamond(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        cs, ct = st * (i + 0.5), y.H / 2.0
        rx, ry = st * 0.5, y.H / 2.0
        y.poly([(cs - rx, ct), (cs, ct + ry), (cs + rx, ct), (cs, ct - ry),
                (cs - rx, ct)], 'a')
        for k in range(12):
            ang = 2 * math.pi * k / 12.0
            ca, sa = math.cos(ang), math.sin(ang)
            d = 1.0 / (abs(ca) / rx + abs(sa) / ry)
            y.seg(cs, ct, cs + d * ca, ct + d * sa, 'b')


def p_bar_bead(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        s = st * (i + 0.5)
        y.seg(s, 0.0, s, y.H, 'a')
        for f in (0.33, 0.66):
            r = st * 0.22
            ct = y.H * f
            y.part([rg.ArcCurve(rg.Arc(y.P(s - r, ct), y.P(s, ct + r), y.P(s + r, ct))),
                    rg.ArcCurve(rg.Arc(y.P(s + r, ct), y.P(s, ct - r), y.P(s - r, ct)))], 'b')


def p_vee_pair(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        s0 = i * st
        y.poly([(s0, y.H), (s0 + st / 2.0, 0.0), (s0 + st, y.H)], 'a')


def p_panel_slat(y, rap):
    n, st = y.units(rap)
    for r in (0.25 * y.H, 0.75 * y.H):
        y.seg(0.0, r, y.L, r, 'b')
    for i in range(n):
        # Fuge absolut statt proportional: 0.12*st waren beim Nennrapport
        # schon 16,8 mm — der norm-Text bewertet aber eine 8-12-mm-Fuge.
        # HOLZ_LUFT (Default 8) ist dieselbe Konvention wie vertikal.
        y.block(i * st + HOLZ_LUFT / 2.0, HOLZ_LUFT,
                (i + 1) * st - HOLZ_LUFT / 2.0, y.H - HOLZ_LUFT,
                HOLZ_D, 'hz', HOLZ_OFF)


def p_arch_stack(y, rap):
    n, st = y.units(rap)
    rt = y.H * 0.38
    y.seg(0.0, rt, y.L, rt, 'b')
    for i in range(n):
        r = st * 0.36
        s0 = i * st + st * 0.5 - r
        s1 = s0 + 2 * r
        y.seg(s0, y.H, s0, rt + r, 'a')
        y.bow((s0, rt + r), (s0 + r, rt), (s1, rt + r), 'a')
        y.seg(s1, rt + r, s1, y.H, 'a')
        r2 = st * 0.20
        s2 = i * st + st * 0.5 - r2
        s3 = s2 + 2 * r2
        y.seg(s2, 0.0, s2, rt - r2, 'a')
        y.bow((s2, rt - r2), (s2 + r2, rt), (s3, rt - r2), 'a')
        y.seg(s3, rt - r2, s3, 0.0, 'a')


def p_hook_j(y, rap):
    n, st = y.units(rap)
    rt = y.H * 0.45
    y.seg(0.0, rt, y.L, rt, 'b')
    for i in range(n):
        r = st * 0.26
        s = st * (i + 0.5) - r
        y.seg(s, y.H, s, r, 'a')
        y.bow((s, r), (s + r, 0.0), (s + 2 * r, r), 'a')
        y.seg(s + 2 * r, r, s + 2 * r, rt, 'a')


def p_lattice_diamond(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        cs = st * (i + 0.5)
        y.poly([(cs - st / 2.0, y.H / 2.0), (cs, y.H), (cs + st / 2.0, y.H / 2.0),
                (cs, 0.0), (cs - st / 2.0, y.H / 2.0)], 'a')
        d = min(st, y.H) * 0.16
        # SCHEIBE heisst rund: der block() lieferte ein schiefes Parallelogramm.
        # Im gestauchten Endfeld (d unter ~20 mm) entfaellt der Akzent ganz,
        # statt als Holz-Chip zu enden.
        if d > 20.0:
            y.plate([_ellipse_loop(cs, y.H / 2.0, d, d)], HOLZ_D, 'hz', HOLZ_OFF)


def p_loop_drop(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        cs = st * (i + 0.5)
        r = st * 0.30
        top = y.H * 0.62
        y.seg(cs - r, 0.0, cs - r, top - r, 'a')
        y.bow((cs - r, top - r), (cs, top), (cs + r, top - r), 'a')
        y.seg(cs + r, top - r, cs + r, 0.0, 'a')
        # Tropfen: Stiel am Handlauf, Spitze sitzt AUF dem Schlaufenbogen
        mid = (y.H * 0.88 + top) / 2.0
        y.seg(cs, y.H, cs, y.H * 0.88, 'b')
        y.arc3((cs, y.H * 0.88), (cs - r * 0.45, mid), (cs, top), 'b')
        y.arc3((cs, top), (cs + r * 0.45, mid), (cs, y.H * 0.88), 'b')


def p_panel_segment(y, rap):
    n, st = y.units(rap)
    # K2 wie bei Staggered Panels, nur eine Stufe frueher: JEDES Segment braucht einen
    # Riegel, auf den es geschraubt wird ("je Segment 1 Schraube pro Riegel").
    # Eine Spalte stapelt 2 ODER 3 Segmente. Mit nur zwei Riegeln (0.25/0.75 H)
    # bleibt fuer den Dreierstapel nach dem Schubfachschluss zwangslaeufig ein
    # Segment ohne Riegel uebrig — das mittlere schwebte zwischen beiden. Es
    # laesst sich auch durch Verschieben der Fugen nicht heilen: drei disjunkte
    # Segmente koennen nicht je einen von zwei Riegeln enthalten. Deshalb ein
    # Riegel je moeglicher Segmentlage. Der dritte auf halber Hoehe traegt das
    # Mittelsegment; bei Zweierstapeln liegt er innerhalb der Segmente und
    # stoert weder Optik noch Fuge. Die HOLZGEOMETRIE bleibt unveraendert —
    # weder Zufallsfolge noch Segmenthoehen aendern sich dadurch.
    rails = (0.25 * y.H, 0.50 * y.H, 0.75 * y.H)
    for r in rails:
        y.seg(0.0, r, y.L, r, 'b')
    for i in range(n):
        segs = min(2 + y.rnd.randrange(2), len(rails))
        t0 = HOLZ_LUFT + y.rnd.random() * y.H * 0.06
        sh = (y.H - t0 - HOLZ_LUFT) / segs
        # Segment k wird dem Riegel sel[k] zugeordnet: erstes Segment auf den
        # untersten, letztes auf den obersten Riegel, der Rest gleichmaessig
        # dazwischen. Bei 2 Segmenten sind das die beiden AEUSSEREN Riegel
        # (0.25/0.75 H) — genau die Zuordnung von vorher.
        sel = [rails[k * (len(rails) - 1) // (segs - 1)] for k in range(segs)]
        # Fugen der gleichmaessigen Segment-Teilung. Trifft die Teilung ihren
        # Riegel (bei allen praxisnahen Feldhoehen der Fall), bleibt sie
        # unangetastet; sonst wandert die Fuge MINIMAL in das zulaessige
        # Fenster — Staggered Panels schiebt den Block, hier wandert die Fuge,
        # damit die
        # gleichmaessige Staffelung erhalten bleibt. HOLZ_LUFT Abstand, weil die
        # Blockkante um die halbe Fugenbreite hinter der Fuge zurueckliegt.
        cut = [t0 + k * sh for k in range(segs + 1)]
        for k in range(1, segs):
            lo, hi = sel[k - 1] + HOLZ_LUFT, sel[k] - HOLZ_LUFT
            cut[k] = min(max(cut[k], lo), hi) if lo < hi else 0.5 * (lo + hi)
        cut[0] = max(0.0, min(cut[0], sel[0] - HOLZ_LUFT))
        cut[segs] = min(y.H, max(cut[segs], sel[segs - 1] + HOLZ_LUFT))
        for k in range(segs):
            y.block(i * st + st * 0.12, cut[k] + HOLZ_LUFT / 2.0,
                    i * st + st * 0.88, cut[k + 1] - HOLZ_LUFT / 2.0,
                    HOLZ_D, 'hz', HOLZ_OFF)


def _ellipse_loop(cs, ct, rs, rt, k=24):
    return [(cs + rs * math.cos(2 * math.pi * i / k),
             ct + rt * math.sin(2 * math.pi * i / k)) for i in range(k)]


def p_sheet_ellipse(y, rap):
    n, st = y.units(rap)
    outer = [(0.0, 0.0), (y.L, 0.0), (y.L, y.H), (0.0, y.H)]
    holes = []
    for i in range(n):
        cs = st * (i + 0.5)
        # Deckel auch fuer den RANDABSTAND: BLECH_RAND galt bisher nur
        # vertikal — zur Feldkante blieben mit dem Default-Rapport nur 28 mm,
        # im schmalen Feld sogar nur BLECH_STEG/2.
        rs = min(st * 0.30, (st - BLECH_STEG) / 2.0, st / 2.0 - BLECH_RAND)
        rt = min(y.H * 0.38, (y.H - 2 * BLECH_RAND) / 2.0)
        if rs > 5.0 and rt > 5.0:
            holes.append(_ellipse_loop(cs, y.H / 2.0, rs, rt))
    y.plate([outer] + holes, BLECH_D, 'st')


def p_rake_random(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        # Stratifiziert statt global gleichverteilt: rein zufaellige Fusspunkte
        # liessen regelmaessig mehrere hundert mm breite Leerzonen entstehen
        # (sichtbar im Muster-Render, Feld 1). Jeder Halm wuerfelt jetzt nur
        # noch INNERHALB seiner Rapportzelle — Zufallscharakter und
        # Seed-Determinismus bleiben, die maximale Luecke ist ~2 Rapporte.
        s0 = (i + y.rnd.random()) * st
        s1 = s0 + (y.rnd.random() - 0.35) * y.L * 0.22
        y.seg(s0, 0.0, max(0.0, min(y.L, s1)), y.H, 'a')


def p_weave_band(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        s0 = i * st
        y.bez((s0, 0.0), (s0 + st, y.H * 0.5), (s0, y.H * 0.5), (s0 + st, y.H), 'a')
        y.bez((s0, y.H), (s0 + st, y.H * 0.5), (s0, y.H * 0.5), (s0 + st, 0.0), 'b')


def p_sheet_grain(y, rap):
    n, st = y.units(rap)
    outer = [(0.0, 0.0), (y.L, 0.0), (y.L, y.H), (0.0, y.H)]
    holes = []
    for i in range(n):
        wl = st * (0.30 + y.rnd.random() * 0.35)
        cs = st * (i + 0.5)
        # Steg- und Randpruefung auf die VOLLE Lochbreite inkl. Bulge
        # (Halbbreite = 0.5*wl + 0.22*wl = 0.72*wl). Vorher wurde nur die
        # nominelle Lochbreite gegen BLECH_STEG geprueft — zwei ausgebauchte
        # Nachbarloecher konnten sich auf ~8 mm Steg naehern, zur Feldkante
        # blieben im Extremfall 4 mm.
        wl = min(wl, (st - BLECH_STEG) / 1.44)
        wl = min(wl, (cs - BLECH_RAND) / 0.72, (y.L - cs - BLECH_RAND) / 0.72)
        if wl < BLECH_STEG:
            continue
        k = 18
        left, right = [], []
        for j in range(k + 1):
            f = j / float(k)
            t = BLECH_RAND + (y.H - 2 * BLECH_RAND) * f
            bulge = math.sin(math.pi * f) * wl * 0.22
            left.append((cs - wl / 2.0 - bulge, t))
            right.append((cs + wl / 2.0 + bulge, t))
        holes.append(left + list(reversed(right)))
    y.plate([outer] + holes, BLECH_D, 'st')


def p_bar_cross_fine(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        y.seg(st * (i + 0.5), 0.0, st * (i + 0.5), y.H, 'a')
    if n == 1:
        # Ein einzelner Stab ohne X widerspraeche der Musterbeschreibung ("Staebe mit
        # Diagonalkreuzungen") — ein Kreuz von Posten zu Posten.
        y.seg(0.0, 0.0, y.L, y.H, 'b', AUSLAGE)
        y.seg(y.L, 0.0, 0.0, y.H, 'b', AUSLAGE)
    for i in range(0, max(n - 1, 0), 2):
        # Bis n-1 statt n-2: mit n-2 blieb bei geradem n am Feldende eine
        # 1,5-Rapport-Zone ohne Diagonalkreuz (Render Feldende: nackte
        # Vertikalstaebe). Erst damit greift die min()-Klemme ueberhaupt —
        # das letzte X wird an den Posten gestaucht statt weggelassen.
        s0 = st * (i + 0.5)
        y.seg(s0, 0.0, min(s0 + 2 * st, y.L), y.H, 'b', AUSLAGE)
        y.seg(min(s0 + 2 * st, y.L), 0.0, s0, y.H, 'b', AUSLAGE)


def p_bar_wave(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        s = st * (i + 0.5)
        amp = st * 0.35
        y.bez((s, 0.0), (s + amp, y.H * 0.33), (s - amp, y.H * 0.66), (s, y.H), 'a')


def p_chevron_h(y, rap):
    rows = 4
    n, st = y.units(rap)
    for r in range(rows):
        base = y.H * (r + 0.5) / rows
        amp = y.H / rows * 0.40
        pts = [(0.0, base - amp)]
        for i in range(n):
            pts.append((i * st + st / 2.0, base + amp))
            pts.append(((i + 1) * st, base - amp))
        # Reihe endet exakt am Posten; oberste/unterste Reihe zusaetzlich an den
        # Gurt angebunden, damit die Fuellung nicht nur an den Posten haengt.
        y.poly(pts, 'a')
        if r == rows - 1:
            # Hochpunkt, nicht Feldmitte: die Spitzen liegen bei i*st + st/2,
            # die Tiefpunkte bei i*st. Auf halber Feldbreite sitzt je nach
            # Einheitenzahl ein Tiefpunkt — der Anbinder haette dort ins Leere
            # gezeigt.
            sp = st * (n // 2) + st / 2.0
            y.seg(sp, base + amp, sp, y.H, 'b')
        if r == 0 and n >= 2:
            # n=1: der einzige innere Tiefpunkt-Index waere 0 — der Anbinder
            # laege exakt in der Postenachse. Die Reihe haengt dann ohnehin
            # an beiden Posten.
            sp = st * (n // 2)
            y.seg(sp, base - amp, sp, 0.0, 'b')


def p_line_density(y, rap):
    n, _ = y.units(rap)
    # (i+0.5)/n statt i/n ueber n+1 Staebe: die Randstaebe lagen exakt AUF den
    # Posten (sin(0) = sin(2pi) = 0, keine Verschiebung) — im Profil versenkt
    # und unsichtbar, aber je Zwischenposten 2*H Rundstahl doppelt in der
    # Stueckliste. Die Dichte-Modulation selbst bleibt unveraendert.
    for i in range(n):
        f = (i + 0.5) / float(max(n, 1))
        s = y.L * (f - 0.045 * math.sin(2 * math.pi * f))
        y.seg(max(0.0, min(y.L, s)), 0.0, max(0.0, min(y.L, s)), y.H, 'a')


def p_bar_width_wave(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        f = i / float(max(n - 1, 1))
        bw = st * (0.25 + 0.60 * (0.5 + 0.5 * math.sin(4 * math.pi * f)))
        cs = st * (i + 0.5)
        y.plate([[(cs - bw / 2.0, 0.0), (cs + bw / 2.0, 0.0),
                  (cs + bw / 2.0, y.H), (cs - bw / 2.0, y.H)]], FLACH_D, 'st')


def p_bar_alternate(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        bw = st * (0.72 if i % 2 == 0 else 0.20)
        cs = st * (i + 0.5)
        y.plate([[(cs - bw / 2.0, 0.0), (cs + bw / 2.0, 0.0),
                  (cs + bw / 2.0, y.H), (cs - bw / 2.0, y.H)]], FLACH_D, 'st')


def p_grid_split(y, rap):
    nx, sx = y.units(rap)
    ny = 2
    sy = y.H / ny
    # Nur die INNEREN Stege: i=0/nx lagen exakt auf den Posten, j=0/ny exakt
    # in Untergurt und Handlauf — der Modulrahmen existiert als Struktur
    # bereits, die deckungsgleichen Staebe waren nur versteckte Stueckliste
    # (2*(L+H) Rundstahl je Feld).
    for i in range(1, nx):
        y.seg(i * sx, 0.0, i * sx, y.H, 'a')
    for j in range(1, ny):
        y.seg(0.0, j * sy, y.L, j * sy, 'a')
    for i in range(nx):
        for j in range(ny):
            s0, t0 = i * sx, j * sy
            if (i + j) % 2 == 0:
                y.seg(s0, t0, s0 + sx, t0 + sy, 'b')
            else:
                y.seg(s0, t0 + sy, s0 + sx, t0, 'b')


def p_rake_cross(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        s0 = st * (i + 0.5)
        s1 = s0 + (y.rnd.random() - 0.5) * st * 3.2
        # Klemmung mit halbem Rapport Randabstand: der harte [0,L]-Clamp
        # stapelte Stabkoepfe exakt in die Ecke Posten/Handlauf (mehrere
        # Staebe koinzident, streckenweise IM Posten).
        lo = min(st * 0.5, y.L / 2.0)
        y.seg(s0, 0.0, max(lo, min(y.L - lo, s1)), y.H, 'a')


def p_bar_scatter(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        y.seg(st * (i + 0.5), 0.0, st * (i + 0.5), y.H, 'a')
    # Schrittweite >= 2, sonst wird aus "eingestreut" bei kleinen n eine
    # lueckenlose Diagonalschar; und mindestens EINE Diagonale, sonst
    # degeneriert das Muster im schmalen Feld zu Vertical Bars.
    step = max(2, n // 3)
    picks = list(range(1, n - 1, step))
    if not picks and n >= 2:
        picks = [n // 2]
    for i in picks:
        s0 = st * (i + 0.5)
        y.seg(s0, 0.0, min(s0 + st, y.L), y.H, 'b', AUSLAGE)


def p_wave_overlay(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        y.seg(st * (i + 0.5), 0.0, st * (i + 0.5), y.H, 'a')
    for f in (0.30, 0.70):
        t = y.H * f
        amp = y.H * 0.12
        half = y.L / 2.0
        y.bez((0.0, t), (half * 0.5, t + amp * 2), (half * 0.5, t - amp * 2),
              (half, t), 'b', AUSLAGE)
        y.bez((half, t), (half * 1.5, t + amp * 2), (half * 1.5, t - amp * 2),
              (y.L, t), 'b', AUSLAGE)


def p_bar_graded(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        s = st * (i + 0.5)
        y.seg(s, 0.0, s, y.H, 'b' if i % 3 == 0 else 'a')


def p_frame_u(y, rap):
    n, st = y.units(rap)
    # Querstueck AUF dem Untergurt, nicht IN ihm: bei t=0 verlief seine
    # Mittellinie exakt in der Untergurt-Mittellinie und verschwand komplett
    # im Gurtprofil — im Render blieben scheinbar nackte Stabpaare uebrig,
    # das U war unsichtbar. 2*STABB Aufstand (Default 24 mm) raeumt die halbe
    # Hoehe des Standard-Untergurts (Flachstahl 40x10 hochkant: 20 mm) frei;
    # die leichte Restueberdeckung liest sich als Schweissanschluss.
    t0 = STABB * 2.0
    for i in range(n):
        s0 = i * st + st * 0.18
        s1 = (i + 1) * st - st * 0.18
        y.poly([(s0, y.H), (s0, t0), (s1, t0), (s1, y.H)], 'a')


def p_bar_railed(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        y.seg(st * (i + 0.5), 0.0, st * (i + 0.5), y.H, 'a')
    for f in (0.32, 0.68):
        y.seg(0.0, y.H * f, y.L, y.H * f, 'b')


def p_flat_horizontal(y, rap):
    n = max(int(round(y.H / max(rap, 1.0))), 2)
    for i in range(n):
        t = y.H * (i + 0.5) / n
        y.seg(0.0, t, y.L, t, 'a')
    y.seg(y.L / 2.0, 0.0, y.L / 2.0, y.H, 'b')


def p_hatch_45(y, rap):
    _, st = y.units(rap)
    k = -y.H
    while k < y.L:
        s0 = max(k, 0.0)
        s1 = min(k + y.H, y.L)
        # Fertigungs-Mindestlaenge statt TOL: je nach L mod st blieb in der
        # Ecke am Posten ein Millimeter-Stummel uebrig, der gebaut, gesweept
        # und in der Stueckliste gezaehlt wurde.
        if (s1 - s0) * math.sqrt(2.0) > 30.0:
            y.seg(s0, s0 - k, s1, s1 - k, 'a')
        k += st


def p_bar_vertical(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        y.seg(st * (i + 0.5), 0.0, st * (i + 0.5), y.H, 'a')


def p_bar_twist(y, rap):
    n, st = y.units(rap)
    for i in range(n):
        y.twisted(st * (i + 0.5), 0.0, y.H, VIERKANT_W, half_turns=1.0)


def p_rake_uniform(y, rap):
    n, st = y.units(rap)
    lean = st * 0.8
    for i in range(n + 1):
        s0 = i * st
        bs, ts = s0 - lean / 2.0, s0 + lean / 2.0
        bc, tc = max(bs, 0.0), min(ts, y.L)
        if tc <= bc:
            continue
        y.seg(bc, y.H * (bc - bs) / lean, tc, y.H * (tc - bs) / lean, 'a')


def p_vee_center(y, rap):
    n, st = y.units(rap)
    dx = st * 0.45
    for i in range(n):
        s = st * (i + 0.5)
        y.poly([(s, y.H), (min(s + dx, y.L), y.H / 2.0), (s, 0.0)], 'a')


BUILDERS = {
    'loop-u': p_loop_u, 'panel-stagger': p_panel_stagger,
    'ray-diamond': p_ray_diamond, 'bar-bead': p_bar_bead,
    'vee-pair': p_vee_pair, 'panel-slat': p_panel_slat,
    'arch-stack': p_arch_stack, 'hook-j': p_hook_j,
    'lattice-diamond': p_lattice_diamond, 'loop-drop': p_loop_drop,
    'panel-segment': p_panel_segment, 'sheet-ellipse': p_sheet_ellipse,
    'rake-random': p_rake_random, 'weave-band': p_weave_band,
    'sheet-grain': p_sheet_grain, 'bar-cross-fine': p_bar_cross_fine,
    'bar-wave': p_bar_wave, 'chevron-h': p_chevron_h,
    'line-density': p_line_density, 'bar-width-wave': p_bar_width_wave,
    'bar-alternate': p_bar_alternate, 'grid-split': p_grid_split,
    'rake-cross': p_rake_cross, 'bar-scatter': p_bar_scatter,
    'wave-overlay': p_wave_overlay, 'bar-graded': p_bar_graded,
    'frame-u': p_frame_u, 'bar-railed': p_bar_railed,
    'flat-horizontal': p_flat_horizontal, 'hatch-45': p_hatch_45,
    'bar-vertical': p_bar_vertical, 'bar-twist': p_bar_twist,
    'rake-uniform': p_rake_uniform, 'vee-center': p_vee_center,
}


# ------------------------------------------------------------------- Ablauf
def _num(v, fallback):
    """Zahl vom Eingang — 0 ist ein gueltiger Wert.

    Vorher stand hier `return f if f > 0 else fallback`, was JEDE Null als
    "nicht angeschlossen" gelesen hat: Muster 0 (U-Loop) war damit
    unerreichbar, der Regler stand auf 0 und die Engine baute stumm Muster 30.
    Nichts hat gewarnt — der Regler zeigte 0, die Geometrie war gueltig, nur
    eben die falsche.
    """
    v = getattr(v, 'Value', v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return fallback


def _pos(v, fallback):
    """Wie _num, aber fuer Masse, die zwingend > 0 sein muessen (Dicken,
    Breiten, Rapport-Faktoren). Hier IST 0 sinnlos und wird zum Default."""
    f = _num(v, fallback)
    return f if f > 0 else fallback


def _crv(o):
    """Eingang zu rg.Curve zwingen.

    Der Typ eines Script-Eingangs laesst sich ueber MCP nicht zuverlaessig
    setzen — kommt der Port als "Generic Data" an, liegen hier GH_Curve-Wrapper
    oder rg.Line-Structs statt fertiger Kurven. Stillschweigend leere Listen
    zurueckzugeben waere genau die Klasse von Fehlern, die dieses Modell schon
    zweimal gruen durchlaufen hat, also wird hier hart geprueft.
    """
    o = getattr(o, 'Value', o)
    if isinstance(o, rg.Curve):
        return o
    if isinstance(o, rg.Line):
        return rg.LineCurve(o)
    to_nurbs = getattr(o, 'ToNurbsCurve', None)
    if to_nurbs:
        return to_nurbs()
    raise TypeError('Eingang ist keine Kurve: %r' % (type(o),))


def _vec(o, fallback):
    o = getattr(o, 'Value', o)
    if isinstance(o, rg.Vector3d):
        return o
    if isinstance(o, rg.Point3d):
        return rg.Vector3d(o)
    return fallback


idx = int(_num(M, 30))                      # Default: Vertical Bars (Referenzfall)
idx = max(0, min(len(DESIGNS) - 1, idx))
D = DESIGNS[idx]

HOLZ_D = _pos(Hd, 30.0)                     # Holzdicke mm
HOLZ_LUFT = _num(Hl, 8.0)                   # Luftspalt/Bodenabstand Holz mm
BLECH_D = _pos(Bd, 4.0)                     # Blechdicke mm
BLECH_STEG = _pos(Bs, 25.0)                 # min. Steg zwischen Aussparungen mm
BLECH_RAND = _pos(Br, 30.0)                 # min. Randabstand Aussparung mm
HOLZ_OFF = _pos(Ho, 12.0)                   # Auslage Holz vor den Stahlriegel mm
FLACH_D = _pos(Fd, 8.0)                     # Dicke Flachstahl mit wechselnder Breite
VIERKANT_W = _pos(Vw, 16.0)                 # Kantenmass tordierter Vierkantstab
AUSLAGE = _num(A, 0.0)                      # Vorsprung vorgesetzter Elemente mm
GMAX = _pos(Gmax, 120.0)                    # groesste zulaessige lichte Weite mm
STABB = _pos(Bw, 12.0)                      # Stabbreite des Fuellprofils mm
UGURT = _num(Ug, 100.0)                     # Untergurt ueber Nosinglinie mm
KWINK = _pos(Kw, 60.0)                      # Grenzwinkel "begehbar" in Grad

dichte = _pos(Dc, 1.0)
rap = D['rap'] * dichte
clamped = False
if D['gap']:
    # Abgeleitete Deckelung statt Slider-Grenze: der Rapport darf nie so gross
    # werden, dass die LICHTE Weite Gmax ueberschreitet. Gleiche Logik wie der
    # bestehende Diagonal-Deckel — die Grenze haengt am Muster, nicht am Regler,
    # damit ein weit aufgezogener Regler kein unzulaessiges Feld ausliefern kann.
    # gapf: Muster, deren groesste Oeffnung um einen bekannten Faktor UEBER dem
    # Rapport liegt (Density Lines: Modulation +28 %), verschaerfen den Deckel
    # entsprechend — sonst garantiert er die 4.2.4-Konformitaet gerade nicht.
    cap = (GMAX + STABB) * D.get('gapf', 1.0)
    if rap > cap:
        rap = cap
        clamped = True

seed0 = int(_num(S, 1))
lo_list = [_crv(c) for c in (Lo or [])]
hi_list = [_crv(c) for c in (Hi or [])]
nrm = _vec(N, rg.Vector3d(0, 1, 0))
if len(lo_list) != len(hi_list):
    raise ValueError('Lo/Hi ungleich lang (%d/%d) — Untergurt und Handlauf muessen '
                     'an denselben Postenparametern geschattert sein'
                     % (len(lo_list), len(hi_list)))

a, b, st, hz, bays = [], [], [], [], []
build = BUILDERS[D['key']]
for i, lo in enumerate(lo_list):
    y = Bay(lo, hi_list[i], nrm, seed0 + idx * 977 + i * 131)
    build(y, rap)
    bays.append(y)
    a += y.a
    b += y.b
    st += y.st
    hz += y.hz

Stab1 = a
Stab2 = b
Stahl = st
Holz = hz

# --------------------------------------------------------- Anschlusspruefung
# K1 aus den Rework-Instructions: kein Stabende darf frei in der Luft enden.
# Zulaessig ist ein Ende auf dem Untergurt (t=0), am Handlauf (t=H), an einem
# Posten (s=0 oder s=L) oder auf einem anderen Stab desselben Feldes (z. B. dem
# Zwischenriegel, den das Muster selbst mit ausgibt).
#
# Diese Pruefung existiert, weil "0 Komponentenfehler" hier nichts beweist: ein
# frei haengender Stab ist eine voellig gueltige Kurve und wird anstandslos
# gesweept. Geprueft werden Staebe; Holz- und Blech-Solids haengen konstruktiv
# an ihren Riegeln bzw. an der Einfassung und liegen absichtlich davor.
ATOL = 1.5   # mm — deckt Rundung aus Bogen-/Bezier-Diskretisierung ab


def _free_ends(bay):
    crvs = bay.a + bay.b
    bad = 0
    for i, c in enumerate(crvs):
        for p in (c.PointAtStart, c.PointAtEnd):
            s, t = bay.st_of(p)
            if (abs(t) <= ATOL or abs(t - bay.H) <= ATOL
                    or abs(s) <= ATOL or abs(s - bay.L) <= ATOL):
                continue
            hit = False
            for j, o in enumerate(crvs):
                if j == i:
                    continue
                ok, u = o.ClosestPoint(p, ATOL)
                if ok and o.PointAt(u).DistanceTo(p) <= ATOL:
                    hit = True
                    break
            if not hit:
                bad += 1
    return bad


free = sum(_free_ends(y) for y in bays)

# ------------------------------------------------- Kletterhilfe, OIB-RL 4 4.2.3
# Zwischen 150 und 600 mm ueber der Stufenvorderkante darf kein horizontales
# oder schraeges Element liegen. t wird ab dem UNTERGURT gemessen, die Zone ab
# der Nosinglinie — der Untergurt liegt UGURT darueber, also verschiebt sich das
# Fenster um genau diesen Betrag nach unten.
#
# Der Winkel wird gegen die ECHTE Waagrechte gemessen, nicht gegen die Steigung:
# ein Stab, der parallel zum Treppenlauf liegt, ist mit ~30 deg eine Rampe und
# damit sehr wohl besteigbar. Die Richtlinie nennt keinen Grenzwinkel — Kw ist
# deshalb ein Regler und keine eingebaute Wahrheit.
ZONE_LO = 150.0 - UGURT
ZONE_HI = 600.0 - UGURT
SAMPLES = 24


def _climb(bay):
    flat = 0
    for c in bay.a + bay.b:
        dom = c.Domain
        for i in range(SAMPLES + 1):
            u = dom.ParameterAt(i / float(SAMPLES))
            p = c.PointAt(u)
            _, t = bay.st_of(p)
            if not (ZONE_LO <= t <= ZONE_HI):
                continue
            tan = c.TangentAt(u)
            if tan.Length < 1e-9:
                continue
            ang = math.degrees(math.asin(min(1.0, abs(tan.Z) / tan.Length)))
            if ang < KWINK:
                flat += 1
                break          # ein Treffer je Stab genuegt
    return flat


climb = sum(_climb(y) for y in bays)
zone_txt = ('Zone 150-600 mm liegt bei t = %.0f..%.0f mm ueber Untergurt'
            % (max(ZONE_LO, 0.0), ZONE_HI))
if ZONE_HI <= 0:
    zone_txt = 'Zone 150-600 mm liegt vollstaendig UNTER dem Untergurt — 4.2.3 hier gegenstandslos'

Norm = [
    'OIB-RL 4 (Mai 2023) — geometrische Vorpruefung, kein Nachweis',
    'Pkt. 4.2.4  Oeffnung <= %.0f mm in mindestens einer Richtung (Rapport gedeckelt: %s)'
    % (GMAX, 'ja' if clamped else 'nicht noetig'),
    'Pkt. 4.2.3  %s' % zone_txt,
    'Pkt. 4.2.3  %d Staebe verlaufen dort flacher als %.0f deg%s'
    % (climb, KWINK,
       '  -> Ausnahme nur ueber Vorsprung <= 30 mm, Oeffnung vertikal <= 20 mm'
       ' oder Lochblech Loch <= 40 mm' if climb else '  -> unkritisch'),
    'Bewertung des Musters: ' + D['norm'],
    'Nicht geprueft: Holmlast (OENORM B 1991-1-1, Kat. A = 0,5 kN/m), Wind,',
    'Gelaenderhoehe (4.2.1: 1,00 m; Wohnungstreppe 0,90 m) und die Statik der',
    'Riegel/Bleche. Die Engine prueft Geometrie, nicht Tragfaehigkeit.',
]

Check = ['Muster %02d %s' % (idx, D['name']),
         'freie Stabenden: %d  (Sollwert 0 — K1)' % free,
         'flach in Zone A: %d Staebe (OIB 4.2.3, Grenze %.0f deg)' % (climb, KWINK),
         'Staebe %d/%d, Stahl-Solids %d, Holz-Solids %d'
         % (len(a), len(b), len(st), len(hz))]

Info = [
    'Muster %02d  %s  (%s)' % (idx, D['name'], D['fam']),
    'Rapport: %.0f mm%s  (Basis %.0f x Faktor %.2f)' % (
        rap, '  [auf Oeffnung-max %.0f gedeckelt]' % GMAX if clamped else '',
        D['rap'], dichte),
    'Anschluss oben:  ' + D['oben'],
    'Anschluss unten: ' + D['unten'],
    'Verbindungen:    ' + D['verb'],
    'Sondermaterial:  ' + (D['sonder'] or 'keines — nur Stahl'),
    'Zufall:          ' + (D['zufall'] or 'keiner — vollstaendig deterministisch'),
    'Teile: %d Staebe (Fuellprofil) / %d Staebe (2. Profil) / %d Stahl-Solids / %d Holz-Solids'
    % (len(a), len(b), len(st), len(hz)),
    'Gebogene Bauteile sind in knickfreie Stuecke zerlegt (Sweep-Anforderung),',
    'die Stueckzahl oben ist daher Schienen, nicht Schlosserteile.',
]
