{% include-markdown "it/dbzero/catalogo/manual/fn_articolo_flag_etichetta.md" %}
# ⚙️ Funzione `fn_articolo_flag_etichetta`

```sql
CREATE FUNCTION fn_articolo_flag_etichetta(p_colonna text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_articolo_flag_etichetta(p_colonna text)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- Il nome di una colonna di catalogo.articoli: nessuna colonna ne e'
    -- il riflesso, quindi text.
    SELECT CASE p_colonna
        WHEN 'is_composito'         THEN 'composito'
        WHEN 'is_solo_componente'   THEN 'solo componente'
        WHEN 'natura_vendita_id'    THEN 'natura di vendita'
        WHEN 'causale_onere_id'     THEN 'causale onere'
        WHEN 'listino_tipologia_id' THEN 'tipologia di listino'
        WHEN 'gestito_a_magazzino'  THEN 'gestito a magazzino'
        WHEN 'requires_lotto'       THEN 'gestito a lotti'
        WHEN 'requires_serial'      THEN 'gestito a matricola'
    END
$function$

COMMENT ON FUNCTION catalogo.fn_articolo_flag_etichetta(p_colonna text)
IS 'Il nome che l''operatore riconosce di una colonna strutturale di catalogo.articoli (le colonne di catalogo.fn_articolo_colonne_struttura): composito, solo componente, natura di vendita, causale onere, tipologia di listino, gestito a magazzino, gestito a lotti, gestito a matricola. Un''altra colonna: NULL. Va nei valori dei messaggi al posto del nome della colonna. Lettori: catalogo.trgfn_articoli_guard_struttura_se_usato, catalogo.trgfn_articoli_guard_onere_natura, catalogo.fn_articolo_correggi_struttura. IMMUTABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
