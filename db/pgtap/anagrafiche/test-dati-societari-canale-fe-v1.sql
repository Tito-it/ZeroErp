-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il canale della fattura elettronica (destinatario_fe): P = PEC, C = codice
--   SDI, NULL = nessun canale. Il canale scelto pretende il suo recapito, e il
--   codice SDI ha la sua forma.
--   Brief: brief-db-character-n-spazi-di-riempimento (D-6, decisioni di Tid
--   del 2026-10-10). ChangeSet: 20261010-37 (vocabolario, forma, coerenza,
--   via gli UNIQUE), -39 (guard), -40 (helper senza canale). Dal 20261011 le
--   scritture passano dal verbo anagrafiche.fn_scrivi_dati_societari (B-5 di
--   brief-db-dati-fiscali-e-societari-del-soggetto).
--
-- Elenco test (plan 13):
--  1) l'helper di fixture crea i dati societari senza canale (NULL)
--  2) canale C con un codice di 7 caratteri: entra
--  3) un codice di 6 caratteri (PA): entra
--  4) codice in minuscolo: E_DATI_SOCIETARI_CODICE_SDI_NON_VALIDO
--  5) codice di 10 caratteri: lo ferma il tipo varchar(7) (22001), prima
--       che i trigger lo vedano
--  6) canale C senza codice: E_DATI_SOCIETARI_CODICE_SDI_MANCANTE
--  7) canale P senza PEC: E_DATI_SOCIETARI_PEC_FATTURAZIONE_MANCANTE
--  8) canale P con la PEC: entra
--  9) un canale fuori vocabolario: 23514 (chiamante rotto, nessuna frase)
-- 10) canale tolto (NULL): entra
-- 11) due soggetti con lo stesso codice SDI e la stessa PEC: entrano (gli
--       UNIQUE non ci sono piu')
-- 12) i tre CHECK del -37 ci sono, nella forma esatta (la rete sotto il guard)
-- 13) uq_ds_codice_sdi e uq_ds_pec_fatt non ci sono piu'
--
-- ⚠️ I pattern delle frasi non attraversano i segnaposti.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- Fixture: due soggetti PG con i loro dati societari
-- ============================================================
CREATE TEMP TABLE _fx ON COMMIT DROP AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('PGTAP Canale FE Uno', p_piva := dbops.fn_pgtap_piva_libera(0)) AS s1,
       NULL::uuid AS s2;
UPDATE _fx SET s2 = dbops.fn_pgtap_crea_soggetto_pg('PGTAP Canale FE Due', p_piva := dbops.fn_pgtap_piva_libera(1));

-- ⭐ Rev 20261011 (brief-db-dati-fiscali-e-societari-del-soggetto, B-5): dal
--   20261011-04 l'app non scrive anagrafiche.dati_societari, la porta e' il verbo
--   anagrafiche.fn_scrivi_dati_societari, che riceve lo STATO INTERO. I casi
--   restano gli stessi: questa funzione legge la riga, sovrappone i soli campi
--   cambiati (jsonb_populate_record: una chiave con null scrive NULL) e chiama il
--   verbo. Un codice di 10 caratteri lo ferma ancora il tipo varchar(7) (22001),
--   ora nel passaggio al tipo della riga, prima del verbo.
CREATE OR REPLACE FUNCTION pg_temp.ds_cambia(p_soggetto uuid, p_cambi jsonb) RETURNS void
LANGUAGE plpgsql AS $f$
DECLARE r anagrafiche.dati_societari;
BEGIN
    SELECT * INTO r FROM anagrafiche.dati_societari WHERE soggetto_id = p_soggetto;
    r := jsonb_populate_record(r, p_cambi);
    PERFORM anagrafiche.fn_scrivi_dati_societari(
        p_soggetto_id        := p_soggetto,
        p_forma_giuridica_id := r.forma_giuridica_id,
        p_id_prov_iscri_rea  := r.id_prov_iscri_rea,
        p_iscrizione_rea     := r.iscrizione_rea,
        p_capitale_sociale   := r.capitale_sociale,
        p_socio_unico        := r.socio_unico,
        p_liquidazione       := r.liquidazione,
        p_destinatario_fe    := r.destinatario_fe,
        p_pec_fatturazione   := r.pec_fatturazione,
        p_codice_sdi         := r.codice_sdi,
        p_data_costituzione  := r.data_costituzione);
END $f$;

-- ============================================================
-- 1. L'helper
-- ============================================================
SELECT is(
    (SELECT ds.destinatario_fe FROM anagrafiche.dati_societari ds
      WHERE ds.soggetto_id = (SELECT s1 FROM _fx)),
    NULL,
    '1) l''helper crea i dati societari senza canale FE'
);

-- ============================================================
-- 2-5. Il codice SDI
-- ============================================================
SELECT lives_ok(
    $$SELECT pg_temp.ds_cambia((SELECT s1 FROM _fx), '{"destinatario_fe": "C", "codice_sdi": "ABC1234"}')$$,
    '2) canale C con un codice di 7 caratteri: entra'
);

SELECT lives_ok(
    $$SELECT pg_temp.ds_cambia((SELECT s1 FROM _fx), '{"codice_sdi": "UFABC1"}')$$,
    '3) un codice di 6 caratteri (PA): entra'
);

SELECT throws_like(
    $$SELECT pg_temp.ds_cambia((SELECT s1 FROM _fx), '{"codice_sdi": "abc1234"}')$$,
    '%codice destinatario SDI%non è valido%',
    '4) codice in minuscolo: E_DATI_SOCIETARI_CODICE_SDI_NON_VALIDO'
);

SELECT throws_ok(
    $$SELECT pg_temp.ds_cambia((SELECT s1 FROM _fx), '{"codice_sdi": "XXXXXXX002"}')$$,
    '22001', NULL,
    '5) codice di 10 caratteri: lo ferma il tipo varchar(7)'
);

-- ============================================================
-- 6-10. Il canale e il suo recapito
-- ============================================================
SELECT throws_like(
    $$SELECT pg_temp.ds_cambia((SELECT s1 FROM _fx), '{"destinatario_fe": "C", "codice_sdi": null}')$$,
    '%con il codice SDI, ma il codice manca%',
    '6) canale C senza codice: E_DATI_SOCIETARI_CODICE_SDI_MANCANTE'
);

SELECT throws_like(
    $$SELECT pg_temp.ds_cambia((SELECT s1 FROM _fx), '{"destinatario_fe": "P", "pec_fatturazione": null}')$$,
    '%via PEC, ma la PEC manca%',
    '7) canale P senza PEC: E_DATI_SOCIETARI_PEC_FATTURAZIONE_MANCANTE'
);

SELECT lives_ok(
    $$SELECT pg_temp.ds_cambia((SELECT s1 FROM _fx), '{"destinatario_fe": "P", "pec_fatturazione": "fatture.pgtap@pec.example.com"}')$$,
    '8) canale P con la PEC: entra'
);

SELECT throws_ok(
    $$SELECT pg_temp.ds_cambia((SELECT s1 FROM _fx), '{"destinatario_fe": "X"}')$$,
    '23514', NULL,
    '9) canale fuori vocabolario: 23514 (lo sceglie una lista, chi lo sbaglia e'' un chiamante rotto)'
);

SELECT lives_ok(
    $$SELECT pg_temp.ds_cambia((SELECT s1 FROM _fx), '{"destinatario_fe": null}')$$,
    '10) canale tolto: entra (nullable, decisione di Tid)'
);

-- ============================================================
-- 11. Un intermediario serve piu' clienti
-- ============================================================
SELECT lives_ok(
    $$SELECT pg_temp.ds_cambia(x.s, '{"destinatario_fe": "C", "codice_sdi": "INTERM1", "pec_fatturazione": "studio.pgtap@pec.example.com"}')
        FROM (SELECT s1 AS s FROM _fx UNION ALL SELECT s2 FROM _fx) x$$,
    '11) due soggetti con lo stesso codice SDI e la stessa PEC: entrano'
);

-- ============================================================
-- 12-13. I vincoli
-- ============================================================
SELECT is(
    (SELECT string_agg(k.conname || ' ' || pg_get_constraintdef(k.oid), E'\n' ORDER BY k.conname)
       FROM pg_constraint k
      WHERE k.conrelid = 'anagrafiche.dati_societari'::regclass
        AND k.conname IN ('chk_dati_societari_canale_fe_coerente',
                          'chk_dati_societari_codice_sdi_forma',
                          'chk_dati_societari_destinatario_fe_canale')),
    'chk_dati_societari_canale_fe_coerente CHECK (((((destinatario_fe)::text IS DISTINCT FROM ''P''::text) OR (COALESCE(btrim((pec_fatturazione)::text), ''''::text) <> ''''::text)) AND (((destinatario_fe)::text IS DISTINCT FROM ''C''::text) OR (codice_sdi IS NOT NULL))))' || E'\n' ||
    'chk_dati_societari_codice_sdi_forma CHECK (((codice_sdi)::text ~ ''^[A-Z0-9]{6,7}$''::text))' || E'\n' ||
    'chk_dati_societari_destinatario_fe_canale CHECK (((destinatario_fe)::text = ANY ((ARRAY[''P''::character varying, ''C''::character varying])::text[])))',
    '12) i tre CHECK del canale FE ci sono, nella forma esatta'
);

SELECT ok(
    NOT EXISTS (SELECT 1 FROM pg_constraint k
                 WHERE k.conrelid = 'anagrafiche.dati_societari'::regclass
                   AND k.conname IN ('uq_ds_codice_sdi', 'uq_ds_pec_fatt')),
    '13) codice SDI e PEC di fatturazione non sono piu'' unici'
);

SELECT * FROM finish();
ROLLBACK;
