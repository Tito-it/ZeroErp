{% include-markdown "it/dbzero/vendite/manual/trgfn_fatturazione_lotti_guard_stato_job.md" %}
# ⚙️ Funzione `trgfn_fatturazione_lotti_guard_stato_job`

```sql
CREATE FUNCTION trgfn_fatturazione_lotti_guard_stato_job()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatturazione_lotti_guard_stato_job()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- ==========================================================
    -- Scopo: la sola regola dei passaggi dello stato del job di
    --   un lotto (stato_lotto), letta dalla matrice. Riscrivere
    --   lo stesso stato passa.
    -- rev 2026-10-27 (20261027-06, brief-modello-documento-
    --   vendita §15, F-4): nasce; la copia del backend si ritira.
    -- ==========================================================
    IF NEW.stato_lotto IS NOT DISTINCT FROM OLD.stato_lotto THEN
        RETURN NEW;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM config.transizioni_stati_lotto_job t
          JOIN config.stati_lotto_job sd ON sd.id = t.stato_da_id
          JOIN config.stati_lotto_job sa ON sa.id = t.stato_a_id
         WHERE t.attivo IS TRUE
           AND sd.codice_interno = OLD.stato_lotto
           AND sa.codice_interno = NEW.stato_lotto
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            TG_TABLE_SCHEMA, TG_NAME, 'E_LOTTO_PARAMETRO_NON_COERENTE',
            jsonb_build_object('parametro', 'transizione_stato_lotto',
                               'lotto_id', NEW.id,
                               'da', OLD.stato_lotto,
                               'a', NEW.stato_lotto),
            NEW.tx_id,
            concat('stato del job ', OLD.stato_lotto, ' -> ', NEW.stato_lotto,
                   ' non ammesso (config.transizioni_stati_lotto_job)'),
            NEW.id::text);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fatturazione_lotti_guard_stato_job()
IS 'Guard (BEFORE UPDATE OF stato_lotto su vendite.fatturazione_lotti): la sola regola dei passaggi dello stato del JOB del lotto. Un cambio di stato e'' ammesso se config.transizioni_stati_lotto_job ha la riga attiva (da, a), letta per codice_interno (la colonna del lotto porta il codice, P-1); riscrivere lo stesso stato passa. Altrimenti E_LOTTO_PARAMETRO_NON_COERENTE (parametro transizione_stato_lotto, con da e a nel contesto). Lo stato fuori vocabolario lo rifiuta la FK fk_fatturazione_lotti_stato_lotto; il fermo del lotto (COMPLETATO solo se non fermo) resta di trgfn_fatturazione_lotti_guard_completato. Prima la regola era scritta due volte, in disaccordo: nel backend (pipeline_repository.set_lotto_job_stato, l''unico scrittore) e in vendite.fn_set_fatturazione_lotto_stato (morta, ritirata). Brief: brief-modello-documento-vendita §15 (F-4, Q-F4, Tid 2026-10-27).';
```

</div>

---
{% include-markdown "signature-core.md" %}
