{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist`

```sql
CREATE FUNCTION fn_scope_ef_whitelist(p_identita_id bigint, p_emittente_sr_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist(p_identita_id bigint, p_emittente_sr_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Logica legacy riprodotta + defense-in-depth:
    --   - identita inesistente / non attiva -> false (fail-closed)
    --   - whitelist vuota (nessuna riga)    -> true (accesso globale)
    --   - whitelist valorizzata             -> true solo se il
    --                                          soggetto_ruolo
    --                                          emittente target e' in lista
    WITH ctx AS (
        SELECT id.auth_user_id
          FROM anagrafiche.identita_digitali id
         WHERE id.id     = p_identita_id
           AND id.attivo = true
    )
    SELECT
        -- Gate: l'identita deve esistere ed essere attiva. Senza
        -- questo, una CTE vuota farebbe passare il NOT EXISTS
        -- sottostante in modo vacuously true (leak).
        EXISTS (SELECT 1 FROM ctx)
        AND (
            NOT EXISTS (
                -- caso 1: nessuna riga in whitelist -> accesso a tutti
                SELECT 1
                  FROM config.user_emittenti_fiscali uef
                  JOIN ctx ON ctx.auth_user_id = uef.auth_user_id
            )
            OR EXISTS (
                -- caso 2: whitelist valorizzata -> target deve essere in lista
                SELECT 1
                  FROM config.user_emittenti_fiscali uef
                  JOIN ctx ON ctx.auth_user_id = uef.auth_user_id
                  JOIN anagrafiche.emittenti_fiscali ef
                    ON ef.id = uef.emittente_fiscale_id
                 WHERE ef.soggetto_ruolo_id = p_emittente_sr_id
            )
        );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist(p_identita_id bigint, p_emittente_sr_id bigint)
IS 'Scope policy EF_WHITELIST: ritorna true se l''identita puo vedere le righe con il soggetto_ruolo emittente specificato. Replica la logica legacy di config.user_emittenti_fiscali (whitelist vuota = accesso globale). STABLE, inlineable.';
```

---
{% include-markdown "signature-core.md" %}
