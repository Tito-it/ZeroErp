## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_clienti_set_parent_istanza`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — la tabella su cui scatta
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza di cui scrive `parent_istanza_id`
> * [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp) — il perno della catena, quando c'è
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_clienti_stessa_chiave](/dbzero/anagrafiche/funzioni/fn_clienti_stessa_chiave) — il predecessore fra le istanze fittizie
> * [anagrafiche.trgfn_clienti_set_periodo](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_periodo) — il periodo, che per nome viene prima
> * [script.fn_subentro_cliente](/dbzero/script/funzioni/fn_subentro_cliente) — il subentro, da cui la catena nasce di solito
> * [script.fn_clone_catasto_from_parent_by_istanza](/dbzero/script/funzioni/fn_clone_catasto_from_parent_by_istanza) — il catasto che l'istanza nuova eredita dal padre

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_clienti_set_parent_istanza` scrive la **catena delle istanze**: sull'istanza del cliente,
`parent_istanza_id` punta all'istanza del cliente che l'ha preceduto nella stessa fornitura.

---

### Chi è il predecessore

* **Con il PDP**: il cliente più recente sullo stesso PDP, su un'altra istanza, non annullato, con l'attivazione
  nello stesso giorno o prima. Senza un predecessore l'istanza è la prima del PDP, e il padre resta vuoto.
* **Senza PDP, su un'istanza fittizia**: l'ultimo cliente con la stessa chiave del cliente manuale (soggetto,
  utility e azienda dell'installazione), su un'altra istanza, con l'attivazione nello stesso giorno o prima. È
  la fornitura manuale che riparte dopo una chiusura, collegata a quella di prima. La lettura è quella della
  chiave, `anagrafiche.fn_clienti_stessa_chiave`.
* **Senza PDP, su un'istanza vera**: la catena non ha un perno, e il trigger non tocca niente.

Ruolo e utility, nel ramo fittizio, sono già quelli del billing account: per nome il trigger viene dopo la
copia. Quando l'istanza riceve un padre e non ha ancora un catasto, un trigger dell'istanza lo copia dal padre:
è il subentro sullo stesso immobile.

---

### Quando scatta

Sulla nascita del cliente e sulle modifiche che nominano `pdp_id` o `data_attivazione`, e solo se il cliente ha
una data di attivazione. Un cliente che si scrive senza nominare quelle colonne non ricalcola la catena.

---

### ⚠️ Che cosa oggi non copre

* **I rami per il cliente senza data e per l'annullato sono irraggiungibili.** Il corpo ha due rami che tolgono
  il padre all'istanza di un cliente senza attivazione o annullato. Ma il trigger scatta solo con la data di
  attivazione, e la condizione si valuta dopo `anagrafiche.trgfn_clienti_set_periodo`, che all'annullato toglie
  le date: il trigger non scatta. Su una modifica, inoltre, l'annullamento nomina lo stato e non le due colonne
  del trigger. Un cliente annullato resta quindi nella catena con il padre che aveva.
* **Si ricalcola un anello solo**: quello del cliente scritto. Il padre del suo successore non si aggiorna
  quando il cliente si annulla, cambia data di attivazione, entra fra due anelli o passa a un altro PDP.
* **Il predecessore sul PDP si cerca sotto la RLS di chi scrive**: un cliente di un'altra azienda sullo stesso
  PDP non si vede, e l'istanza si aggancia a un anello sbagliato o a nessuno.
* **Un cambio di PDP dell'istanza non arriva**: la catena lo vede solo alla prossima scrittura del cliente che
  nomini una delle due colonne.

---

### Test

* `db/pgtap/anagrafiche/test-istanza-cliente-chain.sql` — la catena sul PDP attraverso i subentri, con un
  annullato inserito.
* `db/pgtap/anagrafiche/test-simula-subentro.sql` — il padre scritto al subentro e il catasto clonato.
* `db/pgtap/anagrafiche/test-cliente-manuale-chiave-unica-v1.sql` — la catena delle istanze fittizie.

---

### Note di migrazione

* 2026-10-14 — nasce il ramo delle istanze fittizie, con il predecessore della stessa chiave del cliente
  manuale. Prima i clienti senza PDP non avevano catena.

---

{% include-markdown "signature-core.md" %}
