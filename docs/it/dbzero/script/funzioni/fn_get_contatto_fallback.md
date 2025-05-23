# Funzione `fn_get_contatto_fallback`

```sql
CREATE FUNCTION fn_get_contatto_fallback(p_soggetto_id uuid, p_tipo_contatto_id integer, p_soggetto_ruolo_id integer, p_utility_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_contatto_fallback(p_soggetto_id uuid, p_tipo_contatto_id integer, p_soggetto_ruolo_id integer DEFAULT NULL::integer, p_utility_id integer DEFAULT NULL::integer)
 RETURNS anagrafiche.contatti
 LANGUAGE plpgsql
 STABLE
AS $function$
--====================================================================
-- Function: script.fn_get_contatto_fallback
--   Restituisce il contatto più specifico disponibile secondo l'ordine:
--     1) servizio (utility_id)
--     2) ruolo   (soggetto_ruolo_id)
--     3) soggetto
--     4) Soggetto default
--   Parametri:
--     p_soggetto_id       UUID (obbligatorio)
--     p_tipo_contatto_id  INTEGER (obbligatorio)
--     p_soggetto_ruolo_id INTEGER DEFAULT NULL (opzionale)
--     p_utility_id        INTEGER DEFAULT NULL (opzionale)
-- Returns: record di tipo anagrafiche.contatti
-- Schema: script

DECLARE
    rec anagrafiche.contatti%ROWTYPE;
    default_id INTEGER;
BEGIN
    -- primo tentativo: servizio → ruolo → soggetto
    SELECT c.* INTO rec
    FROM (
      SELECT c.*,
        CASE
          WHEN c.utility_id        IS NOT DISTINCT FROM p_utility_id        THEN 1
          WHEN c.soggetto_ruolo_id IS NOT DISTINCT FROM p_soggetto_ruolo_id THEN 2
          ELSE 3
        END AS priority
      FROM anagrafiche.contatti c
      WHERE c.soggetto_id      = p_soggetto_id
        AND c.tipo_contatto_id = p_tipo_contatto_id
    ) AS candidate
    ORDER BY priority, date_insert DESC
    LIMIT 1;

-- 4) se non trovato reperisco l'informazione da soggetto contatto_default
    IF NOT FOUND THEN
        -- fallback finale: contatto di default dal soggetto
        SELECT default_contatto_id INTO default_id
          FROM anagrafiche.soggetti
         WHERE id = p_soggetto_id;

        SELECT * INTO rec
          FROM anagrafiche.contatti
         WHERE id = default_id;
    END IF;

    RETURN rec;
END;
$function$
```