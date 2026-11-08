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
--   sorgente DDT_VENDITA (data-driven). La bolla ha chiave id: si
--   cerca per sorgente_id.
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
     WHERE d.id = NEW.sorgente_id;

    -- Una bolla di TRASFERIMENTO fra depositi non genera un reso. La merce e'
    --   rimasta nostra (e' entrata nel magazzino di arrivo al CONSEGNATO): un
    --   reso la farebbe rientrare una seconda volta, con un accredito verso un
    --   cliente che non l'ha mai comprata. Si riconosce dalla causale di
    --   magazzino della sua causale di trasporto (TRASF_OUT), non dal codice
    --   scritto a mano. Prima del controllo di stato: e' la risposta vera.
    SELECT d.* INTO v_ddt
      FROM vendite.ddt d
     WHERE d.id = NEW.sorgente_id;
    IF FOUND AND vendite.fn_ddt_causale_magazzino(v_ddt) = 'TRASF_OUT' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','trgfn_resi_guard_ddt_consegnato','E_RESO_DA_DDT_TRASFERIMENTO',
            jsonb_build_object('sorgente_id', NEW.sorgente_id, 'ddt_id', v_ddt.id),
            NULL::uuid, COALESCE(v_ddt.numero, v_ddt.id::text));
    END IF;

    IF v_stato IS DISTINCT FROM 'CONSEGNATO' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','trgfn_resi_guard_ddt_consegnato','E_RESO_DDT_NON_CONSEGNATO',
            jsonb_build_object('sorgente_id', NEW.sorgente_id, 'stato_ddt', v_stato),
            NULL::uuid, COALESCE(v_stato, 'NULL'));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_guard_ddt_consegnato()
IS 'Guard del reso: la bolla sorgente (DDT_VENDITA, cercata per sorgente_id: la bolla ha chiave id) deve essere CONSEGNATA (E_RESO_DDT_NON_CONSEGNATO). Prima, una bolla di trasferimento fra depositi (causale di magazzino TRASF_OUT) non genera un reso (E_RESO_DA_DDT_TRASFERIMENTO): la merce e'' rimasta nostra, e un reso la farebbe rientrare due volte. Il dettaglio dei due errori porta la chiave della bolla (sorgente_id), e ddt_id o stato_ddt.';
```

</div>

---
{% include-markdown "signature-core.md" %}
