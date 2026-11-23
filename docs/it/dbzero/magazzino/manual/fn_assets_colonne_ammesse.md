## 📘 Documentazione Concettuale – Funzione `magazzino.fn_assets_colonne_ammesse`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.assets](/dbzero/magazzino/tabelle/assets) — la tabella di cui elenca le colonne
>
> Approfondimento funzioni:
>
> * [magazzino.fn_crea_asset](/dbzero/magazzino/funzioni/fn_crea_asset) — la nascita, che legge la lista «crea»
> * [script.fn_guard_campi_ammessi](/dbzero/script/funzioni/fn_guard_campi_ammessi) — il controllo che usa la lista

---

### 🎯 Scopo Principale

Le colonne che una persona compila per un seriale, nel gesto di crearlo o di modificarlo: la **sede unica** della lista, che leggono il database e il backend.

---

### Che cosa c'è nella lista

Alla nascita: seriale, cliente a cui è legato, note strutturate, stato e proprietà. In modifica nessuna colonna: il seriale non ha un verbo di modifica, e la sua storia la scrivono gli eventi. L'articolo e l'azienda sono argomenti del building block.

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
