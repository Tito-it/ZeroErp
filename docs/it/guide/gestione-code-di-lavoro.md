# Guida – Gestione delle code di lavoro

> **Ultimo aggiornamento**: 7 novembre 2026
>
> Destinatari: sviluppatori backend e database, analisti funzionali
>
> Vedi anche
>
> * [Tracciamento processi e job](/guide/analisi-tracciamento-processi-e-job) — dove si osservano le esecuzioni del lavoratore che svuota la coda
> * [Messaggi di errore e generazione log](/guide/Messaggi-di-Errore-e-Generazione-Log) — dove finiscono gli errori
> * [I lavori automatici: che natura hanno e per conto di chi girano](/guide/processi-automatici-classe-e-identita) — **da leggere prima**: dice quali lavori devono passare di qui e con quale identità
> * [Processi pgAgent funzionali](/guide/processi-pgagent-funzionali) — l'elenco dei lavori a orario
> * [Gestione mail](/guide/gestione-mail) — il secondo utilizzatore naturale (invio asincrono)
> * [dbops.coda_lavori](/dbzero/dbops/tabelle/coda_lavori) e [dbops.fn_accoda_lavoro](/dbzero/dbops/funzioni/fn_accoda_lavoro) — il dettaglio tecnico

---

## In una frase

Una **coda di lavoro** è una lista di compiti che il sistema deve svolgere **più
tardi e in autonomia**, senza far aspettare l'utente davanti allo schermo. Si
"mette in coda" il compito e un programma in sottofondo lo esegue, uno dopo
l'altro.

## Il problema che risolve

Alcune operazioni dell'ERP sono **lunghe** o si fanno **a lotti**: un intero giro
di fatturazione, la stampa di centinaia di documenti, l'invio di molte email o
PEC. Se l'utente dovesse aspettare che finiscano, resterebbe bloccato con la
clessidra per minuti, e un errore a metà rischierebbe di lasciare le cose a metà.

La soluzione è **spezzare in due momenti**:

1. **Adesso** l'utente chiede l'operazione: il sistema la **registra in coda** e
   risponde subito («ho preso in carico, ci sto lavorando»).
2. **Poco dopo** un lavoratore in sottofondo (lo chiamiamo *worker*) prende il
   compito dalla coda e lo svolge. L'utente, intanto, continua a lavorare e vede
   l'avanzamento aggiornarsi.

## Come funziona in ZeroErp (in parole semplici)

* Un compito da svolgere si chiama **job**. Ha un **tipo** (cosa fare, es.
  «giro di fatturazione») e i suoi **dati** (es. il mese di competenza).
* Si mette in coda con una sola operazione (**accodare**). Questo avviene
  **insieme** al salvataggio del dato di business, non dopo (è il punto chiave —
  vedi sotto).
* Un **unico worker** legge la coda, prende i job in ordine di **priorità**, e per
  ciascuno chiama il pezzo di programma giusto in base al tipo (il *dispatch*).
* Se un job **fallisce**, non blocca gli altri: viene **ritentato** più tardi, per
  un numero massimo di volte; oltre la soglia resta segnato come *errore* e un
  operatore può decidere se rilanciarlo.
* La coda **non fa doppioni**: se lo stesso lavoro viene richiesto due volte
  mentre è ancora in corso, la seconda richiesta si aggancia alla prima invece di
  crearne una copia (**idempotenza**).
* Un job chiesto da una persona **appartiene a un'azienda sola**: quella in cui la
  persona sta lavorando quando lo chiede. Chi lavora «su tutte le aziende» insieme
  ne mette in coda uno per azienda, oppure sceglie prima l'azienda. I job di
  sistema, che non riguardano i dati di nessuna azienda, non ne hanno.
* Un job si mette in coda solo **a proprio nome** e dentro le proprie aziende: il
  job girerà poi con quell'identità, e vedrà i dati di quell'azienda.
* **Chi vede quali job** lo decide il database, non solo lo schermo: una persona
  vede i job delle sue aziende; i job di sistema li vedono solo l'amministratore
  generale e il worker.
* Il worker lavora **un'azienda alla volta**, con un utente tecnico per ogni
  azienda. Un'azienda a cui l'utente tecnico manca resta con i job in attesa, e
  un presidio lo segnala
  ([dbops.vw_emittenti_non_serviti](/dbzero/dbops/views/vw_emittenti_non_serviti)).

Chi vuole il dettaglio tecnico (colonne, stati, indici) lo trova in
[dbops.coda_lavori](/dbzero/dbops/tabelle/coda_lavori).

## Quando usarla — e quando no

**Usala quando** l'operazione:

* è **lunga** o **a lotti** (fatturazione massiva, invii multipli, export grandi);
* deve poter **ritentare** da sola in caso di intoppo temporaneo;
* deve partire **in modo garantito insieme** al salvataggio di un dato importante
  (soprattutto dati fiscali o contabili);
* non deve tenere l'utente in attesa.

**Non usarla quando** l'operazione:

* è **istantanea** (una semplice lettura o un piccolo salvataggio): falla e basta;
* è un **lavoro schedulato a orari fissi** che riguarda la manutenzione del
  sistema o gli accessi (ogni notte, ogni ora): quello resta gestito dagli
  strumenti di pianificazione già in uso
  ([pgAgent + timer di sistema](/guide/processi-pgagent-funzionali)).

> 🔴 **Correzione del 06-09-2026, e ribalta la riga qui sopra per metà dei
> casi.** Qui c'era scritto che i lavori a orario la coda «non li sostituisce».
> Per i lavori che toccano i dati di un'azienda **li sostituisce**: l'orologio
> si limita a **svegliare** — accoda un lavoro per ogni azienda — e a eseguirlo
> è la coda, con l'identità di quell'azienda addosso.
>
> Il motivo in due righe: dentro l'orologio un lavoro non ha un nome, quindi le
> protezioni che si basano sul nome non possono fare niente; e un suo fallimento
> non arriva a nessuno. ⇒ [I lavori automatici — capitolo 4](/guide/processi-automatici-classe-e-identita)
>
> ⚠️ Ne segue una regola pratica: **un lavoro di dominio non si può accodare
> senza un operatore**. Il sistema lo rifiuta, ed è voluto — è ciò che gli
> impedisce di tornare a girare in incognito.

## Perché è stata costruita sul database, e non con Celery/RQ

Nel mondo Python lo strumento "classico" per i lavori in sottofondo è un **broker
di messaggi** esterno (Redis) con Celery o RQ. In ZeroErp abbiamo scelto
deliberatamente di **tenere la coda dentro PostgreSQL**. Il motivo principale è
uno, e pesa più di tutti gli altri:

**L'accodamento avviene nella stessa "scatola" del dato di business.** Quando
salvi il documento e metti in coda il lavoro, o **succedono entrambe le cose o
nessuna** delle due (è un'unica transazione del database). Non può capitare di
aver salvato il documento ma perso il lavoro, né il contrario.

Con un broker esterno, invece, ci sono **due sistemi separati** (il database e
Redis): salvi nel database *e poi* mandi il messaggio a Redis. Se una delle due
va a buon fine e l'altra no, resti in uno stato incoerente — il classico problema
del **"doppio salvataggio" (dual-write)**. Per lavori che toccano **fatture,
numerazioni fiscali, contabilità**, questo rischio è inaccettabile.

Riassumendo, in parole semplici:

| | Coda su database (questa) | Broker esterno (Redis + Celery/RQ) |
| --- | --- | --- |
| Accodare **insieme** al dato | ✅ tutto-o-niente, nessun rischio di incoerenza | ❌ due sistemi, due possibili fallimenti |
| Serve nuova infrastruttura? | No: PostgreSQL c'è già | Sì: Redis + worker + monitoraggio |
| Come si controlla lo stato | Guardando una tabella (una query) | Servono cruscotti esterni |
| Adatto a dati fiscali/contabili | ✅ ideale | ⚠️ rischioso |

> La scelta **non è "il database batte sempre i broker"**. Un broker esterno resta
> un'opzione futura per volumi enormi di lavori *non transazionali* ed eterogenei.
> Ma per i lavori dell'ERP — che quasi sempre nascono attaccati a un dato di
> business — la coda su database è la scelta più sicura e più semplice.

## Chi la usa: oggi e domani

* **Oggi** — il **giro di fatturazione on-demand**: l'operatore chiede «fattura il
  mese», il sistema accoda il lavoro e lui vede l'avanzamento senza restare
  bloccato. (È il tipo `FATTURAZIONE_GIRO`.)
* **Domani — l'invio di email / PEC / SDI**: è il **secondo utilizzatore
  naturale**. Oggi le email hanno un loro "cassetto di bozze"
  ([gestione mail](/guide/gestione-mail)) e l'invio parte in modo diretto;
  spostare l'**invio massivo e la PEC/SDI** sulla coda generica darebbe loro, in un
  colpo solo, gli stessi vantaggi di **ripetizione automatica, priorità e
  ripartenza** già collaudati sul giro di fatturazione.
* **Più avanti** — report pesanti, export di grandi moli di dati, e ogni nuovo
  lavoro asincrono che dovesse servire.

Il bello è che **aggiungere un nuovo utilizzatore non richiede una nuova coda né
modifiche al database**: basta dichiarare un nuovo *tipo* di job e scrivere il
pezzo di programma che lo svolge.

## Come si osserva, e cosa succede agli errori

La coda non vive isolata: si aggancia a due sistemi già esistenti dell'ERP.

**Osservabilità — chi ha fatto cosa e quando.** Il lavoratore che svuota la coda è,
a tutti gli effetti, uno dei "lavori in sottofondo" che il sistema già traccia: ogni
sua passata lascia un record in
[maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) (con esito, durata
e un blocco anti-sovrapposizione), esattamente come il giro di fatturazione notturno o
lo svuotamento della coda di stampa. In più, **ogni singolo lavoro conserva il
collegamento alla passata che lo ha eseguito**. Il quadro di come si leggono queste
esecuzioni è nella
[guida Tracciamento processi e job](/guide/analisi-tracciamento-processi-e-job).

**Errori — due momenti, due posti giusti.**

* Se qualcosa non va **al momento di mettere in coda** (tipo di lavoro sconosciuto o
  disattivato), l'errore passa dal sistema centrale dei
  [messaggi di errore](/guide/Messaggi-di-Errore-e-Generazione-Log): un **codice
  stabile**, un messaggio leggibile e una traccia che **resta anche se l'operazione
  viene annullata**.
* Se un lavoro **fallisce mentre viene svolto**, l'errore viene annotato sul lavoro
  stesso (l'ultimo errore e il numero di tentativi) e l'esito della passata finisce nel
  registro dei job. Il lavoro viene **ritentato** e, superata la soglia, resta segnato
  come *errore* per l'intervento di un operatore. Perché la traccia sia utile, chi
  scrive un nuovo tipo di lavoro deve segnalare i fallimenti con un **codice di errore
  registrato** (non un errore generico).

In breve: **niente errori silenziosi** — o finiscono nel registro centrale, o restano
scritti sul lavoro e sulla passata che lo ha trattato.

## Una nota: la coda di stampa è una cosa a parte

Oltre a questa coda generica esiste già una **coda dedicata alla stampa dei
documenti** (le fatture di un lotto). Non è un doppione: ha una natura più
"tipizzata" ed è pensata per crescere verso un archivio documentale. La regola
che seguiamo è **"code diverse dove serve, ma un solo motore che le fa girare"**:
la logica che preleva i compiti, li ritenta e recupera quelli rimasti appesi è
**condivisa**, così non viene scritta due volte.

## In pratica

L'operatore preme «Fattura competenza»:

1. Il sistema **accoda** il lavoro insieme alla richiesta e risponde subito con un
   "biglietto" (l'identificativo del job).
2. Il worker in sottofondo prende il job, esegue il giro di fatturazione con i
   permessi dell'operatore, e ne segna l'esito.
3. La schermata dell'operatore, controllando quel biglietto, mostra
   l'avanzamento e infine l'esito — senza che nessuno sia mai rimasto bloccato in
   attesa.

---

*Per il dettaglio tecnico degli oggetti database vedi
[dbops.coda_lavori](/dbzero/dbops/tabelle/coda_lavori),
[dbops.coda_lavori_tipi](/dbzero/dbops/tabelle/coda_lavori_tipi) e
[dbops.fn_accoda_lavoro](/dbzero/dbops/funzioni/fn_accoda_lavoro).*

---
{% include-markdown "signature-core.md" %}
