{% include-markdown "it/dbzero/vendite/manual/trgfn_resi_guard_ddt_consegnato.md" %}
# ⚙️ Funzione `trgfn_resi_guard_ddt_consegnato`

```sql
CREATE FUNCTION trgfn_resi_guard_ddt_consegnato()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

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
    v_ddt    vendite.ddt%ROWTYPE;
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

    -- rev 2026-09-28 (brief-db-magazzino-lotto-3-scarico-da-ddt, D-L3-c): una
    --   bolla di TRASFERIMENTO fra depositi non genera un reso. La merce e'
    --   rimasta nostra (e' entrata nel magazzino di arrivo al CONSEGNATO): un
    --   reso la farebbe rientrare una seconda volta, con un accredito verso un
    --   cliente che non l'ha mai comprata. Si riconosce dalla causale di
    --   magazzino della sua causale di trasporto (TRASF_OUT), non dal codice
    --   scritto a mano. Prima del controllo di stato: e' la risposta vera.
    SELECT d.* INTO v_ddt
      FROM vendite.ddt d
     WHERE d.uid = NEW.sorgente_uid;
    IF FOUND AND vendite.fn_ddt_causale_magazzino(v_ddt) = 'TRASF_OUT' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','trgfn_resi_guard_ddt_consegnato','E_RESO_DA_DDT_TRASFERIMENTO',
            jsonb_build_object('sorgente_uid', NEW.sorgente_uid, 'ddt_id', v_ddt.id),
            NULL::uuid, COALESCE(v_ddt.numero, v_ddt.id::text));
    END IF;

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
IS 'Guard: reso ammesso solo se il DDT sorgente (DDT_VENDITA, per sorgente_uid) e in stato CONSEGNATO (E_RESO_DDT_NON_CONSEGNATO). brief §3. rev 2026-07-13. rev 2026-09-28 (brief-db-magazzino-lotto-3-scarico-da-ddt, D-L3-c): una bolla di TRASFERIMENTO fra depositi (causale di magazzino TRASF_OUT) non genera un reso — E_RESO_DA_DDT_TRASFERIMENTO, prima del controllo di stato: la merce e'' rimasta nostra, un reso la farebbe rientrare due volte.';
```

</div>

---
{% include-markdown "signature-core.md" %}
