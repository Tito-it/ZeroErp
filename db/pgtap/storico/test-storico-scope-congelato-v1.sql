-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test fa DDL — crea madri di prova in vendite/acquisti
--   con le loro shadow e i loro trigger, e mette FORCE ROW LEVEL SECURITY sulla
--   shadow di prova: e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   chi fa la DDL lavora come proprietario (zeroerp_owner) e non puo' diventare
--   zeroerp_app nella stessa transazione: il ruolo di login non ne e' membro.
--   rev 2026-11-09 (brief-db-revisione-dbops, giro 14, M37). E la fixture costruisce
--   DUE aziende: un operatore dentro un perimetro non potrebbe crearle.
-- pgTAP test — lo SCOPE CONGELATO delle shadow di storico
--   fn_storico_arma_scope · fn_ensure_storico_table · trgfn_storico_generic ·
--   fn_storico_risolvi_scope (ripiego sull'archivio del padre)
--
-- Brief: brief-db-rls-storico-scope-congelato.md §4b (D1, D2, D4), §5 passi 3-6
-- ChangeSet: 20260911-24 · -25 · -26 · -27 · -28 · -29 · -31
--
-- ⭐ LA STORIA DI UNA RIGA PROTETTA E' LA STESSA INFORMAZIONE DELLA RIGA. Ogni
--   versione porta l'emittente di ALLORA, congelato alla scrittura, e la shadow
--   lo filtra per l'operatore come la madre filtra la riga.
--
-- ⚠️ I TEST 2, 3 E 22 SONO ROSSI SU DEV FINCHE' NON PASSA IL PROVISIONING: 66 shadow
--   sono di `postgres` e i changeSet non possono alterarle (WARN nell'audit).
--   Il rimedio e' `scripts/sql/provision_storico_scope.sql` da superuser. Non e'
--   un difetto del test: e' esattamente cio' che deve dire. In CI sono verdi.
--
-- ⭐ IL COMPORTAMENTO SI PROVA SU MADRI COSTRUITE, non sui dati: due aziende
--   (fn_pgtap_crea_emittente_operatore), tre madri di prova — `vendite.zz_…`
--   (EF), `acquisti.zz_…` OMONIMA (NESSUNO: e' la shadow condivisa del §4b.2) e
--   una figlia con FK ON DELETE CASCADE (PADRE) — dichiarate nella mappa dentro
--   la transazione. Il ROLLBACK pulisce tutto.
--
-- Elenco test (plan 23):
--   STRUTTURA — le shadow vere
--    1  : gemello «esiste»: ci sono madri col trigger di storico
--    2  : ogni shadow di una madre col trigger ha le due colonne (dev: provisioning)
--    3  : ogni shadow di una madre PROTETTA ha la RLS accesa e le tre policy
--    4  : gemello del 3: almeno una madre protetta con shadow
--    5  : nessuna shadow armata se TUTTE le sue madri sono NESSUNO
--    6  : la policy di lettura filtra su scope_emittente_fiscale_id, veste OPERATORE,
--         fn_scope_ef_perimetro col perimetro in sottoquery — la rotta, non
--         un'altra (rev 2026-10-18, D-3b-2: era fn_scope_ef_whitelist per riga)
--    7  : le policy di scrittura sono INSERT/UPDATE con «true»
--   COMPORTAMENTO — madri costruite
--    8  : la shadow di prova NASCE armata: RLS, tre policy, origine_schema NOT NULL
--    9  : ogni versione porta origine_schema = lo schema della madre
--   10  : la versione di A porta l'EF di A, quella di B l'EF di B
--   11  : la versione della madre NESSUNO (acquisti) porta origine e scope NULL
--   12  : ⭐ collisione: vendite id 1 e acquisti id 1 nella stessa shadow, ciascuna
--         con la SUA versione aperta — non si chiudono a vicenda (D2)
--   13  : la versione precedente di vendite id 1 e' chiusa (la chiusura funziona)
--   14  : ⭐ DELETE a cascata: la versione finale della figlia porta l'EF del padre
--         letto dall'ARCHIVIO del padre, che non e' piu' vivo (ripiego del resolver)
--   15  : ⭐ CONGELATO: cambiato l'emittente della madre, le versioni PRECEDENTI
--         restano con quello di allora; solo la nuova porta il nuovo
--   LETTURA SOTTO RLS — FORCE sulla shadow di prova
--   16  : l'operatore A vede le versioni di A
--   17  : ⛔ e non quelle di B
--   18  : ⛔ ne' quelle senza scope (acquisti): fail-closed
--   19  : ⛔ senza veste applicativa: niente
--   20  : ⭐ il trigger SCRIVE attraverso la RLS: l'operatore A aggiorna la sua riga,
--         la versione nuova c'e' e la precedente si chiude (policy di scrittura «true»)
--   21  : gemello del 20: le versioni aperte di A restano UNA
--   GRANT — passo 7
--   22  : ⛔ zeroerp_app non ha DELETE su nessuna shadow: uno snapshot non si
--         cancella (dev: provisioning)
--   PROPRIETA' — decisione (a), §4d
--   23  : ogni shadow ha lo STESSO proprietario della madre: l'archivio di una
--         tabella e' di chi possiede la tabella (il generatore la cede, rev -34)
-- ------------------------------------------------------------

BEGIN;

-- pgtap-contesto: escluso — il contesto operatore si imposta PIU' SOTTO, sulle
--   due aziende costruite dal test (A e B), non su quello generico: qui la
--   domanda e' proprio «chi vede cosa», e serve sapere chi e' A.

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(23);

-- Canale dblink spento: gli audit delle primitive e le versioni di prova devono
-- morire col ROLLBACK.
SET LOCAL myapp.log_with_dblink = 'off';

-- ============================================================
-- STRUTTURA — le shadow vere
-- ============================================================
CREATE TEMP TABLE _madri ON COMMIT DROP AS
SELECT DISTINCT n.nspname AS sch, c.relname AS tab,
       pg_catalog.to_regclass(format('storico.%I', c.relname)) AS sto_oid
  FROM pg_trigger t
  JOIN pg_class c     ON c.oid = t.tgrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  JOIN pg_proc p      ON p.oid = t.tgfoid
 WHERE p.proname = 'trgfn_storico_generic' AND NOT t.tgisinternal;

SELECT cmp_ok((SELECT count(*) FROM _madri), '>', 0::bigint,
              '1. gemello «esiste»: ci sono madri col trigger di storico');

SELECT is((SELECT count(DISTINCT m.sto_oid) FROM _madri m
            WHERE m.sto_oid IS NOT NULL
              AND (   NOT EXISTS (SELECT 1 FROM pg_attribute a WHERE a.attrelid = m.sto_oid AND a.attname = 'origine_schema' AND NOT a.attisdropped)
                   OR NOT EXISTS (SELECT 1 FROM pg_attribute a WHERE a.attrelid = m.sto_oid AND a.attname = 'scope_emittente_fiscale_id' AND NOT a.attisdropped))),
          0::bigint,
          '2. ogni shadow di una madre col trigger ha origine_schema e scope_emittente_fiscale_id (su dev: provisioning da superuser)');

-- Le madri PROTETTE secondo la mappa, e la loro shadow.
CREATE TEMP TABLE _protette ON COMMIT DROP AS
SELECT m.sch, m.tab, m.sto_oid
  FROM _madri m
  JOIN dbops.storico_scope_policy p ON p.schema_tabella = m.sch AND p.nome_tabella = m.tab
 WHERE p.modo <> 'NESSUNO' AND m.sto_oid IS NOT NULL;

SELECT is((SELECT count(*) FROM _protette pr
            WHERE NOT (SELECT c.relrowsecurity FROM pg_class c WHERE c.oid = pr.sto_oid)
               OR (SELECT count(*) FROM pg_policy pol WHERE pol.polrelid = pr.sto_oid
                    AND pol.polname IN (left(format('rls_sto_%s_ef_whitelist', pr.tab), 63),
                                        left(format('rls_sto_%s_trg_ins', pr.tab), 63),
                                        left(format('rls_sto_%s_trg_upd', pr.tab), 63))) <> 3),
          0::bigint,
          '3. ogni shadow di una madre protetta ha la RLS accesa e le tre policy (su dev: provisioning da superuser)');

SELECT cmp_ok((SELECT count(*) FROM _protette), '>', 0::bigint,
              '4. gemello del 3: almeno una madre protetta con shadow');

SELECT is((SELECT count(*) FROM (SELECT DISTINCT sto_oid FROM _madri WHERE sto_oid IS NOT NULL) s
            WHERE (SELECT c.relrowsecurity FROM pg_class c WHERE c.oid = s.sto_oid)
              AND NOT EXISTS (SELECT 1 FROM _protette pr WHERE pr.sto_oid = s.sto_oid)),
          0::bigint,
          '5. nessuna shadow armata se tutte le sue madri sono NESSUNO: non si arma per sbaglio');

-- ⛔ La ROTTA della policy, non solo la sua esistenza (lezione della slice
--   arrotondamenti): filtra sulla colonna congelata, con la funzione di scope
--   EF, per la veste OPERATORE.
-- ⭐ Rev 2026-10-18 (D-3b-2, 20261018-20/-21): la funzione di scope e'
--   fn_scope_ef_perimetro e il perimetro le arriva in una sottoquery
--   (`fn_scope_ef_perimetro((SELECT ...`): e' cio' che lo fa calcolare una
--   volta per istruzione invece che per riga.
SELECT is((SELECT count(*) FROM _protette pr
             JOIN pg_policy pol ON pol.polrelid = pr.sto_oid
                               AND pol.polname = left(format('rls_sto_%s_ef_whitelist', pr.tab), 63)
            WHERE pol.polcmd <> 'r'
               OR pg_get_expr(pol.polqual, pol.polrelid) NOT LIKE '%fn_scope_ef_perimetro(( SELECT %scope_emittente_fiscale_id)%'
               OR pg_get_expr(pol.polqual, pol.polrelid) NOT LIKE '%''OPERATORE''%'),
          0::bigint,
          '6. la policy di lettura e'' FOR SELECT, veste OPERATORE, fn_scope_ef_perimetro col perimetro in sottoquery su scope_emittente_fiscale_id');

SELECT is((SELECT count(*) FROM _protette pr
             JOIN pg_policy pol ON pol.polrelid = pr.sto_oid
                               AND pol.polname IN (left(format('rls_sto_%s_trg_ins', pr.tab), 63),
                                                   left(format('rls_sto_%s_trg_upd', pr.tab), 63))
            WHERE NOT (   (pol.polcmd = 'a' AND pg_get_expr(pol.polwithcheck, pol.polrelid) = 'true')
                       OR (pol.polcmd = 'w' AND pg_get_expr(pol.polqual, pol.polrelid) = 'true'
                                            AND pg_get_expr(pol.polwithcheck, pol.polrelid) = 'true'))),
          0::bigint,
          '7. le policy di scrittura del trigger sono INSERT / UPDATE con «true»: la scrittura non si filtra');

-- ============================================================
-- COMPORTAMENTO — madri costruite, due aziende
-- ============================================================
CREATE TEMP TABLE _mondi ON COMMIT DROP AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Tre madri di prova. ⚠️ Nomi con prefisso zz_pgtap: vivono solo in questa
-- transazione. La colonna `storicizza` e' il contratto del trigger.
CREATE TABLE vendite.zz_pgtap_scope (
    id                   bigint PRIMARY KEY,
    emittente_fiscale_id bigint NOT NULL,
    nota                 text,
    storicizza           boolean NOT NULL DEFAULT true);
CREATE TABLE acquisti.zz_pgtap_scope (           -- OMONIMA: stessa shadow (D2)
    id                   bigint PRIMARY KEY,
    fornitore_nota       text,
    storicizza           boolean NOT NULL DEFAULT true);
CREATE TABLE vendite.zz_pgtap_scope_riga (        -- figlia, FK a cascata (PADRE)
    id                   bigint PRIMARY KEY,
    zz_pgtap_scope_id    bigint NOT NULL REFERENCES vendite.zz_pgtap_scope (id) ON DELETE CASCADE,
    qta                  integer,
    storicizza           boolean NOT NULL DEFAULT true);

INSERT INTO dbops.storico_scope_policy (id, schema_tabella, nome_tabella, modo, colonna, padre_schema, padre_tabella, ragione) VALUES
    (900101, 'vendite',  'zz_pgtap_scope',      'EF',      'emittente_fiscale_id', NULL, NULL, NULL),
    (900102, 'acquisti', 'zz_pgtap_scope',      'NESSUNO', NULL, NULL, NULL,
             'Madre di prova del pgTAP, omonima di vendite.zz_pgtap_scope: e'' la shadow condivisa del §4b.2, senza asse emittente.'),
    (900103, 'vendite',  'zz_pgtap_scope_riga', 'PADRE',   'zz_pgtap_scope_id', 'vendite', 'zz_pgtap_scope', NULL);

-- ⚠️ Memoria CONTINUA: senza questa registrazione il trigger spegne `storicizza`
--   dopo la prima modifica («a richiesta», Fase 5 di trgfn_storico_generic) e le
--   scritture successive — il cambio di emittente, il DELETE a cascata, la
--   scrittura di A sotto RLS — non produrrebbero nessuna versione. Trovato alla
--   prima corsa: tre test rossi con «have: NULL / 0», e il meccanismo era sano.
INSERT INTO config.storico_set_storicizza (table_name) VALUES
    ('vendite.zz_pgtap_scope'), ('acquisti.zz_pgtap_scope'), ('vendite.zz_pgtap_scope_riga');

-- Le shadow le crea il generatore (la seconda chiamata trova la condivisa e
-- torna); i trigger si montano a mano come farebbe l'automazione.
SELECT dbops.fn_ensure_storico_table('vendite',  'zz_pgtap_scope',      'zz_pgtap_scope_id',      false, false);
SELECT dbops.fn_ensure_storico_table('acquisti', 'zz_pgtap_scope',      'zz_pgtap_scope_id',      false, false);
SELECT dbops.fn_ensure_storico_table('vendite',  'zz_pgtap_scope_riga', 'zz_pgtap_scope_riga_id', false, false);
CREATE TRIGGER trg_zz_pgtap_scope_z90_storico_upd_dlt BEFORE UPDATE OR DELETE ON vendite.zz_pgtap_scope
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_storico_generic('zz_pgtap_scope_id');
CREATE TRIGGER trg_zz_pgtap_scope_z90_storico_upd_dlt BEFORE UPDATE OR DELETE ON acquisti.zz_pgtap_scope
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_storico_generic('zz_pgtap_scope_id');
CREATE TRIGGER trg_zz_pgtap_scope_riga_z90_storico_upd_dlt BEFORE UPDATE OR DELETE ON vendite.zz_pgtap_scope_riga
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_storico_generic('zz_pgtap_scope_riga_id');

SELECT ok((SELECT c.relrowsecurity FROM pg_class c WHERE c.oid = 'storico.zz_pgtap_scope'::regclass)
          AND (SELECT count(*) FROM pg_policy WHERE polrelid = 'storico.zz_pgtap_scope'::regclass) = 3
          AND (SELECT a.attnotnull FROM pg_attribute a WHERE a.attrelid = 'storico.zz_pgtap_scope'::regclass AND a.attname = 'origine_schema'),
          '8. la shadow di prova nasce ARMATA dal generatore: RLS, tre policy, origine_schema NOT NULL');

-- Le righe: vendite A (id 1) e B (id 2), acquisti id 1 (stesso id di A!), una
-- figlia di A e una di B. Poi un UPDATE ciascuna: e' cio' che scrive le versioni.
INSERT INTO vendite.zz_pgtap_scope (id, emittente_fiscale_id, nota)
SELECT 1, emittente_fiscale_id, 'A' FROM _mondi WHERE lato = 'A';
INSERT INTO vendite.zz_pgtap_scope (id, emittente_fiscale_id, nota)
SELECT 2, emittente_fiscale_id, 'B' FROM _mondi WHERE lato = 'B';
INSERT INTO acquisti.zz_pgtap_scope (id, fornitore_nota) VALUES (1, 'acquisto');
INSERT INTO vendite.zz_pgtap_scope_riga (id, zz_pgtap_scope_id, qta) VALUES (10, 1, 1), (20, 2, 2);

UPDATE vendite.zz_pgtap_scope  SET nota = nota || '!' WHERE id IN (1, 2);
UPDATE acquisti.zz_pgtap_scope SET fornitore_nota = 'acquisto!' WHERE id = 1;
UPDATE vendite.zz_pgtap_scope_riga SET qta = qta + 1 WHERE id IN (10, 20);

SELECT is((SELECT count(*) FROM storico.zz_pgtap_scope s WHERE s.origine_schema IS NULL
              OR s.origine_schema NOT IN ('vendite', 'acquisti')),
          0::bigint,
          '9. ogni versione porta origine_schema = lo schema della madre che l''ha scritta');

SELECT ok((SELECT s.scope_emittente_fiscale_id FROM storico.zz_pgtap_scope s
            WHERE s.origine_schema = 'vendite' AND s.zz_pgtap_scope_id = 1 AND s.valid_to IS NULL)
              = (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'A')
          AND (SELECT s.scope_emittente_fiscale_id FROM storico.zz_pgtap_scope s
                WHERE s.origine_schema = 'vendite' AND s.zz_pgtap_scope_id = 2 AND s.valid_to IS NULL)
              = (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'B'),
          '10. la versione aperta di A porta l''EF di A, quella di B l''EF di B');

SELECT ok((SELECT count(*) FROM storico.zz_pgtap_scope s
            WHERE s.origine_schema = 'acquisti' AND s.zz_pgtap_scope_id = 1) > 0
          AND (SELECT bool_and(s.scope_emittente_fiscale_id IS NULL) FROM storico.zz_pgtap_scope s
                WHERE s.origine_schema = 'acquisti'),
          '11. la madre NESSUNO scrive le sue versioni con origine acquisti e scope NULL');

SELECT is((SELECT string_agg(origine_schema || ':' || n, ',' ORDER BY origine_schema)
             FROM (SELECT s.origine_schema, count(*) AS n FROM storico.zz_pgtap_scope s
                    WHERE s.zz_pgtap_scope_id = 1 AND s.valid_to IS NULL GROUP BY 1) x),
          'acquisti:1,vendite:1',
          '12. collisione: vendite id 1 e acquisti id 1 hanno ciascuna la SUA versione aperta — non si chiudono a vicenda');

SELECT is((SELECT count(*) FROM storico.zz_pgtap_scope s
            WHERE s.origine_schema = 'vendite' AND s.zz_pgtap_scope_id = 1 AND s.valid_to IS NOT NULL),
          1::bigint,
          '13. la versione precedente di vendite id 1 e'' chiusa: la chiusura nello stesso schema funziona');

-- ⭐ DELETE a cascata su B: il padre sparisce PRIMA che la figlia scriva la sua
--   versione finale. Lo scope della figlia viene dall'ARCHIVIO del padre.
DELETE FROM vendite.zz_pgtap_scope WHERE id = 2;
SELECT is((SELECT s.scope_emittente_fiscale_id FROM storico.zz_pgtap_scope_riga s
            WHERE s.zz_pgtap_scope_riga_id = 20 AND s.tipo_operazione = 3),
          (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'B'),
          '14. DELETE a cascata: la versione finale della figlia porta l''EF del padre, letto dal suo archivio');

-- ⭐ CONGELATO: la madre A cambia emittente (il modello non lo ammette sui
--   documenti veri, qui serve a provare che l'archivio NON segue il presente).
UPDATE vendite.zz_pgtap_scope SET emittente_fiscale_id = (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'B')
 WHERE id = 1;
SELECT ok((SELECT bool_and(s.scope_emittente_fiscale_id = (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'A'))
             FROM storico.zz_pgtap_scope s
            WHERE s.origine_schema = 'vendite' AND s.zz_pgtap_scope_id = 1 AND s.valid_to IS NOT NULL)
          AND (SELECT s.scope_emittente_fiscale_id FROM storico.zz_pgtap_scope s
                WHERE s.origine_schema = 'vendite' AND s.zz_pgtap_scope_id = 1 AND s.valid_to IS NULL)
              = (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'B'),
          '15. CONGELATO: le versioni precedenti restano con l''emittente di allora, solo la nuova porta il nuovo');
-- Torna ad A: i test di lettura sotto contano le versioni di A.
UPDATE vendite.zz_pgtap_scope SET emittente_fiscale_id = (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'A')
 WHERE id = 1;

-- ============================================================
-- LETTURA SOTTO RLS — l'owner diventa soggetto alle policy col FORCE
-- ============================================================
ALTER TABLE storico.zz_pgtap_scope FORCE ROW LEVEL SECURITY;

DO $perimetro$
DECLARE
    v_ef_a bigint := (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'A');
    v_ef_b bigint := (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'B');
    v_n    bigint;
    v_aperte_prima bigint;
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondi WHERE lato = 'A'));

    SELECT count(*) INTO v_n FROM storico.zz_pgtap_scope s WHERE s.scope_emittente_fiscale_id = v_ef_a;
    PERFORM set_config('pgtap.vede_a', v_n::text, true);

    SELECT count(*) INTO v_n FROM storico.zz_pgtap_scope s WHERE s.scope_emittente_fiscale_id = v_ef_b;
    PERFORM set_config('pgtap.vede_b', v_n::text, true);

    SELECT count(*) INTO v_n FROM storico.zz_pgtap_scope s WHERE s.origine_schema = 'acquisti';
    PERFORM set_config('pgtap.vede_null', v_n::text, true);

    -- ⭐ Il trigger scrive ATTRAVERSO la RLS: A aggiorna la propria riga.
    SELECT count(*) INTO v_aperte_prima FROM storico.zz_pgtap_scope s
     WHERE s.origine_schema = 'vendite' AND s.zz_pgtap_scope_id = 1 AND s.valid_to IS NULL;
    UPDATE vendite.zz_pgtap_scope SET nota = 'scritta da A' WHERE id = 1;
    SELECT count(*) INTO v_n FROM storico.zz_pgtap_scope s
     WHERE s.origine_schema = 'vendite' AND s.zz_pgtap_scope_id = 1 AND s.snapshot ->> 'nota' = 'scritta da A';
    PERFORM set_config('pgtap.scritta', v_n::text, true);
    SELECT count(*) INTO v_n FROM storico.zz_pgtap_scope s
     WHERE s.origine_schema = 'vendite' AND s.zz_pgtap_scope_id = 1 AND s.valid_to IS NULL;
    PERFORM set_config('pgtap.aperte', v_n::text, true);

    -- ⛔ Nessuna veste: fail-closed.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    SELECT count(*) INTO v_n FROM storico.zz_pgtap_scope;
    PERFORM set_config('pgtap.senza_veste', v_n::text, true);
END
$perimetro$;

ALTER TABLE storico.zz_pgtap_scope NO FORCE ROW LEVEL SECURITY;

SELECT cmp_ok(current_setting('pgtap.vede_a')::bigint, '>', 0::bigint,
              '16. l''operatore A vede le versioni di A');
SELECT is(current_setting('pgtap.vede_b')::bigint, 0::bigint,
          '17. e non vede quelle di B');
SELECT is(current_setting('pgtap.vede_null')::bigint, 0::bigint,
          '18. ne'' quelle senza scope (madre NESSUNO): fail-closed');
SELECT is(current_setting('pgtap.senza_veste')::bigint, 0::bigint,
          '19. senza veste applicativa: niente');
SELECT is(current_setting('pgtap.scritta')::bigint, 1::bigint,
          '20. il trigger scrive attraverso la RLS: la versione di A c''e'' (policy INSERT «true»)');
SELECT is(current_setting('pgtap.aperte')::bigint, 1::bigint,
          '21. e la precedente si e'' chiusa (policy UPDATE «true»): le versioni aperte di A restano una');

-- ============================================================
-- GRANT — passo 7
-- ============================================================
-- ⛔ Uno snapshot non si cancella: la retention è del proprietario. Il DELETE
--   lo darebbero il loop dei grant, il provisioning e i DEFAULT PRIVILEGES; lo
--   toglie fn_storico_arma_scope, shadow per shadow (dev: provisioning).
SELECT is((SELECT count(DISTINCT m.sto_oid) FROM _madri m
            WHERE m.sto_oid IS NOT NULL
              AND has_table_privilege('zeroerp_app', m.sto_oid, 'DELETE')),
          0::bigint,
          '22. zeroerp_app non ha DELETE su nessuna shadow: uno snapshot non si cancella (su dev: provisioning da superuser)');

-- ============================================================
-- PROPRIETA' — decisione (a)
-- ============================================================
-- ⭐ Il job pgAgent crea come `postgres`, il generatore cede al proprietario
--   della madre (rev -34). Una shadow con proprietario diverso dalla madre e'
--   una shadow che la convergenza salterebbe: il presidio la vede.
SELECT is((SELECT count(*) FROM _madri m
             JOIN pg_class ms ON ms.oid = to_regclass(format('%I.%I', m.sch, m.tab))
             JOIN pg_class ss ON ss.oid = m.sto_oid
            WHERE ms.relowner <> ss.relowner),
          0::bigint,
          '23. ogni shadow ha lo stesso proprietario della madre: l''archivio e'' di chi possiede la tabella');

SELECT * FROM finish();
ROLLBACK;
