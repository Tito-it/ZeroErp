# Brief DB — le porte che si aprono con la sola GUC

> **⏭️ Chi riparte — aggiornato al 2026-11-23**
>
> **Riparte: Tid**, con la lettura delle quindici porte (§2) e la scelta, porta per porta, della strada (§3).
> Aperto, non iniziato: nessuna riga di codice.
>
> | # | Chi | Che cosa | Dove | Aspetta |
> | --- | --- | --- | --- | --- |
> | 1 | team DB | ✅ censimento delle porte sul catalogo di dbdev (2026-11-23) | §2 | — |
> | 2 | Tid | la strada per ogni porta: D-1 … D-3 | §3 | — |
> | 3 | team DB | ricognizione dei chiamanti di ogni porta (chi accende la GUC, da dove), poi i giri | §4 | 2 |
> | 4 | team BE | il censimento lato backend delle GUC che accende (richiesta da scrivere col giro) | §4 | 3 |
>
> Decisioni aperte di Tid: D-1 … D-3 (§3). Da committare: niente oltre questo file.
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

## Il piano da percorrere

**Prima di scrivere**

- [x] Censimento delle porte sul catalogo (2026-11-23, §2)
- [ ] Le decisioni di Tid, D-1 … D-3 (§3)
- [ ] La ricognizione dei chiamanti, porta per porta (§4)

**I giri** (si scrivono dopo le decisioni)

- [ ] Le porte che passano a «GUC + proprietario»
- [ ] Le porte di manutenzione che restano, dichiarate come tali
- [ ] Le richieste al BE, tutte insieme

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
| 8 | `zeroerp.allow_contabile_riga_delete_override` | `pagamenti.trgfn_vendite_contabili_righe_guard_contenuto` | `pagamenti.vendite_contabili_righe` | la cancellazione di una riga del contabile | nessuna funzione DB |
| 9 | `app.registrazione_tardiva_riga_id` | `pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale` | `pagamenti.vendite_contabili_righe` | la registrazione tardiva su una distinta finale | `pagamenti.fn_posta_riga_tardiva` (INVOKER) |
| 10 | `zeroerp.allow_user_emittente_delete_override` | `config.trgfn_user_emittenti_fiscali_guard_delete` | `config.user_emittenti_fiscali` | la cancellazione del legame utente-emittente | nessuna funzione DB |
| 11 | `zeroerp.ddt_riconsegna` | `script.trgfn_righe_guard_articolo_ammesso` | `vendite.ddt_righe` | una riga di riconsegna con un articolo non ammesso altrove | `vendite.fn_genera_ddt_riconsegna` (INVOKER) |
| 12 | `zeroerp.ddt_riga_ritira_legame` (solo `DELETE`) | `vendite.trgfn_ddt_riga_legame_guard` | `vendite.ordini_righe_fulfillment` | il ritiro del legame fuori bozza (con la seconda condizione: bozza, o la porta del ritiro della bolla) | `vendite.fn_ddt_riga_ritira_legami` (INVOKER) |
| 13 | idem | idem | `vendite.resi_righe_riconsegne` | idem | idem |
| 14 | `zeroerp.maintenance_indirizzi_dettaglio` | `anagrafiche.trgfn_indirizzi_dettaglio_protect_update` | `anagrafiche.indirizzi_dettaglio` | il cambio di `stradario_id` | `dbops.fn_admin_merge_stradario` (INVOKER) |
| 15 | `zeroerp.maintenance_toponomastica` | `config.trgfn_toponomastica_protect_update` | `config.toponomastica` | la modifica della toponomastica | `maintenance.proc_bump_toponomastica` (INVOKER) |

⚠️ È una fotografia del catalogo al 2026-11-23: la lista si rilegge al primo giro. Fuori dal censimento le porte
che chiedono già il proprietario (§5.8 del brief archiviato) e i trigger che leggono la GUC dell'utente
(`app.jwt_user`, `app.current_user_id`), che non sono porte.

## 3. Decisioni aperte — a Tid

| # | Domanda | Strade | Raccomandazione |
| --- | --- | --- | --- |
| **D-1** | Le porte che servono a un'operazione del flusso (1-7, 9, 11-13): si portano a «GUC + proprietario»? | **a** sì: l'operazione diventa (o è chiamata da) un verbo DEFINER, e il trigger aggiunge `fn_is_proprietario_tabella`, come la D-V1 · **b** no, restano con la sola GUC, dichiarate | ⭐ **a**: è la D-V1 applicata alle porte nate prima. Chi accende oggi la GUC sono funzioni INVOKER: si guarda per ognuna se è già chiamata da un verbo DEFINER, o se la chiama il backend |
| **D-2** | Le porte senza una funzione DB che le accenda (8, 10): chi le usa? | **a** il backend: diventano un verbo, e si torna a D-1 · **b** nessuno, sono porte di manutenzione a mano: restano, dichiarate · **c** nessuno e non servono: si ritirano | da decidere dopo la ricognizione dei chiamanti (§4) |
| **D-3** | Le porte di manutenzione (14, 15, e quelle che D-2 dichiara tali): come si dichiarano? | **a** restano con la sola GUC, scritte nella guida come porte di manutenzione · **b** chiedono anche un ruolo (il migratore, `session_user`) | ⭐ **a** finché non c'è un controesempio: la manutenzione la fa chi ha in mano la connessione |

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
