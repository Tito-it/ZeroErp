## 📘 Documentazione Concettuale – Vista `dbops.vw_magazzino_dipendenze_inverse`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro, il servizio che non deve conoscere i suoi clienti
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che la iscrive come cancello
>
> Approfondimento funzioni:
>
> * [magazzino.fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) — la porta del registro
> * [vendite.fn_posta_ddt](/dbzero/vendite/funzioni/fn_posta_ddt) — il verso giusto: il posting della bolla sta nelle vendite
> * [vendite.fn_posta_reso](/dbzero/vendite/funzioni/fn_posta_reso) — il verso giusto: il posting del reso sta nelle vendite
>
> Guide:
>
> * [Mappa concentrica](/mappa-concentrica) — l'anello 2 e la matrice delle dipendenze

---

### 🎯 Scopo Principale

Le cose dello schema `magazzino` che nominano uno schema di **processo** che lo usa: le vendite,
gli acquisti, i pagamenti. È un **cancello**: deve restare vuota, e una riga fa fallire un test in
CI.

---

### ⭐ Perché esiste, detto sul modello

Il magazzino contiene due cose diverse. Il **registro** dice dove sta la merce e quanto vale, e ha
una porta sola per scriverci. È un **servizio**, come il motore che stampa i documenti: chi muove
merce (una bolla, un reso, domani un carico da fornitore) scrive il proprio posting nel proprio
schema e chiama la porta, e il registro non sa chi è.

Quando il registro conosce un suo cliente, ogni cliente nuovo lo costringe a cambiare, e due parti
del programma che dovrebbero stare una dentro l'altra si tengono a vicenda. La regola «mai
dipendenze all'indietro» era **scritta** nella matrice delle dipendenze, ma nessun test la
**leggeva**: questa vista la legge.

---

### Due lenti

| Lente | `come` | Che cosa vede |
| --- | --- | --- |
| **il catalogo del database** | `CATALOGO` | i legami che il database registra da solo: un collegamento fra tabelle, una vista costruita su un'altra tabella, un trigger che esegue una funzione altrui, una regola di visibilità, un valore predefinito, il tipo di un parametro, il corpo di una funzione scritta in SQL standard. È esatta: non legge testo |
| **il testo delle funzioni** | `CORPO` | le funzioni scritte come programma, di cui il database non registra i legami: il loro testo, tolti i commenti di riga, cercato per «nome dello schema, punto, nome» |

Le regole, i trigger, le regole di visibilità e i valori predefiniti prendono lo schema della
tabella che li porta: il catalogo da solo non lo dice.

---

### Che cosa conta e che cosa no

| Conta | Non conta |
| --- | --- |
| una funzione del magazzino che legge una tabella delle vendite | una funzione delle **vendite** che usa il magazzino: è il verso giusto |
| un collegamento da una tabella del magazzino verso un documento | un commento di riga che nomina le vendite |
| una vista del magazzino costruita su una tabella degli acquisti | i trigger generati che impediscono di spegnere un magazzino ancora usato da una bolla: nascono dal legame **della bolla verso il magazzino**, il verso giusto, e la vista non legge gli argomenti dei trigger |

⚠️ Solo i commenti di riga si tolgono dal testo: un commento a blocco che nominasse una tabella
delle vendite accenderebbe la riga come se fosse codice.

⚠️ Il perimetro dei processi è scritto **dentro la vista**. ⛔ Non si allarga per far tornare vuota
la vista: cresce solo quando nasce uno schema di processo nuovo, ed è un cambiamento di questa vista,
firmato e motivato.

---

### Se compare una riga

La riga dice **che cosa** nel magazzino (`oggetto`, `tipo_oggetto`), **in che modo** (`come`) e
**quale processo** nomina (`schema_nominato`, `nominati`).

L'esito atteso è uno solo: **la conoscenza si sposta dal lato di chi usa**. Il processo scrive nel
proprio spazio ciò che gli serve e chiama il registro dalla sua porta; un legame fra dati lo porta il
documento, non il registro.

---

### Chi la può vedere

Legge solo il catalogo del database, con i permessi di chi la interroga: non tocca dati. A catalogo
è un `CANCELLO`, perimetro `LIBERO`.

---

### Test

* `db/pgtap/magazzino/test-registro-non-nomina-i-consumatori-v1.sql` — gira in CI: pretende la
  vista vuota, costruisce sei testimoni (una funzione, una vista, un collegamento, un trigger, una
  regola di visibilità e un valore predefinito che nominano un processo) e verifica che la vista li
  veda tutti, e che non veda una funzione che nomina le vendite solo in un commento.

---

### Note di migrazione

* 2026-10-01 — nasce col ritorno del registro nell'anello interno
  (`brief-db-magazzino-registro-anello-interno`, P-6). Il verso inverso era entrato con lo scarico
  dalla bolla e il carico dal reso senza un rosso: due funzioni del registro leggevano le tabelle
  delle vendite, e quel giorno sono passate nelle vendite. Al primo giro la vista ha trovato anche il
  seriale di un bene che sapeva sotto quale contratto di vendita stava, e il legame è stato tolto.

---

{% include-markdown "signature-core.md" %}
