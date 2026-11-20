# Guida — Configurare il sistema senza perdere le modifiche agli aggiornamenti

> **Ultimo aggiornamento**: 20 novembre 2026
>
> **Destinatari**: chi configura il sistema per un'azienda (amministratori, consulenti di avvio),
> analisti funzionali, chi assiste gli operatori; sviluppatori che vogliono il quadro prima del
> dettaglio tecnico
>
> **Vedi anche** — schemi DB:
>
> * [dbops.automazione_seed_primo_impianto](/dbzero/dbops/tabelle/automazione_seed_primo_impianto) — l'elenco delle tabelle che seguono queste regole, con i campi del programma e quelli dell'azienda
> * [dbops.seed_righe](/dbzero/dbops/tabelle/seed_righe) — quali righe ha proposto il programma
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [dbops.fn_seed_superficie](/dbzero/dbops/funzioni/fn_seed_superficie) — per una riga: se l'ha proposta il programma, e quali campi restano suoi
>
> **Vedi anche** — guide correlate:
>
> * [Gestione mail](/guide/gestione-mail) — account e modelli delle mail
> * [Configurazione e responsività delle liste](/guide/configurazione-liste) — liste, colonne e viste salvate
> * [Automazione DB](/guide/automazione-db) — §4.9, il meccanismo per chi sviluppa

---

## In breve

Il programma arriva con una configurazione già pronta: l'account per spedire le mail, i testi
delle mail, le pagine elenco con le loro colonne e le viste salvate. È un **punto di partenza**.
Ogni azienda la adatta: scrive il proprio server di posta, riformula i testi, cambia le
etichette e l'ordine delle colonne.

La regola è una sola: **quello che l'azienda ha modificato, un aggiornamento del programma non
lo riscrive.** Quello che nessuno ha toccato, invece, l'aggiornamento continua a migliorarlo.

---

## 1. Tre tipi di dati

Non tutti i dati che il programma installa si comportano allo stesso modo.

| Tipo | Esempi | Chi decide | Agli aggiornamenti |
| --- | --- | --- | --- |
| **Regole del programma** | i codici di errore, gli stati dei documenti, le aliquote di catalogo | il programma | si aggiornano sempre; l'azienda non le modifica |
| **Configurazione proposta** | l'account mail di sistema, i modelli delle mail, le liste, le colonne e le viste salvate | il programma finché nessuno tocca la riga, poi l'azienda | il programma aggiorna solo le righe che nessuno ha modificato |
| **Dati dell'azienda** | clienti, fornitori, utenti, documenti | l'azienda | il programma non li crea e non li tocca |

Questa guida parla del secondo tipo, la **configurazione proposta**.

---

## 2. Che cosa succede a un aggiornamento

Per ogni riga della configurazione proposta il programma sa due cose: se l'ha proposta lui e se
qualcuno l'ha modificata dopo.

* **Riga proposta e mai toccata.** Segue il programma: se l'aggiornamento corregge un testo o
  aggiunge una colonna, la riga si aggiorna da sola.
* **Riga proposta e poi modificata dall'azienda.** Resta come l'ha lasciata l'azienda.
  L'aggiornamento non la riscrive, nemmeno nei campi che l'azienda non ha toccato: da quel
  momento la riga è dell'azienda.
* **Riga creata dall'azienda.** Il programma non la conosce e non la tocca mai.

⭐ **Perché si fa così.** Prima, un aggiornamento ricaricava la configurazione di partenza su
tutte le righe e cancellava il lavoro dell'azienda: il server di posta tornava quello di esempio
e la password andava persa. Ora la modifica dell'azienda vince sempre su quella del programma.

⚠️ **Una riga modificata non riceve più le migliorie.** Se il programma migliora il testo di una
mail che l'azienda ha già riscritto, quella mail resta com'era. Oggi non c'è un comando per
riportare una riga alla versione del programma.

### Un caso a parte: l'account mail di sistema

L'account `SISTEMA` il programma lo crea **una volta sola**, all'installazione, con valori di
esempio (un server finto e una password segnaposto) che ogni azienda sostituisce. Dopo non lo
aggiorna più, che l'azienda l'abbia toccato o no: un account di posta non ha niente che il
programma possa migliorare. I dettagli sono in [Gestione mail](/guide/gestione-mail).

---

## 3. Che cosa si può cambiare e che cosa no

### I campi del programma e i campi dell'azienda

Su alcune righe proposte una parte dei campi resta del programma, perché il programma la usa
per ritrovare la riga o per farla funzionare. Sulle righe che ha proposto lui questi campi
**non si cambiano**; tutti gli altri sì.

| Che cosa | Campi del programma (non si cambiano) | Campi dell'azienda (si cambiano) |
| --- | --- | --- |
| **Modelli delle mail** | il codice, il reparto, il tipo di pratica, la lingua, le variabili disponibili | l'oggetto, il testo, l'interruttore acceso/spento |
| **Liste** | il codice, il nome nel catalogo, la vista da cui legge, le regole sull'azienda emittente | le note, l'interruttore, il numero minimo di caratteri della ricerca |
| **Colonne delle liste** | il codice, il campo che mostrano, il tipo e il formato, se si possono filtrare, ordinare e cercare, se il dato è riservato, la chiave della traduzione | l'etichetta, la larghezza, l'ordine, l'allineamento, il gruppo, l'esportazione, la priorità quando lo spazio manca, l'interruttore |
| **Viste salvate (preset)** | la lista, il codice e il posto (per tutti, per un profilo, per un'azienda) | il nome, le righe per pagina, l'ordinamento, i filtri, le colonne mostrate, l'interruttore |

Sulle pagine che lo mostrano, i campi del programma sono spenti e spiegano perché. Dove non lo
mostrano, il salvataggio viene rifiutato con un messaggio che dice quale campo il programma non
lascia cambiare.

⭐ **Per avere una versione diversa si crea una riga nuova.** Un modello di mail diverso per un
reparto o per una lingua è un modello nuovo, che vale accanto a quello del programma. Una lista o
una vista salvata nuova è dell'azienda per intero, in tutti i suoi campi.

### Le righe proposte non si cancellano: si spengono

Una riga proposta dal programma non si elimina. Si **spegne**: smette di essere usata e resta
nell'archivio, pronta a essere riaccesa. Il motivo è che il programma, o i dati che ci sono già,
possono contare su di essa: una mail spedita ricorda l'account e il modello con cui è partita.
Le righe create dall'azienda seguono le regole della loro pagina.

### Le viste salvate e le loro colonne

Le colonne di una vista salvata fanno parte della vista. Se l'azienda cambia quali colonne mostra
una vista proposta dal programma, o il loro ordine, la vista diventa dell'azienda: gli
aggiornamenti successivi non ne cambiano più le colonne.

Finché una vista proposta resta intatta, invece, il programma può migliorarla. Gli utenti che
partivano da quella vista vedono allora l'avviso «preset aggiornato», come quando la modifica un
amministratore ([Configurazione delle liste](/guide/configurazione-liste), §10.5).

---

## 4. Dove valgono queste regole

Oggi le seguono:

* l'**account mail di sistema** (creato una volta sola, §2);
* i **modelli delle mail**;
* le **liste**, le loro **colonne**, le **viste salvate** e le colonne di ogni vista salvata.

Le altre tabelle di configurazione appartengono al primo tipo del §1 (regole del programma) o al
terzo (dati dell'azienda). L'elenco aggiornato, con i campi del programma e quelli dell'azienda
tabella per tabella, è nella scheda del
[registro](/dbzero/dbops/tabelle/automazione_seed_primo_impianto).

---

## 5. Caricare la configurazione in blocco

Capita di voler caricare molte righe insieme invece di inserirle una per una dalle pagine:
per esempio i testi delle mail in un'altra lingua, o le colonne di una lista copiate da
un'installazione di prova.

**Un caricamento fatto dall'azienda vale come una modifica dalle pagine.** Le regole sono le
stesse del §3:

* le **righe nuove** sono dell'azienda, in tutti i campi;
* su una **riga proposta dal programma** si possono scrivere i campi dell'azienda, e la riga
  diventa dell'azienda (non riceverà più le migliorie, §2);
* un caricamento che prova a cambiare un **campo del programma** su una riga proposta viene
  rifiutato (e con lui tutto il blocco, se il caricamento è un'operazione sola): si correggono i
  dati e si ricarica;
* un caricamento che prova a **cancellare** una riga proposta viene rifiutato: la riga si spegne.

⚠️ **Il caricamento si fa con le credenziali dell'applicazione, mai con quelle che il
programma usa per aggiornarsi.** Il programma riconosce chi scrive dall'utente del database.
Quello degli aggiornamenti per lui è il programma stesso, e il caricamento sbaglia in due modi:

* le scritture sulle righe che l'azienda ha modificato vengono **scartate**: il caricamento
  sembra riuscito ma non ha cambiato niente, e lo dice solo un avviso nel registro della sessione;
* le righe **nuove** risultano proposte dal programma: non si potranno più cancellare, e i loro
  campi del programma non si potranno più cambiare.

### Il verso opposto: una configurazione che entra nel programma

Una lista preparata a mano su un'installazione di prova può diventare parte del programma, e
arrivare così a tutte le installazioni. Lo fa chi sviluppa: esporta le righe dal database,
le aggiunge ai file di partenza del programma, e da quel rilascio sono **configurazione
proposta**. Su ogni installazione seguono le regole di questa guida: dove la riga manca il
programma la crea, dove c'è già ed è stata modificata non la tocca.

---

## 6. Domande frequenti

**Ho provato a eliminare un modello di mail e il programma dice di no.**
È una riga proposta dal programma: si spegne con l'interruttore, non si elimina (§3).

**Non riesco a cambiare il codice di una colonna.**
Il codice è un campo del programma: le viste salvate e le preferenze degli utenti ritrovano la
colonna da lì. Per una colonna diversa se ne crea una nuova.

**Dopo l'aggiornamento il testo di una mail non è cambiato, ma le note di rilascio dicevano di sì.**
Il modello era stato modificato dall'azienda: l'aggiornamento non lo riscrive (§2). Il testo
nuovo si può copiare a mano.

**Voglio tornare alla versione del programma di una riga che ho modificato.**
Oggi non c'è un comando che lo faccia: la riga resta dell'azienda. Si possono riscrivere a mano
i valori del programma, ma la riga resta comunque dell'azienda e non riceve le migliorie.

**Ho caricato dei dati e non è cambiato niente.**
Probabilmente il caricamento è partito con le credenziali degli aggiornamenti (§5): va rifatto
con quelle dell'applicazione. Le righe nuove che quel caricamento ha creato risultano proposte dal
programma: per correggerle serve chi sviluppa.

---

## 7. Per chi sviluppa

Il meccanismo è una regola del framework delle automazioni: registro delle tabelle, trigger,
runner e porta di manutenzione sono descritti in [Automazione DB §4.9](/guide/automazione-db).
Le tre specie di seed, il criterio per scegliere la forma di una tabella (per riga, per colonna,
solo inserimento, figlia) e il divieto di ritoccare il CSV nello stesso rilascio in cui la tabella
entra nel registro stanno in [linee-guida SQL §11.7](/linee-guida-sql).

Le pagine di amministrazione leggono «proposta dal programma» e «campi del programma» da
[dbops.fn_seed_superficie](/dbzero/dbops/funzioni/fn_seed_superficie): l'elenco dei campi non si
ricopia nel backend né nel frontend.

---
{% include-markdown "signature-core.md" %}
