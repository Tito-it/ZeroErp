# Guida — Generazione di un Cliente

> **Ultimo aggiornamento**: 26 novembre 2026
>
> **Destinatari**: sviluppatori database, backend e analisti funzionali
>
> **Vedi anche** — schemi DB:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la persona o azienda
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — i ruoli del soggetto (es. CLIENTE)
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — il ciclo di servizio su un indirizzo
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — l'account di fatturazione
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — il record cliente
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — il collegamento di ogni billing account alla sua azienda
> * [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp) — il punto di prelievo (contatore/allaccio)
> * [anagrafiche.catasto_unita_immobiliari](/dbzero/anagrafiche/tabelle/catasto_unita_immobiliari) — i dati catastali
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — l'indirizzo civico
> * [config.utilities](/dbzero/config/tabelle/utilities) — il tipo di servizio (GAS, ENERGIA, …)
> * [config.stati_cliente](/dbzero/config/tabelle/stati_cliente) — gli stati del cliente (AT, CH, AN, …)
> * [config.stati_pdp](/dbzero/config/tabelle/stati_pdp) — gli stati tecnici del PDP
>
> **Vedi anche** — funzioni DB:
>
> * [anagrafiche.fn_crea_cliente](/dbzero/anagrafiche/funzioni/fn_crea_cliente) — fa di un soggetto un cliente: ruolo, billing account, cliente
> * [anagrafiche.fn_crea_billing_account](/dbzero/anagrafiche/funzioni/fn_crea_billing_account) — il billing account e, se serve, l'istanza fittizia
> * [anagrafiche.fn_update_cliente](/dbzero/anagrafiche/funzioni/fn_update_cliente) — la modifica del cliente
> * [anagrafiche.fn_check_pdp_occupato](/dbzero/anagrafiche/funzioni/fn_check_pdp_occupato) — un cliente occupa il PDP in un giorno?
> * [script.fn_cliente_dal_billing_account](/dbzero/script/funzioni/fn_cliente_dal_billing_account) — ruolo e utility del cliente vengono dal billing account
> * [script.fn_subentro_cliente](/dbzero/script/funzioni/fn_subentro_cliente) — chiude il cliente precedente sul punto di prelievo
> * [script.fn_disdetta_cliente](/dbzero/script/funzioni/fn_disdetta_cliente) — la cessazione senza subentro
> * [anagrafiche.trgfn_billing_account_link_ef](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef) — il billing account nasce collegato a un'azienda
> * [anagrafiche.trgfn_billing_account_guard_normalize](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_normalize) — il padre del billing account
> * [anagrafiche.fn_check_ba_padre](/dbzero/anagrafiche/funzioni/fn_check_ba_padre) — l'albero a un livello, un padre per cliente e per azienda
> * [anagrafiche.fn_guard_ba_cambio_emittente](/dbzero/anagrafiche/funzioni/fn_guard_ba_cambio_emittente) — il cambio d'azienda, solo senza documenti
> * [anagrafiche.fn_guard_albero_ba_emittente](/dbzero/anagrafiche/funzioni/fn_guard_albero_ba_emittente) — padre e figli sulla stessa azienda
> * [script.trgfn_prevent_modification_generic](/dbzero/script/funzioni/trgfn_prevent_modification_generic) — il billing account non si cancella
>
> **Vedi anche** — guide correlate:
>
> * [Glossario termini utility](/glossario/glossario-utility) — PDP, istanza, billing account e gli altri termini ricorrenti
> * [Soggetti e Ruoli](/guide/soggetti-e-ruoli-anagrafici) — il modello anagrafico su cui poggia il cliente
> * [Gestione delle Istanze Utility](/guide/gestione-delle-istanze-utility) — il ciclo di vita dell'istanza
> * [Termini di pagamento](/guide/termini-di-pagamento) — il catalogo delle condizioni di pagamento

---

## Introduzione

In Zero ERP un **cliente** non e semplicemente una persona: e l'insieme di informazioni che collegano un soggetto (la persona o azienda) a un servizio e ai dati necessari per fatturare.

Questa guida spiega **come nasce un cliente** — quali entita creare, in che ordine, e perche il modello e fatto cosi. La logica e la stessa sia per una prima attivazione, sia per un subentro (cambio di intestatario), sia per una ripartenza dopo una cessazione.

**Cosa troverai in questa guida:**

* Le entita coinvolte e il loro ruolo nel processo
* La sequenza obbligatoria di creazione (cosa si crea prima e cosa dopo)
* Come funzionano i flussi di subentro e disdetta
* Le garanzie di sicurezza offerte dal database (transazioni, vincoli)

### Il modello e generico, non solo per le utility

La struttura descritta in questa guida (soggetto → istanza → billing account → cliente) **funziona per qualsiasi tipo di azienda**, non solo per il settore utility. L'istanza e un ponte trasparente tra il soggetto e la fatturazione: in contesti non-utility (commercio, servizi, gestione pompe funebri, ecc.) viene creata automaticamente come contenitore tecnico senza che l'utente debba occuparsene.

Le funzionalita specifiche del mondo utility — PDP (contatore), catasto, subentro, disdetta — sono **estensioni opzionali** che si attivano solo quando servono. La struttura base permette la fatturazione a prescindere dal modello di business, anche dove non esiste una parte contrattualistica complessa.

In pratica:

* **Azienda utility**: soggetto → istanza (con PDP, catasto, subentro) → BA → cliente
* **Azienda non-utility**: soggetto → istanza (generata in trasparenza, senza PDP ne catasto) → BA → cliente

Gli esempi in questa guida usano spesso il dominio utility perche e il caso piu articolato, ma le regole di base (sequenza di creazione, vincoli, transazionalita) valgono per tutti.

---

## Le entita e il loro significato

### Soggetto

E la persona fisica o giuridica registrata nel sistema. Puo avere piu ruoli (cliente, fornitore, ecc.) e piu utenze attive contemporaneamente su servizi diversi. Il soggetto **esiste prima e indipendentemente** dal contratto.

### Istanza utility

E il **ciclo tecnico-commerciale** di un servizio su un indirizzo per un soggetto. In pratica: quando un servizio gas o energia viene collegato a un civico per conto di una persona, nasce un'istanza.

L'istanza **non e il cliente**: precede il contratto (puo esistere in fase precontrattuale) e sopravvive alla chiusura del rapporto come record storico. Ma non esiste mai da sola: **nasce insieme al suo billing account** (vedi [Ogni istanza nasce col suo billing account](/guide/gestione-delle-istanze-utility#ogni-istanza-nasce-col-suo-billing-account)).

L'istanza **non ha una utility sua**: la utility sta sul billing account, uno per ciascuna utility dell'istanza.

**Perche l'istanza e legata al soggetto e non al ruolo?**
Perche l'istanza identifica semplicemente "chi" e associato a un certo indirizzo/servizio, e sopravvive al rapporto commerciale. Il ruolo CLIENTE nasce con l'istanza, perche il billing account che nasce con lei fattura a quel ruolo; il **cliente** — la specializzazione in `clienti`, con le sue date — arriva dopo, con il contratto.

Un soggetto puo non acquisire mai il ruolo CLIENTE: per esempio un soggetto che e solo fornitore. In quel caso non ha nemmeno istanze.

### Billing account (BA)

E l'account di fatturazione. Identifica **a chi fatturare**, **per quale utility** e **con quale codice**. Nasce **insieme all'istanza**, nella stessa operazione, e prima del cliente: esiste gia nella fase precontrattuale (preventivi, offerte) e viene "ereditato" dal cliente alla firma del contratto. Il suo codice si genera quando nasce.

Il BA supporta una gerarchia padre/figlio per aggregare la fatturazione di piu utenze sullo stesso intestatario. L'albero ha **un livello solo**: chi ha un padre non fa da padre, e chi fa da padre non ha un padre. Un cliente (la stessa identita fiscale o, senza, lo stesso soggetto) ha **un solo padre per azienda**, e la fattura di un figlio va al suo padre diretto. Il padre non si toglie e non si cambia finche il figlio ha attivita non fatturate. Vedi la [documentazione dedicata](/dbzero/anagrafiche/tabelle/billing_account) per i dettagli.

Un BA **non si cancella** (`E_BA_NON_SI_CANCELLA`): un cliente che non serve piu si chiude annullandolo (stato «AN annulla servizio») o, se e stato una fornitura, chiudendolo.

> **Invariante BA ↔ istanza (1:1 per utility).** Per una data utility, un
> billing account ha **una sola** istanza e un'istanza ha **un solo** BA
> (`billing_account.istanza_utility_id` FK NOT NULL + UNIQUE
> `(istanza_utility_id, utility_id)`). Quindi **dato il BA, l'istanza e'
> univoca**: i documenti che hanno gia' un BA (ordini, DDT, fatture) ricavano
> l'istanza dal BA e non la memorizzano; i precontrattuali
> (preventivi/offerte/contratti) scelgono l'istanza e la portano sulla propria
> testata accanto al BA, e il database pretende che il BA sia quello della
> coppia (istanza, utility). Dettaglio:
> [Gestione Istanze Utility — Istanza e billing account](/guide/gestione-delle-istanze-utility#istanza-e-billing-account-relazione-11-per-utility-invariante).

### Cliente

E la specializzazione commerciale del **billing account**: un cliente per billing account (`uq_clienti_billing_account`), quindi un'istanza con due utility puo avere due clienti. Lega insieme:

* l'istanza (dove)
* il billing account (a chi fatturare, e per quale utility)
* il ruolo CLIENTE del soggetto (chi)
* le date commerciali (da quando a quando)

Ruolo e utility del cliente sono **copie** di quelle del suo billing account, e non si cambiano dopo la nascita: billing account, istanza, ruolo e utility di un cliente sono la sua fornitura (`E_CLIENTE_FORNITURA_IMMUTABILE`).

### PDP (Punto Di Prelievo)

E l'entita fisica che rappresenta il contatore o allaccio a un indirizzo, per una utility. Il PDP ha un proprio stato tecnico, a catalogo in [config.stati_pdp](/dbzero/config/tabelle/stati_pdp): disponibile, attivo, staccato, dismesso. Il passaggio fra **disponibile** e **attivo** e automatico e segue l'occupazione da parte dei clienti; «staccato» e «dismesso» li governano processi loro.

Non tutti i clienti hanno un PDP (le istanze possono essere "fittizie"), ma quando c'e un PDP, esso diventa il perno del vincolo di unicita: **un solo cliente per PDP in ogni giorno**.

---

## Sequenza obbligatoria di creazione

La creazione di un cliente segue un ordine preciso, imposto dai vincoli del database. Non e possibile saltare passaggi.

### Ordine dei passi

```text
1. Soggetto        (deve gia esistere)
2. Ruolo CLIENTE   (creato se manca, tramite fn_get_or_create_soggetto_ruolo)
3. Istanza         (richiede soggetto_id NOT NULL)
4. Billing Account (richiede istanza_utility_id, soggetto_ruolo_id e utility_id NOT NULL)
5. Cliente         (richiede istanza_utility_id, billing_account_id e soggetto_ruolo_id NOT NULL)
```

### Perche questo ordine?

Ogni entita dipende dalla precedente tramite chiavi esterne obbligatorie:

| Non si puo creare... | ...senza prima aver creato... | Motivo                                                       |
| -------------------- | ----------------------------- | ------------------------------------------------------------ |
| Istanza              | Soggetto                      | `soggetto_id NOT NULL`                                       |
| Billing Account      | Istanza                       | `istanza_utility_id NOT NULL`                                |
| Cliente              | Istanza + BA                  | `istanza_utility_id NOT NULL`, `billing_account_id NOT NULL` |
| Cliente              | Ruolo CLIENTE                 | `soggetto_ruolo_id NOT NULL`                                 |

Due FK composite su `clienti` tengono il cliente legato al suo billing account: `(billing_account_id, istanza_utility_id)` garantisce che il BA sia della stessa istanza del cliente, `(billing_account_id, soggetto_ruolo_id, utility_id)` che ruolo e utility siano quelli del BA.

### Flusso pre-contrattuale vs attivazione diretta

**Pre-contrattuale** (il contratto arriva dopo):

```text
Soggetto → Ruolo CLIENTE + Istanza + Billing Account → [pausa, anche indefinita] → Cliente
```

La pausa sta **dopo il billing account**: istanza, ruolo CLIENTE e billing
account nascono insieme, nella stessa operazione, e possono restare cosi a
lungo — e il tempo dei preventivi e delle offerte. Un'istanza senza billing
account non e uno stato ammesso: il database la rifiuta (vedi [Ogni istanza
nasce col suo billing account](/guide/gestione-delle-istanze-utility#ogni-istanza-nasce-col-suo-billing-account)).
Cio che puo arrivare dopo, o non arrivare mai, e il **cliente**: il contratto.

**Attivazione diretta** (il contratto c'e gia):

```text
Soggetto + Ruolo CLIENTE → Istanza → Billing Account → Cliente
```

In entrambi i casi istanza e billing account nascono nella **stessa transazione**: non e un consiglio, il database lo pretende. Il cliente puo nascere nella stessa transazione (attivazione diretta) o dopo, col contratto.

### La creazione in una chiamata: `fn_crea_cliente`

La sequenza sta in un verbo del database,
[anagrafiche.fn_crea_cliente](/dbzero/anagrafiche/funzioni/fn_crea_cliente), che con una
chiamata sola:

* crea (o recupera) il ruolo CLIENTE del soggetto;
* crea il billing account per la utility indicata, con
  [anagrafiche.fn_crea_billing_account](/dbzero/anagrafiche/funzioni/fn_crea_billing_account),
  oppure usa un billing account che esiste gia;
* se non gli si indica un'istanza, `fn_crea_billing_account` crea l'**istanza fittizia**,
  con l'indirizzo se gli viene dato;
* crea il cliente coi campi ricevuti: se non si indica uno stato, il cliente nasce **attivo**
  dalla data operativa; con uno stato, le date le porta chi chiama, e le controlla il guard
  degli stati;
* aggiunge il contatto e gli indirizzi del ruolo, se ci sono.

Una chiave che il verbo non conosce viene rifiutata (`E_CAMPO_NON_AMMESSO`). Il subentro non
fa parte del verbo: la chiusura del cliente precedente e
[`script.fn_subentro_cliente`](/dbzero/script/funzioni/fn_subentro_cliente) (vedi l'appendice sul subentro). Le modifiche successive passano da
[anagrafiche.fn_update_cliente](/dbzero/anagrafiche/funzioni/fn_update_cliente).

Tutto avviene in una transazione atomica: se un passo fallisce, nessuna modifica viene salvata.

### Creazione manuale vs creazione da pratica

Il sistema supporta due modalita di creazione del cliente, governate dal flag `config.utilities.richiede_pdp`:

| `richiede_pdp` | Modalita                 | Istanza         | Indirizzo    | Esempio utility         |
| -------------- | ------------------------ | --------------- | ------------ | ----------------------- |
| `false`        | Manuale (da interfaccia) | Sempre fittizia | Facoltativo  | Manifatturiero, servizi |
| `true`         | Solo via pratiche        | Reale (con PDP) | Obbligatorio | GAS, Energia, Idrico    |

**Creazione manuale** (`richiede_pdp = false`):

L'operatore crea il cliente direttamente dall'interfaccia. `fn_crea_cliente` genera in trasparenza l'istanza fittizia, il billing account e il record cliente in una transazione atomica. L'operatore puo facoltativamente collegare un indirizzo all'istanza, ma non e obbligatorio. L'istanza resta fittizia in entrambi i casi perche non rappresenta un punto di erogazione fisico.

**Creazione da pratica** (`richiede_pdp = true`):

Per utility con ciclo tecnico complesso (contatore, allaccio, verifica fisica), la creazione del cliente passa dal motore pratiche. L'istanza e reale, collegata a un indirizzo e a un PDP, e il flusso include step di verifica e approvazione. Il database lo pretende dal lato del cliente: per una utility con `richiede_pdp = true` un cliente senza PDP viene rifiutato (`E_PDP_OBBLIGATORIO`). L'istanza reale non la crea un verbo del database: `fn_crea_billing_account` crea solo istanze fittizie, e a `fn_crea_cliente` l'istanza reale si passa gia scritta.

---

## Flusso operativo step-by-step

### 1. Creazione dell'istanza

Ogni cliente nasce da un'**istanza di servizio**. L'istanza puo essere:

* **reale** (`fittizia = FALSE`): associata a un indirizzo e, opzionalmente, a un PDP
* **fittizia** (`fittizia = TRUE`): senza indirizzo obbligatorio, utile per servizi che non richiedono un punto fisico

Se c'e un PDP, l'istanza non puo essere fittizia (`chk_iu_pdp_not_fittizia`), deve avere un indirizzo (`chk_iu_pdp_requires_address`) e quell'indirizzo e lo stesso del PDP: la FK `fk_iu_pdp_id_addr` lega la coppia (PDP, indirizzo) dell'istanza a quella del PDP. Niente viene copiato dal PDP all'istanza: l'indirizzo lo scrive chi crea l'istanza, e la FK lo rifiuta se non coincide. La utility non sta sull'istanza: quella del PDP si confronta con quella del billing account quando nasce il cliente (`E_PDP_UTILITY_MISMATCH`).

### 2. Creazione del billing account

Il BA viene sempre associato all'istanza (`istanza_utility_id NOT NULL`), a un ruolo soggetto e a una utility, e nasce **nella stessa operazione** dell'istanza: un'istanza senza billing account non esiste. Esiste gia **prima del cliente** (fase precontrattuale). L'istanza, il ruolo e la utility di un BA non si cambiano dopo la nascita (`E_BA_ISTANZA_IMMUTABILE`).

Il campo `codice` (l'account di fatturazione vero e proprio) viene generato automaticamente dal trigger `trgfn_billing_account_gen_codice` se non specificato, e poi non cambia.

### 3. Creazione del cliente

Il record in `anagrafiche.clienti` lega tutte le entita precedenti:

* `istanza_utility_id` → quale istanza
* `billing_account_id` → a chi fatturare, per quale utility
* `soggetto_ruolo_id` → chi e il cliente (copiato dal BA)
* `stato_cliente_id` → in che stato si trova (attivo, se alla creazione non se ne indica un altro)
* `data_attivazione` → da quando e attivo

Sulla scheda cliente vivono anche le **condizioni di pagamento** predefinite —
vedi il paragrafo successivo.

I trigger sulla tabella clienti si occupano automaticamente di:

* controllare che lo stato segua il percorso ammesso e che ogni stato abbia la sua data
* calcolare il `periodo` commerciale (daterange `[data_attivazione, data_chiusura)`)
* copiare `pdp_id` dall'istanza, e ruolo e utility dal billing account
* aggiornare lo stato del PDP secondo l'occupazione (vedi [Ordine di esecuzione](#ordine-di-esecuzione-visione-rapida))
* mantenere la catena `parent_istanza_id` per la tracciabilita dei subentri
* rifiutare, alla conferma, un secondo cliente manuale per lo stesso soggetto, servizio e azienda ([Un cliente manuale per soggetto, servizio e azienda](/guide/gestione-delle-istanze-utility#un-cliente-manuale-per-soggetto-servizio-e-azienda))

### 3-bis. Le condizioni di pagamento del cliente

Il cliente porta **due riferimenti a catalogo**, entrambi facoltativi:

* `termine_pagamento_id` — **quando** e in quante rate si paga;
* `modalita_pagamento_id` — **come** si paga (bonifico, RID, …).

Sono riferimenti, non numeri liberi: la condizione vera vive nel catalogo dei
[termini di pagamento](/guide/termini-di-pagamento), e il cliente si limita a
sceglierne uno. Chi ha condizioni particolari usa un termine dedicato a catalogo.

Due conseguenze pratiche:

* **Lasciare il termine vuoto è legittimo.** Se il cliente non ne ha uno, la
  fatturazione applica «unica rata». Non serve riempirlo per forza.
* **Il termine non è solo un dato anagrafico**: entra nei criteri con cui il
  lavoro si raggruppa, quindi cambiare il termine di un cliente può cambiare
  **quante fatture** riceverà. Il perché sta in
  [Termini di pagamento §4](/guide/termini-di-pagamento).

### 4. Dati catastali

I dati catastali (foglio, particella, subalterno, categoria, rendita) sono legati all'istanza tramite `catasto_unita_immobiliare_id`. Il collegamento tra catasto e indirizzo civico avviene tramite la tabella ponte `catasto_unita_immobiliari_indirizzi`, mantenuta in automatico dal trigger `trgfn_iu_sync_catasto_unita_indirizzo`.

Tre regole fondamentali del catasto:

* **Clone, mai condivisione**: nel subentro il catasto viene duplicato. Ogni istanza ha il proprio record indipendente, e un indice unico impedisce che due istanze nominino la stessa unità; modificare il catasto di un'istanza non tocca le altre
* **Sorgente unica**: la clonazione cerca il catasto solo nella parent istanza diretta (`parent_istanza_id`). Se il parent non ha catasto, il flusso prosegue senza errore
* **Tabella ponte**: il legame catasto ↔ indirizzo e N:M e viene creato automaticamente. La stessa unita catastale puo essere associata a piu indirizzi e viceversa

Per il flusso completo dei trigger di clonazione e tutti i dettagli: [Il catasto delle istanze](/guide/catasto-delle-istanze).

---

## Vincoli e regole di coerenza

### Regola fondamentale: un cliente per PDP in ogni giorno

Su ciascun PDP i periodi dei clienti non si sovrappongono: in un dato giorno il PDP ha **al massimo un cliente**. Lo impone il vincolo di esclusione `ex_clienti_no_overlap_stesso_pdp` su `(pdp_id, periodo)`. Un cliente annullato non ha periodo, e non conta.

**Attenzione**: il vincolo opera **per PDP**, non per indirizzo. Sullo stesso indirizzo possono coesistere clienti attivi di utility diverse. Esempio: un appartamento puo avere contemporaneamente un cliente GAS attivo e un cliente ENERGIA attivo, perche sono due PDP distinti.

### Multi-utility e soggetto con piu istanze

Sullo stesso civico possono coesistere clienti attivi di utility diverse (GAS + ENERGIA), ciascuno col proprio billing account, tutti collegati allo stesso soggetto e allo stesso ruolo CLIENTE. Con un PDP, ogni utility ha la sua istanza, perche l'istanza ha un solo `pdp_id`; senza PDP, la stessa istanza puo portare piu utility, un billing account e un cliente per ciascuna.

Per gli esempi dettagliati e le casistiche: [Guida Gestione Istanze Utility – Multi-utility](/guide/gestione-delle-istanze-utility#multi-utility-sullo-stesso-indirizzo).

### Altri vincoli

* Se `fittizia = FALSE`, allora `indirizzo_dettaglio_id` deve essere NOT NULL
* Se `pdp_id` e valorizzato, l'istanza non puo essere fittizia e deve avere l'indirizzo del PDP
* Ruolo e utility su `clienti` sono quelli del billing account: li copia il trigger, e un valore diverso viene rifiutato (`E_DOC_CLIENTE_DIVERSO_DA_BA`)
* Se il cliente ha un PDP, la utility del PDP e quella del billing account (`E_PDP_UTILITY_MISMATCH`); se la utility richiede il PDP, il PDP c'e (`E_PDP_OBBLIGATORIO`)
* Un cliente non puo esistere senza istanza e senza billing account

---

## L'emittente del cliente — si sceglie una volta

Il legame cliente → emittente nasce **qui**, automaticamente: non c'è nessun passaggio in cui si
sceglie, ed è il motivo per cui vale la pena saperlo prima di creare il primo cliente.

### Nasce da solo, e prende l'emittente di chi sta creando

Nel momento in cui il billing account viene creato, un trigger lo aggancia
all'**emittente dell'operatore corrente** o, senza un operatore in sessione
(un import, un processo notturno) o se l'operatore non ha un emittente,
all'**emittente predefinito**. Non c'è un passaggio in cui il cliente esiste
«senza emittente»: nasce già agganciato, e il collegamento non si toglie più.
Senza nessun emittente nell'installazione il billing account non nasce
(`E_EMITTENTE_DEFAULT_MISSING`). Chi crea il cliente con
`fn_crea_cliente` puo indicare l'emittente esplicitamente; se un operatore e in
sessione, l'emittente indicato deve essere il suo.

⚠️ **Conseguenza pratica da conoscere**: se l'operatore sta lavorando
sull'emittente sbagliato, il cliente **nasce sbagliato**. È un errore di
inserimento ordinario, e va corretto subito.

### Perché «subito» non è un modo di dire

Un documento già emesso porta con sé chi lo ha emesso, e **non lo cambia mai**.
Spostare il cliente su un altro emittente non riscrive quei documenti: li
lascia dove sono. Da quel momento chi li ha emessi continua a vedere i documenti
e **smette di vedere il cliente** a cui si riferiscono.

⇒ Per questo il legame si può cambiare, **modificando l'emittente sul
collegamento**, finché sul cliente non è passato **nessun documento**, di
qualunque famiglia e in qualunque stato, anche in bozza, e non più dopo. Chi ha
sbagliato emittente e ha già scritto documenti li cancella prima. Il controllo
che lo impone è
[`anagrafiche.fn_guard_ba_cambio_emittente`](/dbzero/anagrafiche/funzioni/fn_guard_ba_cambio_emittente),
e il messaggio che restituisce dice con quale emittente il cliente ha già
documenti, e quanti per famiglia. Spostare l'emittente predefinito non cambia
l'emittente di nessun cliente già nato.

### E se il cliente è passato davvero all'altro emittente?

Allora non si sposta: **si apre presso il nuovo emittente una fornitura nuova**.
I documenti già emessi restano con chi li ha emessi, il cliente resta lo stesso
soggetto, e le due posizioni convivono.

⚠️ Non esiste un «cliente gemello» sulla stessa fornitura, e non è una
dimenticanza: un indice univoco lo vieta — per una istanza e una utility c'è
**un** billing account e uno solo, e per un billing account **un** cliente.

### ⚠️ E l'albero dei clienti si muove tutto insieme

Padre e figli devono stare sullo **stesso** emittente. Agganciare un cliente a un
padre di un altro emittente, o spostare l'emittente di un solo nodo, viene
respinto: vedi
[`anagrafiche.fn_guard_albero_ba_emittente`](/dbzero/anagrafiche/funzioni/fn_guard_albero_ba_emittente).

---

## Trigger e funzioni coinvolte nella creazione

### Ordine di esecuzione (visione rapida)

Entro i trigger BEFORE e entro gli AFTER di una tabella, PostgreSQL li esegue in ordine
alfabetico di nome. I controlli **differiti** scattano alla conferma dell'operazione, dopo tutto
il resto, qualunque sia il loro nome.

```text
INSERT istanza
  BEFORE ├─ gen_codice            → genera il codice dell'istanza
         ├─ codice_maiuscolo
         ├─ audit + tx_id
         └─ normalize             → non fa niente
  AFTER  ├─ sync_catasto_indirizzo → legame catasto ↔ indirizzo
         └─ alla conferma         → soggetto e indirizzo attivi; l'istanza ha un BA
  │
INSERT billing_account
  BEFORE ├─ date_validita         → valido_al non prima di valido_dal
         ├─ gen_codice            → genera il codice dell'account
         ├─ guard_admin_globale   → chi crea ha un emittente su cui scrivere
         ├─ codice_maiuscolo
         ├─ guard_soggetto_istanza → il ruolo e del soggetto dell'istanza, ed e un ruolo cliente
         ├─ audit + tx_id
         └─ guard_normalize       → il padre: coerente, albero a un livello, un padre per cliente e azienda
  AFTER  ├─ link_ef               → collega il BA all'emittente dell'operatore, o al predefinito
         ├─ guard_albero_emittente → padre e figli sullo stesso emittente
         ├─ guard_istanza_emittente → i BA dell'istanza sono di un solo emittente
         └─ alla conferma         → la categoria cliente e attiva
  │
INSERT cliente
  BEFORE ├─ guard_stato_date      → lo stato e le sue date
         ├─ audit + tx_id
         ├─ guard_ruolo_cliente   → il ruolo e un ruolo cliente
         ├─ set_periodo           → periodo [attivazione, chiusura)
         ├─ sync_pdp              → pdp_id dall'istanza
         ├─ sync_utility_from_ba  → ruolo e utility dal BA; PDP obbligatorio e della stessa utility
         └─ set_parent_istanza    → catena dei subentri sull'istanza
  AFTER  ├─ sync_stato_pdp        → stato del PDP secondo l'occupazione
         └─ alla conferma         → PDP e termine di pagamento attivi; chiave unica del cliente manuale
```

Sulle modifiche si aggiungono, in testa ai BEFORE, i blocchi delle colonne che non cambiano
(il codice e il soggetto dell'istanza; codice, istanza, ruolo e utility del BA; la fornitura del
cliente) e, in coda, lo storico di `billing_account` e `clienti`. La cancellazione di un BA è
rifiutata prima di ogni altro trigger (`E_BA_NON_SI_CANCELLA`).

### Dettaglio completo

#### Sull'istanza (`anagrafiche.istanze_utilities`)

| Trigger / Funzione | Quando scatta | Cosa fa |
| --- | --- | --- |
| [`trgfn_istanze_utilities_gen_codice`](/dbzero/anagrafiche/funzioni/trgfn_istanze_utilities_gen_codice) | BEFORE INSERT, UPDATE OF `codice` | Genera il codice automatico dell'istanza |
| `script.trgfn_lock_columns` | BEFORE UPDATE OF `codice`, `soggetto_id` | Codice e soggetto non cambiano (`E_CODICE_NON_MODIFICABILE`, `E_ISTANZA_SOGGETTO_IMMUTABILE`) |
| [`trgfn_istanze_utilities_normalize`](/dbzero/anagrafiche/funzioni/trgfn_istanze_utilities_normalize) | BEFORE INSERT/UPDATE | Nessuna azione: restituisce la riga com'è |
| [`trgfn_iu_sync_catasto_unita_indirizzo`](/dbzero/anagrafiche/funzioni/trgfn_iu_sync_catasto_unita_indirizzo) | AFTER INSERT, UPDATE che cambia catasto o indirizzo | Mantiene il legame catasto ↔ indirizzo: al cambio toglie la coppia di prima e cancella l'unità che nessuno nomina più |
| [`trgfn_iu_clone_catasto_from_parent`](/dbzero/anagrafiche/funzioni/trgfn_iu_clone_catasto_from_parent) | AFTER INSERT con la parent, UPDATE che cambia `parent_istanza_id` | Clona il catasto della parent, se l'istanza non ne ha |
| [`trgfn_istanze_utilities_require_utility_dichiarata`](/dbzero/anagrafiche/funzioni/trgfn_istanze_utilities_require_utility_dichiarata) | AFTER INSERT, alla conferma | L'istanza ha almeno un billing account (`E_ISTANZA_SENZA_BA`) |

#### Sul billing account (`anagrafiche.billing_account`)

| Trigger / Funzione | Quando scatta | Cosa fa |
| --- | --- | --- |
| [`trgfn_billing_account_gen_codice`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_gen_codice) | BEFORE INSERT, UPDATE OF `codice` | Genera il codice dell'account |
| `script.trgfn_lock_columns` | BEFORE UPDATE OF codice, istanza, ruolo, utility | Codice e coppia istanza/utility non cambiano (`E_BA_ISTANZA_IMMUTABILE`) |
| [`script.trgfn_prevent_modification_generic`](/dbzero/script/funzioni/trgfn_prevent_modification_generic) (`trg_billing_account_a05_block_delete_dlt`) | BEFORE DELETE | Il BA non si cancella: il cliente si annulla (`E_BA_NON_SI_CANCELLA`) |
| [`trgfn_billing_account_guard_admin_globale`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_admin_globale) | BEFORE INSERT | Rifiuta la creazione a chi non ha un emittente su cui scrivere |
| [`trgfn_billing_account_guard_soggetto_coerenza_istanza`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_soggetto_coerenza_istanza) | BEFORE INSERT, UPDATE OF istanza o ruolo | Il ruolo è del soggetto dell'istanza, ed è un ruolo cliente |
| [`trgfn_billing_account_guard_normalize`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_normalize) | BEFORE INSERT/UPDATE | Il padre: non sé stesso, raggiungibile, dello stesso cliente; un livello solo e un padre per cliente e azienda ([`fn_check_ba_padre`](/dbzero/anagrafiche/funzioni/fn_check_ba_padre): `E_PARENT_CON_PADRE`, `E_PARENT_HA_FIGLI`, `E_PARENT_SECONDO_PADRE`); non si stacca né si cambia con attività da fatturare (`E_DISSOCIAZIONE_PARENT_CON_ATTIVITA`) |
| [`trgfn_billing_account_link_ef`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef) | AFTER INSERT | Collega il BA all'emittente dell'operatore corrente o, senza, al predefinito; senza nessun emittente il BA non nasce (`E_EMITTENTE_DEFAULT_MISSING`) |
| [`trgfn_billing_account_guard_albero_emittente`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_albero_emittente) | AFTER INSERT, UPDATE OF `parent_account_id` | Padre e figli sullo stesso emittente |
| [`trgfn_billing_account_guard_istanza_emittente`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_istanza_emittente) | AFTER INSERT | I BA di un'istanza sono di un solo emittente (`E_ISTANZA_EMITTENTI_DIVERSI`) |

#### Sul cliente (`anagrafiche.clienti`)

| Trigger / Funzione | Quando scatta | Cosa fa |
| --- | --- | --- |
| [`trgfn_clienti_guard_stato_date`](/dbzero/anagrafiche/funzioni/trgfn_clienti_guard_stato_date) | BEFORE INSERT/UPDATE | Il cambio di stato segue il percorso; ogni stato ha la sua data; la chiusura di un chiuso non cambia |
| `script.trgfn_lock_columns` | BEFORE UPDATE OF BA, istanza, ruolo, utility | La fornitura del cliente non cambia (`E_CLIENTE_FORNITURA_IMMUTABILE`) |
| [`trgfn_clienti_guard_ruolo_cliente`](/dbzero/anagrafiche/funzioni/trgfn_clienti_guard_ruolo_cliente) | BEFORE INSERT/UPDATE | Il ruolo del cliente è un ruolo CLIENTE |
| [`trgfn_clienti_set_periodo`](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_periodo) | BEFORE INSERT/UPDATE | Calcola `periodo` = `[data_attivazione, data_chiusura)`; un annullato non ha date né periodo |
| [`trgfn_clienti_sync_pdp`](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_pdp) | BEFORE INSERT/UPDATE | Copia `pdp_id` dall'istanza |
| [`trgfn_clienti_sync_utility_from_ba`](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_utility_from_ba) | BEFORE INSERT/UPDATE | Ruolo e utility dal BA (via [`script.fn_cliente_dal_billing_account`](/dbzero/script/funzioni/fn_cliente_dal_billing_account)); PDP obbligatorio se la utility lo richiede, e della stessa utility |
| [`trgfn_clienti_set_parent_istanza`](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_parent_istanza) | BEFORE INSERT, UPDATE OF `pdp_id`, `data_attivazione`, con data di attivazione | Scrive `parent_istanza_id` sull'istanza del cliente |
| [`trgfn_clienti_sync_stato_pdp`](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_stato_pdp) | AFTER INSERT, UPDATE OF stato, PDP, date | Ricalcola lo stato del PDP del cliente, e di quello lasciato, secondo l'occupazione di oggi ([`fn_check_pdp_occupato`](/dbzero/anagrafiche/funzioni/fn_check_pdp_occupato)) |
| `dbops.trgfn_child_requires_active_parent` | AFTER INSERT/UPDATE, alla conferma | Il PDP e il termine di pagamento del cliente sono attivi |
| [`trgfn_clienti_guard_chiave_unica`](/dbzero/anagrafiche/funzioni/trgfn_clienti_guard_chiave_unica) | AFTER INSERT/UPDATE, alla conferma | Un cliente manuale per soggetto, servizio e azienda (`E_CLIENTE_STESSA_CHIAVE`) |

#### Comuni alle tre tabelle

| Trigger / Funzione | Quando scatta | Cosa fa |
| --- | --- | --- |
| [`dbops.trgfn_tx_id_managed`](/dbzero/dbops/funzioni/trgfn_tx_id_managed) | BEFORE INSERT/UPDATE | Genera `tx_id` per tracciabilita transazionale |
| [`script.trgfn_audit_data_user_generic`](/dbzero/script/funzioni/trgfn_audit_data_user_generic) | BEFORE INSERT/UPDATE | Aggiorna i campi audit (`data_update`, `user_update`) |
| [`script.trgfn_storico_generic`](/dbzero/script/funzioni/trgfn_storico_generic) | BEFORE UPDATE/DELETE su `billing_account` e `clienti` | Snapshot storico del record modificato; l'istanza non ha storico |

---

## Garanzia transazionale

Tutte le operazioni descritte in questa guida (creazione istanza, BA, cliente, e i trigger che scattano in cascata) avvengono all'interno di una **singola transazione PostgreSQL**.

Cosa significa in pratica:

* Se un qualsiasi trigger della catena fallisce (es. vincolo violato, dato mancante), **tutte le operazioni vengono annullate** (rollback atomico)
* **Non esistono stati parziali**: o tutto va a buon fine, o nulla viene modificato
* Questo vale anche per le catene del subentro, dove un trigger su `clienti` scrive sull'istanza e fa scattare quelli dell'istanza
* I controlli differiti parlano alla conferma: dentro la transazione l'ordine delle scritture e libero, alla fine la regola deve valere

Questa garanzia e offerta nativamente dal motore PostgreSQL e non richiede codice aggiuntivo.

---

## Appendice – Subentro cliente

Il **subentro** (o voltura) e il passaggio di titolarita su un PDP: un cliente esce, un altro entra sullo stesso punto di prelievo.

### Cosa fa `fn_subentro_cliente`

La funzione [`script.fn_subentro_cliente`](/dbzero/script/funzioni/fn_subentro_cliente) si occupa **esclusivamente della chiusura del cliente precedente**: una chiamata con il punto di prelievo e la data di attivazione del nuovo ([esempio](#area-tecnica-esempi)).

Effetti:

* Individua il cliente piu recente sul PDP che non e annullato, e stato attivato prima della nuova data e ha il periodo ancora aperto a quella data
* Imposta `data_chiusura = p_data_attivazione - 1 giorno`
* Imposta lo stato **CH** (chiuso); se la chiusura e ammessa dallo stato in cui il cliente si trova lo decide il guard degli stati
* Se non esiste alcun cliente da chiudere → ritorna NULL (prima attivazione)
* I trigger aggiornano in automatico il `periodo` e lo stato del PDP

> ⚠️ **Il giorno prima del subentro il PDP resta senza cliente.** La funzione chiude il
> precedente al giorno prima dell'attivazione nuova, e il `periodo` calcolato da
> [`trgfn_clienti_set_periodo`](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_periodo) esclude
> il giorno di chiusura: il periodo del precedente finisce cosi due giorni prima del nuovo, non
> uno. I commenti delle colonne `data_chiusura` e `periodo` descrivono invece la chiusura come
> inclusiva, e la disdetta scrive la data di cessazione cosi com'e. Le due letture della data di
> chiusura non coincidono.

**La funzione non crea** la nuova istanza, il nuovo billing account e il nuovo cliente. Questi passi sono a carico del chiamante. La sequenza completa e:

1. `fn_subentro_cliente(pdp_id, data)` → chiude il precedente
2. istanza reale sullo stesso PDP → billing account e cliente (con `fn_crea_cliente`, indicando l'istanza) → attiva il nuovo

Tutti questi passi vanno eseguiti nella stessa transazione.

### Catena trigger del subentro

Quando si crea un nuovo cliente sullo stesso PDP dopo la chiusura del precedente, scatta una catena di trigger:

**Passo 1** — `trgfn_clienti_set_parent_istanza` (BEFORE INSERT su clienti, se c'e la data di attivazione)
Cerca il cliente precedente sullo stesso PDP (non annullato, attivato non dopo il nuovo) e scrive la sua istanza in `parent_istanza_id` sulla nuova istanza. Su un'istanza fittizia, senza PDP, il predecessore e l'ultimo cliente con lo stesso soggetto, servizio e azienda. Questo mantiene la catena storica dei subentri.

**Passo 2** — `trgfn_iu_clone_catasto_from_parent` (AFTER INSERT con la precedente, o UPDATE che cambia `parent_istanza_id`, su istanze)
Quando nasce il legame con l'istanza precedente, la nuova istanza ha un indirizzo e non ha ancora un catasto, clona i dati catastali dall'istanza precedente. Il catasto non e mai condiviso: viene sempre duplicato.

**Passo 3** — `trgfn_iu_sync_catasto_unita_indirizzo` (AFTER INSERT/UPDATE su istanze)
Inserisce automaticamente il legame tra il catasto clonato e l'indirizzo nella tabella ponte `catasto_unita_immobiliari_indirizzi`.

**Passo 4** — `trgfn_clienti_sync_stato_pdp` (AFTER INSERT/UPDATE su clienti)
Ricalcola lo stato del PDP: se oggi un cliente lo occupa e il PDP e disponibile, diventa attivo.

Tutti questi trigger avvengono nella stessa transazione. Se uno fallisce, tutto viene annullato (vedi sezione "Garanzia transazionale").

### Funzioni e trigger coinvolti nel subentro

* [`anagrafiche.trgfn_clienti_set_parent_istanza`](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_parent_istanza)
* [`anagrafiche.trgfn_iu_clone_catasto_from_parent`](/dbzero/anagrafiche/funzioni/trgfn_iu_clone_catasto_from_parent)
* [`anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo`](/dbzero/anagrafiche/funzioni/trgfn_iu_sync_catasto_unita_indirizzo)
* [`anagrafiche.trgfn_clienti_sync_stato_pdp`](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_stato_pdp)
* [`script.fn_subentro_cliente`](/dbzero/script/funzioni/fn_subentro_cliente)
* [`script.fn_get_catasto_source_by_istanza`](/dbzero/script/funzioni/fn_get_catasto_source_by_istanza)
* [`script.fn_clone_catasto_from_parent_by_istanza`](/dbzero/script/funzioni/fn_clone_catasto_from_parent_by_istanza)

---

## Appendice – Disdetta (cessazione senza subentro)

La **disdetta** e la chiusura del servizio senza che un nuovo intestatario subentri. Il cliente disdice, il PDP torna disponibile per future attivazioni.

### Cosa fa `fn_disdetta_cliente`

La funzione [`script.fn_disdetta_cliente`](/dbzero/script/funzioni/fn_disdetta_cliente) incapsula la cessazione ([esempio](#area-tecnica-esempi)).

Effetti:

* Verifica che `p_data_cessazione >= data_attivazione` del cliente
* Da quale stato si può chiudere lo decide il percorso degli stati del cliente: attivo e sospeso
  sì, un cliente già chiuso, annullato o pre-contrattuale no ([Gli stati del cliente](/guide/gestione-delle-istanze-utility#gli-stati-del-cliente-e-le-loro-date))
* Imposta `data_chiusura = p_data_cessazione`
* Imposta `stato_cliente = CH` (chiuso)
* Ritorna l'`id` del cliente chiuso

I trigger si occupano automaticamente di:

* Ricalcolare il `periodo` commerciale → `[data_attivazione, data_cessazione)`
* Aggiornare lo stato PDP → **disponibile**, se oggi nessun altro cliente lo occupa
* Storicizzare il record e aggiornare i campi audit

⚠️ Lo stato del PDP si ricalcola quando si scrive il cliente: una cessazione con data futura
libera il PDP alla prossima scrittura del cliente, non il giorno della cessazione.

### Policy sul billing account dopo la disdetta

Il billing account **non viene toccato** dalla disdetta, e non si cancella mai. Resta attivo per consentire:

* Emissione di fatture finali
* Conguagli e riconciliazioni

Il billing account di un cliente chiuso **non si riattiva**: un cliente chiuso non si riapre.
Se la fornitura riparte, nasce una catena nuova — istanza, billing account e cliente nuovi,
collegata alla precedente — come nel subentro. Vedi
[Gestione delle istanze utility — Chiusura del cliente](/guide/gestione-delle-istanze-utility#5-chiusura-del-cliente).

La chiusura del billing account (tramite `valido_al`) e un'operazione separata, da eseguire solo quando tutti i documenti fiscali sono stati emessi e le partite aperte sono chiuse.

### Cosa succede all'istanza dopo la disdetta

L'istanza non ha un campo "stato" proprio. La sua "chiusura" e implicita: quando i suoi clienti — uno per billing account, cioe uno per utility — sono chiusi, l'istanza e considerata storica. Resta nel database come record per:

* Tracciabilita delle precedenti attivazioni
* Riferimento per eventuali futuri subentri sullo stesso PDP
* Base per la catena `parent_istanza_id`

### Differenza tra subentro e disdetta

|              | Subentro                                                             | Disdetta                                         |
| ------------ | -------------------------------------------------------------------- | ------------------------------------------------ |
| Cosa succede | Un cliente esce, un altro entra                                      | Il cliente esce, nessuno entra                   |
| PDP dopo     | Resta attivo, se il nuovo cliente lo occupa gia oggi                 | Torna disponibile, se oggi nessuno lo occupa     |
| Funzione DB  | `fn_subentro_cliente` (chiude il precedente) + creazione nuovo ciclo | `fn_disdetta_cliente` (solo chiusura)            |
| BA           | Nuovo BA per il nuovo intestatario                                   | BA resta attivo per fatture finali               |
| Istanza      | Nuova istanza con `parent_istanza_id`                                | L'istanza resta come record storico              |

---

## Diagramma ER

````mermaid
%%{init: {'er': {'layoutDirection': 'TB'}}}%%
erDiagram

%% Relazioni principali per la generazione di un cliente

    soggetti                  ||--o{ soggetti_ruoli    : ha
    tipi_ruoli                ||--o{ soggetti_ruoli    : classifica

    soggetti_ruoli            ||--o{ billing_account   : fatturato_a
    soggetti_ruoli            ||--o{ clienti           : come_cliente

    soggetti                  ||--o{ istanze_utilities : ha

    istanze_utilities         ||--o{ billing_account   : genera
    istanze_utilities         ||--o{ clienti           : assegnato_a
    istanze_utilities         |o--o{ istanze_utilities : parent_di
    catasto_unita_immobiliari |o--o{ istanze_utilities : descrive

    utilities                 ||--o{ billing_account   : per
    utilities                 ||--o{ clienti           : ha
    utilities                 ||--o{ pdp               : tipo_di
    stati_cliente             ||--o{ clienti           : stato
    stati_pdp                 ||--o{ pdp               : stato

    billing_account           ||--o| clienti           : fattura
    billing_account           |o--o{ billing_account   : padre_di

    pdp                       |o--o{ istanze_utilities : collegato_a
    pdp                       |o--o{ clienti           : occupato_da

    indirizzi_dettaglio       |o--o{ istanze_utilities : opzionale_per
    indirizzi_dettaglio       ||--o{ pdp               : situato_a
    indirizzi_dettaglio       ||--o{ indirizzi         : normalizzato_da
````

## Area tecnica — esempi

**Chiudere il cliente precedente su un punto di prelievo (subentro)** — la funzione non crea il nuovo
cliente: chiude il vecchio, lasciando il punto libero per il subentrante:

```sql
SELECT script.fn_subentro_cliente(p_pdp_id, p_data_attivazione_nuovo);
```

**Cessare il servizio senza subentro (disdetta)** — il punto di prelievo torna disponibile per future
attivazioni:

```sql
SELECT script.fn_disdetta_cliente(p_cliente_id, p_data_cessazione);
```

---

{% include-markdown "signature-core.md" %}
