{% include-markdown "it/dbzero/pagamenti/manual/trgfn_vendite_contabili_guard_validazione.md" %}
# ⚙️ Funzione `trgfn_vendite_contabili_guard_validazione`

```sql
CREATE FUNCTION trgfn_vendite_contabili_guard_validazione()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_vendite_contabili_guard_validazione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_stato_da              pagamenti.vendite_contabili_stati.codice_interno%TYPE;
    v_stato_a               pagamenti.vendite_contabili_stati.codice_interno%TYPE;
    v_a_righe_lavorabili    pagamenti.vendite_contabili_stati.righe_lavorabili%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Le CONDIZIONI su una transizione che la matrice
    --   (stato_da, stato_a) non puo' portare, perche' dipendono da
    --   colonne della riga o dalle righe figlie:
    --
    --   1) entrando in VALIDATA — «ho finito di inserire»: nessuna
    --      riga attiva non lavorata (IMPORTATA, DA_ABBINARE), e se
    --      la distinta DICHIARA un totale la somma delle righe deve
    --      corrispondere. ⭐ Rev 2026-09-18 (D20-a): i due motivi
    --      stanno in script.fn_check_contabile_validabile, in
    --      quest'ordine; qui si chiama la check e si solleva il
    --      primo. Il guard non fa piu' i conti da se': la stessa
    --      check la legge il dettaglio della distinta, e cosi'
    --      il pulsante spento e il rifiuto non possono divergere;
    --   2) uscendo da VALIDATA verso BOZZA — solo se e' MANUALE;
    --   3) ⭐ Rev 2026-09-30 (D-4): entrando in uno stato che
    --      CONGELA le righe (righe_lavorabili = false, oggi
    --      ANNULLATA) — solo se e' MANUALE.
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
        max(CASE WHEN s.id = NEW.stato_id THEN s.codice_interno END),
        bool_or(s.righe_lavorabili) FILTER (WHERE s.id = NEW.stato_id)
      INTO v_stato_da, v_stato_a, v_a_righe_lavorabili
      FROM pagamenti.vendite_contabili_stati s
     WHERE s.id IN (OLD.stato_id, NEW.stato_id);

    -- ── 1) Entrando in VALIDATA: la check decide, il guard solleva
    -- ⭐ NEW.importo_dichiarato e non una rilettura: BEFORE ROW, il
    --    valore che sta entrando non e' ancora nella tabella.
    -- ⛔ Il codice si legge dall'array → fn_raise_primo_motivo_se_presente
    --    (AGENTS.md §«Due funzioni per sollevare»). p_campo NULL: il
    --    campo, quando c'e', viaggia nel dettaglio della check.
    IF v_stato_a = 'VALIDATA' THEN
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'database',
            'pagamenti.trgfn_vendite_contabili_guard_validazione',
            script.fn_check_contabile_validabile(NEW.id, NEW.importo_dichiarato),
            NULL,
            NEW.tx_id,
            jsonb_build_object(
                'contabile_id', NEW.id,
                'codice',       NEW.codice,
                'origine',      NEW.origine));
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

    -- ── 3) L'annullo e' solo della MANUALE (D-4, 2026-09-30)
    -- ⭐ Sulla BANDIERA e non sul letterale 'ANNULLATA': la
    --    collisione col giro dei fondi nasce dal congelamento
    --    delle righe (sync che le sposta, cancellazione che le
    --    toglie), non dal nome dello stato.
    -- ⚠️ IS FALSE: uno stato d'arrivo che non si legge non e'
    --    «congelante» — lo decide la matrice, che ha gia' parlato.
    -- ⚠️ Whitelist sull'origine: l'AUTOMATICA cade nel rifiuto
    --    finche' il cantiere dell'import non decide.
    IF v_a_righe_lavorabili IS FALSE
       AND NEW.origine IS DISTINCT FROM 'MANUALE' THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'pagamenti.trgfn_vendite_contabili_guard_validazione',
            'E_CONTABILE_ANNULLO_NON_MANUALE',
            jsonb_build_object(
                'contabile_id', NEW.id,
                'codice',       NEW.codice,
                'origine',      NEW.origine,
                'stato_a',      v_stato_a,
                'reason',       'ANNULLO_NON_MANUALE'
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
IS 'Le condizioni su una transizione che la MATRICE non sa esprimere, perche'' dipendono da colonne della riga o dalle righe figlie. (1) Entrando in VALIDATA — «ho finito di inserire» (D14-a-bis) — chiama script.fn_check_contabile_validabile(NEW.id, NEW.importo_dichiarato) e solleva il codice del PRIMO motivo con fn_raise_primo_motivo_se_presente: prima le righe attive NON LAVORATE (lavorata = false sul catalogo: IMPORTATA, DA_ABBINARE — E_CONTABILE_VALIDAZIONE_RIGHE_NON_LAVORATE, D20-a), poi la quadratura col dichiarato quando c''e'' (E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA, SCARTATA compresa: quel denaro e'' arrivato). ⭐ Rev 2026-09-18: il guard non calcola piu'' la quadratura in proprio — la check e'' la sede unica, letta anche dal dettaglio della distinta (can_validare), cosi'' pulsante spento e rifiuto non possono divergere. NEW.importo_dichiarato e non una rilettura: BEFORE ROW, il valore che entra non e'' ancora nella tabella. ⚠️ Non puo'' stare in un trigger di riga, dove la somma torna solo alla fine. (2) VALIDATA -> BOZZA solo se origine = MANUALE: l''automatica e'' la copia di un file ed e'' immutabile, la generata si rifa''. (3) ⭐ Rev 2026-09-30 (D-4, D-5): si entra in uno stato che CONGELA le righe — righe_lavorabili = false, oggi ANNULLATA — solo se origine = MANUALE, E_CONTABILE_ANNULLO_NON_MANUALE. La generata la governa il giro che l''ha prodotta (per togliere un fondo si cancella l''atto, per togliere una sistemazione la si annulla): annullarne la testata a mano faceva spostare la riga dal sync dei fondi in una distinta nuova, e col congelamento delle righe sotto un''annullata (quinta mossa di trgfn_vendite_contabili_righe_guard_distinta_finale) sarebbe diventato un 500 sulla pipeline o un atto non piu'' cancellabile. Sulla bandiera e non sul letterale: la collisione nasce dal congelamento. Whitelist: l''AUTOMATICA cade nel rifiuto finche'' il cantiere dell''import non decide. Codice proprio e non E_CONTABILE_RIAPERTURA_NON_MANUALE, che dice «non si riapre». ⚠️ Chi legge la sola matrice non vede queste tre regole. Brief: brief-db-validata-e-registrazione-tardiva §4 P-4; brief-db-righe-distinta-annullata-fuori-dalle-code §8.';
```

</div>

---
{% include-markdown "signature-core.md" %}
