{% include-markdown "it/dbzero/script/manual/fn_doc_stato_id.md" %}
# ⚙️ Funzione `fn_doc_stato_id`

```sql
CREATE FUNCTION fn_doc_stato_id(p_testata regclass, p_codice text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_doc_stato_id(p_testata regclass, p_codice text)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- Il vocabolario e l'id di uno stato di una qualunque testata
    -- della mappa: bigint in tutti, nessuna colonna comune a cui
    -- ancorarli.
    v_vocabolario regclass;
    v_id          bigint;
BEGIN
    -- =========================================================
    -- Scopo: l'id dello stato attivo con quel codice_interno nel
    --   vocabolario della testata. NULL: nessuno stato attivo con
    --   quel codice (decide il chiamante).
    -- =========================================================
    SELECT m.vocabolario
      INTO v_vocabolario
      FROM script.fn_doc_stato_modello(p_testata) m;

    IF v_vocabolario IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_doc_stato_id', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('testata', p_testata::text),
            NULL::uuid,
            'script.fn_doc_stato_id',
            'p_testata: una testata della mappa del modello (script.fn_doc_stato_modello)');
    END IF;

    EXECUTE format(
        'SELECT s.id FROM %s s WHERE s.codice_interno = $1 AND s.attivo IS TRUE',
        v_vocabolario)
       INTO v_id
      USING p_codice;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION script.fn_doc_stato_id(p_testata regclass, p_codice text)
IS 'BB del modello del documento: l''id dello stato ATTIVO con quel codice_interno (la chiave stabile del vocabolario) nel vocabolario degli stati di una testata, letto dalla mappa script.fn_doc_stato_modello. NULL se nessuno stato attivo ha quel codice: uno stato spento non e'' una destinazione (U-3), e l''errore lo decide il chiamante. Testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA. Sede unica della traduzione codice -> id: la leggono i verbi di stato (vendite.fn_cambia_stato_preventivo, vendite.fn_cambia_stato_ddt), la domanda intera script.fn_doc_azione_passaggio, la fixture dbops.fn_pgtap_porta_a_stato e il backend. Gemello inverso (id -> codice): script.fn_doc_stato_codice. Brief: brief-modello-documento-vendita §8 e §8.11 (Tid 2026-10-25).';
```

</div>

---
{% include-markdown "signature-core.md" %}
