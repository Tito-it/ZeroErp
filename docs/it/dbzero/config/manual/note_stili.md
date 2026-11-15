## 📘 Documentazione Concettuale – Tabella `config.note_stili`

> **Ultimo aggiornamento**: 13 novembre 2026

> 👀 **Vedi anche**
>
Approfondimenti tabelle note e messaggi:
>
> [config.lingue](/dbzero/config/tabelle/lingue)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimenti funzioni/trigger generici:
>
[script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic)

---

La tabella **`config.note_stili`** definisce il **dominio degli stili applicabili alle note** nel sistema.

Serve a **normalizzare** il campo "stile" utilizzato nei testi di note, commenti, messaggi e descrizioni, evitando codifiche libere e inconsistenti.

Esempi di stili tipici:

* `NORMALE`
* `GRASSETTO`
* `AVVISO`
* `PICCOLO`
* `EVIDENZIATO`

---
### 🎯 Scopo Principale
(latest review 15-01-26)
* Fornire un **catalogo centralizzato** degli stili che possono essere applicati alle note (formattazione e/o semantica).
* Separare la **semantica dello stile** (es. AVVISO, AVVERTENZA, INFO) dalla renderizzazione effettiva lato UI/templating.
* Supportare la definizione di **regole visuali e di priorità** per note e messaggi (es. stile per warning, info, errori, note di servizio).

---

### Vincoli e Regole Aziendali

* **Codice esposto** (`codice`):

  * campo `varchar(16)` univoco (`uq_cfg_note_stili_codice`);
  * è il **codice utilizzabile da UI, configurazioni e integrazioni** (es. `NORMALE`, `WARN`, `SMALL`);
  * utilizzato per ricerche e filtri in UI e integrazioni.

* **Codice interno** (`codice_interno`):

  * campo `varchar(16)` univoco (`uq_cfg_note_stili_codice_interno`);
  * vincolato da `chk_cfg_note_stili_codice_interno_len` (min 2, max 16 caratteri);
  * pensato come **codice funzionale immutabile**, da bloccare via trigger per evitare modifiche accidentali;
  * usato come chiave stabile nelle logiche applicative e nei mapping.

* **Descrizione** (`descrizione`):

  * testo leggibile che descrive lo stile (es. "Testo normale", "Avviso importante", "Testo piccolo");
  * usata per ricerca e presentazione in UI e template.

* **Stato di attivazione** (`attivo`):

  * se `true`, lo stile è selezionabile e proposto nelle configurazioni/UI;
  * indicizzato da `ix_cfg_note_stili_attivo` per ottimizzare i filtri sui soli stili attivi.

* **Note di configurazione** (`note`):

  * campo testuale libero per documentare **uso previsto**, **linee guida** o **restrizioni**;
  * utile per chiarire ai configuratori quando usare uno stile e quando evitarlo.

* **Soglia di storicizzazione** (`storicizza`):

  * flag booleano che indica se lo stile è **abilitato alla storicizzazione** nell’ambito del motore note;
  * può essere usato per differenziare stili "di sistema" (magari non storicizzati) da stili legati a contenuti da mantenere nel tempo.

* **Nota assente** (`note`, dal 2026-11-13, `90_end/20261112-58`):

  * uno stile senza nota ha `note` `NULL`, mai la stringa vuota: il `CHECK` `chk_note_stili_note_non_vuota` la rifiuta, anche di soli spazi;
  * nel CSV del seed la cella senza valore porta il token `NULL`; dal pannello, svuotare il campo salva `NULL` (`config.fn_pannello_scrivi`, `20_code/config/20261112-57`).

* **Audit**:

  * `data_insert`, `user_insert`, `data_update`, `user_update` tracciano chi ha inserito/modificato ogni stile e quando;
  * la gestione può essere centralizzata tramite un trigger generico di audit.

---

### Relazioni

`config.note_stili` è una tabella **di dominio** che viene referenziata da:

* **Tabelle delle note** (es. `config.note`, `...note_*`):

  * ogni nota può avere un campo tipo `stile_id` / `note_stile_id` che punta ad uno stile definito qui;
  * in base allo stile, la UI e i template di stampa possono decidere **come rendere** il testo (dimensione, grassetto, colore, icone).

* **Tabelle dei messaggi** (es. `config.messaggi_errore`):

  * eventuale collegamento per definire uno stile predefinito del messaggio (INFO, WARN, ERROR, SYSTEM, ecc.).

* **Tabelle di configurazione editor/testi**:

  * per limitare la lista di stili selezionabili in determinate sezioni dell’applicazione.

> In combinazione con `config.note_tipologie` e `config.lingue`, `config.note_stili` permette di definire **note tipizzate, stilizzate e localizzate**.

---

### Trigger Associati (attesi / suggeriti)

Sebbene non siano definiti nel DDL riportato, è consigliabile introdurre i seguenti trigger:

1. **Trigger di audit** (es. `trg_upd_note_stili_audit_data_user`)

   * **Quando**: `BEFORE UPDATE` su `config.note_stili`.
   * **Cosa fa**: aggiorna `data_update` e `user_update` ad ogni modifica.
   * **Come**: delega a `script.trgfn_audit_data_user_generic()`.

2. **Trigger di protezione del codice interno** (es. `trg_note_stili_protect_codice_interno`)

   * **Quando**: `BEFORE UPDATE`.
   * **Cosa fa**: impedisce la modifica del campo `codice_interno` se già valorizzato, sollevando un errore applicativo.
   * **Obiettivo**: garantire che il **codice funzionale interno resti immutabile**, come previsto dal commento di colonna.

> Questo approccio rende il dominio robusto: gli stili possono essere arricchiti o disattivati, ma i codici interni rimangono stabili nel tempo.

---

### Vantaggi Operativi

* **Uniformità di presentazione**: tutte le componenti che usano note e messaggi condividono lo stesso catalogo stili.
* **Separa logica da presentazione**: la semantica (NORMALE, AVVISO, ECC.) viene configurata a livello di dominio; la resa grafica viene gestita da frontend/templates.
* **Governance**: tramite `attivo`, `note` e `storicizza` è possibile governare in modo fine il ciclo di vita e l’uso degli stili.
* **Estendibilità futura**: eventuali nuovi stili (es. per canali specifici, mobile vs desktop, stampe fiscali) possono essere introdotti senza impattare le tabelle che li usano.

---

> **“Definire chiaramente il dominio degli stili delle note rende l’interfaccia più coerente e permette di governare in modo centralizzato la semantica visuale di messaggi e annotazioni.”**
