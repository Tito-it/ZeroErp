-- ---------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: creazione soggetto "Banca Zero" come ISTITUTO DI CREDITO
--       + inserimento di una filiale in anagrafiche.bank_branches
-- ------------------------------------------------------------

-- ============================================================================
-- rev 2026-08-18 — bonifica baseline. Il file era NON TRANSAZIONALE: apriva la
-- transazione a meta' e chiudeva in COMMIT, quindi lasciava il soggetto nel
-- database. Alla corsa dopo una «pulizia preventiva» in testa cercava di
-- cancellarlo — e da quando anagrafiche.bank_branches e' fra le tabelle di
-- dbops.automation_delete_block_ruoli (2026-01-23) quel DELETE non e' piu'
-- permesso. Risultato: il file moriva alla riga 44, ZERO asserzioni eseguite.
--
-- ⭐ Il rimedio non e' cancellare il residuo — sotto i residui di anagrafiche
-- ci sono 37 istanze utility e 16 clienti, e non e' roba da cancellare per far
-- passare un test. E' togliere al test il BISOGNO di cancellare:
--   1. BEGIN ... ROLLBACK, e la pulizia preventiva sparisce (il ROLLBACK e' la
--      garanzia: comunque vada, questo file non lascia nulla dietro di se');
--   2. una P.IVA NUOVA, valida e mai usata. Il vincolo che faceva collidere le
--      corse e' uq_soggetto_idstato_id_fiscale_univoco, e il vecchio
--      05555555555 e' bruciato da «Banca Zero Test pgTAP» del 2025-11-25, che
--      resta li' e da oggi non da' piu' fastidio a nessuno.
-- ============================================================================
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(4);

-- =========================================================
-- Costanti per il test (TEMP TABLE)
-- =========================================================
CREATE TEMP TABLE tmp_costanti_banca_zero AS
SELECT
    '88800100005'::text      AS piva_test,              -- P.IVA fittizia valida e mai usata (rev 2026-08-18)
    'BANK_B'::varchar        AS codice_ruolo_istituto,  -- config.tipi_ruoli.codice_interno (da adattare)
    'EUR'::varchar           AS codice_valuta,          -- se servirà in futuro
    'ZEROERP'::varchar       AS codice_prod_software,   -- se servirà in futuro
    '03069'::varchar         AS bank_code_test,         -- es. ABI fittizio
    '01234'::varchar         AS branch_code_test,       -- es. CAB fittizio
    'BZEROIT2XXX'::varchar   AS bic_swift_test;         -- BIC/SWIFT fittizio 8+3



-- ---------------------------------------------------------
-- 1) Inserimento soggetto "Banca Zero Test pgTAP"
-- ---------------------------------------------------------
-- ⭐ FINESTRA DIFFERITA (rev 2026-08-18) — e' il punto che teneva rosso il file.
--   Su anagrafiche.soggetti ci sono TRE guard DEFERRABLE INITIALLY DEFERRED
--   (dati societari, indirizzi, contatti richiesti). Sono differiti APPOSTA:
--   un soggetto si costruisce come SAGA — testata, dati societari, indirizzo,
--   contatto — e la completezza ha senso verificarla quando la saga e' finita,
--   non dopo il primo INSERT.
--   Il `SET CONSTRAINTS ALL IMMEDIATE` del preambolo obbligatorio li fa pero'
--   scattare subito, cioe' prima che la saga possa esistere. Qui si riaprono
--   per il tempo della costruzione e si richiudono sotto: la verifica NON si
--   perde, si sposta dove il modello la vuole. ⚠️ La richiusura non e'
--   facoltativa: senza, il ROLLBACK finale se li porterebbe via non verificati
--   e il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL DEFERRED;

WITH nuovo_soggetto AS (
    INSERT INTO anagrafiche.soggetti (
        ragione_sociale,
        cognome,
        nome,
        sesso,
        stato_id,
        partita_iva,
        -- rev 2026-08-18: il codice fiscale non c'era. Per una societa' di
        -- capitali trgfn_soggetti_guard_cf_piva_obbligatori lo pretende, e
        -- per una PG coincide con la partita IVA.
        codice_fiscale,
        tipo_soggetto_dettaglio_id,
        storicizza,
        attivo
    )
    SELECT
        'Banca Zero Test pgTAP',
        NULL,
        NULL,
        -- una societa' non ha sesso (sesso_policy NONE); era 'S', fuori
        --   vocabolario dal 2026-10-09 (brief-db-sesso-senza-default)
        NULL,
        1,                 -- stato_id IT (adatta se diverso)
        k.piva_test,
        k.piva_test,
        3,                 -- tipo_soggetto_dettaglio_id (PG IT, adatta se diverso)
        TRUE,
        TRUE
    FROM tmp_costanti_banca_zero k
    RETURNING id, codice
)
SELECT *
INTO TEMP TABLE tmp_soggetto_banca
FROM nuovo_soggetto;

-- Test 1: soggetto inserito
SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto_banca),
    1,
    'Inserito esattamente 1 soggetto di tipo Banca Zero'
);

-- Contatto minimo per il soggetto
INSERT INTO anagrafiche.contatti (
    tipo_contatto_id,
    soggetto_id,
    nominativo,
    email,
    is_default,
    default_context
)
VALUES (
    1,  -- TODO: tipo_contatto_id valido da config.tipi_contatti
    (SELECT id FROM tmp_soggetto_banca),
    'Referente Banca Zero Test pgTAP',
    'bancazero.pgtap@example.com',
    TRUE,
    'soggetto'
);

-- ---------------------------------------------------------
-- 1-bis) Dati societari (rev 2026-08-18)
--
-- Una societa' di capitali senza riga in anagrafiche.dati_societari non e' piu'
-- ammessa: la policy la pretende. Quando questo file e' stato scritto non
-- esisteva, ed e' il terzo dei guard entrati dopo che lo tenevano rosso.
-- ---------------------------------------------------------
-- ⭐ Rev 20261011 (brief-db-dati-fiscali-e-societari-del-soggetto, B-5): dal
--   20261011-04 l'app non scrive la tabella, si passa dal verbo; la forma e'
--   NOT NULL e ammessa dalla natura (SC -> SRL, C-1, C-2).
SELECT anagrafiche.fn_scrivi_dati_societari(
           p_soggetto_id        := s.id,
           p_forma_giuridica_id := (SELECT fg.id FROM config.forme_giuridiche fg WHERE fg.codice = 'SRL'),
           p_id_prov_iscri_rea  := (SELECT p.id FROM config.province p ORDER BY p.id LIMIT 1),
           p_iscrizione_rea     := 'REA-PGTAP-01',
           p_capitale_sociale   := 10000.00,
           p_socio_unico        := 'SM',
           p_liquidazione       := 'LN',
           p_destinatario_fe    := NULL,   -- nessun canale FE (D-6, 20261010-37)
           p_pec_fatturazione   := NULL,
           p_codice_sdi         := NULL,
           p_data_costituzione  := NULL)
  FROM tmp_soggetto_banca s;

-- Indirizzi obbligatori del SOGGETTO, in forma libera: la forma la sceglie
-- dallo stato il guard anagrafiche.trgfn_indirizzi_guard_forma_libera (rev
-- 2026-10-18: l'Italia vuole comune e CAP del catalogo; li da'
-- dbops.fn_pgtap_indirizzo_libero_forma). Stessa forma di create-cliente.sql.
INSERT INTO anagrafiche.indirizzi_soggetti (
    soggetto_id, tipo_indirizzo_id,
    indirizzo_libero, stato_id, comune_id, codice_postale_id, locality, postal_code
)
-- ⚠️ I tipi ammessi li decide config.tipi_soggetto_dettaglio_tipi_indirizzo
--   per il tipo_soggetto_dettaglio del soggetto (qui 3 = PG IT), NON la
--   matrice dei ruoli: 'RES' e' un tipo da persona fisica e su una PG viene
--   respinto. Si legge la matrice invece di elencare i codici a mano, cosi'
--   il test segue la configurazione se cambia.
SELECT s.id, m.tipo_indirizzo_id,
       'Via pgTAP Banca Zero 1', 1, f.comune_id, f.codice_postale_id, f.locality, f.postal_code
  FROM tmp_soggetto_banca s
 CROSS JOIN dbops.fn_pgtap_indirizzo_libero_forma(1) f
  JOIN config.tipi_soggetto_dettaglio_tipi_indirizzo m
    ON m.tipo_soggetto_dettaglio_id = 3 AND m.attivo
  JOIN config.tipi_indirizzi ti ON ti.id = m.tipo_indirizzo_id
 WHERE ti.codice_interno IN ('DOMFISC', 'SEDELEG');

-- Saga completa: si richiude la finestra. I tre guard differiti scattano QUI,
-- su un soggetto finito — ed e' esattamente la verifica che il modello vuole.
SET CONSTRAINTS ALL IMMEDIATE;

-- ---------------------------------------------------------
-- 2) Assegnazione ruolo ISTITUTO_CREDITO (es. codice 'IC')
--    tramite fn_get_or_create_soggetto_ruolo
-- ---------------------------------------------------------
WITH soggetto_ruolo_istituto AS (
    SELECT
        script.fn_get_or_create_soggetto_ruolo(
            p_soggetto_id   := s.id,
            p_cd_int_ruolo  := k.codice_ruolo_istituto
        ) AS id
    FROM tmp_soggetto_banca s,
         tmp_costanti_banca_zero k
)
SELECT id
INTO TEMP TABLE tmp_soggetto_ruolo_istituto
FROM soggetto_ruolo_istituto;

-- Test 2: ruolo istituto di credito assegnato
SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto_ruolo_istituto),
    1,
    'Assegnato esattamente 1 ruolo ISTITUTO_CREDITO al soggetto Banca Zero'
);

-- ---------------------------------------------------------
-- 3) Inserimento filiale in anagrafiche.bank_branches
-- ---------------------------------------------------------
WITH ins_filiale AS (
    INSERT INTO anagrafiche.bank_branches (
        soggetto_ruolo_id,
        bank_code,
        branch_code,
        bic_swift,
        name
    )
    SELECT
        sr.id,
        k.bank_code_test,
        k.branch_code_test,
        k.bic_swift_test,
        'Banca Zero - Filiale Test pgTAP'
    FROM tmp_soggetto_ruolo_istituto sr,
         tmp_costanti_banca_zero k
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_bank_branch
FROM ins_filiale;

-- Test 3: filiale inserita
SELECT is(
    (SELECT count(*)::int FROM tmp_bank_branch),
    1,
    'Inserita esattamente 1 filiale in anagrafiche.bank_branches per Banca Zero'
);

-- Test 4: verifica base su bank_code/branch_code e attivo
SELECT ok(
    EXISTS (
        SELECT 1
        FROM anagrafiche.bank_branches bb
        JOIN tmp_bank_branch tbb ON bb.id = tbb.id
        JOIN tmp_costanti_banca_zero k ON TRUE
        WHERE bb.bank_code   = k.bank_code_test
          AND bb.branch_code = k.branch_code_test
          AND bb.attivo      = TRUE
    ),
    'La filiale ha bank_code/branch_code attesi ed è attiva'
);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'.
-- ⚠️ finish() sta PRIMA: pgTAP tiene il suo stato in una temp table, e dopo il
-- ROLLBACK non esiste piu' («la relazione __tcache__ non esiste»).
ROLLBACK;

-- (Opzionale) pulizia della temp table, non strettamente necessaria
-- DROP TABLE IF EXISTS tmp_costanti_banca_zero;

