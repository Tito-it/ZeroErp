{% include-markdown "it/dbzero/anagrafiche/manual/fn_accendi_veste.md" %}
# ⚙️ Funzione `fn_accendi_veste`

```sql
CREATE FUNCTION fn_accendi_veste(p_identita_id bigint, p_auth_user_id integer, p_vesti config.ruolo_applicativo[])
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_accendi_veste(p_identita_id bigint, p_auth_user_id integer, p_vesti config.ruolo_applicativo[] DEFAULT NULL::config.ruolo_applicativo[])
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_attivo anagrafiche.identita_digitali.attivo%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Accendere la veste p_identita_id della credenziale
    --   p_auth_user_id, se e' fra p_vesti (NULL = qualunque).
    --   Ritorna true se la veste c'e' (accesa ora o gia'),
    --   false se non c'e' (o non e' di quella credenziale, o
    --   non e' fra le vesti ammesse).
    --
    -- Regole:
    --   - argomenti NULL: E_SCRIPT_CHIAMATA_NON_VALIDA;
    --   - gia' accesa: nessuna scrittura.
    -- =========================================================
    IF p_identita_id IS NULL OR p_auth_user_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_accendi_veste', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('identita_id',  p_identita_id,
                               'auth_user_id', p_auth_user_id),
            NULL::uuid,
            'anagrafiche.fn_accendi_veste',
            'veste o credenziale mancanti');
    END IF;

    SELECT idg.attivo
      INTO v_attivo
      FROM anagrafiche.identita_digitali idg
     WHERE idg.id = p_identita_id
       AND idg.auth_user_id = p_auth_user_id
       AND (p_vesti IS NULL OR idg.ruolo_applicativo = ANY (p_vesti));

    IF NOT FOUND THEN
        RETURN false;
    END IF;

    IF NOT v_attivo THEN
        UPDATE anagrafiche.identita_digitali idg
           SET attivo = true
         WHERE idg.id = p_identita_id;
    END IF;

    RETURN true;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_accendi_veste(p_identita_id bigint, p_auth_user_id integer, p_vesti config.ruolo_applicativo[])
IS 'Accende la veste p_identita_id (anagrafiche.identita_digitali.attivo = true) della credenziale p_auth_user_id, se e'' fra le vesti p_vesti (NULL = qualunque). Ritorna true se la veste c''e'' (accesa adesso, o gia'' accesa e allora senza scrivere), false se non c''e'', non e'' di quella credenziale o non e'' fra le vesti ammesse. Argomenti NULL: E_SCRIPT_CHIAMATA_NON_VALIDA. Una veste revocata non si accende: la ferma anagrafiche.trgfn_identita_digitali_guard_revoca (E_VESTE_REVOCATA). Coerenza, natura della credenziale, unicita'' della veste accesa e sincronizzazione di auth_user.is_active: i trigger della tabella. SECURITY DEFINER, search_path fissato, senza guard di permesso: la chiamano richieste senza un amministratore, il link dell''invito (anonimo: il controllo e'' il token, che il backend consuma nella stessa transazione) e la persona che accende una propria veste. E'' la sede unica dell''accensione: la usano anche il verbo dei dati di sviluppo, anagrafiche.fn_crea_primo_amministratore e dbops.fn_pgtap_crea_operatore_umano.';
```

</div>

---
{% include-markdown "signature-core.md" %}
