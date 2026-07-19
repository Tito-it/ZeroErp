-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: script.fn_available_actions_offerta — capability layer offerte commerciali
-- ------------------------------------------------------------
-- Indice test (1..15):
--  1) Offerta inesistente → NULL
--  2) BOZZA: available_actions ha 2 azioni (emetti + annulla)
--  3) BOZZA: can_edit_testata=true, can_push_contratto=false, non_editable_fields lista corta
--  4) EMESSA: available_actions ha 3 azioni (accetta + rifiuta + crea_revisione)
--  5) EMESSA: can_edit_testata=false, can_create_revisione=true
--  6) EMESSA: azione rifiuta ha requires_motivazione=true (verifica meta update 20260526-01)
--  7) ACCETTATA senza contratto ne' ordine: can_push_contratto=true, push_contratto presente
--  8) ACCETTATA con contratto generato (mutua esclusivita'): can_push_contratto=false
--     E can_genera_ordine=false, entrambi reason='OFFERTA_CONTRATTO_GIA_GENERATO',
--     push_contratto E genera_ordine assenti -> available_actions=[]
--  9) Terminale (RIFIUTATA): available_actions=[], can_edit_testata=false,
--     can_push_contratto=false, non_editable_fields lista lunga
-- 10) Tutte le label_key in available_actions iniziano per 'vendite.offerte.'
-- 11) ACCETTATA senza ordine ne' contratto: can_genera_ordine=true, reason null, genera_ordine presente
-- 12) ACCETTATA con ordine generato (mutua esclusivita'): can_genera_ordine=false
--     E can_push_contratto=false, entrambi reason='OFFERTA_ORDINE_GIA_GENERATO',
--     genera_ordine E push_contratto assenti -> available_actions=[]
-- 13) non ACCETTATA (BOZZA): can_genera_ordine=false, reason='OFFERTA_NON_ACCETTATA'
-- 14) Indice: secondo ordine ('OFFERTA', X) viola uq_ordini_v_documento_origine_offerta
-- 15) Indice: due ordini ('PREVENTIVO', Y) consentiti (indice non li vincola)
-- 16a/16b) BOZZA senza listino_versione_id: azione verso EMESSA enabled=false +
--     reason='LISTINO_VERSIONE_MANCANTE' (rev 2026-07-19, uniformita' 6 domini)
-- 17) BOZZA con versione ATTIVA: azione verso EMESSA enabled=true
-- ------------------------------------------------------------

BEGIN;
SELECT plan(18);

-- ============================================================
-- Setup fixture: contesti di riferimento
-- (stesso approccio del test state_machine: BA senza tipi_utenze
--  per evitare guard tipo/classe sui contratti_utilities al push)
-- ============================================================
CREATE TEMP TABLE tmp_aa_ctx AS
SELECT
    (SELECT ba.id
       FROM anagrafiche.billing_account ba
      WHERE NOT EXISTS (
          SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
      )
      ORDER BY ba.id LIMIT 1) AS billing_account_id,
    (SELECT ba.istanza_utility_id
       FROM anagrafiche.billing_account ba
      WHERE NOT EXISTS (
          SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
      )
      ORDER BY ba.id LIMIT 1) AS istanza_utility_id,
    (SELECT ba.utility_id
       FROM anagrafiche.billing_account ba
      WHERE NOT EXISTS (
          SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
      )
      ORDER BY ba.id LIMIT 1) AS utility_id,
    (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
    (SELECT l.id FROM vendite.listini l WHERE l.attivo IS TRUE ORDER BY l.id LIMIT 1) AS listino_id,
    (SELECT lv.id FROM vendite.listini_versioni lv WHERE lv.stato = 'ATTIVA' ORDER BY lv.id LIMIT 1) AS listino_versione_id_attiva,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')     AS stato_bozza_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'EMESSA')    AS stato_emessa_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'ACCETTATA') AS stato_accettata_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'RIFIUTATA') AS stato_rifiutata_id;

-- GUC vuota: gli INSERT su vendite.ordini (test 11-15) superano i guard
-- emittente/scope senza restrizione (stesso approccio del test fn_aa_ordine).
SELECT set_config('app.current_user_id', '', true);

-- Riferimenti per creare ordini reali (test genera_ordine + indice).
-- BA=NULL + emittente esplicito = niente guard emittente<->BA da soddisfare.
CREATE TEMP TABLE tmp_aa_ord AS
SELECT
    (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr ORDER BY sr.id LIMIT 1) AS soggetto_ruolo_id,
    (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'DRAFT' AND attivo IS TRUE LIMIT 1) AS stato_draft_ordine_id,
    (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
    (SELECT emittente_fiscale_id FROM tmp_aa_ctx) AS emittente_fiscale_id;

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

-- Slot EMESSA: BOZZA->EMESSA tramite trigger guard (test 4-6)
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

UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_emessa_id FROM tmp_aa_ctx)
 WHERE id = (SELECT offerta_id FROM tmp_aa_ids WHERE slot = 'EMESSA');

-- Slot ACCT-1: INSERT diretto in ACCETTATA, senza contratto (test 7)
-- INSERT bypass il trigger BEFORE UPDATE: stato direttamente terminale.
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2084-01-01', ctx.stato_accettata_id
      FROM tmp_aa_ctx ctx
    RETURNING id
)
INSERT INTO tmp_aa_ids SELECT 'ACCT-1', id FROM ins;

-- Slot ACCT-2: INSERT diretto in ACCETTATA, poi fn_push genera il contratto (test 8)
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2085-01-01', ctx.stato_accettata_id
      FROM tmp_aa_ctx ctx
    RETURNING id
)
INSERT INTO tmp_aa_ids SELECT 'ACCT-2', id FROM ins;

-- Genera il contratto da ACCT-2 tramite fn_push (p_pratica_id = NULL).
SELECT vendite.fn_push_offerta_a_contratto(
    (SELECT offerta_id FROM tmp_aa_ids WHERE slot = 'ACCT-2'),
    NULL
);

-- Slot RIFIUTATA: INSERT diretto in RIFIUTATA (terminale, test 9)
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2086-01-01', ctx.stato_rifiutata_id
      FROM tmp_aa_ctx ctx
    RETURNING id
)
INSERT INTO tmp_aa_ids SELECT 'RIFIUTATA', id FROM ins;

-- Slot ACCT-ORD: ACCETTATA con un ordine gia' generato
-- (documento_origine = ('OFFERTA', id)) -> genera_ordine NON disponibile
-- (test 12) e secondo ordine bloccato dall'indice (test 14).
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2087-01-01', ctx.stato_accettata_id
      FROM tmp_aa_ctx ctx
    RETURNING id
)
INSERT INTO tmp_aa_ids SELECT 'ACCT-ORD', id FROM ins;

-- Ordine collegato all'offerta ACCT-ORD (documento_origine OFFERTA).
INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
    stato_doc_ordine_id, valuta_id, data, storicizza,
    documento_origine_tipo, documento_origine_id
)
SELECT od.soggetto_ruolo_id, NULL::bigint, od.emittente_fiscale_id,
       od.stato_draft_ordine_id, od.valuta_id, DATE '2087-01-02', false,
       'OFFERTA', (SELECT offerta_id FROM tmp_aa_ids WHERE slot = 'ACCT-ORD')
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
-- TEST 5) EMESSA: can_edit_testata=false, can_create_revisione=true
-- ============================================================
SELECT ok(
    (SELECT
         (script.fn_available_actions_offerta(o.offerta_id)->>'can_edit_testata')::boolean IS FALSE
         AND (script.fn_available_actions_offerta(o.offerta_id)->>'can_create_revisione')::boolean IS TRUE
       FROM tmp_aa_ids o WHERE o.slot = 'EMESSA'
    ),
    '5) EMESSA: can_edit_testata=false, can_create_revisione=true'
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
--         contratto). Entrambe le azioni speciali assenti e ACCETTATA non ha
--         transizioni manuali -> available_actions=[].
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
         -- entrambe le azioni speciali assenti -> available_actions vuoto
         AND jsonb_array_length(
                 script.fn_available_actions_offerta(o.offerta_id)->'available_actions'
             ) = 0
       FROM tmp_aa_ids o WHERE o.slot = 'ACCT-2'
    ),
    '8) ACCETTATA con contratto (mutua esclusivita): push E ordine bloccati, reason=OFFERTA_CONTRATTO_GIA_GENERATO, available_actions=[]'
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
--          dell'ordine). Entrambe le azioni speciali assenti e ACCETTATA non ha
--          transizioni manuali -> available_actions=[].
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
         -- entrambe le azioni speciali assenti -> available_actions vuoto
         AND jsonb_array_length(
                 script.fn_available_actions_offerta(o.offerta_id)->'available_actions'
             ) = 0
       FROM tmp_aa_ids o WHERE o.slot = 'ACCT-ORD'
    ),
    '12) ACCETTATA con ordine (mutua esclusivita): ordine E push bloccati, reason=OFFERTA_ORDINE_GIA_GENERATO, available_actions=[]'
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
-- TEST 14) Indice: secondo ordine ('OFFERTA', X) sull'offerta ACCT-ORD
--          (che ne ha gia' uno) viola uq_ordini_v_documento_origine_offerta.
-- ============================================================
SELECT throws_ok(
    $sql$
        INSERT INTO vendite.ordini (
            soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
            stato_doc_ordine_id, valuta_id, data, storicizza,
            documento_origine_tipo, documento_origine_id
        )
        SELECT od.soggetto_ruolo_id, NULL::bigint, od.emittente_fiscale_id,
               od.stato_draft_ordine_id, od.valuta_id, DATE '2087-01-03', false,
               'OFFERTA', (SELECT offerta_id FROM tmp_aa_ids WHERE slot = 'ACCT-ORD')
          FROM tmp_aa_ord od
    $sql$,
    '23505',
    NULL,
    '14) secondo ordine OFFERTA duplicato viola uq_ordini_v_documento_origine_offerta'
);

-- ============================================================
-- TEST 15) Indice: due ordini ('PREVENTIVO', Y) sono consentiti
--          (l'indice parziale vincola solo OFFERTA). Id origine arbitrario:
--          documento_origine_id e' polimorfo senza FK.
-- ============================================================
INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
    stato_doc_ordine_id, valuta_id, data, storicizza,
    documento_origine_tipo, documento_origine_id
)
SELECT od.soggetto_ruolo_id, NULL::bigint, od.emittente_fiscale_id,
       od.stato_draft_ordine_id, od.valuta_id, DATE '2087-02-01', false,
       'PREVENTIVO', 999999
  FROM tmp_aa_ord od;

SELECT lives_ok(
    $sql$
        INSERT INTO vendite.ordini (
            soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
            stato_doc_ordine_id, valuta_id, data, storicizza,
            documento_origine_tipo, documento_origine_id
        )
        SELECT od.soggetto_ruolo_id, NULL::bigint, od.emittente_fiscale_id,
               od.stato_draft_ordine_id, od.valuta_id, DATE '2087-02-02', false,
               'PREVENTIVO', 999999
          FROM tmp_aa_ord od
    $sql$,
    '15) due ordini PREVENTIVO con stessa origine consentiti (indice non li vincola)'
);

-- ============================================================
-- 16-17) enabled/reason sull'azione verso EMESSA (rev 2026-07-19):
--   la capability specchia il guard BOZZA->EMESSA (versione listino
--   valorizzata + ATTIVA). Brief-db-guard-righe-avanzamento-stato §1a.
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
    'false'::jsonb,
    '16a) BOZZA senza versione listino: azione verso EMESSA disabled'
);

SELECT is(
    (SELECT a
       FROM jsonb_array_elements(
              script.fn_available_actions_offerta(
                (SELECT offerta_id FROM tmp_aa_ids WHERE slot = 'BOZZA_NOLISTINO')
              ) -> 'available_actions') AS a
      WHERE a ->> 'target_state' = 'EMESSA') ->> 'reason',
    'LISTINO_VERSIONE_MANCANTE',
    '16b) ...con reason LISTINO_VERSIONE_MANCANTE'
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

SELECT * FROM finish();
ROLLBACK;
