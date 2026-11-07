{% include-markdown "it/dbzero/dbops/manual/fn_foreign_keys_info.md" %}
# ⚙️ Funzione `fn_foreign_keys_info`

```sql
CREATE FUNCTION fn_foreign_keys_info(p_tabella regclass)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_foreign_keys_info(p_tabella regclass)
 RETURNS TABLE(relazione text, constraint_name name, posizione bigint, source_table regclass, source_column name, target_table regclass, target_column name)
 LANGUAGE sql
 STABLE
AS $function$
  -- Scopo: le FK entranti e uscenti di una tabella, una riga per
  --   colonna della chiave.
  -- Uso: SELECT * FROM dbops.fn_foreign_keys_info('vendite.fatture');
  WITH fk AS (
      SELECT c.conname,
             c.conrelid,
             c.confrelid,
             k.n,
             ac.attname AS source_column,
             af.attname AS target_column,
             -- un clone di partizione che ripete il vincolo padre dallo stesso lato
             (pc.oid IS NOT NULL AND pc.conrelid  = c.conrelid)  AS clone_uscente,
             (pc.oid IS NOT NULL AND pc.confrelid = c.confrelid) AS clone_entrante
        FROM pg_catalog.pg_constraint c
       CROSS JOIN LATERAL unnest(c.conkey, c.confkey) WITH ORDINALITY AS k(num_figlia, num_padre, n)
        JOIN pg_catalog.pg_attribute ac
          ON ac.attrelid = c.conrelid  AND ac.attnum = k.num_figlia
        JOIN pg_catalog.pg_attribute af
          ON af.attrelid = c.confrelid AND af.attnum = k.num_padre
        LEFT JOIN pg_catalog.pg_constraint pc
          ON pc.oid = c.conparentid
       WHERE c.contype = 'f'
         AND (c.conrelid = p_tabella OR c.confrelid = p_tabella)
  )
  SELECT 'incoming'::text, fk.conname, fk.n,
         fk.conrelid::regclass, fk.source_column,
         fk.confrelid::regclass, fk.target_column
    FROM fk
   WHERE fk.confrelid = p_tabella
     AND NOT fk.clone_entrante
  UNION ALL
  SELECT 'outgoing'::text, fk.conname, fk.n,
         fk.conrelid::regclass, fk.source_column,
         fk.confrelid::regclass, fk.target_column
    FROM fk
   WHERE fk.conrelid = p_tabella
     AND NOT fk.clone_uscente
   ORDER BY 1, 4, 2, 3;
$function$

COMMENT ON FUNCTION dbops.fn_foreign_keys_info(p_tabella regclass)
IS 'Le FK di una tabella: entranti (relazione incoming: un''altra tabella punta a questa) e uscenti (outgoing: questa punta a un''altra), una riga per colonna della chiave con la sua posizione, la colonna della figlia accoppiata alla colonna del padre nello stesso posto (unnest di conkey e confkey WITH ORDINALITY: una FK composita non si moltiplica). La tabella si passa come regclass, schema compreso, e le tabelle del risultato sono regclass. Legge pg_constraint, non information_schema: la risposta non dipende dai privilegi di chi chiama. Su una tabella partizionata un clone della FK che ripete dallo stesso lato il vincolo dichiarato non si mostra; una partizione vede le FK che la vincolano. Strumento DBA; la chiama dbops.fn_find_file_usage per le sole entranti.';
```

</div>

---
{% include-markdown "signature-core.md" %}
