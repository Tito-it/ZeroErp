## 📘 Documentazione Concettuale – Tabella `dbops.error_log`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore) — il catalogo dei messaggi a cui ogni riga punta
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — il registro delle esecuzioni, che si legge insieme a questo
> * [dbops.request_log](/dbzero/dbops/tabelle/request_log) — la chiamata HTTP da cui l'errore può essere uscito
>
> Approfondimento funzioni:
>
> * [script.fn_log_error_only](/dbzero/script/funzioni/fn_log_error_only) — la sola porta di scrittura, su una connessione separata
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e poi solleva
> * [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed) — il trigger sul `tx_id`
> * [dbops.fn_apply_cleanup_at](/dbzero/dbops/funzioni/fn_apply_cleanup_at) — il job che calcola la scadenza
>
> Guide:
>
> * [Messaggi di errore e generazione log](/guide/Messaggi-di-Errore-e-Generazione-Log) — i codici, il catalogo e il canale di log
> * [Audit Logging](/guide/messaggi-audit) — chi può scrivere nei registri

---

### 🎯 Scopo Principale

Il **registro tecnico di ogni errore** registrato dal sistema: quale funzione, di quale area,
con quale codice del catalogo, in quale transazione e con quale contesto. Lo scrivono le funzioni
del database e il backend, attraverso la stessa porta.

È il posto dove resta traccia di un errore anche quando la transazione che l'ha prodotto viene
annullata.

---

### ⭐ Si scrive fuori dalla transazione

Ogni riga nasce da `script.fn_log_error_only` (direttamente, o da `script.fn_log_and_raise_error`
che la chiama e poi solleva). La funzione scrive su una **connessione separata** via `dblink`, con
il ruolo del canale di log: la riga sopravvive all'annullamento della transazione che ha sbagliato.
Il backend registra i propri errori di servizio con la stessa funzione.

⚠️ Senza canale di log configurato, o con `dblink` che non risponde, la funzione emette un avviso
nel log del server e **la riga non nasce**: il registro non ha un ripiego in transazione.

---

### Che cosa dice una riga

* `area` è l'ambito di origine (`database`, `backend`, uno schema di dominio…), `function_name` la
  funzione o il metodo che ha registrato l'errore.
* `messaggio_errore_id` punta al catalogo `config.messaggi_errore`: da lì vengono il codice, la
  frase, la causa e la soluzione. La riga non ricopia il testo.
* `context` porta i dati utili a capire il caso: parametri, valori, identificativi coinvolti.
* `tx_id` è la transazione dell'errore, ed è **obbligatorio**. La porta di scrittura lo prende dal
  chiamante o, se manca, dalla sessione; senza canale per il transaction id è la sentinella nulla.
  È il filo per passare dal giornale di dominio, o da `dbops.audit_log`, agli errori della stessa
  transazione.

---

### ⛔ Append-only per l'applicazione

`zeroerp_app` può leggere e aggiungere, non modificare, cancellare o svuotare: un registro
modificabile da chi è registrato non è un registro. Nessuna funzione e nessun codice del backend
aggiorna o cancella righe di `error_log`; la cancellazione delle righe scadute è mestiere del
proprietario. Il ruolo del canale di log ha il solo diritto di aggiungere.

⚠️ La postura non è una revoca scritta una volta: si dichiara nel ciclo dei grant della
convergenza del rilascio e nel provisioning, che a ogni passata riconcedono i privilegi. Regola:
[Linee guida SQL — sezione 11](/linee-guida-sql#11-ciclo-di-vita-di-un-changeset-i-divieti),
punto 11.8.

---

### 🔎 Ogni filtro della consultazione ha il suo indice

La consultazione degli errori tecnici dell'amministrazione filtra per finestra di date, area,
funzione (esatta o a prefisso), codice e `tx_id`, e ogni filtro ha un indice da cui partire: uno
sul tempo (la finestra, sempre presente, e la prima pagina in ordine di tempo), uno su area e
tempo, uno su funzione e tempo, uno su `tx_id`. Il codice non sta qui: si risolve prima nel
catalogo, e si entra dall'indice sulla chiave verso il messaggio.

⛔ Due cose sul prefisso di `function_name`:

1. la collation del database è italiana, e un indice ordinario non serve una ricerca a prefisso.
   L'indice su funzione usa l'operatore per i pattern, che serve l'uguaglianza e il `LIKE` a
   prefisso, **mai** `ILIKE`;
2. `_` è un jolly di `LIKE`, e i nomi di funzione ne sono pieni: un prefisso non escapato ha come
   parte fissa solo ciò che precede il primo `_`, il planner torna a scandire la tabella, e il
   risultato combacia con nomi sbagliati. Il prefisso va escapato.

⚠️ Gli indici costano in scrittura, sul ramo che sta già fallendo: è il posto giusto per pagarli,
ed è dichiarato.

---

### Il registro tecnico accanto ai log di dominio

`error_log` conserva il dettaglio tecnico. I processi di dominio hanno i propri log, con la fase e
l'esito che l'utente vede (per la fatturazione, il log del lotto e quello del documento): un errore
di processo finisce in entrambi, e i due si legano col `tx_id`.

---

### Scade dopo 90 giorni

Una riga resta **90 giorni** dall'orario dell'errore (`occurred_at`), come le chiamate di
`dbops.request_log`: chi indaga su una richiesta guarda la chiamata e l'errore che ne è uscito, e i
due registri scadono insieme. La scadenza la calcola il job delle automazioni, sulle righe che non
ce l'hanno ancora: ⛔ non c'è un trigger alla nascita, perché la riga la scrive il ruolo del canale
di log, che non legge le regole delle automazioni, e il trigger farebbe fallire la registrazione
degli errori. `cleanup_at` è una data di pulizia, non una scadenza funzionale dell'errore.

---

### Test

* `db/pgtap/dbops/test-registri-append-only-postura-v1.sql` — l'applicazione legge e aggiunge, e
  non modifica né cancella né svuota.
* `db/pgtap/dbops/test-registri-dbops-scadenza-v1.sql` — il registro è nello scope delle
  automazioni con la sua regola, e non ha il trigger alla nascita.
* `db/pgtap/dbops/test-indici-letture-trasversali-v1.sql` — gli indici della consultazione, e
  l'operatore per i pattern su `function_name`.

---

### Note di migrazione

* 2026-09-11 — il registro diventa append-only per l'applicazione: la protezione è nei privilegi,
  e non c'è un trigger di blocco.
* 2026-09-19 — entrano i quattro indici della consultazione tecnica.
* 2026-10-23 — entra nello scope delle automazioni con la regola di scadenza a 90 giorni: prima
  nessuna riga scadeva.

---

{% include-markdown "signature-core.md" %}
