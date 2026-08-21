{% include-markdown "it/dbzero/vendite/manual/trgfn_fondi_source_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_fondi_source_guard_transizione`

```sql
CREATE FUNCTION trgfn_fondi_source_guard_transizione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fondi_source_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: far rispettare la matrice degli stati del fondo.
--        ANNULLATO e ESEGUITO sono terminali, per ragioni
--        opposte e simmetriche: dal primo si e' tolto denaro
--        dal tavolo, nel secondo lo si e' mosso. In entrambi i
--        casi tornare indietro non disfa niente — se serve un
--        altro esito, si compie un atto NUOVO.
-- Uso:   BEFORE UPDATE OF stato FOR EACH ROW
DECLARE
    v_ammessa BOOLEAN;
BEGIN
    -- Nessun movimento di stato: niente da verificare.
    IF NEW.stato IS NOT DISTINCT FROM OLD.stato THEN
        RETURN NEW;
    END IF;

    v_ammessa := CASE OLD.stato
        WHEN 'DISPONIBILE' THEN NEW.stato IN ('ASSEGNATO', 'ANNULLATO')
        -- ⭐ ESEGUITO dal 2026-08-21 (D11): lo scrive il trigger
        --    pagamenti.trgfn_vendite_contabili_righe_marca_fondo_eseguito
        --    quando la riga contabile del fondo entra in POSTATA.
        -- ⚠️ DISPONIBILE resta ammessa ma dal changeSet -54 non
        --    la percorre piu' nessuno: il reset di un atto non
        --    eseguito lo CANCELLA. Resta come unica strada per
        --    disfare l'assegnazione senza cancellare l'atto.
        WHEN 'ASSEGNATO'   THEN NEW.stato IN ('DISPONIBILE', 'ANNULLATO', 'ESEGUITO')
        WHEN 'ANNULLATO'   THEN FALSE
        WHEN 'ESEGUITO'    THEN FALSE
        ELSE FALSE
    END;

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'trgfn_fondi_source_guard_transizione',
            'E_FONDO_STATO_NON_AMMESSO',
            jsonb_build_object(
                'fondo_source_id',     NEW.id,
                'fattura_sorgente_id', NEW.fattura_sorgente_id,
                'stato_da',            OLD.stato,
                'stato_a',             NEW.stato),
            NULL::uuid,
            OLD.stato, NEW.stato);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fondi_source_guard_transizione()
IS 'Matrice degli stati del fondo fattura: DISPONIBILE -> ASSEGNATO|ANNULLATO, ASSEGNATO -> DISPONIBILE|ANNULLATO|ESEGUITO, ANNULLATO e ESEGUITO terminali. ⭐ rev 2026-08-21 (cantiere incassi, lotto 3, passo S1-15): il quarto stato ESEGUITO entra nella matrice. Nasce perche'' ANNULLATO portava TRE significati — non si deve fare piu'', non si e'' piu'' capienti, e'' gia'' stato eseguito — e il terzo produceva un record autocontraddittorio (ANNULLATO con fattura_figlia_id ancora valorizzato). ⚠️ ESEGUITO e'' TERMINALE perche'' descrive un fatto avvenuto: il trasferimento e'' stato registrato in contabilita'', e uscire da li'' non lo annullerebbe — lo renderebbe invisibile all''atto che l''ha prodotto, cioe'' il doppio conteggio che il lotto 3 chiude. Simmetrico ad ANNULLATO letto dall''altro capo: li'' si e'' tolto denaro dal tavolo, qui lo si e'' mosso. Un fondo eseguito sbagliato non si corregge tornando indietro: si compie un atto NUOVO, ed e'' la ragione per cui i rimborsi sono un processo (pagamenti.sistemazioni) e non un UPDATE. ⚠️ ASSEGNATO -> DISPONIBILE resta ammessa ma dal changeSet 20260821-54 NON la percorre piu'' nessuno: fn_reset_fondi_fattura cancella l''atto non eseguito invece di riaprirlo. Resta come unica strada per disfare l''assegnazione senza cancellare l''atto. Guard e non lookup di transizioni: sono quattro valori interni senza etichette ne'' azioni di UI. D11 del brief incassi; D-7 di brief-db-fondo-fattura-ricalcolo-e-governo §8.2 e'' SUPERATA (diceva «tre stati e non quattro»).';
```

---
{% include-markdown "signature-core.md" %}
