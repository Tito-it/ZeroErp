{% include-markdown "it/dbzero/script/manual/fn_indirizzi_obbligatori_mancanti.md" %}
# ⚙️ Funzione `fn_indirizzi_obbligatori_mancanti`

```sql
CREATE FUNCTION fn_indirizzi_obbligatori_mancanti(p_ambito character varying, p_tipi_presenti integer[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_indirizzi_obbligatori_mancanti(p_ambito character varying, p_tipi_presenti integer[])
 RETURNS text[]
 LANGUAGE sql
 STABLE
AS $function$
-- rev 2026-10-20 (20261020-51, brief-db-grammatica-unica-documenti, 2d G-6):
--   p_ambito e' il codice della sorgente del documento (FATTURA,
--   DDT_VENDITA...), ancorato.
  -- Codici obbligatori dell'ambito non presenti tra i tipi passati.
  SELECT COALESCE(
           array_agg(t.codice_interno ORDER BY t.codice_interno),
           ARRAY[]::text[])
    FROM config.tipi_indirizzi_allowed a
    JOIN config.tipi_indirizzi t ON t.id = a.tipo_indirizzo_id
   WHERE a.ambito = p_ambito
     AND a.attivo IS TRUE
     AND a.obbligatorio IS TRUE
     AND NOT (a.tipo_indirizzo_id = ANY(COALESCE(p_tipi_presenti, ARRAY[]::integer[])));
$function$

COMMENT ON FUNCTION script.fn_indirizzi_obbligatori_mancanti(p_ambito character varying, p_tipi_presenti integer[])
IS 'Rev 2026-10-20 (20261020-51, brief-db-grammatica-unica-documenti 2d, G-6): p_ambito e'' il codice della sorgente del documento, ancorato a config.tipi_indirizzi_allowed.ambito%TYPE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
