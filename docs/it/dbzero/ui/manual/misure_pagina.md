## 📘 Documentazione Concettuale – Tabella `ui.misure_pagina`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — il preset dichiara una misura del catalogo, o nessuna
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — la misura che una persona sceglie per una lista
> * [ui.dashboard_preset](/dbzero/ui/tabelle/dashboard_preset) — il massimo di card della dashboard, che non passa da qui
>
> Approfondimento funzioni:
>
> * [ui.fn_get_misure_pagina](/dbzero/ui/funzioni/fn_get_misure_pagina) — la lettura unica per l'applicazione
> * [ui.fn_misura_pagina_ammessa](/dbzero/ui/funzioni/fn_misura_pagina_ammessa) — la misura è nel catalogo?
> * [ui.fn_misura_pagina_default](/dbzero/ui/funzioni/fn_misura_pagina_default) — la misura di default per un uso
> * [ui.fn_guard_misura_pagina](/dbzero/ui/funzioni/fn_guard_misura_pagina) — il rifiuto di una misura fuori catalogo
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — la lista risponde sempre una misura del catalogo
> * [ui.trgfn_misure_pagina_guard_default_per_uso](/dbzero/ui/funzioni/trgfn_misure_pagina_guard_default_per_uso) — a fine transazione, un default per ogni uso
> * [ui.trgfn_misure_pagina_ritira_dalle_preferenze](/dbzero/ui/funzioni/trgfn_misure_pagina_ritira_dalle_preferenze) — la misura ritirata esce dalle preferenze
>
> Guide:
>
> * [Configurazione delle liste](/guide/configurazione-liste) — preset e preferenze delle liste

---

### 🎯 Scopo Principale

`ui.misure_pagina` è il catalogo delle misure «righe per pagina» che i paginatori dell'applicazione
offrono, e delle due misure di default: una per le liste compatte (drawer e dialog), una per le liste
a pagina intera.

Il selettore sotto ogni lista mostra le misure di questo catalogo, in ordine crescente. Preset e
preferenze delle liste configurabili possono dichiarare solo una di queste misure.

---

### Una riga per misura, e la misura è la chiave

La misura (quante righe) è unica e positiva, ed è la chiave con cui gli altri la citano: il preset
di una lista punta al numero, non all'`id`. Una misura non si riscrive, e un lucchetto di colonna lo impone
(`E_UI_MISURA_PAGINA_IMMUTABILE`): una misura nuova è una riga nuova, e la vecchia si toglie.

---

### Un default per ogni uso

`uso_default` dice se la riga è il default di un uso. Gli usi sono un vocabolario chiuso, l'enum
`ui.uso_misura_pagina`, lo stesso con cui ogni lista dichiara dove si mostra
([lista_definizione](/dbzero/ui/tabelle/lista_definizione), `uso_misura`):

* `COMPATTA` — liste nei drawer e nei dialog;
* `PAGINA` — liste a pagina intera.

Una riga senza uso è una misura solo offerta. Ogni uso sta su **esattamente una** riga: al più una
la garantisce l'indice unico, almeno una un trigger differito, che a fine transazione rifiuta un
catalogo rimasto senza il default di un uso. Spostare un default da una misura a un'altra si fa
quindi in una transazione sola: togliere l'uso da una riga e darlo all'altra. Il default si legge
con [fn_misura_pagina_default](/dbzero/ui/funzioni/fn_misura_pagina_default), che non risponde mai
vuoto: un uso senza riga è un catalogo rotto, e la funzione solleva.

---

### Chi cita il catalogo, e come

* **Il preset di una lista** ha una FK verso la misura, e un guard che rifiuta prima della FK con un
  codice parlante. Nessuna misura vuol dire «il default».
* **La preferenza di una persona** porta la misura dentro un campo JSONB: una FK non ci arriva, e la
  controlla alla scrittura il guard di forma della preferenza
  ([trgfn_preferenza_guard_forma](/dbzero/ui/funzioni/trgfn_preferenza_guard_forma)). Quando una
  misura si toglie dal catalogo, esce anche dalle preferenze che la citano: il resto della
  preferenza resta, e la persona torna allo standard.
* **La lista configurabile**, quando si apre, risponde sempre una misura del catalogo: quella della
  preferenza se è nel catalogo, altrimenti quella del preset di base se è nel catalogo, altrimenti il
  default dell'uso della lista (`COMPATTA` o `PAGINA`).
* **Tutti i paginatori**, anche quelli che non sono liste configurabili, leggono misure e default
  con [fn_get_misure_pagina](/dbzero/ui/funzioni/fn_get_misure_pagina).

---

### ⛔ La scrive solo il seed

La tabella è posseduta dal seed: l'applicazione ha solo `SELECT`, e non ci sono policy RLS. Una
misura nasce, si sposta di uso o si toglie con un changeSet.

---

### ⚠️ Il massimo di card della dashboard è un'altra regola

`ui.dashboard_preset.dimensione_max` e la `dimensione_max` della preferenza di dashboard non sono
misure di questo catalogo. Non dicono quante righe offre un paginatore, ma **quante card al più** la
dashboard mostra: un tetto, non una voce di un menu. Il catalogo non le controlla: il tetto da 1 a 100,
per il preset e per la preferenza, lo dice [fn_dimensione_max_ammessa](/dbzero/ui/funzioni/fn_dimensione_max_ammessa).

---

### ⚠️ Che cosa oggi non copre

* **Una misura citata da un preset non si toglie, ma col 23503 grezzo** della FK, senza un codice di
  catalogo. Il catalogo lo scrive solo un changeSet, e chi lo scrive legge la FK.
* **Il backend ha una sua costante** per le chiamate API fuori dalle liste configurabili, che non
  passano da questo catalogo.

---

### Codici errore

* `E_UI_MISURA_PAGINA_NON_AMMESSA` — un preset o una preferenza con una misura fuori catalogo, o con
  un valore che non è un numero intero.
* `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE` — il catalogo non ha il default chiesto: alla lettura, o a
  fine transazione quando una scrittura lascia un uso senza default.
* `E_UI_MISURA_PAGINA_IMMUTABILE` — si riscrive una misura.
* Il `DELETE` o l'UPDATE di una misura citata da un preset arriva come violazione della FK
  `fk_lista_preset_misure_pagina`.

---

### Test

* `db/pgtap/ui/test-misure-pagina-v1.sql` — un default per uso, la lettura unica, il rifiuto di
  preset e preferenze fuori catalogo, il resolver che risponde la misura scelta, i permessi
  dell'applicazione.
* `db/pgtap/ui/test-ui-misure-catalogo-e-uso-v1.sql` — un default per ogni uso (lo spostamento in una
  transazione), la misura che non si riscrive, il ritiro che esce dalle preferenze, il ripiego
  sull'uso della lista, i preset senza default di colonna.
* `db/pgtap/ui/test-fn-resolve-lista-config-cascata-per-chiave-v1.sql` — la misura per chiave:
  preferenza, preset di base, default `PAGINA`.
* `db/pgtap/ui/test-fn-resolve-lista-config.sql` — la misura del preset e della preferenza nella
  cascata.

---

### Note di migrazione

* 2026-09-30 — nasce il catalogo: le misure prima stavano in due costanti del frontend e in un
  numero ripetuto nella funzione che risolve le liste, e nessuno rifiutava una misura fuori elenco.
* 2026-11-01 — la lista risponde la misura per chiave: la preferenza, poi il preset di base, poi il
  default.
* 2026-11-21 — l'uso diventa un vocabolario condiviso con le liste, che dichiarano il proprio; il
  catalogo ha sempre un default per uso, la misura non si riscrive, e il ritiro di una misura esce
  dalle preferenze.

---

{% include-markdown "signature-core.md" %}
