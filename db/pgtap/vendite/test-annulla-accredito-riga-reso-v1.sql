-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): la commessa da dbops.fn_pgtap_crea_commessa (sorgente ROOT), le attivita' da dbops.fn_pgtap_crea_commessa_attivita (sorgente DDT_VENDITA, E-3), le fatture agganciate da dbops.fn_pgtap_fattura_attivita: ritirato pg_temp.ann_fattura; il reset del lotto (pg_temp.ann_reset_lotto, UPDATE a mano) diventa il verbo vero vendite.fn_cleanup_fatture_by_ids sulle note che fatturano le rettifiche (E-4); restano a mano la seconda riga di fattura e la seconda coppia sul ponte (il caso del plurale).
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): il reso dal builder dbops.fn_pgtap_crea_reso (che concede da se' conferma_reso); resta scritta a mano la commessa con la fattura e la seconda coppia sul ponte, che sono il caso del test.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine; resta scritto a mano il reso (giro 2) e la commessa con la fattura, che sono il caso del test.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_annulla_accredito_riga_reso — l'annullo dell'accredito
--       (brief-db-note-credito-prerequisiti-be-fe §8 passo 3 / §9;
--        changeset 20260818-71)
-- ------------------------------------------------------------
-- ⛔ QUESTO FILE NON PUO' ESSERE VERDE FINCHE' 20260818-71 NON E' APPLICATO:
--    la funzione non esiste ancora nel DB. Prima dell'apply il rosso atteso e'
--    «function ... does not exist», non un difetto del test.
--
-- Indice test (1..23):
--   PARTITA A — il percorso pulito (la rettifica non viene mai emessa)
--     1) fixture: la coda vede l'accredito dovuto 3
--     2) il verbo scrive UNA coppia sul ponte
--     3) guard: motivo vuoto -> rifiuto
--     4) guard: parametro nullo -> errore di dominio (P0001)
--     5) guard: riga di reso inesistente -> rifiuto
--     6) ⭐ dopo i tre rifiuti NIENTE e' cambiato — un guard che scrive non e'
--        un guard, ed e' l'unico modo di accorgersene
--     7) l'annullo riesce e RITORNA la coppia rimossa
--     8) il ponte e' vuoto
--     9) la rettifica e' ANNULLATA, non cancellata
--    10) ⭐ LA CODA RISALE: accredito_dovuto torna 3, gia_accreditato torna 0.
--        E' l'unica prova osservabile che l'annullo ha funzionato: senza,
--        «la riga e' sparita» direbbe solo che una DELETE e' andata a buon fine
--    11) audit: l'evento ACCREDITO_ANNULLATO porta il motivo
--    12) un secondo annullo -> E_ACCREDITO_NON_TROVATO
--    13) ⭐ un secondo accredito RIESCE: la merce e' di nuovo accreditabile
--
--   PARTITA B — la semantica d'INSIEME (C-2), che il caso singolo non verifica
--    14) fixture plurale: DUE coppie e DUE rettifiche sulla stessa riga di reso
--    15) ⭐ una sola rettifica emessa -> l'annullo rifiuta ENTRAMBE
--    16) ⭐ e non ha toccato niente: tutto-o-niente, non «quel che si puo'»
--    17) ⭐ dopo il reset del lotto l'attivita' fatturabile SOPRAVVIVE sbloccata,
--        e l'annullo riesce lo stesso — «esiste una AF -> bloccato» sarebbe
--        stata la scorciatoia sbagliata (§9 D-9-3)
--    18) ⭐⭐ IL PERCORSO COMPLETO: accredito -> emissione -> reset -> annullo
--        -> LA CODA RISALE. E' l'unico test che dimostra chiuso il difetto di
--        §10, e prima del changeset 20260818-73 e' ROSSO — vedi sotto.
--
--   PARTITA C — LA SEDE UNICA (2026-08-25, changeset 20260825-22/23/24).
--     Il team BE ha chiesto che il DB dica SE l'annullo e' ammesso e PERCHE'
--     no, «con lo stesso predicato della guardia, non una seconda scrittura».
--     Il predicato e' uscito dal corpo della madre ed e' diventato
--     script.fn_check_accredito_annullabile, che la madre INTERROGA e che il
--     read-side legge per spegnere il pulsante.
--    19) la funzione di check esiste
--    20) e' STABLE — e' una lettura, non un verbo
--    21) e' SECURITY INVOKER: il perimetro RLS di chi chiede e' il suo
--    22) ⛔⛔ SEDE UNICA: la madre CHIAMA la check e NON contiene piu' il
--        predicato. E' il presidio della richiesta del BE: due predicati che
--        divergono riportano al difetto di partenza — pulsante spento su un
--        annullo che sarebbe passato, o acceso su uno che verra' rifiutato
--    23) la coda accrediti porta annullo_blocco_codice in riga (linee-guida-sql
--        §12.4: le liste gate sui codici che hanno gia' in riga)
--
-- ⚠️ PERCHE' DUE PARTITE E NON UNA. Il caso plurale esige che le rettifiche
--    siano EMESSE, e l'emissione crea attivita_fatturabili che restano nel
--    conto della merce. La partita A tiene quindi il percorso in cui la coda
--    e' osservabile pulita (nessuna emissione), la B la semantica d'insieme.
--    Sulla B il ritorno in coda e' il TEST 18, e non e' un di piu': e' il
--    percorso che il messaggio di E_ACCREDITO_ANNULLO_NON_AMMESSO consiglia
--    all'operatore («resetta il lotto, poi annulla»). ⛔ Prima del changeset
--    20260818-73 quel test e' ROSSO, e il rosso NON e' del test: e'
--    vw_af_merce_per_riga che continua a contare l'attivita_fatturabili di una
--    rettifica ANNULLATA, quindi la partita resta pareggiata e la riga non
--    torna mai in coda (brief §10).
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, che qui non arriva mai (si chiude
--   in ROLLBACK). Senza questa riga il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti): azienda + operatore + cliente BA, e il builder apre
--   da se' il contesto su quell'operatore. Niente utente 1 inchiodato.
CREATE TEMP TABLE tmp_mondo_acc AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP annulla accredito');
-- Il mondo ha gia' aperto il contesto sul suo operatore: la riga lo
--   dichiara (e il guardrail del preambolo la cerca).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_mondo_acc)); END $ctx$;

SELECT plan(23);

-- ============================================================
-- Riferimenti — ogni scelta col suo ORDER BY: senza, quale riga esca dipende
-- dal piano del planner e il test passa a giorni alterni.
-- ============================================================
-- Servono alla SECONDA coppia della partita B (riga di fattura e rettifica
-- scritte a mano: e' il caso del plurale).
CREATE TEMP TABLE tmp_refs_ann AS
SELECT
  ba.id                                        AS billing_account_id,
  ba.istanza_utility_id                        AS istanza_utility_id,
  -- ⛔ rev 2026-10-13: l'articolo si COSTRUISCE (merce non solo-componente, non
  --   gestito: il test non misura il magazzino) — da zero il catalogo ha solo ONERE_*.
  dbops.fn_pgtap_crea_articolo('PGTAP-ANN-ACC', false)                  AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)            AS iva_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)                               AS tipo_doc_fiscale_id,
  config.fn_get_natura_doc_fiscale_id('NOTA_CREDITO')                                                                     AS natura_nc_id
-- ⛔ rev 2026-10-13: il BA e' quello del mondo costruito, non il primo del database.
FROM tmp_mondo_acc m
JOIN anagrafiche.billing_account ba ON ba.id = m.billing_account_id;

-- ============================================================
-- Fixture. La partita (bolla CONSEGNATA da ordine) e' del builder
-- dbops.fn_pgtap_crea_ddt_da_ordine; la merce viene FATTURATA per intero
-- (attivita' sul segmento della bolla, emessa, agganciata a una fattura vera)
-- da dbops.fn_pgtap_fattura_attivita: e' la catena che la madre risale per
-- copiare il prezzo. Senza `fattura_riga_id` l'accredito e' impossibile.
-- ⚠️ Padre e figlio in DUE istruzioni, mai in una CTE sola: le CTE che
--    scrivono condividono la stessa snapshot e una policy che risolve il
--    perimetro dal padre non lo trova, negando fail-closed.
-- ============================================================

-- ============================================================
-- COMMESSA + PARTITA A: consegnati 10 a 25, fatturati 10, resi 3
--                       -> tenuti 7, fatturati 10 -> accredito dovuto 3
-- ============================================================
CREATE TEMP TABLE tmp_com_ann AS
SELECT c.commessa_id
  FROM dbops.fn_pgtap_crea_commessa('annulla accredito', NULL,
           (SELECT billing_account_id FROM tmp_refs_ann), p_con_sorgente_root => true) c;

CREATE TEMP TABLE tmp_pa AS
SELECT b.ordine_riga_id, b.ddt_id, b.ddt_uid, b.ddt_riga_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('annulla accredito',
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs_ann),
           p_quantita             => 10,
           p_prezzo               => 25,
           p_articolo_id          => (SELECT articolo_id FROM tmp_refs_ann),
           p_fatturazione_trigger => 'CONSEGNATO') b;
-- E-3: l'attivita' sul segmento della bolla dichiara la sorgente DDT_VENDITA.
CREATE TEMP TABLE tmp_pa_att AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM tmp_com_ann), 25,
           p_articolo_id      => (SELECT articolo_id FROM tmp_refs_ann),
           p_sorgente_codice  => 'DDT_VENDITA',
           p_sorgente_uid     => (SELECT ddt_uid FROM tmp_pa)::text,
           p_sorgente_riga_id => (SELECT ddt_riga_id FROM tmp_pa),
           p_quantita         => 10);
CREATE TEMP TABLE tmp_pa_fattura AS
SELECT f.fattura_riga_id
  FROM dbops.fn_pgtap_fattura_attivita('annulla accredito pa',
           ARRAY[(SELECT attivita_id FROM tmp_pa_att)]) f;
-- Il reso a credito di 3, confermato.
CREATE TEMP TABLE tmp_pa_reso AS
SELECT x.resi_riga_id
  FROM dbops.fn_pgtap_crea_reso('annulla accredito', (SELECT ddt_id FROM tmp_pa), 3,
           p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_pa)) x;

SELECT is(
  (SELECT q.accredito_dovuto FROM vendite.vw_resi_da_accreditare q
    WHERE q.resi_riga_id = (SELECT resi_riga_id FROM tmp_pa_reso)),
  3::numeric,
  '1) fixture: la partita e'' in coda accrediti con accredito dovuto 3'
);

-- ⭐ Si passa DALLA MADRE, non si inserisce la coppia a mano: un ramo si
--    verifica dal percorso che lo attraversa, non dal codice che lo dichiara.
CREATE TEMP TABLE tmp_acc_a AS
SELECT * FROM vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_pa_reso));

SELECT is(
  (SELECT count(*)::int FROM vendite.resi_righe_accrediti a
    WHERE a.resi_riga_id = (SELECT resi_riga_id FROM tmp_pa_reso)),
  1,
  '2) il verbo ha scritto UNA coppia sul ponte (la partita ha una sola riga di fattura)'
);

-- ============================================================
-- I RIFIUTI. ⚠️ SQLSTATE o frase, mai throws_ok nudo: senza discriminante
--    accetterebbe qualunque errore, anche il crash del guard stesso.
-- ============================================================
SELECT throws_like(
  format($$ SELECT * FROM vendite.fn_annulla_accredito_riga_reso(%s, '   ') $$,
         (SELECT resi_riga_id FROM tmp_pa_reso)),
  '%motivo%',
  '3) il motivo e'' obbligatorio: l''annullo cancella, e senza motivo resta il fatto senza la ragione'
);

SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_annulla_accredito_riga_reso(NULL, 'motivo') $$,
  'P0001', NULL,
  '4) guard sul parametro: id nullo -> errore di dominio, mai normalizzazione silenziosa'
);

SELECT throws_like(
  $$ SELECT * FROM vendite.fn_annulla_accredito_riga_reso(999999999, 'motivo') $$,
  '%valore%',
  '5) riga di reso inesistente -> rifiuto parlante, non un insieme vuoto trattato come «niente da fare»'
);

-- ⭐ La verifica che i tre rifiuti non abbiano lasciato tracce. Un guard che
--    scrive prima di rifiutare passa inosservato per anni: e' l'unica forma in
--    cui il difetto si vede.
SELECT is(
  (SELECT count(*)::int FROM vendite.resi_righe_accrediti a
     WHERE a.resi_riga_id = (SELECT resi_riga_id FROM tmp_pa_reso))::text
  || '|' ||
  (SELECT ca.stato_emissione FROM vendite.commesse_attivita ca
     WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_acc_a)),
  '1|NON_EMESSA',
  '6) dopo i tre rifiuti NIENTE e'' cambiato: la coppia c''e'' e la rettifica e'' ancora da emettere'
);

-- ============================================================
-- L'ANNULLO
-- ============================================================
CREATE TEMP TABLE tmp_ann_a AS
SELECT * FROM vendite.fn_annulla_accredito_riga_reso(
    (SELECT resi_riga_id FROM tmp_pa_reso), 'riga sbagliata, pgTAP');

SELECT is(
  (SELECT count(*)::int || '|' || (min(commessa_attivita_id) = (SELECT commessa_attivita_id FROM tmp_acc_a))::text
     FROM tmp_ann_a),
  '1|true',
  '7) l''annullo ritorna la coppia rimossa, nella stessa forma con cui la madre l''aveva creata'
);

SELECT is(
  (SELECT count(*)::int FROM vendite.resi_righe_accrediti a
    WHERE a.resi_riga_id = (SELECT resi_riga_id FROM tmp_pa_reso)),
  0,
  '8) il ponte e'' vuoto: la coppia si CANCELLA, non si marca (da qui dipende il gate della rinuncia)'
);

SELECT is(
  (SELECT ca.stato_emissione FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_acc_a)),
  'ANNULLATA'::varchar,
  '9) la rettifica e'' ANNULLATA e non cancellata: resta con importo e storia, smette solo di essere eleggibile'
);

-- ============================================================
-- 10) ⭐ L'ASSERZIONE CHE CONTA. «La riga e' sparita» direbbe solo che una
--     DELETE e' andata a buon fine; che l'annullo abbia FUNZIONATO lo dice la
--     coda, ed e' l'unico effetto osservabile dall'operatore.
-- ============================================================
-- ⚠️ Confronto NUMERICO e non testuale: la scala con cui la vista compone
--    accredito_dovuto non e' un contratto, e '3.000000' vs '3.0' renderebbe
--    rosso un test corretto. Se la riga non torna in coda, il risultato e'
--    NULL e ok() fallisce — che e' esattamente cio' che si vuole vedere.
SELECT ok(
  (SELECT q.accredito_dovuto = 3::numeric AND q.gia_accreditato = 0::numeric
     FROM vendite.vw_resi_da_accreditare q
    WHERE q.resi_riga_id = (SELECT resi_riga_id FROM tmp_pa_reso)),
  '10) LA CODA RISALE: l''accredito torna dovuto per intero e il gia'' accreditato torna a zero'
);

SELECT is(
  (SELECT l.dettaglio ->> 'motivo' FROM vendite.commesse_attivita_log l
    WHERE l.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_acc_a)
      AND l.evento = 'ACCREDITO_ANNULLATO'
    ORDER BY l.id DESC LIMIT 1),
  'riga sbagliata, pgTAP',
  '11) audit: l''evento ACCREDITO_ANNULLATO porta il motivo — unica traccia del perche'''
);

SELECT throws_like(
  format($$ SELECT * FROM vendite.fn_annulla_accredito_riga_reso(%s, 'ancora') $$,
         (SELECT resi_riga_id FROM tmp_pa_reso)),
  '%nessun accredito%',
  '12) un secondo annullo non trova nulla: dopo il primo, «mai accreditato» e «gia'' annullato» sono lo stesso stato'
);

-- ⭐ La prova finale: la merce e' di nuovo accreditabile DAVVERO, non solo
--    «sembra» libera. Se il ponte non fosse stato cancellato, la madre
--    solleverebbe ancora E_ACCREDITO_GIA_ESEGUITO.
SELECT is(
  (SELECT count(*)::int FROM vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_pa_reso))),
  1,
  '13) un secondo accredito RIESCE: e'' la prova che l''annullo ha restituito la merce alla coda'
);

-- ============================================================
-- PARTITA B — LA SEMANTICA D'INSIEME (C-2)
--   Senza questo blocco una fixture a UNA sola rettifica passerebbe anche con
--   la versione sbagliata della funzione, quella che annulla «quel che puo'».
-- ============================================================
CREATE TEMP TABLE tmp_pb AS
SELECT b.ordine_riga_id, b.ddt_id, b.ddt_uid, b.ddt_riga_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('annulla accredito',
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs_ann),
           p_quantita             => 10,
           p_prezzo               => 25,
           p_articolo_id          => (SELECT articolo_id FROM tmp_refs_ann),
           p_fatturazione_trigger => 'CONSEGNATO') b;
-- E-3: l'attivita' sul segmento della bolla dichiara la sorgente DDT_VENDITA.
CREATE TEMP TABLE tmp_pb_att AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM tmp_com_ann), 25,
           p_articolo_id      => (SELECT articolo_id FROM tmp_refs_ann),
           p_sorgente_codice  => 'DDT_VENDITA',
           p_sorgente_uid     => (SELECT ddt_uid FROM tmp_pb)::text,
           p_sorgente_riga_id => (SELECT ddt_riga_id FROM tmp_pb),
           p_quantita         => 10);
CREATE TEMP TABLE tmp_pb_fattura AS
SELECT f.fattura_riga_id
  FROM dbops.fn_pgtap_fattura_attivita('annulla accredito pb',
           ARRAY[(SELECT attivita_id FROM tmp_pb_att)]) f;
CREATE TEMP TABLE tmp_pb_reso AS
SELECT x.resi_riga_id
  FROM dbops.fn_pgtap_crea_reso('annulla accredito', (SELECT ddt_id FROM tmp_pb), 3,
           p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_pb)) x;

CREATE TEMP TABLE tmp_acc_b AS
SELECT * FROM vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_pb_reso));

-- La SECONDA coppia. ⚠️ Costruita qui e non attesa dalla madre: il plurale
--   nasce dal consumo LIFO su piu' righe di fattura o dai componenti di un
--   kit, e nessuna delle due forme si fissa in una fixture senza inseguire
--   l'aritmetica della coda. Cio' che si collauda qui e' la semantica
--   dell'ANNULLO, il cui ingresso e' il ponte — e la seconda rettifica nasce
--   comunque da fn_upsert_commessa_attivita, la stessa che usa la madre.
-- ⚠️ L'INSERT ... RETURNING sta in una CTE e non in una sottoquery del FROM:
--    PostgreSQL ammette gli statement che scrivono SOLO dentro un WITH.
--    ⛔ E la fattura padre e' gia' stata scritta da un'istruzione PRECEDENTE:
--    padre e figlio nella stessa CTE condividerebbero la snapshot, e la policy
--    che risolve il perimetro dal padre non lo troverebbe.
CREATE TEMP TABLE tmp_pb_riga2 AS
WITH ins AS (
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione,
      uom_id, qta, prezzo_unitario, iva_id, imponibile_riga, competenza_dal, competenza_al)
  SELECT fr.fattura_id, 2, r.articolo_id, 'Seconda riga fattura pgTAP', fr.uom_id, 5, 25,
         r.iva_id, 125, script.fn_data_operativa(), script.fn_data_operativa()
    FROM vendite.fatture_righe fr, tmp_refs_ann r
   WHERE fr.id = (SELECT fattura_riga_id FROM tmp_pb_fattura)
  RETURNING id)
SELECT id AS fattura_riga_id FROM ins;

CREATE TEMP TABLE tmp_pb_ret2 AS
SELECT u.attivita_id AS commessa_attivita_id
  FROM tmp_refs_ann r,
       vendite.fn_upsert_commessa_attivita(
         p_commessa_id                 => (SELECT commessa_id FROM tmp_com_ann),
         p_segment_key                 => (script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_pb)::text,
                                                                 (SELECT ddt_riga_id FROM tmp_pb))
                                            || '#RET:2')::varchar,
         p_articolo_id                 => r.articolo_id,
         p_istanza_utility_id          => r.istanza_utility_id,
         p_data_attivita               => DATE '2026-07-31',
         p_uom_id                      => (SELECT uom_id FROM tmp_pb_att),
         p_quantita                    => -1,
         p_competenza_mese             => DATE '2026-07-01',
         p_competenza_dal              => DATE '2026-07-31',
         p_competenza_al               => DATE '2026-07-31',
         p_prezzo_snapshot             => 25,
         p_prezzo_base_snapshot        => 25,
         p_origine_prezzo              => 'MANUALE',
         -- ⚠️ I primi 19 parametri della upsert NON hanno DEFAULT: vanno
         --    passati tutti, anche quelli che qui non dicono nulla.
         p_tipo_variazione_applicata     => 'NESSUNA',
         p_valore_variazione_applicata   => NULL,
         p_promo_id                      => NULL,
         p_contratto_id                  => NULL,
         p_categoria_cliente_id_snapshot => NULL,
         p_classe_utenza_id_snapshot     => NULL,
         p_tipo_doc_fiscale_id         => r.tipo_doc_fiscale_id,
         p_valuta_id                   => r.valuta_id,
         p_prezzo_bloccato             => true,
         p_pricing_mode                => 'FIXED',
         p_stato_approvazione          => 'APPROVATA',
         p_stato_emissione             => 'NON_EMESSA',
         p_tipo_movimento              => 'RETTIFICA',
         p_natura_doc_id               => r.natura_nc_id,
         p_fattura_riga_rettificata_id => (SELECT fattura_riga_id FROM tmp_pb_riga2)) AS u;

INSERT INTO vendite.resi_righe_accrediti
       (resi_riga_id, fattura_riga_rettificata_id, qta, qta_partita, gruppo, commessa_attivita_id, meta)
SELECT (SELECT resi_riga_id FROM tmp_pb_reso),
       (SELECT fattura_riga_id FROM tmp_pb_riga2),
       1, 1,
       (script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_pb)::text, (SELECT ddt_riga_id FROM tmp_pb)) || '#RET:2')::varchar,
       (SELECT commessa_attivita_id FROM tmp_pb_ret2),
       '{}'::jsonb;

SELECT is(
  (SELECT count(*)::int FROM vendite.resi_righe_accrediti a
     WHERE a.resi_riga_id = (SELECT resi_riga_id FROM tmp_pb_reso))::text
  || '|' ||
  (SELECT count(DISTINCT a.commessa_attivita_id)::int FROM vendite.resi_righe_accrediti a
     WHERE a.resi_riga_id = (SELECT resi_riga_id FROM tmp_pb_reso))::text,
  '2|2',
  '14) fixture plurale: la riga di reso porta DUE coppie e DUE rettifiche'
);

-- Le rettifiche vengono EMESSE e FATTURATE, ciascuna nella sua nota (il
-- builder emette dalla madre tutte le attivita' approvate della commessa);
-- poi si toglie SOLO la prima nota col verbo vero del reset,
-- vendite.fn_cleanup_fatture_by_ids (E-4): resta una rettifica emessa e una
-- che ha attraversato il reset, con l'attivita' fatturabile sopravvissuta.
CREATE TEMP TABLE tmp_pb_nc1 AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('annulla accredito nc 1',
           ARRAY[(SELECT commessa_attivita_id FROM tmp_acc_b)]);
CREATE TEMP TABLE tmp_pb_nc2 AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('annulla accredito nc 2',
           ARRAY[(SELECT commessa_attivita_id FROM tmp_pb_ret2)]);
CREATE TEMP TABLE tmp_pb_reset1 AS
SELECT * FROM vendite.fn_cleanup_fatture_by_ids(ARRAY[(SELECT fattura_id FROM tmp_pb_nc1)], NULL);

SELECT throws_like(
  format($$ SELECT * FROM vendite.fn_annulla_accredito_riga_reso(%s, 'ci ho ripensato') $$,
         (SELECT resi_riga_id FROM tmp_pb_reso)),
  '%gia'' emesse%',
  '15) UNA sola rettifica emessa basta a rifiutare l''INTERO annullo: la decisione e'' d''insieme'
);

SELECT is(
  (SELECT count(*)::int FROM vendite.resi_righe_accrediti a
     WHERE a.resi_riga_id = (SELECT resi_riga_id FROM tmp_pb_reso))::text
  || '|' ||
  (SELECT ca.stato_emissione FROM vendite.commesse_attivita ca
     WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_acc_b)),
  '2|NON_EMESSA',
  '16) e il rifiuto non ha toccato NIENTE: tutto-o-niente, non «quel che si puo''»'
);

-- ============================================================
-- 17) ⭐ Reset anche della seconda. Le attivita_fatturabili SOPRAVVIVONO al
--     reset (fn_cleanup_fatture_by_ids le sblocca e azzera fattura_riga_id,
--     non le cancella): se la funzione avesse scritto la scorciatoia «esiste
--     una AF -> bloccato», qui rifiuterebbe per sempre un annullo legittimo.
-- ============================================================
CREATE TEMP TABLE tmp_pb_reset2 AS
SELECT * FROM vendite.fn_cleanup_fatture_by_ids(ARRAY[(SELECT fattura_id FROM tmp_pb_nc2)], NULL);

-- ⚠️ Il verbo si chiama in un'ISTRUZIONE A PARTE, mai dentro la SELECT che ne
--    verifica gli effetti. Sotto READ COMMITTED tutte le sottoquery di uno
--    stesso statement condividono la snapshot presa al suo inizio: la
--    `count(*)` sul ponte leggerebbe lo stato PRIMA della DELETE e il test
--    fallirebbe accusando la funzione di non aver fatto nulla. E' la stessa
--    trappola delle CTE che scrivono, in un'altra veste.
CREATE TEMP TABLE tmp_ann_b AS
SELECT * FROM vendite.fn_annulla_accredito_riga_reso(
    (SELECT resi_riga_id FROM tmp_pb_reso), 'dopo il reset del lotto');

SELECT is(
  (SELECT count(*)::int FROM tmp_ann_b)::text
  || '|' ||
  (SELECT count(*)::int FROM vendite.resi_righe_accrediti a
     WHERE a.resi_riga_id = (SELECT resi_riga_id FROM tmp_pb_reso))::text
  || '|' ||
  (SELECT count(*)::int FROM vendite.commesse_attivita ca
     WHERE ca.id IN ((SELECT commessa_attivita_id FROM tmp_acc_b),
                     (SELECT commessa_attivita_id FROM tmp_pb_ret2))
       AND ca.stato_emissione = 'ANNULLATA'),
  '2|0|2',
  '17) l''AF sopravvissuta al reset NON blocca: l''annullo toglie entrambe le coppie e annulla entrambe le rettifiche'
);

-- ============================================================
-- 18) ⭐⭐ LA CHIUSURA DEL CERCHIO. Il test 10 mostra che la coda risale sul
--     percorso pulito; questo lo mostra sul percorso che l'errore stesso
--     consiglia — accredito, emissione, reset del lotto, annullo.
--     ⚠️ Le due rettifiche della partita B hanno lasciato ciascuna la propria
--     attivita_fatturabili, sopravvissuta al reset. Se il conto della merce
--     continuasse a sommarle, la partita resterebbe pareggiata e questa riga
--     non tornerebbe MAI accreditabile da nessuno: il ponte e' vuoto, ma la
--     merce e' persa. E' il difetto di §10, e questo test e' la sua misura.
--     ⛔ Rosso prima del changeset 20260818-73, verde dopo.
-- ============================================================
SELECT ok(
  (SELECT q.accredito_dovuto = 3::numeric AND q.gia_accreditato = 0::numeric
     FROM vendite.vw_resi_da_accreditare q
    WHERE q.resi_riga_id = (SELECT resi_riga_id FROM tmp_pb_reso)),
  '18) percorso completo (accredito -> emissione -> reset -> annullo): LA CODA RISALE, e la merce resa torna accreditabile'
);


-- ---- 19..23: PARTITA C — la sede unica del predicato ---------------------
SELECT has_function('script', 'fn_check_accredito_annullabile',
                    ARRAY['bigint'],
                    '19) script.fn_check_accredito_annullabile esiste');

-- E' una LETTURA, non un verbo: se un domani scrivesse, la vista che la chiama
-- per riga diventerebbe una scrittura per riga di lista.
SELECT is(
    (SELECT provolatile::text FROM pg_proc
      WHERE oid = 'script.fn_check_accredito_annullabile(bigint)'::regprocedure),
    's', '20) fn_check_accredito_annullabile e'' STABLE');

-- SECURITY INVOKER: il motivo FUORI_PERIMETRO nasce dalla RLS di
-- commesse_attivita, e deve essere quella di CHI CHIEDE. Con DEFINER
-- risponderebbe sempre «si puo''» e il pulsante resterebbe acceso su un annullo
-- che la madre rifiuta — di nuovo il difetto di partenza.
SELECT is(
    (SELECT prosecdef FROM pg_proc
      WHERE oid = 'script.fn_check_accredito_annullabile(bigint)'::regprocedure),
    false, '21) fn_check_accredito_annullabile e'' SECURITY INVOKER');

-- ⛔⛔ IL PRESIDIO DELLA RICHIESTA DEL BE, e vale la pena dire perche' e'
--    STRUTTURALE e non comportamentale. Un test che chiamasse la madre e
--    confrontasse l'esito col check proverebbe che oggi coincidono; questo
--    prova che NON POSSONO divergere, perche' la regola sta scritta in un
--    posto solo. E' la differenza fra misurare un accordo e renderlo
--    impossibile da rompere.
--    Le due asserzioni sono una sola condizione in due meta': la chiamata c'e'
--    E il predicato non c'e' piu'. Senza la seconda, un copia-incolla
--    dimenticato passerebbe.
SELECT is(
    (SELECT count(*)::int FROM (
        SELECT pg_get_functiondef('vendite.fn_annulla_accredito_riga_reso(bigint,text)'::regprocedure) AS src
     ) q
     WHERE q.src LIKE '%script.fn_check_accredito_annullabile%'
       AND q.src NOT LIKE '%stato_emissione <> ''NON_EMESSA''%'),
    1, '22) sede unica: la madre chiama la check e non ripete il predicato');

-- linee-guida-sql §12.4: «le capability stanno solo sul DETTAGLIO, mai per riga
-- di lista; le liste fanno il gate sui codici che hanno gia' in riga».
SELECT has_column('vendite', 'vw_resi_da_accreditare', 'annullo_blocco_codice',
                  '23) la coda accrediti porta annullo_blocco_codice in riga');

SELECT * FROM finish();
ROLLBACK;
