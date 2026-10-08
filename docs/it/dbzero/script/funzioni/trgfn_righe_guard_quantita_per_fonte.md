# ⚙️ Funzione `trgfn_righe_guard_quantita_per_fonte`

```sql
CREATE FUNCTION trgfn_righe_guard_quantita_per_fonte()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_righe_guard_quantita_per_fonte()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: rifiutare una riga (contratto o offerta) che porta una
--   quantita' con una fonte che non la porta. La fonte dice da dove
--   arriva la quantita' che si fattura: FISSA e' quella della riga,
--   DERIVATA_COMPONENTI la scrive il DB dai componenti; con ogni altra
--   fonte (MANUALE, LETTURE, TIMESHEET) arriva a valle, e sulla riga
--   quantita e qta_operativa restano vuote.
-- Uso:   BEFORE INSERT OR UPDATE FOR EACH ROW
--        WHEN (NEW.tipo_eccezione <> 'ESCLUSIONE'), fascia _a10_,
--        su vendite.contratti_righe e
--        vendite.offerte_commerciali_eccezioni.
-- TG_ARGV[0]: colonna del documento padre ('contratto_id',
--   'offerta_id'), solo per il contesto dell'errore.
-- ⭐ L'elenco e' quello dei CHECK chk_*_quantita_per_fonte: le fonti
--   che PORTANO la quantita'. Una fonte nuova nasce «a valle».
-- Fonte NULL: la riga senza fonte la giudicano il guard d'obbligo e
--   il CHECK dell'esclusione, non questo.
DECLARE
    c_fonti_con_quantita CONSTANT text[] := ARRAY['FISSA', 'DERIVATA_COMPONENTI'];
    v_col_padre   text := TG_ARGV[0];
    v_valorizzati text[];
BEGIN
    IF NEW.fonte_quantita_attesa IS NULL
       OR NEW.fonte_quantita_attesa = ANY (c_fonti_con_quantita) THEN
        RETURN NEW;
    END IF;

    -- qta_operativa per prima: e' l'input del form, e quantita la
    -- deriva trgfn_qta_from_operativa.
    v_valorizzati := array_remove(ARRAY[
        CASE WHEN NEW.qta_operativa IS NOT NULL THEN 'qta_operativa' END,
        CASE WHEN NEW.quantita      IS NOT NULL THEN 'quantita' END], NULL);

    IF cardinality(v_valorizzati) = 0 THEN
        RETURN NEW;
    END IF;

    PERFORM script.fn_log_and_raise_error(
        'vendite',
        TG_NAME::text,
        'E_RIGA_QUANTITA_CON_FONTE_A_VALLE',
        jsonb_build_object(
            'campo',                 v_valorizzati[1],
            'colonne',               to_jsonb(v_valorizzati),
            'fonte_quantita_attesa', NEW.fonte_quantita_attesa,
            'riga_id',               NEW.id,
            v_col_padre,             to_jsonb(NEW) -> v_col_padre,
            'articolo_id',           NEW.articolo_id),
        NEW.tx_id,
        VARIADIC ARRAY[]::text[]);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_righe_guard_quantita_per_fonte()
IS 'Guard: una riga di vendite.contratti_righe o di vendite.offerte_commerciali_eccezioni con una fonte a valle (ogni fonte_quantita_attesa che non è FISSA né DERIVATA_COMPONENTI: oggi MANUALE, LETTURE, TIMESHEET) non porta quantita né qta_operativa: la quantità arriva a valle, periodo per periodo (E_RIGA_QUANTITA_CON_FONTE_A_VALLE, DATO_ERRATO, nessun valore). campo = qta_operativa se valorizzata, altrimenti quantita (canale COLUMN); colonne = le valorizzate. Fonte NULL: non giudica. Stessa regola e stesso elenco dei CHECK chk_contrighe_quantita_per_fonte / chk_offerte_eccezioni_quantita_per_fonte, che restano la rete. TG_ARGV[0] = colonna del padre (contratto_id | offerta_id), solo per il contesto. Trigger _a10_ BEFORE INSERT OR UPDATE WHEN (NEW.tipo_eccezione <> ''ESCLUSIONE''), senza colonne sull''UPDATE perché la fonte la può riallineare un altro BEFORE. Prende il posto della copia Python _apply_fonte_quantita_logic (solo contratto). Nasce il 2026-10-07, brief-db-offerta-emissione-ed-erogazione §D.4 punto 2 (decisione di Tid: «DB, rifiuto»).';
```

---
{% include-markdown "signature-core.md" %}
