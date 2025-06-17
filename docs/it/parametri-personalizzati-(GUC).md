## 📘 Parametri Personalizzati (GUC) in PostgreSQL

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

### 🔒 Best Practices

* Utilizzare nomi di parametri chiari e descrittivi, preferibilmente con prefissi applicativi (ad esempio, `myapp.`).
* Evitare di esporre informazioni sensibili o credenziali direttamente nei parametri GUC, soprattutto in ambienti di produzione.
* Nota: in casi eccezionali, come per dblink.log_connection, la stringa di connessione può includere credenziali per garantire funzionalità di logging remoto. Assicurarsi in questi casi di limitare l'accesso al file di configurazione e al database a ruoli con privilegi ridotti.
* Documentare chiaramente ciascun parametro, includendo scopo, formato e uso previsto per agevolare la manutenzione e l’integrazione.

---

> 🧠 **“I parametri personalizzati (GUC) forniscono uno strumento potente e flessibile per la configurazione centralizzata, contribuendo alla modularità e facilità di gestione del sistema.”**
