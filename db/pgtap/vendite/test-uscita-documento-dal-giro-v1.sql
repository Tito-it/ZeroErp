-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Elenco test (plan 17):
--  1) la check AMMETTE un documento in ERRORE (nessun motivo)
--  2) la check rifiuta un documento COMPLETED -> DOCUMENTO_NON_IN_ERRORE
--  3) la check su un documento che il lotto non ha -> SENZA_ESITO
--  4) la madre toglie dal giro il documento rotto
--  5) PRECEDENZA: un documento gia' uscito da' SOLO GIA_USCITO
--  6) la madre esclude: stato ESCLUSO e motivo scritto
--  7) il TIMBRO lo scrive il database, non il chiamante
--  8) l'errore originale RESTA sulla riga uscita
--  9) il PERIMETRO non viene toccato (D-1)
-- 10) il rientro e' rifiutato: ESCLUSO e' terminale (D-3)
-- 11) riassegnare ESCLUSO a una riga gia' esclusa NON e' rifiutato
-- 12) la madre rifiuta l'uscita senza motivo (D-5)
-- 13) il CHECK di tabella rifiuta un motivo di soli spazi
-- 14) una critica di un documento USCITO non conta piu'
-- 15) una critica del GIRO (gruppo_key NULL) continua a contare
-- 16) la segnalazione resta LEGGIBILE: non e' stata ritirata
-- 17) un documento senza bozza non trascina nessuno
-- 18) ⭐ P-1 — la frase resa del motivo 1 nomina lo STATO DEL LOTTO
-- 19) ⭐ LA GIUNTURA: il marcatore non muore su un documento uscito
-- 20) ⭐ …e non smette di marcare quelli sani
-- 21) ⭐ l'uscita COMPARE nel giornale, col suo motivo
-- 22) ⭐ una critica su un documento uscito non si scrive, un'informativa si'
--
-- Scopo:
--  - presidiare il verbo «togli un documento rotto dal giro», che esiste per
--    non far tenere in ostaggio un lotto intero da un documento solo.
--
-- ⚠️ TUTTI I CASI SONO COSTRUITI, anche i due lotti (rev 2026-10-27, lotto 4
--   di D7: prima tipo documento ed emittente si leggevano dall'ultimo lotto
--   del DB).
--
-- ⛔ QUELLO CHE QUESTO FILE NON PROVA, E VA DETTO: il TRASCINAMENTO positivo —
--   escludere un documento la cui bozza copre anche altri, e vedere gli altri
--   tornare a PENDING. Richiede fatture, righe, attivita' fatturabili e
--   commesse: una fixture piu' grande della cosa da provare. Il test 16 copre
--   il verso costruibile (senza bozza non si trascina nessuno); il verso
--   positivo e' stato collaudato sul database vero in transazione annullata
--   (brief §9-bis) ed e' un debito dichiarato.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(22);

-- ============================================================
-- Fixture: un lotto con tre documenti — uno rotto, uno sano, uno gia' fuori
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): i due lotti si COSTRUISCONO
--   (dbops.fn_pgtap_crea_lotto, azienda di chi agisce, stato raggiunto per la
--   matrice). Prima si scrivevano a mano con tipo documento ed emittente
--   pescati dall'ultimo lotto del DB: da zero non c'era, e fuori dal
--   perimetro la RLS rifiutava gruppi ed esiti qui sotto.
-- ⚠️ LO STATO SERVE: la check legge `congela_fiscale` FAIL-CLOSED
--   (COALESCE(..., true)), quindi un lotto senza stato risulta «oltre il
--   pre-fiscale» e blocca TUTTO. ⛔ `codice_interno`, mai un id.
CREATE TEMP TABLE tmp_lotto AS
SELECT l.lotto_id AS id FROM dbops.fn_pgtap_crea_lotto('uscita giro', 'DRAFT') l;

-- ⭐ UN SECONDO LOTTO, OLTRE IL PRE-FISCALE, per il test 18. Serve perche'
--   il MOTIVO 1 (E_LOTTO_NON_PRE_FISCALE) non scatta mai sul lotto DRAFT
--   qui sopra — ed e' proprio il motivo su cui la frase era sbagliata.
--   ⛔ `codice_interno`, mai un id: DEFINITIVA e' uno degli stati con
--   `congela_fiscale = true`, e il confine si legge dal flag.
CREATE TEMP TABLE tmp_lotto_fiscale AS
SELECT l.lotto_id AS id FROM dbops.fn_pgtap_crea_lotto('uscita giro fiscale', 'DEFINITIVA') l;

DO $fixture$
DECLARE
    v_lotto          vendite.fatturazione_lotti.id%TYPE := (SELECT id FROM tmp_lotto);
BEGIN

    -- Il perimetro: tre documenti presi in carico.
    INSERT INTO vendite.fatturazione_lotti_gruppi (lotto_id, gruppo_key)
    VALUES (v_lotto, 'PGTAP:rotto'), (v_lotto, 'PGTAP:sano'), (v_lotto, 'PGTAP:terzo');

    -- Gli esiti: uno fallito, uno riuscito, uno riuscito.
    INSERT INTO vendite.fatturazione_lotti_esiti
        (lotto_id, gruppo_key, stato_esecuzione, errore_codice, errore_messaggio)
    VALUES (v_lotto, 'PGTAP:rotto', 'ERRORE', 'E_PULL_COMMESSA', 'rotto per la prova'),
           (v_lotto, 'PGTAP:sano',  'COMPLETED', NULL, NULL),
           (v_lotto, 'PGTAP:terzo', 'COMPLETED', NULL, NULL);

    -- Due segnalazioni critiche: una DEL DOCUMENTO rotto, una DEL GIRO.
    INSERT INTO vendite.fatturazione_lotti_log (lotto_id, messaggio, status, gruppo_key)
    VALUES (v_lotto, 'Errore emissione del documento rotto', 'C', 'PGTAP:rotto'),
           (v_lotto, 'Emittente non risolto: e'' del giro',  'C', NULL);
END;
$fixture$;

-- ============================================================
-- 1..4 — la CHECK
-- ============================================================
SELECT is(
    script.fn_check_documento_escludibile_da_giro((SELECT id FROM tmp_lotto), 'PGTAP:rotto'),
    '[]'::jsonb,
    'un documento in ERRORE si puo'' togliere dal giro: nessun motivo'
);

SELECT is(
    script.fn_check_documento_escludibile_da_giro((SELECT id FROM tmp_lotto), 'PGTAP:sano')
        -> 0 ->> 'reason',
    'DOCUMENTO_NON_IN_ERRORE',
    'un documento SANO non si toglie: dal giro escono solo quelli falliti (D-4)'
);

SELECT is(
    script.fn_check_documento_escludibile_da_giro((SELECT id FROM tmp_lotto), 'PGTAP:mai-visto')
        -> 0 ->> 'reason',
    'SENZA_ESITO',
    'un documento che il lotto non ha lavorato non ha niente da togliere'
);

-- ============================================================
-- 5..8 — la MADRE, il caso felice
-- ============================================================
SELECT lives_ok(
    format($$SELECT vendite.fn_escludi_documento_da_giro(%s, 'PGTAP:rotto', 'esce per la prova')$$,
           (SELECT id FROM tmp_lotto)),
    'la madre toglie dal giro il documento rotto'
);

-- ⭐ PRECEDENZA: adesso che e' uscito, il motivo dev''essere UNO SOLO. Un
--   documento ESCLUSO e'' ANCHE «non in errore»: senza la precedenza dichiarata
--   scatterebbero due motivi e la madre solleverebbe quello sbagliato.
SELECT is(
    (SELECT jsonb_array_length(
        script.fn_check_documento_escludibile_da_giro((SELECT id FROM tmp_lotto), 'PGTAP:rotto'))
     || ':' ||
     (script.fn_check_documento_escludibile_da_giro((SELECT id FROM tmp_lotto), 'PGTAP:rotto')
      -> 0 ->> 'reason')),
    '1:GIA_USCITO',
    'un documento gia'' uscito da'' UN SOLO motivo, e il piu'' specifico'
);

SELECT is(
    (SELECT stato_esecuzione || '|' || uscita_motivo
       FROM vendite.fatturazione_lotti_esiti
      WHERE lotto_id = (SELECT id FROM tmp_lotto) AND gruppo_key = 'PGTAP:rotto'),
    'ESCLUSO|esce per la prova',
    'il documento risulta ESCLUSO col motivo che l''operatore ha scritto'
);

SELECT ok(
    (SELECT uscita_quando IS NOT NULL AND uscita_da IS NOT NULL
       FROM vendite.fatturazione_lotti_esiti
      WHERE lotto_id = (SELECT id FROM tmp_lotto) AND gruppo_key = 'PGTAP:rotto'),
    'il timbro dell''uscita lo scrive il database, non il chiamante'
);

-- ⭐ Non si cancella niente e non si mente: l'errore per cui e'' uscito resta.
SELECT is(
    (SELECT errore_codice FROM vendite.fatturazione_lotti_esiti
      WHERE lotto_id = (SELECT id FROM tmp_lotto) AND gruppo_key = 'PGTAP:rotto'),
    'E_PULL_COMMESSA',
    'l''errore originale RESTA sulla riga del documento uscito'
);

SELECT is(
    (SELECT count(*) FROM vendite.fatturazione_lotti_gruppi
      WHERE lotto_id = (SELECT id FROM tmp_lotto)),
    3::bigint,
    'il PERIMETRO non viene toccato: il lotto ricorda di averli presi tutti (D-1)'
);

-- ============================================================
-- 9..12 — i rifiuti
-- ============================================================
SELECT throws_ok(
    format($$UPDATE vendite.fatturazione_lotti_esiti SET stato_esecuzione = 'ERRORE'
              WHERE lotto_id = %s AND gruppo_key = 'PGTAP:rotto'$$,
           (SELECT id FROM tmp_lotto)),
    'P0001',
    NULL,
    'ESCLUSO e'' terminale: il documento uscito non rientra (D-3)'
);

SELECT lives_ok(
    format($$UPDATE vendite.fatturazione_lotti_esiti SET stato_esecuzione = 'ESCLUSO'
              WHERE lotto_id = %s AND gruppo_key = 'PGTAP:rotto'$$,
           (SELECT id FROM tmp_lotto)),
    'riassegnare lo STESSO valore non e'' un rientro e non si rifiuta'
);

SELECT throws_ok(
    format($$SELECT vendite.fn_escludi_documento_da_giro(%s, 'PGTAP:terzo', '   ')$$,
           (SELECT id FROM tmp_lotto)),
    'P0001',
    NULL,
    'un documento non esce senza motivo (D-5)'
);

SELECT throws_ok(
    format($$INSERT INTO vendite.fatturazione_lotti_esiti
                 (lotto_id, gruppo_key, stato_esecuzione, uscita_motivo)
             VALUES (%s, 'PGTAP:muto', 'ESCLUSO', '  ')$$,
           (SELECT id FROM tmp_lotto)),
    '23514',
    NULL,
    'il CHECK di tabella rifiuta anche un motivo fatto di soli spazi'
);

-- ============================================================
-- 13..15 — il CONTEGGIO, che e' la ragione per cui il verbo esiste
-- ============================================================
-- ⭐ Delle due critiche della fixture, quella del documento uscito non conta
--   piu'; quella del GIRO si': non ha un documento da togliere.
SELECT is(
    (SELECT lotto_critical_count
       FROM vendite.fn_get_lotto_segnalazioni_summary((SELECT id FROM tmp_lotto))),
    1::bigint,
    'la critica di un documento USCITO non ferma piu'' il giro'
);

SELECT is(
    (SELECT count(*) FROM vendite.fatturazione_lotti_log
      WHERE lotto_id = (SELECT id FROM tmp_lotto) AND status = 'C' AND gruppo_key IS NULL),
    1::bigint,
    'la critica del GIRO (gruppo_key NULL) resta, e resta quella che blocca'
);

-- ⭐ Non si e'' disabilitato niente: e'' il documento a non essere piu'' in gioco.
SELECT is(
    (SELECT count(*) FROM vendite.fatturazione_lotti_log
      WHERE lotto_id = (SELECT id FROM tmp_lotto) AND disabilitato IS TRUE),
    0::bigint,
    'nessuna segnalazione e'' stata ritirata: restano tutte leggibili'
);

-- ============================================================
-- 16 — il trascinamento, verso costruibile
-- ============================================================
SELECT is(
    script.fn_gruppi_trascinati_da_uscita((SELECT id FROM tmp_lotto), 'PGTAP:sano'),
    '[]'::jsonb,
    'un documento senza bozza non trascina nessuno'
);

-- ============================================================
-- 18) ⭐ P-1 — LA FRASE RESA, che nessun cancello statico vede
-- ============================================================
-- ⛔ IL DIFETTO ERA VIVO fino al 2026-09-09. vendite.fn_escludi_documento_da_giro
--   passava `p_gruppo_key` come PRIMO valore: giusto per i motivi 2, 3 e 4, che
--   cominciano tutti con «Il documento %s». Ma il MOTIVO 1 e'
--   E_LOTTO_NON_PRE_FISCALE — «Il lotto e' oltre lo stato pre-fiscale (stato
--   attuale: %s)» — e a video usciva il GRUPPO DEL DOCUMENTO al posto dello
--   stato del lotto. Ed e' il motivo che sta PRIMO nell'array, cioe' quello che
--   la madre solleva sul percorso piu' comune.
--   ⚠️ Arita' giusta (un segnaposto, un valore): nessun `W_MESSAGGIO_ARITA`,
--   nessun cancello rosso. I `throws_ok` dei test 9-12 asseriscono `P0001`, che
--   la frase non la guarda.
--
-- ⭐ Dal changeSet 20260909-02 i `valori` li emette la check accanto al proprio
--   codice, quindi ogni motivo porta i suoi. Questo test lo prova RENDENDO la
--   frase: e' l'unica verifica che vede l'ORDINE dei valori, che nessun
--   conteggio di segnaposto puo' vedere (il precedente e' del 2026-09-01 su
--   E_REGISTRO_SERIE_NON_AMMESSA).
-- ⚠️ Il CASE con `coalesce` non e' pignoleria: senza, una check che smettesse
--   di emettere `valori` farebbe alzare 22023 a format() e ABORTIREBBE il file,
--   seppellendo le altre diciassette asserzioni. E scritto con un `<>` nudo non
--   guarderebbe niente: `jsonb_typeof(NULL) <> 'array'` vale NULL, non vero.
SELECT matches(
  (WITH v AS (
     SELECT script.fn_check_documento_escludibile_da_giro(
              (SELECT id FROM tmp_lotto_fiscale), 'PGTAP:qualunque') -> 0 AS motivo)
   SELECT CASE
            WHEN coalesce(v.motivo ->> 'codice', '') <> 'E_LOTTO_NON_PRE_FISCALE'
              THEN format('(il primo motivo e'' %s)', v.motivo ->> 'codice')
            WHEN coalesce(jsonb_typeof(v.motivo -> 'valori'), 'assente') <> 'array'
              THEN '(la check non emette valori)'
            ELSE format(
                   (SELECT m.messaggio FROM config.messaggi_errore m
                     WHERE m.codice = 'E_LOTTO_NON_PRE_FISCALE' AND m.lingua = 'it'),
                   VARIADIC ARRAY(SELECT jsonb_array_elements_text(v.motivo -> 'valori')))
          END
     FROM v),
  'stato attuale: DEFINITIVA',
  '18) la frase resa nomina lo STATO DEL LOTTO, non il gruppo del documento'
);

-- ============================================================
-- 19-20) ⭐ LA GIUNTURA — uscita dal giro + marcatore
-- ============================================================
-- ⛔ IL DIFETTO ERA VIVO, e lo ha trovato un collaudo a video (BE, 2026-09-08):
--   tolto un documento dal giro e premuto «Rilancia step», il rilancio moriva
--   con E_PIPELINE 400. `fn_segna_esito_gruppo_lotto` marcava TUTTI i documenti
--   della commessa fallita, compreso quello uscito; il guard dell'uscita
--   rifiutava — correttamente, ESCLUSO e' terminale — e l'eccezione usciva dal
--   marcatore. ⇒ Il verbo che esiste per far ripartire un lotto lo rendeva
--   impossibile da rilanciare.
--
-- ⚠️ E IL DANNO NON ERA IL DOCUMENTO USCITO. Il guard e' BEFORE ROW e il
--   marcatore fa UN SOLO `INSERT ... ON CONFLICT DO UPDATE`: l'eccezione su una
--   riga saltava l'INTERO statement, quindi restavano senza esito anche i
--   documenti SANI della stessa commessa. E' il motivo per cui il test 20
--   esiste: da solo il 19 passerebbe anche su un rimedio che si limita a NON
--   sollevare smettendo di marcare tutto.
--
-- ⭐ PERCHE' NESSUN PRESIDIO LO VEDEVA, e non e' che «non poteva»: i pgTAP
--   provavano le due funzioni una per una, e il difetto nasce dalla SEQUENZA.
--   La fixture per provarla c'era gia' — questo file — e mancava solo la
--   chiamata. Un buco dichiarato inevitabile e' un buco che resta aperto.
--   Brief: brief-db-il-marcatore-scrive-su-un-documento-uscito.md
--   ChangeSet: 20260909-18-update-fn-segna-esito-gruppo-lotto-salta-usciti
SELECT lives_ok(
    format($$ SELECT * FROM vendite.fn_segna_esito_gruppo_lotto(
                       %s, 'ERRORE', 'PGTAP:rotto', NULL,
                       'E_PULL_COMMESSA', 'il pull fallisce ancora, come al collaudo') $$,
           (SELECT id FROM tmp_lotto)),
    '19) il marcatore non solleva su un documento gia'' uscito dal giro: lo salta'
);

-- ⚠️ Due cose in una asserzione, e vanno insieme: il documento SANO riceve
--   davvero il suo esito, e quello uscito resta ESCLUSO — cioe' il marcatore
--   non ha "risolto" smettendo di scrivere, e non ha nemmeno riscritto la riga
--   uscita col vecchio valore per farla passare.
-- ⚠️ IL VERBO IN UN'ISTRUZIONE SEPARATA, e non e' stile: dentro una sola
--   espressione l'ordine di valutazione degli operandi NON e' garantito, e le
--   letture di stato possono precedere la scrittura. Scritta tutta insieme,
--   questa asserzione leggeva 'COMPLETED' su una riga che la chiamata accanto
--   stava marcando 'ERRORE' — un rosso che non dipendeva dal codice sotto
--   esame.
CREATE TEMP TABLE tmp_marcati_sano AS
SELECT * FROM vendite.fn_segna_esito_gruppo_lotto(
         (SELECT id FROM tmp_lotto), 'ERRORE', 'PGTAP:sano', NULL,
         'E_PULL_COMMESSA', 'il pull fallisce ancora');

SELECT is(
    (SELECT marcati::text FROM tmp_marcati_sano)
     || '|' ||
     (SELECT e.stato_esecuzione FROM vendite.fatturazione_lotti_esiti e
       WHERE e.lotto_id = (SELECT id FROM tmp_lotto) AND e.gruppo_key = 'PGTAP:rotto')
     || '|' ||
     (SELECT e.stato_esecuzione FROM vendite.fatturazione_lotti_esiti e
       WHERE e.lotto_id = (SELECT id FROM tmp_lotto) AND e.gruppo_key = 'PGTAP:sano'),
    '1|ESCLUSO|ERRORE',
    '20) il documento sano viene marcato, quello uscito resta ESCLUSO'
);

-- ============================================================
-- 21) ⭐ L'USCITA COMPARE NEL GIORNALE, COL SUO MOTIVO
-- ============================================================
-- ⛔ Fino al 2026-09-09 non c'era nessuna riga: il timbro stava solo sulla riga
--   dell'esito (uscita_motivo/quando/da), quindi chi guardava la STORIA del
--   lotto non vedeva che un documento era uscito ne' perche'. Un fatto voluto,
--   con una motivazione che il CHECK di tabella rende obbligatoria, che il
--   giornale non registrava.
-- ⚠️ Si verificano tre cose insieme perche' separate non dicono niente: che la
--   riga ci sia, che sia `I` (un fatto, non un allarme: non deve contare fra le
--   critiche) e che porti la `gruppo_key` — senza, sarebbe «del giro» e nessuno
--   saprebbe di chi parla ne' potrebbe toglierla.
-- ⚠️ E il MOTIVO si cerca nel messaggio, non in `meta`: chi legge il giornale
--   legge il messaggio.
SELECT is(
    (SELECT g.status || '|' || g.gruppo_key || '|' ||
            CASE WHEN g.messaggio LIKE '%esce per la prova%' THEN 'col motivo'
                 ELSE 'SENZA motivo: ' || g.messaggio END
       FROM vendite.fatturazione_lotti_log g
      WHERE g.lotto_id = (SELECT id FROM tmp_lotto)
        AND g.fase = 'USCITA_DAL_GIRO'),
    'I|PGTAP:rotto|col motivo',
    '21) l''uscita lascia nel giornale una informativa col documento e il motivo'
);

-- ============================================================
-- 22) ⭐ UNA CRITICA SU UN DOCUMENTO USCITO NON SI SCRIVE — UNA `I` SI'
-- ============================================================
-- ⛔ Al rilancio il pull di una commessa fallita fallisce ancora, e il backend
--   riscriveva una critica per OGNI suo documento, compreso quello uscito. Non
--   bloccava — il conteggio le scarta gia' — ma se ne accumulava una a ogni
--   giro su un documento che non e' piu' in gioco.
-- ⭐ Le due meta' vanno insieme: da sola la prima passerebbe anche su una
--   regola che ha smesso di scrivere QUALUNQUE cosa sul documento uscito — e
--   allora sparirebbe anche la riga del test 21.
-- ⚠️ Le scritture stanno in istruzioni SEPARATE dalla lettura: dentro una sola
--   espressione l'ordine di valutazione non e' garantito.
SELECT vendite.fn_log_pipeline_fase(
    (SELECT id FROM tmp_lotto),
    (SELECT l.stato_doc_fiscale_id FROM vendite.fatturazione_lotti l
      WHERE l.id = (SELECT id FROM tmp_lotto)),
    'PGTAP_PROVA', 'C'::char, 'critica su un documento uscito',
    '{}'::jsonb, NULL, 'PGTAP:rotto');

SELECT vendite.fn_log_pipeline_fase(
    (SELECT id FROM tmp_lotto),
    (SELECT l.stato_doc_fiscale_id FROM vendite.fatturazione_lotti l
      WHERE l.id = (SELECT id FROM tmp_lotto)),
    'PGTAP_PROVA', 'I'::char, 'informativa su un documento uscito',
    '{}'::jsonb, NULL, 'PGTAP:rotto');

SELECT is(
    (SELECT coalesce(string_agg(g.status::text, ',' ORDER BY g.status), '(nessuna)')
       FROM vendite.fatturazione_lotti_log g
      WHERE g.lotto_id = (SELECT id FROM tmp_lotto)
        AND g.fase = 'PGTAP_PROVA'),
    'I',
    '22) sul documento uscito la critica non si scrive, l''informativa si'''
);

SELECT * FROM finish();
ROLLBACK;
