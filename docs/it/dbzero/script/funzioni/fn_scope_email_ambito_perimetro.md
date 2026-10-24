{% include-markdown "it/dbzero/script/manual/fn_scope_email_ambito_perimetro.md" %}
# ⚙️ Funzione `fn_scope_email_ambito_perimetro`

```sql
CREATE FUNCTION fn_scope_email_ambito_perimetro(p_super_admin boolean, p_uo_id integer, p_processo boolean, p_perimetro bigint[], p_auth_user_id integer, p_ambito character varying, p_emittente_fiscale_id bigint, p_unita_organizzativa_id integer, p_creato_da_user_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_email_ambito_perimetro(p_super_admin boolean, p_uo_id integer, p_processo boolean, p_perimetro bigint[], p_auth_user_id integer, p_ambito character varying, p_emittente_fiscale_id bigint, p_unita_organizzativa_id integer, p_creato_da_user_id integer)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- Scopo: chi guarda puo' vedere una mail con questo ambito, questa
    --   azienda, questo reparto e questo autore? La regola di
    --   script.fn_scope_email_ambito, con le quattro risposte su chi guarda
    --   gia' calcolate dalla policy:
    --     p_super_admin  script.fn_is_super_admin(utente)
    --     p_uo_id        script.fn_get_uo_id_for_user(utente)
    --     p_processo     script.fn_scope_identita_processo(utente, codice),
    --                    false se nessun processo e' ammesso (l'outbox)
    --     p_perimetro    script.fn_get_emittenti_scope_pk_ids(utente)
    -- ⚠️ Utente senza reparto: p_uo_id NULL, il confronto non e' vero, la
    --   riga non si vede. Fail-closed, voluto.
    -- ⚠️ L'emittente resta in AND anche per l'autore e per il processo.
    SELECT COALESCE(
        CASE p_ambito
            WHEN 'SISTEMA' THEN
                p_super_admin OR p_processo
            WHEN 'REPARTO' THEN
                (p_super_admin
                 OR p_unita_organizzativa_id = p_uo_id
                 OR p_processo)
                AND script.fn_scope_ef_perimetro(p_perimetro, p_emittente_fiscale_id)
            WHEN 'OPERATORE' THEN
                (p_super_admin
                 OR p_creato_da_user_id = p_auth_user_id
                 OR p_processo)
                AND script.fn_scope_ef_perimetro(p_perimetro, p_emittente_fiscale_id)
            ELSE false
        END,
        false)
$function$

COMMENT ON FUNCTION script.fn_scope_email_ambito_perimetro(p_super_admin boolean, p_uo_id integer, p_processo boolean, p_perimetro bigint[], p_auth_user_id integer, p_ambito character varying, p_emittente_fiscale_id bigint, p_unita_organizzativa_id integer, p_creato_da_user_id integer)
IS 'La regola dell''ambito delle email (sede unica: la compone anche script.fn_scope_email_ambito), con le quattro risposte su chi guarda gia'' calcolate dalla policy una volta per istruzione: super admin (script.fn_is_super_admin), reparto (script.fn_get_uo_id_for_user), identita'' del processo (script.fn_scope_identita_processo; false dove nessun processo e'' ammesso) e perimetro emittenti (script.fn_get_emittenti_scope_pk_ids). SISTEMA: super admin o processo. REPARTO: super admin, stesso reparto o processo, E l''emittente nel perimetro. OPERATORE: super admin, autore o processo, E l''emittente nel perimetro. Altro ambito: false. Pura, non legge tabelle (linee-guida-sql §10.3). Rev 2026-10-21 (20261021-41, giro 5 di brief-db-perimetro-una-volta-famiglie-residue).';
```

</div>

---
{% include-markdown "signature-core.md" %}
