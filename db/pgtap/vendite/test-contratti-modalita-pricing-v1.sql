-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-26 (brief-modello-documento-vendita §11): il contratto ha la porta sulla colonna di
--   stato (E_DOC_STATO_SOLO_DAL_VERBO). L'attivazione del setup del test 4 passa dalla fixture
--   dbops.fn_pgtap_porta_a_stato (il verbo, con emetti_contratto concessa); prima un UPDATE
--   diretto dello stato. Stessi esiti attesi.
-- pgTAP test per Zero ERP
--
-- Test: contratti — combinazioni listino/variazione globale (modello unificato).
--       Aggiornato per Fase 2 refactor contratti (20260515-10):
--       i vecchi test 3-7 sui CHECK/trigger modalità A/B/C rimossi
--       (chk_contratti_modalita_pricing, chk_contratti_variazione_globale_coerente,
--        trg_contratti_a10_guard_modalita_c_activation_ins_upd,
--        trg_contratti_righe_a10_guard_modalita_c_ins_upd droppati).
--
-- Indice test (1..4):
--   1) listino + variazione globale in DRAFT -> ok
--   2) listino NULL + variazione NULL in DRAFT -> ok
--   3) Contratto con listino, in DRAFT: riga di ESCLUSIONE senza prezzo ammessa
--   4) Contratto ATTIVO: inserimento di riga vietato (pricing immutabile)
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

SELECT plan(4);

-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.6.5): il
--   cliente e il billing account sono COSTRUITI (dbops.fn_pgtap_crea_cliente_ba),
--   come il listino. Prima erano «il primo BA per id» del DB: su un database
--   ricostruito da zero (CI) non c'e' nessun BA e il file era nel registro dei
--   rossi di CI per questo.
CREATE TEMP TABLE tmp_ctx_ba AS
SELECT billing_account_id, istanza_utility_id, utility_id
  FROM dbops.fn_pgtap_crea_cliente_ba(
    'modalita pricing',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_ctx_stato_draft AS
SELECT id AS stato_id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT';

CREATE TEMP TABLE tmp_ctx_stato_attivo AS
SELECT id AS stato_id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO';

-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.1.2, A-D2): il
--   listino e' COSTRUITO, con una versione valida da oggi. Prima era «il primo
--   listino attivo per id» del DB: il test 4 lo attiva, e da quel giorno un
--   contratto con un listino senza versione in vigore non si attiva piu'. Con un
--   listino preso dai dati l'esito dipendeva da cosa c'era sulla macchina.
CREATE TEMP TABLE tmp_ctx_listino AS
SELECT listino_id, listino_versione_id FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_ctx_ba), 'modalita pricing');

-- ⛔ rev 2026-10-13 (brief-db-articoli-ammessi-per-documento, Lotto 3b, A-5):
--   l'articolo si COSTRUISCE e sta nel listino. Prima era il primo del catalogo,
--   fuori dal listino del contratto: un'ESCLUSIONE di un articolo che il listino
--   non ha non esclude niente, e dal Lotto 3b e' rifiutata.
--   ⚠️ Due istruzioni: la riga che il builder scrive non e' visibile alla JOIN
--   della stessa istruzione (lo snapshot e' preso prima), e la tabella
--   nascerebbe vuota — col test 3 verde per sottrazione (zero righe inserite).
CREATE TEMP TABLE tmp_ctx_articolo AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-MOD-PRICING', false) AS articolo_id;
SELECT dbops.fn_pgtap_listino_aggiungi_articoli(
    (SELECT listino_versione_id FROM tmp_ctx_listino), ARRAY[(SELECT articolo_id FROM tmp_ctx_articolo)]);

-- 1) listino + variazione globale in DRAFT -> ok
SELECT lives_ok(
    $$INSERT INTO vendite.contratti(
          numero, billing_account_id, istanza_utility_id, utility_id, stato_doc_contratto_id,
          valido_dal, valido_al, listino_id, tipo_variazione_globale, valore_variazione_globale)
      SELECT 'PGTAP_CONTR_A', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
             sd.stato_id, '2050-01-01', '2050-12-31',
             l.listino_id, 'PERCENTUALE', -10
        FROM tmp_ctx_ba ba, tmp_ctx_stato_draft sd, tmp_ctx_listino l$$,
    '1) listino + variazione globale in DRAFT ammessa'
);

-- 2) listino NULL + variazione NULL in DRAFT -> ok (ex-modalita'' C)
SELECT lives_ok(
    $$INSERT INTO vendite.contratti(
          numero, billing_account_id, istanza_utility_id, utility_id, stato_doc_contratto_id,
          valido_dal, valido_al, listino_id, tipo_variazione_globale, valore_variazione_globale)
      SELECT 'PGTAP_CONTR_C', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
             sd.stato_id, '2051-01-01', '2051-12-31',
             NULL, NULL, NULL
        FROM tmp_ctx_ba ba, tmp_ctx_stato_draft sd$$,
    '2) listino NULL + variazione NULL in DRAFT ammessa'
);

-- 🔴 RIORDINATO IL 2026-08-18.
--   Il test 3 falliva con E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE, e non
--   perche' la proprieta' che verifica sia venuta meno: perche' il SETUP
--   attivava il contratto prima di inserire la riga, e
--   `trg_contratti_righe_a05_doc_righe_lock_fuori_bozza` (Step 2.3) vieta
--   INSERT/UPDATE/DELETE su `contratti_righe` quando il padre e' ATTIVO.
--
--   ⚠️ Quell'attivazione era un residuo: serviva al guard «modalita' C
--   activation», che la Fase 2 ha DROPPATO (vedi la testata di questo file).
--   Restava li' a fare da setup di un guard che non esiste piu', ed e' andata a
--   sbattere contro uno che nel frattempo e' nato.
--
--   ⚠️ E sotto ce n'era una seconda, che si e' vista solo togliendo la prima:
--   `contratti_righe.tipo_eccezione` e' NOT NULL, e il CHECK
--   `chk_contrighe_prezzo_per_tipo_eccezione` detta la regola vera —
--
--       ESCLUSIONE            -> prezzo_unitario **deve** essere NULL
--       OVERRIDE | AGGIUNTA   -> prezzo_unitario **deve** essere valorizzato
--
--   cioe' «riga senza prezzo perche' il prezzo lo mette il listino» non e' piu'
--   un caso di questo modello: `contratti_righe` e' diventata la tabella delle
--   ECCEZIONI a un listino, non l'elenco delle righe con prezzo facoltativo. La
--   proprieta' del titolo, presa alla lettera, oggi e' FALSA.
--
--   Quello che resta vero, e che il test ora verifica, e' *quando* una riga
--   senza prezzo e' ammessa: come ESCLUSIONE, e solo in DRAFT. E l'attivazione,
--   invece di essere buttata, diventa il test 4 e copre la regola NUOVA — dopo
--   l'attivazione il pricing e' immutabile — che fin qui nessuno guardava e che
--   si era fatta notare solo rompendo questo file.

-- 3) Contratto con listino, in DRAFT: riga di ESCLUSIONE senza prezzo ammessa
--    rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende): l'esclusione
--    nasce vuota; la qta_operativa 1 di prima e' un dato di vendita, ora rifiutato.
SELECT lives_ok(
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione,
                                          prezzo_unitario, attivo)
      SELECT c.id, a.articolo_id, 'ESCLUSIONE'::vendite.tipo_eccezione_contratto,
             NULL, TRUE
        FROM vendite.contratti c, tmp_ctx_articolo a
       WHERE c.numero = 'PGTAP_CONTR_A'$$,
    '3) Contratto con listino in DRAFT: riga di ESCLUSIONE senza prezzo ammessa'
);

-- Ora si attiva il contratto: da qui in poi il pricing e' congelato.
-- rev 2026-10-26 (§11): dalla fixture degli stati (il verbo), non con un UPDATE.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, c.id, 'ATTIVO')
  FROM vendite.contratti c
 WHERE c.numero = 'PGTAP_CONTR_A';

-- 4) Dopo l'attivazione, le righe sono bloccate
--    ⚠️ Lo SQLSTATE si passa: `throws_ok` senza accetta QUALUNQUE errore, e qui
--    l'INSERT ha molti modi di fallire che non c'entrano col lock.
SELECT throws_ok(
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione,
                                          prezzo_unitario, attivo)
      SELECT c.id, a.articolo_id, 'ESCLUSIONE'::vendite.tipo_eccezione_contratto,
             NULL, TRUE
        FROM vendite.contratti c, tmp_ctx_articolo a
       WHERE c.numero = 'PGTAP_CONTR_A'$$,
    'P0001',
    NULL,
    '4) Contratto ATTIVO: inserimento di riga vietato (pricing immutabile post-attivazione)'
);

SELECT * FROM finish();
ROLLBACK;
