# Guida — Sicurezza di ZeroErp

> **Ultimo aggiornamento**: 26 settembre 2026
>
> **Destinatari**: chiunque voglia capire come ZeroErp protegge i dati e il codice, senza
> bisogno di essere uno sviluppatore. Chi deve configurare o usare gli strumenti legge il
> documento tecnico: [Sicurezza e qualità statica](../dev/sicurezza-e-qualita-statica.md).
>
> **Vedi anche** — guide correlate:
>
> * [Architettura Permessi e Autorizzazioni](architettura-permessi-e-autorizzazioni.md) — chi può fare cosa
> * [Architettura multi face auth](architettura-multi-face-auth.md) — come si entra, e con quale veste
> * [Risorse umane e accessi](risorse-umane-e-accessi.md) — credenziali, blocchi, reset password
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
   seguito — per esempio provando password a raffica — viene rallentato e poi respinto. Le parti
   del sistema che servono solo agli sviluppatori, da fuori, semplicemente non esistono.

2. **Chi sei.** Per entrare servono credenziali. Dopo alcuni tentativi sbagliati l'accesso si
   frena, poi si blocca. Le password devono essere robuste (maiuscole, minuscole, cifre, simboli),
   e chi riceve una password provvisoria è obbligato a cambiarla al primo accesso. L'accesso dura
   un tempo limitato e si rinnova in automatico; all'uscita il «biglietto» viene annullato.

3. **Cosa puoi fare.** Ogni funzione di ZeroErp appartiene a un'**area** (vendite, anagrafiche,
   configurazione, …). Per ogni area un utente può avere accesso completo, sola lettura, oppure
   nessun accesso. Una funzione che non dichiara la propria area è **negata per principio**: nel
   dubbio, il sistema dice no.

4. **Cosa puoi vedere.** Anche dentro un'area, non tutti vedono tutto: un'azienda del gruppo vede
   i propri documenti, un reparto le proprie mail. Questa regola non sta solo nel programma, ma
   **dentro il database**: anche se il programma avesse un errore, il database non restituirebbe
   righe che l'utente non deve vedere.

5. **Nessuna modifica per sbaglio.** Una schermata che si limita a *mostrare* dati non ha il
   permesso tecnico di modificarli.

6. **La traccia.** Il sistema registra chi ha fatto cosa, quando e da quale sessione. Gli accessi
   bloccati e i permessi negati finiscono in un registro dedicato alla sicurezza.

---

## Mentre si scrive il software: i controlli automatici

Ogni modifica al codice passa da due controlli automatici: uno sul computer di chi la scrive, al
momento del salvataggio nel progetto (il *commit*), e uno sul server, prima che la modifica venga
unita al resto (la *CI*).

| Controllo | Che cosa cerca, in parole semplici |
| --- | --- |
| **Analisi del codice** | errori di programmazione e costruzioni pericolose: per esempio un'interrogazione al database composta in modo che un utente malintenzionato potrebbe manipolarla, o un errore che viene ignorato in silenzio |
| **Ricerca di segreti** | password, chiavi o token finiti per sbaglio nel codice. Un segreto pubblicato va considerato perso: questo controllo lo ferma prima |
| **Componenti di terze parti** | le librerie esterne che ZeroErp usa vengono confrontate con gli elenchi pubblici di vulnerabilità note |
| **Pacchetto finale** | il pacchetto pronto da installare viene analizzato allo stesso modo |
| **Configurazione di produzione** | che le impostazioni di sicurezza del server siano quelle giuste (cookie protetti, modalità di debug spenta, chiave segreta robusta) |
| **Regole del database** | che nessuna modifica al database dia a qualcuno più permessi del dovuto |
| **Test** | migliaia di prove automatiche, fra cui quelle che verificano che ogni funzione sia protetta da un permesso |

Ogni controllo è stato acceso **dopo** aver corretto tutto ciò che trovava già: così, quando uno
di questi controlli si accende di rosso, vuol dire sempre che il problema l'ha appena introdotto
la modifica in esame.

---

## I segreti

Password del database, chiave segreta del server e simili **non stanno mai nel codice**: vivono in
file che restano solo sulla macchina che li usa. Nel progetto c'è soltanto un **modello** con i
nomi delle impostazioni, da compilare.

Se il server viene avviato senza la chiave segreta, **si rifiuta di partire** invece di usarne
una di ripiego. Una partenza «di ripiego» sarebbe più comoda, ma è proprio il genere di comodità
che, dimenticata, finisce in produzione.

---

## Cosa non c'è ancora

ZeroErp è in sviluppo, e alcune difese sono decise ma non ancora costruite. L'elenco aggiornato è
nel documento tecnico, sezione «Aperto»: fra le principali, alcune intestazioni di sicurezza del
sito web e l'accesso con un secondo fattore (per esempio un codice sul telefono).

---

## Hai trovato un problema di sicurezza?

**Non aprire una segnalazione pubblica.** Segui le istruzioni del file `SECURITY.md` nella radice
del progetto: la segnalazione arriva riservata, con i tempi di risposta indicati lì.

---

## Per approfondire

Il documento tecnico — strumenti, file di configurazione, comandi, e dove sta ogni regola:
**[Sicurezza e qualità statica](../dev/sicurezza-e-qualita-statica.md)**.
