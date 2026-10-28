{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_ruoli_conti_bancari_guard.md" %}
# ⚙️ Funzione `trgfn_soggetti_ruoli_conti_bancari_guard`

```sql
CREATE FUNCTION trgfn_soggetti_ruoli_conti_bancari_guard()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_ruoli_conti_bancari_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Guard su anagrafiche.soggetti_ruoli_conti_bancari.
--
-- rev 2026-08-04 (bonifica riferimenti morti, F4):
--   - TGNAME -> TG_NAME (la variabile speciale ha l'underscore;
--     senza, plpgsql la risolve come colonna e non la trova).
--   - anagrafiche.fn_log_and_raise_error non esiste: e' script.
DECLARE
  v_attivo anagrafiche.conti_bancari.attivo%TYPE;
BEGIN
  -- Evita legami a conti disattivati
  SELECT attivo INTO v_attivo
    FROM anagrafiche.conti_bancari
  WHERE id = NEW.conto_bancario_id;
  IF v_attivo IS NOT TRUE THEN

    PERFORM script.fn_log_and_raise_error(
                        'database',
                        TG_NAME,
                        'E_CONTO_BANCARIO',
                        jsonb_build_object(
                          'campo', 'conto_bancario_id',
                          'tabella','soggetti_ruoli_conti_bancari',
                          'conto_bancario_id',  NEW.conto_bancario_id::text
                        ) ,
                         NEW.tx_id::uuid,
                         NEW.conto_bancario_id::text
                      );
  END IF;

  -- rev 20260923-45: la coerenza delle date non e' piu' qui. Ha una sede
  --   sola, script.trgfn_guard_date_validita, montata dall'automazione
  --   DATE_VALIDITA su ogni tabella con valido_dal/valido_al — questa compresa.
  RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_ruoli_conti_bancari_guard()
IS 'Guard-rail: impedisce uso di conti non attivi. Rev 20260923-45: la coerenza delle date (valido_al non precede valido_dal) non e'' piu'' qui, ha una sede sola: script.trgfn_guard_date_validita (automazione DATE_VALIDITA).';
```

</div>

---
{% include-markdown "signature-core.md" %}
