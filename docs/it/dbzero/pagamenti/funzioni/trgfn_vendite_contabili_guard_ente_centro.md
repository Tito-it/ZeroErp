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
  v_is_compensazione pagamenti.centri_riscossione.is_compensazione%TYPE;
  v_has_lotto_link boolean := false;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Garantire coerenza della testata contabile:
  --   - centro/ente incasso
  --   - regole di compensazione
  --
  -- Rev 2026-08-21 (passo P-7): i quattro E_GENERICO passano ai
  -- codici registrati. Nessun predicato e' cambiato.
  -- =========================================================

  -- 1) Coerenza ente_incasso -> centro_riscossione.
  IF NEW.ente_incasso_id IS NOT NULL THEN
    SELECT ei.centro_riscossione_id
      INTO v_centro_ente
      FROM pagamenti.enti_incasso ei
     WHERE ei.id = NEW.ente_incasso_id;

    -- ⚠️ Due cause, un codice: l'ente non esiste, oppure esiste e
    --    non ha centro (la colonna e' nullable). Stesso rimedio:
    --    si va a guardare l'ente.
    IF v_centro_ente IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.trgfn_vendite_contabili_guard_ente_centro', 'E_ENTE_INCASSO_SENZA_CENTRO',
        jsonb_build_object(
          'detail', 'ente_incasso senza centro_riscossione valido',
          'campo', 'ente_incasso_id',
          'ente_incasso_id', NEW.ente_incasso_id
        ),
        NULL::uuid,
        NEW.ente_incasso_id::text
      );
    END IF;

    IF NEW.centro_riscossione_id IS DISTINCT FROM v_centro_ente THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.trgfn_vendite_contabili_guard_ente_centro', 'E_CONTABILE_CENTRO_ENTE_INCOERENTE',
        jsonb_build_object(
          'detail', 'coerenza centro/ente non rispettata',
          'campo', 'centro_riscossione_id',
          'contabile_id', NEW.id,
          'centro_riscossione_id', NEW.centro_riscossione_id,
          'ente_incasso_id', NEW.ente_incasso_id,
          'centro_riscossione_ente', v_centro_ente
        ),
        NULL::uuid,
        NEW.centro_riscossione_id::text,
        NEW.ente_incasso_id::text,
        v_centro_ente::text
      );
    END IF;
  END IF;

  -- 2) Regole specifiche compensazione.
  IF NEW.compensazione_id IS NOT NULL THEN
    SELECT c.is_compensazione
      INTO v_is_compensazione
      FROM pagamenti.centri_riscossione c
     WHERE c.id = NEW.centro_riscossione_id;

    -- ⚠️ Dal 2026-08-21 (20260821-11) il centro di compensazione e'
    --    UNICO per costruzione: indice unico parziale su
    --    is_compensazione. Prima l'unicita' era solo dichiarata.
    IF COALESCE(v_is_compensazione, false) IS FALSE THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.trgfn_vendite_contabili_guard_ente_centro', 'E_CENTRO_NON_ABILITATO_COMPENSAZIONE',
        jsonb_build_object(
          'detail', 'centro_riscossione non abilitato a compensazione',
          'campo', 'centro_riscossione_id',
          'contabile_id', NEW.id,
          'centro_riscossione_id', NEW.centro_riscossione_id,
          'compensazione_id', NEW.compensazione_id
        ),
        NULL::uuid,
        NEW.centro_riscossione_id::text
      );
    END IF;

    IF NEW.id IS NOT NULL THEN
      SELECT EXISTS (
        SELECT 1
          FROM pagamenti.vendite_contabili_lotti vcl
         WHERE vcl.contabile_id = NEW.id
      )
        INTO v_has_lotto_link;

      -- ⭐ Stesso codice del guard gemello sui lotti: e' la stessa
      --    regola letta nel verso opposto. Il messaggio ha un solo
      --    segnaposto perche' questa porta non conosce il lotto.
      IF v_has_lotto_link THEN
        PERFORM script.fn_log_and_raise_error(
          'database', 'pagamenti.trgfn_vendite_contabili_guard_ente_centro', 'E_CONTABILE_COMPENSAZIONE_CON_LOTTO',
          jsonb_build_object(
            'detail', 'testata compensazione non compatibile con link lotto',
            'contabile_id', NEW.id,
            'compensazione_id', NEW.compensazione_id
          ),
          NULL::uuid,
          NEW.id::text
        );
      END IF;
    END IF;
  END IF;

  RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
