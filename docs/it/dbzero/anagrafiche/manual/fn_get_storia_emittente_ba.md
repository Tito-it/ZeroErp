## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_get_storia_emittente_ba`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_ba_ha_storia_emittente](/dbzero/anagrafiche/manual/fn_ba_ha_storia_emittente)
> • [anagrafiche.fn_guard_ba_cambio_emittente](/dbzero/anagrafiche/manual/fn_guard_ba_cambio_emittente)
> • [script.fn_check_ba_cambio_emittente](/dbzero/script/manual/fn_check_ba_cambio_emittente)
>
Approfondimenti tabelle:
>
[anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> • [vendite.famiglie_documento](/dbzero/vendite/manual/famiglie_documento)

---
### 🎯 Scopo Principale
(latest review 31-08-2026)

Dice **quanta storia** ha un cliente sull'emittente a cui è agganciato, e **di che
specie**: una riga per ogni tipo di documento che ha già almeno un numero addosso,
col suo conteggio.

Nessuna riga significa: nessuna storia.

---

### Che cosa conta come «storia», e perché non è un giudizio

Non si conta quello che «sembra importante»: si conta **ciò che porta una copia
dell'emittente che nessuno riscriverà più**.

Con quel criterio, dal 31 agosto 2026 la risposta è una sola e vale per tutti:
**un documento che ha già preso un numero da un registro**. Il registro appartiene
a un emittente, e quel numero è la sua copia scritta in cifre — non si rifà.

⚠️ **Prima la regola era diversa, e va detto perché è cambiata.** Si contavano
solo fatture e commesse, e ordini e documenti di trasporto restavano fuori con una
motivazione precisa: *il loro emittente non è una copia che invecchia, perché un
controllo lo riallinea al cliente a ogni scrittura*. Quella motivazione **è caduta
il giorno in cui quei documenti hanno cominciato a prendere il numero dal
registro**: il numero, quello sì, nessuno lo riallinea.

⭐ E l'elenco dei tipi di documento **non è scritto dentro questa funzione**: si
legge dal catalogo delle famiglie. È la differenza fra una regola che si aggiorna
da sé e un elenco che qualcuno deve ricordarsi di allungare.

---

### La bozza non conta più, ed è una scelta

Un documento senza numero non ha congelato niente. Ne discende che **una fattura
in bozza non blocca più** lo spostamento del cliente, mentre prima lo bloccava —
perché il vecchio conteggio guardava le fatture, non i loro numeri.

È il verso giusto: la possibilità di correggere un cliente nato sotto l'emittente
sbagliato esiste **prima** che ci passi del lavoro vero, e una bozza è
esattamente quel momento.

⛔ Va detto per intero: una bozza porta già l'indicazione dell'emittente, e nessun
controllo la riallinea al cliente. Spostare il cliente la lascerebbe sull'emittente
di prima. Resta però una bozza — si cancella e si rifà — e presidiarla costerebbe
la finestra di correzione per intero.

---

### Perché una riga per tipo, e non due numeri

Perché il messaggio che l'operatore legge deve dire **quale** documento lo sta
bloccando. Con cinque tipi di documento in gioco, una frase che ne nominasse solo
due — *«ha già 3 fatture e 1 commesse»* — sarebbe **peggio** di una che non ne
nomina nessuno: manderebbe a cercare fatture a un cliente bloccato da un documento
di trasporto.

I nomi che finiscono nella frase sono le descrizioni del catalogo, non etichette
ricopiate: un tipo di documento in più domani cambia la frase da sé.

⚠️ I tipi a zero **non escono**. «Nessuna riga» è la risposta «nessuna storia», e
chi compone la frase non deve stare a filtrare gli zeri.

---

### Quando si chiama, e quando invece no

Solo **dopo** aver deciso di rifiutare. Il sì/no lo dà la funzione gemella, che si
ferma al primo documento trovato: contare cinque tipi per rispondere «sì» sarebbe
lavoro buttato, e lo si butterebbe a ogni caricamento della lista degli agganci.

---

### Perché è privilegiata

Fatture e commesse sono protette da regole di visibilità per emittente. Se questa
funzione girasse con i permessi di chi la chiama, **la storia di un altro emittente
sarebbe invisibile**: risponderebbe «non c'è niente» proprio nel caso in cui la
risposta deve fermare l'operazione.

---

### Impatto e Vantaggi

* una definizione sola di «storia», che si aggiorna da sé quando nasce un tipo di
  documento nuovo;
* il messaggio di rifiuto dice dove guardare, invece di mandare a cercare a mano
  in cinque posti.
