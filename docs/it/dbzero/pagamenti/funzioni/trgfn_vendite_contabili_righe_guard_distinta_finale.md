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
    v_is_final     pagamenti.vendite_contabili_stati.is_final%TYPE;
    v_stato        pagamenti.vendite_contabili_stati.codice_interno%TYPE;
    v_codice       pagamenti.vendite_contabili.codice%TYPE;
    v_da_guardare  boolean;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Impedire che una riga contabile finisca sotto una distinta
    --   in stato finale (CHIUSA o ANNULLATA): la' non entra in
    --   nessun conto e non verra' mai registrata.
    --
    -- ⚠️ TRE mosse, non una: nascere li', esserci RIATTIVATA,
    --    esserci SPOSTATA da un'altra distinta.
    --
    -- ⚠️ Cio' che NON si rifiuta: le altre scritture su una riga
    --    gia' li'. Rifiutare tutto impedirebbe perfino di
    --    correggere il motivo_sospeso di una riga annullata.
    -- =========================================================

    v_da_guardare := CASE
        WHEN TG_OP = 'INSERT' THEN NEW.attivo IS TRUE
        -- riattivazione, oppure spostamento sotto un'altra distinta
        ELSE (NEW.attivo IS TRUE AND OLD.attivo IS NOT TRUE)
          OR (NEW.contabile_id IS DISTINCT FROM OLD.contabile_id)
    END;

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
IS 'C-5, porta d''INGRESSO: nessuna riga nuova, riattivata o spostata sotto una distinta contabile in stato finale. Una riga li'' non entra nel saldo contabile (la testata e'' finale), non entra nel saldo movimenti (non e'' registrata) e non verra'' mai registrata (il posting parte dalla testata): denaro dichiarato che non compare da nessuna parte, e la differenza fa RIGENERARE il fondo fattura. La porta d''USCITA e'' l''altra, e la chiude pagamenti.trgfn_vendite_contabili_guard_chiusura.';
```

---
{% include-markdown "signature-core.md" %}
