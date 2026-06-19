{% include-markdown "it/dbzero/vendite/manual/fn_numera_fattura_opz_emessa.md" %}
# ⚙️ Funzione `fn_numera_fattura_opz_emessa`

```sql
CREATE FUNCTION fn_numera_fattura_opz_emessa(p_fattura_id bigint, p_set_emessa boolean, p_codice_interno_emessa character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_numera_fattura_opz_emessa(p_fattura_id bigint, p_set_emessa boolean DEFAULT true, p_codice_interno_emessa character varying DEFAULT 'EMESSA'::character varying)
 RETURNS TABLE(registro_id bigint, anno smallint, mese smallint, serie character varying, numero bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_is_numbered  BOOLEAN;
    v_reset        vendite.registri_fatturazione.reset_policy%TYPE;
    v_data         vendite.fatture.data%TYPE;
    v_registro_id  vendite.fatture.registro_id%TYPE;
    v_anno         vendite.fatture.anno%TYPE;
    v_mese         SMALLINT;
    v_serie        vendite.fatture.serie%TYPE;
    v_numero       vendite.fatture.numero%TYPE;
    v_stato_emessa_id config.stati_doc_fiscale.id%TYPE;
BEGIN
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_numera_fattura_opz_emessa', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id), NULL::uuid, 'p_fattura_id obbligatorio e > 0');
    END IF;

    IF p_set_emessa IS TRUE AND (p_codice_interno_emessa IS NULL OR btrim(p_codice_interno_emessa) = '') THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_numera_fattura_opz_emessa', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_codice_interno_emessa', 'valore', p_codice_interno_emessa),
            NULL::uuid, 'p_codice_interno_emessa obbligatorio se p_set_emessa=true');
    END IF;

    -- Lock riga fattura (solo la riga fattura, alias f)
    SELECT f.numero IS NOT NULL, f.data, f.registro_id, r.reset_policy, f.anno, f.serie, f.numero
      INTO v_is_numbered, v_data, v_registro_id, v_reset, v_anno, v_serie, v_numero
      FROM vendite.fatture f
      JOIN vendite.registri_fatturazione r ON r.id = f.registro_id
     WHERE f.id = p_fattura_id FOR UPDATE OF f;

    IF v_registro_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_numera_fattura_opz_emessa', 'E_FATTURA_NON_TROVATA',
            jsonb_build_object('fattura_id', p_fattura_id), NULL::uuid, p_fattura_id::text);
    END IF;

    -- Idempotente: se gia' numerata ritorna valori correnti
    IF v_is_numbered THEN
        v_mese := CASE WHEN v_reset = 'MENSILE' THEN EXTRACT(MONTH FROM v_data)::SMALLINT ELSE NULL END;
        RETURN QUERY SELECT v_registro_id, v_anno, v_mese, v_serie, v_numero;
        RETURN;
    END IF;

    -- Assegna numero
    SELECT t.registro_id, t.anno, t.mese, t.serie, t.numero
      INTO v_registro_id, v_anno, v_mese, v_serie, v_numero
      FROM vendite.fn_assign_numero_fattura(p_fattura_id) AS t;

    -- Opzionale: stato EMESSA
    IF p_set_emessa THEN
        SELECT id INTO v_stato_emessa_id
          FROM config.stati_doc_fiscale WHERE codice_interno = p_codice_interno_emessa LIMIT 1;

        IF v_stato_emessa_id IS NOT NULL THEN
            UPDATE vendite.fatture SET stato_doc_fiscale_id = COALESCE(stato_doc_fiscale_id, v_stato_emessa_id) WHERE id = p_fattura_id;
        END IF;
    END IF;

    RETURN QUERY SELECT v_registro_id, v_anno, v_mese, v_serie, v_numero;
END;
$function$

COMMENT ON FUNCTION vendite.fn_numera_fattura_opz_emessa(p_fattura_id bigint, p_set_emessa boolean, p_codice_interno_emessa character varying)
IS 'Assegna numero fattura (idempotente) e opzionalmente imposta stato EMESSA.';
```

---
{% include-markdown "signature-core.md" %}
