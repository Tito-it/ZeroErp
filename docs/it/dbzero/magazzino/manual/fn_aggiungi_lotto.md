## 📘 Documentazione Concettuale – Funzione `magazzino.fn_aggiungi_lotto`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.lotti](/dbzero/magazzino/tabelle/lotti) — la tabella in cui nasce la riga
>
> Approfondimento funzioni:
>
> * [magazzino.fn_crea_lotto](/dbzero/magazzino/funzioni/fn_crea_lotto) — il building block che scrive la riga
> * [magazzino.fn_lotti_colonne_ammesse](/dbzero/magazzino/funzioni/fn_lotti_colonne_ammesse) — le colonne che accetta
> * [script.fn_guard_livello](/dbzero/script/funzioni/fn_guard_livello) — il permesso, prima di tutto
>
> Guide:
>
> * [Architettura dei permessi — il permesso nel verbo di scrittura](/guide/architettura-permessi-e-autorizzazioni#74-il-permesso-nel-verbo-di-scrittura) — il modello che questi verbi seguono

---

### 🎯 Scopo Principale

Il gesto «nuovo lotto» dell'operatore: controlla il permesso e fa nascere la riga col building block della tabella. Ritorna l'id.

---

### Regole

L'articolo, il codice e la data di arrivo sono argomenti. L'azienda la mette la sessione, e la controlla il perimetro della tabella.

---

### Codici errore

* `E_PERMESSO_NEGATO` — l'operatore non ha il livello «tutto» sull'oggetto, o non c'è un operatore collegato.
* `E_CAMPO_NON_AMMESSO` — un campo fuori lista; il codice lo nomina.

---

### Test

`db/pgtap/magazzino/test-verbi-anagrafiche-magazzino-v1.sql` (il permesso, il perimetro, i campi); `db/pgtap/magazzino/test-colonne-ammesse-e-nascita-anagrafiche-v1.sql` (le liste e la nascita).

---

### Note di migrazione

* 2026-11-22 — nasce quando le anagrafiche di magazzino passano dai verbi: prima le scriveva il backend, direttamente sulle tabelle (`brief-db-magazzino-tutte-le-scritture-dal-verbo`).

---

{% include-markdown "it/dbzero/magazzino/_verbi-di-scrittura.md" %}

---

{% include-markdown "signature-core.md" %}
