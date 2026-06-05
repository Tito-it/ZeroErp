{% include-markdown "it/dbzero/vendite/manual/trgfn_ordini_ricalcola_totali.md" %}
# ⚙️ Funzione `trgfn_ordini_ricalcola_totali`

```sql
CREATE FUNCTION trgfn_ordini_ricalcola_totali()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ordini_ricalcola_totali()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ordine_id vendite.ordini.id%TYPE;
BEGIN
    IF NEW.emittente_fiscale_id IS DISTINCT FROM OLD.emittente_fiscale_id THEN
        v_ordine_id := NEW.id;
        PERFORM vendite.fn_ricalcola_totali_ordine(v_ordine_id);
    END IF;

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_ordini_ricalcola_totali()
IS 'Trigger function _z90_: ricalcola i totali ordine dopo cambio di ordini.emittente_fiscale_id, campo che puo'' cambiare l''aliquota effettiva via config.fn_get_aliquota_iva.';
```

---
{% include-markdown "signature-core.md" %}
