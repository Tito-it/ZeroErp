{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_conti_bancari_guard.md" %}
# ⚙️ Funzione `trgfn_soggetti_conti_bancari_guard`

```sql
CREATE FUNCTION trgfn_soggetti_conti_bancari_guard()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_conti_bancari_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Guard su anagrafiche.soggetti_conti_bancari.
--
-- rev 2026-08-04 (bonifica riferimenti morti, F4+F5):
--   - anagrafiche.fn_log_and_raise_error non esiste: e' script.
--   - SQLERRM fuori da un blocco EXCEPTION non e' risolvibile.
--   - NEW.data_al / NEW.data_dal non sono colonne di questa
--     tabella: sono valido_al / valido_dal, le stesse gia' usate
--     nell'IF che governa il ramo.
DECLARE
  v_attivo boolean;
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

  -- Coerenza validità già controllata da CHECK, ma forziamo normalizzazione date
  IF NEW.valido_dal IS NOT NULL AND NEW.valido_al IS NOT NULL
     AND NEW.valido_al < NEW.valido_dal THEN

      PERFORM script.fn_log_and_raise_error(
                        'database',
                        'trgfn_soggetti_conti_bancari_guard',
                        'E_DATA_AL_MINORE_DAL',
                        jsonb_build_object(
                          'tabella','anagrafiche.soggetti_conti_bancari',
                          'valido_al',  NEW.valido_al::text,
                          'valido_dal',  NEW.valido_dal::text
                        ) , NULL::uuid, NEW.valido_al::text, NEW.valido_dal::text
                      );
  END IF;


  RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_conti_bancari_guard()
IS 'Guard-rail su anagrafiche.soggetti_conti_bancari: blocca uso di conti_bancari non attivi e normalizza coerenza date/audit.';
```

---
{% include-markdown "signature-core.md" %}
