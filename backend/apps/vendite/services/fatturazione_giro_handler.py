# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Handler del job `FATTURAZIONE_GIRO` (coda lavori generica, C-3): il
#        giro di fatturazione on-demand richiesto dall'operatore. È il primo
#        consumatore della coda `dbops.coda_lavori`. Registrato nel registry
#        handler (`handler_code = fatturazione_giro_default`, dal seed DB) al
#        boot di `VenditeConfig.ready()`.
#
#        Contesto d'esecuzione: il drainer lo invoca DENTRO
#        `operator_identity_context` (run_as=OPERATORE) → RLS ATTIVA con
#        l'identità dell'operatore che ha accodato. La discovery
#        (`fn_list_emittibili_lane`) e l'esecuzione della pipeline sono quindi
#        **scoped all'operatore via RLS** («esegue con i permessi
#        dell'operatore», guida Gestione code di lavoro). Nessun filtro
#        emittente esplicito qui: lo scope è la RLS, non un parametro.
#
#        Invariante I-1: chiama lo STESSO core del cron
#        (`esegui_giro_fatturazione`), niente seconda implementazione. Corsia
#        `differita` (on-demand): si ferma a EMESSA (D-1); la numerazione è un
#        atto separato (C-4). Best-effort per-terna (il core non solleva su
#        terna fallita): l'esito strutturato diventa il `result` del job.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from apps.core.services.coda_lavori.drain_engine import contesto_terminale
from apps.core.services.error_manager import ServiceError
from apps.vendite.services._fatturazione_job_helpers import (
    JOB_TYPE_FATTURAZIONE_GIRO,
    MOTIVO_ESECUZIONE_FALLITA,
    TernaKey,
    corsia_del_giro,
    messaggio_gruppi_non_serviti,
    parse_competenza_mese,
    parse_data_iso,
    parse_gruppi,
    spiega_gruppi_non_serviti,
    terna_key,
)

logger = logging.getLogger(__name__)

# handler_code seedato in dbops.coda_lavori_tipi per il tipo FATTURAZIONE_GIRO.
HANDLER_CODE = "fatturazione_giro_default"

# La corsia dell'EMISSIONE MIRATA (BF-1) NON e' ridichiarata qui: si importa
# dal driver, che ne e' l'owner (`_MODALITA`). Un secondo letterale "mirata"
# in questo modulo si sarebbe potuto disallineare dal dizionario delle corsie
# — e il sintomo sarebbe stato un giro che parte e non fattura nulla.
# L'import e' locale alla funzione, come quello del core: il modulo e'
# registrato in `ready()` e non deve tirarsi dietro la catena driver al boot.

# Codice errore per payload di giro malformato: fallimento di dominio parlante
# (finisce in `coda.ultimo_errore`; non è una risposta HTTP → non va in
# error_policies). Parse condiviso in _fatturazione_job_helpers (regola del 2).
E_GIRO_PAYLOAD = "E_FATTURAZIONE_GIRO_PAYLOAD"

# Emissione MIRATA che non produce nemmeno un lotto: il perimetro qui e'
# NOMINALE — l'operatore ha indicato quei gruppi, uno per uno. «Zero lotti su N
# gruppi chiesti» non e' un giro senza lavoro (quello e' il caso del giro di
# massa, ed e' legittimo): e' una richiesta esplicita non soddisfatta, e deve
# risultare tale nella coda. Stesso principio del ritiro delle bandiere sui task
# per-fattura: chi chiede e non ottiene non legge «fatto».
E_GIRO_NESSUN_LOTTO = "E_FATTURAZIONE_GIRO_NESSUN_LOTTO"


# Scopo: Esegue il giro di fatturazione on-demand. `payload`:
#        `{competenza_mese: ISO, fino_a_stato?: codice, gruppi?: [chiavi]}`.
#        `scope`: catturato all'enqueue (`{auth_user_id, emittente_ids}`) — qui
#        NON usato per filtrare (lo fa la RLS del contesto operatore), presente
#        per il vincolo DB run_as↔scope e per l'audit. Ritorna l'esito compatto
#        del giro (senza la lista per-terna) come `result` del job.
#
#        Due modi nello STESSO job type, distinti dalla presenza di `gruppi`:
#        senza → giro di massa del mese (corsia differita, comportamento
#        storico); con → EMISSIONE MIRATA sui soli gruppi richiesti (corsia
#        mirata). Un solo verbo, un solo handler: la differenza e' il
#        perimetro, non il processo (invariante I-1).
def fatturazione_giro_handler(
    payload: dict[str, Any], *, scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    competenza = parse_competenza_mese(
        payload.get("competenza_mese"), error_code=E_GIRO_PAYLOAD,
    )
    fino_a_stato = payload.get("fino_a_stato")
    gruppi = parse_gruppi(payload.get("gruppi"), error_code=E_GIRO_PAYLOAD)
    # ⭐ La data documento dichiarata per i lotti che questo giro creera'
    #    (BE-1). ⛔ `parse_data_iso` e NON `parse_competenza_mese`: la seconda
    #    normalizza al 1° del mese e trasformerebbe la data scelta in un'altra,
    #    senza sollevare niente.
    # ⚠️ Assente = la decide la politica del registro. Non e' «oggi».
    data_documento = parse_data_iso(
        payload.get("data_documento"),
        error_code=E_GIRO_PAYLOAD,
        campo="data_documento",
    )

    # Import locale: evita di caricare la catena driver al boot del modulo
    # (registrato in ready()); il core è l'unico punto di verità I-1.
    from apps.vendite.services.fatturazione_driver_service import (
        esegui_giro_fatturazione,
    )

    kwargs: dict[str, Any] = {
        # ⭐ La corsia arriva dal PAYLOAD quando chi accoda l'ha scelta (il batch
        #    notturno produce sia «immediata» sia «differita»); altrimenti la
        #    decide la regola condivisa — la stessa che l'accodamento ha usato
        #    per comporre la chiave di dedup, cosi' le due non possono divergere.
        "modalita": payload.get("modalita")
        or corsia_del_giro(JOB_TYPE_FATTURAZIONE_GIRO, gruppi=gruppi),
        "competenza": competenza,
    }
    if gruppi:
        kwargs["gruppi"] = gruppi
    if fino_a_stato:
        kwargs["fino_a_stato"] = fino_a_stato
    if data_documento is not None:
        kwargs["data_documento"] = data_documento

    summary = esegui_giro_fatturazione(**kwargs)

    # Emissione mirata a vuoto: si fallisce, invece di restituire un successo
    # muto (difetto misurato il 2026-08-03, job 141). DUE cause distinte, e
    # vanno tenute separate:
    #   - terne trovate ma pipeline fallita (`falliti` > 0) → la causa PRIMARIA
    #     e' negli esiti per terna, e puo' essere TRANSIENTE (lock, DB): niente
    #     marca terminale (i retry della coda hanno senso). ⚠️ Dal 2026-08-16
    #     la diagnosi gira ANCHE qui: prima veniva soppressa per l'intero giro
    #     («racconterebbe la cosa sbagliata»), ma quella motivazione e' caduta
    #     con `terne_pronte` — ora la diagnosi sa distinguere per gruppo, e la
    #     soppressione per-giro lasciava muta una commessa in BOZZA che stava
    #     nello stesso giro della corsia rotta: la stessa classe di silenzio
    #     del §11.4 punto 3, sull'altro ramo;
    #   - nessuna terna → la diagnosi di perimetro spiega perche', ed e'
    #     deterministica (una commessa in BOZZA resta in BOZZA al 5° tentativo).
    if gruppi and not summary.get("lotti"):
        if summary.get("falliti"):
            _fallisci_giro_mirato_per_errori_terna(gruppi, competenza, summary)
        _fallisci_giro_mirato(gruppi, competenza, summary)

    # Emissione mirata PARZIALE: lotti prodotti, ma qualche gruppo richiesto
    # non e' stato servito. Era il caso PEGGIORE dei tre perche' l'unico
    # silenzioso: «zero fatture» solleva ed e' un errore parlante, «2 su 3»
    # sembrava un successo pieno e il lavoro non fatturato restava fermo senza
    # che nessuno lo cercasse. NON si solleva — i lotti prodotti sono lavoro
    # vero e il job e' riuscito per la sua parte — ma l'esito porta il
    # consuntivo, cosi' il FE puo' dire «2 su 3, il terzo no perche'…».
    #
    # ⚠️ Il «chi manca» e' MISURATO a consuntivo (`fn_esito_gruppi_giro` sui
    # lotti prodotti), non piu' previsto alla discovery: fra discovery e
    # pipeline le righe di un gruppo possono essere prese da un giro
    # concorrente, e la previsione lo dava per coperto — pieno successo su un
    # gruppo non fatturato (§8.2/§9.7 del brief).
    if gruppi and summary.get("lotti"):
        _annota_esito_gruppi(summary, competenza)

    # Compatta per il `result` del job (la lista per-terna gonfierebbe il jsonb;
    # il dettaglio vive nei log/task_runs, correlati via job_run). La chiave
    # `lotti` NON si potata: e' l'estratto compatto che alimenta il «vai al
    # lotto» del FE, e senza di essa l'operatore dovrebbe cercare a mano nella
    # lista lotti il contenitore appena prodotto.
    return {k: v for k, v in summary.items() if k != "esiti"}


# Scopo: Annota sull'esito del job il CONSUNTIVO per gruppo di un giro mirato
#        che ha prodotto lotti. Distingue i tre esiti del DB, e la distinzione
#        e' il punto:
#          - SERVITO           → nulla da dire, e' il lavoro fatto;
#          - NON_SERVITO       → restano righe da emettere: e' il caso su cui
#                                l'operatore agisce, quindi si DIAGNOSTICA il
#                                perche' (stessa fotografia del giro a vuoto);
#          - FATTURATO_ALTROVE → non resta nulla da emettere, le righe sono su
#                                fatture di ALTRI lotti. Non e' un errore: e' il
#                                lavoro preso da un altro giro. Raccontarlo come
#                                «non servito» manderebbe l'operatore a cercare
#                                un problema che non c'e'.
#        Nessuna chiave aggiunta se non c'e' niente da dire: un esito che
#        elenca liste vuote e' rumore.
#
#        ⚠️ Consuntivo e diagnosi sono LETTURE a valle di lavoro gia'
#        COMMITTATO: le fatture ci sono. Se una delle due fallisce (il cancello
#        RLS di `fn_esito_gruppi_giro` solleva `E_LOTTO_NON_TROVATO` su un lotto
#        fuori scope, o il DB non risponde) l'eccezione NON deve salire:
#        manderebbe in ERRORE un job riuscito, perdendo `lotti` — cioe' il «vai
#        al lotto» del FE, unico aggancio ai contenitori appena prodotti — e la
#        coda rifarebbe il giro, che al secondo colpo non trova piu' nulla e
#        fallisce con «gia' emesse»: un'emissione riuscita raccontata come
#        fallita. Stesso principio della resilienza per-lotto di
#        `fatturazione_numera_handler`. Il buco NON si ingoia: un consuntivo non
#        misurato e' un fatto, e va nell'esito con il suo codice.
def _annota_esito_gruppi(summary: dict[str, Any], competenza: date) -> None:
    lotto_ids = [
        int(l["lotto_id"]) for l in (summary.get("lotti") or []) if l.get("lotto_id")
    ]
    if not lotto_ids:
        return
    try:
        _misura_esito_gruppi(summary, competenza, lotto_ids)
    except Exception as exc:  # il giro e' gia' riuscito
        code = getattr(exc, "code", type(exc).__name__)
        logger.warning(
            "fatturazione_giro.consuntivo_non_misurato lotti=%s code=%s",
            lotto_ids, code,
        )
        summary["gruppi_esito_non_misurato"] = {"code": code, "lotti": lotto_ids}


# Scopo: la misura vera e propria di `_annota_esito_gruppi` — separata perche' il
#        guard di quella non deve poter nascondere per sbaglio altro codice.
def _misura_esito_gruppi(
    summary: dict[str, Any], competenza: date, lotto_ids: list[int],
) -> None:
    from apps.vendite.db.commesse_repository import CommesseRepository

    esiti = CommesseRepository().esito_gruppi_giro(lotto_ids)

    non_serviti = [e["gruppo_key"] for e in esiti if e["esito"] == "NON_SERVITO"]
    altrove = [e["gruppo_key"] for e in esiti if e["esito"] == "FATTURATO_ALTROVE"]

    if non_serviti:
        # Il PERCHE' resta della diagnostica: il consuntivo dice CHE non e'
        # stato servito, non per quale ostacolo.
        #
        # ⚠️ Le terne FALLITE del giro entrano nella diagnosi come CONTESTO, e
        # sono un fatto gia' in mano nostra (gli esiti per terna del core). Un
        # gruppo il cui lavoro pronto ricade in una corsia rotta non e' bloccato
        # dal perimetro: l'esecuzione si e' interrotta e si rilancia. Senza
        # questo incrocio quel gruppo si prendeva «verificare emittente e
        # utility della commessa» — una causa inesistente, su cose che sono a
        # posto (§10.6 → §11 del brief emittibilita').
        #
        # La distinzione e' PER GRUPPO, non per giro: un `if falliti > 0`
        # globale avrebbe spento il messaggio anche sui gruppi bloccati sul
        # serio nello stesso giro, sostituendo un messaggio impreciso con un
        # silenzio — che e' il difetto peggiore dei due.
        summary["gruppi_non_serviti"] = _diagnostica_e_spiega(
            non_serviti, competenza, terne_fallite=_terne_fallite(summary),
        )
    if altrove:
        summary["gruppi_fatturati_altrove"] = altrove


# Scopo: Le corsie del giro la cui pipeline e' FALLITA, come tuple confrontabili.
#        Sono un FATTO gia' misurato dal core (un esito per terna, con `ok`
#        False), non una nuova query: si legge cio' che il giro ha appena
#        registrato.
#        ⚠️ Va chiamata sul `summary` del DRIVER, che porta `esiti`: i result
#        compattati (i dict NUOVI costruiti dalle `{k: v ...}` ai punti di
#        uscita — la compattazione non muta `summary`) non li hanno piu'.
def _terne_fallite(summary: dict[str, Any]) -> frozenset[TernaKey]:
    # `is False`, non `not e.get("ok")`: un esito SENZA la chiave (il dry-run
    # del driver ne produce cosi') non e' una terna fallita — e' un esito che
    # non ha girato. Col falsy-check ogni corsia del giro sarebbe risultata
    # «rotta», e ogni gruppo non servito si sarebbe sentito dire «rilancia».
    return frozenset(
        terna_key(e) for e in (summary.get("esiti") or []) if e.get("ok") is False
    )


# Scopo: Diagnostica e classifica un elenco di gruppi non serviti — la STESSA
#        fotografia e la STESSA classificazione per entrambi gli esiti che la
#        usano: il giro a vuoto (che poi solleva) e il giro parziale (che
#        arricchisce l'esito). Sede unica di proposito: se la catena cambia
#        (un kwarg nuovo, un filtro), i due percorsi non possono divergere.
def _diagnostica_e_spiega(
    gruppi_non_serviti: tuple[str, ...] | list[str],
    competenza: date,
    *,
    terne_fallite: frozenset[TernaKey] = frozenset(),
) -> list[dict[str, Any]]:
    # Import locale come il core: l'handler e' importato in `ready()` e non deve
    # tirarsi dietro il repository al boot.
    from apps.vendite.db.commesse_repository import CommesseRepository

    diagnosi = CommesseRepository().diagnostica_gruppi(
        gruppi=gruppi_non_serviti, competenza_mese=competenza,
    )
    return spiega_gruppi_non_serviti(diagnosi, terne_fallite=terne_fallite)


# Scopo: SOLLEVA per il giro mirato in cui le terne c'erano ma OGNI pipeline e'
#        fallita. Il messaggio parte dagli errori per terna (dagli `esiti` del
#        core), che sono la causa primaria. NON terminale: un errore pipeline
#        puo' essere transiente e i retry con backoff della coda sono il
#        rimedio giusto — al contrario del fallimento di perimetro qui sotto.
#
#        ⚠️ La diagnosi gira ANCHE qui (2026-08-16), col contesto delle terne
#        fallite: i gruppi delle corsie rotte sono gia' raccontati dagli errori
#        di terna, ma un gruppo fermo per un'ALTRA causa nello stesso giro —
#        una commessa in BOZZA la cui corsia non e' nemmeno partita — prima
#        restava muto dietro l'errore dell'altra corsia, e il job non-terminale
#        veniva ritentato 5 volte senza che nessuno lo dicesse. Nel messaggio
#        entrano le sole cause NON di corsia (le altre sarebbero ridondanti);
#        il dettaglio completo va nel context, che la coda persiste.
def _fallisci_giro_mirato_per_errori_terna(
    gruppi: tuple[str, ...],
    competenza: date,
    summary: dict[str, Any],
) -> None:
    errori = [
        f"{e.get('errore_code') or '?'}: {e.get('errore_detail') or ''}".strip(": ")
        for e in summary.get("esiti") or []
        if e.get("ok") is False
    ]
    spiegazioni = _diagnostica_e_spiega(
        gruppi, competenza, terne_fallite=_terne_fallite(summary),
    )
    altre_cause = [
        s for s in spiegazioni if s["motivo"] != MOTIVO_ESECUZIONE_FALLITA
    ]
    message = (
        "Nessun lotto prodotto: il giro sui gruppi selezionati è fallito "
        f"({'; '.join(errori) or 'nessun dettaglio dalle terne'})."
    )
    if altre_cause:
        dettagli = "; ".join(
            f"{s.get('commessa_codice') or s.get('gruppo_key')}: {s['dettaglio']}"
            for s in altre_cause[:3]
        )
        message += f" Inoltre: {dettagli}."
    raise ServiceError(
        code=E_GIRO_NESSUN_LOTTO,
        message=message,
        detail=f"gruppi richiesti: {len(gruppi)}, terne fallite: {summary['falliti']}",
        context={
            "errori_terna": errori,
            "gruppi_non_serviti": spiegazioni,
            "summary": {k: v for k, v in summary.items() if k != "esiti"},
        },
    )


# Scopo: Diagnostica i gruppi richiesti e SOLLEVA con il motivo per ciascuno.
#        Obiettivo: l'operatore che ha chiesto «fattura questo» deve leggere
#        perche' non e' successo, non un generico «nulla era fatturabile».
#        Il messaggio finisce in `coda_lavori.ultimo_errore.message`, che il FE
#        rende com'e'; il dettaglio strutturato (un motivo per gruppo) va in
#        `context`, che il motore della coda PERSISTE dentro `ultimo_errore`
#        (drain_engine._lavora_item): resta interrogabile senza riparsare il
#        testo.
#
#        `context["terminale"]`: il fallimento e' DETERMINISTICO — una commessa in
#        BOZZA resta in BOZZA anche al quinto tentativo. Senza questa marca la
#        coda ripeterebbe il giro `max_tentativi` volte (5 per FATTURAZIONE_GIRO)
#        con backoff, lasciando il job «in corso» a video per minuti e scrivendo
#        cinque volte lo stesso errore.
def _fallisci_giro_mirato(
    gruppi: tuple[str, ...],
    competenza: date,
    summary: dict[str, Any],
) -> None:
    # `terne_fallite` passa anche da qui (oggi e' sempre vuoto per costruzione:
    # con `falliti > 0` solleva prima il ramo per-errori-terna) cosi' il
    # contratto «stessa fotografia, stessa classificazione» resta VERO per
    # firma e non per coincidenza di ordinamento dei rami.
    spiegazioni = _diagnostica_e_spiega(
        gruppi, competenza, terne_fallite=_terne_fallite(summary),
    )
    raise ServiceError(
        code=E_GIRO_NESSUN_LOTTO,
        message=messaggio_gruppi_non_serviti(
            spiegazioni, totale_richiesti=len(gruppi),
        ),
        detail=f"gruppi richiesti: {len(gruppi)}, lotti prodotti: 0",
        context=contesto_terminale(
            gruppi_non_serviti=spiegazioni,
            summary={k: v for k, v in summary.items() if k != "esiti"},
        ),
    )


# Scopo: Registra l'handler nel registry della coda. Chiamata da
#        `VenditeConfig.ready()` (import del modulo). Dispatch controllato:
#        `dbops.coda_lavori_tipi.handler_code` → questa funzione.
def register() -> None:
    from apps.core.services.coda_lavori.handler_registry import register_handler
    register_handler(HANDLER_CODE, fatturazione_giro_handler)
