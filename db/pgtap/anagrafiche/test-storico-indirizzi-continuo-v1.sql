-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: lo storico continuo di indirizzi, civici e vie
--   anagrafiche.indirizzi · anagrafiche.indirizzi_dettaglio · config.stradario
--   script.trgfn_storico_generic · config.storico_set_storicizza
-- ChangeSet: 20261123-38, -39, -40, -41
-- Brief: brief-db-revisione-anagrafiche §18 (Q7 riaperta, strada (b), giro 1)
--
-- Elenco test (plan 16):
--  1-3)  ⭐ storicizza ha DEFAULT true sulle tre tabelle
--  4)    ⭐ le tre tabelle sono nel registro dello storico, come decisione
--        (insert_manuale = true: la sync settimanale non le pota)
--  -- la via (config.stradario) --
--  5)    una via nuova, scritta senza il flag, nasce accesa
--  6)    ⭐ due modifiche lasciano la versione di partenza e due versioni
--  7)    ⭐ dopo le modifiche il flag e' ancora acceso (prima il trigger lo
--        spegneva, e la seconda modifica non lasciava traccia)
--  8)    ⭐ la cancellazione lascia la sua versione
--  -- il civico (anagrafiche.indirizzi_dettaglio) --
--  9)    il civico fabbricato dal building block del dominio nasce acceso
--  10)   ⭐ due modifiche: partenza e due versioni
--  11)   ⭐ la cancellazione dopo le modifiche lascia la sua versione (il
--        trigger guarda il flag SALVATO, che ora resta acceso)
--  -- l'indirizzo di ruolo (anagrafiche.indirizzi) --
--  12)   fixture: il ruolo ha un indirizzo (dal builder o dalla madre)
--  13)   l'indirizzo scritto dalla madre del dominio nasce acceso
--  14)   ⭐ due modifiche: partenza e due versioni
--  15)   ⭐ dopo le modifiche il flag e' ancora acceso
--  16)   una scrittura che passa false non lascia traccia: il flag resta il
--        modo di chi scrive di dire «questa no»
--
-- ⚠️ Le modifiche sono UPDATE che riscrivono una colonna col suo valore: lo
--   storico registra ogni UPDATE, non solo quelli che cambiano un valore, e
--   cosi' il test non dipende dai guard di forma dell'indirizzo.
-- ⚠️ La cancellazione dell'indirizzo di ruolo non si prova: se il tipo e'
--   obbligatorio per il ruolo, il guard degli obbligatori la rifiuta, e la
--   fixture non sceglie il tipo. Il meccanismo e' lo stesso trigger provato
--   sulla via e sul civico (8, 11).
-- ⚠️ La fixture si FABBRICA: via, civico, soggetto, ruolo e indirizzo nascono
--   qui. Dal seed si prendono solo comune, stradario generale e codice
--   postale di una via qualunque, come ancora.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- I builder del soggetto e del ruolo aprono e richiudono da se' la finestra
-- dei differiti.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- ============================================================
-- 1-4. La struttura: il default e il registro
-- ============================================================
SELECT col_default_is('anagrafiche', 'indirizzi', 'storicizza', 'true',
    '1) anagrafiche.indirizzi.storicizza ha DEFAULT true');
SELECT col_default_is('anagrafiche', 'indirizzi_dettaglio', 'storicizza', 'true',
    '2) anagrafiche.indirizzi_dettaglio.storicizza ha DEFAULT true');
SELECT col_default_is('config', 'stradario', 'storicizza', 'true',
    '3) config.stradario.storicizza ha DEFAULT true');

SELECT is(
    (SELECT count(*)::integer
       FROM config.storico_set_storicizza
      WHERE table_name IN ('anagrafiche.indirizzi', 'anagrafiche.indirizzi_dettaglio', 'config.stradario')
        AND insert_manuale),
    3,
    '4) le tre tabelle sono nel registro dello storico, come decisione');

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _f ON COMMIT DROP AS
SELECT NULL::integer AS via_id,
       NULL::bigint  AS civico_id,
       NULL::uuid    AS soggetto_id,
       NULL::bigint  AS ruolo_id,
       NULL::bigint  AS indirizzo_id;

-- La via: su uno stradario generale nuovo (comune, via generale e CAP sono
-- una chiave unica), scritta SENZA il flag, che deve prendere dal default.
-- Toponimo e via generale come in maintenance/test-bump-toponomastica-v1.
ALTER TABLE _f ADD COLUMN topo_id integer, ADD COLUMN sg_id integer;

WITH ins AS (
    INSERT INTO config.toponomastica (descrizione, stato_id, attivo)
    VALUES ('PGTAP STORICO ' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSUS'),
            (SELECT id FROM config.stati ORDER BY id LIMIT 1), true)
    RETURNING id
)
UPDATE _f SET topo_id = (SELECT id FROM ins);

WITH ins AS (
    INSERT INTO config.stradario_generale (toponomastica_id, descrizione, descrizione_breve)
    SELECT f.topo_id, 'PGTAP STRADA STORICO', 'PGTAPSTOR'
      FROM _f f
    RETURNING id
)
UPDATE _f SET sg_id = (SELECT id FROM ins);

WITH ancora AS (
    SELECT s.comune_id, s.codice_postale_id
      FROM config.stradario s
     ORDER BY s.id
     LIMIT 1
), ins AS (
    INSERT INTO config.stradario (comune_id, stradario_generale_id, codice_postale_id)
    SELECT a.comune_id, f.sg_id, a.codice_postale_id
      FROM ancora a CROSS JOIN _f f
    RETURNING id
)
UPDATE _f SET via_id = (SELECT id FROM ins);

-- Il civico: dal building block del dominio, come un indirizzo vero.
UPDATE _f SET civico_id = dbops.fn_pgtap_crea_indirizzo_dettaglio('pgTAPstor');

-- Il soggetto e il ruolo cliente, coi loro indirizzi obbligatori.
UPDATE _f SET soggetto_id = dbops.fn_pgtap_crea_soggetto_pg('pgTAP storico indirizzi', 3,
                                                           script.fn_stato_id_da_iso2('IT'));
UPDATE _f SET ruolo_id = dbops.fn_pgtap_crea_soggetto_ruolo(soggetto_id, 'CL',
                                                            script.fn_stato_id_da_iso2('IT'));

-- L'indirizzo del ruolo: quello che il builder ha scritto, se il ruolo ne
-- pretende; altrimenti uno nuovo dalla madre, del primo tipo che il picker
-- del ruolo propone, nella forma libera che il guard pretende per l'Italia.
DO $fx$
DECLARE
    v_ruolo  bigint;
    v_tipo   integer;
    v_it     integer := script.fn_stato_id_da_iso2('IT');
    f        record;
BEGIN
    SELECT ruolo_id INTO v_ruolo FROM _f;

    IF NOT EXISTS (SELECT 1 FROM anagrafiche.indirizzi i WHERE i.soggetto_ruolo_id = v_ruolo) THEN
        SELECT p.tipo_indirizzo_id INTO v_tipo
          FROM anagrafiche.fn_tipi_indirizzo_proponibili_ruolo(v_ruolo, NULL) p
         WHERE p.ammesso
         ORDER BY p.tipo_indirizzo_id
         LIMIT 1;
        SELECT * INTO f FROM dbops.fn_pgtap_indirizzo_libero_forma(v_it);
        IF v_tipo IS NOT NULL THEN
            PERFORM anagrafiche.fn_crea_indirizzi_ruolo(
                v_ruolo,
                jsonb_build_array(jsonb_strip_nulls(jsonb_build_object(
                    'tipo_indirizzo_id', v_tipo,
                    'indirizzo_libero',  'Via pgTAP storico 1',
                    'stato_id',          v_it,
                    'comune_id',         f.comune_id,
                    'codice_postale_id', f.codice_postale_id,
                    'locality',          f.locality,
                    'postal_code',       f.postal_code))));
        END IF;
    END IF;

    UPDATE _f SET indirizzo_id = (SELECT i.id
                                    FROM anagrafiche.indirizzi i
                                   WHERE i.soggetto_ruolo_id = v_ruolo
                                   ORDER BY i.id
                                   LIMIT 1);
END
$fx$;

-- Le versioni di una riga si leggono nell'ordine in cui sono nate:
-- 1 partenza, 2 modifica, 3 cancellazione.

-- ============================================================
-- 5-8. La via
-- ============================================================
SELECT ok((SELECT s.storicizza FROM config.stradario s JOIN _f ON _f.via_id = s.id),
    '5) una via scritta senza il flag nasce accesa');

UPDATE config.stradario SET meta = meta WHERE id = (SELECT via_id FROM _f);
UPDATE config.stradario SET meta = meta WHERE id = (SELECT via_id FROM _f);

SELECT is(
    (SELECT string_agg(h.tipo_operazione::text, ',' ORDER BY h.id)
       FROM storico.stradario h JOIN _f ON _f.via_id = h.stradario_id
      WHERE h.origine_schema = 'config'),
    '1,2,2',
    '6) due modifiche della via: la versione di partenza e due versioni');

SELECT ok((SELECT s.storicizza FROM config.stradario s JOIN _f ON _f.via_id = s.id),
    '7) dopo le modifiche il flag della via e'' ancora acceso');

DELETE FROM config.stradario WHERE id = (SELECT via_id FROM _f);

SELECT is(
    (SELECT string_agg(h.tipo_operazione::text, ',' ORDER BY h.id)
       FROM storico.stradario h JOIN _f ON _f.via_id = h.stradario_id
      WHERE h.origine_schema = 'config'),
    '1,2,2,3',
    '8) la cancellazione della via lascia la sua versione');

-- ============================================================
-- 9-11. Il civico
-- ============================================================
SELECT ok((SELECT d.storicizza FROM anagrafiche.indirizzi_dettaglio d JOIN _f ON _f.civico_id = d.id),
    '9) il civico fabbricato dal building block nasce acceso');

UPDATE anagrafiche.indirizzi_dettaglio SET civico = civico WHERE id = (SELECT civico_id FROM _f);
UPDATE anagrafiche.indirizzi_dettaglio SET civico = civico WHERE id = (SELECT civico_id FROM _f);

SELECT is(
    (SELECT string_agg(h.tipo_operazione::text, ',' ORDER BY h.id)
       FROM storico.indirizzi_dettaglio h JOIN _f ON _f.civico_id = h.indirizzi_dettaglio_id
      WHERE h.origine_schema = 'anagrafiche'),
    '1,2,2',
    '10) due modifiche del civico: la versione di partenza e due versioni');

DELETE FROM anagrafiche.indirizzi_dettaglio WHERE id = (SELECT civico_id FROM _f);

SELECT is(
    (SELECT string_agg(h.tipo_operazione::text, ',' ORDER BY h.id)
       FROM storico.indirizzi_dettaglio h JOIN _f ON _f.civico_id = h.indirizzi_dettaglio_id
      WHERE h.origine_schema = 'anagrafiche'),
    '1,2,2,3',
    '11) la cancellazione del civico dopo le modifiche lascia la sua versione');

-- ============================================================
-- 12-16. L'indirizzo di ruolo
-- ============================================================
SELECT ok((SELECT indirizzo_id IS NOT NULL FROM _f),
    '12) fixture: il ruolo cliente ha un indirizzo');

SELECT ok((SELECT i.storicizza FROM anagrafiche.indirizzi i JOIN _f ON _f.indirizzo_id = i.id),
    '13) l''indirizzo scritto dalla madre nasce acceso');

UPDATE anagrafiche.indirizzi SET tipo_indirizzo_id = tipo_indirizzo_id WHERE id = (SELECT indirizzo_id FROM _f);
UPDATE anagrafiche.indirizzi SET tipo_indirizzo_id = tipo_indirizzo_id WHERE id = (SELECT indirizzo_id FROM _f);

SELECT is(
    (SELECT string_agg(h.tipo_operazione::text, ',' ORDER BY h.id)
       FROM storico.indirizzi h JOIN _f ON _f.indirizzo_id = h.indirizzi_id
      WHERE h.origine_schema = 'anagrafiche'),
    '1,2,2',
    '14) due modifiche dell''indirizzo di ruolo: la versione di partenza e due versioni');

SELECT ok((SELECT i.storicizza FROM anagrafiche.indirizzi i JOIN _f ON _f.indirizzo_id = i.id),
    '15) dopo le modifiche il flag dell''indirizzo di ruolo e'' ancora acceso');

UPDATE anagrafiche.indirizzi SET storicizza = false WHERE id = (SELECT indirizzo_id FROM _f);

SELECT is(
    (SELECT count(*)::integer
       FROM storico.indirizzi h JOIN _f ON _f.indirizzo_id = h.indirizzi_id
      WHERE h.origine_schema = 'anagrafiche'),
    3,
    '16) una scrittura che passa storicizza = false non lascia traccia');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: questo file non lascia niente dietro di se'.
ROLLBACK;
