## 📘 Documentazione Concettuale – Vista `dbops.vw_lock_columns_vivi`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [dbops.vw_non_editable_fields](/dbzero/dbops/views/vw_non_editable_fields) — il form, che la legge
>
> Approfondimento funzioni:
>
> * [dbops.fn_lock_columns_divergenze](/dbzero/dbops/funzioni/fn_lock_columns_divergenze) — il confronto col registro, che la legge
> * [dbops.fn_trigger_argomenti](/dbzero/dbops/funzioni/fn_trigger_argomenti) — taglia gli argomenti del trigger
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — la funzione che riconosce un lock
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — il giro delle automazioni e le sue regole

---

### 🎯 Scopo Principale

I **lock di colonna vivi**: una riga per ogni trigger su `script.trgfn_lock_columns`, in qualunque
schema, su qualunque tabella e con qualunque nome, montato dal runner o scritto a mano. È un
inventario, non un allarme: non dice se un lock è giusto, dice che c'è.

---

### ⭐ Sede unica della lettura del lock vivo

Due oggetti hanno bisogno di sapere che cosa i trigger bloccano davvero, e lo leggono da qui:

* `dbops.fn_lock_columns_divergenze`, che confronta il vivo con il registro;
* `dbops.vw_non_editable_fields`, che dice al form quali campi spegnere.

Prima la lettura stava scritta dentro la funzione del confronto, e il form leggeva il registro: due
risposte diverse alla stessa domanda.

---

### Che cosa dice di ogni trigger

* `argomenti` — le coppie (colonna, codice d'errore) che il trigger controlla: sono le colonne che
  l'UPDATE rifiuta;
* `colonne_update_of` — le colonne di `UPDATE OF`, che dicono **quando** il trigger scatta, non che
  cosa blocca; vuoto vuol dire «su ogni UPDATE»;
* `abilitato` — se il trigger scatta nelle sessioni normali. Un trigger disabilitato non blocca
  niente;
* `trigger_tipo` — la forma del trigger (`19` è `BEFORE UPDATE` per riga, quella che il runner
  monta);
* `tipo_tabella` — tabella o tabella partizionata.

L'ambito delle automazioni non si applica qui: lo applica chi legge. Il presidio
`dbops/test-lock-columns-convergenza` usa la vista anche **fuori** dall'ambito, dove il runner non
arriva e il lock lo monta una migrazione: pretende che ogni lock vivo sia dichiarato in
`dbops.automation_lock_columns` con lo stesso codice, e che ogni riga attiva del registro abbia il
suo lock vivo.

---

### Test

* `db/pgtap/dbops/test-lock-columns-convergenza.sql` — il confronto col registro, e fuori
  dall'ambito lock vivi e registro che coincidono nei due versi.
* `db/pgtap/dbops/test-non-editable-fields-dal-lock-vivo-v1.sql` — il form che la legge.

---

### Note di migrazione

* 2026-11-08 — nasce (`20261109-59`, brief-db-revisione-dbops D25 e D32) dalla lettura dei
  trigger che stava in `dbops.fn_lock_columns_divergenze`.

---

{% include-markdown "signature-core.md" %}
