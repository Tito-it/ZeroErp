{% include-markdown "it/dbzero/pagamenti/manual/trgfn_vendite_contabili_guard_ente_centro.md" %}
# ⚙️ Funzione `trgfn_vendite_contabili_guard_ente_centro`

```sql
CREATE FUNCTION trgfn_vendite_contabili_guard_ente_centro()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_vendite_contabili_guard_ente_centro()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_centro_ente pagamenti.enti_incasso.centro_riscossione_id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Garantire coerenza tra testata contabile e ente incasso.
  --
  -- Regole:
  --   - se ente_incasso_id e' valorizzato, il suo centro
  --     deve coincidere con centro_riscossione_id della testata
  -- =========================================================

  IF NEW.ente_incasso_id IS NOT NULL THEN
    SELECT ei.centro_riscossione_id
      INTO v_centro_ente
      FROM pagamenti.enti_incasso ei
     WHERE ei.id = NEW.ente_incasso_id;

    IF v_centro_ente IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'pagamenti', TG_NAME, 'E_GENERICO',
        jsonb_build_object(
          'detail', 'ente_incasso senza centro_riscossione valido',
          'ente_incasso_id', NEW.ente_incasso_id
        ),
        NULL::uuid,
        'ente_incasso non valido o privo di centro_riscossione'
      );
    END IF;

    IF NEW.centro_riscossione_id IS DISTINCT FROM v_centro_ente THEN
      PERFORM script.fn_log_and_raise_error(
        'pagamenti', TG_NAME, 'E_GENERICO',
        jsonb_build_object(
          'detail', 'coerenza centro/ente non rispettata',
          'contabile_id', NEW.id,
          'centro_riscossione_id', NEW.centro_riscossione_id,
          'ente_incasso_id', NEW.ente_incasso_id,
          'centro_riscossione_ente', v_centro_ente
        ),
        NULL::uuid,
        'Incoerenza tra centro_riscossione_id testata e centro ente_incasso'
      );
    END IF;
  END IF;

  RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
