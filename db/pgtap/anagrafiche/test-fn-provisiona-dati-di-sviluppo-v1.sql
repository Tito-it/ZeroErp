-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: l'ambiente SVILUPPO si dichiara qui (riga di
--   dbops.installazione a trigger spento, solo il proprietario), perche' il
--   file non dipenda dalla macchina; e l'omonimo senza etichetta si costruisce
--   creando una credenziale con fn_crea_auth_user, che scrive django.auth_user.
--
-- Il verbo dei dati di sviluppo:
--   anagrafiche.fn_provisiona_dati_di_sviluppo   (20261018-60)
--   Brief: brief-db-processi-accensione-per-ambiente (R-4, 2b-3);
--   l'elenco: brief-be-utenti-di-sviluppo §7. Il rifiuto in PRODUZIONE:
--   dbops/test-etichette-di-prova-v1 (test 14).
--
-- ⚠️ I DUE MONDI. In CI lo schema django e' vuoto (manage.py migrate gira dopo
--   Liquibase, e in ci.yaml non gira): il verbo crea credenziali, e li' non
--   puo'. I test che lo chiamano si dichiarano con skip() motivato; la forma
--   (1-2) si prova sempre. Il mondo con django e' dbdev e lo scratch.
--
-- Elenco test (plan 20):
--   forma
--    1) SECURITY DEFINER
--    2) search_path fissato, pg_catalog per primo
--   la prima corsa (mondo con django)
--    3) venti radici: create quelle che mancavano, riallineate quelle che c'erano
--       (su un database nuovo tutte create; su dbdev, dopo il command, tutte riallineate)
--    4) otto credenziali e dodici soggetti etichettati
--    5) secondo fattore: solo dev.smoke
--    6) dev.smoke e' SUPER_ADMIN
--    7) tutte le vesti dei dev.* sono accese
--    8) dev.emittente: profilo DEV_OPERATIVO, whitelist solo A
--    9) dev.bloccato: vendite.contratto BLOCCATO
--   10) gli operatori lavorano su A (emittente attivo)
--   11) il cliente B ha il BA legato a B, i clienti 1-3 ad A
--   12) i due magazzini predefiniti, uno per emittente
--   13) DEV_LETTURA ha LETTURA su tutte le aree presenti
--   14) dev.lettura e' un OPERATORE per fn_categoria_accesso (la categoria non legge l'etichetta)
--   15) le GUC di sessione sono come prima
--   la seconda corsa
--   16) venti radici, tutte riallineate, nessuna etichetta nuova
--   17) una password data in riallineamento si scrive
--   18) un'area nuova entra nel profilo alla corsa dopo
--   l'omonimo
--   19) uno username dell'elenco gia' preso senza etichetta: E_RADICE_DI_PROVA_SENZA_ETICHETTA
--   20) ... e non e' stato adottato (nessuna etichetta)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(20);


-- Il mondo: c'e' django.auth_user?
CREATE TEMP TABLE t_mondo AS SELECT to_regclass('django.auth_user') IS NOT NULL AS django;

-- ============================================================
-- Forma
-- ============================================================
SELECT is((SELECT p.prosecdef FROM pg_proc p
            WHERE p.oid = 'anagrafiche.fn_provisiona_dati_di_sviluppo(jsonb)'::regprocedure),
          true, '1. SECURITY DEFINER: e'' l''unico scrittore delle etichette');

SELECT ok((SELECT array_to_string(p.proconfig, ',') ~ '^search_path=pg_catalog'
             FROM pg_proc p WHERE p.oid = 'anagrafiche.fn_provisiona_dati_di_sviluppo(jsonb)'::regprocedure),
          '2. search_path fissato, pg_catalog per primo');

-- L'ambiente SVILUPPO, dichiarato qui.
ALTER TABLE dbops.installazione DISABLE TRIGGER trg_installazione_a05_guard_immutabile_upd_dlt;
DELETE FROM dbops.installazione;
INSERT INTO dbops.installazione (ambiente) VALUES ('SVILUPPO');
ALTER TABLE dbops.installazione ENABLE TRIGGER trg_installazione_a05_guard_immutabile_upd_dlt;

-- Le GUC prima del verbo (le rimette lui com'erano).
CREATE TEMP TABLE t_guc AS
SELECT current_setting('app.current_user_id', true) AS u, current_setting('app.current_emittente_id', true) AS e;

CREATE TEMP TABLE t_c1 (tipo text, chiave text, radice_id text, esito text, secondo_fattore boolean);

-- ⚠️ rev 2026-10-19: le radici di prova che esistono GIA', prima della prima
--   corsa. Su un database dove il command e' gia' girato (dbdev, dal collaudo
--   del 2026-10-18) il verbo non crea: riallinea. Il test 3 pretendeva «tutte
--   create», cioe' un database senza dati di sviluppo, ed era rosso su dbdev
--   con il verbo giusto. Ora pretende il conto esatto di create e riallineate.
CREATE TEMP TABLE t_prima AS
SELECT (SELECT count(*) FROM dbops.credenziali_di_prova WHERE chiave LIKE 'dev.%')
     + (SELECT count(*) FROM dbops.soggetti_di_prova WHERE chiave LIKE 'DEV-%') AS radici;
CREATE TEMP TABLE t_c2 (LIKE t_c1);

-- ⚠️ I vincoli differiti (indirizzi obbligatori, satelliti dell'istanza) si
--   chiudono a corsa finita, come al COMMIT del command.
SET CONSTRAINTS ALL DEFERRED;
DO $c1$
BEGIN
    IF (SELECT django FROM t_mondo) THEN
        INSERT INTO t_c1 SELECT * FROM anagrafiche.fn_provisiona_dati_di_sviluppo();
    END IF;
END
$c1$;
SET CONSTRAINTS ALL IMMEDIATE;

CREATE OR REPLACE FUNCTION pg_temp.au(p_username text) RETURNS integer LANGUAGE sql AS $$
    SELECT cp.auth_user_id FROM dbops.credenziali_di_prova cp WHERE cp.chiave = p_username
$$;
CREATE OR REPLACE FUNCTION pg_temp.ef(p_codice text) RETURNS bigint LANGUAGE sql AS $$
    SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.codice = p_codice
$$;

-- ============================================================
-- La prima corsa
-- ============================================================
SELECT CASE WHEN (SELECT django FROM t_mondo) THEN
    is((SELECT format('%s|%s|%s', count(*), count(*) FILTER (WHERE esito = 'creata'),
                      count(*) FILTER (WHERE esito = 'riallineata')) FROM t_c1),
       (SELECT format('20|%s|%s', 20 - radici, radici) FROM t_prima),
       '3. venti radici: create quelle che mancavano, riallineate quelle che c''erano')
  ELSE skip('mondo CI: django.auth_user non c''e'', il verbo non crea credenziali', 1) END;

SELECT CASE WHEN (SELECT django FROM t_mondo) THEN
    is(format('%s|%s',
              (SELECT count(*) FROM dbops.credenziali_di_prova WHERE chiave LIKE 'dev.%'),
              (SELECT count(*) FROM dbops.soggetti_di_prova WHERE chiave LIKE 'DEV-%')),
       '8|12', '4. otto credenziali e dodici soggetti etichettati')
  ELSE skip('mondo CI: django.auth_user non c''e''', 1) END;

SELECT CASE WHEN (SELECT django FROM t_mondo) THEN
    is((SELECT string_agg(chiave, ',') FROM t_c1 WHERE secondo_fattore), 'dev.smoke',
       '5. secondo fattore: solo dev.smoke')
  ELSE skip('mondo CI: django.auth_user non c''e''', 1) END;

SELECT CASE WHEN (SELECT django FROM t_mondo) THEN
    is((SELECT pa.tipo::text
          FROM anagrafiche.identita_digitali idg
          JOIN config.profili_accesso_bindings pab ON pab.identita_digitale_id = idg.id
          JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
         WHERE idg.auth_user_id = pg_temp.au('dev.smoke') AND idg.ruolo_applicativo = 'OPERATORE'),
       'SUPER_ADMIN', '6. dev.smoke e'' SUPER_ADMIN')
  ELSE skip('mondo CI: django.auth_user non c''e''', 1) END;

SELECT CASE WHEN (SELECT django FROM t_mondo) THEN
    is((SELECT count(*)::int FROM anagrafiche.identita_digitali idg
          JOIN dbops.credenziali_di_prova cp ON cp.auth_user_id = idg.auth_user_id
         WHERE cp.chiave LIKE 'dev.%' AND NOT idg.attivo),
       0, '7. tutte le vesti dei dev.* sono accese')
  ELSE skip('mondo CI: django.auth_user non c''e''', 1) END;

SELECT CASE WHEN (SELECT django FROM t_mondo) THEN
    is(format('%s|%s',
              (SELECT pa.codice FROM anagrafiche.identita_digitali idg
                 JOIN config.profili_accesso_bindings pab ON pab.identita_digitale_id = idg.id
                 JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
                WHERE idg.auth_user_id = pg_temp.au('dev.emittente') AND idg.ruolo_applicativo = 'OPERATORE'),
              (SELECT string_agg(uef.emittente_fiscale_id::text, ',') FROM config.user_emittenti_fiscali uef
                WHERE uef.auth_user_id = pg_temp.au('dev.emittente')) = pg_temp.ef('DEVA')::text),
       'DEV_OPERATIVO|t', '8. dev.emittente: profilo DEV_OPERATIVO, whitelist solo A')
  ELSE skip('mondo CI: django.auth_user non c''e''', 1) END;

SELECT CASE WHEN (SELECT django FROM t_mondo) THEN
    is((SELECT format('%s.%s=%s', uoo.app_label, uoo.model_name, uoo.livello)
          FROM config.user_override_oggetti uoo WHERE uoo.auth_user_id = pg_temp.au('dev.bloccato')),
       'vendite.contratto=BLOCCATO', '9. dev.bloccato: vendite.contratto BLOCCATO')
  ELSE skip('mondo CI: django.auth_user non c''e''', 1) END;

SELECT CASE WHEN (SELECT django FROM t_mondo) THEN
    is((SELECT count(*)::int FROM config.user_emittente_attivo uea
         WHERE uea.auth_user_id IN (SELECT pg_temp.au(u) FROM unnest(ARRAY['dev.smoke', 'dev.lettura', 'dev.bloccato', 'dev.emittente', 'dev.multiveste']) u)
           AND uea.emittente_fiscale_id = pg_temp.ef('DEVA')),
       5, '10. i cinque operatori lavorano su A (emittente attivo)')
  ELSE skip('mondo CI: django.auth_user non c''e''', 1) END;

SELECT CASE WHEN (SELECT django FROM t_mondo) THEN
    is((SELECT string_agg(sp.chiave || '=' || ef.codice, ',' ORDER BY sp.chiave)
          FROM dbops.soggetti_di_prova sp
          JOIN anagrafiche.soggetti_ruoli sr ON sr.soggetto_id = sp.soggetto_id
          JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id AND tr.codice_interno = 'CL'
          JOIN anagrafiche.billing_account ba ON ba.soggetto_ruolo_id = sr.id
          JOIN anagrafiche.emittenti_fiscali_billing_account efba ON efba.billing_account_id = ba.id
          JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = efba.emittente_soggetto_ruolo_id
         WHERE sp.chiave LIKE 'DEV-CLIENTE-%'),
       'DEV-CLIENTE-1=DEVA,DEV-CLIENTE-2=DEVA,DEV-CLIENTE-3=DEVA,DEV-CLIENTE-B=DEVB',
       '11. il cliente B ha il BA legato a B, i clienti 1-3 ad A')
  ELSE skip('mondo CI: django.auth_user non c''e''', 1) END;

SELECT CASE WHEN (SELECT django FROM t_mondo) THEN
    is((SELECT string_agg(mg.codice || ':' || mg.predefinito, ',' ORDER BY mg.codice)
          FROM magazzino.magazzini mg
         WHERE mg.codice IN ('DEVA-MAG', 'DEVB-MAG')
           AND mg.emittente_fiscale_id = pg_temp.ef(substr(mg.codice, 1, 4))),
       'DEVA-MAG:true,DEVB-MAG:true', '12. i due magazzini predefiniti, uno per emittente')
  ELSE skip('mondo CI: django.auth_user non c''e''', 1) END;

SELECT CASE WHEN (SELECT django FROM t_mondo) THEN
    is((SELECT format('%s|%s', count(*), count(*) FILTER (WHERE paa.livello = 'LETTURA'))
          FROM config.profili_accesso pa JOIN config.profili_accesso_aree paa ON paa.profilo_accesso_id = pa.id
         WHERE pa.codice = 'DEV_LETTURA'),
       format('%s|%s', (SELECT count(*) FROM config.aree_funzionali), (SELECT count(*) FROM config.aree_funzionali)),
       '13. DEV_LETTURA ha LETTURA su tutte le aree presenti')
  ELSE skip('mondo CI: django.auth_user non c''e''', 1) END;

SELECT CASE WHEN (SELECT django FROM t_mondo) THEN
    is(script.fn_categoria_accesso(pg_temp.au('dev.lettura'))::text, 'OPERATORE',
       '14. dev.lettura e'' un OPERATORE: la categoria non legge l''etichetta')
  ELSE skip('mondo CI: django.auth_user non c''e''', 1) END;

SELECT is(format('%s|%s', current_setting('app.current_user_id', true), current_setting('app.current_emittente_id', true)),
          (SELECT format('%s|%s', u, e) FROM t_guc),
          '15. le GUC di sessione sono come prima');

-- ============================================================
-- La seconda corsa
-- ============================================================
-- Un'area nuova fra le due corse (test 18), e la password di dev.lettura (17).
DO $area$
BEGIN
    IF (SELECT django FROM t_mondo) THEN
        -- id esplicito: la colonna non ha default (il catalogo e' del CSV).
        INSERT INTO config.aree_funzionali (id, codice, codice_interno, descrizione, schema_db)
        SELECT max(af.id) + 1, 'PGTAP_AREA_NUOVA', 'PGTAP_AREA_NUOVA', 'pgTAP: area nuova fra due corse', 'pgtap_area_nuova'
          FROM config.aree_funzionali af;
    END IF;
END
$area$;

SET CONSTRAINTS ALL DEFERRED;
DO $c2$
BEGIN
    IF (SELECT django FROM t_mondo) THEN
        INSERT INTO t_c2 SELECT * FROM anagrafiche.fn_provisiona_dati_di_sviluppo('{"dev.lettura": "pbkdf2_sha256$pgtap$riallineata"}');
    END IF;
END
$c2$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT CASE WHEN (SELECT django FROM t_mondo) THEN
    is(format('%s|%s|%s', (SELECT count(*) FROM t_c2), (SELECT count(*) FROM t_c2 WHERE esito = 'riallineata'),
              (SELECT count(*) FROM dbops.credenziali_di_prova WHERE chiave LIKE 'dev.%')
              + (SELECT count(*) FROM dbops.soggetti_di_prova WHERE chiave LIKE 'DEV-%')),
       '20|20|20', '16. venti radici, tutte riallineate, nessuna etichetta nuova')
  ELSE skip('mondo CI: django.auth_user non c''e''', 1) END;

SELECT CASE WHEN (SELECT django FROM t_mondo) THEN
    is((SELECT u.password::text FROM django.auth_user u WHERE u.id = pg_temp.au('dev.lettura')),
       'pbkdf2_sha256$pgtap$riallineata', '17. una password data in riallineamento si scrive')
  ELSE skip('mondo CI: django.auth_user non c''e''', 1) END;

SELECT CASE WHEN (SELECT django FROM t_mondo) THEN
    is((SELECT paa.livello::text
          FROM config.profili_accesso pa
          JOIN config.profili_accesso_aree paa ON paa.profilo_accesso_id = pa.id
          JOIN config.aree_funzionali af ON af.id = paa.area_id
         WHERE pa.codice = 'DEV_LETTURA' AND af.schema_db = 'pgtap_area_nuova'),
       'LETTURA', '18. un''area nuova entra nel profilo alla corsa dopo')
  ELSE skip('mondo CI: django.auth_user non c''e''', 1) END;

-- ============================================================
-- L'omonimo senza etichetta (su un mondo senza le radici di prima)
-- ============================================================
CREATE TEMP TABLE t_om (codice text, etichette int);
-- L'etichetta di dev.portale2 si toglie (trigger spento) DENTRO un blocco che
-- poi si annulla: il verbo trova la credenziale senza etichetta. Gli esiti si
-- tengono in variabili e si scrivono dopo l'annullo.
DO $om$
DECLARE
    v_c text;
    v_n int;
BEGIN
    IF (SELECT django FROM t_mondo) THEN
        BEGIN
            ALTER TABLE dbops.credenziali_di_prova DISABLE TRIGGER trg_credenziali_di_prova_a05_guard_ins_upd_dlt;
            DELETE FROM dbops.credenziali_di_prova WHERE chiave = 'dev.portale2';
            ALTER TABLE dbops.credenziali_di_prova ENABLE TRIGGER trg_credenziali_di_prova_a05_guard_ins_upd_dlt;
            BEGIN
                PERFORM * FROM anagrafiche.fn_provisiona_dati_di_sviluppo();
            EXCEPTION WHEN SQLSTATE 'P0001' THEN
                GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
            END;
            SELECT count(*)::int INTO v_n FROM dbops.credenziali_di_prova WHERE chiave = 'dev.portale2';
            RAISE EXCEPTION 'annulla' USING ERRCODE = 'P0002';
        EXCEPTION WHEN SQLSTATE 'P0002' THEN
            NULL;
        END;
        INSERT INTO t_om VALUES (v_c, v_n);
    END IF;
END
$om$;

SELECT CASE WHEN (SELECT django FROM t_mondo) THEN
    is((SELECT codice FROM t_om), 'E_RADICE_DI_PROVA_SENZA_ETICHETTA',
       '19. uno username dell''elenco gia'' preso senza etichetta: E_RADICE_DI_PROVA_SENZA_ETICHETTA')
  ELSE skip('mondo CI: django.auth_user non c''e''', 1) END;

SELECT CASE WHEN (SELECT django FROM t_mondo) THEN
    is((SELECT etichette FROM t_om), 0, '20. ... e non e'' stato adottato (nessuna etichetta)')
  ELSE skip('mondo CI: django.auth_user non c''e''', 1) END;

SELECT * FROM finish();

ROLLBACK;
