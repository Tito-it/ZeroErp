{% include-markdown "it/dbzero/vendite/manual/trgfn_offerte_commerciali_revisione.md" %}
# ⚙️ Funzione `trgfn_offerte_commerciali_revisione`

```sql
CREATE FUNCTION trgfn_offerte_commerciali_revisione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_offerte_commerciali_revisione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: al momento dell'INSERT di una rev.N+1 (revisione_padre_id NOT NULL),
-- porta la rev.N precedente in stato SUPERATA tramite UPDATE diretto.
-- L'UPDATE riattiva il guard _a10_ sulla stessa tabella: la transizione
-- EMESSA->SUPERATA e' ammessa in config.stati_doc_offerte_transizioni (Step 4).
-- Nota O4: l'UPDATE riguarda una riga diversa da quella inserita, nessuna
-- autoricorsione ne' conflitto intra-transazione.
DECLARE
    v_stato_superata_id config.stati_doc_offerte.id%TYPE;
BEGIN
    -- Se non e' una revisione (prima rev.), niente da fare.
    IF NEW.revisione_padre_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- Risolve l'id di SUPERATA dalla config (no hardcode).
    SELECT id INTO v_stato_superata_id
      FROM config.stati_doc_offerte
     WHERE codice_interno = 'SUPERATA';

    -- Porta la revisione padre in SUPERATA.
    -- Il guard _a10_ verifica che EMESSA->SUPERATA sia transizione ammessa.
    UPDATE vendite.offerte_commerciali
       SET stato_doc_offerta_id = v_stato_superata_id
     WHERE id = NEW.revisione_padre_id;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_offerte_commerciali_revisione()
IS 'AFTER INSERT su offerte_commerciali: se revisione_padre_id IS NOT NULL, porta la revisione padre in stato SUPERATA. Innesca il guard _a10_ (EMESSA->SUPERATA ammessa in stati_doc_offerte_transizioni). Nota O4: agisce su riga diversa dall''INSERT scatenante, nessun conflitto. rev 2026-05-24.';
```

---
{% include-markdown "signature-core.md" %}
