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
#           Crea pratica BOZZA -> APERTA, registra contesto violazione in meta,
#           invia email al ruolo approver (best-effort).
#        2) approva(riga_id) - endpoint POST /vendite/righe/<id>/approva-prezzo/
#           verifica permesso azione approva_prezzo, UPDATE riga
#           stato_approvazione_prezzo=APPROVED, chiude pratica con nota OK.
#        3) rifiuta(riga_id, motivazione) - endpoint POST .../rifiuta-prezzo/
#           UPDATE riga REJECTED, chiude pratica con nota KO + motivazione.
#        4) lista_coda() - endpoint GET /vendite/approvazioni-prezzo/
#           pratiche tipo APPROVAZIONE_PREZZO con stato APERTA, scope emittente.
# ------------------------------------------------------------

"""ApprovazioniPrezzoService — workflow L3 listini v5 §14.6."""

from decimal import Decimal
from typing import Any

from django.db import connection, transaction

from apps.core.services.email_service import EmailDispatchService
from apps.core.services.error_manager import ErrorManager
from apps.core.services.permissions_resolver import PermissionResolver
from apps.pratiche.db.pratiche_repository import PraticheRepository
from apps.pratiche.services.pratiche_service import (
    aggiorna_pratica,
    cambia_stato_pratica,
    cerca_pratiche,
    crea_nota_pratica,
    crea_pratica,
)
from apps.vendite.db.preventivi_repository import PreventiviRepository

_FN = "vendite.approvazioni_prezzo_service"

# Costanti dominio L3.
TIPO_PRESTAZIONE_CODICE = "APPROVAZIONE_PREZZO"
PRIORITA_DEFAULT_CODICE_INTERNO = "NORMALE"
AZIONE_PROCESSO = "approva_prezzo"
EMAIL_TEMPLATE_CODICE = "APPROVAZIONE_PREZZO_RICHIESTA"
PARAM_EMAIL_RECIPIENT = "VENDITE_APPROVAZIONE_PREZZO_RECIPIENT_EMAIL"

# Stati workflow pratica L3.
_STATO_PRATICA_INIZIALE = "APERTA"  # crea_pratica parte da BOZZA, transito immediato
_STATO_PRATICA_CHIUSURA = "CHIUSA"

# Stati workflow riga preventivo (DB-E-3 colonna stato_approvazione_prezzo).
_STATO_RIGA_PENDING = "PENDING"
_STATO_RIGA_APPROVED = "APPROVED"
_STATO_RIGA_REJECTED = "REJECTED"

# Note esito (tipi_nota seed: INTERNA visibile solo agli operatori).
_NOTA_TIPO_INTERNA = "INTERNA"


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
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM pratiche.tipi_prestazione WHERE codice = %s AND attivo = true",
                [TIPO_PRESTAZIONE_CODICE],
            )
            row = cursor.fetchone()
            ErrorManager.require(
                row is not None,
                code="E_CONFIG_MANCANTE",
                message=(
                    f"Tipo prestazione '{TIPO_PRESTAZIONE_CODICE}' non configurato in "
                    f"pratiche.tipi_prestazione. Richiesto seed Sprint E DB-E-2."
                ),
                function_name=f"{_FN}._get_tipo_prestazione_id",
            )
            assert row is not None
            _TIPO_PRESTAZIONE_ID_CACHE = int(row[0])
    return _TIPO_PRESTAZIONE_ID_CACHE


# Scopo: lookup id priorita pratica default (NORMALE) con cache modulo.
def _get_priorita_default_id() -> int:
    global _PRIORITA_DEFAULT_ID_CACHE
    if _PRIORITA_DEFAULT_ID_CACHE is None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM config.priorita_pratiche WHERE codice_interno = %s AND attivo = true",
                [PRIORITA_DEFAULT_CODICE_INTERNO],
            )
            row = cursor.fetchone()
            ErrorManager.require(
                row is not None,
                code="E_CONFIG_MANCANTE",
                message=(
                    f"Priorita default '{PRIORITA_DEFAULT_CODICE_INTERNO}' non trovata "
                    f"in config.priorita_pratiche."
                ),
                function_name=f"{_FN}._get_priorita_default_id",
            )
            assert row is not None
            _PRIORITA_DEFAULT_ID_CACHE = int(row[0])
    return _PRIORITA_DEFAULT_ID_CACHE


# ============================================================
# Workflow API pubbliche
# ============================================================


# Scopo: orchestra creazione richiesta approvazione L3 quando l'utente
#        preventiva oltre il limite L2 con flag richiesta_approvazione=true.
#        Pattern: crea pratica APERTA + nota interna con contesto + invia
#        email al ruolo approver (best-effort: se SMTP fallisce, pratica
#        resta valida e visibile in coda).
#
#        Restituisce pratica_id, da inserire poi nella riga preventivo
#        come pratica_approvazione_prezzo_id.
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
    testata = repo.get_preventivo(preventivo_id)
    ErrorManager.require(
        testata is not None,
        code="E_PREV_NOT_FOUND",
        message="Preventivo non trovato.",
        function_name=f"{_FN}.crea_richiesta_approvazione",
    )
    assert testata is not None

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

    descrizione = (
        f"Richiesta approvazione prezzo riga preventivo {testata.get('numero_documento') or preventivo_id} - "
        f"violazione L2 {violazione.get('tipo_violazione')}: "
        f"{violazione.get('variazione_abs_pct')}% (max {violazione.get('limite_pct')}%)."
    )
    meta = {
        "preventivo_id": preventivo_id,
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
        istanza_utility_id=testata.get("istanza_utility_id"),
        priorita_id=_get_priorita_default_id(),
        descrizione=descrizione,
        meta=meta,
    )

    # Transito immediato BOZZA -> APERTA per renderla visibile nella coda
    # approver. Se la transizione e' bloccata da un trigger di workflow,
    # solleva: meglio fail-fast che lasciare pratica in BOZZA invisibile.
    cambia_stato_pratica(pratica_id, _STATO_PRATICA_INIZIALE)

    # Email best-effort. Email ID risolto via template + recipient gestito
    # dal template stesso (placeholder: se template non esiste, log warning
    # e pratica resta valida — l'approver puo' visualizzarla in coda).
    _invia_email_richiesta_approvazione(
        pratica_id=pratica_id,
        emittente_fiscale_id=contesto["emittente_fiscale_id"],
        descrizione=descrizione,
        meta=meta,
    )

    return pratica_id


# Scopo: approva la richiesta su una riga PENDING. Verifica permesso azione
#        approva_prezzo, UPDATE riga -> APPROVED, chiude pratica con nota
#        interna OK. Transazione atomica.
@transaction.atomic
def approva(
    *,
    riga_id: int,
    auth_user_id: int | None,
    nota: str | None = None,
) -> dict[str, Any]:
    # Permesso PRIMA del lookup riga: evita di leakare informazioni
    # sull'esistenza/stato di una riga a chi non ha autorizzazione.
    _check_permesso_approva_prezzo(auth_user_id, function_name=f"{_FN}.approva")

    riga = _get_riga_pending(riga_id, function_name=f"{_FN}.approva")
    pratica_id = int(riga["pratica_approvazione_prezzo_id"])

    repo = PreventiviRepository()
    repo.update_riga(riga_id, stato_approvazione_prezzo=_STATO_RIGA_APPROVED)

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
@transaction.atomic
def rifiuta(
    *,
    riga_id: int,
    auth_user_id: int | None,
    motivazione: str | None = None,
) -> dict[str, Any]:
    # Permesso PRIMA del lookup riga (vedi approva: defense-in-depth).
    _check_permesso_approva_prezzo(auth_user_id, function_name=f"{_FN}.rifiuta")

    riga = _get_riga_pending(riga_id, function_name=f"{_FN}.rifiuta")
    pratica_id = int(riga["pratica_approvazione_prezzo_id"])

    repo = PreventiviRepository()
    repo.update_riga(riga_id, stato_approvazione_prezzo=_STATO_RIGA_REJECTED)

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
def lista_coda(
    *,
    auth_user_id: int | None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    ErrorManager.require(
        auth_user_id is not None,
        code="E_PREV_OVERRIDE_NON_AUTORIZZATO",
        message="Lista coda approvazioni richiede utente autenticato.",
        function_name=f"{_FN}.lista_coda",
    )
    assert auth_user_id is not None

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
        order_by="data_insert",
        order_dir="desc",
    )
    return {"results": risultati, "count": total, "limit": limit, "offset": offset}


# ============================================================
# Helper privati
# ============================================================


# Scopo: carica e valida una riga preventivo che deve essere PENDING.
#        Errore esplicito se riga non trovata, non PENDING o senza pratica.
def _get_riga_pending(riga_id: int, *, function_name: str) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, preventivo_id, stato_approvazione_prezzo,
                   pratica_approvazione_prezzo_id
              FROM vendite.preventivi_righe
             WHERE id = %s
            """,
            [riga_id],
        )
        cols = [c[0] for c in cursor.description]
        row = cursor.fetchone()
    ErrorManager.require(
        row is not None,
        code="E_PREV_RIGA_NOT_FOUND",
        message="Riga preventivo non trovata.",
        detail=f"riga_id={riga_id}",
        function_name=function_name,
    )
    assert row is not None
    riga = dict(zip(cols, row))

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


# Scopo: verifica che l'utente abbia l'azione processo approva_prezzo.
#        Bypass per superuser (ma esplicitamente, non implicito al check).
def _check_permesso_approva_prezzo(
    auth_user_id: int | None, *, function_name: str
) -> None:
    ErrorManager.require(
        auth_user_id is not None,
        code="E_PREV_OVERRIDE_NON_AUTORIZZATO",
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
        code="E_PREV_OVERRIDE_NON_AUTORIZZATO",
        message="Permesso 'approva_prezzo' richiesto.",
        detail="Chiedi all'amministratore di abilitare l'azione 'approva_prezzo'.",
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
            ambito="WORKFLOW_APPROVAZIONE_PREZZO",
        )
    except Exception as exc:  # noqa: BLE001 - best-effort, log + continue
        logger.warning(
            "Email notifica approvazione prezzo fallita per pratica %s: %s",
            pratica_id, exc,
        )


# Scopo: risolve l'email del ruolo approver via parameter dedicato.
#        Restituisce stringa (anche vuota = nessun recipient configurato)
#        o None se ParameterService non e' disponibile / parameter assente.
def _risolvi_email_approver(emittente_fiscale_id: int) -> str | None:
    from apps.core.services.parameter_service import ParameterService
    try:
        valore = ParameterService().get_parameter(
            PARAM_EMAIL_RECIPIENT,
            emittente_fiscale_id=emittente_fiscale_id,
        )
        if valore and str(valore).strip():
            return str(valore).strip()
    except Exception:  # noqa: BLE001 - parameter non configurato = skip
        return None
    return None


# Scopo: arricchisce il meta della pratica con riga_preventivo_id dopo che
#        la riga e' stata creata. La pratica viene creata PRIMA della riga
#        (per ottenere FK), quindi al momento della creazione il riga_id
#        non e' noto. Questo update permette all'approver di risalire alla
#        riga dalla coda (UI ApprovazioniPrezzoListView).
def link_riga_a_pratica(*, pratica_id: int, riga_id: int) -> None:
    repo = PraticheRepository()
    pratica = repo.get_pratica(pratica_id)
    if pratica is None:
        return  # pratica scomparsa: defensive, no raise
    meta = dict(pratica.get("meta") or {})
    meta["riga_preventivo_id"] = riga_id
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
            code="E_PREV_OVERRIDE_NON_AUTORIZZATO",
            message="Utente non trovato.",
            detail=f"auth_user_id={auth_user_id}",
            function_name=f"{_FN}._get_user",
        )
        raise AssertionError("unreachable")  # pragma: no cover
