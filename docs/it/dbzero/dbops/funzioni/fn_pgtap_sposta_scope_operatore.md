{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_sposta_scope_operatore.md" %}
# ⚙️ Funzione `fn_pgtap_sposta_scope_operatore`

```sql
CREATE FUNCTION fn_pgtap_sposta_scope_operatore(p_auth_user_id integer, p_emittente_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_sposta_scope_operatore(p_auth_user_id integer, p_emittente_fiscale_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
-- Scopo: in un pgTAP, portare l'operatore p_auth_user_id sull'azienda
--   p_emittente_fiscale_id, oppure togliergli l'azienda (NULL), dal verbo
--   script.fn_change_user_emittenti_scope. Restituisce il risultato del verbo.
-- Uso:
--   PERFORM dbops.fn_pgtap_sposta_scope_operatore(
--       (SELECT user_id FROM tmp_refs), (SELECT emittente_b FROM tmp_refs));
-- ⚠️ Il verbo chiede il SUPER_ADMIN: lo fa un SUPER_ADMIN di fixture,
--   creato a ogni chiamata, che entra nel contesto e ne esce. Il contesto di
--   prima (app.current_user_id, app.ruolo_applicativo) si rimette, anche
--   in errore. app.current_emittente_id non si tocca.
-- ⚠️ Le regole sono quelle del verbo: l'ultimo SUPER_ADMIN attivo non si
--   sposta, piu' di un'azienda no. Un rifiuto arriva al test com'e'.
DECLARE
    v_utente_prima config.user_emittenti_fiscali.auth_user_id%TYPE
        := script.fn_utente_di_sessione('dbops.fn_pgtap_sposta_scope_operatore');
    -- il valore della GUC di contesto com'era, anche vuoto
    v_ruolo_prima  text := current_setting('app.ruolo_applicativo', true);
    v_super_admin  config.user_emittenti_fiscali.auth_user_id%TYPE;
    v_esito        jsonb;
BEGIN
    SELECT o.auth_user_id
      INTO v_super_admin
      FROM dbops.fn_pgtap_crea_operatore_umano('sposta-scope', true) o;

    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', false);
    PERFORM set_config('app.current_user_id', v_super_admin::text, false);

    BEGIN
        v_esito := script.fn_change_user_emittenti_scope(
                       p_auth_user_id,
                       CASE WHEN p_emittente_fiscale_id IS NULL
                            THEN ARRAY[]::bigint[]
                            ELSE ARRAY[p_emittente_fiscale_id] END);
    EXCEPTION
        WHEN OTHERS THEN
            PERFORM set_config('app.current_user_id', COALESCE(v_utente_prima::text, ''), false);
            PERFORM set_config('app.ruolo_applicativo', COALESCE(v_ruolo_prima, ''), false);
            RAISE;
    END;

    PERFORM set_config('app.current_user_id', COALESCE(v_utente_prima::text, ''), false);
    PERFORM set_config('app.ruolo_applicativo', COALESCE(v_ruolo_prima, ''), false);

    RETURN v_esito;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_sposta_scope_operatore(p_auth_user_id integer, p_emittente_fiscale_id bigint)
IS 'Solo per i pgTAP: porta l''operatore sull''azienda indicata dal verbo script.fn_change_user_emittenti_scope, e restituisce il suo risultato. Con NULL toglie l''azienda, e il verbo lo ammette solo per un SUPER_ADMIN (E_OPERATORE_SCOPE_GLOBALE_SOLO_SUPER_ADMIN): l''operatore senza azienda di un test si costruisce con dbops.fn_pgtap_crea_operatore_umano, che nasce senza, non si ottiene togliendogliela. Il verbo chiede il SUPER_ADMIN: lo fa un SUPER_ADMIN di fixture (dbops.fn_pgtap_crea_operatore_umano) che entra nel contesto e ne esce; app.current_user_id e app.ruolo_applicativo tornano com''erano, anche in errore. Le regole e i rifiuti sono quelli del verbo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
