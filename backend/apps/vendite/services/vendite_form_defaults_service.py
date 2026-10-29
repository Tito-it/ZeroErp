# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Form-defaults BA-aware e contestuali per vendite
#        (Fase 2.B3-B5 refactor frontend vendite).
#
#        Espone 5 funzioni read-only consumate dal FE all'apertura dei
#        drawer per popolare i campi che dipendono da contesto (BA,
#        listino, versione) o da parameters di sistema. Single source
#        of truth lato BE: il FE non deve piu' inventare valuta/termini
#        dal cliente, suffisso/lead_gg dei codici versione, ecc.
#
#        Pattern: niente classe, funzioni `fn_*` allineate al modello
#        di `vendite_lookups_service`. Errori applicativi via
#        ErrorManager (codici E_VENDITE_NOT_FOUND/VALIDATION).
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.anagrafiche.db.billing_account_repository import BillingAccountRepository
from apps.anagrafiche.services.valuta_resolver import resolve_valuta_default
from apps.core.services.error_manager import ErrorManager
from apps.core.services.parameter_service import ParameterService
from apps.vendite.db._documento_eccezioni_repo import fornitura_da_anagrafica
from apps.vendite.db.listini_repository import ListiniRepository


_FN = "vendite.form_defaults_service"

# Codici errore (riusiamo la tassonomia vendite gia' registrata in
# error_policies.py — vedi contratti_service.E_VENDITE_*).
E_VENDITE_NOT_FOUND = "E_VENDITE_NOT_FOUND"
E_VENDITE_VALIDATION = "E_VENDITE_VALIDATION"

# Parameter codes consumati. Single source of truth lato seed DB
# (handoff Fase 2 `2026-04-30`). Mantenere allineati ai default
# usati anche dal FE come fallback in `paramInt`/`paramString`.
_PARAM_CONTRATTO_VALIDO_DAL_LEAD_GG = "VENDITE_CONTRATTO_DEFAULT_VALIDO_DAL_LEAD_GG"
_PARAM_CONTRATTO_DATA_LEAD_GG = "VENDITE_CONTRATTO_DEFAULT_DATA_LEAD_GG"
_PARAM_PREVENTIVO_VALIDITA_GG = "VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG"
_PARAM_LISTINI_NEW_VERSIONE_LEAD_GG = "VENDITE_LISTINI_NEW_VERSIONE_LEAD_GG"
_PARAM_LISTINI_CLONE_VERSIONE_LEAD_GG = "VENDITE_LISTINI_CLONE_VERSIONE_LEAD_GG"
_PARAM_LISTINI_CLONE_VERSIONE_CODICE_SUFFIX = "VENDITE_LISTINI_CLONE_VERSIONE_CODICE_SUFFIX"
_PARAM_LISTINI_CLOSE_VERSIONE_LEAD_GG = "VENDITE_LISTINI_CLOSE_VERSIONE_LEAD_GG"


# ══════════════════════════════════════════════════════════
#  Helpers privati
# ══════════════════════════════════════════════════════════


# Scopo: Cast int safe con default. ParameterService.get_defaults restituisce
#        dict[str, str]: il caller decide il fallback se il parameter non e'
#        seedato o ha valore non numerico (resilienza a config DB incompleto).
def _param_int(defaults: dict[str, str], code: str, fallback: int) -> int:
    raw = defaults.get(code)
    if raw is None:
        return fallback
    try:
        return int(raw)
    except (ValueError, TypeError):
        return fallback


# Scopo: Cast string safe con default.
def _param_str(defaults: dict[str, str], code: str, fallback: str) -> str:
    raw = defaults.get(code)
    if raw is None or raw == "":
        return fallback
    return str(raw)


# Scopo: Verifica che billing_account_id sia un intero positivo.
def _require_positive_int(value: Any, *, field: str, function_name: str) -> int:
    ErrorManager.require(
        value is not None,
        code=E_VENDITE_VALIDATION,
        message=f"Parametro '{field}' obbligatorio.",
        function_name=function_name,
    )
    try:
        as_int = int(value)
    except (ValueError, TypeError):
        ErrorManager.raise_error(
            code=E_VENDITE_VALIDATION,
            message=f"Parametro '{field}' deve essere un intero positivo.",
            detail=f"Valore ricevuto: {value!r}",
            function_name=function_name,
        )
    ErrorManager.require(
        as_int > 0,
        code=E_VENDITE_VALIDATION,
        message=f"Parametro '{field}' deve essere un intero positivo.",
        function_name=function_name,
    )
    return as_int


# ══════════════════════════════════════════════════════════
#  2.B3 — Contratti form-defaults
# ══════════════════════════════════════════════════════════


# Scopo: Defaults per il form contratto contestuali al BA selezionato.
#        Il drawer ContrattoDrawer chiama questo endpoint nel `@select` del
#        BillingAccountLookup per pre-compilare campi che oggi inferisce dal
#        payload del lookup (categoria_cliente_id_snapshot) o lascia vuoti
#        (utility/istanza per coerenza).
#
#        Restituisce sempre `param_defaults` (lead_gg per data e valido_dal):
#        il FE li usa anche all'apertura senza BA. Quando billing_account_id
#        e' presente, aggiunge i campi BA-derived (categoria_cliente_id_snapshot,
#        utility_id, istanza_utility_id).


# Scopo: Estrae i campi BA-derived comuni a contratti/offerte
#        (categoria_cliente_*, utility_*, istanza_utility_*) dal lookup BA
#        e li applica al payload. Helper privato: contratti e offerte
#        condividono lo stesso pattern testata+eccezioni senza
#        termini/iva/modalita_pagamento (quelli sono solo nelle eccezioni).
#        Mantiene `ba_id` esplicito perché il caller può aver già fatto
#        `_require_positive_int`.
def _apply_ba_categoria_utility(
    payload: dict[str, Any], ba: dict[str, Any], ba_id: int,
) -> None:
    payload.update({
        "billing_account_id": ba_id,
        "categoria_cliente_id_snapshot": ba.get("categoria_cliente_id"),
        "categoria_cliente_codice": ba.get("categoria_cliente_codice"),
        "categoria_cliente_descrizione": ba.get("categoria_cliente_descrizione"),
        "utility_id": ba.get("utility_id"),
        "istanza_utility_id": ba.get("istanza_utility_id"),
        "utility_codice": ba.get("utility_codice"),
        "utility_descrizione": ba.get("utility_descrizione"),
    })


# Scopo: la scheda di fornitura che l'anagrafica da' al cliente scelto
#        (R-BE-5 di brief-db-indirizzi-documento-seguono-il-cliente): il drawer
#        di contratto e offerta la precompila in creazione, l'operatore la vede
#        e la corregge (condizione di Tid su D-7). Alla nascita del contratto il
#        DB parte dalla stessa scheda e ci applica le chiavi dell'operatore.
#        `fornitura` None: niente BA, o la coppia senza dati precontrattuali.
def _apply_fornitura(payload: dict[str, Any]) -> None:
    istanza_id = payload.get("istanza_utility_id")
    utility_id = payload.get("utility_id")
    payload["fornitura"] = (
        fornitura_da_anagrafica(int(istanza_id), int(utility_id))
        if istanza_id is not None and utility_id is not None
        else None
    )


def fn_get_contratto_form_defaults(
    *,
    billing_account_id: int | None,
    auth_user_id: int | None = None,
) -> dict[str, Any]:
    function_name = f"{_FN}.fn_get_contratto_form_defaults"
    param_defaults_raw = ParameterService().get_defaults(
        [
            _PARAM_CONTRATTO_VALIDO_DAL_LEAD_GG,
            _PARAM_CONTRATTO_DATA_LEAD_GG,
        ],
        django_user_id=auth_user_id,
    )
    today = oggi_aziendale()
    valido_dal_lead = _param_int(param_defaults_raw, _PARAM_CONTRATTO_VALIDO_DAL_LEAD_GG, 0)
    data_lead = _param_int(param_defaults_raw, _PARAM_CONTRATTO_DATA_LEAD_GG, 0)
    payload: dict[str, Any] = {
        "billing_account_id": None,
        "default_valido_dal": (today + timedelta(days=valido_dal_lead)).isoformat(),
        "default_data": (today + timedelta(days=data_lead)).isoformat(),
        "categoria_cliente_id_snapshot": None,
        "categoria_cliente_codice": None,
        "categoria_cliente_descrizione": None,
        "utility_id": None,
        "istanza_utility_id": None,
        "utility_codice": None,
        "utility_descrizione": None,
        # Valuta risolta via BB `resolve_valuta_default` (catena
        # BA → EF del BA → EF utente → gestore, allineata a
        # `vendite.fn_get_valuta_id` 2026-05-29).
        "valuta_id": None,
        "valuta_codice": None,
        "valuta_descrizione": None,
        "fornitura": None,
    }

    ba: dict[str, Any] | None = None
    ba_id: int | None = None
    if billing_account_id is not None:
        ba_id = _require_positive_int(
            billing_account_id, field="billing_account_id", function_name=function_name,
        )
        ba = BillingAccountRepository().get_lookup_by_id(ba_id)
        ErrorManager.require(
            ba is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Billing account non trovato.",
            detail=f"billing_account_id={ba_id}",
            function_name=function_name,
        )
        assert ba is not None
        _apply_ba_categoria_utility(payload, ba, ba_id)
        _apply_fornitura(payload)

    valuta = resolve_valuta_default(
        billing_account_id=ba_id,
        ba_obj=ba,
        auth_user_id=auth_user_id,
    )
    if valuta:
        payload.update(valuta)
    return payload


# ══════════════════════════════════════════════════════════
#  Offerte form-defaults
# ══════════════════════════════════════════════════════════


# Scopo: Defaults per il form offerta commerciale contestuali al BA.
#        Stesso pattern di `fn_get_contratto_form_defaults` (offerte e
#        contratti condividono il modello "testata + eccezioni" senza
#        termini/iva sul testata): valuta via BB centralizzato + campi
#        BA-derived (utility, categoria_cliente).
def fn_get_offerta_form_defaults(
    *,
    billing_account_id: int | None,
    auth_user_id: int | None = None,
) -> dict[str, Any]:
    function_name = f"{_FN}.fn_get_offerta_form_defaults"
    payload: dict[str, Any] = {
        "billing_account_id": None,
        "categoria_cliente_id_snapshot": None,
        "categoria_cliente_codice": None,
        "categoria_cliente_descrizione": None,
        "utility_id": None,
        "istanza_utility_id": None,
        "utility_codice": None,
        "utility_descrizione": None,
        "valuta_id": None,
        "valuta_codice": None,
        "valuta_descrizione": None,
        "fornitura": None,
    }

    ba: dict[str, Any] | None = None
    ba_id: int | None = None
    if billing_account_id is not None:
        ba_id = _require_positive_int(
            billing_account_id, field="billing_account_id", function_name=function_name,
        )
        ba = BillingAccountRepository().get_lookup_by_id(ba_id)
        ErrorManager.require(
            ba is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Billing account non trovato.",
            detail=f"billing_account_id={ba_id}",
            function_name=function_name,
        )
        assert ba is not None
        _apply_ba_categoria_utility(payload, ba, ba_id)
        _apply_fornitura(payload)

    valuta = resolve_valuta_default(
        billing_account_id=ba_id,
        ba_obj=ba,
        auth_user_id=auth_user_id,
    )
    if valuta:
        payload.update(valuta)
    return payload


# ══════════════════════════════════════════════════════════
#  Ordini form-defaults
# ══════════════════════════════════════════════════════════


# Scopo: Defaults per il form ordine di vendita. Allinea ordini alla famiglia
#        (preventivi/offerte/contratti propongono i default all'apertura del
#        drawer): senza BA ritorna la `valuta_id` dalla catena EF utente →
#        gestore globale (BB centralizzato `resolve_valuta_default`); con BA
#        aggiunge i campi BA-derived (utility, categoria). La utility di default
#        "globale" (parameter DEFAULT_UTILITY) la risolve il FE via
#        useUtilityDefaultId, come negli altri drawer: qui la utility arriva
#        solo dal BA quando selezionato.
def fn_get_ordine_form_defaults(
    *,
    billing_account_id: int | None,
    auth_user_id: int | None = None,
) -> dict[str, Any]:
    function_name = f"{_FN}.fn_get_ordine_form_defaults"
    payload: dict[str, Any] = {
        "billing_account_id": None,
        "utility_id": None,
        "istanza_utility_id": None,
        "utility_codice": None,
        "utility_descrizione": None,
        "valuta_id": None,
        "valuta_codice": None,
        "valuta_descrizione": None,
        "termine_pagamento_id": None,
        "termine_pagamento_codice": None,
        "termine_pagamento_descrizione": None,
        "modalita_pagamento_id": None,
        "modalita_pagamento_codice": None,
        "modalita_pagamento_descrizione": None,
    }

    ba: dict[str, Any] | None = None
    ba_id: int | None = None
    if billing_account_id is not None:
        ba_id = _require_positive_int(
            billing_account_id, field="billing_account_id", function_name=function_name,
        )
        ba_repo = BillingAccountRepository()
        ba = ba_repo.get_lookup_by_id(ba_id)
        ErrorManager.require(
            ba is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Billing account non trovato.",
            detail=f"billing_account_id={ba_id}",
            function_name=function_name,
        )
        assert ba is not None
        payload.update({
            "billing_account_id": ba_id,
            "utility_id": ba.get("utility_id"),
            "istanza_utility_id": ba.get("istanza_utility_id"),
            "utility_codice": ba.get("utility_codice"),
            "utility_descrizione": ba.get("utility_descrizione"),
        })
        # Default pagamento dall'anagrafica cliente del BA (relazione 1:1 via
        # tripletta istanza+soggetto_ruolo+utility) — stesso BB dei preventivi.
        # L'ordine NON ha IVA in testata: prendiamo solo termine + modalita.
        if (ba.get("istanza_utility_id") is not None
                and ba.get("soggetto_ruolo_id") is not None
                and ba.get("utility_id") is not None):
            cliente = ba_repo.get_cliente_defaults(
                istanza_utility_id=int(ba["istanza_utility_id"]),
                soggetto_ruolo_id=int(ba["soggetto_ruolo_id"]),
                utility_id=int(ba["utility_id"]),
            )
            if cliente:
                payload.update({
                    "termine_pagamento_id": cliente.get("termine_pagamento_id"),
                    "termine_pagamento_codice": cliente.get("termine_pagamento_codice"),
                    "termine_pagamento_descrizione": cliente.get("termine_pagamento_descrizione"),
                    "modalita_pagamento_id": cliente.get("modalita_pagamento_id"),
                    "modalita_pagamento_codice": cliente.get("modalita_pagamento_codice"),
                    "modalita_pagamento_descrizione": cliente.get("modalita_pagamento_descrizione"),
                })

    valuta = resolve_valuta_default(
        billing_account_id=ba_id,
        ba_obj=ba,
        auth_user_id=auth_user_id,
    )
    if valuta:
        payload.update(valuta)
    return payload


# ══════════════════════════════════════════════════════════
#  DDT form-defaults
# ══════════════════════════════════════════════════════════


# Scopo: Defaults per il form DDT di vendita. Allinea il DDT alla famiglia
#        (ordini/preventivi/offerte propongono i default all'apertura del
#        drawer): senza BA ritorna la `valuta_id` dalla catena EF utente →
#        gestore globale (BB centralizzato `resolve_valuta_default`); con BA
#        aggiunge i campi utility BA-derived + la valuta del cliente. Il DDT è
#        un documento di trasporto: NON ha termini/modalita di pagamento in
#        testata, quindi il payload si limita a utility + valuta (calco ridotto
#        di fn_get_ordine_form_defaults). La utility di default "globale"
#        (parameter DEFAULT_UTILITY) la risolve il FE via useUtilityDefaultId.
def fn_get_ddt_form_defaults(
    *,
    billing_account_id: int | None,
    auth_user_id: int | None = None,
) -> dict[str, Any]:
    function_name = f"{_FN}.fn_get_ddt_form_defaults"
    payload: dict[str, Any] = {
        "billing_account_id": None,
        "utility_id": None,
        "istanza_utility_id": None,
        "utility_codice": None,
        "utility_descrizione": None,
        "valuta_id": None,
        "valuta_codice": None,
        "valuta_descrizione": None,
    }

    ba: dict[str, Any] | None = None
    ba_id: int | None = None
    if billing_account_id is not None:
        ba_id = _require_positive_int(
            billing_account_id, field="billing_account_id", function_name=function_name,
        )
        ba = BillingAccountRepository().get_lookup_by_id(ba_id)
        ErrorManager.require(
            ba is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Billing account non trovato.",
            detail=f"billing_account_id={ba_id}",
            function_name=function_name,
        )
        assert ba is not None
        payload.update({
            "billing_account_id": ba_id,
            "utility_id": ba.get("utility_id"),
            "istanza_utility_id": ba.get("istanza_utility_id"),
            "utility_codice": ba.get("utility_codice"),
            "utility_descrizione": ba.get("utility_descrizione"),
        })

    valuta = resolve_valuta_default(
        billing_account_id=ba_id,
        ba_obj=ba,
        auth_user_id=auth_user_id,
    )
    if valuta:
        payload.update(valuta)
    return payload


# ══════════════════════════════════════════════════════════
#  2.B4 — Preventivi form-defaults
# ══════════════════════════════════════════════════════════


# Scopo: Defaults per il form preventivo contestuali al BA selezionato.
#        Risolve termine_pagamento_id/modalita_pagamento_id dal cliente
#        associato al BA (tripletta istanza+soggetto+utility) e valuta_id
#        tramite il BB centralizzato `resolve_valuta_default` (catena
#        BA → EF-del-BA → EF-utente).
#
#        Sempre presente `param_defaults` (validita_gg) per il calcolo
#        validita_al = oggi + N. Quando billing_account_id e' assente, i
#        campi BA-derived restano None ma valuta_id viene comunque
#        risolta dall'EF dell'utente loggato (fallback gestore globale per
#        admin globale).
def fn_get_preventivo_form_defaults(
    *,
    billing_account_id: int | None,
    auth_user_id: int | None = None,
) -> dict[str, Any]:
    function_name = f"{_FN}.fn_get_preventivo_form_defaults"
    param_defaults_raw = ParameterService().get_defaults(
        [_PARAM_PREVENTIVO_VALIDITA_GG],
        django_user_id=auth_user_id,
    )
    today = oggi_aziendale()
    validita_gg = _param_int(param_defaults_raw, _PARAM_PREVENTIVO_VALIDITA_GG, 30)
    payload: dict[str, Any] = {
        "billing_account_id": None,
        "default_validita_al": (today + timedelta(days=validita_gg)).isoformat(),
        "valuta_id": None,
        "valuta_codice": None,
        "valuta_descrizione": None,
        "termine_pagamento_id": None,
        "termine_pagamento_codice": None,
        "termine_pagamento_descrizione": None,
        # ⛔ `iva_id`/`iva_codice`/`iva_descrizione` tolte il 2026-08-29
        #    (I0/D7-bis, decisione Q3 del piano BE/FE): venivano da
        #    `anagrafiche.clienti.iva_id`, colonna che non esiste piu'. Nessun
        #    consumatore le leggeva — `vendite.preventivi` una colonna IVA di
        #    testata non ce l'ha, e l'IVA di riga la produrra' il risolutore (I2).
        "modalita_pagamento_id": None,
        "modalita_pagamento_codice": None,
        "modalita_pagamento_descrizione": None,
        "utility_id": None,
        "istanza_utility_id": None,
        "utility_codice": None,
        "utility_descrizione": None,
    }

    # Pre-fetch BA (un solo round-trip riutilizzato dal resolver e dai default
    # BA-specific sotto). Errore parlante se id non valido.
    ba: dict[str, Any] | None = None
    ba_id: int | None = None
    if billing_account_id is not None:
        ba_id = _require_positive_int(
            billing_account_id, field="billing_account_id", function_name=function_name,
        )
        ba_repo = BillingAccountRepository()
        ba = ba_repo.get_lookup_by_id(ba_id)
        ErrorManager.require(
            ba is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Billing account non trovato.",
            detail=f"billing_account_id={ba_id}",
            function_name=function_name,
        )
        assert ba is not None

    # Risoluzione valuta con catena standard (BB cross-dominio):
    # 1) ba.valuta_id  2) EF-del-BA  3) EF-utente (fallback gestore globale).
    valuta = resolve_valuta_default(
        billing_account_id=ba_id,
        ba_obj=ba,
        auth_user_id=auth_user_id,
    )
    if valuta:
        payload.update(valuta)

    if ba is None:
        return payload

    # BA-specific: utility/istanza + cliente (termini/modalita).
    assert ba_id is not None
    payload.update({
        "billing_account_id": ba_id,
        "utility_id": ba.get("utility_id"),
        "istanza_utility_id": ba.get("istanza_utility_id"),
        "utility_codice": ba.get("utility_codice"),
        "utility_descrizione": ba.get("utility_descrizione"),
    })

    # Cliente del BA (relazione 1:1 via tripletta) -> termini/modalita.
    ba_repo = BillingAccountRepository()
    cliente = ba_repo.get_cliente_defaults(
        istanza_utility_id=int(ba["istanza_utility_id"]),
        soggetto_ruolo_id=int(ba["soggetto_ruolo_id"]),
        utility_id=int(ba["utility_id"]),
    )
    if cliente:
        payload.update({
            "termine_pagamento_id": cliente.get("termine_pagamento_id"),
            "termine_pagamento_codice": cliente.get("termine_pagamento_codice"),
            "termine_pagamento_descrizione": cliente.get("termine_pagamento_descrizione"),
            "modalita_pagamento_id": cliente.get("modalita_pagamento_id"),
            "modalita_pagamento_codice": cliente.get("modalita_pagamento_codice"),
            "modalita_pagamento_descrizione": cliente.get("modalita_pagamento_descrizione"),
        })

    return payload


# ══════════════════════════════════════════════════════════
#  2.B5a — Listini-versioni: defaults per nuova versione
# ══════════════════════════════════════════════════════════


# Scopo: Defaults per la creazione di una nuova versione del listino.
#        Restituisce default_valido_dal (oggi + lead_gg da parameter) e la
#        lista delle BOZZE gia' esistenti per il listino: il FE le usa per
#        warning UX ("attenzione, esistono gia' bozze: codici X, Y").
#        Nessun min_valido_dal: la BOZZA ammette retroattivita'; il vincolo
#        di non-overlap e' gestito dal DB su attivazione.
def fn_get_versione_new_defaults(*, listino_id: int, auth_user_id: int | None = None) -> dict[str, Any]:
    function_name = f"{_FN}.fn_get_versione_new_defaults"
    listino_id_int = _require_positive_int(
        listino_id, field="listino_id", function_name=function_name,
    )
    listini_repo = ListiniRepository()
    listino = listini_repo.get_listino(listino_id_int)
    ErrorManager.require(
        listino is not None,
        code=E_VENDITE_NOT_FOUND,
        message="Listino non trovato.",
        detail=f"listino_id={listino_id_int}",
        function_name=function_name,
    )
    param_defaults_raw = ParameterService().get_defaults(
        [_PARAM_LISTINI_NEW_VERSIONE_LEAD_GG],
        django_user_id=auth_user_id,
    )
    lead_gg = _param_int(param_defaults_raw, _PARAM_LISTINI_NEW_VERSIONE_LEAD_GG, 0)
    versioni = listini_repo.list_versioni(listino_id_int)
    bozze = [
        {"id": v["id"], "codice_versione": v.get("codice_versione")}
        for v in versioni
        if v.get("stato") == "BOZZA"
    ]
    return {
        "listino_id": listino_id_int,
        "default_codice_versione": "",
        "default_valido_dal": (oggi_aziendale() + timedelta(days=lead_gg)).isoformat(),
        "default_valido_al": None,
        "min_valido_dal": None,
        "has_existing_draft": len(bozze) > 0,
        "existing_drafts": bozze,
    }


# ══════════════════════════════════════════════════════════
#  2.B5b — Listini-versioni: defaults per clone
# ══════════════════════════════════════════════════════════


# Scopo: Defaults per il clone di una versione esistente. Risolve il
#        codice di partenza dalla sorgente, applica il suffisso configurato
#        (parameter VENDITE_LISTINI_CLONE_VERSIONE_CODICE_SUFFIX, default
#        "-clone") e calcola valido_dal default = oggi + lead_gg.
#        ⛔ Niente `min_valido_dal` dal 2026-10-29 (BE-C3 di
#        brief-modello-documento-vendita §16.16): era una copia di D2 («la copia
#        non comincia prima della sorgente»), che dice il verbo del DB
#        (`vendite.fn_clona_versione_listino`) sul campo `valido_dal`.
def fn_get_versione_clone_defaults(
    *,
    listino_id: int,
    src_versione_id: int,
    auth_user_id: int | None = None,
) -> dict[str, Any]:
    function_name = f"{_FN}.fn_get_versione_clone_defaults"
    listino_id_int = _require_positive_int(
        listino_id, field="listino_id", function_name=function_name,
    )
    src_id = _require_positive_int(
        src_versione_id, field="src_versione_id", function_name=function_name,
    )
    src = ListiniRepository().get_versione(listino_id_int, src_id)
    ErrorManager.require(
        src is not None,
        code=E_VENDITE_NOT_FOUND,
        message="Versione sorgente non trovata.",
        detail=f"listino_id={listino_id_int}, versione_id={src_id}",
        function_name=function_name,
    )
    assert src is not None
    param_defaults_raw = ParameterService().get_defaults(
        [
            _PARAM_LISTINI_CLONE_VERSIONE_LEAD_GG,
            _PARAM_LISTINI_CLONE_VERSIONE_CODICE_SUFFIX,
        ],
        django_user_id=auth_user_id,
    )
    lead_gg = _param_int(param_defaults_raw, _PARAM_LISTINI_CLONE_VERSIONE_LEAD_GG, 1)
    suffix = _param_str(param_defaults_raw, _PARAM_LISTINI_CLONE_VERSIONE_CODICE_SUFFIX, "-clone")
    today = oggi_aziendale()
    default_valido_dal = today + timedelta(days=lead_gg)
    src_valido_dal = src.get("valido_dal")
    src_codice = src.get("codice_versione") or ""
    return {
        "listino_id": listino_id_int,
        "source_versione_id": src_id,
        "source_codice_versione": src_codice,
        "source_valido_dal": src_valido_dal.isoformat() if isinstance(src_valido_dal, date) else src_valido_dal,
        "source_valido_al": src["valido_al"].isoformat() if isinstance(src.get("valido_al"), date) else src.get("valido_al"),
        "default_codice_versione": f"{src_codice}{suffix}" if src_codice else "",
        "default_valido_dal": default_valido_dal.isoformat(),
        "default_valido_al": None,
        # Retroattivo se il default proposto cade nel passato: un avviso, non
        # un vincolo (la decorrenza passata e' ammessa, D2).
        "is_retroactive_default": default_valido_dal < today,
        "retroactive_warning_key": "listini.warning_retroattivo",
    }


# ══════════════════════════════════════════════════════════
#  2.B5c — Listini-versioni: defaults per chiusura
# ══════════════════════════════════════════════════════════


# Scopo: Defaults per la chiusura programmata/immediata di una versione.
#        Se la versione ha gia' una valido_al (chiusura programmata),
#        il default e' quello esistente (UX di "modifica chiusura"), se non e'
#        gia' passato; altrimenti oggi + lead_gg. Espone `current_valido_al` per il flag UX
#        "ha_gia_chiusura".
#        ⛔ Niente `min_valido_al` dal 2026-10-29: era una copia di C-2 («la fine
#        di una ATTIVA non sta nel passato»), che dice il verbo «Chiudi»
#        (`vendite.fn_programma_chiusura_versione_listino`) sul campo
#        `valido_al` (brief-modello-documento-vendita §16.16).
def fn_get_versione_close_defaults(
    *,
    listino_id: int,
    versione_id: int,
    auth_user_id: int | None = None,
) -> dict[str, Any]:
    function_name = f"{_FN}.fn_get_versione_close_defaults"
    listino_id_int = _require_positive_int(
        listino_id, field="listino_id", function_name=function_name,
    )
    ver_id = _require_positive_int(
        versione_id, field="versione_id", function_name=function_name,
    )
    versione = ListiniRepository().get_versione(listino_id_int, ver_id)
    ErrorManager.require(
        versione is not None,
        code=E_VENDITE_NOT_FOUND,
        message="Versione listino non trovata.",
        detail=f"listino_id={listino_id_int}, versione_id={ver_id}",
        function_name=function_name,
    )
    assert versione is not None
    param_defaults_raw = ParameterService().get_defaults(
        [_PARAM_LISTINI_CLOSE_VERSIONE_LEAD_GG],
        django_user_id=auth_user_id,
    )
    lead_gg = _param_int(param_defaults_raw, _PARAM_LISTINI_CLOSE_VERSIONE_LEAD_GG, 0)
    today = oggi_aziendale()
    current_valido_al = versione.get("valido_al")
    # ⚠️ Una fine gia' passata (la versione resta ATTIVA fino al job) non si
    #    ripropone: «Conferma» la manderebbe al verbo, che la rifiuta (C-2), e
    #    il pulsante sembrerebbe rotto. Si propone la fine nuova di default. Non
    #    e' un limite del campo: il rifiuto resta del verbo.
    if isinstance(current_valido_al, date) and current_valido_al >= today:
        default_valido_al = current_valido_al
    else:
        default_valido_al = today + timedelta(days=lead_gg)
    return {
        "listino_id": listino_id_int,
        "versione_id": ver_id,
        "stato_codice": versione.get("stato"),
        "current_valido_al": current_valido_al.isoformat() if isinstance(current_valido_al, date) else current_valido_al,
        "has_existing_chiusura": current_valido_al is not None,
        "default_valido_al": default_valido_al.isoformat() if isinstance(default_valido_al, date) else default_valido_al,
    }
