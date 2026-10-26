# ⚙️ Funzione `trgfn_resi_righe_rientri_guard`

```sql
CREATE FUNCTION trgfn_resi_righe_rientri_guard()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_righe_rientri_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: un rientro nomina un prelievo della riga di bolla da cui la
--   riga di reso viene, e non cambia riga ne' prelievo (D-3b-b).
--   «Solo in bozza» NON sta qui: lo dice il building block
--   vendite.trgfn_doc_righe_lock_fuori_bozza a livello RIGA (rev
--   2026-10-05), montato prima di questo guard.
DECLARE
    v_reso_id     vendite.resi_righe.reso_id%TYPE;
    v_riga_nr     vendite.resi_righe.riga_nr%TYPE;
    v_ddt_riga_id vendite.resi_righe.ddt_riga_id%TYPE;
    v_prel_riga   vendite.ddt_righe_prelievi.ddt_riga_id%TYPE;
    v_regola      text;     -- frase composta qui, nessuna colonna
BEGIN
    -- La riga di reso, sotto RLS. Assente = fuori perimetro, che il
    -- WITH CHECK della policy rifiuta comunque, o FK che parlera'.
    SELECT rr.reso_id, rr.riga_nr, rr.ddt_riga_id
      INTO v_reso_id, v_riga_nr, v_ddt_riga_id
      FROM vendite.resi_righe rr
     WHERE rr.id = NEW.resi_riga_id;
    IF NOT FOUND THEN
        RETURN NEW;
    END IF;

    -- Il prelievo e' della riga di bolla da cui viene la riga di reso.
    IF TG_OP = 'UPDATE'
       AND (NEW.resi_riga_id <> OLD.resi_riga_id
            OR NEW.ddt_riga_prelievo_id <> OLD.ddt_riga_prelievo_id) THEN
        v_regola := 'un rientro non cambia riga ne'' prelievo: toglierlo e scriverne un altro';
    ELSE
        SELECT p.ddt_riga_id INTO v_prel_riga
          FROM vendite.ddt_righe_prelievi p
         WHERE p.id = NEW.ddt_riga_prelievo_id;
        IF v_prel_riga IS DISTINCT FROM v_ddt_riga_id THEN
            v_regola := 'il prelievo indicato non e'' della riga di bolla da cui viene la riga di reso';
        END IF;
    END IF;

    IF v_regola IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.trgfn_resi_righe_rientri_guard',
            'E_RESO_RIENTRO_INCOERENTE',
            jsonb_build_object('reso_id', v_reso_id, 'resi_riga_id', NEW.resi_riga_id,
                               'ddt_riga_prelievo_id', NEW.ddt_riga_prelievo_id,
                               'ddt_riga_id_attesa', v_ddt_riga_id),
            NEW.tx_id,
            v_riga_nr::text, v_regola);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_righe_rientri_guard()
IS 'Guard BEFORE INSERT OR UPDATE su vendite.resi_righe_rientri: E_RESO_RIENTRO_INCOERENTE, la regola nel VARIADIC — il prelievo nominato non e'' della riga di bolla della riga di reso (resi_righe.ddt_riga_id), o un rientro cambia riga o prelievo. Quadratura, tetto per prelievo e posizione (ubicazione secondo il magazzino) li giudica la check della conferma (script.fn_check_reso_merce). «Solo in bozza» (E_RIGA_DOC_NON_BOZZA) non sta piu'' qui dal 2026-10-05: lo dice il building block vendite.trgfn_doc_righe_lock_fuori_bozza a livello RIGA (trg_resi_righe_rientri_a05_doc_bozza_ins_upd_dlt), e la copia scritta qui e'' stata ritirata (regola del 2; brief-db-righe-esclusione-solo-non-si-vende §8.2 B3). Brief d''origine: brief-db-magazzino-lotto-3-bis-carico-da-reso.';
```

</div>

---
{% include-markdown "signature-core.md" %}
