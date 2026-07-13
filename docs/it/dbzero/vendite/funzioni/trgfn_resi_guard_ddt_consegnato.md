{% include-markdown "it/dbzero/vendite/manual/trgfn_resi_guard_ddt_consegnato.md" %}
# ⚙️ Funzione `trgfn_resi_guard_ddt_consegnato`

```sql
CREATE FUNCTION trgfn_resi_guard_ddt_consegnato()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_guard_ddt_consegnato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: il reso e' ammesso solo se il DDT sorgente e' CONSEGNATO
--   (non si rende cio' che non e' stato consegnato). Solo per
--   sorgente DDT_VENDITA (data-driven).
DECLARE
    v_is_ddt boolean;
    v_stato  config.stati_doc_ddt.codice_interno%TYPE;
BEGIN
    -- Applica solo alla sorgente DDT_VENDITA.
    SELECT EXISTS (
        SELECT 1 FROM config.sorgenti
         WHERE id = NEW.sorgente_tipo_id
           AND codice_interno = 'DDT_VENDITA'
    ) INTO v_is_ddt;

    IF NOT v_is_ddt THEN
        RETURN NEW;
    END IF;

    SELECT sdd.codice_interno INTO v_stato
      FROM vendite.ddt d
      JOIN config.stati_doc_ddt sdd ON sdd.id = d.stato_doc_ddt_id
     WHERE d.uid = NEW.sorgente_uid;

    IF v_stato IS DISTINCT FROM 'CONSEGNATO' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','trgfn_resi_guard_ddt_consegnato','E_RESO_DDT_NON_CONSEGNATO',
            jsonb_build_object('sorgente_uid', NEW.sorgente_uid, 'stato_ddt', v_stato),
            NULL::uuid, COALESCE(v_stato, 'NULL'));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_guard_ddt_consegnato()
IS 'Guard: reso ammesso solo se il DDT sorgente (DDT_VENDITA, per sorgente_uid) e in stato CONSEGNATO (E_RESO_DDT_NON_CONSEGNATO). brief §3. rev 2026-07-13.';
```

---
{% include-markdown "signature-core.md" %}
