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

# Chiavi `meta` condivise tra BoMComponentExpander (scrittura) e il wiring
# audit pricing (lettura): centralizzate per evitare drift silente sui literal.
_META_KEY_COMPONENTE_DI = "componente_di"
_META_KEY_ORIGINE_PREZZO = "origine_prezzo"

# Valori ammessi per `commesse_attivita.origine_prezzo` (CHECK
# chk_commesse_attivita_origine_prezzo, speculare ad attivita_fatturabili).
# Il resolver pricing puo' restituire `origine` fuori da questo set (es.
# 'LISTINO_BUNDLE' nello stadio bundle): in quel caso l'audit origine resta
# NULL (NULL passa il CHECK), per non far fallire l'upsert. Allineare a DB se
# il modello aggiunge valori.
_ORIGINE_PREZZO_AMMESSE = frozenset(
    {"PROMO", "CONTRATTO_OVERRIDE", "CONTRATTO_LISTINO", "CATEGORIA", "MANUALE"}
)


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
    # Commesse toccate dal run (create o riusate): alimentano il ponte di
    # emittibilita` post-push in commesse_service e l'esposizione API — i soli
    # contatori non permettevano di risalire alla commessa dal documento sorgente.
    commesse_ids: set[int] = field(default_factory=set)

    def as_dict(self) -> dict[str, Any]:
        """Serializza per commesse_push_log.risultato (JSONB)."""
        return {
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": self.errors,
            "commesse_ids": sorted(self.commesse_ids),
        }


class BoMComponentExpander:
    """Espande PushableRow di articoli compositi in N righe componente.

    Modello unificato componenti BoM 2026-05-13: il padre composito viene
    sempre espanso in N righe (una per ciascun componente attivo della
    riga sorgente). `esposto_in_fattura` ora e' un flag di presentazione
    fattura, non gate di expansion: tutti i figli attivi passano in
    commessa, la separazione fra "padre con totale" e "figli esposti
    come righe descrittive" avviene a valle (generazione fatture_righe).

    Path snapshot (unico, post cleanup legacy 2026-05-14): legge i
    componenti gia' negoziati al documento sorgente via
    `componenti_loader`, che internamente filtra `attivo=TRUE` (solo
    componenti effettivamente inclusi). `esposto_in_fattura` arriva dalla
    proiezione (JOIN runtime su `articoli_componenti`).

    Articolo composito senza loader o con snapshot vuoto: pass-through
    difensivo + `logger.warning` (la riga padre va in commessa non
    espansa). Atteso solo in dev o per handler senza loader iniettato.

    Decisioni di design (sviluppo-listini-v5 §14.4.1):
    - DEC-2: segment_key suffix '#CMP:{componente_id}'
    - DEC-3: quantita = quantita_padre x coeff_qta, no rounding
    - DEC-5: tipo_doc_fiscale_id ereditato dal padre (gia' nella PushableRow)
    - DEC-6: tutti i componenti tracciati (esposti+non), filtro fattura a valle

    Cache locale (vita = istanza, tipicamente vita = ciclo _process_rows):
    - composite_cache: evita lookup ripetuti is_composito per stesso articolo
    """

    def __init__(
        self,
        is_composito_fn: Callable[[Any], bool] | None = None,
        componenti_loader: Callable[[int], list[dict[str, Any]]] | None = None,
    ) -> None:
        self._is_composito_fn = is_composito_fn or self._default_is_composito
        # componenti_loader: snapshot pricing pre-popolato (modello unificato
        # BoM 2026-05-13). Obbligatorio per sorgenti che generano commesse
        # da articoli compositi: senza loader la riga padre composita resta
        # non espansa (pass-through difensivo + warning audit). Il path
        # legacy `fn_resolve_prezzo_composito` e' stato rimosso col cleanup
        # 2026-05-14 (mai realmente esercitato in produzione: preventivi ha
        # snapshot, ordini/ddt non esistono).
        self._componenti_loader = componenti_loader
        self._composite_cache: dict[Any, bool] = {}

    # Scopo: applica la logica BoM a una riga sorgente, restituendo 1 o N
    #        PushableRow. Path unico (modello unificato 2026-05-13): legge
    #        i componenti gia' negoziati al documento via `componenti_loader`
    #        (snapshot pricing pre-popolato lato repository sorgente).
    #        Senza loader o con loader che ritorna lista vuota: pass-through
    #        difensivo con warning audit (la riga padre composita resta non
    #        espansa, ma il push non si blocca).
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

        # Path snapshot (unico, post cleanup legacy 2026-05-14): legge
        # componenti gia' negoziati al documento sorgente (modello unificato:
        # filtrati `attivo=TRUE` dal repository).
        if (
            self._componenti_loader is not None
            and row.riga_sorgente_id is not None
        ):
            snapshot = self._componenti_loader(row.riga_sorgente_id)
            if snapshot:
                return [
                    self._build_componente_row_from_snapshot(row, c) for c in snapshot
                ]

        # Articolo composito senza snapshot loader o con lista vuota.
        # Pass-through difensivo + warning audit: la riga padre va in
        # commessa non espansa. Atteso solo in dev (pre-deploy modello
        # unificato) o per handler senza loader iniettato. Quando una nuova
        # sorgente verra' wirata, fornire un loader analogo a HandlerPreventivi.
        logger.warning(
            "BoMComponentExpander.expand: articolo composito senza snapshot "
            "loader o snapshot vuoto, pass-through padre. "
            "articolo_id=%s riga_sorgente_id=%s",
            row.articolo_id,
            row.riga_sorgente_id,
        )
        return [row]

    # Scopo: cache wrapper per is_composito_fn (1 lookup per articolo per istanza).
    def _is_composito_cached(self, articolo_id: Any) -> bool:
        if articolo_id not in self._composite_cache:
            self._composite_cache[articolo_id] = bool(self._is_composito_fn(articolo_id))
        return self._composite_cache[articolo_id]

    # Scopo: core riusabile per costruire una PushableRow di componente
    #        a partire dal padre. Eredita tutto il contesto (sorgente, BA,
    #        utility, competenza, tipo_doc_fiscale, valuta) e sostituisce
    #        solo i 6 campi specifici del componente (articolo, uom, qta,
    #        prezzo, segment_key, meta). Riusato sia dal path resolver
    #        (`_build_componente_row`) che dal path snapshot
    #        (`_build_componente_row_from_snapshot`): cambiano i nomi dei
    #        field nella sorgente dati (resolver vs preventivi_righe_componenti),
    #        non la logica.
    #        DEC-3: quantita_componente = quantita_padre × coeff_qta (no
    #        rounding — arrotondamento avviene a fatturazione).
    #        DEC-2: segment_key suffix '#CMP:{componente_id}' deterministico
    #        e idempotente per re-run.
    @staticmethod
    def _build_componente_pushable_row(
        row: PushableRow,
        *,
        componente_id: Any,
        componente_uom_id: int | None,
        componente_prezzo: Any,
        coeff_qta: Decimal,
        esposto_in_fattura: bool,
        origine_prezzo: str | None = None,
    ) -> PushableRow:
        quantita_padre = row.quantita if row.quantita is not None else Decimal(0)
        quantita_componente = quantita_padre * coeff_qta

        # Meta: preservo tutto del padre, aggiungo audit componente.
        # `componente_di` permette tracing inverso in commesse_attivita.
        nuovo_meta = dict(row.meta or {})
        nuovo_meta["esposto_in_fattura"] = esposto_in_fattura
        nuovo_meta[_META_KEY_COMPONENTE_DI] = str(row.articolo_id)
        nuovo_meta["coeff_qta"] = str(coeff_qta)
        if origine_prezzo is not None:
            nuovo_meta[_META_KEY_ORIGINE_PREZZO] = origine_prezzo

        return dataclasses.replace(
            row,
            articolo_id=componente_id,
            uom_id=componente_uom_id,
            quantita=quantita_componente,
            prezzo_snapshot=componente_prezzo,
            segment_key=f"{row.segment_key}#CMP:{componente_id}",
            meta=nuovo_meta,
        )

    # Scopo: adatta il dict componente preventivo al builder generico
    #        (refactor 2026-05-11). Differenze chiave dict vs resolver:
    #          - `uom_operativa_id` invece di `uom_id`
    #          - `coeff_qta_snapshot` invece di `coeff_qta`
    #          - `origine_prezzo` propagato in meta per audit downstream.
    #        Modello unificato 2026-05-13: `esposto_in_fattura` arriva
    #        dalla proiezione del repository (JOIN runtime su
    #        `articoli_componenti`, BoM immutabile per design). Init popola
    #        TUTTI i figli (no piu' filtro su esposto). Il `list_componenti_riga`
    #        col default `solo_attivi=True` filtra solo i componenti
    #        effettivamente inclusi nel documento (opzionali disattivati
    #        esclusi dal push verso commessa).
    @classmethod
    def _build_componente_row_from_snapshot(
        cls,
        row: PushableRow,
        componente: dict[str, Any],
    ) -> PushableRow:
        return cls._build_componente_pushable_row(
            row,
            componente_id=componente["componente_id"],
            componente_uom_id=componente.get("uom_operativa_id") or row.uom_id,
            componente_prezzo=componente["prezzo_unitario"],
            coeff_qta=Decimal(str(componente["coeff_qta_snapshot"])),
            esposto_in_fattura=bool(componente.get("esposto_in_fattura", False)),
            origine_prezzo=componente.get("origine_prezzo"),
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
    # Sottoclassi con articoli compositi dichiarano qui una @staticmethod che
    # ritorna un repo con `list_componenti_riga` (ComponentiRepositoryMixin):
    # il default BoMComponentExpander legge da li' i componenti negoziati della
    # riga sorgente e fa fan-out 1→N. None = nessun fan-out da snapshot (handler
    # senza compositi o con override completo di `_expand_rows`, es. consumi).
    # È una staticmethod (non import top-level) perche' i *_repository importano
    # i types del dominio vendite → import locale evita cicli.
    _componenti_repo_factory = None

    def __init__(
        self,
        repo: CommesseRepository,
        bom_expander: BoMComponentExpander | None = None,
        pricing_service: PricingService | None = None,
    ) -> None:
        self._repo = repo
        # Lazy default: l'expander e' creato a richiesta. Iniettabile nei
        # test per isolare la logica del handler dal resolver pricing.
        # Se la sottoclasse dichiara una repo componenti, il default legge i
        # componenti snapshot della riga sorgente (modello unico preventivi/
        # ordini/contratti/DDT); altrimenti expander "nudo" (pass-through).
        if bom_expander is None and self._componenti_repo_factory is not None:
            repo_componenti = self._componenti_repo_factory()
            bom_expander = BoMComponentExpander(
                componenti_loader=repo_componenti.list_componenti_riga,
            )
        self._bom_expander = bom_expander or BoMComponentExpander()
        # PricingService per popolare l'audit snapshot v5 al push (F2-BE-12).
        # Lazy + iniettabile nei test (MagicMock) per non toccare il DB.
        self._pricing_service = pricing_service
        # Cache per-istanza (vita = ciclo _process_rows): dedup risoluzioni
        # audit identiche dentro lo stesso push (stesso articolo/uom/contesto).
        self._pricing_audit_cache: dict[tuple, dict[str, Any]] = {}

    # Scopo: lazy-init del PricingService (creato solo al primo uso reale,
    #        evita dipendenza DB nei test che non esercitano l'audit pricing).
    @property
    def _pricing(self) -> PricingService:
        if self._pricing_service is None:
            self._pricing_service = PricingService()
        return self._pricing_service

    # Scopo: esegue la sincronizzazione della sorgente verso commesse_attivita.
    # `sorgente_uid` (opzionale) restringe l'esecuzione alla riga sorgente del
    # documento specifico (push singolo UI-driven); None = batch handler standard.
    # `righe_ids` (opzionale, richiede sorgente_uid) restringe ulteriormente al
    # sottoinsieme di righe scelto dall'operatore (smistamento selettivo dal
    # Pannello Smistamento — brief-db-smistamento-preventivi.md C).
    def run(
        self,
        *,
        dry_run: bool = False,
        sorgente_uid: int | None = None,
        righe_ids: list[int] | None = None,
    ) -> HandlerResult:
        return self._process_rows(
            dry_run=dry_run, sorgente_uid=sorgente_uid, righe_ids=righe_ids,
        )

    # --- Logica condivisa ---

    def _process_rows(
        self,
        *,
        dry_run: bool = False,
        competenza_mese=None,
        billing_account_id=None,
        limit=None,
        sorgente_uid: int | None = None,
        righe_ids: list[int] | None = None,
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
            righe_ids=righe_ids,
        )

        # Cache locale: evita round-trip DB ripetuti per la stessa commessa.
        commessa_cache: dict[tuple, int] = {}
        pending_inputs: list[CommessaAttivitaInput] = []

        for row in rows:
            try:
                # Savepoint: se fallisce la riga, rollback di get_or_create + link
                # senza corrompere lo stato delle righe precedenti.
                with transaction.atomic():
                    # Punto d'innesto (scaffolding §6): una futura FASE DI
                    # LAVORAZIONE precederebbe qui la creazione commessa. Oggi
                    # identity (no-op): non altera comportamento ne' performance.
                    row = self._pre_commessa_hook(row)
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

                # Fuori dal savepoint: la commessa e` tracciata solo se la riga
                # e` atterrata (un rollback non deve produrre id fantasma).
                result.commesse_ids.add(commessa_id)

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

    def _pre_commessa_hook(self, row: PushableRow) -> PushableRow:
        """Punto d'innesto (scaffolding §6) eseguito per riga PRIMA di
        espansione/creazione commessa. Default: identity (ritorna la riga
        invariata), nessuna logica di produzione. È il punto naturale dove una
        futura FASE DI LAVORAZIONE arricchirebbe/deriverebbe la riga (es. settare
        un fase_lavorazione_id in `meta`) senza toccare il ciclo principale.
        Le sottoclassi possono sovrascriverlo; il contratto è puro
        `PushableRow → PushableRow` (no side-effect)."""
        return row

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

    # Scopo: risolve l'audit snapshot pricing v5 (8 campi diagnostici di
    #        derivazione del prezzo) per una riga, via PricingService (F2-BE-12).
    #        IMPORTANTE: NON tocca `prezzo_snapshot` (negoziato alla sorgente,
    #        autoritativo); popola solo i campi di audit, ricostruendo dal
    #        resolver QUALE listino/contratto/promo/categoria abbia determinato
    #        il prezzo alla data di competenza. La ricostruzione puo' divergere
    #        da un prezzo negoziato manualmente: per i componenti BoM si preferisce
    #        l'`origine_prezzo` gia' negoziato (in meta, autoritativo).
    #        Best-effort: senza input sufficienti o su errore resolver ritorna
    #        dict vuoto (audit a None) e il push NON si blocca.
    def _resolve_pricing_audit(self, row: PushableRow) -> dict[str, Any]:
        # Pre-condizioni: senza questi input il resolver non e' chiamabile
        # (CONSUMI senza articolo, righe pre-espansione con uom None, ecc.).
        if (
            row.articolo_id is None
            or row.uom_id is None
            or row.billing_account_id is None
            or row.utility_id is None
            or row.emittente_soggetto_ruolo_id is None
        ):
            return {}
        data_rif = row.data_attivita or row.competenza_mese
        if data_rif is None:
            return {}

        # Contesto BUNDLE per i componenti BoM: il padre e' tracciato in meta.
        padre_contesto = (row.meta or {}).get(_META_KEY_COMPONENTE_DI)
        cache_key = (
            str(row.articolo_id),
            row.uom_id,
            row.billing_account_id,
            row.utility_id,
            row.emittente_soggetto_ruolo_id,
            data_rif,
            padre_contesto,
        )
        if cache_key in self._pricing_audit_cache:
            return self._pricing_audit_cache[cache_key]

        audit: dict[str, Any] = {}
        try:
            # Savepoint isolato: un errore resolver (DatabaseError → ServiceError)
            # non deve abortire la transazione del push ne' scartare la riga.
            with transaction.atomic():
                r = self._pricing.resolve_prezzo(
                    articolo_id=row.articolo_id,
                    uom_id=row.uom_id,
                    data_riferimento=data_rif,
                    ba_id=row.billing_account_id,
                    utility_id=row.utility_id,
                    emittente_soggetto_ruolo_id=row.emittente_soggetto_ruolo_id,
                    articolo_padre_contesto=padre_contesto,
                )
            audit = {
                "prezzo_base_snapshot": r.get("prezzo_base_snapshot"),
                "origine_prezzo": r.get("origine"),
                "tipo_variazione_applicata": r.get("tipo_variazione_applicata"),
                "valore_variazione_applicata": r.get("valore_variazione_applicata"),
                "promo_id": r.get("promo_id"),
                "contratto_id": r.get("contratto_id"),
                "categoria_cliente_id_snapshot": r.get("categoria_cliente_id_snapshot"),
                "classe_utenza_id_snapshot": r.get("classe_utenza_id_snapshot"),
            }
        except Exception as exc:  # best-effort: audit e' diagnostico, non bloccante
            logger.warning(
                "Audit pricing snapshot non risolto (push prosegue) "
                "articolo_id=%s uom_id=%s: %s: %s",
                row.articolo_id, row.uom_id, type(exc).__name__, exc,
            )
            audit = {}

        self._pricing_audit_cache[cache_key] = audit
        return audit

    def _build_attivita_input(
        self, commessa_id: int, row: PushableRow
    ) -> CommessaAttivitaInput:
        """Costruisce CommessaAttivitaInput da PushableRow con default corretti."""
        audit = self._resolve_pricing_audit(row)
        # Per i componenti BoM l'origine_prezzo negoziato (gia' in meta dal
        # path snapshot) e' autoritativa: prevale sull'origine ricostruita.
        # Whitelist contro il CHECK DB: un valore fuori set (es. resolver
        # 'LISTINO_BUNDLE') diventa NULL invece di far fallire l'upsert.
        origine_candidata = (row.meta or {}).get(_META_KEY_ORIGINE_PREZZO) or audit.get(
            "origine_prezzo"
        )
        origine_prezzo = (
            origine_candidata if origine_candidata in _ORIGINE_PREZZO_AMMESSE else None
        )
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
            # === Snapshot pricing v5 (F2-BE-12) ===
            prezzo_base_snapshot=audit.get("prezzo_base_snapshot"),
            origine_prezzo=origine_prezzo,
            tipo_variazione_applicata=audit.get("tipo_variazione_applicata"),
            valore_variazione_applicata=audit.get("valore_variazione_applicata"),
            promo_id=audit.get("promo_id"),
            contratto_id=audit.get("contratto_id"),
            categoria_cliente_id_snapshot=audit.get("categoria_cliente_id_snapshot"),
            classe_utenza_id_snapshot=audit.get("classe_utenza_id_snapshot"),
        )


# --- Handler concreti ---


class HandlerPreventivi(BaseSourceHandler):
    """Sincronizza preventivi accettati → commesse.

    Compositi: il default BoMComponentExpander legge i componenti negoziati
    pre-popolati su `vendite.preventivi_righe_componenti` (refactor 2026-05-11)
    via `_componenti_repo_factory`, leggendo i prezzi snapshot del preventivo
    invece di chiamare il resolver. Riga senza componenti (CASO B / semplice):
    pass-through (la riga padre va in commessa non espansa).
    """

    name = "HandlerPreventivi"
    sorgente_codice = "PREVENTIVO"

    @staticmethod
    def _componenti_repo_factory():
        # Import locale per evitare ciclo: preventivi_repository importa i
        # types del dominio vendite.
        from apps.vendite.db.preventivi_repository import PreventiviRepository

        return PreventiviRepository()


class HandlerOrdini(BaseSourceHandler):
    """Sincronizza ordini confermati → commesse (#1: ORDINE_VENDITA).

    Compositi: fan-out dai componenti negoziati `vendite.ordini_righe_componenti`
    (modello unico, simmetrico a preventivi).
    """

    name = "HandlerOrdini"
    sorgente_codice = "ORDINE_VENDITA"

    @staticmethod
    def _componenti_repo_factory():
        from apps.vendite.db.ordini_repository import OrdiniRepository

        return OrdiniRepository()


class HandlerContratti(BaseSourceHandler):
    """Sincronizza contratti attivi → commesse.

    Compositi: fan-out dai componenti negoziati
    `vendite.contratti_righe_componenti` (modello unico).
    """

    name = "HandlerContratti"
    sorgente_codice = "CONTRATTO"

    @staticmethod
    def _componenti_repo_factory():
        from apps.vendite.db.contratti_repository import ContrattiRepository

        return ContrattiRepository()


class HandlerDdt(BaseSourceHandler):
    """Sincronizza DDT vendita → commesse.

    Compositi: fan-out dai componenti negoziati `vendite.ddt_righe_componenti`
    (modello unico).
    """

    name = "HandlerDdt"
    sorgente_codice = "DDT_VENDITA"

    @staticmethod
    def _componenti_repo_factory():
        from apps.vendite.db.ddt_repository import DdtRepository

        return DdtRepository()


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

    DIVERSO dai compositi documento (preventivi/ordini/contratti/DDT): un
    consumo (`vendite.attivita_consumi`) e' un totale piatto SENZA tabella
    `*_righe_componenti` negoziata, quindi NON usa il modello unico BoM.
    La decomposizione tariffaria delle utility (gas/energia/acqua/…:
    energia/trasporto/oneri/quota fissa/accise) e' un modello a parte non
    ancora definito → `_fetch_componenti` resta stub. RIMANDATO, NON si fa ora
    (decisione Tid 2026-06-16): serve un modello/brief DB dedicato, da avviare
    solo quando la fatturazione utility per-voce sara' priorita'.
    Override completo di `_expand_rows` (no fan-out finche' lo stub ritorna []).
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
        """Stub — RIMANDATO, NON si fa ora (decisione Tid 2026-06-16). La
        decomposizione tariffaria dei consumi utility (gas/energia/acqua/…:
        energia/trasporto/oneri/quota fissa/accise) richiede un modello/fn DB
        dedicato, distinto dal BoM articolo. Vedi analisi-commesse §4.3 #3.
        Finche' ritorna [], i consumi entrano in commessa come riga singola
        (nessun fan-out)."""
        return []
