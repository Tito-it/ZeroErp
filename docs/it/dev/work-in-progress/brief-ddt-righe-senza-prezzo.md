# Brief — il DDT deve ammettere righe a prezzo zero, e oggi non le ammette

> **Tipo**: brief (decisione presa, perimetro da chiudere) · **Data**: 2026-08-17 ·
> **rev**: 2026-08-18 analisi critica e piano DB (§7–§12) · **rev**: 2026-08-19
> **decisioni chiuse** — D-3 #3 (esito) e D-5 (K2) decise da Tid; D-3 #7 si è
> rivelato un ramo morto (R-10, F-4) ·
> **rev**: 2026-08-19 (sera) **PARTE II — piano BE/FE** (§13→§20), scritta dopo
> il push del team DB ·
> **Owner**: Tid · **Stato**: 🟢 **PERIMETRO DB CHIUSO — 2026-08-19.** Tutte e
> quattro le slice (A, B, C, D) scritte, applicate e collaudate: pgTAP verdi,
> baseline senza regressioni, cancelli statici verdi. 🔴 **Resta il solo lato
> applicativo**: le richieste **BE-1 → BE-4** del §10, da cui dipende l'unica
> casella che l'operatore vede ancora chiusa.
>
> ➡️ **Il piano applicativo è la PARTE II, §13→§20** — verifica del consegnato,
> sette rilievi (di cui tre correggono il §10: i codici da dichiarare sono
> **due**, il FE ha **due** muri che il §10 non nomina, e il flag `fatturabile`
> non arriva all'applicativo), sei decisioni, 4 slice BE + 5 FE. Il §10 resta
> come richiesta originale del team DB; dove i due divergono **vale la PARTE
> II**, che è stata scritta leggendo il codice.
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
tutto è in [brief-be-pricing-codice-errore-fantasma](../work-done/brief-be-pricing-codice-errore-fantasma.md),
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
> | `db/pgtap/vendite/test-fn-resolve-prezzo-listino-esito-v1.sql` | A3 — 12 test, **12 verdi come `zeroerp_app`** |
> | `20_code/vendite/20260819-10-…-contesto-e-ramo-morto-…yaml` | A5 — via il ramo morto (ritiro del 141) + P-6 del BE |
> | `20_code/vendite/20260819-11-…-guscio-codice-dedicato-…yaml` | A6 — il guard prende il codice che gli spetta |
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

### Slice B — L'intento, una volta emesso, non si cambia ✅ **SCRITTA E COLLAUDATA (2026-08-19)**

> ✅ **APPLICATA il 2026-08-19**, pgTAP 5/5 e baseline senza regressioni (corsa di Tid).
>
> | file | cosa |
> |---|---|
> | `80_data/sql/config/codici_errore.csv` + `messaggi_errore.csv` | B0 — `E_DDT_CAUSALE_IMMUTABILE` (932, classe CONFLITTO_STATO), **append** |
> | `20_code/vendite/20260819-20-…-trgfn-ddt-guard-causale-immutabile` | B1 — la funzione |
> | `20_code/vendite/20260819-21-…-trg-ddt-guard-causale-immutabile` | B2 — il trigger |
> | `db/pgtap/vendite/test-ddt-causale-immutabile-v1.sql` | B3 — 5 test |
>
> ⭐ **Due scelte che un guard scritto in fretta sbaglierebbe, ed entrambe hanno
> un test che le protegge:**
>
> * **si legge lo stato VECCHIO, non il nuovo.** L'`UPDATE` che porta
>   DRAFT→EMESSO scegliendo contestualmente la causale è l'operazione legittima
>   per eccellenza; guardando `NEW` la si boccerebbe, e il guard sarebbe verde
>   su tutto il resto (test 4);
> * **la clausola `WHEN` filtra sul valore, non sulla menzione.** `UPDATE OF
>   colonna` scatta anche quando le si riassegna lo **stesso** valore — cioè a
>   ogni salvataggio di testata che rimanda indietro tutti i campi del form.
>   Senza la `WHEN`, riemettere la stessa causale su un DDT spedito verrebbe
>   bloccato: un errore su un'operazione che non cambia niente (test 5).
>
> ⚠️ **Verifica sui guard restrittivi, come impone la regola.** I file pgTAP che
> impostano `causale_trasporto_id` sono **26**; eseguiti tutti col trigger
> attivo, **nessuno si rompe**. Tutti impostano la causale mentre il DDT è in
> bozza, prima di avanzare lo stato — che è anche l'ordine in cui lavora
> l'applicazione. L'unico rosso incontrato
> (`test-vw-situazione-merce-ordine-v1`, test 11 sullo scope) esce **identico
> con e senza** il guard.

#### Contenuto della slice

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

### Slice C — I compositi ✅ **SCRITTA E COLLAUDATA (2026-08-19)**

> ## ✅ CHIUSA — 2026-08-19
>
> **Tutti i changeSet applicati** (`20260819-12` → `-19`) e **pgTAP verde**,
> eseguito da Tid come `zeroerp_app` con RLS attiva e confrontato con la
> baseline: nessuna regressione. Il kit può viaggiare su un DDT che non vende.
>
> | file | cosa |
> |---|---|
> | `20_code/script/20260819-12-…-ricalcola-prezzo-padre-null-aware` | C2 — tre casi: 0 / NULL / SUM |
> | `00_schema/vendite/20260819-13-…-prezzo-nullable` | C1 — prezzo del componente facoltativo |
> | `20_code/vendite/20260819-14-…-fn-check-ddt-riga-richiede-prezzo` | C3a — «questo documento vende?» |
> | `20_code/vendite/20260819-15-…-prezzo-obbligatorio-when` | C3b — la `WHEN` sul trigger |
> | `20_code/script/20260819-16-…-componenti-per-causale` | C4 — il gate segue la causale |
> | `20_code/vendite/20260819-17-…-init-prezzo-facoltativo` | C5a — l'init scrive NULL |
> | `20_code/vendite/20260819-18-…-preview-nucleo` | C5b — la preview non logga più |
> | `00_schema/vendite/20260819-19-…-origine-nullable` | ⚠️ **non previsto dal piano** — vedi sotto |
> | `db/pgtap/vendite/test-ddt-componenti-senza-prezzo-v1.sql` | C6 — 8 test |
>
> ⛔ **`20260819-19` è la lezione della slice.** `origine_prezzo` è NOT NULL e il
> suo CHECK ammette sei valori, nessuno dei quali significa «non risolto» —
> perché fino a ieri il caso non esisteva. Con l'init che scrive il prezzo NULL,
> scrive anche l'origine NULL, e l'INSERT muore con `23502` **proprio nel caso
> che la slice serve ad abilitare**.
>
> ⚠️ E non si vedeva. I collaudi di C5 avevano verificato che l'init
> *compilasse* e che la preview *degradasse* — ma la preview non inserisce, e la
> compilazione non attraversa il ramo. Il difetto è uscito solo quando il pgTAP
> ha provato a costruire **davvero** un kit senza prezzi. La prima impressione è
> stata «il caso non è costruibile su questo DB»: era invece la slice,
> incompleta. È la stessa lente di R-5 — *un ramo si verifica dal percorso che
> lo attraversa*.
>
> ⭐ **Scelta di forma su C3**, che vale oltre questa slice: invece di
> parametrizzare `script.trgfn_componenti_check_prezzo_obbligatorio` — condivisa
> da **quattro** tabelle — si è cambiato **quando** il trigger scatta, con una
> clausola `WHEN`. Il codice condiviso non si tocca: preventivi, ordini e
> contratti restano identici bit per bit, e non c'è logica duplicata da tenere
> allineata fra le due strade.

#### Contenuto della slice

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

### Slice D — Verità documentale ✅ **FATTA (2026-08-19)**

> Nessuna migrazione: quattro documenti allineati al comportamento reale.
>
> | # | dove | cosa |
> |---|---|---|
> | D1 | `work-done/brief-design-fatturazione-due-lenti.md` §10 | **errata corrige a DL-28**: la premessa era falsa per metà, e si dice quale metà — il caso esisteva nel DB (e le ri-consegne lo producono), il gate era esercitato dai pgTAP, ma non è **mai** scattato su un documento reale |
> | D2 | `brief-be-fan-out-isolato-e-esito-parziale.md` §13.2 | la voce resta ⏸️ sospesa, ma **il blocco è cambiato di natura**: non più un pezzo di modello mancante, una riga di Python (BE-1) |
> | D3 | `COMMENT ON script.fn_check_ddt_emittibile` | fatto contestualmente a C4: dichiarava cinque presidi, uno dei quali non poteva scattare |
> | D4 | `dbzero/config/manual/causali_trasporto.md` | `fatturabile` spiegata per quello che è — **la colonna che decide se un documento entra nel giro della fatturazione** — in linguaggio comprensibile anche a chi non legge SQL |
> | D5 | `dbzero/*/manual/` | **doc concettuale degli oggetti nuovi e di quelli cambiati** (2026-08-19), vedi sotto |
>
> **D5 — le pagine `manual/`.** Le pagine auto-generate le rifà il migrate e non
> si toccano a mano: la doc concettuale sta in `manual/`, e andava scritta per i
> tre oggetti nuovi e **corretta** per quattro esistenti, che descrivevano un
> comportamento che questa attività ha cambiato.
>
> | | pagina |
> |---|---|
> | nuove | `vendite/manual/fn_resolve_prezzo_listino_v2_esito.md` · `fn_check_ddt_riga_richiede_prezzo.md` · `trgfn_ddt_guard_causale_immutabile.md` |
> | corrette | `script/manual/fn_ricalcola_prezzo_padre_da_componenti.md` (diceva `COALESCE(SUM,0)`) · `script/manual/fn_check_ddt_emittibile.md` (motivi componenti incondizionati) · `vendite/manual/ddt_righe_componenti.md` (colonne NOT NULL) · `vendite/manual/fn_ddt_riga_componenti_init.md` e `_preview.md` (dicevano che sollevano) |
>
> ⚠️ Nelle pagine corrette il testo storico **resta**, marcato come superato: chi
> legge deve poter vedere che cosa è cambiato e quando, non trovare una verità
> nuova senza traccia della vecchia.
>
> ℹ️ La riga `include-markdown` che aggancia il `manual/` all'auto-gen la scrive
> il generatore: comparirà alla prossima rigenerazione della doc.

#### Contenuto della slice

| # | Cosa | Dove |
|---|---|---|
| D1 | Correggere la premessa di DL-28 (§5 del brief), nella forma di R-2: **non** «il caso non esiste», ma «esiste, lo produce il DB, non ha interfaccia» | `docs/it/dev/work-done/brief-design-fatturazione-due-lenti.md` §10 |
| D2 | Registrare che la mezza casella «blocco parlante» di DL-28 è **provata dai pgTAP** e non provabile in-app finché BE-1 non entra | `brief-be-fan-out-isolato-e-esito-parziale.md` §13.2 |
| D3 | `COMMENT ON` di `fn_check_ddt_emittibile` — oggi dichiara cinque presidi, uno dei quali non può scattare | contestuale a C4 (o, con K1, un changeset di solo commento) |
| D4 | Doc manuale della causale come **dichiarazione d'intento** (unico posto dove l'operatore sceglie se la merce si vende) | `docs/it/dbzero/config/manual/causali_trasporto.md` |

### Ordine dei lavori e cosa consegna ciascuna slice

```
A (resolver a esito) ✅ ┬──► BE-1 (§10) 🔴 ──► articolo semplice senza prezzo
                       └──► C (compositi) ✅ ──► kit senza prezzo: FATTO
B (causale immutabile) ✅ ──────────────────► invariante spostato nel DB
D (documentale) ✅ ─────────────────────────► la doc smette di mentire
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
  ri-scrive lo stesso codice. ✅ **CHIUSO il 2026-08-19**, e su **tutti** i domini,
  non solo sul DDT: decisione DB+BE «il diario lo scrive il database, il backend
  non duplica», attuata in `ErrorManager.raise_from_database_error`. Il confine e'
  il **campo strutturato** — valorizzato solo da `fn_log_and_raise_error`, cioe'
  esattamente la funzione che ha gia' scritto la riga; i `RAISE EXCEPTION` diretti
  e gli errori PG veri continua a loggarli il BE, perche' li' non c'e' nessun
  doppione da evitare ma una riga da non perdere. Storia e prove nel brief
  [brief-be-pricing-codice-errore-fantasma](../work-done/brief-be-pricing-codice-errore-fantasma.md)
  §13 e §14-ter.
* **F-3** (R-6) — l'omaggio con rivalsa IVA non è rappresentabile: `OMAGGIO` è
  `fatturabile=false`, quindi non arriva mai a fattura. Da riprendere sull'asse
  `config.nature_doc_fiscale`, non su quello del prezzo.
* **F-4** (R-10) — ✅ **CHIUSO il 2026-08-19**, e la tesi era sbagliata: quelle righe le scriveva la suite di test del BE, non un percorso di produzione. Storia completa, prove e chiusura nel brief. ➡️ **Uscito da questo
  registro: ha un brief suo**,
  [brief-be-pricing-codice-errore-fantasma](../work-done/brief-be-pricing-codice-errore-fantasma.md)
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

**BE-4 — Rigenerare `error_policies_generated.py`: c'è un codice nuovo.** ⚠️
`E_VENDITE_PRICING_ESITO_ASSENTE` (931, classe **TECNICO** → 500, che è
corretto: se scatta non c'è nulla che l'operatore possa correggere). Nasce dal
rosso del rubinetto degli accumulatori: il guard «il nucleo non ha restituito
righe» usava `E_PARAMETRO_INVALIDO`, e lì non c'è nessun parametro invalido —
c'è un'invariante interna rotta.

**BE-3 — Nessuna azione su ordini/preventivi.** Registrato per evitare che
qualcuno «uniformi» i quattro service: la quarta casella del §6 è un requisito, e
si prova con una controprova, non con la lettura del codice.

---

## 11. Definizione di «fatto» — riformulata sul verificato

Il §6 resta valido nella sostanza; qui è mappato su ciò che si è misurato, con
l'indicazione di **chi** chiude ogni casella.

| # | Casella (§6) | Chi | Stato oggi |
|---|---|---|---|
| 1 | Si carica una riga di DDT senza prezzo, articolo **semplice** | A ✅ + BE-1 | 🔴 **ora dipende solo dal BE**: il DB gli ha dato lo strumento |
| 1-bis | …articolo **composito** | C (K2) | ✅ **FATTO 2026-08-19** — i tre muri del DB sono caduti |
| 2 | Causale fatturabile → emissione **blocca**, parlante, nomina la riga | — | ✅ **già fatto**, provato dai pgTAP; diventa raggiungibile in-app con la casella 1 |
| 3 | Causale non fatturabile → si emette e resta fuori da card e lister | — | ✅ **già fatto** (`fn_list_ddt_da_pushare`, `vw_dash_fatturazione_ddt`), con controprova a test |
| 3-bis | …**e** resta fuori anche se qualcuno cambia la causale dopo | B | ✅ **FATTO** — l'invariante è nel DB, non più in una costante Python |
| 4 | Ordini e preventivi continuano a rifiutare | C6 test 7 | ✅ **PROVATO**: sulle tre tabelle gemelle il prezzo del componente è ancora obbligatorio |
| 5 | La premessa di DL-28 allineata al comportamento reale | D1 | ✅ **FATTO** — errata corrige datata in fondo al §10 del design-of-record |
| 6 | *(nuova)* Una ri-consegna **standalone** si emette senza digitare prezzi a mano | A ✅ + BE-1 | 🔴 il DB è pronto; manca il BE |

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

---

# PARTE II — PIANO DI SVILUPPO BE/FE

> **Scritta il 2026-08-19** (sera), dopo il push del team DB (`d7fffc9f0`,
> merge `9c4cdba40`). **Owner della parte**: BE/FE. La PARTE I sopra resta
> intatta: qui non si ridiscute nulla di deciso, si chiude il lato applicativo
> delle richieste **BE-1 → BE-4** e **FE-1** del §10.
>
> **Metodo**: le definizioni DB dalla doc auto-generata (`docs/it/dbzero/**`,
> che riflette l'oggetto vivo), i percorsi dal codice letto riga per riga. Dove
> il §10 e il codice non concordano, **vince il codice** — ed è successo tre
> volte (V-1, V-3, V-4).

## 13. Verifica del consegnato dal DB

Tutte e quattro le slice sono nel repo e la doc auto-generata le riflette:
gli oggetti esistono **vivi**, non solo negli YAML.

| Slice | Oggetto | Riscontro |
|---|---|---|
| A1 | `vendite.fn_resolve_prezzo_listino_v2_esito` | ✅ 9 parametri, `RETURNS TABLE` **14 + 3** colonne (`esito_codice text`, `esito_context jsonb`, `esito_valori text[]`), `STABLE`. Il contesto di base porta **tutti e nove gli input** (P-6) |
| A2 | `vendite.fn_resolve_prezzo_listino_v2` | ✅ riscritta come guscio, **firma invariata** — `pricing_repository.py` non va toccato |
| A5 | ramo morto #7 | ✅ ritirato, e la doc `manual/` spiega **perché** (categoria NOT NULL dal 2026-04-14) |
| B1/B2 | `trgfn_ddt_guard_causale_immutabile` + `trg_ddt_a10_…_upd` | ✅ presenti, `WHEN (NEW IS DISTINCT FROM OLD)`, stato letto da `OLD` |
| C1 | `ddt_righe_componenti.prezzo_unitario` | ✅ **nullable** (`docs/…/tabelle/ddt_righe_componenti.md`). Le tre gemelle restano NOT NULL |
| C2 | `script.fn_ricalcola_prezzo_padre_da_componenti` | ✅ tre casi: nessun figlio → `0`, un figlio senza prezzo → **`NULL`**, altrimenti `SUM` |
| C3 | `vendite.fn_check_ddt_riga_richiede_prezzo` | ✅ nuova, pura, **fail-closed** su riga non leggibile; causale assente → `FALSE` |
| C4 | `script.fn_check_ddt_emittibile` | ✅ i due motivi «componenti» ora condizionati a `fatturabile`; `E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE` non è più morto |
| C5 | `fn_ddt_riga_componenti_init` / `_preview` | ✅ passano dal nucleo; l'init **inserisce con prezzo NULL** e registra `esito_codice` in `prezzo_resolver_context` |
| B0 | `E_DDT_CAUSALE_IMMUTABILE` (932) · `E_VENDITE_PRICING_ESITO_ASSENTE` (931) | ✅ a catalogo (`codici_errore.csv` + `messaggi_errore.csv`) |
| D | quattro documenti + cinque pagine `manual/` | ✅ presenti, col testo storico marcato come superato |

⭐ **Il contratto su cui poggia tutto il BE**, dalla doc di A1, e va citato nel
codice perché è la trappola numero uno:

> *«Una riga esce sempre. Chi la legge con `SELECT … INTO` deve comunque
> controllare `FOUND`: `SELECT INTO` senza righe non solleva, azzera le
> variabili — e un prezzo `NULL` verrebbe scambiato per un prezzo risolto.»*

Vale identico in Python: `row_to_dict(cursor)` ritorna `None` a zero righe, e
`None.get("prezzo_finale")` non è ciò che succede — succede che il codice a
valle legga un dict vuoto. Il guard va **esplicito** (BE-A2), non un `assert`
che sparisce con `python -O`.

⚠️ **Prerequisito operativo da spuntare prima di lanciare i test BE**: il
`GRANT EXECUTE` a `zeroerp_app` sulla `_esito` è dentro A1, ma il migrate va
comunque applicato sull'ambiente dove gira il BE. Se `resolve_prezzo_esito`
risponde «permesso negato» o «la funzione non esiste», la diagnosi è
**l'ambiente**, non il codice.

## 14. Rilievi della verifica — sette cose che il §10 non dice

### V-1 — I codici errore nuovi da dichiarare sono **due**, non uno

Il §10 (BE-4) nomina solo `E_VENDITE_PRICING_ESITO_ASSENTE`. Misurato sui due
file del backend:

| codice | `error_policies_generated.py` | `error_messages_fallback.py` |
|---|---|---|
| `E_VENDITE_PRICING_ESITO_ASSENTE` (931) | ✅ già presente (`TECNICO`) | ✅ già presente |
| **`E_DDT_CAUSALE_IMMUTABILE`** (932) | ❌ **assente** | ❌ **assente** |

Il 931 è entrato con la rigenerazione del `287fc9436`; il 932 è nato **dopo**,
con la slice B, e nessuno ha rigenerato da allora. Quindi metà di BE-4 è già
fatta e metà no — e la metà mancante è quella di un codice che il DB **solleva
davvero**, da un trigger.

⚠️ Il ripiego del 932 non può essere il messaggio a catalogo: quello ha un
`%s` (il numero del DDT). Il file dei ripieghi è per definizione la variante
**senza segnaposto** — è la ragione per cui esiste.

### V-2 — Il difetto che C2 ha chiuso nel DB è ancora aperto nel BE, un livello sopra

`DdtRepository.list_righe` calcola:

```sql
ROUND((r.quantita * COALESCE(r.prezzo_unitario, 0::numeric)) * (1 - …), 2) AS importo_riga
```

Con il prezzo a `NULL` quel `COALESCE` produce **`0,00 €`**: un importo
*affermato*, dove il modello dice «non si sa». È esattamente la figura di C2 —
un valore sbagliato al posto di un valore assente — spostata dalla `SUM` dei
componenti alla proiezione della riga. Il team DB ha rifiutato il `COALESCE`
per la stessa ragione, testualmente: *«non torna “per sicurezza”:
trasformerebbe il NULL in zero, cioè rifarebbe il difetto in un altro modo»*.

⭐ La stessa formula è in `ordini_repository.py` ed è **legittima lì**: sugli
ordini il prezzo non può mancare (il resolver solleva ancora — BE-3). Si tocca
solo il DDT.

### V-3 — Il FE blocca il kit senza prezzo in **due** punti, e il §10 non ne nomina nessuno

FE-1 chiede un badge al posto del toast. Ma prima del badge ci sono due
validazioni che rifiutano il salvataggio, ed entrambe sono nei building block
**condivisi** con preventivi/ordini/contratti:

| dove | riga | cosa fa |
|---|---|---|
| `_shared/componenti/ComponentiDialog.vue` | `obbligatoriInvalidi` → `if (prezzo == null) return true` | `canConfirm` resta `false`: la Conferma è disabilitata. **Un kit senza prezzi non si salva**, qualunque sia la causale |
| `_shared/componenti/ComponentiPanel.vue` | `isPrezzoEditatoValido` | blocca lo zero sul componente obbligatorio **incondizionatamente** — mirror di un trigger DB che dal 2026-08-19 è invece condizionato |

⛔ **Senza questi due, la slice C non si vede in-app.** Il DB ha tolto tre muri
e il FE ne tiene due in piedi. E c'è un terzo effetto più sottile:
`ComponentiPanel.getPrezzoVisualizzato` fa `Number(comp.prezzo_unitario)`, e
`Number(null)` è **0** — un componente senza prezzo si mostrerebbe a
`0,00 €`, cioè lo stesso difetto di V-2 nella cella.

### V-4 — Il FE non ha modo di sapere se il documento vende

`fn_check_ddt_riga_richiede_prezzo` risponde alla domanda lato DB. Lato
applicativo la risposta **non esiste**: `vw_ddt_lista` porta
`causale_trasporto_id`, `_codice` e `_descrizione`, ma **non** `fatturabile`.
Quindi né il BE né il FE possono replicare la regola senza reinventarla — e
reinventarla vorrebbe dire una whitelist di codici causale nel FE, che è
precisamente ciò che `config.causali_trasporto.fatturabile` esiste per evitare.

⭐ Non serve toccare la vista: `DdtRepository.get_ddt` già decora la vista con
colonne che non ha (`d.fatturazione_immediata`, `ba.istanza_utility_id`). Il
flag entra lì, con un `LEFT JOIN config.causali_trasporto`.

### V-5 — Il gate all'emissione è **già cablato nel FE**: non c'è niente da scrivere

Va detto per non rifarlo. `script.fn_available_actions_ddt` mette in
`available_actions` per la transizione EMESSO il campo **`reasons`** — l'array
completo dei motivi di `fn_check_ddt_emittibile`, ciascuno con `reason_key` —
e `core/composables/useDrawerActions.js` lo normalizza già in tooltip. Le
quattro chiavi i18n esistono **in entrambe** le lingue:

```
vendite.ddt.azione_reason.{causale_mancante, prezzo_non_risolvibile,
                           componenti_prezzo_pendente, componenti_non_valorizzati}
```

Quindi la casella 2 del §11 («causale fatturabile → emissione blocca,
parlante, nomina la riga») è chiusa **anche in-app** nel momento stesso in cui
la casella 1 diventa costruibile. Nessuna riga di FE.

### V-6 — Il ripiego a `"0"` di `_resolve_prezzo_riga` è il difetto di C2 in Python

```python
return str(prezzo) if prezzo is not None else "0"   # ddt_service.py:941
```

Oggi è irraggiungibile (il guscio solleva prima). Con il nucleo diventa **il
ramo normale**: ogni prezzo non risolto entrerebbe come `0`, cioè come
un'affermazione di valore nullo su un documento dove il modello vuole
l'astensione. Va tolto, non adattato.

Stessa figura sul ramo composito di `gestisci_riga`: il padre si inserisce con
`"0"` *«per soddisfare l'eventuale guard»*. Il guard non c'è
(`ddt_righe.prezzo_unitario` è nullable, senza CHECK — R-1) e il ricalcolo di
C2 sovrascrive comunque; ma se l'init dei componenti fallisse a metà,
rimarrebbe uno zero **falso** in tabella. Si inserisce `NULL`.

### V-7 — Due cose che funzionano già e non vanno toccate

* **Cancellare il prezzo di una riga esistente** funziona oggi:
  `aggiorna_riga` normalizza `""` → `None` (`empty_to_none`) e
  `execute_dynamic_update` gira senza `skip_none`, quindi scrive `NULL`.
* **La stampa del DDT non espone prezzi**: il template di
  `ddt_document_context_builder` non ha campi importo, e `format_importo(None)`
  ritorna `None` senza rompersi. Nessun rischio `StrictUndefined`.
* **Il push in commessa** non è toccato: le causali non fatturabili sono fuori
  dal lister per INNER JOIN (R-7), e le fatturabili non escono senza prezzo per
  il gate. `commesse_source_handlers` continua a usare il **guscio** per lo
  snapshot d'audit, ed è giusto così.

## 15. Decisioni BE/FE

### DEC-1 — Due metodi distinti su `PricingService`, non un flag sul metodo esistente ✅

`resolve_prezzo()` resta com'è e continua a chiamare il **guscio**. Accanto
nasce `resolve_prezzo_esito()`, che chiama il **nucleo**.

⛔ **Non** un parametro `raise_on_missing=False`: i due metodi hanno contratti
diversi — uno garantisce «o il prezzo o un'eccezione», l'altro garantisce «una
riga sempre, forse senza prezzo». Un flag li fonde in una firma il cui
contratto dipende da un booleano, e il call site perde la garanzia proprio dove
serve leggerla. È la stessa forma scelta dal DB (nucleo + guscio), e le due
parti si somigliano apposta.

### DEC-2 — `resolve_prezzo()` **non** viene riscritto come guscio Python ⛔

Era la simmetria ovvia, ed è sbagliata. Il guscio DB, oltre a sollevare,
**scrive la riga di diario** (`fn_log_and_raise_error`). Se il Python chiamasse
il nucleo e sollevasse per conto suo, ordini, preventivi, contratti e offerte
**perderebbero la traccia in `dbops.error_log`** — un cambio di comportamento su
quattro domini, dentro un intervento che il §10 (BE-3) dichiara *«nessuna
azione su ordini/preventivi»*.

⭐ Effetto collaterale voluto: sul DDT il doppio log di **F-2** sparisce del
tutto (il nucleo non scrive, e il BE non ha più un `DatabaseError` da
ri-loggare).

> ⚠️ **Aggiornamento 2026-08-19 (pomeriggio)**: la seconda metà di questa frase —
> *«sugli altri quattro resta»* — **non è più vera, ed è una buona notizia**.
> F-2 è stato chiuso **ovunque** poche ore dopo, per un'altra strada: il BE non
> ri-logga più ciò che il database ha già scritto (vedi il registro, F-2).
> **DEC-2 regge lo stesso**, e la ragione principale non cambia: se il Python
> chiamasse il nucleo e sollevasse per conto suo, la riga di diario non la
> scriverebbe *nessuno* dei due — il nucleo non scrive, e il BE ha smesso. Il
> guscio DB resta l'unico che la scrive per ordini, preventivi, contratti e
> offerte.

### DEC-3 — L'avviso viaggia nel `data` della risposta, non nell'envelope errori

La classe `AVVISO` del catalogo, per progetto, *«si scrive nel diario e non
raggiunge mai il client»* (`api.md`). Un prezzo non risolto **deve** raggiungere
il client, e non è un rifiuto: la risposta di `POST /righe/` resta `200` e porta
un campo in più.

```jsonc
{ "data": { "ddt_id": 12, "riga_id": 88, "is_composito": false,
            "prezzo_esito": { "codice": "E_CATEGORIA_LISTINO_NON_MAPPATA",
                              "messaggio": "Nessuna mappa categoria → listino …" } } }
```

`prezzo_esito` è `null` quando il prezzo è stato risolto. **Nessun codice `W_`
nuovo**: la famiglia dei warning è per ciò che finisce nel diario, e qui il
diario non si tocca (è il punto della slice A).

### DEC-4 — Il testo dell'avviso si prende dal ripiego, non si riscrive

`ErrorPolicyRegistry.resolve(codice).user_message` restituisce il messaggio
**senza segnaposto**, che è esattamente ciò che serve (i valori dell'esito non
si vogliono mostrare all'operatore: `esito_valori` è materiale da diario).

⛔ Non si aggiungono chiavi i18n nel FE per gli otto esiti: sarebbe una seconda
copia del catalogo, e divergerebbe. Il FE mostra la stringa che riceve.

### DEC-5 — «Questo documento vende?» ha **una** sede lato applicativo

Il flag `causale_trasporto_fatturabile` sulla testata, esposto grezzo
(`true` / `false` / `null`), e la regola di lettura è la stessa della funzione
DB: **solo `=== true` significa "vende"**. Il `null` (bozza senza causale) sta
col `false`.

⚠️ **Il BE non fa `COALESCE(false)`**: al FE serve distinguere «non vende» da
«non l'ha ancora detto» per scegliere il testo dell'avviso — «documento di solo
trasporto» è un'altra frase da «causale non ancora scelta».

### DEC-6 — Nella UI, prezzo assente ≠ prezzo zero

`formatCurrency(null)` ritorna stringa vuota, e una cella vuota si legge come
«non l'ho guardato». Serve un segno positivo: un `Tag` «senza prezzo». Lo zero
resta `0,00 €`, come qualunque altro importo.


### DEC-7 — La validazione input del resolver si **estrae** (regola del 2) ✅

**Decisione di Tid, 2026-08-19**: *«si estrae — mai duplicare, o quasi»*.

`resolve_prezzo` e `resolve_prezzo_esito` validano gli **stessi otto input**
nello stesso modo: non e' una somiglianza, e' la stessa cosa scritta due volte.
Va in un privato del modulo, `_valida_input_resolver(...)`, chiamato da
entrambi.

⚠️ **Cosa NON entra nell'helper**, o l'estrazione diventa un accentratore: solo
i guard sugli input (uuid, interi positivi, `date`). La traduzione del
`DatabaseError` resta nei due metodi, perche' li' **differiscono** — il guscio
traduce anche i codici del listino, il nucleo no (DEC-2).

⭐ Il beneficio vero non e' risparmiare otto righe: e' che una regola di
validazione nuova entra **in un posto solo**. La forma della duplicazione che
questo repository ha gia' pagato — due copie che divergono in silenzio, e il
difetto vive nella copia che nessuno guarda — nasce sempre cosi'.

### DEC-8 — Il *perche'* di un prezzo assente si persiste anche sulla riga semplice ✅

**Decisione di Tid, 2026-08-19**: F-7 si fa, dentro BE-B.

Oggi l'asimmetria e' questa, e non ha una ragione di modello:

| | dove finisce il motivo | sopravvive al ricarico? |
|---|---|---|
| riga **composita** (figli) | `ddt_righe_componenti.prezzo_resolver_context`, scritto dall'init DB | ✅ si' |
| riga **semplice** | solo nella risposta del save (`prezzo_esito`, DEC-3) | ⛔ no |

**Sede scelta: `ddt_righe.meta`**, chiave **`prezzo_resolver_context`**.

⭐ Il nome non e' una preferenza: e' **lo stesso** della colonna che il DB usa
sui componenti. Due tabelle, un nome, una domanda sola per trovarli entrambi —
mentre `meta.motivo_prezzo` avrebbe funzionato oggi e sarebbe stato illeggibile
fra sei mesi.

Perche' `meta` e non una colonna nuova: `ddt_righe.meta` e' `jsonb NOT NULL
DEFAULT '{}'` ed e' **gia'** nella whitelist di create e update
(`_CREATE_KEYS_RIGA`, `_UPDATE_KEYS_RIGA`) — quindi F-7 non chiede niente al team
DB, e resta interamente lato BE. Se un giorno il dato servisse a una query o a
un indice, quello sara' il momento di chiedere una colonna: non prima.

⚠️ **Tre confini, o la scrittura in `meta` diventa un pozzo:**

1. **si scrive solo quando il nucleo NON risolve.** Prezzo risolto = nessuna
   chiave: l'assenza e' informazione, e una chiave `{"esito_codice": null}` su
   ogni riga sarebbe rumore su cui poi si scrivono `if` sbagliati;
2. **si fonde col `meta` del client, non lo sostituisce.** Il campo e' suo e
   arriva dal payload: `{**meta_client, "prezzo_resolver_context": {...}}`;
3. **`aggiorna_riga` non si tocca** (V-7 vale ancora). Se l'operatore cancella
   il prezzo a mano il motivo non e' del resolver — e inventargliene uno sarebbe
   peggio che non averlo.

## 16. Piano BE

> Convenzioni del progetto: header standard sui file nuovi, `# Scopo:` prima di
> ogni `def`, `ErrorManager.require(...)` + `assert` per il type checker,
> nessun `try/except Exception` nelle view.

### BE-A — Il nucleo arriva in Python  🔴 *è il pezzo da cui dipende tutto*

| # | File | Cosa |
|---|---|---|
| A1 | `apps/vendite/db/pricing_repository.py` | `resolve_prezzo_listino_v2_esito(...)`: **stessa** query decorata (i sei LEFT JOIN che espongono codice/descrizione), su `vendite.fn_resolve_prezzo_listino_v2_esito`, con in più `r.esito_codice`, `r.esito_context`, `r.esito_valori`. Stessi 9 argomenti posizionali |
| A2 | idem | ⛔ **Guard esplicito su zero righe**: `row_to_dict` → `None` significa che il contratto «una riga esce sempre» è rotto. `ErrorManager.require(row is not None, code="E_VENDITE_PRICING_ESITO_ASSENTE", …)` + `assert`. È lo **stesso codice** che il guscio DB usa per lo stesso invariante: due lati, un significato. ⚠️ Non un `assert` nudo — con `-O` sparisce e il `None` prosegue |
| A3 | `apps/vendite/services/pricing_service.py` | `resolve_prezzo_esito(...)`: stessa validazione input di `resolve_prezzo`, poi il repo A1. Il `try/except DatabaseError` **resta**: i due `E_PARAMETRO_INVALIDO` sollevano ancora anche dal nucleo (regola D-3), e il traduttore serve a dargli il codice giusto |
| A4 | idem | ✅ **Deciso da Tid il 2026-08-19: si estrae** (DEC-7). `_valida_input_resolver(...)` privato nel modulo, chiamato da `resolve_prezzo` e `resolve_prezzo_esito`. Dentro **solo** i guard sugli input; la traduzione del `DatabaseError` resta nei due metodi, dove differisce |

**Test (A5)** — `apps/vendite/tests/services/test_pricing_service.py`,
`unittest.TestCase` con repository mockato:

1. nucleo che risolve → `esito_codice is None` e prezzo valorizzato;
2. nucleo che **non** risolve → una riga, prezzo `None`, `esito_codice`
   valorizzato, **nessuna eccezione**;
3. repo che torna `None` → `ServiceError` con `E_VENDITE_PRICING_ESITO_ASSENTE`
   (il guard di A2, che è l'unica cosa che quel codice presidia);
4. `E_PARAMETRO_INVALIDO` continua a sollevare (`DatabaseError` mockato).

### BE-B — Il DDT smette di pretendere il prezzo

| # | File | Cosa |
|---|---|---|
| B1 | `apps/vendite/services/ddt_service.py` | `_resolve_prezzo_riga` → chiama `resolve_prezzo_esito` e ritorna una coppia `(prezzo | None, esito_codice | None)` — un `NamedTuple` locale, non una tupla nuda: il call site deve poter leggere i nomi. ⛔ **Via il ripiego `"0"`** (V-6) |
| B2 | idem | `gestisci_riga`, ramo semplice: `prezzo_unitario` resta `None` se il nucleo non risolve; l'esito entra nel dict di ritorno come `prezzo_esito` (`{codice, messaggio}` da `ErrorPolicyRegistry`, DEC-4), `None` altrimenti |
| B3 | idem | `gestisci_riga`, ramo composito: si inserisce **`None`**, non `"0"` (V-6). Il commento va riscritto: il guard che giustificava lo zero non esiste, e il ricalcolo di C2 mette `NULL` se un figlio è scoperto |
| B4 | `apps/vendite/db/ddt_repository.py` | `list_righe`: **via il `COALESCE(r.prezzo_unitario, 0)`** (V-2). `importo_riga` diventa `NULL` quando il prezzo manca. ⚠️ Solo qui: `ordini_repository.py` resta identico |
| B5 | idem | `get_ddt`: `LEFT JOIN config.causali_trasporto ct ON ct.id = v.causale_trasporto_id` → `ct.fatturabile AS causale_trasporto_fatturabile` (V-4, DEC-5). Grezzo, senza `COALESCE` |

| B7 | idem | **F-7 / DEC-8**: quando il nucleo non risolve su articolo **semplice**, `gestisci_riga` persiste il motivo in `meta` — `{**meta_client, "prezzo_resolver_context": {"esito_codice": <codice>}}`. Solo in create, solo quando il prezzo manca, fuso col `meta` del client |

⚠️ **`aggiorna_riga` non si tocca** (V-7): cancellare il prezzo funziona già.
Va però coperto da un test, perché oggi nessuno lo prova e diventa un
comportamento su cui il FE si appoggia.

**Test (B6)** — `apps/vendite/tests/services/test_ddt_service.py` e
`tests/api/test_ddt_api.py`:

1. articolo semplice, nucleo che non risolve → `create_riga` chiamato con
   `prezzo_unitario=None` **e** risposta con `prezzo_esito.codice`;
2. articolo semplice, nucleo che risolve → identico a oggi, `prezzo_esito`
   assente;
3. composito → `create_riga` con `prezzo_unitario=None` (non `"0"`);
4. PATCH riga con `prezzo_unitario: ""` → `update_riga` riceve `None`;
5. ⭐ **controprova BE-3**: `ordini_service._resolve_prezzo_riga` continua a
   chiamare `resolve_prezzo` (il guscio) e a propagare l'eccezione. La quarta
   casella del §6 *«si prova con una controprova, non con la lettura del
   codice»* — quindi un test, non un commento.

### BE-C — I due codici nuovi entrano nel dizionario (BE-4, esteso da V-1)

| # | Cosa | Stato |
|---|---|---|
| C1 | `./manage-env.sh genera_error_policies` → il modulo generato prende `E_DDT_CAUSALE_IMMUTABILE: "CONFLITTO_STATO"`. ⛔ Non si edita a mano: la prossima rigenerazione butterebbe via tutto | ✅ **2026-08-19** — 719 → 720 voci |
| C2 | `error_messages_fallback.py`, **a mano**: la variante **senza `%s`** del 932 — «La causale di trasporto non si può cambiare dopo l'emissione del DDT.» | ✅ **2026-08-19**, frase come da piano |
| C3 | `./manage-env.sh genera_error_policies --check` verde (è il test `test_error_policies_divergenza_db` che gira in CI) | ✅ verde, **3.832 test verdi** |

⭐ **Il 931 era gia' entrato prima, e non per bravura**: `E_VENDITE_PRICING_ESITO_ASSENTE`
e' stato registrato la mattina del 2026-08-19 perche' il cancello
`test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` e' andato **rosso** appena il
team DB ha seminato il codice. E' la terza volta in un giorno che un codice
nuovo arriva senza il suo ripiego: il ripiego lo scrive il BE, ma saperlo quando
il codice viene seminato costa al DB una riga e a noi una CI rossa in meno.

⚠️ **Prerequisito, e non è formale**: il DB dell'ambiente deve avere applicato
il CSV di `80_data`, e **git deve essere allineato o avanti**. Rigenerare con il
DB avanti rispetto al repo scrive nel modulo codici che nessun commit dichiara.
Oggi la condizione è soddisfatta: il CSV è dentro `d7fffc9f0`.

⭐ Nota di proporzione sul 932: il BE **non espone** il cambio di causale fuori
dalla bozza (`_STATI_MODIFICABILI = {"DRAFT"}`), quindi il codice non può
arrivare all'operatore oggi. Si dichiara lo stesso — un codice che il DB
solleva e che il dizionario non conosce diventa un 500 muto il giorno in cui la
porta si apre, e quel giorno nessuno collegherà le due cose.

### BE-D — Documentazione API

`docs/it/dev/api.md` + la doc del dominio: il campo `prezzo_esito` nella
risposta di `POST /api/v1/vendite/ddt/<id>/righe/`, e la frase che lo spiega —
**il DDT è l'unico documento dove il prezzo mancante non è un errore**.

## 17. Piano FE

### FE-A — La testata dice se il documento vende

`DdtDrawer.vue`: `causaleFatturabile = computed(() => detail.value?.causale_trasporto_fatturabile === true)` (DEC-5), passato come prop a
`DdtRigheTable` → `DdtRigaForm` → `ComponentiDialog` / `DdtRigaComponentiPanel`.

### FE-B — L'avviso, non l'errore (FE-1 del §10)

| # | Dove | Cosa |
|---|---|---|
| B1 | `DdtRigaForm.vue`, `handleSave` | Se `result.prezzo_esito` → `notify.success` (la riga **è** salvata) **più** un `notify.warn` col `messaggio` dell'esito. Mai `notify.error`: il rosso è dell'emissione, ed è già scritto (V-5) |
| B2 | `DdtRigaForm.vue`, campo prezzo | Testo dell'hint da riscrivere. Oggi: *«Lascia vuoto per risolvere il prezzo dal listino.»* Con BE-1 la frase è falsa a metà — il prezzo può restare vuoto. Nuova, in `it.json` **e** `en.json`: *«Lascia vuoto per risolvere il prezzo dal listino; se non è risolvibile la riga resta senza prezzo.»* |
| B3 | idem | ⚠️ **In EDIT la frase è un'altra**: `aggiorna_riga` non ha auto-fill, quindi lì il campo vuoto significa «nessun prezzo», non «provaci». Due chiavi, non una — l'asimmetria esiste già oggi e questo è il primo momento in cui si vede |

### FE-C — La riga senza prezzo si vede (DEC-6)

`DdtRigheTable.vue`, colonna `prezzo_unitario`: quando `data.prezzo_unitario == null`,
un `<Tag severity="secondary">` con `vendite.ddt.riga_senza_prezzo` al posto
della cella vuota. Idem per `importo_riga`, che dopo B4 arriva `null`.

### FE-D — Il kit può viaggiare senza prezzi (rimozione dei due muri di V-3)

| # | File | Cosa |
|---|---|---|
| D1 | `_shared/componenti/ComponentiDialog.vue` | Nuova prop `prezzoRichiesto: { type: Boolean, default: true }`. Con `false`, `obbligatoriInvalidi` **non** considera invalido il prezzo `null`. ⚠️ Il `default: true` non è pigrizia: preventivi, ordini, contratti e listini non passano la prop e restano **identici bit per bit**. È la stessa scelta del team DB su C3 — non si tocca il codice condiviso, si cambia quando la regola si applica |
| D2 | `_shared/componenti/ComponentiPanel.vue` | Stessa prop. `isPrezzoEditatoValido` diventa condizionata, come il trigger DB dopo C3 |
| D3 | idem | `getPrezzoVisualizzato`: `Number(null)` è `0` — va restituito `null` e la cella deve mostrare il `Tag` di FE-C, non `0,00 €` |
| D4 | `DdtRigaForm.vue` / `DdtRigaComponentiPanel.vue` | Passano `:prezzo-richiesto="causaleFatturabile"` |

⭐ **Il `default: true` è ciò che rende questa slice sicura**, ed è l'unico
motivo per cui si può toccare un componente usato da cinque contesti senza
rileggerli tutti e cinque.

### FE-E — i18n

Chiavi nuove in `it.json` **e** `en.json` (il presidio
`scripts/check_i18n_keys.py` le vuole simmetriche):
`vendite.ddt.riga_senza_prezzo`, `vendite.ddt.riga_prezzo_auto_hint` (riscritta),
`vendite.ddt.riga_prezzo_edit_hint`, `vendite.ddt.componenti_senza_prezzo_hint`.

⛔ **Nessuna chiave per gli otto esiti del resolver** (DEC-4).

## 18. Ordine dei lavori

```
BE-A (nucleo in Python) 🔴 ──┬──► BE-B (il DDT non pretende) ──┬──► FE-B/FE-C  ► riga semplice senza prezzo
                             │                                 └──► FE-A (flag testata) ──► FE-D ► kit
BE-C (i due codici)      ────┴── indipendente, si fa in qualunque momento
BE-D (doc API)           ─────── dopo BE-B
```

* **BE-A da sola**: nessun effetto visibile, come la slice A lato DB. È il
  prerequisito di tutto.
* **BE-A + BE-B**: chiude le caselle **1** e **6** del §11 — l'articolo
  semplice senza prezzo e la ri-consegna standalone. Da qui il gate di DL-28 è
  **raggiungibile in-app** per la prima volta, e la casella 2 si chiude da sé
  (V-5).
* **+ FE-A/B/C**: l'operatore vede che cosa è successo invece di subirlo.
* **+ FE-D**: il kit in conto visione, che il DB già ammette e che oggi il FE
  rifiuta.
* **BE-C**: indipendente, e la sola che ha un prerequisito d'ambiente.

## 19. Definizione di «fatto» — colonna BE/FE

Ripresa dal §11, con quel che manca dopo questa PARTE II.

| # | Casella | Chi la chiude | Come si prova |
|---|---|---|---|
| 1 | Riga DDT senza prezzo, articolo **semplice** | BE-A + BE-B | test BE-B6 §1, poi in-app: articolo fuori listino su DDT in bozza → riga salvata, avviso giallo |
| 1-bis | …articolo **composito** | FE-D | in-app: kit su DDT con causale CONTO_VISIONE → dialog confermabile, riga salvata, padre **senza** prezzo (non a zero) |
| 2 | Causale fatturabile → emissione blocca e nomina la riga | ✅ **nessuno** | già cablato (V-5): il tooltip del pulsante Emetti elenca i motivi |
| 3 | Causale non fatturabile → si emette e resta fuori da card e lister | ✅ già fatto | controprova a pgTAP, invariata |
| 3-bis | …anche se qualcuno cambia la causale dopo | ✅ già fatto (slice B) | + BE-C perché l'errore sia leggibile il giorno in cui affiora |
| 4 | Ordini e preventivi **continuano** a rifiutare | BE-B6 §5 | ⭐ una **controprova a test**, non la lettura del codice |
| 5 | Premessa di DL-28 allineata | ✅ già fatto (slice D) | — |
| 6 | Ri-consegna **standalone** senza digitare prezzi | BE-A + BE-B | in-app: reso standalone → ri-consegna → riga senza prezzo ereditabile, emissione bloccata **parlante** invece che a mano |

⚠️ Le caselle 1, 1-bis e 6 si chiudono **in-app da Tid**: sono tutte e tre casi
che il codice può simulare e che nessun test automatico ha mai attraversato
davvero — ed è esattamente lo scenario in cui la slice C ha scoperto
`20260819-19`, il changeSet che il piano non prevedeva.

## 20. Registro — voci nuove, fuori dal perimetro

* **F-5** — `importo_riga` con `COALESCE(prezzo, 0)` esiste anche in
  `ordini_repository.py:305`. Lì è **innocuo** (il prezzo non può mancare), ma
  è la stessa formula: se un giorno gli ordini ammetteranno il prezzo assente,
  il difetto di V-2 nasce già scritto. Da guardare *insieme*, non separatamente.
* **F-6** — Asimmetria create/edit sul prezzo di riga DDT: in create il campo
  vuoto significa «risolvilo tu», in edit «nessun prezzo». Preesistente, resa
  visibile da questo lavoro; FE-B3 la copre con due testi, non la rimuove.
* **F-7** — Il *perché* di un prezzo assente si perde sull'articolo semplice.
  Sul composito è persistito (`prezzo_resolver_context.esito_codice`, scritto
  dall'init); sul semplice l'`esito_codice` vive solo nella risposta del save e
  ricaricando la lista non c'è più. `ddt_righe.meta` è `jsonb NOT NULL` ed è già
  nella whitelist di create e update: persistervi l'esito darebbe la stessa
  simmetria padre/figli scelta dal DB con C2 e C3.
  ✅ **Deciso da Tid il 2026-08-19: si fa** — vedi **DEC-8**, ed entra nel piano
  come **B7** dentro BE-B. È uscita dal registro «fuori perimetro» per la via
  giusta: posta come decisione di modello, non infilata in una slice come
  dettaglio implementativo.

---

## 21. Stato dei lavori e ripartenza (2026-08-19, pomeriggio)

> ⚠️ **Questa sezione non ripete il piano**: il piano e' sopra — §16 (BE), §17
> (FE), §18 (ordine), §19 (definizione di «fatto»). Qui c'e' solo **dove siamo**,
> perche' un piano senza lo stato accanto costringe chi riparte a rileggerlo
> tutto per scoprire cosa manca.

### 21.1 Dove siamo

| blocco | stato | prova |
|---|---|---|
| **BE-C** — i due codici nel dizionario | ✅ **fatto** | policy 720 voci, i due ripieghi senza `%s`, `--check` verde, 3.832 test verdi |
| **BE-A** — il nucleo arriva in Python | ✅ **fatto** | A1-A5 sotto |
| **BE-B** — il DDT smette di pretendere il prezzo | ✅ **fatto** | B1-B7 sotto |
| **BE-D** — doc API (`prezzo_esito`) | ✅ **fatto** | sezione nuova in `api_ddt.md` |
| **FE-A → FE-E** | ✅ **fatto** | §21.1-quinquies |
| caselle 1, 1-bis, 6 del §19 | ⬜ validazione **in-app di Tid** | nessun test automatico le ha mai attraversate — il copione e' in [collaudo-in-app-ddt-righe-senza-prezzo.md](collaudo-in-app-ddt-righe-senza-prezzo.md) (9 prove, dati veri misurati il 2026-08-21) |

**Non committato al momento della scrittura**: le modifiche di BE-C vivono
nell'albero di lavoro insieme ad altro lavoro in corso.

### 21.1-bis Fatto oggi, oltre a BE-C

Due cose di questo perimetro sono state chiuse il 2026-08-19 **prima** che BE-A
partisse, e cambiano il testo del brief piu' sopra:

| # | Cosa | Dove l'ho scritto |
|---|---|---|
| **BE-C** | i due codici nel dizionario: policy rigenerate (720 voci) + i due ripieghi senza `%s` | §16, blocco BE-C, con le prove |
| **F-2** | il doppio log del pricing, chiuso **su tutti i domini** e non solo sul DDT | registro §20 · nota di aggiornamento su **DEC-2** |
| **F-4** | il «codice fantasma» del pricing: non lo scriveva la produzione, lo scriveva la suite di test | gia' uscito da questo registro, ha un brief suo |

⚠️ **F-2 e F-4 vengono da un altro brief e da un'altra giornata di lavoro**: sono
qui perche' questo registro li aveva aperti, e un registro che non si chiude
diventa un elenco di cose che «qualcuno prima o poi». Le prove stanno nel loro
brief, non duplicate qui.

⭐ La conseguenza pratica su questo piano: **DEC-2 va riletta con l'aggiornamento
accanto**. La sua ragione principale regge — anzi si rafforza — ma la frase
«sugli altri quattro il doppio log resta» oggi direbbe il falso a chi la legge.

### 21.1-ter BE-A — fatto il 2026-08-19

| # | Cosa | Dove |
|---|---|---|
| A1 | `resolve_prezzo_listino_v2_esito(...)` — stessa query decorata del guscio, sul nucleo, piu' le tre colonne di esito | `pricing_repository.py` |
| A2 | guard esplicito sulle zero righe → `E_VENDITE_PRICING_ESITO_ASSENTE` (`ErrorManager.require` + `assert`, **non** un `assert` nudo) | idem |
| A3 | `resolve_prezzo_esito(...)` — non solleva per «prezzo non risolto», il `try/except DatabaseError` **resta** per `E_PARAMETRO_INVALIDO` | `pricing_service.py` |
| A4 | `_valida_input_resolver(...)` estratto (DEC-7), chiamato dai due metodi | idem |
| A5 | 5 test nuovi: risolto · non risolto **senza eccezione** · riga assente · parametro invalido · input validati | `test_pricing_service.py` |

**Verifiche**: 18 test sul pricing, **3.837 sull'intera suite**, tutti verdi.

⭐ **E una prova che i mock non possono dare**: chiamata **reale** al DB dal
repository nuovo. Ha risposto `E_PARAMETRO_INVALIDO` su un billing account
inesistente — cioe' e' arrivata dentro la funzione (riga 116 del corpo): la
`_esito` **esiste**, `zeroerp_app` **puo' eseguirla** (il `GRANT` di A1 c'e') e i
nove argomenti combaciano per tipo. I nomi delle tre colonne di ritorno
verificati su `pg_proc`: 17 colonne, `esito_codice`/`esito_context`/`esito_valori`
presenti. Il prerequisito d'ambiente del §13 e' **spuntato**.

⚠️ Quello che la chiamata reale **non** ha potuto provare e' un giro a buon fine
end-to-end: `anagrafiche.billing_account` da shell risulta **vuota** — e' la RLS
senza GUC operatore, non un database senza dati. Si prova in-app, ed e' comunque
una delle caselle che il §19 assegna alla validazione di Tid.

### 21.1-quater BE-B e BE-D — fatto il 2026-08-19

| # | Cosa | Esito |
|---|---|---|
| B1 | `_resolve_prezzo_riga` ritorna `_EsitoPrezzoRiga(prezzo, codice)` e chiama il **nucleo**. ⛔ Via il ripiego `"0"` | fatto |
| B2 | ramo semplice: `prezzo_unitario` resta `None`; `prezzo_esito` `{codice, messaggio}` nella risposta, testo dal ripiego (DEC-3/DEC-4) | fatto |
| B3 | ramo composito: si inserisce `None`, non `"0"`; commento riscritto | fatto |
| B4 | `list_righe`: via il `COALESCE(prezzo, 0)` → `importo_riga` NULL. ⚠️ `ordini_repository.py:305` **non toccato**, come da V-2 | fatto |
| B5 | `get_ddt`: `causale_trasporto_fatturabile` grezzo, senza `COALESCE` (DEC-5) | fatto |
| B7 | F-7/DEC-8: il motivo persiste in `meta.prezzo_resolver_context`, fuso col `meta` del client, solo quando il prezzo manca | fatto |
| B6 | 6 test nuovi | verdi |
| BE-D | sezione «Righe senza prezzo» in `api_ddt.md`: `prezzo_esito`, `importo_riga` NULL, i tre stati di `causale_trasporto_fatturabile` | fatto |

**Suite completa: 3.843 verdi.**

⭐ **Le due prove sul DB vero**, che i mock non danno: la query di `get_ddt` con
il JOIN nuovo **gira** e restituisce 68 colonne fra cui
`causale_trasporto_fatturabile`; `list_righe` senza `COALESCE` **gira** e
restituisce ancora `importo_riga`. Un nome di colonna sbagliato sarebbe passato
indenne fra i mock e sarebbe morto in-app.

⭐ **La controprova del §19 casella 4 e' un test, non un commento**:
`OrdiniPrezzoInvariatoTests` verifica che gli ordini chiamino ancora il **guscio**
(`resolve_prezzo`) e **non** il nucleo, e che l'eccezione risalga. Che
`ordini_service` non sia stato toccato oggi lo dice il diff; il giorno in cui
qualcuno «uniformera' i due domini» il diff non ci sara' piu', il test si'.

⚠️ **Cosa resta prima di poter dire «casella 1 chiusa»**: il FE. Oggi il BE
salva la riga senza prezzo e dice perche', ma nessuna interfaccia lo mostra —
FE-A/B/C. E la prova finale e' in-app, di Tid (§19).

### 21.1-quinquies FE — fatto il 2026-08-19

| # | Cosa | File |
|---|---|---|
| FE-A | `causaleFatturabile` (confronto `=== true`, cosi' `null` NON pretende il prezzo) passato a righe → form → componenti | `DdtDrawer.vue` |
| FE-B1 | save riuscito + `notify.warn` col messaggio dell'esito. Mai rosso: il rosso e' dell'emissione | `DdtRigaForm.vue` |
| FE-B2/B3 | due hint diversi, **create** («se non e' risolvibile la riga resta senza prezzo») e **edit** («in modifica non viene ricalcolato») | idem + i18n |
| FE-C | `Tag` «Senza prezzo» su `prezzo_unitario` **e** su `importo_riga`, che dopo B4 arriva `null` | `DdtRigheTable.vue` |
| FE-D1/D2 | prop `prezzoRichiesto` (default `true`) su `ComponentiDialog` e `ComponentiPanel`: con `false` il prezzo assente non e' piu' un difetto | `_shared/componenti/` |
| FE-D3 | ⛔ `getPrezzoVisualizzato` non fa piu' `Number(null) → 0`: ritorna `null`, e la cella readonly mostra il tag | `ComponentiPanel.vue` |
| FE-D4 | il DDT passa `:prezzo-richiesto="causaleFatturabile"` a dialog e pannello | `DdtRigaForm.vue`, `DdtRigaComponentiPanel.vue` |
| FE-E | 4 chiavi, **it e en**, `check_i18n_keys.py` pulito | `locales/*.json` |

**Verifiche**: `oxlint` pulito sui file toccati, **build FE OK**, backend **3.843
verdi**.

⭐ **Il `default: true` delle due prop nuove e' la cosa che rende sicura la
slice**: preventivi, ordini, contratti e listino bundle non passano la prop e
restano identici. E' la stessa scelta del team DB su C3 — il codice condiviso
non si tocca, si cambia solo dove la regola si applica.

⚠️ **Uno scostamento dal piano, dichiarato**: la frase
`componenti_senza_prezzo_hint` l'ho messa in `DdtRigaForm.vue`, non dentro
`ComponentiPanel`. Quel componente e' condiviso da cinque contesti, e un testo
che parla della «causale di questo DDT» dentro un building block e' un dominio
che tracima: al BB passa un booleano, la spiegazione resta a casa sua.

⚠️ **Un errore che ho fatto e corretto, perche' e' la trappola di questi due
file**: le quattro chiavi i18n erano finite in `vendite.ordini` invece che in
`vendite.ddt` — `riga_prezzo_auto_hint` esiste **due volte** in `it.json`, e
prendere «l'ultima occorrenza» pesca il blocco sbagliato. Se ne e' accorto
`check_i18n_keys.py`, non io: le chiavi risultavano citate e mancanti. Ripristinato
il testo di ordini, verificato che il suo blocco sia intatto.

### 21.1-sexies Revisione critica del codice scritto — 7 rilievi, tutti corretti

Rilettura del solo codice di oggi (documentazione esclusa), cercando bug, codice
fragile, duplicazione e valori cablati. **Sette rilievi, tutti corretti**; i due
piu' seri sono duplicazioni che avevo introdotto io predicando il contrario.

| # | Rilievo | Dove | Cura |
|---|---|---|---|
| **1** | ⛔ **38 righe di SQL duplicate**: guscio e nucleo avevano la stessa decorazione (22 colonne, 6 LEFT JOIN) copiata, piu' due elenchi identici di nove argomenti posizionali | `pricing_repository.py` | estratti `_COLONNE_DECORATE`, `_JOIN_DECORAZIONE`, `_sql_resolver(...)`, `_argomenti_resolver(...)` |
| **2** | ⛔ **contesto del diario scritto due volte**, otto chiavi uguali nei due `except` | `pricing_service.py` | estratto `_contesto_diario(...)`, col commento sul *perche'* delle due chiavi (una copia sola) |
| **3** | **Ramo che non fa niente**: `prezzo_unitario = prezzo_unitario if ... else None`, cioe' un no-op, rimasto dove prima si forzava `"0"` | `ddt_service.py` | ramo rimosso; il *perche'* dell'assenza sta ora sopra il ramo che c'e' |
| **4** | **Import morto**: `Decimal` non serviva piu' dopo B1 | `ddt_service.py` | tolto (verificato che non fosse usato altrove) |
| **5** | ⚠️ **Chiave di dominio dentro un building block**: `t('vendite.ddt.riga_senza_prezzo')` in `ComponentiPanel`, usato da cinque contesti | `_shared/componenti/` | `t(localizedKey('senza_prezzo'))` + chiave in `vendite.componenti.panel` (it/en) |
| **6** | Idioma incoerente: `=== null \|\| === undefined` dove il repository usa `== null` | `DdtRigheTable.vue` | allineato |
| **7** | Codice errore come **stringa nuda** in mezzo al codice | `pricing_repository.py` | costante di modulo, col motivo per cui non si importa dal service (ciclo) |

⭐ **Il rilievo 1 e il 5 sono lo stesso errore in due linguaggi**, ed e' quello
su cui avevo appena scritto due decisioni (DEC-7: «mai duplicare»; e la nota sul
BB che non deve ospitare testo di dominio). Scrivere la regola e violarla nello
stesso pomeriggio e' il motivo per cui la rilettura serve **anche** a chi ha
scritto le regole — anzi, soprattutto.

⚠️ **Cosa NON ho cambiato, e perche'**:

* `getattr(settings, "ERROR_LOG_DB_ENABLED", True)` in `ErrorManager`: il default
  a `True` sembra difensivo di troppo, ma e' la direzione giusta — se un domani
  la setting sparisse, il diario torna acceso invece di spegnersi in silenzio;
* il `Tag` «senza prezzo» ripetuto su due colonne di `DdtRigheTable`: sono tre
  righe l'una, e un componente estratto per questo costerebbe piu' della
  duplicazione che toglie;
* `COALESCE(prezzo, 0)` in `ordini_repository.py:305`: e' **F-5**, si guarda
  insieme agli ordini (V-2) e non di straforo qui.

**Dopo le correzioni**: 3.843 test verdi, `oxlint` pulito sui file toccati,
build FE OK, `check_i18n_keys` pulito. E i due SQL generati sono stati
**rieseguiti sul DB vero** dopo l'estrazione: entrambi arrivano dentro la
funzione (errore di dominio sul BA inesistente), quindi l'estrazione non ha
cambiato la query.

### 21.2 Le decisioni sono chiuse: si puo' scrivere codice

Tutte le domande aperte del piano hanno risposta. L'ultima era **A4**, sciolta
oggi da Tid: **si estrae** (DEC-7). Nessun blocco resta in attesa di una
decisione — BE-A e' partibile.

⚠️ **Restava una cosa che non era una domanda del piano** — F-7, ora decisa — e
**una che lo resta**:

1. ✅ **F-7 — deciso il 2026-08-19: si fa** (DEC-8). Il motivo si persiste in
   `ddt_righe.meta`, chiave `prezzo_resolver_context` — **lo stesso nome** della
   colonna che il DB usa sui componenti. E' entrato nel piano come **B7**, dentro
   BE-B: non piu' una domanda aperta;
2. **F-5 — `COALESCE(prezzo, 0)` in `ordini_repository.py:305`.** Oggi innocuo
   (sugli ordini il prezzo non puo' mancare), ed e' la **stessa formula** che su
   DDT ha prodotto V-2. Si guarda insieme a quello, non separatamente: il giorno
   in cui gli ordini ammetteranno il prezzo assente, il difetto e' gia' scritto.

### 21.3 Prima di lanciare i test di BE-A

Il `GRANT EXECUTE` a `zeroerp_app` su `fn_resolve_prezzo_listino_v2_esito` sta
dentro la slice A1, ma **il migrate va applicato sull'ambiente dove gira il BE**.
Se `resolve_prezzo_esito` risponde «permesso negato» o «la funzione non esiste»,
la diagnosi e' **l'ambiente**, non il codice — e cercarla nel codice costa
un'ora.

### 21.4 Il contratto da citare nel codice, non da ricordare

> *«Una riga esce sempre. Chi la legge deve comunque controllare `FOUND`:
> `SELECT INTO` senza righe non solleva, azzera le variabili — e un prezzo
> `NULL` verrebbe scambiato per un prezzo risolto.»*

In Python la trappola e' identica: `row_to_dict(cursor)` ritorna `None` a zero
righe. Per questo BE-A2 chiede un guard **esplicito** con
`E_VENDITE_PRICING_ESITO_ASSENTE` — e non un `assert`, che con `python -O`
sparisce e lascia proseguire il `None`.
