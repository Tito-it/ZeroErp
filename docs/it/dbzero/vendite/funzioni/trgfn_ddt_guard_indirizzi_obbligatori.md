# ⚙️ Funzione `trgfn_ddt_guard_indirizzi_obbligatori`

```sql
CREATE FUNCTION trgfn_ddt_guard_indirizzi_obbligatori()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_guard_indirizzi_obbligatori()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: bloccare l'emissione (EMESSO) di un DDT privo degli
--   indirizzi marcati obbligatori per l'ambito DDT.
DECLARE
    v_stato_codice config.stati_doc_ddt.codice_interno%TYPE;
    v_presenti     integer[];
    v_mancanti     text[];
BEGIN
    SELECT sdd.codice_interno INTO v_stato_codice
      FROM config.stati_doc_ddt sdd
     WHERE sdd.id = NEW.stato_doc_ddt_id;

    IF v_stato_codice IS DISTINCT FROM 'EMESSO' THEN
        RETURN NEW;
    END IF;

    -- Tipi indirizzo gia' presenti sulla testata DDT.
    SELECT array_agg(di.tipo_indirizzo_id) INTO v_presenti
      FROM vendite.ddt_indirizzi di
     WHERE di.ddt_id = NEW.id;

    v_mancanti := script.fn_indirizzi_obbligatori_mancanti('DDT', v_presenti);

    IF array_length(v_mancanti, 1) IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_INDIRIZZO_DOC_OBBLIGATORIO',
            jsonb_build_object(
                'ddt_id',   NEW.id,
                'numero',   NEW.numero,
                'ambito',   'DDT',
                'mancanti', v_mancanti),
            NEW.tx_id,
            'DDT',
            NEW.id::text,
            array_to_string(v_mancanti, ', ')
        );
    END IF;

    RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
