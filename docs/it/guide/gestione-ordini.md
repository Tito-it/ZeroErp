# Guida — Gestione Ordini di vendita

> **Ultimo aggiornamento**: 3 novembre 2026
>
> **Destinatari**: analisti funzionali, operatori commerciali, sviluppatori
> backend/frontend, DBA.
>
> **Vedi anche** — schemi DB:
>
> * [vendite.ordini](/dbzero/vendite/tabelle/ordini) / [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe) / [vendite.ordini_righe_componenti](/dbzero/vendite/tabelle/ordini_righe_componenti)
> * [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment) / [vendite.ordini_indirizzi](/dbzero/vendite/tabelle/ordini_indirizzi) / [vendite.note_ordini](/dbzero/vendite/tabelle/note_ordini)
> * [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini) / [config.transizioni_stati_ordini](/dbzero/config/tabelle/transizioni_stati_ordini)
> * [vendite.vw_ordini_lista](/dbzero/vendite/manual/vw_ordini_lista) / [vendite.vw_ordini_riepilogo_iva_dettaglio](/dbzero/vendite/manual/vw_ordini_riepilogo_iva_dettaglio)
> * [vendite.vw_situazione_merce_ordine](/dbzero/vendite/manual/vw_situazione_merce_ordine) — per riga: ordinato, spedito, reso, fatturato, residuo e **ritardo**
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — BoM versionata immutabile
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [script.fn_available_actions_ordine](/dbzero/script/funzioni/fn_available_actions_ordine) — azioni disponibili sullo stato corrente
> * [vendite.trgfn_ordini_guard_transizione](/dbzero/vendite/funzioni/trgfn_ordini_guard_transizione) — enforcement del grafo stati + precondizione "≥1 riga" sulla conferma
> * [vendite.fn_push_preventivo_a_ordine](/dbzero/vendite/funzioni/fn_push_preventivo_a_ordine) — smistamento delle righe merce del preventivo verso un ordine
> * [vendite.fn_offerta_righe_espanse](/dbzero/vendite/funzioni/fn_offerta_righe_espanse) — espansione delle righe dell'offerta in fase di conversione
> * [vendite.fn_ordine_riga_componenti_init](/dbzero/vendite/funzioni/fn_ordine_riga_componenti_init) / [vendite.fn_ordine_riga_componenti_preview](/dbzero/vendite/funzioni/fn_ordine_riga_componenti_preview) — componenti BoM (creazione / anteprima)
> * [vendite.fn_list_ordini_da_pushare](/dbzero/vendite/funzioni/fn_list_ordini_da_pushare) — righe eleggibili al push a commessa
> * [vendite.fn_ricalcola_totali_ordine](/dbzero/vendite/funzioni/fn_ricalcola_totali_ordine) — totali di testata e riepilogo IVA per aliquota
> * [vendite.trgfn_ordini_gen_numero](/dbzero/vendite/funzioni/trgfn_ordini_gen_numero) — numero ordine auto-generato e immutabile
> * [script.trgfn_default_emittente_fiscale](/dbzero/script/funzioni/trgfn_default_emittente_fiscale) / [script.trgfn_doc_guard_emittente_ba](/dbzero/script/manual/trgfn_doc_guard_emittente_ba) — emittente fiscale di default (il building block unico, dal 2026-09-15) e coerenza con il cliente
>
> **Vedi anche** — API e service backend:
>
> * [API Ordini](/backend/vendite/manual/api_ordini)
> * [API Preventivi](/backend/vendite/manual/api_preventivi) — conversione preventivo → ordine (§6c smistamento)
> * [API Offerte](/backend/vendite/manual/api_offerte) — conversione offerta → ordine
> * [API Pricing (resolver + limiti L2)](/backend/vendite/manual/api_pricing)
> * [API Situazione merce](/backend/vendite/manual/api_situazione_merce) — il pannello «quanto è uscito, tornato, fatturato, cosa resta», con le date di consegna e il ritardo per riga
>
> **Vedi anche** — guide correlate:
>
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — **le regole comuni a tutti i documenti**: nascita, cambio di stato, permesso sul passaggio, emissione, annullo
> * [Gestione Preventivi](/guide/gestione-preventivi) — la sorgente principale dell'ordine (split per natura)
> * [Gestione Offerte commerciali](/guide/gestione-offerte-commerciali) — l'altra sorgente (1:1, XOR contratto)
> * [Gestione Contratti](/guide/gestione-contratti) — il "gemello ricorrente": l'offerta genera contratto **oppure** ordine, mai entrambi
> * [Gestione DDT](/guide/gestione-ddt) — il documento di consegna: l'ordine confermato si **evade** in uno o più DDT (residuo per riga)
> * [Gestione Commesse](/guide/gestione-commesse) — la destinazione del push (attività fatturabili)
> * [Fatturazione end-to-end](/guide/fatturazione) — il push a commessa avvia la pipeline di fatturazione
> * [Numerazione dei documenti e codici](/guide/numerazione-documenti-e-codici) — **il motore che assegna il numero**: è lo stesso di DDT, fatture, resi e commesse
> * [Il risolutore IVA di riga](/guide/iva-risolutore-di-riga) — **la sede unica** che decide il codice IVA di una riga
> * [Documenti e stampe](/guide/documenti-e-stampe) — generazione del PDF di conferma d'ordine
> * [Gestione Listini e Pricing v5](/guide/gestione-listini) — risoluzione dei prezzi

---

## 1. Cosa è un ordine di vendita

Un ordine di vendita è il **documento operativo** del ciclo attivo: raccoglie le
righe articolo che l'azienda si è impegnata a **consegnare e fatturare** a un
cliente. Risponde alla domanda: *"Cosa consegniamo e fatturiamo a questo cliente,
in quali quantità e a quali prezzi?"*

A differenza di preventivo e offerta — che sono **proposte** (un "se accettassi…")
— l'ordine è un **impegno confermato**. È il punto in cui la trattativa diventa
lavoro da svolgere: una volta confermato, l'ordine alimenta la **commessa** che a
sua volta apre la pipeline di fatturazione.

Caratteristiche di base:

- è intestato a un **cliente** (billing account, con il relativo soggetto) e,
  facoltativamente, a una **utility** (Gas, Energia, Idrico, oppure "Base" per il
  commercio)
- raccoglie **righe** (articolo, quantità, prezzo, IVA) ed eventuali **componenti
  BoM** per gli articoli compositi
- ha un **ciclo di vita** semplice: bozza → confermato → evaso, in parte o del tutto,
  man mano che la merce parte con le bolle (oppure annullato)
- nasce quasi sempre per **conversione** da un preventivo accettato o da un'offerta
  accettata, ma può anche essere creato a mano
- alla conferma può produrre il **PDF di conferma d'ordine**
- una volta confermato viene **spinto in commessa** (push), che lo collega alla
  fatturazione

Il numero documento è auto-generato (trigger `trgfn_ordini_gen_numero`) ed è
**immutabile**: viene assegnato già alla nascita della bozza e non si modifica più.

> ⭐ **Il numero non se lo fabbrica l'ordine.** Il trigger è solo il *momento* in
> cui l'ordine chiede il numero — alla nascita, a differenza del DDT che lo chiede
> all'emissione. A produrlo è il **motore dei registri**, lo stesso che numera
> DDT, fatture, resi e commesse: progressione per azienda emittente, reset
> annuale, forma (prefisso, cifre, serie) presa dal registro. Come funziona, e
> perché non è il catalogo dei formati usato per i codici cliente, sta nella guida
> [Numerazione dei documenti e codici](/guide/numerazione-documenti-e-codici).

> **Differenza chiave con preventivo/offerta.** L'ordine **non ha revisioni** e
> **non ha un listino in testata**: i prezzi delle righe sono già "fotografati"
> (arrivano dalla trattativa a monte o vengono inseriti a mano). Mentre il
> preventivo si "revisiona" finché non è accettato, l'ordine, se va corretto,
> finché è in bozza si modifica liberamente; dopo la conferma è bloccato.

---

## 2. Dove si colloca nel flusso commerciale

L'ordine è il passaggio dalla **proposta** alla **operatività**. Le due sorgenti
naturali sono il preventivo e l'offerta, con due logiche diverse di conversione.

```text
                       ┌──────────────────────────┐
   PREVENTIVO ACCETTATO │ smistamento per riga     │
   (articoli "una tantum)│  → solo le righe MERCE   │── 1:N ──┐
                       └──────────────────────────┘         │
                                                             ▼
   OFFERTA ACCETTATA   ┌──────────────────────────┐    ┌────────────┐  push   ┌──────────┐
   (condizioni in blocco)│ conversione 1:1 in blocco │──▶│   ORDINE   │────────▶│ COMMESSA │──▶ Fattura
                       │  XOR contratto            │    │  DRAFT →   │         │ (attività│
                       └──────────────────────────┘    │ CONFERMATO │         │ fatturab.)│
                                                        │  → EVASO   │         └──────────┘
                                                        └────────────┘
   CREAZIONE MANUALE ──────────────────────────────────────▲
   (ordine "diretto")
```

### 2.1 Dal preventivo: smistamento per riga (1:N)

Un preventivo raccoglie articoli di **natura mista**. Quando viene accettato, le
sue righe non finiscono tutte nello stesso posto:

- le righe di **merce** (natura con destinazione `ORDINE_VENDITA`) vengono **smistate in un
  ordine di vendita**;
- i **servizi una tantum** vanno invece in **commessa** (push commessa);
- i **servizi ricorrenti** non possono nemmeno stare su un preventivo: si gestiscono
  con un'offerta che genera un contratto (vedi [Gestione Offerte §1.2](/guide/gestione-offerte-commerciali)).

Lo smistamento è **riga-per-riga e selettivo**: l'operatore, dal *Pannello
Smistamento* del preventivo, sceglie quali righe merce mandare a ordine. Per questo
il legame preventivo → ordine è **1:N**: dallo stesso preventivo possono nascere
più ordini (per esempio consegne in momenti diversi). Ogni riga di preventivo,
però, può essere smistata **una sola volta** (idempotenza di riga): se si riprova a
smistare una riga già allocata, viene semplicemente saltata.

> Quando non resta più nulla da smistare su **nessun** ramo (né merce né servizi),
> il preventivo passa automaticamente da ACCETTATO a **EVASO** (gate EVASO).

### 2.2 Dall'offerta: conversione 1:1, in alternativa al contratto

L'offerta commerciale propone **condizioni in blocco**. Quando viene convertita in
ordine, l'ordine eredita **tutte** le righe dell'offerta in una volta sola: il
legame è **1:1**. Una stessa offerta genera **al massimo un ordine**: un secondo
tentativo viene rifiutato (`E_ORD_OFFERTA_GIA_CONVERTITA`).

C'è di più: un'offerta accettata può diventare **o** un contratto (fornitura
ricorrente) **o** un ordine (vendita una tantum), **mai tutti e due**. È la regola
di **mutua esclusività** offerta → (contratto XOR ordine): la prima conversione
"consuma" l'offerta verso una delle due strade, finché quel documento non viene annullato.

La conversione la fa il database in un passo solo
([vendite.fn_genera_ordine_da_offerta](/dbzero/vendite/funzioni/fn_genera_ordine_da_offerta)),
e prima di scrivere controlla che ogni riga dell'offerta possa stare in un ordine: un
ordine contiene **solo merce** (più gli oneri che l'operatore aggiunge sull'ordine, §3.6), quindi un'offerta di servizi non si converte
(`E_DOC_RIGA_NON_AMMESSA`, che nomina l'articolo; il pulsante è spento con lo stesso motivo).

### 2.3 Creazione manuale

È sempre possibile creare un ordine **da zero**, scegliendo cliente e righe a mano.
In questo caso l'ordine nasce senza riferimento a un documento di origine.

---

## 3. Le entità in gioco

### 3.1 Testata `ordini`

Contiene il contesto del documento:

- **chi** (`billing_account_id` + `soggetto_ruolo_id`) — il cliente. Se si indica il
  billing account, il soggetto viene derivato da sé.
- **chi emette** (`emittente_fiscale_id`) — l'emittente fiscale; se omesso lo
  imposta un trigger (vedi §7).
- **per cosa** (`utility_id`) — opzionale.
- **quando** (`data`) — default alla data odierna.
- **come si paga** (`modalita_pagamento_id`, `termine_pagamento_id`, `valuta_id`,
  `tasso_cambio`).
- **quando fatturare** (`fatturazione_trigger`: `CONFERMATO` | `SPEDITO` |
  `CONSEGNATO`) — governa il *momento* del push a commessa. Il default è ereditato
  dal cliente; oggi il valore operativo è `CONFERMATO`.
- **da dove arriva** (`canale_origine`: `ADMIN` | `PORTALE` | `SHOP`) — in
  back-office è sempre `ADMIN` e non si cambia.
- **chi ha venduto** (`agente_soggetto_ruolo_id`) — agente/venditore, opzionale.
- **origine documentale** (`documento_origine_tipo` ∈ {`PREVENTIVO`, `OFFERTA_COMMERCIALE`},
  codici di `config.sorgenti`, + `documento_origine_id`) — valorizzata in automatico dalla conversione; NULL se
  l'ordine è creato a mano.
- **identità e stato** (`numero`/`serie`/`anno`, `uid`, `stato_doc_ordine_id`) e i
  **totali** (`imponibile_tot`, `iva_tot`, `totale_doc`), tenuti aggiornati dai
  trigger.

> ⚠️ **Il termine di pagamento non è solo un dato di testata: decide anche
> quante fatture nascono.** Le condizioni di pagamento fanno parte dei criteri
> con cui il lavoro si raggruppa a valle: un ordine con un termine diverso
> **non riusa la commessa** degli altri documenti dello stesso cliente, ne apre
> una nuova, e a fine mese produce una **fattura separata**. Non è un difetto —
> una fattura sola non potrebbe portare due scadenzari — ma va saputo: se ci si
> aspettava un documento solo e ne arrivano due, la prima cosa da guardare è il
> termine sui documenti di partenza.
> Dettaglio in [Termini di pagamento §4](/guide/termini-di-pagamento).

### 3.2 Righe `ordini_righe`

Ogni riga è una voce da consegnare/fatturare:

- **articolo** (`articolo_id`) e **descrizione**
- **quantità** in doppia unità: quella **operativa** scelta dall'operatore
  (`qta_operativa` + `uom_operativa_id`) e quella **base** (`quantita`) calcolata
  automaticamente dal fattore di conversione (`factor_to_base`)
- **prezzo** (`prezzo_unitario`), **sconto** percentuale, **IVA** (`iva_id`)
- **`attivo`** — una riga disattivata non concorre ai totali
- **`preventivo_riga_id`** — il legame con la riga del preventivo da cui è nata
  (presente solo per gli ordini da smistamento); è ciò che garantisce
  l'idempotenza di riga.
- **le due date di consegna** — `data_consegna_richiesta_cliente` (quando il
  cliente la vuole) e `data_consegna_confermata` (quando **noi** ci impegniamo a
  darla). Vedi §3.5.

Vincoli per l'operatore: **quantità > 0** e **prezzo ≥ 0** (un omaggio è quantità
positiva con prezzo zero).

**Quali articoli ammette**: la **merce** e gli **articoli-onere** (trasporto, urgenza, spese…:
gli addebiti che accompagnano la merce, §3.6), mai un articolo **«solo componente»**, che si vende
soltanto dentro il kit che lo contiene. Un altro servizio non entra: uno una tantum va in commessa,
uno ricorrente in contratto (tramite un'offerta). La merce è giudicata
dalla **natura con cui la riga è stata venduta**: una riga nata da un preventivo porta la natura di lì, anche
se nel frattempo l'articolo è cambiato in anagrafica. Il controllo è uno solo per tutti i
documenti ([`script.fn_check_articolo_riga`](/dbzero/script/manual/fn_check_articolo_riga)), e
il messaggio dice perché e dove va invece l'articolo. Un **kit senza componenti** (dal 2026-10-14) non si mette in nessuna riga: va prima completata la sua distinta.

**Nella ricerca dell'articolo** trovi prima quelli che la riga può usare. Gli altri compaiono dopo, in grigio, col motivo sotto, e non si possono scegliere: chi cerca un codice preciso e non lo trova fra i primi vede perché. La ricerca e il rifiuto al salvataggio usano la stessa regola, quindi un articolo proposto non viene rifiutato dopo.

### 3.3 Componenti BoM `ordini_righe_componenti`

Quando una riga punta a un **articolo composito** (distinta base), il sistema
genera in automatico un componente per ogni pezzo della BoM. Come nel resto della
famiglia vendite, il prezzo del padre è la **somma pesata** dei figli e non si
inserisce a mano. La composizione (quali componenti, in quali proporzioni) è
**immutabile**: si possono cambiare i prezzi, non i pezzi.

### 3.4 Note `note_ordini`

L'ordine supporta le **note partizionate** (di testata o di singola riga), con lo
stesso comportamento di preventivi, offerte e contratti.

> `ordini_indirizzi` alimenta la sezione indirizzi del documento, e
> `ordini_righe_fulfillment` registra l'**evasione** dell'ordine in uno o più
> **DDT** (residuo per riga, append-only). Vedi [Gestione DDT](/guide/gestione-ddt).

### 3.5 Le date di consegna, e il ritardo

Le date di consegna stanno **sulla riga**, non sulla testata: una riga può
essere pronta e un'altra no («il pezzo grosso arriva a marzo, il resto subito»).
Sono due, e la differenza fra loro *è* la promessa:

| Colonna | Che cosa dice | Chi la esprime |
|---|---|---|
| `data_consegna_richiesta_cliente` | quando il cliente la vuole | il cliente |
| `data_consegna_confermata` | quando ci impegniamo a darla | **noi** |

La convenzione dei nomi è quella di `numero` / `numero_fornitore`: *non marcato
= nostro, marcato = della controparte*. Sull'ordine d'acquisto vale ribaltata
(`data_consegna_richiesta` la chiediamo noi, `data_consegna_confermata_fornitore`
la conferma lui).

Entrambe sono **facoltative** e si scrivono con la riga (in `DRAFT`); nel form
di riga sono due selettori di data, e la tabella delle righe le mostra in due
colonne. Una data malformata è un errore di validazione sul campo, non un
errore del database.

⛔ **Nessun vincolo fra le due date, ed è una scelta**: si può confermare
*prima* di quanto chiesto, ed è una buona notizia.

⛔ **Una consegna non viene prima dell'ordine.** Nessuna delle due date può
essere anteriore alla data dell'ordine: dal form di riga e da «Aggiorna date di
consegna» una data così si rifiuta, e il messaggio dice la data dell'ordine. La
stessa data dell'ordine va bene (consegna in giornata), e il campo vuoto pure.
Vale anche al contrario: la data dell'ordine non si sposta *dopo* una consegna
già scritta su una riga, e il messaggio dice qual è la prima. Le righe
disattivate non contano. La retrodatazione resta possibile: si retrodata
l'ordine, e le consegne vengono dopo.

⛔ **Nessuna colonna di testata.** La data «dell'ordine» è il minimo delle
richieste sulle righe attive, e una colonna sarebbe una seconda verità che va
fuori sincrono al primo cambio di riga. Dove serve — la lista ordini — la
espone la vista (`data_consegna_richiesta_cliente_min`, §11).

**Da dove arriva.** Se l'ordine nasce dallo smistamento di un preventivo, la
data richiesta dal cliente **viaggia con la riga** (`fn_push_preventivo_a_ordine`
la porta avanti); la confermata nasce vuota, perché sul preventivo non c'era
niente da confermare.

> **Esempio.** Un preventivo chiede la consegna per il 5 ottobre, e diventa un
> ordine il 10. Quella richiesta è già passata: la riga d'ordine nasce **senza
> data richiesta**, e l'operatore la riscrive sull'ordine, che è in bozza. La
> richiesta originale resta sulla riga del preventivo. Non si inventa una data
> che il cliente non ha chiesto, e lo smistamento non si ferma.

**Il ritardo.** Lo calcola il pannello *Situazione merce* dell'ordine
(`vw_situazione_merce_ordine`, colonna `giorni_ritardo`), e sta lì e non altrove
perché il ritardo non è «oggi > data richiesta»: è «oggi > data di riferimento
**e** resta merce da spedire», e il residuo con la soglia dell'impegno vive già
in quella vista. La data di riferimento è la **promessa** se c'è, altrimenti la
richiesta del cliente. Tre valori, e non si appiattiscono:

| `giorni_ritardo` | Significato |
|---|---|
| vuoto | il conto non si applica: niente da spedire, oppure nessuna data dichiarata |
| `0` | c'è da spedire e **non** è tardi |
| `N > 0` | giorni di ritardo |

Nel pannello la colonna «Ritardo» è un'etichetta: verde «In tempo» sullo zero,
rossa «N gg di ritardo» sopra.

**La promessa dopo la conferma.** Le righe si modificano solo in `DRAFT`, ma
la promessa si decide alla conferma e può cambiare dopo. Per questo la **data
confermata** è l'unica colonna di riga che si scrive anche in `CONFERMATO` e
`PARZIALMENTE_EVASO`: dal menu della riga, «Cambia la data di consegna
confermata». Il campo vuoto toglie la promessa.

⛔ **Una riga già spedita tiene la sua data.** Basta un DDT uscito dalla bozza,
anche per una parte della quantità: da quel momento la data confermata della
riga è quella con cui la merce è partita, e l'azione della riga è spenta col
motivo. Se il DDT era un errore, annullarlo: la riga torna libera. Se la
consegna è slittata, si annota nelle note dell'ordine.

#### Aggiornare le date in blocco

Un ordine che si consegna tutto insieme vuole la stessa data su tutte le righe.
L'azione **«Aggiorna date di consegna»**, nella barra del drawer, chiede:

- **quale data** — la richiesta dal cliente o la confermata, fra quelle che in
  quel momento si possono scrivere. In `DRAFT` tutte e due; dopo la conferma la
  sola confermata, e l'azione si spegne col motivo quando l'ordine è in uno
  stato che non la ammette;
- **la data**;
- **su quali righe** — *solo quelle senza data*, oppure *tutte*, che
  sovrascrive anche le date già scritte. Con «tutte» si vede prima quante righe
  verranno toccate, e si conferma.

Le righe già spedite si **saltano**: la data confermata resta quella con cui
sono partite, e il messaggio finale dice quante sono. Ogni altro rifiuto ferma
il gesto per intero, e nessuna riga cambia.

> **Esempio.** Ordine di dodici righe, confermato. Si scrive «tutto il 20
> novembre»: *Aggiorna date di consegna* → data confermata → 20/11 → *tutte*.
> Il 15 il cliente chiede di spostare al 22, e quattro righe sono già partite
> con un DDT: si ripete col 22, *tutte*. Otto righe passano al 22, e le quattro
> spedite restano al 20.

### 3.6 Gli oneri: trasporto, urgenza, spese

Un **onere** è un addebito che accompagna la merce: il trasporto, una maggiorazione per urgenza, le
spese amministrative. In anagrafica è un articolo come gli altri, con una **causale onere** (Trasporto,
Trasferta, Urgenza…) che lo dice onere; la causale nuova si aggiunge al catalogo, senza toccare il
database. Sull'ordine lo aggiunge **l'operatore**, come una riga qualsiasi: ha prezzo e IVA, entra nei
totali e nella stampa, dove compare **dopo** gli articoli.

Un onere però **non si spedisce**, e l'ordine lo tratta di conseguenza:

| | La merce | L'onere |
| --- | --- | --- |
| evasione e residuo da spedire | sì | no: non tiene aperto l'ordine, non lo porta a «evaso» |
| nella bolla | la quantità che si sceglie | passa **intero**, nella **prima** bolla, anche se non lo si sceglie; non si ricopia nelle bolle successive; se la bolla si annulla torna sull'ordine |
| date di consegna | sì (§3.5) | no: la riga di un onere non le porta |
| un ordine fatto **solo** di oneri | — | non si conferma: un addebito senza merce si fa in commessa |

**Dove va messo dipende da come si fattura l'ordine.** Se l'ordine fattura **alla conferma**, l'onere
sta sull'ordine e va in commessa con lui (§10). Se fattura **alla consegna**, si può mettere sull'ordine
(passa nella bolla, che lo porta in commessa) o direttamente sulla bolla. Un addebito che non riguarda
nessun documento si fa dalla commessa, con la porta degli oneri
([Gestione Commesse](/guide/gestione-commesse)).

Un onere su un preventivo o su un'offerta **non** passa all'ordine: lì va in commessa da sé, e
sull'ordine lo aggiunge l'operatore.

---

## 4. Ciclo di vita e stati

⭐ Le regole comuni a tutti i documenti — in che stato si nasce, chi cambia lo stato, quale permesso chiede un passaggio, l'emissione, l'annullo — stanno nel [modello del documento di vendita](/guide/modello-documento-di-vendita), che al §10 dice anche a che punto è l'ordine rispetto al modello. Qui ci sono gli stati e i passaggi che sono suoi.

### 4.1 Stati

Il catalogo `config.stati_doc_ordini` prevede più stati; quelli raggiunti dai
processi di oggi sono cinque. Gli altri sono predisposti per il futuro
(magazzino/finanza).

| Stato | Significato | Modificabile? | In uso oggi |
|---|---|---|---|
| `DRAFT` | Bozza in preparazione | Sì: testata e righe | ✅ |
| `CONFERMATO` | Ordine confermato: nessuna merce ancora partita | No (solo la data di consegna promessa) | ✅ |
| `PARZIALMENTE_EVASO` | Una parte della merce è partita con le bolle | No (solo la data di consegna promessa) | ✅ |
| `EVASO` | Tutta la merce è partita con le bolle | No | ✅ |
| `ANNULLATO` | Ordine annullato, in bozza o confermato | No | ✅ |
| `ALLOCATO` / `SPEDITO` / `CONSEGNATO` / `FATTURATO` | Fasi logistiche/finanziarie future | — | ⏳ non ancora raggiunti |

⭐ **«Evaso» vuol dire «la merce è partita», e lo dicono solo le bolle.** Lo stato
lo proietta il database dalle bolle generate dall'ordine
(`vendite.fn_ordine_proietta_stato_evasione`): nessuna bolla → `CONFERMATO`, in
parte → `PARZIALMENTE_EVASO`, tutta → `EVASO`. Si riproietta a ogni bolla generata,
corretta o ritirata e a ogni reso. ⛔ **L'invio in commessa non cambia lo stato
dell'ordine**, e nemmeno l'annullo della commessa: che l'ordine sia già in
commessa lo dicono la lista «da mandare» e le capability del push (§5, §10).

### 4.2 Transizioni ammesse

Le transizioni sono governate dalla matrice `config.transizioni_stati_ordini`, che
per gli ordini è anche la **fonte unica di verità**: la stessa tabella decide sia
cosa mostrare in interfaccia, sia cosa il database accetta davvero.

```text
DRAFT ──(conferma)──▶ CONFERMATO ◀──(bolle)──▶ PARZIALMENTE_EVASO ◀──(bolle)──▶ EVASO
  │                       │
  └──(annulla)──▶ ANNULLATO ◀──(annulla)──┘   (terminale)
```

- **DRAFT → CONFERMATO** (*conferma*): è l'**emissione** dell'ordine e si fa solo da
  «Emetti», che produce numero e PDF insieme. Richiede **almeno una riga** e l'azione
  `emetti_ordine`.
- **DRAFT → ANNULLATO** (*annulla*): sempre consentito — una bozza non ha nulla da
  evadere.
- **CONFERMATO ↔ PARZIALMENTE_EVASO ↔ EVASO** (*automatiche*): le muove il database
  dalle bolle. Non sono pulsanti: generare, correggere o ritirare una bolla, o un
  reso, riproietta lo stato dell'ordine.
- **CONFERMATO → ANNULLATO** (*annulla*): consentito a chi ha l'azione
  `emetti_ordine`. Se l'ordine ha legami con altri documenti, l'annullo chiede una
  conferma (§4.3).

Ogni cambio di stato passa dal verbo dell'ordine,
[`vendite.fn_cambia_stato_ordine`](/dbzero/vendite/funzioni/fn_cambia_stato_ordine)
(l'annullo dal suo verbo d'annullo, che lo chiama); le transizioni automatiche le
scrive la proiezione dell'evasione. Nessun'altra strada scrive lo stato.

> **Il push a commessa non è una transizione.** Il push crea le entità a valle
> (righe di commessa, poi attività fatturabili) e **non tocca lo stato** dell'ordine.
> Se il push è solo parziale o fallisce, si ripete: le righe già mandate non sono più
> eleggibili.

### 4.3 Annullare un ordine nato da un altro documento

Un ordine può occupare qualcosa di altri documenti: le **righe del preventivo** da
cui è nato, l'**offerta** che ha trasformato, le **righe di commessa** ancora da
emettere che ha spinto. Annullandolo, queste cose tornano disponibili:

* le righe del preventivo si liberano e si possono ordinare di nuovo; se il
  preventivo era `EVASO`, torna `ACCETTATO`;
* l'offerta torna trasformabile, in un ordine o in un contratto: conta solo
  l'ordine **vivo**, quello annullato conserva la provenienza;
* le righe di commessa ancora da emettere si annullano (escono dalla commessa; le
  righe degli altri documenti restano).

Non succede in silenzio. Su un ordine con legami, «Annulla ordine» apre una
**finestra di conferma** che elenca che cosa si riapre e dove; ogni documento
dall'altra parte si apre con un clic. Confermando, l'operatore dichiara quanti
legami ha visto: se nel frattempo sono cambiati, la finestra si ripresenta
aggiornata. Un ordine senza legami si annulla con la sola conferma del cambio di
stato. Le righe di commessa **già emesse** non si riaprono: bloccano l'annullo.

### 4.4 La doppia difesa

Le regole di transizione valgono a **due livelli**:

1. **In interfaccia**: la funzione `fn_available_actions_ordine` legge la matrice e
   restituisce solo le azioni davvero disponibili — così i pulsanti che non hanno
   senso semplicemente non compaiono, e chi non ha `emetti_ordine` non vede
   «Conferma» né l'annullo di un ordine confermato.
2. **Nel database**: il trigger `trgfn_ordini_guard_transizione` rifiuta qualsiasi
   cambio di stato non previsto (`E_ORDINE_TRANSIZIONE_NON_AMMESSA`) e blocca la
   conferma di un ordine senza righe (`E_ORDINE_CONFERMA_SENZA_RIGHE`).

---

## 5. Azioni disponibili

Le azioni eseguibili in ogni momento sono calcolate dal database
(`fn_available_actions_ordine`) ed esposte all'interfaccia come elenco di
*capability*, così il frontend non deve replicare la logica degli stati.

Per ogni stato la funzione indica le azioni e alcuni flag utili:

| Flag | Vero quando |
|---|---|
| `can_edit_testata` / `can_edit_righe` | l'ordine è in `DRAFT` |
| `can_push_commessa` | l'ordine è `CONFERMATO`, `fatturazione_trigger = CONFERMATO` e c'è almeno una riga eleggibile |
| `can_push_commessa_reason` / `_reason_key` | (se il push non è possibile) il motivo, mostrato come tooltip |
| `non_editable_fields` | l'elenco dei campi bloccati (es. cliente, numero) |

In sintesi:

- **In `DRAFT`**: si può **modificare** testata e righe, **confermare** (azione
  *conferma*) o **annullare** (azione *annulla*).
- **In `CONFERMATO`, `PARZIALMENTE_EVASO` o `EVASO`**: testata e righe sono **in
  sola lettura**; l'azione disponibile è il **push a commessa** finché resta una
  riga da mandare. Quando le righe sono già in commessa il push è spento col
  motivo (`ORDINE_GIA_INVIATO`, `ORDINE_GIA_FATTURATO`,
  `ORDINE_NESSUNA_RIGA_PUSHABILE`): l'invio a commessa non si ripete per le stesse
  righe.
- **In `ANNULLATO`**: nessuna azione, sola lettura.

---

## 6. Creazione di un ordine

### 6.1 Da preventivo (smistamento merce)

Dal preventivo accettato, l'operatore apre il *Pannello Smistamento*, seleziona le
righe **merce** e lancia lo smistamento. Il sistema:

1. crea un ordine in `DRAFT` copiando il contesto dal preventivo;
2. copia **solo** le righe selezionate di natura merce, con i loro prezzi, i
   componenti BoM e la **data di consegna richiesta dal cliente** (§3.5);
3. registra su ogni riga il legame con la riga di preventivo di origine
   (idempotenza);
4. valorizza l'origine documentale come `PREVENTIVO`.

Se tutte le righe merce sono già state smistate, l'operazione segnala che non c'è
nulla da convertire (`E_VENDITA_PREVENTIVO_NESSUNA_RIGA_ORDINE`). Se il preventivo
non è in stato accettato, l'operazione è rifiutata
(`E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO`).

### 6.2 Da offerta (conversione 1:1)

Dall'offerta accettata, la conversione genera **un solo** ordine `DRAFT` con
**tutte** le righe espanse dell'offerta (prezzi negoziati e override preservati).
Vincoli:

- l'offerta deve essere **accettata**;
- non deve essere già stata convertita in ordine (`E_ORD_OFFERTA_GIA_CONVERTITA`);
- non deve aver già generato un contratto (mutua esclusività).

### 6.3 Manuale

1. **Nuovo ordine** → scegli il cliente (billing account), eventualmente l'utility,
   la data e le condizioni di pagamento.
2. L'ordine nasce in `DRAFT` con numero già assegnato.
3. **Aggiungi le righe**: cerca l'articolo, indica quantità e — se serve — prezzo e
   sconto. Se ometti il prezzo, il sistema lo propone tramite il pricing (vedi §8).
4. Per gli **articoli compositi**, un dialog mostra l'anteprima dei componenti e ne
   propone i prezzi; alla conferma i componenti vengono salvati.

> **Bozza "usa e getta".** La creazione salva subito una bozza per poter aggiungere
> le righe. Se l'operatore esce senza inserirne nessuna, quella bozza vuota può
> essere eliminata. Un ordine **con righe**, invece, non si cancella: si **annulla**.

---

## 7. Cliente ed emittente fiscale

### 7.1 Cliente immutabile

Una volta creato l'ordine, il **cliente non si cambia più**: i campi
`billing_account_id` e `soggetto_ruolo_id` sono bloccati. Tentare di modificarli dà
`E_ORD_CLIENTE_IMMUTABILE`. La regola è semplice: **cambiare cliente = nuovo
ordine**. È una protezione dagli errori (la ricerca del cliente è frequente, il
cambio è raro e avrebbe pesanti riflessi contabili). Il blocco è applicato sia dal
backend sia, in modo autoritativo, dal database.

### 7.2 Emittente fiscale

Se l'operatore **non** indica un emittente fiscale, lo imposta automaticamente il
trigger di default dell'emittente (`trg_ordini_a10_default_emittente_ins`, che dal
2026-09-15 esegue il meccanismo condiviso `script.trgfn_default_emittente_fiscale` —
lo stesso per preventivi, contratti, DDT, offerte, magazzini e altre tabelle), in base
all'emittente associato all'utente che sta operando. Inoltre, se l'ordine ha un cliente, l'emittente deve
essere **coerente** con quel cliente: a questo pensa il trigger
`script.trgfn_doc_guard_emittente_ba`, che rifiuta combinazioni incoerenti. In pratica
l'operatore raramente deve preoccuparsene, ma se l'utente non ha un emittente
assegnato la creazione viene bloccata con un errore parlante.

---

## 8. Prezzi e totali

### 8.1 Come si determina il prezzo

Il prezzo delle righe arriva da una di queste vie:

- **conversione**: nei percorsi da preventivo/offerta il prezzo è già quello
  negoziato a monte e viene "fotografato" sull'ordine;
- **inserimento manuale**: l'operatore digita il prezzo;
- **proposta automatica**: se il prezzo è assente (e l'articolo non è composito), il
  sistema lo risolve dal listino tramite il *PricingService*.

> **Niente gate prezzi L2/L3 sull'ordine.** A differenza di offerte e contratti,
> l'ordine **non** applica le soglie e l'escalation di approvazione prezzo: è una
> scelta di modello (pricing "stile preventivo" — si risolve il prezzo e si usa
> quello del chiamante). Le eventuali approvazioni sono già avvenute a monte.

### 8.2 Totali e IVA

I totali di testata (imponibile, IVA, totale documento) sono **calcolati e tenuti
aggiornati dal database** ad ogni modifica delle righe (`fn_ricalcola_totali_ordine`
e i relativi trigger): l'operatore li vede aggiornarsi senza dover fare nulla.

L'IVA è calcolata **per gruppo di aliquota** (non riga per riga), secondo la regola
fiscale standard. Il *Riepilogo IVA* dell'ordine mostra una riga per aliquota con
imponibile, imposta, arrotondamento e totale.

> ⚠️ **Attenzione a non confondere due cose diverse.** Il riepilogo **somma** ciò
> che le righe già portano; a decidere il codice IVA della **singola riga** è il
> **risolutore IVA**, una funzione sola condivisa con preventivi, DDT e fatture —
> articolo, poi uso della fornitura, poi eventuali titoli documentati del cliente.
> La regola completa, con il motivo per cui l'`iva_id` non si copia dall'articolo,
> è in [Il risolutore IVA di riga](/guide/iva-risolutore-di-riga).
>
> Il riepilogo dell'ordine è inoltre **«live»**, non uno snapshot: si ricalcola a
> ogni modifica delle righe, perché l'ordine è un documento di lavoro. Lo snapshot
> appartiene ai documenti con un istante di emissione i cui valori diventano
> autorevoli (preventivo, fattura).

---

## 9. Conferma e stampa

Nella famiglia vendite **confermare equivale a emettere il documento**. Il percorso
principale dell'operatore è l'azione **Emetti**:

1. dall'ordine in `DRAFT` si lancia l'emissione;
2. il sistema **conferma** l'ordine (`DRAFT → CONFERMATO`) e, nella **stessa
   operazione atomica**, **genera il PDF** di conferma d'ordine;
3. si possono allegare file opzionali.

Se la generazione del PDF fallisce, **anche la conferma viene annullata**: l'ordine
resta in `DRAFT` e non si crea alcun documento "monco".

Cosa contiene il PDF: numero e data ordine, cliente, emittente, eventuale
provenienza (da preventivo/offerta), righe con quantità/prezzo/sconto, totali per
aliquota IVA e note.

> **Anteprima vs documento definitivo.** In `DRAFT` è disponibile solo
> l'**anteprima** del PDF. Il documento "vero" (persistito, scaricabile,
> ristampabile) nasce con la conferma. Per la stampa serve che esista un **template
> "ORDINE_VENDITA" pubblicato** (vedi [Documenti e stampe](/guide/documenti-e-stampe)).

---

## 10. Push a commessa

Quando l'ordine è `CONFERMATO` (e `fatturazione_trigger = CONFERMATO`), l'azione
**push a commessa** chiude il giro: le righe eleggibili dell'ordine generano le
**attività fatturabili** su una commessa, che a sua volta alimenta la pipeline di
fatturazione.

Sono eleggibili le righe attive, con quantità positiva, non ancora inviate a una
commessa. Gli **oneri** dell'ordine (§3.6) ci vanno insieme alla merce, come oneri con la loro causale
e col riferimento all'ordine: fatturando l'ordine, si fattura anche il suo trasporto. Se non c'è alcuna riga eleggibile, l'azione non è disponibile e
l'interfaccia ne spiega il motivo.

**L'invio a commessa è unico per riga, e non cambia lo stato dell'ordine.** Una riga
mandata in commessa non è più eleggibile; un push **parziale** o **fallito** si
ripete finché non è completo. Lo stato dell'ordine resta quello che dicono le bolle
(§4.1).

**Annullare la commessa riapre l'ordine.** Se la commessa in cui sono finite le
righe viene annullata (con la conferma, vedi
[Gestione Commesse](/guide/gestione-commesse) §«Annullare una commessa»), le righe
ancora da emettere escono dalla commessa e l'ordine torna **da mandare in commessa**,
con lo stato che aveva. Le righe già emesse invece bloccano l'annullo della
commessa.

> **Il push autorizza anche la fatturazione.** Dato che un ordine `CONFERMATO` è già
> autorizzato, al termine del push le commesse toccate vengono rese **emittibili**
> (attività approvate + testata "pronta per la fatturazione"), senza un passaggio di
> approvazione aggiuntivo. Il dettaglio è in [Gestione Commesse](/guide/gestione-commesse)
> e [Fatturazione](/guide/fatturazione).

---

## 11. Lista ordini

La lista ordini è una **lista configurabile** (l'utente può scegliere colonne e
ordinamento). Mostra di norma numero, data, cliente, utility, totale, stato e
trigger di fatturazione; sono disponibili in opzione colonne aggiuntive (importi di
dettaglio, pagamento, emittente, origine documentale, agente, ecc.) e la **data di
consegna richiesta** dell'ordine — il minimo sulle righe attive, calcolato dalla
vista `vw_ordini_lista` (`data_consegna_richiesta_cliente_min`): si accende da
«Personalizza colonne», non è nella vista standard.

Filtri principali: ricerca testuale (numero, ragione sociale, codice cliente, codice
fiscale/P.IVA), stato, cliente, utility, intervallo di date. La lista rispetta
automaticamente lo **scope dell'emittente** dell'utente: ognuno vede solo i propri
ordini.

Dalla lista si aprono il dettaglio, l'export (CSV/XLSX) e la gestione dei documenti
generati.

---

## 12. Casi d'uso operativi

### 12.1 Ordine di sola merce da un preventivo

1. Il preventivo viene **accettato**.
2. Apri il *Pannello Smistamento* → seleziona le righe **merce** → "Smista
   selezionate".
3. Nasce un ordine in `DRAFT` con quelle righe. (I servizi una tantum del
   preventivo seguono il loro percorso verso la commessa.)
4. "Emetti" → l'ordine passa a `CONFERMATO` e si genera il PDF.
5. "Push a commessa" → parte la fatturazione.

### 12.2 Consegne parziali dallo stesso preventivo

1. Primo smistamento: seleziona solo una parte delle righe merce → primo ordine.
2. Più tardi: torna sul preventivo e smista le righe residue → secondo ordine.
3. Quando non resta più nulla da smistare su nessun ramo, il preventivo passa a
   **EVASO** da sé.

### 12.3 Ordine da offerta

1. L'offerta viene **accettata**.
2. "Genera ordine" → nasce **un** ordine con tutte le righe dell'offerta.
3. Da quel momento l'offerta non potrà più generare un contratto (mutua
   esclusività), e un secondo "Genera ordine" verrà rifiutato.

### 12.4 Ordine manuale con articolo composito

1. Nuovo ordine → cliente → "Aggiungi riga" con un articolo composito.
2. Il dialog mostra i componenti e propone i prezzi → conferma.
3. Il prezzo della riga è la somma dei componenti; aggiusta i prezzi se serve.
4. "Emetti" → conferma + PDF.

### 12.5 Bozza creata per errore

1. Ordine ancora in `DRAFT` **senza righe** → eliminabile.
2. Ordine in `DRAFT` **con righe** → non si elimina: usa "Annulla" (→ `ANNULLATO`).

---

## 13. Errori principali

Codici sollevati dal dominio ordini (registrati in `config.messaggi_errore` /
`error_policies`):

| Codice | Quando |
|---|---|
| `E_ORD_NOT_FOUND` | Ordine (o riga/componente) inesistente o fuori dal proprio scope emittente |
| `E_ORD_VALIDAZIONE` | Payload non valido (cliente mancante, campi vuoti, valori non numerici…) |
| `E_ORD_CLIENTE_IMMUTABILE` | Tentativo di cambiare il cliente di un ordine già creato |
| `E_ORD_STATO_TRANSIZIONE` | Operazione non ammessa nello stato (es. modifica fuori da `DRAFT`, oppure delete di una bozza con righe → va annullata) |
| `E_ORD_NESSUNA_RIGA` | Conferma/push senza righe eleggibili (controllo applicativo) |
| `E_ORD_OFFERTA_GIA_CONVERTITA` | Conversione offerta → ordine già avvenuta (univocità 1:1) |
| `E_OFFERTA_CONTRATTO_GIA_GENERATO` | L'offerta ha già generato un contratto: non può generare anche un ordine (mutua esclusività XOR) |
| `E_ORD_ORIGINE_NON_CONVERTIBILE` | Conversione da un'offerta non in stato convertibile (non ACCETTATA) |
| `E_ORDINE_TRANSIZIONE_NON_AMMESSA` | Cambio di stato non previsto/attivo nella matrice transizioni (guard DB) |
| `E_ORDINE_CONFERMA_SENZA_RIGHE` | Conferma di un ordine senza righe (guard DB, gemello di `E_ORD_NESSUNA_RIGA`) |
| `E_ORDINE_CONFERMA_SOLO_ONERI` | Conferma di un ordine che ha solo oneri e nessuna merce (§3.6) |
| `E_RIGA_ONERE_DATA_CONSEGNA` | Una data di consegna sulla riga di un onere (§3.6) |
| `E_RIGA_NATURA_NON_AMMESSA` | Un servizio che non è un onere su una riga d'ordine (§3.2) |
| `E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO` | Smistamento da un preventivo non accettato |
| `E_VENDITA_PREVENTIVO_NESSUNA_RIGA_ORDINE` | Smistamento senza righe merce residue (tutte già allocate o nessuna di natura merce) |
| `E_DOCUMENTI_*` | Stampa: template/versione non risolti, input invalido o render fallito |

---

## 14. Pattern e principi di design

### 14.1 Ordine come "fotografia" operativa

L'ordine non rimanda a un listino né si revisiona: i prezzi sono congelati alla
nascita. È il documento che dice "questo è ciò che facciamo", non "questo è ciò che
proporremmo". Per questo è più semplice di preventivo, offerta e contratto.

### 14.2 Due conversioni, due nature

Preventivo → ordine è **1:N per riga** perché il preventivo è un elenco di articoli
a natura mista. Offerta → ordine è **1:1 in blocco** perché l'offerta è una proposta
unitaria. La stessa offerta, inoltre, sceglie **una** strada — contratto **o**
ordine — mai entrambe.

### 14.3 Matrice transizioni come unica fonte di verità

Per gli ordini la tabella `config.transizioni_stati_ordini` serve **sia** a
costruire i pulsanti in interfaccia **sia** a far rispettare il grafo nel database.
Una sola fonte: ciò che la UI mostra è esattamente ciò che il DB accetta. Per
attivare in futuro gli stati a valle (magazzino/DDT) basterà aggiungere righe a
quella matrice.

### 14.4 Trigger DB come ultima difesa

Cliente immutabile, transizioni ammesse, "almeno una riga" per confermare, coerenza
emittente/cliente, numero immutabile: sono tutte regole presidiate da trigger DB.
Il backend ha controlli equivalenti solo per dare messaggi chiari prima del giro al
database; anche bypassandolo, il database rifiuta comunque le operazioni scorrette.

---

## 15. Glossario rapido

| Termine | Significato |
|---|---|
| **Ordine di vendita** | Documento operativo del ciclo attivo: righe da consegnare/fatturare. Stati: `DRAFT` → `CONFERMATO` → `PARZIALMENTE_EVASO` / `EVASO` dalle bolle (oppure `ANNULLATO`) |
| **Smistamento** | Conversione delle righe **merce** di un preventivo accettato in uno o più ordini (1:N, riga per riga) |
| **Conversione 1:1** | Generazione di un singolo ordine da un'offerta accettata, in alternativa al contratto (XOR) |
| **Emetti** | Conferma dell'ordine + generazione del PDF, in un'unica operazione atomica |
| **Evaso** | La merce dell'ordine è partita con le bolle: tutta (`EVASO`) o in parte (`PARZIALMENTE_EVASO`). Non dipende dall'invio in commessa |
| **Push a commessa** | Invio delle righe eleggibili a una commessa, che avvia la fatturazione; non cambia lo stato dell'ordine (una riga si manda una volta) |
| **`fatturazione_trigger`** | Quando l'ordine pusha a commessa (oggi: `CONFERMATO`) |
| **Cliente immutabile** | Il cliente non si cambia dopo la creazione: "cambiare cliente = nuovo ordine" |
| **Matrice transizioni** | `config.transizioni_stati_ordini`: fonte unica di verità per UI ed enforcement |
| **Date di consegna** | Sulla riga: `data_consegna_richiesta_cliente` (del cliente) e `data_consegna_confermata` (nostra). Nessun vincolo fra le due; la testata non ne ha una |
| **Ritardo** | `giorni_ritardo` nel pannello Situazione merce: vuoto = non si applica, `0` = in tempo, `N` = giorni oltre la promessa (o la richiesta, se non c'è promessa) con merce ancora da spedire |

---

*Per il dettaglio tecnico delle API REST, formati payload e codici errore vedi la
[documentazione API Ordini](/backend/vendite/manual/api_ordini). Le decisioni di
modello sono raccolte negli addendum di sviluppo (`dev/work-done/db-brief-ordini-vendita.md`,
`brief-ordini-stampa.md`, `db-brief-ordini-lock-cliente.md`, `brief-preventivi-ordini.md`;
le date di consegna in `brief-db-modifiche-certe-ciclo-vendita-e-articolo.md`).*

---
{% include-markdown "signature-core.md" %}
