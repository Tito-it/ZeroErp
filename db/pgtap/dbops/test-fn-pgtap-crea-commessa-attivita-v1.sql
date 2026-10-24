-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_crea_commessa_attivita — il BB dell'attivita' di
--   commessa
-- Riferimento: brief-db-fixture-rls-documenti-costruiti (giro 3).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - scrive l'attivita' con la MADRE del dominio, APPROVATA e NON_EMESSA,
--     sulla commessa passata, con l'istanza del suo billing account;
--   - il prezzo e' quello chiesto (default 10);
--   - e' nella forma che l'EMISSIONE prende: e' la ragione per cui esiste;
--   - una commessa che non esiste parla;
--   - rev 2026-10-15 (richiesta del team BE, 20261015-23): l'articolo e la
--     provenienza del prezzo li sceglie il chiamante. Un articolo passato
--     arriva sulla riga coi SUOI flag (dal guard A-10 un articolo usato non li
--     cambia piu': deve nascere giusto); una riga di listino passata da' la
--     sua unita' di misura e, se mancano, articolo e versione; un articolo o
--     una riga di listino che non esistono parlano.
--
-- rev 2026-10-24 (20261024-41, brief-modello-documento-vendita §4-octies): la
--   sorgente (la chiave dal costruttore del dominio), gli stati, la quantita' e il periodo.
-- Elenco test (plan 14):
--   1) la funzione esiste con la firma dichiarata (cinque argomenti)
--   2) l'attivita' esiste sulla commessa, APPROVATA e NON_EMESSA
--   3) istanza di utility del billing account, competenza della commessa
--   4) prezzo: default 10, e quello chiesto quando lo si passa
--   5) l'emissione prende le attivita' del builder (una riga fatturabile
--      per attivita')
--   6) guard: una commessa che non esiste parla
--   7) articolo passato: e' quello sulla riga, con la tipologia di listino
--      che il chiamante gli ha dato prima (nessun articolo costruito)
--   8) riga di listino passata da sola: la riga la cita, con la SUA unita'
--      di misura, il suo articolo e la sua versione
--   9) versione passata senza riga: registrata sotto la versione, nessuna
--      riga di listino
--  10) guard: un articolo che non esiste parla
--  11) guard: una riga di listino che non esiste parla
--  12) sorgente PREVENTIVO: la chiave la compone script.fn_segment_key, sorgente e uid quelli del documento
--  13) quantita', stati di approvazione ed emissione e periodo dichiarati dal test
--  14) guard: una sorgente senza la chiave del documento parla
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre il builder della commessa,
--   chiamato come lo chiamera' un file su un database ricostruito.

SELECT plan(14);

-- 1) La firma
SELECT has_function(
    'dbops', 'fn_pgtap_crea_commessa_attivita',
    ARRAY['bigint', 'numeric', 'uuid', 'bigint', 'bigint', 'character varying', 'text', 'bigint', 'numeric', 'character varying', 'character varying', 'date', 'date'],
    'dbops.fn_pgtap_crea_commessa_attivita(... tredici argomenti) esiste con la firma dichiarata'
);

-- Fixture: una commessa e due attivita' (prezzo di default e prezzo scelto)
CREATE TEMP TABLE t_c AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('presidio attivita');

CREATE TEMP TABLE t_a1 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM t_c));

CREATE TEMP TABLE t_a2 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM t_c), 25);

-- 2) L'attivita' c'e', sulla commessa, nella forma attesa
SELECT is(
    (SELECT ca.commessa_id::text || ' ' || ca.stato_approvazione || ' ' || ca.stato_emissione
       FROM vendite.commesse_attivita ca
      WHERE ca.id = (SELECT attivita_id FROM t_a1)),
    (SELECT commessa_id::text FROM t_c) || ' APPROVATA NON_EMESSA',
    'l''attivita'' esiste sulla commessa, APPROVATA e NON_EMESSA'
);

-- 3) Istanza del billing account, competenza della commessa
SELECT ok(
    (SELECT ca.istanza_utility_id = c.istanza_utility_id
            AND ca.competenza_dal = co.competenza_dal
            AND ca.competenza_al  = co.competenza_al
       FROM vendite.commesse_attivita ca
       JOIN vendite.commesse co ON co.id = ca.commessa_id, t_c c
      WHERE ca.id = (SELECT attivita_id FROM t_a1)),
    'istanza di utility del billing account, competenza della commessa'
);

-- 4) Il prezzo
SELECT is(
    (SELECT string_agg(ca.prezzo_snapshot::numeric(10,2)::text, ' ' ORDER BY ca.prezzo_snapshot)
       FROM vendite.commesse_attivita ca
      WHERE ca.id IN ((SELECT attivita_id FROM t_a1), (SELECT attivita_id FROM t_a2))),
    '10.00 25.00',
    'prezzo: 10 di default, 25 quando lo si chiede'
);

-- 5) L'emissione le prende: la catena dell'applicazione, passo per passo
SELECT vendite.fn_link_commessa_sorgente(
    p_commessa_id      => (SELECT commessa_id FROM t_c),
    p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s
                            WHERE s.codice_interno = 'COMMESSA' AND s.attivo),
    p_sorgente_uid     => (SELECT commessa_id FROM t_c)::text);

UPDATE vendite.commesse
   SET stato_commessa_id = (SELECT s.id FROM vendite.stati_commessa s
                             WHERE s.codice_interno = 'PRONTA_FATTURAZIONE')
 WHERE id = (SELECT commessa_id FROM t_c);

CREATE TEMP TABLE t_emit AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
    p_commessa_id   => (SELECT commessa_id FROM t_c),
    p_only_approved => true,
    p_dry_run       => false);

SELECT is(
    (SELECT count(*)::integer FROM vendite.attivita_fatturabili af
      WHERE af.commessa_attivita_id IN ((SELECT attivita_id FROM t_a1), (SELECT attivita_id FROM t_a2))),
    2,
    'l''emissione prende le attivita'' del builder: una riga fatturabile ciascuna'
);

-- 6) Guard: una commessa che non esiste
SELECT throws_like($$
    SELECT dbops.fn_pgtap_crea_commessa_attivita(-1)
$$,
    '%nessuna commessa con id%',
    'guard: una commessa inesistente parla, invece di far morire la madre su un NULL'
);

-- ============================================================
-- 7-11) L'articolo e il listino dal chiamante (20261015-23)
-- ============================================================
-- Una seconda commessa, fuori dall'emissione del test 5, e un listino della
-- sua utility. L'articolo nasce GIA' della tipologia del listino: un listino
-- tipizzato accetta solo articoli della sua tipologia, e da usato non la
-- cambierebbe piu'.
CREATE TEMP TABLE t_c2 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('presidio attivita listino');

CREATE TEMP TABLE t_l AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_c2), 'presidio attivita');

CREATE TEMP TABLE t_art AS
SELECT dbops.fn_pgtap_crea_articolo(
           ('PGT-BCA-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar,
           false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM t_l)) AS articolo_id;

-- Due righe di listino dello stesso articolo: R1 nella sua unita' di misura,
-- R2 in un'altra (la chiave attiva e' versione + articolo + UoM).
CREATE TEMP TABLE t_uom AS
SELECT a.uom_id AS u1,
       (SELECT u.id FROM catalogo.unita_misura u
         WHERE u.attivo AND u.id <> a.uom_id ORDER BY u.id LIMIT 1) AS u2
  FROM catalogo.articoli a
 WHERE a.id = (SELECT articolo_id FROM t_art);

CREATE TEMP TABLE t_r AS
WITH ins AS (
    INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
    VALUES ((SELECT listino_versione_id FROM t_l), (SELECT articolo_id FROM t_art),
            (SELECT u1 FROM t_uom), 10.00),
           ((SELECT listino_versione_id FROM t_l), (SELECT articolo_id FROM t_art),
            (SELECT u2 FROM t_uom), 20.00)
    RETURNING id, uom_id
)
SELECT (SELECT id FROM ins WHERE uom_id = (SELECT u1 FROM t_uom)) AS r1,
       (SELECT id FROM ins WHERE uom_id = (SELECT u2 FROM t_uom)) AS r2;

CREATE TEMP TABLE t_a3 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM t_c2),
    p_articolo_id => (SELECT articolo_id FROM t_art));

CREATE TEMP TABLE t_a4 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id     => (SELECT commessa_id FROM t_c2),
    p_prezzo_snapshot => 20,
    p_listino_riga_id => (SELECT r2 FROM t_r));

CREATE TEMP TABLE t_a5 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id         => (SELECT commessa_id FROM t_c2),
    p_articolo_id         => (SELECT articolo_id FROM t_art),
    p_listino_versione_id => (SELECT listino_versione_id FROM t_l));

-- 7) L'articolo passato, coi suoi flag
SELECT ok(
    (SELECT a3.articolo_id = art.articolo_id
            AND ca.articolo_id = art.articolo_id
            AND ar.listino_tipologia_id = l.tipologia_id
       FROM t_a3 a3, t_art art, t_l l,
            vendite.commesse_attivita ca, catalogo.articoli ar
      WHERE ca.id = a3.attivita_id
        AND ar.id = art.articolo_id),
    'articolo passato: e'' sulla riga, con la tipologia di listino data prima (nessun articolo costruito)'
);

-- 8) La sola riga di listino: unita' di misura, articolo e versione da lei
SELECT is(
    (SELECT (ca.listino_riga_id = rr.r2)::text || ' ' || (ca.uom_id = u.u2)::text || ' '
            || (ca.articolo_id = art.articolo_id)::text || ' '
            || (ca.listino_versione_id = l.listino_versione_id)::text
       FROM t_a4 a4, t_r rr, t_uom u, t_art art, t_l l, vendite.commesse_attivita ca
      WHERE ca.id = a4.attivita_id),
    'true true true true',
    'riga di listino passata da sola: la riga la cita, con la sua unita'' di misura, il suo articolo e la sua versione'
);

-- 9) La sola versione: registrata sotto la versione, senza riga di listino
SELECT is(
    (SELECT (ca.listino_versione_id = l.listino_versione_id)::text || ' '
            || (ca.listino_riga_id IS NULL)::text
       FROM t_a5 a5, t_l l, vendite.commesse_attivita ca
      WHERE ca.id = a5.attivita_id),
    'true true',
    'versione passata senza riga: registrata sotto la versione, nessuna riga di listino'
);

-- 10-11) Guard sui parametri nuovi
SELECT throws_like(
    format('SELECT dbops.fn_pgtap_crea_commessa_attivita(p_commessa_id => %s, p_articolo_id => %L::uuid)',
           (SELECT commessa_id FROM t_c2), gen_random_uuid()),
    '%nessun articolo con id%',
    'guard: un articolo che non esiste parla, invece di far morire la madre su uom_id'
);

SELECT throws_like(
    format('SELECT dbops.fn_pgtap_crea_commessa_attivita(p_commessa_id => %s, p_listino_riga_id => -1)',
           (SELECT commessa_id FROM t_c2)),
    '%nessuna riga di listino con id%',
    'guard: una riga di listino che non esiste parla'
);

-- 12-14) La sorgente, gli stati, la quantita' e il periodo (rev 2026-10-24)
-- Un preventivo vero: la tabella verifica che la chiave della sorgente esista.
CREATE TEMP TABLE t_prev_sorg AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('presidio attivita sorgente');

CREATE TEMP TABLE t_a_sorg AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT commessa_id FROM t_c),
    p_prezzo_snapshot    => 30,
    p_sorgente_codice    => 'PREVENTIVO',
    p_sorgente_uid       => (SELECT preventivo_uid::text FROM t_prev_sorg),
    p_sorgente_riga_id   => 4242,
    p_quantita           => 3,
    p_stato_approvazione => 'BOZZA',
    p_stato_emissione    => 'EMESSA',
    p_competenza_dal     => DATE '2080-01-01',
    p_competenza_al      => DATE '2080-12-31');

SELECT is(
    (SELECT (ca.segment_key = script.fn_segment_key('PREVENTIVO', (SELECT preventivo_uid::text FROM t_prev_sorg), 4242))::text
            || ' ' || s.codice_interno::text
            || ' ' || (ca.sorgente_uid = (SELECT preventivo_uid::text FROM t_prev_sorg))::text
       FROM t_a_sorg a JOIN vendite.commesse_attivita ca ON ca.id = a.attivita_id
       JOIN config.sorgenti s ON s.id = ca.sorgente_tipo_id),
    'true PREVENTIVO true',
    '12) sorgente PREVENTIVO: la chiave la compone script.fn_segment_key, sorgente e uid sono quelli del documento'
);

SELECT is(
    (SELECT ca.quantita::numeric(18,2)::text || ' ' || ca.stato_approvazione || ' ' || ca.stato_emissione
            || ' ' || ca.competenza_dal::text || ' ' || ca.competenza_al::text
       FROM t_a_sorg a JOIN vendite.commesse_attivita ca ON ca.id = a.attivita_id),
    '3.00 BOZZA EMESSA 2080-01-01 2080-12-31',
    '13) quantita'', stati di approvazione ed emissione e periodo li dichiara il test'
);

SELECT throws_like(
    format($$SELECT dbops.fn_pgtap_crea_commessa_attivita(p_commessa_id => %s, p_sorgente_codice => 'PREVENTIVO')$$,
           (SELECT commessa_id FROM t_c)),
    '%vuole la chiave del documento%',
    '14) guard: una sorgente senza la chiave del documento parla'
);

SELECT * FROM finish();
ROLLBACK;
