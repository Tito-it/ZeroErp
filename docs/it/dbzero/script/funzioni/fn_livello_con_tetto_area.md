{% include-markdown "it/dbzero/script/manual/fn_livello_con_tetto_area.md" %}
# ⚙️ Funzione `fn_livello_con_tetto_area`

```sql
CREATE FUNCTION fn_livello_con_tetto_area(p_livello_specifico config.livello_accesso, p_livello_area config.livello_accesso)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_livello_con_tetto_area(p_livello_specifico config.livello_accesso, p_livello_area config.livello_accesso)
 RETURNS config.livello_accesso
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
-- Scopo: il livello effettivo di un oggetto sotto il tetto della sua area
--   (brief-db-permessi-tetto-area): lo specifico puo' solo restringere.
-- ⛔ L'enum config.livello_accesso e' ordinato TUTTO < LETTURA < BLOCCATO:
--   il piu' restrittivo e' GREATEST, che ignora i NULL (senza specifico
--   vale l'area). Area NULL vale BLOCCATO (fail-closed).
BEGIN
    RETURN GREATEST(p_livello_specifico,
                    COALESCE(p_livello_area, 'BLOCCATO'::config.livello_accesso));
END;
$function$

COMMENT ON FUNCTION script.fn_livello_con_tetto_area(p_livello_specifico config.livello_accesso, p_livello_area config.livello_accesso)
IS 'Regola pura del tetto d''area per un oggetto: il livello effettivo e'' il piu'' restrittivo fra quello specifico (override sull''oggetto) e quello dell''area. Lo specifico puo'' solo restringere, mai allargare (D-1). ⛔ L''enum livello_accesso e'' ordinato TUTTO < LETTURA < BLOCCATO: il piu'' restrittivo e'' GREATEST; specifico NULL -> vale l''area; area NULL -> BLOCCATO (fail-closed). Sede unica del confronto: la chiama script.fn_get_permessi_effettivi_oggetti (e da li'' fn_resolve_livello_oggetto, fn_get_user_object_permissions_map e il pannello permessi). IMMUTABLE, INVOKER. Brief: brief-db-permessi-tetto-area R4.';
```

</div>

---
{% include-markdown "signature-core.md" %}
