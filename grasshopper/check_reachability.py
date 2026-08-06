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
"""Erreichbarkeitspruefung der 34 Muster — OFFLINE, ohne Rhino/Grasshopper.

WOZU
    Die Phase-14-Regression (grasshopper/regress_p14.py) prueft "0 Komponenten-
    fehler", "Solids == Mittellinien" und `_free_ends` aus der Engine. `_free_ends`
    ist aber eine reine ENDPUNKT-Nachbarschaft: jedes Stabende muss irgendetwas
    beruehren. Eine Insel aus zwei Staeben, die sich gegenseitig halten und sonst
    nichts, besteht diese Pruefung anstandslos — sie faellt trotzdem aus dem Feld.
    Dieses Skript schliesst genau diese Luecke: es baut den Beruehrungsgraphen
    ALLER Bauteile eines Feldes und verlangt, dass jede Zusammenhangskomponente
    den Rahmen erreicht.

WIE OHNE RHINO
    Quelle der Wahrheit bleibt patterns.py — die Musterdefinitionen
    werden NICHT kopiert, sondern das Original wird hier ausgefuehrt. Rhino.Geometry
    wird dazu durch einen kleinen Stub ersetzt (Vektoren, Linien, Kreisboegen durch
    3 Punkte, kubische Beziers, Polylinien, sowie Platten-/Loft-Attrappen, die ihre
    Konturen mitfuehren). Der Stub rechnet echte Geometrie, nur eben in reinem
    Python: Boegen und Beziers werden mit 32 Sehnen diskretisiert (Stichhoehe bei
    den hier vorkommenden Radien < 0.02 mm, also weit unter der Toleranz).
    Es wird nichts an Rhino, Grasshopper oder MCP geschickt.

ANKERMODELL (aus der Engine abgeleitet, nicht geraten)
    patterns.py (Abschnitt "Anschlusspruefung") und die Kopfdoku (K1/K2/K3)
    nennen die
    zulaessigen Anschluesse woertlich. Ein Bauteil gilt hier als DIREKT verankert,
    wenn irgendein Punkt seiner Kontur im Feldparameterraum (s, t) liegt auf
        t = 0          Untergurt          (A_UNTEN)
        t = H          Handlauf           (A_OBEN)
        s = 0 / s = L  Posten links/rechts(A_POSTEN)
    jeweils mit ATOL = 1.5 mm, derselben Toleranz, die auch die Engine benutzt.
    Geprueft wird nicht nur der Endpunkt, sondern die ganze abgetastete Kontur:
    der Serpentinen-Bogen etwa LIEGT mit seinem Scheitel auf dem Untergurt auf
    (Katalogtext: "U-Bogen liegt auf dem Untergurt auf") und ist damit unten
    angeschlossen, obwohl seine beiden Enden bei t = r hoeher liegen.

    Ein Bauteil ist INDIREKT verankert, wenn es ueber eine Kette von Beruehrungen
    ein direkt verankertes Bauteil erreicht. Zwei Bauteile beruehren sich, wenn
    ihre Konturen im (s, t)-Raum bis auf JTOL = 1.5 mm zusammenkommen oder eines
    im Umriss des anderen liegt.

    Bewusst in der PROJEKTION (s, t) gerechnet, nicht im Raum: vorgesetzte
    Elemente (Auslage A, Holz vor dem Riegel) liegen um Nh*off vor der Feldebene
    und wuerden im Raum nie beruehren — der Katalog sagt aber genau fuer diese
    Faelle "an den Kreuzungen geheftet" bzw. "Holz auf Riegel verschraubt". Die
    Projektion bildet also die tatsaechliche Verschraubung ab. Umgekehrt heisst
    das: eine Beruehrung in der Projektion IST hier eine Verbindung, auch dort,
    wo die Musterbeschreibung "Kreuzungen nicht verbunden" schreibt
    (Random Rake, Crossed Rakes).
    Damit die Wertung davon nicht abhaengt, weist die Tabelle die Zahl der DIREKT
    verankerten Teile getrennt aus: wo direkt == gesamt, traegt der Graph nichts
    zum Ergebnis bei und die Toleranz gegenueber Kreuzungen ist wirkungslos.

BLECHE (Muster 11 Ellipse Sheet, 14 Grain Sheet, 19 Width Wave,
        20 Alternating Bars)
    Ein Blech ist keine Stabkette, sondern eine Flaeche mit Aussparungen. Statt
    zu rastern wird analytisch geprueft:
      1. jede Aussparung ist eine einfache, nicht selbstschneidende Kontur,
      2. die Aussparungen sind paarweise disjunkt (Mindeststeg > 0),
      3. jede Aussparung liegt ECHT innerhalb der Aussenkontur (Randabstand > 0).
    Sind 1-3 erfuellt, ist das Restmaterial topologisch zusammenhaengend (eine
    einfach zusammenhaengende Flaeche minus disjunkter innerer Scheiben bleibt
    zusammenhaengend) — dann kann kein Blechstueck herausfallen. Schlaegt eine
    der Bedingungen fehl, wird als Rueckfallebene gerastert und die Material-
    komponenten werden gezaehlt.

AUSGABE
    Tabelle je Referenzfeld. Ein Muster ist
        PASS   jede Zusammenhangskomponente erreicht den Rahmen,
        OFFEN  es haengt etwas, ABER das Muster steht in KNOWN_OPEN — die
               Konstruktionsfrage dahinter ist bewusst offen und darf nach
               Rework-Instructions Abschnitt 6 nicht von Agenten beantwortet
               werden (siehe unten),
        FAIL   es haengt etwas, und das ist ein Fehler.

BEKANNTE OFFENE PUNKTE (KNOWN_OPEN)
    Damit dieses Skript als REGRESSIONSGATE taugt, muss es zwischen "neu kaputt"
    und "seit jeher offen" unterscheiden. KNOWN_OPEN listet Muster, deren
    schwebende Teile auf eine offene Nutzer-/Werkstatt-Entscheidung
    zurueckgehen. Sie werden als OFFEN ausgewiesen, gezaehlt und begruendet,
    zaehlen aber NICHT als Fehlschlag: der Standardlauf endet mit 0, solange
    sonst nichts haengt. Wer eine Zeile hier eintraegt, kauft sich damit KEINE
    Ruhe — der Text muss sagen, wessen Entscheidung fehlt.
    Faellt ein KNOWN_OPEN-Muster nicht mehr durch, meldet der Lauf den Eintrag
    als veraltet (HINWEIS); dann gehoert er geloescht.

    --strict schaltet die Nachsicht ab: dann ist OFFEN wieder FAIL und der
    Rueckgabewert 1 — das Verhalten von vor der Einfuehrung dieser Tabelle,
    fuer den Tag, an dem die offenen Fragen beantwortet sind.

Aufruf:  python grasshopper/check_reachability.py            Gate: 0, solange nur
                                                         KNOWN_OPEN haengt
         python grasshopper/check_reachability.py --strict   jede Schwebung ist ein
                                                         Fehler
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "patterns.py")

ATOL = 1.5     # mm, Ankertoleranz — wie in patterns.py
JTOL = 1.5     # mm, Beruehrungstoleranz zwischen zwei Bauteilen
NSEG = 32      # Sehnen je Bogen/Bezier

# Musterindex -> Grund. Siehe Kopfdoku, Abschnitt BEKANNTE OFFENE PUNKTE.
# Eintragen darf hier nur, wessen Schwebung an einer offenen ENTSCHEIDUNG haengt
# (Research/Musterkatalog_Rework_Instructions.md Abschnitt 6 bzw.
# docs/patterns-and-code.md, "Open fabrication decisions") — nicht,
# wer einen Fehler nicht gefunden hat.
KNOWN_OPEN = {
    8: 'Diamond Lattice Holz-Scheiben: Befestigung ungeklaert, '
       'Nutzer-Entscheidung offen',
}


# ======================================================= Rhino.Geometry-Stub
class V3(object):
    __slots__ = ('X', 'Y', 'Z')

    def __init__(self, x=0.0, y=0.0, z=0.0):
        if hasattr(x, 'X'):
            x, y, z = x.X, x.Y, x.Z
        self.X, self.Y, self.Z = float(x), float(y), float(z)

    @property
    def Length(self):
        return math.sqrt(self.X ** 2 + self.Y ** 2 + self.Z ** 2)

    def Unitize(self):
        n = self.Length
        if n < 1e-15:
            return False
        self.X, self.Y, self.Z = self.X / n, self.Y / n, self.Z / n
        return True

    def __mul__(self, o):
        if isinstance(o, (V3, P3)):
            return self.X * o.X + self.Y * o.Y + self.Z * o.Z
        return V3(self.X * o, self.Y * o, self.Z * o)

    __rmul__ = __mul__

    def __add__(self, o):
        return V3(self.X + o.X, self.Y + o.Y, self.Z + o.Z)

    def __sub__(self, o):
        return V3(self.X - o.X, self.Y - o.Y, self.Z - o.Z)

    def __neg__(self):
        return V3(-self.X, -self.Y, -self.Z)

    def __repr__(self):
        return 'V3(%g,%g,%g)' % (self.X, self.Y, self.Z)


class P3(object):
    __slots__ = ('X', 'Y', 'Z')
    Unset = None      # unten gesetzt

    def __init__(self, x=0.0, y=0.0, z=0.0):
        if hasattr(x, 'X'):
            x, y, z = x.X, x.Y, x.Z
        self.X, self.Y, self.Z = float(x), float(y), float(z)

    def DistanceTo(self, o):
        return math.sqrt((self.X - o.X) ** 2 + (self.Y - o.Y) ** 2 + (self.Z - o.Z) ** 2)

    def __add__(self, o):
        return P3(self.X + o.X, self.Y + o.Y, self.Z + o.Z)

    def __sub__(self, o):
        if isinstance(o, V3):
            return P3(self.X - o.X, self.Y - o.Y, self.Z - o.Z)
        return V3(self.X - o.X, self.Y - o.Y, self.Z - o.Z)

    def __mul__(self, o):
        if isinstance(o, (V3, P3)):
            return self.X * o.X + self.Y * o.Y + self.Z * o.Z
        return P3(self.X * o, self.Y * o, self.Z * o)

    def __repr__(self):
        return 'P3(%g,%g,%g)' % (self.X, self.Y, self.Z)


P3.Unset = P3(0.0, 0.0, 0.0)


def _cross(a, b):
    return V3(a.Y * b.Z - a.Z * b.Y, a.Z * b.X - a.X * b.Z, a.X * b.Y - a.Y * b.X)


class Interval(object):
    def __init__(self, t0=0.0, t1=1.0):
        self.T0, self.T1 = t0, t1

    def ParameterAt(self, f):
        return self.T0 + (self.T1 - self.T0) * f


class Curve(object):
    """Kurve = ihre Abtastung. Reicht fuer Laenge, Endpunkte, Naehe, Tangente."""

    def __init__(self, pts):
        self.pts = [P3(p) for p in pts]

    # -- Rhino-API ---------------------------------------------------------
    @property
    def PointAtStart(self):
        return self.pts[0]

    @property
    def PointAtEnd(self):
        return self.pts[-1]

    @property
    def Domain(self):
        return Interval(0.0, 1.0)

    def GetLength(self):
        return sum(self.pts[i].DistanceTo(self.pts[i + 1])
                   for i in range(len(self.pts) - 1))

    def _cum(self):
        c, acc = [0.0], 0.0
        for i in range(len(self.pts) - 1):
            acc += self.pts[i].DistanceTo(self.pts[i + 1])
            c.append(acc)
        return c, acc

    def PointAt(self, u):
        c, tot = self._cum()
        if tot <= 0:
            return self.pts[0]
        d = max(0.0, min(1.0, u)) * tot
        for i in range(len(c) - 1):
            if c[i] <= d <= c[i + 1]:
                seg = c[i + 1] - c[i]
                f = 0.0 if seg <= 0 else (d - c[i]) / seg
                a, b = self.pts[i], self.pts[i + 1]
                return P3(a.X + (b.X - a.X) * f, a.Y + (b.Y - a.Y) * f,
                          a.Z + (b.Z - a.Z) * f)
        return self.pts[-1]

    def TangentAt(self, u):
        c, tot = self._cum()
        if tot <= 0:
            return V3(0, 0, 0)
        d = max(0.0, min(1.0, u)) * tot
        for i in range(len(c) - 1):
            if c[i] <= d <= c[i + 1] and c[i + 1] > c[i]:
                v = self.pts[i + 1] - self.pts[i]
                v = V3(v.X, v.Y, v.Z)
                v.Unitize()
                return v
        v = self.pts[-1] - self.pts[-2]
        v = V3(v.X, v.Y, v.Z)
        v.Unitize()
        return v

    def ClosestPoint(self, p, tol=None):
        """(bool, u) wie Rhino: u normiert auf [0,1], Treffer nur innerhalb tol."""
        best, bu = 1e30, 0.0
        c, tot = self._cum()
        for i in range(len(self.pts) - 1):
            a, b = self.pts[i], self.pts[i + 1]
            vx, vy, vz = b.X - a.X, b.Y - a.Y, b.Z - a.Z
            ll = vx * vx + vy * vy + vz * vz
            if ll <= 0:
                f = 0.0
            else:
                f = ((p.X - a.X) * vx + (p.Y - a.Y) * vy + (p.Z - a.Z) * vz) / ll
                f = max(0.0, min(1.0, f))
            q = P3(a.X + vx * f, a.Y + vy * f, a.Z + vz * f)
            d = q.DistanceTo(p)
            if d < best:
                best = d
                bu = 0.0 if tot <= 0 else (c[i] + f * (c[i + 1] - c[i])) / tot
        if tol is not None and best > tol:
            return False, bu
        return True, bu


class Line(object):
    def __init__(self, a, b):
        self.From, self.To = P3(a), P3(b)


class LineCurve(Curve):
    def __init__(self, a, b=None):
        if b is None and isinstance(a, Line):
            a, b = a.From, a.To
        Curve.__init__(self, [a, b])


class Arc(object):
    """Kreisbogen durch 3 Punkte — mit echtem Umkreismittelpunkt."""

    def __init__(self, p0, pm, p1):
        self.p0, self.pm, self.p1 = P3(p0), P3(pm), P3(p1)
        a = self.p0 - self.p1
        b = self.pm - self.p1
        a = V3(a.X, a.Y, a.Z)
        b = V3(b.X, b.Y, b.Z)
        n = _cross(a, b)
        self.IsValid = n.Length > 1e-9 and a.Length > 1e-9 and b.Length > 1e-9
        self._pts = None
        if not self.IsValid:
            return
        num = _cross(b * (a.Length ** 2) - a * (b.Length ** 2), n)
        cen = self.p1 + num * (1.0 / (2.0 * n.Length ** 2))
        r = cen.DistanceTo(self.p0)
        u = V3(self.p0 - cen)
        u.Unitize()
        nn = V3(n.X, n.Y, n.Z)
        nn.Unitize()
        v = _cross(nn, u)

        def ang(p):
            d = V3(p - cen)
            return math.atan2(d * v, d * u) % (2.0 * math.pi)

        am, a1 = ang(self.pm), ang(self.p1)
        sweep = a1 if am < a1 else a1 - 2.0 * math.pi
        self._pts = []
        for i in range(NSEG + 1):
            th = sweep * i / float(NSEG)
            self._pts.append(cen + u * (r * math.cos(th)) + v * (r * math.sin(th)))


class ArcCurve(Curve):
    def __init__(self, arc):
        Curve.__init__(self, arc._pts if arc._pts else [arc.p0, arc.p1])


class BezierCurve(object):
    def __init__(self, pts):
        self.cp = [P3(p) for p in pts]

    def ToNurbsCurve(self):
        out = []
        for i in range(NSEG + 1):
            u = i / float(NSEG)
            w = 1.0 - u
            c = self.cp
            out.append(P3(
                w ** 3 * c[0].X + 3 * w * w * u * c[1].X + 3 * w * u * u * c[2].X + u ** 3 * c[3].X,
                w ** 3 * c[0].Y + 3 * w * w * u * c[1].Y + 3 * w * u * u * c[2].Y + u ** 3 * c[3].Y,
                w ** 3 * c[0].Z + 3 * w * w * u * c[1].Z + 3 * w * u * u * c[2].Z + u ** 3 * c[3].Z))
        return Curve(out)


class Polyline(list):
    def __init__(self, pts=()):
        list.__init__(self, [P3(p) for p in pts])

    @property
    def IsClosed(self):
        return len(self) > 2 and self[0].DistanceTo(self[-1]) < 1e-9

    def Add(self, p):
        self.append(P3(p))


class PolylineCurve(Curve):
    def __init__(self, pl):
        Curve.__init__(self, list(pl))


class _Face(object):
    def __init__(self, brep):
        self.brep = brep

    def CreateExtrusion(self, path, cap):
        thick = P3(path.PointAtEnd).DistanceTo(P3(path.PointAtStart))
        return _Solid('plate', self.brep.loops, thick)


class _Solid(object):
    def __init__(self, kind, loops, thick):
        self.kind, self.loops, self.thick = kind, loops, thick

    def CapPlanarHoles(self, tol):
        return self


class _PlanarBrep(object):
    def __init__(self, loops):
        self.loops = loops
        self.Faces = [_Face(self)]


class LoftType(object):
    Straight = 0


class Brep(object):
    @staticmethod
    def CreatePlanarBreps(crvs, tol):
        if not crvs:
            return []
        return [_PlanarBrep([list(c.pts) for c in crvs])]

    @staticmethod
    def CreateFromLoft(secs, p0, p1, ltype, closed):
        return [_Solid('twisted', [list(c.pts) for c in secs], 0.0)]


def _install_stub():
    import types
    geom = types.ModuleType('Rhino.Geometry')
    for nm, obj in (('Vector3d', V3), ('Point3d', P3), ('Curve', Curve),
                    ('Line', Line), ('LineCurve', LineCurve), ('Arc', Arc),
                    ('ArcCurve', ArcCurve), ('BezierCurve', BezierCurve),
                    ('Polyline', Polyline), ('PolylineCurve', PolylineCurve),
                    ('Brep', Brep), ('LoftType', LoftType), ('Interval', Interval)):
        setattr(geom, nm, obj)
    rhino = types.ModuleType('Rhino')
    rhino.Geometry = geom
    sys.modules['Rhino'] = rhino
    sys.modules['Rhino.Geometry'] = geom


_install_stub()
with open(SRC, encoding='utf-8') as fh:
    SRC_CODE = compile(fh.read(), SRC, 'exec')


def run_engine(idx, lo, hi, seed=1):
    """patterns.py im Original ausfuehren — keine Kopie der Muster."""
    ns = {'__name__': 'patterns', '__file__': SRC,
          'M': idx, 'Lo': [lo], 'Hi': [hi], 'N': None, 'S': seed, 'Dc': None,
          'Hd': None, 'Hl': None, 'Bd': None, 'Bs': None, 'Br': None,
          'Ho': None, 'Fd': None, 'Vw': None, 'A': None, 'Gmax': None,
          'Bw': None, 'Ug': None, 'Kw': None}
    exec(SRC_CODE, ns)
    return ns


# ============================================================ 2D-Hilfsmittel
def _seg_dist(p, q, r, s):
    """Abstand zweier Strecken in der Ebene."""
    def pt_seg(p, a, b):
        vx, vy = b[0] - a[0], b[1] - a[1]
        ll = vx * vx + vy * vy
        if ll <= 0:
            return math.hypot(p[0] - a[0], p[1] - a[1])
        f = max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / ll))
        return math.hypot(p[0] - (a[0] + vx * f), p[1] - (a[1] + vy * f))

    d1 = (q[0] - p[0], q[1] - p[1])
    d2 = (s[0] - r[0], s[1] - r[1])
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) > 1e-12:
        t = ((r[0] - p[0]) * d2[1] - (r[1] - p[1]) * d2[0]) / den
        u = ((r[0] - p[0]) * d1[1] - (r[1] - p[1]) * d1[0]) / den
        if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
            return 0.0
    return min(pt_seg(p, r, s), pt_seg(q, r, s), pt_seg(r, p, q), pt_seg(s, p, q))


def _bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _bbox_far(b1, b2, tol):
    return (b1[0] - b2[2] > tol or b2[0] - b1[2] > tol
            or b1[1] - b2[3] > tol or b2[1] - b1[3] > tol)


def _path_dist(a, b, cutoff):
    """Kleinster Abstand zweier Polygonzuege, mit Kastenvorfilter."""
    if _bbox_far(_bbox(a), _bbox(b), cutoff):
        return 1e30
    best = 1e30
    for i in range(len(a) - 1):
        sb = _bbox([a[i], a[i + 1]])
        for j in range(len(b) - 1):
            if _bbox_far(sb, _bbox([b[j], b[j + 1]]), best if best < 1e29 else cutoff):
                continue
            d = _seg_dist(a[i], a[i + 1], b[j], b[j + 1])
            if d < best:
                best = d
                if best <= 0.0:
                    return 0.0
    return best


def _inside(pt, poly):
    """Punkt-in-Polygon, Strahlenverfahren (Polygon geschlossen oder offen)."""
    x, y = pt
    n = len(poly)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            xc = xi + (y - yi) * (xj - xi) / (yj - yi)
            if x < xc:
                inside = not inside
        j = i
    return inside


def _min_lin(a, b):
    """Kleinster Betrag einer linear zwischen a und b verlaufenden Groesse."""
    if (a <= 0.0 <= b) or (b <= 0.0 <= a):
        return 0.0
    return min(abs(a), abs(b))


def _self_intersects(poly):
    """Nicht benachbarte Kanten eines geschlossenen Zuges auf Schnitt pruefen."""
    p = list(poly)
    if p[0] != p[-1]:
        p.append(p[0])
    n = len(p) - 1
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            if _seg_dist(p[i], p[i + 1], p[j], p[j + 1]) <= 0.0:
                return True
    return False


# ================================================================ Bauteile
class Elem(object):
    """Ein Bauteil im (s, t)-Raum: Konturen, ggf. Umriss, Auslage."""

    def __init__(self, kind, chan, paths, poly=None, off=0.0, label=''):
        self.kind, self.chan = kind, chan
        self.paths = paths          # Liste von Punktlisten [(s,t), ...]
        self.poly = poly            # geschlossener Umriss oder None
        self.off = off
        self.label = label
        self.holes = []

    def anchored(self, L, H):
        return bool(self.anchor_kinds(L, H))

    def anchor_kinds(self, L, H):
        """Anker STRECKENWEISE, nicht nur an den Abtastpunkten.

        Ein Bogen kann den Untergurt tangential beruehren (U-Loop: der
        Scheitel liegt exakt auf t=0). Bei schiefwinkliger Basis faellt dieser
        Beruehrpunkt nicht auf einen Abtastpunkt — eine reine Punktpruefung
        wuerde den Anschluss uebersehen. Deshalb wird je Sehne das Minimum der
        (linearen) Randabstaende ausgewertet.
        """
        k = set()
        for path in self.paths:
            for i in range(len(path) - 1):
                (s0, t0), (s1, t1) = path[i], path[i + 1]
                if _min_lin(t0, t1) <= ATOL:
                    k.add('Untergurt')
                if _min_lin(t0 - H, t1 - H) <= ATOL:
                    k.add('Handlauf')
                if _min_lin(s0, s1) <= ATOL or _min_lin(s0 - L, s1 - L) <= ATOL:
                    k.add('Posten')
            if len(path) == 1:
                s0, t0 = path[0]
                if abs(t0) <= ATOL:
                    k.add('Untergurt')
                if abs(t0 - H) <= ATOL:
                    k.add('Handlauf')
                if abs(s0) <= ATOL or abs(s0 - L) <= ATOL:
                    k.add('Posten')
        return k


def touches(e1, e2):
    for a in e1.paths:
        for b in e2.paths:
            if _path_dist(a, b, JTOL) <= JTOL:
                return True
    if e2.poly and any(_inside(p, e2.poly) for p in e1.paths[0]):
        return True
    if e1.poly and any(_inside(p, e1.poly) for p in e2.paths[0]):
        return True
    return False


def build_elems(bay, st_of):
    els = []
    for chan in ('a', 'b'):
        for i, c in enumerate(getattr(bay, chan)):
            pts = [st_of(p) for p in c.pts]
            off = _off_of(bay, c.pts[0])
            els.append(Elem('bar', chan, [pts], None, off,
                            '%s[%d]' % (chan, i)))
    for chan in ('st', 'hz'):
        for i, sol in enumerate(getattr(bay, chan)):
            if sol.kind == 'plate':
                loops = [[st_of(p) for p in lp] for lp in sol.loops]
                outer = loops[0]
                e = Elem('plate' if chan == 'st' else 'block', chan,
                         loops, outer, _off_of(bay, sol.loops[0][0]),
                         '%s[%d]' % (chan, i))
                e.holes = loops[1:]
                els.append(e)
            else:                      # tordierter Vierkantstab (Loft)
                allp = [st_of(p) for lp in sol.loops for p in lp]
                s0, t0, s1, t1 = _bbox(allp)
                rect = [(s0, t0), (s1, t0), (s1, t1), (s0, t1), (s0, t0)]
                els.append(Elem('twisted', chan, [rect], rect,
                                0.0, '%s[%d]' % (chan, i)))
    return els


def _off_of(bay, p):
    d = p - bay.O
    return d * bay.Nh


# =========================================================== Blechpruefung
def plate_report(e, L, H, soll_rand=0.0, soll_steg=0.0):
    """Analytischer Zusammenhangsbeweis fuer eine Platte mit Aussparungen."""
    msgs, errs = [], []
    outer, holes = e.paths[0], e.holes
    if not holes:
        return msgs, errs, 1
    for k, h in enumerate(holes):
        if _self_intersects(h):
            errs.append('Aussparung %d schneidet sich selbst' % k)
    d_rand = min(_path_dist(h, outer, 1e9) for h in holes)
    d_steg = 1e30
    for i in range(len(holes)):
        for j in range(i + 1, len(holes)):
            d_steg = min(d_steg, _path_dist(holes[i], holes[j], 1e9))
    for k, h in enumerate(holes):
        if not _inside(h[0], outer):
            errs.append('Aussparung %d liegt ausserhalb der Aussenkontur' % k)
    if d_rand <= 0.0:
        errs.append('Aussparung beruehrt die Aussenkontur (Randabstand 0)')
    if len(holes) > 1 and d_steg <= 0.0:
        errs.append('zwei Aussparungen ueberlappen (Steg 0)')
    msgs.append('%d Aussparungen, Randabstand min %.1f mm, Steg min %s'
                % (len(holes), d_rand,
                   '-' if d_steg > 1e29 else '%.1f mm' % d_steg))
    # Kein Zusammenhangsfehler, aber die Engine hat eigene Mindestmasse (Blech-
    # Rand/Blech-Steg) — unterschreitet die Geometrie sie, steht hier ein Hinweis.
    if soll_rand and d_rand < soll_rand - 0.05:
        msgs.append('HINWEIS Randabstand %.1f < Blech-Rand %.0f mm'
                    % (d_rand, soll_rand))
    if soll_steg and d_steg < soll_steg - 0.05:
        msgs.append('HINWEIS Steg %.1f < Blech-Steg %.0f mm' % (d_steg, soll_steg))
    if errs:
        return msgs, errs, _raster_regions(e, L, H)
    return msgs, errs, 1


def _raster_regions(e, L, H, cells=280):
    """Rueckfallebene: Material rastern und Komponenten zaehlen."""
    s0, t0, s1, t1 = _bbox(e.paths[0])
    ds = (s1 - s0) / cells
    dt = (t1 - t0) / max(1, int(cells * (t1 - t0) / max(s1 - s0, 1e-9)))
    rows = max(1, int((t1 - t0) / dt))
    grid = []
    for r in range(rows):
        t = t0 + (r + 0.5) * dt
        row = []
        for c in range(cells):
            s = s0 + (c + 0.5) * ds
            mat = _inside((s, t), e.paths[0]) and not any(
                _inside((s, t), h) for h in e.holes)
            row.append(mat)
        grid.append(row)
    seen = [[False] * cells for _ in range(rows)]
    comps = 0
    for r in range(rows):
        for c in range(cells):
            if grid[r][c] and not seen[r][c]:
                comps += 1
                stack = [(r, c)]
                seen[r][c] = True
                while stack:
                    y, x = stack.pop()
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < rows and 0 <= nx < cells and grid[ny][nx] \
                                and not seen[ny][nx]:
                            seen[ny][nx] = True
                            stack.append((ny, nx))
    return comps


# ================================================================= Pruefung
def check_pattern(idx, lo, hi):
    ns = run_engine(idx, lo, hi)
    bay = ns['bays'][0]
    D = ns['D']
    L, H = bay.L, bay.H
    els = build_elems(bay, bay.st_of)
    errs, notes = [], []

    for e in els:
        if e.kind == 'plate':
            m, er, regions = plate_report(e, L, H, ns['BLECH_RAND'], ns['BLECH_STEG'])
            notes += m
            errs += er
            if regions > 1:
                errs.append('Blech zerfaellt in %d Materialinseln' % regions)

    n = len(els)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            if find(i) == find(j):
                continue
            if touches(els[i], els[j]):
                parent[find(i)] = find(j)

    comps = {}
    for i in range(n):
        comps.setdefault(find(i), []).append(i)
    direct = [i for i, e in enumerate(els) if e.anchored(L, H)]
    dset = set(direct)
    floating = []
    for root, members in comps.items():
        if not (dset & set(members)):
            floating += members

    kinds = set()
    for i in direct:
        kinds |= els[i].anchor_kinds(L, H)

    return dict(
        idx=idx, name=D['name'], key=D['key'],
        bars=sum(1 for e in els if e.kind == 'bar'),
        solids=sum(1 for e in els if e.kind != 'bar'),
        n=n, comps=len(comps), direct=len(direct),
        floating=[els[i].label + '/' + els[i].kind for i in floating],
        free=ns['free'], anchors=sorted(kinds), notes=notes, errs=errs,
        L=L, H=H)


BAYS = [
    ('flach  L=1000 H=900',
     LineCurve(P3(0, 0, 0), P3(1000, 0, 0)),
     LineCurve(P3(0, 0, 900), P3(1000, 0, 900))),
    ('steil  L=2236 H=1000 (Steigung 2:1)',
     LineCurve(P3(0, 0, 100), P3(1000, 0, 2100)),
     LineCurve(P3(0, 0, 1100), P3(1000, 0, 3100))),
    ('schmal L=420  H=1100',
     LineCurve(P3(0, 0, 0), P3(420, 0, 0)),
     LineCurve(P3(0, 0, 1100), P3(420, 0, 1100))),
]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    strict = False
    for arg in argv:
        if arg == '--strict':
            strict = True
        elif arg in ('-h', '--help'):
            print(__doc__)
            return 0
        else:
            print('Unbekanntes Argument: %s  (erlaubt: --strict)' % arg)
            return 2

    bad = 0                 # echte Fehlschlaege
    open_hits = 0           # Treffer auf KNOWN_OPEN
    open_seen = set()       # welche KNOWN_OPEN-Eintraege ueberhaupt gegriffen haben
    summary = []
    for title, lo, hi in BAYS:
        print('=' * 100)
        print('Referenzfeld: %s' % title)
        print('=' * 100)
        print('%3s %-13s %5s %6s %6s %6s %6s %6s  %s'
              % ('M', 'Name', 'Teile', 'Staebe', 'Solids', 'Komp.', 'direkt',
                 'freieE', 'Befund'))
        for idx in range(34):
            try:
                r = check_pattern(idx, lo, hi)
            except Exception as exc:          # noqa: BLE001 — Report statt Absturz
                print('%3d %-13s %s' % (idx, '?', 'EXCEPTION %s' % exc))
                bad += 1
                continue
            errs = list(r['errs'])
            if r['floating']:
                errs.append('SCHWEBEND %d von %d Teilen: %s%s'
                            % (len(r['floating']), r['n'],
                               ', '.join(r['floating'][:5]),
                               ' ...' if len(r['floating']) > 5 else ''))
            if r['free']:
                errs.append('Engine meldet %d freie Stabenden' % r['free'])
            if r['n'] == 0:
                errs.append('kein Bauteil erzeugt')
            known = KNOWN_OPEN.get(idx) if not strict else None
            if not errs:
                verdict = 'PASS'
            elif known:
                verdict = 'OFFEN'
                open_hits += 1
                open_seen.add(idx)
                summary.append((title, idx, r['name'], '; '.join(errs), known))
            else:
                verdict = 'FAIL'
                bad += 1
                summary.append((title, idx, r['name'], '; '.join(errs), None))
            extra = '; '.join(r['notes'])
            print('%3d %-13s %5d %6d %6d %6d %6d %6d  %-5s %s'
                  % (idx, r['name'][:13], r['n'], r['bars'], r['solids'],
                     r['comps'], r['direct'], r['free'], verdict,
                     ' | '.join(errs) if errs else
                     ('Anker: ' + ','.join(r['anchors'])
                      + ('  [' + extra + ']' if extra else ''))))
        print()
    if summary:
        print('-' * 100)
        for title, idx, name, msg, known in summary:
            print('%-5s Muster %02d %-12s  [%s]\n      %s'
                  % ('OFFEN' if known else 'FAIL', idx, name, title, msg))
            if known:
                print('      offene Entscheidung: %s' % known)
        print('-' * 100)
    stale = sorted(set(KNOWN_OPEN) - open_seen) if not strict else []
    for idx in stale:
        print('HINWEIS KNOWN_OPEN[%d] hat nicht gegriffen — Muster %02d haengt nicht '
              'mehr. Eintrag streichen: %s' % (idx, idx, KNOWN_OPEN[idx]))
    if bad:
        print('FEHLGESCHLAGEN: %d Muster-Feld-Kombinationen mit schwebender Geometrie'
              % bad
              + ('' if not open_hits else
                 ' (zusaetzlich %d als OFFEN gewertet)' % open_hits))
        return 1
    if open_hits:
        print('KEIN NEUER FEHLER: %d Muster-Feld-Kombinationen haengen an einer '
              'offenen Entscheidung (KNOWN_OPEN), sonst erreicht jede '
              'Zusammenhangskomponente den Rahmen' % open_hits)
        return 0
    print('ALLE 34 MUSTER: jede Zusammenhangskomponente erreicht den Rahmen')
    return 0


if __name__ == '__main__':
    sys.exit(main())
