# ⚙️ Funzione `fn_pgtap_imposta_veste`

```sql
CREATE FUNCTION fn_pgtap_imposta_veste(p_identita_id bigint, p_campi jsonb)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_imposta_veste(p_identita_id bigint, p_campi jsonb)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo:
--   Fixture dei test: mettere la veste p_identita_id nello stato e nella
--   forma del caso (attivo, valido_dal, valido_al, invito_inviato_at,
--   ruolo_applicativo, soggetto_ruolo_id), senza chiedere permessi, solo
--   dove sono ammessi i dati di sviluppo.
--
-- Regole:
--   - in PRODUZIONE: E_DATI_DI_SVILUPPO_IN_PRODUZIONE, prima di ogni scrittura;
--   - id NULL o non positivo, p_campi non oggetto o vuoto, una chiave fuori
--     elenco: E_SCRIPT_CHIAMATA_NON_VALIDA;
--   - veste assente: E_VESTE_NON_TROVATA;
--   - una veste revocata non cambia tipo ne' ruolo anagrafico:
--     E_VESTE_REVOCA_SOLO_DAL_VERBO (il guard della tabella lo lascia al
--     proprietario, e questa funzione lo e');
--   - le altre regole della tabella: i suoi trigger.
DECLARE
    c_ammesse  CONSTANT text[] := ARRAY['attivo', 'valido_dal', 'valido_al', 'invito_inviato_at',
                                        'ruolo_applicativo', 'soggetto_ruolo_id'];
    c_coppia   CONSTANT text[] := ARRAY['ruolo_applicativo', 'soggetto_ruolo_id'];
    v_ambiente dbops.installazione.ambiente%TYPE;
    v_fuori    text[];  -- chiavi di p_campi: nomi, non una colonna
    v_revocata anagrafiche.identita_digitali.revocata_at%TYPE;
BEGIN
    -- Il cancello: solo dove sono ammessi i dati di sviluppo.
    v_ambiente := script.fn_ambiente_installazione();
    IF NOT dbops.fn_dati_di_sviluppo_ammessi_su_valori(v_ambiente) THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'dbops.fn_pgtap_imposta_veste',
            'E_DATI_DI_SVILUPPO_IN_PRODUZIONE',
            jsonb_build_object('ambiente', v_ambiente),
            NULL::uuid,
            v_ambiente);
    END IF;

    IF p_identita_id IS NULL OR p_identita_id <= 0
       OR p_campi IS NULL OR jsonb_typeof(p_campi) <> 'object'
       OR p_campi = '{}'::jsonb THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'dbops.fn_pgtap_imposta_veste', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('identita_id', p_identita_id, 'campi', p_campi),
            NULL::uuid,
            'dbops.fn_pgtap_imposta_veste',
            'veste o colonne da cambiare mancanti');
    END IF;

    SELECT array_agg(k ORDER BY k)
      INTO v_fuori
      FROM jsonb_object_keys(p_campi) k
     WHERE k <> ALL (c_ammesse);

    IF v_fuori IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'dbops.fn_pgtap_imposta_veste', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('identita_id', p_identita_id,
                               'fuori_elenco', to_jsonb(v_fuori),
                               'ammesse', to_jsonb(c_ammesse)),
            NULL::uuid,
            'dbops.fn_pgtap_imposta_veste',
            'colonne non ammesse: ' || array_to_string(v_fuori, ', '));
    END IF;

    SELECT idg.revocata_at
      INTO v_revocata
      FROM anagrafiche.identita_digitali idg
     WHERE idg.id = p_identita_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'dbops.fn_pgtap_imposta_veste', 'E_VESTE_NON_TROVATA',
            jsonb_build_object('identita_id', p_identita_id),
            NULL::uuid,
            p_identita_id::text);
    END IF;

    IF v_revocata IS NOT NULL AND p_campi ?| c_coppia THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'dbops.fn_pgtap_imposta_veste', 'E_VESTE_REVOCA_SOLO_DAL_VERBO',
            jsonb_build_object('identita_id', p_identita_id, 'campi', p_campi),
            NULL::uuid, 'UPDATE');
    END IF;

    PERFORM script.fn_scrivi_riga_da_jsonb(
        'anagrafiche.identita_digitali'::regclass,
        p_campi,
        jsonb_build_object('id', p_identita_id));
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_imposta_veste(p_identita_id bigint, p_campi jsonb)
IS 'Fixture dei test (pgTAP e test Django sul database vero): mette la veste p_identita_id nello stato e nella forma del caso, con le sole colonne nominate in p_campi fra attivo, valido_dal, valido_al, invito_inviato_at, ruolo_applicativo e soggetto_ruolo_id (una chiave col valore null porta la colonna a NULL). Scrive con script.fn_scrivi_riga_da_jsonb, e i trigger della tabella scattano come per ogni scrittura: una veste revocata non si accende nemmeno da qui. Il segno della revoca non si scrive da qui: lo scrivono anagrafiche.fn_revoca_veste e anagrafiche.fn_togli_revoca_veste; e una veste revocata non cambia tipo ne'' ruolo anagrafico (E_VESTE_REVOCA_SOLO_DAL_VERBO). SECURITY DEFINER ed eseguibile dall''applicazione, che non aggiorna identita_digitali direttamente: per questo parte solo dove sono ammessi i dati di sviluppo (dbops.fn_dati_di_sviluppo_ammessi_su_valori sull''ambiente dell''installazione), e in PRODUZIONE solleva E_DATI_DI_SVILUPPO_IN_PRODUZIONE. id NULL o non positivo, p_campi vuoto o con una chiave fuori elenco: E_SCRIPT_CHIAMATA_NON_VALIDA; veste assente: E_VESTE_NON_TROVATA. La gemella che cancella e'' dbops.fn_pgtap_cancella_veste.';
```

</div>

---
{% include-markdown "signature-core.md" %}
