-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: tre capability dicono cio' che il frontend leggeva dai codici.
--   ChangeSet: 20261114-74 (script.fn_available_actions_ddt,
--   can_genera_reso_reason_valori), -75 (script.fn_available_actions_contratto,
--   le marche dello stato), -76 (vendite.fn_preventivo_in_smistamento), -77
--   (vendite.fn_preventivo_proietta_stato_smistamento), -78
--   (script.fn_available_actions_preventivo, in_smistamento); giro 6g-bis:
--   -79 (script.fn_available_actions_ordine), -80
--   (script.fn_available_actions_offerta), -81
--   (script.fn_available_actions_documento_interno), i valori del motivo degli
--   altri cinque flag.
--   Brief: brief-db-stati-documento-dal-vocabolario, giri 6g (D-VAL, D-MARCHE,
--   D-SMIST) e 6g-bis (D-VAL-2).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - ogni flag col suo motivo porta i valori della frase del primo motivo
--     (<flag>_reason_valori), [] quando e' vero, quando il motivo e' scritto
--     dalla capability senza valori o quando la frase non ne ha: la bolla
--     (can_genera_reso), l'ordine (can_genera_ddt,
--     can_edit_data_consegna_confermata), l'offerta (can_push_contratto,
--     can_genera_ordine), i documenti interni (can_registra);
--   - la capability del contratto porta le quattro marche dello stato corrente,
--     una per colonna del vocabolario, anche sullo stato di annullo, che non e'
--     iniziale, emissione ne' cessazione;
--   - «il preventivo si smista» ha una sede: vero dallo stato di accettazione e
--     da EVASO, falso altrove e con un argomento NULL; la capability e la
--     proiezione la leggono (presidio sulla FORMA, dichiarato tale).
--
-- ⭐ LA MARCA SPOSTATA: una colonna si sposta in transazione su un altro stato,
--   e la risposta deve seguirla. Gli indici unici parziali sono immediati:
--   prima si spegne la marca di partenza, poi si accende l'altra.
-- ⭐ I CASI SI COSTRUISCONO dai builder, per la strada dell'applicazione.
--   EVASO e' la destinazione di un processo (lo smistamento): non si raggiunge
--   da un builder, e la sua risposta si prova sul building block, che riceve i
--   valori dello stato.
--
-- Elenco test (plan 18):
--   1) bolla di trasferimento: can_genera_reso falso, motivo DDT_TRASFERIMENTO,
--      valori il numero della bolla (o l'id, se non numerata)
--   2) bolla emessa, non consegnata: valori [] (la frase non ha segnaposti)
--   3) bolla consegnata: can_genera_reso vero, valori []
--   4) contratto: le quattro marche in bozza, attivo, cessato e annullato sono le
--      colonne del vocabolario del suo stato
--   5) contrasto: sul seed l'annullato e' solo terminale, il cessato cessazione e
--      terminale
--   6) ⭐ terminale tolto all'annullo: stato_terminale lo segue
--   7) building block: vero da accettazione e da EVASO, falso altrove e con NULL
--   8) building block: IMMUTABLE e non STRICT
--   9) preventivo: in_smistamento falso in bozza e nell'emesso, vero
--      nell'accettato
--  10) ⭐ accettazione spostata sull'emesso: in_smistamento la segue
--  11) forma: la proiezione parte dal building block e non riscrive il
--      predicato
--  12) forma: la capability del preventivo legge il building block
--  13) ordine: can_genera_ddt in bozza coi valori della frase (numero, stato),
--      vero e [] al confermato
--  14) ordine: can_edit_data_consegna_confermata, [] in bozza (il motivo e'
--      della capability) e al confermato, i valori della check sull'evaso
--  15) offerta accettata con un servizio: can_genera_ordine coi valori della
--      frase (etichetta, codice dell'articolo), can_push_contratto vero e []
--  16) offerta in bozza: i due motivi della capability, valori []
--  17) ⭐ riga fuori dal vocabolario della natura: can_push_contratto coi
--      valori della frase
--  18) documento interno: can_registra coi valori in bozza (stato,
--      destinazione) e confermato vuoto (id)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE t_ddt (caso text PRIMARY KEY,   -- l'etichetta del test
                         id   bigint);            -- vendite.ddt.id

INSERT INTO t_ddt
SELECT 'trasferimento', b.ddt_id
  FROM dbops.fn_pgtap_crea_ddt_senza_ordine('giro 6g, trasferimento', 'DRAFT',
                                            p_causale_codice => 'TRASFERIMENTO') b;
INSERT INTO t_ddt
SELECT 'emessa', b.ddt_id FROM dbops.fn_pgtap_crea_ddt_senza_ordine('giro 6g, emessa', 'EMESSO') b;
INSERT INTO t_ddt
SELECT 'consegnata', b.ddt_id FROM dbops.fn_pgtap_crea_ddt_da_ordine('giro 6g, consegnata') b;

CREATE FUNCTION pg_temp.cap_ddt(p_caso text, p_chiave text)   -- text: etichetta e chiave del blob
RETURNS jsonb LANGUAGE sql STABLE AS $$                       -- jsonb: un valore del blob
    SELECT script.fn_available_actions_ddt(t.id) -> p_chiave FROM t_ddt t WHERE t.caso = p_caso
$$;

CREATE TEMP TABLE t_con (caso text PRIMARY KEY,   -- l'etichetta del test
                         id   bigint);            -- vendite.contratti.id

INSERT INTO t_con
SELECT c.caso, k.contratto_id
  FROM (VALUES ('bozza', 'DRAFT'), ('attivo', 'ATTIVO'), ('annullato', 'ANNULLATO')) c(caso, stato)
 CROSS JOIN LATERAL dbops.fn_pgtap_crea_contratto('giro 6g, ' || c.caso, c.stato,
                                                  p_valido_dal => script.fn_data_operativa()) k;
-- La cessazione: dall'attivo, per la strada del verbo, che la vuole con la data
-- di fine valorizzata e arrivata.
INSERT INTO t_con
SELECT 'cessato', k.contratto_id
  FROM dbops.fn_pgtap_crea_contratto('giro 6g, cessato', 'ATTIVO',
                                     p_valido_dal => script.fn_data_operativa(),
                                     p_valido_al  => script.fn_data_operativa()) k;
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass,
                                    (SELECT id FROM t_con WHERE caso = 'cessato'), 'CESSATO');

-- Le quattro marche del blob, nell'ordine iniziale, emissione, cessazione,
-- terminale.
CREATE FUNCTION pg_temp.marche_cap(p_caso text)   -- text: l'etichetta del test
RETURNS text LANGUAGE sql STABLE AS $$            -- text: quattro valori composti
    SELECT concat_ws(' ', b ->> 'stato_iniziale', b ->> 'stato_emissione',
                          b ->> 'stato_cessazione', b ->> 'stato_terminale')
      FROM t_con t CROSS JOIN LATERAL script.fn_available_actions_contratto(t.id) b
     WHERE t.caso = p_caso
$$;

-- Le stesse quattro colonne, lette dal vocabolario dello stato del contratto.
CREATE FUNCTION pg_temp.marche_voc(p_caso text)   -- text: l'etichetta del test
RETURNS text LANGUAGE sql STABLE AS $$            -- text: quattro valori composti
    SELECT concat_ws(' ', to_jsonb(s.iniziale), to_jsonb(s.emissione),
                          to_jsonb(s.cessazione), to_jsonb(s.terminale))
      FROM t_con t
      JOIN vendite.contratti c ON c.id = t.id
      JOIN config.stati_doc_contratti s ON s.id = c.stato_doc_contratto_id
     WHERE t.caso = p_caso
$$;

CREATE TEMP TABLE t_prev (caso text PRIMARY KEY,   -- l'etichetta del test
                          id   bigint);            -- vendite.preventivi.id

INSERT INTO t_prev SELECT 'bozza', p.preventivo_id FROM dbops.fn_pgtap_crea_preventivo('giro 6g, bozza', 'DRAFT') p;
INSERT INTO t_prev
SELECT c.caso, p.preventivo_id
  FROM (VALUES ('emesso', 'EMESSO'), ('accettato', 'ACCETTATO')) c(caso, stato)
 CROSS JOIN LATERAL dbops.fn_pgtap_crea_preventivo_con_righe('giro 6g, ' || c.caso, c.stato) p;

CREATE FUNCTION pg_temp.smista(p_caso text)   -- text: l'etichetta del test
RETURNS text LANGUAGE sql STABLE AS $$        -- text: un valore del blob jsonb
    SELECT script.fn_available_actions_preventivo(t.id) ->> 'in_smistamento' FROM t_prev t WHERE t.caso = p_caso
$$;

-- ============================================================
-- 1-3. La bolla: i valori del motivo di can_genera_reso
-- ============================================================
SELECT is(
    concat_ws(' ', pg_temp.cap_ddt('trasferimento', 'can_genera_reso'),
                   pg_temp.cap_ddt('trasferimento', 'can_genera_reso_reason') #>> '{}',
                   pg_temp.cap_ddt('trasferimento', 'can_genera_reso_reason_valori')),
    (SELECT concat_ws(' ', 'false', 'DDT_TRASFERIMENTO',
                      jsonb_build_array(COALESCE(d.numero, d.id::text)))
       FROM vendite.ddt d WHERE d.id = (SELECT id FROM t_ddt WHERE caso = 'trasferimento')),
    '1. bolla di trasferimento: can_genera_reso falso, DDT_TRASFERIMENTO, coi valori della frase'
);

SELECT is(
    concat_ws(' ', pg_temp.cap_ddt('emessa', 'can_genera_reso'),
                   pg_temp.cap_ddt('emessa', 'can_genera_reso_reason') #>> '{}',
                   pg_temp.cap_ddt('emessa', 'can_genera_reso_reason_valori')),
    'false DDT_NON_CONSEGNATO []',
    '2. bolla emessa: il motivo senza segnaposti porta valori []'
);

SELECT is(
    concat_ws(' ', pg_temp.cap_ddt('consegnata', 'can_genera_reso'),
                   pg_temp.cap_ddt('consegnata', 'can_genera_reso_reason_valori')),
    'true []',
    '3. bolla consegnata: can_genera_reso vero, valori []'
);

-- ============================================================
-- 4-6. Il contratto: le marche dello stato
-- ============================================================
SELECT is(
    (SELECT string_agg(c.caso || ' ' || coalesce(pg_temp.marche_cap(c.caso), 'NULL'), ', ' ORDER BY c.caso)
       FROM t_con c),
    (SELECT string_agg(c.caso || ' ' || coalesce(pg_temp.marche_voc(c.caso), 'NULL'), ', ' ORDER BY c.caso)
       FROM t_con c),
    '4. contratto: le quattro marche sono le colonne del vocabolario dello stato corrente'
);

-- Contrasto sul seed: senza, il test 4 passerebbe anche con quattro chiavi
-- lette dalla stessa colonna.
SELECT is(
    concat_ws(', ', 'annullato ' || pg_temp.marche_cap('annullato'),
                    'cessato '   || pg_temp.marche_cap('cessato')),
    'annullato false false false true, cessato false false true true',
    '5. contrasto: l''annullato e'' solo terminale, il cessato cessazione e terminale'
);

-- ⭐ terminale non ha un indice unico: si toglie all'annullo e basta.
UPDATE config.stati_doc_contratti SET terminale = false WHERE codice_interno = 'ANNULLATO';

SELECT is(
    pg_temp.marche_cap('annullato'),
    'false false false false',
    '6. ⭐ terminale tolto all''annullo: stato_terminale lo segue'
);

UPDATE config.stati_doc_contratti SET terminale = true WHERE codice_interno = 'ANNULLATO';

-- ============================================================
-- 7-8. Il building block dello smistamento
-- ============================================================
SELECT is(
    (SELECT string_agg(format('%s/%s:%s', coalesce(a::text, 'NULL'), coalesce(s, 'NULL'),
                              vendite.fn_preventivo_in_smistamento(a, s)::text), ' ' ORDER BY n)
       FROM (VALUES (1, true,  'ACCETTATO'), (2, false, 'EVASO'),  (3, false, 'EMESSO'),
                    (4, false, 'RIFIUTATO'), (5, NULL,  NULL),     (6, NULL,  'EVASO'),
                    (7, true,  NULL)) v(n, a, s)),
    'true/ACCETTATO:true false/EVASO:true false/EMESSO:false false/RIFIUTATO:false NULL/NULL:false NULL/EVASO:true true/NULL:true',
    '7. building block: vero dallo stato di accettazione e da EVASO, falso altrove e con NULL (mai NULL)'
);

SELECT is(
    (SELECT format('%s %s', p.provolatile, p.proisstrict::text) FROM pg_proc p
      WHERE p.oid = 'vendite.fn_preventivo_in_smistamento(boolean, character varying)'::regprocedure),
    'i false',
    '8. building block: IMMUTABLE e non STRICT (un NULL e'' un caso, non un buco)'
);

-- ============================================================
-- 9-10. Il preventivo: in_smistamento
-- ============================================================
SELECT is(
    concat_ws(' ', pg_temp.smista('bozza'), pg_temp.smista('emesso'), pg_temp.smista('accettato')),
    'false false true',
    '9. preventivo: in_smistamento falso in bozza e nell''emesso, vero nell''accettato'
);

-- ⭐ L'accettazione sull'emesso: prima si spegne, poi si accende (indice unico).
UPDATE config.stati_doc_preventivi SET accettazione = false WHERE codice_interno = 'ACCETTATO';
UPDATE config.stati_doc_preventivi SET accettazione = true  WHERE codice_interno = 'EMESSO';

SELECT is(
    concat_ws(' ', pg_temp.smista('emesso'), pg_temp.smista('accettato')),
    'true false',
    '10. ⭐ accettazione spostata sull''emesso: in_smistamento la segue'
);

UPDATE config.stati_doc_preventivi SET accettazione = false WHERE codice_interno = 'EMESSO';
UPDATE config.stati_doc_preventivi SET accettazione = true  WHERE codice_interno = 'ACCETTATO';

-- ============================================================
-- 11-12. Forma: una sede per «il preventivo si smista»
-- ============================================================
-- Presidio sulla FORMA, dichiarato tale: il comportamento della proiezione lo
-- provano i suoi test (test-preventivo-stati-dal-vocabolario-v1).
SELECT ok(
    (SELECT d ~ 'vendite\.fn_preventivo_in_smistamento\(v_accettazione, v_stato\)'
        AND regexp_replace(d, '--[^\n]*', '', 'g') !~ 'v_accettazione\s+OR\s+v_stato\s*='
       FROM pg_get_functiondef('vendite.fn_preventivo_proietta_stato_smistamento(bigint)'::regprocedure) d),
    '11. forma: la proiezione parte dal building block e non riscrive il predicato'
);

SELECT ok(
    (SELECT d ~ 'vendite\.fn_preventivo_in_smistamento\(v_accettazione, v_stato_cod\)'
       FROM pg_get_functiondef('script.fn_available_actions_preventivo(bigint)'::regprocedure) d),
    '12. forma: la capability del preventivo legge il building block'
);

-- ============================================================
-- 13-18. Giro 6g-bis: i valori del motivo degli altri flag
-- ============================================================
-- Gli ordini: in bozza, confermato, evaso per intero da una bolla emessa.
CREATE TEMP TABLE t_ord (caso text PRIMARY KEY,   -- l'etichetta del test
                         id   bigint);            -- vendite.ordini.id

INSERT INTO t_ord
SELECT c.caso, r.ordine_id
  FROM (VALUES ('bozza', 'DRAFT'), ('conf', 'CONFERMATO')) c(caso, stato)
 CROSS JOIN LATERAL dbops.fn_pgtap_crea_ordine_con_righe('giro 6g-bis, ' || c.caso, c.stato,
                                                         p_fatturazione_trigger => 'CONFERMATO') r;
INSERT INTO t_ord
SELECT 'evaso', d.ordine_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('giro 6g-bis, evaso', 'EMESSO', p_quantita => 10,
                                         p_fatturazione_trigger => 'CONFERMATO') d;

CREATE FUNCTION pg_temp.cap_ord(p_caso text, p_chiave text)   -- text: etichetta e chiave del blob
RETURNS text LANGUAGE sql STABLE AS $$                        -- text: un valore del blob jsonb
    SELECT (script.fn_available_actions_ordine(t.id) -> p_chiave)::text FROM t_ord t WHERE t.caso = p_caso
$$;

SELECT is(
    concat_ws(' | ', pg_temp.cap_ord('bozza', 'can_genera_ddt'),
                     pg_temp.cap_ord('bozza', 'can_genera_ddt_reason_valori'),
                     pg_temp.cap_ord('conf', 'can_genera_ddt'),
                     pg_temp.cap_ord('conf', 'can_genera_ddt_reason_valori')),
    (SELECT concat_ws(' | ', 'false', jsonb_build_array(COALESCE(o.numero, o.id::text), 'DRAFT')::text,
                      'true', '[]')
       FROM vendite.ordini o WHERE o.id = (SELECT id FROM t_ord WHERE caso = 'bozza')),
    '13. ordine: can_genera_ddt in bozza coi valori della frase (numero, stato), vero e [] al confermato'
);

SELECT is(
    concat_ws(' | ', pg_temp.cap_ord('bozza', 'can_edit_data_consegna_confermata_reason'),
                     pg_temp.cap_ord('bozza', 'can_edit_data_consegna_confermata_reason_valori'),
                     pg_temp.cap_ord('conf', 'can_edit_data_consegna_confermata_reason_valori'),
                     pg_temp.cap_ord('evaso', 'can_edit_data_consegna_confermata_reason'),
                     pg_temp.cap_ord('evaso', 'can_edit_data_consegna_confermata_reason_valori')),
    (SELECT concat_ws(' | ', '"ORDINE_IN_BOZZA"', '[]', '[]', '"STATO_NON_AMMETTE"',
                      jsonb_build_array(
                          (SELECT t.etichetta FROM script.fn_get_stato_testata_documento('ORDINE_VENDITA', o.id) t),
                          s.codice_interno, 'modificare')::text)
       FROM vendite.ordini o
       JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
      WHERE o.id = (SELECT id FROM t_ord WHERE caso = 'evaso')),
    '14. ordine: la data di consegna, [] in bozza (motivo della capability) e al confermato, i valori della check sull''evaso'
);

-- Le offerte: un servizio a canone, che l'ordine non ammette; un consumo
-- manuale, che il vocabolario della natura poi esclude; una in bozza.
CREATE TEMP TABLE t_art (sigla text PRIMARY KEY,   -- l'etichetta dell'articolo
                         id    uuid);              -- catalogo.articoli.id

INSERT INTO t_art
SELECT v.sigla,
       dbops.fn_pgtap_crea_articolo(('PGT-6GB-' || v.sigla || substr(md5(clock_timestamp()::text), 1, 8))::varchar,
           p_natura_vendita_id => (SELECT n.id FROM config.nature_vendita n WHERE n.codice_interno = 'SERVIZIO_RICORRENTE'))
  FROM (VALUES ('S'), ('C')) v(sigla);

CREATE TEMP TABLE t_off (caso text PRIMARY KEY,   -- l'etichetta del test
                         id   bigint);            -- vendite.offerte_commerciali.id

INSERT INTO t_off
SELECT c.caso, o.offerta_id
  FROM (VALUES ('serv'), ('cons'), ('bozza')) c(caso)
 CROSS JOIN LATERAL dbops.fn_pgtap_crea_offerta('giro 6g-bis, ' || c.caso, 'BOZZA') o;

INSERT INTO vendite.offerte_commerciali_eccezioni (
    offerta_id, articolo_id, tipo_eccezione, prezzo_unitario,
    qta_operativa, tipo_erogazione, fonte_quantita_attesa, periodicita)
SELECT o.id, a.id, 'AGGIUNTA', 10, v.qta, v.erog, v.fonte, v.periodicita
  FROM (VALUES ('serv', 'S', 1::numeric, 'CANONE', 'FISSA', 'MENSILE'),
               ('cons', 'C', NULL,       'CONSUMO', 'MANUALE', NULL),
               ('bozza', 'S', 1::numeric, 'CANONE', 'FISSA', 'MENSILE')) v(caso, sigla, qta, erog, fonte, periodicita)
  JOIN t_off o ON o.caso = v.caso
  JOIN t_art a ON a.sigla = v.sigla;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali'::regclass, o.id, 'ACCETTATA')
  FROM t_off o WHERE o.caso IN ('serv', 'cons');

CREATE FUNCTION pg_temp.cap_off(p_caso text, p_chiave text)   -- text: etichetta e chiave del blob
RETURNS text LANGUAGE sql STABLE AS $$                        -- text: un valore del blob jsonb
    SELECT (script.fn_available_actions_offerta(t.id) -> p_chiave)::text FROM t_off t WHERE t.caso = p_caso
$$;

SELECT is(
    concat_ws(' | ', pg_temp.cap_off('serv', 'can_genera_ordine'),
                     pg_temp.cap_off('serv', 'can_genera_ordine_reason'),
                     pg_temp.cap_off('serv', 'can_genera_ordine_reason_valori'),
                     pg_temp.cap_off('serv', 'can_push_contratto'),
                     pg_temp.cap_off('serv', 'can_push_contratto_reason_valori')),
    (SELECT concat_ws(' | ', 'false', '"RIGA_NON_AMMESSA"',
                      jsonb_build_array('Ordine dall''offerta ' || COALESCE(o.codice, o.id::text), a.codice)::text,
                      'true', '[]')
       FROM vendite.offerte_commerciali o, catalogo.articoli a
      WHERE o.id = (SELECT id FROM t_off WHERE caso = 'serv')
        AND a.id = (SELECT id FROM t_art WHERE sigla = 'S')),
    '15. offerta accettata con un servizio: can_genera_ordine coi valori della frase, can_push_contratto vero e []'
);

SELECT is(
    concat_ws(' | ', pg_temp.cap_off('bozza', 'can_push_contratto_reason'),
                     pg_temp.cap_off('bozza', 'can_push_contratto_reason_valori'),
                     pg_temp.cap_off('bozza', 'can_genera_ordine_reason'),
                     pg_temp.cap_off('bozza', 'can_genera_ordine_reason_valori')),
    '"OFFERTA_NON_ACCETTATA" | [] | "OFFERTA_NON_ACCETTATA" | []',
    '16. offerta in bozza: i motivi della capability, senza valori (la check non si chiama)'
);

-- ⭐ Il dato fuori dalla riga: CONSUMO/MANUALE esce dal vocabolario della
-- natura, e la riga scritta non e' piu' ammessa nel contratto.
DELETE FROM config.nature_vendita_erogazioni ne
 USING config.nature_vendita n
 WHERE n.id = ne.natura_vendita_id
   AND n.codice_interno = 'SERVIZIO_RICORRENTE'
   AND ne.tipo_erogazione = 'CONSUMO'
   AND ne.fonte_quantita_attesa = 'MANUALE';

SELECT is(
    concat_ws(' | ', pg_temp.cap_off('cons', 'can_push_contratto'),
                     pg_temp.cap_off('cons', 'can_push_contratto_reason'),
                     pg_temp.cap_off('cons', 'can_push_contratto_reason_valori')),
    (SELECT concat_ws(' | ', 'false', '"RIGA_NON_AMMESSA"',
                      jsonb_build_array(
                          script.fn_articolo_riga_contesto('OFFERTA_COMMERCIALE', o.id,
                                                           'AGGIUNTA'::vendite.tipo_eccezione_contratto) ->> 'etichetta',
                          a.codice)::text)
       FROM vendite.offerte_commerciali o, catalogo.articoli a
      WHERE o.id = (SELECT id FROM t_off WHERE caso = 'cons')
        AND a.id = (SELECT id FROM t_art WHERE sigla = 'C')),
    '17. ⭐ riga fuori dal vocabolario della natura: can_push_contratto coi valori della frase (etichetta, codice)'
);

-- I documenti interni: un inventario in bozza e uno confermato senza righe.
CREATE TEMP TABLE t_inv (caso text PRIMARY KEY,   -- l'etichetta del test
                         id   bigint);            -- magazzino.inventari.id

-- ⚠️ Il magazzino nasce in un'istruzione sua: la policy degli inventari ne
-- legge l'emittente con una funzione STABLE, che vede lo snapshot
-- dell'istruzione; nella stessa istruzione il magazzino appena nato non c'e',
-- e sotto RLS la riga sarebbe rifiutata.
CREATE TEMP TABLE t_mag AS
SELECT dbops.fn_pgtap_crea_magazzino(('PGT-6GB-' || substr(md5(clock_timestamp()::text), 1, 8))::varchar) AS id;

WITH ins AS (INSERT INTO magazzino.inventari (magazzino_id)
             SELECT m.id FROM t_mag m CROSS JOIN generate_series(1, 2)
             RETURNING id)
INSERT INTO t_inv
SELECT CASE WHEN row_number() OVER (ORDER BY id) = 1 THEN 'bozza' ELSE 'vuoto' END, id FROM ins;

UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM'
 WHERE id = (SELECT id FROM t_inv WHERE caso = 'vuoto');

SELECT is(
    (SELECT string_agg(format('%s %s %s', t.caso, b -> 'can_registra', b -> 'can_registra_reason_valori'), ', '
                       ORDER BY t.caso)
       FROM t_inv t
      CROSS JOIN LATERAL script.fn_available_actions_documento_interno('INVENTARIO', t.id) b),
    format('bozza false ["DRAFT", "POSTED"], vuoto false [%s]',
           to_jsonb((SELECT id FROM t_inv WHERE caso = 'vuoto')::text)),
    '18. documento interno: can_registra coi valori della frase, in bozza (stato, destinazione) e confermato vuoto (id)'
);

SELECT * FROM finish();

ROLLBACK;
