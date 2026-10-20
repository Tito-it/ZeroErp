{% include-markdown "it/dbzero/vendite/manual/trgfn_fondi_source_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_fondi_source_guard_transizione`

```sql
CREATE FUNCTION trgfn_fondi_source_guard_transizione()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fondi_source_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: far rispettare la matrice degli stati del fondo, dalla
--        NASCITA in poi.
--        ANNULLATO e ESEGUITO sono terminali, per ragioni
--        opposte e simmetriche: dal primo si e' tolto denaro
--        dal tavolo, nel secondo lo si e' mosso. In entrambi i
--        casi tornare indietro non disfa niente — se serve un
--        altro esito, si compie un atto NUOVO.
-- ⭐ E se sono terminali, non sono nemmeno INIZIALI: un atto che
--        nasce gia' terminale e' un record che non e' mai stato
--        vero, e nessuna transizione lo ha prodotto.
-- Uso:   BEFORE INSERT OR UPDATE OF stato FOR EACH ROW
DECLARE
    v_ammessa BOOLEAN;
BEGIN
    -- ── LA NASCITA ────────────────────────────────────────
    -- ⚠️ Ramo separato e in testa: su un INSERT `OLD` non
    --    esiste, quindi il confronto piu' sotto darebbe NULL e
    --    il CASE cadrebbe nell'ELSE, rifiutando ogni INSERT.
    IF TG_OP = 'INSERT' THEN
        -- ⭐ Due stati, ed entrambi sono percorsi VIVI:
        --    DISPONIBILE lo scrive fn_genera_fondi_fattura_source,
        --    ASSEGNATO lo scrive pagamenti.fn_conferma_sistemazione
        --    sul ramo RIPORTO — il riporto nomina gia' la fattura
        --    di destinazione, e farlo nascere DISPONIBILE sarebbe
        --    un credito che aspetta una decisione gia' presa.
        IF NEW.stato NOT IN ('DISPONIBILE', 'ASSEGNATO') THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'trgfn_fondi_source_guard_transizione',
                'E_FONDO_STATO_NON_AMMESSO',
                jsonb_build_object(
                    'operazione',          TG_OP,
                    'fondo_source_id',     NEW.id,
                    'fattura_sorgente_id', NEW.fattura_sorgente_id,
                    'campo',               'stato',
                    -- ⚠️ NULL e non una parola: alla nascita uno stato
                    --    precedente non c'e'. La parola sta nel VARIADIC,
                    --    che compone la frase che una persona legge.
                    'stato_da',            NULL,
                    'stato_a',             NEW.stato),
                NULL::uuid,
                'creazione', NEW.stato);
        END IF;

        RETURN NEW;
    END IF;

    -- ── LE TRANSIZIONI ───────────────────────────────────
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
                'operazione',          TG_OP,
                'fondo_source_id',     NEW.id,
                'fattura_sorgente_id', NEW.fattura_sorgente_id,
                'campo',               'stato',
                'stato_da',            OLD.stato,
                'stato_a',             NEW.stato),
            NULL::uuid,
            OLD.stato, NEW.stato);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fondi_source_guard_transizione()
IS 'Matrice degli stati del fondo fattura, dalla NASCITA in poi. Nascita: DISPONIBILE (giro automatico) o ASSEGNATO (riporto di pagamenti.fn_conferma_sistemazione); ESEGUITO e ANNULLATO alla nascita sono rifiutati. Transizioni: DISPONIBILE -> ASSEGNATO|ANNULLATO, ASSEGNATO -> DISPONIBILE|ANNULLATO|ESEGUITO, ANNULLATO e ESEGUITO terminali. ⭐ rev 2026-08-31 (D-22 di brief-db-fondo-fattura-ricalcolo-e-governo §9.2-c): il guard era montato SOLO in UPDATE e chk_fondi_source_stato ammette tutti e quattro i valori, quindi l''unico presidio sullo stato di nascita era la buona volonta'' di chi faceva l''INSERT — un atto poteva nascere gia'' terminale, cioe'' un record che non e'' mai stato vero. ⚠️ Il ramo INSERT e'' separato e sta in testa: su un INSERT OLD non esiste e il confronto delle transizioni darebbe NULL, facendo cadere ogni INSERT nell''ELSE. ⭐ ASSEGNATO alla nascita e'' un percorso VIVO e non una concessione: il riporto nomina gia'' la fattura di destinazione, e farlo nascere DISPONIBILE sarebbe un credito che aspetta una decisione gia'' presa. ⭐ rev 2026-08-21 (cantiere incassi, lotto 3, passo S1-15): il quarto stato ESEGUITO entra nella matrice. Nasce perche'' ANNULLATO portava TRE significati — non si deve fare piu'', non si e'' piu'' capienti, e'' gia'' stato eseguito — e il terzo produceva un record autocontraddittorio (ANNULLATO con fattura_figlia_id ancora valorizzato). ⚠️ ESEGUITO e'' TERMINALE perche'' descrive un fatto avvenuto: il trasferimento e'' stato registrato in contabilita'', e uscire da li'' non lo annullerebbe — lo renderebbe invisibile all''atto che l''ha prodotto, cioe'' il doppio conteggio che il lotto 3 chiude. Un fondo eseguito sbagliato non si corregge tornando indietro: si compie un atto NUOVO, ed e'' la ragione per cui i rimborsi sono un processo (pagamenti.sistemazioni) e non un UPDATE. ⚠️ ASSEGNATO -> DISPONIBILE resta ammessa ma dal changeSet 20260821-54 NON la percorre piu'' nessuno: fn_reset_fondi_fattura cancella l''atto non eseguito invece di riaprirlo. Guard e non lookup di transizioni: sono quattro valori interni senza etichette ne'' azioni di UI. D11 del brief incassi; D-7 di brief-db-fondo-fattura-ricalcolo-e-governo §8.2 e'' SUPERATA in due riprese (diceva «tre stati e non quattro», e non descriveva la nascita).';
```

</div>

---
{% include-markdown "signature-core.md" %}
