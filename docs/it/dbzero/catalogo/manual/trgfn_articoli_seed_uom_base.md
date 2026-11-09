## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_articoli_seed_uom_base`

> **Ultimo aggiornamento**: 9 novembre 2026
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
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — il controllo che vuole l'articolo attivo sotto una riga attiva
> * [catalogo.trgfn_articoli_uom_operativa_guard_base](/dbzero/catalogo/funzioni/trgfn_articoli_uom_operativa_guard_base) — tiene giusta la riga base dopo la nascita

---

### 🎯 Scopo Principale

Fa nascere ogni articolo con la sua riga base in `catalogo.articoli_uom_operativa`: alla
creazione dell'articolo scrive la riga sull'unità di `articoli.uom_id`, con `is_base` vero,
fattore 1, senza date, attiva o spenta come l'articolo.

Senza questa riga l'articolo avrebbe l'unità base in testata ma non fra le sue unità
operative, e la lista delle unità dell'articolo partirebbe vuota.

---

### Come lavora

Gira dopo l'inserimento di ogni articolo, riga per riga, e inserisce la riga base. L'articolo
è nuovo, quindi nessuna mappatura può già puntarvi: la funzione non prevede una riga che
esiste già.

La riga base segue lo stato dell'articolo: un articolo che nasce spento ha la riga base
spenta. Una riga attiva sotto un articolo spento la rifiuterebbe, alla fine della
transazione, il controllo che vuole l'articolo attivo.

`articoli.uom_id` è obbligatorio, quindi un articolo senza unità non arriva fin qui: lo ferma
prima il vincolo di colonna. Dopo la creazione `articoli.uom_id` è bloccato: la riga base non
deve seguire un cambio di unità che non può avvenire.

Il trigger porta il prefisso di fase `a10`, che per convenzione è dei guard, ma è un seed
che scrive dopo l'inserimento, non un controllo.

---

### Dopo la nascita

La riga resta giusta: fattore 1 e nessuna data li impone un CHECK della tabella, e il guard
della riga base impedisce di spostarla su un'altra unità, di toglierle `is_base` e di
cancellarla finché c'è l'articolo.

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
  sua riga base spenta.

---

### Note di migrazione

* 2026-04-07 — nasce.
* 2026-11-09 — la riga base nasce attiva o spenta come l'articolo; senza la clausola sulla riga
  già esistente (brief-db-revisione-catalogo, giro 2).

---

{% include-markdown "signature-core.md" %}
