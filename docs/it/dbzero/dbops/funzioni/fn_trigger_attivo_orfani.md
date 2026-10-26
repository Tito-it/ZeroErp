{% include-markdown "it/dbzero/dbops/manual/fn_trigger_attivo_orfani.md" %}
# ⚙️ Funzione `fn_trigger_attivo_orfani`

```sql
CREATE FUNCTION fn_trigger_attivo_orfani()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_trigger_attivo_orfani()
 RETURNS TABLE(tabella oid, trigger_nome name, funzione name, argomenti text[], motivo text, dettaglio text)
 LANGUAGE sql
 STABLE
AS $function$
  -- Scopo: i trigger ATTIVO che nominano una tabella o una colonna
  --   che non esiste. motivo: TABELLA_ASSENTE | COLONNA_ASSENTE |
  --   ARGOMENTI_INSUFFICIENTI.
  -- Uso: SELECT * FROM dbops.fn_trigger_attivo_orfani();
  WITH trg AS (
      SELECT t.tgrelid,
             t.tgname,
             p.proname,
             dbops.fn_trigger_argomenti(t.tgargs) AS a,
             p.proname = 'trgfn_prevent_deactivate_if_children' AS is_block
        FROM pg_catalog.pg_trigger t
        JOIN pg_catalog.pg_proc p      ON p.oid = t.tgfoid
        JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
       WHERE NOT t.tgisinternal
         AND n.nspname = 'dbops'
         AND p.proname IN ('trgfn_prevent_deactivate_if_children',
                           'trgfn_child_requires_active_parent')
  ),
  letti AS (
      -- l'«altra» tabella: la figlia per il block, il padre per il require;
      -- in entrambi i casi argomenti 1 e 2.
      SELECT trg.*,
             cardinality(trg.a) >= CASE WHEN trg.is_block THEN 3 ELSE 4 END AS args_ok,
             (SELECT c.oid
                FROM pg_catalog.pg_class c
                JOIN pg_catalog.pg_namespace cn ON cn.oid = c.relnamespace
               WHERE cn.nspname = trg.a[1]
                 AND c.relname  = trg.a[2]
                 AND c.relkind IN ('r', 'p')) AS altra
        FROM trg
  ),
  colonne AS (
      -- le tre colonne che il corpo legge, ognuna con la tabella che la porta
      SELECT l.tgrelid, l.tgname,
             string_agg(format('%s.%s', COALESCE(r.rel::regclass::text, '?'), r.col), ', '
                        ORDER BY r.pos) AS mancanti
        FROM letti l
        CROSS JOIN LATERAL (VALUES
            (1, l.altra,   l.a[3]),
            (2, l.tgrelid, CASE WHEN l.is_block THEN COALESCE(l.a[4], 'id') ELSE l.a[4] END),
            (3, CASE WHEN l.is_block THEN l.tgrelid ELSE l.altra END,
                CASE WHEN l.is_block THEN COALESCE(l.a[5], 'attivo') ELSE COALESCE(l.a[5], 'id') END)
        ) AS r(pos, rel, col)
       WHERE l.args_ok
         AND l.altra IS NOT NULL
         AND NOT EXISTS (SELECT 1
                           FROM pg_catalog.pg_attribute at
                          WHERE at.attrelid = r.rel
                            AND at.attname  = r.col
                            AND at.attnum   > 0
                            AND NOT at.attisdropped)
       GROUP BY l.tgrelid, l.tgname
  )
  SELECT l.tgrelid,
         l.tgname,
         l.proname,
         l.a,
         CASE
           WHEN NOT l.args_ok        THEN 'ARGOMENTI_INSUFFICIENTI'
           WHEN l.altra IS NULL      THEN 'TABELLA_ASSENTE'
           ELSE                           'COLONNA_ASSENTE'
         END,
         CASE
           WHEN NOT l.args_ok        THEN format('%s argomenti', cardinality(l.a))
           WHEN l.altra IS NULL      THEN format('%s.%s', l.a[1], l.a[2])
           ELSE                           c.mancanti
         END
    FROM letti l
    LEFT JOIN colonne c ON c.tgrelid = l.tgrelid AND c.tgname = l.tgname
   WHERE NOT l.args_ok
      OR l.altra IS NULL
      OR c.mancanti IS NOT NULL
   ORDER BY l.tgrelid::regclass::text, l.tgname;
$function$

COMMENT ON FUNCTION dbops.fn_trigger_attivo_orfani()
IS 'I trigger ATTIVO che nominano una tabella o una colonna che non esiste piu'': il block sul padre (dbops.trgfn_prevent_deactivate_if_children: figlia = argomenti 1-2, legge figlia.arg3, padre.arg4 [id], padre.arg5 [attivo]) e il require sul figlio (dbops.trgfn_child_requires_active_parent: padre = argomenti 1-2, legge padre.arg3, figlio.arg4, padre.arg5 [id]). motivo: TABELLA_ASSENTE, COLONNA_ASSENTE (dettaglio: le colonne che mancano), ARGOMENTI_INSUFFICIENTI (errore di scrittura, non un residuo). Orfano = nome morto, NON «FK assente»: i require scritti a mano su chiavi polimorfe non hanno FK e sono legittimi. Legge pg_class/pg_attribute per nome, non information_schema, che filtra per privilegio. Lettore unico di dbops.fn_ritira_attivo_orfani e del pgTAP dbops/test-trigger-attivo-orfani-v1. Brief: brief-be-utenti-di-sviluppo §9.5 (R-1, Q-1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
