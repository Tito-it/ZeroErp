## 📘 Documentazione Concettuale – Procedura `maintenance.proc_sync_storico_set_storicizza`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.storico_set_storicizza](/dbzero/config/tabelle/storico_set_storicizza) — l'insieme che la procedura tiene allineato
>
> Approfondimento funzioni:
>
> * [maintenance.proc_apply_storicizza_defaults](/dbzero/maintenance/funzioni/proc_apply_storicizza_defaults) — il consumatore dell'insieme, che rimette il default
> * [maintenance.proc_sync_storico_set_storicizza_job](/dbzero/maintenance/funzioni/proc_sync_storico_set_storicizza_job) — il wrapper del job settimanale
>
> Guide:
>
> * [Storicizzazione delle tabelle](/guide/storicizzazione-tabelle) — la colonna `storicizza` e il registro delle tabelle a storicizzazione permanente

---

### 🎯 Scopo Principale

Tiene `config.storico_set_storicizza` allineato alla sua derivazione, le tabelle ordinarie che
hanno la colonna `storicizza` con `DEFAULT true`: aggiunge ciò che la derivazione produce e pota
le righe derivate che non puntano più a niente.

Una sincronizzazione ha **due metà**: aggiungere e togliere. Un insieme che si popola da solo
e non si pota da solo accumula righe senza referente, e il suo consumatore ci inciampa.

---

### Le righe aggiunte sono «derivate»

Le righe che la procedura aggiunge nascono derivate (`insert_manuale` falso). Una riga già
presente non si tocca: chiamarla due volte di fila non cambia niente. Le righe manuali sono
quelle messe da una persona o da un changeSet, e la procedura non le crea né le cancella.

---

### ⛔ Si pota una cosa sola, e la distinzione è il cuore

Una riga può smettere di essere prodotta dalla derivazione per **tre** motivi, e solo il primo
giustifica la potatura:

| Caso | Che cosa succede | Perché |
| --- | --- | --- |
| il nome **non risolve** a nessun oggetto, riga derivata | ✅ si pota | non può essere vera in nessun senso |
| il nome non risolve, riga **manuale** | ⛔ non si tocca | è una **decisione** di una persona: se perde il bersaglio va detto a qualcuno, non cancellato di nascosto |
| la tabella **c'è** ma ha perso il `DEFAULT` | ⛔ non si pota | è il caso **transitorio** che `apply_storicizza_weekly` ripara |

> ⚠️ Il terzo è quello che si sbaglierebbe più facilmente. Il `DEFAULT` lo rimette proprio
> l'altra metà del meccanismo, che gira come job a sé: potare lì vorrebbe dire **spegnere la
> storicizzazione di una tabella viva** perché un giro non è ancora passato. Le due metà si
> combatterebbero.

Della riga manuale senza bersaglio parla il consumatore: la salta con un avviso che chiede a
una persona di guardarla.

---

### ⚠️ Il nome si scrive schema-qualificato

La procedura scrive la chiave come «schema.tabella», composta esplicitamente. La conversione
diretta del nome di tabella in testo omette lo schema quando quello schema è nel `search_path`
di chi lancia il job.

⛔ Una chiave che cambia con il `search_path` del chiamante è una chiave che un giorno non
ritrova la propria riga, e la potatura, che risolve il nome, sarebbe la prima a inciampare.

---

### Che cosa NON fa

* Non tocca lo schema delle tabelle: mette a posto solo la **configurazione**. Il `DEFAULT` lo
  applica `maintenance.proc_apply_storicizza_defaults`.
* Non segnala niente a nessuno. Il riepilogo («N aggiunte, M potate») è un `NOTICE`: lo riceve il
  client che l'ha lanciata, e con le impostazioni di registrazione di default non arriva al log
  del server. Lanciata dal job, la traccia della corsa è la riga del giornale delle esecuzioni,
  che a buon fine dice «done».
* Non fallisce per una riga: aggiungere e potare sono due istruzioni sull'insieme, non un ciclo
  per tabella. Se fallisce, fallisce tutta, e il wrapper ne lascia il verbale nel giornale.

---

### Test

`db/pgtap/maintenance/test-storicizza-set-potatura.sql` — l'invariante (nessuna riga derivata
senza referente), i tre casi della tabella qui sopra costruiti uno per uno, il fatto che il sync
continua ad aggiungere ciò che la derivazione produce, e che i nomi dell'insieme sono tutti
schema-qualificati.

---

### Note di migrazione

* 2026-09-05 — arriva la potatura, e il nome diventa schema-qualificato
  (`brief-db-storicizzazione-bersagli-spariti`, R-12). Prima la procedura sapeva solo
  aggiungere: ogni tabella ritirata lasciava una riga che puntava a niente, e tre righe così
  hanno fatto fallire `apply_storicizza_weekly` ogni settimana per sei mesi senza che nessuno se
  ne accorgesse, perché allora il verbale del fallimento veniva annullato insieme al lavoro.
  Dallo stesso giorno `maintenance.fn_run_and_log` lo scrive fuori transazione.

---

{% include-markdown "signature-core.md" %}
