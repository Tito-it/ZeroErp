## 📘 Documentazione Concettuale – Tabella `dbops.cause_fallimento`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — ogni processo dichiara la natura dei suoi fallimenti
> * [config.codici_errore](/dbzero/config/tabelle/codici_errore) — un errore può dichiarare la sua
> * [dbops.presidi_cause](/dbzero/dbops/tabelle/presidi_cause) — a chi tocca ogni causa
>
> Approfondimento viste:
>
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — la causa di ogni lavoro da guardare

---

### 🎯 Scopo Principale

Il vocabolario delle cause per cui un lavoro automatico fallisce: una per ogni natura di guasto,
cioè per ogni risposta possibile alla domanda «a chi tocca rimediare?».

| Causa | Che cosa vuol dire |
| --- | --- |
| `AMBIENTE` | il guasto è del server o del database: spazio, memoria, connessione, un servizio fermo, un ruolo o un permesso che manca. Si rimedia sul server |
| `PROGRAMMA` | il lavoro ha incontrato un caso che il codice o il database non gestiscono. Serve una modifica |
| `CONFIGURAZIONE` | si sistema dalle impostazioni dell'applicazione: una credenziale, un indirizzo, un parametro sbagliato o mancante |

«Chi agisce» non sta qui: lo dice [dbops.presidi_cause](/dbzero/dbops/tabelle/presidi_cause) per il
presidio dei lavori, insieme ai testi per chi interviene.

---

### ⭐ Una tabella sola per due cataloghi

Le stesse cause le dichiarano due cataloghi, ognuno con una FK verso questa tabella:

* [dbops.processi](/dbzero/dbops/tabelle/processi) — **obbligatoria**: di che natura sono i
  fallimenti del processo quando l'ambiente è sano;
* [config.codici_errore](/dbzero/config/tabelle/codici_errore) — **facoltativa**: un errore
  preciso che ha un destinatario suo. Vuota vuol dire «decide il processo».

[maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) le combina,
con i segnali dell'ambiente prima di tutto, e dà a ogni riga la sua causa. Una tabella e non un
elenco ripetuto nei due cataloghi: due copie dello stesso elenco prima o poi dicono cose diverse.

---

### Come si aggiunge una causa

Si edita `80_data/sql/dbops/cause_fallimento.csv` e, nello stesso giro, `presidi_cause.csv` (a chi
tocca) e `presidi_testi.csv` (che cosa fare): il pgTAP del presidio pretende che le cause del
presidio coincidano con questo vocabolario. Una causa nuova serve solo se la vista la sa
produrre: altrimenti nessuna riga la porterà mai. Codice e descrizione non possono essere vuoti.

---

### Test

* `db/pgtap/maintenance/test-vw-job-run-da-guardare-causa-v1.sql` — le cause del presidio dei
  lavori sono esattamente questo vocabolario; i segnali dell'ambiente battono la causa dichiarata,
  la causa del codice batte quella del processo; ogni causa prodotta ha chi la spegne.

---

### Note di migrazione

* 2026-10-16 — nasce con `brief-db-presidio-job-run-a-chi-tocca` (D4): prima il presidio dei lavori
  aveva un solo destinatario per guasti di natura diversa.

---

{% include-markdown "signature-core.md" %}
