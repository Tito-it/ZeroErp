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
  v_fattura_id_riga pagamenti.vendite_contabili_righe.fattura_id%TYPE;
  v_billing_account_id_riga pagamenti.vendite_contabili_righe.billing_account_id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Mantenere coerenti contabile_id/fattura_id/billing_account_id
  --   quando viene valorizzato contabile_riga_id.
  --
  -- Regole:
  --   - derivare i riferimenti dalla riga contabile
  --   - bloccare mismatch su valori passati manualmente
  --
  -- ⚠️ Il guard vale SOLO quando il movimento porta
  --    contabile_riga_id. Un movimento inserito senza riga (la
  --    colonna e' nullable) non lo incontra e sbatte sulla NOT
  --    NULL: non e' il percorso del posting, e' il percorso di chi
  --    scrive a mano.
  --
  -- Rev 2026-08-21 (passo P-7): i cinque E_GENERICO passano ai
  -- codici registrati. Nessun predicato e' cambiato.
  -- =========================================================

  IF NEW.contabile_riga_id IS NOT NULL THEN
    SELECT r.contabile_id, r.fattura_id, r.billing_account_id
      INTO v_contabile_id_riga, v_fattura_id_riga, v_billing_account_id_riga
      FROM pagamenti.vendite_contabili_righe r
     WHERE r.id = NEW.contabile_riga_id;

    -- contabile_id sulla riga e' NOT NULL: se torna nullo, la riga
    -- non esiste.
    IF v_contabile_id_riga IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga', 'E_RIGA_CONTABILE_NON_TROVATA',
        jsonb_build_object(
          'detail', 'contabile_riga_id non valido',
          'campo', 'contabile_riga_id',
          'contabile_riga_id', NEW.contabile_riga_id
        ),
        NULL::uuid,
        NEW.contabile_riga_id::text
      );
    END IF;

    -- ⭐ Il rifiuto centrale del posting: da una riga non abbinata
    --    non si deriva un movimento.
    IF v_fattura_id_riga IS NULL OR v_billing_account_id_riga IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga', 'E_RIGA_CONTABILE_SENZA_ABBINAMENTO',
        jsonb_build_object(
          'detail', 'riga contabile priva di fattura_id o billing_account_id',
          'contabile_riga_id', NEW.contabile_riga_id,
          'fattura_id_riga', v_fattura_id_riga,
          'billing_account_id_riga', v_billing_account_id_riga
        ),
        NULL::uuid,
        NEW.contabile_riga_id::text
      );
    END IF;

    IF NEW.contabile_id IS NOT NULL
       AND NEW.contabile_id IS DISTINCT FROM v_contabile_id_riga THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga', 'E_MOVIMENTO_RIFERIMENTO_INCOERENTE',
        jsonb_build_object(
          'detail', 'contabile_id incoerente con contabile_riga_id',
          'campo', 'contabile_id',
          'contabile_id', NEW.contabile_id,
          'contabile_riga_id', NEW.contabile_riga_id,
          'contabile_id_riga', v_contabile_id_riga
        ),
        NULL::uuid,
        NEW.contabile_riga_id::text, 'contabile_id',
        NEW.contabile_id::text, v_contabile_id_riga::text
      );
    END IF;

    IF NEW.fattura_id IS NOT NULL
       AND NEW.fattura_id IS DISTINCT FROM v_fattura_id_riga THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga', 'E_MOVIMENTO_RIFERIMENTO_INCOERENTE',
        jsonb_build_object(
          'detail', 'fattura_id incoerente con contabile_riga_id',
          'campo', 'fattura_id',
          'fattura_id', NEW.fattura_id,
          'contabile_riga_id', NEW.contabile_riga_id,
          'fattura_id_riga', v_fattura_id_riga
        ),
        NULL::uuid,
        NEW.contabile_riga_id::text, 'fattura_id',
        NEW.fattura_id::text, v_fattura_id_riga::text
      );
    END IF;

    IF NEW.billing_account_id IS NOT NULL
       AND NEW.billing_account_id IS DISTINCT FROM v_billing_account_id_riga THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga', 'E_MOVIMENTO_RIFERIMENTO_INCOERENTE',
        jsonb_build_object(
          'detail', 'billing_account_id incoerente con contabile_riga_id',
          'campo', 'billing_account_id',
          'billing_account_id', NEW.billing_account_id,
          'contabile_riga_id', NEW.contabile_riga_id,
          'billing_account_id_riga', v_billing_account_id_riga
        ),
        NULL::uuid,
        NEW.contabile_riga_id::text, 'billing_account_id',
        NEW.billing_account_id::text, v_billing_account_id_riga::text
      );
    END IF;

    NEW.contabile_id := v_contabile_id_riga;
    NEW.fattura_id := v_fattura_id_riga;
    NEW.billing_account_id := v_billing_account_id_riga;
  END IF;

  RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
