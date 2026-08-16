# Brief BE — Fan-out isolato come building block + esito parziale del pull

> **Tipo**: brief esecutivo backend (piano di sviluppo) · **Data**: 2026-08-09 ·
> **Owner**: Tid · **Branch**: `dev/backend-tid`
>
> **Stato**: ✅ **ESEGUITO** (2026-08-09) — F0..F6 tutte fatte, **2234 test verdi**.
> Consuntivo e scostamenti dal piano in **§11**; il residuo `commessa_cache`, che il
> consuntivo lasciava aperto, è stato **chiuso in giornata** su richiesta di Tid — **§12**.
>
> 🟡 **Questo doc resta APERTO come raccoglitore dell'intera linea**: gli altri tre
> documenti del cantiere sono chiusi e archiviati, e **cio' che manca vive in §13**.
> Nessun altro documento aperto: se cerchi «cosa resta», è lì.
>
> **Stato al 2026-08-10**: ✅ commit fatto e pushato · 🔴 restano le **due validazioni
> in-app** (V1 esito parziale del pull, V2 slice 3-ter) e il **build docs**.
>
> **Stato al 2026-08-16**: ✅ **build docs fatto e verde** (§13.3 — `zensical` nel
> frattempo è installato) · 🔴 restano **solo le due validazioni in-app**. Misurato
> oggi: il pull **non è mai stato lanciato dopo il fix** — nessun task run in tutta
> la pipeline dal 2026-08-03 — quindi V1 è aperta nei fatti, non solo sulla carta
> (§13.1). Per V2 mancano dei soggetti su cui provare: dettaglio in §13.2.
>
> ℹ️ **Il §14 non sposta questa riga.** È la ricognizione dei residui BE che il
> team DB aveva consegnato «fuori da questa linea»: riverificati contro il
> codice, **nessuno dei quattro richiede lavoro BE**. Non toglie né aggiunge
> nulla a «cosa resta», che è e rimane il §13. Quel che il §14 lascia sono due
> voci di *registro*, non di sviluppo (§14.4).
>
> **Origine**: [piano-residui-orchestrazione-e-cruscotti-vendite.md](../work-done/piano-residui-orchestrazione-e-cruscotti-vendite.md) §1 (R-1)
> ← [analisi-orchestrazione-vendite-simmetrie.md](../work-done/analisi-orchestrazione-vendite-simmetrie.md) §B/§B.1.
>
> **Perimetro**: solo backend Python. **Nessuna azione DB** (verificato §5.2), **nessuna
> dipendenza nuova**, nessun frontend.

---

## 1. Le due cose da fare, in una riga ciascuna

1. **Il fix** — quando il pull da commessa emette 7 commesse su 10, deve dire *«giro finito,
   3 rimaste indietro»* invece di dire *«fatto»*. Oggi dice «fatto» e al rilancio dello step
   quelle 3 vengono saltate per sempre.
2. **Il BB** — il telaio che sta intorno a quel ciclo (scopri → isola → aggrega → logga) è
   scritto tre volte a mano, in tre modi diversi. Va estratto una volta sola in
   `apps/core/services/`, adottandolo **contestualmente** in più di un sito (regola del 2).

L'ordine non è negoziabile: **prima il fix, poi l'estrazione**. Il fix cambia un
comportamento; l'estrazione deve essere a parità. Mescolarli renderebbe ambigua qualunque
regressione.

---

## 2. Ricognizione — i tre siti reali (correzione dell'analisi originale)

L'analisi di giugno accoppiava «push» e «pull». Rileggendo il codice per questo brief:
**i siti sono tre, e i due accoppiati allora non sono lo stesso livello.**

| Sito | File | Itera su | Discovery | Isolamento | Aggregazione | Log |
|---|---|---|---|---|---|---|
| **A** | `commesse_push_orchestrator.py` `_run_locked` | **handler** | `_resolve_handlers` | `try/except` — **niente savepoint** | `_compute_stato` → `COMPLETATO`/`PARZIALE`/`ERRORE` | `PUSH_STARTED`/`PUSH_COMPLETED` + `log_push_run` |
| **B** | `commesse_source_handlers.py` `BaseSourceHandler._process_rows` | **righe sorgente** | `fetch_pushable_rows` | `transaction.atomic()` per riga | contatori `created/updated/skipped` + `errors[]` su `HandlerResult` | `logger.exception` per riga |
| **C** | `pipeline_step_executor.py` `_handle_pull_attivita_da_commessa_task` | **commesse** | `list_commesse_emittibili` | `transaction.atomic()` per commessa | `errors[]` + raise **solo** se falliscono tutte | `event_log` + `PipelineErrorLogger` per item |

**Conseguenze di lettura:**

- Il **gemello vero di C è B**, non A: stessa forma esatta (lista scoperta → savepoint per
  item → conteggi/errori). A sta **un livello sopra**: itera su handler che sono *essi
  stessi* fan-out, e per questo non isola in transazione — lo fanno gli handler dentro di sé.
  A è un **aggregatore**, non un fan-out.
- ⚠️ **B ha una coda batch fuori dal ciclo** (`batch_upsert_attivita` + risoluzione id +
  esclusione delle `chiavi_fallite`). Il BB **non deve inghiottirla**: restituisce gli esiti
  per item e il chiamante fa la sua coda. Un BB che pretendesse di gestire anche il batch
  diventerebbe il ciclo di B con un altro nome.
- **Il vocabolario a tre stati esiste già** — `_compute_stato` di A produce
  `COMPLETATO`/`PARZIALE`/`ERRORE` da sempre. Il BB **non inventa una policy**: porta a C la
  terza parola che A ha già e che a C manca. È l'argomento più forte per fare entrambe le
  cose insieme.
- **C'è un quarto parente**, `QueueDrainEngine` (`core/services/coda_lavori/drain_engine.py`):
  stessa forma ma su **coda persistente** (claim, ownership, backoff, ritentativi). Vedi D-1.

---

## 3. Decisioni di disegno

Tutte chiuse con Tid il **2026-08-09**.

| # | Domanda | Stato | Scelta |
|---|---|---|---|
| **D-1** | Il fan-out converge col `QueueDrainEngine`? | ✅ **DECISA** | **NO — due astrazioni, confine dichiarato** |
| **D-2** | Il pull deve segnalare il parziale? | ✅ **DECISA** | **SÌ**, via `TaskEsitoParziale` |
| **D-3** | Il run log entra nel BB? | ✅ **DECISA** | **SÌ, come protocollo minimo opzionale** |

**D-1 — perché NON si converge.** Il drain engine possiede claim, ownership,
`run_after` con backoff esponenziale e la nozione di errore *terminale*: tutta roba che
esiste perché la coda è **durevole** e l'item **sopravvive** al run. Qui la lista è
**effimera**: la scopri, la consumi, e se qualcosa resta indietro lo ritrovi alla prossima
scoperta (che è idempotente). Farne un `QueueBackend` in-memory significa trascinare tre
concetti inutili dentro il caso semplice. La contropartita è che restano due moduli: si paga
con **una riga di doc in ciascuno** che dice quando si usa l'uno e quando l'altro (F6), e con
la voce nel catalogo BB. ⚠️ Quel confine scritto **è** il deliverable della decisione: senza,
fra sei mesi qualcuno riaprirà la stessa domanda davanti a due motori simili.

**D-2 — dettaglio esecutivo in §5.**

**D-3 — perché sta dentro, ma leggero.** Il log del run è **la parte che ci
si dimentica di replicare**: A lo fa bene (start/end + tabella dedicata), B lo fa solo con
`logger.exception`, C lo fa con `event_log` + logger di dominio. Se il BB lo lascia fuori, il
quarto chiamante lo riscriverà a modo suo e saremo al punto di partenza. Ma se lo assorbe
tutto, deve conoscere `event_log`, `commesse_push_log` e `PipelineErrorLogger` — cioè il
dominio. Via d'uscita: un **protocollo a tre metodi**, opzionale (`None` = non loggare),
implementato dai chiamanti:

```text
class FanOutRunLogger(Protocol):
    def start(self, *, totale: int) -> None: ...
    def item_failed(self, *, item, exc: Exception, indice: int) -> None: ...
    def end(self, *, esito: FanOutEsito) -> None: ...
```

Il BB sa *quando* chiamare; il chiamante sa *dove* scrivere. Nessuna dipendenza di `core`
verso `vendite`.

---

## 4. La forma proposta del BB

**File**: `backend/apps/core/services/fan_out.py` (header standard + `# Scopo:` per funzione,
come da AGENTS).

```text
ESITO = COMPLETATO | PARZIALE | ERRORE        # stesse tre parole di _compute_stato

@dataclass
class FanOutItemErrore:
    indice: int
    item: Any
    messaggio: str          # f"{type(exc).__name__}: {exc}"

@dataclass
class FanOutEsito:
    totale: int
    ok: int
    errori: list[FanOutItemErrore]
    esito: str              # COMPLETATO | PARZIALE | ERRORE

    @property
    def parziale(self) -> bool
    @property
    def tutti_falliti(self) -> bool

def run_fan_out(
    items,                          # iterabile GIA' scoperto dal chiamante
    process,                        # callable(item) -> None ; solleva per fallire
    *,
    isola_in_transazione=True,      # savepoint per item (transaction.atomic)
    run_logger=None,                # protocollo D-3, opzionale
) -> FanOutEsito
```

**Regole del contratto** (vanno nel docstring, sono la parte che si dimentica):

- La **discovery resta fuori**: il BB riceve una lista già risolta. Il chiamante conosce i
  suoi filtri di perimetro; il BB no, e non deve.
- `process` comunica il fallimento **sollevando**. Nessun valore di ritorno interpretato:
  un `False` ambiguo è il modo in cui questi telai marciscono.
- **Lista vuota → `COMPLETATO`**, non `ERRORE`. «Niente da fare» è un successo. ⚠️ Nota che
  `_compute_stato` di A oggi fa il contrario (`if not results: return "ERRORE"`) — vedi la
  trappola T-3 in §8.
- Il BB **non decide** cosa fare dell'esito: lo restituisce. È il chiamante che sceglie se
  sollevare, marcare un `task_run` o scrivere un report.
- Nessuna concorrenza, nessun retry, nessun claim: quelli stanno nel `QueueDrainEngine` (D-1).

---

## 5. Il fix del pull (Fase 1) — dettaglio

### 5.1 Comportamento

| Casistica | Oggi | Dopo |
|---|---|---|
| 10 su 10 ok | `task_run` COMPLETATO | invariato |
| 7 ok, 3 ko | `task_run` **COMPLETATO** → al rilancio **SKIP**, le 3 non si ritentano | `task_run` **ERRORE senza raise** → al rilancio **RESUME** |
| 0 su 10 ok | `raise E_PULL_COMMESSA_ALL_FAILED`, lo step si ferma | **invariato** — vedi sotto |
| lista vuota | COMPLETATO | invariato |

**Perché l'all-fail continua a sollevare** e non diventa anch'esso un parziale: se nessuna
commessa è stata emessa, proseguire con i task successivi costruirebbe un **lotto vuoto**.
Lì fermarsi è la cosa giusta. La regola diventa leggibile in una riga: *nessuno passa →
fermati · qualcuno passa e qualcuno no → prosegui ma non dichiarare chiuso · tutti passano →
chiuso*.

### 5.2 Codice errore — nessuna azione DB

Si riusa **`E_PULL_COMMESSA`**, già seedato (`config/codici_errore.csv` riga 470, policy
`DATO_ERRATO`; messaggio in `config/messaggi_errore.csv` riga 511; presente in
`error_policies_generated.py`). È esattamente il criterio applicato dallo snapshot
indirizzi, che riusa `E_INDIRIZZO_FATTURA_MANCANTE` perché è *«il motivo dominante reale del
fallimento per-fattura, non un codice sintetico nuovo»*.

→ **Niente brief al team DB, nessun prerequisito, nessuna attesa.** Se in review emergesse
la necessità di un codice dedicato, quello **sì** diventerebbe una richiesta al team DB e il
lavoro si fermerebbe lì (memoria `feedback_db_actions_passaggio_team`).

### 5.3 Forma

`_handle_pull_attivita_da_commessa_task` cambia firma di ritorno da `None` a
`TaskEsitoParziale | None` — la stessa dei due handler che già lo fanno. L'executor lo
gestisce già (`pipeline_step_executor.py` righe 362-374): **nessuna modifica al chiamante**.

`meta` del `TaskEsitoParziale` porta: `task`, `totale`, `ok`, `falliti`, e i primi N
`commessa_id` falliti (allineato al `errors[:5]` già usato nel raise all-fail).

---

## 6. Piano di sviluppo

| Fase | Contenuto | Esito atteso | Dipende da |
|---|---|---|---|
| **F0** | Conferma **D-1** e **D-3** con Tid | ✅ **FATTA** (2026-08-09): due astrazioni distinte · run logger dentro come protocollo opzionale | — |
| **F1** | **Fix pull esito parziale** + i suoi test | comportamento nuovo isolato e provato, a BB non ancora esistente | F0 ✅ |
| **F2** | **BB `run_fan_out`** in `core/services/fan_out.py` + test unitari del solo BB (nessun chiamante ancora convertito) | BB verde in isolamento | F0 ✅ |
| **F3** | **Adozione in C** (pull) — il ciclo di `_handle_pull_...` diventa una chiamata a `run_fan_out`, il `run_logger` incapsula `PipelineErrorLogger` | pull a parità di comportamento **rispetto a F1** | F1 + F2 |
| **F4** | **Adozione in B** (`_process_rows`) — solo il ciclo per-riga; la **coda batch resta fuori**, invariata | push handler a parità esatta | F2 |
| **F5** | **Valutazione di A** — l'orchestrator adotta il BB solo se `isola_in_transazione=False` gli calza senza forzature; **altrimenti resta com'è** e lo si dichiara nel docstring | decisione motivata, non adozione per simmetria | F3 + F4 |
| **F6** | Doc: catalogo BB backend + riga di confine in `fan_out.py` e in `drain_engine.py` (D-1) + aggiornamento di questo brief e chiusura di R-1 nel piano residui | R-1 chiuso | F3..F5 |

**F3 e F4 sono la regola del 2**: l'estrazione è legittima solo se in quello stesso
intervento **entrambe** vengono convertite. Se una delle due si rivelasse ostica, non si
tiene il BB con un solo chiamante — si torna indietro e si ridiscute (memoria
`feedback_regola_del_2_estrai_bb`).

**F5 è deliberatamente condizionale.** A è un livello diverso (§2): forzarlo dentro il BB per
avere «tre adozioni» sarebbe astrazione a comando. Se non calza, il risultato di F5 è **una
riga di documentazione**, non del codice.

---

## 7. Test

| Fase | Cosa si prova |
|---|---|
| F1 | pull con 3 su 10 falliti → ritorna `TaskEsitoParziale` con `E_PULL_COMMESSA` e `meta` popolata · pull con 10/10 ok → ritorna `None` · pull con 0/10 ok → solleva `E_PULL_COMMESSA_ALL_FAILED` · lista vuota → `None`, nessun errore |
| F1 | **executor**: `TaskEsitoParziale` → `fail_lotto_task_run` con codice/messaggio/meta e **nessuna eccezione propagata**; ritorno `None` → `complete_lotto_task_run`. ✅ **Rettifica 2026-08-09**: contrariamente a quanto scritto nella prima stesura di questo brief, il ramo **è già coperto** — dai test 28/29 (snapshot) e 32/33 (scadenze) di `test_pipeline_step_executor.py`. La classe non compare per nome nei test, il suo comportamento sì. Restano da scrivere i test **specifici del pull**, non quelli del meccanismo |
| F2 | `run_fan_out`: tutti ok → `COMPLETATO` · misto → `PARZIALE` con indici e messaggi giusti · tutti ko → `ERRORE` · **lista vuota → `COMPLETATO`** · `isola_in_transazione=False` non apre transazioni · `run_logger` riceve `start`/`item_failed`×N/`end` nell'ordine · un'eccezione **dentro** il run_logger non affonda il giro |
| F3/F4 | i test esistenti di `test_pipeline_step_executor.py` e `test_commesse_source_handlers.py` passano **senza modifiche di aspettativa** (a parte quelle di F1). Se un test va cambiato in F3/F4, non è un refactor: è un cambio di comportamento non dichiarato |

Regole CI: `unittest.TestCase` con mock, mai `django.test.TestCase` (nessun test deve
dichiarare un database — vedi AGENTS, il vincolo dei 3 test e2e opt-in).

---

## 8. Trappole note

- **T-1 — Il savepoint annidato.** In F4 il ciclo di B è già dentro `transaction.atomic()`
  per riga; se il chiamante avvolgesse a sua volta, si otterrebbero savepoint annidati.
  Verificare che `run_fan_out` apra **un solo** livello e che nessun chiamante lo raddoppi.
- **T-2 — La coda batch di B.** `batch_upsert_attivita` gira **dopo** il ciclo e ha una sua
  logica di errori (`chiavi_fallite` che il ponte di approvazione deve escludere, difetto
  già corretto in review il 2026-07-23). Il BB non la tocca. Se dopo F4 gli `errors[]` del
  batch finissero mescolati a quelli del ciclo, è una regressione.
- **T-3 — Lista vuota: due semantiche opposte.** Il BB proporrà `COMPLETATO`; `_compute_stato`
  di A oggi risponde `ERRORE` (`if not results`). Sono **corretti entrambi nel proprio
  contesto**: per A «nessun handler risolto» è un errore di configurazione, per un fan-out
  «nessun item da lavorare» è un successo. In F5 la differenza va **dichiarata**, non
  appianata di nascosto: appianarla cambierebbe lo stato scritto in `commesse_push_log`.
- **T-4 — Il parziale che diventa rumore.** Con il fix, un lotto con anche una sola commessa
  fallita mostra uno step in ERRORE nel cockpit. È **voluto** (è il punto), ma va guardato
  in-app: se sui dati veri il parziale fosse la norma e non l'eccezione, il problema non è la
  segnalazione — sono i dati, e allora si apre un'altra analisi.
- **T-5 — `dry_run`.** Il pull esce **prima** del ciclo se `dry_run` (`if dry_run: return`).
  Il fix non deve spostare quel ritorno né far comparire esiti parziali in dry-run.

---

## 9. Definizione di «fatto»

- Il pull chiude il `task_run` in ERRORE su rifiuto parziale, **senza sollevare**, e al
  rilancio dello step le commesse fallite vengono **riprovate**.
- `run_fan_out` esiste in `core/services/`, con **almeno due** chiamanti reali convertiti
  (C e B); `_compute_stato`/`errors[]` non sono più logica duplicata dove il BB è adottato.
- Il ramo `TaskEsitoParziale` dell'executor ha test propri (prima non ne aveva).
- Catalogo BB backend aggiornato; confine BB ↔ `QueueDrainEngine` scritto in entrambi i file.
- Suite `apps.vendite` + `apps.core` verde, smoke pipeline eseguito.
- Questo brief in `work-done`, R-1 chiuso nel piano residui.

---

## 10. Cosa NON si fa

- **Niente DB**: nessun codice errore nuovo, nessuna migration, nessun trigger (§5.2).
- **Niente ritentativi automatici** nel BB: il RESUME al rilancio è già il meccanismo di
  ripresa: aggiungerne un secondo dentro il fan-out creerebbe due politiche di retry.
- **Niente parallelismo**: il fan-out resta sequenziale. Nessun sito lo chiede.
- **Nessuna modifica al frontend**: il cockpit già rende gli step in ERRORE.
- **Non si tocca l'all-fail del pull** (§5.1), né la coda batch di B (T-2), né la discovery
  di nessuno dei tre siti.

---

## 11. Consuntivo (2026-08-09) — cosa è stato fatto e cosa si è scostato dal piano

### 11.1 Fasi

| Fase | Esito |
|---|---|
| **F0** decisioni | ✅ D-1 due astrazioni · D-2 pull sistemato · D-3 run logger dentro, opzionale |
| **F1** fix pull | ✅ `_handle_pull_attivita_da_commessa_task` ritorna `TaskEsitoParziale | None`; codice **riusato** `E_PULL_COMMESSA`; nessuna azione DB. **4 test nuovi** (parziale / tutte ok / tutte fallite / dry-run) |
| **F2** BB | ✅ `apps/core/services/fan_out.py` — `run_fan_out`, `FanOutEsito`, `FanOutItemErrore`, `FanOutRunLogger`. **14 test** in `apps/core/tests/services/test_fan_out.py` |
| **F3** adozione pull | ✅ il ciclo è una chiamata a `run_fan_out` + `_PullCommesseRunLogger` (i motivi per-commessa restano sui log di lotto) |
| **F4** adozione `_process_rows` | ✅ ciclo per-riga sul BB; la **coda batch è rimasta fuori**, invariata |
| **F5** valutazione sito A | ✅ **scartato con motivazione scritta** nel docstring di `_compute_stato` — nessun codice, come previsto |
| **F6** doc | ✅ catalogo BB backend (nuova sezione «Fan-out isolato») + confine dichiarato in `fan_out.py` **e** in `drain_engine.py` |

### 11.2 Scostamenti, tutti dichiarati

1. **Cinque test hanno cambiato il bersaglio della `@patch`**, non le asserzioni.
   `apps.vendite.services.pipeline_step_executor.transaction` →
   `apps.core.services.fan_out.transaction`, perché il savepoint si è **spostato** dentro
   il BB. Le verifiche sono identiche prima e dopo: è la giuntura del test che segue il
   codice, non un'aspettativa che cede. Nessun altro test è stato toccato — i 59 di
   `test_commesse_source_handlers` passano invariati.

2. **`_process_rows`: la coda del batch ora si riempie solo per le righe atterrate.**
   Prima `pending_inputs.append(...)` girava **dentro** il savepoint: una riga caduta a
   metà espansione lasciava i suoi input in coda all'upsert, cioè scriveva per una riga
   che era stata annullata. La regola era già scritta nel file per `commesse_ids` («un
   rollback non deve produrre id fantasma»); ora vale per entrambe. **È una correzione,
   non un refactor** — piccola, della stessa famiglia del difetto principale.

3. ~~**`commessa_cache` è rimasta DENTRO il savepoint**~~ → ✅ **CHIUSO nella stessa
   giornata** (Tid: «direi di chiudere questo residuo»). Vedi **§12**.

4. **Il gate dry-run del pull è a due cinture, e quella che conta non è nell'handler.**
   `_run_task` esce in dry-run **prima** di invocare l'handler, quindi il
   `if dry_run: return None` interno non è il presidio primario: è la difesa che tiene se
   un domani l'handler venisse chiamato fuori da `_run_task`. Il test lo dice
   esplicitamente invece di far finta di provare il ramo sbagliato.

### 11.3 Rettifica alla prima stesura

La prima stesura di questo brief affermava che `TaskEsitoParziale` non avesse **nessun**
test. Falso: la classe non compare per nome nei test, ma il suo comportamento è verificato
dai test 28/29 (snapshot indirizzi) e 32/33 (genera scadenze) di
`test_pipeline_step_executor.py`, «nessuna eccezione propagata» compreso. Mancavano solo i
test **specifici del pull**, che F1 ha aggiunto.

### 11.4 Cosa resta

- **Validazione in-app** (Tid): un lotto con una commessa che fallisce deve mostrare lo
  step in **ERRORE** nel cockpit e, al rilancio, ritentare **quella** commessa. È la
  trappola T-4: se sui dati veri il parziale risultasse la norma e non l'eccezione, il
  problema non è la segnalazione — sono i dati, e si apre un'altra analisi.
- **Commit** (Tid): il lavoro è nel working tree, non committato.
- Dopo la validazione: questo brief in `work-done` e **R-1 chiuso** nel piano residui.

---

## 12. Chiusura del residuo `commessa_cache` (2026-08-09, stessa giornata)

### 12.1 Il difetto

`BaseSourceHandler._process_rows` tiene una **cache di lookup** delle commesse: righe
diverse che appartengono alla stessa commessa non tornano al database una seconda volta.
La cache veniva popolata **dentro** il savepoint della riga. Se la riga cadeva *dopo* quel
punto — per esempio su `link_sorgente` — il rollback annullava la commessa **nel database**
ma non toccava il dizionario Python. In cache restava l'id di una commessa inesistente, e
la **riga gemella successiva** lo riusava: fallendo anche lei, su un errore che il codice
si era procurato da solo.

### 12.2 Perché non bastava spostarla a valle

La correzione ovvia — registrare la cache a fine giro, come già si fa per `commesse_ids` e
per la coda del batch — l'avrebbe resa **inutile**: la cache serve alla riga *successiva*
dello stesso giro, e a fine giro non serve più a nessuno. Ogni riga sarebbe tornata al
database, cioè si sarebbe barattata una race rara con una regressione di performance certa.

Serviva un aggancio **durante** il giro, ma **dopo** il commit del singolo item.

### 12.3 La soluzione — `on_success` nel BB

`run_fan_out` accetta ora `on_success(item, risultato)`, chiamato a **savepoint già
rilasciato**: è la versione "durante il giro" di `esito.risultati`, e serve esattamente
quando l'item successivo dipende da ciò che ha prodotto il precedente.

Due scelte di contratto, entrambe scritte nel docstring:

- **`on_success` NON è protetto**: se solleva, il giro si interrompe. È voluto — il lavoro
  dell'item è già committato e non è più annullabile, quindi mascherare l'errore come «item
  fallito» direbbe una bugia. Lì dentro si mettono registrazioni in memoria, non lavoro
  rischioso.
- Resta **opzionale**: il pull non lo usa.

Nel chiamante, `_registra_riga` raccoglie ora tutte e tre le registrazioni — cache,
`commesse_ids`, coda del batch — in un punto solo, e `_lavora_riga` non tocca più nessuna
struttura Python condivisa.

⚠️ È un'aggiunta di superficie al BB **al primo utilizzo**, il modo classico in cui un
building block si gonfia. È stata accettata perché non è un parametro *per un chiamante*:
è la formulazione generale della regola che il BB già dichiarava — *«gli effetti
collaterali valgono solo se l'item è atterrato»* — di cui `risultati` era finora solo la
versione a fine giro.

### 12.4 Test

- **4 test nuovi sul BB** (`OnSuccessTests`): chiamato solo per gli item riusciti · chiamato
  **dopo il rilascio del savepoint** (verifica l'ordine reale: apri → lavora → rilascia →
  registra) · effetto visibile all'item successivo · l'eccezione interrompe il giro e non
  diventa un item fallito.
- **1 test nuovo sul chiamante**: `test_cache_commessa_non_avvelenata_da_riga_caduta` — due
  righe con la stessa chiave commessa, la prima cade su `link_sorgente`, la seconda **deve**
  tornare al database e atterrare.
- ⚠️ **Il test è stato provato contro la regressione**: reintroducendo la scrittura in cache
  dentro il savepoint, fallisce (`1 != 2` sulle chiamate a `get_or_create_commessa`). Non
  passa per il motivo sbagliato.

**Suite: 2234 test verdi** (`apps.vendite` + `apps.core`), da 2229.

---

## 13. Validazioni residue in-app — l'unica cosa aperta di tutta la linea

> ⚠️ **Questo documento è, dal 2026-08-09, il raccoglitore dei residui di TRE cantieri**,
> non solo del proprio. Gli altri due sono chiusi e archiviati in `work-done`:
>
> * [brief-design-fatturazione-due-lenti.md](../work-done/brief-design-fatturazione-due-lenti.md) — i tre cruscotti + DDT/resi (§6-quater) + la guida
> * [piano-residui-orchestrazione-e-cruscotti-vendite.md](../work-done/piano-residui-orchestrazione-e-cruscotti-vendite.md) — il quadro R-1..R-4, con l'analisi che ha generato questo brief
> * [analisi-orchestrazione-vendite-simmetrie.md](../work-done/analisi-orchestrazione-vendite-simmetrie.md) — il disegno originale (temi A/B/C)
>
> Lo scarto fra il titolo («fan-out») e il contenuto di questa sezione è **voluto e
> dichiarato**: serviva un unico posto vivo dove leggere cosa manca, invece di tre documenti
> aperti al 95%. Chi cerca «cosa resta sui cruscotti» lo trova qui.
>
> **Quando entrambe le validazioni saranno passate, anche questo brief va in `work-done`** e
> la linea è chiusa per intero.

### 13.1 V1 — Esito parziale del pull da commessa (da questo brief)

Prerequisito: `kill -HUP` sul master gunicorn — il backend di sviluppo non ha autoreload,
senza il segnale in-app gira ancora il codice vecchio.

- Un lotto in cui **una commessa su N fallisce** deve mostrare lo step in **ERRORE** nel
  cockpit, e le altre commesse devono risultare **emesse** (il giro non si ferma).
- **Rilanciando** lo step, quella commessa deve essere **ritentata** — prima veniva saltata
  (SKIP) e nessuno se ne accorgeva. È il difetto che il cantiere ha chiuso.
- Se **tutte** falliscono, lo step deve **fermarsi** con `E_PULL_COMMESSA_ALL_FAILED`:
  proseguire costruirebbe un lotto vuoto.
- ⚠️ **Trappola T-4** (§8): se sui dati veri il parziale risultasse la **norma** e non
  l'eccezione, il problema non è la segnalazione — sono i dati, e si apre un'altra analisi.
  Non si "abbassa" la segnalazione per far tornare il verde.

> **Misura del 2026-08-16 (mattina) — il ramo nuovo non è mai stato percorso.** In
> `vendite.fatturazione_lotti_task_runs` **non c'è un solo run dal 2026-08-03**, e i
> 13 run storici di `pull_attivita_da_commessa` sono **tutti `COMPLETATO`**, tutti
> precedenti al fix (pushato il 2026-08-10). Non è che la validazione sia andata e
> non sia stata annotata: la pipeline non è proprio stata lanciata da allora. Resta
> valido il prerequisito in testa a questa sezione — senza `kill -HUP` sul master
> gunicorn il backend gira ancora col codice vecchio, e la prova direbbe il falso.

---

> ✅ **Caso normale: PASSATO (2026-08-16, 15:39 UTC).** Tid ha fatturato un gruppo
> da «Competenza fatturazione / Da emettere». Letto dal database (canale di
> sistema, non dall'app):
>
> | | |
> | --- | --- |
> | Lotto | **4135 `LTF-0003953`**, MASSIVO, competenza 2026-08-01, `stato_lotto` COMPLETATO, `riaperto_il` NULL |
> | Task run | **8 su 8 `COMPLETATO`**, tentativo 1, `pull_attivita_da_commessa` in testa |
> | Fattura | **9691** EMESSA, `numero` NULL, 1 riga, imponibile 1.089,00 → totale 1.328,58 |
>
> È il **primo run della pipeline dal 2026-08-03**, quindi la prima volta che il
> fan-out estratto a BB gira davvero in applicazione. Il prerequisito `kill -HUP`
> era soddisfatto (gunicorn riavviato più volte nel frattempo).
>
> **Cosa prova e cosa no.** Prova che l'estrazione del BB **non ha rotto il caso
> sano** — che era il rischio concreto di un ciclo riscritto e mai eseguito.
> **Non** prova il fix: per quello serve il caso parziale (una commessa che
> fallisce mentre le altre passano) e il rilancio che la ritenta invece di
> saltarla. Restano quindi aperti i punti 2 e 3 della lista qui sopra, e servirà
> costruire una commessa che fallisca l'emit dopo aver superato la scoperta.
>
> ⚠️ **Trovato guardando i dati, e non riguarda questo cantiere.** Le tre
> attività di agosto sono legate a **tre fatture diverse, tutte EMESSA e tutte
> senza numero**: 2263, 2457 e la 9691 appena creata. Il verbo «Rendi
> definitive» numera **tutte** le fatture del mese in stato EMESSA — e la
> **2263 non va numerata**. Prima di provare la numerazione va deciso come
> escluderla, altrimenti la prova la trascina dentro.

### 13.2 V2 — Slice 3-ter: DDT e resi nelle lenti (dal brief due-lenti)

Checklist in ordine di rischio, derivata dalle decisioni DL-19..28:

- **DL-19 — il bug che ha originato la slice**: un DDT che ha **superato** lo stato-trigger
  è ancora eleggibile al push (prima usciva per sempre, senza segnalazione). Prova: DDT
  order-backed con trigger `SPEDITO`, portalo a `CONSEGNATO`, verifica che risulti ancora
  da pushare.
- **DL-28 — gate causale**: DDT con causale fatturabile e una riga senza prezzo risolvibile
  → **blocco parlante** all'emissione, non silenzio. E causale non fatturabile (es.
  CONTO_VISIONE) → fuori dalle card.
- **DL-23 — nessun doppio conteggio**: ordine parzialmente spedito con trigger
  `SPEDITO/CONSEGNATO` → serbatoio mostra il **residuo**; con `CONFERMATO` → mostra il
  **pieno**.
- **DL-27 — il contatore**: reso confermato su merce già fatturata → riga in coda accrediti
  con differenza **negativa**; reso in DRAFT → **non** conta.
- **Card e drill-down**: le due aree nuove (DDT, RESI) si aprono davvero — la whitelist a 7
  aree era fail-closed, senza quella le card non erano drillabili.
- **Lista coda accrediti**: colonne 200-203 e i 3 preset resi, priorità responsive.
  ⚠️ Le etichette ora dicono **«Accredito dovuto / facoltativo»**, non più «NC dovuta /
  facoltativa» (allineamento a DL-24: si nomina il fatto, non il rimedio).

> **Misura del 2026-08-16 — due dei sei punti oggi non hanno un soggetto su cui
> girare.** Letto dal database:
>
> | Punto | Soggetti disponibili |
> | --- | --- |
> | DL-19 (DDT oltre lo stato-trigger, ancora eleggibile) | `fn_list_ddt_da_pushare()` → **1 riga**: un soggetto c'è, ed è l'unico |
> | Card DDT | `vw_dash_fatturazione_ddt` → **7 righe**: l'area si può guardare |
> | DL-27 (reso confermato su merce già fatturata → coda accrediti) | `vw_resi_da_accreditare` → **vuota**, pur con **5 resi CONFERMATO** su 10 |
>
> Il caso di DL-27 **va costruito** prima di poterlo provare: nessuno dei resi
> confermati oggi presenti alimenta la coda accrediti. Non è un difetto — è che il
> dato non c'è — ma è la ragione per cui quel punto non si spunta guardando l'app
> così com'è. (La misura non è un falso zero da RLS: le tabelle `resi` e `ddt` hanno
> RLS senza `FORCE` e l'interrogazione gira come proprietario.)

### 13.3 Le due cose non-validazione — una chiusa, una aperta

- ✅ **Commit**: fatto e **pushato** il 2026-08-10. Il BB fan-out e il fix dell'esito
  parziale sono in `388b7dfee`; il resto della linea (guida cruscotti, archiviazione dei
  tre doc, bonifica link) nello stesso commit, più `4828258d6` per la rigenerazione di
  `error_policies_generated.py`. Ramo `dev/backend-tid`, allineato con origin.
- ✅ **Build docs**: **fatto il 2026-08-16**, verde. `zensical` nel frattempo è
  installato nel `.venv` di radice, quindi `python scripts/build_docs_zensical.py`
  gira: **exit 0**, 14 secondi, 2575 pagine preprocessate, 3455 include espansi,
  9348 link riscritti, **zero warning di include**.

  Restano **5 warning, tutti preesistenti e nessuno di questo cantiere**:

  | Dove | Cosa |
  | --- | --- |
  | `docs/it/dbzero/pratiche/index.md` e il gemello `index.ci.md` | 4 link morti: `vw_definizioni_drift.md` e `fn_pubblica_definizione.md` |
  | `docs/it/dev/frontend/i18n-namespace-radici.md` | 1 àncora morta verso `frontend-standards.md#struttura-chiavi--radici-dei-namespace` |

  > ℹ️ **I 4 link morti non sono un contenuto sbagliato: è il generatore.**
  > L'index di schema è **auto-generato** (`scripts/gen_db_docs.py`) e ricopia la
  > prima frase delle pagine `manual/`. Dentro `manual/` un link
  > `[fn_pubblica_definizione](fn_pubblica_definizione.md)` è **corretto** — le due
  > pagine sono sorelle — ma issato di un livello nell'index punta a una cartella
  > dove quel file non c'è. Il generatore non riscrive i link relativi quando li
  > sposta di cartella. Si corregge lì, una volta per tutti gli schemi.

  ⚠️ **E una cosa che va saputa a proposito di questo residuo: non poteva
  validare nulla di questo cantiere.** `work-done/` e `work-in-progress/` sono
  **esclusi** dal build (`exclude_docs` in `mkdocs.yml` e pruning del preprocess:
  `excluded_dirs_removed=2`). I brief non entrano nel sito: il build vale come
  controllo **globale** della documentazione pubblicata, non come verifica dei
  testi di questa linea. La coerenza interna dei brief resta quella verificata a
  mano il 2026-08-10.

---

## 14. Ricognizione dei residui BE consegnati dal DB (2026-08-16)

> Il team DB ha ricontrollato contro il codice i residui che il lato DB aveva
> consegnato al BE «fuori da questa linea», e ne ha segnati **quattro**: due
> chiusi, due aperti. Riverificati qui uno per uno, con le righe di codice.
> **Esito: dei due segnati 🔴 aperti, nessuno lo è**; il terzo 🔴 era già stato
> deciso lo stesso giorno. Le due ✅ sono confermate.
>
> ⚠️ Il DB ha dichiarato di aver **corretto la propria memoria di progetto** su
> questa base. Va rettificata, altrimenti alla prossima sessione tornano a galla
> due residui inesistenti — lo stesso danno del registro sbagliato, col segno
> rovesciato.

| Voce | Segnata | Verificata | Dove |
| --- | --- | --- | --- |
| `terne_pronte` | 🔴 aperta | ✅ **consumata** | `commesse_repository.py:1267` → `GruppoDiagnosi` → `_fatturazione_job_helpers.py:221` |
| `riaperto_il` | 🔴 aperta | ✅ **consumata** | `pipeline_repository.py:2132/2144` → `pipeline_runner.py:392/546` |
| Slot indirizzi (§10.5) | 🔴 aperta | ✅ **decisa** «non si restringe» | §11.1 di `brief-db-indirizzi-su-ordini-contratti-offerte.md` |
| Pricing v5 F2-BE | ✅ fatta | ✅ confermata | `pricing_repository.py:90` chiama `fn_resolve_prezzo_listino_v2` |
| Documenti Fase A | ✅ fatta | ✅ confermata | `_REL_CONSENTITE` in `core/db/dbops_repository.py:26`, usata come guard in 2 punti |

### 14.1 `riaperto_il` — non è «girante ma inutile», governa il giro

Il rilievo diceva «compare solo in `smoke-ritorno-lotto-a-draft.py`, niente in
`backend/apps/`». Non regge: `is_lotto_riaperto()` lo legge
(`pipeline_repository.py:2132`), `azzera_riaperto_il()` lo spegne (`:2144`), e
`pipeline_runner.py:392` lo usa come **terzo motivo per rifare lo step corrente**
invece di avanzare — con l'azzeramento a `:546` quando il giro l'ha onorato,
senza il quale il lotto rifarebbe lo stesso step all'infinito.

⏱️ **E non è codice di oggi**: è entrato il **2026-08-03** (`6728e58cb`), quasi
due settimane prima della misura. Qui non c'è una spiegazione di tempistica: la
verifica ha guardato nel posto sbagliato.

**Cosa sopravvive del rilievo, in forma molto più stretta**: il segnale non
risale all'API e **il FE non mostra da nessuna parte che un lotto è stato
riaperto**. È una richiesta di *visibilità*, non un residuo di consumo — e come
tale va valutata a sé, non ereditata come «funzione DB inutile».

### 14.2 `terne_pronte` — misura scattata 49 minuti troppo presto

Anche qui il consumo c'è: `commesse_repository.py:1267` lo decodifica con
`_decode_jsonb` (col commento sul jsonb che su questa connessione arriva come
stringa), finisce in `GruppoDiagnosi` e `_fatturazione_job_helpers.py:221` lo
usa per distinguere i gruppi le cui terne sono fallite da quelli fermi per
un'altra causa. Tre test lo coprono.

⏱️ **Ma qui la spiegazione c'è, ed è onesta**: quel codice è entrato alle
**15:13** del 2026-08-16 (`4129f5a22`), il commit della verifica è delle
**16:02**. Su un checkout precedente il grep torna vuoto legittimamente. Non è
un errore di metodo — è una fotografia scattata prima del fatto.

### 14.3 Slot indirizzi — decisa, non aperta

«contratto ne dichiara 3, off-comm 4, i template ne stampano 1» è vero come
descrizione dello stato, ma la voce **non è aperta**: il 2026-08-16 è stato
deciso di **non restringere**, perché gli slot seguono
`config.tipi_indirizzi_allowed` — la stessa whitelist che il pannello FE legge a
runtime — e toglierli farebbe sparire in silenzio un indirizzo che l'operatore
può già inserire. Motivazione estesa in §11.1 del brief citato. Anche qui è
questione di minuti: la nota è delle 16:02, la chiusura è stata pushata alle
16:04.

### 14.4 Cosa lascia questa ricognizione

Nessun lavoro BE nuovo: **zero** delle quattro voci richiede codice. Restano due
cose da fare, entrambe di registro e non di sviluppo:

- la **memoria del DB va rettificata** sulle due voci `terne_pronte` e
  `riaperto_il`, altrimenti si autoconfermano alla prossima sessione;
- se la **visibilità FE del lotto riaperto** interessa davvero (§14.1), va
  aperta come richiesta sua, con il suo perimetro — non lasciata implicita
  dentro un residuo che nel merito è chiuso.

⭐ **La lezione, che è la stessa di due volte oggi**: una misura contro il codice
vale quanto il momento in cui è scattata e il posto in cui ha guardato. Una
frase che dichiara *chiuso* ciò che è aperto e una che dichiara *aperto* ciò che
è chiuso costano uguale — restano scritte, e la sessione dopo nessuno le
rimette in discussione.
