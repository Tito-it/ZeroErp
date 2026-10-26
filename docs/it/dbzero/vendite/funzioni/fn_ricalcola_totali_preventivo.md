{% include-markdown "it/dbzero/vendite/manual/fn_ricalcola_totali_preventivo.md" %}
# ⚙️ Funzione `fn_ricalcola_totali_preventivo`

```sql
CREATE FUNCTION fn_ricalcola_totali_preventivo(p_preventivo_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ricalcola_totali_preventivo(p_preventivo_id bigint)
 RETURNS TABLE(preventivo_id bigint, totale_imponibile numeric, totale_iva numeric, totale_documento numeric)
 LANGUAGE plpgsql
AS $function$
-- Scopo: ricalcolare i totali della testata preventivo a
-- partire dal riepilogo IVA aggregato (fiscalmente corretto).
-- La fn invoca prima fn_ricalcola_riepilogo_iva_preventivo
-- (single source of truth) e poi somma le righe del
-- riepilogo per ottenere totale_imponibile, totale_iva,
-- totale_documento.
--
-- Equivalenza con fatture: i totali coincidono con quelli
-- della fattura emessa dallo stesso preventivo (a parita'
-- di righe e stato emittente). Il bug "differenza centesimi
-- preventivo vs fattura" e' risolto strutturalmente.
DECLARE
    v_imponibile vendite.preventivi.totale_imponibile%TYPE;
    v_iva        vendite.preventivi.totale_iva%TYPE;
    v_totale     vendite.preventivi.totale_documento%TYPE;
BEGIN
    IF p_preventivo_id IS NULL OR p_preventivo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'fn_ricalcola_totali_preventivo',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('param', 'p_preventivo_id', 'value', p_preventivo_id),
            NULL::uuid,
            'p_preventivo_id = ' || COALESCE(p_preventivo_id::text, 'NULL')
        );
    END IF;

    -- Step 1: ricalcola riepilogo IVA aggregato.
    PERFORM vendite.fn_ricalcola_riepilogo_iva_preventivo(p_preventivo_id);

    -- Step 2: totali derivati da SUM riepiloghi.
    SELECT
        COALESCE(SUM(ri.imponibile), 0),
        COALESCE(SUM(ri.imposta),    0)
      INTO v_imponibile, v_iva
      FROM vendite.preventivi_riepiloghi_iva ri
     WHERE ri.preventivo_id = p_preventivo_id;

    v_totale := v_imponibile + v_iva;

    -- Step 3: aggiorna testata.
    UPDATE vendite.preventivi p
       SET totale_imponibile = v_imponibile,
           totale_iva        = v_iva,
           totale_documento  = v_totale
     WHERE p.id = p_preventivo_id;

    RETURN QUERY
    SELECT p_preventivo_id, v_imponibile, v_iva, v_totale;
END
$function$

COMMENT ON FUNCTION vendite.fn_ricalcola_totali_preventivo(p_preventivo_id bigint)
IS 'Wrapper sopra fn_ricalcola_riepilogo_iva_preventivo. Ricalcola riepilogo IVA aggregato (fiscalmente corretto), poi somma le righe del riepilogo per i totali testata. Pattern allineato a fatture, garantisce coerenza preventivo <-> fattura emessa. Firma e RETURNS TABLE usano %TYPE su vendite.preventivi.* (tipi concreti risolti a bigint/numeric).';
```

</div>

---
{% include-markdown "signature-core.md" %}
