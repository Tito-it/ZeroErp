{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_billing_account_guard_admin_globale.md" %}
# ⚙️ Funzione `trgfn_billing_account_guard_admin_globale`

```sql
CREATE FUNCTION trgfn_billing_account_guard_admin_globale()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_billing_account_guard_admin_globale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_user_id config.user_override_aree.auth_user_id%TYPE;
    -- l'esito di script.fn_check_user_can_create_ba: nessuna colonna dietro
    v_can_create boolean;
BEGIN
    -- Lettura GUC app.current_user_id (settato dal middleware Django).
    -- Il secondo parametro 'true' di current_setting evita errore se
    -- il GUC non e' definito (ritorna NULL).
    -- ⛔ Nessun blocco EXCEPTION: un app.current_user_id che non e' l'id di
    --   un utente lo rifiuta script.fn_utente_di_sessione, e il rifiuto sale.
    --   Ingoiato, l'utente illeggibile diventava «nessun utente» e la riga
    --   passava senza il controllo.
    v_user_id := script.fn_utente_di_sessione('anagrafiche.trgfn_billing_account_guard_admin_globale');

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
IS 'Guard BEFORE INSERT di anagrafiche.billing_account: rifiuta la creazione quando l''utente di sessione non ha un''azienda su cui scrivere (ne'' una riga in config.user_emittenti_fiscali ne'' un app.current_emittente_id valido per lui, tipicamente il super admin in «Tutti gli emittenti») ed esistono emittenti fiscali attivi: E_BA_ADMIN_GLOBALE_VIETATO. La regola e'' script.fn_check_user_can_create_ba. Senza utente di sessione (seed, manutenzione) tace; un app.current_user_id che non e'' l''id di un utente lo rifiuta script.fn_utente_di_sessione (E_SCRIPT_CHIAMATA_NON_VALIDA), e il rifiuto sale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
