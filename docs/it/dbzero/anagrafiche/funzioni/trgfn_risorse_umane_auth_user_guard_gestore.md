# ⚙️ Funzione `trgfn_risorse_umane_auth_user_guard_gestore`

```sql
CREATE FUNCTION trgfn_risorse_umane_auth_user_guard_gestore()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_risorse_umane_auth_user_guard_gestore()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_soggetto_id uuid;
  v_is_gestore boolean;
BEGIN
  SELECT ru.soggetto_id
    INTO v_soggetto_id
    FROM anagrafiche.risorse_umane ru
   WHERE ru.id = NEW.risorsa_umana_id;

  SELECT EXISTS (
    SELECT 1
      FROM anagrafiche.gestori g
      JOIN anagrafiche.soggetti_ruoli sr
        ON sr.id = g.soggetto_ruolo_id
     WHERE sr.soggetto_id = v_soggetto_id
  )
  INTO v_is_gestore;

  IF NOT v_is_gestore THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_RISORSA_UMANA_AUTH_USER_NON_GESTORE',
      jsonb_build_object(
        'table', TG_TABLE_NAME,
        'risorsa_umana_id', NEW.risorsa_umana_id,
        'soggetto_id', v_soggetto_id
      ),
      NULL::uuid,
      NEW.risorsa_umana_id::text
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_risorse_umane_auth_user_guard_gestore()
IS 'Consente il collegamento auth_user solo per risorse del gestore.';
```

---
{% include-markdown "signature-core.md" %}
