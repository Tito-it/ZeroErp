{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_entra_come_super_admin.md" %}
# ⚙️ Funzione `fn_pgtap_entra_come_super_admin`

```sql
CREATE FUNCTION fn_pgtap_entra_come_super_admin(p_etichetta text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_entra_come_super_admin(p_etichetta text DEFAULT 'super-admin'::text)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
-- Scopo: in un pgTAP, entrare nel contesto di un SUPER_ADMIN di fixture per
--   chiamare un verbo che lo chiede. Restituisce il contesto di prima.
-- Uso:
--   v_prima := dbops.fn_pgtap_entra_come_super_admin('mio-test');
--   BEGIN
--       ... il verbo ...
--   EXCEPTION WHEN OTHERS THEN
--       PERFORM dbops.fn_pgtap_rimetti_contesto(v_prima);
--       RAISE;
--   END;
--   PERFORM dbops.fn_pgtap_rimetti_contesto(v_prima);
-- ⚠️ Il SUPER_ADMIN si crea a ogni chiamata: non dipende da un SUPER_ADMIN
--   gia' presente sul database, che su un database da zero non c'e'.
-- ⚠️ app.current_emittente_id non si tocca.
DECLARE
    v_prima       jsonb := jsonb_build_object(
        'utente', script.fn_utente_di_sessione('dbops.fn_pgtap_entra_come_super_admin'),
        'ruolo',  current_setting('app.ruolo_applicativo', true));
    v_super_admin anagrafiche.identita_digitali.auth_user_id%TYPE;
BEGIN
    SELECT o.auth_user_id
      INTO v_super_admin
      FROM dbops.fn_pgtap_crea_operatore_umano(COALESCE(p_etichetta, 'super-admin'), true) o;

    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', false);
    PERFORM set_config('app.current_user_id', v_super_admin::text, false);

    RETURN v_prima;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_entra_come_super_admin(p_etichetta text)
IS 'Fixture dei pgTAP: entra nel contesto di un SUPER_ADMIN di fixture, creato a ogni chiamata con dbops.fn_pgtap_crea_operatore_umano(p_etichetta, true): scrive app.current_user_id e app.ruolo_applicativo per la sessione e restituisce il contesto di prima ({utente, ruolo}), da passare a dbops.fn_pgtap_rimetti_contesto. app.current_emittente_id non si tocca. La usano i builder che chiamano un verbo riservato al SUPER_ADMIN (dbops.fn_pgtap_sposta_scope_operatore, dbops.fn_pgtap_scrivi_profilo_accesso, dbops.fn_pgtap_lega_profilo_identita), che rimettono il contesto anche in errore.';
```

</div>

---
{% include-markdown "signature-core.md" %}
