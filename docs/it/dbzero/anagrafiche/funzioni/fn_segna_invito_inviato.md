# ⚙️ Funzione `fn_segna_invito_inviato`

```sql
CREATE FUNCTION fn_segna_invito_inviato(p_identita_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_segna_invito_inviato(p_identita_id bigint)
 RETURNS timestamp with time zone
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente  anagrafiche.identita_digitali.revocata_da_user_id%TYPE;
    v_ruolo   anagrafiche.identita_digitali.ruolo_applicativo%TYPE;
    v_inviato anagrafiche.identita_digitali.invito_inviato_at%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: l'amministratore che ha spedito la mail dell'invito
    --   lo segna sulla veste p_identita_id (invito_inviato_at).
    --   Ritorna il momento scritto.
    -- =========================================================
    v_utente := script.fn_utente_di_sessione('anagrafiche.fn_segna_invito_inviato');

    IF p_identita_id IS NULL OR p_identita_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_segna_invito_inviato', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('identita_id', p_identita_id),
            NULL::uuid,
            'anagrafiche.fn_segna_invito_inviato',
            'veste mancante');
    END IF;

    SELECT idg.ruolo_applicativo
      INTO v_ruolo
      FROM anagrafiche.identita_digitali idg
     WHERE idg.id = p_identita_id
       FOR UPDATE;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_segna_invito_inviato', 'E_VESTE_NON_TROVATA',
            jsonb_build_object('identita_id', p_identita_id),
            NULL::uuid,
            p_identita_id::text);
    END IF;

    PERFORM anagrafiche.fn_guard_gestione_veste(v_utente, v_ruolo);

    UPDATE anagrafiche.identita_digitali idg
       SET invito_inviato_at = now()
     WHERE idg.id = p_identita_id
    RETURNING idg.invito_inviato_at INTO v_inviato;

    RETURN v_inviato;
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_segna_invito_inviato(p_identita_id bigint)
IS 'Verbo: segna sulla veste p_identita_id che la mail dell''invito e'' partita (invito_inviato_at = now()) e ritorna il momento scritto. Lo chiama chi ha spedito l''invito, dopo l''invio. Non tocca attivo ne'' il segno della revoca. Lo legge script.fn_stato_veste: un token pendente con la mail partita e'' PENDING, senza e'' NON_SPEDITO. Permesso: anagrafiche.fn_guard_gestione_veste, per tipo di veste, sull''utente della sessione (E_PERMESSO_NEGATO). Veste assente: E_VESTE_NON_TROVATA; id NULL o non positivo: E_SCRIPT_CHIAMATA_NON_VALIDA. SECURITY DEFINER, search_path fissato: l''applicazione non scrive identita_digitali direttamente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
