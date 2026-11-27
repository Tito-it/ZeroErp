# ⚙️ Funzione `fn_pgtap_cancella_veste`

```sql
CREATE FUNCTION fn_pgtap_cancella_veste(p_identita_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_cancella_veste(p_identita_id bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo:
--   Fixture dei test: togliere la veste p_identita_id per costruire il caso
--   dopo, solo dove sono ammessi i dati di sviluppo. Nessun verbo cancella
--   una veste.
--
-- Regole:
--   - in PRODUZIONE: E_DATI_DI_SVILUPPO_IN_PRODUZIONE, prima di ogni scrittura;
--   - id NULL o non positivo: E_SCRIPT_CHIAMATA_NON_VALIDA;
--   - veste assente: E_VESTE_NON_TROVATA;
--   - una veste revocata non si cancella: E_VESTE_REVOCA_SOLO_DAL_VERBO;
--   - le altre regole della tabella: i suoi trigger.
DECLARE
    v_ambiente dbops.installazione.ambiente%TYPE;
    v_revocata anagrafiche.identita_digitali.revocata_at%TYPE;
BEGIN
    v_ambiente := script.fn_ambiente_installazione();
    IF NOT dbops.fn_dati_di_sviluppo_ammessi_su_valori(v_ambiente) THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'dbops.fn_pgtap_cancella_veste',
            'E_DATI_DI_SVILUPPO_IN_PRODUZIONE',
            jsonb_build_object('ambiente', v_ambiente),
            NULL::uuid,
            v_ambiente);
    END IF;

    IF p_identita_id IS NULL OR p_identita_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'dbops.fn_pgtap_cancella_veste', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('identita_id', p_identita_id),
            NULL::uuid,
            'dbops.fn_pgtap_cancella_veste',
            'veste mancante');
    END IF;

    SELECT idg.revocata_at
      INTO v_revocata
      FROM anagrafiche.identita_digitali idg
     WHERE idg.id = p_identita_id
       FOR UPDATE;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'dbops.fn_pgtap_cancella_veste', 'E_VESTE_NON_TROVATA',
            jsonb_build_object('identita_id', p_identita_id),
            NULL::uuid,
            p_identita_id::text);
    END IF;

    IF v_revocata IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'dbops.fn_pgtap_cancella_veste', 'E_VESTE_REVOCA_SOLO_DAL_VERBO',
            jsonb_build_object('identita_id', p_identita_id),
            NULL::uuid, 'DELETE');
    END IF;

    DELETE FROM anagrafiche.identita_digitali idg
     WHERE idg.id = p_identita_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_cancella_veste(p_identita_id bigint)
IS 'Fixture dei test: toglie la veste p_identita_id per costruire il caso dopo (per esempio una veste spenta sola, o una credenziale con una veste sola). Nessun verbo cancella una veste: e'' solo una fixture. I trigger della tabella scattano come per ogni cancellazione, e una veste revocata non si cancella (E_VESTE_REVOCA_SOLO_DAL_VERBO). SECURITY DEFINER ed eseguibile dall''applicazione, che non cancella identita_digitali direttamente: parte solo dove sono ammessi i dati di sviluppo (dbops.fn_dati_di_sviluppo_ammessi_su_valori sull''ambiente dell''installazione), e in PRODUZIONE solleva E_DATI_DI_SVILUPPO_IN_PRODUZIONE. id NULL o non positivo: E_SCRIPT_CHIAMATA_NON_VALIDA; veste assente: E_VESTE_NON_TROVATA. La gemella che cambia stato e forma e'' dbops.fn_pgtap_imposta_veste.';
```

</div>

---
{% include-markdown "signature-core.md" %}
