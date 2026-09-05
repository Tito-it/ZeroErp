# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade del REGISTRO DEI PROCESSI AUTOMATICI: elenco, dettaglio, corse,
#        stato dei sei presidi, e il verbo che crea l'utente tecnico di un
#        processo per un emittente.
# Note: ⭐ Sta in `apps/core` come il suo repository, e per la stessa ragione:
#        il roster serve anche a chi PRODUCE lavoro in `apps/vendite`, e le
#        chiamate laterali fra domini non si fanno. Chi lo ESPONE — le view di
#        `amm_software` — sta un anello piu' fuori.
#        ⛔ Il verbo NON tiene una copia dei guard: la fabbrica e'
#        `script.fn_crea_utente_tecnico`, che ne ha quattro e solleva codici
#        registrati. Qui si traduce e si passa. Duplicarli in Python vorrebbe
#        dire due sedi della stessa regola, e la seconda diverge.
#        Brief: work-in-progress/piano-be-fe-processi-automatici-identita-e-perimetro.md §6
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import LIST_MAX_LIMIT
from apps.core.db.processi_repository import ProcessiRepository
from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import (
    validate_enum_param,
    validate_order_params,
)
from apps.core.services.payload_helpers import translate_db_errors

_FN = "core.processi_service"
E_VALIDATION = "E_CORE_VALIDATION"

# 🔵 RIPIEGO DICHIARATO — richiesta DB-8 al team DB.
# Il codice giusto per «il processo indicato non e' nel registro» non esiste
# ancora a catalogo, e coniarlo e' un seed, non un'azione del backend.
# ⛔ Non si riusa `E_JOB_NON_TROVATO`: quello dice «il LAVORO in coda 42 non
#    esiste», che e' un'altra cosa — e un messaggio che parla del lavoro
#    sbagliato manda a cercare nel posto sbagliato.
# ⚠️ Fino ad allora un codice inesistente in URL risponde 400 con una frase
#    esatta invece di 404. E' il denominatore sicuro: nessuno raggiunge questo
#    endpoint se non digitando un indirizzo a mano, e la frase dice il vero.
#    Il giorno in cui `E_PROCESSO_NON_TROVATO` esiste, qui si cambia una riga.
E_NOT_FOUND = "E_CORE_VALIDATION"

# Vocabolari del registro: sono gli stessi `CHECK` di `dbops.processi`.
# ⚠️ Qui servono a rifiutare un FILTRO senza senso con un 400 parlante invece
#    di consegnare una lista vuota che sembra un dato. Non sono una seconda
#    definizione della classe di un processo: quella e' e resta a database.
_CLASSI = ("MANUTENZIONE", "AMMINISTRAZIONE", "DOMINIO")
_CANALI = ("PGAGENT", "COMMAND", "CODA")

_ORDER_AMMESSI = (
    "codice", "descrizione", "classe", "canale", "attivo", "ultimo_run",
)

# ⭐ Non c'e' nessun elenco dei codici che la fabbrica puo' sollevare, ed e'
#    voluto: `translate_db_errors` legge il codice dal campo STRUTTURATO
#    dell'eccezione e lo lascia passare com'e'. Un elenco qui sarebbe una copia
#    del catalogo che invecchia — e i quattro codici di
#    `fn_crea_utente_tecnico` hanno gia' la loro classe in
#    `error_policies_generated.py`, quindi arrivano al client con lo status
#    giusto senza che nessuno li nomini.


class ProcessiService:
    """Registro dei processi automatici: letture e creazione utente tecnico."""

    def __init__(self, repo: ProcessiRepository | None = None) -> None:
        self._repo = repo or ProcessiRepository()

    # Scopo: Elenco paginato dei processi, con i filtri del pannello.
    def list_processi(
        self,
        *,
        classe: str | None = None,
        canale: str | None = None,
        attivo: bool | None = None,
        search: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> dict[str, Any]:
        # ⚠️ Convenzione OFFSET-based, come ogni lista standard servita da
        #    `<ListaConfigurabile>`: e' lo store del frontend a dettarla, e un
        #    adattatore nel client sarebbe una traduzione in piu' da tenere
        #    allineata.
        fn = f"{_FN}.list_processi"
        limit = min(max(int(limit), 1), LIST_MAX_LIMIT)
        offset = max(int(offset), 0)
        validate_enum_param(
            classe, allowed=_CLASSI, nullable=True, error_code=E_VALIDATION,
            function_name=fn, param_name="classe",
        )
        validate_enum_param(
            canale, allowed=_CANALI, nullable=True, error_code=E_VALIDATION,
            function_name=fn, param_name="canale",
        )
        validate_order_params(
            order_by, order_dir, allowed_columns=_ORDER_AMMESSI, nullable=True,
            error_code=E_VALIDATION, function_name=fn,
        )
        righe, totale = self._repo.list_processi(
            classe=classe, canale=canale, attivo=attivo, search=search,
            limit=limit, offset=offset,
            order_by=order_by, order_dir=order_dir,
        )
        return {"count": totale, "results": righe}

    # Scopo: Dettaglio di un processo: la riga, i bersagli dichiarati, le
    #        identita' con cui lavora. 404 parlante se il codice non esiste.
    def get_processo(self, codice: str) -> dict[str, Any]:
        fn = f"{_FN}.get_processo"
        dettaglio = self._repo.get_processo(codice)
        ErrorManager.require(
            dettaglio is not None,
            code=E_NOT_FOUND,
            message="Il processo indicato non esiste nel registro.",
            detail=f"codice={codice!r}",
            function_name=fn,
        )
        assert dettaglio is not None
        # ⭐ Gli emittenti che questo processo NON serve viaggiano col
        #    dettaglio: e' la domanda che uno si fa guardando le identita'
        #    («ce ne sono due — e la terza azienda?»), e senza risposta si
        #    legge come «e' tutto a posto».
        dettaglio["emittenti_non_serviti"] = self._repo.emittenti_non_serviti(codice)
        return dettaglio

    # Scopo: Le corse recenti di un processo (tab «Ultimi run» del drawer).
    def list_run(
        self, codice: str, *, limit: int = DEFAULT_LIMIT, offset: int = 0,
    ) -> dict[str, Any]:
        limit = min(max(int(limit), 1), LIST_MAX_LIMIT)
        offset = max(int(offset), 0)
        righe, totale = self._repo.list_run_processo(
            codice, limit=limit, offset=offset,
        )
        return {"count": totale, "results": righe}

    # Scopo: Lo stato dei sei presidi, in un round-trip.
    # ⭐ La NATURA di ogni presidio («deve restare vuota» / «registro di debito»)
    #    arriva dal commento della vista a database, non da un elenco qui: e'
    #    il team DB che la dichiara, ed e' giusto che a dirla sia una sede sola.
    def stato_presidi(self) -> dict[str, Any]:
        presidi = self._repo.stato_presidi()
        return {
            "presidi": presidi,
            # Il numero che si guarda per primo: quanti presidi hanno righe.
            "con_righe": sum(1 for p in presidi if p["conteggio"] > 0),
        }

    # Scopo: Crea l'utente tecnico di un processo PER UN EMITTENTE, chiamando la
    #        fabbrica di dominio. Ritorna l'`auth_user_id` creato.
    #
    # ⛔ D-9: il sistema non SCEGLIE l'emittente, lo riceve da una persona. Qui
    #    non c'e' nessuna iterazione «per tutti gli emittenti scoperti»: sarebbe
    #    il sistema che concede perimetri da solo, che e' esattamente cio' che la
    #    decisione ha escluso.
    # ⛔ E non c'e' nessun controllo di eleggibilita' ricopiato: i quattro guard
    #    vivono dentro `fn_crea_utente_tecnico`. Qui si traduce l'errore e si
    #    lascia il codice del database, che e' registrato e sa spiegarsi.
    def crea_utente_tecnico(
        self, processo_codice: str, *, emittente_codice: str,
    ) -> dict[str, Any]:
        fn = f"{_FN}.crea_utente_tecnico"
        ErrorManager.require(
            bool(processo_codice) and bool(emittente_codice),
            code=E_VALIDATION,
            message="Processo ed emittente sono entrambi obbligatori.",
            function_name=fn,
        )
        with translate_db_errors(
            context={"op": fn},
            fallback_code=E_VALIDATION,
            fallback_message="Creazione dell'utente tecnico non riuscita.",
        ):
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT script.fn_crea_utente_tecnico(%s, %s)",
                    [processo_codice, emittente_codice],
                )
                row = cursor.fetchone()
        assert row is not None
        return {"auth_user_id": int(row[0])}
