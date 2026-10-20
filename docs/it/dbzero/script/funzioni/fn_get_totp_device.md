{% include-markdown "it/dbzero/script/manual/fn_get_totp_device.md" %}
# ⚙️ Funzione `fn_get_totp_device`

```sql
CREATE FUNCTION fn_get_totp_device(p_auth_user_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_totp_device(p_auth_user_id integer)
 RETURNS TABLE(stato text, secret_encrypted character varying, ultimo_passo_usato bigint, recovery_rimasti integer)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: lo stato del device del secondo fattore di una credenziale,
--   in una riga sola anche quando il device non c'e'.
BEGIN
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_get_totp_device', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_auth_user_id', 'valore', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_get_totp_device',
                           'credenziale assente o non valida']);
    END IF;

    RETURN QUERY
    SELECT CASE WHEN d.id IS NULL  THEN 'ASSENTE'
                WHEN d.confermato  THEN 'ATTIVO'
                ELSE 'DA_CONFERMARE' END,
           d.secret_encrypted,
           d.ultimo_passo_usato,
           COALESCE(jsonb_array_length(d.recovery_codes_hash), 0)
      FROM (SELECT 1) uno
      LEFT JOIN config.auth_totp_device d
        ON d.auth_user_id = p_auth_user_id;
END;
$function$

COMMENT ON FUNCTION script.fn_get_totp_device(p_auth_user_id integer)
IS 'Lo stato del device del secondo fattore (TOTP) di una credenziale, in UNA riga anche quando il device non c''e'': stato ASSENTE (mai registrato o disabilitato), DA_CONFERMARE (registrato, setup in corso: il segreto c''e'' perche'' il backend ci verifica il primo codice), ATTIVO (confermato, in uso); secret_encrypted (cifrato: lo decifra il backend), ultimo_passo_usato (anti-replay), recovery_rimasti (codici di recupero non ancora usati). E'' la sola sede del significato della riga assente. id NULL o <= 0 -> E_AUTH_CHIAMATA_NON_VALIDA. INVOKER, STABLE: si legge anche prima del login. Brief: brief-db-secondo-fattore-totp §3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
