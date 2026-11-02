-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_disdetta_cliente(p_cliente_id, p_data_cessazione)
--
-- Indice test (12):
--   T01) Precondizioni: config e anagrafiche di riferimento presenti
--   T02) Setup: istanza + BA + cliente attivo con PDP
--   T03) DB-08: fn_disdetta_cliente(NULL, date) -> errore parametro
--   T04) DB-08: fn_disdetta_cliente(id, NULL) -> errore parametro
--   T05) Extra: fn_disdetta_cliente(id_inesistente, date) -> errore non trovato
--   T06) DB-07: data_cessazione < data_attivazione -> errore
--   T07) DB-05: disdetta happy path -> restituisce ID cliente
--   T08) DB-05: stato cliente = CH dopo disdetta
--   T09) DB-05: periodo = [data_attivazione, data_cessazione) dopo disdetta
--   T10) DB-05: PDP stato = DISP dopo disdetta
--   T11) DB-09: BA valido_al IS NULL dopo disdetta (policy: BA resta attivo)
--   T12) DB-06: fn_disdetta_cliente su cliente gia chiuso -> errore
--
-- Nota: soggetto e PDP si COSTRUISCONO (rev 2026-09-23; prima erano pescati
--       dal DB), e le istanze sono fittizia=false per testare il ciclo
--       completo incluso PDP.
-- ------------------------------------------------------------

-- =========================================================
-- Cleanup iniziale (idempotente)
-- =========================================================
DO $$
BEGIN
    -- Abilita manutenzione per poter eliminare clienti
    SET LOCAL zeroerp.maintenance_ruoli_delete = 'on';

    DELETE FROM anagrafiche.clienti c
    WHERE c.codice_cliente_importato LIKE 'TST-DIS-%';

    -- 🔴 Il mapping emittente PRIMA del billing account (2026-08-18).
    --   Ogni BA nuovo riceve automaticamente una riga in
    --   `emittenti_fiscali_billing_account`, e la sua FK impedisce di
    --   cancellare il padre: la pulizia moriva sul figlio che non aveva
    --   creato lei. ⚠️ Quarto strato di questo file — ogni difetto ne
    --   nascondeva un altro.
    DELETE FROM anagrafiche.emittenti_fiscali_billing_account efba
    WHERE efba.billing_account_id IN (
        SELECT ba.id FROM anagrafiche.billing_account ba
        WHERE ba.istanza_utility_id IN (
            SELECT iu.id FROM anagrafiche.istanze_utilities iu
            WHERE iu.codice LIKE 'TST-DIS-%'
        )
    );

    DELETE FROM anagrafiche.billing_account ba
    WHERE ba.istanza_utility_id IN (
        SELECT iu.id FROM anagrafiche.istanze_utilities iu
        WHERE iu.codice LIKE 'TST-DIS-%'
    );

    DELETE FROM anagrafiche.istanze_utilities iu
    WHERE iu.codice LIKE 'TST-DIS-%';
END;
$$;

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. In testa e non in coda apposta:
--   in coda scatterebbero tutti insieme DOPO il cleanup, su righe ormai
--   cancellate. Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- =========================================================
-- 0) Precondizioni: recupera riferimenti esistenti dal DB
-- =========================================================
CREATE TEMP TABLE tmp_dis_cfg AS
SELECT
    (SELECT sc.id FROM config.stati_cliente sc
     WHERE sc.codice_interno = 'AT') AS stato_at_id,
    (SELECT sc.id FROM config.stati_cliente sc
     WHERE sc.codice_interno = 'CH') AS stato_ch_id,
    (SELECT sp.id FROM config.stati_pdp sp
     WHERE sp.codice_interno = 'DISP') AS stato_pdp_disp_id,
    (SELECT sp.id FROM config.stati_pdp sp
     -- rev 2026-08-29: via il codice IVA da questa configurazione e dalla
     --   fixture. La colonna omonima non esiste piu' su anagrafiche.clienti
     --   (changeSet 20260829-22): l'aliquota la decide la merce, non il cliente.
     WHERE sp.codice_interno = 'ATT') AS stato_pdp_att_id;

-- ⛔ 2026-09-23: PDP e soggetto erano PESCATI — «il primo PDP GAS attivo con
--   un indirizzo», «il soggetto del primo billing account senza padre». Su un
--   database ricostruito dai changelog non c'e' nessuno dei due, e la fixture
--   moriva su «Non e' stato fornito un valore per pdp_id». Ora si
--   COSTRUISCONO: un PDP GAS nuovo su un indirizzo suo, e un soggetto persona
--   giuridica col suo ruolo CL completo degli indirizzi di ruolo.
CREATE TEMP TABLE tmp_dis_pdp AS
SELECT p.pdp_id,
       p.indirizzo_dettaglio_id,
       p.utility_id
FROM dbops.fn_pgtap_crea_pdp('GAS') p;

CREATE TEMP TABLE tmp_dis_soggetto_pg AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Cliente disdetta') AS soggetto_id;

CREATE TEMP TABLE tmp_dis_soggetto AS
SELECT s.soggetto_id,
       dbops.fn_pgtap_crea_soggetto_ruolo(s.soggetto_id, 'CL') AS soggetto_ruolo_id
FROM tmp_dis_soggetto_pg s;

SELECT ok(
    (SELECT stato_at_id IS NOT NULL
        AND stato_ch_id IS NOT NULL
        AND stato_pdp_disp_id IS NOT NULL
        AND stato_pdp_att_id IS NOT NULL
     FROM tmp_dis_cfg)
    AND (SELECT pdp_id IS NOT NULL FROM tmp_dis_pdp)
    AND (SELECT soggetto_id IS NOT NULL
            AND soggetto_ruolo_id IS NOT NULL
         FROM tmp_dis_soggetto),
    'T01 Precondizioni: stati AT/CH, stati PDP ATT/DISP, IVA, PDP GAS, soggetto presenti'
);

-- =========================================================
-- 1) Setup: crea istanza + BA + cliente attivo con PDP
-- =========================================================

-- Data base futura per evitare conflitti con dati esistenti
CREATE TEMP TABLE tmp_dis_base AS
SELECT (script.fn_data_operativa() + 60)::date AS d0;

-- Chiusura preventiva eventuale cliente attivo sul PDP alla data test
CREATE TEMP TABLE tmp_dis_subentro_pre AS
SELECT script.fn_subentro_cliente(
    (SELECT pdp_id FROM tmp_dis_pdp),
    (SELECT d0 FROM tmp_dis_base)
) AS cliente_chiuso_id;

-- Tabella per conservare gli ID di test
-- 🔴 DEFERRED LOCALE PER LA SOLA FIXTURE, aggiunto il 2026-08-18.
--   `trg_istanze_utilities_z90_require_utility_dichiarata_ins` e' un CONSTRAINT
--   TRIGGER **DEFERRABLE INITIALLY DEFERRED**: pretende che ogni istanza nuova
--   abbia almeno un satellite, e lo verifica al COMMIT proprio per lasciare
--   spazio a «INSERT istanza + INSERT BA/cliente» nella stessa transazione.
--   La fixture qui sotto fa esattamente cosi', ed e' corretta.
--
--   ⚠️ A romperla e' il `SET CONSTRAINTS ALL IMMEDIATE` del preambolo (riga 63):
--   riporta il trigger a scattare a fine di OGNI istruzione, quindi subito dopo
--   l'INSERT dell'istanza — quando il satellite non c'e' ancora. Il file moriva
--   li'.
--
--   ⭐ Due regole giuste che si scontrano: IMMEDIATE serve a non essere verdi
--   per sottrazione, DEFERRED serve a poter costruire un aggregato. Si risolve
--   restringendo la seconda alla sola fixture — e RIMETTENDO IMMEDIATE prima
--   delle asserzioni, che e' la meta' che non va dimenticata.
SET CONSTRAINTS ALL DEFERRED;

CREATE TEMP TABLE tmp_dis_ids (
    istanza_id bigint,
    ba_id bigint,
    cliente_id bigint
);

DO $$
DECLARE
    v_soggetto_id uuid;
    v_soggetto_ruolo_id bigint;
    v_utility_id integer;
    v_pdp_id bigint;
    v_indirizzo_id bigint;
    v_stato_at_id integer;
    v_d0 date;
    v_istanza_id bigint;
    v_ba_id bigint;
    v_cliente_id bigint;
BEGIN
    SELECT soggetto_id, soggetto_ruolo_id
      INTO v_soggetto_id, v_soggetto_ruolo_id
      FROM tmp_dis_soggetto;

    SELECT pdp_id, indirizzo_dettaglio_id, utility_id
      INTO v_pdp_id, v_indirizzo_id, v_utility_id
      FROM tmp_dis_pdp;

    SELECT stato_at_id
      INTO v_stato_at_id
      FROM tmp_dis_cfg;

    SELECT d0 INTO v_d0 FROM tmp_dis_base;

    -- Istanza non fittizia (con indirizzo e PDP per testare sync stato PDP)
    INSERT INTO anagrafiche.istanze_utilities (
        soggetto_id, fittizia, codice,
        indirizzo_dettaglio_id, pdp_id
    ) VALUES (
        v_soggetto_id, false, 'TST-DIS-IU-01',
        v_indirizzo_id, v_pdp_id
    ) RETURNING id INTO v_istanza_id;

    -- Billing account
    -- 🔴 `categoria_cliente_id` aggiunta il 2026-08-18: la colonna e' diventata
    --   NOT NULL dopo che questa fixture era stata scritta, e il file moriva
    --   qui. Non si vedeva perche' moriva PRIMA, sul constraint trigger
    --   dell'istanza: due strati di difetto, il primo che nascondeva il secondo.
    INSERT INTO anagrafiche.billing_account (
        istanza_utility_id, soggetto_ruolo_id, utility_id, valido_dal,
        categoria_cliente_id
    ) VALUES (
        v_istanza_id, v_soggetto_ruolo_id, v_utility_id::integer, script.fn_data_operativa(),
        (SELECT cc.id FROM anagrafiche.categorie_clienti cc
          WHERE cc.attivo IS TRUE ORDER BY cc.id LIMIT 1)
    ) RETURNING id INTO v_ba_id;

    -- Cliente attivo con PDP
    INSERT INTO anagrafiche.clienti (
        soggetto_ruolo_id, istanza_utility_id,
        stato_cliente_id, data_attivazione,
        billing_account_id,
        pdp_id, codice_cliente_importato
    ) VALUES (
        v_soggetto_ruolo_id, v_istanza_id,
        v_stato_at_id, v_d0,
        v_ba_id,
        v_pdp_id, 'TST-DIS-CLI-01'
    ) RETURNING id INTO v_cliente_id;

    INSERT INTO tmp_dis_ids (istanza_id, ba_id, cliente_id)
    VALUES (v_istanza_id, v_ba_id, v_cliente_id);
END;
$$;

-- ⭐ Ripristino IMMEDIATE: da qui in poi le asserzioni devono vedere i vincoli
--   scattare a fine istruzione, altrimenti il file tornerebbe verde per
--   sottrazione — che e' il motivo per cui il preambolo lo imposta.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT ok(
    (SELECT count(*) FROM tmp_dis_ids) = 1,
    'T02 Setup: istanza + BA + cliente attivo con PDP creati'
);

-- =========================================================
-- 2) DB-08: parametri NULL -> errore
-- =========================================================
SELECT throws_ok(
    $$SELECT script.fn_disdetta_cliente(NULL::bigint, '2026-06-01'::date)$$,
    NULL,
    'T03 DB-08: fn_disdetta_cliente(NULL, date) -> errore parametro invalido'
);

SELECT throws_ok(
    format(
        'SELECT script.fn_disdetta_cliente(%s, NULL::date)',
        (SELECT cliente_id FROM tmp_dis_ids)
    ),
    NULL,
    'T04 DB-08: fn_disdetta_cliente(id, NULL) -> errore parametro invalido'
);

-- =========================================================
-- 3) Cliente non trovato (ID inesistente)
-- =========================================================
SELECT throws_ok(
    $$SELECT script.fn_disdetta_cliente(999999999::bigint, '2026-06-01'::date)$$,
    NULL,
    'T05 fn_disdetta_cliente(id_inesistente, date) -> errore cliente non trovato'
);

-- =========================================================
-- 4) DB-07: data_cessazione < data_attivazione -> errore
-- =========================================================
SELECT throws_ok(
    format(
        'SELECT script.fn_disdetta_cliente(%s, %L::date)',
        (SELECT cliente_id FROM tmp_dis_ids),
        (SELECT (d0 - 1)::date FROM tmp_dis_base)
    ),
    NULL,
    'T06 DB-07: data_cessazione < data_attivazione -> errore'
);

-- =========================================================
-- 5) DB-05: happy path disdetta
-- =========================================================
SELECT is(
    (SELECT script.fn_disdetta_cliente(
        (SELECT cliente_id FROM tmp_dis_ids),
        (SELECT (d0 + 10)::date FROM tmp_dis_base)
    )),
    (SELECT cliente_id FROM tmp_dis_ids),
    'T07 DB-05: disdetta restituisce ID cliente'
);

-- =========================================================
-- 6) DB-05: stato cliente = CH dopo disdetta
-- =========================================================
SELECT is(
    (SELECT sc.codice_interno
       FROM anagrafiche.clienti c
       JOIN config.stati_cliente sc ON sc.id = c.stato_cliente_id
      WHERE c.id = (SELECT cliente_id FROM tmp_dis_ids)),
    -- 🔴 `::bpchar` -> `::varchar` il 2026-08-18: `stati_cliente.codice_interno`
    --   e' passata da `character` a `character varying` con 20260401-21, e
    --   pgTAP non trova piu' una `is(varchar, char, unknown)`. Il test non
    --   falliva: non compilava — terzo strato di difetto in questo file.
    'CH'::varchar,
    'T08 DB-05: stato cliente = CH dopo disdetta'
);

-- =========================================================
-- 7) DB-05: periodo aggiornato [data_attivazione, data_cessazione)
-- =========================================================
SELECT ok(
    (SELECT c.periodo IS NOT NULL
        AND lower(c.periodo) = (SELECT d0 FROM tmp_dis_base)
        AND upper(c.periodo) = (SELECT (d0 + 10)::date FROM tmp_dis_base)
       FROM anagrafiche.clienti c
      WHERE c.id = (SELECT cliente_id FROM tmp_dis_ids)),
    'T09 DB-05: periodo = [data_attivazione, data_cessazione) dopo disdetta'
);

-- =========================================================
-- 8) DB-05: PDP stato = DISP dopo disdetta
-- =========================================================
SELECT is(
    (SELECT sp.codice_interno
       FROM anagrafiche.pdp p
       JOIN config.stati_pdp sp ON sp.id = p.stato_pdp_id
      WHERE p.id = (SELECT pdp_id FROM tmp_dis_pdp)),
    'DISP'::varchar,
    'T10 DB-05: PDP stato = DISP dopo disdetta'
);

-- =========================================================
-- 9) DB-09: BA valido_al IS NULL dopo disdetta (policy: BA resta attivo)
-- =========================================================
SELECT ok(
    (SELECT ba.valido_al IS NULL
       FROM anagrafiche.billing_account ba
      WHERE ba.id = (SELECT ba_id FROM tmp_dis_ids)),
    'T11 DB-09: BA valido_al IS NULL dopo disdetta (policy: BA resta attivo)'
);

-- =========================================================
-- 10) DB-06: disdetta su cliente gia chiuso -> errore
-- =========================================================
SELECT throws_ok(
    format(
        'SELECT script.fn_disdetta_cliente(%s, %L::date)',
        (SELECT cliente_id FROM tmp_dis_ids),
        (SELECT (d0 + 20)::date FROM tmp_dis_base)
    ),
    NULL,
    'T12 DB-06: fn_disdetta_cliente su cliente gia chiuso -> errore non attivo'
);

-- =========================================================
-- Cleanup finale
-- =========================================================
DO $$
BEGIN
    -- ⚠️ rev 2026-10-08 (brief-db-istanza-nasce-col-ba, R-1): l'ultimo BA di
    --   un'istanza non si cancella da solo (constraint trigger
    --   trg_billing_account_z90_require_istanza_ha_ba_dlt). Qui istanza e BA se
    --   ne vanno INSIEME: la finestra differita si apre prima dei DELETE e si
    --   richiude dopo quello delle istanze, cosi' il controllo scatta su uno
    --   stato finito. Con i vincoli IMMEDIATE del preambolo scatterebbe sul
    --   DELETE dei BA, con l'istanza ancora li'.
    SET CONSTRAINTS ALL DEFERRED;
    SET LOCAL zeroerp.maintenance_ruoli_delete = 'on';

    DELETE FROM anagrafiche.clienti c
    WHERE c.codice_cliente_importato LIKE 'TST-DIS-%';

    -- 🔴 Il mapping emittente PRIMA del billing account (2026-08-18).
    --   Ogni BA nuovo riceve automaticamente una riga in
    --   `emittenti_fiscali_billing_account`, e la sua FK impedisce di
    --   cancellare il padre: la pulizia moriva sul figlio che non aveva
    --   creato lei. ⚠️ Quarto strato di questo file — ogni difetto ne
    --   nascondeva un altro.
    DELETE FROM anagrafiche.emittenti_fiscali_billing_account efba
    WHERE efba.billing_account_id IN (
        SELECT ba.id FROM anagrafiche.billing_account ba
        WHERE ba.istanza_utility_id IN (
            SELECT iu.id FROM anagrafiche.istanze_utilities iu
            WHERE iu.codice LIKE 'TST-DIS-%'
        )
    );

    DELETE FROM anagrafiche.billing_account ba
    WHERE ba.istanza_utility_id IN (
        SELECT iu.id FROM anagrafiche.istanze_utilities iu
        WHERE iu.codice LIKE 'TST-DIS-%'
    );

    DELETE FROM anagrafiche.istanze_utilities iu
    WHERE iu.codice LIKE 'TST-DIS-%';

    SET CONSTRAINTS ALL IMMEDIATE;
END;
$$;

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
