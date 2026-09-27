# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio «un oggetto a catalogo si applica su tutte le sue rotte»
#        (brief-db-be-fe-catalogo-oggetti-permessi, caso A, §3.2). Un override
#        per oggetto che una rotta non chiede e' un override che MENTE: il
#        pannello lo mostra, e quella rotta risponde col livello dell'area.
#        Per ogni oggetto, ogni rotta del suo perimetro deve:
#        - chiedere quell'oggetto (`model_permission`), oppure
#        - decidere con un'azione di processo su OGNI metodo che serve
#          (`<metodo>_permission`: li' il livello non si guarda, §5 del brief),
#          oppure
#        - essere un lookup cross-dominio (`skip_area_check` senza area) o una
#          rotta `AdminAPIView` (solo SUPER_ADMIN, fuori dalla catena d'area).
#        Cio' che resta fuori per scelta sta nel registro `_FUORI_PERIMETRO`,
#        con la ragione.
# Note: ⭐ Legge le view DAL PERCORSO REALE (`apps.core.api.rotte`), con
#       `getattr` come la catena: vede anche le classi delle factory
#       (documenti, passaggi, riepilogo IVA, indirizzi) e gli attributi
#       ereditati.
#       ⏳ E' il primo pezzo del presidio della D-3: quando il catalogo sara'
#       un CSV (richiesta al team DB, §3.1 del brief), gli oggetti qui sotto
#       si leggeranno da li' e non da questa tabella, e il test controllera'
#       anche il verso opposto (una voce a catalogo senza rotte).
#       Nessun DB: l'URLconf e' gia' importato dai system check del runner.
# ------------------------------------------------------------

"""
Indice test (0..N):
 0. test_ogni_oggetto_ha_rotte_nel_perimetro
 1. test_ogni_rotta_del_perimetro_chiede_il_suo_oggetto
 2. test_il_registro_fuori_perimetro_non_ha_righe_morte
"""

import re
from dataclasses import dataclass

from django.test import SimpleTestCase

from apps.core.api.base_views import AdminAPIView
from apps.core.api.permissions import ZeroERPPermission
from apps.core.api.rotte import Rotta, rotte_servite

_METODI: tuple[str, ...] = tuple(m.lower() for m in ZeroERPPermission.METHOD_REQUIRES)


# Scopo: un oggetto del catalogo e il perimetro delle sue rotte (pattern sul
#        percorso composto dal resolver, senza `/` iniziale).
@dataclass(frozen=True)
class Perimetro:
    oggetto: tuple[str, str]
    percorsi: tuple[str, ...]


# Il caso A del brief: oggetti gia' a catalogo. Il billing account e' un pezzo
# del cliente (D-5): la sua rotta chiede `cliente`.
_PERIMETRI: tuple[Perimetro, ...] = (
    Perimetro(("vendite", "fattura"), (
        r"^api/v1/vendite/fatture/",
        r"^api/v1/vendite/lotti/<int:lotto_id>/fatture/",
    )),
    Perimetro(("vendite", "preventivo"), (r"^api/v1/vendite/preventivi/",)),
    Perimetro(("vendite", "listino"), (
        r"^api/v1/vendite/listini/",
        # D-6: un lookup della stessa area chiede l'oggetto che legge.
        r"^api/v1/vendite/lookup/listini-",
    )),
    Perimetro(("pratiche", "pratica"), (r"^api/v1/pratiche/",)),
    Perimetro(("anagrafiche", "cliente"), (
        r"^api/v1/anagrafiche/billing-account/<int:billing_account_id>/utilities/",
    )),
)

# ⛔ Rotte nel perimetro di un oggetto che NON sono quell'oggetto. Ogni riga
#    con la ragione: una riga senza ragione e' il posto in cui si mettono le
#    cose per farle passare.
_FUORI_PERIMETRO: dict[str, str] = {
    "ApiCompetenzeFlussiList": "chi e' competente su quale flusso: configurazione dell'area pratiche, non la pratica",
    "ApiCompetenzaFlussoDetail": "idem: configurazione delle competenze",
    "ApiFormuleTempo": "catalogo delle formule di tempo: configurazione, non la pratica",
    "ApiOperatoriReparto": "operatori assegnabili: lookup sulle risorse umane, non la pratica",
}


# Scopo: la rotta e' in regola rispetto all'oggetto? None se si', altrimenti
#        la ragione del no.
def _difetto(rotta: Rotta, oggetto: tuple[str, str]) -> str | None:
    view = rotta.view
    if isinstance(view, type) and issubclass(view, AdminAPIView):
        return None
    if getattr(view, "skip_area_check", False) and not getattr(view, "area_funzionale", None):
        return None
    mp = getattr(view, "model_permission", None)
    if mp is not None:
        return None if tuple(mp) == oggetto else f"chiede {mp}, non {oggetto}"
    metodi = [m for m in _METODI if hasattr(view, m) and m not in ("head", "options")]
    if metodi and all(getattr(view, f"{m}_permission", None) for m in metodi):
        return None
    scoperti = [m for m in metodi if not getattr(view, f"{m}_permission", None)]
    return f"senza model_permission, metodi scoperti: {scoperti}"


# Scopo: le rotte (con classe) del perimetro.
def _rotte_del(perimetro: Perimetro) -> list[Rotta]:
    return [
        r for r in rotte_servite(anche_condizionali=True)
        if r.view is not None and any(re.search(p, r.percorso) for p in perimetro.percorsi)
    ]


class CatalogoOggettiRotteTests(SimpleTestCase):

    # Scopo: un perimetro senza rotte farebbe passare il test 1 a vuoto.
    def test_ogni_oggetto_ha_rotte_nel_perimetro(self):
        for perimetro in _PERIMETRI:
            with self.subTest(oggetto=perimetro.oggetto):
                self.assertTrue(_rotte_del(perimetro), f"nessuna rotta per {perimetro.oggetto}")

    # Scopo: il presidio vero: ogni rotta chiede il suo oggetto.
    def test_ogni_rotta_del_perimetro_chiede_il_suo_oggetto(self):
        difetti: list[str] = []
        for perimetro in _PERIMETRI:
            for rotta in _rotte_del(perimetro):
                if rotta.view.__name__ in _FUORI_PERIMETRO:
                    continue
                motivo = _difetto(rotta, perimetro.oggetto)
                if motivo:
                    difetti.append(f"{rotta.percorso} ({rotta.view.__name__}): {motivo}")
        self.assertEqual(difetti, [], "\n" + "\n".join(difetti))

    # Scopo: una riga del registro che non corrisponde piu' a nessuna rotta del
    #        perimetro va tolta, o il registro smette di dire la verita'.
    def test_il_registro_fuori_perimetro_non_ha_righe_morte(self):
        viste = {r.view.__name__ for p in _PERIMETRI for r in _rotte_del(p)}
        self.assertEqual(sorted(set(_FUORI_PERIMETRO) - viste), [])
