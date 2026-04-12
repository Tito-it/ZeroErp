# ⚙️ Funzione `trgfn_set_validita`

```sql
CREATE FUNCTION trgfn_set_validita()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_set_validita()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: sync colonna validita daterange da valido_dal / valido_al.
--   Funzione generica cross-schema, agganciabile a qualsiasi tabella
--   che abbia le colonne valido_dal (date), valido_al (date), validita (daterange).
-- Regole:
--   - validita = daterange(COALESCE(valido_dal, -infinity), COALESCE(valido_al, infinity), '[]')
--   - validita non e` mai NULL: -infinity e infinity coprono i casi di date aperte
--   - Sovrascrive sempre validita, ignorando eventuali valori passati
-- Invariante: validita e` funzione deterministica di valido_dal e valido_al
BEGIN
    NEW.validita := daterange(
        COALESCE(NEW.valido_dal, '-infinity'::date),
        COALESCE(NEW.valido_al, 'infinity'::date),
        '[]'
    );

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_set_validita()
IS 'Sync validita daterange da valido_dal/valido_al. Generica cross-schema. Usa -infinity/infinity per NULL. validita mai NULL. Migrazione daterange.';
```

---
{% include-markdown "signature-core.md" %}
