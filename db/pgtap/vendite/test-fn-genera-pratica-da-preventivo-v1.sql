-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: CREATE TRIGGER su pratiche.pratiche_sorgenti — fault injection sull'INSERT
--   del link, per dimostrare l'atomicita' della generazione. Il ruolo
--   applicativo ha la DML ma non il privilegio TRIGGER, e non deve averlo.
-- pgTAP per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU GPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: vendite.fn_genera_pratica_da_preventivo (piano analisi-fix-transazioni, #3)
--       + building block condiviso pratiche.fn_crea_pratica.
--
-- Copre:
--   * happy      : crea la pratica (stato APERTA) e il link ROOT in
--                  pratiche_sorgenti, coerente col preventivo.
--   * ATOMICITA'  : se il link fallisce (sorgente PREVENTIVO reso inattivo -> il
--                  trigger require_attivo sul link solleva), la pratica appena
--                  creata dalla figlia NON deve restare (nessun orfano). E' il
--                  cuore del fix: il bug era "pratica creata, link fallisce,
--                  pratica orfana".
--
-- Costruisce il preventivo (rev 2026-10-27, lotto 4 di D7) e legge dal catalogo
-- di seed un tipo_prestazione valido per i guard/definizione. Idempotente:
-- BEGIN ... ROLLBACK.
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

SELECT plan(7);

-- =========================================================
-- Precondizioni: preventivo con BA/emittente + tipo_prestazione valido
-- =========================================================
-- rev 2026-10-27 (lotto 4 di D7): il preventivo si COSTRUISCE
--   (dbops.fn_pgtap_crea_preventivo: azienda di chi agisce, cliente col suo
--   BA legato all'emittente, testata in bozza). Prima si pescava «il primo
--   preventivo con BA ed emittente»: da zero non c'era, e la generazione
--   moriva su «Preventivo non trovato». Il tipo_prestazione resta una
--   lettura del catalogo di seed (20260422-05).
CREATE TEMP TABLE tmp_prev_pb AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('genera pratica');

CREATE TEMP TABLE tmp_prev AS
SELECT p.id, p.uid, p.billing_account_id
FROM vendite.preventivi p
WHERE p.id = (SELECT preventivo_id FROM tmp_prev_pb)
  AND p.billing_account_id IS NOT NULL
  AND anagrafiche.fn_get_emittente_fiscale_pk(p.billing_account_id) IS NOT NULL;

SELECT is((SELECT count(*)::int FROM tmp_prev), 1,
          'Precondizione: esiste un preventivo con billing_account/emittente');

-- tipo_prestazione attivo, non-obsoleto e con definizione risolvibile
-- (supera i guard require_attivo/require_non_obsolete + default_definizione).
CREATE TEMP TABLE tmp_tipo AS
SELECT tp.id
FROM pratiche.tipi_prestazione tp
WHERE tp.attivo IS TRUE
  AND (tp.obsoleto_dal IS NULL OR tp.obsoleto_dal > script.fn_data_operativa())
  AND pratiche.fn_risolvi_definizione(tp.id, NULL) IS NOT NULL
ORDER BY tp.id
LIMIT 1;

SELECT is((SELECT count(*)::int FROM tmp_tipo), 1,
          'Precondizione: esiste un tipo_prestazione valido (attivo/non-obsoleto/con definizione)');

-- =========================================================
-- HAPPY: pratica + link ROOT
-- =========================================================
CREATE TEMP TABLE r_happy AS
SELECT * FROM vendite.fn_genera_pratica_da_preventivo(
    (SELECT id FROM tmp_prev),
    (SELECT id FROM tmp_tipo),
    NULL,
    'pgTAP genera pratica da preventivo'
);

SELECT ok((SELECT pratica_id FROM r_happy) IS NOT NULL,
          'Happy: pratica_id ritornato non nullo');

SELECT is(
    (SELECT sp.codice_interno
       FROM pratiche.pratiche pr
       JOIN config.stati_pratiche sp ON sp.id = pr.stato_id
      WHERE pr.id = (SELECT pratica_id FROM r_happy)),
    'APERTA',
    'Happy: pratica creata in stato APERTA');

SELECT is(
    (SELECT count(*)::int
       FROM pratiche.pratiche_sorgenti ps
       JOIN config.sorgenti s ON s.id = ps.sorgente_tipo_id
      WHERE ps.pratica_id = (SELECT pratica_id FROM r_happy)
        AND s.codice_interno = 'PREVENTIVO'
        AND ps.sorgente_uid = (SELECT uid::text FROM tmp_prev)
        AND ps.ruolo_link = 'ROOT'),
    1,
    'Happy: link ROOT preventivo->pratica creato e coerente');

-- =========================================================
-- ATOMICITA' (cuore del fix): riproduciamo "pratica creata, link fallisce".
-- Un trigger temporaneo fa fallire l'INSERT del link (simula FK/unique/guard
-- violato) DOPO che la figlia fn_crea_pratica ha gia' inserito la pratica.
-- Poiche' e' un'unica statement, il fallimento del link deve annullare anche
-- la pratica: nessun orfano.
-- =========================================================
CREATE FUNCTION pg_temp.pgtap_fail_link() RETURNS trigger
    LANGUAGE plpgsql AS $f$
BEGIN
    RAISE EXCEPTION 'pgtap: fallimento iniettato sull''INSERT del link';
END;
$f$;

CREATE TRIGGER zzz_pgtap_fail_link
    BEFORE INSERT ON pratiche.pratiche_sorgenti
    FOR EACH ROW EXECUTE FUNCTION pg_temp.pgtap_fail_link();

CREATE TEMP TABLE cnt_before AS
SELECT count(*)::int AS n FROM pratiche.pratiche;

-- rev 2026-10-27 (lotto 4 di D7): il discriminante e' la frase del trigger
--   iniettato (sonda: «caught: P0001: pgtap: fallimento iniettato sull'INSERT
--   del link»). Con (NULL, NULL) passava su QUALUNQUE errore — anche su un
--   preventivo non trovato, com'era da zero — e la prova di atomicita' non
--   provava niente.
SELECT throws_ok(
    $$ SELECT * FROM vendite.fn_genera_pratica_da_preventivo(
           (SELECT id FROM tmp_prev),
           (SELECT id FROM tmp_tipo),
           NULL,
           'pgTAP atomicita') $$,
    'P0001',
    'pgtap: fallimento iniettato sull''INSERT del link',
    'Atomicita'': il fallimento del link fa fallire l''intera chiamata');

SELECT is(
    (SELECT count(*)::int FROM pratiche.pratiche),
    (SELECT n FROM cnt_before),
    'Atomicita'': nessuna pratica orfana (creazione annullata insieme al link)');

DROP TRIGGER zzz_pgtap_fail_link ON pratiche.pratiche_sorgenti;

SELECT * FROM finish();

ROLLBACK;
