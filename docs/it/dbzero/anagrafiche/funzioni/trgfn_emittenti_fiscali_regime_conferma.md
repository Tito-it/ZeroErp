{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_emittenti_fiscali_regime_conferma.md" %}
# ⚙️ Funzione `trgfn_emittenti_fiscali_regime_conferma`

```sql
CREATE FUNCTION trgfn_emittenti_fiscali_regime_conferma()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_emittenti_fiscali_regime_conferma()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: chi scrive il regime fiscale lo DICHIARA; data e autore
--   della conferma li deriva questa funzione, mai il chiamante.
-- Uso:   BEFORE UPDATE OF regime_fiscale_rf FOR EACH ROW (a20).
--   Il guard a10 trgfn_emittenti_fiscali_guard_regime_conferma
--   ha gia' rifiutato chi scriveva le due colonne da fuori.
BEGIN
    -- Riempire un regime vuoto e' il default D-1 applicato dopo
    -- (backfill 20261001-16), non una scelta di qualcuno: la
    -- conferma resta com'era, cioe' vuota.
    IF NULLIF(btrim(OLD.regime_fiscale_rf), '') IS NULL THEN
        RETURN NEW;
    END IF;

    -- UPDATE OF scatta anche quando la colonna e' riscritta con lo
    -- stesso valore, ed e' voluto: e' cosi' che si conferma un
    -- regime senza cambiarlo.
    NEW.regime_fiscale_confermato_il := now();
    NEW.regime_fiscale_confermato_da := COALESCE(
        NULLIF(btrim(current_setting('app.jwt_user', true)), ''),
        CURRENT_USER);
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_emittenti_fiscali_regime_conferma()
IS 'Deriva la conferma del regime fiscale (trigger a20, BEFORE UPDATE OF regime_fiscale_rf): un UPDATE che nomina il regime, anche con lo stesso valore, e'' una dichiarazione, e scrive regime_fiscale_confermato_il = now() e regime_fiscale_confermato_da = app.jwt_user (CURRENT_USER se la GUC manca). Un UPDATE che non nomina il regime non tocca la conferma; la INSERT non conferma mai; riempire un regime vuoto (il backfill del default RF01, D-1) non e'' una dichiarazione. Le due colonne non si scrivono da fuori: lo rifiuta il guard a10 trgfn_emittenti_fiscali_guard_regime_conferma. Non solleva. Brief: brief-db-esigibilita-iva-per-cassa-emittente (sezione 10, revisione di D-11).';
```

</div>

---
{% include-markdown "signature-core.md" %}
