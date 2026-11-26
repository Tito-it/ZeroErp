## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_iu_clone_catasto_from_parent`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — la tabella su cui è montata, e di cui il clone scrive `catasto_unita_immobiliare_id`
> * [anagrafiche.catasto_unita_immobiliari](/dbzero/anagrafiche/tabelle/catasto_unita_immobiliari) — dove nasce la copia dell'unità
>
> Approfondimento funzioni:
>
> * [script.fn_clone_catasto_from_parent_by_istanza](/dbzero/script/funzioni/fn_clone_catasto_from_parent_by_istanza) — il clone vero e proprio
> * [script.fn_get_catasto_source_by_istanza](/dbzero/script/funzioni/fn_get_catasto_source_by_istanza) — l'unità da copiare, quella dell'istanza precedente
> * [anagrafiche.trgfn_clienti_set_parent_istanza](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_parent_istanza) — chi scrive la catena che fa scattare il clone
> * [anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo](/dbzero/anagrafiche/funzioni/trgfn_iu_sync_catasto_unita_indirizzo) — il legame della copia col civico
>
> Guide:
>
> * [Il catasto delle istanze](/guide/catasto-delle-istanze) — il flusso intero del catasto

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_iu_clone_catasto_from_parent` dà all'istanza del subentro una copia dell'unità catastale
dell'istanza che la precede. Scatta quando nasce il legame con l'istanza precedente, e passa la mano a
`script.fn_clone_catasto_from_parent_by_istanza`.

---

### ⭐ Al subentro il catasto si copia, non si condivide

L'istanza nuova riceve una riga nuova di `catasto_unita_immobiliari`, con gli stessi dati catastali della
precedente: due istanze, due unità. Così una rettifica sul catasto di chi subentra non cambia quello di chi è
uscito, che resta com'era sull'istanza chiusa. Un'unità è di un'istanza sola: lo scrive l'indice
`uq_istanze_utilities_catasto_unita_immobiliare`.

---

### Quando scatta

Il clone scatta quando nasce il legame con l'istanza precedente, sempre con l'istanza senza unità e col civico.
È montato due volte, dopo la scrittura di `anagrafiche.istanze_utilities`:

* `trg_istanze_utilities_z50_clone_catasto_from_parent_ins` — l'istanza che nasce con la precedente già scritta;
* `trg_istanze_utilities_z50_clone_catasto_from_parent_upd` — la modifica che cambia la precedente. Il trigger
  confronta il valore di prima con quello nuovo: una riscrittura uguale di `parent_istanza_id` non clona.

Di solito la precedente la scrive `anagrafiche.trgfn_clienti_set_parent_istanza`, alla scrittura del cliente: il
clone arriva allora con la nascita del cliente sull'istanza nuova. Un'istanza fittizia senza civico non riceve il
clone.

Il clone copia ciò che la precedente ha quando il legame nasce: un'unità che compare dopo sulla precedente non
arriva, e la rettifica dell'istanza nuova si fa su di lei.

La funzione del trigger non decide niente: le condizioni stanno sul trigger, il lavoro nella funzione di `script`.

---

### Che cosa fa il clone

* **L'istanza ha già un'unità**: niente, resta quella.
* **L'istanza precedente non ha un'unità**: niente, senza errore. Il subentro e la nascita del cliente proseguono.
* **Altrimenti**: copia l'unità della precedente in una riga nuova, compreso il flag dello storico, e la scrive
  sull'istanza. Quella scrittura cambia l'unità, e fa scattare
  `anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo`, che lega la copia al civico dell'istanza nuova.

La sorgente è solo la precedente diretta: non si risale la catena. Copia l'unità, non i suoi legami coi civici:
la copia nasce legata al solo civico dell'istanza. La riga dell'istanza è bloccata per la durata del clone, così
due scritture concorrenti non creano due copie.

---

### ⚠️ Che cosa oggi non copre

* **Il clone avviene una volta.** Una catena che si svuota perché il cliente è annullato lascia sull'istanza
  l'unità copiata dalla precedente di allora.

---

### Test

* `db/pgtap/anagrafiche/test-simula-subentro.sql` — il subentro sullo stesso PDP: la catena scritta dal cliente
  nuovo, l'unità clonata con un id diverso e gli stessi dati, il legame della copia col civico.
* `db/pgtap/anagrafiche/test-catasto-unita-della-sua-istanza-v1.sql` (test 3-5) — l'istanza che nasce con la
  precedente riceve il clone, un'unità sua; la precedente riscritta uguale non clona.

---

### Note di migrazione

* 2026-02-15 — senza un'unità sulla precedente il clone non solleva più errore; il codice
  `CATASTO_SOURCE_NOT_FOUND` esce dal catalogo dei messaggi il 2026-08-05.
* 2026-11-25 — il clone scatta anche all'INSERT con la precedente, e all'UPDATE solo se la precedente cambia;
  i due montaggi prendono i nomi `trg_istanze_utilities_z50_…_ins` e `_upd`.

---

{% include-markdown "signature-core.md" %}
