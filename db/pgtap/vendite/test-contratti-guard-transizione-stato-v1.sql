-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-26 (brief-modello-documento-vendita §11): il contratto ha la porta sulla colonna di
--   stato (E_DOC_STATO_SOLO_DAL_VERBO) e il guard di transizione legge la matrice. Le transizioni
--   provate (1, 2, 3, 6, 8) passano dal verbo vendite.fn_cambia_stato_contratto, che arriva al
--   guard (prima UPDATE diretti); 2, 3, 6 con throws_like sulla frase del rifiuto. Il 3 toglie la
--   data e chiede la cessazione nello stesso blocco, sullo slot _E (su _B l'EXCLUDE di
--   sovrapposizione arrivava prima del guard). _D a CESSATO dalla fixture (valido_al 2019
--   gia' arrivata: niente GUC). Il 7 resta un UPDATE: prova che un UPDATE che non cambia lo stato
--   non scatta (ne' il guard ne' la porta).
--   Attese cambiate: 4 (era «ATTIVO -> CESSATO con valido_al futuro AMMESSO»): il cambio di stato
--   con una data futura e' RIFIUTATO (E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA); la cessazione
--   programmata passa da vendite.fn_cessa_contratto, che scrive la sola data e lascia ATTIVO
--   (nuovi 4b, 4c). 5: la cessazione retroattiva la rifiuta il verbo della cessazione
--   (vendite.fn_cessa_contratto con la data passata, stesso E_CONTRATTO_VALIDO_AL_RETROATTIVO), non
--   piu' il guard: un cambio di stato su un contratto con valido_al gia' passata e' ora ammesso
--   (e' la strada del job). 9: la GUC app.cessazione_automatica e' ritirata; il job e'
--   vendite.fn_cessa_contratti_scaduti (chiamato da dbops.fn_apply_chiusura_scadenze), e il
--   nuovo 10 verifica che _C sia CESSATO. Plan 9 -> 12.
-- pgTAP test per Zero ERP
--
-- Test: guard transizione stato su vendite.contratti
--       (migration 20260426-05, aggiornato 20260514-02).
--
-- Indice test (1..12):
--   1) DRAFT -> ATTIVO ammesso (dal verbo)
--   2) ATTIVO -> DRAFT vietato (E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA)
--   3) ATTIVO -> CESSATO con valido_al NULL vietato
--   4) ATTIVO -> CESSATO con valido_al futuro dal cambio di stato: RIFIUTATO  [rev 2026-10-26, attesa cambiata]
--   4b) cessazione programmata (vendite.fn_cessa_contratto, data futura): programmata, stato ATTIVO  [rev 2026-10-26]
--   4c) dopo la cessazione programmata: contratto ATTIVO con la data nuova  [rev 2026-10-26]
--   5) cessazione con valido_al passato VIETATA (E_CONTRATTO_VALIDO_AL_RETROATTIVO, dal verbo della cessazione) [rev 2026-10-26]
--   6) CESSATO -> ATTIVO vietato (stato terminale)
--   7) ATTIVO -> ATTIVO no-op ammesso (WHEN distinct filter)
--   8) ATTIVO -> CESSATO con valido_al = script.fn_data_operativa() ammesso
--   9) Job automatico (vendite.fn_cessa_contratti_scaduti): valido_al passato, gira  [rev 2026-10-26]
--  10) dopo il job: _C e' CESSATO  [rev 2026-10-26]
--
-- Strategia fixture:
--   - Clona BA da seed esistente (utility commercio, no tipi_utenze)
--     per non incrociare il guard tipo_classe.
--   - Crea contratti modalita' A (listino + variazione globale) con
--     periodi disgiunti per non violare ex_contratti_no_overlap.
--   - SOSPESO escluso dai test: non in scope per il guard attuale.
--
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i contratti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima nascevano
--   gia' ATTIVO o CESSATO). _D (valido_al 2019, passato) arriva a CESSATO per la
--   strada del job notturno (GUC app.cessazione_automatica, come al test 9): la
--   cessazione manuale retroattiva e' vietata, ed e' il caso del test 5.
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- ============================================================
-- Setup fixture: BA + lookup stati
-- ============================================================
-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.6.5): il
--   cliente e il billing account sono COSTRUITI (dbops.fn_pgtap_crea_cliente_ba),
--   come il listino. Prima erano «il primo BA per id» del DB: su un database
--   ricostruito da zero (CI) non c'e' nessun BA e il file era nel registro dei
--   rossi di CI per questo.
CREATE TEMP TABLE tmp_ctx_ba AS
SELECT billing_account_id, istanza_utility_id, utility_id
  FROM dbops.fn_pgtap_crea_cliente_ba(
    'guard transizione contratto',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_ctx_stati AS
SELECT
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT')   AS id_draft,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO')  AS id_attivo,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'CESSATO') AS id_cessato;

-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.1.2, A-D2): il
--   listino e' COSTRUITO, con una versione valida da oggi. Prima era «il primo
--   listino attivo per id» del DB, e il fixture ci ATTIVA dei contratti: da quel
--   giorno un contratto con un listino senza versione in vigore non si attiva
--   piu', e l'esito dipendeva da cosa c'era sulla macchina.
CREATE TEMP TABLE tmp_ctx_listino AS
SELECT listino_id FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_ctx_ba), 'guard transizione contratto');

-- ============================================================
-- Slot fixture: 6 contratti modalita' A su periodi disgiunti.
--   _A   DRAFT  2080-01-01..2080-12-31 (test 1: DRAFT->ATTIVO)
--   _B   ATTIVO 2081-01-01..2081-12-31 (test 2; valido_al futuro per test 4, 4b, 4c)
--   _C   ATTIVO 2020-01-01..2020-12-31 (test 5: valido_al passato; test 9-10: il job)
--   _D   CESSATO 2019-01-01..2019-12-31 (test 6: terminale)
--   _E   ATTIVO 2082-01-01..2082-12-31 (test 3: senza data; test 7: no-op)
--   _F   ATTIVO script.fn_data_operativa()-30..script.fn_data_operativa() (test 8: valido_al = oggi)
-- ============================================================

INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al,
    listino_id, tipo_variazione_globale, valore_variazione_globale
)
SELECT 'PGTAP_GUARD_A', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       DATE '2080-01-01', DATE '2080-12-31',
       l.listino_id, 'PERCENTUALE', -10
  FROM tmp_ctx_ba ba, tmp_ctx_listino l;

INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al,
    listino_id, tipo_variazione_globale, valore_variazione_globale
)
SELECT 'PGTAP_GUARD_B', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       DATE '2081-01-01', DATE '2081-12-31',
       l.listino_id, 'PERCENTUALE', -10
  FROM tmp_ctx_ba ba, tmp_ctx_listino l;

INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al,
    listino_id, tipo_variazione_globale, valore_variazione_globale
)
SELECT 'PGTAP_GUARD_C', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       DATE '2020-01-01', DATE '2020-12-31',
       l.listino_id, 'PERCENTUALE', -10
  FROM tmp_ctx_ba ba, tmp_ctx_listino l;

INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al,
    listino_id, tipo_variazione_globale, valore_variazione_globale
)
SELECT 'PGTAP_GUARD_D', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       DATE '2019-01-01', DATE '2019-12-31',
       l.listino_id, 'PERCENTUALE', -10
  FROM tmp_ctx_ba ba, tmp_ctx_listino l;

INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al,
    listino_id, tipo_variazione_globale, valore_variazione_globale
)
SELECT 'PGTAP_GUARD_E', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       DATE '2082-01-01', DATE '2082-12-31',
       l.listino_id, 'PERCENTUALE', -10
  FROM tmp_ctx_ba ba, tmp_ctx_listino l;

INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al,
    listino_id, tipo_variazione_globale, valore_variazione_globale
)
SELECT 'PGTAP_GUARD_F', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       script.fn_data_operativa() - 30, script.fn_data_operativa(),
       l.listino_id, 'PERCENTUALE', -10
  FROM tmp_ctx_ba ba, tmp_ctx_listino l;

-- Gli stati di partenza, per la matrice e sotto i guard veri (rev 2026-10-24).
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti', k.id, 'ATTIVO')
  FROM vendite.contratti k
 WHERE k.numero IN ('PGTAP_GUARD_B', 'PGTAP_GUARD_C', 'PGTAP_GUARD_D',
                    'PGTAP_GUARD_E', 'PGTAP_GUARD_F')
 ORDER BY k.numero;

-- _D a CESSATO: il valido_al (2019) e' gia' arrivato, il verbo lo cessa (rev
-- 2026-10-26: la GUC app.cessazione_automatica e' ritirata).
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti', k.id, 'CESSATO')
  FROM vendite.contratti k
 WHERE k.numero = 'PGTAP_GUARD_D';

-- ============================================================
-- 1) DRAFT -> ATTIVO ammesso
-- ============================================================
SELECT lives_ok(
    $$SELECT * FROM vendite.fn_cambia_stato_contratto(
          (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_GUARD_A'), 'ATTIVO')$$,
    '1) DRAFT -> ATTIVO e'' una transizione ammessa dal workflow contratti'
);

-- ============================================================
-- 2) ATTIVO -> DRAFT vietato (PGTAP_GUARD_B e'' ATTIVO)
-- ============================================================
SELECT throws_like(
    $$SELECT * FROM vendite.fn_cambia_stato_contratto(
          (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_GUARD_B'), 'DRAFT')$$,
    '%transizione stato ATTIVO -> DRAFT non ammessa%',
    '2) ATTIVO -> DRAFT bloccato (irreversibile)'
);

-- ============================================================
-- 3) ATTIVO -> CESSATO con valido_al NULL vietato
-- ============================================================
-- rev 2026-10-26: la data si toglie e la cessazione si chiede nello stesso blocco
--   (throws_like lo annulla tutto). Sullo slot _E, l'ultimo periodo: senza data
--   _B (2081) si sovrapporrebbe a _E (2082) e lo fermerebbe l'EXCLUDE
--   ex_contratti_no_overlap prima del guard (prima la data e lo stato erano
--   nello stesso UPDATE, e il guard BEFORE ROW arrivava prima).
SELECT throws_like(
    $body$
    DO $inner$
    BEGIN
        UPDATE vendite.contratti SET valido_al = NULL WHERE numero = 'PGTAP_GUARD_E';
        PERFORM vendite.fn_cambia_stato_contratto(
            (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_GUARD_E'), 'CESSATO');
    END
    $inner$
    $body$,
    '%transizione stato ATTIVO -> CESSATO non ammessa (valido_al=NULL)%',
    '3) ATTIVO -> CESSATO con valido_al NULL bloccato (E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA)'
);

-- ============================================================
-- 4) ATTIVO -> CESSATO con valido_al futuro dal cambio di stato: RIFIUTATO
--    (PGTAP_GUARD_B ha valido_al = 2081-12-31 nel futuro)
--    rev 2026-10-26 (§11, attesa cambiata): prima AMMESSO, e il contratto
--    risultava CESSATO con una data fine futura. Ora verso CESSATO la data
--    deve essere arrivata: con una data futura la cessazione e' programmata,
--    e la scrive vendite.fn_cessa_contratto (solo la data, 4b e 4c).
-- ============================================================
SELECT throws_like(
    $$SELECT * FROM vendite.fn_cambia_stato_contratto(
          (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_GUARD_B'), 'CESSATO')$$,
    '%transizione stato ATTIVO -> CESSATO non ammessa (valido_al=2081-12-31)%',
    '4) ATTIVO -> CESSATO con valido_al futuro dal cambio di stato: RIFIUTATO (cessazione programmata, non un cambio di stato)'
);

SELECT is(
    (SELECT stato_precedente::text || ' -> ' || stato_nuovo::text || ' programmata=' || programmata::text
       FROM vendite.fn_cessa_contratto(
                (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_GUARD_B'), DATE '2081-06-30')),
    'ATTIVO -> ATTIVO programmata=true',
    '4b) cessazione con data futura da vendite.fn_cessa_contratto: programmata, lo stato resta ATTIVO'
);

SELECT is(
    (SELECT s.codice_interno::text || ' ' || k.valido_al::text
       FROM vendite.contratti k
       JOIN config.stati_doc_contratti s ON s.id = k.stato_doc_contratto_id
      WHERE k.numero = 'PGTAP_GUARD_B'),
    'ATTIVO 2081-06-30',
    '4c) dopo la cessazione programmata: il contratto e'' ATTIVO con la data di fine nuova'
);

-- ============================================================
-- 5) ATTIVO -> CESSATO con valido_al passato VIETATO
--    (PGTAP_GUARD_C ha valido_al = 2020-12-31, nel passato)
--    Regola post-fix: cessazione manuale retroattiva bloccata.
--    Errore specifico: E_CONTRATTO_VALIDO_AL_RETROATTIVO (449).
--    rev 2026-10-26 (§11): la regola sta nel verbo della cessazione, l'unico
--    che scrive la data (vendite.fn_cessa_contratto); prima nel guard.
-- ============================================================
SELECT throws_like(
    $$SELECT * FROM vendite.fn_cessa_contratto(
          (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_GUARD_C'), DATE '2020-12-31')$$,
    '%Cessazione contratto non ammessa: data fine validita'' 2020-12-31 e'' nel passato%',
    '5) cessazione con valido_al passato BLOCCATA (E_CONTRATTO_VALIDO_AL_RETROATTIVO)'
);

-- ============================================================
-- 6) CESSATO -> ATTIVO vietato (PGTAP_GUARD_D e'' CESSATO)
-- ============================================================
SELECT throws_like(
    $$SELECT * FROM vendite.fn_cambia_stato_contratto(
          (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_GUARD_D'), 'ATTIVO')$$,
    '%transizione stato CESSATO -> ATTIVO non ammessa%',
    '6) CESSATO -> ATTIVO bloccato (stato terminale)'
);

-- ============================================================
-- 7) ATTIVO -> ATTIVO no-op ammesso (WHEN distinct filter)
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_attivo FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_E'$$,
    '7) ATTIVO -> ATTIVO (no-op) non deve invocare il guard'
);

-- ============================================================
-- 8) ATTIVO -> CESSATO con valido_al = script.fn_data_operativa() ammesso
--    (PGTAP_GUARD_F ha valido_al = script.fn_data_operativa())
--    Caso "cesso il contratto oggi": valido_al = oggi >= oggi.
-- ============================================================
SELECT lives_ok(
    $$SELECT * FROM vendite.fn_cambia_stato_contratto(
          (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_GUARD_F'), 'CESSATO')$$,
    '8) ATTIVO -> CESSATO con valido_al = script.fn_data_operativa() ammesso (cessazione immediata oggi)'
);

-- ============================================================
-- 9) Job automatico: valido_al passato ammesso.
--    rev 2026-10-26 (§11): la GUC app.cessazione_automatica e' ritirata; il job
--    e' vendite.fn_cessa_contratti_scaduti, il verbo di chiusura che chiama
--    dbops.fn_apply_chiusura_scadenze per il contratto.
--    PGTAP_GUARD_C e'' ancora ATTIVO (test 5 era throws_like, rollback a savepoint).
-- ============================================================
SELECT lives_ok(
    $$SELECT vendite.fn_cessa_contratti_scaduti()$$,
    '9) job vendite.fn_cessa_contratti_scaduti: valido_al passato ammesso (la strada del job pgAgent)'
);

SELECT is(
    (SELECT s.codice_interno::text
       FROM vendite.contratti k
       JOIN config.stati_doc_contratti s ON s.id = k.stato_doc_contratto_id
      WHERE k.numero = 'PGTAP_GUARD_C'),
    'CESSATO',
    '10) dopo il job: il contratto scaduto PGTAP_GUARD_C e'' CESSATO'
);

SELECT * FROM finish();
ROLLBACK;
