## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_stiva_movimenti_append_only`

> 👀 **Vedi anche**
>
> [anagrafiche.soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti) — il registro che presidia ·
> [anagrafiche.trgfn_soggetti_titoli_iva_movimenti_accumulatore](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_movimenti_accumulatore) — di cui rende irraggiungibili due rami ·
> [anagrafiche.fn_annulla_movimento_titolo_iva](/dbzero/anagrafiche/funzioni/fn_annulla_movimento_titolo_iva) — la via che resta per correggere

---

### 🎯 Scopo Principale

(rev 2026-08-31 — funzione nata il 2026-08-31)

Rende il **registro del plafond IVA** «solo aggiunte»: una riga scritta **non si
modifica e non si cancella**. Si corregge scrivendo un **contro-movimento** di
segno opposto, che lascia a video l'errore, la correzione, e la data di entrambi.

---

### ⭐ Prima era una promessa, adesso è una regola

Tutto il disegno del registro (`D5`) poggia sulla frase *«il registro resta
append-only»*: è la ragione per cui una forzatura è **una riga con motivo, autore
e data** invece di un numero sovrascritto sopra a un altro.

⛔ Ma nel database **non c'era niente che lo imponesse**. Nessun guard su `UPDATE`,
nessuno su `DELETE`: il backend non cancellava perché era scritto in un brief.
Un'istruzione in un documento è una raccomandazione; questo trigger gira.

Decisione di Tid del 2026-08-30, presa guardando esattamente questa differenza.

---

### ⛔ Vieta ENTRAMBE le operazioni, e la metà che sembra meno grave è la peggiore

Verrebbe naturale vietare la sola cancellazione — è quella che «fa sparire le
cose». È il contrario:

| | Cosa succede | Chi se ne accorge |
| --- | --- | --- |
| `DELETE` | la riga sparisce dal registro | si vede: manca una riga |
| `UPDATE` | l'importo cambia **e il totale si riallinea da solo**, perché l'accumulatore ricalcola | ⛔ **nessuno** |

Un `UPDATE` riscrive la storia **in silenzio**: il numero resta «giusto», e non
c'è niente che dica che prima diceva un'altra cosa. Per questo il divieto è su
tutti e due.

---

### ⚠️ Tre rami diventano irraggiungibili — e NON si tolgono

Da questo trigger in poi non arriva più nessun `UPDATE` né `DELETE` su quella
tabella. Quindi sono codice che non gira:

* la branca `TG_OP <> 'INSERT'` dell'**accumulatore** — compresa la sua logica
  dell'array, che porta scritto *«un `UPDATE` che sposta un movimento da un titolo
  a un altro deve ricalcolarli entrambi»*: quel caso **non può più succedere**;
* il trigger di **storico** (`BEFORE DELETE OR UPDATE`);
* la branca `UPDATE` dell'**audit** `data_update`/`user_update`.

⛔ **Restano tutti dove sono**: sono difesa in profondità, e un guard si può sempre
spegnere. Ma vanno **dichiarati** irraggiungibili — è fatto nel manuale
dell'accumulatore — o il prossimo che li legge lavorerà su un caso che il database
non ammette.

> ⭐ *Un ramo morto che sembra vivo costa più di un ramo tolto: chi lo legge ci
> ragiona sopra come se descrivesse il mondo.*

---

### ⚠️ Nessuna esenzione per l'owner

È un trigger e scatta **per tutti**, owner compreso. Una bonifica futura passerà
da una porta dichiarata, non da un cambio di utente: *un guard che si scavalca
cambiando ruolo non è un guard, è un suggerimento.*

---

### ⛔ La pulizia della fattura, un giorno, dovrà passare

Oggi non tocca questa tabella: nel presidio che verifica la copertura della
pulizia fattura è un'**eccezione dichiarata**, con l'alibi «zero righe con una
fattura». Ma la nota di quell'eccezione dice già cosa servirà con `I5`: *«la
pulizia deve **stornare** il movimento prima di cancellare, altrimenti il plafond
di un terzo resta mangiato da un documento che non esiste più»*.

Le due strade, e la seconda è preferibile:

1. un'**apertura dichiarata** — una GUC che la pulizia accende e **richiude** — e
   allora questo guard va esteso a leggerla;
2. ⭐ **la pulizia storna invece di cancellare**, cioè scrive un contro-movimento
   esattamente come fa l'annullo. In quel caso qui non serve **nessuna
   eccezione**, perché nessuno cancella davvero.

Non si decide qui — è materia di `I5` — ma sta scritto nel corpo, così chi
arriverà trova **la domanda** invece di un muro.

---

### Contesto di Esecuzione

* **Tipo**: trigger `BEFORE UPDATE OR DELETE`, per riga
* **Fascia**: `a10` (guard/blocco)
* **Trigger**: `trg_stiva_movimenti_a10_append_only_upd_dlt`

---

### Codici errore

| Codice | Motivo |
| --- | --- |
| `E_TITOLO_IVA_MOVIMENTO_IMMUTABILE` | qualunque `UPDATE` o `DELETE` sul registro (`CONFLITTO_STATO`, 409) |

⚠️ **`CONFLITTO_STATO` e non `DATO_ERRATO`**: non c'è un campo da correggere, è la
**natura del registro** che non lo consente. Ne discende che nel contesto non va
la chiave `campo`.

⚠️ Nel `VARIADIC` viaggiano il **tipo di movimento e la sua data** — le due cose
che una persona riconosce guardando il registro — mai l'id tecnico, che non si
cerca a mano.

---

### Test

`db/pgtap/anagrafiche/test-stiva-movimenti-annullo-v1.sql`, asserzioni **8** e
**9**. ⭐ Sono due e non una: la 9 (`UPDATE`) è quella che conta, per la ragione
della tabella qui sopra.

Cantiere: `brief-db-titoli-iva-movimenti-annullo.md`, decisione `B-1`.

---

{% include-markdown "signature-core.md" %}
