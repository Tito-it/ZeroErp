# Roadmap Fatturazione — Gap enterprise da colmare

> Promemoria di sviluppo derivato dalla review architetturale del 28/02/2026.
> Priorità ordinate per impatto sull'adozione in aziende medio-alte.
>
> 🔄 **Riconciliato con lo stato dei fatti il 2026-08-03**, e l'**item 1
> riverificato il 2026-08-21** sui dati veri (la prima nota di credito esiste).
> Fra la review e
> oggi sono passati **cinque mesi** e **25 brief chiusi** sulla fatturazione
> (cockpit, coda lavori, due lenti, satelliti fattura, emissione mirata,
> drawer fattura…), che questo documento non aveva mai visto. Ogni item è
> stato riverificato sul codice e sui **dati vivi**; lo stato è annotato in
> testa a ogni sezione. Il testo originale è conservato: è ancora la
> descrizione migliore del *perché* di ognuno.

> 🔄 **Riverificato il 2026-09-09**, e la notizia è che **le affermazioni
> portanti reggono ancora**: la scoperta trasversale (`event_log` write-only),
> l'item 2, l'8 e il 9 sono stati ricontrollati sul codice vivo e sono **giusti**
> — vedi §«Cosa è stato ricontrollato». ⭐ È metà del valore di questa passata, e
> senza scriverlo si ripaga daccapo: chi rilegge non deve ri-verificare quattro
> cose per scoprire che erano a posto.
> Ciò che è indietro è il **contesto**: fra il 31-08 e oggi una cinquantina di
> documenti sono entrati o si sono mossi in `work-done/`, e almeno sette
> toccano item di questa roadmap. Gli item 3, 5 e 6 hanno una nota nuova, e c'è
> un **item 11**.

---

## 📊 Stato in una pagina (2026-08-03, item 1 al 2026-08-21, item 10 al 2026-08-22, item 11 al 2026-09-09)

| # | Item | Priorità dichiarata (feb) | Stato verificato |
| --- | --- | --- | --- |
| 1 | Ciclo di vita post-emissione | P1 | 🟡 **la metà «nota di credito» è VIVA sui dati veri** (2026-08-21); resta il ritorno a DRAFT |
| 2 | Integrazione contabile | P1/P3 | 🟡 scadenzario ✅ **chiuso**; contabilità 🔴 schema vuoto |
| 3 | Multi-company / multi-esercizio | P2 | 🟡 numerazione e isolamento ✅; esercizio fiscale 🔴 |
| 4 | Audit trail formale | P0 «una riga» | 🟡 **infrastruttura pronta, cablaggio mancante** |
| 5 | Dashboard operative | P3 | 🟢 in gran parte **fatto** (era P3 e si è fatto da sé) |
| 6 | Alerting e monitoring | P3 | 🔴 l'**alerting sui dati** non è fatto (riverificato 09-09) — ⚠️ ma la metà «vitalità dei **processi**» ha avuto il suo cantiere, chiuso il 07-09 |
| 7 | `correlation_id` | P0 | 🟡 metà: pipeline sì, push no |
| 8 | Diagrammi di stato | P2 | 🔴 zero `stateDiagram-v2` nel repo |
| 9 | Passo SDI: prepara il payload, nessuno lo invia | — (nuovo, 05/08) | 🟡 **sospeso per decisione** — la pipeline ora scrive in `fatture_sdi`, manca il builder XML a valle. ⚠️ Dal 31/08 raccoglie anche il residuo del cantiere IVA: `EsigibilitaIVA`, `DatiContratto` e le righe **spezzate** dal plafond |
| 10 | Preview di fatturazione del contratto | — (assorbito, 22/08) | 🔴 non esiste — il dato c'è nel motore, manca chi lo presenta |
| 11 | Integrità del giro: di chi è questo documento, adesso? | — (nuovo, 09/09) | 🟢 **DB completo**, resta il frontend |

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
[brief-db-seed-messaggi-errore-mancanti.md](../work-done/brief-db-seed-messaggi-errore-mancanti.md).
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
> [la funzione che lo esegue non esiste](../work-done/piano-db-ritorno-lotto-a-draft.md),
> e oltre DEFINITIVA l'unica strada sarebbe una nota di variazione che non
> abbiamo. Sull'ambiente ci sono già **6 fatture DEFINITIVE numerate**: da
> quelle non si torna indietro in alcun modo.
>
> Le due strade sono complementari, non alternative: la **Fase 6 DB** (ritorno
> a DRAFT) copre il pre-numerazione, la **nota di credito** copre il resto.
>
> ---
>
> ⭐ **AGGIORNAMENTO 2026-08-18 — la nota di credito ha un design completo.**
> Non è più «da progettare»: dieci decisioni chiuse con Tid e un piano DB a nove
> slice in
> [brief-design-note-credito-resi.md](../work-done/brief-design-note-credito-resi.md).
> **Quello è il documento unico dell'item, questa roadmap resta il perché.**
>
> Cosa risponde, delle caselle ❌ qui sopra:
>
> | Sotto-punto di questa tabella | Risposta del design |
> | --- | --- |
> | *«nessun tipo documento NC»* | ⭐ **asse nuovo `config.nature_doc_fiscale`**, non una riga in `tipi_doc_fiscale`: canale e natura fiscale sono due assi ortogonali, e quella colonna oggi tiene il canale |
> | *«nessuna `fattura_riferimento_id`»* | **tracciabilità riga↔riga** (`fatture_righe.riga_rettificata_id`) + `fatture_rettifiche` popolata come proiezione — non due verità |
> | *«`fatture_rettifiche` è legacy morto»* | smette di esserlo: diventa l'indice documento↔documento del legame di riga |
> | *«dominio RESI completo ma la NC è fuori scope»* | è **questo** il cantiere che la porta dentro, ed è sbloccato dai due che lo precedevano |
> | *«stati `STORNATA`/`RETTIFICATA`/`NOTA_CREDITO_EMESSA`»* | ⚠️ **non servono**: la natura sta sul documento nuovo, non come stato di quello vecchio. Uno stato `RETTIFICATA` sulla fattura originale sarebbe una seconda verità accanto al legame di riga |
>
> ⚠️ **Resta aperta la metà pre-numerazione** (ritorno a DRAFT): è l'altro
> brief, e le due strade restano complementari come dice il capoverso qui sopra.
>
> ---
>
> ⭐ **AGGIORNAMENTO 2026-08-21 — non è più un design: esiste.** La prima nota di
> credito è sui dati veri (fattura **15353**, natura `NOTA_CREDITO`, tre righe
> che rettificano le righe della fattura **835**), con importi e legami di riga
> corretti. La casella *«nessun tipo documento NC»* si chiude qui.
>
> | Riga della tabella in testa | Stato al 2026-08-21 |
> | --- | --- |
> | Note di credito con legame alla fattura originale | ✅ **fatto** — natura su `config.nature_doc_fiscale`, legame `fatture_righe.riga_rettificata_id` |
> | `fatture_rettifiche` legacy morto | ✅ **non più**: è l'indice documentale, popolato dal task `popola_fatture_rettifiche` (fase DEFINITIVA) |
> | Stati `STORNATA`/`RETTIFICATA`/`NOTA_CREDITO_EMESSA` | ⛔ **decisione: non servono** (vedi sopra) — la voce esce dall'elenco |
> | Dominio RESI: «la NC è fuori scope» | ✅ dentro: dalla coda `vw_resi_da_accreditare` all'accredito, alla riga di commessa, al documento |
> | Storno **post**-numerazione | 🔴 resta bloccato per design — ed è **giusto**: la strada è la nota di variazione, che ora c'è |
> | Storno lotto **pre**-numerazione | 🔴 aperto (Fase 6 DB, ritorno a DRAFT) |
>
> **Cosa è entrato dopo il design**, e non era nel piano di agosto:
>
> * 🔒 **la nota non si numera prima della fattura che corregge**
>   (`E_FATTURA_RETTIFICATA_SENZA_NUMERO`, **937**): la TD04 deve citare numero e
>   data del documento corretto in `DatiFattureCollegate`. Predicato **per riga**
>   e **fail-closed** sulla visibilità RLS. ⚠️ Il difetto era reale ma
>   **mascherato** da un'altra precondizione (piano rate assente): un controllo
>   che protegge per caso non è un presidio;
> * 🔗 **arco N nel lineage** (fattura rettificata → nota di credito), ramo di
>   ritorno come R, ricostruito dalle righe e non dal ponte documentale — che in
>   quella finestra è ancora vuoto. Con la **natura** sul nodo, sul traversal e
>   sulla frontiera: senza, due documenti nati dalla stessa commessa erano
>   indistinguibili;
> * 📖 **la fattura ha il suo pannello «Passaggi»** (`/vendite/fatture/<id>/passaggi/`):
>   la classificazione «capolinea senza superficie propria» è caduta da entrambi i
>   lati — il drawer c'è da luglio, e l'arco N le dà un discendente.
>
> 🔴 **Il vero residuo dell'item 1 è ora uno solo**: il **ritorno a DRAFT**
> (Fase 6 DB). Le fatture **2263** e **2457** citate sopra restano il caso
> d'uso — ⚠️ e la **2263 non va numerata**.

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
> ([brief-db-termine-dal-documento-alla-commessa.md](../work-done/brief-db-termine-dal-documento-alla-commessa.md), 03/08).

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
>
> ⚠️ **Aggiornamento 2026-09-09: «numerazione ✅» non è più la stessa
> numerazione.** Dal 31-08 il tema ha avuto tre cantieri —
> [i due motori](../work-done/analisi-db-numerazione-documenti-e-due-motori.md),
> [il prefisso sul registro e l'allineamento dei contatori](../work-done/brief-db-prefisso-sul-registro-e-allineamento-contatori.md)
> e il [CRUD dei registri lato BE/FE](../work-done/brief-be-fe-crud-registri-di-numerazione.md).
> ⭐ E hanno cambiato una cosa che questa riga dava per assodata: **la serie è un
> asse di sequenza, non un'etichetta**, quindi il pavimento del contatore è per
> `(registro, serie)`. Chi legge il «✅» del 03-08 e progetta sopra la vecchia
> forma sbaglia il perimetro del lock.
> ⛔ Il sotto-punto che NON si è mosso resta l'**esercizio fiscale**: quello è
> ancora 🔴, e non va confuso col reset annuale del progressivo, che è un'altra
> cosa.
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

> ⚠️ **Aggiornamento 2026-09-09.** La fotografia del 03-08 è cresciuta, e le
> due lacune dichiarate («vista push», «reset a step») **non** sono quelle che
> si sono mosse. Cantieri chiusi da allora che vivono in questa sezione:
> [esito-gruppo-lotto](../work-done/brief-db-esito-gruppo-lotto.md) (DB, BE e FE
> completi: il giro sa dire com'è andato **documento per documento**),
> [uscita-documento-dal-giro](../work-done/brief-db-uscita-documento-dal-giro.md)
> (il verbo che toglie un documento dal giro, end-to-end),
> `gruppo_key` sulle segnalazioni e la ricerca sulla dash competenza.
> ⇒ La «vista errori» non è più solo un pannello di lettura: da questi cantieri
> l'operatore **agisce** sul singolo documento — che è esattamente la frase
> finale di questa sezione, arrivata dove non ce l'aspettavamo.

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
>
> ⚠️ **Aggiornamento 2026-09-09 — e la distinzione conta.** I quattro
> sotto-punti qui sopra sono stati **riverificati e reggono**: `event_log` non
> ha ancora nessun lettore. Ma «alerting e monitoring» erano **due cose in una
> riga**, e la seconda ha avuto il suo cantiere:
> [brief-db-sveglia-dei-processi](../work-done/brief-db-sveglia-dei-processi.md),
> ✅ **chiuso il 2026-09-07** su entrambi i lati — tre processi senza sveglia
> trovati e coperti, il registro dei processi, un ramo di installer che la prova
> non copriva. Resta la coda del suo §24.6.
> ⇒ **La vitalità dei PROCESSI è coperta; l'allarme sui DATI no.** Chi legge
> «🔴 non fatto» e va a costruire da zero rifà il primo pezzo: il substrato
> (registro, sveglia, identità) c'è, e quello che manca è la query su
> `event_log` più il canale d'uscita.

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

## 9. Il passo SDI: da oggi scrive, e nessuno legge (2026-08-05)

> 🟡 **SOSPESO per decisione di Tid**, non dimenticato. Arriva qui dal cantiere
> *bonifica dei riferimenti morti*
> ([brief-be-bonifica-riferimenti-morti](../work-done/brief-be-bonifica-riferimenti-morti.md) §1.2 e §6 item 2),
> che si chiude: la voce vive da qui in avanti in questa roadmap, perché è
> materia di fatturazione e non di bonifica.

**Cosa è cambiato.** `vendite.fn_prepare_sdi_payload` — passo `prepare_sdi_payload_lotto`
(registry id 9), montato sulle pipeline **MASSIVO (id 5)** e **GIORNALIERO (id 7)** —
**non è mai riuscito a girare**. Due difetti in serie: nominava la colonna
`tentativo` (che si chiama `tentativo_num`), e riparato quello il calcolo dava
`0` al primo giro con `force_new_tentativo = false` — cioè nella configurazione
in seed — violando `chk_fatture_sdi_tentativo_num CHECK (> 0)`. Riparata il
2026-08-04; verificato su un lotto reale: `false` → 1, `true` → 2.

**Cosa significa adesso.** Il passo gira per la prima volta, quindi le due
pipeline **scrivono** in `vendite.fatture_sdi` — che ad oggi ha **0 righe**,
prova che non ha mai funzionato prima. Ma a valle non c'è nessuno:

- il **builder XML FatturaPA non esiste** (il payload è preparato, il file no);
- l'executor della pipeline **scarta il valore di ritorno** del task;
- `vendite.fatture_sdi_eventi` resta da popolare.

Cioè: da oggi si accumulano righe di tentativo per un invio che nessuno effettua.
Non fa danno — il passo è idempotente per tentativo — ma è un dato che cresce
senza un consumatore, e il ciclo di vita del documento continua a fermarsi a
INVIATA/SDI come dicono gli item 1 e 2.

### ⚠️ Un residuo che arriva dal cantiere IVA, e che va raccolto QUI (2026-08-31)

Il cantiere IVA si è chiuso lasciando **una sola coda**, ed è di questo item:
la voce **`I5`** — *esigibilità e split payment nel payload SDI*.

⭐ **La metà DB è FATTA** (`20260829-54`): `vendite.fatture_righe.esigibilita` e
`split_payment` li riempie un **trigger** dal soggetto cliente, e il backend
**non li tocca** — deve restare così.
⛔ **Quel che manca è solo il trasporto**: il blocco `EsigibilitaIVA` della
FatturaPA, che non ha dove atterrare finché il builder non esiste.

⚠️ **E c'è un secondo blocco che aspetta lo stesso builder**: `DatiContratto`.
La tabella `vendite.fatture_atti` esiste (`20260831-25..27`) e porta lo
**snapshot** di numero, data, CIG, CUP e commessa; `fatture_righe.fattura_atto_id`
aggancia le righe. ⭐ Il blocco è ripetibile `0..N` con
`RiferimentoNumeroLinea`: per il generatore diventa una `SELECT`, non un
`GROUP BY` su testo — che è la forma scartata apposta.

📌 **E una terza cosa che il builder deve sapere**: una riga di fattura può
essere **spezzata** dal plafond di un titolo IVA (`riga_capofila_id`). Sono
**due `DettaglioLinee`**, per obbligo di formato — una riga FatturaPA porta una
sola `AliquotaIVA` e una sola `Natura`. La vista
`vendite.vw_fattura_righe_esposte` le espone già come **righe sorelle**
(`tipo_riga = 'PARTE_PLAFOND'`, entrambe a livello 0): chi genera l'XML legge
quella e non deve rifare il ragionamento.
⛔ Aggregarle produrrebbe **un solo** `DettaglioLinee`, cioè cancellerebbe la
ragione per cui la riga si è spezzata.

📌 Storia completa nei piani chiusi:
[Fase 3](../work-done/brief-be-fe-iva-fase-3-consumatori-risolutore.md) (`F4`) e
[brief madre](../work-done/brief-db-be-iva-risolutore-e-regime-cliente.md) (`I5`).

**Due cose già decise**, da non ridiscutere quando si riprenderà:

| Domanda | Decisione (2026-08-05) |
| --- | --- |
| `force_new_tentativo = false` deve restituire anche le fatture già registrate? | **No.** La semantica attuale è quella giusta per una pipeline: ciò che torna è ciò che va spedito. Il payload completo del lotto, se servirà, è una **funzione read-only separata** |
| Il passo va esercitato subito? | **No, sospeso**: senza builder XML si eserciterebbe una catena che non porta a nulla |

⚠️ **Un buco di copertura da sanare quando si riprende:** su
`fn_prepare_sdi_payload` **non esiste nessun pgTAP**. La funzione è rimasta rotta
per mesi senza che nulla lo segnalasse, ed è esattamente il tipo di silenzio che
un test avrebbe rotto al primo giro. Se il BE aggiunge un test d'integrazione
sulla pipeline, questo è il passo da includere per primo.

---

## 10. Preview di fatturazione del contratto (UI mancante) — verificato 2026-08-22

Assorbito da `sviluppo-fatturazione.md`, che conteneva **solo questo** ed è
stato tolto: due sedi sullo stesso argomento divergono al primo aggiornamento.
Nasce come promemoria **PROMO-1 del 2026-05-19**.

**Il buco.** Non esiste un punto in cui l'operatore veda, per un contratto
ATTIVO, *«sulla competenza di questo mese fatturerà queste righe, per un totale
di X»*. Il dato c'è nel motore — `vendite.fn_list_contratti_da_pushare` produce
un payload per riga × mese — e non c'è nessun componente che lo presenti.

**Che cosa è cambiato dal 2026-05-19, misurato oggi.**

- ⭐ **La condizione «quando affrontarlo» è caduta**: il promemoria diceva
  «probabilmente dopo il motore commesse, `HandlerContratti` è ancora uno
  scheletro vuoto». Non lo è più — è registrato e vivo in
  `commesse_service.py`. L'attesa è finita, il buco no.
- ⚠️ **Esiste una preview di contratto, ma risponde a un'altra domanda.**
  `/contratti/<id>/righe-preview/` è la preview di **pricing**: *quali righe si
  applicano e a che prezzo finale*. Quella che manca è di **fatturazione**:
  *che cosa esce, su quale competenza, per quanto*. Sono adiacenti — ed è
  proprio l'adiacenza che le rende facili da confondere: chi cerca la seconda
  trova la prima e crede che ci sia.

**Perché non è solo una comodità.** Oggi il drawer riga è l'unico posto in cui
l'utente vede la `quantita` di una riga di contratto, e questo pesa sulla
decisione UX aperta su `vendite.contratti_righe` (mostrare o nascondere
`quantita`, esporre `fonte_quantita_attesa`). Con una preview di fatturazione il
drawer riga potrebbe limitarsi alle **regole**, senza dover comunicare il
**totale periodico**. Riferimenti:
[refactor-contratti-fonte-quantita.md](../work-done/refactor-contratti-fonte-quantita.md),
[gestione-commesse-v2.md](../work-done/gestione-commesse-v2.md).

---

## 11. Integrità del giro: di chi è questo documento, adesso? (2026-09-09)

> 🟢 **DB COMPLETO, resta il frontend.** Non era nella review di febbraio, e non
> poteva esserci: nasce dall'uso del cockpit, quando un giro si è fermato e si è
> scoperto che nessuno sapeva dire **chi tenesse** un documento.

**La domanda unica.** Tre cantieri di settembre rispondono tutti alla stessa
cosa, ed è per questo che stanno in un item solo:

| Cantiere | Il pezzo di risposta |
| --- | --- |
| [uscita-documento-dal-giro](../work-done/brief-db-uscita-documento-dal-giro.md) | si può **togliere** un documento da un giro fermo, con la motivazione — invece di annullare tutto il lotto |
| [il marcatore scrive su un documento uscito](brief-db-il-marcatore-scrive-su-un-documento-uscito.md) | e una volta uscito **non si marca, non si conta, non blocca, non si racconta** — il tentativo uccideva il rilancio |
| [documento trattenuto da un lotto vivo](../work-done/brief-db-documento-trattenuto-da-un-lotto-vivo.md) | e finché un giro **vivo** lo tiene, non lo si offre a un secondo giro |

⭐ **La cosa che vale oltre questi tre**, e che è costata due riscritture di
perimetro: *il meccanismo che c'era misurava l'**esito** del lavoro, non il fatto
che il lavoro fosse **in corso**.* `EMESSA` dice «è andato», `LIBERA` dice «non è
mai partito» — mancava la terza, «è dentro un giro che non ha ancora finito».
È lo stesso buco che si presenta ogni volta che si guarda un risultato invece di
uno stato.

⚠️ **E il verdetto non si legge dall'esito.** `ultimo_esito` è muto in **entrambe**
le direzioni: `COMPLETED` su un lotto DRAFT è trattenuto, `ERRORE` su uno
ANNULLATO è libero. Si legge dallo **stato del lotto**, dal flag `is_abortito`
— ⛔ mai `congela_fiscale`, che su ANNULLATA vale `true`.

**Cosa resta**: il frontend. Riga non selezionabile, motivo da
`emissione_blocco_reason_key`, gesto «vai al lotto» da
`emissione_blocco_lotto_id`. ⚠️ Finché non arriva, i quattro campi sono
**dichiarati e non letti** — peggio della loro assenza, perché sembrano
presidiati.

### Voci vicine, che hanno casa altrove

Per non farne item e poi non trovarli più:

* **archiviazione delle righe di coda** — DB applicato il 04-09, chiuso su
  entrambi i lati ([brief](../work-done/brief-db-archiviazione-righe-code.md));
* **fan-out isolato ed esito parziale** — vive nel suo brief e nel collaudo in
  app; tocca l'item 5 (come il giro racconta com'è andato) più che questo.

---

## 🔎 Cosa è stato ricontrollato il 2026-09-09, e REGGE

⭐ Metà del lavoro di una riverifica è scoprire che il documento aveva ragione.
Se non si scrive, si ripaga daccapo — quindi si scrive, **col fatto datato**:

| Affermazione | Come è stata verificata | Esito |
| --- | --- | --- |
| `event_log` è **write-only** | otto file del backend lo nominano, **nessuno lo legge**; zero occorrenze nel frontend | ✅ regge — ed è ancora il perno degli item 5, 6 e 7 |
| item 2 — `contabilita` è uno schema vuoto | zero oggetti in `pg_class` | ✅ regge |
| item 8 — zero diagrammi di stato | ⚠️ e qui la prima misura mentiva: un `grep` ne trovava **due**, ma erano **questo file stesso** e `mermaid.min.js`. Diagrammi veri: **zero** | ✅ regge |
| item 9 — la pipeline prepara e nessuno spedisce | `vendite.fn_prepare_sdi_payload` scrive `fatture_sdi`, nessun lettore a valle | ✅ regge |

⚠️ **La riga dell'item 8 è la lezione della passata**: una misura che *conferma*
ciò che speravi va guardata due volte come una che lo smentisce. Lì per lì
sembrava una voce da aggiornare, ed era il grep a essere sbagliato.

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
| **P0** | **Ritorno a DRAFT (#1, metà rimasta)** | ⭐ **La nota di credito è uscita da questa riga il 2026-08-21**: esiste sui dati veri, con guardia di numerazione e arco N nel lineage (vedi §1). Resta la metà **pre**-numerazione: **2 fatture** uscite sbagliate sono irreparabili, **6 sono già DEFINITIVE**. È ancora l'unico item che *peggiora da solo* col passare del tempo |
| **P0** | **`correlation_id` sul push (#7)** | Il gap è isolato e misurato: `COMMESSE/TASK_RUN` a **0 su 196**. Poche righe, e senza di esso l'item 6 non ha da dove partire |
| **P0** | **Identità reale su `log_event` (#4)** | Resta un quick win, ma **va fatto davvero**: oggi `actor` dice sempre `service:django`. I GUC hanno già l'identità, basta passarla |
| **P1** | **Endpoint di lettura su `event_log`** *(nuovo)* | Non era nel documento di febbraio. Sblocca insieme «ultimo evento» (5a), «vista errori» vera (5b) e alerting (6), ed è ciò che serve allo strumento di consultazione log chiesto il 03/08 |
| **P1** | Riconciliazione incassi (#2) | Già misurata in [brief-incassi-riconciliazione-rate-promemoria.md](brief-incassi-riconciliazione-rate-promemoria.md): manca l'aggancio **rata↔incasso**. Ora che le rate esistono davvero, il buco è visibile |
| **P2** | Vista push + reset a step (#5, le due lacune) | Il resto della dashboard c'è; queste due restano e ora si chiedono in modo preciso |
| **P2** | Alerting (#6) | Dopo l'endpoint di lettura diventa piccolo: `job_liveness()` è il precedente, l'outbox email il canale |
| **P2** | Diagrammi di stato (#8) | Trasposizione, non analisi. Da fare **dopo** #1, così mostra anche la via d'uscita |
| **P3** | Esercizio fiscale (#3) | La parte normativa (numerazione) è coperta; questa serve al **primo bilancio**, non al primo ciclo |
| **P3** | Contabilità (#2) | Schema vuoto: è un modulo, non un item. Prima serve decidere se consuma eventi o vive nella pipeline |
| **P3** | **Preview di fatturazione del contratto (#10)** *(nuovo)* | Entrata il 22/08 assorbendo `sviluppo-fatturazione.md`. Non blocca nessun altro item e niente si rompe senza — ma **sblocca una decisione UX ferma** su `contratti_righe`, e la condizione che la teneva sospesa (motore commesse) è caduta. ⚠️ Da non confondere con `/righe-preview/`, che è la preview di *pricing* |

> ⚠️ **Nota del 2026-09-09 — l'ordine NON è stato rifatto**, ed è una scelta:
> ripianificare dieci voci per aggiornarne due produrrebbe un elenco nuovo di
> zecca e meno verificato di questo. Le due cose che chi lo legge deve sapere
> prima di sceglierne una:
>
> * **P2 «Alerting (#6)»** — la metà «vitalità dei **processi**» è coperta dal
>   cantiere chiuso il 07-09; quello che resta è l'allarme sui **dati**, e
>   dipende ancora dall'endpoint di lettura su `event_log` (P1). L'ordine regge,
>   la stima cala;
> * **item 11 (integrità del giro)** non entra in questo elenco perché il suo
>   lato DB è **finito**: quello che resta è frontend, e va nella coda del
>   frontend, non qui.
>
> ⛔ E una che NON è cambiata: la **#1 (ritorno a DRAFT)** è ancora l'unico item
> che *peggiora da solo*. Le voci nuove di settembre hanno tutte una causa
> esterna che le ha fatte emergere; questa no, e sta lì da febbraio.

### Voci uscite dall'elenco

| Item | Perché esce |
| --- | --- |
| ~~Scadenzario operativo (P1)~~ | ✅ **chiuso** 01-02/08/2026, collaudato 10/10 |
| ~~Dashboard (P3)~~ | 🟢 fatta col cockpit di luglio, salvo le due lacune promosse a P2 |
| ~~User_id «una riga di codice»~~ | ⚠️ non esce: **rientra come P0**, perché sembrava fatto e non lo era |
| ~~Note di credito (#1, metà)~~ | ✅ **chiusa 2026-08-21** — design, DB, BE e documento reale. La riga #1 resta viva per il **ritorno a DRAFT** |
| ~~Stati `STORNATA`/`RETTIFICATA`/`NOTA_CREDITO_EMESSA`~~ | ⛔ **decisione, non rinvio**: la natura sta sul documento nuovo; uno stato sulla fattura originale sarebbe una seconda verità accanto al legame di riga |

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