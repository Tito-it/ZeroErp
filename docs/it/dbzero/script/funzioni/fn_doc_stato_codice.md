{% include-markdown "it/dbzero/script/manual/fn_doc_stato_codice.md" %}
# ⚙️ Funzione `fn_doc_stato_codice`

```sql
CREATE FUNCTION fn_doc_stato_codice(p_testata regclass, p_stato_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_doc_stato_codice(p_testata regclass, p_stato_id bigint)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- Il vocabolario di una qualunque testata della mappa: nessuna
    -- colonna comune a cui ancorare il tipo del codice.
    v_vocabolario regclass;
    v_codice      text;
BEGIN
    -- =========================================================
    -- Scopo: il codice_interno dello stato con quell'id nel
    --   vocabolario della testata. NULL: id NULL o che il
    --   vocabolario non ha (decide il chiamante).
    -- =========================================================
    SELECT m.vocabolario
      INTO v_vocabolario
      FROM script.fn_doc_stato_modello(p_testata) m;

    IF v_vocabolario IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_doc_stato_codice', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('testata', p_testata::text),
            NULL::uuid,
            'script.fn_doc_stato_codice',
            'p_testata: una testata della mappa del modello (script.fn_doc_stato_modello)');
    END IF;

    EXECUTE format(
        'SELECT s.codice_interno::text FROM %s s WHERE s.id = $1',
        v_vocabolario)
       INTO v_codice
      USING p_stato_id;

    RETURN v_codice;
END;
$function$

COMMENT ON FUNCTION script.fn_doc_stato_codice(p_testata regclass, p_stato_id bigint)
IS 'BB del modello del documento: il codice_interno (la chiave stabile del vocabolario) dello stato con quell''id nel vocabolario degli stati di una testata, letto dalla mappa script.fn_doc_stato_modello. Gemello inverso di script.fn_doc_stato_id: la traduzione id <-> codice sta in questa coppia. NULL se l''id e'' NULL o il vocabolario non lo ha: decide il chiamante. Nessun filtro sugli attivi: uno stato spento come destinazione lo rifiuta il verbo (U-3). Testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA. Consumatore: il backend, che compone fn_doc_stato_codice(t, script.fn_stato_emissione_id(t)) per lo stato chiesto da «Emetti». Brief: brief-modello-documento-vendita §8.11 (V-1 di Tid, 2026-10-25).';
```

</div>

---
{% include-markdown "signature-core.md" %}
