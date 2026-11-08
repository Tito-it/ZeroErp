## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_articoli_seed_uom_base`

> **Ultimo aggiornamento**: 8 novembre 2026
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

---

### 🎯 Scopo Principale

Fa nascere ogni articolo con la sua riga base in `catalogo.articoli_uom_operativa`: alla
creazione dell'articolo scrive la riga sull'unità di `articoli.uom_id`, con `is_base` vero,
fattore 1 e attiva.

Senza questa riga l'articolo avrebbe l'unità base in testata ma non fra le sue unità
operative, e la lista delle unità dell'articolo partirebbe vuota.

---

### Come lavora

Gira dopo l'inserimento di ogni articolo, riga per riga. Se per quell'articolo e quell'unità
una riga esiste già, non fa niente: non la aggiorna e non dà errore.

All'inserimento di un articolo nuovo il caso non capita, perché l'id è nuovo e nessuna
mappatura può già puntarvi: quella clausola rende solo la funzione ripetibile, se la si
lanciasse di nuovo sugli stessi articoli.

`articoli.uom_id` è obbligatorio, quindi un articolo senza unità non arriva fin qui: lo ferma
prima il vincolo di colonna. Dopo la creazione `articoli.uom_id` è bloccato: la riga base non
deve seguire un cambio di unità che non può avvenire.

Il trigger porta il prefisso di fase `a10`, che per convenzione è dei guard, ma è un seed
che scrive dopo l'inserimento, non un controllo.

---

### ⚠️ Che cosa oggi non copre

* **Un articolo creato spento non si salva.** La riga base nasce sempre attiva, anche quando
  l'articolo nasce con `attivo = false`. Una riga attiva vuole l'articolo attivo, e il
  controllo scatta alla fine della transazione: l'inserimento dell'articolo spento viene
  rifiutato con `E_ATTIVO_PADRE_NON_ATTIVO`.
* **La riga che scrive non resta protetta.** Dopo la nascita, la riga base si può modificare
  (unità, flag, fattore) o cancellare, e nessun vincolo le impone il fattore 1: questa funzione
  la crea giusta, ma nessuno la tiene giusta.

---

### Codici errore

La funzione non ne solleva di suoi. Un errore che nasce qui è quello di un vincolo della
tabella figlia, o `E_ATTIVO_PADRE_NON_ATTIVO` alla fine della transazione, come detto sopra.

---

### Test

* `db/pgtap/catalogo/test-articoli-seed-uom-base-lock.sql` — la funzione e il trigger ci
  sono; un articolo nuovo ha la sua riga base, e una sola; `articoli.uom_id` non si modifica,
  se non con l'interruttore di manutenzione.

Il caso dell'articolo creato spento non ha un test.

---

### Note di migrazione

* 2026-04-07 — nasce.

---

{% include-markdown "signature-core.md" %}
