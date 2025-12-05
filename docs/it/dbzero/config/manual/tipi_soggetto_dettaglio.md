# 📚 Tabella `config.tipi_soggetto_dettaglio`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:   
>
> * [config.tipi_soggetto](/dbzero/config/tabelle/tipi_soggetto)      
> * [config.stati](/dbzero/config/tabelle/stati)      
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)  
---

La tabella **`config.tipi_soggetto_dettaglio`** definisce le **tipologie dettagliate** di soggetto (persone fisiche, giuridiche, enti, ecc.) in base al **paese** di appartenenza, specificando i **formati** validi per Codice Fiscale e Partita IVA.

---

### 🎯 Scopo Principale

* **Gestione Internazionale**
  Permette di adattare la validazione di CF/P.IVA alle regole di ciascuno Stato (`stato_iso2`).
* **Estendibilità**
  Il collegamento a `config.tipi_soggetto` garantisce macro-categorie estensibili (Fisico, Giuridico, Ente, …).
* **Controllo Applicativo**
  Centralizza il formato di CF/P.IVA, evitando logiche duplicate nel backend.

---

### 🔍 Collegamenti

* **FK →** `config.tipi_soggetto(tipo_soggetto_id)`
  Definisce la macro-tipologia.
* **FK →** `config.stati(codice_iso2)`
  Specifica il Paese di riferimento per il formato.
* **Estensione su** `anagrafiche.soggetti.tipo_soggetto_dettaglio_id`
  Associa ogni soggetto al dettaglio corretto, eliminata la colonna `tipo_soggetto`, è stato aggiunto in `anagrafiche.soggetti` la colonna `tipo_soggetto_dettaglio_id`.


---

### 💡 Vantaggi Operativi

* Evita hard‑coding dei formati di CF/P.IVA nel codice applicativo.
* Facilita l’aggiunta di nuovi paesi o categorie nominative.
* Garantisce coerenza tra DB e validazione backend.

---






# 📘 Integrazione – Tabella `config.tipi_soggetto_dettaglio`

*(Aggiornamento del 2025-12-03)*

Questa integrazione documenta le modifiche introdotte oggi sulla tabella **`config.tipi_soggetto_dettaglio`**, in particolare riguardo i formati CF/P.IVA e la coerenza con la policy sui dati societari.

---

## 🆕 Nuovi Vincoli Introdotti

### 1️⃣ Formati ammessi per CF e P.IVA

Le colonne:

* `formato_cf`
* `formato_piva`

non possono più essere `NULL` e devono rispettare uno dei seguenti formati:

* `NON_APPLICABILE`
* `NUM_<N>`     → solo cifre, lunghezza N
* `ALFA_<N>`    → solo lettere A–Z, lunghezza N
* `ALFANUM_<N>` → lettere + cifre, lunghezza N

Esempi validi:

```
NUM_11
ALFANUM_16
ALFA_10
NON_APPLICABILE
```

Tali vincoli garantiscono che i pattern siano omogenei e validabili in modo generico.

---

## 2️⃣ Coerenza con `dati_societari_policy`

È stato introdotto il vincolo:

* Se `formato_piva = 'NON_APPLICABILE'` → `dati_societari_policy = 'NONE'`
* Se `formato_piva <> 'NON_APPLICABILE'` → `dati_societari_policy ∈ ('OPTIONAL', 'REQUIRED')`

🔍 **Significato funzionale:**

* Se un tipo soggetto non prevede la Partita IVA, allora i dati societari non possono essere richiesti.
* Se il tipo soggetto prevede una P.IVA (qualsiasi formato), allora i dati societari devono essere almeno opzionali.

---

## 3️⃣ Implicazioni funzionali

### ✔ Validazione CF/P.IVA

La funzione:

* `script.fn_validate_cf_piva_it()`

ora lavora utilizzando:

* `formato_cf <> 'NON_APPLICABILE'`
* `formato_piva <> 'NON_APPLICABILE'`

come discriminante per l'attivazione della validazione.

### ✔ Controllo Paese

La validazione rimane agganciata al dispatcher:

* `anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch`

che applica la validazione solo se `stato_iso2 = 'IT'`.

---

## 4️⃣ Benefici Architetturali

* Eliminazione di valori improvvisati nei campi CF/P.IVA.
* Base solida per l'internazionalizzazione futura.
* Maggiore robustezza nelle validazioni fiscali.
* Pulizia semantica tra tipi soggetto, dettagli fiscali e contesto nazionale.

---

## 5️⃣ Estratto dei Vincoli (per completezza)

```sql
CHECK (
  formato_cf = 'NON_APPLICABILE' OR
  formato_cf ~ '^(NUM|ALFA|ALFANUM)_[0-9]{1,2}$'
);

CHECK (
  formato_piva = 'NON_APPLICABILE' OR
  formato_piva ~ '^(NUM|ALFA|ALFANUM)_[0-9]{1,2}$'
);

CHECK (
  (formato_piva = 'NON_APPLICABILE' AND dati_societari_policy = 'NONE') OR
  (formato_piva <> 'NON_APPLICABILE' AND dati_societari_policy IN ('OPTIONAL','REQUIRED'))
);
```

---

## 📌 Nota finale

Queste modifiche rappresentano un consolidamento fondamentale per la gestione internazionale dei tipi di soggetto, rendendo il modello più controllato e predittivo.

Se vuoi integrare anche esempi pratici o diagrammi ER aggiornati, posso prepararli subito.
