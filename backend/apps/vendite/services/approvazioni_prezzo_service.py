# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service workflow L3 approvazione prezzo out-of-policy
#        (sviluppo-listini-v5 §14.6 Sprint E).
#
#        Workflow:
#        1) crea_richiesta_approvazione() - chiamata da preventivi_service
#           quando l'utente preventiva oltre L2 con flag richiesta_approvazione=true.
#           Crea pratica gia' APERTA, registra contesto violazione in meta,
#           invia email al ruolo approver (best-effort).
#        2) approva(riga_id) - endpoint POST /vendite/righe/<id>/approva-prezzo/
#           verifica permesso azione approva_prezzo_override, UPDATE riga
#           stato_approvazione_prezzo=APPROVED, chiude pratica con nota OK.
#        3) rifiuta(riga_id, motivazione) - endpoint POST .../rifiuta-prezzo/
#           UPDATE riga REJECTED, chiude pratica con nota KO + motivazione.
#        4) lista_coda() - endpoint GET /vendite/approvazioni-prezzo/
#           pratiche tipo APPROVAZIONE_PREZZO con stato APERTA, scope emittente.
# ------------------------------------------------------------

"""ApprovazioniPrezzoService — workflow L3 listini v5 §14.6."""

import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)

from django.db import connection, transaction
from django.utils.timezone import now

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import resolve_config_id_by_codice_interno, row_to_dict
from apps.core.services.email_service import EmailDispatchService
from apps.core.services.error_manager import ErrorManager
from apps.core.services.testata_guard import testata_o_not_found
from apps.core.services.permissions_resolver import PermissionResolver
from apps.pratiche.db.pratiche_repository import (
    PRATICHE_ORDER_COLS,
    PraticheRepository,
)
from apps.pratiche.services.pratiche_service import (
    aggiorna_pratica,
    cambia_stato_pratica,
    cerca_pratiche,
    crea_nota_pratica,
    crea_pratica,
)
from apps.vendite.db.preventivi_repository import PreventiviRepository
from apps.vendite.services._approvazioni_prezzo_constants import (
    AZIONE_APPROVA_PREZZO,
    META_KEY_RIGA_CONTRATTO_ID,
    META_KEY_RIGA_OFFERTA_ID,
    META_KEY_RIGA_PREVENTIVO_ID,
    META_KEY_SORGENTE,
    META_SORGENTE_CONTRATTO,
    META_SORGENTE_OFFERTA,
    META_SORGENTE_PREVENTIVO,
    STATO_APPROVAZIONE_APPROVED,
    STATO_APPROVAZIONE_PENDING,
    STATO_APPROVAZIONE_REJECTED,
)

_FN = "vendite.approvazioni_prezzo_service"

# Costanti dominio L3.
TIPO_PRESTAZIONE_CODICE = "APPROVAZIONE_PREZZO"
PRIORITA_DEFAULT_CODICE_INTERNO = "NORMALE"
# Permission codename allineato al seed config.azioni_processo id 10
# (changeSet 80_data 20260423-* / sprint E DB-E-1). Riesportato dalla
# costante centralizzata per non rompere consumer esterni eventuali.
AZIONE_PROCESSO = AZIONE_APPROVA_PREZZO
EMAIL_TEMPLATE_CODICE = "APPROVAZIONE_PREZZO_RICHIESTA"
PARAM_EMAIL_RECIPIENT = "VENDITE_APPROVAZIONE_PREZZO_RECIPIENT_EMAIL"

# Stati workflow pratica L3.
_STATO_PRATICA_INIZIALE = "APERTA"  # crea_pratica nasce gia' APERTA; usato anche come filtro lista
_STATO_PRATICA_CHIUSURA = "CHIUSA"

# Alias locali per leggibilita' nel modulo (i nomi STATO_APPROVAZIONE_* sono
# espliciti e gia' sufficienti, ma il prefisso _STATO_RIGA_* era piu' breve
# nel codice esistente; manteniamo i 2 nomi come alias per minimizzare il
# diff senza re-introdurre le stringhe magic).
_STATO_RIGA_PENDING = STATO_APPROVAZIONE_PENDING
_STATO_RIGA_APPROVED = STATO_APPROVAZIONE_APPROVED
_STATO_RIGA_REJECTED = STATO_APPROVAZIONE_REJECTED

# Note esito (tipi_nota seed: INTERNA visibile solo agli operatori).
_NOTA_TIPO_INTERNA = "INTERNA"

# Codici stabili `action_reason` esposti dalla coda approvazioni (Fase 5.B1).
# Contratto FE: ApprovazioniPrezzoListView.ACTION_REASON_KEYS mappa questi
# codici a chiavi i18n. Aggiungerne uno nuovo richiede di propagare a entrambi.
ACTION_REASON_PERMESSO_MANCANTE = "PERMESSO_MANCANTE"
ACTION_REASON_RIGA_NON_LINKATA = "RIGA_NON_LINKATA"


# ============================================================
# Sorgente-agnosticita' (refactor 2026-05-19 BE porting gate riga contratti)
# ============================================================
# Le pratiche APPROVAZIONE_PREZZO possono originare da preventivi o da
# contratti (DB simmetrizzato con migrations 20260518-01/02). Il dispatch
# verso la tabella/repository corretto avviene tramite questo dict.
# Ogni entry e' single source of truth per la sorgente: aggiungere ordini/
# DDT in futuro = aggiungere una entry, niente if-chain sparse nel service.

# Adapter `update_riga` per ogni sorgente: i 2 repo (PreventiviRepository,
# ContrattiRepository) hanno firme di update_riga diverse (preventivi accetta
# **kwargs; contratti accetta dict positional). Incapsuliamo la differenza
# qui via callable iniettato nel `_SORGENTE_CONFIG` invece che con if-chain
# nel dispatcher: aggiungere una sorgente futura (ordini/DDT) = aggiungere
# una entry, niente modifiche al dispatcher.
def _update_riga_preventivo(riga_id: int, fields: dict[str, Any]) -> None:
    PreventiviRepository().update_riga(riga_id, **fields)


def _update_riga_contratto(riga_id: int, fields: dict[str, Any]) -> None:
    from apps.vendite.db.contratti_repository import ContrattiRepository
    ContrattiRepository().update_riga(riga_id, fields)


def _update_riga_offerta(riga_id: int, fields: dict[str, Any]) -> None:
    # `riga_id` qui e' l'id dell'eccezione offerta. `update_eccezione` accetta
    # un dict positional come `ContrattiRepository.update_riga`.
    from apps.vendite.db.offerte_repository import OfferteRepository
    OfferteRepository().update_eccezione(riga_id, fields)


_SORGENTE_CONFIG: dict[str, dict[str, Any]] = {
    META_SORGENTE_PREVENTIVO: {
        "table": "vendite.preventivi_righe",
        "doc_fk_column": "preventivo_id",
        "meta_key_riga": META_KEY_RIGA_PREVENTIVO_ID,
        "meta_key_doc": "preventivo_id",
        "error_code_not_found": "E_PREV_RIGA_NOT_FOUND",
        "error_message_not_found": "Riga preventivo non trovata.",
        "label_doc": "preventivo",
        "update_riga": _update_riga_preventivo,
    },
    META_SORGENTE_CONTRATTO: {
        "table": "vendite.contratti_righe",
        "doc_fk_column": "contratto_id",
        "meta_key_riga": META_KEY_RIGA_CONTRATTO_ID,
        "meta_key_doc": "contratto_id",
        "error_code_not_found": "E_VENDITE_NOT_FOUND",
        "error_message_not_found": "Riga contratto non trovata.",
        "label_doc": "contratto",
        "update_riga": _update_riga_contratto,
    },
    META_SORGENTE_OFFERTA: {
        "table": "vendite.offerte_commerciali_eccezioni",
        "doc_fk_column": "offerta_id",
        "meta_key_riga": META_KEY_RIGA_OFFERTA_ID,
        "meta_key_doc": "offerta_id",
        "error_code_not_found": "E_VENDITE_NOT_FOUND",
        "error_message_not_found": "Eccezione offerta non trovata.",
        "label_doc": "offerta",
        "update_riga": _update_riga_offerta,
    },
}


def _require_sorgente(sorgente: str) -> dict[str, Any]:
    # Scopo: validate + ritorna config sorgente. Codice errore developer-only:
    # i call site interni non dovrebbero mai passare un valore fuori-whitelist.
    cfg = _SORGENTE_CONFIG.get(sorgente)
    ErrorManager.require(
        cfg is not None,
        code="E_APPROVAZIONE_PREZZO_NON_AMMESSA",
        message=f"Sorgente '{sorgente}' non gestita dal workflow L3.",
        function_name=f"{_FN}._require_sorgente",
    )
    assert cfg is not None
    return cfg


# Scopo: le colonne di riga che il workflow L3 scrive, e SOLO lui (il
#        contratto dell'operatore le rifiuta: `COMPONENTE_PATCH_OPERATORE`,
#        `UPDATE_KEYS_RIGA`). Dichiarate qui perche' il presidio
#        `test_whitelist_service_dentro_repository` le trovi accanto alle chiavi
#        dell'operatore: il repository deve saperle scrivere tutte.
CAMPI_RIGA_WORKFLOW_L3: frozenset[str] = frozenset({
    "stato_approvazione_prezzo", "pratica_approvazione_prezzo_id", "meta",
})


def _update_riga_workflow(
    *,
    sorgente: str,
    riga_id: int,
    fields: dict[str, Any],
) -> None:
    # Scopo: UPDATE workflow su riga (stato_approvazione_prezzo / pratica_id /
    #        meta). Dispatch via callable iniettato in `_SORGENTE_CONFIG`.
    # ⛔ Un campo fuori `CAMPI_RIGA_WORKFLOW_L3` e' un errore di programmazione
    #    (`RuntimeError`, 500 col traceback): la dichiarazione e' cio' che il
    #    presidio confronta col repository, e deve restare vera.
    fuori = sorted(set(fields) - CAMPI_RIGA_WORKFLOW_L3)
    if fuori:
        raise RuntimeError(f"_update_riga_workflow: campi non del workflow L3: {fuori}")
    cfg = _require_sorgente(sorgente)
    cfg["update_riga"](riga_id, fields)


def _coerce_meta_to_dict_safe(value: Any) -> dict[str, Any]:
    # Scopo: wrapper su preventivi_service._coerce_meta_to_dict (import lazy
    #        per evitare ciclo). Il modulo restera' qui finche' non viene
    #        promosso in core. Riusato da approva/rifiuta/_capabilities.
    from apps.vendite.services.preventivi_service import _coerce_meta_to_dict
    return _coerce_meta_to_dict(value)


# ============================================================
# Lookup cache modulo-level
# ============================================================
# I lookup `tipi_prestazione.id` e `priorita_pratiche.id` sono costanti per
# la vita del processo Django (cambiano solo per riseed amministrativo).
# Cache eager al primo uso evita N round-trip DB su pipeline batch.

_TIPO_PRESTAZIONE_ID_CACHE: int | None = None
_PRIORITA_DEFAULT_ID_CACHE: int | None = None


# Scopo: invalidate cache lookup per test / refactor seed amministrativi.
def invalidate_lookup_cache() -> None:
    global _TIPO_PRESTAZIONE_ID_CACHE, _PRIORITA_DEFAULT_ID_CACHE
    _TIPO_PRESTAZIONE_ID_CACHE = None
    _PRIORITA_DEFAULT_ID_CACHE = None


# Scopo: lookup id tipo_prestazione APPROVAZIONE_PREZZO con cache modulo.
def _get_tipo_prestazione_id() -> int:
    global _TIPO_PRESTAZIONE_ID_CACHE
    if _TIPO_PRESTAZIONE_ID_CACHE is None:
        _TIPO_PRESTAZIONE_ID_CACHE = resolve_config_id_by_codice_interno(
            "pratiche.tipi_prestazione",
            TIPO_PRESTAZIONE_CODICE,
            etichetta="Tipo prestazione",
            not_found_message=(
                f"Tipo prestazione '{TIPO_PRESTAZIONE_CODICE}' non configurato in "
                f"pratiche.tipi_prestazione. Richiesto seed Sprint E DB-E-2."
            ),
            function_name=f"{_FN}._get_tipo_prestazione_id",
        )
    return _TIPO_PRESTAZIONE_ID_CACHE


# Scopo: lookup id priorita pratica default (NORMALE) con cache modulo.
def _get_priorita_default_id() -> int:
    global _PRIORITA_DEFAULT_ID_CACHE
    if _PRIORITA_DEFAULT_ID_CACHE is None:
        _PRIORITA_DEFAULT_ID_CACHE = resolve_config_id_by_codice_interno(
            "config.priorita_pratiche",
            PRIORITA_DEFAULT_CODICE_INTERNO,
            etichetta="Priorita default",
            not_found_message=(
                f"Priorita default '{PRIORITA_DEFAULT_CODICE_INTERNO}' non trovata "
                f"in config.priorita_pratiche."
            ),
            function_name=f"{_FN}._get_priorita_default_id",
        )
    return _PRIORITA_DEFAULT_ID_CACHE


# ============================================================
# Workflow API pubbliche
# ============================================================


# Scopo: orchestratore sorgente-agnostico della richiesta L3. Crea la
#        pratica APPROVAZIONE_PREZZO (gia' APERTA), invia email
#        best-effort all'approver, ritorna pratica_id. Per preventivi/contratti
#        i caller pubblici `crea_richiesta_approvazione` e
#        `crea_richiesta_approvazione_contratto` arrivano qui con il proprio
#        `contesto` (emittente + soggetto + ruolo + BA del documento), il numero
#        documento per la descrizione, e `riga_id` per il meta.
#        Riga_id puo' essere None per preventivi (in create_riga il riga
#        non e' ancora noto; link_riga_a_pratica completa poi); per contratti
#        update_riga ha gia' il riga_id e lo passa subito.
@transaction.atomic
def _crea_richiesta_approvazione_impl(
    *,
    sorgente: str,
    documento_id: int,
    riga_id: int | None,
    numero_documento: str | None,
    articolo_id: str,
    contesto: dict[str, Any],
    istanza_utility_id: int | None,
    prezzo_resolver: Decimal | None,
    prezzo_manuale: Decimal,
    violazione: dict[str, Any],
    auth_user_id: int | None,
) -> int:
    cfg = _require_sorgente(sorgente)
    descrizione = (
        f"Richiesta approvazione prezzo riga {cfg['label_doc']} "
        f"{numero_documento or documento_id} - "
        f"violazione L2 {violazione.get('tipo_violazione')}: "
        f"{violazione.get('variazione_abs_pct')}% (max {violazione.get('limite_pct')}%)."
    )
    meta: dict[str, Any] = {
        # Nuove chiavi sorgente-agnostiche (refactor 2026-05-19).
        META_KEY_SORGENTE: sorgente,
        cfg["meta_key_doc"]: documento_id,
        # Chiave sorgente-specifica della riga (riga_preventivo_id /
        # riga_contratto_id). Puo' essere None alla creazione della pratica
        # e popolata dopo via `link_riga_a_pratica`.
        cfg["meta_key_riga"]: riga_id,
        "articolo_id": str(articolo_id),
        "prezzo_resolver": str(prezzo_resolver) if prezzo_resolver is not None else None,
        "prezzo_manuale": str(prezzo_manuale),
        "violazione": violazione,
        "richiedente_auth_user_id": auth_user_id,
    }

    pratica_id = crea_pratica(
        emittente_fiscale_id=contesto["emittente_fiscale_id"],
        tipo_prestazione_id=_get_tipo_prestazione_id(),
        soggetto_id=contesto["soggetto_id"],
        soggetto_ruolo_id=contesto["soggetto_ruolo_id"],
        istanza_utility_id=istanza_utility_id,
        billing_account_id=contesto["billing_account_id"],
        priorita_id=_get_priorita_default_id(),
        descrizione=descrizione,
        meta=meta,
    )

    # La pratica nasce gia' APERTA (crea_pratica): visibile in coda approver
    # senza transito aggiuntivo.

    # Email best-effort. Se template/recipient assenti -> log warning, no raise:
    # la pratica resta valida e visibile in coda anche senza email.
    _invia_email_richiesta_approvazione(
        pratica_id=pratica_id,
        emittente_fiscale_id=contesto["emittente_fiscale_id"],
        descrizione=descrizione,
        meta=meta,
    )

    return pratica_id


# Scopo: wrapper preventivi del workflow L3. Mantiene la firma originaria
#        Sprint E per back-compat con `preventivi_service._orchestrate_l3_request`
#        e i suoi test. Il riga_id non e' noto a questo punto (create_riga
#        avviene dopo): viene popolato post-create via `link_riga_a_pratica`.
@transaction.atomic
def crea_richiesta_approvazione(
    *,
    preventivo_id: int,
    articolo_id: str,
    prezzo_resolver: Decimal | None,
    prezzo_manuale: Decimal,
    violazione: dict[str, Any],
    auth_user_id: int | None,
) -> int:
    repo = PreventiviRepository()
    testata = testata_o_not_found(
        repo.get_preventivo, preventivo_id,
        code="E_PREV_NOT_FOUND", message="Preventivo non trovato.",
        id_name="preventivo_id", function_name=f"{_FN}.crea_richiesta_approvazione",
    )

    contesto = repo.resolve_contesto_pratica(preventivo_id)
    ErrorManager.require(
        contesto is not None,
        code="E_APPROVAZIONE_PREZZO_NON_AMMESSA",
        message=(
            "Impossibile derivare contesto pratica dal preventivo: serve un "
            "billing account valido con emittente fiscale."
        ),
        function_name=f"{_FN}.crea_richiesta_approvazione",
    )
    assert contesto is not None

    return _crea_richiesta_approvazione_impl(
        sorgente=META_SORGENTE_PREVENTIVO,
        documento_id=preventivo_id,
        riga_id=None,  # popolato dopo da link_riga_a_pratica
        # ⚠️ La testata del preventivo ha `numero` (`PreventivoDetailRow`), non
        #    `numero_documento`: fino al 2026-10-09 si leggeva la chiave che non
        #    esiste, e la pratica si descriveva con l'id interno (trovato da mypy).
        numero_documento=testata.get("numero"),
        articolo_id=articolo_id,
        contesto=contesto,
        istanza_utility_id=testata.get("istanza_utility_id"),
        prezzo_resolver=prezzo_resolver,
        prezzo_manuale=prezzo_manuale,
        violazione=violazione,
        auth_user_id=auth_user_id,
    )


# Scopo: wrapper contratti del workflow L3 (refactor 2026-05-19 BE porting
#        gate riga contratti). Speculare a `crea_richiesta_approvazione`
#        preventivi. Per create_riga: riga_id=None (link post-create);
#        per update_riga: riga_id noto subito, passa direttamente.
@transaction.atomic
def crea_richiesta_approvazione_contratto(
    *,
    contratto_id: int,
    riga_id: int | None,
    articolo_id: str,
    prezzo_resolver: Decimal | None,
    prezzo_manuale: Decimal,
    violazione: dict[str, Any],
    auth_user_id: int | None,
) -> int:
    from apps.vendite.db.contratti_repository import ContrattiRepository
    repo = ContrattiRepository()
    testata = testata_o_not_found(
        repo.get_contratto, contratto_id,
        code="E_VENDITE_NOT_FOUND", message="Contratto non trovato.",
        id_name="contratto_id", function_name=f"{_FN}.crea_richiesta_approvazione_contratto",
    )

    contesto = repo.resolve_contesto_pratica(contratto_id)
    ErrorManager.require(
        contesto is not None,
        code="E_APPROVAZIONE_PREZZO_NON_AMMESSA",
        message=(
            "Impossibile derivare contesto pratica dal contratto: serve un "
            "billing account valido con emittente fiscale."
        ),
        function_name=f"{_FN}.crea_richiesta_approvazione_contratto",
    )
    assert contesto is not None

    return _crea_richiesta_approvazione_impl(
        sorgente=META_SORGENTE_CONTRATTO,
        documento_id=contratto_id,
        riga_id=riga_id,
        numero_documento=testata.get("numero"),
        articolo_id=articolo_id,
        contesto=contesto,
        # Contratti hanno istanza_utility_id NOT NULL sul header (a differenza
        # dei preventivi). Coerente con la pratica APPROVAZIONE_PREZZO che
        # eredita il riferimento operativo.
        istanza_utility_id=testata.get("istanza_utility_id"),
        prezzo_resolver=prezzo_resolver,
        prezzo_manuale=prezzo_manuale,
        violazione=violazione,
        auth_user_id=auth_user_id,
    )


# Scopo: wrapper offerte del workflow L3 (refactor 2026-06-01, gate L1/L2/L3
#        sulle offerte). Speculare a `crea_richiesta_approvazione_contratto`.
#        L'eccezione offerta porta `prezzo_unitario` manuale come la riga
#        contratto; `riga_id` qui e' l'id dell'eccezione (noto subito, l'init
#        nel service avviene post-create_eccezione → link via riga_id).
@transaction.atomic
def crea_richiesta_approvazione_offerta(
    *,
    offerta_id: int,
    riga_id: int | None,
    articolo_id: str,
    prezzo_resolver: Decimal | None,
    prezzo_manuale: Decimal,
    violazione: dict[str, Any],
    auth_user_id: int | None,
) -> int:
    from apps.vendite.db.offerte_repository import OfferteRepository
    repo = OfferteRepository()
    testata = testata_o_not_found(
        repo.get_offerta, offerta_id,
        code="E_VENDITE_NOT_FOUND", message="Offerta non trovata.",
        id_name="offerta_id", function_name=f"{_FN}.crea_richiesta_approvazione_offerta",
    )

    contesto = repo.resolve_contesto_pratica(offerta_id)
    ErrorManager.require(
        contesto is not None,
        code="E_APPROVAZIONE_PREZZO_NON_AMMESSA",
        message=(
            "Impossibile derivare contesto pratica dall'offerta: serve un "
            "billing account valido con emittente fiscale."
        ),
        function_name=f"{_FN}.crea_richiesta_approvazione_offerta",
    )
    assert contesto is not None

    return _crea_richiesta_approvazione_impl(
        sorgente=META_SORGENTE_OFFERTA,
        documento_id=offerta_id,
        riga_id=riga_id,
        numero_documento=testata.get("codice"),
        articolo_id=articolo_id,
        contesto=contesto,
        istanza_utility_id=testata.get("istanza_utility_id"),
        prezzo_resolver=prezzo_resolver,
        prezzo_manuale=prezzo_manuale,
        violazione=violazione,
        auth_user_id=auth_user_id,
    )


# Scopo: approva la richiesta su una riga PENDING. Verifica permesso azione
#        approva_prezzo, UPDATE riga -> APPROVED, chiude pratica con nota
#        interna OK. Transazione atomica.
#
#        Parametro `sorgente` (refactor 2026-05-19 sorgente-agnostico):
#        determina la tabella riga (vendite.preventivi_righe o
#        vendite.contratti_righe). Default `preventivo` per back-compat
#        con i call site Sprint E. L'endpoint contratti
#        (/righe-contratto/<id>/approva-prezzo/) passa META_SORGENTE_CONTRATTO.
@transaction.atomic
def approva(
    *,
    riga_id: int,
    auth_user_id: int | None,
    nota: str | None = None,
    sorgente: str = META_SORGENTE_PREVENTIVO,
) -> dict[str, Any]:
    _require_sorgente(sorgente)

    # Permesso PRIMA del lookup riga: evita di leakare informazioni
    # sull'esistenza/stato di una riga a chi non ha autorizzazione.
    _check_permesso_approva_prezzo(auth_user_id, function_name=f"{_FN}.approva")

    riga = _get_riga_pending(
        riga_id, sorgente=sorgente, function_name=f"{_FN}.approva",
    )
    pratica_id = int(riga["pratica_approvazione_prezzo_id"])

    _update_riga_workflow(
        sorgente=sorgente,
        riga_id=riga_id,
        fields={"stato_approvazione_prezzo": _STATO_RIGA_APPROVED},
    )

    cambia_stato_pratica(pratica_id, _STATO_PRATICA_CHIUSURA)
    contenuto_nota = (
        f"Approvato override prezzo. {nota.strip()}" if nota and nota.strip()
        else "Approvato override prezzo."
    )
    crea_nota_pratica(pratica_id, _NOTA_TIPO_INTERNA, contenuto_nota)

    return {"riga_id": riga_id, "pratica_id": pratica_id, "stato": _STATO_RIGA_APPROVED}


# Scopo: rifiuta la richiesta su una riga PENDING. Verifica permesso, UPDATE
#        riga -> REJECTED, chiude pratica con nota KO + motivazione (se data).
#        Il prezzo della riga NON viene riportato al resolver: spetta
#        all'utente decidere come correggere (ridurre sconto, annullare riga).
#
#        Parametro `sorgente`: come `approva`. La proiezione motivazione nel
#        meta della riga avviene su entrambe le tabelle (preventivi_righe.meta
#        e contratti_righe.meta sono entrambi jsonb).
@transaction.atomic
def rifiuta(
    *,
    riga_id: int,
    auth_user_id: int | None,
    motivazione: str | None = None,
    sorgente: str = META_SORGENTE_PREVENTIVO,
) -> dict[str, Any]:
    _require_sorgente(sorgente)

    # Permesso PRIMA del lookup riga (vedi approva: defense-in-depth).
    _check_permesso_approva_prezzo(auth_user_id, function_name=f"{_FN}.rifiuta")

    riga = _get_riga_pending(
        riga_id, sorgente=sorgente, function_name=f"{_FN}.rifiuta",
    )
    pratica_id = int(riga["pratica_approvazione_prezzo_id"])

    # Denormalizzo motivazione + autore + data nel meta della riga (caso d'uso
    # UX: il drawer riga preventivo/contratto mostra il motivo del rifiuto come
    # tooltip all'operatore senza dover navigare alla pratica). La nota interna
    # della pratica resta source-of-truth audit; questa e' una proiezione operativa.
    meta_riga = _coerce_meta_to_dict_safe(riga.get("meta"))
    meta_riga["approvazione_rifiuto"] = {
        "motivazione": (motivazione.strip() if motivazione and motivazione.strip() else None),
        "approver_user_id": auth_user_id,
        "rifiutato_il": now().isoformat(),
        "pratica_id": pratica_id,
    }

    _update_riga_workflow(
        sorgente=sorgente,
        riga_id=riga_id,
        fields={
            "stato_approvazione_prezzo": _STATO_RIGA_REJECTED,
            "meta": meta_riga,
        },
    )

    cambia_stato_pratica(pratica_id, _STATO_PRATICA_CHIUSURA)
    contenuto_nota = (
        f"Rifiutato override prezzo. Motivo: {motivazione.strip()}"
        if motivazione and motivazione.strip()
        else "Rifiutato override prezzo."
    )
    crea_nota_pratica(pratica_id, _NOTA_TIPO_INTERNA, contenuto_nota)

    return {"riga_id": riga_id, "pratica_id": pratica_id, "stato": _STATO_RIGA_REJECTED}


# Scopo: lista paginata della coda approvazioni prezzo per gli approver.
#        Riusa pratiche_service.cerca_pratiche con filtro tipo_prestazione +
#        stato APERTA. Scope emittente derivato dall'utente via PermissionResolver.
#        Fase 5.B1: ogni item arricchito con `can_approve`/`can_reject`/
#        `action_reason` per UX coda (FE disabilita bottoni + mostra tooltip).
def lista_coda(
    *,
    auth_user_id: int | None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    order_by: str | None = None,
    order_dir: str | None = None,
) -> dict[str, Any]:
    ErrorManager.require(
        auth_user_id is not None,
        code="E_PRICING_OVERRIDE_NON_AUTORIZZATO",
        message="Lista coda approvazioni richiede utente autenticato.",
        function_name=f"{_FN}.lista_coda",
    )
    assert auth_user_id is not None

    # L'ordinamento arriva dal chiamante ed e' validato contro la whitelist
    # delle pratiche (`PRATICHE_ORDER_COLS`), che questa coda attraversa via
    # `cerca_pratiche`. Fino al 2026-08-02 era INCHIODATO piu' sotto a
    # `data_insert desc`: la whitelist da 10 voci esisteva ma non era
    # raggiungibile da nessun percorso, quindi la lista non ordinava affatto —
    # il difetto classico «la costante e' a posto, e' il percorso che e' morto».
    # `None` conserva il default storico (data_insert desc), che resta anche il
    # preset dichiarato dal seed.
    # La validazione sta PRIMA della risoluzione utente/emittente: un parametro
    # sbagliato non deve costare due round-trip per essere respinto.
    ErrorManager.require(
        order_by is None or order_by in PRATICHE_ORDER_COLS,
        code="E_VENDITE_VALIDATION",
        message="Colonna di ordinamento non ammessa per la coda approvazioni.",
        detail=f"order_by={order_by!r}; ammesse: {sorted(PRATICHE_ORDER_COLS)}",
        function_name=f"{_FN}.lista_coda",
    )

    user = _get_user(auth_user_id)
    emittente_id = PermissionResolver.get_emittente_for_user(user)
    ErrorManager.require(
        emittente_id is not None,
        code="E_APPROVAZIONE_PREZZO_NON_AMMESSA",
        message=(
            "Coda approvazioni richiede operatore con emittente fiscale assegnato. "
            "Admin globale: usare scope emittente esplicito."
        ),
        function_name=f"{_FN}.lista_coda",
    )
    assert emittente_id is not None

    risultati, total = cerca_pratiche(
        emittente_fiscale_id=emittente_id,
        tipo_prestazione_id=_get_tipo_prestazione_id(),
        stato_codice_interno=_STATO_PRATICA_INIZIALE,
        limit=limit,
        offset=offset,
        order_by=order_by or "data_insert",
        order_dir=order_dir or "desc",
    )
    # Capability per riga (Fase 5.B1). Permesso utente calcolato UNA volta
    # (i check non dipendono dalla riga); per-item solo la verifica linkability
    # con riga_preventivo_id presente nel meta della pratica.
    user_can_act = _user_can_approve_or_reject(user)
    for item in risultati:
        item.update(_capabilities_per_pratica(item, user_can_act=user_can_act))
    return {"results": risultati, "count": total, "limit": limit, "offset": offset}


# Scopo: helper Fase 5.B1. Ritorna True se l'utente puo' approvare/rifiutare
#        secondo permesso azione `approva_prezzo_override`. Superuser bypass.
def _user_can_approve_or_reject(user) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    return PermissionResolver.check_azione(user, AZIONE_PROCESSO)


# Scopo: helper Fase 5.B1. Calcola capability di riga + reason i18n key.
#        Reason possibili (codici stabili esportati come costanti modulo,
#        traduzione lato FE):
#          - PERMESSO_MANCANTE  → utente senza azione approva_prezzo_override.
#            ⚠️ Dall'endpoint della coda NON arriva: la view chiede la stessa
#            azione (`get_permission`), e chi non ce l'ha riceve 403 prima di
#            vedere una riga. Il ramo resta perche' la capability si calcola dal
#            permesso, non dalla porta da cui si e' entrati: `lista_coda` e' un
#            service, e un chiamante che non passa da quella view (o una coda
#            aperta un giorno anche a chi legge soltanto) deve ricevere bottoni
#            spenti col motivo, non accesi (brief-be-verifica-documentazione-api
#            §B11, 2026-10-21).
#          - RIGA_NON_LINKATA   → META_KEY_RIGA_PREVENTIVO_ID assente nel meta
#            (pratica legacy o crash post-create_riga)
#          - None               → can_approve/can_reject = True
def _capabilities_per_pratica(pratica: dict[str, Any], *, user_can_act: bool) -> dict[str, Any]:
    # Sorgente derivata dal meta (fallback preventivo per pratiche legacy
    # Sprint E iniziale senza `sorgente`). Esposta in TUTTI i branch (anche
    # denied) per coerenza FE: il router endpoint approva/rifiuta usa sempre
    # `sorgente` per scegliere /righe/<id>/.. vs /righe-contratto/<id>/..
    meta = _coerce_meta_to_dict_safe(pratica.get("meta"))
    sorgente_raw = meta.get(META_KEY_SORGENTE) or META_SORGENTE_PREVENTIVO
    cfg = _SORGENTE_CONFIG.get(sorgente_raw)
    # Sorgente sconosciuta: trattata come `RIGA_NON_LINKATA` (UI bottoni
    # disabilitati). Esponiamo comunque la chiave `sorgente_raw` cosi' il
    # FE puo' loggare/segnalare anche il valore corrotto. Nessuna sorgente
    # nei branch denied dove user_can_act=False (la coda mostra l'item;
    # l'UI usa sorgente solo per i bottoni attivi).
    if cfg is None:
        logger.warning(
            "approvazioni_prezzo.sorgente_sconosciuta pratica_id=%s sorgente=%r — "
            "bottoni UI disabilitati.",
            pratica.get("id"), sorgente_raw,
        )
        return {
            "can_approve": False,
            "can_reject": False,
            "action_reason": ACTION_REASON_RIGA_NON_LINKATA,
            "sorgente": sorgente_raw,
        }
    if not user_can_act:
        return {
            "can_approve": False,
            "can_reject": False,
            "action_reason": ACTION_REASON_PERMESSO_MANCANTE,
            "sorgente": sorgente_raw,
        }
    riga_key = cfg["meta_key_riga"]
    # Check `is not None` esplicito: 0 e' un id invalido in PG (sequence
    # parte da 1), ma volere "any not None" e' piu' corretto del falsy `or`
    # (B3). ⛔ Nessun ripiego sulla chiave `riga_id` dello sprint E iniziale:
    # nessun writer la scrive piu' nel meta (le chiavi vive sono in
    # `_approvazioni_prezzo_constants`), e un `if` che tiene «valida» una
    # forma che il modello non produce e' software vivo per dati morti
    # (analisi-software-per-dati-morti §2.2, tolto il 2026-09-12).
    riga_id = meta.get(riga_key)
    if riga_id is None:
        # Pratica APPROVAZIONE_PREZZO senza riga linkata: e' una pratica
        # creata male (bug applicativo o crash post-create_riga prima del
        # link_riga_a_pratica). Loggo warning per visibilita' BE-side: lato
        # UI il bottone resta disabilitato col tooltip i18n, ma senza log
        # l'admin non saprebbe che esiste un dato corrotto da pulire.
        logger.warning(
            "approvazioni_prezzo.riga_non_linkata pratica_id=%s sorgente=%s — "
            "meta privo di '%s'. UI bottoni disabilitati.",
            pratica.get("id"), sorgente_raw, riga_key,
        )
        return {
            "can_approve": False,
            "can_reject": False,
            "action_reason": ACTION_REASON_RIGA_NON_LINKATA,
            "sorgente": sorgente_raw,
        }
    return {
        "can_approve": True,
        "can_reject": True,
        "action_reason": None,
        # Esposto al FE per il routing endpoint approva/rifiuta corretto
        # (/righe/<id>/.. preventivi vs /righe-contratto/<id>/.. contratti).
        "sorgente": sorgente_raw,
    }


# ============================================================
# Helper privati
# ============================================================


# Scopo: carica e valida una riga preventivo/contratto che deve essere PENDING.
#        Errore esplicito se riga non trovata, non PENDING o senza pratica.
#        Refactor 2026-05-19: parametro `sorgente` per dispatch tabella +
#        FK column. La query include anche `meta` (serve a rifiuta che
#        denormalizza la motivazione nel meta della riga).
def _get_riga_pending(
    riga_id: int, *, sorgente: str, function_name: str,
) -> dict[str, Any]:
    cfg = _require_sorgente(sorgente)
    # SQL dinamico controllato: tabella e colonna FK sono valori di whitelist
    # interna (`_SORGENTE_CONFIG`), nessun input utente raggiunge il rendering.
    sql = f"""
        SELECT id, {cfg["doc_fk_column"]} AS documento_id,
               stato_approvazione_prezzo,
               pratica_approvazione_prezzo_id,
               meta
          FROM {cfg["table"]}
         WHERE id = %s
    """  # noqa: S608 - whitelist interna
    with connection.cursor() as cursor:
        cursor.execute(sql, [riga_id])
        riga = row_to_dict(cursor)
    ErrorManager.require(
        riga is not None,
        code=cfg["error_code_not_found"],
        message=cfg["error_message_not_found"],
        detail=f"riga_id={riga_id}",
        function_name=function_name,
    )
    assert riga is not None

    ErrorManager.require(
        riga["stato_approvazione_prezzo"] == _STATO_RIGA_PENDING,
        code="E_APPROVAZIONE_PREZZO_NON_AMMESSA",
        message="La riga non e' in attesa di approvazione.",
        detail=f"stato_attuale={riga['stato_approvazione_prezzo']!r}",
        function_name=function_name,
    )
    ErrorManager.require(
        riga["pratica_approvazione_prezzo_id"] is not None,
        code="E_APPROVAZIONE_PREZZO_NON_AMMESSA",
        message="Riga PENDING senza pratica collegata: stato inconsistente.",
        function_name=function_name,
    )
    return riga


# Scopo: verifica che l'utente abbia l'azione processo approva_prezzo_override.
#        Bypass per superuser (ma esplicitamente, non implicito al check).
def _check_permesso_approva_prezzo(
    auth_user_id: int | None, *, function_name: str
) -> None:
    ErrorManager.require(
        auth_user_id is not None,
        code="E_PRICING_OVERRIDE_NON_AUTORIZZATO",
        message="Operazione approvazione richiede utente autenticato.",
        function_name=function_name,
    )
    assert auth_user_id is not None
    user = _get_user(auth_user_id)
    if getattr(user, "is_superuser", False):
        return
    abilitato = PermissionResolver.check_azione(user, AZIONE_PROCESSO)
    ErrorManager.require(
        abilitato,
        code="E_PRICING_OVERRIDE_NON_AUTORIZZATO",
        message=f"Permesso '{AZIONE_PROCESSO}' richiesto.",
        detail=f"Chiedi all'amministratore di abilitare l'azione '{AZIONE_PROCESSO}'.",
        function_name=function_name,
    )


# Scopo: best-effort invio email notifica al ruolo approver. Se recipient
#        non risolvibile / template assente / SMTP fallisce: log warning,
#        NO raise (la pratica resta valida e visibile in coda anche senza email).
#
#        Risoluzione recipient: per ora lookup parameter
#        VENDITE_APPROVAZIONE_PREZZO_RECIPIENT_EMAIL (scope user/group/emittente).
#        Se assente skip silenzioso. Future: risoluzione automatica via
#        binding profilo SUPER_ADMIN o gruppo "approver" - decisione di
#        modello organizzativo non in scope Sprint E.
def _invia_email_richiesta_approvazione(
    *,
    pratica_id: int,
    emittente_fiscale_id: int,
    descrizione: str,
    meta: dict[str, Any],
) -> None:
    import logging
    logger = logging.getLogger(__name__)

    destinatario = _risolvi_email_approver(emittente_fiscale_id)
    if not destinatario:
        logger.info(
            "Skip email approvazione prezzo pratica %s: recipient non configurato "
            "(parametro %s assente).",
            pratica_id, PARAM_EMAIL_RECIPIENT,
        )
        return

    try:
        EmailDispatchService().send_email(
            codice_template=EMAIL_TEMPLATE_CODICE,
            destinatario=destinatario,
            variabili={
                "pratica_id": pratica_id,
                "descrizione": descrizione,
                **meta,
            },
            pratica_id=pratica_id,
            # 🔴 QUI C'ERA `ambito="WORKFLOW_APPROVAZIONE_PREZZO"` (corretto il
            #    2026-09-05). ⛔ Non e' nel vocabolario di `config.email_log`
            #    (`chk_email_log_ambito`: SISTEMA / REPARTO / OPERATORE), quindi
            #    l'accodamento violava il vincolo — e l'except best-effort qui
            #    sotto ingoiava l'errore: la notifica all'approvatore NON e' mai
            #    partita, e a dirlo c'era solo una riga di log.
            # ⚠️ `ambito` classifica A CHI APPARTIENE l'email, non a che cosa
            #    serve: lo scopo lo porta gia' il template. Questa non appartiene
            #    a nessuna azienda — il destinatario e' l'indirizzo di un ruolo,
            #    preso da un parametro — quindi e' `SISTEMA`.
            ambito="SISTEMA",
        )
    except Exception as exc:  # best-effort, log + continue
        logger.warning(
            "Email notifica approvazione prezzo fallita per pratica %s: %s",
            pratica_id, exc,
        )


# Scopo: risolve l'email del ruolo approver via parameter dedicato.
#        Restituisce stringa (anche vuota = nessun recipient configurato)
#        o None se parameter assente.
#
#        IMPORTANTE: la fn DB `fn_get_parameter_full` solleva sempre
#        `RAISE EXCEPTION ERRORE_PARAMETRI_TABELLA` quando il code non
#        esiste in `config.parameters` (anche `get_defaults` lo fa, nonostante
#        il commento del repository — verificato: il loop Python non
#        intercetta perche' psycopg invalida la transazione al primo RAISE).
#        Per non rompere la transazione esterna del workflow L3 (la pratica
#        e' gia' stata creata e va committata anche se la mail non parte)
#        isoliamo la chiamata in un savepoint nested via
#        `transaction.atomic`: se RAISE → rollback solo del savepoint, la
#        transazione esterna sopravvive intatta.
def _risolvi_email_approver(emittente_fiscale_id: int) -> str | None:
    from apps.core.services.parameter_service import ParameterService
    try:
        with transaction.atomic():
            valore = ParameterService().get_parameter(
                PARAM_EMAIL_RECIPIENT,
                emittente_fiscale_id=emittente_fiscale_id,
            )
            if valore and str(valore).strip():
                return str(valore).strip()
    except Exception:  # parameter non configurato = skip email
        return None
    return None


# Scopo: arricchisce il meta della pratica con la chiave riga_*_id dopo che
#        la riga e' stata creata. La pratica viene creata PRIMA della riga
#        (per ottenere FK), quindi al momento della creazione il riga_id
#        non e' noto. Questo update permette all'approver di risalire alla
#        riga dalla coda (UI ApprovazioniPrezzoListView).
#        Refactor 2026-05-19: parametro `sorgente` per la chiave meta corretta
#        (`riga_preventivo_id` vs `riga_contratto_id`).
def link_riga_a_pratica(
    *, pratica_id: int, riga_id: int, sorgente: str = META_SORGENTE_PREVENTIVO,
) -> None:
    cfg = _require_sorgente(sorgente)

    repo = PraticheRepository()
    pratica = repo.get_pratica(pratica_id)
    if pratica is None:
        return  # pratica scomparsa: defensive, no raise
    # `meta` puo' arrivare come dict o stringa JSON (psycopg/repo dependent).
    # Senza normalize, `dict(<stringa>)` solleva ValueError generico che il
    # middleware traduce in E_VALIDATION_INPUT mascherando il vero contesto.
    meta = _coerce_meta_to_dict_safe(pratica.get("meta"))
    meta[cfg["meta_key_riga"]] = riga_id
    # Garantisce presenza di `sorgente` anche per pratiche legacy che fossero
    # arrivate qui senza (defensive: oggi `_crea_richiesta_approvazione_impl`
    # lo popola sempre).
    meta.setdefault(META_KEY_SORGENTE, sorgente)
    aggiorna_pratica(pratica_id, {"meta": meta})


# Scopo: lookup utente Django per check permessi. Estratto come helper
#        per consistenza con preventivi_service e per facilitare mocking.
def _get_user(auth_user_id: int):
    from django.contrib.auth import get_user_model
    user_model = get_user_model()
    try:
        return user_model.objects.get(pk=auth_user_id)
    except user_model.DoesNotExist:
        ErrorManager.raise_error(
            code="E_PRICING_OVERRIDE_NON_AUTORIZZATO",
            message="Utente non trovato.",
            detail=f"auth_user_id={auth_user_id}",
            function_name=f"{_FN}._get_user",
        )
