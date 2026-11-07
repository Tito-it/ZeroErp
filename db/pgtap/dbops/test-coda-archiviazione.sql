-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: archiviazione delle righe di coda — la bandiera che toglie una riga
--       dall'elenco SENZA toccarne lo stato.
--       (brief-db-archiviazione-righe-code, PARTE DB sezione 9;
--        changeset 20260904-01..04 + seed E_CODA_ARCHIVIAZIONE_NON_AMMESSA)
--
-- ⭐ LA PARTE CHE NON SI VEDE SONO I TEST 4-5-6, non i comportamentali.
--   Il brief chiede che le due code siano «simmetriche dal primo giorno, non
--   prima una poi l'altra», perche' «un'asimmetria si paga al primo che tocca
--   solo una delle due». Finche' quella frase resta prosa, la prima divergenza
--   passa: il primo che aggiungera' un vincolo su una sola delle due tabelle
--   non trovera' niente che glielo dica. I test 4, 5 e 6 confrontano le due
--   code — colonne, CHECK, trigger — e trasformano la promessa in
--   un'asserzione.
--
-- ⭐ E IL TEST 14 E' LA RAGIONE PER CUI QUESTO CANTIERE E' UN BRIEF.
--   Le due colonne da sole avrebbero passato ogni verifica lasciando aperto il
--   buco del requeue: una riga archiviata e poi rimessa in coda sarebbe VIVA e
--   INVISIBILE — nel conteggio del badge e fuori dall'elenco, senza nessun modo
--   di arrivarci per rimetterla a posto.
-- ------------------------------------------------------------
-- Indice test (1..18):
--   STRUTTURA E SIMMETRIA
--   1)  dbops.coda_lavori ha la colonna archiviato
--   2)  dbops.coda_lavori ha la colonna archiviato_il
--   3)  dbops.coda_lavori ha la colonna archiviato_da
--   4)  ⭐ le tre colonne sono IDENTICHE sulle due code (tipo, nullabilita', default)
--   5)  ⭐ i due CHECK hanno la STESSA definizione sulle due code
--   6)  ⭐ i due trigger hanno la STESSA definizione e la STESSA funzione
--   7)  il codice errore e' a catalogo con classe CONFLITTO_STATO
--   8)  il messaggio ha ESATTAMENTE un segnaposto
--   COMPORTAMENTO — coda lavori
--   9)  archiviare una riga VIVA -> errore di dominio (P0001)
--  10)  ... e la frase nomina lo STATO, non la colonna
--  11)  archiviare una riga TERMINALE -> passa
--  12)  i due timbri li deriva il database, non il chiamante
--  13)  i due timbri sono IMMUTABILI finche' la riga resta archiviata
--  14)  ⭐ REQUEUE: la riga torna viva -> bandiera e timbri si azzerano
--  15)  INSERT archiviata-e-viva -> lo prende il CHECK (23514)
--  16)  INSERT archiviata senza timbri -> lo prende il CHECK (23514)
--   COMPORTAMENTO — coda stampa
--  17)  archiviare una riga VIVA -> errore di dominio (P0001)
--  18)  archiviare una riga TERMINALE -> passa
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il test gira come gira l'applicazione (ruolo OPERATORE
-- + RLS attiva), non come owner. Serve alla fixture della coda stampa, che
-- dopo il 20260904-06 e' sotto policy.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- Vincoli differiti: senza questa riga smetterebbero di essere verificati (il
-- file si chiude in ROLLBACK, il COMMIT non arriva mai).
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

-- ============================================================
-- Fixture
-- ============================================================
-- ⚠️ 2026-09-04: `dbops.coda_lavori_tipi.processo_codice` e' NOT NULL — ogni
--   tipo di coda dichiara di quale PROCESSO e', e da li' il guard di classe in
--   dbops.fn_accoda_lavoro legge se il lavoro e' di dominio. Un tipo senza
--   processo non avrebbe una classe, quindi niente da controllare.
--   ⇒ La fixture si fabbrica il proprio processo invece di appoggiarsi a uno
--     del catalogo: MANUTENZIONE, cosi' il guard di classe non entra in gioco e
--     questo file continua a collaudare cio' che collaudava.
INSERT INTO dbops.processi (id, codice, descrizione, classe, canale, causa_fallimento)
VALUES (9701, 'PGTAP_PROC_ARCHIVIAZIONE', 'processo di prova per test-coda-archiviazione', 'MANUTENZIONE', 'CODA', 'PROGRAMMA');

INSERT INTO dbops.coda_lavori_tipi
  (codice, handler_code, run_as_default, attivo, processo_codice)
VALUES ('PGTAP_ARCHIVIAZIONE', 'pgtap.archiviazione', 'SISTEMA', true,
        'PGTAP_PROC_ARCHIVIAZIONE');

-- ⭐ Rev 2026-11-07 (blocco 5b di brief-db-revisione-dbops): la coda lavori e'
--   sotto RLS, e un lavoro SISTEMA lo scrivono solo super admin e drenatore.
--   L'operatore di questo file scrive un lavoro OPERATORE della sua azienda
--   (dbops.fn_pgtap_scope_operatore): l'archiviazione non dipende dal run_as.
INSERT INTO dbops.coda_lavori (job_type, run_as, scope, emittente_fiscale_id, origine)
SELECT 'PGTAP_ARCHIVIAZIONE', 'OPERATORE', s.scope,
       (s.scope ->> 'emittente_attivo_id')::bigint, 'API'
  FROM (SELECT dbops.fn_pgtap_scope_operatore() AS scope) s;

CREATE TEMP TABLE _job AS
SELECT id FROM dbops.coda_lavori WHERE job_type = 'PGTAP_ARCHIVIAZIONE';

-- ⚠️ La fattura si sceglie NEL PERIMETRO dell'operatore e SENZA work-item vivo:
--   fuori perimetro la policy del 20260904-05 negherebbe la WITH CHECK, e con
--   un work-item vivo l'indice unico parziale rifiuterebbe l'INSERT — due rossi
--   che non c'entrano niente con cio' che si sta verificando.
-- ⚠️ ORDER BY esplicito: senza, quale fattura esca dipende dal piano, e il
--   test passerebbe a giorni alterni.
CREATE TEMP TABLE _fat AS
SELECT f.id AS fattura_id,
       (SELECT s.id FROM config.sorgenti s
         WHERE s.codice_interno = 'FATTURA') AS tipo_id
  FROM vendite.fatture f
 WHERE f.emittente_soggetto_ruolo_id = script.fn_pgtap_emittente_sr_operatore()
   AND NOT EXISTS (SELECT 1 FROM vendite.fatture_stampa_coda c
                    WHERE c.sorgente_id = f.id
                      AND c.stato IN ('PENDING', 'IN_CORSO'))
 ORDER BY f.id
 LIMIT 1;

-- ============================================================
-- 1-3) Le colonne ci sono
-- ============================================================
SELECT has_column('dbops', 'coda_lavori', 'archiviato',
    '1) coda lavori: colonna archiviato');
SELECT has_column('dbops', 'coda_lavori', 'archiviato_il',
    '2) coda lavori: colonna archiviato_il');
SELECT has_column('dbops', 'coda_lavori', 'archiviato_da',
    '3) coda lavori: colonna archiviato_da');

-- ============================================================
-- 4-6) ⭐ SIMMETRIA — il presidio che rende vera la promessa del brief
-- ============================================================
-- Differenza SIMMETRICA e non un EXCEPT solo: un EXCEPT in una direzione
-- passerebbe anche se una delle due tabelle avesse una colonna IN PIU'.
SELECT is_empty($$
    WITH a AS (
        SELECT column_name, data_type, is_nullable, column_default
          FROM information_schema.columns
         WHERE table_schema = 'dbops' AND table_name = 'coda_lavori'
           AND column_name IN ('archiviato', 'archiviato_il', 'archiviato_da')
    ), b AS (
        SELECT column_name, data_type, is_nullable, column_default
          FROM information_schema.columns
         WHERE table_schema = 'vendite' AND table_name = 'fatture_stampa_coda'
           AND column_name IN ('archiviato', 'archiviato_il', 'archiviato_da')
    )
    SELECT * FROM ((SELECT * FROM a EXCEPT SELECT * FROM b)
                   UNION ALL
                   (SELECT * FROM b EXCEPT SELECT * FROM a)) d
$$, '4) le tre colonne dell''archiviazione sono identiche sulle due code');

-- ⚠️ Il confronto e' sulla DEFINIZIONE RESA da PostgreSQL, non sul testo che
--   abbiamo scritto: due espressioni scritte diverse ma equivalenti si
--   normalizzano uguali, e due scritte uguali su tabelle diverse restano
--   uguali perche' nessuna delle due nomina la propria tabella. E' proprio il
--   fatto che il predicato sia scritto in NEGATIVO («non viva») a renderlo
--   possibile: come elenco dei terminali sarebbe gia' diverso, perche' la coda
--   stampa non ha ANNULLATO.
SELECT is(
    (SELECT count(DISTINCT pg_get_constraintdef(c.oid))
       FROM pg_constraint c
      WHERE c.conname IN ('chk_coda_lavori_archiviato_non_vivo',
                          'chk_fatture_stampa_coda_archiviato_non_vivo',
                          'chk_coda_lavori_archiviato_coerente',
                          'chk_fatture_stampa_coda_archiviato_coerente')),
    2::bigint,
    '5) i quattro CHECK si riducono a DUE definizioni: le due code dicono la stessa cosa');

SELECT is(
    (SELECT count(DISTINCT regexp_replace(
                               regexp_replace(pg_get_triggerdef(t.oid),
                                              '^CREATE TRIGGER \S+ ', ''),
                               ' ON \S+ ', ' '))
       FROM pg_trigger t
      WHERE t.tgname IN ('trg_coda_lavori_a10_archiviazione_upd',
                         'trg_fatture_stampa_coda_a10_archiviazione_upd')),
    1::bigint,
    '6) i due trigger hanno la stessa definizione (eventi, colonne, WHEN, funzione)');

-- ============================================================
-- 7-8) Il codice errore e' registrato, e la frase e' formabile
-- ============================================================
SELECT is(
    (SELECT classe FROM config.codici_errore
      WHERE codice = 'E_CODA_ARCHIVIAZIONE_NON_AMMESSA'),
    'CONFLITTO_STATO',
    '7) il codice e'' a catalogo con la sua classe (409, non un dato da correggere)');

-- ⚠️ Un segnaposto in piu' o in meno fa CRASHARE format() dentro
--   fn_log_and_raise_error, e l'errore che si legge non e' piu' quello di
--   dominio: il guard sembra rotto mentre e' rotta la frase.
SELECT is(
    (SELECT array_length(string_to_array(messaggio, '%s'), 1)
       FROM config.messaggi_errore
      WHERE codice = 'E_CODA_ARCHIVIAZIONE_NON_AMMESSA' AND lingua = 'it'),
    2,
    '8) il messaggio ha esattamente un segnaposto, quanti sono i valori passati');

-- ============================================================
-- 9-10) Una riga VIVA non si archivia
-- ============================================================
SELECT throws_ok(
    $$ UPDATE dbops.coda_lavori SET archiviato = true
        WHERE id = (SELECT id FROM _job) $$,
    'P0001', NULL,
    '9) archiviare una riga PENDING solleva un errore di dominio');

-- ⚠️ throws_like e non throws_ok: P0001 dice «e' un errore di dominio», non
--   QUALE. Qui la posta in gioco e' proprio la frase — deve nominare lo STATO,
--   che e' cio' che la persona vede nella riga, e non il nome della colonna.
-- ⚠️ Il pattern non attraversa il segnaposto.
SELECT throws_like(
    $$ UPDATE dbops.coda_lavori SET archiviato = true
        WHERE id = (SELECT id FROM _job) $$,
    '%ancora in stato PENDING%',
    '10) la frase nomina lo STATO della riga, non la colonna');

-- ============================================================
-- 11-13) Una riga TERMINALE si archivia, e i timbri li mette il database
-- ============================================================
UPDATE dbops.coda_lavori SET stato = 'FATTO' WHERE id = (SELECT id FROM _job);
UPDATE dbops.coda_lavori SET archiviato = true WHERE id = (SELECT id FROM _job);

SELECT is(
    (SELECT archiviato FROM dbops.coda_lavori WHERE id = (SELECT id FROM _job)),
    true,
    '11) una riga terminale si archivia');

SELECT ok(
    (SELECT archiviato_il IS NOT NULL AND archiviato_da IS NOT NULL
       FROM dbops.coda_lavori WHERE id = (SELECT id FROM _job)),
    '12) i due timbri li deriva il trigger: il chiamante ha scritto solo la bandiera');

-- ⭐ L'immutabilita' non e' zelo: e' cio' che impedisce a una riga di dire una
--   cosa che la bandiera smentisce. Senza, il CHECK di coerenza resterebbe
--   soddisfatto (data non nulla, bandiera alzata) e la data sarebbe falsa.
UPDATE dbops.coda_lavori
   SET archiviato_il = '2001-01-01'::timestamptz,
       archiviato_da = 'falsario'
 WHERE id = (SELECT id FROM _job);

SELECT ok(
    (SELECT archiviato_da <> 'falsario' AND archiviato_il > '2020-01-01'::timestamptz
       FROM dbops.coda_lavori WHERE id = (SELECT id FROM _job)),
    '13) i timbri riscritti a mano vengono ripristinati: sono immutabili');

-- ============================================================
-- 14) ⭐ IL REQUEUE — il buco che le due colonne da sole lascerebbero aperto
-- ============================================================
-- CodaLavoriRepository.requeue riporta a PENDING da ERRORE e da IN_CORSO
-- stantio, e non tocca `archiviato`: senza il reset, la riga tornerebbe al
-- lavoro restando fuori dall'elenco.
UPDATE dbops.coda_lavori SET stato = 'PENDING' WHERE id = (SELECT id FROM _job);

SELECT ok(
    (SELECT NOT archiviato AND archiviato_il IS NULL AND archiviato_da IS NULL
       FROM dbops.coda_lavori WHERE id = (SELECT id FROM _job)),
    '14) una riga che torna viva riabbassa la bandiera e azzera i timbri');

-- ============================================================
-- 15-16) L'INSERT lo copre il CHECK, non il trigger
-- ============================================================
-- ⚠️ Il trigger e' un BEFORE UPDATE: su queste due righe non viene nemmeno
--   chiamato. E' esattamente il motivo per cui l'invariante ha anche un CHECK.
-- ⚠️ Righe che la policy ammette (OPERATORE, nell'azienda di chi scrive): con
--   la RLS accesa la WITH CHECK parla prima del CHECK, e una riga respinta da
--   lei darebbe 42501 senza mostrare il vincolo.
SELECT throws_ok(
    format($$ INSERT INTO dbops.coda_lavori
           (job_type, run_as, scope, emittente_fiscale_id, origine,
            archiviato, archiviato_il, archiviato_da)
       VALUES ('PGTAP_ARCHIVIAZIONE', 'OPERATORE', %L::jsonb, %s, 'API', true, now(), 'pgtap') $$,
       dbops.fn_pgtap_scope_operatore()::text,
       dbops.fn_pgtap_scope_operatore() ->> 'emittente_attivo_id'),
    '23514', NULL,
    '15) una riga non puo'' NASCERE archiviata-e-viva: lo ferma il CHECK');

SELECT throws_ok(
    format($$ INSERT INTO dbops.coda_lavori
           (job_type, run_as, scope, emittente_fiscale_id, origine, stato, archiviato)
       VALUES ('PGTAP_ARCHIVIAZIONE', 'OPERATORE', %L::jsonb, %s, 'API', 'FATTO', true) $$,
       dbops.fn_pgtap_scope_operatore()::text,
       dbops.fn_pgtap_scope_operatore() ->> 'emittente_attivo_id'),
    '23514', NULL,
    '16) una riga archiviata SENZA timbri non esiste: lo ferma il CHECK di coerenza');

-- ============================================================
-- 17-18) La coda stampa si comporta allo stesso modo
-- ============================================================
-- ⚠️ Data-dependent: senza una fattura nel perimetro dell'operatore la fixture
--   non si puo' costruire. Si dichiara con uno skip motivato invece di lasciare
--   due asserzioni che passano perche' non verificano niente.
DO $stampa$
DECLARE
    v_fattura_id bigint;
    v_tipo_id    bigint;
BEGIN
    SELECT fattura_id, tipo_id INTO v_fattura_id, v_tipo_id FROM _fat;
    IF v_fattura_id IS NULL OR v_tipo_id IS NULL THEN
        RETURN;
    END IF;
    INSERT INTO vendite.fatture_stampa_coda
        (sorgente_tipo_id, sorgente_id, sorgente_uid, stato)
    VALUES (v_tipo_id, v_fattura_id, v_fattura_id::text, 'PENDING');
END
$stampa$;

CREATE TEMP TABLE _coda AS
SELECT c.id
  FROM vendite.fatture_stampa_coda c
  JOIN _fat f ON f.fattura_id = c.sorgente_id
 WHERE c.stato = 'PENDING';

SELECT CASE WHEN (SELECT count(*) FROM _coda) = 0
    THEN skip('17) coda stampa: nessuna fattura nel perimetro dell''operatore su cui costruire la fixture', 1)
    ELSE throws_ok(
        $$ UPDATE vendite.fatture_stampa_coda SET archiviato = true
            WHERE id = (SELECT id FROM _coda) $$,
        'P0001', NULL,
        '17) coda stampa: archiviare una riga PENDING solleva lo stesso errore')
    END;

UPDATE vendite.fatture_stampa_coda SET stato = 'ERRORE'
 WHERE id IN (SELECT id FROM _coda);
UPDATE vendite.fatture_stampa_coda SET archiviato = true
 WHERE id IN (SELECT id FROM _coda);

SELECT CASE WHEN (SELECT count(*) FROM _coda) = 0
    THEN skip('18) coda stampa: fixture non costruibile (vedi 17)', 1)
    ELSE ok(
        (SELECT archiviato AND archiviato_il IS NOT NULL
           FROM vendite.fatture_stampa_coda WHERE id = (SELECT id FROM _coda)),
        '18) coda stampa: una riga terminale si archivia, coi timbri derivati')
    END;

SELECT * FROM finish();
ROLLBACK;
