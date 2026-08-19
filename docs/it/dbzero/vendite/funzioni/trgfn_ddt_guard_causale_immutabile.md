{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_guard_causale_immutabile.md" %}
# ⚙️ Funzione `trgfn_ddt_guard_causale_immutabile`

```sql
CREATE FUNCTION trgfn_ddt_guard_causale_immutabile()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_guard_causale_immutabile()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: impedire il cambio della causale di trasporto su un DDT
--   che ha gia' lasciato la bozza. La causale dichiara se la merce
--   che viaggia e' una vendita (DL-28) ed e' stampata sul
--   documento: dopo l'emissione, cambiarla vorrebbe dire che il
--   foglio consegnato e l'archivio dicono cose diverse.
-- Uso: BEFORE UPDATE OF causale_trasporto_id FOR EACH ROW
--   WHEN (NEW.causale_trasporto_id IS DISTINCT FROM OLD.causale_trasporto_id)
DECLARE
    v_stato_vecchio config.stati_doc_ddt.codice_interno%TYPE;
BEGIN
    -- ⚠️ Si guarda lo stato VECCHIO, non il nuovo. Un UPDATE che
    --   cambia insieme stato e causale — DRAFT -> EMESSO con la
    --   causale finalmente scelta — e' l'operazione LEGITTIMA per
    --   eccellenza, ed e' quella che il gate all'emissione
    --   presidia. Guardare NEW la boccerebbe, e sarebbe un guard
    --   che vieta proprio il caso giusto.
    SELECT sdd.codice_interno
      INTO v_stato_vecchio
      FROM config.stati_doc_ddt sdd
     WHERE sdd.id = OLD.stato_doc_ddt_id;

    IF v_stato_vecchio IS DISTINCT FROM 'DRAFT' THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_DDT_CAUSALE_IMMUTABILE',
            jsonb_build_object(
                'ddt_id',        NEW.id,
                'numero',        NEW.numero,
                'stato',         v_stato_vecchio,
                'causale_da',    OLD.causale_trasporto_id,
                'causale_a',     NEW.causale_trasporto_id),
            NEW.tx_id,
            COALESCE(NEW.numero, NEW.id::text)
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_guard_causale_immutabile()
IS 'Trigger BEFORE UPDATE OF causale_trasporto_id su vendite.ddt: blocca il cambio se il DDT ha gia'' lasciato la bozza (E_DDT_CAUSALE_IMMUTABILE). La causale e'' stampata sul documento e dichiara se la merce si vende (DL-28): dopo l''emissione il documento e'' quello. ⚠️ Legge lo stato VECCHIO: l''UPDATE che porta DRAFT->EMESSO scegliendo contestualmente la causale e'' legittimo, e guardare NEW lo boccerebbe. Chiude il buco R-4 del brief: il gate all''emissione guarda solo la transizione verso EMESSO, quindi una causale non fatturabile poteva diventare fatturabile a documento gia'' spedito, rendendo eleggibile al lister una riga senza prezzo. Brief: brief-ddt-righe-senza-prezzo §9 slice B (D-4).';
```

---
{% include-markdown "signature-core.md" %}
