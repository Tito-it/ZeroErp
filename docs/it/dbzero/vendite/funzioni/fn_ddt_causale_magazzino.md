# ⚙️ Funzione `fn_ddt_causale_magazzino`

```sql
CREATE FUNCTION fn_ddt_causale_magazzino(p_ddt vendite.ddt)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ddt_causale_magazzino(p_ddt vendite.ddt)
 RETURNS character varying
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: con quale causale di magazzino si muove la merce di questa
--   bolla — la mappatura della sua causale di trasporto (D-L3-g).
-- Ritorna: il codice_interno (SCARICO_VEN, TRASF_OUT, ...) oppure NULL
--   = la bolla non muove merce (causale mancante o non mappata).
DECLARE
    v_causale config.causali_trasporto.causale_magazzino%TYPE;
BEGIN
    SELECT ct.causale_magazzino INTO v_causale
      FROM config.causali_trasporto ct
     WHERE ct.id = p_ddt.causale_trasporto_id;
    RETURN v_causale;
END;
$function$

COMMENT ON FUNCTION vendite.fn_ddt_causale_magazzino(p_ddt vendite.ddt)
IS 'Con quale causale di magazzino si muove la merce di una bolla: config.causali_trasporto.causale_magazzino della sua causale di trasporto (D-L3-g). NULL = non muove merce. Prende la RIGA della bolla, non l''id: il guard BEFORE UPDATE deve vedere la causale nuova. Brief: brief-db-magazzino-lotto-3-scarico-da-ddt.';
```

</div>

---
{% include-markdown "signature-core.md" %}
