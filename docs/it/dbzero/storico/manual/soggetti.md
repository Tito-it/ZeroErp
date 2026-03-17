## 📘 Documentazione Concettuale – Tabella `storico.soggetti`

> 👀 **Vedi anche**
>
Approfondimento Tabelle:
>
[anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
>
Approfondimento funzioni e trigger:
>
[dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)
> [script.trgfn_upd_dlt_storico_generic](/dbzero/script/funzioni/trgfn_upd_dlt_storico_generic)

---

La tabella **`storico.soggetti`** conserva lo **storico** delle operazioni applicate ai record di `anagrafiche.soggetti`. Ciascun record è uno **snapshot** JSONB dello stato del soggetto in corrispondenza di un evento di addizione, aggiornamento o cancellazione.

Questo permette di:

* tracciare l’evoluzione dei dati nel tempo
* garantire auditability e compliance
* ripristinare o analizzare lo storico di un soggetto in qualsiasi momento

---

### 🎯 Scopo Principale

* **Versionamento dei soggetti**
  Ogni modifica (INSERT, UPDATE, DELETE) su `anagrafiche.soggetti` genera un record in storico con lo stato precedente, il tipo di operazione e i metadati di audit.

* **Tracciabilità e audit**
  I campi `data_insert`, `user_insert` e `tx_id` permettono di sapere quando e da chi è stata effettuata l’operazione, e di correlare più cambiamenti in un’unica transazione.

---

### Collegamenti con Altre Tabelle

* **`anagrafiche.soggetti`**

  * `soggetto_id` fa riferimento alla chiave primaria di `anagrafiche.soggetti`.
  * **ON UPDATE CASCADE**, **ON DELETE SET NULL** per mantenere consistenza e non perdere record storico in caso di cancellazione di `anagrafiche.soggetti`.

* **Triggers**

  * `trg_soggetti_ins_upd_gen_tx_id`: assegna `tx_id` su insert/update tramite `dbops.trgfn_tx_id_managed()`.

---

### Campi Rilevanti

| Campo             | Descrizione                                                 |
| ----------------- | ----------------------------------------------------------- |
| `id`              | PK BIGINT, sequence-based (`storico.soggetti_id_seq`)       |
| `valid_from`      | Data/ora inizio validità (inclusiva)                        |
| `valid_to`        | Data/ora fine validità (esclusiva), `NULL` se ancora valido |
| `change_type`     | `A`=Add, `U`=Update, `D`=Delete                             |
| `snapshot`        | Stato completo del soggetto (JSONB)                         |
| `tipo_operazione` | Codice dell’operazione (INSERT=1, UPDATE=2, DELETE=3)       |
| `tx_id`           | UUID di transazione generato dal trigger                    |
| `data_insert`     | Timestamp di inserimento del record storico                 |
| `user_insert`     | Utente che ha creato il record storico                      |

---

### Vantaggi Operativi

* **Analisi storica**
  Possibilità di ricostruire flussi di modifica, comparare versioni e rispondere a esigenze di auditing e compliance.

* **Semplificazione del disaster recovery**
  Grazie agli snapshot JSONB, non servono tabelle storiche separate per ogni colonna, riducendo complessità di backup e restore.

* **Integrazione con data warehousing**
  `valid_from` e `valid_to` permettono di esporre facilmente i dati temporali in viste dimensionali o in processi ETL.

> **“`storico.soggetti` è il registro cronologico di ogni cambiamento ai soggetti: auditing nativo, versioning JSON ed eliminazione di silos storici.”**

