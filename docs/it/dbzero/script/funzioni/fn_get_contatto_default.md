{% include-markdown "it/dbzero/script/manual/fn_get_contatto_default.md" %}
# ⚙️ Funzione `fn_get_contatto_default`

```sql
CREATE FUNCTION fn_get_contatto_default(p_soggetto_id uuid, p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint, p_tipo_contatto_id integer, p_unita_organizzativa_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_contatto_default(p_soggetto_id uuid, p_soggetto_ruolo_id bigint DEFAULT NULL::bigint, p_istanza_utility_id bigint DEFAULT NULL::bigint, p_tipo_contatto_id integer DEFAULT NULL::integer, p_unita_organizzativa_id integer DEFAULT NULL::integer)
 RETURNS TABLE(id bigint, tipo_contatto_id integer, soggetto_id uuid, soggetto_ruolo_id bigint, istanza_utility_id bigint, nominativo character varying, email character varying, telefono character varying, cellulare character varying, pec character varying, note text, is_default boolean, default_context character varying)
 LANGUAGE sql
AS $function$
/*
fn_get_contatto_default

Il contatto predefinito per un soggetto (e opzionalmente ruolo,
istanza, tipo di contatto, reparto), fra i candidati di
fn_get_contatti: fra i predefiniti vince il contesto piu'
specifico (istanza, poi ruolo, poi soggetto), poi l'id.
Ritorna 0 o 1 record.
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
    SELECT a.*,
        ROW_NUMBER() OVER (
            ORDER BY
                CASE
                    WHEN a.istanza_utility_id IS NOT NULL THEN 1
                    WHEN a.soggetto_ruolo_id  IS NOT NULL THEN 2
                    ELSE 3
                END,
                a.id
        ) AS rn
    FROM all_candidates a
    WHERE a.is_default
)
SELECT
    d.id,
    d.tipo_contatto_id,
    d.soggetto_id,
    d.soggetto_ruolo_id,
    d.istanza_utility_id,
    d.nominativo,
    d.email,
    d.telefono,
    d.cellulare,
    d.pec,
    d.note,
    d.is_default,
    d.default_context
FROM only_default d
WHERE d.rn = 1;
$function$

COMMENT ON FUNCTION script.fn_get_contatto_default(p_soggetto_id uuid, p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint, p_tipo_contatto_id integer, p_unita_organizzativa_id integer)
IS 'Il contatto predefinito per un soggetto (opz. ruolo, istanza, tipo, reparto), fra i candidati di script.fn_get_contatti: fra i predefiniti vince il contesto piu'' specifico (istanza, poi ruolo, poi soggetto), poi l''id. 0 o 1 record.';
```

</div>

---
{% include-markdown "signature-core.md" %}
