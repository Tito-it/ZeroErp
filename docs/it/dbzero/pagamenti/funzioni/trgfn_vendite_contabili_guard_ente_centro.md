{% include-markdown "it/dbzero/pagamenti/manual/trgfn_vendite_contabili_guard_ente_centro.md" %}
# ⚙️ Funzione `trgfn_vendite_contabili_guard_ente_centro`

```sql
CREATE FUNCTION trgfn_vendite_contabili_guard_ente_centro()
```

**Definizione completa:**

<div data-search-exclude markdown>

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
  --   Coerenza fra il CANALE e il CENTRO della testata contabile.
  --
  -- Rev 2026-08-22 (lotto 7, D15-e): il ramo 2 — «regole
  --   specifiche compensazione» — e' stato tolto. Si apriva su
  --   NEW.compensazione_id, e quella colonna non esiste piu':
  --   girato il verso del legame, la contabile non sa piu' di
  --   essere nata da un atto, lo sa l'atto. Le due regole non
  --   sono sparite, hanno cambiato casa:
  --     * il centro dedicato -> pagamenti.trgfn_sistemazioni_guard_dati
  --     * il divieto di lotto -> pagamenti.trgfn_vendite_contabili_lotti_guard_sistemazione
  --   ⭐ Vanno dove il dato che le rende decidibili esiste
  --   davvero: un controllo che scatta quando l'informazione non
  --   c'e' ancora non e' un presidio, e' una decorazione.
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

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION pagamenti.trgfn_vendite_contabili_guard_ente_centro()
IS 'Coerenza fra il CANALE e il CENTRO della testata contabile: un ente di incasso deve avere un centro, e dev''essere quello della distinta. ⭐ Dal lotto 6 il canale porta anche il CONTO su cui atterra il denaro, ed e'' il perimetro: questo guard e'' cio'' che tiene insieme le due cose. ⚠️ Rev 2026-08-22 (lotto 7, D15-e): tolto il ramo «regole specifiche compensazione», che si apriva su NEW.compensazione_id — colonna sparita girando il verso del legame. Le due regole hanno cambiato casa e non sono state perse: il centro dedicato vive su trgfn_sistemazioni_guard_dati, il divieto di aggancio al lotto su trgfn_vendite_contabili_lotti_guard_sistemazione. Un controllo che scatta quando l''informazione non c''e'' ancora non e'' un presidio: alla nascita della distinta nessun atto la cita.';
```

</div>

---
{% include-markdown "signature-core.md" %}
