# ⚙️ Funzione `fn_lotto_natura_dal_segno`

```sql
CREATE FUNCTION fn_lotto_natura_dal_segno(p_lotto_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_lotto_natura_dal_segno(p_lotto_id bigint)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- Scopo: un documento che somma negativo e' una nota di credito (D-1). Le
--   attivita' FATTURA del lotto, raggruppate per chiave di testata, si
--   sommano; nei gruppi negativi diventano NOTA_CREDITO, con la marca
--   natura_dal_segno. Rieseguibile. Regola completa nell'intestazione del
--   changeSet 20261031-45.
DECLARE
    v_batch   vendite.fatturazione_lotti.lock_batch_id%TYPE;
    v_fattura config.nature_doc_fiscale.id%TYPE;
    v_nc      config.nature_doc_fiscale.id%TYPE;
    -- CONTEGGIO delle attivita' battezzate nota di credito.
    v_n       integer;
BEGIN
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_lotto_natura_dal_segno',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_lotto_id', p_lotto_id),
            NULL::uuid, 'vendite.fn_lotto_natura_dal_segno',
            'p_lotto_id (obbligatorio, maggiore di zero)');
    END IF;

    SELECT fl.lock_batch_id INTO v_batch
      FROM vendite.fatturazione_lotti fl
     WHERE fl.id = p_lotto_id;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_lotto_natura_dal_segno', 'E_LOTTO_NON_TROVATO',
            jsonb_build_object('lotto_id', p_lotto_id),
            NULL::uuid, p_lotto_id::text);
    END IF;

    v_fattura := config.fn_get_natura_doc_fiscale_id('FATTURA');
    v_nc      := config.fn_get_natura_doc_fiscale_id('NOTA_CREDITO');
    IF v_fattura IS NULL OR v_nc IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_lotto_natura_dal_segno', 'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'config.nature_doc_fiscale'),
            NULL::uuid, 'natura FATTURA o NOTA_CREDITO (config.nature_doc_fiscale)');
    END IF;

    -- 0. Rieseguibile: le marche del lotto si ritirano, e si decide di nuovo.
    UPDATE vendite.attivita_fatturabili a
       SET natura_doc_id    = v_fattura,
           natura_dal_segno = false
     WHERE a.lock_batch_id = v_batch
       AND a.fatturato IS FALSE
       AND COALESCE(a.lock_in_fatturazione, false) IS TRUE
       AND a.natura_dal_segno IS TRUE;

    -- 1. I gruppi delle attivita' FATTURA, per chiave di testata (la stessa
    --    funzione delle testate), e il loro totale.
    WITH att AS (
        SELECT a.id, vendite.fn_build_fattura_key(a.id) AS chiave,
               a.quantita * a.prezzo_unitario AS importo
          FROM vendite.attivita_fatturabili a
         WHERE a.lock_batch_id = v_batch
           AND a.fatturato IS FALSE
           AND COALESCE(a.lock_in_fatturazione, false) IS TRUE
           AND a.natura_doc_id = v_fattura
    ),
    negativi AS (
        SELECT att.chiave FROM att GROUP BY att.chiave HAVING sum(att.importo) < 0
    )
    UPDATE vendite.attivita_fatturabili a
       SET natura_doc_id    = v_nc,
           natura_dal_segno = true
      FROM att
      JOIN negativi n ON n.chiave = att.chiave
     WHERE a.id = att.id;
    GET DIAGNOSTICS v_n = ROW_COUNT;

    RETURN v_n;
END;
$function$

COMMENT ON FUNCTION vendite.fn_lotto_natura_dal_segno(p_lotto_id bigint)
IS 'D-1: un documento che somma negativo e'' una nota di credito. Le attivita'' FATTURA del lotto (lucchetto del lotto, non fatturate), raggruppate per chiave di testata (vendite.fn_build_fattura_key, la stessa delle testate), si sommano (quantita'' x prezzo); nei gruppi a totale negativo diventano NOTA_CREDITO con la marca natura_dal_segno, e la testata nasce nota di credito col suo registro e la sua serie. Il documento misto a totale negativo e'' una nota di credito con dentro la riga positiva; a totale zero o positivo resta FATTURA. Le attivita'' nate NOTA_CREDITO (accredito del reso) sono un gruppo loro e non si toccano (D-1-bis). Rieseguibile: prima ritira le marche del lotto. Si chiama una volta per lotto, prima delle testate (giro del backend). Ritorna quante attivita'' sono diventate nota di credito. SECURITY INVOKER. Nasce il 2026-10-31 (20261031-45), brief-db-contratto-righe-periodiche-in-commessa §7.7 (L17).';
```

</div>

---
{% include-markdown "signature-core.md" %}
