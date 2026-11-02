# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Core del driver di fatturazione (cockpit Fase C, step C-1 —
#        brief-be-fe-processi-fatturazione). Estratto da
#        run_fatturazione_batch: discovery delle terne (emittente,
#        tipo_doc, utility) emittibili di una corsia + pipeline lotto per
#        terna, best-effort (una terna in errore non blocca le altre).
#        UN SOLO processo, due modi di avvio (invariante I-1/D-1): il
#        management command (canale sistema, cron) e l'endpoint
#        `POST /vendite/fatturazione/run/` (scope operatore) chiamano
#        ENTRAMBI questo core — mai una seconda implementazione.
#        Gate fiscale (D-1): `fino_a_stato` ferma la catena allo stato
#        indicato; il default per corsia vive in _MODALITA (immediata =
#        fino in fondo, differita = EMESSA: la numerazione e' un processo
#        separato avviato da umano).
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any, Callable

from apps.core.services.service_errors import ServiceError
from apps.vendite.db.commesse_repository import CommesseRepository
from apps.vendite.db.pipeline_repository import LOTTO_META_KEY_FATTURAZIONE_IMMEDIATA
from apps.vendite.services.pipeline_service import run_lotto_pipeline_until_done

# Stato di fermata del gate fiscale (D-1): il giro differito/da-UI arriva a
# EMESSA; la DEFINITIVA (numerazione+stampa) e' il verbo «Rendi definitive».
STATO_FERMATA_EMESSA = "EMESSA"

# Sentinel: "fermata non passata dal chiamante" != "nessuna fermata (None)".
# Il default per corsia sta in _MODALITA; None esplicito = fino in fondo.
_FERMATA_DA_CORSIA: Any = object()

# Mappatura corsia → (tipo_lotto pipeline, filtro fatturazione_immediata,
# fermata di default). Convenzione del modello a due corsie + D-1:
# l'immediata numera da sola (nessuna fermata), la differita si ferma a
# EMESSA — la numerazione e' un atto umano separato.
#
# La terza voce, `mirata`, e' l'EMISSIONE MIRATA per gruppo fatturabile
# (decisione BF-1, brief BE/FE): il filtro di corsia e' **None**, cioe' non
# filtra. E' deliberato, non una dimenticanza — motivo per esteso:
#   la lista dei gruppi fatturabili (vw_dash_competenza_gruppi) NON conosce la
#   corsia, quindi mostra anche i gruppi di commesse a fatturazione immediata.
#   Se il giro mirato girasse su corsia differita, quei gruppi sarebbero
#   selezionabili a video ma produrrebbero ZERO lotti in silenzio. La
#   selezione esplicita dell'operatore e' un perimetro piu' preciso
#   dell'instradamento automatico: quando c'e', la corsia non serve piu'.
# La fermata resta EMESSA: il gate fiscale I-7 non si tocca.
MODALITA_MIRATA = "mirata"
# Corsia del giro on-demand di MASSA: differita, fermata a EMESSA (gate D-1).
# ⭐ Sta QUI e non nell'handler (dov'era, come `_MODALITA_ONDEMAND`) perche'
# l'owner delle corsie e' questo modulo: chi la usa la importa, non la
# riscrive. Serve a due consumatori — handler ed enqueue — e un secondo
# letterale avrebbe potuto disallinearsi dal dizionario `_MODALITA`.
MODALITA_ONDEMAND = "differita"
_MODALITA: dict[str, tuple[str, bool | None, str | None]] = {
    "immediata": ("GIORNALIERO", True, None),
    "differita": ("MASSIVO", False, STATO_FERMATA_EMESSA),
    MODALITA_MIRATA: ("MASSIVO", None, STATO_FERMATA_EMESSA),
}

# Corsie avviabili dallo SCHEDULER (management command/cron): tutte MENO la
# mirata, che nasce solo da una selezione umana di gruppi e senza gruppi
# degenererebbe in un giro di massa su entrambe le corsie insieme.
# DERIVATA da _MODALITA, non riscritta: un elenco parallelo si sarebbe
# disallineato in silenzio alla prima corsia aggiunta.
_MODALITA_SCHEDULABILI: frozenset[str] = frozenset(_MODALITA) - {MODALITA_MIRATA}

# Callback opzionale di progresso per-terna: (lane, esito, errore) — esito
# valorizzato su successo, errore (ServiceError) su fallimento. Serve al
# command per il log progressivo su stdout; l'endpoint non la usa.
OnLaneEsito = Callable[[Mapping[str, Any], dict[str, Any] | None, ServiceError | None], None]

# Callback opzionale post-discovery: riceve il summary di testata (lane,
# senza_emittente, corsia...) PRIMA dell'esecuzione delle terne — il command
# la usa per stampare l'header in testa al log (parita' col vecchio output).
OnDiscovery = Callable[[dict[str, Any]], None]


# Scopo: Espone le corsie SCHEDULABILI (argparse del management command). NON
#        include `mirata`, che non e' una corsia del calendario ma l'esito di
#        una selezione umana di gruppi: esporla come choice del cron
#        significherebbe offrire un giro senza perimetro su entrambe le corsie.
def modalita_disponibili() -> list[str]:
    return sorted(_MODALITA_SCHEDULABILI)


# Scopo: Esegue il GIRO di fatturazione di una corsia: discovery terne
#        emittibili (bound competenza <= cumulativo) + pipeline lotto per
#        terna, best-effort, con fermata `fino_a_stato` (default di corsia).
#        Obiettivo: unico core condiviso da cron e UI (I-1). Perimetro:
#        nessuna gestione canale/registrazione run (restano al chiamante:
#        registered_job nel command, scope operatore
#        nell'endpoint). Risultato: riepilogo strutturato del run — usato
#        come meta di job_run_log e come esito API.
def esegui_giro_fatturazione(
    *,
    modalita: str,
    competenza: date,
    emittente_soggetto_ruolo_id: int | None = None,
    utility_id: int | None = None,
    limit: int = 10000,
    dry_run: bool = False,
    fino_a_stato: Any = _FERMATA_DA_CORSIA,
    on_lane_esito: OnLaneEsito | None = None,
    on_discovery: OnDiscovery | None = None,
    gruppi: tuple[str, ...] | list[str] | None = None,
    data_documento: date | None = None,
) -> dict[str, Any]:
    if modalita not in _MODALITA:
        raise ValueError(
            f"modalita non valida: {modalita!r} (ammesse: {sorted(_MODALITA.keys())})"
        )
    # La corsia mirata SENZA gruppi degenererebbe in un giro di massa su
    # entrambe le corsie insieme (filtro corsia None + nessun perimetro):
    # fail-fast, mai un default silenzioso.
    if modalita == MODALITA_MIRATA and not gruppi:
        raise ValueError("modalita 'mirata' richiede almeno un gruppo fatturabile")
    tipo_lotto, fatturazione_immediata, fermata_default = _MODALITA[modalita]
    fermata: str | None = (
        fermata_default if fino_a_stato is _FERMATA_DA_CORSIA else fino_a_stato
    )
    gruppi_tuple: tuple[str, ...] | None = None if not gruppi else tuple(gruppi)

    repo = CommesseRepository()

    # Discovery delle terne (emittente, tipo_doc_fiscale, utility) emittibili:
    # sempre via fn_list_emittibili_lane, anche con emittente singolo (che
    # restringe il filtro), perche' il lotto ha bisogno di tipo_doc e utility
    # per terna. `competenza` e' il bound superiore (<=, cumulativo): la lane
    # riporta la competenza_mese con cui creare il lotto. Le righe con
    # tipo_doc NULL sono escluse a monte dalla funzione DB.
    lanes = repo.list_emittibili_lane(
        competenza_mese=competenza,
        utility_id=utility_id,
        emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
        fatturazione_immediata=fatturazione_immediata,
        limit=limit,
        # Emissione mirata: senza questo filtro la discovery restituirebbe
        # TUTTE le terne del perimetro e nascerebbe un lotto vuoto per ognuna.
        gruppi=gruppi_tuple,
    )

    # Un lotto richiede un emittente (emittente_soggetto_ruolo_id NOT NULL):
    # le terne senza emittente non sono fatturabili da qui → saltate e contate.
    terne = [lane for lane in lanes if lane["emittente_soggetto_ruolo_id"] is not None]
    senza_emittente = len(lanes) - len(terne)

    summary: dict[str, Any] = {
        "modalita": modalita,
        "tipo_lotto": tipo_lotto,
        "fatturazione_immediata": fatturazione_immediata,
        "competenza": competenza.isoformat(),
        "fino_a_stato": fermata,
        # Nel riepilogo del giro: a consuntivo, con quale data i lotti sono nati.
        "data_documento": data_documento.isoformat() if data_documento else None,
        "dry_run": dry_run,
        "lane": len(terne),
        "senza_emittente": senza_emittente,
        "falliti": 0,
        "per_motivo": {},
        "esiti": [],
        # Gruppi richiesti (emissione mirata): tenerli nell'esito rende il
        # perimetro leggibile a posteriori nel log/result del job, senza
        # doverlo ricostruire dalla tabella figlia dei lotti.
        "gruppi": list(gruppi_tuple) if gruppi_tuple else None,
        # Lotti prodotti dal giro, COMPATTI: e' il dato del «vai al lotto» del
        # FE. Un giro produce N lotti (un gruppo con righe di tipo doc fiscale
        # diverso finisce in terne diverse — fatto F5/G15 del brief DB), quindi
        # e' una lista, mai un singolo id.
        "lotti": [],
    }
    # Testata disponibile al chiamante PRIMA dell'esecuzione (header nei log).
    if on_discovery is not None:
        on_discovery(summary)
    if not terne:
        return summary

    # DRY-RUN: solo discovery/conteggio (total_candidate gia' nella lane).
    if dry_run:
        summary["esiti"] = [
            {
                "emittente_soggetto_ruolo_id": lane["emittente_soggetto_ruolo_id"],
                "tipo_doc_fiscale_id": lane["tipo_doc_fiscale_id"],
                "utility_id": lane["utility_id"],
                "competenza_mese": lane["competenza_mese"].isoformat(),
                "total_candidate": lane["total_candidate"],
            }
            for lane in terne
        ]
        return summary

    # Esecuzione: un lotto per terna, best-effort. La competenza del lotto e'
    # quella riportata dalla lane (max righe candidate); la select cattura poi
    # via `<=` anche gli eventuali arretrati.
    esiti_per_motivo: dict[str, int] = {}
    falliti = 0
    esiti: list[dict[str, Any]] = []
    for lane in terne:
        base = {
            "emittente_soggetto_ruolo_id": lane["emittente_soggetto_ruolo_id"],
            "tipo_doc_fiscale_id": lane["tipo_doc_fiscale_id"],
            "utility_id": lane["utility_id"],
            "competenza_mese": lane["competenza_mese"].isoformat(),
        }
        try:
            esito = run_lotto_pipeline_until_done(
                competenza_mese=lane["competenza_mese"],
                emittente_soggetto_ruolo_id=lane["emittente_soggetto_ruolo_id"],
                tipo_doc_fiscale_id=lane["tipo_doc_fiscale_id"],
                utility_id=lane["utility_id"],
                tipo_lotto=tipo_lotto,
                meta={LOTTO_META_KEY_FATTURAZIONE_IMMEDIATA: fatturazione_immediata},
                dry_run=False,
                fino_a_stato=fermata,
                # I gruppi non arrivano agli step come parametro: il runner li
                # PERSISTE su vendite.fatturazione_lotti_gruppi nella stessa
                # transazione in cui crea il lotto (contratto §8-bis).
                gruppi=gruppi_tuple,
                # ⭐ La data dichiarata vale per TUTTI i lotti del giro
                # (decisione 5): si scrive alla creazione di ciascuno, e da li'
                # `fn_get_or_create_fattura_header` la usa al posto della
                # politica del registro. None = nessuna dichiarazione.
                data_documento=data_documento,
            )
        except ServiceError as exc:
            falliti += 1
            esiti.append({
                **base,
                "ok": False,
                "errore_code": exc.code,
                "errore_detail": str(exc.detail or exc),
            })
            if on_lane_esito is not None:
                on_lane_esito(lane, None, exc)
            continue
        motivo = str(esito.get("motivo_stop"))
        esiti_per_motivo[motivo] = esiti_per_motivo.get(motivo, 0) + 1
        esiti.append({
            **base,
            "ok": True,
            "lotto_id": esito.get("lotto_id"),
            "motivo_stop": motivo,
            "step_eseguiti": esito.get("step_eseguiti"),
        })
        if on_lane_esito is not None:
            on_lane_esito(lane, esito, None)

    summary["falliti"] = falliti
    summary["per_motivo"] = esiti_per_motivo
    summary["esiti"] = esiti
    # Estratto compatto dei lotti prodotti: sopravvive alla potatura dell'array
    # `esiti` fatta dall'handler di coda (il jsonb del job non deve gonfiarsi),
    # ed e' cio' che permette al FE di offrire N «vai al lotto».
    summary["lotti"] = [
        {
            "lotto_id": e["lotto_id"],
            "tipo_doc_fiscale_id": e["tipo_doc_fiscale_id"],
            "competenza_mese": e["competenza_mese"],
        }
        for e in esiti
        if e.get("ok") and e.get("lotto_id")
    ]
    return summary
