-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: i due pezzi che mancavano al contratto §6.1 — chi SCRIVE una
--       segnalazione puo' dire di quale documento parla, e la conversione
--       «questa commessa quali documenti alimenta» e' chiamabile da fuori.
-- ChangeSet: 20260908-18 (la funzione estratta), -19 (la madre la chiama),
--            -20 (il canale del log accetta il proprietario)
-- ⭐ REV 2026-09-09, due adeguamenti e vengono da due changeSet diversi:
--   · il test 7 legge TRE conteggi e non un intero — dal 20260909-20
--     `fn_segna_esito_gruppo_lotto` e' una `RETURNS TABLE`;
--   · la fixture fa USCIRE il documento DOPO avergli scritto la critica — dal
--     20260909-21 `fn_log_pipeline_fase` rifiuta `W` e `C` su un documento gia'
--     uscito, quindi nato ESCLUSO la riga dei test 11-12 non nascerebbe e i due
--     sarebbero verdi per sottrazione.
--   ⚠️ Il secondo si vedeva SOLO dopo aver riparato il primo: l'errore di firma
--   sul test 7 abortiva il file e i test 8-15 non giravano affatto.
--
-- Elenco test (plan 15):
--   1) la firma che il backend chiamera' esiste, ed e' quella dichiarata
--   2) ⭐ la madre NON contiene piu' la catena (linee-guida-sql §12.5.2)
--   3) ⭐ ...e chiama la funzione estratta
--   4) una commessa che in quel lotto non alimenta niente da' []
--   5) la funzione estratta SOLLEVA su un lotto non valido
--   6) ...e su una commessa non valida
--   7) ⛔ la madre invece NON solleva: torna 0, perche' il guard sta a monte
--   8) fn_log_pipeline_fase scrive la gruppo_key nella COLONNA
--   9) la chiamata POSIZIONALE a sei argomenti continua a funzionare
--  10) una gruppo_key di soli spazi diventa NULL, non un terzo stato
--  11) ⭐ la critica di un documento ESCLUSO non ferma piu' il giro...
--  12) ...e quella del GIRO (gruppo_key NULL) continua a fermarlo
--  13) ⭐ il presidio si accende: una gruppo_key che il lotto non ha
--  14) il verso POSITIVO: senza perimetro si prendono tutti i documenti...
--  15) ...e col perimetro solo quelli che il lotto sta lavorando
--
-- Scopo:
--   Fino al 2026-09-08 il verbo «togli questo documento dal giro» esisteva,
--   funzionava, e sulla corsia del PULL non sbloccava niente: l'unica
--   segnalazione che bloccava nasceva con `gruppo_key` NULL — «e' del giro» —
--   perche' nessuno aveva dove dichiarare il proprietario. Questi tre changeSet
--   chiudono il canale (il parametro) e la conoscenza (la conversione dalla
--   commessa), che sono le due cose che mancavano.
--
-- ⚠️ I CASI SONO TUTTI COSTRUITI, anche il 14-15.
-- rev 2026-10-27 (lotto 4 di D7): i due lotti nascono da
--   dbops.fn_pgtap_crea_lotto (prima: tipo documento ed emittente letti
--   dall'ultimo lotto del DB) e la commessa 1:N dei test 14-15 si costruisce
--   con due preventivi veri come sorgenti (prima: pescata, e da zero i due
--   test saltavano — il debito dichiarato qui fino a oggi).
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(15);

-- ============================================================
-- Fixture: un lotto con due documenti — uno gia' USCITO, uno ancora in gioco
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): il lotto si COSTRUISCE con
--   dbops.fn_pgtap_crea_lotto (madre vera, azienda di chi agisce, stato DRAFT
--   per codice_interno). Prima si scriveva a mano coi riferimenti dell'ultimo
--   lotto del DB: da zero non c'era, e un lotto senza perimetro dell'operatore
--   faceva rifiutare dalla RLS le righe di fatturazione_lotti_gruppi.
-- ⚠️ Lo stato serve: la check dell'uscita legge `congela_fiscale`
--   FAIL-CLOSED, e un lotto senza stato risulta oltre il pre-fiscale. Il
--   builder lo porta nato in DRAFT.
CREATE TEMP TABLE tmp_lotto_gk AS
SELECT * FROM dbops.fn_pgtap_crea_lotto('gruppo key segnalazioni');

CREATE TEMP TABLE tmp_lotto (id bigint);

DO $fixture$
DECLARE
    v_lotto vendite.fatturazione_lotti.id%TYPE;
BEGIN
    SELECT g.lotto_id INTO v_lotto FROM tmp_lotto_gk g;

    INSERT INTO tmp_lotto VALUES (v_lotto);

    -- Il perimetro: due documenti presi in carico.
    INSERT INTO vendite.fatturazione_lotti_gruppi (lotto_id, gruppo_key)
    VALUES (v_lotto, 'PGTAP:GK:uscito'), (v_lotto, 'PGTAP:GK:vivo');

    -- Gli esiti: due documenti rotti dentro il giro.
    -- ⭐ REV 2026-09-09 — IL PRIMO NASCE ANCORA IN `ERRORE`, E L'ORDINE E' IL
    --   PUNTO. Dal changeSet 20260909-21 `fn_log_pipeline_fase` RIFIUTA di
    --   scrivere `W` e `C` su un documento gia' uscito dal giro: nato ESCLUSO,
    --   la critica del test 11 non si scriverebbe piu' e i test 11-12
    --   proverebbero il conteggio su una riga che non esiste — verdi per
    --   sottrazione, cioe' verdi anche se il filtro del conteggio sparisse.
    -- ⇒ Il documento esce DOPO che la sua critica e' stata scritta (blocco
    --   $uscita$ piu' sotto), che e' esattamente il modo in cui il pregresso e'
    --   venuto al mondo: il rubinetto e' chiuso da oggi, le righe di ieri sono
    --   li'. Il conteggio deve continuare a scartarle, ed e' cio' che l'11
    --   verifica.
    INSERT INTO vendite.fatturazione_lotti_esiti
        (lotto_id, gruppo_key, stato_esecuzione, errore_codice, errore_messaggio)
    VALUES (v_lotto, 'PGTAP:GK:uscito', 'ERRORE', 'E_PULL_COMMESSA',
            'rotto per la prova'),
           (v_lotto, 'PGTAP:GK:vivo', 'ERRORE', 'E_PULL_COMMESSA',
            'ancora rotto');
END;
$fixture$;

-- ============================================================
-- 1 — la firma che il backend chiamera'
-- ============================================================
-- ⚠️ Non e' burocrazia: il backend la invoca per NOME e ARITA' da
--   `_PullCommesseRunLogger.item_failed`. Una firma diversa non fallisce qui,
--   fallisce la' — dentro un gestore d'eccezione, cioe' dove il guasto vero
--   verrebbe coperto dal nostro.
SELECT has_function(
    'script', 'fn_gruppi_di_commessa_nel_lotto', ARRAY['bigint', 'bigint'],
    '1) la funzione che il backend chiamera'' esiste con la firma dichiarata'
);

-- ============================================================
-- 2..3 — ⭐ LA SEDE E' UNA SOLA (linee-guida-sql §12.5.2)
-- ============================================================
-- Il presidio da scrivere non e' «gli esiti coincidono» — quello proverebbe
-- che oggi combaciano — ma «la madre non contiene piu' il predicato», che
-- prova che non possono divergere.
-- ⚠️ Si tolgono i COMMENTI prima di cercare: il corpo della madre spiega la
--   trappola citando `commesse_attivita`, e un presidio che legge `prosrc`
--   grezzo accusa chi documenta il difetto invece di chi lo commette.
SELECT ok(
    (SELECT regexp_replace(p.prosrc, '--[^' || chr(10) || ']*', '', 'g')
                NOT LIKE '%commesse_attivita%'
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite'
        AND p.proname = 'fn_segna_esito_gruppo_lotto'),
    '2) la madre non contiene piu'' la catena commessa -> commesse_attivita'
);

SELECT ok(
    (SELECT p.prosrc LIKE '%fn_gruppi_di_commessa_nel_lotto%'
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite'
        AND p.proname = 'fn_segna_esito_gruppo_lotto'),
    '3) ...e chiama la funzione dove quella catena vive adesso'
);

-- ============================================================
-- 4 — una commessa che in questo lotto non alimenta niente
-- ============================================================
-- ⭐ `[]` e' una RISPOSTA e va letta: «questo fallimento non ha un proprietario
--   dentro questo lotto» ⇒ chi scrive la segnalazione ne mette una a
--   `gruppo_key` NULL, che vuol dire «e' del giro» e blocca. ⛔ Non zero righe.
SELECT is(
    script.fn_gruppi_di_commessa_nel_lotto((SELECT id FROM tmp_lotto), 2147483647),
    '[]'::jsonb,
    '4) una commessa che in quel lotto non alimenta niente da'' []'
);

-- ============================================================
-- 5..6 — fail-loud sui parametri
-- ============================================================
-- La chiama anche il backend, direttamente: li' un id <= 0 e' un CHIAMANTE
-- ROTTO, non una condizione di dominio. ⛔ Un [] silenzioso sarebbe
-- indistinguibile da «nessun documento», che ha la conseguenza opposta.
SELECT throws_ok(
    $$SELECT script.fn_gruppi_di_commessa_nel_lotto(0, 1)$$,
    'P0001',
    NULL,
    '5) un lotto non valido non da'' [], solleva'
);

SELECT throws_ok(
    format($$SELECT script.fn_gruppi_di_commessa_nel_lotto(%s, -1)$$,
           (SELECT id FROM tmp_lotto)),
    'P0001',
    NULL,
    '6) una commessa non valida non da'' [], solleva'
);

-- ============================================================
-- 7 — ⛔ ...ma la MADRE non solleva mai, e il guard sta a monte
-- ============================================================
-- La chiama un gestore d'eccezione: un errore su di se' coprirebbe quello
-- vero. Le due promesse convivono solo perche' il guard precede la chiamata.
--
-- ⭐ REV 2026-09-09 — dal changeSet 20260909-20 la madre torna
--   `(marcati, usciti, fuori_perimetro)` e i guard di parametro rendono
--   `0, 0, 0`. Si leggono tutti e tre: qui il rifiuto arriva dal GUARD, e
--   `0|0|0` lo distingue da «i documenti c'erano ma sono usciti» (`0|N|0`) o
--   «erano fuori dal perimetro» (`0|0|N`) — che e' la ragione per cui quel
--   changeSet ha smesso di rispondere con un numero solo.
-- ⚠️ `SELECT ... FROM fn(...)`: su una `RETURNS TABLE` la forma `fn(...)` in
--   lista di select consegna la tupla intera in un campo solo, cioe' un valore
--   plausibile e falso.
SELECT is(
    (SELECT format('%s|%s|%s', marcati, usciti, fuori_perimetro)
       FROM vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id         => (SELECT id FROM tmp_lotto),
        p_stato            => 'ERRORE',
        p_commessa_id      => -1,
        p_errore_codice    => 'E_PULL_COMMESSA',
        p_errore_messaggio => 'commessa non valida')),
    '0|0|0',
    '7) la madre non solleva su una commessa non valida: torna 0'
);

-- ============================================================
-- 8..10 — il CANALE: fn_log_pipeline_fase dichiara il proprietario
-- ============================================================
-- ⚠️ Righe di livello `I`: qui si prova il canale, non il conteggio. Le
--   critiche arrivano ai test 11-12 e non vanno mescolate.
DO $canale$
BEGIN
    -- Il proprietario dichiarato.
    PERFORM vendite.fn_log_pipeline_fase(
        (SELECT id FROM tmp_lotto), NULL, 'PGTAP-GK-con-proprietario', 'I',
        'segnalazione di un documento', '{}'::jsonb, NULL, 'PGTAP:GK:vivo');

    -- ⭐ La chiamata POSIZIONALE a SEI argomenti, che e' quella del backend
    --   (apps/vendite/db/pipeline_repository.py): il parametro nuovo e' in
    --   coda apposta perche' questa continui a funzionare identica.
    PERFORM vendite.fn_log_pipeline_fase(
        (SELECT id FROM tmp_lotto), NULL, 'PGTAP-GK-sei-argomenti', 'I',
        'la chiamata di prima', '{}'::jsonb);

    -- Una chiave fatta di soli spazi: assenza, non un terzo stato.
    PERFORM vendite.fn_log_pipeline_fase(
        (SELECT id FROM tmp_lotto), NULL, 'PGTAP-GK-vuota', 'I',
        'proprietario dichiarato male', '{}'::jsonb, NULL, '   ');
END;
$canale$;

SELECT is(
    (SELECT ll.gruppo_key FROM vendite.fatturazione_lotti_log ll
      WHERE ll.lotto_id = (SELECT id FROM tmp_lotto)
        AND ll.fase = 'PGTAP-GK-con-proprietario'),
    'PGTAP:GK:vivo',
    '8) il proprietario finisce nella COLONNA, non dentro meta'
);

SELECT ok(
    (SELECT ll.gruppo_key IS NULL FROM vendite.fatturazione_lotti_log ll
      WHERE ll.lotto_id = (SELECT id FROM tmp_lotto)
        AND ll.fase = 'PGTAP-GK-sei-argomenti'),
    '9) la chiamata a sei argomenti scrive ancora, e lascia la riga «del giro»'
);

-- ⚠️ NULL e non '': la colonna ha DUE stati, e un terzo passerebbe per «nomina
--   un documento» — lasciando una riga che blocca il lotto per sempre e che
--   nessuno puo' togliere, perche' non c'e' nessun documento da togliere.
SELECT ok(
    (SELECT ll.gruppo_key IS NULL FROM vendite.fatturazione_lotti_log ll
      WHERE ll.lotto_id = (SELECT id FROM tmp_lotto)
        AND ll.fase = 'PGTAP-GK-vuota'),
    '10) una gruppo_key di soli spazi diventa NULL, non una stringa vuota'
);

-- ============================================================
-- 11..12 — ⭐ LA CATENA INTERA, che e' la ragione dei tre changeSet
-- ============================================================
-- Due critiche scritte DAL CANALE VERO: una del documento che poi uscira', una
-- del giro. Il conteggio deve vedere solo la seconda.
DO $critiche$
BEGIN
    PERFORM vendite.fn_log_pipeline_fase(
        (SELECT id FROM tmp_lotto), NULL, 'PGTAP-GK-critica-uscito', 'C',
        'Errore emissione del documento uscito', '{}'::jsonb,
        'E_PULL_COMMESSA', 'PGTAP:GK:uscito');

    PERFORM vendite.fn_log_pipeline_fase(
        (SELECT id FROM tmp_lotto), NULL, 'PGTAP-GK-critica-giro', 'C',
        'Emittente non risolto: e'' del giro', '{}'::jsonb,
        'E_PULL_COMMESSA');
END;
$critiche$;

-- ⭐ E ADESSO il documento esce, con la sua critica gia' scritta: e' la
--   situazione che il conteggio deve saper leggere. ⛔ In un'istruzione a se',
--   dopo le critiche: invertire i due blocchi rimetterebbe i test 11-12 a
--   contare una riga che il rubinetto del -21 non lascia piu' nascere.
-- ⚠️ `uscita_quando` e `uscita_da` NON si scrivono: le deriva il trigger dalla
--   GUC. Il motivo si', perche' il CHECK di tabella lo pretende.
DO $uscita$
BEGIN
    UPDATE vendite.fatturazione_lotti_esiti
       SET stato_esecuzione = 'ESCLUSO',
           uscita_motivo    = 'uscito per la prova'
     WHERE lotto_id = (SELECT id FROM tmp_lotto)
       AND gruppo_key = 'PGTAP:GK:uscito';
END;
$uscita$;

SELECT is(
    (SELECT lotto_critical_count
       FROM vendite.fn_get_lotto_segnalazioni_summary((SELECT id FROM tmp_lotto))),
    1::bigint,
    '11) la critica di un documento USCITO non ferma piu'' il giro'
);

-- ⭐ E non e' stata ritirata: e' il suo documento a non essere piu' in gioco.
SELECT is(
    (SELECT count(*) FROM vendite.fatturazione_lotti_log ll
      WHERE ll.lotto_id = (SELECT id FROM tmp_lotto)
        AND ll.status = 'C'
        AND ll.disabilitato IS FALSE),
    2::bigint,
    '12) le due critiche restano LEGGIBILI: cambia chi conta, non chi c''e'''
);

-- ============================================================
-- 13 — ⭐ il presidio si accende
-- ============================================================
-- `vw_segnalazioni_con_documento_ignoto` era vuota per ASSENZA DI DATO: nessuno
-- valorizzava la colonna. Adesso e' raggiungibile, ed e' il momento di provare
-- che accusa il caso giusto — un proprietario dichiarato MALE, non uno assente.
DO $ignoto$
BEGIN
    PERFORM vendite.fn_log_pipeline_fase(
        (SELECT id FROM tmp_lotto), NULL, 'PGTAP-GK-ignoto', 'C',
        'nomina un documento che il lotto non ha', '{}'::jsonb,
        'E_PULL_COMMESSA', 'PGTAP:GK:mai-visto');
END;
$ignoto$;

SELECT is(
    (SELECT string_agg(v.gruppo_key, ',' ORDER BY v.gruppo_key)
       FROM vendite.vw_segnalazioni_con_documento_ignoto v
      WHERE v.lotto_id = (SELECT id FROM tmp_lotto)),
    'PGTAP:GK:mai-visto',
    '13) il presidio accusa il proprietario SBAGLIATO, non quello assente'
);

-- ============================================================
-- 14..15 — il verso POSITIVO: commessa -> documenti
-- ============================================================
-- Serve una commessa vera con almeno DUE documenti sorgente distinti: e' il
--   caso 1:N, quello che rende necessario l'array.
-- rev 2026-10-27 (lotto 4 di D7): la commessa 1:N si COSTRUISCE — commessa
--   (dbops.fn_pgtap_crea_commessa, sul cliente del lotto), due preventivi veri
--   (dbops.fn_pgtap_crea_preventivo: il guard della sorgente polimorfa
--   pretende che il documento esista) e un'attivita' per ciascuno
--   (dbops.fn_pgtap_crea_commessa_attivita). Prima era la prima commessa del
--   DB con due sorgenti: da zero non c'era, e i test 14-15 saltavano (il
--   debito dichiarato in testata). Le chiavi le calcola ancora la funzione del
--   dominio, dalla tabella: la forma della lettura e' invariata.
CREATE TEMP TABLE tmp_commessa_gk AS
SELECT * FROM dbops.fn_pgtap_crea_commessa(
                'gruppo key 1:N', NULL,
                (SELECT billing_account_id FROM tmp_lotto_gk));

CREATE TEMP TABLE tmp_preventivi_gk AS
SELECT g.n, pr.preventivo_uid
  FROM generate_series(1, 2) AS g(n)
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_preventivo('gruppo key 1:N ' || g.n) pr;

CREATE TEMP TABLE tmp_attivita_gk AS
SELECT a.attivita_id
  FROM tmp_preventivi_gk p
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_commessa_attivita(
                       p_commessa_id     => (SELECT commessa_id FROM tmp_commessa_gk),
                       p_sorgente_codice => 'PREVENTIVO',
                       p_sorgente_chiave => p.preventivo_uid::text) a;

CREATE TEMP TABLE tmp_commessa AS
SELECT ca.commessa_id,
       array_agg(DISTINCT vendite.fn_gruppo_fatturabile_key_di_attivita(ca.sorgente_tipo_id, ca.segment_key, ca.commessa_id)) AS chiavi
  FROM vendite.commesse_attivita ca
 WHERE ca.commessa_id = (SELECT commessa_id FROM tmp_commessa_gk)
 GROUP BY ca.commessa_id
HAVING count(DISTINCT vendite.fn_gruppo_fatturabile_key_di_attivita(ca.sorgente_tipo_id, ca.segment_key, ca.commessa_id)) >= 2;

-- Un secondo lotto SENZA perimetro: li' la commessa li alimenta tutti.
CREATE TEMP TABLE tmp_lotto_massa (id bigint);

-- rev 2026-10-27 (lotto 4 di D7): anche lui dal builder, sullo stesso
--   cliente del primo (prima: INSERT a mano coi riferimenti pescati).
INSERT INTO tmp_lotto_massa
SELECT l.lotto_id
  FROM dbops.fn_pgtap_crea_lotto('gruppo key massa', 'DRAFT',
                                 (SELECT billing_account_id FROM tmp_lotto_gk)) l;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_commessa)
    THEN skip('nessuna commessa con almeno due documenti sorgente visibile all''operatore: il caso 1:N non e'' costruibile qui', 2)
  ELSE is(
    script.fn_gruppi_di_commessa_nel_lotto(
        (SELECT id FROM tmp_lotto_massa), (SELECT commessa_id FROM tmp_commessa)),
    (SELECT jsonb_agg(k ORDER BY k)
       FROM (SELECT DISTINCT unnest(chiavi) AS k FROM tmp_commessa) s),
    '14) senza perimetro la commessa alimenta TUTTI i suoi documenti')
END;

-- Con il perimetro, solo cio' che il lotto sta lavorando: un documento fuori
-- non lo stava lavorando, e appendergli una segnalazione la renderebbe una
-- riga che nessuno potra' mai togliere.
DO $perimetro$
BEGIN
    IF EXISTS (SELECT 1 FROM tmp_commessa) THEN
        INSERT INTO vendite.fatturazione_lotti_gruppi (lotto_id, gruppo_key)
        SELECT (SELECT id FROM tmp_lotto_massa), c.chiavi[1]
          FROM tmp_commessa c;
    END IF;
END;
$perimetro$;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_commessa) THEN NULL
  ELSE is(
    script.fn_gruppi_di_commessa_nel_lotto(
        (SELECT id FROM tmp_lotto_massa), (SELECT commessa_id FROM tmp_commessa)),
    (SELECT jsonb_build_array(c.chiavi[1]) FROM tmp_commessa c),
    '15) col perimetro restano solo i documenti che il lotto sta lavorando')
END;

SELECT * FROM finish();
ROLLBACK;
