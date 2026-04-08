{% include-markdown "it/dbzero/script/manual/fn_check_user_can_create_ba.md" %}
# ⚙️ Funzione `fn_check_user_can_create_ba`

```sql
CREATE FUNCTION fn_check_user_can_create_ba(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_user_can_create_ba(p_auth_user_id integer)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_has_assoc           boolean;
    v_emittenti_attivi    bigint;
BEGIN
    -- Guard input: parametro obbligatorio. Pure check, niente raise:
    -- ritorna FALSE in caso di input invalido (il trigger di fascia
    -- a10 deciderà se sollevare o meno).
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        RETURN false;
    END IF;

    -- 1) Esiste una riga per l'utente in user_emittenti_fiscali?
    --    Se sì => operatore (o admin di emittente) => puo' creare BA.
    SELECT EXISTS (
        SELECT 1
          FROM config.user_emittenti_fiscali uef
         WHERE uef.auth_user_id = p_auth_user_id
    ) INTO v_has_assoc;

    IF v_has_assoc THEN
        RETURN true;
    END IF;

    -- 2) Nessuna associazione: ammesso solo se l'istanza non ha
    --    alcun emittente attivo (caso "0 emittenti").
    SELECT COUNT(*)
      INTO v_emittenti_attivi
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.attivo = true;

    RETURN v_emittenti_attivi = 0;
END
$function$

COMMENT ON FUNCTION script.fn_check_user_can_create_ba(p_auth_user_id integer)
IS 'Pure check (no raise): puo'' l''utente creare billing_account? TRUE se ha riga in user_emittenti_fiscali O se 0 emittenti attivi. FALSE altrimenti (admin globale con emittenti presenti). Usata dal trigger BEFORE INSERT su anagrafiche.billing_account.';
```

---
{% include-markdown "signature-core.md" %}
