-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: seed DB-B (db-brief-lista-preventivi-offerte) — lista configurabile
--       vendite.offerte.
-- Scope: verifica che migration 20260603-06 (vista vw_offerte_commerciali_lista)
--        + append CSV (lista_definizione/colonna/preset/preset_colonna) +
--        priorita (20260603-08) abbiano prodotto lo stato atteso nel DB.
--
-- Indice test (1..16):
--   1.  Vista vw_offerte_commerciali_lista espone ragione_sociale_completa
--   2.  Vista e' security_invoker=on (RLS-ready)
--   3.  Lista vendite.offerte presente e attiva in lista_definizione
--   4.  vista_sql della lista = vw_offerte_commerciali_lista
--   5.  Esattamente 25 colonne attive nel catalogo offerte
--   6.  Colonna id_fiscale ha campo_sorgente = id_fiscale_univoco_cf_piva
--   7.  Tutti i campo_sorgente del catalogo esistono nella vista o nella sintesi della lineage (anti-typo, gemello B2)
--   8.  Preset offerte_default presente con is_default=true
--   9.  Preset: pagina_dimensione=25, ambito=sistema
--   10. Esattamente 12 colonne visibili nel preset offerte_default
--   11. Colonna codice ha fissata=true nel preset (identificatore)
--   12. priorita di dominio applicata (data_emissione=50, ragione_sociale=95, stato=90)
--   13. Anti-regressione sensibile: nessuna colonna offerte sensibile=true
--   14. stato_codice_interno nel catalogo (per Tag severity FE)
--   15. is_scaduta nel catalogo (tipo_dato=boolean) per badge scaduta FE
--   16. is_scaduta esposta dalla vista (materializzata, non piu' solo FE)
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

SELECT plan(16);

-- 1. Vista espone ragione_sociale_completa
SELECT ok(
    EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'vendite'
           AND table_name   = 'vw_offerte_commerciali_lista'
           AND column_name  = 'ragione_sociale_completa'
    ),
    '1. Vista vw_offerte_commerciali_lista espone ragione_sociale_completa'
);

-- 2. Vista security_invoker=on
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
          CROSS JOIN LATERAL unnest(c.reloptions) AS opt
         WHERE n.nspname = 'vendite'
           AND c.relname = 'vw_offerte_commerciali_lista'
           AND opt LIKE 'security_invoker=%'
           AND split_part(opt, '=', 2) IN ('on', 'true')
    ),
    '2. Vista vw_offerte_commerciali_lista: security_invoker=on'
);

-- 3. Lista presente e attiva
SELECT ok(
    EXISTS (
        SELECT 1 FROM ui.lista_definizione
         WHERE codice = 'vendite.offerte' AND attivo = TRUE
    ),
    '3. Lista vendite.offerte presente e attiva in lista_definizione'
);

-- 4. vista_sql corretta
SELECT is(
    (SELECT vista_sql FROM ui.lista_definizione WHERE codice = 'vendite.offerte'),
    'vw_offerte_commerciali_lista',
    '4. Lista offerte: vista_sql = vw_offerte_commerciali_lista'
);

-- 5. Il catalogo e' un INVENTARIO, e cresce per progetto: `>=` e non `=`.
--    ⚠️ Era `esattamente 25`, ed e' rimasto rosso per mesi da quando
--    `pratica`/`fase`/`transito` sono entrate in tutte e quattro le liste
--    documento. Un file rosso finisce in baseline-rossi.tsv, e li' il
--    runner tace sull'INTERO file: le altre 16 asserzioni — fra cui il
--    test 7, l'anti-typo su cui si appoggia P-4 — non le leggeva piu'
--    nessuno. Un conteggio esatto su una cosa che cresce non e' un
--    presidio: e' una fotografia che spegne i presidi veri.
SELECT cmp_ok(
    (
        SELECT COUNT(*)::INTEGER
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.offerte' AND lc.attivo = TRUE
    ),
    '>=', 28,
    '5. Catalogo offerte: almeno 28 colonne attive (nessuna sparita)'
);

-- 6. id_fiscale -> id_fiscale_univoco_cf_piva
SELECT is(
    (
        SELECT lc.campo_sorgente
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.offerte' AND lc.codice = 'id_fiscale'
    ),
    'id_fiscale_univoco_cf_piva',
    '6. Colonna id_fiscale: campo_sorgente = id_fiscale_univoco_cf_piva'
);

-- 7. Ogni campo_sorgente esiste nella vista o nella sintesi della lineage (anti-typo, gemello B2; D-B2 dal 2026-10-11)
SELECT is(
    (
        SELECT COUNT(*)::INTEGER
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.offerte'
           AND lc.attivo = TRUE
           AND lc.tipo_colonna <> 'azione'
           AND COALESCE(lc.campo_sorgente, '') <> ''
           AND NOT EXISTS (
                 SELECT 1 FROM information_schema.columns ic
                  WHERE ic.table_schema = 'vendite'
                    AND ic.table_name   = 'vw_offerte_commerciali_lista'
                    AND ic.column_name  = lc.campo_sorgente
               )
           -- ⭐ D-B2 (giro B di brief-db-lineage-seminata-per-chiave, 2026-10-11):
           --    oppure e' una colonna della SINTESI della lineage, che il backend
           --    chiede per le chiavi della pagina (frontiera, transito…).
           AND NOT EXISTS (
                 SELECT 1 FROM vendite.vw_documento_lineage_sintesi_colonne sc
                  WHERE sc.colonna = lc.campo_sorgente
               )
    ),
    0,
    '7. Tutti i campo_sorgente del catalogo offerte esistono nella vista o nella sintesi della lineage'
);

-- 8. Preset offerte_default is_default=true
SELECT ok(
    EXISTS (
        SELECT 1
          FROM ui.lista_preset lp
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice = 'vendite.offerte'
           AND lp.codice = 'offerte_default'
           AND lp.is_default = TRUE
           AND lp.attivo = TRUE
    ),
    '8. Preset offerte_default presente, is_default=true, attivo=true'
);

-- 9. Preset: pagina_dimensione=25, ambito=sistema
SELECT ok(
    EXISTS (
        SELECT 1
          FROM ui.lista_preset lp
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice = 'vendite.offerte'
           AND lp.codice = 'offerte_default'
           AND lp.pagina_dimensione = 25
           AND lp.ambito::TEXT = 'sistema'
    ),
    '9. Preset offerte_default: pagina_dimensione=25, ambito=sistema'
);

-- 10. ⭐ Qui il conteggio esatto RESTA, e la differenza col 5 e' di merito.
--     Il catalogo e' un inventario; il preset di default e' quello che
--     ogni utente vede alla prima apertura, cioe' una SCELTA. Se cresce
--     da solo, e' un cambio di schermata che nessuno ha deciso — ed e'
--     esattamente cio' che vogliamo vedere rosso.
--     ⚠️ Aggiornato da 12 a 15 (le stesse tre colonne del 5). Chi cambia
--     la vista di default aggiorna QUESTO numero, di proposito.
SELECT is(
    (
        SELECT COUNT(*)::INTEGER
          FROM ui.lista_preset_colonna lpc
          JOIN ui.lista_preset lp      ON lp.id = lpc.preset_id
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice = 'vendite.offerte'
           AND lp.codice = 'offerte_default'
           AND lpc.visibile = TRUE
    ),
    15,
    '10. Preset offerte_default: esattamente 15 colonne visibili'
);

-- 11. codice fissata=true
SELECT ok(
    (
        SELECT lpc.fissata
          FROM ui.lista_preset_colonna lpc
          JOIN ui.lista_colonna lc     ON lc.id = lpc.colonna_id
          JOIN ui.lista_preset lp      ON lp.id = lpc.preset_id
          JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice = 'vendite.offerte'
           AND lp.codice = 'offerte_default'
           AND lc.codice = 'codice'
    ),
    '11. Colonna codice: fissata=true nel preset offerte_default'
);

-- 12. priorita di dominio (data_emissione=50, ragione_sociale=95, stato=90)
SELECT is(
    (
        SELECT array_agg(lc.priorita ORDER BY lc.codice)
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.offerte'
           AND lc.codice IN ('data_emissione', 'ragione_sociale_completa', 'stato')
    ),
    ARRAY[50, 95, 90]::SMALLINT[],
    '12. priorita di dominio: data_emissione=50, ragione_sociale=95, stato=90'
);

-- 13. nessuna colonna sensibile=true
SELECT is(
    (
        SELECT COUNT(*)::INTEGER
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.offerte' AND lc.sensibile = TRUE
    ),
    0,
    '13. Nessuna colonna offerte marcata sensibile=true'
);

-- 14. stato_codice_interno nel catalogo
SELECT is(
    (
        SELECT lc.campo_sorgente
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.offerte' AND lc.codice = 'stato_codice_interno'
    ),
    'stato_codice_interno',
    '14. Colonna stato_codice_interno presente (campo_sorgente=stato_codice_interno)'
);

-- 15. is_scaduta nel catalogo, tipo_dato=boolean
SELECT is(
    (
        SELECT lc.tipo_dato::TEXT
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.offerte' AND lc.codice = 'is_scaduta'
    ),
    'boolean',
    '15. Colonna is_scaduta presente nel catalogo con tipo_dato=boolean'
);

-- 16. is_scaduta esposta dalla vista (materializzata)
SELECT ok(
    EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'vendite'
           AND table_name   = 'vw_offerte_commerciali_lista'
           AND column_name  = 'is_scaduta'
    ),
    '16. Vista vw_offerte_commerciali_lista espone is_scaduta (materializzata)'
);

SELECT * FROM finish();
ROLLBACK;
