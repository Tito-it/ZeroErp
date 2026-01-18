## 📘 Documentazione Concettuale – Funzione `script.fn_subentro_cliente()`

> 👀 **Vedi anche**
>
> **Guide e concetti correlati:**
> 
> • [Guida – Gestione delle Istanze Utility e Collegamento con PDP & Clienti](/guide/gestione-delle-istanze-utility)  
> • [Guida Tecnica – Generazione di un Cliente](/guide/generazione-cliente)  
> • [Regole strutturali delle istanze (modello 2025)](/dbzero/anagrafiche/tabelle/istanze_utilities)   
>
> **Tabelle e funzioni collegate:**
> 
> • [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)   
> • [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)    
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)   
> • [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp)   
> • [config.stati_cliente](/dbzero/config/tabelle/stati_cliente)   
> • [`anagrafiche.trgfn_clienti_set_parent_istanza`](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_parent_istanza)   
> • [`anagrafiche.trgfn_clienti_sync_pdp`](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_pdp)   
> • [`anagrafiche.trgfn_clienti_sync_utility_from_ba`](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_pdp)   
> • [`script.fn_get_or_create_soggetto_ruolo`](/dbzero/anagrfiche/script/fn_get_or_create_soggetto_ruolo)   

---

### 🎯 Scopo Principale

(latest update 09-12-25)
La funzione `script.fn_subentro_cliente()` implementa **l’operazione di subentro standardizzata** su un PDP, incapsulando in un unico punto tutta la logica tecnica e commerciale che, altrimenti, sarebbe demandata al frontend.

In particolare, la funzione:

1. **chiude il cliente attualmente attivo** sul PDP con data di chiusura coerente rispetto alla nuova attivazione;
2. **genera una nuova istanza** per il nuovo intestatario, collegata allo stesso PDP;
3. **genera (o collega) il billing account** alla nuova istanza;
4. **crea il nuovo cliente**, rispettando le regole:

   * 1 istanza ⇄ 1 cliente;
   * 1 cliente attivo per PDP;
   * catena lineare delle istanze tramite `parent_istanza_id`.

La funzione è pensata per essere richiamata da frontend / API come **operazione atomica di subentro**.

---

### 🧱 Tabelle e oggetti coinvolti

**Tabelle principali**

* `anagrafiche.clienti`
  Contiene il cliente **uscente** (attualmente attivo) e il nuovo cliente **entrante** creato dalla funzione.

* `anagrafiche.istanze_utilities`
  Viene utilizzata per:

  * individuare l’istanza associata al cliente uscente;
  * creare la nuova istanza collegata allo stesso PDP;
  * impostare `parent_istanza_id` (direttamente o tramite trigger su `clienti`).

* `anagrafiche.billing_account`
  Collegato alla vecchia e/o nuova istanza; può essere:

  * riutilizzato, oppure
  * rigenerato secondo le regole di business definite (per le utility tipicamente **nuovo BA per nuovo intestatario**).

* `anagrafiche.pdp`
  Identifica il punto di prelievo su cui si effettua il subentro.

* `config.stati_cliente`
  Fornisce gli ID degli stati:

  * `AT` → attivo;
  * `CH` → chiuso;
  * `AN` → annullato (non usato come stato finale di subentro, ma da escludere da catene).

**Funzioni / trigger di supporto**

* `script.fn_get_or_create_soggetto_ruolo(p_soggetto_id, 'CL')`
  Garantisce l’esistenza del ruolo CLIENTE per il soggetto entrante.

* `anagrafiche.trgfn_clienti_set_parent_istanza()`
  Mantiene la catena `parent_istanza_id` delle istanze per PDP.

* `anagrafiche.trgfn_clienti_set_periodo()`
  Normalizza `periodo` a partire da `data_attivazione` e `data_chiusura`.

* `anagrafiche.trgfn_clienti_sync_pdp()` e `trgfn_clienti_sync_utility_from_ba()`
  Mantengono allineati `pdp_id` e `utility_id` fra cliente, istanza e billing account.

---

### 🔢 Parametri e valore di ritorno (schema concettuale)

> ⚠️ I nomi esatti dei parametri vanno allineati con l’implementazione SQL effettiva. Qui si documenta la **semantica**.

Esempio di firma concettuale:

```sql
script.fn_subentro_cliente(
    p_pdp_id           BIGINT,
    p_soggetto_id_new  UUID,
    p_data_attivazione DATE,
    p_opzioni          JSONB DEFAULT '{}'::jsonb
) RETURNS BIGINT
```

* **`p_pdp_id`**
  Identifica il PDP su cui effettuare il subentro.

* **`p_soggetto_id_new`**
  Soggetto che diventerà intestatario del nuovo cliente.

* **`p_data_attivazione`**
  Data di attivazione commerciale del nuovo cliente.
  La funzione userà questa data per calcolare la chiusura del cliente precedente.

* **`p_opzioni`** (JSONB, opzionale)
  Contiene eventuali parametri aggiuntivi per personalizzare il subentro, ad esempio:

  * `"forza_chiusura_precedente" : true/false`
  * `"crea_nuovo_billing_account" : true/false`
  * `"garanzia_importo"`, `"garanzia_tipo"`, ecc.

**Valore di ritorno**:

* `BIGINT` → `id` del nuovo record in `anagrafiche.clienti` creato come risultato del subentro.

---

### 🧠 Logica di business implementata

**1️⃣ Individuazione del cliente attualmente attivo**

Per il `p_pdp_id` indicato, la funzione cerca il cliente **attualmente attivo**, secondo criteri coerenti con il modello:

* `clienti.pdp_id = p_pdp_id`;
* `stato_cliente.codice_interno = 'AT'`;
* `data_attivazione` valorizzata;
* `data_chiusura IS NULL` **oppure** `periodo` aperto verso `infinity`.

Se **non esiste alcun cliente attivo**, la funzione si comporta come **prima attivazione** e salta la fase di chiusura precedente.

Se esistono **più clienti attivi** sullo stesso PDP, viene sollevato un errore di coerenza (violazione del modello) e l’operazione si interrompe.

---

### 2️⃣ Chiusura del cliente precedente

Se viene trovato un cliente attivo precedente:

1. la funzione calcola `data_chiusura_prev = p_data_attivazione - 1 giorno`;
2. aggiorna il record cliente:

   * `data_chiusura = data_chiusura_prev`;
   * `stato_cliente_id` → stato con `codice_interno = 'CH'` (chiuso);
3. lascia che il trigger `trg_clienti_set_periodo` ricalcoli correttamente `periodo`.

> ✅ In questo modo viene rispettato il vincolo di esclusione
> `ex_clienti_no_overlap_stesso_pdp`, evitando sovrapposizioni fra periodi
> commerciali sullo stesso PDP.

Eventuali logiche di validazione aggiuntive (es. `data_chiusura_prev >= data_attivazione_precedente`) sono gestite all’interno della funzione o da vincoli esistenti.

---

### 3️⃣ Creazione nuova istanza per il soggetto entrante

La funzione crea una nuova riga in `anagrafiche.istanze_utilities` per il soggetto entrante, con le seguenti caratteristiche:

* `pdp_id = p_pdp_id` (stesso punto di prelievo);
* `indirizzo_dettaglio_id` copiato dall’istanza precedente (coerenza fisica);
* `soggetto_id = p_soggetto_id_new`;
* `fittizia = FALSE` (in presenza di PDP l’istanza non può essere fittizia);
* `proprietario_inquilino` impostato secondo regole di dominio (ad es. `'P'` o `'I'`);
* `parent_istanza_id` inizialmente NULL (sarà poi calcolato via trigger su `clienti`, o valorizzato direttamente).

Il `codice` dell’istanza è generato automaticamente dal trigger basato su `config.sistema_codici`, se configurato per l’istanza.

---

### 4️⃣ Ruolo cliente per il nuovo soggetto

Prima di creare il nuovo cliente, la funzione garantisce l’esistenza del ruolo CLIENTE per il soggetto entrante:

```sql
v_soggetto_ruolo_id := script.fn_get_or_create_soggetto_ruolo(
    p_soggetto_id_new,
    'CL'  -- ruolo CLIENTE
);
```

In questo modo risultano allineate le tabelle:

* `anagrafiche.soggetti`
* `anagrafiche.soggetti_ruoli` (ruolo CLIENTE)

---

### 5️⃣ Gestione del billing account

A seconda delle regole di business (e/o delle opzioni in `p_opzioni`), la funzione può:

1. **creare un nuovo billing account** per la nuova istanza (scenario tipico per utilities: nuovo intestatario → nuovo BA); oppure
2. **riutilizzare** il billing account esistente, se ammesso.

In entrambi i casi viene rispettato il vincolo:

* `billing_account.istanza_utility_id = nuova_istanza.id`;
* la FK `(clienti.billing_account_id, clienti.istanza_utility_id)` → `(billing_account.id, billing_account.istanza_utility_id)` assicura il legame coerente fra cliente, BA e istanza.

---

### 6️⃣ Creazione del nuovo cliente

Infine, la funzione inserisce il nuovo record in `anagrafiche.clienti`:

* `soggetto_ruolo_id = v_soggetto_ruolo_id` (CLIENTE del soggetto entrante);
* `istanza_utility_id = nuova_istanza.id`;
* `billing_account_id = v_billing_account_id` (nuovo o esistente);
* `pdp_id` e `utility_id` coerenti (via trigger di sync);
* `stato_cliente_id` con `codice_interno = 'AT'` (attivo);
* `data_attivazione = p_data_attivazione`;
* `data_chiusura = NULL`.

I trigger esistenti si occuperanno di:

* calcolare `periodo`;
* impostare `tx_id`;
* aggiornare auditing (`data_insert`, `user_insert`, ecc.);
* settare `parent_istanza_id` sulla nuova istanza (tramite `trgfn_clienti_set_parent_istanza()`).

Il `cliente.id` così generato viene restituito come valore della funzione.

---

### 🧪 Casi d’uso principali

**Caso 1 – Subentro standard con cliente attivo presente**

* Esiste un cliente **ATTIVO** (`AT`) sul PDP con `data_attivazione = D1`, `data_chiusura NULL`.
* Si chiama `fn_subentro_cliente(p_pdp_id, p_soggetto_id_new, D2)` con `D2 > D1`.

Risultato:

1. Cliente precedente:

   * `data_chiusura = D2 - 1`;
   * `stato_cliente = CH`;
   * `periodo = [D1, D2)`.
2. Nuova istanza per il soggetto entrante, collegata al medesimo PDP.
3. Nuovo billing account (se previsto) per la nuova istanza.
4. Nuovo cliente:

   * `data_attivazione = D2`;
   * `data_chiusura = NULL`;
   * catena istanze aggiornata.

**Caso 2 – Prima attivazione sul PDP**

* Nessun cliente attivo sul PDP.
* La funzione salta la fase di chiusura e procede direttamente con:

  * creazione istanza;
  * eventuale billing account;
  * creazione cliente attivo.

**Caso 3 – Incoerenza dati (più clienti attivi)**

* Sul PDP risultano **più** clienti in stato attivo / periodo aperto.
* La funzione **solleva eccezione** (tramite `RAISE` o `fn_log_and_raise_error`) perché non è in grado di identificare in modo deterministico il cliente precedente.

---

### ⚠️ Errori comuni intercettati

* **Più clienti attivi sullo stesso PDP** → errore bloccante.
* **Data di attivazione del nuovo cliente ≤ data_attivazione precedente** → errore di coerenza (se previsto) per evitare inversioni temporali.
* **Mancanza stato `AT` o `CH` in `config.stati_cliente`** → errore di configurazione.
* **Mancanza PDP o indirizzo associato** → errore, in quanto il subentro richiede un contesto fisico ben definito.

---

### 🔧 Note operative

* La funzione è pensata come **API di dominio** da esporre a frontend / servizi applicativi:
  il frontend non deve occuparsi di chiudere manualmente il cliente uscente.
* Tutta la logica critica (periodi, stati, vincoli su PDP, catena istanze) è concentrata lato DB,
  riducendo il rischio di errori applicativi.
* In fase di import / migrazione, è possibile:

  * popolare inizialmente i dati in modo “grezzo”;
  * successivamente eseguire subentri massivi utilizzando questa funzione in batch.

---

### 📌 Sintesi

`script.fn_subentro_cliente()` è il **punto di ingresso ufficiale** per la gestione del subentro
nel modello Zero ERP:

* chiude il cliente precedente in modo consistente;
* crea una nuova istanza e, se necessario, un nuovo billing account;
* genera il nuovo cliente mantenendo tutte le catene e i vincoli (PDP, utility, istanza, ruoli);
* assicura il rispetto dei vincoli di non sovrapposizione e delle regole “1 cliente attivo per PDP”
  e “1 istanza ⇄ 1 cliente`.
