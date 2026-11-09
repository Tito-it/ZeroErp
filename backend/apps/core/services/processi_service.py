# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade del REGISTRO DEI PROCESSI AUTOMATICI: elenco, dettaglio, corse,
#        stato dei presidi, i verbi che creano o riaccendono l'utente tecnico di un
#        processo per un emittente e, dal 2026-09-15, «Esegui ora» su una
#        sveglia di deploy (accoda un lavoro `ESEGUI_PROCESSO`, non esegue).
# Note: ⭐ Sta in `apps/core` come il suo repository, e per la stessa ragione:
#        il roster serve anche a chi PRODUCE lavoro in `apps/vendite`, e le
#        chiamate laterali fra domini non si fanno. Chi lo ESPONE — le view di
#        `amm_software` — sta un anello piu' fuori.
#        ⛔ Il verbo NON tiene una copia dei guard: la fabbrica e'
#        `script.fn_crea_utente_tecnico`, che ne ha quattro e solleva codici
#        registrati. Qui si traduce e si passa. Duplicarli in Python vorrebbe
#        dire due sedi della stessa regola, e la seconda diverge.
#        Brief: work-done/piano-be-fe-processi-automatici-identita-e-perimetro.md §6
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.db import connection

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import limiti_pagina
from apps.core.db.presidi_repository import PresidiRepository
from apps.core.db.processi_repository import PROCESSI_SORT_COLUMNS, ProcessiRepository
from apps.core.services.avvio_manuale import (
    JOB_TYPE_ESEGUI_PROCESSO,
    chiave_idempotenza,
    motivi_esegui_ora,
    riga_sveglia,
)
from apps.core.services.coda_lavori.repository import (
    ORIGINE_API,
    RUN_AS_SISTEMA,
    CodaLavoriRepository,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import (
    validate_enum_param,
    validate_order_params,
)
from apps.core.services.payload_helpers import translate_db_errors
from apps.core.services.service_errors import E_CONFIG_MANCANTE, E_VALIDATION_INPUT
from apps.core.services.sveglie import sveglia_di_processo, sveglie_di_processo

_FN = "core.processi_service"
logger = logging.getLogger(__name__)
E_VALIDATION = "E_CORE_VALIDATION"
# Il codice del payload malformato di un VERBO (unit assente o non del
# processo) e' `E_VALIDATION_INPUT` (da `service_errors`): quello che il resto
# dei verbi di coda usa per la stessa condizione, con `field` nel context per
# accendere il campo a video.

# ✅ Il ripiego dichiarato e' RIENTRATO il 2026-09-05 (DB-8): il codice esiste a
# catalogo con classe `NON_TROVATO`, quindi un codice processo inesistente in URL
# risponde 404 e non piu' 400.
# ⛔ Non si riusa `E_JOB_NON_TROVATO`: quello dice «il LAVORO in coda 42 non
#    esiste», che e' un'altra cosa — e un messaggio che parla del lavoro
#    sbagliato manda a cercare nel posto sbagliato.
E_NOT_FOUND = "E_PROCESSO_NON_TROVATO"
# I limiti della scelta a mano: li solleva il guard di `dbops.processi_accensione`
# (codici a catalogo); qui servono per la capability e per il motivo del gesto
# «torna al default», che a DB non passa dal guard (e' una DELETE).
E_PROCESSO_NON_SPEGNIBILE = "E_PROCESSO_NON_SPEGNIBILE"
E_PROCESSO_SENZA_SVEGLIA = "E_PROCESSO_SENZA_SVEGLIA"
E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE = "E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE"
# Le chiavi i18n del motivo per cui «Accendi» e' spento (il tooltip del drawer,
# `bloccoAttivo(accensione, 'can_accendere', 'can_accendere')`).
_PREFISSO_ACCENDI_BLOCCO = "amministrazione.processi.accendi_blocco."
ACCENDI_REASON_KEY_PER_CODICE: dict[str, str] = {
    E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE: _PREFISSO_ACCENDI_BLOCCO + "non_accendibile_in_produzione",
    E_CONFIG_MANCANTE: _PREFISSO_ACCENDI_BLOCCO + "non_decidibile",
}
E_MOTIVO_OBBLIGATORIO = "E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO"

# Vocabolari del registro: sono gli stessi `CHECK` di `dbops.processi`.
# ⚠️ Qui servono a rifiutare un FILTRO senza senso con un 400 parlante invece
#    di consegnare una lista vuota che sembra un dato. Non sono una seconda
#    definizione della classe di un processo: quella e' e resta a database.
_CLASSI = ("MANUTENZIONE", "AMMINISTRAZIONE", "DOMINIO")
# ⚠️ `CODA_AUTOMATICA` e' il quarto dal 2026-09-05 (`chk_processi_canale`).
#    Ometterlo non darebbe un errore: darebbe un 400 su un filtro LEGITTIMO, e
#    la schermata non saprebbe mostrare i processi svegliati da una macchina.
_CANALI = ("PGAGENT", "COMMAND", "CODA", "CODA_AUTOMATICA")


# ⭐ Non c'e' nessun elenco dei codici che la fabbrica puo' sollevare, ed e'
#    voluto: `translate_db_errors` legge il codice dal campo STRUTTURATO
#    dell'eccezione e lo lascia passare com'e'. Un elenco qui sarebbe una copia
#    del catalogo che invecchia — e i quattro codici di
#    `fn_crea_utente_tecnico` hanno gia' la loro classe in
#    `error_policies_generated.py`, quindi arrivano al client con lo status
#    giusto senza che nessuno li nomini.


# Scopo: LA TESTATA DEI PRESIDI — i tre numeri che si guardano per primi,
#        letti dalle righe che il repository consegna: quanti presidi, quanti
#        ACCESI (hanno righe), quanti NON LETTI (hanno un errore).
#
# ⭐ E' UNA funzione perche' ha DUE lettori (regola del 2, ok Tid 2026-09-18):
#    il pannello «Processi automatici» (`stato_presidi`) e il pallino della
#    topbar (`conteggi_presidi`). Erano due `sum(...)` di una riga ciascuno, e
#    proprio per questo si sarebbero ricopiati: il predicato «chiede un occhio»
#    e' la cosa che il pallino e il pannello devono dire IDENTICA, e due copie
#    smettono di dirla identica alla prima modifica.
# ⚠️ `con_righe` conta i presidi ACCESI, e un presidio NON LETTO non e' uno di
#    quelli — ma non e' nemmeno «a posto»: lo conta `non_letti`. Sommarlo agli
#    accesi direbbe che c'e' un guasto dove c'e' una cecita', e tacerlo sarebbe
#    peggio.
def _testata_presidi(presidi: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "totale": len(presidi),
        # Il numero che si guarda per primo: quanti presidi hanno righe.
        "con_righe": sum(1 for p in presidi if (p.get("conteggio") or 0) > 0),
        "non_letti": sum(1 for p in presidi if p.get("errore")),
    }


class ProcessiService:
    """Registro dei processi automatici: letture, utente tecnico, «Esegui ora»."""

    def __init__(
        self,
        repo: ProcessiRepository | None = None,
        presidi: PresidiRepository | None = None,
        coda: CodaLavoriRepository | None = None,
    ) -> None:
        self._repo = repo or ProcessiRepository()
        # ⭐ I presidi hanno un lettore LORO dal 2026-09-10: non sono i presidi
        #    «dei processi», sono il catalogo intero — e li leggono in due, questa
        #    schermata e il digest.
        self._presidi = presidi or PresidiRepository()
        # La coda generica: «Esegui ora» ACCODA, e la capability nel dettaglio
        # legge i lavori vivi per unit. Iniettabile per i test.
        self._coda = coda or CodaLavoriRepository()

    # Scopo: Elenco paginato dei processi, con i filtri del pannello.
    def list_processi(
        self,
        *,
        classe: str | None = None,
        canale: str | None = None,
        vivo: bool | None = None,
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
        limit, offset = limiti_pagina(limit, offset)
        validate_enum_param(
            classe, allowed=_CLASSI, nullable=True, error_code=E_VALIDATION,
            function_name=fn, param_name="classe",
        )
        validate_enum_param(
            canale, allowed=_CANALI, nullable=True, error_code=E_VALIDATION,
            function_name=fn, param_name="canale",
        )
        validate_order_params(
            order_by, order_dir, allowed_columns=frozenset(PROCESSI_SORT_COLUMNS), nullable=True,
            error_code=E_VALIDATION, function_name=fn,
        )
        righe, totale = self._repo.list_processi(
            classe=classe, canale=canale, vivo=vivo, search=search,
            limit=limit, offset=offset,
            order_by=order_by, order_dir=order_dir,
        )
        return {"count": totale, "results": righe}

    # Scopo: I vocabolari dei filtri del pannello (classe, canale), per il
    #        client. Sono `_CLASSI` e `_CANALI`, cioe' le stesse costanti con
    #        cui `list_processi` rifiuta un filtro: il guardrail
    #        `test_coda_lavori_tipi_handler_guardrail` le tiene uguali ai CHECK
    #        di `dbops.processi`.
    # ⛔ Esiste perche' il frontend NON ne tenga una terza copia (2026-11-09):
    #    la sua, scritta a mano e senza presidio, non aveva `CODA_AUTOMATICA`,
    #    e i processi svegliati da una macchina non si potevano filtrare.
    def vocabolari_filtri(self) -> dict[str, list[str]]:
        return {"classi": list(_CLASSI), "canali": list(_CANALI)}

    # Scopo: Dettaglio di un processo: la riga, i bersagli dichiarati, le
    #        identita' con cui lavora. 404 parlante se il codice non esiste.
    def get_processo(self, codice: str) -> dict[str, Any]:
        dettaglio = self._require_processo(codice, fn=f"{_FN}.get_processo")
        # ⭐ Gli emittenti che questo processo NON serve viaggiano col
        #    dettaglio: e' la domanda che uno si fa guardando le identita'
        #    («ce ne sono due — e la terza azienda?»), e senza risposta si
        #    legge come «e' tutto a posto».
        dettaglio["emittenti_non_serviti"] = self._repo.emittenti_non_serviti(codice)
        # ⭐ Le sveglie di deploy del processo (zero, una o piu'), ognuna con
        #    la capability «Esegui ora» (piano §2.5). Il dichiarato e' cio' che
        #    il client MOSTRA; la capability e' cio' su cui DECIDE — e la
        #    produce lo stesso predicato con cui `esegui_ora` rifiuta.
        # ⭐ L'accensione del processo su questa installazione (brief-db-
        #    processi-accensione-per-ambiente §6.0 punto 5): lo stato effettivo
        #    e da dove viene. E' del PROCESSO, non della sveglia: viaggia una
        #    volta, e le capability delle sveglie la leggono da qui — la STESSA
        #    lettura con cui `esegui_ora` rifiuta.
        accensione = self._repo.accensione_processo(codice)
        dettaglio["accensione"] = _con_capability_accensione(accensione)
        dettaglio["sveglie"] = self._sveglie_con_capability(
            codice, acceso=accensione["acceso"] if accensione else None,
        )
        return dettaglio

    # Scopo: la riga del processo dal registro, o il 404 di dominio. E' il
    #        guard di ogni verbo che nomina un processo in URL: una sede, cosi'
    #        il codice e la frase del rifiuto non divergono fra i verbi.
    def _require_processo(self, codice: str, *, fn: str) -> dict[str, Any]:
        riga = self._repo.get_processo(codice)
        ErrorManager.require(
            riga is not None,
            code=E_NOT_FOUND,
            message="Il processo indicato non esiste nel registro.",
            detail=f"codice={codice!r}",
            function_name=fn,
        )
        assert riga is not None
        return riga

    # Scopo: le righe `sveglie[]` del dettaglio: il dichiarato di deploy piu'
    #        la terna `can_esegui_ora*` per ciascuna. I lavori vivi si leggono
    #        con UNA query per tutte le unit del processo (`= ANY`), non una
    #        per riga.
    def _sveglie_con_capability(
        self, processo_codice: str, *, acceso: bool | None,
    ) -> list[dict[str, Any]]:
        sveglie = sveglie_di_processo(processo_codice)
        if not sveglie:
            return []
        vivi = self._coda.lavori_vivi_per_chiave(
            job_type=JOB_TYPE_ESEGUI_PROCESSO,
            chiavi=[chiave_idempotenza(s.unit) for s in sveglie],
        )
        return [
            riga_sveglia(s, acceso=acceso, lavoro_vivo=vivi.get(chiave_idempotenza(s.unit)))
            for s in sveglie
        ]

    # Scopo: «Esegui ora» su una sveglia: ACCODA un lavoro `ESEGUI_PROCESSO`
    #        con lo scope di chi preme, e risponde con l'handle del lavoro. Il
    #        web non esegue niente: il drenatore lancera' il comando alla corsa
    #        successiva (`esegui_processo_handler`).
    #
    #        Nell'ordine del piano §2.4, e ogni rifiuto sta PRIMA di accodare:
    #          1. `unit` obbligatoria e stringa (400, campo `unit`);
    #          2. il processo esiste (404) e la unit e' fra le SUE sveglie (400,
    #             campo `unit`): il client manda una unit, mai un comando, e il
    #             backend la risolve dal dichiarato — la whitelist;
    #          3. il predicato: primo motivo come rifiuto (422/501/409 dalla
    #             classe a catalogo), con «gia' in coda» letto dal repository;
    #          4. l'accodamento, con la chiave di business per unit.
    #        ⭐ Un lavoro SISTEMA, dal 2026-11-07 (BE10, decisione di Tid,
    #        brief-db-revisione-dbops §5). Il processo che lancia
    #        (`avvio_manuale`) e' di MANUTENZIONE, e il comando lavora da se'
    #        sulle aziende del suo roster: un lavoro intestato a un'azienda
    #        sarebbe stato falso, e in modalita' globale la porta lo rifiuta
    #        (`E_CODA_LAVORO_SENZA_EMITTENTE`). Con la chiave `esegui:<unit>`,
    #        che l'azienda non la contiene, un lavoro per azienda avrebbe
    #        anche risposto `E_CODA_CHIAVE_ALTRUI` a chi preme dopo un altro.
    #        `richiesto_da` (l'`auth_user.id` di chi preme) viaggia nel
    #        payload: e' l'ATTORE del giornale del comando, non un'identita'.
    #        ⚠️ A tipo `attivo = false` il passo 4 risponde
    #        `E_JOB_TYPE_NON_ATTIVO` (501): e' il cancello voluto finche'
    #        l'handler non e' in servizio, e non si maschera.
    def esegui_ora(
        self, codice: str, *, unit: Any, richiesto_da: int,
    ) -> dict[str, Any]:
        fn = f"{_FN}.esegui_ora"
        ErrorManager.require(
            isinstance(unit, str) and bool(unit.strip()),
            code=E_VALIDATION_INPUT,
            message="Indicare la sveglia (`unit`) da eseguire.",
            context={"field": "unit"},
            function_name=fn,
        )
        assert isinstance(unit, str)
        unit = unit.strip()
        self._require_processo(codice, fn=fn)
        sveglia = sveglia_di_processo(codice, unit)
        ErrorManager.require(
            sveglia is not None,
            code=E_VALIDATION_INPUT,
            message=(
                f"La sveglia {unit} non e' fra quelle dichiarate per il processo "
                f"{codice}."
            ),
            detail=f"codice={codice!r} unit={unit!r}",
            context={"field": "unit"},
            function_name=fn,
        )
        assert sveglia is not None

        chiave = chiave_idempotenza(unit)
        vivi = self._coda.lavori_vivi_per_chiave(
            job_type=JOB_TYPE_ESEGUI_PROCESSO, chiavi=[chiave],
        )
        motivi = motivi_esegui_ora(
            sveglia,
            acceso=self._repo.acceso_processo(codice),
            lavoro_vivo=vivi.get(chiave),
        )
        if motivi:
            raise motivi[0].come_errore(unit=unit)

        job_id = self._coda.accoda(
            job_type=JOB_TYPE_ESEGUI_PROCESSO,
            payload={
                "processo_codice": codice, "unit": unit,
                "richiesto_da": int(richiesto_da),
            },
            run_as=RUN_AS_SISTEMA,
            scope=None,
            # Chiave di BUSINESS (una per unit, sui lavori vivi): la rete sotto
            # il 409 qui sopra, per la corsa fra due click contemporanei.
            idempotency_key=chiave,
            origine=ORIGINE_API,
        )
        # ⭐ Lo stato VERO (`stati_dopo_accodamento`): la corsa fra due click
        #    finisce sulla dedup della porta, che restituisce il lavoro già
        #    vivo — può essere IN_CORSO. Chi preme è super admin
        #    (`AdminAPIView`), e un lavoro SISTEMA sotto la RLS della coda lo
        #    vede.
        stato = self._coda.stati_dopo_accodamento([job_id])[job_id]
        return {"job_id": job_id, "stato": stato, "unit": unit}

    # Scopo: La SCELTA A MANO sull'accensione di un processo, su questa
    #        installazione (brief-db-processi-accensione-per-ambiente §6.0
    #        punto 5): `acceso` True/False la scrive, None la toglie e torna il
    #        default per ambiente. Ritorna l'accensione rinfrescata (la stessa
    #        forma del dettaglio), cosi' il drawer non deve ricalcolare niente.
    #
    #        Nell'ordine, e ogni rifiuto prima di scrivere:
    #          1. `acceso` presente e booleano o null (400, campo `acceso`):
    #             null va DETTO — un campo assente non vale «torna al default»;
    #          2. `motivo` obbligatorio per TUTTI e tre i gesti (400, campo
    #             `motivo`). Per accendere e spegnere lo pretende anche il guard
    #             della tabella; per «torna al default» il DB cancella la riga e
    #             non lascia traccia, quindi il motivo e' l'unica cosa che resta
    #             (nel log applicativo, sotto) — vedi la nota ⚠️;
    #          3. il processo esiste (404);
    #          4. il verbo del DB: «non spegnibile» e «senza sveglia» li rifiuta
    #             il guard, col loro codice; qui si traducono.
    # ⚠️ «Chi» lo scrive il DB in `user_update`, ma oggi e' `CURRENT_USER`
    #    (il ruolo PostgreSQL, sempre `zeroerp_app`), non la persona: e' una
    #    richiesta aperta al team DB. Finche' non c'e', la persona e il motivo
    #    stanno nel log applicativo di questo gesto, che e' anche l'unica
    #    traccia di «torna al default».
    def imposta_accensione(
        self, codice: str, payload: dict[str, Any], *, attore: str,
    ) -> dict[str, Any]:
        fn = f"{_FN}.imposta_accensione"
        ErrorManager.require(
            "acceso" in payload and (payload["acceso"] is None or isinstance(payload["acceso"], bool)),
            code=E_VALIDATION_INPUT,
            message="Indicare se accendere (true), spegnere (false) o tornare al default (null).",
            context={"field": "acceso"},
            function_name=fn,
        )
        acceso: bool | None = payload["acceso"]
        motivo_grezzo = payload.get("motivo")
        motivo = motivo_grezzo.strip() if isinstance(motivo_grezzo, str) else ""
        ErrorManager.require(
            bool(motivo),
            code=E_MOTIVO_OBBLIGATORIO,
            message="Indicare il motivo della scelta.",
            context={"field": "motivo"},
            function_name=fn,
        )
        self._require_processo(codice, fn=fn)
        with translate_db_errors(
            context={"op": fn},
            fallback_code=E_VALIDATION,
            fallback_message="Accensione del processo non aggiornata.",
        ):
            self._repo.imposta_accensione(codice, acceso=acceso, motivo=motivo)
        logger.info(
            "accensione processo %s: %s da %s, motivo: %s",
            codice,
            {True: "acceso", False: "spento", None: "torna al default"}[acceso],
            attore,
            motivo,
        )
        accensione = _con_capability_accensione(self._repo.accensione_processo(codice))
        # La riga c'e': il processo l'ha trovato `_require_processo` qui sopra.
        assert accensione is not None
        return accensione

    # Scopo: Le corse recenti di un processo (tab «Ultimi run» del drawer).
    def list_run(
        self, codice: str, *, limit: int = DEFAULT_LIMIT, offset: int = 0,
    ) -> dict[str, Any]:
        limit, offset = limiti_pagina(limit, offset)
        righe, totale = self._repo.list_run_processo(
            codice, limit=limit, offset=offset,
        )
        return {"count": totale, "results": righe}

    # Scopo: Lo stato dei presidi, in un round-trip.
    #
    # ⭐ QUALI presidi si guardino lo dice il CATALOGO (`dbops.presidi`, natura
    #    `ZERO`), non un elenco nel backend; e che cosa significhi una loro riga
    #    lo dice il commento della vista. Il service non classifica niente: le
    #    due decisioni hanno una sede sola, ed e' il database.
    # ⚠️ I tre numeri della testata (`totale`, `con_righe`, `non_letti`) li
    #    calcola `_testata_presidi`, la stessa funzione del pallino: la regola
    #    «accesi e non letti non si sommano» sta scritta la', una volta.
    def stato_presidi(self) -> dict[str, Any]:
        presidi = self._presidi.stato_presidi()
        return {"presidi": presidi, **_testata_presidi(presidi)}

    # Scopo: La SOLA testata dei presidi, per il pallino della topbar: stesso
    #        giro del pannello senza le prime righe (piano osservabilita' §2.2).
    #
    # ⭐ Non e' un secondo predicato: e' `_testata_presidi` sulle stesse righe
    #    che il pannello legge, meno le righe di esempio. Il pallino e il
    #    pannello non possono dire due cose diverse perche' contano con la
    #    stessa funzione lo stesso elenco.
    # ⚠️ Un presidio che non si legge NON e' un errore di questo endpoint: e'
    #    `non_letti + 1`, per contratto — la cecita' si conta, non si solleva.
    def conteggi_presidi(self) -> dict[str, int]:
        return _testata_presidi(self._presidi.stato_presidi(con_righe=False))

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

    # Scopo: Riaccende l'utente tecnico SPENTO di un processo per un emittente.
    #        Ritorna l'`auth_user_id` riattivato.
    #
    # ⭐ E' il secondo verbo di una coppia, e la coppia e' il punto. Sostituire
    #    l'utente di un processo passa per «si spegne il legame e se ne fa uno
    #    nuovo»: ma lo username e' deterministico (`processo@azienda`) ed e'
    #    UNIQUE senza condizioni, quindi la seconda meta' sbatteva su un `23505`
    #    nudo. Dal 2026-09-05 (DB-6) `fn_crea_utente_tecnico` riconosce il caso e
    #    rifiuta dicendo `E_UTENTE_TECNICO_DA_RIATTIVARE` — cioe' manda QUI.
    # ⚠️ Riaccende TUTTA la terna (utente Django, identita' digitale, legame nel
    #    registro): spegnerne uno basta a fermare il processo, quindi riaccenderne
    #    uno solo basta a lasciarlo fermo con l'aria di essere a posto.
    # ⛔ Nessun guard ricopiato, come per la creazione: la fabbrica rifiuta e
    #    spiega, e i suoi codici sono a catalogo.
    def riattiva_utente_tecnico(
        self, processo_codice: str, *, emittente_codice: str,
    ) -> dict[str, Any]:
        fn = f"{_FN}.riattiva_utente_tecnico"
        ErrorManager.require(
            bool(processo_codice) and bool(emittente_codice),
            code=E_VALIDATION,
            message="Processo ed emittente sono entrambi obbligatori.",
            function_name=fn,
        )
        with translate_db_errors(
            context={"op": fn},
            fallback_code=E_VALIDATION,
            fallback_message="Riattivazione dell'utente tecnico non riuscita.",
        ):
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT script.fn_riattiva_utente_tecnico(%s, %s)",
                    [processo_codice, emittente_codice],
                )
                row = cursor.fetchone()
        assert row is not None
        return {"auth_user_id": int(row[0])}


# Scopo: l'accensione come viaggia al client, piu' la capability del gesto:
#        `can_imposta_accensione` (e il suo `_reason`). Il drawer mostra
#        l'interruttore solo se il flag e' vero — «assente sui non
#        spegnibili» (brief DB §6.0 punto 5) — e non deduce niente da
#        `spegnibile` per decidere.
# ⭐ Il flag discende dal catalogo, come il guard che rifiuterebbe il gesto:
#    `spegnibile` False -> il guard dice NON_SPEGNIBILE; NULL (CODA o
#    ritirato, senza sveglia) -> il guard dice SENZA_SVEGLIA.
# ⭐ Piu' la terna del SOLO gesto «accendi» (`can_accendere`, `_reason`,
#    `_reason_key`, R-BE-5 di brief-db-processi-accensione-per-ambiente §6.7.3):
#    in PRODUZIONE un processo non accendibile (lo smoke notturno) si spegne e
#    torna al default, ma non si accende a mano. Il permesso e' la risposta del
#    predicato del guard (`accendere_ammesso` dal repository), non una regola
#    ricostruita qui: False -> NON_ACCENDIBILE_IN_PRODUZIONE, None (ambiente
#    non dichiarato) -> CONFIG_MANCANTE, come il guard.
def _con_capability_accensione(accensione: dict[str, Any] | None) -> dict[str, Any] | None:
    if accensione is None:
        return None
    accensione = dict(accensione)
    ammesso = accensione.pop("accendere_ammesso", None)
    # ⭐ Una scelta «accendi» scritta PRIMA del divieto (o prima che l'ambiente
    #    fosse dichiarato) resta nella riga, ma lo stato effettivo la ignora
    #    (§6.6). Senza dirlo, il drawer mostrerebbe «Spento» sopra «Scelta a
    #    mano: …», che si contraddicono. `ammessa` e' la risposta dello stesso
    #    predicato: una scelta che non accende e' sempre ammessa.
    scelta = accensione.get("scelta_a_mano")
    if scelta is not None:
        accensione["scelta_a_mano"] = {
            **scelta, "ammessa": ammesso is not False if scelta.get("acceso") is True else True,
        }
    spegnibile = accensione.get("spegnibile")
    reason = (
        None if spegnibile is True
        else E_PROCESSO_NON_SPEGNIBILE if spegnibile is False
        else E_PROCESSO_SENZA_SVEGLIA
    )
    reason_accendere = (
        reason if reason is not None
        else None if ammesso is True
        else E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE if ammesso is False
        else E_CONFIG_MANCANTE
    )
    return {
        **accensione,
        # Il processo ha una sveglia da accendere o spegnere? I processi `CODA`
        # (li avvia una persona) e i ritirati no: il drawer non mostra
        # l'accensione. NULL di `spegnibile` e' esattamente quel caso (CHECK
        # del catalogo che lo lega al canale).
        "ha_sveglia": spegnibile is not None,
        "can_imposta_accensione": reason is None,
        "can_imposta_accensione_reason": reason,
        "can_accendere": reason_accendere is None,
        "can_accendere_reason": reason_accendere,
        "can_accendere_reason_key": (
            ACCENDI_REASON_KEY_PER_CODICE.get(reason_accendere) if reason_accendere else None
        ),
    }
