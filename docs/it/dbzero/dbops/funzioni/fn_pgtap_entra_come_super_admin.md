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
-- ⭐ Un SUPER_ADMIN per transazione: il primo ingresso lo crea (non
--   dipende da un SUPER_ADMIN gia' presente sul database, che su un
--   database da zero non c'e'), i seguenti lo riusano finche' resta
--   SUPER_ADMIN. L'id sta nella GUC LOCALE dbops.pgtap_super_admin, che
--   PostgreSQL annulla insieme alla riga: a fine transazione e a ogni
--   savepoint annullato.
-- ⚠️ L'etichetta vale solo per il SUPER_ADMIN che si crea.
-- ⚠️ app.current_emittente_id non si tocca.
DECLARE
    v_prima       jsonb := jsonb_build_object(
        'utente', script.fn_utente_di_sessione('dbops.fn_pgtap_entra_come_super_admin'),
        'ruolo',  current_setting('app.ruolo_applicativo', true));
    v_super_admin anagrafiche.identita_digitali.auth_user_id%TYPE;
BEGIN
    -- Il SUPER_ADMIN gia' creato in questa transazione, se lo e' ancora.
    v_super_admin := NULLIF(current_setting('dbops.pgtap_super_admin', true), '')::int;
    IF v_super_admin IS NOT NULL
       AND NOT script.fn_is_super_admin_account(v_super_admin) THEN
        v_super_admin := NULL;
    END IF;

    IF v_super_admin IS NULL THEN
        SELECT o.auth_user_id
          INTO v_super_admin
          FROM dbops.fn_pgtap_crea_operatore_umano(COALESCE(p_etichetta, 'super-admin'), true) o;
        PERFORM set_config('dbops.pgtap_super_admin', v_super_admin::text, true);
    END IF;

    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', false);
    PERFORM set_config('app.current_user_id', v_super_admin::text, false);

    RETURN v_prima;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_entra_come_super_admin(p_etichetta text)
IS 'Fixture dei pgTAP: entra nel contesto di un SUPER_ADMIN di fixture e restituisce il contesto di prima ({utente, ruolo}), da passare a dbops.fn_pgtap_rimetti_contesto. Scrive app.current_user_id e app.ruolo_applicativo per la sessione; app.current_emittente_id non si tocca. Il SUPER_ADMIN e'' uno per transazione: il primo ingresso lo crea con dbops.fn_pgtap_crea_operatore_umano(p_etichetta, true) e ne scrive l''id nella GUC locale dbops.pgtap_super_admin, gli ingressi seguenti lo riusano finche'' script.fn_is_super_admin_account lo conferma, altrimenti ne creano uno nuovo. La GUC si annulla con la transazione e con ogni savepoint annullato, insieme alla riga che nomina. L''etichetta vale solo per il SUPER_ADMIN che si crea. La usano i builder che chiamano un verbo riservato al SUPER_ADMIN (dbops.fn_pgtap_scrivi_override, dbops.fn_pgtap_sposta_scope_operatore, dbops.fn_pgtap_scrivi_profilo_accesso, dbops.fn_pgtap_lega_profilo_identita), che rimettono il contesto anche in errore.';
```

</div>

---
{% include-markdown "signature-core.md" %}
