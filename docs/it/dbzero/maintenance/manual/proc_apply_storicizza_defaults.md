## 📘 Documentazione Concettuale – Procedura `maintenance.proc_apply_storicizza_defaults`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.storico_set_storicizza](/dbzero/config/tabelle/storico_set_storicizza) — l'insieme che la procedura consuma
>
> Approfondimento funzioni:
>
> * [maintenance.proc_sync_storico_set_storicizza](/dbzero/maintenance/funzioni/proc_sync_storico_set_storicizza) — chi popola e pota l'insieme
> * [maintenance.proc_apply_storicizza_defaults_job](/dbzero/maintenance/funzioni/proc_apply_storicizza_defaults_job) — il wrapper del job settimanale
>
> Guide:
>
> * [Storicizzazione delle tabelle](/guide/storicizzazione-tabelle) — la colonna `storicizza` e il registro delle tabelle a storicizzazione permanente

---

### 🎯 Scopo Principale

Rimette `DEFAULT true` sulla colonna `storicizza` di ogni tabella elencata in
`config.storico_set_storicizza`, così che le righe nuove di quelle tabelle nascano storicizzate.

È il **consumatore** di un insieme derivato: chi lo popola e lo pota è
`maintenance.proc_sync_storico_set_storicizza`. Non tocca l'insieme, e non tocca altro dello
schema delle tabelle che il default di quella colonna.

---

### ⭐ Una riga non ferma le altre

Il giro tratta ogni riga dell'insieme per conto suo, in ordine di nome:

1. una riga che **non risolve** a nessun oggetto viene **saltata**, e lo dice;
2. un cambio di default che fallisce per un altro motivo (un permesso mancante, una colonna
   che non c'è più) isola **quella riga sola**: le altre proseguono;
3. il giro finisce sempre con un riepilogo: quante applicate, saltate, fallite.

Il nome della tabella si risolve una volta sola, come nome completo, e non si smonta mai: dividere
sul punto sbaglierebbe su un nome con più punti o su un identificatore fra virgolette.

L'ordine stabile serve a confrontare due corse leggendo il log del server.

---

### ⚠️ Non è «ingoiare gli errori»: cambia il posto dove il guasto si racconta

Una riga saltata o fallita lascia un `WARNING`, che finisce nel **log del server**. La corsa,
nel giornale delle esecuzioni, resta **riuscita**: un guasto su una riga non fa diventare rossa la
corsa per le altre cento.

Il riepilogo finale è invece un `NOTICE`: lo riceve il client che ha lanciato la procedura, e
con le impostazioni di registrazione di default non arriva al log del server. Chi deve sapere
se qualcosa è stato saltato guarda i `WARNING`.

---

### ⭐ Perché l'isolamento è strutturale, non una toppa

Chi popola e chi consuma sono **due job pgAgent distinti**, e su pgAgent l'apply gira **sempre
prima** del sync: sabato alle 07:00 l'apply, alle 07:05 il sync. L'apply consuma dunque
l'insieme com'era dopo il sync della settimana prima: una tabella ritirata nel frattempo vi
compare ancora. La riga stantia **c'è** a ogni giro in cui qualcosa è stato ritirato.

⇒ Chi consuma un insieme derivato non può morire perché una riga non è ancora stata potata.

In CI l'ordine è l'opposto: la convergenza chiama il sync prima dell'apply (`ci_ordine` 100 e
110 in `dbops.processi`), e lì l'insieme arriva già potato.

---

### ⚠️ Il messaggio distingue due casi, perché hanno rimedi opposti

| Riga saltata | Che cosa succederà |
| --- | --- |
| **derivata** | la poterà il prossimo sync, da sola |
| **manuale** | ⛔ il sync non la tocca mai: è una decisione che ha perso il suo bersaglio, e va guardata da una persona |

Promettere una potatura che non arriverà sarebbe peggio che non dire niente.

---

### Chi la chiama

Il wrapper `maintenance.proc_apply_storicizza_defaults_job`, che passa dal giornale delle
esecuzioni: lo chiamano il job pgAgent `apply_storicizza_weekly` e, in CI, la convergenza dei
job strutturali. La procedura in sé è `SECURITY INVOKER`: gira coi diritti del wrapper, cioè del
proprietario delle tabelle.

> ⚠️ Il job vive in `85_pgagent`, che in CI è `MARK_RAN`: su un ambiente ricostruito da zero
> **non viene creato**, e nessun test lo direbbe. In CI il lavoro gira lo stesso, dalla
> convergenza.

---

### Test

`db/pgtap/maintenance/test-storicizza-set-potatura.sql` — in particolare il test che chiama la
procedura con una riga stantia **davvero presente**, non simulata, e prova che la salta e finisce
il giro.

---

### Note di migrazione

* 2026-09-05 — il giro diventa per riga, con salto delle righe senza referente e isolamento dei
  fallimenti (`brief-db-storicizzazione-bersagli-spariti`, R-12). Prima era tutto-o-niente: un
  cambio di default per riga in un ciclo unico, e una sola riga che puntava a una tabella
  ritirata sollevava `undefined_table` e fermava il lavoro per tutte. Il job settimanale è
  morto così ogni settimana dal 21 febbraio al 5 settembre 2026, e nessuno se n'è accorto:
  il giornale continuava a dire «done», perché il verbale del fallimento veniva scritto e poi
  annullato insieme alla transazione. Dallo stesso giorno `maintenance.fn_run_and_log` scrive
  quel verbale fuori transazione.

---

{% include-markdown "signature-core.md" %}
