{% include-markdown "it/dbzero/script/manual/fn_change_user_emittenti_scope.md" %}
# ⚙️ Funzione `fn_change_user_emittenti_scope`

```sql
CREATE FUNCTION fn_change_user_emittenti_scope(p_auth_user_id integer, p_emittente_ids bigint[])
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_change_user_emittenti_scope(p_auth_user_id integer, p_emittente_ids bigint[])
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo:
--   Il verbo con cui il SUPER_ADMIN porta un operatore su un'azienda,
--   o gliela toglie. E' la strada dell'endpoint di amministrazione.
--
-- Regole:
--   - SECURITY DEFINER: il permesso e' qui, in prima riga, e chiede lo
--     stesso controllo dell'endpoint, il SUPER_ADMIN
--     (script.fn_guard_super_admin: E_PERMESSO_NEGATO, anche senza utente);
--   - le regole dello spostamento e la porta del DELETE stanno nella
--     primitiva script.fn_applica_user_emittenti_scope, che l'app non
--     esegue.
DECLARE
    v_utente config.user_emittenti_fiscali.auth_user_id%TYPE;
BEGIN
    -- Il permesso, prima di ogni altra cosa.
    v_utente := script.fn_utente_di_sessione('script.fn_change_user_emittenti_scope');
    PERFORM script.fn_guard_super_admin(v_utente);

    RETURN script.fn_applica_user_emittenti_scope(p_auth_user_id, p_emittente_ids);
END;
$function$

COMMENT ON FUNCTION script.fn_change_user_emittenti_scope(p_auth_user_id integer, p_emittente_ids bigint[])
IS 'Il verbo con cui il SUPER_ADMIN porta un operatore su un''azienda (un solo emittente) o gliela toglie (array vuoto o NULL). SECURITY DEFINER: in prima riga chiede il SUPER_ADMIN all''utente di sessione (script.fn_guard_super_admin: E_PERMESSO_NEGATO, anche senza utente), lo stesso controllo dell''endpoint. Lo spostamento lo fa la primitiva script.fn_applica_user_emittenti_scope, che l''applicazione non esegue: restituisce changed, scope_mode (SINGLE o GLOBAL) ed emittente_id, e rifiuta parametri non validi (E_OPERATORE_SCOPE_PARAM_NON_VALIDO), più di un emittente (E_OPERATORE_SCOPE_MULTI_NON_AMMESSO) e l''ultimo SUPER_ADMIN attivo (E_PROFILO_ULTIMO_SUPER_ADMIN). Il DELETE della riga di prima passa dalla porta zeroerp.allow_user_emittente_delete_override, che si apre solo per la riga dell''operatore e solo dentro il verbo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
