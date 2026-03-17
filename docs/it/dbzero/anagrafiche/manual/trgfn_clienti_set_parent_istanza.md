## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_clienti_set_parent_istanza()`

> 👀 **Vedi anche**
>
[Guida – Gestione delle Istanze Utility e Collegamento con PDP & Clienti](/guide/gestione-delle-istanze-utility)   
> [Generazione di un cliente](/guide/generazione-cliente)   
>
Approfondimenti tabelle:
> 
[anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)   
> [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)   
> [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp)   
> [config.stati_cliente](/dbzero/config/tabelle/stati_cliente)   

---

### 🎯 Scopo Principale
(latest update 09-12-25)
La funzione `anagrafiche.trgfn_clienti_set_parent_istanza()` ha il compito di **mantenere la catena lineare delle istanze** (`istanze_utilities.parent_istanza_id`) per ciascun **PDP** quando viene inserito o attivato un nuovo cliente.

In particolare:

* collega l’**istanza della nuova attivazione** all’istanza immediatamente precedente sullo stesso PDP;
* garantisce che la catena sia **lineare** (ogni istanza ha al massimo un parent);
* esclude dalla catena i casi non significativi (clienti annullati, senza data di attivazione, senza PDP).

Questa funzione viene richiamata da un **trigger su `anagrafiche.clienti`** (tipicamente `BEFORE INSERT` o `BEFORE INSERT OR UPDATE` sui campi rilevanti) ed è responsabile di aggiornare il campo `parent_istanza_id` sull’istanza collegata al cliente.

---

### Tabelle e colonne coinvolte

**`anagrafiche.clienti`**

Colonne rilevanti:

* `id` – identificativo del cliente;
* `istanza_utility_id` – FK verso `anagrafiche.istanze_utilities(id)`;
* `pdp_id` – FK verso `anagrafiche.pdp(id)` (denormalizzata, sincronizzata dall’istanza);
* `stato_cliente_id` – FK verso `config.stati_cliente(id)`;
* `data_attivazione` – data di inizio validità commerciale;
* `periodo` – intervallo `[data_attivazione, data_chiusura+1)` usato per i vincoli di non sovrapposizione sul PDP.

**`anagrafiche.istanze_utilities`**

Colonne rilevanti:

* `id` – identificativo dell’istanza;
* `parent_istanza_id` – FK auto-riferita alla istanza precedente nella catena;
* `pdp_id` – FK composita con `indirizzo_dettaglio_id` verso `anagrafiche.pdp`.

**`config.stati_cliente`**

Colonne rilevanti:

* `id` – PK logica dello stato cliente;
* `codice_interno` – codice interno dello stato (es. `AT`, `CH`, `AN`, ...).

La funzione utilizza `codice_interno` per **escludere** dalla catena i clienti con stato `AN` (*annullato*).

---

### Regole di business implementate

La funzione applica le seguenti regole:

1. **Prima istanza della catena**

   * Se non esiste alcun cliente precedente valido sullo stesso `pdp_id`, allora:

     * `parent_istanza_id` **rimane NULL** per l’istanza collegata a `NEW.istanza_utility_id`.

2. **Esclusione stati non significativi**

   * I clienti con `stato_cliente.codice_interno = 'AN'` (**annullato**) sono esclusi dalla catena:

     * non diventano parent di nessuno;
     * non generano nuovi collegamenti.

3. **Esclusione clienti senza data di attivazione**

   * Se `NEW.data_attivazione IS NULL`, la funzione **non** crea alcun collegamento di parent.
   * La catena rappresenta solo attivazioni **effettive**, non pre-configurazioni o record incompleti.

4. **Catena per PDP (solo se `pdp_id` non NULL)**

   * La catena è calcolata **solo** se `NEW.pdp_id IS NOT NULL`;
   * i clienti senza PDP non partecipano alla catena delle istanze.

5. **Scelta del parent**

   * Il parent viene selezionato tra i clienti esistenti che soddisfano tutte le condizioni:

     * stesso `pdp_id` di `NEW`;
     * `data_attivazione` non NULL e **strettamente minore** di `NEW.data_attivazione`;
     * stato cliente **diverso da** `AN`;
     * associati a un’istanza diversa da quella corrente (`istanza_utility_id <> NEW.istanza_utility_id`).
   * Tra questi, viene scelto il cliente con **`data_attivazione` più recente**; in caso di parità, tipicamente quello con `id` maggiore.
   * Il relativo `istanza_utility_id` viene usato come `parent_istanza_id` per `NEW.istanza_utility_id`.

6. **Catena lineare (no rami, no cicli)**

   * Ogni istanza può avere **al massimo un parent**;
   * se `parent_istanza_id` è già valorizzato con un valore **diverso** da quello calcolato, la funzione può:

     * o lasciare invariato il valore (scenario conservativo),
     * oppure sollevare un errore (scenario strettamente coerente) – comportamento da definire nella specifica implementativa.

---

### Logica di funzionamento (vista semplificata)

Pseudo-flusso logico interno:

1. **Controlli preliminari**

   ```sql
   IF NEW.pdp_id IS NULL THEN
       RETURN NEW;  -- niente catena senza PDP
   END IF;

   -- Recupero codice interno dello stato cliente
   SELECT sc.codice_interno
   INTO v_codice_stato
   FROM config.stati_cliente sc
   WHERE sc.id = NEW.stato_cliente_id;

   IF v_codice_stato = 'AN' THEN
       RETURN NEW;  -- clienti annullati fuori dalla catena
   END IF;

   IF NEW.data_attivazione IS NULL THEN
       RETURN NEW;  -- senza data attivazione non si concatena
   END IF;
   ```

2. **Ricerca del parent candidato**

   ```sql
   SELECT c_precedente.istanza_utility_id
   INTO v_parent_istanza_id
   FROM anagrafiche.clienti c_precedente
   JOIN config.stati_cliente sc
        ON sc.id = c_precedente.stato_cliente_id
   WHERE c_precedente.pdp_id = NEW.pdp_id
     AND c_precedente.istanza_utility_id <> NEW.istanza_utility_id
     AND c_precedente.data_attivazione IS NOT NULL
     AND c_precedente.data_attivazione < NEW.data_attivazione
     AND sc.codice_interno <> 'AN'
   ORDER BY c_precedente.data_attivazione DESC,
            c_precedente.id DESC
   LIMIT 1;
   ```

3. **Aggiornamento dell’istanza corrente**

   ```sql
   IF v_parent_istanza_id IS NOT NULL THEN
       UPDATE anagrafiche.istanze_utilities iu
       SET parent_istanza_id = v_parent_istanza_id
       WHERE iu.id = NEW.istanza_utility_id
         AND (iu.parent_istanza_id IS NULL
              OR iu.parent_istanza_id = v_parent_istanza_id);

       -- opzionalmente: se parent_istanza_id è già diverso → RAISE EXCEPTION
   END IF;

   RETURN NEW;
   ```

---

### Casi d’uso principali

1. **Primo cliente sul PDP**

   * Non esiste alcun cliente precedente valido sullo stesso `pdp_id`;
   * `v_parent_istanza_id` rimane NULL;
   * l’istanza del nuovo cliente **non ha parent** → inizio catena.

2. **Subentro / voltura sullo stesso PDP**

   * Esiste almeno un cliente precedente con `data_attivazione < NEW.data_attivazione` e stato ≠ `AN`;
   * viene scelto il cliente con `data_attivazione` più recente;
   * l’istanza del nuovo cliente viene collegata con `parent_istanza_id = istanza_utility_id` del precedente.

3. **Cliente annullato**

   * Stato con `codice_interno = 'AN'`;
   * il cliente non entra nella catena e non viene considerato come parent;
   * eventuali clienti successivi “saltano” questo record nella logica di selezione del parent.

4. **Record senza data attivazione**

   * `data_attivazione IS NULL` → la funzione non concatena nulla;
   * utile per configurazioni temporanee o fasi di pre-caricamento dati.

---

### Benefici del disegno

* La **catena delle istanze** per PDP è gestita in modo **automatico**, vicino al dato, senza demandare la logica all’applicativo.
* Si ottiene una cronologia **lineare e interpretabile** delle attivazioni sullo stesso punto di prelievo.
* La separazione tra stati "reali" e stato `AN` evita di sporcare la catena con tentativi annullati o contratti mai effettivamente partiti.
* Il vincolo di **1 cliente per istanza** rende immediata la navigazione:

  * PDP → lista istanze → cronologia clienti;
  * cliente → istanza → PDP e catena precedente.

---

### Trigger associato (schema suggerito)

Un possibile trigger associato alla funzione è:

```sql
CREATE OR REPLACE TRIGGER trg_clienti_set_parent_istanza_ins
    BEFORE INSERT
    ON anagrafiche.clienti
    FOR EACH ROW
    EXECUTE FUNCTION anagrafiche.trgfn_clienti_set_parent_istanza();
```

> ☝️ In base alle esigenze, il trigger può essere esteso anche a `BEFORE UPDATE` sui campi
> `stato_cliente_id`, `pdp_id`, `data_attivazione` e `istanza_utility_id`, con la dovuta cautela
> per evitare riconfigurazioni non coerenti su dati già storicizzati.

---

### Note operative

* La funzione **non modifica `NEW`**, ma agisce su `anagrafiche.istanze_utilities` tramite `parent_istanza_id`.
* È consigliato mantenere la logica **idempotente**: più chiamate sulla stessa riga cliente non devono generare incoerenze.
* In caso di migrazioni dati o import massivi, è possibile eseguire la funzione in modalità batch
  (es. script di popolamento catena) riutilizzandone la logica centrale.
