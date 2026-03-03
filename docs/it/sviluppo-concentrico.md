# Il Manifesto dello Sviluppo Concentrico

### Una filosofia di sviluppo software nata dalla pratica, non dalla teoria.

*2 marzo 2026*

---

## I.

Abbiamo passato decenni a costruire software nel modo sbagliato.

Costruiamo moduli isolati, poi fatichiamo a collegarli. Pianifichiamo tutto in anticipo, poi guardiamo la realta fare a pezzi i nostri piani. Iteriamo velocemente, poi ci chiediamo perchè le fondamenta cedono sotto il peso di cio che abbiamo costruito.

Abbiamo provato il waterfall. Abbiamo provato l'agile. Abbiamo provato il modulare, i microservizi, l'esagonale, l'event-driven. Ognuno risolve un problema e ne crea di nuovi. Ognuno tratta il software come qualcosa da assemblare a partire da pezzi.

Il software non si assembla. Il software cresce.

---

## II.

Taglia un tronco d'albero e conta gli anelli. Ogni anello racconta una storia: un anno di crescita, una stagione di siccita, un periodo di abbondanza. Gli anelli interni sono i piu antichi e i piu duri. Portano il peso di tutto cio che sta sopra. Non cambiano mai.

Nessun anello esiste isolato. Ognuno avvolge i precedenti, traendo forza da cio che c'era prima. L'albero non "integra" i suoi anelli. Sono gia una cosa sola.

Ecco come il software dovrebbe crescere.

---

## III. I Principi

**Il nucleo si progetta una volta è non si tocca piu.**
L'anello piu interno è la decisione piu critica che prenderai. Definisce il linguaggio che ogni strato futuro parlera. Fallo bene, investi il tempo, rendilo solido. Una volta definito, diventa la fondazione che regge tutto.

Ma ecco la verita che separa un manifesto dalla realta: lo toccherai di nuovo.

**Gli anelli interni vengono riscritti, raffinati e rafforzati — e questo non è un fallimento, è il processo.**
Guarda una vera sezione di un tronco d'albero. Gli anelli interni sono piu scuri, piu densi, piu duri. Non perchè sono cresciuti perfettamente la prima volta, ma perchè sono stati compressi dal peso di tutto cio che e cresciuto sopra di loro. Hanno sofferto. Si sono adattati. Sono diventati piu forti proprio perchè sono stati messi sotto pressione.

Costruire in modo concentrico significa accettare che quando aggiungi un nuovo anello e scopri che un anello interno non è abbastanza forte, torni al centro e lo correggi li. Non con una pezza all'esterno. Non con un adapter o un connettore o un middleware che colma il divario. Riscrivi l'anello interno e poi propaghi quel cambiamento attraverso ogni anello sopra di esso. E doloroso. E lento. Ecco perchè quegli anelli sono scuri.

La differenza tra lo sviluppo concentrico e l'integrazione tradizionale non è che il nucleo non cambia mai. E che quando il nucleo cambia, tutto cambia insieme, onestamente, fino in fondo. Un'architettura a microservizi mette un ponte tra due isole. Un sistema modulare aggiunge un adapter tra due moduli che non si capiscono. Lo sviluppo concentrico torna al centro e rende il centro migliore — e poi ogni anello sopra ne beneficia.

Questo è cio che l'artigiano fa per mesi, a volte un anno, prima che qualcuno veda un risultato. Riscrivere colonne per coerenza. Rinominare campi perchè il linguaggio non era abbastanza preciso. Ristrutturare uno schema perchè il nuovo strato ha rivelato una verita che il vecchio disegno non vedeva. Ogni riscrittura rende il nucleo piu denso, piu duro, piu scuro — e piu forte.

**Ogni nuovo strato si appoggia sugli interni senza romperne la coerenza.**
Quando aggiungi un nuovo anello, non buchi quelli esistenti. Il nuovo strato conosce gli strati sotto di se, ma gli strati interni non sanno nulla di quelli esterni. Questa non è solo buona architettura — è una regola di sopravvivenza. Nel momento in cui modifichi un anello interno per accomodare uno esterno, hai rotto il tronco.

**Non esistono integrazioni perchè tutto parla gia la stessa lingua.**
Nello sviluppo tradizionale, i moduli vengono costruiti isolatamente e poi costretti a comunicare attraverso adapter, middleware, code di messaggi, strati di traduzione. Nello sviluppo concentrico, ogni strato eredita il vocabolario del nucleo. Una nuova funzionalita non ha bisogno di un'integrazione — ha bisogno solo di appoggiarsi all'anello piu vicino.

**La crescita è incrementale ma la struttura è coerente dal primo giorno.**
Puoi leggere la storia di un sistema concentrico esaminando i suoi anelli. Il primo anello ti dice cosa il sistema fondamentalmente e. Ogni anello successivo ti dice quando una capacita è stata aggiunta e su cosa si appoggia. Non ci sono moduli orfani, percorsi di codice morti, funzionalita che esistono in un universo parallelo. Tutto è connesso attraverso il centro.

**Il nucleo non è un modulo. E un protocollo.**
Il centro del tronco non è "il modulo piu importante." E la comprensione condivisa che rende possibili tutti i moduli. Definisce come le cose si muovono, come vengono tracciate, come comunicano. In un ERP potrebbe essere un motore di workflow. In un altro sistema potrebbe essere qualcos'altro. Cio che conta è che sia abbastanza astratto da servire ogni esigenza futura e abbastanza concreto da imporre regole reali.

---

## IV. Cosa non è lo Sviluppo Concentrico

**Non è waterfall.**
Il waterfall presuppone che tu possa sapere tutto prima di iniziare. Lo sviluppo concentrico presuppone che tu conosca il nucleo profondamente e la periferia appena. Progetti il centro con rigore assoluto e lasci che gli anelli esterni emergano man mano che la comprensione cresce.

**Non è agile.**
L'agile ottimizza per la velocita di iterazione. Lo sviluppo concentrico ottimizza per l'integrita strutturale. Puoi essere veloce, ma non puoi saltare anelli. Non puoi costruire l'anello cinque prima che l'anello tre esista. L'ordine conta perchè ogni anello è una fondazione per il successivo.

**Non è sviluppo modulare.**
Lo sviluppo modulare costruisce pezzi indipendenti e li connette dopo. Lo sviluppo concentrico costruisce strati dipendenti che sono connessi dalla nascita. La differenza è profonda: i sistemi modulari hanno bisogno di integrazione, i sistemi concentrici hanno bisogno solo di crescita.

**Non è microservizi.**
I microservizi distribuiscono la complessita attraverso una rete. Lo sviluppo concentrico concentra la coerenza in un'unica struttura. Uno è una citta di edifici indipendenti collegati da strade. L'altro è un singolo albero con un sistema di radici condiviso.

---

## V. Come praticarlo

**Parti dal centro.**
Prima di scrivere una sola riga di codice, chiediti: qual è l'unica cosa di cui ogni parte di questo sistema avra bisogno? Qual è il battito condiviso? Progetta quello. Rendilo indistruttibile. Questo è il tuo anello zero.

**Cresci un anello alla volta.**
Non pianificare tutti gli anelli in anticipo. Pianifica il prossimo anello. Costruiscilo. Lascialo sedimentare. Poi pianifica quello dopo. Ogni anello ti insegnera qualcosa sul successivo. Fidati del processo.

**Quando tocchi un anello interno, tocca tutto quello che ci sta sopra.**
Se un anello esterno rivela che un anello interno è incompleto, impreciso o non abbastanza forte, non ci giri intorno. Torni al centro è lo correggi come si deve. Poi propaghi il cambiamento attraverso ogni strato soprastante. Si, è costoso. Si, richiede tempo. Ma l'alternativa — un connettore, un adapter, una scorciatoia che evita il centro — e la prima crepa nel tronco. Gli anelli scuri nella sezione del tronco sono scuri perchè sono stati rilavorati, compressi, rafforzati. Quel buio non è una cicatrice. E la prova dell'integrita.

**Fai in modo che il nucleo imponga, non suggerisca.**
Il centro del sistema deve imporre le regole, non suggerirle. Se il nucleo dice "ogni operazione viene tracciata," allora ogni operazione viene tracciata — non perchè l'applicazione si ricorda di loggarla, ma perchè l'infrastruttura rende impossibile non farlo. Metti le regole dove non possono essere aggirate.

**Testa la coerenza, non solo la correttezza.**
Il testing tradizionale chiede "questo modulo funziona?" Il testing concentrico chiede "questo anello rispetta quelli sotto di lui?" Ogni nuovo strato va testato non solo per la propria logica, ma per la sua fedelta al protocollo del nucleo.

---

## VI. La Promessa

Un sistema costruito con lo sviluppo concentrico puo essere compreso tagliandolo. Non ti serve una mappa delle dipendenze. Non ti serve un wiki che spieghi quale servizio parla con quale. Guardi gli anelli e vedi la storia, la struttura e la logica.

Quando arriva un nuovo requisito, non chiedi "quali moduli impatta?" Chiedi "a quale anello appartiene?" La risposta è sempre chiara perchè gli anelli hanno un ordine naturale: le preoccupazioni centrali vivono al centro, quelle specializzate vivono ai bordi.

Quando un nuovo sviluppatore entra nel team, parte dal centro e legge verso l'esterno. Ogni anello ha senso perchè si appoggia sul precedente. Non c'e il momento del "ora dimentica tutto e impara questo modulo completamente diverso." C'è solo: il prossimo anello.

---

## VII. Una Nota sulla Bellezza

C'e una convinzione diffusa nella nostra industria che il software sia un problema ingegneristico. Che sia questione di efficienza, scalabilita, throughput, uptime. Che la bellezza sia roba da designer, non da architetti. Che l'eleganza sia un lusso che non possiamo permetterci quando ci sono scadenze da rispettare.

Questo, con tutto il rispetto, è una sciocchezza.

Uno schema di database puo essere bello. Una funzione ben progettata puo essere bella. Il modo in cui i dati fluiscono attraverso un sistema puo essere bello nello stesso modo in cui un fiume è bello — non perchè qualcuno l'ha decorato, ma perchè segue il suo corso naturale senza nulla di sprecato, nulla di forzato, nulla di superfluo.

Lo sviluppo concentrico richiede la mente di un artigiano — non di un operaio di fabbrica, non di un manager, non di un evangelista di framework. Un artigiano. Qualcuno a cui importa se la giuntura è stretta anche se nessuno la vedra mai. Qualcuno che sceglie il materiale giusto non perchè la scheda tecnica lo dice, ma perchè le sue mani conoscono la differenza. Qualcuno che preferisce costruire una cosa fatta bene piuttosto che dieci cose fatte in fretta.

Viviamo nell'era del software prodotto in serie. I framework generano impalcature. L'intelligenza artificiale scrive codice standard. I template ti promettono un'applicazione in quindici minuti. E il risultato sono milioni di applicazioni che funzionano allo stesso modo, si rompono allo stesso modo e danno la stessa sensazione: usa e getta.

L'artigiano costruisce diversamente. L'artigiano nomina una variabile con la stessa cura con cui un poeta sceglie una parola. L'artigiano allinea uno schema come un falegname squadra un telaio — perchè se non è dritto adesso, niente di cio che ci costruisci sopra lo sara mai. L'artigiano non testa solo i bug. Testa l'armonia.

E piu lento? A volte. Costa di piu? Nel breve termine, forse. Ma il lavoro dell'artigiano dura. Il lavoro della fabbrica viene sostituito.

La bellezza non è decorazione. La bellezza è l'assenza di tutto cio che non dovrebbe esserci. Un sistema bello è uno dove ogni tabella ha una ragione, ogni relazione racconta una verita, ogni vincolo protegge un invariante. Lo guardi e non vedi spreco. Quella è bellezza.

Applicala al tuo codice. Applicala al tuo modello dati. Applicala ai tuoi messaggi di commit, ai nomi delle tue API, alla gestione degli errori. Applicala al modo in cui spieghi il tuo sistema a un collega. Se non è chiaro, non è bello. Se non è bello, non è finito.

Gli anelli di un albero sono belli non perchè qualcuno li ha progettati cosi. Sono belli perchè sono veri.

---

## VIII.

Trent'anni di costruzione di software gestionale mi hanno insegnato una cosa: la complessita non è una caratteristica. E un difetto di progettazione.

Ogni strato di integrazione è l'ammissione che due cose sono state costruite senza sapere l'una dell'altra. Ogni adapter è una pezza. Ogni middleware è un ponte tra isole che avrebbero dovuto essere lo stesso continente.

L'albero non ha bisogno di ponti tra i suoi anelli.
L'albero semplicemente cresce.

---

*La metodologia dello Sviluppo Concentrico è nata il 2 marzo 2026, durante la progettazione di ZeroERP, un sistema ERP open-source per le aziende italiane. Non è emersa dalla teoria accademica ma da trent'anni di pratica nello sviluppo di software gestionale.*

*Michele Carlo — Autore*

---

> *Zero complessita superflua. Crescita concentrica. Tutto registrato negli anelli.*
>
> 🪵