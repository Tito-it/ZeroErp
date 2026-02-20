{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_dati_societari_guard_forma_giuridica.md" %}
# ⚙️ Funzione `trgfn_dati_societari_guard_forma_giuridica`

```sql
CREATE FUNCTION trgfn_dati_societari_guard_forma_giuridica()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_dati_societari_guard_forma_giuridica()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_soggetto_stato_id anagrafiche.soggetti.stato_id%TYPE;
  v_forma_stato_id    config.forme_giuridiche.stato_id%TYPE;
BEGIN
  
  -- Recupera paese del soggetto
  SELECT s.stato_id
    INTO v_soggetto_stato_id
  FROM anagrafiche.soggetti s
  WHERE s.id = NEW.soggetto_id;

  -- Recupera paese della forma giuridica
  SELECT fg.stato_id
    INTO v_forma_stato_id
  FROM config.forme_giuridiche fg
  WHERE fg.id = NEW.forma_giuridica_id;

  -- Se uno dei due è NULL, non possiamo validare in modo deterministico
  --IF v_soggetto_stato_id IS NULL OR v_forma_stato_id IS NULL THEN
  --  RETURN NEW;
  --END IF;

  -- Coerenza paese: deve combaciare
  IF v_soggetto_stato_id <> v_forma_stato_id THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'trgfn_dati_societari_guard_forma_giuridica',
      'E_FORMA_GIURIDICA_PAESE',
      jsonb_build_object(
        'tabella', 'anagrafiche.dati_societari',
        'soggetto_id', NEW.soggetto_id::text,
        'forma_giuridica_id', NEW.forma_giuridica_id::text,
        'soggetto_stato_id', v_soggetto_stato_id::text,
        'forma_stato_id', v_forma_stato_id::text
      ),
      
      NEW.tx_id::uuid,
      NEW.forma_giuridica_id::text,
      NEW.soggetto_id::text
      
    );

    -- Fallback safety (nel caso fn_log_and_raise_error non faccia RAISE)
    --RAISE EXCEPTION 'Forma giuridica non coerente con il paese del soggetto'
      --USING ERRCODE = '23514';
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_dati_societari_guard_forma_giuridica()
IS 'Guard: verifica coerenza paese (stato_id) tra soggetto e forma giuridica. Emette E_FORMA_GIURIDICA_PAESE se incoerente.';
```

---
{% include-markdown "signature-core.md" %}
