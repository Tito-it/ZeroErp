## 📘 Documentazione Concettuale – Funzione `script.fn_check_ba_cambio_emittente`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_guard_ba_cambio_emittente](/dbzero/anagrafiche/manual/fn_guard_ba_cambio_emittente)
>
[anagrafiche.fn_get_storia_emittente_ba](/dbzero/anagrafiche/manual/fn_get_storia_emittente_ba)
>
[anagrafiche.fn_ba_ha_storia_emittente](/dbzero/anagrafiche/funzioni/fn_ba_ha_storia_emittente) — che cosa è la storia: qualunque documento, anche in bozza
>
Approfondimenti tabelle:
>
[anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account)

---
### 🎯 Scopo Principale

Risponde alla domanda: *«questo billing account può passare da un'azienda
all'altra?»*. È la regola del cambio d'azienda sul collegamento
(`anagrafiche.emittenti_fiscali_billing_account`): il billing account cambia
azienda solo se non ha nessun documento, di qualunque famiglia e in qualunque
stato, anche in bozza.

Non blocca niente. **Nomina** i motivi, e li restituisce in ordine: nessun
motivo significa «si può».

---

### Il cambio d'azienda si fa modificando il collegamento

Ogni billing account ha sempre il suo collegamento, che non si cancella
(`E_BA_COLLEGAMENTO_NON_SI_TOGLIE`) e non passa a un altro conto
(`E_BA_COLLEGAMENTO_NON_SI_SPOSTA`). L'unico gesto che cambia l'azienda di un
cliente è la **modifica** dell'azienda sul suo collegamento: è lì che
`anagrafiche.fn_guard_ba_cambio_emittente` chiama questa funzione, con il
billing account e le due aziende, prima e dopo.

| L'azienda dopo… | Il billing account ha documenti | Si può cambiare? |
| --- | --- | --- |
| è la stessa di prima | sì o no | ✅ sì — non si sposta niente |
| è diversa | no | ✅ sì — è la finestra di correzione |
| è diversa | sì, anche solo una bozza | ⛔ no (`E_BA_EMITTENTE_CON_STORIA`) |

⭐ Anche una bozza chiude il cambio: è già un documento di quell'azienda, e chi
ha sbagliato azienda cancella prima i documenti.

**La riga dell'azienda predefinita** (senza billing account) risponde sempre
con `E_EMITTENTE_DEFAULT_SINGLETON`: la predefinita è una sola, e non è il
collegamento di nessun cliente. Il trigger della storia non la passa mai a
questa funzione; il motivo serve a chi legge la check riga per riga.

---

### La frase deve dire **quale** documento blocca

La storia è fatta di più famiglie di documenti, e una frase che ne nominasse
due sarebbe **peggio** di una che non ne nomina nessuna: manderebbe a cercare
fatture a un cliente bloccato da un documento di trasporto.

⭐ Ora la frase porta un **elenco**: *«Documento di trasporto: 2, Commessa: 1»*. Le
parole sono le descrizioni del catalogo delle famiglie, non etichette ricopiate
qui, quindi un tipo di documento in più domani cambia la frase da sé.

I valori della frase sono tre (cliente, azienda di prima, elenco), e il
dettaglio porta l'elenco per famiglia e il totale dei documenti.

---

### ⭐ Prima si chiede «sì o no», i conteggi vengono dopo

Il caso normale è che non ci sia storia, ed è anche quello che gira di più: la
lista dei collegamenti lo attraversa **una volta per riga**, a ogni caricamento. Lì
si chiede solo *«c'è almeno un documento?»*
(`anagrafiche.fn_ba_ha_storia_emittente`), e ci si ferma al primo che si trova.

I conteggi per tipo si pagano **soltanto** quando si è già deciso di rifiutare,
cioè per scrivere la frase. È lo stesso principio per cui il bersaglio di un
errore si compone dopo il no, non prima.

---

### ⭐ Il pulsante e il rifiuto non possono divergere

Questa funzione non è una copia della regola *per la UI*: è **la** regola. Il
controllo che blocca la scrittura non ne ha una propria — **chiama questa** e
solleva il primo motivo.

La differenza vale la riga: se fossero due implementazioni, un test potrebbe
provare che *oggi* danno la stessa risposta. Così si prova che **non possono**
darne una diversa, perché la risposta è scritta in un posto solo.

⚠️ Ne discende che **l'ordine dei motivi è un contratto**: chi blocca solleva il
primo, e un ordine diverso farebbe dire al tooltip una cosa e all'errore
un'altra.

---

### Perché è privilegiata

La storia si conta su tabelle protette da regole di visibilità per emittente. Con
i permessi di chi chiama, la funzione risponderebbe **«nessuna storia»** proprio
nel caso in cui il pulsante va spento — accendendolo.

---

### Nessun codice di errore nuovo

La funzione **nomina** un codice che esiste già a catalogo. È una regola delle
linee guida, e ha una ragione: se per scrivere questo controllo servisse un
codice nuovo, vorrebbe dire che chi blocca stava rifiutando **senza saper dire
perché** — e il difetto sarebbe a monte.

---

### Impatto e Vantaggi

* il motivo arriva **sulla riga**, dove il pulsante vive, e non solo alla fine
  del gesto;
* la frase nomina il cliente e l'emittente **per codice**: prima l'emittente
  compariva come identificativo numerico in mezzo a una frase italiana;
* e dice **quale tipo di documento** blocca, con le parole del catalogo: chi la
  legge sa dove guardare invece di doverlo indovinare;
* una regola sola per due superfici — il tooltip e l'errore — e un presidio che
  verifica che resti una sola.

---

### Test

* `db/pgtap/anagrafiche/test-ba-storia-qualunque-documento-v1.sql` — un DDT in
  bozza fa già storia e il cambio è respinto; la frase nomina la specie del
  documento che blocca.
* `db/pgtap/anagrafiche/test-ba-cambio-emittente-storia-v1.sql` — il cambio
  passa sul cliente appena nato, è respinto dopo una commessa, passa se
  l'azienda non cambia davvero; il guard chiama questa check.

---

### Note di migrazione

* 2026-11-26 — la storia diventa «qualunque documento, anche in bozza», e la
  domanda smette di essere «si può togliere il collegamento?»: il collegamento
  non si toglie più, e l'azienda si cambia modificandolo.
