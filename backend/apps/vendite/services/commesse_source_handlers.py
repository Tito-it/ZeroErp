# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Handler sorgente per CommessaPushOrchestrator.
#        Ogni handler sa come leggere la propria sorgente e
#        tradurla in chiamate CommesseRepository.
# ------------------------------------------------------------

"""
Handler registrati:
- BaseSourceHandler  — logica condivisa _process_rows (zero duplicazione)
- HandlerPreventivi  — preventivi accettati → commesse
- HandlerOrdini      — ordini confermati → commesse
- HandlerContratti   — contratti attivi → commesse
- HandlerDdt         — DDT vendita → commesse
- HandlerConsumi     — consumi utility → commesse mensili AUTO (fan-out 1→N)

Architettura:
  Tutte le 5 fn_list_*_da_pushare SQL restituiscono 26 colonne condivise
  normalizzate in PushableRow. _process_rows è l'unico punto di
  orchestrazione: cicla le righe, crea/riusa commesse e upsert attivita.
"""

import dataclasses
import logging
import time
from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from django.db import connection, transaction

from apps.vendite.db.commesse_repository import (
    POLICY_FATTURAZIONE_DA_DOCUMENTO,
    TIPO_COMMESSA_AUTO,
    CommessaAttivitaInput,
    CommesseRepository,
    PushableRow,
)
from apps.vendite.services.pricing_service import PricingService

logger = logging.getLogger(__name__)


# Cache modulo-level per is_composito (vita = processo Django, scope cross-istanza
# di BoMComponentExpander). Rationale: is_composito di un articolo cambia
# raramente; un batch grosso di handler.run() su preventivi ricorrenti riusa
# il valore senza ri-query DB. La cache per-istanza resta come L1.
# TTL: 5 minuti. Se cambia is_composito di un articolo (raro: refactor catalogo),
# il valore stale dura al massimo 5 min. Override modificabile per test.
_IS_COMPOSITO_MODULE_CACHE: dict[Any, tuple[bool, float]] = {}
_IS_COMPOSITO_MODULE_CACHE_TTL_SECONDS = 300


# Scopo: invalida la cache modulo-level. Da chiamare nei test e in scenari
#        ammnistrativi (es. switch tenant, reload massivo catalogo).
def invalidate_is_composito_module_cache() -> None:
    _IS_COMPOSITO_MODULE_CACHE.clear()


@dataclass
class HandlerResult:
    """Risultato di un singolo handler all'interno di un run orchestratore."""

    handler_name: str
    sorgente_codice: str = ""
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        """Serializza per commesse_push_log.risultato (JSONB)."""
        return {
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": self.errors,
        }


class BoMComponentExpander:
    """Espande PushableRow di articoli compositi v5 in N righe componente.

    Scopo: single-point per la logica F2-BE-12 (sviluppo-listini-v5 §14.4).
    Una riga padre composito viene espansa in N righe (una per componente
    obbligatorio attivo) quando il resolver DB ritorna piu' di una riga
    (CASO A: almeno un componente esposto in fattura). Pass-through nei
    casi B (1 riga) o quando non si applica la logica (articolo non
    composito, parametri insufficienti).

    Decisioni di design (sviluppo-listini-v5 §14.4.1):
    - DEC-2: segment_key suffix '#CMP:{componente_id}'
    - DEC-3: quantita = quantita_padre x coeff_qta, no rounding
    - DEC-5: tipo_doc_fiscale_id ereditato dal padre (gia' nella PushableRow)
    - DEC-6: tutti i componenti tracciati (esposti+non), filtro fattura a valle

    Cache locale (vita = istanza, tipicamente vita = ciclo _process_rows):
    - composite_cache: evita lookup ripetuti is_composito per stesso articolo
    - resolve_cache: evita ri-chiamata resolver per parametri identici

    Contratto resolver DB (post DB-3, 22-04-2026): il dict ritornato include
    `coeff_qta` (Decimal). Per CASO A vale il `coeff_qta` letto da
    `articoli_componenti`; per CASO B (1 riga padre) vale `1` (padre
    neutro nel calcolo `quantita_padre * coeff_qta`).
    """

    def __init__(
        self,
        pricing_service: PricingService | None = None,
        is_composito_fn: Callable[[Any], bool] | None = None,
    ) -> None:
        # Lazy default: PricingService istanziato solo se serve davvero.
        # Permette di iniettare un mock nei test senza setup DB.
        self._pricing_service = pricing_service
        self._is_composito_fn = is_composito_fn or self._default_is_composito
        self._composite_cache: dict[Any, bool] = {}
        self._resolve_cache: dict[tuple, list[dict[str, Any]]] = {}

    # Scopo: applica la logica BoM v5 a una riga sorgente, restituendo
    #        1 o N PushableRow secondo l'esito del resolver composito.
    def expand(self, row: PushableRow) -> list[PushableRow]:
        # Pre-filtri: condizioni in cui la BoM non si applica o non e'
        # risolvibile. Pass-through silenzioso, no errore.
        if row.articolo_id is None:
            return [row]
        if row.uom_id is None or row.competenza_mese is None:
            return [row]
        if row.utility_id is None:
            return [row]
        # O2: padre con quantita None o zero non genera componenti utili
        # (tutti N componenti avrebbero quantita = 0 * coeff_qta = 0).
        # Pass-through coerente con la semantica "consumo zero = niente da fare".
        if row.quantita is None or row.quantita == 0:
            return [row]

        if not self._is_composito_cached(row.articolo_id):
            return [row]

        righe = self._resolve_cached(row)

        # CASO B (resolver ritorna 1 riga padre): pass-through. Il prezzo
        # del composito e' gia' quello della riga, niente fan-out.
        # Riconosciamo CASO B confrontando componente_id == articolo_id padre.
        if len(righe) == 1 and str(righe[0]["componente_id"]) == str(row.articolo_id):
            return [row]

        # CASO A (N righe): genera N PushableRow, una per componente.
        return [self._build_componente_row(row, r) for r in righe]

    # Scopo: cache wrapper per is_composito_fn (1 lookup per articolo per istanza).
    def _is_composito_cached(self, articolo_id: Any) -> bool:
        if articolo_id not in self._composite_cache:
            self._composite_cache[articolo_id] = bool(self._is_composito_fn(articolo_id))
        return self._composite_cache[articolo_id]

    # Scopo: cache wrapper per resolver composito sui parametri-chiave
    #        (articolo, BA, utility, data, emittente). Stessa coppia BoM/scenario
    #        commerciale -> stesso risultato, evita N round-trip nel _process_rows.
    def _resolve_cached(self, row: PushableRow) -> list[dict[str, Any]]:
        cache_key = (
            str(row.articolo_id),
            row.billing_account_id,
            row.utility_id,
            row.competenza_mese,
            row.emittente_soggetto_ruolo_id,
        )
        if cache_key in self._resolve_cache:
            return self._resolve_cache[cache_key]

        if self._pricing_service is None:
            self._pricing_service = PricingService()

        righe = self._pricing_service.resolve_prezzo_composito(
            prodotto_id=row.articolo_id,
            uom_id=row.uom_id,
            data_riferimento=row.competenza_mese,
            ba_id=row.billing_account_id,
            utility_id=row.utility_id,
            emittente_soggetto_ruolo_id=row.emittente_soggetto_ruolo_id,
        )
        self._resolve_cache[cache_key] = righe
        return righe

    # Scopo: costruisce una PushableRow per un singolo componente, ereditando
    #        dal padre tutti i campi di contesto (sorgente, BA, utility,
    #        competenza, tipo_doc_fiscale, valuta) e sostituendo solo i campi
    #        specifici del componente (articolo, uom, prezzo, quantita,
    #        segment_key, meta).
    @staticmethod
    def _build_componente_row(
        row: PushableRow,
        resolver_riga: dict[str, Any],
    ) -> PushableRow:
        componente_id = resolver_riga["componente_id"]
        componente_uom_id = resolver_riga["uom_id"]
        componente_prezzo = resolver_riga["prezzo_unitario"]
        # coeff_qta dal resolver (DB-3 — vedi docstring classe).
        coeff_qta = Decimal(resolver_riga["coeff_qta"])
        componente_esposto = bool(resolver_riga.get("esposto_in_fattura", False))

        # DEC-3: quantita = padre x coeff_qta, senza rounding (sotto-componenti
        # piene, l'arrotondamento avviene a fatturazione su qta x prezzo).
        quantita_padre = row.quantita if row.quantita is not None else Decimal(0)
        quantita_componente = quantita_padre * coeff_qta

        # Meta: preservo tutto del padre, aggiungo audit specifici componente.
        # 'componente_di' permette tracing inverso in commesse_attivita.
        nuovo_meta = dict(row.meta or {})
        nuovo_meta["esposto_in_fattura"] = componente_esposto
        nuovo_meta["componente_di"] = str(row.articolo_id)
        nuovo_meta["coeff_qta"] = str(coeff_qta)

        # DEC-2: segment_key suffix '#CMP:{componente_id}' — deterministico,
        # idempotente per re-run, leggibile in audit.
        new_segment_key = f"{row.segment_key}#CMP:{componente_id}"

        return dataclasses.replace(
            row,
            articolo_id=componente_id,
            uom_id=componente_uom_id,
            quantita=quantita_componente,
            prezzo_snapshot=componente_prezzo,
            segment_key=new_segment_key,
            meta=nuovo_meta,
        )

    # Scopo: query lean per is_composito (vs CatalogoRepository.get_articolo
    #        che proietta la vista arricchita). Una sola colonna, indicizzata.
    #        Usa cache modulo-level con TTL per evitare query ripetute cross-run
    #        su articoli ricorrenti. La cache per-istanza (L1) resta in
    #        _is_composito_cached, questa e' L2 cross-istanza.
    @staticmethod
    def _default_is_composito(articolo_id: Any) -> bool:
        now = time.monotonic()
        cached = _IS_COMPOSITO_MODULE_CACHE.get(articolo_id)
        if cached is not None:
            value, ts = cached
            if now - ts < _IS_COMPOSITO_MODULE_CACHE_TTL_SECONDS:
                return value
        # Miss o TTL scaduto: query DB.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT is_composito FROM catalogo.articoli WHERE id = %s",
                [articolo_id],
            )
            row = cursor.fetchone()
            value = bool(row[0]) if row else False
        _IS_COMPOSITO_MODULE_CACHE[articolo_id] = (value, now)
        return value


class BaseSourceHandler(ABC):
    """Logica condivisa per tutti gli handler sorgente.

    Ogni handler concreto dichiara:
    - ``name``            — stringa identificativa (es. "HandlerPreventivi")
    - ``sorgente_codice`` — codice config.sorgenti (es. "PREVENTIVO")

    e implementa ``run()`` delegando a ``_process_rows()``.

    L'espansione BoM v5 (F2-BE-12) e' applicata di default tramite
    ``BoMComponentExpander``: handler concreti che vogliano un fan-out
    diverso (es. ``HandlerConsumi`` per consumi utility) possono
    sovrascrivere ``_expand_rows`` direttamente — il loro override
    sostituisce completamente la BoM.
    """

    name: str
    sorgente_codice: str

    def __init__(
        self,
        repo: CommesseRepository,
        bom_expander: BoMComponentExpander | None = None,
    ) -> None:
        self._repo = repo
        # Lazy default: l'expander e' creato a richiesta. Iniettabile nei
        # test per isolare la logica del handler dal resolver pricing.
        self._bom_expander = bom_expander or BoMComponentExpander()

    # Scopo: esegue la sincronizzazione della sorgente verso commesse_attivita.
    # `sorgente_uid` (opzionale) restringe l'esecuzione alla riga sorgente del
    # documento specifico (push singolo UI-driven); None = batch handler standard.
    def run(self, *, dry_run: bool = False, sorgente_uid: int | None = None) -> HandlerResult:
        return self._process_rows(dry_run=dry_run, sorgente_uid=sorgente_uid)

    # --- Logica condivisa ---

    def _process_rows(
        self,
        *,
        dry_run: bool = False,
        competenza_mese=None,
        billing_account_id=None,
        limit=None,
        sorgente_uid: int | None = None,
    ) -> HandlerResult:
        """Ciclo principale: fetch → get_or_create_commessa → link → upsert.

        Usa cache locale per evitare chiamate DB ridondanti a get_or_create_commessa
        quando piu` righe appartengono alla stessa commessa (stessi parametri chiave).
        """
        result = HandlerResult(handler_name=self.name, sorgente_codice=self.sorgente_codice)
        rows = self._repo.fetch_pushable_rows(
            self.sorgente_codice,
            competenza_mese=competenza_mese,
            billing_account_id=billing_account_id,
            limit=limit,
            sorgente_uid=sorgente_uid,
        )

        # Cache locale: evita round-trip DB ripetuti per la stessa commessa.
        commessa_cache: dict[tuple, int] = {}
        pending_inputs: list[CommessaAttivitaInput] = []

        for row in rows:
            try:
                # Savepoint: se fallisce la riga, rollback di get_or_create + link
                # senza corrompere lo stato delle righe precedenti.
                with transaction.atomic():
                    expanded = self._expand_rows(row)
                    tipo_commessa = self._extract_tipo_commessa(row)
                    policy_fatturazione = self._extract_policy_fatturazione(row)

                    cache_key = (
                        row.billing_account_id,
                        row.utility_id,
                        tipo_commessa,
                        policy_fatturazione,
                        row.fatturazione_immediata,
                        row.emittente_soggetto_ruolo_id,
                        row.competenza_dal,
                        row.competenza_al,
                    )

                    if cache_key in commessa_cache:
                        commessa_id = commessa_cache[cache_key]
                    else:
                        commessa_id = self._repo.get_or_create_commessa(
                            billing_account_id=row.billing_account_id,
                            utility_id=row.utility_id,
                            tipo_commessa=tipo_commessa,
                            policy_fatturazione=policy_fatturazione,
                            fatturazione_immediata=row.fatturazione_immediata,
                            emittente_soggetto_ruolo_id=row.emittente_soggetto_ruolo_id,
                            competenza_dal=row.competenza_dal,
                            competenza_al=row.competenza_al,
                        )
                        commessa_cache[cache_key] = commessa_id

                    self._repo.link_sorgente(
                        commessa_id=commessa_id,
                        sorgente_tipo_id=row.sorgente_tipo_id,
                        sorgente_uid=row.sorgente_uid,
                    )

                    for exp in expanded:
                        pending_inputs.append(self._build_attivita_input(commessa_id, exp))

            except Exception as exc:
                msg = f"Errore riga segment_key={row.segment_key}: {type(exc).__name__}: {exc}"
                logger.exception(msg)
                result.errors.append(msg)
                result.skipped += 1

        # Batch upsert in una sola chiamata DB (N round-trip → 1).
        if pending_inputs and not dry_run:
            batch = self._repo.batch_upsert_attivita(pending_inputs)
            result.created = batch.inserted
            result.updated = batch.updated
            result.skipped += len(batch.errors)
            for err in batch.errors:
                result.errors.append(
                    f"Errore batch segment_key={err.get('segment_key')}: {err.get('error')}"
                )
        elif pending_inputs:
            result.created = len(pending_inputs)

        return result

    def _expand_rows(self, row: PushableRow) -> list[PushableRow]:
        """Hook per fan-out 1→N. Default: applica BoM v5 via BoMComponentExpander.

        Articoli compositi con almeno un componente esposto in fattura
        diventano N righe (una per componente obbligatorio attivo).
        Articoli semplici e CASO B del resolver (1 riga padre) sono
        pass-through. Override completo possibile per pattern non-BoM
        (es. HandlerConsumi fan-out su componenti utility).
        """
        return self._bom_expander.expand(row)

    @staticmethod
    def _extract_tipo_commessa(row: PushableRow) -> str:
        """#6: tipo_commessa da meta, default TIPO_COMMESSA_AUTO."""
        if isinstance(row.meta, dict):
            return row.meta.get("tipo_commessa", TIPO_COMMESSA_AUTO)
        return TIPO_COMMESSA_AUTO

    @staticmethod
    def _extract_policy_fatturazione(row: PushableRow) -> str:
        """#6: policy_fatturazione da meta, default POLICY_FATTURAZIONE_DA_DOCUMENTO."""
        if isinstance(row.meta, dict):
            return row.meta.get("policy_fatturazione", POLICY_FATTURAZIONE_DA_DOCUMENTO)
        return POLICY_FATTURAZIONE_DA_DOCUMENTO

    def _build_attivita_input(
        self, commessa_id: int, row: PushableRow
    ) -> CommessaAttivitaInput:
        """Costruisce CommessaAttivitaInput da PushableRow con default corretti."""
        return CommessaAttivitaInput(
            commessa_id=commessa_id,
            segment_key=row.segment_key,
            quantita=row.quantita if row.quantita is not None else Decimal(0),
            competenza_mese=row.competenza_mese,
            articolo_id=row.articolo_id,
            prezzo_snapshot=row.prezzo_snapshot,
            uom_id=row.uom_id,
            tipo_doc_fiscale_id=row.tipo_doc_fiscale_id,
            valuta_id=row.valuta_id,
            prezzo_bloccato=row.prezzo_bloccato,
            pricing_mode=row.pricing_mode,
            tipo_movimento=row.tipo_movimento,
            tipo_consumo=row.tipo_consumo,
            istanza_utility_id=row.istanza_utility_id,
            data_attivita=row.data_attivita,
            competenza_dal=row.competenza_dal,
            competenza_al=row.competenza_al,
            qta_operativa=row.qta_operativa,
            uom_operativa_id=row.uom_operativa_id,
            factor_to_base=row.factor_to_base,
            sorgente_tipo_id=row.sorgente_tipo_id,
            sorgente_uid=row.sorgente_uid,
            meta=row.meta,
        )


# --- Handler concreti ---


class HandlerPreventivi(BaseSourceHandler):
    """Sincronizza preventivi accettati → commesse."""

    name = "HandlerPreventivi"
    sorgente_codice = "PREVENTIVO"


class HandlerOrdini(BaseSourceHandler):
    """Sincronizza ordini confermati → commesse (#1: ORDINE_VENDITA)."""

    name = "HandlerOrdini"
    sorgente_codice = "ORDINE_VENDITA"


class HandlerContratti(BaseSourceHandler):
    """Sincronizza contratti attivi → commesse (#8 nuovo)."""

    name = "HandlerContratti"
    sorgente_codice = "CONTRATTO"


class HandlerDdt(BaseSourceHandler):
    """Sincronizza DDT vendita → commesse (#8 nuovo)."""

    name = "HandlerDdt"
    sorgente_codice = "DDT_VENDITA"


@dataclass(frozen=True)
class ComponenteConsumabile:
    """Struttura per espansione componenti consumo (fan-out 1→N)."""

    codice: str
    articolo_id: Any
    quantita: Any
    prezzo: Any
    uom_id: int | None


class HandlerConsumi(BaseSourceHandler):
    """Sincronizza consumi utility → commesse mensili AUTO (#9: fan-out 1→N).

    Ogni riga consumo base viene espansa in N componenti tramite
    _expand_rows(). _fetch_componenti resta stub — richiede fn DB
    per lookup componenti da catalogo/utility.
    """

    name = "HandlerConsumi"
    sorgente_codice = "ATTIVITA_CONSUMI"

    def _expand_rows(self, row: PushableRow) -> list[PushableRow]:
        """Fan-out: espande una riga consumo base in N righe componente."""
        componenti = self._fetch_componenti(row)
        if not componenti:
            return [row]
        return [
            dataclasses.replace(
                row,
                segment_key=f"{row.segment_key}:COMP:{comp.codice}",
                articolo_id=comp.articolo_id,
                quantita=comp.quantita,
                prezzo_snapshot=comp.prezzo,
                uom_id=comp.uom_id,
            )
            for comp in componenti
        ]

    @staticmethod
    def _fetch_componenti(_row: PushableRow) -> list[ComponenteConsumabile]:
        """Stub: fn DB per lookup componenti utility non ancora disponibile."""
        return []
