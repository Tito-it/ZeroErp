-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: Lineage documenti vendite (Step 5).
--   Oggetti: vendite.vw_documento_lineage_nodi, vw_documento_lineage_archi,
--            vw_documento_lineage, vendite.fn_documento_lineage.
--   Brief: brief-db-lineage-documenti-vendite §5.
--
-- Impostazione: la maggior parte dei test e' SEED-AGNOSTICA (forma degli oggetti,
--   security_invoker, invarianti che valgono su QUALSIASI dato — anche DB vuoto).
--   I 2 spot-check sui casi reali §5 (PRV0000185, commessa 186) sono protetti da
--   skip() quando i dati non sono presenti (es. CI su DB fresco).
--
-- Indice test (1..38):
--    1) vw_documento_lineage_nodi esiste
--    2) vw_documento_lineage_archi esiste
--    3) vw_documento_lineage esiste
--    4) fn_documento_lineage(bigint,text,text) esiste
--    5) colonne di vw_documento_lineage_nodi
--    6) colonne di vw_documento_lineage_archi
--    7) colonne di vw_documento_lineage
--    8) nodi: security_invoker attivo
--    9) archi: security_invoker attivo
--   10) summary: security_invoker attivo
--   11) fn: STABLE
--   12) fn: SECURITY INVOKER (NON definer)
--   13) archi: arco solo in A..H,R,N,S
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

SELECT plan(38);

-- ---- 1..4: esistenza oggetti ---------------------------------------------
SELECT has_view('vendite', 'vw_documento_lineage_nodi',  'vw_documento_lineage_nodi esiste');
SELECT has_view('vendite', 'vw_documento_lineage_archi', 'vw_documento_lineage_archi esiste');
SELECT has_view('vendite', 'vw_documento_lineage',       'vw_documento_lineage esiste');
SELECT has_function('vendite', 'fn_documento_lineage',
                    ARRAY['bigint','text','text'],
                    'fn_documento_lineage(bigint,text,text) esiste');

-- ---- 5..7: forma (set colonne) -------------------------------------------
SELECT columns_are('vendite', 'vw_documento_lineage_nodi',
    ARRAY['tipo_id','uid','codice','stato_codice_interno','stato_codice',
          'stato_descrizione','fase','is_abortito','pipeline_rank',
          -- rev 2026-08-21: la natura del documento (solo nodi FATTURA)
          'natura_doc_codice','natura_doc_descrizione'],
    'colonne di vw_documento_lineage_nodi');

SELECT columns_are('vendite', 'vw_documento_lineage_archi',
    ARRAY['from_tipo_id','from_uid','from_codice','to_tipo_id','to_uid','to_codice',
          'to_stato_codice_interno','to_fase','to_is_abortito','ruolo','arco',
          -- rev 2026-08-21: la proprieta' «ramo di ritorno» vive QUI, una volta
          -- sola: prima la lettera 'R' era ripetuta a mano in tre posti.
          'is_ramo_inverso','from_natura_doc_codice','to_natura_doc_codice'],
    'colonne di vw_documento_lineage_archi');

SELECT columns_are('vendite', 'vw_documento_lineage',
    ARRAY['tipo_id','uid','codice','stato_codice_interno','stato_codice','stato_descrizione',
          'fase','is_abortito','pratica_id','pratica_numero','n_pratiche',
          'frontiera_tipo_id','frontiera_uid','frontiera_codice',
          'frontiera_stato_codice_interno','frontiera_fase',
          'n_discendenti_diretti','n_discendenti_attivi','is_transitato',
          'n_sorgenti','root_tipo_id','root_uid','root_codice',
          -- rev 2026-08-21: la natura del nodo, perche' una lista di fatture
          -- smetta di scrivere «Fattura» sopra una nota di credito.
          -- ⛔ NON c'e' una frontiera_natura_doc_codice, ma la ragione scritta
          -- qui fino al 2026-08-24 era FALSA e diceva: «l'arco N e' escluso dal
          -- grafo forward, quindi una NC non e' mai frontiera e quella colonna
          -- varrebbe sempre NULL». La premessa e' giusta, la conclusione no:
          -- l'arco G (commessa -> fattura) NON e' un ramo di ritorno, quindi una
          -- nota di credito E' raggiungibile in avanti — lo dice il test 30 qui
          -- sotto, ed era gia' misurato il 2026-08-21 (frontiera dell'ordine 240
          -- e della commessa 322). Dal 2026-08-25 l'arco S la rende frontiera
          -- anche del RESO. La colonna non c'e' perche' il consumatore la ricava
          -- da se' (get_lineage_nodo), NON perche' varrebbe sempre NULL.
          -- ⚠️ Era un COMMENTO, cioe' la specie che non fallisce mai: e' stato
          -- corretto sull'oggetto (20260825-20) e qui, insieme.
          'natura_doc_codice','natura_doc_descrizione'],
    'colonne di vw_documento_lineage');

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
    EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) opt
             WHERE c.oid = 'vendite.vw_documento_lineage'::regclass
               AND opt IN ('security_invoker=on','security_invoker=true')),
    'summary: security_invoker attivo');

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
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage_archi
      WHERE arco NOT IN ('A','B','C','D','E','F','G','H','R','N','S')),
    0, 'archi: arco sempre in A..H,R,N,S');

SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage_archi
      WHERE arco = 'R'
        AND to_tipo_id <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'RESO_VENDITA')),
    0, 'archi: arco R punta sempre a un nodo RESO_VENDITA');

SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage_nodi
      WHERE pipeline_rank NOT BETWEEN 0 AND 5),
    0, 'nodi: pipeline_rank sempre in 0..5');

SELECT ok(
    EXISTS (SELECT 1 FROM config.sorgenti WHERE codice_interno = 'RESO_VENDITA' AND attivo IS TRUE),
    'config.sorgenti RESO_VENDITA seedato e attivo (prereq Step 1)');

-- ---- 17..20: invarianti sulla summary/frontiera --------------------------
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage WHERE frontiera_tipo_id IS NULL),
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
    (SELECT count(*)::int FROM vendite.vw_documento_lineage
      WHERE frontiera_tipo_id = (SELECT id FROM config.sorgenti WHERE codice_interno = 'RESO_VENDITA')
        AND tipo_id           <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'RESO_VENDITA')),
    0, 'summary: RESO mai frontiera di un nodo non-reso (forward)');

SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage
      WHERE n_discendenti_attivi > 0 AND frontiera_fase = 'CHIUSO'),
    0, 'invariante: discendenti attivi -> frontiera non CHIUSO');

SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage
      WHERE fase <> 'CHIUSO' AND NOT is_abortito AND frontiera_fase = 'CHIUSO'),
    0, 'invariante: nodo attivo -> frontiera attiva');

-- ---- 21..24: guardie e default della funzione ----------------------------
SELECT throws_ok(
    $$ SELECT * FROM vendite.fn_documento_lineage(0::bigint, 'x', 'avanti') $$,
    NULL::text, NULL::text, 'fn guard: p_tipo_id <= 0 solleva');
SELECT throws_ok(
    $$ SELECT * FROM vendite.fn_documento_lineage(1::bigint, '', 'avanti') $$,
    NULL::text, NULL::text, 'fn guard: p_uid vuoto solleva');
SELECT throws_ok(
    $$ SELECT * FROM vendite.fn_documento_lineage(1::bigint, 'x', 'laterale') $$,
    NULL::text, NULL::text, 'fn guard: p_direzione non valida solleva');
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
    (SELECT count(*)::int FROM vendite.vw_documento_lineage_archi
      WHERE arco = 'N'
        AND (   from_tipo_id <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'FATTURA')
             OR to_tipo_id   <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'FATTURA'))),
    0, '27) archi: l''arco N sta sempre fra due nodi FATTURA');

-- Un arco X->X non direbbe una genealogia, direbbe un ciclo. Il traversal lo
-- scarterebbe comunque (ha il set dei visitati), ma la vista non deve produrlo.
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage_archi
      WHERE arco = 'N' AND from_tipo_id = to_tipo_id AND from_uid = to_uid),
    0, '28) archi: l''arco N non e'' mai un cappio (nessun documento rettifica se stesso)');

-- ⭐ La proprieta' e la lettera devono dire la stessa cosa, nei DUE versi: se
--    un domani nascesse un terzo ramo di ritorno senza entrare nell'elenco,
--    questo test lo direbbe subito — ed e' l'unico posto che lo direbbe.
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage_archi
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
       FROM vendite.vw_documento_lineage s
      WHERE s.tipo_id = (SELECT id FROM config.sorgenti WHERE codice_interno = 'FATTURA')
        AND NOT (s.frontiera_tipo_id = s.tipo_id AND s.frontiera_uid = s.uid)),
    0, '30) summary: una fattura e'' sempre frontiera di se stessa (l''arco N resta fuori dal forward)');

-- La natura e' un asse delle sole fatture: sugli altri sette rami dei nodi
-- deve restare NULL. Un valore li' vorrebbe dire che un ramo l'ha copiata.
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage_nodi
      WHERE natura_doc_codice IS NOT NULL
        AND tipo_id <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'FATTURA')),
    0, '31) nodi: la natura e'' valorizzata solo sui nodi FATTURA');

-- Spot-check sui dati reali, protetto da skip come i due del §5: senza una
-- nota di credito in archivio non c'e' niente da misurare.
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM vendite.vw_documento_lineage_archi WHERE arco = 'N') THEN
        is(
            (SELECT count(*)::int
               FROM vendite.vw_documento_lineage_archi a
              WHERE a.arco = 'N'
                AND a.to_natura_doc_codice   = 'NOTA_CREDITO'
                AND a.from_natura_doc_codice IS DISTINCT FROM 'NOTA_CREDITO'),
            (SELECT count(*)::int FROM vendite.vw_documento_lineage_archi WHERE arco = 'N'),
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
    (SELECT count(*)::int FROM vendite.vw_documento_lineage_archi
      WHERE arco = 'S'
        AND from_tipo_id <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'RESO_VENDITA')),
    0, '33) archi: l''arco S parte sempre da un nodo RESO_VENDITA');

SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage_archi
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
    (SELECT count(*)::int FROM vendite.vw_documento_lineage_archi
      WHERE arco = 'S'
        AND to_natura_doc_codice IS DISTINCT FROM 'NOTA_CREDITO'),
    0, '35) archi: l''arco S arriva sempre a una NOTA DI CREDITO');

-- ⭐ Il presidio della decisione «S non e' un ramo di ritorno», lato discendenti:
--    e' cio' che fa smettere al reso di essere una foglia.
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage s
      WHERE EXISTS (SELECT 1 FROM vendite.vw_documento_lineage_archi a
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
       FROM vendite.vw_documento_lineage s
       JOIN vendite.vw_documento_lineage_archi a
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

SELECT * FROM finish();
ROLLBACK;
