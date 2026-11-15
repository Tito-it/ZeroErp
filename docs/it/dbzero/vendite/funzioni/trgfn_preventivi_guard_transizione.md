{% include-markdown "it/dbzero/vendite/manual/trgfn_preventivi_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_preventivi_guard_transizione`

```sql
CREATE FUNCTION trgfn_preventivi_guard_transizione()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_preventivi_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: enforcement DB-first del grafo transizioni del preventivo.
--   La transizione (OLD.stato -> NEW.stato) e' ammessa solo se
--   presente e ATTIVA in config.transizioni_stati_preventivi.
--   Letto dalla matrice, nessun grafo hardcodato: stessa sorgente
--   di fn_available_actions_preventivo, quindi la UI non puo'
--   proporre cio' che il database rifiuta, ne' viceversa.
--   Mirror di vendite.trgfn_ordini_guard_transizione (Regola 1).
--   Brief: brief-db-vie-uscita-operatore §6.2, §7.4 punto 3.
--   rev 2026-11-14 (brief-db-stati-documento-dal-vocabolario, giro 6a): la
--   Regola 3 riconosce l'accettazione dal vocabolario, non dal codice.
--   rev 2026-08-29: Regola 2, l'aliquota sulle righe che entrano
--   nel riepilogo IVA (brief-db-be-iva-risolutore-e-regime-cliente,
--   I9).
--   rev 2026-10-31: Regola 3 dai motivi di fn_check_preventivo_accettabile,
--   + la validita' finita (brief-db-scadenza-preventivi, E-2).
--   rev 2026-09-24: Regola 3, i prezzi non autorizzati entrando in
--   ACCETTATO (brief-db-preventivi-congelamento-pricing, D-2). Verso
--   EMESSO arrivano gia' dalla Regola 2, dentro
--   fn_check_preventivo_emettibile. Assorbe e ritira il trigger a10
--   trgfn_preventivi_guard_transizione_approvazione.
--
-- Cosa NON fa, per scelta:
--   - l'annullamento ha il suo guard dedicato
--     (trgfn_preventivi_guard_annullamento, 20260804-35): qui si
--     verifica solo che la strada esista, non che sia percorribile;
--   - la regola "documento senza righe" vive ancora nella porta
--     vendite.fn_cambia_stato_preventivo e un UPDATE diretto la
--     aggira: e' un'asimmetria dichiarata, non una dimenticanza.
--     ⚠️ La Regola 2 NON la imita: una regola che protegge un
--     numero fiscale non puo' dipendere da quale porta ha usato
--     il chiamante.
DECLARE
    v_codice_da config.stati_doc_preventivi.codice_interno%TYPE;
    v_codice_a  config.stati_doc_preventivi.codice_interno%TYPE;
    v_ammessa   boolean := false;
    v_motivi    jsonb;
BEGIN
    -- No-op se lo stato non cambia davvero (UPDATE su altre colonne).
    IF NEW.stato_doc_preventivo_id IS NOT DISTINCT FROM OLD.stato_doc_preventivo_id THEN
        RETURN NEW;
    END IF;

    SELECT
        max(CASE WHEN id = OLD.stato_doc_preventivo_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_doc_preventivo_id THEN codice_interno END)
      INTO v_codice_da, v_codice_a
      FROM config.stati_doc_preventivi
     WHERE id IN (OLD.stato_doc_preventivo_id, NEW.stato_doc_preventivo_id);

    -- Regola 1: la transizione deve esistere ed essere attiva.
    SELECT EXISTS (
        SELECT 1
          FROM config.transizioni_stati_preventivi t
         WHERE t.stato_da_id = OLD.stato_doc_preventivo_id
           AND t.stato_a_id  = NEW.stato_doc_preventivo_id
           AND t.attivo IS TRUE
    ) INTO v_ammessa;

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_PREV_TRANSIZIONE_NON_AMMESSA',
            jsonb_build_object(
                'preventivo_id', NEW.id,
                'numero',        NEW.numero,
                'stato_da',      v_codice_da,
                'stato_a',       v_codice_a
            ),
            NEW.tx_id,
            coalesce(v_codice_da, 'NULL'),
            coalesce(v_codice_a,  'NULL')
        );
    END IF;

    -- Regola 2 (rev 2026-08-29): una riga che entra nel riepilogo
    -- IVA deve portare un'aliquota. La regola vive nella funzione
    -- pura, la STESSA che fn_available_actions_preventivo usa per
    -- spegnere il bottone: qui si solleva soltanto, col codice del
    -- PRIMO motivo.
    --
    -- ⚠️ Il predicato e' sulla DESTINAZIONE e non su una coppia
    --   cablata: oggi la matrice ha solo DRAFT->EMESSO, ma e' una
    --   lettura del seed. Cosi' una strada nuova verso EMESSO
    --   nasce gia' coperta.
    --
    -- ⛔ Nel VARIADIC va la DESCRIZIONE della riga e non un numero:
    --   vendite.preventivi_righe NON HA riga_nr, e la colonna
    --   `ordine` ha default 0 — «la riga 0» non aiuterebbe nessuno.
    --   L'id viaggia nel context, che e' il canale di chi diagnostica.
    -- ⛔ E nessuna chiave `campo`: il codice e' CONFLITTO_STATO, non
    --   DATO_ERRATO — la richiesta e' «porta il preventivo a
    --   EMESSO», e non c'e' un campo di QUELLA richiesta da accendere.
    -- ⭐ rev 2026-10-25 (20261025-49, brief-modello-documento-vendita §8):
    --   l'emissione e' lo stato che il vocabolario dichiara (colonna
    --   emissione), non il letterale. E la regola «almeno una riga
    --   attiva» sta QUI, sul passaggio (guida del modello §7): prima la
    --   aveva solo il verbo, e un UPDATE diretto la aggirava.
    IF NEW.stato_doc_preventivo_id = script.fn_stato_emissione_id('vendite.preventivi'::regclass) THEN
        IF NOT EXISTS (SELECT 1
                         FROM vendite.preventivi_righe pr
                        WHERE pr.preventivo_id = NEW.id
                          AND pr.attivo IS TRUE) THEN
            PERFORM script.fn_log_and_raise_error(
                'database', TG_NAME::text,
                'E_PREV_NESSUNA_RIGA_ATTIVA',
                jsonb_build_object('preventivo_id', NEW.id,
                                   'stato_da',      v_codice_da,
                                   'stato_a',       v_codice_a),
                NEW.tx_id,
                COALESCE(NEW.numero, NEW.id::text));
        END IF;

        v_motivi := script.fn_check_preventivo_emettibile(NEW.id);

        -- ⚠️ `riga_id` non si estrae piu' a mano: sta nel `dettaglio` del
        --   motivo, che l'helper fonde nel contesto.
        -- ⭐ La coda del primo motivo sta in un posto solo: l'helper legge il
        --   codice da `v_motivi -> 0`, ne prende i `valori` per la frase, fonde il
        --   `dettaglio` nel contesto e ci mette sempre l'elenco COMPLETO dei motivi.
        -- ⚠️ L'IF e' sparito e NON e' fail-open: l'helper tace su un array vuoto,
        --   che e' esattamente la risposta «passa». Su un non-array resta rumoroso.
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'database', TG_NAME::text,
            v_motivi,
            NULL,
            NEW.tx_id,
            jsonb_build_object(
                'preventivo_id', NEW.id,
                'numero',        NEW.numero,
                'stato_da',      v_codice_da,
                'stato_a',       v_codice_a));
    END IF;

    -- Regola 3 (rev 2026-09-24): un preventivo con un prezzo che nessuno
    -- ha autorizzato — in attesa o rifiutato, su righe o componenti BoM
    -- attivi — non diventa un impegno ACCETTATO (D-1, D-2).
    -- ⭐ rev 2026-10-31 (20261031-63, brief-db-scadenza-preventivi E-2):
    --   e nemmeno un preventivo con la validita' finita. I due motivi
    --   stanno in script.fn_check_preventivo_accettabile, la STESSA che
    --   fn_available_actions_preventivo usa per spegnere «Accetta»: qui
    --   si solleva soltanto, il primo. La regola non aspetta il job delle
    --   scadenze: fra la fine della validita' e il suo passaggio il
    --   preventivo e' ancora EMESSO.
    -- ⭐ NEW.validita_al e non una rilettura per id: questo trigger e'
    --   BEFORE ROW, e la tabella ha ancora la riga di prima.
    -- ⚠️ Sulla DESTINAZIONE, come la Regola 2: oggi ci si arriva solo da
    --   EMESSO, ma una strada nuova nasce gia' coperta. E il modello la
    --   ammette anche da EMESSO: nessun guard vieta di scrivere lo stato
    --   di approvazione sulle righe di un preventivo gia' emesso.
    -- ⚠️ Fino al 2026-09-24 lo diceva il trigger a10
    --   (trgfn_preventivi_guard_transizione_approvazione), che guardava il
    --   solo PENDING e anche le righe disattivate: ritirato nello stesso
    --   giro (20260924-24), era una seconda copia del predicato.
    -- ⭐ rev 2026-11-14 (giro 6a): l'accettazione e' lo stato che il
    --   vocabolario dichiara (colonna accettazione), come l'emissione della
    --   Regola 2. E' la stessa marca da cui la capability spegne «Accetta».
    IF NEW.stato_doc_preventivo_id = script.fn_stato_accettazione_id('vendite.preventivi'::regclass) THEN
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'database', TG_NAME::text,
            script.fn_check_preventivo_accettabile(NEW.id, NEW.validita_al),
            NULL,
            NEW.tx_id,
            jsonb_build_object(
                'preventivo_id', NEW.id,
                'numero',        NEW.numero,
                'stato_da',      v_codice_da,
                'stato_a',       v_codice_a));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_preventivi_guard_transizione()
IS 'Guard del cambio di stato del preventivo (BEFORE UPDATE OF stato_doc_preventivo_id). Le regole leggono il significato della destinazione dal vocabolario config.stati_doc_preventivi, mai il codice, che serve solo al contesto dell''errore. (1) Il passaggio deve essere una riga attiva di config.transizioni_stati_preventivi, altrimenti E_PREV_TRANSIZIONE_NON_AMMESSA. (2) Verso lo stato di emissione (script.fn_stato_emissione_id): almeno una riga attiva (E_PREV_NESSUNA_RIGA_ATTIVA; conta la presenza, un totale zero si emette), poi il primo motivo di script.fn_check_preventivo_emettibile (la validita'' finita, una riga senza aliquota che entrerebbe nel riepilogo IVA, gli indirizzi, i prezzi non autorizzati). (3) Verso lo stato di accettazione (script.fn_stato_accettazione_id): il primo motivo di script.fn_check_preventivo_accettabile(NEW.id, NEW.validita_al), la validita'' finita (E_PREV_VALIDITA_SCADUTA, senza aspettare il job delle scadenze) e poi i prezzi non autorizzati (E_DOC_PREZZO_PENDENTE, E_DOC_PREZZO_RIFIUTATO); validita_al entra da NEW perche'' il trigger e'' BEFORE ROW. Le regole 2 e 3 sono sulla destinazione, non sulla coppia: una strada nuova verso quello stato nasce coperta. Le check sono le stesse con cui script.fn_available_actions_preventivo spegne i pulsanti. L''annullo ha il suo guard, vendite.trgfn_preventivi_guard_annullamento, che scatta prima.';
```

</div>

---
{% include-markdown "signature-core.md" %}
