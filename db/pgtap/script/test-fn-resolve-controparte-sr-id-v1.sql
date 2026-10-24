-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_resolve_controparte_sr_id(modo, chiave) — di quale
--   controparte e' una riga, per ogni modo.
--   Brief: brief-db-perimetro-una-volta-famiglie-residue §6, §7, §8
--   (changeSet 20261021-30, -33, -37; prende il posto di
--   script/test-fn-scope-ba-ownership-via-fattura, ritirato con la funzione dal
--   20261021-40, che i casi li PESCAVA fra le fatture esistenti).
--
-- ⛔ SI COSTRUISCE TUTTO: un cliente con due billing account (uno nato da
--   ADMIN, uno dallo SHOP), una fattura con il suo invio SDI, due ordini (uno
--   ADMIN e uno SHOP) con una riga ciascuno. Ogni modo si prova nei due versi
--   dove ce ne sono due: un modo che rispondesse sempre lo stesso soggetto
--   passerebbe i soli casi positivi.
--
-- Indice test (plan 13):
--    1. billing_account -> il cliente del BA
--    2. ⭐ billing_account_shop sul BA nato dallo shop -> il cliente
--    3. ⛔ billing_account_shop sul BA nato da ADMIN -> NULL
--    4. fattura -> il cliente del BA della fattura
--    5. fattura_sdi -> quello della sua fattura
--    6. ordine -> il cliente dell'ordine
--    7. ordine_riga -> quello del suo ordine
--    8. ⭐ ordine_shop sull'ordine nato dallo shop -> il cliente
--    9. ⛔ ordine_shop sull'ordine nato da ADMIN -> NULL
--   10. ⭐ ordine_riga_shop sulla riga dell'ordine shop -> il cliente
--   11. ⛔ ordine_riga_shop sulla riga dell'ordine ADMIN -> NULL
--   12. chiave NULL -> NULL, per qualunque modo
--   13. ⛔ un modo sconosciuto SOLLEVA (non risponde NULL)
-- BEGIN; + rollback a fine file.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, e qui il COMMIT non arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS).
-- Il risolutore e' DEFINER: risponde lo stesso, ed e' cio' che serve alle policy.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(13);

-- ============================================================
-- La fixture
-- ============================================================
-- La fattura porta con se' azienda, cliente e billing account (nato da ADMIN).
CREATE TEMP TABLE _f AS SELECT * FROM dbops.fn_pgtap_crea_fattura('PGTAP-CONTROPARTE');

CREATE TEMP TABLE _sdi AS
WITH s AS (
    INSERT INTO vendite.fatture_sdi (fattura_id, stato_sdi_id)
    SELECT f.fattura_id, (SELECT st.id FROM config.stati_sdi st ORDER BY st.id LIMIT 1)
      FROM _f f
    RETURNING id
)
SELECT id AS sdi_id FROM s;

-- ⛔ Il secondo billing account NASCE dallo shop: canale_origine e' immutabile
--   dopo l'INSERT. Stesso cliente, altra istanza (uq_billing_instance_utility)
--   e altra utility (un cliente per soggetto, utility e azienda). ⭐ Vincoli
--   differiti per la sola costruzione, come rls/test-rls-clienti: l'istanza
--   fittizia verifica al COMMIT di avere il suo satellite.
SET CONSTRAINTS ALL DEFERRED;

CREATE TEMP TABLE _ba_shop AS
WITH iu AS (
    INSERT INTO anagrafiche.istanze_utilities (codice, soggetto_id, fittizia)
    SELECT 'PGTAP-CTP-SHOP-' || left(md5(random()::text), 8), sr.soggetto_id, TRUE
      FROM _f f JOIN anagrafiche.soggetti_ruoli sr ON sr.id = f.cliente_soggetto_ruolo_id
    RETURNING id
), nuovo AS (
    INSERT INTO anagrafiche.billing_account
        (istanza_utility_id, soggetto_ruolo_id, utility_id, codice,
         categoria_cliente_id, valuta_id, canale_origine)
    SELECT iu.id, ba.soggetto_ruolo_id,
           (SELECT u.id FROM config.utilities u
             WHERE u.richiede_pdp IS FALSE AND u.id <> ba.utility_id
             ORDER BY u.id LIMIT 1),
           left(ba.codice, 40) || '-SHOP', ba.categoria_cliente_id, ba.valuta_id,
           'SHOP'::config.canale_origine
      FROM iu CROSS JOIN _f f
      JOIN anagrafiche.billing_account ba ON ba.id = f.billing_account_id
    RETURNING id
)
SELECT id AS billing_account_id FROM nuovo;

SET CONSTRAINTS ALL IMMEDIATE;

-- ⛔ L'articolo si COSTRUISCE: su un database ricostruito il catalogo non ha merce.
CREATE TEMP TABLE _art AS
SELECT dbops.fn_pgtap_crea_articolo('PGTAP-CONTROPARTE', false) AS id;

-- Due ordini del cliente: uno da ADMIN, uno dallo SHOP (canale immutabile:
-- nasce cosi').
CREATE TEMP TABLE _ord AS
WITH o AS (
    INSERT INTO vendite.ordini
        (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id, fatturazione_trigger,
         emittente_fiscale_id, canale_origine)
    SELECT f.cliente_soggetto_ruolo_id, f.billing_account_id,
           (SELECT st.id FROM config.stati_doc_ordini st ORDER BY st.id LIMIT 1),
           'CONFERMATO', f.emittente_fiscale_id, c.canale
      FROM _f f
      CROSS JOIN (VALUES ('ADMIN'::config.canale_origine), ('SHOP'::config.canale_origine)) c(canale)
    RETURNING id, canale_origine
)
SELECT o.canale_origine AS canale, o.id AS ordine_id FROM o;

CREATE TEMP TABLE _righe AS
WITH r AS (
    INSERT INTO vendite.ordini_righe
        -- ⚠️ `qta_operativa` va valorizzata insieme a `quantita`: un guard la pretende.
        (ordine_id, riga_nr, articolo_id, descrizione, quantita, qta_operativa, prezzo_unitario)
    SELECT o.ordine_id, 1, (SELECT id FROM _art), 'Riga pgTAP controparte', 1, 1, 10.00
      FROM _ord o
    RETURNING id, ordine_id
)
SELECT o.canale, r.id AS riga_id FROM r JOIN _ord o ON o.ordine_id = r.ordine_id;

-- ============================================================
-- 1..3. Il billing account
-- ============================================================
SELECT is(script.fn_resolve_controparte_sr_id('billing_account', (SELECT billing_account_id FROM _f)),
          (SELECT cliente_soggetto_ruolo_id FROM _f),
          '1. billing_account -> il cliente del BA');

SELECT is(script.fn_resolve_controparte_sr_id('billing_account_shop', (SELECT billing_account_id FROM _ba_shop)),
          (SELECT cliente_soggetto_ruolo_id FROM _f),
          '2. billing_account_shop sul BA nato dallo shop -> il cliente');

SELECT is(script.fn_resolve_controparte_sr_id('billing_account_shop', (SELECT billing_account_id FROM _f)),
          NULL::bigint,
          '3. billing_account_shop sul BA nato da ADMIN -> NULL');

-- ============================================================
-- 4..5. La fattura e il suo invio
-- ============================================================
SELECT is(script.fn_resolve_controparte_sr_id('fattura', (SELECT fattura_id FROM _f)),
          (SELECT cliente_soggetto_ruolo_id FROM _f),
          '4. fattura -> il cliente del BA della fattura');

SELECT is(script.fn_resolve_controparte_sr_id('fattura_sdi', (SELECT sdi_id FROM _sdi)),
          (SELECT cliente_soggetto_ruolo_id FROM _f),
          '5. fattura_sdi -> quello della sua fattura');

-- ============================================================
-- 6..11. Gli ordini
-- ============================================================
SELECT is(script.fn_resolve_controparte_sr_id('ordine', (SELECT ordine_id FROM _ord WHERE canale = 'ADMIN')),
          (SELECT cliente_soggetto_ruolo_id FROM _f),
          '6. ordine -> il cliente dell''ordine');

SELECT is(script.fn_resolve_controparte_sr_id('ordine_riga', (SELECT riga_id FROM _righe WHERE canale = 'ADMIN')),
          (SELECT cliente_soggetto_ruolo_id FROM _f),
          '7. ordine_riga -> quello del suo ordine');

SELECT is(script.fn_resolve_controparte_sr_id('ordine_shop', (SELECT ordine_id FROM _ord WHERE canale = 'SHOP')),
          (SELECT cliente_soggetto_ruolo_id FROM _f),
          '8. ordine_shop sull''ordine nato dallo shop -> il cliente');

SELECT is(script.fn_resolve_controparte_sr_id('ordine_shop', (SELECT ordine_id FROM _ord WHERE canale = 'ADMIN')),
          NULL::bigint,
          '9. ordine_shop sull''ordine nato da ADMIN -> NULL');

SELECT is(script.fn_resolve_controparte_sr_id('ordine_riga_shop', (SELECT riga_id FROM _righe WHERE canale = 'SHOP')),
          (SELECT cliente_soggetto_ruolo_id FROM _f),
          '10. ordine_riga_shop sulla riga dell''ordine shop -> il cliente');

SELECT is(script.fn_resolve_controparte_sr_id('ordine_riga_shop', (SELECT riga_id FROM _righe WHERE canale = 'ADMIN')),
          NULL::bigint,
          '11. ordine_riga_shop sulla riga dell''ordine ADMIN -> NULL');

-- ============================================================
-- 12..13. I bordi
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM unnest(ARRAY['billing_account', 'billing_account_shop', 'fattura', 'fattura_sdi',
                                             'ordine', 'ordine_riga', 'ordine_shop', 'ordine_riga_shop']) m
      WHERE script.fn_resolve_controparte_sr_id(m, NULL) IS NOT NULL),
    0,
    '12. chiave NULL -> NULL, per qualunque modo');

SELECT throws_like(
    $$SELECT script.fn_resolve_controparte_sr_id('modo_che_non_esiste', 1)$$,
    '%modo di risoluzione della controparte%non esiste%',
    '13. un modo sconosciuto SOLLEVA, non risponde NULL');

SELECT * FROM finish();
ROLLBACK;
