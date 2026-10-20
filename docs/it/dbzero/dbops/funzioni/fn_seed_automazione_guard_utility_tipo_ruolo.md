{% include-markdown "it/dbzero/dbops/manual/fn_seed_automazione_guard_utility_tipo_ruolo.md" %}
# ⚙️ Funzione `fn_seed_automazione_guard_utility_tipo_ruolo`

```sql
CREATE FUNCTION fn_seed_automazione_guard_utility_tipo_ruolo(p_schemas text[])
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_seed_automazione_guard_utility_tipo_ruolo(p_schemas text[] DEFAULT NULL::text[])
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_schemas text[];
  rtab record;
  v_soggetto_ruolo_col text;
  v_non_a_catalogo text[] := ARRAY[]::text[];
BEGIN
  v_schemas := dbops.fn_resolve_scope(p_schemas);

  FOR rtab IN
    SELECT n.nspname AS schema_name,
           c.relname AS table_name
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE c.relkind = 'r'
       AND n.nspname = ANY(v_schemas)
       AND n.nspname <> 'storico'
       AND dbops.fn_table_in_scope(n.nspname, c.relname)
       AND dbops.fn_col_exists(n.nspname, c.relname, 'utility_id')
  LOOP
    SELECT att.attname
      INTO v_soggetto_ruolo_col
      FROM pg_constraint con
      JOIN unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord) ON true
      JOIN pg_attribute att
        ON att.attrelid = con.conrelid
       AND att.attnum = k.attnum
      JOIN pg_class cref ON cref.oid = con.confrelid
      JOIN pg_namespace nref ON nref.oid = cref.relnamespace
      JOIN pg_class c ON c.oid = con.conrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE con.contype = 'f'
       AND n.nspname = rtab.schema_name
       AND c.relname = rtab.table_name
       AND nref.nspname = 'anagrafiche'
       AND cref.relname = 'soggetti_ruoli'
       AND att.attname LIKE '%_soggetto_ruolo_id'
     ORDER BY
       att.attname
     LIMIT 1;

    IF v_soggetto_ruolo_col IS NULL THEN
      SELECT a.attname
        INTO v_soggetto_ruolo_col
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE n.nspname = rtab.schema_name
         AND c.relname = rtab.table_name
         AND a.attnum > 0
         AND NOT a.attisdropped
         AND a.attname LIKE '%_soggetto_ruolo_id'
       ORDER BY a.attname
       LIMIT 1;
    END IF;

    IF v_soggetto_ruolo_col IS NULL THEN
      CONTINUE;
    END IF;

    -- ⭐ QUI NON SI SCRIVE PIU' — 18-08-2026.
    --
    --   La configurazione di questa automazione e' un MIRROR DEL CSV
    --   `80_data/sql/dbops/automazione_guard_utility_tipo_ruolo.csv`, come per
    --   tutte le altre `automazione_*` di dbops. Decisione di Tid: i seed
    --   girano da CSV, e un misto di script SQL e CSV sulla stessa tabella non
    --   regge — sono due sorgenti di verita' che divergono fra sviluppo e CI,
    --   perche' il mirror e' `runOnChange` e ri-legge a ogni migrate mentre chi
    --   scrive da codice gira quando gira.
    --
    --   ⚠️ Il danno che ha fatto scrivere da qui non e' teorico. L'INSERT
    --   chiudeva con `ON CONFLICT (schema_name, table_name) DO NOTHING`: una
    --   riga scritta una volta non si raddrizzava mai piu'. La configurazione
    --   e' rimasta ferma al 2026-02-16 mentre lo schema andava avanti, e al
    --   2026-08-18 **4 righe su 7 descrivevano tabelle che nel frattempo
    --   avevano perso `utility_id` o erano state rinominate**. Rilevare dallo
    --   schema e' utile; rilevare dallo schema e *scrivere* significa che la
    --   configurazione racconta lo schema del giorno in cui l'ha vista.
    --
    --   Resta la meta' utile: la funzione dice cosa vede e non lo mette in
    --   tabella. Chi legge la diagnosi decide se aggiungere la riga al CSV —
    --   e' l'opt-in esplicito, la stessa forma di `dbops.fk_index_policy`.
    IF NOT EXISTS (
      SELECT 1
        FROM dbops.automazione_guard_utility_tipo_ruolo a
       WHERE a.schema_name = rtab.schema_name
         AND a.table_name  = rtab.table_name
    ) THEN
      v_non_a_catalogo := v_non_a_catalogo
        || (rtab.schema_name || '.' || rtab.table_name
            || ' (' || v_soggetto_ruolo_col || ')');
    END IF;
  END LOOP;

  -- ⚠️ Un NOTICE e non un errore: una tabella nuova che qualifica non e' un
  --   guasto, e' una decisione da prendere. Farla fallire bloccherebbe il
  --   `ci_apply` per una cosa che non e' rotta.
  --   ⚠️ Ed e' anche il limite di questa forma, detto: un NOTICE in mezzo
  --   all'output del `ci_apply` si legge se lo si va a cercare. La sede giusta
  --   sarebbe una vista di diagnosi accanto alle altre di `dbops`; qui si e'
  --   scelto di non aggiungerne una per non allargare il perimetro.
  IF array_length(v_non_a_catalogo, 1) IS NOT NULL THEN
    RAISE NOTICE
      'dbops.fn_seed_automazione_guard_utility_tipo_ruolo: % tabelle qualificano ma non sono nel CSV di configurazione: %. Se vanno protette, aggiungerle a 80_data/sql/dbops/automazione_guard_utility_tipo_ruolo.csv.',
      array_length(v_non_a_catalogo, 1),
      array_to_string(v_non_a_catalogo, ', ');
  END IF;
END;
$function$

COMMENT ON FUNCTION dbops.fn_seed_automazione_guard_utility_tipo_ruolo(p_schemas text[])
IS 'Popola dbops.automazione_guard_utility_tipo_ruolo autodetectando tabelle con utility_id + colonna ruolo (FK diretta o naming *_soggetto_ruolo_id). Post 18-08-2026: NON SCRIVE PIU''. La configurazione e'' un mirror del CSV 80_data/sql/dbops/automazione_guard_utility_tipo_ruolo.csv, come le altre automazione_* di dbops; questa funzione rileva soltanto e segnala con un NOTICE le tabelle che qualificano ma non sono a catalogo. Scriveva con ON CONFLICT DO NOTHING, quindi una riga scritta una volta non si raddrizzava piu'' e la configurazione e'' rimasta ferma al 2026-02-16 mentre lo schema andava avanti: al 2026-08-18, 4 righe su 7 descrivevano tabelle che avevano perso utility_id o erano state rinominate.';
```

</div>

---
{% include-markdown "signature-core.md" %}
