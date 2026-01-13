# Progettare le API di Zero ERP

## Regole, principi e scelte architetturali

---

## 🎯 Scopo del documento

Questo documento definisce le **linee guida ufficiali** per la progettazione delle API di **Zero ERP**, con l’obiettivo di:

* garantire **coerenza funzionale** e **robustezza** del sistema
* allineare API, database e processi di dominio
* facilitare lo sviluppo del frontend e l’onboarding di nuovi collaboratori
* evitare derive CRUD-centriche non adatte a un ERP complesso

Le regole qui descritte non sono vincoli teorici, ma derivano da **scelte architetturali consapevoli** maturate durante la progettazione del database.

---

## 🧠 Visione generale

Zero ERP è progettato come **sistema orientato ai processi di dominio**, non come semplice contenitore di dati.

Di conseguenza:

* il **database** è il luogo delle **regole forti** (integrità, coerenza, audit, workflow)
* l’**API** espone **azioni di dominio**, non solo operazioni CRUD
* il **frontend** invoca comportamenti (“fai qualcosa”), non sequenze di scritture

Questa impostazione riduce la complessità complessiva e aumenta l’affidabilità nel tempo.

---

## 🔁 CRUD vs Azioni di dominio

### ❌ Perché evitare un’API CRUD pura

Un’API CRUD espone direttamente le risorse dati (tabelle o modelli) e permette:

* creazione/modifica diretta dei record
* aggiornamenti parziali non controllati
* logica di business distribuita tra frontend, API e database

In un ERP questo porta a:

* duplicazione delle regole
* stati intermedi incoerenti
* difficoltà di audit e tracciamento
* fragilità nei refactor

---

### ✅ Perché scegliere API a **azioni di dominio**

Un’API a azioni di dominio rappresenta **ciò che il sistema fa**, non solo ciò che contiene.

Ogni endpoint:

* rappresenta un **processo aziendale atomico**
* viene eseguito in **un’unica transazione**
* applica **tutte le regole necessarie**
* produce un **esito chiaro** (successo, errore, stato)

Esempi concettuali:

* crea cliente
* attiva contratto
* genera fattura
* chiudi pratica
* cambia stato documento

---

## 🧱 Architettura a due livelli di API

Le API di Zero ERP sono divise in **due famiglie distinte**.

---

### 1️⃣ Read API (Query)

**Scopo**: consultazione dei dati

Caratteristiche:

* metodo HTTP: `GET`
* **non modificano lo stato** del sistema
* basate su:

  * view
  * materialized view
  * query ottimizzate
* supportano:

  * filtri
  * ordinamenti
  * paginazione

Esempi:

* elenco clienti
* dashboard pratiche
* storico fatture
* stato di avanzamento

Le Read API possono evolvere senza impatto sulle regole di business.

---

### 2️⃣ Command API (Azioni di dominio)

**Scopo**: esecuzione di processi

Caratteristiche:

* metodo HTTP: `POST`
* modificano lo stato del sistema
* chiamano:

  * funzioni
  * procedure
  * workflow DB
* producono:

  * esito
  * identificativi
  * messaggi strutturati

Esempi:

* `POST /clienti/crea`
* `POST /contratti/attiva`
* `POST /fatture/genera`
* `POST /pratiche/{id}/chiudi`

Ogni comando è **un’unità di lavoro completa**.

---

## 🔐 Ruolo del database

Il database è il **motore del dominio**.

Nel DB risiedono:

* regole di integrità
* validazioni complesse
* trigger di audit
* storicizzazione
* gestione stati
* workflow transazionali

Le funzioni di dominio:

* ricevono parametri chiari
* applicano tutte le regole necessarie
* sollevano errori strutturati
* restituiscono risultati consistenti

Questo garantisce che **nessuna azione possa violare il modello**, anche fuori dall’API.

---

## 🧩 Ruolo dell’API (Django / DRF)

L’API ha funzione di **orchestrazione e sicurezza**.

Responsabilità principali:

* autenticazione utenti
* autorizzazioni e ruoli
* multi-tenant
* validazione formale input
* rate limiting
* logging e tracciamento
* serializzazione risposte

L’API **non replica** le regole di business già garantite dal database.

---

## 🎨 Benefici per il frontend

Questa architettura semplifica fortemente il frontend:

* non deve conoscere il modello interno
* non deve orchestrare sequenze di chiamate
* non deve gestire rollback logici

Il frontend invoca:

> “Esegui questa azione”

E riceve:

* esito
* stato
* eventuali messaggi utente

Questo rende possibile:

* cambiare UI senza toccare il backend
* supportare più frontend (web, mobile, integrazioni)

---

## 🧠 Linee guida operative

### Regole fondamentali

* ❌ niente DDL o logica di business dal frontend
* ❌ niente update diretti di stato critico via CRUD
* ✅ ogni cambiamento di stato passa da un comando
* ✅ ogni comando è tracciabile
* ✅ le query non modificano mai lo stato

---

### Naming degli endpoint

* usare verbi di dominio
* evitare nomi di tabella
* evitare ambiguità

Esempi corretti:

* `/fatture/genera`
* `/pratiche/assegna`
* `/contratti/cessa`

---

## 📌 Motivazione della scelta

La scelta di un’API a azioni di dominio è motivata da:

* complessità intrinseca di un ERP
* necessità di coerenza forte
* presenza di workflow e stati
* esigenza di audit e storicizzazione
* volontà di evitare debito tecnico futuro

È una scelta che privilegia:

* stabilità
* chiarezza
* manutenibilità
* evoluzione controllata

---

## 🏁 Conclusione

Le API di Zero ERP **non sono un semplice strato di accesso ai dati**, ma il **canale ufficiale di esecuzione del dominio**.

Questo approccio:

* allinea backend e database
* protegge il modello
* rende il sistema comprensibile
* prepara il progetto alla crescita

---

📄 Documento di riferimento per tutte le API future di Zero ERP
