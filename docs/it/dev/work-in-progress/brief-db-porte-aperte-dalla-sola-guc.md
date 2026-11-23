# Brief DB — le porte che si aprono con la sola GUC

> **⏭️ Chi riparte — aggiornato al 2026-11-23**
>
> **Riparte: Tid**, con le decisioni D-A … D-D (§3-bis.4), che sostituiscono D-1 … D-3 dopo l'analisi critica.
> Aperto, non iniziato: nessuna riga di codice.
>
> | # | Chi | Che cosa | Dove | Aspetta |
> | --- | --- | --- | --- | --- |
> | 1 | team DB | ✅ censimento delle porte sul catalogo di dbdev (2026-11-23), ✅ corretto dall'analisi critica: diciassette porte | §2, §3-bis | — |
> | 2 | Tid | le decisioni D-A … D-D | §3-bis.4 | — |
> | 3 | team DB | la richiesta al BE (chi chiama gli aprenti, chi accende le GUC) | §4 | 2 |
> | 4 | team BE | la ricognizione dei chiamanti | §4 | 3 |
> | 5 | team DB | i giri | Il piano | 4 |
>
> Decisioni aperte di Tid: D-A … D-D (§3-bis.4). Da committare: niente oltre questo file.
>
> **Brief vicini verificati (2026-11-23):**
> [brief-db-magazzino-tutte-le-scritture-dal-verbo](../work-done/2026/brief-db-magazzino-tutte-le-scritture-dal-verbo.md)
> (archiviato), da cui nasce: la sua §5.8 ha ricercato la classe vicina, la porta «GUC + proprietario» attraversata
> da un verbo DEFINER, senza trovare altri casi; questa è un'altra classe. `brief-db-revisione-anagrafiche`,
> segnalazione **S50**, nomina la porta `zeroerp.maintenance_indirizzi_dettaglio` («un parametro di sessione che
> chiunque scriva accende»): è una delle quindici. Se Tid la decide lì, qui si toglie; nel dubbio, decide Tid
> dove la si tratta. `brief-db-revisione-ui`: nomina `fn_is_proprietario_tabella` per altro, nessuna sovrapposizione.
>
> **Guide verificate** (`scripts/guide_coinvolte.py --oggetti` sui quindici trigger, 2026-11-23):
> [gestione-dei-pagamenti](../../guide/gestione-dei-pagamenti.md) (i due guard delle righe del contabile),
> [gestione-degli-indirizzi](../../guide/gestione-degli-indirizzi.md) e
> [riclassificazione-vie](../../guide/riclassificazione-vie.md) (il guard di `stradario_id`, «flag di
> manutenzione»), [gestione-listini](../../guide/gestione-listini.md) (il guard degli articoli ammessi): oggi
> **coerenti**, descrivono le porte come sono. Una strada che aggiunge il proprietario a una porta le
> **contraddice**: è un cambio di modello, e decide Tid (§3). Orfani: dieci trigger che nessuna guida cita
> (`config.trgfn_toponomastica_protect_update`, `config.trgfn_user_emittenti_fiscali_guard_delete`, gli otto di
> `vendite` del reset del lotto e dei legami della bolla); sono dettagli interni dei guard, segnalati qui.
> Rilancio del 2026-11-23 sulle porte 16-17 e sugli aprenti: [documenti-e-stampe](../../guide/documenti-e-stampe.md)
> (la pubblicazione), [tx_id_implementation_guide](../../guide/tx_id_implementation_guide.md),
> [audit-e-tracciabilita](../../guide/audit-e-tracciabilita.md), [automazione-db](../../guide/automazione-db.md),
> [generazione-cliente](../../guide/generazione-cliente.md) (il trigger del `tx_id`): **coerenti** oggi;
> [riclassificazione-vie](../../guide/riclassificazione-vie.md) **indietro** su un punto (§3-bis.3). Orfani: gli
> aprenti `fn_cleanup_fatture_by_ids`, `fn_cancella_fondo_fattura`, `fn_change_user_emittenti_scope`,
> `fn_genera_ddt_riconsegna`, `proc_bump_toponomastica` e il trigger della porta 16.

## Il piano da percorrere

**Prima di scrivere**

- [x] Censimento delle porte sul catalogo (2026-11-23, §2)
- [x] Analisi critica: censimento corretto, decisioni riformulate (2026-11-23, §3-bis)
- [ ] Le decisioni di Tid, D-A … D-D (§3-bis.4)
- [ ] La richiesta al BE, tutta insieme, e la sua risposta (§4)

**I giri** (si scrivono dopo le decisioni e la risposta del BE; forma se passano le proposte)

- [ ] Giro 1: le porte di manutenzione (15, 17 se entra; la 14 secondo D-D), «GUC + proprietario», col pgTAP del controesempio come app
- [ ] Giro 2: gli interruttori del flusso diventano porte «sulla riga» (1-8, 10, 16), aprente e trigger insieme
- [ ] Le guide: ogni porta scritta nella guida del suo dominio, di flusso o di manutenzione
- [ ] D-A b: una voce per dominio nel registro dei residui aperti, che il cantiere di quel dominio raccoglie

## 1. Il problema, sul modello

Un trigger che protegge una regola («una riga d'ordine evasa non si cancella», «lo `stradario_id` di un indirizzo
non si cambia a mano») ha spesso una **porta**: una GUC transazionale che, accesa, lascia passare la scrittura
che la regola altrimenti ferma. La porta serve all'operazione legittima che deve passare dove gli altri no.

La D-V1 del 2026-09-25 (`work-done/2026/brief-db-magazzino-verbi-con-permesso`, strada A) ha stabilito che una
porta si apre con **due** condizioni in AND: la GUC dice **quale operazione su quale riga**, il proprietario della
tabella dice **chi scrive** («non l'app»). Con la sola GUC, la porta l'apre chiunque possa fare `set_config`
nella transazione, cioè anche l'applicazione, che può poi scrivere direttamente la tabella: la regola protegge
da un backend che **sbaglia** solo finché il backend non accende la GUC per sbaglio.

Le porte nate prima della D-V1 sono rimaste con la sola GUC. Non sono tutte un difetto: una porta di
**manutenzione** che si accende a mano, per una correzione fuori dal flusso, è una scelta, e va dichiarata come
tale. Questo brief le mette in fila e chiede, per ognuna, quale delle due è.

## 2. Le quindici porte — censite il 2026-11-23

Catalogo di dbdev: trigger che leggono una GUC con `current_setting` senza chiedere `fn_is_proprietario_tabella`,
su tabelle in cui `zeroerp_app` ha `INSERT`, `UPDATE` e `DELETE`. Chi accende la GUC lato DB è letto dal corpo
delle funzioni (`set_config`); il backend non è stato letto (perimetro DB).

| # | Porta (GUC) | Trigger | Tabella | Che cosa lascia passare | Chi la accende a DB |
| --- | --- | --- | --- | --- | --- |
| 1 | `zeroerp.maintenance_reset_lotto_draft` | `vendite.trgfn_attivita_fatturabili_guard_fatturato` | `vendite.attivita_fatturabili` | il reset di un lotto di fatturazione in bozza | `vendite.fn_cleanup_fatture_by_ids` (INVOKER) |
| 2 | idem | `vendite.trgfn_attivita_fatturabili_guard_quantita_immutabile` | `vendite.attivita_fatturabili` | idem | idem |
| 3 | idem | `vendite.trgfn_commesse_attivita_guard_quantita_immutabile` | `vendite.commesse_attivita` | idem | idem |
| 4 | idem | `vendite.trgfn_commesse_guard_chiave_immutabile` | `vendite.commesse` | idem | idem |
| 5 | idem | `vendite.trgfn_fattura_satellite_guard_congelamento` | `vendite.fatture` e quattro satelliti | idem | idem |
| 6 | idem | `vendite.trgfn_fatturazione_lotti_guard_stato` | `vendite.fatturazione_lotti` | idem | idem |
| 7 | idem | `vendite.trgfn_logs_guard_delete` | `vendite.fatturazione_lotti_log`, `vendite.fatture_log` | idem | idem |
| 8 | `zeroerp.allow_contabile_riga_delete_override` | `pagamenti.trgfn_vendite_contabili_righe_guard_contenuto` | `pagamenti.vendite_contabili_righe` | la cancellazione di una riga del contabile | ~~nessuna funzione DB~~ ⚠️ `vendite.fn_cancella_fondo_fattura` (INVOKER, `SET LOCAL`; §3-bis) |
| 9 | `app.registrazione_tardiva_riga_id` | `pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale` | `pagamenti.vendite_contabili_righe` | la registrazione tardiva su una distinta finale | `pagamenti.fn_posta_riga_tardiva` (INVOKER) |
| 10 | `zeroerp.allow_user_emittente_delete_override` | `config.trgfn_user_emittenti_fiscali_guard_delete` | `config.user_emittenti_fiscali` | la cancellazione del legame utente-emittente | ~~nessuna funzione DB~~ ⚠️ `script.fn_change_user_emittenti_scope` (INVOKER, `SET LOCAL`; §3-bis) |
| 11 | `zeroerp.ddt_riconsegna` | `script.trgfn_righe_guard_articolo_ammesso` | `vendite.ddt_righe` | una riga di riconsegna con un articolo non ammesso altrove | `vendite.fn_genera_ddt_riconsegna` (INVOKER) |
| 12 | `zeroerp.ddt_riga_ritira_legame` (solo `DELETE`) | `vendite.trgfn_ddt_riga_legame_guard` | `vendite.ordini_righe_fulfillment` | il ritiro del legame fuori bozza (con la seconda condizione: bozza, o la porta del ritiro della bolla) | `vendite.fn_ddt_riga_ritira_legami` (INVOKER) |
| 13 | idem | idem | `vendite.resi_righe_riconsegne` | idem | idem |
| 14 | `zeroerp.maintenance_indirizzi_dettaglio` | `anagrafiche.trgfn_indirizzi_dettaglio_protect_update` | `anagrafiche.indirizzi_dettaglio` | il cambio di `stradario_id` | `dbops.fn_admin_merge_stradario` (INVOKER) |
| 15 | `zeroerp.maintenance_toponomastica` | `config.trgfn_toponomastica_protect_update` | `config.toponomastica` | la modifica della toponomastica | `maintenance.proc_bump_toponomastica` (INVOKER) |
| 16 | `zeroerp.allow_template_versione_pubblicazione_override` | `documenti.trgfn_template_documenti_versioni_protect_pubblicata` | `documenti.template_documenti_versioni` | l'uscita dalla bozza verso `PUBBLICATA` (⚠️ aggiunta il 2026-11-23, §3-bis) | `documenti.fn_pubblica_template_documento_versione` (INVOKER) |
| 17 | `myapp.bypass_tx_id_check` | `dbops.trgfn_tx_id_managed` | tutte le tabelle col `tx_id` | la scrittura senza un `tx_id` registrato (⚠️ aggiunta il 2026-11-23, §3-bis) | nessuna funzione DB: la guida del `tx_id` la dichiara un interruttore di debug, test e migrazioni |

⚠️ **Correzioni del 2026-11-23 (analisi critica, §3-bis)**: il censimento cercava gli aprenti solo per `set_config` e
non per `SET LOCAL`, e scartava i trigger il cui corpo **nomina** `fn_is_proprietario_tabella`, invece di guardare se
c'è un **ramo** che apre con la sola GUC. Da qui le porte 8 e 10 senza aprente (lo hanno), e le porte 16 (GUC **o**
proprietario: il proprietario è l'eccezione del seed, la GUC apre da sola) e 17, mancanti. La 16 smentisce anche la
riga «sicura» di §5.8 del brief archiviato. Le porte 12-13 sono censite bene: il trigger chiede il proprietario solo
sul ramo della correzione della quantità.

⚠️ È una fotografia del catalogo al 2026-11-23: la lista si rilegge al primo giro. Fuori dal censimento le porte
che chiedono già il proprietario (§5.8 del brief archiviato) e i trigger che leggono la GUC dell'utente
(`app.jwt_user`, `app.current_user_id`), che non sono porte.

## 3. Decisioni aperte — a Tid

| # | Domanda | Strade | Raccomandazione |
| --- | --- | --- | --- |
| **D-1** | Le porte che servono a un'operazione del flusso (1-7, 9, 11-13): si portano a «GUC + proprietario»? | **a** sì: l'operazione diventa (o è chiamata da) un verbo DEFINER, e il trigger aggiunge `fn_is_proprietario_tabella`, come la D-V1 · **b** no, restano con la sola GUC, dichiarate | ⭐ **a**: è la D-V1 applicata alle porte nate prima. Chi accende oggi la GUC sono funzioni INVOKER: si guarda per ognuna se è già chiamata da un verbo DEFINER, o se la chiama il backend |
| ~~**D-2**~~ ⚠️ premessa smentita: le porte 8 e 10 hanno un aprente a DB (§2, §3-bis) | Le porte senza una funzione DB che le accenda (8, 10): chi le usa? | **a** il backend: diventano un verbo, e si torna a D-1 · **b** nessuno, sono porte di manutenzione a mano: restano, dichiarate · **c** nessuno e non servono: si ritirano | da decidere dopo la ricognizione dei chiamanti (§4) |
| **D-3** | Le porte di manutenzione (14, 15, e quelle che D-2 dichiara tali): come si dichiarano? | **a** restano con la sola GUC, scritte nella guida come porte di manutenzione · **b** chiedono anche un ruolo (il migratore, `session_user`) | ⭐ **a** finché non c'è un controesempio: la manutenzione la fa chi ha in mano la connessione |

## 3-bis. Analisi critica — 2026-11-23

Riletta sul catalogo di dbdev (corpi, privilegi, RLS) e sulla storia della D-V1. ⚠️ Corregge §2 e rende superata la
domanda D-2 di §3; le tre domande di §3 restano scritte, le proposte che le sostituiscono sono in §3-bis.4, da
decidere.

### 3-bis.1 Che cosa ha deciso davvero la D-V1

La D-V1 (2026-09-25) ha chiuso **una** porta, in un dominio che stava passando al modello del verbo: la registrazione
dei documenti di magazzino, aperta da un verbo DEFINER col suo guard. La guida dei permessi (§7.4) scrive la regola
dentro quel modello: l'app perde la scrittura, il verbo gira come proprietario e **rimette il perimetro**, il guard
chiede `fn_is_proprietario_tabella` per sapere se è attraversato da un verbo; i domini esistenti «ci passano quando un
lavoro tocca le loro scritture, uno alla volta». Estendere «GUC + proprietario» alle porte di questo brief **non è
la D-V1 applicata**: è far passare al modello del verbo le operazioni che le aprono. Si dichiara così.

### 3-bis.2 Il costo nascosto della strada D-1 a

Tutti gli aprenti di §2 sono INVOKER, eseguibili da `zeroerp_app`, e **nessuna funzione DEFINER li chiama**: li chiama
il backend. Il proprietario, dentro, non c'è mai. Perché la porta lo chieda, l'aprente (o il verbo d'ingresso che lo
chiama) deve diventare DEFINER, e allora:

- ha il **guard del permesso** in prima riga (§7.4), cioè un'azione o un livello per ciascuna operazione;
- **rimette il perimetro**: le tabelle delle porte 1-9 e 11-13 hanno la RLS **senza** `FORCE`, e il proprietario non
  la subisce. Un DEFINER senza perimetro farebbe scrivere all'app le righe di un altro emittente: peggio di oggi;
- il confine DEFINER va sul **verbo d'ingresso**, non sulla primitiva: `vendite.fn_cleanup_fatture_by_ids` è chiamata
  da almeno sei funzioni (annullo e ritorno in bozza del lotto, eliminazione di una fattura dal lotto, reset dei fondi,
  i `fn_check_*`), ognuna con la sua azione;
- il verbo spegne la GUC nel guard comune (la regola nata da §5.6 del brief archiviato).

### 3-bis.3 Due famiglie di porte, non una

| Famiglia | Porte | La GUC dice | Rispetto alla D-V1 |
| --- | --- | --- | --- |
| **Interruttore** | 1-8, 10, 14-17 | `on`/`true`: tutte le righe, per tutta la transazione | manca anche la prima condizione: «quale operazione su quale riga» |
| **Sulla riga** | 9, 11, 12-13 | l'id della riga (o del reso) | manca solo il proprietario |

Portare un interruttore a «sulla riga» è locale al trigger e al suo aprente: niente DEFINER, niente perimetro, nessuna
firma che cambia. Non ferma un backend che accende la GUC apposta, ma restringe ciò che apre a una riga.

**Le porte di manutenzione.** L'argomento di D-3 a («la manutenzione la fa chi ha in mano la connessione») non regge:
la connessione ce l'ha anche l'app, che ha `USAGE` su `dbops` e `maintenance` ed `EXECUTE` su
`fn_admin_merge_stradario` e `proc_bump_toponomastica`. Per la manutenzione «GUC + proprietario» costa poco: chi la fa
è `zeroerp_owner` (guida dei permessi §7.6), quindi basta il BB nel trigger, senza DEFINER. Il prezzo è che l'app non
potrà più chiamare quelle procedure con successo: lo dice la ricognizione BE.

**La porta 14** è nel tema T7 di `brief-db-revisione-anagrafiche` (S50), che Tid ha tenuto lì il 2026-11-23. La
regola si decide in un posto solo: qui; la sua applicazione alla porta 14 in uno dei due brief, non in entrambi.
Accanto: `riclassificazione-vie` dice in due punti diversi che la porta la apre `fn_admin_merge_stradario` e che resta
«la porta del verbo che sposterà gli indirizzi, quando nascerà» (guida indietro, si allinea col giro della porta 14).

### 3-bis.4 Le decisioni proposte, al posto di §3

| # | Domanda | Strade | Proposta |
| --- | --- | --- | --- |
| **D-A** | Le porte del flusso (1-13, 16) passano a «GUC + proprietario»? | **a** sì, ora: le operazioni che le aprono diventano verbi DEFINER con guard e perimetro · **b** sì, dominio per dominio, quando un cantiere tocca quelle scritture (fatturazione, contabile, DDT, scope emittenti, template); intanto D-B · **c** no, restano con la sola GUC, dichiarate nelle guide | ⭐ **b**: è la regola di §7.4 («uno alla volta»), e la strada **a** è il passaggio al verbo di quattro domini in un brief |
| **D-B** | Gli interruttori del flusso (1-8, 10, 16) diventano porte «sulla riga»? | **a** sì, in questo brief · **b** no, aspettano D-A | ⭐ **a**: è la prima metà della D-V1, costa un trigger e un aprente per porta |
| **D-C** | Le porte di manutenzione (14, 15, 17) chiedono anche il proprietario? | **a** no, solo GUC, dichiarate · **b** sì, `fn_is_proprietario_tabella` nel trigger | ⭐ **b**, se la ricognizione BE non trova l'app fra i chiamanti; la 17 (il `tx_id`) può anche restare fuori, dichiarata: non protegge una regola di dominio |
| **D-D** | La porta 14: qui o nel giro T7 di `brief-db-revisione-anagrafiche`? | **a** qui · **b** in T7, con la regola decisa qui | **b**: T7 tocca già lo stesso trigger per S50 |

## 4. Che cosa si fa dopo le decisioni

* **La ricognizione dei chiamanti**, porta per porta: le funzioni DB che accendono la GUC e chi le chiama
  (`pg_depend` per le `BEGIN ATOMIC`, il corpo per le altre). Per il backend, una richiesta al team BE: «censisci
  dove il backend accende `<GUC>` e perché», con l'elenco chiuso delle GUC di §2.
* **I giri**: per ogni porta che passa a «GUC + proprietario», il trigger nuovo, il verbo che la apre, il pgTAP
  del controesempio (la GUC accesa dall'app e una scrittura diretta: deve fermarsi), e le guide che la descrivono.
* Le garanzie che cambiano si censiscono nei lettori (`.codex/AGENTS.md`, «Una garanzia ritirata»): qui si
  **stringe** una porta, e il lettore da censire è chi la apre oggi.

## Registro

| Data | Chi | Che cosa |
| --- | --- | --- |
| 2026-11-23 | DB | Brief aperto su richiesta di Tid, dalla ricognizione §5.8 di `brief-db-magazzino-tutte-le-scritture-dal-verbo`: quindici porte censite sul catalogo, tre decisioni |
| 2026-11-23 | DB | Analisi critica (§3-bis): aprenti delle porte 8 e 10 trovati (`SET LOCAL`), porte 16 e 17 aggiunte, D-2 superata; la strada D-1 a riletta come passaggio al modello del verbo; D-A … D-D proposte |
