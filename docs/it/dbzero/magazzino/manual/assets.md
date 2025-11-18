## 📘 Documentazione Concettuale – Tabella `magazzino.assets`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) 
> * [config.stati_assets](/dbzero/config/tabelle/stati_assets)
> * [config.assets_ownership](/dbzero/config/tabelle/assets_ownership)
> * [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini)
> * [magazzino.ubicazioni](/dbzero/magazzino/tabelle/ubicazioni)
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> * [vendite.contratti] (/dbzero/vendite/tabelle/contratti)

---

La tabella **`magazzino.assets`** rappresenta l’**istanza fisica di un bene durevole serializzato** (contatore, router, PC, stampante, apparato di rete, ecc.).

Ogni riga descrive **un singolo asset fisico**, collegato ad un articolo di catalogo, ad uno stato del ciclo di vita e, opzionalmente, a un cliente/contratto/magazzino/ubicazione.

---

### 🎯 Scopo Principale

* Tracciare a livello puntuale **tutti gli asset fisici** gestiti da Zero ERP.
* Collegare l’asset a:

  * **articolo** (`articolo_id`),
  * **proprietà** (`ownership_id` → `config.assets_ownership`),
  * **stato operativo/logistico** (`stato_id` → `config.stati_assets`),
  * **billing account** cliente (`billing_account_id`),
  * **contratto** (`contratto_id`),
  * **magazzino** e **ubicazione** (`magazzino_id`, `ubicazione_id`, `ubicazione`).
* Costituire la base per:

  * inventario di beni serializzati,
  * installato presso cliente,
  * manutenzione, sostituzioni, letture, dismissioni.

---


### 🔗 Relazioni principali

* **Catalogo articoli** → identifica modello e caratteristiche dell’asset.
* **Proprietà asset** → `ownership_id` collega a chi è il proprietario.
* **Stato ciclo vita** → definisce posizione nel flusso (magazzino → assegnato → installato → guasto → dismesso).
* **Magazzino & ubicazione** → descrivono dove si trova fisicamente.
* **Contratto & cliente** → aggancio commerciale per billing e manutenzione.

---

### ⚙️ Indici

Ottimizzano ricerche operative:

* `ix_mag_assets_articolo` — ricerca per modello.
* `ix_mag_assets_magazzino` — ricerca per magazzino.
* `ix_mag_assets_ownership_id` — ricerca per tipo proprietà.
* `ix_mag_assets_stato_id` — elenco asset installati/guasti.
* `ix_mag_assets_ubicazione` — elenco per ubicazione.
* `uq_mag_assets_seriale` — garantisce unicità del seriale.

---

### ⚙️ Trigger previsti

* **Trigger audit** → aggiornano `data_update` / `user_update` automaticamente.
* **Trigger TX-ID** → integrano il record nei batch logici.
* **Trigger di storicizzazione** → creano snapshot in tabelle storico (se `storicizza = true`).
* **Trigger di coerenza stato** → opzionale per garantire transizioni ammesse.

---

### 💡 Vantaggi operativi

* Tracciabilità completa del patrimonio fisico.
* Governance chiara di proprietà, stato, ubicazione e contratto.
* Supporto a manutenzione, rientri, sostituzioni, installazioni.
* Struttura compatibile con UI avanzate (icone, colori, info tecniche via `meta`).
* Allineamento al framework Zero ERP (audit, tx-id, storicizzazione).

---

> 🧠 **“`magazzino.assets` è la vista unificata dell’intero ciclo di vita degli asset: logistica, tecnica e commerciale.”**
