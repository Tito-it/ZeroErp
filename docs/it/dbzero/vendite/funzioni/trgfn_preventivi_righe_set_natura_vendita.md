# ⚙️ Funzione `trgfn_preventivi_righe_set_natura_vendita`

```sql
CREATE FUNCTION trgfn_preventivi_righe_set_natura_vendita()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_preventivi_righe_set_natura_vendita()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Natura ereditata e CONGELATA dall'articolo: la riga non puo'
    -- discostarsi dalla classificazione dell'articolo. Qualunque
    -- valore fornito dal chiamante in NEW.natura_vendita_id viene
    -- sovrascritto (no override). Se l'articolo non e' ancora
    -- classificato (natura_vendita_id NULL, transitorio pre-backfill)
    -- la riga resta NULL e non e' smistabile finche' non si classifica.
    SELECT a.natura_vendita_id
      INTO NEW.natura_vendita_id
      FROM catalogo.articoli a
     WHERE a.id = NEW.articolo_id;
    RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
