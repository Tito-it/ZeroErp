# WIP — Gestione Clienti v2: Subentro, Disdetta, Billing Account

> Stato: DA IMPLEMENTARE
>
> Data: aprile 2026
>
> Prerequisiti: [sviluppo-gestione-clienti.md (completato)](../work-done/sviluppo-gestione-clienti.md)
>
> Funzioni DB di riferimento:
>
> * [fn_subentro_cliente](/dbzero/script/funzioni/fn_subentro_cliente)
> * [fn_disdetta_cliente](/dbzero/script/funzioni/fn_disdetta_cliente)

---

## Contesto

La gestione clienti base (creazione manuale, CRUD, lista, drawer con contatti/indirizzi/conti a due livelli) e' completata. Restano da implementare le funzionalita' avanzate del ciclo di vita cliente e la gestione gerarchica dei billing account.

---

## 1. Billing Account — Gestione parent/child

### Stato attuale

Il modello DB supporta gia' `billing_account.parent_account_id` e il repository accetta il parametro in creazione. Tuttavia **non esiste una UI** per:

- Visualizzare la gerarchia parent/child di un billing account
- Assegnare o modificare il parent account
- Navigare tra parent e child account
- Creare un child account da un parent esistente

### Cosa serve

#### 1.1 — Backend: endpoint gerarchia BA

| # | Task | Dettaglio |
| --- | --- | --- |
| 1.1.1 | GET `/api/v1/anagrafiche/billing-accounts/{id}/` | Dettaglio BA con `parent` (dati parent) e `children` (lista child) |
| 1.1.2 | GET `/api/v1/anagrafiche/billing-accounts/{id}/children/` | Lista child BA paginata |
| 1.1.3 | PATCH `/api/v1/anagrafiche/billing-accounts/{id}/` | Modifica BA: assegnazione/rimozione parent, campi editabili |
| 1.1.4 | Lookup BA per autocomplete | GET con search su codice/descrizione per selezionare il parent — filtrato per stessa utility e stesso soggetto |
| 1.1.5 | Repository: metodi gerarchia | `get_billing_account_detail()`, `list_children()`, `update_billing_account()`, `lookup_billing_accounts()` |
| 1.1.6 | Test | Service + API test per creazione child, assegnazione parent, rimozione parent, lookup |

#### 1.2 — Frontend: UI gerarchia BA nel ClienteDrawer

| # | Task | Dettaglio |
| --- | --- | --- |
| 1.2.1 | Sezione BA espansa nel ClienteDrawer (edit) | Mostra: codice BA, parent account (link cliccabile), lista child account |
| 1.2.2 | Autocomplete parent account | Server-side autocomplete per assegnare un parent BA (filtrato per stessa utility) |
| 1.2.3 | Lista child accounts | DataTable compatta sotto la sezione BA con codice, descrizione, stato. Click apre il cliente associato |
| 1.2.4 | Pulsante "Crea child account" | Apre drawer creazione cliente pre-compilato con parent_account_id |

#### 1.3 — Regole di business

- Un BA child eredita l'utility dal parent
- Un BA puo' avere **un solo parent** ma **N child**
- La rimozione del parent non elimina il child, lo rende standalone
- Un BA con child non puo' essere eliminato (guard DB)
- Il parent deve appartenere allo stesso soggetto (o soggetto collegato — da definire con Tid)

---

## 2. Subentro cliente

### Cosa fa

Il subentro chiude il ciclo di un cliente su un'utility e ne apre uno nuovo per un soggetto diverso (o lo stesso con nuova istanza). E' il passaggio di titolarita' di un contratto/servizio.

### Funzione DB esistente

`script.fn_subentro_cliente` — esiste a livello DB, documentata ma **non esposta via API**.

### Cosa serve

#### 2.1 — Backend

| # | Task | Dettaglio |
| --- | --- | --- |
| 2.1.1 | Service: `subentro_cliente()` | Orchestrator che: valida il cliente esistente (deve essere attivo), chiama `fn_subentro_cliente` o equivalente logica Python, crea nuovo ciclo (istanza + BA + cliente) per il subentrante |
| 2.1.2 | Repository: metodi subentro | `close_cliente()` (chiude il cedente), `create_subentro()` (crea il subentrante con riferimento al predecessore) |
| 2.1.3 | Endpoint API | POST `/api/v1/anagrafiche/clienti/{id}/subentro/` — payload: `nuovo_soggetto_id`, dati opzionali indirizzo/BA |
| 2.1.4 | Validazioni | Il cliente cedente deve essere in stato AT (attivo). L'utility deve ammettere subentro. Il nuovo soggetto non deve avere gia' un cliente attivo sulla stessa utility/istanza |
| 2.1.5 | Test | Subentro standard, subentro con stesso soggetto (rinnovo), subentro con indirizzo diverso, guard su stati non ammessi |

#### 2.2 — Frontend

| # | Task | Dettaglio |
| --- | --- | --- |
| 2.2.1 | Pulsante "Subentro" nel ClienteDrawer | Visibile solo su clienti attivi. Apre un dialog/drawer di subentro |
| 2.2.2 | SubentroDialog o SubentroDrawer | Form: selezione nuovo soggetto (SoggettoResolver), indirizzo opzionale, dati BA opzionali. Conferma con dialog "Sei sicuro? Il cliente attuale verra' chiuso" |
| 2.2.3 | Dopo subentro | Aggiorna la lista, apre il drawer del nuovo cliente creato |

#### 2.3 — Regole subentro

- Solo utility con `richiede_pdp = true` passano per pratiche; le altre ammettono subentro manuale
- Il subentro crea un **nuovo ciclo completo**: nuova istanza (se fittizia), nuovo BA, nuovo record clienti
- Il cliente cedente passa in stato CH (chiuso) con `data_fine_validita` = oggi
- Il nuovo cliente ha `data_inizio_validita` = oggi
- Tracciabilita': il record del nuovo cliente dovrebbe avere un riferimento al predecessore (campo `cliente_predecessore_id` o equivalente — verificare se esiste nel modello DB, altrimenti aggiungerlo)

---

## 3. Disdetta cliente

### Cosa fa

La disdetta chiude il rapporto cliente su un'utility senza creare un successore. Il cliente passa da attivo a chiuso.

### Funzione DB esistente

`script.fn_disdetta_cliente` — esiste a livello DB, documentata ma **non esposta via API**.

### Cosa serve

#### 3.1 — Backend

| # | Task | Dettaglio |
| --- | --- | --- |
| 3.1.1 | Service: `disdetta_cliente()` | Valida stato cliente (deve essere AT), esegue chiusura con data fine, aggiorna stato a CH |
| 3.1.2 | Repository: `close_cliente()` | UPDATE clienti SET stato=CH, data_fine_validita, motivo_chiusura. Potrebbe richiamare `fn_disdetta_cliente` se contiene logica aggiuntiva (cascata su istanza/BA) |
| 3.1.3 | Endpoint API | POST `/api/v1/anagrafiche/clienti/{id}/disdetta/` — payload: `motivo` (opzionale), `data_effetto` (default oggi) |
| 3.1.4 | Validazioni | Solo clienti in stato AT. Verificare se ci sono BA child attivi — se si', bloccare o forzare chiusura cascata |
| 3.1.5 | Test | Disdetta standard, disdetta con data futura, guard su stati non ammessi, guard su child attivi |

#### 3.2 — Frontend

| # | Task | Dettaglio |
| --- | --- | --- |
| 3.2.1 | Pulsante "Disdetta" nel ClienteDrawer | Visibile solo su clienti attivi. Colore danger |
| 3.2.2 | Dialog conferma disdetta | "Il cliente verra' chiuso. Questa azione non e' reversibile." + campo motivo opzionale + data effetto (default oggi) |
| 3.2.3 | Dopo disdetta | Aggiorna il drawer (stato CH, campi in readonly), aggiorna la lista |

#### 3.3 — Regole disdetta

- La disdetta e' ammessa sia per utility con `richiede_pdp = false` (manuale) sia per quelle con `richiede_pdp = true` (se gestita fuori pratica, da valutare)
- La chiusura del cliente puo' propagarsi all'istanza e al BA (dipende dalla logica in `fn_disdetta_cliente`)
- Se il BA ha child attivi, la disdetta del parent deve essere bloccata o deve forzare la chiusura dei child (decisione architetturale da prendere)

---

## 4. Permessi e azioni processo

### Stato attuale

Gli endpoint clienti usano `DomainAPIView` con `ZeroERPPermission` sull'area `anagrafiche`, ma **non sono state definite azioni processo specifiche** per le operazioni avanzate.

### Cosa serve

| # | Task | Dettaglio |
| --- | --- | --- |
| 4.1 | Seed azioni processo | `anagrafiche.crea_cliente`, `anagrafiche.modifica_cliente`, `anagrafiche.disattiva_cliente`, `anagrafiche.subentro_cliente`, `anagrafiche.disdetta_cliente` |
| 4.2 | Backend: decorare endpoint con azioni | `post_permission` / `get_permission` sulle view per subentro e disdetta |
| 4.3 | Frontend: `useActionPermission` sui pulsanti | Pulsanti Subentro e Disdetta visibili solo se l'operatore ha il permesso |

---

## 5. Documentazione API mancante

| # | Task | Dettaglio |
| --- | --- | --- |
| 5.1 | Creare `docs/it/backend/anagrafiche/manual/api_clienti.md` | Documentazione endpoint clienti (lista, dettaglio, creazione, modifica) |
| 5.2 | Aggiornare dopo subentro/disdetta | Aggiungere endpoint subentro e disdetta |
| 5.3 | Aggiornare dopo BA parent/child | Aggiungere endpoint gerarchia BA |

---

## Priorita' suggerita

| # | Funzionalita' | Priorita' | Motivazione |
| --- | --- | --- | --- |
| 1 | Billing Account parent/child | **ALTA** | Necessario per clienti multi-contratto, manca completamente la UI |
| 2 | Disdetta | **MEDIA** | Operazione semplice, alto valore operativo |
| 3 | Subentro | **MEDIA** | Piu' complesso, ma essenziale per il ciclo di vita |
| 4 | Permessi | **BASSA** | Puo' seguire dopo il primo rilascio funzionale |
| 5 | Documentazione API | **BASSA** | Da completare progressivamente |

---

*WIP — Gestione Clienti v2 — ZeroERP (aprile 2026)*
