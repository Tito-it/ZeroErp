# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block service per gli indirizzi documento (design
#        brief-design-indirizzi-documenti-vendita, D-1..D-5). Tutta la logica
#        condivisa vive qui — guard di esistenza,
#        validazione snapshot, traduzione errori DB — parametrizzata da una
#        `IndirizziDocumentoConfig` dichiarata una volta per dominio: i
#        service espongono wrapper one-liner.
#
#        Due flussi di upsert (D-4/D-5):
#        - PICKER (origine_indirizzo_id valorizzato): snapshot composto
#          SERVER-SIDE via script.fn_snapshot_indirizzo; dal payload vengono
#          accettati solo i campi di contatto (email/telefono/note).
#        - UNA-TANTUM (origine assente): snapshot libero dal payload,
#          whitelist chiavi + soli valori scalari, con almeno un campo
#          sostanziale. origine_* restano NULL.
#
#        ⭐ Che un indirizzo d'anagrafica sia DEL CLIENTE del documento lo
#        dice il DB: il guard `vendite.trgfn_doc_indirizzi_guard_cliente`
#        sulle sei `*_indirizzi` (`E_INDIRIZZO_DOC_NON_DEL_CLIENTE`, campo
#        `tipo_indirizzo_id`), che guarda anche l'istanza. Fino al 2026-10-12
#        qui c'erano due `require` sull'ownership, la sola sede della regola;
#        e lo slot di default lo riempiva `auto_assegna_indirizzo_default`,
#        ora `vendite.fn_doc_indirizzo_default` (repository,
#        `riempi_indirizzo_default`). Brief
#        brief-db-indirizzi-documento-seguono-il-cliente (R-BE-1, R-BE-2).
#
#        ⭐ In quale stato del documento gli indirizzi si cambiano lo dice il
#        DB: il lock «solo in bozza» dei satelliti
#        (`vendite.trgfn_doc_righe_lock_fuori_bozza`, codice
#        `E_DOC_DATI_COLLEGATI_NON_BOZZA`, 409) e la capability
#        `can_edit_indirizzi`. Fino al 2026-10-11 qui c'era uno
#        `stati_modificabili` per dominio, la seconda copia di quella regola
#        (brief-db-testata-dopo-emissione §11, R-BE-6): il 409 passa com'e'.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator, translate_db_errors


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

# Nome dello slot nel context PDF per ogni tipo indirizzo (config.tipi_indirizzi).
# Il template legge `indirizzi.consegna.*`, non `indirizzi.CON.*`: il codice e'
# vocabolario di dominio, il nome dello slot e' cio' che si scrive in un
# template. Mappa COMPLETA (tutti i tipi a catalogo, non i soli oggi ammessi):
# se un ambito domani ne ammette uno nuovo, lo slot ha gia' un nome e nessuno
# deve ricordarsi di aggiungerlo qui.
INDIRIZZO_SLOT_BY_CODICE: dict[str, str] = {
    "CON": "consegna",
    "FATT": "fatturazione",
    "FORNITURA": "fornitura",
    "RES": "residenza",
    "SPED": "spedizione",
    "SEDELEG": "sede_legale",
    "SEDEOP": "sede_operativa",
    "DOMFISC": "domicilio_fiscale",
    "POSTA": "corrispondenza",
}


# Scopo: Display compatto di uno snapshot ("intestazione — via, cap citta,
#        prov"), mirror del FE `formatSnapshotDisplay`. Ripiega sui componenti
#        quando `display` manca — cosa che sui dati reali accade spesso (26
#        snapshot su 42 al 2026-08-04), mentre `via` c'e' sempre.
def snapshot_display_compatto(s: dict[str, Any]) -> str:
    geo = s.get("display") or ", ".join(
        p for p in (
            s.get("via"),
            " ".join(x for x in (s.get("cap"), s.get("citta")) if x),
            s.get("prov"),
        ) if p
    )
    return " — ".join(p for p in (s.get("intestazione"), geo) if p)


# Scopo: Proiezione degli indirizzi documento per il context PDF — sede unica
#        della forma, condivisa da tutti i domini (estratta il 2026-08-05 alla
#        2a occorrenza, ok Tid; prima viveva privata nel builder DDT).
#
#        Forma: uno slot per ciascun tipo AMMESSO nell'ambito, sempre presente
#        (`None` se il documento non ha quell'indirizzo), e per gli slot pieni
#        l'intero set `SNAPSHOT_KEYS_ORDERED` + `display_compatto`.
#
#        ⚠️ Le chiavi ci sono SEMPRE, ed e' il punto dell'esercizio: il render
#        Jinja usa StrictUndefined, quindi il template puo' scrivere
#        `indirizzi.consegna.via` senza difendersi con `.get()`. Un errore di
#        nome fa fallire il render invece di produrre un indirizzo monco — che
#        e' esattamente come il difetto del template Preventivo e' sopravvissuto
#        fino al 2026-08-04 (brief-db-template-preventivo-indirizzi §2).
#
#        `codici_ammessi` e' dichiarato STATICAMENTE dal builder, non letto da
#        `config.tipi_indirizzi_allowed`: il context deve essere deterministico
#        a parita' di documento (il `context_hash` governa il dedup), e una
#        modifica di configurazione non puo' cambiare la forma di un contesto
#        gia' generato.
def shape_indirizzi_context(
    rows: list[dict[str, Any]],
    *,
    codici_ammessi: tuple[str, ...],
) -> dict[str, Any]:
    per_codice = {r.get("tipo_indirizzo_codice"): (r.get("snapshot") or {}) for r in rows}
    out: dict[str, Any] = {}
    for codice in codici_ammessi:
        slot = INDIRIZZO_SLOT_BY_CODICE.get(codice, codice.lower())
        snapshot = per_codice.get(codice)
        if snapshot is None:
            out[slot] = None
            continue
        shaped = {k: snapshot.get(k) for k in SNAPSHOT_KEYS_ORDERED}
        shaped["display_compatto"] = snapshot_display_compatto(snapshot)
        out[slot] = shaped
    return out

# Scopo: Configurazione per-dominio del BB. Dichiarata una volta a livello di
#        modulo nel service del dominio (vedi ddt_service._INDIRIZZI_CFG).
#        `get_stato` legge il solo codice stato (query leggera, mai il detail
#        completo) per il guard di esistenza; default: repo.get_stato_codice.
@dataclass(frozen=True)
class IndirizziDocumentoConfig:
    repo_factory: Callable[[], Any]
    not_found_code: str
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


# Scopo: Guard condiviso di esistenza del documento: inesistente o fuori
#        perimetro -> not_found_code (404). Lo stato non si giudica qui: lo
#        giudica il lock del DB (vedi header).
def _assert_documento(
    cfg: IndirizziDocumentoConfig,
    repo: Any,
    documento_id: int,
    *,
    op: str,
) -> None:
    get_stato = cfg.get_stato or (lambda r, i: r.get_stato_codice(i))
    stato = get_stato(repo, documento_id)
    ErrorManager.require(
        stato is not None,
        code=cfg.not_found_code,
        message="Documento non trovato.",
        detail=f"documento_id={documento_id}",
        function_name=f"{cfg.fn_prefix}.{op}",
    )


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


# Scopo: GET del pannello indirizzi: slot (tipi ammessi per l'ambito, con
#        flag obbligatorio) + righe correnti. Guard di esistenza: un
#        documento fantasma torna 404, non un pannello vuoto editabile.
def list_indirizzi_documento(
    cfg: IndirizziDocumentoConfig, documento_id: int,
) -> dict[str, Any]:
    repo = cfg.repo_factory()
    _assert_documento(cfg, repo, documento_id, op="list_indirizzi")
    return {
        "tipi_ammessi": repo.list_tipi_indirizzo_ammessi(),
        "indirizzi": repo.list_indirizzi(documento_id),
    }


# Scopo: Upsert di uno slot indirizzo (uno-per-tipo). Vedi header per i due
#        flussi; guard di esistenza (l'appartenenza al cliente e' del DB).
def upsert_indirizzo_documento(
    cfg: IndirizziDocumentoConfig,
    documento_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    op = "upsert_indirizzo"
    repo = cfg.repo_factory()
    _assert_documento(cfg, repo, documento_id, op=op)

    # Gli id del payload passano dal BB: un valore non intero e' un errore di
    # validazione del dominio, non un `ValueError` (500) da un `int()` grezzo.
    # ⚠️ `origine_soggetto_ruolo_id` va al DB cosi' com'e' (lo giudica il
    #    guard cliente): qui se ne controlla solo la forma.
    v = PayloadValidator(
        validation_code=cfg.error_code, function_name=f"{cfg.fn_prefix}.{op}",
    )
    tipo_indirizzo_id = v.require_positive_int(payload, "tipo_indirizzo_id")
    origine_indirizzo_id = v.optional_positive_int(payload, "origine_indirizzo_id")

    raw_snapshot = payload.get("snapshot")
    if raw_snapshot is None:
        raw_snapshot = {}
    ErrorManager.require(
        isinstance(raw_snapshot, dict),
        code=cfg.error_code,
        message="snapshot deve essere un oggetto.",
        function_name=f"{cfg.fn_prefix}.{op}",
    )

    if origine_indirizzo_id is not None:
        # Flusso PICKER: snapshot server-side (D-5) + soli contatti dal payload.
        with _db_errors(cfg, op):
            resolved = repo.snapshot_from_origine(origine_indirizzo_id)
        origine_soggetto_ruolo_id = resolved["origine_soggetto_ruolo_id"]
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
        # il client puo' dichiararla; che sia il cliente del documento lo
        # giudica il guard DB (vedi header). Un vero una-tantum la lascia
        # assente.
        origine_soggetto_ruolo_id = v.optional_positive_int(
            payload, "origine_soggetto_ruolo_id")

    with _db_errors(cfg, op):
        return repo.upsert_indirizzo(
            documento_id=documento_id,
            tipo_indirizzo_id=tipo_indirizzo_id,
            snapshot=snapshot,
            origine_indirizzo_id=origine_indirizzo_id,
            origine_soggetto_ruolo_id=origine_soggetto_ruolo_id,
        )


# Scopo: Rimozione di uno slot indirizzo (lo stato lo giudica il DB).
#        Riga inesistente o di un altro documento -> not_found_code (404,
#        anti-tampering URL).
def delete_indirizzo_documento(
    cfg: IndirizziDocumentoConfig,
    documento_id: int,
    indirizzo_row_id: int,
) -> dict[str, Any]:
    op = "delete_indirizzo"
    repo = cfg.repo_factory()
    _assert_documento(cfg, repo, documento_id, op=op)
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
