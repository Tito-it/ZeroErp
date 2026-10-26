{% include-markdown "it/dbzero/script/manual/fn_check_user_can_create_ba.md" %}
# ⚙️ Funzione `fn_check_user_can_create_ba`

```sql
CREATE FUNCTION fn_check_user_can_create_ba(p_auth_user_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_user_can_create_ba(p_auth_user_id integer)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_has_assoc        boolean;
    v_emittenti_attivi bigint;
    v_attivo           bigint;
BEGIN
    -- Guard input: parametro obbligatorio. Pure check, niente raise:
    -- ritorna FALSE in caso di input invalido (il trigger di fascia
    -- a10 decidera' se sollevare o meno).
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        RETURN false;
    END IF;

    -- 1) Sta lavorando dentro un emittente? (rev 2026-08-04)
    --    E' la stessa regola del ramo 2 in forma di sessione:
    --    "appartieni a un emittente" oppure "ci stai dentro".
    --    Il controllo passa dalla canonica, quindi un utente con
    --    emittente attivo fuori dal proprio scope NON guadagna
    --    il diritto di creare.
    v_attivo := NULLIF(
                    current_setting('app.current_emittente_id', true),
                    ''
                )::bigint;

    IF v_attivo IS NOT NULL
       AND script.fn_check_user_emittente_scope(p_auth_user_id, v_attivo) THEN
        RETURN true;
    END IF;

    -- 2) Esiste una riga per l'utente in user_emittenti_fiscali?
    --    Se si' => operatore (o admin di emittente) => puo' creare BA.
    SELECT EXISTS (
        SELECT 1
          FROM config.user_emittenti_fiscali uef
         WHERE uef.auth_user_id = p_auth_user_id
    ) INTO v_has_assoc;

    IF v_has_assoc THEN
        RETURN true;
    END IF;

    -- 3) Nessuna associazione: ammesso solo se l'istanza non ha
    --    alcun emittente attivo (caso "0 emittenti").
    SELECT COUNT(*)
      INTO v_emittenti_attivi
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.attivo = true;

    RETURN v_emittenti_attivi = 0;
END
$function$

COMMENT ON FUNCTION script.fn_check_user_can_create_ba(p_auth_user_id integer)
IS 'Pure check: l''utente puo'' creare un billing account? Regola (rev 2026-08-04): true se sta lavorando dentro un emittente valido (GUC app.current_emittente_id verificata da fn_check_user_emittente_scope), oppure se ha una riga in config.user_emittenti_fiscali, oppure se l''istanza non ha alcun emittente attivo (bootstrap). Altrimenti false. Usata dal guard a10 anagrafiche.trgfn_billing_account_guard_admin_globale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
