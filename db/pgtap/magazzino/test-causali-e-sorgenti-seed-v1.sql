-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: i due cataloghi che guidano il magazzino, nella forma del Lotto 1 —
--   magazzino.causali e config.sorgenti — piu' il flag dell'articolo
--   (brief-db-magazzino-lotto-1-terreno-vuoto, sezioni 4.1, 4.2, 4.3, 7;
--   M-1, M-4, M-5, D-7, D-8, D-L1-d, D-L1-f).
--
-- ⭐ E' il presidio che la CI NON AVEVA per le cinque sorgenti *_RIGA di
--   vendite (id 3, 5, 7, 9, 11): fino al 14-09 esistevano solo sul DB di
--   sviluppo, archiviate a mano; su un database ricostruito da zero
--   DDT_VENDITA_RIGA non c'era, e lo scarico del Lotto 3 sarebbe stato verde
--   su dev e rosso in CI. Ora stanno nel CSV, attive (D-L1-f), e questo file
--   lo asserisce su ogni database.
-- rev 2026-11-06 (brief-db-sorgente-documento-e-riga lotto R, giro R.2, 20261106-60):
--   le sei *_RIGA di vendita escono dalle sorgenti (S-2: una riga si scrive col tipo
--   del suo documento + sorgente_riga). Restano le quattro di magazzino, che il
--   lotto M porta allo stesso modello; il ritiro delle sei lo asserisce
--   vendite/test-sorgente-righe-vendita-v1.
-- rev 2026-11-09 (brief-db-sorgente-documento-e-riga lotto M, giro M.3, 20261109-20):
--   escono anche le tre *_RIGA di magazzino (e DDT_VENDITA_PRELIEVO, RESO_VENDITA_RIENTRO):
--   il registro e le testate scrivono il tipo del DOCUMENTO. Le sorgenti di magazzino sono
--   ora i tre documenti interni (INVENTARIO, RETTIFICA, TRASFERIMENTO: scope CATALOGO, con la
--   tabella delle righe) e l'evento d'asset (EVENTO_ASSET: MAGAZZINO, senza righe). Il ritiro
--   lo asserisce magazzino/test-sorgente-registro-v1 (16, 17).
-- ⚠️ Nessuna fixture: il soggetto e' il seed. Le asserzioni sono sull'INSIEME
--   dei codici (un catalogo puo' crescere con i lotti successivi: si asserisce
--   che i sedici ci siano, non che siano gli unici).
--
-- Elenco test (plan 11):
--   magazzino.causali:
--    1) le sedici causali del Lotto 1 esistono, per codice_interno
--    2) ogni causale ha segno -1 o +1: nessuna «neutra» (M-1)
--    3) il CHECK del segno ammette solo -1 e +1, e la colonna non ha default
--    4) le otto colonne ritirate non esistono (M-4, M-5, D-8)
--    5) magazzino.ambito_causale non esiste (D-8)
--    6) le due causali dello storno hanno verso opposto (D-L1-d), INV_INIZIALE non e' una rettifica
--   config.sorgenti:
--    7) le quattro sorgenti di magazzino (tre documenti interni e l'evento) esistono, ATTIVE
--    8) ...e ogni target_table (e tabella delle righe) risolve (to_regclass): le tabelle esistono
--    9) ognuna ha lo scope atteso: i documenti CATALOGO, l'evento MAGAZZINO
--   10) MAGAZZINO e' ammesso dal CHECK chk_sorgenti_scope
--   catalogo.articoli:
--   11) requires_lotto esiste, NOT NULL, default false — accanto a requires_serial
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- 1..6 magazzino.causali
-- ============================================================
CREATE TEMP TABLE _attese_causali (codice_interno text, segno smallint) ON COMMIT DROP;
INSERT INTO _attese_causali VALUES
    ('CARICO_ACQ', 1), ('SCARICO_VEN', -1), ('TRASF_OUT', -1), ('TRASF_IN', 1),
    ('RETT_POS', 1), ('RETT_NEG', -1), ('ODL_USCITA_MAT', -1), ('ODL_ENTRATA_MAT', 1),
    ('ASSET_INSTALL', -1), ('ASSET_RIENTRO', 1),
    ('CARICO_RESO_VEN', 1), ('SCARICO_RESO_ACQ', -1), ('ODL_VERSAMENTO_PF', 1),
    ('INV_INIZIALE', 1), ('STORNO_POS', 1), ('STORNO_NEG', -1);

SELECT is(
    (SELECT count(*)::int FROM _attese_causali a
      WHERE NOT EXISTS (SELECT 1 FROM magazzino.causali c WHERE c.codice_interno = a.codice_interno)),
    0,
    '1) le sedici causali del Lotto 1 esistono, per codice_interno');

SELECT is(
    (SELECT count(*)::int FROM _attese_causali a
       JOIN magazzino.causali c ON c.codice_interno = a.codice_interno
      WHERE c.segno <> a.segno),
    0,
    '2) ogni causale ha il verso deciso, -1 o +1: nessuna «neutra» (M-1)');

SELECT ok(
    (SELECT pg_get_constraintdef(oid) ~ '-1' AND pg_get_constraintdef(oid) !~ '\m0\M'
       FROM pg_constraint
      WHERE conrelid = 'magazzino.causali'::regclass AND conname = 'chk_magazzino_causali_segno')
    AND NOT EXISTS (SELECT 1 FROM pg_attribute a JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
                     WHERE a.attrelid = 'magazzino.causali'::regclass AND a.attname = 'segno'),
    '3) chk_magazzino_causali_segno ammette solo -1 e +1, e segno non ha piu'' un default');

SELECT is(
    (SELECT count(*)::int FROM pg_attribute
      WHERE attrelid = 'magazzino.causali'::regclass AND NOT attisdropped
        AND attname IN ('impatto_valorizzazione', 'richiede_lotto', 'richiede_seriale',
                        'richiede_magazzino_dest', 'abilita_billing', 'richiede_odl',
                        'contabilizza_cdc', 'ambito_causale_id')),
    0,
    '4) le otto colonne ritirate non esistono piu'' (M-4, M-5, D-8)');

SELECT ok(
    to_regclass('magazzino.ambito_causale') IS NULL,
    '5) magazzino.ambito_causale non esiste piu'' (D-8)');

SELECT ok(
    (SELECT p.segno = 1 AND n.segno = -1 AND NOT i.is_rettifica
       FROM magazzino.causali p, magazzino.causali n, magazzino.causali i
      WHERE p.codice_interno = 'STORNO_POS' AND n.codice_interno = 'STORNO_NEG'
        AND i.codice_interno = 'INV_INIZIALE'),
    '6) STORNO_POS e STORNO_NEG hanno verso opposto (D-L1-d); INV_INIZIALE non e'' una rettifica');

-- ============================================================
-- 7..10 config.sorgenti
-- ============================================================
CREATE TEMP TABLE _attese_sorgenti (codice_interno text, scope text, target_table text, righe_table text) ON COMMIT DROP;
INSERT INTO _attese_sorgenti VALUES
    ('INVENTARIO',     'CATALOGO',  'magazzino.inventari',     'magazzino.inventari_righe'),
    ('RETTIFICA',      'CATALOGO',  'magazzino.rettifiche',    'magazzino.rettifiche_righe'),
    ('TRASFERIMENTO',  'CATALOGO',  'magazzino.trasferimenti', 'magazzino.trasferimenti_righe'),
    ('EVENTO_ASSET',   'MAGAZZINO', 'magazzino.eventi_assets', NULL);

SELECT is(
    (SELECT count(*)::int FROM _attese_sorgenti a
      WHERE NOT EXISTS (SELECT 1 FROM config.sorgenti s
                         WHERE s.codice_interno = a.codice_interno AND s.attivo)),
    0,
    '7) le quattro sorgenti di magazzino (tre documenti interni e l''evento) esistono e sono ATTIVE');

SELECT is(
    (SELECT count(*)::int FROM _attese_sorgenti a
       JOIN config.sorgenti s ON s.codice_interno = a.codice_interno
      WHERE s.target_table IS NULL
         OR s.target_table::text <> a.target_table
         OR to_regclass(a.target_table) IS NULL
         OR s.righe_table::text IS DISTINCT FROM a.righe_table
         OR (a.righe_table IS NOT NULL AND to_regclass(a.righe_table) IS NULL)
         OR s.key_selector <> 'id'),
    0,
    '8) ogni target_table e tabella delle righe e'' quella attesa, risolve davvero, e la chiave e'' id');

SELECT is(
    (SELECT count(*)::int FROM _attese_sorgenti a
       JOIN config.sorgenti s ON s.codice_interno = a.codice_interno
      WHERE s.scope <> a.scope),
    0,
    '9) lo scope atteso: i documenti interni CATALOGO, l''evento MAGAZZINO (D-7)');

SELECT ok(
    (SELECT pg_get_constraintdef(oid) ~ '''MAGAZZINO'''
       FROM pg_constraint WHERE conrelid = 'config.sorgenti'::regclass AND conname = 'chk_sorgenti_scope'),
    '10) MAGAZZINO e'' ammesso da chk_sorgenti_scope');

-- ============================================================
-- 11 catalogo.articoli
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM pg_attribute a
             LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
            WHERE a.attrelid = 'catalogo.articoli'::regclass AND a.attname = 'requires_lotto'
              AND NOT a.attisdropped AND a.attnotnull
              AND pg_get_expr(d.adbin, d.adrelid) = 'false')
    AND EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'catalogo.articoli'::regclass AND attname = 'requires_serial'),
    '11) catalogo.articoli.requires_lotto esiste, NOT NULL DEFAULT false, accanto a requires_serial (M-5)');

SELECT * FROM finish();
ROLLBACK;
