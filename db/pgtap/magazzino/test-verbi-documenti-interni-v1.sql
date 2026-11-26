-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- I verbi dei documenti interni di magazzino (Lotto 2):
--   il registro e le colonne ammesse              (20261123-05)
--   la nascita delle testate, i due guard comuni  (20261123-07)
--   la nascita delle righe                        (20261123-08)
--   i verbi comuni (modifica, elimina, stato, righe) (20261123-09)
--   Brief: brief-db-magazzino-tutte-le-scritture-dal-verbo, P-5b
--   (D-M5, D-M9, D-M10, D-M11).
--
-- ⭐ I casi si COSTRUISCONO: due emittenti con il loro operatore
--   (fn_pgtap_crea_emittente_operatore: BLOCCATO ovunque); il livello lo
--   scrive il test (dbops.fn_pgtap_concedi_livello_area). Il documento di B nasce nel
--   contesto di B, il tentativo si fa in quello di A.
--
-- ⚠️ Gira come l'APPLICAZIONE: i verbi sono la strada dell'operatore.
--
-- Elenco test (plan 33):
--   il permesso
--    1) senza livello: fn_aggiungi_inventario -> E_PERMESSO_NEGATO
--    2) una famiglia che non esiste: E_PERMESSO_NEGATO (fail-closed)
--   la nascita delle testate
--    3) fn_aggiungi_inventario: nasce in DRAFT, con la descrizione
--    4) nel magazzino di B: E_MAG_MAGAZZINO_NON_TROVATO
--    5) un campo fuori lista (meta): E_CAMPO_NON_AMMESSO
--    6) fn_aggiungi_trasferimento fra due magazzini propri
--    7) un arrivo di B: E_MAG_MAGAZZINO_NON_TROVATO
--    8) l'arrivo in p_campi (e' un argomento): E_CAMPO_NON_AMMESSO
--   la nascita delle righe
--    9) fn_aggiungi_riga_inventario
--   10) su una rettifica che non esiste: E_MAG_DOCUMENTO_NON_TROVATO
--   11) fn_aggiungi_riga_trasferimento
--   12) qta_sistema fra i campi (la scrive la registrazione): E_CAMPO_NON_AMMESSO
--   la testata
--   13) fn_modifica_documento_interno: la descrizione cambia, il ritorno ha
--       solo id e colonne modificabili
--   14) lo stato fra i dati: E_CAMPO_NON_AMMESSO (ha il suo verbo)
--   15) l'arrivo del trasferimento non si modifica: E_CAMPO_NON_AMMESSO
--   le righe
--   16) fn_modifica_riga_documento_interno: la quantita' contata cambia
--   17) una riga di un altro documento: E_MAG_DOCUMENTO_RIGA_NON_TROVATA
--   18) fn_togli_riga_documento_interno: la riga sparisce
--   19) una riga che non c'e': E_MAG_DOCUMENTO_RIGA_NON_TROVATA
--   lo stato
--   20) conferma: CONFIRM
--   21) in CONFIRM la testata non si modifica: E_MAG_DOCUMENTO_TESTATA_CONGELATA
--   22) in CONFIRM una riga non si aggiunge: E_MAG_DOCUMENTO_RIGHE_CONGELATE
--   23) POSTED non si chiede: E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE
--  23b) ...anche con la GUC della registrazione accesa dall'app: il verbo la spegne
--  23c) una riga in CONFIRM con la GUC accesa dall'app: E_MAG_DOCUMENTO_RIGHE_CONGELATE
--   24) riapri: DRAFT
--   25) elimina in DRAFT: la testata e le sue righe spariscono
--   26) elimina una rettifica annullata: E_MAG_DOCUMENTO_NON_ELIMINABILE
--   il perimetro
--   27) il documento di B: E_MAG_DOCUMENTO_NON_TROVATO (no-leak)
--   la forma
--   28) i verbi sono SECURITY DEFINER con search_path bloccato
--   29) ognuno chiama script.fn_guard_livello
--   30) il registro: tre famiglie, nessuna riga per una che non esiste
--   31) le colonne ammesse: NULL su una combinazione che non esiste
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(33);


CREATE OR REPLACE FUNCTION pg_temp.corpo(p regprocedure) RETURNS text
LANGUAGE sql AS $$
    SELECT regexp_replace(p2.prosrc, '--[^\n]*', '', 'g') FROM pg_proc p2 WHERE p2.oid = p
$$;

-- Il livello d'area di un operatore (l'upsert di config.user_override_aree).
-- ⭐ rev 2026-11-25 (D-L a, brief-db-porte-aperte-dalla-sola-guc): il livello d'area lo
--   da' il builder dbops.fn_pgtap_concedi_livello_area; la copia pg_temp.livello_area
--   che stava qui e' ritirata (regola del 2).

-- ============================================================
-- Fixture: B col suo magazzino e una sua rettifica, nel suo contesto
-- ============================================================
CREATE TEMP TABLE _b AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _b)); END $ctx$;
CREATE TEMP TABLE _fb AS SELECT dbops.fn_pgtap_crea_magazzino('PGT-VDI-B', false) AS mag;
DO $b$ BEGIN PERFORM dbops.fn_pgtap_concedi_livello_area((SELECT auth_user_id FROM _b), 'magazzino', 'TUTTO'); END $b$;
CREATE TEMP TABLE _db AS SELECT magazzino.fn_aggiungi_rettifica((SELECT mag FROM _fb)) AS rett;

-- ============================================================
-- Fixture: A (chi agisce), nel suo contesto
-- ============================================================
CREATE TEMP TABLE _a AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _a)); END $ctx$;
CREATE TEMP TABLE _fa AS
SELECT dbops.fn_pgtap_crea_magazzino('PGT-VDI-A1', false)               AS mag,
       dbops.fn_pgtap_crea_magazzino('PGT-VDI-A2', false)               AS mag2,
       dbops.fn_pgtap_crea_articolo('PGT-VDI-ART', true, false, false)  AS art,
       dbops.fn_pgtap_crea_articolo('PGT-VDI-ART2', true, false, false) AS art2;

-- ============================================================
-- 1-2 Il permesso
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_inventario((SELECT mag FROM _fa))$$),
    'E_PERMESSO_NEGATO',
    '1. senza livello: fn_aggiungi_inventario -> E_PERMESSO_NEGATO');

DO $a$ BEGIN PERFORM dbops.fn_pgtap_concedi_livello_area((SELECT auth_user_id FROM _a), 'magazzino', 'TUTTO'); END $a$;

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_cambia_stato_documento_interno('PIPPO', 1, 'CONFIRM')$$),
    'E_PERMESSO_NEGATO',
    '2. una famiglia che non esiste non ha oggetto: E_PERMESSO_NEGATO');

-- ============================================================
-- 3-8 La nascita delle testate
-- ============================================================
CREATE TEMP TABLE _doc AS
SELECT magazzino.fn_aggiungi_inventario(f.mag, '{"descrizione": "Conta di novembre"}'::jsonb) AS inv,
       magazzino.fn_aggiungi_rettifica(f.mag)                                               AS rett,
       magazzino.fn_aggiungi_trasferimento(f.mag, f.mag2)                                   AS trasf
  FROM _fa f;

SELECT is(
    (SELECT i.stato_mag_inventario || '|' || i.descrizione
       FROM magazzino.inventari i WHERE i.id = (SELECT inv FROM _doc)),
    'DRAFT|Conta di novembre',
    '3. fn_aggiungi_inventario: nasce in DRAFT, con la descrizione');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_inventario((SELECT mag FROM _fb))$$),
    'E_MAG_MAGAZZINO_NON_TROVATO',
    '4. nel magazzino di B: E_MAG_MAGAZZINO_NON_TROVATO');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_rettifica((SELECT mag FROM _fa),
        '{"meta": {}}'::jsonb)$$),
    'E_CAMPO_NON_AMMESSO',
    '5. un campo fuori lista (meta): E_CAMPO_NON_AMMESSO');

SELECT is(
    (SELECT t.stato_trasferimento || '|' || (t.magazzino_id_from = f.mag) || '|' || (t.magazzino_id_to = f.mag2)
       FROM magazzino.trasferimenti t, _fa f WHERE t.id = (SELECT trasf FROM _doc)),
    'DRAFT|true|true',
    '6. fn_aggiungi_trasferimento fra due magazzini propri');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_trasferimento((SELECT mag FROM _fa),
        (SELECT mag FROM _fb))$$),
    'E_MAG_MAGAZZINO_NON_TROVATO',
    '7. un arrivo di B: E_MAG_MAGAZZINO_NON_TROVATO');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_trasferimento((SELECT mag FROM _fa),
        (SELECT mag2 FROM _fa), jsonb_build_object('magazzino_id_to', (SELECT mag FROM _fa)))$$),
    'E_CAMPO_NON_AMMESSO',
    '8. l''arrivo in p_campi (e'' un argomento): E_CAMPO_NON_AMMESSO');

-- ============================================================
-- 9-12 La nascita delle righe
-- ============================================================
CREATE TEMP TABLE _righe AS
SELECT magazzino.fn_aggiungi_riga_inventario(d.inv, f.art, 7)      AS r1,
       magazzino.fn_aggiungi_riga_inventario(d.inv, f.art2, 3)     AS r2,
       magazzino.fn_aggiungi_riga_trasferimento(d.trasf, f.art, 2) AS rt
  FROM _doc d, _fa f;

SELECT is(
    (SELECT r.qta_contata::text FROM magazzino.inventari_righe r
      WHERE r.id = (SELECT r1 FROM _righe) AND r.inventario_id = (SELECT inv FROM _doc)),
    '7.000000',
    '9. fn_aggiungi_riga_inventario');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_riga_rettifica(-1,
        (SELECT art FROM _fa), 1)$$),
    'E_MAG_DOCUMENTO_NON_TROVATO',
    '10. su una rettifica che non esiste: E_MAG_DOCUMENTO_NON_TROVATO');

SELECT is(
    (SELECT r.qta::text FROM magazzino.trasferimenti_righe r
      WHERE r.id = (SELECT rt FROM _righe) AND r.trasferimento_id = (SELECT trasf FROM _doc)),
    '2.000000',
    '11. fn_aggiungi_riga_trasferimento');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_riga_inventario((SELECT inv FROM _doc),
        (SELECT art FROM _fa), 1, '{"qta_sistema": 1}'::jsonb)$$),
    'E_CAMPO_NON_AMMESSO',
    '12. qta_sistema fra i campi (la scrive la registrazione): E_CAMPO_NON_AMMESSO');

-- ============================================================
-- 13-15 La testata
-- ============================================================
SELECT is(
    (SELECT (r ->> 'descrizione') || '|' || (SELECT string_agg(k, ',' ORDER BY k) FROM jsonb_object_keys(r) AS k)
       FROM (SELECT magazzino.fn_modifica_documento_interno('INVENTARIO', (SELECT inv FROM _doc),
                                                            '{"descrizione": "Conta rifatta"}'::jsonb) AS r) x),
    'Conta rifatta|data,descrizione,id',
    '13. fn_modifica_documento_interno: la descrizione cambia, il ritorno ha solo id e colonne modificabili');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_modifica_documento_interno('INVENTARIO',
        (SELECT inv FROM _doc), '{"stato_mag_inventario": "CONFIRM"}'::jsonb)$$),
    'E_CAMPO_NON_AMMESSO',
    '14. lo stato fra i dati: E_CAMPO_NON_AMMESSO (ha il suo verbo)');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_modifica_documento_interno('TRASFERIMENTO',
        (SELECT trasf FROM _doc), jsonb_build_object('magazzino_id_to', (SELECT mag FROM _fa)))$$),
    'E_CAMPO_NON_AMMESSO',
    '15. l''arrivo del trasferimento non si modifica: E_CAMPO_NON_AMMESSO');

-- ============================================================
-- 16-19 Le righe
-- ============================================================
SELECT is(
    (SELECT magazzino.fn_modifica_riga_documento_interno('INVENTARIO', (SELECT inv FROM _doc),
                (SELECT r1 FROM _righe), '{"qta_contata": 9}'::jsonb) ->> 'qta_contata'),
    '9.000000',
    '16. fn_modifica_riga_documento_interno: la quantita'' contata cambia');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_modifica_riga_documento_interno('TRASFERIMENTO',
        (SELECT trasf FROM _doc), (SELECT r1 FROM _righe), '{"qta": 1}'::jsonb)$$),
    'E_MAG_DOCUMENTO_RIGA_NON_TROVATA',
    '17. una riga di un altro documento: E_MAG_DOCUMENTO_RIGA_NON_TROVATA');

DO $togli$ BEGIN
    PERFORM magazzino.fn_togli_riga_documento_interno('INVENTARIO', (SELECT inv FROM _doc), (SELECT r2 FROM _righe));
END $togli$;
SELECT is(
    (SELECT count(*) FROM magazzino.inventari_righe r WHERE r.id = (SELECT r2 FROM _righe)),
    0::bigint,
    '18. fn_togli_riga_documento_interno: la riga sparisce');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_togli_riga_documento_interno('INVENTARIO',
        (SELECT inv FROM _doc), (SELECT r2 FROM _righe))$$),
    'E_MAG_DOCUMENTO_RIGA_NON_TROVATA',
    '19. una riga che non c''e'': E_MAG_DOCUMENTO_RIGA_NON_TROVATA');

-- ============================================================
-- 20-26 Lo stato
-- ============================================================
SELECT is(
    magazzino.fn_cambia_stato_documento_interno('INVENTARIO', (SELECT inv FROM _doc), 'CONFIRM'),
    'CONFIRM',
    '20. conferma: CONFIRM');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_modifica_documento_interno('INVENTARIO',
        (SELECT inv FROM _doc), '{"descrizione": "troppo tardi"}'::jsonb)$$),
    'E_MAG_DOCUMENTO_TESTATA_CONGELATA',
    '21. in CONFIRM la testata non si modifica: E_MAG_DOCUMENTO_TESTATA_CONGELATA');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_riga_inventario((SELECT inv FROM _doc),
        (SELECT art FROM _fa), 1)$$),
    'E_MAG_DOCUMENTO_RIGHE_CONGELATE',
    '22. in CONFIRM una riga non si aggiunge: E_MAG_DOCUMENTO_RIGHE_CONGELATE');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_cambia_stato_documento_interno('INVENTARIO',
        (SELECT inv FROM _doc), 'POSTED')$$),
    'E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE',
    '23. POSTED non si chiede: E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE');

-- 23b-23c Il controesempio della GUC: l'app la accende da se' e chiama il verbo,
--   che e' SECURITY DEFINER (dentro, chi scrive e' il proprietario). Il verbo la
--   spegne (fn_documento_interno_blocca): i trigger rispondono come alla
--   scrittura diretta. La set_config sta nella stessa sottotransazione del rifiuto.
SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT set_config('zeroerp.magazzino_posting_inventario',
                                             (SELECT inv::text FROM _doc), true),
                                         magazzino.fn_cambia_stato_documento_interno('INVENTARIO',
                                             (SELECT inv FROM _doc), 'POSTED')$$),
    'E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE',
    '23b. POSTED dal verbo con la GUC accesa dall''app: E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT set_config('zeroerp.magazzino_posting_inventario',
                                             (SELECT inv::text FROM _doc), true),
                                         magazzino.fn_aggiungi_riga_inventario((SELECT inv FROM _doc),
                                             (SELECT art2 FROM _fa), 3)$$),
    'E_MAG_DOCUMENTO_RIGHE_CONGELATE',
    '23c. una riga in CONFIRM dal verbo con la GUC accesa dall''app: E_MAG_DOCUMENTO_RIGHE_CONGELATE');

SELECT is(
    magazzino.fn_cambia_stato_documento_interno('INVENTARIO', (SELECT inv FROM _doc), 'DRAFT'),
    'DRAFT',
    '24. riapri: DRAFT');

DO $elimina$ BEGIN
    PERFORM magazzino.fn_elimina_documento_interno('INVENTARIO', (SELECT inv FROM _doc));
END $elimina$;
SELECT is(
    (SELECT count(*) FROM magazzino.inventari i WHERE i.id = (SELECT inv FROM _doc))
    + (SELECT count(*) FROM magazzino.inventari_righe r WHERE r.inventario_id = (SELECT inv FROM _doc)),
    0::bigint,
    '25. elimina in DRAFT: la testata e le sue righe spariscono');

DO $annulla$ BEGIN
    PERFORM magazzino.fn_cambia_stato_documento_interno('RETTIFICA', (SELECT rett FROM _doc), 'CANCEL');
END $annulla$;
SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_elimina_documento_interno('RETTIFICA',
        (SELECT rett FROM _doc))$$),
    'E_MAG_DOCUMENTO_NON_ELIMINABILE',
    '26. elimina una rettifica annullata: E_MAG_DOCUMENTO_NON_ELIMINABILE');

-- ============================================================
-- 27 Il perimetro
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_cambia_stato_documento_interno('RETTIFICA',
        (SELECT rett FROM _db), 'CANCEL')$$),
    'E_MAG_DOCUMENTO_NON_TROVATO',
    '27. il documento di B: E_MAG_DOCUMENTO_NON_TROVATO (no-leak)');

-- ============================================================
-- 28-31 La forma
-- ============================================================
CREATE TEMP TABLE _verbi (f regprocedure);
INSERT INTO _verbi VALUES
    ('magazzino.fn_aggiungi_inventario(bigint, jsonb)'),
    ('magazzino.fn_aggiungi_rettifica(bigint, jsonb)'),
    ('magazzino.fn_aggiungi_trasferimento(bigint, bigint, jsonb)'),
    ('magazzino.fn_aggiungi_riga_inventario(bigint, uuid, numeric, jsonb)'),
    ('magazzino.fn_aggiungi_riga_rettifica(bigint, uuid, numeric, jsonb)'),
    ('magazzino.fn_aggiungi_riga_trasferimento(bigint, uuid, numeric, jsonb)'),
    ('magazzino.fn_modifica_documento_interno(text, bigint, jsonb)'),
    ('magazzino.fn_elimina_documento_interno(text, bigint)'),
    ('magazzino.fn_cambia_stato_documento_interno(text, bigint, text)'),
    ('magazzino.fn_modifica_riga_documento_interno(text, bigint, bigint, jsonb)'),
    ('magazzino.fn_togli_riga_documento_interno(text, bigint, bigint)');

SELECT is(
    (SELECT array_agg(v.f::text ORDER BY v.f::text)
       FROM _verbi v JOIN pg_proc p ON p.oid = v.f
      WHERE NOT p.prosecdef
         OR p.proconfig IS DISTINCT FROM ARRAY['search_path=pg_catalog, public, pg_temp']),
    NULL,
    '28. i verbi sono SECURITY DEFINER con search_path bloccato');

SELECT is(
    (SELECT array_agg(v.f::text ORDER BY v.f::text)
       FROM _verbi v
      WHERE pg_temp.corpo(v.f) !~ 'script\.fn_guard_livello\('),
    NULL,
    '29. ognuno chiama script.fn_guard_livello');

SELECT is(
    (SELECT string_agg(f.famiglia || ':' || f.tabella, ',' ORDER BY f.famiglia)
       FROM unnest(ARRAY['INVENTARIO', 'RETTIFICA', 'TRASFERIMENTO', 'PIPPO']) AS q(fam)
       CROSS JOIN LATERAL magazzino.fn_documento_interno_famiglia(q.fam) AS f),
    'INVENTARIO:inventari,RETTIFICA:rettifiche,TRASFERIMENTO:trasferimenti',
    '30. il registro: tre famiglie, nessuna riga per una che non esiste');

SELECT ok(
    magazzino.fn_documento_interno_colonne_ammesse('PIPPO', 'testata', 'crea') IS NULL
    AND magazzino.fn_documento_interno_colonne_ammesse('INVENTARIO', 'testata', 'cancella') IS NULL
    AND magazzino.fn_documento_interno_colonne_ammesse('INVENTARIO', 'testata', 'crea') IS NOT NULL,
    '31. le colonne ammesse: NULL su una combinazione che non esiste');

SELECT * FROM finish();

ROLLBACK;
