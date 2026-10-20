# ⚙️ Funzione `trgfn_ui_lista_preferenza_utente_guard_pagina_dimensione`

```sql
CREATE FUNCTION trgfn_ui_lista_preferenza_utente_guard_pagina_dimensione()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_ui_lista_preferenza_utente_guard_pagina_dimensione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: la misura «righe per pagina» salvata nella preferenza e' del
--   catalogo (chiave assente o null: il default).
BEGIN
    PERFORM ui.fn_guard_misura_pagina(NEW.configurazione -> 'pagina_dimensione');
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_ui_lista_preferenza_utente_guard_pagina_dimensione()
IS 'Guard di ui.lista_preferenza_utente: configurazione -> ''pagina_dimensione'' deve essere una misura del catalogo ui.misure_pagina (chiave assente o null = il default). Una FK sul jsonb non arriva: chiede a ui.fn_guard_misura_pagina, col valore com''e'' scritto (anche un non-numero si rifiuta col codice di catalogo). Brief: brief-db-misure-pagina-catalogo §2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
