{% include-markdown "it/dbzero/vendite/manual/fn_reset_fondi_fattura.md" %}
# ⚙️ Funzione `fn_reset_fondi_fattura`

```sql
CREATE FUNCTION fn_reset_fondi_fattura(p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_reset_fondi_fattura(p_fattura_id bigint)
 RETURNS TABLE(updated_source integer, deleted_fondi integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_updated_source INTEGER := 0;
    v_deleted_fondi  INTEGER := 0;
    v_stato_contabile_chiusa_id pagamenti.vendite_contabili_stati.id%TYPE;
BEGIN
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_fondi_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id), NULL::uuid, 'p_fattura_id obbligatorio e > 0');
    END IF;

    SELECT s.id INTO v_stato_contabile_chiusa_id
      FROM pagamenti.vendite_contabili_stati s WHERE s.codice_interno = 'CHIUSA' AND s.attivo IS TRUE LIMIT 1;

    IF v_stato_contabile_chiusa_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_fondi_fattura', 'E_CONFIG_MANCANTE',
            jsonb_build_object('codice_interno', 'CHIUSA'), NULL::uuid, 'stato contabile CHIUSA non configurato');
    END IF;

    -- Logica CTE invariata dall'originale
    WITH src AS (
        SELECT s.id AS source_id, s.fattura_sorgente_id, fs.numero AS fattura_sorgente_numero, fs.data AS fattura_sorgente_data
          FROM vendite.fatture_fondi_fattura_source s
          JOIN vendite.tipi_fondi_fattura t ON t.id = s.tipo_fondo_fattura_id
          JOIN vendite.fatture fs ON fs.id = s.fattura_sorgente_id
         WHERE s.fattura_figlia_id = p_fattura_id AND s.stato = 'ASSEGNATO' AND t.codice_interno = 'F_F_ADD_ACC'
           FOR UPDATE
    ), bloccate AS (
        SELECT DISTINCT src.source_id, src.fattura_sorgente_id, src.fattura_sorgente_numero, src.fattura_sorgente_data
          FROM src
          JOIN pagamenti.vendite_contabili_righe cr ON cr.attivo IS TRUE AND COALESCE(cr.meta->>'origine', '') = 'FONDO_FATTURA' AND COALESCE(cr.meta->>'fondo_source_id', '') = src.source_id::text
          JOIN pagamenti.vendite_contabili c ON c.id = cr.contabile_id
         WHERE c.stato_id = v_stato_contabile_chiusa_id
    ), warn AS (
        INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta, data_insert, user_insert, data_update, user_update)
        SELECT p_fattura_id, now(), format('Minimo non ripristinabile: gia postato (fattura %s del %s)', COALESCE(b.fattura_sorgente_numero::text, 'N/D'), COALESCE(to_char(b.fattura_sorgente_data, 'YYYY-MM-DD'), 'N/D')),
               'W', FALSE, jsonb_build_object('source_id', b.source_id, 'fattura_sorgente_id', b.fattura_sorgente_id, 'cause', 'CONTABILE_CHIUSA'), now(), current_user, now(), current_user
          FROM bloccate b RETURNING id
    ), ann AS (
        UPDATE vendite.fatture_fondi_fattura_source s SET stato = 'ANNULLATO', data_update = now(), user_update = current_user FROM bloccate b WHERE s.id = b.source_id RETURNING s.id
    ), resettabili AS (
        SELECT s.* FROM src s WHERE NOT EXISTS (SELECT 1 FROM bloccate b WHERE b.source_id = s.source_id)
    ), del_righe AS (
        DELETE FROM pagamenti.vendite_contabili_righe cr USING resettabili r, pagamenti.vendite_contabili c
        WHERE c.id = cr.contabile_id AND COALESCE(cr.meta->>'origine', '') = 'FONDO_FATTURA' AND COALESCE(cr.meta->>'fondo_source_id', '') = r.source_id::text AND c.stato_id IS DISTINCT FROM v_stato_contabile_chiusa_id RETURNING cr.id
    ), upd AS (
        UPDATE vendite.fatture_fondi_fattura_source s SET fattura_figlia_id = NULL, data_assegnazione = NULL, user_assegnazione = NULL, stato = 'DISPONIBILE', data_update = now(), user_update = current_user FROM resettabili r WHERE s.id = r.source_id RETURNING s.id, s.fattura_sorgente_id
    ), del_ff AS (
        DELETE FROM vendite.fatture_fondi_fattura ff USING upd u WHERE ff.fattura_id = p_fattura_id AND ff.riferimento_fattura_id = u.fattura_sorgente_id RETURNING ff.id
    )
    SELECT (SELECT COUNT(*)::INTEGER FROM upd), (SELECT COUNT(*)::INTEGER FROM del_ff) INTO v_updated_source, v_deleted_fondi;

    RETURN QUERY SELECT COALESCE(v_updated_source, 0), COALESCE(v_deleted_fondi, 0);
END;
$function$

COMMENT ON FUNCTION vendite.fn_reset_fondi_fattura(p_fattura_id bigint)
IS 'Reset fondi applicati alla fattura con blocco su contabili CHIUSA e warning.';
```

---
{% include-markdown "signature-core.md" %}
