# Roadmap Fatturazione — Gap enterprise da colmare

> Promemoria di sviluppo derivato dalla review architetturale del 28/02/2026.
> Priorità ordinate per impatto sull'adozione in aziende medio-alte.
>
> 🔄 **Riconciliato con lo stato dei fatti il 2026-08-03.** Fra la review e
> oggi sono passati **cinque mesi** e **25 brief chiusi** sulla fatturazione
> (cockpit, coda lavori, due lenti, satelliti fattura, emissione mirata,
> drawer fattura…), che questo documento non aveva mai visto. Ogni item è
> stato riverificato sul codice e sui **dati vivi**; lo stato è annotato in
> testa a ogni sezione. Il testo originale è conservato: è ancora la
> descrizione migliore del *perché* di ognuno.

---

## 📊 Stato in una pagina (2026-08-03)

| # | Item | Priorità dichiarata (feb) | Stato verificato |
| --- | --- | --- | --- |
| 1 | Ciclo di vita post-emissione | P1 | 🔴 **APERTO** — ed è il vero bloccante |
| 2 | Integrazione contabile | P1/P3 | 🟡 scadenzario ✅ **chiuso**; contabilità 🔴 schema vuoto |
| 3 | Multi-company / multi-esercizio | P2 | 🟡 numerazione e isolamento ✅; esercizio fiscale 🔴 |
| 4 | Audit trail formale | P0 «una riga» | 🟡 **infrastruttura pronta, cablaggio mancante** |
| 5 | Dashboard operative | P3 | 🟢 in gran parte **fatto** (era P3 e si è fatto da sé) |
| 6 | Alerting e monitoring | P3 | 🔴 non fatto — ma i mattoni ci sono |
| 7 | `correlation_id` | P0 | 🟡 metà: pipeline sì, push no |
| 8 | Diagrammi di stato | P2 | 🔴 zero `stateDiagram-v2` nel repo |

### 🔑 La scoperta trasversale: `event_log` è **write-only**

`vendite.event_log` viene scritto da due repository (`pipeline_repository`,
`commesse_repository`) e **non è mai riletto**: zero endpoint di lettura, zero
consumatori nel frontend. È il denominatore comune di tre item — la «vista
lotti» non può mostrare l'ultimo evento (5a), la «vista errori» ha dovuto
ripiegare su altre fonti (5b), l'alerting non ha da dove partire (6) — ed è
anche il motivo per cui il `correlation_id` (7) non ha ancora un consumatore
che ne dimostri l'utilità.

**Un endpoint di lettura su `event_log`** (filtro severity + finestra
temporale + `correlation_id`) sblocca 5a, 5b e 6 insieme. È anche esattamente
ciò che serve alla richiesta di uno **strumento di consultazione dei log**
(Tid, 2026-08-03).

➡️ **Il tema è trattato per intero in
[analisi-osservabilita-log.md](analisi-osservabilita-log.md)**, che è il
documento principale dell'osservabilità: gli item **#5 (vista errori)**,
**#6 (alerting)** e **#7 (correlation_id)** di questa roadmap vivono lì come
passi di un piano unico, insieme al prerequisito
[brief-db-seed-messaggi-errore-mancanti.md](brief-db-seed-messaggi-errore-mancanti.md).
Questa roadmap resta il documento **di dominio** (fatturazione); quello è il
documento **trasversale**.

---

## 1. Ciclo di vita post-emissione

> 🔴 **APERTO (verificato 2026-08-03) — e la priorità P1 è, se possibile, sottostimata.**
>
> | Sotto-punto | Stato |
> | --- | --- |
> | Note di credito con legame alla fattura originale | ❌ nessun tipo documento NC, nessuna `fattura_riferimento_id` |
> | Rettifiche / fattura sostitutiva | ⚠️ `vendite.fatture_rettifiche` **esiste ma è legacy morto**: zero consumatori in `migrations_v2`, backend e frontend. Modello dati senza cablaggio |
> | Storno lotto **pre**-numerazione | ✅ `fn_annulla_lotto_da_draft` + task `reset_lotto_draft` |
> | Storno **post**-numerazione | ❌ bloccato per design (`trgfn_fatture_numerata_non_annulabile`) |
> | Stati `STORNATA`/`RETTIFICATA`/`NOTA_CREDITO_EMESSA` | ❌ il seed ha solo DRAFT/EMESSA/DEFINITIVA/INVIATA/REGISTRATA/ANNULLATA |
> | Dominio RESI | ✅ completo — **ma la NC è esplicitamente fuori scope**: esiste `vw_resi_da_accreditare` (la coda), non l'emissione |
>
> **Perché è più urgente della sua priorità.** Non è un requisito da brochure:
> è già costato due volte in una settimana. Le fatture **2263** e **2457** sono
> uscite con il piano rate sbagliato, sono in stato EMESSA, e **non si possono
> né correggere né disfare** — la matrice ammette `EMESSA → DRAFT` ma
> [la funzione che lo esegue non esiste](piano-db-ritorno-lotto-a-draft.md),
> e oltre DEFINITIVA l'unica strada sarebbe una nota di variazione che non
> abbiamo. Sull'ambiente ci sono già **6 fatture DEFINITIVE numerate**: da
> quelle non si torna indietro in alcun modo.
>
> Le due strade sono complementari, non alternative: la **Fase 6 DB** (ritorno
> a DRAFT) copre il pre-numerazione, la **nota di credito** copre il resto.

**Problema:** il flusso copre solo il forward (sorgente → fattura → SDI). Il 5-15% delle fatture ha un ciclo post-emissione che oggi non è documentato né strutturato.

**Da implementare:**

- Note di credito totali e parziali con legame alla fattura originale
- Rettifiche (fattura sostitutiva) con tracciamento della catena documentale
- Storno lotto: annullamento massivo pre-SDI vs gestione post-SDI (nota di credito obbligatoria)
- Stato documento esteso: aggiungere `STORNATA`, `RETTIFICATA`, `NOTA_CREDITO_EMESSA`
- Vincoli: una fattura INVIATA/accettata SDI non può essere stornata, solo creditata

**Impatto ER:**

- Relazione `fatture.fattura_riferimento_id` → fattura originale
- Tipo documento fiscale: `FATTURA`, `NOTA_CREDITO`, `NOTA_DEBITO`
- Possibile tabella `fatture_riferimenti` se una NC copre più fatture

---

## 2. Integrazione contabile

> 🟡 **MISTO (verificato 2026-08-03).** Un P1 è chiuso, il resto è fermo al modello.
>
> | Sotto-punto | Stato |
> | --- | --- |
> | Scadenzario collegato alla pipeline | ✅ **CHIUSO 01-02/08/2026** — `fn_genera_scadenze_fattura`/`_lotto`, task `genera_scadenze_lotto` in **entrambe** le pipeline nello step EMESSA, con policy `RESUME_STEP` e ordine presidiato in `pipeline_step_executor`. Collaudato: `smoke-fattura-scadenze.py` 10/10 |
> | Mapping conti | 🟡 esistono le FK `articoli.conto_contabile_vendita_id` e `iva.conto_iva_vendita_id`. Manca **cliente→partitario** e manca ogni tabella di *regole*. ⚠️ il seed `conti_contabili` ha **3 righe, 2 delle quali con descrizione «eliminare»** |
> | Generazione scritture contabili | ❌ lo schema `contabilita` è **letteralmente vuoto**: zero tabelle, zero funzioni, zero viste |
> | Riconciliazione incassi | ❌ non fatto — ma **misurato**: [brief-incassi-riconciliazione-rate-promemoria.md](brief-incassi-riconciliazione-rate-promemoria.md) (02/08) accerta che «nell'intero database non esiste alcuna colonna `scadenza_id`». Il saldo è **per fattura, non per rata**; le 10 tabelle di `pagamenti` sono a 0 righe |
>
> ⚠️ **La riga «`fatture_scadenze` esiste ma non è nel flusso operativo» qui
> sotto non è più vera** ed è conservata solo come storia. Ora il piano rate
> nasce dentro la pipeline, e le sue condizioni arrivano dal documento sorgente
> ([brief-db-termine-dal-documento-alla-commessa.md](brief-db-termine-dal-documento-alla-commessa.md), 03/08).

**Problema:** il flusso si ferma a INVIATA/SDI. La fattura deve generare scritture contabili, aggiornare il partitario e alimentare lo scadenzario.

**Da implementare:**

- Generazione automatica scritture contabili da fattura definitiva (o da evento DEFINITIVA nella pipeline)
- Mapping conti: articolo/servizio → conto ricavo, aliquota IVA → conto IVA, cliente → conto partitario
- Scadenzario: `fatture_scadenze` esiste ma non è nel flusso operativo — collegarlo alla pipeline come task post-DEFINITIVA
- Riconciliazione incassi: matching pagamento ↔ scadenza (almeno il modello dati)

**Scelta architetturale:**

- La generazione scritture può essere un task pipeline (step post-DEFINITIVA o post-INVIATA)
- Il mapping conti va in configurazione (tabella lookup), non hardcoded
- Valutare se la contabilità è un modulo separato che consuma eventi da `event_log` (disaccoppiamento) o se è integrato nella pipeline lotti

---

## 3. Multi-company e multi-esercizio

> 🟡 **MISTO (verificato 2026-08-03).** La metà normativa è coperta, quella contabile no.
>
> | Sotto-punto | Stato |
> | --- | --- |
> | Numerazione per esercizio/sezionale con reset annuale | ✅ **FATTO** — `registri_fatturazione` (`reset_policy` default `ANNUALE`) + `registri_fatturazione_progressivi` (unique su `registro, anno, mese, serie`) + `fn_assign_numero_fattura` con lock `FOR UPDATE`. È il requisito **normativo non negoziabile**, ed è quello coperto |
> | Isolamento dati per società | ✅ **FATTO** via RLS EF-whitelist, diffusa su tutta la famiglia fatture + commesse + documenti. ⚠️ ma è isolamento per **emittente fiscale**, non per «società»: del **consolidamento cross-company** non c'è traccia |
> | Esercizio fiscale come entità esplicita | ❌ **zero occorrenze** di `esercizio`/`anno_fiscale`/`periodo_contabile` in `migrations_v2` e nel backend. L'esercizio è oggi l'anno solare *derivato* da `fatture.data` |
> | Due esercizi aperti contemporaneamente | ❌ non è nemmeno **esprimibile**: senza l'entità con apertura/chiusura, la domanda non ha un posto dove essere formulata |
>
> Nota: i due ✅ erano in buona parte già in piedi a febbraio — non sono
> avanzamento del periodo, sono stato preesistente che la review non aveva
> registrato.

**Problema:** il modello parla di BA/utility/emittente ma non è chiaro il supporto per esercizi fiscali multipli aperti e consolidamento tra società.

**Da implementare:**

- Esercizio fiscale come entità esplicita (non solo `competenza_mese`)
- Supporto a due esercizi aperti contemporaneamente (chiusura esercizio precedente + operatività corrente)
- Numerazione fatture per esercizio/sezionale con reset annuale
- Perimetro commessa esteso: `(emittente, esercizio, BA, utility, competenza)`
- Se multi-company: isolamento dati per società con possibilità di query cross-company per consolidamento

**Attenzione:**

- La numerazione fiscale (DEFINITIVA) deve rispettare i vincoli di sequenzialità per sezionale/esercizio — questo è un requisito normativo italiano non negoziabile

---

## 4. Audit trail formale

> 🟡 **INFRASTRUTTURA PRONTA, CABLAGGIO MANCANTE (verificato 2026-08-03).**
> Il «quick win» qui sotto sembra fatto e **non lo è**: è la trappola di questo item.
>
> | Sotto-punto | Stato |
> | --- | --- |
> | `user_id` su ogni evento | ⚠️ **falso positivo**. La colonna `actor` esiste ed è popolata su **309 righe su 309** — ma il valore è **sempre `service:django`**. `fn_log_event` accetta il parametro, il repository ha `actor: str = "service:django"` come default, e **nessun chiamante lo sovrascrive**. L'audit dice *«è stato il servizio»*, mai *chi* |
> | `ruolo` sull'evento | ❌ colonna assente |
> | Non-ripudiabilità | ✅ `trg_event_log_append_only_ud` blocca UPDATE e DELETE |
> | Retention 10 anni (normativa fiscale) | ❌ `event_log` **non ha `cleanup_at`**, nessuna policy definita. Le `dbops.*` ce l'hanno, i log di dominio no |
>
> 🔴 **Effetto collaterale misurato**: 98 eventi `PUSH_STARTED` su 309 (32%)
> hanno **`entity_id = 0` e `correlation_id` NULL** insieme — non sono
> collegabili né a un'entità né a un run. Sono scritti da
> `commesse_push_orchestrator`, che passa `entity_id=0` come segnaposto.
> Un terzo del registro eventi, oggi, non è interrogabile.
>
> Il quick win resta **piccolo e vero**: passare l'identità già presente nei
> GUC (`app.current_user_id`, `app.ruolo_applicativo`) ai chiamanti di
> `log_event`. Ma va fatto, non dato per fatto.

**Problema:** l'event_log è ottimo per l'operatività ma non è sufficiente per compliance formale (revisori, SOX-like, certificazione bilancio).

**Da implementare:**

- Registrare `user_id` e `ruolo` su ogni evento (chi ha fatto cosa)
- Propagare `correlation_id` ai livelli mancanti:
  - `PipelineStepExecutor` → task_run
  - `CommessaPushOrchestrator` → eventi push
- Garantire non-ripudiabilità: trigger append-only già c'è, verificare che nessun path applicativo possa bypassarlo
- Retention policy: definire per quanto tempo conservare i log (normativa fiscale italiana: 10 anni per documenti fiscali)

**Quick win:**

- Aggiungere `user_id` a `fn_log_event()` — è una modifica piccola con impatto grande sulla tracciabilità

---

## 5. Dashboard operative

> 🟢 **IN GRAN PARTE FATTO (verificato 2026-08-03)** — pur essendo classificato
> **P3**. Si è fatto da sé, trascinato dal cockpit fatturazione (luglio 2026).
>
> | Sotto-punto | Stato |
> | --- | --- |
> | «Vista lotti» | ✅ **FATTO** — `LottoDrawer.vue`: stato corrente, tab **task-run** (tentativo, esito, `error_code: error_message`), tab **segnalazioni** con severity e banner sui critici. Più `LottiListView` con filtro stato e badge mensili. ⚠️ manca solo «ultimo evento da `event_log`» (vedi §write-only) |
> | «Azioni rapide» | 🟡 **2 su 3** — rerun lotto in errore ✅, approvazione commessa ✅. **Reset a step precedente ❌**: le uniche «reset» esistenti *demoliscono* (portano ad ANNULLATA), non tornano allo step prima, e sono gated su `isDraft` — cioè inutilizzabili proprio sui lotti bloccati |
> | «Vista errori» | 🟡 esiste il pannello nella Lente 1, **ma con semantica diversa**: legge `task_runs` + `fatture.critical`, **non `event_log`**, e il perimetro è il **mese di competenza**, non «ultime N ore». Il link diretto al lotto ✅ c'è; quello alla commessa no |
> | «Vista push» | ❌ **NON FATTO** — nessuna UI per `commesse_push_log`. L'endpoint è solo **puntuale per id** (`GET commesse/push/<id>/`), manca la lista/ultimo-run per sorgente. I contatori `created/updated/skipped/errors` esistono nel payload e **non sono renderizzati da nessuna parte**: l'operatore riceve un `push_log_id` in un toast e non ha modo di aprirlo |
>
> 💡 **L'idea da salvare è la frase finale della sezione** — «la dashboard non
> è un report, è uno strumento di governo» — che si è rivelata giusta: è
> esattamente ciò che il cockpit è diventato. Le due lacune (vista push,
> reset a step) restano valide e ora si possono chiedere in modo preciso.

**Problema:** il modello dati è pronto per un'operatività sofisticata ma senza interfaccia il vantaggio si perde.

**Quando ci lavori, tenere presente:**

- **Vista lotti:** stato corrente, ultimo evento da `event_log`, task_run con tentativo ed esito, segnalazioni attive con severity — l'operatore deve capire in 5 secondi se un lotto è sano o ha problemi
- **Vista errori:** filtro per severity ERROR su event_log nelle ultime N ore, con link diretto al lotto/commessa coinvolto
- **Vista push:** esito ultimo run per sorgente (contatori created/updated/skipped/errors), handler in errore evidenziati
- **Azioni rapide:** rerun lotto in errore, reset a step precedente (con rollback), approvazione commessa — senza passare da API manuali

**Principio:** la dashboard non è un report, è uno strumento di governo. L'operatore deve poter agire, non solo guardare.

---

## 6. Alerting e monitoring produzione

> 🔴 **NON FATTO (verificato 2026-08-03)** — ma i mattoni ci sono tutti, e uno
> è un precedente diretto da imitare.
>
> | Sotto-punto | Stato |
> | --- | --- |
> | Query periodica su `event_log` severity=ERROR | ❌ non esiste **alcun** consumer di lettura di `event_log` in tutto il backend |
> | Alert su lotti in stallo (`IN_ESECUZIONE` da > X min) | ❌ nessuna occorrenza di `stallo`/`stalled`/`watchdog` |
> | Alert su push oltre soglia errori | ❌ nessuna soglia, nessun consumer di `commesse_push_log` |
> | Canale notifica | 🟡 **infrastruttura sì, uso no**: `EmailOutboxService` + `send_pending_emails` (cron) esistono e sono riusabili; nessun chiamante li usa per alert. Webhook: zero occorrenze |
>
> ✅ **Il precedente da riusare esiste già ed è vicinissimo**:
> `MaintenanceRepository.job_liveness()` + le soglie in
> `coda_lavori/gestione_service.py` producono il badge «worker vivo / coda
> ferma», esposto in topbar e in Strumenti → Code di lavoro. È la stessa
> forma di controllo che serve qui — ma applicata ai **drainer**, non ai
> **lotti**, e soprattutto è **pull (badge), non push (notifica)**: nessuno
> viene avvisato se non guarda lo schermo.
>
> Il salto da fare è quindi minore di quanto la sezione lasci pensare:
> non «costruire il monitoring», ma **puntare un meccanismo esistente su
> un'altra sorgente e aggiungergli un canale d'uscita**.

**Problema:** i KPI sono definiti ma non c'è notifica automatica. Un lotto bloccato in ERRORE per ore è invisibile senza monitoring.

**Da implementare (anche minimale):**

- Query periodica su `event_log` con `severity = 'ERROR'` nelle ultime N ore
- Alert su lotti in `IN_ESECUZIONE` da più di X minuti (possibile stallo)
- Alert su push con percentuale errori sopra soglia
- Canale notifica: anche solo email o webhook — l'importante è che esista

**Approccio consigliato:**

- Job Django/cron leggero che interroga event_log e manda notifiche
- Non serve un sistema di monitoring esterno in prima battuta

---

## 7. Correlation_id — completamento propagazione

> 🟡 **A METÀ (verificato 2026-08-03 sui dati vivi).** Il gap è preciso e
> misurabile, non generico:
>
> | Dominio / entità | Eventi con `correlation_id` | |
> | --- | --- | --- |
> | `PIPELINE` / `LOTTO` | **112 su 113** | 🟢 di fatto completo |
> | `COMMESSE` / `TASK_RUN` | **0 su 196** | 🔴 mai popolato |
>
> Causa accertata: `commesse_push_orchestrator.py` chiama `log_event` **senza
> passare `correlation_id`** — la parola non compare nel file. E la tabella
> `fatturazione_lotti_task_runs` **non ha affatto** una colonna
> `correlation_id`: sui task_run la propagazione non è incompleta, è assente
> alla radice.
>
> Resta **P0** ed è la voce più sottovalutata del documento: senza,
> «una singola query ricostruisce l'intera timeline» — la frase qui sotto —
> è vera solo per la pipeline, cioè per il ramo che già si diagnostica bene
> col `LottoDrawer`. È **proprio sul push**, dove gli strumenti mancano, che
> la correlazione non c'è.

**Problema:** documentato onestamente nella guida, ma è un gap tecnico concreto che limita il debug e l'audit.

**Da fare:**

- Propagare `correlation_id` da `LottoPipelineRunner` a `PipelineStepExecutor`
- Propagare ai singoli `task_run` (fn_start/complete/fail_lotto_task_run)
- Generare `correlation_id` nel `CommessaPushOrchestrator` e propagarlo agli eventi push
- Risultato atteso: una singola query su `correlation_id` ricostruisce l'intera timeline di qualsiasi operazione

---

## 8. Flusso errore documentato (diagramma)

> 🔴 **NON FATTO (verificato 2026-08-03), ma è il più economico di tutti.**
>
> Nel repo ci sono **3 diagrammi Mermaid** sulla fatturazione: un `flowchart TD`
> (architettura logica, puro happy-path: nessun `ERRORE`, nessun `rerun`,
> nessun ramo condizionale) e due `erDiagram` strutturali. `cruscotti-fatturazione.md`
> non ne ha nessuno. I `stateDiagram-v2` nel repo sono **zero** — l'unica
> occorrenza della stringa è la riga qui sotto che li richiede.
>
> ✅ **La sostanza è però già scritta**, in prosa e tabelle: i 4 stati del lotto
> e i 4 del task_run esistono e sono documentati; §«Gestione errori e
> osservabilità» e §«Rollback di step» di `fatturazione.md` descrivono dove il
> rollback è possibile e dove serve intervento manuale. **È lavoro di
> trasposizione, non di analisi** — e vale la pena farlo *dopo* aver chiuso
> l'item 1, così il diagramma potrà mostrare anche la via d'uscita
> (ritorno a DRAFT / nota di credito) invece di documentare un vicolo cieco.

**Problema:** il flowchart principale resta happy-path. Con tutto il framework di gestione errori ora presente, manca una visualizzazione del flusso alternativo.

**Da fare:**

- Diagramma di stato del lotto: `DRAFT` → `IN_ESECUZIONE` → `COMPLETATO` | `ERRORE` → `rerun` / `reset`
- Diagramma di stato del task_run: `IN_ESECUZIONE` → `COMPLETATO` | `ERRORE` | `ANNULLATO`
- Evidenziare: dove il rollback è possibile, dove serve intervento manuale, dove il retry è automatico
- Formato: Mermaid `stateDiagram-v2`, coerente col resto della guida

---

## Ordine di attacco — ORIGINALE (28/02/2026, storico)

 i P0 sono cose che puoi fare in poche ore e sbloccano molto, i P1 sono bloccanti per andare in produzione reale, i P2-P3 possono crescere incrementalmente.

| Priorità | Item                                 | Motivazione                                                     |
| -------- | ------------------------------------ | --------------------------------------------------------------- |
| **P0**   | Correlation_id completo (#7)         | Poco effort, abilita debug e audit su tutto il resto            |
| **P0**   | User_id su event_log (#4 quick win)  | Una riga di codice, impatto enorme                              |
| **P1**   | Note di credito (#1)                 | Bloccante per adozione — senza NC non si va in produzione reale |
| **P1**   | Scadenzario operativo (#2 parziale)  | `fatture_scadenze` esiste, va solo collegato al flusso          |
| **P2**   | Multi-esercizio (#3)                 | Necessario per il primo anno fiscale reale                      |
| **P2**   | Diagrammi di stato (#8)              | Aiuta lo sviluppo di tutto il resto                             |
| **P3**   | Integrazione contabile completa (#2) | Modulo separato, può crescere incrementalmente                  |
| **P3**   | Dashboard (#5)                       | Dipende da stabilità del modello dati sottostante               |
| **P3**   | Alerting (#6)                        | Utile ma non bloccante fino alla produzione                     |

---

## 🔄 Ordine di attacco — RIVISTO (2026-08-03)

Cosa è cambiato rispetto a febbraio: **due voci escono** (scadenzario chiuso,
dashboard in gran parte fatta), **una scende** dopo essere stata quasi
chiusa da sé, e soprattutto **la #1 sale in cima** — non per completezza
funzionale ma perché ha già fatto danno.

| Priorità | Item | Perché ora |
| --- | --- | --- |
| **P0** | **Ritorno a DRAFT + note di credito (#1)** | Non più teoria: **2 fatture** in una settimana sono uscite sbagliate e sono irreparabili, **6 sono già DEFINITIVE**. La Fase 6 DB copre il pre-numerazione, la NC il resto. È l'unico item che *peggiora da solo* col passare del tempo |
| **P0** | **`correlation_id` sul push (#7)** | Il gap è isolato e misurato: `COMMESSE/TASK_RUN` a **0 su 196**. Poche righe, e senza di esso l'item 6 non ha da dove partire |
| **P0** | **Identità reale su `log_event` (#4)** | Resta un quick win, ma **va fatto davvero**: oggi `actor` dice sempre `service:django`. I GUC hanno già l'identità, basta passarla |
| **P1** | **Endpoint di lettura su `event_log`** *(nuovo)* | Non era nel documento di febbraio. Sblocca insieme «ultimo evento» (5a), «vista errori» vera (5b) e alerting (6), ed è ciò che serve allo strumento di consultazione log chiesto il 03/08 |
| **P1** | Riconciliazione incassi (#2) | Già misurata in [brief-incassi-riconciliazione-rate-promemoria.md](brief-incassi-riconciliazione-rate-promemoria.md): manca l'aggancio **rata↔incasso**. Ora che le rate esistono davvero, il buco è visibile |
| **P2** | Vista push + reset a step (#5, le due lacune) | Il resto della dashboard c'è; queste due restano e ora si chiedono in modo preciso |
| **P2** | Alerting (#6) | Dopo l'endpoint di lettura diventa piccolo: `job_liveness()` è il precedente, l'outbox email il canale |
| **P2** | Diagrammi di stato (#8) | Trasposizione, non analisi. Da fare **dopo** #1, così mostra anche la via d'uscita |
| **P3** | Esercizio fiscale (#3) | La parte normativa (numerazione) è coperta; questa serve al **primo bilancio**, non al primo ciclo |
| **P3** | Contabilità (#2) | Schema vuoto: è un modulo, non un item. Prima serve decidere se consuma eventi o vive nella pipeline |

### Voci uscite dall'elenco

| Item | Perché esce |
| --- | --- |
| ~~Scadenzario operativo (P1)~~ | ✅ **chiuso** 01-02/08/2026, collaudato 10/10 |
| ~~Dashboard (P3)~~ | 🟢 fatta col cockpit di luglio, salvo le due lacune promosse a P2 |
| ~~User_id «una riga di codice»~~ | ⚠️ non esce: **rientra come P0**, perché sembrava fatto e non lo era |

---

## 📌 Nota di metodo

Questa riconciliazione ha trovato **un falso positivo** (§4: colonna popolata
al 100% ma con un valore costante che non informa) e **un requisito superato
dai fatti** (§2 scadenzario). Nessuno dei due si vedeva leggendo il documento:
si sono visti solo interrogando i dati vivi.

È il motivo per cui conviene riverificare un promemoria prima di usarlo per
decidere — e per cui questo documento porta ora, in ogni sezione, la **data
della verifica** accanto allo stato. Un promemoria senza data di verifica
invecchia in silenzio, e la parte che invecchia peggio è proprio quella che
dichiara «fatto».