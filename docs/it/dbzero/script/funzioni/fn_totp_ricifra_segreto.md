{% include-markdown "it/dbzero/script/manual/fn_totp_ricifra_segreto.md" %}
# ⚙️ Funzione `fn_totp_ricifra_segreto`

```sql
CREATE FUNCTION fn_totp_ricifra_segreto(p_auth_user_id integer, p_secret_atteso character varying, p_secret_nuovo character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_totp_ricifra_segreto(p_auth_user_id integer, p_secret_atteso character varying, p_secret_nuovo character varying)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: portare il segreto di un device sulla chiave di cifratura
--   nuova, solo se e' ancora quello che il comando ha letto.
BEGIN
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0
       OR p_secret_atteso IS NULL OR btrim(p_secret_atteso) = ''
       OR p_secret_nuovo  IS NULL OR btrim(p_secret_nuovo)  = ''
       OR p_secret_atteso = p_secret_nuovo THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_totp_ricifra_segreto', 'E_AUTH_CHIAMATA_NON_VALIDA',
            -- Solo i segni, mai i token: il contesto finisce nel log.
            jsonb_build_object(
                'p_auth_user_id', p_auth_user_id,
                'atteso_vuoto',   p_secret_atteso IS NULL OR btrim(p_secret_atteso) = '',
                'nuovo_vuoto',    p_secret_nuovo  IS NULL OR btrim(p_secret_nuovo)  = '',
                'uguali',         p_secret_atteso = p_secret_nuovo),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_totp_ricifra_segreto',
                           'credenziale, segreto atteso e segreto nuovo (diversi) obbligatori']);
    END IF;

    -- Confronto e scrittura insieme: chi ha cambiato il segreto
    -- nel frattempo vince, e qui il WHERE non combacia piu'.
    UPDATE config.auth_totp_device d
       SET secret_encrypted = p_secret_nuovo
     WHERE d.auth_user_id     = p_auth_user_id
       AND d.secret_encrypted = p_secret_atteso;

    RETURN FOUND;
END;
$function$

COMMENT ON FUNCTION script.fn_totp_ricifra_segreto(p_auth_user_id integer, p_secret_atteso character varying, p_secret_nuovo character varying)
IS 'Porta il segreto TOTP sulla chiave di cifratura nuova alla rotazione delle chiavi del backend (manage.py ricifra_campi_cifrati): sostituisce secret_encrypted solo se e'' ancora il valore letto, confronto e scrittura in UNA istruzione. true se ha scritto; false se il segreto e'' cambiato nel frattempo (device riconfigurato o disabilitato) o il device non c''e'': il comando lo conta, non e'' un errore. Vale per un device in qualunque stato, DA_CONFERMARE compreso. Non tocca altro: ne'' confermato, ne'' l''anti-replay, ne'' i codici di recupero, ne'' ultimo_uso_at. Id NULL o <= 0, segreti NULL o vuoti, atteso = nuovo -> E_AUTH_CHIAMATA_NON_VALIDA (i segreti non entrano nel contesto del log). Nessuno agisce: lo chiama un comando di manutenzione. Limite: il backend sostituisce un segreto senza dire chi e'' — non e'' un potere nuovo, il segreto lo apre solo chi ha le chiavi; il modello protegge da un backend che sbaglia, non da uno manomesso. SECURITY DEFINER del PROPRIETARIO, search_path bloccato; la tabella resta in sola lettura per l''app. Brief: brief-db-totp-ricifra-segreto §2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
