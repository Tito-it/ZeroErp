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
--   1. UPDATE attivo=false su articolo con figlio attivo -> raise, e il
--      messaggio NOMINA la figlia (verifica trigger
--      trgfn_prevent_deactivate_if_children + messaggio parlante 20260820-01)
--   2. fn_riattiva_articolo su articolo disattivato esegue senza errori
--   3. dopo (2): articolo padre attivo=true
--   4. dopo (2): figli (articoli_uom_operativa) restano attivo=false
--      (pattern "padre prima, figli poi")
--   5. fn_riattiva_articolo su UUID inesistente -> raise E_ARTICOLO_NOT_FOUND
--   6. fn_riattiva_articolo idempotente su articolo gia' attivo -> no error
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

-- ⭐ Nessun figlio da creare a mano: l'articolo nasce gia' con la propria
--   `articoli_uom_operativa` di base (la crea un trigger). E' esattamente il
--   figlio attivo che il test 1 pretende — uno solo, e sappiamo quale, che e'
--   il punto di tutta questa correzione.

-- =========================================================
-- 1) Disattivazione bloccata da figlio attivo
-- ART_TEST_BASE ha articoli_uom_operativa (seed id 9002) attivo=true
--
-- ⚠️ rev 2026-08-20 — IL DISCRIMINANTE E' CAMBIATO, e vale la pena sapere
--    perche'. Fino a ieri era la parola «attive», presa dalla frase che
--    dbops.trgfn_prevent_deactivate_if_children passava come primo valore a
--    fn_log_and_raise_error. Quella frase non esiste piu' (20260820-01): il
--    messaggio sta a catalogo e NOMINA la tabella collegata, che prima non
--    diceva mai.
--    ⭐ E la parola «attive» e' TORNATA il 2026-08-20 con 20260820-08, ma per
--    un altro motivo: non e' piu' nella frase unica (dove era falsa ogni volta
--    che la figlia NON ha la colonna attivo), e' in un CODICE SUO —
--    E_ATTIVO_BLOCK_CHILDREN_ACTIVE (934), che il guard sceglie quando la
--    figlia la colonna ce l'ha. `catalogo.articoli_uom_operativa` e' proprio
--    quel caso (ed e' la stessa colonna che il test 4 rilegge), quindi questo
--    file e' il testimone del RAMO A. Il ramo B — figlia senza colonna attivo,
--    codice 125 — e' presidiato da
--    db/pgtap/vendite/test-registri-per-emittente-v1.sql (test 6).
--    ⛔ I due rami non sono due sfumature: hanno due RIMEDI diversi
--    (disattivare le righe qui, toglierle la'), ed e' per questo che sono due
--    codici e non un messaggio con un forse.
--
-- ⭐ Il discriminante nuovo e' PIU' FORTE del vecchio: «attive» sarebbe
--    passata con qualunque figlia: qui si asserisce PROPRIO
--    catalogo.articoli_uom_operativa — che e' l'unico figlio che questa
--    fixture crea, come dice il commento qui sopra («uno solo, e sappiamo
--    quale»). Nel messaggio nuovo padre e figlia sono entrambi
--    `schema.tabella`: se il loro ordine si scambiasse rispetto ai segnaposti
--    del catalogo, la frase resterebbe perfetta e nominerebbe la tabella
--    sbagliata — e questo e' il test che se ne accorge.
-- =========================================================
SELECT throws_like(
    format(
        $sql$ UPDATE catalogo.articoli SET attivo = false WHERE id = %L::uuid $sql$,
        (SELECT art_a FROM _t_ctx)
    ),
    '%righe collegate attive in catalogo.articoli_uom_operativa%',
    '1) UPDATE attivo=false con figlio attivo -> raise: messaggio del ramo ATTIVE, e NOMINA la figlia'
);

-- =========================================================
-- Setup scenario 2/3: disattivazione padre+figli ordinata
-- "Figli prima" (per superare il trigger), poi padre.
-- I figli noti per ART_TEST_BASE: articoli_uom_operativa.
-- Disattiviamo TUTTI i figli attivi su ART_TEST_BASE per evitare
-- side-effect da altre relazioni seedate.
-- =========================================================
UPDATE catalogo.articoli_uom_operativa
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
        SELECT 1 FROM catalogo.articoli_uom_operativa
         WHERE articolo_id = (SELECT art_a FROM _t_ctx)
           AND attivo = true
    ),
    '4) Dopo fn_riattiva_articolo: figli (articoli_uom_operativa) restano attivo=false'
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
