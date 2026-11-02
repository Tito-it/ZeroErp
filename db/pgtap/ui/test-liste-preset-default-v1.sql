-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: ogni lista a catalogo nasce con la sua CONFIGURAZIONE DICHIARATA
--       (brief-db-residui-competenza-dimensione-e-chiave, §8 — segnalazione BE)
-- ------------------------------------------------------------
-- A cosa serve, in una frase
--   Una lista senza preset di default **si vede lo stesso**: il resolver
--   ripiega sul catalogo e restituisce tutte le colonne. Proprio per questo il
--   buco è invisibile — non produce un errore, produce una lista che parte
--   *senza una configurazione dichiarata*, diversa da tutte le sorelle.
--
-- ⛔ PERCHÉ UN PRESIDIO, E NON «basta ricordarsene»
--   Seminare una lista sono TRE tabelle: `lista_definizione`, `lista_colonna`
--   e `lista_preset` (+ le sue colonne). Le prime due si notano subito, la
--   terza no — e il 2026-08-26 è stata dimenticata su `dash_competenza_residui`
--   senza che nulla lo dicesse. L'ha trovata il backend a mano, contando le
--   righe delle liste sorelle. Questo file sposta quel controllo dalla
--   disciplina alla struttura.
--
-- ⚠️ QUESTO FILE MISURA IL **SEED**, ED È LEGITTIMO
--   Non è una fotografia dei dati di una macchina: `ui.lista_*` è
--   configurazione, viene da `80_data` e in CI c'è identica. È «leggere il
--   progetto», non «misurare la popolazione» (AGENTS.md, regola zero).
--   ⚠️ Ma una misura può degradarsi e rendere un cancello verde per
--   sottrazione: per questo il test 1 verifica PRIMA che il denominatore non
--   sia zero.
--
-- ⛔ COSA *NON* ASSERISCE, E PERCHÉ
--   1. «zero colonne a catalogo fuori dal preset» **globalmente**: una colonna
--      fuori dal preset è il meccanismo del banner DEF-2 («ci sono colonne
--      nuove»), quindi è legittima. Misurate il 2026-08-27: 10 liste ce
--      l'hanno. Si asserisce solo che una lista NUOVA non nasca già col banner
--      acceso, il che sarebbe un controsenso;
--   2. «l'`ordinamento_default` nomina una colonna ordinabile»: sarebbe utile,
--      ma il seed usa **due convenzioni** — `clienti_default` e
--      `emittenti_fiscali_default` ordinano per `campo_sorgente`
--      (`ragione_sociale_completa`), gli altri per `codice`. Scegliere qui
--      quale delle due è «giusta» sarebbe decidere una convenzione dentro un
--      test invece che nel cantiere che possiede le liste.
--
-- Indice test (1..5)
--  1) Il denominatore non e zero (senza, i test dopo passano a vuoto)
--  2) ⛔ Ogni lista ATTIVA ha ESATTAMENTE un preset sistema di default
--  3) ⛔ Una colonna di preset appartiene alla STESSA lista del preset
--  4) La lista dei residui (49) ha il suo preset, dichiarato per intero
--  5) La lista dei residui non nasce col banner DEF-2 gia acceso
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, e qui il COMMIT non arriva mai.
--   Senza questa riga non verrebbero esercitati e il file sarebbe verde per
--   sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS).
-- ℹ️ Le tabelle `ui.lista_*` non hanno RLS — sono catalogo, non dati — ma il
--   contesto si imposta lo stesso: e' il preambolo obbligatorio, e un file che
--   se ne esenta senza dichiararlo e' il modo in cui la regola si sfila.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

-- ============================================================
-- 1) Il denominatore
-- ============================================================
-- ⚠️ I test 2 e 3 sono `count(*) = 0` su una popolazione: se quella popolazione
--   diventasse vuota — catalogo non caricato, filtro sbagliato dopo un
--   refactor — passerebbero **smettendo di verificare**. Questo test e' il loro
--   denominatore, e non un controllo di cortesia.
SELECT cmp_ok(
  (SELECT count(*)::integer FROM ui.lista_definizione WHERE attivo),
  '>=', 40,
  '1) il catalogo delle liste e caricato: i test 2 e 3 hanno un denominatore'
);

-- ============================================================
-- 2) ⛔ Ogni lista attiva ha ESATTAMENTE un preset di sistema di default
-- ============================================================
-- ⛔ E' l'invariante che il 2026-08-26 e' stata infranta in silenzio. «Esattamente
--   uno» e non «almeno uno»: due preset di default sulla stessa lista sono
--   un'ambiguita' — a decidere quale vince sarebbe l'ordine di lettura, cioe'
--   il caso.
-- ℹ️ Il perimetro sono i preset di **sistema**: quelli di `ruolo` e di
--   `emittente_fiscale` sono sovrascritture, e per progetto possono mancare.
SELECT is(
  (SELECT count(*)::integer
     FROM ui.lista_definizione ld
    WHERE ld.attivo
      AND (SELECT count(*)
             FROM ui.lista_preset p
            WHERE p.lista_id = ld.id
              AND p.ambito = 'sistema'
              AND p.is_default
              AND p.attivo) <> 1),
  0,
  '2) ogni lista attiva ha esattamente un preset di sistema di default'
);

-- ============================================================
-- 3) ⛔ Le due FK di `lista_preset_colonna` non parlano fra loro
-- ============================================================
-- `ui.lista_preset_colonna` ha una FK verso il **preset** e una verso la
-- **colonna**, separate: niente a livello di schema obbliga la colonna ad
-- appartenere alla stessa lista del preset. Il modello lo AMMETTE, e l'effetto
-- sarebbe una lista che prova a mostrare la colonna di un'altra — senza nessun
-- errore di vincolo.
-- ⚠️ Oggi zero occorrenze (misurato 2026-08-27), ed e' il momento giusto per
--   metterci un cancello: un presidio nato verde costa niente, e uno nato rosso
--   non nasce.
SELECT is(
  (SELECT count(*)::integer
     FROM ui.lista_preset_colonna pc
     JOIN ui.lista_preset  p  ON p.id  = pc.preset_id
     JOIN ui.lista_colonna lc ON lc.id = pc.colonna_id
    WHERE lc.lista_id <> p.lista_id),
  0,
  '3) ogni colonna di un preset appartiene alla stessa lista del preset'
);

-- ============================================================
-- 4) La lista dei residui, per intero
-- ============================================================
-- ⭐ Non solo «il preset esiste»: che sia **dichiarato per intero**. Le 11
--   colonne del catalogo sono tutte nel preset, dieci accese e una spenta di
--   proposito (l'emittente), e la prima e' fissata.
-- ⚠️ La colonna spenta si scrive `visibile = f` DENTRO il preset, non si omette:
--   omessa diventerebbe «colonna nuova» per il banner DEF-2, cioe' una scelta
--   dichiarata si travestirebbe da dimenticanza. E' la differenza fra le liste
--   nate ad agosto (44/45/47/48, preset = catalogo) e quelle di luglio, dove la
--   colonna emittente aggiunta dopo e' rimasta fuori dal preset.
SELECT ok(
  (SELECT p.codice = 'dash_competenza_residui_default'
      AND p.ambito = 'sistema'
      AND p.is_default
      AND p.attivo
      AND p.profilo_accesso_id IS NULL
      AND p.emittente_fiscale_id IS NULL
     FROM ui.lista_preset p
     JOIN ui.lista_definizione ld ON ld.id = p.lista_id
    WHERE ld.codice = 'vendite.dash_competenza_residui')
  AND (SELECT count(*) = 11 AND count(*) FILTER (WHERE pc.visibile) = 10
                            AND count(*) FILTER (WHERE pc.fissata)  = 1
         FROM ui.lista_preset_colonna pc
         JOIN ui.lista_preset p ON p.id = pc.preset_id
         JOIN ui.lista_definizione ld ON ld.id = p.lista_id
        WHERE ld.codice = 'vendite.dash_competenza_residui'),
  '4) la lista dei residui ha il suo preset di sistema, con 11 colonne dichiarate (10 accese, 1 fissata)'
);

-- ============================================================
-- 5) Una lista NUOVA non nasce col banner DEF-2 acceso
-- ============================================================
-- ⚠️ Perimetro DELIBERATAMENTE ristretto a questa lista. Una colonna a catalogo
--   fuori dal preset e' legittima in generale — e' proprio il segnale «ci sono
--   colonne nuove» del banner DEF-2 — ma su una lista appena nata sarebbe un
--   controsenso: nuove rispetto a cosa?
SELECT is(
  (SELECT count(*)::integer
     FROM ui.lista_colonna lc
     JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
    WHERE ld.codice = 'vendite.dash_competenza_residui'
      AND lc.attivo
      AND NOT EXISTS (SELECT 1
                        FROM ui.lista_preset_colonna pc
                        JOIN ui.lista_preset p ON p.id = pc.preset_id
                       WHERE p.lista_id = ld.id
                         AND p.ambito = 'sistema' AND p.is_default
                         AND pc.colonna_id = lc.id)),
  0,
  '5) la lista dei residui non nasce con colonne fuori dal preset (banner DEF-2 spento)'
);

SELECT * FROM finish();
ROLLBACK;
