{% include-markdown "it/dbzero/config/manual/trgfn_user_emittenti_fiscali_guard_delete.md" %}
# ⚙️ Funzione `trgfn_user_emittenti_fiscali_guard_delete`

```sql
CREATE FUNCTION trgfn_user_emittenti_fiscali_guard_delete()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_user_emittenti_fiscali_guard_delete()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   La riga di config.user_emittenti_fiscali e' l'azienda di un
--   operatore: senza, l'operatore non vede niente. Cancellarla mentre
--   l'utente e' acceso si fa solo dal verbo che lo sposta.
--
-- Regole:
--   - la porta zeroerp.allow_user_emittente_delete_override apre solo se
--     vale l'auth_user_id della riga E chi scrive e' il proprietario della
--     tabella: cioe' dentro script.fn_change_user_emittenti_scope
--     (SECURITY DEFINER), che la scrive con la primitiva
--     script.fn_applica_user_emittenti_scope. L'applicazione non la apre,
--     nemmeno accendendo la GUC;
--   - utente Django spento: la riga si cancella (la cessazione);
--   - utente Django che non esiste piu' (DELETE in cascata): si cancella;
--   - utente acceso, fuori dalla porta: E_USER_EMITTENTE_DELETE_VIETATO.
DECLARE
    -- django.auth_user.is_active: le colonne di django non si ancorano
    v_is_active boolean;
BEGIN
    -- La porta, per la riga che il verbo sta spostando.
    IF current_setting('zeroerp.allow_user_emittente_delete_override', true)
           = OLD.auth_user_id::text
       AND script.fn_is_proprietario_tabella(TG_RELID) THEN
        RETURN OLD;
    END IF;

    -- Stato attivo dell'utente Django associato.
    SELECT au.is_active
      INTO v_is_active
      FROM django.auth_user au
     WHERE au.id = OLD.auth_user_id;

    -- Se l'utente non esiste piu' (DELETE in cascata) consentiamo
    -- la rimozione del child: la cessazione e' implicita.
    IF v_is_active IS NULL THEN
        RETURN OLD;
    END IF;

    -- Utente ancora attivo => DELETE vietata.
    IF v_is_active = true THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_USER_EMITTENTE_DELETE_VIETATO',
            jsonb_build_object(
                'detail', 'DELETE su user_emittenti_fiscali consentita solo se l''utente e'' disattivato',
                'auth_user_id', OLD.auth_user_id,
                'emittente_fiscale_id', OLD.emittente_fiscale_id
            ),
            NULL::uuid,
            OLD.auth_user_id::text
        );
    END IF;

    RETURN OLD;
END
$function$

COMMENT ON FUNCTION config.trgfn_user_emittenti_fiscali_guard_delete()
IS 'Guard BEFORE DELETE di config.user_emittenti_fiscali, la riga che dà a un operatore la sua azienda. Mentre l''utente Django è acceso la riga si cancella solo dalla porta zeroerp.allow_user_emittente_delete_override, aperta se vale l''auth_user_id della riga e chi scrive è il proprietario della tabella (script.fn_is_proprietario_tabella): cioè solo dentro il verbo script.fn_change_user_emittenti_scope, SECURITY DEFINER, che sposta l''operatore con la primitiva script.fn_applica_user_emittenti_scope. L''applicazione non la apre, nemmeno accendendo la GUC. Senza porta passano l''utente spento (la cessazione) e quello che non esiste più (la cascata da django.auth_user); l''utente acceso è rifiutato con E_USER_EMITTENTE_DELETE_VIETATO.';
```

</div>

---
{% include-markdown "signature-core.md" %}
