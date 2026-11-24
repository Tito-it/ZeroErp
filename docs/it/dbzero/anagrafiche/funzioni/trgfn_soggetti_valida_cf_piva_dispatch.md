{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_valida_cf_piva_dispatch.md" %}
# ⚙️ Funzione `trgfn_soggetti_valida_cf_piva_dispatch`

```sql
CREATE FUNCTION trgfn_soggetti_valida_cf_piva_dispatch()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_paese config.stati.codice_iso2%TYPE;
BEGIN
    SELECT st.codice_iso2 INTO v_paese
      FROM config.stati st
     WHERE st.id = NEW.stato_id;

    -- Le regole scritte oggi sono quelle italiane: uno stato senza
    -- validatore passa (guida soggetti-e-ruoli-anagrafici).
    IF v_paese = 'IT' THEN
        PERFORM script.fn_validate_cf_piva_it(
            NEW.tipo_soggetto_dettaglio_id,
            NEW.partita_iva,
            NEW.piva_gruppo_acquisto,
            NEW.codice_fiscale);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch()
IS 'Guard del FORMATO di codice_fiscale, partita_iva e piva_gruppo_acquisto di anagrafiche.soggetti, per paese: per IT script.fn_validate_cf_piva_it (E_CF_NON_VALIDO / E_PIVA_NON_VALIDA, con campo); uno stato senza validatore passa. La PRESENZA la giudica trgfn_soggetti_guard_cf_piva_obbligatori. Montata due volte in fase a10: trg_soggetti_a10_valida_cf_piva_ins (BEFORE INSERT) e trg_soggetti_a10_valida_cf_piva_upd (BEFORE UPDATE WHEN cambia CF, P.IVA, P.IVA di gruppo, stato o natura): un soggetto con un CF non piu'' accettato resta modificabile negli altri campi (S43-2, brief-db-revisione-anagrafiche §20, 2026-11-23). Legge i valori gia'' normalizzati da trgfn_soggetti_normalize (a01).';
```

</div>

---
{% include-markdown "signature-core.md" %}
