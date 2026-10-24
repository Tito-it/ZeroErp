-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2d): l'ambito dei tipi d'indirizzo ammessi e' il codice della sorgente (FATTURE -> FATTURA).
-- pgTAP test per Zero ERP
-- Test: vendite.fn_snapshot_indirizzi_fattura (Fase 2.1)
--       + catena script.fn_resolve_indirizzo_documento (2.0-b)
--       + seed del task snapshot_indirizzi_lotto (2.3)
-- Piano: piano-db-satelliti-fattura.md Fase 2.4
-- ------------------------------------------------------------
-- Indice test (1..16):
--  1) Riferimenti minimi presenti (registro, BA, emittente, stato DRAFT)
--  2) Fixture utilizzabile: gli slot indirizzo che il test occupa sono liberi
--  3) Fattura di test creata in DRAFT
--  4) Nessun FATT risolvibile -> E_INDIRIZZO_FATTURA_MANCANTE
--  5) FATT generico presente -> inserted_rows = 1
--  6) Fallback generico: lo snapshot porta l'indirizzo senza istanza
--  7) Shape canonico: le chiavi previste ci sono
--  8) Layer RUOLO: origine_indirizzo_id valorizzato
--  9) Aggiunto il FATT per istanza -> rerun aggiorna (updated_rows = 1)
-- 10) Precedenza per istanza: lo snapshot passa all'indirizzo dell'istanza
-- 11) Idempotenza: terza esecuzione a dati invariati -> (0, 0)
-- 12) Una sola riga FATT per fattura
-- 13) Whitelist: un tipo fuori ambito FATTURA non viene scritto
-- 14) Layer SOGGETTO: CON risolto dal soggetto, origine_indirizzo_id NULL
-- 15) Seed: registry 19 + impl 19 + policy 17/18 presenti e attivi
-- 16) Posizione nello step DRAFT (skip finche' il task non e' armato)
-- ------------------------------------------------------------
-- PERCHE' IL TEST NON CREA UN'ANAGRAFICA NUOVA. Si appoggia a un billing
-- account esistente e occupa solo gli slot indirizzo che gli servono, dopo
-- aver verificato che siano liberi (test 2). Creare soggetto + ruolo + istanza
-- + BA da zero significherebbe attraversare una decina di trigger e vincoli
-- estranei a cio' che si sta testando: il primo rosso arriverebbe dalla
-- fixture, non dalla funzione. Nulla viene cancellato, e il file chiude in
-- ROLLBACK.
--
-- PERCHE' UN SOLO BA E NON DUE ISTANZE. Il piano descrive la precedenza per
-- istanza come «due istanze dello stesso soggetto, ognuna il suo indirizzo».
-- Qui la stessa regola e' esercitata in modo equivalente e piu' economico: si
-- parte dal solo indirizzo generico (test 6 = fallback), poi si aggiunge
-- quello dell'istanza e si rilancia (test 10 = precedenza). Se l'ORDER BY
-- della catena fosse sbagliato, lo snapshot non cambierebbe e il test 10
-- fallirebbe -- che e' esattamente cio' che si vuole sorvegliare.
--
-- ⚠️ TRAPPOLE DI FIXTURE segnalate dal BE (piano BE/FE §4-ter, misurate il
-- 2026-07-31) e qui gia' evitate:
--   (a) CON non e' inseribile sul ruolo cliente (ammesso al solo tipo_ruolo 8):
--       infatti il test 14 lo mette sul layer SOGGETTO, che e' l'unico modo in
--       cui una fattura puo' vederlo;
--   (b) un indirizzo non normalizzato deve avere la forma che lo stato vuole
--       (guard anagrafiche.trgfn_indirizzi_guard_forma_libera, rev 2026-10-18):
--       per l'Italia comune e CAP del catalogo. Le INSERT qui sotto la prendono
--       da dbops.fn_pgtap_indirizzo_libero_forma.
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

-- ============================================================
-- Riferimenti
-- ============================================================
CREATE TEMP TABLE tmp_ti_sif AS
SELECT
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'FATT')    AS fatt_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'CON')     AS con_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'DOMFISC') AS domfisc_id;

-- Riferimenti globali: esistono a prescindere dal BA che si scegliera',
-- quindi il test 1 li verifica davvero invece di passare a vuoto.
CREATE TEMP TABLE tmp_base_sif AS
SELECT
  (SELECT m.registro_id
     FROM vendite.tipi_doc_fiscale_registri m
     JOIN config.tipi_doc_fiscale t ON t.id = m.tipo_doc_fiscale_id
    WHERE t.attivo IS TRUE ORDER BY m.id LIMIT 1)   AS registro_id,
  (SELECT m.tipo_doc_fiscale_id
     FROM vendite.tipi_doc_fiscale_registri m
     JOIN config.tipi_doc_fiscale t ON t.id = m.tipo_doc_fiscale_id
    WHERE t.attivo IS TRUE ORDER BY m.id LIMIT 1)   AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT s.id FROM config.stati_doc_fiscale s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE
    ORDER BY s.id LIMIT 1)                          AS stato_draft_id,
  COALESCE((SELECT st.id FROM config.stati st WHERE st.codice_iso2 = 'IT'),
           (SELECT st.id FROM config.stati st ORDER BY st.id LIMIT 1)) AS stato_id;


-- 1) Riferimenti minimi.
SELECT ok(
  (SELECT registro_id IS NOT NULL AND tipo_doc_fiscale_id IS NOT NULL
      AND valuta_id IS NOT NULL AND stato_draft_id IS NOT NULL
      AND stato_id IS NOT NULL
     FROM tmp_base_sif),
  '1) riferimenti minimi risolti (registro, tipo doc, valuta, stato DRAFT, stato)'
);

CREATE TEMP TABLE tmp_refs_sif AS
SELECT
  ba.id                                             AS billing_account_id,
  ba.soggetto_ruolo_id                              AS soggetto_ruolo_id,
  ba.istanza_utility_id                             AS istanza_utility_id,
  sr.soggetto_id                                    AS soggetto_id,
  anagrafiche.fn_get_emittente_fiscale_id(ba.id)    AS emittente_soggetto_ruolo_id,
  b.registro_id, b.tipo_doc_fiscale_id, b.valuta_id, b.stato_draft_id, b.stato_id
FROM anagrafiche.billing_account ba
JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
CROSS JOIN tmp_ti_sif ti
CROSS JOIN tmp_base_sif b
WHERE anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
  -- ⚠️ Lo spazio indirizzi della fattura dev'essere INTERAMENTE del test, non
  -- solo negli slot che si occupano: basta un RES o un FORNITURA gia' presenti
  -- sul ruolo perche' il task ne scriva uno in piu' e i conteggi dei test 5, 9
  -- e 11 diventino una lotteria sui dati. Si pretende quindi che ne' il ruolo
  -- ne' il soggetto abbiano indirizzi di un tipo ammesso in ambito FATTURA
  -- (piu' DOMFISC, che il test 13 inserisce).
  AND NOT EXISTS (
        SELECT 1 FROM anagrafiche.indirizzi i
         WHERE i.soggetto_ruolo_id = ba.soggetto_ruolo_id
           AND (i.tipo_indirizzo_id = ti.domfisc_id
             OR i.tipo_indirizzo_id IN (SELECT a.tipo_indirizzo_id
                                          FROM config.tipi_indirizzi_allowed a
                                         WHERE a.ambito = 'FATTURA'
                                           AND a.attivo IS TRUE)))
  AND NOT EXISTS (
        SELECT 1 FROM anagrafiche.indirizzi_soggetti isg
         WHERE isg.soggetto_id = sr.soggetto_id
           AND isg.tipo_indirizzo_id IN (SELECT a.tipo_indirizzo_id
                                           FROM config.tipi_indirizzi_allowed a
                                          WHERE a.ambito = 'FATTURA'
                                            AND a.attivo IS TRUE))
ORDER BY ba.id
LIMIT 1;


-- ⛔ IL REGISTRO SI ALLINEA ALL'EMITTENTE, e prima non lo faceva: era scelto
--   dalla mappa tipi_doc_fiscale_registri INDIPENDENTEMENTE da chi emette, e dal
--   2026-08-30 vendite.trgfn_fatture_guard_registro_emittente non ammette piu' la
--   coincidenza. ⚠️ Sta QUI e non accanto a tmp_base_sif: l'emittente nasce con tmp_refs_sif.
UPDATE tmp_base_sif SET registro_id = script.fn_pgtap_registro_fattura(
    (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_sif));
-- 2) Fixture utilizzabile. Se qui e' falso tutto il resto viene saltato:
--    serve un billing account il cui spazio indirizzi (ruolo + soggetto) sia
--    vuoto per i tipi ammessi in ambito FATTURA, cosi' i conteggi dei giri
--    dipendono solo da cio' che inserisce il test.
CREATE TEMP TABLE tmp_gate_sif AS
SELECT EXISTS (SELECT 1 FROM tmp_refs_sif) AS ok;

SELECT ok(
  (SELECT ok FROM tmp_gate_sif),
  '2) fixture utilizzabile: trovato un BA con gli slot indirizzo liberi'
);

-- ============================================================
-- Fattura di test (DRAFT). Le INSERT leggono da tmp_refs_sif:
-- se il gate e' falso non inseriscono nulla e non esplodono.
-- ============================================================
-- ⚠️ Una INSERT ... RETURNING puo' comparire solo dentro una CTE `WITH`:
-- come sottoquery in FROM PostgreSQL la rifiuta con un errore di sintassi.
CREATE TEMP TABLE tmp_fattura_sif AS
WITH ins AS (
  INSERT INTO vendite.fatture (
    registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
    tipo_doc_fiscale_id, stato_doc_fiscale_id, valuta_id, meta
  )
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id,
         r.billing_account_id, r.tipo_doc_fiscale_id, r.stato_draft_id,
         r.valuta_id, jsonb_build_object('test', 'pgtap_snapshot_indirizzi')
    FROM tmp_refs_sif r
  RETURNING id
)
SELECT id FROM ins;

SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sif)
  THEN skip('fixture non disponibile', 1)
  ELSE is((SELECT count(*)::int FROM tmp_fattura_sif), 1,
          '3) fattura di test creata in DRAFT')
END;

-- ============================================================
-- 4) Nessun FATT risolvibile -> errore.
-- ============================================================
SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sif)
  THEN skip('fixture non disponibile', 1)
  ELSE throws_ok(
         format('SELECT * FROM vendite.fn_snapshot_indirizzi_fattura(%s)',
                (SELECT id FROM tmp_fattura_sif)),
         'P0001', NULL,
         '4) FATT assente -> E_INDIRIZZO_FATTURA_MANCANTE')
END;

-- ============================================================
-- Indirizzo FATT GENERICO (istanza_utility_id NULL).
-- Forma libera: indirizzo_libero + stato_id + la forma dello stato (helper).
-- ============================================================
INSERT INTO anagrafiche.indirizzi (
  soggetto_ruolo_id, tipo_indirizzo_id, istanza_utility_id,
  indirizzo_libero, stato_id, comune_id, codice_postale_id, locality, postal_code
)
SELECT r.soggetto_ruolo_id, ti.fatt_id, NULL,
       'Via Generica pgTAP 1', r.stato_id, (dbops.fn_pgtap_indirizzo_libero_forma(r.stato_id)).*  -- rev 2026-10-18: la forma dello stato
  FROM tmp_refs_sif r CROSS JOIN tmp_ti_sif ti;

CREATE TEMP TABLE tmp_run1_sif AS
SELECT s.inserted_rows, s.updated_rows
  FROM tmp_fattura_sif f
 CROSS JOIN LATERAL vendite.fn_snapshot_indirizzi_fattura(f.id) s;

SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sif)
  THEN skip('fixture non disponibile', 1)
  ELSE is((SELECT inserted_rows FROM tmp_run1_sif), 1,
          '5) primo giro: 1 riga inserita')
END;

-- 6) Fallback generico: e' l'indirizzo senza istanza a finire nello snapshot.
SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sif)
  THEN skip('fixture non disponibile', 1)
  ELSE is(
    (SELECT fi.snapshot ->> 'via'
       FROM vendite.fatture_indirizzi fi, tmp_fattura_sif f, tmp_ti_sif ti
      WHERE fi.fattura_id = f.id AND fi.tipo_indirizzo_id = ti.fatt_id),
    'Via Generica pgTAP 1',
    '6) fallback generico: snapshot dall''indirizzo senza istanza')
END;

-- 7) Shape canonico (D-5): le chiavi previste ci sono.
SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sif)
  THEN skip('fixture non disponibile', 1)
  ELSE ok(
    (SELECT fi.snapshot ?& ARRAY['intestazione','via','display']
       FROM vendite.fatture_indirizzi fi, tmp_fattura_sif f, tmp_ti_sif ti
      WHERE fi.fattura_id = f.id AND fi.tipo_indirizzo_id = ti.fatt_id),
    '7) shape canonico: intestazione + via + display presenti')
END;

-- 8) Layer RUOLO: la riga resta agganciata all'indirizzo di origine.
SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sif)
  THEN skip('fixture non disponibile', 1)
  ELSE ok(
    (SELECT fi.origine_indirizzo_id IS NOT NULL
        AND fi.origine_soggetto_ruolo_id IS NOT NULL
       FROM vendite.fatture_indirizzi fi, tmp_fattura_sif f, tmp_ti_sif ti
      WHERE fi.fattura_id = f.id AND fi.tipo_indirizzo_id = ti.fatt_id),
    '8) layer RUOLO: origine_indirizzo_id valorizzato')
END;

-- ============================================================
-- Indirizzo FATT DELL'ISTANZA del BA: deve scavalcare il generico.
-- ============================================================
INSERT INTO anagrafiche.indirizzi (
  soggetto_ruolo_id, tipo_indirizzo_id, istanza_utility_id,
  indirizzo_libero, stato_id, comune_id, codice_postale_id, locality, postal_code
)
SELECT r.soggetto_ruolo_id, ti.fatt_id, r.istanza_utility_id,
       'Via Istanza pgTAP 2', r.stato_id, (dbops.fn_pgtap_indirizzo_libero_forma(r.stato_id)).*  -- rev 2026-10-18: la forma dello stato
  FROM tmp_refs_sif r CROSS JOIN tmp_ti_sif ti;

CREATE TEMP TABLE tmp_run2_sif AS
SELECT s.inserted_rows, s.updated_rows
  FROM tmp_fattura_sif f
 CROSS JOIN LATERAL vendite.fn_snapshot_indirizzi_fattura(f.id) s;

SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sif)
  THEN skip('fixture non disponibile', 1)
  ELSE is((SELECT inserted_rows::text || '/' || updated_rows::text FROM tmp_run2_sif),
          '0/1',
          '9) secondo giro: nessun inserimento, 1 aggiornamento')
END;

-- 10) Precedenza per istanza (C-2 / C-14c): il generico non vince piu'.
SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sif)
  THEN skip('fixture non disponibile', 1)
  ELSE is(
    (SELECT fi.snapshot ->> 'via'
       FROM vendite.fatture_indirizzi fi, tmp_fattura_sif f, tmp_ti_sif ti
      WHERE fi.fattura_id = f.id AND fi.tipo_indirizzo_id = ti.fatt_id),
    'Via Istanza pgTAP 2',
    '10) precedenza per istanza: vince l''indirizzo dell''istanza del BA')
END;

-- ============================================================
-- 11) Idempotenza: a dati invariati il terzo giro non tocca nulla.
-- ============================================================
CREATE TEMP TABLE tmp_run3_sif AS
SELECT s.inserted_rows, s.updated_rows
  FROM tmp_fattura_sif f
 CROSS JOIN LATERAL vendite.fn_snapshot_indirizzi_fattura(f.id) s;

SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sif)
  THEN skip('fixture non disponibile', 1)
  ELSE is((SELECT inserted_rows::text || '/' || updated_rows::text FROM tmp_run3_sif),
          '0/0',
          '11) idempotenza: terzo giro a dati invariati -> (0,0)')
END;

-- 12) Una sola riga FATT per fattura (uq_fatture_indirizzi_uno_per_tipo_).
SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sif)
  THEN skip('fixture non disponibile', 1)
  ELSE is(
    (SELECT count(*)::int
       FROM vendite.fatture_indirizzi fi, tmp_fattura_sif f, tmp_ti_sif ti
      WHERE fi.fattura_id = f.id AND fi.tipo_indirizzo_id = ti.fatt_id),
    1,
    '12) una sola riga FATT per fattura')
END;

-- ============================================================
-- 13) Whitelist: DOMFISC esiste sul ruolo ma non e' ammesso in ambito
--     FATTURA, quindi il task non lo deve nemmeno guardare.
-- ============================================================
INSERT INTO anagrafiche.indirizzi (
  soggetto_ruolo_id, tipo_indirizzo_id, istanza_utility_id,
  indirizzo_libero, stato_id, comune_id, codice_postale_id, locality, postal_code
)
SELECT r.soggetto_ruolo_id, ti.domfisc_id, NULL,
       'Via Domicilio pgTAP 3', r.stato_id, (dbops.fn_pgtap_indirizzo_libero_forma(r.stato_id)).*  -- rev 2026-10-18: la forma dello stato
  FROM tmp_refs_sif r CROSS JOIN tmp_ti_sif ti;

-- ============================================================
-- 14) Layer SOGGETTO (C-14a): CON non puo' stare sul ruolo cliente, quindi
--     arriva dal soggetto. La coppia (origine_indirizzo_id NULL +
--     origine_soggetto_ruolo_id valorizzato) e' cio' che distingue
--     «derivato dall'anagrafica del soggetto» da un una-tantum digitato.
-- ============================================================
INSERT INTO anagrafiche.indirizzi_soggetti (
  soggetto_id, tipo_indirizzo_id,
  indirizzo_libero, stato_id, comune_id, codice_postale_id, locality, postal_code
)
SELECT r.soggetto_id, ti.con_id,
       'Via Consegna Soggetto pgTAP 4', r.stato_id, (dbops.fn_pgtap_indirizzo_libero_forma(r.stato_id)).*  -- rev 2026-10-18: la forma dello stato
  FROM tmp_refs_sif r CROSS JOIN tmp_ti_sif ti;

-- ⚠️ I due indirizzi appena inseriti entrano in gioco solo al giro
-- successivo: senza questa esecuzione i test 13 e 14 guarderebbero lo stato
-- lasciato dal giro precedente e non proverebbero nulla.
CREATE TEMP TABLE tmp_run4_sif AS
SELECT s.inserted_rows, s.updated_rows
  FROM tmp_fattura_sif f
 CROSS JOIN LATERAL vendite.fn_snapshot_indirizzi_fattura(f.id) s;

SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sif)
  THEN skip('fixture non disponibile', 1)
  ELSE is(
    (SELECT count(*)::int
       FROM vendite.fatture_indirizzi fi, tmp_fattura_sif f, tmp_ti_sif ti
      WHERE fi.fattura_id = f.id AND fi.tipo_indirizzo_id = ti.domfisc_id),
    0,
    '13) whitelist: DOMFISC non entra fra gli indirizzi della fattura')
END;

SELECT CASE WHEN NOT (SELECT ok FROM tmp_gate_sif)
  THEN skip('fixture non disponibile', 1)
  ELSE is(
    (SELECT (fi.snapshot ->> 'via') || '|' ||
            (fi.origine_indirizzo_id IS NULL)::text || '|' ||
            (fi.origine_soggetto_ruolo_id IS NOT NULL)::text
       FROM vendite.fatture_indirizzi fi, tmp_fattura_sif f, tmp_ti_sif ti
      WHERE fi.fattura_id = f.id AND fi.tipo_indirizzo_id = ti.con_id),
    'Via Consegna Soggetto pgTAP 4|true|true',
    '14) layer SOGGETTO: snapshot scritto, origine_indirizzo_id NULL')
END;

-- ============================================================
-- 15) Seed del task (2.3, parte inerte).
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM dbops.pipeline_task_registry r
     JOIN dbops.pipeline_task_registry_impl i ON i.task_registry_id = r.id
    WHERE r.task_code = 'snapshot_indirizzi_lotto'
      AND r.attivo IS TRUE AND i.attivo IS TRUE
      AND i.handler_code = 'snapshot_indirizzi_lotto_default')
  +
  (SELECT count(*)::int
     FROM vendite.fatturazione_pipeline_task_policy p
    WHERE p.task_code = 'snapshot_indirizzi_lotto'
      AND p.pipeline_id IN (1, 8) AND p.attivo IS TRUE),
  3,
  '15) seed: registry+impl (1) e policy sulle due corsie DRAFT (2)'
);

-- ============================================================
-- 16) Posizione nello step DRAFT. L'armamento e' deliberatamente rinviato
--     (dipende dalla registrazione del task lato BE): finche' il task non e'
--     nei processi, il test si salta invece di fallire. Si accende da solo.
-- ============================================================
SELECT CASE WHEN NOT EXISTS (
         SELECT 1 FROM vendite.fatturazione_pipeline p
          WHERE p.id IN (1, 8)
            AND p.processi @> '[{"task":"snapshot_indirizzi_lotto"}]'::jsonb)
  THEN skip('task non ancora armato nei processi dello step DRAFT (2.3 parte 2)', 1)
  ELSE is(
    (SELECT count(*)::int FROM vendite.fatturazione_pipeline p
      WHERE p.id IN (1, 8)
        AND (SELECT ord FROM jsonb_array_elements(p.processi)
                          WITH ORDINALITY t(el, ord)
              WHERE el ->> 'task' = 'snapshot_indirizzi_lotto')
          > (SELECT ord FROM jsonb_array_elements(p.processi)
                          WITH ORDINALITY t(el, ord)
              WHERE el ->> 'task' = 'generate_fatture_righe')),
    2,
    '16) posizione: snapshot_indirizzi_lotto dopo generate_fatture_righe su entrambe le corsie')
END;

SELECT * FROM finish();
ROLLBACK;
