# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service delle FAMIGLIE DI DOCUMENTO — validazione del payload,
#        creazione che passa dalla madre e traduzione dei vincoli DB in errori
#        parlanti. Brief: brief-be-fe-crud-registri-di-numerazione §11.10.
# ------------------------------------------------------------
#
# ⛔ I TRE CODICI DEI GUARD NON SI TRADUCONO QUI, ED E' LA VOCE BE-F3 DEL BRIEF.
#    `E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE`, `..._SERIE_NON_DISCRIMINA`
#    e `..._CHIAVE_IMMUTABILE` arrivano come **P0001** — li solleva
#    `script.fn_log_and_raise_error` dentro un trigger, non un vincolo — quindi
#    NON sono `IntegrityError` e non passano di qui: risalgono al middleware,
#    che legge il codice strutturato dall'eccezione e lo risolve con la policy
#    generata dal catalogo. ⚠️ Intercettarli qui vorrebbe dire riscrivere il
#    loro messaggio accanto a quello del database: due frasi per lo stesso
#    rifiuto, che divergono alla prima revisione.

from __future__ import annotations

import logging
from typing import Any

from django.db import IntegrityError, transaction

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import map_integrity_error, vincolo_violato
from apps.core.services.value_normalizer import empty_to_none
from apps.vendite.db.famiglie_repository import FamiglieDocumentoRepository

logger = logging.getLogger(__name__)

E_VENDITE_VALIDATION = "E_VENDITE_VALIDATION"
E_VENDITE_DUPLICATO = "E_VENDITE_DUPLICATO"
E_VENDITE_NOT_FOUND = "E_VENDITE_NOT_FOUND"

# Il vincolo che merita una frase sua (§11.10 BE-F8), tenuto fuori dalla mappa
# generica perche' il suo messaggio ha bisogno di una LETTURA.
_UQ_TABELLA_ATTIVA = "uq_famiglie_documento_tabella_attiva"
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
    ("schema_tabella", "Lo schema della tabella del documento è obbligatorio."),
    ("nome_tabella", "Il nome della tabella del documento è obbligatorio."),
    ("colonna_numero", "La colonna che porta il numero è obbligatoria."),
)


class FamiglieDocumentoService:
    """Orchestrazione del CRUD delle famiglie di documento."""

    def __init__(self) -> None:
        self.repo = FamiglieDocumentoRepository()

    # =================================================================
    # Lettura
    # =================================================================

    def list_famiglie(self, **filtri: Any) -> tuple[list[dict[str, Any]], int]:
        return self.repo.list_famiglie(**filtri)

    def list_lookup(self) -> list[dict[str, Any]]:
        return self.repo.list_lookup()

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

    def crea_famiglia(self, payload: dict[str, Any]) -> dict[str, Any]:
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
            raise  # pragma: no cover — _traduci solleva sempre
        famiglia = self.get_famiglia(esito["famiglia_id"])
        # ⭐ Quanti registri ha provveduto la madre: e' meta' del lavoro che la
        #    creazione ha appena fatto, e la maschera deve poterlo dire.
        famiglia["registri_creati"] = esito["registri_creati"]
        return famiglia

    def update_famiglia(
        self, famiglia_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
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
        try:
            with transaction.atomic():
                toccate = self.repo.update_famiglia(famiglia_id, dati)
        except IntegrityError as exc:
            self._traduci(exc, dati, in_modifica=True)
            raise  # pragma: no cover — _traduci solleva sempre
        # ⚠️ `toccate == 0` ha due cause — la famiglia non esiste, oppure il
        #    payload non portava nessuna colonna scrivibile — e a distinguerle
        #    e' la rilettura, che nel primo caso solleva 404 ed e' anche cio'
        #    che si deve restituire nel secondo.
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
    ) -> None:
        # ⭐ IL DUPLICATO DELLA TABELLA SI NOMINA, e per questo sta fuori dalla
        #    mappa generica. L'indice e' PARZIALE (`WHERE attivo`), quindi la
        #    riga che blocca c'e' ed e' attiva: un «duplicato» nudo manderebbe
        #    l'operatore a cercarla senza dirgli come si chiama, e la troverebbe
        #    solo scorrendo la lista tabella per tabella.
        if vincolo_violato(exc, [_UQ_TABELLA_ATTIVA]) is not None:
            self._rifiuta_tabella_gia_presa(exc, dati)
        if vincolo_violato(exc, [_UQ_CODICE]) is not None:
            # ⚠️ Il campo lo decide il VERBO, non la presenza della chiave nel
            #    payload: in creazione il `codice` non si scrive (non e' in
            #    `_CAMPI_CREATE`), ma un client che lo mandasse comunque lo
            #    avrebbe in `dati` — e l'errore nominerebbe un campo ignorato.
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
            fallback_code=E_VENDITE_VALIDATION,
            fallback_message="Violazione vincolo DB sulla famiglia di documento.",
            context={
                "codice_interno": dati.get("codice_interno"),
                "schema_tabella": dati.get("schema_tabella"),
                "nome_tabella": dati.get("nome_tabella"),
            },
        )

    # Scopo: il rifiuto che NOMINA la famiglia gia' agganciata a quella tabella.
    # ⚠️ La lettura puo' non trovare niente in una sola circostanza — la riga
    #    concorrente e' stata spenta fra il rifiuto e questa query — e in quel
    #    caso si dice comunque la cosa vera («quella tabella ha gia' la sua
    #    famiglia») senza inventare un nome.
    def _rifiuta_tabella_gia_presa(
        self, exc: IntegrityError, dati: dict[str, Any]
    ) -> None:
        tabella = f"{dati.get('schema_tabella')}.{dati.get('nome_tabella')}"
        schema, nome = dati.get("schema_tabella"), dati.get("nome_tabella")
        occupante = (
            self.repo.get_famiglia_attiva_per_tabella(schema, nome)
            if schema and nome
            else None
        )
        chi = (
            f"«{occupante['descrizione']}» ({occupante['codice_interno']})"
            if occupante
            else "un'altra famiglia attiva"
        )
        ErrorManager.raise_error(
            code=E_VENDITE_DUPLICATO,
            message=(
                f"La tabella {tabella} ha già la sua famiglia di documento: "
                f"{chi}. Una tabella può appartenere a una sola famiglia "
                "attiva — si modifica quella che c'è, o la si spegne prima."
            ),
            detail=str(exc),
            context={"field": "nome_tabella", "tabella_documento": tabella},
            cause=exc,
        )

