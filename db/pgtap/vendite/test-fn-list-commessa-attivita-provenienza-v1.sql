-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2d): test 11 su config.sorgenti.apribile (area ritirata).
-- pgTAP test per Zero ERP
--
-- Test: la PROVENIENZA della riga di commessa arriva a valle
--   (changeSet 20260820-03 -> -07, richiesta BE del 2026-08-20 punto 2 e 3;
--    brief-design-note-credito-resi §40).
--
-- Elenco test (plan 22):
--   1) vendite.fn_get_sorgente_documento_ref esiste
--   2) vendite.fn_get_sorgente_documento_id NON esiste piu' (sostituita)
--   3) fn_list_commessa_attivita: una firma sola (nessun overload)
--   4) la RETURNS TABLE espone tipo_movimento
--   5) ... articolo_codice
--   6) ... articolo_descrizione
--   7) ... sorgente_documento_numero
--   8) ... gruppo_key
--   9) config.sorgenti.label_selector esiste
--  10) ⭐ INVARIANTE: ogni label_selector dichiarato nomina una colonna che
--      esiste davvero sulla target_table
--  11) ⭐ INVARIANTE: ogni sorgente con `area` (= documento sfogliabile) ha
--      anche un label_selector
--  12) il resolver risponde UNA riga anche con parametri NULL (mai zero)
--  13) il resolver risponde UNA riga anche su una sorgente inesistente
--  14) spot-check dati veri (skip-abile): un ORDINE risolve id E numero
--  15) fixture: riga SOURCELESS -> sorgente_documento_numero NULL
--  16) fixture: riga SOURCELESS -> gruppo_key = 'MAN:<commessa_id>'
--  17) fixture: la riga sourceless NON sparisce dalla lista
--  18) i sei nomi nuovi sono ammessi in ORDER BY
--  19) un nome fuori whitelist resta fail-loud (P0001)
--  20) vw_dash_competenza_mensile espone tipo_movimento
--  (security_invoker: presidiato da rls/test-rls-viste-security-invoker.sql)
--  22) vw_dash_competenza_mensile: nessuna riga mescola due tipo_movimento
--  23) filtro p_tipo_movimento NULL: nessun filtro, la riga c'e'
--  24) filtro sul movimento presente: la riga c'e'
--  25) filtro su un movimento assente: zero righe, SENZA errore
--  26) ⭐ un valore fuori vocabolario SOLLEVA (P0001), non filtra a vuoto
--  27) tolleranza a spazi e minuscole, come per p_order_by/p_order_dir
--  28) ⭐ la chiamata POSIZIONALE a 8 argomenti (la firma di prima del
--      filtro) funziona ancora: il parametro nuovo e' in coda apposta
--  --- Chiave in forma canonica (rev 2026-10-05, 20261005-26) ---
--  29) il resolver risolve la chiave canonica di una commessa COSTRUITA
--  30) la stessa chiave con zeri davanti NON si risolve (riga a NULL)
--  31) ⭐ un id fuori range NON solleva: una riga a NULL (prima 22003)
--
-- Scopo:
--  - Le colonne nuove escono davvero, e la lista non si rompe ordinando per
--    esse: la whitelist e' CHIUSA e fail-loud, quindi una colonna a catalogo
--    con ordinabile=t su un nome sconosciuto romperebbe la lista al primo
--    click, non produrrebbe una freccia inerte.
--  - ⭐ I due invarianti di catalogo (10 e 11) sono il cancello che rende
--    RUMOROSO un refuso in `label_selector`: senza, l'unico sintomo sarebbe una
--    colonna vuota a video, che nessuna suite vede e nessun errore segnala.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: i test girano come `zeroerp_app` con RLS attiva.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(30);

-- ============================================================
-- 1..3  Gli oggetti: c'e' la nuova, non c'e' piu' la vecchia
-- ============================================================

SELECT ok(
  EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
           WHERE n.nspname = 'vendite' AND p.proname = 'fn_get_sorgente_documento_ref'),
  '1. vendite.fn_get_sorgente_documento_ref esiste'
);

-- ⚠️ Non e' pignoleria: lasciarle entrambe vorrebbe dire due funzioni con lo
--   stesso corpo che risolvono la stessa sorgente polimorfa. La copia
--   sopravvissuta e' quella che al primo ritocco diverge.
SELECT ok(
  NOT EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
               WHERE n.nspname = 'vendite' AND p.proname = 'fn_get_sorgente_documento_id'),
  '2. fn_get_sorgente_documento_id non esiste piu'' (sostituita dalla ref)'
);

SELECT is(
  (SELECT count(*)::int FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite' AND p.proname = 'fn_list_commessa_attivita'),
  1,
  '3. fn_list_commessa_attivita: una firma sola (nessun overload)'
);

-- ============================================================
-- 4..8  Le cinque colonne nuove nella RETURNS TABLE
-- ============================================================
-- Si leggono dai nomi degli argomenti OUT (proargmodes 't' = TABLE), non da una
-- SELECT: cosi' l'asserzione vale anche se la commessa di prova non ha righe.

CREATE TEMP TABLE tmp_out_lcp AS
SELECT unnest(p.proargnames) AS argname
  FROM pg_proc p
  JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname = 'vendite' AND p.proname = 'fn_list_commessa_attivita';

SELECT ok((SELECT count(*) FROM tmp_out_lcp WHERE argname = 'tipo_movimento') = 1,
          '4. RETURNS TABLE espone tipo_movimento');
SELECT ok((SELECT count(*) FROM tmp_out_lcp WHERE argname = 'articolo_codice') = 1,
          '5. RETURNS TABLE espone articolo_codice');
SELECT ok((SELECT count(*) FROM tmp_out_lcp WHERE argname = 'articolo_descrizione') = 1,
          '6. RETURNS TABLE espone articolo_descrizione');
SELECT ok((SELECT count(*) FROM tmp_out_lcp WHERE argname = 'sorgente_documento_numero') = 1,
          '7. RETURNS TABLE espone sorgente_documento_numero');
SELECT ok((SELECT count(*) FROM tmp_out_lcp WHERE argname = 'gruppo_key') = 1,
          '8. RETURNS TABLE espone gruppo_key');

-- ============================================================
-- 9..11  Il catalogo: la colonna, e i due invarianti che la presidiano
-- ============================================================

SELECT has_column('config', 'sorgenti', 'label_selector',
                  '9. config.sorgenti.label_selector esiste');

-- ⭐ IL CANCELLO. Un `label_selector` che nomina una colonna inesistente non da'
--   errore: il resolver cattura undefined_column e risponde NULL. A video si
--   vedrebbe una cella vuota, cioe' niente. Qui diventa un rosso.
SELECT is(
  (SELECT count(*)::int
     FROM config.sorgenti s
    WHERE s.label_selector IS NOT NULL
      AND s.target_table IS NOT NULL
      AND NOT EXISTS (
            SELECT 1 FROM pg_attribute a
             WHERE a.attrelid = s.target_table
               AND a.attname  = s.label_selector
               AND a.attnum > 0 AND NOT a.attisdropped)),
  0,
  '10. ogni label_selector nomina una colonna che esiste sulla target_table'
);

-- ⭐ COERENZA. `apribile` = la sorgente E' un documento con una sua pagina
--   (rev 2026-10-20, 2d: era `area` valorizzata, ritirata), quindi ha un numero
--   che l'operatore legge. Una sorgente nuova sfogliabile e
--   senza label_selector darebbe una colonna «Origine» vuota per sempre, e
--   sarebbe l'unico sintomo.
SELECT is(
  (SELECT count(*)::int FROM config.sorgenti s
    WHERE s.attivo IS TRUE AND s.apribile AND s.label_selector IS NULL),
  0,
  '11. ogni sorgente apribile dichiara un label_selector'
);

-- ============================================================
-- 12..13  Il resolver risponde SEMPRE una riga
-- ============================================================
-- ⚠️ Non e' un dettaglio: una RETURNS TABLE che a volte torna zero righe si usa
--   bene con LEFT JOIN LATERAL e CANCELLA la riga chiamante il giorno in cui
--   qualcuno scrive CROSS JOIN LATERAL. Una riga sempre presente rende
--   quell'errore impossibile invece che improbabile.

SELECT is(
  (SELECT count(*)::int FROM vendite.fn_get_sorgente_documento_ref(NULL, NULL)),
  1,
  '12. il resolver risponde una riga anche con parametri NULL'
);

SELECT is(
  (SELECT count(*)::int FROM vendite.fn_get_sorgente_documento_ref(999999999, 'non-un-uuid')),
  1,
  '13. il resolver risponde una riga anche su una sorgente inesistente'
);

-- ============================================================
-- 14  Spot-check sui dati veri (skip-abile)
-- ============================================================
-- ⚠️ Dipende dai dati, quindi si salta invece di fallire su un DB ricostruito
--   da zero — dove gli ordini non ci sono. Quando c'e', verifica la cosa che
--   nessuna asserzione di forma puo' verificare: che la traduzione FUNZIONI.

CREATE TEMP TABLE tmp_ord_lcp AS
SELECT o.uid, o.numero
  FROM vendite.ordini o
 WHERE o.numero IS NOT NULL
 ORDER BY o.id
 LIMIT 1;

SELECT CASE WHEN (SELECT count(*) FROM tmp_ord_lcp) = 0
  THEN skip('14. nessun ordine con numero: spot-check saltato', 1)
  ELSE is(
    (SELECT r.documento_numero
       FROM tmp_ord_lcp t
       CROSS JOIN LATERAL vendite.fn_get_sorgente_documento_ref(
           (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA'),
           t.uid::text) r),
    (SELECT t.numero::text FROM tmp_ord_lcp t),
    '14. su un ordine vero il resolver restituisce il numero leggibile'
  )
END;

-- ============================================================
-- Fixture: una commessa con una riga SOURCELESS
-- ============================================================
-- ⚠️ La riga sourceless e' il caso che ha cambiato il disegno: RETTIFICA e
--   ONERE non hanno documento a monte per progetto (misurato il 2026-08-20:
--   9 righe su 98, il 100% delle righe di nota di credito). Qui si usa una
--   RETTIFICA perche' l'ONERE pretenderebbe una causale, e il comportamento
--   sotto esame — «niente sorgente» — e' identico. ⛔ Non una NORMALE: senza
--   sorgente la rifiuta il vincolo chk_commesse_attivita_senza_sorgente_onere_rettifica
--   (20261012-27), e il caso non esiste piu' nel modello.

CREATE TEMP TABLE tmp_refs_lcp AS
SELECT
  (SELECT ba.id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS billing_account_id,
  (SELECT ba.utility_id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS utility_id,
  (SELECT ba.istanza_utility_id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS istanza_utility_id,
  -- ⚠️ Un articolo con codice E descrizione: sono le due colonne sotto esame,
  --   e sceglierlo senza guardarle renderebbe il test 15 verde per caso.
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.codice IS NOT NULL AND a.descrizione IS NOT NULL
    ORDER BY a.data_insert DESC NULLS LAST, a.id LIMIT 1) AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  -- Il tipo doc fiscale non e' opzionale da quando esiste
  -- trg_commesse_attivita_a10_guard_tipo_doc_emittibile: senza, la fixture
  -- muore prima di eseguire una sola asserzione.
  (SELECT t.id FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id;

CREATE TEMP TABLE tmp_commessa_lcp AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT billing_account_id FROM tmp_refs_lcp),
  p_utility_id             => (SELECT utility_id FROM tmp_refs_lcp),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_competenza_dal         => DATE '2026-07-01',
  p_competenza_al          => DATE '2026-08-31',
  p_meta                   => jsonb_build_object('test_scope', 'pgtap_lcp_provenienza'),
  p_force_new              => true
) AS commessa_id;

CREATE TEMP TABLE tmp_att_lcp AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id         => (SELECT commessa_id FROM tmp_commessa_lcp),
  p_segment_key         => ('SEG-LCP-1-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar,
  p_articolo_id         => (SELECT articolo_id FROM tmp_refs_lcp),
  p_istanza_utility_id  => (SELECT istanza_utility_id FROM tmp_refs_lcp),
  p_data_attivita       => DATE '2026-07-15',
  p_uom_id              => (SELECT uom_id FROM tmp_refs_lcp),
  p_quantita            => 1.000000,
  p_competenza_mese     => DATE '2026-07-01',
  p_competenza_dal      => DATE '2026-07-01',
  p_competenza_al       => DATE '2026-07-31',
  p_prezzo_snapshot     => 10.0000000000,
  -- ⚠️ Gli otto qui sotto NON hanno un default nella firma: vanno passati
  --   anche a NULL, o la chiamata non risolve affatto («la funzione non
  --   esiste», che e' il modo in cui PostgreSQL dice «nessun overload combacia»).
  p_prezzo_base_snapshot          => NULL,
  p_origine_prezzo                => NULL,
  p_tipo_variazione_applicata     => NULL,
  p_valore_variazione_applicata   => NULL,
  p_promo_id                      => NULL,
  p_contratto_id                  => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot     => NULL,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_lcp),
  p_stato_approvazione  => 'APPROVATA',
  p_stato_emissione     => 'NON_EMESSA',
  -- ⭐ Sorgente ASSENTE: e' il soggetto del test.
  p_sorgente_tipo_id    => NULL,
  p_sorgente_uid        => NULL,
  p_tipo_movimento      => 'RETTIFICA',
  p_meta                => jsonb_build_object('case', 'LCP_SOURCELESS')
) r;

-- ⚠️ Il verbo e' stato chiamato in un'istruzione SEPARATA dalle asserzioni: la
--   snapshot di statement legge PRIMA delle scritture, e un'asserzione nello
--   stesso statement accuserebbe la funzione di un difetto del test.
CREATE TEMP TABLE tmp_riga_lcp AS
SELECT *
  FROM vendite.fn_list_commessa_attivita(
         p_commessa_id => (SELECT commessa_id FROM tmp_commessa_lcp))
 WHERE id = (SELECT commessa_attivita_id FROM tmp_att_lcp);

-- ============================================================
-- 15..17  La riga sourceless: niente numero, ma un gruppo, e non sparisce
-- ============================================================

SELECT ok(
  (SELECT sorgente_documento_numero IS NULL FROM tmp_riga_lcp),
  '15. riga sourceless: sorgente_documento_numero e'' NULL'
);

SELECT is(
  (SELECT gruppo_key FROM tmp_riga_lcp),
  'MAN:' || (SELECT commessa_id FROM tmp_commessa_lcp)::text,
  '16. riga sourceless: gruppo_key = MAN:<commessa_id>, non un documento'
);

-- ⚠️ La cosa che i LATERAL potevano rompere: una funzione che torna zero righe,
--   o una join di decode senza LEFT, farebbero SPARIRE la riga dalla lista —
--   dati mancanti, non un errore.
SELECT is(
  (SELECT count(*)::int FROM tmp_riga_lcp),
  1,
  '17. la riga sourceless resta nella lista (nessun LATERAL la cancella)'
);

-- ============================================================
-- 18..19  L'ordinamento: i sei nomi nuovi, e il fail-loud che resta
-- ============================================================
-- ⚠️ E' la trappola del giro: la whitelist qui dentro e' CHIUSA e fail-loud, e
--   una riga di ui.lista_colonna con `ordinabile = t` su un nome che non
--   conosce NON produce una freccia inerte — rompe la lista al primo click.

SELECT lives_ok($$
  DO $o$
  DECLARE c text; n int; v_commessa bigint;
  BEGIN
    SELECT commessa_id INTO v_commessa FROM tmp_commessa_lcp;
    FOREACH c IN ARRAY ARRAY['tipo_movimento','articolo_codice','articolo_descrizione',
                             'sorgente_codice','sorgente_documento_numero','gruppo_key'] LOOP
      -- ⭐ POSIZIONALE, e di proposito: sono gli OTTO argomenti della firma
      --   precedente al filtro `p_tipo_movimento`. Il nono e' stato appeso IN
      --   CODA con un DEFAULT apposta perche' chiamate come questa continuino a
      --   funzionare senza toccare la catena di chi chiama; se un domani
      --   qualcuno spostasse un parametro in mezzo, questa riga diventerebbe
      --   rossa — ed e' il suo secondo mestiere.
      EXECUTE format(
        'SELECT count(*) FROM vendite.fn_list_commessa_attivita(%s, NULL, NULL, NULL, 1000, 0, %L, %L)',
        v_commessa, c, 'desc') INTO n;
    END LOOP;
  END $o$;
$$, '18. i sei nomi nuovi sono ammessi dalla whitelist di ordinamento');

-- SQLSTATE esplicito: senza, throws_ok accetterebbe QUALUNQUE errore, compreso
-- il crash della funzione. P0001 = errore di dominio sollevato da
-- script.fn_log_and_raise_error.
SELECT throws_ok($$
  SELECT count(*) FROM vendite.fn_list_commessa_attivita(
      (SELECT commessa_id FROM tmp_commessa_lcp), NULL, NULL, NULL, 1000, 0,
      'colonna_inventata', 'asc')
$$, 'P0001', NULL,
   '19. un order_by fuori whitelist resta fail-loud (P0001), non ripiega');

-- ============================================================
-- 20..22  La vista mensile: la dimensione c'e', e lo scope regge
-- ============================================================

SELECT has_column('vendite', 'vw_dash_competenza_mensile', 'tipo_movimento',
                  '20. vw_dash_competenza_mensile espone tipo_movimento');

-- ⛔ QUI `security_invoker` NON SI PRESIDIA PIU' (rev 2026-09-07), e non e' una
--   rinuncia: lo fa gia' db/pgtap/rls/test-rls-viste-security-invoker.sql, su
--   TUTTE le viste che toccano dati in RLS — anche attraverso altre viste — e
--   leggendo la PROPRIETA' invece della parola. Nessun elenco di nomi.
--   ⚠️ Il doppione locale non aggiungeva copertura, e ne ha tolta: era scritto
--   come confronto di GRAFIA (`security_invoker=on`) ed e' diventato ROSSO su
--   una vista perfettamente sana, riscritta con `= true` — che significa la
--   stessa identica cosa. Due falsi allarmi il 2026-09-07, e una bisezione fra
--   due cantieri per scoprire che non era rotto niente.
--   ⭐ Una seconda sede diverge sempre; questa e' divergiata verso il FALSO
--   ALLARME, che e' il verso che fa spegnere i presidi.


-- ⭐ La GRANA, non la sola presenza della colonna: la mensile deve avere
--   esattamente una riga per ogni combinazione di DIMENSIONI del dettaglio.
--   Seed-agnostica — 0 = 0 su un database vuoto — e diventerebbe rossa se
--   qualcuno ri-aggregasse a valle «per non rompere il backend», che e'
--   proprio la scorciatoia da cui questa colonna nasce.
-- ⚠️ AGGIORNATO il 2026-08-26 (D-2, brief-db-residui-competenza-dimensione-e-chiave):
--   `motivo_non_fatturata` e' entrata fra le dimensioni, e questa asserzione
--   e' un presidio di GRANA — cambiando la grana va PORTATA sulla regola nuova,
--   mai spenta. E' lo stesso meccanismo che rese rossi i test 7 e 8 di
--   test-ordini-guard-transizione-v1 quando L7b ALLARGO' un guard: un
--   presidio cade allo stesso modo nelle due direzioni, e i consumatori si
--   cercano dal CODICE, non dalla direzione del cambio.
SELECT is(
  (SELECT count(*)::int FROM vendite.vw_dash_competenza_mensile),
  (SELECT count(*)::int FROM (
      SELECT 1 FROM vendite.vw_dash_competenza_attivita
       GROUP BY competenza_mese, stadio, stato_fattura_codice_interno,
                tipo_movimento, motivo_non_fatturata
   ) x),
  '22. la mensile ha una riga per (mese, stadio, stato, tipo_movimento, motivo_non_fatturata)'
);

-- ============================================================
-- 23..27  Il quarto filtro: p_tipo_movimento
-- ============================================================
-- La fixture ha UNA riga, `RETTIFICA`: basta e avanza, perche' le cinque
-- asserzioni misurano il comportamento del FILTRO, non la popolazione.

SELECT is(
  (SELECT count(*)::int FROM vendite.fn_list_commessa_attivita(
      p_commessa_id => (SELECT commessa_id FROM tmp_commessa_lcp))),
  1,
  '23. p_tipo_movimento assente: nessun filtro, la riga c''e'''
);

SELECT is(
  (SELECT count(*)::int FROM vendite.fn_list_commessa_attivita(
      p_commessa_id    => (SELECT commessa_id FROM tmp_commessa_lcp),
      p_tipo_movimento => 'RETTIFICA')),
  1,
  '24. filtro sul movimento presente: la riga c''e'''
);

-- ⚠️ Zero righe QUI e' l'esito giusto — ed e' proprio per questo che il test 26
--   esiste: senza, «zero righe» sarebbe la risposta sia alla domanda legittima
--   sia al valore sbagliato, e le due diventerebbero indistinguibili.
SELECT is(
  (SELECT count(*)::int FROM vendite.fn_list_commessa_attivita(
      p_commessa_id    => (SELECT commessa_id FROM tmp_commessa_lcp),
      p_tipo_movimento => 'NORMALE')),
  0,
  '25. filtro su un movimento assente: zero righe, senza errore'
);

-- ⭐ L'asserzione per cui il filtro e' stato scritto cosi'. Un valore fuori
--   vocabolario NON deve restituire una lista vuota: si leggerebbe come «non
--   c'e' niente», cioe' il difetto travestito da dato. SQLSTATE esplicito,
--   altrimenti throws_ok accetterebbe anche il crash della funzione.
SELECT throws_ok($$
  SELECT count(*) FROM vendite.fn_list_commessa_attivita(
      p_commessa_id    => (SELECT commessa_id FROM tmp_commessa_lcp),
      p_tipo_movimento => 'MOVIMENTO_INVENTATO')
$$, 'P0001', NULL,
   '26. un tipo_movimento fuori vocabolario SOLLEVA, non filtra a vuoto');

-- Stessa tolleranza gia' applicata a p_order_by e p_order_dir: spazi e
-- minuscole non sono un valore sbagliato, sono lo stesso valore scritto male.
-- Il vocabolario resta chiuso — lo dimostra il test 26.
SELECT is(
  (SELECT count(*)::int FROM vendite.fn_list_commessa_attivita(
      p_commessa_id    => (SELECT commessa_id FROM tmp_commessa_lcp),
      p_tipo_movimento => '  rettifica  ')),
  1,
  '27. p_tipo_movimento tollera spazi e minuscole'
);

-- ⭐ 28. La ragione per cui `p_tipo_movimento` e' il NONO argomento e non il
--   quinto. Questa e' esattamente la firma di prima — otto argomenti, tutti
--   posizionali — e deve continuare a risolvere senza toccare nessun chiamante.
--   Una firma piu' ordinata non vale la ricostruzione della catena di chi
--   chiama; se un domani qualcuno infilasse un parametro in mezzo, questa riga
--   diventerebbe rossa, ed e' il punto.
SELECT lives_ok($$
  SELECT count(*) FROM vendite.fn_list_commessa_attivita(
      (SELECT commessa_id FROM tmp_commessa_lcp), NULL, NULL, NULL, 1000, 0, NULL, 'asc')
$$, '28. la chiamata posizionale a 8 argomenti (firma pre-filtro) regge ancora');


-- ============================================================
-- 29-31) La chiave si riconosce in FORMA CANONICA (20261005-26)
--   Il resolver usa ora i building block script.fn_sorgente_chiave_uuid /
--   _id, la stessa regola di chi salva la chiave (guard, rubinetto) e di chi
--   cerca lo stato. Il 29 tiene il 30 onesto: la stessa commessa, scritta
--   bene, si risolve. Il 31 era un 22003 dentro una lista.
-- ============================================================
SELECT is(
  (SELECT documento_id FROM vendite.fn_get_sorgente_documento_ref(
      (SELECT id FROM config.sorgenti WHERE codice_interno = 'COMMESSA'),
      (SELECT commessa_id FROM tmp_commessa_lcp)::text)),
  (SELECT commessa_id FROM tmp_commessa_lcp)::bigint,
  '29. la chiave canonica di una commessa costruita si risolve'
);

SELECT is(
  (SELECT documento_id FROM vendite.fn_get_sorgente_documento_ref(
      (SELECT id FROM config.sorgenti WHERE codice_interno = 'COMMESSA'),
      '0' || (SELECT commessa_id FROM tmp_commessa_lcp)::text)),
  NULL::bigint,
  '30. la stessa chiave con zeri davanti non si risolve (forma non canonica)'
);

SELECT results_eq(
  $$SELECT documento_id, documento_numero FROM vendite.fn_get_sorgente_documento_ref(
      (SELECT id FROM config.sorgenti WHERE codice_interno = 'COMMESSA'),
      '99999999999999999999')$$,
  $$VALUES (NULL::bigint, NULL::text)$$,
  '31. un id fuori range non solleva: una riga a NULL'
);

SELECT * FROM finish();

ROLLBACK;
