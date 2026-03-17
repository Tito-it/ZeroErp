## 📘 Documentazione Concettuale – Vista `dbops.vw_diag_v_clienti_links`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)
> [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
> [config.utilities](/dbzero/config/tabelle/utilities)
> [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)
> [config.iva](/dbzero/config/tabelle/iva)

---

### 🎯 Scopo Principale

(latest review 25-12-25)
La vista **`dbops.vw_diag_v_clienti_links`** è una **vista diagnostica** che espone in modo “leggibile” i **legami strutturali** tra:

* **Cliente** (`anagrafiche.clienti`)
* **Billing Account** (`anagrafiche.billing_account`)
* **Soggetto/Ruolo** (`anagrafiche.soggetti_ruoli` → `anagrafiche.soggetti`)
* **Istanza utility** (`anagrafiche.istanze_utilities`)
* **Utility** (`config.utilities`)
* **Tipo ruolo** (`config.tipi_ruoli`)
* **IVA** (`config.iva`)

e fornisce, in coda, una serie di **flag di coerenza** per verificare che il `billing_account` associato al cliente (se presente) sia **allineato** con:

* `istanza_utility_id`
* `soggetto_ruolo_id`
* `utility_id`

> In pratica: *“vedo in una riga sola tutte le chiavi e posso capire subito se il legame Cliente → BillingAccount è coerente oppure no.”*

---

### Ruolo nel Modello Dati

Nel modello Zero ERP, un **cliente** è legato a una specifica **istanza_utility** e a una specifica **utility**. Il **billing_account** (quando presente) deve tipicamente essere coerente con questi stessi riferimenti.

Questa vista supporta:

* debug di dati “sporchi” o incoerenti
* validazione post-migrazione/import
* individuazione rapida di clienti con billing account non allineato
* analisi operativa (prima di procedure di consolidamento / fix automatici)

---

### Join e Origine Dati

La vista parte sempre da:

* `anagrafiche.clienti c`

con join **LEFT** (tolleranti a NULL) verso:

* `anagrafiche.billing_account ba` (solo se `c.billing_account_id` valorizzato)
* `anagrafiche.soggetti_ruoli sr` (da `c.soggetto_ruolo_id`)
* `anagrafiche.soggetti s` (da `sr.soggetto_id`)
* `anagrafiche.istanze_utilities iu` (da `c.istanza_utility_id`)
* `config.utilities u` (da `c.utility_id`)
* `config.tipi_ruoli tr` (da `sr.tipo_ruolo_id`)
* `config.iva iv` (da `c.iva_id`)

✅ Scelta intenzionale: i LEFT JOIN permettono di evidenziare dati mancanti (es. cliente senza billing account, o riferimenti non risolti).

---

### 🧾 Struttura – Colonne principali

#### 1) Identificativi e legami del Cliente

| Colonna                      | Origine                | Descrizione                            |
| ---------------------------- | ---------------------- | -------------------------------------- |
| `cliente_id`                 | `c.id`                 | ID cliente                             |
| `cliente_soggetto_ruolo_id`  | `c.soggetto_ruolo_id`  | FK verso `soggetti_ruoli`              |
| `cliente_istanza_utility_id` | `c.istanza_utility_id` | FK verso `istanze_utilities`           |
| `cliente_utility_id`         | `c.utility_id`         | FK verso `utilities`                   |
| `cliente_billing_account_id` | `c.billing_account_id` | FK verso `billing_account` (opzionale) |

#### 2) Identificativi e legami del Billing Account (se presente)

| Colonna                 | Origine                 | Descrizione                                 |
| ----------------------- | ----------------------- | ------------------------------------------- |
| `ba_id`                 | `ba.id`                 | ID billing account                          |
| `ba_istanza_utility_id` | `ba.istanza_utility_id` | Istanza associata al billing account        |
| `ba_soggetto_ruolo_id`  | `ba.soggetto_ruolo_id`  | Soggetto/ruolo associato al billing account |
| `ba_utility_id`         | `ba.utility_id`         | Utility associata al billing account        |

#### 3) Dati soggetto / contesto

| Colonna           | Origine             | Descrizione          |
| ----------------- | ------------------- | -------------------- |
| `soggetto_id`     | `s.id`              | ID soggetto          |
| `soggetto_codice` | `s.codice`          | Codice soggetto      |
| `ragione_sociale` | `s.ragione_sociale` | Ragione sociale (PG) |
| `cognome`         | `s.cognome`         | Cognome (PF)         |
| `nome`            | `s.nome`            | Nome (PF)            |

#### 4) Istanza e Utility

| Colonna                  | Origine            | Descrizione            |
| ------------------------ | ------------------ | ---------------------- |
| `istanza_id`             | `iu.id`            | ID istanza utility     |
| `istanza_fittizia`       | `iu.fittizia`      | Flag istanza fittizia  |
| `utility_id`             | `u.id`             | ID utility             |
| `utility_codice_interno` | `u.codice_interno` | Codice interno utility |
| `utility_descrizione`    | `u.descrizione`    | Descrizione utility    |

#### 5) Ruolo e IVA

| Colonna                     | Origine          | Descrizione          |
| --------------------------- | ---------------- | -------------------- |
| `tipo_ruolo_id`             | `tr.id`          | ID tipo ruolo        |
| `tipo_ruolo_codice_interno` | `tr.codice`      | Codice interno ruolo |
| `tipo_ruolo_descrizione`    | `tr.descrizione` | Descrizione ruolo    |
| `iva_id`                    | `iv.id`          | ID IVA               |
| `iva_codice`                | `iv.codice`      | Codice IVA           |
| `iva_descrizione`           | `iv.descrizione` | Descrizione IVA      |

---

### Flag di coerenza Cliente ↔ Billing Account

Questi tre campi sono booleani e rappresentano un confronto diretto:

| Flag                      | Logica                                         | Significato                                                           |
| ------------------------- | ---------------------------------------------- | --------------------------------------------------------------------- |
| `ba_match_istanza`        | `ba.istanza_utility_id = c.istanza_utility_id` | Il billing account punta alla stessa istanza del cliente              |
| `ba_match_soggetto_ruolo` | `ba.soggetto_ruolo_id = c.soggetto_ruolo_id`   | Il billing account è associato allo stesso soggetto/ruolo del cliente |
| `ba_match_utility`        | `ba.utility_id = c.utility_id`                 | Il billing account usa la stessa utility del cliente                  |

⚠️ Nota su NULL: se `ba` è NULL (cliente senza billing account), i confronti producono `NULL` (non TRUE/FALSE). È un comportamento utile perché distingue:

* **assenza di billing account** (flag NULL)
* **presenza ma incoerenza** (flag FALSE)

---

### Esempi d’uso

#### 1) Clienti con billing account presente ma non coerente

```sql
SELECT *
FROM dbops.vw_diag_v_clienti_links
WHERE cliente_billing_account_id IS NOT NULL
  AND (
    ba_match_istanza IS DISTINCT FROM TRUE
    OR ba_match_soggetto_ruolo IS DISTINCT FROM TRUE
    OR ba_match_utility IS DISTINCT FROM TRUE
  );
```

#### 2) Clienti senza billing account (da completare)

```sql
SELECT cliente_id, soggetto_id, ragione_sociale, cognome, nome,
       cliente_istanza_utility_id, cliente_utility_id
FROM dbops.vw_diag_v_clienti_links
WHERE cliente_billing_account_id IS NULL;
```

#### 3) Vista “audit” su un singolo cliente

```sql
SELECT *
FROM dbops.vw_diag_v_clienti_links
WHERE cliente_id = :cliente_id;
```

#### 4) Conteggio anomalie per tipologia

```sql
SELECT
  count(*) FILTER (WHERE cliente_billing_account_id IS NULL) AS senza_ba,
  count(*) FILTER (WHERE cliente_billing_account_id IS NOT NULL AND ba_match_istanza IS DISTINCT FROM TRUE) AS mismatch_istanza,
  count(*) FILTER (WHERE cliente_billing_account_id IS NOT NULL AND ba_match_soggetto_ruolo IS DISTINCT FROM TRUE) AS mismatch_soggetto_ruolo,
  count(*) FILTER (WHERE cliente_billing_account_id IS NOT NULL AND ba_match_utility IS DISTINCT FROM TRUE) AS mismatch_utility
FROM dbops.vw_diag_v_clienti_links;
```

---

### Vantaggi Operativi

* **Diagnostica immediata**: tutte le FK rilevanti in un’unica riga.
* **Evidenza delle incoerenze**: i tre flag permettono una lettura “a semaforo”.
* **Supporto a migrazioni/import**: utile come “post-check” dopo caricamenti massivi.
* **Base per procedure di fix**: può alimentare job che riallineano `billing_account` o segnalano anomalie.

---

> **“`vw_diag_v_clienti_links` è una lente diagnostica: mostra in modo esplicito come sono collegati Cliente, Billing Account, Soggetto e Istanza e rende visibili a colpo d’occhio le incoerenze.”**

{% include-markdown "signature-core.md" %}
