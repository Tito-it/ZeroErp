## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_stiva_movimenti_guard_annullo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti) — il registro su cui è montata
>
> Approfondimento funzioni:
>
> * [script.fn_check_annullo_movimento_titolo_iva](/dbzero/script/funzioni/fn_check_annullo_movimento_titolo_iva) — se l'annullo si può fare, che chiama
> * [anagrafiche.fn_annulla_movimento_titolo_iva](/dbzero/anagrafiche/funzioni/fn_annulla_movimento_titolo_iva) — la porta dell'annullo, che rende derivati i due controlli di coerenza

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_stiva_movimenti_guard_annullo` presidia le righe del registro del plafond che annullano un altro
movimento: rifiuta l'annullo non ammesso, e quello che non ha lo stesso titolo e l'importo esattamente opposto della
riga annullata.

---

### Due controlli diversi

| | Che cosa chiede | Dove sta la regola |
| --- | --- | --- |
| **Ammissibilità** | il movimento si può annullare? | non qui: chiama `script.fn_check_annullo_movimento_titolo_iva` e solleva il primo motivo |
| **Coerenza della riga** | stesso titolo, importo opposto? | qui |

L'ammissibilità sta nella check perché la stessa check spegne il pulsante nella vista del registro: pulsante e
rifiuto non possono divergere. La coerenza sta qui perché, passando dalla porta dell'annullo, titolo e importo sono
derivati dalla riga annullata e non possono sbagliare: chi arriva con valori incoerenti sta scrivendo nel registro
direttamente, e il rifiuto è tecnico. Non è ridondante: la tabella si scrive anche senza la porta.

---

### ⛔ Il controllo sul titolo è il più importante

Un annullo collegato a un movimento di un altro titolo decurta il plafond sbagliato e lascia gonfiato quello della
forzatura, senza sollevare niente: l'accumulatore somma per titolo, e del collegamento non sa nulla. Si vedrebbe
solo guardando due plafond insieme, e l'altro titolo è di norma di un altro cliente.

Il controllo sull'importo è ciò che rende vera la promessa dell'annullo: senza, un «annullo» di 100 su una
forzatura di 250 entrerebbe, e il consumato non tornerebbe al valore di prima.

---

### Gira sopra la RLS

Deve rileggere la riga annullata, e il registro ha la RLS: coi permessi di chi scrive, una riga fuori perimetro
sembrerebbe inesistente e il guard passerebbe su una premessa non verificata, mentre la chiave esterna (che la RLS
non la vede) il collegamento l'accetterebbe. Gira quindi coi privilegi del proprietario. La scrittura resta della
porta dell'annullo, che gira coi permessi di chi chiama.

---

### Quando scatta

Prima dell'inserimento, e solo per le righe che nominano un movimento da annullare: le altre righe del registro non
lo invocano nemmeno. Non serve sulla modifica, che il registro non ammette.

---

### Codici errore

* `E_TITOLO_IVA_ANNULLO_NON_AMMESSO` — il primo motivo della check: movimento inesistente, non una forzatura,
  esso stesso un annullo, già annullato, o la sua rimozione porterebbe il consumato sotto zero.
* `E_TITOLO_IVA_ANNULLO_INCOERENTE` — titolo diverso da quello della riga annullata, o importo che non ne è
  l'opposto esatto.

---

### Test

* `db/pgtap/anagrafiche/test-stiva-movimenti-annullo-v1.sql` — l'annullo di un movimento di fattura, l'importo
  sbagliato, il titolo sbagliato e l'annullo di un annullo rifiutati; la check che vede la riga anche da un
  perimetro che non la vede.

---

### Note di migrazione

* 2026-08-31 — nasce con l'annullo delle forzature.

---

{% include-markdown "signature-core.md" %}
