## 📘 Documentazione Concettuale – Funzione `maintenance.fn_apply_storicizza_defaults`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.storico_set_storicizza](/dbzero/config/tabelle/storico_set_storicizza) — l'insieme che la funzione consuma
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — dove il riepilogo arriva, come esito della corsa
>
> Approfondimento funzioni:
>
> * [maintenance.proc_sync_storico_set_storicizza](/dbzero/maintenance/funzioni/proc_sync_storico_set_storicizza) — chi popola e pota l'insieme
> * [maintenance.proc_apply_storicizza_defaults_job](/dbzero/maintenance/funzioni/proc_apply_storicizza_defaults_job) — il wrapper del job settimanale
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — legge il riepilogo e decide se la corsa è rossa
>
> Guide:
>
> * [Storicizzazione delle tabelle](/guide/storicizzazione-tabelle) — la colonna `storicizza` e il registro delle tabelle a storicizzazione permanente

---

### 🎯 Scopo Principale

Rimette `DEFAULT true` sulla colonna `storicizza` di ogni tabella elencata in
`config.storico_set_storicizza`, così che le righe nuove di quelle tabelle nascano storicizzate, e
restituisce il riepilogo del giro: quante tabelle applicate, saltate, fallite.

È il **consumatore** di un insieme derivato: chi lo popola e lo pota è
`maintenance.proc_sync_storico_set_storicizza`. Non tocca l'insieme, e non tocca altro dello
schema delle tabelle che il default di quella colonna.

---

### ⭐ Una riga non ferma le altre

Il giro tratta ogni riga dell'insieme per conto suo, in ordine di nome:

1. una riga che **non risolve** a nessun oggetto viene **saltata**, e lo dice;
2. un cambio di default che fallisce per un altro motivo (un permesso mancante, una colonna
   che non c'è più) isola **quella riga sola**: le altre proseguono;
3. il giro finisce sempre restituendo il riepilogo.

Il nome della tabella si risolve una volta sola, come nome completo, e non si smonta mai: dividere
sul punto sbaglierebbe su un nome con più punti o su un identificatore fra virgolette.

---

### ⭐ Il riepilogo è l'esito della corsa

La funzione restituisce un oggetto con cinque voci:

| Voce | Che cosa conta |
| --- | --- |
| `_applicate` | le tabelle che hanno ricevuto il default |
| `_saltate` | le righe che non risolvono a nessun oggetto |
| `_saltate_manuali` | quante di quelle sono righe manuali |
| `_falliti` | i cambi di default che non si sono applicati |
| `_dettaglio` | le righe saltate o fallite, ciascuna col suo esito (e l'errore, per le fallite) |

Lanciata dal job, la legge `maintenance.fn_run_and_log`: il riepilogo va nell'esito della corsa,
e **una tabella fallita rende la corsa rossa** (`E_JOB_ESITO_CON_SCARTI`) senza annullare le
tabelle applicate. È il contratto «riuscita con scarti»: l'isolamento per riga protegge le altre
tabelle, e il conteggio fa sì che il guasto non resti nascosto.

Ogni riga saltata o fallita lascia anche un `WARNING`, utile a chi la lancia a mano.

---

### ⭐ Perché l'isolamento è strutturale, non una toppa

L'ordine è uno solo, in CI e su pgAgent: prima il sync che allinea l'insieme, poi l'apply che lo
consuma. In CI la convergenza li chiama in ordine `ci_ordine` (100 e 110 in `dbops.processi`);
su pgAgent il sync gira il sabato alle 07:00 e l'apply alle 07:05. Di regola l'insieme arriva
all'apply già potato.

Ma chi popola e chi consuma restano **due corse distinte**, e nessuna delle due garantisce
l'altra. Se il sync fallisce, o la sua sveglia è spenta, l'apply gira lo stesso sull'insieme di
prima; una tabella ritirata fra le due corse vi compare ancora; e le righe manuali il sync non le
pota mai. La riga stantia **può esserci**.

⇒ Chi consuma un insieme derivato non può morire perché una riga non è ancora stata potata.

---

### ⚠️ Saltata non è fallita, e una riga saltata ha due rimedi opposti

Una riga che non risolve è **saltata**, non fallita: la corsa resta verde. Ma i due casi sono
diversi, e il riepilogo li separa:

| Riga saltata | Che cosa succederà |
| --- | --- |
| **derivata** | la poterà il prossimo sync, da sola |
| **manuale** | ⛔ il sync non la tocca mai: è una decisione che ha perso il suo bersaglio, e va guardata da una persona (`_saltate_manuali`) |

Promettere una potatura che non arriverà sarebbe peggio che non dire niente.

---

### Chi la chiama

Il wrapper `maintenance.proc_apply_storicizza_defaults_job`, con una `SELECT`, passando dal
giornale delle esecuzioni: lo chiamano il job pgAgent `apply_storicizza_weekly` e, in CI, la
convergenza dei job strutturali. La funzione in sé è `SECURITY INVOKER`: gira coi diritti del
wrapper, cioè del proprietario delle tabelle.

> ⚠️ Il job vive in `85_pgagent`, che in CI è `MARK_RAN`: su un ambiente ricostruito da zero
> **non viene creato**, e nessun test lo direbbe. In CI il lavoro gira lo stesso, dalla
> convergenza.

---

### Codici errore

* `E_JOB_ESITO_CON_SCARTI` — non lo solleva la funzione: lo scrive `maintenance.fn_run_and_log`
  nella corsa del job quando il riepilogo ha `_falliti` maggiore di zero.

---

### Test

* `db/pgtap/maintenance/test-apply-storicizza-esito-v1.sql` — una tabella del set senza la
  colonna `storicizza` è contata in `_falliti` e nominata nel dettaglio, le altre sono applicate
  lo stesso; dal job la corsa è rossa con `E_JOB_ESITO_CON_SCARTI` e il riepilogo è nell'esito;
  la procedura vecchia non esiste più.
* `db/pgtap/maintenance/test-storicizza-set-potatura.sql` — la funzione con una riga stantia
  **davvero presente**, non simulata: la salta e finisce il giro.

---

### Note di migrazione

* 2026-09-05 — il giro diventa per riga, con salto delle righe senza referente e isolamento dei
  fallimenti (`brief-db-storicizzazione-bersagli-spariti`, R-12). Prima era tutto-o-niente: una
  sola riga che puntava a una tabella ritirata sollevava `undefined_table` e fermava il lavoro per
  tutte. Il job settimanale è morto così ogni settimana dal 21 febbraio al 5 settembre 2026, e
  nessuno se n'è accorto: il giornale continuava a dire «done», perché il verbale del fallimento
  veniva scritto e poi annullato insieme alla transazione.
* 2026-11-03 — su pgAgent il sync gira prima dell'apply, come in CI. Prima l'apply consumava
  sempre l'insieme della settimana prima (`brief-db-revisione-maintenance` D7).
* 2026-11-03 — prende il posto della procedura `maintenance.proc_apply_storicizza_defaults`, che si
  ritira: stessa logica, ma il riepilogo si restituisce invece di finire in un `NOTICE`. Prima una
  corsa con tabelle fallite era verde: la procedura chiudeva «done», e il job, che la chiamava con
  `CALL`, non poteva leggere niente (`brief-db-revisione-maintenance` D11).

---

{% include-markdown "signature-core.md" %}
