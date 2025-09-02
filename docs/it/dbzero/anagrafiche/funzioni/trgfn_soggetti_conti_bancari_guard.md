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
DECLARE
  v_attivo boolean;
BEGIN
  -- Evita legami a conti_bancari disattivati
  SELECT attivo INTO v_attivo
    FROM anagrafiche.conti_bancari
   WHERE id = NEW.conto_bancario_id;
  IF v_attivo IS NOT TRUE THEN
    
    PERFORM anagrafiche.fn_log_and_raise_error(
                        'database',
                        'trgfn_soggetti_conti_bancari_guard',
                        'E_CONTO_BANCARIO',
                        jsonb_build_object(
                          'tabella','anagrafiche.conti_bancari',
                          'conto_bancario_id',  NEW.conto_bancario_id::text,
                          'error', SQLERRM
                        ) , NULL::uuid, NEW.conto_bancario_id::text
                      );

  END IF;

  -- Coerenza validità già controllata da CHECK, ma forziamo normalizzazione date
  IF NEW.valido_dal IS NOT NULL AND NEW.valido_al IS NOT NULL
     AND NEW.valido_al < NEW.valido_dal THEN
    
      PERFORM anagrafiche.fn_log_and_raise_error(
                        'database',
                        'trgfn_soggetti_conti_bancari_guard',
                        'E_DATA_AL_MINORE_DAL',
                        jsonb_build_object(
                          'tabella','anagrafiche.conti_bancari',
                          'data_al',  NEW.data_al::text,
                          'data_dal',  NEW.data_dal::text,
                          'error', SQLERRM
                        ) , NULL::uuid, NEW.data_al::text, NEW.data_dal::text
                      ); 
  END IF;


  RETURN NEW;
END$function$
```

---
{% include-markdown "signature-core.md" %}
