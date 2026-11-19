## 📘 Documentazione Concettuale – Tabella `ui.misure_pagina`

> **Ultimo aggiornamento**: 18 novembre 2026
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
di una lista punta al numero, non all'`id`. Una misura non si riscrive: se ne aggiunge una, o se ne
toglie una.

---

### Due default, al più uno per uso

`uso_default` dice se la riga è il default di un uso:

* `COMPATTA` — liste nei drawer e nei dialog;
* `PAGINA` — liste a pagina intera, e il ripiego della lista configurabile quando né la preferenza né
  il preset dichiarano una misura.

Una riga senza uso è una misura solo offerta. Ogni uso sta su al più una riga. Il default si legge
con [fn_misura_pagina_default](/dbzero/ui/funzioni/fn_misura_pagina_default), che non risponde mai
vuoto: un uso senza riga è un catalogo rotto, e la funzione solleva.

---

### Chi cita il catalogo, e come

* **Il preset di una lista** ha una FK verso la misura, e un guard che rifiuta prima della FK con un
  codice parlante. Nessuna misura vuol dire «il default».
* **La preferenza di una persona** porta la misura dentro un campo JSONB: una FK non ci arriva, e la
  controlla il guard alla scrittura della preferenza.
* **La lista configurabile**, quando si apre, risponde sempre una misura del catalogo: quella della
  preferenza se è nel catalogo, altrimenti quella del preset di base se è nel catalogo, altrimenti il
  default `PAGINA`.
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
dashboard mostra: un tetto, non una voce di un menu. Il catalogo non le controlla.

---

### ⚠️ Che cosa oggi non copre

* **Una misura citata da una preferenza si toglie.** La FK arriva solo dai preset: togliere dal
  catalogo, o riscrivere, una misura che sta solo nelle preferenze riesce, e la preferenza resta con
  una misura che non c'è più. La lista la scarta in lettura e risponde lo standard; ma il guard della
  preferenza rifiuta ogni modifica della configurazione che conservi quella misura, anche se tocca
  soltanto le colonne.
* **La misura si riscrive.** Nessun lucchetto ferma l'UPDATE di `misura`: se nessun preset la cita
  passa, le preferenze che la citavano restano orfane e l'uso di default segue la riga sul numero
  nuovo.
* **Il catalogo può restare senza un default.** Il vincolo dice «al più una riga per uso», non
  «esattamente una»: togliere la riga del default, o il suo uso, riesce, e da quel momento ogni
  lettura delle misure solleva `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE`, con tutti i paginatori.
* **Una misura citata da un preset non si toglie, ma col 23503 grezzo** della FK, senza un codice di
  catalogo.
* **Il default `PAGINA` non sta solo qui.** `ui.lista_preset.pagina_dimensione` ha come default di
  colonna un numero scritto: un preset inserito senza la misura nasce con quel numero e non con
  «nessuna misura», quindi non segue più il default del catalogo; e il backend ha una sua costante
  per le chiamate API senza misura.
* **Il default `COMPATTA` non arriva alle liste configurabili.** Il ripiego della lista è sempre
  `PAGINA`: una lista configurabile mostrata compatta ha la misura scritta nel suo preset.

---

### Codici errore

* `E_UI_MISURA_PAGINA_NON_AMMESSA` — un preset o una preferenza con una misura fuori catalogo, o con
  un valore che non è un numero intero.
* `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE` — il catalogo non ha il default chiesto.
* Il `DELETE` o l'UPDATE di una misura citata da un preset arriva come violazione della FK
  `fk_lista_preset_misure_pagina`.

---

### Test

* `db/pgtap/ui/test-misure-pagina-v1.sql` — un default per uso, la lettura unica, il rifiuto di
  preset e preferenze fuori catalogo, il resolver che risponde la misura scelta, i permessi
  dell'applicazione.
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

---

{% include-markdown "signature-core.md" %}
