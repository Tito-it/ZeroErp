{% include-markdown "it/dbzero/vendite/manual/fn_imposta_data_documento_lotto.md" %}
# ⚙️ Funzione `fn_imposta_data_documento_lotto`

```sql
CREATE FUNCTION fn_imposta_data_documento_lotto(p_lotto_id bigint, p_data date)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_imposta_data_documento_lotto(p_lotto_id bigint, p_data date)
 RETURNS TABLE(aggiornate integer, saltate_numerate integer, rate_rigenerate integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_pavimento  vendite.registri_fatturazione_progressivi.ultima_data%TYPE;
    -- ⚠️ `text`: non riflette nessuna colonna. Vale SEQUENZA o
    --    EMISSIONE, e serve solo a scegliere la frase.
    v_origine    text;
    -- ⚠️ `bigint[]` esplicito: `colonna%TYPE[]` non esiste in PostgreSQL.
    v_toccate    bigint[];
    v_id         vendite.fatture.id%TYPE;
    -- ⚠️ `integer` esplicito: sono CONTEGGI, non valori di colonna.
    v_aggiornate integer := 0;
    v_saltate    integer := 0;
    v_rate       integer := 0;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dichiarare la data documento di un lotto: la scrive sul
    --   lotto, la propaga alle fatture non ancora numerate e
    --   rigenera i loro piani rate.
    --
    -- Regole:
    --   - le fatture gia' numerate si SALTANO e si contano;
    --   - le rate si rigenerano solo dove un piano esiste;
    --   - una data sotto il pavimento si rifiuta subito, con il
    --     codice del pavimento che ha morso.
    -- =========================================================

    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_imposta_data_documento_lotto',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'lotto_id obbligatorio e maggiore di zero',
                'p_lotto_id', p_lotto_id),
            NULL::uuid,
            'vendite.fn_imposta_data_documento_lotto',
            'p_lotto_id (obbligatorio, maggiore di zero)');
    END IF;

    IF p_data IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_imposta_data_documento_lotto',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'data documento obbligatoria',
                'p_lotto_id', p_lotto_id),
            NULL::uuid,
            'vendite.fn_imposta_data_documento_lotto',
            'p_data (obbligatorio)');
    END IF;

    -- Il lotto deve esistere ED essere visibile: sotto RLS le due
    -- cose coincidono, e va bene cosi' — non si dichiara la data
    -- di un lotto che non si puo' vedere.
    PERFORM 1 FROM vendite.fatturazione_lotti fl WHERE fl.id = p_lotto_id;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_imposta_data_documento_lotto',
            'E_LOTTO_NON_TROVATO',
            jsonb_build_object('lotto_id', p_lotto_id),
            NULL::uuid, p_lotto_id::text);
    END IF;

    -- ─── 1) IL PAVIMENTO, E QUALE DEI DUE HA MORSO ───────────
    -- ⭐ rev 2026-08-26: si legge la COPPIA. La regola non si
    --    riscrive qui — arriva gia' composta — ma senza l'origine
    --    non si potrebbe scegliere la frase.
    -- ⭐ Il rifiuto arriva QUI e subito invece che a meta' giro di
    --    numerazione. Non e' un secondo presidio: e' la sua
    --    anticamera, e se sfugge (la lettura e' fail-open sotto
    --    RLS) rifiutera' il cancello vero.
    SELECT pl.pavimento, pl.origine
      INTO v_pavimento, v_origine
      FROM vendite.fn_get_pavimento_lotto(p_lotto_id) pl;

    IF v_pavimento IS NOT NULL AND p_data < v_pavimento THEN

        IF v_origine = 'EMISSIONE' THEN
            -- ⛔ Nessun BERSAGLIO: il limite di emissione non ha
            --    dietro nessun documento da aprire, e un pulsante
            --    verso il nulla e' peggio di nessun pulsante.
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'fn_imposta_data_documento_lotto',
                'E_FATTURA_DATA_OLTRE_LIMITE_EMISSIONE',
                jsonb_build_object(
                    'campo',          'data_documento',
                    'lotto_id',       p_lotto_id,
                    'pavimento',      v_pavimento,
                    'origine',        v_origine,
                    'data_richiesta', p_data),
                NULL::uuid,
                -- ⭐ Nella frase va il pavimento EFFETTIVO, in
                --    formato italiano: a leggerlo e' una persona.
                to_char(v_pavimento, 'DD/MM/YYYY'));
        END IF;

        -- Origine SEQUENZA (o pareggio, che va a SEQUENZA).
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_imposta_data_documento_lotto',
            'E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO',
            jsonb_build_object(
                'campo',          'data_documento',
                'lotto_id',       p_lotto_id,
                'ultima_data',    v_pavimento,
                'origine',        v_origine,
                'data_richiesta', p_data,
                -- ⭐ Qui il bersaglio e' il LOTTO: e' la cosa che
                --    l'operatore ha davanti, e la fattura
                --    colpevole non e' ancora stata scelta.
                'bersaglio', jsonb_build_array(
                    jsonb_build_object('tipo', 'LOTTO',
                                       'id', p_lotto_id::text))),
            NULL::uuid,
            to_char(v_pavimento, 'DD/MM/YYYY'));
    END IF;

    -- ─── 2) QUANTE SI SALTANO ─────────────────────────────────
    SELECT count(*)::integer
      INTO v_saltate
      FROM vendite.fatturazione_lotti_fatture lf
      JOIN vendite.fatture f ON f.id = lf.fattura_id
     WHERE lf.lotto_id = p_lotto_id
       AND f.numero IS NOT NULL;

    -- ─── 3) LA DATA SUL LOTTO ─────────────────────────────────
    -- ⚠️ Anche se nessuna fattura si muove: la dichiarazione vale
    --    per i documenti che il lotto produrra' dopo.
    UPDATE vendite.fatturazione_lotti
       SET data_documento = p_data
     WHERE id = p_lotto_id
       AND data_documento IS DISTINCT FROM p_data;

    -- ─── 4) LA DATA SULLE FATTURE ─────────────────────────────
    -- ⛔ Filtro su `numero IS NULL` e NON sullo stato: una fattura
    -- viene numerata MENTRE e' in EMESSA, quindi una soglia per
    -- stato lascerebbe passare una numerata — e il guard
    -- trg_fatture_a10_guard_data_numerata_upd la rifiuterebbe,
    -- facendo fallire l'intera dichiarazione.
    -- ⚠️ Lo stato serve lo stesso, per non toccare documenti oltre
    -- la finestra in cui le rate sono ancora rigenerabili.
    -- ⚠️ `IS DISTINCT FROM`: senza, si riscriverebbe la stessa data
    -- generando storico e audit per niente.
    WITH aggiornate AS (
        UPDATE vendite.fatture f
           SET data = p_data
         WHERE f.id IN (SELECT lf.fattura_id
                          FROM vendite.fatturazione_lotti_fatture lf
                         WHERE lf.lotto_id = p_lotto_id)
           AND f.numero IS NULL
           AND f.data IS DISTINCT FROM p_data
           AND f.stato_doc_fiscale_id IN (
                   SELECT sd.id FROM config.stati_doc_fiscale sd
                    WHERE sd.codice_interno IN ('DRAFT', 'EMESSA'))
        RETURNING f.id
    )
    SELECT array_agg(a.id), count(*)::integer
      INTO v_toccate, v_aggiornate
      FROM aggiornate a;

    -- ─── 5) I PIANI RATE SEGUONO LA DATA ──────────────────────
    -- ⛔ Non e' opzionale: le scadenze si calcolano da f.data, e il
    -- guard D-K verifica la SOMMA delle rate, che non cambia —
    -- quindi una data nuova con rate vecchie passa in silenzio.
    -- ⚠️ Solo dove un piano ESISTE: su una DRAFT senza totali
    -- fn_genera_scadenze_fattura alzerebbe
    -- E_SCADENZE_BASE_NON_PRONTA e farebbe fallire un caso
    -- legittimo. Se il piano non c'e', lo step EMESSA lo creera'
    -- con la data nuova.
    -- ⚠️ In un'istruzione SEPARATA dall'UPDATE qui sopra: dentro la
    -- stessa, la snapshot leggerebbe la data VECCHIA.
    FOREACH v_id IN ARRAY COALESCE(v_toccate, ARRAY[]::bigint[]) LOOP
        IF EXISTS (SELECT 1 FROM vendite.fatture_scadenze s
                    WHERE s.fattura_id = v_id) THEN
            PERFORM vendite.fn_genera_scadenze_fattura(v_id);
            v_rate := v_rate + 1;
        END IF;
    END LOOP;

    RETURN QUERY SELECT COALESCE(v_aggiornate, 0), v_saltate, v_rate;
END;
$function$

COMMENT ON FUNCTION vendite.fn_imposta_data_documento_lotto(p_lotto_id bigint, p_data date)
IS 'Dichiara la data documento di un lotto: la scrive sul lotto, la propaga alle fatture NON ancora numerate e rigenera i loro piani rate. ⭐ E'' una funzione MADRE — quattro scritture, una sola SELECT, atomica per costruzione (linee-guida-sql §5b): farle in sequenza dal backend lascerebbe una data nuova con le rate vecchie. ⛔ LA RIGENERAZIONE DELLE RATE NON E'' OPZIONALE: le scadenze si calcolano da f.data nello step EMESSA, cioe'' PRIMA del numero, e il guard D-K verifica che la SOMMA delle rate quadri col totale — la somma non cambia, cambiano le DATE, quindi una data nuova con rate vecchie passerebbe in silenzio. ⚠️ Si rigenera SOLO dove un piano esiste gia'': su una DRAFT senza totali fn_genera_scadenze_fattura alzerebbe E_SCADENZE_BASE_NON_PRONTA e farebbe fallire l''intera dichiarazione su un caso legittimo. ⚠️ Le fatture GIA'' NUMERATE si SALTANO e si contano, non fanno fallire il lotto: il caso «lotto numerato a meta''» esiste nei dati e rifiutare l''intero lotto renderebbe irrisolvibile proprio il caso per cui questa funzione esiste. ⛔ Il filtro e'' `numero IS NULL` e NON lo stato: una fattura viene numerata MENTRE e'' in EMESSA. ⭐ rev 2026-08-26 (cantiere limite-emissione, DB-9): il guard sul pavimento legge la COPPIA (pavimento, origine) da vendite.fn_get_pavimento_lotto e sceglie fra DUE CODICI — E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO quando a mordere e'' la sequenza, E_FATTURA_DATA_OLTRE_LIMITE_EMISSIONE quando e'' il limite di emissione. Sono due frasi e due rimedi: la prima si risolve risalendo alla fattura che porta quel numero, la seconda solo avvicinando la data a oggi, e dire la prima quando vale la seconda manda a cercare la cosa sbagliata. A parita'' di data vince SEQUENZA, perche'' la sua frase puo'' portare un BERSAGLIO — sul limite di emissione non c''e'' nessun documento da aprire, e un pulsante verso il nulla e'' peggio di nessun pulsante. ⭐ La data nella frase e'' SEMPRE il pavimento EFFETTIVO e non quello di `origine`: nominarne un altro direbbe all''operatore di scegliere una data che verrebbe rifiutata di nuovo. ⭐ QUI IL CONTROLLO E'' SEVERO E NON PER CASO: questa e'' la porta da cui una PERSONA dichiara una data, e qui c''e'' il LOTTO, quindi la competenza vera. Il cancello di fn_get_next_progressivo riceve solo il documento e la sua data e la DEDUCE dalla data stessa (decisione D-7): due severita'' diverse, questa e'' la piu'' stretta, e chi le confronta non deve leggere la differenza come un difetto. ℹ️ Non e'' un secondo presidio: e'' l''anticamera del cancello — la lettura del pavimento e'' fail-open sotto RLS e se sfugge rifiutera'' il cancello vero, che legge il contatore. ℹ️ Torna TRE numeri: rate_rigenerate c''e'' perche'' senza di esso il punto 5 sarebbe invisibile al backend. Brief: brief-db-limite-emissione-e-data-verificata §11 DB-9.';
```

</div>

---
{% include-markdown "signature-core.md" %}
