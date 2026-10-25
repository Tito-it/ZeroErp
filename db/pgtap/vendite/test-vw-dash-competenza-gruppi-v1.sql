-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2d): area_documento diventa documento_apribile (config.sorgenti.area ritirata).
-- pgTAP test per Zero ERP
-- Test: vendite.vw_dash_competenza_gruppi (elenco dei gruppi fatturabili)
-- Brief: brief-db-emissione-fattura-per-documento-sorgente PARTE A (step A10)
-- Changeset coperti: 20260727-16, 20260727-17 (+ seed CSV), 20260727-18
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima il
--   preventivo nasceva gia' ACCETTATO).
-- rev 2026-10-25 (brief-modello-documento-vendita §8, giro 6): il preventivo
--   si emette con una riga (merce, 1 x 10) da
--   dbops.fn_pgtap_crea_preventivo_con_righe (p_preventivo_id): l'emissione
--   senza righe e' rifiutata. Conteggi e valori dei test leggono le righe
--   della commessa, non del preventivo: non cambiano.
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): il mondo si
--   COSTRUISCE (azienda A col suo operatore, cliente, articolo servizio; per il
--   test 8 un'azienda B) invece di pescare «il primo BA / articolo / emittente /
--   operatore»; il contratto nasce DRAFT da dbops.fn_pgtap_crea_contratto.
--   L'articolo-onere resta del catalogo seminato (uno per causale, UNIQUE): si
--   legge per la causale SPESE_TRASFERTA, non «il primo per id».
-- rev 2026-10-24 (brief-modello-documento-vendita R-2/R-9): l'azienda A, il
--   suo operatore, il contesto e il cliente nascono da
--   dbops.fn_pgtap_crea_mondo_cliente (whitelist su A dal builder: tolta la
--   prima riscrittura a mano e il set_config; resta quella del test 8, che
--   sposta lo scope su B ed e' il caso del test); il contratto nasce DRAFT col
--   periodo 2081 dal builder.
-- ------------------------------------------------------------
-- Indice test (plan 8):
--  1) la vista espone i 3 gruppi della commessa: preventivo, contratto, oneri
--  2) n_attivita per gruppo = 2 / 2 / 1
--  3) valore per gruppo = somma di prezzo_snapshot * quantita
--  4) G8 ⭐ la somma dei gruppi coincide con le righe DA_EMETTERE della vista base
--  5) G8 le chiavi esposte sono accettate TALI E QUALI da fn_emit come p_gruppi
--  6) D-5 riferimento del gruppo documento = numero del documento (sorgente apribile)
--  7) G4 il gruppo oneri c'e', con documento_apribile NULL e riferimento = commessa (LEFT JOIN)
--  8) G14 operatore fuori scope emittente -> zero righe
--  (security_invoker: presidiato da rls/test-rls-viste-security-invoker.sql,
--   non piu' qui)
--  (10: TOLTO il 2026-09-09 col ritiro della vista di riepilogo — il perche' e
--   dove e' finito l'invariante stanno in coda al file, dove il test stava)
-- ------------------------------------------------------------
-- ⭐ IL TEST 4 e' quello che protegge la promessa di D-4: l'elenco e' derivato
--    da vw_dash_competenza_attivita proprio perche' i suoi numeri coincidano
--    con quelli della card PER COSTRUZIONE. Se qualcuno riscrivesse la vista
--    come query autonoma, e' il test che se ne accorge.
--
-- ⚠️ COSA QUESTO FILE NON COPRE (limite dichiarato). Il test 8 verifica lo
--    scope sul lato LETTURA (la vista, che filtra via GUC +
--    script.fn_get_emittenti_scope_sr_ids). Lo scope sul lato EMISSIONE —
--    passare a fn_emit la chiave di un gruppo fuori perimetro — e' presidiato
--    dalla RLS su vendite.commesse, che pgTAP NON puo' esercitare: gira come
--    owner e la bypassa. Verificarlo richiede un test applicativo con il ruolo
--    zeroerp_app, non un pgTAP.
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
-- ⭐ rev 2026-10-24 (Q-4): l'azienda A e il suo operatore si costruiscono, e
--   il contesto si apre su di lui; B e' solo un emittente, il perimetro fuori
--   scope del test 8.
-- rev 2026-10-24 (R-9): A, l'operatore, il contesto e il cliente sono il
--   mondo del builder, in una chiamata.
CREATE TEMP TABLE tmp_vg_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('vista gruppi');

CREATE TEMP TABLE tmp_vg_ef_b AS
SELECT * FROM dbops.fn_pgtap_crea_emittente();

-- Il contesto l'ha gia' aperto il mondo sul suo operatore: la riga lo rende
-- esplicito (ed e' cio' che legge scripts/guardrail_pgtap_preambolo.py).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_vg_mondo)); END $ctx$;

SELECT plan(8);

CREATE TEMP TABLE tmp_vg_cli AS
SELECT billing_account_id, istanza_utility_id, utility_id FROM tmp_vg_mondo;

-- ============================================================
-- Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_vg_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_vg_cli)       AS billing_account_id,
  (SELECT utility_id FROM tmp_vg_cli)               AS utility_id,
  (SELECT istanza_utility_id FROM tmp_vg_cli)       AS istanza_utility_id,
  dbops.fn_pgtap_crea_articolo('PGT-VG-SERV', false,
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                               WHERE codice_interno = 'SERVIZIO_UNA_TANTUM')) AS articolo_id,
  (SELECT a.id FROM catalogo.articoli a
     JOIN config.causali_onere co ON co.id = a.causale_onere_id
    WHERE co.codice_interno = 'SPESE_TRASFERTA' AND a.attivo IS TRUE) AS articolo_onere_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT emittente_fiscale_id FROM tmp_vg_mondo) AS emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'ACCETTATO' AND s.attivo IS TRUE LIMIT 1) AS stato_prev_accettato_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE
      AND EXISTS (SELECT 1 FROM vendite.tipi_doc_fiscale_registri m WHERE m.tipo_doc_fiscale_id = t.id)
    ORDER BY t.id LIMIT 1)                          AS tipo_doc_fiscale_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO' LIMIT 1) AS src_preventivo_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'CONTRATTO' LIMIT 1)  AS src_contratto_id,
  (SELECT s.id FROM config.stati_doc_contratti s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE LIMIT 1)                AS stato_contr_draft_id;

-- ⚠️ rev 2026-10-24: il preventivo nasce in bozza (lo stato non si scrive: lo
--   mette il trigger della nascita) e va ad ACCETTATO sotto i guard veri.
-- ⚠️ rev 2026-10-25 (§8, giro 6): con una riga (merce, 1 x 10) scritta in
--   bozza da dbops.fn_pgtap_crea_preventivo_con_righe, che poi porta lo stato:
--   senza righe l'emissione e' rifiutata (E_PREV_NESSUNA_RIGA_ATTIVA). I
--   valori dei gruppi si leggono dalle righe di COMMESSA (100 cad.), non da
--   quella del preventivo: la riga in piu' non li tocca.
CREATE TEMP TABLE tmp_vg_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-VGRUPPI', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2081-01-01', DATE '2081-12-31', r.valuta_id,
         DATE '2081-01-01', false, false,
         jsonb_build_object('test_scope', 'pgtap_vgruppi'), r.emittente_fiscale_id
  FROM tmp_vg_refs r
  RETURNING id, uid, numero)
SELECT * FROM ins;

DO $porta$ BEGIN
  PERFORM dbops.fn_pgtap_crea_preventivo_con_righe('vgruppi', 'ACCETTATO',
            p_preventivo_id => (SELECT id FROM tmp_vg_prev));
END $porta$;

-- Contratto VERO per il gruppo C (rev 2026-10-13): basta la testata in bozza.
--   La madre lo aggancia alla commessa (20261012-46) e il link ne verifica
--   l'esistenza: un uuid inventato non passa piu'.
-- rev 2026-10-24 (Q-2): nasce dal builder, dalla madre di produzione, sul
--   cliente del test.
-- rev 2026-10-24 (R-2): il periodo e la data 2081 li prende dal builder.
CREATE TEMP TABLE tmp_vg_k AS
SELECT * FROM dbops.fn_pgtap_crea_contratto(
                 'vista gruppi', 'DRAFT', (SELECT billing_account_id FROM tmp_vg_refs), NULL,
                 DATE '2081-01-01', DATE '2081-12-31', DATE '2081-01-01');

CREATE TEMP TABLE tmp_vg_contr AS
SELECT k.id, k.uid FROM vendite.contratti k WHERE k.id = (SELECT contratto_id FROM tmp_vg_k);

CREATE TEMP TABLE tmp_vg_comm AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_vg_refs),
  p_utility_id => (SELECT utility_id FROM tmp_vg_refs),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2081-01-01',
  p_competenza_al => DATE '2081-01-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_vgruppi'),
  p_force_new => true
) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id      => (SELECT commessa_id FROM tmp_vg_comm),
  p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_vg_refs),
  p_sorgente_uid     => (SELECT uid::text FROM tmp_vg_prev),
  p_meta             => jsonb_build_object('test_scope', 'pgtap_vgruppi')
);

-- 4 righe documentali: 2 preventivo (100 cad.) + 2 contratto (50 cad.)
CREATE TEMP TABLE tmp_vg_righe AS
SELECT r.attivita_id
FROM (VALUES ('P', 1, 100.0), ('P', 2, 100.0), ('C', 1, 50.0), ('C', 2, 50.0)) AS x(g, n, prezzo)
CROSS JOIN LATERAL (
  SELECT * FROM vendite.fn_upsert_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM tmp_vg_comm),
    p_segment_key => ('SEG-VG-' || x.g || '-' || x.n)::varchar,
    p_articolo_id => (SELECT articolo_id FROM tmp_vg_refs),
    p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_vg_refs),
    p_data_attivita => DATE '2081-01-15',
    p_uom_id => (SELECT uom_id FROM tmp_vg_refs),
    p_quantita => 1.000000,
    p_competenza_mese => DATE '2081-01-01',
    p_competenza_dal => DATE '2081-01-01',
    p_competenza_al => DATE '2081-01-31',
    p_prezzo_snapshot => x.prezzo,
    p_prezzo_base_snapshot => NULL,
    p_origine_prezzo => NULL,
    p_tipo_variazione_applicata => NULL,
    p_valore_variazione_applicata => NULL,
    p_promo_id => NULL,
    p_contratto_id => NULL,
    p_categoria_cliente_id_snapshot => NULL,
    p_classe_utenza_id_snapshot => NULL,
    p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_vg_refs),
    p_valuta_id => (SELECT valuta_id FROM tmp_vg_refs),
    p_stato_approvazione => 'APPROVATA',
    p_stato_emissione => 'NON_EMESSA',
    p_sorgente_tipo_id => CASE WHEN x.g = 'P'
                               THEN (SELECT src_preventivo_id FROM tmp_vg_refs)
                               ELSE (SELECT src_contratto_id FROM tmp_vg_refs) END,
    p_sorgente_uid => CASE WHEN x.g = 'P'
                           THEN (SELECT uid::text FROM tmp_vg_prev)
                           ELSE (SELECT uid::text FROM tmp_vg_contr) END,
    p_tipo_movimento => 'NORMALE',
    p_meta => jsonb_build_object('test_scope', 'pgtap_vgruppi')
  )
) r;

-- Riga onere (500) dalla porta manuale: sourceless.
CREATE TEMP TABLE tmp_vg_onere AS
SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id => (SELECT commessa_id FROM tmp_vg_comm),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_vg_refs),
  p_articolo_onere_id => (SELECT articolo_onere_id FROM tmp_vg_refs),
  p_importo => 500.00,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_vg_refs),
  p_motivo => 'pgtap vista gruppi',
  p_data_attivita => DATE '2081-01-20'
) AS attivita_id;

-- ============================================================
-- ⚠️ SESSIONE OPERATORE: la vista base e' FAIL-CLOSED senza GUC.
--   script.fn_get_emittenti_scope_sr_ids(NULL) restituisce l'array VUOTO
--   (non NULL), e la clausola della vista e'
--     escope.sr_ids IS NULL OR emittente = ANY(sr_ids)
--   quindi senza app.current_user_id nessuna riga passa: e' voluto
--   (fail-closed), ma significa che un test che non imposta la sessione
--   misurerebbe zero per il motivo sbagliato.
--   Qui impersoniamo un operatore whitelistato sull'emittente della commessa
--   fixture; al test 8 spostiamo la whitelist su un altro emittente.
--   rev 2026-10-24 (R-9): la sessione e la whitelist su A le ha aperte il
--   mondo (la commessa nasce sul suo cliente, quindi e' di A): la riscrittura
--   a mano verso «l'emittente effettivo della commessa» e il set_config sono
--   usciti.
-- ============================================================
CREATE TEMP TABLE tmp_vg_op AS
SELECT id.auth_user_id AS user_id
  FROM anagrafiche.identita_digitali id
 WHERE id.auth_user_id = (SELECT auth_user_id FROM tmp_vg_mondo)
   AND id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND id.attivo = true
   AND NOT EXISTS (
       SELECT 1 FROM config.profili_accesso_bindings pab
       JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
       WHERE pab.identita_digitale_id = id.id
         AND pab.attivo = true
         AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso);

-- ============================================================
-- TEST 1: i tre gruppi ci sono tutti — documenti E oneri.
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM vendite.vw_dash_competenza_gruppi g
    WHERE g.commessa_id = (SELECT commessa_id FROM tmp_vg_comm)
      AND g.stadio = 'DA_EMETTERE'),
  3,
  '1) la vista espone 3 gruppi: preventivo, contratto, oneri'
);

-- ============================================================
-- TEST 2: il PESO di ciascun gruppo — e' il numero che dice all'operatore
--   quanto sta per fatturare PRIMA di agire (requisito A3).
-- ============================================================
SELECT is(
  ARRAY(
    SELECT g.n_attivita FROM vendite.vw_dash_competenza_gruppi g
     WHERE g.commessa_id = (SELECT commessa_id FROM tmp_vg_comm)
       AND g.stadio = 'DA_EMETTERE'
     ORDER BY g.tipo_gruppo
  ),
  ARRAY[2::bigint, 1::bigint, 2::bigint],   -- CONTRATTO, ONERI_COMMESSA, PREVENTIVO
  '2) n_attivita per gruppo = 2 (contratto) / 1 (oneri) / 2 (preventivo)'
);

-- ============================================================
-- TEST 3: il valore. 2x100 preventivo, 2x50 contratto, 500 onere.
-- ============================================================
SELECT is(
  (SELECT g.valore FROM vendite.vw_dash_competenza_gruppi g
    WHERE g.commessa_id = (SELECT commessa_id FROM tmp_vg_comm)
      AND g.tipo_gruppo = 'PREVENTIVO'
      AND g.stadio = 'DA_EMETTERE'),
  200.00::numeric,
  '3) valore del gruppo preventivo = 2 x 100'
);

-- ============================================================
-- TEST 4 ⭐ (G8): riconciliazione con la vista base.
--   La somma delle attivita' dei gruppi DEVE coincidere con il numero di
--   righe DA_EMETTERE che alimenta la card. E' la promessa di D-4.
-- ============================================================
SELECT is(
  (SELECT COALESCE(sum(g.n_attivita), 0)::int
     FROM vendite.vw_dash_competenza_gruppi g
    WHERE g.commessa_id = (SELECT commessa_id FROM tmp_vg_comm)
      AND g.stadio = 'DA_EMETTERE'),
  (SELECT count(*)::int
     FROM vendite.vw_dash_competenza_attivita a
    WHERE a.commessa_id = (SELECT commessa_id FROM tmp_vg_comm)
      AND a.stadio = 'DA_EMETTERE'),
  '4) G8: somma dei gruppi = righe DA_EMETTERE della vista base'
);

-- ============================================================
-- TEST 5 (G8): round-trip. Le chiavi che l'elenco mostra sono ESATTAMENTE
--   quelle che l'emissione accetta: il FE passa cio' che legge, senza
--   mappature. Si prende la chiave DALLA VISTA e la si da' a fn_emit.
-- ============================================================
SELECT is(
  (SELECT total_candidate FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
      p_commessa_id => (SELECT commessa_id FROM tmp_vg_comm),
      p_dry_run => true,
      p_gruppi => ARRAY(
        SELECT g.gruppo_key FROM vendite.vw_dash_competenza_gruppi g
         WHERE g.commessa_id = (SELECT commessa_id FROM tmp_vg_comm)
           AND g.tipo_gruppo = 'PREVENTIVO'
           AND g.stadio = 'DA_EMETTERE'))),
  2,
  '5) G8: la chiave letta dalla vista e'' accettata da fn_emit tale e quale'
);

-- ============================================================
-- TEST 6 (D-5): il riferimento leggibile. L'operatore deve vedere il numero
--   del documento, non la chiave. Passa da config.sorgenti.apribile ->
--   vw_dash_fatturazione_documenti.
-- ============================================================
SELECT is(
  (SELECT ARRAY[g.documento_apribile::text, g.riferimento::text]
     FROM vendite.vw_dash_competenza_gruppi g
    WHERE g.commessa_id = (SELECT commessa_id FROM tmp_vg_comm)
      AND g.tipo_gruppo = 'PREVENTIVO'
      AND g.stadio = 'DA_EMETTERE'),
  ARRAY['true'::text, (SELECT numero::text FROM tmp_vg_prev)],
  '6) D-5: gruppo preventivo -> documento apribile e riferimento = numero documento'
);

-- ============================================================
-- TEST 7 (G4): il gruppo oneri non ha sorgente ne' documento, e proprio per
--   questo il join deve essere LEFT: se fosse INNER sparirebbe dall'elenco,
--   che e' esattamente il difetto che il concetto di gruppo evita.
-- ============================================================
SELECT is(
  (SELECT ARRAY[g.tipo_gruppo::text,
                COALESCE(g.documento_apribile::text, '<NULL>'),
                g.riferimento::text]
     FROM vendite.vw_dash_competenza_gruppi g
    WHERE g.commessa_id = (SELECT commessa_id FROM tmp_vg_comm)
      AND g.gruppo_key = 'MAN:' || (SELECT commessa_id::text FROM tmp_vg_comm)),
  ARRAY['ONERI_COMMESSA'::text, '<NULL>'::text,
        (SELECT c.codice::text FROM vendite.commesse c
          WHERE c.id = (SELECT commessa_id FROM tmp_vg_comm))],
  '7) G4: gruppo oneri presente, documento_apribile NULL, riferimento = codice commessa'
);

-- ============================================================
-- TEST 8 (G14): scope emittente. Impostando la sessione come un operatore
--   whitelistato su un ALTRO emittente, i gruppi della commessa spariscono.
--   Non e' una regola riscritta nella vista: e' quella ereditata dalla base.
-- ============================================================
-- Sposta la whitelist dello STESSO operatore su un emittente diverso:
-- cambia solo il perimetro, non l'identita'. Se i gruppi restassero
-- visibili, vorrebbe dire che la vista non eredita davvero lo scope.
-- ⚠️ Questa riscrittura RESTA (rev 2026-10-24, R-9): e' il caso del test.
SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_vg_op);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id)
-- L'emittente diverso e' B, costruito (rev 2026-10-24): prima «il primo
-- emittente attivo diverso».
SELECT (SELECT user_id FROM tmp_vg_op), b.emittente_fiscale_id
  FROM tmp_vg_ef_b b;

SELECT is(
  (SELECT count(*)::int FROM vendite.vw_dash_competenza_gruppi g
    WHERE g.commessa_id = (SELECT commessa_id FROM tmp_vg_comm)),
  0,
  '8) G14: operatore fuori scope emittente -> zero gruppi'
);

SELECT set_config('app.current_user_id', '', true);

-- ============================================================
-- TEST 9: la reloption che PostgreSQL azzera in silenzio a ogni
--   CREATE OR REPLACE VIEW. Perderla trasformerebbe le viste in
--   security_definer di fatto, aprendo un buco nello scope emittente
--   su tutte le dashboard di competenza.
-- ============================================================
-- ⛔ QUI `security_invoker` NON SI PRESIDIA PIU' (rev 2026-09-07), e non e' una
--   rinuncia: lo fa gia' db/pgtap/rls/test-rls-viste-security-invoker.sql, su
--   TUTTE le viste che toccano dati in RLS — anche attraverso altre viste — e
--   leggendo la PROPRIETA' invece della parola. Nessun elenco di nomi.
--   ⚠️ Il doppione locale non aggiungeva copertura, e ne ha tolta: era scritto
--   come confronto di GRAFIA (`security_invoker=on`) ed e' diventato ROSSO su
--   una vista perfettamente sana, riscritta con `= true` — che significa la
--   stessa identica cosa. Due falsi allarmi il 2026-09-07, e una bisezione fra
--   due cantieri per scoprire che non era rotto niente.
--   ⭐ Una seconda sede diverge sempre; questa e' divergiata verso il FALSO
--   ALLARME, che e' il verso che fa spegnere i presidi.


-- ============================================================
-- TEST 10 — TOLTO il 2026-09-09: il suo SOGGETTO non esiste piu'
-- ============================================================
-- ⛔ Asseriva «il riepilogo coincide con la somma dell'elenco» su
--   vendite.vw_dash_competenza_gruppi_riepilogo, RITIRATA dal changeSet
--   20260909-64: il riepilogo che il frontend mostra lo calcola una query del
--   backend, che applica i filtri dell'operatore — cosa che una vista
--   aggregata per (competenza, stadio, emittente) non puo' fare. Le due sedi
--   non convivevano, e a perdere e' stata la vista.
--
-- ⚠️ NON e' un presidio abbandonato: l'invariante si e' SPOSTATO dove sta il
--   calcolo — `P-10` di brief-db-il-trattenuto-passa-lo-stesso.md, un test
--   Django con database. Un invariante si asserisce dove il numero si produce,
--   non dove starebbe comodo.
--
-- ⭐ E COME E' ARRIVATO QUI UN ROSSO: il `-64` aveva censito i lettori della
--   vista e ne aveva trovato UNO (il test 15-ter di
--   test-vw-dash-competenza-v1.sql, tolto nello stesso giro). Questo file era
--   il secondo, e non e' stato guardato. *Cancellare una fonte e' censire i suoi
--   lettori — tutti, e la ricerca si fa sul NOME dell'oggetto in tutto il
--   repository.*
-- ⚠️ Il rosso che ne usciva non era «un test che fallisce»: era un ERRORE di
--   relazione inesistente, quindi il file si fermava li' e perdeva anche il
--   plan. Otto asserzioni sane, e `pg_prove` che dice `Bad plan`.

SELECT * FROM finish();
ROLLBACK;
