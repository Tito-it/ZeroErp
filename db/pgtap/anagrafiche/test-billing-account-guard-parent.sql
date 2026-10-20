-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: guard dissociazione parent_account_id su billing_account
-- Funzione: anagrafiche.trgfn_billing_account_guard_normalize()
-- Trigger:  trg_billing_account_guard_normalize_ins_upd
--
-- Scenario:
--   1) Precondizioni: riferimenti config presenti
--   2) Setup: crea BA padre + BA figlio + commessa + attivita_fatturabili
--   3) Rimozione parent_account_id con attivita non fatturate → FALLISCE
--   4) Attivita fatturata → rimozione parent_account_id → OK
--   5) BA figlio senza attivita → rimozione parent_account_id → OK
--
-- Nota: il soggetto e' il cliente costruito da dbops.fn_pgtap_crea_mondo_cliente
--       (2026-09-23): prima lo si pescava «per evitare la complessita' di
--       creare soggetto + contatto + indirizzi», che ora e' del builder.
-- ------------------------------------------------------------

-- =========================================================
-- Cleanup iniziale (idempotente)
-- =========================================================
DO $$
DECLARE
    l_codici_commesse text[] := ARRAY[
        'TST-GUARD-PARENT-COMM-01'
    ];
    l_codici_ba text[];
BEGIN
    -- Cleanup attivita_fatturabili (via commessa)
    DELETE FROM vendite.attivita_fatturabili af
    WHERE af.commessa_id IN (
        SELECT c.id FROM vendite.commesse c WHERE c.codice = ANY(l_codici_commesse)
    );

    -- Cleanup commesse_attivita
    DELETE FROM vendite.commesse_attivita ca
    WHERE ca.commessa_id IN (
        SELECT c.id FROM vendite.commesse c WHERE c.codice = ANY(l_codici_commesse)
    );

    -- Cleanup commesse
    DELETE FROM vendite.commesse c
    WHERE c.codice = ANY(l_codici_commesse);

    -- Cleanup billing_account (child prima del parent per FK)
    SELECT array_agg(ba.codice) INTO l_codici_ba
    FROM anagrafiche.billing_account ba
    JOIN anagrafiche.istanze_utilities iu ON iu.id = ba.istanza_utility_id
    WHERE iu.codice LIKE 'TST-GUARD-PARENT-%';

    IF l_codici_ba IS NOT NULL THEN
        -- Prima rimuovi parent_account_id dai figli (altrimenti FK blocca delete parent)
        UPDATE anagrafiche.billing_account ba
           SET parent_account_id = NULL
         WHERE ba.id IN (
            SELECT ba2.id
            FROM anagrafiche.billing_account ba2
            JOIN anagrafiche.istanze_utilities iu ON iu.id = ba2.istanza_utility_id
            WHERE iu.codice LIKE 'TST-GUARD-PARENT-%'
              AND ba2.parent_account_id IS NOT NULL
         );

        -- ⚠️ Prima il legame con l'emittente: vedi la nota nel cleanup finale
        --   (FK fk_emittenti_fiscali_billing_account_ba, 20260819-04).
        DELETE FROM anagrafiche.emittenti_fiscali_billing_account efba
        WHERE efba.billing_account_id IN (
            SELECT ba.id FROM anagrafiche.billing_account ba
            WHERE ba.istanza_utility_id IN (
                SELECT iu.id FROM anagrafiche.istanze_utilities iu
                WHERE iu.codice LIKE 'TST-GUARD-PARENT-%'
            )
        );

        DELETE FROM anagrafiche.billing_account ba
        WHERE ba.istanza_utility_id IN (
            SELECT iu.id FROM anagrafiche.istanze_utilities iu
            WHERE iu.codice LIKE 'TST-GUARD-PARENT-%'
        );
    END IF;

    -- Cleanup istanze_utilities
    DELETE FROM anagrafiche.istanze_utilities iu
    WHERE iu.codice LIKE 'TST-GUARD-PARENT-%';
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
--   ogni istruzione era una transazione a se'. Messa in testa e non in coda
--   apposta: in coda scatterebbero tutti insieme DOPO il cleanup, su righe
--   ormai cancellate, e fallirebbero per un motivo che non riguarda il test.
--   Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

-- =========================================================
-- 0) Precondizioni: il cliente si COSTRUISCE, i cataloghi si scelgono
-- =========================================================
-- ⛔ 2026-09-23: soggetto, ruolo e utility venivano PESCATI da «un billing
--   account senza padre», e l'articolo da «l'ultimo inserito». Su un database
--   ricostruito dai changelog i billing account sono zero: la fixture moriva
--   sul NOT NULL di `istanze_utilities.soggetto_id`. Il soggetto del mondo e'
--   un cliente vero dell'azienda di chi agisce (contesto aperto sopra: il BB
--   riusa la sua azienda), e le tre istanze qui sotto sono sue.
CREATE TEMP TABLE tmp_mondo_guard_parent AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('guard parent');

CREATE TEMP TABLE tmp_refs_guard_parent AS
SELECT
    m.cliente_soggetto_id       AS soggetto_id,
    m.cliente_soggetto_ruolo_id AS soggetto_ruolo_id,
    m.utility_id,
    -- ⚠️ Non gestito a magazzino: il caso e' il guard del parent, non il
    --   movimento dell'articolo.
    dbops.fn_pgtap_crea_articolo('PGTAP-GPAR-' || m.billing_account_id,
                                 p_gestito := false) AS articolo_id,
    (SELECT u.id
       FROM catalogo.unita_misura u
      WHERE u.attivo IS TRUE
      ORDER BY u.id
      LIMIT 1) AS uom_id,
    (SELECT t.id
       FROM config.tipi_doc_fiscale t
      WHERE t.attivo IS TRUE
      ORDER BY t.id
      LIMIT 1) AS tipo_doc_fiscale_id,
    (SELECT v.id
       FROM config.valute v
      ORDER BY v.id
      LIMIT 1) AS valuta_id
FROM tmp_mondo_guard_parent m;

SELECT ok(
    (SELECT soggetto_id IS NOT NULL
        AND soggetto_ruolo_id IS NOT NULL
        AND utility_id IS NOT NULL
        AND articolo_id IS NOT NULL
        AND uom_id IS NOT NULL
        AND tipo_doc_fiscale_id IS NOT NULL
        AND valuta_id IS NOT NULL
     FROM tmp_refs_guard_parent),
    'Precondizioni: riferimenti config e anagrafiche presenti'
);

-- =========================================================
-- 1) Setup: crea istanze, BA padre, BA figli
-- =========================================================

-- 3 istanze: una per BA padre, una per BA figlio con attivita, una per BA figlio senza attivita
CREATE TEMP TABLE tmp_ids_guard (
    parent_ba_id bigint,
    child1_ba_id bigint,
    child2_ba_id bigint
);

DO $$
DECLARE
    v_soggetto_id uuid;
    v_utility_id integer;
    v_soggetto_ruolo_id bigint;
    v_parent_istanza_id bigint;
    v_child1_istanza_id bigint;
    v_child2_istanza_id bigint;
    v_parent_ba_id bigint;
    v_child1_ba_id bigint;
    v_child2_ba_id bigint;
    v_articolo_id uuid;
    v_uom_id bigint;
    v_tipo_doc_id bigint;
    v_valuta_id integer;
    v_commessa_id bigint;
    v_commessa_attivita_id bigint;
    v_categoria_cliente_id integer;
BEGIN
    SELECT soggetto_id, utility_id, soggetto_ruolo_id,
           articolo_id, uom_id, tipo_doc_fiscale_id, valuta_id
      INTO v_soggetto_id, v_utility_id, v_soggetto_ruolo_id,
           v_articolo_id, v_uom_id, v_tipo_doc_id, v_valuta_id
      FROM tmp_refs_guard_parent;

    -- Categoria cliente: `billing_account.categoria_cliente_id` e' diventata
    -- NOT NULL dopo la scrittura di questo file. Si prende per CODICE INTERNO e
    -- non con un LIMIT 1: fra le categorie ci sono anche residui di smoke test
    -- disattivati, e un LIMIT senza ORDER BY non verifica, scommette.
    SELECT id INTO v_categoria_cliente_id
      FROM anagrafiche.categorie_clienti
     WHERE codice_interno = 'STANDARD';

    -- ⭐ FINESTRA DIFFERITA. Un'istanza utility non e' un INSERT, e' una SAGA:
    --   `trg_istanze_utilities_z90_require_utility_dichiarata_ins` e' un
    --   CONSTRAINT TRIGGER DEFERRABLE INITIALLY DEFERRED che al COMMIT pretende
    --   almeno un satellite (BA, dati precontrattuali o cliente) — un'istanza
    --   senza satellite non e' uno stato legale del modello. Il preambolo
    --   obbligatorio (SET CONSTRAINTS ALL IMMEDIATE) lo fa scattare sul PRIMO
    --   insert, cioe' prima che i tre BA qui sotto possano esistere: e' li' che
    --   questo file moriva, con ZERO asserzioni eseguite.
    --   Si apre la finestra, si costruiscono le istanze CON i loro BA, e si
    --   RICHIUDE: la verifica non si perde, si sposta dove il modello la vuole.
    SET CONSTRAINTS ALL DEFERRED;

    -- Crea 3 istanze per lo stesso soggetto
    INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
    VALUES (v_soggetto_id, true, 'TST-GUARD-PARENT-IU-01')
    RETURNING id INTO v_parent_istanza_id;

    INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
    VALUES (v_soggetto_id, true, 'TST-GUARD-PARENT-IU-02')
    RETURNING id INTO v_child1_istanza_id;

    INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
    VALUES (v_soggetto_id, true, 'TST-GUARD-PARENT-IU-03')
    RETURNING id INTO v_child2_istanza_id;

    -- BA padre (stand-alone)
    INSERT INTO anagrafiche.billing_account (
        istanza_utility_id, soggetto_ruolo_id, utility_id, valido_dal,
        categoria_cliente_id
    ) VALUES (
        v_parent_istanza_id, v_soggetto_ruolo_id, v_utility_id, script.fn_data_operativa(),
        v_categoria_cliente_id
    ) RETURNING id INTO v_parent_ba_id;

    -- BA figlio 1 (con parent, avra attivita_fatturabili)
    INSERT INTO anagrafiche.billing_account (
        istanza_utility_id, soggetto_ruolo_id, utility_id, parent_account_id, valido_dal,
        categoria_cliente_id
    ) VALUES (
        v_child1_istanza_id, v_soggetto_ruolo_id, v_utility_id, v_parent_ba_id, script.fn_data_operativa(),
        v_categoria_cliente_id
    ) RETURNING id INTO v_child1_ba_id;

    -- BA figlio 2 (con parent, senza attivita)
    INSERT INTO anagrafiche.billing_account (
        istanza_utility_id, soggetto_ruolo_id, utility_id, parent_account_id, valido_dal,
        categoria_cliente_id
    ) VALUES (
        v_child2_istanza_id, v_soggetto_ruolo_id, v_utility_id, v_parent_ba_id, script.fn_data_operativa(),
        v_categoria_cliente_id
    ) RETURNING id INTO v_child2_ba_id;

    -- Saga completa: ogni istanza ha il suo BA, il guard differito scatta QUI e
    -- le trova finite.
    SET CONSTRAINTS ALL IMMEDIATE;

    -- Commessa per BA figlio 1
    -- ⚠️ L'emittente NON si lascia a NULL. `vendite.commesse` ha una policy
    --   RLS (rls_commesse_ef_whitelist) il cui WITH CHECK passa da
    --   `script.fn_scope_ef_whitelist_via_sr(utente, emittente_soggetto_ruolo_id)`:
    --   con la colonna vuota la scrittura viene NEGATA, e il file moriva qui.
    --   L'helper da' il soggetto_ruolo dell'emittente su cui l'operatore del
    --   contesto puo' davvero scrivere: la scelta di «quale emittente» resta in
    --   un posto solo.
    INSERT INTO vendite.commesse (
        codice, billing_account_id, utility_id, emittente_soggetto_ruolo_id
    ) VALUES (
        'TST-GUARD-PARENT-COMM-01', v_child1_ba_id, v_utility_id,
        script.fn_pgtap_emittente_sr_operatore()
    ) RETURNING id INTO v_commessa_id;

    -- Commessa attivita. -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
    INSERT INTO vendite.commesse_attivita (
        commessa_id, segment_key, articolo_id, istanza_utility_id,
        data_attivita, uom_id, quantita,
        competenza_mese, competenza_dal, competenza_al,
        prezzo_snapshot, tipo_doc_fiscale_id, valuta_id,
        sorgente_tipo_id, sorgente_uid
    ) VALUES (
        v_commessa_id, 'TST-SEG-01', v_articolo_id, v_child1_istanza_id,
        script.fn_data_operativa(), v_uom_id, 1,
        date_trunc('month', script.fn_data_operativa())::date,
        date_trunc('month', script.fn_data_operativa())::date,
        (date_trunc('month', script.fn_data_operativa()) + interval '1 month - 1 day')::date,
        10.00, v_tipo_doc_id, v_valuta_id,
        (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'), v_commessa_id::text
    ) RETURNING id INTO v_commessa_attivita_id;

    -- Attivita fatturabili (NON fatturata) per BA figlio 1
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id, billing_account_id, istanza_utility_id,
        data_attivita, quantita,
        competenza_mese, competenza_dal, competenza_al,
        commessa_id, commessa_attivita_id,
        tipo_doc_fiscale_id, valuta_id,
        approvato
    ) VALUES (
        v_articolo_id, v_child1_ba_id, v_child1_istanza_id,
        script.fn_data_operativa(), 1,
        date_trunc('month', script.fn_data_operativa())::date,
        date_trunc('month', script.fn_data_operativa())::date,
        (date_trunc('month', script.fn_data_operativa()) + interval '1 month - 1 day')::date,
        v_commessa_id, v_commessa_attivita_id,
        v_tipo_doc_id, v_valuta_id,
        false
    );

    -- Salva gli ID per i test successivi
    INSERT INTO tmp_ids_guard (parent_ba_id, child1_ba_id, child2_ba_id)
    VALUES (v_parent_ba_id, v_child1_ba_id, v_child2_ba_id);
END;
$$;

SELECT ok(
    (SELECT count(*) FROM tmp_ids_guard) = 1,
    'Setup: BA padre + 2 figli + commessa + attivita creati'
);

-- =========================================================
-- 2) Verifica: BA figlio 1 ha attivita non fatturate
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
        FROM vendite.attivita_fatturabili af
        WHERE af.billing_account_id = (SELECT child1_ba_id FROM tmp_ids_guard)
          AND af.fatturato IS FALSE
    ),
    'BA figlio 1 ha attivita non fatturate'
);

-- =========================================================
-- 3) DB-02: rimozione parent con attivita non fatturate → FALLISCE
-- =========================================================
SELECT throws_ok(
    $$
      UPDATE anagrafiche.billing_account
         SET parent_account_id = NULL
       WHERE id = (SELECT child1_ba_id FROM tmp_ids_guard);
    $$,
    NULL,
    'Rimozione parent_account_id con attivita non fatturate: FALLISCE'
);

-- =========================================================
-- 4) Verifica: parent_account_id e' ancora presente (non e' stato rimosso)
-- =========================================================
SELECT ok(
    (SELECT parent_account_id IS NOT NULL
       FROM anagrafiche.billing_account
      WHERE id = (SELECT child1_ba_id FROM tmp_ids_guard)),
    'parent_account_id ancora presente dopo tentativo di rimozione fallito'
);

-- =========================================================
-- 5) DB-03: rimozione parent senza attivita → OK
-- =========================================================
SELECT lives_ok(
    $$
      UPDATE anagrafiche.billing_account
         SET parent_account_id = NULL
       WHERE id = (SELECT child2_ba_id FROM tmp_ids_guard);
    $$,
    'Rimozione parent_account_id senza attivita: OK'
);

-- =========================================================
-- 6) Dopo fatturazione, rimozione parent → OK
-- =========================================================
-- ⛔ rev 2026-08-26 — «marcare come fatturate» non e' piu' possibile.
--   Dal changeSet 20260826-33 `fatturato` e' una colonna GENERATA su
--   `fattura_riga_id IS NOT NULL`: il timbro non si SCRIVE, si OTTIENE
--   agganciando l'attivita' a una riga di fattura vera.
--   ⭐ E la fixture ci guadagna. Prima diceva «fatturata» a un'attivita' che
--   nessuna fattura conteneva — cioe' costruiva proprio lo stato incoerente
--   che il cantiere brief-db-lavoro-che-non-torna-indietro ha reso
--   impossibile, e su cui il guard qui sotto veniva interrogato. Adesso la
--   fattura c'e', e la domanda che il test pone e' quella vera.
-- ⚠️ La fatturazione e' SETUP e sta FUORI dal lives_ok: il test 6 asserisce
--   che il parent si stacchi, non che si riesca a fatturare.
DO $fatt$
DECLARE
    v_fattura_id bigint;
    v_riga_id    bigint;
BEGIN
-- ⚠️ utility_id dal BA, come la testata vera (fn_get_or_create_fattura_header):
--   una fattura senza utility l'applicazione non la crea, e dal 20261021-15 le sue
--   righe senza regole dell'articolo non hanno parametri d'importo
--   (brief-db-modelli-documento-standard §10.7 R-3).
    INSERT INTO vendite.fatture (
        registro_id, emittente_soggetto_ruolo_id, billing_account_id,
        tipo_doc_fiscale_id, valuta_id, stato_doc_fiscale_id, data, utility_id)
    SELECT script.fn_pgtap_registro_fattura(script.fn_pgtap_emittente_sr_operatore()),
           script.fn_pgtap_emittente_sr_operatore(),
           af.billing_account_id, af.tipo_doc_fiscale_id, af.valuta_id,
           (SELECT s.id FROM config.stati_doc_fiscale s
             WHERE s.codice_interno = 'DRAFT' ORDER BY s.id LIMIT 1),
           script.fn_data_operativa(),
           (SELECT ba.utility_id FROM anagrafiche.billing_account ba WHERE ba.id = af.billing_account_id)
      FROM vendite.attivita_fatturabili af
     WHERE af.billing_account_id = (SELECT child1_ba_id FROM tmp_ids_guard)
     ORDER BY af.id
     LIMIT 1
    RETURNING id INTO v_fattura_id;

    INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione,
                                       qta, prezzo_unitario, imponibile_riga, competenza_dal, competenza_al)
    VALUES (v_fattura_id, 1, 'Riga PGTAP guard parent', 1, 10, 10, script.fn_data_operativa(), script.fn_data_operativa())
    RETURNING id INTO v_riga_id;

    UPDATE vendite.attivita_fatturabili
       SET fattura_riga_id = v_riga_id
     WHERE billing_account_id = (SELECT child1_ba_id FROM tmp_ids_guard);
END
$fatt$;

SELECT lives_ok(
    $$
      UPDATE anagrafiche.billing_account
         SET parent_account_id = NULL
       WHERE id = (SELECT child1_ba_id FROM tmp_ids_guard);
    $$,
    'Rimozione parent_account_id dopo fatturazione attivita: OK'
);

-- ⚠️ Si smonta subito, e non e' pignoleria: il cleanup finale CANCELLA le
--   attivita', e dal changeSet 20260826-26 la chiave esterna verso la riga di
--   fattura e' NO ACTION — piu' il guard di riga che rifiuta di toccare
--   un'attivita' ancora agganciata. Sganciare qui tiene il cleanup semplice
--   invece di fargli aggirare il muro con la GUC di manutenzione.
DO $smonta$
DECLARE
    v_fattura_id bigint;
BEGIN
    SELECT f.id INTO v_fattura_id
      FROM vendite.fatture f
     WHERE f.billing_account_id = (SELECT child1_ba_id FROM tmp_ids_guard)
     ORDER BY f.id DESC
     LIMIT 1;

    IF v_fattura_id IS NULL THEN
        RETURN;
    END IF;

    PERFORM set_config('zeroerp.maintenance_reset_lotto_draft', 'on', true);
    UPDATE vendite.attivita_fatturabili
       SET fattura_riga_id = NULL
     WHERE fattura_riga_id IN (SELECT fr.id FROM vendite.fatture_righe fr
                                WHERE fr.fattura_id = v_fattura_id);
    PERFORM set_config('zeroerp.maintenance_reset_lotto_draft', 'off', true);

    DELETE FROM vendite.fatture_righe WHERE fattura_id = v_fattura_id;
    DELETE FROM vendite.fatture       WHERE id = v_fattura_id;
END
$smonta$;

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
    DELETE FROM vendite.attivita_fatturabili af
    WHERE af.commessa_id IN (
        SELECT c.id FROM vendite.commesse c WHERE c.codice = 'TST-GUARD-PARENT-COMM-01'
    );

    DELETE FROM vendite.commesse_attivita ca
    WHERE ca.commessa_id IN (
        SELECT c.id FROM vendite.commesse c WHERE c.codice = 'TST-GUARD-PARENT-COMM-01'
    );

    DELETE FROM vendite.commesse c
    WHERE c.codice = 'TST-GUARD-PARENT-COMM-01';

    -- ⚠️ Prima il legame con l'emittente, poi il BA. Ogni billing account viene
    --   agganciato a un emittente fiscale da
    --   `trg_billing_account_z90_link_ef_ins`, e dal 2026-08-19 quel legame ha
    --   una FK verso il BA (`fk_emittenti_fiscali_billing_account_ba`,
    --   changeSet 20260819-04): senza questa DELETE la cancellazione del BA
    --   viola la chiave esterna e il file muore prima di finish().
    DELETE FROM anagrafiche.emittenti_fiscali_billing_account efba
    WHERE efba.billing_account_id IN (
        SELECT ba.id FROM anagrafiche.billing_account ba
        WHERE ba.istanza_utility_id IN (
            SELECT iu.id FROM anagrafiche.istanze_utilities iu
            WHERE iu.codice LIKE 'TST-GUARD-PARENT-%'
        )
    );

    DELETE FROM anagrafiche.billing_account ba
    WHERE ba.istanza_utility_id IN (
        SELECT iu.id FROM anagrafiche.istanze_utilities iu
        WHERE iu.codice LIKE 'TST-GUARD-PARENT-%'
    );

    DELETE FROM anagrafiche.istanze_utilities iu
    WHERE iu.codice LIKE 'TST-GUARD-PARENT-%';

    SET CONSTRAINTS ALL IMMEDIATE;
END;
$$;

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
