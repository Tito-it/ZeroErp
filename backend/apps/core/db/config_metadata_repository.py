# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per metadata tabelle config via information_schema e
#        pg_catalog. Introspezione tecnica — non logica business (non viola
#        DB-first). I metadata sono cacheable in memoria (non cambiano a runtime).
#        Dal 2026-09-21 legge anche le CHIAVI ESTERNE (per il widget di lookup
#        del drawer generico) e i VINCOLI (per tradurre un IntegrityError nel
#        campo da correggere) — il drawer generico resta metadata-driven, ma
#        legge piu' modello (piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config §3).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.db.dbops_repository import LOOKUP_COLONNE_VALORE
from apps.core.db.tabelle_gestibili_repository import TabelleGestibiliRepository

# Colonne di sistema da escludere — audit, transazione, storicizzazione, e le
# identita' tecniche che scrive il DB (`uid` con default `uuidv7()`): un campo
# che l'operatore non deve compilare non si mostra come obbligatorio.
# ⚠️ Regola, non elenco: una colonna il cui default e' una FUNZIONE e che non
# e' mai un dato dell'operatore. Oggi `uid` e' la sola.
# ⛔ DUE SEDI, dichiarate (2026-09-25): la stessa lista e' la costante
# `c_escluse` del verbo `config.fn_pannello_scrivi`, che RIFIUTA le colonne
# che qui si nascondono. Se divergono, il form offre un campo che il
# salvataggio respinge (o nasconde uno che si potrebbe scrivere). Chiesto al
# team DB di esporre le colonne scrivibili con una funzione che il verbo e
# questo metadata leggano entrambi (brief-db-pannello-config-verbo-generico §6).
_EXCLUDED_COLUMNS = frozenset({
    "data_insert", "user_insert", "data_update", "user_update",
    "tx_id", "storicizza", "uid",
})

# Mapping tipo SQL → tipo frontend per il renderer dinamico.
_TYPE_MAP = {
    "integer": "number",
    "bigint": "number",
    "smallint": "number",
    "numeric": "number",
    "boolean": "boolean",
    "jsonb": "json",
    "json": "json",
    "text": "text",
    "character varying": "text",
    "character": "text",
    "varchar": "text",
    "char": "text",
    "date": "date",
    "timestamp with time zone": "datetime",
    "timestamp without time zone": "datetime",
    "uuid": "text",
}

# Cache in memoria — {schema.table: [columns]} e {schema.table: [constraints]}
_cache: dict[str, list[dict[str, Any]]] = {}
_cache_vincoli: dict[str, list[dict[str, Any]]] = {}

# Le FK a UNA colonna della tabella: {colonna: ("schema.tabella_target",
# "colonna_target")}. Da pg_catalog e non da information_schema:
# `referential_constraints` non porta le colonne, e ricomporle da
# `key_column_usage` vuole tre JOIN.
# ⚠️ La colonna TARGET viaggia perche' una FK non punta per forza a `id`: nel
# registro del pannello `config.stati_doc_*.esito` e
# `pratiche.template_flussi.esito_default` referenziano
# `config.esiti_flussi_pratiche(codice_interno)`. Senza, il FE avrebbe montato
# la `LookupSelect` col suo default `valueField='id'` e salvato un intero dove
# il DB vuole un codice (trovato in revisione il 2026-09-21).
_SQL_FK = """
    SELECT a.attname, cn.nspname || '.' || cl.relname, fa.attname
      FROM pg_constraint c
      JOIN pg_class t ON t.oid = c.conrelid
      JOIN pg_namespace tn ON tn.oid = t.relnamespace
      JOIN pg_class cl ON cl.oid = c.confrelid
      JOIN pg_namespace cn ON cn.oid = cl.relnamespace
      JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
      JOIN pg_attribute fa ON fa.attrelid = c.confrelid AND fa.attnum = c.confkey[1]
     WHERE c.contype = 'f'
       AND tn.nspname = %s AND t.relname = %s
       AND array_length(c.conkey, 1) = 1
"""

# I vincoli UNIQUE / FK / CHECK della tabella con le loro colonne, per nome.
_SQL_VINCOLI = """
    SELECT c.conname, c.contype,
           ARRAY(SELECT a.attname
                   FROM unnest(c.conkey) AS k(attnum)
                   JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
                  ORDER BY a.attnum)
      FROM pg_constraint c
      JOIN pg_class t ON t.oid = c.conrelid
      JOIN pg_namespace tn ON tn.oid = t.relnamespace
     WHERE c.contype IN ('u', 'f', 'c')
       AND tn.nspname = %s AND t.relname = %s
     ORDER BY c.conname
"""
_TIPO_VINCOLO = {"u": "unique", "f": "fk", "c": "check"}


# Scopo: Normalizza il `column_default` di information_schema nel valore tipizzato
# da usare come default del form di creazione. Restituisce None quando il default
# non e' un literal riconoscibile (es. sequenze nextval(...), espressioni now(),
# cast complessi): in quel caso il FE applica il proprio fallback.
def _parse_column_default(raw_default: str | None, fe_type: str) -> Any:
    if raw_default is None:
        return None
    # Strip cast esplicito (es. "'false'::boolean", "0::integer", "''::text").
    val = raw_default.split("::", 1)[0].strip()
    if fe_type == "boolean":
        # Postgres puo' rappresentare il default come `false` o `'false'`.
        unquoted = val[1:-1] if len(val) >= 2 and val[0] == "'" and val[-1] == "'" else val
        if unquoted in ("true", "false"):
            return unquoted == "true"
        return None
    if fe_type == "number":
        try:
            return int(val)
        except ValueError:
            try:
                return float(val)
            except ValueError:
                return None
    # text/date/json: prefill solo se literal stringa quotata, altrimenti None
    # (evita di propagare espressioni SQL come now() nel form).
    if len(val) >= 2 and val[0] == "'" and val[-1] == "'":
        return val[1:-1]
    return None


class ConfigMetadataRepository:
    """Legge metadata colonne da information_schema per il CRUD generico config."""

    # Scopo: Restituisce la lista colonne gestibili di una tabella.
    # Esclude colonne audit/sistema. Cacheable — si legge una volta.
    def get_table_columns(self, schema: str, table: str) -> list[dict[str, Any]]:
        cache_key = f"{schema}.{table}"
        if cache_key in _cache:
            return _cache[cache_key]

        # ⛔ Fuori anche le colonne che il DB calcola da se' (generate, identity
        # ALWAYS, salvo `id`): il verbo del pannello le RIFIUTA
        # (`E_PANNELLO_CAMPO_NON_AMMESSO`), quindi mostrarle nel form sarebbe
        # offrire un campo che il salvataggio respinge. Stessa regola del verbo.
        sql = """
            SELECT column_name, data_type, is_nullable, column_default
              FROM information_schema.columns
             WHERE table_schema = %s AND table_name = %s
               AND is_generated <> 'ALWAYS'
               AND (identity_generation IS DISTINCT FROM 'ALWAYS' OR column_name = 'id')
             ORDER BY ordinal_position
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [schema, table])
            rows = cursor.fetchall()
            cursor.execute(_SQL_FK, [schema, table])
            fk_per_colonna = {r[0]: (r[1], r[2]) for r in cursor.fetchall()}
        rel_lookup = TabelleGestibiliRepository().rel_lookup()

        columns = []
        for row in rows:
            col_name = row[0]
            if col_name in _EXCLUDED_COLUMNS:
                continue
            fe_type = _TYPE_MAP.get(row[1], "text")
            # ⭐ La FK dice al drawer QUALE tabella e QUALE colonna la colonna
            # nomina; se quella tabella e' ammessa al lookup generico E la
            # colonna target e' fra quelle che il lookup restituisce, il campo
            # diventa una `LookupSelect` (con `valueField` = colonna target),
            # altrimenti resta un valore a mano — e lo dichiara. Lo sa il BE
            # (`config.tabelle_gestibili`, `LOOKUP_COLONNE_VALORE`), non il FE: esce
            # come flag. ⛔ Il flag a `true` con una colonna che il lookup non
            # porta sarebbe una select che salva `undefined`.
            references, references_column = fk_per_colonna.get(col_name, (None, None))
            columns.append({
                "name": col_name,
                "type": fe_type,
                "db_type": row[1],
                "nullable": row[2] == "YES",
                # ⭐ Distinto da `default`: quello e' None anche quando il default
                # ESISTE ma non e' un literal (`now()`, `nextval(...)`). Qui si
                # dice se il DB riempie la colonna da solo — e allora un NOT NULL
                # non e' un campo obbligatorio per l'operatore (niente `*`, dal
                # 2026-09-21 il drawer lo legge).
                "has_default": row[3] is not None,
                # Default DB normalizzato (literal) per inizializzare il form di
                # creazione; None se non e' un literal riconoscibile.
                "default": _parse_column_default(row[3], fe_type),
                "is_pk": col_name == "id",
                "references": references,
                "references_column": references_column,
                "references_lookup": (
                    references in rel_lookup and references_column in LOOKUP_COLONNE_VALORE
                ),
            })

        _cache[cache_key] = columns
        return columns

    # Scopo: Restituisce tutti i nomi colonne incluso id (per SELECT).
    def get_all_column_names(self, schema: str, table: str) -> list[str]:
        return [c["name"] for c in self.get_table_columns(schema, table)]

    # Scopo: I vincoli UNIQUE / FK / CHECK della tabella, con le colonne che
    #        coinvolgono: `[{"name", "type", "columns"}]`. Servono al service
    #        per tradurre un IntegrityError nel CAMPO da correggere (le mappe di
    #        `translate_db_errors` sono per nome di vincolo, e qui i nomi si
    #        leggono dal catalogo invece di essere scritti a mano per 90 tabelle).
    def get_table_constraints(self, schema: str, table: str) -> list[dict[str, Any]]:
        cache_key = f"{schema}.{table}"
        if cache_key in _cache_vincoli:
            return _cache_vincoli[cache_key]
        with connection.cursor() as cursor:
            cursor.execute(_SQL_VINCOLI, [schema, table])
            rows = cursor.fetchall()
        vincoli = [
            {"name": r[0], "type": _TIPO_VINCOLO[r[1]], "columns": list(r[2])}
            for r in rows
        ]
        _cache_vincoli[cache_key] = vincoli
        return vincoli

    # Scopo: Invalida la cache (utile in test).
    @staticmethod
    def clear_cache() -> None:
        _cache.clear()
        _cache_vincoli.clear()
