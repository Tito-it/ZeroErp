-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2025 Tid (Michele Carlo Titini)
--
-- Test: costruzione della catena cliente — soggetto, ruolo, istanza utility,
--       billing account, cliente — e coerenza dei suoi legami.
-- ------------------------------------------------------------
-- Indice test (1..8):
--   1) Trovato il ruolo CLIENTE in config.tipi_ruoli
--   2) Trovata l'utility di test in config.utilities
--   2-bis) Riferimenti risolti per codice: tipo soggetto e stato
--   3) Creato il soggetto (persona fisica privata, tipo PR), dal builder
--   4) Assegnato il ruolo cliente via script.fn_get_or_create_soggetto_ruolo
--   5) Inserita l'istanza utility (fittizia)
--   6) Inserito il billing account per quell'istanza
--   7) Inserito il cliente
--   8) I legami del cliente col billing account sono coerenti
-- ------------------------------------------------------------
-- ⚠️ RISCRITTO IL 2026-07-31: da fixture che COMMITTAVA a test in
--   BEGIN/ROLLBACK, come gli altri 140.
--
-- COS'ERA. Il file era un generatore di dati: creava un cliente di prova e lo
--   COMMITTAVA, e per essere rieseguibile apriva con cinque DELETE di pulizia.
--   Quelle DELETE hanno smesso di funzionare quando e' arrivato il guard
--   script.trgfn_delete_block_by_guc su anagrafiche.clienti (seed
--   automation_delete_block_ruoli, 2026-01-23): da allora il file moriva alla
--   prima istruzione con E_DELETE_NOT_ALLOWED, senza eseguire NESSUNA
--   asserzione — ed era la prima riga di db/pgtap/baseline-rossi.tsv,
--   classificato ERRORE_FIXTURE.
--
-- PERCHE' LA CURA NON E' LA GUC DI MANUTENZIONE. Si poteva sbloccare con
--   `SET zeroerp.maintenance_ruoli_delete = 'on'`, cioe' aggirare il guard.
--   Ma le DELETE esistevano SOLO perche' il file committava: in
--   BEGIN/ROLLBACK non serve pulire nulla, quindi il guard non viene nemmeno
--   sfiorato. Si toglie la causa invece di disinnescare il sintomo, e sparisce
--   anche il motivo per cui questo file era diverso da tutti gli altri.
--
-- ⚠️ IL DEBITO CHE QUESTA RISCRITTURA RENDE VISIBILE. Il soggetto storico con
--   CF di una persona vera di dev resta in tabella (non lo cancelliamo: vedi sotto),
--   ma da qui in avanti NESSUNO lo ricrea. Tre pgTAP lo cercano li' —
--   test-contatti-soggetto-cliente (oggi verde), test-risorse-umane e
--   soggetti-con-contatti (gia' rossi) — e oggi lo trovano solo perche' questo
--   file lo aveva committato tempo fa. Vanno resi autosufficienti: e' un debito
--   che questa riscrittura rende visibile, non uno che introduce. Un test che
--   dipende dai residui di un altro test e' verde per fortuna, non per
--   costruzione.
-- ------------------------------------------------------------
BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI — ⭐ QUI LA FINESTRA SI DICHIARA, NON SI PRESUME.
--   La fixture e' una SAGA: soggetto, poi contatto, poi indirizzi, poi ruolo,
--   poi l'indirizzo del ruolo — in istruzioni separate. I guard di
--   anagrafiche.soggetti e soggetti_ruoli sono constraint trigger DEFERRABLE
--   INITIALLY DEFERRED, e il SET CONSTRAINTS ALL IMMEDIATE di questo file sta
--   in fondo, «dove l'unita' di lavoro e' completa».
--   ⛔ Ma la riga di contesto qui sopra ESCE CON I VINCOLI IMMEDIATE (rev
--   20260921-18, come ogni helper pgTAP): fino al 21-09 lo faceva solo sul
--   database da zero, dove costruisce il mondo, e questo file — il PRIMO della
--   suite, l'unico a percorrere quel ramo — moriva in CI all'INSERT del
--   soggetto su «Indirizzo obbligatorio mancante … RES», verde su dev e da
--   solo. Contare sulla finestra di DEFAULT e' contare su cio' che nessuno ha
--   promesso: la si riapre, e il file dice da se' cosa vuole.
SET CONSTRAINTS ALL DEFERRED;

SELECT plan(8);

-- =========================================================
-- Costanti di test (CF e P.IVA li sceglie il builder del soggetto)
-- =========================================================
-- ⚠️ Niente id numerici indovinati: si risolve tutto per codice_interno.
-- Era la fragilita' di fondo di questo file — vedi il tipo soggetto qui sotto.
CREATE TEMP TABLE tmp_costanti_cc AS
SELECT 'CL'::varchar            AS codice_ruolo_cliente,  -- tipi_ruoli.codice_interno
       -- ⚠️ BASE e non GAS: GAS/ENERGIA/IDRICO hanno richiede_pdp = true e il
       --   guard pretende un punto di prelievo sul cliente. Questo file
       --   costruisce la CATENA cliente, non collauda le regole di una
       --   commodity: si sceglie l'utility che non aggiunge requisiti estranei.
       'BASE'::varchar          AS codice_utility_test,   -- utilities.codice_interno
       'PR'::varchar            AS codice_tipo_soggetto,  -- tipi_soggetto_dettaglio.codice_interno
       'STANDARD'::varchar      AS codice_categoria_cliente;  -- categorie_clienti.codice_interno

-- Tipo soggetto e stato, risolti e non ipotizzati.
-- ⚠️ `PR` = «Persona Fisica - Privato»: piva_obbligatoria = false,
--   cf_obbligatorio = true. Il file usava l'id 3 hardcoded, che e' `SC`
--   (Societa' di Capitali) e pretende la partita IVA — mentre l'INSERT la
--   teneva commentata. Da quando esiste il guard
--   trgfn_soggetti_guard_cf_piva_obbligatori, quella combinazione non passa
--   piu': persona fisica dichiarata societa'. Risolvere per codice_interno
--   rende l'incoerenza impossibile invece che solo corretta una volta.
CREATE TEMP TABLE tmp_rif_cc AS
SELECT (SELECT tsd.id FROM config.tipi_soggetto_dettaglio tsd, tmp_costanti_cc k
         WHERE tsd.codice_interno = k.codice_tipo_soggetto
           AND tsd.stato_iso2 = 'IT')                         AS tipo_soggetto_dettaglio_id,
       (SELECT st.id FROM config.stati st WHERE st.codice_iso2 = 'IT') AS stato_id,
       -- Aggiunta al billing account nell'aprile 2026 e diventata NOT NULL
       -- dopo: il file e' piu' vecchio della colonna e non la valorizzava.
       (SELECT cc.id FROM anagrafiche.categorie_clienti cc, tmp_costanti_cc k
         WHERE cc.codice_interno = k.codice_categoria_cliente
           AND cc.attivo)                                  AS categoria_cliente_id;

-- ---------------------------------------------------------
-- 1) Ruolo CLIENTE
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_ruolo_cliente AS
SELECT tr.id
  FROM config.tipi_ruoli tr, tmp_costanti_cc k
 WHERE tr.codice_interno = k.codice_ruolo_cliente;

SELECT is(
    (SELECT count(*)::int FROM tmp_ruolo_cliente),
    1,
    'Trovato esattamente 1 ruolo cliente (config.tipi_ruoli.codice_interno = CL)'
);

-- ---------------------------------------------------------
-- 2) Utility di test
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_utility AS
SELECT u.id
  FROM config.utilities u, tmp_costanti_cc k
 WHERE u.codice_interno = k.codice_utility_test;

SELECT is(
    (SELECT count(*)::int FROM tmp_utility),
    1,
    'Trovata esattamente 1 utility di test (config.utilities.codice_interno = BASE)'
);

-- ---------------------------------------------------------
-- 3) Soggetto (persona fisica)
-- ---------------------------------------------------------
-- ⚠️ Rev 2026-11-17 (brief-db-fornitore-privato-indirizzi §10.3): il privato
--   lo costruisce dbops.fn_pgtap_crea_soggetto_pf, gia' completo di contatto
--   e indirizzi obbligatori, dalle madri del dominio. Prima c'erano un INSERT
--   diretto su anagrafiche.soggetti, il contatto e gli indirizzi scritti a
--   mano (RES + DOMFISC, coi tipi elencati dal file): una seconda strada che
--   ricopiava la matrice della natura invece di leggerla. Qui il soggetto e'
--   il veicolo della catena, non l'oggetto del test. Il codice fiscale e'
--   libero (lo sceglie il builder): non contende piu' quello di nessuno.
--   Il builder esce coi vincoli IMMEDIATE: la saga del ruolo, che segue,
--   riapre la finestra.
CREATE TEMP TABLE tmp_soggetto AS
SELECT dbops.fn_pgtap_crea_soggetto_pf(
           p_cognome                    := 'Pgtap',
           p_nome                       := 'Cliente Test',
           p_tipo_soggetto_dettaglio_id := r.tipo_soggetto_dettaglio_id,
           p_stato_id                   := r.stato_id) AS id
  FROM tmp_rif_cc r;

SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto),
    1,
    'Creato esattamente 1 soggetto di test (PF), dal builder'
);

SET CONSTRAINTS ALL DEFERRED;

-- ---------------------------------------------------------
-- 4) Ruolo cliente sul soggetto (via funzione di dominio)
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_soggetto_ruolo AS
SELECT script.fn_get_or_create_soggetto_ruolo(
           p_soggetto_id  := s.id,
           p_cd_int_ruolo := k.codice_ruolo_cliente
       ) AS id
  FROM tmp_soggetto s, tmp_costanti_cc k;

SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto_ruolo),
    1,
    'Assegnato esattamente 1 ruolo cliente via script.fn_get_or_create_soggetto_ruolo'
);

-- Indirizzo obbligatorio del RUOLO cliente.
-- ⚠️ Serve ANCHE questo, oltre a quelli di soggetto: sono due guard distinti
--   su due matrici distinte. config.tipi_ruolo_tipi_indirizzo pretende FATT
--   per il ruolo CLIENTE, e trgfn_soggetti_ruoli_guard_indirizzi_required lo
--   cerca in anagrafiche.indirizzi — il layer RUOLO. Il suo fallback porta a
--   un altro TIPO (DOMFISC), non all'altro LAYER: un indirizzo di soggetto,
--   per quanto presente, non lo soddisfa.
INSERT INTO anagrafiche.indirizzi (
    soggetto_ruolo_id, tipo_indirizzo_id, istanza_utility_id,
    indirizzo_libero, stato_id, comune_id, codice_postale_id, locality, postal_code
)
SELECT sr.id, ti.id, NULL,
       'Via pgTAP create-cliente 2', r.stato_id, f.comune_id, f.codice_postale_id, f.locality, f.postal_code
  FROM tmp_soggetto_ruolo sr, tmp_rif_cc r, config.tipi_indirizzi ti,
       dbops.fn_pgtap_indirizzo_libero_forma(r.stato_id) f
 WHERE ti.codice_interno = 'FATT';

-- ---------------------------------------------------------
-- 5) Istanza utility (fittizia: nessun indirizzo di dettaglio)
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_istanza AS
WITH ins AS (
    INSERT INTO anagrafiche.istanze_utilities (
        fittizia, proprietario_inquilino, soggetto_id, indirizzo_dettaglio_id
    )
    SELECT TRUE, 'I', s.id, NULL
      FROM tmp_soggetto s
    RETURNING id
)
SELECT id FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_istanza),
    1,
    'Inserita esattamente 1 istanza_utility di test'
);

-- ---------------------------------------------------------
-- 6) Billing account per l'istanza (codice generato dal trigger)
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_billing_account AS
WITH ins AS (
    INSERT INTO anagrafiche.billing_account (
        istanza_utility_id, soggetto_ruolo_id, utility_id, codice,
        categoria_cliente_id
    )
    -- `codice` NULL di proposito: lo genera trgfn_billing_account_gen_codice.
    SELECT i.id, sr.id, u.id, NULL, r.categoria_cliente_id
      FROM tmp_istanza i, tmp_soggetto_ruolo sr, tmp_utility u, tmp_rif_cc r
    RETURNING id
)
SELECT id FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_billing_account),
    1,
    'Inserito esattamente 1 billing_account per l''istanza di test'
);

-- ---------------------------------------------------------
-- 7) Cliente
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_cliente AS
WITH stato AS (
    SELECT id FROM config.stati_cliente WHERE codice_interno = 'PR' LIMIT 1
), ins AS (
    INSERT INTO anagrafiche.clienti (
        soggetto_ruolo_id, istanza_utility_id, stato_cliente_id,
        billing_account_id,
        -- Nullable, ma il test 8 verifica proprio che coincida con quella del
        -- billing account: lasciarla NULL renderebbe ba_match_utility NULL e
        -- il test rosso per omissione invece che per incoerenza.
        utility_id
        -- ⚠️ rev 2026-08-29: via `iva_id` (e la CTE che la risolveva) e via la
        --   nota su `cliente_pa`: quelle colonne non esistono piu' su
        --   anagrafiche.clienti (changeSet 20260829-22). L'aliquota la decide la
        --   merce; i due flag di scissione sono saliti su anagrafiche.soggetti.
        -- (rev 2026-07-31: tipo_gg_scadenza_ft e nr_giorni_scadenza, che qui
        --  erano citate, non esistono piu' — D-I, piano satelliti 3a.5.)
    )
    SELECT sr.id, i.id, sc.id, ba.id, u.id
      FROM tmp_soggetto_ruolo sr, tmp_istanza i, stato sc,
           tmp_billing_account ba, tmp_utility u
    RETURNING id
)
SELECT id FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_cliente),
    1,
    'Inserito esattamente 1 cliente collegato a istanza, ruolo e billing_account'
);

-- ---------------------------------------------------------
-- 8) Coerenza dei legami cliente <-> billing account
-- ---------------------------------------------------------
SELECT is(
    (SELECT count(*)::int
       -- rev 2026-07-31: la vista e' stata rinominata in vw_* (20260402-06),
       -- il file puntava ancora al nome vecchio.
       FROM dbops.vw_diag_v_clienti_links v
      WHERE v.cliente_id IN (SELECT id FROM tmp_cliente)
        AND v.ba_match_istanza
        AND v.ba_match_soggetto_ruolo
        AND v.ba_match_utility),
    1,
    'Il cliente di test ha legami coerenti con billing_account (istanza, soggetto_ruolo, utility).'
);

-- Forza la valutazione dei constraint deferrable PRIMA del rollback:
-- senza, un vincolo violato passerebbe inosservato perche' nessuno commetta.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT * FROM finish();
ROLLBACK;
