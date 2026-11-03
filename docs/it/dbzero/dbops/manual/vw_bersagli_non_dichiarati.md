## 📘 Documentazione Concettuale – Vista `dbops.vw_bersagli_non_dichiarati`

> **Ultimo aggiornamento**: 4 novembre 2026
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

---

### 🎯 Scopo Principale

Il cancello del vocabolario dei bersagli: ogni tipo di entità scritto in un corpo PL/pgSQL vivo che
costruisce il bersaglio di un errore, e che `config.tipi_entita` non dichiara (`ASSENTE`) o dichiara
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

Entrano solo le funzioni PL/pgSQL che nominano un bersaglio, e un tipo conta quando è scritto come
valore della chiave `tipo` (maiuscole, cifre e trattini bassi). Dal testo si tolgono i commenti di
riga, così un tipo citato in una nota non conta.

⚠️ **Che cosa non vede**: i tipi costruiti per concatenazione o passati in una variabile, e — perché
toglie solo i commenti di riga — prende per scritto anche un tipo citato in un commento a blocco. È
lo stesso limite della gemella e la stessa scelta: fra i due errori si preferisce quello che si
corregge guardando i falsi positivi.

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

---

### Note di migrazione

* 2026-08-23 — nasce con `brief-db-bersaglio-errore` §6 L3, insieme al canale del bersaglio di
  `fn_log_and_raise_error`, dopo la decisione di Tid del 2026-08-22 di far crescere il catalogo una
  voce per volta.
* 2026-10-09 — il giorno da cui una voce conta come ritirata diventa il giorno operativo dell'azienda.

---

{% include-markdown "signature-core.md" %}
