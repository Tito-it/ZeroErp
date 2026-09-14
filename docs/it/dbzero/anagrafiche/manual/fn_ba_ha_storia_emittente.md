## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_ba_ha_storia_emittente`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_get_storia_emittente_ba](/dbzero/anagrafiche/manual/fn_get_storia_emittente_ba)
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

Risponde a **una sola domanda**: questo cliente ha già almeno un documento con un
numero addosso? Sì o no.

Si ferma al primo che trova.

---

### Perché esiste separata dal conteggio

C'è una funzione gemella che dice **quanti** documenti ci sono e di che tipo.
Sembra che ne basterebbe una: la si chiama, e se i numeri sono tutti a zero non
c'è storia.

Non basta, ed è una questione di **quando** ciascuna serve.

* la domanda «sì o no» viene fatta **in continuazione**: ogni volta che si
  guarda la lista degli agganci di un emittente, una volta per riga, per decidere
  se accendere o spegnere il cestino;
* la domanda «quanti e quali» serve **solo per scrivere il messaggio di rifiuto**,
  cioè quando si è già deciso di dire no.

⭐ Contare cinque tipi di documento per rispondere «sì» quando bastava trovarne
uno è lavoro buttato, e lo si butterebbe ad ogni caricamento di quella lista.
Fermarsi al primo è lo stesso principio per cui il messaggio di un errore si
compone **dopo** aver deciso di sollevarlo, non prima.

---

### Che cosa conta come «storia»

Un documento che ha già preso un **numero da un registro**. Il registro appartiene
a un emittente: quel numero è, in tutto e per tutto, una copia dell'emittente
scritta sotto forma di cifre — e nessuno la riscriverà mai.

L'elenco dei tipi di documento **non è scritto qui**: si legge dal catalogo delle
famiglie. Un tipo di documento nuovo entra nella regola il giorno in cui si
registra la sua famiglia, senza che nessuno debba ricordarsi di venire a
modificare questa funzione.

⚠️ **Una bozza non conta.** Un documento senza numero non ha congelato niente, e
proprio per questo lasciarlo passare è corretto: la possibilità di correggere un
cliente nato sotto l'emittente sbagliato esiste **prima** che ci passi del lavoro
vero.

---

### Perché è privilegiata

Fatture e commesse sono protette da regole di visibilità per emittente. Se questa
funzione girasse con i permessi di chi la chiama, **la storia di un altro
emittente sarebbe invisibile**: risponderebbe «no, nessuna storia» proprio nel
caso in cui la risposta deve fermare l'operazione.

Sarebbe il difetto peggiore possibile: un controllo che dice *«si può fare»*
perché non vede quello che c'è.

---

### Impatto e Vantaggi

* il controllo che gira spesso costa poco, e quello che costa gira di rado;
* la definizione di «storia» sta in un posto solo, condivisa da chi spegne il
  pulsante e da chi rifiuta l'operazione: non possono divergere.

### 🔄 rev 2026-09-14 — le famiglie senza billing account restano fuori dal giro

Dal `20260914-09/-10` la funzione gira solo sulle famiglie che **dichiarano**
una colonna del billing account (`vendite.famiglie_documento.colonna_billing_account`
è facoltativa da quel giorno). Il salto sta nella query che sceglie le famiglie,
**non** dentro la composizione dell'SQL: un nome vuoto lì dentro avrebbe
prodotto un errore tecnico senza codice, o — peggio — un'interrogazione muta.
Una famiglia senza cliente non può contribuire alla storia di nessun cliente.
Brief: `brief-db-modifiche-certe-ciclo-vendita-e-articolo`, sezione 3-bis.
