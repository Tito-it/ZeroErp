{% include-markdown "it/dbzero/pagamenti/manual/trgfn_vendite_movimenti_sync_contabile_from_riga.md" %}
# ⚙️ Funzione `trgfn_vendite_movimenti_sync_contabile_from_riga`

```sql
CREATE FUNCTION trgfn_vendite_movimenti_sync_contabile_from_riga()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_contabile_id_riga pagamenti.vendite_contabili_righe.contabile_id%TYPE;
  v_fattura_id_riga pagamenti.vendite_contabili_righe.fattura_id%TYPE;
  v_billing_account_id_riga pagamenti.vendite_contabili_righe.billing_account_id%TYPE;
  v_scadenza_id_riga pagamenti.vendite_contabili_righe.scadenza_id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Mantenere coerenti contabile_id/fattura_id/
  --   billing_account_id/scadenza_id quando viene valorizzato
  --   contabile_riga_id.
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
  -- Rev 2026-08-22 (S2-2): si copia anche scadenza_id. Da tre
  -- riferimenti a quattro, stesso meccanismo e stesso rifiuto.
  -- =========================================================

  IF NEW.contabile_riga_id IS NOT NULL THEN
    SELECT r.contabile_id, r.fattura_id, r.billing_account_id, r.scadenza_id
      INTO v_contabile_id_riga, v_fattura_id_riga, v_billing_account_id_riga, v_scadenza_id_riga
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

    -- ⭐ S2-2: la rata. Stesso meccanismo dei tre sopra — se il
    --    chiamante ne passa una diversa da quella della riga, il
    --    movimento racconterebbe un'altra storia.
    IF NEW.scadenza_id IS NOT NULL
       AND NEW.scadenza_id IS DISTINCT FROM v_scadenza_id_riga THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga', 'E_MOVIMENTO_RIFERIMENTO_INCOERENTE',
        jsonb_build_object(
          'detail', 'scadenza_id incoerente con contabile_riga_id',
          'campo', 'scadenza_id',
          'scadenza_id', NEW.scadenza_id,
          'contabile_riga_id', NEW.contabile_riga_id,
          'scadenza_id_riga', v_scadenza_id_riga
        ),
        NULL::uuid,
        NEW.contabile_riga_id::text, 'scadenza_id',
        NEW.scadenza_id::text, COALESCE(v_scadenza_id_riga::text, 'nessuna rata')
      );
    END IF;

    NEW.contabile_id := v_contabile_id_riga;
    NEW.fattura_id := v_fattura_id_riga;
    NEW.billing_account_id := v_billing_account_id_riga;
    NEW.scadenza_id := v_scadenza_id_riga;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga()
IS 'Deriva dalla riga contabile i riferimenti del movimento e rifiuta chi ne passa uno diverso. ⭐ rev 2026-08-22 (S2-2): i riferimenti copiati passano da TRE a QUATTRO — si aggiunge scadenza_id, la rata. E'' cio'' che impedisce alla colonna nuova sul movimento di diventare una SECONDA SORGENTE DI VERITA'': non la scrive il chiamante, la deriva il mirror, ed e'' una copia buona per leggere senza passare dalla riga (che puo'' essere disattivata o vivere sotto una distinta annullata). ⚠️ Il guard vale SOLO quando il movimento porta contabile_riga_id: un movimento inserito senza riga non lo incontra e sbatte sulla NOT NULL — non e'' il percorso del posting, e'' il percorso di chi scrive a mano. Era vero prima e resta vero. rev 2026-08-21 (P-7): i cinque E_GENERICO sono passati ai codici registrati, nessun predicato cambiato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
