# ⚙️ Funzione `trgfn_a10_v_contratti_protect_num`

```sql
CREATE FUNCTION trgfn_a10_v_contratti_protect_num()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_a10_v_contratti_protect_num()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_codice_stato text;
BEGIN
  SELECT s.codice_interno
    INTO v_codice_stato
    FROM config.stati_doc_contratti s
   WHERE s.id = OLD.stato_doc_contratti_id;

  -- dopo CONSEGNATO/RESO/ANNULLATO blocco numerazione/data (adatta la lista se ti serve SPEDITO)
  IF v_codice_stato <> 'DRAFT' THEN
    IF NEW.numero_contratto IS DISTINCT FROM OLD.numero_contratto
       OR NEW.data  IS DISTINCT FROM OLD.data THEN
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_NUMERAZIONE_IMMUTABILE',
        jsonb_build_object('contratti_id', OLD.id, 'stato', v_codice_stato),
        NULL::uuid, 'vendite.contratti' , OLD.id::text
      );
    END IF;
  END IF;
  RETURN NEW;
END$function$
```

---
{% include-markdown "signature-core.md" %}
