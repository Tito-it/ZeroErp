# Addendum brief DB — bug `script.fn_available_actions_offerta`

> **Stato**: bug critico in produzione FE+BE. Da fixare urgente sul branch
> `dev/db-tid`.
> **Data segnalazione**: 2026-05-26 (dopo smoke utente).
> **Sorgente**: errore live durante la creazione di un'offerta commerciale.

---

## 1. Sintomo

La creazione di un'offerta commerciale (e qualsiasi GET successivo sul
dettaglio) restituisce `E_DATABASE` al client. L'offerta viene **comunque
creata** (INSERT testata + eccezioni + utility committati nella stessa
`transaction.atomic()`), ma il successivo `get_offerta` arricchito col blob
capability fallisce sulla chiamata a `script.fn_available_actions_offerta`.

Effetto downstream:

- Il FE riceve l'errore E_DATABASE e mostra il banner "Errore durante
  l'operazione database".
- Quando l'operatore riapre l'offerta dalla lista, il drawer dovrebbe
  caricarla in EDIT BOZZA (editabile), ma `get_offerta` rifallisce → il
  detail non arriva mai → drawer mostra le righe in "sola lettura" o
  cade in stato inconsistente.

## 2. Errore PostgreSQL puntuale

```text
l'operatore non esiste: jsonb ?? unknown
LINE 21: AND t.meta ?? 'action_key'
                ^
HINT: Nessun operatore trovato con nome e tipi di argomenti forniti.
CONTEXT: funzione PL/pgSQL fn_available_actions_offerta(bigint) riga 94
```

Estratto della query incriminata (interno alla fn):

```sql
SELECT COALESCE(
  jsonb_agg(
    jsonb_build_object(
      'key', t.meta->>'action_key',
      'target_state', sa.codice_interno,
      'label_key', t.meta->>'label_key',
      ...
    )
    ORDER BY sa.ordine
  ),
  '[]'::jsonb
)
FROM config.stati_doc_offerte_transizioni t
JOIN config.stati_doc_offerte sa ON sa.id = t.stato_a_id
WHERE t.stato_da_id = v_stato_id
  AND t.attivo IS TRUE
  AND COALESCE((t.meta->>'manuale')::boolean, true) IS TRUE
  AND t.meta ?? 'action_key'    -- ← BUG: operatore `??` non esiste in PG
  AND t.meta ?? 'label_key'     -- ← BUG: stesso
```

## 3. Causa

L'operatore `??` non esiste in PostgreSQL.

L'operatore corretto per "il JSONB ha la chiave top-level X" e' **`?`
singolo**:

| Operatore JSONB PostgreSQL | Significato |
| --- | --- |
| `jsonb ? text`  | la chiave (o stringa) **esiste** come elemento top-level |
| `jsonb ?\| text[]` | almeno una delle chiavi esiste |
| `jsonb ?& text[]` | tutte le chiavi esistono |

Il `??` letterale non esiste e PostgreSQL lo segnala come "operatore non
trovato". L'errore puo' essere dovuto a:

1. Refuso (raddoppio accidentale del `?`).
2. Tentativo di "escape" per psycopg/JDBC: in alcuni driver `?` e' usato
   come placeholder e si scappa con `??`. **Ma questo escape non si
   applica dentro il corpo di una function PL/pgSQL** consegnata via
   Liquibase: il body viene salvato letteralmente con `CREATE FUNCTION
   ... AS $$ ... $$`, nessuna sostituzione `??` → `?` avviene a runtime.
   Lo si vede chiaramente dall'errore: PostgreSQL vede `??` letterale.

## 4. Fix richiesto

Sostituire `??` con `?` (operatore JSONB "ha chiave") nella fn
`script.fn_available_actions_offerta` (migration `20260526-01`). Due
opzioni equivalenti:

**Opzione A — uso diretto dell'operatore `?`** (piu' conciso):

```sql
  AND t.meta ? 'action_key'
  AND t.meta ? 'label_key'
```

**Opzione B — uso di `?&` con array** (esplicito, leggibile):

```sql
  AND t.meta ?& ARRAY['action_key', 'label_key']
```

**Opzione C — pattern equivalente `IS NOT NULL`** (massima portabilita',
nessun dubbio di escape):

```sql
  AND (t.meta -> 'action_key') IS NOT NULL
  AND (t.meta -> 'label_key')  IS NOT NULL
```

**Raccomandazione**: Opzione C. Nessun rischio futuro di nuovi tool/driver
che provino a interpretare `?` come placeholder; semantica identica.

## 5. Suite test pgTAP — caso minimo da aggiungere

Il test che ha generato il bug NON copre il path "fn invocata su offerta
in BOZZA con seed transizioni reale" — i 9 test esistenti devono passare
**solo se la query dentro la fn esegue senza errore SQL**. Aggiungere
almeno un test:

```sql
-- Offerta BOZZA reale -> fn ritorna jsonb non-null senza eccezioni SQL.
PREPARE check_smoke AS
  SELECT script.fn_available_actions_offerta(<id_offerta_bozza_fixture>);
SELECT lives_ok(
  'EXECUTE check_smoke',
  'fn_available_actions_offerta non solleva eccezioni SQL su BOZZA reale'
);
```

I 9 test attuali probabilmente non lo intercettano perche':

- Validano la firma + casi di shape (offerta NULL → NULL, ecc.).
- I casi BOZZA/EMESSA/ACCETTATA potrebbero usare seed di
  `stati_doc_offerte_transizioni` con `meta` mancante delle chiavi
  `action_key`/`label_key` → la `WHERE` cortocircuita prima del bug
  oppure il match e' vuoto e non viene esercitato l'operatore.

Senza un test smoke che esegua la fn su uno stato `BOZZA` con le righe
seed reali della tabella transizioni, il bug passa la suite.

## 6. Impatto BE (gia' mitigato lato applicativo)

Lato BE, il merge del blob in `OfferteService.get_offerta` viene ora
wrappato in `try/except` (commit applicativo simultaneo a questo
addendum): se la fn DB fallisce, il dettaglio viene comunque ritornato
**senza** il blob capability. Il FE cade in **modalita' readonly
conservativa** (canEditTestata=false) finche' la fn DB non e' corretta.
Risultato per l'operatore: niente piu' errore criptico E_DATABASE; vede
l'offerta ma non puo' editarla. Quando il team DB applica il fix di §4 +
la migration nuova viene caricata in dev, tutto torna a regime senza
ulteriori interventi BE/FE.

## 7. Sequenza richiesta

1. Identificare la migration `20260526-01-create-fn-available-actions-offerta-mctit.yaml`.
2. Creare migration nuova (es. `20260526-02-fix-fn-available-actions-offerta-jsonb-exists-mctit.yaml`)
   con `runOnChange: true` che ridefinisce la fn applicando il fix di §4.
   **Non modificare** la migration precedente (regola: changelog gia'
   pushati non si toccano, vedi `AGENTS.md §Liquibase v2 Workflow`).
3. Aggiungere test pgTAP smoke (§5).
4. Verifica `make db-migrate` locale.
5. Push su `dev/db-tid`.

---

*Addendum DB — fix bug operatore `??` JSONB. Pronto per applicazione su
`dev/db-tid`. Tempo stimato: 15 minuti (fix singolo operatore + 1 test
pgTAP smoke + migration runOnChange).*
