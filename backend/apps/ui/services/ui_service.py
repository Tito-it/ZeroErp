# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service di lettura per personalizzazioni liste — espone:
#        - get_lista_config(): wrapper su `ui.fn_resolve_lista_config`
#          con derivazione automatica `emittente_fiscale_id` (1:1
#          operatore->emittente via PermissionResolver) e traduzione
#          DatabaseError P0001 in ServiceError.
#        - get_lista_config_per_video(): la stessa, piu' cio' che serve
#          solo alla schermata (`ricerca_full`, la casella di ricerca).
#        - get_catalogo(): catalogo colonne per la modale di
#          personalizzazione (filtra colonne BLOCCATE riusando
#          get_lista_config — single source of truth permessi).
#        - get_misure_pagina(): le misure «righe per pagina» e i due
#          default, per tutti i paginatori (catalogo `ui.misure_pagina`).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import DatabaseError

from apps.core.services import perimetro_emittente
from apps.core.services.error_manager import ErrorManager
from apps.core.services.permissions_resolver import PermissionResolver
from apps.ui.db.ui_repository import UiRepository

__all__ = [
    "UiService",
    "E_UI_LISTA_NON_TROVATA",
    "E_UI_GENERIC_FAILED",
    "E_UI_CHIAMATA_NON_VALIDA",
]


# Codici errore registrati in apps/core/services/error_policies.py.
E_UI_LISTA_NON_TROVATA = "E_UI_LISTA_NON_TROVATA"
E_UI_GENERIC_FAILED = "E_UI_GENERIC_FAILED"  # fallback per DatabaseError ignote
E_UI_CHIAMATA_NON_VALIDA = "E_UI_CHIAMATA_NON_VALIDA"  # contesto di sessione != utente

# Marker substring per riconoscere errori del DB. Stessa strategia di
# `pricing_service._KNOWN_DB_ERROR_MARKERS`: il codice originale e'
# preservato anche quando passa dal MESSAGE_TEXT del RAISE.
_KNOWN_DB_ERROR_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (E_UI_LISTA_NON_TROVATA, ("E_UI_LISTA_NON_TROVATA",)),
)


class UiService:
    """Facade lettura schema `ui`."""

    def __init__(self, repository: UiRepository | None = None) -> None:
        self._repo = repository or UiRepository()
        # Cache PER-ISTANZA delle risoluzioni di permesso/scope. Le view
        # costruiscono un `UiService` per richiesta, quindi vale una richiesta.
        # Serve perche' `get_catalogo` chiama `get_lista_config`: senza, la
        # stessa domanda sul perimetro andrebbe al database DUE volte per una
        # sola apertura di modale.
        self._perm_cache: dict[str, Any] = {}

    # Scopo: Risolve la configurazione effettiva di una lista per l'utente
    #        autenticato. Deriva `emittente_fiscale_id` 1:1 dall'utente via
    #        `PermissionResolver.get_emittente_for_user` (admin globale ->
    #        None: la fn DB lo gestisce). Cattura DatabaseError P0001 e
    #        traduce in ServiceError preservando il codice originale.
    def get_lista_config(
        self,
        user: Any,
        lista_codice: str,
        emittente_esplicito: Any = None,
    ) -> dict[str, Any]:
        emittente_fiscale_id = PermissionResolver.get_emittente_for_user(user)
        try:
            config = self._repo.resolve_lista_config(
                lista_codice=lista_codice,
                auth_user_id=user.id,
                emittente_fiscale_id=emittente_fiscale_id,
            )
        except DatabaseError as exc:
            ErrorManager.raise_from_database_error(
                exc,
                known_markers=_KNOWN_DB_ERROR_MARKERS,
                fallback_code=E_UI_GENERIC_FAILED,
                message="Errore risoluzione lista.",
                context={
                    "lista_codice": lista_codice,
                    "auth_user_id": user.id,
                },
                function_name="ui_service.get_lista_config",
            )

        # Difensivo: la fn DB solleva sempre E_UI_LISTA_NON_TROVATA via
        # fn_log_and_raise_error quando il codice non esiste; questo path
        # e' raggiungibile solo per regressioni del contratto fn.
        if not config:
            ErrorManager.raise_error(
                code=E_UI_LISTA_NON_TROVATA,
                message="Lista non trovata.",
                detail=f"codice lista: '{lista_codice}'",
                context={"lista_codice": lista_codice},
            )

        # Chiave ADDITIVA: chi non la legge non si accorge di niente.
        # ⚠️ E' una CONCLUSIONE, non un dato: `multi_emittente` (che resta
        # esposto com'e') dice cosa sa fare la LISTA, questa dice se in questo
        # momento, per QUESTO utente, la lista va sbarrata. La deriva il
        # backend perche' e' l'unico che conosce la cardinalita' dello scope:
        # farla ricalcolare al frontend creerebbe una seconda sede della stessa
        # verita', ed e' la duplicazione che poi diverge (P-2b).
        # ⚠️ L'ordine dei due termini NON e' indifferente, ed e' lo stesso di
        # `guard_lista_per_codice`: il flag e' gia' in memoria (arriva
        # nell'envelope), la cardinalita' dello scope costa una query. Scritto
        # al contrario, ogni apertura di una lista CERTIFICATA pagherebbe un
        # round-trip per un risultato che il flag da solo aveva gia' deciso.
        # ⭐ La formula sta nel building block, non qui: era scritta due volte
        #    (qui e nel cancello dell'endpoint) ed e' cresciuta di un termine —
        #    l'emittente esplicito — il 2026-09-01. Due copie della stessa
        #    conclusione sono il modo classico di far dire cose diverse al
        #    pannello e all'API.
        # ⚠️ `perimetro_emittente` con default `True` e non `bool(get(...))`: se
        #    la chiave mancasse — un risolutore piu' vecchio del backend —
        #    `bool(None)` direbbe «questa lista non ha perimetro» e APRIREBBE il
        #    cancello su tutte le liste insieme, in silenzio. Il verso prudente
        #    e' quello che chiude, ed e' anche il default della colonna.
        config["richiede_scelta_emittente"] = perimetro_emittente.richiede_scelta_emittente(
            user=user,
            multi_emittente=bool(config.get("multi_emittente")),
            perimetro_emittente=bool(config.get("perimetro_emittente", True)),
            emittente_esplicito=emittente_esplicito,
            cache=self._perm_cache,
        )

        return config

    # Scopo: La configurazione della lista per la SCHERMATA che la mostra
    #        (`GET /ui/liste/<codice>/config`): quella di `get_lista_config`
    #        piu' cio' che serve solo a video.
    # ⭐ `ricerca_full` (chiave ADDITIVA): la lista ha, per QUESTO utente,
    #    almeno una colonna in cui la ricerca libera cerca. Il frontend mostra
    #    la casella di ricerca solo se e' vera (Tid, 2026-09-23 — brief-be-
    #    ricerca-full-liste-residue §7-bis): una casella senza colonne accese
    #    non trova niente per costruzione (il BB mette `FALSE`). La lettura e'
    #    la stessa del BB (`colonne_ricerca_accese`): una seconda sede della
    #    stessa verita' sarebbe la duplicazione che poi diverge.
    # ⭐ La SOGLIA della ricerca (`ricerca_min_caratteri`) non si aggiunge qui:
    #    arriva gia' nel jsonb del risolutore, accanto a `pagina_dimensione`,
    #    letta dalla stessa colonna che legge il BB di ricerca
    #    (`soglia_ricerca`) — brief-db-be-fe-ricerca-soglia-per-lista §4-bis. Il
    #    frontend non manda un termine sotto quella soglia.
    # ⚠️ Qui e NON in `get_lista_config` (Tid, 2026-09-24): quella la leggono
    #    anche l'export (`export_helpers`) e la modale (`get_catalogo`), che
    #    la casella non la mostrano e pagherebbero una query per niente.
    # ⛔ La guardia di contesto (brief §12): la configurazione risponde per
    #    `user.id`, passato esplicito; `ricerca_full` e la ricerca vera per
    #    l'utente della GUC `app.current_user_id`. In una richiesta HTTP
    #    coincidono, ma il modello ammette che non coincidano (GUC vuota fuori
    #    da una richiesta, contesto aperto per un altro utente): allora la
    #    casella direbbe una cosa e la ricerca ne farebbe un'altra — le colonne
    #    sensibili, senza utente, non hanno grant — senza nessun errore. Non si
    #    sceglie una delle due fonti: una differenza fa rumore, con un errore
    #    TECNICO (l'operatore non ha niente da correggere).
    def get_lista_config_per_video(
        self,
        user: Any,
        lista_codice: str,
        emittente_esplicito: Any = None,
    ) -> dict[str, Any]:
        config = self.get_lista_config(
            user, lista_codice, emittente_esplicito=emittente_esplicito,
        )
        utente_guc = self._repo.utente_di_sessione()
        ErrorManager.require(
            utente_guc is not None and utente_guc == user.id,
            code=E_UI_CHIAMATA_NON_VALIDA,
            message=(
                "Chiamata non valida alla configurazione della lista: il "
                "contesto della richiesta non corrisponde all'utente."
            ),
            context={
                "lista_codice": lista_codice,
                "auth_user_id": user.id,
                "utente_di_sessione": utente_guc,
            },
            function_name="ui_service.get_lista_config_per_video",
            log_to_db=True,
        )
        config["ricerca_full"] = self._repo.ha_ricerca_full(lista_codice)
        return config

    # Scopo: Catalogo colonne per la modale di personalizzazione.
    #        Strategia: riusa get_lista_config() — il suo risultato
    #        contiene gia' tutte le colonne del catalogo non BLOCCATE
    #        (la fn DB Step 3 fa il merge automatico delle nuove colonne
    #        e Step 5 rimuove le BLOCCATE). Poi arricchisce con i metadati
    #        ricchi del catalogo (etichetta, gruppo, formato, ecc.) che la
    #        fn DB non espone. 2 round-trip totali, error handling
    #        centralizzato in get_lista_config.
    def get_catalogo(
        self,
        user: Any,
        lista_codice: str,
    ) -> dict[str, Any]:
        # 1. Risoluzione (404 + permessi) — riusato per non duplicare logica.
        config = self.get_lista_config(user, lista_codice)
        codici_visibili = {
            c.get("codice")
            for c in (config.get("colonne") or [])
            if c.get("codice") is not None
        }

        # 2. Metadati ricchi delle colonne (single query con JOIN).
        colonne_meta = self._repo.list_colonne_by_codice(lista_codice)

        # 3. Arricchimento per intersezione: tieni solo i metadati delle
        #    colonne effettivamente visibili al profilo utente. Le colonne
        #    sensibili senza grant cadono qui — la modale non puo' offrire
        #    l'attivazione di una colonna proibita.
        colonne_visibili = [
            c for c in colonne_meta if c["codice"] in codici_visibili
        ]

        return {"colonne": colonne_visibili}

    # Scopo: le misure «righe per pagina» ammesse e i due default
    #        (`COMPATTA`, `PAGINA`), lette dal catalogo `ui.misure_pagina`:
    #        la sede unica per DB, backend e frontend. Non dipendono
    #        dall'utente ne' dalla lista: il frontend le legge una volta per
    #        sessione. Un default mancante e' un errore del DB, non si ripiega.
    def get_misure_pagina(self) -> dict[str, Any]:
        return self._repo.get_misure_pagina()
