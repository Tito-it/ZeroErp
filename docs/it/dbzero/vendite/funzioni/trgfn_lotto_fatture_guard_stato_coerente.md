{% include-markdown "it/dbzero/vendite/manual/trgfn_lotto_fatture_guard_stato_coerente.md" %}
# ⚙️ Funzione `trgfn_lotto_fatture_guard_stato_coerente`

```sql
CREATE FUNCTION trgfn_lotto_fatture_guard_stato_coerente()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_lotto_fatture_guard_stato_coerente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_lotto_id vendite.fatturazione_lotti.id%TYPE;
BEGIN
  IF TG_TABLE_NAME = 'fatturazione_lotti' THEN
    -- Il lotto si e' mosso: verifica le sue fatture.
    PERFORM vendite.fn_guard_lotto_fatture_stato_coerente(NEW.id);

  ELSIF TG_TABLE_NAME = 'fatture' THEN
    -- La fattura si e' mossa: verifica ogni lotto che la contiene
    -- (lo schema del ponte ammette 1:N, anche se oggi e' 1:1).
    FOR v_lotto_id IN
      SELECT DISTINCT lf.lotto_id
        FROM vendite.fatturazione_lotti_fatture lf
       WHERE lf.fattura_id = NEW.id
    LOOP
      PERFORM vendite.fn_guard_lotto_fatture_stato_coerente(v_lotto_id);
    END LOOP;

  ELSIF TG_TABLE_NAME = 'fatturazione_lotti_fatture' THEN
    -- Il legame e' cambiato (aggancio/sgancio/esclusione): il
    -- perimetro dell'invariante cambia, quindi si riverifica.
    IF TG_OP = 'DELETE' THEN
      v_lotto_id := OLD.lotto_id;
    ELSE
      v_lotto_id := NEW.lotto_id;
    END IF;
    PERFORM vendite.fn_guard_lotto_fatture_stato_coerente(v_lotto_id);

    -- Su UPDATE il lotto puo' essere cambiato: verifica anche il vecchio.
    IF TG_OP = 'UPDATE' AND OLD.lotto_id IS DISTINCT FROM NEW.lotto_id THEN
      PERFORM vendite.fn_guard_lotto_fatture_stato_coerente(OLD.lotto_id);
    END IF;
  END IF;

  -- AFTER trigger: il valore di ritorno e' ignorato.
  RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_lotto_fatture_guard_stato_coerente()
IS 'Trigger function condivisa dai constraint trigger DEFERRED su vendite.fatture, vendite.fatturazione_lotti e vendite.fatturazione_lotti_fatture: risolve i lotti impattati dalla riga e delega a vendite.fn_guard_lotto_fatture_stato_coerente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
