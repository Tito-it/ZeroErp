# Analisi — simmetria del ciclo ordini fra `vendite` e `acquisti`

> Stato: **ANALISI**. Nessuna migration, nessun backend, nessun frontend.
> Le decisioni del §5 vanno chiuse **prima** di aprire il cantiere: ognuna cambia il DDL.
>
> Data creazione: 2026-09-01
> Branch target (futuro): `dev/db-tid` (DB) · `dev/backend-tid` (BE/FE)
>
> Riferimenti letti per scrivere questa analisi:
>
> * [`docs/it/dbzero/acquisti/`](/dbzero/acquisti/) — doc auto-generata dello schema (sorgente
>   autorevole per il DDL: gli YAML sono quasi sempre stantii)
> * [`_dominio-acquisti.md`](/dbzero/acquisti/_dominio-acquisti) — la pagina di dominio, che
>   dichiara già la cautela sulla simmetria
> * [sviluppo-preventivi-acquisti.md](sviluppo-preventivi-acquisti.md) — l'RFQ **a monte**
> * [listini-fornitori.md](listini-fornitori.md) — il **prezzo** della riga
> * [analisi-db-magazzino-aggancio-documento-e-produzione.md](analisi-db-magazzino-aggancio-documento-e-produzione.md) — D-1 e D-7 nominano acquisti
> * [brief-design-partita-merce-generalizzata](../work-done/brief-design-partita-merce-generalizzata.md) e
>   [brief-db-resi-vendita](../work-done/brief-db-resi-vendita.md) — il modello da specchiare per la ricezione
> * [brief-be-fe-crud-registri-di-numerazione.md](../work-done/brief-be-fe-crud-registri-di-numerazione.md) — il motore di numerazione, chiuso il 2026-09-01

---

## 0. In due parole, senza tecnicismi

Vogliamo gli **ordini di acquisto**. L'idea di partenza è ricopiare il ciclo di vendita
cambiando il cliente col fornitore.

Dal lato dei **programmi** — il backend e le schermate — l'idea regge, e regge bene: quasi
tutto ciò che serve esiste già come pezzo riutilizzabile, e va solo agganciato.

Dal lato della **base dati** no, e non per dettagli. Le tabelle degli acquisti sono state
disegnate nel 2025 e da allora la vendita è andata avanti: il perimetro dell'emittente
fiscale, la sicurezza riga per riga, i registri di numerazione, gli indirizzi, il catalogo dei
documenti. Sono strade che gli acquisti **non hanno percorso**, e che i pezzi riutilizzabili
danno per scontate.

⇒ **Prima si allinea la base dati, poi il resto si scrive quasi in fotocopia.** Nell'ordine
inverso si scrive due volte: una contro lo schema di oggi e una dopo averlo corretto.

---

## 1. Perimetro e metodo

**Copre**: l'ordine di acquisto (testata + righe) e la sua **ricezione** (DDT fornitore,
carico, reso al fornitore, attesa di ri-consegna).

**Non copre**, e sono cantieri loro: il preventivo di acquisto / RFQ, i listini fornitore, la
fattura passiva, il carico a magazzino nel dettaglio del ledger. Vedi §11.

⚠️ **Regola zero applicata a questo documento.** Le misure qui dentro sono **fatti datati**,
mai motivi. Dove si legge «zero righe» o «zero rotte» non è l'argomento: l'argomento è sempre
sulla **struttura** — che cosa il modello ammette, quale colonna esiste, quale vincolo c'è. Un
conteggio non decide niente e invecchia in silenzio.

Il DDL è stato letto dalla **doc auto-generata**, non dagli YAML.

---

## 2. Lo stato di oggi, per anello

Fatto misurato il **2026-09-01**, sul repo e sulla doc auto-generata.

| Anello | Acquisti | Gemello vendite (ordini) |
| --- | --- | --- |
| **Tabelle DB** | 9 (`ordini`, `ordini_righe`, `ordini_righe_fulfillment`, `ddt`, `ddt_righe`, `ddt_indirizzi`, `note` + 2 partizioni) | — |
| **Viste DB** | **0** | 7 |
| **Funzioni DB** | **2** (`fn_get_acquisti_note`, un trigger guard sull'indirizzo) | 18 |
| **Backend** | scheletro: `apps.py`, `models.py`, `admin.py`, `api/views.py` e `api/urls.py` **vuoti**, tre `README.md` segnaposto | 2.779 righe su 5 file, **29 rotte** |
| **Frontend** | due `.gitkeep` | 1.991 righe su 10 file |
| **Navigazione FE** | dominio presente in [`navigation.js:118`](../../../../frontend/src/core/navigation.js#L118), **menu L2 vuoto** (`'acquisti': []`) | 12 voci |
| **i18n** | radice `acquisti` **inesistente** in `it.json`/`en.json` | `vendite.ordini` popolata |
| **Area funzionale** | a catalogo (`aree_funzionali.csv` id 3), **zero azioni di processo** | 20 azioni su area 2 |
| **Liste configurabili** | nessuna | `vendite.ordini` (id 7) |

⭐ **Il numero che conta non è nessuno di questi**: è che le due funzioni di acquisti non
includono **né un motore di stato, né un generatore di numero, né una capability, né un
ricalcolo di totali**. Non è «poco lavoro fatto»: è che i quattro ganci a cui i building block
si attaccano non ci sono.

---

## 3. I documenti che esistono già, e che vincolano

⛔ **Non esiste nessun brief «ordini di acquisto»**, né in `work-in-progress/` né in
`work-done/`. Questo documento è il primo.

Esistono però quattro documenti che ci girano intorno e che **non si possono ignorare**:

| Documento | Stato | Perché vincola |
| --- | --- | --- |
| [sviluppo-preventivi-acquisti.md](sviluppo-preventivi-acquisti.md) | DA IMPLEMENTARE | È l'RFQ **a monte**. Dichiara come prerequisito «schema `acquisti` operativo: ordini, righe, ddt» e come proprio downstream l'ordine fornitore. ⇒ ciò che decidiamo qui sulla controparte e sugli stati **lo eredita** |
| [listini-fornitori.md](listini-fornitori.md) | ANALISI | È il **prezzo** della riga d'ordine. Finché non c'è, il prezzo si digita (§9) |
| [analisi-db-magazzino-aggancio-documento-e-produzione.md](analisi-db-magazzino-aggancio-documento-e-produzione.md) | APERTO | **D-1**: `magazzino.movimenti` ha due modi di dire «da dove viene», e il doppio «vale anche per `acquisti`, che ha lo stesso». **D-7**: «il DDT di acquisto non è una sorgente registrata». ⇒ il **carico** dipende da decisioni prese lì, non qui |
| [sviluppo-multi-face-da-completare.md](sviluppo-multi-face-da-completare.md) | APERTO | Il `FORNITORE_PORTALE` è la veste per cui esistono già (spente) le policy RLS di acquisti — §4.1 |

---

## 4. Le dodici divergenze

La pagina di dominio [`_dominio-acquisti.md`](/dbzero/acquisti/_dominio-acquisti) lo dice già,
ed è la frase da tenere presente leggendo tutto il resto:

> «la simmetria dei nomi non garantisce la simmetria delle colonne»

Qui sotto le divergenze **verificate sulla struttura**, raggruppate per decisione che aprono.

### 4.1 Il perimetro: emittente e RLS

**① `emittente_fiscale_id` non esiste su `acquisti.ordini`.**
In `vendite.ordini` è `NOT NULL` ed è il perno di cinque meccanismi in esercizio: RLS
`EF_WHITELIST`, scope emittente delle liste, registri di numerazione, template documentali,
cruscotti. Non è «una colonna in meno»: è **l'assenza dell'ancora** su cui tutto il perimetro
poggia.

**② Le policy RLS sono scritte e non armate.**
`00_schema/acquisti/20260419-65` e `-66` creano `rls_acquisti_ordini_fornitore_ownership` e il
gemello DDT. Il commento del changeSet lo dichiara: *«DRY RUN … Nessun ENABLE / FORCE»*, e
infatti **non esiste nessun `ENABLE ROW LEVEL SECURITY` su `acquisti.*`**.

Due cose da sapere, e la seconda è la più importante:

* una policy senza `ENABLE` **non presidia niente e sembra presidiare** — è la forma di
  difetto peggiore, quella che nessun test rende rosso;
* quelle due policy coprono il solo `FORNITORE_PORTALE` (il fornitore che guarda i propri
  ordini dal portale). **Per l'operatore interno non c'è nessuna policy**, e non può esserci
  finché non c'è ①.

### 4.2 Gli stati

**③ `config.stati_doc_ordini` è condivisa e parla vendite.**
Ci puntano le FK di `vendite.ordini` **e** di `acquisti.ordini`. Ma il vocabolario è del ciclo
attivo — `SPEDITO`, `CONSEGNATO`, `FATTURATO`, `EVASO` — e le `meta.nessuna_azione_key`
puntano a `vendite.ordini.stato_info.*`, cioè al **namespace i18n del frontend vendite**.

⛔ Ne discendono due cose, non una: un ordine di acquisto che riusa quegli stati mostrerebbe
**testi di vendita** a video, e — più grave — **nulla nel modello impedisce** a un ordine di
acquisto di trovarsi in stato `SPEDITO`. Una tabella condivisa senza discriminante è
fail-open per costruzione.

Il manuale della tabella lo dichiara già come rischio aperto:
> *«Mappa centrata sul ciclo di VENDITA. La tabella è condivisa con `acquisti.ordini` […] Un
> eventuale futuro resolver per l'ordine di acquisto dovrà validare che questa mappa calzi la
> sua semantica […] o valutare lo split della tabella.»*

⚠️ **E la seconda occorrenza è già lì**: `config.stati_doc_ddt` ha la stessa forma —
condivisa con `acquisti.ddt`, con stati `EMESSO`/`SPEDITO`/`CONSEGNATO`/`RESO` che descrivono
un documento **emesso da noi**, non uno ricevuto.

**④ Non esiste un motore di stato per acquisti.**
Per gli ordini di vendita ci sono `config.transizioni_stati_ordini`,
`trgfn_ordini_guard_transizione`, `script.fn_available_actions_ordine`. Per acquisti:
**niente**. Senza `fn_available_actions_*` la `DrawerActionsBar` non ha azioni da mappare, la
prop `infoKey` non ha sorgente, e le capability di riga (`fn_check_*` → colonna della vista)
non esistono. Cioè **tutto lo standard delle azioni resta muto**, non «da collegare».

### 4.3 La numerazione

**⑤ Assente, e non è «da collegare».**
`acquisti.ordini` ha `uq_ordini_ao_anno_serie_numero` e il lock
`trgfn_lock_columns('numero')` — ma **nessun generatore**: il numero va fornito da fuori e poi
si congela. Il motore chiuso il 2026-09-01 (`vendite.famiglie_documento` +
`vendite.registri_fatturazione`) è parametrico sulla tabella, ma va guardato da vicino: vedi
il §6, che risponde all'obiezione sul billing account.

### 4.4 Gli indirizzi

**⑥ Due modelli diversi dentro lo stesso schema — e uno dei due è già convergente.**

| | Forma | Conseguenza |
| --- | --- | --- |
| `acquisti.ddt_indirizzi` | snapshot **per tipo** (`UNIQUE(ddt_id, tipo_indirizzo_id)`), con `origine_indirizzo_id`/`origine_soggetto_ruolo_id` | ✅ **già convergente sul BB condiviso**, dal 2026-07-11: vedi sotto |
| `acquisti.ordini` | `indirizzo_consegna_id` **NOT NULL** + colonna `indirizzo_cons_snapshot` jsonb sulla testata | ⛔ il BB **non** si aggancia: non c'è tabella satellite |

⭐ **Il DDT di acquisto non è «da fare»: è già fatto e non usato.** Verificato il 2026-09-01:
`00_schema/acquisti/20260711-28` + `20_code/acquisti/20260711-29` hanno fatto convergere
`acquisti.ddt_indirizzi` sulla funzione parametrica condivisa —
`vendite.trgfn_tipi_indirizzi_only_allowed('ACQUISTI_DDT')` — e hanno **ritirato la funzione
dedicata di acquisti**. L'ambito `ACQUISTI_DDT` esiste nel CHECK di
`config.tipi_indirizzi_allowed` ed è **seminato** con due tipi: `CON` (consegna) e `FORNITURA`.
Il cantiere è [brief-db-indirizzi-documenti-simmetria-e-cascata](../work-done/brief-db-indirizzi-documenti-simmetria-e-cascata.md).

⇒ `acquisti.ordini` è quindi **l'unico documento del progetto rimasto sulla forma vecchia**,
non «il primo documento di acquisto da modellare». La differenza cambia la taglia del lavoro.

E il `NOT NULL` ha un secondo effetto, indipendente dal BB: **impedisce la bozza**. Non si
crea un ordine finché non si è scelto l'indirizzo — mentre tutto il pattern drawer del
progetto è auto-save della bozza (`useDrawerAutosaveBozza`, adottato da ordini, preventivi,
DDT). È la forma descritta in memoria come *«un `NOT NULL` va dove il dato SI PUÒ
fornire»*: qui l'anello finale rompe chi copia.

Il resto — *di chi* è l'indirizzo, e i due limiti veri del BB — sta al **§7-bis**.

### 4.5 La merce

**⑦ L'UNIQUE del DDT contraddice il proprio manuale.**
`uq_a_ddt_anno_serie_numero` è su `(anno, serie, numero)` — **senza il fornitore**, e
**senza** `WHERE numero IS NOT NULL` (a differenza dell'omologo su `ordini`, che è parziale).

Il manuale della stessa tabella dice testualmente il contrario:
> *«i vincoli di unicità del numero, se ci sono, vanno pensati **per fornitore** e non in
> assoluto: due fornitori diversi possono legittimamente emettere lo stesso numero»*

⛔ È il vincolo scritto che dice l'opposto del documento che lo spiega, e va corretto
**prima** che il backend cominci a scriverci: dopo, la correzione ha dei dati da sanare.

**⑧ `acquisti.ddt.ordine_id` non è di troppo: è SBAGLIATO.**

🔴 **Riformulato il 2026-09-01.** La prima stesura lo trattava come una ridondanza da
sciogliere — «due sedi per la stessa relazione, scegliamone una». È un modo di dirlo troppo
gentile, e sposta la discussione sul terreno dell'ordine invece che su quello del modello.

Esistono **sia** `acquisti.ddt.ordine_id` (FK di **testata**) **sia**
`acquisti.ordini_righe_fulfillment` (il ponte **riga-a-riga**). Il manuale dice già che il
legame «passa dal ponte […] non dalla testata». Ma la ragione vera è più netta:

> ⛔ **Un fornitore consegna abitualmente più ordini in una bolla sola.** Una FK di testata
> dice che **non può**. Il ponte riga-a-riga quel caso lo regge; la testata lo nega.

⇒ Non è «scegliamo una delle due sedi»: è che **una delle due nega un caso normale del
dominio**. La FK di testata va tolta, non arbitrata. ⚠️ E se serve una scorciatoia di lettura
(«l'ordine principale di questa bolla»), quella si **deriva** dal ponte — non si memorizza,
altrimenti torna lo stesso vincolo travestito da comodità.

⚠️ Resta vero che è la **stessa specie** del doppio che l'analisi magazzino discute in D-1, e
le due decisioni vanno prese guardandosi. Ma qui la risposta è già determinata dal dominio.

### 4.6 Il catalogo delle sorgenti

**⑨ Acquisti è fuori.**
`config.sorgenti` ha 10 righe, **tutte `vendite.*`**. Ne discende a cascata, e nessuna di
queste è un «di più»:

* nessun **lineage** (`vw_documento_lineage`) ⇒ nessun pannello «Passaggi», nessuna colonna
  «Transito» nelle liste;
* nessun **motore documentale** ⇒ nessuna stampa PDF dell'ordine fornitore (e oggi un
  `sorgente_tipo_id` valorizzato su `acquisti.ordini` punterebbe a una **sorgente di
  vendita**, cosa che nessun vincolo impedisce);
* nessuna voce in `config.tipi_entita` ⇒ il **bersaglio d'errore** non sa aprire un ordine di
  acquisto.

Lo segnala già il brief magazzino in D-7.

### 4.7, 4.8, 4.9 — le restanti

**⑩ Totali `*_atteso` senza chi li calcoli.** `vendite` ha `fn_ricalcola_totali_ordine` più
due trigger. `acquisti` ha `imponibile_tot_atteso` / `sconto_tot_atteso` / `iva_tot_atteso` /
`totale_doc_atteso` e **nessuna funzione**. ⭐ Il suffisso dice la semantica **giusta** —
l'ordine è un'aspettativa, la fattura del fornitore è il fatto — ma un totale che nessuno
riempie, a video, si legge come un difetto.

**⑪ Il trasporto sta sulla testata dell'ordine.** `causale_trasporto_id`, `aspetto_bene_id`,
`num_colli`, pesi, volume, `modalita_addebito_trasporto_id`, `data_ora_consegna_prev` stanno
su `acquisti.ordini`; in vendite vivono sul **DDT**. È una scelta difendibile (l'ordine dice
*come* vuoi che la merce arrivi, il DDT dice com'è arrivata) ma **va dichiarata**, perché
rompe lo specchio esattamente dove si copierebbe il codice.

**⑫ Minori, da sistemare nello stesso giro.**

* `acquisti.ordini.uid` è **nullable** mentre l'omologo di vendite è `NOT NULL`, e ci sta
  sopra un UNIQUE. Se `uid` diventa la chiave del lineage o del motore documentale, un NULL
  passa senza che nulla fallisca.
* Nessun `acquisti.ordini_righe_componenti`: da decidere se un ordine a fornitore espande i
  kit (§5, D-9).
* `acquisti.ddt_righe` non ha `iva_id` né prezzo — coerente con «registro la merce, non il
  valore», ma da confermare esplicitamente perché è ciò che rende il DDT di acquisto **non**
  una base di fatturazione.

---

## 5. Le decisioni — stato al 2026-09-01

⭐ Le risposte di Tid sono del **2026-09-01**, in conversazione. Restano **due punti aperti**
e una raccomandazione da confermare.

| # | Decisione | Risposta | Stato |
| --- | --- | --- | --- |
| **D-1** | **Perimetro emittente**: l'ordine di acquisto è dell'emittente fiscale? | ✅ **Sì, stesso schema di vendite**, `emittente_fiscale_id` ricavato dall'operatore | **CHIUSA** |
| **D-2** | **RLS**: si arma il perimetro operatore, e che si fa delle due policy fornitore in dry-run? | discende da D-1: EF_WHITELIST sull'operatore. ⚠️ **Le policy fornitore restano da decidere**: armarle insieme o lasciarle spente e dichiararlo | **aperta (parte)** |
| **D-3** | **Stati**: split o tabella unica? | ✅ **Tabella unica con le regole che suddividono il dominio**, «ma accetto consigli» → raccomandazione al **§7** | **CHIUSA sul principio, da confermare la forma** |
| **D-4** | **Motore di stato**: transizioni + `fn_available_actions_ordine_acquisto` + capability | discende da D-3 | aperta |
| **D-5** | **Numerazione**: motore di vendite o proprio? | ✅ **Quello di vendite**. Obiezione sul billing account → **§6**, l'obiezione è fondata | **CHIUSA sul principio** |
| **D-6** | **Indirizzi**: tabella satellite allineata al BB, o forma attuale? | ✅ **Stesso BB**. Verificato: l'ancora è un parametro, non «il cliente», e il DDT di acquisto **è già convergente**. Restano due limiti del BB da estendere → **§7-bis** | **CHIUSA sul principio** |
| **D-6b** | **L'ordine di acquisto ha DUE ancore** (sede fornitore / consegna nostra): mappa `tipo → colonna` sul BB (A) o ancora unica + scelta esplicita (B)? | aperta qui dal §7-bis. Raccomandazione: **A** | **APERTA** |
| **D-7** | **Perimetro del cantiere**: solo ordine, o ordine + ricezione? | ✅ **Ordine + ricezione DDT**, con il meccanismo carico / reso al fornitore / da ri-consegnare → **§8** | **CHIUSA** |
| **D-8** | **Prezzo**: a mano o listini fornitore? | ✅ **A mano**, con l'ipotesi di un «prezzo fornitore» sull'articolo → **§9** | **CHIUSA sul principio, da progettare** |
| **D-9** | **Kit / BoM**: l'ordine a fornitore espande i compositi? | ✅ **Sì, se l'articolo lo richiede** ⇒ `acquisti.ordini_righe_componenti` + i gemelli di `fn_ordine_riga_componenti_init` / `_preview`, modello snapshot come in vendite | **CHIUSA** |
| **D-10** | **Dove vive il motore di numerazione** ora che serve a due domini: resta in `vendite` o sale in `config`/`script`? | ✅ **Sale, ma NON adesso.** Si spacca: la correzione di `colonna_billing_account` è del Lotto 1; il **trasloco si rimanda** al giorno in cui il primo ordine di acquisto prende davvero un numero. Il secondo consumatore non esiste ancora ⇒ la regola del 2 non si applica → **§6** | **CHIUSA: fare la correzione, rimandare il trasloco** |
| **D-11** | **`config.ambiti`**: che farne (popolarla per il suo scopo localizzato, o ritirarla)? | ⛔ **fuori da questo cantiere** — §7 dice perché | rinviata |
| **D-12** | **Il numero della controparte**: dove sta, e come non collide col nostro | ✅ posta da Tid. `numero` = sempre il **nostro**; il riferimento del fornitore ha colonna propria. Su `acquisti.ddt` il `numero` liberato **si toglie**, non si tiene vuoto → **§6, «I DUE numeri»** | **CHIUSA sul principio** |
| **D-13** | **`acquisti.ddt.serie` e `.anno`**: sono del fornitore o nostri? | ✅ **Del fornitore** (Tid): `serie_fornitore`, `anno_fornitore`. Servono davvero, e servono all'unicità per fornitore — una bolla è identificata da **numero + anno del suo emittente**. La data di ricezione sta in una colonna data, non in un intero: tenerla in `anno` sarebbe la stessa collisione di `numero` un giro dopo → **§6** | **CHIUSA** |
| **D-13b** | **`acquisti.ddt.data`**: è la data del documento del fornitore o quella di ricezione? | emersa chiudendo D-13: è `NOT NULL DEFAULT CURRENT_DATE`, e **il default è il campanello**. Proposta: `data_documento_fornitore` (sua, senza default) + ricezione su `data_ora_consegna_eff`. ⛔ Sono tre colonne dello stesso documento: farne due su tre lascia la terza a mentire | **APERTA** |
| **D-14** | **La chiusura del ramo CREDITO** dei resi a fornitore | ⭐ buco individuato in revisione: la coda «da accreditare» non ha porta d'uscita finché non c'è il ciclo passivo. Serve la **dichiarazione esplicita di accredito**, sul modello di `resi_righe_rinunce` → **§8** | **da progettare — è del Lotto 3** |
| **D-15** | **I presidi della classe «esiste e non è armata»** (3 viste `dbops` che devono restare vuote) | ⭐ proposto in revisione: 4 istanze in 2 analisi, nessuna produce un rosso → **§9-bis**. ⚠️ **cantiere di `dbops`, non di questo** | **proposta, fuori perimetro** |

---

## 6. Approfondimento: la numerazione, e perché avevo nominato il billing account

**L'obiezione è fondata: il billing account con la numerazione non c'entra niente.** Avevo
citato la colonna senza dire a che cosa serve, e la citazione da sola dice una cosa sbagliata.
Ecco il fatto verificato.

`vendite.famiglie_documento` è l'elenco dei tipi di documento che prendono il numero da un
registro. Per ognuno dichiara **dove vive**: schema, tabella, e il nome di tre colonne —
`colonna_numero`, `colonna_serie`, `colonna_billing_account`.

⭐ **`colonna_billing_account` non serve a numerare.** Serve a un'**altra** regola, che legge
lo stesso catalogo: *un cliente non si sposta da un emittente a un altro quando ha già un
documento numerato*. Per rispondere a «questo cliente ha documenti numerati?» bisogna
guardare in cinque tabelle, e il catalogo esiste proprio per non ricopiare quell'elenco
altrove. Lo dice il manuale della tabella:

> *«Se quell'elenco di cinque tabelle fosse ricopiato dentro la regola, il giorno in cui un
> sesto documento entrasse nei registri qualcuno dovrebbe ricordarsi di aggiungerlo. Chi se ne
> dimentica non rompe niente: la regola continua a funzionare, semplicemente smette di
> guardare dove dovrebbe.»*

**Ne discende però un ostacolo concreto, e va detto:** nel DDL
(`00_schema/vendite/20260830-13`) `colonna_billing_account` è dichiarata **`nullable: false`**,
e il guard `trgfn_famiglie_documento_guard_riferimenti` verifica su `pg_attribute` che la
colonna nominata **esista davvero** sulla tabella. Un ordine di acquisto non ha un billing
account. ⇒ **registrare `acquisti.ordini` come famiglia, oggi, fallisce il guard** con
`E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE`.

### La correzione, e perché è piccola e già disegnata

Il pattern giusto **esiste già nella stessa tabella**: `colonna_serie` è nullable, e il vuoto
non è un dato mancante — è **la dichiarazione che quella famiglia una serie non ce l'ha**
(reso e commessa). Il manuale lo scrive per esteso.

⇒ La proposta è la stessa forma per il billing account:

| Cosa | Come |
| --- | --- |
| `famiglie_documento.colonna_billing_account` | da `NOT NULL` a **nullable** — `NULL` = «questa famiglia non ha un billing account» |
| `trgfn_famiglie_documento_guard_riferimenti` | salta il controllo su `pg_attribute` quando la colonna è `NULL` (esattamente come già fa, o dovrà fare, per `colonna_serie`) |
| `fn_ba_ha_storia_emittente` / `fn_get_storia_emittente_ba` | **saltano** le famiglie con colonna `NULL`. ⭐ È corretto per costruzione, non una scorciatoia: un ordine di acquisto non ha un BA, quindi non può contribuire alla storia di nessun BA |

⚠️ **Attenzione a dove si scrive il salto** — le due funzioni compongono SQL dinamico con
`%I`: va messo **nella query che sceglie le famiglie**, non dentro la composizione.

> 🔴 **Correzione del 2026-09-02, verificata sul database** (rilievo di Tid; la stessa
> correzione è nel [brief](brief-db-modifiche-certe-ciclo-vendita-e-articolo.md) §3-bis).
> La prima stesura motivava la regola così: *«un `NULL` passato a `format('%I')` produce
> l'identificatore letterale, non un errore parlante»*. ⛔ **Era falso in tutte e due le
> metà.** Misurato:
>
> | Espressione | Risultato reale |
> | --- | --- |
> | `format('%I', NULL)` | ⛔ **solleva**: `i valori vuoti non possono essere formattati come un identificativo SQL` (`22004`) |
> | `format('%L', NULL)` | la stringa `NULL` |
> | `format('%s', NULL)` | **stringa vuota** |
>
> ⭐ **La regola resta identica e il motivo diventa migliore.** Non è il silenzio il
> problema: è *dove* e *come* si fallisce. Comporre e poi sollevare significa che
> l'operatore riceve un errore **di PostgreSQL** — nessun codice di dominio, nessun
> `context`, nessun campo da accendere — nel bel mezzo di uno **spostamento di billing
> account**, che con le famiglie di documento non c'entra niente e non nomina la propria
> causa. È **esattamente** il difetto per cui esiste
> `trgfn_famiglie_documento_guard_riferimenti`, il cui commento lo descrive con le stesse
> parole (*«fallisce con un `undefined_table` NUDO … senza nominare la propria causa»*).
> ⇒ Si salta **prima** per non arrivarci.
>
> ⚠️ **E il ramo muto esiste, ma vive su `%s`**: lì un `NULL` diventa stringa vuota e il
> comando si compone lo stesso, sbagliato e silenzioso. Se una di quelle due funzioni
> compone un pezzo con `%s`, il pericolo è quello — non `%I`.

### E la domanda che l'obiezione fa emergere (D-10) — **si rimanda, e c'è la ragione**

Il motore vive in `vendite` — `vendite.famiglie_documento`, `vendite.registri_fatturazione` —
e il nome dice *fatturazione*. Con acquisti dentro diventerebbe un motore **cross-dominio in
uno schema di dominio**, e sembra la regola del 2 che bussa.

🔴 **Non bussa, e la prima stesura lo dava per scontato.** La regola del 2 si applica quando
il **secondo consumatore esiste**. Qui non esiste: non c'è un ordine di acquisto, non c'è un
registro che gli assegni un numero, e la forma stessa del catalogo potrebbe cambiare mentre lo
si costruisce. Traslocare adesso vuol dire **migrare un motore per un consumatore ipotetico** —
ed è lo stesso schema già pagato con le pratiche, stavolta con l'aggravante dei **changeSet già
mergiati da rispettare** (che non si toccano: servirebbe un oggetto nuovo più una migrazione
dei dati).

⇒ **La decisione si spacca in due, e le due parti hanno tempi diversi:**

| Cosa | Quando | Perché |
| --- | --- | --- |
| `colonna_billing_account` da `NOT NULL` a **nullable** + il salto nel guard e nelle due `fn_*_storia_emittente` | **subito**, Lotto 1 | è piccola, è **certa**, e ha già il suo precedente identico in `colonna_serie`. Senza, la famiglia dell'acquisto non si registra affatto |
| **trasloco** del motore fuori da `vendite` | **il giorno in cui il primo ordine di acquisto prende davvero un numero da un registro** | a quel punto si **sa** se la forma del catalogo regge a due domini, invece di sperarlo. E il debito, nel frattempo, è dichiarato in una riga |

⭐ È lo stesso criterio con cui questo documento rifiuta le misure come motivo: *un refactoring
per un consumatore che non c'è è una previsione travestita da progetto.*

⛔ Comunque si decida poi, `config.sistema_codici` **non si tocca**: è un'altra tabella e un
altro mestiere.

### I DUE numeri: il nostro e quello del fornitore (D-12)

Rilievo di Tid, 2026-09-01: *«nella tabella acquisti dovremmo avere il numero **ns.** di
ordine acquisto, ma poi dobbiamo poter avere la colonna del numero **del fornitore**»*.

È giusto, e ha una conseguenza più larga di quanto sembri.

**Il fatto verificato**: nessun documento del progetto — né di vendita né di acquisto — ha
oggi una colonna per il riferimento della **controparte**. Non c'è un precedente da copiare:
è un caso nuovo, e va disegnato invece che dedotto.

**E c'è già una trappola in casa**, nello stesso schema:

| Colonna | Chi assegna il numero | Come lo dice |
| --- | --- | --- |
| `acquisti.ordini.numero` | **noi** — lo assegna il registro | implicito |
| `acquisti.ddt.numero` | **il fornitore** — lo subiamo | *«il numero è quello del fornitore, e non è sotto il nostro controllo»* (manuale della tabella) |

⛔ **Due colonne con lo stesso nome e proprietà opposta, nello stesso schema.** Non è
teorico: `famiglie_documento.colonna_numero` significa *«la colonna in cui il registro scrive
il numero»*. Puntarla su `acquisti.ddt.numero` farebbe **sovrascrivere il numero del
fornitore** con uno nostro, e nessun vincolo se ne accorgerebbe.

**La convenzione che propongo**, e vale per tutto il progetto perché è la prima volta che
serve:

> `numero` (+ `serie`, `anno`) è **sempre e solo il numero nostro**, quello che assegna un
> registro. Il numero della controparte ha un nome proprio e non occupa mai quella colonna.

⭐ **E ha già due applicazioni in questo documento**, il che è ciò che la rende una regola e non
una toppa: qui, sul DDT di acquisto (dove si applica *dopo* il difetto, correggendolo), e al
**§8** sulla dichiarazione di accredito, dove il riferimento alla nota di credito del fornitore
si chiama `numero_nota_credito_fornitore` — cioè dove si applica **prima** che il difetto
esista. ⚠️ La seconda vale più della prima: una convenzione si giudica da come si comporta sul
caso che deve ancora nascere.

Ne discendono tre interventi, tutti nel Lotto 1:

| Dove | Cosa | Perché |
| --- | --- | --- |
| `acquisti.ordini` | **aggiungere** `numero_fornitore` (+ eventuale `data_conferma_fornitore`) | è la conferma d'ordine del fornitore, e arriva **dopo** che l'ordine è partito |
| `acquisti.ddt` | **rinominare** `numero` → `numero_fornitore`, e ⛔ **NON** lasciare un `numero` vuoto al suo posto | vedi il riquadro qui sotto |
| `famiglie_documento` | il DDT di acquisto **non si registra** come famiglia finché non ha un numero nostro | una famiglia dichiarata senza registro non produce documenti |

#### 🔴 Correzione: il `numero` liberato NON si tiene

La prima stesura proponeva di *«lasciare `numero` libero per un eventuale protocollo nostro di
ricezione»*. **È sbagliato, ed è il difetto che questo stesso documento contesta due volte** —
⑩ (i totali `*_atteso` che nessuno calcola) e §7 (la struttura che sembra funzione). Un
protocollo di ricezione **oggi non esiste**: una colonna vuota tenuta «per quando servirà» è
esattamente ciò che costringe a spiegarla a ogni lettura, e nel frattempo non presidia niente.

⇒ La mossa pulita è **toglierla** e rimetterla il giorno in cui le ricezioni si numerano
davvero. Costa una riga di DDL *allora*; costa spiegazioni *ogni volta* fino ad allora.

⭐ **E questo scioglie ⑦ meglio di come lo scioglieva la prima versione.** Sparito `numero`,
sparisce anche `uq_a_ddt_anno_serie_numero` — il vincolo che contraddiceva il proprio manuale.
Al suo posto l'unicità torna dove il manuale la voleva: **per fornitore**, cioè
`(mittente_soggetto_ruolo_id, numero_fornitore, …)`.

#### D-13 — `serie` e `anno`: **sono del fornitore** (chiusa)

✅ **Decisione di Tid, 2026-09-01.** Erano gli accessori di un `numero` che è del fornitore:
**sono suoi**, e si rinominano con lui — `serie_fornitore`, `anno_fornitore`.

⭐ **E non è una rinomina di simmetria: quelle due colonne servono davvero**, e servono
proprio all'unicità per fornitore che il §6 vuole. Una bolla italiana è identificata da
**numero + anno del suo emittente**: senza l'anno, due bolle dello stesso fornitore con lo
stesso numero in anni diversi collidono. ⇒ il vincolo diventa
`(mittente_soggetto_ruolo_id, anno_fornitore, serie_fornitore, numero_fornitore)`.

⛔ **E la data di ricezione non entra qui.** È un'altra cosa e ha il suo posto naturale in una
colonna **data**, non in un intero. Tenere `anno` con dentro l'anno di ricezione sarebbe **la
stessa collisione di `numero`, un giro dopo**: una colonna il cui nome non dice di chi è il
dato.

⚠️ **Ne esce un terzo membro della stessa famiglia, e va chiuso nello stesso giro**:
`acquisti.ddt.data`. Oggi è `NOT NULL DEFAULT CURRENT_DATE` — e **il default è il campanello**:
un default «oggi» descrive il momento in cui *noi* registriamo, ma su un documento che
subiamo la `data` che conta è quella **del suo documento**. Sono di nuovo due domande su una
colonna sola. ⇒ Applicando lo stesso criterio: `data_documento_fornitore` (sua, e senza quel
default) e il momento della ricezione dove già c'è — `data_ora_consegna_eff`, che è nostro. ⛔
Da confermare, ma la direzione è la stessa e conviene deciderla adesso: sono tre colonne dello
stesso documento, e farne due su tre lascia la terza a mentire.

⚠️ **Due dettagli che decidono se funziona:**

* `numero_fornitore` **deve restare fuori da `trgfn_lock_columns`**. Oggi
  `trg_ordini_a10_lock_columns_upd` congela `numero`, ed è giusto — quello nostro non si
  tocca più. Ma il riferimento del fornitore **arriva dopo**, e va scritto su un ordine già
  emesso: metterlo sotto lo stesso lock lo renderebbe impossibile da valorizzare;
* l'unicità, **se c'è**, è **per fornitore** — stessa lezione di ⑦. Ed è più debole ancora:
  due nostri ordini diversi possono legittimamente ricevere la stessa conferma dal fornitore
  (un ordine cumulativo). ⇒ nessun UNIQUE finché non è un caso reale: è un dato di
  riferimento, non una chiave.

⭐ E la simmetria che ne esce **vale anche per la vendita**: il «vostro riferimento» del
cliente sull'ordine di vendita è lo stesso concetto, non ce l'ha nessuno, e il giorno che
servirà avrà già la sua convenzione. Non lo faccio qui — è fuori perimetro — ma la regola
nasce generale apposta.

---

## 7. Approfondimento: una tabella sola per gli stati — come si fa perché regga

La preferenza è una tabella unica «con le regole che suddividono il dominio». **È la scelta
che consiglio anch'io**, ma con una precisazione che decide se regge o no.

### Perché la tabella unica nuda non basta

Oggi `config.stati_doc_ordini` è già una tabella unica, e il problema è esattamente che è
**nuda**: non c'è nessuna colonna che dica a quale ciclo appartiene uno stato. Ne discende
che niente impedisce a un ordine di acquisto di essere `SPEDITO`. Una regola che non ha dove
essere scritta non è una regola: è una convenzione, e le convenzioni le rompe il primo che
non le ha lette.

### La forma che consiglio

Non una colonna `ambito` sullo stato — perché alcuni stati sono legittimamente **di
entrambi** (`DRAFT`, `CONFERMATO`, `ANNULLATO`) e una colonna singola costringerebbe a
duplicarli. Serve un **satellite**, cioè la tabella di ammissione:

```
config.stati_doc_ordini                     ← il vocabolario (resta com'è)
config.stati_doc_ordini_ambiti              ← NUOVA: quali stati ammette ciascun ciclo
   (stato_doc_ordine_id, ambito, nessuna_azione_key, ordine)
   PRIMARY KEY (stato_doc_ordine_id, ambito)
```

Tre cose che questa forma risolve **insieme**, e che sono il motivo per cui la consiglio:

| Domanda | Dove trova risposta |
| --- | --- |
| «questo stato è ammesso per un ordine di acquisto?» | esiste la riga `(stato, ACQUISTI)` — e un guard `BEFORE` su ciascuna delle due tabelle lo verifica |
| «che cosa dice questo stato **in questo ciclo**?» | `nessuna_azione_key` sta sul **paio**, non sullo stato: `EVASO` dice cose diverse in vendita e in acquisto, e un solo indirizzo i18n non può servirle entrambe |
| «in che ordine si susseguono?» | `ordine` sul paio: `FATTURATO` è terminale in vendita, in acquisto la fattura del fornitore arriva **prima** che l'ordine si chiuda |

⚠️ **E lo stesso vale per le transizioni.** `config.transizioni_stati_ordini` ha bisogno della
stessa chiave: una transizione lecita in vendita può essere illecita in acquisto. Senza
`ambito` nella chiave, il guard di transizione degli acquisti leggerebbe le regole della
vendita.

⭐ **Il beneficio che si compra**, ed è quello che rende la tabella unica migliore dello
split: la **proiezione di stato di dominio** (`fase`, `esito`, `terminale`) resta **una sola**
per tutti i cicli. Situazione aperta, backlog e lineage continuano a leggere un solo
vocabolario. Con due tabelle separate quella proiezione andrebbe scritta due volte — ed è
esattamente la classe di duplicazione che il progetto paga più cara.

### Il vocabolario dell'ambito: ce ne sono QUATTRO, e non sono lo stesso asse

🔴 **Correzione del 2026-09-01 (rilievo di Tid).** La prima stesura diceva che il ruolo di
`config.ambiti` «è stato assunto da `magazzino.ambito_causale`». **Non è dimostrato, e
l'ho ripetuto da una pagina auto-generata che lo inferisce dalla somiglianza del nome** —
esattamente l'errore contro cui quella stessa pagina mette in guardia due paragrafi sopra
(«la somiglianza è precisamente ciò che rende facile sbagliarsi… è successo scrivendo la prima
versione di questa pagina»). Ci è successo una seconda volta.

**Cosa dice invece la struttura di `config.ambiti`**: ha una colonna `extra_country` jsonb con
un indice su `(extra_country->>'stato_utilizzo', ->>'settore', ->>'codice_ambito')`. Le uniche
altre tabelle del progetto con `extra_country` sono `stati`, `regioni`, `province`, `comuni`:
è la famiglia dei **riferimenti anagrafici localizzati**. ⇒ `config.ambiti` è nata per portare
codici di ambito **per paese e per settore**, e col magazzino non ha niente a che vedere.

I quattro assi che oggi si chiamano tutti «ambito», e che non vanno confusi:

| Asse | Dove vive | Valori | Chi lo legge |
| --- | --- | --- | --- |
| **famiglia di documento** (per gli indirizzi) | `config.tipi_indirizzi_allowed.ambito` (CHECK) | `PREVENTIVI`, `OFFERTE`, `CONTRATTI`, `ORDINI`, `DDT`, `FATTURE`, **`ACQUISTI_DDT`** | `trgfn_tipi_indirizzi_only_allowed` |
| **ambito della causale di magazzino** | `magazzino.ambito_causale` | `VENDITE`, `ACQUISTI`, `ODL`, `TRASF`, `INVENTARIO`, `GENERICO` | `magazzino.causali` |
| **applicabilità di un titolo IVA** | `anagrafiche.soggetti_titoli_iva_ambiti` | articolo / gruppo voce / tipo voce | `fn_resolve_iva_riga` stadio B |
| **riferimento localizzato** | `config.ambiti` — **vuota, zero FK entranti** | — | nessuno |

Il discriminante che serve a noi — **il ciclo**: vendita o acquisto — è un **quinto** asse.
Coincide per *valori* con `magazzino.ambito_causale` ma non per *significato*, e quella tabella
vive in `magazzino`: una FK da `config` verso `magazzino` andrebbe **contro il verso degli
anelli**.

⇒ **Raccomandazione**: non riusare nessuna delle quattro. Sul satellite del §7 il ciclo è un
**CHECK a due valori** (`VENDITE`, `ACQUISTI`) — due valori non fanno una tabella, e il giorno
in cui ne servisse un terzo si valuta allora. ⛔ E `config.ambiti` **non si tocca in questo
cantiere**: che farne (popolarla per il suo scopo, o ritirarla) è una domanda sua, e
riempirla di stati la trasformerebbe in una quinta cosa ancora.

### ⛔ Qui non si rompono dei DATI: si rompe una FUNZIONE che gira

> 🔴 **Riscritta il 2026-09-02.** La prima stesura chiamava questa parte «migrazione su un
> dominio vivo, con dati veri» e ne faceva una questione di **cautela sui dati**. ⛔ È il
> registro sbagliato: i dati sono di prova e si rifanno quando si vuole (Tid, 2026-09-02).
> ⭐ **Ma il punto non era mai stato quello**, e riscriverlo lo rende più forte: il satellite
> non mette a rischio delle righe — mette a rischio **un pezzo di vendita che oggi
> funziona**.

L'argomento «prima che qualsiasi riga esista» vale per `acquisti`, che è a zero. **Non vale
qui**, e per una ragione che non ha niente a che fare con la popolazione:

> Il guard `BEFORE` legge il satellite. Se il satellite non ha la riga `(stato, VENDITE)`,
> **l'ordine di vendita non cambia più stato.** Non un ordine vecchio: *qualunque* ordine,
> anche uno creato dopo, anche su un database appena rifatto.

Lo stesso per le transizioni con `ambito` nella chiave: senza le righe `VENDITE`, il guard di
transizione della vendita non trova più le proprie regole.

⭐ **È la distinzione che vale la pena tenere a mente oltre questo caso**: «non siamo in
produzione» toglie il **rischio sui dati** — nessuna bonifica, nessun rollback, breaking
secchi ammessi. **Non toglie il rischio funzionale**: una regola incompleta rompe il
comportamento anche a tabella vuota, e si ripresenta identica sul database ricostruito in CI.

⇒ Due cose obbligatorie, e nessuna delle due è una precauzione sui dati:

| | Cosa | Perché |
| --- | --- | --- |
| 1 | il seed copre **ogni** riga di `stati_doc_ordini` e `stati_doc_ddt` col gemello `VENDITE`, e ogni transizione con `ambito = VENDITE` | ⚠️ non è un backfill di dati: `config` è **catalogo che spedisce**, e un catalogo incompleto è una funzione incompleta |
| 2 | ⭐ un pgTAP sull'invariante: **nessuno stato senza almeno un ambito** | il seed incompleto **non fallisce: non fa niente**. È la sola forma che lo rende rumoroso — e vale in CI, dove il database nasce vuoto |

⭐ E l'invariante del punto 2 è un altro membro della famiglia del **§9-bis**: uno stato che
non appartiene a nessun ciclo è «esiste e non è armato» applicato a una riga di catalogo.

### La coda fuori dal DB — c'è, ed è più corta del temuto

Spostare `nessuna_azione_key` dallo stato al **paio** cambia chi la legge. Verificato il
2026-09-01, i lettori sono tre e **non si comportano allo stesso modo**:

| Lettore | Cambia? | Perché |
| --- | --- | --- |
| le funzioni `script.fn_available_actions_ordine` e `_ddt` | ✅ **sì, nello stesso migrate** | leggono il `meta` dello stato; devono leggere il satellite. Sono **due**, non otto: le altre sei insistono su tabelle di stato che questo lavoro non tocca |
| il **backend e il frontend** di vendite | ⭐ **no** — e non è fortuna | il contratto non è la colonna: è il campo **`stato_info_key`** che la funzione **emette**. Finché l'output non cambia forma, `DrawerActionsBar` e la prop `infoKey` non sanno da dove viene |
| il guard CI `scripts/check_i18n_keys.py` | ⚠️ **dipende dal NOME della proprietà** | scandisce **ogni** CSV di `80_data/sql` (quindi il satellite nuovo è coperto da sé) ma matcha sul contenuto: `label_key\|reason_key\|nessuna_azione_key` |

⛔ **Da cui la regola operativa più stretta di questa sezione**: nel satellite la proprietà
**deve continuare a chiamarsi `nessuna_azione_key`**. Ribattezzarla — anche per allinearla al
più sensato `stato_info_key` che la funzione emette — renderebbe il guard **verde per
cecità**, che è già il modo in cui questo presidio ha fallito due volte. L'asimmetria fra il
nome della proprietà e il nome del campo emesso è **voluta e documentata**: non si "sistema"
di straforo.

⇒ Ne discende che il pezzo di BE/FE di vendite dentro questo lotto è **zero righe**, a
condizione che le due funzioni preservino il proprio contratto d'uscita. ⚠️ Ed è una
condizione da **provare**, non da assumere: se una delle due cambia la forma del blob, il
lotto «solo DB» rompe il dominio che funziona.

### E lo stesso trattamento serve a `config.stati_doc_ddt`

⚠️ È la seconda occorrenza della stessa cosa, e conviene farle **insieme**: gli stati del DDT
di vendita (`EMESSO`, `SPEDITO`, `CONSEGNATO`) descrivono un documento che **emettiamo noi**;
quelli di un DDT ricevuto sono altri (§8). Farne una adesso e l'altra dopo significa scrivere
due volte lo stesso satellite e scoprire al secondo giro che le due forme non coincidono.

---

## 7-bis. Approfondimento: gli indirizzi, e **di chi** sono (D-6)

La domanda posta è: *«la società X chiede un acquisto alla società Y; l'indirizzo di
spedizione è di chi compila, che i suoi indirizzi ce li ha già caricati — si può usare lo
stesso BB, che è già legato al ruolo?»*. Verificato, e la risposta è **sì, con due limiti
precisi**.

### La verifica: l'ancora è un parametro, non «il cliente»

`script.fn_resolve_indirizzo_documento(p_soggetto_ruolo_id, p_istanza_utility_id,
p_tipo_codice)` risponde a *«da dove prende l'indirizzo di tipo X questo documento»* con due
layer — **RUOLO → SOGGETTO**, con precedenza all'istanza. ⭐ **Non sa, e non può sapere, se
quel `soggetto_ruolo` sia un cliente, un fornitore o noi stessi**: lo riceve come parametro.

Lo stesso vale lato Python: `IndirizziDocumentoRepositoryMixin` dichiara
`_indirizzi_doc_sr_column`, cioè **il nome della colonna della testata che porta l'ancora**.
In vendite vale `soggetto_ruolo_id` per gli ordini e `destinatario_soggetto_ruolo_id` per i
DDT — due colonne diverse, stesso BB.

⇒ **Il BB regge per costruzione.** Ciò che cambia fra vendita e acquisto non è il building
block: è **quale colonna si dichiara come ancora**.

### Perché «ti stavi incartando»: la ragione è nel modello, non nel ragionamento

In **vendita** tutti gli indirizzi del documento appartengono alla **controparte**: dove
consegno, dove fatturo, dove fornisco — sono tutti del cliente. Un'ancora sola basta, e il BB
è nato con una sola.

In **acquisto** no, e sono due soggetti diversi:

| Indirizzo | Di chi è | Ancora |
| --- | --- | --- |
| sede del fornitore (dove mandiamo l'ordine) | del **fornitore** | `acquisti.ordini.soggetto_ruolo_id` |
| luogo di consegna (dove vogliamo la merce) | **nostro** | il soggetto_ruolo del **nostro emittente fiscale** |

⭐ **È la prima volta che il progetto incontra un documento a DUE ancore.** Non è una lacuna
del tuo ragionamento: è un caso che il BB non ha ancora, e che va nominato prima di
scriverlo.

⭐⭐ **E D-1 lo ha appena reso facile.** Avendo chiuso che l'ordine di acquisto porta
`emittente_fiscale_id`, «i nostri indirizzi» sono raggiungibili **con la stessa identica
cascata**: l'emittente fiscale *è* un `soggetto_ruolo` (tipo `EF`), quindi cambia solo quale
SR si passa alla funzione. Non serve nessun meccanismo nuovo.
⚠️ Attenzione al dettaglio in cui si sbaglia: `fn_get_emittente_fiscale_id` restituisce il
**`soggetto_ruolo_id`**, non la PK di `emittenti_fiscali`. Qui è esattamente ciò che serve —
ma è lo stesso nome che altrove ha tratto in inganno.

### I due limiti veri del BB, entrambi piccoli e nominabili

**Limite 1 — il join al billing account è cablato.**
`get_ancora_indirizzi_documento` compone sempre
`LEFT JOIN anagrafiche.billing_account ba ON ba.id = d.billing_account_id`. `acquisti.ordini`
**non ha** quella colonna ⇒ la query fallirebbe con `undefined_column`. Il rimedio è lo stesso
idioma già usato per `_indirizzi_doc_sr_column`: renderlo **dichiarativo e opzionale**
(`_indirizzi_doc_ba_column: str | None`), e comporre il join solo quando è dichiarato.

**Limite 2 — l'ancora è una sola.**
`_indirizzi_doc_sr_column` è **un** attributo di classe. Due strade:

| | Come | Costo / rischio |
| --- | --- | --- |
| **A** (consigliata) | l'ancora diventa una **mappa `tipo_indirizzo → colonna`**, con un default. Vendite dichiara un solo tipo e non cambia di una riga | tocca il BB, quindi va provato sui 5 domini che lo usano già |
| **B** | ancora unica = fornitore; l'indirizzo di consegna **non** passa dalla cascata ma è una scelta esplicita fra i nostri indirizzi | ⛔ è una **seconda sede** della stessa regola: due modi di risolvere un indirizzo di documento, e il giorno che la cascata cambia uno dei due resta indietro |

⇒ Consiglio **A**, ed è la stessa ragione per cui il BB esiste: la regola «da dove viene
l'indirizzo di tipo X» deve stare in **una** sede. B costa meno oggi e paga dopo.

### Il seed che serve

Sul modello di `ACQUISTI_DDT` (già a catalogo con `CON` + `FORNITURA`), serve l'ambito
**`ACQUISTI_ORDINI`** in `config.tipi_indirizzi_allowed`, con i tipi da decidere — presumibilmente
`CON` (consegna, ancora *nostra*) e `SEDELEG`/`SEDEOP` per il fornitore. ⚠️ Il valore va
aggiunto **anche al CHECK** `chk_tipi_indirizzi_ambito` (`20260711-16` è il precedente): un
seed con un ambito fuori CHECK viene rifiutato — è già successo, e sta scritto nel brief degli
indirizzi.

---

## 8. La ricezione: dal DDT fornitore al carico, al reso, all'attesa

È il pezzo che hai chiesto, ed è quello dove lo specchio è **più fedele** di quanto sembri.

### Cosa fa la vendita, in una riga

Il conto della merce non sta sull'ordine: sta sulla **partita**, e *una partita è una riga di
documento di trasporto* — sempre, che dietro ci sia un ordine oppure no
(`vw_partite_merce`, dal 2026-08-17). Su ogni partita si contano `consegnato`, `reso`,
`in_riconsegna`, `tenuti`, `fatturato`, e la `differenza` — che la vista **traduce** in uno
`stato` leggibile, una volta sola, per tutti quelli che la leggono.

Sopra ci stanno il documento **reso** (`vendite.resi`, ibrido: righe *a credito* oppure *per
ri-consegna*), le due **code di lavoro** (`vw_resi_da_accreditare`, `vw_resi_da_riconsegnare`)
e la **rinuncia** (`resi_righe_rinunce`) — che non muove nessun numero: dichiara che una quota
pendente non tornerà più, e tutto il resto è conseguenza.

### Lo specchio, verso invertito

La corrispondenza è quasi puntuale. La colonna «⚠️» segnala dove **non** lo è.

| Vendita | Acquisto | ⚠️ |
| --- | --- | --- |
| partita = riga di DDT **uscita** | partita = riga di DDT **ricevuto** | — |
| `consegnato` | `ricevuto` | — |
| `reso` (il cliente ci restituisce) | `reso_al_fornitore` (noi restituiamo) | il verso del **movimento di magazzino** si inverte |
| `in_riconsegna` (merce che **ri-spediamo** al cliente) | `in_attesa_di_ri-consegna` (merce che il **fornitore deve rimandarci**) | il ponte punta a un DDT **di acquisto** in entrata, non a uno in uscita |
| `tenuti` = quanto ha in mano il cliente | `tenuti` = **quanto abbiamo davvero in casa** | ⭐ è questo il numero che deve quadrare col magazzino |
| `fatturato` | *fatturato dal fornitore* | ⛔ **non esiste una sorgente**: vedi sotto |
| `resi_righe_rinunce` = «non tornerà più al cliente» | «il fornitore non me la manderà più» → il residuo dell'ordine si chiude senza merce | — |
| `tipi_reso.riapre_residuo` riapre il residuo della riga d'ordine | **identico**: riapre il residuo su `acquisti.ordini_righe_fulfillment` | ⭐ è già il meccanismo che chiedi, e c'è già il ponte |

### Le tre destinazioni di una riga ricevuta — e la quarta

Sono quelle che hai descritto, con il nome del gemello di vendita accanto:

1. **CARICO** — la merce entra in magazzino. Causale `CARICO_ACQ` (segno `+1`) **esiste già** a
   seed in `magazzino.causali`.
2. **RESO AL FORNITORE, a credito** — torna indietro e ci aspettiamo una nota di credito.
   ⛔ La causale di scarico per reso a fornitore **non esiste** nel seed: c'è `SCARICO_VEN` (DDT
   vendita) ma nessuna `SCARICO_RESO_FORN`.
3. **RESO AL FORNITORE, per ri-consegna** — torna indietro e deve tornare. ⭐ Il residuo
   dell'ordine si riapre: è `riapre_residuo` applicato a `ordini_righe_fulfillment`.
4. **RINUNCIA** — la quarta, che c'è in vendita e serve anche qui: si dichiara che quella quota
   non arriverà più. Senza, una ri-consegna mai eseguita lascia l'ordine parzialmente evaso
   **per sempre** — è letteralmente il difetto che in vendita ha fatto nascere
   `resi_righe_rinunce`.

### ⛔ Le tre cose da sapere prima di disegnarlo

**a) L'asse fiscale non c'è, e non è un dettaglio.** In vendita la partita conta anche il
`fatturato`, perché la fattura è **nostra** e sta in `vendite.fatture`. In acquisto la fattura
è **del fornitore**: non esiste una tabella `acquisti.fatture`, e lo schema `contabilita` è
vuoto e fuori perimetro (verificato 2026-09-01, `PROJECT_CONTEXT.md`).
⇒ La partita di acquisto nasce **su due assi soltanto** — *ricevuto / reso / in casa* — e
l'asse «fatturato dal fornitore» arriva col ciclo passivo. Va dichiarato nel modello, non
lasciato come colonna sempre vuota: una colonna che nessuno riempie, a video, si legge come un
difetto (è la stessa lezione di ⑩).

**b) Il carico dipende da decisioni che stanno in un altro brief.** `magazzino.movimenti` ha
oggi **due** modi di dire da dove viene un movimento, e il DDT di acquisto **non è una
sorgente registrata**. Sono D-1 e D-7 di
[analisi-db-magazzino-aggancio-documento-e-produzione.md](analisi-db-magazzino-aggancio-documento-e-produzione.md),
e sono **aperte**. ⇒ La ricezione si può progettare, ma il momento in cui il carico tocca il
ledger va concordato con quel cantiere, non deciso qui.

**c) Gli stati del DDT ricevuto sono altri.** `EMESSO`/`SPEDITO` non hanno senso per un
documento che riceviamo: servono qualcosa come *RICEVUTO → VERIFICATO → CARICATO*, più
*RESPINTO*. È l'altra metà del §7, e il motivo per cui i due satelliti conviene farli insieme.

### ⛔ Il buco: il ramo CREDITO non ha una porta d'uscita

⭐ **Aggiunto il 2026-09-01, ed è il punto più importante di questa sezione.** La prima stesura
notava che l'asse fiscale non c'è (§8-a) ma **non ne traeva la conseguenza sulla coda** — e la
conseguenza è quella che decide se il meccanismo è usabile.

**In vendita la coda «da accreditare» si chiude perché la nota di credito la emettiamo noi**:
il ciclo è interno, e `fn_accredita_riga_reso` è la porta. In acquisto il reso a credito si
chiude con una **nota di credito del fornitore**, che nel sistema **non entra da nessuna
parte** finché non esiste il ciclo passivo.

⇒ Senza una porta, quella coda **non si svuota mai**. E una coda che non si svuota si riempie
di roba vecchia, finché la gente smette di guardarla — che è **letteralmente la piaga che in
vendita ha fatto nascere le rinunce**: *«una ri-consegna mai eseguita lasciava l'ordine
`PARZIALMENTE_EVASO` per sempre, la riga in coda indistinguibile da una lavorabile»*.

**La simmetria è incompleta, e va vista bene:**

| Ramo | In vendita si chiude con | In acquisto si chiude con |
| --- | --- | --- |
| ri-consegna | il DDT di ri-spedizione, **oppure** la rinuncia (`resi_righe_rinunce`) | il DDT di ri-ricezione, **oppure** la rinuncia — ✅ coperto, §8 sopra |
| credito | `fn_accredita_riga_reso` → rettifica → nota di credito **nostra** | ⛔ **niente** |

**Serve una dichiarazione esplicita di accredito**, sul modello di `resi_righe_rinunce`:
*«questo reso è stato accreditato, fuori sistema, il giorno X, con la nota di credito numero
Y»*. Forma e proprietà, entrambe prese dal precedente:

* ⭐ **è una dichiarazione, non un calcolo** — «scrivere qui non muove nessun numero»: registra
  data, riferimento della nota di credito del fornitore, importo dichiarato e chi lo dichiara.
  Tutto il resto (la riga esce dalla coda) è **conseguenza** del cambio di natura;
* ⛔ **e il campo del riferimento NON si chiama `numero`** — è la **seconda applicazione** della
  convenzione D-12 (§6), e la prima in cui si applica *prima* di sbagliare invece che dopo.
  Quella nota di credito è del **fornitore**: il nome è `numero_nota_credito_fornitore`, o
  qualunque altro che dica di chi è. ⭐ La convenzione nasce così con **due casi** invece che
  con uno — e un caso solo si legge come una toppa a `acquisti.ddt`, due si leggono come una
  regola;
* ⚠️ **non è una rinuncia**, e i due non vanno fusi: la rinuncia dice *«non tornerà più»*,
  l'accredito dichiarato dice *«è stato compensato»*. Fondere i due farebbe sparire dalla coda
  righe per cui non è arrivato niente;
* ⭐ **è il ponte verso il ciclo passivo, non un ripiego**: il giorno in cui la fattura
  fornitore entra nel sistema, questa tabella diventa il posto dove **agganciarla** — la
  dichiarazione a mano è il caso degradato di un legame che allora sarà automatico. Non è un
  dato da buttare.

⛔ **È un'aggiunta piccola oggi e insanabile dopo.** Costruire la coda senza la sua uscita
significa consegnare un meccanismo che al terzo mese nessuno guarda più — e a quel punto
aggiungere la porta non basta, perché la coda va anche **bonificata a mano** di tutto
l'arretrato che nel frattempo si è depositato.

---

## 9. Il prezzo: a mano, e il «prezzo fornitore» sull'articolo

Prezzo digitato a mano per ora — ✅ D-8. L'idea del prezzo fornitore sull'articolo è buona
come aiuto alla digitazione, ma va disegnata sapendo dove finisce, altrimenti diventa la prima
metà di un modello che poi non si può completare.

**Il punto da guardare:** [listini-fornitori.md](listini-fornitori.md) esiste già e prevede la
mappatura articolo ↔ fornitore (codice del fornitore, sua descrizione, sua unità di misura) e
i listini «sorgente». Un `prezzo_fornitore` messo su `catalogo.articoli` come colonna singola
è **una risposta a una domanda diversa**: dice «quanto costa», ma non «a quale fornitore» né
«da quando». Al secondo fornitore la colonna non basta più, e al primo cambio di prezzo non
sa dire da quando vale.

⇒ Due strade, e la scelta è tua:

| | Forma | Cosa compra | Cosa costa |
| --- | --- | --- | --- |
| **A** | colonna `prezzo_acquisto_riferimento` su `catalogo.articoli` | il default di riga, subito, una riga di DDL | ⛔ è una **seconda sede** rispetto a `listini-fornitori`: il giorno che quel cantiere apre, va migrata e ritirata |
| **B** | anticipare la sola **anagrafica** `catalogo.articoli_fornitori` (articolo, fornitore, codice suo, uom sua, prezzo di riferimento, validità) | il default di riga **e** il primo mattone di `listini-fornitori`, senza doppioni | una tabella invece di una colonna |

⭐ **Consiglio B**, e la ragione non è «è più completo»: è che A crea un dato che dovrà essere
**cancellato**, e i dati che vanno cancellati sopravvivono. Ma è una decisione tua, e A è
legittima se dichiarata come ponte con la sua data di scadenza.

⚠️ In entrambi i casi il prezzo è un **suggerimento all'apertura della riga**, non un
resolver: sull'acquisto non esiste (e non serve oggi) il gemello di `PricingService`.

---

## 9-bis. La classe di difetto che continua a uscire: «esiste e non è armata»

⭐ **Rilievo trasversale, 2026-09-01.** Fra questa analisi e
[analisi-db-commessa-e-produzione-predisposizione.md](analisi-db-commessa-e-produzione-predisposizione.md) —
scritte lo stesso giorno — lo **stesso difetto è uscito quattro volte**, in forme diverse:

| Istanza | Dove | Cosa sembra | Cosa fa |
| --- | --- | --- | --- |
| il **guard tipizzato** montato su zero tabelle | magazzino | un presidio | niente |
| le **due policy RLS** senza `ENABLE` | `acquisti.ordini`, `acquisti.ddt` (§4.1) | sicurezza a livello di riga | niente |
| `magazzino.causali.ambito_causale_id` **vuota in tutte e dieci** le righe seminate | magazzino | una classificazione | niente |
| `config.ambiti`: **zero righe, zero FK entranti** (§7) | config | un vocabolario | niente |

⛔ **Nessuna delle quattro produce un rosso**, e nessuna delle quattro è un difetto di
scrittura: sono tutte cose costruite bene e **non collegate**. È la specie peggiore, perché
l'oggetto c'è — chi lo cerca lo trova, chi legge il codice lo conta come presidiato.

### La proposta: presidiare la CLASSE, non le quattro istanze

Il progetto ha già **otto** viste di questa identica forma in `dbops` —
`vw_bersagli_non_dichiarati`, `vw_eventi_non_dichiarati`, `vw_codici_errore_da_dichiarare`,
`vw_riferimenti_morti_da_sanare`, `vw_parameter_fk_surrogate_dangling`,
`vw_operatori_senza_emittente`, `vw_liste_multi_emittente_non_certificate`,
`vw_fk_senza_indice` — e una guida che spiega come aggiungerne una
([presidi-e-registri-del-debito §6](/guide/presidi-e-registri-del-debito)). Non c'è niente da
inventare: c'è da **applicare lo stampo a una classe che nessuno ha ancora nominato**.

Tre viste in `dbops`, **che devono restare vuote**:

| Vista | Cosa elenca | Query, in una riga |
| --- | --- | --- |
| *funzioni trigger montate da nessuno* | le `trgfn_*` di `script`/dominio che **nessun trigger** invoca | `pg_proc` meno i `tgfoid` di `pg_trigger` |
| *policy su tabelle senza RLS attiva* | le `pg_policy` la cui tabella ha `relrowsecurity = false` | `pg_policy` ⋈ `pg_class` |
| *cataloghi orfani* | le tabelle di riferimento con **zero righe e zero FK entranti** | `pg_class` ⋈ `pg_constraint` + `n_live_tup` |

⚠️ **Due avvertenze**, o il presidio nasce già da spegnere:

* le tre viste avranno **falsi positivi legittimi**: una funzione trigger tenuta per un
  cantiere aperto, una policy in dry-run **dichiarata** come le due di §4.1. ⇒ ognuna vuole il
  suo **registro delle eccezioni motivate**, esattamente come `baseline-rossi.tsv` — non un
  filtro cablato nella vista. *Un cancello che boccia a caso viene spento, e un presidio
  spento è peggio di uno assente.*
* la terza è la più delicata: «zero righe» è una **misura**, e da sola non decide niente
  (regola zero). La condizione che vale è **strutturale** — *zero FK entranti* — e le righe
  sono solo il secondo indizio. Una tabella piena e non referenziata è ugualmente orfana.

⭐ **Costa tre query e chiude la classe invece dell'istanza**, e chiude anche le prossime:
`config.ambiti` (D-11) e la causale del reso a fornitore (§8) sarebbero **uscite da sole** da
un presidio così, invece che da due analisi lette a mano. È probabilmente l'ora meglio spesa
del Lotto 1 — e ⚠️ **non è di questo cantiere**: è un cantiere di `dbops`, che questo documento
si limita a proporre.

---

## 10. L'ordine in cui conviene costruire

Non è un piano — le decisioni aperte lo cambiano. È la sequenza che evita di scrivere due
volte.

| Lotto | Cosa | Perché prima di quello dopo |
| --- | --- | --- |
| **0** | Chiudere **D-2** (policy fornitore) e **D-6b** (ancora doppia degli indirizzi) + confermare la forma del satellite §7 | sono le due rimaste. D-6b decide se si tocca un BB usato da 5 domini |
| **1a — DB, terreno vuoto** (solo `acquisti`) | `emittente_fiscale_id` + guard; `acquisti.ordini_indirizzi` + ambito `ACQUISTI_ORDINI` (§7-bis); **le colonne del fornitore** — `numero_fornitore` su ordini; su DDT `numero`→`numero_fornitore`, `serie`/`anno`→`_fornitore`, `data`→`data_documento_fornitore`, **DROP** del `numero` liberato, UNIQUE per fornitore (§6, che assorbe ⑦ e D-13); **rimozione** di `ddt.ordine_id` ⑧; `uid NOT NULL` ⑫ | ⭐ **qui l'argomento «prima che qualsiasi riga esista» vale davvero**: `acquisti` è a zero, e ognuna di queste dopo sarebbe una migrazione con dati da sanare |
| **1b — DB, tocca una FUNZIONE che gira** (`config` + `vendite`) | satellite ambiti su `stati_doc_ordini` **e** `stati_doc_ddt` + **backfill `VENDITE` completo**; `ambito` nella chiave delle transizioni + backfill; aggiornamento di `fn_available_actions_ordine` e `_ddt`; `colonna_billing_account` nullable (§6, **senza** il trasloco) | ⛔ **Non va nello stesso paniere di 1a**, e non per i dati (quelli sono di prova): il guard legge il satellite, e un catalogo incompleto **impedisce a qualunque ordine di vendita di cambiare stato** — anche su un database appena rifatto. Invariante da provare: **§7 «Qui non si rompono dei DATI»** |
| **2 — DB, motore** | RLS armata; `fn_available_actions_ordine_acquisto`; numerazione (§6); `fn_ricalcola_totali_ordine_acquisto`; sorgenti a catalogo ⑨ | sono i **quattro ganci** a cui i building block si attaccano. Senza, il BE si scrive contro il nulla |
| **3 — DB, ricezione** | partita di acquisto, reso al fornitore, ri-consegna, rinuncia **e la dichiarazione di accredito** (§8, D-14) — coordinato con l'analisi magazzino | poggia sul motore del lotto 2. ⛔ La porta d'uscita del ramo credito entra **qui**, non dopo: una coda senza uscita al terzo mese non la guarda più nessuno |
| **4 — BE** | app `acquisti`: repository + service + rotte, in fotocopia da `vendite` | ⭐ qui la simmetria paga davvero |
| **5 — FE** | dominio `acquisti`: lista configurabile (è **dato**, non DDL — si semina in-app), drawer, righe, ricezione | idem |
| **6** | azioni di processo su area 3, i18n `acquisti.*`, menu L2 | sono le tre cose che oggi sono vuote e che nessun lotto precedente riempie da sé |

---

## 11. Cosa NON è di questa analisi

* **Il preventivo di acquisto / RFQ** — ha il suo documento
  ([sviluppo-preventivi-acquisti.md](sviluppo-preventivi-acquisti.md)) e sta a monte.
* **I listini fornitore** — [listini-fornitori.md](listini-fornitori.md). Qui se ne tocca solo
  il bordo, al §9.
* **La fattura passiva e la contabilità** — `contabilita` è vuoto e fuori perimetro. §8-a dice
  che cosa ne discende per la partita.
* **Il ledger di magazzino** — le decisioni D-1 e D-7 stanno nel brief magazzino. Qui si
  dichiara la dipendenza, non la si risolve.
* **Il portale fornitore** — le due policy in dry-run sono sue; §4.1 dice solo che esistono e
  non sono armate.

---

## 12. Registro delle revisioni

| Data | Cosa |
| --- | --- |
| 2026-09-01 | Prima stesura. Misure di stato prese lo stesso giorno. Decisioni D-1, D-3, D-5, D-7, D-8 chiuse sul principio da Tid; D-6 non risposta; D-9 e D-10 aperte in questa analisi |
| 2026-09-01 | 🔴 **Correzione su `config.ambiti`** (rilievo di Tid): la prima stesura le attribuiva un legame col magazzino, ripetendo un'inferenza per somiglianza di nome della pagina auto-generata. La struttura (`extra_country` + indice su `stato_utilizzo`/`settore`/`codice_ambito`) dice che è della famiglia dei riferimenti localizzati. §7 riscritto: gli assi «ambito» sono **quattro** e il nostro è un quinto ⇒ CHECK a due valori, nessuna tabella riusata. Nuova **D-11** (che farne), rinviata |
| 2026-09-01 | ⭐ **D-6 chiusa** dopo verifica: l'ancora del BB indirizzi è un **parametro**, non «il cliente» ⇒ il BB si usa. Emerso che `acquisti.ddt_indirizzi` **è già convergente** dal 2026-07-11 (ambito `ACQUISTI_DDT`, funzione dedicata ritirata): `acquisti.ordini` è l'unico documento rimasto sulla forma vecchia. Nuovo **§7-bis** con i due limiti veri del BB (join BA cablato, ancora singola) e la nuova **D-6b** |
| 2026-09-01 | **D-9 chiusa** (kit sì, se l'articolo lo richiede) e **D-10 chiusa sul principio** (il motore di numerazione sale, se la salita compra una pulizia) |
| 2026-09-01 | ⭐ **D-12, posta da Tid**: servono due numeri, il nostro e quello del fornitore. Verificato che **nessun documento del progetto** ha oggi una colonna per il riferimento della controparte — non c'è precedente. Emersa una collisione già in casa: `acquisti.ddt.numero` **è già** il numero del fornitore, e `famiglie_documento.colonna_numero` puntata lì lo sovrascriverebbe. Nuova convenzione generale al §6 |
| 2026-09-01 | 🔴 **Revisione — cinque rilievi, tre correggono il documento.** ① **D-10 rimandata**: la regola del 2 non si applica a un secondo consumatore che non esiste; si fa la correzione di `colonna_billing_account` e si rimanda il trasloco. ② **Il `numero` liberato su `acquisti.ddt` si TOGLIE**, non si tiene vuoto — la prima stesura ricadeva nel difetto che essa stessa contesta in ⑩ e §7; e così ⑦ si scioglie meglio. ③ **⑧ riformulato**: `ddt.ordine_id` non è ridondante, è **sbagliato** — un fornitore consegna più ordini in una bolla, e la FK di testata lo nega. ④ Nuovo **§8 «Il buco: il ramo CREDITO non ha una porta d'uscita»** (D-14) — la coda «da accreditare» non si chiude senza ciclo passivo, e serve la dichiarazione esplicita di accredito. ⑤ Nuovo **§9-bis** (D-15): la classe «esiste e non è armata» è uscita **quattro volte in due analisi**, si presidia con tre viste `dbops` invece che istanza per istanza. Nuove **D-13**, **D-14**, **D-15** |
| 2026-09-01 | ⭐ **La convenzione D-12 acquista il suo secondo caso** (rilievo di Tid): il riferimento della nota di credito del fornitore nella dichiarazione di accredito (D-14) è già una sua applicazione, e il campo non si chiama `numero`. ⚠️ È l'applicazione che vale di più — è **preventiva**, non correttiva: con un caso solo la convenzione si legge come una toppa a `acquisti.ddt`, con due come una regola. Annotata in §6 e §8 |
| 2026-09-01 | 🔴 **Revisione — il Lotto 1 non era tutto su terreno vuoto** (rilievo di Tid). ① Il satellite degli ambiti sta in `config`, su tabelle che **`vendite` usa in esercizio**: senza il backfill `VENDITE` completo il guard rifiuta il primo cambio di stato di un ordine di vendita. Il Lotto 1 è stato **spaccato in 1a (terreno vuoto, solo `acquisti`) e 1b (migrazione su dominio vivo)**, con l'invariante «nessuno stato senza ambito» da provare in pgTAP — il seed incompleto non fallisce, *non fa niente*. ② Verificata la **coda fuori dal DB**: cambiano **due** funzioni (`fn_available_actions_ordine`/`_ddt`), BE e FE **zero righe** perché il contratto è il campo emesso `stato_info_key` e non la colonna — ⚠️ ma la proprietà nel satellite deve restare `nessuna_azione_key`, o `check_i18n_keys.py` diventa verde per cecità. ③ **D-13 chiusa**: `serie` e `anno` sono del fornitore, e ne esce **D-13b** su `data` |
| 2026-09-02 | 🔴 **Corretto un fatto sbagliato al §6** (rilievo di Tid), e **verificato sul DB** invece che ragionato: `format('%I', NULL)` **solleva** (`22004`, «i valori vuoti non possono essere formattati come un identificativo SQL»), non produce l'identificatore letterale. Era falso in tutte e due le metà. ⭐ La regola — saltare nella query che sceglie le famiglie — **non cambia**, e il motivo migliora: si fallirebbe con un errore **di PostgreSQL**, senza codice di dominio, dentro uno spostamento di billing account che con le famiglie non c'entra. ⚠️ Il ramo muto vive su `%s` (stringa vuota), non su `%I`. Allineato al [brief](brief-db-modifiche-certe-ciclo-vendita-e-articolo.md) §3-bis, che era già stato corretto: i due documenti dicevano due cose opposte sullo stesso fatto |
| 2026-09-02 | 🔴 **Tolta la cerimonia da produzione** (Tid: «i dati sono solo di test, possiamo fare quello che vogliamo»). Il §7 chiamava il Lotto 1b «migrazione su dominio vivo con dati veri» e ne faceva una cautela sui **dati**: registro sbagliato. ⭐ Riscritto sul punto vero, che ne esce **più forte** — il satellite non mette a rischio delle righe, mette a rischio **una funzione di vendita che gira**: un catalogo incompleto impedisce a *qualunque* ordine di cambiare stato, anche su un DB appena rifatto. ⇒ La distinzione da tenere: «niente produzione» toglie il rischio **sui dati**, non quello **funzionale**. Da tre obblighi a due, e il Lotto 1b rinominato |
