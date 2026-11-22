# Brief DB — la regola ATTIVO sulle FK senza `_id`

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-21. **A chi:** Tid per le decisioni; poi team DB.
> **Stato:** giro DB applicato da Tid coi pgTAP verdi il 2026-11-22 (§9); tutte le decisioni prese (D-1,
> D-2, D-4, D-5, D-6 il 2026-11-21; D-3 sulle righe incerte il 2026-11-22). Revisione FK per FK chiusa (§3.2).
>
> **Brief vicini verificati** (rifatto il 2026-11-21 sugli **oggetti**, non solo sul filtro): nessuno
> in `work-in-progress/` tocca il filtro `_id` del motore ATTIVO; due toccano FK dell'elenco del §2.
>
> * [brief-db-revisione-ui](../../work-in-progress/brief-db-revisione-ui.md): scrive anche lui in `automazione_attivo_eccezioni.csv`,
>   coi giri 5-6 ancora da fare. Le righe del CSV si aggiungono per sostituzione del testo attuale.
>   ⚠️ *Correzione del 2026-11-21 (§3.2): qui si leggeva che toccava «le FK di `ui` (`ambito`, `vista`)».
>   Non è così: `ambito` è di `config.tipi_indirizzi_allowed`, `vista` di `dbops.presidi_*`, e nessuna FK
>   di `ui` è nell'elenco. Il vicino è solo il CSV in comune.*
> * [analisi-db-magazzino-carico-e-scarico](../../work-in-progress/analisi-db-magazzino-carico-e-scarico.md):
>   `ubicazione_id_da`/`_a`, `causale_magazzino`, `stato_lotto`. Si incrociano due voci aperte del
>   PROJECT_CONTEXT, «La matrice di `stato_lotto` in due sedi che dissentono» e «La porta dell'esito
>   ancora aperta» (le FK `esito*`): la revisione di quelle FK chiede a Tid se aspetta i due cantieri.
>
> * [brief-db-fornitore-doppioni-del-soggetto](brief-db-fornitore-doppioni-del-soggetto.md) (aggiunto il
>   2026-11-22, su segnalazione della sessione del fornitore): il registro delle inclusioni nasce dalla sua D-6/D-7
>   (§7.2). Il giro D-8 dello stesso brief (§7.4, Tid 2026-11-22) tocca oggetti di questo giro: il motivo
>   `pgtap-runner` di `dbops/test-automazione-attivo-inclusioni-v1.sql` e `config/manual/regimi_fiscali.md`
>   (un paragrafo nuovo in «Come si cambia»). Quando parte il §5, quei due file si riprendono dal testo
>   attuale, per sostituzione. Se il pgTAP si ritira o si riscrive, il motivo aggiornato va portato con sé.
>   ⛔ Il BLOCK sul regime resta voluto (D-7 «2»): con D-1 deve nascere da solo, ed è una delle 36 FK legate
>   del §3.2. Al commit, i file del giro D-8 restano separati da questo brief.
>
> Nessuno di questi basta a ospitare questo lavoro: il tema qui è la regola del motore, che vale per
> tutte le FK. Il registro delle inclusioni nasce nel commit `790fc04325` (regime fiscale, la D-6 di
> quel giro, non la D-6 di questo brief), dalla D-6/D-7 di `brief-db-fornitore-doppioni-del-soggetto` §7.2.
> ⚠️ *Correzione del 2026-11-22: qui si leggeva «che non ha un brief».*

## ⏭️ Chi riparte — aggiornato al 2026-11-22

**Brief chiuso e archiviato (sessione DB, 2026-11-22, §10). Non riparte nessuno**: il lavoro BE/FE del §6.1 è
committato (`ebd81ec653`, in `Tito-dev` con la PR #194), e al DB il BE/FE non chiede niente. Il giro DB è
applicato da Tid coi pgTAP verdi (2026-11-22, §9): 36 FK si legano (68 trigger nuovi, nessuno in più), 13 vanno fra
le eccezioni, il registro delle inclusioni è ritirato.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ Tid | D-1 «a», D-2 «b», D-3 come metodo (2026-11-21) | §4 | — |
| 2 | ✅ sessione DB | La prova sullo scratch delle FK ereditate da una tabella partizionata (2026-11-21) | §3.1 | 1 |
| 3 | ✅ Tid | D-4 «a», D-5 «a», D-6 come proposta, caso inverso «sì» (2026-11-21) | §4 | 2 |
| 4 | ✅ sessione DB | La revisione FK per FK, sulla radice per le ereditate (2026-11-21) | §3.2 | 3 |
| 5 | ✅ Tid | D-3 sulle 6 incerte: si legano, senza aspettare i cantieri vicini (2026-11-22) | §3.2 | 4 |
| 6 | ✅ sessione DB | Il giro scritto e provato in `ROLLBACK` (2026-11-22) | §9 | 5 |
| 7 | ✅ Tid | Apply di `20261121-21` … `-25` e i pgTAP del §9.3, verdi (2026-11-22) | §9 | 6 |
| 7-bis | ✅ Tid | Il commit del giro e la rigenerazione della doc auto-generata (2026-11-22) | §9.4 | 7 |
| 8 | ✅ team BE/FE | I codici d'errore sulle maschere toccate, e il censimento dei lettori (2026-11-22): cinque legami del campo, il `campiErrati` dei tab dell'editor dei workflow, quattro prove sul DB vero. Committato (`ebd81ec653`, PR #194) | §6.1 | 7 |
| 9 | ✅ sessione DB | Tolta la pagina `manual/` del registro ritirato e la sua voce in `dbops/index.ci.md` (2026-11-22) | §9.4 | 7-bis |
| 10 | ✅ sessione DB | Chiusura e archiviazione del brief (2026-11-22): nessuna correttiva chiesta dal BE/FE, nessun debito | §10 | 8 |

Decisioni aperte di Tid: nessuna. Il giro DB (changeSet, CSV, pgTAP, doc) e il lavoro BE/FE del §6.1 sono
committati; da committare solo l'archiviazione.

## 1. Il problema

Il motore ATTIVO (`dbops.fn_run_automations_attivo`) mette la coppia di regole su ogni FK a una
colonna verso un padre con `attivo`:

* **require** sul figlio: a un figlio acceso non si dà un padre spento (`E_ATTIVO_PADRE_NON_ATTIVO`);
* **block** sul padre: un padre che un figlio acceso usa non si spegne (`E_ATTIVO_BLOCK_CHILDREN_ACTIVE`).

Ma salta, **in silenzio**, ogni FK la cui colonna non finisce in `_id`
(`dbops.fn_attivo_fk_esclusa`, risposta `FK_NO_ID_SUFFIX`). Quel filtro è un'**esclusione
implicita**: niente elenco, niente motivo, e chi crea una FK senza `_id` non sa di averla lasciata
fuori.

Va contro il principio di Tid del 2026-11-04: le regole si fanno **per esclusione**. Un'eccezione
dimenticata si vede, perché la regola scatta e dà errore. Un'inclusione dimenticata no: la regola
manca e nessuno se ne accorge.

Il registro `dbops.automazione_attivo_inclusioni` (2026-11-21, regime fiscale) è una pezza **per
inclusione** sopra quel filtro. Questo cantiere la rende inutile.

### 1.1 Da dove viene il filtro (verificato il 2026-11-22, `git log -S`)

Il filtro **non** nasce da una decisione di modello: era un **ripiego tecnico**, e il limite che
copriva è stato tolto ad aprile.

* **2026-01-15, commit `1f0ff0fdf2`** (changeSet `20260113-04-update-fn-run-automations-attivo-require`).
  Nasce il passo «2.1) applica automations solo su FK con suffisso _id», senza nessun motivo scritto
  (né nel changeSet né nella guida). Il runner di allora passava alla funzione trigger la **PK del
  padre** («PK monocolonna del padre (fallback 'id')»), non la colonna che la FK referenzia. Su una FK
  verso un codice il trigger avrebbe cercato il padre per `id` con un valore di codice, e non avrebbe
  funzionato. Il suffisso `_id` faceva da indizio per «questa FK punta alla PK»: un modo per stare
  sul caso che il runner sapeva trattare.
* **2026-04-08, commit `7e51d01575`**: il runner e le due funzioni trigger passano alla **colonna
  realmente referenziata** dalla FK («può essere una UNIQUE diversa dalla PK»: `confkey`, non la PK).
  Da qui il motivo tecnico non c'è più, ma il filtro resta.
* **2026-11-21**: la prova sui due `regime_fiscale_rf` conferma che il runner lega una FK verso una
  UNIQUE non primaria (§2).

* **2026-10-19, due changeSet si appoggiano al filtro** (trovati dalla verifica del 2026-11-22): ne
  scrivono l'effetto come voluto («la FK lega il NOME, non l'accensione»), senza dargli un motivo suo.
  `20261019-15` (`config.tipi_entita.sorgente_codice_interno` → `config.sorgenti`) è fra le 13 eccezioni
  del §3.2, col motivo del COMMENT di tabella. `20261019-87` (`vendite.ordini.documento_origine_tipo`)
  parla di una colonna tolta da `20261106-96`.

Quindi D-1 non **revoca** una decisione: toglie un ripiego rimasto dopo che il limite era stato
corretto. Nessun brief in `work-done/` e nessuna guida dà al filtro un motivo di modello; i due changeSet
del 2026-10-19 ne usano l'effetto, e quello vivo diventa un'eccezione dichiarata.

**Cosa si generalizza, e cosa no.** Il comportamento «un padre usato da un figlio acceso non si spegne,
e un figlio acceso non sceglie un padre spento» **non è nuovo**: è la regola ATTIVO che vale già per
ogni FK con `_id` nel perimetro del motore. D-1 la estende alle 36 FK che il nome escludeva, e le
eccezioni (13, §3.2) restano dove il modello dice altro. La forma più forte, «usato **una volta**, non
si spegne più», vale dove la figlia non ha `attivo`. Per le 6 FK decise il 2026-11-22 è la stessa scelta
che le loro sorelle con `_id` avevano già.

## 2. Perché esistono FK senza `_id`

La regola dei nomi (`linee-guida-sql.md` §4, «Eccezioni e Alternative») diceva solo di **preferire** colonne
`<tabella>_id`, e solo per non usare le chiavi composte. ⚠️ *Dal 2026-11-22 è una regola obbligatoria, in
`linee-guida-sql.md` §2, «La colonna FK dice che cosa porta» (D-2 «b», D-6).* Le FK senza `_id` sono di due specie.

**a) Puntano all'`id` del padre, con un nome fuori regola.** Il suffisso è un prefisso o sta in mezzo:
`id_lingua`, `id_stile`, `id_iva_split`, `magazzino_id_from`, `magazzino_id_to`, `ubicazione_id_da`,
`ubicazione_id_a`, `assoggettamento_id_override`, `categoria_cliente_id_snapshot`. Sono legami
padre/figlio come gli altri: il motore li salta per il nome, non per il modello. Fuori dal perimetro
ATTIVO, perché il padre non ha `attivo`, la stessa forma hanno anche `id_prov_iscri_rea` e
`classe_utenza_id_snapshot`: contano per D-6 (§4), non per D-1.

**b) Puntano a un codice del padre, per scelta.** È la forma ammessa per gli stati e i cataloghi
(`linee-guida-sql.md`, §Framework `dbops.automazione_chiusura_scadenze`: lo stato come FK a un
catalogo, coi codici in `codice_interno`): `esito`, `esito_richiesto`,
`esito_default`, `regime_fiscale_rf`, `lingua` (→ `codice_iso`), `processo_codice`, `job_type`,
`azione_processo_codename` (→ `permission_codename`), `vista`, `famiglia_documento`, `ambito`,
`causale_magazzino`, `destinazione_tipo`, `stato_lotto`, `sorgente_codice_interno`, `codice_interno`.

Il motore dal 2026-11-21 sa già legare una FK verso una colonna UNIQUE non primaria: è provato sui
due `regime_fiscale_rf`.

**Fatto datato** (dbdev, 2026-11-21; il perimetro lo decide il modello, non questo conteggio): 140
FK a una colonna senza `_id`, 95 verso un padre con `attivo`. Di queste 95, 59 sono della specie a)
(per lo più `id_lingua` e `id_stile` delle 24+24 tabelle `note*`) e 36 della specie b). La query è in §7.

## 3. La revisione FK per FK (dopo D-1)

Ogni FK della specie a) e b) verso un padre con `attivo` riceve una delle due risposte:

* **si lega**: nessuna riga, il motore genera la coppia;
* **eccezione**: una riga in `dbops.automazione_attivo_eccezioni`, col motivo del modello (per esempio:
  «il figlio è uno storico, deve poter citare un padre spento»).

⚠️ **Una figlia senza `attivo` conta per intero** (`dbops.trgfn_prevent_deactivate_if_children`): il
block conta **ogni riga** della figlia e risponde `E_ATTIVO_BLOCK_CHILDREN_EXIST`, e il require vale per
ogni riga. Un padre citato una volta da una figlia senza `attivo` non si spegne più. È il primo dato da
leggere su ogni FK, dalla doc auto-generata della figlia.

### Le famiglie di motivo già decise

La revisione non dà 95 giudizi nuovi: ogni FK si mette prima in una delle famiglie che
`automazione_attivo_eccezioni.csv` porta già, col motivo deciso da Tid. A Tid va solo ciò che non ci
rientra (D-3).

| Famiglia | Il motivo, in breve | Decisione |
| --- | --- | --- |
| Preferenza dell'utente | uno stato dell'utente, non un'entità col suo ciclo di vita; i risolutori ripiegano | Tid 2026-11-08 (revisione-dbops, §23.12) |
| Riga di composizione | una parte, non un figlio: senza `attivo` il padre non si spegnerebbe mai | Tid 2026-11-08 (revisione-dbops, §23.12) |
| Nota d'anagrafica | annota l'oggetto, non lo tiene in vita | Tid 2026-11-08 (revisione-catalogo, Q12) |
| Storia (stampa, log, bozza) | la fotografia del momento; chi può usare cosa oggi lo dice il risolutore | Tid 2026-11-14 (revisione-documenti, Q1); 2026-11-19 (Q24) |
| Si lega | un figlio vivo, con `attivo`, che dipende dal padre | il default di D-1 «a» |

### Da guardare con cura

La coppia cambia cosa si può spegnere:

* ⚠️ *Correzione del 2026-11-21: la riga diceva «una lingua usata da una nota accesa non si spegne».
  Le note non hanno `attivo`.* **Lingue e stili delle note** (`id_lingua`, `id_stile`): con la coppia,
  una lingua o uno stile usati da **una nota qualsiasi** non si spengono più, e una nota in una lingua
  spenta non si modifica più. La famiglia vicina è «nota d'anagrafica», ma lì l'annotato è il padre e
  qui la lingua è un attributo della nota: va deciso (D-3). Con D-4 «a» la coppia resta intera.
  Sono FK ereditate da una tabella partizionata (§3.1), quindi si decidono sulla radice (D-5 «a»).
  ⭐ **Una terza via, ammessa da Tid (2026-11-21): dare alle note la colonna `attivo`**, se la revisione
  la trova necessaria. Con `attivo` sulla nota, il block conta solo le note accese
  (`E_ATTIVO_BLOCK_CHILDREN_ACTIVE`) e il require non chiede niente a una nota spenta: «si lega» diventa
  sostenibile. Si aggiunge sulla radice partizionata e la ereditano le partizioni. Se la si sceglie, la
  revisione deve censire:
  * le righe di `automazione_attivo_eccezioni.csv` su `target_id` delle note, il cui motivo dice «la
    partizione non ha attivo». Il motivo va riscritto, oppure la decisione Q12 del 2026-11-08 va
    riaperta: con `attivo`, un articolo spento con note accese non si spegnerebbe;
  * i lettori delle note lato DB (funzioni, viste) che dovrebbero filtrare le note spente, e la
    richiesta al BE/FE (il campo nel drawer delle note, le liste);
  * le altre automazioni che si accendono sulla colonna `attivo`, che la nota erediterebbe.

  ⚠️ *Esito della revisione (§3.2, 2026-11-21): la terza via non serve.* Con `attivo` sulla nota, per
  spegnere una lingua bisognerebbe spegnere tutte le note scritte in quella lingua. È la stessa
  confusione fra «non si usa più» e «chi l'ha usata si spegne» che l'eccezione evita;
* **cataloghi di configurazione fra loro** (transizioni → permessi, stati → esiti): spegnere una voce
  diventa rifiutato finché un'altra voce accesa la cita;
* ⚠️ *Correzione del 2026-11-21 (§3.2): le due righe che seguono parlavano di FK che il motore non
  vede.* **Giornali e code** (`maintenance.job_run_log.processo_codice`, `dbops.coda_lavori.job_type`):
  stanno **fuori dal perimetro del motore**, come `dbops.presidi_testi.lingua`, quindi D-1 non li tocca
  (§3.2, «Fuori dal perimetro»);
* **`config.messaggi_errore.lingua`**: catalogo seed, da verificare anche sui CSV (§5).

### 3.1 Le FK ereditate dalle tabelle partizionate (provato il 2026-11-21)

`catalogo.note` (e le gemelle degli altri schemi) è partizionata: `fk_cat_note_id_lingua` e
`fk_cat_note_id_stile` stanno sul padre partizionato e ogni partizione le eredita (`conparentid` ≠ 0).
Il cursore di `dbops.fn_run_automations_attivo` non guarda né `conparentid` né `relkind`, quindi tratta
la FK della radice e ogni FK ereditata come FK a sé.

**La prova** (scratch `zeroerp_ruoli`, come `zeroerp_owner`, `scripts/prova_changeset.py` con un estratto
in `ROLLBACK`; catalogo identico prima e dopo). Il soggetto è `catalogo.note.id_lingua` → `config.lingue`:
radice partizionata (`relkind = p`), due partizioni (`note_articoli`, `note_articoli_componenti`),
nessuna con `attivo`, il padre con `attivo`. Le FK si sono rese eleggibili con righe del registro delle
inclusioni, che oggi è l'unico modo di farlo senza cambiare il runner.

| Caso | Righe nei registri | Require | Block su `config.lingue` |
| --- | --- | --- | --- |
| A | inclusione sulla sola radice | 1 sulla radice, che PostgreSQL **clona** sulle 2 partizioni (`tgparentid` ≠ 0) | 1, che nomina la radice |
| B | inclusione sulla radice e sulle 2 partizioni: è ciò che fa il runner **senza il filtro** | 1 sulla radice + 2 cloni + 2 propri delle partizioni: **ogni partizione ha due require** | 3: la radice e ciascuna partizione |
| C | come B, più un'eccezione sulla sola radice | spariscono quello della radice e i cloni; **restano i 2 propri delle partizioni** | 2, sulle partizioni |

Che cosa dice:

* `CREATE CONSTRAINT TRIGGER` su una radice partizionata **funziona**: nessun errore, e PostgreSQL lo
  propaga da sé alle partizioni, anche a quelle future. La radice basta da sola (caso A).
* Col filtro tolto e il runner invariato, i controlli si **raddoppiano** (caso B): due require per
  partizione e un block per partizione in più della radice. Il risultato è giusto ma ripetuto, e ogni
  partizione nuova ne aggiunge uno.
* ⛔ **Un'eccezione sulla radice non copre le partizioni** (caso C): la FK resta legata partizione per
  partizione. Per escludere davvero una FK ereditata servirebbe una riga per partizione, tutte col motivo
  uguale, e una partizione nuova nascerebbe legata.

Quindi D-5 «b» non è una scelta neutra: lascia i doppioni e un'eccezione che non dice ciò che dichiara.
⚠️ D-5 «a» cambia il runner e il ritiro (si salta `conparentid` ≠ 0), quindi non vale più la riga del §5
«il runner e il ritiro non si toccano».

**Limiti della prova:** una sola radice e una sola FK. Il conteggio delle figlie fatto dal block sulla
radice non è stato messo alla prova con righe costruite: si dà per buono che una lettura sulla tabella
partizionata veda le partizioni, ed è da coprire nel pgTAP costruito del §5. La prova gira da owner.
L'estratto è in
`/tmp/claude-1000/-home-tid-software-ZeroErp/b0ca8875-d2e9-4183-b40b-effb4646f9b4/scratchpad/prova-fk-ereditate.yaml`,
che è un file temporaneo: va spostato se serve rifarla.

### 3.2 La revisione (sessione DB, 2026-11-21)

**Da dove** (2026-11-21, scratch `zeroerp_ruoli`, sola lettura). Il perimetro è quello del runner:
schemi di `dbops.fn_resolve_scope(NULL)`, tabelle di `dbops.fn_table_in_scope`, padre con la colonna
`attivo` letta con l'override `ATTIVO_COL`, FK monocolonna. Le FK senza `_id` sono 89 dentro, di cui
40 ereditate dalle partizioni delle note, e 6 fuori. Il conto torna con le 95 del §2. Le 40 ereditate
seguono la loro radice (D-5 «a»), quindi le righe da decidere sono 49.

**Il criterio che decide, oltre alle famiglie del §3: le sorelle.** Una FK senza `_id` fa come le FK
con `_id` **della stessa figlia**, che il motore lega già, a meno che la colonna non dica una cosa
diversa (per esempio uno snapshot). Il nome non ha mai deciso il modello: la sorella legata è la
decisione già presa su quella tabella.

#### Si lega (30)

| Figlia · colonna | Padre (colonna) | Figlia con `attivo` | Perché |
| --- | --- | --- | --- |
| `config.stati_doc_offerte_transizioni`, `config.transizioni_stati_{contratti,ddt,listino_versioni,ordini,preventivi,reso}`, `vendite.transizioni_stati_commessa` · `azione_processo_codename` (8) | `config.azioni_processo` (`permission_codename`) | sì | Una transizione accesa con l'azione spenta è una porta che non si apre; le sorelle `stato_da_id`/`stato_a_id` sono legate |
| `config.stati_doc_fiscale_transizioni` · `azione_processo_codename` | `config.azioni_processo` (`permission_codename`) | **no** | Come sopra. Senza `attivo` conta ogni transizione, ed è la stessa scelta delle sorelle `stato_from_id`/`stato_to_id`, già legate |
| `config.stati_doc_{contratti,ddt,offerte,ordini,preventivi,reso}` · `esito` (6) | `config.esiti_flussi_pratiche` (`codice_interno`) | sì | Uno stato acceso non porta a un esito spento |
| `pratiche.template_flussi` · `esito_default` | `config.esiti_flussi_pratiche` (`codice_interno`) | sì | Il modello di flusso è configurazione viva |
| `pratiche.template_flussi_handler_eventi` · `esito_richiesto` | `config.esiti_flussi_pratiche` (`codice_interno`) | sì | Come sopra |
| `pratiche.template_flussi_avanzamento_proiezione` · `esito_richiesto` | `config.esiti_flussi_pratiche` (**`codice`**) | sì | Come sopra. ⚠️ È l'unica FK verso `codice` e non verso `codice_interno`: da segnalare a parte, non decide qui |
| `pratiche.template_flussi_prerequisiti` · `esito_richiesto` | `config.esiti_flussi_pratiche` (`codice_interno`) | no | Le sorelle `template_flusso_id`/`prerequisito_id` sono legate. L'esito è un valore richiesto, non il padre di cui il prerequisito è parte, quindi la famiglia «composizione» non vale |
| `config.tipi_indirizzi_allowed` · `ambito` | `config.sorgenti` (`codice_interno`) | sì | Configurazione viva |
| `vendite.famiglie_documento` · `codice_interno` | `config.sorgenti` (`codice_interno`) | sì | La famiglia **è** una sorgente (1:1): una famiglia accesa su una sorgente spenta non ha senso |
| `config.nature_vendita` · `destinazione_tipo` | `config.sorgenti` (`codice_interno`) | sì | Configurazione viva |
| `vendite.registri_fatturazione` · `famiglia_documento` | `vendite.famiglie_documento` (`codice_interno`) | sì | Un registro acceso non numera una famiglia spenta |
| `config.causali_trasporto` · `causale_magazzino` | `magazzino.causali` (`codice_interno`) | sì | Configurazione viva |
| `config.iva` · `id_iva_split` | `config.iva` (`id`), autoriferita | sì | Un'aliquota accesa non rimanda a uno split spento; la sorella `assoggettamento_id` è legata |
| `config.iva_stati` · `assoggettamento_id_override` | `config.iva_assoggettamenti` (`id`) | no | L'override per Paese; la sorella `iva_id` è legata |
| `magazzino.eventi_assets` · `magazzino_id_from`, `magazzino_id_to` (2) | `magazzino.magazzini` (`id`) | sì | Le sorelle `asset_id`, `tipo_evento_id` sono legate |
| `anagrafiche.emittenti_fiscali`, `anagrafiche.fornitori` · `regime_fiscale_rf` (2) | `config.regimi_fiscali` (`codice_interno`) | sì / no | Già legate oggi per inclusione (D-6 del regime fiscale): con D-1 si legano da sole, e l'inclusione si ritira |

#### Eccezione (13)

| Figlia · colonna | Padre | Famiglia | Motivo da scrivere nel CSV, in breve |
| --- | --- | --- | --- |
| `vendite.{attivita_fatturabili,commesse_attivita,contratti}` · `categoria_cliente_id_snapshot` (3) | `anagrafiche.categorie_clienti` | Storia (provenienza) | Lo snapshot è la categoria del cliente **al momento** del documento: è la provenienza di un dato già scritto, come `listino_riga_id` delle righe di contratto. Spegnere la categoria dopo non rende lo snapshot sbagliato |
| `{acquisti,catalogo,magazzino,vendite}.note` · `id_lingua`, `id_stile` (8, sulla radice) | `config.lingue`, `config.note_stili` | Nota | Lingua e stile sono attributi di presentazione di una nota, che non ha `attivo`. Col block una lingua o uno stile usati una volta non si spegnerebbero più; col require una nota in una lingua poi spenta non si correggerebbe più. Che cosa si sceglie per una nota nuova lo dice l'elenco delle voci accese |
| `config.messaggi_errore` · `lingua` | `config.lingue` (`codice_iso`) | **Nuova: traduzione** | Un testo tradotto non è un figlio vivo della lingua. Col require non si potrebbe preparare la traduzione prima di accendere la lingua; col block una lingua tradotta non si spegnerebbe. `script.fn_get_messaggio` sceglie la lingua dalla sessione e ripiega su `it` |
| `config.tipi_entita` · `sorgente_codice_interno` | `config.sorgenti` (`codice_interno`) | Registro senza `attivo` per scelta | Lo dice il COMMENT della tabella: è senza `attivo` perché un lucchetto ATTIVO fermerebbe il giornale, e la deprecazione si fa con `obsoleto_dal`. Col block una sorgente registrata come tipo non si spegnerebbe mai |

#### Incerte (6): ✅ si legano (Tid, 2026-11-22)

✅ **Deciso (Tid, 2026-11-22): le sei si legano**, per coerenza con le sorelle. Non aspettano i cantieri vicini:
l'analisi magazzino, «La porta dell'esito» e la matrice di `stato_lotto` trovano la coppia già al suo posto. Le
FK che si legano sono quindi **36**, e le eccezioni restano 13.

Tutte e sei hanno la stessa forma: una figlia **operativa senza `attivo`** (un documento, un flusso, un
lotto), le cui sorelle con `_id` sono già legate. Se si legano, valgono le sorelle: un magazzino, un esito
o uno stato usati una volta non si spengono più. Se la risposta è «storia», sono le sorelle a essere un
debito, e l'eccezione su una colonna sola lascerebbe la tabella a metà.

| Figlia · colonna | Padre | Sorelle già legate | Cantiere vicino |
| --- | --- | --- | --- |
| `magazzino.trasferimenti` · `magazzino_id_from`, `magazzino_id_to` (2) | `magazzino.magazzini` | `sorgente_tipo_id` | analisi magazzino |
| `magazzino.trasferimenti_righe` · `ubicazione_id_da`, `ubicazione_id_a` (2) | `magazzino.ubicazioni` | `articolo_id`, `lotto_id`, `asset_id` | analisi magazzino |
| `pratiche.flussi` · `esito` | `config.esiti_flussi_pratiche` | `stato_id`, `template_flusso_id`, `risorsa_umana_id`, `unita_organizzativa_id` | «La porta dell'esito ancora aperta» |
| `vendite.fatturazione_lotti` · `stato_lotto` | `config.stati_lotto_job` | `stato_doc_fiscale_id`, `tipo_doc_fiscale_id`, `area_geografica_id` | «La matrice di `stato_lotto`» |

**Proposta** (accolta il 2026-11-22): si legano, per coerenza con le sorelle. Se Tid pensa che queste figlie siano storia, la
domanda è più larga di questo cantiere: riguarda tutte le FK di quelle tabelle, e va in un brief suo.

#### Fuori dal perimetro (6): D-1 non le tocca

| Figlia · colonna | Padre | Perché fuori |
| --- | --- | --- |
| `maintenance.job_run_log` · `processo_codice` | `dbops.processi` | lo schema `maintenance` non è nello scope, e `dbops.processi` non è fra le tabelle in scope |
| `dbops.coda_lavori` · `job_type`; `dbops.coda_lavori_tipi` · `processo_codice` | `dbops.coda_lavori_tipi`, `dbops.processi` | tabelle di `dbops` fuori da `fn_table_in_scope` |
| `dbops.presidi_cause` · `vista`; `dbops.presidi_testi` · `vista`, `lingua` | `dbops.presidi`, `config.lingue` | come sopra (le figlie) |

È una scelta di contratto, lo scope del motore, e non la rimette in discussione questo giro. Il
presidio del §5 usa lo stesso perimetro, quindi non le chiede.

#### Per D-6: i nomi fuori regola (stessa data, tutte le FK, non solo quelle ATTIVO)

* **Verso una colonna che porta un id, senza `_id` nel nome** (l'elenco congelato): `id_lingua` e
  `id_stile` delle quattro radici `note`, `id_iva_split`, `assoggettamento_id_override`,
  `magazzino_id_from`/`_to` (trasferimenti, eventi_assets), `ubicazione_id_da`/`_a`,
  `categoria_cliente_id_snapshot` (3), `classe_utenza_id_snapshot` (2),
  `anagrafiche.dati_societari.id_prov_iscri_rea`: 22 FK.
  ⚠️ *Correzione del 2026-11-22 (§9.3): sono 23, con `config.credenziali.bloccata_da`, che lo scratch non ha.*
* **Il caso inverso** (deciso «sì» da Tid, 2026-11-21): oggi nessuna. Le due `emittente_soggetto_ruolo_id`
  (billing account e utilities degli emittenti) puntano a `emittenti_fiscali.soggetto_ruolo_id`, che non
  è la PK ma **porta un id**: il nome dice il vero.
* Le FK verso una PK naturale (`target_tipo`/`entity_type` → `config.tipi_entita.codice`,
  `codici_errore.classe`, `messaggi_errore.codice`, `dbops.emittente_modi.modo`) sono della specie b):
  la regola non le riguarda.

Il criterio di D-6 quindi si precisa così: **una colonna FK finisce in `_id` se e solo se la colonna
referenziata porta un id** (`id`, o un nome che finisce in `_id`). Detto «la PK `id`», avrebbe messo fuori
regola le due `emittente_soggetto_ruolo_id`.

## 4. Decisioni di Tid

* ✅ **D-1 — Il filtro `_id` si toglie?** Deciso «a» (Tid, 2026-11-21).
  * a) Sì: il motore lega ogni FK a una colonna verso un padre con `attivo`. Chi non si lega sta fra
    le eccezioni, col motivo. Le inclusioni si ritirano. *(raccomandata: è il principio del 2026-11-04)*
  * b) No: resta il filtro, e le inclusioni crescono una riga alla volta.
* ✅ **D-2 — I nomi della specie a) si correggono?** Deciso «b» (Tid, 2026-11-21): i nomi di oggi restano,
  la regola diventa obbligatoria per le FK nuove. (`id_lingua` → `lingua_id`, `magazzino_id_from` →
  `magazzino_da_id`…)
  * a) Sì, in un giro dedicato: tocca BE e FE (campi delle note, dei trasferimenti, dell'IVA) e va
    concordato con loro.
  * b) No: con D-1 «a» il nome non decide più niente per ATTIVO. Si rende **obbligatoria** la regola
    `<cosa>_id` per le FK **nuove** verso un `id`, con un controllo che la fa rispettare.
    *(raccomandata: separa il rinomino, che costa al BE, dalla regola, che non costa niente)*
* ✅ **D-3 — Le righe incerte del §3.** Chiusa (Tid, 2026-11-22): le 6 incerte del §3.2 si legano. Metodo accettato (Tid, 2026-11-21): la sessione DB propone, FK per FK,
  «si lega» o «eccezione» col motivo; Tid decide solo le righe che la proposta marca come incerte. Le risposte
  si scrivono qui, nel §3, prima di scrivere il giro. La proposta parte dalle famiglie di motivo del §3.
* ✅ **D-4 — La coppia si può dividere?** Deciso «a» (Tid, 2026-11-21): la coppia resta intera. Un'eccezione
  toglie block **e** require insieme; il registro delle inclusioni lo motivava con «nessuna riga chiede una
  parte sola». Con la specie b) una riga potrebbe chiederla: «non si scrive una nota nuova in una lingua
  spenta, ma la lingua si spegne anche se citata» (solo require), o il contrario.
  * a) No: la coppia resta intera, e una FK che ne vorrebbe metà sceglie fra legarsi ed eccezione.
    *(raccomandata, se la revisione del §3 non trova una riga che la chiede: lo dice il brief, e la domanda si chiude)*
  * b) Sì: le eccezioni prendono una colonna «quale parte» (`BLOCK`, `REQUIRE`, entrambe), letta dal runner e dal
    ritiro.

  Nella revisione del §3, una FK che vorrebbe una parte sola lo scrive nella sua riga e sceglie fra «si lega»
  ed «eccezione». Se una riga non regge nessuna delle due, torna a Tid come incerta: è l'unico modo di
  riaprire D-4.
* ✅ **D-5 — Le FK ereditate dalle partizioni** (§3.1, provato il 2026-11-21). Deciso «a» (Tid, 2026-11-21): si
  legano e si escludono sulla radice; il runner e il ritiro cambiano (§5).
  * a) Si legano e si escludono **sulla radice**: il runner e il ritiro saltano le FK con `conparentid` ≠ 0, e
    un'eccezione sulla radice vale per tutte le partizioni. Il require della radice lo clona PostgreSQL (caso A).
    *(raccomandata: una regola, una riga; una partizione nuova eredita la decisione)*
  * b) Il runner resta com'è: ogni controllo si ripete sulla radice e su ogni partizione (caso B), e per escludere
    una FK ereditata serve una riga per partizione (caso C).
  * Le FK **proprie** di una partizione (`target_id` delle note, `conparentid` = 0) restano come oggi in tutti e due
    i casi.
* ✅ **D-6 — Come si fa rispettare la regola dei nomi di D-2 «b».** Accettata la proposta (Tid, 2026-11-21):
  * Il criterio sta sulla colonna **referenziata**: una FK verso la PK `id` del padre si chiama `<cosa>_id`. Il
    nome della figlia non decide.
  * I nomi di oggi restano (D-2 «b»), quindi il controllo ha bisogno di un **elenco congelato** delle FK fuori
    regola (le 22 del §3.2): un registro per esclusione, col motivo «nome storico, D-2 b».
  * Il predicato è `LIKE '%\_id'` (col `_` protetto), non quello del motore.
  * Il controllo è un pgTAP strutturale, non un guard sulla creazione.
  * ✅ **Il caso inverso: sì** (Tid, 2026-11-21). Una colonna `x_id` che punta a un codice è fuori regola,
    perché il suffisso dichiara che la colonna porta un `id`. Il controllo è a due versi. Oggi non ce n'è
    nessuna (§3.2).
  * ⚠️ Il criterio, precisato dalla revisione (§3.2): «finisce in `_id` se e solo se la colonna referenziata
    porta un id», non «se e solo se punta alla PK `id`». Detto così, la regola non mette fuori regola
    `emittente_soggetto_ruolo_id`, che punta a una UNIQUE `soggetto_ruolo_id`. L'elenco congelato ha 22 FK.
    ⚠️ *Correzione del 2026-11-22 (§9.3): 23.*

## 5. Il giro (dopo le decisioni)

* `dbops.fn_attivo_fk_esclusa` senza il ramo `_id`: risponde solo `ECCEZIONE_DICHIARATA`.
* Per D-5 «a», il runner e il ritiro cambiano: il cursore del runner salta le FK ereditate
  (`conparentid` ≠ 0) e lega la radice, il cui require PostgreSQL clona sulle partizioni. Il ritiro
  toglie i trigger propri che una FK ereditata ha avuto prima del giro, se ce ne sono. Il pgTAP
  costruito del §5 prova una radice con due partizioni: un require sulla radice, nessun doppione sulle
  partizioni, un block sul padre che conta le figlie di tutte le partizioni, un'eccezione sulla radice
  che le copre tutte. Nel runner il ramo
  `ATTIVO_SKIP_FK_NO_ID` del dry run diventa codice morto: si toglie, e con lui il token
  `FK_NO_ID_SUFFIX` dalla guida e dai lettori del diario.
  ⚠️ *Correzione della verifica del 2026-11-22 (§8.1): per il ritiro «salta» è il verbo sbagliato.* Il
  ritiro deve **togliere** i trigger propri (`tgparentid` = 0) di una FK ereditata e **non toccare mai** i
  cloni (`tgparentid` ≠ 0): un `DROP TRIGGER` su un clone fallisce, perché il trigger della radice lo
  richiede. Oggi il ritiro non filtra `tgparentid`, e trova le FK solo per nome con
  `fn_attivo_fk_esclusa`, che non sa se una FK è ereditata. Proposta: la regola «ereditata» la dà
  `fn_attivo_fk_esclusa` come terza risposta (`FK_EREDITATA`, letta da `pg_constraint.conparentid` della
  colonna sulla figlia), così runner e ritiro la leggono da una sede sola. Il ramo del dry run allora non
  muore: cambia token (`ATTIVO_SKIP_FK_EREDITATA`).
* ⚠️ L'ordine dei changeSet: `fn_attivo_fk_esclusa` è `BEGIN ATOMIC` e dipende dalla tabella delle
  inclusioni. Prima si riscrive la funzione, poi si fa il `DROP` della tabella.
* Le righe nuove di `automazione_attivo_eccezioni.csv`, una per FK esclusa, col motivo della sua
  famiglia (§3). Il CSV lo tocca anche `brief-db-revisione-ui`: si rilegge prima di scrivere.
* Il ritiro di `dbops.automazione_attivo_inclusioni`: tabella, CSV, changeSet di carico, pagina
  `manual/`, il paragrafo «Le inclusioni» di `guide/automazione-db.md`, il pgTAP
  `dbops/test-automazione-attivo-inclusioni-v1` (riscritto sul registro delle eccezioni, o ritirato).
  Il `CHECK` «solo senza `_id`» perde senso insieme al registro.
  ⚠️ *Aggiunta della verifica del 2026-11-22:* anche le pagine `manual/` che linkano la tabella o
  descrivono il filtro, altrimenti restano link rotti: `config/manual/regimi_fiscali.md` (due link),
  `anagrafiche/manual/fornitori.md` (uno), e `dbops/manual/` di `fn_attivo_fk_esclusa`,
  `fn_run_automations_attivo`, `fn_ritira_attivo_eccezioni`, `automazione_attivo_eccezioni`.
* Il provision ATTIVO in `90_end`, con la prova in `ROLLBACK`: l'elenco dei trigger creati deve
  essere uguale a quello delle FK che si legano, nessuno in più.
* ⚠️ **I dati prima dell'apply:** una riga accesa che oggi cita un padre spento diventa non
  modificabile. Il require scatta a `INSERT OR UPDATE OF <fk>, <attivo>`, quindi anche a valore
  invariato, ogni volta che l'UPDATE nomina la colonna. Prima del provision si cercano quelle righe,
  FK per FK, e si decide se riaccendere il padre, cambiare il figlio o fare un'eccezione.
* ⚠️ **I seed, che sono contratto e non fotografia.** Molte figlie della specie b) sono seed (transizioni,
  `presidi_testi`, `messaggi_errore`). Un `loadUpdateData` scrive tutte le colonne e fa scattare il
  require: un CSV con una figlia accesa che cita un padre seminato spento non si ricarica più, e lo si
  scopre al giro di seed successivo, in CI. Al primo impianto non si vede, perché il seed passa prima
  del `90_end`. Allo stesso modo, un CSV che spegne un padre citato da figlie accese del seed viene
  rifiutato dal block. Per ogni FK legata si verificano i CSV di `80_data`: nessuna figlia accesa del
  seed cita un padre spento del seed.
* Il pgTAP, in due parti:
  * **strutturale**: ogni FK verso un padre con `attivo` **nel perimetro del motore** è legata oppure è
    fra le eccezioni. Vale per tutte le FK, non solo per quelle senza `_id`: dopo D-1 il nome non
    decide più niente. Il perimetro è quello del runner (`dbops.fn_resolve_scope`,
    `dbops.fn_table_in_scope`), e la colonna del padre si legge con l'override `ATTIVO_COL`
    (`dbops.fn_get_override_col`), non con il nome `attivo`. Si guardano le FK con `conparentid` = 0:
    una FK ereditata è legata dal clone del require della radice ed esclusa dall'eccezione della radice
    (D-5 «a»);
  * **costruito**: una tabella di prova con una FK senza `_id` verso un padre con `attivo`, un giro del
    motore, e i due trigger ci sono. Senza questo caso il test prova solo le FK che lo schema contiene
    oggi.

  È il presidio che impedisce di ricreare un'esclusione silenziosa.
* Per D-2 «b»: ✅ la regola dei nomi è scritta in `linee-guida-sql.md` §2 («La colonna FK dice che cosa
  porta», 2026-11-22), nei due versi e coi nomi storici che restano. Restano per il giro l'elenco congelato
  delle 22 FK storiche (§3.2) e il pgTAP strutturale di D-6. La regola dichiara che il presidio non c'è
  ancora: col giro, quella riga si toglie.
  ⚠️ *Verifica del 2026-11-22:* il pgTAP di D-6 guarda le FK **monocolonna** con `conparentid` = 0.
  Senza il filtro sulle ereditate, l'elenco congelato dovrebbe portare anche le 40 FK delle partizioni
  delle note.

**Garanzie ritirate:** nessuna. Il giro ne **aggiunge**: ogni FK legata guadagna le due regole.

## 6. Ricadute sul BE/FE (richiesta al team, 2026-11-22)

⚠️ *Il titolo diceva «da scrivere per intero quando il giro è deciso»: è scritta qui, col giro del §9.*

**Che cosa cambia per chi scrive.** Dopo l'apply, 34 FK in più hanno la coppia ATTIVO (le 36 del §3.2 meno le due
`regime_fiscale_rf`, che l'avevano già). I codici sono quelli di sempre, e nessuno è nuovo:

* chi **scrive la figlia** con un padre spento riceve `E_ATTIVO_PADRE_NON_ATTIVO`, col `campo` = la colonna FK nel
  contesto. Il require scatta al commit, e su ogni `UPDATE` che nomina la colonna, anche se il valore non cambia;
* chi **spegne il padre** in uso riceve `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` se la figlia ha `attivo` (conta le figlie
  accese), `E_ATTIVO_BLOCK_CHILDREN_EXIST` se non ce l'ha (conta ogni riga). Nessuno dei padri ha `obsoleto_dal`,
  quindi `E_ATTIVO_BLOCK_SI_RITIRA` non esce.

| Padre che non si spegne più se in uso | Figlie nuove | Figlia senza `attivo` (conta ogni riga) | Padre nel pannello |
| --- | --- | --- | --- |
| `config.azioni_processo` | le 9 tabelle di transizione (`azione_processo_codename`) | `config.stati_doc_fiscale_transizioni` | no |
| `config.esiti_flussi_pratiche` | 6 `config.stati_doc_*` (`esito`), `pratiche.template_flussi` (`esito_default`), 3 tabelle di `pratiche.template_flussi_*` (`esito_richiesto`), `pratiche.flussi` (`esito`) | `template_flussi_prerequisiti`, `flussi` | no |
| `config.sorgenti` | `config.tipi_indirizzi_allowed` (`ambito`), `vendite.famiglie_documento` (`codice_interno`), `config.nature_vendita` (`destinazione_tipo`) | — | sì |
| `vendite.famiglie_documento` | `vendite.registri_fatturazione` (`famiglia_documento`) | — | no |
| `magazzino.causali` | `config.causali_trasporto` (`causale_magazzino`) | — | sì |
| `config.iva` | `config.iva` (`id_iva_split`, autoriferita) | — | sì |
| `config.iva_assoggettamenti` | `config.iva_stati` (`assoggettamento_id_override`) | `config.iva_stati` | sì |
| `magazzino.magazzini` | `magazzino.eventi_assets`, `magazzino.trasferimenti` (`magazzino_id_from`, `_to`) | `trasferimenti` | no |
| `magazzino.ubicazioni` | `magazzino.trasferimenti_righe` (`ubicazione_id_da`, `_a`) | `trasferimenti_righe` | no |
| `config.stati_lotto_job` | `vendite.fatturazione_lotti` (`stato_lotto`) | `fatturazione_lotti` | no |

«Padre nel pannello» è `config.tabelle_gestibili.pannello` (scratch, 2026-11-22): lì lo spegnimento passa dal
pannello generico (`config.fn_pannello_scrivi`), che riceve il codice come per ogni altra coppia ATTIVO.
Dove la figlia non ha `attivo`, un padre usato **una volta** non si spegne più: un magazzino che ha un
trasferimento, un esito che ha chiuso un flusso, un'aliquota usata come override.

**Garanzie ritirate.** Nessuna proprietà che un lettore dava per scontata sparisce. Sparisce una **possibilità**: «il
padre si spegne anche se in uso», per i dieci padri della tabella. È la richiesta al team:

1. **Censisci i lettori e gli scrittori che contano su «questo padre si spegne anche se in uso»**: maschere,
   import, comandi o job che spengono una voce dei dieci padri, e i test che lo fanno nelle fixture. L'elenco dei
   padri sopra è chiuso; **dove lo si spegne no**, ed è quello che il DB non vede.
2. Dove una maschera **scrive la figlia**, che `E_ATTIVO_PADRE_NON_ATTIVO` arrivi all'operatore sul campo giusto (il
   `campo` è il nome della colonna FK, anche quando non finisce in `_id`: `esito`, `causale_magazzino`,
   `azione_processo_codename`, `magazzino_id_from`…).
3. Dove una maschera **spegne il padre**, che i due codici del block arrivino col loro testo.
4. ⚠️ La voce aperta «`E_ATTIVO_REQUIRE` è TECNICO anche quando il dato l'ha scelto una persona» (PROJECT_CONTEXT) non
   cambia: `E_ATTIVO_REQUIRE` è l'errore del **montaggio** di un trigger, non del dato. Con questo giro non esce
   all'operatore.

Lato DB il censimento è fatto (2026-11-22): nessuna funzione spegne uno dei dieci padri con un `UPDATE … SET attivo`,
e nessuna vista legge il registro delle inclusioni. Il seed e i dati di dbdev non hanno figlie vive con un padre
spento (§8).

### 6.1 Che cosa ha fatto il BE/FE (2026-11-22, `dev/backend-tid`)

**Il canale è uno, e regge.** Il trigger mette la colonna FK nel canale `COLUMN` dell'eccezione e il codice in
`CONSTRAINT`. I punti di traduzione la portano in `error.fields`, e il FE la riceve in `campiErrati` di
`useApiHandler`. Vale per ogni nome di colonna, con o senza `_id`. Nessun codice nuovo: i tre `E_ATTIVO_*` hanno già
classe (`CONFLITTO_STATO`, 409) e ripiego.

**Quando l'operatore lo vede.** Un padre non si spegne più mentre ha figlie accese, quindi il require esce in due
casi: quando si **riaccende una figlia spenta** che punta a un padre spento, e quando si sceglie un padre che un
altro operatore ha appena spento. Il modello ammette tutti e due.

⚠️ **Il require è differito al commit.** Con `ATOMIC_REQUESTS` spento il commit è quello dell'istruzione, dentro il
`try` del service, e l'errore si traduce lì. I test lo riproducono con `SET CONSTRAINTS ALL IMMEDIATE`: in una
transazione annullata il commit non arriva mai, e un test senza sarebbe verde perché il controllo non scatta
(provato: tolto `IMMEDIATE`, i due casi del require vanno rossi).

**Punto 1, chi spegne i dieci padri** (`grep` su tabella e colonna in `backend/` e `frontend/`, poi i percorsi):

| Padre | Chi lo spegne | Esito |
| --- | --- | --- |
| `vendite.famiglie_documento` | `FamiglieRepository.set_attivo` (`vendite/db/famiglie_repository.py`) | Non ne dipende: `script.fn_check_famiglia_documento_disattivabile` ha già `HA_REGISTRI_ATTIVI`, e il guard dedicato (`…_a10_guard_disattivazione_upd`) scatta prima del block ATTIVO (ordine alfabetico). L'operatore riceve il motivo specifico, il block è la rete |
| `magazzino.magazzini`, `magazzino.ubicazioni` | PATCH `attivo` da `anagrafiche_magazzino_service` | Adeguato col solo test: con un trasferimento il magazzino non si spegne più (`E_ATTIVO_BLOCK_CHILDREN_EXIST`), e il codice passa intatto dal suo `make_db_errors_translator`. Il test esistente che spegne un magazzino appena nato (`test_anagrafiche_magazzino_db.py`) non ha trasferimenti, e resta verde |
| `config.sorgenti`, `magazzino.causali`, `config.iva`, `config.iva_assoggettamenti` | il pannello (`config.fn_pannello_scrivi`, drawer generico) | Non ne dipende: il codice arriva dal canale comune del pannello, col testo del catalogo |
| `config.azioni_processo`, `config.esiti_flussi_pratiche`, `config.stati_lotto_job` | nessuno | Non ne dipende: nessun `UPDATE … attivo` in BE/FE, negli smoke o nelle fixture; nessuno dei tre è nel pannello |

**Punto 2, chi scrive le figlie, e se il campo si accende:**

| Figlia (colonna) | Maschera | Esito |
| --- | --- | --- |
| tabelle del pannello: `config.causali_trasporto` (`causale_magazzino`), `config.iva` (`id_iva_split`), `config.stati_doc_contratti`, `_ddt`, `_ordini`, `_preventivi`, `_reso` (`esito`) | `GenericConfigDrawer` | Già legato: `:invalid="campiErrati.includes(col.name)"` (`config.tabelle_gestibili.pannello` letto su dbdev il 2026-11-22) |
| `config.nature_vendita` (`destinazione_tipo`, fuori pannello), `config.stati_doc_offerte` (`esito`, fuori pannello), `config.iva_stati` (`assoggettamento_id_override`), `config.tipi_indirizzi_allowed` (`ambito`), queste due nemmeno registrate | nessuna maschera | Nessuno le scrive da BE/FE: sono seed. Se una entra nel pannello, il drawer generico la copre senza modifiche |
| `vendite.registri_fatturazione.famiglia_documento` | `RegistroNumerazioneDrawer` | Già legato (in creazione; in modifica la famiglia non si sceglie, e il messaggio dice il resto) |
| `vendite.famiglie_documento.codice_interno` → `config.sorgenti` | `FamigliaDocumentoDrawer` | Già legato |
| `pratiche.template_flussi.esito_default` | `DefinizioneStepForm` | **Legato** (mancava) |
| `esito_richiesto` di prerequisiti, handler eventi e regole di generazione | `StepPrerequisitiTab`, `StepHandlerEventiTab`, `ArchiRegoleTab` | **Legato** (mancava), dopo la correzione qui sotto |
| `pratiche.flussi.esito` | `FlussoDrawer` | **Legato** (mancava) |
| `magazzino.trasferimenti*`, `magazzino.eventi_assets`, `vendite.fatturazione_lotti.stato_lotto`, le nove tabelle di transizione (`azione_processo_codename`) | nessuna maschera | Le scrivono funzioni DB o nessuno (§5.1 del brief del magazzino) |

⚠️ **Un difetto che c'era già, trovato qui.** I sei tab dell'editor dei workflow ricevevano `campiErrati` come prop
dalla vista, che ha un `useApiHandler` suo, ma salvano con l'`execute` di `useEditableCollection`, che ne ha un
altro. I campi del rifiuto finivano in un'istanza che nessuno leggeva: nessun campo dei tab diventava mai rosso,
nemmeno `attivo` e `descrizione`, che erano già legati. Ora il BB espone il `campiErrati` della sua istanza, e i tab
leggono quello (catalogo BB FE, `useEditableCollection`). Presidio: `useEditableCollection.spec.js` (provato: tolta
la correzione, va rosso).

⚠️ **E due difetti della correzione, trovati in verifica.** Il `campiErrati` esposto era anche quello del toggle
`attivo` e dell'eliminazione, che partono da una riga dell'elenco: proprio il caso del require (riaccendere una
figlia su un esito spento) accendeva `esito_richiesto` nel form aperto su un'altra riga. E nessuno lo azzerava
all'apertura del form, né del `FlussoDrawer`, né del form dello step da uno step all'altro: il campo di un rifiuto
restava rosso sul record dopo. Ora toggle ed eliminazione hanno un `useApiHandler` loro, e i campi si azzerano a ogni
apertura (casi 3 e 4 dello spec, provati rossi col codice di prima).

**Punto 3, il testo del block.** Arriva quello del catalogo, letto dal DB nei test e non ricopiato. I tre messaggi
sono frasi chiuse: il padre e la figlia viaggiano nel contesto, non nel testo.

**Le prove sul DB vero** (`ZEROERP_TEST_DB_E2E=1`, dbdev come `zeroerp_app`, transazione annullata, 4/4 verdi):

* `apps/core/tests/db/test_attivo_fk_senza_suffisso_db.py`. Dal pannello: una causale di trasporto su una causale
  di magazzino spenta è `E_ATTIVO_PADRE_NON_ATTIVO`, 409, con `fields = ("causale_magazzino",)`. La causale di
  magazzino in uso non si spegne (`E_ATTIVO_BLOCK_CHILDREN_ACTIVE`); spenta la figlia, sì. Il terzo caso fa passare
  lo stesso rifiuto da `_mapped_db_errors` dell'editor dei workflow, che riconosce solo i codici del suo dominio e
  rilancia gli altri: arriva all'envelope col codice e col campo, non come `E_DATABASE`;
* `apps/magazzino/tests/db/test_magazzino_spento_con_trasferimenti_db.py`. Il magazzino di partenza e quello d'arrivo
  di un trasferimento non si spengono (`E_ATTIVO_BLOCK_CHILDREN_EXIST`); un magazzino senza trasferimenti sì.

Al DB non si chiede niente.

## 7. La query della misura

```sql
SELECT a.attname AS colonna, pa.attname AS colonna_padre,
       c.conrelid::regclass AS figlia, c.confrelid::regclass AS padre
  FROM pg_constraint c
  JOIN pg_attribute a  ON a.attrelid  = c.conrelid  AND a.attnum  = c.conkey[1]
  JOIN pg_attribute pa ON pa.attrelid = c.confrelid AND pa.attnum = c.confkey[1]
  JOIN pg_namespace n  ON n.oid = c.connamespace
 WHERE c.contype = 'f' AND array_length(c.conkey, 1) = 1
   AND lower(a.attname) NOT LIKE '%\_id'
   AND n.nspname NOT IN ('django', 'pg_catalog', 'public', 'pgagent')
   AND EXISTS (SELECT 1 FROM pg_attribute x
                WHERE x.attrelid = c.confrelid AND x.attname = 'attivo' AND NOT x.attisdropped)
 ORDER BY 1, 3;
```

⚠️ Il motore usa `LIKE '%_id'`, col `_` jolly: una colonna come `xid` passerebbe per «con `_id`».
Con D-1 «a» il predicato sparisce, e il dubbio con lui.

⚠️ La query misura un'approssimazione del perimetro, non il perimetro. Esclude gli schemi a mano invece
di usare lo scope del motore, cerca la colonna `attivo` per nome senza l'override `ATTIVO_COL`, e conta
ogni partizione come una FK a sé (le 24+24 delle note sono due FK ereditate, §3.1). Va bene per il
fatto datato del §2, non per il presidio del §5.

## 8. Verifica critica (sessione DB, 2026-11-22)

Rifatta sul catalogo dello scratch `zeroerp_ruoli` (struttura e seed) e, per i dati, su dbdev, in sola
lettura. Le correzioni stanno nelle loro sezioni, marcate «verifica del 2026-11-22».

**Che cosa regge.** I conti del §3.2 tornano: 30 + 6 FK legate, 13 eccezioni, 49 righe, 40 ereditate, 6 fuori
perimetro. L'elenco congelato di D-6 conta 22 FK proprie nei due versi, più le 40 ereditate (§5). Le sole radici
partizionate sono le quattro `note`, con tre FK ciascuna: `id_lingua` e `id_stile`, che vanno fra le eccezioni, e
`target_tipo`, il cui padre non ha `attivo`. Quindi D-5 «a» oggi non cambia nessun trigger esistente: serve perché
l'eccezione sulla radice copra le partizioni, e per le partizioni future. Il motore lega già FK autoriferite
(`parent_id` di unità organizzative e ubicazioni), quindi `config.iva.id_iva_split` non è un caso nuovo. Il token
`FK_NO_ID_SUFFIX` e il registro delle inclusioni li leggono solo `fn_attivo_fk_esclusa`, il runner, il ritiro e il
pgTAP delle inclusioni: nessuna vista. Nessuna funzione DB spegne i padri che si legano con un `UPDATE … SET attivo`.

**Fatto datato** (non decide niente: cerca un controesempio, come chiede il §5). Righe vive (accese, o tutte se la
figlia non ha `attivo`) che citano un padre spento, su ogni FK senza `_id` verso un padre con `attivo`: sullo
scratch, cioè sul seed, nessuna; su dbdev, solo `vendite.contratti.categoria_cliente_id_snapshot` (115 righe), che
è fra le eccezioni. Il controllo del §5 prima del provision va rifatto lo stesso: la query è
`/tmp/claude-1000/-home-tid-software-ZeroErp/8dd95481-f7b8-445b-8c7f-ae2eabd3cbe9/scratchpad/padri_spenti.sql`,
un file temporaneo da spostare se serve rifarla.

### 8.1 Il ritiro con D-5 «a»

D-5 «a» diceva che runner **e ritiro** «saltano» le FK con `conparentid` ≠ 0. Per il runner è giusto, per il ritiro
no: il ritiro deve togliere i trigger propri di una FK ereditata, e deve lasciare stare i cloni, che PostgreSQL non
fa cancellare. La correzione e la proposta (`FK_EREDITATA` come terza risposta di `fn_attivo_fk_esclusa`) sono nel
§5. Non è una decisione di modello nuova: è come si scrive D-5 «a».

### 8.2 I lettori dei trigger ATTIVO, coi cloni sulle partizioni

Dopo il giro un require su una radice partizionata ha un clone su ogni partizione (`tgparentid` ≠ 0). Oggi non ne
nasce nessuno, perché le FK delle note vanno fra le eccezioni, ma il modello lo ammette e il pgTAP costruito lo
crea. Leggono i trigger ATTIVO: `fn_trigger_attivo_orfani`, `fn_trigger_exists_require_by_args`,
`fn_trigger_padre_stato`, `fn_trigger_attivo_argomenti`, `catalogo.fn_riattiva_articolo`,
`script.fn_resolve_emittente_for_user`, `vendite.fn_genera_ddt_riconsegna`. Nel giro, per ognuno si scrive se un
clone sulla partizione gli cambia la risposta, o perché no. `fn_trigger_attivo_orfani` non scambia un clone per un
orfano: guarda che la tabella e la colonna esistano, e la partizione le ha.

## 9. Il giro (sessione DB, 2026-11-22)

✅ **Applicato da Tid il 2026-11-22, pgTAP verdi.**

Scritto col via di Tid del 2026-11-22, numeri da `20261121-21` (dati da Tid). Provato in `ROLLBACK` sullo scratch e
su dbdev con `scripts/prova_changeset.py`. Il mirror del CSV non è SQL estraibile: nella prova le 13 righe sono
entrate da un `INSERT` equivalente.

### 9.1 I changeSet

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/dbops/20261121-21` | `dbops.fn_attivo_fk_esclusa` senza il ramo `_id` e senza il registro delle inclusioni: risponde `ECCEZIONE_DICHIARATA` o `FK_EREDITATA` (§8.1). `BEGIN ATOMIC`, provato anche attraverso il driver JDBC |
| `20_code/dbops/20261121-22` | Il motore: cambia solo il dry run (`ATTIVO_SKIP_FK_EREDITATA` al posto di `ATTIVO_SKIP_FK_NO_ID`). Il cursore non cambia, e i nomi dei trigger esistenti nemmeno |
| `20_code/dbops/20261121-23` | Il ritiro guarda solo i trigger propri (`tgparentid = 0`): le copie della radice non si toccano |
| CSV `80_data/sql/dbops/automazione_attivo_eccezioni.csv` | Le 13 eccezioni del §3.2 (mirror `20260925-49`, `runOnChange`) |
| `90_end/20261121-24` | Provision: il motore su tutto l'ambito. preCondition sul building block nuovo e sulle 13 righe |
| `90_end/20261121-25` | `DROP TABLE dbops.automazione_attivo_inclusioni`, in `90_end` perché `90_end/20261121-15` la pretende (linee-guida §11.14). ⛔ Il mirror `80_data/20261121-14` e il suo CSV restano intatti: ha `runOnChange`, e toccarli lo farebbe rigirare su una tabella che non c'è più |

### 9.2 Le prove (scratch `zeroerp_ruoli`, salvo dove detto)

* Prima del giro, il presidio strutturale trova 47 FK non legate: le 34 nuove più le 13 eccezioni, nessun buco fra le
  FK con `_id`.
* Dopo il giro: 68 trigger ATTIVO in più (834 → 902), cioè le 34 coppie, nessuno in più.
* Le preCondition di `-24` e `-25`, lette **dopo** l'estratto che le precede: verdi.
* L'estratto intero gira anche su dbdev, coi suoi dati.
* Il test 11 del pgTAP nuovo, **senza** `-23`, si ferma su `2BP01` (il `DROP` rifiutato sul clone): il ritiro di
  prima avrebbe fermato ogni giro su una radice legata.

### 9.3 I pgTAP

| pgTAP | Esito nella prova (dopo l'apply: verdi, Tid 2026-11-22) |
| --- | --- |
| `dbops/test-automazione-attivo-senza-filtro-nome-v1` (nuovo, 13 test, runner owner) | 13/13 con l'estratto |
| `dbops/test-automazione-attivo-inclusioni-v1` (test 1, 2 e 6 riscritti senza il registro; il motivo del runner di D-8 resta) | 12/12 |
| `dbops/test-automazione-attivo-eccezioni-v1` | 9/9, invariato |
| `dbops/test-fk-nome-dice-cosa-porta-v1` (nuovo, D-6) | 2/2 sullo scratch e su dbdev. ⚠️ Lanciato dalla sessione con psql, in sola lettura del catalogo: un'eccezione alla regola «i pgTAP li lancia Tid», da non ripetere |

⚠️ **Correzione di D-6: l'elenco congelato ha 23 FK, non 22.** Su dbdev c'è anche `config.credenziali.bloccata_da` →
`django.auth_user.id`, che lo scratch e la CI non hanno: la FK nasce solo dove esiste lo schema `django` (il residuo
aperto «Le FK verso `django.auth_user` non nascono su un'installazione nuova»). Il modello la ammette, quindi è
nell'elenco, marcata «può mancare». Le 22 del §3.2 erano misurate sul solo scratch.

### 9.4 La documentazione

Aggiornate: `guide/automazione-db.md` (§1.3 e §4.2), le pagine `manual/` di `fn_attivo_fk_esclusa`,
`fn_run_automations_attivo`, `fn_ritira_attivo_eccezioni`, `automazione_attivo_eccezioni`, `regimi_fiscali` (per
sostituzione sul testo del giro D-8), `fornitori`, e `linee-guida-sql.md` §2 (la riga «il presidio non c'è ancora»
diventa il pgTAP). La doc auto-generata è rigenerata (Tid, 2026-11-22): la pagina della tabella ritirata non c'è più, e con lei
sono state tolte la pagina `manual/automazione_attivo_inclusioni.md` e la sua voce in `dbops/index.ci.md`.


## 10. Chiusura (sessione DB, 2026-11-22)

* **Il BE/FE non chiede correttive al DB.** Il §6.1 risponde ai punti 1-3 della richiesta del §6. Il punto 4 non
  chiedeva lavoro. Nessuna funzione, nessun codice d'errore e nessuna riga del catalogo da cambiare: i tre
  `E_ATTIVO_*` avevano già classe e ripiego. Lavoro committato in `ebd81ec653` (PR #194).
* **Niente debito.** I due punti aperti che il brief tocca hanno già la loro voce, e questo giro non li cambia:
  «`E_ATTIVO_REQUIRE` è TECNICO anche quando il dato l'ha scelto una persona» (PROJECT_CONTEXT, §6 punto 4) e «Le FK
  verso `django.auth_user` non nascono su un'installazione nuova» (registro dei residui, §9.3).
* **Archiviato** in `work-done/2026/`. I rimandi per percorso (i tre brief vicini in testata, la voce del
  PROJECT_CONTEXT) sono riallineati. I rimandi per nome nelle intestazioni dei changeSet, dei pgTAP, delle pagine
  `manual/` e dei test BE non cambiano.
