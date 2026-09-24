-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: P-2 — IL RUBINETTO della coda «solleva il primo motivo»
--       Piano: brief-db-coda-primo-motivo-in-un-posto-solo, sezione 7
-- ------------------------------------------------------------
-- Elenco test (plan 7) — numerati come li stampa il TAP:
--  1) l'helper esiste, con la firma dichiarata
--  2) ⭐⭐ IL RUBINETTO: zero punti IN PERIMETRO sollevano il primo motivo a mano
--  3) ⭐ zero punti NON CLASSIFICATI — un presidio che non sa leggere un sito
--        deve diventare ROSSO, non saltarlo
--  4) il debito FUORI perimetro non cresce (soglia 6, puo' solo calare)
--  5) le ventitre' funzioni bonificate CHIAMANO davvero l'helper (una
--        chiamata, non una menzione: i commenti sono fuori dal conteggio)
--  6) ⚠️ il marcatore non e' troppo LARGO: un codice LETTERALE resta fuori
--  7) ⭐⭐ la canarina: il marcatore non e' troppo STRETTO
--
-- Scopo:
--   ⭐⭐ QUESTO E' IL PRESIDIO CHE CONTA, piu' della bonifica. Senza, i dieci
--   punti sanati tornano: chi scrive una fn_check_* copia la coda dalla guard
--   accanto, ed e' cosi' che si e' arrivati a ventitre' senza che nessuno
--   avesse deciso niente. «Rincorrere gli esistenti senza chiudere il rubinetto
--   e' la forma in cui questi registri non calano mai.»
--
--   ⭐ IL PERIMETRO SI DERIVA, NON SI ELENCA. Un punto e' in perimetro quando
--   fa DUE cose insieme:
--     1) il CODICE che solleva non e' un letterale: lo legge da un motivo
--     2) la fn_check_* da cui viene l'array emette `valori`
--   Solo li' l'helper puo' stare. Dove la check NON emette `valori` la frase la
--   compone il chiamante dai propri dati, e delegare la spezzerebbe:
--   uscirebbero i `%s` grezzi a video (§2.2 del brief). ⇒ Li' il `-> 0` e'
--   LEGITTIMO, e pretendere zero anche li' sarebbe un cancello che boccia il
--   caso giusto — dopo due blocchi sbagliati qualcuno lo spegne.
--   ⭐ Derivandolo, una check che domani aggiunge `valori` fa entrare il suo
--   sito nel perimetro DA SOLA, senza che nessuno aggiorni un elenco.
--
--   🔴 IL MARCATORE E' `->> 'codice'` E NON `-> 0 ->> 'codice'`, e questa riga
--   e' costata una prova per mutazione. Col secondo, il presidio era VERDE PER
--   COSTRUZIONE: prendeva solo la forma scritta INLINE, mentre i dieci siti
--   bonificati usano una variabile d'appoggio —
--       v_primo := v_motivi -> 0;      <- riga a se'
--       ... v_primo ->> 'codice' ...   <- dentro la chiamata
--   cioe' proprio la forma che questo cantiere ha appena tolto non era
--   presidiabile. Rimessa a mano una coda vecchia, il conteggio non si muoveva.
--   ⇒ L'invariante VERO non e' come e' scritto l'indice: e' che **il codice non
--   e' un letterale**. Ed e' lo stesso fatto che rende questi siti invisibili
--   al rubinetto degli accumulatori, che i letterali `'E_...'` li cerca (§7.3).
--
--   ⚠️ QUESTO FILE LEGGE `pg_proc.prosrc`, cioe' il TESTO delle funzioni. E'
--   un'euristica, e va detto: riconosce la forma scritta, non il significato.
--   Per questo esistono il test 3 (un sito che non si riesce a legare alla sua
--   check e' ROSSO, non saltato) e il test 7 (la canarina che si accorge se il
--   marcatore viene ristretto).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- Fixture — la classificazione, in una vista temporanea sola: i test la
--   interrogano invece di ripetere la derivazione cinque volte (e di poter
--   divergere fra loro, che e' il difetto classico dei presidi copiati).
-- ============================================================

-- ⭐ DAL 2026-09-08 LA DERIVAZIONE NON VIVE PIU' QUI (passo V-0 del brief
--   «i motivi si fermano dentro la check»). Stava in questo `pg_temp`, dove
--   nessun altro presidio poteva leggerla — e infatti lo scanner dell'arita'
--   dei messaggi, che ne aveva bisogno, se la sarebbe ricopiata: due letture
--   dello stesso fatto che cominciano a dissentire senza che nessuno lo veda.
--   Adesso e' dbops.vw_punti_primo_motivo (changeSet 20260908-34), e questo
--   file la INTERROGA. Le regole portanti — marcatore `->> 'codice'` e non
--   `-> 0 ->> 'codice'`, tutte le fn_check_* nominate nel corpo e non solo
--   quella assegnata a `v_motivi`, perimetro PESSIMISTA — sono le stesse, e
--   stanno scritte nel commento della vista.
-- ⚠️ Da qui in avanti questo file DIPENDE da quella vista.
CREATE TEMP VIEW punti_primo_motivo AS
SELECT sch,
       fn,
       count(DISTINCT check_funzione)::int                 AS check_trovate,
       -- (i testimoni del test 7 restano fuori dai conteggi: vedi laggiu')
       -- ⭐ PESSIMISTA: basta UNA delle check nominate che emetta `valori`
       --   perche' il sito sia in perimetro. Un presidio che sceglie il ramo
       --   ottimista assolve il caso che dovrebbe segnalare.
       coalesce(bool_or(check_emette_valori), false)       AS in_perimetro
  FROM dbops.vw_punti_primo_motivo
 WHERE fn !~ '^pgtap_'
 GROUP BY sch, fn;

-- ============================================================
-- Asserzioni
-- ============================================================

-- 1) L'helper c'e', e con la firma che il brief dichiara. ⚠️ Il confronto
--    include i NOMI dei parametri, perche' pg_get_function_identity_arguments()
--    li restituisce: scritta coi soli tipi, questa asserzione e' rossa a vuoto.
SELECT is(
    (SELECT pg_get_function_identity_arguments(p.oid)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script' AND p.proname = 'fn_raise_primo_motivo_se_presente'),
    'p_area text, p_funzione text, p_motivi jsonb, p_campo text, p_tx_id uuid, p_context_extra jsonb',
    'script.fn_raise_primo_motivo_se_presente esiste con la firma dichiarata');

-- 2) ⭐⭐ IL RUBINETTO. Zero, e non «pochi»: qui l'helper puo' stare, quindi
--    ogni punto rimasto e' una coda copiata.
SELECT is(
    (SELECT count(*)::int FROM punti_primo_motivo WHERE in_perimetro),
    0,
    'nessun punto IN PERIMETRO solleva ancora il primo motivo a mano');

-- 3) ⭐ Il ramo cieco e' rosso. Un punto marcato di cui non si trovi nessuna
--    fn_check_* non e' «a posto»: e' un sito che il presidio non sa leggere, e
--    un presidio che salta cio' che non capisce diventa verde per sottrazione.
SELECT is(
    (SELECT count(*)::int FROM punti_primo_motivo WHERE check_trovate = 0),
    0,
    'ogni punto marcato si riesce a legare alla sua check: nessun ramo cieco');

-- 4) Il debito fuori perimetro. ⚠️ E' un REGISTRO, non una lista di eccezioni:
--    la soglia puo' solo calare. Cala quando una di quelle check impara a
--    emettere `valori` e il suo sito passa all'helper — il cantiere lasciato
--    aperto nel §6 del brief.
--    ⛔ Non si alza per far passare la CI: un numero piu' alto significa che
--    qualcuno ha scritto una coda nuova, ed e' esattamente la cosa da vedere.
SELECT cmp_ok(
    (SELECT count(*)::int FROM punti_primo_motivo WHERE NOT in_perimetro),
    '<=', 6,
    -- ⭐ 2026-09-09: da 13 a 6. Sei funzioni sono uscite dal debito con C-1/C-2
    --   (escludi_documento_da_giro, riapri_riconsegna_reso, i guard di
    --   transizione di commesse/ordini/preventivi e il guard della chiusura
    --   sorgente), perche' le loro check hanno imparato a emettere `valori`.
    --   ⛔ Non e' un allentamento: la soglia CALA, ed e' l'unico verso ammesso.
    'il debito dei siti FUORI perimetro non cresce (soglia 6, puo'' solo calare)');

-- 5) La bonifica e' arrivata dove diceva: dieci funzioni chiamano l'helper.
--    ⭐ E' il test che ha morso nella prova per mutazione, quando il 2 non
--    mordeva: rimessa una coda vecchia, qui il conteggio scende a nove.
--    🔴 DAL 2026-09-18 SI CONTA UNA CHIAMATA, NON UNA MENZIONE: si tolgono i
--    commenti `--` e si pretende il nome seguito da `(` — la stessa forma con
--    cui dbops.vw_punti_primo_motivo riconosce `fn_log_and_raise_error\s*\(`.
--    Fino a quel giorno il predicato era `prosrc ~ 'fn_raise_primo_motivo_se_presente'`,
--    cioe' il TESTO: e il 18-09 e' entrata script.fn_check_disponibilita_uscita,
--    una fn_check_* PURA che nel proprio commento di testa nomina l'helper
--    come cosa che fa il suo CONSUMATORE. Il predicato vecchio la contava fra
--    «le funzioni che chiamano l'helper» — 20 invece di 19 — e l'asserzione
--    avrebbe affermato una cosa falsa aggiornando il numero. E' la lezione gia'
--    pagata da `_sorgente_senza_commenti` (2026-08-26): un presidio che cerca
--    una stringa nel sorgente si accende sulla PROSA che la spiega.
SELECT is(
    (SELECT count(*)::int FROM pg_proc p
      WHERE regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ 'fn_raise_primo_motivo_se_presente\s*\('
        AND p.proname <> 'fn_raise_primo_motivo_se_presente'),
    23,
    -- ⚠️ 2026-09-09: da 10 a 16. E' un'uguaglianza ESATTA, non una soglia:
    --   scende se una bonifica viene disfatta (ed e' il test che ha morso nella
    --   prova per mutazione), sale se qualcuno ne bonifica un'altra senza
    --   aggiornare questa riga. In entrambi i casi va guardato.
    -- ⭐ 2026-09-14: da 16 a 17. Non una bonifica: un sito NUOVO nato gia'
    --   sull'helper — pagamenti.trgfn_vendite_contabili_righe_guard_contenuto
    --   (D17, brief riga-manuale-nasce-abbinata-ed-elimina-riga), che solleva
    --   il primo motivo di script.fn_check_riga_contabile_eliminabile.
    -- ⭐ 2026-09-18: da 17 a 19. Due siti NUOVI nati sull'helper col Lotto 2 del
    --   magazzino (brief-db-magazzino-lotto-2-motore): magazzino.fn_scrivi_movimento
    --   (20260918-18, due chiamate: fn_check_riga_magazzino e
    --   fn_check_disponibilita_uscita — si conta la FUNZIONE, non le chiamate)
    --   e magazzino.fn_posta_inventario (20260918-23, fn_check_riga_magazzino).
    --   La terza menzione del giorno — fn_check_disponibilita_uscita — e' un
    --   commento, e da questa rev non conta (vedi sopra).
    -- ⭐ 2026-09-18 (sera): da 19 a 20. Un sito NUOVO nato sull'helper —
    --   pagamenti.trgfn_vendite_contabili_guard_validazione (20260918-37,
    --   D20-a, brief-db-validata-e-registrazione-tardiva), che entrando in
    --   VALIDATA solleva il primo motivo di script.fn_check_contabile_validabile.
    -- ⭐ 2026-09-22: da 20 a 21. Un sito NUOVO, e nasce da una bonifica vera:
    --   magazzino.fn_posta_rettifica (20260922-21, R-1 del Lotto 2-bis) non
    --   controllava piu' stato e righe nel proprio corpo — li chiede a
    --   script.fn_check_documento_interno_registrabile, la STESSA funzione da cui
    --   la capability del drawer accende «Registra», e ne solleva il primo motivo.
    --   La gemella fn_posta_inventario era gia' nel conto dal 18-09 (chiamava
    --   l'helper sul motivo di riga) e non si muove: si conta la FUNZIONE, non le
    --   chiamate.
    -- ⭐ 2026-09-24: da 21 a 23. Due siti NUOVI nati sull'helper col building
    --   block dei prezzi non autorizzati (brief-db-preventivi-congelamento-
    --   pricing): vendite.trgfn_contratti_guard_transizione_stato (20260924-25,
    --   verso ATTIVO) e vendite.trgfn_offerte_commerciali_guard_transizione
    --   (20260924-27, verso EMESSA e ACCETTATA), che sollevano il primo motivo di
    --   script.fn_check_prezzi_autorizzati. Il contratto sostituisce un codice
    --   letterale (E_COMPONENTE_PREZZO_PENDENTE), l'offerta un controllo che non
    --   c'era. Le altre due chiamate nuove dello stesso giro — Regola 3 di
    --   trgfn_preventivi_guard_transizione (-22) e Regola 5 di
    --   trgfn_ordini_guard_transizione (-29) — stanno in funzioni gia' nel conto:
    --   si conta la FUNZIONE, non le chiamate.
    'le ventitre'' funzioni bonificate chiamano l''helper');

-- 6) ⚠️ Il marcatore non e' troppo LARGO. vendite.fn_cleanup_fatture_by_ids
--    solleva un codice LETTERALE e dal primo motivo legge solo un valore per la
--    frase (`-> 0 ->> 'dettaglio'`): con un marcatore su `-> 0` entrerebbe nel
--    perimetro e sarebbe un falso positivo. Se questo test diventa rosso,
--    qualcuno ha allargato il marcatore e il cancello ha cominciato a bocciare
--    il caso giusto.
SELECT ok(
    NOT EXISTS (SELECT 1 FROM punti_primo_motivo
                 WHERE sch = 'vendite' AND fn = 'fn_cleanup_fatture_by_ids'),
    'un sito che solleva un codice LETTERALE resta fuori dal perimetro');

-- 7) ⭐⭐ LA CANARINA: il marcatore non e' troppo STRETTO. L'helper e' l'unico
--    posto dove la coda vive ancora, e la scrive nella forma con la variabile
--    d'appoggio — la stessa dei dieci siti bonificati. Se il marcatore smette
--    di riconoscerla, questo test si accorge PRIMA che il rubinetto diventi
--    verde per costruzione.
--    ⚠️ E' successo davvero: la prima stesura cercava `-> 0 ->> 'codice'` e non
--    vedeva nessuno dei dieci. Solo una prova per mutazione l'ha mostrato.
--    ⭐ DAL 2026-09-08 LA CANARINA E' UN TESTIMONE COSTRUITO, e il cambio e'
--    la lezione del file gemello: prima l'asserzione ri-scriveva il marcatore
--    QUI e lo applicava all'helper — cioe' sorvegliava una COPIA del marcatore,
--    non la sede. Da quando la derivazione vive in dbops.vw_punti_primo_motivo,
--    restringerlo LA' lasciava questa riga verde.
--    ⇒ Adesso il test si fabbrica un sito nella forma con la variabile
--    d'appoggio e pretende che la VISTA lo veda. Se qualcuno riporta il
--    marcatore a `-> 0 ->> 'codice'`, questo diventa rosso.
--    ⚠️ Il testimone e' escluso dai conteggi dei test 2-4 (`fn !~ '^pgtap_'`):
--    un presidio che si conta addosso i propri semi sposta le sue soglie.
CREATE FUNCTION pg_temp.pgtap_coda_variabile_appoggio() RETURNS void
LANGUAGE plpgsql AS $f$
DECLARE
    v_motivi jsonb;
    v_primo  jsonb;
BEGIN
    v_motivi := script.fn_check_sorgente_chiudibile(1::bigint, 'PGTAP');
    IF jsonb_array_length(v_motivi) > 0 THEN
        v_primo := v_motivi -> 0;
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'pgtap_coda_variabile_appoggio', v_primo ->> 'codice',
            '{}'::jsonb, NULL::uuid,
            VARIADIC ARRAY(SELECT jsonb_array_elements_text(v_primo -> 'valori')));
    END IF;
END
$f$;

SELECT ok(
    EXISTS (SELECT 1 FROM dbops.vw_punti_primo_motivo
             WHERE sch ~ '^pg_temp' AND fn = 'pgtap_coda_variabile_appoggio'
               AND check_funzione = 'fn_check_sorgente_chiudibile'),
    'la vista riconosce la forma con la variabile d''appoggio e la lega alla sua check (canarina)');

SELECT * FROM finish();
ROLLBACK;
