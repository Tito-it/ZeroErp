# ⚙️ Funzione `trgfn_righe_guard_quantita_per_fonte`

```sql
CREATE FUNCTION trgfn_righe_guard_quantita_per_fonte()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_righe_guard_quantita_per_fonte()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: rifiutare una riga (contratto o offerta) che porta una
--   quantita' operativa con una fonte che non la porta. La fonte dice
--   da dove arriva la quantita' che si fattura: FISSA e' quella della
--   riga; con ogni altra fonte (MANUALE, LETTURE, TIMESHEET) arriva a
--   valle. Rev 2026-10-21 (brief-db-offerta-emissione-ed-erogazione
--   §I.1): DERIVATA_COMPONENTI ritirata, solo commento.
-- Uso:   BEFORE INSERT OR UPDATE FOR EACH ROW
--        WHEN (NEW.tipo_eccezione <> 'ESCLUSIONE'), fascia _a10_,
--        su vendite.contratti_righe e
--        vendite.offerte_commerciali_eccezioni.
-- TG_ARGV[0]: colonna del documento padre ('contratto_id',
--   'offerta_id'), solo per il contesto dell'errore.
-- ⭐ Rifiuta solo l'INPUT (qta_operativa). quantita e' calcolata: con
--   una fonte a valle la porta a NULL script.trgfn_qta_from_operativa,
--   che gira dopo questo trigger (rev 2026-10-08, F-1.2).
-- ⭐ L'elenco delle fonti che portano la quantita' e'
--   script.fn_fonte_porta_quantita; i CHECK chk_*_quantita_per_fonte
--   (la rete) tengono lo stesso elenco, e un pgTAP li confronta.
-- Fonte NULL: la riga senza fonte la giudicano il guard d'obbligo e
--   il CHECK dell'esclusione, non questo.
DECLARE
    v_col_padre text := TG_ARGV[0];
BEGIN
    IF NEW.fonte_quantita_attesa IS NULL
       OR NEW.qta_operativa IS NULL
       OR script.fn_fonte_porta_quantita(NEW.fonte_quantita_attesa) THEN
        RETURN NEW;
    END IF;

    PERFORM script.fn_log_and_raise_error(
        'vendite',
        TG_NAME::text,
        'E_RIGA_QUANTITA_CON_FONTE_A_VALLE',
        jsonb_build_object(
            'campo',                 'qta_operativa',
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
IS 'Guard: una riga di vendite.contratti_righe o di vendite.offerte_commerciali_eccezioni con una fonte a valle (script.fn_fonte_porta_quantita = false: oggi MANUALE, LETTURE, TIMESHEET) non porta qta_operativa: la quantità arriva a valle, periodo per periodo (E_RIGA_QUANTITA_CON_FONTE_A_VALLE, DATO_ERRATO, nessun valore, campo qta_operativa nel canale COLUMN). quantita non è materia del rifiuto: è calcolata, e con una fonte a valle la porta a NULL script.trgfn_qta_from_operativa, che gira dopo. Fonte NULL: non giudica. I CHECK chk_contrighe_quantita_per_fonte / chk_offerte_eccezioni_quantita_per_fonte (stesso elenco) restano la rete. TG_ARGV[0] = colonna del padre (contratto_id | offerta_id), solo per il contesto. Trigger _a10_ BEFORE INSERT OR UPDATE WHEN (NEW.tipo_eccezione <> ''ESCLUSIONE''), senza colonne sull''UPDATE perché la fonte la può riallineare un altro BEFORE. Nasce il 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §D.4 punto 2); rev 2026-10-08 (§F.1, F-1.2: solo l''input); rev 2026-10-21 (20261021-47, §I.1: il commento non nomina piu'' DERIVATA_COMPONENTI, ritirata).';
```

</div>

---
{% include-markdown "signature-core.md" %}
