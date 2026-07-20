# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
_MODALITA: dict[str, tuple[str, bool, str | None]] = {
    "immediata": ("GIORNALIERO", True, None),
    "differita": ("MASSIVO", False, STATO_FERMATA_EMESSA),
}

# Callback opzionale di progresso per-terna: (lane, esito, errore) — esito
# valorizzato su successo, errore (ServiceError) su fallimento. Serve al
# command per il log progressivo su stdout; l'endpoint non la usa.
OnLaneEsito = Callable[[dict[str, Any], dict[str, Any] | None, ServiceError | None], None]

# Callback opzionale post-discovery: riceve il summary di testata (lane,
# senza_emittente, corsia...) PRIMA dell'esecuzione delle terne — il command
# la usa per stampare l'header in testa al log (parita' col vecchio output).
OnDiscovery = Callable[[dict[str, Any]], None]


# Scopo: Espone le corsie valide (per argparse del command e validazione API).
def modalita_disponibili() -> list[str]:
    return sorted(_MODALITA.keys())


# Scopo: Esegue il GIRO di fatturazione di una corsia: discovery terne
#        emittibili (bound competenza <= cumulativo) + pipeline lotto per
#        terna, best-effort, con fermata `fino_a_stato` (default di corsia).
#        Obiettivo: unico core condiviso da cron e UI (I-1). Perimetro:
#        nessuna gestione canale/registrazione run (restano al chiamante:
#        system_process_context+registered_job nel command, scope operatore
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
) -> dict[str, Any]:
    if modalita not in _MODALITA:
        raise ValueError(f"modalita non valida: {modalita!r} (ammesse: {modalita_disponibili()})")
    tipo_lotto, fatturazione_immediata, fermata_default = _MODALITA[modalita]
    fermata: str | None = (
        fermata_default if fino_a_stato is _FERMATA_DA_CORSIA else fino_a_stato
    )

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
        "dry_run": dry_run,
        "lane": len(terne),
        "senza_emittente": senza_emittente,
        "falliti": 0,
        "per_motivo": {},
        "esiti": [],
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
    return summary
