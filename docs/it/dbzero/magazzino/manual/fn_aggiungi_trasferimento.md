## 📘 Documentazione Concettuale – Funzione `magazzino.fn_aggiungi_trasferimento`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.trasferimenti](/dbzero/magazzino/tabelle/trasferimenti) — la testata che nasce
>
> Approfondimento funzioni:
>
> * [magazzino.fn_guard_magazzino_nel_perimetro](/dbzero/magazzino/funzioni/fn_guard_magazzino_nel_perimetro) — il magazzino nel perimetro
> * [magazzino.fn_documento_interno_colonne_ammesse](/dbzero/magazzino/funzioni/fn_documento_interno_colonne_ammesse) — le colonne che accetta
> * [magazzino.fn_cambia_stato_documento_interno](/dbzero/magazzino/funzioni/fn_cambia_stato_documento_interno) — il gesto successivo: conferma, riapri, annulla
>
> Guide:
>
> * [Architettura dei permessi — il permesso nel verbo di scrittura](/guide/architettura-permessi-e-autorizzazioni#74-il-permesso-nel-verbo-di-scrittura) — il modello che questi verbi seguono

---

### 🎯 Scopo Principale

Il gesto «nuovo trasferimento» dell'operatore: la testata nasce in bozza, pronta a ricevere le righe. Ritorna l'id.

---

### Regole

Il magazzino di partenza e quello di arrivo sono argomenti, e tutti e due devono essere dell'azienda dell'operatore; possono coincidere, per spostare la merce fra ubicazioni. Partenza e arrivo non cambiano dopo la nascita.

Che i magazzini siano attivi, che la provenienza sia coerente e che il documento stia nel perimetro lo dicono i controlli della tabella.

---

### Codici errore

* `E_PERMESSO_NEGATO` — l'operatore non ha il livello «tutto» sul documento.
* `E_MAG_MAGAZZINO_NON_TROVATO` — un magazzino non esiste o è di un'altra azienda, senza dire quale dei due.
* `E_CAMPO_NON_AMMESSO` — un campo fuori lista; il codice lo nomina.

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
