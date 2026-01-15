## 📘 Documentazione Concettuale – Tabella `config.assets_ownership`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.assets](/dbzero/magazzino/tabelle/assets)
> * [config.stati_assets](/dbzero/config/tabelle/stati_assets)
> * [config.lingue](/dbzero/config/tabelle/lingue)

---

La tabella **`config.assets_ownership`** definisce il **dominio ufficiale dei tipi di proprietà degli asset**.

Serve a normalizzare il campo `ownership` della tabella `magazzino.assets`, garantendo coerenza nei processi di gestione, installazione, rientro, contabilizzazione e responsabilità dell’asset.

Esempi tipici di proprietà:

| `codice_interno`    | `codice`      | Significato operativo              |
| ------------------- | ------------- | ---------------------------------- |
| `ASSET_OWNED`       | `owned`       | Asset di proprietà del gestore     |
| `ASSET_CONSIGNMENT` | `consignment` | Asset in conto visione/consignment |
| `ASSET_CUSTOMER`    | `customer`    | Asset di proprietà del cliente     |

---

### 🎯 Scopo Principale

* Definire un **catalogo univoco e governato** delle modalità di proprietà degli asset.
* Assicurare coerenza tra domini diversi (magazzino, installazioni, contratti, fatturazione, manutenzione).
* Abilitare logiche avanzate, tra cui:

  * tracciamento responsabilità dei beni;
  * gestione dei rientri e dei guasti;
  * regole di fatturazione (es. canoni per noleggio/uso);
  * distinzioni patrimoniali nei report.

---

### 🔒 Vincoli e Regole Aziendali

* **Chiave primaria** (`id`): identificatore tecnico della modalità di proprietà.

* **Codice interno** (`codice_interno`):

  * stringa univoca (`uq_cfg_assets_ownership_codice_interno`),
  * immutabile per design (es. `ASSET_OWNED`),
  * usata per mapping applicativo e logiche interne.

* **Codice esposto** (`codice`):

  * stringa univoca (`uq_cfg_assets_ownership_codice`),
  * utilizzata in `magazzino.assets.ownership` come FK,
  * deve essere stabile e leggibile (es. `owned`, `consignment`, `customer`).

* **Descrizione** (`descrizione`):

  * testo leggibile in italiano;
  * utile in UI e reportistica.

* **Attivo** (`attivo`):

  * indica se la modalità è utilizzabile nei processi correnti;
  * permette di disattivare codici obsoleti senza cancellarli.

* **Metadati** (`meta`):

  * dizionario `jsonb` per estensioni future;
  * esempi:

    * icona/colore per UI (es. `{"icon": "pi pi-home"}`),
    * mapping contabile,
    * label multilingua (via chiavi ISO + `config.lingue`).

* **Audit** (`data_insert`, `user_insert`, `data_update`, `user_update`):

  * valori gestiti automaticamente (tramite trigger generico se abilitato);
  * garantiscono rintracciabilità delle modifiche.

* **Indici**:

  * `ix_cfg_assets_ownership_attivo` per filtrare le modalità attive;

---

### 🔗 Relazioni

`config.assets_ownership` è referenziata da:

#### **1. `magazzino.assets`**

Campo:

```sql
ownership VARCHAR(32) REFERENCES config.assets_ownership(codice)
```

Usato per definire la proprietà effettiva dell’asset.

#### **2. Processi e moduli vari**

* flussi di **installazione** (asset owned vs asset del cliente),
* flussi di **rientro** e **sostituzione**,
* **contratti** (distinguere asset dati in comodato vs asset del cliente),
* **manutenzione** (responsabilità e SLA basati sulla proprietà),
* eventuali moduli futuri (ammortamenti, cespiti, inventari patrimoniali).


---

### 💡 Vantaggi Operativi

* **Governance forte e centralizzata** su codici di proprietà asset.
* **Coerenza cross-modulo**: tutti i processi condividono lo stesso dominio.
* **Flessibilità**: tramite `meta` puoi aggiungere nuove caratteristiche senza alterare la tabella.
* **Controlli robusti**: la FK obbliga gli asset a usare solo valori ammessi.
* **Compatibilità con UI/UX**: label multilingua e icone permettono di rendere gli stati comprensibili immediatamente.

---

> 🧠 **“`config.assets_ownership` garantisce che ogni asset abbia una proprietà corretta, tracciabile e governata, abilitando processi solidi lungo tutta la vita del bene.”**
