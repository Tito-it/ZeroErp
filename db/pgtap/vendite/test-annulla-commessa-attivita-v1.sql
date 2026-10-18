-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE vendite.commesse_attivita_log ADD/DROP CONSTRAINT temporaneo:
--   fault injection per dimostrare che l'INSERT del log fallisce davvero e che
--   l'annullamento e' atomico. Senza DDL il ramo non e' raggiungibile.
-- pgTAP test per Zero ERP
-- Test: annullamento di una riga MANUALE di commessa
--       (vendite.fn_annulla_commessa_attivita).
-- Brief: brief-annullamento-righe-manuali-commessa §4e (garanzie A1-A9),
--        changeset D4 del §9.
--
-- COSA DIMOSTRA. Non che una colonna sia cambiata — quello e' il minimo — ma
-- l'EFFETTO VOLUTO: la riga annullata esce dalla catena di fatturazione (non
-- produce attivita fatturabili) e sparisce dal cockpit di competenza (attivita
-- e gruppi), mentre le sue sorelle restano intatte. Sono i test 19, 24, 25, 26.
--
-- PERIMETRO DEL GUARD. Righe SOURCELESS (sorgente_tipo_id IS NULL) e NON_EMESSA.
-- Le tre vie di rifiuto hanno codici DISTINTI perche' portano l'operatore a tre
-- azioni diverse: gia' annullata (564, non fare nulla), non manuale (565, vai a
-- monte sul documento), gia' emessa (566, nota di credito).
--
-- FIXTURE — due commesse, per non far interferire i test fra loro:
--   com1  giro funzionale: guard, caso felice, riannullamento, riga con
--         sorgente, emissione selettiva, riga emessa, atomicita'.
--   com2  viste di competenza: richiedono una SESSIONE OPERATORE whitelistata
--         (le viste sono fail-closed senza GUC) e un cambio di stato commessa
--         che disturberebbe com1.
--
-- NOTA su come nascono due righe della fixture:
--   - la riga "con sorgente" (test 17-18) e' un onere a cui si assegna una
--     sorgente con UPDATE diretto, invece di simulare un push completo: il
--     test riguarda il GUARD, non il modo in cui le righe da push nascono.
--   - la riga "gia' EMESSA" (test 20-21) lo diventa passando davvero da
--     fn_emit_attivita_fatturabili_da_commessa, non con un UPDATE: cosi' il
--     test 20 verifica il rifiuto su uno stato prodotto dal percorso reale.
-- ------------------------------------------------------------
-- Indice test (1..27):
--   1   funzione madre presente
--   2   codici errore 564-567 a catalogo
--   3   CHECK stato_emissione ammette ANNULLATA (nessuna colonna nuova)
--   4   fixture: commessa con due oneri NON_EMESSA
--   5   guard: id NULL rifiutato
--   6   guard: id <= 0 rifiutato
--   7   guard: motivo vuoto (soli spazi) rifiutato
--   8   guard: motivo NULL rifiutato
--   9   guard: riga inesistente rifiutata
--  10   [A4] dopo i guard nessuna scrittura: stato invariato e log vuoto
--  11   [A1] la madre ritorna il commessa_attivita_id
--  12   [A1] stato_emissione = ANNULLATA
--  13   [A1] stato_approvazione INVARIATO (due assi distinti)
--  14   [A1] evento RIGA_MANUALE_ANNULLATA con motivo, stato_precedente, prezzo
--  15   [A3-bis] riannullare -> E_RIGA_COMMESSA_GIA_ANNULLATA
--  16   [A3-bis] nessun secondo evento nel log
--  17   [A2] riga CON sorgente -> respinta
--  18   [A2] riga con sorgente: stato invariato
--  18-bis ⭐ [D-6] il messaggio NOMINA il documento sorgente, non l uid
--  19   [A5] fn_emit non produce alcuna AF per la riga annullata
--  20   [A3] riga EMESSA (dal percorso reale) -> respinta
--  21   [A3] riga emessa: stato invariato
--  22   [A7] fault injection: l'INSERT del log fallisce davvero
--  23   [A7] atomicita': INSERT del log fallito -> lo stato non cambia
--  24   [A6] la riga annullata sparisce da vw_dash_competenza_attivita
--  25   [A8] gruppo MAN: ancora presente finche' resta una riga viva
--  26   [A8] gruppo MAN: assente quando tutte le righe sono annullate
--  27   [A9] contatori fn_get_commessa_stato ciechi alle righe annullate
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

SELECT plan(28);

-- ============================================================
-- 1..3 struttura
-- ============================================================
SELECT has_function('vendite', 'fn_annulla_commessa_attivita',
    '1) madre fn_annulla_commessa_attivita presente');

SELECT is(
  (SELECT count(*)::int FROM config.messaggi_errore
    WHERE lingua = 'it'
      AND codice IN ('E_RIGA_COMMESSA_GIA_ANNULLATA',
                     'E_RIGA_COMMESSA_NON_MANUALE',
                     'E_RIGA_COMMESSA_GIA_EMESSA',
                     'E_RIGA_COMMESSA_MOTIVO_OBBLIGATORIO')
      AND id BETWEEN 564 AND 567),
  4,
  '2) i quattro codici errore 564-567 sono a catalogo');

-- Il valore ANNULLATA esisteva gia' nel CHECK dal 20260224-07: questa slice non
-- ha aggiunto nessuna colonna e nessun valore. Se il CHECK cambiasse, il resto
-- del test fallirebbe in modo oscuro: meglio dirlo qui.
SELECT ok(
  (SELECT pg_get_constraintdef(c.oid) LIKE '%ANNULLATA%'
     FROM pg_constraint c
     JOIN pg_class t ON t.oid = c.conrelid
     JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname = 'vendite' AND t.relname = 'commesse_attivita'
      AND c.conname = 'chk_commesse_attivita_stato_emissione'),
  '3) CHECK stato_emissione ammette gia'' ANNULLATA (nessuna colonna nuova)');

-- ============================================================
-- fixture comune
-- ============================================================
-- ⭐ Il cliente si FABBRICA, legato all'emittente dell'operatore di contesto
--   (rev 2026-10-18). Prima si pescava «il primo billing account con un
--   emittente»: su un database ricostruito da zero non ce n'e' nessuno, e la
--   fixture moriva con E_PARAMETRO p_billing_account_id.
CREATE TEMP TABLE tmp_cliente AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'pgTAP annulla riga commessa', NULL, script.fn_pgtap_emittente_sr_operatore());

SET CONSTRAINTS ALL IMMEDIATE;

CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_cliente) AS billing_account_id,
  (SELECT utility_id FROM tmp_cliente) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_cliente) AS istanza_utility_id,
  (SELECT anagrafiche.fn_get_emittente_fiscale_id(billing_account_id) FROM tmp_cliente) AS emittente_soggetto_ruolo_id,
  (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
  -- Sorgente ROOT: COMMESSA con uid = id della commessa stessa (la riga esiste
  -- per costruzione). fn_emit esige una ROOT sulla commessa, non ne dereferenzia
  -- il tipo. Stesso espediente di test-porta-oneri-giro-completo-v1.sql.
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA' AND s.attivo LIMIT 1) AS sorgente_root_id,
  (SELECT id FROM catalogo.articoli WHERE codice = 'ONERE_TRASFERTA') AS articolo_onere_id,
  (SELECT id FROM catalogo.articoli WHERE codice = 'ONERE_PENALE') AS articolo_penale_id;

-- ===== com1: giro funzionale =====
CREATE TEMP TABLE tmp_com1 AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
  p_utility_id => (SELECT utility_id FROM tmp_refs),
  p_tipo_commessa => 'AUTO', p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false, p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01', p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_annulla_riga'), p_force_new => true
) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_com1),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs),
  p_sorgente_uid => (SELECT commessa_id FROM tmp_com1)::text,
  p_sorgente_riga => 1, p_meta => '{}'::jsonb);

-- Riga A: quella che verra' annullata.
CREATE TEMP TABLE tmp_riga_a AS
SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id        => (SELECT commessa_id FROM tmp_com1),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs),
  p_articolo_onere_id  => (SELECT articolo_onere_id FROM tmp_refs),
  p_importo            => 500.00,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs),
  p_motivo             => 'onere caricato per errore — pgtap',
  p_data_attivita      => DATE '2026-07-15'
) AS id;

-- Riga B: la sorella che deve restare intatta e poi essere emessa davvero.
CREATE TEMP TABLE tmp_riga_b AS
SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id        => (SELECT commessa_id FROM tmp_com1),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs),
  p_articolo_onere_id  => (SELECT articolo_penale_id FROM tmp_refs),
  p_importo            => 90.00,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs),
  p_motivo             => 'onere buono — pgtap',
  p_data_attivita      => DATE '2026-07-16'
) AS id;

SELECT ok(
  (SELECT count(*) = 2
     FROM vendite.commesse_attivita ca
    WHERE ca.commessa_id = (SELECT commessa_id FROM tmp_com1)
      AND ca.stato_emissione = 'NON_EMESSA'
      AND ca.sorgente_tipo_id IS NULL),
  '4) fixture: commessa con due oneri sourceless NON_EMESSA');

-- ============================================================
-- 5..10 guard di input — nessuno deve scrivere nulla
-- ============================================================
SELECT throws_ok(
  $$ SELECT vendite.fn_annulla_commessa_attivita(NULL::bigint, 'motivo valido') $$,
  'P0001', NULL,
  '5) guard: commessa_attivita_id NULL rifiutato');

SELECT throws_ok(
  $$ SELECT vendite.fn_annulla_commessa_attivita(0, 'motivo valido') $$,
  'P0001', NULL,
  '6) guard: commessa_attivita_id <= 0 rifiutato');

-- Il motivo e' normalizzato con btrim: una stringa di soli spazi e' vuota.
SELECT throws_ok(
  $$ SELECT vendite.fn_annulla_commessa_attivita((SELECT id FROM tmp_riga_a), '   ') $$,
  'P0001', NULL,
  '7) guard: motivo di soli spazi rifiutato (btrim)');

SELECT throws_ok(
  $$ SELECT vendite.fn_annulla_commessa_attivita((SELECT id FROM tmp_riga_a), NULL) $$,
  'P0001', NULL,
  '8) guard: motivo NULL rifiutato');

-- Id inesistente calcolato dal MAX vivo, non una costante a caso: un
-- 999999999 hardcoded diventerebbe un id reale il giorno che la tabella
-- cresce, e il test passerebbe (o fallirebbe) per il motivo sbagliato.
SELECT throws_ok(
  $$ SELECT vendite.fn_annulla_commessa_attivita(
       (SELECT COALESCE(MAX(id), 0) + 1000 FROM vendite.commesse_attivita),
       'motivo valido') $$,
  'P0001', NULL,
  '9) guard: riga inesistente rifiutata');

-- A4: i guard rifiutano PRIMA di toccare qualsiasi cosa. Se uno di loro
-- scrivesse e poi sollevasse, in una transazione lunga (il BE ne apre) lo
-- stato parziale sopravviverebbe fino al rollback esterno.
SELECT ok(
  (SELECT ca.stato_emissione = 'NON_EMESSA'
     FROM vendite.commesse_attivita ca WHERE ca.id = (SELECT id FROM tmp_riga_a))
  AND NOT EXISTS (
    SELECT 1 FROM vendite.commesse_attivita_log l
     WHERE l.commessa_attivita_id = (SELECT id FROM tmp_riga_a)
       AND l.evento = 'RIGA_MANUALE_ANNULLATA'),
  '10) [A4] dopo i guard: stato invariato e nessun evento di annullamento');

-- ============================================================
-- 11..14 [A1] il caso felice
-- ============================================================
CREATE TEMP TABLE tmp_esito_a AS
SELECT vendite.fn_annulla_commessa_attivita(
  (SELECT id FROM tmp_riga_a),
  '  causale sbagliata, ricaricato correttamente  '
) AS id_ritornato;

SELECT is(
  (SELECT id_ritornato FROM tmp_esito_a),
  (SELECT id FROM tmp_riga_a),
  '11) [A1] la madre ritorna il commessa_attivita_id');

SELECT is(
  (SELECT ca.stato_emissione FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT id FROM tmp_riga_a)),
  'ANNULLATA'::varchar,
  '12) [A1] stato_emissione = ANNULLATA');

-- Due assi distinti con CHECK separati: la riga annullata conserva la memoria
-- di essere stata approvata. Azzerare anche l'approvazione perderebbe
-- informazione senza guadagnare nulla.
SELECT is(
  (SELECT ca.stato_approvazione FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT id FROM tmp_riga_a)),
  'APPROVATA'::varchar,
  '13) [A1] stato_approvazione INVARIATO (assi separati)');

-- Il motivo e' salvato NORMALIZZATO (btrim), non come arriva.
SELECT ok(
  (SELECT l.dettaglio->>'motivo' = 'causale sbagliata, ricaricato correttamente'
      AND l.dettaglio->>'stato_precedente' = 'NON_EMESSA'
      AND (l.dettaglio->>'prezzo_snapshot')::numeric = 500.00
      AND l.dettaglio->>'tipo_movimento' = 'ONERE'
     FROM vendite.commesse_attivita_log l
    WHERE l.commessa_attivita_id = (SELECT id FROM tmp_riga_a)
      AND l.evento = 'RIGA_MANUALE_ANNULLATA'),
  '14) [A1] evento con motivo normalizzato, stato_precedente, prezzo, tipo_movimento');

-- ============================================================
-- 15..16 [A3-bis] riannullare: codice DEDICATO, non "gia' emessa"
-- ============================================================
-- Il messaggio 566 ("gia' entrata nella catena di fatturazione") detto a chi ha
-- riannullato una riga e' FALSO e lo manda a cercare una fattura inesistente.
SELECT throws_ok(
  $$ SELECT vendite.fn_annulla_commessa_attivita(
       (SELECT id FROM tmp_riga_a), 'secondo tentativo') $$,
  'P0001', NULL,
  '15) [A3-bis] riannullare e'' rifiutato (E_RIGA_COMMESSA_GIA_ANNULLATA)');

SELECT is(
  (SELECT count(*)::int FROM vendite.commesse_attivita_log l
    WHERE l.commessa_attivita_id = (SELECT id FROM tmp_riga_a)
      AND l.evento = 'RIGA_MANUALE_ANNULLATA'),
  1,
  '16) [A3-bis] nessun secondo evento nel log');

-- ============================================================
-- 17..18 [A2] riga CON sorgente: il rimedio e' a monte
-- ============================================================
-- Riga C: nasce onere e le si assegna una sorgente con UPDATE diretto. Il test
-- riguarda il guard, non il modo in cui le righe da push nascono; la coppia
-- (tipo, uid) rispetta chk_commesse_attivita_sorgente_pair.
CREATE TEMP TABLE tmp_riga_c AS
SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id        => (SELECT commessa_id FROM tmp_com1),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs),
  p_articolo_onere_id  => (SELECT articolo_onere_id FROM tmp_refs),
  p_importo            => 10.00,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs),
  p_motivo             => 'riga che diventera'' con sorgente — pgtap'
) AS id;

UPDATE vendite.commesse_attivita
   SET sorgente_tipo_id = (SELECT sorgente_root_id FROM tmp_refs),
       sorgente_uid     = (SELECT commessa_id FROM tmp_com1)::text
 WHERE id = (SELECT id FROM tmp_riga_c);

SELECT throws_ok(
  $$ SELECT vendite.fn_annulla_commessa_attivita(
       (SELECT id FROM tmp_riga_c), 'tentativo su riga da push') $$,
  'P0001', NULL,
  '17) [A2] riga con sorgente respinta (E_RIGA_COMMESSA_NON_MANUALE)');

SELECT is(
  (SELECT ca.stato_emissione FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT id FROM tmp_riga_c)),
  'NON_EMESSA'::varchar,
  '18) [A2] riga con sorgente: stato invariato');

-- ============================================================
-- 18-bis) ⭐ IL MESSAGGIO NOMINA IL DOCUMENTO (D-6, 2026-08-26)
-- ============================================================
-- ⛔ Qui la FRASE e' la posta in gioco, non il codice: il terzo segnaposto
--   riceveva `sorgente_uid` e a video usciva un UUID, cioe' un valore con cui
--   l'operatore non puo' fare niente. Adesso arriva da
--   vendite.fn_get_sorgente_documento_ref e porta il numero che si legge.
-- ⚠️ Il pattern NON attraversa i segnaposto (AGENTS.md): si aggancia al
--   testo stabile prima e dopo, e al valore atteso in mezzo.
-- ℹ️ La fixture punta la sorgente COMMESSA sulla commessa stessa, e per
--   quella riga di config.sorgenti il label_selector e' `codice`: il numero
--   atteso e' quindi il CODICE della commessa. E' un caso vero della
--   famiglia polimorfa, non un caso costruito per far passare il test.
SELECT throws_like(
  $$ SELECT vendite.fn_annulla_commessa_attivita(
       (SELECT id FROM tmp_riga_c), 'tentativo su riga da push') $$,
  '%nasce dal documento sorgente ' ||
    (SELECT co.codice FROM vendite.commesse co
      WHERE co.id = (SELECT commessa_id FROM tmp_com1)) || '%',
  '18-bis) [D-6] il messaggio NOMINA il documento sorgente, non ne stampa l uid');

-- ============================================================
-- 19 [A5] la porta verso la fattura: l'effetto che conta davvero
-- ============================================================
-- Sulla commessa restano: A (annullata), B (viva), C (viva ma con sorgente).
-- L'emissione deve raccogliere B e C e IGNORARE A.
SELECT vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM tmp_com1), 'PRONTA_FATTURAZIONE');

CREATE TEMP TABLE tmp_emit AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com1));

SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM vendite.attivita_fatturabili af
     WHERE af.commessa_attivita_id = (SELECT id FROM tmp_riga_a))
  AND EXISTS (
    SELECT 1 FROM vendite.attivita_fatturabili af
     WHERE af.commessa_attivita_id = (SELECT id FROM tmp_riga_b)),
  '19) [A5] fn_emit: nessuna AF per la riga annullata, l''AF della sorella c''e''');

-- ============================================================
-- 20..21 [A3] riga EMESSA dal percorso reale
-- ============================================================
-- B e' passata a EMESSA per mano di fn_emit, non con un UPDATE di comodo:
-- il rifiuto viene misurato su uno stato prodotto dal percorso vero.
SELECT throws_ok(
  $$ SELECT vendite.fn_annulla_commessa_attivita(
       (SELECT id FROM tmp_riga_b), 'tentativo su riga emessa') $$,
  'P0001', NULL,
  '20) [A3] riga emessa respinta (E_RIGA_COMMESSA_GIA_EMESSA)');

SELECT is(
  (SELECT ca.stato_emissione FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT id FROM tmp_riga_b)),
  'EMESSA'::varchar,
  '21) [A3] riga emessa: stato invariato');

-- ============================================================
-- 22 [A7] atomicita' con fault injection
-- ============================================================
-- linee-guida-sql §5b esige di provare il ROLLBACK TOTALE, non solo il caso
-- felice. Nulla puo' far fallire spontaneamente l'INSERT del log: lo si fa
-- fallire con un CHECK temporaneo. NOT VALID perche' in questa transazione
-- esiste gia' un evento RIGA_MANUALE_ANNULLATA (riga A) che lo violerebbe in
-- fase di validazione: NOT VALID salta le righe esistenti e vincola solo le
-- nuove, che e' esattamente cio' che serve.
CREATE TEMP TABLE tmp_riga_d AS
SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id        => (SELECT commessa_id FROM tmp_com1),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs),
  p_articolo_onere_id  => (SELECT articolo_onere_id FROM tmp_refs),
  p_importo            => 33.00,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs),
  p_motivo             => 'riga per test atomicita'' — pgtap'
) AS id;

ALTER TABLE vendite.commesse_attivita_log
  ADD CONSTRAINT tmp_pgtap_blocca_evento_annullamento
  CHECK (evento <> 'RIGA_MANUALE_ANNULLATA') NOT VALID;

SELECT throws_ok(
  $$ SELECT vendite.fn_annulla_commessa_attivita(
       (SELECT id FROM tmp_riga_d), 'motivo valido') $$,
  '23514', NULL,
  '22) [A7] fault injection: l''INSERT del log fallisce davvero');

ALTER TABLE vendite.commesse_attivita_log
  DROP CONSTRAINT tmp_pgtap_blocca_evento_annullamento;

-- L'UPDATE dello stato era gia' avvenuto quando l'INSERT e' fallito: se la
-- madre non fosse un'unita' atomica, qui troveremmo ANNULLATA senza log.
SELECT is(
  (SELECT ca.stato_emissione FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT id FROM tmp_riga_d)),
  'NON_EMESSA'::varchar,
  '23) [A7] atomicita'': INSERT del log fallito -> stato NON cambiato');

-- ============================================================
-- 23..25 [A6][A8] il cockpit di competenza — com2 + sessione operatore
-- ============================================================
-- ⚠️ Le viste sono FAIL-CLOSED senza GUC: script.fn_get_emittenti_scope_sr_ids(NULL)
--   torna l'array VUOTO (non NULL) e la clausola e' "sr_ids IS NULL OR ...",
--   quindi senza sessione impostata nessuna riga passa e i test misurerebbero
--   zero per il motivo sbagliato. Si impersona un operatore whitelistato
--   sull'emittente EFFETTIVO della commessa fixture.
CREATE TEMP TABLE tmp_com2 AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
  p_utility_id => (SELECT utility_id FROM tmp_refs),
  p_tipo_commessa => 'AUTO', p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false, p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01', p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_annulla_riga_viste'), p_force_new => true
) AS commessa_id;

CREATE TEMP TABLE tmp_riga_e AS
SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id        => (SELECT commessa_id FROM tmp_com2),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs),
  p_articolo_onere_id  => (SELECT articolo_onere_id FROM tmp_refs),
  p_importo            => 120.00,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs),
  p_motivo             => 'onere vista 1 — pgtap'
) AS id;

CREATE TEMP TABLE tmp_riga_f AS
SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id        => (SELECT commessa_id FROM tmp_com2),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs),
  p_articolo_onere_id  => (SELECT articolo_penale_id FROM tmp_refs),
  p_importo            => 80.00,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs),
  p_motivo             => 'onere vista 2 — pgtap'
) AS id;

-- Operatore non-SUPER_ADMIN, whitelistato sull'emittente della commessa.
CREATE TEMP TABLE tmp_op AS
SELECT id.auth_user_id AS user_id
  FROM anagrafiche.identita_digitali id
 WHERE id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND id.attivo = true
   AND NOT EXISTS (
       SELECT 1 FROM config.profili_accesso_bindings pab
       JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
       WHERE pab.identita_digitale_id = id.id
         AND pab.attivo = true
         AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso)
 ORDER BY id.id LIMIT 1;

CREATE TEMP TABLE tmp_ef AS
SELECT ef.id AS emittente_fiscale_id
  FROM anagrafiche.emittenti_fiscali ef
  JOIN vendite.commesse c ON c.id = (SELECT commessa_id FROM tmp_com2)
 WHERE ef.soggetto_ruolo_id = c.emittente_soggetto_ruolo_id
 LIMIT 1;

SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_op);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id)
SELECT (SELECT user_id FROM tmp_op), (SELECT emittente_fiscale_id FROM tmp_ef);

SELECT set_config('app.current_user_id', (SELECT user_id::text FROM tmp_op), true);

-- Annullo E: deve sparire dalla lista attivita, mentre F resta.
SELECT vendite.fn_annulla_commessa_attivita(
  (SELECT id FROM tmp_riga_e), 'annullata per test viste');

SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM vendite.vw_dash_competenza_attivita v
     WHERE v.commessa_attivita_id = (SELECT id FROM tmp_riga_e))
  AND EXISTS (
    SELECT 1 FROM vendite.vw_dash_competenza_attivita v
     WHERE v.commessa_attivita_id = (SELECT id FROM tmp_riga_f)),
  '24) [A6] la riga annullata sparisce da vw_dash_competenza_attivita, la sorella resta');

-- Il gruppo fatturabile degli oneri e' UNO per commessa (MAN:<commessa_id>):
-- finche' resta una riga viva il gruppo deve restare selezionabile.
SELECT is(
  (SELECT g.n_attivita::int FROM vendite.vw_dash_competenza_gruppi g
    WHERE g.commessa_id = (SELECT commessa_id FROM tmp_com2)
      AND g.gruppo_key = 'MAN:' || (SELECT commessa_id::text FROM tmp_com2)),
  1,
  '25) [A8] gruppo MAN: presente con la sola riga viva');

SELECT vendite.fn_annulla_commessa_attivita(
  (SELECT id FROM tmp_riga_f), 'annullata anche la seconda');

-- Con tutte le righe annullate il gruppo non deve piu' esistere: altrimenti
-- resterebbe a video un gruppo fatturabile selezionabile che non produce nulla.
SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM vendite.vw_dash_competenza_gruppi g
     WHERE g.commessa_id = (SELECT commessa_id FROM tmp_com2)
       AND g.gruppo_key = 'MAN:' || (SELECT commessa_id::text FROM tmp_com2)),
  '26) [A8] gruppo MAN: assente quando tutte le righe sono annullate');

-- ============================================================
-- 26 [A9] i contatori di testata (changeset D3)
-- ============================================================
-- com2 ha due righe, entrambe annullate: il funnel deve mostrare zero
-- approvate e zero non emesse, mentre il totale fisico resta 2 (le righe
-- esistono, e il totale non deve mentire sull'esistenza).
SELECT ok(
  (SELECT s.total_attivita = 2
      AND s.total_approvate = 0
      AND s.total_non_emesse = 0
     FROM vendite.fn_get_commessa_stato((SELECT commessa_id FROM tmp_com2)) s),
  '27) [A9] contatori: approvate/non_emesse escludono le annullate, il totale no');

SELECT set_config('app.current_user_id', '', true);

SELECT * FROM finish();
ROLLBACK;
