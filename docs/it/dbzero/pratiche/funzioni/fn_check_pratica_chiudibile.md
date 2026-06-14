{% include-markdown "it/dbzero/pratiche/manual/fn_check_pratica_chiudibile.md" %}
# ⚙️ Funzione `fn_check_pratica_chiudibile`

```sql
CREATE FUNCTION fn_check_pratica_chiudibile(p_pratica_id bigint, p_escludi_template_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_check_pratica_chiudibile(p_pratica_id bigint, p_escludi_template_id integer DEFAULT NULL::integer)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
-- Scopo: fn_check_* puro (no raise). La pratica e' chiudibile se
--   non resta alcun template obbligatorio "bloccante" (obbligatorio,
--   non completato, ancora percorribile) in fn_check_chiusura_pratica.
-- p_escludi_template_id: se valorizzato, ignora quel template dai
--   bloccanti (usato dal guard pre-completamento per escludere il
--   flusso di chiusura stesso, non ancora COMPLETATO).
    SELECT NOT EXISTS (
        SELECT 1
          FROM pratiche.fn_check_chiusura_pratica(p_pratica_id) c
         WHERE c.bloccante
           AND (p_escludi_template_id IS NULL
                OR c.template_flusso_id <> p_escludi_template_id)
    );
$function$

COMMENT ON FUNCTION pratiche.fn_check_pratica_chiudibile(p_pratica_id bigint, p_escludi_template_id integer)
IS 'Pure check: la pratica e'' chiudibile (nessun obbligatorio bloccante in fn_check_chiusura_pratica). p_escludi_template_id ignora un template dal calcolo (es. il flusso di chiusura prima del suo completamento). Consumata da auto-chiusura e guard pre-completamento.';
```

---
{% include-markdown "signature-core.md" %}
