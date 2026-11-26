# ⚙️ Funzione `fn_revoca_veste`

```sql
CREATE FUNCTION fn_revoca_veste(p_identita_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_revoca_veste(p_identita_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente anagrafiche.identita_digitali.revocata_da_user_id%TYPE;
    v_ruolo  anagrafiche.identita_digitali.ruolo_applicativo%TYPE;
    v_attivo anagrafiche.identita_digitali.attivo%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: l'amministratore revoca la veste p_identita_id:
    --   la spegne e ci scrive quando e chi. Ritorna se era
    --   accesa prima della chiamata.
    -- =========================================================
    v_utente := script.fn_utente_di_sessione('anagrafiche.fn_revoca_veste');

    IF p_identita_id IS NULL OR p_identita_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_revoca_veste', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('identita_id', p_identita_id),
            NULL::uuid,
            'anagrafiche.fn_revoca_veste',
            'veste mancante');
    END IF;

    SELECT idg.ruolo_applicativo, idg.attivo
      INTO v_ruolo, v_attivo
      FROM anagrafiche.identita_digitali idg
     WHERE idg.id = p_identita_id
       FOR UPDATE;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_revoca_veste', 'E_VESTE_NON_TROVATA',
            jsonb_build_object('identita_id', p_identita_id),
            NULL::uuid,
            p_identita_id::text);
    END IF;

    PERFORM anagrafiche.fn_guard_gestione_veste(v_utente, v_ruolo);

    UPDATE anagrafiche.identita_digitali idg
       SET attivo              = false,
           revocata_at         = COALESCE(idg.revocata_at, now()),
           revocata_da_user_id = COALESCE(idg.revocata_da_user_id, v_utente)
     WHERE idg.id = p_identita_id
       AND (idg.attivo OR idg.revocata_at IS NULL);

    RETURN v_attivo;
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_revoca_veste(p_identita_id bigint)
IS 'Verbo: l''amministratore revoca la veste p_identita_id. La spegne (attivo = false) e ci scrive il segno della revoca: revocata_at e revocata_da_user_id, l''utente della sessione (script.fn_utente_di_sessione). Mette il segno anche su una veste gia'' spenta, per esempio con l''invito pendente; su una veste gia'' revocata tiene il segno di prima. Ritorna se la veste era accesa prima della chiamata. Permesso: anagrafiche.fn_guard_gestione_veste, per tipo di veste (E_PERMESSO_NEGATO). Veste assente: E_VESTE_NON_TROVATA; id NULL o non positivo: E_SCRIPT_CHIAMATA_NON_VALIDA. Una veste revocata non si riaccende finche'' anagrafiche.fn_togli_revoca_veste non toglie il segno (anagrafiche.trgfn_identita_digitali_guard_revoca). Non chiude sessioni ne'' token: lo fa il backend nella stessa transazione. SECURITY DEFINER, search_path fissato: il segno lo scrive solo il proprietario della tabella.';
```

</div>

---
{% include-markdown "signature-core.md" %}
