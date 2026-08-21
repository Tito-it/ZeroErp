{% include-markdown "it/dbzero/pagamenti/manual/trgfn_vendite_contabili_guard_validazione.md" %}
# ⚙️ Funzione `trgfn_vendite_contabili_guard_validazione`

```sql
CREATE FUNCTION trgfn_vendite_contabili_guard_validazione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_vendite_contabili_guard_validazione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_stato_da  pagamenti.vendite_contabili_stati.codice_interno%TYPE;
    v_stato_a   pagamenti.vendite_contabili_stati.codice_interno%TYPE;
    v_somma     pagamenti.vendite_contabili_righe.importo%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Le CONDIZIONI su una transizione che la matrice
    --   (stato_da, stato_a) non puo' portare, perche' dipendono da
    --   colonne della riga:
    --
    --   1) entrando in VALIDATA — se la distinta DICHIARA un
    --      totale, la somma delle righe deve corrispondere;
    --   2) uscendo da VALIDATA verso BOZZA — solo se e' MANUALE.
    --
    -- ⚠️ La quadratura NON puo' stare in un trigger di riga: la
    --    somma torna solo alla fine del caricamento. Qui il
    --    momento e' dichiarato dall'operatore.
    -- =========================================================

    IF NEW.stato_id IS NOT DISTINCT FROM OLD.stato_id THEN
        RETURN NEW;
    END IF;

    SELECT
        max(CASE WHEN s.id = OLD.stato_id THEN s.codice_interno END),
        max(CASE WHEN s.id = NEW.stato_id THEN s.codice_interno END)
      INTO v_stato_da, v_stato_a
      FROM pagamenti.vendite_contabili_stati s
     WHERE s.id IN (OLD.stato_id, NEW.stato_id);

    -- ── 1) Quadratura col totale dichiarato, entrando in VALIDATA
    IF v_stato_a = 'VALIDATA' AND NEW.importo_dichiarato IS NOT NULL THEN
        -- ⚠️ TUTTE le righe attive, SCARTATA compresa: quel denaro
        --    e' arrivato. Se le scartate uscissero dalla somma, il
        --    primo scarto romperebbe una distinta sana.
        SELECT COALESCE(SUM(cr.importo), 0)
          INTO v_somma
          FROM pagamenti.vendite_contabili_righe cr
         WHERE cr.contabile_id = NEW.id
           AND cr.attivo IS TRUE;

        IF v_somma IS DISTINCT FROM NEW.importo_dichiarato THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                'pagamenti.trgfn_vendite_contabili_guard_validazione',
                'E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA',
                jsonb_build_object(
                    'campo',              'importo_dichiarato',
                    'contabile_id',       NEW.id,
                    'codice',             NEW.codice,
                    'origine',            NEW.origine,
                    'importo_dichiarato', NEW.importo_dichiarato,
                    'somma_righe',        v_somma
                ),
                NEW.tx_id,
                NEW.codice,
                NEW.importo_dichiarato::text,
                v_somma::text
            );
        END IF;
    END IF;

    -- ── 2) La riapertura e' solo della MANUALE
    IF v_stato_da = 'VALIDATA' AND v_stato_a = 'BOZZA'
       AND NEW.origine IS DISTINCT FROM 'MANUALE' THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'pagamenti.trgfn_vendite_contabili_guard_validazione',
            'E_CONTABILE_RIAPERTURA_NON_MANUALE',
            jsonb_build_object(
                'contabile_id', NEW.id,
                'codice',       NEW.codice,
                'origine',      NEW.origine
            ),
            NEW.tx_id,
            NEW.codice,
            CASE NEW.origine
                WHEN 'AUTOMATICA' THEN 'arrivata da un file'
                WHEN 'GENERATA'   THEN 'prodotta dal sistema'
                ELSE NEW.origine
            END
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pagamenti.trgfn_vendite_contabili_guard_validazione()
IS 'Le condizioni su una transizione che la MATRICE non sa esprimere, perche'' dipendono da colonne della riga. (1) Entrando in VALIDATA: se importo_dichiarato e'' valorizzato, la somma delle righe attive - SCARTATA COMPRESA, quel denaro e'' arrivato - deve corrispondere. Il controllo sta al gesto «ho finito di inserire» per decisione (D14-a-bis): li'' l''operatore e'' ancora nel flusso. ⚠️ Non puo'' stare in un trigger di riga, dove la somma torna solo alla fine. (2) VALIDATA -> BOZZA solo se origine = MANUALE: l''automatica e'' la copia di un file ed e'' immutabile, la generata si rifa''. ⚠️ Chi legge la sola matrice non vede queste due regole.';
```

---
{% include-markdown "signature-core.md" %}
