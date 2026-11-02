-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: catalogo.trgfn_articoli_componenti_guard_iva — copertura RIATTIVAZIONE.
-- Riferimento: migration 20260603-01 (corpo) + 20260603-02 (binding
--   INSERT OR UPDATE OF attivo).
--
-- Contesto:
--   L'invariante "BoM attiva => IVA padre = IVA figlio" e' garantito alla
--   sorgente. Prima del 2026-06-03 la guardia era solo-INSERT e guard B
--   (trgfn_articoli_guard_iva_bom_attiva) filtra ac.attivo=TRUE, lasciando
--   scoperto il percorso: spegni legame -> cambia IVA padre -> riaccendi.
--   Ora la guardia ricontrolla l'IVA quando il legame (ri)diventa attivo.
--
-- Indice test (1..5):
--   1. Setup: articoli + legame coerente creato (INSERT guard IVA passa)
--   2. Deattivazione legame (attivo=FALSE) -> OK
--   3. Cambio IVA padre con legame spento -> OK (guard B ignora i legami spenti)
--   4. Riattivazione legame in stato incoerente -> raise E_BOM_IVA_DISCORDANTE  [FIX]
--   5. Ripristino IVA coerente + riattivazione -> OK (controllo)
--
-- Fixture: crea due articoli dedicati (padre composito + figlio) con stessa
-- IVA (iva_a), li lega, poi manipola attivo/iva. Due aliquote distinte
-- (iva_a, iva_b) richieste. BEGIN + ROLLBACK isolamento completo.
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

SELECT plan(5);

-- =========================================================
-- Setup: riferimenti seed + due aliquote IVA distinte
-- =========================================================
CREATE TEMP TABLE _seed AS
SELECT
    (SELECT id FROM catalogo.unita_misura     WHERE attivo IS TRUE ORDER BY id LIMIT 1)          AS uom_id,
    (SELECT id FROM vendite.articoli_tipologie WHERE attivo IS TRUE ORDER BY id LIMIT 1)         AS tipo_id,
    (SELECT id FROM vendite.articoli_gruppi    WHERE attivo IS TRUE ORDER BY id LIMIT 1)         AS gruppo_id,
    (SELECT id FROM vendite.articoli_spesa     WHERE attivo IS TRUE ORDER BY id LIMIT 1)         AS spesa_id,
    (SELECT id FROM config.iva                 WHERE attivo IS TRUE ORDER BY id LIMIT 1)         AS iva_a,
    (SELECT id FROM config.iva                 WHERE attivo IS TRUE ORDER BY id OFFSET 1 LIMIT 1) AS iva_b;

-- Guard prerequisiti: senza i seed o due IVA distinte il test non e' eseguibile.
DO $g$
BEGIN
    IF (SELECT uom_id IS NULL OR tipo_id IS NULL OR gruppo_id IS NULL
               OR spesa_id IS NULL OR iva_a IS NULL OR iva_b IS NULL
               OR iva_a = iva_b
          FROM _seed) THEN
        RAISE EXCEPTION 'Prerequisiti mancanti (uom/tipo/gruppo/spesa o due IVA distinte): impossibile eseguire test.';
    END IF;
END
$g$;

-- Crea padre composito + figlio con stessa IVA (iva_a) e li lega.
-- L'INSERT del legame attraversa la guardia IVA su INSERT: se padre!=figlio
-- fallirebbe qui. Coerente per costruzione.
CREATE TEMP TABLE _art (prodotto_id uuid, componente_id uuid, link_id uuid);

DO $c$
DECLARE
    v_p  uuid;
    v_f  uuid;
    v_l  uuid;
    v_ts text := to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS');
BEGIN
    INSERT INTO catalogo.articoli (
        codice, descrizione, uom_id, tipo_voce_id, gruppo_voce_id, spesa_id, iva_id, is_composito
    )
    SELECT 'ART_IVAREACT_PAD_' || v_ts, 'Padre composito test riattivazione IVA',
           uom_id, tipo_id, gruppo_id, spesa_id, iva_a, TRUE
      FROM _seed
    RETURNING id INTO v_p;

    INSERT INTO catalogo.articoli (
        codice, descrizione, uom_id, tipo_voce_id, gruppo_voce_id, spesa_id, iva_id
    )
    SELECT 'ART_IVAREACT_FIG_' || v_ts, 'Figlio test riattivazione IVA',
           uom_id, tipo_id, gruppo_id, spesa_id, iva_a
      FROM _seed
    RETURNING id INTO v_f;

    INSERT INTO catalogo.articoli_componenti (
        prodotto_id, componente_id, coeff_qta, obbligatorio,
        valido_dal, valido_al, attivo
    )
    VALUES (
        v_p, v_f, 1, TRUE,
        (script.fn_data_operativa() - INTERVAL '1 day')::date, NULL, TRUE
    )
    RETURNING id INTO v_l;

    INSERT INTO _art (prodotto_id, componente_id, link_id) VALUES (v_p, v_f, v_l);
END
$c$;

-- =========================================================
-- 1) Setup riuscito: legame coerente creato (INSERT guard IVA passa)
-- =========================================================
SELECT ok(
    (SELECT link_id IS NOT NULL FROM _art),
    '1. Setup: articoli + legame coerente creato (INSERT guard IVA passa)'
);

-- =========================================================
-- 2) Deattivazione legame -> OK
-- =========================================================
SELECT lives_ok(
    format(
        $sql$ UPDATE catalogo.articoli_componenti SET attivo = FALSE WHERE id = %L::uuid $sql$,
        (SELECT link_id FROM _art)
    ),
    '2. Deattivazione legame (attivo=FALSE) -> OK'
);

-- =========================================================
-- 3) Cambio IVA padre con legame spento -> OK
-- guard B (trgfn_articoli_guard_iva_bom_attiva) filtra ac.attivo=TRUE:
-- con il legame spento non vede incoerenza e lascia passare.
-- =========================================================
SELECT lives_ok(
    format(
        $sql$ UPDATE catalogo.articoli SET iva_id = %L WHERE id = %L::uuid $sql$,
        (SELECT iva_b FROM _seed),
        (SELECT prodotto_id FROM _art)
    ),
    '3. Cambio IVA padre con legame spento -> OK (guard B ignora i legami spenti)'
);

-- =========================================================
-- 4) Riattivazione legame in stato incoerente -> raise  [FIX 2026-06-03]
-- padre ora iva_b, figlio iva_a: riaccendere il legame deve essere bloccato
-- da trgfn_articoli_componenti_guard_iva (E_BOM_IVA_DISCORDANTE).
-- throws_like (non throws_ok generico): tutti i raise di fn_log_and_raise_error
-- condividono SQLSTATE P0001, quindi il codice errore non discrimina. Matchiamo
-- la frase stabile del messaggio 445 (config.messaggi_errore) per attribuire il
-- blocco proprio alla guardia IVA e non a un altro vincolo coincidente.
-- =========================================================
SELECT throws_like(
    format(
        $sql$ UPDATE catalogo.articoli_componenti SET attivo = TRUE WHERE id = %L::uuid $sql$,
        (SELECT link_id FROM _art)
    ),
    '%aliquote IVA di padre e figli BoM devono coincidere%',
    '4. Riattivazione legame incoerente -> raise E_BOM_IVA_DISCORDANTE (msg 445)'
);

-- =========================================================
-- 5) Ripristino IVA coerente + riattivazione -> OK (controllo)
-- Riporto il padre a iva_a (legame ancora spento: guard B passa), poi
-- riaccendo: padre=figlio=iva_a, la guardia non blocca.
-- =========================================================
UPDATE catalogo.articoli
   SET iva_id = (SELECT iva_a FROM _seed)
 WHERE id = (SELECT prodotto_id FROM _art);

SELECT lives_ok(
    format(
        $sql$ UPDATE catalogo.articoli_componenti SET attivo = TRUE WHERE id = %L::uuid $sql$,
        (SELECT link_id FROM _art)
    ),
    '5. Ripristino IVA coerente + riattivazione -> OK'
);

SELECT * FROM finish();
ROLLBACK;
