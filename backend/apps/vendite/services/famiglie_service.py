# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service delle FAMIGLIE DI DOCUMENTO — validazione del payload,
#        creazione che passa dalla madre e traduzione dei vincoli DB in errori
#        parlanti. Brief: brief-be-fe-crud-registri-di-numerazione §11.10.
# ------------------------------------------------------------
#
# ⛔ I QUATTRO CODICI DEI GUARD NON SI TRADUCONO QUI, ED E' LA VOCE BE-F3 DEL BRIEF.
#    `E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE`, `..._SERIE_NON_DISCRIMINA`,
#    `..._CHIAVE_IMMUTABILE` e `..._TABELLA_GIA_NUMERATA` (dal 2026-10-20: era
#    l'indice `uq_famiglie_documento_tabella_attiva`, che questo service
#    traduceva nominando la famiglia occupante; la regola e' passata nel guard
#    dei riferimenti, perche' la tabella ora viene dalla sorgente e un indice
#    non fa join — brief-db-grammatica-unica-documenti 2c) arrivano come **P0001** — li solleva
#    `script.fn_log_and_raise_error` dentro un trigger, non un vincolo — quindi
#    NON sono `IntegrityError` e non passano di qui: risalgono al middleware,
#    che legge il codice strutturato dall'eccezione e lo risolve con la policy
#    generata dal catalogo. ⚠️ Intercettarli qui vorrebbe dire riscrivere il
#    loro messaggio accanto a quello del database: due frasi per lo stesso
#    rifiuto, che divergono alla prima revisione.
# ⭐ Il campo da accendere lo porta il guard (`campo` nel contesto -> COLUMN ->
#    `error.fields`), non questo service. Dal 2026-10-23 anche
#    `..._RIFERIMENTO_INESISTENTE` e' un DATO_ERRATO (400) col campo
#    (`codice_interno`, `colonna_numero`, `colonna_billing_account`,
#    `colonna_serie`): era TECNICO (500) sulla premessa «la riga la scrive una
#    migrazione», caduta col CRUD (D1 di brief-be-verifica-documentazione-api).

from __future__ import annotations

import logging
from typing import Any, NoReturn

from django.db import IntegrityError, transaction

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import (
    PayloadValidator,
    map_integrity_error,
    vincolo_violato,
)
from apps.core.services.value_normalizer import empty_to_none
from apps.vendite.db.famiglie_repository import (
    _CAMPI_CREATE,
    _CAMPI_UPDATE,
    FamiglieDocumentoRepository,
)

logger = logging.getLogger(__name__)

E_VENDITE_VALIDATION = "E_VENDITE_VALIDATION"
E_VENDITE_DUPLICATO = "E_VENDITE_DUPLICATO"
E_VENDITE_NOT_FOUND = "E_VENDITE_NOT_FOUND"

# Il `codice` dell'operatore (dal 2026-09-24). Fuori dalla mappa generica
# perche' il campo da accendere dipende dal verbo: in modifica e' `codice`, in
# creazione il codice nasce uguale al `codice_interno` (trigger) — e' quello
# che l'operatore ha scritto, ed e' quello da correggere.
# ⚠️ Letto con `vincolo_violato` (confine di parola): `..._codice` e' un
#    prefisso di `..._codice_interno`, e un confronto per sottostringa li
#    confonderebbe.
_UQ_CODICE = "uq_famiglie_documento_codice"

_UNIQUE_CONSTRAINTS: dict[str, tuple] = {
    "uq_famiglie_documento_codice_interno": (
        E_VENDITE_DUPLICATO,
        "Esiste già una famiglia di documento con questo codice interno.",
        "codice_interno",
    ),
}

# ⭐ La famiglia e' quella di una SORGENTE (G-5, 2026-10-20): il suo
#    `codice_interno` e' il `codice_interno` di `config.sorgenti`, e la FK lo
#    pretende. Il drawer sceglie da `list_sorgenti_numerabili`, quindi qui arriva
#    solo un client che scrive il codice a mano: gli si dice che cosa manca, non
#    «violazione vincolo».
# ⚠️ Su una famiglia ATTIVA rifiuta prima il guard dei riferimenti
#    (`E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE`, la sorgente non dichiara
#    una tabella: 400 sul campo `codice_interno`, dal 2026-10-23); su una creata
#    SPENTA il guard non guarda, e risponde la FK — stesso campo, stesso 400.
#    Provato su dbdev il 2026-10-20: i due rami sono vivi.
_FK_CONSTRAINTS: dict[str, tuple] = {
    "fk_famiglie_documento_sorgenti": (
        E_VENDITE_VALIDATION,
        "Il codice interno della famiglia deve essere quello di una sorgente "
        "di documento esistente (config.sorgenti).",
        "codice_interno",
    ),
}

# I campi che la madre pretende: senza uno di questi non si crea niente.
# ⚠️ `colonna_serie` NON e' qui — la sua assenza e' un'informazione («questa
#    famiglia non gestisce le serie»), non un campo dimenticato.
# ⚠️ E dal 2026-09-14 (P-9 di brief-db-modifiche-certe-ciclo-vendita-e-articolo,
#    changeSet `20260914-07/-11`) NEMMENO `colonna_billing_account`: `NULL` =
#    «questa famiglia non ha un billing account», ed e' la forma dell'ordine di
#    acquisto, la cui controparte e' un `soggetto_ruolo`. Stessa forma di
#    `colonna_serie`; la madre normalizza `''` a NULL e non la pretende piu'.
#    Finche' questa riga la pretendeva, il BE rifiutava PRIMA della madre: una
#    capacita' del DB non ancora esposta, non un difetto.
_OBBLIGATORI_CREATE: tuple[tuple[str, str], ...] = (
    ("codice_interno", "Il codice interno della famiglia è obbligatorio."),
    ("descrizione", "La descrizione della famiglia è obbligatoria."),
    ("colonna_numero", "La colonna che porta il numero è obbligatoria."),
)


class FamiglieDocumentoService:
    """Orchestrazione del CRUD delle famiglie di documento."""

    def __init__(self) -> None:
        self.repo = FamiglieDocumentoRepository()
        self._v = PayloadValidator(validation_code=E_VENDITE_VALIDATION)

    # =================================================================
    # Lettura
    # =================================================================

    def list_famiglie(self, **filtri: Any) -> tuple[list[dict[str, Any]], int]:
        return self.repo.list_famiglie(**filtri)

    def list_lookup(self) -> list[dict[str, Any]]:
        return self.repo.list_lookup()

    def list_sorgenti_numerabili(self) -> list[dict[str, Any]]:
        return self.repo.list_sorgenti_numerabili()

    # Scopo: il dettaglio, o un 404 parlante.
    def get_famiglia(self, famiglia_id: int) -> dict[str, Any]:
        famiglia = self.repo.get_famiglia(famiglia_id)
        if famiglia is None:
            ErrorManager.raise_error(
                code=E_VENDITE_NOT_FOUND,
                message="Famiglia di documento non trovata.",
                context={"famiglia_id": famiglia_id},
            )
        return famiglia

    # =================================================================
    # Scrittura
    # =================================================================

    # Scopo: normalizza il payload — una sede sola per create e update.
    # ⛔ Stringhe vuote a NULL (`feedback_null_vs_empty`): su `colonna_serie` la
    #    differenza NON e' cosmetica. `NULL` significa «questa famiglia non
    #    gestisce le serie» ed e' cio' che legge
    #    `fn_check_registro_serie_ammessa`; una stringa vuota salvata come `''`
    #    la farebbe risultare una colonna dichiarata — e il guard dei
    #    riferimenti la cercherebbe sul documento, non trovandola.
    def _normalizza(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {k: empty_to_none(v) for k, v in payload.items()}

    # Scopo: il contratto delle chiavi di ogni verbo — le colonne che il
    #        repository scrive (i parametri della madre in creazione).
    # ⛔ Una chiave in piu' e' un 400 parlante, dal 2026-09-26. Fino a quel
    #    giorno il repository la SCARTAVA IN SILENZIO (`if c in dati`, e in
    #    creazione `dati.get(c)` sui soli parametri della madre): un
    #    salvataggio «riuscito» senza aver scritto il campo — per esempio
    #    `attivo` o `codice` spediti in modifica, che hanno il loro verbo.
    def _verifica_chiavi(
        self, payload: dict[str, Any], *, ammesse: tuple[str, ...], verbo: str,
    ) -> None:
        self._v.validate_allowed_keys(
            payload,
            allowed=frozenset(ammesse),
            message=f"Campi non ammessi in {verbo} della famiglia di documento.",
        )

    def crea_famiglia(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._verifica_chiavi(payload, ammesse=_CAMPI_CREATE, verbo="creazione")
        dati = self._normalizza(payload)
        for campo, messaggio in _OBBLIGATORI_CREATE:
            if not dati.get(campo):
                ErrorManager.raise_error(
                    code=E_VENDITE_VALIDATION,
                    message=messaggio,
                    context={"field": campo},
                )
        try:
            with transaction.atomic():
                esito = self.repo.crea_famiglia(dati)
        except IntegrityError as exc:
            self._traduci(exc, dati, in_modifica=False)
        famiglia = self.get_famiglia(esito["famiglia_id"])
        # ⭐ Quanti registri ha provveduto la madre: e' meta' del lavoro che la
        #    creazione ha appena fatto, e la maschera deve poterlo dire.
        famiglia["registri_creati"] = esito["registri_creati"]
        return famiglia

    def update_famiglia(
        self, famiglia_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        self._verifica_chiavi(payload, ammesse=_CAMPI_UPDATE, verbo="modifica")
        dati = self._normalizza(payload)
        # Il `codice` si cambia, non si svuota: e' NOT NULL con un CHECK di non
        # vuoto, e un `""` normalizzato a NULL arriverebbe come violazione
        # generica su un campo che l'operatore ha davanti.
        if "codice" in dati and dati["codice"] is None:
            ErrorManager.raise_error(
                code=E_VENDITE_VALIDATION,
                message="Il codice della famiglia non può essere vuoto.",
                context={"field": "codice"},
            )
        # ⛔ Un PATCH senza campi e' un 400, non un 200 che non scrive (Tid,
        #    2026-10-20, brief-be-verifica-documentazione-api §A2).
        self._v.require_campi_da_aggiornare(dati)
        try:
            with transaction.atomic():
                toccate = self.repo.update_famiglia(famiglia_id, dati)
        except IntegrityError as exc:
            self._traduci(exc, dati, in_modifica=True)
        # ⚠️ `toccate == 0` vuol dire che la famiglia non esiste (il payload
        #    vuoto e' gia' un 400, qui sopra): lo dice la rilettura, che
        #    solleva 404.
        logger.debug("update_famiglia id=%s righe=%s", famiglia_id, toccate)
        return self.get_famiglia(famiglia_id)

    # Scopo: accende o spegne la famiglia.
    # ⛔ Non si ricontrolla qui se e' spegnibile: a rifiutare e' il guard di
    #    disattivazione, e la check che la vista legge serve a spegnere il
    #    pulsante. Un controllo applicativo sarebbe il secondo elenco.
    def set_attivo(self, famiglia_id: int, attivo: bool) -> dict[str, Any]:
        # ⭐ Si scrive prima e si rilegge una volta sola: «zero righe» ha due
        #    cause e la rilettura le separa da sola — inesistente -> 404, gia'
        #    nello stato richiesto -> la riga com'e', che e' la risposta giusta
        #    (il verbo e' idempotente).
        self.repo.set_attivo(famiglia_id, attivo)
        return self.get_famiglia(famiglia_id)

    # Scopo: la traduzione dei vincoli DB, in una sede sola per i due verbi.
    def _traduci(
        self, exc: IntegrityError, dati: dict[str, Any], *, in_modifica: bool,
    ) -> NoReturn:
        if vincolo_violato(exc, [_UQ_CODICE]) is not None:
            # ⚠️ Il campo lo decide il VERBO, non la presenza della chiave nel
            #    payload: in creazione il `codice` non si scrive (non e' in
            #    `_CAMPI_CREATE`, e dal 2026-09-26 `_verifica_chiavi` lo
            #    rifiuta prima) — il vincolo violato e' quello del codice nato
            #    dal `codice_interno`.
            campo = "codice" if in_modifica else "codice_interno"
            ErrorManager.raise_error(
                code=E_VENDITE_DUPLICATO,
                message=(
                    "Esiste già una famiglia di documento con questo codice."
                    if campo == "codice" else
                    "Il codice interno coincide con il codice di un'altra "
                    "famiglia di documento: alla nascita il codice vale il "
                    "codice interno, e i codici sono unici."
                ),
                detail=str(exc),
                context={"field": campo, campo: dati.get(campo)},
                cause=exc,
            )
        map_integrity_error(
            exc,
            unique_constraints=_UNIQUE_CONSTRAINTS,
            fk_constraints=_FK_CONSTRAINTS,
            fallback_code=E_VENDITE_VALIDATION,
            fallback_message="Violazione vincolo DB sulla famiglia di documento.",
            context={"codice_interno": dati.get("codice_interno")},
        )
