-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): emissione, fattura in bozza, riga e legame da dbops.fn_pgtap_fattura_attivita, la sorgente ROOT da dbops.fn_pgtap_crea_commessa (p_con_sorgente_root); ritirato l'UPDATE diretto dello stato della commessa a PRONTA_FATTURAZIONE (aggirava la matrice; l'emissione non lo chiede). Della catena non resta niente a mano.
-- pgtap-contesto: escluso — la ragione e' scritta per esteso piu' sotto in
--   questo stesso file. Dichiarazione leggibile dal cancello
--   scripts/guardrail_pgtap_preambolo.py: distingue «escluso apposta» da
--   «dimenticato», che una nota in prosa non fa.
--   ⚠️ Da riguardare: le esclusioni `rls/` furono fatte IN BLOCCO, e almeno
--   una non ne aveva diritto (brief pgtap-runner-rls-baseline §30.2).
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE vendite.fatture_righe / fatture_riepiloghi_iva ENABLE + FORCE ROW
--   LEVEL SECURITY: il test arma e disarma la RLS per misurare l'invarianza
--   delle viste che ci joinano sopra.
-- pgTAP test — INVARIANZA delle viste che joinano vendite.fatture_righe
--   rispetto all'armamento della RLS sui satelliti fattura (20260729-01..05).
--
-- LA DOMANDA. Armare la RLS su fatture_righe cambia cio' che un operatore
-- vede nelle viste che quella tabella la joinano? La risposta attesa e' NO —
-- le viste filtrano gia' per emittente e la fattura di una commessa ha lo
-- stesso emittente della commessa — ma e' una previsione, e questo file la
-- misura.
--
-- L'ESPERIMENTO. Confrontare "owner" contro "operatore" NON risponderebbe:
-- differirebbero comunque, perche' le viste hanno un proprio filtro di scope
-- (escope.sr_ids) che nulla ha a che vedere con la RLS. Il confronto giusto
-- tiene fissa la sessione OPERATORE e muove una sola variabile:
--
--     stesso operatore, stessa vista, RLS su fatture_righe DISATTIVA
--     stesso operatore, stessa vista, RLS su fatture_righe ENABLE + FORCE
--
-- Tutto cio' che cambia fra le due misure e' imputabile alle policy nuove, e
-- a nient'altro. FORCE serve perche' la sessione gira come titodb (owner):
-- senza, la RLS verrebbe bypassata e il test misurerebbe se' stesso.
--
-- ⭐ IL TEST 2 E' IL PIU' IMPORTANTE. vw_dash_competenza_attivita joina
-- fatture_righe in LEFT JOIN: se le righe fattura sparissero, le sue righe
-- NON sparirebbero — resterebbero con i campi fattura a NULL. Cioe'
-- un'attivita' fatturata mostrata come non fatturata, e la quota del
-- 20260728-13 calcolata sul nulla. E' l'unico modo in cui questa slice
-- potrebbe sbagliare SENZA DIRLO, e contare le sole righe non sparisce:
-- bisogna contare quelle con la fattura ancora agganciata.
-- Le altre due viste joinano in INNER: se qualcosa andasse storto perdono
-- righe, il che e' brutto ma rumoroso.
-- ------------------------------------------------------------
-- ⭐ Rev 2026-10-07 (brief-db-fixture-rls-documenti-costruiti, giro 3): IL
-- MONDO SI COSTRUISCE. Fino a oggi il file pescava «un emittente con una
-- fattura con righe» e misurava cio' che quell'emittente aveva nel DB: su
-- zeroerp_ci (da zero) le viste erano vuote e le quattro uguaglianze passavano
-- come 0 = 0, cioe' senza misurare niente — anche il test 2, il solo che
-- conta. Ora la catena intera, ciascun passo dal dominio: commessa e attivita'
-- (dbops.fn_pgtap_crea_commessa / _attivita), emissione delle attivita'
-- fatturabili (vendite.fn_emit_attivita_fatturabili_da_commessa), fattura
-- dello stesso cliente con la sua riga e il legame attivita' -> riga di
-- fattura, che in esercizio scrive il backend (pipeline di fatturazione): oggi
-- tutti e tre da dbops.fn_pgtap_fattura_attivita (rev 2026-10-25).
-- Il caso 0 dice che il caso del test 2 ESISTE prima di confrontarlo.
-- ------------------------------------------------------------
-- Indice test (0..4):
--   0   senza RLS l'operatore vede l'attivita' di A CON la fattura agganciata, e il suo arco
--   1   vw_dash_competenza_attivita  — stesso numero di righe
--   2   ⭐ vw_dash_competenza_attivita — stesso numero di righe con fattura
--       agganciata (il fallimento SILENZIOSO del LEFT JOIN)
--   3   vw_dash_competenza_errori    — stesso numero di righe
--   4   vw_documento_lineage_archi   — stessi archi DEI DOCUMENTI DI A
--
-- ⚠️ IL LINEAGE SI MISURA SUI DOCUMENTI DI A, NON SUL GRAFO INTERO (rev
--   2026-10-07). vw_documento_lineage_archi non ha un filtro di emittente suo:
--   e' security_invoker, e il suo perimetro E' la RLS delle tabelle di base
--   (tutte con la RLS attiva: per l'applicazione il grafo e' gia' nel
--   perimetro). Da owner, armando il FORCE sulla sola fatture_righe, gli archi
--   verso le fatture delle ALTRE aziende spariscono — ed e' giusto: e' la RLS
--   che lavora. Il conteggio globale quindi DEVE cambiare, e confrontarlo
--   pretendeva una proprieta' che la vista non ha. Fino al 2026-10-07 era verde
--   perche' la fixture pescava l'emittente che su dbdev possedeva tutte quelle
--   fatture: un verde dovuto ai dati. La domanda vera e' l'altra: armare la RLS
--   non deve far sparire gli archi dei PROPRI documenti.
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
-- ⭐ Rev 2026-10-07 (brief-db-veste-utilizzabile): fino a oggi questo file non
--   la aveva, perche' costruiva l'operatore a mano con fn_crea_soggetto_pf e
--   lasciava il soggetto senza indirizzo, contando sul ROLLBACK (§22.4). Ora
--   l'operatore viene dalla madre (dbops.fn_pgtap_crea_operatore_umano), che
--   lo consegna COMPLETO: la riga torna, e i guard del soggetto si esercitano.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- =========================================================
-- Fixture: la catena commessa -> attivita' -> fattura dell'azienda A
-- =========================================================
-- Il builder apre il contesto sul SUO operatore (tecnico) di A: la catena gira
-- nei panni di chi lavora per A, come la gira l'applicazione. La commessa
-- nasce con la sorgente ROOT.
CREATE TEMP TABLE _a AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('rls viste fattura', p_con_sorgente_root => true);

CREATE TEMP TABLE _att AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM _a));

-- L'emissione, la fattura dello STESSO cliente in bozza con la sua riga e il
-- legame attivita' -> riga di fattura (in esercizio lo scrive il backend):
-- dal builder.
CREATE TEMP TABLE _f AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('rls viste fattura', ARRAY[(SELECT attivita_id FROM _att)]);

-- Da qui l'identita' la dichiara il file: si riparte da «nessuno».
SELECT set_config('app.ruolo_applicativo', '', false),
       set_config('app.current_user_id',   '', false);

CREATE TEMP TABLE _refs AS
SELECT emittente_fiscale_id AS emit_pk FROM _a;

-- I nodi di A nel grafo del lineage: la commessa e la fattura costruite.
CREATE TEMP TABLE _nodi_a (tipo_id bigint, uid text);
INSERT INTO _nodi_a
SELECT s.id, (SELECT commessa_id FROM _a)::text
  FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA' AND s.attivo
UNION ALL
SELECT s.id, (SELECT fattura_id FROM _f)::text
  FROM config.sorgenti s WHERE s.codice_interno = 'FATTURA' AND s.attivo;

CREATE TEMP TABLE _op (auth_user_id int, soggetto_id uuid, sr_id bigint, identita_id bigint);

-- ⭐ Rev 2026-10-07 (brief-db-veste-utilizzabile): l'operatore viene dalla
--   MADRE (dbops.fn_pgtap_crea_operatore_umano: persona fisica completa,
--   risorsa umana, veste OPERATORE accesa come all'invito accettato) e
--   l'emittente gli si da' con la funzione di dominio
--   script.fn_change_user_emittenti_scope. Prima la fixture costruiva
--   soggetto, soggetto_ruolo e veste a mano, senza risorsa umana: uno stato
--   che la madre non produce, e che da D-2 (l'operatore umano vale finche'
--   vale il suo rapporto, script.fn_veste_utilizzabile) non e' piu' un
--   operatore valido. Il builder esce con i vincoli IMMEDIATE: niente piu'
--   finestra differita da riaprire per lui.
INSERT INTO _op
SELECT o.auth_user_id, o.soggetto_id, o.soggetto_ruolo_id, o.identita_id
  FROM dbops.fn_pgtap_crea_operatore_umano('rls viste fattura') o;

-- Whitelist = A, con la funzione di dominio (l'operatore nasce senza azienda,
-- come in produzione).
SELECT script.fn_change_user_emittenti_scope(
    (SELECT auth_user_id FROM _op), ARRAY[(SELECT emit_pk FROM _refs)]);

-- Sessione operatore: resta identica per entrambe le misure.
SELECT set_config('app.ruolo_applicativo', 'OPERATORE', true);
SELECT set_config('app.current_user_id', (SELECT auth_user_id FROM _op)::text, true);

CREATE TEMP TABLE _m (fase text, vista text, n bigint);

-- =========================================================
-- MISURA 1 — RLS su fatture_righe NON forzata (l'owner la bypassa)
-- =========================================================
INSERT INTO _m SELECT 'off', 'attivita',        count(*) FROM vendite.vw_dash_competenza_attivita;
INSERT INTO _m SELECT 'off', 'attivita_fatt',   count(*) FROM vendite.vw_dash_competenza_attivita
                                                 WHERE fattura_id IS NOT NULL;
INSERT INTO _m SELECT 'off', 'errori',          count(*) FROM vendite.vw_dash_competenza_errori;
INSERT INTO _m SELECT 'off', 'lineage',         count(*) FROM vendite.vw_documento_lineage_archi a
                                                 WHERE (a.from_tipo_id, a.from_uid) IN (SELECT tipo_id, uid FROM _nodi_a)
                                                    OR (a.to_tipo_id,   a.to_uid)   IN (SELECT tipo_id, uid FROM _nodi_a);

-- ⭐ I casi che i test 2 e 4 proteggono devono ESISTERE: senza, le
--   uguaglianze passerebbero come 0 = 0.
SELECT ok(
    (SELECT n FROM _m WHERE fase = 'off' AND vista = 'attivita_fatt') >= 1
    AND (SELECT n FROM _m WHERE fase = 'off' AND vista = 'lineage') >= 1,
    '0. senza RLS l''operatore vede l''attivita'' di A con la fattura agganciata, e il suo arco nel lineage: i casi dei test 2 e 4 esistono');

-- =========================================================
-- MISURA 2 — stessa sessione, RLS ARMATA e FORZATA
-- =========================================================
ALTER TABLE vendite.fatture_righe          ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_righe          FORCE  ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_riepiloghi_iva ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_riepiloghi_iva FORCE  ROW LEVEL SECURITY;

INSERT INTO _m SELECT 'on',  'attivita',        count(*) FROM vendite.vw_dash_competenza_attivita;
INSERT INTO _m SELECT 'on',  'attivita_fatt',   count(*) FROM vendite.vw_dash_competenza_attivita
                                                 WHERE fattura_id IS NOT NULL;
INSERT INTO _m SELECT 'on',  'errori',          count(*) FROM vendite.vw_dash_competenza_errori;
INSERT INTO _m SELECT 'on',  'lineage',         count(*) FROM vendite.vw_documento_lineage_archi a
                                                 WHERE (a.from_tipo_id, a.from_uid) IN (SELECT tipo_id, uid FROM _nodi_a)
                                                    OR (a.to_tipo_id,   a.to_uid)   IN (SELECT tipo_id, uid FROM _nodi_a);

ALTER TABLE vendite.fatture_righe          NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_riepiloghi_iva NO FORCE ROW LEVEL SECURITY;

-- =========================================================
-- Asserzioni
-- =========================================================
SELECT is(
    (SELECT n FROM _m WHERE fase='on'  AND vista='attivita'),
    (SELECT n FROM _m WHERE fase='off' AND vista='attivita'),
    '1. vw_dash_competenza_attivita: stesso numero di righe con e senza RLS');

SELECT is(
    (SELECT n FROM _m WHERE fase='on'  AND vista='attivita_fatt'),
    (SELECT n FROM _m WHERE fase='off' AND vista='attivita_fatt'),
    '2. vw_dash_competenza_attivita: stesse righe CON FATTURA agganciata '
    '(il LEFT JOIN non deve svuotarsi in silenzio)');

SELECT is(
    (SELECT n FROM _m WHERE fase='on'  AND vista='errori'),
    (SELECT n FROM _m WHERE fase='off' AND vista='errori'),
    '3. vw_dash_competenza_errori: stesso numero di righe con e senza RLS');

SELECT is(
    (SELECT n FROM _m WHERE fase='on'  AND vista='lineage'),
    (SELECT n FROM _m WHERE fase='off' AND vista='lineage'),
    '4. vw_documento_lineage_archi: gli archi dei documenti di A restano con e senza RLS');

SELECT set_config('app.ruolo_applicativo', '', true);
SELECT set_config('app.current_user_id', '', true);

SELECT * FROM finish();
ROLLBACK;
