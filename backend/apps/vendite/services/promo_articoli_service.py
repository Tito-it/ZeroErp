# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service admin per vendite.promo_articoli.
#        Overlay promo temporale per (articolo, uom) — STADIO 0 del resolver
#        prezzi v5: batte listini e matrice categoria.
#        E' l'UNICO livello che ammette `tipo_variazione = PREZZO_FISSO`
#        (prezzo assoluto sostitutivo).
#
#        Riferimento: sviluppo-listini-v5 §6 + trigger DB
#        `chk_promo_articoli_*` + `ex_promo_articoli_no_overlap`.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.db import IntegrityError

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.services.error_manager import ErrorManager
from apps.core.services.testata_guard import testata_o_not_found
from apps.core.services.payload_helpers import (
    PayloadValidator,
    map_integrity_error,
)
from apps.vendite.db.promo_articoli_repository import (
    _ORDER_COLS,
    PromoArticoliRepository,
)


# Codici errore (registrati in error_policies.py).
E_VENDITE_VALIDATION = "E_VENDITE_VALIDATION"
E_VENDITE_NOT_FOUND = "E_VENDITE_NOT_FOUND"
E_VENDITE_DUPLICATO = "E_VENDITE_DUPLICATO"
E_VENDITE_FK = "E_VENDITE_FK"
E_VENDITE_PROMO_OVERLAP = "E_VENDITE_PROMO_OVERLAP"
# Guard Profilo A promo data-driven (vedi error_policies.py + brief DB
# trigger guard). Stato derivato dalle date correnti, non da una colonna stato.
E_PROMO_RETROATTIVA = "E_PROMO_RETROATTIVA"
E_PROMO_INIZIATA_CAMPI_RISTRETTI = "E_PROMO_INIZIATA_CAMPI_RISTRETTI"
E_PROMO_SCADUTA_IMMUTABILE = "E_PROMO_SCADUTA_IMMUTABILE"


# Whitelist campi mutabili quando la promo e' INIZIATA (oggi compreso fra
# valido_dal e valido_al). Tipo/valore variazione sono bloccati: cambiarli
# in corsa altera i calcoli pricing per i nuovi push e per i riallinea-prezzo
# senza un audit storico chiaro. Per cambiare strategia: chiudere questa
# promo (valido_al=oggi) e crearne una nuova.
_UPDATE_KEYS_INIZIATA: frozenset[str] = frozenset({
    "descrizione",
    "valido_al",
    "meta",
})


# Whitelist order_by ammessi dal service (gate prima del repository), DERIVATA
# dalla whitelist del repository (`_ORDER_COLS`), unica fonte di verita' —
# stesso schema di `_ORDER_BY_CONTRATTI`/`_ORDER_BY_OFFERTE`. Era una copia a
# mano: su offerte la stessa copia aveva gia' divergito in entrambi i versi.
_ORDER_BY_VALIDI: frozenset[str] = frozenset(_ORDER_COLS)


# Chiavi ammesse in create: dimensioni + variazione + date + meta.
_CREATE_KEYS: frozenset[str] = frozenset({
    "codice",
    "descrizione",
    "articolo_id",
    "uom_id",
    "tipo_variazione",
    "valore_variazione",
    "valido_dal",
    "valido_al",
    "meta",
    "attivo",
})

# Chiavi ammesse in update: codice/articolo/uom immutabili (identificatori
# semantici della riga promo). Mutabili: descrizione, variazione, date,
# meta, attivo.
_UPDATE_KEYS: frozenset[str] = frozenset({
    "descrizione",
    "tipo_variazione",
    "valore_variazione",
    "valido_dal",
    "valido_al",
    "meta",
    "attivo",
})

# Campi immutabili in PATCH.
_IMMUTABLE_KEYS: frozenset[str] = frozenset({
    "codice",
    "articolo_id",
    "uom_id",
})


# Valori ammessi per tipo_variazione (coerenti con CHECK DB).
# PREZZO_FISSO e' ammesso SOLO qui (vietato in listini e matrice categoria).
_TIPI_VARIAZIONE: frozenset[str] = frozenset({
    "PERCENTUALE",
    "VALORE_FISSO",
    "PREZZO_FISSO",
})

# Limiti varchar coerenti con DDL.
_MAX_CODICE_LEN = 64
_MAX_DESCRIZIONE_LEN = 255


_MESSAGE = "Payload promo non valido."


# Mapping vincoli DB -> codici errore applicativi (word boundary match).
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "uq_promo_articoli_codice": (
        E_VENDITE_DUPLICATO,
        "Esiste gia' una promo con questo codice.",
        "codice",
    ),
    "ex_promo_articoli_no_overlap": (
        E_VENDITE_PROMO_OVERLAP,
        "Esiste gia' una promo attiva per questo (articolo, uom) nel periodo indicato.",
    ),
}
_FK_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "fk_promo_articoli_articolo": (
        E_VENDITE_FK,
        "Articolo inesistente.",
    ),
    "fk_promo_articoli_uom": (
        E_VENDITE_FK,
        "Unita' di misura inesistente.",
    ),
}


class PromoArticoliService:
    """Service admin per `vendite.promo_articoli` (STADIO 0 resolver)."""

    def __init__(self) -> None:
        self._repo = PromoArticoliRepository()
        self._v = PayloadValidator(validation_code=E_VENDITE_VALIDATION)

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata promo con filtri dimensionali + validita'.
    def list_promo(
        self,
        *,
        search: str | None = None,
        attivo: bool | None = None,
        articolo_id: str | None = None,
        uom_id: int | None = None,
        tipo_variazione: str | None = None,
        valid_at: date | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str = "valido_dal",
        order_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        self._v.validate_order_by(order_by, allowed=_ORDER_BY_VALIDI, order_dir=order_dir)
        # tipo_variazione filter whitelist (evita SQL con valori arbitrari).
        if tipo_variazione is not None:
            ErrorManager.require(
                tipo_variazione in _TIPI_VARIAZIONE,
                code=E_VENDITE_VALIDATION,
                message="Filtro tipo_variazione non valido.",
                detail=f"Ammessi: {', '.join(sorted(_TIPI_VARIAZIONE))}.",
                context={"tipo_variazione": tipo_variazione},
            )
        # articolo_id UUID stringa: validazione formato.
        if articolo_id is not None:
            articolo_id = self._coerce_uuid(articolo_id, field="articolo_id")
        return self._repo.list_promo(
            search=search,
            attivo=attivo,
            articolo_id=articolo_id,
            uom_id=uom_id,
            tipo_variazione=tipo_variazione,
            valid_at=valid_at,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_dir=order_dir,
        )

    # Scopo: Dettaglio singola promo; solleva NOT_FOUND se assente.
    #        Le capability (stato_temporale, can_update, min_valido_*,
    #        non_editable_fields) arrivano da script.fn_capability_promo_articolo
    #        e viaggiano intatte SOTTO `capabilities` (api.md §«Il blob sta
    #        SOTTO `capabilities`»).
    def get_promo(self, record_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(record_id, field="record_id")
        result = testata_o_not_found(
            self._repo.get_promo, record_id,
            code=E_VENDITE_NOT_FOUND, message="Promo non trovata.",
            id_name="record_id", function_name="promo_articoli_service.get_promo",
        )
        result["capabilities"] = self._repo.get_capabilities(record_id)
        return result

    # =================================================================
    # Creazione
    # =================================================================

    # Scopo: Crea una nuova promo con validazione FK + enum + variazione +
    #        date + codice UNIQUE. Mappa UNIQUE/FK/EXCLUDE su codici parlanti.
    def create_promo(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.validate_allowed_keys(payload, allowed=_CREATE_KEYS, message=_MESSAGE)
        data = self._build_create_data(payload)
        self._assert_create_non_retroattiva(data)

        try:
            new_id = self._repo.create_promo(data)
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fk_constraints=_FK_CONSTRAINTS,
                fallback_code=E_VENDITE_VALIDATION,
                fallback_message="Violazione vincolo DB su promo.",
                context={"codice": data.get("codice")},
            )
        return self.get_promo(new_id)

    # =================================================================
    # Aggiornamento
    # =================================================================

    # Scopo: Aggiorna una promo. codice, articolo_id, uom_id sono immutabili:
    #        cambiarli vorrebbe dire rimpiazzare la promo.
    def update_promo(self, record_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.guard_positive_int(record_id, field="record_id")
        self._v.reject_keys(
            payload,
            forbidden=_IMMUTABLE_KEYS,
            reason="Le chiavi identificative della promo sono immutabili.",
            detail_prefix=(
                "codice, articolo_id, uom_id non modificabili. Per cambiarli "
                "disattivare la promo corrente e crearne una nuova. Campi rifiutati"
            ),
            context_extra={"record_id": record_id},
        )
        self._v.validate_allowed_keys(payload, allowed=_UPDATE_KEYS, message=_MESSAGE)
        data = self._build_update_data(payload)

        self._v.require_campi_da_aggiornare(
            data,
            context={"allowed_keys": sorted(_UPDATE_KEYS)},
        )

        # Carica lo stato attuale per applicare guard data-driven.
        # NOTE: get_promo solleva NOT_FOUND se l'id non esiste -> bail-out
        # prima di toccare la tabella, niente race con l'update.
        current = self.get_promo(record_id)

        # Drop no-op: la FE invia tutti i campi del form (non solo quelli
        # cambiati), qui consideriamo modifica reale solo i campi con valore
        # diverso dal corrente. Necessario per non rifiutare PATCH idempotenti
        # in stato INIZIATA con campi non-whitelist invariati.
        data = {k: v for k, v in data.items() if v != current.get(k)}
        if not data:
            return current

        self._assert_patch_allowed_for_data_state(current, data)

        try:
            updated = self._repo.update_promo(record_id, data)
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fk_constraints=_FK_CONSTRAINTS,
                fallback_code=E_VENDITE_VALIDATION,
                fallback_message="Violazione vincolo DB su promo.",
                context={"record_id": record_id},
            )
        ErrorManager.require(
            updated,
            code=E_VENDITE_NOT_FOUND,
            message="Promo non trovata.",
            context={"record_id": record_id},
        )
        return self.get_promo(record_id)

    # =================================================================
    # Helpers privati — composizione dict per repository
    # =================================================================

    # Scopo: Compone il dict create validando ogni campo. Tutti obbligatori
    #        tranne meta e attivo (default DB).
    def _build_create_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        tipo = self._extract_tipo_variazione(payload, required=True)
        valore = self._extract_valore_variazione(payload, required=True, tipo=tipo)
        assert tipo is not None
        assert valore is not None
        data: dict[str, Any] = {
            "codice": self._v.require_string(
                payload, "codice", max_len=_MAX_CODICE_LEN, message=_MESSAGE,
            ),
            "descrizione": self._v.require_string(
                payload, "descrizione", max_len=_MAX_DESCRIZIONE_LEN, message=_MESSAGE,
            ),
            "articolo_id": self._v.require_uuid(payload, "articolo_id", message=_MESSAGE),
            "uom_id": self._v.require_positive_int(payload, "uom_id", message=_MESSAGE),
            "tipo_variazione": tipo,
            "valore_variazione": valore,
            "valido_dal": self._v.require_date(payload, "valido_dal", message=_MESSAGE),
            "valido_al": self._v.require_date(payload, "valido_al", message=_MESSAGE),
        }
        # L'ordine delle date (valido_al non precede valido_dal) lo giudica il
        # DB: guard comune `script.trgfn_guard_date_validita`, E_DATA_AL_MINORE_DAL
        # col campo `valido_al` (dal 2026-09-23). Non si ripete qui.

        attivo = self._v.optional_bool(payload, "attivo")
        if attivo is not None:
            data["attivo"] = attivo
        meta = self._v.optional_meta(payload)
        if meta is not None:
            data["meta"] = meta
        return data

    # Scopo: Compone il dict update. tipo/valore sono coppia: se uno presente
    #        serve anche l'altro (DB enforcerebbe comunque via CHECK ma il
    #        messaggio e' piu' chiaro qui).
    def _build_update_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if "descrizione" in payload:
            data["descrizione"] = self._v.require_string(
                payload, "descrizione", max_len=_MAX_DESCRIZIONE_LEN, message=_MESSAGE,
            )
        # Variazione: se entra almeno una chiave, rivalidiamo la coppia
        # leggendo il valore attuale dal payload (per quello che c'e') e
        # pretendendo la coerenza. NB: valore_variazione dipende da tipo,
        # quindi se cambi tipo devi fornire anche valore (e viceversa).
        if "tipo_variazione" in payload or "valore_variazione" in payload:
            tipo = self._extract_tipo_variazione(payload, required=True)
            valore = self._extract_valore_variazione(
                payload, required=True, tipo=tipo
            )
            data["tipo_variazione"] = tipo
            data["valore_variazione"] = valore

        if "valido_dal" in payload:
            data["valido_dal"] = self._v.require_date(
                payload, "valido_dal", message=_MESSAGE
            )
        if "valido_al" in payload:
            data["valido_al"] = self._v.require_date(
                payload, "valido_al", message=_MESSAGE
            )
        # L'ordine delle date (valido_al non precede valido_dal) lo giudica il
        # DB: guard comune `script.trgfn_guard_date_validita`, E_DATA_AL_MINORE_DAL
        # col campo `valido_al` (dal 2026-09-23). Non si ripete qui.

        if "attivo" in payload:
            value = self._v.optional_bool(payload, "attivo")
            ErrorManager.require(
                value is not None,
                code=E_VENDITE_VALIDATION,
                message="Il campo 'attivo' non puo' essere NULL.",
                context={"field": "attivo"},
            )
            data["attivo"] = value
        if "meta" in payload:
            meta = self._v.optional_meta(payload)
            if meta is not None:
                data["meta"] = meta
        return data

    # =================================================================
    # Helpers privati — type coercion dominio-specifici
    # =================================================================

    # Scopo: Estrae e valida tipo_variazione contro whitelist. `required=True`
    #        lo rende obbligatorio; `False` accetta None. La lettura (stringa,
    #        `strip().upper()`, vocabolario) e' del BB `PayloadValidator`; il
    #        vocabolario resta qui, specchio del CHECK di `promo_articoli`.
    def _extract_tipo_variazione(
        self, payload: dict[str, Any], *, required: bool
    ) -> str | None:
        if required:
            return self._v.require_enum(
                payload, "tipo_variazione", allowed=_TIPI_VARIAZIONE, message=_MESSAGE,
            )
        return self._v.optional_enum(
            payload, "tipo_variazione", allowed=_TIPI_VARIAZIONE, message=_MESSAGE,
        )

    # Scopo: Estrae e valida valore_variazione come Decimal con CHECK
    #        coerenza su tipo: PERC/VAL_FISSO > 0, PREZZO_FISSO >= 0.
    def _extract_valore_variazione(
        self,
        payload: dict[str, Any],
        *,
        required: bool,
        tipo: str | None,
    ) -> Decimal | None:
        # La coercizione (bool e NaN rifiutati) e' del BB `PayloadValidator`;
        # qui resta la coerenza col tipo, che e' di dominio.
        value: Decimal | None
        if required:
            value = self._v.require_decimal(payload, "valore_variazione", message=_MESSAGE)
        else:
            value = self._v.optional_decimal(payload, "valore_variazione", message=_MESSAGE)
            if value is None:
                return None

        # Coerenza con tipo. Convenzione firmata coerente col resolver DB
        # fn_resolve_prezzo_listino_v2: `base * (1 + valore/100)` e
        # `base + valore` -> negativo = sconto, positivo = aumento.
        # Il vincolo pre-v5 era `> 0` (bug storico): bloccava gli sconti
        # promo. Ora ammettiamo negativi; rifiutiamo solo il valore 0 che
        # sarebbe una promo no-op.
        if tipo in ("PERCENTUALE", "VALORE_FISSO"):
            ErrorManager.require(
                value != 0,
                code=E_VENDITE_VALIDATION,
                message=_MESSAGE,
                detail=f"Per tipo_variazione={tipo} il valore_variazione deve essere != 0.",
                context={"tipo_variazione": tipo, "valore_variazione": str(value)},
            )
        elif tipo == "PREZZO_FISSO":
            # PREZZO_FISSO = prezzo assoluto sostitutivo, sempre >= 0.
            ErrorManager.require(
                value >= 0,
                code=E_VENDITE_VALIDATION,
                message=_MESSAGE,
                detail="Per tipo_variazione=PREZZO_FISSO il valore_variazione deve essere >= 0.",
                context={"tipo_variazione": tipo, "valore_variazione": str(value)},
            )
        return value

    # Scopo: Coerce UUID usando il validator centrale. Usato dal filtro di
    #        lista (articolo_id query param) — non serve un helper locale.
    def _coerce_uuid(self, value: Any, *, field: str) -> str:
        return self._v.require_uuid({field: value}, field, message=_MESSAGE)

    # =================================================================
    # Helpers privati — guard data-driven Profilo A promo
    # =================================================================

    # Scopo: in create rifiuta date retroattive. La promo deve partire da
    #        domani in poi (preavviso operativo di 1 gg). Il check su
    #        valido_al e' ridondante: valido_al >= valido_dal (guard comune
    #        delle date a DB) + valido_dal > today implica valido_al > today
    #        per costruzione. Coerente con la decisione DB nel trigger
    #        trgfn_promo_articoli_guard_data_driven.
    def _assert_create_non_retroattiva(self, data: dict[str, Any]) -> None:
        today = oggi_aziendale()
        ErrorManager.require(
            data["valido_dal"] > today,
            code=E_PROMO_RETROATTIVA,
            message="valido_dal non puo' essere oggi o nel passato.",
            detail="In create la data di inizio promo deve essere > oggi.",
            context={
                "valido_dal": data["valido_dal"].isoformat(),
                "today": today.isoformat(),
            },
        )

    # Scopo: in update applica la whitelist campi data-driven. Lo stato e'
    #        derivato dalle date CORRENTI (current), non dal payload:
    #         - SCADUTA  (today > valido_al)        -> immutabile
    #         - INIZIATA (valido_dal <= today <= valido_al) -> whitelist
    #           ristretta (descrizione, valido_al >= today, meta)
    #         - FUTURA   (today < valido_dal)       -> tutto, ma date solo
    #           verso il futuro (no spostamento al passato)
    #
    #        Pre-condizione: `data` contiene solo le modifiche reali
    #        (no-op gia' droppati a monte).
    def _assert_patch_allowed_for_data_state(
        self,
        current: dict[str, Any],
        data: dict[str, Any],
    ) -> None:
        today = oggi_aziendale()
        cur_dal = current["valido_dal"]
        cur_al = current["valido_al"]

        # SCADUTA: nessun campo modificabile.
        if today > cur_al:
            ErrorManager.raise_error(
                code=E_PROMO_SCADUTA_IMMUTABILE,
                message="Promo scaduta non modificabile.",
                detail=(
                    f"valido_al={cur_al.isoformat()} antecedente a oggi. "
                    "Per riproporre la promo creare una nuova riga."
                ),
                context={
                    "stato_data_driven": "SCADUTA",
                    "valido_al": cur_al.isoformat(),
                    "today": today.isoformat(),
                    "campi_richiesti": sorted(data.keys()),
                },
            )

        # INIZIATA: whitelist ristretta + valido_al non puo' tornare al passato.
        if cur_dal <= today <= cur_al:
            forbidden = sorted(set(data.keys()) - _UPDATE_KEYS_INIZIATA)
            ErrorManager.require(
                not forbidden,
                code=E_PROMO_INIZIATA_CAMPI_RISTRETTI,
                message="Promo gia' iniziata: campi modificabili limitati.",
                detail=(
                    f"Solo {sorted(_UPDATE_KEYS_INIZIATA)} mutabili. Per "
                    "cambiare strategia chiudere questa promo (valido_al=oggi) "
                    "e crearne una nuova."
                ),
                context={
                    "stato_data_driven": "INIZIATA",
                    "valido_dal": cur_dal.isoformat(),
                    "valido_al": cur_al.isoformat(),
                    "today": today.isoformat(),
                    "campi_rifiutati": forbidden,
                },
            )
            if "valido_al" in data:
                ErrorManager.require(
                    data["valido_al"] >= today,
                    code=E_PROMO_RETROATTIVA,
                    message="valido_al non puo' essere antecedente a oggi.",
                    context={
                        "valido_al": data["valido_al"].isoformat(),
                        "today": today.isoformat(),
                    },
                )
            return

        # FUTURA: tutto modificabile, ma date solo verso il futuro.
        if "valido_dal" in data:
            ErrorManager.require(
                data["valido_dal"] > today,
                code=E_PROMO_RETROATTIVA,
                message="valido_dal non puo' essere oggi o nel passato.",
                context={
                    "valido_dal": data["valido_dal"].isoformat(),
                    "today": today.isoformat(),
                },
            )
        if "valido_al" in data:
            ErrorManager.require(
                data["valido_al"] >= today,
                code=E_PROMO_RETROATTIVA,
                message="valido_al non puo' essere antecedente a oggi.",
                context={
                    "valido_al": data["valido_al"].isoformat(),
                    "today": today.isoformat(),
                },
            )
