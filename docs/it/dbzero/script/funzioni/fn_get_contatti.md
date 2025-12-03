{% include-markdown "it/dbzero/script/manual/fn_get_contatti.md" %}
# ⚙️ Funzione `fn_get_contatti`

```sql
CREATE FUNCTION fn_get_contatti(p_soggetto_id uuid, p_soggetto_ruolo_id bigint, p_utility_id integer, p_tipo_contatto_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_contatti(p_soggetto_id uuid, p_soggetto_ruolo_id bigint DEFAULT NULL::bigint, p_utility_id integer DEFAULT NULL::integer, p_tipo_contatto_id integer DEFAULT NULL::integer)
 RETURNS TABLE(id bigint, tipo_contatto_id integer, soggetto_id uuid, soggetto_ruolo_id bigint, utility_id integer, nominativo character varying, email character varying, telefono character varying, cellulare character varying, pec character varying, note text, is_default boolean, default_context character varying)
 LANGUAGE sql
AS $function$

/*
fn_get_contatti

Scopo:
    Restituisce, per un dato soggetto (ed eventuale ruolo/utility),
    il "miglior" contatto per ciascun tipo_contatto_id, secondo logica di priorità:

    1) soggetto + ruolo + utility
    2) soggetto + ruolo
    3) soggetto + utility
    4) solo soggetto

    A parità di priorità, viene preferito il contatto marcato is_default = TRUE,
    se presente.

Nota:
    Questa funzione è pensata anche per essere riutilizzata da una funzione
    dedicata ai "default" (es. script.fn_get_contatto_default) che potrà
    filtrare sul flag is_default e/o su default_context.
*/

WITH validate AS (
    -- 1) Validazione p_soggetto_id (obbligatorio)
    SELECT script.fn_log_and_raise_error(
        'database',
        'fn_get_contatti',
        'ERRORE_PARAMETRI',
        jsonb_build_object(
            'soggetto_id',        p_soggetto_id,
            'soggetto_ruolo_id',  p_soggetto_ruolo_id,
            'utility_id',         p_utility_id,
            'tipo_contatto_id',   p_tipo_contatto_id
        ),
        NULL::uuid,                                  -- p_tx_id (NULL → helper lo ricrea)
        COALESCE(p_soggetto_id::text, 'NULL')
    )
    WHERE p_soggetto_id IS NULL
),
candidates AS (
    -- 2) Costruzione dei candidati con calcolo della priority
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
            WHEN c.soggetto_ruolo_id IS NOT DISTINCT FROM p_soggetto_ruolo_id
            AND c.utility_id        IS NOT DISTINCT FROM p_utility_id
                THEN 1   -- ruolo + utility
            WHEN c.soggetto_ruolo_id IS NOT DISTINCT FROM p_soggetto_ruolo_id
                THEN 2   -- solo ruolo
            WHEN c.utility_id        IS NOT DISTINCT FROM p_utility_id
                THEN 3   -- solo utility
            ELSE 4           -- solo soggetto
        END AS priority
    FROM anagrafiche.contatti AS c
    WHERE c.soggetto_id = p_soggetto_id
    AND (
            c.soggetto_ruolo_id IS NULL
        OR c.soggetto_ruolo_id IS NOT DISTINCT FROM p_soggetto_ruolo_id
    )
    AND (
            c.utility_id IS NULL
        OR c.utility_id IS NOT DISTINCT FROM p_utility_id
    )
    AND (
            p_tipo_contatto_id IS NULL
        OR c.tipo_contatto_id = p_tipo_contatto_id
    )
),
ranked AS (
    -- 3) Una sola riga per tipo_contatto_id:
    --    priorità di contesto + preferenza per is_default = TRUE
    SELECT
        candidates.*,
        ROW_NUMBER() OVER (
            PARTITION BY candidates.tipo_contatto_id
            ORDER BY
                candidates.priority,
                CASE WHEN candidates.is_default THEN 0 ELSE 1 END,
                candidates.id   -- per stabilizzare l'ordinamento
        ) AS rn
    FROM candidates
)

-- 4) Ritorno solo i "migliori" per tipo_contatto_id
SELECT
    r.id,
    r.tipo_contatto_id,
    r.soggetto_id,
    r.soggetto_ruolo_id,
    r.utility_id,
    r.nominativo,
    r.email,
    r.telefono,
    r.cellulare,
    r.pec,
    r.note,
    r.is_default,
    r.default_context
FROM ranked AS r
WHERE r.rn = 1;

$function$
```

---
{% include-markdown "signature-core.md" %}
