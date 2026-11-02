-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la causale di trasporto non si cambia dopo l'emissione.
--   Slice B del brief brief-ddt-righe-senza-prezzo.md
--   (decisione D-4, rilievo R-4), changeSet 20260819-20 e -21.
--
-- COSA PRESIDIA. Il gate all'emissione guarda SOLO la transizione verso
--   EMESSO: dopo, una causale non fatturabile poteva diventare fatturabile
--   senza ripassare da nessun controllo, e con essa una riga senza prezzo
--   diventava eleggibile al lister. L'errore sarebbe poi arrivato in batch,
--   dal NOT NULL di commesse_attivita.prezzo_snapshot: tardi, e senza nominare
--   la causa.
--
-- ⚠️ Il test 4 e' quello che protegge dall'errore piu' facile da commettere
--   scrivendo questo guard: leggere lo stato NUOVO invece del VECCHIO.
--   L'UPDATE che porta DRAFT->EMESSO scegliendo contestualmente la causale e'
--   l'operazione legittima per eccellenza — un guard che la bocciasse sarebbe
--   verde su tutti gli altri test e romperebbe l'unica cosa che conta.
--
-- Indice test (1..5):
--   1) (precondizione) fixture: un DDT in bozza con causale
--   2) in BOZZA la causale si cambia liberamente
--   3) su DDT EMESSO il cambio e' BLOCCATO (P0001)
--   4) ⚠️ l'UPDATE che cambia stato e causale INSIEME (DRAFT->EMESSO) — dal 2026-10-25
--      rifiutato dalla porta sullo stato (attesa cambiata, vedi la rev qui sotto)
--   5) riscrivere la STESSA causale su un DDT emesso non e' un cambio: passa
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2c/2d): l'ambito degli indirizzi della bolla e' DDT_VENDITA.
-- rev 2026-10-25 (brief-modello-documento-vendita §7, giro 5): lo stato si cambia solo dal verbo;
--   la porta (trg_ddt_a05_stato_solo_dal_verbo_upd) rifiuta ogni UPDATE diretto della colonna di
--   stato con E_DOC_STATO_SOLO_DAL_VERBO. La fixture emette il DDT n.1 con
--   dbops.fn_pgtap_porta_a_stato. ⚠️ ATTESA CAMBIATA sul test 4 (regola ritirata «una bolla senza
--   merce passa dall'UPDATE diretto»): l'UPDATE che sceglie la causale ed emette insieme non e' piu'
--   un'operazione legittima — prima la causale in bozza (test 2), poi il verbo — e la porta lo
--   ferma prima del guard della causale. Il test lo asserisce sulla frase della porta, cosi' un
--   rifiuto del guard della causale (che leggesse NEW) resterebbe rosso.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): le due bolle dal builder
--   dbops.fn_pgtap_crea_ddt_senza_ordine (n.1 VENDITA EMESSO, n.2 CONTO_VISIONE in bozza);
--   a mano resta solo il cliente (fn_pgtap_crea_cliente_ba, condiviso dalle due bolle).
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

SELECT plan(5);

-- ============================================================
-- FIXTURE — due DDT gemelli in bozza, con una riga a prezzo e gli indirizzi
-- obbligatori: servono entrambi perche' i test 3 e 4 partono da situazioni
-- diverse (uno gia' emesso, l'altro ancora in bozza) e non possono
-- condividere lo stesso documento.
-- ⚠️ L'emittente lo detta l'OPERATORE (guard di scope), non il billing
--   account: vedi test-ddt-componenti-senza-prezzo-v1.
-- ============================================================
CREATE TEMP TABLE tmp_b (ddt_emesso bigint, ddt_bozza bigint,
                         caus_vendita bigint, caus_visione bigint);

DO $fix$
DECLARE
  v_ba      bigint;
  v_cv      bigint;
  v_cc      bigint;
  v_uno     bigint;
  v_due     bigint;

BEGIN
  -- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-4/D-5): il cliente si
  --   FABBRICA. Prima era il primo BA del database accanto al primo ruolo del
  --   database, scollegati: la FK composta fk_ddt_ba_cliente lo rifiuta. Il
  --   trigger z90 lega il BA all'emittente dell'operatore in sessione.
  SELECT c.billing_account_id INTO v_ba
    FROM dbops.fn_pgtap_crea_cliente_ba('causale immutabile') c;
  SET CONSTRAINTS ALL IMMEDIATE;
  SELECT id INTO v_cv FROM config.causali_trasporto WHERE codice='VENDITA' LIMIT 1;
  SELECT id INTO v_cc FROM config.causali_trasporto WHERE codice='CONTO_VISIONE' LIMIT 1;

  IF v_ba IS NULL OR v_cv IS NULL OR v_cc IS NULL THEN
    RETURN;
  END IF;

  BEGIN
    -- Le due bolle dal builder della bolla senza ordine: testata con la
    -- causale, indirizzi obbligatori, una riga a prezzo (1 a 10, con l'IVA) su
    -- un articolo merce costruito, e lo stato chiesto coi verbi.
    -- DDT n.1 — VENDITA, EMESSO
    SELECT b.ddt_id INTO v_uno
      FROM dbops.fn_pgtap_crea_ddt_senza_ordine('causale immutabile 1', 'EMESSO', v_ba,
               p_quantita => 1, p_prezzo => 10, p_causale_codice => 'VENDITA') b;

    -- DDT n.2 — CONTO_VISIONE, resta in bozza: serve ai test 2 e 4
    SELECT b.ddt_id INTO v_due
      FROM dbops.fn_pgtap_crea_ddt_senza_ordine('causale immutabile 2', 'DRAFT', v_ba,
               p_quantita => 1, p_prezzo => 10, p_causale_codice => 'CONTO_VISIONE') b;

    INSERT INTO tmp_b VALUES (v_uno, v_due, v_cv, v_cc);
  EXCEPTION WHEN OTHERS THEN
    -- Il motivo si DICE: uno skip inspiegato somiglia troppo a un verde.
    RAISE WARNING 'fixture causale-immutabile non costruibile: % (%)', SQLERRM, SQLSTATE;
  END;
END $fix$;

SELECT isnt((SELECT count(*)::int FROM tmp_b), 0,
    '(precondizione) fixture costruita: un DDT emesso e uno in bozza');

-- ============================================================
-- 2) In BOZZA la causale si cambia liberamente. Se questo diventasse rosso, il
--    guard avrebbe stretto troppo: la bozza serve proprio a cambiare idea.
-- ============================================================
SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM tmp_b)
  THEN skip('fixture non costruibile su questo DB', 1)
  ELSE lives_ok(
       format('UPDATE vendite.ddt SET causale_trasporto_id = %s WHERE id = %s',
              (SELECT caus_vendita FROM tmp_b), (SELECT ddt_bozza FROM tmp_b)),
       'in BOZZA la causale di trasporto si cambia liberamente')
END;

-- ============================================================
-- 3) Su un DDT EMESSO il cambio e' bloccato.
--    ⚠️ SQLSTATE esplicito: throws_ok senza discriminante accetterebbe
--    qualunque errore, compreso il crash del guard stesso.
-- ============================================================
SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM tmp_b)
  THEN skip('fixture non costruibile su questo DB', 1)
  ELSE throws_ok(
       format('UPDATE vendite.ddt SET causale_trasporto_id = %s WHERE id = %s',
              (SELECT caus_visione FROM tmp_b), (SELECT ddt_emesso FROM tmp_b)),
       'P0001',
       NULL,
       'su un DDT EMESSO la causale non si cambia piu''')
END;

-- ============================================================
-- 4) ⚠️ IL CASO CHE UN GUARD SCRITTO MALE ROMPEREBBE: stato e causale
--    cambiati NELLO STESSO UPDATE, da bozza a emesso. Fino al 2026-10-24 era
--    l'operazione legittima per eccellenza — l'operatore sceglie la causale ed
--    emette — e passava solo se il guard leggeva lo stato VECCHIO.
--    ⚠️ ATTESA CAMBIATA il 2026-10-25 (giro 5): lo stato si cambia solo dal
--    verbo, e la porta ferma l'UPDATE diretto PRIMA del guard della causale.
--    Si asserisce la frase della porta: se a rifiutare fosse il guard della
--    causale (che leggesse NEW), il messaggio sarebbe un altro e il test rosso.
--    ⛔ DISCRIMINA PER L'ORDINE DEI NOMI (confermato da Tid, 2026-10-25): il lock
--    della causale (trg_ddt_a05_lock_fuori_bozza_upd) scatta PRIMA della porta
--    (trg_ddt_a05_stato_solo_dal_verbo_upd), «lock» < «stato». Se un rinomina
--    facesse parlare prima la porta, questo test diventerebbe verde senza provare
--    piu' niente: chi rinomina uno dei due trigger rilegge questo test.
-- ============================================================
SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM tmp_b)
  THEN skip('fixture non costruibile su questo DB', 1)
  ELSE throws_like(
       format($q$UPDATE vendite.ddt
                    SET causale_trasporto_id = %s,
                        stato_doc_ddt_id = (SELECT id FROM config.stati_doc_ddt
                                             WHERE codice_interno='EMESSO' LIMIT 1)
                  WHERE id = %s$q$,
              (SELECT caus_vendita FROM tmp_b), (SELECT ddt_bozza FROM tmp_b)),
       '%si cambia solo dalle sue operazioni%',
       'DRAFT->EMESSO con la causale scelta nello STESSO update: rifiutato dalla porta, non dal guard della causale')
END;

-- ============================================================
-- 5) Riscrivere la STESSA causale su un DDT emesso non e' un cambio. E' cio'
--    che fa un salvataggio di testata che rimanda indietro tutti i campi del
--    form: senza la clausola WHEN sul valore, `UPDATE OF` scatterebbe lo
--    stesso e bloccherebbe un'operazione che non cambia niente.
-- ============================================================
SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM tmp_b)
  THEN skip('fixture non costruibile su questo DB', 1)
  ELSE lives_ok(
       format('UPDATE vendite.ddt SET causale_trasporto_id = %s WHERE id = %s',
              (SELECT caus_vendita FROM tmp_b), (SELECT ddt_emesso FROM tmp_b)),
       'riscrivere la STESSA causale su un DDT emesso non e'' un cambio: passa')
END;

SELECT * FROM finish();
ROLLBACK;
