# ⚙️ Funzione `trgfn_ordini_v_protect_num`

```sql
CREATE FUNCTION trgfn_ordini_v_protect_num()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ordini_v_protect_num()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_codice text;
BEGIN
  -- recupera il codice dello stato corrente (OLD)
  SELECT s.codice INTO v_codice
    FROM config.stati_doc_ordini s
   WHERE s.id = OLD.stato_doc_ordine_id;

  IF v_codice NOT IN ('DRAFT','') THEN
    IF NEW.numero IS DISTINCT FROM OLD.numero
       OR NEW.serie  IS DISTINCT FROM OLD.serie
       OR NEW.anno   IS DISTINCT FROM OLD.anno
       OR NEW.data   IS DISTINCT FROM OLD.data THEN
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_NUMERAZIONE_IMMUTABILE',
        jsonb_build_object('id', OLD.id, 'stato', v_codice),
        NULL::uuid,'vendite.ordini' , OLD.id::text
      );
    END IF;
  END IF;

  RETURN NEW;
END
$function$
```

---
{% include-markdown "signature-core.md" %}
