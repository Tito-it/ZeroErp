-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2c): le famiglie di numerazione col codice della sorgente (DDT_VENDITA, ORDINE_VENDITA, RESO_VENDITA, DISTINTA_INCASSO).
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture CREA un emittente e i suoi registri per
--   provare il provisioning, e nessun operatore ne vede piu' di uno
--   (config.user_emittenti_fiscali ha UNIQUE su auth_user_id). ⚠️ Il test 1
--   girerebbe da chiunque: e' una funzione PURA, e questa e' esattamente la sua
--   qualita' — ma il file e' uno.
-- pgtap-contesto: escluso — discende dal marcatore qui sopra.
-- pgTAP test per Zero ERP
-- Test: il prefisso vive sul REGISTRO, e i contatori sono allineati
--   vendite.fn_componi_numero_documento        (20260831-41)
--   uq_registri_fatturazione_prefisso_suffisso (20260831-40)
--   vendite.fn_provision_registri_emittente    (20260831-44)
--   Piano: brief-db-prefisso-sul-registro-e-allineamento-contatori, §4
-- ------------------------------------------------------------
-- Elenco test (plan 6):
-- 1) ⭐⭐ La COMPOSIZIONE, su una tabella di casi — senza fixture
-- 2) ⛔ Due registri dello stesso emittente con la stessa coppia: respinti
-- 3) ⭐ ...ma due SENZA prefisso ne' suffisso convivono
-- 4) ⭐ I contatori sono allineati: nessuno sotto il massimo gia' emesso
-- 5) ⭐ ...e ci sono contatori da controllare (il gemello anti-muto del 4)
-- 6) ⭐ Un emittente NUOVO nasce con i registri gia' prefissati
--
-- Scopo:
--   ⭐⭐ IL TEST 1 E' IL GUADAGNO DELLA CENTRALIZZAZIONE, e vale la pena dirlo:
--   prima la composizione stava in quattro funzioni, dentro quattro trigger, e
--   per provarla bisognava FABBRICARE un documento — un DDT con la sua riga,
--   il suo indirizzo, la sua causale e la sua transizione di stato. Ora e' una
--   funzione PURA sui VALORI: si prova in una riga di SQL, e tutti i casi
--   stanno in una tabella che si legge a occhio.
--   ⇒ Il costo di provare un caso in piu' e' passato da venti righe di fixture
--   a una riga di VALUES. E' il motivo per cui la funzione pura esiste.
--
--   ⭐ IL TEST 3 E' IL GEMELLO DEL 2, e senza non si distingue «respinge la
--   coppia duplicata» da «respinge due registri qualunque». Il vincolo e'
--   PARZIALE apposta: un registro senza prefisso non ha un nome da tenere
--   distinto, e vietarne due impedirebbe una configurazione legittima.
--
--   ⚠️ IL TEST 5 E' IL GEMELLO ANTI-MUTO DEL 4: un controllo che cerca
--   contatori disallineati passa anche quando di contatori non ce n'e' nessuno.
--
-- ⚠️ COSA QUESTO FILE NON PROVA: che i quattro documenti chiamino davvero la
--   funzione centrale. Quello e' di
--   db/pgtap/vendite/test-documenti-numerazione-trasloco-v1.sql, che li
--   attraversa dal percorso reale.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- 1) ⭐⭐ LA COMPOSIZIONE — pura, senza fixture
-- ============================================================
-- ⭐ Tutti i casi in una tabella: si leggono a occhio, e aggiungerne uno costa
--   una riga. ⚠️ Un `is()` solo e non sei: il diff di pgTAP stampa la riga che
--   diverge, quindi la diagnosi non ci perde niente.
SELECT is(
    (SELECT string_agg(
                c.caso || ' => ' ||
                COALESCE(vendite.fn_componi_numero_documento(
                    c.prefisso, c.corpo, c.progressivo, c.lunghezza, c.suffisso), '<NULL>'),
                E'\n' ORDER BY c.caso)
       FROM (VALUES
           -- caso                    prefisso   corpo             progr  len suffisso
           ('1 standard',             'ORD',     NULL,             1::bigint, 7, NULL),
           ('2 prefisso vuoto',       NULL,      NULL,             1::bigint, 7, NULL),
           ('3 con suffisso',         'DDT',     NULL,             42::bigint, 7, '/A'),
           ('4 commessa',             'CMM-',    'ACME-2026-',     7::bigint, 9, NULL),
           ('5 commessa senza pref',  NULL,      'ACME-2026-',     7::bigint, 9, NULL),
           ('6 progressivo assente',  'ORD',     NULL,             NULL::bigint, 7, NULL)
       ) AS c(caso, prefisso, corpo, progressivo, lunghezza, suffisso)),
    E'1 standard => ORD0000001\n'
    || E'2 prefisso vuoto => 0000001\n'
    || E'3 con suffisso => DDT0000042/A\n'
    || E'4 commessa => CMM-ACME-2026-000000007\n'
    || E'5 commessa senza pref => ACME-2026-000000007\n'
    || '6 progressivo assente => <NULL>',
    '1) La composizione: prefisso, corpo, cifre, suffisso — e il vuoto non lascia residui');

-- ============================================================
-- 2/3) ⛔ LA COPPIA E' UNICA DENTRO L'EMITTENTE
-- ============================================================
-- ⚠️ Si usa un emittente esistente e una utility diversa da NULL, perche' lo
--   slot (famiglia, emittente, utility NULL) e' gia' occupato dal provisioning
--   — e quell'indice non filtra su `attivo`, quindi spegnere non lo libera.
CREATE TEMP TABLE tmp_pfx AS
SELECT r.emittente_soggetto_ruolo_id AS emittente_sr,
       (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1)       AS ut_1,
       (SELECT u.id FROM config.utilities u ORDER BY u.id DESC LIMIT 1)  AS ut_2
  FROM vendite.registri_fatturazione r
 WHERE r.famiglia_documento = 'DDT_VENDITA' AND r.utility_id IS NULL AND r.attivo
 ORDER BY r.id
 LIMIT 1;

INSERT INTO vendite.registri_fatturazione (
    codice, descrizione, emittente_soggetto_ruolo_id,
    famiglia_documento, reset_policy, attivo, utility_id, prefisso, suffisso)
SELECT 'PFXA', 'pgTAP prefisso A', p.emittente_sr, 'DDT_VENDITA', 'ANNUALE', true,
       p.ut_1, 'PFX', 'Z'
  FROM tmp_pfx p;

PREPARE pfx_doppione AS
INSERT INTO vendite.registri_fatturazione (
    codice, descrizione, emittente_soggetto_ruolo_id,
    famiglia_documento, reset_policy, attivo, utility_id, prefisso, suffisso)
SELECT 'PFXB', 'pgTAP prefisso B', p.emittente_sr, 'ORDINE_VENDITA', 'ANNUALE', true,
       p.ut_2, 'PFX', 'Z'
  FROM tmp_pfx p;

SELECT throws_ok(
    'EXECUTE pfx_doppione',
    '23505',
    NULL,
    '2) Due registri dello stesso emittente non possono avere la stessa coppia');

-- ⭐ Il gemello: senza, non si distingue «respinge la coppia duplicata» da
--   «respinge due registri qualunque». Il vincolo e' PARZIALE apposta.
SELECT lives_ok(
    $q$INSERT INTO vendite.registri_fatturazione (
           codice, descrizione, emittente_soggetto_ruolo_id,
           famiglia_documento, reset_policy, attivo, utility_id)
       SELECT 'PFXC', 'pgTAP senza nome', p.emittente_sr, 'ORDINE_VENDITA', 'ANNUALE',
              true, p.ut_2
         FROM tmp_pfx p$q$,
    '3) ...ma due registri SENZA prefisso ne'' suffisso convivono');

-- ============================================================
-- 4/5) ⭐ I CONTATORI SONO ALLINEATI
-- ============================================================
-- ⛔ E' la riparazione del 20260831-39: prima il contatore ripartiva da 1 sotto
--   una forma identica al pregresso, e il vincolo non se ne accorgeva perche'
--   le righe vecchie hanno registro_id NULL — con un NULL da una parte e un
--   registro dall'altra non si collide mai.
-- ⚠️ Si guarda per (registro, anno): il pregresso si lega al registro
--   attraverso l'EMITTENTE, come fa la bonifica.
-- ⚠️ rev 2026-09-21: il contatore che vale e' il MASSIMO fra il secchio
--   dell'anno e il secchio CONTINUO (anno = 0). Dal 20260908-10 un registro
--   con reset_policy = 'NESSUNA' numera in un secchio unico, anno = 0, seminato
--   dal massimo dei secchi d'anno; il secchio 2026 resta com'era, fermo. Il
--   test leggeva SOLO il secchio dell'anno e il 20-09 e' diventato rosso al
--   primo ordine numerato da ORD-72 dopo il cambio di policy (contatore 2026
--   fermo a 36007, continuo a 36008 = il numero emesso): non era un contatore
--   indietro, era il test che guardava il secchio sbagliato. Un registro
--   passato a NESSUNA che non ha ancora numerato non ha il secchio 0, e allora
--   vale quello dell'anno: per questo e' un massimo su entrambi, non un CASE.
-- ⚠️ rev 2026-10-18: il progressivo si legge TOGLIENDO dal numero le parti che
--   il registro dichiara — prefisso, anno con trattino (anno_nel_numero),
--   suffisso — e solo dopo tenendo le cifre. Prima si tenevano tutte le cifre
--   del numero: su un registro con l'anno nel numero ORD2026-0000009 diventava
--   20260000009, e il contatore giusto (9) usciva «sotto il massimo». E' uscito
--   col primo registro con anno_nel_numero che ha numerato davvero (l'ordine di
--   DEVA dagli smoke di dev.smoke): difetto del test, non del contatore.
--   ⭐ Un numero che NON comincia col prefisso (il pregresso nato prima dei
--   prefissi, tutto cifre) non perde niente: per quelli la lettura e' identica
--   a prima. La composizione da cui si risale e' quella di
--   vendite.fn_assegna_numero_documento.
CREATE TEMP TABLE tmp_all AS
WITH documenti AS (
    SELECT 'ORDINE_VENDITA'::character varying AS fam, ef.soggetto_ruolo_id AS sr,
           EXTRACT(YEAR FROM o.data)::smallint AS anno, o.numero::text AS numero
      FROM vendite.ordini o
      JOIN anagrafiche.emittenti_fiscali ef ON ef.id = o.emittente_fiscale_id
     WHERE o.numero IS NOT NULL
    UNION ALL
    SELECT 'DDT_VENDITA', ef.soggetto_ruolo_id, EXTRACT(YEAR FROM d.data)::smallint, d.numero::text
      FROM vendite.ddt d
      JOIN anagrafiche.emittenti_fiscali ef ON ef.id = d.emittente_fiscale_id
     WHERE d.numero IS NOT NULL
    UNION ALL
    SELECT 'RESO_VENDITA', ef.soggetto_ruolo_id, EXTRACT(YEAR FROM r.data)::smallint, r.numero::text
      FROM vendite.resi r
      JOIN anagrafiche.emittenti_fiscali ef ON ef.id = r.emittente_fiscale_id
     WHERE r.numero IS NOT NULL
), spogliati AS (
    SELECT d.fam, d.anno, reg.id AS registro_id, reg.codice AS registro, x3.n AS resto
      FROM documenti d
      JOIN vendite.registri_fatturazione reg
        ON reg.emittente_soggetto_ruolo_id = d.sr
       AND reg.famiglia_documento = d.fam
       AND reg.utility_id IS NULL
     CROSS JOIN LATERAL (SELECT CASE WHEN coalesce(reg.prefisso, '') <> ''
                                          AND starts_with(d.numero, reg.prefisso)
                                     THEN substr(d.numero, length(reg.prefisso) + 1)
                                     ELSE d.numero END AS n) x1
     CROSS JOIN LATERAL (SELECT CASE WHEN reg.anno_nel_numero
                                          AND starts_with(x1.n, d.anno::text || '-')
                                     THEN substr(x1.n, length(d.anno::text) + 2)
                                     ELSE x1.n END AS n) x2
     CROSS JOIN LATERAL (SELECT CASE WHEN coalesce(reg.suffisso, '') <> ''
                                          AND right(x2.n, length(reg.suffisso)) = reg.suffisso
                                     THEN left(x2.n, length(x2.n) - length(reg.suffisso))
                                     ELSE x2.n END AS n) x3
     WHERE d.anno IS NOT NULL
), pregresso AS (
    SELECT fam, anno, registro_id, registro,
           max(NULLIF(regexp_replace(resto, '\D', '', 'g'), '')::bigint) AS max_n
      FROM spogliati
     GROUP BY 1, 2, 3, 4
)
SELECT p.fam, p.anno, p.max_n, p.registro,
       COALESCE((SELECT max(pr.last_numero)
                   FROM vendite.registri_fatturazione_progressivi pr
                  WHERE pr.registro_id = p.registro_id
                    AND pr.anno IN (p.anno, 0)), 0) AS contatore
  FROM pregresso p
 WHERE p.max_n IS NOT NULL;

SELECT is(
    (SELECT COALESCE(string_agg(
                a.fam || '/' || a.registro || '/' || a.anno ||
                ': contatore ' || a.contatore || ' < max ' || a.max_n,
                ', ' ORDER BY a.fam, a.anno), '')
       FROM tmp_all a
      WHERE a.contatore < a.max_n),
    '',
    '4) Nessun contatore e'' sotto il massimo progressivo gia'' emesso');

-- ⚠️ Il gemello anti-muto: un controllo che cerca contatori disallineati passa
--   anche quando di contatori non ce n'e' nessuno.
SELECT ok(
    (SELECT count(*) FROM tmp_all) > 0,
    '5) ...e ci sono contatori da controllare');

-- ============================================================
-- 6) ⭐ UN EMITTENTE NUOVO NASCE GIA' PREFISSATO
-- ============================================================
-- ⚠️ La commessa attende `CMM-` col trattino, e non e' un dettaglio: dal
--   2026-08-31 il separatore non e' piu' un campo a se' e sta DENTRO il
--   prefisso. Copiarne solo meta' e' il difetto che il 20260831-47/48 ha
--   corretto — invisibile sugli altri tre, il cui separatore e' vuoto.
-- ⛔ E' il presidio che chiude il buco aperto dalla decisione «nessun ripiego»:
--   i generatori leggono il prefisso SOLO dal registro, quindi un registro
--   creato senza produce numeri NUDI in silenzio. E questo e' il punto in cui
--   nascono i registri di ogni emittente nuovo — il momento in cui nessuno
--   guarda.
CREATE TEMP TABLE tmp_pfx_new AS
WITH sogg AS (
  SELECT s.id
    FROM anagrafiche.soggetti s
    JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = s.tipo_soggetto_dettaglio_id
    JOIN config.tipi_ruoli_nature_ammesse na ON na.tipo_soggetto_id = tsd.tipo_soggetto_id
    JOIN config.tipi_ruoli tr ON tr.id = na.tipo_ruolo_id AND tr.codice_interno = 'EF'
   WHERE s.attivo IS TRUE
     AND NOT EXISTS (SELECT 1 FROM anagrafiche.soggetti_ruoli sr
                      WHERE sr.soggetto_id = s.id AND sr.tipo_ruolo_id = tr.id)
   ORDER BY s.id LIMIT 1
), ruolo AS (
  INSERT INTO anagrafiche.soggetti_ruoli (soggetto_id, tipo_ruolo_id)
  SELECT sogg.id, (SELECT id FROM config.tipi_ruoli WHERE codice_interno = 'EF')
    FROM sogg
  RETURNING id AS sr
), ins AS (
  INSERT INTO anagrafiche.emittenti_fiscali (soggetto_ruolo_id, codice, brand_meta)
  SELECT ruolo.sr, 'PGTPFX', jsonb_build_object('test_scope', 'pgtap_prefisso')
    FROM ruolo
  RETURNING soggetto_ruolo_id
)
SELECT soggetto_ruolo_id AS sr FROM ins;

SELECT is(
    (SELECT COALESCE(string_agg(r.famiglia_documento || '=' || COALESCE(r.prefisso, '<vuoto>'),
                                ', ' ORDER BY r.famiglia_documento), '<nessun registro>')
       FROM vendite.registri_fatturazione r, tmp_pfx_new n
      WHERE r.emittente_soggetto_ruolo_id = n.sr
        AND r.famiglia_documento <> 'FATTURA'),
    -- ⭐ Rev 2026-09-15: la sesta famiglia, DISTINTA (DIS-), e' la prima fuori
    --   da vendite (brief distinta-numerata-sul-registro, L11/L12).
    'COMMESSA=CMM-, DDT_VENDITA=DDT, DISTINTA_INCASSO=DIS-, ORDINE_VENDITA=ORD, RESO_VENDITA=RESO',
    '6) I registri di un emittente nuovo nascono gia'' col prefisso');

SELECT * FROM finish();
ROLLBACK;
