## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_albero_ba_emittente`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_check_ba_coppia_emittente_omogenea](/dbzero/anagrafiche/manual/fn_check_ba_coppia_emittente_omogenea)
>
Approfondimenti tabelle:
>
[anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)

---
### 🎯 Scopo Principale
(latest review 18-08-26)

Verifica che un billing account sia coerente per emittente **con il genitore e
con tutti i figli**, e blocca l'operazione se non lo e'.

---

### Perche' conta davvero

Quando si emette una fattura, l'emittente si prende **dal genitore**. Un albero
che attraversa due emittenti produce quindi un documento **emesso da un
emittente che chi ha fatto il lavoro non puo' nemmeno vedere**, con una
numerazione che non e' la sua.

Non da' errore, non avvisa nessuno: si scopre a fine mese, e non si sa da dove
venga.

---

### Il verso che si dimentica

Il controllo guarda in **due** direzioni:

1. **verso il genitore** — quello a cui si pensa subito;
2. **verso i figli** — quello che si dimentica sempre. Cambiare l'emittente di
   un billing account non spacca solo il legame verso l'alto: spacca anche tutti
   quelli verso il basso, e in un colpo solo.

---

### Perche' e' privilegiata

La funzione legge la tabella dei billing account, che e' protetta da regole di
visibilita' per emittente. Se girasse con i permessi di chi sta scrivendo, un
genitore o un figlio **di un altro emittente sarebbe invisibile** — e
«non lo vedo» diventerebbe indistinguibile da «e' a posto».

Sarebbe il difetto peggiore possibile: un controllo che risponde *«tutto bene»*
proprio nel caso che deve bloccare. Gira quindi con i privilegi del
proprietario della tabella, che vede tutto.

---

### Impatto e Vantaggi

* nessuna eccezione per i dati preesistenti e nessun interruttore di
  disattivazione: **un invariante con l'interruttore non e' un invariante**;
* l'errore nomina i due billing account **e** i due emittenti, cosi' chi lo
  legge sa cosa sistemare senza andarlo a cercare.
