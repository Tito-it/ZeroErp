## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_articoli_seed_uom_base`

> **Ultimo aggiornamento**: 11 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — la tabella su cui è montata, alla creazione dell'articolo
> * [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa) — dove scrive la riga base
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_articoli_uom_operativa_guard_base](/dbzero/catalogo/funzioni/trgfn_articoli_uom_operativa_guard_base) — tiene giusta la riga base dopo la nascita

---

### 🎯 Scopo Principale

Fa nascere ogni articolo con la sua riga base in `catalogo.articoli_uom_operativa`: alla
creazione dell'articolo scrive la riga sull'unità di `articoli.uom_id`, con `is_base` vero,
fattore 1, senza date, sempre attiva.

Senza questa riga l'articolo avrebbe l'unità base in testata ma non fra le sue unità
operative, e la lista delle unità dell'articolo partirebbe vuota.

---

### Come lavora

Gira dopo l'inserimento di ogni articolo, riga per riga, e inserisce la riga base. L'articolo
è nuovo, quindi nessuna mappatura può già puntarvi: la funzione non prevede una riga che
esiste già.

La riga base nasce attiva anche sotto un articolo che nasce spento. La base non ha stati: vale
1 a ogni data, e da lei l'unità base prende le regole della quantità, che una riga spenta non
darebbe. Il legame fra la mappatura e l'attivo dell'articolo è fra le eccezioni
dell'automazione ATTIVO: l'articolo si spegne e si riaccende con la sua base intatta.

`articoli.uom_id` è obbligatorio, quindi un articolo senza unità non arriva fin qui: lo ferma
prima il vincolo di colonna. Dopo la creazione `articoli.uom_id` è bloccato: la riga base non
deve seguire un cambio di unità che non può avvenire.

Il trigger porta il prefisso di fase `a10`, che per convenzione è dei guard, ma è un seed
che scrive dopo l'inserimento, non un controllo.

---

### Dopo la nascita

La riga resta giusta: fattore 1 e nessuna data li impone un CHECK della tabella, e il guard
della riga base impedisce di spostarla su un'altra unità, di toglierle `is_base`, di
spegnerla e di cancellarla finché c'è l'articolo.

---

### Codici errore

La funzione non ne solleva di suoi. Un errore che nasce qui è quello di un vincolo della
tabella figlia.

---

### Test

* `db/pgtap/catalogo/test-articoli-seed-uom-base-lock.sql` — la funzione e il trigger ci
  sono; un articolo nuovo ha la sua riga base, e una sola; `articoli.uom_id` non si modifica,
  se non con l'interruttore di manutenzione.

* `db/pgtap/catalogo/test-uom-fattore-e-regole-v1.sql` — un articolo creato spento nasce, con la
  sua riga base attiva.

---

### Note di migrazione

* 2026-04-07 — nasce.
* 2026-11-09 — la riga base nasce attiva o spenta come l'articolo; senza la clausola sulla riga
  già esistente (brief-db-revisione-catalogo, giro 2).
* 2026-11-11 — la riga base nasce sempre attiva: il legame con l'attivo dell'articolo è fra le
  eccezioni, e una base spenta toglieva le regole della quantità (brief-db-revisione-catalogo,
  Q34).

---

{% include-markdown "signature-core.md" %}
