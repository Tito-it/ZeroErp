## 📘 Documentazione Concettuale – Tabella `config.stati_assets`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:
>
> * [assets.assets](/dbzero/assets/tabelle/assets) *(quando disponibile)*
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) *(per stati legati al ciclo fisico)*
>
> Approfondimenti domini collegati:
>
> * [config.lingue](/dbzero/config/tabelle/lingue)
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti)
>
> Approfondimenti funzioni/trigger generici:
>
> * [script.trgfn_upd_audit_data_user_generic](/dbzero/script/funzioni/trgfn_upd_audit_data_user_generic)

---

La tabella **`config.stati_assets`** definisce il **dominio degli stati degli asset** (es. contatori, apparati di rete, componenti d’impianto, dispositivi in campo).

Gli stati descrivono la **posizione funzionale e logistica** dell’asset lungo il suo ciclo di vita, ad esempio:

| `codice_interno`      | `codice`     | Esempio descrizione                           |
| --------------------- | ------------ | --------------------------------------------- |
| `ASSET_ST_IN_STOCK`   | `IN_STOCK`   | “Disponibile a magazzino”                     |
| `ASSET_ST_ASSEGNATO`  | `ASSEGNATO`  | “Assegnato (in carico a tecnico/ODL/cliente)” |
| `ASSET_ST_INSTALLATO` | `INSTALLATO` | “Installato presso cliente/impianto”          |
| `ASSET_ST_RIENTRATO`  | `RIENTRATO`  | “Rientrato a magazzino”                       |
| `ASSET_ST_GUASTO`     | `GUASTO`     | “Guasto / fuori servizio”                     |
| `ASSET_ST_DISMISSED`  | `DISMISSED`  | “Dismesso / rottamato”                        |

---

### 🎯 Scopo Principale

* Fornire un **catalogo centralizzato e stabile** degli stati in cui può trovarsi un asset.
* Supportare la gestione del **ciclo di vita degli asset**, inclusi:

  * magazzino → assegnazione → installazione → rientro → dismissione;
  * gestione del guasto / sostituzione.
* Abilitare regole di processo su:

  * disponibilità a magazzino,
  * patrimonio attivo presso clienti/impianti,
  * gestione manutenzione / sostituzioni / resi,
  * dismissione e rottamazione.

---

### 🔒 Vincoli e Regole Aziendali

* **Identificatore tecnico** (`id`):

  * chiave primaria `bigint` generata automaticamente.

* **Codici di stato**:

  * `codice_interno`:

    * codice funzionale interno, univoco (`uq_stati_assets_codice_interno`),
    * pensato per essere **immutabile** (es. `ASSET_ST_IN_STOCK`, `ASSET_ST_INSTALLATO`),
    * utilizzato nel codice applicativo e nelle configurazioni di processo.
  * `codice`:

    * codice operativo/stabile, anch’esso univoco (`uq_stati_assets_codice`),
    * tipicamente più compatto (es. `IN_STOCK`, `INSTALLATO`, `GUASTO`).

* **Descrizione** (`descrizione`):

  * testo leggibile per operatori e schermate di configurazione;
  * indicizzata tramite `ix_stati_assets_descrizione_upper` per ricerche case-insensitive.

* **Stato di attivazione** (`attivo`):

  * indica se lo stato è ancora utilizzabile per nuovi asset o per avanzamenti di stato;
  * l’indice `ix_stati_assets_attivo` ottimizza i filtri sui soli stati attivi.

* **Ordinamento** (`ordine`):

  * numero intero che consente di definire un **ordine di presentazione** (es. ciclo logico: IN_STOCK → ASSEGNATO → INSTALLATO → RIENTRATO → DISMISSED);
  * può essere usato in UI per mostrare stati in sequenza logica.

* **Metadati estensibili** (`meta`):

  * campo `jsonb` obbligatorio con default `{}`;
  * contiene **dizionari multilingua, alias, icone**, e ulteriori parametri di comportamento, ad esempio:

    * label localizzate per i vari stati (in combinazione con `config.lingue`),
    * icona/colore suggerito per UI (es. verde per IN_STOCK, rosso per GUASTO, grigio per DISMISSED),
    * flag di **stato finale** (es. `is_final: true` per DISMISSED),
    * flag per indicare se lo stato comporta **asset disponibile/non disponibile**.

* **Audit**:

  * `data_insert`, `user_insert`, `data_update`, `user_update` tracciano la storia delle modifiche al dominio;
  * in linea con gli altri domini `config`, la gestione può essere centralizzata tramite trigger di audit generico.

* **Indici per ricerche case-insensitive**:

  * `ix_stati_assets_codice_interno_upper`, `ix_stati_assets_codice_upper`, `ix_stati_assets_descrizione_upper`:

    * permettono ricerche veloci per codice/descrizione senza distinzione tra maiuscole/minuscole;
    * fondamentali quando gli input arrivano da UI, file o integrazioni non normalizzate.

---

### 🔗 Relazioni

`config.stati_assets` è una tabella di dominio referenziata da:

* **Tabella principale degli asset** (es. `assets.assets`):

  * campo tipo `stato_asset_id` / `stato_id` che punta a `config.stati_assets.id`;
  * lo stato governa la disponibilità e il comportamento dell’asset nei processi.

* **Movimenti e storico stati**:

  * eventuali tabelle di storico (es. `assets.assets_storico_stati`) possono registrare i passaggi di stato nel tempo,
  * collegando ogni transizione a un valore di `config.stati_assets`.

* **Processi di manutenzione / ticket / ODL**:

  * gli stati possono guidare logiche di:

    * apertura/chiusura ODL,
    * gestione rientri,
    * sostituzioni di contatori o apparati.

> 🔁 In combinazione con i movimenti di magazzino e i dati impianto/cliente, `config.stati_assets` consente una visione coerente del ciclo di vita dell’asset.

---

### ⚙️ Trigger Associati (attesi/suggeriti)

Al momento non sono definiti trigger specifici nella DDL riportata, ma è consigliabile introdurre:

1. **Trigger di audit** (es. `trg_upd_stati_assets_audit_data_user`)

   * **Quando**: `BEFORE UPDATE`.
   * **Cosa fa**: aggiorna `data_update` e `user_update`.
   * **Come**: delega a `script.trgfn_upd_audit_data_user_generic()`.

2. **Trigger di protezione del codice interno** (es. `trg_stati_assets_protect_codice_interno`)

   * **Quando**: `BEFORE UPDATE`.
   * **Cosa fa**: impedisce la modifica di `codice_interno` una volta creato il record.
   * **Obiettivo**: garantire la **stabilità semantica** del dominio, evitando che cambi di codice rompano logiche applicative o storici.

> ✅ In questo modo, il dominio degli stati diventa affidabile anche in contesti dove l’asset viene tracciato per molti anni.

---

### 💡 Vantaggi Operativi

* **Governance del ciclo di vita**: gli stati descrivono in modo chiaro dove si trova l’asset e in quale fase del suo ciclo si trova (magazzino, installato, guasto, dismesso, ecc.).
* **Coerenza cross-modulo**: tutti i moduli (magazzino, impianti, manutenzione, fatturazione basata su asset/contatori) condividono lo stesso dominio di stati.
* **Supporto a UI e reportistica**: grazie a `meta` è possibile definire label multilingua, icone e colori per rendere immediata la lettura dello stato da parte degli operatori.
* **Flessibilità configurabile**: nuovi stati possono essere introdotti (es. per workflow specifici di un gestore) senza rompere il modello esistente.
* **Ricerca efficiente**: gli indici in upper permettono ricerche rapide anche su basi dati di grandi dimensioni.

---

> 🧠 **“Un dominio chiaro degli stati degli asset è essenziale per governare disponibilità, manutenzione e patrimonio installato, specialmente in contesti come utilities e asset distribuiti sul territorio.”**
