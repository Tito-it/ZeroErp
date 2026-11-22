-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- L'ordine di acquisto porta il termine di pagamento, come quello di vendita
--   (20261121-04, brief-db-fornitore-doppioni-del-soggetto, giro B, D-3).
--
-- ⭐ Il contratto si legge dalla struttura e si confronta col gemello di
--   vendita, non con una costante: se vendite.ordini cambia forma, il test
--   dice che i due ordini si sono separati.
--
-- Elenco test (plan 4):
--   1) acquisti.ordini non ha piu' giorni_pagamento ne' fine_mese
--   2) termine_pagamento_id e' una FK su config.termini_pagamento(id)
--   3) ... con le stesse azioni (ON UPDATE, ON DELETE) della FK di vendite.ordini
--   4) ... e lo stesso tipo della colonna di vendite.ordini
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(4);

SELECT is(
    (SELECT COALESCE(array_agg(a.attname::text ORDER BY a.attname), '{}'::text[])
       FROM pg_catalog.pg_attribute a
      WHERE a.attrelid = 'acquisti.ordini'::regclass
        AND a.attnum > 0 AND NOT a.attisdropped
        AND a.attname IN ('giorni_pagamento', 'fine_mese')),
    '{}'::text[],
    '1. acquisti.ordini: giorni_pagamento e fine_mese ritirati');

SELECT fk_ok('acquisti', 'ordini', 'termine_pagamento_id',
             'config', 'termini_pagamento', 'id',
             '2. acquisti.ordini.termine_pagamento_id: FK su config.termini_pagamento(id)');

SELECT is(
    (SELECT format('%s|%s', c.confupdtype, c.confdeltype)
       FROM pg_catalog.pg_constraint c
       JOIN pg_catalog.pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
      WHERE c.conrelid = 'acquisti.ordini'::regclass AND c.contype = 'f'
        AND c.confrelid = 'config.termini_pagamento'::regclass
        AND a.attname = 'termine_pagamento_id'),
    -- L'atteso non e' mai NULL: senza la FK di riferimento su vendite.ordini
    -- i due lati sarebbero NULL (anche senza la FK di acquisti) e is() li
    -- darebbe uguali (verde a vuoto).
    COALESCE((SELECT format('%s|%s', c.confupdtype, c.confdeltype)
       FROM pg_catalog.pg_constraint c
       JOIN pg_catalog.pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
      WHERE c.conrelid = 'vendite.ordini'::regclass AND c.contype = 'f'
        AND c.confrelid = 'config.termini_pagamento'::regclass
        AND a.attname = 'termine_pagamento_id'), '<FK di riferimento assente su vendite.ordini>'),
    '3. la FK del termine ha le azioni di quella di vendite.ordini');

SELECT is(
    (SELECT format_type(a.atttypid, a.atttypmod) FROM pg_catalog.pg_attribute a
      WHERE a.attrelid = 'acquisti.ordini'::regclass AND a.attname = 'termine_pagamento_id'),
    -- Stesso presidio: senza la colonna di riferimento i due lati sarebbero NULL.
    COALESCE((SELECT format_type(a.atttypid, a.atttypmod) FROM pg_catalog.pg_attribute a
      WHERE a.attrelid = 'vendite.ordini'::regclass AND a.attname = 'termine_pagamento_id'),
             '<colonna di riferimento assente su vendite.ordini>'),
    '4. termine_pagamento_id ha il tipo della colonna di vendite.ordini');

SELECT * FROM finish();

ROLLBACK;
