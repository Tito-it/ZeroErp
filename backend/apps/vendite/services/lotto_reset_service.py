# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: gli atti che DISFANO il lavoro di un lotto ancora pre-fiscale —
#        annullamento, ritorno in bozza, eliminazione di una fattura e, dal
#        2026-09-08, l'uscita di un DOCUMENTO dal giro.
#        ⚠️ Il modulo diceva «reset tecnico lotto DRAFT»: era vero quando il
#        perimetro era il solo DRAFT e i verbi erano tre. Oggi il confine e' il
#        PRE-FISCALE (slice 6-B) e i verbi sono quattro; l'uscita del documento
#        sta qui perche' COMPONE l'eliminazione della fattura, non accanto ad
#        essa — separarla vorrebbe dire un file per un metodo, che le
#        convenzioni di progetto escludono.
# ------------------------------------------------------------


from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import translate_db_errors
from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.types import (
    AnnullaLottoDaDraftResult,
    EliminaFatturaDaLottoResult,
    EsclusioneDocumentoDaGiroResult,
    RiportaLottoADraftResult,
)

# Servizio applicativo: espone il reset tecnico lotto DRAFT.


# ⭐ IL CODICE CHE SI USA QUANDO IL RIFIUTO NON NE PORTA UNO — sede unica.
#
# ⚠️ Serve in DUE punti che devono dire la stessa cosa: qui, come `fallback_code`
#    della traduzione, e nel diario del giro di massa
#    (`pipeline_service._EsclusioneRunLogger`), che di codice deve metterne uno
#    anche quando il logger non ha visto l'eccezione — `run_fan_out` inghiotte i
#    fallimenti del proprio logger di proposito, quindi quel ripiego e'
#    RAGGIUNGIBILE, non decorativo.
# ⛔ Due letterali uguali scritti a mano divergerebbero senza fallire: il report
#    per riga mostrerebbe un codice che il traduttore non usa piu', e chi
#    instrada su quel codice smetterebbe di agganciare in silenzio.
CODICE_RIPIEGO_USCITA = "E_PIPELINE_VALIDATION"


class LottoResetService:
    # Scopo: Inizializza la istanza.
    def __init__(self, repository: VenditePipelineRepository | None = None) -> None:
        self.repository = repository or VenditePipelineRepository()

    # Scopo: Annullamento del lotto in DRAFT (guard sui parametri + delega al
    #        repository). Nome allineato alla funzione SQL dopo D-L: e' un
    #        annullamento, non un ritorno in bozza.
    def annulla_lotto_da_draft(self, lotto_id: int) -> AnnullaLottoDaDraftResult:
        ErrorManager.require(
            lotto_id is not None and lotto_id > 0,
            code="E_RESET_LOTTO_VALIDATION",
            message="Parametro lotto non valido.",
            detail="lotto_id obbligatorio e > 0",
            context={"lotto_id": lotto_id},
            function_name="vendite.lotto_reset_service.annulla_lotto_da_draft",
            log_to_db=True,
        )
        assert lotto_id is not None
        return self.repository.annulla_lotto_da_draft(lotto_id)

    # Scopo: RITORNO A BOZZA del lotto (Fase 6): guard sui parametri + delega.
    #        Da non confondere col vicino `annulla_lotto_da_draft`, che CHIUDE
    #        il lotto: questo lo rimette in gioco perche' rifaccia il giro.
    #        Le precondizioni vere (tipo lotto, stato, nessuna fattura numerata)
    #        stanno nella funzione DB e non si riscrivono qui: qui si presidia
    #        solo il parametro, come fa il gemello.
    def riporta_lotto_a_draft(self, lotto_id: int) -> RiportaLottoADraftResult:
        ErrorManager.require(
            lotto_id is not None and lotto_id > 0,
            code="E_RESET_LOTTO_VALIDATION",
            message="Parametro lotto non valido.",
            detail="lotto_id obbligatorio e > 0",
            context={"lotto_id": lotto_id},
            function_name="vendite.lotto_reset_service.riporta_lotto_a_draft",
            log_to_db=True,
        )
        assert lotto_id is not None
        return self.repository.riporta_lotto_a_draft(lotto_id)

    # Scopo: Elimina una singola fattura dal lotto, liberandone le attivita'
    #        (guard sui parametri + delega al repository). Perimetro:
    #        lotto E fattura PRE-FISCALI (DRAFT o EMESSA) — le precondizioni
    #        vivono in `script.fn_check_fattura_eliminabile_da_lotto`, unica
    #        sede, e non si ricopiano qui.
    #        Non e' un'«estrazione»: togliere la fattura vuol dire CANCELLARLA,
    #        righe e satelliti compresi (RD-7). Il «DRAFT» che questo commento
    #        portava fino al 2026-08-04 era il perimetro vecchio del lotto.
    def elimina_fattura_da_lotto(
        self,
        lotto_id: int,
        fattura_id: int,
    ) -> EliminaFatturaDaLottoResult:
        ErrorManager.require(
            lotto_id is not None and lotto_id > 0 and fattura_id is not None and fattura_id > 0,
            code="E_RESET_LOTTO_FATTURA_VALIDATION",
            message="Parametri reset fattura non validi.",
            detail="lotto_id e fattura_id obbligatori e > 0",
            context={"lotto_id": lotto_id, "fattura_id": fattura_id},
            function_name="vendite.lotto_reset_service.elimina_fattura_da_lotto",
            log_to_db=True,
        )
        assert lotto_id is not None
        assert fattura_id is not None
        return self.repository.elimina_fattura_da_lotto(lotto_id, fattura_id)

    # Scopo: toglie UN documento dal giro di fatturazione, cosi' che il lotto
    #        possa ripartire con quelli che restano.
    #
    # ⛔ QUI NON C'E' NESSUNA REGOLA DI DOMINIO, e non e' una svista: il verdetto
    #    («si puo' togliere?») lo da' `script.fn_check_documento_escludibile_da_giro`,
    #    che la funzione MADRE chiama per rifiutare — la STESSA da cui la lista
    #    prende il motivo del pulsante spento. Riscriverne anche un pezzo qui
    #    farebbe dire due cose diverse al tooltip e all'errore (§6.3 del brief).
    #
    # ⚠️ Il guard sotto e' sui PARAMETRI, non sul dominio: `lotto_id <= 0` e
    #    `gruppo_key` vuota vengono da un chiamante rotto, non da una persona, e
    #    fermarli qui evita un giro al database per dire la stessa cosa.
    # ⛔ Il MOTIVO invece NON si valida qui, ed e' deliberato: e' una regola di
    #    dominio (D-5, «il motivo e' obbligatorio»), la tiene il `CHECK` di
    #    tabella e la madre solleva `E_PARAMETRO_INVALIDO` anche sui soli spazi.
    #    Un secondo controllo in Python sarebbe la seconda sede di una regola
    #    che il database gia' possiede.
    def escludi_documento_da_giro(
        self, lotto_id: int, gruppo_key: str, motivo: str,
    ) -> EsclusioneDocumentoDaGiroResult:
        ErrorManager.require(
            lotto_id is not None and lotto_id > 0 and bool((gruppo_key or "").strip()),
            code="E_RESET_LOTTO_VALIDATION",
            message="Parametri non validi.",
            detail="lotto_id obbligatorio e > 0, gruppo_key obbligatoria",
            context={"lotto_id": lotto_id, "gruppo_key": gruppo_key},
            function_name="vendite.lotto_reset_service.escludi_documento_da_giro",
            log_to_db=True,
        )
        assert lotto_id is not None
        # ⭐ IL CODICE DEL RIFIUTO DEVE ARRIVARE FIN QUI, e per questo la
        #    traduzione sta nel SERVICE e non al confine dell'API.
        #
        # 🔴 Il difetto che chiude, misurato sul giro di massa: senza, dentro il
        #    fan-out l'eccezione e' ancora quella grezza di psycopg — nessun
        #    `.code` — e il report per riga usciva con il codice di ripiego su
        #    OGNI documento rifiutato. `E_LOTTO_DOC_NON_IN_ERRORE` e
        #    `E_LOTTO_DOC_GIA_USCITO` diventavano la stessa cosa, cioe' proprio
        #    l'informazione su cui il frontend deve instradare.
        # ⚠️ Sul verbo SINGOLO non si vedeva: li' l'eccezione arriva al
        #    middleware, che traduce. Il giro di massa non ci passa mai.
        #
        # ⛔ Nessuna mappa di vincoli: qui non si scrive su tabelle con UNIQUE o
        #    FK proprie — si chiama una funzione che SOLLEVA con un codice a
        #    catalogo, e il BB lo estrae dai `diag` del `RAISE`. Il fallback
        #    resta per cio' che non e' un errore di dominio.
        with translate_db_errors(
            context={"op": "vendite.lotto_reset_service.escludi_documento_da_giro"},
            fallback_code=CODICE_RIPIEGO_USCITA,
            fallback_message="Uscita del documento dal giro non riuscita.",
        ):
            return self.repository.escludi_documento_da_giro(lotto_id, gruppo_key, motivo)
