{% include-markdown "it/dbzero/script/manual/fn_get_indirizzi_by_soggetto.md" %}
# ⚙️ Funzione `fn_get_indirizzi_by_soggetto`

```sql
CREATE FUNCTION fn_get_indirizzi_by_soggetto(p_soggetto_id uuid)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzi_by_soggetto(p_soggetto_id uuid)
 RETURNS SETOF anagrafiche.vw_indirizzi_resolved_soggetto
 LANGUAGE sql
 STABLE
AS $function$
  -- Restituisce tutti gli indirizzi identitari (layer SOGGETTO)
  -- per il soggetto indicato, ordinati per tipo indirizzo e id.
  -- Legge la vista che DICHIARA come tipo di ritorno (rev 20261010-31):
  -- e' la base filtrata per scope = SOGGETTO, con le sue colonne. Proiettare
  -- r.* dalla base, come prima, si rompe a ogni colonna aggiunta alla base.
  SELECT r.*
  FROM anagrafiche.vw_indirizzi_resolved_soggetto r
  WHERE r.soggetto_id = p_soggetto_id
  ORDER BY r.tipo_indirizzo_codice, r.indirizzo_id;
$function$

COMMENT ON FUNCTION script.fn_get_indirizzi_by_soggetto(p_soggetto_id uuid)
IS 'Restituisce tutti gli indirizzi layer SOGGETTO (identitario) per un dato soggetto_id, ordinati per tipo e id. Legge vw_indirizzi_resolved_soggetto, il suo tipo di ritorno (rev 20261010-31: proiettava la base e restituiva troppe colonne).';
```

</div>

---
{% include-markdown "signature-core.md" %}
