# Brief DB — I modelli di documento standard: un emittente nuovo emette dal primo giorno

## ⏭️ Chi riparte — aggiornato al 2026-10-20

**Riparte: il BE, con la versione restituita dalla risoluzione (§8.4, P-2) e la coda di stampa che
passa il tipo (§9.4), poi «personalizza» e la lista Modelli documento con il FE (§6); il team DB,
con la voce nuova del censimento (§2, Q-6 … Q-8: `emittenti_fiscali_utilities`).**

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | **Tid** | ✅ D-1, D-2, D-3 come da proposta (2026-10-19) | §5 | — |
| 2 | **team DB** | ✅ Disegno della forma e risposte a Q-1 … Q-5 (2026-10-19) | §4.1 | 1 |
| 3 | **Tid** | ✅ Strada B per Q-2 e via allo sviluppo (2026-10-19) | §4.1 | 2 |
| 4 | **team DB** | ✅ Tranche 1: forma, guard, risoluzione, coerenza, derivazione, vista, codici, lock, pgTAP (`20261020-04` … `-12`), provata sullo scratch | §8.1 | 3 |
| 5 | **Tid** | ✅ Apply della tranche 1, pgTAP verdi (2026-10-19) | §8.1 | 4 |
| 6 | **Tid** | ✅ Contenuti (D-3) e testi fissi: proposte accettate (2026-10-19) | §8.2 | — |
| 7 | **team DB** | ✅ Tranche 2: il seed dei sei standard (`20261020-13` … `-18`), provato sullo scratch e su dbdev | §8.2 | 6 |
| 8 | **Tid** | ✅ Apply della tranche 2, pgTAP verdi (2026-10-19) | §8.2 | 7 |
| 8-bis | **team DB** | ✅ Correzione Q-2: conta solo un modello che può stampare (`20261020-26`), provata sullo scratch e su dbdev | §8.4 | — |
| 8-ter | **Tid** | ✅ Apply di `20261020-26` e dei due CSV dei codici, pgTAP verdi (2026-10-20) | §8.4 | 8-bis |
| 9 | **BE** | ✅ La risoluzione a due livelli: `risolvi_template_applicabile`, ritiro di `count_templates_attivi_no_default`, perimetro di lettura con lo standard, test e smoke allineati, policy rigenerate dopo `-26` (`fad3ad71f` PR #1905, `323c96a5c` PR #1907) | §6 | 5, 8-ter |
| 9-bis | **BE/FE** | L'azione «personalizza» (`derivata_da_versione_id`) e la lista Modelli documento (badge standard, «si usa lo standard», emittente senza predefinito, stato dello scarto) | §6 | 9 |
| 9-ter | **team DB** | Censimento, voce «parametri d'importo per utility» (`emittenti_fiscali_utilities`): risposte a Q-6 … Q-8; DEVA non chiude una fattura | §2 | — |
| 9-quater | **team DB** | ✅ Coda di stampa: risposte a Q-1 … Q-4 della richiesta BE, sulla struttura (2026-10-20). Nessun changeSet scritto | §9 | — |
| 9-quinquies | **Tid** | ✅ C-1 … C-3, P-1 e P-2 come da proposta, e via allo sviluppo (2026-10-20) | §9.3, §8.4 | 9-quater |
| 9-sexies | **team DB** | ✅ ChangeSet `20261020-27` … `-31`, tre righe di CSV, pgTAP e manuali, provati sullo scratch (2026-10-20) | §9.5 | 9-quinquies |
| 9-septies | **Tid** | ✅ Apply su scratch e dbdev (2026-10-20, due migrate su dbdev), pgTAP verdi, nessuna regressione | §9.5 | 9-sexies |
| 9-octies | **BE** | P-2: `risolvi_template_applicabile` usa `template_versione_id` e ritira i filtri di `get_versione_pubblicata_attiva` per la stampa. Coda: `claim_stampe_pending` porta la colonna, il worker la passa a `genera_documento`; il task di pipeline passa il tipo dove lo conosce | §8.4, §9.4 | 9-septies |
| 10 | **BE** | Il giro degli smoke su `dev.smoke` (DEVA emette con lo standard) | §7 | 8, 9, 9-ter |
| 11 | **Tid** | Archiviazione in `work-done/` | — | 10 |

**Decisioni aperte di Tid: nessuna.** P-1, P-2 e C-1 … C-3 decise come da proposta (2026-10-20).
Committati: tranche 1 e 2 (`560d5d97e`, PR #1899), `20261020-26` (`0ff115bf0`, PR #1906), BE
(`fad3ad71f`, `323c96a5c`), e la coda di stampa con P-2 (`20261020-27` … `-31`, tre CSV, pgTAP,
manuali, 2026-10-20).

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-18. **A chi:** Tid (§5), poi il team DB;
> la §6 al BE/FE.
> **Origine:** il collaudo T-5 di [brief-be-utenti-di-sviluppo](brief-be-utenti-di-sviluppo.md)
> (§9). L'emittente di prova A, creato dal verbo di sviluppo, non emette nessun documento: non ha
> modelli. Proposta di Tid (2026-10-18): «la cosa migliorativa è fornire un set di modelli
> standard».
> **Stato:** ✅ lato DB chiuso per i modelli: tranche 1, tranche 2 (seed) e `-26` applicate, pgTAP
> verdi, committate. ✅ BE: la risoluzione a due livelli (2026-10-20). Restano «personalizza» e la
> lista FE (§6), la coda di stampa che dice che cosa stampare (§9, al DB dopo le decisioni di Tid)
> e il giro degli smoke (§7). Dettaglio nel §8.

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

➡️ **La voce «parametri d'importo per utility»: al team DB** (sessione BE, 2026-10-19, smoke
`push-termine-documento-commessa`). Con il registro a posto, il giro arriva alla fattura e si ferma
in `vendite.fn_ricalcola_totali_fattura` con `E_CONFIG_MANCANTE` «configurazione emittente/utility
mancante». I fatti di struttura (doc `dbzero`):

* `anagrafiche.emittenti_fiscali_utilities` porta, per la coppia (emittente, utility), i decimali
  e il metodo dell'arrotondamento degli importi (`arrotondamento_importi_dec`,
  `metodo_arrotondamento_importi`, entrambi `NOT NULL`) e le soglie del minimo
  (`minimo_soglia_min`/`_max`, nullable). La chiave unica è `(emittente_soggetto_ruolo_id,
  utility_id)`;
* `fn_ricalcola_totali_fattura` la legge con una `SELECT … LIMIT 1` e, se non trova la riga
  (`v_decimali IS NULL`), solleva `E_CONFIG_MANCANTE`: **senza la riga la fattura non si chiude**;
* nessun meccanismo la crea alla nascita dell'emittente, né per le utility che l'emittente
  esercita: si scrive solo dalla UI.

⚠️ **E il modello la legge in due modi.** `anagrafiche.fn_lookup_utilities_per_ba` la prende in
`LEFT JOIN`, con il commento «override parametri per emittente (politica ibrida)»: lì è un
**override facoltativo**. `fn_ricalcola_totali_fattura` la tratta invece come **obbligatoria**.
Le due letture non possono essere vere insieme, ed è la prima cosa da decidere.

**Le domande al team DB:**

* **Q-6.** La riga è un override facoltativo o una configurazione obbligatoria? Se è un override,
  qual è il valore di sistema da cui si parte quando manca (decimali e metodo — la valuta
  dell'emittente ha già la sua precisione?), e `fn_ricalcola_totali_fattura` deve ripiegare lì
  invece di sollevare. Se è obbligatoria, chi la crea: nasce con l'emittente per ogni utility
  ammessa al suo tipo di ruolo, o nasce quando l'emittente comincia a esercitare una utility?
* **Q-7.** Le soglie del minimo restano dell'emittente, senza standard (sono una scelta
  commerciale, come i listini al §7)? Oggi sono già nullable: va solo confermato che il NULL
  significa «nessun minimo».
* **Q-8.** C'è un pgTAP che costruisce un emittente nuovo e porta una fattura fino al ricalcolo
  dei totali? È il presidio che avrebbe visto il buco prima dello smoke
  (`dbops.fn_pgtap_crea_fattura` scrive la riga a mano, quindi non lo vede).

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
* ⚠️ *Corretto il 2026-10-20 (§8.4): «attivo» va letto «che può stampare». Un modello conta solo
  se è attivo e ha una versione PUBBLICATA, attiva e valida alla data operativa; una bozza non
  toglie lo standard.*
  ✅ **La regola (Tid, 2026-10-19, strada B).** Il livello si decide dai **modelli attivi**
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
* ⚠️ *Superato in sviluppo (§8.1, correzione 1): i due motivi sono due codici nuovi,
  non `E_DOCUMENTI_NOT_FOUND`.*
  **Nessun modello risolto**: la funzione solleva lei `E_DOCUMENTI_NOT_FOUND`, con due motivi
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
* ⚠️ *Ridimensionato in sviluppo (§8.1, correzione 2): col CHECK di Q-1 il NULL esiste solo
  sullo standard, quindi il buco è chiuso anche dal CHECK. La riscrittura resta, perché la regola
  non deve dipenderne.*
  ⛔ **Il guard di oggi si aprirebbe da solo.** Il confronto è
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
    vista lo fa vedere **prima**. ⚠️ *Precisato in sviluppo (§8.1, correzione 3): il DB non
    conosce la costante del builder, quindi il riferimento è l'ultima versione standard
    pubblicata.*

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

⚠️ *Superato in sviluppo (§8.2): niente CSV, anche la riga del modello nasce dal changeSet.*
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

> ⚠️ Fino a questi passi del BE la tranche 1 **non cambia niente a video**: `find_template_applicabile`
> filtra ancora per emittente, quindi lo standard non si usa, e le liste non lo mostrano. Nessuna
> scrittura del BE di oggi viene rifiutata: i modelli d'emittente passano il guard come prima
> (test 7 del file app).

* **BE — risoluzione.** `find_template_applicabile` chiama
  `documenti.fn_risolvi_template_applicabile(sorgente, emittente del documento, tipo)` e usa il
  `template_documento_id` che restituisce. `count_templates_attivi_no_default` si ritira nello
  stesso giro (regola del 2): i due casi che distingueva sono ora due codici del DB,
  `E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO` (409, rimedia l'operatore) ed
  `E_DOCUMENTI_TEMPLATE_NON_RISOLTO` (404). Il tipo va **sempre** passato dove il BE ce l'ha:
  senza, su una sorgente con più tipi, la funzione solleva `E_DOCUMENTI_TEMPLATE_AMBIGUO` (500)
  invece di prendere l'id più basso. Il filtro di perimetro `emittente_ids_scope` delle letture
  (lista, dettaglio, versioni) deve lasciar passare lo standard (`… OR t.standard`).
* **BE — scrittura.** Il rifiuto lo dà il DB: `E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA`
  (§4.1 Q-1, `NON_PERMESSO`), anche sulle versioni dello standard. Al BE resta solo la policy
  generata dei codici nuovi (`error_policies_generated.py`). «Personalizza» crea il modello
  dell'emittente e scrive `derivata_da_versione_id` sulla sua prima versione (§4.1 Q-5); un valore
  sbagliato è `E_DOCUMENTI_TEMPLATE_DERIVAZIONE_INVALIDA` (500), e fuori bozza l'origine non cambia
  (`E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE`).
* **Codici nuovi** (sei, nei due CSV): `E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA`,
  `E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO`, `E_DOCUMENTI_TEMPLATE_NON_RISOLTO`,
  `E_DOCUMENTI_TEMPLATE_AMBIGUO`, `E_DOCUMENTI_RISOLVI_TEMPLATE_INPUT_INVALIDO`,
  `E_DOCUMENTI_TEMPLATE_DERIVAZIONE_INVALIDA`.
* **FE — lista Modelli documento.** Lo standard compare con un badge «standard» in sola lettura.
  Sull'emittente che non ha il suo, la riga dice che si usa lo standard. Azione «personalizza».
  Un emittente che ha modelli suoi ma nessuno predefinito non riceve lo standard (§4.1 Q-2,
  strada B): la lista lo segnala, perché è lo stato che ferma l'emissione.
  Sulle copie, lo stato di `vw_template_personalizzati_scarto` (§4.1 Q-5).
* **Documento generato.** Lo storico (`documenti_generati`) punta già alla versione usata: nessun
  cambio.

### Stato al 2026-10-19 (verifica della sessione BE, prima di iniziare)

**Il DB, verificato su dbdev:** `documenti.fn_risolvi_template_applicabile(bigint, bigint, bigint)`
e `documenti.vw_template_personalizzati_scarto` esistono; i sei standard ci sono (id 2728-2733),
predefiniti e attivi, ognuno con la versione 1 `PUBBLICATA`.

**Il BE, già fatto:** le policy dei sei codici nuovi sono rigenerate in `error_policies_generated.py`
ed `error_messages_fallback.py`.

**Il BE, da fare** (aggiornato il 2026-10-20 dalla sessione DB, sul codice: i punti ✅ sono
committati in `fad3ad71f`, PR #1905, e il test della strada B adeguato alla `-26` in `323c96a5c`,
PR #1907):

1. ✅ `DocumentiRepository.find_template_applicabile` filtra ancora per emittente e chiude con
   `ORDER BY t.id LIMIT 1`, quindi lo standard non si usa mai. Deve chiamare
   `fn_risolvi_template_applicabile`. → ora `risolvi_template_applicabile`.
2. ✅ `count_templates_attivi_no_default` e il suo ramo in
   `DocumentGenerationService._resolve_template` si ritirano.
3. Il tipo di output non lo passa nessun chiamante di `genera_documento`
   (`stampa_coda_drainer_service`, `sorgente_documenti_views`). Va passato dove il BE lo conosce.
   → Le viste di `sorgente_documenti_views` lo accettano dal chiamante
   (`tipo_documento_output_id`, opzionale). Il worker della coda no, perché la riga della coda non
   lo porta: è un difetto del modello della coda, ed è il §9.
4. Il filtro `emittente_ids_scope` delle letture (lista, dettaglio, versioni, asset) deve lasciar
   passare lo standard. ✅ lista e dettaglio dei modelli (`_TEMPLATE_IN_SCOPE`), e le versioni che
   passano dal dettaglio; gli asset restano dell'emittente del documento.
5. L'azione «personalizza», che scrive `derivata_da_versione_id`. Da fare (nessun riferimento alla
   colonna in `backend/apps/documenti`, 2026-10-20).
6. ✅ Si allineano i test dei due metodi (`test_document_generation_service*.py`,
   `test_documenti_repository_render.py`) e lo smoke `smoke-fatturazione-render-stampa.py`, che
   li usano.

**Il FE, da fare** (ancora tutto, 2026-10-20): in `ModelliDocumentiTemplatesView`, `TemplateDocumentiSearchTable` e
`TemplateDocumentoDrawer`, le cose elencate sopra: il badge «standard» in sola lettura, la riga
«si usa lo standard», la segnalazione dell'emittente senza predefinito, l'azione «personalizza» nel
kebab e lo stato dello scarto sulle copie.

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

## 8. Sviluppo

### 8.1 Tranche 1 — la forma e le regole (2026-10-19; ✅ applicata da Tid, pgTAP verdi)

Il seed dei contenuti è nella tranche 2 (§8.2): la D-3 chiede che Tid li rilegga prima.

| ChangeSet | Che cosa | Risposta |
| --- | --- | --- |
| `00_schema/documenti/20261020-04-alter-template-documenti-standard` | colonna `standard`, emittente nullable solo sullo standard (`chk_template_documenti_standard_senza_emittente`), i tre unici rifatti `NULLS NOT DISTINCT` con lo stesso nome | Q-1 |
| `00_schema/documenti/20261020-05-add-template-documenti-versioni-derivata-da` | colonna `derivata_da_versione_id` (FK sulla stessa tabella) | Q-5 |
| `20_code/documenti/20261020-06-recreate-trigger-default-emittente-template-salta-standard` | il default dell'emittente rimontato con `WHEN (NEW.standard IS NOT TRUE)`; il BB non cambia | Q-1 |
| `20_code/documenti/20261020-07-create-trgfn-template-standard-guard-sola-lettura` | guard `a05` su modelli e versioni: lo standard lo scrive solo il proprietario della tabella (`script.fn_is_proprietario_tabella`, lo stesso BB di `ui.lista_definizione.multi_emittente`) | D-2 |
| `20_code/documenti/20261020-08-update-trgfn-documenti-generati-check-coerenza-standard` | regola 4 «stesso emittente, oppure standard»; i quattro confronti in `IS DISTINCT FROM` | Q-3 |
| `20_code/documenti/20261020-09-create-fn-risolvi-template-applicabile` | la risoluzione a due livelli, strada B | Q-2 |
| `20_code/documenti/20261020-10-create-trgfn-template-versioni-guard-derivata-da` | l'origine è una versione standard della stessa coppia, e fuori bozza non cambia | Q-5 |
| `20_code/documenti/20261020-11-create-vw-template-personalizzati-scarto` | la vista dello scarto, quattro stati | Q-5 |
| `90_end/20261020-12-provision-lock-template-documenti-standard` | il lock di `standard` subito, col runner che converge | Q-1 |

Dati: sei codici in `config/codici_errore.csv` e `config/messaggi_errore.csv` (id 1371-1376), la
causa di `E_DOCUMENTI_GENERATO_COERENZA` aggiornata, una riga in
`dbops/automation_lock_columns.csv` (`documenti.template_documenti.standard`,
`E_COLONNA_NON_MODIFICABILE`). Manuali: `documenti/manual/template_documenti.md` (§ «Il modello
standard»), `fn_risolvi_template_applicabile.md`, `vw_template_personalizzati_scarto.md`.

pgTAP:

* `documenti/test-documenti-template-standard-v1.sql` (30 test, **da owner** col marcatore: la
  fixture costruisce degli standard, che l'applicazione non può costruire);
* `documenti/test-documenti-template-standard-app-v1.sql` (7 test, **come app**: il rifiuto). I
  test 3-6 hanno bisogno di uno standard del seed: fino alla tranche 2 sono `skip` dichiarati.

**Tre correzioni al §4.1, emerse scrivendo:**

1. **Q-2, i codici.** Il §4.1 diceva `E_DOCUMENTI_NOT_FOUND` con due motivi. Sono due codici,
   perché i rimedi sono di due persone diverse: `E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO`
   (`CONFLITTO_STATO`: lo risolve l'operatore segnando un predefinito) ed
   `E_DOCUMENTI_TEMPLATE_NON_RISOLTO` (`NON_TROVATO`: manca lo standard). Il messaggio di
   `E_DOCUMENTI_NOT_FOUND` è generico («Documento o template non trovato.») e non ha segnaposti.
2. **Q-3, il buco del `!=`.** Col CHECK di Q-1 l'emittente del modello è NULL **solo** sullo
   standard: il vecchio `!=` avrebbe lasciato passare i documenti resi con lo standard, cioè
   proprio quelli da ammettere, e nessun altro. Il «guard che si apre da solo» lo chiude anche il
   CHECK. La riscrittura resta, perché la regola deve dire lo standard per nome e non dipendere da
   un vincolo di un'altra sede. Il pgTAP prova i due lati (test 19 e 20).
3. **Q-5, il riferimento di `CONTESTO_SUPERATO`.** Il DB non conosce la costante del builder del
   BE. Il riferimento è l'ultima versione standard pubblicata, che i changeSet di evoluzione
   tengono al passo col builder.

E due scelte di forma, dichiarate:

* il lock di `standard` usa il codice generico `E_COLONNA_NON_MODIFICABILE`, perché lo incontra
  solo il proprietario: dall'applicazione, su una riga standard, parla prima il guard `a05`;
* `derivata_da_versione_id` non è nell'elenco a mano del guard della versione pubblicata. La regola
  «fuori bozza non cambia» la dice il guard della derivazione, con lo stesso codice
  (`E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE`), invece di rimontare quel trigger.

**La prova (2026-10-19, sullo scratch `zeroerp_ruoli`, da owner, in transazione annullata).**
L'SQL è estratto dagli YAML. Il seed dei codici e del registro dei lock è **simulato** con degli
`INSERT` dalle righe nuove dei CSV: la prova non esercita il loader.

* `test-documenti-template-standard-v1.sql`: 30/30.
* File app: da owner i test 1 e 2 sono rossi **per costruzione**, perché il guard lascia passare
  il proprietario. Con `script.fn_is_proprietario_tabella` ridefinita a `false` dentro la
  transazione (simulazione del ruolo app) danno 7/7, 3 test verdi e 4 skip; con uno standard
  simulato anche i 4 skip diventano verdi. Il verde come app vero arriva dalla corsa di Tid.
* Mutazione: senza `-06` (il `WHEN`) quattro test vanno in rosso, e il seed senza sessione si
  ferma su `E_EMITTENTE_NON_RISOLTO`.
* Prima e dopo, stessi esiti su tutti i pgTAP di `documenti/` e sui presidi trasversali:
  `script/test-trgfn-default-emittente-fiscale-v1`, `test-catalogo-messaggi-errore-completo`,
  `test-permessi-funzioni-risoluzione`, `test-security-definer-search-path-v1`;
  `dbops/test-lock-columns-convergenza`, `test-vw-codici-errore-motivo-nominato`,
  `test-vw-codici-errore-valore-atteso`, `test-storico-scope-policy-v1`,
  `test-storico-automazione-colonna-fk-v1`, `test-storico-colonna-fk-dei-trigger-v1`,
  `test-automazione-attivo-eccezioni-v1`, `test-sorgenti-orfane-v1`, `test-riferimenti-morti-v1`,
  `test-stati-check-scrittori-v1`, `test-vw-bersagli-non-dichiarati`;
  `rls/test-rls-perimetro-scoperto`, `test-rls-viste-security-invoker`. I rossi preesistenti da
  owner (`documenti-generati-eventi` 16, `sec-functions-owner-riservato-v1` 5-7, 9, 10) sono
  identici prima e dopo.
* Da `ci_apply` l'automazione ATTIVO genererà i trigger del padre attivo anche sulla FK nuova
  `derivata_da_versione_id`. È un effetto voluto della policy, non è stato provato qui.

### 8.2 Tranche 2 — il seed dei sei standard (2026-10-19; ✅ applicata da Tid, pgTAP verdi)

**Le scelte di Tid (2026-10-19): proposte accettate.** Tolte le scritte «Template demo», tolto il
piè di pagina «Zero ERP» (si toglie l'intero blocco `@bottom-left`, che portava solo quella
scritta), `codice_interno` = il codice del tipo di documento in minuscolo.

| ChangeSet (`80_data/changelog/`) | Standard (`codice_interno`) | Tipo / sorgente | Origine (emittente 32) | `versione_contesto` |
| --- | --- | --- | --- | --- |
| `20261020-13-seed-template-standard-preventivo` | `preventivo` | PREVENTIVO / PREVENTIVO | `test` v4 | 2 |
| `20261020-14-seed-template-standard-contratto` | `contratto` | CONTRATTO / CONTRATTO | `contratto` v3 | 2 |
| `20261020-15-seed-template-standard-offerta-commerciale` | `offerta_commerciale` | OFFERTA_COMMERCIALE / OFFERTA_COMMERCIALE | `off-comm` v3 | 2 |
| `20261020-16-seed-template-standard-ordine-vendita` | `ordine_vendita` | ORDINE_VENDITA / ORDINE_VENDITA | `ord-ven` v4 | 2 |
| `20261020-17-seed-template-standard-ddt-vendita` | `ddt_vendita` | DDT_VENDITA / DDT_VENDITA | `ddt-ven` v3 | 2 |
| `20261020-18-seed-template-standard-fattura-vendita` | `fattura_vendita` | FATTURA_VENDITA / FATTURA | `fattura` v7 | 5 |

Ogni changeSet scrive il modello standard (predefinito, attivo, senza emittente) e la sua versione
1 come bozza. Poi la pubblica con `fn_pubblica_template_documento_versione`, che controlla anche la
forma dei dati, con **`valido_dal = 2000-01-01`**. La stampa sceglie la versione valida alla data
operativa, e lo standard deve valere anche per un documento con una data passata. Idempotente: se
lo standard c'è già (chiave `standard + sorgente + codice_interno`), non fa niente. Il contenuto è
scritto nel changeSet: al migrate non si legge niente da dbdev.

Due ritocchi al contenuto, oltre alle scelte di Tid, dichiarati nell'intestazione del changeSet:

* nel preventivo il refuso `sizea: A4;` diventa `size: A4;`: era una proprietà sconosciuta, che
  il render ignorava;
* titoli delle versioni puliti («Ordine di vendita» al posto di «stampa odine vendita», e così via).

⚠️ **Corretto rispetto al §4.1 («Il seed») e alla prima stesura di questo paragrafo: niente CSV.**
`template_documenti` è una tabella mista: i modelli degli emittenti nascono dall'applicazione.

* Un mirror con id espliciti collide con gli id che l'applicazione crea.
* Un mirror sulla chiave naturale aggiornerebbe le copie degli emittenti con lo stesso codice
  interno: su dbdev `contratto` è anche il codice di una copia dell'emittente 32.

Lo standard nasce quindi con un changeSet SQL forward-only, cioè con la stessa forma con cui si
fanno le sue evoluzioni. Non ci sono due sorgenti di verità, perché la tabella non ha un CSV.

**La prova (2026-10-19, in transazione annullata).** L'SQL è estratto dagli YAML.

* Seed eseguito due volte, sullo scratch `zeroerp_ruoli` (vuoto, come un database da zero) e su
  dbdev: sei standard pubblicati, nessuna riga in più al secondo giro, nessuna scritta «Zero ERP»
  nel contenuto.
* Sopra il seed, sui due database: `test-documenti-template-standard-v1.sql` 30/30, e il file app
  7/7 con la simulazione del ruolo app (zero skip: con il seed i test 3-6 sono asserzioni vere).
* I pgTAP di `documenti/` e `script/test-trgfn-default-emittente-fiscale-v1` hanno gli stessi
  esiti prima e dopo il seed. Da owner il file app passa da 2 a 5 rossi **per costruzione**: con il
  seed i test 3-5 non sono più skip, e da owner il guard lascia passare il proprietario. Come app,
  nella corsa di Tid, il verde atteso è 7/7.

La prima stesura del paragrafo, prima delle scelte:

**La sorgente (D-3)**: le versioni pubblicate dell'emittente 32 su dbdev, lette il 2026-10-19:

| Modello (id) | Tipo / sorgente | Versione | `versione_contesto` |
| --- | --- | --- | --- |
| `test` (40) | PREVENTIVO / PREVENTIVO | 4 | 2 |
| `contratto` (41) | CONTRATTO / CONTRATTO | 3 | 2 |
| `off-comm` (74) | OFFERTA_COMMERCIALE / OFFERTA_COMMERCIALE | 3 | 2 |
| `ord-ven` (75) | ORDINE_VENDITA / ORDINE_VENDITA | 4 | 2 |
| `ddt-ven` (76) | DDT_VENDITA / DDT_VENDITA | 3 | 2 |
| `fattura` (77) | FATTURA_VENDITA / FATTURA | 7 | 5 |

* **Asset**: nessuna versione richiama `asset:`. Q-4 non chiede di togliere niente.
* **Testi fissi trovati** (da decidere, Tid):
  * il piè di pagina `content: "Zero ERP"` nel CSS di cinque modelli;
  * le scritte `"Zero ERP - Template demo contratto"`, `"… demo preventivo"`, `"… demo offerta
    commerciale"` nell'HTML di tre modelli.

  Proposta: togliere le scritte «Template demo»; il piè di pagina «Zero ERP» o si toglie, o si
  sostituisce con un dato dell'emittente dal contesto.
* **Il `codice_interno` dello standard**: proposta = il codice del tipo di documento in minuscolo
  (`preventivo`, `contratto`, …), non `test` né le sigle di oggi. È la chiave con cui i changeSet di
  evoluzione futuri lo trovano.

⚠️ *Superato: niente CSV, vedi sopra.* **La forma** (§4.1, «Il seed»): le sei righe dei modelli in un CSV di catalogo con id esplicito e
mirror `loadUpdateData`; le versioni in un changeSet forward-only per modello in
`80_data/changelog`, che scrive la bozza e la pubblica con
`fn_pubblica_template_documento_versione`. Poi il file app perde i suoi skip.

### 8.3 La prima evoluzione di uno standard (rimando, 2026-10-20)

Lo standard «Ordine di vendita» ha la versione 2 (`20261020-25`), nella forma di Q-5: copia della pubblicata,
solo sullo standard, pubblicata dalla data operativa. Dichiara la **forma dei dati 3** (chiave nuova
`origine.etichetta`): dopo il giro BE le copie degli emittenti in forma 2 non stampano più. Sede:
[brief-db-grammatica-unica-documenti §12.10](brief-db-grammatica-unica-documenti.md).

### 8.4 Correzione Q-2: conta solo un modello che può stampare (2026-10-20; ✅ applicata da Tid, pgTAP verdi)

**Il difetto** (segnalato dal BE, decisione di Tid del 2026-10-19). La strada B decideva dai
modelli **attivi**. Ma un modello si prepara solo da attivo: una versione attiva sotto un modello
spento la rifiuta `trgfn_child_requires_active_parent`. Su `template_documenti`, `attivo` dice
insieme «esiste» e «in uso per la stampa». La copia appena creata da «personalizza» ha solo una
bozza, e bastava a togliere lo standard: da lì ogni stampa dell'emittente si fermava con «nessuna
versione pubblicata».

**La regola.** Un modello è un candidato solo se **può stampare**: è attivo e ha una versione
`PUBBLICATA`, attiva e valida alla data operativa (`validita @> script.fn_data_operativa()`). Sono i
filtri di `get_versione_pubblicata_attiva` del BE.

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/documenti/20261020-26-update-fn-risolvi-template-applicabile-solo-stampabili` | la regola nei tre passi; firma, `STABLE` e `SECURITY INVOKER` invariati (`CREATE OR REPLACE`) |

* **Passo 1, la deduzione del tipo**: contano solo i candidati, come proposto. Una bozza di un altro
  tipo non rende più ambigua una sorgente che stampa con un tipo solo.
* **Passo 2, il livello EMITTENTE**: il conteggio e la scelta del predefinito leggono gli stessi
  candidati. Un modello stampabile non predefinito accanto a un predefinito in bozza dà
  `E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO`.
* **Passo 3, il livello STANDARD — P-1, ✅ confermato da Tid (2026-10-20).** La richiesta diceva «nessun cambio: lo
  standard nasce pubblicato dal seed». L'ho messo anche qui. Il modello ammette uno standard
  predefinito senza una versione valida oggi: una versione spenta, o un'evoluzione pubblicata da
  una data futura. In quel caso la risposta giusta è `E_DOCUMENTI_TEMPLATE_NON_RISOLTO`, il cui
  rimedio è del sistema. Senza il filtro la funzione restituirebbe uno standard che poi fallisce
  alla stampa con un codice generico. In più un candidato si definisce una volta sola, per tutti i
  livelli. Se Tid preferisce la lettera della richiesta, si toglie il filtro dalla sola parte
  standard della lettura del passo 2.
* **La forma.** I passi 2 e 3 sono una lettura sola (conteggio dei candidati dell'emittente, il suo
  predefinito, il predefinito standard), con il `max()` protetto da
  `uq_template_documenti_default_attivo`. Nel contesto di `SENZA_PREDEFINITO` la chiave
  `modelli_attivi` diventa `modelli_stampabili`. Il BE non la legge: `risolvi_template_applicabile`
  seleziona solo `template_documento_id, livello`.
* **Al BE**: `error_policies_generated.py` ricopia le note dei codici, che cambiano: va
  rigenerato (solo commenti, nessuna classe cambia). I test DB del BE
  (`test_template_standard_db.py`) usano lo standard del seed, che è pubblicato: non cambiano esito.
  ⚠️ *Smentito dalla corsa (sessione BE, 2026-10-20):* il caso 3 (strada B) creava il modello
  **dell'emittente** senza versioni, e con la `-26` quel modello non conta più: la risoluzione dava
  `STANDARD` e il test era rosso. Adeguato: il modello riceve una bozza, il test prova che con la sola
  bozza resta lo standard (il difetto di «personalizza» che ha motivato la `-26`), poi la pubblica
  da `TemplateVersioniAdminService` e vuole `E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO` (409). Verde su
  dbdev, 4/4.
* **Codici**: nessuno nuovo. Aggiornate le note di `SENZA_PREDEFINITO`, `NON_RISOLTO` e `AMBIGUO`
  (`codici_errore.csv`) e la causa e la soluzione di `SENZA_PREDEFINITO` e `NON_RISOLTO`
  (`messaggi_errore.csv`). Il testo dei messaggi non cambia.
* **Manuali**: `fn_risolvi_template_applicabile.md` (§ «Conta solo un modello che può stampare»),
  `template_documenti.md` (§ «Il modello standard»).

**P-2 — ✅ decisa da Tid (2026-10-20) e fatta: `20261020-27`, §9.5. La funzione restituisce anche la versione.** Ora «può stampare» è scritto in due
livelli: nel DB, che sceglie il modello, e nel BE (`get_versione_pubblicata_attiva`), che ne carica
la versione con gli stessi filtri. Se le due copie divergono, la funzione sceglie un modello che il
BE poi non riesce a stampare. La forma che chiude la copia: `RETURNS TABLE` con anche
`template_versione_id`, la versione stampabile del modello scelto, e il BE la usa invece di
ricercarla. Cambia la firma di ritorno (`DROP` + `CREATE`). Il BE chiama già la funzione
(`risolvi_template_applicabile`, dal 2026-10-20), ma seleziona le colonne per nome: una colonna in
più in coda non lo rompe, e il BE passa alla versione restituita quando vuole, ritirando nello stesso
giro i filtri di `get_versione_pubblicata_attiva` usati per la stampa. Decide Tid.

**pgTAP** (`test-documenti-template-standard-v1.sql`, da 30 a 35 test; la risoluzione è 11-23):

* 12) modello dell'emittente attivo e predefinito con la sola bozza → `STANDARD`;
* 13) lo stesso modello, pubblicato con `fn_pubblica_template_documento_versione` → `EMITTENTE`;
* 14) un modello stampabile non predefinito più un predefinito in bozza → `SENZA_PREDEFINITO`;
* 15) versione pubblicata ma spenta → non conta, `STANDARD`;
* 17) versione pubblicata con `valido_dal` fra trenta giorni → non conta, `STANDARD`;
* 19) tipo non indicato, una bozza di un altro tipo → dedotto, non `AMBIGUO`;
* 22) standard predefinito con la sola bozza → `NON_RISOLTO` (P-1).

La fixture dà ora una versione pubblicata ai due standard di prova (le versioni dello standard
salgono prima della risoluzione), e aggiunge un quarto emittente (E4) per la data futura.

**La prova (2026-10-20, da owner, in transazione annullata, SQL estratto dallo YAML).**

* Scratch `zeroerp_ruoli` e dbdev: il file 35/35 con il changeSet. Senza, sono rossi i test 12, 14,
  15 e 17, e il 19 interrompe il file con `AMBIGUO`: è il corpo vecchio.
* Stessi esiti prima e dopo su tutti i pgTAP di `documenti/` (i rossi da owner preesistenti,
  `documenti-generati-eventi` 16 e il file app 1-5 per costruzione, sono identici) e sui presidi
  `test-catalogo-messaggi-errore-completo`, `test-permessi-funzioni-risoluzione`,
  `test-security-definer-search-path-v1`, `test-vw-codici-errore-motivo-nominato`,
  `test-vw-codici-errore-valore-atteso`, `test-plan-cache-mode-piano-generico-v1`,
  `test-rubinetto-primo-motivo-v1`, `test-riferimenti-morti-v1`, `test-stati-check-scrittori-v1`.
* Fatto datato, non una prova: su dbdev, il 2026-10-20, nessuna delle 24 combinazioni
  emittente × (tipo, sorgente) cambia risposta. I casi nuovi li prova il pgTAP, costruiti.
* Il seed dei codici non è stato esercitato: cambiano solo le colonne `note`, `causa` e
  `soluzione`, che nessun test confronta.
* Dopo ogni corsa, `md5(pg_get_functiondef)` della funzione è uguale a prima, e non resta nessuna
  riga `pgtap-%`.

## 9. La coda di stampa delle fatture dice che cosa stampare (2026-10-20)

> **Chi scrive:** la richiesta è della sessione BE (2026-10-20); le risposte sono della sessione DB
> (`dev/db-tid`), scritte sulla struttura (doc `dbzero`, corpi delle funzioni, scrittori nel
> changelog e nel BE). È il disegno: nessun changeSet scritto. Il via lo dà Tid (§9.3).

### 9.1 Il caso

Il worker della coda (`stampa_coda_drainer_service`) chiama `genera_documento` senza il tipo di
documento, perché la riga della coda non lo porta. Con il tipo NULL,
`fn_risolvi_template_applicabile` accetta un solo candidato; con due solleva
`E_DOCUMENTI_TEMPLATE_AMBIGUO`. Il modello ammette più tipi di output per la stessa sorgente (il
predefinito unico è per terna, §4.1 Q-2), quindi il giorno in cui la sorgente FATTURA ha modelli di
due tipi, ogni riga della coda va in errore tecnico. È un difetto del modello della coda, non un
caso futuro.

**Decisioni già prese da Tid** (riportate dal BE): colonna nuova `tipo_documento_output_id` sulla
coda, nullable, con FK, scritta da chi accoda. NULL vuol dire «decide il DB, se il candidato è
uno», cioè la semantica di oggi: le righe esistenti e gli accodamenti di oggi non cambiano
comportamento. L'unicità delle righe vive si decide insieme alla colonna.

**I fatti di struttura**, verificati (doc `dbzero`, 2026-10-20):

* `vendite.fatture_stampa_coda` porta `sorgente_tipo_id`, `sorgente_id`, `template_documento_id`
  (nullable, l'override del modello). ⚠️ `template_documento_id` non ha FK, e nemmeno
  `documento_id` (già segnalato in `valutazione-modello-di-dominio-db`; fuori da questa richiesta).
* **Un solo scrittore di righe**: `vendite.fn_accoda_stampe_lotto(p_lotto_id)`, chiamata dal task
  di pipeline `stampa_documenti_lotto` (`pipeline_repository.accoda_stampe_lotto`). Non scrive né il
  modello né il tipo: l'override esiste solo sulla carta. Gli altri scrittori (claim, reaper, esito,
  archiviazione) fanno solo `UPDATE` di stato fra `PENDING`, `IN_CORSO`, `FATTO` ed `ERRORE`, e non
  toccano modello e tipo.
* `uq_fatture_stampa_coda_vivo`: unico su `(sorgente_tipo_id, sorgente_id)`, parziale su
  `PENDING`/`IN_CORSO`. `fn_accoda_stampe_lotto` lo nomina per colonne nell'`ON CONFLICT … DO
  NOTHING`.
* `documenti.tipi_documento_output` non ha legami con la sorgente. Quali tipi una sorgente può
  stampare lo dicono solo i modelli.
* `template_documenti`: `tipo_documento_output_id` e `sorgente_tipo_id` sono `NOT NULL` e non sono
  nel registro dei lock.

### 9.2 Le risposte

**Q-1 — Il tipo arriva da un parametro di `fn_accoda_stampe_lotto`, non dal lotto.**

* Firma `fn_accoda_stampe_lotto(p_lotto_id bigint, p_tipo_documento_output_id bigint DEFAULT
  NULL)`. Il parametro va in coda, e il default riproduce l'accodamento di oggi.
* **Perché non il lotto.** Il lotto è un insieme fiscale: emittente, tipo di documento fiscale,
  competenza. Dice **quali** fatture, non **che cosa** stampare. Se una fattura deve produrre due
  documenti, sul lotto servirebbe un elenco, cioè una tabella in più. Con il parametro sono due
  chiamate, ognuna idempotente sul suo tipo. E il tipo sta in una sede sola, la riga, quindi non
  c'è da decidere quale dei due vale.
* **Nessun controllo «tipo stampabile per la FATTURA» all'accodamento.** L'esistenza la dà la FK;
  se il tipo può stampare lo decide la risoluzione al drenaggio (`E_DOCUMENTI_TEMPLATE_NON_RISOLTO`
  sulla riga). Ripeterlo qui sarebbe una seconda copia della regola di `fn_risolvi_template_applicabile`.
* Forma: `DROP` della firma vecchia e `CREATE`, perché un parametro in più crea un overload.
  Grant da ricontrollare; il pgTAP `test-stampa-coda-fondamenta-v1` (13, `has_function(…,
  ARRAY['bigint'])`) passa alla firma nuova.
* Chi passa il tipo: il task di pipeline, nel BE. Oggi non lo passa nessuno, quindi NULL e nessun
  cambio di comportamento.

**Q-2 — Una regola sola, scritta come vincolo di esclusione: «una riga col tipo NULL esclude le
altre righe vive della stessa fattura».**

Per una fattura, le righe vive sono **o** una col tipo NULL, **o** più righe con tipi diversi. Il
NULL vuol dire «qualunque tipo il DB risolva», quindi si sovrappone a tutti. Se il DB risolve il
NULL in X, la riga NULL e la riga X sarebbero la stessa stampa; se non lo risolve, la riga NULL
fallisce comunque con `AMBIGUO`. In nessun caso le due righe hanno senso insieme.

```sql
CONSTRAINT ex_fatture_stampa_coda_vivo
    EXCLUDE USING gist (
        sorgente_tipo_id WITH =,
        sorgente_id WITH =,
        int8range(tipo_documento_output_id, tipo_documento_output_id, '[]') WITH &&)
    WHERE (stato IN ('PENDING', 'IN_CORSO'))
```

* `int8range(NULL, NULL)` è l'intervallo illimitato: si sovrappone a ogni tipo, ed è proprio «il
  NULL esclude le altre». Un tipo valorizzato è un intervallo di un punto: due tipi diversi
  convivono, due uguali no. Un solo vincolo dice le tre regole (un NULL per fattura, tipi distinti,
  NULL contro tipati). Sul tipo l'intervallo serve anche con `=` disponibile: con `=` due NULL non
  sono mai in conflitto, e il NULL non escluderebbe niente.
* Il `=` sulle due colonne `bigint` della sorgente in un indice gist richiede `btree_gist`, che c'è
  già: la crea `20260224-01-create-listini-core` e la usano i vincoli di esclusione di listini,
  contratti, promo, sospensioni e conti d'incasso. Il changeSet porta la stessa `preCondition` di
  quei file (`pg_extension` con `btree_gist`). ⚠️ *Corretto il 2026-10-20: la prima stesura diceva
  che l'estensione non era installata e scriveva anche la sorgente come intervalli; l'errore veniva
  dall'elenco delle estensioni di `PROJECT_CONTEXT.md`, che non la nomina.*
* **Perché non un trigger.** Un guard `BEFORE ROW` che legge le altre righe non regge a due sessioni
  concorrenti che accodano la stessa fattura; il vincolo sì.
* **Perché non il tipo obbligatorio.** Contraddice la decisione di Tid sul NULL, e costringerebbe a
  risolvere il tipo all'accodamento: una sola fattura ambigua fermerebbe l'accodamento dell'intero
  lotto.
* **L'`ON CONFLICT`.** Un vincolo di esclusione ammette solo `ON CONFLICT DO NOTHING` **senza**
  bersaglio. Nel changeSet cambiano insieme il vincolo (al posto di `uq_fatture_stampa_coda_vivo`)
  e la funzione. L'unico altro vincolo che l'`INSERT` può incontrare è la chiave primaria, che è
  generata. La semantica resta quella di oggi: una riga viva che copre già la fattura vince, e il
  valore di ritorno conta solo le righe nuove. Il caso «X accodato mentre è viva una riga NULL» si
  chiude da solo: se il candidato è uno, la riga NULL stampa proprio quello; se sono due, la riga
  NULL arriva a `ERRORE` per `AMBIGUO`, e il riaccodamento con il tipo passa.
* **Sul database che c'è.** Le righe vive di oggi hanno tutte il tipo NULL e sono già una per
  fattura (lo garantiva l'indice vecchio), quindi il vincolo nasce valido per costruzione, non per
  conteggio.
* Ricadute di testo: la manuale di `fatture_stampa_coda` («Un solo work-item vivo», «Archiviare una
  riga») e quella di `fn_accoda_stampe_lotto` nominano l'indice; la nota di
  `E_CODA_ARCHIVIAZIONE_NON_AMMESSA` in `codici_errore.csv` pure, e la ricopia
  `error_policies_generated.py` (da rigenerare, solo commenti). Il test 10 di
  `test-stampa-coda-fondamenta-v1` controlla l'indice per nome e passa al vincolo
  (`contype = 'x'` e la clausola, non solo il nome).
* **La prova** (2026-10-20, cluster PG18 usa-e-getta, tabella di prova con la sola forma del
  vincolo, non lo schema vero): due tipi convivono; doppione, NULL contro tipati e tipato contro
  NULL vanno in `DO NOTHING`; dopo `FATTO` si riaccoda; un `INSERT` senza `ON CONFLICT` in
  conflitto dà `23P01`. La prova usava la forma della prima stesura, con anche la sorgente come
  intervalli: la parte che decide (il tipo come intervallo, il NULL illimitato) è la stessa, ma la
  forma con `=` va riprovata nello sviluppo.

**Q-3 — L'override porta il tipo, e una FK composta tiene insieme modello, tipo e sorgente.**

* `CHECK (template_documento_id IS NULL OR tipo_documento_output_id IS NOT NULL)`: chi indica il
  modello indica anche il tipo.
* FK composta `(template_documento_id, tipo_documento_output_id, sorgente_tipo_id)` →
  `documenti.template_documenti (id, tipo_documento_output_id, sorgente_tipo_id)`, con un `UNIQUE`
  nuovo su quelle tre colonne di `template_documenti` (un sovrainsieme della chiave primaria). È
  anche la FK mancante su `template_documento_id`. Più una FK semplice
  `tipo_documento_output_id` → `tipi_documento_output`.
* **Perché il CHECK.** Una FK composta `MATCH SIMPLE` non si controlla affatto se una delle colonne
  è NULL: un override col tipo NULL passerebbe senza verifica della sorgente. Col CHECK, quando c'è
  l'override ci sono sempre tutte e tre le colonne. E il tipo scritto fa lavorare il vincolo di Q-2
  sul tipo vero: un override col tipo NULL bloccherebbe ogni altro tipo per quella fattura.
* Nel changeSet, prima del CHECK, le righe con l'override e senza tipo prendono il tipo dal modello.
  Lo scrittore di oggi non scrive l'override, ma il changeSet deve reggere su ogni database. Un
  override che punta a un modello inesistente (la FK non c'era) fa fallire il changeSet: è un dato
  da correggere a mano, non da cancellare in silenzio.
* **L'emittente dell'override non si controlla in coda.** La regola 4 di
  `trgfn_documenti_generati_check_coerenza` («stesso emittente, oppure standard», §4.1 Q-3) lo
  controlla alla generazione. Un guard all'accodamento ne sarebbe una seconda copia.
* Effetti da sapere: con la FK composta (`NO ACTION`), il tipo o la sorgente di un modello citato
  dalla coda, righe `FATTO` comprese, non si cambiano più. Mi sembra corretto: lo stesso vale già
  per i modelli citati da `documenti_generati`. Da `ci_apply`, l'automazione ATTIVO genererà i
  trigger del padre attivo sulle FK nuove (si accoda solo con un tipo e un modello accesi). Per la
  FK composta va verificato nel corpo, non dato per scontato. Poi la policy degli indici FK in
  `90_end` e lo storico scope.

**Q-4 — pgTAP: `vendite/test-stampa-coda-tipo-documento-v1.sql`, su casi costruiti.**

La fixture costruisce un secondo tipo di output (`pgtap-%`) e un modello di quel tipo per la
sorgente FATTURA, accanto al modello del tipo FATTURA_VENDITA, poi una fattura in un lotto.

1. accoda col tipo X e col tipo Y → due righe vive;
2. riaccoda X → 0 nuove;
3. accoda col tipo NULL con X viva → 0, nessuna riga;
4. un'altra fattura con una riga NULL viva, accoda X → 0;
5. dopo `FATTO`, riaccoda X → una riga nuova;
6. un `INSERT` diretto in conflitto → `23P01` (il vincolo regge anche senza la funzione);
7. override con un tipo diverso da quello del modello → `23503`; override senza tipo → `23514`;
8. override col modello di un'altra sorgente → `23503`;
9. struttura: il vincolo è un'esclusione parziale sui due stati vivi; la firma `(bigint, bigint)`
   esiste e `(bigint)` no.

Il rifiuto `AMBIGUO` col tipo NULL e due candidati lo prova già
`test-documenti-template-standard-v1`: non si ripete qui.

### 9.3 Decisioni di Tid

✅ **Decise il 2026-10-20: C-1, C-2 e C-3 come da proposta**, e via allo sviluppo (insieme a P-1 e
P-2). Sviluppo nel §9.5.

* **C-1** — Il tipo arriva da un parametro di `fn_accoda_stampe_lotto` e non dal lotto (Q-1).
* **C-2** — Il vincolo di esclusione al posto dell'indice unico, con `DO NOTHING` anche sul caso NULL
  contro tipato (Q-2).
* **C-3** — Il CHECK «l'override porta il tipo» e la FK composta (Q-3).

### 9.4 Ricaduta sul BE (dopo l'apply; la fa la sessione BE)

* `claim_stampe_pending` aggiunge `tipo_documento_output_id` al `RETURNING`; il worker lo passa a
  `genera_documento(tipo_documento_output_id=…)`.
* `accoda_stampe_lotto` passa il tipo dove il task lo conosce (secondo parametro, per posizione).
* Nessun codice nuovo: il rifiuto `AMBIGUO` esiste già. Da rigenerare `error_policies_generated.py`
  se cambia la nota di `E_CODA_ARCHIVIAZIONE_NON_AMMESSA`.
* ➕ **Cambiata (§9.5):** la nota di `E_CODA_ARCHIVIAZIONE_NON_AMMESSA` nomina ora
  `ex_fatture_stampa_coda_vivo`, quindi `error_policies_generated.py` va rigenerato (solo un
  commento). I commenti di `pipeline_repository.py` che nominano `uq_fatture_stampa_coda_vivo`
  (claim) vanno aggiornati.
* ➕ **P-2 (§8.4):** `risolvi_template_applicabile` seleziona anche `template_versione_id`, e la
  stampa usa quella versione invece di `get_versione_pubblicata_attiva`. Nello stesso giro si
  ritirano i filtri di stampa di quel metodo, se la stampa era il suo solo uso (regola del 2). La
  colonna è in coda: fino a quel giro il BE non si rompe.

### 9.5 Sviluppo (2026-10-20; ✅ applicato da Tid su scratch e dbdev, pgTAP verdi, nessuna regressione)

| ChangeSet | Che cosa | Risposta |
| --- | --- | --- |
| `20_code/documenti/20261020-27-update-fn-risolvi-template-applicabile-con-versione` | `fn_risolvi_template_applicabile` restituisce anche `template_versione_id` (`DROP` + `CREATE`: cambia il `RETURNS TABLE`, gli argomenti no). La lettura dei passi 2 e 3 va da `EXISTS` a `JOIN` sulla versione stampabile: candidato e versione escono dalla stessa riga, e il predicato resta scritto due volte, come prima | P-2 |
| `00_schema/documenti/20261020-28-add-uq-template-documenti-id-tipo-sorgente` | `UNIQUE (id, tipo_documento_output_id, sorgente_tipo_id)` su `template_documenti`: il bersaglio della FK composta | Q-3 |
| `00_schema/vendite/20261020-29-alter-fatture-stampa-coda-tipo-documento-output` | colonna `tipo_documento_output_id` con FK; il tipo preso dal modello per le righe con l'override; `chk_fatture_stampa_coda_modello_con_tipo`; `fk_fatture_stampa_coda_template_documento` (composta); `ex_fatture_stampa_coda_vivo` | Q-2, Q-3 |
| `20_code/vendite/20261020-30-update-fn-accoda-stampe-lotto-tipo-documento` | `fn_accoda_stampe_lotto(p_lotto_id, p_tipo_documento_output_id DEFAULT NULL)`, `ON CONFLICT DO NOTHING` senza bersaglio, `SECURITY INVOKER` esplicito (`DROP` della firma `(bigint)` + `CREATE`) | Q-1, Q-2 |
| `00_schema/vendite/20261020-31-drop-uq-fatture-stampa-coda-vivo` | il ritiro dell'indice vecchio, **dopo** la `-30`: fino a lì l'`ON CONFLICT` della funzione di prima lo nominava | Q-2 |

**Dati (tre righe di CSV):**

* `dbops/automazione_attivo_eccezioni.csv`: `vendite.fatture_stampa_coda.tipo_documento_output_id`.
  L'automazione ATTIVO avrebbe generato su questa FK un trigger REQUIRE che scatta su **ogni**
  `UPDATE` della riga (`trgfn_child_requires_active_parent` non guarda se la FK è cambiata). Con
  un tipo spento il claim del worker, che è una `UPDATE` sola su N righe, si sarebbe fermato per
  tutto il lotto. E il BLOCK sul padre avrebbe impedito di spegnere un tipo finché una riga storica
  lo nomina. Se il tipo può stampare lo decide la risoluzione al drenaggio. La FK composta non ha
  bisogno di eccezioni: l'automazione considera solo le FK a una colonna;
* `dbops/stati_check_dichiarazioni.csv`: `fatture_stampa_coda.stato = IN_CORSO`, canale
  `APPLICAZIONE` (lo scrive il claim del BE). ⚠️ Lo ha fatto emergere la prova: fino a oggi il
  presidio lo dava scritto dal DB perché la vecchia `fn_accoda_stampe_lotto` nominava il valore
  nell'`ON CONFLICT … WHERE stato IN ('PENDING', 'IN_CORSO')`. Nominare non è scrivere: è la stessa
  coincidenza testuale della riga di `magazzino.inventari` del 2026-09-22;
* `config/codici_errore.csv`: la nota di `E_CODA_ARCHIVIAZIONE_NON_AMMESSA` nomina il vincolo nuovo.

**pgTAP:**

* nuovo `vendite/test-stampa-coda-tipo-documento-v1.sql` (14 test, **come app**): i casi di Q-4 su
  un lotto e due fatture costruiti dal test; i tipi e i modelli dell'override sono quelli del seed,
  cercati per `codice_interno`. Il rifiuto `AMBIGUO` resta a `test-documenti-template-standard-v1`
  (20);
* `vendite/test-stampa-coda-fondamenta-v1.sql`: il 10 guarda il vincolo di esclusione con la sua
  clausola (`pg_get_constraintdef`), non più l'indice; il 13 e il 14 la firma `(bigint, bigint)`;
* `documenti/test-documenti-template-standard-v1.sql` (da 35 a 36): l'11 e il 13 chiedono anche
  la versione (prima chiedevano solo modello e livello); il 36 è nuovo: due versioni pubblicate di
  un modello, una sola valida oggi, e la funzione restituisce quella.

**Manuali:** `documenti/manual/fn_risolvi_template_applicabile.md` (§ «Dice anche con quale
versione si stampa»), `vendite/manual/fatture_stampa_coda.md` (il tipo, l'override, il vincolo
delle righe vive), `vendite/manual/fn_accoda_stampe_lotto.md` (il parametro, l'idempotenza).
`PROJECT_CONTEXT.md`: `btree_gist` aggiunta all'elenco delle estensioni.

**Scelte dichiarate, oltre al §9.2:**

* nessuna riga di `fk_index_policy` per le due FK nuove (la policy è opt-in): puntano a cataloghi
  piccoli, e il loro controllo scatta solo quando si cancella o si cambia una riga del catalogo;
* `tipo_documento_output_id` e `template_documento_id` non vanno nel registro dei lock: oggi
  nessuno li cambia dopo l'INSERT. Se servirà, sarà una riga di `automation_lock_columns`.

**La prova (2026-10-20).**

* **Prima dell'apply**, sullo scratch `zeroerp_ruoli`, da owner, in transazione annullata, con
  l'SQL estratto dagli YAML: le cinque `preConditions` danno il valore atteso, e il DDL gira anche
  su dbdev, dove la coda ha già delle righe (il vincolo nasce valido). 36 pgTAP prima e dopo:
  stessi esiti, salvo i previsti (fondamenta 10, 13 e 14; il file della risoluzione dall'11; il
  file nuovo). L'unica differenza non prevista era `stati-check-scrittori` 2, che ha portato alla
  riga `IN_CORSO` sopra.
* ⚠️ **Durante la prova Tid ha applicato** (`databasechangelog`: dbdev 11:51, scratch 11:52; su
  dbdev un secondo migrate alle 11:53 ha caricato la riga `IN_CORSO`, aggiunta al CSV dopo il
  primo). Le corse «dopo» con l'SQL estratto successive all'apply non valgono, e non le conto.
* **Dopo l'apply**, gli stessi 36 file sui due database, senza SQL estratto: tutti verdi tranne i
  rossi già noti e uguali a prima, cioè `documenti-generati-eventi` 16 e il file app 1-5 (rossi da
  owner per costruzione). Su dbdev `test-documenti-template-documenti` si interrompe al primo
  INSERT: il test crea un predefinito per l'emittente 32, che su dbdev ne ha già uno suo per la
  stessa terna (modello 40, del 2026-05-04). Il vincolo che scatta,
  `uq_template_documenti_default_attivo`, non è di questo giro: sullo scratch il file è verde. È un
  test che pesca i dati della macchina, e va segnalato a parte.
* Dopo ogni corsa nessuna riga `pgtap-%` è rimasta sui due database, e le righe della coda su
  dbdev sono le stesse di prima.
* ⚠️ Il file nuovo, da owner, non esercita la RLS. ✅ La corsa di Tid (2026-10-20): pgTAP verdi,
  nessuna regressione.
* Non provati: il loader dei CSV (simulato con degli `INSERT` prima dell'apply, poi caricato
  dall'apply vero) e le automazioni di `ci_apply` (l'eccezione ATTIVO si vede solo lì).
