{% include-markdown "it/dbzero/script/manual/trgfn_righe_guard_esclusione_senza_dati.md" %}
# ⚙️ Funzione `trgfn_righe_guard_esclusione_senza_dati`

```sql
CREATE FUNCTION trgfn_righe_guard_esclusione_senza_dati()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_righe_guard_esclusione_senza_dati()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: rifiutare una riga ESCLUSIONE (contratto o offerta) che
--   porta un dato di vendita. L'esclusione dice solo «questo
--   articolo non si vende»: i dieci campi restano vuoti.
-- Uso:   BEFORE INSERT FOR EACH ROW
--        WHEN (NEW.tipo_eccezione = 'ESCLUSIONE'), fascia _a10_,
--        su vendite.contratti_righe e
--        vendite.offerte_commerciali_eccezioni.
-- TG_ARGV[0]: colonna del documento padre ('contratto_id',
--   'offerta_id'), solo per il contesto dell'errore.
-- ⭐ L'elenco e' quello dei CHECK chk_*_esclusione_senza_dati,
--   nello stesso ordine: il primo valorizzato e' il `campo`.
DECLARE
    c_dati CONSTANT text[] := ARRAY[
        'prezzo_unitario', 'quantita', 'qta_operativa',
        'uom_operativa_id', 'factor_to_base', 'tipo_erogazione',
        'fonte_quantita_attesa', 'periodicita',
        'generazione_canone', 'competenza_canone'];
    v_col_padre text := TG_ARGV[0];
    v_riga      jsonb := to_jsonb(NEW);
    v_valorizzati text[];
BEGIN
    SELECT array_agg(d.col ORDER BY d.pos)
      INTO v_valorizzati
      FROM unnest(c_dati) WITH ORDINALITY AS d(col, pos)
     WHERE jsonb_typeof(v_riga -> d.col) IS DISTINCT FROM 'null'
       AND v_riga ? d.col;

    IF v_valorizzati IS NULL THEN
        RETURN NEW;
    END IF;

    PERFORM script.fn_log_and_raise_error(
        'vendite',
        TG_NAME::text,
        'E_RIGA_ESCLUSIONE_CON_DATI',
        jsonb_build_object(
            'campo',       v_valorizzati[1],
            'colonne',     to_jsonb(v_valorizzati),
            'riga_id',     NEW.id,
            v_col_padre,   v_riga -> v_col_padre,
            'articolo_id', NEW.articolo_id),
        NEW.tx_id,
        VARIADIC ARRAY[]::text[]);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_righe_guard_esclusione_senza_dati()
IS 'Guard: una riga ESCLUSIONE di vendite.contratti_righe o di vendite.offerte_commerciali_eccezioni non porta dati di vendita: prezzo_unitario, quantita, qta_operativa, uom_operativa_id, factor_to_base, tipo_erogazione, fonte_quantita_attesa, periodicita, generazione_canone, competenza_canone restano vuoti (E_RIGA_ESCLUSIONE_CON_DATI, DATO_ERRATO, nessun valore). campo = il primo valorizzato nell''ordine dell''elenco (canale COLUMN), colonne = tutti i valorizzati. Stessa regola e stesso elenco dei CHECK chk_contrighe_esclusione_senza_dati / chk_offerte_eccezioni_esclusione_senza_dati, che restano la rete. TG_ARGV[0] = colonna del padre (contratto_id | offerta_id), solo per il contesto. Trigger _a10_ BEFORE INSERT WHEN (NEW.tipo_eccezione = ''ESCLUSIONE''): l''UPDATE di un''esclusione lo rifiuta il guard _a05_, il cambio di tipo il lock di colonna, ciascuno col suo rimedio. Nasce il 2026-10-04, brief-db-righe-esclusione-solo-non-si-vende (R1, R8; decisione di Tid: «l''esclusione e'' solo non si vende»).';
```

</div>

---
{% include-markdown "signature-core.md" %}
