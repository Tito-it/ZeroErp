{% include-markdown "it/dbzero/config/manual/fn_pannello_colonne_scrivibili.md" %}
# ⚙️ Funzione `fn_pannello_colonne_scrivibili`

```sql
CREATE FUNCTION fn_pannello_colonne_scrivibili(p_tabella text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_pannello_colonne_scrivibili(p_tabella text)
 RETURNS text[]
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: dire quali colonne il pannello di configurazione scrive per una
--   tabella della lista (pannello = true), nell'ordine della tabella.
--   NULL se il pannello non gestisce la tabella.
DECLARE
    -- Le colonne che scrive il DB per ogni riga: il pannello non le tocca.
    c_di_sistema CONSTANT text[] := ARRAY['id', 'data_insert', 'user_insert',
                                         'data_update', 'user_update', 'tx_id',
                                         'storicizza', 'uid'];
    v_relid      oid;
    v_colonne    text[];
BEGIN
    SELECT c.oid
      INTO v_relid
      FROM config.tabelle_gestibili tg
      JOIN pg_catalog.pg_namespace n ON n.nspname = tg.schema_tabella
      JOIN pg_catalog.pg_class c     ON c.relnamespace = n.oid
                                    AND c.relname = tg.nome_tabella
                                    AND c.relkind IN ('r', 'p')
     WHERE tg.codice_interno = p_tabella
       AND tg.pannello;

    IF v_relid IS NULL THEN
        RETURN NULL;
    END IF;

    SELECT array_agg(a.attname::text ORDER BY a.attnum)
      INTO v_colonne
      FROM pg_catalog.pg_attribute a
     WHERE a.attrelid = v_relid
       AND a.attnum > 0
       AND NOT a.attisdropped
       AND a.attgenerated = ''
       AND a.attidentity <> 'a'
       AND a.attname::text <> ALL (c_di_sistema);

    RETURN COALESCE(v_colonne, ARRAY[]::text[]);
END;
$function$

COMMENT ON FUNCTION config.fn_pannello_colonne_scrivibili(p_tabella text)
IS 'Check pura: le colonne che il pannello di configurazione scrive per una tabella di config.tabelle_gestibili con pannello = true (p_tabella = codice_interno, schema.tabella), nell''ordine della tabella. Escluse le colonne che scrive il DB per ogni riga (id, audit, tx_id, storicizza, uid), le generate e le identity ALWAYS. NULL se il pannello non gestisce la tabella (fuori lista, pannello = false, inesistente): a sollevare e'' il verbo. Sede unica della regola: la chiama config.fn_pannello_scrivi (passo 2) e la legge il metadata del backend per i campi del form. STABLE, INVOKER. Brief: brief-db-pannello-config-verbo-generico, sezione 6.';
```

</div>

---
{% include-markdown "signature-core.md" %}
