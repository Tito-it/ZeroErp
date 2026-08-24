{% include-markdown "it/dbzero/pagamenti/manual/trgfn_vendite_contabili_righe_guard_distinta_finale.md" %}
# ⚙️ Funzione `trgfn_vendite_contabili_righe_guard_distinta_finale`

```sql
CREATE FUNCTION trgfn_vendite_contabili_righe_guard_distinta_finale()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_is_final       pagamenti.vendite_contabili_stati.is_final%TYPE;
    v_stato          pagamenti.vendite_contabili_stati.codice_interno%TYPE;
    v_codice         pagamenti.vendite_contabili.codice%TYPE;
    v_diventa_pronta pagamenti.vendite_contabili_righe_stati.is_postabile%TYPE;
    v_da_guardare    boolean;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Impedire che una riga contabile finisca — o torni utile —
    --   sotto una distinta in stato finale (CHIUSA o ANNULLATA):
    --   la' non entra in nessun conto e non verra' mai registrata.
    --
    -- ⚠️ QUATTRO mosse, non una: nascere li', esserci RIATTIVATA,
    --    esserci SPOSTATA da un'altra distinta, e — dal
    --    2026-08-22 — diventarci PRONTA DA REGISTRARE restando
    --    dov'e'.
    --
    -- ⚠️ Cio' che NON si rifiuta: le altre scritture su una riga
    --    gia' li'. Rifiutare tutto impedirebbe perfino di
    --    correggere il motivo_sospeso di una riga annullata — e,
    --    dalla quarta mossa in poi, impedirebbe di DIRE che cosa
    --    ne e' stato di quel denaro (sospenderla, scartarla),
    --    che e' l'unica cosa che resta da fare.
    -- =========================================================

    v_da_guardare := CASE
        WHEN TG_OP = 'INSERT' THEN NEW.attivo IS TRUE
        -- riattivazione, oppure spostamento sotto un'altra distinta
        ELSE (NEW.attivo IS TRUE AND OLD.attivo IS NOT TRUE)
          OR (NEW.contabile_id IS DISTINCT FROM OLD.contabile_id)
    END;

    -- ⭐ QUARTA MOSSA. La riga non si sposta e non si riattiva:
    --    cambia stato, e il nuovo stato la rende PRONTA DA
    --    REGISTRARE. Sotto una distinta finale quel denaro non
    --    verrebbe mai registrato — il posting parte dalla testata,
    --    e una CHIUSA la rifiuta.
    -- ⚠️ La domanda si fa al CATALOGO (`is_postabile`), non a un
    --    elenco di stati scritto qui: e' la stessa scelta di
    --    `richiede_abbinamento` sul guard gemello.
    -- ℹ️ La lettura si paga solo se le altre tre mosse non hanno
    --    gia' deciso, e solo su un cambio di stato vero.
    IF NOT v_da_guardare
       AND TG_OP = 'UPDATE'
       AND NEW.attivo IS TRUE
       AND NEW.stato_id IS DISTINCT FROM OLD.stato_id
    THEN
        SELECT s.is_postabile
          INTO v_diventa_pronta
          FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.id = NEW.stato_id;

        v_da_guardare := COALESCE(v_diventa_pronta, false);
    END IF;

    IF NOT v_da_guardare THEN
        RETURN NEW;
    END IF;

    -- ⚠️ Quando pagamenti avra' la RLS (slice 3, S3-5) questa
    --    lettura va riguardata: un guard che legge sotto RLS non
    --    distingue «non lo vedo» da «e' di un altro».
    SELECT s.is_final, s.codice_interno, c.codice
      INTO v_is_final, v_stato, v_codice
      FROM pagamenti.vendite_contabili c
      JOIN pagamenti.vendite_contabili_stati s ON s.id = c.stato_id
     WHERE c.id = NEW.contabile_id;

    IF COALESCE(v_is_final, false) IS FALSE THEN
        RETURN NEW;
    END IF;

    PERFORM script.fn_log_and_raise_error(
        'database',
        'pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale',
        'E_RIGA_CONTABILE_DISTINTA_FINALE',
        jsonb_build_object(
            'contabile_riga_id', NEW.id,
            'contabile_id',      NEW.contabile_id,
            'contabile_codice',  v_codice,
            'stato_distinta',    v_stato,
            'stato_riga_id',     NEW.stato_id,
            'diventa_pronta',    COALESCE(v_diventa_pronta, false),
            'operazione',        TG_OP
        ),
        NEW.tx_id,
        COALESCE(v_codice, NEW.contabile_id::text),
        CASE WHEN v_stato = 'ANNULLATA' THEN 'annullata' ELSE 'chiusa' END
    );

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale()
IS 'Porta d''INGRESSO del difetto C-5: nessuna riga contabile utile sotto una distinta in stato finale (CHIUSA o ANNULLATA), dove non entrerebbe in nessun conto e non verrebbe mai registrata. ⚠️ QUATTRO mosse: nascere li'', esserci RIATTIVATA, esserci SPOSTATA da un''altra distinta, e — dal 2026-08-22, lotto 4 — DIVENTARCI PRONTA DA REGISTRARE restando dov''e''. ⭐ La quarta e'' nata con la madre del posting: la madre chiude la distinta appena ha registrato (la chiusura e'' la conseguenza del registrare, decisione di Tid), e sotto possono restare righe DA_ABBINARE — che il guard di chiusura NON considera un ostacolo, deliberatamente, o la distinta non si chiuderebbe mai. Abbinarne una il giorno dopo produrrebbe denaro dichiarato e pronto sotto una distinta che il posting rifiuta perche'' finale. ⚠️ Si vieta SOLO l''ingresso in uno stato is_postabile: sospendere, scartare o correggere il motivo di una riga che sta li'' resta possibile, ed e'' deliberato — dire che cosa ne e'' stato di quel denaro deve restare l''ultima cosa che si puo'' fare. ⚠️ Non blocca il posting per due ragioni indipendenti: POSTATA non e'' uno stato postabile, e la distinta e'' ancora VALIDATA quando la madre muove le righe. ⚠️ La domanda «questo stato e'' pronto?» si fa al catalogo (is_postabile) e non a un elenco scritto dentro il guard. Gemello d''uscita: pagamenti.trgfn_vendite_contabili_guard_chiusura (E_CONTABILE_CHIUSURA_CON_RIGHE_PRONTE).';
```

---
{% include-markdown "signature-core.md" %}
