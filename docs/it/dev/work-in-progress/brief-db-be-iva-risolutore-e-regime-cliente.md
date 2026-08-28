# Brief DB/BE — l'IVA non ha un risolutore: l'articolo decide da solo, e il regime del cliente è scritto e mai letto

> **Destinatario:** team DB (`dev/db-tid`) per le voci 1 e 3, backend per la 2.
>
> **Origine.** Domanda di Tid del 2026-08-27, durante il collaudo della prova 9 di
> [collaudo-in-app-ddt-righe-senza-prezzo.md](../work-done/collaudo-in-app-ddt-righe-senza-prezzo.md):
> *«nel caso ad esempio di omaggio o anche di reverse charge l'IVA non discende
> più dall'articolo, è giusto che possa essere modificata o no?»*.
>
> Il caso da cui è partita — una riga di ri-consegna senza aliquota — è
> l'inciampo, non il tema: quello sta in
> [brief-db-ddt-riconsegna-eredita-testata.md](../work-done/brief-db-ddt-riconsegna-eredita-testata.md).
> Cercando la risposta è emerso che **l'IVA, in questo progetto, la decide
> l'articolo e nessun altro** — e che le colonne dove vive il regime fiscale del
> cliente sono compilate dall'operatore e lette da nessuno.
>
> **Stato.** 2026-08-27 — analisi sulla **struttura**: corpo delle funzioni,
> colonne, whitelist del backend, template del frontend. Nessuna misura sui dati,
> nessun file scritto, nessuna migrazione.
>
> ⭐ **Due decisioni di dominio già prese** (Tid, 2026-08-27) e **una ancora
> aperta**: sono nel §D, etichettate una per una. Le decise non vanno ri-discusse
> a valle; l'aperta **blocca** la richiesta `I6` e nient'altro.
>
> **Correlati:**
> [config.iva](/dbzero/config/tabelle/iva) ·
> [anagrafiche.clienti](/dbzero/anagrafiche/manual/clienti) ·
> [fn_get_iva_override](/dbzero/script/funzioni/fn_get_iva_override) ·
> [trgfn_ddt_guard_causale_emissione](/dbzero/vendite/funzioni/trgfn_ddt_guard_causale_emissione) ·
> [causali_trasporto §fatturabile](/dbzero/config/manual/causali_trasporto)

---

## 0. Le quattro voci in una riga

| # | Cosa | Gravità | Chi lo vede oggi |
| --- | --- | --- | --- |
| **1** | L'IVA si determina in **due punti indipendenti** (riga di documento, riga di fattura) e in entrambi **dal solo articolo**. Uno dei due è nel **frontend** | 🔴 il numero fiscale di una riga non ha una sede | nessuno: finché tutti i clienti sono a regime ordinario i due valori coincidono |
| **2** | `clienti.iva_id` (**`NOT NULL`**), `clienti.split_payment`, `clienti.cliente_pa`: l'operatore li compila nel drawer, **nessun documento li legge** | 🔴 un campo che promette una cosa che non succede | chi imposta un cliente in reverse charge e ritrova l'aliquota ordinaria in fattura |
| **3** | Il gate all'emissione del DDT pretende il **prezzo** e non l'**aliquota** | 🟠 piccolo, ed è quello che chiude il collaudo | chi emette un DDT con una riga senza IVA: esce, e il riepilogo è muto |
| **4** | La **dichiarazione d'intento** non ha nessuna sede: la natura `N3.5` è seminata e **orfana** — nessun codice IVA la usa, nessuna tabella tiene protocollo, validità e plafond | 🔴 un titolo di non imponibilità che il sistema non sa rappresentare | chi vende a un esportatore abituale: oggi non ha nessuna strada |

⭐ **Cosa hanno in comune**: sono lo stesso buco visto da tre distanze. Il prezzo
ha un risolutore centralizzato e una memoria che ne vieta gli scavalcamenti
(`feedback_pricing_centralizzato`); l'IVA — l'**altro** numero di una riga
fiscale — non ha niente.

---

## D. Decisioni e questioni aperte — 2026-08-27

> Stanno qui in testa perché ognuna delle richieste del §5 discende da una di
> esse, e perché una decisione che vive solo dentro una conversazione viene
> ri-aperta al primo dubbio.
>
> ⚠️ **Ognuna dice di chi è.** `D2` e `D3` sono **decisioni di Tid**, prese a
> parole il 2026-08-27. `D1` è **aperta**: c'è la proposta e l'argomento, non
> c'è la decisione. `D4` non è una decisione affatto — è una constatazione
> tecnica. Attribuire a qualcuno una scelta che non ha fatto è il modo in cui un
> documento diventa inaffidabile, e qui non serve nemmeno: l'argomento regge da
> sé anche senza una firma sotto.

### D1 · ❓ **APERTA** — l'IVA di riga è modificabile a mano o no?

**Proposta: no**, su nessun documento. Varrebbe per **DDT, ordini e preventivi**
— le tre sedi che hanno una riga con aliquota — sia in CREATE che in EDIT: il
valore lo produce il risolutore (**D2**), l'operatore non lo digita e non lo
corregge.

**L'argomento a favore, ed è il cuore di tutto il brief**: *l'IVA non è una scelta, è una
conseguenza*. Qui sta la differenza col **prezzo**, che invece è editabile a
ragion veduta — un prezzo si **negozia**, e infatti chi lo scavalca passa dal
workflow di approvazione L1/L2. L'IVA non si negozia con nessuno: si applica. Un
campo digitabile inviterebbe ad «aggiustare» un dato che dipende dalla legge, e
lo farebbe **senza traccia e senza approvazione**, perché per l'IVA un workflow
di scostamento non ha nemmeno senso.

⚠️ **Ma «non modificabile» è corretto solo se il valore c'è ed è giusto.** Oggi
il blocco c'è (`:disabled="isEdit"` nei tre form) e blocca ciò che ha detto
l'articolo: su un cliente fuori regime ordinario blocca un valore **sbagliato**
che nessuno può correggere, e su una riga generata dal DB blocca un **buco**.
Bloccare un buco non protegge una scelta, la impedisce. Per questo D1 **non è
applicabile prima** di D2: vedi l'avvertenza sull'ordine in `I6`.

⭐ **L'argomento contro, e va guardato prima di decidere**: esistono casi in cui
la controparte comunica il proprio titolo **sull'operazione singola** e non sul
rapporto — una dichiarazione d'intento che copre un plafond, un'operazione
occasionale fuori regime. Se quei casi si modellano (una dichiarazione d'intento
è un documento con validità e importo, non un flag), allora restano dentro il
risolutore e D1 regge; se non si modellano, l'unica uscita per l'operatore
sarebbe proprio la casella che D1 chiude. **La domanda da decidere non è «bloccare
sì o no», è «il risolutore arriverà a coprire tutti i titoli, o ne resta fuori
qualcuno?»** — e finché la risposta non c'è, bloccare significa scegliere di non
avere un'uscita.

⭐ **Aggiornamento in giornata**: la dichiarazione d'intento — che era proprio il
caso che sembrava non copribile — ha una sua forma modellabile, ed è il **§2.6**.
Se quella strada si prende, l'argomento contro cade e `D1` può essere decisa
«non modificabile». Resta da verificare che non ci siano **altri** titoli
per-operazione fuori dal risolutore: è quello, e solo quello, che tiene `D1`
ancora aperta.

⚠️ **E oggi il blocco è una convenzione del solo frontend.** Il backend
l'aggiornamento dell'IVA lo accetta: `iva_id` è dentro `_UPDATE_KEYS_RIGA` in
`ddt_service.py`. Una regola presidiata da un `:disabled` in un template non è
una regola — è un suggerimento che chiunque chiami l'endpoint scavalca.

### D2 · ✅ **DECISA (Tid)** — quando cliente e articolo divergono, **vince il cliente**

La ragione sta sul modello, non sulla preferenza: *l'articolo dichiara la natura
merceologica* — cosa è quella merce, e quindi quale aliquota le compete in via
ordinaria. *Il cliente dichiara il regime* — in che rapporto fiscale è quella
controparte con chi vende (esente art. 8, reverse charge, PA in scissione dei
pagamenti). Il regime è una proprietà del **rapporto**, e un rapporto vince su
una classificazione merceologica perché la modifica **per legge**, non per scelta.

### D3 · ✅ **DECISA (Tid)** — un'aliquota assente, **dove serve il prezzo**, è un errore, non un'annotazione

Rilievo di Tid: *«l'IVA deve esserci sempre, se non indicata deve andare in
errore — forse solo se il prezzo è null, IVA null»*. La condizione è **la stessa**
del prezzo e la dichiara la stessa causale: dove la merce si vende servono
entrambi, dove non si vende non serve nessuno dei due. Realizzazione nel §3.

⛔ **Opzione scartata, ed era mia**: un Tag «Senza IVA» nella lista righe, sul
modello del «Senza prezzo» della DEC-6. Sbagliata, e la differenza è netta — il
prezzo **può legittimamente mancare** (DDT di solo trasporto: il Tag distingue
«non si applica» da «me ne sono dimenticato», ed è per quello che esiste),
l'aliquota su un documento che vende **no**. Rendere elegante la vista di uno
stato che non deve esistere è il modo di farlo sopravvivere.

### D4 · 📌 **Constatazione, non decisione** — `split_payment` e `cliente_pa` non sono un codice IVA

La scissione dei pagamenti non cambia l'aliquota: cambia **chi versa l'imposta
all'erario**, e in fattura elettronica è l'`EsigibilitaIVA`. Restano **fuori** dal
risolutore e viaggiano sulla testata della fattura e nel payload SDI (`I5`).
Confonderli farebbe nascere codici IVA fasulli a catalogo — e un codice fasullo,
una volta seminato, se lo porta dietro ogni documento emesso.

### D5 · ✅ **APPROVATA (Tid)** — il consumo del plafond è un **registro di movimenti**, non un numero sovrascritto

`imponibile_utilizzato` resta la colonna memorizzata che `P3` chiede, ma è la
**somma di un registro**: ogni fattura, ogni nota di credito e ogni **forzatura
manuale** è una **riga**, con motivo, autore e data. Dettaglio e ragioni nel
**§2.6.2**.

⭐ La ragione per cui non poteva restare un numero: una colonna memorizzata *e*
forzabile a mano diverge in silenzio da ciò che rappresenta, e su un plafond quel
numero è precisamente ciò che l'Agenzia delle Entrate verifica. Una forzatura che
sovrascrive non lascia traccia del **perché**; una forzatura che è una riga **è**
la traccia.

### D6 · ✅ **DECISA (Tid)** — il risolutore ha **due stadi**, e la cascata è solo sul primo

Sotto la parola «regime» convivevano due meccanismi che rispondono a domande
diverse: **quale aliquota compete alla merce** (varia per utility perché varia la
**merce**) e **se la controparte ha un titolo che la sostituisce** (della partita
IVA). Non competono, quindi non c'è nessuna precedenza da invertire. Forma
completa nel **§2.7**.

---

## 1. Il fatto: due determinazioni, un solo ingrediente

### 1.1 Dove nasce l'IVA di una riga di documento

Nel **frontend**, in `DdtRigaForm.vue` (e nei gemelli ordini/preventivi):

```js
function onArticoloSelect(item) {
  ...
  // Auto-fill IVA dall'articolo (sovrascrivibile prima del save).
  if (item.iva_id != null) form.value.iva_id = item.iva_id
}
```

Il backend l'accetta e basta: `iva_id` è in `_CREATE_KEYS_RIGA` **e** in
`_UPDATE_KEYS_RIGA` (`ddt_service.py`), senza nessuna validazione di merito.

⛔ È logica di dominio fiscale che vive in un componente Vue, contro il *«zero
logica business nel frontend»* di `AGENTS.md`. E il campo è `:disabled="isEdit"`,
cioè la regola «non si cambia dopo» è **una convenzione del solo template**: chi
chiama l'endpoint la scavalca senza accorgersene.

### 1.2 Dove nasce l'IVA di una riga di fattura — e **non** è quella di sopra

La riga di fattura **non legge** l'IVA del documento: la rilegge dall'articolo.
In `pipeline_repository.py`, la proiezione delle attività da raggruppare dice

```sql
art.iva_id
```

e `vendite.attivita_fatturabili` una colonna IVA **non ce l'ha proprio**: il
valore non transita nella catena, viene ri-preso a valle.

⚠️ **Conseguenza pratica, ed è il motivo per cui questo difetto è invisibile**:
oggi i due valori coincidono *per costruzione*, perché la sorgente è la stessa.
Il giorno che una delle due strade impara qualcosa che l'altra non sa, divergono
su documenti già emessi. È esattamente la forma già incontrata e scritta in
`fatture_righe_service.py` per prezzo e sconto delle rettifiche:

> *«Oggi i due valori COINCIDONO per costruzione, ed è precisamente il motivo per
> cui prendere quello dell'attività non darebbe nessun sintomo: si vedrebbe solo
> il giorno in cui divergono, su documenti già emessi.»*

### 1.3 ⭐ Il confronto che rende evidente il buco

| | Prezzo | IVA |
| --- | --- | --- |
| Risolutore | `PricingService` / `fn_resolve_prezzo_listino_v2` | **nessuno** |
| Catena | listino → contratto → promo → override | articolo |
| Dove gira | DB, chiamato dal BE | **frontend**, e di nuovo nel BE a valle |
| Scavalcabile? | no — `feedback_pricing_centralizzato` lo vieta | non c'è niente da scavalcare |
| Modificabile a mano? | sì, ed è **giusto**: un prezzo si negozia, e infatti esiste il workflow di approvazione L1/L2 | — |

⭐ **E qui sta la risposta alla domanda che ha aperto il brief.** Il prezzo è
editabile perché è una **scelta**, e una scelta che scavalca la catena passa da
un'approvazione. L'IVA non è una scelta: è una **conseguenza**, e non si negozia
con nessuno. Quindi il campo resta **bloccato** — ma «bloccato» è corretto solo
se blocca un valore **calcolato**. Oggi blocca ciò che l'articolo ha detto, e per
un cliente fuori regime ordinario blocca un valore **sbagliato** che nessuno può
correggere.

---

## 2. 🔴 La catena che manca

### 2.1 L'errore da non fare: pensare che il reverse charge sia «un'aliquota diversa»

In questo modello un'inversione contabile o un'esenzione **non sono un'aliquota
sovrascritta**: sono un **codice IVA a sé** in `config.iva`, con `aliquota_iva = 0`
più `natura_iva_id` o `assoggettamento_id`. Lo impone il CHECK
`chk_iva_zero_requires_natura_or_assogg`, ed è la ragione per cui
`formatIvaLabel` lato FE può mostrare il codice parlante (`N1`, `ESENTE17`) al
posto di uno `0%` muto.

> Quindi la domanda giusta non è *«l'operatore può cambiare l'aliquota?»* ma
> **«chi sceglie il codice IVA, e l'articolo ha l'ultima parola?»**.

### 2.2 E l'omaggio non è un caso di IVA

`OMAGGIO` è già modellato, e a un altro livello: è una **causale di trasporto**
con `fatturabile = false`. Il manuale delle causali lo dice per esteso — *«i casi
ambigui — l'omaggio, che qualcuno fattura a sconto 100% — si risolvono cambiando
una cella di seed»*. Un documento che dichiara di non vendere non ha bisogno né
di prezzo né di aliquota. **Nessuna richiesta in questo brief lo riguarda**: si
cita perché era nella domanda di partenza e la risposta è «già fatto, altrove».

### 2.3 ⭐ Chi vince: il cliente

Decisione **D2**, con il suo argomento: non si ripete qui per non avere due sedi
della stessa regola che invecchiano separate.

### 2.4 Gli ingredienti

> ⚠️ **La *forma* del risolutore è nel §2.7** (`D6`: due stadi, cascata solo sul
> primo, ritorno a ripartizione). Qui ci sono i soli **ingredienti**, cioè le
> sedi che esistono già e che nessuno legge — la ragione per cui questo brief
> parla di anelli mancanti e non di cose da inventare.

* **articolo** — `catalogo.articoli.iva_id`: la proposta ordinaria dello
  **stadio A**;
* **fornitura** — l'anello dello stadio A che oggi non esiste da nessuna parte:
  l'uso della fornitura (gas domestico vs altri usi) non ha una sede. Vedi §2.7.2;
* **cliente / soggetto** — `anagrafiche.clienti.iva_id`, che è **`NOT NULL`**: una
  IVA di cliente c'è **sempre**, non è un caso da gestire. È l'anello che oggi
  manca del tutto. ⚠️ La sua **sede** è però in discussione (§2.6.3): la colonna
  sta su una riga per istanza di utenza, mentre `D6` colloca il titolo sul
  **soggetto**;
* **titolo documentato** — `anagrafiche.soggetti_intento` (§2.6), lo **stadio B**:
  da costruire, con la natura `N3.5` che è già a seed e orfana;
* **stato** — `script.fn_get_iva_override(codice_iva, stato_id)` +
  `config.iva_stati`: esiste già, e nella catena vendite non la chiama nessuno.

⚠️ **`split_payment` e `cliente_pa` NON sono un codice IVA e non entrano nel
risolutore.** La scissione dei pagamenti non cambia l'aliquota: cambia **chi versa
l'imposta all'erario**, e in fattura elettronica è l'`EsigibilitaIVA`, non una
natura. Sono un secondo esito, che viaggia sulla testata della fattura e nel
payload SDI. Confonderli farebbe nascere codici IVA fasulli.

### 2.5 ⚠️ Due avvertenze per chi scriverà

1. **La sede del risolutore è UNA.** Se il DB lo espone e il BE lo chiama ma il
   frontend continua a fare il suo `onArticoloSelect`, ci saranno *due* risposte
   diverse alla stessa domanda — cioè il difetto di oggi con un pezzo in più.
   L'auto-fill nel form va **sostituito** da una chiamata al risolutore, non
   affiancato.
2. **Cambia il comportamento delle fatture esistenti**, perché la riga di fattura
   smette di leggere `art.iva_id`. È un breaking change dichiarato, e in questo
   progetto è ammesso (`project_no_produzione_solo_sviluppo`) — ma va **detto**,
   non scoperto.

### 2.6 🔴 La dichiarazione d'intento — `anagrafiche.soggetti_intento`

Richiesta di Tid, 2026-08-27: *«serve una tabella specifica dove si salvano le
informazioni della dichiarazione d'intento con data inizio e fine validità e il
plafond; se i valori sono validi si "sovrascrive" il codice IVA con quello del
plafond, per il tetto valido»*. **Nome deciso: `anagrafiche.soggetti_intento`.**

#### 2.6.1 Cosa c'è oggi

* ⛔ **Nessuna tabella**: `dichiarazioni_intento`, `plafond` o equivalenti non
  esistono in nessuno schema;
* ✅ **`config.iva_natura` ha già `N3.5`** (id 8) — *«non imponibili - a seguito di
  dichiarazioni d'intento»*, seminata dal 2025;
* ⛔ **e nessun `config.iva` la usa**: dei 14 codici a seed, **zero** hanno
  `natura_iva_id = 8`. La natura è **orfana**.

⭐ Qualcuno, tempo fa, ha seminato la natura giusta. Manca tutto il resto — il
codice IVA che la porta, la tabella che dice quando si applica, il risolutore che
la sceglie. È il segno che la direzione era già stata vista, non che il caso sia
nuovo.

#### 2.6.2 ✅ Le decisioni di Tid (2026-08-27)

Un plafond non è un predicato come una finestra di validità: è un
**accumulatore**, e ogni fattura ne mangia un pezzo. Le domande che ne discendono
sono state poste e **risolte tutte**.

| # | Domanda | ✅ Decisione |
| --- | --- | --- |
| **P1** | Quando si consuma: fattura o DDT? | **La fattura, assolutamente.** Il DDT *simula e applica*, ma in fattura **va rifatto**. Vale per **tutti** i documenti a monte |
| **P2** | Documento che supera il residuo | **Si spezza**: non imponibile fino a capienza, il resto ad aliquota ordinaria |
| **P3** | Residuo calcolato o memorizzato | **Memorizzato** — ed è un nodo voluto: serve a poterlo **ridurre manualmente** (forzatura) quando esistono fatturazioni fuori dal sistema. ✅ Realizzato col registro di `D5` |
| **P4** | La nota di credito restituisce plafond? | **Sì.** ⭐ E si memorizza l'**imponibile già applicato**, non il residuo: è verificabile direttamente, e il residuo è aritmetica (`plafond − imponibile`). ✅ Realizzato col registro di `D5` |
| **P5** | Il protocollo arriva in fattura e nell'XML? | **Sì, anche in XML** |
| **sede** | A chi appartiene | **Al soggetto, senza dubbio** |

##### ⭐ P1 è un principio, non un dettaglio: **il documento a monte proietta, la fattura decide**

*«Il documento fiscale è legge; il DDT simula e applica, ma poi nella fattura va
rifatto.»* Ha due conseguenze che vanno scritte perché cambiano il codice:

1. **L'IVA di una riga di DDT/ordine/preventivo è una proiezione, non un fatto.**
   Serve a far vedere all'operatore che cosa verrà applicato, e al riepilogo IVA
   del documento. Non è il valore che finirà in fattura;
2. ⛔ **quindi il valore NON si trasporta a valle**: l'alternativa che avevo messo
   in `I4` — *«o l'IVA entra nella catena `attivita_fatturabili` e viaggia»* — è
   **esclusa per decisione**. La fattura ri-risolve. Oggi in effetti *ri-fa* già
   (rilegge `art.iva_id`), solo che ri-fa **con l'ingrediente sbagliato**: il
   difetto non è che ricalcoli, è **che cosa** legge per ricalcolare.

##### ⚠️ P3 + P4: quello che memorizzo è un accumulatore, e un accumulatore forzabile ha bisogno di un registro

Le due risposte insieme dicono una cosa precisa: la colonna da tenere è
**`imponibile_utilizzato`**, non `residuo`. Giusto, ed è la scelta più
verificabile — quel numero si confronta con la somma degli imponibili fatturati,
mentre un residuo si confronta con niente.

⛔ **Ma un numero memorizzato *e* forzabile a mano diverge in silenzio da ciò che
dovrebbe rappresentare**, ed è la forma esatta di `feedback_duplicazione_nasconde_il_bug`:
due sorgenti della stessa verità, e nessuna delle due sa di essere sbagliata.
Su un plafond il costo non è un numero storto in una lista — è il dato che
l'Agenzia delle Entrate **verifica**.

⭐ **✅ APPROVATA da Tid il 2026-08-27** (`D5`): non una colonna che si
sovrascrive, ma un **registro di movimenti** —
`anagrafiche.soggetti_intento_movimenti`:

| Movimento | Segno | Da dove |
| --- | --- | --- |
| fattura emessa sotto la dichiarazione | `+` | riga di fattura |
| nota di credito | `−` | riga di rettifica (**P4**) |
| **forzatura manuale** | `±` | operatore, con **motivo obbligatorio** |

`imponibile_utilizzato` resta la colonna memorizzata che **P3** chiede — ma è la
somma del registro, non un numero scritto sopra a un altro. Si guadagnano tre
cose che la colonna nuda non dà: la forzatura ha un **motivo, un autore e una
data**; il consumo è **algebrico** senza casi speciali per la NC; e la riconcilia-
zione col fatturato è una query, non un'indagine.

⚠️ È lo stesso schema che il progetto usa già in due punti: il ponte
`resi_righe_riconsegne` e le rettifiche di `vw_partite_merce`, dove *«il fatturato
somma anche le RETTIFICHE, negative o zero»*. Non è un pattern nuovo da inventare.

#### 2.6.3 ✅ La sede: il soggetto — e il rilievo che ne discende

Deciso: **appartiene al soggetto**. Che è anche l'unica risposta che regge sul
modello — la dichiarazione è della **partita IVA**, e un esportatore abituale con
tre forniture ha **una** dichiarazione, non tre.

⛔ Il motivo per cui la domanda andava posta: `anagrafiche.clienti` è **una riga
per istanza di utenza** (`UNIQUE uq_clienti_istanza_utility`). Agganciarci la
dichiarazione l'avrebbe moltiplicata per il numero di forniture, e tre copie
hanno **tre plafond che si consumano separatamente**: il tetto sarebbe diventato
il triplo di quello vero, in silenzio.

⚠️ **E lo stesso rilievo investe `clienti.iva_id`, cioè la catena di `D2`.** Se il
regime fiscale è del soggetto — e la decisione appena presa dice di sì — allora
una colonna di regime su una riga per istanza è nella sede sbagliata: due istanze
dello stesso soggetto possono oggi dichiarare regimi diversi e niente lo impedisce.
Un'**aliquota** diversa per utility è legittima (la porta l'articolo); un
**regime** diverso per fornitura dello stesso soggetto no.

> **Resta al team DB** una sola domanda, e decide se `I2` tocca anche `clienti`:
> `clienti.iva_id` è nato per essere *«il regime fiscale del cliente»* o
> *«l'aliquota di default di questa fornitura»*? Il modello concettuale la mette
> accanto a `cliente_pa` e `split_payment` e scrive `iva ||--o{ clienti : vat_of`,
> il che suggerisce la prima — e allora è una **migrazione** verso
> `soggetti_ruoli`, non solo una lettura in più.

#### 2.6.4 La forma proposta della tabella

Da leggere come **punto di partenza**, non come DDL: la sede delle definizioni è
il team DB.

* `anagrafiche.soggetti_intento` — soggetto (o `soggetto_ruolo_id`, secondo la
  risposta del §2.6.3), **protocollo** e **data di ricezione** dell'Agenzia
  (**P5**: viaggiano fino all'XML), `validita` come **`daterange`** — la
  convenzione del progetto dal 2026-04, non due colonne date sciolte —
  `plafond` (imponibile massimo), `iva_id` del codice non imponibile da applicare,
  `imponibile_utilizzato` (**P3/P4**), `attivo`, audit `data_*`/`user_*`, `tx_id`;
* `anagrafiche.soggetti_intento_movimenti` — il registro del §2.6.2;
* **un codice `config.iva` nuovo** con `natura_iva_id = 8`, che oggi non esiste:
  senza, la natura resta orfana e il risolutore non ha niente da restituire;
* ⚠️ **guard di non sovrapposizione**: due dichiarazioni valide contemporaneamente
  sullo stesso soggetto rendono la scelta del risolutore ambigua — e
  un'ambiguità che dipende dall'ordine degli id è precisamente ciò che
  `AGENTS.md` chiama *«un'ambiguità del modello, non una scelta»*. `daterange` +
  `EXCLUDE USING gist` la chiude a livello di vincolo.

#### 2.6.5 Effetto su `D1`, e il punto che Tid ha aggiunto

Era proprio la dichiarazione d'intento il caso che sembrava non copribile dal
risolutore. Modellata così, ci rientra: il titolo non è più qualcosa che
l'operatore *digita sulla riga*, è qualcosa che **si registra una volta** — con
protocollo, validità e tetto — e che il risolutore legge. Che è anche il posto
giusto: un titolo di non imponibilità è un **fatto documentato**, non una scelta
di riga.

⭐ E Tid ci ha messo sopra la ragione generale: *«avere un risolutore ci permette
di gestire anche altre eccezioni in un unico punto»*. È il criterio con cui
guardare le prossime — ogni titolo che oggi non ha una sede si registra, non si
digita.

⚠️ **`D1` resta formalmente aperta** solo per la verifica che non ci siano
**altri** titoli per-operazione fuori dal risolutore. Il caso che la teneva in
piedi è risolto.

### 2.7 ⭐ La forma del risolutore: due stadi, una cascata, una ripartizione

Origine: domanda di Tid del 2026-08-27 — *«il regime è anche sotto utility: fra
gas, EE e acqua i regimi possono essere diversi… potremmo gestire la cascata con
un fallback, come accade con gli indirizzi. L'unico problema è che il soggetto
vincerebbe in presenza di dichiarazione d'intento mentre vincerebbe il BA se non
presente… brutto vero?»*.

**È brutto**, e lo è perché la parola «regime» tiene insieme **due meccanismi**.
Separati, la precedenza che si inverte sparisce.

#### 2.7.1 Due domande, non due livelli della stessa domanda

| | Domanda | Da cosa dipende | Esempio |
| --- | --- | --- | --- |
| **A · aliquota ordinaria** | *quale aliquota compete a questa merce?* | dalla **cosa venduta** — e quindi legittimamente dall'utility e dalla fornitura | EE al 10%; gas «uso domestico» vs «altri usi» |
| **B · titolo di non imponibilità** | *questa controparte, oggi, ha un titolo che **sostituisce** l'aliquota?* | dalla **partita IVA** | dichiarazione d'intento, inversione contabile, art. 8 |

⭐ **L'EE al 10% non è un regime del soggetto: è l'aliquota dell'energia
elettrica, uguale per tutti i clienti.** Varia per utility perché varia **la
merce**, non perché vari il cliente. È chiamarla «regime» che faceva sembrare che
i due livelli si contendessero qualcosa.

⛔ **Quindi non c'è nessuna inversione**: A e B non competono, perché non
rispondono alla stessa domanda. B non «vince su» A in una cascata — B
**sostituisce il risultato di A**, dopo che A ha risposto.

```
Stadio A   quale aliquota ordinaria?          articolo → … → fornitura   [più specifico vince]
Stadio B   c'è un titolo che la sostituisce?  soggetto                   [se sì, rimpiazza]
```

Nessun livello compare in tutti e due: il soggetto non entra mai in A, la
fornitura non entra mai in B. Non c'è niente da invertire.

#### 2.7.2 La cascata serve — ed è dello **stadio A**

Il livello fornitura in A non è un ripiego: per le utility l'aliquota dipende
spesso dall'**uso della fornitura** (gas uso domestico vs altri usi), che è una
proprietà della fornitura — non dell'articolo, e men che meno del soggetto.

⚠️ **Se si riusa il vocabolario della cascata degli indirizzi, si riusa intero**:
nel progetto è a **tre** livelli — `FONTE_ORDER = { soggetto: 0, ruolo: 1, istanza: 2 }`
in `core/utils/string.js`, con `sortByFonte` che li ordina. Una versione a due
gradini nata qui sarebbe un secondo vocabolario che qualcuno dovrà riallineare.

#### 2.7.3 ⭐ Il risolutore non ritorna un codice IVA: ritorna una **ripartizione**

Firma: una lista di `(quota imponibile, codice IVA)`, con **un solo elemento** nel
caso ordinario.

**La ragione è `P2`, e da sola basta**: plafond esaurito a metà riga → parte non
imponibile fino a capienza, il resto ad aliquota ordinaria. Una funzione che
ritorna *un* codice non sa esprimere quella risposta, e chi la chiama dovrebbe
ricostruire la spezzatura per conto suo — cioè la regola tornerebbe fuori dal
risolutore proprio nel caso per cui il risolutore esiste.

⚠️ **È una decisione da prendere adesso perché è la *firma*.** Cambiarla dopo
significa toccare ogni chiamante.

#### 2.7.4 ⛔ Fuori perimetro, dichiarato: gli scaglioni del gas

Uno scaglione di consumo è **un tetto che spezza una riga**: la stessa forma di
`P2`. La ripartizione del §2.7.3 lo accoglierebbe senza costo.

**Decisione di Tid, 2026-08-27: NON si fa adesso.** Resta scritto qui come
memoria, non come lavoro.

⭐ **E la ragione per cui è giusto tenerlo fuori sta nella regola zero, non nella
fretta**: gli scaglioni **non sono modellati** — cercato il 2026-08-27, «scaglioni»
compare nel repository solo come concetto di *prezzo* nella prosa di
`contratti_righe` e `listini_versioni`, mai come banda di aliquota. Progettare su
di loro sarebbe progettare su una previsione dei dati, che è precisamente ciò che
`AGENTS.md` vieta.

⚠️ **Prova del nove, ed è il motivo per cui il §2.7.3 resta in piedi**: togliendo
gli scaglioni dall'argomento, la ripartizione serve **lo stesso** — la pretende
`P2`, che è già decisa. Gli scaglioni sono un di più che quella forma accoglie,
non la ragione per cui la si sceglie. Se l'argomento fosse stato *«serve la
ripartizione perché un giorno faremo gli scaglioni»*, andava rifiutato.

#### 2.7.5 ❓ Aperto: lo stadio B è probabilmente una **famiglia**, non una colonna

L'ho descritto come «del soggetto», ma non tutti i titoli lo sono davvero: il
**reverse charge edile** dipende dal *tipo di operazione*, non dalla controparte;
la **dichiarazione d'intento** è già un documento con protocollo, validità e
tetto, non un flag.

Il che suggerisce che B non sia una colonna sul soggetto ma un insieme di
**qualificazioni**, ognuna con il proprio ambito e la propria prova documentale.

> ⭐ Se è così, `anagrafiche.soggetti_intento` è **la prima di una famiglia**, e
> conviene che nasca sapendolo — allargare dopo una tabella nata come caso unico
> è il modo in cui si ottengono due meccanismi per la stessa cosa. Non serve
> costruire la famiglia adesso: serve non chiudere la porta.


---

## 3. 🟠 Il gate all'emissione: chiede il prezzo, non l'aliquota

`vendite.trgfn_ddt_guard_causale_emissione` (che delega la valutazione a
`script.fn_check_ddt_emittibile`, single source con la capability) oggi verifica:

1. la causale di trasporto è dichiarata;
2. se la causale è **fatturabile**, ogni riga attiva ha un **prezzo risolvibile**.

⭐ **Manca il terzo, ed è simmetrico al secondo**: se la causale è fatturabile,
ogni riga attiva deve avere anche un'**aliquota**. Rilievo di Tid, 2026-08-27:
*«l'IVA deve esserci sempre, se non indicata deve andare in errore — forse solo
se il prezzo è null, IVA null»*. È esattamente la stessa condizione: **dove serve
il prezzo serve l'IVA**, e a dichiararlo è la stessa causale.

### 3.1 Perché **non** una `NOT NULL` sulla colonna

`vendite.ddt_righe.iva_id` è nullable, e deve restarlo: un DDT di **solo
trasporto** (conto visione, campionatura, trasferimento, omaggio) non vende, e
un'aliquota lì è un dato che non si applica — la stessa ragione per cui il prezzo
non è `NOT NULL`. Una `NOT NULL` spegnerebbe i documenti legittimi per prendere
quelli difettosi.

### 3.2 La sede

Dentro `script.fn_check_ddt_emittibile`, accanto a `E_DDT_PREZZO_NON_RISOLVIBILE`.
Da lì raggiunge **da sé** i tre consumatori — il trigger che solleva,
`fn_available_actions_ddt` che spegne il pulsante, e il motivo che il frontend
mostra — senza che nessuno dei tre vada toccato. Serve un codice nuovo a
catalogo, con la sua classe (`DATO_ERRATO`, 400: il dato lo fornisce una persona)
e il ripiego senza `%s` (`feedback_ripiego_ogni_codice_vivo`).

---

## 4. 🔴 I campi scritti e mai letti

`anagrafiche.clienti` porta il regime fiscale della controparte:

| Colonna | Nullable | Chi la scrive | Chi la legge |
| --- | --- | --- | --- |
| `iva_id` | **`NO`** | `fn_update_cliente` + `ClienteDrawer.vue` (con default da `DEFAULT_IVA_ID`) | ⛔ **nessuno**, in tutta la catena vendite |
| `split_payment` | `NO`, default `'N'` | `ClienteDrawer.vue` | ⛔ **nessuno** — non è né su `vendite.fatture` né in `fn_prepare_sdi_payload` |
| `cliente_pa` | `NO`, default `'N'` | `ClienteDrawer.vue` | ⛔ **nessuno** |

Il modello concettuale della tabella li dichiara: *«classificazioni speciali (PA,
split payment)»*, e il diagramma scrive `iva ||--o{ clienti : vat_of`.

⛔ **Non è un campo dimenticato: è un campo che l'operatore compila.** C'è il
drawer, c'è perfino il parametro di sistema per il default. Chi imposta un cliente
in reverse charge ha tutto il diritto di credere di aver deciso qualcosa, e in
fattura ritrova l'aliquota dell'articolo. È peggio di un campo assente, perché un
campo assente non mente.

⚠️ **O entrano nella catena (voce 2), o si dichiarano non usati.** Quello che non
va fatto è lasciarli così: la terza via — «li sistemiamo quando serviranno» — è il
modo in cui questo difetto è arrivato fin qui.

---

## 5. La richiesta, in ordine

| # | Cosa | A chi | Blocca il collaudo? |
| --- | --- | --- | --- |
| **I1** | Gate IVA all'emissione dentro `script.fn_check_ddt_emittibile` + codice errore nuovo a catalogo (§3) | DB | 🟠 è la voce che lo chiude |
| **I2** | Risolutore IVA a **due stadi** (§2.7, `D6`): A = aliquota ordinaria con cascata `articolo → … → fornitura`; B = titolo di non imponibilità dal **soggetto**, che sostituisce A. ⭐ **Ritorna una ripartizione** `(quota, codice IVA)`, non un codice (§2.7.3). Funzione DB sul modello di `fn_resolve_prezzo_listino_v2` | DB | no |
| **I3** | Il BE chiama I2 alla creazione della riga; il FE **smette** di fare l'auto-fill e mostra il risultato del risolutore (§2.5.1) | BE + FE | no |
| **I4** | La riga di fattura smette di rileggere `art.iva_id` e **ri-risolve** via I2. ⛔ L'alternativa «l'IVA viaggia nella catena `attivita_fatturabili`» è **esclusa da P1**: la fattura rifà, non trasporta. ⚠️ **Breaking change dichiarato** (§2.5.2) | DB + BE | no |
| **I5** | `split_payment` / `cliente_pa` → testata fattura + payload SDI (`EsigibilitaIVA`), **fuori** dal risolutore (§2.4) | DB + BE | no |
| **I7** | **`anagrafiche.soggetti_intento`** + registro movimenti + codice `config.iva` con `natura_iva_id = 8` (oggi la natura è **orfana**) + `EXCLUDE` anti-sovrapposizione. ✅ **Le sei domande sono decise** (§2.6.2/§2.6.3): consumo alla **fattura**, riga che **si spezza**, `imponibile_utilizzato` memorizzato, NC che **restituisce**, protocollo **fino all'XML**, sede sul **soggetto** | DB + BE | no — ma **sblocca D1** |
| **I6** | ❓ **Ferma su D1.** Se «l'IVA di riga non si cambia» è una regola, la sua sede non è un `:disabled` nel template: o scende nel BE (`iva_id` fuori da `_UPDATE_KEYS_RIGA`) o si dichiara che è solo un aiuto della UI | BE | no |

⛔ **L'ordine fra I6 e le altre non è indifferente, ed è l'unico modo di sbagliare
in silenzio.** `I6` toglie all'operatore l'ultima uscita manuale: applicata
**prima** di I2/I3 — cioè prima che le righe nascano con l'aliquota giusta —
cementerebbe i buchi e i valori sbagliati che oggi si possono ancora correggere
via API. `I6` va **per ultima**, e solo dopo che D1 è stata decisa.

⚠️ **I1 è indipendente da tutte le altre** e vale la pena farla per prima: chiude
la casella del collaudo e rende **visibile** il difetto delle altre voci invece di
lasciarlo silenzioso. Un documento che oggi esce senza aliquota, domani si ferma
e lo dice.

---

## 6. Presidi attesi

* **pgTAP su I1**: causale fatturabile + riga senza `iva_id` → l'emissione
  solleva il codice nuovo, con il `riga_id` nel contesto; causale **non**
  fatturabile + riga senza `iva_id` → l'emissione **passa** (è il DDT di solo
  trasporto, e senza questo test la voce diventa una `NOT NULL` mascherata);
* **pgTAP su I2**, e va **costruito**, non cercato: cliente con `iva_id` diverso
  da quello dell'articolo → il risolutore ritorna **quello del cliente**. Un test
  che itera sui clienti di oggi passerebbe a vuoto se nessuno diverge, ed è la
  forma del «verde per sottrazione» che `AGENTS.md` vieta;
* **il test che nessuno scrive**: `split_payment = 'S'` **non** cambia il codice
  IVA risolto. È la confusione più facile da fare e la più cara da scoprire in
  fattura;
* ⭐ **la prova che le due determinazioni si sono unite** (I4): stessa riga letta
  come documento e come attività di fatturazione → **stesso** `iva_id`. Finché
  restano due strade, è l'unico test che si accorge quando divergono.

---

## 7. Cosa NON è in questo brief

* la riga di ri-consegna che nasce senza IVA: è
  [brief-db-ddt-riconsegna-eredita-testata.md](../work-done/brief-db-ddt-riconsegna-eredita-testata.md)
  §3-bis / R4. Le due cose si toccano ma non si sostituiscono — la ri-consegna
  deve ereditare l'aliquota **applicata sulla spedizione d'origine**, che è un
  fatto storico e non il risultato del risolutore di oggi;
* l'omaggio (§2.2): già risolto dalla causale;
* ⛔ **gli scaglioni di aliquota del gas** (§2.7.4): fuori perimetro **per
  decisione di Tid**, 2026-08-27. La documentazione resta come **memoria futura** —
  la forma del risolutore li accoglierebbe, ma non sono modellati e non si
  progetta su una previsione;
* 📌 **il manuale dell'IVA**: Tid, 2026-08-27 — *«poi nel caso vedo se generare un
  manuale specifico per l'IVA che indica tutto il funzionamento e descrive cosa
  esiste / da fare»*. Questo brief è un documento di **cantiere**: nasce da un
  difetto e muore quando il difetto è chiuso. Un manuale è un'altra cosa e ha
  un'altra sede (`docs/it/backend/.../manual/`, template `manual-standard.md`) —
  quando si scriverà, questo brief è materiale, non il documento;
* qualunque misura sui dati. Qui non ce n'è nessuna, ed è voluto: la domanda
  «quanti clienti hanno un'IVA diversa da quella dei loro articoli?» non decide
  niente. Il modello ammette la divergenza — `clienti.iva_id` è una colonna
  `NOT NULL` con una FK a `config.iva` — e tanto basta.
