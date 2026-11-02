-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la revisione dell'offerta nel lineage (arco V)
--   vendite.fn_documento_lineage_archi (20261031-23), il legame
--   (vendite.fn_documento_lineage_legami, 20261031-24), la sintesi che lo
--   scarta (vendite.fn_documento_lineage_sintesi, 20261031-25) e le origini
--   della fattura che non lo risalgono (vendite.fn_fattura_origini, 20261031-26).
--   Brief: brief-modello-documento-vendita §17.7 e §18 (Tid 2026-10-31).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - una revisione e' un arco V dalla madre alla figlia, nei due modi del
--     lettore degli archi: grafo intero e seme (uscente dalla madre, entrante
--     nella figlia, una volta sola se il seme le ha entrambe);
--   - il pannello «Passaggi» lo mostra: indietro dalla figlia c'e' la madre,
--     col suo numero (e' da qui che la finestra dell'annullo prende il nome);
--   - il legame e' di sola testata: mai ritirato con i due nodi vivi;
--   - la sintesi non lo conta: la madre superata non ha discendenti e non e'
--     transitata, la figlia non ha sorgenti ne' radice;
--   - le origini della fattura non lo risalgono.
--
-- Elenco test (plan 9):
--   1) grafo intero: l'arco V madre -> figlia c'e', una volta
--   2) seme sulla madre: l'arco V uscente
--   3) seme sulla figlia: l'arco V entrante
--   4) seme con madre e figlia: l'arco V una volta sola
--   5) «Passaggi» indietro dalla figlia: la madre col suo numero, arco V
--   6) il legame V con i due nodi vivi: non ritirato (false, non NULL)
--   7) sintesi della madre: nessun discendente, non transitata
--   8) sintesi della figlia: nessuna sorgente, nessuna radice
--   9) presidio sulla forma: fn_fattura_origini non risale l'arco V
--
-- ⚠️ Il test 9 legge il corpo, ed e' un presidio sulla forma dichiarato:
--   costruire una fattura che arriva da un contratto nato da una revisione
--   chiede l'intera pipeline (commessa, lotto, numerazione) per provare una
--   condizione di una riga. Il comportamento del lineage che la fattura legge
--   lo provano i test 1-5.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'emetti_offerta');

-- ── Fixture ─────────────────────────────────────────────────────────
-- Stampo: vendite/test-offerta-al-modello-v1. Una madre emessa, la sua
-- revisione in bozza (la madre passa a superata).
CREATE TEMP TABLE t_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'revisione nel lineage',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE t_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_cli), 'revisione nel lineage');

CREATE TEMP TABLE t_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-OFF-LIN-V') AS articolo_id;

CREATE TEMP TABLE t_madre AS
WITH o AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, revisione_numero)
    SELECT script.fn_pgtap_emittente_operatore(), c.billing_account_id, c.istanza_utility_id, c.utility_id,
           l.listino_id, l.listino_versione_id, DATE '2096-01-01', 1
      FROM t_cli c, t_listino l
    RETURNING id, uid
)
SELECT * FROM o;

INSERT INTO vendite.offerte_commerciali_utilities (offerta_id, istanza_utility_id, utility_id)
SELECT m.id, c.istanza_utility_id, c.utility_id FROM t_madre m, t_cli c;

INSERT INTO vendite.offerte_commerciali_eccezioni (
    offerta_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa,
    prezzo_unitario, attivo, qta_operativa)
SELECT m.id, a.articolo_id, 'AGGIUNTA'::vendite.tipo_eccezione_contratto, 'UNA_TANTUM', 'FISSA',
       50.00, TRUE, 1.00
  FROM t_madre m, t_art a;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', (SELECT id FROM t_madre), 'EMESSA') AS stato;

-- Il verbo in un'istruzione sua: in una WHERE girerebbe per ogni riga scandita.
CREATE TEMP TABLE t_rev AS
SELECT vendite.fn_crea_revisione_offerta((SELECT id FROM t_madre), NULL) AS id;

CREATE TEMP TABLE t_figlia AS
SELECT oc.id, oc.uid FROM vendite.offerte_commerciali oc WHERE oc.id = (SELECT id FROM t_rev);

CREATE TEMP TABLE t_k AS
SELECT s.id AS tipo,
       (SELECT uid::text FROM t_madre)  AS u_madre,
       (SELECT uid::text FROM t_figlia) AS u_figlia,
       (SELECT o.codice FROM vendite.offerte_commerciali o WHERE o.id = (SELECT id FROM t_madre)) AS cod_madre
  FROM config.sorgenti s
 WHERE s.codice_interno = 'OFFERTA_COMMERCIALE';

-- 1) Grafo intero
SELECT is(
    (SELECT count(*)::integer
       FROM vendite.fn_documento_lineage_archi() a, t_k k
      WHERE a.arco = 'V' AND a.from_tipo_id = k.tipo AND a.from_uid = k.u_madre
        AND a.to_tipo_id = k.tipo AND a.to_uid = k.u_figlia),
    1,
    'grafo intero: l''arco V dalla madre alla figlia, una volta'
);

-- 2-4) Col seme
SELECT is(
    (SELECT count(*)::integer
       FROM t_k k, vendite.fn_documento_lineage_archi(ARRAY[k.tipo], ARRAY[k.u_madre]) a
      WHERE a.arco = 'V' AND a.to_uid = k.u_figlia),
    1,
    'seme sulla madre: l''arco V uscente verso la figlia'
);

SELECT is(
    (SELECT count(*)::integer
       FROM t_k k, vendite.fn_documento_lineage_archi(ARRAY[k.tipo], ARRAY[k.u_figlia]) a
      WHERE a.arco = 'V' AND a.from_uid = k.u_madre),
    1,
    'seme sulla figlia: l''arco V entrante dalla madre'
);

SELECT is(
    (SELECT count(*)::integer
       FROM t_k k, vendite.fn_documento_lineage_archi(ARRAY[k.tipo, k.tipo], ARRAY[k.u_madre, k.u_figlia]) a
      WHERE a.arco = 'V'),
    1,
    'seme con madre e figlia: l''arco V una volta sola'
);

-- 5) Il pannello «Passaggi», indietro dalla figlia
SELECT is(
    (SELECT string_agg(l.arco || ':' || l.from_codice, ',')
       FROM t_k k, vendite.fn_documento_lineage(k.tipo, k.u_figlia, 'indietro') l),
    (SELECT 'V:' || cod_madre FROM t_k),
    '«Passaggi» indietro dalla figlia: la madre col suo numero, dall''arco V'
);

-- 6) Il legame
SELECT is(
    (SELECT l.is_legame_ritirato
       FROM t_k k, vendite.fn_documento_lineage(k.tipo, k.u_figlia, 'indietro') l
      WHERE l.arco = 'V'),
    false,
    'il legame V con madre e figlia vive: non ritirato (censito, non NULL)'
);

-- 7-8) La sintesi non lo conta
SELECT is(
    (SELECT s.n_discendenti_diretti::text || ' ' || COALESCE(s.is_transitato::text, 'NULL')
       FROM t_k k, vendite.fn_documento_lineage_sintesi(ARRAY[k.tipo], ARRAY[k.u_madre]) s),
    '0 false',
    'sintesi della madre superata: nessun discendente, non transitata (la revisione non e'' un passaggio)'
);

SELECT is(
    (SELECT s.n_sorgenti::text || ' ' || COALESCE(s.root_uid, 'NULL')
       FROM t_k k, vendite.fn_documento_lineage_sintesi(ARRAY[k.tipo], ARRAY[k.u_figlia]) s),
    '0 NULL',
    'sintesi della figlia: nessuna sorgente, nessuna radice'
);

-- 9) Presidio sulla forma (dichiarato in testa)
SELECT ok(
    (SELECT p.prosrc ~ 'l\.arco\s+NOT\s+IN\s*\(\s*''G''\s*,\s*''V''\s*\)'
       FROM pg_proc p
      WHERE p.oid = 'vendite.fn_fattura_origini(bigint)'::regprocedure),
    'fn_fattura_origini: la risalita non passa dall''arco V (ne'' da G)'
);

SELECT * FROM finish();
ROLLBACK;
