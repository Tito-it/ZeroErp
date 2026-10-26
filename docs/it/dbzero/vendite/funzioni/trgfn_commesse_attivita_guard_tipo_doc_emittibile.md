{% include-markdown "it/dbzero/vendite/manual/trgfn_commesse_attivita_guard_tipo_doc_emittibile.md" %}
# ⚙️ Funzione `trgfn_commesse_attivita_guard_tipo_doc_emittibile`

```sql
CREATE FUNCTION trgfn_commesse_attivita_guard_tipo_doc_emittibile()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_commesse_attivita_guard_tipo_doc_emittibile()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: invariante di riga. Una riga commesse_attivita in stato
--   emittibile (APPROVATA + NON_EMESSA) deve avere tipo_doc_fiscale_id
--   valorizzato, altrimenti sarebbe invisibile alla discovery delle
--   corsie di fatturazione (fn_list_emittibili_lane) e il fatturato
--   andrebbe perso in silenzio. Fail-fast con codice parlante.
BEGIN
    IF NEW.stato_approvazione = 'APPROVATA'
       AND NEW.stato_emissione = 'NON_EMESSA'
       AND NEW.tipo_doc_fiscale_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO',
            jsonb_build_object(
                'campo', 'tipo_doc_fiscale_id',
                'commessa_id', NEW.commessa_id,
                'attivita_id', NEW.id,
                'segment_key', NEW.segment_key
            ),
            NEW.tx_id,
            NEW.commessa_id::text,
            NEW.id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_commesse_attivita_guard_tipo_doc_emittibile()
IS 'Trigger function: invariante di riga commesse_attivita. (APPROVATA + NON_EMESSA) => tipo_doc_fiscale_id NOT NULL (E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO). Evita righe emittibili invisibili alla discovery delle corsie. rev 2026-06-19.';
```

</div>

---
{% include-markdown "signature-core.md" %}
