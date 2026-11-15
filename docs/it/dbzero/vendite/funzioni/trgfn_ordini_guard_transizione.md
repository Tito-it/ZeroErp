{% include-markdown "it/dbzero/vendite/manual/trgfn_ordini_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_ordini_guard_transizione`

```sql
CREATE FUNCTION trgfn_ordini_guard_transizione()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ordini_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: enforcement DB-first del grafo transizioni stato ordine.
--   La transizione (OLD.stato -> NEW.stato) e' ammessa solo se
--   presente e attiva in config.transizioni_stati_ordini. In piu',
--   DRAFT->CONFERMATO richiede almeno una riga ordine ATTIVA,
--   ->CONFERMATO passa da script.fn_check_ordine_confermabile e
--   ->ANNULLATO da script.fn_check_ordine_annullabile.
--   Letto dalla matrice (no grafo hardcodato): SSOT col lato
--   lettura fn_available_actions_ordine.
--   rev 2026-07-16: Regola 2 filtra attivo IS TRUE.
--   rev 2026-08-04: Regola 3, l'annullamento riattivato ha i suoi
--   controlli (brief-db-vie-uscita-operatore).
--   rev 2026-08-29: Regola 4, l'aliquota sulle righe che portano
--   un prezzo (brief-db-be-iva-risolutore-e-regime-cliente, I9).
--   rev 2026-09-24: Regola 5, i prezzi non autorizzati su DRAFT ->
--   CONFERMATO (brief-db-preventivi-congelamento-pricing, D-5/D-6).
--   rev 2026-11-14 (brief-db-stati-documento-dal-vocabolario, giro 6b):
--   le regole 2-5 sul significato degli stati, dal vocabolario: lo stato
--   iniziale della partenza, lo stato di emissione e quello di annullo
--   (is_abortito) della destinazione. Dove sotto si legge DRAFT,
--   CONFERMATO o ANNULLATO, vale lo stato che il vocabolario marca.
DECLARE
    v_codice_da config.stati_doc_ordini.codice_interno%TYPE;
    v_codice_a  config.stati_doc_ordini.codice_interno%TYPE;
    -- Il significato della partenza e della destinazione, dal vocabolario.
    v_iniziale_da  config.stati_doc_ordini.iniziale%TYPE;
    v_emissione_a  config.stati_doc_ordini.emissione%TYPE;
    v_abortito_a   config.stati_doc_ordini.is_abortito%TYPE;
    v_ammessa   boolean := false;
    v_motivi    jsonb;
BEGIN
    -- No-op se lo stato non cambia davvero (UPDATE su altre colonne).
    IF NEW.stato_doc_ordine_id IS NOT DISTINCT FROM OLD.stato_doc_ordine_id THEN
        RETURN NEW;
    END IF;

    SELECT
        max(CASE WHEN id = OLD.stato_doc_ordine_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_doc_ordine_id THEN codice_interno END),
        bool_or(iniziale)    FILTER (WHERE id = OLD.stato_doc_ordine_id),
        bool_or(emissione)   FILTER (WHERE id = NEW.stato_doc_ordine_id),
        bool_or(is_abortito) FILTER (WHERE id = NEW.stato_doc_ordine_id)
      INTO v_codice_da, v_codice_a, v_iniziale_da, v_emissione_a, v_abortito_a
      FROM config.stati_doc_ordini
     WHERE id IN (OLD.stato_doc_ordine_id, NEW.stato_doc_ordine_id);

    -- Regola 1: la transizione deve esistere ed essere attiva in matrice.
    SELECT EXISTS (
        SELECT 1
          FROM config.transizioni_stati_ordini t
         WHERE t.stato_da_id = OLD.stato_doc_ordine_id
           AND t.stato_a_id  = NEW.stato_doc_ordine_id
           AND t.attivo IS TRUE
    ) INTO v_ammessa;

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_ORDINE_TRANSIZIONE_NON_AMMESSA',
            jsonb_build_object(
                'ordine_id', NEW.id,
                'numero',    NEW.numero,
                'stato_da',  v_codice_da,
                'stato_a',   v_codice_a
            ),
            NEW.tx_id,
            NEW.id::text,
            coalesce(v_codice_da, 'NULL'),
            coalesce(v_codice_a,  'NULL')
        );
    END IF;

    -- Regola 2: DRAFT->CONFERMATO richiede almeno una riga ATTIVA.
    -- Spostata da ordini_service.py (E_ORD_NESSUNA_RIGA inline) per
    -- DB-first: vale per ogni chiamante, non solo conferma().
    -- Una riga disattivata e' logicamente cancellata: un ordine con
    -- sole righe inattive e' vuoto e non va confermato.
    -- Nessun vincolo su quantita/prezzo/totale: conta la sola
    -- presenza (un ordine a totale zero deve poter avanzare).
    IF v_iniziale_da AND v_emissione_a THEN
        IF NOT EXISTS (
            SELECT 1 FROM vendite.ordini_righe r
             WHERE r.ordine_id = NEW.id
               AND r.attivo IS TRUE
        ) THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME::text,
                'E_ORDINE_CONFERMA_SENZA_RIGHE',
                jsonb_build_object(
                    'ordine_id', NEW.id,
                    'numero',    NEW.numero
                ),
                NEW.tx_id,
                NEW.id::text,
                coalesce(NEW.numero, 'NULL')
            );
        END IF;
    END IF;

    -- Regola 3 (rev 2026-08-04): l'annullamento non deve poter
    -- cancellare un documento che ha gia' prodotto qualcosa a
    -- valle. La regola vive nella funzione pura, la STESSA che
    -- fn_available_actions_ordine usa per accendere il bottone:
    -- qui si solleva soltanto, col codice del PRIMO motivo.
    IF v_abortito_a THEN
        v_motivi := script.fn_check_ordine_annullabile(NEW.id);

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
                'ordine_id', NEW.id,
                'numero',    NEW.numero,
                'stato_da',  v_codice_da,
                'stato_a',   v_codice_a));
    END IF;

    -- Regola 4 (rev 2026-08-29): una riga che porta un PREZZO porta
    -- anche l'ALIQUOTA. Stessa forma della Regola 3 — la regola sta
    -- nella funzione pura, qui si solleva soltanto.
    --
    -- ⚠️ Il perimetro e' QUALUNQUE transizione verso CONFERMATO, non
    --   il solo DRAFT->CONFERMATO della Regola 2: la matrice ammette
    --   il rientro da PARZIALMENTE_EVASO e da EVASO, e un ordine che
    --   torna CONFERMATO con una riga senza aliquota produce lo
    --   stesso riepilogo storto del percorso diretto. La vista del
    --   riepilogo non sa da dove si arriva, e il vincolo deve avere
    --   lo stesso perimetro del consumatore che protegge.
    --
    -- ⚠️ Nel VARIADIC va il NUMERO di riga, non l'id: quel valore
    --   riempie i %s, cioe' compone la frase che una persona legge,
    --   e un id tecnico non si cerca a mano sul documento. L'id
    --   viaggia nel context, che e' il canale di chi diagnostica.
    -- ⛔ E nessuna chiave `campo`: il codice e' CONFLITTO_STATO, non
    --   DATO_ERRATO — la richiesta e' «porta l'ordine a CONFERMATO»,
    --   e non c'e' un campo di QUELLA richiesta da accendere.
    IF v_emissione_a THEN
        v_motivi := script.fn_check_ordine_confermabile(NEW.id);

        -- ⚠️ `riga_id` e `riga_nr` NON si estraggono piu' a mano: stanno nel
        --   `dettaglio` del motivo, che l'helper fonde nel contesto. Erano due
        --   righe che ricopiavano una struttura decisa dalla check.
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
                'ordine_id', NEW.id,
                'numero',    NEW.numero,
                'stato_da',  v_codice_da,
                'stato_a',   v_codice_a));
    END IF;

    -- Regola 5 (rev 2026-09-24): un ordine con un prezzo che nessuno ha
    -- autorizzato — in attesa o rifiutato, sui componenti BoM attivi (la
    -- riga d'ordine lo stato non lo porta) — non si conferma (D-1, D-6).
    --
    -- ⭐ Il predicato e' il building block script.fn_check_prezzi_autorizzati,
    --   lo STESSO che fn_available_actions_ordine usa per spegnere
    --   «Conferma»: qui si solleva soltanto.
    -- ⛔ Solo DRAFT -> CONFERMATO, e NON dentro fn_check_ordine_confermabile
    --   come l'aliquota della Regola 4. La matrice fa RIENTRARE l'ordine in
    --   CONFERMATO da EVASO e PARZIALMENTE_EVASO, in automatico, quando
    --   l'evasione torna indietro (un DDT annullato). Quel rientro non
    --   conferma niente di nuovo: un prezzo rimasto non autorizzato sul
    --   documento lo bloccherebbe, e con lui l'annullamento a valle — una via
    --   d'uscita (D-2). L'aliquota invece protegge il riepilogo IVA, che non
    --   sa da dove si arriva: per questo le due regole hanno perimetri
    --   diversi, ed e' voluto.
    IF v_iniziale_da AND v_emissione_a THEN
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'database', TG_NAME::text,
            script.fn_check_prezzi_autorizzati('vendite.ordini'::regclass, NEW.id),
            NULL,
            NEW.tx_id,
            jsonb_build_object(
                'ordine_id', NEW.id,
                'numero',    NEW.numero,
                'stato_da',  v_codice_da,
                'stato_a',   v_codice_a));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ordini_guard_transizione()
IS 'Trigger function (BEFORE UPDATE dello stato di vendite.ordini): giudica il passaggio. Regola 1: la transizione esiste attiva in config.transizioni_stati_ordini (E_ORDINE_TRANSIZIONE_NON_AMMESSA). Regola 2: dallo stato iniziale allo stato di emissione l''ordine ha almeno una riga attiva (E_ORDINE_CONFERMA_SENZA_RIGHE), senza vincoli su quantita'' e prezzo. Regola 3: verso lo stato di annullo (is_abortito) il primo motivo di script.fn_check_ordine_annullabile. Regola 4: verso lo stato di emissione, da qualunque partenza (anche il rientro automatico dall''evasione), il primo motivo di script.fn_check_ordine_confermabile: una riga attiva che porta un prezzo porta anche l''aliquota, perche'' il riepilogo IVA non sa da dove si arriva. Regola 5: dallo stato iniziale allo stato di emissione il primo motivo di script.fn_check_prezzi_autorizzati (componenti BoM attivi col prezzo in attesa o rifiutato); non sul rientro dall''evasione, che non conferma niente di nuovo e non deve fermare l''annullamento a valle. Il significato degli stati (iniziale, emissione, is_abortito) si legge da config.stati_doc_ordini; i codici vanno nel contesto degli errori. Sono gli stessi predicati che script.fn_available_actions_ordine usa per spegnere i pulsanti.';
```

</div>

---
{% include-markdown "signature-core.md" %}
