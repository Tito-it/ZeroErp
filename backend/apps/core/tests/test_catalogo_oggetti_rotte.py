# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio della D-3 (brief-db-be-fe-catalogo-oggetti-permessi): le
#        porte che chiedono il livello di un oggetto dicono la stessa cosa del
#        catalogo. Un override per oggetto che una rotta non chiede e' un
#        override che MENTE: il pannello lo mostra, e quella rotta risponde col
#        livello dell'area. Un oggetto chiesto e non a catalogo e' l'opposto: il
#        codice lo dichiara configurabile, il pannello non lo offre.
#        Le porte confrontate col catalogo:
#        - il seed `80_data/sql/config/area_model_overrides.csv` (il catalogo,
#          righe `riservato = f`: i riservati sono dichiarati, non offerti);
#        - il `model_permission` delle view BE, letto dal percorso reale;
#        - `READONLY_MODELS` del FE (`core/constants.js`).
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
#       (documenti, passaggi, riepilogo IVA, indirizzi, situazione merce) e gli
#       attributi ereditati.
#       ⭐ Il catalogo si legge dal CSV del seed (D-3, `20260928-03`), non dal
#       DB: nessun DB, e il test va rosso nella PR che rompe l'allineamento,
#       non all'apply. L'URLconf e' gia' importato dai system check del runner.
#       ⏳ `_IN_ATTESA_DI_CATALOGO`: oggetti che BE e FE applicano gia' su tutte
#       le rotte e la cui riga di catalogo e' chiesta al team DB. Il test 5
#       pretende che la riga esca dal registro il giorno in cui entra nel CSV.
# ------------------------------------------------------------

"""
Indice test (0..6):
 0. test_ogni_oggetto_ha_rotte_nel_perimetro
 1. test_ogni_rotta_del_perimetro_chiede_il_suo_oggetto
 2. test_il_registro_fuori_perimetro_non_ha_righe_morte
 3. test_ogni_oggetto_chiesto_dal_be_e_a_catalogo
 4. test_ogni_oggetto_a_catalogo_ha_un_perimetro
 5. test_il_fe_chiede_gli_stessi_oggetti_del_catalogo
 6. test_il_registro_in_attesa_non_ha_righe_gia_a_catalogo
"""

import csv
import re
from dataclasses import dataclass

from django.test import SimpleTestCase

from apps.core.api.base_views import AdminAPIView
from apps.core.api.permissions import ZeroERPPermission
from apps.core.api.rotte import Rotta, rotte_servite
from apps.core.tests._repo import repo_root

_METODI: tuple[str, ...] = tuple(m.lower() for m in ZeroERPPermission.METHOD_REQUIRES)

_CATALOGO_CSV = (
    repo_root() / "db/changelog/migrations_v2/80_data/sql/config/area_model_overrides.csv"
)
_COSTANTI_FE = repo_root() / "frontend/src/core/constants.js"


# Scopo: gli oggetti PERSONALIZZABILI del catalogo (`riservato = f`), dal seed.
def _catalogo_personalizzabile() -> set[tuple[str, str]]:
    with _CATALOGO_CSV.open(encoding="utf-8", newline="") as fh:
        righe = list(csv.DictReader(fh))
    assert righe, f"catalogo vuoto: {_CATALOGO_CSV}"
    return {(r["app_label"], r["model_name"]) for r in righe if r["riservato"] == "f"}


# Scopo: i nomi di modello di `READONLY_MODELS` del FE (i valori, non le chiavi).
def _readonly_models_fe() -> set[str]:
    testo = _COSTANTI_FE.read_text(encoding="utf-8")
    blocco = re.search(r"export const READONLY_MODELS = \{(.*?)\n\}", testo, re.S)
    assert blocco, f"READONLY_MODELS non trovato in {_COSTANTI_FE}"
    valori = set(re.findall(r":\s*'(\w+)'", blocco.group(1)))
    assert valori, "READONLY_MODELS senza valori leggibili"
    return valori


# ⏳ Oggetti che BE (model_permission su tutte le rotte) e FE (READONLY_MODELS)
#    applicano gia', in attesa della riga di catalogo chiesta al team DB. Senza
#    la riga vale l'area, come prima: il giorno in cui entra, le quattro porte
#    dicono gia' la stessa cosa.
# ⭐ VUOTO dal 2026-09-28: `ordine`, `ddt`, `contratto`, `reso` sono entrati
#    nel CSV (§3.6 del brief). Il registro resta perche' e' la strada del
#    prossimo oggetto (BE e FE prima, catalogo poi), e il test 6 la sorveglia.
_IN_ATTESA_DI_CATALOGO: dict[tuple[str, str], str] = {}


# Scopo: un oggetto del catalogo e il perimetro delle sue rotte (pattern sul
#        percorso composto dal resolver, senza `/` iniziale).
@dataclass(frozen=True)
class Perimetro:
    oggetto: tuple[str, str]
    percorsi: tuple[str, ...]


# Un perimetro per ogni oggetto a catalogo (o in attesa). Il billing account e'
# un pezzo del cliente (D-5): la sua rotta chiede `cliente`.
_PERIMETRI: tuple[Perimetro, ...] = (
    Perimetro(("anagrafiche", "soggetto"), (
        # I conti bancari sotto il soggetto sono l'oggetto `conto_bancario`.
        r"^api/v1/anagrafiche/soggetti/(?!<str:soggetto_id>/conti-bancari/)",
        r"^api/v1/anagrafiche/titoli-iva/",
    )),
    Perimetro(("anagrafiche", "cliente"), (
        r"^api/v1/anagrafiche/clienti/",
        r"^api/v1/anagrafiche/billing-account/<int:billing_account_id>/utilities/",
    )),
    Perimetro(("anagrafiche", "fornitore"), (r"^api/v1/anagrafiche/fornitori/",)),
    Perimetro(("anagrafiche", "conto_bancario"), (
        r"^api/v1/anagrafiche/(soggetti/<str:soggetto_id>|ruoli/<int:soggetto_ruolo_id>)/conti-bancari/",
        r"^api/v1/anagrafiche/conti-bancari/",
    )),
    Perimetro(("catalogo", "articolo"), (
        r"^api/v1/catalogo/articoli/",
        r"^api/v1/catalogo/note/",
    )),
    Perimetro(("catalogo", "unita_misura"), (r"^api/v1/catalogo/(unita-misura|conversioni-uom)/",)),
    Perimetro(("catalogo", "uom_tipi"), (r"^api/v1/catalogo/uom-tipi/",)),
    Perimetro(("vendite", "promo_articolo"), (r"^api/v1/vendite/promo-articoli/",)),
    Perimetro(("vendite", "fattura"), (
        r"^api/v1/vendite/fatture/",
        r"^api/v1/vendite/lotti/<int:lotto_id>/fatture/",
    )),
    Perimetro(("vendite", "preventivo"), (r"^api/v1/vendite/preventivi/",)),
    Perimetro(("vendite", "offerta_commerciale"), (r"^api/v1/vendite/offerte/",)),
    Perimetro(("vendite", "ordine"), (r"^api/v1/vendite/ordini/",)),
    Perimetro(("vendite", "ddt"), (r"^api/v1/vendite/ddt/",)),
    Perimetro(("vendite", "contratto"), (r"^api/v1/vendite/contratti/",)),
    Perimetro(("vendite", "reso"), (r"^api/v1/vendite/resi/",)),
    Perimetro(("vendite", "listino"), (
        r"^api/v1/vendite/listini/",
        # D-6: un lookup della stessa area chiede l'oggetto che legge.
        r"^api/v1/vendite/lookup/listini-",
    )),
    Perimetro(("pratiche", "pratica"), (r"^api/v1/pratiche/",)),
)

# ⛔ Rotte nel perimetro di un oggetto che NON sono quell'oggetto. Ogni riga
#    con la ragione: una riga senza ragione e' il posto in cui si mettono le
#    cose per farle passare.
_FUORI_PERIMETRO: dict[str, str] = {
    "ApiCompetenzeFlussiList": "chi e' competente su quale flusso: configurazione dell'area pratiche, non la pratica",
    "ApiCompetenzaFlussoDetail": "idem: configurazione delle competenze",
    "ApiFormuleTempo": "catalogo delle formule di tempo: configurazione, non la pratica",
    "ApiOperatoriReparto": "operatori assegnabili: lookup sulle risorse umane, non la pratica",
    "ValidaCFPIVAView": "calcolo senza dati: controlla un codice fiscale o una partita IVA, non legge ne' scrive un soggetto",
    "GeneraCFView": "calcolo senza dati: compone un codice fiscale dai dati del form, non legge ne' scrive un soggetto",
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


# Scopo: le rotte servite, con la loro classe.
def _rotte() -> list[Rotta]:
    return [r for r in rotte_servite(anche_condizionali=True) if r.view is not None]


# Scopo: le rotte (con classe) del perimetro.
def _rotte_del(perimetro: Perimetro) -> list[Rotta]:
    return [r for r in _rotte() if any(re.search(p, r.percorso) for p in perimetro.percorsi)]


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

    # Scopo: D-3, verso BE -> catalogo. Un `model_permission` che il catalogo
    #        non ha dichiara configurabile un oggetto che il pannello non offre
    #        (caso B del brief): vale sempre l'area, in silenzio.
    def test_ogni_oggetto_chiesto_dal_be_e_a_catalogo(self):
        ammessi = _catalogo_personalizzabile() | set(_IN_ATTESA_DI_CATALOGO)
        fuori: dict[tuple[str, str], list[str]] = {}
        for rotta in _rotte():
            mp = getattr(rotta.view, "model_permission", None)
            if mp is not None and tuple(mp) not in ammessi:
                fuori.setdefault(tuple(mp), []).append(rotta.percorso)
        self.assertEqual(fuori, {})

    # Scopo: D-3, verso catalogo -> BE. Ogni oggetto personalizzabile ha un
    #        perimetro (e quindi, test 0, delle rotte che lo chiedono): una voce
    #        a catalogo senza rotte e' un override che nessuna richiesta guarda.
    def test_ogni_oggetto_a_catalogo_ha_un_perimetro(self):
        attesi = _catalogo_personalizzabile() | set(_IN_ATTESA_DI_CATALOGO)
        con_perimetro = {p.oggetto for p in _PERIMETRI}
        self.assertEqual(sorted(attesi - con_perimetro), [], "oggetti senza perimetro")
        self.assertEqual(sorted(con_perimetro - attesi), [], "perimetri di oggetti fuori catalogo")

    # Scopo: D-3, la porta FE. `useReadonlyMode(area, model)` con un modello
    #        fuori catalogo nasconde pulsanti che l'API non chiude; un oggetto
    #        a catalogo che il FE non chiede lascia i pulsanti a un override
    #        che l'API applica (il «terzo caso» del §1, nei due versi).
    def test_il_fe_chiede_gli_stessi_oggetti_del_catalogo(self):
        attesi = {m for _, m in _catalogo_personalizzabile() | set(_IN_ATTESA_DI_CATALOGO)}
        self.assertEqual(sorted(_readonly_models_fe() ^ attesi), [])

    # Scopo: una riga in attesa che e' gia' nel CSV va tolta dal registro: da
    #        quel giorno l'oggetto e' a catalogo, e il registro direbbe il falso.
    def test_il_registro_in_attesa_non_ha_righe_gia_a_catalogo(self):
        self.assertEqual(sorted(set(_IN_ATTESA_DI_CATALOGO) & _catalogo_personalizzabile()), [])
