{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_gen_codice.md" %}
# ⚙️ Funzione `trgfn_ddt_gen_codice`

```sql
CREATE FUNCTION trgfn_ddt_gen_codice()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_gen_codice()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_stato_codice config.stati_doc_ddt.codice_interno%TYPE;
BEGIN
    IF (NEW.numero IS NULL OR btrim(NEW.numero::text) = '') THEN
        SELECT sdd.codice_interno INTO v_stato_codice
          FROM config.stati_doc_ddt sdd
         WHERE sdd.id = NEW.stato_doc_ddt_id;
        IF v_stato_codice = 'EMESSO' THEN
            NEW.numero := script.fn_generate_codice('ddt');
        END IF;
    END IF;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_gen_codice()
IS 'Genera ddt.numero solo alla transizione a EMESSO (no buchi fiscali da bozze DRAFT scartate). In DRAFT numero resta NULL. Immutabilita'' post-assegnazione: trgfn_v_ddt_protect_num. C6, rev 2026-07-09.';
```

---
{% include-markdown "signature-core.md" %}
