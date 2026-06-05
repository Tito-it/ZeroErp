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

import json
import logging
import re
from collections.abc import Iterator
from decimal import Decimal, InvalidOperation
from contextlib import contextmanager
from datetime import date
from typing import Any

from django.db import DatabaseError, IntegrityError, transaction

from apps.core.api.payload_validators import paginated_envelope
from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import map_integrity_error
from apps.core.services.value_normalizer import empty_to_none
from apps.vendite.db.ordini_repository import OrdiniRepository
from apps.vendite.services._componenti_service_helpers import (
    normalize_componenti_overrides,
)
from apps.vendite.services._pricing_gate_helpers import (
    validate_componenti_overrides_authorization,
)

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
    righe = repo.list_righe(ordine_id)
    # Capability data-driven da script.fn_available_actions_ordine (matrice
    # config.transizioni_stati_ordini): available_actions (conferma/annulla/
    # push), can_edit_testata/righe, can_push_commessa(+reason), non_editable_
    # fields, stato_codice. Sostituisce il calcolo hardcoded: la verita' e' a DB
    # (lettura) + trigger guard (enforcement). `can_conferma` non e' piu' un
    # flag: la conferma e' un'entry di available_actions (key='conferma').
    capabilities = repo.get_capabilities(ordine_id)
    return {
        **testata,
        **capabilities,
        "righe_count": len(righe),
    }


# Scopo: Lista righe di un ordine.
def list_righe(ordine_id: int) -> list[dict[str, Any]]:
    return OrdiniRepository().list_righe(ordine_id)


# Scopo: Riepilogo IVA aggregato dell'ordine (una riga per aliquota). Calcolo
#        fiscalmente corretto gia' applicato in DB via la view derivata
#        vw_ordini_riepilogo_iva_dettaglio (stessa formula dei preventivi): il
#        service legge, nessun ricalcolo Python. Usato dal FE per il pannello
#        "Riepilogo IVA" del drawer ordine e dal context builder della stampa.
def list_riepilogo_iva(ordine_id: int) -> list[dict[str, Any]]:
    return OrdiniRepository().list_riepilogo_iva(ordine_id)


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
        # Stesso codice della difesa DB (lock-columns, DB-ORD-LOCK): un solo
        # codice user-facing per "cliente immutabile", indipendente dal layer
        # che lo intercetta (service vs UPDATE diretta su DB).
        ErrorManager.require(
            nuovo_ba == attuale_ba,
            code="E_ORD_CLIENTE_IMMUTABILE",
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


# ══════════════════════════════════════════════════════════
#  CONVERSIONE UPSTREAM — preventivo/offerta → ordine (§7.4)
# ══════════════════════════════════════════════════════════

# Stati del documento di origine che ammettono la generazione di un ordine.
_STATI_PREVENTIVO_CONVERTIBILI: frozenset[str] = frozenset({"ACCETTATO"})
_STATI_OFFERTA_CONVERTIBILI: frozenset[str] = frozenset({"ACCETTATA"})


# Scopo: Crea la testata ordine DRAFT da un documento upstream + valorizza la
#        provenienza `documento_origine`. Condiviso da preventivo/offerta →
#        ordine (regola del 2). Ritorna (ordine_id, numero). Da chiamare DENTRO
#        una transaction.atomic del caller (che orchestra anche la copia righe).
def _crea_testata_ordine_da_origine(
    header: dict[str, Any], tipo_origine: str, origine_id: int,
) -> tuple[int, str | None]:
    creato = crea_ordine(header)
    ordine_id = int(creato["id"])
    # Coerenza con le altre scritture del modulo: errori DB tradotti in
    # ServiceError parlante (CHECK vocabolario/co-presenza documento origine)
    # invece di propagare un 500 grezzo.
    with _db_errors(f"crea_ordine_da_{tipo_origine.lower()}"):
        OrdiniRepository().set_documento_origine(
            ordine_id, tipo_origine, int(origine_id),
        )
    return ordine_id, creato.get("numero")


# Scopo: Mappa una riga preventivo nel payload riga ordine (whitelist
#        _CREATE_KEYS_RIGA). Nota rename: preventivo usa `sconto_percentuale`,
#        ordine usa `sconto_perc`. Il prezzo unitario è copiato "congelato"
#        (la riga non-composita non viene ri-prezzata); per le righe composite
#        gestisci_riga re-inizializza i componenti ai prezzi correnti (la
#        struttura BoM è copiata, i prezzi componente sono risolti all'ordine —
#        scelta v1 documentata, vedi analisi §7.4).
def _riga_payload_da_preventivo(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "articolo_id": r.get("articolo_id"),
        "descrizione": r.get("descrizione"),
        "quantita": r.get("quantita"),
        "qta_operativa": r.get("qta_operativa"),
        "uom_operativa_id": r.get("uom_operativa_id"),
        "factor_to_base": r.get("factor_to_base"),
        "prezzo_unitario": r.get("prezzo_unitario"),
        "sconto_perc": r.get("sconto_percentuale"),
        "iva_id": r.get("iva_id"),
        "meta": r.get("meta") if isinstance(r.get("meta"), dict) else None,
    }


# Scopo: Genera un nuovo ordine in DRAFT da un preventivo ACCETTATO, copiando
#        testata (cliente/utility/valuta/termine/emittente) + righe (1:1, prezzi
#        congelati) + componenti BoM (struttura, ri-prezzati), e valorizzando
#        documento_origine = (PREVENTIVO, preventivo_id). Predisposto da A1: il
#        link non ha UNIQUE → da uno stesso preventivo si possono generare più
#        ordini (riordini). Orchestrazione Python (riusa crea_ordine + gestisci_riga
#        come il normale flusso di creazione ordine), tutto in una transazione.
def crea_ordine_da_preventivo(preventivo_id: int) -> dict[str, Any]:
    # Import locale: evita accoppiamento a livello di modulo tra i due domini
    # (entrambi in apps.vendite) e qualunque rischio di import circolare.
    from apps.vendite.db.preventivi_repository import PreventiviRepository

    prev_repo = PreventiviRepository()
    testata = prev_repo.get_preventivo(preventivo_id)
    ErrorManager.require(
        testata is not None,
        code="E_PREV_NOT_FOUND",
        message="Preventivo non trovato.",
        detail=f"preventivo_id={preventivo_id}",
        function_name=f"{_FN}.crea_ordine_da_preventivo",
    )
    assert testata is not None
    ErrorManager.require(
        testata.get("stato_codice_interno") in _STATI_PREVENTIVO_CONVERTIBILI,
        code="E_ORD_ORIGINE_NON_CONVERTIBILE",
        message="Il preventivo deve essere ACCETTATO per generare un ordine.",
        detail=f"stato={testata.get('stato_codice_interno')}",
        function_name=f"{_FN}.crea_ordine_da_preventivo",
    )

    righe = [r for r in prev_repo.list_righe(preventivo_id) if r.get("attivo", True)]

    header = {
        "billing_account_id": testata.get("billing_account_id"),
        "utility_id": testata.get("utility_id"),
        "emittente_fiscale_id": testata.get("emittente_fiscale_id"),
        "valuta_id": testata.get("valuta_id"),
        "termine_pagamento_id": testata.get("termine_pagamento_id"),
        "data": date.today().isoformat(),
    }

    with transaction.atomic():
        ordine_id, numero = _crea_testata_ordine_da_origine(
            header, "PREVENTIVO", preventivo_id,
        )
        for r in righe:
            gestisci_riga(ordine_id, _riga_payload_da_preventivo(r))

    return {
        "ordine_id": ordine_id,
        "numero": numero,
        "righe_create": len(righe),
        "documento_origine": {"tipo": "PREVENTIVO", "id": int(preventivo_id)},
    }


def _as_str(value: Any) -> str | None:
    return None if value is None else str(value)


# Scopo: Costruisce la mappa override prezzi componenti {componente_id: prezzo}
#        dal jsonb `componenti` della fn `fn_offerta_righe_espanse`. psycopg può
#        restituire il jsonb già parsato (list) o come stringa → coerce difensivo
#        (pattern speculare al FE `coerceJsonbToArray`). Chiave = uuid articolo
#        componente (allineata al keying di `fn_ordine_riga_componenti_init`).
def _overrides_da_componenti(componenti: Any) -> dict[str, str]:
    if isinstance(componenti, str):
        try:
            componenti = json.loads(componenti)
        except (ValueError, TypeError):
            return {}
    if not isinstance(componenti, list):
        return {}
    out: dict[str, str] = {}
    for c in componenti:
        if not isinstance(c, dict):
            continue
        cid = c.get("componente_id")
        prezzo = c.get("prezzo")
        if cid is None or prezzo is None:
            continue
        # La fn DB `fn_ordine_riga_componenti_init` RIFIUTA un override prezzo 0
        # (E_PARAMETRO_INVALIDO "prezzo override deve essere diverso da zero"):
        # un componente negoziato a 0 viene escluso dagli override → ricade sul
        # resolver (prezzo corrente). Limitazione nota del vincolo override DB.
        try:
            if Decimal(str(prezzo)) == 0:
                continue
        except InvalidOperation:
            continue
        out[str(cid)] = str(prezzo)
    return out


# Scopo: Copia una riga «espansa» dell'offerta in una riga ordine PRESERVANDO i
#        prezzi NEGOZIATI (l'offerta è ACCETTATA → niente ri-prezzatura, a
#        differenza del preventivo). Non-composito: `prezzo_unitario` congelato.
#        Composito: il prezzo padre è ricalcolato dal trigger DB
#        (`trgfn_componenti_ricalcola_padre`) sui componenti, i cui prezzi
#        negoziati sono passati come `componenti_overrides` (dal jsonb della fn).
def _copia_riga_offerta_espansa(
    repo: OrdiniRepository, ordine_id: int, r: dict[str, Any],
    *, emittente_sr_id: int, data_rif: date,
) -> None:
    is_composito = bool(r.get("is_composito"))
    riga_nr = repo.next_riga_nr(ordine_id)
    created = repo.create_riga(
        ordine_id=ordine_id,
        riga_nr=riga_nr,
        articolo_id=str(r["articolo_id"]),
        descrizione=r.get("descrizione"),
        quantita=_as_str(r.get("quantita")),
        qta_operativa=_as_str(r.get("qta_operativa")),
        uom_operativa_id=r.get("uom_operativa_id"),
        factor_to_base=_as_str(r.get("factor_to_base")),
        # Padre composito: 0 placeholder, il trigger ricalcola da SUM(componenti).
        prezzo_unitario="0" if is_composito else _as_str(r.get("prezzo_unitario")),
        sconto_perc=_as_str(r.get("sconto_perc")),
        iva_id=r.get("iva_id"),
    )
    if not is_composito:
        return
    repo.init_componenti_riga(
        riga_id=int(created["id"]),
        emittente_soggetto_ruolo_id=emittente_sr_id,
        data_riferimento=data_rif,
        componenti_overrides=_overrides_da_componenti(r.get("componenti")) or None,
    )


# Scopo: Genera un ordine DRAFT da un'offerta ACCETTATA. A differenza del
#        preventivo (righe già piatte), l'offerta non ha righe materializzate: le
#        righe «effettive» (listino + variazione + eccezioni, con BoM) sono
#        prodotte dalla fn DB `fn_offerta_righe_espanse` (ordine-ready). Copia
#        testata (cliente/utility/valuta/emittente) + righe espanse PRESERVANDO i
#        prezzi negoziati (anche componenti) + documento_origine = (OFFERTA, id).
def crea_ordine_da_offerta(offerta_id: int) -> dict[str, Any]:
    from apps.vendite.db.offerte_repository import OfferteRepository

    off_repo = OfferteRepository()
    testata = off_repo.get_offerta(offerta_id)
    ErrorManager.require(
        testata is not None,
        code="E_VENDITE_NOT_FOUND",
        message="Offerta non trovata.",
        detail=f"offerta_id={offerta_id}",
        function_name=f"{_FN}.crea_ordine_da_offerta",
    )
    assert testata is not None
    ErrorManager.require(
        testata.get("stato_codice_interno") in _STATI_OFFERTA_CONVERTIBILI,
        code="E_ORD_ORIGINE_NON_CONVERTIBILE",
        message="L'offerta deve essere ACCETTATA per generare un ordine.",
        detail=f"stato={testata.get('stato_codice_interno')}",
        function_name=f"{_FN}.crea_ordine_da_offerta",
    )

    righe = off_repo.list_righe_espanse(offerta_id)

    header = {
        "billing_account_id": testata.get("billing_account_id"),
        "utility_id": testata.get("utility_id"),
        "emittente_fiscale_id": testata.get("emittente_fiscale_id"),
        "valuta_id": testata.get("valuta_id"),
        "data": date.today().isoformat(),
    }

    repo = OrdiniRepository()
    with transaction.atomic():
        ordine_id, numero = _crea_testata_ordine_da_origine(
            header, "OFFERTA", offerta_id,
        )
        # emittente SR + data riferimento dalla testata ordine creata (per il
        # pricing/data-snapshot dei componenti BoM).
        testata_ord = _get_testata_or_raise(
            repo, ordine_id, op="crea_ordine_da_offerta",
        )
        emittente_sr_id = _resolve_emittente_sr_id(repo, testata_ord)
        data_rif = _data_riferimento(testata_ord)
        with _db_errors("crea_ordine_da_offerta"):
            for r in righe:
                _copia_riga_offerta_espansa(
                    repo, ordine_id, r,
                    emittente_sr_id=emittente_sr_id, data_rif=data_rif,
                )

    return {
        "ordine_id": ordine_id,
        "numero": numero,
        "righe_create": len(righe),
        "documento_origine": {"tipo": "OFFERTA", "id": int(offerta_id)},
    }


# Scopo: Hard-delete ordine BOZZA ORFANO (solo supporto al pattern "abbandono
#        bozza" del drawer: create auto-salva una BOZZA per abilitare le righe;
#        se l'operatore esce senza inserirne, la bozza vuota viene rimossa).
#        NON e' un'azione di cancellazione di ordini reali: un ordine con righe
#        o non in bozza NON si cancella, si ANNULLA (cambia_stato → ANNULLATO).
#        Allineato a `elimina_preventivo` (niente hard-delete di dati reali).
# Guard di dominio (defense-in-depth: il FE filtra gia' su righe_count=0):
#  - ordine esistente, stato BOZZA (DRAFT), zero righe.
def elimina_ordine(ordine_id: int) -> dict[str, Any]:
    repo = OrdiniRepository()
    _assert_stato(repo, ordine_id, _STATI_MODIFICABILI, op="elimina_ordine")
    righe_count = len(repo.list_righe(ordine_id))
    ErrorManager.require(
        righe_count == 0,
        code="E_ORD_STATO_TRANSIZIONE",
        message=(
            "Impossibile eliminare un ordine con righe: annullare l'ordine "
            "(cambio stato → ANNULLATO) invece di cancellarlo."
        ),
        detail=f"righe_count={righe_count}",
        function_name=f"{_FN}.elimina_ordine",
    )
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


# Scopo: Esegue una transizione di stato data-driven dell'ordine (es. annulla
#        DRAFT->ANNULLATO). Generico: lo stato destinazione arriva dal codice
#        interno (`available_actions[].target_state` della fn capabilities).
#        L'ammissibilita' della transizione e' validata dal trigger DB
#        `trgfn_ordini_guard_transizione` (matrice config.transizioni_stati_ordini):
#        il service non duplica il grafo. La conferma (DRAFT->CONFERMATO) ha un
#        endpoint dedicato (`conferma`) per le sue precondizioni; questa copre le
#        altre transizioni manuali esposte.
def cambia_stato(ordine_id: int, stato_codice: str) -> dict[str, Any]:
    repo = OrdiniRepository()
    testata = _get_testata_or_raise(repo, ordine_id, op="cambia_stato")
    stato_prec = testata.get("stato_codice_interno")
    target = (stato_codice or "").strip()
    ErrorManager.require(
        bool(target),
        code="E_ORD_VALIDAZIONE",
        message="stato_codice obbligatorio per il cambio stato.",
        function_name=f"{_FN}.cambia_stato",
    )
    stato_id = repo.get_stato_id_by_codice(target)
    ErrorManager.require(
        stato_id is not None,
        code="E_ORD_VALIDAZIONE",
        message=f"Stato '{target}' non configurato in config.stati_doc_ordini.",
        function_name=f"{_FN}.cambia_stato",
    )
    assert stato_id is not None
    # La transizione (stato_prec -> target) e' validata dal trigger guard DB;
    # eventuale errore tradotto da _db_errors (E_ORDINE_TRANSIZIONE_NON_AMMESSA).
    with _db_errors("cambia_stato"):
        repo.update_stato(ordine_id, int(stato_id))
    return {"ordine_id": ordine_id, "stato_precedente": stato_prec, "stato": target}


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

    # Override prezzi componenti BoM (dialog pre-save, simmetria preventivi).
    # Gate L1: l'override manuale richiede il permesso dedicato. Poi normalizza
    # la mappa {componente_id: prezzo} (None se assente). Applicata solo per
    # articolo composito (vedi init componenti sotto).
    validate_componenti_overrides_authorization(
        payload, auth_user_id, function_name=f"{_FN}.gestisci_riga",
    )
    componenti_overrides = normalize_componenti_overrides(
        payload.get("componenti_overrides"),
        function_name=f"{_FN}.gestisci_riga",
        error_code="E_ORD_VALIDAZIONE",
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

        # Auto-init componenti BoM per articolo composito. Con override prezzi
        # dal dialog pre-save (se presenti); altrimenti la fn DB risolve i
        # prezzi componente dal pricing corrente.
        if is_composito:
            emittente_sr_id = _resolve_emittente_sr_id(repo, testata)
            data_rif = _data_riferimento(testata)
            repo.init_componenti_riga(
                riga_id=riga_id,
                emittente_soggetto_ruolo_id=emittente_sr_id,
                data_riferimento=data_rif,
                componenti_overrides=componenti_overrides,
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
