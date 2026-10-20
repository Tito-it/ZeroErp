# ⚙️ Funzione `trgfn_ddt_default_magazzino`

```sql
CREATE FUNCTION trgfn_ddt_default_magazzino()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_default_magazzino()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: una bolla nata senza magazzino prende il predefinito del suo
--   emittente (D-L3-h). Solo se manca: chi lo sceglie vince.
DECLARE
    v_magazzino_id magazzino.magazzini.id%TYPE;
BEGIN
    IF NEW.magazzino_id IS NULL AND NEW.emittente_fiscale_id IS NOT NULL THEN
        SELECT m.id INTO v_magazzino_id
          FROM magazzino.magazzini m
         WHERE m.emittente_fiscale_id = NEW.emittente_fiscale_id
           AND m.predefinito
           AND m.attivo;
        NEW.magazzino_id := v_magazzino_id;   -- NULL se non c'e' un predefinito
    END IF;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_default_magazzino()
IS 'BEFORE INSERT su vendite.ddt: se magazzino_id manca, prende il magazzino predefinito e attivo dell''emittente della bolla (uno solo per emittente, uq_mag_magazzini_predefinito_emittente) — D-L3-h. Nessun predefinito: resta NULL, e se la bolla muove merce lo chiede la check dell''emissione. Brief: brief-db-magazzino-lotto-3-scarico-da-ddt. rev 2026-10-13 (20261013-53): il trigger e'' trg_ddt_z10_default_magazzino_ins e gira dopo trg_ddt_normalize_ins_upd. Prima era _a10_ e girava dopo il solo default dell''emittente, che sulle bolle con la sorgente non fa niente: una bolla generata da un ordine nasceva senza magazzino.';
```

</div>

---
{% include-markdown "signature-core.md" %}
