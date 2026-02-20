{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_ruoli_conti_bancari_guard.md" %}
# ⚙️ Funzione `trgfn_soggetti_ruoli_conti_bancari_guard`

```sql
CREATE FUNCTION trgfn_soggetti_ruoli_conti_bancari_guard()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_ruoli_conti_bancari_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_attivo boolean;
BEGIN
  -- Evita legami a conti disattivati
  SELECT attivo INTO v_attivo
    FROM anagrafiche.conti_bancari
  WHERE id = NEW.conto_bancario_id;
  IF v_attivo IS NOT TRUE THEN

    PERFORM anagrafiche.fn_log_and_raise_error(
                        'database',
                        TGNAME,
                        'E_CONTO_BANCARIO',
                        jsonb_build_object(
                          'tabella','soggetti_ruoli_conti_bancari',
                          'conto_bancario_id',  NEW.conto_bancario_id::text
                        ) , 
                         NEW.tx_id::uuid,
                         NEW.conto_bancario_id::text
                      ); 
  END IF;

  -- Coerenza date
  IF NEW.valido_dal IS NOT NULL AND NEW.valido_al IS NOT NULL
    AND NEW.valido_al < NEW.valido_dal THEN

        PERFORM anagrafiche.fn_log_and_raise_error(
                        'database',
                        TGNAME,
                        'E_DATA_AL_MINORE_DAL',
                        jsonb_build_object(
                          'tabella','anagrafiche.soggetti_ruoli_conti_bancari',
                          'valido_al',  NEW.valido_al::text,
                          'valido_dal',  NEW.valido_dal::text
                        ) , 
                        NEW.tx_id::uuid, 
                        NEW.valido_al::text, NEW.valido_dal::text
                      ); 
  END IF;
  RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_ruoli_conti_bancari_guard()
IS 'Guard-rail: impedisce uso di conti non attivi, 
controlla coerenza date e cura audit base.';
```

---
{% include-markdown "signature-core.md" %}
