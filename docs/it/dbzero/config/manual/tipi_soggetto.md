## 📘 Documentazione Concettuale – Tabella `config.tipi_soggetto`

> 👀 **Vedi anche**
>
> **Approfondimento Tabelle:**
>
> * [`config.tipi_soggetto_dettaglio`](/dbzero/config/tabelle/tipi_soggetto_dettaglio)    
> * Impatto su: [`anagrafiche.soggetti` → colonna `tipo_soggetto_dettaglio_id`](/dbzero/anagrafiche/tabelle/soggetti)     
>
> **Funzioni collegate:**  
>
> * [`anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch`](/dbzero/anagrafiche/funzioni/trgfn_soggetti_valida_cf_piva_dispatch)   

---

### 🎯 Scopo Principale

La tabella **`config.tipi_soggetto`** definisce le **macro-tipologie** dei soggetti presenti nel sistema ERP:

* **PF** → Persona Fisica
* **PG** → Persona Giuridica
* **ENTE** → Ente / Ente non commerciale
* **ALTRO** → Categoria generica o residuale

Questa classificazione di alto livello:

* evita l’uso di codici fissi hardcoded (`F`, `G`, `X`),
* consente di espandere facilmente il modello per nuove tipologie,
* separa le logiche **generali** (ruoli, natura, flussi) da quelle **fiscali e nazionali**, gestite invece nella tabella `config.tipi_soggetto_dettaglio`.

---

### 🧩 Struttura della Tabella

| Colonna                      | Tipo                          | Note                                             |
| ---------------------------- | ----------------------------- | ------------------------------------------------ |
| `id`                         | varchar(10) PK                | Codice macro‑tipologia (es. PF, PG, ENTE, ALTRO) |
| `descrizione`                | varchar(100)                  | Descrizione leggibile                            |
| `natura_soggetto`            | `config.natura_soggetto_enum` | Enum che identifica la natura del soggetto       |
| `user_insert`, `data_insert` | audit                         | Impostati automaticamente                        |
| `user_update`, `data_update` | audit                         | Aggiornati dal trigger                           |

### 🔤 Enum `config.natura_soggetto_enum`

Valori ammessi:

* **PF** – Persona Fisica
* **PG** – Persona Giuridica
* **ENTE** – Ente / Ente non commerciale
* **ALTRO** – Categoria residuale

> 📌 Usato per distinguere flussi, controlli e tassazioni basate sulla natura giuridica.

---

### 🔍 Problematiche Affrontate

**1. Coerenza tra classificazione generale e dettaglio**

La macro‑tipologia permette di definire comportamenti e flussi di base (persona fisica vs giuridica), mentre `tipi_soggetto_dettaglio` gestisce:

* paese,
* formato CF / P.IVA,
* policy fiscali,
* regole di validazione.

**2. Evoluzione e internazionalizzazione**

Aggiungere nuovi paesi o normative non richiede modifiche alla tabella principale: basta aggiungere righe nella tabella dettaglio.

**3. Eliminazione dei codici hardcoded**

La logica applicativa non dipende più da valori fissi, ma da configurazione strutturata.

---

### 🔒 Vincoli e Trigger

* **PK:** `pk_tipi_soggetto` su `id`
* **NOT NULL:** `natura_soggetto`
* **Trigger audit:** `trg_tipi_soggetto_audit_data_user_generic_upd`
  → aggiorna `user_update` e `data_update`

---

### ⚙️ Meccanismo di Integrazione con il Modello Dati

 1️⃣ Inserimento Tipi Base

Esempio di popolamento iniziale:

```sql
INSERT INTO config.tipi_soggetto(id, descrizione, natura_soggetto)
VALUES
  ('PF',   'Persona Fisica',        'PF'),
  ('PG',   'Persona Giuridica',     'PG'),
  ('ENTE', 'Ente Non Commerciale',  'ENTE'),
  ('ALTRO','Tipologia Generica',    'ALTRO');
```

 2️⃣ Collegamento con `config.tipi_soggetto_dettaglio`

Ogni macro‑tipo può avere **uno o più dettagli**, ad esempio:

* PF → PF_IT_NO_PIVA, PF_IT_CON_PIVA, PF_FR, ...
* PG → PG_IT, PG_DE, ...

Questo permette di definire formati CF/P.IVA, policy fiscali, vincoli nazionali.

 3️⃣ Impatto sui soggetti

`anagrafiche.soggetti.tipo_soggetto_dettaglio_id` → determina:

* natura giuridica (tramite join su `tipi_soggetto`),
* regole di validazione (via trigger `trgfn_soggetti_valida_cf_piva_dispatch`),
* policy relative a dati societari.

---

### 💡 Vantaggi Operativi

* **Chiarezza architetturale**: macro‑tipologie stabili, dettagli variabili.
* **Scalabilità internazionale**: nuove normative = nuovi dettagli, senza toccare i macro‑tipi.
* **Validazioni flessibili**: CF/P.IVA dipendono dal paese e dal dettaglio, non dal macro‑tipo.
* **Riduzione della logica hardcoded**: tutto viene configurato a livello tabellare.

> 🧠 **“Separare la macro‑tipologia dal dettaglio permette un modello robusto, scalabile e adatto a gestire qualsiasi evoluzione normativa.”**
