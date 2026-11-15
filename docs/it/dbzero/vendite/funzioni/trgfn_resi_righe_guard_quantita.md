{% include-markdown "it/dbzero/vendite/manual/trgfn_resi_righe_guard_quantita.md" %}
# ⚙️ Funzione `trgfn_resi_righe_guard_quantita`

```sql
CREATE FUNCTION trgfn_resi_righe_guard_quantita()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_righe_guard_quantita()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- rev 2026-11-14 (brief-db-stati-documento-dal-vocabolario, giro 6e): i resi non annullati dalla
--   colonna is_abortito, non dal codice.
-- Scopo: guardia over-return su resi_righe. Sigma quantita (base)
--   dei resi non annullati (non nello stato di annullo: la colonna
--   is_abortito del vocabolario) sulla stessa ddt_riga_id <= consegnato
--   (ddt_righe.quantita). Lock FOR UPDATE anti-concorrenza.
DECLARE
    v_consegnato vendite.ddt_righe.quantita%TYPE;
    v_gia_reso   numeric;
    v_residuo    numeric;
BEGIN
    -- 0) qta > 0 (difesa oltre al CHECK).
    IF NEW.quantita IS NULL OR NEW.quantita <= 0 THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_resi_righe_guard_quantita','E_QTA_NON_POSITIVA',
        jsonb_build_object('campo', 'quantita', 'quantita', NEW.quantita),
        NEW.tx_id, NEW.quantita::text);
    END IF;

    -- 1) Lock riga DDT sorgente + gruppo resi_righe sulla stessa
    --    ddt_riga (serializza over-return concorrente).
    PERFORM 1 FROM vendite.ddt_righe WHERE id = NEW.ddt_riga_id FOR UPDATE;
    PERFORM 1 FROM vendite.resi_righe q WHERE q.ddt_riga_id = NEW.ddt_riga_id FOR UPDATE;

    -- 2) Quantita consegnata di quella riga DDT (base).
    SELECT quantita INTO v_consegnato
      FROM vendite.ddt_righe WHERE id = NEW.ddt_riga_id;

    -- 3) Somma resa sulla stessa riga DDT dai resi non annullati
    --    (esclusa la riga corrente in UPDATE).
    SELECT COALESCE(SUM(rr.quantita), 0)
      INTO v_gia_reso
      FROM vendite.resi_righe rr
      JOIN vendite.resi r          ON r.id = rr.reso_id
      JOIN config.stati_doc_reso s ON s.id = r.stato_doc_reso_id
     WHERE rr.ddt_riga_id = NEW.ddt_riga_id
       AND s.is_abortito IS NOT TRUE
       AND (TG_OP <> 'UPDATE' OR rr.id <> NEW.id);

    v_residuo := v_consegnato - v_gia_reso;

    IF NEW.quantita > v_residuo THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_resi_righe_guard_quantita','E_RESO_QTA_SUPERA_CONSEGNATO',
        jsonb_build_object('ddt_riga_id', NEW.ddt_riga_id,
                           'consegnato', v_consegnato,
                           'gia_reso', v_gia_reso,
                           'qta_nuova', NEW.quantita,
                           'residuo', v_residuo),
        NEW.tx_id,
        NEW.ddt_riga_id::text, v_consegnato::text,
        v_gia_reso::text, NEW.quantita::text, v_residuo::text);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_righe_guard_quantita()
IS 'Guardia sulle righe del reso (fase a20, dopo qta_from_operativa): la quantita'' resa su una riga di bolla, sommata sui resi non annullati (non nello stato di annullo: la colonna is_abortito di config.stati_doc_reso), non supera la consegnata (E_RESO_QTA_SUPERA_CONSEGNATO); una quantita'' non positiva e'' E_QTA_NON_POSITIVA. La riga di bolla e le righe di reso sulla stessa riga si prendono FOR UPDATE: due resi concorrenti si serializzano. Gemella di trgfn_ordini_ful_guard_consistenza.';
```

</div>

---
{% include-markdown "signature-core.md" %}
