-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: catalogo.vw_articoli_componenti_dettaglio campi capability
-- (Fase 2 BE 28-04-2026, migration 20260428-03).
--
-- Capability esposte:
--   puo_chiudersi          BOOLEAN  = (valido_al IS NULL)
--   data_min_chiusura      DATE     = GREATEST(valido_dal, script.fn_data_operativa() - 1)
--                                                    [NULL se non chiudibile]: la fine
--                                                    non cambia i giorni gia' passati
--   data_default_chiusura  DATE     = GREATEST(valido_dal, script.fn_data_operativa())
--                                                    [NULL se non chiudibile]
--   motivo_non_chiudibile  TEXT     = 'RIGA_GIA_CHIUSA' [NULL se chiudibile]
--
-- Nota decisione (28-04-2026 opzione i): attivo (true/false) e'
-- ortogonale a puo_chiudersi. La verifica e' code-review only sullo
-- SQL della vista (nessun riferimento ad ac.attivo nei CASE WHEN).
--
-- Setup: 3 righe BoM con validita' / couple disgiunti per evitare
-- overlap su ex_articoli_componenti_no_overlap. Le 2 righe con
-- valido_al NULL (aperta + futura) usano couple (prodotto, componente)
-- distinti: la futura ha un padre suo (PGT-BOMCAP-C), con lo stesso
-- componente. ROLLBACK finale.
-- 🔴 rev 2026-10-13 (brief-db-articoli-ammessi-per-documento D-4): prima la
--   riga futura SCAMBIAVA padre e componente (B dentro A, A dentro B: entrambi
--   compositi). Era un ciclo, e una distinta a due livelli: il guard
--   catalogo.trgfn_articoli_componenti_guard_un_livello (20261013-01) lo
--   rifiuta, perche' la distinta ha un livello solo. Il test misura le
--   capability della riga, non la coppia: basta un terzo padre.
--
-- Indice test (1..12):
--   Riga APERTA (BASE/FALLBACK, [oggi-30, +inf)):
--     1. puo_chiudersi          = true
--     2. data_min_chiusura      = ieri (valido_dal e' oggi-30)
--     3. data_default_chiusura  = oggi (GREATEST con valido_dal passato)
--     4. motivo_non_chiudibile  = NULL
--   Riga CHIUSA (BASE/FALLBACK, [oggi-100, oggi-50]):
--     5. puo_chiudersi          = false
--     6. data_min_chiusura      = NULL
--     7. data_default_chiusura  = NULL
--     8. motivo_non_chiudibile  = 'RIGA_GIA_CHIUSA'
--   Riga FUTURA (FALLBACK/BASE invertito, [oggi+10, +inf)):
--     9. puo_chiudersi          = true
--    10. data_min_chiusura      = oggi+10
--    11. data_default_chiusura  = oggi+10 (GREATEST con valido_dal futuro)
--    12. motivo_non_chiudibile  = NULL
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

SELECT plan(12);

-- =========================================================
-- Setup fixture
-- =========================================================
-- ⛔ Gli articoli si COSTRUISCONO (2026-09-23). Fino a oggi questo file
--   pescava `ART_TEST_BASE` / `ART_TEST_FALLBACK`, che non stanno in nessun
--   changelog: sono due righe messe a mano su questa macchina (UUID …101 e
--   …102). Su un database ricostruito non esistono, e il file moriva nella
--   fixture — copertura zero, non parziale.
-- I due PADRI nascono is_composito=true per ammettere INSERT in
-- articoli_componenti come prodotto; il componente resta semplice.
CREATE TEMP TABLE _t_bomcap AS
SELECT
    dbops.fn_pgtap_crea_articolo('PGT-BOMCAP-A', p_is_composito => true) AS art_base,
    dbops.fn_pgtap_crea_articolo('PGT-BOMCAP-B')                         AS art_fallback,
    dbops.fn_pgtap_crea_articolo('PGT-BOMCAP-C', p_is_composito => true) AS art_padre_futura;

CREATE TEMP TABLE _t_righe (scenario text, riga_id uuid);

-- Riga CHIUSA: BASE/FALLBACK, [oggi-100, oggi-50]
WITH ins AS (
    INSERT INTO catalogo.articoli_componenti (
        prodotto_id, componente_id, coeff_qta, obbligatorio,
        esposizione_in_fattura, valido_dal, valido_al, attivo
    )
    SELECT art_base, art_fallback, 1, true, 'NASCOSTO',
           (script.fn_data_operativa() - INTERVAL '100 days')::date,
           (script.fn_data_operativa() - INTERVAL '50  days')::date,
           true
      FROM _t_bomcap
    RETURNING id
)
INSERT INTO _t_righe (scenario, riga_id) SELECT 'chiusa', id FROM ins;

-- Riga APERTA: BASE/FALLBACK, [oggi-30, +inf). No overlap con la
-- chiusa (oggi-30 > oggi-50).
WITH ins AS (
    INSERT INTO catalogo.articoli_componenti (
        prodotto_id, componente_id, coeff_qta, obbligatorio,
        esposizione_in_fattura, valido_dal, valido_al, attivo
    )
    SELECT art_base, art_fallback, 1, true, 'NASCOSTO',
           (script.fn_data_operativa() - INTERVAL '30 days')::date,
           NULL,
           true
      FROM _t_bomcap
    RETURNING id
)
INSERT INTO _t_righe (scenario, riga_id) SELECT 'aperta', id FROM ins;

-- Riga FUTURA: padre C, componente FALLBACK (couple distinto dalla riga
-- aperta, quindi nessun overlap), [oggi+10, +inf).
WITH ins AS (
    INSERT INTO catalogo.articoli_componenti (
        prodotto_id, componente_id, coeff_qta, obbligatorio,
        esposizione_in_fattura, valido_dal, valido_al, attivo
    )
    SELECT art_padre_futura, art_fallback, 1, true, 'NASCOSTO',
           (script.fn_data_operativa() + INTERVAL '10 days')::date,
           NULL,
           true
      FROM _t_bomcap
    RETURNING id
)
INSERT INTO _t_righe (scenario, riga_id) SELECT 'futura', id FROM ins;

-- =========================================================
-- Riga APERTA (1..4)
-- =========================================================
SELECT is(
    (SELECT puo_chiudersi
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'aperta')),
    true,
    '1) APERTA: puo_chiudersi = true (valido_al IS NULL)'
);
SELECT is(
    (SELECT data_min_chiusura
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'aperta')),
    script.fn_data_operativa() - 1,
    '2) APERTA: data_min_chiusura = ieri, non valido_dal (oggi-30): la fine non cambia i giorni passati'
);
SELECT is(
    (SELECT data_default_chiusura
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'aperta')),
    script.fn_data_operativa(),
    '3) APERTA: data_default_chiusura = GREATEST(valido_dal, today) = today'
);
SELECT is(
    (SELECT motivo_non_chiudibile
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'aperta')),
    NULL::text,
    '4) APERTA: motivo_non_chiudibile = NULL'
);

-- =========================================================
-- Riga CHIUSA (5..8)
-- =========================================================
SELECT is(
    (SELECT puo_chiudersi
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'chiusa')),
    false,
    '5) CHIUSA: puo_chiudersi = false (valido_al NOT NULL)'
);
SELECT is(
    (SELECT data_min_chiusura
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'chiusa')),
    NULL::date,
    '6) CHIUSA: data_min_chiusura = NULL (riga non chiudibile)'
);
SELECT is(
    (SELECT data_default_chiusura
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'chiusa')),
    NULL::date,
    '7) CHIUSA: data_default_chiusura = NULL'
);
SELECT is(
    (SELECT motivo_non_chiudibile
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'chiusa')),
    'RIGA_GIA_CHIUSA',
    '8) CHIUSA: motivo_non_chiudibile = RIGA_GIA_CHIUSA'
);

-- =========================================================
-- Riga FUTURA (9..12)
-- =========================================================
SELECT is(
    (SELECT puo_chiudersi
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'futura')),
    true,
    '9) FUTURA: puo_chiudersi = true (valido_al IS NULL anche se valido_dal > today)'
);
SELECT is(
    (SELECT data_min_chiusura
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'futura')),
    (script.fn_data_operativa() + INTERVAL '10 days')::date,
    '10) FUTURA: data_min_chiusura = valido_dal (oggi+10)'
);
SELECT is(
    (SELECT data_default_chiusura
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'futura')),
    (script.fn_data_operativa() + INTERVAL '10 days')::date,
    '11) FUTURA: data_default_chiusura = GREATEST(valido_dal, today) = valido_dal (futuro)'
);
SELECT is(
    (SELECT motivo_non_chiudibile
       FROM catalogo.vw_articoli_componenti_dettaglio
      WHERE id = (SELECT riga_id FROM _t_righe WHERE scenario = 'futura')),
    NULL::text,
    '12) FUTURA: motivo_non_chiudibile = NULL'
);

SELECT * FROM finish();
ROLLBACK;
