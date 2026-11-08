{% include-markdown "it/dbzero/dbops/manual/fn_trigger_attivo_argomenti.md" %}
# ⚙️ Funzione `fn_trigger_attivo_argomenti`

```sql
CREATE FUNCTION fn_trigger_attivo_argomenti(p_funzione name, p_argomenti text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_trigger_attivo_argomenti(p_funzione name, p_argomenti text[])
 RETURNS TABLE(valido boolean, dettaglio text, figlia_schema name, figlia_tabella name, padre_schema name, padre_tabella name, fk_col name, ref_col name, stato_col name, esenzione_col name)
 LANGUAGE plpgsql
 IMMUTABLE PARALLEL SAFE
AS $function$
-- Scopo: gli argomenti di un trigger ATTIVO letti per nome.
--   Una riga sola; valido = false con il motivo in dettaglio e
--   i campi a NULL se il montaggio non rispetta la grammatica.
-- Uso: SELECT * FROM dbops.fn_trigger_attivo_argomenti(
--        'trgfn_child_requires_active_parent', TG_ARGV);
-- ⚠️ PL/pgSQL e non SQL: una funzione SQL si espande dentro chi la chiama, e
--   la rinumerazione dell'array si ripeteva per ogni colonna letta (circa 2 ms
--   a trigger). Qui si calcola una volta per chiamata.
DECLARE
    -- la base dell'array non e' sempre 1 (TG_ARGV parte da 0): una fetta
    -- dell'array riparte da 1
    a        text[] := p_argomenti[array_lower(p_argomenti, 1):array_upper(p_argomenti, 1)];
    is_block boolean := p_funzione = 'trgfn_prevent_deactivate_if_children';
    minimo   integer;
    massimo  integer;
    errore   text;
BEGIN
    minimo := CASE p_funzione
                  WHEN 'trgfn_prevent_deactivate_if_children'     THEN 5
                  WHEN 'trgfn_child_requires_active_parent'       THEN 5
                  WHEN 'trgfn_child_requires_non_obsolete_parent' THEN 5
              END;
    massimo := CASE p_funzione
                  WHEN 'trgfn_prevent_deactivate_if_children'     THEN 5
                  WHEN 'trgfn_child_requires_active_parent'       THEN 5
                  WHEN 'trgfn_child_requires_non_obsolete_parent' THEN 6
               END;

    IF a IS NULL THEN
        a := ARRAY[]::text[];
    END IF;

    errore := CASE
                WHEN minimo IS NULL THEN
                  format('%s non e'' una funzione trigger ATTIVO', p_funzione)
                WHEN cardinality(a) NOT BETWEEN minimo AND massimo THEN
                  format('%s argomenti, attesi %s', cardinality(a),
                         CASE WHEN minimo = massimo THEN minimo::text
                              ELSE format('%s o %s', minimo, massimo) END)
                WHEN EXISTS (SELECT 1 FROM unnest(a) AS x
                              WHERE NULLIF(btrim(x), '') IS NULL) THEN
                  'un argomento e'' vuoto'
              END;

    valido        := errore IS NULL;
    dettaglio     := errore;
    figlia_schema := CASE WHEN errore IS NULL AND is_block     THEN a[1] END;
    figlia_tabella:= CASE WHEN errore IS NULL AND is_block     THEN a[2] END;
    padre_schema  := CASE WHEN errore IS NULL AND NOT is_block THEN a[1] END;
    padre_tabella := CASE WHEN errore IS NULL AND NOT is_block THEN a[2] END;
    fk_col        := CASE WHEN errore IS NULL THEN CASE WHEN is_block THEN a[3] ELSE a[4] END END;
    ref_col       := CASE WHEN errore IS NULL THEN CASE WHEN is_block THEN a[4] ELSE a[5] END END;
    stato_col     := CASE WHEN errore IS NULL THEN CASE WHEN is_block THEN a[5] ELSE a[3] END END;
    esenzione_col := CASE WHEN errore IS NULL AND NOT is_block THEN a[6] END;
    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION dbops.fn_trigger_attivo_argomenti(p_funzione name, p_argomenti text[])
IS 'La grammatica degli argomenti dei trigger ATTIVO, letta per nome: una riga con valido, dettaglio (il motivo, se non valido) e i campi figlia_schema, figlia_tabella, padre_schema, padre_tabella, fk_col, ref_col, stato_col, esenzione_col. Block (dbops.trgfn_prevent_deactivate_if_children, sul padre): figlia_schema, figlia_tabella, fk_col, ref_col, stato_col = attivo del padre. Require (dbops.trgfn_child_requires_active_parent, sulla figlia): padre_schema, padre_tabella, stato_col = attivo del padre, fk_col, ref_col. Require non obsoleto (dbops.trgfn_child_requires_non_obsolete_parent): come il require, stato_col = obsoleto_dal del padre, e un sesto facoltativo, esenzione_col. Tutti gli altri argomenti sono obbligatori e non vuoti: nessun ripiego. Accetta TG_ARGV (base 0) e l''array di dbops.fn_trigger_argomenti (base 1): rinumera prima di leggere. Non solleva: con un montaggio fuori grammatica i campi sono NULL e il chiamante sceglie il codice. La leggono le tre funzioni trigger, i building block dbops.fn_trigger_padre_stato e dbops.fn_trigger_figlie_presenti, dbops.fn_trigger_attivo_orfani e dbops.fn_ritira_attivo_eccezioni.';
```

</div>

---
{% include-markdown "signature-core.md" %}
