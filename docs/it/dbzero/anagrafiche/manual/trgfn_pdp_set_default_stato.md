## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_pdp_set_default_stato`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp) — il PDP che nasce
> * [config.stati_pdp](/dbzero/config/tabelle/stati_pdp) — gli stati tecnici
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_clienti_sync_stato_pdp](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_stato_pdp) — chi muove lo stato dopo la nascita

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_pdp_set_default_stato` dà lo stato tecnico «disponibile» (`DISP`) a un PDP che nasce senza
stato.

---

### Lo stato di nascita

Un PDP nasce senza clienti, e quindi disponibile. Il trigger scatta solo alla nascita: se chi scrive passa
uno stato, lo tiene; se non lo passa, scrive `DISP`, cercato per codice interno nel catalogo degli stati.
Dopo la nascita lo stato lo muove la scrittura dei clienti del PDP, secondo l'occupazione per periodo, e
nessun altro trigger della tabella lo tocca.

Che lo stato sia attivo nel catalogo lo controlla al COMMIT il trigger generico del genitore attivo.

---

### ⚠️ Che cosa oggi non copre

* **Uno stato passato non si giudica.** Un PDP può nascere `ATT` senza nessun cliente, o `DISM`: il trigger
  non confronta lo stato con l'occupazione, e la scrittura dei clienti lo corregge solo fra `DISP` e `ATT`, e
  solo quando un cliente del PDP si scrive.
* **Il contesto dell'errore è malformato.** Quando manca `DISP`, il contesto porta come chiave una frase e
  come valore un nulla.

---

### Codici errore

* `E_CODICE` — manca lo stato `DISP` nel catalogo; nella frase il codice cercato e la tabella.

---

### Test

* `db/pgtap/anagrafiche/test-create-pdp.sql` — i PDP creati senza stato nascono `DISP`.

---

{% include-markdown "signature-core.md" %}
