## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_flussi_guard_chiusura_prematura`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — la tabella su cui è montato il guard
>
> Approfondimento funzioni:
>
> * [pratiche.fn_check_pratica_chiudibile](/dbzero/pratiche/funzioni/fn_check_pratica_chiudibile) — la regola «la pratica si può chiudere», che il guard interroga
> * [pratiche.trgfn_flussi_autochiusura_pratica](/dbzero/pratiche/funzioni/trgfn_flussi_autochiusura_pratica) — l'auto-chiusura che segue il completamento del flusso di chiusura

---

### 🎯 Scopo Principale

Il **flusso di chiusura** (il flusso il cui template ha `chiude_pratica`) è lo step che chiude la
pratica: non può essere completato finché la pratica **non è chiudibile**. Il guard è coerente con
quello di chiusura della pratica, ed evita che l'auto-chiusura conseguente fallisca, e con lei
l'intera transazione di completamento.

---

### Quando scatta

* Alla **transizione** dello stato del flusso verso `COMPLETATO`; un aggiornamento che lascia lo
  stato com'è non viene esaminato.
* Solo per i flussi il cui template ha `chiude_pratica`; un flusso di un template che non chiude la
  pratica passa.
* È un guard della fase `_a10_` dell'aggiornamento dello stato, e convive con gli altri guard della
  stessa fase sul flusso (esito completato, pratica terminale, transizione).

---

### ⭐ Il flusso di chiusura non conta sé stesso

Il completamento è ammesso solo se `pratiche.fn_check_pratica_chiudibile` risponde di sì
**escludendo il flusso di chiusura stesso**, in due modi:

* il suo **template** dai flussi obbligatori bloccanti;
* la sua **istanza** dai flussi ancora aperti.

Nel momento in cui il guard parla il flusso è ancora in corso: senza l'esclusione dell'istanza si
vedrebbe come un flusso aperto, e il suo completamento fallirebbe sempre.

⚠️ Il flusso di chiusura va quindi eseguito **per ultimo**: prima si completano (o si rendono non
percorribili) gli altri obbligatori e si chiudono i flussi aperti.

---

### Codici errore

* `E_PRATICHE_CHIUSURA_FLUSSO_PREMATURO` — completamento del flusso di chiusura con altri flussi
  obbligatori bloccanti, o altri flussi ancora aperti.

---

### Test

* `db/pgtap/pratiche/test-autochiusura-pratica.sql`, scenario B (tipo di prestazione **con** flusso
  di chiusura) — il completamento con un altro obbligatorio pendente fallisce; completato l'altro
  obbligatorio la pratica resta aperta; completato il flusso di chiusura la pratica si chiude.

---

{% include-markdown "signature-core.md" %}
