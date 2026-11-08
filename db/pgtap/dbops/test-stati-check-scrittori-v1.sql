-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — questo file non interroga NESSUN dato di dominio:
--   legge il catalogo di PostgreSQL (pg_constraint, pg_attrdef, pg_proc) e il
--   registro delle dichiarazioni. Un contesto operatore non cambierebbe una
--   riga del risultato, e metterlo darebbe l'impressione che la RLS qui sia
--   esercitata, che sarebbe falso. Dichiarazione leggibile dal cancello
--   scripts/guardrail_pgtap_preambolo.py: distingue «escluso apposta» da
--   «dimenticato».
-- pgtap-runner: owner
-- pgtap-runner-motivo: i test 4..14 CREANO tabelle con un CHECK e funzioni di
--   prova (in transazione, poi annullata) perche' un criterio si prova
--   COSTRUENDO i casi. E' DDL piu' CREATE FUNCTION: il ruolo applicativo non
--   ne fa e non ne deve fare. Stesso criterio del file gemello
--   rls/test-rls-perimetro-scoperto.sql.
--
-- pgTAP test ANTI-REGRESSIONE — il PRESIDIO C1: uno stato previsto dal
-- modello (nel CHECK di una colonna di stato) e mai scritto.
--
-- ChangeSet di riferimento: 20260921-15 (registro), 20260921-16 (misura),
--                           20260921-17 (lista di lavoro), 20260921-19 (seed),
--                           20261104-28 (il corpo da dbops.fn_corpo_funzione)
-- Brief: brief-db-presidio-stati-mai-scritti §2, §3-bis, §4
--
-- Indice test (plan 17):
--   1) ⭐ il perimetro vede ancora le TRENTADUE colonne misurate il 21-09 — o
--      il loro CHECK non e' piu' di quella forma
--   2) ⛔ IL PRESIDIO: nessuna riga NON_DICHIARATO in vw_stati_check_da_sanare
--   3) ⛔ e nessuna DEBITO_ESTINTO: una riga di registro il cui valore ha
--      trovato uno scrittore, o e' uscito dal CHECK, va tolta
--   4) ⭐ ogni canale ammesso dal CHECK del registro e' un ramo VIVO della
--      vista (perimetro letto dal vincolo, non da un elenco)
--   5) ⛔ un valore NUOVO nel CHECK di una tabella di prova, che nessuno
--      scrive, esce NON_DICHIARATO ed e' nella lista di lavoro (COSTRUITO)
--   6) ⛔ una funzione che NOMINA il valore in un WHERE senza scrivere la
--      tabella NON lo rende SCRITTO (COSTRUITO — la trappola 1)
--   7) ⭐ un DEFAULT di colonna rende SCRITTO_DA_DEFAULT il solo valore del
--      default, non gli altri (COSTRUITO — la trappola 2)
--   8) ⭐ una funzione che scrive la tabella per POSIZIONE (INSERT … VALUES
--      (…, p_x, …)) e un chiamante che passa il letterale → SCRITTO con
--      scrittori_indiretti = 1 e scrittori_fn = 0 (COSTRUITO — il secondo salto)
--   9) ⚠️ IL LIMITE: il letterale a TRE salti resta NON_DICHIARATO
--      (COSTRUITO — dichiara il punto cieco, non lo nasconde)
--  10) ⭐ il registro classifica: canale APPLICAZIONE → DICHIARATO_APPLICAZIONE,
--      canale ESENTE → ESENTE (COSTRUITO)
--  11) ⛔ DEBITO_ESTINTO nei due versi: una riga APPLICAZIONE il cui valore ha
--      trovato uno scrittore a DB, e una riga su un valore che nel CHECK non
--      c'e' (COSTRUITO — la dichiarazione non e' un'esenzione)
--  12) ⛔ la forma VARCHAR del CHECK entra nel perimetro (COSTRUITO — la regex
--      del 19-09 ne vedeva una sola)
--  13) ⭐ fuori perimetro PER COSTRUZIONE: `tipo_stato` e `esito_richiesto`
--      non entrano, senza nessun ramo di esclusione (COSTRUITO)
--  14) ⭐ la lista di lavoro e' esattamente la misura filtrata sui due esiti
--      (COSTRUITO: le sette righe di prova, ne' una in piu' ne' una in meno)
--  15) ⛔ una FIXTURE pgTAP (prefisso fn_pgtap_) che scrive il valore — per
--      via diretta e per via indiretta — non lo rende SCRITTO: il presidio
--      misura il sistema, non chi lo collauda (COSTRUITO, rev 20260923-51)
--  16) ⭐ uno scrittore SQL `BEGIN ATOMIC` rende SCRITTO il suo valore: il
--      corpo non sta in prosrc (COSTRUITO, rev 20261104-28 — D15)
--  17) ⭐ un letterale '--' sulla riga dello scrittore non gli taglia il
--      valore: i commenti si tolgono rispettando i letterali (COSTRUITO, rev
--      20261104-28 — D14)
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ IL PROBLEMA, E PERCHE' NON SI VEDE.
--   Un CHECK di appartenenza e' una promessa del modello: ogni valore ammesso
--   e' uno stato che il sistema sa raggiungere. Se un valore e' ammesso e
--   NESSUNO lo scrive, il sistema e' MUTO proprio sul caso che quel valore
--   doveva raccontare — che di regola e' il fallimento. `ERRORE` e' stato nel
--   CHECK di fatturazione_lotti_esiti.stato_esecuzione dal primo giorno, con
--   un contatore dedicato nella summary; nessuno l'ha scritto fino al
--   2026-08-21, e le corse chiudevano in COMPLETATO con un documento
--   rifiutato. ⚠️ E la summary lo NOMINAVA: un presidio che cercasse il
--   letterale nei corpi sarebbe stato verde. E' il test 6.
--
-- ⛔ NON E' UNA MISURA SUI DATI. «Zero righe in stato ERRORE» non dice niente
--   (Regola zero): il presidio guarda CHI PUO' SCRIVERE quel valore —
--   funzioni, default di colonna, chiamanti — cioe' la struttura.
--
-- ⛔ E L'INVARIANTE NON E' «LA VISTA E' VUOTA».
--   Il database vede tre scrittori (default, funzione col letterale,
--   chiamante che lo passa) e NON vede il quarto: un repository Python. Quei
--   valori sono NON_DICHIARATO per il database, legittimamente, e stanno nel
--   registro con canale APPLICAZIONE — li verifica il test del backend. Gli
--   ESENTE portano ragione e data. L'invariante e' «nessuna NON_DICHIARATO e
--   nessuna DEBITO_ESTINTO», nei due versi:
--     * NON_DICHIARATO = un valore che nessuno scrive e nessuno ha guardato;
--     * DEBITO_ESTINTO = una riga di registro che non serve piu': va TOLTA,
--       o zittisce per sempre un valore che potrebbe tornare non scritto.
--
-- ⚠️ DICHIARARE UNA RIGA ZITTISCE QUESTO TEST, e va detto qui.
--   I test 2 e 3 tacciono su tutto cio' che sta nel registro. E' il patto che
--   permette di accendere il cancello subito — ma vuol dire che il presidio
--   vero, per un valore nuovo, sono i test 5..14: provano che la
--   classificazione e' un GESTO e non l'impostazione di fabbrica.
--
-- ⚠️ COSA QUESTO TEST NON DICE. Che il valore scritto sia scritto nel momento
--   giusto. Dice che esiste uno scrittore. Il criterio e' TESTUALE e i suoi
--   limiti stanno nel COMMENT della vista: nominare non e' scrivere (test 6
--   copre il caso «nessuna scrittura», non il WHERE dentro uno scrittore), due
--   salti e non tre (test 9), la copia colonna→colonna e il Python non si
--   vedono (si dichiarano).
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(17);

-- ============================================================
-- ⭐ LA MISURA SI PRENDE UNA VOLTA, NON QUATTORDICI
-- ============================================================
-- La vista scandisce il sorgente di OGNI funzione del database: costa (misurato
-- il 2026-09-22 su dbdev, dopo la rev 20260922-23: ~230 ms a chiamata) e questo
-- file la interrogava DICIASSETTE volte, sempre sullo stesso mondo — 8,3 s di
-- suite per un criterio che non cambia fra un'asserzione e l'altra.
-- ⇒ Due fotografie in TEMP TABLE, una per ciascuno dei due momenti che questo
--   file ha davvero: PRIMA dei casi costruiti (invariante sul database vero) e
--   DOPO (i casi che il test si fabbrica). Fra le asserzioni di uno stesso
--   momento non si crea, non si scrive e non si cancella niente: la fotografia
--   dice esattamente quello che direbbe la vista.
-- ⛔ Non si riscrive qui il FILTRO di vw_stati_check_da_sanare: sarebbe una
--   seconda copia del criterio, cioe' il difetto che questo presidio esiste per
--   trovare. Si fotografa anche quella vista, com'e'.
CREATE TEMP TABLE _misura_0 AS SELECT * FROM dbops.vw_stati_check_scrittori;
CREATE TEMP TABLE _sanare_0 AS SELECT * FROM dbops.vw_stati_check_da_sanare;


-- ============================================================
-- 1. ⭐ IL PERIMETRO NON SI E' RISTRETTO
-- ============================================================
-- ⛔ Le trentadue colonne che la misura ha trovato il 2026-09-21. Restano
--   scritte qui APPOSTA, ed e' l'unico elenco del file: non e' il perimetro
--   (quello lo decide il criterio), e' la prova che il perimetro non si e'
--   ristretto. Senza, «zero righe da sanare» sarebbe compatibile con una rete
--   che ha smesso di pescare — ed e' gia' successo: la regex del 19-09 ne
--   vedeva DICIOTTO, e nessun test lo diceva.
-- ⭐ La via d'uscita non e' il criterio stesso — sarebbe circolare — ma un
--   fatto strutturale indipendente: la colonna non ha piu' un CHECK di
--   appartenenza su di se' (vocabolario passato a catalogo, colonna tolta).
SELECT is_empty(
    $$WITH misurate (sch, tab, col) AS (
          VALUES
            ('config','email_log','stato'),
            ('config','email_outbox','stato'),
            ('dbops','audit_log','status'),
            ('dbops','coda_lavori','stato'),
            ('dbops','idempotency_keys','status'),
            ('documenti','documenti_generati','stato'),
            ('documenti','documenti_generati_eventi','esito'),
            ('documenti','template_documenti_versioni','stato'),
            ('magazzino','inventari','stato_mag_inventario'),
            ('magazzino','movimenti_attesi','stato'),
            ('magazzino','rettifiche','stato_mag_rettifiche'),
            ('magazzino','trasferimenti','stato_trasferimento'),
            ('pagamenti','sepa_mandati','stato'),
            ('pagamenti','sistemazioni','stato'),
            ('pratiche','workflow_definizioni','stato'),
            ('vendite','attivita_consumi','stato_calcolo'),
            ('vendite','attivita_fatturabili','stato_esecuzione'),
            ('vendite','commesse_attivita','stato_approvazione'),
            ('vendite','commesse_attivita','stato_emissione'),
            ('vendite','commesse_push_log','stato'),
            ('vendite','documenti_fatturazione_canali','stato_canale'),
            ('vendite','event_log','severity'),
            ('vendite','fatturazione_lotti','stato_lotto'),
            ('vendite','fatturazione_lotti','stato_operativo'),
            ('vendite','fatturazione_lotti_esiti','stato_esecuzione'),
            ('vendite','fatturazione_lotti_fatture','stato_esecuzione'),
            ('vendite','fatturazione_lotti_log','stato_operativo'),
            ('vendite','fatturazione_lotti_log','status'),
            ('vendite','fatture_fondi_fattura_source','stato'),
            ('vendite','fatture_log','status'),
            ('vendite','fatture_stampa_coda','stato'),
            ('vendite','listini_versioni','stato')
      ), ancora_vincolate AS (
          -- la colonna ha ANCORA un CHECK di appartenenza tutto suo
          SELECT m.sch, m.tab, m.col
            FROM misurate m
            JOIN pg_namespace n  ON n.nspname = m.sch
            JOIN pg_class c      ON c.relnamespace = n.oid AND c.relname = m.tab
            JOIN pg_attribute a  ON a.attrelid = c.oid AND a.attname = m.col
            JOIN pg_constraint k ON k.conrelid = c.oid AND k.contype = 'c'
                                AND array_length(k.conkey, 1) = 1
                                AND k.conkey[1] = a.attnum
                                AND pg_get_constraintdef(k.oid) ~ '= ANY \(\(?ARRAY\['
      )
      SELECT v.sch || '.' || v.tab || '.' || v.col
        FROM ancora_vincolate v
       WHERE NOT EXISTS (SELECT 1 FROM _misura_0 w
                          WHERE w.schema_tabella = v.sch
                            AND w.nome_tabella   = v.tab
                            AND w.colonna        = v.col)$$,
    '1. il perimetro vede ancora le trentadue colonne misurate il 21-09, o il loro CHECK non e'' piu'' di quella forma'
);

-- ============================================================
-- 2..3. ⛔ IL PRESIDIO, nei due versi
-- ============================================================
-- In fallimento il messaggio NOMINA tabella, colonna e valore: su un difetto
-- che non ha nessun altro sintomo, sapere QUALE e' meta' del lavoro.
SELECT is(
    (SELECT string_agg(v.schema_tabella || '.' || v.nome_tabella || '.' || v.colonna || ' = ' || v.valore,
                       ', ' ORDER BY v.schema_tabella, v.nome_tabella, v.colonna, v.valore)
       FROM _sanare_0 v
      WHERE v.esito = 'NON_DICHIARATO'),
    NULL,
    '2. nessun valore di una colonna di stato che nessuno scrive e nessuno ha dichiarato'
);

SELECT is(
    (SELECT string_agg(v.schema_tabella || '.' || v.nome_tabella || '.' || v.colonna || ' = ' || v.valore || ' (' || v.canale || ')',
                       ', ' ORDER BY v.schema_tabella, v.nome_tabella, v.colonna, v.valore)
       FROM _sanare_0 v
      WHERE v.esito = 'DEBITO_ESTINTO'),
    NULL,
    '3. nessuna riga di registro senza piu'' la sua ragione: il valore ha trovato uno scrittore, o e'' uscito dal CHECK'
);

-- ============================================================
-- I casi costruiti — da qui in giu' si semina
-- ============================================================
-- ⛔ I test 1..3 girano PRIMA: dopo queste righe il database contiene apposta
--   valori non dichiarati, e l'ordine non e' un dettaglio.

-- La tabella di prova: dieci valori, un default, e nessun OTTO (serve al
-- test 11: una riga di registro su un valore che nel CHECK non c'e').
-- DIECI e UNDICI (rev 20261104-28) hanno uno scrittore ciascuno, quindi non
-- entrano nella lista di lavoro del test 14.
CREATE TABLE dbops.pgtap_stati_prova (
    id    int  PRIMARY KEY,
    stato text NOT NULL DEFAULT 'UNO'
          CONSTRAINT chk_pgtap_stati_prova_stato
          CHECK (stato = ANY (ARRAY['UNO','DUE','TRE','QUATTRO','CINQUE','SEI','SETTE','NOVE','DIECI','UNDICI']))
);

-- La forma VARCHAR: PostgreSQL la scrive `((stato)::text = ANY ((ARRAY[…
-- ::character varying])::text[]))`, cioe' NON la forma della tabella sopra.
CREATE TABLE dbops.pgtap_stati_prova_vc (
    id    int PRIMARY KEY,
    stato varchar(10) NOT NULL
          CONSTRAINT chk_pgtap_stati_prova_vc_stato CHECK (stato IN ('VA', 'VB'))
);

-- Fuori perimetro per costruzione: un vocabolario chiuso su colonne che NON
-- sono uno stato. Se entrassero, il criterio sarebbe «ogni CHECK di
-- appartenenza» — una regola diversa, che farebbe rumore su ogni
-- classificazione e insegnerebbe a spegnere il presidio.
CREATE TABLE dbops.pgtap_stati_fuori (
    id              int  PRIMARY KEY,
    tipo_stato      text NOT NULL CHECK (tipo_stato = ANY (ARRAY['VARCHAR','FK'])),
    esito_richiesto text NOT NULL CHECK (esito_richiesto = ANY (ARRAY['POSITIVO','NEGATIVO']))
);

-- 6. Nomina DUE in un WHERE e non scrive la tabella: la trappola 1.
CREATE FUNCTION dbops.fn_prova_stati_conta()
RETURNS bigint LANGUAGE sql AS $f$
    SELECT count(*) FROM dbops.pgtap_stati_prova WHERE stato = 'DUE';
$f$;

-- 8. Lo scrittore POSIZIONALE: la colonna nell'elenco, il valore nel VALUES,
--    nessun `SET stato = p_stato` da riconoscere.
CREATE FUNCTION dbops.fn_prova_stati_scrivi(p_id int, p_stato text)
RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    INSERT INTO dbops.pgtap_stati_prova (id, stato)
    VALUES (p_id, p_stato);
END
$f$;

-- 8. Il chiamante che passa TRE dentro la chiamata: il secondo salto.
CREATE FUNCTION dbops.fn_prova_stati_chiama()
RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    PERFORM dbops.fn_prova_stati_scrivi(1, 'TRE');
END
$f$;

-- 9. Il terzo salto: QUATTRO passa per DUE funzioni intermedie.
CREATE FUNCTION dbops.fn_prova_stati_chiama_param(p_stato text)
RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    PERFORM dbops.fn_prova_stati_scrivi(2, p_stato);
END
$f$;
CREATE FUNCTION dbops.fn_prova_stati_terzo()
RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    PERFORM dbops.fn_prova_stati_chiama_param('QUATTRO');
END
$f$;

-- ⚠️ rev 2026-09-23 (20260923-51): le funzioni di prova si chiamano
--   fn_prova_stati_*, non piu' fn_pgtap_stati_*. Il prefisso fn_pgtap_ e'
--   quello degli helper di FIXTURE, che la vista da quella rev non conta: con
--   il nome vecchio i casi 6..11 sarebbero spariti dalla misura.

-- 15. Una FIXTURE che scrive NOVE, nei due modi che la vista riconosce:
--     diretto (UPDATE … SET stato = 'NOVE') e indiretto (passa il letterale
--     allo scrittore posizionale). Il nome ha apposta il prefisso degli
--     helper di fixture: NOVE deve restare NON_DICHIARATO (test 5, 7, 14, 15).
CREATE FUNCTION dbops.fn_pgtap_crea_stati_nove()
RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    UPDATE dbops.pgtap_stati_prova SET stato = 'NOVE' WHERE id = 1;
    PERFORM dbops.fn_prova_stati_scrivi(3, 'NOVE');
END
$f$;

-- 11. Lo scrittore diretto di SETTE, che rende ESTINTA la dichiarazione.
CREATE FUNCTION dbops.fn_prova_stati_sette()
RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    UPDATE dbops.pgtap_stati_prova SET stato = 'SETTE' WHERE id = 1;
END
$f$;

-- 16. Lo scrittore SQL BEGIN ATOMIC: prosrc e' VUOTO, il corpo sta in
--     prosqlbody. Prima di 20261104-28 la vista non lo vedeva, e DIECI usciva
--     NON_DICHIARATO.
CREATE FUNCTION dbops.fn_prova_stati_dieci()
RETURNS void LANGUAGE sql
BEGIN ATOMIC
    UPDATE dbops.pgtap_stati_prova SET stato = 'DIECI' WHERE id = 1;
END;

-- 17. Un letterale '--' PRIMA del valore, sulla stessa riga. La copia di
--     prima toglieva da '--' a fine riga e UNDICI spariva; il building block
--     sa che quel '--' sta dentro un letterale.
CREATE FUNCTION dbops.fn_prova_stati_undici(p_nota text)
RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    UPDATE dbops.pgtap_stati_prova SET stato = CASE WHEN p_nota = '--' THEN 'UNDICI' END WHERE id = 1;
END
$f$;

-- Le righe di registro di prova: due canali vivi (10), una dichiarazione
-- che uno scrittore ha reso inutile e una su un valore fuori dal CHECK (11).
INSERT INTO dbops.stati_check_dichiarazioni
    (schema_tabella, nome_tabella, colonna, valore, canale, ragione)
VALUES
    ('dbops', 'pgtap_stati_prova', 'stato', 'CINQUE', 'APPLICAZIONE',
     'Riga di prova del pgTAP: dichiara che CINQUE lo scrive un repository Python, per provare il ramo DICHIARATO_APPLICAZIONE.'),
    ('dbops', 'pgtap_stati_prova', 'stato', 'SEI', 'ESENTE',
     'Riga di prova del pgTAP: dichiara SEI esente con una ragione, per provare il ramo ESENTE.'),
    ('dbops', 'pgtap_stati_prova', 'stato', 'SETTE', 'APPLICAZIONE',
     'Riga di prova del pgTAP: dichiara SETTE scritto dal Python mentre una funzione a DB lo scrive, per provare il verso DEBITO_ESTINTO.'),
    ('dbops', 'pgtap_stati_prova', 'stato', 'OTTO', 'ESENTE',
     'Riga di prova del pgTAP: dichiara un valore che nel CHECK non esiste, per provare il verso DEBITO_ESTINTO fuori dal perimetro.');


-- La SECONDA fotografia: da qui in giu' si asserisce sui casi costruiti, e il
-- mondo non cambia piu' fino al cleanup (vedi la nota sopra la prima).
CREATE TEMP TABLE _misura_1 AS SELECT * FROM dbops.vw_stati_check_scrittori;
CREATE TEMP TABLE _sanare_1 AS SELECT * FROM dbops.vw_stati_check_da_sanare;

-- ============================================================
-- 4. ⭐ I CANALI DEL REGISTRO CONTRO I RAMI DELLA VISTA
-- ============================================================
-- ⛔ Il perimetro non e' un elenco mio: e' il CHECK di
--   dbops.stati_check_dichiarazioni. Il giorno in cui qualcuno aggiunge un
--   canale al vocabolario e non gli da' un ramo nella vista, quel canale
--   sarebbe dichiarabile e mai classificato. Qui diventa rosso e dice quale.
-- ⭐ Gira DOPO i casi costruiti: e' con quelli che entrambi i rami sono
--   abitati per costruzione, non per come e' fatto il registro di oggi.
-- ⛔ E si guarda SOLO cio' che il criterio produce — `esito <> 'DEBITO_ESTINTO'`
--   — perche' quel ramo ripubblica il canale leggendolo dal REGISTRO
--   (rls/test-rls-perimetro-scoperto.sql t.3: senza questo filtro il test
--   restava verde a ramo tolto).
SELECT is(
    (SELECT count(*)::int
       FROM (
           SELECT unnest(regexp_matches(
                      pg_get_constraintdef(c.oid),
                      '''([A-Z_]+)''::text', 'g')) AS canale
             FROM pg_constraint c
            WHERE c.conrelid = 'dbops.stati_check_dichiarazioni'::regclass
              AND c.conname  = 'chk_stati_check_dichiarazioni_canale'
       ) v
      WHERE NOT EXISTS (SELECT 1 FROM _misura_1 w
                         WHERE w.canale = v.canale
                           AND w.esito <> 'DEBITO_ESTINTO')),
    0,
    '4. ogni canale ammesso dal CHECK del registro e'' un ramo vivo della vista'
);

-- ============================================================
-- 5..14. I casi costruiti, uno per proprieta'
-- ============================================================
SELECT is(
    (SELECT w.esito || ' / ' || (EXISTS (SELECT 1 FROM _sanare_1 s
                                          WHERE s.nome_tabella = 'pgtap_stati_prova' AND s.valore = 'NOVE'))::text
       FROM _misura_1 w
      WHERE w.schema_tabella = 'dbops' AND w.nome_tabella = 'pgtap_stati_prova' AND w.valore = 'NOVE'),
    'NON_DICHIARATO / true',
    '5. un valore nuovo che nessuno scrive esce NON_DICHIARATO ed e'' nella lista di lavoro: la classificazione e'' un gesto, non l''impostazione di fabbrica'
);

SELECT is(
    (SELECT w.esito || ' / fn=' || w.scrittori_fn || ' / ind=' || w.scrittori_indiretti
       FROM _misura_1 w
      WHERE w.schema_tabella = 'dbops' AND w.nome_tabella = 'pgtap_stati_prova' AND w.valore = 'DUE'),
    'NON_DICHIARATO / fn=0 / ind=0',
    '6. una funzione che NOMINA il valore in un WHERE senza scrivere la tabella non lo rende SCRITTO (trappola 1: nominare non e'' scrivere)'
);

SELECT is(
    (SELECT string_agg(w.valore || ':' || w.esito || ':' || w.ha_default, ', ' ORDER BY w.valore)
       FROM _misura_1 w
      WHERE w.schema_tabella = 'dbops' AND w.nome_tabella = 'pgtap_stati_prova'
        AND w.valore IN ('UNO', 'NOVE')),
    'NOVE:NON_DICHIARATO:false, UNO:SCRITTO_DA_DEFAULT:true',
    '7. il DEFAULT rende SCRITTO_DA_DEFAULT il solo valore del default, non gli altri (trappola 2: il default nasconde uno scrittore assente)'
);

SELECT is(
    (SELECT w.esito || ' / fn=' || w.scrittori_fn || ' / ind=' || w.scrittori_indiretti || ' / ' || w.scrittori_nomi
       FROM _misura_1 w
      WHERE w.schema_tabella = 'dbops' AND w.nome_tabella = 'pgtap_stati_prova' AND w.valore = 'TRE'),
    'SCRITTO / fn=0 / ind=1 / dbops.fn_prova_stati_chiama',
    '8. scrittore POSIZIONALE (INSERT … VALUES (…, p_stato, …)) piu'' un chiamante che passa il letterale: SCRITTO per il secondo salto, e il nome e'' quello del chiamante'
);

SELECT is(
    (SELECT w.esito FROM _misura_1 w
      WHERE w.schema_tabella = 'dbops' AND w.nome_tabella = 'pgtap_stati_prova' AND w.valore = 'QUATTRO'),
    'NON_DICHIARATO',
    '9. IL LIMITE: a tre salti il letterale resta NON_DICHIARATO — il punto cieco e'' scritto, non nascosto'
);

SELECT is(
    (SELECT string_agg(w.valore || ':' || w.esito, ', ' ORDER BY w.valore)
       FROM _misura_1 w
      WHERE w.schema_tabella = 'dbops' AND w.nome_tabella = 'pgtap_stati_prova'
        AND w.valore IN ('CINQUE', 'SEI')),
    'CINQUE:DICHIARATO_APPLICAZIONE, SEI:ESENTE',
    '10. il registro classifica per canale: APPLICAZIONE → DICHIARATO_APPLICAZIONE, ESENTE → ESENTE'
);

SELECT is(
    (SELECT string_agg(w.valore || ':' || w.esito || ':' || coalesce(w.vincolo, '-'), ', ' ORDER BY w.valore)
       FROM _sanare_1 s
       JOIN _misura_1 w USING (schema_tabella, nome_tabella, colonna, valore)
      WHERE s.schema_tabella = 'dbops' AND s.nome_tabella = 'pgtap_stati_prova'
        AND s.valore IN ('SETTE', 'OTTO')),
    'OTTO:DEBITO_ESTINTO:-, SETTE:DEBITO_ESTINTO:chk_pgtap_stati_prova_stato',
    '11. DEBITO_ESTINTO nei due versi: la dichiarazione APPLICAZIONE che uno scrittore a DB ha reso inutile, e la riga su un valore fuori dal CHECK — e tutte e due sono nella lista di lavoro'
);

SELECT is(
    (SELECT string_agg(w.valore || ':' || w.esito, ', ' ORDER BY w.valore)
       FROM _misura_1 w
      WHERE w.schema_tabella = 'dbops' AND w.nome_tabella = 'pgtap_stati_prova_vc'),
    'VA:NON_DICHIARATO, VB:NON_DICHIARATO',
    '12. la forma VARCHAR del CHECK ((col)::text = ANY ((ARRAY[…])::text[])) entra nel perimetro: la regex del 19-09 ne vedeva una sola'
);

SELECT is_empty(
    $$SELECT colonna FROM _misura_1
       WHERE schema_tabella = 'dbops' AND nome_tabella = 'pgtap_stati_fuori'$$,
    '13. tipo_stato ed esito_richiesto restano fuori PER COSTRUZIONE (forma positiva del nome), senza nessun ramo di esclusione'
);

SELECT is(
    (SELECT string_agg(s.nome_tabella || '.' || s.valore || ':' || s.esito, ', ' ORDER BY s.nome_tabella, s.valore)
       FROM _sanare_1 s
      WHERE s.schema_tabella = 'dbops' AND s.nome_tabella LIKE 'pgtap_stati_%'),
    'pgtap_stati_prova.DUE:NON_DICHIARATO, pgtap_stati_prova.NOVE:NON_DICHIARATO, pgtap_stati_prova.OTTO:DEBITO_ESTINTO, pgtap_stati_prova.QUATTRO:NON_DICHIARATO, pgtap_stati_prova.SETTE:DEBITO_ESTINTO, pgtap_stati_prova_vc.VA:NON_DICHIARATO, pgtap_stati_prova_vc.VB:NON_DICHIARATO',
    '14. la lista di lavoro e'' esattamente la misura filtrata sui due esiti: le sette righe di prova, ne'' una in piu'' ne'' una in meno'
);

SELECT is(
    (SELECT w.esito || ' / fn=' || w.scrittori_fn || ' / ind=' || w.scrittori_indiretti
       FROM _misura_1 w
      WHERE w.schema_tabella = 'dbops' AND w.nome_tabella = 'pgtap_stati_prova' AND w.valore = 'NOVE'),
    'NON_DICHIARATO / fn=0 / ind=0',
    '15. una FIXTURE pgTAP (fn_pgtap_*) che scrive il valore, diretta o indiretta, non lo rende SCRITTO: il presidio misura il sistema, non chi lo collauda'
);

SELECT is(
    (SELECT w.esito || ' / fn=' || w.scrittori_fn || ' / ' || w.scrittori_nomi
       FROM _misura_1 w
      WHERE w.schema_tabella = 'dbops' AND w.nome_tabella = 'pgtap_stati_prova' AND w.valore = 'DIECI'),
    'SCRITTO / fn=1 / dbops.fn_prova_stati_dieci',
    '16. uno scrittore SQL BEGIN ATOMIC rende SCRITTO il suo valore: il corpo si legge da dbops.fn_corpo_funzione, non da prosrc (vuoto)'
);

SELECT is(
    (SELECT w.esito || ' / fn=' || w.scrittori_fn || ' / ' || w.scrittori_nomi
       FROM _misura_1 w
      WHERE w.schema_tabella = 'dbops' AND w.nome_tabella = 'pgtap_stati_prova' AND w.valore = 'UNDICI'),
    'SCRITTO / fn=1 / dbops.fn_prova_stati_undici',
    '17. un letterale ''--'' sulla riga dello scrittore non gli taglia il valore: i commenti si tolgono rispettando i letterali'
);

DELETE FROM dbops.stati_check_dichiarazioni
 WHERE schema_tabella = 'dbops' AND nome_tabella = 'pgtap_stati_prova';
DROP FUNCTION dbops.fn_pgtap_crea_stati_nove();
DROP FUNCTION dbops.fn_prova_stati_sette();
DROP FUNCTION dbops.fn_prova_stati_undici(text);
DROP FUNCTION dbops.fn_prova_stati_dieci();
DROP FUNCTION dbops.fn_prova_stati_terzo();
DROP FUNCTION dbops.fn_prova_stati_chiama_param(text);
DROP FUNCTION dbops.fn_prova_stati_chiama();
DROP FUNCTION dbops.fn_prova_stati_scrivi(int, text);
DROP FUNCTION dbops.fn_prova_stati_conta();
DROP TABLE dbops.pgtap_stati_fuori;
DROP TABLE dbops.pgtap_stati_prova_vc;
DROP TABLE dbops.pgtap_stati_prova;

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia dietro di se' nessuna tabella, nessuna funzione e
-- nessuna riga di registro di prova.
ROLLBACK;
