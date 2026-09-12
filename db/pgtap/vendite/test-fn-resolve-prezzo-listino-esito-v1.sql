-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_resolve_prezzo_listino_v2_esito (NUCLEO puro del resolver
--   prezzi) e vendite.fn_resolve_prezzo_listino_v2 (GUSCIO che ne solleva
--   l'esito). Changeset 20260819-07 / 20260819-08.
--   Brief: brief-ddt-righe-senza-prezzo.md
--          §9 slice A (decisione D-3).
--
-- COSA PRESIDIA, in una riga: che le due funzioni siano lo STESSO corpo con
--   due contratti diversi. Se un domani qualcuno modificasse la risoluzione
--   nel guscio invece che nel nucleo, i test 3/4/5 diventerebbero rossi.
--
-- Elenco test (1..11):
--   1) (precondizione) la fixture ha trovato un contesto risolvibile
--   2) il nucleo esiste con la firma a 9 parametri
--   3) RISOLVE: nucleo e guscio danno lo STESSO prezzo_finale
--   4) RISOLVE: ...e la stessa origine e la stessa listino_riga_id
--   5) RISOLVE: esito_codice del nucleo e' NULL
--   6) NON RISOLVE: il nucleo ritorna ESATTAMENTE una riga (non zero)
--   7) NON RISOLVE: esito_codice valorizzato e prezzo_finale NULL
--   8) NON RISOLVE: il guscio sullo stesso input solleva P0001
--   9) NON RISOLVE: l'arita' regge — nessun segnaposto %s residuo nel messaggio
--  10) PARAMETRO INVALIDO: il nucleo solleva COMUNQUE (regola D-3)
--  11) ⭐ il nucleo NON scrive in dbops.error_log — la ragione della slice
--      (conteggio filtrato su function_name: il log e' globale e la suite
--       Django ci scrive dentro mentre gira)
--  12) P-6: l'esito porta gli INPUT della chiamata, non solo i campi del
--      proprio stadio — una riga di log sola deve bastare a ricostruire il caso
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- ============================================================
-- FIXTURE — mutuata da test-fn-resolve-prezzo-listino-v2-v1.sql, che ha gia'
-- pagato il prezzo di scoprire le tre condizioni non ovvie: utility senza
-- dimensione tipo/classe, utility compatibile con l'emittente secondo
-- config.utilities_tipi_ruolo, e nessun contratto sull'istanza (un contratto
-- porterebbe il resolver sullo STADIO 1, che qui non e' la strada in esame).
-- ============================================================
CREATE TEMP TABLE tmp_ctx AS
SELECT
    ba.id                       AS ba_id,
    ba.categoria_cliente_id     AS categoria_id,
    ba.utility_id               AS utility_id,
    (SELECT soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali
      WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS emittente_srid,
    a.id                        AS articolo_id,
    a.uom_id                    AS uom_id,
    a.listino_tipologia_id      AS tipologia_id
  FROM anagrafiche.billing_account ba
  JOIN catalogo.articoli a
    ON a.attivo IS TRUE
   AND a.listino_tipologia_id IS NOT NULL
 WHERE ba.categoria_cliente_id IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id)
   AND EXISTS (
       SELECT 1
         FROM config.utilities_tipi_ruolo utr
         JOIN anagrafiche.soggetti_ruoli sr
           ON sr.id = (SELECT soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali
                        WHERE attivo IS TRUE ORDER BY id LIMIT 1)
        WHERE utr.utility_id    = ba.utility_id
          AND utr.tipo_ruolo_id = sr.tipo_ruolo_id
          AND utr.attivo IS TRUE)
   AND NOT EXISTS (SELECT 1 FROM vendite.contratti c WHERE c.istanza_utility_id = ba.istanza_utility_id)
 ORDER BY ba.id, a.id
 LIMIT 1;

-- 1) La fixture deve aver trovato qualcosa: senza, i test 3/4/5 sarebbero
--    verdi per sottrazione (confronterebbero NULL con NULL).
SELECT isnt(
    (SELECT count(*)::int FROM tmp_ctx), 0,
    '(precondizione) esiste un billing account/articolo su cui il resolver puo'' lavorare');

CREATE TEMP TABLE tmp_listino AS
SELECT l.id AS listino_id
  FROM vendite.listini l, tmp_ctx t
 WHERE l.tipologia_id = t.tipologia_id AND l.attivo = TRUE
 ORDER BY l.id LIMIT 1;

INSERT INTO vendite.listini_versioni(listino_id, codice_versione, valido_dal, valido_al, stato, attivo)
SELECT l.listino_id, 'PGTAP_ESITO_VER', CURRENT_DATE, CURRENT_DATE + 365, 'ATTIVA', TRUE
  FROM tmp_listino l
 WHERE NOT EXISTS (
     SELECT 1 FROM vendite.listini_versioni lv
      WHERE lv.listino_id = l.listino_id AND lv.attivo = TRUE AND lv.validita @> CURRENT_DATE)
ON CONFLICT DO NOTHING;

CREATE TEMP TABLE tmp_versione AS
SELECT lv.id AS versione_id, lv.listino_id
  FROM vendite.listini_versioni lv, tmp_listino l
 WHERE lv.listino_id = l.listino_id AND lv.attivo IS TRUE AND lv.validita @> CURRENT_DATE
 ORDER BY lv.id DESC LIMIT 1;

INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.versione_id, t.articolo_id, t.uom_id, 100
  FROM tmp_versione v, tmp_ctx t
ON CONFLICT DO NOTHING;

INSERT INTO anagrafiche.categorie_clienti_listini(
    categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id,
    classe_utenza_id, listino_id, tipo_variazione, valore_variazione,
    valido_dal, valido_al)
SELECT t.categoria_id, t.utility_id, t.emittente_srid, NULL, v.listino_id,
       'VALORE_FISSO', -5, CURRENT_DATE, CURRENT_DATE + 365
  FROM tmp_ctx t, tmp_versione v;

-- Emittente NON mappato: un soggetto_ruolo che nella matrice non compare per
-- nessuna combinazione. E' la via piu' corta a un caso «non risolvibile» senza
-- rompere niente. ORDER BY esplicito: la riga si sceglie, non si pesca.
CREATE TEMP TABLE tmp_no_map AS
SELECT sr.id AS srid
  FROM anagrafiche.soggetti_ruoli sr
 WHERE NOT EXISTS (
     SELECT 1 FROM anagrafiche.categorie_clienti_listini ccl
      WHERE ccl.emittente_soggetto_ruolo_id = sr.id)
 ORDER BY sr.id LIMIT 1;

-- ============================================================
-- 2) Il nucleo esiste, con la firma attesa.
-- ============================================================
SELECT has_function(
    'vendite', 'fn_resolve_prezzo_listino_v2_esito',
    ARRAY['uuid','bigint','date','bigint','integer','bigint','integer','uuid','bigint'],
    'vendite.fn_resolve_prezzo_listino_v2_esito esiste con i 9 parametri del resolver');

-- ============================================================
-- CASO RISOLVIBILE — le due funzioni devono essere indistinguibili.
-- ============================================================
CREATE TEMP TABLE tmp_ok_nucleo AS
SELECT * FROM tmp_ctx t, LATERAL vendite.fn_resolve_prezzo_listino_v2_esito(
    t.articolo_id, t.uom_id, CURRENT_DATE, t.ba_id, t.utility_id, t.emittente_srid) r;

CREATE TEMP TABLE tmp_ok_guscio AS
SELECT * FROM tmp_ctx t, LATERAL vendite.fn_resolve_prezzo_listino_v2(
    t.articolo_id, t.uom_id, CURRENT_DATE, t.ba_id, t.utility_id, t.emittente_srid) r;

-- 3) Stesso prezzo. 100 - 5 = 95: il valore atteso e' scritto, non dedotto dal
--    risultato, altrimenti il test confermerebbe qualunque cosa esca.
SELECT is(
    (SELECT prezzo_finale FROM tmp_ok_nucleo),
    95::numeric,
    'RISOLVE: il nucleo applica la variazione VALORE_FISSO -5 su base 100');

-- 4) ...e il guscio proietta esattamente le stesse colonne.
SELECT ok(
    (SELECT n.prezzo_finale   IS NOT DISTINCT FROM g.prezzo_finale
        AND n.origine         IS NOT DISTINCT FROM g.origine
        AND n.listino_riga_id IS NOT DISTINCT FROM g.listino_riga_id
        AND n.listino_id      IS NOT DISTINCT FROM g.listino_id
       FROM tmp_ok_nucleo n, tmp_ok_guscio g),
    'RISOLVE: guscio e nucleo proiettano prezzo, origine, listino e riga identici');

-- 5) Nessun esito quando ha risolto.
SELECT ok(
    (SELECT esito_codice IS NULL AND esito_context IS NULL AND esito_valori IS NULL
       FROM tmp_ok_nucleo),
    'RISOLVE: i tre canali dell''esito restano NULL');

-- ============================================================
-- CASO NON RISOLVIBILE — il nucleo torna, il guscio solleva.
-- ============================================================
CREATE TEMP TABLE tmp_ko AS
SELECT * FROM tmp_ctx t, tmp_no_map m, LATERAL vendite.fn_resolve_prezzo_listino_v2_esito(
    t.articolo_id, t.uom_id, CURRENT_DATE, t.ba_id, t.utility_id, m.srid) r;

-- 6) UNA riga, non zero. ⚠️ Non e' pedanteria: il guscio fa SELECT INTO, e
--    SELECT INTO senza righe non solleva — azzera le variabili e prosegue.
--    Se il nucleo tornasse zero righe, il guscio restituirebbe un prezzo NULL
--    spacciandolo per risolto.
SELECT is(
    (SELECT count(*)::int FROM tmp_ko), 1,
    'NON RISOLVE: il nucleo ritorna comunque UNA riga (il guscio ci conta sopra)');

-- 7) L'esito c'e' e il prezzo no.
SELECT ok(
    (SELECT esito_codice = 'E_CATEGORIA_LISTINO_NON_MAPPATA'
        AND prezzo_finale IS NULL
        AND array_length(esito_valori, 1) = 5
       FROM tmp_ko),
    'NON RISOLVE: esito_codice = E_CATEGORIA_LISTINO_NON_MAPPATA, prezzo NULL, 5 valori');

-- 8) Il guscio, sullo stesso input, solleva ancora.
--    ⚠️ SQLSTATE esplicito: throws_ok senza SQLSTATE accetta QUALUNQUE errore,
--    compreso il crash del guscio stesso — e il test passerebbe proprio nel
--    caso che deve prendere.
SELECT throws_ok(
    format('SELECT prezzo_finale FROM vendite.fn_resolve_prezzo_listino_v2(%L::uuid, %s, %L::date, %s, %s, %s)',
           (SELECT articolo_id FROM tmp_ctx), (SELECT uom_id FROM tmp_ctx), CURRENT_DATE,
           (SELECT ba_id FROM tmp_ctx), (SELECT utility_id FROM tmp_ctx), (SELECT srid FROM tmp_no_map)),
    'P0001',
    NULL,
    'NON RISOLVE: il guscio solleva l''errore di dominio (P0001), come prima della slice');

-- 9) L'arita' dei valori regge: il messaggio esce sostituito, non a segnaposto.
--    ⚠️ format() con meno valori dei segnaposto degrada al template: il codice
--    sopravvive ma l'operatore legge «%s». Qui il giro e' nucleo -> array ->
--    VARIADIC, cioe' un passaggio in piu' rispetto a prima: va verificato.
CREATE TEMP TABLE tmp_msg(msg text);
DO $arita$
DECLARE v_msg text;
BEGIN
    PERFORM prezzo_finale FROM vendite.fn_resolve_prezzo_listino_v2(
        (SELECT articolo_id FROM tmp_ctx), (SELECT uom_id FROM tmp_ctx), CURRENT_DATE,
        (SELECT ba_id FROM tmp_ctx), (SELECT utility_id FROM tmp_ctx), (SELECT srid FROM tmp_no_map));
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
    INSERT INTO tmp_msg VALUES (v_msg);
END $arita$;

SELECT is(
    (SELECT position('%s' IN msg) FROM tmp_msg), 0,
    'NON RISOLVE: il messaggio sollevato dal guscio ha i segnaposto sostituiti');

-- ============================================================
-- 10) La meta' che NON degrada: un parametro invalido resta un errore anche
--     nel nucleo. E' la regola D-3, ed e' il confine dell'allentamento.
-- ============================================================
SELECT throws_ok(
    format('SELECT prezzo_finale FROM vendite.fn_resolve_prezzo_listino_v2_esito(%L::uuid, -1, %L::date, %s, %s, %s)',
           (SELECT articolo_id FROM tmp_ctx), CURRENT_DATE,
           (SELECT ba_id FROM tmp_ctx), (SELECT utility_id FROM tmp_ctx), (SELECT emittente_srid FROM tmp_ctx)),
    'P0001',
    NULL,
    'PARAMETRO INVALIDO: il nucleo solleva comunque — un parametro sbagliato non e'' un esito');

-- ============================================================
-- 11) ⭐ LA RAGIONE DELLA SLICE. dbops.error_log e' scritto via dblink FUORI
--     transazione: le righe sopravvivono al ROLLBACK di questo test, quindi
--     il conteggio si puo' misurare davvero. Venti risoluzioni fallite col
--     nucleo devono lasciare il log INTATTO — se un domani qualcuno
--     rimettesse un fn_log_and_raise_error sul percorso dell'esito, o
--     avvolgesse il nucleo in un BEGIN..EXCEPTION, questo test lo prende.
--
--     ⚠️ IL CONTEGGIO E' FILTRATO SUL NOME DELLA FUNZIONE, e non e' pignoleria:
--     dbops.error_log e' GLOBALE e non ha recinto fra test e produzione. La
--     suite Django del backend scrive li' dentro mentre gira (~19.800 righe di
--     solo pricing con contesti di fixture), e puo' girare in qualunque
--     momento, anche durante questo test. Un delta sul totale sarebbe rosso
--     per colpa di qualcun altro — un test che accusa l'innocente e' peggio di
--     un test che manca. Il filtro su function_name isola cio' che SOLO il
--     nucleo puo' scrivere: e' lui a firmarsi col proprio nome (20260819-07).
--     Segnalato dal BE il 2026-08-19, brief-be-pricing-codice-errore-fantasma.
-- ============================================================
CREATE TEMP TABLE tmp_log_prima AS
SELECT count(*) AS n FROM dbops.error_log
 WHERE area = 'vendite' AND function_name = 'fn_resolve_prezzo_listino_v2_esito';

-- In un DO e non in una SELECT nuda: una SELECT qui stamperebbe il proprio
-- risultato in mezzo al flusso TAP, che deve contenere solo asserzioni.
DO $venti$
DECLARE v_n integer;
BEGIN
    SELECT count(*) INTO v_n
      FROM generate_series(1, 20) g, tmp_ctx t, tmp_no_map m,
           LATERAL vendite.fn_resolve_prezzo_listino_v2_esito(
               t.articolo_id, t.uom_id, CURRENT_DATE, t.ba_id, t.utility_id, m.srid) r
     WHERE r.esito_codice IS NOT NULL;
    IF v_n <> 20 THEN
        RAISE EXCEPTION 'fixture test 11: attese 20 risoluzioni fallite, ottenute %', v_n;
    END IF;
END $venti$;

SELECT is(
    (SELECT count(*) FROM dbops.error_log
      WHERE area = 'vendite' AND function_name = 'fn_resolve_prezzo_listino_v2_esito')
    - (SELECT n FROM tmp_log_prima),
    0::bigint,
    'venti risoluzioni fallite col nucleo NON scrivono nessuna riga a suo nome in dbops.error_log');

-- ============================================================
-- 12) P-6 (richiesta BE, 2026-08-19). Deciso che a loggare sia il DB, la riga
--     del backend sparisce — e con lei articolo_id, ba_id e uom_id, che il DB
--     su diversi esiti non scriveva. Sono i campi da cui si parte per
--     ricostruire un caso: senza, resta una riga che dice cosa e' fallito ma
--     non su cosa. Verifica sull'esito piu' povero di tutti, quello della
--     matrice categoria, che prima portava solo i campi del proprio stadio.
-- ============================================================
SELECT ok(
    (SELECT esito_context ?& ARRAY['articolo_id','ba_id','uom_id',
                                   'utility_id','data_riferimento',
                                   'emittente_soggetto_ruolo_id',
                                   'classe_utenza_id']
        -- e i campi specifici dello stadio restano al loro posto: l'operatore
        -- || fa vincere la destra, quindi arricchisce senza sovrascrivere.
        AND esito_context ? 'categoria_cliente_id'
       FROM tmp_ko),
    'P-6: l''esito porta gli input della chiamata E conserva i campi del proprio stadio');

SELECT * FROM finish();
ROLLBACK;
