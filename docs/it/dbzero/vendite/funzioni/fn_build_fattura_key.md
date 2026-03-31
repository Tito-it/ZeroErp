{% include-markdown "it/dbzero/vendite/manual/fn_build_fattura_key.md" %}
# ⚙️ Funzione `fn_build_fattura_key`

```sql
CREATE FUNCTION fn_build_fattura_key(p_attivita_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_build_fattura_key(p_attivita_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ba_id              anagrafiche.billing_account.id%TYPE;
    v_ba_fattura_id      anagrafiche.billing_account.id%TYPE;
    v_tipo_doc_fiscale_id config.tipi_doc_fiscale.id%TYPE;
    v_valuta_id          config.valute.id%TYPE;
    v_utility_id         config.utilities.id%TYPE;
    v_emittente_id       anagrafiche.soggetti_ruoli.id%TYPE;
    v_reseller_id        anagrafiche.soggetti_ruoli.id%TYPE;
    v_registro_id        vendite.registri_fatturazione.id%TYPE;
BEGIN
    -- Guard: parametro obbligatorio
    IF p_attivita_id IS NULL OR p_attivita_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_build_fattura_key', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_attivita_id', 'valore', p_attivita_id),
            NULL::uuid, 'p_attivita_id obbligatorio e > 0'
        );
    END IF;

    -- Recupera BA, tipo doc, valuta, utility dall'attivita'
    SELECT a.billing_account_id,
           COALESCE(ba.parent_account_id, a.billing_account_id),
           a.tipo_doc_fiscale_id,
           a.valuta_id,
           ba.utility_id
      INTO v_ba_id, v_ba_fattura_id, v_tipo_doc_fiscale_id, v_valuta_id, v_utility_id
      FROM vendite.attivita_fatturabili a
      JOIN anagrafiche.billing_account ba ON ba.id = a.billing_account_id
     WHERE a.id = p_attivita_id;

    IF v_ba_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_build_fattura_key', 'E_VALORE_MANCANTE',
            jsonb_build_object('attivita_id', p_attivita_id),
            NULL::uuid, concat('attivita o BA non trovati per id ', p_attivita_id)
        );
    END IF;

    -- Emittente dal mapping BA → emittente fiscale
    v_emittente_id := anagrafiche.fn_get_emittente_fiscale_id(v_ba_fattura_id);

    -- Reseller dal mapping BA → reseller (opzionale)
    SELECT rb.reseller_soggetto_ruolo_id
      INTO v_reseller_id
      FROM anagrafiche.resellers_billing_account rb
     WHERE rb.billing_account_id = v_ba_fattura_id
     ORDER BY rb.id
     LIMIT 1;

    -- Registro dal tipo documento
    v_registro_id := vendite.fn_get_registro_id(v_tipo_doc_fiscale_id);

    RETURN jsonb_build_object(
        'billing_account_id', v_ba_fattura_id,
        'tipo_doc_fiscale_id', v_tipo_doc_fiscale_id,
        'valuta_id', v_valuta_id,
        'emittente_soggetto_ruolo_id', v_emittente_id,
        'reseller_soggetto_ruolo_id', v_reseller_id,
        'utility_id', v_utility_id,
        'registro_id', v_registro_id
    );
END;
$function$

COMMENT ON FUNCTION vendite.fn_build_fattura_key(p_attivita_id bigint)
IS 'Chiave logica aggregazione documento da attivita_fatturabili. BA padre se presente, emittente, reseller, registro.';
```

---
{% include-markdown "signature-core.md" %}
