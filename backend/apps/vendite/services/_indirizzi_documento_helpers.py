# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block service per gli indirizzi documento (design
#        brief-design-indirizzi-documenti-vendita, D-1..D-5). Tutta la logica
#        condivisa vive qui — guard esistenza/stato, ownership del picker,
#        validazione snapshot, traduzione errori DB — parametrizzata da una
#        `IndirizziDocumentoConfig` dichiarata una volta per dominio: i
#        service espongono wrapper one-liner.
#
#        Due flussi di upsert (D-4/D-5):
#        - PICKER (origine_indirizzo_id valorizzato): snapshot composto
#          SERVER-SIDE via script.fn_snapshot_indirizzo; dal payload vengono
#          accettati solo i campi di contatto (email/telefono/note). Guard di
#          OWNERSHIP: l'indirizzo deve appartenere al soggetto_ruolo del
#          cliente del documento (anti-tampering: senza guard un id qualsiasi
#          congelerebbe l'indirizzo di un ALTRO cliente sul documento).
#        - UNA-TANTUM (origine assente): snapshot libero dal payload,
#          whitelist chiavi + soli valori scalari, con almeno un campo
#          sostanziale. origine_* restano NULL.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import translate_db_errors

logger = logging.getLogger(__name__)

# Chiavi ammesse nello snapshot (shape canonico fn_snapshot_indirizzo +
# campi di contatto aggiunti dal BE). Tutto il resto viene scartato.
# La tupla ORDINATA e' la fonte unica: i consumer che devono garantire
# chiavi fisse (context builder PDF con StrictUndefined) la importano —
# mai ridichiarare il mirror a mano (drift silenzioso sul PDF).
SNAPSHOT_KEYS_ORDERED: tuple[str, ...] = (
    "intestazione", "via", "cap", "citta", "prov", "stato",
    "display", "email", "telefono", "note",
)
SNAPSHOT_KEYS: frozenset[str] = frozenset(SNAPSHOT_KEYS_ORDERED)
# Campi di contatto integrabili dal payload anche nel flusso picker.
_CONTACT_KEYS: frozenset[str] = frozenset({"email", "telefono", "note"})
# Almeno una di queste chiavi deve essere valorizzata in un una-tantum.
_SUBSTANTIVE_KEYS: frozenset[str] = frozenset({"via", "citta", "display"})

# Scopo: Configurazione per-dominio del BB. Dichiarata una volta a livello di
#        modulo nel service del dominio (vedi ddt_service._INDIRIZZI_CFG).
#        `get_stato` legge il solo codice stato (query leggera, mai il detail
#        completo); default: repo.get_stato_codice.
@dataclass(frozen=True)
class IndirizziDocumentoConfig:
    repo_factory: Callable[[], Any]
    stati_modificabili: frozenset[str]
    not_found_code: str
    stato_error_code: str
    error_code: str
    fn_prefix: str
    get_stato: Callable[[Any, int], str | None] | None = None


# Scopo: Traduzione uniforme degli errori DB del flusso indirizzi (trigger
#        whitelist E_TIPO_INDIRIZZO, fn E_INDIRIZZO_SNAPSHOT_NOT_FOUND, FK):
#        stessa envelope su tutti i domini, nessun 500 grezzo. Delega al BB
#        condiviso `translate_db_errors` (core payload_helpers) col fallback
#        code della cfg di dominio.
@contextmanager
def _db_errors(cfg: IndirizziDocumentoConfig, op: str) -> Iterator[None]:
    with translate_db_errors(
        context={"op": f"{cfg.fn_prefix}.{op}"},
        fallback_code=cfg.error_code,
        fallback_message="Violazione vincolo DB sugli indirizzi documento.",
    ):
        yield


# Scopo: Guard condiviso esistenza (+ opzionale editabilita') del documento.
#        Esistenza -> not_found_code (404); stato fuori perimetro ->
#        stato_error_code. Ritorna lo stato per eventuali usi del chiamante.
def _assert_documento(
    cfg: IndirizziDocumentoConfig,
    repo: Any,
    documento_id: int,
    *,
    op: str,
    richiedi_modificabile: bool,
) -> str:
    get_stato = cfg.get_stato or (lambda r, i: r.get_stato_codice(i))
    stato = get_stato(repo, documento_id)
    ErrorManager.require(
        stato is not None,
        code=cfg.not_found_code,
        message="Documento non trovato.",
        detail=f"documento_id={documento_id}",
        function_name=f"{cfg.fn_prefix}.{op}",
    )
    assert stato is not None
    if richiedi_modificabile:
        ErrorManager.require(
            stato in cfg.stati_modificabili,
            code=cfg.stato_error_code,
            message=f"Indirizzi non modificabili nello stato {stato}.",
            detail=f"ammessi={sorted(cfg.stati_modificabili)}",
            function_name=f"{cfg.fn_prefix}.{op}",
        )
    return stato


# Scopo: Normalizza un dict snapshot dal payload: whitelist chiavi, soli
#        valori scalari (str/int/float -> str trim), stringhe vuote rimosse
#        (coerenza null vs empty). Oggetti/array/bool vengono scartati: nel
#        documento si congela solo testo.
def _clean_snapshot(raw: dict[str, Any], allowed: frozenset[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if k not in allowed or isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            v = str(v)
        if not isinstance(v, str):
            continue
        v = v.strip()
        if v:
            out[k] = v
    return out


# Scopo: Tipo di default dell'ambito: CON (Consegna, standard cross-dominio)
#        → fallback FATT → primo ammesso (mirror della regola FE UX v2).
def _tipo_default(tipi_ammessi: list[dict[str, Any]]) -> dict[str, Any] | None:
    return (
        next((x for x in tipi_ammessi if x["tipo_indirizzo_codice"] == "CON"), None)
        or next((x for x in tipi_ammessi if x["tipo_indirizzo_codice"] == "FATT"), None)
        or (tipi_ammessi[0] if tipi_ammessi else None)
    )


# Scopo: Auto-assegnazione BEST-EFFORT dell'indirizzo di default alla
#        creazione del documento (UX v2): se il cliente ha un indirizzo di
#        RUOLO di tipo CON (altrimenti FATT), viene congelato nello slot
#        default. Mai bloccante: qualsiasi errore viene loggato e la
#        creazione del documento procede (l'operatore puo' sempre impostare
#        l'indirizzo dal pannello; l'obbligo resta sul guard DB all'emissione).
def auto_assegna_indirizzo_default(
    cfg: IndirizziDocumentoConfig, documento_id: int,
) -> None:
    try:
        repo = cfg.repo_factory()
        default = _tipo_default(repo.list_tipi_indirizzo_ammessi())
        if default is None:
            return
        # Slot gia' valorizzato (es. cascata dal documento sorgente): non toccare.
        esistenti = {r["tipo_indirizzo_id"] for r in repo.list_indirizzi(documento_id)}
        if default["tipo_indirizzo_id"] in esistenti:
            return
        soggetto_ruolo, istanza_utility = repo.get_ancora_indirizzi_documento(
            documento_id)
        if soggetto_ruolo is None:
            return
        # Catena di priorita' (decisa con Tid 2026-07-12): per ciascun tipo
        # (CON, poi FATT) si prova a risolvere l'indirizzo.
        # Dal 2026-07-31 i due layer (RUOLO con aggancio origine → SOGGETTO
        # senza) vivono dentro `script.fn_resolve_indirizzo_documento`, che
        # applica anche la **precedenza all'istanza** del documento: qui resta
        # solo la priorita' fra i TIPI, che e' regola di UX e non di dominio.
        for tipo_codice in ("CON", "FATT"):
            risolto = repo.resolve_indirizzo_documento(
                soggetto_ruolo_id=soggetto_ruolo,
                istanza_utility_id=istanza_utility,
                tipo_codice=tipo_codice,
            )
            if risolto is not None:
                # `origine_indirizzo_id` valorizzato = layer RUOLO (riga
                # agganciabile); NULL con `origine_soggetto_ruolo_id` valorizzato
                # = layer SOGGETTO, che il FE distingue dal vero una-tantum
                # digitato (quello non ha nessuna delle due origini).
                repo.upsert_indirizzo(
                    documento_id=documento_id,
                    tipo_indirizzo_id=int(default["tipo_indirizzo_id"]),
                    snapshot=dict(risolto["snapshot"]),
                    origine_indirizzo_id=risolto["origine_indirizzo_id"],
                    origine_soggetto_ruolo_id=risolto["origine_soggetto_ruolo_id"],
                )
                return
    except Exception:
        logger.warning(
            "auto-assegnazione indirizzo default fallita (best-effort) "
            "documento_id=%s prefix=%s", documento_id, cfg.fn_prefix,
            exc_info=True,
        )


# Scopo: GET del pannello indirizzi: slot (tipi ammessi per l'ambito, con
#        flag obbligatorio) + righe correnti. Guard di esistenza: un
#        documento fantasma torna 404, non un pannello vuoto editabile.
def list_indirizzi_documento(
    cfg: IndirizziDocumentoConfig, documento_id: int,
) -> dict[str, Any]:
    repo = cfg.repo_factory()
    _assert_documento(cfg, repo, documento_id, op="list_indirizzi",
                      richiedi_modificabile=False)
    return {
        "tipi_ammessi": repo.list_tipi_indirizzo_ammessi(),
        "indirizzi": repo.list_indirizzi(documento_id),
    }


# Scopo: Upsert di uno slot indirizzo (uno-per-tipo). Vedi header per i due
#        flussi; guard stato (documento modificabile) + ownership picker.
def upsert_indirizzo_documento(
    cfg: IndirizziDocumentoConfig,
    documento_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    op = "upsert_indirizzo"
    repo = cfg.repo_factory()
    _assert_documento(cfg, repo, documento_id, op=op, richiedi_modificabile=True)

    tipo_indirizzo_id = payload.get("tipo_indirizzo_id")
    ErrorManager.require(
        tipo_indirizzo_id is not None,
        code=cfg.error_code,
        message="tipo_indirizzo_id obbligatorio.",
        function_name=f"{cfg.fn_prefix}.{op}",
    )

    raw_snapshot = payload.get("snapshot")
    if raw_snapshot is None:
        raw_snapshot = {}
    ErrorManager.require(
        isinstance(raw_snapshot, dict),
        code=cfg.error_code,
        message="snapshot deve essere un oggetto.",
        function_name=f"{cfg.fn_prefix}.{op}",
    )

    origine_indirizzo_id = payload.get("origine_indirizzo_id")
    if origine_indirizzo_id is not None:
        # Flusso PICKER: snapshot server-side (D-5) + soli contatti dal payload.
        with _db_errors(cfg, op):
            resolved = repo.snapshot_from_origine(int(origine_indirizzo_id))
        origine_soggetto_ruolo_id = resolved["origine_soggetto_ruolo_id"]
        # Ownership: l'indirizzo deve appartenere al cliente del documento.
        # Se il soggetto_ruolo del documento non e' risolvibile (BA assente)
        # il guard non e' applicabile e resta la sola whitelist tipi.
        doc_soggetto_ruolo = repo.get_soggetto_ruolo_documento(documento_id)
        ErrorManager.require(
            doc_soggetto_ruolo is None
            or origine_soggetto_ruolo_id == doc_soggetto_ruolo,
            code=cfg.error_code,
            message="L'indirizzo selezionato non appartiene al cliente del documento.",
            detail=(f"origine_soggetto_ruolo_id={origine_soggetto_ruolo_id}, "
                    f"documento_soggetto_ruolo_id={doc_soggetto_ruolo}"),
            function_name=f"{cfg.fn_prefix}.{op}",
        )
        snapshot = dict(resolved["snapshot"])
        snapshot.update(_clean_snapshot(raw_snapshot, _CONTACT_KEYS))
    else:
        # Flusso UNA-TANTUM (D-4): snapshot dal payload, whitelist + sostanza.
        snapshot = _clean_snapshot(raw_snapshot, SNAPSHOT_KEYS)
        ErrorManager.require(
            any(k in snapshot for k in _SUBSTANTIVE_KEYS),
            code=cfg.error_code,
            message=(
                "snapshot una-tantum vuoto: valorizzare almeno via/citta "
                "(oppure passare origine_indirizzo_id per un indirizzo del cliente)."
            ),
            function_name=f"{cfg.fn_prefix}.{op}",
        )
        # Provenienza "anagrafica soggetto" (picker su riga fonte=soggetto):
        # il client puo' dichiararla, ma SOLO se coincide col cliente del
        # documento (anti-tampering); un vero una-tantum la lascia assente.
        origine_soggetto_ruolo_id = payload.get("origine_soggetto_ruolo_id")
        if origine_soggetto_ruolo_id is not None:
            doc_soggetto_ruolo = repo.get_soggetto_ruolo_documento(documento_id)
            ErrorManager.require(
                doc_soggetto_ruolo is not None
                and int(origine_soggetto_ruolo_id) == doc_soggetto_ruolo,
                code=cfg.error_code,
                message=(
                    "origine_soggetto_ruolo_id non coincide con il cliente "
                    "del documento."
                ),
                function_name=f"{cfg.fn_prefix}.{op}",
            )
            origine_soggetto_ruolo_id = int(origine_soggetto_ruolo_id)

    with _db_errors(cfg, op):
        return repo.upsert_indirizzo(
            documento_id=documento_id,
            tipo_indirizzo_id=int(tipo_indirizzo_id),
            snapshot=snapshot,
            origine_indirizzo_id=(
                int(origine_indirizzo_id) if origine_indirizzo_id is not None else None
            ),
            origine_soggetto_ruolo_id=origine_soggetto_ruolo_id,
        )


# Scopo: Rimozione di uno slot indirizzo (solo documento modificabile).
#        Riga inesistente o di un altro documento -> not_found_code (404,
#        anti-tampering URL).
def delete_indirizzo_documento(
    cfg: IndirizziDocumentoConfig,
    documento_id: int,
    indirizzo_row_id: int,
) -> dict[str, Any]:
    op = "delete_indirizzo"
    repo = cfg.repo_factory()
    _assert_documento(cfg, repo, documento_id, op=op, richiedi_modificabile=True)
    with _db_errors(cfg, op):
        deleted = repo.delete_indirizzo(documento_id, indirizzo_row_id)
    ErrorManager.require(
        deleted,
        code=cfg.not_found_code,
        message="Indirizzo non trovato sul documento.",
        detail=f"indirizzo_id={indirizzo_row_id}",
        function_name=f"{cfg.fn_prefix}.{op}",
    )
    return {"deleted": True, "id": indirizzo_row_id}
