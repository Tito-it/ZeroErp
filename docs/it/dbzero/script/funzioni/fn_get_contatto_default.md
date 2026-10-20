{% include-markdown "it/dbzero/script/manual/fn_get_contatto_default.md" %}
# ⚙️ Funzione `fn_get_contatto_default`

```sql
CREATE FUNCTION fn_get_contatto_default(p_soggetto_id uuid, p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint, p_tipo_contatto_id integer, p_unita_organizzativa_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_contatto_default(p_soggetto_id uuid, p_soggetto_ruolo_id bigint DEFAULT NULL::bigint, p_istanza_utility_id bigint DEFAULT NULL::bigint, p_tipo_contatto_id integer DEFAULT NULL::integer, p_unita_organizzativa_id integer DEFAULT NULL::integer)
 RETURNS TABLE(id bigint, tipo_contatto_id integer, soggetto_id uuid, soggetto_ruolo_id bigint, istanza_utility_id bigint, nominativo character varying, email character varying, telefono character varying, cellulare character varying, pec character varying, note text, is_default boolean, default_context character varying)
 LANGUAGE sql
AS $function$

/*
fn_get_contatto_default

Restituisce il contatto marcato come DEFAULT per un soggetto
(e opzionalmente per ruolo, istanza, tipo_contatto, unita_organizzativa).
Riutilizza fn_get_contatti per costruire i candidati.
Filtra is_default = TRUE. Ritorna 0 o 1 record.
*/

WITH all_candidates AS (
    SELECT *
    FROM script.fn_get_contatti(
        p_soggetto_id,
        p_soggetto_ruolo_id,
        p_istanza_utility_id,
        p_tipo_contatto_id,
        p_unita_organizzativa_id
    )
),
only_default AS (
    SELECT *,
        ROW_NUMBER() OVER (
                ORDER BY
                    CASE WHEN is_default THEN 0 ELSE 1 END,
                    id
        ) AS rn
    FROM all_candidates
    WHERE is_default = TRUE
)

SELECT
    id,
    tipo_contatto_id,
    soggetto_id,
    soggetto_ruolo_id,
    istanza_utility_id,
    nominativo,
    email,
    telefono,
    cellulare,
    pec,
    note,
    is_default,
    default_context
FROM only_default
WHERE rn = 1;

$function$

COMMENT ON FUNCTION script.fn_get_contatto_default(p_soggetto_id uuid, p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint, p_tipo_contatto_id integer, p_unita_organizzativa_id integer)
IS 'Contatto DEFAULT per soggetto (opz. ruolo, istanza, tipo, unita). Wrapper su fn_get_contatti con filtro is_default. 0 o 1 record.';
```

</div>

---
{% include-markdown "signature-core.md" %}
