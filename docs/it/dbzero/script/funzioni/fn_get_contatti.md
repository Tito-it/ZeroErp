{% include-markdown "it/dbzero/script/manual/fn_get_contatti.md" %}
# Funzione `fn_get_contatti`

```sql
CREATE FUNCTION fn_get_contatti(p_soggetto_id uuid, p_soggetto_ruolo_id integer, p_utility_id integer, p_tipo_contatto_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_contatti(p_soggetto_id uuid, p_soggetto_ruolo_id integer DEFAULT NULL::integer, p_utility_id integer DEFAULT NULL::integer, p_tipo_contatto_id integer DEFAULT NULL::integer)
 RETURNS TABLE(id integer, tipo_contatto_id integer, soggetto_id uuid, soggetto_ruolo_id integer, utility_id integer, nominativo character varying, email character varying, telefono character varying, cellulare character varying, pec character varying, note text, is_default boolean, default_context character varying)
 LANGUAGE plpgsql
AS $function$
  BEGIN
      -- ====================================================================
      -- Restituisce per ogni tipo_contatto_id il contatto con priorità:
      --   1) soggetto+ruolo+utility
      --   2) soggetto+ruolo  
      --   3) soggetto+utility
      --   4) solo soggetto
      -- Filtra esattamente sui parametri passati.
      -- p_soggetto_id obbligatorio.
      -- Se p_soggetto_ruolo_id è NULL, considera tutti i ruoli del soggetto.
      -- Se p_utility_id è NULL, considera tutti i contatti del soggetto. 
      -- Se p_tipo_contatto_id è NULL, considera tutti i tipi di contatto.  
      -- Se p_soggetto_id è NULL o 0, solleva un errore.  
      -- ====================================================================
      -- Validazione input obbligatorio con wrapper di log
      IF p_soggetto_id IS NULL  or p_soggetto_id = 0 THEN
          PERFORM script.fn_log_and_raise_error(
              'database',
              'fn_get_contatti',
              'ERRORE_PARAMETRI',
              jsonb_build_object(
                'soggetto_id',       p_soggetto_id,
                'soggetto_ruolo_id', p_soggetto_ruolo_id,
                'utility_id',        p_utility_id,
                'tipo_contatto_id',  p_tipo_contatto_id
              ),
              COALESCE(p_soggetto_id::text,'NULL')
          );
      END IF;
      RETURN QUERY
      WITH candidates AS (
          SELECT
            c.id,
            c.tipo_contatto_id,
            c.soggetto_id,
            c.soggetto_ruolo_id,
            c.utility_id,
            c.nominativo,
            c.email,
            c.telefono,
            c.cellulare,
            c.pec,
            c.note,
            c.is_default,
            c.default_context,
            CASE
              WHEN c.soggetto_ruolo_id IS NOT NULL AND c.utility_id IS NOT NULL THEN 1
              WHEN c.soggetto_ruolo_id IS NOT NULL THEN 2
              WHEN c.utility_id IS NOT NULL THEN 3
              ELSE 4
            END AS priority
          FROM anagrafiche.contatti c
          WHERE c.soggetto_id = p_soggetto_id
            AND (
                (p_soggetto_ruolo_id IS NULL AND c.soggetto_ruolo_id IS NULL)
              OR (p_soggetto_ruolo_id IS NOT NULL AND c.soggetto_ruolo_id = p_soggetto_ruolo_id)
            )
            AND (
                (p_utility_id IS NULL AND c.utility_id IS NULL)
              OR (p_utility_id IS NOT NULL AND c.utility_id = p_utility_id)
            )
            AND (p_tipo_contatto_id IS NULL OR c.tipo_contatto_id = p_tipo_contatto_id)
      )
      SELECT id,
            tipo_contatto_id,
            soggetto_id,
            soggetto_ruolo_id,
            utility_id,
            nominativo,
            email,
            telefono,
            cellulare,
            pec,
            note,
            is_default,
            default_context
      FROM (
          SELECT *, row_number() OVER (
              PARTITION BY tipo_contatto_id
              ORDER BY priority
          ) AS rn
          FROM candidates
      ) sub
      WHERE rn = 1;
  END;
  $function$
```