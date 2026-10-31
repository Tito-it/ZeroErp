# Guida — Gestione Contratti vendita

> **Ultimo aggiornamento**: 31 ottobre 2026
>
> **Destinatari**: analisti funzionali, sviluppatori backend/frontend, DBA.
>
> **Vedi anche** — schemi DB:
>
> * [vendite.contratti](/dbzero/vendite/tabelle/contratti) / [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe) / [vendite.contratti_righe_componenti](/dbzero/vendite/tabelle/contratti_righe_componenti)
> * [vendite.contratti_utilities](/dbzero/vendite/tabelle/contratti_utilities)
> * [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti) / [config.transizioni_stati_contratti](/dbzero/config/tabelle/transizioni_stati_contratti)
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — BoM versionata immutabile
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2) — resolver pricing bundle-aware, STADIO 1
> * [vendite.trgfn_contratti_freeze_listino_versione](/dbzero/vendite/manual/trgfn_contratti_freeze_listino_versione) — snapshot versione listino a DRAFT→ATTIVO
> * [vendite.trgfn_doc_testata_lock_fuori_bozza](/dbzero/vendite/funzioni/trgfn_doc_testata_lock_fuori_bozza) — che cosa della testata si cambia ancora dopo la bozza
> * [vendite.trgfn_doc_righe_lock_fuori_bozza](/dbzero/vendite/manual/trgfn_doc_righe_lock_fuori_bozza) — righe solo in bozza (building block condiviso con DDT e ordini)
> * [script.fn_check_articolo_riga](/dbzero/script/manual/fn_check_articolo_riga) — quali articoli ammette una riga (contratto e offerta): AGGIUNTA già in listino, OVERRIDE ed ESCLUSIONE solo su un articolo del listino, solo componente, kit senza componenti, figlio di bundle
> * [vendite.fn_contratto_riga_componenti_init](/dbzero/vendite/manual/fn_contratto_riga_componenti_init) — popola componenti BoM su riga padre composito
> * [vendite.fn_contratto_riga_componenti_preview](/dbzero/vendite/manual/fn_contratto_riga_componenti_preview) — suggerimento prezzi pre-save
> * [vendite.fn_contratti_addebiti_maturati](/dbzero/vendite/manual/fn_contratti_addebiti_maturati) — che cosa il contratto addebita a ogni giro (una tantum, canoni, storni), e che cosa non può partire
> * [vendite.fn_list_contratti_da_pushare](/dbzero/vendite/manual/fn_list_contratti_da_pushare) — il lister del push dei contratti
> * [vendite.fn_canone_periodi](/dbzero/vendite/funzioni/fn_canone_periodi) — la regola dei periodi del canone
>
> **Vedi anche** — guide correlate:
>
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — **le regole comuni a tutti i documenti**: nascita, cambio di stato, permesso sul passaggio, emissione, annullo
> * [Gestione Listini e Pricing v5](/guide/gestione-listini) — cascata promo → contratto → categoria
> * [Gestione Preventivi](/guide/gestione-preventivi) — proposta puntuale (→ commessa); modello simmetrico
> * [Fatturazione end-to-end](/guide/fatturazione) — la pipeline a valle del contratto
> * [Cruscotti fatturazione](/guide/cruscotti-fatturazione) — dove si vede un contratto fermo
> * [Modello componenti BoM](/dev/manual/modello-componenti-bom) — simmetria cross-dominio

---

## 1. Cosa è un contratto

Un contratto è la **relazione commerciale duratura** fra l'azienda e un cliente
per una specifica utility (Gas, Energia, Idrico, ecc.). Risponde alla domanda:
*"Quali condizioni di prezzo si applicano a questo cliente su questo servizio
nel periodo di validità?"*

Caratteristiche di base:

* è intestato a un **billing account** (cliente) e a una **utility** (servizio)
* definisce il **listino di riferimento** (opzionale) e un'eventuale **variazione
  globale** (sconto o maggiorazione applicata a tutto il listino)
* può contenere **eccezioni puntuali** per singoli articoli (prezzi personalizzati,
  esclusioni, articoli fuori listino, articoli del listino che il cliente prende)
* **addebita** quello che il cliente ha sottoscritto: una tantum e canoni a periodi
  (§4-bis)
* ha un **ciclo di vita** con stati da bozza a attivo, fino alla cessazione
* quando **attivato**, viene usato come primo stadio (STADIO 1) del resolver
  pricing per determinare il prezzo applicabile a ogni articolo del BA

Il numero documento è auto-generato (prefisso `CNT`) e non modificabile.

### 1.1 Il modello unificato (post-refactor maggio 2026)

Prima del refactor esistevano tre "modalità" esplicite (A/B/C) che l'operatore
sceglieva all'apertura del form. Le modalità sono state eliminate: il contratto
ha ora un **modello unico**, e la sua "forma" è derivata automaticamente dai
dati compilati:

| Forma derivata    | Condizione            | Significato commerciale                                                                                |
| ----------------- | --------------------- | ------------------------------------------------------------------------------------------------------ |
| **Con listino**   | `listino_id NOT NULL` | Il cliente ha un listino di partenza (con o senza variazione globale e con o senza eccezioni puntuali) |
| **Senza listino** | `listino_id NULL`     | Tutto negoziato puntualmente — le righe sono l'unica fonte di prezzo                                   |

La variazione globale è un campo opzionale della testata. Le eccezioni sulle righe
sono compatibili con la variazione globale: un contratto con listino può avere
sia variazione globale che override su singoli articoli — non c'è contraddizione.

---

## 2. Le entità in gioco

### 2.1 Testata `contratti`

Contiene il contesto commerciale e i parametri di pricing:

* **chi** (`billing_account_id`, `istanza_utility_id`)
* **per cosa** (`utility_id`, `ambito`: COMMODITY / COMMERCIO)
* **quando** (`data`, `valido_dal`, `valido_al`)
* **listino** (`listino_id` nullable, `listino_versione_id` nullable — fissato all'attivazione)
* **variazione globale** (`tipo_variazione_globale`, `valore_variazione_globale`) — opzionale;
  si applica a tutte le righe listino salvo override puntuale
* **canone**: il mese da cui si contano i periodi (`mese_partenza_canone`) e se i
  canoni sono anticipati o normali (`generazione_canone`) — vedi §4-bis.3
* **stato** corrente (`stato_doc_contratto_id`)
* **categoria cliente** al momento della creazione (`categoria_cliente_id`) — snapshot
  congelato, non segue variazioni anagrafica

I campi `listino_id`, `listino_versione_id`, `tipo_variazione_globale`,
`valore_variazione_globale` diventano **immutabili** al passaggio in ATTIVO
(lock post-attivazione — vedi §6).

### 2.2 Eccezioni `contratti_righe`

Contiene le **eccezioni puntuali** al listino. Una riga non è un "articolo da
ordinare" come in un preventivo, ma un **modificatore** che sovrascrive o
integra il listino per un articolo specifico. Il campo `tipo_eccezione` (ENUM
NOT NULL) qualifica esplicitamente il tipo:

| `tipo_eccezione` | Significato                                                                                                                       | `prezzo_unitario` |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------- | ----------------- |
| `OVERRIDE`       | Prezzo personalizzato per articolo **presente nel listino** — la variazione globale non si applica; l'override è il prezzo finale | NOT NULL          |
| `ESCLUSIONE`     | Articolo del listino **non disponibile** per questo cliente — il resolver solleva errore se richiesto                             | NULL              |
| `AGGIUNTA`       | Articolo **non presente nel listino**, aggiunto al contratto — valido anche su contratti senza listino                            | NOT NULL          |
| `ADESIONE`       | Articolo **del listino** che il cliente prende, al prezzo del listino con la variazione globale — sulla riga solo quantità e periodicità | NULL              |

Constraint DB:

* OVERRIDE, ESCLUSIONE e ADESIONE: al massimo una riga per `(contratto, articolo)` (unique parziale)
* AGGIUNTA: al massimo una riga per `(contratto, articolo)` (unique parziale separato)
* CHECK: `prezzo_unitario NOT NULL` se OVERRIDE o AGGIUNTA; NULL obbligatorio se ESCLUSIONE o ADESIONE
* Guard: una AGGIUNTA è bloccata se l'articolo è già nel listino fissato al contratto
  (si deve usare OVERRIDE)
* Guard: una ESCLUSIONE è bloccata se l'articolo è un **componente** (figlio) di un
  bundle del listino del contratto — l'esclusione va applicata al **padre bundle**,
  non al singolo componente (`E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA`)
* Nella ricerca dell'articolo di una riga nuova compaiono prima gli articoli che la riga può
  usare; gli altri sono in grigio, col motivo sotto, e non si scelgono. È la stessa regola dei
  guard qui sopra

Per gli **articoli compositi** (distinta base): una riga ESCLUSIONE **non genera
componenti**. L'esclusione toglie l'articolo per intero, quindi non ha prezzo né
pezzi da dettagliare — coerente con il vincolo "ESCLUSIONE ⇒ prezzo NULL". I
componenti si inizializzano solo per OVERRIDE e AGGIUNTA su articolo composito.

**Quantità e unità di misura operativa**: la quantità segue lo **stesso meccanismo**
di preventivi e offerte (vedi [Gestione preventivi §2.2](gestione-preventivi.md)).
L'operatore la inserisce **nell'unità di misura operativa scelta** (`qta_operativa`);
il sistema deriva da sé il valore nell'unità base (`quantita = qta_operativa ×
factor_to_base`, fattore "fotografato" sulla riga). La quantità **può essere negativa**
(resi/storni), **non può essere zero**. La quantità la porta la **fonte**: quando è
*fissa* è obbligatoria; quando è *derivata dai componenti* la scrive il sistema; con
ogni altra fonte (letture, timesheet, inserimento manuale a ogni periodo) arriva a
valle, e sulla riga **deve restare vuota**: il database rifiuta una quantità scritta
lì (`E_RIGA_QUANTITA_CON_FONTE_A_VALLE`, sul campo). La regola è la stessa sulle righe
dell'offerta.

Operativamente: in DRAFT le righe sono liberamente modificabili; dopo l'attivazione
ogni INSERT / UPDATE / DELETE è bloccato dal trigger di lock.

### 2.3 Utility `contratti_utilities`

Riga 1:1 con l'utility del contratto. Porta i parametri specifici della fornitura:
tipo utenza, classe utenza, dati PDP (punto di prelievo/consegna), parametri
precontrattuali. È creata contestualmente alla testata.

### 2.4 Componenti BoM `contratti_righe_componenti`

Quando una riga punta a un articolo `is_composito = TRUE`, il sistema genera
automaticamente un record per ogni **componente** della BoM. Il prezzo del padre
(OVERRIDE o AGGIUNTA) è la **somma pesata** dei prezzi figli — mai inserita a
mano.

I componenti portano:

* riferimento al componente del catalogo + UoM + quantità (= padre × `coeff_qta`)
* prezzo unitario (modificabile con autorizzazioni)
* snapshot del coefficiente al momento della creazione
* origine prezzo (CONTRATTO_OVERRIDE / CONTRATTO_AGGIUNTA / CONTRATTO_LISTINO / CATEGORIA)

La struttura BoM (quali componenti, in che quantità relative) è **immutabile per
contratto**: si possono cambiare i prezzi, non la composizione.

---

## 3. Ciclo di vita e stati

⭐ Le regole comuni a tutti i documenti — in che stato si nasce, chi cambia lo stato, quale permesso chiede un passaggio, l'emissione, l'annullo — stanno nel [modello del documento di vendita](/guide/modello-documento-di-vendita), che al §10 dice anche a che punto è il contratto rispetto al modello. Qui ci sono gli stati e i passaggi che sono suoi.

### 3.1 Stati e transizioni

Gli stati sono governati da `config.stati_doc_contratti` e le transizioni ammesse
da `config.transizioni_stati_contratti`:

| Stato       | Significato                                                   | Modificabile?               |
| ----------- | ------------------------------------------------------------- | --------------------------- |
| `DRAFT`     | Bozza in costruzione                                          | Sì: testata, righe, utility |
| `ATTIVO`    | Contratto in vigore — usato dal resolver pricing              | No (lock post-attivazione)  |
| `CESSATO`   | Contratto scaduto o terminato                                 | No (terminale)              |
| `ANNULLATO` | Bozza annullata prima dell'attivazione (`is_abortito = true`) | No (terminale)              |

La transizione `ATTIVO → CESSATO` può essere **automatica** (la chiusura per
scadenza, quando la data di fine è passata) o **manuale** (operatore che chiude il
contratto). La cessazione manuale chiede sempre la **data di fine**, e la data decide:

| Data di cessazione | Che cosa succede |
| --- | --- |
| oggi | il contratto passa subito a `CESSATO` |
| futura | **cessazione programmata**: si scrive solo la data, il contratto resta `ATTIVO` fino a quel giorno e la chiusura per scadenza lo cessa il giorno dopo |
| passata | rifiutata (`E_CONTRATTO_VALIDO_AL_RETROATTIVO`): non si riscrive la storia del contratto |
| mancante | rifiutata (`E_CONTRATTO_CESSAZIONE_SENZA_DATA`) |

Attivazione e cessazione chiedono l'azione `emetti_contratto` (chi non ce l'ha non vede
«Attiva» né «Cessa»); l'annullo della bozza chiede solo il permesso sul contratto. I
passaggi ammessi sono quelli della matrice `config.transizioni_stati_contratti`, e lo
stato si cambia solo dalle operazioni del contratto (il
[modello del documento di vendita](/guide/modello-documento-di-vendita), §5-§6).

La transizione `DRAFT → ANNULLATO` è sempre ammessa: una bozza non ancora
attivata può essere annullata in qualsiasi momento. Un contratto ANNULLATO non
partecipa al controllo di overlap temporale: dopo l'annullamento è possibile
creare un nuovo contratto sulla stessa quadrupla senza conflitti.

**Annullare un contratto nato da un'offerta.** L'offerta torna trasformabile, in
un contratto o in un ordine: conta solo il contratto **vivo**, quello annullato
conserva la provenienza. Se il contratto ha spinto righe in commessa ancora da
emettere, si annullano anche quelle. Non succede in silenzio: «Annulla
contratto» apre una **finestra di conferma** che elenca che cosa si riapre, con
l'offerta e la commessa apribili con un clic, e l'operatore dichiara quanti
legami ha visto. Le righe di commessa **già emesse** non si riaprono: bloccano
l'annullo.

Non esiste revisione come nei preventivi: se le condizioni cambiano, si cessa il
contratto corrente e se ne crea uno nuovo.

### 3.2 Cosa succede alla transizione DRAFT → ATTIVO

> **L'attivazione passa OBBLIGATORIAMENTE dall'emissione documentale.** Non esiste
> più un semplice cambio-stato "Attiva": l'operatore usa l'azione **Emetti**
> (endpoint `POST /api/v1/vendite/contratti/<id>/emetti/`, dialog
> `ContrattoEmissioneDialog`), che in **una transazione atomica** esegue il cambio
> stato + il freeze della versione listino + la **generazione del PDF** (con
> eventuali allegati). Vale l'invariante "contratto ATTIVO ⇒ esiste un documento
> PDF". Un `cambia_stato` diretto verso ATTIVO è **rifiutato**.

Durante l'attivazione, il trigger `trgfn_contratti_freeze_listino_versione`
interviene BEFORE UPDATE sulla colonna `stato_doc_contratto_id`. In sequenza:

0. **Generazione documento** (atomica con i passi successivi): se il PDF non può
   essere generato, l'intera transazione viene annullata e il contratto resta DRAFT.
1. **Guard negoziato puro senza righe**: se `listino_id IS NULL` e non esiste almeno
   una riga **AGGIUNTA con prezzo valorizzato** in `contratti_righe`, solleva
   `E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE` (451). Su un contratto senza listino
   l'OVERRIDE non è applicabile (presuppone l'articolo presente nel listino):
   l'unica via di valorizzazione è l'AGGIUNTA con prezzo.
2. **Snapshot versione listino**: se il contratto ha `listino_id` valorizzato,
   cerca la versione attiva alla data corrente e scrive `listino_versione_id`.
   Da quel momento la versione è **congelata** (§4.2 per le implicazioni runtime).
3. **Lock**: da ATTIVO in poi, testata e righe sono immutabili (§6).

---

## 4. Il modello di pricing del contratto

### 4.1 Il contratto come STADIO 1 del resolver

Il resolver prezzi `fn_resolve_prezzo_listino_v2` valuta tre stadi in cascata:

```text
STADIO 0: promo_articoli (overlay)
STADIO 1: contratto attivo (OVERRIDE / ESCLUSIONE / AGGIUNTA + listino con versione fissata)
STADIO 2: matrice categorie_clienti_listini (listino categoria)
```

Il contratto è **STADIO 1**: se esiste un contratto ATTIVO per il BA alla data
richiesta, i prezzi vengono risolti da lì prima di guardare la categoria cliente.

### 4.2 Versione listino fissata all'attivazione

In DRAFT il contratto "segue" la versione corrente del listino: ogni volta che
si legge la preview righe, il resolver usa la versione attiva alla data odierna.

Alla transizione DRAFT → ATTIVO il trigger **fissa** `listino_versione_id`:

* da quel momento il contratto legge **sempre quella versione specifica** del
  listino, anche se nel frattempo ne esce una v6, v7, ecc.
* il cliente ha un prezzo prevedibile per tutta la durata del contratto
* gli articoli non presenti nella versione fissata (aggiunti in versioni
  successive) **non** sono automaticamente disponibili nel contratto

**Conseguenza in DRAFT**: se durante la lavorazione della bozza viene pubblicata
una nuova versione del listino, la preview si aggiorna automaticamente ai nuovi
prezzi. Gli OVERRIDE e AGGIUNTA già inseriti restano validi (puntano all'articolo,
non alla versione). Il banner UI segnala il drift: "Il listino è stato aggiornato
alla v6 — le tue eccezioni fanno ancora riferimento alla v5, rivedi prima di
attivare".

### 4.3 Logica di risoluzione prezzo (STADIO 1)

Dato un articolo richiesto per il contratto, il resolver cerca in `contratti_righe`:

1. **Riga ESCLUSIONE** → `E_ARTICOLO_ESCLUSO_DA_CONTRATTO` (453). L'articolo non è
   fatturabile per questo cliente con questo contratto.
2. **Riga OVERRIDE** → usa `prezzo_unitario` come prezzo finale (`origine =
   CONTRATTO_OVERRIDE`). La variazione globale **non** si applica; l'override è
   il prezzo negoziato definitivo.
3. **Riga AGGIUNTA** → usa `prezzo_unitario` (`origine = CONTRATTO_AGGIUNTA`).
   Vale anche se il contratto non ha listino.
4. **Nessuna eccezione + listino presente** → legge il prezzo dalla versione
   listino fissata e applica eventuale `tipo_variazione_globale` + `valore_variazione_globale`
   (`origine = CONTRATTO_LISTINO`).
5. **Nessuna eccezione + nessun listino** → `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C`.

Se il contratto non è trovato (nessun contratto ATTIVO per BA+utility+data), il
resolver scende a STADIO 2 (categoria cliente).

### 4.4 Variazione globale — comportamento

La variazione globale (`tipo_variazione_globale` + `valore_variazione_globale`) si
applica **solo alle righe che non hanno un OVERRIDE puntuale**. Un articolo con
OVERRIDE riceve esattamente il prezzo negoziato, senza variazione globale.

| `tipo_variazione_globale` | Formula                                                          |
| ------------------------- | ---------------------------------------------------------------- |
| `PERCENTUALE`             | `prezzo_listino * (1 + valore / 100)` — valore negativo = sconto |

> A livello testata è ammessa **solo** la variazione PERCENTUALE. `VALORE_FISSO`
> globale è vietato perché un delta in euro insensibile alla magnitudine del
> listino opacizza la natura della variazione e la rende fragile a evoluzioni del
> catalogo. Resta ammesso `VALORE_FISSO` come **OVERRIDE** su singola riga
> (semantica esplicita di "prezzo fisso sostitutivo per quell'articolo"). Il
> lookup FE espone solo PERCENTUALE; il service rifiuta con messaggio parlante
> eventuali tentativi via curl/API esterna.

---

## 4-bis. Come il contratto si addebita: una tantum e canoni

Il contratto dà i prezzi agli acquisti del cliente (§4), ma addebita anche qualcosa
di suo: quello che il cliente ha sottoscritto. Gli addebiti vanno **in commessa**, e
dalla commessa in fattura (vedi [Gestione commesse](/guide/gestione-commesse) e
[Fatturazione](/guide/fatturazione)). A mandarli in commessa è il **push dei
contratti**, che gira a ogni giro del push e prende quello che è maturato.

### 4-bis.1 Che cosa si addebita

| Riga del contratto | Si addebita? | A che prezzo |
| --- | --- | --- |
| **ADESIONE** — un articolo del listino che il cliente prende | sì | quello del listino, con la variazione globale |
| **AGGIUNTA** — un articolo fuori listino | sì | quello della riga |
| **OVERRIDE** — il prezzo del cliente per un articolo del listino | **no**, salvo su una quota fissa (sotto) | — |
| **ESCLUSIONE** | no | — |

Due regole da sapere:

* **L'OVERRIDE è solo un prezzo.** Dice quanto paga il cliente *se e quando* compra
  quell'articolo (un preventivo, un ordine). Il contratto non lo addebita da solo:
  altrimenti il cliente lo pagherebbe due volte.
* **Le quote fisse del listino si addebitano da sole.** Una voce del listino di
  tipologia «quota fissa» (canone o quota periodica indipendente dal consumo) la paga
  ogni contratto di quel listino, senza bisogno di una riga: una volta per periodo, con
  la periodicità scritta sulla riga del listino. Il contratto la cambia con una riga
  sua: un OVERRIDE ne cambia il prezzo (e qui l'OVERRIDE si addebita, al posto della
  quota), un'ESCLUSIONE la toglie.

Le altre voci del listino (servizi, prodotti) sono solo prezzi: il cliente le paga se
le prende, cioè con un'ADESIONE.

### 4-bis.2 Una tantum

Una riga **una tantum** si addebita **una volta**, alla data di inizio del contratto,
appena il contratto è attivo.

### 4-bis.3 Il canone

Una riga **a canone** si addebita a periodi. Lo decidono tre dati:

| Dato | Dove sta | Che cosa dice |
| --- | --- | --- |
| **Periodicità** | sulla riga (sulla quota fissa: sulla riga del listino) | mensile, bimestrale, trimestrale, quadrimestrale, semestrale, annuale. Sull'ADESIONE la propone il listino |
| **Mese di partenza** | sulla testata | da quale mese si contano i periodi. Gennaio = il calendario normale (trimestri gen-mar, apr-giu…); febbraio = feb-apr, mag-lug… |
| **Anticipato o normale** | sulla testata; una riga può forzarlo | *anticipato*: il periodo si addebita appena **comincia**; *normale*: appena **finisce** |

Come si calcola il periodo:

* i periodi **cominciano sempre il giorno 1** del mese;
* il periodo **incompleto**, all'inizio o alla fine del contratto, si paga **in
  proporzione**: i mesi interi a mesi, il mese a metà a giorni;
* un periodo che **scavalca il 31 dicembre** si spezza in due righe di commessa, una per
  anno, per la competenza contabile;
* i periodi **arretrati** si recuperano: ogni giro riparte dal giorno dopo l'ultimo
  periodo addebitato, quindi un giro saltato non perde niente.

La quantità del periodo:

* a **quantità fissa**: la quantità della riga, per la parte di periodo addebitata
  (mezzo trimestre = metà);
* a **durata**: il sistema conta i giorni o i mesi del periodo, nell'unità di misura
  dell'articolo. Il periodo incompleto è già dentro.

Il prezzo è quello della riga (OVERRIDE, AGGIUNTA), oppure quello del listino del
contratto **all'inizio del periodo**, con la variazione globale (ADESIONE, quota fissa).

> **Esempio.** Contratto dal 15 febbraio, trimestrale, anticipato, mese di partenza
> gennaio, quota fissa da 100 € a trimestre. Primo giro, a ottobre:
>
> * 15/02 – 31/03: **0,5** trimestre (mezzo febbraio e marzo, su tre mesi) → 50 €;
> * 01/04 – 30/06, 01/07 – 30/09, 01/10 – 31/12: un trimestre ciascuno → 100 € l'uno.
>
> Il giro di novembre non manda niente: il trimestre in corso è già addebitato.

Ogni riga di commessa del canone porta come **mese di competenza** il mese del giro, e
come **periodo** le date del pezzo addebitato.

### 4-bis.4 La cessazione e gli storni

Con il canone anticipato, quando il contratto cessa a metà periodo il periodo è già
stato addebitato per intero. Il push allora **storna la parte non goduta**: una riga
negativa, allo stesso prezzo, per quanto si sarebbe addebitato in meno con la fine
nota. Le righe negative vanno nella fattura successiva.

La data di fine si può cambiare finché il contratto è attivo (§6.1): anticiparla,
spostarla più avanti, toglierla. Lo storno segue: è sempre la **differenza** fra
quanto è dovuto con la fine di oggi e quanto è già stato stornato. Se la fine arretra
si storna ancora, se avanza (o sparisce) si riaddebita quello che era stato stornato in
più. Alla fine il periodo vale sempre quanto varrebbe con un taglio solo, alla data di
fine di oggi.

### 4-bis.5 Che cosa non parte, e dove si vede

Un canone **non parte** se:

* la riga (o la quota fissa del listino) non ha la periodicità;
* è a durata su un'unità di misura che non si conta dal calendario;
* il listino non ha un prezzo alla data del periodo.

Il contratto compare allora nel **Backlog** come anomalia, «Rivedi il contratto»; quello
che ha solo addebiti maturati da mandare compare come «Esegui il push dei canoni» (vedi
[Cruscotti fatturazione §4](/guide/cruscotti-fatturazione)). Le righe sono chiuse fuori
dalla bozza (§6.2): un canone che non può partire su un contratto attivo si risolve fuori
dalla riga, con un contratto nuovo o con il prezzo nel listino.

Le righe **a ore** e **a consumo** non arrivano ancora dal contratto: aspettano le loro
fonti (rendicontazione ore, letture). Il **pacchetto di ore fisse** al periodo è un
canone a quantità fissa sull'unità di misura delle ore.

Dove sta la regola, per chi sviluppa: una funzione sola, che il push e la dashboard
leggono tutti e due —
[`vendite.fn_contratti_addebiti_maturati`](/dbzero/vendite/manual/fn_contratti_addebiti_maturati).
I periodi li calcola [`vendite.fn_canone_periodi`](/dbzero/vendite/funzioni/fn_canone_periodi).

---

## 5. Articoli compositi e BoM

### 5.1 Cosa succede quando aggiungi un composito

Aggiungendo una riga con articolo `is_composito = TRUE` (come OVERRIDE o AGGIUNTA),
il sistema chiama `fn_contratto_riga_componenti_init`:

1. apre il dialog di **anteprima componenti** che pre-popola i prezzi dei figli
   via `fn_contratto_riga_componenti_preview`
2. l'operatore conferma (o modifica i prezzi suggeriti) e salva
3. il backend crea in transazione atomica:
   * una riga padre in `contratti_righe` (OVERRIDE o AGGIUNTA)
   * N righe figlie in `contratti_righe_componenti` (una per ogni figlio attivo
     nella BoM valida alla data del contratto)
4. il trigger DB ricalcola il prezzo padre come SUM(figli × `coeff_qta_snapshot`)

Se la BoM del padre non ha figli validi, il sistema solleva
`E_DOC_COMPOSITO_BOM_VUOTA`.

### 5.2 Composito OVERRIDE vs composito AGGIUNTA

* **OVERRIDE composito**: il padre è un articolo del listino con prezzo personalizzato.
  I figli BoM leggono la BoM del bundle sulla versione listino fissata al contratto.
  Il resolver usa `p_articolo_padre_contesto` per attivare lo STADIO BUNDLE.
* **AGGIUNTA composita**: il padre è un articolo fuori listino aggiunto al contratto.
  Stessa inizializzazione figli, ma il contesto è autonomo (non dipende dal listino).

### 5.3 Cosa può modificare l'operatore

* ✅ **prezzi unitari** dei componenti, con controlli di autorizzazione (gate L1/L2/L3)
* ✅ **IVA** del componente (deve restare coerente col padre)
* ❌ **non** può aggiungere o rimuovere componenti dalla composizione
* ❌ **non** può cambiare `coeff_qta` (snapshot immutabile)
* ❌ **nessuna modifica** dopo l'attivazione (lock post-attivazione)

---

## 6. Dopo la bozza: che cosa si cambia ancora

### 6.1 La testata

Dopo l'attivazione il contratto è un documento firmato: quasi tutto resta com'era.

| Che cosa | In ATTIVO | In CESSATO e ANNULLATO |
| --- | --- | --- |
| data, valuta | fermi | fermi |
| cliente (billing account, istanza) | fermo | fermo |
| utility, azienda che emette | ferme (già in bozza) | ferme |
| listino, versione, variazioni globali, ambito, decorrenza, contratto padre, categoria cliente | fermi | fermi |
| offerta e sorgente da cui nasce | ferme | ferme |
| fine validità (`valido_al`), CIG, CUP, codice commessa, note | **si cambiano** | fermi |

La fine validità si sposta per programmare la cessazione (se un canone anticipato è già
addebitato oltre la data nuova, il push storna o riaddebita la differenza: §4-bis.4); CIG, CUP e codice
commessa arrivano spesso dopo la firma. A contratto cessato o annullato si ferma
tutto. Utility e azienda che emette non si cambiano nemmeno in bozza: in bozza
si cambia il cliente, dentro la stessa utility. Il rifiuto dice quale famiglia
di dati si è toccata (`E_DOC_IDENTITA_FUORI_BOZZA`, `E_DOC_CONDIZIONI_FUORI_BOZZA`,
`E_DOC_CLIENTE_FUORI_BOZZA`, `E_DOC_SORGENTE_FUORI_BOZZA`, `E_DOC_CHIUSO`,
`E_DOC_UTILITY_IMMUTABILE`, `E_DOC_EMITTENTE_IMMUTABILE`). La
regola sta nel montaggio del lock di testata, e da lì la legge anche la
capability del contratto per spegnere i campi nel form. Fino al 10 ottobre 2026 i
quattro dati di pricing li fermava un controllo a parte, solo in ATTIVO
(`E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE`, ritirato).

### 6.2 Righe bloccate

Le righe di un contratto si aggiungono, modificano e tolgono **solo finché il
contratto è in bozza**. Fuori dalla bozza — ATTIVO, ma anche CESSATO e
ANNULLATO — qualsiasi INSERT, UPDATE o DELETE su `contratti_righe` è rifiutato
con `E_RIGA_DOC_NON_BOZZA`. La regola non è dei contratti: è il meccanismo
condiviso «le righe di un documento si toccano solo in bozza»
([`trgfn_doc_righe_lock_fuori_bozza`](/dbzero/vendite/manual/trgfn_doc_righe_lock_fuori_bozza)),
lo stesso di DDT e ordini.

**Conseguenza operativa**: se il cliente rinegozia le condizioni, non si "modifica"
il contratto — si **cessa** quello esistente e si crea un nuovo contratto con le
condizioni aggiornate.

### 6.3 Rimozione listino con eccezioni

Se in DRAFT l'operatore tenta di rimuovere il `listino_id` da un contratto che
ha eccezioni OVERRIDE o ESCLUSIONE, l'API risponde 422 con
`E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI`. Gli OVERRIDE e ESCLUSIONE perdono
significato senza un listino di riferimento. Le AGGIUNTA non bloccano (sono
articoli fuori listino, compatibili con entrambe le forme). Mettere o sostituire
il listino quando ci sono già righe risponde 422 con
`E_DOC_LISTINO_CAMBIO_CON_RIGHE`: le righe sono state caricate contro il listino di
prima. Le due regole le dice il database, e valgono anche per l'offerta.

---

## 7. Gate prezzo (L1 / L2 / L3)

Lo stesso meccanismo dei preventivi si applica agli override/variazioni del
contratto. Un operatore che tenta di inserire un prezzo OVERRIDE (o una
variazione globale) passa per tre gate:

* **L1 — Permesso "variare prezzi"**: se l'utente non ha questo permesso,
  il campo variazione e le azioni di override/esclusione/aggiunta sono
  disabilitati in UI e il BE rifiuta in PATCH.
* **L2 — Soglia**: il delta rispetto al prezzo suggerito dal resolver non può
  eccedere le soglie configurate (cascata parametri: user → categoria_cliente →
  group → emittente → default). Oltre il limite, 403 retryable.
* **L3 — Escalation**: l'operatore può richiedere approvazione al superiore
  tramite pratica `APPROVAZIONE_PREZZO`. La riga / variazione resta `PENDING`
  finché approvata o rifiutata. Il contratto non può essere attivato con
  approvazioni pendenti.

> **Approvazione ereditata dall'offerta.** Se il contratto nasce da un'offerta
> commerciale (push offerta → contratto), lo `stato_approvazione_prezzo` e il
> collegamento alla pratica già presenti sull'offerta sono trasportati **1:1** su
> righe e componenti del contratto: un'approvazione L3 ottenuta in fase di offerta
> **non** va richiesta di nuovo sul contratto.

---

## 8. Workflow end-to-end

### 8.1 Flusso tipico

```text
   ┌──────────────────┐
   │ Nuovo contratto  │
   │ (operatore crea  │
   │  da zero)        │
   └────────┬─────────┘
            │
   ┌────────▼──────────┐      annullamento bozza    ┌─────────────┐
   │      DRAFT        │ ──────────────────────────► │  ANNULLATO  │
   │ Operatore compila │                             │  (terminale)│
   │ testata + utility │                             │ is_abortito │
   │ + eccezioni righe │                             └─────────────┘
   └────────┬──────────┘
            │
            │ Emissione (/emetti/): genera PDF + fissa listino_versione_id
            │               + blocca testata e righe (transazione atomica)
            │
   ┌────────▼──────────┐
   │      ATTIVO       │
   │ Resolver prezzi   │
   │ usa STADIO 1      │
   └────────┬──────────┘
            │
            │ cessazione con la data di oggi, oppure data di fine passata
            │ (chiusura per scadenza); una data futura la programma
            │
   ┌────────▼──────────┐
   │      CESSATO      │
   │ (terminale)       │
   └───────────────────┘
```

### 8.2 Condizioni di attivazione

L'attivazione fallisce (oltre alle guard trigger) se:

* il contratto è in overlap temporale con un altro contratto **vincolante**
  (ATTIVO/CESSATO, cioè **non** DRAFT e **non** ANNULLATO) per la stessa quadrupla
  `(ba, istanza_utility, utility, ambito)` nel periodo `(valido_dal, valido_al)` —
  constraint `ex_contratti_no_overlap` (EXCLUDE USING gist parziale,
  `WHERE partecipa_overlap_snapshot`, colonna GENERATED = `NOT is_abortito AND NOT
  is_draft`). I contratti **DRAFT** (oltre agli ANNULLATO) **non** partecipano al
  vincolo: l'esclusività scatta **solo all'attivazione**, quindi due DRAFT
  sovrapposti — e un DRAFT sovrapposto a un ATTIVO — sono ammessi (abilita la
  preparazione delle bozze di successione). Sulla bozza sovrapposta il pulsante
  «Attiva» è **spento** e dice quale contratto è in conflitto; chi prova comunque
  riceve `E_CONTRATTO_OVERLAP_ESISTENTE`, col numero di quel contratto. La regola
  sta in [`script.fn_check_contratto_sovrapposto`](/dbzero/script/funzioni/fn_check_contratto_sovrapposto),
  e il vincolo di esclusione resta la difesa dura
* il contratto è "negoziato puro" (senza listino) e non ha **almeno una riga
  AGGIUNTA con prezzo valorizzato**
* ci sono approvazioni prezzo PENDING non risolte

---

## 9. Casi d'uso operativi

### 9.1 Cliente con listino standard e sconto globale

1. Crea nuovo contratto → seleziona BA, utility, ambito
2. Sezione Pricing: seleziona il listino → inserisci variazione globale (es. `-5%`)
3. Salva testata in DRAFT
4. Sezione Righe: preview mostra tutti gli articoli del listino con sconto 5% applicato
5. Nessuna eccezione necessaria → clicca **"Emetti"** → si apre il dialog di
   emissione (scelta template + eventuali allegati) → conferma: il sistema genera il
   PDF e **attiva** il contratto nella stessa operazione
6. L'emissione fissa la versione listino corrente — il cliente mantiene i prezzi
   della v5 anche quando viene pubblicata la v6

### 9.2 Cliente VIP con override su articoli specifici

1. Crea contratto con listino (opzionale: variazione globale 0%)
2. Nella vista righe, seleziona articolo → "Modifica prezzo" → inserisci prezzo negoziato
3. L'eccezione viene salvata come `tipo_eccezione = OVERRIDE` in `contratti_righe`
4. Al momento del pricing, il resolver usa quel prezzo; la variazione globale (se presente)
   non viene applicata su quell'articolo
5. Se il delta supera la soglia L2 → gate L3 → pratica approvazione

### 9.3 Cliente senza listino di riferimento (tutto negoziato)

1. Crea contratto **senza** listino (campo vuoto)
2. Nella vista righe, aggiungi articoli uno per uno ("Aggiungi articolo fuori listino")
3. Ogni riga viene salvata come `tipo_eccezione = AGGIUNTA` con prezzo esplicito
4. Tentativo di attivare senza righe → blocco `E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE`
5. Aggiunte almeno le righe necessarie → attivazione OK

### 9.4 Articolo escluso per cliente specifico

1. Contratto con listino già in DRAFT
2. Nella vista righe, seleziona articolo → "Escludi"
3. Riga salvata come `tipo_eccezione = ESCLUSIONE` (prezzo NULL)
4. Da quel momento, il resolver per quel BA + articolo solleva
   `E_ARTICOLO_ESCLUSO_DA_CONTRATTO` invece di restituire un prezzo

### 9.5 Condizioni rinegozia­te post-attivazione

Il contratto attivo è blindato: nessun campo è modificabile.

1. Cessa il contratto corrente (data cessazione = oggi o data concordata)
2. Crea un nuovo contratto DRAFT con le condizioni aggiornate
3. Attiva il nuovo contratto

Non esiste "modifica" di un contratto attivo. Il nuovo contratto sostituirà il
vecchio quando `valido_dal` del nuovo coincide con la cessazione del vecchio.

### 9.6 Kit composto (articolo bundle) in contratto

1. Nella vista righe aggiungi un articolo con `is_composito = TRUE`
2. Si apre il dialog componenti con prezzi pre-popolati (resolver bundle-aware)
3. Conferma (o modifica prezzi figli con eventuale approvazione L3)
4. La riga padre è salvata come AGGIUNTA o OVERRIDE; i figli in
   `contratti_righe_componenti`; il prezzo padre è ricalcolato automaticamente

---

## 10. Errori principali

Codici sollevati dal dominio contratti (registrati in `config.messaggi_errore`):

| Codice                                         | ID  | HTTP | Quando                                                                                                                   |
| ---------------------------------------------- | --- | ---- | ------------------------------------------------------------------------------------------------------------------------ |
| `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO`          | 450 | 422  | AGGIUNTA su articolo già presente nel listino fissato — usare OVERRIDE                                                   |
| `E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE`       | 451 | 422  | Attivazione contratto senza listino e senza almeno una riga AGGIUNTA con prezzo valorizzato                              |
| `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE`  | 452 | 422  | ⛔ Ritirato il 2026-10-10: il pricing di un contratto fuori bozza lo ferma `E_DOC_CONDIZIONI_FUORI_BOZZA` (§6.1)         |
| `E_ARTICOLO_ESCLUSO_DA_CONTRATTO`              | 453 | 422  | Resolver chiede prezzo per articolo con ESCLUSIONE attiva                                                                |
| `E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI`  | 454 | 422  | ⛔ Ritirato il 2026-10-11: ora `E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI` (§6.3), comune a contratto e offerta              |
| `E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA` | 455 | 422  | ESCLUSIONE su un articolo che è componente (figlio) di un bundle del listino — escludere il padre bundle                 |
| `E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO` | 1201 | 409 | Attivazione di un contratto con listino che non ha una versione in vigore oggi (il DB congela la versione all'attivazione). In DRAFT il listino si sceglie comunque |
| `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C`      | —   | 422  | Contratto senza listino e nessuna eccezione per l'articolo                                                               |
| `E_OFFERTA_ORDINE_GIA_GENERATO`                | 478 | 409  | Push offerta → contratto quando l'offerta ha già generato un **ordine** (mutua esclusività XOR)                          |
| `E_OFFERTA_CONTRATTO_GIA_GENERATO`             | —   | 409  | Push offerta → contratto già generato (idempotenza)                                                                      |
| `E_DOC_COMPOSITO_BOM_VUOTA`                    | —   | 400  | Composito senza figli BoM validi alla data del contratto                                                                 |

> **Nota.** `E_LISTINO_VERSIONE_NON_ATTIVA` (id 448, HTTP 404) **non** è l'errore di
> attivazione contratto: è un errore di runtime del **resolver di pricing**
> (`fn_resolve_prezzo_listino_v2`), sollevato quando un listino determinato non ha
> una versione attiva alla data di riferimento. Per il contratto, l'errore corretto
> è `E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO` (sopra). Il vecchio
> `E_CONTRATTO_LISTINO_SENZA_VERSIONE_ATTIVA`, che impediva di scegliere il listino, è
> ritirato dal 2026-10-07.

---

## 11. Pattern e principi di design

### 11.1 Il contratto come delta del listino

Il contratto non importa le righe del listino: nella tabella `contratti_righe`
vivono **solo le eccezioni**. Il listino è un riferimento esterno letto in runtime
dal resolver. Questo mantiene la tabella snella e la semantica delle righe sempre
chiara: se una riga esiste, è un'eccezione intenzionale.

### 11.2 Snapshot della versione e immutabilità

La fissazione di `listino_versione_id` all'attivazione è l'equivalente contrattuale
degli snapshot riga-per-riga dei preventivi: la fotografia dei prezzi viene congelata
al momento della firma. La versione listino, già immutabile per design
(`valido_dal/valido_al` non modificabili sulle righe), garantisce che il contratto
non risenta di modifiche future al catalogo prezzi.

Parallelo con i preventivi:

| Artefatto  | Snapshot di                                                | Destinazione                     |
| ---------- | ---------------------------------------------------------- | -------------------------------- |
| Preventivo | Prezzo riga-per-riga (materializzato in `prezzo_unitario`) | Commessa → fattura una tantum    |
| Contratto  | Versione listino (snap di `listino_versione_id`)           | Pipeline fatturazione ricorrente |

### 11.3 Trigger DB come ultima difesa

I lock post-attivazione, il guard negoziato puro, il guard AGGIUNTA-già-in-listino
sono trigger DB: anche se il backend non fa le verifiche, il DB rifiuta. Il backend
ha controlli equivalenti per messaggi di errore parlanti prima del roundtrip, ma la
fonte di verità è sempre il trigger.

### 11.4 BoM modello cross-dominio

Lo stesso modello componenti BoM (`*_righe_componenti`) è condiviso tra preventivi,
contratti, ordini e ddt. Guards, trigger di ricalcolo padre e UI del dialog componenti
sono gli stessi in tutti i domini. Vedi [modello componenti BoM](/dev/manual/modello-componenti-bom).

---

## 12. Glossario rapido

| Termine                      | Significato                                                                                                         |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **Contratto**                | Relazione commerciale duratura con un BA per una utility. Stato DRAFT → ATTIVO → CESSATO (oppure DRAFT → ANNULLATO) |
| **ANNULLATO**                | Bozza annullata prima dell'attivazione. Stato terminale con `is_abortito = true`. Non partecipa al check di overlap |
| **Forma derivata**           | "Con listino" / "Senza listino" — derivata dai dati, non scelta dall'operatore                                      |
| **OVERRIDE**                 | Eccezione di riga: prezzo personalizzato per articolo del listino. Variazione globale non si applica                |
| **ESCLUSIONE**               | Eccezione di riga: articolo del listino non disponibile per il cliente                                              |
| **AGGIUNTA**                 | Eccezione di riga: articolo fuori listino aggiunto al contratto                                                     |
| **ADESIONE**                 | Eccezione di riga: articolo del listino che il cliente prende, al prezzo del listino. Si addebita                   |
| **Quota fissa**              | Voce del listino a canone che ogni contratto del listino paga da sé, a periodi, salvo un'eccezione che la cambia     |
| **Storno del canone**        | Riga negativa che restituisce la parte di un canone anticipato non goduta dopo la cessazione                        |
| **Versione listino fissata** | `listino_versione_id` snapshot all'attivazione. Il contratto legge sempre quella versione                           |
| **Drift listino**            | In DRAFT, se esce una nuova versione del listino mentre si lavorano le eccezioni, il banner UI avverte              |
| **Lock post-attivazione**    | Da ATTIVO in poi, testata e righe sono immutabili — trigger DB enforced                                             |
| **Negoziato puro**           | Contratto senza listino: tutte le righe sono AGGIUNTA, nessun listino di riferimento                                |
| **STADIO 1**                 | Posizione del contratto nella cascata del resolver pricing v5 (dopo promo, prima di categoria)                      |
| **L1/L2/L3**                 | Livelli di autorizzazione pricing: Permesso / Soglia / Workflow approvazione                                        |

---

## Nota — Il collegamento offerta commerciale → contratto

Storicamente il ciclo di vita del contratto aveva un **inizio non tracciato**: il
contratto nasceva direttamente dall'operatore in DRAFT, senza un documento precedente
che formalizzasse la proposta di condizioni al cliente. Quel collegamento mancante è
ora **implementato**: è l'**offerta commerciale** — una proposta di condizioni quadro
(listino + variazione + eccezioni proposte) distinta dal preventivo (che è invece una
proposta di transazione puntuale).

➡️ Vedi la guida dedicata: [Gestione Offerte commerciali](/guide/gestione-offerte-commerciali).

Il parallelo nel modello:

| Proposta                          | Accettazione genera              | Tipo di fornitura             |
| --------------------------------- | -------------------------------- | ----------------------------- |
| **Preventivo** (`PRV-*`)          | Commessa → fattura               | Transazione puntuale          |
| **Offerta commerciale** (`OFC-*`) | Contratto in DRAFT → attivazione | Relazione ricorrente duratura |

Perché i due documenti esistono separati e non si usa il preventivo come proposta di
contratto? Il preventivo è una fotografia riga-per-riga a un dato istante (snapshot
materializzato, articoli + quantità + prezzi specifici). L'offerta commerciale è una
proposta di **condizioni quadro** (listino + variazione + delta), e il suo "snapshot"
è la versione del listino — la stessa struttura del contratto. La simmetria del modello
implica che i due artefatti abbiano snapshot strutturalmente diversi, e usare il
preventivo come offerta commerciale sarebbe una forzatura semantica.

L'offerta è stata realizzata come **entità separata** `offerte_commerciali` con flusso
`fn_push_offerta_a_contratto` (legame 1:1, idempotente): l'offerta accettata genera un
contratto DRAFT che ne eredita 1:1 le condizioni. Il dettaglio è nella guida sopra.

> **Contratto OPPURE ordine — mai entrambi (XOR).** Da un'offerta ACCETTATA si genera
> al massimo *uno* tra contratto (fornitura ricorrente) e ordine (vendita puntuale).
> Se l'offerta ha già generato un ordine, il push a contratto fallisce con
> `E_OFFERTA_ORDINE_GIA_GENERATO`; specularmente, la generazione di un ordine su
> un'offerta che ha già un contratto fallisce con `E_OFFERTA_CONTRATTO_GIA_GENERATO`.
> Resta valida l'idempotenza (un secondo push dello stesso contratto fallisce con
> `E_OFFERTA_CONTRATTO_GIA_GENERATO`).

*Per il dettaglio tecnico delle API REST, formati payload e codici errore vedi
[API Contratti](/backend/vendite/manual/api_contratti). Le decisioni di modello
del refactor sono recepite nelle sezioni precedenti e nella documentazione backend
di dominio.*

---
{% include-markdown "signature-core.md" %}
