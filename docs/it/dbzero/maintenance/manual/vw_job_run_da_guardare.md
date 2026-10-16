## 📘 Documentazione Concettuale – View `maintenance.vw_job_run_da_guardare`

> **Collegamenti utili**
>
Approfondimenti tabelle:
>
[`maintenance.job_run_log`](/dbzero/maintenance/manual/job_run_log)
>
Approfondimenti funzioni:
>
[`maintenance.fn_job_run_log_failure`](/dbzero/maintenance/manual/fn_job_run_log_failure) ·
[`maintenance.fn_run_and_log`](/dbzero/maintenance/manual/fn_run_and_log)
>
Approfondimenti cause:
>
[`dbops.cause_fallimento`](/dbzero/dbops/manual/cause_fallimento) ·
[`dbops.presidi_cause`](/dbzero/dbops/manual/presidi_cause)

---
### 🎯 Scopo Principale
(latest review 16-10-2026)

**Il posto dove guardare**: i lavori automatici che chiedono un occhio. Deve
restare vuota.

---

### ⛔ Perché non basta scrivere i fallimenti

Da settembre 2026 un lavoro che fallisce lascia finalmente una riga nel giornale.
Ma **righe rosse in una tabella che nessuno apre sono un silenzio nuovo**: il
guasto smette di essere invisibile e diventa illeggibile, che per chi deve
accorgersene è la stessa cosa.

---

### ⭐ La domanda è «quale lavoro sta andando male», non «elenca i rossi»

Ed è la scelta che tiene la vista capace di **tornare vuota**: si guarda
l'**ultima corsa** di ogni lavoro.

⇒ Niente colonna «visto», niente finestra scelta a caso, niente pulizia a mano.

> ⚠️ Il 2026-09-05 un comando aveva **29 fallimenti in un giorno**. Elencandoli
> tutti la vista sarebbe nata con ventinove righe che dicono la stessa cosa.

⛔ **L'ultima corsa è l'ultima corsa VERA** *(rev 2026-10-10)*. Le corse
**saltate** (`job_run_log.saltata`: il lock della corsia era occupato, il lavoro
non è partito) sono escluse. Una corsa appesa tiene il lock, e ogni sveglia
successiva scrive una skip più recente di lei: prima la skip diventava
«l'ultima corsa», e il motivo **presa e mai chiusa** non scattava più. Il caso
che la vista esiste per vedere lo copriva proprio la sveglia che doveva farlo
emergere. Brief: `brief-db-corsa-saltata-non-e-una-corsa`.

---

### Tre motivi, perché sono tre guasti diversi

| Motivo | Che cos'è successo |
| --- | --- |
| **l'ultima corsa è fallita** | il lavoro è arrivato in fondo e ha detto perché |
| **presa e mai chiusa** | ⛔ non ha parlato nemmeno il gestore d'errore: il processo è morto di colpo |
| **intermittente** | l'ultima è andata bene, oppure è in corso adesso, ma di recente il lavoro ha fallito |

⭐ **Il terzo è il più insidioso, e senza di lui la vista sarebbe cieca proprio
dove serve.** Un lavoro che fallisce e passa, fallisce e passa, ha l'ultima corsa
verde: guardando solo quella nessuno lo direbbe malato.

⚠️ Ne segue che il rientro **non è immediato**: servono sette giorni tranquilli.
Ed è giusto — un lavoro che ha fallito cinque minuti fa **ha appena fallito**.

---

### ⚠️ La soglia di un'ora è una scelta, non una misura

Una corsa senza fine da meno di un'ora può essere semplicemente **in corso**.
L'ora viene dal fatto che questi lavori durano secondi.

⛔ *(rev 2026-10-16)* La soglia vale anche per il **motivo**, non solo per
l'ingresso nella vista. Prima una corsa partita cinque minuti fa, di un lavoro
con fallimenti recenti, era detta «presa e mai chiusa»: era in corso, non morta.
Ora il suo motivo è «in corso adesso, ma ha fallito di recente».

⛔ Una soglia dedotta dai tempi di oggi si taglierebbe addosso al carico di oggi.

---

### ⭐ A chi tocca: la causa di ogni riga *(rev 2026-10-16)*

Le righe di questa vista sono guasti di natura diversa: un disco pieno va a chi
gestisce il server, le regressioni dello smoke notturno allo sviluppo. Un
destinatario unico per tutto il presidio mandava metà delle righe alla persona
sbagliata.

Per questo ogni riga porta una **causa** (colonna `causa`, vocabolario
[`dbops.cause_fallimento`](/dbzero/dbops/manual/cause_fallimento)), e
[`dbops.presidi_cause`](/dbzero/dbops/manual/presidi_cause) dice a chi tocca:

| Causa | Chi agisce |
| --- | --- |
| `AMBIENTE` | chi gestisce il server |
| `PROGRAMMA` | lo sviluppo |
| `CONFIGURAZIONE` | l'amministratore, dalle impostazioni dell'applicazione |

La causa si decide **in quest'ordine**:

1. la corsa è appesa (morta senza chiudersi) → `AMBIENTE`, qualunque lavoro sia;
2. l'errore è passato dal database con un codice di guasto dell'ambiente
   (connessione, spazio o memoria, arresto, errore di sistema, permesso mancante,
   tabella occupata) → `AMBIENTE`. La lista sta in
   [`script.fn_sqlstate_di_ambiente`](/dbzero/script/manual/fn_sqlstate_di_ambiente).
   ⭐ *(rev 2026-10-16)* Anche le automazioni rilanciano questi errori così come sono,
   invece di coprirli col loro codice: un permesso mancante in un'automazione arriva
   al sistemista, non allo sviluppo;
3. il codice d'errore dichiara la sua causa
   ([`config.codici_errore`](/dbzero/config/manual/codici_errore)) → quella;
4. altrimenti decide il processo, che dichiara la natura dei suoi fallimenti
   ([`dbops.processi`](/dbzero/dbops/manual/processi));
5. una corsa senza processo (solo righe vecchie) → `PROGRAMMA`.

⭐ Nessuna riga resta senza causa, quindi nessuna finisce fra quelle «senza
indicazione di chi agisce».

⭐ La causa si legge dall'**ultimo fallimento**, non dall'ultima corsa: per un
intermittente l'ultima corsa è andata bene e non ha errore. La colonna
`ultimo_rosso_job_run_id` dice da quale corsa è stata letta.

⚠️ Per i lavori lanciati dal backend il punto 2 vede il guasto dell'ambiente
solo quando il backend scrive il codice del database nel giornale
(`job_run_log.sqlstate`).

---

### ⛔ Che cosa questa vista NON vede

**Il lavoro che non parte affatto.** Se nessuno lo sveglia non c'è nessuna corsa
da guardare — e per accorgersene servirebbe che ogni processo dichiarasse **ogni
quanto** deve girare, cosa che oggi il registro non ha.

⇒ È scritto qui perché non sembri coperta: è la stessa forma di guasto vista da
un altro lato, e resta scoperta.

---

### ⚠️ Chi la può vedere

Nessuna regola di riga: un giro di manutenzione **non appartiene a un'azienda**,
e un perimetro qui non vorrebbe dire niente.

⇒ Il database la concede all'applicazione; **chi la vede lo decide il backend**
con l'area funzionale e il profilo, come per le altre viste di presidio.

---

### Verifica

`db/pgtap/maintenance/test-vw-job-run-da-guardare.sql` — i casi costruiti uno per
uno, compreso il rientro automatico e la corsa ancora in corso che **non** deve
comparire. La corsa appesa seguita da una skip: `test-job-run-saltata-v1.sql`, test 7.
La causa, ramo per ramo: `test-vw-job-run-da-guardare-causa-v1.sql`.

---

{% include-markdown "signature-core.md" %}
