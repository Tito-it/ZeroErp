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
> vero: ogni voce qui dentro è agganciata a una delle D-1 → D-9. Il piano
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

📌 **`reservations` è decisa come `magazzino.movimenti_attesi`** dal 2026-09-02
(generica sui due versi, gemella del ledger): la decisione e le sue ragioni stanno
in [analisi-db-magazzino-carico-e-scarico §7-bis](analisi-db-magazzino-carico-e-scarico.md). ⚠️ In questo documento
resta il nome di oggi, perché qui si descrive la struttura **esistente** — ma il
punto della D-1 vale identico sotto il nome nuovo.

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

📌 **Il vocabolario delle causali per intero** — tutte e dieci, con segno,
valorizzazione e ambito, più le due che **mancano** (il versamento del prodotto
finito e lo scarico per reso a fornitore) — sta in
[analisi-db-magazzino-carico-e-scarico §2 e §3](analisi-db-magazzino-carico-e-scarico.md). Qui restano le sole due
causali `ODL_*`, perché servono all'argomento di questa sezione: che la produzione
era stata **nominata** e l'oggetto a cui punta non esiste.

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
| **D-4** | **`uq_mag_movimenti_docref`: che cosa deve vincolare davvero?** Le tre forme sono: toglierlo, renderlo `NULLS NOT DISTINCT` con dentro `causale_id` o `transfer_uid`, oppure spostare l'unicità su una **chiave dell'operazione**. ⭐ La terza è scritta per intero — con le due condizioni senza cui non funziona — in [analisi-db-magazzino-carico-e-scarico §6](analisi-db-magazzino-carico-e-scarico.md). ⚠️ *Fino al 2026-09-02 questo puntatore diceva «§8-quater», sezione che nel frattempo è stata traslocata: era un riferimento morto* | ⛔ oggi il vincolo dice due cose opposte a seconda di un NULL: qualunque scelta è meglio, ma va scelta. ⚠️ E toglierlo porta via anche una protezione buona non dichiarata (il doppio scarico): la sostituzione si decide **insieme** alla rimozione |
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

## 8-ter. L'ordine di costruzione e la regola anti-doppio — **traslocati**

📌 **Spostati il 2026-09-02 in [analisi-db-magazzino-carico-e-scarico.md](analisi-db-magazzino-carico-e-scarico.md)**,
insieme al resto di ciò che riguarda **come si scrive un movimento**.

* la sequenza in cui conviene costruire i carichi e gli scarichi (inventario →
  scarico da bolla → acquisti → produzione) è ora la sua **§8**;
* la regola anti-doppio — l'identità di un movimento, cioè la risposta alla
  **D-4** di questo documento — è la sua **§6**.

⭐ **Il motivo del trasloco**: quel ragionamento non era di questo documento. Qui
si decide **come un movimento dichiara la propria origine** (D-1 → D-9); là si
descrive **come il movimento si scrive**. Erano due argomenti in un documento
solo, e il secondo non si ritrovava perché nessun titolo lo nominava.

⚠️ **Le due cose si leggono insieme**: la D-4 vive qui, la sua risposta là.

---

## 9. Che cosa NON è di questo brief

Concordato con Tid: qui c'è **solo l'aggancio al documento di origine**. Resta
fuori, per l'**analisi successiva** su «cosa serve / cosa manca a magazzino»:

📌 **Tutto ciò che segue ha trovato una sede il 2026-09-02**, ed è
[analisi-db-magazzino-carico-e-scarico.md](analisi-db-magazzino-carico-e-scarico.md) — che le raccoglie e dichiara,
nella sua §9, quali sono ancora da scrivere:

- il rapporto fra `causali.segno` e il segno di `movimenti.qta` — ✅ **deciso il
  2026-09-02** ([là §4](analisi-db-magazzino-carico-e-scarico.md)): **il verso sta nella quantità**, la causale lo
  dichiara e lo valida. ⚠️ Ne discende un guard nuovo su `movimenti`, e che
  `vw_giacenza` **è corretta** com'è — chi la vedesse incompleta e le aggiungesse
  il join alle causali **raddoppierebbe il segno**;
- valorizzazione e costo medio (là §7 e M-4);
- lotti, seriali, ubicazioni e `reservations` come impianto di disponibilità
  (M-3, M-5);
- il perimetro emittente / RLS su `magazzino`, oggi assente (M-6);
- la copertura pgTAP: il dominio ha **un solo file**
  (`test-movimenti-vincoli-v1.sql`, nato il 21-08) e la sorgente polimorfa non è
  presidiata da nulla (M-7).

⛔ **Restano fuori da questo documento** — non da quello: qui si decide solo
l'aggancio al documento di origine.

---

## 10. Perimetro e regole del cantiere

- ⛔ **Niente è stato applicato**, e niente va applicato prima che D-1 → D-9
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
