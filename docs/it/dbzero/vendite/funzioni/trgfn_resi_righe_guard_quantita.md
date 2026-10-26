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
-- Scopo: guardia over-return su resi_righe. Sigma quantita (base)
--   dei resi non-ANNULLATI sulla stessa ddt_riga_id <= consegnato
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

    -- 3) Somma resa sulla stessa riga DDT dai resi NON-ANNULLATI
    --    (esclusa la riga corrente in UPDATE).
    SELECT COALESCE(SUM(rr.quantita), 0)
      INTO v_gia_reso
      FROM vendite.resi_righe rr
      JOIN vendite.resi r          ON r.id = rr.reso_id
      JOIN config.stati_doc_reso s ON s.id = r.stato_doc_reso_id
     WHERE rr.ddt_riga_id = NEW.ddt_riga_id
       AND s.codice_interno <> 'ANNULLATO'
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
IS 'Guard over-return resi_righe: Sigma quantita non-ANNULLATI su ddt_riga <= consegnato (E_RESO_QTA_SUPERA_CONSEGNATO). Lock FOR UPDATE. Mirror trgfn_ordini_ful_guard_consistenza. Fase a20 (dopo qta_from_operativa). rev 2026-07-13.';
```

</div>

---
{% include-markdown "signature-core.md" %}
