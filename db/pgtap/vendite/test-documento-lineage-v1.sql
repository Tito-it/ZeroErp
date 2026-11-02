-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: Lineage documenti vendite (Step 5).
--   Oggetti: vw_documento_lineage_nodi, vw_documento_lineage_archi,
--            vw_documento_lineage, vendite.fn_documento_lineage.
--   Brief: brief-db-lineage-documenti-vendite §5.
--
-- Impostazione: la maggior parte dei test e' SEED-AGNOSTICA (forma degli oggetti,
--   security_invoker, invarianti che valgono su QUALSIASI dato — anche DB vuoto).
--   I 2 spot-check sui casi reali §5 (PRV0000185, commessa 186) sono protetti da
--   skip() quando i dati non sono presenti (es. CI su DB fresco).
--
-- Indice test (1..47):
--    1) vw_documento_lineage_nodi esiste
--    2) vw_documento_lineage_archi esiste
--    3) vw_documento_lineage ritirata, la sintesi e' fn_documento_lineage_sintesi (rev 2026-10-11)
--    4) fn_documento_lineage(bigint,text,text) esiste
--    5) colonne di vw_documento_lineage_nodi
--    6) colonne di vw_documento_lineage_archi
--    7) colonne della sintesi (fn_documento_lineage_sintesi), nell'ordine (rev 2026-10-11)
--    8) nodi: security_invoker attivo
--    9) archi: security_invoker attivo
--   10) sintesi: SECURITY INVOKER e STABLE (rev 2026-10-11; era la vista)
--   11) fn: STABLE
--   12) fn: SECURITY INVOKER (NON definer)
--   13) archi: arco solo in A..H,R,N,S,T,U,V (vocabolario CHIUSO: e' un cricchetto)
--   14) archi: arco 'R' punta sempre a un nodo RESO_VENDITA
--   15) nodi: pipeline_rank sempre in 0..5
--   16) config.sorgenti RESO_VENDITA seedato e attivo (prereq Step 1)
--   17) summary: frontiera sempre valorizzata (self e' sempre candidato)
--   18) summary: RESO mai frontiera di un nodo non-reso (arco R escluso;
--       un reso e' pero' frontiera di se stesso finche' NON e' accreditato —
--       dal 2026-08-25 l'arco S gli da' la nota di credito come frontiera)
--   19) invariante: n_discendenti_attivi>0 -> frontiera_fase <> 'CHIUSO'
--   20) invariante: nodo attivo -> frontiera attiva
--   21) fn guard: p_tipo_id <= 0 solleva
--   22) fn guard: p_uid vuoto solleva
--   23) fn guard: p_direzione non valida solleva
--   24) fn: direzione di default ('avanti') non solleva
--   25) §5 (skip-able): PRV0000185 -> catena forward raggiunge un DDT (arco H)
--   26) §5 (skip-able): commessa 186 -> indietro trova >=2 sorgenti (ROOT+COLLEGATO)
--   ⭐ 27..32 — L'ARCO N e la NATURA, aggiunti il 2026-08-21 (changeSet
--      20260821-01..04). L'arco N e' «fattura rettificata -> nota di credito»:
--      il legame esisteva nei dati (fatture_righe.riga_rettificata_id) ma non
--      nel grafo, quindi dalla nota non si risaliva al documento corretto.
--   27) archi: l'arco N sta sempre fra due nodi FATTURA
--   28) archi: l'arco N non e' mai un cappio (un documento non rettifica se')
--   29) archi: is_ramo_inverso e' true ESATTAMENTE per R e N
--   30) ⭐⭐ summary: una FATTURA e' sempre frontiera di se stessa — e' il
--       presidio della decisione del 2026-08-21 (l'arco N e' un ramo di ritorno
--       e resta fuori dal grafo forward delle liste). ⚠️ Non «una NC non e' mai
--       frontiera»: quella formulazione e' sbagliata e l'ha detto il test
--   31) nodi: la natura e' valorizzata SOLO sui nodi FATTURA
--   32) §44 (skip-able): dalla nota di credito si risale alla fattura che
--       rettifica, e i due nodi si distinguono per natura
--   ⭐ 33..38 — L'ARCO S e il PERIMETRO RLS, aggiunti il 2026-08-25 (changeSet
--      20260825-19..21). L'arco S e' «reso -> nota di credito»: il grafo si
--      fermava sul reso, e i due rami di ritorno — la merce che torna e il
--      valore che torna — non si toccavano mai.
--   33) archi: l'arco S parte sempre da un nodo RESO_VENDITA
--   34) archi: l'arco S arriva sempre a un nodo FATTURA
--   35) archi: e quella fattura e' sempre una NOTA DI CREDITO
--   36) summary: un reso con arco S non e' piu' una foglia (is_transitato)
--   37) summary: la frontiera di un reso accreditato e' la nota, non se stesso
--   38) ⭐⭐ archi: NESSUN arco esce dal perimetro RLS
--   ⭐ 39 — L'ARCO T, aggiunto il 2026-08-28 (changeSet 20260828-05). E'
--      «reso -> DDT di ri-consegna»: il grafo aveva R (la merce torna) e S
--      (il valore si accredita) ma non l'arco che dice che la merce e'
--      RIPARTITA, e un reso ri-consegnato restava una foglia.
--   39) archi: T va da RESO_VENDITA a DDT_VENDITA ed e' un AVANZAMENTO
--       (gemello di S), non un ramo di ritorno
--   ⭐ 40 — LA NATURA DEL NODO DI FRONTIERA, aggiunta il 2026-08-28 (changeSet
--      20260828-22). Senza quella colonna ogni lista che rende il chip
--      «Transito» chiama «Fattura» una nota di credito: vendite.fatture e' UNA
--      tabella e le viste di lista non proiettano frontiera_uid, cioe' la
--      chiave con cui si andrebbe a leggere la natura.
--   40) summary: frontiera_natura_doc_codice_interno E' la natura del nodo di
--       frontiera — non quella del nodo proprio
--   ⭐ 41..43 — L'ARCO U e il RANGO DICHIARATO, aggiunti il 2026-08-28
--      (changeSet 20260828-24 e -25). U e' «DDT -> Commessa», la quarta
--      sorgente di commessa: le righe DDT_VENDITA di commesse_sorgenti non
--      producevano nessun arco e quelle commesse dichiaravano di non avere
--      origine. rango_origine toglie il ROOT dalle mani di from_tipo_id,
--      cioe' di un id di seed.
--   41) archi: OGNI arco ha un rango_origine (il cricchetto del rango)
--   42) archi: ogni riga DDT_VENDITA di commesse_sorgenti che vede le due
--       testate produce il suo arco U (presidio della CHIAVE polimorfa)
--   43) ⭐⭐ summary: il ROOT scelto e' il MIGLIORE degli archi entranti
--       secondo la regola dichiarata — nessun arco entrante lo batte
--   44) ⭐⭐ summary: il ROOT e' un arco che ESISTE — cioe' i tre array_agg
--       hanno pescato dalla stessa riga (il 43 da solo non lo vede)
--   ⭐ 45..46 — IL CODICE DEL TIPO, aggiunto il 2026-08-29 (changeSet
--      20260829-02, richiesta BE). Il grafo esponeva il tipo solo come
--      tipo_id e ogni consumatore se lo traduceva da se': dieci copie a mano
--      nel backend. ⛔ Il nome e' `*_codice_interno` e non `*_codice` perche'
--      il valore e' config.sorgenti.codice_interno, cioe' la colonna
--      IMMUTABILE su cui si fa logica (linee-guida-sql §6c).
--   45) nodi/summary: tipo_codice_interno E' il codice_interno di tipo_id
--   46) summary: frontiera_tipo_codice_interno idem, sul nodo di frontiera
--   ⭐ 47 — IL NUMERO DOCUMENTO, aggiunto il 2026-08-29 (changeSet 20260829-16):
--      il `codice` del nodo FATTURA non e' piu' il contatore nudo ma il numero
--      documento composto dalla sede unica fn_numero_documento_fattura.
--   47) nodi: il codice di un nodo FATTURA E' quello della sede unica —
--       nessun ramo se lo ricompone per conto suo
--   ⭐ 48 — L'ARCO V, aggiunto il 2026-11-01 (changeSet 20261031-68):
--   48) archi: V va dalla revisione madre alla figlia (offerta -> offerta,
--       revisione_padre_id), non e' di ritorno, e ha il rango piu' basso
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

-- ============================================================
-- ⭐ IL GRAFO SI LEGGE UNA VOLTA SOLA — e non e' un'ottimizzazione cosmetica.
--
-- ⛔ Il difetto, misurato il 2026-09-10. Le tre viste di lineage costano ~10
--   volte tanto quando le legge l'APPLICAZIONE invece dell'owner: sotto RLS con
--   il contesto operatore una scansione di `vw_documento_lineage_archi` passa da
--   **38 ms a 430 ms**, e il summary da 40 a 357. Questo file le rilegge decine
--   di volte — alcune dentro `EXISTS` correlati, che le rivalutano **riga per
--   riga** su 465 nodi. Risultato: **109 secondi** contro l'unico secondo che
--   costa lo stesso file girato come owner.
--
-- ⚠️ E il danno non era la lentezza, era l'INSTABILITA': `pgtap-baseline.sh`
--   uccide ogni file a **90 secondi**, quindi questo entrava e usciva
--   dall'elenco dei rossi a seconda del carico della macchina, comparendo come
--   «regressione nuova» in una corsa e sparendo in quella dopo. E non essendo in
--   nessuna baseline, ogni corsa lo vedeva per la prima volta.
--
-- ⭐ Perche' materializzare NON indebolisce il test: le tre tabelle si popolano
--   **dopo** aver preso il contesto operatore, quindi contengono esattamente le
--   righe che la RLS lascia vedere a quell'operatore — le stesse su cui le
--   asserzioni giravano prima. Cambia quante volte si paga il filtro, non cosa
--   si vede.
--
-- ⛔ L'ECCEZIONE, ed e' una sola: il **test 38** («nessun arco esce dal
--   perimetro RLS») continua a interrogare le VISTE VIVE. E' l'unico che non
--   asserisce una proprieta' del grafo ma il comportamento del **filtro**:
--   chiederlo a una copia vorrebbe dire misurare la RLS attraverso una tabella
--   che la RLS non ha, cioe' un presidio che si auto-neutralizza.
--
-- ⚠️ Chi aggiunge un'asserzione qui dentro si fermi un attimo: se parla del
--   GRAFO usa `_lin_*`; se parla del PERIMETRO usa la vista.
-- ============================================================
CREATE TEMP TABLE _lin_nodi    AS SELECT * FROM vendite.vw_documento_lineage_nodi;
CREATE TEMP TABLE _lin_archi   AS SELECT * FROM vendite.vw_documento_lineage_archi;
-- ⭐ rev 2026-10-11 (giro B di brief-db-lineage-seminata-per-chiave): la sintesi
--   per nodo non e' piu' una vista (vw_documento_lineage, ritirata in
--   20261011-98) ma vendite.fn_documento_lineage_sintesi, chiesta qui per TUTTI
--   i nodi visibili: stesse 28 colonne, stessa regola. Gli invarianti sotto
--   («summary: …») la misurano come misuravano la vista.
CREATE TEMP TABLE _lin_summary AS
SELECT * FROM vendite.fn_documento_lineage_sintesi(
    -- ⚠️ coalesce: su un database da zero non ci sono nodi, e un seme NULL la
    --    sintesi lo rifiuta (E_ERRORE_PARAMETRI); vuoto vuol dire zero righe.
    coalesce((SELECT array_agg(tipo_id) FROM _lin_nodi), '{}'::bigint[]),
    coalesce((SELECT array_agg(uid)     FROM _lin_nodi), '{}'::text[]));

-- Gli indici servono agli EXISTS correlati, che sono il grosso del costo.
CREATE INDEX ON _lin_nodi  (tipo_id, uid);
CREATE INDEX ON _lin_archi (from_tipo_id, from_uid);
CREATE INDEX ON _lin_archi (to_tipo_id, to_uid);
ANALYZE _lin_nodi;
ANALYZE _lin_archi;
ANALYZE _lin_summary;

SELECT plan(48);

-- ---- 1..4: esistenza oggetti ---------------------------------------------
SELECT has_view('vendite', 'vw_documento_lineage_nodi',  'vw_documento_lineage_nodi esiste');
SELECT has_view('vendite', 'vw_documento_lineage_archi', 'vw_documento_lineage_archi esiste');
SELECT ok(to_regclass('vendite.vw_documento_lineage') IS NULL
          AND to_regprocedure('vendite.fn_documento_lineage_sintesi(bigint[], text[])') IS NOT NULL,
    'vw_documento_lineage ritirata (20261011-98): la sintesi e'' fn_documento_lineage_sintesi');
SELECT has_function('vendite', 'fn_documento_lineage',
                    ARRAY['bigint','text','text'],
                    'fn_documento_lineage(bigint,text,text) esiste');

-- ---- 5..7: forma (set colonne) -------------------------------------------
SELECT columns_are('vendite', 'vw_documento_lineage_nodi',
    ARRAY['tipo_id','uid','codice','stato_codice_interno','stato_codice',
          'stato_descrizione','fase','is_abortito','pipeline_rank',
          -- rev 2026-08-21: la natura del documento (solo nodi FATTURA)
          'natura_doc_codice_interno','natura_doc_descrizione',
          -- ⭐ rev 2026-08-29: il CODICE del tipo accanto al suo id, cosi' i
          -- consumatori smettono di rifarsi il join a config.sorgenti (dieci
          -- copie a mano nel backend). ⛔ `_codice_interno` e non `_codice`:
          -- e' la colonna immutabile, e §6c vieta di chiamarla col nome
          -- dell'altra — il guardrail CI fallisce sul pattern.
          'tipo_codice_interno'],
    'colonne di vw_documento_lineage_nodi');

SELECT columns_are('vendite', 'vw_documento_lineage_archi',
    ARRAY['from_tipo_id','from_uid','from_codice','to_tipo_id','to_uid','to_codice',
          'to_stato_codice_interno','to_fase','to_is_abortito','ruolo','arco',
          -- rev 2026-08-21: la proprieta' «ramo di ritorno» vive QUI, una volta
          -- sola: prima la lettera 'R' era ripetuta a mano in tre posti.
          'is_ramo_inverso','from_natura_doc_codice_interno','to_natura_doc_codice_interno',
          -- ⭐ rev 2026-08-28: il rango DICHIARATO della sorgente. Vive qui per
          -- la stessa ragione di is_ramo_inverso — una proprieta' dell'arco,
          -- calcolata una volta sola — e serve alla CTE inc della summary, che
          -- prima sceglieva il root su from_tipo_id, cioe' su un id di seed.
          'rango_origine'],
    'colonne di vw_documento_lineage_archi');

-- ⭐ rev 2026-10-11: le colonne della SINTESI, nell'ordine, dal catalogo
--   (vendite.vw_documento_lineage_sintesi_colonne): e' il contratto che liste e
--   drawer uniscono alle righe.
SELECT is(
    (SELECT array_agg(colonna ORDER BY posizione) FROM vendite.vw_documento_lineage_sintesi_colonne),
    ARRAY['tipo_id','uid','codice','stato_codice_interno','stato_codice','stato_descrizione',
          'fase','is_abortito','pratica_id','pratica_numero','n_pratiche',
          'frontiera_tipo_id','frontiera_uid','frontiera_codice',
          'frontiera_stato_codice_interno','frontiera_fase',
          'n_discendenti_diretti','n_discendenti_attivi','is_transitato',
          'n_sorgenti','root_tipo_id','root_uid','root_codice',
          -- rev 2026-08-21: la natura del nodo, perche' una lista di fatture
          -- smetta di scrivere «Fattura» sopra una nota di credito.
          'natura_doc_codice_interno','natura_doc_descrizione',
          -- ⭐ rev 2026-08-28 (20260828-22): la natura del nodo di FRONTIERA.
          -- ⛔ QUI STAVA SCRITTO, PER TRE VERSIONI, PERCHE' QUESTA COLONNA NON
          -- DOVEVA ESISTERE — ed e' la ragione per cui il commento sta ancora
          -- qui invece di essere cancellato. Prima diceva «l'arco N e' escluso
          -- dal grafo forward, quindi una NC non e' mai frontiera e la colonna
          -- varrebbe sempre NULL»: premessa giusta, conclusione falsa, perche'
          -- l'arco G (commessa -> fattura) NON e' un ramo di ritorno e una nota
          -- di credito E' raggiungibile in avanti — lo dice il test 30, ed era
          -- gia' misurato il 2026-08-21. Poi, corretta quella, diceva «non c'e'
          -- perche' il consumatore la ricava da se'»: vero per UNO (il pannello
          -- del drawer, che legge questa vista e quindi ha frontiera_uid) e
          -- falso per tutte le viste di LISTA, che frontiera_uid non la
          -- proiettano e senza la chiave del nodo non hanno modo onesto di
          -- leggere la natura.
          -- ⚠️ Tre versioni della stessa frase, e nessuna e' mai fallita: un
          -- commento e' la specie che non si accorge di essere sbagliata. La
          -- colonna adesso c'e', e il test 40 qui sotto dice COSA contiene —
          -- che e' l'unica forma che fallisce.
          -- ⚠️ Sta in ULTIMA posizione, e non accanto alle sorelle frontiera_*,
          -- perche' CREATE OR REPLACE VIEW puo' solo appendere: chi rilegge
          -- questo elenco non ci veda un disordine da sistemare.
          'frontiera_natura_doc_codice_interno',
          -- ⭐ rev 2026-08-29: il codice del tipo, del nodo e della frontiera.
          'tipo_codice_interno','frontiera_tipo_codice_interno']::text[],
    'colonne della sintesi (fn_documento_lineage_sintesi), nell''ordine');

-- ---- 8..10: security_invoker=on sulle 3 viste ----------------------------
SELECT ok(
    EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) opt
             WHERE c.oid = 'vendite.vw_documento_lineage_nodi'::regclass
               AND opt IN ('security_invoker=on','security_invoker=true')),
    'nodi: security_invoker attivo');
SELECT ok(
    EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) opt
             WHERE c.oid = 'vendite.vw_documento_lineage_archi'::regclass
               AND opt IN ('security_invoker=on','security_invoker=true')),
    'archi: security_invoker attivo');
SELECT ok(
    (SELECT NOT p.prosecdef AND p.provolatile = 's' FROM pg_proc p
      WHERE p.oid = 'vendite.fn_documento_lineage_sintesi(bigint[], text[])'::regprocedure),
    'sintesi: SECURITY INVOKER e STABLE (la RLS resta di chi legge)');

-- ---- 11..12: proprieta' della funzione -----------------------------------
SELECT is(
    (SELECT provolatile::text FROM pg_proc
      WHERE oid = 'vendite.fn_documento_lineage(bigint,text,text)'::regprocedure),
    's', 'fn_documento_lineage e'' STABLE');
SELECT is(
    (SELECT prosecdef FROM pg_proc
      WHERE oid = 'vendite.fn_documento_lineage(bigint,text,text)'::regprocedure),
    false, 'fn_documento_lineage e'' SECURITY INVOKER');

-- ---- 13..16: invarianti strutturali sugli archi/nodi ---------------------
-- ⭐ VOCABOLARIO CHIUSO, ED E' UN CRICCHETTO VOLUTO: ogni arco nuovo fa
--    fallire questo test finche' non lo si DICHIARA qui. E' l'unico posto del
--    progetto che enumera le lettere (verificato il 2026-08-28: il frontend
--    legge `is_ramo_inverso`, non la lettera; fn_documento_lineage e la
--    summary pure). ⛔ Chi allarga l'elenco aggiunge anche l'asserzione che
--    dice COSA SIGNIFICA la lettera nuova — sotto, come per R e N. Allargare
--    e basta trasformerebbe un cricchetto in una formalita'.
--    · T aggiunto il 2026-08-28 (reso -> DDT di ri-consegna),
--      brief-db-ddt-riconsegna-eredita-testata §9.4.1.
--    · U aggiunto il 2026-08-28 (DDT -> commessa, la quarta sorgente di
--      commessa), brief-db-lineage-residui-root-e-sorgente-ddt §2.
--    · V aggiunto il 2026-11-01 (revisione dell'offerta, madre -> figlia),
--      brief-modello-documento-vendita §17.7; il significato e' il test 48.
--      Il 20261031-23 l'aveva fatta nascere senza dichiararla qui e senza
--      rango: i due cricchetti l'hanno presa, che e' il loro mestiere.
-- ⛔ E DAL 2026-08-28 IL CRICCHETTO E' DOPPIO: il test 41 chiede a ogni arco
--    anche un rango_origine. Una lettera nuova che passasse di qui senza
--    rango non farebbe fallire QUESTO test — passerebbe l'elenco e prenderebbe
--    un ordinamento silenzioso nel root. Le due asserzioni vanno lette
--    insieme: l'elenco dice CHI esiste, il rango dice QUANTO conta.
SELECT is(
    (SELECT count(*)::int FROM _lin_archi
      WHERE arco NOT IN ('A','B','C','D','E','F','G','H','R','N','S','T','U','V')),
    0, 'archi: arco sempre in A..H,R,N,S,T,U,V');

SELECT is(
    (SELECT count(*)::int FROM _lin_archi
      WHERE arco = 'R'
        AND to_tipo_id <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'RESO_VENDITA')),
    0, 'archi: arco R punta sempre a un nodo RESO_VENDITA');

SELECT is(
    (SELECT count(*)::int FROM _lin_nodi
      WHERE pipeline_rank NOT BETWEEN 0 AND 5),
    0, 'nodi: pipeline_rank sempre in 0..5');

SELECT ok(
    EXISTS (SELECT 1 FROM config.sorgenti WHERE codice_interno = 'RESO_VENDITA' AND attivo IS TRUE),
    'config.sorgenti RESO_VENDITA seedato e attivo (prereq Step 1)');

-- ---- 17..20: invarianti sulla summary/frontiera --------------------------
SELECT is(
    (SELECT count(*)::int FROM _lin_summary WHERE frontiera_tipo_id IS NULL),
    0, 'summary: frontiera sempre valorizzata (il nodo stesso e'' candidato)');

-- Un RESO non e' mai raggiunto via forward (arco R escluso), quindi non e' mai
-- frontiera di un ALTRO documento. Un reso e' pero' legittimamente frontiera di
-- SE STESSO (foglia, lvl 0) -> escludere le origini che sono gia' un reso.
-- ⚠️ rev 2026-08-25: «frontiera di se stesso» vale finche' il reso NON e'
--   accreditato. Con l'arco S (reso -> nota di credito, che NON e' un ramo di
--   ritorno) un reso accreditato ed emesso prende la NOTA come frontiera — ed e'
--   il punto del cantiere, presidiato dai test 36 e 37. Questa invariante resta
--   vera lo stesso, perche' parla di chi PUNTA a un reso, non di dove va il reso:
--   l'arco S porta verso una FATTURA, e nessun arco forward porta a un reso.
SELECT is(
    (SELECT count(*)::int FROM _lin_summary
      WHERE frontiera_tipo_id = (SELECT id FROM config.sorgenti WHERE codice_interno = 'RESO_VENDITA')
        AND tipo_id           <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'RESO_VENDITA')),
    0, 'summary: RESO mai frontiera di un nodo non-reso (forward)');

SELECT is(
    (SELECT count(*)::int FROM _lin_summary
      WHERE n_discendenti_attivi > 0 AND frontiera_fase = 'CHIUSO'),
    0, 'invariante: discendenti attivi -> frontiera non CHIUSO');

SELECT is(
    (SELECT count(*)::int FROM _lin_summary
      WHERE fase <> 'CHIUSO' AND NOT is_abortito AND frontiera_fase = 'CHIUSO'),
    0, 'invariante: nodo attivo -> frontiera attiva');

-- ---- 21..24: guardie e default della funzione ----------------------------
SELECT throws_like(
    $$ SELECT * FROM vendite.fn_documento_lineage(0::bigint, 'x', 'avanti') $$,
    '%p_tipo_id non valido%', 'fn guard: p_tipo_id <= 0 solleva');
SELECT throws_like(
    $$ SELECT * FROM vendite.fn_documento_lineage(1::bigint, '', 'avanti') $$,
    '%p_uid non valido%', 'fn guard: p_uid vuoto solleva');
SELECT throws_like(
    $$ SELECT * FROM vendite.fn_documento_lineage(1::bigint, 'x', 'laterale') $$,
    '%p_direzione non valido%', 'fn guard: p_direzione non valida solleva');
SELECT lives_ok(
    $$ SELECT * FROM vendite.fn_documento_lineage(
           (SELECT id FROM config.sorgenti WHERE codice_interno = 'PREVENTIVO'),
           '00000000-0000-0000-0000-000000000000') $$,
    'fn: direzione di default (avanti) non solleva');

-- ---- 25..26: casi reali §5 (skip-able quando i dati non ci sono) ----------
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM vendite.preventivi WHERE numero = 'PRV0000185') THEN
        ok(
            EXISTS (
                SELECT 1 FROM vendite.fn_documento_lineage(
                    (SELECT id FROM config.sorgenti WHERE codice_interno = 'PREVENTIVO'),
                    (SELECT uid::text FROM vendite.preventivi WHERE numero = 'PRV0000185'),
                    'avanti')
                 WHERE arco = 'H'),
            '§5 PRV0000185: la catena forward raggiunge un DDT (arco H)')
    ELSE skip('PRV0000185 non presente nei dati', 1)
END;

SELECT CASE
    WHEN EXISTS (SELECT 1 FROM vendite.commesse WHERE id = 186) THEN
        ok(
            (SELECT count(*) FROM vendite.fn_documento_lineage(
                    (SELECT id FROM config.sorgenti WHERE codice_interno = 'COMMESSA'),
                    '186', 'indietro')
              WHERE ruolo IN ('ROOT','COLLEGATO')) >= 2,
            '§5 commessa 186: indietro trova >=2 sorgenti (ROOT+COLLEGATO)')
    ELSE skip('commessa id=186 non presente nei dati', 1)
END;

-- ---- 27..32: l'arco N (nota di credito) e la natura ----------------------
-- ⭐ L'arco N sta fra due nodi dello STESSO tipo: e' il primo del grafo, e la
--    coppia di controlli qui sotto e' quello che impedisce che diventi altro.
SELECT is(
    (SELECT count(*)::int FROM _lin_archi
      WHERE arco = 'N'
        AND (   from_tipo_id <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'FATTURA')
             OR to_tipo_id   <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'FATTURA'))),
    0, '27) archi: l''arco N sta sempre fra due nodi FATTURA');

-- Un arco X->X non direbbe una genealogia, direbbe un ciclo. Il traversal lo
-- scarterebbe comunque (ha il set dei visitati), ma la vista non deve produrlo.
SELECT is(
    (SELECT count(*)::int FROM _lin_archi
      WHERE arco = 'N' AND from_tipo_id = to_tipo_id AND from_uid = to_uid),
    0, '28) archi: l''arco N non e'' mai un cappio (nessun documento rettifica se stesso)');

-- ⭐ La proprieta' e la lettera devono dire la stessa cosa, nei DUE versi: se
--    un domani nascesse un terzo ramo di ritorno senza entrare nell'elenco,
--    questo test lo direbbe subito — ed e' l'unico posto che lo direbbe.
SELECT is(
    (SELECT count(*)::int FROM _lin_archi
      WHERE is_ramo_inverso <> (arco IN ('R','N'))),
    0, '29) archi: is_ramo_inverso e'' true esattamente per i rami di ritorno (R, N)');

-- ⭐⭐ IL PRESIDIO DELLA DECISIONE del 2026-08-21: l'arco N e' un ramo di
--    RITORNO e resta FUORI dal grafo forward della summary. Se ci entrasse, la
--    regola della frontiera (l'attivo piu' profondo) farebbe vincere la nota di
--    credito sulla fattura stessa, e ogni riga di lista cambierebbe frontiera —
--    senza errori e senza log, solo con un valore diverso.
--    ⚠️ E l'invariante NON e' «una NC non e' mai frontiera di nessuno»: questa
--    e' la prima formulazione che ho scritto ed era SBAGLIATA — l'ha detto
--    questo stesso test, diventando rosso. La nota di credito e' raggiungibile
--    in avanti dalla COMMESSA (arco G, che non e' un ramo di ritorno), e
--    misurato sul DB del 2026-08-21 e' gia' oggi la frontiera dell'ordine 240 e
--    della commessa 322: e' corretto, e' l'ultimo documento nato da quel lavoro.
--    Cio' che l'arco N non deve fare e' rendere la nota discendente della
--    FATTURA che rettifica — e una fattura, nel grafo forward, non ha archi
--    uscenti: la sua frontiera e' sempre se stessa. Misurato prima di
--    scriverlo: zero fatture con frontiera diversa da se'.
SELECT is(
    (SELECT count(*)::int
       FROM _lin_summary s
      WHERE s.tipo_id = (SELECT id FROM config.sorgenti WHERE codice_interno = 'FATTURA')
        AND NOT (s.frontiera_tipo_id = s.tipo_id AND s.frontiera_uid = s.uid)),
    0, '30) summary: una fattura e'' sempre frontiera di se stessa (l''arco N resta fuori dal forward)');

-- La natura e' un asse delle sole fatture: sugli altri sette rami dei nodi
-- deve restare NULL. Un valore li' vorrebbe dire che un ramo l'ha copiata.
SELECT is(
    (SELECT count(*)::int FROM _lin_nodi
      WHERE natura_doc_codice_interno IS NOT NULL
        AND tipo_id <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'FATTURA')),
    0, '31) nodi: la natura e'' valorizzata solo sui nodi FATTURA');

-- Spot-check sui dati reali, protetto da skip come i due del §5: senza una
-- nota di credito in archivio non c'e' niente da misurare.
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM _lin_archi WHERE arco = 'N') THEN
        is(
            (SELECT count(*)::int
               FROM _lin_archi a
              WHERE a.arco = 'N'
                AND a.to_natura_doc_codice_interno   = 'NOTA_CREDITO'
                AND a.from_natura_doc_codice_interno IS DISTINCT FROM 'NOTA_CREDITO'),
            (SELECT count(*)::int FROM _lin_archi WHERE arco = 'N'),
            '32) §44: ogni arco N va da un documento non-NC a una NOTA DI CREDITO'
        )
    ELSE
        skip('32) §44: nessuna nota di credito in archivio, spot-check saltato', 1)
END;

-- ---- 33..38: l'arco S (reso -> nota di credito) e il perimetro RLS -------
-- ⭐ Il grafo si fermava sul reso: la nota di credito che lo accredita era
--    collegata alla fattura che rettifica (arco N) e alla commessa (arco G), ma
--    NON al reso. Il dato c'era gia' ed era esatto — vendite.resi_righe_accrediti
--    dal 2026-08-18 — solo che nessuno lo leggeva.
-- ⭐ S NON e' un ramo di ritorno, ed e' la decisione portante: e' l'AVANZAMENTO
--    del reso (la merce e' tornata, adesso si accredita), come H lo e'
--    dell'ordine. Il presidio di quella scelta e' il test 29 qui sopra, che
--    diventa rosso se qualcuno aggiunge S ai rami di ritorno «per simmetria».

SELECT is(
    (SELECT count(*)::int FROM _lin_archi
      WHERE arco = 'S'
        AND from_tipo_id <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'RESO_VENDITA')),
    0, '33) archi: l''arco S parte sempre da un nodo RESO_VENDITA');

SELECT is(
    (SELECT count(*)::int FROM _lin_archi
      WHERE arco = 'S'
        AND to_tipo_id <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'FATTURA')),
    0, '34) archi: l''arco S arriva sempre a un nodo FATTURA');

-- ⭐ Il tipo del nodo non basta: vendite.fatture e' UNA tabella, e fattura e nota
--    di credito si distinguono SOLO per natura_doc_id (e' il motivo per cui la
--    natura e' stata portata sul nodo il 2026-08-21). L'invariante e' tenuta in
--    DUE punti indipendenti, e nessuno dei due deriva la natura dal segno:
--      · vendite.fn_accredita_riga_reso — l'UNICO scrittore di
--        resi_righe_accrediti — la IMPONE:
--        v_natura_nc := config.fn_get_natura_doc_fiscale_id('NOTA_CREDITO'),
--        con E_CONFIG_MANCANTE se quella natura non e' a catalogo;
--      · vendite.fn_build_fattura_key la porta DENTRO la chiave di aggregazione
--        (rev 2026-08-18, N3: «e'' cio' che impedisce a un'attivita' di rettifica
--        di finire nella fattura ordinaria»), e trg_fatture_lock_natura_doc la
--        blocca sulla testata.
--    Se questo test diventa rosso uno dei due si e' rotto: e' un difetto, non un
--    caso legittimo.
-- ⚠️ IS DISTINCT FROM e non <>: fatture.natura_doc_id e' NULLABLE e il nodo la
--    espone in LEFT JOIN. Con <> una natura a NULL darebbe NULL, la riga non
--    verrebbe contata e il test passerebbe PROPRIO sul caso peggiore.
SELECT is(
    (SELECT count(*)::int FROM _lin_archi
      WHERE arco = 'S'
        AND to_natura_doc_codice_interno IS DISTINCT FROM 'NOTA_CREDITO'),
    0, '35) archi: l''arco S arriva sempre a una NOTA DI CREDITO');

-- ⭐ Il presidio della decisione «S non e' un ramo di ritorno», lato discendenti:
--    e' cio' che fa smettere al reso di essere una foglia.
SELECT is(
    (SELECT count(*)::int FROM _lin_summary s
      WHERE EXISTS (SELECT 1 FROM _lin_archi a
                     WHERE a.arco = 'S' AND a.from_tipo_id = s.tipo_id AND a.from_uid = s.uid)
        AND NOT s.is_transitato),
    0, '36) summary: un reso con arco S non e'' piu'' una foglia (is_transitato)');

-- ⭐ Lo stesso presidio, lato frontiera: «questo reso e' gia' stato accreditato,
--    con QUEL documento». Marcare S come inverso lo lascerebbe frontiera di se'
--    stesso, cioe' al punto di partenza.
-- ⚠️ L'invariante e' INCONDIZIONATA rispetto allo stato del reso, e va detto
--    perche' non sembri una svista: nel row_number() della frontiera il nodo
--    stesso sta a lvl 0 e la nota a lvl 1; a parita' di rango (nota attiva ->
--    rango 0) il tie-break e' lvl DESC, quindi la nota vince SEMPRE, che il reso
--    sia chiuso o no. Il filtro sulla fase serve solo a escludere le note chiuse
--    o abortite, per le quali il reso resta legittimamente frontiera di se'.
SELECT is(
    (SELECT count(*)::int
       FROM _lin_summary s
       JOIN _lin_archi a
         ON a.arco = 'S' AND a.from_tipo_id = s.tipo_id AND a.from_uid = s.uid
      WHERE a.to_fase <> 'CHIUSO'
        AND NOT COALESCE(a.to_is_abortito, false)
        AND s.frontiera_tipo_id = s.tipo_id
        AND s.frontiera_uid     = s.uid),
    0, '37) summary: la frontiera di un reso accreditato e'' la nota, non se stesso');

-- ⭐⭐ IL PRESIDIO DEL PERIMETRO, ed e' generale: non parla dell'arco S.
--    Ogni ramo della vista deve passare dalle TABELLE-TESTATA dei due documenti
--    che collega, perche' sono quelle che portano la RLS. Le tabelle-ponte
--    (commesse_sorgenti, attivita_fatturabili, resi_righe, resi_righe_accrediti)
--    hanno relrowsecurity = f e non danno nessun perimetro: un ramo che si ferma
--    li' produce un arco verso un documento che il chiamante NON puo' vedere, e
--    la decorazione non lo ferma perche' i join a vw_documento_lineage_nodi sono
--    LEFT — la riga resta, col codice a NULL.
--    Fino al 2026-08-24 lo facevano B, E, F (entrambi gli estremi) e G (la
--    commessa): quattro rami su dieci. Corretti da 20260825-19.
-- ⚠️ Questo test vale SOLO perche' la suite gira come zeroerp_app con la RLS
--    attiva (dal 2026-08-07). Con PGTAP_RUNNER=owner sarebbe verde per
--    costruzione e non presidierebbe niente: chi lo sposta lo spegne.
-- ⚠️ E non e' una riproduzione. Sul DB di sviluppo del 2026-08-25 la whitelist
--    dell'operatore copre tutte e 60 le commesse e tutti e 13 i resi, quindi
--    sarebbe verde anche con i rami vecchi. E' un presidio per il giorno in cui
--    un operatore sara' ristretto a un emittente.
-- ⭐ E' anche il collaudo delle chiavi POLIMORFE di commesse_sorgenti.sorgente_uid
--    (uid per il preventivo, id::text per ordine e contratto): un join scritto
--    con la chiave sbagliata non darebbe errore, azzererebbe quel gruppo di archi.
SELECT is(
    (SELECT count(*)::int
       FROM vendite.vw_documento_lineage_archi a
      WHERE NOT EXISTS (SELECT 1 FROM vendite.vw_documento_lineage_nodi n
                         WHERE n.tipo_id = a.from_tipo_id AND n.uid = a.from_uid)
         OR NOT EXISTS (SELECT 1 FROM vendite.vw_documento_lineage_nodi n
                         WHERE n.tipo_id = a.to_tipo_id   AND n.uid = a.to_uid)),
    0, '38) archi: nessun arco esce dal perimetro RLS (entrambi gli estremi visibili)');

-- ⭐ COSA SIGNIFICA L'ARCO T (2026-08-28) — reso -> DDT di RI-CONSEGNA.
--    Le due proprieta' che lo definiscono, insieme: parte da un RESO_VENDITA,
--    arriva a un DDT_VENDITA, e NON e' un ramo di ritorno.
-- ⭐ La seconda meta' e' quella che vale: T e' la GEMELLA di S — la merce e'
--    tornata (arco R, quello si' di ritorno) e adesso RIPARTE, come con S
--    torna il valore. Se un domani finisse dentro l'elenco dei rami inversi,
--    il reso smetterebbe di avere il DDT di ri-consegna come frontiera e
--    tornerebbe a essere una foglia — senza errori, solo con una colonna
--    diversa in ogni lista. Il 29) non lo direbbe: quello confronta la
--    proprieta' con l'elenco, e se cambiassero INSIEME resterebbe verde.
SELECT is(
    (SELECT count(*)::int FROM _lin_archi a
      WHERE a.arco = 'T'
        AND (a.from_tipo_id <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'RESO_VENDITA')
          OR a.to_tipo_id   <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'DDT_VENDITA')
          OR a.is_ramo_inverso)),
    0, '39) archi: T va da RESO_VENDITA a DDT_VENDITA ed e'' un AVANZAMENTO, non un ritorno');

-- ⭐ COSA PRESIDIA IL 40 — e perche' non e' una tautologia.
--    La summary porta la natura della frontiera dalla CTE `frontiera`, dove il
--    LEFT JOIN sui nodi c'era gia' per il pipeline_rank del tie-break. Qui la
--    si ri-deriva per la strada opposta: si rilegge il nodo di frontiera dalla
--    sua CHIAVE (frontiera_tipo_id, frontiera_uid) e si confronta.
-- ⛔ L'ERRORE CHE PRENDE, ed e' quello plausibile: esporre la natura del NODO
--    PROPRIO al posto di quella del nodo di FRONTIERA — cioe' scrivere
--    `n.natura_doc_codice_interno` dove va `fr.d_natura_doc_codice_interno`. Le due colonne
--    hanno lo stesso tipo, la vista si crea senza un errore, e su OGNI nodo che
--    e' frontiera di se stesso (che sono la maggioranza) i due valori
--    coincidono: il difetto si vedrebbe solo sulle righe che il chip «Transito»
--    esiste per rendere. Verde per costruzione ovunque tranne dove serve.
-- ⚠️ IS DISTINCT FROM e non <>: la natura e' NULL su sette tipi di nodo su
--    otto ed e' corretto, e con <> quelle righe non entrerebbero MAI nel
--    conteggio — il test sarebbe verde anche se la colonna fosse sempre NULL.
-- ⚠️ Seed-agnostico: vale anche su un DB vuoto, dove conta zero righe e
--    asserisce zero. Non e' una riproduzione del caso del reso 24.
SELECT is(
    (SELECT count(*)::int
       FROM _lin_summary s
      WHERE s.frontiera_tipo_id IS NOT NULL
        AND s.frontiera_natura_doc_codice_interno IS DISTINCT FROM
            (SELECT n.natura_doc_codice_interno
               FROM _lin_nodi n
              WHERE n.tipo_id = s.frontiera_tipo_id
                AND n.uid     = s.frontiera_uid)),
    0, '40) summary: frontiera_natura_doc_codice_interno e'' la natura del nodo di FRONTIERA');

-- ---- 41..43: l'arco U e il rango dichiarato -------------------------------

-- ⭐ IL CRICCHETTO DEL RANGO, gemello del 13 e per la stessa ragione.
--    rango_origine e' un CASE sulla lettera senza ELSE: un arco nuovo non
--    elencato li' vale NULL. E NULL non fa rumore — nella CTE inc finirebbe
--    semplicemente in fondo all'ORDER BY (ASC mette i NULL per ultimi), cioe'
--    l'arco nuovo non sarebbe MAI il root di nessuno, in silenzio.
-- ⛔ E' il motivo per cui anche R e N un rango ce l'hanno pur essendo rami di
--    ritorno, che nella inc non entrano mai: un'eccezione «tanto non serve» e'
--    il buco da cui passa il prossimo arco senza rango.
SELECT is(
    (SELECT count(*)::int FROM _lin_archi
      WHERE rango_origine IS NULL),
    0, '41) archi: ogni arco ha un rango_origine dichiarato');

-- ⭐ IL PRESIDIO DELLA CHIAVE POLIMORFA, sul ramo appena nato.
--    commesse_sorgenti.sorgente_uid segue config.sorgenti.key_selector: 'uid'
--    per il preventivo, 'id' per ordine, contratto e DDT. Il ramo U usa
--    d.id::text — e se un giorno qualcuno lo «allineasse» al ramo B copiandogli
--    d.uid::text, non ci sarebbe NESSUN errore: il join non troverebbe piu'
--    niente e il gruppo di archi U si azzererebbe. Le commesse tornerebbero
--    senza origine come prima, e nessun test se ne accorgerebbe.
-- ⚠️ Il test parte dalla RIGA e cerca l'arco, non viceversa: e' l'unico verso
--    che vede un gruppo di archi SPARITO. Contare gli archi U non lo direbbe —
--    zero archi e' anche il risultato di un DB senza righe DDT_VENDITA.
-- ⚠️ I due join alle testate non sono decorativi nemmeno qui: sotto RLS una
--    riga la cui commessa o il cui DDT non sono visibili non deve produrre
--    arco, quindi non deve nemmeno essere pretesa da questa asserzione.
SELECT is(
    (SELECT count(*)::int
       FROM vendite.commesse_sorgenti cs
       JOIN config.sorgenti s ON s.id = cs.sorgente_tipo_id
                             AND s.codice_interno = 'DDT_VENDITA'
       JOIN vendite.ddt      d  ON d.id::text = cs.sorgente_uid
       JOIN vendite.commesse cm ON cm.id      = cs.commessa_id
      WHERE NOT EXISTS (
              SELECT 1 FROM _lin_archi a
               WHERE a.arco     = 'U'
                 AND a.from_uid = d.id::text
                 AND a.to_uid   = cm.id::text)),
    0, '42) archi: ogni sorgente DDT di commessa produce il suo arco U');

-- ⭐⭐ LA REGOLA DEL ROOT, ASSERITA COME REGOLA E NON COME DATO.
--    Non ricopia l'ORDER BY della CTE inc — sarebbe una tautologia. Dice la
--    proprieta' che quell'ORDER BY deve produrre: fra tutti gli archi forward
--    che entrano in un nodo, quello scelto come root non deve essere battuto
--    da nessun altro. Seed-agnostica: su un DB vuoto conta zero e asserisce
--    zero, e non nomina nessun documento reale.
-- ⛔ L'ERRORE CHE PRENDE, ed e' quello vero: root_tipo_id, root_uid e
--    root_codice escono da TRE array_agg separati che devono avere lo stesso
--    ORDER BY. Se uno solo divergesse, il root sarebbe composto a pezzi presi
--    da archi DIVERSI — un documento che non esiste, senza nessun errore.
--    Qui il join cerca UN arco che vada davvero da (root_tipo_id, root_uid) al
--    nodo: un root composto a pezzi non lo trova e il conteggio non torna.
-- ⚠️ L'ordine dei criteri e' replicato per PROPRIETA', non per copia:
--    (ruolo='ROOT') DESC NULLS LAST mette prima TRUE, poi FALSE, poi NULL —
--    ed e' il CASE qui sotto, che vale 0/1/2. Chi cambiasse la regola nella
--    vista senza cambiarla qui vedrebbe rosso, che e' lo scopo.
-- ⛔ COSA QUESTO TEST NON PRENDE, e va detto invece di lasciarlo credere.
--    Provato per MUTAZIONE il 2026-08-28, riscrivendo la CTE inc in quattro
--    modi sbagliati e rigirando la suite:
--      · rango_origine DESC (la scala letta al contrario) ......... ROSSO
--      · ORDER BY senza (ruolo='ROOT') (la dichiarazione ignorata)  ROSSO
--      · il ritorno a from_tipo_id, cioe' al vecchio id di seed .... VERDE
--    L'ultima resta VERDE, e non e' un difetto del test: sul DB di sviluppo
--    del 2026-08-28 l'ordine accidentale degli id COINCIDE con la scala
--    dichiarata su ogni nodo, quindi il caso non e' producibile. E' un
--    PRESIDIO, non una riproduzione: diventera' rosso il giorno in cui i due
--    ordini divergeranno — che e' esattamente il giorno per cui esiste.
--    ⚠️ Chi lo legge non concluda «allora il rango non serviva»: la coincidenza
--    di oggi e' proprio la ragione per cui il difetto era invisibile.
SELECT is(
    (SELECT count(*)::int
       FROM _lin_summary s
       JOIN _lin_archi ar
         ON  ar.to_tipo_id   = s.tipo_id      AND ar.to_uid   = s.uid
         AND ar.from_tipo_id = s.root_tipo_id AND ar.from_uid = s.root_uid
         AND NOT ar.is_ramo_inverso
      WHERE s.root_tipo_id IS NOT NULL
        AND EXISTS (
              SELECT 1
                FROM _lin_archi a2
               WHERE a2.to_tipo_id = s.tipo_id AND a2.to_uid = s.uid
                 AND NOT a2.is_ramo_inverso
                 AND (CASE WHEN a2.ruolo = 'ROOT' THEN 0
                           WHEN a2.ruolo IS NOT NULL THEN 1 ELSE 2 END,
                      a2.rango_origine)
                   < (CASE WHEN ar.ruolo = 'ROOT' THEN 0
                           WHEN ar.ruolo IS NOT NULL THEN 1 ELSE 2 END,
                      ar.rango_origine))),
    0, '43) summary: nessun arco entrante batte il ROOT scelto (regola dichiarata)');

-- ⭐⭐ IL ROOT E' UN ARCO CHE ESISTE, e questo test nasce da un buco del 43.
--    root_tipo_id, root_uid e root_codice escono da TRE array_agg separati
--    della CTE inc. Devono avere lo stesso ORDER BY: se uno solo divergesse,
--    il root verrebbe composto a PEZZI presi da archi diversi — il tipo di uno
--    e l'uid di un altro — cioe' un documento che non esiste, senza nessun
--    errore da nessuna parte.
-- ⛔ IL 43 DA SOLO NON LO VEDE, ed e' stato misurato: disallineando UN solo
--    array_agg il test 43 resta VERDE. Il motivo e' istruttivo e vale oltre
--    questo file — il 43 fa un JOIN sull'arco scelto e conta le violazioni, e
--    un root composto a pezzi NON TROVA nessun arco: il nodo esce dal join e
--    smette di essere contato. Un test che conta i cattivi diventa muto
--    proprio quando il dato e' cosi' rotto da sparire dal conteggio.
-- ⚠️ Per questo qui si conta al contrario: si parte dai nodi che DICHIARANO un
--    root e si pretende che l'arco esista. Le due asserzioni vanno insieme —
--    il 44 dice che il root e' una riga vera, il 43 che e' la riga giusta.
SELECT is(
    (SELECT count(*)::int
       FROM _lin_summary s
      WHERE s.root_tipo_id IS NOT NULL
        AND NOT EXISTS (
              SELECT 1 FROM _lin_archi a
               WHERE a.to_tipo_id   = s.tipo_id      AND a.to_uid   = s.uid
                 AND a.from_tipo_id = s.root_tipo_id AND a.from_uid = s.root_uid
                 AND NOT a.is_ramo_inverso)),
    0, '44) summary: il ROOT corrisponde a un arco entrante che esiste davvero');

-- ⭐ 45..46 — IL CODICE DEL TIPO DICE DAVVERO IL TIPO.
--    Non e' una tautologia: la colonna esiste per SOSTITUIRE dieci join a
--    config.sorgenti scritti a mano, e qui si rifa' quel join una volta sola,
--    dalla parte opposta, per pretendere lo stesso risultato.
-- ⛔ L'errore che prende e' quello che ha reso necessaria la colonna: un join
--    sbagliato o dimenticato. E ne prende uno peggiore — `s.codice` al posto
--    di `s.codice_interno`: oggi i due valori COINCIDONO su tutte e 15 le
--    righe di config.sorgenti, quindi il difetto sarebbe invisibile finche'
--    qualcuno non rinomina un codice a video. Qui il confronto e' esplicito
--    contro codice_interno, che e' la colonna immutabile.
-- ⚠️ Seed-agnostici: su un DB vuoto contano zero e asseriscono zero.
SELECT is(
    (SELECT count(*)::int
       FROM _lin_summary s
       JOIN config.sorgenti so ON so.id = s.tipo_id
      WHERE s.tipo_codice_interno IS DISTINCT FROM so.codice_interno),
    0, '45) summary: tipo_codice_interno e'' il codice_interno di tipo_id');

SELECT is(
    (SELECT count(*)::int
       FROM _lin_summary s
       JOIN config.sorgenti so ON so.id = s.frontiera_tipo_id
      WHERE s.frontiera_tipo_id IS NOT NULL
        AND s.frontiera_tipo_codice_interno IS DISTINCT FROM so.codice_interno),
    0, '46) summary: frontiera_tipo_codice_interno e'' il codice_interno della frontiera');

-- ⭐ 47 — IL NODO LEGGE LA SEDE UNICA, e non una copia della regola.
--    La composizione del numero documento vive in
--    vendite.fn_numero_documento_fattura (20260829-15). Qui si pretende che il
--    `codice` del nodo FATTURA sia ESATTAMENTE quello che la sede unica
--    produce sulla stessa riga.
-- ⛔ L'ERRORE CHE PRENDE e' il piu' probabile di tutti su questa vista: che
--    qualcuno, dovendo toccare il ramo FATTURA, ricomponga la regola a mano
--    invece di chiamare la funzione. Non darebbe nessun errore — darebbe un
--    formato leggermente diverso, e a quel punto le sedi tornerebbero due.
--    Il test 5 (columns_are) non lo vedrebbe: il nome della colonna e il tipo
--    non cambiano.
-- ⛔ COSA QUESTO TEST NON PRENDE, e va detto invece di lasciarlo credere.
--    NON verifica che il FORMATO sia giusto: confronta il nodo con la STESSA
--    funzione, quindi i due lati si muovono insieme. Provato per mutazione il
--    2026-08-29 — aggiungendo STRICT alla funzione, o togliendole il ramo
--    della serie vuota, questo test resta VERDE mentre
--    test-fn-numero-documento-fattura.sql diventa rosso (2 e 3 asserzioni).
-- ⭐ Ed e' la divisione dei compiti voluta: la CORRETTEZZA della regola sta
--    nel file della funzione, qui sta solo che il nodo la CHIAMI invece di
--    ricopiarla. Due domande diverse, due sedi diverse — che e' poi la stessa
--    ragione per cui la sede unica esiste.
-- ⚠️ La forma e' quella dei presidi «riga per riga» di questo file: si conta
--    quante righe DISSENTONO, e si pretende zero. Seed-agnostico — su un DB
--    senza fatture conta zero e asserisce zero, e non nomina nessun documento.
-- ⚠️ IS DISTINCT FROM e non <>: il codice e' NULL su ogni fattura non ancora
--    numerata (4 su 22 il 2026-08-29), e con <> quelle righe non entrerebbero
--    MAI nel conteggio — il test resterebbe verde anche se il ramo tornasse a
--    mostrare il contatore nudo su tutte le altre.
SELECT is(
    (SELECT count(*)::int
       FROM _lin_nodi n
       JOIN config.sorgenti s ON s.id = n.tipo_id AND s.codice_interno = 'FATTURA'
       JOIN vendite.fatture f ON f.id::text = n.uid
      WHERE n.codice IS DISTINCT FROM
            vendite.fn_numero_documento_fattura(f.numero, f.serie)::varchar),
    0, '47) nodi: il codice di un nodo FATTURA e'' quello della sede unica');

-- ---- 48: l'arco V, la revisione dell'offerta ------------------------------
-- ⭐ COSA SIGNIFICA LA LETTERA V (il cricchetto del 13 lo chiede): l'arco va
--    dalla revisione madre alla figlia, entrambe OFFERTA_COMMERCIALE, e la
--    figlia ha davvero quella madre in revisione_padre_id. Non e' un ramo di
--    ritorno (si legge nel verso del pannello, come C e D), e non e'
--    un'origine: il rango e' il piu' basso di tutti, sotto ogni arco che lo
--    e'. La sintesi e le origini della fattura lo scartano per lettera.
-- ⚠️ Invariante sugli archi che ci sono, come il 14: su un DB senza revisioni
--    conta zero righe e asserisce zero. E' un presidio, non una riproduzione.
SELECT is(
    (SELECT count(*)::int
       FROM _lin_archi a
      WHERE a.arco = 'V'
        AND (   a.from_tipo_id IS DISTINCT FROM (SELECT id FROM config.sorgenti WHERE codice_interno = 'OFFERTA_COMMERCIALE')
             OR a.to_tipo_id   IS DISTINCT FROM (SELECT id FROM config.sorgenti WHERE codice_interno = 'OFFERTA_COMMERCIALE')
             OR a.is_ramo_inverso
             OR a.rango_origine IS NULL
             OR EXISTS (SELECT 1 FROM _lin_archi o
                         WHERE o.arco <> 'V' AND o.rango_origine >= a.rango_origine)
             OR NOT EXISTS (SELECT 1
                              FROM vendite.offerte_commerciali figlia
                              JOIN vendite.offerte_commerciali madre ON madre.id = figlia.revisione_padre_id
                             WHERE figlia.uid::text = a.to_uid
                               AND madre.uid::text  = a.from_uid))),
    0, '48) archi: V va dalla revisione madre alla figlia, in avanti, col rango piu'' basso');

SELECT * FROM finish();
ROLLBACK;
