-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: un KIT puo' viaggiare su un DDT che non vende, senza prezzi sui
--   componenti — e continua a non poterlo fare su un DDT che vende.
--   Slice C del brief brief-ddt-righe-senza-prezzo.md
--   (decisione D-5 = K2, Tid 2026-08-19), changeSet 20260819-12 → -18.
--
-- COSA PRESIDIA, in una riga: che l'allentamento sia arrivato SOLO dove doveva.
--   Il prezzo assente e' ammesso nel DATO (colonna facoltativa, init che scrive
--   NULL) e resta inammissibile nel DOCUMENTO CHE SI FATTURA (gate). Se un
--   domani qualcuno togliesse la condizione sulla causale da una delle due
--   parti, i test 5/6 o il 7 diventano rossi.
--
-- ⚠️ Il test piu' importante e' il 4, ed e' quello che sembra un dettaglio.
--   Il prezzo del kit e' SUM(figli): con un figlio scoperto deve venire NULL,
--   non la somma dei rimanenti. Un kit a prezzo ASSENTE lo ferma il gate; un
--   kit a prezzo PARZIALE il gate lo passa — un prezzo c'e' — e arriva in
--   fattura. E' l'unico difetto della slice che nessun altro controllo
--   prenderebbe.
--
-- Indice test (1..8):
--   1) (precondizione) la fixture ha costruito un kit coi componenti scoperti
--   2) init CREA i componenti invece di far fallire la riga (prima: eccezione)
--   3) i componenti non risolti hanno prezzo NULL e il motivo nel contesto
--   4) ⚠️ il padre ha prezzo NULL, NON la somma parziale dei figli valorizzati
--   5) causale NON fatturabile: il gate NON nomina i componenti
--   6) causale VENDITA: il gate nomina E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE
--   7) controprova di perimetro: sulle tabelle gemelle il prezzo e' NOT NULL
--   8) il divieto del prezzo ZERO sui componenti obbligatori segue la causale
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

SELECT plan(8);

-- ============================================================
-- FIXTURE — un DDT in bozza con una riga composita i cui componenti NON si
-- risolvono. Il modo piu' corto e piu' stabile per ottenerlo e' passare a
-- fn_ddt_riga_componenti_init un emittente che nella matrice
-- categorie_clienti_listini non compare: nessuna mappa, nessun prezzo.
-- ⚠️ Non si tocca la configurazione dei listini per fabbricare il caso: si
--   sceglie un ingresso che la configurazione gia' non copre. Un test che si
--   costruisce il mondo attorno finisce per provare il proprio setup.
--
-- Blocco robusto (EXCEPTION -> fixture vuota -> skip): su un DB senza articoli
-- compositi o senza emittenti liberi il caso non e' costruibile, e allora si
-- salta invece di fallire.
-- ============================================================
-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti). Prima il kit era «il primo composito del catalogo con
--   una distinta viva» e l'emittente fuori matrice «il primo soggetto_ruolo
--   senza mappa»: su zeroerp_ci il kit non c'era e la precondizione era rossa.
--   Ora un'azienda nuova col suo operatore (contesto aperto su di lui), il
--   cliente legato a lei (dbops.fn_pgtap_crea_mondo_cliente), e il kit: un
--   prodotto e due componenti costruiti (dbops.fn_pgtap_crea_articolo, non
--   gestiti; il kit nasce composito, flag che serve PRIMA della distinta), la distinta coi
--   default del dominio (obbligatorio, NASCOSTO) viva da trenta giorni.
--   L'emittente fuori matrice e' l'azienda appena nata: nessuna mappa in
--   anagrafiche.categorie_clienti_listini, verificato sotto e non sperato.
--   Modello: test-componenti-propaga-qta-da-operativa-v1.
CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('kit senza prezzo');

-- Il kit nasce composito: il flag serve PRIMA della distinta
-- (la check della distinta, script.fn_articolo_riga_contesto).
CREATE TEMP TABLE _art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-KSP-KIT', false, p_is_composito => true) AS kit_id,
       dbops.fn_pgtap_crea_articolo('PGT-KSP-CMP1', false) AS cmp1_id,
       dbops.fn_pgtap_crea_articolo('PGT-KSP-CMP2', false) AS cmp2_id;

INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)
SELECT a.kit_id, c.cmp_id, 1, script.fn_data_operativa() - 30
  FROM _art a
 CROSS JOIN LATERAL (VALUES (a.cmp1_id), (a.cmp2_id)) AS c(cmp_id);

CREATE TEMP TABLE tmp_kit (ddt_id bigint, riga_id bigint, n_comp integer);

DO $fix$
DECLARE
  v_art      catalogo.articoli.id%TYPE;
  v_ba       anagrafiche.billing_account.id%TYPE;
  v_sr       anagrafiche.soggetti_ruoli.id%TYPE;
  v_val      config.valute.id%TYPE;
  v_ef       anagrafiche.emittenti_fiscali.id%TYPE;
  v_sr_nomap anagrafiche.soggetti_ruoli.id%TYPE;
  v_draft    config.stati_doc_ddt.id%TYPE;
  v_utility  anagrafiche.billing_account.utility_id%TYPE;
  v_ddt      vendite.ddt.id%TYPE;
  v_riga     vendite.ddt_righe.id%TYPE;
  v_n        integer;
BEGIN
  -- ⚠️ L'EMITTENTE LO DETTA L'OPERATORE, non il billing account. Il guard
  --   script.trgfn_guard_emittente_scope rifiuta un DDT il cui emittente non
  --   sia nella whitelist di chi scrive, e i pgTAP girano come l'applicazione:
  --   scegliere il BA per primo e derivarne l'emittente faceva fallire
  --   l'INSERT prima ancora di arrivare al caso in esame. Si parte quindi
  --   dall'emittente dell'operatore di test (helper dedicato) e si cerca un BA
  --   che gli corrisponda — cosi' passa anche trgfn_ddt_guard_emittente_ba,
  --   che pretende la coerenza fra i due.
  v_ef := script.fn_pgtap_emittente_operatore();

  -- ⚠️ E il BA NON si vincola all'emittente. Chiedere anche
  --   fn_get_emittente_fiscale_id(ba) = v_ef sembrava piu' rigoroso e invece
  --   svuotava la fixture: su questo DB nessun billing account risolve
  --   all'emittente dell'operatore di test (misurato: zero su 42). Il guard
  --   che conta e' quello di SCOPE, gia' soddisfatto dalla riga sopra.
  -- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-4/D-5): il cliente si
  --   FABBRICA. Prima era il primo BA del database accanto al primo ruolo del
  --   database, scollegati: la FK composta fk_ddt_ba_cliente lo rifiuta. Il
  --   trigger z90 lega il BA all'emittente dell'operatore in sessione.
  -- ⛔ rev 2026-10-13: il cliente e' quello del mondo costruito in testa.
  SELECT m.billing_account_id, m.utility_id, m.cliente_soggetto_ruolo_id
    INTO v_ba, v_utility, v_sr
    FROM _m m;
  SELECT id INTO v_val FROM config.valute ORDER BY id LIMIT 1;
  SELECT id INTO v_draft FROM config.stati_doc_ddt
   WHERE codice_interno = 'DRAFT' AND attivo IS TRUE LIMIT 1;

  -- Articolo composito con distinta viva alla data: quello COSTRUITO in testa
  --   (rev 2026-10-13). La distinta viva si verifica, non si spera.
  SELECT a.id INTO v_art
    FROM catalogo.articoli a
   WHERE a.id = (SELECT kit_id FROM _art)
     AND a.is_composito IS TRUE AND a.attivo IS TRUE
     AND EXISTS (SELECT 1 FROM catalogo.articoli_componenti ac
                  WHERE ac.prodotto_id = a.id
                    AND COALESCE(ac.attivo, TRUE)
                    AND ac.validita @> script.fn_data_operativa());

  -- Emittente FUORI dalla matrice: e' cio' che rende i prezzi non risolvibili.
  --   ⛔ rev 2026-10-13: e' l'azienda appena costruita, non «il primo
  --   soggetto_ruolo senza mappa» del database; la condizione resta.
  SELECT m.emittente_soggetto_ruolo_id INTO v_sr_nomap
    FROM _m m
   WHERE NOT EXISTS (SELECT 1 FROM anagrafiche.categorie_clienti_listini ccl
                      WHERE ccl.emittente_soggetto_ruolo_id = m.emittente_soggetto_ruolo_id);

  IF v_art IS NULL OR v_ba IS NULL OR v_ef IS NULL OR v_sr_nomap IS NULL
     OR v_utility IS NULL THEN
    RETURN;  -- caso non costruibile su questo DB
  END IF;

  BEGIN
    -- ⚠️ utility_id VA VALORIZZATA. Senza, l'init dei componenti passa al
    --   resolver una utility nulla e questo solleva E_PARAMETRO_INVALIDO —
    --   correttamente, perche' un parametro nullo resta un errore anche dopo
    --   la slice (regola D-3). La fixture moriva li', e l'esito sembrava «il
    --   kit non si carica»: cioe' il difetto che la slice ha appena tolto.
    INSERT INTO vendite.ddt (data, stato_doc_ddt_id, destinatario_soggetto_ruolo_id,
                             billing_account_id, utility_id, valuta_id,
                             emittente_fiscale_id, storicizza, meta)
    VALUES (script.fn_data_operativa(), v_draft, v_sr, v_ba, v_utility, v_val, v_ef, false,
            jsonb_build_object('test_scope','pgtap_kit_senza_prezzo'))
    RETURNING id INTO v_ddt;

    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
                                   qta_operativa, quantita, storicizza, meta)
    VALUES (v_ddt, 1, v_art, 'Kit in conto visione', 1.000000, 1.000000, false,
            jsonb_build_object('test_scope','pgtap_kit_senza_prezzo'))
    RETURNING id INTO v_riga;

    -- ⭐ IL CUORE DEL TEST: prima della slice questa chiamata SOLLEVAVA e la
    --   riga-kit non nasceva affatto. Se torna a sollevare, la fixture resta
    --   vuota e i test 2..6 si skippano — cioe' il file lo dice, non tace.
    PERFORM vendite.fn_ddt_riga_componenti_init(v_riga, v_sr_nomap, script.fn_data_operativa());

    SELECT count(*) INTO v_n FROM vendite.ddt_righe_componenti
     WHERE riga_ddt_id = v_riga;

    IF v_n > 0 THEN
      INSERT INTO tmp_kit(ddt_id, riga_id, n_comp) VALUES (v_ddt, v_riga, v_n);
    END IF;
  EXCEPTION WHEN OTHERS THEN
    -- ⚠️ Il motivo si DICE. Una fixture che fallisce in silenzio manda il file
    --   a skip senza spiegare, e uno skip inspiegato somiglia troppo a un
    --   verde: chi legge l'output non sa se il caso non e' costruibile su
    --   questo DB o se la slice si e' rotta.
    RAISE WARNING 'fixture kit-senza-prezzo non costruibile: % (%)', SQLERRM, SQLSTATE;
  END;
END $fix$;

-- 1) La fixture deve esserci: senza, i test seguenti sarebbero verdi per
--    sottrazione (confronterebbero insiemi vuoti).
SELECT isnt(
    (SELECT count(*)::int FROM tmp_kit), 0,
    '(precondizione) fixture costruita: un DDT in bozza con una riga-kit');

-- ============================================================
-- 2) L'init ha creato i componenti. E' la differenza fra prima e dopo: con il
--    resolver che sollevava, qui non c'era nessuna riga da contare.
-- ============================================================
SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM tmp_kit)
  THEN skip('fixture non costruibile su questo DB', 1)
  ELSE cmp_ok((SELECT n_comp FROM tmp_kit), '>', 0,
       'init ha CREATO i componenti del kit invece di far fallire la riga')
END;

-- ============================================================
-- 3) I componenti non risolti hanno prezzo NULL, e il perche' non si perde.
-- ============================================================
SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM tmp_kit)
  THEN skip('fixture non costruibile su questo DB', 1)
  ELSE ok((SELECT bool_and(drc.prezzo_unitario IS NULL
                           AND drc.prezzo_resolver_context ? 'esito_codice'
                           AND drc.prezzo_resolver_context->>'esito_codice' IS NOT NULL)
             FROM vendite.ddt_righe_componenti drc, tmp_kit k
            WHERE drc.riga_ddt_id = k.riga_id),
       'i componenti non risolti hanno prezzo NULL e il motivo in prezzo_resolver_context')
END;

-- ============================================================
-- 4) ⚠️ IL TEST CHE CONTA. Il prezzo del padre e' NULL, non la somma parziale.
--    Con la SUM semplice di prima il padre avrebbe preso la somma dei figli
--    valorizzati (o 0 se nessuno lo e'): un prezzo, quindi qualcosa che il gate
--    all'emissione accetta. Un prezzo assente il gate lo ferma; un prezzo
--    parziale arriva in fattura.
-- ============================================================
SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM tmp_kit)
  THEN skip('fixture non costruibile su questo DB', 1)
  ELSE ok((SELECT dr.prezzo_unitario IS NULL
             FROM vendite.ddt_righe dr, tmp_kit k WHERE dr.id = k.riga_id),
       'il prezzo del kit e'' NULL — non la somma parziale dei componenti valorizzati')
END;

-- ============================================================
-- 5) e 6) LA STESSA SITUAZIONE, LE DUE CAUSALI. E' la coppia che dimostra che
--    l'allentamento segue la dichiarazione dell'operatore e non il caso.
-- ============================================================
CREATE TEMP TABLE tmp_motivi (quando text, motivi jsonb);

DO $causali$
DECLARE v_ddt bigint;
BEGIN
  SELECT ddt_id INTO v_ddt FROM tmp_kit;
  IF v_ddt IS NULL THEN RETURN; END IF;

  UPDATE vendite.ddt SET causale_trasporto_id =
      (SELECT id FROM config.causali_trasporto WHERE codice = 'CONTO_VISIONE')
   WHERE id = v_ddt;
  INSERT INTO tmp_motivi
  SELECT 'non_fatturabile', jsonb_path_query_array(script.fn_check_ddt_emittibile(d.*), '$[*].codice')
    FROM vendite.ddt d WHERE d.id = v_ddt;

  UPDATE vendite.ddt SET causale_trasporto_id =
      (SELECT id FROM config.causali_trasporto WHERE codice = 'VENDITA')
   WHERE id = v_ddt;
  INSERT INTO tmp_motivi
  SELECT 'fatturabile', jsonb_path_query_array(script.fn_check_ddt_emittibile(d.*), '$[*].codice')
    FROM vendite.ddt d WHERE d.id = v_ddt;
END $causali$;

SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM tmp_motivi WHERE quando='non_fatturabile')
  THEN skip('fixture non costruibile su questo DB', 1)
  ELSE ok(NOT ((SELECT motivi FROM tmp_motivi WHERE quando='non_fatturabile')
               @> '["E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE"]'::jsonb),
       'causale NON fatturabile: il gate NON si lamenta dei componenti non valorizzati')
END;

SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM tmp_motivi WHERE quando='fatturabile')
  THEN skip('fixture non costruibile su questo DB', 1)
  ELSE ok((SELECT motivi FROM tmp_motivi WHERE quando='fatturabile')
          @> '["E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE"]'::jsonb,
       'causale VENDITA: il gate ferma l''emissione e nomina i componenti non valorizzati')
END;

-- ============================================================
-- 7) CONTROPROVA DI PERIMETRO. L'allentamento e' del solo DDT: sulle tre
--    tabelle gemelle il prezzo del componente resta obbligatorio. Senza questo
--    test, una ALTER distratta su tutte e quattro passerebbe inosservata — ed
--    e' la quarta casella della definizione di fatto del brief.
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
                                              JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'vendite' AND a.attname = 'prezzo_unitario' AND a.attnotnull
        AND c.relname IN ('preventivi_righe_componenti',
                          'ordini_righe_componenti',
                          'contratti_righe_componenti')),
    3,
    'perimetro: su preventivi, ordini e contratti il prezzo del componente e'' ancora obbligatorio');

-- ============================================================
-- 8) Il divieto del prezzo ZERO sui componenti obbligatori segue la causale.
--    E' la clausola WHEN del trigger (20260819-15): stessa regola del gate, un
--    livello piu' sotto. Si esercita sulla riga della fixture, che ora ha
--    causale VENDITA (l'ha lasciata cosi' il blocco 5/6).
-- ============================================================
SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM tmp_kit)
  THEN skip('fixture non costruibile su questo DB', 1)
  ELSE throws_ok(
       format($q$UPDATE vendite.ddt_righe_componenti SET prezzo_unitario = 0
                  WHERE id = (SELECT drc.id FROM vendite.ddt_righe_componenti drc
                               JOIN catalogo.articoli_componenti ac
                                 ON ac.id = drc.articolo_componente_id
                              WHERE drc.riga_ddt_id = %s
                                AND COALESCE(ac.obbligatorio, TRUE)
                              ORDER BY drc.id LIMIT 1)$q$,
              (SELECT riga_id FROM tmp_kit)),
       'P0001',
       NULL,
       'causale VENDITA: il prezzo ZERO su un componente obbligatorio resta vietato')
END;

SELECT * FROM finish();
ROLLBACK;
