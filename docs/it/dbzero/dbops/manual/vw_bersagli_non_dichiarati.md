## 📘 Documentazione Concettuale – Vista `dbops.vw_bersagli_non_dichiarati`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_entita](/dbzero/config/tabelle/tipi_entita) — il vocabolario dei tipi di bersaglio
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — la riga di catalogo del presidio
>
> Approfondimento viste:
>
> * [dbops.vw_codici_errore_da_dichiarare](/dbzero/dbops/views/vw_codici_errore_da_dichiarare) — la gemella, che legge anche lei il sorgente
> * [dbops.vw_eventi_non_dichiarati](/dbzero/dbops/views/vw_eventi_non_dichiarati) — la spia sui dati, che non è una gemella
>
> Approfondimento funzioni:
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — porta il bersaglio di un errore nel suo canale
> * [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa) — il giorno da cui una voce ritirata conta come ritirata
> * [dbops.fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione) — il corpo senza commenti da cui la vista legge i tipi
> * [dbops.fn_corpo_leggibile](/dbzero/dbops/funzioni/fn_corpo_leggibile) — quali funzioni hanno un corpo da leggere: il perimetro

---

### 🎯 Scopo Principale

Il cancello del vocabolario dei bersagli: ogni tipo di entità scritto in un corpo vivo leggibile, PL/pgSQL
o SQL, che costruisce il bersaglio di un errore, e che `config.tipi_entita` non dichiara (`ASSENTE`) o dichiara
ritirato (`OBSOLETO`). Deve essere vuota.

Il bersaglio è l'entità a cui un errore si riferisce, e il frontend lo trasforma in un gesto che
porta l'operatore a quella schermata. Un tipo che il catalogo non conosce porterebbe a una schermata
che non esiste; uno ritirato, dove il progetto ha smesso di andare.

---

### ⭐ Rende sicuro far crescere il catalogo una voce per volta

Il vocabolario dei tipi cresce insieme al messaggio che usa la voce nuova, non tutto in anticipo.
È una scelta sicura solo se dimenticare la voce è impossibile: con questa vista, dimenticarla fa
fallire la build, non l'operatore.

⛔ **Il rubinetto non si chiude con una FK.** Il bersaglio vive in un dato strutturato dentro il
contesto dell'errore, e comunque il canale d'errore non può smettere di funzionare perché manca una
voce di catalogo: la porta degli errori controlla solo la forma del bersaglio, e uno malformato si
perde con un avviso mentre l'errore di dominio parte lo stesso.

---

### ⚠️ Legge il sorgente, non i dati

È gemella di [vw_codici_errore_da_dichiarare](/dbzero/dbops/views/vw_codici_errore_da_dichiarare),
non di [vw_eventi_non_dichiarati](/dbzero/dbops/views/vw_eventi_non_dichiarati): i codici evento li
scrive il backend e si guardano nei dati, mentre il bersaglio lo scrive il database, quindi la misura
giusta è il testo delle funzioni. Una vista sui dati sarebbe cieca su un ambiente senza traffico, e
da una misura cieca non si può far dipendere una build.

Entrano le funzioni dal corpo leggibile, PL/pgSQL e SQL (comprese le SQL `BEGIN ATOMIC`), come le
decide [fn_corpo_leggibile](/dbzero/dbops/funzioni/fn_corpo_leggibile), che nominano un bersaglio: il
bersaglio viaggia con la chiamata a `fn_log_and_raise_error`, e una funzione SQL la può fare come una
PL/pgSQL. Un tipo conta quando è scritto come valore della chiave `tipo` (maiuscole, cifre e trattini
bassi). Il corpo si legge da [fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione): senza i
commenti, di riga e a blocco, e con i letterali intatti, così un tipo citato in una nota non conta e
uno scritto dopo una stringa che contiene un doppio trattino non sparisce.

Davanti resta un prefiltro economico sul sorgente testuale: lascia passare solo i testi che nominano
un bersaglio. Una funzione SQL `BEGIN ATOMIC` però non ha un sorgente testuale (il suo è vuoto), e il
prefiltro da solo la terrebbe fuori: per questo la lascia passare sempre, e la decide il filtro vero,
sul corpo ricostruito.

⚠️ **Che cosa non vede**: i tipi costruiti per concatenazione o passati in una variabile. È lo stesso
limite della gemella e la stessa scelta: fra i due errori si preferisce quello che si corregge
guardando i falsi positivi.

---

### Come si legge

Una riga per tipo e motivo, con quante funzioni lo scrivono e quali. `ASSENTE` chiede di aggiungere
la voce al catalogo; `OBSOLETO` chiede di cambiare il bersaglio, perché la voce è stata ritirata di
proposito. Una voce conta come ritirata dal giorno operativo in cui scade.

La vista è `security_invoker` e legge i cataloghi di sistema e il catalogo dei tipi; nel catalogo dei
presidi il suo perimetro è `LIBERO`, e la sua natura `CANCELLO`: fuori dal digest, perché il merge è
già bloccato.

---

### Test

* `db/pgtap/dbops/test-vw-bersagli-non-dichiarati.sql` — il cancello: nessun bersaglio punta a un
  tipo non dichiarato o ritirato. Su funzioni finte costruite nel test: la vista distingue `ASSENTE`
  da `OBSOLETO`, ignora i tipi nominati solo in un commento di riga, e non prende una funzione che
  nomina un tipo senza costruire un bersaglio.
* `db/pgtap/dbops/test-presidi-codici-corpo-leggibile-v1.sql` — vede il tipo di un bersaglio
  costruito da una funzione SQL `BEGIN ATOMIC`, che il prefiltro lascia passare (caso costruito).

---

### Note di migrazione

* 2026-08-23 — nasce con `brief-db-bersaglio-errore` §6 L3, insieme al canale del bersaglio di
  `fn_log_and_raise_error`, dopo la decisione di Tid del 2026-08-22 di far crescere il catalogo una
  voce per volta.
* 2026-10-09 — il giorno da cui una voce conta come ritirata diventa il giorno operativo dell'azienda.
* 2026-11-04 — il corpo si legge da `fn_corpo_funzione` (D14 di `brief-db-revisione-dbops`): prima si
  toglievano i soli commenti di riga, quindi un tipo citato in un commento a blocco contava come
  scritto, e uno scritto dopo un letterale che conteneva un doppio trattino spariva.
* 2026-11-09 — il perimetro passa dal solo PL/pgSQL ai corpi leggibili, PL/pgSQL e SQL, letti da
  `fn_corpo_leggibile`; il prefiltro lascia passare le SQL `BEGIN ATOMIC`, che non hanno un sorgente
  testuale (`20261110-82`, `brief-db-revisione-dbops`, giro 12).

---

{% include-markdown "signature-core.md" %}
