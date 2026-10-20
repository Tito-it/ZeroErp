{% include-markdown "it/dbzero/script/manual/fn_get_contatti.md" %}
# ⚙️ Funzione `fn_get_contatti`

```sql
CREATE FUNCTION fn_get_contatti(p_soggetto_id uuid, p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint, p_tipo_contatto_id integer, p_unita_organizzativa_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_contatti(p_soggetto_id uuid, p_soggetto_ruolo_id bigint DEFAULT NULL::bigint, p_istanza_utility_id bigint DEFAULT NULL::bigint, p_tipo_contatto_id integer DEFAULT NULL::integer, p_unita_organizzativa_id integer DEFAULT NULL::integer)
 RETURNS TABLE(id bigint, tipo_contatto_id integer, soggetto_id uuid, soggetto_ruolo_id bigint, istanza_utility_id bigint, nominativo character varying, email character varying, telefono character varying, cellulare character varying, pec character varying, note text, is_default boolean, default_context character varying)
 LANGUAGE sql
AS $function$

/*
fn_get_contatti

Scopo:
    Restituisce, per un dato soggetto (ed eventuale ruolo/istanza),
    il "miglior" contatto per ciascun tipo_contatto_id, secondo logica
    di priorita a 3 livelli:

    1) soggetto + ruolo + istanza
    2) soggetto + ruolo (generico)
    3) solo soggetto (fallback)

    A parita di priorita, viene preferito il contatto marcato
    is_default = TRUE, se presente.
*/

WITH validate AS (
    -- Validazione p_soggetto_id (obbligatorio)
    SELECT script.fn_log_and_raise_error(
        'database',
        'fn_get_contatti',
        'ERRORE_PARAMETRI',
        jsonb_build_object(
            'soggetto_id',           p_soggetto_id,
            'soggetto_ruolo_id',     p_soggetto_ruolo_id,
            'istanza_utility_id',    p_istanza_utility_id,
            'tipo_contatto_id',      p_tipo_contatto_id,
            'unita_organizzativa_id', p_unita_organizzativa_id
        ),
        NULL::uuid,
        COALESCE(p_soggetto_id::text, 'NULL')
    )
    WHERE p_soggetto_id IS NULL
),
candidates AS (
    -- Costruzione dei candidati con calcolo della priority (3 livelli)
    SELECT
        c.id,
        c.tipo_contatto_id,
        c.unita_organizzativa_id,
        c.soggetto_id,
        c.soggetto_ruolo_id,
        c.istanza_utility_id,
        c.nominativo,
        c.email,
        c.telefono,
        c.cellulare,
        c.pec,
        c.note,
        c.is_default,
        c.default_context,
        CASE
            -- Livello 1: ruolo + istanza (match esatto)
            WHEN c.soggetto_ruolo_id IS NOT DISTINCT FROM p_soggetto_ruolo_id
             AND c.istanza_utility_id IS NOT DISTINCT FROM p_istanza_utility_id
             AND c.istanza_utility_id IS NOT NULL
                THEN 1
            -- Livello 2: ruolo generico (istanza NULL)
            WHEN c.soggetto_ruolo_id IS NOT DISTINCT FROM p_soggetto_ruolo_id
             AND c.istanza_utility_id IS NULL
                THEN 2
            -- Livello 3: solo soggetto
            ELSE 3
        END AS priority
    FROM anagrafiche.contatti AS c
    WHERE c.soggetto_id = p_soggetto_id
    AND (
            c.soggetto_ruolo_id IS NULL
        OR c.soggetto_ruolo_id IS NOT DISTINCT FROM p_soggetto_ruolo_id
    )
    AND (
            c.istanza_utility_id IS NULL
        OR c.istanza_utility_id IS NOT DISTINCT FROM p_istanza_utility_id
    )
    AND (
            p_tipo_contatto_id IS NULL
        OR c.tipo_contatto_id = p_tipo_contatto_id
    )
    AND (
            c.unita_organizzativa_id IS NULL
        OR c.unita_organizzativa_id IS NOT DISTINCT FROM p_unita_organizzativa_id
    )
),
ranked AS (
    -- Una sola riga per tipo_contatto_id:
    -- priorita di contesto + preferenza per is_default = TRUE
    SELECT
        candidates.*,
        ROW_NUMBER() OVER (
            PARTITION BY candidates.tipo_contatto_id
            ORDER BY
                candidates.priority,
                CASE
                    WHEN p_unita_organizzativa_id IS NULL THEN 0
                    WHEN candidates.unita_organizzativa_id IS NOT DISTINCT FROM p_unita_organizzativa_id THEN 0
                    ELSE 1
                END,
                CASE WHEN candidates.is_default THEN 0 ELSE 1 END,
                candidates.id
        ) AS rn
    FROM candidates
)

-- Ritorno solo i "migliori" per tipo_contatto_id
SELECT
    r.id,
    r.tipo_contatto_id,
    r.soggetto_id,
    r.soggetto_ruolo_id,
    r.istanza_utility_id,
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

COMMENT ON FUNCTION script.fn_get_contatti(p_soggetto_id uuid, p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint, p_tipo_contatto_id integer, p_unita_organizzativa_id integer)
IS 'Contatto migliore per tipo_contatto_id con cascata 3 livelli: (1) ruolo+istanza, (2) ruolo generico, (3) soggetto. p_soggetto_id obbligatorio.';
```

</div>

---
{% include-markdown "signature-core.md" %}
