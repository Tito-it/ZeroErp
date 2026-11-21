# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il gate prezzi di una riga di documento, letto dal CONTESTO DELLA
#        TESTATA — in un posto solo (regola del 2, ok Tid 2026-11-15, passo 6e
#        di brief-db-provenienza-prezzo-segue-il-prezzo §8.13).
#
#        Due building block, uno per famiglia di testata:
#        * `RegolePrezzoTestata` — ordine e DDT: emittente e data dalla
#          testata, il resolver del listino sul suo contesto, il gate. Erano
#          due copie gemelle (`_resolve_emittente_sr_id`, `_data_riferimento`,
#          `_resolve_prezzo_riga`, `_gate_prezzo_riga` in `ordini_service` e
#          `ddt_service`), diverse solo nei parametri di dominio.
#        * `resolve_or_check_override_prezzo_con_listino` — offerta e
#          contratto: il salto senza listino (col 409 sulla dichiarazione) e la
#          data della testata. Erano i due wrapper
#          `resolve_or_check_override_prezzo_riga_offerta` / `_contratto`.
#
#        Il gate vero resta UNO: `_pricing_gate_helpers.resolve_or_check_
#        override_prezzo`. Qui sta solo cio' che ogni documento gli passava
#        ricopiato.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Protocol

from apps.core.services.error_manager import ErrorManager
from apps.vendite.services._iva_contesto_documento import data_di_riferimento
from apps.vendite.services._pricing_gate_helpers import (
    EsitoPrezzoRiga,
    ProvenienzaDichiarata,
    resolve_or_check_override_prezzo,
    rifiuta_provenienza_dichiarata,
)

__all__ = [
    "RegolePrezzoTestata",
    "resolve_or_check_override_prezzo_con_listino",
]


# Scopo: cio' che il BB chiede al repository del dominio: la traduzione della
#        PK dell'emittente nel `soggetto_ruolo_id` che il pricing vuole.
#        `OrdiniRepository` e `DdtRepository` la hanno uguale.
class _RepoEmittente(Protocol):
    def get_emittente_sr_id_by_fiscale_id(self, fiscale_id: int) -> int | None: ...


# Scopo: le regole del prezzo di riga di un documento la cui testata porta
#        emittente, billing account, utility e data (ordine, DDT). Si
#        costruisce una volta per dominio, al livello del modulo del service
#        (`_REGOLE_PREZZO`), e il service ne chiama i metodi.
# ⛔ Niente alias di modulo per i metodi (`_gate_prezzo_riga = …`): i metodi si
#    chiamano fra loro, e una patch sull'alias non arriverebbe al gate, senza
#    errore. I test patchano la classe (`test_la_patch_sulla_classe_arriva_al_gate`).
#
# ⭐ Immutabile e senza stato: i parametri sono di dominio, il repository e la
#    testata arrivano a ogni chiamata. Condividerla fra richieste non
#    trasporta niente dall'una all'altra.
#
# Parametri di dominio:
#   - `documento`: il soggetto delle frasi d'errore («Ordine», «DDT»);
#   - `error_code`: il codice di validazione del dominio;
#   - `function_name`: il prefisso del `function_name` (il `_FN` del service);
#   - `prezzo_assente_ammesso`: ⛔ LA differenza fra i due domini, ed e' una
#     sola. Sull'ordine il prezzo e' obbligatorio: il resolver e' il GUSCIO
#     (`resolve_prezzo`), che solleva quando non risolve, e un gate senza
#     prezzo e' un errore (BE-3/DEC-2 di brief-ddt-righe-senza-prezzo). Sul
#     DDT un prezzo che il listino non da' NON e' un errore: il resolver e' il
#     NUCLEO (`resolve_prezzo_esito`), e l'esito torna senza prezzo e col
#     motivo (`esito_codice`), che il chiamante conserva. Guscio e obbligo
#     vanno insieme: un flag solo, perche' due potrebbero divergere.
#
# ⛔ Niente ripiego a «0» sul prezzo che manca (V-6 di
#    brief-ddt-righe-senza-prezzo): zero e' un prezzo, e una riga a valore
#    nullo entrerebbe in fattura invece di essere fermata.
# Senza L3: ordine e DDT non hanno il workflow di approvazione, e una
#    violazione L2 e' un rifiuto.
@dataclass(frozen=True)
class RegolePrezzoTestata:
    documento: str
    error_code: str
    function_name: str
    prezzo_assente_ammesso: bool

    # Scopo: l'`emittente_soggetto_ruolo_id` che pricing e componenti vogliono,
    #        dalla PK `emittente_fiscale_id` della testata.
    # ⛔ La testata porta la PK di `anagrafiche.emittenti_fiscali`, NON il
    #    `soggetto_ruolo_id` (memoria feedback_emittente_pk_vs_soggetto_ruolo):
    #    qui la si traduce. Su ordine e DDT il trigger normalize la garantisce
    #    NOT NULL alla creazione: una testata senza e' anomala.
    def emittente_sr_id(self, repo: _RepoEmittente, testata: Mapping[str, Any]) -> int:
        fn = f"{self.function_name}.emittente_sr_id"
        fiscale_id = testata.get("emittente_fiscale_id")
        ErrorManager.require(
            fiscale_id is not None,
            code=self.error_code,
            message=f"{self.documento} senza emittente fiscale: impossibile risolvere prezzi e componenti.",
            function_name=fn,
        )
        assert fiscale_id is not None
        sr_id = repo.get_emittente_sr_id_by_fiscale_id(int(fiscale_id))
        ErrorManager.require(
            sr_id is not None,
            code=self.error_code,
            message="Soggetto-ruolo emittente non risolvibile.",
            function_name=fn,
        )
        assert sr_id is not None
        return int(sr_id)

    # Scopo: la data di riferimento di pricing e componenti: la data del
    #        documento. Senza, non c'e' niente da chiedere al listino. La
    #        regola e' del BB `data_di_riferimento`, la stessa del risolutore
    #        IVA; qui c'e' solo la frase.
    def data_riferimento(self, testata: Mapping[str, Any]) -> date:
        return data_di_riferimento(
            testata,
            error_code=self.error_code,
            message=f"{self.documento} senza data: impossibile risolvere prezzi e componenti.",
            function_name=f"{self.function_name}.data_riferimento",
        )

    # Scopo: il prezzo di riga dal listino via `PricingService` (BB condiviso,
    #        mai query dirette su listini — memoria feedback_pricing_centralizzato):
    #        la riga intera del resolver, provenienza e contesto compresi. Guscio
    #        o nucleo secondo `prezzo_assente_ammesso`.
    def resolve_prezzo_riga(
        self, repo: _RepoEmittente, testata: Mapping[str, Any], *,
        articolo_id: str, uom_id: int | None,
    ) -> dict[str, Any]:
        # Import locale: `pricing_service` e' un vicino pesante, e i test lo
        # patchano alla sua sede (`apps.vendite.services.pricing_service`).
        from apps.vendite.services.pricing_service import PricingService

        fn = f"{self.function_name}.resolve_prezzo_riga"
        ErrorManager.require(
            testata.get("billing_account_id") is not None,
            code=self.error_code,
            message=f"{self.documento} senza billing_account: impossibile risolvere il prezzo.",
            function_name=fn,
        )
        ErrorManager.require(
            testata.get("utility_id") is not None,
            code=self.error_code,
            message=f"{self.documento} senza utility: impossibile risolvere il prezzo.",
            function_name=fn,
        )
        ErrorManager.require(
            uom_id is not None,
            code=self.error_code,
            message="uom_operativa_id obbligatorio per risolvere il prezzo.",
            context={"field": "uom_operativa_id"},
            function_name=fn,
        )
        assert uom_id is not None
        emittente_sr_id = self.emittente_sr_id(repo, testata)
        pricing = PricingService()
        risolvi = (
            pricing.resolve_prezzo_esito if self.prezzo_assente_ammesso
            else pricing.resolve_prezzo
        )
        return risolvi(
            articolo_id=articolo_id,
            uom_id=int(uom_id),
            data_riferimento=self.data_riferimento(testata),
            ba_id=int(testata["billing_account_id"]),
            utility_id=int(testata["utility_id"]),
            emittente_soggetto_ruolo_id=emittente_sr_id,
        )

    # Scopo: il gate prezzi di una riga (BB `resolve_or_check_override_prezzo`)
    #        col resolver del listino sul contesto della testata.
    def gate_prezzo_riga(
        self, repo: _RepoEmittente, testata: Mapping[str, Any], *,
        articolo_id: str, uom_id: int | None, payload_prezzo: Any,
        dichiarata: ProvenienzaDichiarata | None, auth_user_id: int | None,
        function_name: str,
    ) -> EsitoPrezzoRiga:
        # Senza unita' di misura il listino non si interroga, e il gate
        # tratterebbe ogni prezzo come scritto a mano (L1): qui si dice al form
        # quale campo manca.
        ErrorManager.require(
            uom_id is not None,
            code=self.error_code,
            message="uom_operativa_id obbligatorio per risolvere il prezzo.",
            context={"field": "uom_operativa_id"},
            function_name=function_name,
        )

        def _resolver(
            _documento_id: int, *, articolo_id: str, uom_id: int, auth_user_id: int | None,
        ) -> dict[str, Any]:
            del auth_user_id
            return self.resolve_prezzo_riga(repo, testata, articolo_id=articolo_id, uom_id=uom_id)

        esito = resolve_or_check_override_prezzo(
            testata=testata, articolo_id=articolo_id, uom_id=uom_id,
            payload_prezzo=payload_prezzo, auth_user_id=auth_user_id,
            function_name=function_name, resolver_fn=_resolver,
            error_code_validazione=self.error_code, dichiarata=dichiarata,
        )
        if esito.prezzo is None and not self.prezzo_assente_ammesso:
            # Il guscio che non risolve SOLLEVA, e l'errore risale dal gate col
            # suo codice: qui resta il contesto che manca alla testata.
            ErrorManager.raise_error(
                code=self.error_code,
                message="Prezzo unitario non risolvibile dal listino: indicarlo.",
                context={"field": "prezzo_unitario"},
                function_name=function_name,
            )
        return esito


# Scopo: il gate prezzi di una riga di un documento il cui prezzo viene da un
#        listino SCELTO in testata (offerta, contratto). Due cose che i due
#        wrapper di dominio ricopiavano:
#        1. ⛔ senza listino non c'e' gate: il prezzo e' del payload (negoziato,
#           decisione del 2026-05-20) e la provenienza la decide il DB
#           (MANUALE). Una dichiarazione «dal listino» li' non si puo'
#           verificare: 409, come il gate senza contesto (R-2 della revisione
#           del 2026-11-15; prima diventava MANUALE in silenzio);
#        2. la data: il gate legge `testata["data"]`, la testata la chiama a
#           modo suo (`campo_data`: `validita_dal` sull'offerta, `valido_dal`
#           sul contratto).
#
# ⚠️ `resolver_fn` lo passa il wrapper di dominio a ogni chiamata, e non si
#    fissa in una factory: il wrapper lo legge dal suo modulo al momento della
#    chiamata, ed e' cio' che i test patchano.
def resolve_or_check_override_prezzo_con_listino(
    *,
    testata: Mapping[str, Any],
    campo_data: str,
    articolo_id: Any,
    uom_id: Any,
    payload_prezzo: Any,
    auth_user_id: int | None,
    function_name: str,
    resolver_fn: Callable[..., dict[str, Any]],
    error_code_validazione: str,
    richiesta_approvazione: bool = False,
    dichiarata: ProvenienzaDichiarata | None = None,
) -> EsitoPrezzoRiga:
    if testata.get("listino_id") is None:
        if dichiarata is not None and payload_prezzo is not None:
            rifiuta_provenienza_dichiarata(
                dichiarata, dettaglio="Il documento non ha un listino da cui il prezzo possa venire.",
                function_name=function_name,
            )
        return EsitoPrezzoRiga(prezzo=payload_prezzo)

    testata_con_data = (
        testata if testata.get("data") is not None
        else {**testata, "data": testata.get(campo_data)}
    )
    return resolve_or_check_override_prezzo(
        testata=testata_con_data,
        articolo_id=articolo_id,
        uom_id=uom_id,
        payload_prezzo=payload_prezzo,
        auth_user_id=auth_user_id,
        function_name=function_name,
        resolver_fn=resolver_fn,
        error_code_validazione=error_code_validazione,
        richiesta_approvazione=richiesta_approvazione,
        dichiarata=dichiarata,
    )
