{% include-markdown "it/dbzero/script/manual/fn_utente_di_sessione.md" %}
# ⚙️ Funzione `fn_utente_di_sessione`

```sql
CREATE FUNCTION fn_utente_di_sessione(p_chi text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_utente_di_sessione(p_chi text DEFAULT NULL::text)
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- text: il valore della GUC com'e' scritto, prima di leggerlo come id
    v_guc text := NULLIF(current_setting('app.current_user_id', true), '');
BEGIN
    -- Scopo: l'utente della richiesta, cioe' l'auth_user.id che il
    --   backend scrive in app.current_user_id.
    --   Assente o vuota: NULL, e decide chi legge.
    --   Un valore che non e' l'id di un utente: chiamante rotto,
    --   E_SCRIPT_CHIAMATA_NON_VALIDA.
    IF v_guc IS NULL THEN
        RETURN NULL;
    END IF;

    -- Il CASE garantisce l'ordine: il confronto numerico solo su un
    -- intero positivo senza zeri in testa, di al piu' dieci cifre.
    IF (CASE WHEN v_guc ~ '^[1-9][0-9]{0,9}$' THEN v_guc::bigint > 2147483647
             ELSE TRUE END) THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            COALESCE(p_chi, 'script.fn_utente_di_sessione'),
            'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('app_current_user_id', v_guc),
            NULL::uuid,
            COALESCE(p_chi, 'script.fn_utente_di_sessione'),
            'app.current_user_id non e'' l''id di un utente');
    END IF;

    RETURN v_guc::integer;
END;
$function$

COMMENT ON FUNCTION script.fn_utente_di_sessione(p_chi text)
IS 'BB: l''utente della richiesta, cioè l''auth_user.id che il backend scrive in app.current_user_id, letto da una sede sola. GUC assente o vuota: NULL, e che cosa voglia dire «nessun utente» lo decide chi legge. Un valore che non è l''id di un utente (non solo cifre, zeri in testa, zero, oltre il massimo di integer): E_SCRIPT_CHIAMATA_NON_VALIDA, col valore in context.app_current_user_id. p_chi: la funzione che legge, nel log e nella frase; senza, il BB stesso. Ogni funzione e vista che legge l''utente di sessione passa da qui, invece di convertire la GUC da sé. STABLE, INVOKER, non legge tabelle.';
```

</div>

---
{% include-markdown "signature-core.md" %}
