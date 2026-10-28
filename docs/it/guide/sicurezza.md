# Guida — Sicurezza di ZeroErp

> **Ultimo aggiornamento**: 25 ottobre 2026
>
> **Destinatari**: chiunque voglia capire come ZeroErp protegge i dati e il codice, senza
> bisogno di essere uno sviluppatore. Chi deve configurare o usare gli strumenti legge il
> documento tecnico: [Sicurezza e qualità statica](../dev/sicurezza-e-qualita-statica.md).
>
> **Vedi anche** — guide correlate:
>
> * [Architettura Permessi e Autorizzazioni](architettura-permessi-e-autorizzazioni.md) — chi può fare cosa
> * [Architettura multi face auth](architettura-multi-face-auth.md) — come si entra, e con quale veste
> * [Risorse umane e accessi](risorse-umane-e-accessi.md) — credenziali, blocchi, secondo fattore, reset password
> * [Audit e tracciabilità](audit-e-tracciabilita.md) — chi ha fatto cosa, e quando
> * [Presidi e registri del debito](presidi-e-registri-del-debito.md) — perché un controllo automatico vale più di una regola scritta

---

## L'idea in una riga

ZeroErp non si affida a **una** porta blindata: mette **più cancelli in fila**, ognuno con un
compito solo. Se uno sbaglia, il successivo ferma comunque la richiesta.

E la stessa idea vale per il codice: prima che una modifica entri nel progetto, la controllano
degli **strumenti automatici**, non la buona volontà di chi la scrive.

---

## Due momenti diversi

La sicurezza di ZeroErp lavora in due momenti:

| Quando | Cosa si controlla | Con che cosa |
| --- | --- | --- |
| **Mentre si scrive il software** | che il codice nuovo non introduca difetti, segreti o dipendenze vulnerabili | strumenti di analisi automatica, al salvataggio della modifica e prima di unirla al progetto |
| **Mentre il software lavora** | che ogni richiesta arrivi da chi dice di essere, e tocchi solo ciò che le spetta | i cancelli descritti qui sotto |

---

## Mentre il software lavora: i cancelli

Quando un utente apre una schermata, la sua richiesta attraversa questi cancelli, in quest'ordine.

1. **L'ingresso.** C'è una sola porta d'entrata, cifrata (HTTPS). Chi bussa troppe volte di
   seguito viene rallentato e poi respinto, con limiti più stretti sul login e sul recupero della
   password. Le parti del sistema che servono solo agli sviluppatori, da fuori, semplicemente non
   esistono. Il browser riceve istruzioni che gli impediscono di caricare codice da altri siti o di
   mostrare ZeroErp dentro la pagina di qualcun altro.

2. **Chi sei.** Per entrare servono credenziali, e chi entra lo fa da una **porta**: quella degli
   operatori, quella del portale clienti e fornitori, quella del negozio online. La persona è una
   sola, con una sola password, anche se ha più ruoli.
   * **Password robuste**: maiuscole, minuscole, cifre e simboli. Quando un amministratore lo
     chiede, il cambio della password è obbligatorio al primo accesso utile. Chi viene invitato la
     sceglie da sé: nessuno gli manda una password provvisoria.
   * **Secondo fattore**: oltre alla password, un codice generato da un'app sul telefono. È
     obbligatorio per gli amministratori del sistema, e lo si può rendere obbligatorio per una
     persona o per un profilo. Se si perde il telefono, ci sono codici di recupero da usare una volta
     sola.
   * **Chi prova le password a ripetizione** viene frenato: dopo alcuni errori dalla stessa
     macchina l'accesso da lì si sospende per qualche minuto, e oltre una soglia ogni nuovo tentativo
     deve aspettare un po' di più. Il titolare, dalla sua macchina, può entrare lo stesso. Un nome
     utente che non esiste riceve le stesse risposte di uno che esiste: chi prova non scopre quali
     nomi sono veri. Il blocco vero e proprio di un account lo decide solo un amministratore, con un
     motivo.
   * **La sessione** dura poco e si rinnova da sola finché si lavora; il «biglietto» che la rinnova
     sta in un cookie che il codice della pagina non può leggere. All'uscita il biglietto viene
     annullato.

3. **Cosa puoi fare.** Ogni funzione di ZeroErp appartiene a un'**area** (vendite, anagrafiche,
   configurazione, …). Per ogni area un utente può avere accesso completo, sola lettura, oppure
   nessun accesso. Una funzione che non dichiara la propria area è **negata per principio**: nel
   dubbio, il sistema dice no.

4. **Cosa puoi vedere.** Anche dentro un'area, non tutti vedono tutto: un operatore vede i documenti
   delle aziende del gruppo che gli sono assegnate, un reparto le proprie mail, un cliente del
   portale solo i propri documenti, un cliente del negozio solo i propri acquisti fatti lì. Questa
   regola non sta solo nel programma, ma **dentro il database**: anche se il programma avesse un
   errore, il database non restituirebbe righe che l'utente non deve vedere. Gli utenti tecnici che
   potrebbero scavalcare questa regola non sono usabili dal sito.

5. **Nessuna modifica per sbaglio.** Una schermata che si limita a *mostrare* dati non ha il
   permesso tecnico di modificarli.

6. **La traccia.** Il sistema registra chi ha fatto cosa, quando e da quale sessione. Gli accessi
   bloccati e i permessi negati finiscono in un registro dedicato alla sicurezza.

E due attenzioni che stanno nella pagina, non nel server: il testo delle email che arriva da fuori
viene ripulito prima di essere mostrato, e all'uscita i dati dell'utente vengono cancellati dalla
memoria del browser, così chi entra dopo sullo stesso computer non li vede.

---

## Mentre si scrive il software: i controlli automatici

Ogni modifica al codice passa da due controlli automatici: uno sul computer di chi la scrive, al
momento del salvataggio nel progetto (il *commit*), e uno sul server, prima che la modifica venga
unita al resto (la *CI*).

| Controllo | Che cosa cerca, in parole semplici |
| --- | --- |
| **Analisi del codice** | errori di programmazione e costruzioni pericolose: per esempio un'interrogazione al database composta in modo che un utente malintenzionato potrebbe manipolarla, o un errore che viene ignorato in silenzio. Vale per il server e per la pagina |
| **Ricerca di segreti** | password, chiavi o token finiti per sbaglio nel codice. Un segreto pubblicato va considerato perso: questo controllo lo ferma prima |
| **Componenti di terze parti** | le librerie esterne che ZeroErp usa, sul server e nella pagina, vengono confrontate con gli elenchi pubblici di vulnerabilità note |
| **Pacchetto finale** | il pacchetto pronto da installare viene analizzato allo stesso modo |
| **Configurazione di produzione** | che le impostazioni di sicurezza del server siano quelle giuste (cookie protetti, modalità di debug spenta, chiave segreta robusta) |
| **Regole del database** | che nessuna modifica al database dia a qualcuno più permessi del dovuto, e che ogni tabella con dati di un'azienda abbia la sua regola di visibilità |
| **Test** | migliaia di prove automatiche, fra cui quelle che verificano che ogni funzione sia protetta da un permesso e che l'identità di un utente non resti appesa alla richiesta di un altro |

Ogni controllo è stato acceso **dopo** aver sistemato ciò che trovava già: corretto, oppure scritto
in un registro che può solo calare. Così, quando uno di questi controlli si accende di rosso, vuol
dire che il problema l'ha appena introdotto la modifica in esame.

---

## I segreti

Password del database, chiave segreta del server e simili **non stanno mai nel codice**: vivono in
file che restano solo sulla macchina che li usa. Nel progetto c'è soltanto un **modello** con i
nomi delle impostazioni, da compilare.

Se il server viene avviato senza la chiave segreta, o senza le chiavi che cifrano i dati delicati
salvati nel database (come il segreto del secondo fattore), **si rifiuta di partire** invece di
usarne una di ripiego. Una partenza «di ripiego» sarebbe più comoda, ma è proprio il genere di
comodità che, dimenticata, finisce in produzione.

---

## Cosa non c'è ancora

ZeroErp è in sviluppo, e alcune cose sono decise o proposte ma non ancora fatte. L'elenco aggiornato
è nel documento tecnico, sezione «Aperto»: fra le principali, un filtro che oscuri i dati sensibili
nei log e un servizio che segnali da solo gli aggiornamenti di sicurezza delle librerie.

---

## Hai trovato un problema di sicurezza?

**Non aprire una segnalazione pubblica.** Segui le istruzioni del file `SECURITY.md` nella radice
del progetto: la segnalazione arriva riservata, con i tempi di risposta indicati lì.

---

## Per approfondire

Il documento tecnico — strumenti, file di configurazione, comandi, e dove sta ogni regola:
**[Sicurezza e qualità statica](../dev/sicurezza-e-qualita-statica.md)**.
