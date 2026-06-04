# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade applicativa per ordini di vendita (CRUD, stato, righe, push).
# ------------------------------------------------------------

# Orchestrazione ordini di vendita: validazione, guard su stato, delega al
# repository, pricing via building block condivisi (PricingService — regola del
# 2, mai query dirette su listini), componenti BoM via fn DB
# `fn_ordine_riga_componenti_*`, push singolo a commessa.
#
# Scheletro (analisi-ordini-vendita.md §5): niente revisioni (gli ordini non le
# hanno). Il gate prezzi L2/L3 stile contratti e' una DECISIONE DI DOMINIO ANCORA
# APERTA (analisi §8.bis): qui si usa il pricing stile preventivo (resolve +
# prezzo passato dal caller), passando comunque dai BB condivisi.

import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from typing import Any

from django.db import DatabaseError, IntegrityError, transaction

from apps.core.api.payload_validators import paginated_envelope
from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import map_integrity_error
from apps.core.services.value_normalizer import empty_to_none
from apps.vendite.db.ordini_repository import OrdiniRepository

logger = logging.getLogger(__name__)

# Codici errore vendite (registrati in error_policies.py) usati come fallback
# nella traduzione errori DB. I codici trigger E_ORDINE_* sono estratti via regex.
E_VENDITE_VALIDATION = "E_VENDITE_VALIDATION"
E_VENDITE_DUPLICATO = "E_VENDITE_DUPLICATO"
E_VENDITE_FK = "E_VENDITE_FK"
_DB_ERROR_CODE_RE = re.compile(r"\b(E_[A-Z][A-Z0-9_]+)\b")

# Mappe vincolo DB -> (codice, messaggio) per map_integrity_error (frammento
# nome vincolo). Minime: i casi non mappati cadono su E_VENDITE_VALIDATION.
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "uq_ordrig_riga_nr": (E_VENDITE_DUPLICATO, "Numero riga duplicato sull'ordine."),
    "uq_ordini_v_anno_serie_numero": (E_VENDITE_DUPLICATO, "Numero ordine duplicato."),
}
_FK_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "fk_ordrig_articolo": (E_VENDITE_FK, "Articolo non valido."),
    "fk_ordini_v_billing_account": (E_VENDITE_FK, "Cliente (billing account) non valido."),
    "fk_ordini_v_cliente_ruolo": (E_VENDITE_FK, "Cliente non valido."),
}

# ── Costanti di dominio ──
_FN = "vendite.ordini_service"
_STATO_BOZZA = "DRAFT"
_STATO_CONFERMATO = "CONFERMATO"
_STATI_MODIFICABILI: frozenset[str] = frozenset({"DRAFT"})
_STATI_RIGHE_MODIFICABILI: frozenset[str] = frozenset({"DRAFT"})
_STATI_PUSHABILI: frozenset[str] = frozenset({"CONFERMATO"})

# Whitelist campi testata accettati in create/update (null_vs_empty → None).
_CREATE_KEYS_ORDINE: frozenset[str] = frozenset({
    "billing_account_id", "soggetto_ruolo_id", "utility_id",
    "emittente_fiscale_id", "valuta_id", "modalita_pagamento_id",
    "termine_pagamento_id", "fatturazione_trigger", "agente_soggetto_ruolo_id",
    "data", "meta",
})
# NB: billing_account_id NON e' aggiornabile (cliente immutabile post-creazione,
# vedi aggiorna_ordine): a differenza di create, dove deriva soggetto_ruolo_id.
_UPDATE_KEYS_ORDINE: frozenset[str] = frozenset({
    "utility_id", "valuta_id", "modalita_pagamento_id",
    "termine_pagamento_id", "fatturazione_trigger", "agente_soggetto_ruolo_id",
    "data", "meta",
})
_CREATE_KEYS_RIGA: frozenset[str] = frozenset({
    "articolo_id", "descrizione", "quantita", "qta_operativa",
    "uom_operativa_id", "factor_to_base", "prezzo_unitario", "sconto_perc",
    "iva_id", "meta",
})
_UPDATE_KEYS_RIGA: frozenset[str] = frozenset({
    "descrizione", "quantita", "qta_operativa", "uom_operativa_id",
    "factor_to_base", "prezzo_unitario", "sconto_perc", "iva_id", "meta",
})


# ══════════════════════════════════════════════════════════
#  LETTURE — Lista (envelope + rows per export)
# ══════════════════════════════════════════════════════════

# Scopo: Letture grezze (righe + totale) della lista ordini. Condivisa tra
#        lista paginata (envelope) ed export (DEF-1) — regola del 2.
def list_ordini_rows(
    *,
    stato_codice: str | None = None,
    billing_account_id: int | None = None,
    utility_id: int | None = None,
    data_da: date | None = None,
    data_al: date | None = None,
    search: str | None = None,
    auth_user_id: int | None = None,
    limit: int,
    offset: int,
    order_by: str = "data",
    order_dir: str = "desc",
) -> tuple[list[Any], int]:
    repo = OrdiniRepository()
    return repo.list_ordini(
        stato_codice=stato_codice,
        billing_account_id=billing_account_id,
        utility_id=utility_id,
        data_da=data_da,
        data_al=data_al,
        search=search,
        auth_user_id=auth_user_id,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_dir=order_dir,
    )


# Scopo: Lista ordini paginata (envelope standard).
def list_ordini(
    *,
    stato_codice: str | None = None,
    billing_account_id: int | None = None,
    utility_id: int | None = None,
    data_da: date | None = None,
    data_al: date | None = None,
    search: str | None = None,
    auth_user_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
    order_by: str = "data",
    order_dir: str = "desc",
) -> dict[str, object]:
    safe_page = max(1, int(page))
    safe_size = max(1, min(int(page_size), 200))
    offset = (safe_page - 1) * safe_size
    rows, total = list_ordini_rows(
        stato_codice=stato_codice,
        billing_account_id=billing_account_id,
        utility_id=utility_id,
        data_da=data_da,
        data_al=data_al,
        search=search,
        auth_user_id=auth_user_id,
        limit=safe_size,
        offset=offset,
        order_by=order_by,
        order_dir=order_dir,
    )
    return paginated_envelope(rows, total, page=safe_page, page_size=safe_size)


# Scopo: Etichette leggibili dei filtri applicati per il metadato del file
#        export (DEF-1). Gemello resolve_filtri_export_label preventivi.
def resolve_filtri_export_label(
    *,
    search: str | None = None,
    stato_codice: str | None = None,
    billing_account_id: int | None = None,
    utility_id: int | None = None,
    data_da: date | None = None,
    data_al: date | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if search:
        out["Ricerca"] = search
    if stato_codice:
        out["Stato"] = stato_codice
    if billing_account_id is not None:
        out["Cliente BA (id)"] = billing_account_id
    if utility_id is not None:
        out["Utility (id)"] = utility_id
    if data_da is not None:
        out["Dal"] = str(data_da)
    if data_al is not None:
        out["Al"] = str(data_al)
    return out


# Scopo: Dettaglio testata ordine (righe lette a parte via /righe/).
def get_ordine(ordine_id: int) -> dict[str, object]:
    repo = OrdiniRepository()
    testata = repo.get_ordine(ordine_id)
    ErrorManager.require(
        testata is not None,
        code="E_ORD_NOT_FOUND",
        message="Ordine non trovato.",
        detail=f"ordine_id={ordine_id}",
        function_name=f"{_FN}.get_ordine",
    )
    assert testata is not None
    stato = testata.get("stato_codice_interno")
    righe = repo.list_righe(ordine_id)
    # Capability minime data-driven (niente fn_available_actions_ordine):
    # modifica solo in DRAFT, push solo da CONFERMATO con righe eleggibili.
    can_push = stato in _STATI_PUSHABILI and repo.count_righe_pushable(ordine_id) > 0
    return {
        **testata,
        "righe_count": len(righe),
        "can_edit_testata": stato in _STATI_MODIFICABILI,
        "can_edit_righe": stato in _STATI_RIGHE_MODIFICABILI,
        "can_conferma": stato == _STATO_BOZZA and len(righe) > 0,
        "can_push_commessa": can_push,
    }


# Scopo: Lista righe di un ordine.
def list_righe(ordine_id: int) -> list[dict[str, Any]]:
    return OrdiniRepository().list_righe(ordine_id)


# ══════════════════════════════════════════════════════════
#  SCRITTURE — Testata
# ══════════════════════════════════════════════════════════

# Scopo: Crea un nuovo ordine in stato DRAFT (BOZZA). `numero` generato dal
#        trigger DB. soggetto_ruolo_id derivato dal billing_account se assente.
def crea_ordine(payload: dict[str, Any]) -> dict[str, Any]:
    repo = OrdiniRepository()
    data = {k: empty_to_none(v) for k, v in payload.items() if k in _CREATE_KEYS_ORDINE}

    billing_account_id = data.get("billing_account_id")
    soggetto_ruolo_id = data.get("soggetto_ruolo_id")
    if soggetto_ruolo_id is None and billing_account_id is not None:
        soggetto_ruolo_id = repo.get_soggetto_ruolo_id_by_ba(int(billing_account_id))
    ErrorManager.require(
        soggetto_ruolo_id is not None,
        code="E_ORD_VALIDAZIONE",
        message="Cliente obbligatorio (billing_account_id o soggetto_ruolo_id).",
        function_name=f"{_FN}.crea_ordine",
    )
    assert soggetto_ruolo_id is not None

    stato_bozza_id = repo.get_stato_id_by_codice(_STATO_BOZZA)
    ErrorManager.require(
        stato_bozza_id is not None,
        code="E_ORD_VALIDAZIONE",
        message="Stato DRAFT non configurato in config.stati_doc_ordini.",
        function_name=f"{_FN}.crea_ordine",
    )
    assert stato_bozza_id is not None

    with _db_errors("crea_ordine"):
        return repo.create_ordine(
            soggetto_ruolo_id=int(soggetto_ruolo_id),
            billing_account_id=int(billing_account_id) if billing_account_id is not None else None,
            utility_id=data.get("utility_id"),
            emittente_fiscale_id=data.get("emittente_fiscale_id"),
            valuta_id=data.get("valuta_id"),
            modalita_pagamento_id=data.get("modalita_pagamento_id"),
            termine_pagamento_id=data.get("termine_pagamento_id"),
            fatturazione_trigger=data.get("fatturazione_trigger"),
            agente_soggetto_ruolo_id=data.get("agente_soggetto_ruolo_id"),
            data=data.get("data"),
            stato_doc_ordine_id=int(stato_bozza_id),
            meta=data.get("meta") if isinstance(data.get("meta"), dict) else None,
        )


# Scopo: Aggiorna testata ordine (solo in DRAFT).
#
# Cliente immutabile post-creazione: billing_account_id NON e' nella whitelist
# _UPDATE_KEYS_ORDINE. vendite.ordini denormalizza soggetto_ruolo_id (NOT NULL)
# accanto a billing_account_id, ma nessun trigger DB li ri-sincronizza su UPDATE
# (trgfn_ordini_normalize tocca solo fatturazione_trigger): cambiare il BA
# lascerebbe soggetto_ruolo_id stantio -> incoerenza cliente<->soggetto. Regola
# "cambiare cliente = nuovo ordine" (come utility immutabile in preventivi).
# Un tentativo ESPLICITO di cambiare BA e' rifiutato (non ignorato in silenzio);
# un BA invariato nel payload e' tollerato (il form FE puo' reinviarlo).
def aggiorna_ordine(ordine_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repo = OrdiniRepository()
    _assert_stato(repo, ordine_id, _STATI_MODIFICABILI, op="aggiorna_ordine")

    if "billing_account_id" in payload:
        raw_ba = empty_to_none(payload["billing_account_id"])
        # Coercion difensiva: un billing_account_id non numerico e' input
        # invalido -> 422 parlante, non 500 (int() su garbage solleverebbe
        # ValueError non gestito). attuale_ba dal DB e' gia' bigint.
        try:
            nuovo_ba = int(raw_ba) if raw_ba is not None else None
        except (TypeError, ValueError):
            nuovo_ba = None
            ErrorManager.require(
                False,
                code="E_ORD_VALIDAZIONE",
                message="billing_account_id non valido.",
                detail=f"billing_account_id={payload['billing_account_id']!r}",
                function_name=f"{_FN}.aggiorna_ordine",
            )
        testata = repo.get_ordine(ordine_id)
        attuale_ba = (testata or {}).get("billing_account_id")
        attuale_ba = int(attuale_ba) if attuale_ba is not None else None
        ErrorManager.require(
            nuovo_ba == attuale_ba,
            code="E_ORD_VALIDAZIONE",
            message=(
                "Cliente (billing_account_id) immutabile dopo la creazione. "
                "Per cambiare cliente crea un nuovo ordine."
            ),
            detail=f"attuale={attuale_ba} richiesto={nuovo_ba}",
            function_name=f"{_FN}.aggiorna_ordine",
        )

    data = {k: empty_to_none(v) for k, v in payload.items() if k in _UPDATE_KEYS_ORDINE}
    ErrorManager.require(
        len(data) > 0,
        code="E_ORD_VALIDAZIONE",
        message="Nessun campo aggiornabile nel payload.",
        function_name=f"{_FN}.aggiorna_ordine",
    )
    with _db_errors("aggiorna_ordine"):
        repo.update_ordine(ordine_id, **data)
    return {"ordine_id": ordine_id, "updated": True}


# Scopo: Hard-delete ordine (abbandono bozza). Solo DRAFT.
def elimina_ordine(ordine_id: int) -> dict[str, Any]:
    repo = OrdiniRepository()
    _assert_stato(repo, ordine_id, _STATI_MODIFICABILI, op="elimina_ordine")
    with _db_errors("elimina_ordine"):
        deleted = repo.delete_ordine(ordine_id)
    return {"ordine_id": ordine_id, "deleted": deleted}


# Scopo: Conferma ordine (DRAFT → CONFERMATO). La transizione e' validata dal
#        trigger DB; qui si applica solo il guard di stato + righe presenti.
def conferma(ordine_id: int) -> dict[str, Any]:
    repo = OrdiniRepository()
    stato = _assert_stato(repo, ordine_id, _STATI_MODIFICABILI, op="conferma")
    righe = repo.list_righe(ordine_id)
    ErrorManager.require(
        len(righe) > 0,
        code="E_ORD_NESSUNA_RIGA",
        message="Impossibile confermare un ordine senza righe.",
        detail=f"ordine_id={ordine_id}",
        function_name=f"{_FN}.conferma",
    )
    stato_conf_id = repo.get_stato_id_by_codice(_STATO_CONFERMATO)
    ErrorManager.require(
        stato_conf_id is not None,
        code="E_ORD_VALIDAZIONE",
        message="Stato CONFERMATO non configurato in config.stati_doc_ordini.",
        function_name=f"{_FN}.conferma",
    )
    assert stato_conf_id is not None
    with _db_errors("conferma"):
        repo.update_stato(ordine_id, int(stato_conf_id))
    return {"ordine_id": ordine_id, "stato_precedente": stato, "stato": _STATO_CONFERMATO}


# ══════════════════════════════════════════════════════════
#  SCRITTURE — Righe (ricalcolo totali via trigger DB)
# ══════════════════════════════════════════════════════════

# Scopo: Aggiunge una riga all'ordine (solo DRAFT). Pricing stile preventivo:
#        se il prezzo non e' passato e l'articolo NON e' composito, lo risolve
#        via PricingService (BB condiviso). Per articolo composito il prezzo
#        padre e' 0 e i componenti BoM sono inizializzati via fn DB.
def gestisci_riga(
    ordine_id: int, payload: dict[str, Any], *, auth_user_id: int | None = None,
) -> dict[str, Any]:
    repo = OrdiniRepository()
    testata = _get_testata_or_raise(repo, ordine_id, op="gestisci_riga")
    ErrorManager.require(
        testata["stato_codice_interno"] in _STATI_RIGHE_MODIFICABILI,
        code="E_ORD_STATO_TRANSIZIONE",
        message="Righe modificabili solo su ordine in bozza.",
        detail=f"stato={testata['stato_codice_interno']}",
        function_name=f"{_FN}.gestisci_riga",
    )

    data = {k: empty_to_none(v) for k, v in payload.items() if k in _CREATE_KEYS_RIGA}
    articolo_id = data.get("articolo_id")
    ErrorManager.require(
        articolo_id is not None and str(articolo_id).strip() != "",
        code="E_ORD_VALIDAZIONE",
        message="articolo_id obbligatorio.",
        function_name=f"{_FN}.gestisci_riga",
    )
    assert articolo_id is not None

    is_composito = repo.is_articolo_composito(str(articolo_id))
    prezzo_unitario = data.get("prezzo_unitario")

    # Pricing auto-fill (solo articolo NON composito, prezzo non passato).
    if not is_composito and prezzo_unitario is None:
        prezzo_unitario = _resolve_prezzo_riga(
            repo, testata, articolo_id=str(articolo_id),
            uom_id=data.get("uom_operativa_id"),
        )
    elif is_composito:
        # Padre composito: prezzo = SUM(figli), ricalcolato dal trigger DB dopo
        # init componenti. Si inserisce con 0 per soddisfare l'eventuale guard.
        prezzo_unitario = prezzo_unitario if prezzo_unitario is not None else "0"

    with _db_errors("gestisci_riga"), transaction.atomic():
        riga_nr = repo.next_riga_nr(ordine_id)
        created = repo.create_riga(
            ordine_id=ordine_id,
            riga_nr=riga_nr,
            articolo_id=str(articolo_id),
            descrizione=data.get("descrizione"),
            quantita=data.get("quantita"),
            qta_operativa=data.get("qta_operativa"),
            uom_operativa_id=data.get("uom_operativa_id"),
            factor_to_base=data.get("factor_to_base"),
            prezzo_unitario=prezzo_unitario,
            sconto_perc=data.get("sconto_perc"),
            iva_id=data.get("iva_id"),
            meta=data.get("meta") if isinstance(data.get("meta"), dict) else None,
        )
        riga_id = int(created["id"])

        # Auto-init componenti BoM per articolo composito.
        if is_composito:
            emittente_sr_id = _resolve_emittente_sr_id(repo, testata)
            data_rif = _data_riferimento(testata)
            repo.init_componenti_riga(
                riga_id=riga_id,
                emittente_soggetto_ruolo_id=emittente_sr_id,
                data_riferimento=data_rif,
            )

    return {"ordine_id": ordine_id, "riga_id": riga_id, "is_composito": is_composito}


# Scopo: Aggiorna una riga ordine esistente (solo DRAFT).
def aggiorna_riga(
    ordine_id: int, riga_id: int, payload: dict[str, Any],
    *, auth_user_id: int | None = None,
) -> dict[str, Any]:
    repo = OrdiniRepository()
    testata = _get_testata_or_raise(repo, ordine_id, op="aggiorna_riga")
    ErrorManager.require(
        testata["stato_codice_interno"] in _STATI_RIGHE_MODIFICABILI,
        code="E_ORD_STATO_TRANSIZIONE",
        message="Righe modificabili solo su ordine in bozza.",
        function_name=f"{_FN}.aggiorna_riga",
    )
    riga = repo.get_riga(riga_id)
    ErrorManager.require(
        riga is not None and riga["ordine_id"] == ordine_id,
        code="E_ORD_NOT_FOUND",
        message="Riga non trovata per questo ordine.",
        function_name=f"{_FN}.aggiorna_riga",
    )
    data = {k: empty_to_none(v) for k, v in payload.items() if k in _UPDATE_KEYS_RIGA}
    ErrorManager.require(
        len(data) > 0,
        code="E_ORD_VALIDAZIONE",
        message="Nessun campo aggiornabile nel payload riga.",
        function_name=f"{_FN}.aggiorna_riga",
    )
    with _db_errors("aggiorna_riga"):
        repo.update_riga(riga_id, **data)
    return {"ordine_id": ordine_id, "riga_id": riga_id, "updated": True}


# Scopo: Elimina riga ordine (HARD DELETE, solo DRAFT). I componenti BoM hanno
#        ON DELETE CASCADE; il trigger DB blocca se la riga e' collegata a DDT.
def elimina_riga(ordine_id: int, riga_id: int) -> dict[str, Any]:
    repo = OrdiniRepository()
    testata = _get_testata_or_raise(repo, ordine_id, op="elimina_riga")
    ErrorManager.require(
        testata["stato_codice_interno"] in _STATI_RIGHE_MODIFICABILI,
        code="E_ORD_STATO_TRANSIZIONE",
        message="Righe eliminabili solo su ordine in bozza.",
        function_name=f"{_FN}.elimina_riga",
    )
    riga = repo.get_riga(riga_id)
    ErrorManager.require(
        riga is not None and riga["ordine_id"] == ordine_id,
        code="E_ORD_NOT_FOUND",
        message="Riga non trovata per questo ordine.",
        function_name=f"{_FN}.elimina_riga",
    )
    with _db_errors("elimina_riga"):
        deleted = repo.delete_riga(riga_id)
    return {"ordine_id": ordine_id, "riga_id": riga_id, "deleted": deleted}


# ══════════════════════════════════════════════════════════
#  Componenti riga (BoM CASO A)
# ══════════════════════════════════════════════════════════

# Scopo: Preview read-only componenti BoM per il drawer riga (pre-save).
def preview_componenti_riga(
    ordine_id: int, *, articolo_id: str, uom_operativa_id: int | None,
    quantita: Any, auth_user_id: int | None = None,
) -> list[dict[str, Any]]:
    repo = OrdiniRepository()
    testata = _get_testata_or_raise(repo, ordine_id, op="preview_componenti_riga")
    emittente_sr_id = _resolve_emittente_sr_id(repo, testata)
    return repo.preview_componenti_riga(
        articolo_id=articolo_id,
        uom_id=uom_operativa_id,
        quantita_padre=quantita,
        data_riferimento=_data_riferimento(testata),
        ba_id=testata.get("billing_account_id"),
        utility_id=testata.get("utility_id"),
        emittente_soggetto_ruolo_id=emittente_sr_id,
    )


# Scopo: Lista componenti persistiti di una riga.
def list_componenti_riga(
    ordine_id: int, riga_id: int, *, solo_attivi: bool = True,
) -> list[dict[str, Any]]:
    return OrdiniRepository().list_componenti_riga(riga_id, solo_attivi=solo_attivi)


# Scopo: Aggiorna un componente BoM (solo DRAFT, scope componente→riga→ordine).
def update_componente(
    ordine_id: int, riga_id: int, componente_id: int, payload: dict[str, Any],
) -> dict[str, Any]:
    repo = OrdiniRepository()
    scope = repo.load_componente_with_scope(componente_id)
    ErrorManager.require(
        scope is not None and scope["ordine_id"] == ordine_id
        and scope["riga_ordine_id"] == riga_id,
        code="E_ORD_NOT_FOUND",
        message="Componente non trovato in questo ordine/riga.",
        function_name=f"{_FN}.update_componente",
    )
    assert scope is not None
    ErrorManager.require(
        scope["stato_codice_interno"] in _STATI_RIGHE_MODIFICABILI,
        code="E_ORD_STATO_TRANSIZIONE",
        message="Componenti modificabili solo su ordine in bozza.",
        function_name=f"{_FN}.update_componente",
    )
    allowed = {"prezzo_unitario", "attivo", "esposto_in_fattura", "meta"}
    data = {k: empty_to_none(v) for k, v in payload.items() if k in allowed}
    with _db_errors("update_componente"):
        repo.update_componente(componente_id, **data)
    return {"componente_id": componente_id, "updated": True}


# Scopo: Elimina (soft, attivo=FALSE via mixin) un componente BoM (solo DRAFT).
def delete_componente(
    ordine_id: int, riga_id: int, componente_id: int,
) -> dict[str, Any]:
    repo = OrdiniRepository()
    scope = repo.load_componente_with_scope(componente_id)
    ErrorManager.require(
        scope is not None and scope["ordine_id"] == ordine_id
        and scope["riga_ordine_id"] == riga_id,
        code="E_ORD_NOT_FOUND",
        message="Componente non trovato in questo ordine/riga.",
        function_name=f"{_FN}.delete_componente",
    )
    assert scope is not None
    ErrorManager.require(
        scope["stato_codice_interno"] in _STATI_RIGHE_MODIFICABILI,
        code="E_ORD_STATO_TRANSIZIONE",
        message="Componenti eliminabili solo su ordine in bozza.",
        function_name=f"{_FN}.delete_componente",
    )
    with _db_errors("delete_componente"):
        deleted = repo.delete_componente(componente_id)
    return {"componente_id": componente_id, "deleted": deleted}


# ══════════════════════════════════════════════════════════
#  INTEGRAZIONE — Push singolo a commessa (chiusura giro)
# ══════════════════════════════════════════════════════════

# Scopo: Push singolo dell'ordine CONFERMATO a commessa (chiusura giro). Riusa
#        l'orchestratore commesse esistente con sorgente ORDINE_VENDITA →
#        attivita_fatturabili → pipeline lotto → fattura. Pattern push singolo
#        gemello preventivi/offerte (decisione §8.3).
def push_a_commessa(ordine_id: int) -> dict[str, Any]:
    repo = OrdiniRepository()
    testata = _get_testata_or_raise(repo, ordine_id, op="push_a_commessa")
    ErrorManager.require(
        testata["stato_codice_interno"] in _STATI_PUSHABILI,
        code="E_ORD_STATO_TRANSIZIONE",
        message="Solo ordini confermati possono essere inviati a commessa.",
        detail=f"stato={testata['stato_codice_interno']}",
        function_name=f"{_FN}.push_a_commessa",
    )
    righe_count = repo.count_righe_pushable(ordine_id)
    ErrorManager.require(
        righe_count > 0,
        code="E_ORD_NESSUNA_RIGA",
        message="Nessuna riga eleggibile per il push a commessa.",
        detail=f"ordine_id={ordine_id}",
        function_name=f"{_FN}.push_a_commessa",
    )
    # Import locale per evitare cicli.
    from apps.vendite.services.commesse_service import pr_run_commesse_push_one

    report = pr_run_commesse_push_one(
        sorgente_codice="ORDINE_VENDITA",
        sorgente_uid=ordine_id,
    )
    return {
        "ordine_id": ordine_id,
        "stato": report["stato"],
        "push_log_id": report["push_log_id"],
        "durata_ms": report["durata_ms"],
        "handlers": report["handlers"],
        "righe_pushable": righe_count,
        "fatturazione_trigger": testata.get("fatturazione_trigger"),
    }


# ══════════════════════════════════════════════════════════
#  Helper privati
# ══════════════════════════════════════════════════════════

# Scopo: Context manager per normalizzare errori DB in ServiceError parlanti.
#        Gemello _db_errors di offerte_service: IntegrityError (unique/fk) via
#        map_integrity_error + mappe vincolo; DatabaseError (trigger P0001) via
#        estrazione regex del codice E_* dal MESSAGE del RAISE, cosi' il FE puo'
#        fare routing UI specifico. Fallback E_VENDITE_VALIDATION.
@contextmanager
def _db_errors(op: str) -> Iterator[None]:
    context = {"op": f"{_FN}.{op}"}
    try:
        yield
    except IntegrityError as exc:
        map_integrity_error(
            exc,
            unique_constraints=_UNIQUE_CONSTRAINTS,
            fk_constraints=_FK_CONSTRAINTS,
            fallback_code=E_VENDITE_VALIDATION,
            fallback_message="Violazione vincolo DB su ordine.",
            context=context,
        )
    except DatabaseError as exc:
        exc_text = str(exc)
        match = _DB_ERROR_CODE_RE.search(exc_text)
        code = match.group(1) if match else E_VENDITE_VALIDATION
        ErrorManager.raise_error(
            code=code,
            message=exc_text.split("\n", maxsplit=1)[0].strip()
            or "Violazione vincolo DB su ordine.",
            detail=exc_text,
            context=context,
        )


def _get_testata_or_raise(
    repo: OrdiniRepository, ordine_id: int, *, op: str,
) -> dict[str, Any]:
    testata = repo.get_ordine(ordine_id)
    ErrorManager.require(
        testata is not None,
        code="E_ORD_NOT_FOUND",
        message="Ordine non trovato.",
        detail=f"ordine_id={ordine_id}",
        function_name=f"{_FN}.{op}",
    )
    assert testata is not None
    return testata


def _assert_stato(
    repo: OrdiniRepository, ordine_id: int, ammessi: frozenset[str], *, op: str,
) -> str:
    stato = repo.get_stato_codice(ordine_id)
    ErrorManager.require(
        stato is not None,
        code="E_ORD_NOT_FOUND",
        message="Ordine non trovato.",
        detail=f"ordine_id={ordine_id}",
        function_name=f"{_FN}.{op}",
    )
    assert stato is not None
    ErrorManager.require(
        stato in ammessi,
        code="E_ORD_STATO_TRANSIZIONE",
        message=f"Operazione non ammessa nello stato {stato}.",
        detail=f"ammessi={sorted(ammessi)}",
        function_name=f"{_FN}.{op}",
    )
    return stato


def _resolve_emittente_sr_id(repo: OrdiniRepository, testata: dict[str, Any]) -> int:
    fiscale_id = testata.get("emittente_fiscale_id")
    ErrorManager.require(
        fiscale_id is not None,
        code="E_ORD_VALIDAZIONE",
        message="Ordine senza emittente fiscale: impossibile risolvere i componenti.",
        function_name=f"{_FN}._resolve_emittente_sr_id",
    )
    sr_id = repo.get_emittente_sr_id_by_fiscale_id(int(fiscale_id))
    ErrorManager.require(
        sr_id is not None,
        code="E_ORD_VALIDAZIONE",
        message="Soggetto-ruolo emittente non risolvibile.",
        function_name=f"{_FN}._resolve_emittente_sr_id",
    )
    assert sr_id is not None
    return int(sr_id)


def _data_riferimento(testata: dict[str, Any]) -> date:
    raw = testata.get("data")
    if isinstance(raw, date):
        return raw
    ErrorManager.require(
        raw is not None,
        code="E_ORD_VALIDAZIONE",
        message="Ordine senza data: impossibile risolvere prezzi/componenti.",
        function_name=f"{_FN}._data_riferimento",
    )
    return date.fromisoformat(str(raw))


# Scopo: Risolve il prezzo unitario riga via PricingService (BB condiviso,
#        mai query dirette su listini — memoria feedback_pricing_centralizzato).
def _resolve_prezzo_riga(
    repo: OrdiniRepository, testata: dict[str, Any], *,
    articolo_id: str, uom_id: int | None,
) -> str:
    from decimal import Decimal

    from apps.vendite.services.pricing_service import PricingService

    fn = f"{_FN}._resolve_prezzo_riga"
    ErrorManager.require(
        testata.get("billing_account_id") is not None,
        code="E_ORD_VALIDAZIONE",
        message="Ordine senza billing_account: impossibile risolvere il prezzo.",
        function_name=fn,
    )
    ErrorManager.require(
        testata.get("utility_id") is not None,
        code="E_ORD_VALIDAZIONE",
        message="Ordine senza utility: impossibile risolvere il prezzo.",
        function_name=fn,
    )
    ErrorManager.require(
        uom_id is not None,
        code="E_ORD_VALIDAZIONE",
        message="uom_operativa_id obbligatorio per risolvere il prezzo.",
        function_name=fn,
    )
    emittente_sr_id = _resolve_emittente_sr_id(repo, testata)
    result = PricingService().resolve_prezzo(
        articolo_id=articolo_id,
        uom_id=int(uom_id),
        data_riferimento=_data_riferimento(testata),
        ba_id=int(testata["billing_account_id"]),
        utility_id=int(testata["utility_id"]),
        emittente_soggetto_ruolo_id=emittente_sr_id,
    )
    prezzo = result.get("prezzo_finale")
    if isinstance(prezzo, Decimal):
        return str(prezzo)
    return str(prezzo) if prezzo is not None else "0"
