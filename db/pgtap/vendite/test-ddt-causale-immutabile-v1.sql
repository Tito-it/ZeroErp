-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
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
  v_ef      bigint;
  v_ba      bigint;
  v_utility integer;
  v_sr      bigint;
  v_val     integer;
  v_draft   bigint;
  v_emesso  bigint;
  v_art     uuid;
  v_iva     integer;
  v_cv      bigint;
  v_cc      bigint;
  v_uno     bigint;
  v_due     bigint;

BEGIN
  v_ef := script.fn_pgtap_emittente_operatore();
  -- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-4/D-5): il cliente si
  --   FABBRICA. Prima era il primo BA del database accanto al primo ruolo del
  --   database, scollegati: la FK composta fk_ddt_ba_cliente lo rifiuta. Il
  --   trigger z90 lega il BA all'emittente dell'operatore in sessione.
  SELECT c.billing_account_id, c.utility_id, c.soggetto_ruolo_id
    INTO v_ba, v_utility, v_sr
    FROM dbops.fn_pgtap_crea_cliente_ba('causale immutabile') c;
  SET CONSTRAINTS ALL IMMEDIATE;
  SELECT id INTO v_val FROM config.valute ORDER BY id LIMIT 1;
  SELECT id INTO v_iva FROM config.iva WHERE attivo IS TRUE ORDER BY id LIMIT 1;
  SELECT id INTO v_draft  FROM config.stati_doc_ddt WHERE codice_interno='DRAFT'  AND attivo LIMIT 1;
  SELECT id INTO v_emesso FROM config.stati_doc_ddt WHERE codice_interno='EMESSO' AND attivo LIMIT 1;
  SELECT id INTO v_cv FROM config.causali_trasporto WHERE codice='VENDITA' LIMIT 1;
  SELECT id INTO v_cc FROM config.causali_trasporto WHERE codice='CONTO_VISIONE' LIMIT 1;
  -- 🔴 rev 2026-10-13 (brief-db-articoli-ammessi-per-documento D-1/D-2): l'articolo si
  --   COSTRUISCE. Prima si pescava dal catalogo (il primo per id, o il piu' recente):
  --   il primo per id e' l'onere del seed ONERE_SENZA_CONTRATTO (natura servizio), e
  --   da 20261013-42 ordine e bolla portano solo merce. Un articolo costruito ha solo
  --   le proprieta' che il test gli da' (merce, non gestito a magazzino).
  v_art := dbops.fn_pgtap_crea_articolo('PGT-DCI-ART', false);

  IF v_ef IS NULL OR v_ba IS NULL OR v_art IS NULL OR v_cv IS NULL OR v_cc IS NULL THEN
    RETURN;
  END IF;

  BEGIN
    -- DDT n.1 — verra' portato a EMESSO
    INSERT INTO vendite.ddt (data, stato_doc_ddt_id, destinatario_soggetto_ruolo_id,
        billing_account_id, utility_id, valuta_id, emittente_fiscale_id,
        causale_trasporto_id, storicizza, meta)
    VALUES (script.fn_data_operativa(), v_draft, v_sr, v_ba, v_utility, v_val, v_ef, v_cv, false,
            jsonb_build_object('test_scope','pgtap_causale_immutabile'))
    RETURNING id INTO v_uno;

    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
        qta_operativa, quantita, prezzo_unitario, iva_id, storicizza, meta)
    VALUES (v_uno, 1, v_art, 'Riga con prezzo', 1, 1, 10, v_iva, false,
            jsonb_build_object('test_scope','pgtap_causale_immutabile'));

    INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
    SELECT v_uno, ti.id, '{"display":"pgtap"}'::jsonb
      FROM config.tipi_indirizzi ti
     WHERE ti.codice_interno = ANY (script.fn_indirizzi_obbligatori_mancanti('DDT_VENDITA', NULL))
    ON CONFLICT DO NOTHING;

    -- rev 2026-10-25 (giro 5): l'emissione dal verbo, sotto la porta.
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ddt', v_uno, 'EMESSO');

    -- DDT n.2 — resta in bozza, serve al test 4
    INSERT INTO vendite.ddt (data, stato_doc_ddt_id, destinatario_soggetto_ruolo_id,
        billing_account_id, utility_id, valuta_id, emittente_fiscale_id,
        causale_trasporto_id, storicizza, meta)
    VALUES (script.fn_data_operativa(), v_draft, v_sr, v_ba, v_utility, v_val, v_ef, v_cc, false,
            jsonb_build_object('test_scope','pgtap_causale_immutabile'))
    RETURNING id INTO v_due;

    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
        qta_operativa, quantita, prezzo_unitario, iva_id, storicizza, meta)
    VALUES (v_due, 1, v_art, 'Riga con prezzo', 1, 1, 10, v_iva, false,
            jsonb_build_object('test_scope','pgtap_causale_immutabile'));

    INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
    SELECT v_due, ti.id, '{"display":"pgtap"}'::jsonb
      FROM config.tipi_indirizzi ti
     WHERE ti.codice_interno = ANY (script.fn_indirizzi_obbligatori_mancanti('DDT_VENDITA', NULL))
    ON CONFLICT DO NOTHING;

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
