{% include-markdown "it/dbzero/anagrafiche/manual/fn_consuma_plafond_titolo_iva_righe.md" %}
# ⚙️ Funzione `fn_consuma_plafond_titolo_iva_righe`

```sql
CREATE FUNCTION fn_consuma_plafond_titolo_iva_righe(p_titolo_iva_id bigint, p_fattura_id bigint, p_fattura_riga_ids bigint[], p_imponibili numeric[], p_data_movimento date, p_tx_id uuid)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_consuma_plafond_titolo_iva_righe(p_titolo_iva_id bigint, p_fattura_id bigint, p_fattura_riga_ids bigint[], p_imponibili numeric[], p_data_movimento date, p_tx_id uuid DEFAULT NULL::uuid)
 RETURNS TABLE(fattura_riga_id bigint, imponibile numeric, quota_coperta numeric, quota_ordinaria numeric, frazione numeric, residuo_dopo numeric, movimento_id bigint)
 LANGUAGE plpgsql
AS $function$
-- Scopo: consumare la capienza di un titolo IVA con tetto per le
--   righe di UNA fattura che il chiamante attribuisce a quel titolo,
--   sul loro valore NETTO, e ritornare per ogni riga la ripartizione
--   fra parte coperta dal titolo e parte che torna all'aliquota
--   ordinaria.
--   Perimetro: un lock di riga sul titolo (D15-bis), un movimento
--   FATTURA per riga con quota diversa da zero, COL SEGNO della riga;
--   l'accumulatore riporta imponibile_utilizzato alla somma.
--   Risultato atteso: per ogni riga quota_coperta + quota_ordinaria
--   = imponibile; la stessa frazione per tutte le righe di un gruppo;
--   la somma dei movimenti fra zero e la capienza.
--   Brief: brief-db-bom-flag-quantita-e-kit-in-fattura §11 (D-5) e
--   §13 (decisione C di Tid, 2026-10-04).
-- ⭐ LA REGOLA (C): le righe positive consumano, le negative
--   restituiscono; la fattura non consuma piu' della capienza e non
--   restituisce piu' di quanto essa stessa consuma.
-- ⚠️ Non e' il risolutore: quello e' STABLE e non consuma (D14).
-- ⚠️ Non fa la restituzione della nota di credito (P4): quella nomina
--   il documento rettificato, qui si nettizza la fattura stessa.
DECLARE
    v_titolo      record;
    v_ha_plafond  config.tipi_titolo_iva.ha_plafond%TYPE;
    v_tipo_descr  config.tipi_titolo_iva.descrizione%TYPE;
    v_capienza    anagrafiche.soggetti_titoli_iva.plafond%TYPE;
    v_residuo     anagrafiche.soggetti_titoli_iva.plafond%TYPE;
    -- ⚠️ `integer` esplicito: contatori, non valori di colonna. Il
    --    contatore dei FOR (i, g) lo dichiara il ciclo da se'.
    v_n           integer;
    v_n_gruppi    integer;
    v_n_esist     integer;
    -- Le righe, nell'ordine dei gruppi (array paralleli).
    -- ⚠️ Array espliciti: `colonna%TYPE[]` non esiste in PostgreSQL.
    --    v_ids sono fatture_righe.id; v_imp l'imponibile DICHIARATO (uguale
    --    a imponibile_riga, lo pretende il guard), quello che si restituisce;
    --    v_impc lo stesso importo alla scala del REGISTRO, su cui si calcola;
    --    v_grp il numero d'ordine del gruppo (un contatore).
    v_ids         bigint[];
    v_imp         numeric[];
    v_impc        numeric[];
    v_grp         integer[];
    -- La scala di soggetti_titoli_iva_movimenti.imponibile, letta dal
    -- catalogo: e' un attributo del tipo, non il valore di una colonna.
    v_scala       integer;
    -- Per gruppo: netto e quota (importi di riga), frazione (un rapporto).
    v_netto       numeric[];
    v_quota_g     numeric[];
    v_fraz        numeric[];
    -- Per riga: quota coperta (importo di riga) e movimento.
    v_quote       numeric[];
    v_mov_ids     bigint[];
    -- ⭐ Gli scalari del calcolo si ancorano al REGISTRO: ogni quota diventa
    --    un movimento, quindi il calcolo si fa alla sua scala (v_impc). Un
    --    importo di riga con piu' decimali (imponibile_riga e' numeric(18,6))
    --    scritto nel registro verrebbe arrotondato dall'INSERT in silenzio: il
    --    movimento non sarebbe piu' la quota, l'idempotenza rileggerebbe un
    --    altro numero, e una quota di frazioni di centesimo diventerebbe uno
    --    zero che chk_stiva_movimenti_segno rifiuta.
    v_tot_pos     anagrafiche.soggetti_titoli_iva_movimenti.imponibile%TYPE := 0;
    v_tot_neg     anagrafiche.soggetti_titoli_iva_movimenti.imponibile%TYPE := 0;
    v_resto_neg   anagrafiche.soggetti_titoli_iva_movimenti.imponibile%TYPE;
    v_resto_pos   anagrafiche.soggetti_titoli_iva_movimenti.imponibile%TYPE;
    v_consumo     anagrafiche.soggetti_titoli_iva_movimenti.imponibile%TYPE;
    v_r           anagrafiche.soggetti_titoli_iva_movimenti.imponibile%TYPE;
    v_d           anagrafiche.soggetti_titoli_iva_movimenti.imponibile%TYPE;
    -- Il movimento riletto dal registro (idempotenza): il valore della colonna.
    v_q           anagrafiche.soggetti_titoli_iva_movimenti.imponibile%TYPE;
    v_mid         anagrafiche.soggetti_titoli_iva_movimenti.id%TYPE;
    v_rec         record;
BEGIN
    -- ── Guard di invocazione. Questi errori non li puo' produrre
    --    una persona: li produce un chiamante rotto, quindi la
    --    classe e' TECNICA e il messaggio nomina il PARAMETRO —
    --    e' il solo caso in cui nominarlo e' la cosa giusta.
    IF p_titolo_iva_id IS NULL OR p_titolo_iva_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'fn_consuma_plafond_titolo_iva_righe',
            'E_TITOLO_IVA_CONSUMO_NON_INVOCABILE',
            jsonb_build_object('parametro', 'titolo_iva_id',
                               'valore', p_titolo_iva_id),
            p_tx_id, 'titolo_iva_id');
    END IF;

    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'fn_consuma_plafond_titolo_iva_righe',
            'E_TITOLO_IVA_CONSUMO_NON_INVOCABILE',
            jsonb_build_object('parametro', 'fattura_id',
                               'valore', p_fattura_id),
            p_tx_id, 'fattura_id');
    END IF;

    -- ⚠️ Almeno una riga, nessuna NULL, nessuna ripetuta: due quote
    --    sulla stessa riga sarebbero due movimenti che la UNIQUE del
    --    registro rifiuta con un 23505 muto. Un movimento di fattura
    --    nomina SEMPRE la sua riga (la forma storica «riga NULL» e'
    --    ritirata con fn_consuma_plafond_titolo_iva, decisione C).
    v_n := COALESCE(cardinality(p_fattura_riga_ids), 0);
    IF v_n = 0
       OR array_position(p_fattura_riga_ids, NULL) IS NOT NULL
       OR (SELECT count(DISTINCT x) FROM unnest(p_fattura_riga_ids) x) <> v_n THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'fn_consuma_plafond_titolo_iva_righe',
            'E_TITOLO_IVA_CONSUMO_NON_INVOCABILE',
            jsonb_build_object('parametro', 'fattura_riga_ids',
                               'valore', p_fattura_riga_ids),
            p_tx_id, 'fattura_riga_ids');
    END IF;

    -- Un imponibile per riga.
    IF COALESCE(cardinality(p_imponibili), 0) <> v_n THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'fn_consuma_plafond_titolo_iva_righe',
            'E_TITOLO_IVA_CONSUMO_NON_INVOCABILE',
            jsonb_build_object('parametro', 'imponibili',
                               'valore', p_imponibili),
            p_tx_id, 'imponibili');
    END IF;

    -- ⚠️ La data e' un PARAMETRO e non `now()`: e' lo stesso
    --    vincolo di firma di D14, e per la stessa ragione — il
    --    lotto puo' girare il giorno dopo la data documento.
    IF p_data_movimento IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'fn_consuma_plafond_titolo_iva_righe',
            'E_TITOLO_IVA_CONSUMO_NON_INVOCABILE',
            jsonb_build_object('parametro', 'data_movimento'),
            p_tx_id, 'data_movimento');
    END IF;

    -- ⭐ Le righe nominate sono della fattura passata, sono CAPOFILA
    --    e non sono rettifiche. La FK del movimento dice solo che la
    --    riga esiste: senza, un movimento poteva legare la fattura A
    --    a una riga della fattura B. Una PARTE di plafond non consuma
    --    (il movimento sta sulla capofila), e una rettifica non passa
    --    dal plafond: la sua IVA e' quella della riga che rettifica
    --    (N-1), e la restituzione e' della nota di credito (P4).
    IF EXISTS (SELECT 1
                 FROM unnest(p_fattura_riga_ids) r(id)
                WHERE NOT EXISTS (SELECT 1 FROM vendite.fatture_righe fr
                                   WHERE fr.id = r.id
                                     AND fr.fattura_id = p_fattura_id
                                     AND fr.riga_capofila_id IS NULL
                                     AND fr.riga_rettificata_id IS NULL)) THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'fn_consuma_plafond_titolo_iva_righe',
            'E_TITOLO_IVA_CONSUMO_NON_INVOCABILE',
            jsonb_build_object('parametro', 'fattura_riga_ids',
                               'valore', p_fattura_riga_ids,
                               'fattura_id', p_fattura_id),
            p_tx_id, 'fattura_riga_ids');
    END IF;

    -- ⭐ L'importo dichiarato e' quello della riga. Un chiamante che ha
    --    letto la riga prima che cambiasse spezzerebbe quantita' e kit su
    --    un numero che non c'e' piu': meglio fermarsi qui. IS DISTINCT FROM
    --    prende anche il NULL.
    IF EXISTS (SELECT 1
                 FROM unnest(p_fattura_riga_ids, p_imponibili) AS x(id, imp)
                 JOIN vendite.fatture_righe fr ON fr.id = x.id
                WHERE fr.imponibile_riga IS DISTINCT FROM x.imp) THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'fn_consuma_plafond_titolo_iva_righe',
            'E_TITOLO_IVA_CONSUMO_NON_INVOCABILE',
            jsonb_build_object('parametro', 'imponibili',
                               'valore', p_imponibili,
                               'fattura_riga_ids', p_fattura_riga_ids),
            p_tx_id, 'imponibili');
    END IF;

    -- ⭐ Un kit si passa INTERO (D-5): se ne mancasse un componente,
    --    le due chiamate darebbero al kit due frazioni diverse, e la
    --    vista di esposizione una quantita' NULL.
    IF EXISTS (SELECT 1
                 FROM vendite.fatture_righe k
                WHERE k.fattura_id = p_fattura_id
                  AND k.riga_capofila_id IS NULL
                  AND k.riga_rettificata_id IS NULL
                  AND k.kit_key IN (SELECT fr.kit_key
                                      FROM vendite.fatture_righe fr
                                     WHERE fr.id = ANY (p_fattura_riga_ids))
                  AND NOT (k.id = ANY (p_fattura_riga_ids))) THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'fn_consuma_plafond_titolo_iva_righe',
            'E_TITOLO_IVA_CONSUMO_NON_INVOCABILE',
            jsonb_build_object('parametro', 'fattura_riga_ids',
                               'valore', p_fattura_riga_ids,
                               'fattura_id', p_fattura_id,
                               'motivo', 'kit incompleto'),
            p_tx_id, 'fattura_riga_ids');
    END IF;

    -- ══ I GRUPPI, letti dalle righe ═════════════════════════
    -- ⭐ Chi raggruppa e' QUI: stessa kit_key = un gruppo, una riga
    --    senza kit_key = un gruppo da sola. I gruppi nell'ordine della
    --    loro prima riga (riga_nr, poi id), che e' l'ordine di stampa:
    --    a plafond quasi esaurito decide chi resta coperto.
    -- ⭐ L'imponibile e' quello DICHIARATO (p_imponibili): il guard sopra ha
    --    gia' preteso che sia uguale a imponibile_riga. Si porta quello perche'
    --    e' cio' che il chiamante ha in mano e cio' che gli si restituisce.
    -- ⚠️ La chiave del gruppo e' la COPPIA (kit_key, id se kit_key e'
    --    NULL): un prefisso inventato su kit_key potrebbe collidere
    --    con una kit_key vera.
    WITH r AS (
        SELECT fr.id, fr.riga_nr, d.imp, fr.kit_key,
               CASE WHEN fr.kit_key IS NULL THEN fr.id END AS sciolta
          FROM vendite.fatture_righe fr
          JOIN unnest(p_fattura_riga_ids, p_imponibili) AS d(id, imp) ON d.id = fr.id
    ), gr AS (
        SELECT r.kit_key, r.sciolta,
               dense_rank() OVER (ORDER BY min(r.riga_nr), min(r.id)) AS ord
          FROM r
         GROUP BY r.kit_key, r.sciolta
    )
    SELECT array_agg(r.id            ORDER BY gr.ord, r.riga_nr, r.id),
           array_agg(r.imp           ORDER BY gr.ord, r.riga_nr, r.id),
           array_agg(gr.ord::integer ORDER BY gr.ord, r.riga_nr, r.id),
           max(gr.ord)::integer
      INTO v_ids, v_imp, v_grp, v_n_gruppi
      FROM r
      JOIN gr ON gr.kit_key IS NOT DISTINCT FROM r.kit_key
             AND gr.sciolta IS NOT DISTINCT FROM r.sciolta;

    -- ⭐ L'importo su cui si calcola e' alla scala del REGISTRO: ogni quota
    --    diventa un movimento, e il movimento deve essere ESATTAMENTE la
    --    quota. Troncato verso lo zero (trunc), cosi' la quota non supera
    --    mai il suo imponibile; le frazioni di centesimo restano nella quota
    --    ordinaria (imponibile - quota). Su un importo gia' alla scala del
    --    registro — il caso normale, arrotondamento dell'articolo a 2 — e'
    --    lo stesso numero.
    SELECT CASE WHEN a.atttypmod > 0 THEN (a.atttypmod - 4) & 65535 END
      INTO v_scala
      FROM pg_attribute a
     WHERE a.attrelid = 'anagrafiche.soggetti_titoli_iva_movimenti'::regclass
       AND a.attname  = 'imponibile';
    FOR i IN 1 .. v_n LOOP
        v_impc[i] := CASE WHEN v_scala IS NULL THEN v_imp[i]
                          ELSE trunc(v_imp[i], v_scala) END;
    END LOOP;

    -- Il netto di ogni gruppo.
    FOR g IN 1 .. v_n_gruppi LOOP
        v_netto[g] := 0;
    END LOOP;
    FOR i IN 1 .. v_n LOOP
        v_netto[v_grp[i]] := v_netto[v_grp[i]] + v_impc[i];
    END LOOP;

    -- ══ IL LOCK (D15-bis) ═══════════════════════════════════
    -- ⭐ FOR UPDATE sulla riga del titolo: due transizioni a
    --    DEFINITIVA in parallelo si serializzano qui, e la seconda
    --    legge il residuo GIA' aggiornato dalla prima. Senza,
    --    consumerebbero la stessa capienza e il plafond andrebbe
    --    sotto zero senza che nessun errore lo dica.
    SELECT t.id, t.plafond, t.imponibile_utilizzato, t.validita,
           t.tipo_titolo_iva_id
      INTO v_titolo
      FROM anagrafiche.soggetti_titoli_iva t
     WHERE t.id = p_titolo_iva_id
       FOR UPDATE;

    -- ⚠️ SELECT INTO senza righe azzera il record: senza questa
    --    uscita si proseguirebbe su NULL e si scriverebbe un
    --    movimento orfano (che la FK poi rifiuta, con un 23503
    --    muto invece del codice giusto).
    IF v_titolo.id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'fn_consuma_plafond_titolo_iva_righe',
            'E_TITOLO_IVA_CONSUMO_NON_INVOCABILE',
            jsonb_build_object('parametro', 'titolo_iva_id',
                               'valore', p_titolo_iva_id),
            p_tx_id, 'titolo_iva_id');
    END IF;

    SELECT tt.ha_plafond, tt.descrizione
      INTO v_ha_plafond, v_tipo_descr
      FROM config.tipi_titolo_iva tt
     WHERE tt.id = v_titolo.tipo_titolo_iva_id;

    -- ── Un consumo fuori dalla validita' del titolo e' un errore
    --    di chi ha risolto, non dell'operatore: il risolutore
    --    sceglie i titoli validi ALLA DATA DEL DOCUMENTO.
    IF NOT (v_titolo.validita @> p_data_movimento) THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'fn_consuma_plafond_titolo_iva_righe',
            'E_TITOLO_IVA_CONSUMO_FUORI_VALIDITA',
            jsonb_build_object('titolo_iva_id', p_titolo_iva_id,
                               'data_movimento', p_data_movimento),
            p_tx_id,
            COALESCE(v_tipo_descr, ''),
            to_char(p_data_movimento, 'DD/MM/YYYY'));
    END IF;

    -- ══ TITOLO SENZA TETTO: copre tutto, non scrive niente ═══
    -- ⚠️ `imponibile - quota_coperta` e non il letterale 0: il
    --    letterale esce con scala ZERO, gli altri rami con la
    --    scala dell'importo (correzione di I7, fatta dal test).
    IF v_ha_plafond IS NOT TRUE THEN
        FOR i IN 1 .. v_n LOOP
            fattura_riga_id := v_ids[i];
            imponibile      := v_imp[i];
            quota_coperta   := v_imp[i];
            quota_ordinaria := v_imp[i] - quota_coperta;
            frazione        := 1;
            residuo_dopo    := NULL;
            movimento_id    := NULL;
            RETURN NEXT;
        END LOOP;
        RETURN;
    END IF;

    -- ══ IDEMPOTENZA ═════════════════════════════════════════
    -- ⭐ Se una delle righe ha gia' consumato questo titolo per
    --    questa fattura, si rilegge il registro invece di scrivere:
    --    la quota di ogni riga E' il suo movimento (col segno), zero
    --    dove non c'e'. La UNIQUE parziale resta la rete, ma parla
    --    con un 23505 muto.
    SELECT count(*) INTO v_n_esist
      FROM anagrafiche.soggetti_titoli_iva_movimenti m
     WHERE m.titolo_iva_id  = p_titolo_iva_id
       AND m.tipo_movimento = 'FATTURA'
       AND m.fattura_id     = p_fattura_id
       AND m.fattura_riga_id = ANY (v_ids);

    IF v_n_esist > 0 THEN
        FOR g IN 1 .. v_n_gruppi LOOP
            v_quota_g[g] := 0;
        END LOOP;
        FOR i IN 1 .. v_n LOOP
            -- ⚠️ SELECT INTO a zero righe azzera le variabili:
            --    e' proprio il «vale zero» delle righe scoperte.
            SELECT m.imponibile, m.id
              INTO v_q, v_mid
              FROM anagrafiche.soggetti_titoli_iva_movimenti m
             WHERE m.titolo_iva_id   = p_titolo_iva_id
               AND m.tipo_movimento  = 'FATTURA'
               AND m.fattura_id      = p_fattura_id
               AND m.fattura_riga_id = v_ids[i];
            v_quote[i]   := COALESCE(v_q, v_impc[i] - v_impc[i]);
            v_mov_ids[i] := v_mid;
            v_quota_g[v_grp[i]] := v_quota_g[v_grp[i]] + v_quote[i];
        END LOOP;
        v_residuo := v_titolo.plafond - v_titolo.imponibile_utilizzato;
        FOR i IN 1 .. v_n LOOP
            fattura_riga_id := v_ids[i];
            imponibile      := v_imp[i];
            quota_coperta   := v_quote[i];
            quota_ordinaria := v_imp[i] - v_quote[i];
            -- Netto zero: coperto per intero (§13.2, punto 6).
            frazione        := CASE WHEN v_netto[v_grp[i]] = 0 THEN 1
                                    ELSE v_quota_g[v_grp[i]] / v_netto[v_grp[i]] END;
            residuo_dopo    := v_residuo;
            movimento_id    := v_mov_ids[i];
            RETURN NEXT;
        END LOOP;
        RETURN;
    END IF;

    -- ══ LA QUOTA DI OGNI GRUPPO, SUL NETTO (C) ══════════════
    -- ⚠️ GREATEST(..., 0): un titolo gia' sfondato da una forzatura
    --    ha residuo negativo, e senza questo la capienza diventerebbe
    --    negativa — cioe' un consumo che RESTITUISCE capienza.
    v_capienza := GREATEST(v_titolo.plafond - v_titolo.imponibile_utilizzato, 0);

    FOR g IN 1 .. v_n_gruppi LOOP
        IF v_netto[g] > 0 THEN
            v_tot_pos := v_tot_pos + v_netto[g];
        ELSIF v_netto[g] < 0 THEN
            v_tot_neg := v_tot_neg - v_netto[g];
        END IF;
    END LOOP;

    -- ⭐ Prima i NEGATIVI, fino a quanto valgono i positivi: la
    --    fattura non restituisce piu' di quanto consuma. Il negativo
    --    che avanza resta all'ordinaria: restituire plafond consumato
    --    da un ALTRO documento e' della nota di credito (P4).
    v_resto_neg := LEAST(v_tot_neg, v_tot_pos);
    -- ⭐ Poi i POSITIVI, fino alla capienza PIU' quanto i negativi
    --    hanno restituito: il primo per intero, poi uno spezzato, poi
    --    gli altri all'ordinaria, nell'ordine dei gruppi.
    v_resto_pos := LEAST(v_tot_pos, v_capienza + v_resto_neg);

    FOR g IN 1 .. v_n_gruppi LOOP
        IF v_netto[g] < 0 THEN
            v_quota_g[g] := -LEAST(-v_netto[g], v_resto_neg);
            v_resto_neg  := v_resto_neg + v_quota_g[g];
            v_fraz[g]    := v_quota_g[g] / v_netto[g];
        ELSIF v_netto[g] > 0 THEN
            v_quota_g[g] := LEAST(v_netto[g], v_resto_pos);
            v_resto_pos  := v_resto_pos - v_quota_g[g];
            v_fraz[g]    := v_quota_g[g] / v_netto[g];
        ELSE
            -- ⭐ Netto zero (un omaggio nel kit, o +50 e −50): coperto
            --    per intero. Non consuma niente, quindi il titolo non
            --    ha motivo di lasciarlo.
            v_quota_g[g] := 0;
            v_fraz[g]    := 1;
        END IF;
    END LOOP;

    -- ══ LA QUOTA DI OGNI RIGA ═══════════════════════════════
    -- ⭐ La STESSA frazione per le righe di un gruppo, arrotondata
    --    alla scala del suo imponibile (quella dell'arrotondamento
    --    del suo articolo): la riga spezzata ricalcola esattamente
    --    la sua quota. Con 0 < f < 1 il prodotto arrotondato resta
    --    fra zero e l'imponibile, col suo segno.
    FOR i IN 1 .. v_n LOOP
        IF v_fraz[v_grp[i]] = 1 THEN
            v_quote[i] := v_impc[i];
        ELSIF v_fraz[v_grp[i]] = 0 THEN
            v_quote[i] := v_impc[i] - v_impc[i];
        ELSE
            v_quote[i] := round(v_impc[i] * v_fraz[v_grp[i]], scale(v_impc[i]));
        END IF;
    END LOOP;

    -- ⭐ Il resto dei centesimi, gruppo per gruppo: prima alla riga
    --    col valore assoluto piu' grande DELLO STESSO SEGNO del
    --    gruppo (a pari merito l'ultima), poi, se il suo margine non
    --    basta, alle successive. Ogni riga si sposta solo verso i
    --    suoi estremi (zero e il suo imponibile), quindi nessuna
    --    quota cambia segno e la somma del gruppo torna esatta: il
    --    margine totale basta sempre, perche' la quota del gruppo sta
    --    fra la somma dei negativi e quella dei positivi.
    FOR g IN 1 .. v_n_gruppi LOOP
        v_r := v_quota_g[g];
        FOR i IN 1 .. v_n LOOP
            IF v_grp[i] = g THEN
                v_r := v_r - v_quote[i];
            END IF;
        END LOOP;
        CONTINUE WHEN v_r = 0;
        FOR v_rec IN
            SELECT x.i
              FROM unnest(v_impc, v_grp) WITH ORDINALITY AS x(imp, grp, i)
             WHERE x.grp = g
             ORDER BY (sign(x.imp) = sign(v_netto[g])) DESC, abs(x.imp) DESC, x.i DESC
        LOOP
            -- Il margine della riga nel verso del resto: verso l'alto
            -- fino a max(0, imponibile), verso il basso fino a
            -- min(0, imponibile).
            IF v_r > 0 THEN
                v_d := LEAST(v_r, GREATEST(v_impc[v_rec.i], 0) - v_quote[v_rec.i]);
            ELSE
                v_d := GREATEST(v_r, LEAST(v_impc[v_rec.i], 0) - v_quote[v_rec.i]);
            END IF;
            v_quote[v_rec.i] := v_quote[v_rec.i] + v_d;
            v_r := v_r - v_d;
            EXIT WHEN v_r = 0;
        END LOOP;
    END LOOP;

    -- ══ IL REGISTRO: un movimento per riga, col SEGNO della riga ══
    -- ⚠️ Prima i POSITIVI, poi i negativi: l'accumulatore rifiuta il
    --    conto sotto zero a OGNI riga scritta, e un negativo scritto
    --    per primo su un titolo intonso lo farebbe scattare anche se
    --    la fattura, a fine giro, consuma.
    -- ⚠️ Zero non e' un movimento (chk_stiva_movimenti_segno): una
    --    riga a quota zero non scrive.
    FOR i IN 1 .. v_n LOOP
        v_mov_ids[i] := NULL;
    END LOOP;
    FOR i IN 1 .. v_n LOOP
        IF v_quote[i] > 0 THEN
            INSERT INTO anagrafiche.soggetti_titoli_iva_movimenti
                (titolo_iva_id, tipo_movimento, imponibile, data_movimento,
                 fattura_id, fattura_riga_id, tx_id)
            VALUES
                (p_titolo_iva_id, 'FATTURA', v_quote[i], p_data_movimento,
                 p_fattura_id, v_ids[i], p_tx_id)
            RETURNING id INTO v_mid;
            v_mov_ids[i] := v_mid;
        END IF;
    END LOOP;
    FOR i IN 1 .. v_n LOOP
        IF v_quote[i] < 0 THEN
            INSERT INTO anagrafiche.soggetti_titoli_iva_movimenti
                (titolo_iva_id, tipo_movimento, imponibile, data_movimento,
                 fattura_id, fattura_riga_id, tx_id)
            VALUES
                (p_titolo_iva_id, 'FATTURA', v_quote[i], p_data_movimento,
                 p_fattura_id, v_ids[i], p_tx_id)
            RETURNING id INTO v_mid;
            v_mov_ids[i] := v_mid;
        END IF;
    END LOOP;

    -- Il consumo NETTO della fattura: e' lui che il registro somma.
    v_consumo := 0;
    FOR g IN 1 .. v_n_gruppi LOOP
        v_consumo := v_consumo + v_quota_g[g];
    END LOOP;

    FOR i IN 1 .. v_n LOOP
        fattura_riga_id := v_ids[i];
        imponibile      := v_imp[i];
        quota_coperta   := v_quote[i];
        quota_ordinaria := v_imp[i] - v_quote[i];
        frazione        := v_fraz[v_grp[i]];
        residuo_dopo    := v_capienza - v_consumo;
        movimento_id    := v_mov_ids[i];
        RETURN NEXT;
    END LOOP;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_consuma_plafond_titolo_iva_righe(p_titolo_iva_id bigint, p_fattura_id bigint, p_fattura_riga_ids bigint[], p_imponibili numeric[], p_data_movimento date, p_tx_id uuid)
IS 'Consumo del plafond di un titolo IVA con tetto per le righe di UNA fattura che il chiamante attribuisce a quel titolo, sul loro valore NETTO (brief-db-bom-flag-quantita-e-kit-in-fattura §13, decisione C di Tid del 2026-10-04; §11, D-5): le righe positive consumano, le negative restituiscono, e la fattura non consuma piu'' della capienza ne'' restituisce piu'' di quanto essa stessa consuma. ⭐ I GRUPPI li fa lei: stessa kit_key = un gruppo (un kit si spezza come un''unita'' sola, D-5), una riga senza kit_key = un gruppo da sola, nell''ordine della prima riga (riga_nr, poi id), che e'' l''ordine di stampa. L''imponibile si legge dalla riga (imponibile_riga); p_imponibili resta nella firma, che non si riordina, come contratto di coerenza: deve dire lo stesso, o la chiamata si ferma (il chiamante ha ragionato su una riga che e'' cambiata). ⭐ LA QUOTA DI OGNI GRUPPO: i gruppi a netto negativo si coprono, in ordine, fino a quanto valgono i positivi (N- = min(negativi, positivi)); i positivi, in ordine, fino a min(positivi, capienza + N-): il primo per intero, poi uno spezzato, poi gli altri all''ordinaria; un gruppo a netto zero e'' coperto per intero (frazione 1). Il negativo che avanza resta all''ordinaria: restituire plafond consumato da un altro documento e'' della nota di credito (P4). ⭐ DENTRO IL GRUPPO una frazione sola: ogni riga round(imponibile * f, scala del suo imponibile), il resto dei centesimi alla riga di valore assoluto piu'' grande dello stesso segno del gruppo (a pari merito l''ultima), poi alle successive entro il loro margine: ogni quota resta fra zero e il suo imponibile, col suo segno, e la somma e'' esatta. ⭐ IL REGISTRO: un movimento FATTURA per riga con quota diversa da zero, COL SEGNO della riga (chk_stiva_movimenti_segno ammette FATTURA <> 0 da 20261004-02), prima tutti i positivi e poi i negativi, perche'' l''accumulatore rifiuta il conto sotto zero a ogni riga scritta. Ritorna per ogni riga imponibile, quota coperta, quota ordinaria (che sommano all''imponibile), la frazione del suo gruppo (con cui il chiamante divide quantita'' e kit_qta), il residuo del titolo dopo il consumo netto e il movimento. ⭐ E'' la SEDE delle regole di consumo: guard (righe della fattura, capofila, non rettifiche, kit interi), lock sul titolo (D15-bis), validita'', titolo senza tetto (copre tutto, non scrive), idempotenza (se una riga ha gia'' un movimento si rilegge il registro: quota = movimento, zero dove non c''e''; netto zero = frazione 1) e capienza GREATEST(plafond - utilizzato, 0). ⛔ Chi sceglie il titolo e'' il chiamante: il BE risolve ogni gruppo con vendite.fn_resolve_iva_riga(p_consumo => true), giudicando un kit sull''articolo PADRE (D-5.1), e passa qui tutte le righe di quel titolo in una chiamata. ⛔ La forma a una riga (fn_consuma_plafond_titolo_iva) e'' ritirata da 20261004-05, e con lei la riga NULL. ⛔ Non e'' il risolutore (STABLE, non consuma) e non fa la restituzione della nota di credito (P4).';
```

</div>

---
{% include-markdown "signature-core.md" %}
