-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
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
--
-- Scopo:
--  - presidiare il verbo «togli un documento rotto dal giro», che esiste per
--    non far tenere in ostaggio un lotto intero da un documento solo.
--
-- ⚠️ TUTTI I CASI SONO COSTRUITI. L'unica cosa presa dai dati sono i due
--   riferimenti obbligatori del lotto (tipo documento ed emittente), letti da
--   un lotto esistente perche' devono stare nel perimetro dell'operatore.
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

SELECT plan(18);

-- ============================================================
-- Fixture: un lotto con tre documenti — uno rotto, uno sano, uno gia' fuori
-- ============================================================
CREATE TEMP TABLE tmp_rif AS
SELECT l.tipo_doc_fiscale_id, l.emittente_soggetto_ruolo_id
  FROM vendite.fatturazione_lotti l
 ORDER BY l.id DESC
 LIMIT 1;

CREATE TEMP TABLE tmp_lotto (id bigint);
CREATE TEMP TABLE tmp_lotto_fiscale (id bigint);

DO $fixture$
DECLARE
    v_lotto          vendite.fatturazione_lotti.id%TYPE;
    v_lotto_fiscale  vendite.fatturazione_lotti.id%TYPE;
BEGIN
    -- ⚠️ LO STATO SERVE, e la prima stesura di questa fixture non lo metteva:
    --   la check legge `congela_fiscale` FAIL-CLOSED (COALESCE(..., true)),
    --   quindi un lotto senza stato risulta «oltre il pre-fiscale» e blocca
    --   TUTTO. E' il comportamento voluto — non sapere in che stato e' il giro
    --   non e' un buon motivo per lasciarci mettere le mani — ma rende il lotto
    --   inutilizzabile come fixture. ⛔ `codice_interno`, mai un id.
    INSERT INTO vendite.fatturazione_lotti
        (codice, competenza_mese, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id,
         stato_doc_fiscale_id)
    SELECT 'PGTAP-USCITA-GIRO', date_trunc('month', CURRENT_DATE)::date,
           t.tipo_doc_fiscale_id, t.emittente_soggetto_ruolo_id,
           (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno = 'DRAFT')
      FROM tmp_rif t
    RETURNING id INTO v_lotto;

    INSERT INTO tmp_lotto VALUES (v_lotto);

    -- ⭐ UN SECONDO LOTTO, OLTRE IL PRE-FISCALE, per il test 18. Serve perche'
    --   il MOTIVO 1 (E_LOTTO_NON_PRE_FISCALE) non scatta mai sul lotto DRAFT
    --   qui sopra — ed e' proprio il motivo su cui la frase era sbagliata.
    --   ⛔ `codice_interno`, mai un id: DEFINITIVA e' uno degli stati con
    --   `congela_fiscale = true`, e il confine si legge dal flag.
    INSERT INTO vendite.fatturazione_lotti
        (codice, competenza_mese, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id,
         stato_doc_fiscale_id)
    SELECT 'PGTAP-USCITA-GIRO-FISCALE', date_trunc('month', CURRENT_DATE)::date,
           t.tipo_doc_fiscale_id, t.emittente_soggetto_ruolo_id,
           (SELECT s.id FROM config.stati_doc_fiscale s
             WHERE s.codice_interno = 'DEFINITIVA')
      FROM tmp_rif t
    RETURNING id INTO v_lotto_fiscale;

    INSERT INTO tmp_lotto_fiscale VALUES (v_lotto_fiscale);

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

SELECT * FROM finish();
ROLLBACK;
