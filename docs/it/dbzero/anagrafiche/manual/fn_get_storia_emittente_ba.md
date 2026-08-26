## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_get_storia_emittente_ba`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_guard_ba_cambio_emittente](/dbzero/anagrafiche/manual/fn_guard_ba_cambio_emittente)
>
Approfondimenti tabelle:
>
[anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)

---
### 🎯 Scopo Principale
(latest review 26-08-26)

Dice **quanta storia** ha un cliente sull'emittente a cui è agganciato: quante
fatture e quante commesse.

---

### Che cosa conta come «storia», e perché non è un giudizio

Non si conta quello che «sembra importante»: si conta **ciò che porta una copia
dell'emittente che nessuno riscriverà più**. Con quel criterio la lista si
compila da sola, e sono due cose:

* le **fatture** — il documento fiscale porta con sé chi lo ha emesso, e non lo
  cambia mai;
* le **commesse** — dal 2026-08-26 anche loro portano una copia dell'emittente,
  fissata alla nascita.

⛔ **Ordini e DDT non si contano**, e non per indulgenza: il loro emittente
**non è una copia che invecchia**, perché un controllo lo riallinea al cliente a
ogni scrittura. Metterli nella lista bloccherebbe più casi senza chiudere
nessun buco in più — e *«blocca di più»* non è un argomento.

---

### Perché è privilegiata

Fatture e commesse sono protette da regole di visibilità per emittente. Se
questa funzione girasse con i permessi di chi la chiama, **la storia di un altro
emittente sarebbe invisibile**: risponderebbe «zero» proprio nel caso in cui la
risposta deve fermare l'operazione.

Sarebbe il difetto peggiore possibile — un conteggio che dice *«non c'è
niente»* quando c'è tutto.

---

### Perché restituisce due numeri e non un sì/no

Perché il messaggio che l'operatore legge deve dire **quante** fatture e
**quante** commesse. Un «non si può» senza numeri manda a cercare a mano cosa
c'è sotto, e chi lo riceve non ha modo di capire se sono due documenti o
duecento.

---

### Impatto e Vantaggi

* una definizione sola di «storia», condivisa da chi blocca il singolo cliente e
  da chi presidia lo spostamento del gestore globale;
* entrambi i conteggi sono serviti da un indice: la domanda si può fare spesso
  senza pagarla.
