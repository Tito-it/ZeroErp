{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_billing_account_guard_admin_globale.md" %}
# ⚙️ Funzione `trgfn_billing_account_guard_admin_globale`

```sql
CREATE FUNCTION trgfn_billing_account_guard_admin_globale()
```

**Definizione completa:**

<div data-search-exclude markdown>

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

    -- La regola sta in fn_check_user_can_create_ba (rev 2026-08-04):
    -- serve un emittente su cui scrivere, cioe' una riga in
    -- user_emittenti_fiscali oppure app.current_emittente_id valido
    -- per l'utente; senza, passa solo un'istanza a zero emittenti attivi.
    v_can_create := script.fn_check_user_can_create_ba(v_user_id);

    IF v_can_create IS NOT TRUE THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_BA_ADMIN_GLOBALE_VIETATO',
            jsonb_build_object(
                'detail', 'Nessun emittente fiscale su cui scrivere (ne'' riga in user_emittenti_fiscali ne'' app.current_emittente_id valido) ed esistono emittenti attivi: billing account non creabile',
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
IS 'Guard BEFORE INSERT su billing_account: rifiuta la creazione quando l''utente non ha un emittente fiscale su cui scrivere, cioe'' ne'' una riga in config.user_emittenti_fiscali ne'' un app.current_emittente_id valido per lui (tipicamente il super admin in «Tutti gli emittenti»), ed esistono emittenti fiscali attivi. La regola e'' delegata a script.fn_check_user_can_create_ba (rev 2026-08-04). Skip se GUC app.current_user_id non impostato (seed/bootstrap). Solleva E_BA_ADMIN_GLOBALE_VIETATO (il nome del codice resta per compatibilita'').';
```

</div>

---
{% include-markdown "signature-core.md" %}
