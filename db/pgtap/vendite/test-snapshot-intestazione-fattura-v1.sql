-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- Test: vendite.fn_snapshot_intestazione_fattura (changeSet 20260731-06)
--       + guard di congelamento sulla TESTATA (changeSet 20260731-05)
-- Piano: piano-db-satelliti-fattura.md, cantiere INTESTAZIONE passo I.6
-- Brief: brief-db-snapshot-intestazione-fattura.md §3.1-§3.4, §10.3
-- ------------------------------------------------------------
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): le fatture nascono in
--   bozza e la «congelata» si porta avanti con dbops.fn_pgtap_porta_a_stato
--   (prima nasceva gia' DEFINITIVA). Per uscire dalla bozza le si scrivono a
--   mano indirizzo FATT e intestazione — NON con la funzione sotto test — e in
--   EMESSA (sotto soglia) si tolgono di nuovo: arriva in DEFINITIVA con
--   l'intestazione a NULL come prima, e l'11 prova ancora la prima scrittura.
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): azienda, cliente e
--   le due fatture li costruiscono i builder (fn_pgtap_crea_emittente_operatore,
--   fn_pgtap_crea_fattura): non si pesca piu' «il primo BA con la sede sul
--   soggetto», che su un database ricostruito non c'e'. La «congelata» arriva
--   in DEFINITIVA gia' spogliata dal builder; il commento sulla fixture dice
--   perche' l'uso di fn_snapshot_intestazione_fattura lungo la strada non
--   tocca cio' che il file prova. Il 2 conta righe vere.
-- Indice test (1..12):
--   1) Cablaggio: guard di congelamento BEFORE UPDATE OF le due colonne
--   2) Fixture: emittente con sede sul SOGGETTO + due fatture (DRAFT e DEFINITIVA nuda)
--   3) Prima esecuzione: scritta = true
--   4) Shape emittente: le chiavi identitarie ci sono
--   5) Shape cliente: identita' + BA di TESTATA (D-P), non il conto del figlio
--   6) jsonb_strip_nulls: nessuna chiave valorizzata a null
--   7) Nessun padding: i character a larghezza fissa arrivano ripuliti
--   8) ANTI-TEST-VACUO: il ruolo emittente non ha SEDELEG proprio
--   9) Catena della sede: risolta dal layer SOGGETTO, shape canonico
--  10) Idempotenza: seconda esecuzione scritta = false, colonne invariate
--  11) Guard di congelamento: oltre soglia l'intestazione non si tocca
--  12) ...ed e' mirato: sulla stessa fattura un'altra colonna resta scrivibile
-- ------------------------------------------------------------
-- PERCHE' QUESTO FILE ESISTE, E PERCHE' ARRIVA DOPO. Le due colonne di
-- intestazione erano applicate da I.1-I.3 e usate da tre consumatori — il
-- contesto di stampa del BE (Fase 2 del loro piano), il guard di uscita dalla
-- bozza I.4, e il wrapper di lotto — senza che nessun test ne descrivesse la
-- FORMA. Il wrapper era coperto, la funzione sorella no: e' esattamente la
-- classe di buco che questo cantiere esiste per chiudere (una cosa che sembra
-- coperta perche' qualcosa vicino a lei lo e').
--
-- L'8 E IL 9 SONO UNA COPPIA, E VANNO LETTI INSIEME. Il 9 da solo non
-- proverebbe nulla: una sede valorizzata potrebbe venire dal layer RUOLO, che
-- e' il caso banale. E' l'8 a dire che quel layer e' VUOTO, e quindi che
-- l'unica strada percorribile era il fallback sul SOGGETTO. Misurato sul DB il
-- 2026-08-01: 42 emittenti su 42 hanno la sede sul soggetto, ZERO sul ruolo —
-- il che conferma il rilievo §10.3 del brief su tutta la popolazione, non su un
-- campione. E' anche la ragione per cui questo test non e' condizionale: la
-- proprieta' e' strutturale, e dal 2026-10-24 l'azienda la COSTRUISCE il
-- builder; il test 2 fallisce rumorosamente se un giorno smettesse di averla.
--
-- PERCHE' IL 7 CONTROLLA GLI SPAZI. `province.sigla`, `stati.codice_iso2` e
-- `dati_societari.destinatario_fe` sono `character(n)`: PostgreSQL li riempie a
-- spazi, e un jsonb non ha modo di dire che quel riempimento non e' un dato.
-- E' gia' costato un `"prov": "AV        "` congelato dentro un documento
-- fiscale. Il test non guarda una colonna in particolare: guarda che NESSUN
-- valore testuale dello snapshot sia diverso dal proprio btrim, cosi' copre
-- anche i `character` che nessuno ha ancora aggiunto.
--
-- PERCHE' IL 6 NON E' PEDANTERIA. Lo shape e' dichiarato non contrattuale
-- (§10.2) finche' il builder XML non esiste, ma UNA promessa la fa: le chiavi
-- assenti NON compaiono, invece di comparire a `null`. Il guard I.4 verifica
-- l'intestazione con `jsonb_typeof` proprio perche' si fida di questo; e il
-- giorno in cui uno `jsonb_strip_nulls` cadesse per distrazione, la differenza
-- fra «assente» e «presente ma vuoto» smetterebbe di essere leggibile.
--
-- Idempotente: BEGIN ... ROLLBACK.
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
-- ⛔ L'AZIENDA SI COSTRUISCE (rev 2026-10-24, Q-4), e il contesto e' quello del
--   SUO operatore: prima si apriva sul primo operatore del database e si
--   pescava il primo BA con un emittente risolvibile, che su un database
--   ricostruito (lo scratch, la CI) non c'e'.
CREATE TEMP TABLE tmp_mondo_int AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM tmp_mondo_int)); END $ctx$;

SELECT plan(12);

-- ============================================================
-- 1) Cablaggio del guard di congelamento sulla testata.
--    tgtype = 19 -> ROW(1) + BEFORE(2) + UPDATE(16).
--    tgattr deve contenere ESATTAMENTE le due colonne di intestazione:
--    confronto insiemistico, non posizionale, perche' l'ordine dipende da
--    come e' stata scritta la CREATE TRIGGER e non e' cio' che ci interessa.
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM pg_trigger t
     JOIN pg_class c     ON c.oid = t.tgrelid
     JOIN pg_namespace n ON n.oid = c.relnamespace
     JOIN pg_proc p      ON p.oid = t.tgfoid
    WHERE n.nspname = 'vendite'
      AND c.relname = 'fatture'
      AND p.proname = 'trgfn_fattura_satellite_guard_congelamento'
      AND NOT t.tgisinternal
      AND t.tgtype = 19
      AND (SELECT array_agg(x ORDER BY x)
             FROM unnest(string_to_array(t.tgattr::text, ' ')::int[]) x)
        = (SELECT array_agg(a.attnum::int ORDER BY a.attnum)
             FROM pg_attribute a
            WHERE a.attrelid = 'vendite.fatture'::regclass
              AND a.attname IN ('emittente_snapshot', 'cliente_snapshot'))),
  1,
  '1) guard di congelamento montato BEFORE UPDATE OF (emittente_snapshot, cliente_snapshot)'
);

-- ============================================================
-- Riferimenti e fixture.
-- ⚠️ Serve un emittente la cui sede legale stia sul layer SOGGETTO, che e' il
--    caso reale (§10.3) e l'unico che esercita la catena. Prima lo si
--    SELEZIONAVA fra i BA del database; ora l'azienda e' costruita, e il 2
--    verifica che la proprieta' ce l'abbia (e l'8 che il layer RUOLO e' vuoto).
-- ============================================================
-- Le due fatture dal builder, sullo stesso cliente. La «congelata» arriva in
-- DEFINITIVA SENZA indirizzi ne' intestazione (p_spoglia_*): l'11 trova
-- l'intestazione a NULL, come quando la fattura nasceva congelata.
-- ⚠️ fn_snapshot_intestazione_fattura e' la funzione sotto test, e il builder
--    la chiama per la «congelata»: e' solo la strada d'uscita dalla bozza
--    (trgfn_fatture_guard_uscita_draft vuole l'intestazione), poi in EMESSA la
--    spoglia. Lo stato finale non dipende dal suo risultato, e l'11-12
--    guardano il guard di congelamento, non lo snapshot. La funzione sotto
--    test si esercita solo sulla «draft», che il builder lascia vergine.
CREATE TEMP TABLE tmp_f_draft_int AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('snapshot intestazione draft');

CREATE TEMP TABLE tmp_f_cong_int AS
SELECT * FROM dbops.fn_pgtap_crea_fattura(
    'snapshot intestazione congelata', 'DEFINITIVA',
    (SELECT billing_account_id FROM tmp_f_draft_int), true, true);

CREATE TEMP TABLE tmp_fatture_int AS
SELECT fattura_id AS id, 'draft'::text AS caso FROM tmp_f_draft_int
UNION ALL SELECT fattura_id, 'congelata' FROM tmp_f_cong_int;

CREATE TEMP TABLE tmp_refs_int AS
SELECT d.billing_account_id,
       d.emittente_soggetto_ruolo_id,
       d.cliente_soggetto_ruolo_id
  FROM tmp_f_draft_int d;

-- ⚠️ Il 2 conta righe VERE: la sede dell'emittente costruito sul layer
--   SOGGETTO, la «draft» vergine in DRAFT, la «congelata» in DEFINITIVA con
--   l'intestazione a NULL.
SELECT ok(
  (SELECT count(*)
     FROM tmp_refs_int r
     JOIN anagrafiche.soggetti_ruoli sr        ON sr.id = r.emittente_soggetto_ruolo_id
     JOIN anagrafiche.indirizzi_soggetti isg   ON isg.soggetto_id = sr.soggetto_id
     JOIN config.tipi_indirizzi ti             ON ti.id = isg.tipo_indirizzo_id
    WHERE ti.codice_interno = 'SEDELEG') >= 1
  AND (SELECT count(*)::int
         FROM tmp_fatture_int t
         JOIN vendite.fatture f          ON f.id = t.id
         JOIN config.stati_doc_fiscale s ON s.id = f.stato_doc_fiscale_id
        WHERE s.codice_interno = CASE t.caso WHEN 'draft' THEN 'DRAFT' ELSE 'DEFINITIVA' END
          AND f.emittente_snapshot IS NULL
          AND f.cliente_snapshot IS NULL) = 2,
  '2) fixture: emittente con sede sul layer SOGGETTO costruito, due fatture create'
);

-- ============================================================
-- 3) Prima esecuzione: c'e' lavoro da fare, quindi scrive.
-- ============================================================
CREATE TEMP TABLE tmp_run1_int AS
SELECT scritta
  FROM vendite.fn_snapshot_intestazione_fattura(
         (SELECT id FROM tmp_fatture_int WHERE caso = 'draft'));

SELECT ok(
  (SELECT scritta FROM tmp_run1_int),
  '3) prima esecuzione su fattura vergine: scritta = true'
);

-- Congelo lo stato scritto: serve al 10 per dire «invariate» senza ri-leggere
-- una cosa che nel frattempo potrebbe essere cambiata.
CREATE TEMP TABLE tmp_snap_int AS
SELECT f.id, f.emittente_snapshot, f.cliente_snapshot
  FROM vendite.fatture f
 WHERE f.id = (SELECT id FROM tmp_fatture_int WHERE caso = 'draft');

-- ============================================================
-- 4-5) Shape delle due parti.
--      Il 5 e' anche il presidio di D-P: il billing account congelato e'
--      quello di TESTATA, che in gerarchia e' il PADRE. Chi leggera' quello
--      snapshot fra sei mesi deve trovare il conto giusto, non quello del
--      figlio che ha consumato.
-- ============================================================
SELECT ok(
  (SELECT emittente_snapshot ?& ARRAY['soggetto_ruolo_id', 'soggetto_id', 'denominazione']
     FROM tmp_snap_int),
  '4) emittente_snapshot porta le chiavi identitarie (ruolo, soggetto, denominazione)'
);

SELECT ok(
  (SELECT s.cliente_snapshot ?& ARRAY['soggetto_ruolo_id', 'denominazione',
                                      'billing_account_id', 'ba_codice']
      AND (s.cliente_snapshot ->> 'billing_account_id')::bigint
          = (SELECT r.billing_account_id FROM tmp_refs_int r)
      AND (s.cliente_snapshot ->> 'soggetto_ruolo_id')::bigint
          = (SELECT r.cliente_soggetto_ruolo_id FROM tmp_refs_int r)
     FROM tmp_snap_int s),
  '5) cliente_snapshot: identita'' + billing account di TESTATA (D-P)'
);

-- ============================================================
-- 6) jsonb_strip_nulls: le chiavi assenti non compaiono, non compaiono
--    valorizzate a null. Si guardano anche i due oggetti annidati.
-- ============================================================
SELECT ok(
  (SELECT NOT EXISTS (
     SELECT 1
       FROM tmp_snap_int s
       CROSS JOIN LATERAL (VALUES (s.emittente_snapshot),
                                  (s.cliente_snapshot),
                                  (s.emittente_snapshot -> 'sede'),
                                  (s.emittente_snapshot -> 'rea'),
                                  (s.emittente_snapshot -> 'forma_giuridica')) AS o(obj)
       CROSS JOIN LATERAL jsonb_each(COALESCE(o.obj, '{}'::jsonb)) AS kv(k, v)
      WHERE jsonb_typeof(kv.v) = 'null')),
  '6) jsonb_strip_nulls applicato: nessuna chiave valorizzata a null'
);

-- ============================================================
-- 7) Nessun padding da character(n). Non si guarda una colonna: si guarda
--    che nessun valore testuale sia diverso dal proprio btrim.
-- ============================================================
SELECT ok(
  (SELECT NOT EXISTS (
     SELECT 1
       FROM tmp_snap_int s
       CROSS JOIN LATERAL (VALUES (s.emittente_snapshot),
                                  (s.cliente_snapshot),
                                  (s.emittente_snapshot -> 'sede'),
                                  (s.emittente_snapshot -> 'rea'),
                                  (s.emittente_snapshot -> 'forma_giuridica')) AS o(obj)
       CROSS JOIN LATERAL jsonb_each(COALESCE(o.obj, '{}'::jsonb)) AS kv(k, v)
      WHERE jsonb_typeof(kv.v) = 'string'
        AND (kv.v #>> '{}') IS DISTINCT FROM btrim(kv.v #>> '{}'))),
  '7) nessun valore testuale con spazi di riempimento (trappola character(n))'
);

-- ============================================================
-- 8) ANTI-TEST-VACUO DEL 9. Se il ruolo emittente avesse una sede propria, il
--    9 passerebbe senza aver mai esercitato il fallback sul layer SOGGETTO —
--    cioe' senza provare la cosa per cui esiste.
-- ============================================================
SELECT ok(
  (SELECT NOT EXISTS (
     SELECT 1
       FROM anagrafiche.indirizzi i
       JOIN config.tipi_indirizzi ti ON ti.id = i.tipo_indirizzo_id
      WHERE i.soggetto_ruolo_id = (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_int)
        AND ti.codice_interno = 'SEDELEG')),
  '8) il ruolo emittente non ha SEDELEG proprio: il layer RUOLO e'' vuoto (§10.3)'
);

-- ============================================================
-- 9) La sede c'e' comunque, e ha lo SHAPE CANONICO degli indirizzi — cioe'
--    e' passata dalla catena condivisa e non da una composizione a mano
--    (D-5: lo snapshot non si compone mai a mano).
-- ============================================================
SELECT ok(
  (SELECT jsonb_typeof(s.emittente_snapshot -> 'sede') = 'object'
      AND s.emittente_snapshot -> 'sede' <> '{}'::jsonb
      AND NOT EXISTS (
            SELECT 1 FROM jsonb_object_keys(s.emittente_snapshot -> 'sede') k
             WHERE k NOT IN ('intestazione', 'via', 'cap', 'citta',
                             'prov', 'stato', 'display'))
     FROM tmp_snap_int s),
  '9) sede risolta dal layer SOGGETTO, con lo shape canonico e nessuna chiave estranea'
);

-- ============================================================
-- 10) Idempotenza. Non basta che il secondo giro dica «niente da fare»: le
--     colonne devono essere anche RIMASTE quelle. Il contatore e le colonne
--     possono mentire in modi diversi.
-- ============================================================
SELECT ok(
  (SELECT NOT scritta
     FROM vendite.fn_snapshot_intestazione_fattura(
            (SELECT id FROM tmp_fatture_int WHERE caso = 'draft')))
  AND (SELECT f.emittente_snapshot IS NOT DISTINCT FROM s.emittente_snapshot
          AND f.cliente_snapshot   IS NOT DISTINCT FROM s.cliente_snapshot
         FROM vendite.fatture f JOIN tmp_snap_int s ON s.id = f.id),
  '10) seconda esecuzione: scritta = false e le due colonne sono invariate'
);

-- ============================================================
-- 11) Oltre la soglia l'intestazione e' uno snapshot fiscale: non si tocca.
--     E' la simmetria chiesta dal brief §3.4 — un satellite blindato e una
--     testata aperta sarebbe una porta di servizio.
-- ============================================================
SELECT throws_ok(
  format($$ UPDATE vendite.fatture
               SET emittente_snapshot = '{"denominazione":"Manomessa"}'::jsonb
             WHERE id = %s $$,
         (SELECT id FROM tmp_fatture_int WHERE caso = 'congelata')),
  'P0001', NULL,
  '11) fattura in DEFINITIVA: UPDATE dell''intestazione rifiutato'
);

-- ============================================================
-- 12) Il guard e' montato con UPDATE OF: presidia le due colonne, non
--     congela l'intera riga. Senza questo test, un montaggio senza OF
--     passerebbe l'11 e bloccherebbe in silenzio ogni altra scrittura sulla
--     testata di una fattura emessa — contabilizzazione compresa.
-- ============================================================
SELECT lives_ok(
  format($$ UPDATE vendite.fatture SET data_contabilizzazione = script.fn_data_operativa()
             WHERE id = %s $$,
         (SELECT id FROM tmp_fatture_int WHERE caso = 'congelata')),
  '12) sulla stessa fattura DEFINITIVA un''altra colonna resta scrivibile'
);

SELECT * FROM finish();
ROLLBACK;
