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

from apps.config.sorgenti import (
    SORGENTE_ATTIVITA_CONSUMI,
    SORGENTE_CONTRATTO,
    SORGENTE_DDT_VENDITA,
    SORGENTE_ORDINE_VENDITA,
    SORGENTE_PREVENTIVO,
)
from apps.core.services.fan_out import run_fan_out
from apps.vendite.db.commesse_repository import (
    POLICY_FATTURAZIONE_DA_DOCUMENTO,
    TIPO_COMMESSA_AUTO,
    CommessaAttivitaInput,
    CommesseRepository,
    PushableRow,
)
from apps.vendite.services import _kit_meta as kit_meta
from apps.vendite.services.prezzo_riga_commessa import (
    argomenti_resolver,
    origine_ammessa,
    provenienza_da_resolver,
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
# Il contratto kit (`componente_di`, `esposizione`, suffisso del
# `segment_key`) sta in `_kit_meta`: e' letto anche dalla generazione righe
# fattura, che e' l'altro capo del contratto.
_META_KEY_ORIGINE_PREZZO = "origine_prezzo"
# ⚠️ Le origini ammesse dal CHECK di `commesse_attivita.origine_prezzo` stanno
#    nel building block `prezzo_riga_commessa` (`origine_ammessa`), insieme al
#    resto della provenienza del prezzo: fino al 2026-10-08 erano qui.


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
    # Id delle righe attivita` effettivamente upsertate dal run, per commessa.
    # Alimentano il ponte di approvazione: il push autorizza le PROPRIE righe,
    # non tutte le BOZZA della commessa (brief porta-oneri §4b, trappola T1).
    attivita_ids_per_commessa: dict[int, list[int]] = field(default_factory=dict)

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
    riga sorgente). `esposizione_in_fattura` e' il modo di presentazione
    in fattura (NASCOSTO / DESCRITTIVO / VALORIZZATO), non gate di
    expansion: tutti i figli attivi passano in commessa, e cosa sta nel
    totale del padre e cosa sulla riga del componente lo decide a valle
    `vw_fattura_righe_esposte`.

    Path snapshot (unico, post cleanup legacy 2026-05-14): legge i
    componenti gia' negoziati al documento sorgente via
    `componenti_loader`, che internamente filtra `attivo=TRUE` (solo
    componenti effettivamente inclusi). `esposizione_in_fattura` arriva dalla
    proiezione (JOIN runtime su `articoli_componenti`).

    Il kit che il documento NON negozia (la quota fissa del listino arriva
    senza riga; l'ADESIONE su un kit non ha componenti suoi): li da' il
    listino, dal secondo lettore `componenti_listino_loader` (riceve la
    riga, oggi lo inietta il solo `HandlerContratti`: D-2 (c) di
    brief-db-contratto-righe-periodiche-in-commessa §7.2). Stessa forma
    dello snapshot, prezzo del DB: nessun prezzo calcolato qui.

    Articolo composito senza componenti da nessuno dei due: pass-through
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
        componenti_listino_loader: Callable[[PushableRow], list[dict[str, Any]]] | None = None,
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
        # I componenti del kit dal LISTINO del documento, quando la riga non
        # ne ha di negoziati (D-2 (c)): stessa forma dello snapshot.
        self._componenti_listino_loader = componenti_listino_loader
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

        # Il kit che il documento non negozia: i componenti dal listino, alla
        # data del pezzo (D-2 (c)). La quota fissa arriva senza riga
        # sorgente, l'ADESIONE con la riga ma senza componenti suoi.
        if self._componenti_listino_loader is not None:
            dal_listino = self._componenti_listino_loader(row)
            if dal_listino:
                return [
                    self._build_componente_row_from_snapshot(row, c) for c in dal_listino
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
        componente_uom_id: int,
        componente_prezzo: Any,
        coeff_qta: Decimal,
        esposizione: str,
        origine_prezzo: str | None = None,
    ) -> PushableRow:
        quantita_padre = row.quantita if row.quantita is not None else Decimal(0)
        quantita_componente = quantita_padre * coeff_qta

        # Meta: preservo tutto del padre, aggiungo audit componente.
        # `componente_di` permette tracing inverso in commesse_attivita.
        nuovo_meta = dict(row.meta or {})
        nuovo_meta[kit_meta.META_KEY_ESPOSIZIONE] = esposizione
        nuovo_meta[kit_meta.META_KEY_COMPONENTE_DI] = str(row.articolo_id)
        nuovo_meta[kit_meta.META_KEY_COEFF_QTA] = str(coeff_qta)
        # Quantita' e UoM della riga PADRE: la fattura le congela sulla riga
        # del kit (`kit_qta`, `kit_uom_id`). Ricavarle dai componenti non si
        # puo': con coefficienti diversi o unita' diverse non dicono un numero
        # solo (brief-db-bom-flag-quantita-e-kit-in-fattura §2.2).
        # `expand` arriva qui solo con quantita' e UoM del padre valorizzate.
        nuovo_meta[kit_meta.META_KEY_QTA_PADRE] = str(quantita_padre)
        nuovo_meta[kit_meta.META_KEY_UOM_PADRE] = row.uom_id
        if origine_prezzo is not None:
            nuovo_meta[_META_KEY_ORIGINE_PREZZO] = origine_prezzo

        return dataclasses.replace(
            row,
            articolo_id=componente_id,
            uom_id=componente_uom_id,
            quantita=quantita_componente,
            prezzo_snapshot=componente_prezzo,
            segment_key=kit_meta.segment_key_componente(
                row.segment_key, componente_id
            ),
            meta=nuovo_meta,
        )

    # Scopo: adatta il dict componente preventivo al builder generico
    #        (refactor 2026-05-11). Differenze chiave dict vs resolver:
    #          - `uom_operativa_id` invece di `uom_id`
    #          - `coeff_qta_snapshot` invece di `coeff_qta`
    #          - `origine_prezzo` propagato in meta per audit downstream.
    #        Modello unificato 2026-05-13: `esposizione_in_fattura` arriva
    #        dalla proiezione del repository (JOIN runtime su
    #        `articoli_componenti`, BoM immutabile per design). Init popola
    #        TUTTI i figli (nessun filtro sull'esposizione). Il `list_componenti_riga`
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
            # NOT NULL sulle `*_righe_componenti` dal 2026-10-02: niente
            # ripiego sulla UoM del padre, che su un kit misto trasformerebbe
            # «3 metri» in «3 kit» (brief-db-bom-flag-quantita-e-kit-in-fattura
            # §2.3, R-BE-B4).
            componente_uom_id=componente["uom_operativa_id"],
            componente_prezzo=componente["prezzo_unitario"],
            coeff_qta=Decimal(str(componente["coeff_qta_snapshot"])),
            # LEFT JOIN sulla distinta nella proiezione: un NULL vale il
            # default della colonna, non un errore.
            esposizione=kit_meta.esposizione_o_default(
                componente.get("esposizione_in_fattura")
            ),
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
    _componenti_repo_factory: Callable[[], Any] | None = None
    # Il periodo della riga entra nella chiave della commessa? Si' per le
    # sorgenti a evento (un documento, un periodo). ⛔ No per il contratto
    # (G-6 del brief-db-contratto-righe-periodiche-in-commessa): ogni pezzo di
    # canone ha il suo periodo, e col periodo nella chiave dal secondo pezzo
    # si aprirebbe un'altra commessa, che la madre rifiuta
    # (`E_COMMESSA_SORGENTE_ALTRA_COMMESSA`, D-12). Una commessa viva per
    # contratto accumula i pezzi finche' non si fattura.
    _commessa_per_periodo: bool = True

    # Scopo: il secondo lettore dell'espansore, i componenti di un kit dal
    #        listino del documento quando la riga non ne ha di negoziati
    #        (`BoMComponentExpander.componenti_listino_loader`). Nessuno di
    #        default: lo da' la sorgente che ha kit non negoziati (il contratto).
    @staticmethod
    def _componenti_listino_loader(
        repo_componenti: Any,
    ) -> Callable[[PushableRow], list[dict[str, Any]]] | None:
        del repo_componenti
        return None

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
                componenti_listino_loader=self._componenti_listino_loader(repo_componenti),
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
        """Ciclo principale: fetch → get_or_create_commessa → upsert.

        Il link documento → commessa (`vendite.commesse_sorgenti`) non si
        scrive qui: lo scrive la madre DB delle righe, vedi `_lavora_riga`.

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

        # Scopo: Lavora UNA riga sorgente — hook, espansione BoM, risoluzione o
        #        creazione della commessa — e restituisce
        #        cio' che va registrato SOLO SE la riga e' atterrata: chiave di
        #        cache, id commessa e input attivita' da accodare al batch.
        #        Gira dentro il savepoint aperto dal fan-out, quindi NON tocca
        #        nessuna struttura Python condivisa: le registra `_registra_riga`
        #        a savepoint rilasciato, perche' un rollback annulla le righe di
        #        database ma non un `append`.
        def _lavora_riga(row: PushableRow) -> tuple[tuple, int, list[CommessaAttivitaInput]]:
            # Punto d'innesto (scaffolding §6): una futura FASE DI
            # LAVORAZIONE precederebbe qui la creazione commessa. Oggi
            # identity (no-op): non altera comportamento ne' performance.
            row = self._pre_commessa_hook(row)
            expanded = self._expand_rows(row)
            tipo_commessa = self._extract_tipo_commessa(row)
            policy_fatturazione = self._extract_policy_fatturazione(row)

            # ⚠️ Le condizioni di pagamento SONO dimensioni di questa
            # chiave, non decorazione: D-R le mette nella chiave della
            # commessa. Ometterle qui farebbe collassare in UNA sola
            # commessa due ordini dello stesso cliente con termini
            # DIVERSI — la cache locale restituirebbe l'id della prima
            # e la seconda erediterebbe il termine sbagliato. E'
            # l'errore che si commette fixando solo la propagazione:
            # produce un difetto piu' difficile da vedere di quello
            # che si voleva togliere.
            #
            # ⭐ UN ELENCO SOLO, e la chiave si DERIVA da quello. Fino al
            # 2026-08-26 le dimensioni erano scritte due volte — la
            # `cache_key` e i `kwargs` della chiamata, identici e a cinque
            # righe di distanza — e a tenerle allineate c'era solo la
            # disciplina di chi le toccava. Toglierne una dalla chiave e
            # lasciarla nella chiamata non rompe niente di visibile: fa
            # riusare una commessa che non andava riusata, cioe' il difetto
            # che il commento qui sopra descrive. Con un elenco solo la
            # divergenza non e' improbabile: e' impossibile.
            # ⚠️ I tre che restano fuori NON sono fuori per la stessa
            # ragione, e vale distinguerle. `priorita_operativa` E' una
            # dimensione della chiave anche a database, ma qui non si
            # passa: vale il default, quindi e' costante per tutto il giro
            # — il giorno in cui venisse passata entrerebbe nella chiave da
            # sola, ed e' il comportamento giusto.
            # ⛔ `meta` e `force_new` invece non sono dimensioni affatto:
            # il database non li mette ne' nell'hash del lock ne' nel WHERE
            # del riuso. E `force_new` e' peggio di un di piu': e' il
            # comando che DISABILITA il riuso, quindi in una cache di riuso
            # sarebbe una contraddizione — chi un giorno lo passasse deve
            # saltare questa cache, non aggiungerlo a questo dizionario.
            # ⭐ L'EMITTENTE non c'e' piu', e non perche' abbia smesso di
            # essere una dimensione della commessa: lo e' ancora, ma si
            # DERIVA dal billing account, che nell'elenco c'e' gia'. Due
            # righe con lo stesso `billing_account_id` ricadono per
            # costruzione sullo stesso emittente, quindi non discriminava
            # niente — e dal `20260826-52` la funzione DB non lo accetta
            # nemmeno piu' in ingresso. ⚠️ `row.emittente_soggetto_ruolo_id`
            # resta esposto da `PushableRow`: le `fn_list_*_da_pushare`
            # continuano a calcolarlo e serve altrove. Cambia solo chi lo
            # ri-passa.
            dimensioni_commessa: dict[str, Any] = {
                "billing_account_id": row.billing_account_id,
                "utility_id": row.utility_id,
                "tipo_commessa": tipo_commessa,
                "policy_fatturazione": policy_fatturazione,
                "fatturazione_immediata": row.fatturazione_immediata,
                "competenza_dal": row.competenza_dal if self._commessa_per_periodo else None,
                "competenza_al": row.competenza_al if self._commessa_per_periodo else None,
                "termine_pagamento_id": row.termine_pagamento_id,
                "modalita_pagamento_id": row.modalita_pagamento_id,
            }
            # I `dict` conservano l'ordine di inserimento (Python 3.7+):
            # la chiave e' stabile dentro il giro, che e' quanto serve a
            # una cache che vive il tempo di un push.
            cache_key = tuple(dimensioni_commessa.values())

            if cache_key in commessa_cache:
                commessa_id = commessa_cache[cache_key]
            else:
                commessa_id = self._repo.get_or_create_commessa(**dimensioni_commessa)

            # ⛔ Il LINK della sorgente non si scrive qui. Dal 2026-10-12 lo
            # scrive la madre DB `vendite.fn_upsert_commessa_attivita`, per
            # ogni riga con una sorgente di scope PUSH_COMMESSA, prima di
            # scriverla (D-13 di brief-db-annullo-a-valle-riapre-a-monte): la
            # regola «un documento in una sola commessa APERTA» (D-12) la
            # attraversa ogni invio, non solo quelli che si ricordano di
            # chiamarla. Il rifiuto (`E_COMMESSA_SORGENTE_ALTRA_COMMESSA`)
            # arriva quindi dal batch, come errore della riga.

            return cache_key, commessa_id, [
                self._build_attivita_input(commessa_id, exp) for exp in expanded
            ]

        # Scopo: Registra gli effetti della riga ATTERRATA — cache di lookup,
        #        commesse toccate, input in coda al batch. Il BB lo chiama a
        #        savepoint gia' rilasciato: e' il punto in cui il lavoro della
        #        riga e' definitivo, quindi l'unico in cui e' lecito scrivere
        #        strutture Python, che un rollback non saprebbe annullare.
        #        ⚠️ La cache DEVE stare qui e non dentro il savepoint: una riga
        #        che cadesse dopo averla popolata lascerebbe l'id di una commessa
        #        annullata, e la riga gemella successiva fallirebbe anch'essa —
        #        un errore che si propaga da solo. E deve stare qui e non a fine
        #        giro: serve alla riga SUCCESSIVA, che e' l'unica ragione per cui
        #        la cache esiste.
        #        La regola era gia' scritta per `commesse_ids` («un rollback non
        #        deve produrre id fantasma»); ora vale per tutte e tre.
        def _registra_riga(_row: PushableRow, prodotto: tuple) -> None:
            cache_key, commessa_id, inputs = prodotto
            commessa_cache[cache_key] = commessa_id
            result.commesse_ids.add(commessa_id)
            pending_inputs.extend(inputs)

        # Fan-out isolato: un savepoint per riga, errore catturato, giro che
        # prosegue. Lo stack dell'eccezione lo logga il BB.
        esito = run_fan_out(rows, _lavora_riga, on_success=_registra_riga)

        for errore in esito.errori:
            result.errors.append(
                f"Errore riga segment_key={errore.item.segment_key}: {errore.messaggio}"
            )
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
            # Il batch DB ritorna solo contatori: risolviamo gli id dalle chiavi
            # naturali (commessa_id, segment_key) per dire al ponte QUALI righe
            # sono nostre. Le chiavi FALLITE vanno escluse esplicitamente: per
            # gli INSERT falliti la riga non esiste e la query non la trova, ma
            # per gli UPDATE falliti la riga preesistente (del push precedente)
            # esiste ancora — senza il filtro il ponte la approverebbe coi
            # VALORI STALI mentre il report la segna in errore (review
            # 2026-07-23: BOZZA→APPROVATA→fatturata col vecchio importo).
            chiavi_fallite = {
                err.get("segment_key") for err in batch.errors
            }
            result.attivita_ids_per_commessa = self._repo.list_attivita_ids_by_segments(
                [
                    (inp.commessa_id, inp.segment_key)
                    for inp in pending_inputs
                    if inp.segment_key not in chiavi_fallite
                ]
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

        Articoli compositi diventano N righe (una per componente attivo,
        qualunque sia il suo modo di esposizione in fattura).
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

    # Scopo: risolve la PROVENIENZA del prezzo di una riga (i
    #        `CAMPI_PROVENIENZA` del building block `prezzo_riga_commessa`:
    #        gli 8 campi diagnostici di derivazione e la versione di listino)
    #        via PricingService (F2-BE-12).
    #        IMPORTANTE: NON tocca `prezzo_snapshot` (negoziato alla sorgente,
    #        autoritativo); popola solo la provenienza, ricostruendo dal
    #        resolver QUALE listino/contratto/promo/categoria abbia determinato
    #        il prezzo alla data di competenza. La ricostruzione puo' divergere
    #        da un prezzo negoziato manualmente: per i componenti BoM si preferisce
    #        l'`origine_prezzo` gia' negoziato (in meta, autoritativo).
    #        ⭐ Cosa chiedere al resolver e cosa scrivere della risposta lo
    #        decide il building block, lo stesso di riallinea e sblocca
    #        (regola del 2, 2026-10-08): contesto del kit, ripiego della data su
    #        `competenza_mese` e versione di listino non possono piu' divergere.
    #        Best-effort: senza input sufficienti o su errore resolver ritorna
    #        dict vuoto (audit a None) e il push NON si blocca.
    def _resolve_pricing_audit(self, row: PushableRow) -> dict[str, Any]:
        # Pre-condizioni: senza questi input il resolver non e' chiamabile
        # (CONSUMI senza articolo, righe pre-espansione con uom None, ecc.).
        argomenti = argomenti_resolver(
            articolo_id=row.articolo_id,
            uom_id=row.uom_id,
            data_attivita=row.data_attivita,
            competenza_mese=row.competenza_mese,
            billing_account_id=row.billing_account_id,
            utility_id=row.utility_id,
            emittente_soggetto_ruolo_id=row.emittente_soggetto_ruolo_id,
            meta=row.meta,
        )
        if argomenti is None:
            return {}

        cache_key = tuple(
            str(v) if k == "articolo_id" else v for k, v in argomenti.items()
        )
        if cache_key in self._pricing_audit_cache:
            return self._pricing_audit_cache[cache_key]

        audit: dict[str, Any] = {}
        try:
            # Savepoint isolato: un errore resolver (DatabaseError → ServiceError)
            # non deve abortire la transazione del push ne' scartare la riga.
            with transaction.atomic():
                r = self._pricing.resolve_prezzo(**argomenti)
            audit = provenienza_da_resolver(r)
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
        origine_prezzo = origine_ammessa(
            (row.meta or {}).get(_META_KEY_ORIGINE_PREZZO) or audit.get("origine_prezzo")
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
            # ⭐ La versione di listino da cui verrebbe il prezzo (2026-10-08):
            #    senza, il guard «versione cambiata» di `fn_riallinea_prezzo`
            #    confrontava con NULL e non scattava mai sulle righe del push.
            listino_versione_id=audit.get("listino_versione_id"),
            # ⛔ `listino_riga_id` NON si prende dal resolver (decisione B di
            #    Tid, 2026-10-09): la riga di listino si cita solo se il prezzo
            #    e' venuto DAVVERO da li', e il push oggi non lo sa — il prezzo
            #    e' quello del documento. Citarla la renderebbe «propagata»
            #    (immutabile) senza che nessuno ne porti il prezzo. Resta NULL
            #    finche' la provenienza non viaggia col prezzo dal documento
            #    (brief-db-provenienza-prezzo-segue-il-prezzo).
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
    sorgente_codice = SORGENTE_PREVENTIVO

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
    sorgente_codice = SORGENTE_ORDINE_VENDITA

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
    sorgente_codice = SORGENTE_CONTRATTO
    # G-6: la commessa del contratto si apre senza periodo (vedi la base).
    _commessa_per_periodo = False

    @staticmethod
    def _componenti_repo_factory():
        from apps.vendite.db.contratti_repository import ContrattiRepository

        return ContrattiRepository()

    # Scopo: il kit che il contratto non negozia (quota fissa del listino,
    #        ADESIONE) prende i componenti dal listino del contratto, alla
    #        data del pezzo (`data_attivita`, la stessa a cui il lister prezza
    #        il kit; D-2 (c)). Il contratto e' la sorgente della riga
    #        (`sorgente_uid` = `contratti.uid`).
    #        ⭐ Una lettura per (contratto, kit, data) nel giro: lo stesso pezzo
    #        si rilegge per ogni riga che lo porta. L'handler nasce a ogni giro
    #        di push (`commesse_service._build_handlers`), quindi la memoria
    #        vive quanto il giro e non vede un listino vecchio. I componenti
    #        sono in sola lettura per l'espansore: condividerli e' sicuro.
    @staticmethod
    def _componenti_listino_loader(
        repo_componenti: Any,
    ) -> Callable[[PushableRow], list[dict[str, Any]]] | None:
        letti: dict[tuple[Any, Any, Any], list[dict[str, Any]]] = {}

        def _loader(row: PushableRow) -> list[dict[str, Any]]:
            data = row.data_attivita or row.competenza_dal
            if data is None:
                return []
            chiave = (row.sorgente_uid, row.articolo_id, data)
            if chiave not in letti:
                letti[chiave] = repo_componenti.list_componenti_kit_dal_listino(
                    contratto_uid=row.sorgente_uid,
                    articolo_padre_id=row.articolo_id,
                    data=data,
                )
            return letti[chiave]

        return _loader


class HandlerDdt(BaseSourceHandler):
    """Sincronizza DDT vendita → commesse.

    Compositi: fan-out dai componenti negoziati `vendite.ddt_righe_componenti`
    (modello unico).
    """

    name = "HandlerDdt"
    sorgente_codice = SORGENTE_DDT_VENDITA

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
    sorgente_codice = SORGENTE_ATTIVITA_CONSUMI

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
