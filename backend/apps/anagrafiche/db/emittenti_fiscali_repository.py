# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per gestione emittenti fiscali (ruolo EF).
#        CRUD emittenti, lista paginata via JOIN soggetti_ruoli + soggetti.
#        Accesso DB-first via cursor; la creazione e' la madre
#        anagrafiche.fn_crea_emittente_fiscale.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from django.db import connection

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db.sql_write_helpers import execute_dynamic_insert, execute_dynamic_update
from apps.core.db._helpers import (
    colonna_ordinamento,
    sql_order_direction_lista,
    RicercaFull,
    add_ricerca_full_condition,
    sql_order_clause,
    sql_tiebreak_direction,
    fetch_paged_with_total,
    row_to_dict,
)


# Whitelist colonne ammesse per ORDER BY: chiave = `campo_sorgente` del catalogo
# 'anagrafiche.emittenti_fiscali' (e' quello che `<ListaConfigurabile>` invia
# come sortField), valore = espressione SQL qualificata.
#
# `partita_iva` aggiunta il 2026-07-31 col seed del secondo lotto: per un
# emittente la P.IVA *e'* l'identificativo fiscale, quindi appartiene al nucleo
# sempre ordinabile. `valuta_iso` e `regime_fiscale_rf` restano fuori: nel seed
# sono `ordinabile=f`.
#
# `descrizione` rimossa il 2026-08-02 con la DROP della colonna
# (`20260802-22`, brief `brief-emittente-ragione-sociale-dal-soggetto.md`): il
# nome dell'emittente e' la ragione sociale del suo soggetto. Il seed della
# lista 18 ha tolto la colonna e il preset ordina ora per
# `ragione_sociale_completa` — il default qui sotto deve dire la stessa cosa,
# altrimenti la lista nasce ordinata diversamente da come si dichiara.
_EMITTENTI_ORDER_COLS: dict[str, str] = {
    "codice": "ef.codice",
    "ragione_sociale_completa": "s.ragione_sociale_completa",
    "partita_iva": "s.partita_iva",
    "attivo": "ef.attivo",
    "data_insert": "ef.data_insert",
}

# Colonna d'ordinamento di default: allineata all'`ordinamento_default` del
# preset `emittenti_fiscali_default` (seed `lista_preset`, riga 18).
_EMITTENTI_ORDER_DEFAULT = "ragione_sociale_completa"


# Cosa si PUO' cercare; cosa si cerca lo dice il catalogo (`add_ricerca_full_condition`).
# ⭐ Emittenti: si cerca per id fiscale univoco, per uniformita' con le altre
#    anagrafiche (Tid, 2026-09-23). `partita_iva` tolta il 2026-09-24, dopo che
#    il seed l'ha spenta (brief DB §3.2): l'id fiscale univoco la contiene.
_RICERCA_EMITTENTI = RicercaFull("anagrafiche.emittenti_fiscali", {
    "codice": "ef.codice",
    "ragione_sociale_completa": "s.ragione_sociale_completa",
    "id_fiscale_univoco_cf_piva": "s.id_fiscale_univoco_cf_piva",
})
_RICERCA_EMITTENTE_BA = RicercaFull("anagrafiche.emittente_billing_account", {
    "billing_account_codice": "ba.codice",
    "billing_account_ragione_sociale": "s.ragione_sociale_completa",
    "id_fiscale_univoco": "s.id_fiscale_univoco_cf_piva",
})


# Campi editabili sull'emittente (codice escluso: bloccato dal trigger lock_columns).
# `descrizione` tolta il 2026-08-02 con la DROP della colonna: il nome
# dell'emittente si cambia sul SOGGETTO, non qui.
# ⚠️ Whitelist RIGIDA del BB `execute_dynamic_update` (2026-09-26): e' anche la
#    base del contratto PATCH che `EmittentiFiscaliService` valida (400).
EMITTENTE_UPDATE_ALLOWED: frozenset[str] = frozenset({
    "attivo",
    "regime_fiscale_rf",
    "bollo_auto",
    "bollo_soglia",
    "rounding_policy",
    "valuta_id",
})


# ⭐ LA CONFERMA DEL REGIME FISCALE (§10 di brief-db-esigibilita-iva-per-cassa-
#    emittente, applicato il 2026-10-02): data e autore li DERIVA il database.
#    Ogni `UPDATE OF regime_fiscale_rf`, anche con lo stesso valore, e' una
#    dichiarazione del regime e il trigger `trgfn_emittenti_fiscali_regime_
#    conferma` scrive `confermato_il`/`_da` (autore da `app.jwt_user`).
#    ⛔ Le due colonne di conferma non si scrivono da qui: il guard
#    `trgfn_emittenti_fiscali_guard_regime_conferma` le RIFIUTA
#    (`E_EMITTENTE_REGIME_CONFERMA_DERIVATA`). Restano fuori dalle whitelist
#    di create e update, e il BB le ferma prima di arrivare al DB.
#    ⚠️ Una INSERT non conferma mai (il default RF01 e un RF01 scelto sono
#    indistinguibili): chi crea dichiarando il regime fa poi un UPDATE del
#    regime nella stessa transazione (`EmittentiFiscaliService.crea_emittente`).


class EmittentiFiscaliRepository:
    """Accesso DB per emittenti fiscali."""

    # =================================================================
    # Lookup
    # =================================================================

    # Scopo: Risolve il `soggetto_ruolo_id` dell'emittente fiscale dato il
    # suo `id` (PK reale). Single source of truth per i caller cross-dominio
    # (vendite/preventivi/contratti) che devono passare lo sr_id alle fn
    # pricing/componenti (che lavorano su soggetto_ruolo_id, non sulla PK
    # `emittenti_fiscali.id`). Vedi memoria `feedback_emittente_pk_vs_soggetto_ruolo`.
    # Ritorna None se l'id non esiste. Estratto da
    # `*Repository.get_emittente_sr_id_by_fiscale_id` duplicato simmetrico
    # (Fase H residue 2026-05-14): i repo sorgente ora delegano qui.
    def get_sr_id_by_fiscale_id(self, fiscale_id: int) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali "
                "WHERE id = %s",
                [fiscale_id],
            )
            row = cursor.fetchone()
            return int(row[0]) if row else None

    # =================================================================
    # Creazione
    # =================================================================

    # Scopo: Crea l'emittente fiscale di un soggetto con la madre del DB
    #        `anagrafiche.fn_crea_emittente_fiscale`: il ruolo EF (creato se
    #        manca) e la riga, in un'istruzione. `campi` sono le chiavi
    #        opzionali (le assenti al DEFAULT; una chiave estranea la rifiuta
    #        il DB, `E_CAMPO_NON_AMMESSO`). Un regime indicato e' CONFERMATO dal
    #        verbo. Registri e mapping di default nascono dai trigger.
    #        Ritorna `(emittente_fiscale_id, soggetto_ruolo_id)`.
    # ⭐ Dal 2026-10-18 (2b-2 del brief-db-processi-accensione-per-ambiente):
    #    fino ad allora la saga ruolo + INSERT + UPDATE di conferma era scritta
    #    qui e nel builder pgTAP; la madre e' la sede unica.
    def crea_emittente_fiscale(
        self, soggetto_id: str, codice: str, campi: dict[str, Any],
    ) -> tuple[int, int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT emittente_fiscale_id, soggetto_ruolo_id
                  FROM anagrafiche.fn_crea_emittente_fiscale(%s::uuid, %s, %s::jsonb)
                """,
                [soggetto_id, codice, json.dumps(campi, default=str)],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0]), int(row[1])

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata emittenti fiscali con search e filtro attivo.
    #        Join con soggetti_ruoli e soggetti per display fields.
    def list_emittenti_fiscali(
        self, *,
        search: str | None = None,
        attivo: bool | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str = _EMITTENTI_ORDER_DEFAULT,
        order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_EMITTENTI_ORDER_COLS,
            default=_EMITTENTI_ORDER_COLS[_EMITTENTI_ORDER_DEFAULT],
            tiebreak="ef.id",
        )
        conditions: list[str] = ["(%s::boolean IS NULL OR ef.attivo = %s)"]
        params: list[Any] = [attivo, attivo]
        add_ricerca_full_condition(conditions, params, search, _RICERCA_EMITTENTI)
        sql = f"""
            SELECT ef.id,
                   ef.uid,
                   ef.soggetto_ruolo_id,
                   ef.codice,
                   ef.attivo,
                   ef.regime_fiscale_rf,
                   ef.bollo_auto,
                   ef.bollo_soglia,
                   ef.rounding_policy,
                   ef.valuta_id,
                   v.iso_code AS valuta_iso,
                   sr.soggetto_id,
                   s.ragione_sociale_completa,
                   s.codice_fiscale,
                   s.partita_iva,
                   s.id_fiscale_univoco_cf_piva,
                   ef.data_insert,
                   ef.data_update,
                   COUNT(*) OVER () AS total_count
              FROM anagrafiche.emittenti_fiscali ef
              JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ef.soggetto_ruolo_id
              JOIN anagrafiche.soggetti s        ON s.id  = sr.soggetto_id
              LEFT JOIN config.valute v          ON v.id  = ef.valuta_id
             WHERE {" AND ".join(conditions)}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params.extend([limit, offset])
        return fetch_paged_with_total(sql, params, offset=offset)

    # Scopo: Dettaglio completo di un emittente fiscale con dati soggetto e valuta.
    def get_emittente(self, emittente_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT ef.id,
                   ef.uid,
                   ef.soggetto_ruolo_id,
                   ef.codice,
                   ef.attivo,
                   ef.regime_fiscale_rf,
                   -- Il codice a video del regime: il catalogo lo tiene
                   -- distinto da `codice_interno` (BB FE `voceRegimeFiscale`).
                   rf.codice              AS regime_fiscale_codice,
                   rf.descrizione         AS regime_fiscale_descrizione,
                   ef.regime_fiscale_confermato_il,
                   ef.regime_fiscale_confermato_da,
                   ef.bollo_auto,
                   ef.bollo_soglia,
                   ef.rounding_policy,
                   ef.valuta_id,
                   v.iso_code             AS valuta_iso,
                   v.descrizione          AS valuta_descrizione,
                   ef.brand_meta,
                   -- Soggetto
                   sr.soggetto_id,
                   s.ragione_sociale_completa,
                   s.codice_fiscale,
                   s.partita_iva,
                   -- Audit
                   ef.data_insert,
                   ef.data_update
              FROM anagrafiche.emittenti_fiscali ef
              JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ef.soggetto_ruolo_id
              JOIN anagrafiche.soggetti s        ON s.id  = sr.soggetto_id
              LEFT JOIN config.valute v          ON v.id  = ef.valuta_id
              -- FK `fk_emittenti_fiscali_regimi_fiscali` + NOT NULL: la riga
              -- c'e' sempre; LEFT per non perdere l'emittente se un domani no.
              LEFT JOIN config.regimi_fiscali rf ON rf.codice_interno = ef.regime_fiscale_rf
             WHERE ef.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [emittente_id])
            return row_to_dict(cursor)

    # =================================================================
    # Aggiornamento
    # =================================================================

    # ⛔ `regime_fiscale_rf` NON c'e' piu' (2026-10-01): e' NOT NULL con FK al
    #    catalogo, e un vuoto portato a NULL diventava un 23502. Lo valida il
    #    service, che rifiuta il vuoto con 400 sul campo.
    _UPDATE_NULLABLE = {
        "rounding_policy",
        "bollo_soglia",
        "valuta_id",
    }

    # Scopo: Aggiorna campi editabili di un emittente fiscale (delta update).
    #        Il campo codice e' bloccato dal trigger DB (lock_columns) e va escluso.
    #        BB `execute_dynamic_update` (2026-09-26): whitelist RIGIDA
    #        `EMITTENTE_UPDATE_ALLOWED`, le chiavi le valida prima il service (400).
    #        ⭐ Se `data` porta `regime_fiscale_rf` la UPDATE lo nomina, e il
    #        database lo registra come conferma (vedi sopra).
    def update_emittente(self, emittente_id: int, data: dict[str, Any]) -> bool:
        # Copia: non si muta l'input del chiamante.
        valori = dict(data)
        # Normalizza stringhe vuote a None per campi nullable
        for k in self._UPDATE_NULLABLE:
            val = valori.get(k)
            if isinstance(val, str) and not val.strip():
                valori[k] = None
        return execute_dynamic_update(
            "anagrafiche.emittenti_fiscali", emittente_id, valori,
            allowed=EMITTENTE_UPDATE_ALLOWED,
        )

    # =================================================================
    # Risoluzione id <-> soggetto_ruolo_id
    # =================================================================

    # Scopo: Risolve soggetto_ruolo_id da emittente_id (per metodi sub-resource).
    def get_soggetto_ruolo_id(self, emittente_id: int) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali WHERE id = %s",
                [emittente_id],
            )
            row = cursor.fetchone()
            return row[0] if row else None

    # Scopo: Restituisce la P.IVA del soggetto base (None se non valorizzata).
    #        Usato per validare che l'emittente fiscale sia legato a un soggetto
    #        con P.IVA valida (requisito legale per emissione fattura SDI).
    def get_soggetto_partita_iva(self, soggetto_id: str) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT partita_iva FROM anagrafiche.soggetti WHERE id = %s",
                [soggetto_id],
            )
            row = cursor.fetchone()
            if not row:
                return None
            piva = row[0]
            if isinstance(piva, str):
                piva = piva.strip()
                return piva or None
            return piva


# =================================================================
# Sotto-tabella: emittenti_fiscali_billing_account (mapping BA -> emittente)
# =================================================================


class EmittentiFiscaliBillingAccountRepository:
    """Accesso DB per il mapping BA -> emittente fiscale.

    Regole:
      - Il default globale e' il record con billing_account_id IS NULL e is_default = true.
      - Esiste al piu' UN default (UNIQUE INDEX su is_default WHERE is_default).
      - Ogni BA puo' essere mappato a un solo emittente (UNIQUE su billing_account_id).
      - is_default e billing_account_id sono vincolati da un CHECK: True+NULL oppure False+NOT NULL.
    """

    # Whitelist ORDER BY: chiave = `campo_sorgente` del catalogo
    # 'anagrafiche.emittente_billing_account', valore = espressione qualificata.
    _ORDER_COLS: dict[str, str] = {
        "billing_account_codice": "ba.codice",
        "billing_account_ragione_sociale": "s.ragione_sociale_completa",
        "id_fiscale_univoco": "s.id_fiscale_univoco_cf_piva",
        "is_default": "m.is_default",
        "data_insert": "m.data_insert",
    }

    # Scopo: Lista paginata dei collegamenti BA di un emittente, con search su
    #        ragione_sociale_completa, codice BA e id_fiscale_univoco_cf_piva.
    #        IN CONSULTAZIONE dal 2026-11-27 (D-T4-3, Tid §26.2): niente piu'
    #        motivo di rimozione per riga (la LATERAL su
    #        `script.fn_check_ba_cambio_emittente`), perche' nessuna riga si
    #        toglie.
    def list_by_emittente(
        self,
        emittente_soggetto_ruolo_id: int,
        *,
        search: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str = "billing_account_codice",
        order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        order_col = (
            colonna_ordinamento(order_by, self._ORDER_COLS)
            or self._ORDER_COLS["billing_account_codice"]
        )
        direction = sql_order_direction_lista(
            order_by, order_dir, colonne=self._ORDER_COLS, default=order_col,
        )
        tiebreak_dir = sql_tiebreak_direction(direction)
        # Default-first e' il prefisso fisso dell'ordinamento (la riga default
        # in testa qualunque colonna si ordini). Se pero' l'operatore ordina
        # PROPRIO per is_default — colonna del catalogo, `ordinabile=t` — il
        # prefisso vincerebbe sempre sulla direzione scelta (freccia che non
        # ordina): in quel caso l'unica chiave e' la sua, con la sua direzione.
        order_prefix = "" if order_col == "m.is_default" else "m.is_default DESC, "
        conditions: list[str] = ["m.emittente_soggetto_ruolo_id = %s"]
        params: list[Any] = [emittente_soggetto_ruolo_id]
        add_ricerca_full_condition(conditions, params, search, _RICERCA_EMITTENTE_BA)
        sql = f"""
            SELECT m.id,
                   m.billing_account_id,
                   m.is_default,
                   ba.codice                   AS billing_account_codice,
                   s.ragione_sociale_completa   AS billing_account_ragione_sociale,
                   s.id_fiscale_univoco_cf_piva AS id_fiscale_univoco,
                   m.data_insert,
                   m.data_update,
                   COUNT(*) OVER ()            AS total_count
              FROM anagrafiche.emittenti_fiscali_billing_account m
              LEFT JOIN anagrafiche.billing_account ba ON ba.id = m.billing_account_id
              LEFT JOIN anagrafiche.soggetti_ruoli sr  ON sr.id = ba.soggetto_ruolo_id
              LEFT JOIN anagrafiche.soggetti s         ON s.id  = sr.soggetto_id
             WHERE {" AND ".join(conditions)}
             ORDER BY {order_prefix}{order_col} {direction}, m.id {tiebreak_dir}
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params.extend([limit, offset])
        rows, total = fetch_paged_with_total(sql, params, offset=offset)
        return rows, total

    # Scopo: Rende l'emittente l'azienda PREDEFINITA (la riga
    #        `billing_account_id` NULL, `is_default`): l'azienda in cui nascono i
    #        billing account creati senza sessione. La riga si SPOSTA, non si
    #        cancella e ricrea: il DB rifiuta la cancellazione di ogni
    #        collegamento, anche questo (`E_BA_COLLEGAMENTO_NON_SI_TOGLIE`: «la
    #        predefinita si cambia modificandola», giro 6). Ritorna l'id della
    #        riga, None se la predefinita non c'e'.
    # ⛔ Niente INSERT di ripiego: appena esiste un emittente la predefinita e'
    #    obbligatoria (la porta il bootstrap del primo emittente, e
    #    `trgfn_emittenti_fiscali_default_guard` la esige al COMMIT), quindi
    #    «non c'e'» e' uno stato che il modello esclude. Crearla qui rifarebbe
    #    in silenzio il lavoro del bootstrap; il None lo fa dire al service.
    def imposta_predefinita(self, emittente_soggetto_ruolo_id: int) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE anagrafiche.emittenti_fiscali_billing_account
                   SET emittente_soggetto_ruolo_id = %s
                 WHERE is_default
                RETURNING id
                """,
                [emittente_soggetto_ruolo_id],
            )
            row = cursor.fetchone()
        return None if row is None else int(row[0])

    # Scopo: Riepilogo dei mapping per un emittente, indipendente da paginazione/search.
    #        Usato dal FE per disabilitare il pulsante "default" senza dipendere dalla
    #        pagina corrente: vedi analisi-refactor.frontend-amm-software (A8/C3).
    def summary_by_emittente(
        self,
        emittente_soggetto_ruolo_id: int,
    ) -> dict[str, Any]:
        sql = """
            SELECT
                COUNT(*) FILTER (WHERE is_default)              AS default_count,
                COUNT(*) FILTER (WHERE NOT is_default)          AS specifici_count
              FROM anagrafiche.emittenti_fiscali_billing_account
             WHERE emittente_soggetto_ruolo_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [emittente_soggetto_ruolo_id])
            row = cursor.fetchone()
            assert row is not None
            return {
                "has_default": bool(row[0]),
                "count_specifici": int(row[1]),
            }


# =================================================================
# Sotto-tabella: emittenti_fiscali_utilities (parametri per emittente+utility)
# =================================================================


UTILITIES_UPDATE_ALLOWED: frozenset[str] = frozenset({
    "minimo_soglia_min",
    "minimo_soglia_max",
    "arrotondamento_importi_dec",
    "metodo_arrotondamento_importi",
    "attivo",
})
_UTILITIES_UPDATE_NULLABLE = {
    "minimo_soglia_min",
    "minimo_soglia_max",
}

# Identificatori della tabella override per il pattern slot/override.
# Costanti modulo: usate sia da list_by_emittente (delega a LookupRepository) sia
# implicitamente registrate nella whitelist di LookupRepository._ALLOWED_UTILITY_OVERRIDES.
# Allinearle se la tabella o la colonna FK cambia nome.
_UTILITIES_OVERRIDES_TABLE = "anagrafiche.emittenti_fiscali_utilities"
_UTILITIES_OVERRIDES_FK_COLUMN = "emittente_soggetto_ruolo_id"


class EmittentiFiscaliUtilitiesRepository:
    """Accesso DB per la matrice emittente_fiscale x utility (parametri fatturazione).

    Vincoli:
      - UNIQUE (emittente_soggetto_ruolo_id, utility_id)
      - Trigger child_requires_active_parent: emittente padre deve essere attivo
      - Trigger guard_utility_tipo_ruolo: la utility deve essere ammessa per il ruolo EF
        (vedi config.utilities_tipi_ruolo, fail-open se la utility non ha matrice)
    """

    # Scopo: Matrice utility ammesse per ruolo EF + override specifici dell'emittente.
    #        Delega al metodo generico LookupRepository.list_entity_utility_matrix
    #        (pattern slot/override). Ritorna SEMPRE tutte le utility ammesse: per
    #        quelle non personalizzate, i campi override sono NULL e record_id e' NULL.
    def list_by_emittente(self, emittente_soggetto_ruolo_id: int) -> list[dict[str, Any]]:
        from apps.core.db.lookup_repository import LookupRepository
        return LookupRepository().list_entity_utility_matrix(
            entity_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
            tipo_ruolo_codice="EF",
            overrides_table=_UTILITIES_OVERRIDES_TABLE,
            overrides_fk_column=_UTILITIES_OVERRIDES_FK_COLUMN,
        )

    # Scopo: Inserisce un record utility per l'emittente.
    #        Tutti i campi NOT NULL devono essere forniti (arrotondamento_dec, metodo).
    def create_record(
        self,
        *,
        emittente_soggetto_ruolo_id: int,
        utility_id: int,
        arrotondamento_importi_dec: int,
        metodo_arrotondamento_importi: str,
        minimo_soglia_min: Any = None,
        minimo_soglia_max: Any = None,
        attivo: bool | None = None,
    ) -> int:
        # BB `execute_dynamic_insert` (2026-09-26). `allowed=None`: le chiavi
        # sono i nomi letterali qui sotto. `skip_none=True`: gli opzionali a
        # None si omettono e resta il DEFAULT del DB, come prima.
        riga = execute_dynamic_insert(
            "anagrafiche.emittenti_fiscali_utilities",
            {
                "emittente_soggetto_ruolo_id": emittente_soggetto_ruolo_id,
                "utility_id": utility_id,
                "arrotondamento_importi_dec": arrotondamento_importi_dec,
                "metodo_arrotondamento_importi": metodo_arrotondamento_importi,
                "minimo_soglia_min": minimo_soglia_min,
                "minimo_soglia_max": minimo_soglia_max,
                "attivo": attivo,
            },
            allowed=None, skip_none=True,
        )
        return riga["id"]

    # Scopo: Aggiorna campi editabili (delta update). utility_id e' immutabile (PK logica).
    #        BB `execute_dynamic_update` (2026-09-26): whitelist RIGIDA
    #        `UTILITIES_UPDATE_ALLOWED`, le chiavi le valida prima il service.
    def update_record(self, record_id: int, data: dict[str, Any]) -> bool:
        clean = dict(data)
        for k in _UTILITIES_UPDATE_NULLABLE:
            if k in clean and isinstance(clean[k], str) and not clean[k].strip():
                clean[k] = None
        return execute_dynamic_update(
            "anagrafiche.emittenti_fiscali_utilities", record_id, clean,
            allowed=UTILITIES_UPDATE_ALLOWED,
        )

    # Scopo: Elimina un record utility per id.
    def delete_record(self, record_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM anagrafiche.emittenti_fiscali_utilities WHERE id = %s",
                [record_id],
            )
            return cursor.rowcount > 0

    # Scopo: Verifica appartenenza del record all'emittente atteso (sicurezza sub-resource).
    def belongs_to_emittente(self, record_id: int, emittente_soggetto_ruolo_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM anagrafiche.emittenti_fiscali_utilities
                 WHERE id = %s AND emittente_soggetto_ruolo_id = %s
                """,
                [record_id, emittente_soggetto_ruolo_id],
            )
            return cursor.fetchone() is not None


