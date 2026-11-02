# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
    "E_PRICING_SCONTO_ECCESSIVO",
    "E_PRICING_MAGGIORAZIONE_ECCESSIVA",
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
# ⚠️ Il marker di `E_PREZZO_LISTINO_NON_TROVATO` e' ritirato il 2026-10-07
#    (E-2 di analisi-be-difetti-emersi-verifica-doc-api-core): il codice e'
#    ritirato a catalogo dal 2026-08-19 e il ramo che lo sollevava e' tolto
#    dalla funzione DB (`20260819-10`), quindi il marker non poteva piu' scattare.
_KNOWN_DB_ERROR_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
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

    # Scopo: il contesto che finisce nel diario quando il resolver fallisce.
    #        Uno solo per i due metodi: sono gli stessi parametri, e un diario
    #        che li descrive in due modi e' un diario su cui non si puo'
    #        contare.
    #
    #        ⚠️ `classe_utenza_id` e `listino_versione_id_preferito` NON sono
    #        decorazione: sono i due parametri che cambiano lo STADIO a cui il
    #        resolver fallisce. Senza, due tentativi diversi lasciano un
    #        contesto IDENTICO e diventano indistinguibili a posteriori — e'
    #        l'ambiguita' che ha fatto perdere tempo al team DB il 2026-08-19
    #        (brief-be-pricing-codice-errore-fantasma.md §6.3).
    @staticmethod
    def _contesto_diario(
        *,
        articolo_str: str,
        uom_id: int,
        data_riferimento: date,
        ba_id: int,
        utility_id: int,
        classe_utenza_id: int | None,
        padre_str: str | None,
        listino_versione_id_preferito: int | None,
    ) -> dict[str, Any]:
        return {
            "articolo_id": articolo_str,
            "uom_id": uom_id,
            "ba_id": ba_id,
            "utility_id": utility_id,
            "data_riferimento": data_riferimento.isoformat(),
            "articolo_padre_contesto": padre_str,
            "classe_utenza_id": classe_utenza_id,
            "listino_versione_id_preferito": listino_versione_id_preferito,
        }

    # Scopo: i guard sugli input dei due resolver — `resolve_prezzo` (guscio) e
    #        `resolve_prezzo_esito` (nucleo). Ritorna la coppia gia' normalizzata
    #        `(articolo_str, padre_str)`, che e' l'unico esito che i chiamanti
    #        usano oltre al fatto che non hanno sollevato.
    #
    #        ⭐ Estratto il 2026-08-19 alla SECONDA occorrenza identica (regola
    #        del 2, decisione DEC-7 del brief-ddt-righe-senza-prezzo): otto guard
    #        uguali in due metodi non sono due cose simili, sono la stessa cosa
    #        scritta due volte — e la forma del difetto che ne nasce e' sempre la
    #        stessa: una regola nuova entra in una copia sola.
    #
    #        ⚠️ QUI DENTRO NON ENTRA LA TRADUZIONE DEL `DatabaseError`, e non e'
    #        una dimenticanza: li' i due metodi DIFFERISCONO davvero. Il guscio
    #        traduce anche i codici del listino (`_KNOWN_DB_ERROR_MARKERS`), il
    #        nucleo non solleva quei codici perche' li restituisce come esito.
    #        Un helper che accentrasse anche quella riuscirebbe solo a rendere
    #        difficile vedere la differenza che conta.
    def _valida_input_resolver(
        self,
        *,
        articolo_id: UUID | str,
        uom_id: int,
        data_riferimento: date,
        ba_id: int,
        utility_id: int,
        emittente_soggetto_ruolo_id: int,
        classe_utenza_id: int | None,
        articolo_padre_contesto: UUID | str | None,
        listino_versione_id_preferito: int | None,
    ) -> tuple[str, str | None]:
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
        if listino_versione_id_preferito is not None:
            self._v.guard_positive_int(
                listino_versione_id_preferito, field="listino_versione_id_preferito",
            )
        # Validazione articolo_padre_contesto opzionale (modello unificato BoM
        # 2026-05-13): se fornito attiva lo STADIO BUNDLE del resolver DB.
        padre_str: str | None = None
        if articolo_padre_contesto is not None:
            padre_str = self._v.require_uuid(
                {"articolo_padre_contesto": articolo_padre_contesto},
                "articolo_padre_contesto",
            )
        return articolo_str, padre_str

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
        listino_versione_id_preferito: int | None = None,
    ) -> dict[str, Any]:
        articolo_str, padre_str = self._valida_input_resolver(
            articolo_id=articolo_id,
            uom_id=uom_id,
            data_riferimento=data_riferimento,
            ba_id=ba_id,
            utility_id=utility_id,
            emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
            classe_utenza_id=classe_utenza_id,
            articolo_padre_contesto=articolo_padre_contesto,
            listino_versione_id_preferito=listino_versione_id_preferito,
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
                listino_versione_id_preferito=listino_versione_id_preferito,
            )
        except DatabaseError as exc:
            ErrorManager.raise_from_database_error(
                exc,
                known_markers=_KNOWN_DB_ERROR_MARKERS,
                fallback_code=E_VENDITE_PRICING_FAILED,
                message="Impossibile risolvere il prezzo listino.",
                function_name="pricing_service.resolve",
                context=self._contesto_diario(
                    articolo_str=articolo_str,
                    uom_id=uom_id,
                    data_riferimento=data_riferimento,
                    ba_id=ba_id,
                    utility_id=utility_id,
                    classe_utenza_id=classe_utenza_id,
                    padre_str=padre_str,
                    listino_versione_id_preferito=listino_versione_id_preferito,
                ),
            )

    # =================================================================
    # BE-A3 — resolver «a esito» (nucleo, non solleva quando non risolve)
    # =================================================================

    # Scopo: Risolve il prezzo come `resolve_prezzo`, ma sul NUCLEO: quando il
    #        prezzo non e' risolvibile **non solleva** — torna il dict con
    #        `prezzo_finale = None` e il motivo in `esito_codice`.
    #
    #        A CHI SERVE, e perche' non e' il default. Il DDT e' l'unico
    #        documento dove il prezzo mancante non e' un errore: una riga in
    #        conto visione o in ri-consegna nasce senza prezzo, e pretenderlo
    #        significa impedire di salvarla. Ordini, preventivi, contratti e
    #        offerte continuano a chiamare `resolve_prezzo`: li' il prezzo
    #        assente e' un difetto, e il RAISE e' l'unica cosa che lo ferma.
    #
    #        ⚠️ IL `try/except DatabaseError` RESTA, e non e' ridondante: il
    #        nucleo non solleva per «prezzo non risolto», ma solleva ancora per
    #        parametri invalidi (`E_PARAMETRO_INVALIDO`) — e quella eccezione
    #        va tradotta come sempre, o arriva al client come guasto generico.
    #
    #        Riferimento: brief-ddt-righe-senza-prezzo §16 BE-A3, DEC-1, DEC-2.
    def resolve_prezzo_esito(
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
        listino_versione_id_preferito: int | None = None,
    ) -> dict[str, Any]:
        articolo_str, padre_str = self._valida_input_resolver(
            articolo_id=articolo_id,
            uom_id=uom_id,
            data_riferimento=data_riferimento,
            ba_id=ba_id,
            utility_id=utility_id,
            emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
            classe_utenza_id=classe_utenza_id,
            articolo_padre_contesto=articolo_padre_contesto,
            listino_versione_id_preferito=listino_versione_id_preferito,
        )

        try:
            return self._repo.resolve_prezzo_listino_v2_esito(
                articolo_id=articolo_str,
                uom_id=uom_id,
                data_riferimento=data_riferimento,
                ba_id=ba_id,
                utility_id=utility_id,
                emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
                classe_utenza_id=classe_utenza_id,
                articolo_padre_contesto=padre_str,
                listino_versione_id_preferito=listino_versione_id_preferito,
            )
        except DatabaseError as exc:
            ErrorManager.raise_from_database_error(
                exc,
                known_markers=_KNOWN_DB_ERROR_MARKERS,
                fallback_code=E_VENDITE_PRICING_FAILED,
                message="Impossibile risolvere il prezzo listino.",
                function_name="pricing_service.resolve_esito",
                context=self._contesto_diario(
                    articolo_str=articolo_str,
                    uom_id=uom_id,
                    data_riferimento=data_riferimento,
                    ba_id=ba_id,
                    utility_id=utility_id,
                    classe_utenza_id=classe_utenza_id,
                    padre_str=padre_str,
                    listino_versione_id_preferito=listino_versione_id_preferito,
                ),
            )
