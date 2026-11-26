# ⚙️ Funzione `fn_togli_revoca_veste`

```sql
CREATE FUNCTION fn_togli_revoca_veste(p_identita_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_togli_revoca_veste(p_identita_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente    anagrafiche.identita_digitali.revocata_da_user_id%TYPE;
    v_riga      anagrafiche.identita_digitali%ROWTYPE;
    v_tolti     integer;  -- conteggio delle righe toccate
BEGIN
    -- =========================================================
    -- Scopo: il nuovo invito dell'amministratore toglie il
    --   segno della revoca dalla coppia (credenziale, ruolo
    --   anagrafico, veste) della veste p_identita_id. La veste
    --   resta spenta: la accende il link dell'invito.
    -- =========================================================
    v_utente := script.fn_utente_di_sessione('anagrafiche.fn_togli_revoca_veste');

    IF p_identita_id IS NULL OR p_identita_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_togli_revoca_veste', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('identita_id', p_identita_id),
            NULL::uuid,
            'anagrafiche.fn_togli_revoca_veste',
            'veste mancante');
    END IF;

    SELECT * INTO v_riga
      FROM anagrafiche.identita_digitali idg
     WHERE idg.id = p_identita_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_togli_revoca_veste', 'E_VESTE_NON_TROVATA',
            jsonb_build_object('identita_id', p_identita_id),
            NULL::uuid,
            p_identita_id::text);
    END IF;

    PERFORM anagrafiche.fn_guard_gestione_veste(v_utente, v_riga.ruolo_applicativo);

    UPDATE anagrafiche.identita_digitali idg
       SET revocata_at         = NULL,
           revocata_da_user_id = NULL
     WHERE idg.auth_user_id      = v_riga.auth_user_id
       AND idg.soggetto_ruolo_id = v_riga.soggetto_ruolo_id
       AND idg.ruolo_applicativo = v_riga.ruolo_applicativo
       AND idg.revocata_at IS NOT NULL;
    GET DIAGNOSTICS v_tolti = ROW_COUNT;

    RETURN v_tolti > 0;
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_togli_revoca_veste(p_identita_id bigint)
IS 'Verbo: il nuovo invito dell''amministratore toglie il segno della revoca (revocata_at, revocata_da_user_id) da tutte le vesti della coppia (credenziale, ruolo anagrafico, veste) di p_identita_id. La veste resta spenta: la accende il link dell''invito (anagrafiche.fn_accendi_veste). Il backend la chiama nella transazione in cui scrive il token. Ritorna se ha tolto un segno; idempotente. Permesso: anagrafiche.fn_guard_gestione_veste, per tipo di veste, dall''utente della sessione e anche quando non c''e'' niente da togliere (E_PERMESSO_NEGATO). Veste assente: E_VESTE_NON_TROVATA; id NULL o non positivo: E_SCRIPT_CHIAMATA_NON_VALIDA. SECURITY DEFINER, search_path fissato: il segno lo tocca solo il proprietario della tabella.';
```

</div>

---
{% include-markdown "signature-core.md" %}
