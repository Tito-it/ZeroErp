## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_annulla_movimento_titolo_iva`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti) — il registro in cui scrive
>
> Approfondimento viste:
>
> * [anagrafiche.vw_stiva_movimenti_dettaglio](/dbzero/anagrafiche/views/vw_stiva_movimenti_dettaglio) — dove si preme il pulsante, già spento col motivo
>
> Approfondimento funzioni:
>
> * [script.fn_check_annullo_movimento_titolo_iva](/dbzero/script/funzioni/fn_check_annullo_movimento_titolo_iva) — se l'annullo si può fare
> * [anagrafiche.trgfn_stiva_movimenti_guard_annullo](/dbzero/anagrafiche/funzioni/trgfn_stiva_movimenti_guard_annullo) — la difesa contro la scrittura diretta
> * [anagrafiche.trgfn_soggetti_titoli_iva_movimenti_accumulatore](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_movimenti_accumulatore) — chi riporta il consumato al valore giusto
> * [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa) — la data dell'annullo

---

### 🎯 Scopo Principale

`anagrafiche.fn_annulla_movimento_titolo_iva` annulla una forzatura del registro del plafond scrivendo il
contro-movimento di segno opposto, e ne restituisce l'identificativo. È la porta dell'annullo: chi chiama dice
quale riga e perché.

---

### ⭐ Importo e titolo si derivano, non si ricevono

Il titolo e l'importo dell'annullo si leggono dalla riga annullata. Così chi chiama non li può sbagliare, e i due
controlli di coerenza del guard sulla riga di annullo (stesso titolo, importo opposto) restano una difesa contro chi
scrive nel registro direttamente, non un errore che l'operatore può fare. Il guard resta comunque: la tabella si
può scrivere anche senza passare di qui.

---

### Chiama la check, non riscrive la regola

Se l'annullo si può fare lo decide `script.fn_check_annullo_movimento_titolo_iva`, la stessa che spegne il pulsante
nella vista del registro: la funzione la interroga e solleva il primo motivo. Il pulsante spento e il rifiuto non
possono dire cose diverse, perché la regola è scritta una volta.

---

### Come annulla

1. Rifiuta una riga non indicata o un motivo vuoto. Il motivo lo pretende già un controllo sulla tabella, ma lì
   uscirebbe come violazione di vincolo, un errore muto; qui esce come rifiuto con un codice.
2. Chiede alla check se l'annullo è ammesso: non lo è per un movimento che non esiste, che non è una forzatura, che
   è esso stesso un annullo o è già annullato, o la cui rimozione porterebbe il consumato sotto zero.
3. Rilegge la riga coi permessi di chi chiama, per titolo e importo. La check, che gira sopra la RLS, l'ha già
   dichiarata annullabile: se qui non si vede, chi opera non ha il perimetro per annullarla, e la funzione si
   ferma.
4. Scrive la nuova forzatura: stesso titolo, importo opposto, nessuna fattura, il motivo ricevuto, il collegamento
   alla riga annullata.

La data del movimento è la **data dell'annullo**, non quella della forzatura: il giorno operativo, cioè la data di
oggi nel fuso dell'azienda (`script.fn_data_operativa`). È una delle ragioni per cui l'annullo è una riga e non un
flag: dice quando qualcuno si è accorto dell'errore.

Non tocca il consumato: l'accumulatore somma senza filtri, e il contro-movimento lo riporta al valore di prima da sé.

---

### Gira coi permessi di chi chiama

La scrittura passa dalla RLS del registro: un operatore annulla solo forzature dei titoli del suo perimetro. Sono la
check e il guard a girare coi privilegi del proprietario, e solo per le letture di coerenza.

---

### Codici errore

* `E_TITOLO_IVA_ANNULLO_NON_AMMESSO` — il primo motivo della check, o la riga fuori dal perimetro di chi chiama.
* `E_TITOLO_IVA_ANNULLO_INCOERENTE` — riga non indicata o motivo vuoto: un chiamante rotto, non un errore
  dell'operatore.

---

### Test

* `db/pgtap/anagrafiche/test-stiva-movimenti-annullo-v1.sql` — annullata una forzatura il registro ha due righe e
  il consumato è tornato al valore precedente; i rifiuti (doppio annullo, movimento di fattura, importo e titolo
  sbagliati, annullo di un annullo); la vista che espone lo stesso motivo che la funzione rifiuta. L'asserzione
  sull'importo sbagliato è quella che rende vera la prima: senza, il numero giusto lo scriverebbe la fixture.

---

### Note di migrazione

* 2026-08-31 — nasce insieme al registro solo aggiunte.

---

{% include-markdown "signature-core.md" %}
