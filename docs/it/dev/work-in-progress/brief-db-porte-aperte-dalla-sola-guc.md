# Brief DB — le strade per cui l'app scrive senza il verbo: le porte della sola GUC e le viste aggiornabili

> **⏭️ Chi riparte — aggiornato al 2026-11-24**
>
> **Riparte: il team DB, leggendo la risposta del BE alla richiesta 3d (§4.5, 2026-11-24)**, poi il giro 12-13 (un
> pgTAP e la guida, D-E a) e i giri delle porte del flusso, al via di Tid. Il superuser Django è deciso (D-J **a**) e
> fatto nel BE (§4.7). D-K (il primo amministratore di un'installazione nuova) è decisa: al team DB la richiesta
> R-DB-K1 del verbo di primo impianto, poi il BE col comando (§4.7).
> ✅ Fatti e verdi (Tid, 2026-11-24): giro 1 (porte di manutenzione 14 e 15, la 17 dichiarata), giro 1-bis (la
> fusione dei comuni, il presidio di `maintenance`), giro 3 (le viste in sola lettura per l'app, con la fase `post`
> del provisioning su dbdev). Tutto applicato e committato.
> Decise: D-A **a**, D-C **b** per 14 e 15, D-D **a** (2026-11-23); dalla verifica critica (§3-ter) D-E **a** e D-F
> **a** (2026-11-23); D-G **a**, D-H **a** (2026-11-24); D-B decaduta. Il brief ospita anche la seconda famiglia di
> strade, **le viste aggiornabili** (§5, D-V), nata dal giro 2 di `brief-db-revisione-anagrafiche` (§19).
>
> | # | Chi | Che cosa | Dove | Aspetta |
> | --- | --- | --- | --- | --- |
> | 1 | team DB | ✅ censimento delle porte sul catalogo di dbdev (2026-11-23), ✅ corretto dall'analisi critica: diciassette porte | §2, §3-bis | — |
> | 1b | team DB | ✅ la seconda famiglia, le viste aggiornabili: censite e decise da Tid (D-V, 2026-11-23) | §5 | — |
> | 2 | Tid | ✅ D-A (**a**) · ✅ D-C (**b**) · ✅ D-D (**a**), 2026-11-23 | §3-bis.4, §4.3 | — |
> | 3 | team DB | ✅ la richiesta unica al BE: chi accende le GUC, chi chiama gli aprenti, chi scrive su una vista (2026-11-23) | §4.1 | — |
> | 3b | Tid | ✅ superato: la Parte B l'ha risposta il BE, la Parte A l'ha letta il DB (2026-11-23) | §4.1 | — |
> | 3c | Tid | ✅ D-E (**a**) · ✅ D-F (**a**), 2026-11-23 | §3-ter | — |
> | 3d | team BE | la richiesta 3d: ✅ scritta e precompilata dal DB (2026-11-24); ✅ risposta del BE (2026-11-24) | §4.4, §4.5 | — |
> | 3e | team DB | leggere la risposta 3d: le due correzioni a §4.3 (azioni delle porte 1-7 e 11), i test della Parte C, il task `reset_lotto_draft` | §4.5 | — |
> | 3f | Tid | ✅ D-I: il task `reset_lotto_draft` si ritira · ✅ D-J: il superuser Django non concede più niente, strada **a** (2026-11-24) | §4.6 | — |
> | 3h | team BE | D-J: ✅ bypass tolti, test adeguati, suite verde (2026-11-24); da rivedere con `/verifica` | §4.7 | — |
> | 3i | team DB | D-K: il verbo `fn_crea_primo_amministratore` e la sua prova (R-DB-K1); la porta di `fn_crea_operatore_v2` nel piano dei giri (R-DB-K2) | §4.7 | — |
> | 3j | team BE | D-K: il comando `crea_primo_amministratore`, il playbook e `configurazione-django.md` senza `createsuperuser` | §4.7 | 3i |
> | 3g | team DB, poi team BE | il ritiro del task `reset_lotto_draft`: prima i CSV del DB, poi il BE | §4.6 | — |
> | 4 | team BE / DB | ✅ Parte B, le viste: «nessuno», dal BE (2026-11-23) · ✅ Parte A, le GUC e gli aprenti: letta dal DB sul ramo del BE (2026-11-23) | §4.2, §5.1 | — |
> | 4a | Tid | ✅ il giro 1: applicato, pgTAP verdi (2026-11-24) | §6 | — |
> | 4c | Tid | ✅ D-G (**a**) · ✅ D-H (**a**), 2026-11-24 | §6.4, §6.5 | — |
> | 4d | Tid | ✅ l'apply di `20261123-46`, pgTAP verdi · ✅ il pgTAP di D-H come app, verde (2026-11-24) | §6.5 | — |
> | 4b | team DB | ✅ il giro 3, le viste: scritto e provato sullo scratch (2026-11-24) | §7 | — |
> | 4e | Tid | ✅ il giro 3: apply, `ci_apply`, fase `post` del provisioning su dbdev, pgTAP verde (2026-11-24) | §7.4 | — |
> | 5 | Tid / team BE | ✅ la richiesta 3d girata al BE, e la risposta (2026-11-24) | §4.5 | — |
> | 6 | team DB | i giri delle porte del flusso | Il piano | 3e; 3f per i giri 16 e 1-7 |
> | 5 | Tid / team BE | la richiesta 3d girata al BE, e la risposta | §4.4 | — |
> | 5b | team DB | ✅ il giro 12-13, verde come app (2026-11-24) | §8 | — |
> | 6 | team DB | i giri delle porte del flusso 16, 10, 9, 11, 8, 1-7 | Il piano | 3d |
>
> Decisioni aperte di Tid: nessuna. Committati il 2026-11-24 i giri 1, 1-bis e 3 (`64f00b35b1`) e il giro 12-13
> (`969ea14566`). Da committare: niente di questo brief; le due righe di `brief-db-revisione-anagrafiche` che
> rimandano qui le porta il commit dell'altra sessione, che ha quel brief in lavorazione.
>
> **Brief vicini verificati (2026-11-23):**
> [brief-db-magazzino-tutte-le-scritture-dal-verbo](../work-done/2026/brief-db-magazzino-tutte-le-scritture-dal-verbo.md)
> (archiviato), da cui nasce: la sua §5.8 ha ricercato la classe vicina, la porta «GUC + proprietario» attraversata
> da un verbo DEFINER, senza trovare altri casi; questa è un'altra classe. `brief-db-revisione-anagrafiche`,
> segnalazione **S50**, nomina la porta `zeroerp.maintenance_indirizzi_dettaglio` («un parametro di sessione che
> chiunque scriva accende»): è una delle diciassette. Se Tid la decide lì, qui si toglie; nel dubbio, decide Tid
> dove la si tratta. ✅ Decisa qui (D-D, 2026-11-23): S50 la rimanda a questo brief. `brief-db-revisione-ui`: nomina `fn_is_proprietario_tabella` per altro, nessuna sovrapposizione.
> [brief-incassi-riconciliazione-rate-promemoria](brief-incassi-riconciliazione-rate-promemoria.md) (il cantiere
> «contabili di pagamento», aperto; ⚠️ trovato il 2026-11-23, dopo la D-A): possiede le decisioni sulle funzioni delle
> porte 8 e 9 (D10-D11 sul fondo, D20-b la registrazione tardiva con `fn_posta_riga_tardiva`). Non cambia la D-A, che
> non tocca **cosa** fanno quelle funzioni ma **come girano**; i giri delle porte 8 e 9 rileggono quelle decisioni
> prima di scrivere il verbo, e le portano nei pgTAP.
> [brief-db-revisione-anagrafiche](brief-db-revisione-anagrafiche.md) §19 (giro 2, T2): ha trovato la seconda famiglia
> (§5) e l'ha portata qui il 2026-11-23, con la decisione di Tid; lì resta l'analisi sul catalogo di `anagrafiche`.
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
> Rilancio del 2026-11-23 sulle sei viste di §5:
> [configurazione-liste](../../guide/configurazione-liste.md) (`vw_liste_multi_emittente_non_certificate`) e
> [processi-automatici-classe-e-identita](../../guide/processi-automatici-classe-e-identita.md)
> (`vw_processi_dominio_su_pgagent`) le descrivono come controlli in lettura: **coerenti**.
> [architettura-permessi-e-autorizzazioni](../../guide/architettura-permessi-e-autorizzazioni.md) §7.4 «La porta» non
> nomina le viste: **indietro** quando la D-V entra nel codice, si completa in quel giro. Orfani:
> `catalogo.vw_causali_onere_assegnabili`, `dbops.vw_emittenti_regime_non_confermato`, `script.vw_audit_sources`,
> `script.vw_stati_estesi` (proiezioni interne, nessuna guida da scrivere).

## Il piano da percorrere

**Prima di scrivere**

- [x] Censimento delle porte sul catalogo (2026-11-23, §2)
- [x] Analisi critica: censimento corretto, decisioni riformulate (2026-11-23, §3-bis)
- [x] La seconda famiglia, le viste aggiornabili: censite, decise da Tid (D-V, 2026-11-23, §5)
- [x] D-A decisa da Tid: strada **a**, tutte le porte del flusso ora (2026-11-23, §4.3); D-B decaduta
- [x] D-C decisa da Tid: strada **b** per 14, 15 e 17, la 17 chiusa con tutte e due le chiavi (2026-11-23); ⚠️ per la 17 superata da D-F
- [x] Verifica critica a decisioni prese (2026-11-23, §3-ter)
- [x] D-E decisa da Tid: **a**, la bozza delle 12-13 resta con la GUC sulla riga, dichiarata (2026-11-23)
- [x] D-F decisa da Tid: **a**, la 17 esce dalla D-C, dichiarata interruttore di timbratura (2026-11-23)
- [x] D-D decisa da Tid: la porta 14 qui, nel giro 1 con la 15 (2026-11-23); in `brief-db-revisione-anagrafiche` S50 la rimanda qui
- [x] La richiesta unica al BE, scritta (2026-11-23, §4.1)
- [x] La Parte B della richiesta (le viste): il BE risponde «nessuno», limiti verificati sul catalogo (2026-11-23, §5.1)
- [x] La Parte A della richiesta (le GUC e gli aprenti): letta dal DB su `origin/dev/backend-tid` `f1b8f9df7a` (2026-11-23, §4.2)

**I giri** (si scrivono dopo le decisioni e la risposta del BE; forma se passano le proposte)

- [x] Giro 1 (2026-11-24, applicato da Tid, pgTAP verdi): le porte di manutenzione (D-C b), «GUC + proprietario» nel trigger, nessun DEFINER: la manutenzione la fa
  `zeroerp_owner`. Per ognuna il pgTAP del controesempio **come app** (GUC accesa, scrittura diretta: si ferma) e quello
  del proprietario (passa); la guida che la descrive dice «porta di manutenzione, solo dal proprietario»
  - [x] scritto e provato sullo scratch il 2026-11-23, applicato e pgTAP verdi il 2026-11-24 (§6)
  - [x] 15, la toponomastica (`riclassificazione-vie`): `20_code/config/20261123-44`
  - [x] 14, gli indirizzi di una via (D-D a: qui, con la 15; `riclassificazione-vie` indietro, §3-bis.3; `gestione-degli-indirizzi`): `20_code/anagrafiche/20261123-43`
  - [x] 14 e 15: i due aprenti riservati al proprietario (§3-ter.4): `90_end/20261123-45`, `v_fn_riservate` del loop, provisioning
  - [x] 17, il `tx_id` (D-F a): nessun codice; guida scritta il 2026-11-23. La guida `tx_id_implementation_guide` dice che la GUC e la riga
    `tx_id_bypass_enabled` sono un interruttore di **timbratura**, non una porta: il trigger non rifiuta mai una
    scrittura, e un `tx_id` scritto a mano passa comunque (§3-ter.1). ~~Tutte e due le chiavi al proprietario~~ ⚠️ superato
    da D-F. Il tema «una riga con un `tx_id` non registrato si rifiuta» non è aperto qui
- [ ] ~~Giro 2: gli interruttori del flusso diventano porte «sulla riga»~~ ⚠️ decaduto con D-A a: la GUC sulla riga entra nel giro di ogni porta
- [x] Prima dei giri delle porte del flusso, la tabella «verbo d'ingresso → azione che l'endpoint controlla» dal BE, e
  il profilo dell'utente tecnico della pipeline (§4.3, soluzione 2): ✅ richiesta scritta e precompilata il 2026-11-24
  (§4.4); ✅ risposta del BE il 2026-11-24 (§4.5), da leggere dal DB
- [ ] Giri delle porte del flusso (D-A a), uno per riga, in quest'ordine. ⛔ Ognuno chiude **tutte** queste voci, o non è chiuso:
  - **il verbo**: DEFINER sul verbo d'ingresso, guard in prima riga con la **stessa azione** dell'endpoint
    (soluzione 2), la GUC spenta all'ingresso e riaccesa **sulla riga**, le primitive senza `EXECUTE` all'app;
  - **il perimetro** (soluzione 1): **un** controllo d'ambito all'ingresso, sull'oggetto padre (lotto, fattura,
    reso, riga del contabile), e la rete di `trgfn_guard_emittente_scope` dove c'è; nessun filtro ricopiato query
    per query;
  - **il trigger**: «GUC sulla riga **e** proprietario»;
  - **i pgTAP**: il controesempio (GUC accesa dall'app e scrittura diretta: si ferma), **due emittenti** (il verbo
    sull'oggetto dell'altro: si ferma), l'utente senza l'azione (`E_PERMESSO_NEGATO`), i pgTAP esistenti che
    scrivono diretti portati al verbo o al seed;
  - le primitive chiuse si scrivono in `v_fn_riservate`, nelle tre sedi di §11.8 (§3-ter.4);
  - nei giri 8 e 1-7: `vendite.fn_check_fondo_cancellabile`, che salta il controllo della figlia congelata con la GUC del reset (§3-ter.3);
  - la guida del dominio e la richiesta al BE del giro.
  - [x] 12-13, i legami della bolla (D-E a, 2026-11-24, pgTAP verde come app; §8): niente da cambiare nel trigger
    (il ramo fuori bozza chiede già il proprietario, §3-ter.2). Un pgTAP che fissa i due rami (come app, fuori bozza
    con le GUC: si ferma; in bozza con la GUC sulla riga: passa) e la guida che dichiara la bozza «sola GUC sulla
    riga» come scelta
  - [ ] 16, il template: il verbo, e il trigger che distingue il seed dal verbo
  - [ ] 10, lo scope emittenti: il verbo con `fn_guard_super_admin` (nessuna RLS)
  - [ ] 9, la registrazione tardiva: da qui si prova il perimetro; prima si rilegge la D20-b di `brief-incassi-riconciliazione-rate-promemoria`
  - [ ] 11, la bolla di riconsegna
  - [ ] 8, il fondo fattura: verbo pubblico e primitiva separati; prima si rileggono D10-D11 dello stesso brief
  - [ ] 1-7, il reset del lotto: quattro verbi d'ingresso, due primitive chiuse
- [x] Giro 3 (2026-11-24, applicato da Tid con la fase `post` del provisioning, pgTAP verde; §7): le viste (§5): ~~prima i verbi delle scritture che il BE trova~~ (nessuna, §5.1), l'app con solo `SELECT` sulle viste,
  nelle tre sedi di `linee-guida-sql.md` §11.8, col pgTAP di postura a criterio e la guida dei permessi §7.4;
  il caso costruito passa dal criterio del loop, non da un `REVOKE` nel test (i privilegi di default danno il DML anche alle viste, §3-ter.4)
- [ ] Le guide: ogni porta scritta nella guida del suo dominio, di flusso o di manutenzione

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

## 2. Le porte — censite il 2026-11-23 (quindici, diciassette dopo §3-bis)

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
| 17 | `myapp.bypass_tx_id_check` | `dbops.trgfn_tx_id_managed` | tutte le tabelle col `tx_id` | la scrittura senza un `tx_id` registrato (⚠️ aggiunta il 2026-11-23, §3-bis) | nessuna funzione DB: la guida del `tx_id` la dichiara un interruttore di debug, test e migrazioni. ⚠️ Ha una **seconda chiave**, la riga `tx_id_bypass_enabled` di `config.parameters`, che l'app può scrivere (`INSERT`, `UPDATE`, catalogo 2026-11-23): accesa lì, il bypass vale per tutti, non per una transazione |

⚠️ **Correzioni del 2026-11-23 (analisi critica, §3-bis)**: il censimento cercava gli aprenti solo per `set_config` e
non per `SET LOCAL`, e scartava i trigger il cui corpo **nomina** `fn_is_proprietario_tabella`, invece di guardare se
c'è un **ramo** che apre con la sola GUC. Da qui le porte 8 e 10 senza aprente (lo hanno), e le porte 16 (GUC **o**
proprietario: il proprietario è l'eccezione del seed, la GUC apre da sola) e 17, mancanti. La 16 smentisce anche la
riga «sicura» di §5.8 del brief archiviato. ~~Le porte 12-13 sono censite bene: il trigger chiede il proprietario solo
sul ramo della correzione della quantità.~~ ⚠️ Falso (§3-ter.2): il ramo fuori bozza chiede il proprietario dentro
`vendite.fn_doc_porta_ritiro_ammette`; la sola GUC apre il ramo della bozza.

⚠️ È una fotografia del catalogo al 2026-11-23: la lista si rilegge al primo giro. Fuori dal censimento le porte
che chiedono già il proprietario (§5.8 del brief archiviato) e i trigger che leggono la GUC dell'utente
(`app.jwt_user`, `app.current_user_id`), che non sono porte.

## 3. Decisioni aperte — a Tid

⚠️ Superata da §3-bis.4 (2026-11-23): D-1 … D-3 sono state riformulate in D-A … D-D, tutte decise. Resta scritta
perché le proposte di §3-bis la discutono.

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
| **D-A** | Le porte del flusso (1-13, 16) passano a «GUC + proprietario»? | **a** sì, ora: le operazioni che le aprono diventano verbi DEFINER con guard e perimetro · **b** sì, dominio per dominio, quando un cantiere tocca quelle scritture (fatturazione, contabile, DDT, scope emittenti, template); intanto D-B · **c** no, restano con la sola GUC, dichiarate nelle guide | ⭐ **b**: è la regola di §7.4 («uno alla volta»), e la strada **a** è il passaggio al verbo di quattro domini in un brief. ✅ **Decisa da Tid il 2026-11-23: a** (§4.3, con le soluzioni ai due rischi) |
| **D-B** | Gli interruttori del flusso (1-8, 10, 16) diventano porte «sulla riga»? | **a** sì, in questo brief · **b** no, aspettano D-A | ⭐ **a**: è la prima metà della D-V1, costa un trigger e un aprente per porta. ⚠️ **Decaduta** con D-A a: la GUC sulla riga entra nel giro di ogni porta |
| **D-C** | Le porte di manutenzione (14, 15, 17) chiedono anche il proprietario? | **a** no, solo GUC, dichiarate · **b** sì, `fn_is_proprietario_tabella` nel trigger | ⭐ **b**, se la ricognizione BE non trova l'app fra i chiamanti; la 17 (il `tx_id`) può anche restare fuori, dichiarata: non protegge una regola di dominio. ✅ **Decisa da Tid il 2026-11-23: b per tutte e tre, la 17 compresa, con la sua seconda chiave** (`config.parameters`) |
| **D-D** | La porta 14: qui o nel giro T7 di `brief-db-revisione-anagrafiche`? | **a** qui · **b** in T7, con la regola decisa qui | ✅ **Decisa da Tid il 2026-11-23: a.** ~~**b**: T7 tocca già lo stesso trigger per S50~~ ⚠️ non verificato, e falso (catalogo, 2026-11-23): `trgfn_indirizzi_dettaglio_protect_update` protegge solo `stradario_id`; le altre parti di S50 (il `NOT NULL` di `via_norm`, la forma libera, `geoloc`) stanno su altri oggetti. In comune con T7 c'è solo la porta. Proposta rivista: **a**, nel giro 1 con la 15 |

## 3-ter. Verifica critica a decisioni prese — 2026-11-23

Riletta sul catalogo di dbdev: corpi dei diciassette trigger, `prosecdef`, `pg_default_acl`, le azioni di
`config.azioni_processo`. Reggono: nessuna funzione di trigger delle porte è DEFINER (quindi
`fn_is_proprietario_tabella` dentro il trigger vede chi scrive davvero); le sei azioni citate in §4.3 esistono;
`fn_guard_super_admin` esiste; i sei `fn_annulla_*` sono DEFINER **e** rimettono il perimetro
(`fn_scope_ef_whitelist_via_*` sulla testata). Quattro punti non reggono.

### 3-ter.1 La porta 17 non ferma niente

`dbops.trgfn_tx_id_managed` **non rifiuta mai una scrittura**: decide solo quale `tx_id` timbrare.

- con `NEW.tx_id` già valorizzato esce subito, senza guardare il registro: l'app scrive una riga con un `tx_id`
  qualsiasi, anche non registrato, senza nessuna GUC;
- con un `dbops.tx_id` di sessione non registrato logga `W_TXID_NOT_REGISTERED` e timbra `uuid_nil()`, senza
  fermarsi;
- il bypass (GUC o riga di `config.parameters`) fa solo timbrare il `tx_id` di sessione o `uuid_nil()` invece di
  crearne uno.

La riga di §2 («lascia passare la scrittura senza un `tx_id` registrato») descrive una regola che il trigger non ha.
Chiudere le due chiavi con il proprietario non toglie all'app niente che non abbia già scrivendo il `tx_id` da sé.
La proposta di D-C lo diceva a metà («non protegge una regola di dominio»); la decisione **b** per la 17 è stata presa
sulla premessa sbagliata. La guida del `tx_id` lo descrive correttamente: è il brief a essere indietro.
Accanto: `config.parameters` ha già una colonna `ammette_override`; se un attributo «riservato al proprietario»
servirà, il giro parte da lì (regola del 2).

✅ **D-F decisa da Tid il 2026-11-23: a.**

**D-F**: **a** la 17 esce dal giro 1, dichiarata nella guida come interruttore di timbratura, senza
proprietario · **b** resta **b** con le due chiavi, sapendo che non chiude la strada del `tx_id` scritto a mano ·
**c** si apre il tema vero («una riga senza `tx_id` registrato si rifiuta»), che è un cambio di modello del `tx_id`
e un altro brief. ⭐ **a**: è l'unica che non promette una garanzia che il codice non dà.

### 3-ter.2 Le porte 12-13: il ramo fuori bozza chiede già il proprietario

Nel `DELETE` di `vendite.trgfn_ddt_riga_legame_guard` la porta è aperta se la GUC vale l'id della riga **e** se vale
una di queste: la bolla non si trova, la bolla non ha stato, la bolla è in bozza, oppure
`vendite.fn_doc_porta_ritiro_ammette`. Quest'ultima chiede già GUC `zeroerp.doc_ritira_legami` **e**
`fn_is_proprietario_tabella`. Il giro di §4.3 («il proprietario sul ramo fuori bozza») è quindi **già fatto**: non
cambierebbe niente. Le strade con la sola GUC sono la bozza e i due casi senza bolla o senza stato, che §4.3 tiene
aperti di proposito (li apre `trgfn_dlt_block_ordrig_ddtrig`, INVOKER, quando l'app cancella una riga in bozza).

✅ **D-E decisa da Tid il 2026-11-23: a.**

**D-E**: **a** le porte 12-13 si dichiarano chiuse dal lato del flusso confermato; il ramo della bozza resta
«sola GUC sulla riga», scritto nella guida come scelta (oggi la bozza la scrive l'app) · **b** anche la bozza al
proprietario: la cancellazione di una riga di bolla in bozza passa da un verbo DEFINER, ed è il passaggio al verbo
delle bozze di `vendite`, non un giro di questo brief. ⭐ **a**, con un pgTAP che fissi i due rami come sono.

### 3-ter.3 Una porta fuori dai trigger: `vendite.fn_check_fondo_cancellabile`

Il censimento cercava solo nelle funzioni di trigger. `vendite.fn_check_fondo_cancellabile`, funzione di criterio
(INVOKER, eseguibile dall'app), legge `zeroerp.maintenance_reset_lotto_draft` e, se è accesa, **salta il controllo
della figlia congelata**. La chiamano `vendite.fn_cancella_fondo_fattura` (che il BE chiama diretta, porta 8),
`fn_reset_fondi_fattura` e il trigger della porta 8. Quindi oggi l'app accende la GUC del reset del lotto e cancella
il fondo di una fattura figlia già congelata. Il commento della funzione dice il contrario («il gesto di una persona
questa GUC non ce l'ha e non può darsela»): è falso dal momento in cui l'app può fare `set_config`.

Nessuna decisione nuova: è un lettore della porta 1-7 e la D-A **a** lo copre. Entra nei giri 8 e 1-7 come voce
obbligatoria (la GUC sulla riga **e** il proprietario anche qui, o la funzione chiamata solo dal verbo). La guida
[fatturazione](../../guide/fatturazione.md) nomina la funzione come predicato: **coerente** oggi, da completare in
quei giri.

### 3-ter.4 Il pgTAP di postura delle viste, così scritto, non prova la regola

`pg_default_acl` di `zeroerp_owner` dà a `zeroerp_app` `arwd` su ogni relazione nuova dei quattordici schemi, e il
tipo `r` dei privilegi di default copre tabelle **e** viste. Una vista creata in un pgTAP nasce quindi col DML
all'app: il «caso costruito che risponde `42501`» (§5) è rosso, se il test non ripassa il loop, oppure verde per
sottrazione, se il test fa un `REVOKE` da sé. Il giro 3 deve far passare il caso costruito **dal criterio del loop**
(la stessa funzione o lo stesso elenco), e sapere che fra un `CREATE VIEW` e la passata `ci_apply` successiva la
vista ha il DML all'app, come ogni tabella di `v_tabelle_sola_lettura_app` (§11.8).

Lo stesso vale per le primitive delle porte del flusso: «senza `EXECUTE` all'app» si scrive in `v_fn_riservate`,
nelle tre sedi di §11.8, non con un `REVOKE`. Per le porte 14 e 15 il giro 1 mette lì anche
`dbops.fn_admin_merge_stradario` e `maintenance.proc_bump_toponomastica`: con la D-C **b** l'app che le chiama
riceve un errore dal trigger, meglio un `42501` all'ingresso.

## 4. Che cosa si fa dopo le decisioni

* **La ricognizione dei chiamanti**, porta per porta: le funzioni DB che accendono la GUC e chi le chiama
  (`pg_depend` per le `BEGIN ATOMIC`, il corpo per le altre). Per il backend, una richiesta al team BE: «censisci
  dove il backend accende `<GUC>` e perché», con l'elenco chiuso delle GUC di §2.
* **I giri**: per ogni porta che passa a «GUC + proprietario», il trigger nuovo, il verbo che la apre, il pgTAP
  del controesempio (la GUC accesa dall'app e una scrittura diretta: deve fermarsi), e le guide che la descrivono.
* Le garanzie che cambiano si censiscono nei lettori (`.codex/AGENTS.md`, «Una garanzia ritirata»): qui si
  **stringe** una porta, e il lettore da censire è chi la apre oggi.

⚠️ **2026-11-23: la ricognizione BE non aspetta le decisioni.** D-C la usa come premessa («se la ricognizione BE non
trova l'app fra i chiamanti»), e D-A, D-B e D-D non cambiano ciò che si chiede. La richiesta è una sola, per le due
famiglie (§4.1), e parte al via di Tid.

### 4.1 La richiesta unica al team BE/FE — scritta il 2026-11-23

> **Le strade per cui l'app scrive senza passare da un verbo.** Il DB sta chiudendo due strade per cui l'app può
> scrivere una tabella aggirando la regola «una scrittura = un verbo». Prima di cambiare, ci serve sapere dove il
> backend le usa oggi. Il DB non cambia niente finché non arriva la risposta.
>
> **Parte A — le porte aperte da una GUC.** Alcuni trigger lasciano passare una scrittura che di regola rifiutano,
> quando una GUC di sessione è accesa. Oggi basta la GUC, e il backend può accenderla. Per ognuna di queste dieci GUC:
> dove il backend la accende (`set_config`, `SET LOCAL`, `SET`, anche nei test e nelle fixture), e perché.
>
> | GUC | Che cosa lascia passare |
> | --- | --- |
> | `zeroerp.maintenance_reset_lotto_draft` | il reset di un lotto di fatturazione in bozza |
> | `zeroerp.allow_contabile_riga_delete_override` | la cancellazione di una riga del contabile |
> | `app.registrazione_tardiva_riga_id` | la registrazione tardiva su una distinta finale |
> | `zeroerp.allow_user_emittente_delete_override` | la cancellazione del legame utente-emittente |
> | `zeroerp.ddt_riconsegna` | una riga di riconsegna con un articolo non ammesso altrove |
> | `zeroerp.ddt_riga_ritira_legame` | il ritiro del legame di una riga di bolla fuori bozza |
> | `zeroerp.maintenance_indirizzi_dettaglio` | il cambio di `stradario_id` di un indirizzo |
> | `zeroerp.maintenance_toponomastica` | la modifica della toponomastica |
> | `zeroerp.allow_template_versione_pubblicazione_override` | la pubblicazione di una versione di template |
> | `myapp.bypass_tx_id_check` | la scrittura senza un `tx_id` registrato |
>
> E per ognuna di queste nove funzioni DB, che accendono una di quelle GUC: da dove il backend la chiama (endpoint,
> service, comando, job), o «da nessuna parte».
>
> `vendite.fn_cleanup_fatture_by_ids`, `vendite.fn_cancella_fondo_fattura`, `pagamenti.fn_posta_riga_tardiva`,
> `script.fn_change_user_emittenti_scope`, `vendite.fn_genera_ddt_riconsegna`, `vendite.fn_ddt_riga_ritira_legami`,
> `dbops.fn_admin_merge_stradario`, `maintenance.proc_bump_toponomastica`,
> `documenti.fn_pubblica_template_documento_versione`.
>
> **Parte B — le scritture su una vista.** Oggi `zeroerp_app` ha `INSERT`, `UPDATE` e `DELETE` su tutte le viste di
> ogni schema (tranne `maintenance`), perché il loop dei grant le conta fra le tabelle. Il DB toglierà quel permesso:
> sulle viste l'app avrà solo `SELECT`. Il motivo: una vista aggiornabile senza `security_invoker` scrive la tabella
> sotto coi permessi del suo proprietario, e aggira la sola lettura dell'app. Una scrittura su una vista non
> aggiornabile fallisce già oggi; quelle che riescono passano solo da queste quindici viste, le uniche aggiornabili
> (catalogo di dbdev, 2026-11-23):
>
> | Schema | Viste |
> | --- | --- |
> | `catalogo` | `vw_causali_onere_assegnabili` |
> | `config` | `vw_codici_errore_identita`, `vw_email_in_coda` |
> | `dbops` | `vw_af_senza_giro`, `vw_coda_lavori_da_guardare`, `vw_email_da_guardare`, `vw_emittenti_regime_non_confermato`, `vw_fatture_stampa_coda_da_guardare`, `vw_liste_multi_emittente_non_certificate`, `vw_magazzino_movimenti_senza_costo`, `vw_processi_dominio_su_pgagent` |
> | `documenti` | `vw_template_asset_utilizzabili` |
> | `script` | `vw_audit_sources`, `vw_stati_estesi` |
> | `vendite` | `vw_preventivi_righe_smistabili_ordine` |
>
> Dove il backend scrive (`INSERT`, `UPDATE`, `DELETE`, `MERGE`, `COPY … FROM`) su una vista: l'SQL scritto a mano
> (`cursor.execute`, `raw`, anche col nome costruito a runtime); i modelli `managed = False` con `db_table` su una
> vista, con `save`, `create`, `update`, `delete`, `bulk_*`, anche dall'admin; il pannello generico e le liste in
> modifica, quando la sorgente o la destinazione è una vista; i test e le fixture che scrivono su una vista con la
> connessione dell'app.
>
> **Come rispondere.** Un elenco chiuso, una riga per punto: `file:riga`, la GUC o la funzione o la vista,
> l'operazione, il dato di dominio che vuole cambiare, e il verbo DB che fa già la stessa cosa, se c'è. «Nessuno» è
> una risposta valida, se dice come si è cercato.
>
> **Chi cambia per primo.** Il DB, dopo la risposta. Dove il backend usa una di queste strade, il DB scrive prima il
> verbo che manca, il backend ci passa, e solo dopo il DB chiude la strada. Fino ad allora il backend non cambia
> niente.

### 4.2 La Parte A, letta sul ramo del BE — 2026-11-23

Su indicazione di Tid il DB ha letto il ramo `origin/dev/backend-tid` (commit `f1b8f9df7a`, sola lettura, nessuna
modifica a `backend/`), invece di aspettare la risposta del team. Il catalogo è quello di dbdev.

**Le dieci GUC: il BE non ne accende nessuna.** Ricerca dei dieci nomi su tutto il ramo fuori da `db/` e `docs/`
(codice, test, smoke, settings, CI): compaiono solo nei commenti di `error_policies_generated.py`, nei nomi delle
funzioni, e in `ci-validate.yaml:547`, che dice di **non** accendere `bypass_tx_id_check`. Tutte le accensioni del BE
(`set_config`, `SET LOCAL`, anche col nome in una variabile) sono le GUC d'identità (`app.jwt_user`,
`app.current_user_id`, `app.current_identita_id`, `app.ruolo_applicativo`, `app.soggetto_ruolo_id`,
`app.current_emittente_id`) e la lingua (`myapp.user_language`). Le porte, oggi, si aprono solo dagli aprenti a DB.

**I nove aprenti: chi li raggiunge.** Tutti INVOKER, tutti eseguibili dall'app. Chiamanti a DB letti dai corpi senza
commenti né stringhe, e da `pg_depend` per le `BEGIN ATOMIC`:

| Aprente (porte) | Dal BE, diretto | Dal DB, verbi che lo chiamano (e il BE chiama) |
| --- | --- | --- |
| `vendite.fn_cleanup_fatture_by_ids` (1-7) | no | `fn_annulla_lotto_da_draft`, `fn_riporta_lotto_a_draft`, `fn_elimina_fattura_da_lotto` (BE: `pipeline_repository.py`), quest'ultimo anche da `fn_escludi_documento_da_giro`; `fn_reset_fondi_fattura` (chiamata anche dall'aprente stesso) |
| `vendite.fn_cancella_fondo_fattura` (8) | sì: `vendite_repository.cancella_fondo_fattura`, endpoint di `views_fondi_fattura.py` | `pagamenti.fn_annulla_sistemazione` (BE: `pagamenti_repository.annulla_sistemazione`), `vendite.fn_reset_fondi_fattura` |
| `pagamenti.fn_posta_riga_tardiva` (9) | sì: `pagamenti_repository.posta_riga_tardiva` («Abbina e registra») | — |
| `script.fn_change_user_emittenti_scope` (10) | sì: `amm_software_repository.change_user_emittenti_scope`; test `core/tests/db/test_email_bozza_invio_db.py:257` | `anagrafiche.fn_provisiona_dati_di_sviluppo` (DEFINER, solo SVILUPPO) |
| `vendite.fn_genera_ddt_riconsegna` (11) | sì: `resi_repository.genera_ddt_riconsegna`, endpoint di `views_resi.py` | `dbops.fn_pgtap_crea_ddt_riconsegna` (fixture pgTAP) |
| `vendite.fn_ddt_riga_ritira_legami` (12-13) | no | `vendite.fn_documento_ritira_legami`, da sei `fn_annulla_*` (commessa, contratto, DDT, offerta, ordine, preventivo; BE: i loro repository); il trigger `trgfn_dlt_block_ordrig_ddtrig` |
| `dbops.fn_admin_merge_stradario` (14) | **no** | nessuno |
| `maintenance.proc_bump_toponomastica` (15) | **no** | nessuno |
| `documenti.fn_pubblica_template_documento_versione` (16) | sì: `documenti_repository.pubblica_versione` | — |

**Che cosa ne segue per le decisioni** (fatti datati, non motivi: le decisioni restano di Tid):

* **D-C**: la premessa «se la ricognizione BE non trova l'app fra i chiamanti» è vera per le porte 14 e 15 (nessun
  chiamante, né dal BE né dal DB) e per la 17 (nessuno la accende fuori da `db/`). La strada **b** non rompe niente
  nel BE.
* **D-A / D-B**: le porte del flusso hanno tutte un percorso BE vivo, diretto (8, 9, 10, 11, 16) o attraverso un
  verbo DB (1-7, 12-13). Chi passa una porta a «GUC + proprietario» deve rendere DEFINER il **verbo d'ingresso** di
  questa tabella, non l'aprente (§3-bis.2); per le porte 1-7 i verbi d'ingresso sono almeno quattro, per le 12-13
  sei, più il trigger. ⚠️ Superato da §4.3 per le 12-13: i sei `fn_annulla_*` sono già DEFINER, basta il trigger.
* **D-D**: invariata.

### 4.3 La strada D-A a, riletta dopo §4.2 — 2026-11-23

Tid propende per **a**. Le sue implicazioni, porta per porta, sul catalogo di dbdev (sicurezza dei verbi, azioni di
`config.azioni_processo`):

| Porte | Il verbo d'ingresso oggi | Che cosa serve con **a** | Azione che lo protegge |
| --- | --- | --- | --- |
| 12-13 | i sei `fn_annulla_*` sono **già DEFINER** (senza guard del permesso: lo tiene l'endpoint) | solo il trigger: il proprietario sul ramo **fuori bozza** (la porta del ritiro dell'annullo). Il ramo della bozza resta con la sola GUC sulla riga, perché lo apre anche `trgfn_dlt_block_ordrig_ddtrig` quando l'app cancella una riga di bolla in bozza | nessuna nuova; nessun `fn_annulla_*` si tocca, quindi il fermo del 2026-10-25 non entra |
| 16 | `fn_pubblica_template_documento_versione`, INVOKER, chiamata dal BE | il verbo DEFINER col guard; il trigger va riscritto: oggi il proprietario passa **senza** GUC (l'eccezione del seed), quindi dentro un verbo la GUC non servirebbe più. Il seed va distinto dal verbo | `documenti_template_manage` |
| 10 | `script.fn_change_user_emittenti_scope`, INVOKER, dal BE (amministrazione) | DEFINER col guard; tabella senza RLS | `fn_guard_super_admin`; il test BE `test_email_bozza_invio_db.py:257` va dato a un SUPER_ADMIN |
| 9 | `pagamenti.fn_posta_riga_tardiva`, INVOKER, dal BE | DEFINER col guard e il **perimetro** (RLS); la GUC è già sulla riga | da scegliere: `registra_distinta` o un'azione nuova |
| 11 | `vendite.fn_genera_ddt_riconsegna`, INVOKER, dal BE | DEFINER col guard e il perimetro | `conferma_reso` (da confermare) |
| 8 | `vendite.fn_cancella_fondo_fattura`, INVOKER, dal BE **e** da `fn_annulla_sistemazione`, `fn_reset_fondi_fattura` | si separa il verbo pubblico (guard) dalla primitiva (niente `EXECUTE` all'app), che chiamano solo verbi DEFINER: altrimenti chi annulla una sistemazione deve avere anche `governa_fondo_fattura` | `governa_fondo_fattura`; per `fn_annulla_sistemazione` da scegliere |
| 1-7 | `fn_annulla_lotto_da_draft`, `fn_riporta_lotto_a_draft`, `fn_elimina_fattura_da_lotto`, `fn_escludi_documento_da_giro`, tutti INVOKER | quattro verbi DEFINER col guard e il perimetro; `fn_cleanup_fatture_by_ids` e `fn_reset_fondi_fattura` diventano primitive senza `EXECUTE` all'app; la GUC diventa sulla riga | `reset_lotto_draft`, `reset_lotto_fattura_draft`; per l'esclusione dal giro da scegliere. L'utente tecnico della pipeline deve averle |

**Gli effetti negativi, in ordine di peso:**

1. **Il perimetro** (porte 1-9, 11): un verbo DEFINER non subisce la RLS. Ogni lettura e scrittura della catena del
   reset, del fondo, della registrazione tardiva e della riconsegna deve rimettere l'emittente. Una lettura dimenticata
   è un reset che tocca un'altra azienda, e nessun test lo vede se non lo costruisce. Il precedente c'è (i verbi
   DEFINER di vendite e di magazzino, il guard di ambito), ma la catena del reset è la più lunga del database.
   ⭐ **Come si risolve** (catalogo, 2026-11-23): il controllo si fa **una volta, all'ingresso**, sull'oggetto da cui
   la catena discende (il lotto, la fattura, il reso, la riga del contabile), non in ogni query: le righe figlie
   seguono il loro padre. Sotto resta la rete che c'è già: `script.trgfn_guard_emittente_scope` su
   `vendite.fatture`, `vendite.fatturazione_lotti` e `pagamenti.vendite_contabili_righe` è scritto per funzionare
   **anche dentro una DEFINER** (legge l'utente di sessione, non `current_user`). Il pgTAP costruisce due emittenti e
   prova che il verbo, chiamato su un oggetto dell'altro, si ferma.
2. **Il permesso controllato due volte**: chi oggi passa dall'endpoint senza l'azione riceverà `E_PERMESSO_NEGATO`
   dal DB. Il rischio vero sono l'utente tecnico dei lavori batch e i profili a cui l'azione manca: si controllano
   **prima** del giro. ⭐ **Come si risolve**: il verbo chiede la **stessa** azione che l'endpoint già controlla
   (le funzioni di risoluzione sono le stesse, §7.4 della guida dei permessi), quindi chi arriva al DB l'ha già e non
   nasce nessun rifiuto nuovo. Serve una tabella «endpoint → azione che controlla» (richiesta al BE, una riga per
   verbo d'ingresso) e, per l'utente tecnico della pipeline, l'azione nel suo profilo di seed.
3. **Le primitive chiuse all'app** rompono chi le chiama oggi come app: i chiamanti si censiscono tutti (`pg_depend`
   e i corpi), pgTAP compresi.
4. **I pgTAP**: circa settanta file nominano questi aprenti. Quelli che preparano i casi scrivendo diretti sulle
   tabelle protette, o chiamando le primitive come app, vanno portati al verbo o al seed.
5. **Il BE**: nessuna GUC da togliere (§4.2), nessuna firma che cambia; i nuovi `E_PERMESSO_NEGATO` e i test.

✅ **D-A a, decisa da Tid il 2026-11-23.** **L'ordine dei giri:** 12-13 (solo il trigger), 16, 10, 9, 11, 8, 1-7. Dal più piccolo al più
delicato; il perimetro si prova a partire dal giro della 9. Con **a**, D-B decade: la GUC sulla riga entra nello
stesso giro di ogni porta.

### 4.4 La richiesta 3d al team BE/FE — scritta il 2026-11-24

Precompilata dal DB sul ramo `origin/dev/backend-tid` (`f1b8f9df7a`, sola lettura): i verbi e i loro chiamanti BE
da §4.2, il meccanismo del permesso dagli attributi delle view. Una richiesta sola per tutti i giri delle porte del
flusso (16, 10, 9, 11, 8, 1-7); il giro 12-13 non la aspetta.

> **Il permesso dei verbi che diventano SECURITY DEFINER.** Nei prossimi giri il DB porta dieci funzioni da
> `SECURITY INVOKER` a `SECURITY DEFINER`, così le porte dei loro trigger smettono di aprirsi con una GUC che l'app
> può accendere da sé. Un verbo DEFINER gira come proprietario: deve controllare in prima riga il permesso di chi lo
> chiama (`E_PERMESSO_NEGATO`) e rimettere il perimetro dell'emittente, che la RLS non applica più. Il verbo
> chiederà **lo stesso permesso che l'endpoint controlla già**, con le stesse funzioni di risoluzione, perché chi
> arriva al DB dall'endpoint non riceva un rifiuto nuovo. Per questo ci serve sapere con precisione che cosa
> controlla oggi ogni endpoint. Il DB non cambia niente finché non arriva la risposta.
>
> **Parte A — la tabella dei verbi.** Per ogni riga: conferma o correggi ciò che abbiamo letto, e completa le
> colonne vuote. Se un verbo è raggiunto da più strade (endpoint, servizio, task della pipeline, comando,
> job), una riga per strada.
>
> | # | Verbo DB (porta) | Chiamante BE letto dal DB | View | Permesso letto dal DB | Da completare |
> | --- | --- | --- | --- | --- | --- |
> | 1 | `documenti.fn_pubblica_template_documento_versione` (16) | `documenti_repository.py:1007` | `ApiTemplateVersionePubblica` | `post_permission = "documenti_template_manage"`, area `documenti` | il livello sull'area, se conta |
> | 2 | `script.fn_change_user_emittenti_scope` (10) | `amm_software_repository.change_user_emittenti_scope` | ? | ? (il DB userà `fn_guard_super_admin`) | la view, e se chiede SUPER_ADMIN o altro |
> | 3 | `pagamenti.fn_posta_riga_tardiva` (9) | `pagamenti_repository.py:537` | `ApiRigaRegistra`? | ? | view e permesso |
> | 4 | `vendite.fn_genera_ddt_riconsegna` (11) | `resi_repository.py:966` | `ApiResoGeneraDdtRiconsegna` | area `vendite`, `model_permission = ("vendite", "reso")` | che cosa vuol dire `model_permission` in termini di azione o livello DB |
> | 5 | `vendite.fn_cancella_fondo_fattura` (8) | `vendite_repository.py:3619`, endpoint di `views_fondi_fattura.py` | la view del DELETE | `delete_permission = "governa_fondo_fattura"` | — |
> | 6 | `pagamenti.fn_annulla_sistemazione` (8, chiama la 5) | `pagamenti_repository.py:2386` | `ApiSistemazioneAnnulla` | area pagamenti, ? | il permesso |
> | 7 | `vendite.fn_annulla_lotto_da_draft` (1-7) | `pipeline_repository.py:3149`; anche il task `reset_lotto_draft` della pipeline (`pipeline_repository.py:461`) | `ApiResetLottoDraft` | `post_passaggio` sul lotto, stato del modello `annullo` | chi esegue il task e con quale permesso |
> | 8 | `vendite.fn_riporta_lotto_a_draft` (1-7) | `pipeline_repository.py:3178` | `ApiRiportaLottoADraft` | `post_passaggio` sul lotto, stato del modello `iniziale` | — |
> | 9 | `vendite.fn_elimina_fattura_da_lotto` (1-7) | `pipeline_repository.py:3238` | `ApiResetLottoFatturaDraft` | `post_permission = "reset_lotto_fattura_draft"` | — |
> | 10 | `vendite.fn_escludi_documento_da_giro` (1-7, chiama la 9) | `pipeline_repository.py:3267` | `ApiEscludiDocumentiDaGiro` | `post_permission = "reset_lotto_fattura_draft"` | — |
>
> Per le righe `post_passaggio`: il commento della view dice che l'azione viene dalla riga del passaggio «la stessa
> che legge il verbo». Indicaci la funzione DB (o la query) con cui il BE risolve il passaggio, così il verbo usa
> quella e non una copia.
>
> **Parte B — l'utente tecnico della pipeline.** I processi automatici girano come `zeroerp_app` con un utente
> tecnico per azienda. Quali di questi dieci verbi raggiunge, da quale task o comando, e con quali azioni nel suo
> profilo? Dove nasce quel profilo (seed del DB, comando BE, a mano)? Se un'azione della Parte A gli manca, il verbo
> DEFINER lo fermerebbe: è il rischio principale dei giri.
>
> **Parte C — chi chiama queste funzioni senza passare dall'endpoint.** I test e le fixture (Django e smoke) che
> chiamano uno dei dieci verbi con un utente che non ha il permesso della Parte A: dopo i giri riceveranno
> `E_PERMESSO_NEGATO`. Ne conosciamo uno: `core/tests/db/test_email_bozza_invio_db.py:257` chiama
> `fn_change_user_emittenti_scope` e dovrà farlo con un SUPER_ADMIN. E conferma che il backend non chiama
> direttamente nessuna di queste quattro funzioni, che diventeranno interne (senza `EXECUTE` all'app):
> `vendite.fn_cleanup_fatture_by_ids`, `vendite.fn_reset_fondi_fattura`, `vendite.fn_ddt_riga_ritira_legami`,
> `vendite.fn_check_fondo_cancellabile`. Sul ramo il DB non ne ha trovato nessuna chiamata.
>
> **Come rispondere.** Un elenco chiuso: la tabella della Parte A completata, una riga per strada; per la Parte B
> l'elenco task → verbo → azioni; per la Parte C l'elenco `file:riga`, oppure «nessuno» con il modo in cui si è
> cercato.
>
> **Chi cambia per primo.** Il DB, porta per porta, nell'ordine 16, 10, 9, 11, 8, 1-7. Ogni giro porta la sua
> richiesta al BE: i test della Parte C da adeguare, e le risposte `E_PERMESSO_NEGATO` nuove dove la Parte A
> dicesse che oggi l'endpoint non controlla niente. Fino ad allora il backend non cambia niente: nessuna firma
> cambia, nessuna GUC da togliere.

### 4.5 La risposta del BE alla richiesta 3d — 2026-11-24

Dal team BE, branch `dev/backend-tid` `601fd0b29`, sola lettura, nessun file di `backend/` modificato. **Come si è
cercato**: i quattordici nomi di funzione (i dieci verbi e le quattro primitive) e i metodi di repository e service
che li chiamano, su `backend/apps`, `backend/scripts` e gli smoke, senza `error_policies_generated.py`; da ogni
metodo si è risaliti alla view, al comando o al task; per ogni view si è letto il ramo della catena dei permessi che
la decide (`apps/core/api/permissions.py`, `ZeroERPPermission.valuta` e `IsAdminZeroERP.valuta`). Nessun tool
dell'assistente AI è gemello di una di queste view.

**Le tre regole del gate BE che il verbo deve rifare, o nasce un rifiuto nuovo** (`ZeroERPPermission.valuta`):

1. **SUPER_ADMIN passa sempre** (`script.fn_is_super_admin(user_id)`), prima di ogni azione e di ogni livello;
2. ⚠️ **passa sempre anche il superuser di Django** (`auth_user.is_superuser`), anche senza il binding SUPER_ADMIN.
   Il DB non lo vede come tale: un superuser senza binding passa l'endpoint e verrebbe fermato dal verbo. Da
   decidere nel primo giro (16): o il verbo lo ammette, o il BE toglie il bypass (oggi lo usa anche
   `apri_contesto_operatore` dei test e2e, che di default prende un `is_superuser`);
3. con un `<metodo>_permission` (o un passaggio che dà un'azione) **decide solo l'azione**
   (`script.fn_check_azione_processo(user_id, codename)`): il livello d'area non si guarda. Senza azione decide il
   livello: `POST` chiede `add`, `DELETE` `delete`, e li dà solo `TUTTO`.

**Parte A — la tabella dei verbi, corretta e completata.** Una strada per riga; la funzione di risoluzione è quella
che il verbo deve usare.

| # | Verbo DB (porta) | Strada BE | View e metodo | Che cosa controlla oggi | Funzione DB della decisione |
| --- | --- | --- | --- | --- | --- |
| 1 | `documenti.fn_pubblica_template_documento_versione` (16) | `TemplateVersioniAdminService.pubblica_versione` → `documenti_repository.py:996` | `ApiTemplateVersionePubblica` (`documenti/api/views.py:628`), POST | azione `documenti_template_manage`; il livello sull'area `documenti` **non** conta (regola 3) | `fn_check_azione_processo` |
| 2 | `script.fn_change_user_emittenti_scope` (10) | `AmmSoftwareService.put_emittenti_scope` → `amm_software_repository.py:871` | `EmittentiScopeView` (`amm_software/api/views.py:266`), PUT; base `AdminAPIView` | SUPER_ADMIN, oppure superuser Django (regola 2); nient'altro | `fn_is_super_admin`, quindi `fn_guard_super_admin` è coerente |
| 3 | `pagamenti.fn_posta_riga_tardiva` (9) | `pagamenti_service.registra_riga_tardiva` → `pagamenti_repository.py:537` | `ApiRigaRegistra` (`pagamenti/api/views.py:719`), POST | azione `registra_distinta` | `fn_check_azione_processo` |
| 4 | `vendite.fn_genera_ddt_riconsegna` (11) | `resi_service.genera_ddt_riconsegna` → `resi_repository.py:966` | `ApiResoGeneraDdtRiconsegna` (`vendite/api/views_resi.py:610`), POST | **nessuna azione**: livello `TUTTO` sull'oggetto `vendite.reso` (da `model_permission`), con ricaduta sull'area `vendite` se l'oggetto non ha un livello suo | `fn_resolve_livello_oggetto(user_id, 'vendite', 'reso', 'vendite')` |
| 5 | `vendite.fn_cancella_fondo_fattura` (8) | `vendite_service.fn_cancella_fondo_fattura` → `vendite_repository.py:3615` | `ApiFondoFatturaDelete` (`vendite/api/views_fondi_fattura.py:196`), DELETE | azione `governa_fondo_fattura` | `fn_check_azione_processo` |
| 6 | `pagamenti.fn_annulla_sistemazione` (8, chiama la 5) | `sistemazioni_service.annulla_sistemazione` → `pagamenti_repository.py:2360` | `ApiSistemazioneAnnulla` (`pagamenti/api/views.py:1280`), POST | **nessuna azione**: livello `TUTTO` sull'area `pagamenti` | `fn_resolve_livello_area(user_id, 'pagamenti')` |
| 7 | `vendite.fn_annulla_lotto_da_draft` (1-7) | `pipeline_service.fn_annulla_lotto_da_draft` → `LottoResetService` → `pipeline_repository.py:3142` | `ApiResetLottoDraft` (`vendite/api/views.py:600`), POST | il passaggio verso lo stato d'annullo; oggi la riga DRAFT → annullo non ha azione (Q-F2), quindi decide il livello `TUTTO` sull'area `vendite` | vedi sotto, «Il passaggio» |
| 7b | idem | task `reset_lotto_draft` della pipeline (`pipeline_step_executor.py:1197`, mappa `pipeline_repository.py:454`) | nessuna | **non raggiunto**: vedi Parte B | — |
| 8 | `vendite.fn_riporta_lotto_a_draft` (1-7) | `pipeline_service.fn_riporta_lotto_a_draft` → `pipeline_repository.py:3171`; anche lo smoke `smoke-ritorno-lotto-a-draft.py:169` | `ApiRiportaLottoADraft` (`vendite/api/views.py:658`), POST | il passaggio verso lo stato iniziale: da EMESSA l'azione della riga (oggi `numera_fatture_lotti`, dal commento della view); sul lotto già in bozza la riga non c'è e decide il livello `TUTTO` sull'area `vendite` | vedi sotto |
| 9 | `vendite.fn_elimina_fattura_da_lotto` (1-7) | `pipeline_service.fn_elimina_fattura_da_lotto` → `pipeline_repository.py:3231` | `ApiResetLottoFatturaDraft` (`vendite/api/views.py:718`), POST | azione `reset_lotto_fattura_draft` | `fn_check_azione_processo` |
| 10 | `vendite.fn_escludi_documento_da_giro` (1-7, chiama la 9) | `pipeline_service.fn_escludi_documenti_da_giro` (un savepoint per documento, `run_fan_out`) → `fn_escludi_documento_da_giro` → `pipeline_repository.py:3260` | `ApiEscludiDocumentiDaGiro` (`vendite/api/views.py:776`), POST | azione `reset_lotto_fattura_draft` | `fn_check_azione_processo` |

**Il passaggio** (righe 7 e 8, `PassaggioDocumento.azione`, `apps/core/api/permissions.py`). Il BE non ha una query
sua: lo stato d'arrivo è `script.fn_stato_abortito_id('vendite.fatturazione_lotti')` (annullo) o
`script.fn_doc_stato_iniziale_id(...)` (iniziale), tradotto in codice con `script.fn_doc_stato_codice`; l'azione è
`azione_processo_codename` di `script.fn_doc_azione_passaggio('vendite.fatturazione_lotti'::regclass, lotto_id,
<codice>)`. Se è NULL, o la riga non c'è, decide il livello sull'area `vendite` (regola 3, al contrario). Il verbo
usa le stesse funzioni.

**Due correzioni a §4.3** (fatti del codice, 2026-11-24):

* porte 1-7: `reset_lotto_draft` non è un'azione viva. È spenta nel seed (`azioni_processo.csv`, id 6,
  `attivo = f`), e le due view l'hanno sostituita col passaggio. Le azioni dei quattro verbi sono quelle della
  tabella;
* porta 11: l'endpoint non chiede `conferma_reso`, chiede il livello `TUTTO` sull'oggetto `vendite.reso`. Con
  `conferma_reso` nel verbo, chi oggi genera la riconsegna senza quell'azione riceverebbe un rifiuto nuovo.
* Porta 8, il secondo chiamante: `fn_annulla_sistemazione` è protetto dal livello `TUTTO` sull'area `pagamenti`.
  Non serve un'azione nuova.

**Parte B — l'utente tecnico della pipeline.** I processi headless girano dentro il giro per azienda
(`apps/core/services/giro_per_azienda.py`), con un utente tecnico per (processo × azienda). Sono:
`run_fatturazione_batch`, `draina_coda_lavori` con gli handler `fatturazione_giro`, `fatturazione_numera`,
`chiusura_scadenze`, `notifica_digest_muto` ed `esegui_processo`, poi `draina_coda_stampa` e `send_pending_emails`.

* **Nessuno raggiunge uno dei dieci verbi.** L'unico aggancio è il task `reset_lotto_draft`, nel rollback dello
  step EMESSA della pipeline 3 MASSIVO (seed `fatturazione_pipeline.csv`). Il runner esegue i rollback solo da
  `_should_execute_auto_step_rollback` (`pipeline_runner.py:496`), che **esclude** proprio una lista di rollback
  con `reset_lotto_draft` (righe 521-524, «evita rollback distruttivi in auto-run»). La facade
  `pipeline_service.fn_execute_pipeline_step` (`:704`), l'altra strada verso un rollback, non la chiama nessuno
  fuori dai test.
  ⚠️ Per il DB: il task è registrato (`pipeline_task_registry`, `ALLOWED_TASK_FUNCTIONS`) ma nessun percorso lo
  esegue. Se un giorno lo eseguisse, l'utente tecnico non avrebbe né l'azione né il livello (punto sotto), e il verbo
  DEFINER lo fermerebbe. Se dichiararlo o ritirarlo, lo decide Tid col giro 1-7.
* **Il profilo**: nasce a DB, in `script.fn_crea_utente_tecnico`. Il BE la chiama da
  `processi_service.py:466`, dietro l'amministrazione (SUPER_ADMIN). Il profilo è facoltativo, solo `AD_HOC`, e
  «di norma non si passa»: di default l'utente tecnico **non ha azioni né livelli**. Nessun comando BE lo assegna.

**Parte C — chi chiama i verbi senza passare dall'endpoint.** Chiamate vere (non mock), a DB reale:

| `file:riga` | Verbo | Con quale contesto | Dopo il giro |
| --- | --- | --- | --- |
| `core/tests/db/test_email_bozza_invio_db.py:257` | `fn_change_user_emittenti_scope` | **nessuno**: il contesto si apre dopo, a `:263` | va dato un SUPER_ADMIN (`fn_pgtap_crea_operatore_umano(…, true)` o `apri_contesto_operatore(cur, super_admin=True)`) |
| `vendite/tests/services/test_fondi_fattura_service.py:415` (`CancellaFondoFatturaBindingTests`) | `fn_cancella_fondo_fattura` | **nessuno**; si aspetta `E_FONDO_NON_TROVATO` su un id inesistente | col guard in prima riga risponde il permesso: serve un contesto con `governa_fondo_fattura` o SUPER_ADMIN |
| `documenti/tests/db/test_template_standard_db.py:218, 310, 494, 548, 554` | `fn_pubblica_template_documento_versione` | l'operatore di `dbops.fn_pgtap_crea_emittente_operatore()`, cioè un utente tecnico **senza profilo** | senza `documenti_template_manage`, rifiuto: da confermare dal DB con `fn_check_azione_processo` su quell'utente |
| `documenti/tests/db/test_versione_contesto_db.py:164, 170, 240, 248` | idem | idem | idem |
| `core/tests/db/test_date_validita_guard_comune_db.py:318` | idem | idem | idem (il test si aspetta il rifiuto delle date: arriverebbe prima il permesso) |
| `documenti/tests/db/_stampa.py:78` (`pubblica_per_stampare`), usato da `test_ricerca_liste_db.py:179` e `test_scritture_dinamiche_db.py:228` | idem | idem | idem |
| `pagamenti/tests/db/test_validata_e_tardiva_db.py:313, 353` | `fn_posta_riga_tardiva` | idem | senza `registra_distinta`, rifiuto |
| `scripts/tests/smoke-ritorno-lotto-a-draft.py:169` | `fn_riporta_lotto_a_draft` | l'utente degli smoke, SUPER_ADMIN (lo verifica `_smoke_contesto.py`) | passa, se il verbo ammette SUPER_ADMIN come l'endpoint (regola 1) |
| `scripts/tests/smoke-test-vendite.sh:177`, `smoke-test-resi-vendita.sh:388, 404` | `fn_annulla_lotto_da_draft`, `fn_genera_ddt_riconsegna` | via HTTP, l'utente del login degli smoke | passano dall'endpoint: stessa condizione |

I test API e di service che usano i mock (`test_*_api.py`, `test_resi_service`, `test_sistemazioni_service`,
`test_escludi_documento_da_giro`, `test_pipeline_*`) non arrivano al DB: non cambiano.

**Le quattro primitive** (`fn_cleanup_fatture_by_ids`, `fn_reset_fondi_fattura`, `fn_ddt_riga_ritira_legami`,
`fn_check_fondo_cancellabile`): **confermato, nessuna chiamata dal BE**, né nel codice né nei test né negli smoke.
Compaiono solo nei commenti (`pipeline_repository.py:470`, `pipeline_step_executor.py:222`,
`vendite_repository.py:3590`).

**Che cosa ne segue per i giri** (fatti datati, non motivi):

* il verbo chiede ciò che la tabella dice, e ammette SUPER_ADMIN. Sul superuser Django decide Tid (regola 2);
* i test della Parte C si adeguano nel giro della loro porta, come richiesta al BE di quel giro. I sei file di
  `documenti` e quello di `pagamenti` cambiano tutti nello stesso modo: il builder dell'operatore deve dare l'azione.
  Se il DB offre un builder con un profilo (o un parametro di `fn_pgtap_crea_emittente_operatore`), il BE lo usa.
  Altrimenti ogni test apre un SUPER_ADMIN, e il caso «operatore senza l'azione» lo prova il pgTAP;
* nessuna firma BE cambia, nessuna GUC da togliere.

### 4.6 Le due decisioni nate dalla risposta 3d — 2026-11-24

**D-I, il task `reset_lotto_draft`: ✅ decisa da Tid il 2026-11-24, si ritira.** Riverificato prima della
decisione (branch `dev/backend-tid` `601fd0b29` e doc generata del DB):

* nel BE l'unico esecutore di un rollback è `_should_execute_auto_step_rollback` (`pipeline_runner.py:496`). Gira
  solo con `meta.auto_step_rollback` acceso, su un rerun d'errore del MASSIVO, e rifiuta una lista che contiene
  `reset_lotto_draft`. La facade `fn_execute_pipeline_step` non ha chiamanti fuori dai test, nessuna view la espone,
  e i giri headless non la usano;
* a DB nessuna funzione esegue i task: `fn_check_pipeline_task_registered` e `fn_get_pipeline_task_implementation`
  li leggono soltanto, per il runner del BE. L'annullo del lotto ha la sua strada, il verbo
  `fn_annulla_lotto_da_draft` dall'endpoint;
* tolto il task, il rollback della pipeline 3 resta vuoto, e il runner su una lista vuota fa già ciò che fa oggi:
  non esegue niente.

Che cosa si ritira, e chi cambia per primo. **Il DB per primo**: il BE che toglie l'handler prima del seed lascerebbe
un task registrato senza implementazione.

| Lato | Che cosa |
| --- | --- |
| DB (CSV di `80_data`, §11.2) | la voce di rollback in `vendite/fatturazione_pipeline.csv` (pipeline 3); le righe di `dbops/pipeline_task_registry.csv`, `pipeline_task_registry_impl.csv` e `vendite/fatturazione_pipeline_task_policy.csv`; l'azione spenta `reset_lotto_draft` di `config/azioni_processo.csv`, se nessun binding la nomina più (da verificare a DB) |
| BE, dopo il DB | `"reset_lotto_draft"` in `ALLOWED_TASK_FUNCTIONS` (`pipeline_repository.py:454`); l'handler `_handle_reset_lotto_draft_task` e la sua voce (`pipeline_step_executor.py:265, 1197`); l'esclusione per nome in `_should_execute_auto_step_rollback` (`pipeline_runner.py:521-524`), che diventa codice morto; i test che li nominano (`test_pipeline_step_executor.py:132` e i casi del rollback) |

Effetto sui giri: la riga 7b della tabella 3d sparisce, e il giro 1-7 ha una strada in meno.

**D-J, il superuser Django: ✅ decisa da Tid il 2026-11-24, strada a.** Il lavoro BE parte subito su
`dev/backend-tid`, prima del giro 16 (§4.7). I fatti (2026-11-24): nessun percorso di ZeroErp crea un superuser:
`anagrafiche.fn_crea_auth_user` scrive `is_superuser = false`, l'admin Django non c'è (`settings.py:144`). Ne nasce
uno solo con `manage.py createsuperuser`. Il BE però lo onora in una decina di punti, e non solo nel gate dei
permessi (`permissions.py:298, 310, 465, 601`). Lo onora anche nel perimetro (`endpoint_helpers.get_scope_user_id`:
`None`, cioè «nessun limite»), nello scope dei billing account (`billing_account_service.py:147`), nei gate dei prezzi
(`_pricing_gate_helpers.py`, `approvazioni_prezzo_service.py`) e in `ui/api/views_admin.py:130`.

* **a** `is_superuser` non concede più niente: il BE toglie tutti i bypass, e l'unico privilegio d'amministrazione
  resta SUPER_ADMIN, che il DB vede · **b** il verbo DEFINER lo ammette, leggendo `auth_user.is_superuser` ·
  **c** solo il gate dei permessi lo perde, il resto resta.
* ⭐ **a**. Il resolver dichiara già SUPER_ADMIN «single source of truth per il privilegio admin». Il superuser è una
  seconda sede, che nessun oggetto del DB conosce: la RLS non la vede, i verbi nemmeno. **b** la porterebbe dentro
  ogni guard, e il bypass del perimetro (`get_scope_user_id`) resterebbe una lettura senza muri. **c** lascia le
  stesse due sedi negli altri punti.
* Costo di **a**: un lavoro BE a sé (i punti elencati, i loro test, `apri_contesto_operatore` dei test e2e, che di
  default prende un `is_superuser`), da fare **prima** del giro 16. Chi oggi ha un superuser in sviluppo gli dà il
  binding SUPER_ADMIN.

### 4.7 D-J nel BE: i bypass di `is_superuser` tolti — ✅ fatto, 2026-11-24

**Fatto, nel codice di produzione** (`dev/backend-tid`, non committato):

| File | Che cosa |
| --- | --- |
| `core/api/permissions.py` | tolti i quattro bypass (`IsAdminZeroERP.valuta` e `has_permission`, `ZeroERPPermission.valuta` e `has_permission`); resta SUPER_ADMIN |
| `core/api/endpoint_helpers.py` | `get_scope_user_id` dà l'id dell'utente autenticato, mai più `None` per il superuser |
| `ui/api/views_admin.py` | `_require_any_action` senza il bypass |
| `anagrafiche/api/views_billing_account.py`, `services/billing_account_service.py` | tolto il parametro `is_superuser` |
| `vendite/services/_pricing_gate_helpers.py` (tre punti), `approvazioni_prezzo_service.py` (due) | tolti i bypass: SUPER_ADMIN passa già da `fn_check_azione_processo`, che gli dà `true` |
| una ventina di file | i commenti che dicevano «`None` = superuser» |

**Il presidio rosso** (suite completa, 2026-11-24). Base prima del giro: 6743 test, OK. Dopo: **608 failure e
59 errori in 85 moduli di test**. La causa è una sola: **77 file** di test API autenticano con
`JWTAuthentication.authenticate` patchato a `(Mock(), None)`. Un `Mock()` nudo ha `is_superuser` vero, quindi quei
test passavano per il bypass **senza dirlo**, che è il difetto già nominato dal BB `operatore_di_prova`. Senza il
bypass la catena interroga il DB con l'id di un mock, e risponde 500 o 403. Gli altri rossi (circa 25 punti) sono i
test che dichiarano `is_superuser=True` per saltare un permesso, e i tre che provavano proprio il bypass
(`test_admin_permission`, `test_permissions`, `test_billing_account_service`).

> ⚠️ **Superato: deciso da Tid (ok al BB) e fatto lo stesso giorno**, vedi sotto «I test, adeguati il 2026-11-24».

**Da decidere prima di adeguare i test** (regola del 2, a Tid): un BB di test, `super_admin_di_prova()`, in
`core/tests/_helpers/`. È l'operatore autenticato più il patch di `PermissionResolver.is_super_admin` a `True`, da
usare dove un test vuole davvero passare la catena per guardare la view. I 77 file passano dal `Mock()` nudo a
`operatore_di_prova()` + `super_admin_di_prova()` (oppure ai permessi che il test vuole provare), e i tre test del
bypass si riscrivono come «il superuser senza SUPER_ADMIN è negato».

**Resta fuori, dichiarato**: `core/tests/db_e2e.apri_contesto_operatore` sceglie di default un utente con
`is_superuser` per aprire la GUC (76 chiamanti). Il DB non guarda quel flag, quindi non concede niente, ma il
criterio di scelta non ha più senso. Lo si cambia nello stesso giro dei test. ✅ Fatto, vedi sotto.

**I test, adeguati il 2026-11-24** (ok Tid al BB):

* il BB `core/tests/_helpers/super_admin_di_prova.py`, registrato nel catalogo. In `JwtMockedApiTest` si dichiara
  con l'attributo di classe `come_super_admin = True` (default `False`), messo in **129 classi**;
* `ZeroERPPermission.valuta` legge il ruolo applicativo **dopo** il bypass SUPER_ADMIN: serve solo al messaggio
  del diniego;
* i test che provavano il bypass (`test_admin_permission`, `test_permissions`, `test_billing_account_service`,
  `test_tool_registry`, `test_approvazioni_prezzo_service`, due di `test_preventivi_service`, i perimetri di
  `test_actor_user_id_api`, `test_lotti_list_api` e `test_lotto_fatture_list_api`) ora provano il contrario: il
  superuser senza SUPER_ADMIN è trattato come chiunque. ⚠️ Due di questi (`test_superuser_bypass`,
  `test_superuser_allowed`) erano verdi **per i dati**: interrogavano il DB vero con l'utente 1, che su dbdev è
  SUPER_ADMIN. Ora patchano `is_super_admin` a `False`;
* tre attese `auth_user_id=None` in `test_pipeline_api` passano all'id dell'operatore;
* `apri_contesto_operatore` di default prende il primo utente con la veste OPERATORE attiva
  (`script.fn_has_identita_attiva`).

**Esito**: suite completa **6743 test, OK, 339 saltati** (identica alla base); ruff e il cancello mypy verdi.

**Dalla verifica critica** (`/verifica`, 2026-11-24): corretti il catalogo BB (sette voci ancora alla regola del
superuser), un commento di `gestione_service.py`, il commento di `frontend/src/vendite/api/approvazioniPrezzo.js`.
Provato che i test rovesciati sono un presidio: con il bypass rimesso in `ZeroERPPermission.valuta`,
`IsAdminZeroERP.valuta` e `get_scope_user_id` ne diventano rossi sei.

**D-K, il primo amministratore di un'installazione nuova: ✅ decisa da Tid il 2026-11-24.**

*Il problema.* Il playbook e `configurazione-django.md` dicevano che l'utente di `createsuperuser` è il primo con cui
si entra dal frontend. Non era vero nemmeno prima di D-J: il login chiede una veste attiva (`MultiVesteTokenSerializer`,
403 `E_VESTE_NON_ATTIVA`), e `createsuperuser` crea solo la credenziale. Dopo D-J il flag non concede neanche più
niente. Un'installazione nuova non ha quindi una strada scritta per arrivare al primo SUPER_ADMIN.
`provision_utenti_sviluppo` vale solo fuori da PRODUZIONE.

*Che cosa c'è già* (letto dalla doc generata del DB, 2026-11-24, senza una chiamata vera):

* `anagrafiche.fn_crea_operatore_v2(…, p_is_super_admin)` crea soggetto, credenziale, risorsa umana e veste, e
  attraverso `fn_crea_risorsa_umana_v2` il binding SUPER_ADMIN (profilo da `config.fn_profilo_super_admin_id`);
* **nessuno dei due verbi guarda chi li chiama**, e nessun trigger di `config.profili_accesso_bindings` pretende che
  un SUPER_ADMIN lo conceda: il problema dell'uovo e della gallina non c'è. L'audit
  (`trgfn_audit_data_user_generic`) senza `app.jwt_user` ripiega su `CURRENT_USER`;
* la veste OPERATORE nasce **spenta, sempre** (R-2 di brief-db-blocco-login-per-credenziale): la accende
  l'attivazione dell'invito, cioè una mail. Sul primo impianto serve `anagrafiche.fn_accendi_veste`;
* «ne esiste già uno» lo dice `script.fn_check_almeno_un_super_admin_attivo`.

*La scelta.* La condizione che apre il bootstrap è «**non esiste ancora un SUPER_ADMIN attivo**», non «non c'è un
utente». La seconda resterebbe vera per sempre, per chiunque non sia autenticato; la prima si chiude da sola alla
nascita del primo. ⚠️ Non c'entra con il `None` dei filtri di perimetro (la verifica critica dello stesso giorno):
quello è un filtro di lettura, e chiudere l'uno non chiude l'altro.

**R-DB-K1 — al team DB: il verbo di primo impianto.** Chi cambia per primo: il DB. Il BE non ha niente da adeguare
finché il verbo non c'è.

* `anagrafiche.fn_crea_primo_amministratore(...)` (nome e firma li decide il DB), `SECURITY DEFINER`, così non
  dipende dalla RLS né dalle GUC della connessione che lo chiama;
* **in prima riga** rifiuta se `fn_check_almeno_un_super_admin_attivo()` è vero, con un codice nuovo (per esempio
  `E_PRIMO_AMMINISTRATORE_GIA_PRESENTE`, NON_PERMESSO), e serializza la verifica (lock) così due chiamate
  concorrenti non ne creano due;
* poi chiama `fn_crea_operatore_v2(…, p_is_super_admin => true)` e accende la veste con `fn_accendi_veste`, nella
  stessa transazione: o l'amministratore entra, o non nasce niente;
* riceve l'hash Django della password (il DB non lo calcola, come in `provision_utenti_sviluppo`);
* il pgTAP: su un DB senza SUPER_ADMIN crea il primo, veste accesa e `fn_is_super_admin` vero; la seconda chiamata
  è rifiutata; un SUPER_ADMIN **spento** o scaduto non conta come presente (la condizione è quella di
  `fn_identita_super_admin_senza_scadenza`, da confermare dal DB);
* da verificare dal DB, perché qui non è stato provato: quali righe di seed il verbo pretende su un'installazione
  vuota (qualifica, unità organizzativa, il soggetto PR), e se servono a `p_qualifica_id` e
  `p_unita_organizzativa_id` dei default di primo impianto;
* il codice d'errore nuovo entra nel catalogo con la sua policy generata e un ripiego senza `%s`.

**R-DB-K2 — al team DB: una porta in più per il piano dei giri.** `fn_crea_operatore_v2` e `fn_crea_risorsa_umana_v2`
sono `SECURITY INVOKER` e non guardano il chiamante. Oggi l'unico muro fra un utente qualunque e un binding
SUPER_ADMIN nuovo è l'endpoint del BE (`AdminAPIView`), ed è la classe di questo brief. Va valutata come porta
(guard SUPER_ADMIN nel verbo con `fn_guard_super_admin`, salvo la strada del primo impianto, che passa da R-DB-K1),
con la sua riga nella tabella delle porte e il giro che la chiude.

**Al team BE, dopo R-DB-K1** (passo 3j): un management command `crea_primo_amministratore`. Chiede i dati e la
password, calcola l'hash, chiama il verbo e traduce il rifiuto in un messaggio chiaro. Il playbook (§11) e
`configurazione-django.md` sostituiscono `createsuperuser` con il comando e tolgono la nota ⚠️ messa il 2026-11-24.
Il test: il comando chiama il verbo con l'hash, e il rifiuto «già presente» esce come messaggio, non come traceback.

## 5. La seconda famiglia: le viste aggiornabili — 2026-11-23

**Il varco.** Il loop dei grant (`90_end/ci_apply/20260205-41`) dà all'app `INSERT`, `UPDATE` e `DELETE` «on all
tables» di ogni schema tranne `maintenance`, e PostgreSQL ci conta le viste. Una vista **aggiornabile** e **senza**
`security_invoker` controlla i permessi sulla tabella sotto come il suo proprietario: con il DML sulla vista, l'app
scrive la tabella anche quando è nella lista `v_tabelle_sola_lettura_app`. È la stessa classe delle porte di §2,
una scrittura diretta che aggira il verbo, per un'altra via: non un trigger, un permesso.

**Il censimento** (catalogo di dbdev, 2026-11-23, viste `relkind = 'v'` con `pg_relation_is_updatable`): quindici
viste aggiornabili fuori da `public`, nessun trigger `INSTEAD OF`, nessuna regola. Sei sono senza `security_invoker`,
su otto tabelle; su tutte l'app ha già il DML, quindi oggi non si apre niente in più:

| Vista | Tabelle sotto |
| --- | --- |
| `catalogo.vw_causali_onere_assegnabili` | `catalogo.articoli`, `config.causali_onere` |
| `dbops.vw_emittenti_regime_non_confermato` | `anagrafiche.emittenti_fiscali` |
| `dbops.vw_liste_multi_emittente_non_certificate` | `ui.lista_colonna`, `ui.lista_definizione` |
| `dbops.vw_processi_dominio_su_pgagent` | `dbops.processi` |
| `script.vw_audit_sources` | `dbops.audit_sources` |
| `script.vw_stati_estesi` | `config.stati` |

Il modello però lo ammette, e nessun presidio lo guarda: basta una vista semplice su una tabella di `magazzino`, tutta
in sola lettura per l'app dal 2026-11-23. L'analisi, con le viste di `anagrafiche`, sta in
`brief-db-revisione-anagrafiche` §19.

**D-V — decisa da Tid il 2026-11-23.** L'app riceve solo `SELECT` sulle viste, in tutto il database:

* dichiarato nel loop dei grant come eccezione per `relkind = 'v'`, nelle tre sedi di `linee-guida-sql.md` §11.8
  (il changeSet `90_end` che revoca subito, il loop, la fase `post` del provisioning);
* un pgTAP di postura **a criterio**: nessuna vista dà all'app più di `SELECT`, e un caso costruito (una vista
  aggiornabile senza flag su una tabella in sola lettura per l'app) risponde `42501`;
* prima, la Parte B della richiesta di §4.1: una scrittura trovata vuole prima il suo verbo.

Scartata l'alternativa più stretta (lasciare il DML, e un presidio che rifiuta una vista aggiornabile senza
`security_invoker`): lascia all'app un privilegio che nessun oggetto del DB usa.

### 5.1 La risposta del BE alla Parte B — 2026-11-23

**«Nessuno»** (branch `dev/backend-tid`, 2026-11-23): in `backend/` e `frontend/` nessun punto scrive su una vista,
né `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `COPY … FROM` né `TRUNCATE`; dal BE non serve nessun verbo nuovo. Come ha
cercato: le 193 viste della doc generata, tutte `vw_*`; una scansione dell'SQL scritto a mano su 2.769 file, test e
smoke compresi; le destinazioni in una variabile (`execute_dynamic_insert` / `execute_dynamic_update`, i mixin di
`vendite`, il BB delle note, i repository delle definizioni e dei conti), tutte tabelle, mentre le variabili che
contengono una vista stanno solo dopo `FROM` o `JOIN`; le quindici viste aggiornabili una per una, tutte in lettura;
i quindici modelli `managed = False`, tutti su tabelle, senza admin né fixture; il pannello, che scrive solo con
`config.fn_pannello_scrivi`; le liste, che scrivono su `ui.lista_*`.

**I due limiti che il BE dichiara, verificati dal DB sul catalogo di dbdev (2026-11-23):**

* *una vista aggiornabile che non si chiama `vw_*` o che non è nella doc*: le viste fuori da `maintenance` e `public`
  sono 193, come quelle della doc; l'unica aggiornabile con un altro nome è `public.geometry_columns`, di PostGIS;
* *le connessioni dei pgTAP*: nessun pgTAP scrive su una vista (le sole occorrenze di `UPDATE … vw_*` sotto `db/` sono
  titoli di changeSet).

**Che cosa ne segue per il giro 3.** Nessun verbo da scrivere prima: la revoca non ha lettori da censire. Il giro
decide `public.geometry_columns`: è un oggetto dell'estensione, con le sue regole di scrittura, e il loop lo tratta
oggi come ogni vista di `public`; lo si guarda nel giro, non si dà per scontato. ✅ Guardato (§7.1): regole
`DO INSTEAD NOTHING`; entra nella regola, chiusa dal provisioning.

## 6. Il giro 1, le porte di manutenzione — scritto il 2026-11-23

### 6.1 Che cosa si cambia

| File | Che cosa |
| --- | --- |
| `20_code/anagrafiche/20261123-43-update-trgfn-indirizzi-dettaglio-porta-proprietario` | porta 14: GUC **e** `fn_is_proprietario_tabella(TG_RELID)`; codice e frase del rifiuto invariati; `COMMENT` nuovo |
| `20_code/config/20261123-44-update-trgfn-toponomastica-porta-proprietario` | porta 15: stessa forma; montaggio invariato (`BEFORE UPDATE OF descrizione`); `COMMENT` riscritto |
| `90_end/20261123-45-postura-aprenti-manutenzione-riservati` | `REVOKE EXECUTE … FROM PUBLIC, zeroerp_app` su `dbops.fn_admin_merge_stradario` e `maintenance.proc_bump_toponomastica` |
| `90_end/ci_apply/20260205-41` (il loop) | `dbops.fn_admin_merge_stradario` in `v_fn_riservate` |
| `scripts/sql/provision_zeroerp.sql` | la stessa voce nel blocco «LA PORTA SULLE FUNZIONI» |
| `db/pgtap/dbops/test-porte-manutenzione-solo-proprietario-v1.sql` | nuovo, come app: forma, i due controesempi, la postura (12 test) |
| `db/pgtap/dbops/test-fusioni-comune-stradario-v1.sql` | marcatore `pgtap-runner: owner`, col motivo |
| `db/pgtap/maintenance/test-bump-toponomastica-v1.sql` | marcatore `pgtap-runner: owner`, col motivo |
| `db/pgtap/config/test-toponomastica-stradario-generale.sql` | passo 4: l'app non esegue la correzione (`42501`) e il toponimo resta com'era; il piano resta 11 |
| guide | `riclassificazione-vie`, `gestione-degli-indirizzi`, `tx_id_implementation_guide` (D-F), `architettura-permessi-e-autorizzazioni` §7.4 «La porta» |

Le due funzioni trigger restano INVOKER: è ciò che fa vedere al BB chi scrive (il test 1 lo presidia). Nessuna
variabile nuova nei corpi, quindi nessun `%TYPE` da ancorare.

**Le sedi della postura.** `fn_admin_merge_stradario` sta in `dbops`, dentro il loop: le tre sedi di §11.8.
`proc_bump_toponomastica` sta in `maintenance`, fuori dal loop e dal provisioning delle funzioni: lì l'`EXECUTE`
all'app arrivava solo dall'`=X` di PUBLIC, e basta il forward, come in `20_code/maintenance/20261014-55`.
⚠️ Il loop applica `v_fn_riservate` solo alle funzioni (`prokind = 'f'`): una procedura in quell'elenco non
sarebbe chiusa. Qui non serve, ma una procedura riservata in uno schema del loop chiederebbe di estenderlo.

### 6.2 La prova sullo scratch (`prova_changeset.py`, da owner, 2026-11-23)

- i tre changeSet più il loop, in testa al test nuovo: senza 2 ok / 10 not ok, con 6 ok / 6 not ok. Con l'estratto
  passano la forma (1), l'UPDATE che non tocca `stradario_id` (4) e la postura (7-10). Restano rossi 2, 3, 5, 6, 11
  e 12, ed è il comportamento giusto da owner: il proprietario con la GUC passa, e gli strumenti li può chiamare.
  Il verdetto come app arriva dopo l'apply;
- i tre changeSet in testa ai due file che passano all'owner: `test-fusioni-comune-stradario-v1` 37/37 →
  37/37, `test-bump-toponomastica-v1` 8/8 → 8/8. È il ramo del proprietario: la fusione sposta gli indirizzi, la
  correzione arriva fino agli indirizzi, con le porte chiuse all'app;
- catalogo identico prima e dopo; guardrail runOnChange, preCondition, ruoli batch e preambolo pgTAP verdi.

### 6.3 L'esito — 2026-11-24

✅ Tid ha applicato i tre changeSet e la passata `ci_apply`; i quattro pgTAP del giro sono verdi. Resta la doc
auto-generata delle due funzioni trigger, da rigenerare (cambia il `COMMENT`).

### 6.4 Due fatti trovati facendo il giro, e la proposta D-G

- `dbops.fn_admin_merge_comune` è lo strumento gemello: fonde due comuni e ripunta ogni figlia letta dal catalogo.
  È INVOKER, senza un guard del permesso, e l'app lo esegue. Non lo chiama nessuna funzione DB, né il BE (ramo
  `origin/dev/backend-tid`, 2026-11-24).
- In `maintenance` l'app esegue sette routine, tutte tramite l'`=X` di PUBLIC: `proc_bump_indirizzi_dettaglio`,
  `proc_sync_storico_set_storicizza`, `fn_analyze_statistiche`, `fn_apply_storicizza_defaults`, `fn_run_and_log`
  (INVOKER), `fn_job_run_log_failure` e `fn_sveglia_accesa` (DEFINER). Il provisioning dice «nessuna funzione di
  `maintenance`» all'app. Chi le chiama a DB sono le `proc_*_job` (DEFINER, girano come proprietario) e
  `proc_bump_toponomastica` (ormai riservata). Il BE ne chiama una sola, `fn_sveglia_accesa`
  (`maintenance_repository`, il comando `e_dovuto`); delle altre parla solo nei commenti. Con
  `fn_job_run_log_failure`, l'app può scrivere nel giornale dei job una corsa fallita che nessun job ha fatto.

Sono lo stesso tema del brief (l'app scrive senza passare da un verbo, attraverso uno strumento che non è per
lei), e non porte: per questo D-G, non un brief nuovo.

**D-G** (a Tid): **a** un giro 1-bis qui: `fn_admin_merge_comune` in `v_fn_riservate` (tre sedi di §11.8), e in
`maintenance` l'`EXECUTE` revocato a PUBLIC su tutto, con il solo `fn_sveglia_accesa` concesso all'app per nome; un
pgTAP **a criterio**: in `maintenance` l'app esegue solo l'elenco dichiarato · **b** solo
`fn_admin_merge_comune`, `maintenance` in un brief suo · **c** niente, dichiarati. ⭐ **a**.
⚠️ Il limite che decide la forma: in PostgreSQL i privilegi di default **per schema** si sommano a quelli globali e
non tolgono l'`=X` di PUBLIC. Quindi una routine nuova di `maintenance` nasce comunque aperta, e a fermarla è il
pgTAP a criterio, insieme al `REVOKE … FROM PUBLIC` nel changeSet che la crea (lo stampo di
`20_code/maintenance/20261014-55`). Prima del giro si verifica con quale ruolo gira `e_dovuto`.

✅ **D-G decisa da Tid il 2026-11-24: a.** ⚠️ La metà su `maintenance` è sospesa da D-H (§6.5): la verifica prima
del giro ne ha smentito la premessa.

### 6.5 Il giro 1-bis — 2026-11-24

**La verifica chiesta da Tid: `e_dovuto` gira come `zeroerp_app`.** `backend/bin/run-command.sh` lancia
`manage.py`; Django ha una connessione sola, `DATABASES["default"]`, con `DB_USER`, che `backend/.env.example`
fissa a `zeroerp_app` (ramo `origin/dev/backend-tid`, 2026-11-24). E i passi dei job pgAgent chiamano
`maintenance.fn_sveglia_accesa` direttamente, come `zeroerp_job`. Oggi tutti e due la ricevono solo da PUBLIC: una
revoca a PUBLIC le deve concedere a tutti e due per nome, e la concessione a `zeroerp_job` sta nel provisioning, fase
`post`, accanto alle procedure dei job.

**La premessa di D-G su `maintenance` non regge (smentita sul modello, 2026-11-24).** Una routine INVOKER gira coi
privilegi di chi la chiama: all'app non dà niente che l'app non possa fare da sé con i suoi permessi. In giro 1 la
differenza la faceva la **porta** che `proc_bump_toponomastica` apriva, non la procedura. Fra le sette, nessuna INVOKER
apre una porta. Delle due DEFINER, `fn_sveglia_accesa` legge, e la usano il BE e pgAgent. `fn_job_run_log_failure`
scrive una corsa fallita nel giornale, timbrando `ruolo_sessione` e `agent_host` della sessione: è ciò che l'app fa
già col verbo pubblico `script.fn_job_run_start` / `fn_job_run_end` (DEFINER, `p_origine` scelto dal chiamante), che
usa per i suoi processi headless. La riga «senza un job» che la §6.4 attribuiva a `fn_job_run_log_failure` l'app la
scrive comunque, e firmata come sé.
Chiudere `maintenance` a PUBLIC sarebbe quindi ordine della postura, non una strada chiusa, e costerebbe tre pgTAP
che girano come app e chiamano quelle routine (`test-fn-analyze-statistiche-v1` 4-7, che perderebbe il suo caso
negativo; `config/test-stradario-riclassificazione-unico` 5; `script/test-canale-log-v1` 12 e il verbale «spento»).

**D-H** (a Tid): **a** su `maintenance` niente revoca: si corregge il commento del provisioning («nessuna funzione di
`maintenance`» non è vero) e un pgTAP **a criterio** guarda la classe che conta, «in `maintenance` le DEFINER
eseguibili dall'app sono solo quelle dichiarate» (oggi `fn_sveglia_accesa`, `fn_job_run_log_failure`) · **b** la
revoca completa di D-G, con i tre pgTAP rifatti e le due concessioni di `fn_sveglia_accesa` · **c** niente.
⭐ **a**: presidia l'unico caso in cui una routine di `maintenance` darebbe all'app più dei suoi permessi, cioè una
DEFINER nuova nata con l'`=X` di PUBLIC.

**La fusione dei comuni (metà di D-G che regge), scritta e provata il 2026-11-24.** Anche lei è INVOKER e non apre
porte, quindi non è una strada chiusa: è la coerenza col giro 1 («le fusioni sono strumenti DBA», guida
`riclassificazione-vie`), a costo minimo.

| File | Che cosa |
| --- | --- |
| `90_end/20261123-46-postura-fn-admin-merge-comune-riservata` | `REVOKE EXECUTE … FROM PUBLIC, zeroerp_app` |
| `90_end/ci_apply/20260205-41` | la voce in `v_fn_riservate` |
| `scripts/sql/provision_zeroerp.sql` | la voce nel blocco «LA PORTA SULLE FUNZIONI» |
| `db/pgtap/dbops/test-porte-manutenzione-solo-proprietario-v1.sql` | 13-14: l'app e PUBLIC non la eseguono (piano 14) |
| `db/pgtap/dbops/test-fusioni-comune-stradario-v1.sql` | il motivo del runner owner la nomina |
| guida `riclassificazione-vie` | la nomina fra gli strumenti DBA |

Prova sullo scratch (`prova_changeset.py`, da owner): il test nuovo passa da 6 ok / 8 not ok a 8 ok / 6 not ok (13 e
14 diventano verdi; i sei rossi sono quelli che da owner sono rossi per costruzione, §6.2); le fusioni restano 37/37;
catalogo identico, guardrail verdi. ✅ Applicato da Tid, pgTAP verdi (2026-11-24).

**D-H decisa da Tid il 2026-11-24: a. Scritta lo stesso giorno**, nessun changeSet:

| File | Che cosa |
| --- | --- |
| `scripts/sql/provision_zeroerp.sql` | il commento «nessuna funzione di `maintenance`» corretto: niente GRANT, ma l'`=X` di PUBLIC resta sulle routine senza REVOKE; perché le INVOKER non sono una strada, e l'elenco delle DEFINER aperte |
| `db/pgtap/maintenance/test-app-definer-dichiarate-v1.sql` | nuovo, come app, a criterio: in `maintenance` le DEFINER eseguibili dall'app sono esattamente `fn_sveglia_accesa` e `fn_job_run_log_failure` (`set_eq`, in tutti e due i versi), e le due esistono e sono DEFINER (piano 2) |

Il criterio letto sul catalogo, in sola lettura (2026-11-24): su dbdev e sullo scratch dà esattamente le due voci.
Preambolo pgTAP verde. Il caso costruito (una DEFINER nuova in `maintenance`) chiede DDL che l'app non può fare: il
test lo dichiara, e il presidio è il criterio, che vale per ogni routine presente. Nessuna guida descrive le due
funzioni (`guide_coinvolte.py`: orfane, dettagli interni dei job). ✅ Test verde come app (Tid, 2026-11-24).

## 7. Il giro 3, le viste — scritto il 2026-11-24

### 7.1 I fatti che decidono la forma (catalogo di dbdev, 2026-11-24)

- Il loop concede `SELECT, INSERT, UPDATE, DELETE` a ogni relazione `relkind` `r`, `p`, `v`, `m`, `f` degli schemi
  applicativi; il provisioning, fase `post`, fa lo stesso con `GRANT … ON ALL TABLES` anche in `public` e
  `django`, e lì gira come superuser. L'app aveva il DML su **197** viste: le 193 di progetto e quattro di `public`
  delle estensioni (`geometry_columns`, `geography_columns` di PostGIS; `pg_all_foreign_keys`, `tap_funky` di pgTAP).
- Nessuna funzione DB scrive su una vista (corpi di `pg_proc`); ogni vista fuori da `maintenance` è leggibile
  dall'app. Il BE non scrive su nessuna vista (§5.1).
- **`public.geometry_columns`** (la domanda di §5.1): è «aggiornabile» solo perché PostGIS ci monta tre regole
  `DO INSTEAD NOTHING` per `INSERT`, `UPDATE` e `DELETE`. Il DML lì non fa niente. Entra nella regola come ogni vista,
  e la chiude il provisioning, perché è di `postgres`.
- Nessuna vista materializzata oggi: entrano nello stesso ramo, perché il DML su di loro non esiste e il privilegio
  non serve.

### 7.2 Che cosa si cambia

| File | Che cosa |
| --- | --- |
| `90_end/20261123-47-postura-viste-solo-select-app` | `REVOKE INSERT, UPDATE, DELETE … FROM zeroerp_app` su ogni vista e materializzata del proprietario |
| `90_end/ci_apply/20260205-41` (il loop) | il ramo **per tipo** (`v`, `m`), in testa, prima degli elenchi per nome: solo `SELECT` |
| `scripts/sql/provision_zeroerp.sql` | blocco «POSTURA DICHIARATA: le viste», fase `post`, prima degli append-only: arriva anche alle quattro di `public`; `django` fuori (§11.9) |
| `db/pgtap/dbops/test-viste-app-solo-select-v1.sql` | nuovo, come app, a criterio (piano 5): nessuna vista dà il DML all'app; la lettura resta; il perimetro non è vuoto; `UPDATE` e `DELETE … WHERE false` su una vista aggiornabile del proprietario senza `security_invoker`: `42501` |
| `linee-guida-sql.md` | §6 la regola; §11.8 il ramo per tipo e il limite dei privilegi di default |
| guida `architettura-permessi-e-autorizzazioni` §7.4 «La porta» | il punto sulle viste (era **indietro**, ora coerente) |

⚠️ Il limite, dichiarato in tutte e tre le sedi: `ALTER DEFAULT PRIVILEGES … ON TABLES` non distingue una vista da
una tabella. Una vista nuova nasce col DML all'app fino alla passata `ci_apply` successiva; in CI la passata viene
prima dei pgTAP, e il presidio la vede. Il caso costruito (una vista nuova) chiede DDL, che l'app non può fare: il
test lo dichiara, e il presidio è il criterio (§3-ter.4: non un `REVOKE` nel test).

### 7.3 La prova sullo scratch (`prova_changeset.py`, da owner)

- Il forward e il loop in testa al test nuovo: 2 ok / 3 not ok, prima e dopo. Verdi la lettura (2) e il perimetro
  (3); rossi da owner per costruzione il 4 e il 5 (il proprietario scrive). L'1 resta rosso **solo** per le quattro
  viste di `public`: lo prova un pgTAP diagnostico usa e getta, con l'estratto 0 → 1 ok sull'elenco esatto dei
  residui `public.geography_columns, public.geometry_columns, public.pg_all_foreign_keys, public.tap_funky`. Quelle
  le chiude la fase `post` del provisioning, che la prova non esegue;
- la query del blocco del provisioning, letta su dbdev con l'elenco degli schemi in linea, genera 197 revoche, 4 in
  `public`;
- catalogo identico; guardrail e preambolo verdi.

### 7.4 L'esito — 2026-11-24

✅ Tid ha applicato `20261123-47` e la passata `ci_apply`. Il test nuovo, prima della fase `post`, era rosso
**solo** sul test 1, con i quattro residui previsti dalla prova (`geography_columns`, `geometry_columns`,
`pg_all_foreign_keys`, `tap_funky`); gli altri quattro test erano verdi. Dopo la fase `post` del provisioning su
dbdev (`sudo -u postgres psql -d zeroerp -v fase=post < scripts/sql/provision_zeroerp.sql`) il test è verde, 5/5.
È la conferma della terza sede di §11.8: le viste di `public` delle estensioni le chiude solo il provisioning.
⚠️ Lo scratch si allinea quando lo ricostruisce `ci-local.sh`, che lancia la fase `post`.

## 8. Il giro 12-13, i legami della bolla — scritto il 2026-11-24

Nessun changeSet (D-E a): il trigger `vendite.trgfn_ddt_riga_legame_guard` resta com'è. Il giro fissa i due rami
del `DELETE` in un pgTAP e li scrive nella guida.

**Che cosa c'era già.** `vendite/test-ddt-righe-evase-dall-ordine-v1` (gira come app) ha il test 41: fuori bozza,
la sola GUC del legame accesa a mano non toglie il legame. Non prova la condizione del proprietario: senza la
seconda GUC (`zeroerp.doc_ritira_legami`), `fn_doc_porta_ritiro_ammette` risponde no anche al proprietario. Il
test 43 è un'altra porta (la correzione della quantità, `zeroerp.ddt_riga_correggi_qta`).

| File | Che cosa |
| --- | --- |
| `db/pgtap/vendite/test-ddt-righe-evase-dall-ordine-v1.sql` | piano 43 → 45. **44**: fuori bozza (la bolla A, emessa) l'app accende **tutte e due** le GUC del ritiro dell'annullo e cancella il legame diretta: rifiuto, perché manca il proprietario. Rosso da owner per costruzione, come il 43. **45**: in bozza (bolla K, nuova dal builder) la sola GUC sulla riga basta, il `DELETE` diretto toglie il legame (1 riga): la scelta di D-E a, fissata |
| guida `gestione-ddt` | §15.3 «Chi toglie un legame»: la bozza con il solo parametro della riga, come scelta; fuori bozza anche il ritiro della bolla e il proprietario. Nel «Vedi anche» il guard e `fn_doc_porta_ritiro_ammette`, che nessuna guida citava |

Il ramo è lo stesso per le due tabelle (`ordini_righe_fulfillment`, porta 12, e `resi_righe_riconsegne`, porta 13):
una funzione sola, montata con gli argomenti del trigger. Il test lo prova sulla prima; dichiarato. I due casi senza
bolla o senza stato (`v_ddt_id IS NULL`, `v_stato_ddt IS NULL`) restano aperti con la sola GUC, come in §3-ter.2, e
non hanno un test: sono le righe che la cascata della testata porta via.

Preambolo pgTAP verde. Nessuna prova sullo scratch: senza changeSet `prova_changeset.py` non si applica, e da owner
il 44 sarebbe rosso per costruzione. ✅ Verde come app, 45/45 (Tid, 2026-11-24).

## Registro

| Data | Chi | Che cosa |
| --- | --- | --- |
| 2026-11-24 | Tid | **D-K decisa** (§4.7): il primo amministratore nasce da un verbo DB di primo impianto che si chiude alla nascita del primo SUPER_ADMIN (R-DB-K1), poi un comando BE; la porta di `fn_crea_operatore_v2` al piano dei giri (R-DB-K2) |
| 2026-11-24 | BE | D-J fatta (§4.7): bypass di `is_superuser` tolti nel BE, BB `super_admin_di_prova` (ok Tid), 129 classi di test dichiarate, test del bypass rovesciati; suite verde come la base |
| 2026-11-24 | Tid | **D-J decisa: a**, `is_superuser` non concede più niente; il lavoro BE parte subito (§4.7) |
| 2026-11-24 | Tid | **D-I decisa: il task `reset_lotto_draft` si ritira**, dopo la riverifica (nessun esecutore, né nel BE né a DB); prima il DB, poi il BE (§4.6). D-J proposta (§4.6) |
| 2026-11-24 | BE | Risposta alla richiesta 3d (§4.5): la tabella dei dieci verbi con le funzioni di decisione; due correzioni a §4.3 (`reset_lotto_draft` spenta, la riconsegna chiede il livello su `vendite.reso` e non `conferma_reso`); il superuser Django passa l'endpoint (decisione a Tid); nessun processo headless raggiunge i verbi, il task `reset_lotto_draft` non lo esegue nessun percorso; i test della Parte C che girano senza contesto o con l'utente tecnico senza profilo; le quattro primitive mai chiamate dal BE |
| 2026-11-24 | DB | Richiesta 3d al BE scritta (§4.4): dieci verbi da portare a DEFINER, precompilati dal ramo del BE (chiamanti, view, meccanismo del permesso); parti B (utente tecnico della pipeline) e C (test che chiamano i verbi, primitive da chiudere) |
| 2026-11-24 | Tid | Giro 3 applicato; fase `post` del provisioning su dbdev; `test-viste-app-solo-select-v1` verde 5/5 (prima della fase `post` rosso solo sulle quattro viste di `public`, come previsto, §7.4) |
| 2026-11-24 | DB | Giro 3 scritto (§7): le viste in sola lettura per l'app nelle tre sedi (`20261123-47`, il ramo per tipo del loop, la fase `post`), pgTAP a criterio, §6 e §11.8 delle linee guida, guida dei permessi §7.4; `geometry_columns` deciso (regole `DO INSTEAD NOTHING`, chiusa dal provisioning); provato sullo scratch |
| 2026-11-24 | Tid | Giro 3 al via; `test-app-definer-dichiarate-v1` verde |
| 2026-11-24 | DB | D-H a scritta (§6.5): commento del provisioning corretto, pgTAP a criterio `test-app-definer-dichiarate-v1`; nessun changeSet |
| 2026-11-24 | Tid | **D-H decisa: a** · `20261123-46` applicato, pgTAP verdi |
| 2026-11-24 | DB | Giro 1-bis (§6.5): `e_dovuto` gira come `zeroerp_app`; la metà di D-G su `maintenance` smentita sul modello (le INVOKER non danno all'app più dei suoi permessi), D-H a Tid; la fusione dei comuni riservata (`20261123-46`), provata sullo scratch |
| 2026-11-24 | Tid | **D-G decisa: a** |
| 2026-11-24 | Tid | Giro 1 applicato, pgTAP verdi (§6.3) |
| 2026-11-24 | DB | D-G proposta (§6.4): `fn_admin_merge_comune` e le sette routine di `maintenance` eseguibili dall'app; chiamanti letti a DB e sul ramo del BE |
| 2026-11-23 | DB | Brief aperto su richiesta di Tid, dalla ricognizione §5.8 di `brief-db-magazzino-tutte-le-scritture-dal-verbo`: quindici porte censite sul catalogo, tre decisioni |
| 2026-11-23 | DB | Analisi critica (§3-bis): aprenti delle porte 8 e 10 trovati (`SET LOCAL`), porte 16 e 17 aggiunte, D-2 superata; la strada D-1 a riletta come passaggio al modello del verbo; D-A … D-D proposte |
| 2026-11-23 | DB | Su decisione di Tid il brief ospita la seconda famiglia, le viste aggiornabili (§5, D-V), da `brief-db-revisione-anagrafiche` §19; la richiesta al BE diventa una sola per le due famiglie (§4.1) |
| 2026-11-23 | DB | La risposta del BE alla Parte B: «nessuno»; i due limiti verificati sul catalogo (§5.1). Il giro 3 non aspetta più il BE |
| 2026-11-23 | DB | La Parte A letta sul ramo del BE, su indicazione di Tid (§4.2): nessuna porta accesa dal BE; i percorsi dei nove aprenti; le porte 14, 15 e 17 senza chiamanti |
| 2026-11-23 | DB | Riverifica della D-A dopo le modifiche al documento: nessun changeSet di codice applicato dopo le 17:30, aprenti e annulli come in §4.3, la rete di scope c'è; trovato un brief vicino non dichiarato (`brief-incassi-riconciliazione-rate-promemoria`, porte 8 e 9); §3 e un punto di §4.2 marcati superati |
| 2026-11-23 | Tid | **D-D decisa: a**, la porta 14 nel giro 1 con la 15; S50 di `brief-db-revisione-anagrafiche` rimanda qui. Tutte le decisioni prese |
| 2026-11-23 | Tid | **D-C decisa: b** per 14, 15 e 17; la 17 si chiude con tutte e due le chiavi (la GUC e la riga di `config.parameters`, trovata scrivibile dall'app) |
| 2026-11-23 | Tid | **D-A decisa: a**; D-B decaduta. Le soluzioni ai due rischi (perimetro, permesso) entrano nel piano come voci obbligatorie di ogni giro |
| 2026-11-23 | DB | Giro 1 scritto (§6): porte 14 e 15 a «GUC + proprietario» (`20261123-43`, `-44`), i due aprenti riservati (`-45`, loop, provisioning), un pgTAP nuovo e tre adeguati, quattro guide; provato sullo scratch. Da applicare |
| 2026-11-23 | Tid | **D-E decisa: a** (la bozza delle 12-13 resta con la GUC sulla riga, dichiarata) · **D-F decisa: a** (la 17 esce dalla D-C, interruttore di timbratura dichiarato). Tutte le decisioni prese |
| 2026-11-23 | DB | Verifica critica a decisioni prese (§3-ter): la porta 17 non ferma nessuna scrittura (D-F a Tid); il ramo fuori bozza delle 12-13 chiede già il proprietario (D-E a Tid); una porta fuori dai trigger, `fn_check_fondo_cancellabile`; il pgTAP delle viste e le primitive passano da `v_fn_riservate` e dal criterio del loop |
| 2026-11-23 | DB | La strada D-A a riletta porta per porta (§4.3): gli annulli sono già DEFINER, quindi le porte 12-13 chiedono solo il trigger e il fermo non entra; la porta 16 chiede di separare il seed dal verbo |
