## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — la tabella su cui è montata: l'unità e il civico dell'istanza
> * [anagrafiche.catasto_unita_immobiliari_indirizzi](/dbzero/anagrafiche/tabelle/catasto_unita_immobiliari_indirizzi) — la tabella ponte che scrive
> * [anagrafiche.catasto_unita_immobiliari](/dbzero/anagrafiche/tabelle/catasto_unita_immobiliari) — l'unità catastale
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — il civico
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_iu_clone_catasto_from_parent](/dbzero/anagrafiche/funzioni/trgfn_iu_clone_catasto_from_parent) — il clone del subentro, la cui scrittura fa scattare questo trigger
>
> Guide:
>
> * [Il catasto delle istanze](/guide/catasto-delle-istanze) — il flusso intero del catasto

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo` fa seguire l'istanza alla tabella ponte e all'unità
catastale: scrive la coppia (unità catastale, civico) dell'istanza, quando l'istanza ha tutti e due, e al cambio
toglie la coppia di prima e l'unità che nessuno nomina più. Chi aggancia un'unità a un'istanza non scrive il
legame col civico: lo deriva il database.

---

### ⭐ L'istanza dice la coppia, la ponte la ricorda

L'istanza nomina la sua unità (`catasto_unita_immobiliare_id`) e il suo civico (`indirizzo_dettaglio_id`), e la
coppia va in `anagrafiche.catasto_unita_immobiliari_indirizzi`. Il trigger è montato due volte, dopo la scrittura
di `anagrafiche.istanze_utilities`:

* `trg_istanze_utilities_z40_sync_catasto_unita_indirizzo_ins` — l'istanza che nasce con unità e civico;
* `trg_istanze_utilities_z40_sync_catasto_unita_indirizzo_upd` — la modifica che cambia l'unità o il civico. Il
  trigger confronta i valori di prima con quelli nuovi: una riscrittura uguale non fa niente.

Lo fa anche al subentro: il clone dell'unità si scrive sull'istanza con una modifica, e la copia si lega così al
civico dell'istanza nuova. La fase `z40` gira prima del clone (`z50`).

Se manca l'unità o il civico, non c'è coppia nuova da scrivere.

---

### Al cambio, la ponte segue l'istanza

Quando l'istanza cambia unità o civico, nell'ordine:

1. **La coppia di prima esce.** La coppia (unità di prima, civico di prima) si toglie dalla ponte, se nessun'altra
   istanza ha la stessa coppia. Le coppie scritte a mano con altri civici restano: la ponte è molti a molti. Il
   civico lasciato, senza più legami, si può spegnere.
2. **L'unità lasciata si cancella.** Se l'istanza è passata a un'altra unità e nessun'altra istanza nomina più la
   prima, la prima si cancella. Lo storico di `catasto_unita_immobiliari` ne tiene la versione, e i suoi legami
   nella ponte se ne vanno con lei.
3. **La coppia nuova entra**, se l'istanza ha unità e civico.

---

### Idempotente

La coppia già presente non si duplica e non dà errore: l'inserimento si appoggia al vincolo unico
`uq_catunitaindir`. Il trigger non solleva errori propri; un civico spento lo rifiuta, a fine transazione, il
controllo dell'automazione ATTIVO sulla tabella ponte.

La regola intera sta nella guida [Il catasto delle istanze](/guide/catasto-delle-istanze).

---

### ⚠️ Che cosa oggi non copre

* **La cancellazione dell'istanza** non tocca l'unità: un'istanza cancellata lascia la sua unità senza nessuno che
  la nomini.

---

### Test

* `db/pgtap/anagrafiche/test-simula-subentro.sql` — la coppia scritta quando la prima istanza riceve la sua unità,
  e quella della copia al subentro.
* `db/pgtap/anagrafiche/test-catasto-unita-della-sua-istanza-v1.sql` (test 6-10) — il cambio di civico toglie la
  coppia di prima e scrive la nuova, il civico lasciato si spegne, il cambio di unità cancella quella che nessuno
  nomina più e lega la nuova al civico.

---

{% include-markdown "signature-core.md" %}
