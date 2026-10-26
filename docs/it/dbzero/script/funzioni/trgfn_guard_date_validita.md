# ⚙️ Funzione `trgfn_guard_date_validita`

```sql
CREATE FUNCTION trgfn_guard_date_validita()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_guard_date_validita()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: la regola del PERIODO — valido_al non precede
--   valido_dal — in un posto solo, per ogni tabella che porta la
--   coppia di date. Si giudica solo con entrambe le date presenti.
-- Montaggio: dbops.fn_run_automations_date_validita (regola
--   DATE_VALIDITA), BEFORE INSERT OR UPDATE OF valido_dal,
--   valido_al: prima del calcolo di `validita` generata, che
--   altrimenti rifiuterebbe con una frase tecnica (22000).
BEGIN
    IF NEW.valido_dal IS NOT NULL
       AND NEW.valido_al IS NOT NULL
       AND NEW.valido_al < NEW.valido_dal THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.trgfn_guard_date_validita',
            'E_DATA_AL_MINORE_DAL',
            jsonb_build_object(
                'campo',      'valido_al',
                'tabella',    TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'valido_dal', NEW.valido_dal,
                'valido_al',  NEW.valido_al),
            NULL::uuid,
            NEW.valido_al::text,
            NEW.valido_dal::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_guard_date_validita()
IS 'Building block: il guard della regola del PERIODO — valido_al non precede valido_dal — per ogni tabella con la coppia di date. Solleva E_DATA_AL_MINORE_DAL (DATO_ERRATO) con campo valido_al, e giudica solo quando le due date ci sono entrambe (la semantica dei CHECK). ⭐ Lo monta l''automazione DATE_VALIDITA (dbops.fn_run_automations_date_validita) sulla sola presenza delle due colonne, BEFORE INSERT OR UPDATE OF valido_dal, valido_al: i BEFORE girano prima del calcolo di `validita` generata, che altrimenti rifiuterebbe per primo con la frase tecnica del daterange (22000). ⚠️ I CHECK sulle date restano: sono la regola dichiarata e l''ultima difesa. Brief: brief-db-guard-date-validita.md';
```

</div>

---
{% include-markdown "signature-core.md" %}
