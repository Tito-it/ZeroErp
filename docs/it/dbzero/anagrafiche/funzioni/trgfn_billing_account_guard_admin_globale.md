{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_billing_account_guard_admin_globale.md" %}
# ⚙️ Funzione `trgfn_billing_account_guard_admin_globale`

```sql
CREATE FUNCTION trgfn_billing_account_guard_admin_globale()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_billing_account_guard_admin_globale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_user_id integer;
    v_can_create boolean;
BEGIN
    -- Lettura GUC app.current_user_id (settato dal middleware Django).
    -- Il secondo parametro 'true' di current_setting evita errore se
    -- il GUC non e' definito (ritorna NULL).
    BEGIN
        v_user_id := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    EXCEPTION WHEN OTHERS THEN
        v_user_id := NULL;
    END;

    -- Bootstrap / seed / job senza utente: non bloccare.
    -- Le INSERT applicative passano sempre da middleware quindi
    -- il GUC c'e'. L'unico scenario senza GUC sono i seed di
    -- migrazione e le manutenzioni manuali.
    IF v_user_id IS NULL THEN
        RETURN NEW;
    END IF;

    v_can_create := script.fn_check_user_can_create_ba(v_user_id);

    IF v_can_create IS NOT TRUE THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_BA_ADMIN_GLOBALE_VIETATO',
            jsonb_build_object(
                'detail', 'Admin globale non puo'' creare billing account quando esistono emittenti fiscali',
                'auth_user_id', v_user_id,
                'codice_ba', NEW.codice
            ),
            NULL::uuid,
            coalesce(NEW.codice, '')
        );
    END IF;

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_billing_account_guard_admin_globale()
IS 'Guard BEFORE INSERT su billing_account: vieta agli admin globali (utenti senza riga in user_emittenti_fiscali) di creare BA quando esistono emittenti fiscali attivi. Skip se GUC app.current_user_id non impostato (seed/bootstrap). Solleva E_BA_ADMIN_GLOBALE_VIETATO.';
```

---
{% include-markdown "signature-core.md" %}
