-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: Colonne lineage sulle liste documento (Fase B).
--   ⚠️ SEI fino al 2026-08-28, SETTE dal 2026-08-29: il blocco frontiera_*
--   ce l'ha anche vw_fatture_lista, che in questo file non era mai entrata.
--   Viste: vw_preventivi_lista, vw_offerte_commerciali_lista, vw_ordini_lista,
--          vw_contratti_lista, vw_ddt_lista, vw_resi_lista — estese con fase +
--          colonne lineage.
--   Seed: ui.lista_colonna (pratica/fase/transito su liste 4..9).
--   Brief: brief-db-colonne-lineage-liste §5;
--          brief-db-lineage-arco-reso-nota-credito §5 DB-F (la sesta sorella).
--
-- ⛔ 2026-08-25 — PERCHE' I TEST 25/26/29 SONO STATI RITOCCATI E NON SOLO
--   AFFIANCATI. Erano ancorati a `lista_id IN (4,5,6,7,8)` e alla costante 15.
--   Aggiungendo la lista 9 (resi) NON sarebbero diventati rossi: sarebbero
--   rimasti verdi smettendo di coprire la lista nuova — cioe' copertura che
--   sparisce senza che nessun rosso lo dica, la forma peggiore. Una whitelist
--   si verifica dal percorso che la attraversa, non dal nome del test.
--
-- CI-safe: forma (colonne presenti), security_invoker preservato, presenza/
--   correttezza del seed, invariante seed-agnostica. 1 spot-check §5 (PRV0000185)
--   protetto da skip() se i dati non ci sono.
--
-- ⭐ rev 2026-10-11 — GIRO B di brief-db-lineage-seminata-per-chiave (D-B2).
--   Le 8 colonne del GRAFO (frontiera_*, n_discendenti_attivi, is_transitato)
--   escono dalle viste di lista (20261011-97): il backend le chiede a
--   vendite.fn_documento_lineage_sintesi per le chiavi della pagina e le unisce
--   alle righe con gli stessi nomi. La pratica (filtrabile e ordinabile) e la
--   fase restano nella vista. Quindi: i test che dicevano «la vista espone
--   frontiera_*» (3, 6, 9, 12, 15, 18, 31-37, 40-46) ora dicono che NON la
--   espone piu' (hasnt_column); gli invarianti 28, 39, 47 si misurano sulla
--   sintesi chiesta per le chiavi delle righe di ogni lista, come fa il backend.
--   Che il catalogo trovi le sue colonne nella vista o nella sintesi lo dice il
--   test 7 di ui/test-lista-*-seed.
--
-- Indice test (1..47):
--   1..18) le 6 viste espongono pratica_numero, fase, frontiera_codice
--  19..24) le 6 viste hanno security_invoker attivo (preservato)
--     25)  seed: 18 righe (pratica/fase/transito su liste 4..9)
--     26)  seed: campo_sorgente corretto (pratica->pratica_numero, fase->fase,
--          transito->frontiera_codice)
--     27)  invariante: pratica_numero NULL -> n_pratiche = 0 (preventivi)
--     28)  §5 (skip-able): il caso reale si sceglie dai dati (pratica+frontiera
--          insieme -> la fase non manca mai)
--     29)  §7 follow-up: preset default liste 4..9 hanno pratica/fase/transito
--          con visibile=true (18 righe lista_preset_colonna, resi inclusi)
--     30)  §7 follow-up: preset ddt_default (lista 8) creato e is_default
--   ⭐ 31..39 — LA NATURA DELLA FRONTIERA, aggiunta il 2026-08-29 (changeSet
--      20260829-01). Senza, il chip «Transito» decodifica il solo tipo e
--      chiama «Fattura» una nota di credito: vendite.fatture e' UNA tabella.
--      ⛔ E QUI LE VISTE SONO SETTE, non sei: il blocco frontiera_* ce l'ha
--      anche vw_fatture_lista. I test 1..30 ne coprono sei perche' la settima
--      non era mai entrata in questo file — ed e' il motivo per cui l'elenco
--      delle sorelle, nei documenti, era sbagliato.
--  31..37) le 7 viste espongono frontiera_natura_doc_codice_interno
--     38)  vw_fatture_lista ha security_invoker attivo (la settima, che nei
--          test 19..24 non c'era)
--     39)  ⭐⭐ invariante: una natura di frontiera valorizzata implica una
--          frontiera di tipo FATTURA — su tutte e sette insieme
--   ⭐ 40..47 — IL CODICE DEL TIPO DI FRONTIERA, aggiunto il 2026-08-29
--      (changeSet 20260829-02, richiesta BE): prima ogni repository si
--      rifaceva il join a config.sorgenti — sette copie, piu' due altrove.
--  40..46) le 7 viste espongono frontiera_tipo_codice_interno
--     47)  ⭐⭐ invariante: quel valore e' SEMPRE un codice_interno che
--          esiste in config.sorgenti (l'errore da prendere e' la riga
--          copiata dalla sorella: una fase o una natura al posto del tipo)
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

SELECT plan(47);

-- ⭐ LE VISTE SI LEGGONO UNA VOLTA SOLA (rev 2026-10-05). Ogni vista di lista
--   calcola la frontiera con una ricorsione su TUTTO vendite.vw_documento_lineage_archi,
--   qualunque sia il numero di righe: come applicazione (RLS attiva) e' un costo
--   quasi fisso di ~0,7-3 s per lettura (misurato su dbdev il 2026-10-05:
--   offerte 10 righe 0,78 s, preventivi 168 righe 3,1 s). I test 27, 28, 39 e 47
--   le rileggevano 17 volte — ~23 s — e il 47 rivalutava un NOT EXISTS per riga.
--   Si copiano qui, DOPO il contesto operatore: la copia contiene esattamente le
--   righe che la RLS lascia vedere a quell'operatore, quindi le asserzioni non si
--   indeboliscono — cambia quante volte si paga il filtro, non cosa si vede.
--   ⚠️ Una colonna nuova da asserire si aggiunge QUI, o il test leggerebbe la vista
--   di nuovo (e tornerebbe lento) o una copia che non la porta (e non compilerebbe).
-- ⭐ rev 2026-10-11 (giro B di brief-db-lineage-seminata-per-chiave, D-B2): le
--   8 colonne del grafo non stanno piu' nelle viste di lista. Il backend le chiede
--   a vendite.fn_documento_lineage_sintesi per le chiavi della pagina; qui si fa
--   lo stesso, per le chiavi di TUTTE le righe di ogni lista, una chiamata per
--   lista. La pratica e la fase restano nella vista.
CREATE TEMP TABLE _chiavi_liste AS
SELECT 'preventivi'::text AS vista, (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO') AS tipo_id, l.uid::text AS uid FROM vendite.vw_preventivi_lista l
UNION ALL SELECT 'offerte'::text AS vista, (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'OFFERTA_COMMERCIALE') AS tipo_id, l.uid::text AS uid FROM vendite.vw_offerte_commerciali_lista l
UNION ALL SELECT 'ordini'::text AS vista, (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA') AS tipo_id, l.id::text AS uid FROM vendite.vw_ordini_lista l
UNION ALL SELECT 'contratti'::text AS vista, (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'CONTRATTO') AS tipo_id, l.id::text AS uid FROM vendite.vw_contratti_lista l
UNION ALL SELECT 'ddt'::text AS vista, (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'DDT_VENDITA') AS tipo_id, l.id::text AS uid FROM vendite.vw_ddt_lista l
UNION ALL SELECT 'resi'::text AS vista, (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'RESO_VENDITA') AS tipo_id, l.id::text AS uid FROM vendite.vw_resi_lista l
UNION ALL SELECT 'fatture'::text AS vista, (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'FATTURA') AS tipo_id, l.id::text AS uid FROM vendite.vw_fatture_lista l;

CREATE TEMP TABLE _sintesi_liste AS
SELECT k.vista, s.*
  FROM (SELECT vista, array_agg(tipo_id) AS t, array_agg(uid) AS u FROM _chiavi_liste GROUP BY vista) k
 CROSS JOIN LATERAL vendite.fn_documento_lineage_sintesi(k.t, k.u) s;

CREATE TEMP TABLE _lin_prev AS
SELECT l.pratica_numero, l.n_pratiche, l.fase, s.frontiera_codice,
       s.frontiera_natura_doc_codice_interno, s.frontiera_tipo_id, s.frontiera_tipo_codice_interno
  FROM vendite.vw_preventivi_lista l
  LEFT JOIN _sintesi_liste s ON s.vista = 'preventivi' AND s.uid = l.uid::text;

CREATE TEMP TABLE _lin_frontiera AS
SELECT vista, frontiera_natura_doc_codice_interno, frontiera_tipo_id, frontiera_tipo_codice_interno
  FROM _sintesi_liste;

-- ---- 1..18: pratica e fase restano sulle 6 viste; frontiera_codice no ----
-- (dal giro B la frontiera viene dalla sintesi: D-B2, 2026-10-11)
SELECT has_column('vendite', 'vw_preventivi_lista',          'pratica_numero',  'preventivi: pratica_numero');
SELECT has_column('vendite', 'vw_preventivi_lista',          'fase',            'preventivi: fase');
SELECT hasnt_column('vendite', 'vw_preventivi_lista', 'frontiera_codice', 'preventivi: frontiera_codice non sta piu'' nella vista (viene dalla sintesi, D-B2)');
SELECT has_column('vendite', 'vw_offerte_commerciali_lista', 'pratica_numero',  'offerte: pratica_numero');
SELECT has_column('vendite', 'vw_offerte_commerciali_lista', 'fase',            'offerte: fase');
SELECT hasnt_column('vendite', 'vw_offerte_commerciali_lista', 'frontiera_codice', 'offerte: frontiera_codice non sta piu'' nella vista (viene dalla sintesi, D-B2)');
SELECT has_column('vendite', 'vw_ordini_lista',              'pratica_numero',  'ordini: pratica_numero');
SELECT has_column('vendite', 'vw_ordini_lista',              'fase',            'ordini: fase');
SELECT hasnt_column('vendite', 'vw_ordini_lista', 'frontiera_codice', 'ordini: frontiera_codice non sta piu'' nella vista (viene dalla sintesi, D-B2)');
SELECT has_column('vendite', 'vw_contratti_lista',           'pratica_numero',  'contratti: pratica_numero');
SELECT has_column('vendite', 'vw_contratti_lista',           'fase',            'contratti: fase');
SELECT hasnt_column('vendite', 'vw_contratti_lista', 'frontiera_codice', 'contratti: frontiera_codice non sta piu'' nella vista (viene dalla sintesi, D-B2)');
SELECT has_column('vendite', 'vw_ddt_lista',                 'pratica_numero',  'ddt: pratica_numero');
SELECT has_column('vendite', 'vw_ddt_lista',                 'fase',            'ddt: fase');
SELECT hasnt_column('vendite', 'vw_ddt_lista', 'frontiera_codice', 'ddt: frontiera_codice non sta piu'' nella vista (viene dalla sintesi, D-B2)');
-- ⭐ rev 2026-08-25: la SESTA sorella. vw_resi_lista era l'unica lista documento
--    senza genealogia, e su un reso la colonna «transito» (frontiera_codice) e'
--    il numero della NOTA DI CREDITO che lo accredita — l'arco S del cantiere
--    brief-db-lineage-arco-reso-nota-credito. ⚠️ `fase` non c'era proprio: la
--    vista aveva lo stato ma non la fase normalizzata, e senza quella colonna il
--    seed omonimo sarebbe nato vuoto in silenzio.
SELECT has_column('vendite', 'vw_resi_lista',                'pratica_numero',  'resi: pratica_numero');
SELECT has_column('vendite', 'vw_resi_lista',                'fase',            'resi: fase');
SELECT hasnt_column('vendite', 'vw_resi_lista', 'frontiera_codice', 'resi: frontiera_codice non sta piu'' nella vista (viene dalla sintesi, D-B2)');

-- ---- 19..24: security_invoker preservato --------------------------------
SELECT ok(EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) o
                   WHERE c.oid='vendite.vw_preventivi_lista'::regclass
                     AND o IN ('security_invoker=on','security_invoker=true')),
          'preventivi: security_invoker preservato');
SELECT ok(EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) o
                   WHERE c.oid='vendite.vw_offerte_commerciali_lista'::regclass
                     AND o IN ('security_invoker=on','security_invoker=true')),
          'offerte: security_invoker preservato');
SELECT ok(EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) o
                   WHERE c.oid='vendite.vw_ordini_lista'::regclass
                     AND o IN ('security_invoker=on','security_invoker=true')),
          'ordini: security_invoker preservato');
SELECT ok(EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) o
                   WHERE c.oid='vendite.vw_contratti_lista'::regclass
                     AND o IN ('security_invoker=on','security_invoker=true')),
          'contratti: security_invoker preservato');
SELECT ok(EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) o
                   WHERE c.oid='vendite.vw_ddt_lista'::regclass
                     AND o IN ('security_invoker=on','security_invoker=true')),
          'ddt: security_invoker preservato');
SELECT ok(EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) o
                   WHERE c.oid='vendite.vw_resi_lista'::regclass
                     AND o IN ('security_invoker=on','security_invoker=true')),
          'resi: security_invoker preservato');

-- ---- 25..26: seed ui.lista_colonna --------------------------------------
SELECT is(
    (SELECT count(*)::int FROM ui.lista_colonna
      WHERE lista_id IN (4,5,6,7,8,9) AND codice IN ('pratica','fase','transito') AND attivo),
    18, 'seed: 18 colonne lineage (pratica/fase/transito su liste 4..9)');

SELECT is(
    (SELECT count(*)::int FROM ui.lista_colonna
      WHERE lista_id IN (4,5,6,7,8,9)
        AND ( (codice = 'pratica'  AND campo_sorgente = 'pratica_numero')
           OR (codice = 'fase'     AND campo_sorgente = 'fase')
           OR (codice = 'transito' AND campo_sorgente = 'frontiera_codice') )),
    18, 'seed: campo_sorgente corretto per le 18 colonne');

-- ---- 27: invariante seed-agnostica --------------------------------------
SELECT is(
    (SELECT count(*)::int FROM _lin_prev
      WHERE pratica_numero IS NULL AND n_pratiche > 0),
    0, 'invariante: pratica_numero NULL -> n_pratiche = 0');

-- ---- 28: caso reale §5, scelto dai dati e non nominato ------------------
-- 🔴 RESO SEED-AGNOSTICO IL 2026-08-18.
--   Prima questo test nominava un documento: PRV0000185, e si aspettava
--   'PRA-0000818|DDT0000031|CHIUSO'. Falliva con `have: NULL`.
--   ⚠️ Non e' un difetto della vista, ed e' stato verificato prima di
--   riscrivere: delle 46 righe con una pratica, **35 hanno anche la
--   frontiera** — la proiezione funziona. E' quel documento ad averla persa
--   (ne sono 11 nella stessa condizione). La `||` con un NULL restituisce
--   NULL, e il test cadeva li'.
--
--   ⚠️ Il difetto era nel test: scommetteva sui dati di sviluppo di un giorno
--   preciso. Lo `skip` che lo protegge guarda solo se il preventivo ESISTE —
--   e infatti esiste ancora, quindi lo skip non e' mai scattato e il test si e'
--   rotto sul contenuto. Un guscio di prudenza che non copre il caso che
--   cambia davvero.
--
--   Ora il caso reale si SCEGLIE dai dati invece di essere nominato: si prende
--   un preventivo che soddisfa la premessa e si verifica la proprieta' che il
--   §5 voleva davvero — che le tre colonne di lineage arrivino INSIEME in
--   lista. Se un domani nessun documento avra' piu' la terna, il test lo dice
--   con uno skip onesto invece di mentire su un numero di documento.
--   E' la forma del test 23 qui sopra, che infatti non e' mai stato rosso.
SELECT CASE
    WHEN EXISTS (
        SELECT 1 FROM _lin_prev
         WHERE pratica_numero IS NOT NULL
           AND frontiera_codice IS NOT NULL
           AND fase IS NOT NULL
    ) THEN
        is(
            (SELECT count(*)::int
               FROM _lin_prev
              WHERE pratica_numero IS NOT NULL
                AND frontiera_codice IS NOT NULL
                AND fase IS NULL),
            0,
            '§5 lineage: dove ci sono pratica e frontiera, la fase non manca mai')
    ELSE skip('nessun preventivo con la terna pratica+frontiera+fase nei dati', 1)
END;

-- ---- 29..30: §7 follow-up — visibilita' di default sui preset 4..9 -------
SELECT is(
    (SELECT count(*)::int
       FROM ui.lista_preset_colonna pc
       JOIN ui.lista_colonna lc ON lc.id = pc.colonna_id
       JOIN ui.lista_preset pr ON pr.id = pc.preset_id AND pr.is_default IS TRUE
      WHERE pc.preset_id IN (4,5,6,7,8,9)
        AND lc.codice IN ('pratica','fase','transito')
        AND pc.visibile IS TRUE),
    18, 'preset default (6 liste): 18 colonne lineage visibili');

SELECT ok(
    EXISTS (SELECT 1 FROM ui.lista_preset
             WHERE lista_id = 8 AND codice = 'ddt_default' AND is_default IS TRUE AND attivo),
    'preset ddt_default creato e is_default');

-- ---- 31..37: la natura della frontiera sulle SETTE liste -----------------
-- ⚠️ L'ELENCO E' ESPLICITO, E DEVE RESTARLO. La forma comoda sarebbe un giro
--    su information_schema con table_name LIKE 'vw_%_lista': resterebbe VERDE
--    aggiungendo una lista che la colonna non ce l'ha, perche' conterebbe solo
--    quelle che ci sono. In un elenco entra chi c'e', non chi dovrebbe
--    esserci. Stessa lezione dei test 25/26/29 in testa a questo file.
-- ⭐ Sono SETTE e non sei: il blocco frontiera_* ce l'ha anche
--    vw_fatture_lista. La sesta/settima e' esattamente l'errore che si vuole
--    rendere impossibile da ripetere.
SELECT hasnt_column('vendite', 'vw_preventivi_lista', 'frontiera_natura_doc_codice_interno', 'preventivi: frontiera_natura_doc_codice_interno non sta piu'' nella vista (viene dalla sintesi, D-B2)');
SELECT hasnt_column('vendite', 'vw_offerte_commerciali_lista', 'frontiera_natura_doc_codice_interno', 'offerte: frontiera_natura_doc_codice_interno non sta piu'' nella vista (viene dalla sintesi, D-B2)');
SELECT hasnt_column('vendite', 'vw_ordini_lista', 'frontiera_natura_doc_codice_interno', 'ordini: frontiera_natura_doc_codice_interno non sta piu'' nella vista (viene dalla sintesi, D-B2)');
SELECT hasnt_column('vendite', 'vw_contratti_lista', 'frontiera_natura_doc_codice_interno', 'contratti: frontiera_natura_doc_codice_interno non sta piu'' nella vista (viene dalla sintesi, D-B2)');
SELECT hasnt_column('vendite', 'vw_ddt_lista', 'frontiera_natura_doc_codice_interno', 'ddt: frontiera_natura_doc_codice_interno non sta piu'' nella vista (viene dalla sintesi, D-B2)');
SELECT hasnt_column('vendite', 'vw_resi_lista', 'frontiera_natura_doc_codice_interno', 'resi: frontiera_natura_doc_codice_interno non sta piu'' nella vista (viene dalla sintesi, D-B2)');
-- ⚠️ La settima: su vw_fatture_lista la colonna e' COSTANTE (una fattura e'
--    sempre frontiera di se stessa - pgTAP 30 di test-documento-lineage-v1) e
--    il chip non e' montato. C'e' lo stesso, e il test la pretende, perche' la
--    ragione e' di FORMA: sette sorelle devono esporre lo stesso blocco, o chi
--    scrive l'ottava copia da quella diversa.
SELECT hasnt_column('vendite', 'vw_fatture_lista', 'frontiera_natura_doc_codice_interno', 'fatture: frontiera_natura_doc_codice_interno non sta piu'' nella vista (viene dalla sintesi, D-B2)');

-- ---- 38: security_invoker sulla SETTIMA ---------------------------------
-- ⛔ vw_fatture_lista non era in questo file, quindi nessuno verificava che
--    conservasse security_invoker - ed e' una reloption INVISIBILE in
--    pg_get_viewdef: un CREATE OR REPLACE che non la ripete la azzera senza
--    nessun errore, e la RLS emittente smette di mordere su quella lista.
--    Il 20260829-01 fa un replace anche su di lei: senza questa riga sarebbe
--    l'unica delle sette a passare da un replace non presidiato.
SELECT ok(EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) o
                   WHERE c.oid='vendite.vw_fatture_lista'::regclass
                     AND o IN ('security_invoker=on','security_invoker=true')),
          'fatture: security_invoker preservato');

-- ---- 39: l'invariante che has_column non sa vedere -----------------------
-- ⭐⭐ COSA PRESIDIA, e perche' i sette has_column da soli non bastano.
--    has_column verifica il NOME della colonna, non da dove viene il valore.
--    L'errore plausibile qui e' la riga copiata dalla sorella sopra:
--      lin.frontiera_fase AS frontiera_natura_doc_codice_interno
--    Sette viste quasi identiche, sette righe quasi identiche, e il replace
--    non darebbe nessun errore: has_column resterebbe verde e il chip
--    scriverebbe una FASE dove va una natura.
-- ⚠️ L'invariante e' seed-agnostica e non nomina nessun documento: la natura
--    esiste SOLO per le fatture (e' un asse diverso dal tipo), quindi una
--    natura di frontiera valorizzata implica una frontiera di tipo FATTURA.
--    Su un DB vuoto conta zero e asserisce zero.
-- ⚠️ Elenco esplicito anche qui, per la stessa ragione dei 31..37: una lista
--    nuova non entra da sola, e non deve sembrare che ci sia.
SELECT is(
    -- dalla copia delle sette viste (vedi in testa)
    (SELECT count(*)::int FROM _lin_frontiera
      WHERE frontiera_natura_doc_codice_interno IS NOT NULL
        AND frontiera_tipo_id <> (SELECT id FROM config.sorgenti WHERE codice_interno='FATTURA')),
    0, 'liste: una natura di frontiera valorizzata implica una frontiera FATTURA');

-- ---- 40..46: il codice del tipo di frontiera sulle SETTE liste ----------
-- ⚠️ Elenco esplicito, per la stessa ragione dei 31..37: in un elenco entra
--    chi c'e', non chi dovrebbe esserci.
-- ⛔ E il nome e' `_codice_interno`, non `_codice`: il BE aveva chiesto
--    `frontiera_tipo_codice` per non cambiare una riga a valle, ma quel valore
--    e' config.sorgenti.codice_interno — la colonna IMMUTABILE, che il FE usa
--    per la chiave i18n e per instradare, cioe' come LOGICA. §6c vieta
--    `codice_interno AS *_codice` e il guardrail CI fallisce sul pattern.
SELECT hasnt_column('vendite', 'vw_preventivi_lista', 'frontiera_tipo_codice_interno', 'preventivi: frontiera_tipo_codice_interno non sta piu'' nella vista (viene dalla sintesi, D-B2)');
SELECT hasnt_column('vendite', 'vw_offerte_commerciali_lista', 'frontiera_tipo_codice_interno', 'offerte: frontiera_tipo_codice_interno non sta piu'' nella vista (viene dalla sintesi, D-B2)');
SELECT hasnt_column('vendite', 'vw_ordini_lista', 'frontiera_tipo_codice_interno', 'ordini: frontiera_tipo_codice_interno non sta piu'' nella vista (viene dalla sintesi, D-B2)');
SELECT hasnt_column('vendite', 'vw_contratti_lista', 'frontiera_tipo_codice_interno', 'contratti: frontiera_tipo_codice_interno non sta piu'' nella vista (viene dalla sintesi, D-B2)');
SELECT hasnt_column('vendite', 'vw_ddt_lista', 'frontiera_tipo_codice_interno', 'ddt: frontiera_tipo_codice_interno non sta piu'' nella vista (viene dalla sintesi, D-B2)');
SELECT hasnt_column('vendite', 'vw_resi_lista', 'frontiera_tipo_codice_interno', 'resi: frontiera_tipo_codice_interno non sta piu'' nella vista (viene dalla sintesi, D-B2)');
SELECT hasnt_column('vendite', 'vw_fatture_lista', 'frontiera_tipo_codice_interno', 'fatture: frontiera_tipo_codice_interno non sta piu'' nella vista (viene dalla sintesi, D-B2)');

-- ---- 47: il valore, non solo il nome ------------------------------------
-- ⭐⭐ L'INVARIANTE CHE I SETTE has_column NON SANNO FARE. L'errore plausibile
--    su sette viste quasi identiche e' la riga copiata dalla sorella accanto:
--      lin.frontiera_fase                  AS frontiera_tipo_codice_interno
--      lin.frontiera_natura_doc_codice_interno AS frontiera_tipo_codice_interno
--    Nessun errore alla creazione, i has_column tutti verdi, e il consumatore
--    che instrada sul tipo finisce su una fase.
-- ⚠️ Qui si pretende che il valore sia un codice_interno che ESISTE in
--    config.sorgenti: 'IN_CORSO' e 'NOTA_CREDITO' non ci sono, e la copia
--    viene presa. Seed-agnostica: su un DB vuoto conta zero e asserisce zero.
SELECT is(
    -- dalla copia delle sette viste (vedi in testa)
    (SELECT count(*)::int FROM _lin_frontiera f
      WHERE f.frontiera_tipo_codice_interno IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM config.sorgenti s
                         WHERE s.codice_interno = f.frontiera_tipo_codice_interno)),
    0, 'liste: frontiera_tipo_codice_interno e'' sempre un codice_interno di config.sorgenti');

SELECT * FROM finish();
ROLLBACK;
