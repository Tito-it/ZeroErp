# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Core del worker DRAINER della coda stampa (outbox documentale, Fase C
#        C-2b/C-2d). Drena `vendite.fatture_stampa_coda`: per ogni fattura in
#        coda numera (backstop C-2d, idempotente) e genera il PDF via il motore
#        documentale in CONTESTO SISTEMA (C-0, `emittente_scope=None`), poi
#        aggiorna lo stato della riga (FATTO / PENDING-riprova / ERRORE).
#
#        Invarianti (brief-be-fe-processi-fatturazione, §FASE C):
#         - I-4/D-7: la stampa è stupida. Il drainer non conosce «lotto» né
#           «fatturazione»: sa solo drenare la coda un work-item alla volta.
#         - I-4b: il render avviene FUORI dalla transazione di numerazione; la
#           connessione non tiene lock fiscali durante l'I/O di rendering.
#         - Resilienza per-riga: un render fallito incrementa i tentativi e non
#           ferma gli altri (`ERRORE` oltre soglia, altrimenti `PENDING` per il
#           PROSSIMO giro — non ri-lavorato nello stesso, per non ciclare).
#         - Idempotenza: l'indice unico parziale della coda impedisce doppioni
#           vivi; il claim `FOR UPDATE SKIP LOCKED` regge più worker paralleli.
#
#        È il CORE unico (I-1): il management command `draina_coda_stampa` ne è
#        un chiamante sottile (argparse + registered_job + console).
#
#        ⭐ DAL 2026-09-05 IL DRENATORE LAVORA UN EMITTENTE ALLA VOLTA, con
#        l'identità dell'UTENTE TECNICO di quell'emittente — non più su un
#        canale `BYPASSRLS` che attraversa tutte le aziende. Il giro completo
#        (`draina_coda_stampa_per_roster`) itera il roster del processo e
#        chiama questo core una volta per badge, dentro
#        `operator_identity_context`: la RLS su `vendite.fatture_stampa_coda`
#        seleziona da sé le righe giuste, e l'audit dice chi ha stampato.
#        ⛔ Se un emittente non ha un utente tecnico il suo lavoro NON viene
#        fatto, e il giro lo DICE (`emittenti_non_serviti` nell'esito): senza
#        quella riga sarebbe un «FATTO, 0 elaborate» silenzioso, cioè il guasto
#        che la D-9 esiste per rendere visibile.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

from apps.core.db.processi_repository import ProcessiRepository
from apps.core.services.db_error_fields import bersagli_envelope, diagnostica_db
from apps.core.services.error_manager import ServiceError
from apps.core.services.giro_per_azienda import giro_per_azienda
from apps.core.services.processi import PROCESSO_DRAINA_CODA_STAMPA
from apps.documenti.services.document_generation_service import (
    DocumentGenerationService,
)
from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.db.vendite_repository import VenditeRepository

logger = logging.getLogger(__name__)

# Soglia oltre cui una riga passa a ERRORE terminale (P-2: default sensato,
# tarabile). Cadenza worker e cap batch tarabili su volumi veri (P-5).
_SOGLIA_TENTATIVI_DEFAULT = 5
# Righe claimate per giro: batch unico per run (niente re-claim delle righe
# fallite nello stesso giro → nessun ciclo di retry immediato). Backlog >
# limit: lo raccoglie il giro successivo del cron.
_LIMIT_DEFAULT = 500
# Reaper: righe IN_CORSO più vecchie di N minuti = worker morto → riportate a
# PENDING. Soglia larga (≫ tempo di un render) per non toccare worker lenti.
_STALE_MINUTI_DEFAULT = 30

# I contatori che il giro completo somma emittente per emittente. Sede unica:
# aggiungerne uno qui lo fa comparire nell'esito senza toccare il ciclo.
_CHIAVI_AGGREGATE = ("recuperate", "claimate", "fatto", "errore", "riprovabili")


# Scopo: Drena la coda stampa. Perimetro e risultato:
#         1. (opz.) reaper delle righe IN_CORSO stantie → PENDING (o ERRORE
#            oltre soglia: il recupero consuma un tentativo, anti poison-job);
#         2. claim atomico di ≤ `limit` work-item PENDING (SKIP LOCKED);
#         3. per ciascuno: risolve l'emittente dalla fattura, numera (backstop
#            C-2d), genera il PDF in contesto sistema, marca l'esito;
#         4. esito strutturato aggregato per il run-log e la console.
#        Best-effort per-riga: nessun fallimento di render propaga oltre la
#        riga. Un fallimento di scrittura sulla coda (DB) invece propaga: la
#        run va marcata fallita (job_run_log), non mascherata.
def draina_coda_stampa(
    *,
    emittente_fiscale_id: int,
    limit: int = _LIMIT_DEFAULT,
    soglia_tentativi: int = _SOGLIA_TENTATIVI_DEFAULT,
    stale_minuti: int = _STALE_MINUTI_DEFAULT,
    on_item_esito: Callable[[dict[str, Any], dict[str, Any]], None] | None = None,
    repo: VenditePipelineRepository | None = None,
    vendite_repo: VenditeRepository | None = None,
    doc_service: DocumentGenerationService | None = None,
) -> dict[str, Any]:
    repo = repo or VenditePipelineRepository()
    vendite_repo = vendite_repo or VenditeRepository()
    doc_service = doc_service or DocumentGenerationService()

    # Il reaper consuma un tentativo per riga recuperata (anti poison-job):
    # passa la stessa soglia usata da marca_stampa_errore.
    recuperate = (
        repo.reset_stale_stampe_in_corso(
            stale_minuti, soglia_tentativi=soglia_tentativi,
        )
        if stale_minuti > 0 else 0
    )

    items = repo.claim_stampe_pending(limit)

    fatto = 0
    errore = 0        # righe passate a ERRORE terminale
    riprovabili = 0   # righe rimesse a PENDING (ritenteranno al prossimo giro)
    for item in items:
        esito = _lavora_item(
            repo, vendite_repo, doc_service, item, soglia_tentativi,
            emittente_fiscale_id=emittente_fiscale_id,
        )
        if esito["esito"] == "fatto":
            fatto += 1
        elif esito["esito"] == "errore":
            errore += 1
        else:
            riprovabili += 1
        if on_item_esito is not None:
            on_item_esito(item, esito)

    return {
        "emittente_fiscale_id": emittente_fiscale_id,
        "recuperate": recuperate,
        "claimate": len(items),
        "fatto": fatto,
        "errore": errore,
        "riprovabili": riprovabili,
        "soglia_tentativi": soglia_tentativi,
        "limit": limit,
    }


# Scopo: IL GIRO COMPLETO — drena la coda stampa per OGNI emittente servito dal
#        processo `draina_coda_stampa`, uno alla volta, con l'identità del
#        rispettivo utente tecnico. Aggrega gli esiti per il run-log e la
#        console.
#
# ⭐ Il perimetro lo decide il BADGE, non il lavoro: si iterano gli emittenti
#    per cui esiste un utente tecnico. Un emittente senza badge non viene
#    servito — ed è una decisione (D-9: la riga la scrive una persona), non una
#    dimenticanza. Per questo l'esito porta `emittenti_non_serviti`: il numero
#    che distingue «non c'era niente da stampare» da «non ho guardato».
#
# ⚠️ Un emittente che fallisce NON ferma gli altri. Il fallimento è di quel
#    badge: gli altri hanno già fatto il loro lavoro, e buttarlo via perché il
#    terzo è andato storto sarebbe peggio del difetto.
#
# ⛔ Nessun `system_process_context` qui dentro: è il punto del cantiere. Se un
#    giorno ricomparisse, questo giro tornerebbe a vedere tutte le aziende
#    insieme senza che niente lo segnali.
def draina_coda_stampa_per_roster(
    *,
    limit: int = _LIMIT_DEFAULT,
    soglia_tentativi: int = _SOGLIA_TENTATIVI_DEFAULT,
    stale_minuti: int = _STALE_MINUTI_DEFAULT,
    on_item_esito: Callable[[dict[str, Any], dict[str, Any]], None] | None = None,
    on_emittente_esito: Callable[[Mapping[str, Any], dict[str, Any] | None, Exception | None], None] | None = None,
    processi_repo: ProcessiRepository | None = None,
) -> dict[str, Any]:
    # Scopo: il lavoro di UN badge, gia' dentro la sua identita' (la apre il BB).
    def _drena(badge: Mapping[str, Any]) -> dict[str, Any]:
        esito = draina_coda_stampa(
            emittente_fiscale_id=badge["emittente_fiscale_id"],
            limit=limit,
            soglia_tentativi=soglia_tentativi,
            stale_minuti=stale_minuti,
            on_item_esito=on_item_esito,
        )
        esito["emittente_codice"] = badge["emittente_codice"]
        return esito

    # ⭐ Il giro (roster, identita', isolamento, non serviti) e' il BB
    #    `giro_per_azienda` (regola del 2, 2026-11-07): qui restano il lavoro e
    #    il riepilogo.
    giro = giro_per_azienda(
        PROCESSO_DRAINA_CODA_STAMPA,
        _drena,
        evento="stampa_coda",
        on_badge=on_emittente_esito,
        processi_repo=processi_repo,
    )
    per_emittente = [esito for _badge, esito in giro.serviti]
    # ⚠️ Le chiavi da sommare si dichiarano UNA volta (`_CHIAVI_AGGREGATE`).
    totali = {
        chiave: sum(esito.get(chiave, 0) for esito in per_emittente)
        for chiave in _CHIAVI_AGGREGATE
    }
    return {
        **totali,
        "emittenti_serviti": len(per_emittente),
        "emittenti_falliti": giro.falliti,
        # ⭐ Il numero che rompe il silenzio: emittenti attivi che nessun badge
        #    copre. Zero e' la condizione normale; diverso da zero e' una
        #    persona che deve creare un utente tecnico.
        "emittenti_non_serviti": giro.non_serviti,
        "soglia_tentativi": soglia_tentativi,
        "limit": limit,
        "per_emittente": per_emittente,
    }


# Scopo: Lavora un singolo work-item della coda (render di una fattura).
#        Best-effort: qualunque errore di dominio/render viene CATTURATO e
#        registrato sulla riga (marca_stampa_errore decide ERRORE vs PENDING);
#        non propaga, così le altre righe del batch proseguono. Ritorna un dict
#        {esito: 'fatto'|'errore'|'riprovabile', ...} per il tally/console.
def _lavora_item(
    repo: VenditePipelineRepository,
    vendite_repo: VenditeRepository,
    doc_service: DocumentGenerationService,
    item: dict[str, Any],
    soglia_tentativi: int,
    *,
    emittente_fiscale_id: int,
) -> dict[str, Any]:
    coda_id = int(item["id"])
    fattura_id = int(item["sorgente_id"])
    try:
        # Emittente autoritativo dalla fattura (la coda non lo denormalizza:
        # brief §5). None = fattura sparita/fuori-portata → errore registrato.
        entity = vendite_repo.get_fattura_for_documento_generation(fattura_id)
        if entity is None:
            stato = repo.marca_stampa_errore(
                coda_id,
                errore={
                    "code": "E_FATTURA_NON_TROVATA",
                    "message": "Fattura in coda non risolta (sparita o fuori portata).",
                    "fattura_id": fattura_id,
                },
                soglia_tentativi=soglia_tentativi,
            )
            return _esito_da_stato(stato, code="E_FATTURA_NON_TROVATA")

        # Il repo risolve la PK emittente con LEFT JOIN: fattura esistente ma
        # senza record EF (dato sporco) → errore PARLANTE sulla riga, non un
        # TypeError generico a valle.
        if entity.get("emittente_fiscale_id") is None:
            stato = repo.marca_stampa_errore(
                coda_id,
                errore={
                    "code": "E_FATTURA_EMITTENTE_NON_RISOLTO",
                    "message": "Emittente fiscale non risolto per la fattura in coda.",
                    "fattura_id": fattura_id,
                },
                soglia_tentativi=soglia_tentativi,
            )
            return _esito_da_stato(stato, code="E_FATTURA_EMITTENTE_NON_RISOLTO")

        # C-2d: numerazione backstop PRIMA del render (idempotente).
        repo.numera_fattura_backstop(fattura_id)

        # ⭐ Render DENTRO IL PERIMETRO dell'utente tecnico (2026-09-05): lo
        # scope non e' piu' `None` («vedo tutto») ma la lista di UN emittente,
        # quello per cui questo giro sta lavorando. ⇒ `guard_emittente_in_scope`
        # verifica che la fattura appartenga davvero a quell'emittente: un
        # controllo che prima NON esisteva — il worker generava il documento di
        # chiunque.
        # ⚠️ Difesa in profondita', non il filtro primario: le righe di coda le
        # seleziona gia' la RLS (`rls_fatture_stampa_coda_ef_whitelist`), che
        # sotto l'identita' tecnica mostra solo il proprio emittente. Qui si
        # prende il caso in cui quella policy non ci fosse.
        documento = doc_service.genera_documento(
            None,
            emittente_fiscale_id=int(entity["emittente_fiscale_id"]),
            sorgente_tipo_id=int(item["sorgente_tipo_id"]),
            sorgente_id=fattura_id,
            sorgente_uid=str(item["sorgente_uid"]),
            # Il tipo lo porta la riga (§9): senza, su una sorgente con piu'
            # tipi la risoluzione si fermerebbe con AMBIGUO.
            tipo_documento_output_id=item.get("tipo_documento_output_id"),
            template_documento_id=item.get("template_documento_id"),
            emittente_scope=[emittente_fiscale_id],
        )
        repo.marca_stampa_fatto(coda_id, int(documento["id"]))
        return {"esito": "fatto", "documento_id": int(documento["id"])}

    except ServiceError as exc:
        errore = _errore_riga_coda(exc)
        stato = repo.marca_stampa_errore(
            coda_id, errore=errore, soglia_tentativi=soglia_tentativi,
        )
        logger.warning(
            "stampa_coda.render_fallito coda_id=%s fattura_id=%s code=%s stato=%s",
            coda_id, fattura_id, errore["code"], stato,
        )
        return _esito_da_stato(stato, code=str(errore["code"]))

    except Exception as exc:  # resilienza per-riga voluta
        errore = _errore_riga_coda(exc)
        stato = repo.marca_stampa_errore(
            coda_id, errore=errore, soglia_tentativi=soglia_tentativi,
        )
        logger.warning(
            "stampa_coda.render_errore_imprevisto coda_id=%s fattura_id=%s "
            "code=%s type=%s stato=%s",
            coda_id, fattura_id, errore["code"], type(exc).__name__, stato,
        )
        return _esito_da_stato(stato, code=str(errore["code"]))


# Scopo: il MOTIVO che finisce sulla riga di coda, coi suoi canali: codice di
#        dominio, frase leggibile, dettaglio, campo e bersagli.
#
# ⭐ BE-6 (brief numerazione §8). Qui dentro passa anche il BACKSTOP di
#    numerazione (`numera_fattura_backstop`), che dal 2026-08-25 puo' RIFIUTARE:
#    il cancello di `fn_get_next_progressivo` respinge un documento la cui data
#    e' anteriore all'ultimo numero emesso sul sezionale. Prima in coda finiva
#    `ProgrammingError` col testo dentro — cioe' un render fallito muto su un
#    rifiuto che ha un nome, un campo e un bersaglio.
#
# ⚠️ Il backstop gira SENZA UN OPERATORE DAVANTI: la riga di coda e' l'unico
#    posto dove quel motivo puo' essere letto, e va scritto qui o non esiste da
#    nessuna parte.
#
# ⭐ UNO SOLO PER I DUE RAMI, e non e' economia di righe: un `ServiceError` di
#    dominio porta gli stessi canali (`targets`), e prima li perdeva — la stessa
#    riga di coda raccontava due storie diverse a seconda di quale `except`
#    l'avesse presa.
#
# ⭐ Si legge dal BB `diagnostica_db`, non ricopiando `diag.*`: i punti che
#    traducono un errore DB sono gia' cinque, e una sesta lettura parziale e' il
#    modo in cui divergono. Su un'eccezione non-DB il BB torna semplicemente
#    tutto vuoto, e valgono i ripieghi.
def _errore_riga_coda(exc: BaseException) -> dict[str, Any]:
    diag = diagnostica_db(exc)
    # ⚠️ `message_primary` prima di `str(exc)`: su un errore PL/pgSQL il secondo
    #    e' il messaggio PIU' lo stack CONTEXT, e in una riga di coda che
    #    qualcuno leggera' a mano quella e' la parte che nasconde la frase.
    messaggio = (
        diag.messaggio
        or getattr(exc, "message", None)
        or str(exc)
    )
    errore: dict[str, Any] = {
        "code": diag.codice or getattr(exc, "code", None) or type(exc).__name__,
        "message": str(messaggio),
    }
    # Le chiavi si mettono SOLO se c'e' qualcosa da dire: una chiave presente e
    # vuota non vuol dire «nessun campo», vuol dire «campo rotto» — stessa
    # disciplina dei bersagli nel runner.
    dettaglio = diag.detail or getattr(exc, "detail", None)
    if dettaglio:
        errore["detail"] = dettaglio
    if diag.campo:
        errore["campo"] = diag.campo
    bersagli = bersagli_envelope(diag.bersagli or getattr(exc, "targets", ()))
    if bersagli:
        errore["bersagli"] = bersagli
    return errore


# Scopo: Traduce lo stato risultante della coda (ERRORE terminale vs PENDING
#        riprovabile) nell'esito del tally del drainer. Confronto sulla
#        costante del repo (owner del vocabolario stati), non su letterale.
def _esito_da_stato(stato: str, *, code: str) -> dict[str, Any]:
    if stato == VenditePipelineRepository.STAMPA_STATO_ERRORE:
        return {"esito": "errore", "code": code}
    return {"esito": "riprovabile", "code": code}
