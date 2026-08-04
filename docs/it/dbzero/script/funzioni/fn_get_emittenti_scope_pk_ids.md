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
    v_ids    bigint[];
    v_attivo bigint;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Scope emittenti per i filtri su colonne PK.
    --   Semantica: NULL = tutto, '{}' = nessuno, array = whitelist.
    --
    -- Struttura (rev 2026-08-04): USCITA UNICA. Prima si calcola
    -- lo scope "di diritto" (super admin / whitelist), poi lo si
    -- interseca con l'emittente attivo in un solo punto. I RETURN
    -- anticipati di prima rendevano impossibile intersecare il
    -- ramo super admin, che e' proprio quello da restringere.
    -- =========================================================

    v_attivo := NULLIF(
                    current_setting('app.current_emittente_id', true),
                    ''
                )::bigint;

    -- 1. Identita OPERATORE attiva (helper DRY §4.6.B.0).
    --    '{}' e' gia' il valore piu' restrittivo: nessuna
    --    intersezione potrebbe cambiarlo, esce subito.
    IF NOT script.fn_has_identita_attiva(
               p_auth_user_id,
               'OPERATORE'::config.ruolo_applicativo) THEN
        RETURN '{}'::bigint[];
    END IF;

    -- 2. Scope di diritto.
    IF script.fn_is_super_admin(p_auth_user_id) THEN
        -- Nessuna restrizione: NULL = universo.
        v_ids := NULL;
    ELSE
        -- OPERATIVO: whitelist PK reale. Lettura diretta da
        -- user_emittenti_fiscali (la colonna e' gia' la PK).
        -- NULL (whitelist vuota) = nessuna restrizione
        -- (parita' con _sr_ids).
        SELECT array_agg(uef.emittente_fiscale_id)
          INTO v_ids
          FROM config.user_emittenti_fiscali uef
         WHERE uef.auth_user_id = p_auth_user_id;
    END IF;

    -- 3. Intersezione con l'emittente attivo (uscita unica).
    IF v_attivo IS NULL THEN
        RETURN v_ids;                      -- nessuna impersonazione
    END IF;

    IF v_ids IS NULL THEN
        RETURN ARRAY[v_attivo];            -- universo ∩ {X} = {X}
    END IF;

    IF v_attivo = ANY(v_ids) THEN
        RETURN ARRAY[v_attivo];            -- {A,B} ∩ {X}, X presente
    END IF;

    RETURN '{}'::bigint[];                 -- X fuori scope: nessuno
END
$function$

COMMENT ON FUNCTION script.fn_get_emittenti_scope_pk_ids(p_auth_user_id integer)
IS 'Scope emittenti per filtri su colonne PK (emittenti_fiscali.id). Semantica: NULL=tutto, ''{}''=nessuno, array=whitelist. Identita OPERATORE mancante -> []; SUPER_ADMIN -> NULL; altrimenti whitelist PK. Post 2026-08-04: uscita unica e intersezione con la GUC app.current_emittente_id (universo ∩ {X} = {X}; whitelist senza X -> []). Gemella di fn_get_emittenti_scope_sr_ids (che e'' un wrapper su questa). Vedi guida soggetti-e-ruoli §5b.';
```

---
{% include-markdown "signature-core.md" %}
