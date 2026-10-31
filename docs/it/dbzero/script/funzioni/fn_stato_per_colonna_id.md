{% include-markdown "it/dbzero/script/manual/fn_stato_per_colonna_id.md" %}
# ⚙️ Funzione `fn_stato_per_colonna_id`

```sql
CREATE FUNCTION fn_stato_per_colonna_id(p_testata regclass, p_colonna name, p_lettore text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_stato_per_colonna_id(p_testata regclass, p_colonna name, p_lettore text DEFAULT NULL::text)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- Il vocabolario, il tipo della colonna e l'id di uno stato
    -- di una qualunque testata della mappa: bigint in tutti,
    -- nessuna colonna comune a cui ancorarli.
    v_vocabolario regclass;
    v_tipo        regtype;
    v_id          bigint;
    -- La funzione che il messaggio nomina: la porta, o questa.
    v_lettore     text := COALESCE(p_lettore, 'script.fn_stato_per_colonna_id');
BEGIN
    -- =========================================================
    -- Scopo: l'id dello stato che la colonna p_colonna (boolean)
    --   marca nel vocabolario della testata. Vedi l'intestazione
    --   del changeSet.
    -- =========================================================
    SELECT m.vocabolario
      INTO v_vocabolario
      FROM script.fn_doc_stato_modello(p_testata) m;

    IF v_vocabolario IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_stato_per_colonna_id', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('testata', p_testata::text),
            NULL::uuid,
            v_lettore,
            'p_testata: una testata della mappa del modello (script.fn_doc_stato_modello)');
    END IF;

    SELECT a.atttypid::regtype
      INTO v_tipo
      FROM pg_catalog.pg_attribute a
     WHERE a.attrelid = v_vocabolario
       AND a.attname  = p_colonna
       AND a.attnum   > 0
       AND NOT a.attisdropped;

    -- Il vocabolario non ha la colonna: il documento non ha
    -- quello stato.
    IF v_tipo IS NULL THEN
        RETURN NULL;
    END IF;

    IF v_tipo <> 'boolean'::regtype THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_stato_per_colonna_id', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('testata', p_testata::text, 'colonna', p_colonna, 'tipo', v_tipo::text),
            NULL::uuid,
            v_lettore,
            'p_colonna: una colonna boolean del vocabolario che marca uno stato');
    END IF;

    EXECUTE format('SELECT s.id FROM %s s WHERE s.%I', v_vocabolario, p_colonna)
       INTO v_id;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION script.fn_stato_per_colonna_id(p_testata regclass, p_colonna name, p_lettore text)
IS 'BB del modello del documento: l''id dello stato che una colonna boolean del vocabolario degli stati di una testata MARCA (al massimo uno: indice unico parziale e CHECK «attivo» su ogni colonna; la mappa e'' script.fn_doc_stato_modello). NULL se il vocabolario non ha la colonna (il documento non ha quello stato) o se non marca nessuno stato; testata fuori mappa o colonna non boolean: E_SCRIPT_CHIAMATA_NON_VALIDA, che nomina p_lettore (la porta che chiama) o, senza, questa funzione. ⛔ Non si chiama dai consumatori: e'' la logica comune dei lettori con il nome, che restano la porta (script.fn_stato_emissione_id, script.fn_stato_abortito_id, script.fn_stato_cessazione_id, script.fn_stato_accettazione_id). Brief: brief-modello-documento-vendita §17 (regola del 2, Tid 2026-10-31).';
```

</div>

---
{% include-markdown "signature-core.md" %}
