## 📘 Documentazione Concettuale – View `dbops.vw_processi_roster`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[dbops.processi](/dbzero/dbops/manual/processi)
>
Approfondimenti funzioni:
>
[dbops.fn_accoda_chiusura_scadenze](/dbzero/dbops/manual/fn_accoda_chiusura_scadenze) ·
[script.fn_riattiva_utente_tecnico](/dbzero/script/manual/fn_riattiva_utente_tecnico)

---
### 🎯 Scopo Principale
(latest review 05-09-2026)

Risponde a una domanda sola: **con quale identità un processo automatico lavora
ciascuna azienda?**

Ogni riga è una coppia *(processo, azienda)* con il nome dell'utente tecnico che
la serve.

---

### ⭐ Perché è nata come vista, e non come l'ennesima query

Questo fatto **esisteva già**, ma viveva dentro una stringa SQL nel codice
Python del backend (`processi_repository.roster_processo`): serviva solo a chi
lancia la fatturazione, che è backend.

Dal momento in cui anche il database deve accodare da solo — il lavoro notturno
della chiusura scadenze — la stessa domanda serve dai due lati.

⛔ Riscriverla in una funzione sarebbe stata una **seconda scrittura dello stesso
fatto**. Due scritture prima o poi dissentono: basta il giorno in cui qualcuno
aggiunge una condizione a una sola delle due.

⇒ Il fatto diventa una vista, e i due lati la leggono.

> ⚠️ **Al backend**: `roster_processo` può diventare un `SELECT` su questa vista.
> Non è urgente. Ma finché restano due copie, sono due copie.

---

### Le cinque condizioni, e perché sono tutte necessarie

Un'identità compare qui solo se **tutte e cinque** valgono:

| Condizione | Che cosa vuol dire |
| --- | --- |
| il legame è attivo | quel processo è ancora affidato a quell'utente |
| l'identità è attiva | l'utente applicativo non è stato spento |
| il ruolo è `OPERATORE` | è la veste che le regole di sicurezza riconoscono |
| l'utente Django è attivo | l'accesso non è stato revocato |
| l'azienda è attiva | c'è ancora qualcuno da servire |

⛔ Toglierne una lascerebbe passare un'identità **spenta a un livello solo**: il
lavoro partirebbe per fermarsi subito dopo — o, peggio, girerebbe a vuoto.

⭐ È la stessa terna che `script.fn_riattiva_utente_tecnico` riaccende tutta
insieme: **spegnerne uno basta a fermare, quindi guardarne uno solo basta a
sbagliare.**

---

### ⚠️ L'ordine non è un dettaglio estetico

Chi accoda accoda **nell'ordine in cui legge**. Senza un ordine stabile due
notti diverse produrrebbero la stessa cosa in sequenze diverse, e confrontarle
diventerebbe illeggibile.

---

### Che cosa NON dice

* Non dice se il processo è **andato bene**: quello sta nel giornale delle
  esecuzioni e, per i lavori di coda, in
  [vw_coda_lavori_da_guardare](/dbzero/dbops/manual/vw_coda_lavori_da_guardare).
* Non dice quali aziende sono **scoperte**: quella è
  `dbops.vw_emittenti_non_serviti`, che nomina la coppia senza identità.

⚠️ Sono domande diverse: qui si legge *chi c'è*, là *chi manca*.

---

### Verifica

`db/pgtap/dbops/test-vw-processi-roster.sql` — spegne, uno alla volta, i quattro
livelli costruibili e verifica che ognuno **basti da solo** a far sparire la
coppia.
