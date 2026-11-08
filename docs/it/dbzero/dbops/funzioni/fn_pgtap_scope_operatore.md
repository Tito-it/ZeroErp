{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_scope_operatore.md" %}
# ⚙️ Funzione `fn_pgtap_scope_operatore`

```sql
CREATE FUNCTION fn_pgtap_scope_operatore(p_emittente_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_scope_operatore(p_emittente_fiscale_id bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- ⚠️ `integer` esplicito: django.auth_user.id, a cui il DB non si lega.
    v_utente    integer;
    -- ⚠️ `bigint[]` esplicito: elementi = anagrafiche.emittenti_fiscali.id.
    v_perimetro bigint[];
    v_emittente anagrafiche.emittenti_fiscali.id%TYPE;
    v_identita  anagrafiche.identita_digitali.id%TYPE;
BEGIN
    -- Scopo: lo scope di un lavoro OPERATORE accodato da chi e' in
    --   sessione: la sua identita' e un'azienda del suo perimetro
    --   (quella chiesta, oppure la prima). Super admin (perimetro
    --   NULL): la prima azienda attiva.
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    IF v_utente IS NULL THEN
        RAISE EXCEPTION 'dbops.fn_pgtap_scope_operatore: nessun utente in sessione (app.current_user_id); prima script.fn_pgtap_set_contesto_operatore()';
    END IF;

    v_perimetro := script.fn_get_emittenti_scope_pk_ids(v_utente);

    v_emittente := COALESCE(
        p_emittente_fiscale_id,
        (SELECT min(e) FROM unnest(v_perimetro) AS e),
        CASE WHEN v_perimetro IS NULL
             THEN (SELECT min(ef.id) FROM anagrafiche.emittenti_fiscali ef)
        END);
    IF v_emittente IS NULL THEN
        RAISE EXCEPTION 'dbops.fn_pgtap_scope_operatore: l''utente % non ha nessuna azienda nel perimetro', v_utente;
    END IF;

    SELECT idg.id INTO v_identita
      FROM anagrafiche.identita_digitali idg
     WHERE idg.auth_user_id = v_utente
       AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
     ORDER BY idg.id
     LIMIT 1;

    RETURN jsonb_build_object(
        'auth_user_id',        v_utente,
        'username',            'pgtap',
        'identita_id',         v_identita,
        'emittente_attivo_id', v_emittente,
        'emittente_ids',       jsonb_build_array(v_emittente),
        'scope_key',           v_emittente::text);
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_scope_operatore(p_emittente_fiscale_id bigint)
IS 'Helper di fixture pgTAP: lo scope di un lavoro OPERATORE di dbops.coda_lavori accodato da chi e'' in sessione: auth_user_id dal contesto (app.current_user_id), l''identita'' OPERATORE dell''utente, e un''azienda del suo perimetro in emittente_attivo_id ed emittente_ids (quella passata, altrimenti la prima; per il super admin la prima azienda). E'' lo scope che dbops.fn_accoda_lavoro accetta da una sessione dell''applicazione. Solleva se in sessione non c''e'' nessuno, o se l''utente non ha aziende. Prima: script.fn_pgtap_set_contesto_operatore().';
```

</div>

---
{% include-markdown "signature-core.md" %}
