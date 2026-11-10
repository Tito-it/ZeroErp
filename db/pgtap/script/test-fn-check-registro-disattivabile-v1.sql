-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture CREA un registro di numerazione e ne fa
--   girare il contatore — dato di configurazione, non di operatore — e la
--   funzione sotto esame legge vendite.fatture e pagamenti.vendite_contabili,
--   che hanno la RLS. Da dentro un perimetro il conteggio dei documenti
--   sarebbe parziale e la check risponderebbe «si puo' disattivare» proprio
--   nel caso da bloccare. E la distinta del test 7 si inserisce senza operatore
--   in sessione: da app il guard di scope la rifiuterebbe.
-- pgtap-contesto: escluso — discende dal marcatore qui sopra.
-- pgTAP test per Zero ERP
-- Test: script.fn_check_registro_disattivabile  (20260831-38)
--       Richiesta: brief-db-richieste-aperte-dal-backend-2, voce 2
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2c/2d): la famiglia della bolla e' DDT_VENDITA.
-- ------------------------------------------------------------
-- Elenco test (plan 9):
-- 1) ⭐ Un registro SENZA figli: la check risponde []
-- 2) ⭐ ...e la disattivazione passa davvero (il gemello positivo)
-- 3) ⛔ Con un progressivo vivo: la check nomina HA_PROGRESSIVI
-- 4) ⛔ ...e la disattivazione viene rifiutata (P0001)
-- 5) ⭐ La check e il rifiuto dicono LA STESSA COSA
-- 6) ⭐⭐ STRUTTURALE: la check copre TUTTI i guard montati
-- 7) ⭐ Con una DISTINTA collegata: HA_DISTINTE arriva DOPO HA_PROGRESSIVI
--       (l'ordine e' quello dei trigger, e la figlia e' di un ALTRO schema)
-- 8) ⛔ Spento il contatore, resta la distinta: la check nomina solo HA_DISTINTE
-- 9) ⭐ ...e il rifiuto e' E_ATTIVO_BLOCK_CHILDREN_EXIST, come il motivo della check
--
-- Scopo:
--   ⛔ Su vendite.registri_fatturazione i guard di disattivazione sono OTTO, ed
--   erano TRE fino al 2026-08-31: col trasloco vendite.ddt, ordini e resi hanno
--   guadagnato `registro_id`, e l'automazione ha montato il guard DA SOLA a
--   partire dalla FK — a ci_apply, senza annunciarlo. Poi `commesse` (02-09) e
--   `pagamenti.vendite_contabili` (17-09, la distinta numerata sul registro:
--   la PRIMA figlia fuori dallo schema vendite).
--   ⚠️ Quello che sorprende resta il contatore: un registro che ha numerato
--   anche UN SOLO documento ha una riga di progressivi viva, quindi non si
--   spegne piu'. Il cestino e' percio' quasi sempre indisponibile — e senza un
--   motivo a video l'operatore lo scopre premendo.
--
--   ⭐ IL TEST 2 SERVE QUANTO IL 4: senza il gemello positivo, una check che
--   rispondesse «bloccato» SEMPRE passerebbe il 3 e il 4 esattamente come
--   quella giusta. E' la differenza fra «rifiuta il caso giusto» e «rifiuta
--   tutto».
--
--   ⭐⭐ IL TEST 6 E' IL PRESIDIO CHE CONTA, ed e' al posto di quello che il
--   §12.5.2 chiederebbe. La regola sarebbe «la madre CHIAMA la check», ma qui
--   una madre NON ESISTE: a rifiutare e'
--   dbops.trgfn_prevent_deactivate_if_children, un trigger GENERICO guidato da
--   TG_ARGV e condiviso da tutto il database — farlo chiamare una check
--   specifica dei registri ne romperebbe la genericita' per un caso solo.
--   ⇒ Quello che si puo' presidiare e' l'altra meta': che la check non resti
--   INDIETRO rispetto ai guard. Il test 6 legge da `pg_trigger` quali tabelle
--   figlie bloccano davvero la disattivazione, e le confronta con quelle che la
--   check copre. Il giorno che ne compare una in piu', diventa rosso — invece di
--   lasciare la check a spegnere un cestino che il trigger poi rifiuta.
--
-- ⚠️ COSA QUESTO FILE NON PROVA: la frase tradotta. Le OTTO `reason_key` sono un
--   debito verso il FE (§12.3) e le presidia scripts/check_i18n_keys.py — al
--   2026-09-18 `ha_distinte` nei locales non c'e' ancora.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- Fixture: un'azienda NUOVA, e su di lei un registro senza figli
-- ============================================================
-- ⭐ IL MONDO SI COSTRUISCE, NON SI CERCA (rev 2026-09-18). Fino a oggi la
--   fixture pescava «un registro DDT per tutte le utility» fra quelli
--   ESISTENTI: su dbdev c'e', su un database ricostruito dai changelog
--   (`zeroerp_ci`) ce ne sono ZERO — la CTE usciva vuota, ogni asserzione
--   confrontava NULL e il file stava in `baseline-rossi-ci.tsv` come
--   ERRORE_FIXTURE. Cioe' il test 6 — il presidio che conta — era MUTO
--   proprio nell'unico posto in cui il guard nasce da zero (ci_apply).
--   `dbops.fn_pgtap_crea_emittente()` fa nascere l'azienda E i suoi registri
--   (trgfn_emittenti_fiscali_provision_registri), quindi il resto della
--   fixture non cambia. Basta il BB nudo, senza operatore: qui si gira da
--   owner e nessun test guarda attraverso un perimetro.
CREATE TEMP TABLE tmp_crd_ef AS
SELECT * FROM dbops.fn_pgtap_crea_emittente();

-- ⚠️ Si nasce su una `utility_id` valorizzata, e non e' un dettaglio:
--   uq_registri_fatturazione_famiglia_emittente_utility occupa lo slot
--   (famiglia, emittente, utility) e quello «per tutte le utility» e' gia'
--   preso dal provisioning — anche sull'azienda appena nata. ⛔ E lo slot NON
--   si libera spegnendo il registro che c'e': quell'indice non filtra su
--   `attivo`.
CREATE TEMP TABLE tmp_crd AS
WITH ins AS (
  INSERT INTO vendite.registri_fatturazione (
      codice, descrizione, emittente_soggetto_ruolo_id,
      famiglia_documento, reset_policy, attivo, utility_id)
  SELECT 'CRD-' || ef.soggetto_ruolo_id::text,
         'Registro pgTAP check disattivabile',
         ef.soggetto_ruolo_id, 'DDT_VENDITA', 'ANNUALE', true,
         (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1)
    FROM tmp_crd_ef ef
  RETURNING id, emittente_soggetto_ruolo_id
)
SELECT id AS registro_id, emittente_soggetto_ruolo_id AS emittente_sr FROM ins;

-- ============================================================
-- 1/2) ⭐ Senza figli: la check tace, e la disattivazione passa
-- ============================================================
SELECT is(
    (SELECT script.fn_check_registro_disattivabile(t.registro_id) FROM tmp_crd t),
    '[]'::jsonb,
    '1) Un registro senza figli: nessun motivo, il cestino resta acceso');

SELECT lives_ok(
    format('UPDATE vendite.registri_fatturazione SET attivo = false WHERE id = %s',
           (SELECT registro_id FROM tmp_crd)),
    '2) ...e la disattivazione passa davvero');

-- ⚠️ Si riaccende: i test successivi hanno bisogno di un registro vivo, e un
--   registro spento non e' il caso in esame.
UPDATE vendite.registri_fatturazione
   SET attivo = true
 WHERE id = (SELECT registro_id FROM tmp_crd);

-- ============================================================
-- 3/4/5) ⛔ Con un progressivo vivo
-- ============================================================
-- ⭐ Il contatore si fa girare dal MOTORE, non inserendo a mano una riga in
--   registri_fatturazione_progressivi: cosi' il test prova il caso che capita
--   davvero — «e' bastato numerare un documento».
-- ⚠️ Verbo in un'istruzione separata dall'asserzione: fn_get_next_progressivo
--   scrive.
CREATE TEMP TABLE tmp_crd_num AS
SELECT vendite.fn_get_next_progressivo(
           (SELECT registro_id FROM tmp_crd),
           DATE '2101-06-15', NULL, '', NULL, 'DDT_VENDITA') AS numero;

SELECT is(
    (SELECT string_agg(m ->> 'reason', ',' ORDER BY m ->> 'reason')
       FROM tmp_crd t,
            LATERAL jsonb_array_elements(
                script.fn_check_registro_disattivabile(t.registro_id)) m),
    'HA_PROGRESSIVI',
    '3) Con un progressivo vivo la check nomina HA_PROGRESSIVI, e solo quello');

PREPARE crd_disattiva AS
UPDATE vendite.registri_fatturazione SET attivo = false
 WHERE id = (SELECT registro_id FROM tmp_crd);

SELECT throws_ok(
    'EXECUTE crd_disattiva',
    'P0001',
    NULL,
    '4) ...e la disattivazione viene rifiutata');

-- ⭐ Il punto: il tooltip e il rifiuto devono dire LA STESSA COSA. Il rifiuto porta la
--   frase del codice che il primo motivo della check nomina. La frase non nomina
--   tabelle (brief-db-revisione-dbops, S-BE-1): quale figlia blocca lo dice la
--   reason del motivo, e nel rifiuto il contesto del diario.
SELECT throws_ok(
    'EXECUTE crd_disattiva',
    'P0001',
    (SELECT me.messaggio
       FROM tmp_crd t
       CROSS JOIN LATERAL script.fn_check_registro_disattivabile(t.registro_id) c(motivi)
       JOIN config.messaggi_errore me ON me.codice = c.motivi -> 0 ->> 'codice' AND me.lingua = 'it'),
    '5) Il rifiuto porta la frase del codice che il primo motivo della check nomina');

-- ============================================================
-- 6) ⭐⭐ La check copre TUTTI i guard montati — derivato da pg_trigger
-- ============================================================
-- ⛔ E' il presidio che sostituisce quello del §12.5.2, qui inapplicabile: a
--   rifiutare e' un trigger generico, non una madre di dominio. Quello che si
--   puo' garantire e' che la check non resti INDIETRO.
-- ⚠️ Le figlie si leggono dal SECONDO argomento di
--   dbops.trgfn_prevent_deactivate_if_children, che e' il nome della tabella
--   figlia. Se ne comparisse un'ottava, questa riga diventa rossa.
--
-- ⭐ ED E' GIA' SUCCESSO, il 2026-09-02: `vendite.commesse` ha guadagnato
--   `registro_id` (changeSet 20260902-07) e l'automazione ATTIVO ha montato il
--   SETTIMO guard da sola, al migrate. Questa riga e' diventata rossa PRIMA
--   che qualcuno premesse un cestino — che e' tutto il punto. La check ha
--   imparato il motivo con 20260902-12.
-- ⭐ E RIACCADUTO il 2026-09-18: `pagamenti.vendite_contabili` — la distinta
--   di incasso — ha guadagnato `registro_id` col 20260915-21 (numerazione
--   DIS-<SIGLA>-<ANNO>-<N>), e a ci_apply l'automazione ha montato l'OTTAVO
--   guard. Il brief lo aveva previsto (P-1), la conseguenza sulla check no: a
--   dirla e' stata questa riga. La check ha imparato il motivo con 20260918-05.
--   ⚠️ E' la prima figlia di un ALTRO schema: la regexp qui sotto legge solo
--   il NOME della tabella (secondo argomento), quindi l'elenco non porta lo
--   schema — lo schema lo prova il test 9, sulla frase del rifiuto.
-- ⛔ E QUANDO RIACCADE: si aggiunge il motivo alla check, POI si aggiorna
--   l'elenco atteso. Aggiornare solo questa riga farebbe tacere il presidio
--   invece di rispondergli, e lascerebbe il cestino acceso su un registro che
--   il trigger rifiuta.
SELECT is(
    (SELECT string_agg(DISTINCT x.figlia, ',' ORDER BY x.figlia)
       FROM pg_trigger t
       JOIN pg_class     c ON c.oid = t.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
       CROSS JOIN LATERAL (
           SELECT (regexp_match(pg_get_triggerdef(t.oid),
                                '''[^'']+''\s*,\s*''([^'']+)''')) [1] AS figlia) x
      WHERE NOT t.tgisinternal
        AND n.nspname = 'vendite'
        AND c.relname = 'registri_fatturazione'
        AND pg_get_triggerdef(t.oid) LIKE '%prevent_deactivate_if_children%'),
    'commesse,ddt,fatture,ordini,registri_fatturazione_progressivi,resi,tipi_doc_fiscale_registri,vendite_contabili',
    '6) I guard di disattivazione montati sono esattamente quelli che la check copre');

-- ============================================================
-- 7/8/9) ⭐ L'ottavo guard, COSTRUITO: una distinta sul registro
-- ============================================================
-- ⛔ Il test 6 dice che la check COPRE la figlia; questi tre dicono che la
--   copre BENE: il ramo giusto (_EXIST, la distinta non ha `attivo`),
--   l'ordine giusto (dopo i progressivi: `v` > `r`), e la frase giusta (con
--   lo schema `pagamenti.`, che e' l'unica cosa nuova rispetto alle sette
--   sorelle di `vendite`). Un motivo aggiunto con lo schema sbagliato
--   passerebbe il test 6 e farebbe divergere tooltip e rifiuto sul nome.
-- ⚠️ La distinta si inserisce con un `codice` FORNITO: cosi'
--   trgfn_vendite_contabili_gen_codice e' un no-op (non numera, non tocca
--   registro_id) e `registro_id` lo scriviamo noi sul registro della fixture,
--   che e' di famiglia DDT — la FK e il guard guardano l'id, non la famiglia.
--   L'emittente e' quello del registro (livello 1 di fn_get_emittente_distinta:
--   fornito e coerente), nessun canale, un centro di riscossione attivo
--   qualunque (il guard centro/canale scatta solo con un canale).
-- ⚠️ Runner owner senza contesto: trgfn_guard_emittente_scope non scatta
--   (row_security_active e' falso per il proprietario senza FORCE) — e' il
--   motivo dichiarato in testa per cui questo file resta su owner.
CREATE TEMP TABLE tmp_crd_dist AS
WITH ins AS (
  INSERT INTO pagamenti.vendite_contabili (
      codice, registro_id, emittente_soggetto_ruolo_id, centro_riscossione_id,
      data_contabile, data_registrazione, origine)
  SELECT 'PGTAP-CRD-DIS-' || t.registro_id::text,
         t.registro_id, t.emittente_sr,
         (SELECT c.id FROM pagamenti.centri_riscossione c
           WHERE c.attivo ORDER BY c.id LIMIT 1),
         DATE '2101-06-15', DATE '2101-06-15', 'MANUALE'
    FROM tmp_crd t
  RETURNING id
)
SELECT id AS contabile_id FROM ins;

-- ⭐ Qui si legge l'ORDINE DELL'ARRAY, non quello alfabetico: e' il contratto
--   della check (la superficie mostra il primo), e deve coincidere con
--   l'ordine di scatto dei trigger — progressivi prima della distinta.
SELECT is(
    (SELECT string_agg(m.value ->> 'reason', ',' ORDER BY m.ordinality)
       FROM tmp_crd t,
            LATERAL jsonb_array_elements(
                script.fn_check_registro_disattivabile(t.registro_id))
                WITH ORDINALITY AS m),
    'HA_PROGRESSIVI,HA_DISTINTE',
    '7) Con una distinta collegata la check nomina anche HA_DISTINTE, DOPO i progressivi');

-- ⭐ Spegnere il contatore e' lecito («figli prima, padre poi»), e isola
--   l'ottavo guard: da qui in avanti a bloccare e' SOLO la distinta.
UPDATE vendite.registri_fatturazione_progressivi
   SET attivo = false
 WHERE registro_id = (SELECT registro_id FROM tmp_crd);

SELECT is(
    (SELECT string_agg(m ->> 'reason', ',' ORDER BY m ->> 'reason')
       FROM tmp_crd t,
            LATERAL jsonb_array_elements(
                script.fn_check_registro_disattivabile(t.registro_id)) m),
    'HA_DISTINTE',
    '8) Spento il contatore, la check nomina HA_DISTINTE e solo quello');

-- ⭐ La prima figlia fuori da vendite (pagamenti.vendite_contabili, senza colonna
--   attivo): il rifiuto e' quello del ramo dell'esistenza, lo stesso codice della check.
SELECT throws_ok(
    'EXECUTE crd_disattiva',
    'P0001',
    (SELECT me.messaggio FROM config.messaggi_errore me
      WHERE me.codice = 'E_ATTIVO_BLOCK_CHILDREN_EXIST' AND me.lingua = 'it'),
    '9) ...e il rifiuto e'' E_ATTIVO_BLOCK_CHILDREN_EXIST, come il motivo HA_DISTINTE della check');

SELECT * FROM finish();
ROLLBACK;
