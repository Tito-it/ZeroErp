-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — questo file non interroga NESSUN dato: legge il
--   catalogo di PostgreSQL (pg_class, pg_depend, pg_rewrite). Un contesto
--   operatore non cambierebbe una riga del risultato, e metterlo darebbe
--   l'impressione che la RLS qui sia esercitata, che sarebbe falso.
--   Dichiarazione leggibile dal cancello scripts/guardrail_pgtap_preambolo.py:
--   distingue «escluso apposta» da «dimenticato».
-- pgtap-runner: owner
-- pgtap-runner-motivo: i test 3..5 CREANO viste di prova (in transazione, poi
--   annullata) perche' il criterio si prova solo COSTRUENDO i casi. E' DDL: il
--   ruolo applicativo non ne fa e non ne deve fare.
--
-- pgTAP test ANTI-REGRESSIONE — security_invoker su TUTTE le viste che toccano
-- dati protetti da RLS.
--
-- ChangeSet di riferimento: 20260601-26 (conversione), 20260706-15 (fix V-1),
--                           20260707-10 (ripristino), 20260907-04 (l'ultima
--                           scoperta, trovata proprio da questo criterio)
--
-- Indice test (plan 7):
--   1) ⭐ il criterio COPRE tutto cio' che i quattro elenchi a mano garantivano
--   2) ⛔ IL PRESIDIO: nessuna vista che tocca dati in RLS e' priva del flag
--   3) ⛔ il criterio e' TRANSITIVO: prende una vista che arriva alla tabella
--      attraverso un'altra vista (caso COSTRUITO)
--   4) ⚠️ e prende anche il caso diretto a un anello solo (caso COSTRUITO)
--   5) ⚠️ e NON prende una vista che dati protetti non ne tocca (caso COSTRUITO)
--   6) ⭐ (rev 2026-09-21) e ATTRAVERSA una FUNZIONE `BEGIN ATOMIC` INVOKER:
--      una vista che legge una tabella in RLS solo tramite la funzione resta
--      nel perimetro (caso COSTRUITO — e' la forma di vw_partite_merce)
--   7) ⛔ (rev 2026-09-21) ma una funzione SECURITY DEFINER in mezzo SPEGNE la
--      catena come una vista senza flag: la vista sopra e' un trasgressore,
--      anche col suo flag acceso (caso COSTRUITO)
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ IL PROBLEMA, E PERCHE' NON SI VEDE.
--   Una vista senza `security_invoker` gira come il suo OWNER. Se quell'owner
--   possiede anche le tabelle sottostanti — ed e' il caso: `titodb` le possiede
--   tutte — e la RLS non e' `FORCE`, l'owner ne e' ESENTE. La vista continua a
--   rispondere: risponde solo di piu'. Nessun errore, nessuna pagina rotta.
--   ⚠️ E la reloption NON compare in `pg_get_viewdef`: chi ricrea una vista
--   partendo dalla definizione stampata la perde senza nessun avviso.
--
-- ⛔ PERCHE' IL CRITERIO HA SOSTITUITO GLI ELENCHI (rev 2026-09-07).
--   Fino a oggi la stessa proprieta' era asserita in QUATTRO posti, tutti a
--   elenco:
--     * questo file           — 9 nomi scritti a mano;
--     * vendite/test-vw-dash-security-invoker.sql — le `vendite.vw_dash_*` per
--       PREFISSO, piu' una coda esplicita (ritirato oggi: confluito qui);
--     * quattro doppioni locali dentro test funzionali (tolti oggi);
--     * sei altri controlli sparsi, cinque dei quali confrontavano la GRAFIA.
--   ⚠️ Un elenco copre cio' che qualcuno si e' ricordato di scriverci. Le sette
--   viste `*stato_sorgente*` erano scoperte da sette settimane e sono state
--   trovate per caso; `script.vw_pratica_doc_sorgente` era scoperta da DUE MESI
--   e l'ha trovata questo criterio il 2026-09-07 (fix: 20260907-04). Quella
--   sfuggiva a tutti e tre i modi di cercarla: schema sbagliato, nome sbagliato,
--   e arrivava alle tabelle solo ATTRAVERSO altre viste.
--   ⭐ Il criterio non e' un'idea nuova: era gia' scritto, in prosa,
--   nell'intestazione del file ritirato — *«il modo per trovarne altre non e'
--   leggere questo elenco, e' rifare la misura»*. Qui la misura e' il test.
--
-- ⛔ E LA CATENA SI PERDE AL PRIMO ANELLO SPENTO, non all'ultimo.
--   `security_invoker` NON si propaga: da dentro una vista DEFINER, «il
--   chiamante» che gli anelli interni onorano e' l'owner della vista esterna.
--   Sei anelli accesi e uno spento fanno una catena spenta — ed e' esattamente
--   il caso del 20260907-04. Per questo il test 3 non e' un di piu': senza, il
--   criterio sarebbe cieco proprio dove il difetto e' vissuto piu' a lungo.
--
-- ⭐ E LA CATENA PASSA ANCHE PER LE FUNZIONI (rev 2026-09-21, D14 quarta leva).
--   vendite.vw_partite_merce e' la proiezione di vendite.fn_partite_merce: la
--   sua regola di riscrittura dipende da una FUNZIONE, non da tabelle. Se il
--   criterio si fermasse li', la vista USCIREBBE dal perimetro in silenzio (il
--   test 1 lo avrebbe detto, perche' la nomina; una vista nuova nella stessa
--   forma no). Si cammina quindi anche pg_proc → pg_depend: e' possibile SOLO
--   per le funzioni `BEGIN ATOMIC`, che registrano le dipendenze nel catalogo —
--   una `LANGUAGE sql` a stringa o una plpgsql sono OPACHE, e una vista che
--   arriva ai dati solo attraverso di loro non e' presidiabile da qui (e' la
--   ragione per cui una vista-proiezione si scrive su un corpo BEGIN ATOMIC).
--   ⛔ Una funzione SECURITY DEFINER in mezzo gira come il suo owner: e' un
--   anello SPENTO, esattamente come una vista senza flag — la catena e' spenta
--   e la vista sopra e' un trasgressore anche col flag acceso.
--
-- ⚠️ COSA QUESTO TEST NON DICE. Che una vista abbia il flag non significa che
--   la RLS a valle sia scritta bene: dice solo che verra' applicata a chi legge.
--   Le policy si provano nei file `test-rls-*` accanto a questo.
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- Il criterio, in un posto solo
-- ============================================================
-- ⭐ Ogni vista, e ogni tabella con RLS che raggiunge — anche attraverso altre
--   viste. La ricorsione e' il punto: vedi la nota sulla catena, in testa.
CREATE TEMP VIEW _tocca_rls AS
WITH RECURSIVE dip AS (
    -- Da che cosa dipende ogni vista: si legge dalla sua regola di riscrittura
    -- (tabelle, altre viste, e — rev 2026-09-21 — FUNZIONI).
    SELECT rw.ev_class AS da_oid, d.refobjid AS dip_oid, false AS spento
      FROM pg_rewrite rw
      JOIN pg_depend d ON d.objid = rw.oid AND d.classid = 'pg_rewrite'::regclass
     -- ⚠️ Una vista dipende anche da se stessa: senza questa riga la
     --   ricorsione non termina.
     WHERE d.refobjid <> rw.ev_class
    UNION ALL
    -- Da che cosa dipende ogni funzione `BEGIN ATOMIC`: le sue dipendenze
    -- stanno in pg_depend (una funzione a stringa non ne ha: e' opaca).
    -- ⛔ Una SECURITY DEFINER e' un anello SPENTO: si attraversa lo stesso —
    --   la vista sopra DEVE comparire — ma la catena porta il segno.
    SELECT p.oid, d.refobjid, p.prosecdef
      FROM pg_proc p
      JOIN pg_depend d ON d.objid = p.oid AND d.classid = 'pg_proc'::regclass
     WHERE p.prosqlbody IS NOT NULL
       AND d.refclassid IN ('pg_class'::regclass, 'pg_proc'::regclass)
       AND d.refobjid <> p.oid
), catena AS (
    SELECT v.oid AS vista_oid, d.dip_oid, d.spento
      FROM pg_class v JOIN dip d ON d.da_oid = v.oid
     WHERE v.relkind = 'v'
    UNION
    SELECT c.vista_oid, d.dip_oid, (c.spento OR d.spento)
      FROM catena c JOIN dip d ON d.da_oid = c.dip_oid
)
SELECT n.nspname::text AS sch,
       v.relname::text AS vista,
       -- Accesa SOLO se ha il flag E nessuna funzione DEFINER sul cammino
       -- verso una tabella protetta: sei anelli accesi e uno spento fanno
       -- una catena spenta (vedi la nota in testa).
       (COALESCE((SELECT o.option_value::boolean
                    FROM pg_options_to_table(v.reloptions) o
                   WHERE o.option_name = 'security_invoker'), false)
        AND NOT bool_or(c.spento)) AS invoker
  FROM catena c
  JOIN pg_class v     ON v.oid = c.vista_oid AND v.relkind = 'v'
  JOIN pg_namespace n ON n.oid = v.relnamespace
  JOIN pg_class t     ON t.oid = c.dip_oid
                     AND t.relkind = 'r'
                     AND t.relrowsecurity
 WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
 GROUP BY n.nspname, v.relname, v.reloptions;

-- ============================================================
-- 1. ⭐ LA MIGRAZIONE NON PERDE NIENTE
-- ============================================================
-- ⛔ Sostituire un elenco con un criterio si prova cosi', e non altrimenti: il
--   criterio deve contenere TUTTO cio' che gli elenchi nominavano. Senza questo
--   test, «zero trasgressori» sarebbe compatibile con una rete che ha smesso di
--   pescare — il verde per sottrazione, sul presidio peggiore su cui averlo.
-- ⚠️ Questi nomi restano scritti qui APPOSTA, ed e' l'unico elenco che
--   sopravvive: non e' il perimetro (quello lo decide il criterio), e' la prova
--   che il perimetro non si e' ristretto.
SELECT is_empty(
    $$WITH garantite (sch, vista) AS (
          VALUES
            -- i 9 nomi che questo file elencava prima del 2026-09-07
            ('vendite','vw_preventivi'), ('vendite','vw_preventivi_lista'),
            ('vendite','vw_preventivi_pratiche'),
            ('vendite','vw_preventivi_smistamento'),
            ('vendite','vw_preventivi_smistamento_righe'),
            ('vendite','vw_offerte_commerciali_lista'),
            ('anagrafiche','vw_clienti_lista'),
            ('anagrafiche','vw_clienti_codice_ba'),
            ('dbops','vw_diag_v_clienti_links'),
            -- la coda esplicita del file ritirato (vendite/test-vw-dash-security-invoker)
            ('vendite','vw_lotti_gruppi_serviti'),
            ('script','vw_stato_sorgente'),
            ('vendite','vw_stato_sorgente_contratto'),
            ('vendite','vw_stato_sorgente_ddt'),
            ('vendite','vw_stato_sorgente_offerta'),
            ('vendite','vw_stato_sorgente_ordine'),
            ('vendite','vw_stato_sorgente_preventivo'),
            ('vendite','vw_stato_sorgente_reso'),
            -- le sei presidiate a mano nei test funzionali, tolte oggi
            ('vendite','vw_contratti_lista'), ('vendite','vw_ordini_lista'),
            ('vendite','vw_partite_merce'), ('script','vw_giornale_entita'),
            ('vendite','vw_dash_competenza_attivita'),
            ('vendite','vw_dash_competenza_gruppi')
      )
      SELECT g.sch || '.' || g.vista
        FROM garantite g
       WHERE EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                      WHERE n.nspname = g.sch AND c.relname = g.vista AND c.relkind = 'v')
         AND NOT EXISTS (SELECT 1 FROM _tocca_rls r
                          WHERE r.sch = g.sch AND r.vista = g.vista)$$,
    '1. il criterio copre tutte le viste che i quattro elenchi a mano garantivano'
);

-- ============================================================
-- 2. ⛔ IL PRESIDIO
-- ============================================================
-- In fallimento il messaggio NOMINA le viste: su un difetto che non ha nessun
-- altro sintomo, sapere QUALE e' meta' del lavoro.
SELECT is(
    (SELECT string_agg(r.sch || '.' || r.vista, ', ' ORDER BY r.sch, r.vista)
       FROM _tocca_rls r WHERE NOT r.invoker),
    NULL,
    '2. nessuna vista che tocca dati in RLS gira come DEFINER'
);

-- ============================================================
-- I casi costruiti — da qui in giu' si semina
-- ============================================================
-- ⛔ Il test 2 gira PRIMA: dopo queste righe il database contiene apposta una
--   vista trasgressiva, e l'ordine non e' un dettaglio.
CREATE VIEW dbops.pgtap_si_ponte WITH (security_invoker = on) AS
    SELECT c.id FROM vendite.contratti c;

-- Due anelli: questa e' spenta, quella sotto e' accesa. La catena e' spenta.
CREATE VIEW dbops.pgtap_si_indiretta AS
    SELECT p.id FROM dbops.pgtap_si_ponte p;

-- Un anello solo, spenta.
CREATE VIEW dbops.pgtap_si_diretta AS
    SELECT c.id FROM vendite.contratti c;

-- Spenta, ma non tocca niente di protetto: NON deve entrare nel perimetro.
CREATE VIEW dbops.pgtap_si_innocua AS
    SELECT s.id FROM config.sorgenti s;

SELECT isnt_empty(
    $$SELECT vista FROM _tocca_rls
       WHERE sch = 'dbops' AND vista = 'pgtap_si_indiretta' AND NOT invoker$$,
    '3. il criterio prende una vista che arriva alla tabella ATTRAVERSO un''altra vista'
);

SELECT isnt_empty(
    $$SELECT vista FROM _tocca_rls
       WHERE sch = 'dbops' AND vista = 'pgtap_si_diretta' AND NOT invoker$$,
    '4. e prende anche il caso diretto, a un anello solo'
);

-- ⛔ Senza questo, il criterio potrebbe essere «ogni vista vuole il flag», che
--   e' una regola DIVERSA e sbagliata: una vista che non tocca dati protetti non
--   ha niente da filtrare, e pretenderglielo insegnerebbe a metterlo ovunque
--   per far tacere il test.
SELECT is_empty(
    $$SELECT vista FROM _tocca_rls
       WHERE sch = 'dbops' AND vista = 'pgtap_si_innocua'$$,
    '5. e NON prende una vista che dati protetti non ne tocca'
);

DROP VIEW dbops.pgtap_si_innocua;
DROP VIEW dbops.pgtap_si_diretta;
DROP VIEW dbops.pgtap_si_indiretta;
DROP VIEW dbops.pgtap_si_ponte;

-- ============================================================
-- 6-7) L'anello FUNZIONE (rev 2026-09-21): la forma di vw_partite_merce.
-- ⚠️ `BEGIN ATOMIC`, non `AS $$…$$`: solo cosi' la dipendenza dalla tabella
--   sta nel catalogo e il criterio ha qualcosa da leggere.
-- ============================================================
CREATE FUNCTION dbops.pgtap_si_fn_invoker() RETURNS TABLE(id bigint)
LANGUAGE sql STABLE
BEGIN ATOMIC
    SELECT c.id FROM vendite.contratti c;
END;

CREATE FUNCTION dbops.pgtap_si_fn_definer() RETURNS TABLE(id bigint)
LANGUAGE sql STABLE SECURITY DEFINER
BEGIN ATOMIC
    SELECT c.id FROM vendite.contratti c;
END;

-- Flag acceso, tabella raggiunta SOLO attraverso la funzione invoker: e' nel
-- perimetro ed e' in regola.
CREATE VIEW dbops.pgtap_si_via_fn WITH (security_invoker = on) AS
    SELECT f.id FROM dbops.pgtap_si_fn_invoker() f;

-- Flag acceso, ma la funzione in mezzo e' DEFINER: catena spenta, trasgressore.
CREATE VIEW dbops.pgtap_si_via_definer WITH (security_invoker = on) AS
    SELECT f.id FROM dbops.pgtap_si_fn_definer() f;

SELECT isnt_empty(
    $$SELECT vista FROM _tocca_rls
       WHERE sch = 'dbops' AND vista = 'pgtap_si_via_fn' AND invoker$$,
    '6. il criterio attraversa una funzione BEGIN ATOMIC invoker: la vista resta nel perimetro, in regola'
);

SELECT isnt_empty(
    $$SELECT vista FROM _tocca_rls
       WHERE sch = 'dbops' AND vista = 'pgtap_si_via_definer' AND NOT invoker$$,
    '7. una funzione SECURITY DEFINER in mezzo spegne la catena: la vista sopra e'' un trasgressore anche col flag'
);

DROP VIEW dbops.pgtap_si_via_definer;
DROP VIEW dbops.pgtap_si_via_fn;
DROP FUNCTION dbops.pgtap_si_fn_definer();
DROP FUNCTION dbops.pgtap_si_fn_invoker();

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia dietro di se' nessuna vista di prova.
ROLLBACK;
