-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
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
-- COME SONO SCRITTE LE ASSERZIONI. Non su un documento scelto a mano ma
-- sulla POPOLAZIONE: «quanti violano la regola, su quanti esistono». Una
-- fixture costruita apposta puo' confermare un ramo morto; un conteggio di
-- violazioni su tutti i documenti reali no. Il test 8 e' il guardiano
-- contro il verde vacuo: se la popolazione fosse vuota, i sette verdi
-- sopra non direbbero nulla e questo diventa rosso.
--
-- Indice test (1..8):
--   1) Il DATO: ogni riga `annulla` delle 8 matrici ha outlined=true e
--      l'icona del lotto (pi pi-times-circle), che e' lo standard scelto
--   2) Il PERCORSO: tutte le azioni emesse portano la CHIAVE `outlined`
--      (era assente su preventivo e offerta: il difetto vero)
--   3) Il PERCORSO: ogni «annulla» emesso ha outlined = true
--   4) Il PERCORSO: ogni «annulla» emesso ha icon = pi pi-times-circle
--   5) Ogni azione che cambia stato porta la CHIAVE
--      `target_state_descrizione`
--   6) ...e il suo valore e' la descrizione vera della tabella di stato,
--      non NULL e non un'invenzione
--   7) Le azioni che NON cambiano stato (ristampa, push, crea_revisione)
--      hanno descrizione NULL: non hanno una destinazione da nominare
--   8) Anti-vacuita': la popolazione misurata non e' vuota
--
-- ⚠️ SE IL TEST 3 O IL 4 DIVENTA ROSSO l'aspetto del pulsante distruttivo
-- e' tornato a divergere fra domini. La sede della scelta e' UNA — il
-- `meta` delle transizioni — e questa e' la misura che impedisce che
-- l'ottavo pulsante diverso nasca di nuovo senza che nessuno se ne accorga
-- (decisione dell'owner 2026-08-06: l'aspetto resta un dato, non diventa
-- una regola del design system).
-- ------------------------------------------------------------

BEGIN;
SELECT plan(8);

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

SELECT is(
    (SELECT count(*)::int FROM _seed_annulla
      WHERE (meta->>'outlined') IS DISTINCT FROM 'true'
         OR (meta->>'icon')     IS DISTINCT FROM 'pi pi-times-circle'
         OR (meta->>'severity') IS DISTINCT FROM 'danger'),
    0,
    format('1) seed: le %s righe «annulla» degli 8 domini sono danger + outlined + pi pi-times-circle',
           (SELECT count(*) FROM _seed_annulla)));

-- ------------------------------------------------------------
-- La popolazione del percorso: OGNI azione emessa da OGNI documento degli
-- 8 domini, con accanto la descrizione che la tabella di stato dichiara
-- per la destinazione. Si calcola UNA volta sola, cosi' i conteggi delle
-- asserzioni parlano tutti degli stessi soggetti.
--
-- `descr_attesa` si risolve per codice_interno (non per id): e' la stessa
-- strada che farebbe un consumatore, e se la funzione emettesse la
-- descrizione di un altro stato il test 6 lo vedrebbe.
-- ------------------------------------------------------------
CREATE TEMP TABLE _cap_azioni AS
SELECT 'preventivo'::text AS dominio, a, s.descrizione AS descr_attesa
  FROM vendite.preventivi p
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_preventivo(p.id)->'available_actions') a
  LEFT JOIN config.stati_doc_preventivi s ON s.codice_interno = a->>'target_state'
UNION ALL
SELECT 'offerta', a, s.descrizione
  FROM vendite.offerte_commerciali o
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_offerta(o.id)->'available_actions') a
  LEFT JOIN config.stati_doc_offerte s ON s.codice_interno = a->>'target_state'
UNION ALL
SELECT 'ordine', a, s.descrizione
  FROM vendite.ordini o
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_ordine(o.id)->'available_actions') a
  LEFT JOIN config.stati_doc_ordini s ON s.codice_interno = a->>'target_state'
UNION ALL
SELECT 'ddt', a, s.descrizione
  FROM vendite.ddt d
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_ddt(d.id)->'available_actions') a
  LEFT JOIN config.stati_doc_ddt s ON s.codice_interno = a->>'target_state'
UNION ALL
SELECT 'reso', a, s.descrizione
  FROM vendite.resi r
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_reso(r.id)->'available_actions') a
  LEFT JOIN config.stati_doc_reso s ON s.codice_interno = a->>'target_state'
UNION ALL
SELECT 'contratto', a, s.descrizione
  FROM vendite.contratti c
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_contratto(c.id)->'available_actions') a
  LEFT JOIN config.stati_doc_contratti s ON s.codice_interno = a->>'target_state'
UNION ALL
SELECT 'commessa', a, s.descrizione
  FROM vendite.commesse c
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_commessa(c.id)->'available_actions') a
  LEFT JOIN vendite.stati_commessa s ON s.codice_interno = a->>'target_state'
UNION ALL
SELECT 'lotto', a, s.descrizione
  FROM vendite.fatturazione_lotti fl
  CROSS JOIN LATERAL jsonb_array_elements(
         script.fn_available_actions_lotto(fl.id)->'available_actions') a
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
-- 4) L'icona. Il lotto e' il riferimento: X dentro un cerchio.
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _cap_azioni WHERE a->>'key' = 'annulla') = 0
  THEN pass('4) SKIP: nessun documento con azione «annulla» disponibile (nulla da misurare)')
  ELSE is(
    (SELECT count(*)::int FROM _cap_azioni
      WHERE a->>'key' = 'annulla'
        AND (a->>'icon') IS DISTINCT FROM 'pi pi-times-circle'),
    0,
    format('4) percorso: icon = pi pi-times-circle su tutti i %s «annulla» emessi',
           (SELECT count(*) FROM _cap_azioni WHERE a->>'key' = 'annulla')))
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
--    azioni: un dominio assente non e' un rosso (il DB di sviluppo puo'
--    non avere quei documenti), ma deve VEDERSI, perche' su di lui la
--    copertura di questo file e' zero — non "parziale".
-- ============================================================
SELECT cmp_ok(
    (SELECT count(DISTINCT dominio)::int FROM _cap_azioni),
    '>', 0,
    format('8) misurati %s domini su 8: %s',
           (SELECT count(DISTINCT dominio) FROM _cap_azioni),
           COALESCE((SELECT string_agg(DISTINCT dominio, ', ' ORDER BY dominio) FROM _cap_azioni),
                    'NESSUNO')));

SELECT * FROM finish();
ROLLBACK;
