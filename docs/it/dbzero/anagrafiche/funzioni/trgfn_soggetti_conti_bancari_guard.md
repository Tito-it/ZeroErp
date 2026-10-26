{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_conti_bancari_guard.md" %}
# ⚙️ Funzione `trgfn_soggetti_conti_bancari_guard`

```sql
CREATE FUNCTION trgfn_soggetti_conti_bancari_guard()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_conti_bancari_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Guard su anagrafiche.soggetti_conti_bancari: conto attivo.
--
-- rev 2026-08-04 (bonifica riferimenti morti, F4+F5):
--   - anagrafiche.fn_log_and_raise_error non esiste: e' script.
--   - SQLERRM fuori da un blocco EXCEPTION non e' risolvibile.
--   - NEW.data_al / NEW.data_dal non sono colonne di questa
--     tabella: sono valido_al / valido_dal, le stesse gia' usate
--     nell'IF che governa il ramo.
DECLARE
  v_attivo anagrafiche.conti_bancari.attivo%TYPE;
BEGIN
  -- Evita legami a conti_bancari disattivati
  SELECT attivo INTO v_attivo
    FROM anagrafiche.conti_bancari
   WHERE id = NEW.conto_bancario_id;
  IF v_attivo IS NOT TRUE THEN

    PERFORM script.fn_log_and_raise_error(
                        'database',
                        'trgfn_soggetti_conti_bancari_guard',
                        'E_CONTO_BANCARIO',
                        jsonb_build_object(
                          'campo', 'conto_bancario_id',
                          'tabella','anagrafiche.conti_bancari',
                          'conto_bancario_id',  NEW.conto_bancario_id::text
                        ) , NULL::uuid, NEW.conto_bancario_id::text
                      );

  END IF;

  -- rev 20260923-44: la coerenza delle date non e' piu' qui. Ha una sede
  --   sola, script.trgfn_guard_date_validita, montata dall'automazione
  --   DATE_VALIDITA su ogni tabella con valido_dal/valido_al — questa compresa.

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_conti_bancari_guard()
IS 'Guard-rail su anagrafiche.soggetti_conti_bancari: blocca uso di conti_bancari non attivi. Rev 20260923-44: la coerenza delle date (valido_al non precede valido_dal) non e'' piu'' qui, ha una sede sola: script.trgfn_guard_date_validita (automazione DATE_VALIDITA).';
```

</div>

---
{% include-markdown "signature-core.md" %}
