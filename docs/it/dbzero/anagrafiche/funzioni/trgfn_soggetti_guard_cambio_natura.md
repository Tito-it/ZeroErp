{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_guard_cambio_natura.md" %}
# ⚙️ Funzione `trgfn_soggetti_guard_cambio_natura`

```sql
CREATE FUNCTION trgfn_soggetti_guard_cambio_natura()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_guard_cambio_natura()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: un soggetto cambia natura solo se nessun motivo lo
--   impedisce. I motivi li elenca, tutti e in ordine,
--   anagrafiche.fn_check_cambio_natura_soggetto; qui si solleva
--   il primo. Il cambio non pulisce niente.
-- Aggancio: BEFORE UPDATE, WHEN la natura cambia. I valori della
--   riga entrano come NEW: chi corregge un flag o la P.IVA nello
--   stesso salvataggio passa.
-- =========================================================
BEGIN
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'database',
        'anagrafiche.trgfn_soggetti_guard_cambio_natura',
        anagrafiche.fn_check_cambio_natura_soggetto(
            NEW.id, NEW.tipo_soggetto_dettaglio_id,
            NEW.partita_iva, NEW.cliente_pa, NEW.split_payment),
        NULL,
        NEW.tx_id);
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_guard_cambio_natura()
IS 'Guard BEFORE UPDATE su anagrafiche.soggetti, quando la natura di dettaglio cambia: solleva il primo motivo di anagrafiche.fn_check_cambio_natura_soggetto, calcolato coi valori proposti della riga (partita_iva, cliente_pa, split_payment), con script.fn_raise_primo_motivo_se_presente; il campo e tutti i motivi viaggiano nel contesto. Il cambio non pulisce niente: chi agisce toglie i motivi e riprova.';
```

</div>

---
{% include-markdown "signature-core.md" %}
