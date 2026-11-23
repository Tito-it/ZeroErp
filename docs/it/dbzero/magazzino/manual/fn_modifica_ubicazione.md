## 📘 Documentazione Concettuale – Funzione `magazzino.fn_modifica_ubicazione`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.ubicazioni](/dbzero/magazzino/tabelle/ubicazioni) — la tabella che modifica
>
> Approfondimento funzioni:
>
> * [magazzino.fn_ubicazioni_colonne_ammesse](/dbzero/magazzino/funzioni/fn_ubicazioni_colonne_ammesse) — le colonne modificabili
> * [script.fn_scrivi_riga_da_jsonb](/dbzero/script/funzioni/fn_scrivi_riga_da_jsonb) — la scrittura del delta
> * [script.fn_guard_livello](/dbzero/script/funzioni/fn_guard_livello) — il permesso, prima di tutto
>
> Guide:
>
> * [Architettura dei permessi — il permesso nel verbo di scrittura](/guide/architettura-permessi-e-autorizzazioni#74-il-permesso-nel-verbo-di-scrittura) — il modello che questi verbi seguono

---

### 🎯 Scopo Principale

Il gesto «modifica l'ubicazione» dell'operatore: controlla il permesso, trova la riga nel perimetro e scrive le colonne che cambiano. Ritorna la riga con le colonne modificabili.

---

### Regole

L'ubicazione si individua dentro il suo magazzino: un'ubicazione di un altro magazzino è «non trovata», come una che non esiste o un magazzino di un'altra azienda.

Si spegne con la modifica dello stato attivo: non c'è un verbo che elimina.

---

### Codici errore

* `E_PERMESSO_NEGATO` — l'operatore non ha il livello «tutto» sull'oggetto.
* `E_MAG_UBICAZIONE_NON_TROVATA` — la riga non c'è o è fuori dal perimetro, senza dire quale dei due.
* `E_CAMPO_NON_AMMESSO` — un campo fuori dalla lista «modifica»; il codice lo nomina.
* `E_SCRIPT_CHIAMATA_NON_VALIDA` — il delta non è un oggetto.

---

### Test

`db/pgtap/magazzino/test-verbi-anagrafiche-magazzino-v1.sql` (il permesso, il perimetro, i campi).

---

### Note di migrazione

* 2026-11-22 — nasce quando le anagrafiche di magazzino passano dai verbi: prima le scriveva il backend, direttamente sulle tabelle (`brief-db-magazzino-tutte-le-scritture-dal-verbo`).

---

{% include-markdown "it/dbzero/magazzino/_verbi-di-scrittura.md" %}

---

{% include-markdown "signature-core.md" %}
