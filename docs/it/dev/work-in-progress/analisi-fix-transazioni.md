# Analisi e piano di fix — gestione transazioni backend

> Stato: **BE completo + guardrail attivo** — Classi A/B/C/D + rete di prevenzione (2026-07-08).
> Residui: riconciliazione outbox #16 (follow-up), smoke E2E #3 (§6.3), guardrail v2 service-level (§7).
> Data: 2026-07-07 (piano) · aggiornato 2026-07-08 (BE)
> Ambito: `backend/apps/*` (service + repository + view) e `db/changelog` per le funzioni madre
> Branch coinvolti: `dev/db-tid` (funzioni DB + pgTAP), `dev/backend-tid` (semplificazione service)
>
> **Avanzamento fix — stato al 2026-07-08 (BE non ancora committato su `dev/backend-tid`):**
>
> | # | Metodo | Classe | DB | BE | Smoke E2E |
> |---|---|---|---|---|---|
> | 1 | `update_cliente` | A | ✅ | ✅ | ✅ `smoke-test-clienti.sh` (0..12) |
> | 2 | `create_contratto` | A | ✅ | ✅ | ✅ `smoke-test-contratti-addebito-standard.sh` (numero da fn) |
> | 3 | `genera_pratica` | A | ✅ | ✅ | ⬜ TODO §6.3 (serve fixture preventivo ACCETTATO) |
> | 10 | `crea_ordine_da_preventivo` | A | ✅ | ✅ | ✅ `smoke-test-preventivi-smistamento-ordine.sh` |
> | 4 | `push_a_commessa` (ordini) | B | — | ✅ | (happy-path coperto; atomicità = reasoning) |
> | 5 | `push_a_commessa` (preventivi) | B | — | ✅ | (idem) |
> | 6 | `update_riga` L3 (contratti) | B | — | ✅ | — |
> | 7 | `create_riga` L3 (contratti) | B | — | ✅ | — |
> | 8 | `crea_eccezione` L3 (offerte) | B | — | ✅ | — |
> | 9 | `aggiorna_eccezione` L3 (offerte) | B | — | ✅ | — |
> | 13 | `create_indirizzo` (geo) | D | ✅ | ✅ | — |
> | 14 | `create_conto_soggetto` | D | — | ✅ | — |
> | 15 | `create_conto_ruolo` | D | — | ✅ | — |
> | 11 | `_process_rows` (batch) | D | — | ⏸️ già mitigato | — |
> | 12 | `_run_locked` (batch) | D | — | ⏸️ già mitigato | — |
> | 16 | `confirm_and_send` (outbox) | C | — | ✅ (core) | riconciliazione = follow-up |
> | 17 | `reinvia_invito_*` (saga, cliente+fornitore+**shop**) | C | — | ✅ | — |
> | igiene | `_db_errors`→`_map_db_errors` + `upsert_bundle_componenti` atomic | — | — | ✅ | — |
> | guardrail | test AST anti-regressione (§7) + 4 hardening repo | — | — | ✅ | gira senza DB (CI) |
>
> **Dettagli DB (funzioni madre create):** `anagrafiche.fn_update_cliente` (`20260707-11`),
> `vendite.fn_create_contratto` (`20260707-12`, ritorna `contratto_id`+`numero`),
> `pratiche.fn_crea_pratica` (`20260707-13`, figlia condivisa) + `vendite.fn_genera_pratica_da_preventivo`
> (`20260707-14`), `vendite.fn_push_preventivo_a_ordine` estesa a 5 param con sezione EVASO + `p_flusso_id`
> (`20260708-01`), `anagrafiche.fn_create_indirizzo` (`20260708-02`). pgTAP: 20/20, 9/9, 7/7, 9/9, 6/6.
>
> **Note BE chiave:**
> - **#2**: il numero viene da `fn_generate_codice` (sequence, non fa rollback) → un fallimento lascia
>   un gap di numerazione innocuo; il fix elimina l'orfano, non il gap (che c'era già).
> - **#4/#5** (decisione Tid 2026-07-08): **rollback totale** — un fallimento dell'aggancio-pratica
>   rolla l'intero push (idempotente/ri-eseguibile). La transizione EVASO resta best-effort ma su
>   **savepoint dedicato** (swallow di `DatabaseError` dentro l'atomic esterno lo corromperebbe).
> - **#10**: `p_flusso_id` resta dormiente — `push_a_ordine` ha un solo caller (standalone,
>   `pratica_id=None`); nessun caller pratica-driven da valorizzare oggi.
> - **#16**: fix core = 3 write post-invio in un atomic; la **riconciliazione** dei READY fantasma
>   è follow-up e va progettata per NON ri-inviare (idempotente, non re-send).

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

## 2-ter. Criterio di scelta: funzione madre DB *vs* `transaction.atomic()` Django

L'atomicità non è "sempre in DB" né "sempre in Django": si decide **per-operazione**, non
per-dominio. La domanda unica da porsi:

> **L'operazione compone SOLO scritture/funzioni DB, senza un passo che è per-forza Python?**
> (advisory lock, dispatch a handler Python, invio email/chiamata esterna, control-flow
> applicativo complesso)

| Risposta | Meccanismo | Perché |
|---|---|---|
| **SÌ** — tutto pure-DB componibile | **Funzione madre DB** (una `SELECT fn_()`) | Atomicità *per costruzione*, garantita a qualunque chiamante, DB-first pura. Immune alla disciplina del BE. Es. #1/#2/#3/#10. |
| **NO** — serve orchestrazione Python | **`with transaction.atomic()`** nel service | L'orchestrazione Python resta dov'è; l'atomic lega i pezzi DB + Python. Es. #4/#5, Classe B. |
| C'è un **side-effect esterno** (SMTP) | **Outbox/saga**, mai atomic | Una transazione DB non contiene un invio email. Es. #16/#17. |

**Il lato Django NON è un ripiego — tre punti:**

1. **L'architettura lo prevede.** [api.md](../api.md) assegna al *service layer* «orchestrazione,
   **transazioni**, regole Python». Il coordinamento transazionale è di casa in Django; la madre DB
   è un *rafforzamento* per i casi pure-DB, non l'unico posto legittimo.
2. **Non viola il DB-first.** DB-first riguarda *dove vivono le regole* (vincoli, macchine a stati,
   guard → DB); il *confine transazionale* è coordinamento di caso d'uso. Il DB possiede le regole,
   Django dichiara l'unità di lavoro. Convivono.
3. **`transaction.atomic()` esplicito è SICURO** (a differenza di `ATOMIC_REQUESTS`, §2). Il rollback
   avviene al confine del blocco `atomic` (nel suo `__exit__`), *prima* che `handle_post_json`
   catturi l'eccezione → immune alla trappola dell'error-contract. È un attrezzo di prima classe.

**Domini con entrambe le nature (es. pratiche):** le operazioni pure-dato (crea pratica, link
sorgente, chiudi flusso singolo) → **madre DB** (`pratiche.fn_crea_pratica`); il *motore flussi* con
**dispatch a handler** ([[reference_binding_handler_flusso_attivo_false]]), advisory lock e
control-flow di step → **`transaction.atomic()` Django** (un handler Python non è chiamabile da una
fn DB: lì la transazione DEVE spanare il BE). I due meccanismi convivono nello stesso dominio.

**Il guardrail (§2) è agnostico rispetto al meccanismo:** *"una azione = una unità atomica"*, che
l'unità sia una `SELECT fn_madre()` o un `with transaction.atomic()`. È lì che si previene il
prossimo bug, non nella scelta DB-vs-Django.

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
| 1 ✅ | `anagrafiche/services/clienti_service.py:99` `update_cliente` | categoria BA committata, poi UPDATE cliente fallisce → 2 entità disallineate — **RISOLTO** (fn madre + BE) |
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

Finding: **#1, #2, #3, #10**. Orchestrazioni cross-dominio che già chiamano `fn_`
figlie in sequenza → si fondono in una funzione madre.

> **Riclassifica #4/#5 → Classe B (2026-07-07, analisi in corso).** All'implementazione è emerso
> che #4 (`push_a_commessa` ordini) e #5 (`push_a_commessa` preventivi) **non** hanno un confine
> madre-DB pulito: il push è l'orchestratore Python `pr_run_commesse_push_one` (già atomico —
> advisory lock, handler, log, ponte emittibilità) e la chiusura-step è anch'essa orchestrazione
> Python. Una madre DB dovrebbe **reimplementare due orchestratori in PL/pgSQL** (alto rischio +
> divergenza), e comunque non coprirebbe il push. Fix corretto = **`transaction.atomic()` in Python**
> attorno a push + post-write (l'atomic interno del push diventa savepoint). Spostati in Classe B.
> Nota: #4 **non crea** un link `pratiche_sorgenti` COLLEGATO (usa `commesse_sorgenti` + risolve un
> link esistente) → la decisione D-B su `flusso_id` **non** lo riguarda; riguarda #5 (link
> commessa-servizi) e #10 (link ordine).

**Step lato DB (`dev/db-tid`)**

| # | Funzione madre proposta | Assorbe |
|---|---|---|
| 1 ✅ | `anagrafiche.fn_update_cliente(p_cliente_id, p_ba_categoria_cliente_id, p_cliente_fields jsonb) RETURNS TABLE` — **FATTO** (migr. `20260707-11`, pgTAP 20/20) | UPDATE billing_account + UPDATE clienti (delta JSONB, SECURITY INVOKER) |
| 2 🟦 | `vendite.fn_create_contratto(p_testata jsonb, p_utility jsonb) RETURNS TABLE(contratto_id, numero)` — **DB ESEGUITO** (migr. `20260707-12` applicata, pgTAP 9/9; BE pendente) | numero (`fn_generate_codice`) + INSERT contratto + INSERT utility opzionale (dinamici, SECURITY INVOKER) |
| 3 🟦 | `vendite.fn_genera_pratica_da_preventivo(...) RETURNS TABLE(pratica_id)` — **DB ESEGUITO** (migr. `20260707-13/14` applicate, pgTAP 7/7; BE pendente) | figlia **condivisa** `pratiche.fn_crea_pratica` + INSERT `pratiche_sorgenti` ROOT (SECURITY INVOKER) |
| ~~4~~ → B | *(riclassificato Classe B — orchestratore Python, vedi nota sopra)* | — |
| ~~5~~ → B | *(riclassificato Classe B — orchestratore Python; il `flusso_id` D-B sul link commessa-servizi si gestisce nel wrap BE)* | — |
| 10 🟦 | `vendite.fn_push_preventivo_a_ordine(...)` estesa a 5 param — **DB ESEGUITO** (migr. `20260708-01` applicata, pgTAP 9/9; BE pendente) | +sezione EVASO atomica (bi-ramo) + `p_flusso_id` sul link COLLEGATO (D-B) |

> ⚠️ **Coordinamento con [brief-design-guida-rollout-multidominio](brief-design-guida-rollout-multidominio.md)
> (decisione D-B / G-est.2).** I finding **#4, #5, #10** generano un documento a valle e creano il link
> `pratiche_sorgenti` con `ruolo_link='COLLEGATO'`. Oggi quell'INSERT **non valorizza `flusso_id`**
> (`fn_push_preventivo_a_ordine` inserisce `(pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link)` e
> basta). Il roll-out multi-dominio ha deciso (D-B) di **valorizzare `flusso_id` sul COLLEGATO alla
> generazione**. Poiché queste madri riscrivono *proprio* quell'INSERT, il `flusso_id` va aggiunto **qui,
> contestualmente**, non con un changeset separato pochi giorni dopo. Conseguenze pratiche mentre si
> sviluppa **#10** (madre DB) e **#5** (wrap BE):
>
> - **Progettare la firma della madre per ricevere/risolvere il `flusso_id`** (il flusso dello step
>   generatore — es. `CONFERMA_ORDINE` per #10). Oggi le push ricevono `p_pratica_id` ma non il
>   flusso: aggiungerlo dopo = seconda modifica di firma → `DROP FUNCTION` obbligatorio (regola
>   `RETURNS TABLE`). Farla giusta ora.
> - **#3 e #4 esclusi**: #3 crea il link **ROOT** (`flusso_id` già gestito dal pilota GUIDA); #4 **non
>   crea** alcun link `pratiche_sorgenti` (ne risolve uno esistente). Non applicare D-B lì.
> - **Invarianti già allineati**: entrambi i piani impongono `SECURITY INVOKER` (§2-bis) e la lezione
>   GRANT-a-`zeroerp_app` + documento-sovrano del pilota. Nessuna divergenza da sanare.

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

### Classe B — Riposiziona/avvolgi l'atomic in Python (nessuna fn nuova)

Finding: **#4, #5** (push a commessa, orchestratore Python) + **#6, #7, #8, #9** (cluster gate
pricing L3 in contratti/offerte).

**#4/#5 — wrap `transaction.atomic()` attorno a push + post-write.** Il push
(`pr_run_commesse_push_one`) è già atomico; avvolgere push + `update_stato(EVASO)` +
chiusura-step (e, per #5, l'aggancio pratica-servizi con `flusso_id` D-B) in **un solo**
`transaction.atomic()` in `push_a_commessa`: l'atomic interno del push diventa savepoint, le parti
diventano un'unità. Togliere il `try/except` best-effort attorno a `update_stato`.

**#6/#7/#8/#9 — cluster gate pricing L3 in contratti/offerte.**

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
- **#13 → DB FATTO (madre).** `anagrafiche.fn_create_indirizzo`
  (`20_code/anagrafiche/20260708-02-...`) fonde upsert stradario (×2) + `fn_get_or_create_indirizzo_dettaglio`
  in un'unica statement atomica; pgTAP `db/pgtap/anagrafiche/test-fn-create-indirizzo-v1.sql`
  (6/6, incl. atomicità = niente stradario orfano). BE: `geo_service.create_indirizzo` chiama la fn.
- **#14/#15 → BE one-liner (NESSUN lavoro DB, §2-ter).** In `conti_bancari_service` il metodo ha
  **già** un `with transaction.atomic()` attorno al legame: basta spostare
  `_resolve_conto_bancario(payload)` (il get_or_create IBAN) **dentro** quell'atomic. Fabbricare una
  madre DB qui sarebbe over-engineering.

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

---

## 6. Appendice — note fuori-scope emerse durante l'implementazione

Osservazioni raccolte mentre si eseguivano i fix, da **affrontare in workstream separati**
(non sono difetti del fix transazionale, non bloccano il piano).

### 6.1 🔴 Canoni RICORRENTI: nessuna serie mensile nel push commesse (da valutare)

Emerso il **2026-07-08** durante lo smoke E2E del **#2** (`smoke-test-contratti-addebito-standard.sh`).
`vendite.fn_list_contratti_da_pushare` seleziona il contratto **solo nel mese di inizio**:

```sql
AND (p_competenza_mese IS NULL
     OR date_trunc('month', COALESCE(c.valido_dal, c.data))::date = p_competenza_mese)
```

Non c'è alcun `generate_series` sui mesi di validità. Conseguenza:

- **ADDEBITO STANDARD una-tantum** → 1 sola attività: **corretto**.
- **RICORRENTE / canone periodico** (gas-energia-acqua, canoni) → servirebbe **1 attività per
  ogni mese di competenza** da `valido_dal` a `valido_al`. Oggi un contratto a canone di 12 mesi
  genera **una sola** attività di fatturazione (nel mese di inizio): **gap funzionale reale**.

Stato: **deliberatamente rinviato** (già annotato come "sviluppo rinviato, §3a" nell'header dello
smoke). È **lavoro DB** (estendere `fn_list_contratti_da_pushare` con l'espansione mensile) →
parte da un **brief al team DB** su `dev/db-tid`, non dall'agent. Ortogonale ai fix transazionali.

### 6.3 🟡 TODO in-scope — smoke E2E #3 `genera_pratica` da scrivere

Il BE del **#3** è fatto e coperto da unit test + pgTAP DB (7/7, incl. atomicità), ma **manca
uno smoke curl E2E**: nessuno smoke esistente esercita `POST /vendite/preventivi/{id}/genera-pratica/`.
Serve una fixture "preventivo **ACCETTATO**" (giro flusso pratica event-driven, cfr.
`smoke-test-pratica-preventivi-conferma.sh` che porta il preventivo ROOT ad ACCETTATO). Da
aggiungere: una tappa `genera-pratica` dopo che il preventivo è ACCETTATO, con verifica che la
pratica sia creata **e** linkata (ROOT su `pratiche_sorgenti`) — la prova E2E che la fn madre ha
fuso le due scritture. **Aperto al 2026-07-08.**

### 6.2 🟡 Smoke contratti non idempotente sull'attivazione (igiene test)

Lo stesso smoke, al ri-run, fallisce l'`/emetti/` con `E_VENDITE_CONTRATTO_OVERLAP`: un run
precedente lascia un contratto **ATTIVO** sovrapposto (stesso BA+istanza+ambito+periodo) e il
guard anti-overlap blocca l'attivazione del nuovo. La **creazione** (percorso #2) passa; è solo la
transizione DRAFT→ATTIVO a incrociare il residuo. Fix igiene: periodo/BA fresco per run o cleanup
proattivo dei contratti attivi di test (memoria `feedback_smoke_test_idempotenti`). Non è una
regressione del #2.

---

## 7. Rete di prevenzione — guardrail-test (FATTO 2026-07-08)

Implementata la rete anti-regressione della §4 ("una azione = una unità atomica").

### 7.1 Il test

`backend/apps/core/tests/test_transaction_atomicity_guardrail.py` — **analisi statica AST**
(nessun DB, gira in CI): fallisce se un metodo compone **2+ scritture DB non tutte dentro un
`transaction.atomic()`**.

- **Regola v1 (conservativa, zero-rumore):** rileva SOLO `cursor.execute(...)` con SQL di
  scrittura (`INSERT/UPDATE/DELETE` o `SELECT fn_` di mutazione). Immune ai falsi positivi da
  `dict.update()` / `create_*()` su variabili locali (che nelle prime iterazioni davano 35→23 hit
  spuri). Copre la composizione a livello **repository**.
- **Conteggio compositional:** rami `if/else` → **max** (mutuamente esclusivi, non somma →
  elimina il falso positivo `_set_super_admin_binding`); sequenziale → somma; `with ...atomic()` →
  scritture nel body protette; `_map_db_errors`/`_db_errors` **non** contano come atomic.
- **Due test:** (a) nessuna violazione fuori `ALLOWLIST`; (b) nessuna voce `ALLOWLIST` stantia
  (una voce che non è più violazione va rimossa → evita suppressioni morte).
- **`ALLOWLIST`:** 1 sola voce — `IdempotencyStore.claim_or_replay` (protocollo idempotency: il
  claim atomico è garantito dall'`INSERT ... ON CONFLICT DO NOTHING` a livello statement; un
  `atomic()` non aggiungerebbe garanzie).

### 7.2 4 fragilità reali scoperte e hardenate

Applicato al codebase, il guardrail ha trovato — oltre a `claim_or_replay` (allowlist) — **4
metodi repository con 2+ scritture sequenziali senza atomic** (la categoria "8 mitigate dal
caller" della §3). Resi **self-atomici** (`with transaction.atomic(), connection.cursor()`;
nested = savepoint se il caller ha già un atomic):

| Metodo | Scritture fuse |
|---|---|
| `anagrafiche/db/indirizzi_repository.get_or_create_stradario` | 2 upsert stradario |
| `vendite/db/commesse_repository.update_attivita_prezzo` | 2 UPDATE (era "caller gestisce transazione") |
| `vendite/db/listini_repository.clone_versione` | INSERT testata + INSERT righe |
| `vendite/db/listini_repository.delete_versione` | 3 DELETE a cascata |

### 7.3 Follow-up v2 (documentato)

Il v1 copre il livello **repository** (`cursor.execute`). La composizione a livello **service**
(2+ chiamate a metodi-write del repo senza atomic — es. il vecchio `update_cliente`) richiede
euristiche *receiver-aware* (quali attributi sono repository) per non generare rumore da
`self._build_*`/`self._validate_*`. È il naturale v2.

### 7.4 Fix da review critica (2026-07-08)

Controllo adversariale su tutte le modifiche della sessione (4 review parallele). Nucleo
transazionale confermato corretto; 4 finding corretti:

- **#17 asimmetria SHOP_CUSTOMER** (reale): `reinvia_invito_shop_customer` invalidava i token
  **fuori** dall'atomic — la stessa vulnerabilità sanata per cliente/fornitore, dimenticata sullo
  shop. Ora simmetrica su tutte e tre le vesti (regola simmetria-modello).
- **Contratti CM order**: in `create_riga`/`update_riga` invertito `transaction.atomic(), _map_db_errors`
  → `_map_db_errors, transaction.atomic()` (allineato a offerte): il rollback su errore trigger
  avviene prima del log-to-db, che altrimenti girava su connessione avvelenata e andava perso.
- **clienti "no fields"**: `E_ANAG_NOT_FOUND` (404) → `E_ANAG_VALIDAZIONE` (400) — l'esistenza è
  già provata da `get_cliente`, quindi "niente da aggiornare" è validazione, non not-found.
- **dead code**: rimossi `contratti_repository.create_contratto` + `generate_numero` (superati da
  `create_contratto_atomico`) + test obsoleti.
