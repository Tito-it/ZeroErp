{% include-markdown "it/dbzero/vendite/manual/trgfn_fatturazione_lotti_esiti_uscita.md" %}
# ⚙️ Funzione `trgfn_fatturazione_lotti_esiti_uscita`

```sql
CREATE FUNCTION trgfn_fatturazione_lotti_esiti_uscita()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatturazione_lotti_esiti_uscita()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: governa l'uscita di un documento dal giro.
--        1) DIVIETO: ESCLUSO e' terminale, non si torna indietro;
--        2) TIMBRO : uscita_quando/uscita_da le scrive il database.
-- Uso:   BEFORE INSERT OR UPDATE OF stato_esecuzione FOR EACH ROW.
DECLARE
    v_utente vendite.fatturazione_lotti_esiti.uscita_da%TYPE;
BEGIN
    -- ── 1) IL DIVIETO ─────────────────────────────────────
    -- ⚠️ Solo su UPDATE: la matrice delle transizioni non
    --    vincola l'INSERT (seed, import, riga che nasce gia'
    --    nello stato finale).
    -- ⚠️ E guarda la DIREZIONE: riassegnare ESCLUSO a una riga
    --    gia' esclusa non cambia niente e non si rifiuta.
    IF TG_OP = 'UPDATE'
       AND OLD.stato_esecuzione = 'ESCLUSO'
       AND NEW.stato_esecuzione IS DISTINCT FROM OLD.stato_esecuzione THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'trgfn_fatturazione_lotti_esiti_uscita',
            'E_LOTTO_DOC_USCITA_IRREVERSIBILE',
            jsonb_build_object('lotto_id',   NEW.lotto_id,
                               'gruppo_key', NEW.gruppo_key,
                               'stato_richiesto', NEW.stato_esecuzione,
                               -- ⭐ Il bersaglio e' il LOTTO: chi
                               --   legge questo errore sta guardando
                               --   il giro, non la riga di esito.
                               'bersaglio',  jsonb_build_array(
                                   jsonb_build_object('tipo', 'LOTTO',
                                                      'id', NEW.lotto_id::text))),
            NULL::uuid,
            -- ⛔ Nel VARIADIC va la cosa che una persona riconosce:
            --   il documento, non il nome della colonna.
            NEW.gruppo_key,
            NEW.stato_esecuzione);
    END IF;

    -- ── 2) IL TIMBRO ──────────────────────────────────────
    IF NEW.stato_esecuzione = 'ESCLUSO'
       AND (TG_OP = 'INSERT'
            OR OLD.stato_esecuzione IS DISTINCT FROM 'ESCLUSO') THEN
        -- Il documento esce ADESSO: data e nome li mette il database.
        v_utente := COALESCE(
            NULLIF(current_setting('app.jwt_user', true), ''),
            CURRENT_USER);
        NEW.uscita_quando := CURRENT_TIMESTAMP;
        NEW.uscita_da     := v_utente;

    ELSIF NEW.stato_esecuzione = 'ESCLUSO' THEN
        -- ⭐ Resta esclusa: le derivate NON si toccano piu'. Chi
        --    passasse con una data propria non la vedrebbe
        --    attecchire, e non c'e' modo di far dire alla riga una
        --    cosa che il suo stato smentisce.
        NEW.uscita_quando := OLD.uscita_quando;
        NEW.uscita_da     := OLD.uscita_da;

    ELSE
        -- ⚠️ Non e' esclusa: non puo' portare un timbro d'uscita.
        --    «Non uscita, uscita il 3 settembre» e' un dato
        --    composito spostato a meta'.
        NEW.uscita_quando := NULL;
        NEW.uscita_da     := NULL;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fatturazione_lotti_esiti_uscita()
IS 'Governa l''uscita di un documento dal giro di fatturazione. 1) ESCLUSO e'' TERMINALE: il documento uscito non rientra (D-3 del brief) — se si vuole tutto in un lotto solo si annulla il lotto e si rigenera. 2) uscita_quando/uscita_da le DERIVA questa funzione dalla GUC app.jwt_user, mai il chiamante: data_update e user_update le riscriverebbe qualunque aggiornamento successivo e il momento dell''uscita si perderebbe in silenzio. ⚠️ Il rifiuto guarda la DIREZIONE e non la menzione della colonna (UPDATE OF scatta anche riassegnando lo stesso valore). ⛔ Su INSERT non solleva mai — solo timbra —, quindi il CHECK chk_fatturazione_lotti_esiti_uscita_parlante continua a valutare dopo e a rifiutare l''uscita senza motivo. ⛔ Il nome non porta guard perche'' la funzione scrive NEW. Errore: E_LOTTO_DOC_USCITA_IRREVERSIBILE, classe TECNICO — qui ci arriva solo un UPDATE diretto, perche'' la madre fn_escludi_documento_da_giro chiede prima alla sua check. Brief: brief-db-uscita-documento-dal-giro.';
```

</div>

---
{% include-markdown "signature-core.md" %}
