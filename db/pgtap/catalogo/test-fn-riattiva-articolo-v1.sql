-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: catalogo.fn_riattiva_articolo (Fase 7 BE 28-04-2026,
-- migration 20260428-08).
--
-- Pattern "padre prima, figli poi" + idempotenza.
-- Disattivazione bloccata da trigger esistente
-- trgfn_prevent_deactivate_if_children su 13+ relazioni figlie.
--
-- Setup: ART_TEST_BASE ha gia' figli attivi via seed
-- (articoli_uom_operativa.csv id 9002 attivo=true). Sfruttiamo quel
-- seed per scenario 1 (disattivazione bloccata). Per scenario 2/3
-- (riattivazione padre, figli inattivi) prima disattiviamo tutti i
-- figli noti via UPDATE ad-hoc + ROLLBACK ripristina il seed.
--
-- Indice test (1..6):
--   1. UPDATE attivo=false su articolo con figlio attivo -> raise con la
--      frase del ramo ATTIVE (trgfn_prevent_deactivate_if_children, figlia
--      con la colonna attivo)
--   2. fn_riattiva_articolo su articolo disattivato esegue senza errori
--   3. dopo (2): articolo padre attivo=true
--   4. dopo (2): figli (articoli_descrizioni_aggiuntive) restano attivo=false
--      (pattern "padre prima, figli poi")
--   5. fn_riattiva_articolo su UUID inesistente -> raise E_ARTICOLO_NOT_FOUND
--   6. fn_riattiva_articolo idempotente su articolo gia' attivo -> no error
--
-- 🔄 2026-11-10 — il figlio attivo e' una descrizione aggiuntiva, non piu' la
--   mappatura di base. La mappatura e' storia (brief-db-revisione-catalogo Q31):
--   articoli_uom_operativa e' in dbops.automazione_attivo_eccezioni e non blocca
--   piu' lo spegnimento dell'articolo. Serviva un figlio che lo blocca davvero.
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

SELECT plan(6);

-- =========================================================
-- Setup: 2 articoli rilevanti
-- =========================================================
-- 🔴 ARTICOLI PROPRI invece di ART_TEST_BASE / ART_TEST_FALLBACK — 2026-08-18.
--   Il file usava due articoli CONDIVISI del seed. `catalogo.articoli` ha oggi
--   **28 tabelle figlie guardate** da `prevent_deactivate_if_children`, e su un
--   articolo condiviso e di lunga vita quelle righe si accumulano: la
--   disattivazione del padre (passo centrale di questo test) era diventata
--   impossibile, e il file moriva.
--
--   ⚠️ Il commento qui sotto diceva «i figli noti per ART_TEST_BASE:
--   articoli_uom_operativa». Erano noti quando e' stato scritto. Un test che si
--   appoggia all'inventario dei figli di un oggetto condiviso ha una scadenza
--   che nessuno ha fissato.
--
--   ⭐ Il rimedio e' gia' in casa: sei test di questa cartella creano il proprio
--   articolo clonando i riferimenti da uno esistente, e sono tutti verdi. Qui
--   si fa lo stesso. Il file e' transazionale: gli articoli spariscono al
--   ROLLBACK, e con loro ogni figlio.
CREATE OR REPLACE FUNCTION pg_temp.mk_articolo(p_codice text)
RETURNS uuid AS $mk$
DECLARE v_id uuid;
BEGIN
    -- I riferimenti si CLONANO da un articolo esistente: cosi' la fixture non
    -- deve conoscere il dominio (tipo voce, gruppo, spesa, iva) ne' inseguirlo
    -- quando cambia. ORDER BY id: deterministico, non «il primo che capita».
    INSERT INTO catalogo.articoli (codice, descrizione, uom_id, tipo_voce_id,
                                   gruppo_voce_id, spesa_id, iva_id)
    SELECT p_codice, 'pgTAP riattiva articolo',
           a.uom_id, a.tipo_voce_id, a.gruppo_voce_id, a.spesa_id, a.iva_id
      FROM catalogo.articoli a ORDER BY a.id LIMIT 1
    RETURNING id INTO v_id;
    RETURN v_id;
END $mk$ LANGUAGE plpgsql;

CREATE TEMP TABLE _t_ctx AS
SELECT pg_temp.mk_articolo('PGTAP_RIATT_A') AS art_a,
       pg_temp.mk_articolo('PGTAP_RIATT_B') AS art_b;

-- ⭐ Un figlio attivo, uno solo e sappiamo quale: una descrizione aggiuntiva.
--   La mappatura di base che nasce dal trigger non conta piu': dal 2026-11-10
--   e' in eccezione (Q31), e non blocca lo spegnimento.
INSERT INTO vendite.articoli_descrizioni_aggiuntive (articolo_id, descrizione)
SELECT art_a, 'pgTAP riattiva articolo' FROM _t_ctx;

-- =========================================================
-- 1) Disattivazione bloccata da figlio attivo
-- L'articolo ha una descrizione aggiuntiva attiva.
--
-- ⭐ Il discriminante e' il RAMO: catalogo.articoli ha il ritiro (obsoleto_dal), quindi il guard
--    sceglie E_ATTIVO_BLOCK_SI_RITIRA e la sua frase: un articolo nominato da altre righe non si
--    spegne, si ritira (Q35 (c), brief-db-revisione-catalogo §16.6.6). I due rami delle tabelle
--    senza ritiro (E_ATTIVO_BLOCK_CHILDREN_ACTIVE ed _EXIST) li presidiano
--    db/pgtap/dbops/test-trgfn-prevent-deactivate-if-children-pdp.sql e
--    db/pgtap/vendite/test-registri-per-emittente-v1.sql (test 6).
-- ⛔ La frase NON nomina la figlia: le frasi della famiglia ATTIVO non nominano tabelle
--    (brief-db-revisione-dbops, S-BE-1). Quale tabella blocca sta nel contesto del diario.
--    Che la frase non porti nomi di tabelle lo presidia dbops/test-bersaglio-guard-attivo-v1.
-- =========================================================
SELECT throws_ok(
    format(
        $sql$ UPDATE catalogo.articoli SET attivo = false WHERE id = %L::uuid $sql$,
        (SELECT art_a FROM _t_ctx)
    ),
    'P0001',
    (SELECT m.messaggio FROM config.messaggi_errore m
      WHERE m.codice = 'E_ATTIVO_BLOCK_SI_RITIRA' AND m.lingua = 'it'),
    '1) UPDATE attivo=false con figlio attivo -> raise con la frase del ritiro (E_ATTIVO_BLOCK_SI_RITIRA)'
);

-- =========================================================
-- Setup scenario 2/3: disattivazione padre+figli ordinata
-- "Figli prima" (per superare il trigger), poi padre.
-- Il figlio noto: la descrizione aggiuntiva creata sopra.
-- =========================================================
UPDATE vendite.articoli_descrizioni_aggiuntive
   SET attivo = false
 WHERE articolo_id = (SELECT art_a FROM _t_ctx)
   AND attivo = true;

UPDATE catalogo.articoli
   SET attivo = false
 WHERE id = (SELECT art_a FROM _t_ctx);

-- =========================================================
-- 2) fn_riattiva_articolo: padre torna attivo
-- =========================================================
SELECT lives_ok(
    format(
        $sql$ SELECT catalogo.fn_riattiva_articolo(%L::uuid) $sql$,
        (SELECT art_a FROM _t_ctx)
    ),
    '2) fn_riattiva_articolo su articolo disattivato esegue senza errori'
);

SELECT is(
    (SELECT attivo FROM catalogo.articoli
      WHERE id = (SELECT art_a FROM _t_ctx)),
    true,
    '3) padre attivo=true dopo fn_riattiva_articolo'
);

-- =========================================================
-- 3) Figli rimangono inattivi (pattern padre prima, figli poi)
-- =========================================================
SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM vendite.articoli_descrizioni_aggiuntive
         WHERE articolo_id = (SELECT art_a FROM _t_ctx)
           AND attivo = true
    ),
    '4) Dopo fn_riattiva_articolo: figli (articoli_descrizioni_aggiuntive) restano attivo=false'
);

-- =========================================================
-- 4) UUID inesistente -> raise E_ARTICOLO_NOT_FOUND
-- =========================================================
SELECT throws_ok(
    $sql$ SELECT catalogo.fn_riattiva_articolo(gen_random_uuid()) $sql$,
    NULL, NULL,
    '5) fn_riattiva_articolo su UUID inesistente -> raise E_ARTICOLO_NOT_FOUND'
);

-- =========================================================
-- 5) Idempotente su articolo gia' attivo (ART_TEST_FALLBACK)
-- =========================================================
SELECT lives_ok(
    format(
        $sql$ SELECT catalogo.fn_riattiva_articolo(%L::uuid) $sql$,
        (SELECT art_b FROM _t_ctx)   -- ART_TEST_FALLBACK gia' attivo
    ),
    '6) fn_riattiva_articolo idempotente su articolo gia'' attivo -> no error'
);

SELECT * FROM finish();
ROLLBACK;
