# Analisi DB — magazzino: come un movimento dice da dove viene, e perché oggi non lo può dire per la produzione

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Origine.** Domanda di Tid, 2026-09-01: *«sul magazzino abbiamo sempre la
> sorgente polimorfa?»*. La risposta è sì su quattro tabelle — ma cercandola è
> emerso che in `magazzino` di modi per dire «da dove viene questo movimento» ne
> convivono **due**, che il ledger usa quello **senza catalogo**, e che il
> vocabolario delle causali **nomina già la produzione** mentre la cosa a cui
> punta non esiste.
>
> **Perché adesso.** Tid: *«siamo vicini a iniziare lo sviluppo, e anche se ora
> non c'è dobbiamo prevederlo in modo che possa funzionare anche per la
> produzione»*. ⭐ È la condizione migliore in cui si possa aprire un cantiere:
> **zero righe in tutte le tabelle operative**, quindi nessuna bonifica dati e
> nessun vincolo storico da rispettare. Ciò che si decide qui si decide libero.
>
> **Stato:** 🔵 **APERTO — è un'ANALISI, non un piano.** Nessun changeSet
> scritto, niente applicato. Le decisioni stanno in §8 e vanno prese **prima**
> che si scriva la prima riga di `magazzino`.
>
> 📌 **Declassato ad analisi il 2026-09-01** (decisione di Tid), e rinominato da
> `brief-db-…` a `analisi-db-…`: ⭐ è la stessa distinzione già usata dal cantiere
> numerazione, dove l'**analisi** dice *perché* e il **brief** dice *cosa si fa*.
> ⛔ **Di questo documento non esce nessuna modifica certa**, ed è il suo esito
> vero: ogni voce qui dentro è agganciata a una delle D-1 → D-8. Il piano
> operativo delle sole modifiche **certe** vive in
> [brief-db-modifiche-certe-ciclo-vendita-e-articolo.md](brief-db-modifiche-certe-ciclo-vendita-e-articolo.md),
> e sta quasi tutto su `vendite` e `catalogo`.
>
> ⚠️ **Perimetro di questa analisi:** solo l'**aggancio al documento di origine** e
> ciò che serve perché regga anche per la produzione. Il resto di *«cosa manca a
> magazzino»* — valorizzazione, giacenza, ubicazioni, lotti/seriali, il rapporto
> fra `causali.segno` e `movimenti.qta` — è l'**analisi successiva**, concordata
> con Tid nella stessa sessione. Vedi §9.

---

## 0. In due parole, senza tecnicismi

Ogni volta che della merce entra o esce dal magazzino, il sistema scrive una
riga: *questo articolo, questa quantità, in questa data*. E accanto scrive **da
dove viene quel movimento** — da una bolla, da un reso, da un inventario.

Il problema è tutto lì, in quella seconda parte.

- **Oggi quel «da dove viene» si scrive come si scriverebbe su un foglietto.**
  Sono tre caselle di testo libero. Nessuno controlla che il documento citato
  esista davvero: si può scrivere il numero di una bolla mai emessa e il sistema
  lo accetta senza fiatare. ⚠️ Il guaio è che una cosa così **non si scopre
  subito**: si scopre mesi dopo, quando una giacenza non torna e bisogna capire
  perché.
- **Le altre tabelle del magazzino invece un controllo ce l'hanno** — ma è fatto
  in un modo che riesce a riconoscere solo due tipi di documento su dieci, e non
  sono quelli che servono. Le bolle, i resi e gli ordini, cioè il pane
  quotidiano, **non entrano**.
- **La produzione è già scritta a metà.** Nell'elenco delle causali ci sono già
  «uscita materiali per ordine di lavoro» e «rientro materiali». Ma **l'ordine di
  lavoro come cosa non esiste**: c'è il nome, non c'è l'oggetto. Se domani si
  cominciasse a produrre, quei movimenti punterebbero al nulla.
- ⭐ **La buona notizia è che il magazzino è ancora completamente vuoto.** Non
  c'è una sola riga da correggere. È l'unico momento in cui si può cambiare la
  forma delle cose invece di aggiungere pezze sopra, e costa zero.

Il resto di questo documento spiega ognuno di questi punti con i dettagli
tecnici, e in §8 elenca le **decisioni da prendere prima di cominciare**.

---

## 1. Che cosa è stato misurato, e di che natura è

Misurato il **2026-09-01** sulla documentazione auto-generata (`docs/it/dbzero/`,
che riflette gli oggetti vivi) e su `db/changelog/migrations_v2/`.

⚠️ **Sono tutte misure di struttura, non di contenuto**: colonne, vincoli,
indici, seed di catalogo. Nessuna decisione qui sotto poggia su un `count(*)` —
e quando compare «zero righe» è per dire che *non c'è una bonifica da fare*, mai
per dire che un caso non esiste.

---

## 2. In `magazzino` i modi di dire «da dove viene» sono due

| Modello | Come è fatto | Chi lo usa in `magazzino` |
| --- | --- | --- |
| **Sorgente polimorfa a catalogo** | `sorgente_tipo_id` → `config.sorgenti` (FK) + la chiave del record puntato | `rettifiche`, `trasferimenti`, `inventari`, `eventi_assets` |
| **Riferimento testuale libero** | `doc_schema` + `doc_table` + `doc_id` + `doc_riga_id`, tutte stringhe/bigint **senza FK e senza catalogo** | ⛔ `movimenti` (il ledger) e `reservations` |

⛔ **Il paradosso è nella colonna di destra.** Le tabelle di *testata* — una
rettifica, un trasferimento, un inventario — puntano al catalogo. **Il ledger,
cioè la tabella che conta, no.** E le righe di quelle testate generano movimenti:
i due lati dello stesso fatto parlano due lingue diverse, e nessuna delle due
sa tradurre nell'altra.

⚠️ `doc_schema`, `doc_table` e `doc_id` sono **NOT NULL**: ogni movimento *deve*
dichiarare un documento. Non esiste oggi la forma «movimento senza documento», e
la conseguenza pratica è che chi non ne ha uno è **costretto a inventare dei
valori** — che è il modo in cui un riferimento libero si sporca il primo giorno.

---

## 3. Le quattro tabelle a catalogo non possono riferire i documenti che servono

Le quattro hanno `sorgente_tipo_id` + `sorgente_uid uuid`. **Non hanno
`sorgente_riga`.**

Il guard tipizzato (`script.trgfn_guard_sorgente_polimorfa_tipizzata`) dichiara
nel proprio corpo dove sta la chiave, e sono due colonne alternative:

> *MODELLO A (colonne tipizzate alternative): la chiave sta in `NEW.sorgente_riga`
> (BIGINT) per selector `'id'` e in `NEW.sorgente_uid` (UUID) per selector `'uid'`.*

E in `config.sorgenti` il `key_selector` è **`id` per otto sorgenti su dieci**:

| `key_selector = 'id'` | `key_selector = 'uid'` |
| --- | --- |
| COMMESSA · ATTIVITA · CONTRATTO · ORDINE_VENDITA · **DDT_VENDITA** · FATTURA · ATTIVITA_CONSUMI · **RESO_VENDITA** | PREVENTIVO · OFFERTA_COMMERCIALE |

⛔ **Quindi quelle quattro tabelle, per struttura, sanno riferire solo preventivi
e offerte** — le due sorgenti che a magazzino servono meno di tutte. Una
rettifica nasce da un inventario, un trasferimento da un ordine, un evento asset
da un DDT o da un reso: **tutte `id`, e non esiste la colonna in cui scriverle**.

⚠️ **Non è un difetto solo di `magazzino`.** Censite le **23 tabelle** del
database che hanno `sorgente_tipo_id`: **7 hanno il modello completo**
(`sorgente_riga` + `sorgente_uid`), **15 hanno solo `sorgente_uid`**, una non ha
né l'una né l'altra. Per alcune delle quindici l'assenza è **corretta** — un
contratto nasce da un'offerta, un ordine da un preventivo, e sono `uid` — ma è
una risposta che va data **tabella per tabella, sul modello**: quali sorgenti
possono legittimamente alimentarla. ⛔ Non si generalizza in nessuna delle due
direzioni.

---

## 4. Il guard tipizzato non è agganciato da nessuna parte

`script.trgfn_guard_sorgente_polimorfa_tipizzata` esiste. Cercandolo su tutte le
tabelle del database, risulta montato su **due sole**: `pratiche.pratiche_sorgenti`
e `vendite.commesse_sorgenti` — ed entrambe usano la **sorella `_testuale`**.

⛔ **La variante tipizzata — quella scritta apposta per il modello a colonne
alternative, cioè quello che `magazzino` usa — oggi non presidia niente.**

⭐ È **la stessa forma del difetto di luglio**, sopravvissuta in un dominio che
quella bonifica non aveva guardato. Il changelog del 26 luglio lo dice con
queste parole: *«il guard sulla sorgente polimorfa esisteva ma non era agganciato
a nulla»*. Allora si agganciò dove c'erano righe da bonificare; `magazzino` era
vuoto, e un dominio vuoto non produce il rosso che fa accorgere.

---

## 5. Un UNIQUE che ha due comportamenti opposti, e nessuno dei due è quello voluto

```sql
CREATE UNIQUE INDEX uq_mag_movimenti_docref
    ON magazzino.movimenti (doc_schema, doc_table, doc_id, doc_riga_id);
```

`doc_riga_id` è **nullable**, e in PostgreSQL i NULL in un indice unico sono
**distinti** per default. Quindi lo stesso indice fa due cose opposte:

| Se `doc_riga_id` è… | Che cosa vincola davvero |
| --- | --- |
| **valorizzato** | ⛔ **un solo movimento per riga di documento, per sempre** |
| **NULL** | ⛔ **niente**: due NULL non collidono, i duplicati passano tutti |

⚠️ **Il ramo restrittivo è già in rotta di collisione con un caso normale**: un
trasferimento genera **due** movimenti — `TRASF_OUT` e `TRASF_IN` — dalla stessa
riga di `trasferimenti_righe`. Con `doc_riga_id` valorizzato il secondo INSERT
viola l'indice. La colonna `movimenti.transfer_uid` esiste e sembra nata per
tenere insieme la coppia, ma **non compare in questo indice**.

⚠️ E il ramo permissivo è peggio del ramo assente, perché *sembra* un presidio:
è la trappola già registrata nel progetto — «due forme fanno evaporare un
vincolo senza errore».

---

## 6. La produzione: il vocabolario c'è già, la cosa a cui punta no

⭐ **Questa è la parte che rende il brief urgente**, ed è anche la notizia buona:
chi ha disegnato `magazzino` la produzione l'aveva **prevista**.

Nel seed di `magazzino.causali` (10 righe) ci sono già:

| Causale | Segno | `richiede_odl` |
| --- | --- | --- |
| `ODL_USCITA_MAT` — Uscita materiali per ODL | −1 | **`t`** |
| `ODL_ENTRATA_MAT` — Rientro materiali da ODL | +1 | **`t`** |

e in `magazzino.ambito_causale` c'è `ODL — Movimenti da Ordini di Lavoro`.

⛔ **Ma l'ODL non esiste**: nessuna tabella «ordine di lavoro» in nessuno dei 21
schemi, nessuno schema `produzione`, e **nessuna sorgente ODL** in
`config.sorgenti` — dove le dieci sorgenti registrate sono **tutte di `vendite`**
(scope `PIPELINE_MARKER`, `PUSH_COMMESSA`, `POST_INVOICE`, `PUSH_CONTRATTO`,
`REVERSE_FLOW`). ⚠️ Non c'è nemmeno una sorgente di **acquisti**, benché
`CARICO_ACQ` — «Carico da DDT acquisto» — sia la prima causale del seed.

Quindi oggi un versamento di produzione dovrebbe scrivere in
`movimenti.doc_schema/doc_table/doc_id` — **NOT NULL** — il riferimento a una
tabella che non c'è. Non fallirebbe: sono stringhe libere. **Scriverebbe un
riferimento a vuoto, e nessun vincolo se ne accorgerebbe.**

⚠️ **Un secondo dettaglio, piccolo e dello stesso tipo:** in tutte e 10 le
causali del seed la colonna `ambito_causale_id` è **vuota**. Il vocabolario dei
sei ambiti esiste e **non è collegato a niente**.

---

## 7. Perché la produzione non è «un consumatore in più»

⭐ La produzione non aggiunge solo righe al catalogo delle sorgenti: **rompe due
assunzioni** che il modello di oggi dà per buone, e per questo va decisa adesso
e non quando arriverà.

1. **Un documento riga → N movimenti, in tempi diversi.** Un ODL preleva
   materiale in **prelievi parziali** e versa il prodotto finito in **versamenti
   parziali**. L'assunzione «una riga di documento, un movimento» del §5 non è
   stretta: è **falsa** per la produzione, e lo è già per il trasferimento.
2. **Un movimento senza documento a monte.** Uno sfrido, un recupero, un
   versamento a fronte di un ODL a ciclo aperto: il ledger di produzione ha
   movimenti la cui origine è **un ordine di lavoro, non un documento
   commerciale** — e `doc_schema/doc_table/doc_id` NOT NULL costringe comunque a
   riempire tre colonne.

⛔ **E c'è una decisione di modello sotto, che non la prende un piano
operativo**: se l'ODL sarà una **sorgente** come le altre (una riga in
`config.sorgenti`, `target_table = produzione.ordini_lavoro`, `key_selector =
'id'`) oppure un **anello proprio**, con un ledger suo che si riversa in
magazzino. La prima strada riusa tutto ciò che esiste; la seconda è la scelta che
si fa quando il dominio ha un ciclo di vita che il magazzino non deve conoscere.

---

## 8. Le decisioni da prendere — prima di scrivere

> Nessuna di queste è stata presa. Sono qui perché il cantiere non parta
> assumendo la risposta.

| # | Decisione | Perché non la decide un piano |
| --- | --- | --- |
| **D-1** | **Un modello solo o due?** `movimenti`/`reservations` passano alla sorgente a catalogo, oppure `doc_schema/doc_table/doc_id` resta ed è **il** modello del ledger — e allora sono le quattro testate a doversi allineare a lui. ⛔ Quello che non regge è **tenerli entrambi senza una regola** | è una scelta di architettura del dominio, e vale anche per `acquisti`, che ha lo stesso doppio |
| **D-2** | **Le quattro testate prendono `sorgente_riga`?** Se sì, diventano capaci di riferire le otto sorgenti `id` e il guard tipizzato ha finalmente dove agganciarsi. Se no, va scritto **quali sorgenti sono ammesse** e presidiato | dipende da D-1 |
| **D-3** | **Si aggancia il guard tipizzato** alle tabelle del modello A, in `magazzino` e altrove? ⭐ Oggi non presidia niente: o trova i suoi consumatori o è codice morto | il roll-out tocca 15 tabelle: è un perimetro, non una riga |
| **D-4** | **`uq_mag_movimenti_docref`: che cosa deve vincolare davvero?** Le tre forme sono: toglierlo, renderlo `NULLS NOT DISTINCT` con dentro `causale_id` o `transfer_uid`, oppure spostare l'unicità su una **chiave dell'operazione**. ⭐ La terza è scritta per intero al **§8-quater**, con le due condizioni senza cui non funziona | ⛔ oggi il vincolo dice due cose opposte a seconda di un NULL: qualunque scelta è meglio, ma va scelta. ⚠️ E toglierlo porta via anche una protezione buona non dichiarata (il doppio scarico): la sostituzione si decide **insieme** alla rimozione |
| **D-5** | **L'ODL è una sorgente o un anello?** (§7). Da questa discende se `config.sorgenti` cresce di 1 riga o se nasce uno schema `produzione` | è la decisione di dominio, e la prende Tid |
| **D-6** | **Il movimento senza documento è ammesso?** Se sì, `doc_*` smette di essere NOT NULL e serve una regola su chi può ometterlo; se no, ogni movimento deve avere un documento **che esiste**, e allora serve il catalogo | ⚠️ oggi la risposta è «obbligatorio, ma non verificato»: il peggiore dei tre mondi |
| **D-7** | **Acquisti entra nel catalogo delle sorgenti?** `CARICO_ACQ` è la prima causale del seed e il DDT di acquisto non è una sorgente registrata | tocca `acquisti`, che è un altro dominio fermo |
| **D-8** | **`causali.ambito_causale_id` si valorizza** (e allora l'ambito serve a qualcosa) **o l'ambito si ritira?** ⛔ Oggi la colonna è **vuota in tutte e dieci le causali**: il vocabolario dei sei ambiti esiste e non è collegato a niente | ⛔ un vocabolario collegato a zero righe è debito che **sembra** struttura — e chi legge lo scambia per un pezzo funzionante (§8-ter) |
| **D-9** | **I due presidi che compensano il polimorfismo** (§8-bis): il tipo di sorgente vincolato al catalogo, e una **vista dei riferimenti orfani che deve restare vuota**. ⚠️ Sul ledger **non sono aggiungibili da soli**: presuppongono D-1 | il pattern è già di casa e si riusa; ma la parte sul ledger *è* la decisione D-1, non un'aggiunta sopra |

---

## 8-bis. I due presidi che compensano il polimorfismo (D-9)

> **Origine:** nota di revisione portata da Tid, 2026-09-01. La proposta è
> accolta nel merito; le due precisazioni sotto sono la ragione per cui entra
> come **decisione** e non come rifinitura.

**Il ragionamento, in parole semplici.** Quando una riga può puntare a *qualsiasi*
tipo di documento, il database non può più garantire da solo che quel documento
esista — la garanzia automatica funziona solo quando il bersaglio è **uno e
sempre lo stesso**. È il prezzo della flessibilità, ed è un prezzo accettabile:
ma va pagato con due controlli scritti a mano, se no la prima riga sbagliata la
si scopre leggendo una giacenza che non torna.

I due controlli sono:

1. **Il tipo di sorgente deve venire da un elenco chiuso**, non essere scritto a
   mano. Chi sbaglia a scrivere il tipo deve ricevere un rifiuto subito.
2. **Una vista che elenca i riferimenti a vuoto, e che deve restare vuota.** Se
   compare una riga, qualcuno sta puntando a un documento che non c'è. ⭐ È lo
   stesso identico meccanismo che il progetto usa già in Anello 0
   (`dbops.vw_bersagli_non_dichiarati`, `vw_eventi_non_dichiarati` e i due
   registri dei codici errore): non è un'invenzione, è un pattern da riusare.

⭐ **E c'è un dettaglio che rende il secondo davvero fattibile**, non solo
auspicabile: nel catalogo delle sorgenti la colonna che dice *quale tabella
guardare* non è testo libero, è un **riferimento vero a un oggetto del
database**, e accanto c'è già scritto *quale campo usare come chiave*. Con
quelle due informazioni la vista degli orfani si scrive **una volta sola** e vale
per tutte le sorgenti, presenti e future — produzione compresa.

### ⚠️ Due precisazioni, e cambiano la taglia del lavoro

**Il primo controllo, sulle quattro tabelle di testata, c'è già.** Rettifiche,
trasferimenti, inventari ed eventi asset hanno il tipo di sorgente agganciato al
catalogo. ⛔ **Manca sul registro dei movimenti e sulle prenotazioni**, che il
catalogo non lo usano affatto: lì il riferimento è testo libero. Quindi metterlo
non è «consolidare un presidio»: è **portare il registro sul modello a
catalogo**, che è la **D-1**. Sembra una rifinitura da mezz'ora ed è invece la
scelta portante — va presa come tale.

**E due presidi non risolvono §5.** Dicono che il documento citato *esiste*. Non
dicono **quante volte** una riga di documento può generare un movimento — e su
quello il vincolo di oggi ammette *un movimento solo*, oppure non controlla
niente. ⛔ Il trasferimento lo rompe **già adesso**, prima e indipendentemente
dalla produzione: da una sola riga nascono due movimenti, l'uscita da un
magazzino e l'entrata nell'altro. Quello è **D-4**, ed è un problema di modello:
nessuna vista di orfani lo intercetta.

---

## 8-ter. L'ordine in cui conviene costruire

> Anche questo dalla nota di revisione del 2026-09-01, ed è la parte che
> sottoscrivo per intera.

| # | Passo | Perché in questo punto |
| --- | --- | --- |
| 1 | **Sistemare il segno delle causali** *prima* della prima riga | è la cosa che, sbagliata, falsa ogni numero a valle — e correggerla dopo vuol dire ricalcolare tutto (⚠️ perimetro dell'analisi successiva, §9) |
| 2 | **Inventario iniziale** come primo carico | è la sorgente più semplice: **non ha un documento a monte**, quindi collauda il registro senza dipendere da nessuna catena |
| 3 | **Scarico da bolla di vendita** come primo consumo | il primo caso con un documento vero dietro, su una catena che esiste già ed è collaudata |
| 4 | **Acquisti** come seconda sorgente | entra su un registro già provato, e porta con sé la sua decisione (D-7) |
| 5 | **Produzione** come terza | ⭐ se i punti sopra sono stati decisi bene, è *una sorgente in più e un set di causali*, non una riscrittura |

⚠️ **Il passo 3 è il primo che ha bisogno del §8-quater**: è lì che nasce il
doppio scarico, e la chiave dell'operazione va decisa prima di scriverlo — non
dopo aver tolto l'indice.

⚠️ **Ma il passo 2 è già la prova della D-6, e va saputo prima di farlo.**
L'inventario iniziale è proprio il caso del **movimento senza documento
commerciale** — mentre oggi le tre caselle del riferimento sono **obbligatorie**.
Quindi la primissima riga che si scriverà in magazzino è esattamente quella che
mette alla prova la decisione che nessuno ha ancora preso. È un ottimo collaudo
e una pessima sorpresa: **D-6 va decisa prima del passo 2**, non durante.

⚠️ **E una nota sul passo 5**, per non lasciare in piedi una rassicurazione
sbagliata: *«la produzione sarà una sorgente in più, non una riscrittura»* è vero
**solo se D-4 e D-6 vengono decise adesso**. Se il vincolo di §5 resta com'è, la
produzione — che preleva e versa **in più riprese**, quindi molti movimenti per
una sola riga di ordine — quel vincolo lo riscrive. E il «nuovo set di causali»
in buona parte **c'è già** (§6): quello che manca è l'ordine di lavoro, non le
causali.

---

## 8-quater. La chiave dell'operazione — dove vive la regola anti-doppio (D-4)

> **Origine:** appunti di revisione portati da Tid il 2026-09-01 (*«quell'indice va
> tolto, non riparato: è una chiave di idempotenza travestita da vincolo
> semantico»*) e la domanda che ne è seguita — *«la stessa colonna potrebbe
> impedire anche il doppio carico, quando riceveremo gli acquisti?»*. Sì, e la
> risposta completa è questa sezione.
>
> ⚠️ **È una proposta, non una decisione presa.** La D-4 resta di Tid: qui c'è la
> terza delle sue tre forme, scritta per intero perché sia scegliibile.

### Il difetto non è che l'indice sia sbagliato: è che risponde a un'altra domanda

`uq_mag_movimenti_docref` guarda il **documento**. Ma il documento è il
*contesto* di un movimento, non la sua *identità*: da una riga di documento
possono nascere legittimamente N movimenti, e già oggi ne nascono due (il
trasferimento). ⛔ Vincolare sul documento significa scrivere «una riga di
documento, un movimento», che è una frase **falsa adesso**, non fra due cantieri.

⭐ E c'è una protezione buona nascosta là dentro che nessuno aveva dichiarato: di
rimbalzo, quell'indice impedisce anche il **doppio scarico** della stessa riga di
bolla. Togliendolo si porta via anche quella. ⚠️ **Per questo la sostituzione va
decisa insieme alla rimozione, non a valle**: toglierlo e basta lascia scoperto un
caso che capita davvero.

### Il precedente è già in esercizio, e non è una tabella

Lo stesso identico problema — *un batch rilanciato non deve spingere due volte la
stessa riga* — è già risolto nella pipeline di fatturazione, ed è risolto con una
**colonna**: `vendite.commesse_attivita.segment_key`, con
`uq_commesse_attivita_commessa_segment` su `(commessa_id, segment_key)`. Le chiavi
sono composte a mano e ricalcolabili — verificato il 2026-09-01, i prefissi in uso
sono `ORD`, `DDT`, `PREV`, `MAN` (es. `ORD:{uid}:R:{riga}`).

⛔ **Una tabella dedicata «registro degli scarichi» è la versione debole**, e va
scartata per una ragione di modello: esisterebbe **solo per reggere un vincolo**,
non risponde a nessuna domanda che qualcuno farebbe, e crea **due sedi dello
stesso fatto** — il ledger dice «questa riga ha scaricato», il registro pure. Chi
scrive un movimento senza passare di lì le separa in silenzio.

⭐ **Quando invece una tabella è giusta**: quando la relazione *è* un dato che
qualcuno legge. È il caso di `vendite.ordini_righe_fulfillment`, che esiste perché
«quanto manca da evadere?» è una domanda vera — e l'unicità gli viene in regalo.
Per lo scarico quella domanda non c'è: **il movimento stesso è la risposta**.

### La proposta

🔴 **Riscritta il 2026-09-02 dopo un rilievo di Tid**, e il rilievo cambia la
forma. La prima stesura proponeva una **chiave testuale composta a mano**
(`operazione_key`). ⛔ Se la D-1 atterra sul catalogo, il movimento porta **già**
`sorgente_tipo_id` più la chiave del record: una stringa che ripete quelle
informazioni è una **seconda sede dello stesso fatto** — precisamente ciò che
questo documento contesta al §2 e che l'analisi acquisto contesta a
`ddt.ordine_id`. *Non si può denunciare un doppio e poi introdurne uno.*

⭐ **La forma giusta è derivata, non parallela**: l'identità di un movimento è
**la sua sorgente più il verbo dell'operazione**.

| Cosa | Come |
| --- | --- |
| Identità del movimento | `(sorgente_tipo_id, chiave della sorgente, verbo)` — nessuna colonna nuova che *ripeta* le prime due |
| Colonna nuova | solo il **verbo**: `operazione_verbo` (`SCARICO`, `CARICO`, `OUT`, `IN`, `PRELIEVO`, `VERSAMENTO`, …) |
| Il vincolo | `UNIQUE` **parziale** sulle tre, attivo dove la sorgente è valorizzata |
| `uq_mag_movimenti_docref` | ⛔ si **toglie** |
| `transfer_uid` | resta, e fa il lavoro **opposto**: raggruppa i due movimenti di un trasferimento (il suo indice è **non** unico, apposta). Una dice «questi vanno insieme», l'altra «questo esiste una volta sola» |

⭐ **Dove l'operazione è essa stessa un record, la sorgente È l'operazione** — e
allora non c'è più niente da comporre: il ricevimento, il prelievo, la riga
d'inventario hanno un id, e quello è la chiave. ⚠️ Ne discende che il catalogo
deve conoscere anche le **operazioni**, non solo i documenti commerciali: è
esattamente l'allargamento che la D-6 già richiede, non un costo nuovo.
⭐ E il precedente c'è: `config.sorgenti` porta già **cinque sorgenti di riga** —
`DDT_VENDITA_RIGA`, `ORDINE_VENDITA_RIGA`, `FATTURA_RIGA`, `CONTRATTO_RIGA`,
`PREVENTIVO_RIGA`, tutte con `key_selector = 'id'`.

⚠️ **Perché resta tutto nullable, e non è pigrizia.** Ci saranno movimenti senza
un'operazione a monte (una correzione a mano, un caso nuovo). Con le colonne
obbligatorie, chi non ha una sorgente **se la inventa** — ed è esattamente il modo
in cui il riferimento libero di §2 si sporca il primo giorno. Chi ha una sorgente
è protetto; chi non ce l'ha passa, e **si vede** che non ce l'ha.

#### ⛔ E la stringa leggibile? Non può essere una colonna generata

La tentazione successiva è tenere anche una stringa parlante — `DDT:47:SCARICO` —
come colonna **generata**, così non può contraddire le altre. ⛔ **Non è
possibile, ed è verificato il 2026-09-02**: una `GENERATED ALWAYS AS … STORED` non
ammette sottoquery (*«non è possibile utilizzare la sottoquery nell'espressione di
generazione di colonne»*), e il prefisso vive in `config.sorgenti` — cioè
richiede un join.

⇒ Delle due l'una, e vanno tenute distinte:

| | Dove sta l'identità | Il prefisso | Il rischio |
| --- | --- | --- | --- |
| **A — consigliata** | sulle **colonne** `(sorgente, chiave, verbo)` | non serve: nessuna stringa da comporre | ⭐ la contraddizione è **impossibile**, non «rilevabile» |
| **B** | su una stringa scritta dalla funzione madre | dal `codice_interno` del catalogo | ⚠️ la stringa può **divergere** dalle colonne, e serve un presidio che lo scopra |

⭐ **Si può avere anche la leggibilità, senza pagarla**: la stringa parlante la
compone una **vista** (che il join lo può fare), non una colonna. Nessun dato
duplicato, nessuna divergenza possibile, e chi legge il ledger vede
`DDT_VENDITA_RIGA:47:SCARICO` lo stesso.

### ⛔ Le due condizioni senza cui non funziona

**1. La chiave la compone l'OPERAZIONE, non il documento.**
Sul ricevimento di acquisto la stessa riga di bolla del fornitore può caricare
**più volte, legittimamente**: arrivano 100 pezzi, se ne accettano 60 oggi e 40
dopo il controllo. E c'è la **ri-consegna**, dove la stessa riga d'ordine riceve
merce una seconda volta. ⛔ Una chiave `BOLLA-ACQ:{riga}:CARICO` respingerebbe il
secondo carico legittimo — cioè riprodurrebbe il difetto di partenza con un nome
più bello. **Il documento entra nella chiave come contesto; l'identità è
l'operazione** («il ricevimento numero 3 della riga 47», non «la riga 47»).

**2. La chiave è RICALCOLABILE, non estratta a caso.**
Un identificativo casuale generato a ogni chiamata produrrebbe una chiave **nuova**
a ogni tentativo ripetuto: nessuna collisione, doppio movimento, e una protezione
che *sembra* esserci. Deve valere *dagli stessi fatti esce sempre la stessa
chiave* — è precisamente la proprietà per cui `segment_key` funziona.
⇒ Ne discende **chi la compone**: la funzione madre che scrive il movimento, in
modo deterministico. ⚠️ Non un valore che arriva dal backend a ogni chiamata.

### Che cosa copre, senza aggiungere niente per ogni caso nuovo

> ⚠️ La colonna di mezzo mostra la **forma leggibile** (quella che compone la
> vista). L'identità vera è la terna `(sorgente, chiave, verbo)`: sotto ogni riga
> di questa tabella c'è quella, non una stringa memorizzata.

| Operazione | Come si legge | Nota |
| --- | --- | --- |
| Scarico da riga di bolla di vendita | `DDT_VENDITA_RIGA:{riga}:SCARICO` | ⭐ la sorgente **esiste già** a catalogo |
| Carico da bolla del fornitore, anche **parziale e ripetuto** | sorgente = il **ricevimento**, non la riga di bolla | ⭐ è il caso che smaschera l'identità sbagliata |
| Reso al fornitore | sorgente = il reso | |
| Ri-consegna sullo stesso ordine | sorgente = la ri-consegna | non collide col primo carico |
| Trasferimento | stessa sorgente, verbo `OUT` e verbo `IN` | ⭐ due righe distinte: **il caso che l'indice di oggi sbaglia** |
| Prelievi e versamenti di produzione | sorgente = il prelievo / il versamento | N legittimi, nessuno blocca l'altro |
| Inventario, rettifica | sorgente = la propria riga | |
| Correzione a mano, senza operazione | sorgente vuota | ⚠️ il vincolo parziale non si applica: passa, e **si vede** che è così |

⭐ **È il vero argomento per togliere l'indice**: non «era sbagliato», ma
*rispondeva alla domanda sbagliata*. Spostata la domanda sull'operazione, il
trasferimento smette di essere un'eccezione, il ricevimento parziale funziona, e
la produzione non ha bisogno di niente di nuovo.

### Che cosa questa colonna NON fa

* ⛔ **Non dice chi può scrivere un movimento**, né se il documento citato esiste:
  quelle sono D-1 e i due presidi di §8-bis.
* ⛔ **Non sostituisce il controllo dentro la funzione**, che resta e serve a
  un'altra cosa: dare un messaggio comprensibile («questa riga ha già scaricato
  il …»).
* 🔴 **E NON è «la rete per chi non passa dalla funzione».** *(Frase della prima
  stesura, corretta il 2026-09-02 su rilievo di Tid: era sbagliata.)* Chi scrive
  in `movimenti` scavalcando la funzione madre **non compone nemmeno la
  sorgente**: lascia i campi vuoti, e con il vincolo parziale passa liscio.
  ⇒ Il `UNIQUE` protegge dalla **funzione chiamata due volte** — batch rilanciato,
  retry, doppio click — che è protezione vera e sufficiente per il caso che
  capita. Ma è **un'altra cosa**, e crederla più larga di così vuol dire sentirsi
  coperti su uno scenario che resta scoperto.
  ⭐ **Lo scrittore estraneo non si ferma con un vincolo: si ferma con i
  permessi.** «In `magazzino.movimenti` non scrive nessuno se non attraverso la
  funzione» è una regola di `GRANT` e di `SECURITY DEFINER`, e va nel perimetro
  RLS/permessi che la §9 dichiara ancora assente.
* ⛔ **Non è un sostituto della macchina a stati**: che un DDT vada in `EMESSO`
  una volta sola resta compito del guard di transizione.

### Quel che resta da fissare, ed è piccolo

* il **nome** e il vocabolario del verbo (`operazione_verbo`): CHECK a valori
  chiusi, oppure lookup — la seconda se i verbi dovranno portare attributi;
* lo **scope dell'unicità**: **globale**, e va scritto come **dipendenza, non
  come preferenza**. ⭐ È globale *perché la terna contiene già la sorgente*,
  quindi il magazzino non aggiunge identità. ⚠️ Il giorno in cui una chiave non
  contenesse più la sorgente, l'unicità globale diventerebbe **sbagliata in
  silenzio** — quindi la ragione va nel `COMMENT`, non lasciata al lettore;
* ⭐ **la grammatica dei prefissi non è più un problema aperto**, ed è il
  guadagno della forma A: se l'identità sta sulle colonne, non c'è nessuna
  stringa da comporre e **nessun quinto vocabolario parallelo** da tenere
  allineato. ⚠️ Nella forma B invece il prefisso deve venire dal
  `codice_interno` di `config.sorgenti` — mai da un elenco scritto a mano
  accanto: è la trappola in cui il gemello acquisto è appena caduto con gli
  «ambiti», quattro assi diversi con lo stesso nome.

---

## 9. Che cosa NON è di questo brief

Concordato con Tid: qui c'è **solo l'aggancio al documento di origine**. Resta
fuori, per l'**analisi successiva** su «cosa serve / cosa manca a magazzino»:

- il rapporto fra `causali.segno` e il segno di `movimenti.qta` — ⚠️ già
  annotato come aperto nella mappa: `vw_giacenza` somma **senza guardare il
  segno della causale**. ⛔ **Fuori da questo brief ma non dopo di esso**: è il
  **passo 1** di §8-ter, e va chiuso prima della prima riga;
- valorizzazione e costo medio (`costo_medio`, `vw_costo_medio*`,
  `impatto_valorizzazione` sulle causali);
- lotti, seriali, ubicazioni e `reservations` come impianto di disponibilità;
- il perimetro emittente / RLS su `magazzino`, oggi assente;
- la copertura pgTAP: il dominio ha **un solo file**
  (`test-movimenti-vincoli-v1.sql`, nato il 21-08) e la sorgente polimorfa non è
  presidiata da nulla.

---

## 10. Perimetro e regole del cantiere

- ⛔ **Niente è stato applicato**, e niente va applicato prima che D-1 → D-8
  abbiano una risposta: **cambiare il modello dopo** costerebbe più che deciderlo
  adesso, ed è l'unico momento in cui non c'è una riga da bonificare.
- **Lato BE/FE non si chiede nulla in questa fase**: `backend/apps/magazzino`
  segue il dominio, non lo precede.
- ⭐ **Il vantaggio da non sprecare**: tutte le tabelle operative di `magazzino`
  sono a **zero righe**. Non è un argomento per fare o non fare qualcosa — è la
  ragione per cui questo cantiere può permettersi di **cambiare forma** invece di
  aggiungere strati compatibili.

---

## 11. Riferimenti

- ⭐ **Il brief gemello, lato `vendite`** (2026-09-01): dove il ciclo si può
  fermare, perché non è la commessa, e le dimensioni che al ciclo di vendita
  mancano comunque —
  [analisi-db-commessa-e-produzione-predisposizione.md](analisi-db-commessa-e-produzione-predisposizione.md).
  ⚠️ La sua §7 è la **gemella della D-5** qui sotto e va decisa insieme.
- Convenzione della sorgente polimorfa:
  [sorgente-polimorfa.md](../../guide/sorgente-polimorfa.md)
- Il precedente in cui il guard esisteva e non era agganciato:
  [brief-db-guard-sorgente-polimorfa.md](../work-done/brief-db-guard-sorgente-polimorfa.md)
  e la bonifica dei test che ne seguì,
  [brief-db-bonifica-pgtap-sorgente-polimorfa.md](../work-done/brief-db-bonifica-pgtap-sorgente-polimorfa.md)
- Stato del dominio nella mappa: [mappa-concentrica.md](../../mappa-concentrica.md)
  § Anello 3
