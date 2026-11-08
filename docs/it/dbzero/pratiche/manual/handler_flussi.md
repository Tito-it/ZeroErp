## 📘 Documentazione Concettuale – Tabella `pratiche.handler_flussi`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — i template che delegano all'handler l'avvio dello step
> * [pratiche.template_flussi_handler_eventi](/dbzero/pratiche/tabelle/template_flussi_handler_eventi) — i collegamenti fra template, evento ed handler

---

### 🎯 Scopo Principale

La tabella `pratiche.handler_flussi` è il registro degli handler dei flussi: ogni riga associa una
`handler_key` univoca a un handler del backend. Il database tiene solo la chiave; la classe che la
esegue sta nel registro del backend.

---

### Il ruolo nel processo

* Un template di flusso con `handler_id` valorizzato delega l'esecuzione a un handler automatico,
  all'avvio dello step (`IN_CORSO`); un template senza handler è uno step manuale, completato
  dall'operatore.
* `pratiche.template_flussi_handler_eventi` permette di eseguire un handler anche al `COMPLETATO` di
  uno step, in funzione dell'esito. Il registro degli handler è lo stesso.
* I parametri operativi dell'handler stanno sul template (`handler_params`) o sul collegamento
  all'evento, non qui.

Il backend risolve `handler_key` nella classe dell'handler e le passa il flusso e la pratica.

---

### ⛔ Il registro del database e quello del backend dicono la stessa cosa

Un handler si ritira prima nel database (collegamenti spenti, poi handler spento) e solo dopo dal
codice: l'ordine e il perché stanno in `pratiche.template_flussi_handler_eventi`. Il database aiuta a
tenerlo: un handler non si spegne finché un template o un collegamento all'evento attivi lo usano. La
coerenza fra le chiavi del database e quelle del backend la verifica un test del backend.

---

### Le colonne che non si capiscono dal nome

* `handler_key` — la chiave, unica, con cui il backend trova la classe.
* `codice` — un codice leggibile, unico, scritto in maiuscolo.

---

### Convenzioni

È un registro di configurazione: niente storico e niente `tx_id`. I trigger standard (audit, blocco
della disattivazione con figli attivi, codice maiuscolo) li applicano i runner del framework di
automazione.

---

{% include-markdown "signature-core.md" %}
