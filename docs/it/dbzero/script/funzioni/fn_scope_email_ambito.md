# ⚙️ Funzione `fn_scope_email_ambito`

```sql
CREATE FUNCTION fn_scope_email_ambito(p_auth_user_id integer, p_ambito character varying, p_emittente_fiscale_id bigint, p_unita_organizzativa_id integer, p_creato_da_user_id integer, p_processo_codice text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_email_ambito(p_auth_user_id integer, p_ambito character varying, p_emittente_fiscale_id bigint, p_unita_organizzativa_id integer, p_creato_da_user_id integer, p_processo_codice text DEFAULT NULL::text)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- =====================================================
    -- Scopo:
    --   «Chi guarda (p_auth_user_id) puo' vedere una mail con
    --   questo ambito, questa azienda, questo reparto e questo
    --   autore?» Sede unica per le policy di email_log e
    --   email_outbox, in lettura e in scrittura.
    --
    --   SISTEMA   -> super admin | processo
    --   REPARTO   -> (super admin | stesso reparto | processo)
    --                AND emittente in scope
    --   OPERATORE -> (super admin | autore | processo)
    --                AND emittente in scope
    --
    -- ⚠️ p_processo_codice NULL = nessun processo ammesso
    --   (l'outbox). Il log passa 'send_pending_emails':
    --   portare e' leggere.
    -- ⛔ Con p_auth_user_id NULL ogni ramo e' false: il
    --   cancello emittente (che per NULL dice true) e'
    --   sempre in AND con una condizione falsa.
    -- =====================================================
    SELECT COALESCE(
        CASE p_ambito
            WHEN 'SISTEMA' THEN
                script.fn_is_super_admin(p_auth_user_id)
                OR (p_processo_codice IS NOT NULL
                    AND script.fn_scope_identita_processo(
                            p_auth_user_id, p_processo_codice))
            WHEN 'REPARTO' THEN
                (   script.fn_is_super_admin(p_auth_user_id)
                 -- ⚠️ Utente senza reparto: la funzione rende
                 --   NULL, il confronto non e' vero, la riga
                 --   non si vede. Fail-closed, voluto.
                 OR p_unita_organizzativa_id
                    = script.fn_get_uo_id_for_user(p_auth_user_id)
                 OR (p_processo_codice IS NOT NULL
                     AND script.fn_scope_identita_processo(
                             p_auth_user_id, p_processo_codice)))
                AND script.fn_scope_ef_whitelist(
                        p_auth_user_id, p_emittente_fiscale_id)
            WHEN 'OPERATORE' THEN
                (   script.fn_is_super_admin(p_auth_user_id)
                 OR p_creato_da_user_id = p_auth_user_id
                 OR (p_processo_codice IS NOT NULL
                     AND script.fn_scope_identita_processo(
                             p_auth_user_id, p_processo_codice)))
                AND script.fn_scope_ef_whitelist(
                        p_auth_user_id, p_emittente_fiscale_id)
            ELSE false
        END,
        false);
$function$

COMMENT ON FUNCTION script.fn_scope_email_ambito(p_auth_user_id integer, p_ambito character varying, p_emittente_fiscale_id bigint, p_unita_organizzativa_id integer, p_creato_da_user_id integer, p_processo_codice text)
IS 'Chi vede una mail secondo il suo AMBITO. SISTEMA: super admin (piu'' il processo, se nominato). REPARTO: super admin, chi e'' nello stesso reparto (script.fn_get_uo_id_for_user) o il processo, E l''emittente nel perimetro di chi guarda. OPERATORE: super admin, chi l''ha creata (creato_da_user_id) o il processo, E l''emittente nel perimetro. Qualunque altro ambito: false. ⭐ Sede unica della regola per rls_email_log_ambito e rls_email_outbox_ambito, in USING e WITH CHECK: quattro sedi che non possono divergere. ⭐ p_processo_codice: il log passa send_pending_emails (portare e'' leggere: senza, una mail REPARTO o OPERATORE fallita non verrebbe ritentata); l''outbox passa NULL, perche'' nessun processo la apre. ⚠️ D-1: l''emittente resta in AND anche per l''autore e per il processo. ⛔ Utente NULL: sempre false, anche se il cancello emittente per NULL dice true. La regola della scheda pratica (D-3) non e'' qui. Brief: brief-db-email-visibilita-per-ambito. rev 2026-09-25.';
```

</div>

---
{% include-markdown "signature-core.md" %}
