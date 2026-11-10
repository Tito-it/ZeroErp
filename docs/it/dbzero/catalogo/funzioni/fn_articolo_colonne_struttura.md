{% include-markdown "it/dbzero/catalogo/manual/fn_articolo_colonne_struttura.md" %}
# ⚙️ Funzione `fn_articolo_colonne_struttura`

```sql
CREATE FUNCTION fn_articolo_colonne_struttura()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_articolo_colonne_struttura()
 RETURNS text[]
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- La dichiarazione: le colonne che un articolo usato non cambia, e che
    -- la porta della struttura corregge. L'ordine e' quello in cui il guard
    -- cerca la prima cambiata.
    SELECT ARRAY['is_composito', 'is_solo_componente', 'natura_vendita_id',
                 'causale_onere_id', 'listino_tipologia_id',
                 'gestito_a_magazzino', 'requires_lotto', 'requires_serial']::text[];
$function$

COMMENT ON FUNCTION catalogo.fn_articolo_colonne_struttura()
IS 'La dichiarazione delle colonne strutturali di un articolo: quelle che non cambiano quando l''articolo e'' usato (catalogo.fn_articolo_usato) e che il SUPER_ADMIN corregge con catalogo.fn_articolo_correggi_struttura. Otto colonne, nell''ordine in cui il guard cerca la prima cambiata: is_composito, is_solo_componente, natura_vendita_id, causale_onere_id, listino_tipologia_id, gestito_a_magazzino, requires_lotto, requires_serial. La leggono il guard catalogo.trgfn_articoli_guard_struttura_se_usato (nel corpo), la porta (le colonne ammesse in p_campi) e il backend (i campi che la scheda articolo riapre in correzione). Le due copie che non si leggono a runtime, l''elenco UPDATE OF del trigger del guard e le regole del form in dbops.lock_columns_conditional sul predicato dell''uso, le confronta il pgTAP catalogo/test-articolo-colonne-struttura-v1: una regola del form spenta non toglie la colonna alla porta. IMMUTABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
