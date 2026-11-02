-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- LENTE (non cancello) — il quarto lato del codice errore:
--   «il messaggio descrive la condizione che solleva davvero?»
--   Brief: docs/it/dev/work-done/brief-db-be-terzo-lato-presidio-codici.md §18
--
-- ⚠️ PERCHE' `check_` E NON `guardrail_`, ed e' la cosa piu' importante di
--   questo file. Gli altri tre lati del codice errore hanno una regola
--   meccanica — «il codice e' a catalogo?», «ha una policy?», «e' ritirato ma
--   ancora sollevato?» — e quindi un cancello in CI che li tiene. Questo no:
--   chiede di capire COSA SIGNIFICA la condizione, e nessuna euristica sul
--   testo ci arriva.
--
--   Misurato il 2026-08-06: 998 punti di sollevamento, 349 codici distinti,
--   ~31 candidati, **7 difetti reali**. Precisione ~23%. Con quel rapporto un
--   cancello verrebbe spento in una settimana, e spegnere un presidio e' peggio
--   che non averlo. Questa resta una lente da puntare **quando si apre un
--   lotto**, letta a mano.
--
-- ⚠️ NON FIDARSI DELL'ESITO: sono CANDIDATI. Decide la lettura del punto che
--   solleva. Nella misura del 2026-08-06 la maggior parte dei candidati erano
--   falsi positivi — tipicamente guardie di assenza scritte con una variabile
--   (`IF NOT v_trovato`) invece che con `NOT FOUND`, che l'euristica non
--   riconosce come assenza.
--
-- Uso (read-only):
--   psql "$DB_URL" -f scripts/sql/check_messaggio_vs_condizione.sql
--
-- I due gruppi che stampa:
--   A) il NOME promette un'assenza, ma si solleva da un HANDLER DI ECCEZIONE
--      -> il codice dichiara UNA causa e ne cattura qualunque
--   B) la guardia e' un `IF NOT FOUND` netto, ma ne' il nome ne' il messaggio
--      dicono «non trovato» -> il backend dara' 400/422 dove la verita' e' 404
--
-- Cosa ha trovato la prima passata (tutti confermati leggendo il codice):
--   A) E_DOC_COMPONENTE_LISTINO_MANCANTE x4 (handler P0001 che inghiotte 7
--      codici diversi del resolver listini) · E_SNAPSHOT_ID_NOT_FOUND x1
--   B) E_PARAMETRO_INVALIDO x2 — corretti il 2026-08-06 con
--      E_OFFERTA_NON_TROVATA e E_PROFILO_ACCESSO_NON_TROVATO
-- ------------------------------------------------------------

\pset pager off

WITH righe AS (
    -- prosrc spezzato in righe numerate: serve per risalire dalla riga che
    -- nomina il codice alla guardia che la precede.
    SELECT n.nspname::text AS sch,
           p.proname::text AS fn,
           p.oid,
           l.riga,
           l.n
      FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace
      CROSS JOIN LATERAL regexp_split_to_table(p.prosrc, E'\n') WITH ORDINALITY AS l(riga, n)
     WHERE p.prolang = (SELECT oid FROM pg_language WHERE lanname = 'plpgsql')
       AND n.nspname NOT IN ('pg_catalog', 'information_schema')
),
punti AS (
    -- una riga che nomina un codice E_* ed e' preceduta (entro 6 righe) da una
    -- chiamata a fn_log_and_raise_error: e' un argomento, non una menzione.
    --
    -- ⭐ OPPURE la riga DICHIARA UN MOTIVO (linee-guida-sql §12.5.1), dal
    --   2026-09-08. Nel pattern «la madre CHIAMA la check» il letterale E_*
    --   sta DENTRO la fn_check_*, dove nessuna chiamata gli sta vicino: erano
    --   35 codici su 50 codici-motivo, invisibili a questa lente esattamente
    --   come lo erano a dbops.vw_codici_errore_forme_condizione.
    --   ⚠️ Questa lente ha un sensore SUO, copiato da quella vista: allargare
    --   solo la vista l'avrebbe lasciata cieca. Sono due copie dello stesso
    --   fatto, ed e' il motivo per cui vanno toccate insieme.
    --   ⚠️ Il marcatore e' per FORMA e non per nome di funzione: un motivo
    --   dichiarato fuori da una fn_check_* entra lo stesso — un perimetro
    --   scritto a elenco invecchia da solo.
    SELECT r.sch, r.fn, r.oid, r.n,
           (regexp_match(r.riga, '''(E_[A-Z0-9_]+)'''))[1] AS codice
      FROM righe r
     WHERE r.riga ~ '''E_[A-Z0-9_]+'''
       AND r.riga !~ '^\s*--'
       AND (EXISTS (
                 SELECT 1 FROM righe p2
                  WHERE p2.oid = r.oid
                    AND p2.n BETWEEN r.n - 6 AND r.n
                    AND p2.riga ~* 'fn_log_and_raise_error')
            OR r.riga ~ '''codice''\s*,\s*''E_[A-Z0-9_]+''')
),
con_guardia AS (
    -- la guardia e' la piu' vicina fra le righe precedenti che apre un ramo
    SELECT pt.*,
           (SELECT g.riga
              FROM righe g
             WHERE g.oid = pt.oid
               AND g.n <= pt.n
               AND g.n >= pt.n - 25
               AND g.riga ~* '^\s*(IF|ELSIF|ELSE|EXCEPTION\s+WHEN|WHEN\s+OTHERS|WHEN\s+SQLSTATE)\M'
             ORDER BY g.n DESC
             LIMIT 1) AS guardia
      FROM punti pt
),
arricchito AS (
    SELECT c.*,
           me.messaggio,
           -- il NOME promette un'assenza?
           c.codice ~* '(NON_TROVAT|NOT_FOUND|_MANCANTE|_NON_RISOLTO|_ASSENTE|_NON_CONFIGURAT)' AS nome_assenza,
           -- il MESSAGGIO parla di assenza?
           COALESCE(me.messaggio, '') ~* '(non\s+(e''?\s+stat|trovat|esiste|risolt)|inesistente|mancante|nessun)' AS msg_assenza,
           -- la guardia e' un handler di eccezione?
           c.guardia ~* '(EXCEPTION\s+WHEN|WHEN\s+OTHERS|WHEN\s+SQLSTATE)' AS da_eccezione,
           -- la guardia e' un IF NOT FOUND netto?
           c.guardia ~* '^\s*IF\s+NOT\s+FOUND\M' AS if_not_found
      FROM con_guardia c
      -- ⚠️ Due join, e non e' pignoleria: dal 2026-08-07 (changeSet 20260807-13)
      -- il RITIRO sta su `config.codici_errore` — una riga per codice — mentre la
      -- FRASE resta su `config.messaggi_errore`, chiavata (codice, lingua).
      -- Tenere il filtro sul ritiro dentro il join della frase lo renderebbe di
      -- nuovo per-lingua, che e' il difetto appena chiuso.
      LEFT JOIN config.messaggi_errore me
             ON me.codice = c.codice
            AND me.lingua = 'it'
      LEFT JOIN config.codici_errore ce
             ON ce.codice = c.codice
     WHERE c.guardia IS NOT NULL
       AND (ce.obsoleto_dal IS NULL OR ce.obsoleto_dal > CURRENT_DATE)
)
SELECT gruppo, codice, funzione, dettaglio
  FROM (
    -- Riga di contesto: senza, un risultato vuoto non si distingue da una
    -- misura che non ha guardato niente (la lezione dei presidi «silenziosamente
    -- verdi»). Se `punti` fosse zero, l'euristica e' rotta, non il database sano.
    SELECT '0 · base misurata'::text AS gruppo,
           format('%s punti', (SELECT count(*) FROM con_guardia)) AS codice,
           format('%s codici distinti', (SELECT count(DISTINCT codice) FROM con_guardia)) AS funzione,
           format('%s senza guardia riconoscibile (esclusi)',
                  (SELECT count(*) FROM con_guardia WHERE guardia IS NULL)) AS dettaglio,
           0 AS ord
    UNION ALL
    -- (A) nome = assenza, ma si solleva da un handler di eccezione
    SELECT 'A · nome dice assenza, solleva da EXCEPTION',
           codice,
           sch || '.' || fn,
           regexp_replace(guardia, '\s+', ' ', 'g'),
           1
      FROM arricchito
     WHERE nome_assenza AND da_eccezione
    UNION ALL
    -- (B) IF NOT FOUND netto, ma ne' nome ne' messaggio dicono «non trovato»
    SELECT 'B · IF NOT FOUND, ma nome e messaggio tacciono',
           codice,
           sch || '.' || fn,
           COALESCE(messaggio, '(fuori catalogo)'),
           2
      FROM arricchito
     WHERE if_not_found AND NOT nome_assenza AND NOT msg_assenza
  ) x
 ORDER BY ord, codice, funzione;
