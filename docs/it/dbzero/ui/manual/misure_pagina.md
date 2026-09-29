## 📘 Documentazione Concettuale – Tabella `ui.misure_pagina`

> 👀 **Vedi anche**
>
> **Chi la cita:** [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) (FK) · [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) (guard)
>
> **La lettura per l'applicazione:** [fn_get_misure_pagina](/dbzero/ui/funzioni/fn_get_misure_pagina)
>
> **Le domande:** [fn_misura_pagina_ammessa](/dbzero/ui/funzioni/fn_misura_pagina_ammessa) · [fn_misura_pagina_default](/dbzero/ui/funzioni/fn_misura_pagina_default) · il rifiuto: [fn_guard_misura_pagina](/dbzero/ui/funzioni/fn_guard_misura_pagina)

---

### 🎯 Scopo Principale
(scritta il 30-09-2026)

Sotto ogni lista c'è il selettore **«righe per pagina»**. Questa tabella dice
**quali misure offre** (oggi 10, 25, 50, 100) e **quali sono i default**:

| Uso | Dove | Oggi |
| --- | --- | --- |
| `COMPATTA` | liste nei drawer e nei dialog | 10 |
| `PAGINA` | liste a pagina intera, e il ripiego quando nessuno ha scelto | 25 |

È la **sede unica** (decisioni di Tid del 29-09-2026): database, backend e
frontend leggono le misure da qui. Prima erano scritte in tre posti — due
costanti del frontend e un 25 ripetuto cinque volte nella funzione che risolve
le liste — e nessuno rifiutava una misura fuori elenco: il 28-09 un preset a 15
lasciava il selettore **vuoto**, senza nessun errore.

---

### Le regole

* **Un preset** può dichiarare solo una misura di questa tabella, o nessuna
  (vuol dire «il default»). Una misura diversa viene rifiutata con un messaggio
  che elenca quelle ammesse.
* **La misura che una persona salva** per una lista vale lo stesso.
* **La lista risponde sempre una misura di questa tabella**: quella scelta, se
  è ammessa; altrimenti il default `PAGINA`.
* Una misura **in uso da un preset non si può togliere**.
* La tabella la scrive **solo il file di seed**
  (`80_data/sql/ui/misure_pagina.csv`): l'applicazione la legge soltanto.

---

### Come si cambia

* **Aggiungere una misura**: una riga nel CSV. Compare in tutti i paginatori.
* **Spostare un default** (per esempio `COMPATTA` da 10 a 25): in due passaggi
  del CSV — prima si toglie l'uso dalla riga vecchia, poi lo si mette sulla
  nuova — perché un uso non può stare su due righe nemmeno per un istante.
* **Togliere una misura**: tolta dal CSV non sparisce da sola (il caricamento
  aggiunge e aggiorna, non cancella); serve una cancellazione esplicita, che il
  database rifiuta finché un preset la usa.

---

### Storia

* 2026-09-30 — nasce (`20260930-01` → `-13`). Brief: brief-db-misure-pagina-catalogo.

{% include-markdown "signature-core.md" %}
