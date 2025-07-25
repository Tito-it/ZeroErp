{% include-markdown "it/dbzero/config/manual/trgfn_toponomastica_upd_non_permesso.md" %}
# ⚙️ Funzione `trgfn_toponomastica_upd_non_permesso`

```sql
CREATE FUNCTION trgfn_toponomastica_upd_non_permesso()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.trgfn_toponomastica_upd_non_permesso()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Se il record non è usato in config.stradario_generale, lascio passare
  IF NOT EXISTS (
    SELECT 1
      FROM config.stradario_generale
     WHERE  toponomastica_id = OLD.id
  ) THEN
    RETURN NEW;
  END IF;

  -- Se siamo qui, il record è in uso: controllo ciascuna colonna
  IF OLD.descrizione IS DISTINCT FROM NEW.descrizione THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_COLONNA_NON_MODIFICABILE',
      jsonb_build_object('column','descrizione','id',OLD.id),
       NULL::uuid,
      'descrizione'
    );
  END IF;
  RETURN NEW;
END;
$function$
```
---
{% include-markdown "signature-core.md" %}
