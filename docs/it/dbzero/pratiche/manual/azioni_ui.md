## 📘 Documentazione Concettuale – Tabella `pratiche.azioni_ui`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — il template che offre l'attività, con `azione_ui_id`
> * [pratiche.handler_flussi](/dbzero/pratiche/tabelle/handler_flussi) — il gemello lato server

---

### 🎯 Scopo Principale

La tabella `pratiche.azioni_ui` è il catalogo delle attività interattive che un passo di pratica può
offrire all'operatore: ogni riga è una chiave che il frontend risolve in un componente di dominio
(per esempio il drawer di un preventivo aperto dentro la pratica).

È lo specchio, lato interfaccia, del registro degli handler: `pratiche.handler_flussi` lega una chiave
a un'automazione eseguita dal backend sull'evento di flusso, `pratiche.azioni_ui` lega una chiave a
un'attività che l'operatore svolge.

---

### ⭐ Il database conserva la chiave, non la interpreta

`azione_ui_key` è unica e il database non le dà nessun significato, esattamente come `handler_key`: la
registrazione effettiva delle attività vive nel registro del frontend, che risolve la chiave nel
componente con un caricamento differito, così il dominio delle pratiche non dipende da quello delle
vendite. Il catalogo è il riferimento delle chiavi ammesse.

* Un template di flusso con `azione_ui_id` valorizzato offre l'attività nel suo passo.
* Un template senza `azione_ui_id` non offre nessuna attività interattiva: il passo si avvia e si
  completa nel modo standard.
* Una chiave che il frontend non conosce non produce nessun pulsante: è il comportamento sicuro.

Una voce entra nel catalogo quando nasce il flusso che la usa: una riga, un consumatore reale, come in
`pratiche.handler_flussi`.

---

### Le regole della tabella

* `codice` è unico, ed è la forma leggibile della voce; si scrive in maiuscolo.
* Una voce non si disattiva finché un template di flusso la usa.
* È un registro di configurazione: non si storicizza e non porta la transazione.

---

{% include-markdown "signature-core.md" %}
