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
--   - una commessa che non esiste parla.
--
-- Elenco test (plan 6):
--   1) la funzione esiste con la firma dichiarata
--   2) l'attivita' esiste sulla commessa, APPROVATA e NON_EMESSA
--   3) istanza di utility del billing account, competenza della commessa
--   4) prezzo: default 10, e quello chiesto quando lo si passa
--   5) l'emissione prende le attivita' del builder (una riga fatturabile
--      per attivita')
--   6) guard: una commessa che non esiste parla
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre il builder della commessa,
--   chiamato come lo chiamera' un file su un database ricostruito.

SELECT plan(6);

-- 1) La firma
SELECT has_function(
    'dbops', 'fn_pgtap_crea_commessa_attivita',
    ARRAY['bigint', 'numeric'],
    'dbops.fn_pgtap_crea_commessa_attivita(bigint, numeric) esiste con la firma dichiarata'
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

SELECT * FROM finish();
ROLLBACK;
