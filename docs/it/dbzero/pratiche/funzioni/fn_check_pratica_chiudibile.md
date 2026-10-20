{% include-markdown "it/dbzero/pratiche/manual/fn_check_pratica_chiudibile.md" %}
# ⚙️ Funzione `fn_check_pratica_chiudibile`

```sql
CREATE FUNCTION fn_check_pratica_chiudibile(p_pratica_id bigint, p_escludi_template_id integer, p_escludi_flusso_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_check_pratica_chiudibile(p_pratica_id bigint, p_escludi_template_id integer DEFAULT NULL::integer, p_escludi_flusso_id bigint DEFAULT NULL::bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
-- Scopo: fn_check_* puro (no raise). La pratica e' chiudibile quando NON ha
--   piu' lavoro (brief §2):
--   (a) nessun template obbligatorio "bloccante" (fn_check_chiusura_pratica), E
--   (b) nessun flusso ISTANZIATO in stato non terminale (fn_pratica_flussi_aperti, D1).
-- p_escludi_template_id: ignora un template dai bloccanti (guard pre-completamento).
-- p_escludi_flusso_id: ignora un'istanza dai flussi aperti (il flusso che sta
--   completando, ancora non-terminale nel guard BEFORE).
    SELECT NOT EXISTS (
             SELECT 1
               FROM pratiche.fn_check_chiusura_pratica(p_pratica_id) c
              WHERE c.bloccante
                AND (p_escludi_template_id IS NULL
                     OR c.template_flusso_id <> p_escludi_template_id)
           )
       AND NOT EXISTS (
             SELECT 1
               FROM pratiche.fn_pratica_flussi_aperti(p_pratica_id, p_escludi_flusso_id)
           );
$function$

COMMENT ON FUNCTION pratiche.fn_check_pratica_chiudibile(p_pratica_id bigint, p_escludi_template_id integer, p_escludi_flusso_id bigint)
IS 'Pure check: la pratica e'' chiudibile se (a) nessun obbligatorio bloccante (fn_check_chiusura_pratica) E (b) nessun flusso istanziato non terminale (fn_pratica_flussi_aperti, D1). p_escludi_template_id ignora un template dai bloccanti (flusso di chiusura pre-completamento); p_escludi_flusso_id ignora un''istanza dai flussi aperti (il flusso che sta completando). Consumata da auto-chiusura e guard pre-completamento.';
```

</div>

---
{% include-markdown "signature-core.md" %}
