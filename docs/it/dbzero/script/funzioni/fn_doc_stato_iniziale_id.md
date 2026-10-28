{% include-markdown "it/dbzero/script/manual/fn_doc_stato_iniziale_id.md" %}
# ⚙️ Funzione `fn_doc_stato_iniziale_id`

```sql
CREATE FUNCTION fn_doc_stato_iniziale_id(p_testata regclass)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_doc_stato_iniziale_id(p_testata regclass)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- Il vocabolario di una qualunque testata della mappa:
    -- nessuna colonna comune a cui ancorarlo.
    v_vocabolario regclass;
BEGIN
    -- =========================================================
    -- Scopo: l'id dello stato iniziale della testata, dal suo
    --   vocabolario.
    -- Regole:
    --   - testata fuori mappa: il chiamante e' rotto,
    --     E_SCRIPT_CHIAMATA_NON_VALIDA;
    --   - lo stato iniziale lo dice script.fn_stato_iniziale_id
    --     (NULL se il vocabolario non ne dichiara).
    -- =========================================================
    SELECT m.vocabolario
      INTO v_vocabolario
      FROM script.fn_doc_stato_modello(p_testata) m;

    IF v_vocabolario IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_doc_stato_iniziale_id', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('testata', p_testata::text),
            NULL::uuid,
            'script.fn_doc_stato_iniziale_id',
            'p_testata: una testata della mappa del modello (script.fn_doc_stato_modello)');
    END IF;

    RETURN script.fn_stato_iniziale_id(v_vocabolario);
END;
$function$

COMMENT ON FUNCTION script.fn_doc_stato_iniziale_id(p_testata regclass)
IS 'BB del modello del documento: l''id dello stato INIZIALE di una testata, letto dal suo vocabolario degli stati (la mappa e'' script.fn_doc_stato_modello; la regola, colonna iniziale = true, e'' script.fn_stato_iniziale_id, a cui delega). Unica sede da cui lo legge chi ha in mano una testata: nessuno scrive ''DRAFT'' per dire «lo stato in cui si nasce», ne'' il vocabolario che corrisponde alla testata. NULL se il vocabolario non lo dichiara; testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA. Non e'' un overload di script.fn_stato_iniziale_id (stesso tipo d''argomento): quella resta per chi ha il vocabolario e non una testata della mappa (il trigger della nascita, le righe dell''ordine). Gemello di script.fn_stato_emissione_id e script.fn_stato_abortito_id. Consumatori: il backend («riporta in bozza» del lotto, lo stato di arrivo per la riga del passaggio), i builder pgTAP dbops.fn_pgtap_crea_preventivo, _preventivo_con_righe, _ordine, _ordine_con_righe, _ddt_da_ordine, _ddt_senza_ordine, _ddt_riconsegna, _commessa, _fattura. Brief: brief-modello-documento-vendita §15.13 (Tid 2026-10-27).';
```

</div>

---
{% include-markdown "signature-core.md" %}
