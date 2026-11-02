# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio sulle COPPIE lista/export: la view `…/export/` deve
#        dichiarare lo STESSO `lista_codice` della lista `…/` da cui nasce.
#        E' il punto dell'export configurabile — le colonne del file sono
#        quelle che l'operatore VEDE (preferenza + preset + permessi, risolte
#        da `build_export_response` sul `lista_codice`) — e il cancello di
#        perimetro emittente vale sulla porta piu' larga solo se le due view
#        dicono lo stesso codice. Due letterali uguali divergono al primo
#        rename SENZA nessun errore: l'export scaricherebbe le colonne di
#        un'altra lista, o cadrebbe fuori dal cancello.
#
#        Trovato in rilettura il 2026-09-18: 25 coppie con il letterale
#        ricopiato nelle due classi. Due (`distinta_righe`,
#        `sistemazioni_fattura`) leggono ora il codice dalla lista
#        (`lista_codice = ApiX.lista_codice`); le altre restano letterali e
#        questo test le tiene uguali — cosi' il letterale ricopiato smette di
#        essere un rischio senza che si debba toccare 15 file.
# Note: ⭐ Le coppie si leggono DALLE ROTTE (`get_resolver`), non da un elenco
#       scritto qui: una rotta `…/export/` nuova entra da sola, e la sua lista
#       e' la rotta con lo stesso percorso meno `export/`. Nessun DB: l'URLconf
#       e' gia' importato dai system check del runner.
# ------------------------------------------------------------
"""
Indice test (0..N):
 0. test_la_scansione_trova_le_coppie_che_deve_trovare
 1. test_ogni_export_dichiara_il_lista_codice_della_sua_lista
"""

from dataclasses import dataclass
from functools import lru_cache

from django.test import SimpleTestCase

from apps.core.api.rotte import rotte_servite

_SUFFISSO_EXPORT = "export/"


@dataclass(frozen=True)
class _Coppia:
    percorso_lista: str
    # Le view «lista» accanto all'export: di norma una (la rotta senza il
    # suffisso), ma la rotta base puo' essere un RIEPILOGO e la lista stare un
    # segmento sotto (`lotti/<id>/segnalazioni/` e' il summary, la lista e'
    # `segnalazioni/rows/`). Si prendono quindi la base e i figli di primo
    # livello che dichiarano un `lista_codice` — ⚠️ esclusi i figli che hanno
    # un export PROPRIO (`resi/da-accreditare/` sotto `resi/`): quelli sono
    # un'altra coppia, non un'altra lettura di questa.
    liste: tuple[type, ...]
    export: type


# Scopo: percorso completo -> classe di view, per ogni rotta dell'URLconf
#        (anche quelle montate a condizione). Il cammino e' il BB
#        `apps.core.api.rotte` (estratto il 2026-09-25, regola del 2).
def _rotte() -> dict[str, type]:
    return {
        r.percorso: r.view
        for r in rotte_servite(anche_condizionali=True)
        if r.view is not None
    }


# Scopo: le coppie (liste, export) — ogni rotta che finisce in `export/`
#        accoppiata alla rotta base (stesso percorso meno il suffisso) e ai suoi
#        figli di primo livello con un `lista_codice`. Un export senza nessuna
#        lista accanto resta con `liste` vuota, e il test 1 lo dice.
@lru_cache(maxsize=1)
def _coppie() -> tuple[_Coppia, ...]:
    rotte = _rotte()
    coppie = []
    for percorso, cls_export in rotte.items():
        if not percorso.endswith(_SUFFISSO_EXPORT):
            continue
        base = percorso[: -len(_SUFFISSO_EXPORT)]
        liste = tuple(
            cls for p, cls in sorted(rotte.items())
            if p != percorso
            and (p == base or (p.startswith(base) and p[len(base):].count("/") == 1))
            and getattr(cls, "lista_codice", None)
            and (p == base or p + _SUFFISSO_EXPORT not in rotte)
        )
        coppie.append(_Coppia(base, liste, cls_export))
    return tuple(sorted(coppie, key=lambda c: c.percorso_lista))


class ExportListaCodicePariTests(SimpleTestCase):
    # Scopo: la scansione ha materia — se le rotte cambiassero forma e le
    #        coppie diventassero zero, il test 1 sarebbe verde per sottrazione.
    #        Al 2026-09-18 le coppie con una lista accanto sono 28 (29 export;
    #        `famiglie/` non ha `lista_codice` da nessuna delle due parti).
    def test_la_scansione_trova_le_coppie_che_deve_trovare(self) -> None:
        con_codice = [c for c in _coppie() if c.liste]
        self.assertGreaterEqual(len(con_codice), 25, [c.percorso_lista for c in con_codice])

    # Scopo: stesso `lista_codice` fra l'export e OGNI lista accanto. Se nessuna
    #        lista ne dichiara uno, nemmeno l'export deve inventarselo: un
    #        export con un codice che la lista non ha non copia nessuna videata.
    def test_ogni_export_dichiara_il_lista_codice_della_sua_lista(self) -> None:
        for coppia in _coppie():
            with self.subTest(rotta=coppia.percorso_lista):
                codice_export = getattr(coppia.export, "lista_codice", None)
                attesi = {cls.lista_codice for cls in coppia.liste} or {None}
                self.assertEqual(
                    attesi, {codice_export},
                    f"{coppia.export.__name__} dice `{codice_export}`, le liste "
                    f"accanto ({', '.join(c.__name__ for c in coppia.liste) or 'nessuna'}) "
                    f"dicono {sorted(map(str, attesi))}: il file avrebbe le colonne "
                    "di un'altra lista, o cadrebbe fuori dal cancello di perimetro. "
                    "La forma che non diverge e' `lista_codice = ApiLista.lista_codice`.",
                )
