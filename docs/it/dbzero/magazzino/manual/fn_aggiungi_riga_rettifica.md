## 📘 Documentazione Concettuale – Funzione `magazzino.fn_aggiungi_riga_rettifica`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.rettifiche_righe](/dbzero/magazzino/tabelle/rettifiche_righe) — la riga che nasce
> * [magazzino.rettifiche](/dbzero/magazzino/tabelle/rettifiche) — la testata a cui appartiene
>
> Approfondimento funzioni:
>
> * [magazzino.fn_documento_interno_blocca](/dbzero/magazzino/funzioni/fn_documento_interno_blocca) — la testata presa nel perimetro
> * [magazzino.fn_documento_interno_colonne_ammesse](/dbzero/magazzino/funzioni/fn_documento_interno_colonne_ammesse) — le colonne che accetta
> * [magazzino.fn_modifica_riga_documento_interno](/dbzero/magazzino/funzioni/fn_modifica_riga_documento_interno) — la modifica della riga
>
> Guide:
>
> * [Architettura dei permessi — il permesso nel verbo di scrittura](/guide/architettura-permessi-e-autorizzazioni#74-il-permesso-nel-verbo-di-scrittura) — il modello che questi verbi seguono

---

### 🎯 Scopo Principale

Il gesto «aggiungi una riga» di un rettifica: la riga nasce dentro la sua testata, che deve essere in bozza. Ritorna l'id della riga.

---

### Regole

L'articolo e la quantità di correzione, col segno, sono argomenti; motivo, ubicazione, lotto, seriale e costo unitario si passano insieme.

Che la testata sia in bozza, la posizione, le quantità e la coerenza dell'azienda di lotto e seriale li dicono i controlli della riga.

---

### Codici errore

* `E_PERMESSO_NEGATO` — l'operatore non ha il livello «tutto» sul documento.
* `E_MAG_DOCUMENTO_NON_TROVATO` — la testata non esiste o è fuori dal perimetro.
* `E_CAMPO_NON_AMMESSO` — un campo fuori lista; il codice lo nomina.
* `E_MAG_DOCUMENTO_RIGHE_CONGELATE` — la testata non è in bozza.

---

### Test

`db/pgtap/magazzino/test-verbi-documenti-interni-v1.sql` (il permesso, il perimetro, i campi, gli stati e la variabile della registrazione accesa dall'applicazione); `db/pgtap/magazzino/test-documenti-interni-guard-v1.sql` (la matrice, le righe congelate e l'eliminazione, attraverso i verbi).

---

### Note di migrazione

* 2026-11-23 — nasce quando i documenti interni passano dai verbi: prima testate, righe e stati li scriveva il backend, direttamente sulle tabelle (`brief-db-magazzino-tutte-le-scritture-dal-verbo`).

---

{% include-markdown "it/dbzero/magazzino/_verbi-di-scrittura.md" %}

---

{% include-markdown "it/dbzero/magazzino/_documenti-interni.md" %}

---

{% include-markdown "signature-core.md" %}
