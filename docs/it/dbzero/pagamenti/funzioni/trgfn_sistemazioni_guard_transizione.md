{% include-markdown "it/dbzero/pagamenti/manual/trgfn_sistemazioni_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_sistemazioni_guard_transizione`

```sql
CREATE FUNCTION trgfn_sistemazioni_guard_transizione()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_sistemazioni_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⭐ Le colonne che il varco lascia cambiare. Si elencano le
    --   AMMESSE e non le vietate: cosi' una colonna nuova sulla
    --   tabella nasce CHIUSA invece di diventare modificabile in
    --   silenzio.
    v_ammesse   text[] := ARRAY[
        'stato', 'motivo', 'data_esecuzione', 'user_esecuzione',
        'fondo_source_id', 'meta',
        -- tecniche: le scrivono i trigger di audit e di tx_id
        'data_update', 'user_update', 'tx_id'];
    v_varco     boolean;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il percorso dell'atto, che e' cortissimo:
    --     BOZZA -> CONFERMATA | ANNULLATA.
    --   ⭐ Con UN varco, e uno solo: CONFERMATA -> ANNULLATA sul
    --   ramo RIPORTO, perche' quello e' l'unico che non lascia
    --   dietro una distinta e quindi l'unico senza contropartita.
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

        -- ── IL VARCO (G-4 · G-5, Tid 2026-08-29) ───────────
        -- Tre assi, e devono valere tutti e tre insieme:
        --   1. la transizione: solo CONFERMATA -> ANNULLATA;
        --   2. la destinazione: solo RIPORTO — gli altri due
        --      lasciano una DISTINTA, e per quella il rimedio
        --      esiste gia' (correzione guidata, S6);
        --   3. le colonne: solo quelle dell'esito.
        -- ⚠️ Il puntatore al fondo DEVE uscire azzerato: la FK
        --   fk_sistemazioni_fondo_source e' NO ACTION, quindi
        --   finche' l'atto lo punta il fondo non si cancella. E
        --   con lui cadono data_esecuzione e user_esecuzione,
        --   perche' chk_sistemazioni_eseguita li vuole tutti NULL
        --   fuori da CONFERMATA: sono un dato COMPOSITO, e si
        --   sposta intero o non si sposta.
        v_varco :=
                OLD.stato        =  'CONFERMATA'
            AND OLD.destinazione =  'RIPORTO'
            AND NEW.stato        =  'ANNULLATA'
            AND NEW.fondo_source_id IS NULL
            AND (to_jsonb(NEW) - v_ammesse)
                IS NOT DISTINCT FROM
                (to_jsonb(OLD) - v_ammesse);

        IF NOT v_varco THEN
            -- ⭐ Il gesto «annulla» su un atto che lascia una
            --   distinta NON e' semplicemente vietato: ha
            --   un'altra strada, e il rifiuto deve nominarla.
            --   «Questo atto e' immutabile» e' vero e non aiuta —
            --   e' l'autocritica scritta nel COMMENT di questo
            --   stesso guard.
            IF OLD.stato        =  'CONFERMATA'
               AND NEW.stato    =  'ANNULLATA'
               AND OLD.destinazione IN ('RIMBORSO', 'COMPENSAZIONE')
            THEN
                PERFORM script.fn_log_and_raise_error(
                    'database',
                    'pagamenti.trgfn_sistemazioni_guard_transizione',
                    'E_SISTEMAZIONE_ANNULLO_NON_AMMESSO',
                    jsonb_build_object(
                        'detail', 'un atto che ha prodotto una distinta si corregge sulla distinta',
                        'sistemazione_id', OLD.id,
                        'destinazione',    OLD.destinazione,
                        'stato',           OLD.stato
                    ),
                    NULL::uuid,
                    OLD.id::text, lower(OLD.destinazione::text)
                );
            END IF;

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

        -- Il varco e' passato: l'atto scende ad ANNULLATA, e la
        -- matrice qui sotto non ha altro da dire.
        RETURN NEW;
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
IS 'Il percorso dell''atto di sistemazione: nasce in BOZZA, e da li'' va a CONFERMATA (diventa un fatto: genera la contabile o il fondo) oppure ad ANNULLATA. ⭐ rev 2026-08-31 (D-25 di brief-db-fondo-fattura-ricalcolo-e-governo §9.6 e §9.8, decisioni G-4 e G-5 di Tid): si apre UN varco, CONFERMATA -> ANNULLATA sul solo ramo RIPORTO. Perche'' proprio quello: le altre due destinazioni lasciano dietro una DISTINTA e per una distinta sbagliata il rimedio esiste gia'' — la correzione guidata (S6) — mentre il RIPORTO lascia un FONDO in vendite, e per quello non c''era niente. Una sistemazione NUOVA non e'' la contropartita di un riporto sbagliato: la sistemazione pretende un''eccedenza, e quel riporto l''ha gia'' consumata. ⚠️ Il varco e'' chirurgico su TRE assi — la transizione (solo quella), la destinazione (solo RIPORTO: aprire anche agli altri due darebbe DUE strade per disfare lo stesso fatto, ed e'' il modo in cui due meccanismi cominciano a divergere) e le COLONNE, perche'' su un atto terminale si rifiuta ogni modifica e non solo quelle di stato. Passano solo stato, motivo, data_esecuzione, user_esecuzione, fondo_source_id, meta e le tecniche di audit: il confronto elenca le colonne AMMESSE e non le vietate, cosi'' una colonna nuova sulla tabella nasce CHIUSA invece di diventare modificabile in silenzio. ⚠️ fondo_source_id deve uscire azzerato perche'' fk_sistemazioni_fondo_source e'' NO ACTION e finche'' l''atto punta il fondo il fondo non si cancella; con lui cadono data_esecuzione e user_esecuzione, che chk_sistemazioni_eseguita vuole NULL fuori da CONFERMATA — sono un dato composito e si sposta intero. La memoria di quando l''atto era stato eseguito la conserva fn_annulla_sistemazione dentro meta, che nessun CHECK vincola: allargare il CHECK sarebbe stata l''altra strada, ed e'' scartata perche'' ammetterebbe per sempre un atto ANNULLATO che dichiara di essere stato eseguito. ⭐ E il rifiuto dell''annullamento su RIMBORSO/COMPENSAZIONE NOMINA L''ALTERNATIVA con E_SISTEMAZIONE_ANNULLO_NON_AMMESSO invece di dire «immutabile»: e'' l''autocritica che questo COMMENT portava gia'' — «non puo'' passare da CONFERMATA a BOZZA» e'' vero ma non aiuta chi sta provando a correggere un importo gia'' eseguito. ⛔ Nessuna tabella-matrice, di proposito: le azioni del frontend sono i verbi stessi, e chi cerca la regola nei dati non la trova — e'' qui. ⛔ E la sede resta una sola: fn_annulla_sistemazione continua a NON ricontrollare lo stato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
