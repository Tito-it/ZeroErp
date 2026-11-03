## 📘 Documentazione Concettuale – Vista `dbops.vw_processi_roster`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo
> * [dbops.processi_identita](/dbzero/dbops/tabelle/processi_identita) — il legame processo-utente tecnico
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — l'identità applicativa dell'utente tecnico
> * [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali) — l'emittente servito dall'utente
>
> Approfondimento viste:
>
> * [dbops.vw_emittenti_non_serviti](/dbzero/dbops/views/vw_emittenti_non_serviti) — l'altra domanda: chi manca
> * [dbops.vw_coda_lavori_da_guardare](/dbzero/dbops/views/vw_coda_lavori_da_guardare) — com'è andato il lavoro accodato
>
> Approfondimento funzioni:
>
> * [dbops.fn_accoda_chiusura_scadenze](/dbzero/dbops/funzioni/fn_accoda_chiusura_scadenze) — il produttore del database che accoda una riga per coppia
> * [script.fn_riattiva_utente_tecnico](/dbzero/script/funzioni/fn_riattiva_utente_tecnico) — riaccende insieme gli anelli che il roster pretende
> * [script.fn_get_auth_user_stato](/dbzero/script/funzioni/fn_get_auth_user_stato) — lo stato dell'utente Django, letto senza nominare le tabelle di Django

---

### 🎯 Scopo Principale

Per ogni processo automatico, con quale identità lavora ciascuna azienda: una riga per coppia
processo-emittente, con l'utente tecnico (id, username, identità) e l'emittente che serve.

---

### ⭐ Una sede sola, letta dai due lati

Il fatto viveva in una query dentro il codice Python del backend, finché serviva solo a chi lancia
la fatturazione. Quando anche il database ha dovuto accodare da solo (il job della chiusura per
scadenze), riscriverlo in una funzione sarebbe stata una seconda scrittura della stessa regola, e
due scritture prima o poi dissentono: basta una condizione aggiunta a una sola delle due.

⇒ Il fatto è questa vista, e la leggono tutti e due i lati: il produttore del database e il
repository del backend, che filtra per processo e non ripete le condizioni.

---

### ⛔ Cinque condizioni, tutte necessarie

Una coppia compare solo se valgono tutte:

| Condizione | Che cosa vuol dire |
| --- | --- |
| il legame è attivo | quel processo è ancora affidato a quell'utente |
| l'identità è attiva, con ruolo `OPERATORE` | è la veste che le regole di sicurezza riconoscono |
| l'utente Django è attivo | l'accesso non è stato revocato |
| l'emittente è attivo | c'è ancora un'azienda da servire |
| il processo è attivo e non ritirato | il lavoro esiste ancora |

⛔ Spegnere un anello basta a fermare il processo, quindi guardarne uno solo basta a sbagliare:
un'identità spenta a un livello solo farebbe partire un lavoro che si ferma a metà, o che gira a
vuoto. È la stessa catena che `script.fn_riattiva_utente_tecnico` riaccende tutta insieme.

La vista non pretende il flag `tecnica` sull'identità: lo controlla il presidio
[vw_processi_dominio_senza_identita](/dbzero/dbops/views/vw_processi_dominio_senza_identita).

---

### ⚠️ L'utente Django si chiede a una funzione

La condizione sull'utente Django passa da
[script.fn_get_auth_user_stato](/dbzero/script/funzioni/fn_get_auth_user_stato) e non da un
collegamento diretto: le tabelle di Django le crea Django dopo le migrazioni del database, e una
vista che le nominasse non si potrebbe creare su un database ricostruito da zero.

⛔ La condizione non è stata sacrificata per aggirare il problema («tanto lo dice già l'identità
applicativa»): l'allineamento fra le due va in un verso solo, e un utente disattivato dentro Django
risulterebbe ancora attivo per il database.

---

### L'ordine

La vista ordina per processo, emittente e utente: chi accoda accoda nell'ordine in cui legge, e due
notti diverse producono le stesse code nella stessa sequenza. ⚠️ L'ordine di una vista non è un
contratto per chi la filtra da fuori: chi ne ha bisogno lo ripete.

---

### Che cosa non dice

* Se il lavoro è **andato bene**: quello sta nel giornale delle corse e, per i lavori di coda, in
  [vw_coda_lavori_da_guardare](/dbzero/dbops/views/vw_coda_lavori_da_guardare).
* Quali aziende sono **scoperte**: lo dice [vw_emittenti_non_serviti](/dbzero/dbops/views/vw_emittenti_non_serviti).
  Qui si legge chi c'è, là chi manca.

---

### Test

* `db/pgtap/dbops/test-vw-processi-roster.sql` — le colonne che il produttore legge; la coppia
  costruita compare una volta sola; spenti uno alla volta il legame, l'identità, l'utente Django e
  il ruolo, la coppia sparisce. ⚠️ L'emittente spento non è isolabile su un emittente che ha un
  utente tecnico, e il file lo dichiara invece di fingerlo.
* `db/pgtap/dbops/test-fn-accoda-chiusura-scadenze.sql` — il produttore accoda un lavoro per ogni
  azienda del roster, e il lavoro è dell'operatore tecnico, non di sistema.

---

### Note di migrazione

* 2026-09-05 — nasce come sede unica del roster (`brief-db-processi-automatici-identita-e-perimetro`,
  §12.12), insieme al produttore della chiusura per scadenze; lo stesso giorno la condizione su
  Django passa alla funzione, dopo che il collegamento diretto aveva fermato la build da zero.
  Poi il repository del backend smette di ripetere la regola e legge la vista.

---

{% include-markdown "signature-core.md" %}
