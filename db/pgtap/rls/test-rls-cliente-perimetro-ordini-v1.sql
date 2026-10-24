-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-contesto: escluso — il file prova la veste CLIENTE_PORTALE, non l'operatore: il
--   contesto lo imposta a mano dentro il blocco $perimetro$, con l'identita' costruita.
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy. E la
--   fixture costruisce DUE aziende e una veste portale: un operatore dentro un
--   perimetro non potrebbe crearle. Stesso criterio di rls/test-rls-ordini-satelliti.
-- pgTAP test FUNZIONALE RLS — il cliente portale vede i PROPRI ordini
--   Brief: brief-db-perimetro-una-volta-famiglie-residue §7 (giro 3),
--   changeSet 20261021-33..-36.
--
-- ⭐ IL PUNTO DI QUESTO FILE. Le policy del cliente su ordini e satelliti
--   chiedono il perimetro dell'identita' una volta per istruzione
--   (script.fn_get_identita_sr_perimetro) e per riga il cliente della riga
--   (la colonna dell'ordine, o script.fn_resolve_controparte_sr_id coi modi
--   'ordine' e 'ordine_riga'). I test che c'erano provavano solo il NO (una
--   veste che non possiede l'ordine non vede niente): un perimetro che non
--   lasciasse vedere nulla a nessuno li avrebbe passati. Qui il SI' si
--   costruisce: un cliente con la sua veste CLIENTE_PORTALE e il suo ordine.
--
-- Elenco test (plan 9):
--  1) il risolutore, modo 'ordine': il cliente dell'ordine
--  2) il risolutore, modo 'ordine_riga': il cliente dell'ordine della riga
--  3) il risolutore su un ordine che non c'e': NULL
--  4) il perimetro della veste CLIENTE_PORTALE e' il suo soggetto
--  5) ⭐ la stessa identita' chiesta per la veste SHOP_CUSTOMER: NULL, perche'
--     la policy passa la veste del proprio gate
--  6) ⭐ il cliente A vede il PROPRIO ordine (policy rls_ordini_cliente_ownership)
--  7) ⭐ e la PROPRIA riga (rls_ordini_righe_cliente_ownership, modo 'ordine')
--  8) ⛔ e NON l'ordine ne' la riga del cliente B
--  9) ⛔ senza veste non vede niente: fail-closed
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, e qui il COMMIT non arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- Due aziende, un cliente per ciascuna, un ordine con una riga per cliente
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE _clienti AS
SELECT m.lato, m.emittente_fiscale_id, c.*
  FROM _mondi m
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba('RLS cliente ordini ' || m.lato, NULL, m.soggetto_ruolo_id) c;

-- ⛔ L'articolo si COSTRUISCE: su un database ricostruito il catalogo non ha merce.
CREATE TEMP TABLE _art AS
SELECT dbops.fn_pgtap_crea_articolo('PGTAP-RLS-CLI-ORD', false) AS id;

CREATE TEMP TABLE _ordini AS
WITH ord AS (
    INSERT INTO vendite.ordini
        (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id, fatturazione_trigger,
         emittente_fiscale_id)
    SELECT c.soggetto_ruolo_id, c.billing_account_id,
           (SELECT st.id FROM config.stati_doc_ordini st ORDER BY st.id LIMIT 1),
           'CONFERMATO',
           c.emittente_fiscale_id
      FROM _clienti c
    RETURNING id, emittente_fiscale_id, soggetto_ruolo_id
)
SELECT c.lato, o.id AS ordine_id, o.soggetto_ruolo_id
  FROM ord o JOIN _clienti c ON c.emittente_fiscale_id = o.emittente_fiscale_id;

CREATE TEMP TABLE _righe AS
WITH r AS (
    INSERT INTO vendite.ordini_righe
        -- ⚠️ `qta_operativa` va valorizzata insieme a `quantita`: un guard la pretende.
        (ordine_id, riga_nr, articolo_id, descrizione, quantita, qta_operativa, prezzo_unitario)
    SELECT o.ordine_id, 1, (SELECT id FROM _art), 'Riga pgTAP cliente', 1, 1, 100.00
      FROM _ordini o
    RETURNING id, ordine_id
)
SELECT o.lato, r.id AS riga_id, r.ordine_id FROM r JOIN _ordini o ON o.ordine_id = r.ordine_id;

-- La veste CLIENTE_PORTALE del cliente A, su una credenziale costruita.
CREATE TEMP TABLE _veste (auth_user_id int, identita_id bigint);
DO $veste$
DECLARE
    v_au int;
BEGIN
    INSERT INTO django.auth_user (
        username, password, is_active, is_staff, is_superuser,
        first_name, last_name, email, date_joined)
    VALUES ('_pgtap_cli_ord_' || substring(md5(clock_timestamp()::text) from 1 for 8),
            '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_au;
    INSERT INTO _veste
    SELECT v_au, anagrafiche.fn_crea_veste_portale(
               v_au, (SELECT soggetto_ruolo_id FROM _clienti WHERE lato = 'A'),
               'CLIENTE_PORTALE', true);
END
$veste$;

-- ============================================================
-- 1..5. I building block, chiesti direttamente
-- ============================================================
SELECT is(script.fn_resolve_controparte_sr_id('ordine', (SELECT ordine_id FROM _ordini WHERE lato = 'A')),
          (SELECT soggetto_ruolo_id FROM _clienti WHERE lato = 'A'),
          '1. il risolutore, modo ordine: il cliente dell''ordine');

SELECT is(script.fn_resolve_controparte_sr_id('ordine_riga', (SELECT riga_id FROM _righe WHERE lato = 'A')),
          (SELECT soggetto_ruolo_id FROM _clienti WHERE lato = 'A'),
          '2. il risolutore, modo ordine_riga: il cliente dell''ordine della riga');

SELECT is(script.fn_resolve_controparte_sr_id('ordine', -1), NULL::bigint,
          '3. il risolutore su un ordine che non c''e'': NULL');

SELECT is(script.fn_get_identita_sr_perimetro((SELECT identita_id FROM _veste),
                                              ARRAY['CLIENTE_PORTALE']::config.ruolo_applicativo[]),
          (SELECT soggetto_ruolo_id FROM _clienti WHERE lato = 'A'),
          '4. il perimetro della veste CLIENTE_PORTALE e'' il suo soggetto');

SELECT is(script.fn_get_identita_sr_perimetro((SELECT identita_id FROM _veste),
                                              ARRAY['SHOP_CUSTOMER']::config.ruolo_applicativo[]),
          NULL::bigint,
          '5. la stessa identita'' chiesta per la veste SHOP_CUSTOMER: NULL (la policy passa la veste del suo gate)');

-- ============================================================
-- 6..9. Il perimetro, esercitato dalle policy
-- ============================================================
-- FORCE locale alla transazione: senza, l'owner sarebbe esente e il test
-- misurerebbe tutto. Il ROLLBACK finale lo annulla.
ALTER TABLE vendite.ordini       FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.ordini_righe FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_a  record;
    v_b  record;
    v_n  integer;
BEGIN
    SELECT o.ordine_id, r.riga_id INTO v_a
      FROM _ordini o JOIN _righe r ON r.ordine_id = o.ordine_id WHERE o.lato = 'A';
    SELECT o.ordine_id, r.riga_id INTO v_b
      FROM _ordini o JOIN _righe r ON r.ordine_id = o.ordine_id WHERE o.lato = 'B';

    -- La veste del cliente A, come la darebbe il middleware.
    PERFORM set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);
    PERFORM set_config('app.current_identita_id', (SELECT identita_id FROM _veste)::text, true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _veste)::text, true);

    SELECT count(*) INTO v_n FROM vendite.ordini o WHERE o.id = v_a.ordine_id;
    PERFORM set_config('pgtap.ordine_a', v_n::text, true);
    SELECT count(*) INTO v_n FROM vendite.ordini_righe r WHERE r.id = v_a.riga_id;
    PERFORM set_config('pgtap.riga_a', v_n::text, true);
    SELECT (SELECT count(*) FROM vendite.ordini o WHERE o.id = v_b.ordine_id)
         + (SELECT count(*) FROM vendite.ordini_righe r WHERE r.id = v_b.riga_id)
      INTO v_n;
    PERFORM set_config('pgtap.di_b', v_n::text, true);

    -- ⛔ Nessuna veste: fail-closed.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    SELECT (SELECT count(*) FROM vendite.ordini o WHERE o.id IN (v_a.ordine_id, v_b.ordine_id))
         + (SELECT count(*) FROM vendite.ordini_righe r WHERE r.id IN (v_a.riga_id, v_b.riga_id))
      INTO v_n;
    PERFORM set_config('pgtap.senza_veste', v_n::text, true);

    PERFORM set_config('app.current_identita_id', '', true);
    PERFORM set_config('app.current_user_id', '', true);
END
$perimetro$;

ALTER TABLE vendite.ordini_righe NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.ordini       NO FORCE ROW LEVEL SECURITY;

SELECT is(current_setting('pgtap.ordine_a', true), '1',
          '6. il cliente A vede il proprio ordine');

SELECT is(current_setting('pgtap.riga_a', true), '1',
          '7. e la riga del proprio ordine');

SELECT is(current_setting('pgtap.di_b', true), '0',
          '8. e NON l''ordine ne'' la riga del cliente B');

SELECT is(current_setting('pgtap.senza_veste', true), '0',
          '9. senza veste non vede niente: fail-closed');

SELECT * FROM finish();
ROLLBACK;
