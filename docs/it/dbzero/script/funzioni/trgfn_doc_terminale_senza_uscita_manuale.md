# ⚙️ Funzione `trgfn_doc_terminale_senza_uscita_manuale`

```sql
CREATE FUNCTION trgfn_doc_terminale_senza_uscita_manuale()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_doc_terminale_senza_uscita_manuale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- La testata del montaggio (TG_ARGV[0]): regclass, nessuna
    -- colonna a cui ancorarla.
    v_testata regclass;
    v_stato   text;   -- codice_interno di uno di sette vocabolari
    v_uscita  text;   -- idem
BEGIN
    -- =========================================================
    -- Scopo: da uno stato terminale non esce nessun passaggio a
    --   mano (S-1, lettura A). Giudica la configurazione intera
    --   della testata, non la sola riga: una riga di matrice e
    --   la colonna terminale del vocabolario sono due meta' della
    --   stessa regola.
    -- Montaggio: CONSTRAINT TRIGGER differito, per riga, con un
    --   argomento, la testata (script.fn_doc_stato_modello).
    -- =========================================================
    IF TG_NARGS <> 1 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('trigger', TG_NAME,
                               'table',   TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'tg_argv', TG_ARGV),
            NULL::uuid,
            TG_NAME::text,
            'un argomento: la testata del documento (script.fn_doc_stato_modello)');
    END IF;
    v_testata := TG_ARGV[0]::regclass;

    SELECT x.stato, x.uscita
      INTO v_stato, v_uscita
      FROM script.fn_doc_terminali_con_uscita_manuale(v_testata) AS x
     LIMIT 1;

    IF v_stato IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.trgfn_doc_terminale_senza_uscita_manuale',
            'E_DOC_TERMINALE_CON_USCITA_MANUALE',
            jsonb_build_object('testata', v_testata::text,
                               'table',   TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'stato',   v_stato,
                               'uscita',  v_uscita),
            NULL::uuid,
            v_stato,
            v_uscita,
            v_testata::text);
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION script.trgfn_doc_terminale_senza_uscita_manuale()
IS 'Building block: da uno stato terminale non esce nessun passaggio a mano. Trigger differito (CONSTRAINT TRIGGER DEFERRABLE INITIALLY DEFERRED, per riga) montato sui vocabolari degli stati che hanno la colonna terminale e sulle loro matrici, con un argomento: la testata del documento (script.fn_doc_stato_modello). Giudica la configurazione intera della testata con script.fn_doc_terminali_con_uscita_manuale, a transazione completa, cosi'' vocabolario e matrice si scrivono in qualunque ordine; alla prima coppia (stato terminale, destinazione a mano) solleva E_DOC_TERMINALE_CON_USCITA_MANUALE. Lo incontra solo chi scrive la configurazione. Un montaggio senza l''argomento solleva E_SCRIPT_CHIAMATA_NON_VALIDA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
