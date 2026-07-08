# Analisi e piano di fix — gestione transazioni backend

> Stato: **analisi + piano** (nessun codice ancora scritto)
> Data: 2026-07-07
> Ambito: `backend/apps/*` (service + repository + view) e `db/changelog` per le funzioni madre
> Branch coinvolti: `dev/db-tid` (funzioni DB + pgTAP), `dev/backend-tid` (semplificazione service)

---

## 1. Il problema in generale

L'architettura del progetto è **DB-first**: la logica di business vive nelle funzioni e nei
trigger PostgreSQL, mentre Django orchestra e i service Python compongono le operazioni.
Questa scelta è solida, ma introduce un rischio specifico e ben noto: **la gestione delle
transazioni quando il Python chiama più scritture in sequenza.**

Lo scenario del rischio, in una frase:

> il service esegue `scrittura1()`, poi `scrittura2()`. Se la seconda fallisce, la prima è
> **già stata committata** → resta uno stato parziale (dati sporchi) impossibile da riconciliare.

### Perché succede proprio qui

Django in questo progetto gira in **autocommit**: nel blocco `DATABASES["default"]`
([settings.py](../../../backend/zeroerp_backend/settings.py)) **non** è impostato
`ATOMIC_REQUESTS`. Quindi ogni `cursor.execute` committa da solo, a meno che non sia
racchiuso in un `transaction.atomic()` esplicito. L'atomicità è quindi **opt-in per metodo**,
affidata alla disciplina di chi scrive il codice, **non garantita dall'infrastruttura**.

Le base view (`DomainAPIView`, `AdminAPIView`, ...) gestiscono solo auth e permessi: **non
aprono transazioni**. La regola dichiarata in [api.md](../api.md) («ogni endpoint POST è
un'unità di lavoro eseguita in un'unica transazione») è quindi una **convenzione applicata a
mano nei service**, non un vincolo strutturale.

### La difesa forte già presente: la "funzione madre" DB

Dove il progetto fa la cosa giusta, la composizione di più scritture **vive dentro una singola
funzione PL/pgSQL** invocata con una sola `SELECT`. Esempi: `anagrafiche.fn_crea_operatore_v2`
(chiama in sequenza 4 figlie), `vendite.fn_push_preventivo_a_ordine`,
`pratiche.fn_genera_pratica_da_flusso`.

Una sola `SELECT fn_madre(...)` su connessione autocommit è **atomica per costruzione**:
PostgreSQL avvolge l'intera statement in una transazione implicita, e **qualsiasi eccezione non
gestita dentro la funzione annulla l'intero effetto** — su tutte le tabelle e tutti gli schemi
toccati. Non serve scrivere blocchi `BEGIN ... EXCEPTION` per ottenere l'all-or-nothing: è il
comportamento di default. I blocchi `EXCEPTION` servono solo per *catturare/tradurre* un errore
o creare un savepoint di recupero parziale.

I finding di questa analisi sono, nella maggior parte, **orchestrazioni "sfuggite" in Python**
invece di stare nella funzione madre. Il piano di fix le riporta sul binario canonico.

---

## 2. Perché `ATOMIC_REQUESTS` NON è la rete giusta in questo codebase

`ATOMIC_REQUESTS = True` sembra la rete globale ideale (avvolge ogni request in una
transazione), ma **qui non funziona** per un dettaglio concreto:

`handle_post_json` — l'helper obbligatorio per **tutti** i POST
([endpoint_helpers.py:147-160](../../../backend/apps/core/api/endpoint_helpers.py)) —
**cattura ogni eccezione e restituisce una `Response`, senza rilanciarla:**

```python
except Exception as exc:
    ...
    return exception_to_error_response(exc)   # ritorna, NON rilancia
```

Django fa rollback con `ATOMIC_REQUESTS` **solo se l'eccezione esce dalla view**. Sui POST non
esce mai. Conseguenze:

- **Errore logico (guard/`ServiceError`) dopo una scrittura riuscita**: viene catturato →
  `Response` → **la transazione committa il parziale**. La rete è inefficace proprio sui casi
  che ci interessano.
- **Errore DB (`IntegrityError`)**: la connessione va in `needs_rollback`; a fine atomic Django
  forza il rollback **ma solleva `TransactionManagementError`** → il 4xx strutturato diventa
  **500**. Rompe il contratto d'errore.

Rendere `ATOMIC_REQUESTS` efficace richiederebbe di rifattorizzare `handle_post_json` perché
**rilanci** (lasciando che `ApiExceptionMiddleware` formatti la risposta) **e** spostare il
`mark_failed` dell'idempotency fuori dalla transazione che rolla (altrimenti il segno "failed"
sparisce nel rollback). Blast radius alto, e comunque le saghe (email/SMTP) resterebbero da
marcare `@transaction.non_atomic_requests` a mano.

### La rete scelta (coerente con DB-first)

| Rete | Efficacia | Rischio | Su-asse DB-first |
|---|---|---|---|
| **Regola "una azione = una `SELECT fn_()`"** | Alta: l'atomicità è *nella statement*, immune al problema di `handle_post_json` | Nullo | ✅ |
| **Guardrail automatico (test/CI)** che fallisce se un service compone 2+ scritture senza atomic | Alta sul *prossimo* caso, costo minimo | Nullo | ✅ |
| `ATOMIC_REQUESTS` | Teoricamente massima, ma qui va in conflitto con l'error-contract e le saghe | Alto | ❌ (rete Python, non DB) |

**Decisione:** funzione madre come regola + guardrail-test. `ATOMIC_REQUESTS` scartato.

---

## 2-bis. Vincoli invarianti da NON rompere

Il fix transazionale **non deve regredire l'RLS operatori** già attiva.

- **Le funzioni madre (Classe A) sono `SECURITY INVOKER`** (default PL/pgSQL) — **mai
  `SECURITY DEFINER`** salvo necessità deliberata e motivata. Girano come il ruolo chiamante,
  quindi RLS e scope emittente (le 5 GUC di sessione `app.*`, session-scoped) si valutano
  **identici** a come li valuta oggi il Python: stessa connessione, stesso ruolo, stessi filtri.
  Spostare le scritture dentro una fn madre `SECURITY INVOKER` **non cambia** chi vede/scrive cosa.
- **Le view non si toccano.** I fix transazionali agiscono su service/repository e su funzioni di
  scrittura; le viste `vw_*` con `(security_invoker = on)` (es.
  `vw_dash_fatturazione_*`, `vw_dash_competenza_*`, `vw_dash_backlog_*`) restano invariate. Nessun
  changeSet di questo piano deve alterare `security_invoker` sulle viste.
- **GUC session-scoped preservate.** `JwtAuditAuthentication` imposta le GUC con
  `set_config(..., is_local=false)` (session-scoped, non `SET LOCAL`) → sopravvivono a qualunque
  `transaction.atomic()`/savepoint introdotto. Nessuna delle modifiche deve passare a `SET LOCAL`.
- **Ruoli `BYPASSRLS`** (migrazioni, job batch owner) restano esenti come oggi: i fix non devono
  spostare percorsi web su ruoli batch né viceversa.

Checklist per ogni funzione madre: dichiarare esplicitamente `SECURITY INVOKER`, verificare che
le policy RLS delle tabelle scritte ammettano l'operazione per l'emittente in scope, e coprire con
pgTAP anche il caso "connessione senza GUC → 0 righe / write negata" (fail-closed).

---

## 3. Lista dei problemi trovati

Criterio di finding: **un singolo metodo Python** che esegue **2+ scritture con side-effect**
(INSERT/UPDATE/DELETE, o `SELECT fn_` di mutazione, o 2+ chiamate a metodi write del repo)
**senza** che tutte siano avvolte in **un solo** `transaction.atomic()`.

**17 finding reali** + 8 fragilità "mitigate solo dal caller" + alcuni dubbi latenti.
Distribuzione: `vendite` è l'epicentro; `anagrafiche` ha il bug capostipite + 3 minori; `core`
e `portale` un caso "saga" ciascuno; `documenti / ui / pratiche / catalogo / config /
amm_software` sono puliti.

### 🔴 Tier 1 — stato parziale su entità di dominio reali (alto impatto)

| # | Metodo | Scenario di dati sporchi |
|---|---|---|
| 1 | `anagrafiche/services/clienti_service.py:99` `update_cliente` | categoria BA committata, poi UPDATE cliente fallisce → 2 entità disallineate |
| 2 | `vendite/services/contratti_service.py:650` `create_contratto` | contratto committato + numero consumato, poi `create_utility` fallisce → contratto orfano |
| 3 | `vendite/services/preventivi_service.py:2004` `genera_pratica` | `crea_pratica` committa (è `@atomic` a sé), poi `link_pratica` fallisce → pratica orfana |
| 4 | `vendite/services/ordini_service.py:992` `push_a_commessa` | commesse committate + ordine EVASO, poi step pratica non chiuso → pratica non riconciliabile |
| 5 | `vendite/services/preventivi_service.py:1769` `push_a_commessa` | push committato, poi aggancio pratica fallisce → commessa-servizi orfana |
| 6 | `vendite/services/contratti_service.py:1450` `update_riga` (L3) | pratica approvazione committata, poi UPDATE riga fallisce → pratica orfana |
| 7 | `vendite/services/contratti_service.py:1203` `create_riga` (L3) | pratica L3 fuori dall'atomic → orfana se il CRUD rolla |
| 8 | `vendite/services/offerte_service.py:921` `crea_eccezione` (L3) | pratica L3 committata, eccezione fallisce → orfana |
| 9 | `vendite/services/offerte_service.py:1062` `aggiorna_eccezione` (L3) | idem |
| 10 | `vendite/services/ordini_service.py:444` `crea_ordine_da_preventivo` | ordine creato, poi transizione preventivo→EVASO salta su errore non-DB → preventivo ACCETTATO ma merce già su ordine |

### 🟠 Tier 2 — impatto contenuto (batch tracking / registro dedup)

| # | Metodo | Scenario |
|---|---|---|
| 11 | `vendite/services/commesse_source_handlers.py:387` `_process_rows` (batch) | commesse+link committati per-riga, poi upsert attività fallisce → commesse senza attività |
| 12 | `vendite/services/commesse_push_orchestrator.py:148` `_run_locked` (batch) | log run non scritto → run non tracciabile, retry doppio |
| 13 | `anagrafiche/services/geo_service.py:301` `create_indirizzo` | righe stradario registro orfane se il dettaglio fallisce (dedup, non corruzione) |
| 14 | `anagrafiche/services/conti_bancari_service.py:74` `create_conto_soggetto` | IBAN registro orfano se il legame fallisce |
| 15 | `anagrafiche/services/conti_bancari_service.py:171` `create_conto_ruolo` | idem #14 |

### ⚫ Categoria a parte — saghe con side-effect esterno (NON risolvibili con `atomic()`)

| # | Metodo | Scenario |
|---|---|---|
| 16 | `core/services/email_outbox_service.py:124` `confirm_and_send` | dopo l'invio SMTP, `copy_allegati_to_log` fallisce → outbox resta `READY` fantasma |
| 17 | `portale/services/invito_portale_service.py:221` `reinvia_invito_*` | invalida i token vecchi, poi la ri-emissione fallisce → utente senza token validi |

### 🟡 Fragilità strutturali (non-bug oggi, garanzia nel caller)

8 metodi in `vendite` (`emetti`, `_crea_testata_ordine_da_origine`, `init_componenti_riga`,
`upsert_bundle_componenti`, pipeline, ecc.) sono multi-write **senza atomic proprio**, protetti
solo perché *ogni caller attuale* li avvolge. Rischio latente su nuovi caller.

Due trappole di leggibilità da correggere:
- `_db_errors` in `vendite/services/contratti_service.py:491` *sembra* un atomic, è solo un
  mapper di eccezioni.
- Il docstring di `upsert_bundle_componenti` (listini) dichiara "in una transazione atomica"
  pur non avendone una.

Dubbi latenti: `pratiche_service.completa_step_pratica`, `assegna_pratica`, `assegna_flusso`
(single-write oggi, fragili a una companion-write futura). Presidiati dal guardrail-test.

---

## 4. Piano di fix

Quattro classi di fix. Per ogni classe, gli step **DB** e gli step **BE** sono separati.

### Classe A — Funzione madre DB (una `SELECT`)

Finding: **#1, #2, #3, #4, #5, #10**. Orchestrazioni cross-dominio che già chiamano `fn_`
figlie in sequenza → si fondono in una funzione madre.

**Step lato DB (`dev/db-tid`)**

| # | Funzione madre proposta | Assorbe |
|---|---|---|
| 1 | `anagrafiche.fn_update_cliente(cliente_id, ba_categoria_id, campi_cliente)` | UPDATE billing_account + UPDATE clienti |
| 2 | `vendite.fn_create_contratto(testata, utility?)` | numero (`fn_generate_codice`) + INSERT contratto + INSERT utility opzionale |
| 3 | `vendite.fn_genera_pratica_da_preventivo(...)` | fn figlia `crea_pratica` + INSERT `pratiche_sorgenti` (link) |
| 4 | `vendite.fn_push_ordine_a_commessa(...)` | `pr_run_commesse_push_one` + `update_stato EVASO` + chiusura step pratica |
| 5 | `vendite.fn_push_preventivo_a_commessa(...)` | push + transizione EVASO + aggancio pratica-servizi |
| 10 | estendere `vendite.fn_push_preventivo_a_ordine` | inglobare la transizione preventivo→EVASO (oggi separata in Python) |

Per ogni funzione madre:
1. Scrivere il changeSet Liquibase in `db/changelog/.../20_code/<schema>/` (naming `fn_*`,
   `logicalFilePath`, numerazione globale per data).
2. Scrivere il test **pgTAP** che verifica sia il caso felice sia il rollback totale su
   fallimento di una figlia.
3. Rigenerare la doc auto-gen dbzero (lato Tid, non a mano).

**Step lato BE (`dev/backend-tid`)**

1. Sostituire nel service le 2+ chiamate separate con **una sola** `SELECT fn_madre(...)` nel
   repository.
2. Rimuovere l'eventuale logica di orchestrazione Python ora spostata nel DB.
3. Aggiornare/creare i test service (mock repository) e lo smoke-test curl.

### Classe B — Riposiziona l'atomic (nessuna fn nuova)

Finding: **#6, #7, #8, #9** (cluster gate pricing L3 in contratti/offerte).

Il gate che crea la pratica di approvazione oggi è invocato **prima** del `transaction.atomic()`
che avvolge il CRUD. In **preventivi** lo stesso gate è già *dentro* l'atomic → è il modello
corretto da replicare.

**Step lato BE (`dev/backend-tid`)** — nessun lavoro DB

1. Spostare la chiamata al gate-L3 **dentro** lo stesso `with transaction.atomic()` del CRUD
   riga/eccezione (l'atomic annidato della fn pratica diventa un savepoint, comportamento
   corretto).
2. Aggiornare i test service per coprire il fallimento del CRUD dopo il gate (verifica: nessuna
   pratica orfana).

> Da valutare leggendo il gate: se risulta **regola di dominio** e non orchestrazione, promuoverlo
> a funzione madre DB (Classe A) invece del semplice riposizionamento.

### Classe C — Saga / Outbox (NON atomic, NON madre)

Finding: **#16, #17**. C'è un invio email in mezzo: una transazione DB non può contenere un
side-effect esterno.

**#16 `email_outbox.confirm_and_send`** — Step lato BE

1. Commit deliberato dello stato `READY` **prima** dell'invio SMTP.
2. Invio SMTP.
3. Step DB **post-invio** (`update_log_outbox_link` + `copy_allegati_to_log` +
   `update_outbox_stato SENT`) raggruppati in **un** `transaction.atomic()` separato.
4. Job/endpoint di riconciliazione per gli outbox rimasti `READY` (bozze fantasma).

**#17 `reinvia_invito_*`** — Step lato BE

1. Racchiudere le **due fasi DB** (invalida token vecchi + ri-emette identità/token) in **un**
   `transaction.atomic()`.
2. L'invio email resta **fuori**, best-effort (già gestito come recuperabile).

### Classe D — Basso valore (assorbi o lascia; priorità bassa)

Finding: **#11, #12** (batch commesse), **#13, #14, #15** (registro get-or-create).

**Step lato BE**

- #11/#12: avvolgere loop commesse + upsert attività + log in un `atomic()` per-run, oppure
  rendere il batch idempotente/ripartibile.
- #13/#14/#15: `atomic()` leggero sul metodo. *In alternativa* (lato DB) assorbire il
  `get_or_create` registro dentro la fn figlia. L'orfano è una riga di dedup riutilizzabile,
  non corruzione → priorità bassa.

### Igiene (non-bug)

- Rinominare/chiarire `_db_errors` (contratti) — non è un atomic.
- Correggere il docstring falso di `upsert_bundle_componenti` (listini).
- Nessun fix immediato sugli 8 metodi "mitigati dal caller" e sui dubbi latenti: li presidia il
  guardrail-test.

### Rete di prevenzione (trasversale)

**Step lato BE**

1. Adottare la regola esplicita: **"una azione di dominio = una sola `SELECT fn_()`"**.
2. Aggiungere un **guardrail-test** (o check CI) che scandaglia i service e **fallisce** se un
   metodo compone 2+ scritture (2+ chiamate repo write, o `cursor.execute` multipli con
   side-effect) senza `transaction.atomic()`.

`ATOMIC_REQUESTS` **non** entra nel piano (vedi §2).

---

## 5. Sequenza consigliata

1. **Pilota** su un finding di Classe A — proposto **#3 `genera_pratica`** (cross-dominio
   vendite→pratiche, orfano netto) oppure **#1 `update_cliente`** (il più isolato). Fissa il
   template (fn madre + pgTAP + semplificazione BE) da replicare.
2. Restanti Classe A.
3. Classe B (solo BE, veloce e ripetitivo).
4. Classe C (saghe, attenzione al pattern outbox).
5. Guardrail-test.
6. Classe D + igiene.

> Nota workflow: le funzioni madre + pgTAP sono lavoro DB su `dev/db-tid`; le semplificazioni
> service su `dev/backend-tid`. È un intervento a due branch. Nessuna modifica/commit senza
> "procedi" esplicito.
