-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-11-07 (brief-db-sorgente-documento-e-riga, giro T.5, 20261106-96): documento_origine_* e
--   uq_ordini_v_documento_origine_offerta sono ritirati. Gli ordini della fixture e dei test 14-15
--   scrivono la sola provenienza (sorgente_*), come i verbi; il 14 sbatte su uq_ordini_v_sorgente_offerta,
--   il 15 cita un preventivo vero (il guard unico vuole un documento che esiste: prima bastava un id
--   inventato nella colonna parallela, polimorfa e senza FK). Attese invariate.
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2b, 20261019-87 … -99):
--   l'ordine nato dall'offerta porta documento_origine_tipo = OFFERTA_COMMERCIALE, il
--   codice della sorgente (era OFFERTA: ora la FK verso config.sorgenti lo rifiuta).
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): le offerte nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima nascevano
--   gia' ACCETTATA o RIFIUTATA).
-- ⚠️ rev 2026-10-21 (brief-db-offerta-emissione-ed-erogazione §H.3 H-R3, 20261021-58):
--   da ACCETTATA si esce anche annullando (transizione ACCETTATA->ANNULLATA). I test 8
--   e 12 non vedono piu' available_actions=[]: c'e' «annulla», SPENTA col motivo
--   DOCUMENTI_VIVI perche' l'offerta vive nel contratto o nell'ordine generato.
-- rev 2026-10-26 (brief-modello-documento-vendita §13, giro 9): lo slot EMESSA dal verbo
--   (dbops.fn_pgtap_porta_a_stato), non con un UPDATE diretto dello stato: la porta lo rifiuta.
--   emetti_offerta concessa in testa, esplicita: la capability nasconde «Emetti» da BOZZA e
--   «Annulla» da ACCETTATA a chi non ha il permesso. Nessuna attesa cambiata.
-- pgTAP test per Zero ERP
-- Test: script.fn_available_actions_offerta — capability layer offerte commerciali
-- ------------------------------------------------------------
-- Indice test (1..15):
--  1) Offerta inesistente → NULL
--  2) BOZZA: available_actions ha 2 azioni (emetti + annulla)
--  3) BOZZA: can_edit_testata=true, can_push_contratto=false, non_editable_fields lista corta
--  4) EMESSA: available_actions ha 3 azioni (accetta + rifiuta + crea_revisione)
--  5) EMESSA: can_edit_testata=true (le note), listino e cliente non modificabili, can_create_revisione=true
--  6) EMESSA: azione rifiuta ha requires_motivazione=true (verifica meta update 20260526-01)
--  7) ACCETTATA senza contratto ne' ordine: can_push_contratto=true, push_contratto presente
--  8) ACCETTATA con contratto generato (mutua esclusivita'): can_push_contratto=false
--     E can_genera_ordine=false, entrambi reason='OFFERTA_CONTRATTO_GIA_GENERATO',
--     push_contratto E genera_ordine assenti; available_actions = [annulla SPENTA,
--     reason DOCUMENTI_VIVI] (rev 2026-10-21)
--  9) Terminale (RIFIUTATA): available_actions=[], can_edit_testata=false,
--     can_push_contratto=false, non_editable_fields lista lunga
-- 10) Tutte le label_key in available_actions iniziano per 'vendite.offerte.'
-- 11) ACCETTATA senza ordine ne' contratto: can_genera_ordine=true, reason null, genera_ordine presente
-- 12) ACCETTATA con ordine generato (mutua esclusivita'): can_genera_ordine=false
--     E can_push_contratto=false, entrambi reason='OFFERTA_ORDINE_GIA_GENERATO',
--     genera_ordine E push_contratto assenti; available_actions = [annulla SPENTA,
--     reason DOCUMENTI_VIVI] (rev 2026-10-21)
-- 13) non ACCETTATA (BOZZA): can_genera_ordine=false, reason='OFFERTA_NON_ACCETTATA'
-- 14) Indice: secondo ordine dalla stessa offerta (provenienza) viola uq_ordini_v_sorgente_offerta
-- 15) Indice: due ordini ('PREVENTIVO', Y) consentiti (indice non li vincola)
-- 16a/16b) BOZZA senza listino_versione_id su un listino con una versione in
--     vigore: azione verso EMESSA ACCESA, nessun motivo. ⚠️ Rev 2026-10-07
--     (brief-db-offerta-emissione-ed-erogazione §C.1.3): fino a quel giorno qui
--     si pretendeva enabled=false + LISTINO_VERSIONE_MANCANTE, cioe' il test
--     pinnava il difetto — la versione si congela ALL'emissione, e il pulsante
--     non ci arrivava mai. Il caso «listino senza versione in vigore» sta in
--     vendite/offerte_commerciali/test-offerta-emissione-congela-listino-v1.
-- 17) BOZZA con versione ATTIVA: azione verso EMESSA enabled=true
-- 19) Tutte le reason_key di push_contratto/genera_ordine iniziano per
--     'vendite.offerte.' (guard namespace i18n, 20260719-13)
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

SELECT plan(19);

-- ============================================================
-- Setup fixture: contesti di riferimento
-- (stesso approccio del test state_machine: BA senza tipi_utenze
--  per evitare guard tipo/classe sui contratti_utilities al push)
-- ============================================================
-- ⛔ L'EMITTENTE NON SI PESCA, SI DERIVA (2026-09-23, guida pgTAP §5). Con
--   una sola azienda a catalogo «il primo emittente attivo» e quello di chi
--   agisce coincidevano per caso; su un database ricostruito il mondo se lo
--   costruisce la riga di contesto, e il primo per id e' un ALTRO — da cui
--   «Accesso negato per scope emittente fiscale».
-- ⛔ rev 2026-09-23 (brief-db-fixture-che-costruiscono-giro-2, lotto 2).
--   BA, listino e versione ATTIVA si PESCAVANO («il primo BA la cui utility
--   non e' un'utenza», «il primo listino attivo», «la prima versione
--   ATTIVA» — tre sotto-select indipendenti, e listino e versione nemmeno
--   legati fra loro), e l'ordine prendeva «il primo soggetto_ruolo». Su un
--   database ricostruito (la CI) non c'e' niente di tutto questo e il file
--   moriva al primo INSERT (billing_account_id NULL) con zero asserzioni.
--   Ora: il cliente su una utility che non e' un'utenza (il criterio di
--   prima, diventato una precondizione COSTRUITA) viene da
--   dbops.fn_pgtap_crea_cliente_ba — con il contesto aperto il BA e' legato
--   all'emittente di chi agisce — e il listino con la sua versione ATTIVA
--   da dbops.fn_pgtap_crea_listino (20260923-50), sulla stessa utility.
--   ⛔ Cio' che i builder scrivono si legge in un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_aa_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'available actions offerta',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_aa_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_aa_cli), 'available actions offerta');

CREATE TEMP TABLE tmp_aa_ctx AS
SELECT
    (SELECT billing_account_id FROM tmp_aa_cli) AS billing_account_id,
    (SELECT istanza_utility_id FROM tmp_aa_cli) AS istanza_utility_id,
    (SELECT utility_id FROM tmp_aa_cli) AS utility_id,
    script.fn_pgtap_emittente_operatore() AS emittente_fiscale_id,
    (SELECT listino_id FROM tmp_aa_listino) AS listino_id,
    (SELECT listino_versione_id FROM tmp_aa_listino) AS listino_versione_id_attiva,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')     AS stato_bozza_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'EMESSA')    AS stato_emessa_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'ACCETTATA') AS stato_accettata_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'RIFIUTATA') AS stato_rifiutata_id;

-- GUC vuota: gli INSERT su vendite.ordini (test 11-15) superano i guard
-- emittente/scope senza restrizione (stesso approccio del test fn_aa_ordine).
-- ⛔ 2026-09-04 — QUI IL TEST SPEGNEVA IL GUARD, e adesso non piu'.
--   La riga rimossa era `set_config('app.current_user_id', '', true)`: senza
--   utente in sessione `script.trgfn_guard_emittente_scope` usciva subito con
--   RETURN NEW, e le fixture entravano senza che nessuno guardasse l'emittente.
--   La fase 6 di `brief-db-processi-automatici-identita-e-perimetro` chiude quel
--   ramo — una sessione applicativa senza utente non scrive piu'.
--   ⇒ Il contesto operatore del preambolo RESTA valido per tutto il file, e le
--     fixture prendono l'emittente su cui quell'operatore puo' davvero scrivere
--     (`script.fn_pgtap_emittente_operatore()`).
--   ⭐ Non e' una riparazione di comodo: prima questo file collaudava il
--     comportamento di una porta aperta, adesso attraversa il guard come lo
--     attraversa l'applicazione.

-- Riferimenti per creare ordini reali (test genera_ordine + indice).
-- BA=NULL + emittente esplicito = niente guard emittente<->BA da soddisfare.
CREATE TEMP TABLE tmp_aa_ord AS
SELECT
    -- Il ruolo dell'ordine e' quello del cliente costruito, non «il primo».
    (SELECT soggetto_ruolo_id FROM tmp_aa_cli) AS soggetto_ruolo_id,
    (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'DRAFT' AND attivo IS TRUE LIMIT 1) AS stato_draft_ordine_id,
    (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
    (SELECT emittente_fiscale_id FROM tmp_aa_ctx) AS emittente_fiscale_id;

-- ⚠️ rev 2026-10-26 (giro 9): la capability nasconde il passaggio senza il suo
--   permesso (permesso => nascondi). «Emetti» da BOZZA (test 2, 16, 17) e
--   «Annulla» da ACCETTATA (test 8, 12) vogliono emetti_offerta: la si concede
--   all'utente del contesto, esplicita. Il file prova i motivi di stato, non il
--   permesso (lo concederebbe comunque dbops.fn_pgtap_porta_a_stato, piu' sotto).
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'emetti_offerta');

-- Tabella di appoggio: slot -> offerta_id
CREATE TEMP TABLE tmp_aa_ids (
    slot       text PRIMARY KEY,
    offerta_id bigint
);

-- Slot BOZZA: offerta in BOZZA con listino_versione valorizzata (test 2-3)
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2082-01-01', ctx.stato_bozza_id
      FROM tmp_aa_ctx ctx
    RETURNING id
)
INSERT INTO tmp_aa_ids SELECT 'BOZZA', id FROM ins;

-- Slot EMESSA: BOZZA->EMESSA dal verbo, con la fixture (test 4-6). rev 2026-10-26:
--   prima un UPDATE diretto dello stato, che la porta dell'offerta ora rifiuta.
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2083-01-01', ctx.stato_bozza_id
      FROM tmp_aa_ctx ctx
    RETURNING id
)
INSERT INTO tmp_aa_ids SELECT 'EMESSA', id FROM ins;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', i.offerta_id, 'EMESSA')
  FROM tmp_aa_ids i
 WHERE i.slot = 'EMESSA';

-- Slot ACCT-1: ACCETTATA senza contratto (test 7). Nasce in BOZZA e
-- arriva ad ACCETTATA per la matrice (rev 2026-10-24).
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2084-01-01', ctx.stato_bozza_id
      FROM tmp_aa_ctx ctx
    RETURNING id
)
INSERT INTO tmp_aa_ids SELECT 'ACCT-1', id FROM ins;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', i.offerta_id, 'ACCETTATA')
  FROM tmp_aa_ids i
 WHERE i.slot = 'ACCT-1';

-- Slot ACCT-2: ACCETTATA per la matrice, poi fn_push genera il contratto (test 8)
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2085-01-01', ctx.stato_bozza_id
      FROM tmp_aa_ctx ctx
    RETURNING id
)
INSERT INTO tmp_aa_ids SELECT 'ACCT-2', id FROM ins;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', i.offerta_id, 'ACCETTATA')
  FROM tmp_aa_ids i
 WHERE i.slot = 'ACCT-2';

-- Genera il contratto da ACCT-2 tramite fn_push (p_pratica_id = NULL).
SELECT vendite.fn_push_offerta_a_contratto(
    (SELECT offerta_id FROM tmp_aa_ids WHERE slot = 'ACCT-2'),
    NULL
);

-- Slot RIFIUTATA: RIFIUTATA per la matrice (terminale, test 9)
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2086-01-01', ctx.stato_bozza_id
      FROM tmp_aa_ctx ctx
    RETURNING id
)
INSERT INTO tmp_aa_ids SELECT 'RIFIUTATA', id FROM ins;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', i.offerta_id, 'RIFIUTATA')
  FROM tmp_aa_ids i
 WHERE i.slot = 'RIFIUTATA';

-- Slot ACCT-ORD: ACCETTATA (per la matrice) con un ordine gia' generato
-- (la provenienza: OFFERTA_COMMERCIALE + uid) -> genera_ordine NON disponibile
-- (test 12) e secondo ordine bloccato dall'indice (test 14).
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2087-01-01', ctx.stato_bozza_id
      FROM tmp_aa_ctx ctx
    RETURNING id
)
INSERT INTO tmp_aa_ids SELECT 'ACCT-ORD', id FROM ins;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', i.offerta_id, 'ACCETTATA')
  FROM tmp_aa_ids i
 WHERE i.slot = 'ACCT-ORD';

-- Ordine collegato all'offerta ACCT-ORD (la provenienza: OFFERTA_COMMERCIALE + uid).
-- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-1/D-6): col BA del cliente, quello
--   dell'offerta da cui nasce. Prima nasceva col BA NULL.
INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
    stato_doc_ordine_id, valuta_id, data, storicizza,
    -- la provenienza, come la scrive il verbo (giro T.5 di brief-db-sorgente-documento-e-riga)
    sorgente_tipo_id, sorgente_uid
)
SELECT od.soggetto_ruolo_id, (SELECT c.billing_account_id FROM tmp_aa_cli c), od.emittente_fiscale_id,
       od.stato_draft_ordine_id, od.valuta_id, DATE '2087-01-02', false,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'OFFERTA_COMMERCIALE'),
       (SELECT o.uid FROM vendite.offerte_commerciali o
         WHERE o.id = (SELECT offerta_id FROM tmp_aa_ids WHERE slot = 'ACCT-ORD'))
  FROM tmp_aa_ord od;

-- ============================================================
-- TEST 1) Offerta inesistente → NULL
-- ============================================================
SELECT is(
    script.fn_available_actions_offerta(-1),
    NULL,
    '1) fn_available_actions_offerta(-1): offerta inesistente → NULL'
);

-- ============================================================
-- TEST 2) BOZZA: available_actions ha 2 azioni (emetti + annulla)
-- ============================================================
SELECT is(
    (SELECT jsonb_array_length(
                script.fn_available_actions_offerta(o.offerta_id)->'available_actions'
            )
       FROM tmp_aa_ids o WHERE o.slot = 'BOZZA'
    ),
    2,
    '2) BOZZA: available_actions ha 2 azioni (emetti + annulla)'
);

-- ============================================================
-- TEST 3) BOZZA: can_edit_testata=true, can_push=false, non_editable_fields lista corta
-- ============================================================
SELECT ok(
    (SELECT
         (script.fn_available_actions_offerta(o.offerta_id)->>'can_edit_testata')::boolean IS TRUE
         AND (script.fn_available_actions_offerta(o.offerta_id)->>'can_push_contratto')::boolean IS FALSE
         AND jsonb_array_length(
                 script.fn_available_actions_offerta(o.offerta_id)->'non_editable_fields'
             ) < 15
       FROM tmp_aa_ids o WHERE o.slot = 'BOZZA'
    ),
    '3) BOZZA: can_edit_testata=true, can_push_contratto=false, non_editable_fields lista corta'
);

-- ============================================================
-- TEST 4) EMESSA: available_actions ha 3 azioni (accetta + rifiuta + crea_revisione)
-- ============================================================
SELECT is(
    (SELECT jsonb_array_length(
                script.fn_available_actions_offerta(o.offerta_id)->'available_actions'
            )
       FROM tmp_aa_ids o WHERE o.slot = 'EMESSA'
    ),
    3,
    '4) EMESSA: available_actions ha 3 azioni (accetta + rifiuta + crea_revisione)'
);

-- ============================================================
-- TEST 5) EMESSA: can_edit_testata=true (le note), listino e cliente fermi
--   ⚠️ rev 2026-10-10 (brief-db-testata-dopo-emissione, fase 2, D-0/D-10):
--   can_edit_testata si legge dal montaggio del lock di testata e vuol dire
--   «in questo stato almeno un campo della testata si cambia» (le note, nei
--   documenti vivi). Che il documento non si RISCRIVA lo dice
--   non_editable_fields, che deve contenere identita' e condizioni.
-- ============================================================
SELECT ok(
    (SELECT
         (script.fn_available_actions_offerta(o.offerta_id)->>'can_edit_testata')::boolean IS TRUE
         AND (script.fn_available_actions_offerta(o.offerta_id)->'non_editable_fields') @> '["listino_id","billing_account_id","validita_al"]'
         AND NOT (script.fn_available_actions_offerta(o.offerta_id)->'non_editable_fields') @> '["meta"]'
         AND (script.fn_available_actions_offerta(o.offerta_id)->>'can_create_revisione')::boolean IS TRUE
       FROM tmp_aa_ids o WHERE o.slot = 'EMESSA'
    ),
    '5) EMESSA: can_edit_testata=true (le note), listino, cliente e validita'' non modificabili, can_create_revisione=true'
);

-- ============================================================
-- TEST 6) EMESSA: azione rifiuta ha requires_motivazione=true
--         Verifica che il meta update (20260526-01) sia applicato.
-- ============================================================
SELECT ok(
    (SELECT
         bool_or(
             (elem->>'key') = 'rifiuta'
             AND (elem->>'requires_motivazione')::boolean IS TRUE
         )
       FROM tmp_aa_ids o,
            jsonb_array_elements(
                script.fn_available_actions_offerta(o.offerta_id)->'available_actions'
            ) AS elem
      WHERE o.slot = 'EMESSA'
    ),
    '6) EMESSA: azione rifiuta ha requires_motivazione=true (verifica meta update 20260526-01)'
);

-- ============================================================
-- TEST 7) ACCETTATA senza contratto: can_push=true, push_contratto in available_actions
-- ============================================================
SELECT ok(
    (SELECT
         (script.fn_available_actions_offerta(o.offerta_id)->>'can_push_contratto')::boolean IS TRUE
         AND (script.fn_available_actions_offerta(o.offerta_id)->>'can_push_contratto_reason') IS NULL
         AND EXISTS (
             SELECT 1
               FROM jsonb_array_elements(
                        script.fn_available_actions_offerta(o.offerta_id)->'available_actions'
                    ) AS elem
              WHERE elem->>'key' = 'push_contratto'
         )
       FROM tmp_aa_ids o WHERE o.slot = 'ACCT-1'
    ),
    '7) ACCETTATA senza contratto: can_push_contratto=true, push_contratto in available_actions, reason=null'
);

-- ============================================================
-- TEST 8) ACCETTATA con contratto generato (mutua esclusivita'):
--         contratto presente, NESSUN ordine. push_contratto bloccato dal proprio
--         contratto; genera_ordine ANCHE bloccato (own-doc first -> reason del
--         contratto). Entrambe le azioni speciali assenti; l'unica transizione
--         manuale da ACCETTATA (annulla, rev 2026-10-21) e' SPENTA col motivo
--         DOCUMENTI_VIVI: l'offerta vive nel contratto.
-- ============================================================
SELECT ok(
    (SELECT
         -- push_contratto: bloccato dal contratto gia' generato
         (script.fn_available_actions_offerta(o.offerta_id)->>'can_push_contratto')::boolean IS FALSE
         AND (script.fn_available_actions_offerta(o.offerta_id)->>'can_push_contratto_reason')
             = 'OFFERTA_CONTRATTO_GIA_GENERATO'
         -- genera_ordine: ora ANCHE bloccato (mutua esclusivita'); reason = contratto
         AND (script.fn_available_actions_offerta(o.offerta_id)->>'can_genera_ordine')::boolean IS FALSE
         AND (script.fn_available_actions_offerta(o.offerta_id)->>'can_genera_ordine_reason')
             = 'OFFERTA_CONTRATTO_GIA_GENERATO'
         -- entrambe le azioni speciali assenti: resta solo annulla, SPENTA
         AND (SELECT jsonb_agg(jsonb_build_array(a->>'key', a->>'enabled', a->>'reason'))
                FROM jsonb_array_elements(
                         script.fn_available_actions_offerta(o.offerta_id)->'available_actions') a)
             = '[["annulla", "false", "DOCUMENTI_VIVI"]]'::jsonb
       FROM tmp_aa_ids o WHERE o.slot = 'ACCT-2'
    ),
    '8) ACCETTATA con contratto (mutua esclusivita): push E ordine bloccati, reason=OFFERTA_CONTRATTO_GIA_GENERATO, resta solo annulla spenta (DOCUMENTI_VIVI)'
);

-- ============================================================
-- TEST 9) Terminale (RIFIUTATA): 0 azioni, can_edit=false, can_push=false,
--         non_editable_fields lista lunga (tutti i campi bloccati)
-- ============================================================
SELECT ok(
    (SELECT
         jsonb_array_length(
             script.fn_available_actions_offerta(o.offerta_id)->'available_actions'
         ) = 0
         AND (script.fn_available_actions_offerta(o.offerta_id)->>'can_edit_testata')::boolean IS FALSE
         AND (script.fn_available_actions_offerta(o.offerta_id)->>'can_push_contratto')::boolean IS FALSE
         AND jsonb_array_length(
                 script.fn_available_actions_offerta(o.offerta_id)->'non_editable_fields'
             ) > 15
       FROM tmp_aa_ids o WHERE o.slot = 'RIFIUTATA'
    ),
    '9) RIFIUTATA (terminale): 0 azioni, can_edit_testata=false, can_push=false, non_editable_fields lista lunga'
);

-- ============================================================
-- TEST 10) Tutte le label_key in available_actions iniziano per 'vendite.offerte.'
--          Copre azioni da seed CSV (BOZZA, EMESSA) + hardcoded (ACCT-1).
-- ============================================================
SELECT ok(
    COALESCE(
        (SELECT bool_and((elem->>'label_key') LIKE 'vendite.offerte.%')
           FROM (VALUES ('BOZZA'), ('EMESSA'), ('ACCT-1')) AS slots(slot)
           JOIN tmp_aa_ids o USING (slot),
                jsonb_array_elements(
                    script.fn_available_actions_offerta(o.offerta_id)->'available_actions'
                ) AS elem
        ),
        false
    ),
    '10) Tutte le label_key in available_actions iniziano per vendite.offerte.'
);

-- ============================================================
-- TEST 11) ACCETTATA senza ordine: can_genera_ordine=true, reason null,
--          genera_ordine in available_actions.
-- ============================================================
SELECT ok(
    (SELECT
         (script.fn_available_actions_offerta(o.offerta_id)->>'can_genera_ordine')::boolean IS TRUE
         AND (script.fn_available_actions_offerta(o.offerta_id)->>'can_genera_ordine_reason') IS NULL
         AND EXISTS (
             SELECT 1
               FROM jsonb_array_elements(
                        script.fn_available_actions_offerta(o.offerta_id)->'available_actions'
                    ) AS elem
              WHERE elem->>'key' = 'genera_ordine'
         )
       FROM tmp_aa_ids o WHERE o.slot = 'ACCT-1'
    ),
    '11) ACCETTATA senza ordine: can_genera_ordine=true, reason null, genera_ordine in available_actions'
);

-- ============================================================
-- TEST 12) ACCETTATA con ordine generato (mutua esclusivita'):
--          ordine presente, NESSUN contratto. genera_ordine bloccato dal proprio
--          ordine; push_contratto ANCHE bloccato (own-doc first -> reason
--          dell'ordine). Entrambe le azioni speciali assenti; l'unica transizione
--          manuale da ACCETTATA (annulla, rev 2026-10-21) e' SPENTA col motivo
--          DOCUMENTI_VIVI: l'offerta vive nell'ordine.
-- ============================================================
SELECT ok(
    (SELECT
         -- genera_ordine: bloccato dall'ordine gia' generato
         (script.fn_available_actions_offerta(o.offerta_id)->>'can_genera_ordine')::boolean IS FALSE
         AND (script.fn_available_actions_offerta(o.offerta_id)->>'can_genera_ordine_reason')
             = 'OFFERTA_ORDINE_GIA_GENERATO'
         -- push_contratto: ora ANCHE bloccato (mutua esclusivita'); reason = ordine
         AND (script.fn_available_actions_offerta(o.offerta_id)->>'can_push_contratto')::boolean IS FALSE
         AND (script.fn_available_actions_offerta(o.offerta_id)->>'can_push_contratto_reason')
             = 'OFFERTA_ORDINE_GIA_GENERATO'
         -- entrambe le azioni speciali assenti: resta solo annulla, SPENTA
         AND (SELECT jsonb_agg(jsonb_build_array(a->>'key', a->>'enabled', a->>'reason'))
                FROM jsonb_array_elements(
                         script.fn_available_actions_offerta(o.offerta_id)->'available_actions') a)
             = '[["annulla", "false", "DOCUMENTI_VIVI"]]'::jsonb
       FROM tmp_aa_ids o WHERE o.slot = 'ACCT-ORD'
    ),
    '12) ACCETTATA con ordine (mutua esclusivita): ordine E push bloccati, reason=OFFERTA_ORDINE_GIA_GENERATO, resta solo annulla spenta (DOCUMENTI_VIVI)'
);

-- ============================================================
-- TEST 13) non ACCETTATA (BOZZA): can_genera_ordine=false,
--          reason='OFFERTA_NON_ACCETTATA'.
-- ============================================================
SELECT ok(
    (SELECT
         (script.fn_available_actions_offerta(o.offerta_id)->>'can_genera_ordine')::boolean IS FALSE
         AND (script.fn_available_actions_offerta(o.offerta_id)->>'can_genera_ordine_reason')
             = 'OFFERTA_NON_ACCETTATA'
       FROM tmp_aa_ids o WHERE o.slot = 'BOZZA'
    ),
    '13) non ACCETTATA (BOZZA): can_genera_ordine=false, reason=OFFERTA_NON_ACCETTATA'
);

-- ============================================================
-- TEST 14) Indice: secondo ordine ('OFFERTA_COMMERCIALE', X) sull'offerta ACCT-ORD
--          (che ne ha gia' uno) viola uq_ordini_v_sorgente_offerta.
-- ============================================================
SELECT throws_ok(
    $sql$
        INSERT INTO vendite.ordini (
            soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
            stato_doc_ordine_id, valuta_id, data, storicizza,
            sorgente_tipo_id, sorgente_uid
        )
        SELECT od.soggetto_ruolo_id, (SELECT c.billing_account_id FROM tmp_aa_cli c), od.emittente_fiscale_id,
               od.stato_draft_ordine_id, od.valuta_id, DATE '2087-01-03', false,
               (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'OFFERTA_COMMERCIALE'),
               (SELECT o.uid FROM vendite.offerte_commerciali o
                 WHERE o.id = (SELECT offerta_id FROM tmp_aa_ids WHERE slot = 'ACCT-ORD'))
          FROM tmp_aa_ord od
    $sql$,
    '23505',
    NULL,
    '14) secondo ordine dalla stessa offerta viola uq_ordini_v_sorgente_offerta'
);

-- ============================================================
-- TEST 15) Indice: due ordini ('PREVENTIVO', Y) sono consentiti
--          (l'indice parziale vincola solo OFFERTA). Il preventivo e' vero: la
--          provenienza la valida il guard unico, che vuole un documento che esiste.
-- ============================================================
CREATE TEMP TABLE tmp_aa_prev AS
SELECT preventivo_uid FROM dbops.fn_pgtap_crea_preventivo_con_righe('PGT-AA-PREV', 'DRAFT');

INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
    stato_doc_ordine_id, valuta_id, data, storicizza,
    sorgente_tipo_id, sorgente_uid
)
SELECT od.soggetto_ruolo_id, (SELECT c.billing_account_id FROM tmp_aa_cli c), od.emittente_fiscale_id,
       od.stato_draft_ordine_id, od.valuta_id, DATE '2087-02-01', false,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO'),
       (SELECT preventivo_uid FROM tmp_aa_prev)
  FROM tmp_aa_ord od;

SELECT lives_ok(
    $sql$
        INSERT INTO vendite.ordini (
            soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
            stato_doc_ordine_id, valuta_id, data, storicizza,
            sorgente_tipo_id, sorgente_uid
        )
        SELECT od.soggetto_ruolo_id, (SELECT c.billing_account_id FROM tmp_aa_cli c), od.emittente_fiscale_id,
               od.stato_draft_ordine_id, od.valuta_id, DATE '2087-02-02', false,
               (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO'),
               (SELECT preventivo_uid FROM tmp_aa_prev)
          FROM tmp_aa_ord od
    $sql$,
    '15) due ordini PREVENTIVO con stessa origine consentiti (indice non li vincola)'
);

-- ============================================================
-- 16-17) enabled/reason sull'azione verso EMESSA: la capability specchia il
--   guard BOZZA->EMESSA. Rev 2026-10-07: entrambi leggono
--   script.fn_check_listino_congelabile sulla versione che VERREBBE congelata
--   (la fissata, altrimenti quella in vigore oggi), non la colonna nuda.
-- ============================================================
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, NULL,
           DATE '2088-01-01', ctx.stato_bozza_id
      FROM tmp_aa_ctx ctx
    RETURNING id
)
INSERT INTO tmp_aa_ids SELECT 'BOZZA_NOLISTINO', id FROM ins;

SELECT is(
    (SELECT a
       FROM jsonb_array_elements(
              script.fn_available_actions_offerta(
                (SELECT offerta_id FROM tmp_aa_ids WHERE slot = 'BOZZA_NOLISTINO')
              ) -> 'available_actions') AS a
      WHERE a ->> 'target_state' = 'EMESSA') -> 'enabled',
    'true'::jsonb,
    '16a) BOZZA senza versione fissata, listino con una versione in vigore: azione verso EMESSA accesa'
);

SELECT is(
    (SELECT a
       FROM jsonb_array_elements(
              script.fn_available_actions_offerta(
                (SELECT offerta_id FROM tmp_aa_ids WHERE slot = 'BOZZA_NOLISTINO')
              ) -> 'available_actions') AS a
      WHERE a ->> 'target_state' = 'EMESSA') -> 'reasons',
    '[]'::jsonb,
    '16b) ...senza nessun motivo (LISTINO_VERSIONE_MANCANTE non si emette piu'')'
);

SELECT is(
    (SELECT a
       FROM jsonb_array_elements(
              script.fn_available_actions_offerta(
                (SELECT offerta_id FROM tmp_aa_ids WHERE slot = 'BOZZA')
              ) -> 'available_actions') AS a
      WHERE a ->> 'target_state' = 'EMESSA') -> 'enabled',
    'true'::jsonb,
    '17) BOZZA con versione ATTIVA: azione verso EMESSA enabled'
);

-- ============================================================
-- TEST 19) Guard namespace i18n sulle reason_key (20260719-13).
-- Gemello del test 10, che copre le label_key: qui si coprono le
-- reason_key di push_contratto e genera_ordine, che erano emesse
-- sotto `offerte.*` — radice inesistente nei locales FE. Una chiave
-- non risolta non da' errore: da' testo mancante, quindi il motivo
-- del pulsante grigio non compariva e nessuno se ne accorgeva.
-- Convenzione: docs/it/dev/frontend/i18n-namespace-radici.md
-- Brief: brief-db-i18n-reason-mancanti-offerte-preventivi §2a
-- ============================================================
SELECT ok(
    COALESCE(
        (SELECT bool_and(k LIKE 'vendite.offerte.%')
           FROM (VALUES ('BOZZA'), ('EMESSA'), ('ACCT-1')) AS slots(slot)
           JOIN tmp_aa_ids o USING (slot)
           CROSS JOIN LATERAL (VALUES
               (script.fn_available_actions_offerta(o.offerta_id)->>'can_push_contratto_reason_key'),
               (script.fn_available_actions_offerta(o.offerta_id)->>'can_genera_ordine_reason_key')
           ) AS chiavi(k)
          WHERE k IS NOT NULL
        ),
        false
    ),
    '19) Tutte le reason_key di push/genera_ordine iniziano per vendite.offerte.'
);

SELECT * FROM finish();
ROLLBACK;
