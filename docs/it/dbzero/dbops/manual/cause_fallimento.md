## 📘 Documentazione Concettuale – Tabella `dbops.cause_fallimento`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.processi](/dbzero/dbops/manual/processi) — *ogni processo dichiara la natura dei suoi fallimenti*
>
• [config.codici_errore](/dbzero/config/manual/codici_errore) — *un errore può dichiarare la sua*
>
• [dbops.presidi_cause](/dbzero/dbops/manual/presidi_cause) — *a chi tocca ogni causa*
>
**Approfondimento viste:**
>
• [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/manual/vw_job_run_da_guardare) — *la causa di ogni lavoro da guardare*

### 🎯 Scopo Principale
(latest review 16-10-2026)

Quando un lavoro automatico fallisce, la prima domanda è **a chi tocca
rimediare**. Questa tabella è l'elenco delle risposte possibili, una per ogni
natura di guasto:

| Causa | Che cosa vuol dire | Chi agisce |
| --- | --- | --- |
| `AMBIENTE` | il guasto è del server o del database: spazio, memoria, connessione, un servizio fermo, un permesso che manca | chi gestisce il server |
| `PROGRAMMA` | il lavoro ha incontrato un caso che il programma non sa gestire | lo sviluppo |
| `CONFIGURAZIONE` | si sistema dalle impostazioni dell'applicazione: una credenziale, un indirizzo, un parametro sbagliato o mancante | l'amministratore |

«Chi agisce» non sta qui: lo dice
[`dbops.presidi_cause`](/dbzero/dbops/manual/presidi_cause) per il presidio dei
lavori, insieme ai testi per chi interviene.

---

### Chi la usa

Le stesse cause le dichiarano **due** cataloghi, ognuno con una FK verso questa
tabella:

* [`dbops.processi`](/dbzero/dbops/manual/processi) — **obbligatoria**: di che
  natura sono i fallimenti del processo quando l'ambiente è sano;
* [`config.codici_errore`](/dbzero/config/manual/codici_errore) — **facoltativa**:
  un errore preciso che ha un destinatario suo. Vuota vuol dire «decide il
  processo».

La vista
[`maintenance.vw_job_run_da_guardare`](/dbzero/maintenance/manual/vw_job_run_da_guardare)
le combina, con i segnali dell'ambiente prima di tutto, e dà a ogni riga la sua
causa.

⭐ È **una** tabella e non un elenco ripetuto nei due cataloghi: due copie dello
stesso elenco prima o poi dicono cose diverse.

---

### Le regole che la tengono completa

| Regola | Dove vive |
| --- | --- |
| Ogni processo dichiara una causa del vocabolario | il database (`NOT NULL` e FK su `dbops.processi`) |
| Un codice d'errore, se la dichiara, usa una causa del vocabolario | il database (FK su `config.codici_errore`) |
| Le cause del presidio dei lavori sono **esattamente** queste | test `db/pgtap/maintenance/test-vw-job-run-da-guardare-causa-v1.sql` (test 1) |
| Ogni causa che la vista produce ha chi la spegne | stesso test (test 14) |

---

### Come si aggiunge una causa

Si edita `80_data/sql/dbops/cause_fallimento.csv` e, nello stesso giro,
`presidi_cause.csv` (a chi tocca) e `presidi_testi.csv` (che cosa fare). Una causa
nuova serve solo se la vista la sa produrre: altrimenti nessuna riga la porterà
mai.

---

*Brief: `brief-db-presidio-job-run-a-chi-tocca.md`.*
