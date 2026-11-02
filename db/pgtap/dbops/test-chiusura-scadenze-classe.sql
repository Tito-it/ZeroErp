-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture semina su dbops.automazione_chiusura_scadenze,
--   catalogo che a runtime NON scrive nessuno (lo popola il mirror CSV di
--   80_data) e che il framework legge per decidere quali tabelle toccare.
--   Verificato cercando gli scrittori, non dedotto.
--
-- Test: la classe per BERSAGLIO in dbops.fn_apply_chiusura_scadenze
-- Brief: brief-db-processi-automatici-identita-e-perimetro §6 (fase 5)
--
-- Elenco test (plan 6):
--  1) automazione_chiusura_scadenze ha la colonna classe
--  2) il CHECK respinge una classe fuori vocabolario
--  3) ⭐ il CANCELLO: la colonna e' NOT NULL — una riga nuova deve dichiararsi
--  4) i due bersagli seedati sono entrambi DOMINIO
--  5) la funzione accetta la chiamata SENZA argomenti (job pgAgent invariato)
--  6) ⭐ chiamata con una classe, lavora SOLO i bersagli di quella classe
--
-- Scopo:
--  - distinguere le DUE cose che la fase 5 introduce, perche' si confondono:
--    il FILTRO `p_classe` sceglie cosa lavorare in un giro (test 5 e 6), il
--    CANCELLO e' il NOT NULL che decide cosa puo' entrare in tabella (test 3);
--  - fissare che il job pgAgent non e' stato toccato (test 5): `85_pgagent` in
--    CI non gira mai, quindi una rottura li' si scoprirebbe solo a mano.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- 1..3. La colonna, il vocabolario, il cancello
-- ============================================================
SELECT has_column('dbops', 'automazione_chiusura_scadenze', 'classe',
                  'automazione_chiusura_scadenze ha la colonna classe');

SELECT throws_ok(
    $$INSERT INTO dbops.automazione_chiusura_scadenze
          (id, schema_tabella, nome_tabella, col_stato, tipo_stato,
           stato_attivo_codice, stato_chiuso_codice, classe)
      VALUES (9601, 'vendite', 'pgtap_finto', 'stato', 'VARCHAR',
              'ATTIVO', 'CHIUSO', 'FANTASIA')$$,
    '23514',
    NULL,
    'il CHECK respinge una classe fuori vocabolario'
);

-- ⭐ IL CANCELLO DELLA FASE. Il filtro sceglie cosa lavorare; questo decide
--   cosa puo' ENTRARE. Senza, una riga nuova nel CSV arruolerebbe un'altra
--   tabella nel giro notturno senza dichiarare di che natura e' — che e'
--   esattamente il difetto per cui la fase 5 esiste.
SELECT throws_ok(
    $$INSERT INTO dbops.automazione_chiusura_scadenze
          (id, schema_tabella, nome_tabella, col_stato, tipo_stato,
           stato_attivo_codice, stato_chiuso_codice)
      VALUES (9602, 'vendite', 'pgtap_finto', 'stato', 'VARCHAR',
              'ATTIVO', 'CHIUSO')$$,
    '23502',
    NULL,
    'una riga senza classe non entra: e'' il cancello della fase'
);

-- ============================================================
-- 4. Il seed
-- ============================================================
-- Entrambi i bersagli portano l'emittente: `vendite.contratti` con la colonna
-- diretta, `vendite.listini_versioni` attraverso il listino. Quindi il job e'
-- di dominio per intero — non si spacca (brief §8.2).
SELECT is_empty(
    $$SELECT nome_tabella
        FROM dbops.automazione_chiusura_scadenze
       WHERE attivo AND classe <> 'DOMINIO'$$,
    'i bersagli seedati sono tutti di classe DOMINIO'
);

-- ============================================================
-- 5..6. Il filtro
-- ============================================================
-- ⚠️ Il job pgAgent chiama `dbops.fn_apply_chiusura_scadenze()` senza
--   argomenti, e `85_pgagent` in CI non gira MAI (MARK_RAN): se la chiamata a
--   zero argomenti si rompesse, lo si scoprirebbe solo a mano, di notte.
SELECT lives_ok(
    $$SELECT dbops.fn_apply_chiusura_scadenze()$$,
    'la chiamata senza argomenti funziona: il job pgAgent non e'' stato toccato'
);

-- ⭐ E il filtro fa il suo mestiere: chiesta una classe che nessun bersaglio
--   attivo ha, il giro non tocca niente. E' cio' che permettera' ai bersagli di
--   DOMINIO di migrare sulla coda senza che pgAgent li lavori due volte.
-- ⚠️ La forma del ritorno e' VERIFICATA sul corpo vivo, non supposta: un
--   oggetto con una chiave per bersaglio piu' `_total` e `_executed_at`.
--   Asserire su una chiave inventata avrebbe dato un verde per sottrazione.
SELECT is(
    (dbops.fn_apply_chiusura_scadenze('MANUTENZIONE') ->> '_total')::int,
    0,
    'chiamata con una classe senza bersagli attivi, non lavora nulla'
);

SELECT * FROM finish();

ROLLBACK;
