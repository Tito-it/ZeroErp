-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test — l'annullamento chiude la vita: un lotto annullato e' VUOTO, e
--   COMPLETATO si guadagna.
--   Brief: brief-db-annullamento-chiude-la-vita §9 (decisioni di Tid, 2026-09-23).
--   ChangeSet: 20260923-30 (guard su COMPLETATO), -31 (l'annullo chiude gli
--   esiti), -33 (dbops.vw_lotti_chiusi_con_errori_da_guardare) + la riga in
--   presidi.csv. Il -32 (COMMENT) e il -34 (allineamento del pregresso) non
--   hanno asserzioni qui: il primo e' testo, il secondo gira una volta sola.
--
-- ⭐ COSA PRESIDIA QUESTO FILE, IN UNA RIGA:
--     COMPLETATO non si scrive su un lotto fermo o annullato; l'annullo porta
--     ogni esito a ESCLUSO, e da li' la contraddizione «chiuso con documenti in
--     errore» sparisce per il lotto annullato SENZA che nessun lettore lo filtri;
--     e il presidio resta vivo sull'unica porta che il guard non chiude.
--
-- ⛔ IL MONDO SI COSTRUISCE, NON SI CERCA: azienda, operatore e lotti li scrive
--   il file (builder del 18-09), quindi gira identico su dbdev e su un database
--   ricostruito dai changelog. Nessuno skip.
--
-- ⭐ OGNI RAMO HA IL SUO CONTRASTO. Un guard che rifiuta sempre, un annullo che
--   svuota la vista a prescindere, un presidio che tace sempre: ognuno sarebbe
--   verde sulla sola meta' «negativa». Per questo 2 va con 5, 7 con 11, e 15-16
--   provano che il presidio sa ancora dire qualcosa.
--
-- ⚠️ Gira come l'applicazione (zeroerp_app + contesto operatore, RLS attiva).
--   Il test 16 toglie la veste per provare la cecita' della vista e l'onesta'
--   del contatore DEFINER, e la rimette subito dopo.
--
-- Elenco test (plan 17):
--  1) il guard e' montato: BEFORE UPDATE OF stato_lotto, la funzione giusta
--  2) lotto con un documento in ERRORE: COMPLETATO rifiutato, con il CODICE
--     (P0001 + E_LOTTO_COMPLETATO_NON_GUADAGNATO) e la frase del ramo «fermo»
--  3) ...e stato_lotto e' rimasto IN_ESECUZIONE
--  4) contrasto: lo stesso documento COMPLETED → COMPLETATO passa
--  5) lotto ANNULLATO senza niente di fermo: COMPLETATO rifiutato, ramo «annullato»
--  6) prima dell'annullo: il lotto chiuso con un documento in ERRORE e' nominato
--     dalla sorgente di vendite E dal lettore a catalogo
--  7) l'annullo non solleva
--  8) dopo: i tre esiti aperti (ERRORE, COMPLETED, PENDING) sono ESCLUSO, con il
--     motivo dell'annullo e il timbro scritto dal trigger
--  9) l'esito gia' ESCLUSO tiene il SUO motivo
-- 10) dopo: il lotto non e' piu' nominato, da nessuno dei due (contrasto col 6)
-- 11) la sede unica non lo dice piu' fermo, e gli esiti in errore sono zero
-- 12) il giornale ha UNA riga ANNULLO_LOTTO `I` con il numero dei documenti usciti
-- 13) un lotto annullato SENZA esiti non scrive nessuna riga ANNULLO_LOTTO
-- 14) stato_lotto dell'annullato e' ancora COMPLETATO (l'annullo non lo tocca)
-- 15) la porta dell'ESITO resta aperta: un documento marcato ERRORE su un lotto
--     GIA' COMPLETATO e' nominato dal lettore a catalogo
-- 16) DEFINER onesto: senza veste il lettore risponde ZERO (cecita') e
--     fn_conta_presidio conta comunque la riga costruita (delta = 1)
-- 17) catalogo: la riga e' ZERO / DEFINER / GIORNALIERA / attiva
-- ------------------------------------------------------------

BEGIN;

-- ⛔ L'AZIENDA SI COSTRUISCE, e il contesto e' quello del SUO operatore.
CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(17);

-- ============================================================
-- Fixture: i riferimenti, e quattro lotti in DRAFT
-- ============================================================
CREATE TEMP TABLE _rif AS
SELECT m.soggetto_ruolo_id                                   AS emittente_sr_id,
       (SELECT t.id FROM config.tipi_doc_fiscale t
         WHERE t.codice_interno = 'BACKOFFICE')              AS tipo_doc_fiscale_id,
       -- ⛔ codice_interno, mai un id.
       (SELECT s.id FROM config.stati_doc_fiscale s
         WHERE s.codice_interno = 'DRAFT')                   AS stato_draft_id
  FROM _mondo m;

-- A: il lotto del guard — nasce IN_ESECUZIONE (il default), come un giro in corso.
-- B: il lotto da annullare — nasce COMPLETATO: l'INSERT non passa dal guard
--    (che e' su UPDATE), ed e' il modo di costruire il pregresso che il guard
--    oggi impedirebbe.
-- C: un lotto vuoto, che si annulla e poi si prova a completare.
-- D: la porta dell'esito — nasce COMPLETATO, l'ERRORE gli arriva dopo.
CREATE TEMP TABLE _lotti AS
WITH ins AS (
    INSERT INTO vendite.fatturazione_lotti
        (codice, tipo_doc_fiscale_id, competenza_mese,
         emittente_soggetto_ruolo_id, stato_doc_fiscale_id, stato_lotto, meta)
    SELECT 'PGTAP-VITA-' || v.sigla || '-' || r.emittente_sr_id, r.tipo_doc_fiscale_id,
           date_trunc('month', script.fn_data_operativa())::date, r.emittente_sr_id,
           r.stato_draft_id, v.stato_lotto,
           jsonb_build_object('test_scope', 'pgtap_annullamento_vita', 'sigla', v.sigla)
      FROM _rif r,
           (VALUES ('A', 'IN_ESECUZIONE'),
                   ('B', 'COMPLETATO'),
                   ('C', 'IN_ESECUZIONE'),
                   ('D', 'COMPLETATO')) AS v(sigla, stato_lotto)
    RETURNING id, codice, meta ->> 'sigla' AS sigla
)
SELECT id, codice, sigla FROM ins;

-- Cattura SQLSTATE, codice di dominio (CONSTRAINT) e frase di un UPDATE di
-- stato_lotto. ⚠️ throws_ok vede solo SQLSTATE e messaggio: il codice esce nel
-- campo CONSTRAINT, e si legge solo con GET STACKED DIAGNOSTICS. Il blocco
-- EXCEPTION annulla il solo statement, non la transazione del test.
CREATE FUNCTION pg_temp.prova_completato(p_lotto_id bigint)
RETURNS TABLE(v_sqlstate text, v_codice text, v_messaggio text)
LANGUAGE plpgsql
AS $fn$
BEGIN
    BEGIN
        UPDATE vendite.fatturazione_lotti
           SET stato_lotto = 'COMPLETATO'
         WHERE id = p_lotto_id;
        v_sqlstate := NULL; v_codice := NULL; v_messaggio := NULL;
        RETURN NEXT;
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS
            v_sqlstate  = RETURNED_SQLSTATE,
            v_codice    = CONSTRAINT_NAME,
            v_messaggio = MESSAGE_TEXT;
        RETURN NEXT;
    END;
END;
$fn$;

-- ============================================================
-- 1) Il guard e' montato
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1
              FROM pg_trigger t
              JOIN pg_proc p ON p.oid = t.tgfoid
             WHERE t.tgrelid = 'vendite.fatturazione_lotti'::regclass
               AND NOT t.tgisinternal
               AND p.proname = 'trgfn_fatturazione_lotti_guard_completato'
               AND pg_get_triggerdef(t.oid) LIKE '%BEFORE UPDATE OF stato_lotto ON vendite.fatturazione_lotti FOR EACH ROW%'),
    '1. il guard su COMPLETATO e'' montato: BEFORE UPDATE OF stato_lotto, per riga'
);

-- ============================================================
-- 2-4) Ramo «fermo», e il suo contrasto
-- ============================================================
INSERT INTO vendite.fatturazione_lotti_esiti
    (lotto_id, gruppo_key, stato_esecuzione, errore_codice, errore_messaggio)
SELECT l.id, 'PGTAP:VITA:A1', 'ERRORE', 'E_PULL_COMMESSA', 'costruito dal test'
  FROM _lotti l WHERE l.sigla = 'A';

SELECT is(
    (SELECT ROW(p.v_sqlstate, p.v_codice, p.v_messaggio LIKE '%documenti in errore%')::text
       FROM pg_temp.prova_completato((SELECT id FROM _lotti WHERE sigla = 'A')) p),
    ROW('P0001', 'E_LOTTO_COMPLETATO_NON_GUADAGNATO', true)::text,
    '2. un documento in ERRORE: COMPLETATO rifiutato (P0001 + E_LOTTO_COMPLETATO_NON_GUADAGNATO), la frase dice perche'''
);

SELECT is(
    (SELECT l.stato_lotto FROM vendite.fatturazione_lotti l
      WHERE l.id = (SELECT id FROM _lotti WHERE sigla = 'A')),
    'IN_ESECUZIONE',
    '3. rifiutato: stato_lotto e'' ancora IN_ESECUZIONE'
);

-- ⭐ Il contrasto: senza, il 2 passerebbe anche su un guard che rifiuta SEMPRE.
UPDATE vendite.fatturazione_lotti_esiti SET stato_esecuzione = 'COMPLETED'
 WHERE lotto_id = (SELECT id FROM _lotti WHERE sigla = 'A')
   AND gruppo_key = 'PGTAP:VITA:A1';

-- ⚠️ Il verbo in un'istruzione SUA: letto nella stessa, stato_lotto verrebbe
--   dalla fotografia presa prima dell'UPDATE, e direbbe IN_ESECUZIONE.
CREATE TEMP TABLE _prova_4 AS
SELECT p.* FROM pg_temp.prova_completato((SELECT id FROM _lotti WHERE sigla = 'A')) p;

SELECT is(
    (SELECT ROW(p.v_sqlstate,
                (SELECT l.stato_lotto FROM vendite.fatturazione_lotti l
                  WHERE l.id = (SELECT id FROM _lotti WHERE sigla = 'A')))::text
       FROM _prova_4 p),
    ROW(NULL::text, 'COMPLETATO')::text,
    '4. lo stesso documento COMPLETED: COMPLETATO passa'
);

-- ============================================================
-- 5) Ramo «annullato»
-- ============================================================
-- ⚠️ C non ha niente che lo fermi: il rifiuto puo' venire solo dal flag
--   is_abortito del suo stato fiscale. E' il caso che il ramo 1 da solo
--   lascerebbe passare, ora che l'annullo chiude gli esiti.
DO $annulla_c$
BEGIN
    PERFORM * FROM vendite.fn_annulla_lotto_da_draft((SELECT id FROM _lotti WHERE sigla = 'C'));
END
$annulla_c$;

SELECT is(
    (SELECT ROW(p.v_sqlstate, p.v_codice, p.v_messaggio LIKE '%annullato%')::text
       FROM pg_temp.prova_completato((SELECT id FROM _lotti WHERE sigla = 'C')) p),
    ROW('P0001', 'E_LOTTO_COMPLETATO_NON_GUADAGNATO', true)::text,
    '5. lotto annullato e non fermo: COMPLETATO rifiutato, e la frase dice «annullato»'
);

-- ============================================================
-- 6-14) L'annullo chiude gli esiti
-- ============================================================
-- B: un documento per stato aperto, piu' uno gia' uscito col suo motivo.
INSERT INTO vendite.fatturazione_lotti_esiti
    (lotto_id, gruppo_key, stato_esecuzione, errore_codice, errore_messaggio)
SELECT l.id, v.gk, v.st, v.cod, v.msg
  FROM _lotti l,
       (VALUES ('PGTAP:VITA:B1', 'ERRORE',    'E_PULL_COMMESSA', 'costruito dal test'),
               ('PGTAP:VITA:B2', 'COMPLETED', NULL,              NULL),
               ('PGTAP:VITA:B3', 'PENDING',   NULL,              NULL),
               ('PGTAP:VITA:B4', 'ERRORE',    'E_PULL_COMMESSA', 'uscira'' prima')) AS v(gk, st, cod, msg)
 WHERE l.sigla = 'B';

UPDATE vendite.fatturazione_lotti_esiti
   SET stato_esecuzione = 'ESCLUSO', uscita_motivo = 'pgTAP: tolto a mano prima'
 WHERE lotto_id = (SELECT id FROM _lotti WHERE sigla = 'B')
   AND gruppo_key = 'PGTAP:VITA:B4';

SELECT is(
    (SELECT ROW(
        (SELECT c.gruppi_in_errore::int FROM vendite.vw_lotti_chiusi_con_gruppi_in_errore c
          WHERE c.lotto_id = (SELECT id FROM _lotti WHERE sigla = 'B')),
        (SELECT d.stato_codice_interno FROM dbops.vw_lotti_chiusi_con_errori_da_guardare d
          WHERE d.lotto_id = (SELECT id FROM _lotti WHERE sigla = 'B'))
    )::text),
    ROW(1, 'DRAFT')::text,
    '6. prima dell''annullo: il lotto chiuso con un documento in ERRORE e'' nominato dalla sorgente e dal lettore a catalogo'
);

SELECT lives_ok(
    format($$SELECT * FROM vendite.fn_annulla_lotto_da_draft(%s)$$,
           (SELECT id FROM _lotti WHERE sigla = 'B')),
    '7. l''annullo del lotto non solleva'
);

SELECT is(
    (SELECT ROW(count(*),
                bool_and(e.stato_esecuzione = 'ESCLUSO'),
                bool_and(e.uscita_motivo = 'Annullo del lotto ' || (SELECT codice FROM _lotti WHERE sigla = 'B')),
                bool_and(e.uscita_quando IS NOT NULL AND e.uscita_da IS NOT NULL))::text
       FROM vendite.fatturazione_lotti_esiti e
      WHERE e.lotto_id = (SELECT id FROM _lotti WHERE sigla = 'B')
        AND e.gruppo_key IN ('PGTAP:VITA:B1', 'PGTAP:VITA:B2', 'PGTAP:VITA:B3')),
    ROW(3::bigint, true, true, true)::text,
    '8. ERRORE, COMPLETED e PENDING sono ESCLUSO, col motivo dell''annullo e il timbro del trigger'
);

SELECT is(
    (SELECT e.uscita_motivo FROM vendite.fatturazione_lotti_esiti e
      WHERE e.lotto_id = (SELECT id FROM _lotti WHERE sigla = 'B')
        AND e.gruppo_key = 'PGTAP:VITA:B4'),
    'pgTAP: tolto a mano prima',
    '9. l''esito gia'' ESCLUSO tiene il SUO motivo'
);

-- ⭐ Il contrasto col 6: stesso lotto, stessa vista, e la sola differenza e'
--   l'annullo. La vista non filtra gli annullati: il lotto esce perche' non ha
--   piu' documenti in ERRORE.
SELECT is(
    (SELECT ROW(
        (SELECT count(*)::int FROM vendite.vw_lotti_chiusi_con_gruppi_in_errore c
          WHERE c.lotto_id = (SELECT id FROM _lotti WHERE sigla = 'B')),
        (SELECT count(*)::int FROM dbops.vw_lotti_chiusi_con_errori_da_guardare d
          WHERE d.lotto_id = (SELECT id FROM _lotti WHERE sigla = 'B'))
    )::text),
    ROW(0, 0)::text,
    '10. dopo l''annullo il lotto non e'' piu'' nominato, ne'' dalla sorgente ne'' dal lettore'
);

SELECT is(
    (SELECT ROW(s.fermo, s.esiti_stato_esecuzione_errore_count)::text
       FROM vendite.vw_lotti_segnalazioni_summary s
      WHERE s.lotto_id = (SELECT id FROM _lotti WHERE sigla = 'B')),
    ROW(false, 0::bigint)::text,
    '11. la sede unica non dice piu'' fermo il lotto annullato, e gli esiti in errore sono zero'
);

SELECT is(
    (SELECT ROW(count(*), min(g.status), min((g.meta ->> 'esiti_chiusi')::int))::text
       FROM vendite.fatturazione_lotti_log g
      WHERE g.lotto_id = (SELECT id FROM _lotti WHERE sigla = 'B')
        AND g.fase = 'ANNULLO_LOTTO'),
    ROW(1::bigint, 'I', 3)::text,
    '12. il giornale ha UNA riga ANNULLO_LOTTO, status I, con i tre documenti usciti'
);

SELECT is(
    (SELECT count(*)::int FROM vendite.fatturazione_lotti_log g
      WHERE g.lotto_id = (SELECT id FROM _lotti WHERE sigla = 'C')
        AND g.fase = 'ANNULLO_LOTTO'),
    0,
    '13. un lotto annullato senza esiti non scrive righe ANNULLO_LOTTO: zero usciti e'' rumore'
);

SELECT is(
    (SELECT l.stato_lotto FROM vendite.fatturazione_lotti l
      WHERE l.id = (SELECT id FROM _lotti WHERE sigla = 'B')),
    'COMPLETATO',
    '14. l''annullo non tocca stato_lotto (rev 2026-09-07): resta COMPLETATO'
);

-- ============================================================
-- 15-16) La porta dell'ESITO, e il contatore DEFINER
-- ============================================================
-- Il contatore PRIMA che D diventi una contraddizione: il 16 misura il DELTA,
-- cosi' non dipende da cosa c'e' sulla macchina.
CREATE TEMP TABLE _conta_prima AS
SELECT dbops.fn_conta_presidio('dbops.vw_lotti_chiusi_con_errori_da_guardare') AS n;

-- ⭐ D e' gia' COMPLETATO: l'ERRORE gli arriva dopo, dal marcatore. Il guard
--   del 20260923-30 non lo vede (stato_lotto non cambia) — ed e' per questo che
--   il presidio esiste ancora.
DO $porta$
BEGIN
    PERFORM vendite.fn_segna_esito_gruppo_lotto(
        p_lotto_id         => (SELECT id FROM _lotti WHERE sigla = 'D'),
        p_stato            => 'ERRORE',
        p_gruppo_key       => 'PGTAP:VITA:D1',
        p_errore_codice    => 'E_PULL_COMMESSA',
        p_errore_messaggio => 'costruito dal test');
END
$porta$;

SELECT is(
    (SELECT ROW(count(*), min(d.gruppi_in_errore))::text
       FROM dbops.vw_lotti_chiusi_con_errori_da_guardare d
      WHERE d.lotto_id = (SELECT id FROM _lotti WHERE sigla = 'D')),
    ROW(1::bigint, 1::bigint)::text,
    '15. la porta dell''esito e'' aperta: ERRORE marcato su un lotto gia'' COMPLETATO, e il presidio lo nomina'
);

-- ⚠️ Si toglie la VESTE, non l'utente: `app.current_user_id` vuoto vale
--   «nessuna restrizione»; il cancello che chiude e' app.ruolo_applicativo.
SELECT set_config('app.ruolo_applicativo', '', true);

SELECT is(
    (SELECT ROW(
        (SELECT count(*)::int FROM dbops.vw_lotti_chiusi_con_errori_da_guardare),
        (SELECT dbops.fn_conta_presidio('dbops.vw_lotti_chiusi_con_errori_da_guardare')
              - (SELECT n FROM _conta_prima))
    )::text),
    ROW(0, 1::bigint)::text,
    '16. senza veste il lettore risponde ZERO (cecita''); fn_conta_presidio vede comunque la riga costruita (delta = 1)'
);

SELECT set_config('app.ruolo_applicativo', 'OPERATORE', true);

-- ============================================================
-- 17) Il catalogo
-- ============================================================
SELECT is(
    (SELECT ROW(p.natura, p.perimetro, p.cadenza, p.attivo, p.obsoleto_dal IS NULL)::text
       FROM dbops.presidi p
      WHERE p.vista = 'dbops.vw_lotti_chiusi_con_errori_da_guardare'),
    ROW('ZERO', 'DEFINER', 'GIORNALIERA', true, true)::text,
    '17. a catalogo: ZERO, DEFINER (le tabelle hanno la RLS), GIORNALIERA, attivo'
);

SELECT * FROM finish();
ROLLBACK;
