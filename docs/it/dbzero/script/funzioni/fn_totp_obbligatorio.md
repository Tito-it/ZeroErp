{% include-markdown "it/dbzero/script/manual/fn_totp_obbligatorio.md" %}
# ⚙️ Funzione `fn_totp_obbligatorio`

```sql
CREATE FUNCTION fn_totp_obbligatorio(p_auth_user_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_totp_obbligatorio(p_auth_user_id integer)
 RETURNS TABLE(obbligatorio boolean, motivo text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: dire se la credenziale deve usare il secondo fattore, e
--   perche': CREDENZIALE, PROFILO o nessun obbligo (NULL).
DECLARE
    v_credenziale config.credenziali.totp_obbligatorio%TYPE;
BEGIN
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_totp_obbligatorio', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_auth_user_id', 'valore', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_totp_obbligatorio',
                           'credenziale assente o non valida']);
    END IF;

    -- 1. La credenziale. Riga assente: SELECT INTO lascia NULL = false.
    SELECT c.totp_obbligatorio
      INTO v_credenziale
      FROM config.credenziali c
     WHERE c.auth_user_id = p_auth_user_id;

    IF COALESCE(v_credenziale, false) THEN
        RETURN QUERY SELECT true, 'CREDENZIALE'::text;
        RETURN;
    END IF;

    -- 2. I profili: quelli applicabili in qualunque veste, e il
    --    SUPER_ADMIN, che fra quelli non c'e' e ha sempre il segno.
    IF script.fn_is_super_admin_account(p_auth_user_id)
       OR EXISTS (
           SELECT 1
             FROM script.fn_get_profili_accesso_applicabili(p_auth_user_id, NULL) ap
             JOIN config.profili_accesso pa
               ON pa.id = ap.profilo_accesso_id
            WHERE pa.richiede_secondo_fattore) THEN
        RETURN QUERY SELECT true, 'PROFILO'::text;
        RETURN;
    END IF;

    RETURN QUERY SELECT false, NULL::text;
END;
$function$

COMMENT ON FUNCTION script.fn_totp_obbligatorio(p_auth_user_id integer)
IS 'La risposta unica sull''obbligo del secondo fattore (TOTP) di una CREDENZIALE (brief-db-secondo-fattore-totp §2.3): obbligatorio = flag sulla credenziale OPPURE profilo privilegiato. motivo: CREDENZIALE (config.credenziali.totp_obbligatorio), PROFILO (un profilo applicabile in qualunque veste con richiede_secondo_fattore, o la credenziale e'' SUPER_ADMIN per script.fn_is_super_admin_account — il SUPER_ADMIN non e'' fra i profili di fn_get_profili_accesso_applicabili, e fn_is_super_admin si spegne fuori dalla veste OPERATORE), NULL = nessun obbligo. La credenziale e'' una e vale per tutte le porte. La chiama il backend al login e nel middleware che porta al setup; il motivo serve al frontend per spiegare perche''. Credenziale inesistente: (false, NULL), e'' una lettura; id NULL o <= 0 -> E_AUTH_CHIAMATA_NON_VALIDA. SECURITY DEFINER (la risposta non dipende da cosa vede chi chiede: senza contesto una RLS futura darebbe fail-open), STABLE, search_path bloccato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
