## 📘 Parametri Personalizzati (GUC) in PostgreSQL


> 👀 **Vedi anche**  
> 
> Approfondimento Tabelle:   
> - [config.parameters](/dbzero/config/tabelle/parameters)      
> - [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)      
>
> Approfondimento funzioni :    
> - [script.fn_get_parametr_full](/dbzero/script/funzioni/fn_get_parametr_full)     
> 
> All'interno del documento viene spiegata la differenza tra parametri GUC e parametri tabellari


I **Parametri Personalizzati (GUC - Grand Unified Configuration)** di PostgreSQL consentono agli sviluppatori di definire e gestire variabili globali personalizzate per il proprio database o applicazione. Tali parametri permettono di configurare in modo flessibile il comportamento delle applicazioni, centralizzando impostazioni e facilitando manutenzione e configurazione.

---

### 🎯 Scopo Principale

* Centralizzare configurazioni applicative specifiche direttamente nel database PostgreSQL.
* Facilitare modifiche dinamiche a parametri senza intervenire sul codice applicativo.
* Consentire l’accesso semplificato a configurazioni globali da procedure, funzioni e trigger del database.

---

### 🛠️ Definizione e Utilizzo

La definizione dei parametri avviene normalmente modificando il file `postgresql.conf` oppure utilizzando comandi SQL come:

```sql
ALTER DATABASE mydb SET parametro_personalizzato = 'valore';
```

L'accesso ai parametri definiti avviene tramite la funzione SQL:

```sql
SELECT current_setting('parametro_personalizzato', true);
```

Questi parametri possono inoltre essere sovrascritti a diversi livelli, ad esempio:

* A livello di **utente**:

  ```sql
  ALTER USER username SET myapp.user_language = 'en';
  ```

* A livello di **ruolo**:

  ```sql
  ALTER ROLE rolename SET myapp.user_language = 'fr';
  ```

* Per la **sessione corrente**:

  ```sql
  SET myapp.user_language = 'de';
  ```

Questo meccanismo è particolarmente utile per impostazioni come la lingua, permettendo una gestione flessibile e personalizzata per singoli utenti o gruppi.

---

### 📋 Esempi di Parametri in Zero ERP

Di seguito i parametri personalizzati (GUC) definiti in `postgresql.conf` e utilizzati nel progetto Zero ERP:

* **`dblink.log_connection`**

  Configura la stringa di connessione utilizzata dall'estensione `dblink` per effettuare connessioni cross-database, specialmente utile per operazioni di logging remoto.

  Esempio:

  ```sql
  dblink.log_connection = 'host=localhost port=5432 dbname=Zero user=user password=pwd'
  ```

* **`myapp.user_language`**

  Definisce la lingua di default utilizzata dalle funzioni applicative per selezionare messaggi e configurazioni linguistiche appropriate. Tale valore viene usato tipicamente per localizzazione dei messaggi.

  Esempio:

  ```sql
  myapp.user_language = 'it'
  ```

---

### ⚖️ Confronto: GUC vs Modello a Tabelle

| Caratteristica              | GUC PostgreSQL                                      | Tabella Override (`config.parameters` + `config.parameter_overrides`)              |
| --------------------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------- |
| **Livelli di applicazione** | `database`, `role`, `session`, **statici**          | `global → tenant → user → session → function` (dinamici)                           |
| **Flessibilità**            | Rigido (solo livelli predefiniti)                   | Altamente estendibile a nuovi scope (es. ruolo, feature, modulo)                   |
| **Versioning**              | No (config file o DDL)                              | Sì (versionato con Liquibase in script SQL)                                        |
| **Audit**                   | Limitato (no audit built‑in)                        | Sì (campi `data_insert`, `user_insert`, trigger di audit)                          |
| **Accesso runtime**         | Solo `SET` o `current_setting`                      | API/Query dirette a database, integrabili in endpoint REST                         |
| **Use case ideale**         | Parametri **DB‑centrici** (work\_mem, search\_path) | Parametri **business‑centrici** (timeout, currency, workflow, feature flags, etc.) |

> **Quando scegliere...**
>
> * **GUC PostgreSQL**: per configurazioni strettamente tecniche o performance‑oriented, con requisiti statici o legati al ruolo DB.
> * **Tabella Override**: per impostazioni dinamiche, multi‑tenant e variabili in base a user/session/function, con tracciamento e versioning completo.

---

### 🔒 Best Practices

* Utilizzare nomi di parametri chiari e descrittivi, preferibilmente con prefissi applicativi (ad esempio, `myapp.`).
* Evitare di esporre informazioni sensibili o credenziali direttamente nei parametri GUC, soprattutto in ambienti di produzione.
* Documentare chiaramente ciascun parametro, includendo scopo, formato e uso previsto.
* Cache lato applicazione: caricare in memoria i parametri all’avvio e rinnovarli periodicamente (es. TTL 5’).
* Per i secrets, utilizzare un Vault dedicato anziché GUC o tabelle.

---

> 🧠 **“I parametri GUC sono ideali per la configurazione DB‑centric; per logica applicativa e scenari multi‑tenant multi‑scope, il modello a tabelle offre flessibilità, versioning e audit.”**
