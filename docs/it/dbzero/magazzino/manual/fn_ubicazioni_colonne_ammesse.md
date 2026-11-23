## 📘 Documentazione Concettuale – Funzione `magazzino.fn_ubicazioni_colonne_ammesse`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.ubicazioni](/dbzero/magazzino/tabelle/ubicazioni) — la tabella di cui elenca le colonne
>
> Approfondimento funzioni:
>
> * [magazzino.fn_crea_ubicazione](/dbzero/magazzino/funzioni/fn_crea_ubicazione) — la nascita, che legge la lista «crea»
> * [magazzino.fn_modifica_ubicazione](/dbzero/magazzino/funzioni/fn_modifica_ubicazione) — il verbo che legge la lista «modifica»
> * [script.fn_guard_campi_ammessi](/dbzero/script/funzioni/fn_guard_campi_ammessi) — il controllo che usa la lista

---

### 🎯 Scopo Principale

Le colonne che una persona compila per un'ubicazione, nel gesto di crearlo o di modificarlo: la **sede unica** della lista, che leggono il database e il backend.

---

### Che cosa c'è nella lista

Alla nascita: codice, descrizione, tipo, ubicazione padre, le coordinate (area, corsia, scaffale, piano, posizione) e le note strutturate. In modifica le stesse, più lo stato attivo. Il magazzino non è in lista: è l'identità della nascita e poi non cambia.

---

### ⭐ Una lista sola per tre lettori

La nascita, il verbo di modifica e il form del backend leggono la stessa lista: una colonna nuova si aggiunge qui, e il form la vede senza che nessuno ricopi un elenco. Fuori lista restano sempre l'identificativo, le colonne di audit e quelle che scrive il sistema.

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — il gesto non è né «crea» né «modifica».

---

### Test

`db/pgtap/magazzino/test-colonne-ammesse-e-nascita-anagrafiche-v1.sql`.

---

### Note di migrazione

* 2026-11-22 — nasce dalle liste che stavano in tre posti: nella funzione di nascita e nelle costanti del backend (`brief-db-magazzino-tutte-le-scritture-dal-verbo`).

---

{% include-markdown "signature-core.md" %}
