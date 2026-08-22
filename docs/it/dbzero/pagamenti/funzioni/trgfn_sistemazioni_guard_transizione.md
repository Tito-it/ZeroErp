{% include-markdown "it/dbzero/pagamenti/manual/trgfn_sistemazioni_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_sistemazioni_guard_transizione`

```sql
CREATE FUNCTION trgfn_sistemazioni_guard_transizione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_sistemazioni_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il percorso dell'atto, che e' cortissimo:
    --     BOZZA -> CONFERMATA | ANNULLATA, ed entrambi finiscono.
    --
    -- ⛔ Nessuna tabella-matrice, di proposito: due passaggi
    --   sarebbero due righe che nessuno interroga, e le azioni
    --   del frontend sono i due verbi stessi. Chi cerca la regola
    --   nei dati non la trova: e' qui, e per questo il codice
    --   errore la nomina per esteso.
    -- =========================================================

    IF TG_OP = 'INSERT' THEN
        -- ⭐ Un atto non nasce gia' fatto: nasce come DECISIONE, e
        --   diventa un fatto quando qualcuno lo conferma.
        IF NEW.stato <> 'BOZZA' THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                'pagamenti.trgfn_sistemazioni_guard_transizione',
                'E_SISTEMAZIONE_TRANSIZIONE_NON_AMMESSA',
                jsonb_build_object(
                    'detail', 'una sistemazione nasce in BOZZA',
                    'campo',  'stato',
                    'stato_richiesto', NEW.stato
                ),
                NULL::uuid,
                'BOZZA', NEW.stato::text
            );
        END IF;

        RETURN NEW;
    END IF;

    -- ── UPDATE ──────────────────────────────────────────────
    -- ⭐ Su un atto TERMINALE si rifiuta OGNI modifica, non solo
    --   quelle che cambiano stato: un atto confermato ha generato
    --   un documento, e se il registro potesse cambiare sotto
    --   racconterebbe una cosa e il documento un'altra.
    IF OLD.stato IN ('CONFERMATA', 'ANNULLATA') THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'pagamenti.trgfn_sistemazioni_guard_transizione',
            'E_SISTEMAZIONE_IMMUTABILE',
            jsonb_build_object(
                'detail', 'atto terminale: nessuna modifica ammessa',
                'sistemazione_id', OLD.id,
                'stato', OLD.stato
            ),
            NULL::uuid,
            OLD.id::text, OLD.stato::text
        );
    END IF;

    -- Da BOZZA si va a CONFERMATA o ad ANNULLATA, e basta.
    IF NEW.stato IS DISTINCT FROM OLD.stato
       AND NEW.stato NOT IN ('CONFERMATA', 'ANNULLATA')
    THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'pagamenti.trgfn_sistemazioni_guard_transizione',
            'E_SISTEMAZIONE_TRANSIZIONE_NON_AMMESSA',
            jsonb_build_object(
                'detail', 'passaggio di stato non previsto',
                'campo',  'stato',
                'sistemazione_id', OLD.id,
                'stato_da', OLD.stato,
                'stato_a',  NEW.stato
            ),
            NULL::uuid,
            OLD.stato::text, NEW.stato::text
        );
    END IF;

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION pagamenti.trgfn_sistemazioni_guard_transizione()
IS 'Il percorso dell''atto di sistemazione: nasce in BOZZA, e da li'' va a CONFERMATA (diventa un fatto: genera la contabile o il fondo) oppure ad ANNULLATA. ⭐ Entrambi gli esiti sono TERMINALI: da CONFERMATA non si torna perche'' il denaro si e'' gia'' mosso, e la correzione e'' una sistemazione NUOVA — la stessa regola della distinta contabile chiusa. ⛔ Nessuna tabella-matrice come per la contabile, di proposito: tre stati e due passaggi sarebbero due righe che nessuno interroga, e la matrice esiste anche perche'' il frontend ci legge le azioni — qui le azioni sono i due verbi stessi. Chi cerca la regola nei dati non la trova: e'' qui. ⚠️ Su un atto terminale rifiuta OGNI update e non solo quelli di stato, con un codice diverso (E_SISTEMAZIONE_IMMUTABILE): «non puo'' passare da CONFERMATA a BOZZA» e'' vero ma non aiuta chi sta provando a correggere un importo gia'' eseguito.';
```

---
{% include-markdown "signature-core.md" %}
