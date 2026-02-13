{% include-markdown "it/dbzero/pagamenti/manual/trgfn_vendite_contabili_lotti_guard_compensazione.md" %}
# ⚙️ Funzione `trgfn_vendite_contabili_lotti_guard_compensazione`

```sql
CREATE FUNCTION trgfn_vendite_contabili_lotti_guard_compensazione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_vendite_contabili_lotti_guard_compensazione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_compensazione_id pagamenti.vendite_contabili.compensazione_id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Impedire l'associazione a lotto di testate contabili
  --   nate da compensazione.
  -- =========================================================

  SELECT vc.compensazione_id
    INTO v_compensazione_id
    FROM pagamenti.vendite_contabili vc
   WHERE vc.id = NEW.contabile_id;

  IF v_compensazione_id IS NOT NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database','pagamenti.trgfn_vendite_contabili_lotti_guard_compensazione' , 'E_GENERICO',
      jsonb_build_object(
        'detail', 'testata compensazione non associabile a lotto',
        'contabile_id', NEW.contabile_id,
        'lotto_id', NEW.lotto_id,
        'compensazione_id', v_compensazione_id
      ),
      NULL::uuid,
      concat('Contabile di compensazione non associabile a lotto',
        ', contabile_id: ', NEW.contabile_id::text,
        ', lotto_id: ', NEW.lotto_id::text,
        ', compensazione_id: ', v_compensazione_id::text
      )
    );
  END IF;

  RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
