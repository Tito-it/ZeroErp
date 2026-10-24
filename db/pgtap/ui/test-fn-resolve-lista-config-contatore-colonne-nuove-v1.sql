-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: ui.fn_resolve_lista_config — il contatore `colonne_nuove` deve contare
--       le colonne che l'utente puo' davvero TROVARE, non quelle mergiate dal
--       catalogo e poi rimosse dal filtro dei permessi.
--       (changeSet 20260818-04; brief-db-dash-competenza-gruppi-cliente-e-ricerca §4-ter)
--
-- Elenco test (plan 5):
--   1) colonna `sensibile` SENZA grant: non compare nell'array delle colonne
--   2) ⭐ e NON viene contata in `colonne_nuove` — e' il difetto
--   3) la stessa colonna CON un grant: torna nell'array
--   4) ⭐ e torna contata
--   5) una colonna nuova NON sensibile e' contata (la correzione non spegne
--      il contatore: conta di meno solo dove deve)
--
-- Scopo:
--  - Il difetto, segnalato dal team BE il 2026-08-17: il passo 3 conta le
--    colonne mergiate, il passo 5 toglie quelle BLOCCATO **senza decrementare**,
--    il passo 6 restituisce il numero gonfiato. Il badge annuncia una colonna
--    che la funzione ha appena rimosso, e chi apre il pannello non trova nulla —
--    senza modo di distinguere fra «cerco male», «e' rotto» ed «esiste ma non
--    mi e' concessa».
--
--  - ⚠️ **Era latente su OGNI lista**, non su una: si manifesta ovunque ci sia
--    una colonna `sensibile = TRUE` senza grant in `ui.lista_colonna_permesso`.
--    Al 2026-08-18 non ne esiste nemmeno una, e il seed dei grant non esiste
--    affatto: per questo il difetto non si era mai visto, e per questo la
--    fixture se lo costruisce. Un ramo si verifica dal percorso che lo
--    attraversa, e qui nessun dato lo attraversa.
--
--  - ⚠️ La colonna di prova nasce e muore **dentro la transazione**: non tocca
--    il seed, quindi il cancello lato BE `test_colonna_sensibile_ha_sempre_un_grant`
--    (che vieta `sensibile = t` senza grant nel CATALOGO seedato) resta verde.
--    Sono due presidi complementari: quello impedisce di arrivarci per
--    distrazione, questo verifica che se ci si arriva il conto sia giusto.
--
--  - I test 3-4 sono l'altra meta': un contatore che dicesse sempre «meno» non
--    sarebbe corretto, sarebbe rotto in modo opposto.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE. Senza, un fallimento a meta' lascia la colonna di prova
--   nel catalogo e rompe OGNI lista nelle corse successive.
BEGIN;

-- ⚠️ 2. VINCOLI DIFFERITI. Scattano al COMMIT, e qui il COMMIT non arriva mai:
--   senza questa riga il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- ⚠️ 3. CONTESTO APPLICATIVO. La funzione risolve i profili dell'utente dalla
--   veste corrente (`app.ruolo_applicativo`): senza contesto la cascata dei
--   permessi non e' quella dell'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

-- ============================================================
-- Fixture: una lista qualsiasi fra quelle attive, e una colonna nuova a
-- catalogo marcata `sensibile` e priva di grant.
-- ⭐ La lista si sceglie con ORDER BY esplicito: un LIMIT 1 senza ordinamento
--    non verifica, scommette.
-- ============================================================
-- ⚠️ L'utente NON e' quello del contesto pgTAP. Misurato il 2026-08-18:
--    l'operatore di prova non ha **alcun** profilo di accesso applicabile,
--    quindi su di lui il ramo «colonna sensibile CON grant» e' irraggiungibile
--    — un grant si aggancia a un profilo, e se l'utente non ne ha nessuno la
--    colonna resta bloccata comunque. I test 3-4 sarebbero verdi per la ragione
--    sbagliata. Si sceglie quindi il primo utente che ha davvero un profilo
--    sotto la veste corrente, con un criterio esplicito e non un id fisso.
-- ⛔ E L'UTENTE COL PROFILO SI COSTRUISCE (2026-09-23). Sceglierlo fra quelli
--    che ne hanno gia' uno e' lo stesso criterio, ma su un database
--    ricostruito NESSUNO ne ha uno (misurato: zero utenti con profilo
--    applicabile) e la sotto-select tornava NULL: la funzione veniva chiamata
--    con l'utente NULL, il contatore rispondeva un numero suo e il test 5
--    falliva dicendo «have 1, want 2» — cioe' il file misurava l'assenza di
--    dati, non il contatore. Qui il profilo lo si crea e lo si lega
--    all'identita' dell'operatore di contesto: il criterio del commento qui
--    sopra («un utente che ha davvero un profilo sotto la veste corrente»)
--    diventa una precondizione costruita invece che una speranza.
CREATE TEMP TABLE _t_profilo AS
WITH ins AS (
    INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo)
    VALUES ('AD_HOC',
            '_PGTAP_COLNEW_' || upper(substr(md5(clock_timestamp()::text), 1, 8)),
            'Profilo AD_HOC per il contatore colonne_nuove', TRUE)
    RETURNING id
)
SELECT id AS profilo_id FROM ins;

DO $lega$
BEGIN
    PERFORM config.fn_lega_profilo_identita((SELECT profilo_id FROM _t_profilo), idg.id) FROM anagrafiche.identita_digitali idg
 WHERE idg.auth_user_id = NULLIF(current_setting('app.current_user_id', true), '')::integer
   AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND idg.attivo;
END
$lega$;

CREATE TEMP TABLE _t_ctx AS
SELECT ld.codice                                                         AS lista_codice,
       ld.id                                                             AS lista_id,
       NULLIF(current_setting('app.current_user_id', true), '')::integer AS auth_user_id,
       -- ⚠️ `campo_sorgente` NON si inventa: `trgfn_ui_lista_colonna_a10_valida_campo_sorgente`
       --    verifica che corrisponda a un attributo reale della vista della
       --    lista. Si riusa quello di una colonna gia' a catalogo — il codice
       --    e' nuovo, ed e' il codice a identificare la colonna.
       (SELECT lc.campo_sorgente FROM ui.lista_colonna lc
         WHERE lc.lista_id = ld.id AND lc.attivo IS TRUE
           AND lc.campo_sorgente IS NOT NULL
         ORDER BY lc.id LIMIT 1)                                          AS campo_reale
  FROM ui.lista_definizione ld
 WHERE ld.attivo IS TRUE
 ORDER BY ld.id
 LIMIT 1;

-- Il numero di partenza: quante colonne nuove annuncia la lista PRIMA della
-- prova. Tutto il test ragiona per differenza, cosi' non dipende dal seed.
CREATE TEMP TABLE _t_base AS
SELECT (ui.fn_resolve_lista_config(
          (SELECT lista_codice FROM _t_ctx),
          (SELECT auth_user_id FROM _t_ctx),
          NULL) ->> 'colonne_nuove')::integer AS nuove;

-- La colonna sensibile, senza alcun grant.
INSERT INTO ui.lista_colonna (
    id, lista_id, codice, etichetta, campo_sorgente, tipo_colonna, tipo_dato,
    ordine_default, allineamento, ordinabile, ricercabile_full, sensibile,
    esportabile, attivo, larghezza_default, user_insert)
SELECT 900001, c.lista_id, 'zz_pgtap_sensibile', 'Prova sensibile',
       c.campo_reale, 'informazione', 'string',
       9990, 'left', false, false, TRUE, true, true, 80, 'pgtap'
FROM _t_ctx c;

CREATE OR REPLACE FUNCTION pg_temp.cfg()
RETURNS jsonb AS $$
  SELECT ui.fn_resolve_lista_config(
           (SELECT lista_codice FROM _t_ctx),
           (SELECT auth_user_id FROM _t_ctx),
           NULL);
$$ LANGUAGE sql;

-- ============================================================
-- 1-2) Senza grant: invisibile E non contata
-- ============================================================
SELECT ok(
  NOT EXISTS (SELECT 1 FROM jsonb_array_elements(pg_temp.cfg() -> 'colonne') e
               WHERE e ->> 'codice' = 'zz_pgtap_sensibile'),
  '1) colonna sensibile senza grant: non compare fra le colonne risolte');

SELECT is(
  (pg_temp.cfg() ->> 'colonne_nuove')::integer,
  (SELECT nuove FROM _t_base),
  '2) ⭐ e il contatore NON la annuncia: resta al valore di partenza');

-- ============================================================
-- 3-4) Col grant: torna visibile E torna contata
-- ============================================================
-- ⚠️ La veste va passata come la legge la funzione (dalla GUC), non NULL: con
--    NULL i profili applicabili sono un altro insieme, e il grant finirebbe su
--    un profilo che la funzione non guarda.
INSERT INTO ui.lista_colonna_permesso (colonna_id, profilo_accesso_id, livello_accesso, user_insert)
SELECT 900001, p.profilo_accesso_id, 'TUTTO', 'pgtap'
  FROM script.fn_get_profili_accesso_applicabili(
         (SELECT auth_user_id FROM _t_ctx),
         NULLIF(current_setting('app.ruolo_applicativo', true), '')::config.ruolo_applicativo) p
 ORDER BY p.profilo_accesso_id
 LIMIT 1;

SELECT CASE WHEN (SELECT auth_user_id FROM _t_ctx) IS NULL
  THEN skip('nessun utente con un profilo di accesso: il ramo del grant non e'' esercitabile', 1)
  ELSE ok(
    EXISTS (SELECT 1 FROM jsonb_array_elements(pg_temp.cfg() -> 'colonne') e
             WHERE e ->> 'codice' = 'zz_pgtap_sensibile'),
    '3) con un grant la colonna sensibile torna fra le colonne risolte')
  END;

SELECT CASE WHEN (SELECT auth_user_id FROM _t_ctx) IS NULL
  THEN skip('idem', 1)
  ELSE is(
    (pg_temp.cfg() ->> 'colonne_nuove')::integer,
    (SELECT nuove FROM _t_base) + 1,
    '4) ⭐ e il contatore la annuncia: +1 rispetto al valore di partenza')
  END;

-- ============================================================
-- 5) Non-regressione: una colonna nuova NON sensibile va contata.
--    Un contatore che dicesse sempre «meno» sarebbe rotto in modo opposto.
-- ============================================================
INSERT INTO ui.lista_colonna (
    id, lista_id, codice, etichetta, campo_sorgente, tipo_colonna, tipo_dato,
    ordine_default, allineamento, ordinabile, ricercabile_full, sensibile,
    esportabile, attivo, larghezza_default, user_insert)
SELECT 900002, c.lista_id, 'zz_pgtap_normale', 'Prova normale',
       c.campo_reale, 'informazione', 'string',
       9991, 'left', false, false, FALSE, true, true, 80, 'pgtap'
FROM _t_ctx c;

SELECT is(
  (pg_temp.cfg() ->> 'colonne_nuove')::integer,
  (SELECT nuove FROM _t_base) + 2,
  '5) una colonna nuova non sensibile e'' contata: la correzione non spegne il contatore');

SELECT * FROM finish();
ROLLBACK;
