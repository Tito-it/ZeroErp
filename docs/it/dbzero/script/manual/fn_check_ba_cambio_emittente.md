## 📘 Documentazione Concettuale – Funzione `script.fn_check_ba_cambio_emittente`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_guard_ba_cambio_emittente](/dbzero/anagrafiche/manual/fn_guard_ba_cambio_emittente)
>
[anagrafiche.fn_get_storia_emittente_ba](/dbzero/anagrafiche/manual/fn_get_storia_emittente_ba)
>
Approfondimenti tabelle:
>
[anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account)

---
### 🎯 Scopo Principale
(latest review 27-08-26)

Risponde alla domanda che il **pulsante** deve farsi prima di accendersi:
*«questo aggancio cliente → emittente si può ancora togliere?»*

Non blocca niente. **Nomina** i motivi, e li restituisce in ordine: nessun
motivo significa «si può».

---

### Perché esiste: il pulsante era acceso su qualcosa che sarebbe stato rifiutato

Nel tab «Billing Account» di un emittente il cestino di riga era **sempre**
acceso. Su un cliente con documenti già emessi presso un altro emittente il
gesto veniva rifiutato — correttamente — **dopo** che l'operatore aveva premuto e
confermato.

⇒ È la forma che le linee guida chiamano *«la terza via»*: l'operatore scopre il
vincolo **sbagliando**. Il rifiuto era giusto; era la fine sbagliata del gesto.

---

### ⛔ La metà del predicato che si dimentica

Sembra che la domanda sia *«questo cliente ha una storia?»*. **Non è quella**, ed
è l'errore che costerebbe più caro.

Togliere l'aggancio specifico non lascia il cliente senza emittente: lo fa
ricadere su quello **generale dell'installazione**. Quindi un cambio c'è
**soltanto se** l'emittente della riga è **diverso** da quello generale.

| L'emittente della riga… | Il cliente ha storia | Si può togliere? |
| --- | --- | --- |
| coincide col generale | sì | ✅ **sì** — non si sposta nessun documento |
| coincide col generale | no | ✅ sì |
| è diverso | no | ✅ sì — è la finestra di correzione |
| è diverso | sì | ⛔ no |

⚠️ Scrivere solo la seconda metà spegnerebbe il cestino su **quasi tutte** le
righe di un'installazione a un solo emittente — tutte a torto.

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
* una regola sola per due superfici — il tooltip e l'errore — e un presidio che
  verifica che resti una sola.
