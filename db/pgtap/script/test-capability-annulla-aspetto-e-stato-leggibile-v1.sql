-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'azione «Annulla» ha lo stesso aspetto nei 8 domini, e ogni azione
--       che cambia stato dice come si CHIAMA lo stato di destinazione.
--       Due lavori del 2026-08-06, misurati insieme perche' vivono nella
--       stessa riga di jsonb_build_object delle stesse otto funzioni.
--
-- PERCHE' NON BASTA GUARDARE IL SEED.
-- `severity: danger` era gia' su tutti e otto i domini; a divergere era
-- `outlined` — e non solo nel dato. Su preventivo e offerta le
-- fn_available_actions_* NON emettevano affatto la chiave: il frontend
-- riceveva un'azione senza quel campo e applicava il default false.
-- Correggere il solo CSV avrebbe dato una verifica VERDE interrogando la
-- tabella e un pulsante rosso pieno a video. E' la stessa lezione del
-- cantiere vie d'uscita: un campo si verifica dal PERCORSO che lo
-- attraversa, non dal punto in cui e' scritto. Il test 1 guarda il dato,
-- i test 2..7 guardano l'uscita delle funzioni — che e' cio' che il
-- frontend riceve davvero.
--
-- ⚠️ LA TRAPPOLA DEL «FALSE» CHE E' UN «ASSENTE».
-- Prima di questo lavoro `a->>'outlined'` su preventivo e offerta tornava
-- NULL, non 'false'. Un controllo scritto `= 'false'` NON li avrebbe presi
-- e sarebbe passato senza misurare niente. Per questo il test 2 verifica
-- la PRESENZA della chiave (`a ? 'outlined'`) separatamente dal suo
-- valore: sono due difetti diversi e devono dare due rossi diversi.
--
-- COME SONO SCRITTE LE ASSERZIONI. Non su un documento scelto a mano ma su
-- UN DOCUMENTO PER OGNI STATO IN USO, in ciascuno degli 8 domini: «quanti
-- violano la regola, su quanti rami esistono». Il test 8 e' il guardiano
-- contro il verde vacuo: se la popolazione fosse vuota, i sette verdi sopra
-- non direbbero nulla e questo diventa rosso.
--
-- ⚠️ rev 2026-09-17 — PERCHE' «UNO PER STATO» E NON «TUTTI I DOCUMENTI».
-- Fino a oggi la popolazione erano TUTTI i documenti degli 8 domini (~49 s
-- come applicazione, di cui 43 sui 51 DDT: D14 di
-- migliorie-generali-da-test-valutazione.md). Il taglio non e' un
-- campionamento sui dati, e' il perimetro giusto per cio' che questo file
-- misura, cioe' la FORMA delle azioni emesse:
--   * le transizioni le produce `t.stato_da_id = <stato del documento>`:
--     due documenti nello stesso stato emettono le STESSE righe di matrice,
--     con la stessa forma. Il secondo ripete il ramo del primo;
--   * le azioni applicative (push, crea_revisione, ristampa) sono oggetti
--     COSTANTI nel codice della funzione: la loro forma non dipende dal
--     documento, dipende solo dal fatto che compaiano. Compaiono se il
--     documento scelto le esercita — e questo NON e' garantito, ne' lo era
--     prima: sulla popolazione intera comparivano «se qualche documento le
--     esercitava». Il test 7 le misura dove le trova; un presidio sulla loro
--     forma che non dipenda dai dati si scrive con una fixture, non
--     allargando la popolazione.
-- Il documento rappresentante di uno stato si sceglie in modo DETERMINISTICO
-- (`ORDER BY stato, id`): un `LIMIT` senza ordine scommette.
--
-- ⚠️ rev 2026-09-27 — L'ICONA NON E' PIU' UN DATO DEL DB.
-- Decisione D-1 di Tid (brief-db-icone-azioni-per-significato, opzione A):
-- il DB manda il SIGNIFICATO dell'azione (`key`), il frontend sceglie il segno
-- dal `key` con una mappa verbo -> icona in core/. Fino a oggi i test 1 e 4
-- pretendevano `icon = pi pi-times-circle` su ogni «annulla»: pinnavano il
-- contratto vecchio. Adesso asseriscono il rovescio — l'`icon` NON c'e' —
-- e due test nuovi (9, 10) lo presidiano dove il campione non arriva:
--   * 9 guarda TUTTE le righe delle 8 matrici, non solo «annulla»;
--   * 10 guarda il CORPO di ogni script.fn_available_actions_*: le azioni
--     applicative (push, crea_revisione, genera_ordine, ristampa) e il
--     documento interno di magazzino avevano il glifo scritto nel codice, e
--     compaiono nel campione solo se un documento le esercita. Il testo della
--     funzione non dipende dai dati.
-- L'aspetto dell'«annulla» che resta un dato (severity, outlined) resta
-- misurato come prima.
--
-- ⚠️ rev 2026-09-28 — NEMMENO IL COLORE E' PIU' UN DATO DEL DB.
-- Decisione di Tid (brief-db-icone-azioni-per-significato §9.1): il colore
-- del pulsante (`severity`) segue la regola dell'icona, lo decide il VERBO,
-- uguale in tutti i domini, e il frontend lo ricava dal `key`. Lo stesso
-- verbo portava colori diversi fra i domini (conferma, riapri, push_commessa).
-- Il test 1 non pretende piu' `severity = danger` (pinnava il contratto
-- vecchio) e resta sulla sola `outlined`; i test 4, 9 e 10 asseriscono
-- l'assenza di `severity` accanto a quella di `icon`, con lo stesso perimetro.
-- ⭐ `outlined` resta un DATO: cambia per STATO (l'annulla di una bozza e'
-- solo bordato), non per verbo, e il test 3 continua a misurarlo.
--
-- rev 2026-10-25 (brief-modello-documento-vendita §7, giro 5): i passaggi di bolla e reso che
--   portano un'azione (emetti_ddt, conferma_reso) si NASCONDONO a chi non l'ha. Il file misura la
--   FORMA delle azioni, non il permesso: l'operatore in sessione riceve le due azioni, cosi' le
--   righe di DDT e reso restano nel campione. Attese invariate.
--
-- Indice test (1..10):
--   1) Il DATO: ogni riga `annulla` delle 8 matrici ha outlined=true
--   2) Il PERCORSO: tutte le azioni emesse portano la CHIAVE `outlined`
--      (era assente su preventivo e offerta: il difetto vero)
--   3) Il PERCORSO: ogni «annulla» emesso ha outlined = true
--   4) Il PERCORSO: nessuna azione emessa porta la chiave `icon` o `severity`
--   5) Ogni azione che cambia stato porta la CHIAVE
--      `target_state_descrizione`
--   6) ...e il suo valore e' la descrizione vera della tabella di stato,
--      non NULL e non un'invenzione
--   7) Le azioni che NON cambiano stato (ristampa, push, crea_revisione)
--      hanno descrizione NULL: non hanno una destinazione da nominare
--   8) Anti-vacuita': la popolazione misurata non e' vuota
--   9) Il DATO: nessuna riga delle 8 matrici ha `icon` o `severity` nel meta
--  10) Il TESTO: nessuna script.fn_available_actions_* nomina `'icon'`,
--      `'severity'` o un glifo `pi pi-...` nel corpo
--
-- ⚠️ SE IL TEST 4, IL 9 O IL 10 DIVENTA ROSSO un glifo o un colore e'
-- tornato nel DB: l'aspetto lo sceglie il frontend dal `key`, e un segno
-- mandato dal DB sarebbe di nuovo la seconda sede che il brief ha chiuso.
--
-- ⚠️ SE IL TEST 3 DIVENTA ROSSO l'aspetto del pulsante distruttivo
-- e' tornato a divergere fra domini. La sede della scelta e' UNA — il
-- `meta` delle transizioni — e questa e' la misura che impedisce che
-- l'ottavo pulsante diverso nasca di nuovo senza che nessuno se ne accorga
-- (decisione dell'owner 2026-08-06: l'aspetto resta un dato, non diventa
-- una regola del design system).
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

-- rev 2026-10-25 (giro 5): si misura la forma, non il permesso — l'operatore
--   riceve le azioni dei passaggi di bolla e reso, senza le quali sparirebbero.
DO $az$ BEGIN
  PERFORM dbops.fn_pgtap_concedi_azione(NULLIF(current_setting('app.current_user_id', true), '')::integer, 'emetti_ddt');
  PERFORM dbops.fn_pgtap_concedi_azione(NULLIF(current_setting('app.current_user_id', true), '')::integer, 'conferma_reso');
END $az$;

SELECT plan(10);

-- ============================================================
-- 1) Il dato. Le 8 matrici, lette con la loro chiave nativa
--    (`attivo` per sette, `ammesso` per quella fiscale), filtrate per
--    action_key e NON per numero di riga: un append al CSV li sposta.
--    Le righe non attive entrano lo stesso: se un giorno vengono
--    riaccese devono gia' avere l'aspetto giusto.
-- ============================================================
CREATE TEMP TABLE _seed_annulla AS
SELECT 'preventivo'::text AS dominio, t.meta FROM config.transizioni_stati_preventivi t
 WHERE t.meta->>'action_key' = 'annulla'
UNION ALL
SELECT 'offerta',    t.meta FROM config.stati_doc_offerte_transizioni t
 WHERE t.meta->>'action_key' = 'annulla'
UNION ALL
SELECT 'ordine',     t.meta FROM config.transizioni_stati_ordini t
 WHERE t.meta->>'action_key' = 'annulla'
UNION ALL
SELECT 'ddt',        t.meta FROM config.transizioni_stati_ddt t
 WHERE t.meta->>'action_key' = 'annulla'
UNION ALL
SELECT 'reso',       t.meta FROM config.transizioni_stati_reso t
 WHERE t.meta->>'action_key' = 'annulla'
UNION ALL
SELECT 'contratto',  t.meta FROM config.transizioni_stati_contratti t
 WHERE t.meta->>'action_key' = 'annulla'
UNION ALL
SELECT 'commessa',   t.meta FROM vendite.transizioni_stati_commessa t
 WHERE t.meta->>'action_key' = 'annulla'
UNION ALL
SELECT 'lotto',      t.meta FROM config.stati_doc_fiscale_transizioni t
 WHERE t.meta->>'action_key' = 'annulla';

-- rev 2026-09-28: solo outlined. Il colore non e' piu' nel meta (test 9).
SELECT is(
    (SELECT count(*)::int FROM _seed_annulla
      WHERE (meta->>'outlined') IS DISTINCT FROM 'true'),
    0,
    format('1) seed: le %s righe «annulla» degli 8 domini sono outlined',
           (SELECT count(*) FROM _seed_annulla)));

-- ------------------------------------------------------------
-- Il CAMPIONE: un documento per ogni (dominio, stato) in uso — vedi la rev
-- 2026-09-17 in testa. `DISTINCT ON (stato) ... ORDER BY stato, id`: il
-- rappresentante e' il documento piu' vecchio di quello stato, sempre lo
-- stesso a parita' di dati. Si popola DOPO il contesto operatore: contiene
-- solo cio' che la RLS lascia vedere.
-- ⚠️ `fatturazione_lotti.stato_doc_fiscale_id` e' NULLABLE per modello: un
--   lotto senza stato e' un gruppo a se' (`DISTINCT ON` tratta i NULL come un
--   valore), e la sua capability entra nella misura come ogni altra.
-- ------------------------------------------------------------
CREATE TEMP TABLE _campione AS
SELECT * FROM (SELECT DISTINCT ON (p.stato_doc_preventivo_id)
                      'preventivo'::text AS dominio, p.id, p.stato_doc_preventivo_id AS stato_id
                 FROM vendite.preventivi p
                ORDER BY p.stato_doc_preventivo_id, p.id) x
UNION ALL
SELECT * FROM (SELECT DISTINCT ON (o.stato_doc_offerta_id)
                      'offerta', o.id, o.stato_doc_offerta_id
                 FROM vendite.offerte_commerciali o
                ORDER BY o.stato_doc_offerta_id, o.id) x
UNION ALL
SELECT * FROM (SELECT DISTINCT ON (o.stato_doc_ordine_id)
                      'ordine', o.id, o.stato_doc_ordine_id
                 FROM vendite.ordini o
                ORDER BY o.stato_doc_ordine_id, o.id) x
UNION ALL
SELECT * FROM (SELECT DISTINCT ON (d.stato_doc_ddt_id)
                      'ddt', d.id, d.stato_doc_ddt_id
                 FROM vendite.ddt d
                ORDER BY d.stato_doc_ddt_id, d.id) x
UNION ALL
SELECT * FROM (SELECT DISTINCT ON (r.stato_doc_reso_id)
                      'reso', r.id, r.stato_doc_reso_id
                 FROM vendite.resi r
                ORDER BY r.stato_doc_reso_id, r.id) x
UNION ALL
SELECT * FROM (SELECT DISTINCT ON (c.stato_doc_contratto_id)
                      'contratto', c.id, c.stato_doc_contratto_id
                 FROM vendite.contratti c
                ORDER BY c.stato_doc_contratto_id, c.id) x
UNION ALL
SELECT * FROM (SELECT DISTINCT ON (c.stato_commessa_id)
                      'commessa', c.id, c.stato_commessa_id
                 FROM vendite.commesse c
                ORDER BY c.stato_commessa_id, c.id) x
UNION ALL
SELECT * FROM (SELECT DISTINCT ON (fl.stato_doc_fiscale_id)
                      'lotto', fl.id, fl.stato_doc_fiscale_id
                 FROM vendite.fatturazione_lotti fl
                ORDER BY fl.stato_doc_fiscale_id, fl.id) x;

-- ------------------------------------------------------------
-- La popolazione del percorso: OGNI azione emessa da OGNI documento del
-- campione, con accanto la descrizione che la tabella di stato dichiara per
-- la destinazione. Si calcola UNA volta sola, cosi' i conteggi delle
-- asserzioni parlano tutti degli stessi soggetti.
--
-- `descr_attesa` si risolve per codice_interno (non per id): e' la stessa
-- strada che farebbe un consumatore, e se la funzione emettesse la
-- descrizione di un altro stato il test 6 lo vedrebbe.
-- ------------------------------------------------------------
CREATE TEMP TABLE _cap_azioni AS
SELECT 'preventivo'::text AS dominio, a, s.descrizione AS descr_attesa
  FROM (SELECT id FROM _campione WHERE dominio = 'preventivo') c
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_preventivo(c.id)->'available_actions') a
  LEFT JOIN config.stati_doc_preventivi s ON s.codice_interno = a->>'target_state'
UNION ALL
SELECT 'offerta', a, s.descrizione
  FROM (SELECT id FROM _campione WHERE dominio = 'offerta') c
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_offerta(c.id)->'available_actions') a
  LEFT JOIN config.stati_doc_offerte s ON s.codice_interno = a->>'target_state'
UNION ALL
SELECT 'ordine', a, s.descrizione
  FROM (SELECT id FROM _campione WHERE dominio = 'ordine') c
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_ordine(c.id)->'available_actions') a
  LEFT JOIN config.stati_doc_ordini s ON s.codice_interno = a->>'target_state'
UNION ALL
SELECT 'ddt', a, s.descrizione
  FROM (SELECT id FROM _campione WHERE dominio = 'ddt') c
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_ddt(c.id)->'available_actions') a
  LEFT JOIN config.stati_doc_ddt s ON s.codice_interno = a->>'target_state'
UNION ALL
SELECT 'reso', a, s.descrizione
  FROM (SELECT id FROM _campione WHERE dominio = 'reso') c
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_reso(c.id)->'available_actions') a
  LEFT JOIN config.stati_doc_reso s ON s.codice_interno = a->>'target_state'
UNION ALL
SELECT 'contratto', a, s.descrizione
  FROM (SELECT id FROM _campione WHERE dominio = 'contratto') c
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_contratto(c.id)->'available_actions') a
  LEFT JOIN config.stati_doc_contratti s ON s.codice_interno = a->>'target_state'
UNION ALL
SELECT 'commessa', a, s.descrizione
  FROM (SELECT id FROM _campione WHERE dominio = 'commessa') c
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_commessa(c.id)->'available_actions') a
  LEFT JOIN vendite.stati_commessa s ON s.codice_interno = a->>'target_state'
UNION ALL
SELECT 'lotto', a, s.descrizione
  FROM (SELECT id FROM _campione WHERE dominio = 'lotto') c
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_lotto(c.id)->'available_actions') a
  LEFT JOIN config.stati_doc_fiscale s ON s.codice_interno = a->>'target_state';

-- ============================================================
-- 2) La chiave `outlined` esiste in OGNI azione emessa.
--    E' il difetto che il solo seed non avrebbe scoperto: prima di oggi
--    preventivo e offerta non la emettevano affatto.
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _cap_azioni) = 0
  THEN fail('2) nessuna azione emessa da nessuno degli 8 domini: vedi test 8')
  ELSE is(
    (SELECT count(*)::int FROM _cap_azioni WHERE NOT (a ? 'outlined')),
    0,
    format('2) percorso: tutte le %s azioni emesse portano la chiave outlined',
           (SELECT count(*) FROM _cap_azioni)))
END;

-- ============================================================
-- 3) Il valore. Chi annulla ha il bordo, non il pieno.
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _cap_azioni WHERE a->>'key' = 'annulla') = 0
  THEN pass('3) SKIP: nessun documento con azione «annulla» disponibile (nulla da misurare)')
  ELSE is(
    (SELECT count(*)::int FROM _cap_azioni
      WHERE a->>'key' = 'annulla'
        AND (a->>'outlined') IS DISTINCT FROM 'true'),
    0,
    format('3) percorso: outlined = true su tutti i %s «annulla» emessi',
           (SELECT count(*) FROM _cap_azioni WHERE a->>'key' = 'annulla')))
END;

-- ============================================================
-- 4) L'icona non arriva dal DB (rev 2026-09-27). Si misura la PRESENZA
--    della chiave, non il valore: un `icon` a null sarebbe ancora la
--    seconda sede, e `a->>'icon' IS NULL` non lo distinguerebbe.
--    Su TUTTE le azioni emesse, non solo «annulla».
--    rev 2026-09-28: anche `severity`, con la stessa regola (brief §9).
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _cap_azioni) = 0
  THEN fail('4) nessuna azione emessa da nessuno degli 8 domini: vedi test 8')
  ELSE is(
    (SELECT count(*)::int FROM _cap_azioni WHERE a ?| ARRAY['icon', 'severity']),
    0,
    format('4) percorso: nessuna delle %s azioni emesse porta la chiave icon o severity',
           (SELECT count(*) FROM _cap_azioni)))
END;

-- ============================================================
-- 5) Il nome dello stato di arrivo: la chiave c'e' su chi cambia stato.
--    Come per outlined, la presenza si misura a parte dal valore: una
--    chiave assente e un valore NULL sono due difetti diversi.
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _cap_azioni WHERE a->>'target_state' IS NOT NULL) = 0
  THEN pass('5) SKIP: nessuna azione di cambio stato disponibile (nulla da misurare)')
  ELSE is(
    (SELECT count(*)::int FROM _cap_azioni
      WHERE a->>'target_state' IS NOT NULL
        AND NOT (a ? 'target_state_descrizione')),
    0,
    format('5) percorso: tutte le %s azioni di cambio stato portano la chiave target_state_descrizione',
           (SELECT count(*) FROM _cap_azioni WHERE a->>'target_state' IS NOT NULL)))
END;

-- ============================================================
-- 6) ...e ne portano il valore VERO. Se la funzione emettesse la
--    descrizione di un altro stato — o NULL — l'operatore leggerebbe una
--    frase sbagliata con la stessa faccia di una giusta.
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _cap_azioni WHERE a->>'target_state' IS NOT NULL) = 0
  THEN pass('6) SKIP: nessuna azione di cambio stato disponibile (nulla da misurare)')
  ELSE is(
    (SELECT count(*)::int FROM _cap_azioni
      WHERE a->>'target_state' IS NOT NULL
        AND (a->>'target_state_descrizione') IS DISTINCT FROM descr_attesa),
    0,
    format('6) percorso: target_state_descrizione == descrizione dello stato di arrivo, su %s azioni',
           (SELECT count(*) FROM _cap_azioni WHERE a->>'target_state' IS NOT NULL)))
END;

-- ============================================================
-- 7) Chi non cambia stato non ha una destinazione da nominare: ristampa,
--    push_commessa, push_contratto, genera_ordine, crea_revisione.
--    Se qui comparisse una descrizione sarebbe un nome inventato.
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _cap_azioni WHERE a->>'target_state' IS NULL) = 0
  THEN pass('7) SKIP: nessuna azione applicativa disponibile (nulla da misurare)')
  ELSE is(
    (SELECT count(*)::int FROM _cap_azioni
      WHERE a->>'target_state' IS NULL
        AND (a->>'target_state_descrizione') IS NOT NULL),
    0,
    format('7) percorso: nessuna descrizione sulle %s azioni che non cambiano stato',
           (SELECT count(*) FROM _cap_azioni WHERE a->>'target_state' IS NULL)))
END;

-- ============================================================
-- 8) Anti-vacuita'. I sette verdi sopra valgono solo se qualcosa e' stato
--    davvero misurato. Il messaggio elenca i domini che hanno prodotto
--    azioni e, per ciascuno, quanti STATI il campione ha attraversato: un
--    dominio assente non e' un rosso (il DB di sviluppo puo' non avere quei
--    documenti), ma deve VEDERSI, perche' su di lui la copertura di questo
--    file e' zero — non "parziale". E dal 2026-09-17 il numero che conta e'
--    quello degli stati, perche' e' quello il perimetro della misura.
-- ============================================================
SELECT cmp_ok(
    (SELECT count(DISTINCT dominio)::int FROM _cap_azioni),
    '>', 0,
    format('8) misurati %s domini su 8, %s stati in tutto: %s',
           (SELECT count(DISTINCT dominio) FROM _cap_azioni),
           (SELECT count(*) FROM _campione),
           COALESCE((SELECT string_agg(d.dominio || ' (' || d.n || ')', ', ' ORDER BY d.dominio)
                       FROM (SELECT c.dominio, count(*) AS n
                               FROM _campione c
                              WHERE c.dominio IN (SELECT DISTINCT dominio FROM _cap_azioni)
                              GROUP BY c.dominio) d),
                    'NESSUNO')));

-- ============================================================
-- 9) Il dato, su TUTTE le righe delle 8 matrici (anche le spente e le
--    automatiche): nessuna porta `icon` ne' `severity` nel meta. E' il seed
--    che il CSV scrive, quindi in CI la popolazione c'e' sempre.
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM (
        SELECT meta FROM config.transizioni_stati_preventivi
        UNION ALL SELECT meta FROM config.stati_doc_offerte_transizioni
        UNION ALL SELECT meta FROM config.transizioni_stati_ordini
        UNION ALL SELECT meta FROM config.transizioni_stati_ddt
        UNION ALL SELECT meta FROM config.transizioni_stati_reso
        UNION ALL SELECT meta FROM config.transizioni_stati_contratti
        UNION ALL SELECT meta FROM vendite.transizioni_stati_commessa
        UNION ALL SELECT meta FROM config.stati_doc_fiscale_transizioni
     ) m WHERE m.meta ?| ARRAY['icon', 'severity']),
    0,
    '9) seed: nessuna riga delle 8 matrici di transizione ha icon o severity nel meta');

-- ============================================================
-- 10) Il testo delle funzioni. Non dipende dai dati: copre le azioni
--     applicative e il documento interno, che il campione puo' non
--     esercitare. Il perimetro e' la FAMIGLIA per prefisso, cosi' una
--     fn_available_actions_* nuova entra da sola; il messaggio dice quante
--     ne ha lette, perche' un perimetro vuoto sarebbe un verde muto.
-- ============================================================
SELECT is(
    (SELECT string_agg(p.proname, ', ' ORDER BY p.proname)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script'
        AND p.proname LIKE 'fn\_available\_actions\_%'
        AND p.prosrc ~ '''icon''|''severity''|pi pi-'),
    NULL,
    format('10) testo: nessuna delle %s script.fn_available_actions_* emette icon, severity o un glifo pi pi-*',
           (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'script' AND p.proname LIKE 'fn\_available\_actions\_%')));

SELECT * FROM finish();
ROLLBACK;
