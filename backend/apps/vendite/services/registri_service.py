# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service dei REGISTRI DI NUMERAZIONE — validazione payload, le due
#        specie di registro e la traduzione dei vincoli DB in errori parlanti.
#        Brief: brief-be-fe-crud-registri-di-numerazione §BE-1/§BE-2/§10.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any, NoReturn

from django.db import IntegrityError, transaction

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator, map_integrity_error
from apps.core.services.value_normalizer import empty_to_none
from apps.vendite.db.famiglie_repository import FamiglieDocumentoRepository
from apps.vendite.db.registri_repository import (
    _CAMPI_CREATE,
    _CAMPI_UPDATE,
    RegistriRepository,
)

logger = logging.getLogger(__name__)

E_VENDITE_VALIDATION = "E_VENDITE_VALIDATION"
E_VENDITE_DUPLICATO = "E_VENDITE_DUPLICATO"
E_VENDITE_NOT_FOUND = "E_VENDITE_NOT_FOUND"
E_VENDITE_FK = "E_VENDITE_FK"

# ⛔ QUI C'ERA `_FAMIGLIA_FISCALE = "FATTURA"`, ED E' STATO TOLTO IL 2026-09-02
#    (§11.10 BE-F2). Era il secondo di due letterali paralleli — l'altro viveva
#    in `frontend/src/amministrazione/constants.js` — e diceva col nome di UNA
#    riga una proprieta' che ora e' una COLONNA:
#    `vendite.famiglie_documento.presidia_data_documento`.
#    ⭐ La differenza non e' di stile: col letterale, una famiglia nuova che
#    presidia la data sarebbe stata trattata come non fiscale da entrambi i
#    lati, e i suoi campi sarebbero spariti dalla maschera senza che niente
#    fallisse. Ora la domanda si fa al catalogo, che e' l'unico a saperlo.

# ⭐ I TRE CAMPI CONDIZIONATI ALLA FAMIGLIA, col loro valore NEUTRO — cioe' cio'
#    che il `CHECK` pretende quando la famiglia non ammette le regole fiscali. Verificato sul
#    database vivo il 2026-09-01, non dedotto dal nome:
#
#      CHECK (famiglia = 'FATTURA' OR (limite_giorni IS NULL
#             AND limite_giorno_mese IS NULL AND politica_data = 'OGGI'))
#
# ⛔ `politica_data_documento` NON e' azzerabile a NULL: la colonna e' NOT NULL
#    e il suo neutro e' il valore 'OGGI'. Trattarla come le altre due — cioe'
#    mettendola a None — la farebbe respingere da un vincolo diverso, con un
#    messaggio che parla di un campo obbligatorio invece che della famiglia.
#    E' la ragione per cui qui c'e' una MAPPA e non un elenco di nomi
#    (`feedback_normalize_guard_simmetrico`).
_NEUTRI_SENZA_REGOLE_FISCALI: dict[str, Any] = {
    "limite_emissione_giorni": None,
    "limite_emissione_giorno_mese": None,
    "politica_data_documento": "OGGI",
}

# ⭐ COLONNE `NOT NULL` CHE HANNO UN DEFAULT A DATABASE. Per queste «campo
#    assente» e «campo vuoto» vogliono dire la stessa cosa — *usa il default* —
#    e l'unico modo di sbagliare e' mandare un `NULL` esplicito, che il vincolo
#    respinge con un messaggio che parla di un campo obbligatorio invece che
#    della scelta che l'operatore non ha fatto.
# ⛔ Si TOGLIE la chiave, non si scrive qui il valore: il default vive nella
#    colonna (`reset_policy DEFAULT 'ANNUALE'`), e ricopiarlo in Python
#    creerebbe una terza sede — dopo il database e la costante del frontend —
#    che nessun presidio tiene allineata.
# ⚠️ Serve da quando `reset_policy` e' un campo scrivibile (2026-09-08):
#    `empty_to_none` trasforma la stringa vuota in `None`, e senza questo passo
#    un payload con `"reset_policy": ""` arriverebbe all'INSERT come NULL.
_NOT_NULL_CON_DEFAULT_DB: frozenset[str] = frozenset({"reset_policy"})

# ⭐ LE DUE VOCI CHE VALGONO IL CANTIERE, e dicono la stessa cosa su due assi.
#
# ⛔ NESSUNA DELLE DUE PUO' DIRE «esiste gia'» E BASTA. I due UNIQUE sono
#    PARZIALI e **non filtrano su `attivo`**: un registro spento continua a
#    occupare il suo slot. Un messaggio che non lo dice manda l'operatore a
#    cercare in una lista dove la riga che lo blocca non si vede — ed e' il
#    difetto che il §0 del brief descrive per intero.
#
# ⚠️ E LA TUPLA E' LUNGA DIVERSA, PER UNA RAGIONE VERA (map_integrity_error,
#    terzo elemento = il campo che il client accende):
#    * la TERNA e' composta su tre colonne che l'operatore sceglie tutte —
#      nessuna e' «piu' sbagliata» delle altre, e dichiararne una manderebbe a
#      correggere un campo che non e' piu' sbagliato degli altri due ⇒ tupla a
#      DUE;
#    * la COPPIA prefisso/suffisso ha in gioco due colonne, l'emittente non e'
#      un campo del form (lo da' il tab) e la coppia e' cio' che l'operatore ha
#      appena scritto ⇒ si dichiara `prefisso`, che e' quello che si corregge
#      per primo.
_UNIQUE_CONSTRAINTS: dict[str, tuple] = {
    "uq_registri_fatturazione_famiglia_emittente_utility": (
        E_VENDITE_DUPLICATO,
        "Esiste già un registro per questa famiglia, questo emittente e questa "
        "utility — possibilmente disattivato. Un registro spento continua a "
        "occupare lo slot: per la stessa combinazione si riattiva quello che "
        "c'è, non se ne crea un altro.",
    ),
    "uq_registri_fatturazione_prefisso_suffisso": (
        E_VENDITE_DUPLICATO,
        "Questo emittente ha già un registro con questa coppia "
        "prefisso/suffisso — possibilmente disattivato. Due sezionali dello "
        "stesso emittente non possono produrre numeri della stessa forma: si "
        "riusa quello che c'è, o si cambia la forma.",
        "prefisso",
    ),
    "uq_registri_fatturazione_codice": (
        E_VENDITE_DUPLICATO,
        "Esiste già un registro con questo codice.",
        "codice",
    ),
}

_FK_CONSTRAINTS: dict[str, tuple] = {
    "fk_registri_fatturazione_famiglia": (
        E_VENDITE_FK,
        "Famiglia documento non valida.",
        "famiglia_documento",
    ),
    "fk_registri_fatturazione_emitt": (E_VENDITE_FK, "Emittente fiscale non valido."),
    "fk_registri_fatturazione_utility": (
        E_VENDITE_FK,
        "Utility non valida.",
        "utility_id",
    ),
}

# ⭐ I `CHECK` si traducono perche' altrimenti arriva al client il fallback
#    generico, che non dice quale campo e' sbagliato ne' cosa e' ammesso.
_CHECK_CONSTRAINTS: dict[str, tuple] = {
    "chk_registri_fatturazione_famiglia_regole_fattura": (
        E_VENDITE_VALIDATION,
        "I campi del limite di emissione e una politica data non neutra sono "
        "ammessi solo sui registri di famiglia FATTURA.",
    ),
    # ⚠️ IL MESSAGGIO DICE COSA IL `CHECK` AMMETTE, non cosa il backend espone.
    #    Fino al 2026-09-08 diceva «e' ANNUALE e non e' modificabile», ed era
    #    falso dal 2026-09-01: il changeSet `20260901-06` ha allargato il vincolo
    #    a ANNUALE **e** NESSUNA, e `fn_get_next_progressivo` ramifica davvero
    #    (sotto NESSUNA il secchio e' uno solo e vale 0).
    # ⛔ La frase non doveva parlare della whitelist del backend: questo e' il
    #    messaggio di un vincolo del DATABASE, e se un giorno il campo si apre
    #    e' l'unica cosa che l'operatore legge quando sbaglia il valore. Una
    #    frase che nomina un divieto applicativo lo manderebbe a cercare il
    #    permesso invece del valore ammesso.
    "chk_registri_fatturazione_reset": (
        E_VENDITE_VALIDATION,
        "La politica di reset del contatore ammette solo ANNUALE (il "
        "progressivo riparte a ogni anno) o NESSUNA (un contatore solo, che "
        "non riparte mai).",
    ),
    "chk_registri_fatturazione_politica_data": (
        E_VENDITE_VALIDATION,
        "Politica data documento non valida.",
        "politica_data_documento",
    ),
    "chk_registri_fatturazione_limite_giorni": (
        E_VENDITE_VALIDATION,
        "Limite di emissione in giorni fuori intervallo ammesso.",
        "limite_emissione_giorni",
    ),
    "chk_registri_fatturazione_limite_giorno_mese": (
        E_VENDITE_VALIDATION,
        "Giorno del mese del limite di emissione fuori intervallo ammesso.",
        "limite_emissione_giorno_mese",
    ),
    "chk_registri_fatturazione_limite_coerenza": (
        E_VENDITE_VALIDATION,
        "I due limiti di emissione non sono coerenti fra loro.",
    ),
}


class RegistriService:
    """Regole applicative dei registri di numerazione."""

    def __init__(self) -> None:
        self.repo = RegistriRepository()
        # ⭐ Il catalogo delle famiglie e' un LETTORE, non una dipendenza di
        #    scrittura: serve a chiedere se la famiglia presidia la data del
        #    documento (§11.10 BE-F2), che prima era un letterale cablato.
        self.famiglie = FamiglieDocumentoRepository()
        self._v = PayloadValidator(validation_code=E_VENDITE_VALIDATION)

    # =================================================================
    # Lettura
    # =================================================================

    def list_registri(
        self,
        emittenti_sr_ids: list[int] | None,
        **filtri: Any,
    ) -> tuple[list[dict[str, Any]], int]:
        return self.repo.list_registri(emittenti_sr_ids, **filtri)

    # Scopo: dettaglio + i contatori in sola lettura (§BE-4).
    # ⚠️ I progressivi si leggono DOPO aver risolto il registro nello scope: se
    #    li si leggesse per id prima del controllo, un id fuori perimetro
    #    risponderebbe coi contatori di un sezionale altrui — e la risposta
    #    sarebbe un 404 con dentro il dato che il 404 nega.
    def get_registro(
        self,
        registro_id: int,
        emittenti_sr_ids: list[int] | None,
    ) -> dict[str, Any]:
        registro = self.repo.get_registro(registro_id, emittenti_sr_ids)
        if registro is None:
            ErrorManager.raise_error(
                code=E_VENDITE_NOT_FOUND,
                message="Registro di numerazione non trovato.",
                context={"registro_id": registro_id},
            )
        registro["progressivi"] = self.repo.list_progressivi(registro_id)
        return registro

    # =================================================================
    # Scrittura
    # =================================================================

    # Scopo: normalizza il payload in ingresso — una sede sola per create e
    #        update, cosi' le due non divergono.
    # ⛔ Le stringhe vuote diventano NULL (`feedback_null_vs_empty`): su
    #    `prefisso` e `suffisso` la differenza NON e' cosmetica, e' il predicato
    #    dell'UNIQUE parziale — `WHERE COALESCE(prefisso,'') <> '' OR ...`. Un
    #    prefisso salvato come stringa vuota invece che NULL non cambia niente
    #    per l'indice, ma un `suffisso` vuoto salvato come `''` renderebbe la
    #    riga indistinguibile da una senza suffisso in ogni lettura successiva.
    def _normalizza(self, payload: dict[str, Any]) -> dict[str, Any]:
        dati = {k: empty_to_none(v) for k, v in payload.items()}
        famiglia = dati.get("famiglia_documento")
        # ⚠️ NASCONDERE NON BASTA, VANNO ANCHE NON SPEDITI (§FE-4) — e il
        #    backend non si fida del fatto che il form li abbia tolti: un
        #    `defaultForm()` li porta comunque, e su una famiglia non fiscale il
        #    CHECK li rifiuta con un messaggio che parla di un campo che
        #    l'operatore non ha nemmeno visto.
        # ⭐ Si azzerano solo quando la famiglia e' NOTA e diversa da FATTURA:
        #    in update la famiglia non e' nel payload (non e' modificabile), e
        #    dedurre «non e' FATTURA» dalla sua assenza cancellerebbe i limiti
        #    di un registro fiscale a ogni salvataggio.
        if famiglia is not None and not self._famiglia_ammette_regole_fiscali(famiglia):
            for campo, neutro in _NEUTRI_SENZA_REGOLE_FISCALI.items():
                if campo in dati and dati[campo] != neutro:
                    dati[campo] = neutro
        # «Vuoto» su una NOT NULL con default = «non l'ho scelto»: si toglie la
        # chiave e decide la colonna. Vedi `_NOT_NULL_CON_DEFAULT_DB`.
        for campo in _NOT_NULL_CON_DEFAULT_DB:
            if campo in dati and dati[campo] is None:
                del dati[campo]
        return dati

    # Scopo: «la famiglia di questo registro ammette le regole fiscali?», cioe'
    #        i tre campi condizionati.
    # ⚠️ Famiglia SCONOSCIUTA -> `False`, e quindi i tre campi si azzerano: e'
    #    la risposta prudente, e non nasconde niente — a rifiutare la famiglia
    #    inesistente e' la FK `fk_registri_fatturazione_famiglia`, un attimo
    #    dopo e col suo messaggio. Ripiegare su `True` avrebbe fatto arrivare al
    #    database dei valori che il CHECK respinge, con un errore che parla di
    #    un campo invece che della famiglia.
    def _famiglia_ammette_regole_fiscali(self, codice_interno: str) -> bool:
        return bool(self.famiglie.ammette_regole_fiscali(codice_interno))

    # Scopo: il contratto delle chiavi di ogni verbo — le colonne che il
    #        repository scrive. L'emittente non c'e': la view lo toglie dal
    #        corpo e lo passa a parte, dopo averlo verificato nello scope.
    # ⛔ Una chiave in piu' e' un 400 parlante, dal 2026-09-26. Fino a quel
    #    giorno il repository la SCARTAVA IN SILENZIO (`if c in dati`): un
    #    `serie_default` o un `reset_policy` spediti in MODIFICA — i campi che
    #    la view dichiara non modificabili — rispondevano 200 senza aver
    #    scritto niente, cioe' «salvato» su un campo che non si salva.
    def _verifica_chiavi(
        self, payload: dict[str, Any], *, ammesse: tuple[str, ...], verbo: str,
    ) -> None:
        self._v.validate_allowed_keys(
            payload,
            allowed=frozenset(ammesse),
            message=f"Campi non ammessi in {verbo} del registro.",
        )

    def create_registro(
        self,
        emittente_soggetto_ruolo_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._verifica_chiavi(payload, ammesse=_CAMPI_CREATE, verbo="creazione")
        dati = self._normalizza(payload)
        if not dati.get("codice"):
            ErrorManager.raise_error(
                code=E_VENDITE_VALIDATION,
                message="Il codice del registro è obbligatorio.",
                context={"field": "codice"},
            )
        if not dati.get("descrizione"):
            ErrorManager.raise_error(
                code=E_VENDITE_VALIDATION,
                message="La descrizione del registro è obbligatoria.",
                context={"field": "descrizione"},
            )
        try:
            with transaction.atomic():
                registro_id = self.repo.create_registro(
                    emittente_soggetto_ruolo_id, dati,
                )
        except IntegrityError as exc:
            self._traduci(exc, dati)
        return self.get_registro(registro_id, [emittente_soggetto_ruolo_id])

    def update_registro(
        self,
        registro_id: int,
        emittenti_sr_ids: list[int] | None,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._verifica_chiavi(payload, ammesse=_CAMPI_UPDATE, verbo="modifica")
        dati = self._normalizza(payload)
        # ⛔ Un PATCH senza campi e' un 400, non un 200 che non scrive (Tid,
        #    2026-10-20, brief-be-verifica-documentazione-api §A2).
        self._v.require_campi_da_aggiornare(dati)
        try:
            with transaction.atomic():
                toccate = self.repo.update_registro(
                    registro_id, emittenti_sr_ids, dati,
                )
        except IntegrityError as exc:
            self._traduci(exc, dati)
        # ⚠️ `toccate == 0` vuol dire che il registro non esiste o e' fuori
        #    perimetro (il payload vuoto e' gia' un 400, qui sopra): lo dice la
        #    rilettura, che solleva 404.
        logger.debug("update_registro id=%s righe=%s", registro_id, toccate)
        return self.get_registro(registro_id, emittenti_sr_ids)

    # Scopo: accende o spegne il registro.
    # ⛔ NON si ricontrolla qui se e' disattivabile. A rifiutare sono i SEI
    #    trigger di disattivazione, e la `script.fn_check_registro_disattivabile`
    #    che la lista legge serve a SPEGNERE IL PULSANTE, non a decidere al
    #    posto del database. Un controllo applicativo in mezzo sarebbe un
    #    settimo elenco che diverge in silenzio il giorno che nasce la settima
    #    figlia — ed e' gia' successo, da tre a sei, in una giornata.
    def set_attivo(
        self,
        registro_id: int,
        emittenti_sr_ids: list[int] | None,
        attivo: bool,
    ) -> dict[str, Any]:
        # ⚠️ SI SCRIVE PRIMA E SI LEGGE UNA VOLTA SOLA. La prima stesura leggeva
        #    anche prima, per distinguere il 404 — ma ogni lettura fa girare le
        #    DUE check in LATERAL piu' la query dei contatori, e le pagava due
        #    volte per un'informazione che la rilettura da' comunque.
        # ⭐ «Zero righe» ha due cause e la rilettura le separa da sola: fuori
        #    perimetro o inesistente -> `get_registro` solleva 404; gia' nello
        #    stato richiesto -> torna la riga com'e', che e' la risposta giusta
        #    (il verbo e' idempotente).
        self.repo.set_attivo(registro_id, emittenti_sr_ids, attivo)
        return self.get_registro(registro_id, emittenti_sr_ids)

    # Scopo: la traduzione dei vincoli DB, in una sede sola per i due verbi.
    def _traduci(self, exc: IntegrityError, dati: dict[str, Any]) -> NoReturn:
        map_integrity_error(
            exc,
            unique_constraints=_UNIQUE_CONSTRAINTS,
            fk_constraints=_FK_CONSTRAINTS,
            check_constraints=_CHECK_CONSTRAINTS,
            fallback_code=E_VENDITE_VALIDATION,
            fallback_message="Violazione vincolo DB sul registro di numerazione.",
            context={
                "codice": dati.get("codice"),
                "famiglia_documento": dati.get("famiglia_documento"),
                "prefisso": dati.get("prefisso"),
                "suffisso": dati.get("suffisso"),
            },
        )
