{% include-markdown "it/dbzero/script/manual/fn_azzera_tentativi_credenziale.md" %}
# ⚙️ Funzione `fn_azzera_tentativi_credenziale`

```sql
CREATE FUNCTION fn_azzera_tentativi_credenziale(p_auth_user_id integer, p_provenienza inet)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_azzera_tentativi_credenziale(p_auth_user_id integer, p_provenienza inet DEFAULT NULL::inet)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: azzerare i tentativi falliti di una credenziale. Sempre i
--   fallimenti consecutivi (attesa crescente); le righe di provenienza
--   (freno): la sola coppia con p_provenienza, tutte con NULL.
--   Non tocca il blocco dell'admin ne' il cambio password obbligatorio.
DECLARE
    v_credenziale_id config.credenziali.id%TYPE;
BEGIN
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_azzera_tentativi_credenziale', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_auth_user_id', 'valore', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_azzera_tentativi_credenziale',
                           'credenziale assente o non valida']);
    END IF;

    UPDATE config.credenziali c
       SET fallimenti_consecutivi = 0,
           ultimo_fallimento_at   = NULL
     WHERE c.auth_user_id = p_auth_user_id
    RETURNING c.id INTO v_credenziale_id;

    -- Nessuna riga: niente da azzerare.
    IF v_credenziale_id IS NULL THEN
        RETURN;
    END IF;

    IF p_provenienza IS NULL THEN
        -- Reset password: la password e' cambiata, nessun tentativo conta piu'.
        DELETE FROM config.credenziali_provenienze p
         WHERE p.credenziale_id = v_credenziale_id;
    ELSE
        -- Accesso riuscito: solo la coppia da cui si e' entrati.
        DELETE FROM config.credenziali_provenienze p
         WHERE p.credenziale_id = v_credenziale_id
           AND p.provenienza    = p_provenienza;
    END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_azzera_tentativi_credenziale(p_auth_user_id integer, p_provenienza inet)
IS 'Azzera i tentativi falliti di una credenziale. Sempre i fallimenti consecutivi (attesa crescente); le righe di provenienza (freno): con p_provenienza la sola coppia da cui si e'' entrati (accesso riuscito, ramo successo di fn_registra_tentativo_login — il freno sulla macchina di chi attacca resta), con NULL tutte (reset password riuscito, D-2: la password e'' cambiata e i tentativi sulla vecchia non contano piu''). Non tocca il blocco dell''admin (D-B3: lo toglie solo fn_sblocca_credenziale) ne'' deve_cambiare_password. Senza riga non c''e'' niente da azzerare. SECURITY DEFINER del PROPRIETARIO, non di un superuser, search_path bloccato; nessun guard di permesso, dichiarato (login e reset girano prima che esista un utente). Brief: brief-db-blocco-login-per-credenziale §3.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
