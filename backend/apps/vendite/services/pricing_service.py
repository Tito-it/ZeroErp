# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service wrapper per il resolver prezzi v5 (pricing v5). Espone
#        `resolve_prezzo()`, wrapper 1:1 su `fn_resolve_prezzo_listino_v2`
#        (resolver bundle-aware 3 stadi).
#
#        Il resolver vive interamente nel DB (filosofia DB-first). Il service
#        fa SOLO: validazione input tipizzata, derivazione
#        emittente_soggetto_ruolo_id dal JWT quando necessario (vedi pattern
#        in pricing_api, NON qui — il service riceve gia' l'id risolto), e
#        traduzione dei P0001 applicativi in ServiceError con il codice
#        originale del DB (MESSAGE-based parsing controllato).
#
#        Note: il legacy `resolve_prezzo_composito` (BoM ibrido A/B1/B2
#        pre-modello-unificato) e' stato rimosso col cleanup 2026-05-14
#        post-Fase H. La distinzione CASO A vs CASO B non ha piu' senso col
#        modello unificato (padre = SUM(figli × coeff_qta)). Path standard
#        preventivi/contratti: le fn DB
#        `fn_<sorgente>_riga_componenti_init/preview` chiamano internamente
#        `fn_resolve_prezzo_listino_v2(... p_articolo_padre_contesto)`.
#
#        Riferimento: sviluppo-listini-v5 §7 (resolver 3 stadi) + §8 (BoM).
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from django.db import DatabaseError

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator
from apps.vendite.db.pricing_repository import PricingRepository

__all__ = [
    "PricingService",
    "E_VENDITE_PRICING_FAILED",
    "PARAM_MAX_SCONTO_PCT",
    "PARAM_MAX_MAGGIORAZIONE_PCT",
    "L2_ERROR_CODES",
]


E_VENDITE_VALIDATION = "E_VENDITE_VALIDATION"

# Parametri L2 autorizzazioni prezzi (Sprint D). Centralizzati qui per
# evitare stringhe magic in service/view/test. Valori DB in
# config.parameters (seed CSV), default '0' = nessuna variazione ammessa.
PARAM_MAX_SCONTO_PCT = "VENDITE_MAX_SCONTO_PCT"
PARAM_MAX_MAGGIORAZIONE_PCT = "VENDITE_MAX_MAGGIORAZIONE_PCT"

# Codici errore L2 che il FE intercetta per banner inline (vs toast standard).
L2_ERROR_CODES = (
    "E_PREV_SCONTO_ECCESSIVO",
    "E_PREV_MAGGIORAZIONE_ECCESSIVA",
)
# Codice generico per errori di dominio sollevati dal resolver DB.
# Il chiamante trova il codice DB originale in `detail` (es.
# "E_CATEGORIA_LISTINO_NON_MAPPATA: ..."). Non duplichiamo qui l'elenco
# dei 11 codici DB: sono gia' registrati in config.messaggi_errore.
E_VENDITE_PRICING_FAILED = "E_VENDITE_PRICING_FAILED"


# Codici noti sollevati dal resolver. Ogni voce e' una tupla di substring
# che devono TUTTE comparire nel MESSAGE per classificare l'errore — evita
# che un marker corto e comune (es. "non negoziato") catturi messaggi non
# correlati. Il template esatto vive in config.messaggi_errore (CSV):
# cambi lato DB richiedono aggiornamento coordinato qui.
#
# B4/F1 review 2026-04-15: match-singolo-substring era fragile a
# localizzazione (GUC myapp.user_language) e a template generici. Soluzione
# strutturale completa = esporre il codice in DETAIL/HINT del RAISE lato DB;
# fino a che quel refactor non e' fatto, usiamo match multi-substring stretto
# con test di regressione che protegge dai drift del CSV.
_KNOWN_DB_ERROR_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "E_PREZZO_LISTINO_NON_TROVATO",
        ("Nessun prezzo listino risolto per articolo",),
    ),
    (
        "E_CATEGORIA_LISTINO_NON_MAPPATA",
        ("Nessuna mappa categoria", "-> listino per utility"),
    ),
    (
        "E_PREZZO_LISTINO_RIGA_NON_TROVATA",
        ("Riga listino non trovata per articolo",),
    ),
    (
        "E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C",
        ("modalita' C:", "non negoziato"),
    ),
)


class PricingService:
    """Service wrapper per il resolver prezzi v5 (F2-BE-09 + F2-BE-10)."""

    def __init__(self) -> None:
        self._repo = PricingRepository()
        self._v = PayloadValidator(
            validation_code=E_VENDITE_VALIDATION,
            log_to_db=True,
            function_name="pricing_service",
        )

    # =================================================================
    # F2-BE-09 — resolver principale (3 stadi)
    # =================================================================

    # Scopo: Risolve il prezzo unitario per (articolo, uom, data, BA, utility,
    #        emittente, classe_utenza?). Valida input, delega al DB, converte
    #        P0001 di dominio in ServiceError preservando il codice originale
    #        quando riconosciuto.
    #
    #        Contratto caller: `emittente_soggetto_ruolo_id` e' derivato dal
    #        JWT dell'operatore (mapping 1-a-1) dal chiamante API/pipeline.
    def resolve_prezzo(
        self,
        *,
        articolo_id: UUID | str,
        uom_id: int,
        data_riferimento: date,
        ba_id: int,
        utility_id: int,
        emittente_soggetto_ruolo_id: int,
        classe_utenza_id: int | None = None,
        articolo_padre_contesto: UUID | str | None = None,
    ) -> dict[str, Any]:
        # require_uuid accetta solo payload dict; simulo un payload per
        # riutilizzare l'helper centralizzato del validator.
        articolo_str = self._v.require_uuid({"articolo_id": articolo_id}, "articolo_id")
        self._v.guard_positive_int(uom_id, field="uom_id")
        self._v.guard_positive_int(ba_id, field="ba_id")
        self._v.guard_positive_int(utility_id, field="utility_id")
        self._v.guard_positive_int(
            emittente_soggetto_ruolo_id, field="emittente_soggetto_ruolo_id"
        )
        ErrorManager.require(
            isinstance(data_riferimento, date),
            code=E_VENDITE_VALIDATION,
            message="data_riferimento deve essere un oggetto date.",
            context={"data_riferimento": str(data_riferimento)},
            log_to_db=True,
        )
        if classe_utenza_id is not None:
            self._v.guard_positive_int(classe_utenza_id, field="classe_utenza_id")
        # Validazione articolo_padre_contesto opzionale (modello unificato BoM
        # 2026-05-13): se fornito attiva lo STADIO BUNDLE del resolver DB.
        padre_str: str | None = None
        if articolo_padre_contesto is not None:
            padre_str = self._v.require_uuid(
                {"articolo_padre_contesto": articolo_padre_contesto},
                "articolo_padre_contesto",
            )

        try:
            return self._repo.resolve_prezzo_listino_v2(
                articolo_id=articolo_str,
                uom_id=uom_id,
                data_riferimento=data_riferimento,
                ba_id=ba_id,
                utility_id=utility_id,
                emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
                classe_utenza_id=classe_utenza_id,
                articolo_padre_contesto=padre_str,
            )
        except DatabaseError as exc:
            self._raise_pricing_error(
                exc,
                context={
                    "articolo_id": articolo_str,
                    "uom_id": uom_id,
                    "ba_id": ba_id,
                    "utility_id": utility_id,
                    "data_riferimento": data_riferimento.isoformat(),
                    "articolo_padre_contesto": padre_str,
                },
            )
            raise AssertionError("unreachable")  # pragma: no cover

    # =================================================================
    # Helpers privati
    # =================================================================

    # Scopo: Converte una DatabaseError del resolver (P0001 via
    #        fn_log_and_raise_error) in ServiceError. Riconosce i codici
    #        noti via substring-match sul MESSAGE — se match, propaga il
    #        codice originale; altrimenti usa E_VENDITE_PRICING_FAILED.
    def _raise_pricing_error(
        self,
        exc: DatabaseError,
        *,
        context: dict[str, Any],
    ) -> None:
        msg = str(exc)
        matched_code: str | None = None
        for code_candidate, markers in _KNOWN_DB_ERROR_MARKERS:
            if all(marker in msg for marker in markers):
                matched_code = code_candidate
                break
        code = matched_code or E_VENDITE_PRICING_FAILED
        ErrorManager.raise_error(
            code=code,
            message="Impossibile risolvere il prezzo listino.",
            detail=msg,
            context=context,
            cause=exc,
            log_to_db=True,
            function_name="pricing_service.resolve",
        )
