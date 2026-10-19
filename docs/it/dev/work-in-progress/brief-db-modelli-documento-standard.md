# Brief DB — I modelli di documento standard: un emittente nuovo emette dal primo giorno

## ⏭️ Chi riparte — aggiornato al 2026-10-19

**Riparte: Tid, che legge le risposte del team DB (§4.1) e dà il via allo sviluppo.**

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | **Tid** | ✅ D-1, D-2, D-3 come da proposta (2026-10-19) | §5 | — |
| 2 | **team DB** | ✅ Disegno della forma e risposte a Q-1 … Q-5 (2026-10-19) | §4.1 | 1 |
| 3 | **Tid** | Lettura del §4.1 e via allo sviluppo | §4.1 | 2 |
| 4 | **team DB** | ChangeSet, seed dei sei modelli, pgTAP | §4 | 3 |
| 5 | **Tid** | Apply su dbdev, pgTAP | — | 4 |
| 6 | **BE/FE** | La risoluzione a due livelli e la lista Modelli documento | §6 | 5 |
| 7 | **BE** | Il giro degli smoke su `dev.smoke` (DEVA emette con lo standard) | §7 | 6 |
| 8 | **Tid** | Archiviazione in `work-done/` | — | 7 |

**Decisioni aperte di Tid: nessuna di disegno; resta il via (§4.1).** Da committare: questo documento.

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-18. **A chi:** Tid (§5), poi il team DB;
> la §6 al BE/FE.
> **Origine:** il collaudo T-5 di [brief-be-utenti-di-sviluppo](brief-be-utenti-di-sviluppo.md)
> (§9). L'emittente di prova A, creato dal verbo di sviluppo, non emette nessun documento: non ha
> modelli. Proposta di Tid (2026-10-18): «la cosa migliorativa è fornire un set di modelli
> standard».
> **Stato:** 📝 proposta; nessun codice scritto.

## 1. Il caso

Un emittente fiscale nasce senza modelli di documento. Finché qualcuno non ne scrive uno per tipo
dalla UI (Configurazione → Modelli documento), ogni emissione si ferma con `E_DOCUMENTI_NOT_FOUND`
«Nessun template applicabile per la sorgente»: preventivo, offerta, contratto, ordine, DDT e
fattura.

Vale per ogni emittente nuovo: quello di un'installazione di produzione appena fatta, il secondo
emittente di un'azienda che ne aggiunge uno, gli emittenti di prova del verbo di sviluppo, un
database ricostruito da zero in CI.

## 2. Perché è un difetto del modello

**Un emittente è un'identità completa solo se può emettere.** I modelli non nascono con
l'emittente, e senza modelli l'emittente si può creare ma non usare. È uno stato che il modello
lascia nascere e che nessuna regola chiude.

⚠️ **Non solo i modelli** (fatto del 2026-10-18, smoke `push-termine-documento-commessa`):
l'emittente di prova A non ha nemmeno il **registro delle fatture**.
`vendite.fn_get_registro_id` solleva `E_CONFIG_MANCANTE` «registro non risolto per tipo_doc 1 e
natura 1» quando la commessa genera la fattura. È lo stesso difetto su un'altra configurazione: al
team DB chiediamo di censire che cosa serve a un emittente per emettere ogni documento (modelli,
registri, altro) e di dire, per ciascuna voce, se nasce con l'emittente o ha uno standard. Il
censimento si fa sulla struttura (funzioni di risoluzione, FK, guard), non sulle righe di dbdev.

➡️ **La voce «registri» ha la sua risposta** (team DB, 2026-10-18): è R-BE-14, in
[brief-db-processi-accensione-per-ambiente §6.14](../work-done/brief-db-processi-accensione-per-ambiente.md). Nessun
emittente nasceva col registro delle fatture. ✅ Fatto il 2026-10-18 (`20261019-07` … `-12`, applicati su
dbdev, pgTAP verdi): il registro delle fatture standard nasce con l'emittente, dallo stesso meccanismo che crea già
i registri delle altre famiglie. Le altre voci del censimento restano da fare.

C'è anche un secondo difetto, e riguarda come i modelli **evolvono**:

* nessun changeSet **crea** una riga di `documenti.template_documenti`: le righe nascono solo dalla
  UI;
* i changeSet che fanno **evolvere** un modello (esempio: `20260816-01`, la forma a slot degli
  indirizzi del preventivo) scrivono una bozza nuova e la pubblicano, **cercando i modelli per
  `codice_interno`** (`WHERE t.codice_interno = 'test'`, `IN ('ord-ven', 'contratto', 'off-comm')`)
  su tutti gli emittenti insieme.

Quindi:

* su un'installazione nuova quei changeSet non trovano niente, e l'evoluzione non arriva da nessuna
  parte;
* un modello scritto dalla UI con un altro `codice_interno` resta alla forma vecchia. Quando il
  context builder cambia forma (il caso del 2026-08-16), quel modello si rompe al render;
* ogni emittente porta **la sua copia** dello stesso modello, e un'evoluzione va ripetuta su ognuna.
  Le copie, prima o poi, divergono.

Un insieme standard **di sistema**, fornito dal seed e fatto evolvere dai changeSet, chiude
entrambi: l'emittente nuovo emette dal primo giorno, e l'evoluzione ha una sede sola.

## 3. I fatti di struttura (doc `dbzero`, 2026-10-18)

| Pezzo | Com'è oggi | Che cosa c'entra |
| --- | --- | --- |
| `template_documenti.emittente_fiscale_id` | `NOT NULL`, FK su `emittenti_fiscali` | lo standard non ha un emittente |
| `trg_template_documenti_a10_default_emittente_ins` | `script.trgfn_default_emittente_fiscale('SOLLEVA')`: all'INSERT l'emittente viene dalla sessione, e se manca solleva | una riga di sistema non nasce da una sessione d'operatore |
| `uq_template_documenti_default_attivo` | un solo default attivo per `(tipo_documento_output, sorgente, emittente)` | serve anche per lo standard; con un emittente NULL l'indice unico non lo protegge (i NULL sono distinti) |
| `uq_template_documenti_emittente_sorgente_codice[_interno]` | unicità per emittente | come sopra |
| `trgfn_documenti_generati_check_coerenza`, regola 4 | l'emittente del modello deve essere quello del documento generato (`E_DOCUMENTI_GENERATO_COERENZA`) | un documento di DEVA reso con lo standard la viola |
| `template_asset` | catalogo per emittente (`emittente_fiscale_id NOT NULL`, unicità per emittente) | il logo di un modello standard non può essere un asset fisso: deve essere quello dell'emittente del documento |
| `template_documenti_versioni.versione_contesto` | la forma dei dati che la versione legge, controllata da `fn_guard_versione_contesto` | lo standard segue lo stesso patto: nessuna regola nuova |
| RLS su `template_documenti` | nessuna policy; il perimetro lo applica il BE (`emittente_ids_scope`) | la lettura dello standard va aperta a tutti, la scrittura no (§6) |
| Seed | i sei `tipi_documento_output` (PREVENTIVO, CONTRATTO, OFFERTA_COMMERCIALE, ORDINE_VENDITA, DDT_VENDITA, FATTURA_VENDITA) ci sono; nessun modello | il seed nuovo è uno per tipo |

## 4. La proposta, al team DB

**Un modello standard per ogni tipo di documento di output, di sistema, usato come ripiego.**

* Il seed fornisce un modello standard per tipo, con una versione pubblicata.
* La risoluzione ha due livelli: se l'emittente del documento **ha modelli attivi** per quel tipo
  e quella sorgente, si usa il suo **default attivo**; se non ne ha nessuno, si usa il **default
  attivo standard** della stessa coppia (tipo output, sorgente). La regola precisa è nel §4.1,
  Q-2 (strada B, Tid 2026-10-19).
* Un emittente che vuole un modello suo lo crea. Da quel momento vince il suo, e lo standard resta
  il ripiego degli altri.
* I changeSet che fanno evolvere un modello scrivono **sullo standard**, trovato per chiave e non
  per `codice_interno` sparso tra gli emittenti.

La forma è del team DB. Le domande che vediamo:

* **Q-1 — Come si scrive «standard»?** `emittente_fiscale_id` nullable con un `CHECK`, oppure un
  flag di sistema con l'emittente nullo, oppure una tabella sorella. Va tenuto conto di
  `trgfn_default_emittente_fiscale('SOLLEVA')`, che oggi riempie l'emittente dalla sessione, e
  degli indici unici, che con un NULL non proteggono (`NULLS NOT DISTINCT` o un indice parziale
  apposta).
* **Q-2 — La risoluzione a due livelli: dove vive?** Oggi la scrive il BE
  (`DocumentiRepository.find_template_applicabile`). Se la regola sta nel DB (una funzione
  `fn_risolvi_template_applicabile`), il BE la chiama e non la riscrive. Lo proponiamo: è una
  regola del modello, non una query di lista.
* **Q-3 — La coerenza del documento generato.** La regola 4 di
  `trgfn_documenti_generati_check_coerenza` diventa: l'emittente del modello è quello del documento
  **oppure** il modello è standard.
* **Q-4 — Il logo e gli asset.** Un modello standard non può puntare a un asset di un emittente.
  Il logo arriva dal contesto, con l'asset dell'emittente del documento se ce l'ha. Oppure lo
  standard non ha logo. Tutte e due le strade funzionano: dite voi quale.
* **Q-5 — Il destino delle copie di oggi.** Gli emittenti che hanno già i loro sei modelli restano
  com'erano: sono personalizzazioni a tutti gli effetti, e vincono sullo standard. Quello che
  cambia è che i changeSet di evoluzione futuri scrivono sullo standard. Le copie che vogliono la
  stessa evoluzione vanno trattate una per una, o ritirate (spente) a favore dello standard.
  Proponete voi il criterio. Non serve un giro di pulizia adesso.
  ➕ **Aggiunta (Tid, 2026-10-19):** una copia personalizzata smette di ricevere le evoluzioni dello
  standard. Chi l'ha fatta deve poter **vedere** che lo standard è andato avanti, e in particolare
  che la sua copia è rimasta a una `versione_contesto` superata (il caso del 2026-08-16, che si
  rompe al render).

pgTAP, sui casi costruiti e non sulle righe di dbdev: un emittente nuovo emette con lo standard;
l'emittente con il suo default lo preferisce; un secondo default standard per la stessa coppia è
rifiutato; un documento generato con lo standard passa la coerenza, uno con il modello di un altro
emittente no.

### 4.1 Le risposte del team DB (2026-10-19)

> Scritte dalla sessione DB (`dev/db-tid`) sulla struttura (doc `dbzero`, corpi delle funzioni,
> mount dei trigger), non sulle righe di dbdev. Sono il disegno: nessun changeSet scritto.

**Q-1 — «Standard» è un flag esplicito sulla stessa tabella, con l'emittente nullo.**

* Colonna nuova `template_documenti.standard boolean NOT NULL DEFAULT false`, più
  `CHECK (standard = (emittente_fiscale_id IS NULL))`. L'emittente diventa nullable, ma il NULL
  è ammesso **solo** sulla riga standard, e la riga standard non ha mai un emittente. Il CHECK
  chiude anche il caso «NULL per dimenticanza».
* **Perché non solo il NULL.** Un NULL che vuol dire «standard» è un significato nascosto in un
  valore assente: ogni lettore dovrebbe saperlo, e il trigger di default non lo sa. Il flag dice
  l'intenzione, e il `WHEN` del trigger la legge (punto seguente).
* **Perché non una tabella sorella.** `template_documenti_versioni.template_documento_id` e
  `documenti_generati.template_documento_id` puntano a questa tabella. Una sorella
  raddoppierebbe le versioni, `fn_pubblica_template_documento_versione`, i guard della versione
  pubblicata e quelli di `versione_contesto`: è la regola del 2 al contrario.
* **Il trigger di default.** `trg_template_documenti_a10_default_emittente_ins` è montato a mano
  (`20260915-45`, non è un'automazione di `ci_apply`): si rimonta con
  `WHEN (NEW.standard IS NOT TRUE)`, e il BB `trgfn_default_emittente_fiscale` resta com'è.
  Senza il `WHEN`, il seed (che gira senza GUC) solleverebbe `E_EMITTENTE_NON_RISOLTO`. Una riga
  d'operatore senza emittente continua a riceverlo dalla sessione, quindi dalla UI non nasce uno
  standard per sbaglio.
* **Gli indici unici** si rifanno `NULLS NOT DISTINCT`: `uq_template_documenti_default_attivo`
  (un solo default attivo standard per tipo e sorgente), `uq_…_emittente_sorgente_codice` e
  `uq_…_emittente_sorgente_codice_interno` (il `codice_interno` dello standard è unico fra gli
  standard). Uno standard e la copia personalizzata di un emittente possono avere lo stesso
  `codice_interno`, perché il loro emittente è diverso. Il pgTAP controlla la **clausola**
  (`pg_index.indnullsnotdistinct`), non solo il nome.
* **`standard` non si cambia dopo l'INSERT.** Va aggiunto a `trgfn_lock_columns`. Insieme al
  CHECK, questo impedisce anche di trasformare il modello di un emittente in uno standard (o il
  contrario) con un UPDATE dell'emittente.
* **D-2 nel DB.** Un guard `BEFORE INSERT/UPDATE/DELETE` su `template_documenti` e
  `template_documenti_versioni` rifiuta la scrittura di una riga standard se chi scrive non è
  **membro** del ruolo proprietario (si controlla la membership, non il nome del ruolo). Codice
  nuovo: `E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA`. Così il BE non scrive un controllo suo
  (§6): traduce il codice.
* Il trigger del padre attivo sull'emittente (`…_emittenti_fiscali_require_att_…`) con la FK a
  NULL va **verificato nel corpo** prima di contarci; non lo do per scontato.

**Q-2 — La risoluzione sta nel DB: `documenti.fn_risolvi_template_applicabile`.**

* Firma: `(p_sorgente_tipo_id, p_emittente_fiscale_id, p_tipo_documento_output_id)`, STABLE,
  SECURITY INVOKER. Restituisce il `template_documento_id` e il **livello** (`EMITTENTE` |
  `STANDARD`).
* ✅ **La regola (Tid, 2026-10-19, strada B).** Il livello si decide dai **modelli attivi**
  dell'emittente, non dal suo predefinito:
  1. l'emittente ha almeno un modello attivo per la terna (tipo output, sorgente, emittente) →
     livello `EMITTENTE`. Si usa il suo default attivo; se nessuno dei suoi è predefinito, la
     funzione solleva (punto seguente) e lo standard **non** entra;
  2. l'emittente non ha nessun modello attivo per la terna → livello `STANDARD`, e si usa il
     default attivo standard della coppia.

  Il motivo: un modello attivo dell'emittente vuol dire «per questo documento uso i miei». Lo
  standard serve a chi non ne ha nessuno, non a coprire un predefinito dimenticato. Altrimenti il
  documento uscirebbe col modello sbagliato senza nessun errore.
  ⚠️ **Strada scartata (A):** «conta solo il predefinito dell'emittente». Era più semplice, ma
  con un modello suo non predefinito l'emittente sarebbe passato allo standard in silenzio.
* **Nessun modello risolto**: la funzione solleva lei `E_DOCUMENTI_NOT_FOUND`, con due motivi
  diversi:
  * «l'emittente ha modelli attivi ma nessuno predefinito»: il rimedio è segnarne uno;
  * «nessun modello, neanche lo standard» (lo standard del tipo spento o mancante): il rimedio è
    del sistema, non dell'operatore.

  Così `count_templates_attivi_no_default` del BE si ritira nello stesso giro: oggi ricopia i
  filtri di `find_template_applicabile`, e copiarli una terza volta nel DB farebbe tre versioni
  della stessa regola.
* ⚠️ **Spegnere i propri modelli riporta allo standard.** Se l'emittente disattiva tutti i suoi
  modelli di un tipo, torna al livello `STANDARD`. È voluto: «non ho più modelli miei» equivale a
  «uso lo standard».
* ⛔ **Un difetto di oggi da non portarsi dietro.** Il BE accetta il tipo di output **opzionale**
  e chiude con `ORDER BY t.id LIMIT 1`. Il modello ammette più tipi di output per la stessa
  sorgente (il default unico è per terna), quindi senza il tipo vince la riga con l'id più basso.
  È un'ambiguità del modello, non una scelta. Nella funzione il tipo NULL è ammesso solo se il
  candidato è uno; con più candidati la funzione solleva.
* Il perimetro: la funzione riceve l'emittente **del documento**, che il chiamante ha già letto
  sotto RLS. Non rifà lo scope: lo standard si legge da tutti.

**Q-3 — Coerenza: «stesso emittente, oppure standard».** E si scrive con `IS DISTINCT FROM`.

* La regola 4 diventa: si solleva se il modello non è standard **e**
  `emittente_fiscale_id IS DISTINCT FROM NEW.emittente_fiscale_id`.
* ⛔ **Il guard di oggi si aprirebbe da solo.** Il confronto è
  `v_tv_emittente_id != NEW.emittente_fiscale_id`: con l'emittente del modello a NULL vale NULL,
  l'`IF` non scatta e passa **qualunque** documento. Rendere la colonna nullable senza riscrivere
  la regola la spegnerebbe in silenzio, e il pgTAP «modello di un altro emittente rifiutato»
  resterebbe verde, perché quel caso ha l'emittente valorizzato. Il caso standard va provato a
  parte.
* `documenti_generati.emittente_fiscale_id` resta NOT NULL: il documento ha sempre un emittente,
  anche quando lo rende lo standard.

**Q-4 — Lo standard non richiama asset.**

* Fatto di struttura: le versioni richiamano gli asset per nome (`asset:<codice_interno>`). Il
  risolutore li cerca **fra gli asset dell'emittente del documento**, e un asset che manca è
  `E_DOCUMENTI_RENDER_FAILED`, senza ripiego (decisione di Tid del 2026-10-01: un logo generico
  al suo posto darebbe un PDF sbagliato senza errore).
* Quindi uno standard che scrive `asset:logo` non stamperebbe per nessun emittente che non ha
  caricato quel logo, e il primo è proprio l'emittente nuovo del §1. Lo standard nasce senza
  `asset:`, ed è coerente con la D-3 («si tolgono gli asset»).
* L'evoluzione «logo dell'emittente se ce l'ha» richiede che il template possa chiedere se un
  asset esiste (un dato di contesto o una funzione del render). È lavoro del BE e va fuori da
  questo brief. Il DB non ha niente da aggiungere: `template_asset` resta per emittente.

**Q-5 — Le copie: si registra da dove derivano, e lo scarto si vede.**

* Colonna nuova `template_documenti_versioni.derivata_da_versione_id`, nullable, con FK sulla
  versione standard. La scrive l'azione «personalizza» (D-2) sulla prima versione della copia. Un
  guard `a10` (non un `CHECK`, perché legge altre righe) controlla che la versione da cui si
  deriva sia di uno standard, con lo stesso tipo di output e la stessa sorgente.
* **Lo scarto (aggiunta di Tid).** Una vista `documenti.vw_template_personalizzati_scarto`
  mette, per ogni modello di emittente attivo che ha uno standard sulla stessa coppia: la versione
  da cui deriva, l'ultima versione standard pubblicata e le due `versione_contesto`. Lo stato è
  uno di tre:
  * `ALLINEATA`: deriva dall'ultima versione standard;
  * `STANDARD_AVANTI`: lo standard ha pubblicato dopo; la copia funziona ma non ha l'evoluzione;
  * `CONTESTO_SUPERATO`: la `versione_contesto` della copia non è più quella che il builder
    produce. È il caso del 2026-08-16: alla stampa scatta già il guard di `versione_contesto`, la
    vista lo fa vedere **prima**.

  Una copia senza `derivata_da_versione_id` (tutte quelle di oggi, e ogni modello scritto da zero)
  esce `ORIGINE_NON_DICHIARATA`, e il confronto si fa solo sulla `versione_contesto`. La lista FE
  la legge per il badge (§6).
* **Il criterio per le copie di oggi.** Restano e vincono (§4). Non si scrive un changeSet di
  pulizia: sono dati di sviluppo (non c'è produzione), e un changeSet che le spegne per
  `codice_interno` ripeterebbe proprio il difetto del §2. Se su dbdev Tid vuole che un emittente
  passi allo standard, si spegne il suo default **a mano**, e la vista sopra dice quali copie
  sono indietro.
* I changeSet di evoluzione **futuri** scrivono solo sullo standard, cercato per
  `(standard, tipo_documento_output_id, sorgente_tipo_id, codice_interno)`. Quelli già applicati
  (`20260816-01` e simili) non si toccano.

**Il seed (D-3), forma.** La riga standard di `template_documenti` è una riga di catalogo: va in un
CSV di `80_data` con id esplicito. Le **versioni** invece no: la pubblicazione porta la versione
precedente in `OBSOLETA` con un UPDATE, e un mirror `loadUpdateData` la riporterebbe indietro a
ogni giro. Per le versioni si usa la forma che le evoluzioni hanno già: un changeSet forward-only in
`80_data/changelog` che scrive la bozza e chiama `fn_pubblica_template_documento_versione`. Il
contenuto lo rilegge Tid prima (D-3).

**pgTAP, oltre ai quattro casi sopra.**

* Il seed senza GUC non solleva.
* Una riga d'operatore senza emittente lo riceve dalla sessione e non diventa standard.
* `standard` non si cambia dopo l'INSERT.
* `zeroerp_app` non scrive lo standard.
* Il tipo NULL con due candidati solleva.
* Strada B: un emittente con un modello suo attivo ma non predefinito riceve
  `E_DOCUMENTI_NOT_FOUND` col motivo «senza predefinito», e **non** lo standard. Lo stesso
  emittente, spenti i suoi modelli, torna allo standard.
* La vista dello scarto classifica i quattro stati su casi costruiti.

Presidi trasversali da far girare prima dell'apply: catalogo messaggi d'errore completo, scrittori
degli stati, perimetro RLS e storico scope (la colonna nuova sulle versioni ha una FK).

## 5. Decisioni di Tid

✅ **Decise il 2026-10-19: D-1, D-2 e D-3 come da proposta.**

* **D-1 — Ripiego o copia alla nascita?** Proposta: **ripiego** (§4). Una copia fatta alla nascita
  dell'emittente ripete il difetto del §2: N copie dello stesso modello, e un'evoluzione da
  ripetere N volte.
* **D-2 — Chi modifica lo standard?** Proposta: **solo i changeSet**, come ogni seed di sistema.
  Nella UI lo standard si vede in sola lettura, con un'azione «personalizza per questo emittente»
  che crea il modello dell'emittente partendo dalla versione standard. È una copia voluta,
  dichiarata e fatta da chi la vuole: diversa da quelle del §2.
* **D-3 — Da dove viene il contenuto?** I modelli di oggi sono stati scritti a mano dalla UI per un
  emittente. Proposta: si parte dalle versioni pubblicate dell'emittente 32 (quelle che i changeSet
  di evoluzione hanno tenuto aggiornate) e si tolgono i riferimenti specifici dell'azienda (testi
  fissi, asset). Il contenuto va riletto da Tid prima del seed.

## 6. Ricaduta BE/FE (dopo l'apply)

* **BE — risoluzione.** `find_template_applicabile` chiama `fn_risolvi_template_applicabile`;
  `count_templates_attivi_no_default` si ritira, perché il motivo dell'`E_DOCUMENTI_NOT_FOUND` lo
  dà la funzione (§4.1 Q-2). Il filtro di perimetro `emittente_ids_scope` delle letture deve
  lasciar passare lo standard (`… OR t.standard`).
* **BE — scrittura.** Il rifiuto lo dà il DB: `E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA`
  (§4.1 Q-1). Al BE resta solo la policy generata del codice. «Personalizza» crea il modello
  dell'emittente e scrive `derivata_da_versione_id` sulla sua prima versione (§4.1 Q-5).
* **FE — lista Modelli documento.** Lo standard compare con un badge «standard» in sola lettura.
  Sull'emittente che non ha il suo, la riga dice che si usa lo standard. Azione «personalizza».
  Un emittente che ha modelli suoi ma nessuno predefinito non riceve lo standard (§4.1 Q-2,
  strada B): la lista lo segnala, perché è lo stato che ferma l'emissione.
  Sulle copie, lo stato di `vw_template_personalizzati_scarto` (§4.1 Q-5).
* **Documento generato.** Lo storico (`documenti_generati`) punta già alla versione usata: nessun
  cambio.

## 7. Ricaduta sugli smoke

Con lo standard, l'emittente di prova A (DEVA) emette senza configurazione. Gli smoke che oggi si
fermano su `E_DOCUMENTI_NOT_FOUND` (preventivi, smistamento-ordine, contratti-addebito,
listini-v5 dal passo 16, pratica-preventivi-bivio, resi-vendita sul modello delle bolle) arrivano in
fondo. L'elenco aggiornato è la tabella di R-BE-14 in
[brief-db-processi-accensione-per-ambiente §6.12](../work-done/brief-db-processi-accensione-per-ambiente.md)
(2026-10-19): lì il BE ha chiesto registri e template insieme; i template sono di questo brief. Gli smoke della fatturazione, che cercano un'attività
fatturabile esistente, restano un lavoro loro: si costruiscono la materia (brief BE utenti di
sviluppo, §9, T-7).

Restano fuori da questo brief, perché non hanno un default di sistema sensato: i listini e la
mappa categoria cliente → listino. Sono decisioni commerciali dell'azienda, e gli smoke li creano
da sé (T-7).
