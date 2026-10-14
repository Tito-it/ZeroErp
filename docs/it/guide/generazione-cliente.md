# Guida — Generazione di un Cliente

> **Ultimo aggiornamento**: 14 ottobre 2026
>
> **Destinatari**: sviluppatori database, backend e analisti funzionali
>
> **Vedi anche** — schemi DB:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la persona o azienda
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — i ruoli del soggetto (es. CLIENTE)
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — il ciclo di servizio su un indirizzo
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — l'account di fatturazione
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — il record cliente
> * [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp) — il punto di prelievo (contatore/allaccio)
> * [anagrafiche.catasto_unita_immobiliari](/dbzero/anagrafiche/tabelle/catasto_unita_immobiliari) — i dati catastali
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — l'indirizzo civico
> * [config.utilities](/dbzero/config/tabelle/utilities) — il tipo di servizio (GAS, ENERGIA, …)
> * [config.stati_cliente](/dbzero/config/tabelle/stati_cliente) — gli stati del cliente (AT, CH, AN, …)
>
> **Vedi anche** — funzioni DB:
>
> * [script.fn_subentro_cliente](/dbzero/script/funzioni/fn_subentro_cliente) — chiude il cliente precedente sul punto di prelievo
> * [script.fn_disdetta_cliente](/dbzero/script/funzioni/fn_disdetta_cliente) — la cessazione senza subentro
>
> **Vedi anche** — guide correlate:
>
> * [Glossario termini utility](/glossario/glossario-utility) — PDP, istanza, billing account e gli altri termini ricorrenti
> * [Soggetti e Ruoli](/guide/soggetti-e-ruoli-anagrafici) — il modello anagrafico su cui poggia il cliente
> * [Gestione delle Istanze Utility](/guide/gestione-delle-istanze-utility) — il ciclo di vita dell'istanza
> * [Termini di pagamento](/guide/termini-di-pagamento) — il catalogo delle condizioni di pagamento

---

## Introduzione

In Zero ERP un **cliente** non e semplicemente una persona: e l'insieme di informazioni che collegano un soggetto (la persona o azienda) a un servizio e ai dati necessari per fatturare.

Questa guida spiega **come nasce un cliente** — quali entita creare, in che ordine, e perche il modello e fatto cosi. La logica e la stessa sia per una prima attivazione, sia per un subentro (cambio di intestatario), sia per una riattivazione dopo una cessazione.

**Cosa troverai in questa guida:**

* Le entita coinvolte e il loro ruolo nel processo
* La sequenza obbligatoria di creazione (cosa si crea prima e cosa dopo)
* Come funzionano i flussi di subentro e disdetta
* Le garanzie di sicurezza offerte dal database (transazioni, vincoli)

### Il modello e generico, non solo per le utility

La struttura descritta in questa guida (soggetto → istanza → billing account → cliente) **funziona per qualsiasi tipo di azienda**, non solo per il settore utility. L'istanza e un ponte trasparente tra il soggetto e la fatturazione: in contesti non-utility (commercio, servizi, gestione pompe funebri, ecc.) viene creata automaticamente come contenitore tecnico senza che l'utente debba occuparsene.

Le funzionalita specifiche del mondo utility — PDP (contatore), catasto, subentro, disdetta — sono **estensioni opzionali** che si attivano solo quando servono. La struttura base permette la fatturazione a prescindere dal modello di business, anche dove non esiste una parte contrattualistica complessa.

In pratica:

* **Azienda utility**: soggetto → istanza (con PDP, catasto, subentro) → BA → cliente
* **Azienda non-utility**: soggetto → istanza (generata in trasparenza, senza PDP ne catasto) → BA → cliente

Gli esempi in questa guida usano spesso il dominio utility perche e il caso piu articolato, ma le regole di base (sequenza di creazione, vincoli, transazionalita) valgono per tutti.

---

## Le entita e il loro significato

### Soggetto

E la persona fisica o giuridica registrata nel sistema. Puo avere piu ruoli (cliente, fornitore, ecc.) e piu utenze attive contemporaneamente su servizi diversi. Il soggetto **esiste prima e indipendentemente** dal contratto.

### Istanza utility

E il **ciclo tecnico-commerciale** di un servizio su un indirizzo per un soggetto. In pratica: quando un servizio gas o energia viene collegato a un civico per conto di una persona, nasce un'istanza.

L'istanza **non e il cliente**: precede il contratto (puo esistere in fase precontrattuale) e sopravvive alla chiusura del rapporto come record storico. Ma non esiste mai da sola: **nasce insieme al suo billing account** (vedi [Ogni istanza nasce col suo billing account](/guide/gestione-delle-istanze-utility#ogni-istanza-nasce-col-suo-billing-account)).

**Perche l'istanza e legata al soggetto e non al ruolo?**
Perche l'istanza identifica semplicemente "chi" e associato a un certo indirizzo/servizio, e sopravvive al rapporto commerciale. Il ruolo CLIENTE nasce con l'istanza, perche il billing account che nasce con lei fattura a quel ruolo; il **cliente** — la specializzazione in `clienti`, con le sue date — arriva dopo, con il contratto.

Un soggetto puo non acquisire mai il ruolo CLIENTE: per esempio un soggetto che e solo fornitore. In quel caso non ha nemmeno istanze.

### Billing account (BA)

E l'account di fatturazione. Identifica **a chi fatturare** e **con quale codice**. Nasce **insieme all'istanza**, nella stessa operazione, e prima del cliente: esiste gia nella fase precontrattuale (preventivi, offerte) e viene "ereditato" dal cliente alla firma del contratto. Il suo codice si genera quando nasce.

Il BA supporta una gerarchia padre/figlio per aggregare la fatturazione di piu utenze sullo stesso intestatario. Vedi la [documentazione dedicata](/dbzero/anagrafiche/manual/billing_account) per i dettagli.

> **Invariante BA ↔ istanza (1:1 per utility).** Per una data utility, un
> billing account ha **una sola** istanza e un'istanza ha **un solo** BA
> (`billing_account.istanza_utility_id` FK NOT NULL + UNIQUE
> `(istanza_utility_id, utility_id)`). Quindi **dato il BA, l'istanza e'
> univoca**: i documenti che hanno gia' un BA (ordini, DDT, fatture) ricavano
> l'istanza dal BA e non la memorizzano; i precontrattuali
> (preventivi/offerte/contratti) scelgono l'istanza e la portano sulla propria
> testata accanto al BA, e il database pretende che il BA sia quello della
> coppia (istanza, utility). Dettaglio:
> [Gestione Istanze Utility — Istanza e billing account](/guide/gestione-delle-istanze-utility#istanza-e-billing-account-relazione-11-per-utility-invariante).

### Cliente

E la specializzazione commerciale dell'istanza. Nasce quando il soggetto firma il contratto e lega insieme:

* l'istanza (dove e cosa)
* il billing account (a chi fatturare)
* il ruolo CLIENTE del soggetto (chi)
* le date commerciali (da quando a quando)

### PDP (Punto Di Prelievo)

E l'entita fisica che rappresenta il contatore o allaccio a un indirizzo. Il PDP ha un proprio stato tecnico (ATTIVO, DISPONIBILE) che cambia in automatico quando un cliente si attiva o si chiude. Non tutti i clienti hanno un PDP (le istanze possono essere "fittizie"), ma quando c'e un PDP, esso diventa il perno del vincolo di unicita: **un solo cliente attivo per PDP**.

---

## Sequenza obbligatoria di creazione

La creazione di un cliente segue un ordine preciso, imposto dai vincoli del database. Non e possibile saltare passaggi.

### Ordine dei passi

```text
1. Soggetto       (deve gia esistere)
2. Ruolo CLIENTE  (creato automaticamente se manca, tramite fn_get_or_create_soggetto_ruolo)
3. Istanza        (richiede soggetto_id NOT NULL)
4. Billing Account (richiede istanza_utility_id NOT NULL e soggetto_ruolo_id NOT NULL)
5. Cliente        (richiede istanza_utility_id, billing_account_id e soggetto_ruolo_id NOT NULL)
```

### Perche questo ordine?

Ogni entita dipende dalla precedente tramite chiavi esterne obbligatorie:

| Non si puo creare... | ...senza prima aver creato... | Motivo                                                       |
| -------------------- | ----------------------------- | ------------------------------------------------------------ |
| Istanza              | Soggetto                      | `soggetto_id NOT NULL`                                       |
| Billing Account      | Istanza                       | `istanza_utility_id NOT NULL`                                |
| Cliente              | Istanza + BA                  | `istanza_utility_id NOT NULL`, `billing_account_id NOT NULL` |
| Cliente              | Ruolo CLIENTE                 | `soggetto_ruolo_id NOT NULL`                                 |

La FK composita `(billing_account_id, istanza_utility_id)` su `clienti` garantisce inoltre che il billing account appartenga alla stessa istanza del cliente.

### Flusso pre-contrattuale vs attivazione diretta

**Pre-contrattuale** (il contratto arriva dopo):

```text
Soggetto → Ruolo CLIENTE + Istanza + Billing Account → [pausa, anche indefinita] → Cliente
```

La pausa sta **dopo il billing account**: istanza, ruolo CLIENTE e billing
account nascono insieme, nella stessa operazione, e possono restare cosi a
lungo — e il tempo dei preventivi e delle offerte. Un'istanza senza billing
account non e uno stato ammesso: il database la rifiuta (vedi [Ogni istanza
nasce col suo billing account](/guide/gestione-delle-istanze-utility#ogni-istanza-nasce-col-suo-billing-account)).
Cio che puo arrivare dopo, o non arrivare mai, e il **cliente**: il contratto.

**Attivazione diretta** (il contratto c'e gia):

```text
Soggetto + Ruolo CLIENTE → Istanza → Billing Account → Cliente
```

In entrambi i casi istanza e billing account nascono nella **stessa transazione**: non e un consiglio, il database lo pretende. Il cliente puo nascere nella stessa transazione (attivazione diretta) o dopo, col contratto.

### Orchestrazione automatica

Per evitare che il frontend debba gestire manualmente tutti questi passi, e previsto un **orchestrator Django** (`ClienteService`) che incapsula l'intera sequenza in una singola chiamata API. L'orchestrator:

* valida il soggetto
* crea (o recupera) il ruolo CLIENTE
* nel caso di subentro, chiude il cliente precedente
* crea l'istanza
* crea il billing account
* crea il cliente con stato ATTIVO

Tutto avviene in una transazione atomica: se un passo fallisce, nessuna modifica viene salvata.

### Creazione manuale vs creazione da pratica

Il sistema supporta due modalita di creazione del cliente, governate dal flag `config.utilities.richiede_pdp`:

| `richiede_pdp` | Modalita                 | Istanza         | Indirizzo    | Esempio utility         |
| -------------- | ------------------------ | --------------- | ------------ | ----------------------- |
| `false`        | Manuale (da interfaccia) | Sempre fittizia | Facoltativo  | Manifatturiero, servizi |
| `true`         | Solo via pratiche        | Reale (con PDP) | Obbligatorio | GAS, Energia, Idrico    |

**Creazione manuale** (`richiede_pdp = false`):

L'operatore crea il cliente direttamente dall'interfaccia. Il `ClienteService` genera in trasparenza l'istanza fittizia, il billing account e il record cliente in una transazione atomica. L'operatore puo facoltativamente collegare un indirizzo del soggetto all'istanza, ma non e obbligatorio. L'istanza resta fittizia in entrambi i casi perche non rappresenta un punto di erogazione fisico.

**Creazione da pratica** (`richiede_pdp = true`):

Per utility con ciclo tecnico complesso (contatore, allaccio, verifica fisica), la creazione del cliente passa obbligatoriamente dal motore pratiche. L'istanza e reale, collegata a un indirizzo e a un PDP, e il flusso include step di verifica e approvazione.

> **Nota architetturale**: il flag `richiede_pdp` e il discriminante unico per le due modalita. Se in futuro servira un'utility senza PDP che richiede comunque il workflow pratiche, bastera aggiungere un boolean `solo_pratica` su `config.utilities`; l'ipotesi e gia stata annotata nell'analisi interna sulla gestione clienti.

---

## Flusso operativo step-by-step

### 1. Creazione dell'istanza

Ogni cliente nasce da un'**istanza di servizio**. L'istanza puo essere:

* **reale** (`fittizia = FALSE`): associata a un indirizzo e, opzionalmente, a un PDP
* **fittizia** (`fittizia = TRUE`): senza indirizzo obbligatorio, utile per servizi che non richiedono un punto fisico

Se c'e un PDP, l'istanza eredita automaticamente indirizzo e utility dal PDP, e non puo essere fittizia.

### 2. Creazione del billing account

Il BA viene sempre associato all'istanza (`istanza_utility_id NOT NULL`) e a un ruolo soggetto, e nasce **nella stessa operazione** dell'istanza: un'istanza senza billing account non esiste. Esiste gia **prima del cliente** (fase precontrattuale). L'istanza e la utility di un BA non si cambiano dopo la nascita.

Il campo `codice` (l'account di fatturazione vero e proprio) viene generato automaticamente dal trigger `trgfn_billing_account_gen_codice` se non specificato.

### 3. Creazione del cliente

Il record in `anagrafiche.clienti` lega tutte le entita precedenti:

* `istanza_utility_id` → quale servizio
* `billing_account_id` → a chi fatturare
* `soggetto_ruolo_id` → chi e il cliente
* `stato_cliente_id` → in che stato si trova (tipicamente ATTIVO alla creazione)
* `data_attivazione` → da quando e attivo

Sulla scheda cliente vivono anche le **condizioni di pagamento** predefinite —
vedi il paragrafo successivo.

I trigger sulla tabella clienti si occupano automaticamente di:

* normalizzare il `periodo` commerciale (daterange calcolato da `data_attivazione` e `data_chiusura`)
* allineare `pdp_id` e `utility_id` dall'istanza e dal billing account
* aggiornare lo stato del PDP (ATTIVO quando il cliente si attiva, DISPONIBILE quando si chiude)
* mantenere la catena `parent_istanza_id` per la tracciabilita dei subentri

### 3-bis. Le condizioni di pagamento del cliente

Il cliente porta **due riferimenti a catalogo**, entrambi facoltativi:

* `termine_pagamento_id` — **quando** e in quante rate si paga;
* `modalita_pagamento_id` — **come** si paga (bonifico, RID, …).

Sono riferimenti, non numeri liberi: la condizione vera vive nel catalogo dei
[termini di pagamento](/guide/termini-di-pagamento), e il cliente si limita a
sceglierne uno.

> ⚠️ **Se si trova codice o documentazione che nomina `tipo_gg_scadenza_ft` e
> `nr_giorni_scadenza`, è anteriore alla riforma**: erano i due campi liberi che
> dicevano la stessa cosa del termine, in un altro modo. Quelle colonne non
> esistono più — due modi di dire la stessa cosa possono dirla diversa, e non
> c'era regola che dicesse quale vincesse. Chi ha condizioni particolari usa un
> termine dedicato a catalogo.

Due conseguenze pratiche:

* **Lasciare il termine vuoto è legittimo.** Se il cliente non ne ha uno, la
  fatturazione applica «unica rata». Non serve riempirlo per forza.
* **Il termine non è solo un dato anagrafico**: entra nei criteri con cui il
  lavoro si raggruppa, quindi cambiare il termine di un cliente può cambiare
  **quante fatture** riceverà. Il perché sta in
  [Termini di pagamento §4](/guide/termini-di-pagamento).

### 4. Dati catastali

I dati catastali (foglio, particella, subalterno, categoria, rendita) sono legati all'istanza tramite `catasto_unita_immobiliare_id`. Il collegamento tra catasto e indirizzo civico avviene tramite la tabella ponte `catasto_unita_immobiliari_indirizzi`, mantenuta in automatico dal trigger `trgfn_iu_sync_catasto_unita_indirizzo`.

Tre regole fondamentali del catasto:

* **Clone, mai condivisione**: nel subentro il catasto viene duplicato. Ogni istanza ha il proprio record indipendente; modificare il catasto di un'istanza non tocca le altre
* **Sorgente unica**: la clonazione cerca il catasto solo nella parent istanza diretta (`parent_istanza_id`). Se il parent non ha catasto, il flusso prosegue senza errore
* **Tabella ponte**: il legame catasto ↔ indirizzo e N:M e viene creato automaticamente. La stessa unita catastale puo essere associata a piu indirizzi e viceversa

Per il flusso completo dei trigger di clonazione e tutti i dettagli: [Architettura catasto](/dbzero/anagrafiche/manual/catasto-architettura).

---

## Vincoli e regole di coerenza

### Regola fondamentale: un cliente attivo per PDP

Per ciascun PDP puo esistere **al massimo un cliente attivo**. Questo vincolo e implementato dall'indice di esclusione `ex_clienti_no_overlap_stesso_pdp` che opera su `(pdp_id, periodo)`.

**Attenzione**: il vincolo opera **per PDP**, non per indirizzo. Sullo stesso indirizzo possono coesistere clienti attivi di utility diverse. Esempio: un appartamento puo avere contemporaneamente un cliente GAS attivo e un cliente ENERGIA attivo, perche sono due PDP distinti.

### Multi-utility e soggetto con piu istanze

Il vincolo "un solo cliente attivo" opera **per PDP**, non per indirizzo. Sullo stesso civico possono coesistere clienti attivi di utility diverse (GAS + ENERGIA), ciascuno con la propria istanza e il proprio billing account, ma tutti collegati allo stesso soggetto e allo stesso ruolo CLIENTE.

Per gli esempi dettagliati e le casistiche: [Guida Gestione Istanze Utility – Multi-utility](/guide/gestione-delle-istanze-utility#multi-utility-sullo-stesso-indirizzo).

### Altri vincoli

* Se `fittizia = FALSE`, allora `indirizzo_dettaglio_id` deve essere NOT NULL
* Se `pdp_id` e valorizzato, l'istanza non puo essere fittizia
* `utility_id` su `clienti` deve essere coerente con `billing_account.utility_id` (mantenuto in automatico dal trigger)
* Un cliente non puo esistere senza istanza e senza billing account

---

## L'emittente del cliente — si sceglie una volta

Il legame cliente → emittente nasce **qui**, automaticamente: non c'è nessun passaggio in cui si
sceglie, ed è il motivo per cui vale la pena saperlo prima di creare il primo cliente.

### Nasce da solo, e prende l'emittente di chi sta creando

Nel momento in cui il billing account viene creato, un trigger lo aggancia
all'**emittente dell'operatore corrente**. Non c'è un passaggio in cui il
cliente esiste «senza emittente»: nasce già agganciato.

⚠️ **Conseguenza pratica da conoscere**: se l'operatore sta lavorando
sull'emittente sbagliato, il cliente **nasce sbagliato**. È un errore di
inserimento ordinario, e va corretto subito.

### Perché «subito» non è un modo di dire

Un documento già emesso porta con sé chi lo ha emesso, e **non lo cambia mai**.
Spostare il cliente su un altro emittente non riscrive quei documenti: li
lascia dove sono. Da quel momento chi li ha emessi continua a vedere i documenti
e **smette di vedere il cliente** a cui si riferiscono.

⇒ Per questo il legame si può cambiare **finché sul cliente non è passato del
lavoro** — nessuna fattura, nessuna commessa — e non più dopo. Il controllo che
lo impone è
[`anagrafiche.fn_guard_ba_cambio_emittente`](/dbzero/anagrafiche/manual/fn_guard_ba_cambio_emittente),
e il messaggio che restituisce dice **quante** fatture e **quante** commesse
stanno bloccando.

### E se il cliente è passato davvero all'altro emittente?

Allora non si sposta: **si apre presso il nuovo emittente una fornitura nuova**.
I documenti già emessi restano con chi li ha emessi, il cliente resta lo stesso
soggetto, e le due posizioni convivono.

⚠️ Non esiste un «cliente gemello» sulla stessa fornitura, e non è una
dimenticanza: un indice univoco lo vieta — per una istanza di utility c'è **un**
billing account e uno solo.

### ⚠️ E l'albero dei clienti si muove tutto insieme

Padre e figli devono stare sullo **stesso** emittente. Agganciare un cliente a un
padre di un altro emittente, o spostare l'emittente di un solo nodo, viene
respinto: vedi
[`anagrafiche.fn_guard_albero_ba_emittente`](/dbzero/anagrafiche/manual/fn_guard_albero_ba_emittente).

---

## Trigger e funzioni coinvolte nella creazione

### Ordine di esecuzione (visione rapida)

```text
INSERT istanza
  ├─ gen_codice         → genera codice istanza
  ├─ normalize          → normalizza campi, verifica coerenze
  ├─ tx_id + audit      → tracciabilita e metadati
  │
INSERT billing_account
  ├─ gen_codice         → genera codice account
  ├─ guard_normalize    → validazioni e normalizzazione BA
  ├─ tx_id + audit
  │
INSERT cliente
  ├─ set_parent_istanza → collega alla parent istanza (catena subentri)
  ├─ set_periodo        → calcola periodo [attivazione, chiusura)
  ├─ sync_pdp           → allinea pdp_id dall'istanza
  ├─ sync_utility       → allinea utility_id dal BA
  ├─ sync_stato_pdp     → PDP diventa ATTIVO
  ├─ tx_id + audit + storico
```

### Dettaglio completo

| Trigger / Funzione                      | Quando scatta                    | Cosa fa                                             |
| --------------------------------------- | -------------------------------- | --------------------------------------------------- |
| `trgfn_istanze_utilities_gen_codice`    | INSERT su istanze                | Genera il codice automatico dell'istanza            |
| `trgfn_istanze_utilities_normalize`     | INSERT/UPDATE su istanze         | Normalizza campi e verifica coerenze                |
| `trgfn_billing_account_gen_codice`      | INSERT su billing_account        | Genera il codice dell'account                       |
| `trgfn_billing_account_guard_normalize` | INSERT/UPDATE su billing_account | Guard e normalizzazione BA                          |
| `trgfn_clienti_set_periodo`             | INSERT/UPDATE su clienti         | Calcola `periodo` da date attivazione/chiusura      |
| `trgfn_clienti_set_parent_istanza`      | INSERT su clienti                | Imposta la catena `parent_istanza_id`               |
| `trgfn_clienti_sync_pdp`                | INSERT/UPDATE su clienti         | Allinea `pdp_id` dall'istanza                       |
| `trgfn_clienti_sync_utility_from_ba`    | INSERT/UPDATE su clienti         | Allinea `utility_id` dal billing account            |
| `trgfn_clienti_sync_stato_pdp`          | INSERT/UPDATE su clienti         | Aggiorna stato PDP (AT→ATTIVO, CH→DISPONIBILE)      |
| `dbops.trgfn_tx_id_managed`             | INSERT/UPDATE su tutte           | Genera `tx_id` per tracciabilita transazionale      |
| `script.trgfn_audit_data_user_generic`  | INSERT/UPDATE su tutte           | Aggiorna campi audit (`data_update`, `user_update`) |
| `script.trgfn_storico_generic`          | UPDATE/DELETE su tutte           | Snapshot storico del record modificato              |

---

## Garanzia transazionale

Tutte le operazioni descritte in questa guida (creazione istanza, BA, cliente, e i trigger che scattano in cascata) avvengono all'interno di una **singola transazione PostgreSQL**.

Cosa significa in pratica:

* Se un qualsiasi trigger della catena fallisce (es. vincolo violato, dato mancante), **tutte le operazioni vengono annullate** (rollback atomico)
* **Non esistono stati parziali**: o tutto va a buon fine, o nulla viene modificato
* Questo vale anche per le catene complesse del subentro (4-5 trigger in cascata)

Questa garanzia e offerta nativamente dal motore PostgreSQL e non richiede codice aggiuntivo.

---

## Appendice – Subentro cliente

Il **subentro** (o voltura) e il passaggio di titolarita su un PDP: un cliente esce, un altro entra sullo stesso punto di prelievo.

## Cosa fa `fn_subentro_cliente`

La funzione [`script.fn_subentro_cliente`](/dbzero/script/funzioni/fn_subentro_cliente) si occupa **esclusivamente della chiusura del cliente precedente**: una chiamata con il punto di prelievo e la data di attivazione del nuovo ([esempio](#area-tecnica-esempi)).

Effetti:

* Individua il cliente attivo piu recente sul PDP
* Imposta `data_chiusura = p_data_attivazione_nuovo - 1 giorno`
* Imposta `stato_cliente = CH` (chiuso)
* Se non esiste alcun cliente attivo → ritorna NULL (prima attivazione)
* I trigger aggiornano in automatico il `periodo` e lo stato del PDP

**La funzione non crea** la nuova istanza, il nuovo billing account e il nuovo cliente. Questi passi sono a carico del chiamante (frontend, API o orchestrator Django). La sequenza completa e:

1. `fn_subentro_cliente(pdp_id, data)` → chiude il precedente
2. INSERT istanza → INSERT billing account → INSERT cliente → attiva il nuovo

Tutti questi passi vanno eseguiti nella stessa transazione.

## Catena trigger del subentro

Quando si crea un nuovo cliente sullo stesso PDP dopo la chiusura del precedente, scatta una catena di trigger:

**Passo 1** — `trgfn_clienti_set_parent_istanza` (BEFORE INSERT su clienti)
Cerca l'istanza precedente sullo stesso PDP e imposta `parent_istanza_id` sulla nuova istanza. Questo mantiene la catena storica dei subentri.

**Passo 2** — `trgfn_iu_clone_catasto_from_parent` (AFTER UPDATE su istanze)
Quando `parent_istanza_id` viene impostato e la nuova istanza non ha ancora un catasto, clona i dati catastali dall'istanza precedente. Il catasto non e mai condiviso: viene sempre duplicato.

**Passo 3** — `trgfn_iu_sync_catasto_unita_indirizzo` (AFTER INSERT/UPDATE su istanze)
Inserisce automaticamente il legame tra il catasto clonato e l'indirizzo nella tabella ponte `catasto_unita_immobiliari_indirizzi`.

**Passo 4** — `trgfn_clienti_sync_stato_pdp` (AFTER INSERT/UPDATE su clienti)
Aggiorna lo stato del PDP: ATTIVO per il nuovo cliente.

Tutti questi trigger avvengono nella stessa transazione. Se uno fallisce, tutto viene annullato (vedi sezione "Garanzia transazionale").

## Funzioni e trigger coinvolti nel subentro

* [`anagrafiche.trgfn_clienti_set_parent_istanza`](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_parent_istanza)
* [`anagrafiche.trgfn_iu_clone_catasto_from_parent`](/dbzero/anagrafiche/funzioni/trgfn_iu_clone_catasto_from_parent)
* [`anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo`](/dbzero/anagrafiche/funzioni/trgfn_iu_sync_catasto_unita_indirizzo)
* [`script.fn_subentro_cliente`](/dbzero/script/funzioni/fn_subentro_cliente)
* [`script.fn_get_catasto_source_by_istanza`](/dbzero/script/funzioni/fn_get_catasto_source_by_istanza)
* [`script.fn_clone_catasto_from_parent_by_istanza`](/dbzero/script/funzioni/fn_clone_catasto_from_parent_by_istanza)

---

## Appendice – Disdetta (cessazione senza subentro)

La **disdetta** e la chiusura del servizio senza che un nuovo intestatario subentri. Il cliente disdice, il PDP torna disponibile per future attivazioni.

## Cosa fa `fn_disdetta_cliente`

La funzione [`script.fn_disdetta_cliente`](/dbzero/script/funzioni/fn_disdetta_cliente) incapsula la cessazione ([esempio](#area-tecnica-esempi)).

Effetti:

* Verifica che `p_data_cessazione >= data_attivazione` del cliente
* Da quale stato si può chiudere lo decide il percorso degli stati del cliente: attivo e sospeso
  sì, un cliente già chiuso, annullato o pre-contrattuale no ([Gli stati del cliente](/guide/gestione-delle-istanze-utility#gli-stati-del-cliente-e-le-loro-date))
* Imposta `data_chiusura = p_data_cessazione`
* Imposta `stato_cliente = CH` (chiuso)
* Ritorna l'`id` del cliente chiuso

I trigger si occupano automaticamente di:

* Ricalcolare il `periodo` commerciale → `[data_attivazione, data_cessazione)`
* Aggiornare lo stato PDP → **DISPONIBILE**, se dalla data di oggi nessun altro cliente lo occupa
* Storicizzare il record e aggiornare i campi audit

## Policy sul billing account dopo la disdetta

Il billing account **non viene toccato** dalla disdetta. Resta attivo per consentire:

* Emissione di fatture finali
* Conguagli e riconciliazioni

Il billing account di un cliente chiuso **non si riattiva**: un cliente chiuso non si riapre
(decisione del 2026-10-13). Se la fornitura riparte, nasce una catena nuova — istanza, billing
account e cliente nuovi, collegata alla precedente — come nel subentro. Vedi
[Gestione delle istanze utility — Chiusura del cliente](/guide/gestione-delle-istanze-utility#5-chiusura-del-cliente).

La chiusura del billing account (tramite `valido_al`) e un'operazione separata, da eseguire solo quando tutti i documenti fiscali sono stati emessi e le partite aperte sono chiuse.

## Cosa succede all'istanza dopo la disdetta

L'istanza non ha un campo "stato" proprio. La sua "chiusura" e implicita: se il suo unico cliente e in stato CH (chiuso), l'istanza e considerata storica. Resta nel database come record per:

* Tracciabilita delle precedenti attivazioni
* Riferimento per eventuali futuri subentri sullo stesso PDP
* Base per la catena `parent_istanza_id`

## Differenza tra subentro e disdetta

|              | Subentro                                                             | Disdetta                              |
| ------------ | -------------------------------------------------------------------- | ------------------------------------- |
| Cosa succede | Un cliente esce, un altro entra                                      | Il cliente esce, nessuno entra        |
| PDP dopo     | Resta ATTIVO (nuovo cliente)                                         | Torna DISPONIBILE                     |
| Funzione DB  | `fn_subentro_cliente` (chiude il precedente) + creazione nuovo ciclo | `fn_disdetta_cliente` (solo chiusura) |
| BA           | Nuovo BA per il nuovo intestatario                                   | BA resta attivo per fatture finali    |
| Istanza      | Nuova istanza con `parent_istanza_id`                                | L'istanza resta come record storico   |

---

## Diagramma ER

````mermaid
%%{init: {'er': {'layoutDirection': 'TB'}}}%%
erDiagram

%% Relazioni principali per la generazione di un cliente

    soggetti               ||--o{ soggetti_ruoli            : ha
    tipi_ruoli             ||--o{ soggetti_ruoli            : classifica

    soggetti_ruoli         ||--o{ clienti                   : come_cliente

    soggetti               ||--o{ istanze_utilities         : ha

    istanze_utilities      ||--o{ clienti                   : assegnato_a
    istanze_utilities      ||--o{ billing_account           : genera
    istanze_utilities      ||--o{ catasto_unita_immobiliari : puo_avere

    stati_cliente          ||--o{ clienti                   : stato
    utilities              ||--o{ clienti                   : ha

    billing_account        ||--o| clienti                   : fattura
    billing_account        ||--o{ billing_account           : padre_di

    pdp                    ||--o{ istanze_utilities         : collegato_a

    indirizzi_dettaglio    ||--o{ istanze_utilities         : opzionale_per
    indirizzi_dettaglio    ||--o{ indirizzi                 : normalizzato_da
````

## Area tecnica — esempi

**Chiudere il cliente precedente su un punto di prelievo (subentro)** — la funzione non crea il nuovo
cliente: chiude il vecchio, lasciando il punto libero per il subentrante:

```sql
SELECT script.fn_subentro_cliente(p_pdp_id, p_data_attivazione_nuovo);
```

**Cessare il servizio senza subentro (disdetta)** — il punto di prelievo torna disponibile per future
attivazioni:

```sql
SELECT script.fn_disdetta_cliente(p_cliente_id, p_data_cessazione);
```

---

{% include-markdown "signature-core.md" %}
