## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo`

> **Ultimo aggiornamento**: 22 novembre 2026
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

`anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo` scrive nella tabella ponte la coppia (unità catastale, civico)
di un'istanza, quando l'istanza ha tutti e due. Chi aggancia un'unità a un'istanza non scrive il legame col civico:
lo deriva il database.

---

### ⭐ L'istanza dice la coppia, la ponte la ricorda

L'istanza nomina la sua unità (`catasto_unita_immobiliare_id`) e il suo civico (`indirizzo_dettaglio_id`). Il
trigger `trg_iu_z40_sync_catasto_unita_indirizzo_aft_ins_upd` scatta dopo la nascita dell'istanza e dopo ogni
modifica di una delle due colonne, e porta la coppia in `anagrafiche.catasto_unita_immobiliari_indirizzi`. Lo fa
anche al subentro: il clone dell'unità si scrive sull'istanza con una modifica, e la copia si lega così al civico
dell'istanza nuova.

Se manca l'unità o il civico, non c'è coppia e il trigger non fa niente.

---

### Idempotente, e solo in aggiunta

La coppia già presente non si duplica e non dà errore: l'inserimento si appoggia al vincolo unico
`uq_catunitaindir`. Il trigger non solleva errori propri; un civico spento lo rifiuta, a fine transazione, il
controllo dell'automazione ATTIVO sulla tabella ponte.

Il trigger aggiunge e non toglie: non cancella né corregge legami esistenti.

---

### ⚠️ Che cosa oggi non copre

* **La coppia di prima resta.** Un'istanza che cambia civico o unità aggiunge la coppia nuova e lascia quella
  vecchia, che continua a impedire lo spegnimento del civico.

---

### Test

* `db/pgtap/anagrafiche/test-simula-subentro.sql` — la coppia scritta quando la prima istanza riceve la sua unità,
  e quella della copia al subentro.

---

{% include-markdown "signature-core.md" %}
