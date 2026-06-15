# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB per dominio commesse (CRUD + pull AF + push sorgenti).
# ------------------------------------------------------------

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json
from typing import Any

from django.db import connection

from apps.core.services.error_manager import ErrorManager
from apps.vendite.types import CommessaEmitResult, CommessaPushLogRow, CommessaStatoResult

# Repository SQL: incapsula accesso DB per commesse, commesse_attivita e push log.


# --- Mapping codice sorgente → fn SQL da chiamare ---
_SORGENTE_FN_MAP: dict[str, str] = {
    "PREVENTIVO": "vendite.fn_list_preventivi_da_pushare",
    "ORDINE_VENDITA": "vendite.fn_list_ordini_da_pushare",
    "ATTIVITA_CONSUMI": "vendite.fn_list_consumi_da_pushare",
    "CONTRATTO": "vendite.fn_list_contratti_da_pushare",
    "DDT_VENDITA": "vendite.fn_list_ddt_da_pushare",
}

# Sorgenti la cui fn_list_*_da_pushare espone il 5o parametro `p_righe_ids`
# (smistamento selettivo per sottoinsieme righe). Oggi solo PREVENTIVO
# (brief-db-smistamento-preventivi.md C); aggiungere qui quando le altre fn
# acquisiranno il parametro (sviluppo concentrico: la whitelist e' il punto
# unico di espansione).
_SORGENTE_SUPPORTA_RIGHE_IDS: frozenset[str] = frozenset({"PREVENTIVO"})

# Nomi delle 26 colonne condivise da tutte le fn_list_*_da_pushare.
# La colonna opzionale `riga_id` (presente in preventivi/ordini/contratti/ddt,
# assente in consumi) e' aggiunta al col_map a runtime dentro
# `fetch_pushable_rows` e mappata su `PushableRow.riga_sorgente_id`
# (refactor componenti 2026-05-11).
_PUSHABLE_SHARED_COLS = (
    "billing_account_id",
    "utility_id",
    "emittente_soggetto_ruolo_id",
    "competenza_dal",
    "competenza_al",
    "fatturazione_immediata",
    "sorgente_tipo_id",
    "sorgente_uid",
    "segment_key",
    "articolo_id",
    "istanza_utility_id",
    "data_attivita",
    "uom_id",
    "quantita",
    "qta_operativa",
    "uom_operativa_id",
    "factor_to_base",
    "competenza_mese",
    "prezzo_snapshot",
    "prezzo_bloccato",
    "pricing_mode",
    "tipo_movimento",
    "tipo_consumo",
    "valuta_id",
    "meta",
    "tipo_doc_fiscale_id",
)


# --- Risultati upsert ---


@dataclass(frozen=True)
class UpsertAttivitaResult:
    """Risultato singolo di fn_upsert_commessa_attivita (attivita_id, is_new)."""

    attivita_id: int
    is_new: bool


@dataclass(frozen=True)
class BatchUpsertResult:
    """Risultato batch di fn_batch_upsert_commessa_attivita."""

    total_rows: int
    inserted: int
    updated: int
    errors: list[dict]


# --- Costanti dominio commesse (valori allineati ai DEFAULT delle fn SQL) ---
TIPO_COMMESSA_AUTO = "AUTO"
POLICY_FATTURAZIONE_DA_DOCUMENTO = "DA_DOCUMENTO"
PRIORITA_OPERATIVA_NORMALE = "NORMALE"
PRICING_MODE_FIXED = "FIXED"
STATO_APPROVAZIONE_BOZZA = "BOZZA"
STATO_EMISSIONE_NON_EMESSA = "NON_EMESSA"
TIPO_MOVIMENTO_NORMALE = "NORMALE"
TIPO_CONSUMO_CONGUAGLIO = "CONGUAGLIO"


@dataclass(frozen=True)
class CommessaAttivitaInput:
    """Input per fn_upsert_commessa_attivita — tutti i campi della riga operativa.

    Campi obbligatori (senza default) prima; opzionali (con default) dopo.
    I default sono allineati ai DEFAULT della fn_upsert_commessa_attivita.
    """

    # === Campi obbligatori (sempre presenti dalle fn_list) ===
    commessa_id: int
    segment_key: str
    quantita: Decimal
    competenza_mese: date
    articolo_id: Any | None  # UUID dal DB; None per consumi (handler risolve)
    prezzo_snapshot: Decimal | None  # None per consumi (calcolato da listino)

    # === Campi con default — allineati a fn_upsert_commessa_attivita ===
    uom_id: int | None = None  # #3: nullable (handler risolve da catalogo)
    tipo_doc_fiscale_id: int | None = None  # #4: default da config
    valuta_id: int | None = None  # None per consumi/contratti
    prezzo_bloccato: bool = False
    pricing_mode: str = PRICING_MODE_FIXED
    prezzo_da_riallineare: bool = False  # #5: default False
    stato_approvazione: str = STATO_APPROVAZIONE_BOZZA
    stato_emissione: str = STATO_EMISSIONE_NON_EMESSA
    tipo_movimento: str = TIPO_MOVIMENTO_NORMALE
    tipo_consumo: str = TIPO_CONSUMO_CONGUAGLIO

    # === Campi opzionali ===
    istanza_utility_id: int | None = None
    data_attivita: date | None = None
    competenza_dal: date | None = None
    competenza_al: date | None = None
    qta_operativa: Decimal | None = None
    uom_operativa_id: int | None = None
    factor_to_base: Decimal | None = None
    posticipa_al: date | None = None
    area_geografica_id: int | None = None
    listino_versione_id: int | None = None
    sorgente_tipo_id: int | None = None
    sorgente_uid: str | None = None
    meta: dict[str, Any] | None = None

    # === Snapshot pricing v5 (F2-BE-11) ===
    # Firma fn_upsert_commessa_attivita li dichiara obbligatori: vanno passati
    # sempre, anche come NULL esplicito quando la dimensione non si applica
    # (es. classe_utenza per utility commercio, contratto per origine CATEGORIA).
    # La popolazione effettiva e' a carico di F2-BE-12 (wiring pricing_service
    # nei source handlers); per ora i caller passano None.
    prezzo_base_snapshot: Decimal | None = None
    origine_prezzo: str | None = None  # PROMO|CONTRATTO_OVERRIDE|CONTRATTO_LISTINO|CATEGORIA|MANUALE
    tipo_variazione_applicata: str | None = None  # PERCENTUALE|VALORE_FISSO|PREZZO_FISSO|NESSUNA
    valore_variazione_applicata: Decimal | None = None
    promo_id: int | None = None
    contratto_id: int | None = None
    categoria_cliente_id_snapshot: int | None = None
    classe_utenza_id_snapshot: int | None = None


@dataclass(frozen=True)
class PushableRow:
    """Riga normalizzata da fn_list_*_da_pushare — 26 colonne condivise."""

    billing_account_id: int
    utility_id: int | None
    emittente_soggetto_ruolo_id: int
    competenza_dal: date | None
    competenza_al: date | None
    fatturazione_immediata: bool
    sorgente_tipo_id: int
    sorgente_uid: str
    segment_key: str
    articolo_id: Any  # UUID o None (consumi)
    istanza_utility_id: int | None
    data_attivita: date | None
    uom_id: int | None
    quantita: Decimal | None
    qta_operativa: Decimal | None
    uom_operativa_id: int | None
    factor_to_base: Decimal
    competenza_mese: date
    prezzo_snapshot: Decimal | None
    prezzo_bloccato: bool
    pricing_mode: str
    tipo_movimento: str
    tipo_consumo: str
    valuta_id: int | None
    meta: dict[str, Any]
    tipo_doc_fiscale_id: int | None
    # ID della riga sorgente (es. `preventivi_righe.id`, `ordini_righe.id`).
    # Popolato dalle fn DB che lo espongono — None per sorgenti che non
    # hanno granularita' riga (es. CONSUMI) o nei test legacy senza override.
    # Usato dal BoMComponentExpander per leggere componenti pre-popolati su
    # `<sorgente>_righe_componenti` (refactor componenti 2026-05-11) invece
    # di chiamare il resolver al push. Default None per backward compat.
    riga_sorgente_id: int | None = None


def _decode_jsonb(value: Any, default: Any) -> Any:
    """Decodifica JSONB: gestisce str, dict, list. Unico punto di decodifica."""
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
    return default


def _map_pushable_row(col_map: dict[str, int], row: tuple) -> PushableRow:
    """Scopo: converte una tupla cursor in PushableRow usando la mappa colonne per nome."""
    def _col(name: str) -> Any:
        return row[col_map[name]]

    meta_raw = _decode_jsonb(_col("meta"), {})

    # Guard: sorgente_uid e segment_key devono essere non-null dal DB.
    raw_sorgente_uid = _col("sorgente_uid")
    raw_segment_key = _col("segment_key")
    if raw_sorgente_uid is None or raw_segment_key is None:
        raise ValueError(
            f"sorgente_uid o segment_key NULL dal DB: "
            f"sorgente_uid={raw_sorgente_uid!r}, segment_key={raw_segment_key!r}"
        )

    # Guard: factor_to_base=None → default Decimal(1); Decimal(0) preservato.
    raw_factor = _col("factor_to_base")
    factor_to_base = raw_factor if raw_factor is not None else Decimal(1)

    # riga_sorgente_id mappato dalla colonna `riga_id` se presente nella fn DB.
    # Le fn `fn_list_preventivi_da_pushare`/`fn_list_ordini_da_pushare`/etc.
    # lo espongono; CONSUMI no -> None default. `col_map.get` evita KeyError.
    riga_sorgente_id_raw = (
        row[col_map["riga_id"]] if "riga_id" in col_map else None
    )

    return PushableRow(
        billing_account_id=_col("billing_account_id"),
        utility_id=_col("utility_id"),
        emittente_soggetto_ruolo_id=_col("emittente_soggetto_ruolo_id"),
        competenza_dal=_col("competenza_dal"),
        competenza_al=_col("competenza_al"),
        fatturazione_immediata=bool(_col("fatturazione_immediata")),
        sorgente_tipo_id=_col("sorgente_tipo_id"),
        sorgente_uid=str(raw_sorgente_uid),
        riga_sorgente_id=(
            int(riga_sorgente_id_raw) if riga_sorgente_id_raw is not None else None
        ),
        segment_key=str(raw_segment_key),
        articolo_id=_col("articolo_id"),
        istanza_utility_id=_col("istanza_utility_id"),
        data_attivita=_col("data_attivita"),
        uom_id=_col("uom_id"),
        quantita=_col("quantita"),
        qta_operativa=_col("qta_operativa"),
        uom_operativa_id=_col("uom_operativa_id"),
        factor_to_base=factor_to_base,
        competenza_mese=_col("competenza_mese"),
        prezzo_snapshot=_col("prezzo_snapshot"),
        prezzo_bloccato=bool(_col("prezzo_bloccato")),
        pricing_mode=str(_col("pricing_mode")),
        tipo_movimento=str(_col("tipo_movimento")),
        tipo_consumo=str(_col("tipo_consumo")),
        valuta_id=_col("valuta_id"),
        meta=meta_raw,
        tipo_doc_fiscale_id=_col("tipo_doc_fiscale_id"),
    )


class CommesseRepository:
    """Wrapper SQL a basso livello per il dominio commesse."""

    @staticmethod
    def _to_jsonb_param(value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value)

    @staticmethod
    def _decode_jsonb(value: Any, default: Any) -> Any:
        return _decode_jsonb(value, default)

    # --- Gruppo 0: Fetch righe sorgente per push ---

    @staticmethod
    def validate_sorgente_map() -> list[str]:
        """Verifica _SORGENTE_FN_MAP contro config.sorgenti (scope=PUSH_COMMESSA).

        Restituisce lista di warning (vuota = tutto OK).
        Utile come safety-net a startup o nei test di integrazione.
        """
        warnings: list[str] = []
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COALESCE(codice_interno, codice) AS codice FROM config.sorgenti"
                " WHERE scope = 'PUSH_COMMESSA' AND attivo = true"
            )
            db_codici = {row[0] for row in cursor.fetchall()}

        map_codici = set(_SORGENTE_FN_MAP.keys())
        missing = db_codici - map_codici
        extra = map_codici - db_codici
        if missing:
            warnings.append(
                f"Sorgenti PUSH_COMMESSA nel DB ma non in _SORGENTE_FN_MAP: {sorted(missing)}"
            )
        if extra:
            warnings.append(
                f"Codici in _SORGENTE_FN_MAP ma non nel DB (scope PUSH_COMMESSA): {sorted(extra)}"
            )
        return warnings

    @staticmethod
    def list_active_push_sources() -> list[str]:
        """Codici sorgente attivi per scope PUSH_COMMESSA, ordinati per id registrazione."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COALESCE(codice_interno, codice) AS codice FROM config.sorgenti"
                " WHERE scope = 'PUSH_COMMESSA' AND attivo = true"
                " ORDER BY id"
            )
            return [row[0] for row in cursor.fetchall()]

    # Scopo: invoca la fn_list_<sorgente>_da_pushare parametrizzata e restituisce
    # le righe normalizzate come PushableRow. Unico punto di accesso per tutti gli handler.
    # `sorgente_uid` (opzionale) restringe la query alla riga sorgente del documento
    # specifico (es. preventivo_id per sorgente PREVENTIVO): None = lista globale del
    # batch orchestrator, valorizzato = push singolo UI-driven. Allinea col 4o param
    # `p_<sorgente>_id DEFAULT NULL` aggiunto alle fn DB lato `dev/db-tid` (vedi
    # docs/it/dev/work-in-progress/brief-db-fn-list-preventivi-push-singolo.md).
    def fetch_pushable_rows(
        self,
        sorgente_codice: str,
        *,
        competenza_mese: date | None = None,
        billing_account_id: int | None = None,
        limit: int | None = None,
        sorgente_uid: int | None = None,
        righe_ids: list[int] | None = None,
    ) -> list[PushableRow]:
        """Chiama fn_list_<sorgente>_da_pushare e restituisce PushableRow normalizzati."""
        fn_name = _SORGENTE_FN_MAP.get(sorgente_codice)
        ErrorManager.require(
            fn_name is not None,
            code="E_COMMESSA_SORGENTE_SCONOSCIUTA",
            message=f"Sorgente '{sorgente_codice}' non supportata per push",
        )
        assert fn_name is not None
        # `righe_ids` (sottoinsieme righe, smistamento selettivo dal Pannello
        # Smistamento): 5o parametro `p_righe_ids` disponibile solo sulle fn
        # delle sorgenti in _SORGENTE_SUPPORTA_RIGHE_IDS (oggi PREVENTIVO,
        # brief-db-smistamento-preventivi.md C). Guard esplicito: estendere la
        # whitelist quando le altre fn acquisiranno il parametro.
        ErrorManager.require(
            righe_ids is None or sorgente_codice in _SORGENTE_SUPPORTA_RIGHE_IDS,
            code="E_COMMESSA_VALIDATION",
            message="Filtro righe non supportato per questa sorgente.",
            detail=f"sorgente_codice={sorgente_codice} non supporta righe_ids",
        )

        # 4 param posizionali base (il 4o e' il filtro per id sorgente,
        # DEFAULT NULL lato DB se omesso ma qui sempre passato) + 5o
        # `p_righe_ids` SOLO quando valorizzato: le fn delle altre sorgenti
        # hanno 4 parametri e il 5o le romperebbe.
        placeholders = "%s, %s, %s, %s"
        params: list = [competenza_mese, billing_account_id, limit, sorgente_uid]
        if righe_ids is not None:
            placeholders += ", %s::bigint[]"
            params.append(righe_ids)

        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM {fn_name}({placeholders})",  # noqa: S608 — fn_name da whitelist
                params,
            )
            # Costruisce mappa colonna → indice per estrarre solo le 25 condivise.
            col_names = [desc[0] for desc in cursor.description]
            col_map = {name: idx for idx, name in enumerate(col_names) if name in _PUSHABLE_SHARED_COLS}
            # Include `riga_id` opzionalmente: alcune fn lo espongono
            # (preventivi/ordini/contratti/ddt), CONSUMI no. Serve al
            # BoMComponentExpander per leggere componenti pre-popolati
            # nelle tabelle `<sorgente>_righe_componenti` (refactor 2026-05-11).
            if "riga_id" in col_names:
                col_map["riga_id"] = col_names.index("riga_id")
            rows = cursor.fetchall()

        return [_map_pushable_row(col_map, row) for row in rows]

    # --- Gruppo 1: Commessa ---

    # Scopo: risolve o crea una commessa. Restituisce commessa_id.
    # Default allineati a fn_get_or_create_commessa.
    def get_or_create_commessa(
        self,
        *,
        billing_account_id: int,
        utility_id: int | None = None,
        tipo_commessa: str = TIPO_COMMESSA_AUTO,
        policy_fatturazione: str = POLICY_FATTURAZIONE_DA_DOCUMENTO,
        fatturazione_immediata: bool = False,
        priorita_operativa: str = PRIORITA_OPERATIVA_NORMALE,
        emittente_soggetto_ruolo_id: int | None = None,
        competenza_dal: date | None = None,
        competenza_al: date | None = None,
        meta: dict | None = None,
        force_new: bool = False,
    ) -> int:
        """Risolve o crea una commessa. Restituisce commessa_id."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_get_or_create_commessa(
                    p_billing_account_id => %s,
                    p_utility_id => %s,
                    p_tipo_commessa => %s,
                    p_policy_fatturazione => %s,
                    p_fatturazione_immediata => %s,
                    p_priorita_operativa => %s,
                    p_emittente_soggetto_ruolo_id => %s,
                    p_competenza_dal => %s,
                    p_competenza_al => %s,
                    p_meta => %s::jsonb,
                    p_force_new => %s
                )
                """,
                [
                    billing_account_id,
                    utility_id,
                    tipo_commessa,
                    policy_fatturazione,
                    fatturazione_immediata,
                    priorita_operativa,
                    emittente_soggetto_ruolo_id,
                    competenza_dal,
                    competenza_al,
                    self._to_jsonb_param(meta),
                    force_new,
                ],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    def link_sorgente(
        self,
        *,
        commessa_id: int,
        sorgente_tipo_id: int,
        sorgente_uid: str,
        sorgente_riga: int | None = None,
        meta: dict | None = None,
    ) -> int:
        """Collega la sorgente ROOT alla commessa. Idempotente su stesso sorgente_uid.
        Restituisce il link_id."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_link_commessa_sorgente(
                    p_commessa_id => %s,
                    p_sorgente_tipo_id => %s,
                    p_sorgente_uid => %s,
                    p_sorgente_riga => %s,
                    p_meta => %s::jsonb
                )
                """,
                [
                    commessa_id,
                    sorgente_tipo_id,
                    sorgente_uid,
                    sorgente_riga,
                    self._to_jsonb_param(meta or {}),
                ],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    def approva_commessa_attivita(
        self,
        *,
        commessa_id: int,
        righe_ids: list[int] | None = None,
        user: str | None = None,
    ) -> int:
        """Porta le righe commessa BOZZA→APPROVATA (righe_ids NULL = tutte le
        NON_EMESSA). Idempotente. Restituisce il numero di righe approvate.
        Wrapper di vendite.fn_approva_commessa_attivita (macchina transizioni)."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_approva_commessa_attivita(
                    p_commessa_id => %s,
                    p_righe_ids => %s,
                    p_user => %s
                )
                """,
                [commessa_id, righe_ids, user],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    def cambia_stato_commessa(
        self,
        *,
        commessa_id: int,
        nuovo_stato: str,
        user: str | None = None,
    ) -> dict[str, Any]:
        """Transizione di stato sanzionata della testata commessa (guard di
        matrice + guard di dominio a DB). Restituisce {commessa_id, stato_da,
        stato_a}. Wrapper di vendite.fn_cambia_stato_commessa."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT commessa_id, stato_da, stato_a
                FROM vendite.fn_cambia_stato_commessa(
                    p_commessa_id => %s,
                    p_nuovo_stato => %s,
                    p_user => %s
                )
                """,
                [commessa_id, nuovo_stato, user],
            )
            row = cursor.fetchone()
        assert row is not None
        return {"commessa_id": int(row[0]), "stato_da": row[1], "stato_a": row[2]}

    def get_commessa_id_by_sorgente(
        self, *, sorgente_codice: str, sorgente_uid: str,
        ruolo_link: str | None = None,
    ) -> int | None:
        """commessa_id collegata a una sorgente via vendite.commesse_sorgenti,
        o None. Risolve sorgente_tipo_id da config.sorgenti per codice_interno.
        Usato per l'idempotenza del push preventivo→commessa.

        ruolo_link=None (default) = QUALUNQUE ruolo: col modello commessa
        multi-sorgente (auto-ruolo DB) la prima sorgente e' ROOT ma le
        successive che confluiscono nella stessa commessa sono COLLEGATO —
        filtrare per ROOT nasconderebbe il link di un preventivo confluito
        (bug trovato dallo smoke pratica CONFERMA, 2026-06-11)."""
        sql = """
            SELECT cs.commessa_id
            FROM vendite.commesse_sorgenti cs
            JOIN config.sorgenti s ON s.id = cs.sorgente_tipo_id
            WHERE s.codice_interno = %s
              AND cs.sorgente_uid = %s
              AND (%s::text IS NULL OR cs.ruolo_link = %s)
            LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [sorgente_codice, sorgente_uid, ruolo_link, ruolo_link])
            row = cursor.fetchone()
        return int(row[0]) if row else None

    def get_commessa_stato(self, commessa_id: int) -> CommessaStatoResult | None:
        """Stato testata + flag di governance + contatori della commessa in un
        round-trip. Espone tutti i campi prodotti da `fn_get_commessa_stato`
        (flag chiude/emittibile/modificabile, config testata, contatori righe):
        servono alla UI commesse per stato e azioni senza chiamate extra."""

        def _int(v: object) -> int | None:
            return int(v) if v is not None else None  # type: ignore[arg-type]

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT stato_commessa_id, stato_commessa,
                       chiude_commessa, emittibile, modificabile,
                       policy_fatturazione, fatturazione_immediata, priorita_operativa,
                       billing_account_id, utility_id, emittente_soggetto_ruolo_id,
                       total_attivita, total_approvate, total_non_approvate,
                       total_emesse, total_non_emesse, total_prezzo_da_riallineare,
                       last_update
                FROM vendite.fn_get_commessa_stato(%s)
                """,
                [commessa_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return CommessaStatoResult(
            stato_commessa_id=int(row[0]),
            stato_commessa=row[1],
            chiude_commessa=bool(row[2]),
            emittibile=bool(row[3]),
            modificabile=bool(row[4]),
            policy_fatturazione=row[5],
            fatturazione_immediata=(None if row[6] is None else bool(row[6])),
            priorita_operativa=_int(row[7]),
            billing_account_id=_int(row[8]),
            utility_id=_int(row[9]),
            emittente_soggetto_ruolo_id=_int(row[10]),
            total_attivita=int(row[11]),
            total_approvate=int(row[12]),
            total_non_approvate=int(row[13]),
            total_emesse=int(row[14]),
            total_non_emesse=int(row[15]),
            total_prezzo_da_riallineare=int(row[16]),
            last_update=(row[17].isoformat() if row[17] is not None else None),
        )

    def get_commessa_stato_codice(self, commessa_id: int) -> str | None:
        """`codice_interno` dello stato corrente della testata commessa, o None
        se inesistente. Usato dall'orchestratore CONFERMA_VENDITA per lo skip
        idempotente della transizione a PRONTA_FATTURAZIONE quando una commessa
        multi-sorgente è già stata portata pronta da una sorgente precedente."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT sc.codice_interno
                  FROM vendite.commesse c
                  JOIN vendite.stati_commessa sc ON sc.id = c.stato_commessa_id
                 WHERE c.id = %s
                """,
                [commessa_id],
            )
            row = cursor.fetchone()
        return row[0] if row else None

    # --- Gruppo 2: Attività commessa ---

    def upsert_attivita(self, inp: CommessaAttivitaInput) -> UpsertAttivitaResult:
        """Inserisce o aggiorna una riga operativa sulla commessa (idempotente su segment_key).
        Restituisce UpsertAttivitaResult(attivita_id, is_new)."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT attivita_id, is_new FROM vendite.fn_upsert_commessa_attivita(
                    p_commessa_id => %s,
                    p_segment_key => %s,
                    p_articolo_id => %s,
                    p_istanza_utility_id => %s,
                    p_data_attivita => %s,
                    p_uom_id => %s,
                    p_quantita => %s,
                    p_competenza_mese => %s,
                    p_competenza_dal => %s,
                    p_competenza_al => %s,
                    p_prezzo_snapshot => %s,
                    p_prezzo_base_snapshot => %s,
                    p_origine_prezzo => %s,
                    p_tipo_variazione_applicata => %s,
                    p_valore_variazione_applicata => %s,
                    p_promo_id => %s,
                    p_contratto_id => %s,
                    p_categoria_cliente_id_snapshot => %s,
                    p_classe_utenza_id_snapshot => %s,
                    p_qta_operativa => %s,
                    p_uom_operativa_id => %s,
                    p_factor_to_base => %s,
                    p_posticipa_al => %s,
                    p_tipo_doc_fiscale_id => %s,
                    p_valuta_id => %s,
                    p_area_geografica_id => %s,
                    p_listino_versione_id => %s,
                    p_prezzo_bloccato => %s,
                    p_pricing_mode => %s,
                    p_prezzo_da_riallineare => %s,
                    p_stato_approvazione => %s,
                    p_stato_emissione => %s,
                    p_sorgente_tipo_id => %s,
                    p_sorgente_uid => %s,
                    p_tipo_movimento => %s,
                    p_tipo_consumo => %s,
                    p_meta => %s::jsonb
                )
                """,
                [
                    inp.commessa_id,
                    inp.segment_key,
                    inp.articolo_id,
                    inp.istanza_utility_id,
                    inp.data_attivita,
                    inp.uom_id,
                    inp.quantita,
                    inp.competenza_mese,
                    inp.competenza_dal,
                    inp.competenza_al,
                    inp.prezzo_snapshot,
                    inp.prezzo_base_snapshot,
                    inp.origine_prezzo,
                    inp.tipo_variazione_applicata,
                    inp.valore_variazione_applicata,
                    inp.promo_id,
                    inp.contratto_id,
                    inp.categoria_cliente_id_snapshot,
                    inp.classe_utenza_id_snapshot,
                    inp.qta_operativa,
                    inp.uom_operativa_id,
                    inp.factor_to_base,
                    inp.posticipa_al,
                    inp.tipo_doc_fiscale_id,
                    inp.valuta_id,
                    inp.area_geografica_id,
                    inp.listino_versione_id,
                    inp.prezzo_bloccato,
                    inp.pricing_mode,
                    inp.prezzo_da_riallineare,
                    inp.stato_approvazione,
                    inp.stato_emissione,
                    inp.sorgente_tipo_id,
                    inp.sorgente_uid,
                    inp.tipo_movimento,
                    inp.tipo_consumo,
                    self._to_jsonb_param(inp.meta),
                ],
            )
            row = cursor.fetchone()
        assert row is not None
        return UpsertAttivitaResult(attivita_id=int(row[0]), is_new=bool(row[1]))

    # --- Gruppo 2b: Batch upsert attività ---

    @staticmethod
    def _inp_to_jsonb_row(inp: CommessaAttivitaInput) -> dict:
        """Serializza CommessaAttivitaInput in dict JSONB-safe per fn_batch_upsert."""
        def _date(v: date | None) -> str | None:
            return v.isoformat() if v else None

        def _decimal(v: Decimal | None) -> str | None:
            return str(v) if v is not None else None

        return {
            "commessa_id": inp.commessa_id,
            "segment_key": inp.segment_key,
            "articolo_id": str(inp.articolo_id) if inp.articolo_id else None,
            "istanza_utility_id": inp.istanza_utility_id,
            "data_attivita": _date(inp.data_attivita),
            "uom_id": inp.uom_id,
            "quantita": _decimal(inp.quantita),
            "competenza_mese": _date(inp.competenza_mese),
            "competenza_dal": _date(inp.competenza_dal),
            "competenza_al": _date(inp.competenza_al),
            "prezzo_snapshot": _decimal(inp.prezzo_snapshot),
            "qta_operativa": _decimal(inp.qta_operativa),
            "uom_operativa_id": inp.uom_operativa_id,
            "factor_to_base": _decimal(inp.factor_to_base),
            "posticipa_al": _date(inp.posticipa_al),
            "tipo_doc_fiscale_id": inp.tipo_doc_fiscale_id,
            "valuta_id": inp.valuta_id,
            "area_geografica_id": inp.area_geografica_id,
            "listino_versione_id": inp.listino_versione_id,
            "prezzo_bloccato": inp.prezzo_bloccato,
            "pricing_mode": inp.pricing_mode,
            "prezzo_da_riallineare": inp.prezzo_da_riallineare,
            "stato_approvazione": inp.stato_approvazione,
            "stato_emissione": inp.stato_emissione,
            "sorgente_tipo_id": inp.sorgente_tipo_id,
            "sorgente_uid": inp.sorgente_uid,
            "tipo_movimento": inp.tipo_movimento,
            "tipo_consumo": inp.tipo_consumo,
            "meta": inp.meta or {},
            # Snapshot pricing v5 (F2-BE-11). Il wrapper batch DB deve
            # estrarre queste chiavi e passarle a fn_upsert_commessa_attivita
            # (dipendenza DB: estensione `fn_batch_upsert_commessa_attivita`).
            "prezzo_base_snapshot": _decimal(inp.prezzo_base_snapshot),
            "origine_prezzo": inp.origine_prezzo,
            "tipo_variazione_applicata": inp.tipo_variazione_applicata,
            "valore_variazione_applicata": _decimal(inp.valore_variazione_applicata),
            "promo_id": inp.promo_id,
            "contratto_id": inp.contratto_id,
            "categoria_cliente_id_snapshot": inp.categoria_cliente_id_snapshot,
            "classe_utenza_id_snapshot": inp.classe_utenza_id_snapshot,
        }

    def batch_upsert_attivita(self, inputs: list[CommessaAttivitaInput]) -> BatchUpsertResult:
        """Upsert batch di righe attivita in una sola chiamata DB.
        Restituisce BatchUpsertResult con contatori e errori per riga."""
        if not inputs:
            return BatchUpsertResult(total_rows=0, inserted=0, updated=0, errors=[])
        rows_json = json.dumps([self._inp_to_jsonb_row(inp) for inp in inputs])
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM vendite.fn_batch_upsert_commessa_attivita(%s::jsonb)",
                [rows_json],
            )
            row = cursor.fetchone()
        assert row is not None
        errors_raw = _decode_jsonb(row[3], [])
        return BatchUpsertResult(
            total_rows=int(row[0]),
            inserted=int(row[1]),
            updated=int(row[2]),
            errors=errors_raw if isinstance(errors_raw, list) else [],
        )

    # --- Gruppo 3: Emit attività fatturabili (pull) ---

    def emit_attivita_fatturabili(
        self,
        commessa_id: int,
        *,
        lotto_attivita_id: int | None = None,
        only_approved: bool = True,
        dry_run: bool = False,
    ) -> CommessaEmitResult:
        """Pull commessa → attivita_fatturabili (step 0 pipeline fatturazione).
        Idempotente. Restituisce contatori candidati/inseriti/aggiornati."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT total_candidate, inserted_rows, updated_rows
                FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
                    p_commessa_id => %s,
                    p_lotto_attivita_id => %s,
                    p_only_approved => %s,
                    p_dry_run => %s
                )
                """,
                [commessa_id, lotto_attivita_id, only_approved, dry_run],
            )
            row = cursor.fetchone()
        assert row is not None
        return CommessaEmitResult(
            total_candidate=int(row[0]),
            inserted_rows=int(row[1]),
            updated_rows=int(row[2]),
        )

    # Scopo: Restituisce le commesse emittibili nel perimetro del contesto lotto.
    def list_commesse_emittibili(
        self,
        *,
        competenza_mese: date | None = None,
        billing_account_id: int | None = None,
        utility_id: int | None = None,
        emittente_soggetto_ruolo_id: int | None = None,
        limit: int = 1000,
    ) -> list[int]:
        """Chiama vendite.fn_list_commesse_emittibili e restituisce i commessa_id."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT commessa_id
                FROM vendite.fn_list_commesse_emittibili(
                    p_competenza_mese => %s,
                    p_billing_account_id => %s,
                    p_utility_id => %s,
                    p_emittente_soggetto_ruolo_id => %s,
                    p_limit => %s
                )
                """,
                [competenza_mese, billing_account_id, utility_id,
                 emittente_soggetto_ruolo_id, limit],
            )
            return [row[0] for row in cursor.fetchall()]

    # --- Gruppo 3b: Lista attività commessa (paginata) ---

    # Colonne restituite da vendite.fn_list_commessa_attivita.
    _ATTIVITA_COLS = (
        "id", "commessa_id", "segment_key", "articolo_id",
        "istanza_utility_id", "data_attivita", "uom_id", "quantita",
        "competenza_mese", "competenza_dal", "competenza_al",
        "prezzo_snapshot", "prezzo_bloccato", "prezzo_da_riallineare",
        "stato_approvazione", "stato_emissione", "sorgente_tipo_id",
        "sorgente_codice", "meta", "data_update",
    )
    # Type mapping per serializzazione colonne attivita.
    _ATTIVITA_DATE_COLS = frozenset({
        "data_attivita", "competenza_mese", "competenza_dal", "competenza_al", "data_update",
    })
    _ATTIVITA_JSONB_COLS = frozenset({"meta"})
    _ATTIVITA_UUID_COLS = frozenset({"articolo_id"})

    def list_commessa_attivita(
        self,
        commessa_id: int,
        *,
        stato_emissione: str | None = None,
        stato_approvazione: str | None = None,
        competenza_mese: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """Lista paginata attività di una commessa via vendite.fn_list_commessa_attivita.

        Restituisce {"count": <total_righe_filtrate>, "rows": [dict, ...]}.
        """
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

        # Parametri WHERE condivisi tra count e data query.
        where_params: list = [commessa_id]
        where_clauses = ["ca.commessa_id = %s"]
        if stato_emissione is not None:
            where_clauses.append("ca.stato_emissione = %s")
            where_params.append(stato_emissione)
        if stato_approvazione is not None:
            where_clauses.append("ca.stato_approvazione = %s")
            where_params.append(stato_approvazione)
        if competenza_mese is not None:
            where_clauses.append("ca.competenza_mese = date_trunc('month', %s::date)::date")
            where_params.append(competenza_mese)
        where_sql = " AND ".join(where_clauses)

        _cols_sql = ", ".join(self._ATTIVITA_COLS)
        with connection.cursor() as cursor:
            # Total count (stessi filtri, senza LIMIT/OFFSET).
            cursor.execute(
                f"SELECT COUNT(*) FROM vendite.commesse_attivita ca WHERE {where_sql}",
                where_params,
            )
            count_row = cursor.fetchone()
            total_count = int(count_row[0]) if count_row else 0

            # Data query paginata.
            cursor.execute(
                f"""
                SELECT {_cols_sql}
                FROM vendite.fn_list_commessa_attivita(
                    p_commessa_id => %s,
                    p_stato_emissione => %s,
                    p_stato_approvazione => %s,
                    p_competenza_mese => %s,
                    p_limit => %s,
                    p_offset => %s
                )
                """,  # noqa: S608 — colonne da costante _ATTIVITA_COLS
                [commessa_id, stato_emissione, stato_approvazione,
                 competenza_mese, safe_limit, safe_offset],
            )
            raw_rows = cursor.fetchall()

        rows = []
        for raw in raw_rows:
            row_dict: dict[str, Any] = {}
            for idx, col in enumerate(self._ATTIVITA_COLS):
                val = raw[idx]
                if col in self._ATTIVITA_JSONB_COLS:
                    val = self._decode_jsonb(val, {})
                elif col in self._ATTIVITA_DATE_COLS and val is not None:
                    val = val.isoformat()
                elif col in self._ATTIVITA_UUID_COLS and val is not None:
                    val = str(val)
                row_dict[col] = val
            rows.append(row_dict)

        return {"count": total_count, "rows": rows}

    # --- Gruppo 4: Push log ---

    def log_push_run(
        self,
        *,
        stato: str,
        dry_run: bool = False,
        source_types: list[str] | None = None,
        risultato: dict[str, Any] | None = None,
        durata_ms: int | None = None,
    ) -> int:
        """Registra il risultato di un run dell'orchestratore push.
        Restituisce push_log_id."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_log_commessa_push_run(
                    p_dry_run => %s,
                    p_source_types => %s,
                    p_risultato => %s::jsonb,
                    p_stato => %s,
                    p_durata_ms => %s
                )
                """,
                [
                    dry_run,
                    source_types,
                    self._to_jsonb_param(risultato),
                    stato,
                    durata_ms,
                ],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    def get_push_log(self, push_log_id: int) -> CommessaPushLogRow | None:
        """Legge un record di push log per id."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, run_at, dry_run, source_types,
                       risultato, stato, durata_ms
                FROM vendite.commesse_push_log
                WHERE id = %s
                """,
                [push_log_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        risultato_raw: Any = self._decode_jsonb(row[4], None)
        return CommessaPushLogRow(
            id=int(row[0]),
            run_at=row[1].isoformat() if row[1] else "",
            dry_run=bool(row[2]),
            source_types=list(row[3]) if row[3] else None,
            risultato=risultato_raw if isinstance(risultato_raw, dict) else None,
            stato=str(row[5]),
            durata_ms=None if row[6] is None else int(row[6]),
        )

    # --- Gruppo 5: Pricing operations (N5, N7, N7-sblocco) ---

    # Scopo: Blocca l'attivita` commessa con FOR UPDATE per prevenire race condition
    #        durante operazioni pricing (N5, N7, N7-sblocco).
    def lock_attivita_for_update(self, attivita_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM vendite.commesse_attivita WHERE id = %s FOR UPDATE",
                [attivita_id],
            )
            return cursor.fetchone() is not None

    # Scopo: Restituisce l'attivita` di una commessa con dati pricing e stato fatturazione.
    def get_attivita_pricing(self, commessa_id: int, attivita_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    ca.id,
                    ca.commessa_id,
                    ca.prezzo_snapshot,
                    ca.prezzo_bloccato,
                    ca.listino_versione_id,
                    ca.listino_riga_id,
                    ca.pricing_mode,
                    ca.prezzo_da_riallineare,
                    ca.articolo_id,
                    ca.uom_id,
                    ca.data_attivita,
                    ca.meta,
                    sc.codice_interno AS commessa_stato,
                    sc.modificabile AS commessa_modificabile,
                    c.billing_account_id,
                    c.utility_id,
                    c.emittente_soggetto_ruolo_id,
                    af.id AS af_id,
                    af.prezzo_unitario AS af_prezzo_unitario,
                    af.prezzo_bloccato AS af_prezzo_bloccato,
                    af.fattura_riga_id
                  FROM vendite.commesse_attivita ca
                  JOIN vendite.commesse c ON c.id = ca.commessa_id
                  JOIN vendite.stati_commessa sc ON sc.id = c.stato_commessa_id
                  LEFT JOIN vendite.attivita_fatturabili af
                    ON af.commessa_attivita_id = ca.id
                 WHERE ca.commessa_id = %s
                   AND ca.id = %s
                """,
                [commessa_id, attivita_id],
            )
            from apps.core.db._helpers import row_to_dict
            return row_to_dict(cursor)

    # Scopo: Aggiorna prezzo snapshot su commessa_attivita + prezzo_unitario su
    #        attivita_fatturabili. Caller gestisce transazione.
    def update_attivita_prezzo(
        self,
        attivita_id: int,
        prezzo: str,
        prezzo_bloccato: bool,
        meta: dict[str, Any] | None,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.commesse_attivita
                   SET prezzo_snapshot = %(prezzo)s::numeric,
                       prezzo_bloccato = %(bloccato)s,
                       prezzo_da_riallineare = FALSE,
                       meta = %(meta)s::jsonb,
                       data_update = now()
                 WHERE id = %(att_id)s
                """,
                {
                    "att_id": attivita_id,
                    "prezzo": prezzo,
                    "bloccato": prezzo_bloccato,
                    "meta": json.dumps(meta) if meta else None,
                },
            )
            # Propaga su attivita_fatturabili (se esiste la riga collegata)
            cursor.execute(
                """
                UPDATE vendite.attivita_fatturabili
                   SET prezzo_unitario = %(prezzo)s::numeric,
                       prezzo_bloccato = %(bloccato)s,
                       data_update = now()
                 WHERE commessa_attivita_id = %(att_id)s
                   AND fattura_riga_id IS NULL
                """,
                {
                    "att_id": attivita_id,
                    "prezzo": prezzo,
                    "bloccato": prezzo_bloccato,
                },
            )

    # --- Gruppo 6: Event log ---

    # Scopo: Scrive un evento su vendite.event_log tramite fn_log_event.
    def log_event(
        self,
        *,
        domain: str,
        entity_type: str,
        entity_id: int,
        event_code: str,
        severity: str = "INFO",
        correlation_id: str | None = None,
        actor: str = "service:django",
        source: str = "django",
        payload: dict[str, Any] | None = None,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_log_event(
                    %s, %s, %s, %s, %s, %s::uuid, %s, %s, %s::jsonb
                )
                """,
                [
                    domain,
                    entity_type,
                    entity_id,
                    event_code,
                    severity,
                    correlation_id,
                    actor,
                    source,
                    self._to_jsonb_param(payload or {}),
                ],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])
