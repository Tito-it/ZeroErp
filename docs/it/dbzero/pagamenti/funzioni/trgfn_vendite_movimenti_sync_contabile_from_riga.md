{% include-markdown "it/dbzero/pagamenti/manual/trgfn_vendite_movimenti_sync_contabile_from_riga.md" %}
# ⚙️ Funzione `trgfn_vendite_movimenti_sync_contabile_from_riga`

```sql
CREATE FUNCTION trgfn_vendite_movimenti_sync_contabile_from_riga()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_contabile_id_riga pagamenti.vendite_contabili_righe.contabile_id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Mantenere coerente contabile_id con contabile_riga_id.
  --
  -- Regole:
  --   - se contabile_riga_id e' valorizzato, contabile_id viene
  --     derivato dalla riga contabile
  --   - se contabile_id e' passato ma incoerente, errore
  -- =========================================================

  IF NEW.contabile_riga_id IS NOT NULL THEN
    SELECT r.contabile_id
      INTO v_contabile_id_riga
      FROM pagamenti.vendite_contabili_righe r
     WHERE r.id = NEW.contabile_riga_id;

    IF v_contabile_id_riga IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga', 'E_GENERICO',
        jsonb_build_object(
          'detail', 'contabile_riga_id non valido',
          'contabile_riga_id', NEW.contabile_riga_id
        ),
        NULL::uuid,
        'contabile_riga_id non valido'
      );
    END IF;

    IF NEW.contabile_id IS NOT NULL
       AND NEW.contabile_id IS DISTINCT FROM v_contabile_id_riga THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga', 'E_GENERICO',
        jsonb_build_object(
          'detail', 'contabile_id incoerente con contabile_riga_id',
          'contabile_id', NEW.contabile_id,
          'contabile_riga_id', NEW.contabile_riga_id,
          'contabile_id_riga', v_contabile_id_riga
        ),
        NULL::uuid,
        concat('contabile_id incoerente con contabile_riga_id: ', NEW.contabile_id, ' != ', v_contabile_id_riga)
      );
    END IF;

    NEW.contabile_id := v_contabile_id_riga;
  END IF;

  RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
