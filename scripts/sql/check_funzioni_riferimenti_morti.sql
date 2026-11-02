-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- Zero ERP — controllo diagnostico (NON e' un changeSet)
--
-- Funzioni plpgsql con riferimenti che non si risolvono piu'.
--
-- USO:
--   set -a; . db/internal.env; set +a
--   psql -X -q -f scripts/sql/check_funzioni_riferimenti_morti.sql \
--        -o /tmp/riferimenti-morti.txt
--
-- Richiede l'estensione `plpgsql_check` (changeSet 20260804-36, contesto
-- provision). Se manca, il file fallisce subito e in modo eloquente.
--
-- Brief: docs/it/dev/work-done/brief-db-bonifica-riferimenti-morti.md
--
-- v1 (2026-08-04) produsse 60 righe, di cui ~33 falsi positivi di DUE
-- tipi soli. La v2 li classifica invece di nasconderli: nessuna riga
-- sparisce, ognuna esce con la sua etichetta.
--
--   1) TRIGGER MULTI-TABELLA — la v1 validava una trigger function
--      contro UN SOLO trigger (il primo). Una funzione generica scritta
--      per tre tabelle veniva quindi controllata contro una sola, e i
--      rami delle altre due risultavano «errori».
--      ⚠️ Rimedio: si valida contro OGNI tabella su cui e' agganciata, e
--      l'errore vale solo se compare per TUTTE. Se compare per alcune e
--      non per altre, e' un ramo dedicato a un'altra tabella — cioe' il
--      comportamento voluto, non un difetto.
--
--   2) VARIADIC — `script.fn_log_and_raise_error(..., VARIADIC text[])`
--      ammette di omettere del tutto i valori variadici; plpgsql_check
--      non lo sa e segnala «la funzione non esiste».
--      ⚠️ Ma NON tutte queste righe sono false: se fra gli argomenti c'e'
--      un `bigint`, un `integer` o un `text[]`, il cast implicito a
--      `text` non esiste e la chiamata fallisce DAVVERO a runtime — il
--      guard solleva un errore incomprensibile invece del messaggio di
--      dominio. Si distingue guardando i TIPI: se sono tutti
--      testo-compatibili e' rumore, se ce n'e' uno che non lo e' e' un
--      difetto vero.
--      Il riconoscimento usa lo SQLSTATE 42883 (undefined_function), non
--      il testo del messaggio: cosi' non dipende dalla lingua del server.
--
--   3) TRANSITION TABLE — `REFERENCING NEW TABLE AS new_rows` crea una
--      relazione che esiste SOLO durante lo scatto del trigger. Il nome
--      non si indovina: si legge da `pg_trigger.tgnewtable/tgoldtable`.
--
--   4) SQL DINAMICO — un errore di sintassi dentro un `EXECUTE` e' quasi
--      sempre un segnaposto non ancora sostituito, non codice rotto.
--
-- ── v3 (2026-08-04), dopo la prima bonifica vera ─────────────────────
--   Tre cose imparate lavorando le 33 righe, tutte scritte qui perche' il
--   prossimo che legge non le ri-scopra:
--
--   A) La regola VARIADIC era troppo larga e ha scusato un difetto vero.
--      Ora l'esenzione richiede che la funzione chiamata **abbia davvero**
--      un parametro VARIADIC (`pg_proc.provariadic <> 0`). Dettaglio nel
--      commento della regola (2) piu' sotto.
--
--   B) ⚠️ La regola RAMO_ALTRA_TABELLA ha un buco speculare a quello che
--      copre. Confronta le tabelle **agganciate**: un ramo scritto per una
--      tabella che non e' agganciata a niente — perche' non esiste piu' —
--      compare su tutte e passa per difetto vero. Il verdetto e' giusto
--      (e' codice morto), la motivazione no. Non e' automatizzabile:
--      per questo la lista REALE si **legge**, non si applica.
--
--   C) Esiste una terza forma di ramo condizionale che nessuna regola
--      vede: quella che dipende da `TG_ARGV`, non dalla tabella. Un BB
--      generico parametrico puo' avere rami irraggiungibili con tutti i
--      trigger esistenti (caso `trgfn_qta_from_operativa`, `20260804-52`):
--      per deciderlo bisogna leggere gli argomenti dei trigger, non le
--      loro tabelle.
--
--   E una che il controllo non trova per costruzione: un riferimento che
--   si risolve verso la cosa **sbagliata** (`fn_admin_merge_stradario`
--   scriveva comune_id in colonne via_id_*, `20260804-60`). La semantica
--   non si compila.
-- ------------------------------------------------------------

-- ⚠️ v3 — la misura NON e' piu' definita qui.
--    Vive nel DB come `dbops.fn_check_funzioni_riferimenti_morti()`
--    (changeSet `20260804-62`), perche' la chiamano in due: questo script
--    e il pgTAP `db/pgtap/dbops/test-riferimenti-morti-v1.sql`. Due copie
--    della stessa classificazione sono due copie che prima o poi
--    divergono, e un presidio che diverge dal suo strumento mente in
--    silenzio.
--    Le REGOLE e i loro limiti restano documentati qui sopra: e' il posto
--    dove si va a leggere prima di fidarsi di un'etichetta.

\pset pager off

-- ⚠️ Si materializza UNA VOLTA: la funzione valida ~500 funzioni una per
-- una, interrogarla tre volte triplicherebbe il lavoro per niente.
CREATE TEMP TABLE misura AS SELECT * FROM dbops.fn_check_funzioni_riferimenti_morti();

-- 1) Il conto per classe: la scala del problema, senza rumore.
SELECT classe, count(*) AS righe, count(DISTINCT schema_nome||'.'||funzione) AS funzioni
  FROM misura GROUP BY classe ORDER BY 1;

-- 1-bis) 🔴 LE FUNZIONI CHE NON SI SONO POTUTE CONTROLLARE.
--    Da leggere PRIMA della (2): se qui c'e' qualcosa, plpgsql_check ha
--    sollevato invece di rispondere, e di quelle funzioni non si sa niente —
--    quindi la (2) e' incompleta e non lo dice.
-- ⛔ Non sono difetti. Il 2026-09-10 questa classe non esisteva e quelle righe
--    finivano in REALE: 779 su 780 funzioni, con un registro del debito di due
--    voci. Se il conto qui e' grosso, il sospetto e' la VERSIONE di
--    plpgsql_check contro quella di PostgreSQL, non il codice del progetto.
--    Brief: brief-db-un-destinatario-per-i-presidi §9.3.
SELECT schema_nome, funzione, argomenti, esito
  FROM misura WHERE classe = 'NON_MISURATO'
 ORDER BY schema_nome, funzione;

-- 2) SOLO i difetti veri, che sono la lista di lavoro.
SELECT schema_nome, funzione, argomenti, esito
  FROM misura WHERE classe IN ('REALE', 'ORFANA')
 ORDER BY classe, schema_nome, funzione;

-- 3) I falsi positivi, per controllarli a campione invece di fidarsi
--    della classificazione.
SELECT classe, schema_nome, funzione, esito
  FROM misura WHERE classe LIKE 'FP\_%'
 ORDER BY classe, schema_nome, funzione;

-- ------------------------------------------------------------
-- 4) SECONDA MISURA — riferimenti morti scritti in un DATO
--
-- ⚠️ plpgsql_check compila i CORPI. Un riferimento a una tabella scritto
--    come stringa in una tabella di configurazione gli e' invisibile: nel
--    corpo che lo consuma compare solo come parametro, e nessuna analisi
--    statica del codice puo' arrivarci.
--
--    Non e' teoria. Il 2026-08-04 questa misura ha trovato la riga
--    `lotti_attivita` di config.sistema_codici, che puntava a
--    `vendite.attivita_fatturabili_lotti` — droppata cinque mesi prima,
--    nello stesso `DROP … CASCADE` da cui e' nato tutto questo cantiere.
--    Le funzioni erano state trovate al primo giro; la riga di
--    configurazione no, ed era la stessa morte.
--    (Rimossa da `20260804-50`.)
--
--    Le colonne sono quelle che nominano una relazione per stringa: se ne
--    aggiungono altre, si estende questa UNION. Il criterio per entrarci
--    e' semplice — una colonna che contiene un nome di tabella e che
--    nessuna FK protegge.
-- ------------------------------------------------------------
SELECT 'config.sistema_codici' AS tabella,
       sc.id::text             AS riga,
       sc.codice_interno       AS chiave,
       sc.schema_tabella || '.' || sc.nome_tabella AS riferimento_morto
  FROM config.sistema_codici sc
 WHERE sc.nome_tabella IS NOT NULL
   AND to_regclass(sc.schema_tabella || '.' || sc.nome_tabella) IS NULL
 ORDER BY 1, 2;
