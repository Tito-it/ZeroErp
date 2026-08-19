# Brief — il DDT deve ammettere righe a prezzo zero, e oggi non le ammette

> **Tipo**: brief (decisione presa, perimetro da chiudere) · **Data**: 2026-08-17 ·
> **rev**: 2026-08-18 analisi critica e piano DB (§7–§12) · **rev**: 2026-08-19
> **decisioni chiuse** — D-3 #3 (esito) e D-5 (K2) decise da Tid; D-3 #7 si è
> rivelato un ramo morto (R-10, F-4) ·
> **Owner**: Tid · **Stato**: 🟡 **APERTO** — ⭐ **nessuna decisione pendente: il
> piano DB del §9 è eseguibile così com'è.** Perimetro DB verificato, misurato e
> pianificato (§7, §9, §12); perimetro BE/FE scritto come richiesta (§10).
> Nessuna migrazione applicata.
>
> ⚠️ **I §1, §3 e §4 sono stati scritti prima della verifica su codice e DB.**
> Si leggano insieme al **§7**, che ne corregge tre premesse: il DB ammette già
> la riga senza prezzo, il gate di DL-28 non è irraggiungibile (lo esercitano i
> pgTAP, e il DB stesso produce righe senza prezzo dalle ri-consegne), e la
> distinzione `0`/`NULL` del §3.2 oggi non ha consumatori. Restano intatti
> perché la decisione di dominio del §2 nasce da lì e **non cambia**.
>
> **Origine**: rilievo in-app di Tid (2026-08-17) mentre validava **DL-28**:
> *«se inserisco un articolo senza prezzo compare "impossibile risolvere il
> prezzo listino", e questo per qualsiasi causale scelga»*.
>
> **Decisione di Tid (2026-08-17)**: **deve essere permesso inserire articoli a
> prezzo 0 nel DDT.**
>
>
> ## 🔢 ORDINE DEI LAVORI COLLEGATI
>
> **1.** partita generalizzata → **2.** pannello situazione merce (ordine e DDT)
> → **3.** nota di credito.  ·  *In parallelo e indipendente*: righe DDT a
> prezzo zero.
>
> Catena completa e ragioni in
> [brief-design-partita-merce-generalizzata.md](brief-design-partita-merce-generalizzata.md).
>
> **Rif.**: [brief-design-fatturazione-due-lenti.md](../work-done/brief-design-fatturazione-due-lenti.md)
> §10 **DL-28** · [brief-db-fatturazione-ddt-resi.md](../work-done/brief-db-fatturazione-ddt-resi.md) §4a ·
> checklist V2 in [brief-be-fan-out-isolato-e-esito-parziale.md](brief-be-fan-out-isolato-e-esito-parziale.md) §13.2.

---

## 1. Il fatto: una premessa del design non è vera nel prodotto

DL-28 poggia su questa frase, testuale:

> *«Il DDT ammette righe senza prezzo **per design** ("solo trasporto"), ma il
> lister non le esclude → standalone senza prezzi a SPEDITO = "da fatturare" con
> prezzo vuoto.»*

Su quella premessa è stato costruito il **gate all'emissione**: causale
fatturabile → ogni riga deve avere un prezzo **risolvibile**, altrimenti blocco
parlante; *«il prezzo dimenticato diventa errore, non silenzio»*.

⚠️ **Ma la riga senza prezzo non è inseribile.** Provando a caricarla, il
pricing la respinge con *«impossibile risolvere il prezzo listino»* — **e lo fa
per qualunque causale**, comprese quelle non fatturabili (conto visione,
campionatura, trasferimento, conto lavoro, omaggio).

Ne discendono due conseguenze, entrambe da sanare:

1. **il DDT di solo trasporto non è realizzabile**, pur essendo il caso che DL-28
   dichiara esistere «per design»;
2. **la metà «blocco parlante» di DL-28 è irraggiungibile**: un gate che si
   attiva su una condizione che il sistema non consente di produrre non scatta
   mai. Non è un gate sbagliato — è un gate che presidia una porta murata.

## 2. La decisione

**Le righe a prezzo zero sono ammesse nel DDT.** Il documento di trasporto
descrive merce che si muove, e la merce si muove anche quando non si vende:
conto visione, campionatura, riparazione, trasferimento fra depositi, conto
lavorazione, omaggio. Pretendere un prezzo di listino su quei documenti è
chiedere un dato che per essi non ha significato.

⭐ **E il vocabolario per distinguerli esiste già**: `config.causali_trasporto`
porta la colonna `fatturabile`, seedata il 2026-07-17 — `VENDITA` è l'unica
`true`, le altre sette `false`. Era già la sede dell'intento, secondo la regola
di DL-28: *«l'intento non si inferisce dall'assenza di prezzo (ambiguo:
dimenticanza o scelta): si dichiara col campo che l'operatore già compila»*.

## 3. Le due domande da chiudere prima di scrivere codice

**3.1 Il prezzo zero è ammesso sempre, o solo su causale non fatturabile?**

Le due letture non sono equivalenti:

* **sempre** — la riga si carica comunque, e chi presidia è il **solo** gate
  all'emissione di DL-28: con causale fatturabile il DDT non esce finché i
  prezzi non ci sono. Il difetto («ho dimenticato il prezzo») viene intercettato
  al momento giusto, cioè quando il documento sta per avere effetti;
* **solo se non fatturabile** — il blocco resta in inserimento per le vendite.
  Più stretto, ma sposta l'errore su un momento in cui la causale potrebbe non
  essere ancora stata scelta, e obbliga a ri-validare le righe se la causale
  cambia dopo.

⚠️ **La seconda lettura ha un effetto collaterale da non sottovalutare**: la
causale è di **testata** e le righe si caricano dopo. Un vincolo di riga che
dipende dalla testata si rompe ogni volta che la testata cambia — e DL-28 aveva
già scelto di mettere il presidio **all'emissione** proprio per non incastrarsi
in quell'ordine.

**Raccomandazione**: ammettere il prezzo zero **sempre**, lasciando a DL-28 il
presidio. È anche l'unica delle due che rende raggiungibile il gate già scritto.

**3.2 Prezzo `0` o prezzo assente?**

Non sono la stessa cosa e il modello deve dirlo:

* `0` = «vale zero», un'affermazione — è il caso dell'omaggio;
* `NULL` = «non si applica», un'astensione — è il caso del trasferimento fra
  depositi.

Oggi la riga di DDT non consente né l'uno né l'altro. Va deciso se ne bastano
uno solo o se servono entrambi, perché la scelta si riflette sul gate di DL-28
(«prezzo risolvibile» deve considerare lo zero un valore valido?) e sulla stampa
del documento.

## 4. Da verificare prima di stimare

* **dove sta il blocco**: se in `PricingService`/`fn_resolve_prezzo_listino_v2`
  (che solleva quando non risolve) o in una validazione BE a monte. Cambia il
  perimetro: nel primo caso il chiamante DDT deve poter chiedere una risoluzione
  **non obbligatoria**, nel secondo basta allentare il guard;
* **chi altro dipende da quel comportamento**: il pricing è condiviso, e
  ammettere il non-risolto per i DDT non deve ammetterlo per ordini e
  preventivi, dove un prezzo mancante è davvero un difetto;
* **l'effetto sul contatore**: una riga a prezzo zero che entra in commessa
  produce un'attività a valore zero. Va confermato che i cruscotti a valore la
  reggano senza contarla come «merce da fatturare» per zero euro — o che le
  causali non fatturabili la tengano fuori, come DL-28 già prevede.

## 5. Conseguenza documentale, da non dimenticare

Qualunque sia la scelta del §3, **la premessa di DL-28 va corretta nel
design-of-record**. Oggi il §10 descrive come esistente un caso che il prodotto
non consente, e chi lo rileggerà fra sei mesi non avrà modo di accorgersene:
troverà un gate coerente con una premessa falsa.

⚠️ Finché la premessa non è vera, la voce **DL-28 della checklist V2 non è
spuntabile per intero**: la metà «causale non fatturabile fuori dalle card» si
prova (basta un DDT con prezzo e causale CONTO_VISIONE), la metà «blocco
parlante sul prezzo mancante» **no**, perché il caso non si può costruire.

## 6. Definizione di «fatto» (bozza)

* [ ] si carica una riga di DDT senza prezzo (o a zero) senza che il pricing la
      respinga;
* [ ] con causale **fatturabile**, l'emissione **blocca** con messaggio
      parlante che indica la riga — DL-28 finalmente esercitato;
* [ ] con causale **non fatturabile**, il DDT si emette e resta **fuori** da
      card e lister;
* [ ] ordini e preventivi **continuano** a rifiutare il prezzo non risolvibile:
      l'allentamento è del solo DDT;
* [ ] la premessa di DL-28 nel design-of-record è allineata al comportamento
      reale (§5).

---

## 7. Analisi critica del brief (rev 2026-08-18, dopo verifica su codice e DB)

> Metodo: le definizioni vengono dalla doc auto-generata (`docs/it/dbzero/**`,
> che riflette l'oggetto **vivo**), i percorsi dal codice, i numeri da query di
> sola lettura sul DB di sviluppo (§12). Dove il brief e il DB non concordano,
> vince il DB.

### R-1 — Il DB ammette già la riga senza prezzo: il muro è altrove, e sono **due** muri

`vendite.ddt_righe.prezzo_unitario` è **nullable**, senza CHECK e senza trigger
che lo pretenda. Nessuna riga del §2 va conquistata a livello di tabella: c'è già.

Il rifiuto che Tid ha visto in-app nasce in due punti **diversi**, e il brief li
tratta come uno solo (§4, primo punto):

| Percorso | Dove si rompe | Natura |
|---|---|---|
| Articolo **semplice** | `ddt_service.gestisci_riga` → `_resolve_prezzo_riga` (`backend/apps/vendite/services/ddt_service.py`, riga 534) | **BE**. Non è una validazione del DDT: è un **auto-fill** che non sa fallire. Il prezzo assente nel payload viene letto come «risolvilo tu», e il resolver DB solleva se non trova |
| Articolo **composito** | `vendite.fn_ddt_riga_componenti_init` → resolver; e a valle `ddt_righe_componenti.prezzo_unitario` **NOT NULL**; e ancora `script.trgfn_componenti_check_prezzo_obbligatorio` che vieta lo **zero** sui componenti obbligatori | **DB**, e in triplice copia |

⭐ Ne discende la prima correzione al perimetro: per il kit la riga senza prezzo è
impossibile **tre volte**, e tutte e tre stanno nel DB. Per l'articolo semplice il
DB non oppone nulla e il lavoro è del BE. Il brief chiedeva «dove sta il blocco,
perché cambia il perimetro»: la risposta è *tutti e due*, e il perimetro DB esiste
davvero — ma non dove il §4 lo cercava.

### R-2 — «Un gate che presidia una porta murata» è vero solo per metà, e la metà vera è più interessante

La porta **non** è murata nel DB:

* i pgTAP la attraversano scrivendo righe senza prezzo in SQL puro
  (`db/pgtap/script/test-fn-check-ddt-emittibile-v1.sql` test 5,
  `db/pgtap/vendite/test-ddt-solo-trasporto-causale-v1.sql` test 3): il caso «si
  può costruire» eccome, e il gate lo blocca come previsto;
* e c'è una **strada di produzione** che le righe senza prezzo le crea da sé:
  `vendite.fn_genera_ddt_riconsegna` inserisce le righe di ri-consegna
  valorizzando `qta_operativa` e **non** `prezzo_unitario`.

Quel che è vero — e va detto con la precisione che merita — è che il gate **non è
mai scattato su un documento reale**: le 271 occorrenze di
`E_DDT_PREZZO_NON_RISOLVIBILE` in `dbops.error_log` hanno **tutte** un `ddt_id`
che non esiste più, cioè sono corse di pgTAP (il log è out-of-transaction via
dblink: sopravvive al ROLLBACK dei test).

> **Riformulazione onesta della premessa di DL-28**: il DDT senza prezzo è
> realizzabile e *già realizzato* — dal DB. È irrealizzabile **dall'operatore**.
> La premessa da correggere nel design-of-record (§5) non è «il caso non esiste»,
> è «il caso esiste ma non ha un'interfaccia».

### R-3 — Le righe senza prezzo che esistono passano per **eredità**, e c'è una corsia dove non passerebbero

Le 6 righe attive senza prezzo sul DB di sviluppo sono **tutte** ri-consegne, e
tutte ereditano il prezzo dalla riga d'ordine via `ordini_righe_fulfillment` — la
`COALESCE` che il gate applica apposta. Emissione legittima, nessun falso
positivo osservato.

⚠️ Ma `fn_genera_ddt_riconsegna` gestisce **esplicitamente** il caso standalone
(`ordine_riga_id IS NULL` → nessun fulfillment). Lì la riga non ha né prezzo
proprio né prezzo da ereditare. E la causale giusta per quel documento è
**VENDITA**: il §N7 di `vw_partite_merce`, scritto ieri, dice che la quota
accreditata torna ri-fatturabile, quindi quella ri-consegna *si vende*. Risultato:
l'emissione si blocca con `E_DDT_PREZZO_NON_RISOLVIBILE` e l'unica uscita è
digitare il prezzo a mano su una riga che il DB ha generato da sé.

Sul DB di sviluppo le righe di reso standalone sono 2 su 17: il caso non è
teorico, è solo non ancora incontrato. **Il cantiere nota di credito si è chiuso
ieri lasciando questa porta stretta**, e questo brief è il posto dove la si allarga.

### R-4 — La causale è mutabile dopo l'emissione, e il gate guarda **solo** la transizione

`trgfn_ddt_guard_causale_emissione` esce in testa se lo stato NEW non è `EMESSO`.
Un `UPDATE` che porta `causale_trasporto_id` da CONTO_VISIONE a VENDITA su un DDT
già SPEDITO non ripassa da nessun controllo. Da lì:

1. la riga senza prezzo diventa eleggibile per `fn_list_ddt_da_pushare` (il cui
   unico discriminatore è `caus.fatturabile IS TRUE`);
2. il push la porta a `fn_upsert_commessa_attivita`, che la respinge con
   `E_PARAMETRO_INVALIDO` — «prezzo_snapshot obbligatorio».

Non c'è corruzione (la terza cintura, `commesse_attivita.prezzo_snapshot` NOT
NULL, tiene), ma l'errore arriva **tardi, in batch, e non nomina la causa**.

⚠️ Oggi quella porta è chiusa **in Python** (`_STATI_MODIFICABILI = {"DRAFT"}` in
`ddt_service`). In un progetto DB-first questo è esattamente il tipo di invariante
che non deve vivere lì: la domanda non è «è successo?», è «può succedere?».

### R-5 — In `fn_check_ddt_emittibile` c'è **già** un ramo morto, ed è lo stesso difetto che il brief denuncia

Il motivo `E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE` (§5, secondo blocco) si
attiva su `drc.prezzo_unitario IS NULL`. Ma quella colonna è **NOT NULL** su tutte
e quattro le `*_righe_componenti` (preventivi, ordini, contratti, DDT). La
condizione non può essere vera: il ramo non scatta mai.

> È la stessa figura del §1.2 — un presidio davanti a una porta murata — ma
> dentro alla funzione che il brief cita come parte sana. O si dichiara morto in
> un commento, o lo si rende vivo (slice C): lasciarlo ambiguo significa che tra
> sei mesi qualcuno lo leggerà come copertura di un caso che nessuno copre.

### R-6 — Il §3.2 (`0` vs `NULL`) chiede una distinzione che oggi non ha lettori

I due esempi del brief cadono **entrambi** sullo stesso lato del vocabolario:

| Causale (seed 2026-07-09) | `fatturabile` |
|---|---|
| VENDITA | `t` |
| CONTO_VISIONE · RESO · RIPARAZIONE · CAMPIONATURA · TRASFERIMENTO · CONTO_LAVORO · **OMAGGIO** | `f` |

L'omaggio — il caso che nel brief giustifica lo `0` come *affermazione* — è
**non fatturabile** come il trasferimento. Nessuno dei due arriva a fattura;
`vw_ddt_righe_iva_base` filtra `prezzo_unitario IS NOT NULL`, quindi esclude il
NULL e include lo zero, che somma zero: stesso identico riepilogo. Introdurre due
stati significherebbe mantenere una differenza che **nessun consumatore legge**.

⭐ La distinzione diventa reale il giorno in cui esisterà l'**omaggio con rivalsa
IVA**: merce a valore zero su un documento che *si fattura*. Ma quello non è un
fatto del prezzo — è un fatto della **natura** del documento, cioè l'asse aperto
ieri con `config.nature_doc_fiscale`. Trattarlo come un terzo stato del prezzo
oggi vuol dire pagarlo due volte.

### R-7 — Il terzo punto del §4 (effetto sul contatore) è già chiuso, e in bene

`vw_partite_merce` ragiona in **quantità**, non in valore: una riga a prezzo zero
o assente non muove nessun saldo. La causale non fatturabile la porta a
`stato = 'NON_FATTURABILE'` con `differenza IS NULL`, che è il predicato esplicito
con cui il lister la scarta. `fn_list_ddt_da_pushare` e `vw_dash_fatturazione_ddt`
escludono le causali non fatturabili con lo stesso INNER JOIN. **Nessun lavoro
richiesto**: le due caselle del §6 su card e lister sono già verdi, e i pgTAP
`test-ddt-solo-trasporto-causale-v1.sql` (test 5 e 6, con controprova) le
presidiano.

### R-8 — Ma quell'INNER JOIN ha un effetto collaterale, fuori perimetro e da registrare

`vw_dash_fatturazione_ddt` prevede il motivo `DOC_BOZZA`, quindi si aspetta di
vedere i DDT in bozza. Il JOIN su `causali_trasporto ... AND fatturabile IS TRUE`
è però **INNER**, e in bozza la causale può legittimamente essere NULL (lo dice
`fn_check_ddt_emittibile`: «in bozza il NULL resta legittimo»). Un DDT in bozza
senza causale non compare nel cockpit: non è «fermo», è **invisibile**. Preesistente
e indipendente da questo brief — va nel registro, non nel piano (F-1).

### R-9 — Il costo nascosto del «respinge» è il **log**, e decide la forma della soluzione

`script.fn_log_error_only` scrive su `dbops.error_log` via **dblink fuori
transazione**. Quindi ogni tentativo di risoluzione fallito lascia una riga anche
quando tutto rollbacka — e il BE ne aggiunge una **seconda**, ri-loggando lo
stesso codice in `pricing_service.resolve`. Sul DB di sviluppo la famiglia «prezzo
che non c'è» pesa ~2.300 righe (§12).

⛔ **Conseguenza operativa**: qualunque soluzione che si limiti a *catturare*
l'eccezione — un `BEGIN … EXCEPTION WHEN` in DB, o un `try/except` in Python —
**lascia il log intatto**. Il log lo scrive il DB prima di sollevare: solo il DB
può smettere di scriverlo. È l'argomento che decide la forma della slice A: non
un wrapper che ingoia, ma un nucleo che **non solleva affatto**.

### R-10 — Il secondo ramo morto, e un errore che il DB non solleva più ma l'operatore continua a leggere

Emerso mentre si istruiva la domanda #7 della tabella D-3, ed è più grosso della
domanda che doveva chiudere.

Il resolver solleva `E_PREZZO_LISTINO_NON_TROVATO` quando
`v_categoria_cliente_id IS NULL`, cioè «billing account senza categoria e senza
contratto attivo». Ma `anagrafiche.billing_account.categoria_cliente_id` è
**NOT NULL** dal **2026-04-14** (`00_schema/anagrafiche/20260414-03`, il backfill
che assegnò STANDARD e chiuse la colonna). Se il BA esiste la categoria c'è; se
non esiste si è già usciti prima con `E_PARAMETRO_INVALIDO`. **La condizione non
può più essere vera** — ed è il secondo ramo strutturalmente irraggiungibile
trovato in questo giro, dopo R-5.

⚠️ **E il codice continua a circolare lo stesso.** Misura su `dbops.error_log`:

| chi ha scritto | `E_PREZZO_LISTINO_NON_TROVATO` | `E_CATEGORIA_LISTINO_NON_MAPPATA` |
|---|---|---|
| `vendite` (il DB) | **0** | 21 |
| `backend` (`pricing_service.resolve`) | **587** | **587** |

I due 587 non sono una coincidenza: stesso primo giorno (2026-07-18), stesso
ultimo (2026-08-18). Il backend registra **due volte** lo stesso fallimento, una
col codice giusto e una con un codice che il DB **non solleva da aprile**.
Verificato su un caso reale (`ba_id=100`, `utility_id=7`, 2026-06-01): il BA ha
categoria STANDARD, non ha contratto attivo, e la matrice
`categorie_clienti_listini` per quella coppia è **vuota** — la condizione è
`E_CATEGORIA_LISTINO_NON_MAPPATA`, non «nessun prezzo risolto».

⛔ **Perché non è cosmetico.** I due codici portano all'operatore due istruzioni
diverse e solo una è giusta:

* `E_PREZZO_LISTINO_NON_TROVATO` → *«Verificare listini, associazioni e versioni
  attive per articolo/uom/data»* — manda a guardare i listini, dove non c'è nulla
  da guardare;
* `E_CATEGORIA_LISTINO_NON_MAPPATA` → *«Aggiungere la mappa in
  categorie_clienti_listini oppure assegnare un contratto individuale al BA»* —
  è la riparazione vera.

⭐ **Approfondito e documentato a parte.** Accoppiando le righe per contesto
identico, **587 su 587** hanno una gemella: prima `E_CATEGORIA_LISTINO_NON_MAPPATA`,
poi — **55 millisecondi dopo**, troppo poco per una seconda azione dell'operatore
— quella col codice fantasma, entrambe sotto `function_name='pricing_service.resolve'`.
È la stessa richiesta che logga due volte con due codici diversi. Il **meccanismo**
non l'ho isolato (serve un debugger sul BE) ma ho escluso cinque ipotesi, e il
tutto è in [brief-be-pricing-codice-errore-fantasma](brief-be-pricing-codice-errore-fantasma.md),
che è la sede giusta: **il difetto non è del DDT, è del pricing**, quindi di ogni
dominio che lo chiama. Qui resta solo il rimando (**F-4**).

---

## 8. Decisioni

### D-1 — Il prezzo può mancare **sempre**; il presidio resta all'emissione ✅

Conferma la raccomandazione del §3.1, con una ragione in più che il brief non
poteva avere: **il DB è già così**. La causale non entra in nessun vincolo di
riga, e i presidi stanno tutti a valle (gate all'emissione → esclusione dal lister
→ `prezzo_snapshot` NOT NULL). Legare un vincolo di riga alla testata
introdurrebbe nel DB proprio l'accoppiamento che il §3.1 teme, e lo
introdurrebbe *contro* un impianto che ha già scelto altrimenti.

### D-2 — Un solo stato: `NULL`. Lo `0` resta un valore scrivibile, non un secondo significato ✅

Nessuna colonna nuova, nessun flag. Il *perché* dell'assenza non si inferisce e
non si inventa: si **dichiara con la causale** (regola di DL-28) e, quando serve
il dettaglio tecnico, si legge nell'`esito_codice` che la slice A restituisce
(«articolo non a listino» ≠ «categoria non mappata»). Da rivedere quando nascerà
l'omaggio con rivalsa, e **sull'asse natura**, non su quello prezzo (R-6).

### D-3 — L'assenza di prezzo è un **esito**; un parametro sbagliato resta un **errore**

Il resolver si sdoppia: un nucleo **puro** che *riporta* l'esito e un guscio
sottile che lo *solleva*. Ripartizione dei 10 punti di raise oggi presenti in
`fn_resolve_prezzo_listino_v2`:

| # | Codice | Stadio | Nel nucleo puro |
|---|---|---|---|
| 1 | `E_PARAMETRO_INVALIDO` | guard input | **resta errore** — è un difetto del chiamante |
| 2 | `E_PARAMETRO_INVALIDO` | billing_account inesistente | **resta errore** — entità che non esiste |
| 3 | `E_ARTICOLO_ESCLUSO_DA_CONTRATTO` | 1a | **esito** ✅ *deciso da Tid il 2026-08-19* — vedi nota sotto |
| 4 | `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C` | 1b | esito |
| 5 | `E_LISTINO_VERSIONE_NON_ATTIVA` | 1b-1 | esito |
| 6 | `E_PREZZO_LISTINO_RIGA_NON_TROVATA` | 1b-3 | esito |
| 7 | `E_PREZZO_LISTINO_NON_TROVATO` | 2 (BA senza categoria) | **esito** ✅ *non c'era niente da decidere* — ramo **morto**, vedi R-10 |
| 8 | `E_CATEGORIA_LISTINO_NON_MAPPATA` | 2 | esito |
| 9 | `E_LISTINO_VERSIONE_NON_ATTIVA` | 2-1 | esito |
| 10 | `E_PREZZO_LISTINO_RIGA_NON_TROVATA` | 2-3 | esito |

Regola in una riga: **«un parametro sbagliato è un errore; un prezzo che non c'è
è un esito.»**

⭐ **Nota sul #3 — perché l'esclusione da contratto degrada a esito (Tid, 2026-08-19).**
L'esclusione è una decisione esplicita, e resta tale: ma parla di **fatturare**,
non di **spostare merce**. Lo dice il catalogo stesso, testualmente — *«non può
essere fatturato tramite questo contratto»*, *«l'articolo non deve generare
**valore** nel contratto»* (`messaggi_errore`, 453). Su un DDT che non vende
(riparazione, reso, conto visione) quella frase non ha oggetto: non c'è nessun
valore da generare.

Il divieto non si allenta di un millimetro, **si sposta dove ha effetto**: con
causale fatturabile la riga resta senza prezzo e il gate di DL-28 blocca
l'emissione. E il *perché* non si perde — l'`esito_codice` viaggia insieme al
risultato, quindi il FE può mostrare «articolo escluso dal contratto» come
avviso sulla riga (FE-1, §10) invece che come muro all'inserimento.

⚠️ Scartata la variante «esito solo se la causale non fattura»: il resolver è
condiviso con preventivi, ordini e contratti e **non conosce il documento
chiamante**. Insegnarglielo vorrebbe dire fargli conoscere i DDT — l'accoppiamento
che D-1 rifiuta.

⭐ **Nota sul #7 — non era una decisione, era un ramo morto (verificato 2026-08-19).**
Vedi **R-10**: `anagrafiche.billing_account.categoria_cliente_id` è **NOT NULL**
dal 2026-04-14, quindi la condizione che solleva quel codice non può più essere
vera. Nel nucleo puro il ramo **si conserva** e si classifica come esito — non si
cancella: se un domani il NOT NULL cadesse, il comportamento corretto sotto D-3 è
già quello. Ma si **commenta** che oggi è irraggiungibile e perché, che è
esattamente ciò che non è stato fatto per il ramo di R-5.

✅ **La tabella D-3 è chiusa: nessun punto resta aperto.**

### D-4 — La causale di trasporto diventa **immutabile fuori dalla bozza**

È la lettura corretta anche fuori dal difetto: la causale è **stampata sul
documento di trasporto**. Una volta emesso, il documento è quello.

Alternativa scartata: ri-valutare `fn_check_ddt_emittibile` a ogni cambio di
causale. Costa uguale, e non copre il caso «già pushato e poi cambiato», dove il
problema non è più la validità ma la **coerenza con quanto già in commessa**.

### D-5 — Compositi: **K2, allentamento simmetrico** ✅ *deciso da Tid il 2026-08-19*

| | K1 — limite dichiarato | **K2 — allentamento simmetrico** ⭐ **scelto** |
|---|---|---|
| Cosa fa | Il kit non viaggia senza prezzi. Si migliora solo il **messaggio** e lo si scrive nella doc | Il componente ammette il prezzo assente quando il documento non vende, con la **stessa** regola del padre (la causale) |
| Costo DB | ~0 (una riga di CSV messaggi + una nota) | 5 punti (slice C), di cui uno delicato (**C2**) |
| Cosa resta rotto | Campionatura / conto visione / riparazione **di un kit** | nulla di noto |
| Rischio | zero | il ricalcolo del padre (**C2**): se non si tocca, produce una **somma parziale silenziosa** |

**Motivazione della scelta.** K1 lasciava irrisolto un caso ordinario — mandare in
visione, in campionatura o in riparazione un prodotto composito — e lo lasciava
irrisolto per un motivo che non regge al confronto col padre: la riga-kit e le
sue righe-componente descrivono **la stessa merce sullo stesso documento**, e non
c'è ragione perché obbediscano a due regole diverse su cosa significhi «questo
documento non vende». La simmetria «padre e figli obbediscono alla stessa
dichiarazione» è la stessa idea di DL-28, applicata un livello più sotto.

⛔ **La condizione della scelta è C2, e non è negoziabile.** Il prezzo del kit è
`SUM(prezzo componente × coefficiente)`. Oggi
`script.fn_ricalcola_prezzo_padre_da_componenti` usa una `SUM` semplice e il suo
stesso commento dichiara la premessa che K2 rimuove: *«SUM standard è sufficiente
(no NULL propagation) — prezzo sempre NOT NULL»*. Tolta la NOT NULL, quella `SUM`
**ignora** il componente senza prezzo e restituisce la somma dei rimanenti: un
prezzo **sbagliato**, non un prezzo **assente**, e nessuno se ne accorge. Un kit a
prezzo assente è un caso che il gate all'emissione intercetta; un kit a prezzo
parziale passa il gate e finisce in fattura. **C2 va scritto e va scritto prima
di C1** (§9).

⭐ Perimetro dell'allentamento: **solo `vendite.ddt_righe_componenti`**.
Preventivi, ordini e contratti restano NOT NULL — lì il prezzo mancante è un
difetto vero, e la quarta casella del §6 dice esattamente questo.

---

## 9. Piano di sviluppo DB

> **Convenzioni** · file `db/changelog/migrations_v2/<fase>/<schema>/YYYYMMDD-NN-<tipo>-<descrizione>-mctit.yaml`,
> un changeSet per file, `logicalFilePath` sempre, `runOnChange: false` nello stato
> finale. **NN è una sequenza globale per data fra tutte le cartelle**: al
> 2026-08-18 il primo libero è **77**. Corpo delle funzioni esistenti **dalla doc
> auto-gen**, firma e `RETURNS` **dall'ultimo YAML** (l'auto-gen scioglie i `%TYPE`);
> ricordare il `;` dopo `$function$`.
>
> ⛔ **Nessuna migrazione va applicata**: il piano si scrive, si fa rivedere, e
> l'`update` lo lancia Tid.

### Slice A — Il resolver impara a dire «non risolvo» ✅ **SCRITTA (2026-08-19), da applicare**

> **Stato**: i quattro punti sono scritti e verificati in transazione annullata
> sul DB di sviluppo. ⛔ **Nessuna migrazione applicata**: l'`update` lo lancia Tid.
>
> | file | cosa |
> |---|---|
> | `20_code/vendite/20260819-07-create-fn-resolve-prezzo-listino-v2-esito-mctit.yaml` | A1 — il nucleo |
> | `20_code/vendite/20260819-08-update-fn-resolve-prezzo-listino-v2-guscio-mctit.yaml` | A2 — il guscio |
> | `db/pgtap/vendite/test-fn-resolve-prezzo-listino-esito-v1.sql` | A3 — 11 test, **11 verdi** |
> | `docs/it/dbzero/vendite/manual/fn_resolve_prezzo_listino_v2.md` | A4 — doc concettuale |
>
> **Verificato sul dato vero, non solo compilato:**
>
> * caso risolvibile → nucleo e guscio danno prezzo, origine, listino e riga
>   **identici** (95,00 = 100 − 5, valore atteso scritto nel test, non dedotto);
> * caso non risolvibile → il nucleo ritorna **una** riga con
>   `esito_codice = E_CATEGORIA_LISTINO_NON_MAPPATA` e prezzo NULL;
> * il guscio sullo stesso input solleva ancora `P0001` **con il codice sul
>   canale `CONSTRAINT`** — che è ciò su cui il BE decide 409/404/422 — e col
>   messaggio a segnaposti **sostituiti**: il giro nucleo → array → VARIADIC
>   non perde l'arità;
> * `E_PARAMETRO_INVALIDO` solleva ancora **anche dal nucleo** (regola D-3);
> * ⭐ **venti risoluzioni fallite col nucleo scrivono ZERO righe** in
>   `dbops.error_log`. È la ragione della slice, ed è un test, non una promessa.
>
> ⚠️ **Il collaudo è girato come owner**, perché creare funzioni richiede quei
> permessi: la corsa definitiva come `zeroerp_app` (con RLS attiva) si può fare
> solo dopo l'apply. Il `GRANT EXECUTE` per `zeroerp_app` è **dentro** A1, quindi
> il test non aspetta la passata serale di `ci_apply`.

#### Contenuto della slice

**Forma**: nucleo puro + guscio che solleva. Non un wrapper che cattura (R-9).

| # | Oggetto | Fase | Tipo | Note |
|---|---|---|---|---|
| A1 | `vendite.fn_resolve_prezzo_listino_v2_esito(...)` — **nuova** | `20_code/vendite` | `create-fn` | Corpo identico all'attuale, con i 10 `PERFORM fn_log_and_raise_error` sostituiti: i 2 «errore» restano, gli 8 «esito» diventano `RETURN` con le 14 colonne a NULL più `esito_codice varchar`, `esito_context jsonb`, `esito_valori text[]`. `STABLE`. **Non logga, non solleva** (per gli 8). ⚠️ Il ramo #7 si **conserva** e si **commenta** come oggi irraggiungibile, con il perché (R-10): è l'errore che R-5 documenta, e ripeterlo nel file che lo denuncia sarebbe grottesco |
| A2 | `vendite.fn_resolve_prezzo_listino_v2(...)` — **riscritta come guscio** | `20_code/vendite` | `update-fn` | `SELECT * INTO` dal nucleo; se `esito_codice IS NOT NULL` → `PERFORM script.fn_log_and_raise_error('vendite','fn_resolve_prezzo_listino_v2', esito_codice, esito_context, NULL::uuid, VARIADIC esito_valori)`; altrimenti proietta e `RETURN NEXT`. **Firma e `RETURNS TABLE` invariati** → basta `CREATE OR REPLACE`, nessun DROP, nessun overload |
| A3 | pgTAP `db/pgtap/vendite/test-fn-resolve-prezzo-listino-esito-v1.sql` | — | test | (1) esiste; (2) caso risolvibile: le due funzioni danno lo **stesso** `prezzo_finale` e `esito_codice IS NULL`; (3) caso non risolvibile: il nucleo torna **1 riga** con prezzo NULL ed `esito_codice = 'E_PREZZO_LISTINO_RIGA_NON_TROVATA'`; (4) **regressione**: il guscio solleva ancora `P0001` con lo stesso codice sul canale `CONSTRAINT` (`throws_ok` **con** SQLSTATE); (5) i due codici «parametro» sollevano **anche** dal nucleo |
| A4 | doc manuale `docs/it/dbzero/vendite/manual/fn_resolve_prezzo_listino_v2.md` | — | doc | Perché due funzioni, e la regola D-3. La `_esito` non è né `fn_check_*` (non torna un boolean) né `fn_guard_*` (non solleva): **riporta**, e il nome lo dice |

⚠️ **Trappole note su questa slice**

* la `_esito` è una funzione **nuova**: il `GRANT EXECUTE` per `zeroerp_app`
  arriva dal loop di `90_end/ci_apply/20260205-41`, che su un migrate manuale
  **non gira** (di sera ci pensa il pgagent). Il pgTAP gira come `zeroerp_app`:
  se lanciato subito dopo l'update fallirà con «permesso negato», e non sarà un
  difetto della funzione. Attendere `ci_apply`, oppure marcare il file
  `-- pgtap-runner: owner` **con motivo** — e toglierlo dopo;
* nessuna delle 10 chiamate esistenti (6 `fn_*_componenti_init/preview` in DB +
  `pricing_repository.py`, che passa 9 argomenti posizionali e legge per nome)
  va toccata: è il punto della slice;
* la `_esito` **non deve** contenere una seconda copia della logica. Se durante
  la scrittura si è tentati di «semplificare» il nucleo, ci si ferma: il valore
  di A sta nell'essere lo **stesso** corpo.

⭐ **Da sola, A non cambia nulla per l'operatore.** Consegna lo strumento: chi lo
usa è il BE (BE-1, §10) per gli articoli semplici e la slice C per i compositi.
Va detto nel commit, altrimenti sembra un lavoro senza effetto.

### Slice B — L'intento, una volta emesso, non si cambia

| # | Oggetto | Fase | Tipo | Note |
|---|---|---|---|---|
| B0 | `E_DDT_CAUSALE_IMMUTABILE` | `80_data` | append CSV | **Solo append** a `80_data/sql/config/messaggi_errore.csv` — i loader `runOnChange` esistenti ripescano il file, nessun loader nuovo. Un `%s` (numero DDT), `causa` e `soluzione` valorizzate, classe `E_` |
| B1 | `vendite.trgfn_ddt_guard_causale_immutabile()` | `20_code/vendite` | `create-fn` | Blocca se `OLD.causale_trasporto_id IS DISTINCT FROM NEW.causale_trasporto_id` e lo stato **OLD** non è `DRAFT`. Lo stato si legge da `config.stati_doc_ddt.codice_interno` (mai per `codice`) |
| B2 | `trg_ddt_a10_guard_causale_immutabile_upd` | `20_code/vendite` | `create-trg` | `BEFORE UPDATE OF causale_trasporto_id ... WHEN (NEW.causale_trasporto_id IS DISTINCT FROM OLD.causale_trasporto_id)`. Fase `a10` = guard |
| B3 | pgTAP `db/pgtap/vendite/test-ddt-causale-immutabile-v1.sql` | — | test | (1) in DRAFT si cambia; (2) su EMESSO `throws_ok(..., 'P0001')`; (3) un `UPDATE` che tocca **altre** colonne su EMESSO passa (il guard non è un lucchetto sulla testata); (4) valore invariato nel payload → nessun blocco |

⚠️ **Prima di scrivere B2, grep obbligatorio** sui pgTAP che fanno `UPDATE` su
`vendite.ddt`: un guard restrittivo entrato dopo è la causa più frequente di rossi
nuovi su fixture vecchie. Da confrontare con `scripts/pgtap-baseline.sh vendite`
**prima** e **dopo**, e da distinguere dalla baseline CI (popolazioni diverse).

> **Nota di proporzione**: oggi il BE non espone questo cambio
> (`_STATI_MODIFICABILI = {"DRAFT"}`). B non ripara un difetto osservabile: sposta
> un invariante da Python al DB, dove il progetto ha deciso che stia. Priorità
> **media** — se il tempo è poco, si fa dopo A e C.

### Slice C — I compositi *(D-5 = **K2**, deciso 2026-08-19: slice **confermata**)*

| # | Oggetto | Fase | Tipo | Note |
|---|---|---|---|---|
| C1 | `vendite.ddt_righe_componenti.prezzo_unitario` → **nullable** | `00_schema/vendite` | `alter-table` | **Solo la tabella del DDT.** Preventivi, ordini e contratti restano NOT NULL: lì il prezzo mancante è un difetto vero |
| C2 | `script.fn_ricalcola_prezzo_padre_da_componenti` | `20_code/script` | `update-fn` | ⛔ **Il punto delicato.** Oggi fa `COALESCE(SUM(prezzo * coeff), 0)` e il suo stesso commento dichiara la premessa che C1 rimuove: *«SUM standard è sufficiente (no NULL propagation) — prezzo sempre NOT NULL»*. Con un figlio NULL la SUM lo **ignora** e il padre riceve una **somma parziale**: un prezzo sbagliato, non un prezzo assente. Nuova regola: se esiste un figlio attivo con prezzo NULL → padre **NULL**; se non ci sono figli attivi → `0` (invariato) |
| C3 | `script.trgfn_componenti_check_prezzo_obbligatorio` | `20_code/script` | `update-fn` | Il divieto dello zero sul componente obbligatorio vale finché il documento **vende**. Parametrizzare come già fa `trgfn_componenti_guard_coerenza_bom`, che riceve la strada verso la testata (`'vendite','ddt_righe','riga_ddt_id','ddt','ddt_id','data'`): stessa forma, nessuna logica nuova, nessun caso speciale hardcoded sul DDT dentro una funzione condivisa da 4 tabelle |
| C4 | `script.fn_check_ddt_emittibile` | `20_code/script` | `update-fn` | I due motivi «componenti» (§5) diventano condizionati a `fatturabile`, esattamente come il motivo prezzo del §3. Il ramo `E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE` **smette di essere morto** (R-5) e inizia a fare il suo mestiere |
| C5 | `vendite.fn_ddt_riga_componenti_init` + `..._preview` | `20_code/vendite` | `update-fn` | Passano dal nucleo `_esito` (A1). Prezzo non risolto → si inserisce NULL invece di sollevare; `prezzo_resolver_context` registra l'`esito_codice`, così il *perché* non si perde. La `_preview` mostra «non risolto» invece di fallire il dialog |
| C6 | pgTAP `db/pgtap/vendite/test-ddt-componenti-senza-prezzo-v1.sql` | — | test | (1) kit su causale non fatturabile: init inserisce, padre = **NULL**, non una somma parziale; (2) emissione **passa**; (3) stesso kit su VENDITA: emissione **bloccata** (`P0001`, codice componenti); (4) preventivi/ordini invariati — la NOT NULL è ancora lì (controprova: senza, C1 potrebbe essere stata applicata a tappeto); (5) padre = SUM quando tutti i figli hanno prezzo (regressione su C2) |

⚠️ **Ordine imposto**: C2 **prima** di C1 nella numerazione. L'autogen ordina per
NN e mescola `00_schema` e `20_code`: se la colonna diventa nullable prima che il
ricalcolo sappia gestire il NULL, esiste una finestra in cui il padre riceve
somme parziali. La finestra è di minuti su un DB solo, ma è esattamente il tipo di
dato sporco che poi non si sa più da dove viene.

### Slice D — Verità documentale *(nessuna migrazione, ma non è opzionale)*

| # | Cosa | Dove |
|---|---|---|
| D1 | Correggere la premessa di DL-28 (§5 del brief), nella forma di R-2: **non** «il caso non esiste», ma «esiste, lo produce il DB, non ha interfaccia» | `docs/it/dev/work-done/brief-design-fatturazione-due-lenti.md` §10 |
| D2 | Registrare che la mezza casella «blocco parlante» di DL-28 è **provata dai pgTAP** e non provabile in-app finché BE-1 non entra | `brief-be-fan-out-isolato-e-esito-parziale.md` §13.2 |
| D3 | `COMMENT ON` di `fn_check_ddt_emittibile` — oggi dichiara cinque presidi, uno dei quali non può scattare | contestuale a C4 (o, con K1, un changeset di solo commento) |
| D4 | Doc manuale della causale come **dichiarazione d'intento** (unico posto dove l'operatore sceglie se la merce si vende) | `docs/it/dbzero/config/manual/causali_trasporto.md` |

### Ordine dei lavori e cosa consegna ciascuna slice

```
A (resolver a esito) ✅ ┬──► BE-1 (§10) ──► articolo semplice senza prezzo: FATTO
                       └──► C (compositi) ──► kit senza prezzo: FATTO
B (causale immutabile) ─────────────────────► invariante spostato nel DB
D (documentale) ────────────────────────────► la doc smette di mentire
```

* **A da sola**: nessun effetto visibile. È il prerequisito di tutto il resto.
* **A + BE-1**: chiude 3 delle 5 caselle del §6 (righe semplici, gate esercitato,
  ordini e preventivi invariati).
* **+ C**: chiude il caso kit (visione, campionatura, riparazione di un
  composito). Non è più opzionale — D-5 l'ha scelta — ma resta **l'ultima** in
  ordine di dipendenza: senza A non ha da chi farsi dire «non risolvo».
* **B** e **D** sono indipendenti e possono entrare in qualunque momento.

### Registro (fuori perimetro, da non perdere)

* **F-1** (R-8) — `vw_dash_fatturazione_ddt`: l'INNER JOIN sulla causale rende
  invisibili i DDT in bozza senza causale, mentre la vista prevede il motivo
  `DOC_BOZZA`. Preesistente, indipendente da questo brief.
* **F-2** (R-9) — doppio log per ogni fallimento del pricing: il DB scrive, il BE
  ri-scrive lo stesso codice. Da valutare quando si toccherà `ErrorManager`.
* **F-3** (R-6) — l'omaggio con rivalsa IVA non è rappresentabile: `OMAGGIO` è
  `fatturabile=false`, quindi non arriva mai a fattura. Da riprendere sull'asse
  `config.nature_doc_fiscale`, non su quello del prezzo.
* **F-4** (R-10) — ⛔ **BE, e con effetto sull'operatore.** ➡️ **Uscito da questo
  registro: ha un brief suo**,
  [brief-be-pricing-codice-errore-fantasma](brief-be-pricing-codice-errore-fantasma.md)
  (DB → BE, 2026-08-19), perché tocca **ogni dominio che chiama il pricing** e in
  un registro «fuori perimetro» di un brief sui DDT si sarebbe perso.
  In sintesi: `pricing_service` scrive `E_PREZZO_LISTINO_NON_TROVATO` 587 volte
  per un fallimento che è `E_CATEGORIA_LISTINO_NON_MAPPATA`, e il DB quel codice
  non può sollevarlo dal 2026-04-14. Le **587 righe sbagliate hanno tutte e 587
  una gemella corretta**, stesso contesto, scritta **55 ms prima**: è la stessa
  richiesta che logga due volte. Il banner manda l'operatore sui listini invece
  che sulla matrice categoria→listino.

---

## 10. Richieste al BE e al FE

> Perimetro DB: qui si **scrivono**, non si implementano.

**BE-1 — L'auto-fill del prezzo sul DDT deve poter fallire senza rumore.** ⭐
In `ddt_service.gestisci_riga` il ramo «prezzo non passato → risolvi» chiama oggi
`PricingService.resolve_prezzo`, che solleva. Deve chiamare il nucleo `_esito`
(A1) — nuovo metodo dedicato, es. `PricingService.resolve_prezzo_esito()` — e:

* se risolve → prezzo come oggi;
* se non risolve → riga salvata con `prezzo_unitario = NULL` e `esito_codice`
  restituito nella risposta come **avviso**, non come errore.

⚠️ **Solo per il DDT.** Ordini, preventivi, contratti e offerte continuano a
chiamare il guscio che solleva: l'allentamento non è del pricing, è del DDT.

**BE-2 — Il FE deve poter dire «senza prezzo» e non solo «risolvilo tu».**
Oggi il campo vuoto significa *auto* (`riga_prezzo_auto_hint`: «Lascia vuoto per
risolvere il prezzo dal listino»). Con BE-1 i due casi collassano bene — vuoto =
prova, e se non riesce resta vuoto — quindi **non serve un terzo controllo**:
serve che l'avviso di BE-1 arrivi al FE e sia mostrato come tale.

**FE-1 — L'avviso, non l'errore.** Prezzo non risolto → badge/hint sulla riga con
il testo dell'`esito_codice`, mai un toast rosso che blocca. Il rosso arriva
all'emissione, dal gate, ed è già scritto e già parlante
(`E_DDT_PREZZO_NON_RISOLVIBILE`, 545, nomina la riga).

**BE-3 — Nessuna azione su ordini/preventivi.** Registrato per evitare che
qualcuno «uniformi» i quattro service: la quarta casella del §6 è un requisito, e
si prova con una controprova, non con la lettura del codice.

---

## 11. Definizione di «fatto» — riformulata sul verificato

Il §6 resta valido nella sostanza; qui è mappato su ciò che si è misurato, con
l'indicazione di **chi** chiude ogni casella.

| # | Casella (§6) | Chi | Stato oggi |
|---|---|---|---|
| 1 | Si carica una riga di DDT senza prezzo, articolo **semplice** | A + BE-1 | ⛔ bloccato dal BE |
| 1-bis | …articolo **composito** | C (K2 ✅) | ⛔ bloccato dal DB, tre volte |
| 2 | Causale fatturabile → emissione **blocca**, parlante, nomina la riga | — | ✅ **già fatto**, provato dai pgTAP; diventa raggiungibile in-app con la casella 1 |
| 3 | Causale non fatturabile → si emette e resta fuori da card e lister | — | ✅ **già fatto** (`fn_list_ddt_da_pushare`, `vw_dash_fatturazione_ddt`), con controprova a test |
| 3-bis | …**e** resta fuori anche se qualcuno cambia la causale dopo | B | ⛔ oggi difeso solo in Python |
| 4 | Ordini e preventivi continuano a rifiutare | BE-1 (per omissione) + C6 test 4 | ✅ per costruzione, **da provare** |
| 5 | La premessa di DL-28 allineata al comportamento reale | D1 | ⛔ e ora si sa **come** va corretta (R-2) |
| 6 | *(nuova)* Una ri-consegna **standalone** si emette senza digitare prezzi a mano | A + BE-1 | ⛔ R-3 — non era nel §6 perché il caso è nato ieri |

---

## 12. Riscontri sul DB di sviluppo (2026-08-18, sola lettura)

> ⚠️ I dati di sviluppo **non misurano la gravità**: dicono se un caso si presenta,
> non quanto costa. Servono a distinguere ciò che è successo da ciò che può
> succedere — non a decidere che ciò che non è successo non conta.

**Righe DDT attive senza prezzo** — 6, tutte con causale VENDITA o nessuna, tutte
**ri-consegne**, tutte con prezzo ereditabile dall'ordine:

| stato | causale | righe senza prezzo | ereditano |
|---|---|---|---|
| DRAFT | *(nessuna)* | 4 | sì (80,00) |
| EMESSO | VENDITA | 1 | sì (60,00) |
| CONSEGNATO | VENDITA | 1 | sì (60,00) |

Nessuna riga a prezzo **zero** in tutto il DB: lo `0` come affermazione non è mai
stato usato (R-6).

**Il gate di DL-28** — `E_DDT_PREZZO_NON_RISOLVIBILE`: 271 occorrenze, dal
2026-07-18 a oggi, **tutte** da `trg_ddt_a10_guard_causale_emissione_upd` e
**tutte** con un `ddt_id` che non esiste più → sono corse di pgTAP. Su un
documento reale: **zero**. Il gate funziona ed è provato; non è mai stato
attraversato da un operatore.

**Il rumore nel log** (R-9) — famiglia «prezzo che non c'è» in `dbops.error_log`:

| codice | righe |
|---|---|
| `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C` | 795 |
| `E_VENDITE_PRICING_FAILED` | 666 |
| `E_CATEGORIA_LISTINO_NON_MAPPATA` | 607 |
| `E_PREZZO_LISTINO_NON_TROVATO` | 586 |
| `E_DOC_COMPONENTE_LISTINO_MANCANTE` | 252 |
| `E_LISTINO_VERSIONE_NON_ATTIVA` | 158 |
| `E_ARTICOLO_ESCLUSO_DA_CONTRATTO` | 157 |
| `E_PREZZO_LISTINO_RIGA_NON_TROVATA` | 5 |

di cui **1.777 scritte da `pricing_service.resolve`**, cioè il BE che ri-logga un
codice che il DB aveva già loggato. ⚠️ Il log non distingue una corsa di test da
un uso reale — è out-of-transaction e sopravvive al ROLLBACK — quindi il numero
misura il **rumore complessivo**, non l'operatività. È comunque il rumore che una
riga di DDT senza prezzo produrrebbe a ogni salvataggio, moltiplicato per le righe.

**Compositi** — 16 articoli compositi attivi, 9 righe di DDT che li usano. Il caso
«kit in conto visione» non è un angolo remoto (D-5).

**Resi standalone** — 2 righe su 17. È la popolazione da cui può nascere la
ri-consegna senza prezzo ereditabile di R-3.

**Billing account senza categoria** (R-10) — **0 su 42**, e non per fortuna: la
colonna è **NOT NULL** dal 2026-04-14. Il ramo del resolver che presidia quel
caso non può scattare, e infatti non è mai scattato: `E_PREZZO_LISTINO_NON_TROVATO`
ha **0** righe di log scritte dal DB e **587** scritte dal backend, esattamente
quante ne ha `E_CATEGORIA_LISTINO_NON_MAPPATA` dallo stesso mittente e nello
stesso arco di date (F-4).
