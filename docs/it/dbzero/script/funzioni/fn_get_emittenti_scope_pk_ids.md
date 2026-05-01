{% include-markdown "it/dbzero/script/manual/fn_get_emittenti_scope_pk_ids.md" %}
# ⚙️ Funzione `fn_get_emittenti_scope_pk_ids`

```sql
CREATE FUNCTION fn_get_emittenti_scope_pk_ids(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_emittenti_scope_pk_ids(p_auth_user_id integer)
 RETURNS bigint[]
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_ids bigint[];
BEGIN
    -- 1. Identita OPERATORE attiva (helper DRY §4.6.B.0).
    IF NOT script.fn_has_identita_attiva(
               p_auth_user_id,
               'OPERATORE'::config.ruolo_applicativo) THEN
        RETURN '{}'::bigint[];
    END IF;

    -- 2. Super admin? Nessuna restrizione.
    IF script.fn_is_super_admin(p_auth_user_id) THEN
        RETURN NULL;
    END IF;

    -- 3. OPERATIVO: whitelist PK reale.
    --    Lettura diretta da user_emittenti_fiscali (no JOIN
    --    a emittenti_fiscali necessario: la colonna e' gia' la PK).
    SELECT array_agg(uef.emittente_fiscale_id)
      INTO v_ids
      FROM config.user_emittenti_fiscali uef
     WHERE uef.auth_user_id = p_auth_user_id;

    -- NULL (whitelist vuota) = nessuna restrizione (parita' con _sr_ids).
    RETURN v_ids;
END
$function$

COMMENT ON FUNCTION script.fn_get_emittenti_scope_pk_ids(p_auth_user_id integer)
IS 'Scope emittenti per filtri su colonne PK (emittenti_fiscali.id). Semantica: NULL=tutto, ''{}''=nessuno, array=whitelist. Identita OPERATORE mancante -> []; SUPER_ADMIN -> NULL; altrimenti whitelist PK. Gemella di fn_get_emittenti_scope_sr_ids (che e'' un wrapper su questa). Vedi guida soggetti-e-ruoli §5b.';
```

---
{% include-markdown "signature-core.md" %}
