-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Un civico, una riga: l'unicita' di anagrafiche.indirizzi_dettaglio e il suo
-- «trova o crea». Brief: brief-db-unicita-civico-indirizzi-dettaglio (§5.4).
-- I casi si COSTRUISCONO (civici 9997x, interni ZZPGTU*): nessuna asserzione
-- si appoggia alle righe presenti.
--
-- Elenco test (plan 28):
--  1) l'indice v2 e' sulle sette colonne nude, NULLS NOT DISTINCT (la clausola, non il nome)
--  2) l'indice vecchio (COALESCE, civico nudo) non c'e' piu'
--  3) CHECK di rete sul civico, forma esatta
--  4) CHECK di rete sul dettaglio leggibile, forma esatta
--  5) il guard z10 e' montato BEFORE INSERT OR UPDATE
--  6) A: una riga SNC con un dettaglio nasce
--  7) A: la seconda riga SNC identica e' rifiutata dall'indice (23505)
--  8) A: il BB sullo stesso SNC restituisce l'id esistente
--  9) C: il BB crea con estensione e interno minuscoli
-- 10) C: stessa chiave scritta maiuscola e con spazi -> stesso id (prima: NULL)
-- 11) C: estensione gia' col prefisso '/' -> stesso id
-- 12) vuoto: palazzina '' e palazzina NULL sono la stessa riga
-- 13) vuoto: la palazzina '' si salva NULL
-- 14) D2-a: INSERT con civico 0 rifiutato dal guard
-- 15) D2-a: il BB con civico negativo e' rifiutato
-- 16) D8: estensione di soli segni rifiutata
-- 17) D8: scala di soli segni rifiutata
-- 18) D8: piano -1 ed estensione /B accettati
-- 19) D8: interno di soli spazi = nessun interno (stesso id)
-- 20) D5: il BB su una riga disattivata restituisce il suo id
-- 21) D5: e la riattiva
-- 22) D6: UPDATE che porta una riga sulla chiave di un'altra -> frase del doppione
-- 23) D6: UPDATE che non tocca la chiave passa
-- 24) D6: UPDATE su una chiave libera passa
-- 25) D4: via che non si risolve (comune senza provincia) -> errore leggibile
-- 26) fn_check_indirizzo_duplicato: l'SNC costruito e' un match esatto
-- 27) builder di fixture: la stessa etichetta da' lo stesso id (ON CONFLICT sul v2)
-- 28) builder di fixture: etichette diverse danno id diversi
--
-- Scopo:
--  - presidiare i tre buchi del brief (A civico SNC fuori dall'indice, B due
--    modi di dire SNC, C il lookup coi valori grezzi) e le decisioni D2-a, D4,
--    D5, D6, D8;
--  - asserire la CLAUSOLA dell'indice e la forma dei CHECK (linee guida SQL
--    §8.4-bis), non solo i nomi.
--  ⚠️ Non presidia la corsa concorrente (due sessioni) ne' la ri-lettura vuota
--    (E_INDIRIZZO_DETTAGLIO_NON_RILETTO): in una sessione sola non si producono.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE: un fallimento a meta' non lascia dati di prova.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: gira come zeroerp_app, RLS attiva.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI: IMMEDIATE, o non verrebbero esercitati.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(28);

-- =========================================================
-- Fixture: uno stradario di seed che si risolve nella vista, e gli id
-- =========================================================
CREATE TEMP TABLE tmp_u (
    k   text PRIMARY KEY,
    id  bigint
);

INSERT INTO tmp_u (k, id)
SELECT 'stradario', s.id
  FROM config.stradario s
  JOIN script.vw_indirizzo_completo v ON v.id_stradario = s.id
 ORDER BY s.id
 LIMIT 1;

-- =========================================================
-- 1-5) Struttura
-- =========================================================
SELECT is(
    (SELECT pg_get_indexdef(i.indexrelid) || ' nnd=' || i.indnullsnotdistinct
       FROM pg_index i
      WHERE i.indexrelid = to_regclass('anagrafiche.uq_indirizzi_dettaglio_norm_v2')),
    'CREATE UNIQUE INDEX uq_indirizzi_dettaglio_norm_v2 ON anagrafiche.indirizzi_dettaglio USING btree (stradario_id, civico, estensione_civico, palazzina, scala, piano, interno) NULLS NOT DISTINCT nnd=true',
    '1. uq_indirizzi_dettaglio_norm_v2: sette colonne nude, NULLS NOT DISTINCT'
);

SELECT ok(
    to_regclass('anagrafiche.uq_indirizzi_dettaglio_norm') IS NULL,
    '2. l''indice vecchio uq_indirizzi_dettaglio_norm non c''e'' piu'''
);

SELECT is(
    (SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c
      WHERE c.conrelid = 'anagrafiche.indirizzi_dettaglio'::regclass
        AND c.conname = 'chk_indirizzi_dettaglio_civico_positivo'),
    'CHECK (((civico IS NULL) OR (civico > 0)))',
    '3. CHECK di rete sul civico: NULL o > 0'
);

SELECT is(
    (SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c
      WHERE c.conrelid = 'anagrafiche.indirizzi_dettaglio'::regclass
        AND c.conname = 'chk_indirizzi_dettaglio_dettaglio_leggibile'),
    'CHECK ((((estensione_civico IS NULL) OR ((estensione_civico)::text ~ ''[[:alnum:]]''::text)) AND ((palazzina IS NULL) OR ((palazzina)::text ~ ''[[:alnum:]]''::text)) AND ((scala IS NULL) OR ((scala)::text ~ ''[[:alnum:]]''::text)) AND ((piano IS NULL) OR ((piano)::text ~ ''[[:alnum:]]''::text)) AND ((interno IS NULL) OR ((interno)::text ~ ''[[:alnum:]]''::text))))',
    '4. CHECK di rete sul dettaglio: le cinque colonne NULL o con una lettera o una cifra'
);

-- tgtype: 1 ROW + 2 BEFORE + 4 INSERT + 16 UPDATE = 23. La funzione si
-- confronta per OID: regproc::text dipende dal search_path di chi esegue.
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
         WHERE t.tgrelid = 'anagrafiche.indirizzi_dettaglio'::regclass
           AND t.tgname = 'trg_indirizzi_dettaglio_z10_guard_chiave_ins_upd'
           AND t.tgtype = 23
           AND t.tgfoid = to_regprocedure('anagrafiche.trgfn_indirizzi_dettaglio_guard_chiave()')),
    '5. guard z10 BEFORE INSERT OR UPDATE FOR EACH ROW'
);

-- =========================================================
-- 6-8) A: il civico SNC e' nella chiave
-- =========================================================
SELECT lives_ok(
    format($$INSERT INTO anagrafiche.indirizzi_dettaglio (stradario_id, civico, interno)
             VALUES (%s, NULL, 'zzpgtua')$$, (SELECT id FROM tmp_u WHERE k = 'stradario')),
    '6. A: una riga SNC con interno nasce'
);

INSERT INTO tmp_u (k, id)
SELECT 'snc', d.id
  FROM anagrafiche.indirizzi_dettaglio d
 WHERE d.stradario_id = (SELECT id FROM tmp_u WHERE k = 'stradario')
   AND d.civico IS NULL AND d.interno = 'ZZPGTUA';

SELECT throws_ok(
    format($$INSERT INTO anagrafiche.indirizzi_dettaglio (stradario_id, civico, interno)
             VALUES (%s, NULL, 'ZZPGTUA')$$, (SELECT id FROM tmp_u WHERE k = 'stradario')),
    '23505', NULL,
    '7. A: la seconda riga SNC identica urta l''indice'
);

SELECT is(
    anagrafiche.fn_get_or_create_indirizzo_dettaglio(
        (SELECT id FROM tmp_u WHERE k = 'stradario')::integer,
        p_interno := 'zzpgtua'),
    (SELECT id FROM tmp_u WHERE k = 'snc'),
    '8. A: il BB sullo stesso SNC restituisce l''id esistente'
);

-- =========================================================
-- 9-13) C e il vuoto: il lookup confronta i valori come si salvano
-- =========================================================
INSERT INTO tmp_u (k, id)
SELECT 'c', anagrafiche.fn_get_or_create_indirizzo_dettaglio(
    (SELECT id FROM tmp_u WHERE k = 'stradario')::integer, 99971,
    p_estensione_civico := 'a', p_interno := 'zzpgtuc');

SELECT ok(
    (SELECT d.estensione_civico || '|' || d.interno FROM anagrafiche.indirizzi_dettaglio d
      WHERE d.id = (SELECT id FROM tmp_u WHERE k = 'c')) = '/A|ZZPGTUC',
    '9. C: il BB crea, e il trigger salva /A e ZZPGTUC'
);

SELECT is(
    anagrafiche.fn_get_or_create_indirizzo_dettaglio(
        (SELECT id FROM tmp_u WHERE k = 'stradario')::integer, 99971,
        p_estensione_civico := ' A ', p_interno := 'ZZPGTUC '),
    (SELECT id FROM tmp_u WHERE k = 'c'),
    '10. C: la stessa chiave in maiuscolo e con spazi trova la riga (prima: NULL)'
);

SELECT is(
    anagrafiche.fn_get_or_create_indirizzo_dettaglio(
        (SELECT id FROM tmp_u WHERE k = 'stradario')::integer, 99971,
        p_estensione_civico := '/a', p_interno := 'zzPgtuc'),
    (SELECT id FROM tmp_u WHERE k = 'c'),
    '11. C: l''estensione gia'' col prefisso / trova la stessa riga'
);

INSERT INTO tmp_u (k, id)
SELECT 'vuoto', anagrafiche.fn_get_or_create_indirizzo_dettaglio(
    (SELECT id FROM tmp_u WHERE k = 'stradario')::integer, 99972, p_palazzina := '');

SELECT is(
    anagrafiche.fn_get_or_create_indirizzo_dettaglio(
        (SELECT id FROM tmp_u WHERE k = 'stradario')::integer, 99972),
    (SELECT id FROM tmp_u WHERE k = 'vuoto'),
    '12. vuoto: palazzina '''' e palazzina NULL sono la stessa riga'
);

SELECT ok(
    (SELECT d.palazzina IS NULL FROM anagrafiche.indirizzi_dettaglio d
      WHERE d.id = (SELECT id FROM tmp_u WHERE k = 'vuoto')),
    '13. vuoto: la palazzina '''' si salva NULL'
);

-- =========================================================
-- 14-15) D2-a: SNC e' solo il civico vuoto
-- =========================================================
SELECT throws_like(
    format($$INSERT INTO anagrafiche.indirizzi_dettaglio (stradario_id, civico, interno)
             VALUES (%s, 0, 'ZZPGTUB')$$, (SELECT id FROM tmp_u WHERE k = 'stradario')),
    '%deve essere maggiore di zero%',
    '14. D2-a: civico 0 rifiutato dal guard, con la frase'
);

SELECT throws_like(
    format($$SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(%s, -5)$$,
           (SELECT id FROM tmp_u WHERE k = 'stradario')),
    '%deve essere maggiore di zero%',
    '15. D2-a: il BB con civico negativo e'' rifiutato'
);

-- =========================================================
-- 16-19) D8: almeno una lettera o una cifra
-- =========================================================
SELECT throws_like(
    format($$SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(%s, 99973, '/')$$,
           (SELECT id FROM tmp_u WHERE k = 'stradario')),
    '%serve almeno una lettera o una cifra%',
    '16. D8: estensione di soli segni rifiutata'
);

SELECT throws_like(
    format($$SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(%s, 99973, p_scala := '-')$$,
           (SELECT id FROM tmp_u WHERE k = 'stradario')),
    '%serve almeno una lettera o una cifra%',
    '17. D8: scala di soli segni rifiutata'
);

SELECT lives_ok(
    format($$SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(%s, 99973, '/b', p_piano := '-1')$$,
           (SELECT id FROM tmp_u WHERE k = 'stradario')),
    '18. D8: estensione /B e piano -1 accettati'
);

SELECT is(
    anagrafiche.fn_get_or_create_indirizzo_dettaglio(
        (SELECT id FROM tmp_u WHERE k = 'stradario')::integer, 99974, p_interno := '   '),
    anagrafiche.fn_get_or_create_indirizzo_dettaglio(
        (SELECT id FROM tmp_u WHERE k = 'stradario')::integer, 99974),
    '19. D8: interno di soli spazi = nessun interno'
);

-- =========================================================
-- 20-21) D5: la riga spenta torna in uso
-- =========================================================
UPDATE anagrafiche.indirizzi_dettaglio
   SET attivo = false
 WHERE id = (SELECT id FROM tmp_u WHERE k = 'c');

SELECT is(
    anagrafiche.fn_get_or_create_indirizzo_dettaglio(
        (SELECT id FROM tmp_u WHERE k = 'stradario')::integer, 99971,
        p_estensione_civico := 'A', p_interno := 'ZZPGTUC'),
    (SELECT id FROM tmp_u WHERE k = 'c'),
    '20. D5: il BB su una riga disattivata ne restituisce l''id'
);

SELECT ok(
    (SELECT d.attivo FROM anagrafiche.indirizzi_dettaglio d
      WHERE d.id = (SELECT id FROM tmp_u WHERE k = 'c')),
    '21. D5: e la riattiva'
);

-- =========================================================
-- 22-24) D6: la modifica sul posto che collide
-- =========================================================
SELECT throws_like(
    format($$UPDATE anagrafiche.indirizzi_dettaglio
                SET civico = 99971, estensione_civico = 'a', interno = 'zzpgtuc'
              WHERE id = %s$$, (SELECT id FROM tmp_u WHERE k = 'vuoto')),
    '%la modifica ne creerebbe un doppione%',
    '22. D6: UPDATE sulla chiave di un''altra riga -> frase del doppione'
);

SELECT lives_ok(
    format($$UPDATE anagrafiche.indirizzi_dettaglio SET altro = 'pgTAP unicita'
              WHERE id = %s$$, (SELECT id FROM tmp_u WHERE k = 'vuoto')),
    '23. D6: UPDATE che non tocca la chiave passa'
);

SELECT lives_ok(
    format($$UPDATE anagrafiche.indirizzi_dettaglio SET civico = 99975
              WHERE id = %s$$, (SELECT id FROM tmp_u WHERE k = 'vuoto')),
    '24. D6: UPDATE su una chiave libera passa'
);

-- =========================================================
-- 25) D4: la via che non si risolve
--     config.comuni.provincia_id e' nullable: un comune senza provincia
--     esce dai JOIN di script.vw_indirizzo_completo.
-- =========================================================
INSERT INTO config.comuni (descrizione, provincia_id)
VALUES ('PGTAP Comune senza provincia', NULL);

INSERT INTO config.stradario (comune_id, stradario_generale_id, codice_postale_id, storicizza)
SELECT (SELECT c.id FROM config.comuni c WHERE c.descrizione = 'PGTAP Comune senza provincia'),
       s.stradario_generale_id, s.codice_postale_id, false
  FROM config.stradario s
 WHERE s.id = (SELECT id FROM tmp_u WHERE k = 'stradario');

INSERT INTO tmp_u (k, id)
SELECT 'non_risolto', s.id
  FROM config.stradario s
  JOIN config.comuni c ON c.id = s.comune_id
 WHERE c.descrizione = 'PGTAP Comune senza provincia';

SELECT throws_like(
    format($$SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(%s, 5, p_scala := 'B')$$,
           (SELECT id FROM tmp_u WHERE k = 'non_risolto')),
    '%non è completa nell''elenco delle vie%',
    '25. D4: via non risolta -> errore leggibile (prima: 23502 su via_norm)'
);

-- =========================================================
-- 26) fn_check_indirizzo_duplicato dice la stessa cosa dell'indice
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM script.fn_check_indirizzo_duplicato(
                   p_stradario_id := (SELECT id FROM tmp_u WHERE k = 'stradario')::integer,
                   p_interno      := 'zzpgtua') r
         WHERE r.indirizzo_dettaglio_id = (SELECT id FROM tmp_u WHERE k = 'snc')
           AND r.exact_match),
    '26. fn_check_indirizzo_duplicato: l''SNC costruito e'' un match esatto'
);

-- =========================================================
-- 27-28) Il builder delle fixture segue l'indice nuovo
-- =========================================================
SELECT is(
    dbops.fn_pgtap_crea_indirizzo_dettaglio('pgtu uno'),
    dbops.fn_pgtap_crea_indirizzo_dettaglio('pgtu uno'),
    '27. builder: la stessa etichetta da'' lo stesso id'
);

SELECT isnt(
    dbops.fn_pgtap_crea_indirizzo_dettaglio('pgtu uno'),
    dbops.fn_pgtap_crea_indirizzo_dettaglio('pgtu due'),
    '28. builder: etichette diverse danno id diversi'
);

SELECT * FROM finish();
ROLLBACK;
