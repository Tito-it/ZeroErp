-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la motivazione dell'offerta si accetta solo dove il passaggio la chiede
--   vendite.fn_cambia_stato_offerta (20261031-22).
--   Brief: brief-modello-documento-vendita §17.8, decisione (b) di Tid del
--   2026-10-31.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - su un passaggio della matrice che non chiede la motivazione
--     (requires_motivazione falso o assente), una motivazione non vuota e'
--     rifiutata con E_OFFERTA_MOTIVAZIONE_NON_AMMESSA, e niente si scrive;
--   - una motivazione di soli spazi e' «nessuna motivazione»: il passaggio va;
--   - dove la riga la chiede si scrive, come prima.
--
-- Elenco test (plan 5):
--   1) EMESSA -> ACCETTATA con una motivazione: rifiutato (E_OFFERTA_MOTIVAZIONE_NON_AMMESSA)
--   2) ... e l'offerta e' ancora EMESSA, senza motivazione scritta
--   3) EMESSA -> ACCETTATA con soli spazi: passa
--   4) EMESSA -> RIFIUTATA con la motivazione: passa, ed e' scritta
--   5) il codice e' registrato: classe DATO_ERRATO, non ritirato
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'emetti_offerta');

-- ── Fixture ─────────────────────────────────────────────────────────
-- Stampo: vendite/test-offerta-al-modello-v1. Due offerte emesse.
CREATE TEMP TABLE t_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'motivazione offerta',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE t_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_cli), 'motivazione offerta');

CREATE TEMP TABLE t_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-OFF-MOT-1') AS articolo_id;

CREATE FUNCTION pg_temp.t_offerta_emessa()
RETURNS bigint LANGUAGE plpgsql AS $f$
DECLARE
    v_id bigint;
BEGIN
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, revisione_numero)
    SELECT script.fn_pgtap_emittente_operatore(), c.billing_account_id, c.istanza_utility_id, c.utility_id,
           l.listino_id, l.listino_versione_id, DATE '2096-01-01', 1
      FROM t_cli c, t_listino l
    RETURNING id INTO v_id;

    INSERT INTO vendite.offerte_commerciali_utilities (offerta_id, istanza_utility_id, utility_id)
    SELECT v_id, c.istanza_utility_id, c.utility_id FROM t_cli c;

    INSERT INTO vendite.offerte_commerciali_eccezioni (
        offerta_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa,
        prezzo_unitario, attivo, qta_operativa)
    SELECT v_id, a.articolo_id, 'AGGIUNTA'::vendite.tipo_eccezione_contratto, 'UNA_TANTUM', 'FISSA',
           50.00, TRUE, 1.00
      FROM t_art a;

    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', v_id, 'EMESSA');
    RETURN v_id;
END
$f$;

CREATE TEMP TABLE t_a AS SELECT pg_temp.t_offerta_emessa() AS id;
CREATE TEMP TABLE t_r AS SELECT pg_temp.t_offerta_emessa() AS id;

-- 1-2) Una motivazione dove il passaggio non la chiede
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_offerta(%s, 'ACCETTATA', 'pgTAP: non va')$$, (SELECT id FROM t_a)),
    'Per portare l''offerta % nello stato % non si indica una motivazione.%',
    'EMESSA -> ACCETTATA con una motivazione: rifiutato (E_OFFERTA_MOTIVAZIONE_NON_AMMESSA)'
);

SELECT is(
    (SELECT s.codice_interno || ' ' || COALESCE(o.motivazione_rifiuto, 'NULL')
       FROM vendite.offerte_commerciali o
       JOIN config.stati_doc_offerte s ON s.id = o.stato_doc_offerta_id
      WHERE o.id = (SELECT id FROM t_a)),
    'EMESSA NULL',
    'dopo il rifiuto l''offerta e'' ancora EMESSA, senza motivazione scritta'
);

-- 3) Soli spazi: nessuna motivazione
SELECT is(
    (SELECT stato_nuovo::text
       FROM vendite.fn_cambia_stato_offerta((SELECT id FROM t_a), 'ACCETTATA', '   ')),
    'ACCETTATA',
    'EMESSA -> ACCETTATA con soli spazi: e'' nessuna motivazione, il passaggio va'
);

-- 4) Dove la riga la chiede, come prima. Il verbo in un'istruzione sua: una
--    lettura nella stessa istruzione non vedrebbe la riga che scrive.
CREATE TEMP TABLE t_esito AS
SELECT * FROM vendite.fn_cambia_stato_offerta((SELECT id FROM t_r), 'RIFIUTATA', 'pgTAP: il cliente rifiuta');

SELECT is(
    (SELECT e.stato_nuovo::text || ' ' || o.motivazione_rifiuto
       FROM t_esito e JOIN vendite.offerte_commerciali o ON o.id = e.offerta_id),
    'RIFIUTATA pgTAP: il cliente rifiuta',
    'EMESSA -> RIFIUTATA con la motivazione: passa, ed e'' scritta'
);

-- 5) Il codice a catalogo
SELECT is(
    (SELECT classe::text || ' ' || COALESCE(obsoleto_dal::text, 'NULL')
       FROM config.codici_errore WHERE codice = 'E_OFFERTA_MOTIVAZIONE_NON_AMMESSA'),
    'DATO_ERRATO NULL',
    'E_OFFERTA_MOTIVAZIONE_NON_AMMESSA a catalogo: DATO_ERRATO, in servizio'
);

SELECT * FROM finish();
ROLLBACK;
