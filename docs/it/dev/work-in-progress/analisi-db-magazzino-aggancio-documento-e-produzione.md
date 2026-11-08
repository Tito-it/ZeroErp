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
> ⚠️ **Superata per D-1, D-2, D-3, D-7 e D-9 (2026-11-08).** La provenienza del magazzino è passata al modello
> unico in `brief-db-sorgente-documento-e-riga` (lotto M): il registro e le testate dicono il documento con
> `sorgente_id` o `sorgente_uid` e la riga in `sorgente_riga`, col `CHECK` di forma `…_sorgente_forma` e il guard
> unico `script.trgfn_guard_sorgente`; il «modello A», il guard tipizzato e i tipi di foglia (`INVENTARIO_RIGA`,
> `RETTIFICA_RIGA`, `TRASFERIMENTO_RIGA`, `RESO_VENDITA_RIGA` e le righe di vendita) sono ritirati; gli UNIQUE
> parziali vecchi delle quattro testate sono sostituiti. Il meccanismo è nella guida
> [Sorgente polimorfa](../../guide/sorgente-polimorfa.md). Resta viva la sola **D-5** (l'ODL), che quando si apre
> segue il modello unico.
>
> **Stato al 2026-09-26:** 🟡 **otto decisioni su nove PRESE e REALIZZATE; resta
> aperta la sola D-5** (l'ODL sorgente o anello), che serve solo alla produzione.
> ⚠️ Le §0 → §7 sono la **fotografia del 2026-09-01** e descrivono una struttura
> che **non esiste più**: il ragionamento resta valido, lo stato no. Lo stato di
> oggi, decisione per decisione, è nella tabella «Realizzato» in coda a §8.
>
> * ✅ **Lotto 1** ([brief](../work-done/brief-db-magazzino-lotto-1-terreno-vuoto.md),
>   chiuso il 15-09, PR #1593): D-1, D-2, D-3, D-4, D-6, D-7, D-8;
> * ✅ **Lotto 2** ([brief](../work-done/brief-db-magazzino-lotto-2-motore.md),
>   DB applicato il 18-09, archiviato il 24-09): D-9 (vista degli orfani), la
>   primitiva `fn_scrivi_movimento` come unica porta sul ledger, e il **rinvio**
>   di `causali.sorgente_tipo_id` (D-L2-i, vedi D-8);
> * ✅ **Verbi con permesso** ([brief](../work-done/brief-db-magazzino-verbi-con-permesso.md),
>   24/25-09): l'app scrive il ledger **solo** da `fn_posta_inventario` /
>   `fn_posta_rettifica`, sotto l'azione `registra_magazzino`.
>
> *Stato precedente, per la storia:* ✅ **2026-09-14 — otto delle nove decisioni
> sono PRESE da Tid** (D-1, D-2, D-3, D-4, D-6, D-7, D-8, D-9; resta aperta la
> sola **D-5**, rinviata di proposito con la §7 dell'analisi commessa). ⚠️ *Fino
> al 26-09 qui c'era scritto «sette»: l'elenco fra parentesi ne ha sempre avute
> otto.* Il verbale è in **§8-quater**.
>
> 📌 **Declassato ad analisi il 2026-09-01** (decisione di Tid), e rinominato da
> `brief-db-…` a `analisi-db-…`: ⭐ è la stessa distinzione già usata dal cantiere
> numerazione, dove l'**analisi** dice *perché* e il **brief** dice *cosa si fa*.
> ⛔ **Di questo documento non esce nessuna modifica certa**, ed è il suo esito
> vero: ogni voce qui dentro è agganciata a una delle D-1 → D-9. Il piano
> operativo delle sole modifiche **certe** vive in
> [brief-db-modifiche-certe-ciclo-vendita-e-articolo.md](../work-done/brief-db-modifiche-certe-ciclo-vendita-e-articolo.md),
> e sta quasi tutto su `vendite` e `catalogo`.
>
> ⚠️ **Perimetro di questa analisi:** solo l'**aggancio al documento di origine** e
> ciò che serve perché regga anche per la produzione. Il resto di *«cosa manca a
> magazzino»* — valorizzazione, giacenza, ubicazioni, lotti/seriali, il rapporto
> fra `causali.segno` e `movimenti.qta` — è l'**analisi successiva**, concordata
> con Tid nella stessa sessione. Vedi §9.

---

## 0. In due parole, senza tecnicismi

> ⚠️ **Fotografia del 2026-09-01, superata dal Lotto 1** (15-09): il «foglietto»
> di testo libero non esiste più, il ledger punta al catalogo delle sorgenti. Si
> legge come il **perché** delle decisioni di §8; lo stato di oggi è in §8,
> tabella «Realizzato».

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

> ⚠️ **§2 → §7 descrivono la struttura del 2026-09-01**, prima del Lotto 1: le
> `doc_*`, `uq_mag_movimenti_docref`, le dieci causali con `ambito_causale` e i
> flag, il guard tipizzato montato su nessuna tabella di `magazzino`, `config.sorgenti`
> a dieci righe. Oggi nulla di questo è più vero (§8, «Realizzato»). ⚠️ E
> `uq_mag_movimenti_docref` esisteva **solo su dev**: su un database da zero il
> suo changeSet era `MARK_RAN` (Lotto 1, registro del 15-09 sera).

| Modello | Come è fatto | Chi lo usa in `magazzino` |
| --- | --- | --- |
| **Sorgente polimorfa a catalogo** | `sorgente_tipo_id` → `config.sorgenti` (FK) + la chiave del record puntato | `rettifiche`, `trasferimenti`, `inventari`, `eventi_assets` |
| **Riferimento testuale libero** | `doc_schema` + `doc_table` + `doc_id` + `doc_riga_id`, tutte stringhe/bigint **senza FK e senza catalogo** | ⛔ `movimenti` (il ledger) e `reservations` |

📌 **`reservations` è decisa come `magazzino.movimenti_attesi`** dal 2026-09-02 (✅ **rinominata** il 15-09, `20260915-06`)
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

> Sono qui perché il cantiere non parta assumendo la risposta. ✅ **Il
> 2026-09-14 sono state prese tutte tranne la D-5** — la colonna «Esito» dice
> come, e §8-quater dice perché.

| # | Decisione | Perché non la decide un piano | Esito (2026-09-14) |
| --- | --- | --- | --- |
| **D-1** | **Un modello solo o due?** `movimenti`/`reservations` passano alla sorgente a catalogo, oppure `doc_schema/doc_table/doc_id` resta ed è **il** modello del ledger — e allora sono le quattro testate a doversi allineare a lui. ⛔ Quello che non regge è **tenerli entrambi senza una regola** | è una scelta di architettura del dominio, e vale anche per `acquisti`, che ha lo stesso doppio | ✅ **CATALOGO.** `sorgente_tipo_id` + `sorgente_riga`/`sorgente_uid` su `movimenti` e `movimenti_attesi`; le tre `doc_*` **si tolgono**, non convivono |
| **D-2** | **Le quattro testate prendono `sorgente_riga`?** Se sì, diventano capaci di riferire le otto sorgenti `id` e il guard tipizzato ha finalmente dove agganciarsi. Se no, va scritto **quali sorgenti sono ammesse** e presidiato | dipende da D-1 | ✅ **SÌ**, nel Lotto 1 (terreno vuoto). ⚠️ Emerso rileggendo il DDL il 14-09: `rettifiche.sorgente_tipo_id` **non ha la FK** verso `config.sorgenti` (le altre tre ce l'hanno), e `trasferimenti` porta la coppia **due volte** — `sorgenti_tipo_id`/`sorgenti_uid` (refuso, con **due** FK, una chiamata `fk_mag_rettifiche_sorgenti_tipo`) accanto a `sorgente_tipo_id`/`sorgente_uid`. Si sanano nello stesso passo |
| **D-3** | **Si aggancia il guard tipizzato** alle tabelle del modello A, in `magazzino` e altrove? ⭐ Oggi non presidia niente: o trova i suoi consumatori o è codice morto | il roll-out tocca 15 tabelle: è un perimetro, non una riga | ✅ **SÌ, per le sei di `magazzino`** (quattro testate + ledger + attesi). ⛔ Le altre nove restano un cantiere `dbops`, non di questo brief |
| **D-4** | **`uq_mag_movimenti_docref`: che cosa deve vincolare davvero?** Le tre forme sono: toglierlo, renderlo `NULLS NOT DISTINCT` con dentro `causale_id` o `transfer_uid`, oppure spostare l'unicità su una **chiave dell'operazione**. ⭐ La terza è scritta per intero — con le due condizioni senza cui non funziona — in [analisi-db-magazzino-carico-e-scarico §6](analisi-db-magazzino-carico-e-scarico.md). ⚠️ *Fino al 2026-09-02 questo puntatore diceva «§8-quater», sezione che nel frattempo è stata traslocata: era un riferimento morto* | ⛔ oggi il vincolo dice due cose opposte a seconda di un NULL: qualunque scelta è meglio, ma va scelta. ⚠️ E toglierlo porta via anche una protezione buona non dichiarata (il doppio scarico): la sostituzione si decide **insieme** alla rimozione | ✅ **La terza forma, com'è scritta in §6 di carico/scarico**, col discriminante fisico. Il «progressivo di occorrenza» **non serve**: un'operazione parziale è un record per tranche (condizione 1 di quella sezione) — va nel `COMMENT` del vincolo, non in una colonna. ⚠️ Il brief propone un affinamento — **il verbo è la causale** — da confermare lì (D-L1-c) |
| **D-5** | **L'ODL è una sorgente o un anello?** (§7). Da questa discende se `config.sorgenti` cresce di 1 riga o se nasce uno schema `produzione` | è la decisione di dominio, e la prende Tid | ⏸️ **APERTA di proposito**: serve solo al passo 5 (produzione) e si decide con la §7 dell'analisi commessa. Nessun lotto 1-4 la presuppone |
| **D-6** | **Il movimento senza documento è ammesso?** Se sì, `doc_*` smette di essere NOT NULL e serve una regola su chi può ometterlo; se no, ogni movimento deve avere un documento **che esiste**, e allora serve il catalogo | ⚠️ oggi la risposta è «obbligatorio, ma non verificato»: il peggiore dei tre mondi | ✅ **NO: ogni movimento ha una sorgente, `NOT NULL`** (sul ledger; su `movimenti_attesi` resta nullable, perché il blocco manuale non ha un documento). Ragione in §8-quater: **nessuno scriverebbe senza** — la correzione a mano è una `rettifica`, che è un documento. ⚠️ Rovescia la riga «resta tutto nullable» di carico/scarico §6, corretta lo stesso giorno |
| **D-7** | **Acquisti entra nel catalogo delle sorgenti?** `CARICO_ACQ` è la prima causale del seed e il DDT di acquisto non è una sorgente registrata | tocca `acquisti`, che è un altro dominio fermo | ✅ **SÌ, ed è più largo**: il catalogo registra le **operazioni** di magazzino (`INVENTARIO_RIGA`, `RETTIFICA_RIGA`, `TRASFERIMENTO_RIGA`, `EVENTO_ASSET`, `RESO_VENDITA_RIGA` nel Lotto 1; il ricevimento nel Lotto 4; `ODL_*` nel 5), con uno `scope` proprio. 🔴 E le cinque `*_RIGA` di vendite che §6 di carico/scarico dava «già a catalogo» **esistono solo sul DB di sviluppo** (§8-quater): entrano nel CSV nel Lotto 1 |
| **D-8** | **`causali.ambito_causale_id` si valorizza** (e allora l'ambito serve a qualcosa) **o l'ambito si ritira?** ⛔ Oggi la colonna è **vuota in tutte e dieci le causali**: il vocabolario dei sei ambiti esiste e non è collegato a niente | ⛔ un vocabolario collegato a zero righe è debito che **sembra** struttura — e chi legge lo scambia per un pezzo funzionante (§8-ter) | ✅ **SI RITIRA**, insieme ai tre flag morti (`richiede_odl`, `contabilizza_cdc`, `abilita_billing`). La primitiva è guidata da due cataloghi e l'ambito non è fra i suoi controlli; ed è il quinto asse chiamato «ambito» (analisi acquisti §7). Se un giorno servirà «questa causale accetta solo questa sorgente», la forma è un `causali.sorgente_tipo_id` 1:1, non un ambito |
| **D-9** | **I due presidi che compensano il polimorfismo** (§8-bis): il tipo di sorgente vincolato al catalogo, e una **vista dei riferimenti orfani che deve restare vuota**. ⚠️ Sul ledger **non sono aggiungibili da soli**: presuppongono D-1 | il pattern è già di casa e si riusa; ma la parte sul ledger *è* la decisione D-1, non un'aggiunta sopra | ✅ **SÌ**, discende da D-1: FK + guard tipizzato sul ledger (Lotto 1); la vista degli orfani, generica su `config.sorgenti`, nel Lotto 2 con i suoi pgTAP |

### ✅ Realizzato — stato al 2026-09-26

> ⚠️ Fotografia del 2026-09-26: per D-1, D-2, D-3, D-7 e D-9 lo stato di oggi è quello dell'avviso in testa.

> Verificato sulla doc auto-generata (`docs/it/dbzero/magazzino/`, `dbzero/dbops/`),
> sul CSV di `config.sorgenti` e sui brief chiusi. Sono letture di **struttura**.

| # | Che cosa esiste oggi | Dove | Scostamento dalla decisione |
| --- | --- | --- | --- |
| **D-1** | `movimenti` e `movimenti_attesi` portano `sorgente_tipo_id` (FK a `config.sorgenti`) + `sorgente_riga`/`sorgente_uid` con CHECK di chiave; le `doc_*` **non esistono più**. `reservations` è rinominata `movimenti_attesi` | `20260915-05`, `-06`, `-07` | ➕ le `doc_*` sono state tolte **anche da `eventi_assets`** (Lotto 1 §4.7, `20260915-11`), che D-1 non nominava |
| **D-2** | le quattro testate hanno `sorgente_riga` + `chk_mag_<t>_sorgente_chiave`; `rettifiche` ha la sua FK; su `trasferimenti` resta la sola coppia `sorgente_*` | `20260915-11` | ⚠️ restano gli **UNIQUE parziali vecchi** su `(sorgente_tipo_id, sorgente_uid)` delle quattro testate (`uq_mag_rettifiche_source_fk`, `uq_mag_trasf_sorgente_fk`, `uq_mag_invetario_sorgente_fk`, `uq_mag_eventi_assets_sorgente_fk`): coprono il solo ramo `uid`, e nessuna decisione li nomina — **da decidere se servono** |
| **D-3** | `trgfn_guard_sorgente_polimorfa_tipizzata` montato sulle **sei** tabelle (`trg_<t>_a10_guard_sorgente_ins_upd`) | Lotto 1 | nessuno. Le altre nove tabelle del modello A restano un cantiere `dbops` |
| **D-4** | `uq_mag_movimenti_identita` su `(sorgente_tipo_id, sorgente_riga, sorgente_uid, causale_id, asset_id, lotto_id, ubicazione_id)` **`NULLS NOT DISTINCT`**, col `COMMENT` sull'operazione-per-tranche; `uq_mag_movimenti_docref` **droppato** (e `uq_mag_reservations_docref`) | `20260915-05`, `-07` | ✅ **D-L1-c confermata da Tid il 15-09: il verbo è la causale**, nessuna colonna `operazione_verbo`. ➕ `uq_mag_movimenti_storno_di` e `E_MAG_MOVIMENTO_GIA_REGISTRATO` nella primitiva (`20260918-18`) |
| **D-5** | — | — | ⏸️ **ancora aperta**, con la §7 dell'analisi commessa |
| **D-6** | `movimenti.sorgente_tipo_id` **NOT NULL**; nullable su `movimenti_attesi` e `rettifiche`; `lotto_id`/`asset_id` propagati alle righe delle testate | Lotto 1 | ➕ «lo storno eredita la sorgente» è **fatto rispettare dalla primitiva** (`E_MAG_STORNO_INCOERENTE`, `20260918-18`); la utility di storno è del Lotto 3. ⚠️ La riga «trasferimento → `trasferimenti_righe`» della tabella di §8-quater è **superata da D-L2-g**: `magazzino.trasferimenti` è il solo trasferimento **interno**, quello con trasporto è il DDT con causale `TRASFERIMENTO` e la sua sorgente è una riga di DDT (Lotto 3) |
| **D-7** | `config.sorgenti.csv` a **20 righe**: le cinque `*_RIGA` di vendite entrate (id 3-11), più `INVENTARIO_RIGA`, `RETTIFICA_RIGA`, `TRASFERIMENTO_RIGA`, `EVENTO_ASSET` con scope **`MAGAZZINO`** (esteso in `20260915-01`) e `RESO_VENDITA_RIGA` | `80_data/sql/config/sorgenti.csv` | ⚠️ `RESO_VENDITA_RIGA` (id 16) ha scope **`ROW_VALIDATOR`**, non `MAGAZZINO`. ➕ Le cinque `*_RIGA` su dev erano **archiviate** (`attivo = f`), non solo fuori CSV: rientrate **attive** per D-L1-f. Nessuna sorgente di acquisti né ODL, come previsto (Lotti 4 e 5) |
| **D-8** | `ambito_causale` droppata con `richiede_odl`, `contabilizza_cdc`, `abilita_billing` | `20260915-02`, `-03` | ⛔ **`causali.sorgente_tipo_id` 1:1 NON è stata fatta**: D-L2-i (Tid, 17-09) la **rinvia** e ne **smentisce la forma** — `RETT_POS` nasce da due sorgenti (`INVENTARIO_RIGA`, `RETTIFICA_RIGA`), quindi il rapporto è 1:N e servirà una tabella ponte, al primo scrittore che riceve la causale da fuori |
| **D-9** | `dbops.fn_sorgenti_orfane()`, `fn_sorgenti_orfane_perimetro()`, `dbops.vw_sorgenti_orfane`, iscritta in `presidi.csv` (natura `ZERO`, settimanale); pgTAP `dbops/test-sorgenti-orfane-v1.sql` | `20260918-25`, `-27` | nessuno: il perimetro si deriva dalle FK verso `config.sorgenti`, quindi copre anche le tabelle future |

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

## 8-quater. ✅ Le decisioni del 2026-09-14 — il verbale

> Prese da Tid il 2026-09-14 in una seduta sola, su proposta motivata, dopo
> aver constatato che carico/scarico aveva **tutte le M chiuse** e che ciò che
> bloccava la prima riga erano **queste** D, che quel documento presuppone
> senza possederle. La D-5 è rimasta aperta **per scelta**, non per dimenticanza.

### D-1 — catalogo, e le `doc_*` si tolgono

Tre cose già decise altrove **richiedono** il catalogo, e nessuna funziona col
testo libero: l'identità del movimento di carico/scarico §6 (sorgente,
chiave e verbo), il conteggio di M-3 *«guidato da `config.sorgenti`»*, e la
vista degli orfani di D-9, che si scrive una volta sola perché `target_table`
e `key_selector` stanno a catalogo. Il testo libero non ha un argomento a
favore oltre a «c'è già». ⛔ E non convivono: le tre `doc_*` **cadono** — due
modelli sulla stessa tabella sono esattamente ciò che questo documento
contesta dal §2.

### D-6 — no: ogni movimento ha una sorgente, ed è `NOT NULL`

> ⚠️ È la decisione che **rovescia una riga scritta** (carico/scarico §6,
> *«perché resta tutto nullable, e non è pigrizia»*), e per questo va motivata
> per intero.

**L'argomento è una domanda sola: chi scriverebbe davvero un movimento senza
sorgente?** Nessuno. Ogni modo di far entrare o uscire merce è un'operazione,
e ogni operazione **è già un record**:

| Chi muove la merce | Il record che è la sorgente |
| --- | --- |
| inventario (iniziale o periodico) | `inventari_righe` |
| ⭐ **correzione a mano** | `rettifiche_righe` — esiste apposta, con `qta_delta`, `motivo`, stato `DRAFT → CONFIRM → POSTED → CANCEL` |
| trasferimento | `trasferimenti_righe` — ⚠️ *dal 17-09 (D-L2-g) solo il trasferimento **interno**; quello con trasporto è il DDT con causale `TRASFERIMENTO`, sorgente una riga di DDT (Lotto 3)* |
| installazione / rientro di un asset | `eventi_assets` |
| bolla di vendita, reso del cliente | `ddt_righe`, `resi_righe` |
| ricevimento, reso al fornitore | il record di ricevimento (Lotto 4) |
| prelievo / versamento di produzione | il record dell'ODL (Lotto 5) |
| storno | eredita la sorgente del movimento che corregge |

⭐ **Il dubbio di Tid** — *«nel caso si vogliano caricare delle righe di
rettifica al magazzino, dobbiamo passare per qualche procedura che ne
specifichi la provenienza; comunque deve essere permessa la rettifica»* — ha la
risposta nella seconda riga: la rettifica **resta possibile ed è lei stessa la
provenienza**. L'operatore compila la rettifica (magazzino, articolo, delta,
motivo — dati che dovrebbe compilare comunque), la porta a `POSTED`, e la
transizione chiama la primitiva con `RETTIFICA_RIGA:{id}`. Non «specifica la
provenienza»: la conosce l'operazione, perché è il proprio record.

**La libertà che si voleva tenere vive un livello più su**, dov'è giusta:
`rettifiche.sorgente_tipo_id` — *da dove nasce la rettifica* (un inventario, o
niente) — resta **nullable**. Obbligatoria è la provenienza del **movimento**,
non quella del documento.

**L'argomento del nullable era contro il testo libero**, e sotto D-1 non vale
più: *«chi non ha una sorgente se la inventa»* era vero con tre stringhe senza
FK; con FK a catalogo, guard tipizzato e vista degli orfani, una sorgente non
si inventa. ⛔ E un ramo `NULL` che nessuno dovrebbe percorrere, lasciato
aperto, è la classe «esiste e non è armata» che questi documenti inseguono.

**Che cosa si guadagna, e non è poco:**

- il `UNIQUE` di carico/scarico §6 diventa **pieno**, non parziale ⇒ il
  doppio storno è impedito **ovunque**, e cade il caveat di §7-quinquies («sui
  movimenti senza sorgente lo impedisce solo la funzione»);
- la rettifica-documento porta **il perché** (`motivo`, data, autore, stato):
  esattamente ciò che §7-quinquies rimprovera all'annullo;
- la rettifica ha `magazzino_id` ⇒ il perimetro di M-6 la copre da sé.

⚠️ **Ne discende un pezzo che carico/scarico non trattava**: `rettifiche_righe`,
`inventari_righe` e `trasferimenti_righe` portano `lotto`/`seriale` come
**testo**. Se il movimento nasce da quelle righe, la riga deve avere
`lotto_id`/`asset_id` da passare alla primitiva — M-5 va **propagata alle righe
delle testate**, nello stesso lotto. La rettifica è il caso che lo rende
obbligatorio, non opzionale.

⚠️ Su **`movimenti_attesi`** la sorgente resta invece **nullable**: il blocco
manuale («tieni da parte 10 pezzi per Rossi») non ha un documento per
definizione — è l'unica cosa che quella tabella conserva che non si deriva.

### D-4 — la terza forma, e il progressivo non serve

Adottata l'identità di carico/scarico §6 così com'è scritta, discriminante
fisico compreso. Il «caso scoperto» (stesso prelievo in due riprese senza
niente che le distingua) **non esiste** se vale la condizione 1 di quella
sezione — *la chiave la compone l'operazione, non il documento*: un'operazione
parziale è **un record per tranche**, e due riprese sono due record. Va nel
`COMMENT` del vincolo, perché è la frase che fra sei mesi qualcuno cercherà.

### D-7 — sì, e il catalogo registra le OPERAZIONI

Non «acquisti entra»: **entrano le operazioni di magazzino**, perché sotto D-6
ogni movimento nomina il proprio record e il catalogo deve conoscerlo. Nel
Lotto 1: `INVENTARIO_RIGA`, `RETTIFICA_RIGA`, `TRASFERIMENTO_RIGA`,
`EVENTO_ASSET`, `RESO_VENDITA_RIGA`; il ricevimento col Lotto 4; `ODL_*` col 5.
Con uno `scope` proprio (`chk_sorgenti_scope` è un elenco chiuso: si estende
come per `REVERSE_FLOW`).

🔴 **E un fatto di struttura trovato scrivendo il verbale**: le cinque sorgenti
di riga di vendite — `PREVENTIVO_RIGA`, `CONTRATTO_RIGA`, `ORDINE_VENDITA_RIGA`,
`DDT_VENDITA_RIGA`, `FATTURA_RIGA` (id 3, 5, 7, 9, 11) — **non sono nel CSV**
`80_data/sql/config/sorgenti.csv` (10 righe; il DB di sviluppo ne ha 15).
Registrato nell'intestazione di `20260820-03` e mai sanato. Su un database
ricostruito da zero **non esistono**: lo scarico da DDT del Lotto 3 sarebbe
verde su dev e rosso in CI. ⇒ Entrano nel CSV nel Lotto 1, con i loro id.

### D-8 — l'ambito si ritira, con i tre flag morti

La primitiva di M-2 è guidata da **due** cataloghi — la causale (verso,
stock negativo) e l'articolo (lotto, seriale, gestito a magazzino) — e
`ambito_causale_id` non è in quella tabella: **non ha un consumatore**, e
l'analisi acquisti §7 ha già contato **quattro** assi diversi chiamati
«ambito» nel progetto. Stessa sorte per `richiede_odl`, `contabilizza_cdc`
(punta a un centro di costo che non esiste) e `abilita_billing`: dichiarati,
seminati, letti da nessuno.

⭐ **Se un giorno servisse** la regola *«questa causale accetta solo questa
sorgente»* — `SCARICO_VEN` solo da `DDT_VENDITA_RIGA` — la forma giusta è un
`causali.sorgente_tipo_id` nullable, 1:1, che la primitiva legge subito. Non
un ambito, che è più grosso di ciò che il controllo chiede (`ODL_USCITA_MAT` e
`ODL_ENTRATA_MAT` sono entrambe `ODL` e vanno da sorgenti diverse). Candidata
al Lotto 2, quando la primitiva esiste.

⛔ **Esito (Lotto 2, D-L2-i, Tid 17-09): rinviata, e la forma 1:1 è smentita.**
`RETT_POS` nasce da **due** sorgenti (`INVENTARIO_RIGA` e `RETTIFICA_RIGA`): il
rapporto è 1:N, quindi servirà una tabella ponte causale ↔ sorgente, non una
colonna. Si scrive quando arriva il primo scrittore che riceve la causale da
fuori invece di ricavarla da sé.

### D-2, D-3, D-9 — discendono (D-2 e D-3 nel Lotto 1, D-9 nel Lotto 2)

Le quattro testate prendono `sorgente_riga` e il guard tipizzato si monta su
**sei** tabelle di `magazzino`; la vista degli orfani nasce nel Lotto 2 col
suo pgTAP. ⚠️ Rileggendo il DDL per scriverlo: `rettifiche.sorgente_tipo_id`
è **senza FK** (le altre tre l'hanno), e `trasferimenti` porta la coppia
**due volte** (`sorgenti_*` refuso con due FK, più `sorgente_*`). Si sanano
nello stesso passo: sono la stessa classe del §4 — un presidio che sembra
esserci.

---

## 9. Che cosa NON è di questo brief

Concordato con Tid: qui c'è **solo l'aggancio al documento di origine**. Resta
fuori, per l'**analisi successiva** su «cosa serve / cosa manca a magazzino»:

✅ **Al 2026-09-26 tutte le voci sotto sono decise e quasi tutte costruite**
(Lotti 1 e 2; dettaglio in carico/scarico §9). In particolare: il guard del verso
esiste, il perimetro RLS di `magazzino` è acceso dal 15-09 (`20260915-16`), i
pgTAP del dominio sono una ventina di file, e la sorgente polimorfa è presidiata
dal guard tipizzato su sei tabelle e dalla vista degli orfani. Le righe sotto
restano come erano scritte il 01-09.

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

> ✅ **Al 2026-09-26 i tre punti sotto sono storia**: il Lotto 1 è applicato dal
> 15-09 e il Lotto 2 dal 18-09; il lato BE/FE è arrivato (richiesta D-L1-g del
> Lotto 1, brief 2-bis e piano BE/FE del Lotto 2, chiusi il 23 e il 25-09); e le
> tabelle operative non sono più vuote su dev. Restano come la regola con cui il
> cantiere è partito.

- ⛔ **Niente è stato applicato**, e niente va applicato prima che D-1 → D-9
  abbiano una risposta: **cambiare il modello dopo** costerebbe più che deciderlo
  adesso, ed è l'unico momento in cui non c'è una riga da bonificare.
  ✅ *Dal 2026-09-14 la risposta c'è per tutte tranne la D-5, che nessun lotto
  prima della produzione presuppone: il cantiere può partire* (§8-quater).
- **Lato BE/FE non si chiede nulla in questa fase**: `backend/apps/magazzino`
  segue il dominio, non lo precede.
- ⭐ **Il vantaggio da non sprecare**: tutte le tabelle operative di `magazzino`
  sono a **zero righe** (fatto datato 2026-09-01). Non è un argomento per fare o non fare qualcosa — è la
  ragione per cui questo cantiere può permettersi di **cambiare forma** invece di
  aggiungere strati compatibili.

---

## 11. Riferimenti

- ⭐ **Il brief gemello, lato `vendite`** (2026-09-01): dove il ciclo si può
  fermare, perché non è la commessa, e le dimensioni che al ciclo di vendita
  mancano comunque —
  [analisi-db-commessa-e-produzione-predisposizione.md](analisi-db-commessa-e-produzione-predisposizione.md).
  ⚠️ La sua §7 è la **gemella della D-5** (§8) e va decisa insieme.
- Convenzione della sorgente polimorfa:
  [sorgente-polimorfa.md](../../guide/sorgente-polimorfa.md)
- Il precedente in cui il guard esisteva e non era agganciato:
  [brief-db-guard-sorgente-polimorfa.md](../work-done/brief-db-guard-sorgente-polimorfa.md)
  e la bonifica dei test che ne seguì,
  [brief-db-bonifica-pgtap-sorgente-polimorfa.md](../work-done/brief-db-bonifica-pgtap-sorgente-polimorfa.md)
- Stato del dominio nella mappa: [mappa-concentrica.md](../../mappa-concentrica.md)
  § Anello 3
- Dove le decisioni sono diventate DDL:
  [Lotto 1](../work-done/brief-db-magazzino-lotto-1-terreno-vuoto.md) (D-1 → D-4,
  D-6 → D-8), [Lotto 2](../work-done/brief-db-magazzino-lotto-2-motore.md) (D-9,
  D-L2-g, D-L2-i), [verbi con permesso](../work-done/brief-db-magazzino-verbi-con-permesso.md)
  (la porta del ledger)

---

## 12. Registro delle revisioni

| Data | Cosa |
| --- | --- |
| 2026-09-01 | Prima stesura, declassata ad analisi lo stesso giorno. D-1 → D-9 poste, nessuna presa |
| 2026-09-02 | §8-ter traslocato in carico/scarico; D-4 punta alla sua risposta (§6 di là); `reservations` → `movimenti_attesi` annotato in §2 |
| 2026-09-14 | ✅ **Otto decisioni prese da Tid in una seduta** *(fino al 26-09 diceva «sette»)* (verbale in **§8-quater**, esito riga per riga in §8): **D-1** catalogo e `doc_*` via; **D-6** sorgente **obbligatoria** sul ledger — rovescia la riga «resta tutto nullable» di carico/scarico §6, perché ogni scrittore è un'operazione con un record (la correzione a mano è una `rettifica`) e l'argomento del nullable valeva contro il testo libero; **D-4** la terza forma senza progressivo; **D-7** il catalogo registra le **operazioni**, e 🔴 le cinque `*_RIGA` di vendite esistono **solo sul DB di sviluppo** (id 3-11, fuori dal CSV: verde su dev, rosso in CI); **D-8** ambito e tre flag morti **ritirati**; D-2/D-3/D-9 discendono (D-2/D-3 nel Lotto 1, D-9 nel Lotto 2) — dove si sanano anche `rettifiche` **senza FK** sulla sorgente e la coppia `sorgenti_*` **duplicata** su `trasferimenti`. ⏸️ **D-5 resta aperta di proposito**. Primo pezzo eseguibile: `brief-db-magazzino-lotto-1-terreno-vuoto.md` |
| 2026-09-26 | 🟡 **Riallineamento allo stato di sviluppo** (verifica su doc auto-generata, CSV e brief chiusi). Intestazione riscritta; aggiunta in §8 la tabella **«Realizzato»**, decisione per decisione con i changeSet; note di **fotografia superata** su §0 e §2 → §7, §9, §10. Corretti: «sette» decisioni → **otto** (l'elenco ne aveva sempre otto); D-9 nel **Lotto 2**, non nel 1. Registrati gli esiti che il documento non aveva: **D-L1-c** confermata (il verbo è la causale); le `*_RIGA` di vendite erano **archiviate** su dev e sono rientrate attive (D-L1-f); `RESO_VENDITA_RIGA` ha scope `ROW_VALIDATOR`, non `MAGAZZINO`; `causali.sorgente_tipo_id` 1:1 **rinviata e smentita** (D-L2-i, 1:N); il trasferimento con trasporto è il DDT `TRASFERIMENTO` (D-L2-g); lo storno eredita la sorgente **per guard** della primitiva. ⚠️ Emerso: sulle quattro testate restano gli **UNIQUE parziali** vecchi sul ramo `uid`, che nessuna decisione nomina. ⏸️ D-5 resta aperta |
