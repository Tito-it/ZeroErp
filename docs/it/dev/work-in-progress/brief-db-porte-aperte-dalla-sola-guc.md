# Brief DB — le strade per cui l'app scrive senza il verbo: le porte della sola GUC e le viste aggiornabili

> **⏭️ Chi riparte — aggiornato al 2026-11-25**
>
> **Riparte: il team BE**, con la richiesta di R-DB-K1 e R-DB-K4 (§4.9.7, passo 3j: `20261125-30` … `-32`, i due CSV degli errori, i due seed di `tid` tolti; ✅ scritto e provato sullo scratch, ✅ applicato da Tid e pgTAP verdi il 2026-11-25, doc auto-generata rigenerata, committato). **Tid**, con la richiesta al BE del giro unico 8 + 1-7 (§13.9, committato `e4bf00af69`: ✅ scritto e provato dal team DB, ✅ applicato da Tid, pgTAP come app verdi e doc auto-generata rigenerata il 2026-11-25; `20261125-01` … `-22`, `-26`): la richiesta di §13.8 (6e-septies). **Il team DB**, al via di Tid: il giro 10-bis quando il BE risponde al censimento di §10.6. **Il team BE**, col 6d-quinquies del giro 11 (§12.6: ✅ applicato da Tid e verde il 2026-11-25, con `20261124-12`, §12.7). **Il team BE**, col 6c-quinquies del giro 9 (§11.6: ✅ applicato da Tid e verde il 2026-11-25). **Il team BE**, col 6b-quinquies del giro 10 (§10.6: ✅ applicato da Tid e verde il 2026-11-25). **Il team BE**, col passo 3n di R-DB-I3 (§4.8: ✅ scritta, applicata da Tid e verde il 2026-11-24) e col 3k-bis
> di R-DB-K3, e col 6a-quinquies del giro 16 (§9.5). **Il team DB**, col giro unico 8 + 1-7 (i giri 16, 10, 9, 11 sono applicati e verdi) e con le due richieste nuove del BE da §4.7, R-DB-K3 (la descrizione di `E_SCOPE_SENZA_UTENTE`, passo 3k: ✅ scritta e applicata il 2026-11-24, ora la rigenerazione del BE, 3k-bis) e R-DB-K4 (i due changeSet del
> SUPER_ADMIN di sviluppo, passo 3l). Al via di Tid: il verbo di primo impianto (D-K, R-DB-K1, passo 3i) e i giri
> delle porte del flusso. ✅ Il ritiro di `reset_lotto_draft` è fatto, DB e BE (2026-11-24, §4.8). Il superuser Django è
> deciso (D-J **a**) e fatto nel BE (§4.7); il `None` del perimetro si rifiuta (§4.7, BE, 2026-11-24).
> ✅ Fatti e verdi (Tid, 2026-11-24): giro 1 (porte di manutenzione 14 e 15, la 17 dichiarata), giro 1-bis (la
> fusione dei comuni, il presidio di `maintenance`), giro 3 (le viste in sola lettura per l'app, con la fase `post`
> del provisioning su dbdev), giro 12-13 (i legami della bolla, §8). Tutto applicato e committato.
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
> | 3e | team DB | ✅ letta la risposta 3d (2026-11-24): §4.3 corretta, il guard di ogni porta coi BB che ci sono, i builder per i test della Parte C, due punti per i giri 8 e 1-7 | §4.5-bis | — |
> | 3e-bis | Tid | ✅ D-L **a** (2026-11-24): `dbops.fn_pgtap_concedi_livello_area` nasce nel primo giro che lo usa (8 o 1-7), le quattro copie `pg_temp.livello_area` si ritirano nello stesso giro | §4.5-bis | — |
> | 3f | Tid | ✅ D-I: il task `reset_lotto_draft` si ritira · ✅ D-J: il superuser Django non concede più niente, strada **a** (2026-11-24) | §4.6 | — |
> | 3h | team BE | D-J: ✅ bypass tolti, test adeguati, suite verde · ✅ rivisto con `/verifica` (2026-11-24) | §4.7 | — |
> | 3i | team DB | D-K: il verbo `fn_crea_primo_amministratore` e la sua prova (R-DB-K1); la porta di `fn_crea_operatore_v2` nel piano dei giri (R-DB-K2) · ✅ analisi con R-DB-K4, ✅ scritto e provato (2026-11-25) | §4.7, §4.9 | — |
> | 3i-bis | Tid | R-DB-K1 e R-DB-K4: ✅ D-K7 **b**, ✅ D-K8 **a2**, ✅ il via (2026-11-25) | §4.9.3, §4.9.4 | — |
> | 3i-ter | team DB | R-DB-K1 e R-DB-K4: ✅ `20261125-30` … `-32`, CSV, seed tolti, pgTAP, guide e `manual/`; prova sullo scratch (2026-11-25) | §4.9.6 | — |
> | 3i-quater | Tid | R-DB-K1 e R-DB-K4: ✅ apply, ✅ pgTAP come app e `test-crea-primo-amministratore-v1` su dbdev verdi, ✅ doc auto-generata rigenerata (2026-11-25) | §4.9.6 | 3i-ter |
> | 3j | team BE | il comando, `genera_error_policies`, il censimento dei lettori: la richiesta | §4.9.7 | 3i-quater |
> | 3k | team DB | R-DB-K3: la descrizione di `E_SCOPE_SENZA_UTENTE` allargata alle letture · ✅ scritta, ✅ applicata da Tid, `test-catalogo-messaggi-errore-completo` verde (2026-11-24) | §4.7 | — |
> | 3k-bis | team BE | R-DB-K3: dopo l'apply, `manage.py genera_error_policies` (le `note` di `E_SCOPE_SENZA_UTENTE` e `E_UI_CHIAMATA_NON_VALIDA` sono cambiate: `test_il_file_generato_e_allineato_al_catalogo` è rosso fino alla rigenerazione) | §4.7 | 3k |
> | 3l | team DB | R-DB-K4: i due changeSet del SUPER_ADMIN di sviluppo (`20260309-01`, `20260419-95`): ritirarli o farli passare dal verbo di R-DB-K1 · ✅ analisi: la (b) non si può fare; ✅ D-K8 **a2**, i due file tolti (2026-11-25) | §4.7, §4.9.4 | — |
> | 3g | team DB, poi team BE | il ritiro del task `reset_lotto_draft`: ✅ analisi, ✅ D-I.1 **a** e D-I.2 **a** (Tid), ✅ scritto, applicato, pgTAP 9/9, pushato · ✅ il BE: whitelist, handler, esclusione del runner, test e manuali (2026-11-24) | §4.6, §4.8 | — |
> | 3m | team DB | R-DB-I3 (D-I.3 **a**, Tid): ✅ `distruttivo` sul registro, `auto_step_rollback` colonna della pipeline col `CHECK` sul `meta`, `vendite.fn_check_rollback_step_automatico`, pgTAP 14/14 sullo scratch, guide (2026-11-24) | §4.8 | — |
> | 3m-bis | Tid | R-DB-I3: ✅ apply (`20261123-95`, `-96`, `-97` e i due mirror), pgTAP `test-rollback-step-automatico-v1` come app verde, doc auto-generata rigenerata (2026-11-24) | §4.8 | — |
> | 3n | team BE | R-DB-I3: il runner chiede `vendite.fn_check_rollback_step_automatico` al posto di `is_auto_step_rollback_attivo`, i test che scrivono la chiave nel `meta` passano alla colonna, manuale `api_pipeline_task` (⚠️ dall'apply `test_auto_step_rollback_dalla_pipeline_db` è rosso: atteso) | §4.8 | — |
> | 3o | Tid, poi team BE | dalla `/verifica` del 2026-11-24: ✅ D-K5 **a** (il resolver delega al BB), ✅ D-K6 **a** (il motore documentale riceve l'utente tecnico), ✅ D-I.4 **a** (`auto_step_rollback` dalla pipeline) · ✅ il BE, coi test (2026-11-24) | §4.7, §4.8 | — |
> | 4 | team BE / DB | ✅ Parte B, le viste: «nessuno», dal BE (2026-11-23) · ✅ Parte A, le GUC e gli aprenti: letta dal DB sul ramo del BE (2026-11-23) | §4.2, §5.1 | — |
> | 4a | Tid | ✅ il giro 1: applicato, pgTAP verdi (2026-11-24) | §6 | — |
> | 4c | Tid | ✅ D-G (**a**) · ✅ D-H (**a**), 2026-11-24 | §6.4, §6.5 | — |
> | 4d | Tid | ✅ l'apply di `20261123-46`, pgTAP verdi · ✅ il pgTAP di D-H come app, verde (2026-11-24) | §6.5 | — |
> | 4b | team DB | ✅ il giro 3, le viste: scritto e provato sullo scratch (2026-11-24) | §7 | — |
> | 4e | Tid | ✅ il giro 3: apply, `ci_apply`, fase `post` del provisioning su dbdev, pgTAP verde (2026-11-24) | §7.4 | — |
> | 5 | Tid / team BE | ✅ la richiesta 3d girata al BE, e la risposta (2026-11-24) | §4.5 | — |
> | 5b | team DB | ✅ il giro 12-13, verde come app (2026-11-24) | §8 | — |
> | 6 | team DB | i giri delle porte del flusso 16, 10, 9, 11, 8, 1-7 | Il piano | — |
> | 6a | team DB | giro 16: ✅ analisi (2026-11-24) | §9 | — |
> | 6a-bis | Tid | giro 16: ✅ D-M **a**, ✅ D-N **a**, il via (2026-11-24) | §9.3 | — |
> | 6a-ter | team DB | giro 16: ✅ `20261123-98`, `-99`, pgTAP nuovo e quattordici adeguati, guide e `manual/`, provato sullo scratch (2026-11-24) | §9.4 | — |
> | 6a-quater | Tid | giro 16: ✅ apply, pgTAP come app verdi, doc auto-generata rigenerata (2026-11-24) | §9.4 | — |
> | 6a-quinquies | team BE | giro 16: i test Django che pubblicano danno `documenti_template_manage` (§9.5) | §9.5 | — |
> | 6b | team DB | giro 10: ✅ analisi (2026-11-24) | §10 | — |
> | 6b-bis | Tid | giro 10: ✅ D-O **a**, ✅ D-P **a**, ✅ D-Q **a**, il via (2026-11-24) | §10.3 | — |
> | 6b-ter | team DB | giro 10: ✅ `20261124-01` … `-06`, le altre due sedi di §11.8, pgTAP nuovo e ventiquattro adeguati, guide e `manual/`, provato sullo scratch (2026-11-25) | §10.5 | — |
> | 6b-quater | Tid | giro 10: ✅ apply, pgTAP come app verdi, doc auto-generata rigenerata (2026-11-25) | §10.5 | — |
> | 6b-quinquies | team BE | giro 10: i test che chiamano il verbo da SUPER_ADMIN; il censimento di chi scrive `config.user_emittenti_fiscali` (per il giro 10-bis) | §10.6 | — |
> | 6c | team DB | giro 9: ✅ analisi, D20-b riletta (2026-11-25) | §11 | — |
> | 6c-bis | Tid | giro 9: ✅ D-S **a**, il via (2026-11-25) | §11.3 | — |
> | 6c-ter | team DB | giro 9: ✅ `20261124-07` … `-09`, pgTAP nuovo e quattro adeguati, guida e `manual/`, provato sullo scratch (2026-11-25) | §11.5 | — |
> | 6c-quater | Tid | giro 9: ✅ apply, pgTAP come app verdi, doc auto-generata rigenerata (2026-11-25) | §11.5 | — |
> | 6c-quinquies | team BE | giro 9: i test che chiamano il verbo danno `registra_distinta`; la mappatura di `E_SCOPE_EMITTENTE` dal verbo | §11.6 | — |
> | 6d | team DB | giro 11: ✅ analisi, nessuna decisione nuova (2026-11-25) | §12 | — |
> | 6d-ter | team DB | giro 11: ✅ `20261124-10`, `-11`, pgTAP nuovo (i ventuno esistenti invariati), guide e `manual/`, provato sullo scratch (2026-11-25) | §12.5 | — |
> | 6d-bis | team DB | il blocco `EXCEPTION` del giro 9 tolto (decisione di Tid, 2026-11-25): ✅ `20261124-12` scritto e provato | §12.7 | — |
> | 6d-quater | Tid | giro 11 e `20261124-12`: ✅ apply, pgTAP come app verdi, doc auto-generata rigenerata (2026-11-25) | §12.5, §12.7 | — |
> | 6d-quinquies | team BE | giro 11: i test che chiamano il verbo con un operatore senza il livello su `vendite.reso` | §12.6 | — |
> | 6e | team DB | giro 8: ✅ analisi, D10-D11 rilette (2026-11-25) | §13 | — |
> | 6e-bis | Tid | giro 8: ✅ D-T **b** (i giri 8 e 1-7 insieme), D-U **a** (2026-11-25) | §13.3 | — |
> | 6e-ter | team DB | giro 8 + 1-7: ✅ l'analisi della parte 1-7, col passaggio senza azione (2026-11-25) | §13.5-§13.8 | — |
> | 6e-quater | Tid | giro 8 + 1-7: ✅ D-W **a**, D-X **a**, D-Y **a**, D-Z **a**, ✅ il via, ✅ runner owner per i pgTAP delle strade chiuse (2026-11-25) | §13.7, §13.9 | — |
> | 6e-quinquies | team DB | giro 8 + 1-7: ✅ changeSet, pgTAP, builder, guide e `manual/`, prova sullo scratch (2026-11-25) | §13.9 | — |
> | 6e-sexies | Tid | giro 8 + 1-7: ✅ apply, ✅ pgTAP come app verdi, ✅ doc auto-generata rigenerata dopo le pagine `manual/` (2026-11-25) | §13.9 | — |
> | 6e-septies | team BE | giro 8 + 1-7: la richiesta | §13.8 | — |
>
> Decisioni aperte di Tid: nessuna (D-K7 **b** e D-K8 **a2** decise il 2026-11-25, §4.9; D-W … D-Z il 2026-11-25, §13.7). R-DB-K1 e R-DB-K4 sono applicati, verdi e committati (2026-11-25). Il blocco `EXCEPTION` del giro 9 si toglie (Tid, 2026-11-25: `20261124-12`, §12.7): è deciso.
> Committati il 2026-11-24 i giri 1, 1-bis e 3 (`64f00b35b1`), il giro 12-13
> (`969ea14566`), dal BE §4.5-§4.7 con D-J (`4271a0dc69`, PR #232), e il 2026-11-24 il lato DB del ritiro di
> `reset_lotto_draft` con la pulizia della testata (§4.8). Dal BE, il 2026-11-24 (`5fc466c729`): il `None` del perimetro
> che si rifiuta, il lato BE del ritiro di `reset_lotto_draft`, D-K5, D-K6 e D-I.4, e le richieste R-DB-K3, R-DB-K4 e
> R-DB-I3. Dal DB, il 2026-11-24 su `dev/db-tid`: R-DB-K3 (§4.7) e R-DB-I3 (§4.8), applicate e verdi; il giro 16
> (`3045e11677`) e il 2026-11-25 il giro 10 (§10.5), pushati. Il 2026-11-25 anche il giro 9 (§11.5), pushato. Il 2026-11-25 anche il giro 11 (§12.5) con `20261124-12` (§12.7), `8f29eee1cb`, PR #241. Il 2026-11-25 anche il giro 8 + 1-7 (§13.9), `e4bf00af69`, pushato.
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
  (§4.4); ✅ risposta del BE il 2026-11-24 (§4.5); ✅ letta dal DB il 2026-11-24 (§4.5-bis)
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
  - [ ] 16, il template: il verbo, e il trigger che distingue il seed dal verbo (§9)
    - [x] analisi (2026-11-24, §9)
    - [x] D-M **a** e D-N **a** (Tid, 2026-11-24)
    - [x] changeSet, pgTAP, guide; prova sullo scratch (2026-11-24, §9.4)
    - [x] apply e pgTAP come app: verdi (Tid, 2026-11-24)
    - [x] la doc auto-generata rigenerata (Tid, 2026-11-24)
    - [x] commit su `dev/db-tid` (2026-11-24)
    - [ ] il BE: i test Django che pubblicano (§9.5)
  - [ ] 10, lo scope emittenti: il verbo con `fn_guard_super_admin` (nessuna RLS) (§10)
    - [x] analisi (2026-11-24, §10)
    - [x] D-O **a**, D-P **a**, D-Q **a** (Tid, 2026-11-24)
    - [x] changeSet, pgTAP nuovo e ventiquattro adeguati, builder, guide e `manual/`; prova sullo scratch (2026-11-25, §10.5)
    - [x] apply e pgTAP come app: verdi (Tid, 2026-11-25)
    - [x] la doc auto-generata rigenerata (Tid, 2026-11-25)
    - [x] commit e push su `dev/db-tid` (2026-11-25)
    - [ ] il BE: i test che chiamano il verbo da SUPER_ADMIN, e il censimento di chi scrive la tabella (§10.6)
  - [ ] 9, la registrazione tardiva: da qui si prova il perimetro; prima si rilegge la D20-b di `brief-incassi-riconciliazione-rate-promemoria` (§11)
    - [x] analisi, D20-b riletta (2026-11-25, §11)
    - [x] D-S **a** (Tid, 2026-11-25)
    - [x] changeSet, pgTAP nuovo e quattro adeguati, guida e `manual/`; prova sullo scratch (2026-11-25, §11.5)
    - [x] apply e pgTAP come app: verdi (Tid, 2026-11-25)
    - [x] la doc auto-generata rigenerata (Tid, 2026-11-25)
    - [x] commit e push su `dev/db-tid` (2026-11-25)
    - [ ] il BE: i test che chiamano il verbo danno `registra_distinta` (§11.6)
  - [ ] 11, la bolla di riconsegna: il verbo col livello su `vendite.reso`, il perimetro del reso (§12)
    - [x] analisi, nessuna decisione nuova (2026-11-25, §12)
    - [x] changeSet, pgTAP nuovo, guide e `manual/`; prova sullo scratch (2026-11-25, §12.5)
    - [x] apply e pgTAP come app: verdi, con `20261124-12` (Tid, 2026-11-25)
    - [x] la doc auto-generata rigenerata (Tid, 2026-11-25)
    - [x] commit e push su `dev/db-tid` (`8f29eee1cb`, 2026-11-25)
    - [ ] il BE: i test che chiamano il verbo senza il livello (§12.6)
  - [ ] 8 + 1-7, un giro solo (D-T **b**, Tid, 2026-11-25): il fondo fattura (verbo pubblico e primitiva separati) e il reset del lotto (quattro verbi d'ingresso, tre primitive chiuse). Qui nasce `dbops.fn_pgtap_concedi_livello_area` (D-L a) e si ritirano le quattro copie (§13)
    - [x] analisi della parte 8, D10-D11 rilette (2026-11-25, §13.1-13.4)
    - [x] D-T **b**, D-U **a** (Tid, 2026-11-25, §13.3)
    - [x] analisi della parte 1-7, col passaggio senza azione (2026-11-25, §13.5-§13.8)
    - [x] D-W **a**, D-X **a**, D-Y **a**, D-Z **a** (Tid, 2026-11-25, §13.7)
    - [x] il via (Tid, 2026-11-25)
    - [x] changeSet, pgTAP, builder, guide e `manual/`; prova sullo scratch (2026-11-25, §13.9)
    - [x] apply e pgTAP come app: verdi (Tid, 2026-11-25)
    - [x] la doc auto-generata rigenerata, anche dopo le pagine `manual/` (Tid, 2026-11-25)
    - [x] commit e push su `dev/db-tid` (`e4bf00af69`, 2026-11-25)
    - [ ] il BE: i test della Parte C del giro
- [x] Giro 3 (2026-11-24, applicato da Tid con la fase `post` del provisioning, pgTAP verde; §7): le viste (§5): ~~prima i verbi delle scritture che il BE trova~~ (nessuna, §5.1), l'app con solo `SELECT` sulle viste,
  nelle tre sedi di `linee-guida-sql.md` §11.8, col pgTAP di postura a criterio e la guida dei permessi §7.4;
  il caso costruito passa dal criterio del loop, non da un `REVOKE` nel test (i privilegi di default danno il DML anche alle viste, §3-ter.4)
- [x] Il ritiro del task `reset_lotto_draft` (D-I, §4.8)
  - [x] analisi (2026-11-24)
  - [x] D-I.1 **a** e D-I.2 **a**, decise da Tid (2026-11-24)
  - [x] CSV, `DELETE` `20261123-67`, pgTAP del `rollback`, guide: scritto e provato sullo scratch (2026-11-24)
  - [x] apply su dbdev e pgTAP dell'invariante 9/9 (Tid, 2026-11-24)
  - [x] commit e push su `dev/db-tid` (2026-11-24)
  - [x] il BE: whitelist, handler, esclusione del runner, test e manuali (2026-11-24)
- [ ] Il rollback distruttivo non parte da solo (R-DB-I3, D-I.3 **a**, §4.8)
  - [x] scelte di Tid: decisione intera nella funzione, `auto_step_rollback` colonna (2026-11-24)
  - [x] `20261123-95`, `-96`, `-97`, i due CSV coi mirror, pgTAP, guide: scritto e provato sullo scratch (2026-11-24)
  - [x] apply su dbdev e pgTAP `test-rollback-step-automatico-v1` come app: verde (Tid, 2026-11-24)
  - [x] la doc auto-generata rigenerata (Tid, 2026-11-24)
  - [ ] il BE: il runner sulla funzione, i test, il manuale (passo 3n)
- [ ] R-DB-K1 e R-DB-K4 insieme (Tid, 2026-11-25): il verbo di primo impianto e il ritiro dei due seed di `tid` (§4.9)
  - [x] analisi, guide verificate (2026-11-25, §4.9)
  - [x] D-K7 **b** e D-K8 **a2** (Tid), il via (2026-11-25)
  - [x] changeSet, codice d'errore, pgTAP, guide e nota `_ultimo-super-admin`; prova sullo scratch (2026-11-25, §4.9.6)
  - [x] apply e pgTAP come app e su dbdev verdi (Tid, 2026-11-25)
  - [x] commit su `dev/db-tid` (2026-11-25)
  - [x] doc auto-generata rigenerata (Tid, 2026-11-25)
  - [ ] il BE: passo 3j, `genera_error_policies`, il censimento (§4.9.7)
- [ ] Giro 10-bis (D-O **a**, Tid, 2026-11-24): `config.user_emittenti_fiscali` in sola lettura per l'app, con
  `script.fn_crea_utente_tecnico` a verbo e R-DB-K2 (`fn_crea_operatore_v2`); parte dalla risposta del BE al
  censimento di §10.6
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

Fuori dal censimento, a ragione, anche le porte che passano da `script.fn_porta_manutenzione_aperta` (dal
2026-11-17): con la GUC accesa si aprono solo alla sessione del migratore, e lasciano una riga in
`dbops.porte_manutenzione_passaggi`. Per l'app restano chiuse. Sono i sei trigger del suo `COMMENT`, fra cui i
lucchetti di colonna (`script.trgfn_lock_columns`, `zeroerp.allow_lock_columns_override`). ⚠️ Riletto sul catalogo il
2026-11-24, dopo che `brief-db-revisione-anagrafiche` §20.6 li aveva dati per una porta da registrare qui: non lo è.

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

> ⚠️ La colonna «Azione che lo protegge» è corretta dalla risposta del BE (§4.5) e dalla sua lettura (§4.5-bis, 2026-11-24):
> per le porte 1-7, 11 e il secondo chiamante della 8 vale la tabella di §4.5-bis.

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

### 4.5-bis La risposta 3d letta dal DB — 2026-11-24

Letta sui BB del catalogo (doc auto-generata di `script`), non sugli YAML. Le regole 1 e 3 del gate BE il DB le ha già:
`script.fn_guard_azione` e `script.fn_guard_livello` decidono con le stesse funzioni del BE
(`fn_check_azione_processo`, `fn_resolve_livello_oggetto`), e tutte e due fanno passare il SUPER_ADMIN. La regola 2, il
superuser di Django, non c'è più: D-J **a** l'ha tolta dal BE (§4.7), quindi il verbo non la rifà.

**Il guard di ogni porta** (al posto della colonna «Azione che lo protegge» di §4.3):

| Porte | Verbo | Che cosa controlla l'endpoint (§4.5) | Il guard nel verbo |
| --- | --- | --- | --- |
| 16 | `fn_pubblica_template_documento_versione` | azione `documenti_template_manage` | `fn_guard_azione(…, 'documenti_template_manage')` |
| 10 | `fn_change_user_emittenti_scope` | SUPER_ADMIN | `fn_guard_super_admin` |
| 9 | `fn_posta_riga_tardiva` | azione `registra_distinta` | `fn_guard_azione(…, 'registra_distinta')`, più il perimetro |
| 11 | `fn_genera_ddt_riconsegna` | livello `TUTTO` sull'oggetto `vendite.reso`, con ricaduta sull'area | `fn_guard_livello(…, 'vendite', 'reso', 'TUTTO')`: è la stessa forma (oggetto, poi area). ⚠️ Non `conferma_reso`, come §4.3 diceva |
| 8 | `fn_cancella_fondo_fattura` | azione `governa_fondo_fattura` | `fn_guard_azione(…, 'governa_fondo_fattura')` sul verbo pubblico; la primitiva separata non ha guard |
| 8 | `fn_annulla_sistemazione` (chiama la primitiva) | livello `TUTTO` sull'**area** `pagamenti`, senza oggetto | ⚠️ **Nessun BB lo dice così**: `fn_guard_livello` vuole un oggetto e ricade sull'area solo se l'oggetto non ha un livello suo. Si decide nel giro 8 (punto 2 sotto) |
| 1-7 | `fn_elimina_fattura_da_lotto`, `fn_escludi_documento_da_giro` | azione `reset_lotto_fattura_draft` | `fn_guard_azione(…, 'reset_lotto_fattura_draft')` |
| 1-7 | `fn_annulla_lotto_da_draft`, `fn_riporta_lotto_a_draft` | il passaggio verso annullo o stato iniziale: l'azione della riga, oppure, se la riga non ha azione o non c'è, il livello `TUTTO` sull'area `vendite` | ⚠️ `fn_guard_passaggio` **non basta da solo**: con la riga senza azione passa («il permesso lo controlla il backend»), e senza riga sullo stato già raggiunto solleva `E_DOC_GIA_NELLO_STATO`. Si decide nel giro 1-7 (punto 3 sotto) |

`reset_lotto_draft` non è più un'azione del modello (spenta nel seed) e non è più un task (ritirato, D-I, §4.8): la
correzione del BE per le porte 1-7 è già consumata.

**La Parte B è chiusa.** Nessun processo automatico raggiunge uno dei dieci verbi: l'unico aggancio era il task
`reset_lotto_draft`, ritirato. L'utente tecnico di default non ha né azioni né livelli (`script.fn_crea_utente_tecnico`),
e nessun verbo dei giri gli serve. Se un giro aggiungesse una strada dai processi, il suo profilo entra in quel giro.

**La Parte C: con che cosa i test danno il permesso.** L'operatore di `dbops.fn_pgtap_crea_emittente_operatore` non ha
né azioni né aree (il contratto di `dbops.fn_pgtap_concedi_azione` lo dice): dopo il giro della sua porta ogni test della
Parte C riceve `E_PERMESSO_NEGATO`, come il BE prevede. I builder ci sono già, e il BE li usa:

* **azione** (porte 16, 9, 8, 1-7 per eliminazione ed esclusione): `dbops.fn_pgtap_concedi_azione(utente, codename)`,
  che apre anche l'area al minimo dell'azione. Il BE la chiama già (`vendite/tests/db/test_ddt_cambia_stato_db.py`,
  `test_offerta_cambia_stato_db.py`, uno smoke del magazzino). I sei file di `documenti` e quello di `pagamenti` la
  usano: è la risposta alla domanda del BE «se il DB offre un builder con un profilo»;
* **livello d'area** (porta 8 col secondo chiamante, porte 1-7 senza azione): lato BE c'è
  `core/tests/db_e2e.apri_operatore_con_aree`. Lato DB **nessun BB**: quattro pgTAP scrivono lo stesso helper
  `pg_temp.livello_area` (`catalogo/test-chiudi-legame-con-prezzi-v1`, `magazzino/test-verbi-anagrafiche-magazzino-v1`,
  `magazzino/test-lotto-dell-azienda-v1`, `magazzino/test-verbi-documenti-interni-v1`). È la regola del 2 già superata:
  **D-L** a Tid (sotto);
* **livello d'oggetto** (porta 11, `vendite.reso`): nessun builder, in nessuno dei due lati. Il test della porta 11
  costruisce l'override d'oggetto (`config.user_override_oggetti`) o usa il livello d'area, su cui l'oggetto ricade;
  si decide nel giro 11;
* **SUPER_ADMIN** (porta 10, e gli smoke): `dbops.fn_pgtap_crea_operatore_umano(…, true)` lato DB,
  `apri_contesto_operatore(cur, super_admin=True)` lato BE.

**Tre punti per i giri** (non aprono decisioni ora; ognuno si chiude nel giro della sua porta):

1. **D-L, il builder del livello d'area** (Tid). ⭐ Proposta: nel primo giro che ne ha bisogno (la 8, o la 1-7 se
   viene prima) nasce `dbops.fn_pgtap_concedi_livello_area(utente, area, livello)`, gemello di
   `fn_pgtap_concedi_azione`, e le quattro copie `pg_temp.livello_area` si ritirano nello stesso giro. Il BE resta sul
   suo `apri_operatore_con_aree`, che è l'altro lato e non una copia. In alternativa il debito resta, dichiarato.
   ✅ **Decisa da Tid il 2026-11-24: a.**
2. **Giro 8, il livello sull'area senza oggetto.** `fn_annulla_sistemazione` chiede `TUTTO` sull'area `pagamenti`. O
   il verbo usa `fn_resolve_livello_area` con un guard scritto sul posto (prima occorrenza), oppure si sceglie l'oggetto
   di `pagamenti` che la sistemazione rappresenta e si passa a `fn_guard_livello`. La seconda cambia ciò che il BE
   controlla oggi (l'override d'oggetto vincerebbe sull'area): va chiesta al BE nel giro.
3. **Giro 1-7, il passaggio senza azione.** Dove la riga del passaggio non ha azione, il BE ricade sul livello
   `TUTTO` dell'area `vendite`; `fn_guard_passaggio` invece passa. Il verbo DEFINER, che non ha più la RLS dietro, deve
   rifare anche la ricaduta: `fn_guard_passaggio` e poi, se la riga non ha azione, il livello. E `fn_riporta_lotto_a_draft`
   su un lotto già in bozza: il BE lo ammette col livello, `fn_guard_passaggio` risponde `E_DOC_GIA_NELLO_STATO`. Il
   giro legge il corpo del verbo e sceglie quale dei due è il comportamento voluto.

**Guide.** `architettura-permessi-e-autorizzazioni` (§7.4, le funzioni di risoluzione sono le stesse dei due lati)
**coerente**. Le guide di dominio delle porte si aggiornano nel giro di ognuna (piano, ultima voce).

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

**Il `None` del perimetro: si rifiuta, non apre — fatto il 2026-11-24 (ok Tid).** Dopo D-J `auth_user_id=None` non
era più «il superuser», ma il filtro di scope lo leggeva ancora come «nessuna restrizione»: un chiamante che
dimenticava l'argomento leggeva tutti gli emittenti senza errore. L'inventario (BE, 2026-11-24): a DB i `NULL` di
`p_auth_user_id` sono guard che sollevano, il punto aperto era solo nel BE. Un difetto vero: il tool AI di ricerca
contratti non passava l'utente (corretto, commit `dfa44930b`). Tre livelli:

1. **il tool AI** passa `get_scope_user_id(request)`, come il gemello dei preventivi; test
   `ai_assistant/tests/tools/test_ricerca_perimetro_emittente.py`;
2. **`None` solleva `E_SCOPE_SENZA_UTENTE`** in `fetch_emittenti_scope_ids`, la primitiva da cui passano tutte le
   strade (`add_emittente_scope_condition`, la coda stampa, l'archiviazione stampa, le rate dei pagamenti). Le tre
   che lo scavalcavano con un loro `if auth_user_id is not None` non lo fanno più. Test
   `core/tests/db/test_scope_senza_utente.py` e `vendite/tests/db/test_offerte_scope_emittente.py`, provati a
   rovescio (guard tolto: sei rossi; bypass delle rate rimesso: rosso);
3. **i metodi di lista di vendite perdono il default `None`** di `auth_user_id` (repository e service, una
   trentina di firme), come magazzino e pagamenti già facevano: chi lo dimentica riceve un `TypeError`, e mypy
   lo vede (`call-arg`). I test di repository che leggono la SQL di una lista dichiarano il perimetro col BB di test
   `core/tests/_helpers/perimetro_admin_globale_di_prova.py` (regola del 2, ok Tid 2026-11-24): il risolutore
   risponde «nessuna restrizione», come per l'admin globale, invece di passare `auth_user_id=None`.

⚠️ **L'unico `None` legittimo, dichiarato**: il motore documentale genera senza utente dal worker della coda stampa
(`genera_documento(None, …, emittente_scope=[…])`) e verifica il perimetro a monte (`guard_emittente_in_scope`).
`VenditeRepository.get_fattura_testata` tiene per quel caso un ramo locale che con `None` salta il filtro
applicativo; il builder della fattura ora gli inoltra l'utente, così dal web il filtro si somma al guard. L'ha
trovato mypy, togliendo il default. ✅ **Ritirato lo stesso giorno con D-K6 a** (sotto): il worker passa il suo utente
tecnico, e il ramo non c'è più.

⚠️ **Corretto dalla `/verifica` del 2026-11-24.** Tre letture della fattura tenevano ancora il default `None` sul
service (`get_fattura_dettaglio`, `get_fattura_giornale`, `list_fattura_righe_pagina`): passano da
`get_fattura_testata`, e chi dimenticava l'utente arrivava senza errore al ramo dichiarato, quello che salta il filtro
applicativo (resta la RLS). Le view passavano l'utente: nessun caso reale, una porta aperta per dimenticanza. Tolto il
default anche da `fn_lotti_mensile` e dalle due code dei resi (`list_da_accreditare`, `list_da_riconsegnare`), che con
`None` avrebbero già sollevato dal BB. Presidio sulle firme in `core/tests/db/test_scope_senza_utente.py` (6), provato a
rovescio (default rimesso su `get_fattura_dettaglio`: rosso). Restano col default i verbi del lotto (`numera_lotto`,
`ristampa_lotto`, `finestra_numerazione`): con `None` sollevano da `get_lotto`, e non sono letture di lista.

**Richiesta al team DB (R-DB-K3)**: `E_SCOPE_SENZA_UTENTE` nasce per il trigger `trgfn_guard_emittente_scope` (una
**scrittura** senza chi agisce). Dal 2026-11-24 il BE lo solleva anche per una **lettura** con perimetro senza
utente: la descrizione del catalogo va allargata ai due casi. Lo stesso significato, non un codice nuovo.

*La risposta del DB (2026-11-24).* Fatta nei due CSV del catalogo, caricati dal mirror `runOnChange` `20260614-08`:
nessun changeSet nuovo.

* **`codici_errore.csv`, la `note` di `E_SCOPE_SENZA_UTENTE`**: apre col significato comune («il perimetro emittente
  chiesto senza dire chi agisce: non si apre, si rifiuta») e nomina le due sedi, la scrittura del trigger e la lettura
  del BE (`fetch_emittenti_scope_ids`, dal 2026-11-24, con la storia del `None` che apriva). Classe invariata, `TECNICO`.
* **`messaggi_errore.csv`, causa e soluzione**: ognuna dice i due casi («In scrittura… In lettura…»). In lettura la
  soluzione è passare l'utente della richiesta (`get_scope_user_id`) o l'utente tecnico del worker, e il ⛔ dice che
  l'assenza non si risolve come «nessuna restrizione».
* ⚠️ **Il `messaggio` resta quello del trigger** («Scrittura su %s.%s senza un utente in sessione…»). È la frase di chi
  solleva il codice **dal database**, e l'unico è il trigger, che passa schema e tabella. Il BE solleva con la sua frase,
  senza segnaposto (`error_messages_fallback.py`, che già dice i due casi), e non mostra la frase del catalogo. Una
  frase chiusa per tutti e due toglierebbe al trigger la tabella dal messaggio (resterebbe nel contesto) e lo
  lascerebbe a passare due valori che nessun segnaposto usa: la regola «segnaposto e valori si contano» della guida
  `Messaggi-di-Errore-e-Generazione-Log` chiederebbe di riscrivere il trigger, montato su 24+ tabelle. Il presidio
  dell'arità non lo vedrebbe (il test 5 di `test-catalogo-messaggi-errore-completo` conta solo i valori in meno).
* **Trovato facendo il giro**: la `note` di `E_UI_CHIAMATA_NON_VALIDA` motivava la sua scelta con «non
  E_SCOPE_SENZA_UTENTE (copre solo la GUC vuota, e parla di scritture)». Dopo R-DB-K3 era falsa. Ora dice che
  `E_SCOPE_SENZA_UTENTE` è l'assenza di chi agisce sul perimetro emittente, in scrittura o in lettura, mentre lì il
  guasto è il contesto della lista.
* **Ricaduta sul BE (passo 3k-bis)**: `error_policies_generated.py` porta la `note` di ogni codice come commento, e
  `test_error_policies_divergenza_db.test_il_file_generato_e_allineato_al_catalogo` confronta il testo intero. Dopo
  l'apply è rosso finché il BE non rilancia `manage.py genera_error_policies`. Chi cambia per primo: il DB.
* ✅ Applicata da Tid il 2026-11-24, `test-catalogo-messaggi-errore-completo` verde.
* Guide: `architettura-permessi-e-autorizzazioni` (§6.3, già allineata dal BE) **coerente**;
  `Messaggi-di-Errore-e-Generazione-Log` **coerente** (la regola dei segnaposto vale per il `messaggio`, che non
  cambia); `manual/trgfn_guard_emittente_scope` descrive il trigger, **coerente**.

**Resta fuori, dichiarato**: `clienti_service._guard_can_create_ba` con `auth_user_id=None` **salta** il gate di
creazione del billing account («contesto di sistema, test fixture»). È la stessa forma, ma su un gate di scrittura
e non su un perimetro; la difesa finale è il trigger DB `trgfn_billing_account_guard_admin_globale`. Da decidere
in un giro a parte.

Della stessa forma, e dichiarato con lui (`/verifica` del 2026-11-24): il gate L2 dei prezzi
(`_pricing_gate_helpers.check_limite_variazione_prezzo` e `check_limite_variazione_globale`) con `auth_user_id=None`
ritorna senza controllare, perché L1 ha già deciso. Anche lui è un gate di scrittura, non un perimetro.

**Dalla `/verifica` del 2026-11-24, corretti** (nessun cambio di comportamento in esercizio):

* `pagamenti_repository` chiamava `fetch_emittenti_scope_ids` da una copia importata con `from … import`, che il BB di
  test `perimetro_admin_globale_di_prova` non raggiunge: il presidio delle liste interrogava davvero il DB con l'utente
  finto (verde per un'altra ragione). Ora la chiama dal modulo; presidio `NessunaCopiaDelRisolutoreTests` in
  `core/tests/db/test_scope_senza_utente.py`, provato a rovescio;
* commenti rimasti alla regola di prima: la «sede unica del rifiuto» del BB (i due metodi di `PermissionResolver`
  leggono le funzioni DB per conto loro), il «None = coda senza scope» di `pipeline_service.esiti_fatturazione`, il
  «filtro applicativo no-opa con `None`» dei fondi da decidere, il «`fn_check_user_emittente_scope` risponde true con
  NULL» delle rate (dalla Q-1 risponde FALSE), il «superuser bypass» del gate dei prezzi;
* il ripiego di `E_SCOPE_SENZA_UTENTE` in `error_messages_fallback.py` (BE) dice i due casi, scrittura e lettura, come
  chiede R-DB-K3 al catalogo;
* api.md e catalogo BB nominano le eccezioni dichiarate (`get_fattura_testata`, i verbi del lotto) e il limite del BB di
  test.

**Due decisioni dalla `/verifica` del 2026-11-24: ✅ decise da Tid, a e a, e fatte nel BE lo stesso giorno** (esito
sotto l'elenco).

* **D-K5, i due metodi del resolver.** `PermissionResolver.get_emittenti_sr_ids` / `get_emittenti_pk_ids` (circa 37
  chiamanti) chiamano le stesse funzioni DB di `fetch_emittenti_scope_ids`, con la loro cache. Non aprono il perimetro:
  con l'anonimo passano NULL e il DB risponde `'{}'`. Ma con `user=None` danno un `AttributeError`, cioè un 500 generico e
  non `E_SCOPE_SENZA_UTENTE`, e sono una seconda sede della stessa domanda. · **a** farli delegare al BB, tenendo la cache
  (cambio interno, nessuna firma pubblica, niente DB) · **b** lasciarli, con la sede doppia dichiarata (fatto: commento e
  catalogo). ⭐ **a**, per la regola del 2.
* **D-K6, il `None` del motore documentale.** Il drenatore della coda stampa (`stampa_coda_drainer_service`) chiama
  `genera_documento(None, …, emittente_scope=[…])` dentro `giro_per_azienda`, dove ha in mano l'utente tecnico del badge.
  Passandolo, il filtro applicativo di `get_fattura_testata` si sommerebbe anche nel worker e il ramo dichiarato
  `if auth_user_id is not None` sparirebbe, insieme al default `None` di `build_context` (base dei context builder e
  builder della fattura). · **a** passare l'utente tecnico (cambia il contratto del motore documentale, che oggi riceve un
  oggetto utente) · **b** tenere il `None` dichiarato. ⭐ **a**: un ramo senza filtro è una porta, anche quando oggi la
  attraversa solo il worker.

*Fatto nel BE (2026-11-24).*

* **D-K5**: `PermissionResolver.get_emittenti_sr_ids` / `get_emittenti_pk_ids` delegano a `fetch_emittenti_scope_ids`
  (`_emittenti_dal_bb`, chiamato dal modulo, così il patch del BB di test arriva anche lì). La cache della richiesta
  resta, con le chiavi di prima; un rifiuto non entra in cache. Un utente assente o anonimo è `E_SCOPE_SENZA_UTENTE`:
  prima l'anonimo passava NULL e il DB rispondeva chiuso, `user=None` era un 500. Chiuso era e chiuso resta. Nessun
  chiamante passa un anonimo per scelta (viste autenticate, `request.user`, worker con l'utente tecnico). Presidio:
  nessun sorgente fuori dal BB interroga le due funzioni DB (`core/tests/db/test_scope_senza_utente.py`, test 8),
  più quattro test del resolver; provati a rovescio.
* **D-K6**: il drenatore carica l'utente tecnico del badge (uno per badge; un badge senza utente è un'azienda fallita
  del giro) e lo passa a `genera_documento` insieme a `emittente_scope=[id]`. Il motore pretende l'utente su tutti e
  due i percorsi (`_resolve_scope_chiamante`): `user=None` è `E_DOCUMENTI_VALIDATION` anche col perimetro esplicito.
  `get_fattura_testata` non ha più il ramo che con `None` saltava il filtro. `build_context` non ha più il default
  `None`, sulla base e sui sei builder di vendite. Il contratto pubblico del motore non cambia firma: riceveva già un
  oggetto utente. ⚠️ Cambia un dato: `documenti_generati.generato_da_user_id` (e l'utente dell'evento) dei documenti
  del worker ora nomina l'utente tecnico, prima era NULL; e `_meta.auth_user_id` del contesto, quindi il
  `context_hash` dei documenti del worker. Test: motore (27-30 riscritti), drenatore (2 riscritto, 9-10 nuovi sul
  giro), presidi in `test_scope_senza_utente` (testata fattura con `None`, builder senza default); provati a
  rovescio. Il test DB dei contesti di stampa passa dal BB di test del perimetro.
* ✅ **«L'utente per id», estratto (regola del 2, ok Tid 2026-11-24).** Le sedi erano sette, non cinque: drenatore,
  gate dei prezzi ×2, approvazioni prezzo, componenti, preventivi, permessi effettivi/audit, più il comando di
  provisioning. Il BB `apps/core/services/utente_per_id.py` legge e risponde `None` (id `None`: nessuna query), e
  ogni chiamante tiene il suo rifiuto col codice del suo dominio: nessun codice d'errore nuovo, nessuna policy al DB.
  Ritirato `_pricing_gate_helpers._get_user_or_none`, copia esatta del BB. Test del BB e presidio di sede unica
  (`core/tests/services/test_utente_per_id.py`), provato a rovescio; i test che patchavano `get_user_model` nei moduli
  chiamanti ora patchano `utente_per_id`.

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

**R-DB-K4 — al team DB: il primo amministratore «di sviluppo» che c'è già** (`/verifica`, 2026-11-24, su domanda di
Tid: «non avevamo previsto un superadmin di default nei CSV?»). *I fatti*, letti dai changeSet: nessun CSV di seed porta
un utente, una veste o un binding SUPER_ADMIN, e nessuno è stato cancellato nella storia. Esistono invece due changeSet
della convenzione «tid = super-admin di dev»:

* `80_data/changelog/20260309-01-seed-auth-user-tid-risorsa-umana-emittente-mctit.yaml` lega `auth_user id=1` a una
  risorsa umana e all'emittente 32;
* `80_data/changelog/20260419-95-seed-operatore-tid-post-cutover-mctit.yaml` ricostruisce dopo il cutover l'intera
  catena per `auth_user id=1`: soggetto → risorsa umana → veste OPERATORE → binding SUPER_ADMIN → emittente 32.

Nessuno dei due crea la credenziale: presuppongono `createsuperuser`, e senza `auth_user id=1` (DB ricostruito da zero,
CI) vanno in MARK_RAN. Portano id cablati (emittente 32, tipo ruolo 14, qualifica 1, profilo 9100). D-K quindi non
revoca niente, ma non li nomina, e sul modello lasciano due cose aperte:

* **una seconda strada al SUPER_ADMIN.** Un'installazione su cui `createsuperuser` gira prima di `migrate` (o un DB
  ripristinato con un utente id 1) riceve da `20260419-95` un SUPER_ADMIN senza passare da `fn_crea_primo_amministratore`
  e senza la sua condizione «non esiste ancora un SUPER_ADMIN attivo». Che oggi l'ordine dei comandi lo eviti non conta:
  è un percorso che il modello ammette;
* **id fissi** su emittente, tipo ruolo e profilo, fuori dalla regola «mai id cablati» (lookup per codice).

*La richiesta.* Il DB decide fra due strade e lo scrive qui: (a) **ritirarli** dal primo impianto (contesto di sviluppo
esplicito, oppure precondizione che li spenga fuori da un DB di sviluppo), lasciando a R-DB-K1 l'unica strada; (b)
**tenerli**, dichiarandoli seed di sviluppo, e farli passare dal verbo di R-DB-K1 al posto degli `INSERT` diretti, coi
lookup per codice al posto degli id. Chi cambia per primo: il DB; il BE non ha niente da adeguare
(`provision_utenti_sviluppo` resta la strada di sviluppo lato BE, fuori da PRODUZIONE). ⚠️ Un changeSet già applicato non
si modifica: il ritiro o la sostituzione è un changeSet nuovo.

**Al team BE, dopo R-DB-K1** (passo 3j): un management command `crea_primo_amministratore`. Chiede i dati e la
password, calcola l'hash, chiama il verbo e traduce il rifiuto in un messaggio chiaro. Il playbook (§11) e
`configurazione-django.md` sostituiscono `createsuperuser` con il comando e tolgono la nota ⚠️ messa il 2026-11-24.
Il test: il comando chiama il verbo con l'hash, e il rifiuto «già presente» esce come messaggio, non come traceback.

### 4.8 Il ritiro del task `reset_lotto_draft` (D-I, passo 3g) — analisi del 2026-11-24

**La richiesta del BE** (2026-11-24, girata da Tid): il DB toglie per primo le righe del task, e le cancella anche
dal database, non solo dai CSV (§11.2). Poi, dopo il push e `/arrivi-db`, il BE toglie `ALLOWED_TASK_FUNCTIONS`,
l'handler e la sua voce, l'esclusione per nome di `pipeline_runner.py:521-524` e i test che li nominano. Restano fuori
dal giro: la GUC `zeroerp.maintenance_reset_lotto_draft`, che è la porta 1 e ha un nome quasi uguale; il commento di
`W_FONDO_FIGLIA_CONGELATA`; gli YAML storici.

**I fatti** (dbdev e repo, 2026-11-24):

* le quattro righe del task ci sono, tutte attive: `dbops.pipeline_task_registry` id 5,
  `pipeline_task_registry_impl` id 5 (`reset_lotto_draft_default`), `vendite.fatturazione_pipeline_task_policy`
  id 6 (`RESET_STEP`) e la voce nel `rollback` della pipeline 3;
* chiavi esterne: dall'implementazione al registro c'è una FK `NO ACTION`, quindi si cancella prima l'implementazione.
  Dalla policy alla pipeline c'è una FK, ma la pipeline resta. Fra le pipeline e il registro non c'è una FK: le pipeline
  nominano i task per nome dentro un JSON. Sul registro e sull'implementazione non ci sono trigger;
* `vendite.fatturazione_lotti_task_runs` ha zero corse di `reset_lotto_draft`. La colonna `task_code` è testo e non
  ha FK: un'installazione con corse vecchie le tiene come storia;
* nessuna funzione del DB nomina il task. Le occorrenze nei corpi sono tutte la GUC della porta 1. I quattro lettori
  del registro e della policy (`fn_check_pipeline_task_registered`, `fn_get_pipeline_task_implementation`,
  `fn_get_pipeline_task_policy`, `fn_resolve_lotto_task_execution_mode`) leggono per codice;
* tolta la policy 6, il valore `RESET_STEP` non lo usa più nessuna riga del seed. Il `CHECK` lo ammette ancora, e il
  pgTAP `test-fatturazione-pipeline-task-runtime` lo prova con una sua fixture: il valore resta nel vocabolario;
* l'azione `reset_lotto_draft` (`config.azioni_processo` id 6, spenta) non ha figlie su dbdev, né per id né per
  codice, in nessuna delle dodici tabelle che la puntano. Due pgTAP però la vogliono **presente e spenta**:
  `test-permessi-funzioni-risoluzione` test 30 e `test-fattura-lotto-al-modello-v1`, dal giro 11 di
  `brief-modello-documento-vendita` (Q-F1, 2026-10-27). Lì la riga spenta è la traccia della decisione;
* il presidio `test-pipeline-processi-invariante-v1` (test 6 e 7) verifica che ogni task nominato nei `processi` sia
  registrato e abbia la sua policy. Il `rollback` non lo guarda: se un `rollback` nominasse un task tolto dal registro,
  la migrazione passerebbe e il presidio resterebbe verde;
* il precedente `close_lotto` (2026-02-18) è stato **spento**, non cancellato, nel registro e nell'implementazione.

**Le guide** (`scripts/guide_coinvolte.py` sui quattro CSV e sulle quattro tabelle):

* [fatturazione](../../guide/fatturazione.md): **indietro**. Le righe 458, 548-560 e 637-639 danno il task come
  rollback di EMESSA. Il seed diventa `[]`. La demolizione che la guida descrive resta vera, ma la fa il verbo
  `fn_annulla_lotto_da_draft` dall'endpoint, non un task della pipeline;
* il manuale di `vendite.fatturazione_pipeline` (righe 105-110: la whitelist e «il reset tecnico in pipeline»):
  **indietro**;
* il manuale di `dbops.pipeline_task_registry`: va aggiunta una nota di migrazione;
* [analisi-tracciamento-processi-e-job](../../guide/analisi-tracciamento-processi-e-job.md),
  [gestione-pratiche](../../guide/gestione-pratiche.md), il manuale di `config.azioni_processo` e
  [modello-documento-di-vendita](../../guide/modello-documento-di-vendita.md) (l'azione ritirata): **coerenti**.

**Le due scelte di forma** (decide Tid):

* **D-I.1, il task: cancellato o spento?** · **a** si cancella, come chiede il BE · **b** si spegne, come `close_lotto`.
  ⭐ **a**. Lo spegnimento di `close_lotto` è servito a lasciare il task riaccendibile. D-I dice che questo task non
  ha più un ruolo, e il BE ne toglie l'handler. Una riga spenta che nomina un `handler_code` senza codice dietro
  sarebbe una registrazione falsa.
* **D-I.2, l'azione `reset_lotto_draft`: si toglie?** · **a** non si tocca · **b** si cancella, e i due pgTAP passano
  da «presente e spenta» ad «assente». ⭐ **a**. L'azione è già stata ritirata il 2026-10-27, con la decisione di un
  altro brief. La riga spenta è la traccia di quel ritiro, ed è fissata da due test. Il task e l'azione sono due cose,
  e D-I riguarda solo il task. La condizione «nessun binding la nomina» è verificata, ma da sola non basta per
  cancellarla.

**Che cosa si cambia, al via di Tid** (con D-I.1 **a** e D-I.2 **a**):

| File | Che cosa |
| --- | --- |
| `80_data/sql/vendite/fatturazione_pipeline.csv` | pipeline id 3: il `rollback` diventa `[]`, lo riallinea il mirror `runOnChange` |
| `80_data/sql/vendite/fatturazione_pipeline_task_policy.csv` | via la riga id 6 |
| `80_data/sql/dbops/pipeline_task_registry_impl.csv` | via la riga id 5 |
| `80_data/sql/dbops/pipeline_task_registry.csv` | via la riga id 5 |
| `80_data/changelog/<NN>-delete-task-reset-lotto-draft-mctit.yaml` (nuovo) | il `DELETE` forward-only di §11.2, idempotente, sulla chiave naturale (`task_code` / `handler_code` + `task_registry_id`): prima l'implementazione, poi il registro, poi la policy. Il numero lo dà `prossimo_changeset.py` al salvataggio |
| `db/pgtap/vendite/test-pipeline-processi-invariante-v1.sql` | test 8 e 9, lo specchio dei test 6 e 7 sul `rollback`: ogni task nominato nel `rollback` è registrato, attivo e ha la sua policy. Il controesempio è lo stato a metà: registro cancellato e `rollback` della pipeline 3 ancora pieno. Lì il test 8 è rosso |
| guida `fatturazione`, manuali `fatturazione_pipeline` e `pipeline_task_registry` | come sopra |

Ogni CSV si modifica per riga, e `git diff --numstat` lo conferma (§11.2). La prova si fa con `prova_changeset.py`:
il `DELETE` con in coda il pgTAP dell'invariante. Il `rollback` della pipeline 3 lo riscrive il mirror, che nella
prova non gira. Se lo script non lo simula, i test 8 e 9 si provano dopo l'apply di Tid.

**Dopo il push del DB, al BE**: l'elenco della sua richiesta, senza aggiunte. Il BE cambia dopo il DB: finché le
righe sono a DB, il codice del BE che le legge resta coerente.

**✅ Decise da Tid il 2026-11-24: D-I.1 a, D-I.2 a.** Scritto lo stesso giorno, come da tabella:

* i quattro CSV, una riga per file (`git diff --numstat`: 0/1, 0/1, 0/1 e 1/1 sul `rollback` della pipeline 3);
* `80_data/changelog/20261123-67-delete-task-reset-lotto-draft-mctit.yaml`, con una `preCondition` sulle tre tabelle;
* `test-pipeline-processi-invariante-v1`: piano 7 → 9, test 8 e 9 sul `rollback`. Corretto anche il commento dei
  test 1-2, che dava il `rollback` delle due corsie come «divergente apposta»;
* la guida `fatturazione` (le due corsie, il seed del rollback, l'annullo come verbo, i vincoli), i manuali di
  `fatturazione_pipeline` e `pipeline_task_registry` (nota di migrazione: cancellato, non spento come `close_lotto`),
  e quello di `azioni_processo`, che diceva «il task resta».

**La prova** (`prova_changeset.py`, scratch `zeroerp_ruoli` come owner, 2026-11-24):

* **il controesempio**, il solo `DELETE` con il `rollback` della pipeline 3 ancora pieno: invariante 9 ok → **7 ok, 2
  not ok** (i test 8 e 9). Il presidio nuovo vede lo stato a metà;
* **lo stato finale**, il `DELETE` e il mirror della pipeline 3 simulato da un changeSet di prova (`UPDATE … SET
  rollback = '[]'`): **9 ok, 0 not ok**. Catalogo identico prima e dopo;
* guardrail verdi: forme dei changeSet, `runOnChange`, letterali SQL, `preCondition` dei seed, preambolo pgTAP.

✅ Applicato su dbdev da Tid, `test-pipeline-processi-invariante-v1` verde 9/9 (2026-11-24); committato e pushato. Restano invariati
`test-permessi-funzioni-risoluzione` e `test-fattura-lotto-al-modello-v1`, perché l'azione non si tocca.

**Il lato BE: ✅ fatto il 2026-11-24, dopo `/arrivi-db`** (ok Tid, esclusione del runner tolta come proposto):

* `VenditePipelineRepository.ALLOWED_TASK_FUNCTIONS`: via la voce `reset_lotto_draft`;
* `PipelineStepExecutor`: via la voce `reset_lotto_draft_default` di `handler_registry` e l'handler
  `_handle_reset_lotto_draft_task`. Resta `annulla_lotto_da_draft` del repository, chiamato dall'endpoint
  `reset-draft` (il verbo dell'operatore), con il commento allineato;
* `LottoPipelineRunner._should_execute_auto_step_rollback`: via l'esclusione per nome. Il rollback automatico parte
  quando la pipeline ne ha uno;
* i test: il mock base del runner non ha più rollback, come il seed; il test 8 da «salta il rollback distruttivo» è
  diventato «senza rollback in pipeline non lo esegue», provato a rovescio (`return True` al posto della lettura:
  rosso); il commento del test 37 è allineato; via il test 9 dell'executor e la voce della mappa di prova;
* i manuali BE `api_pipeline_task` (catalogo dei task: rollback «nessuno») e `fn_reset_lotto_draft` (la funzione DB
  si chiama `fn_annulla_lotto_da_draft`, e non è più un task), e le due righe dell'indice di `vendite`.

Verdi: `test_pipeline_runner`, `test_pipeline_step_executor`, `test_reset_lotto_draft_api` e, sul DB vero,
`test_pipeline_task_handler_guardrail` (138 test). Gli handler scendono a 14, che è la soglia di
`test_la_misura_non_e_degradata`: verde, ma senza margine.

**D-I.3, il rollback distruttivo che verrà: ✅ decisa da Tid il 2026-11-24, strada a.**

*Il problema.* Una pipeline può avere un `rollback` per step. Con `meta.auto_step_rollback` acceso, al rilancio di
un lotto massivo in errore il runner lo esegue **da solo**. L'unico `rollback` del seed era `reset_lotto_draft`, che
annullava il lotto e ne cancellava le fatture, e il runner lo saltava per nome. Ritirato il task, il BE ha tolto anche
l'esclusione (§4.8, lato BE). Oggi nessuna pipeline ha un `rollback`, quindi non c'è un caso vivo. Il modello però
lo ammette: un task che cancella dati, messo domani in un `rollback`, girerebbe in automatico al primo rilancio, e
niente lo sa pericoloso. Il presidio dell'invariante (test 8-9) vede che il task esiste e ha la policy, non che cosa fa.

*Le due strade.* **a** la proprietà «distruttivo, mai in auto-run» la dichiara il DB, e il runner la legge;
**b** non si dichiara niente e basta il presidio dell'invariante. ✅ **a**: un guard per nome protegge solo il nome
che conosce, una proprietà dichiarata vale per ogni task che verrà.

**Richiesta al team DB (R-DB-I3).**

* **La proprietà**: un flag dichiarato «distruttivo, mai in esecuzione automatica», `NOT NULL` con default `false`.
  La sede la sceglie il DB e la scrive qui: sul task (`dbops.pipeline_task_registry`), se è la natura del task in
  ogni pipeline, oppure sulla policy (`vendite.fatturazione_pipeline_task_policy`), se dipende da dove il task gira;
* **la lettura**: una funzione che, dato lo step e la corsia (gli stessi argomenti con cui il BE legge il `rollback`
  dello step), dica se nel suo `rollback` c'è almeno un task distruttivo. Il BE non compone la query sulle tabelle;
* **il presidio**: il pgTAP dell'invariante (o uno suo vicino) prova la lettura, col controesempio di un task
  distruttivo messo in un `rollback`;
* **il seed**: oggi nessun task è distruttivo, perché nessuna pipeline ha un `rollback`. La colonna nasce con tutti
  `false`, e la guida `fatturazione` (§ rollback) e il manuale della tabella scelta dicono che cosa significa.

*Chi cambia per primo*: il DB. Fino al suo push il BE resta com'è oggi, senza esclusione, ed è coerente perché nessun
`rollback` esiste. **Dopo il push, al BE**: `LottoPipelineRunner._should_execute_auto_step_rollback` chiama la
funzione e non esegue in auto-run un `rollback` che contiene un task distruttivo. Il rollback resta eseguibile solo su
richiesta esplicita. Il test del runner va col caso distruttivo e con la controprova non distruttiva.

**D-I.4, da dove viene `auto_step_rollback`: ✅ decisa da Tid, a, e fatta nel BE** (`/verifica` del 2026-11-24). La guida `fatturazione` (§ rollback)
dice «se la pipeline ha `meta.auto_step_rollback = true`», e `vendite.fatturazione_pipeline` ha una colonna `meta`. Il
runner invece legge il flag **solo dal `meta` del body** della richiesta di run (`views._run_lotto_kwargs` →
`LottoPipelineParams.meta` → `run_pipeline`), e la colonna della pipeline non la legge nessuno. Il frontend non lo manda.
Oggi non fa danno, perché nessuna pipeline ha un `rollback`; con R-DB-I3 chi lo accende deciderebbe se un rollback parte da
solo. · **a** il runner legge il flag dalla pipeline (configurazione, come dice la guida) e il body non lo accende più ·
**b** resta del chiamante, e la guida si allinea al codice. ⭐ **a**: è una proprietà della corsia, non di una singola
richiesta, e va con R-DB-I3.

*Fatto nel BE (2026-11-24).* `VenditePipelineRepository.is_auto_step_rollback_attivo` legge `meta.auto_step_rollback`
dalla riga di `vendite.fatturazione_pipeline` dello step, risolta da `fn_resolve_fatturazione_pipeline_step` con gli
stessi argomenti del suo `rollback`: flag e lista vengono dalla stessa riga. Accende solo il booleano JSON `true`. Il
runner non legge più il flag dal body; il `meta` del body resta il `meta` del lotto. Prerequisito DB: nessuno, la
colonna c'è. Guida `fatturazione` (§ rollback): ora coerente, era il codice a essere indietro. Test: runner (7 e 37
col flag sulla pipeline, 8a nuovo: il body non accende), DB vero
(`vendite/tests/db/test_auto_step_rollback_dalla_pipeline_db.py`: binding, solo `true` accende, step sconosciuto
spento). Manuale `api_pipeline_task.md` aggiornato.

*Per R-DB-I3* (al team DB, insieme al flag «distruttivo»): oggi il patto è una chiave di un `jsonb` che il DB non
controlla. Un `"auto_step_rolback"` scritto storto spegne il rollback senza errore. Se il DB preferisce dichiararlo, la
scelta è sua, e la scrive qui: una colonna, un `CHECK` sul tipo, oppure lo stesso flag restituito dalla funzione di
R-DB-I3. Il BE si adegua nel passo 3n.

**La risposta del DB a R-DB-I3 (2026-11-24).** Le due forme le ha scelte Tid lo stesso giorno: la funzione dà la
**decisione intera**, e `auto_step_rollback` diventa una **colonna**.

* **La sede del flag: il task**, `dbops.pipeline_task_registry.distruttivo` (`boolean NOT NULL DEFAULT false`,
  `00_schema/dbops/20261123-95`). Che un task cancelli dati è la sua natura, la stessa in ogni pipeline che lo nomina; la
  policy dice come il task gira in una corsia (`annullabile`, `resume_mode`), e un task distruttivo in una corsia e innocuo
  in un'altra non esiste. Il seed nasce tutto `false` (CSV e mirror `20260208-07`).
* **Il patto della corsia: una colonna**, `vendite.fatturazione_pipeline.auto_step_rollback` (`boolean NOT NULL DEFAULT
  false`, `00_schema/vendite/20261123-96`). La chiave omonima del `meta`, dove c'è, passa nella colonna (accende solo il
  booleano JSON `true`, come la leggeva il BE) e lascia il `meta`. Poi `chk_fatturazione_pipeline_meta_senza_auto_step_rollback`
  la rifiuta: una sede sola, e un nome storto non spegne più niente in silenzio. CSV e mirror `20260128-06` con la colonna,
  tutta `f`. Nessun changeSet né pgTAP scriveva la chiave: il `CHECK` nasce valido anche da zero (§11.14).
* **La lettura: `vendite.fn_check_rollback_step_automatico(p_tipo_lotto, p_stato_doc_fiscale_id, p_utility_id,
  p_tipo_doc_fiscale_id)`** (`20_code/vendite/20261123-97`, `LANGUAGE sql BEGIN ATOMIC`, `STABLE`, `SECURITY INVOKER`,
  `GRANT` a `zeroerp_app`). Gli argomenti sono quelli di `fn_resolve_fatturazione_pipeline_step`, che risolve lo step
  (`p_rollback => true`): stessa precedenza e stessa riga da cui il runner legge la lista, e i suoi guard sui parametri
  (`E_PARAMETRO_INVALIDO`). Risponde `true` solo se la corsia accende il flag, il rollback ha almeno un task, e ogni task è
  registrato e attivo nel dominio `FATTURAZIONE` attivo e non è distruttivo. ⭐ Fail-closed: un task spento, sconosciuto o
  un elemento senza la chiave `task` danno `false` come un distruttivo. Step che non si risolve: `false`.
* **Il presidio: `db/pgtap/vendite/test-rollback-step-automatico-v1.sql`** (plan 14), coi casi **costruiti** (uno stato
  con la sua pipeline, tre task di prova): le due colonne, il `CHECK`, il controesempio del distruttivo, lo spento, lo
  sconosciuto, l'elemento senza `task`, un distruttivo nei `processi` che non chiude il rollback, lo step che non si
  risolve, il parametro invalido. Il seed non saprebbe produrne nessuno: nessuna pipeline ha un rollback.
* ✅ **Applicata da Tid il 2026-11-24**, pgTAP `test-rollback-step-automatico-v1` come app: verde.
* **Prova sullo scratch** (`prova_changeset.py`, owner, `ROLLBACK`): preCondition vere, estratto eseguito per intero,
  catalogo identico dopo. Il test nuovo 14/14 con l'estratto. Uguali prima e dopo: `test-pipeline-processi-invariante-v1`
  (9/9), `dbops/test-pipeline-task-registry` (10/10), `test-fatturazione-pipeline-fallback` (8/8),
  `dbops/test-comment-al-presente-v1` (8/8). Il caricatore dei due CSV non è provato: i CSV sono controllati campo per
  campo (9 e 15 campi su ogni riga, nessun `\r`).
* **Guide**: `fatturazione` (§ Rollback di step) era **indietro** (diceva `meta.auto_step_rollback`): ora dice la colonna,
  la funzione e il task distruttivo, con i due oggetti nel «Vedi anche». `analisi-tracciamento-processi-e-job` **coerente**
  (non tratta il rollback). Pagine `manual/` di `dbops.pipeline_task_registry` (la sezione del distruttivo, il test, la
  nota) e di `vendite.fatturazione_pipeline` (la colonna e il vincolo) aggiornate. La doc auto-generata si rigenera dopo
  l'apply.

**Garanzie ritirate.** Una sola, ed è voluta: **«la chiave `meta.auto_step_rollback` accende il rollback automatico»**.
Dopo l'apply la chiave non può più stare nel `meta`, quindi chi la legge legge sempre «spento». Lettori lato DB: nessuno
(né funzioni, né viste, né trigger, né job; nessun pgTAP la scrive). Lettori lato BE, da censire tutti dal team BE (il
censimento qui sotto viene da una ricerca del nome, non è un elenco chiuso): `VenditePipelineRepository.is_auto_step_rollback_attivo`
(`vendite/db/pipeline_repository.py`), il runner che lo chiama (`vendite/services/pipeline_runner.py`), i test
`vendite/tests/db/test_auto_step_rollback_dalla_pipeline_db.py` (scrive la chiave nel `meta`: dopo l'apply il `CHECK` lo
rifiuta, quindi è rosso) e `vendite/tests/services/test_pipeline_runner.py`, il manuale `api_pipeline_task.md`. Effetto in
esercizio fra l'apply e il passo 3n: nessuno, perché nessuna pipeline ha un rollback.

**Richiesta al team BE (passo 3n), dopo l'apply.** Chi cambia per primo: il DB.

* il runner (`LottoPipelineRunner._should_execute_auto_step_rollback`) chiede `vendite.fn_check_rollback_step_automatico`
  con gli stessi argomenti con cui legge il rollback dello step, e non legge più il flag per conto suo:
  `is_auto_step_rollback_attivo` si ritira, insieme alla lettura del `meta` (regola del 2: la regola sta in una sede);
* i test: il caso distruttivo e la controprova non distruttiva, il flag acceso dalla colonna e non dal `meta`; il test DB
  di D-I.4 passa alla colonna;
* il manuale `api_pipeline_task.md` (come parte il rollback automatico).

**Corretto dalla stessa `/verifica`**: il diario di un task di rollback fallito. La riscrittura best-effort della riga
ERRORE fuori transazione (`LottoPipelineRunner._persist_task_run_error_safely`) scriveva `meta = {"rollback": false}` fisso:
un rollback fallito, nella riga riscritta, diventava un passo in avanti. Era dormiente finché l'auto-rollback escludeva
l'unico rollback del seed. Ora l'executor mette il verso nelle coordinate dell'eccezione e il runner lo rilegge; due test,
provati a rovescio (`PersistTaskRunErrorVersoTests` del runner, `test_execute_step_fail_in_rollback_porta_il_verso`
dell'executor). Manuali BE: `api_pipeline_task` (registro a 20, come parte il rollback automatico),
`fn_reset_lotto_draft` (titolo e catena), indice di `vendite` rigenerato.

### 4.9 R-DB-K1 e R-DB-K4 insieme: il verbo di primo impianto e i due seed di `tid` — analisi del 2026-11-25

Si fanno insieme (Tid, 2026-11-25). Lettura in sola lettura sul catalogo di dbdev e sullo scratch, corpi da
`pg_get_functiondef`. Nessun changeSet scritto: si aspetta il via.

**Guide verificate** (`guide_coinvolte.py` sui due changeSet e su otto oggetti, 2026-11-25):

| Guida o nota | Esito |
| --- | --- |
| nota `anagrafiche/_ultimo-super-admin` | **coerente**, ed è la fonte della D-K7 qui sotto: «le scritture che migliorano la garanzia passano sempre… è così che si esce da un sistema scoperto», e §«Che cosa oggi non vede» elenca stati scoperti raggiungibili. **Indietro** col giro: non nomina il verbo di primo impianto fra le strade che fanno nascere un SUPER_ADMIN |
| [risorse-umane-e-accessi](../../guide/risorse-umane-e-accessi.md) | **indietro** col giro: §«Primo accesso e gestione credenziali» descrive solo l'invito, che presuppone un amministratore. Il primo amministratore di un'installazione nuova va scritto lì |
| [architettura-multi-face-auth](../../guide/architettura-multi-face-auth.md) | **coerente**: la veste OPERATORE nasce spenta (R-2); il verbo la accende nella stessa transazione, ed è un'eccezione da dichiarare nella guida, non una contraddizione: R-2 dice chi accende la veste di un operatore invitato |
| [architettura-permessi-e-autorizzazioni](../../guide/architettura-permessi-e-autorizzazioni.md) | **coerente**: il SUPER_ADMIN ha lo scope `NULL` (tutto) da `fn_get_emittenti_scope_pk_ids`, quindi il primo amministratore non ha bisogno di nessun emittente, e su un'installazione vuota non ce n'è nessuno. §7.4: il verbo è DEFINER **senza** guard di permesso, perché non c'è ancora nessuno che possa averlo: lo si dichiara come la sola eccezione, chiusa dalla sua condizione |
| altre dodici (soggetti, contatti, commesse, iva…) | nominano solo le tabelle (`soggetti`, `emittenti_fiscali`): il giro non ne cambia il comportamento |

Orfano: `config.fn_profilo_super_admin_id`, dettaglio interno di `fn_crea_risorsa_umana_v2`.

#### 4.9.1 Che cosa c'è oggi (catalogo di dbdev, 2026-11-25)

* `anagrafiche.fn_crea_operatore_v2` e `fn_crea_risorsa_umana_v2`: INVOKER. Il primo vuole email e qualifica
  (`p_qualifica_id` obbligatorio, attivo in `config.qualifiche`), nel flusso A crea il soggetto **PR** (persona fisica
  privata, sesso obbligatorio), riusa la credenziale dell'email **solo col consenso** (`p_riusa_auth_user_id`, altrimenti
  `E_CREDENZIALE_DA_CONFERMARE`), crea la veste OPERATORE **spenta** e, con `p_is_super_admin`, il legame al profilo
  scelto dal tipo (`config.fn_profilo_super_admin_id`: esattamente un profilo `SUPER_ADMIN` attivo, altrimenti
  `E_CONFIG_MANCANTE`). Ritorna `auth_user_id`, `username`, `credenziale_riusata`, **non** l'id della veste.
* `anagrafiche.fn_accendi_veste(p_identita_id, p_auth_user_id, p_vesti)`: INVOKER, accende se la veste è di quella
  credenziale.
* `script.fn_check_almeno_un_super_admin_attivo()`: la condizione è «esiste una veste **senza scadenza**»
  (`fn_identita_super_admin_senza_scadenza`: legame attivo a profilo `SUPER_ADMIN` attivo, veste OPERATORE utilizzabile
  oggi, nessuna data di fine su veste e rapporto, credenziale non bloccata).
* Sulle sei tabelle che il verbo scrive (`soggetti`, `soggetti_ruoli`, `risorse_umane`, `identita_digitali`,
  `profili_accesso_bindings`, `credenziali`) nessun trigger legge una GUC `zeroerp.*` o chiede
  `fn_is_proprietario_tabella`: il verbo DEFINER non ha GUC da spegnere (memoria della D-V1, §5.8 del brief archiviato).
* In `script` e `dbops` nessuna funzione usa `pg_advisory_xact_lock`: non c'è un BB di serializzazione da riusare.
* La qualifica `AMMINISTRATORE` è nel seed di catalogo (`80_data/sql/config/qualifiche.csv`, `codice_interno`).

#### 4.9.2 R-DB-K1, il verbo — che cosa si propone

`anagrafiche.fn_crea_primo_amministratore(p_cognome, p_nome, p_codice_fiscale, p_sesso, p_email, p_username,
p_password_hash, p_data_nascita DEFAULT NULL, p_comune_nascita_id DEFAULT NULL, p_riusa_auth_user_id DEFAULT NULL)`
→ `TABLE(auth_user_id, username, credenziale_riusata)`, i tipi con `%TYPE` dove c'è una colonna. `SECURITY DEFINER`,
`SET search_path = pg_catalog, public, pg_temp` come i verbi dei giri 9-11, `EXECUTE` a `zeroerp_app` (il comando del BE
gira come app, §6.5).

1. **Serializza** con `LOCK TABLE config.profili_accesso_bindings IN SHARE ROW EXCLUSIVE MODE`. Il modo è in conflitto
   con se stesso e con ogni `INSERT`/`UPDATE` della tabella: si serializza «nasce un legame», da qualunque strada
   arrivi, non solo due chiamate del verbo fra loro (un advisory lock fermerebbe solo quelle; la strada di
   `fn_crea_operatore_v2` resta aperta finché R-DB-K2 non la chiude). Il blocco dura una transazione sola, una volta
   per installazione.
2. **La condizione** (D-K7): se non è vera, `E_PRIMO_AMMINISTRATORE_GIA_PRESENTE` (NON_PERMESSO, ripiego senza `%s`).
3. **La qualifica** per `codice_interno = 'AMMINISTRATORE'`, non per id; mancante o spenta: `E_CODICE`, come il PR in
   `fn_crea_operatore_v2`. L'unità organizzativa resta `NULL` (facoltativa).
4. `fn_crea_operatore_v2(…, p_is_super_admin => true, p_riusa_auth_user_id => p_riusa_auth_user_id)`: il consenso al
   riuso passa così com'è. Serve: chi ha seguito il playbook vecchio ha già una credenziale da `createsuperuser` con
   quell'email.
5. La veste: `SELECT id … WHERE auth_user_id = … AND ruolo_applicativo = 'OPERATORE'` (una sola: il verbo madre rifiuta
   una credenziale già operatore), poi `fn_accendi_veste(id, auth_user_id, ARRAY['OPERATORE'])`.
6. ⚠️ Superato dal giro scritto (§4.9.6): la postcondizione non entra nel verbo, la prova il pgTAP. ~~**Postcondizione fail-loud**: se dopo `fn_check_almeno_un_super_admin_attivo()` non è vera, errore e `ROLLBACK`
   implicito. È la promessa del D-K «o l'amministratore entra, o non nasce niente», scritta come controllo e non come
   speranza (una `fn_data_operativa` diversa dalla data del server, una veste non utilizzabile per un motivo nuovo).~~
7. Nessun guard di permesso in prima riga: non c'è ancora nessuno che possa averlo. Il posto del guard lo prende la
   condizione, e la guida dei permessi §7.4 lo dichiara.
8. L'audit: dentro il DEFINER, senza `app.jwt_user`, `user_insert` è il proprietario. È il vero: nessuna persona è
   autenticata.

#### 4.9.3 D-K7, la condizione che apre il verbo — a Tid

Il verbo è eseguibile dall'app, quindi da qualunque strada del backend, anche sbagliata. La condizione è l'unica cosa
che lo chiude. La richiesta del BE diceva «un SUPER_ADMIN spento o scaduto non conta come presente», da confermare dal
DB. Sul modello non regge da sola: la nota `_ultimo-super-admin` elenca stati scoperti che si raggiungono senza che
nessun guard parli (la veste dell'ultimo amministratore spostata su una credenziale bloccata, il profilo che cambia
tipo, la cancellazione del rapporto dalla porta di manutenzione). Con la condizione «nessuno senza scadenza», in quegli
stati l'app può far nascere un SUPER_ADMIN nuovo, con dati scelti da lei. E il sistema scoperto ha già la sua uscita, che
passa dal proprietario: le scritture che migliorano la garanzia passano sempre.

✅ **D-K7 decisa da Tid il 2026-11-25: b.**

**D-K7**: **a** si apre se `fn_check_almeno_un_super_admin_attivo()` è falso (la richiesta del BE: si riapre su un
sistema scoperto, e diventa anche una strada di recupero aperta all'app) · **b** si apre solo se **nessuna veste ha un
legame `SUPER_ADMIN`, acceso o spento**: è l'installazione nuova, e si chiude alla nascita del primo legame. Il
recupero di un sistema scoperto resta del proprietario, con le scritture che migliorano la garanzia. ⭐ **b**: è il
«si chiude da sola alla nascita del primo» del D-K preso alla lettera. E non lascia all'app una porta che si riapre
quando la garanzia si rompe, che è proprio il momento in cui non la si vuole aperta. ⚠️ Con **b** un legame si può
ancora cancellare quando non è l'ultimo senza scadenza: cancellando tutti i legami di amministratori che scadono si
torna a «nessun legame». È un caso costruito, che chiede di cancellare righe a cui l'app oggi arriva solo da
SUPER_ADMIN: lo si scrive nel pgTAP come limite dichiarato, non si chiude qui.

#### 4.9.4 R-DB-K4, i due seed di `tid` — i fatti e la proposta

*I fatti* (2026-11-25):

* su **dbdev** tutti e due sono `MARK_RAN` (2026-03-09 e 2026-04-19): il SUPER_ADMIN di sviluppo di dbdev non è nato da
  loro;
* sullo **scratch**, costruito da zero, `20260419-95` è `MARK_RAN` e `20260309-01` **non è nel `databasechangelog`**.
  La sua `preCondition` legge `anagrafiche.risorse_umane_auth_user`, che da zero non esiste quando gira `80_data` (le
  fasi vanno in ordine, §11.14, e la tabella è stata ritirata). Con `failOnError: false` l'errore si perde, e il
  changeSet si ritenta a ogni `update`;
* il commento di `80_data/changelog/20260127-57` (2026-09-02) li nomina già fra i seed di macchina «da trattare, e per
  quelli il contesto serve davvero», insieme a `20260819-05` e `20260831-03`. Nessuno dei quattro ha il `context`;
* **il controesempio, sul modello**: su un database con `auth_user id = 1` e senza una sua veste OPERATORE,
  `20260419-95` cerca «l'ultima risorsa umana attiva senza veste attiva» e, se la trova, ci appoggia la veste di `id = 1`
  col legame al profilo `9100`. Su un'installazione popolata vuol dire dare il SUPER_ADMIN a una credenziale qualunque,
  **sul soggetto di un altro dipendente**, senza la condizione di R-DB-K1. A questo si aggiungono gli id cablati
  (emittente 32, tipo ruolo 14, qualifica 1, profilo 9100) e il legame all'emittente 32, che a un SUPER_ADMIN non serve
  (lo scope è `NULL`).

*Le strade.* La (b) della richiesta, «tenerli e farli passare dal verbo», non si può fare senza riscrivere un changeSet
applicato, e non serve: la strada di sviluppo c'è già, è `provision_utenti_sviluppo` del BE, fuori da PRODUZIONE. Resta
la (a), il ritiro, in due forme:

✅ **D-K8 decisa da Tid il 2026-11-25: a2.**

**D-K8**: **a1** `context: dati_macchina` sui due file: è la forma prevista da §11.7 e scritta nel file del
2026-09-02, il `context` non entra nel checksum. Però filtra solo dove l'invocazione dice `!dati_macchina` (la CI sì,
la produzione «solo se la riga c'è»), e tocca due file pushati · **a2** si tolgono i due file dal changelog: sui
database che li hanno, la riga del `databasechangelog` resta e non dà fastidio; su un database nuovo non esistono più.
Chiude la strada ovunque, senza dipendere dalla riga di comando, ma è un'eccezione a «mai modificare un changelog
pushato» (§11) · **a3** un changeSet nuovo non basta: i due vecchi girerebbero comunque prima di lui su un database
nuovo. ⭐ **a2**: è l'unica che chiude la strada del controesempio su ogni installazione. Il divieto di §11 protegge la
catena dei checksum, e un file tolto non la rompe: lo si dichiara come eccezione, col motivo. Se Tid preferisce restare
dentro la regola alla lettera, **a1**, sapendo che in produzione il filtro dipende dalla riga di comando.

⚠️ Vicini, fuori da questo giro: `20260819-05` e `20260831-03` (l'intestazione dei registri) sono della stessa lista
del 2026-09-02 e sono ancora senza `context`. Il loro guard *fail-loud* sull'emittente li rende innocui su un database
vuoto. Decide Tid se trattarli con la stessa D-K8 o lasciarli.

#### 4.9.5 Il pgTAP e le altre sedi, quando arriva il via

* **pgTAP nuovo** `anagrafiche/test-crea-primo-amministratore-v1`. ⚠️ Per costruire «nessun SUPER_ADMIN» bisogna
  ridurre la garanzia, e i guard dell'ultimo SUPER_ADMIN lo rifiutano. Il test gira quindi col runner owner e tiene
  spenti i quattro guard nella sua transazione, oppure usa la porta di manutenzione: la forma si sceglie dall'indice dei
  pattern pgTAP prima di scrivere, e la chiamata al verbo avviene come app (`SET LOCAL ROLE zeroerp_app`). Casi: sul
  sistema vuoto nasce il primo (veste accesa, `fn_is_super_admin` vero, soggetto PR, qualifica `AMMINISTRATORE`, nessun
  emittente); la seconda chiamata è rifiutata; con un SUPER_ADMIN presente è rifiutata e non nasce nessuna riga; il caso
  della D-K7 (solo legami spenti: **a** crea, **b** rifiuta); l'email con una credenziale senza consenso:
  `E_CREDENZIALE_DA_CONFERMARE` e nessuna riga; postura (DEFINER, `EXECUTE` all'app). La concorrenza non si prova in
  una sessione sola: la presidia il lock, ed è dichiarato.
* **Catalogo errori**: `E_PRIMO_AMMINISTRATORE_GIA_PRESENTE` in `80_data/sql/config/messaggi_errore.csv`, con un
  ripiego senza `%s`.
* **Al BE, dopo l'apply**: il passo 3j (il comando, il playbook, `configurazione-django.md`), più
  `manage.py genera_error_policies` per il codice nuovo, come il 3k-bis.
* **Guide**: `risorse-umane-e-accessi` (il primo amministratore), la nota `_ultimo-super-admin` (la strada che fa
  nascere il primo), `architettura-permessi-e-autorizzazioni` §7.4 (il verbo senza guard, chiuso dalla condizione).

#### 4.9.6 Il giro scritto — 2026-11-25

D-K7 **b** e D-K8 **a2** (Tid), poi il via. Numeri `20261125-30` … `-32` e id `1539` dei messaggi, assegnati da Tid.

**La prova del punto 1** (scratch, in `ROLLBACK`, prima di scrivere): i passi del verbo fatti a mano da proprietario
sul sistema vuoto danno un amministratore che entra (veste accesa, `fn_is_super_admin`, perimetro `NULL`,
`fn_check_almeno_un_super_admin_attivo` vero). Il vuoto si costruisce: lo scratch, costruito da zero, ha **zero**
legami SUPER_ADMIN, mentre su dbdev ci sono. Da proprietario, col guard dei legami spento nella transazione, si
cancellano; acceso, il guard rifiuta. Due fatti che hanno cambiato la forma:

* il soggetto PR pretende **residenza e domicilio fiscale** (`E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO`) e un
  contatto, con guard **differiti** al `COMMIT`. `fn_crea_operatore_v2` riceve gli indirizzi solo come id di dettaglio,
  che il comando di un'installazione vuota non ha. Il verbo riceve quindi `p_indirizzo_residenza jsonb` (e
  `p_indirizzo_domicilio_fiscale`, facoltativo) nella forma di `fn_crea_indirizzo_soggetto`;
* «il domicilio fiscale che manca è la residenza» era già nel passo 4 di `fn_crea_operatore_v2`: la seconda copia si
  **estrae** (regola del 2) in `anagrafiche.fn_crea_indirizzi_operatore`, e la madre la chiama.

**Due scostamenti da §4.9.2, dichiarati:**

* la classe di `E_PRIMO_AMMINISTRATORE_GIA_PRESENTE` è **CONFLITTO_STATO** (409), non NON_PERMESSO: il rifiuto dipende
  da com'è il sistema, non da un diritto che manca (la guida dei messaggi, §classi), gemello di
  `E_CREDENZIALE_GIA_OPERATORE`;
* la postcondizione del punto 6 non entra: per sollevarla serviva un secondo codice nuovo, TECNICO, che il catalogo non
  ha in forma generica, e un id non assegnato. La garanzia «il primo amministratore entra» la prova il pgTAP (test 6-9)
  sulla composizione vera.

| File | Che cosa |
| --- | --- |
| `20_code/anagrafiche/20261125-30-create-fn-crea-indirizzi-operatore` | il BB: residenza e domicilio fiscale in jsonb, senza tipo (il tipo nell'oggetto è `E_SCRIPT_CHIAMATA_NON_VALIDA`), senza residenza niente |
| `20_code/anagrafiche/20261125-31-update-fn-crea-operatore-v2-indirizzi-dal-bb` | il passo 4 dal BB. Corpo dal catalogo, firma ancorata come in `20261101-11`, attributi invariati (INVOKER, VOLATILE, COST 100); il `COMMENT` riscritto al presente; rollback = il corpo vivo |
| `20_code/anagrafiche/20261125-32-create-fn-crea-primo-amministratore` | il verbo: DEFINER, `search_path`, il lock dei legami, la condizione D-K7 b, la qualifica per codice, la madre, il BB, la veste accesa. `EXECUTE` all'app dal loop dei grant |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | `E_PRIMO_AMMINISTRATORE_GIA_PRESENTE`, CONFLITTO_STATO, id 1539, senza segnaposto. Li ricarica il mirror `runOnChange` |
| `80_data/changelog/20260309-01-…`, `20260419-95-…` | **tolti** (D-K8 a2). Il master li prende con `includeAll`: nessuna riga da togliere; nessuno script o pgTAP li nomina. Eccezione dichiarata a «mai modificare un changelog pushato»: la catena dei checksum non si rompe, le righe del `databasechangelog` restano dove ci sono |
| `db/pgtap/anagrafiche/test-crea-primo-amministratore-v1` | nuovo, runner owner (i guard dell'ultimo SUPER_ADMIN si spengono con `DISABLE TRIGGER`; il verbo è DEFINER, quindi dal runner owner si prova lo stesso corpo; l'`EXECUTE` dell'app lo asserisce il test 2). Piano 18 |
| `db/pgtap/dbops/test-character-n-v1` | il verbo nel registro delle funzioni: `p_sesso` ancora `anagrafiche.soggetti.sesso%TYPE`, una colonna del registro, come `fn_crea_operatore_v2` |
| `manual/` | `fn_crea_primo_amministratore`, `fn_crea_indirizzi_operatore` (nuove), `fn_crea_operatore_v2` |
| guide | `risorse-umane-e-accessi` (§«Il primo amministratore di un'installazione nuova», header), `architettura-permessi-e-autorizzazioni` §7.4 (il verbo senza guard, header), `architettura-multi-face-auth` (la veste accesa del primo), nota `_ultimo-super-admin` (§«Il primo amministratore») |

**Prova sullo scratch** (`prova_changeset.py`, da owner; le due righe del catalogo errori da uno YAML usa-e-getta
fuori dal repo, perché la prova non legge i CSV): il pgTAP nuovo 18/18 con l'estratto (senza: interrotto, il verbo
non c'è); `test-character-n-v1` 8/8 con (senza: 7/8, il registro nomina una funzione che non c'è ancora: atteso fino
all'apply); invariati gli undici pgTAP che chiamano `fn_crea_operatore_v2` (cinque passano gli indirizzi, quindi
passano dal BB) e i presidi trasversali (catalogo messaggi, codici nei corpi, `search_path` delle DEFINER, DEFINER
dichiarate, rubinetto del primo motivo). Catalogo identico dopo il `ROLLBACK`. Guardrail verdi (forme, `COMMENT` al
presente, letterali, runOnChange, preambolo pgTAP).

✅ **Applicato da Tid il 2026-11-25, pgTAP verdi**, compreso `test-crea-primo-amministratore-v1` su dbdev: il ramo che
cancella legami SUPER_ADMIN **veri** (lo scratch non ne ha) è provato. Doc auto-generata rigenerata.

#### 4.9.7 La richiesta al team BE/FE (dopo l'apply)

Chi cambia per primo: il DB. Il BE non ha niente da adeguare finché il verbo non è applicato.

* **Passo 3j**: il comando `crea_primo_amministratore`. Chiede cognome, nome, codice fiscale, sesso, email, username,
  password e la **residenza** (un indirizzo libero con stato, comune e CAP, o una via da risolvere, nella forma di
  `fn_crea_indirizzo_soggetto` senza il tipo); il domicilio fiscale facoltativo (se manca è la residenza: il comando
  non lo ricopia). Calcola l'hash Django e chiama `anagrafiche.fn_crea_primo_amministratore` con una sola `SELECT * FROM`.
  Traduce `E_PRIMO_AMMINISTRATORE_GIA_PRESENTE` in un messaggio («il primo amministratore esiste già»), e
  `E_CREDENZIALE_DA_CONFERMARE` in una domanda di conferma che richiama il verbo con `p_riusa_auth_user_id` (chi ha
  seguito il playbook vecchio ha già una credenziale da `createsuperuser` con quell'email). Il playbook e
  `configurazione-django.md` sostituiscono `createsuperuser` col comando. Il test: il comando chiama il verbo con
  l'hash, e i due rifiuti escono come messaggio, non come traceback.
* **`manage.py genera_error_policies`**: il codice nuovo è nel catalogo, e
  `test_il_file_generato_e_allineato_al_catalogo` è rosso fino alla rigenerazione.
* **Censisci i lettori di `fn_crea_operatore_v2`** che contano sul suo `COMMENT` o sulla sua firma: la firma non cambia,
  il comportamento neanche (gli indirizzi passano da un BB, con la stessa regola). Atteso: «nessuno».

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

## 9. Il giro 16, la pubblicazione del template — analisi del 2026-11-24

### 9.1 Che cosa c'è oggi (catalogo di dbdev, doc auto-generata del 2026-11-16 e 2026-11-17, dopo l'ultimo changeSet)

* **Il verbo**, `documenti.fn_pubblica_template_documento_versione`, è `INVOKER`, senza guard del permesso (lo tiene
  l'endpoint: azione `documenti_template_manage`, §4.5). Apre la porta con `set_config(…, 'on', true)` per le sue due
  scritture (la chiusura delle versioni precedenti, la pubblicazione) e la richiude, anche in errore.
* **Il trigger**, `documenti.trgfn_template_documenti_versioni_protect_pubblicata`, apre con la **GUC accesa**
  (`'on'`, tutte le righe) **oppure** col proprietario (`fn_is_proprietario_tabella`, l'eccezione del seed). Per l'app
  quindi la sola GUC: accesa da sé, un `UPDATE` diretto porta una bozza a `PUBBLICATA`, o chiude a `OBSOLETA` una
  pubblicata di un altro modello. È la porta 16.
* **Chi scrive la tabella**: il verbo; `documenti.fn_crea_bozza_da_versione` (nasce in `BOZZA`, la porta non serve); il
  backend sulle bozze (stato `BOZZA`, la porta non serve). La tabella non ha RLS: il giro non ha perimetro da rimettere.
* **Il migrate chiama il verbo**: dodici changeSet di `80_data` pubblicano template standard con
  `fn_pubblica_template_documento_versione`, in una sessione senza utente applicativo.
* **I pgTAP**: quindici lo nominano. Undici lo chiamano **come app** e nessuno dà `documenti_template_manage` al suo
  operatore; quattro girano da proprietario (`pgtap-runner: owner`).

### 9.2 Che cosa si cambia

1. **Il verbo diventa `SECURITY DEFINER`** (`SET search_path TO 'pg_catalog', 'public', 'pg_temp'`, come i verbi di
   magazzino), con in prima riga l'utente di sessione (`script.fn_utente_di_sessione`) e
   `script.fn_guard_azione(v_utente, 'documenti_template_manage')`: la stessa azione dell'endpoint, quindi nessun rifiuto
   nuovo per chi arriva dal backend (SUPER_ADMIN passa, regola 1). Firma e `RETURNS TABLE` si ri-ancorano con `%TYPE`
   (la doc li mostra sciolti): `CREATE OR REPLACE`, la firma non cambia.
2. **La GUC sulla riga**: il verbo la scrive con l'id del modello (`v_template_id`), non `'on'`, e la svuota all'uscita e
   in errore. Il trigger apre solo se la GUC vale `NEW.template_documento_id` **e** chi scrive è il proprietario: dentro
   il verbo DEFINER sì, per l'app mai, anche con la GUC accesa.
3. **Il seed si distingue dal verbo**: il ramo «il proprietario scrive lo stato senza porta» (regole 1 e 2) passa da
   `fn_is_proprietario_tabella` (`current_user`, che dentro il verbo DEFINER è il proprietario) a
   `dbops.fn_sessione_del_migratore()` (`session_user`: il migrate, non un verbo chiamato dall'app). È il BB delle porte
   di manutenzione e del seed di primo impianto. L'immutabilità fuori bozza vale per tutti, come oggi.
4. **I pgTAP**: uno nuovo, come app, coi controesempi (GUC accesa dall'app col valore giusto e `UPDATE` diretto: si
   ferma; il verbo senza l'azione: `E_PERMESSO_NEGATO`; con l'azione: pubblica; la GUC vuota dopo il verbo). Negli
   undici che lo chiamano come app, `dbops.fn_pgtap_concedi_azione(…, 'documenti_template_manage')` sull'operatore del
   contesto, col motivo. I quattro da proprietario non cambiano (sessione del migratore).
5. **Le guide**: `documenti-e-stampe` (chi pubblica, il permesso nel verbo); il trigger è **orfano** (nessuna guida lo
   nomina): entra nel suo «Vedi anche». `architettura-permessi-e-autorizzazioni` §7.4, la porta 16 fra quelle chiuse.
6. **La richiesta al BE**: i test della Parte C di `documenti` e `core/tests/db/test_date_validita_guard_comune_db.py`
   danno l'azione con `dbops.fn_pgtap_concedi_azione` (§4.5-bis); nessuna firma cambia, nessuna GUC da togliere.

### 9.3 Due scelte per Tid

* **D-M, il migrate pubblica senza il guard del permesso.** I dodici changeSet di `80_data` chiamano il verbo in una
  sessione senza utente: `fn_guard_azione` li fermerebbe (fail-closed), e un database ricostruito da zero non
  nascerebbe. **a** il guard si salta quando la sessione è del migratore (`dbops.fn_sessione_del_migratore`): il migrate
  è il software che pubblica uno standard, come per il trigger e le porte di manutenzione · **b** i changeSet futuri
  pubblicano dal seed senza il verbo, e i dodici vecchi restano col verbo (non si modificano): non regge, i vecchi
  rigirano da zero. ⭐ **a**: la sessione del migratore è già la definizione di «il software» nel database, e un
  `SET ROLE` non la finge (limite dichiarato del BB). ✅ **Decisa da Tid il 2026-11-24: a.**
* **D-N, il valore della GUC sulla riga.** La pubblicazione scrive più righe: la versione nuova e le precedenti che
  chiude, tutte dello stesso modello. **a** la GUC vale l'id del modello (`template_documento_id`): apre le righe di quel
  modello e nessun altro · **b** l'id della versione pubblicata: la chiusura delle precedenti chiederebbe un'altra
  chiave. ⭐ **a**: l'operazione è «la pubblicazione del modello X», e il trigger la confronta con una colonna della
  riga, senza leggere altro. ✅ **Decisa da Tid il 2026-11-24: a.**

### 9.4 Il giro scritto — 2026-11-24

| File | Che cosa |
| --- | --- |
| `20_code/documenti/20261123-98-update-protect-pubblicata-porta-sulla-riga-e-proprietario` | il trigger: la porta chiede la GUC uguale a `NEW.template_documento_id` **e** `fn_is_proprietario_tabella`; i due rami del seed (regole 1 e 2) passano a `dbops.fn_sessione_del_migratore()`; l'immutabilità invariata; `COMMENT`. Montaggio invariato, resta INVOKER |
| `20_code/documenti/20261123-99-update-fn-pubblica-template-documento-versione-definer-guard` | il verbo: `SECURITY DEFINER`, `search_path` `pg_catalog, public, pg_temp`; fuori dalla sessione del migratore `fn_utente_di_sessione` e `fn_guard_azione(…, 'documenti_template_manage')` (D-M a); la GUC spenta all'ingresso, scritta con l'id del modello, svuotata all'uscita e in errore (D-N a); firma e `RETURNS TABLE` ri-ancorate; `COMMENT` |
| `db/pgtap/documenti/test-porta-pubblicazione-template-v1.sql` | nuovo, come app, plan 10: la forma (DEFINER, INVOKER), senza l'azione il verbo rifiuta e non scrive, l'app non apre la porta né con `on` né con l'id del modello (pubblicare e chiudere), col verbo pubblica, chiude e lascia la GUC vuota. Operatore costruito, senza azioni |
| undici pgTAP di `documenti` che pubblicano come app | `dbops.fn_pgtap_concedi_azione(script.fn_utente_di_sessione(), 'documenti_template_manage')` dopo il contesto, col motivo |
| `test-fn-pubblica-template-documento-versione-v1` | il 21: la GUC dopo il verbo è vuota, non `off`; il 23 e il suo commento: la porta per l'app non si apre |
| `test-documenti-pubblicazione-e-copia-v1` | 9 e 10, e il commento: la porta per l'app non si apre |
| guide | `documenti-e-stampe` (chi pubblica; il trigger, orfano, nel «Vedi anche»); `architettura-permessi-e-autorizzazioni` §7.4 (la porta sulla riga, il seed dalla sessione del migratore; la pubblicazione esce dall'elenco delle porte aperte) |
| `manual/` | `fn_pubblica_template_documento_versione` (il permesso, la porta), `trgfn_template_documenti_versioni_protect_pubblicata` (la porta, la sessione del migratore, il test, la nota) |

**La prova sullo scratch** (`prova_changeset.py`, owner, `ROLLBACK`; 2026-11-24). Estratto eseguito per intero,
catalogo identico dopo; dopo l'estratto una sola `fn_pubblica_template_documento_versione`, argomenti e risultato
identici al vivo, `prosecdef` vero. I quindici pgTAP che nominano il verbo e `test-documenti-numero-versione-v1`:
stesso esito senza e con l'estratto, salvo il 21 di `fn-pubblica`, verde solo con. I rossi da owner che c'erano
restano uguali (`generati-eventi` 1, `vocabolari-forma` 1, `numero-versione` 3, `pubblicazione-e-copia` 8).

⚠️ **Il limite della prova, e come è stato aggirato.** Da owner la sessione è del migratore: il guard del verbo non
gira (D-M a) e il proprietario passa la porta. Una copia nello scratchpad dei pgTAP, con
`dbops.fn_sessione_del_migratore` ridefinita a `false` dentro la transazione, fa girare il guard: il test nuovo dà
10/10 (con 6 e 9 sostituiti, perché l'owner resta proprietario e la porta gli si apre), e gli undici adeguati danno
lo stesso esito o meglio (`pubblicazione-e-copia` da 8 rossi a 0: erano rossi da owner). **Il rifiuto dell'app con la
GUC giusta (6 e 9) si vede solo come app vera**: è il pgTAP di Tid dopo l'apply. ✅ Applicato da Tid il 2026-11-24:
`test-porta-pubblicazione-template-v1` e gli undici di `documenti` verdi come app, 6 e 9 compresi.

Guardrail sui file del giro: forme dei changeSet, `COMMENT` al presente, `runOnChange`, preambolo dei pgTAP:
verdi. Pre-commit: verde.

**Garanzie ritirate.** Nessuna che un lettore usasse: la GUC accesa dall'app apriva una porta che il modello non
voleva aperta. Il proprietario per `current_user` non salta più le regole 1 e 2: lo faceva il migrate, che passa
ancora (sessione del migratore), e lo farebbe un verbo DEFINER, che invece deve passare dalla porta.

### 9.5 La richiesta al team BE/FE (dopo l'apply)

Chi cambia per primo: il DB. Nessuna firma cambia, nessuna GUC da togliere (il BE non la accende).

* **I test Django che pubblicano** con un operatore di `dbops.fn_pgtap_crea_emittente_operatore` (senza azioni)
  ricevono `E_PERMESSO_NEGATO`: danno l'azione con `dbops.fn_pgtap_concedi_azione(<auth_user_id>,
  'documenti_template_manage')`, come già fanno `test_ddt_cambia_stato_db` e `test_offerta_cambia_stato_db`. L'elenco
  della risposta 3d (§4.5, Parte C), da censire tutto (la ricerca è del nome, non un elenco chiuso):
  `documenti/tests/db/test_template_standard_db.py`, `test_versione_contesto_db.py`, `_stampa.py`
  (`pubblica_per_stampare`, e con lui `test_ricerca_liste_db.py`, `test_scritture_dinamiche_db.py`),
  `core/tests/db/test_date_validita_guard_comune_db.py` (si aspetta il rifiuto delle date: senza l'azione arriverebbe
  prima il permesso).
* **Il manuale BE** della pubblicazione dei template, se racconta la porta o chi può pubblicare.

**Guide verificate per il giro** (`guide_coinvolte.py --oggetti` sui tre oggetti, 2026-11-24):
`documenti-e-stampe` — **indietro** dopo il giro (non dice chi può pubblicare né la porta), si aggiorna nello stesso
giro; il trigger orfano — segnale di «Vedi anche» incompleto, si aggiunge lì.

## 10. Il giro 10, lo scope degli emittenti — analisi del 2026-11-24

### 10.1 Che cosa c'è oggi (catalogo di dbdev, 2026-11-24)

* **Il modello** (guida dei permessi §4.9): `config.user_emittenti_fiscali` ha una riga per operatore (`UNIQUE
  (auth_user_id)`), ed è **fail-closed**: senza la riga l'operatore non vede nessun emittente. Il SUPER_ADMIN è l'unico
  multi-emittente e non passa da qui. Quindi **scrivere la riga è dare l'accesso a un'azienda**, cancellarla è
  toglierlo, e spostarla (cancellare e riscrivere) è far passare l'operatore a un'altra azienda.
* **Il verbo**, `script.fn_change_user_emittenti_scope(p_auth_user_id, p_emittente_ids)`: `INVOKER`, senza guard del
  permesso (lo tiene l'endpoint: SUPER_ADMIN, §4.5). Guard dei parametri, niente multi-emittente, il no-op, l'ultimo
  SUPER_ADMIN. Sposta con `DELETE` e `INSERT`, e apre la porta con `SET LOCAL … = 'on'` per il solo `DELETE`.
* **Il trigger**, `config.trgfn_user_emittenti_fiscali_guard_delete` (`BEFORE DELETE`): con la GUC `'on'` lascia
  passare **qualunque** riga, senza chiedere chi scrive. Senza GUC, ammette il `DELETE` solo se l'utente Django è
  spento o non esiste più (la cascata da `django.auth_user`). È la porta 10.
* **La tabella**: nessuna RLS; `zeroerp_app` ha `INSERT`, `UPDATE`, `DELETE`. L'`UPDATE` di `emittente_fiscale_id` lo
  ferma il lucchetto di colonna (`script.trgfn_lock_columns`, che passa da `fn_porta_manutenzione_aperta`: chiuso per
  l'app). L'`INSERT` **non lo ferma niente**.
* **Chi chiama il verbo**: il BE (amministrazione, §4.5); `anagrafiche.fn_provisiona_dati_di_sviluppo` (DEFINER,
  eseguibile dall'app, solo in SVILUPPO), che lo lancia il comando BE degli utenti di sviluppo senza un utente in
  sessione; quattordici pgTAP, nove dei quali girano da owner.
* **Chi scrive la tabella senza il verbo**: `script.fn_crea_utente_tecnico` (INVOKER, eseguibile dall'app), con un
  `INSERT` diretto. La chiamano i changeSet `80_data` `20260904-27` e `-39`, `scripts/sql/provision_zeroerp.sql` e il
  builder `dbops.fn_pgtap_crea_emittente_operatore`, su cui poggia la maggior parte dei pgTAP del dominio.
* **I pgTAP che aprono la porta da sé**: quattordici file accendono la GUC e cancellano la riga diretti (dodici come app,
  uno da owner, più il commento di `test-billing-account-auto-link-ef`). Quasi tutti per **spostare** l'operatore di
  contesto su un'altra azienda in mezzo al test.

### 10.2 Che cosa si cambia

1. **Il verbo diventa `SECURITY DEFINER`** (`SET search_path TO 'pg_catalog', 'public', 'pg_temp'`), con in prima riga
   `script.fn_utente_di_sessione` e `script.fn_guard_super_admin`: lo stesso controllo dell'endpoint, quindi nessun
   rifiuto nuovo per chi arriva dal backend. Firma e risultato invariati.
2. **La GUC sulla riga**: il verbo la scrive con l'`auth_user_id` dell'operatore che sposta, la spegne all'ingresso, la
   svuota all'uscita e in errore. Il trigger apre solo se la GUC vale `OLD.auth_user_id` **e** chi scrive è il
   proprietario (`fn_is_proprietario_tabella`). I due rami senza GUC (utente spento, utente che non esiste più) restano
   come sono: sono il modello, non una porta.
3. **Il perimetro**: nessuno da rimettere. La tabella non ha RLS, e chi passa il guard è il SUPER_ADMIN, che vede tutti
   gli emittenti. Il pgTAP «due emittenti» del piano qui non ha oggetto: lo si dichiara nel test.
4. **I pgTAP**: uno nuovo, come app, coi controesempi (la GUC accesa dall'app, con `on` e con l'id giusto, e il `DELETE`
   diretto: si ferma; il verbo da un operatore che non è SUPER_ADMIN: `E_PERMESSO_NEGATO`, e la riga resta; da
   SUPER_ADMIN sposta, e la GUC dopo è vuota). I quattordici che aprono la porta da sé passano al verbo (D-Q).
   `test-fn-change-user-emittenti-scope` e `test-user-emittenti-fiscali-immutable`, che provano proprio questa porta,
   si riscrivono sul modello nuovo.
5. **Le guide**: `architettura-permessi-e-autorizzazioni` §4.9 («si registra la sua riga»: si scrive col verbo, solo dal
   SUPER_ADMIN) e §7.4 (lo scope esce dall'elenco delle porte aperte); `risorse-umane-e-accessi` «Assegnazione emittente
   fiscale» (chi può assegnare). Il verbo e il trigger sono **orfani**: entrano nel «Vedi anche» di quelle due guide.
6. **La richiesta al BE**: il test `core/tests/db/test_email_bozza_invio_db.py:257`, e ogni test che chiama il verbo,
   lo chiama da SUPER_ADMIN (§4.5-bis); con D-O **a**, anche il censimento di chi scrive la tabella direttamente.

### 10.3 Tre scelte per Tid

* **D-O, la tabella in sola lettura per l'app.** La guida (§7.4, «La porta») lo dice già: l'app perde `INSERT`,
  `UPDATE` e `DELETE` sulle tabelle che il verbo protegge. Qui conta più che altrove, perché un `INSERT` diretto per un
  operatore senza riga gli **dà un'azienda** senza passare dal guard: chiudere solo la porta del `DELETE` lascia aperta
  la strada più semplice. Il costo è fuori da questo verbo: `fn_crea_utente_tecnico` scrive la tabella come app, e su
  di lei poggiano il seed degli utenti tecnici, il provisioning e il builder dei pgTAP; portarla a DEFINER chiede di
  sapere chi la chiama dal BE e con quale permesso, e tocca la stessa zona di R-DB-K2 (`fn_crea_operatore_v2`).
  **a** il giro 10 chiude la porta e il verbo; la tabella resta scrivibile, dichiarata nelle due guide come aperta
  («dominio a metà», §7.4), e la sola lettura diventa il **giro 10-bis**, con `fn_crea_utente_tecnico` e R-DB-K2,
  aperto con la richiesta al BE di questo giro · **b** tutto nel giro 10: sola lettura nel loop dei grant,
  `fn_crea_utente_tecnico` a DEFINER, prima la risposta del BE · **c** la sola lettura non si fa. ⭐ **a**: il modello
  non cambia e il giro 10-bis entra subito nel piano, con la data. **c** contraddirebbe la guida. ✅ **Decisa da Tid il 2026-11-24: a.**
* **D-P, il provisioning dei dati di sviluppo.** Lo lancia il comando BE senza un utente in sessione: col guard nel
  verbo si fermerebbe. La sessione del migratore (D-M) qui non aiuta, perché la connessione è dell'app. **a** il verbo
  si divide: il verbo pubblico tiene il nome, la firma e il guard, e chiama una primitiva senza guard
  (`script.fn_applica_user_emittenti_scope`, nome da confermare) che sposta la riga. La primitiva non è eseguibile
  dall'app (`v_fn_riservate`, nelle tre sedi di §11.8) e il provisioning, che è DEFINER, chiama lei. È la forma del
  giro 8 · **b** il provisioning apre il contesto di un SUPER_ADMIN prima di chiamare il verbo: `dev.smoke` nasce nello
  stesso giro, ma l'ordine dell'elenco diventerebbe una regola. ⭐ **a**: è la forma che il piano già prevede per la 8, e
  non lega il provisioning a un utente. ✅ **Decisa da Tid il 2026-11-24: a.**
* **D-Q, come i pgTAP spostano l'operatore.** Dodici file come app fanno la stessa cosa a mano (GUC, `DELETE`,
  `INSERT`): spostare l'operatore di contesto su un'altra azienda. Dopo il giro la porta non si apre più per loro.
  **a** nasce `dbops.fn_pgtap_sposta_scope_operatore(utente, emittente)` (INVOKER), che lo fa **dal verbo**: un
  SUPER_ADMIN di fixture (`fn_pgtap_crea_operatore_umano(…, true)`) entra nel contesto, chiama il verbo, e il contesto di
  prima si rimette. Le dodici copie si ritirano nello stesso giro (regola del 2) · **b** ogni test lo fa a mano, come
  il builder. ⭐ **a**: è la stessa operazione dodici volte, e il builder prova il verbo vero invece di aggirarlo. ✅ **Decisa da Tid il 2026-11-24: a.**

### 10.4 Le guide (`guide_coinvolte.py --oggetti` sui quattro oggetti, 2026-11-24)

* `architettura-permessi-e-autorizzazioni`: §7.4 **coerente** con il giro (descrive già la porta sulla riga e la sola
  lettura); §4.9 e l'elenco delle porte aperte di §7.4 **indietro** dopo il giro, si aggiornano nello stesso giro.
* `risorse-umane-e-accessi`: **indietro** dopo il giro (non dice che assegna solo il SUPER_ADMIN), si aggiorna.
* `architettura-multi-face-auth` §5.3, `soggetti-e-ruoli-anagrafici`: descrivono la tabella in lettura, **coerenti**.
* Orfani: `script.fn_change_user_emittenti_scope` e `config.trgfn_user_emittenti_fiscali_guard_delete`. Sono il verbo e
  la porta di un concetto del dominio, quindi un «Vedi anche» incompleto, non una guida che manca: entrano nelle due
  guide sopra.

**Garanzie ritirate.** Nessuna su cui conti un lettore. La GUC accesa dall'app apriva una porta che il modello non
voleva aperta, e il BE non la accende (§4.2). Chi chiamava il verbo senza essere SUPER_ADMIN ora è rifiutato, e sono
solo test: l'endpoint chiede già il SUPER_ADMIN.

### 10.5 Il giro scritto — 2026-11-25

| File | Che cosa |
| --- | --- |
| `20_code/script/20261124-01-create-fn-applica-user-emittenti-scope` | la primitiva (D-P a): il corpo di prima del verbo, senza permesso; la GUC spenta all'ingresso, scritta con l'`auth_user_id`, svuotata dopo il `DELETE` e in errore; firma ancorata, `bigint[]` con la ragione; `COMMENT` |
| `20_code/script/20261124-02-update-fn-change-user-emittenti-scope-definer-guard` | il verbo: `SECURITY DEFINER`, `search_path` `pg_catalog, public, pg_temp`, `fn_utente_di_sessione` e `fn_guard_super_admin` in prima riga, poi la primitiva; nessuna eccezione per la sessione del migratore (nessun changeSet lo chiama); firma ancorata, identica al vivo; `COMMENT` |
| `20_code/anagrafiche/20261124-03-update-fn-provisiona-dati-di-sviluppo-scope-dalla-primitiva` | il provisioning chiama la primitiva: alla riga della chiamata l'utente di sessione è vuoto per costruzione. Corpo e attributi dal catalogo (ultimo `20261123-84`), una riga cambiata |
| `20_code/config/20261124-04-update-trgfn-user-emittenti-fiscali-guard-delete-porta-sulla-riga` | il guard: la porta chiede la GUC uguale a `OLD.auth_user_id` **e** `fn_is_proprietario_tabella`; utente spento e utente cancellato invariati; `COMMENT`. Montaggio invariato, resta INVOKER |
| `20_code/dbops/20261124-05-create-fn-pgtap-sposta-scope-operatore` | il builder (D-Q a): un SUPER_ADMIN di fixture entra nel contesto, chiama il verbo, il contesto di prima si rimette, anche in errore. L'utente di prima si legge da `fn_utente_di_sessione` (presidio `test-fn-utente-di-sessione-v1`, 14) |
| `90_end/20261124-06-postura-fn-applica-user-emittenti-scope-riservata` | la primitiva senza `EXECUTE` a PUBLIC e all'app; le altre due sedi di §11.8: `v_fn_riservate` del loop `20260205-41` e il blocco «LA PORTA SULLE FUNZIONI» di `provision_zeroerp.sql` |
| `db/pgtap/config/test-porta-scope-emittenti-v1.sql` | nuovo, come app, plan 12: la forma, la primitiva non eseguibile, il verbo da operatore e senza utente (`E_PERMESSO_NEGATO`, la riga resta), il `DELETE` diretto con `on` e con l'id giusto (rifiutato), dal verbo da SUPER_ADMIN (sposta, GUC vuota, contesto rimesso) |
| ventiquattro pgTAP | undici che chiamavano il verbo per dare o togliere l'azienda alla fixture (nove `rls/`, `script/test-scope-emittenti-fail-closed-v1`, `script/test-fn-scope-ef-whitelist`) e tredici che aprivano la porta a mano: al builder, coi commenti. `test-user-emittenti-fiscali-immutable`, 3, rovesciato (la GUC `on` non apre più). `test-fn-change-user-emittenti-scope` ricostruito: operatore e SUPER_ADMIN da `fn_pgtap_crea_operatore_umano`, che nascono senza azienda, e il verbo chiamato dal SUPER_ADMIN; la precondizione non tocca né la porta né il verbo |
| guide | `architettura-permessi-e-autorizzazioni` §4.9 (chi scrive la riga, e la tabella ancora aperta per l'`INSERT`), §7.4 (lo scope fuori dalle porte aperte), «Vedi anche»; `risorse-umane-e-accessi` (solo il SUPER_ADMIN assegna), «Vedi anche» |
| `manual/` | riscritte `fn_change_user_emittenti_scope` e `trgfn_user_emittenti_fiscali_guard_delete` (raccontavano la porta con `on` e il cleanup a mano); nuove `fn_applica_user_emittenti_scope` e `fn_pgtap_sposta_scope_operatore`; corrette `user_emittenti_fiscali`, `fn_get_user_emittenti_scope`, `fn_pgtap_crea_operatore_umano`, `fn_cancella_fondo_fattura` e `trgfn_vendite_contabili_righe_guard_contenuto` (la porta 8 non ha più «la stessa forma» della 10) |

**La prova sullo scratch** (`prova_changeset.py`, owner, `ROLLBACK`; 2026-11-25). I sei changeSet insieme: estratto
eseguito per intero, catalogo identico dopo. La `preCondition` del `-06` sullo scratch dà 0: la primitiva nasce nel
`-01` dello stesso giro, sul database che lo incontra c'è. Attributi dopo l'estratto (pgTAP di prova nello
scratchpad, 8/8): verbo, primitiva e provisioning con una firma sola, argomenti e risultato identici al vivo; ACL del
verbo e del provisioning invariate; la primitiva eseguibile dal solo proprietario; il guard con un montaggio,
INVOKER. I trenta pgTAP che nominano verbo, porta, tabella o builder: con l'estratto tutti verdi, salvo
`test-porta-scope-emittenti-v1` 9 (da owner il proprietario apre la porta: si vede solo come app) e
`test-rls-email-ambito-reparto-operatore`, rosso da owner come prima del giro (7 ok / 15, test da app). Presidi
trasversali (`riferimenti-morti`, `security-definer-search-path`, `comment-al-presente`, catalogo dei messaggi, le
riservate di `dbops` e `pratiche`): stesso esito senza e con. Guardrail dei changeSet e del preambolo, pre-commit:
verdi.

⚠️ **Da owner i rifiuti del verbo si vedono** (il guard non ha l'eccezione del migratore), **quello della porta col
valore giusto no**: è il 9 del pgTAP nuovo, e lo vede la corsa di Tid come app. ✅ Applicato da Tid il 2026-11-25:
`test-porta-scope-emittenti-v1` e i ventiquattro adeguati verdi come app, 9 compreso; doc auto-generata rigenerata.

**Un fatto trovato facendo il giro, per R-DB-K2.** Il builder dà il SUPER_ADMIN con `fn_pgtap_crea_operatore_umano(…,
true)`, che lavora come app: oggi l'app può crearsi un SUPER_ADMIN (operatore da `fn_crea_operatore_v2` e binding
scritto diretto). Il builder non apre niente di nuovo, ma lo mostra: è la porta di R-DB-K2, e il giro 10-bis la
incontra.

### 10.6 La richiesta al team BE/FE (dopo l'apply)

Chi cambia per primo: il DB. Nessuna firma cambia, nessuna GUC da togliere (il BE non la accende, §4.2).

* **I test che chiamano `script.fn_change_user_emittenti_scope`** con un operatore che non è SUPER_ADMIN, o senza
  contesto, ricevono `E_PERMESSO_NEGATO`: lo chiamano da SUPER_ADMIN (`apri_contesto_operatore(cur,
  super_admin=True)`, o il BB `super_admin_di_prova` di §4.7). Il noto è `core/tests/db/test_email_bozza_invio_db.py:257`
  (§4.5, Parte C); la ricerca è del nome, non un elenco chiuso.
* **I test che tolgono la riga di scope a mano**, accendendo `zeroerp.allow_user_emittente_delete_override` e
  cancellando da `config.user_emittenti_fiscali`: la porta non si apre più. Passano al verbo da SUPER_ADMIN.
* **Il censimento per il giro 10-bis** (D-O a): chi scrive `config.user_emittenti_fiscali` senza il verbo, nel
  codice e nei test (`INSERT`, `DELETE` diretti), e chi chiama `script.fn_crea_utente_tecnico`, con quale utente e
  quale permesso controlla l'endpoint. Serve a chiudere la tabella in sola lettura per l'app senza rompere chi la
  scrive oggi.
* **Il manuale BE** dell'endpoint dello scope (`api_amm_software`), se racconta chi può cambiare l'emittente.

**Guide verificate per il giro** (`guide_coinvolte.py --oggetti` sui cinque oggetti, 2026-11-25):
`architettura-permessi-e-autorizzazioni` e `risorse-umane-e-accessi` — **indietro**, aggiornate nello stesso giro;
verbo e guard non più orfani. `anagrafiche.fn_provisiona_dati_di_sviluppo` resta orfano: è uno strumento dello
sviluppo, non un concetto del dominio. Primitiva e builder non hanno ancora la pagina auto-generata: la porta la
rigenerazione dopo l'apply.

## 11. Il giro 9, la registrazione tardiva — analisi del 2026-11-25

### 11.1 Che cosa c'è oggi (catalogo di dbdev, 2026-11-25)

* **La decisione che il giro rispetta** (D20-b, `work-done/2026/brief-db-validata-e-registrazione-tardiva` §2.2 e
  §4.1, riletta): la madre abbina e registra una riga `SOSPESA` sotto una distinta registrata, **passando da
  `ABBINATA`** perché girino tutti i guard dell'abbinamento (transizione, dati, rata col doppio tempo, scope). Alla
  4ª mossa del guard sulla distinta finale si presenta con la GUC `app.registrazione_tardiva_riga_id` = l'id della
  riga, e la richiude prima di uscire. La chiama solo il BE (`POST /pagamenti/righe/{id}/registra/`, permesso
  `registra_distinta`, BE-3). Il giro non cambia **cosa** fa la madre: cambia **come gira**.
* **Il verbo**, `pagamenti.fn_posta_riga_tardiva`: `INVOKER`, senza guard del permesso, senza `search_path`. Scrive
  la riga (due `UPDATE`) e il movimento (`INSERT`). Nessuna funzione DB lo chiama.
* **Il trigger**, `pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale`: la porta è **già sulla riga**
  (GUC = `NEW.id`, solo nel ramo del cambio di stato verso uno stato postabile), ma senza il proprietario.
* **Il perimetro, oggi, lo fa la RLS.** Le tre tabelle hanno la policy dell'operatore:
  * `vendite_contabili`: la distinta del proprio emittente;
  * `vendite_contabili_righe`: la riga se è propria la distinta **oppure** la fattura;
  * `vendite_movimenti`: il movimento se è propria la fattura.
  Il verbo legge la riga **in join con la distinta**: sotto la RLS la regola effettiva è «la distinta è nel
  perimetro», e fuori risponde `E_RIGA_CONTABILE_NON_TROVATA` (stessa frase di «non esiste», no-leak). La fattura
  di destinazione la controllano il guard di scope sulla riga (`trgfn_guard_emittente_scope('fattura')`, quando la
  colonna cambia) e la `WITH CHECK` della policy del movimento.
* ⚠️ **Il difetto trovato, sulla rete di sotto.** Su `vendite_movimenti` il guard di scope
  (`trg_vendite_movimenti_a10_guard_emittente_scope_ins_upd`) gira **prima** del mirror che ricava la fattura dalla
  riga (`trg_vendite_movimenti_a10_sync_contabile_from_riga_ins_upd`: `guard` < `sync` nell'ordine dei nomi). I due
  scrittori del movimento (`fn_posta_contabile`, la tardiva) non passano la fattura: il guard la vede vuota e lascia
  passare. Sotto la RLS non si vedeva (la `WITH CHECK` della policy gira sulla riga finale); dentro una DEFINER la
  RLS non c'è, e il guard è muto. È la regola «chi legge una colonna gira dopo chi la risolve» (linee guida trigger).
  Oggi nessuna DEFINER scrive movimenti: la tardiva sarebbe la prima.

### 11.2 Che cosa si cambia

1. **Il verbo diventa `SECURITY DEFINER`** (`search_path` `pg_catalog, public, pg_temp`), con in prima riga
   `script.fn_utente_di_sessione` e `script.fn_guard_azione(v_utente, 'registra_distinta')`: la stessa azione
   dell'endpoint (§4.5), quindi nessun rifiuto nuovo per chi arriva dal backend. Firma e `RETURNS TABLE` ri-ancorate
   con `%TYPE` (la doc le mostra sciolte), identiche al vivo.
2. **Il perimetro, una volta all'ingresso, sull'oggetto padre.** Dopo la lettura della riga: la distinta deve essere
   nel perimetro dell'utente (`script.fn_check_user_emittente_scope` sull'emittente di
   `fn_resolve_emittente_fiscale_id('contabile', …)`), altrimenti `E_RIGA_CONTABILE_NON_TROVATA`, come oggi. È la
   regola che la RLS faceva valere, non una nuova. E la **fattura di destinazione** deve esserlo
   (`E_SCOPE_EMITTENTE`, il codice del guard di scope): il guard sulla riga tace se la riga ha già quella fattura, e
   quello del movimento oggi è muto (sopra). Nessun filtro ricopiato nelle query: le righe figlie seguono la riga.
3. **La GUC sulla riga** resta com'è nel valore; si spegne all'ingresso e si svuota anche in errore (oggi solo
   all'uscita buona). Il trigger chiede in più il proprietario (`fn_is_proprietario_tabella`): dentro il verbo sì,
   per l'app mai.
4. **La rete del movimento** (D-S): il guard di scope gira dopo il mirror.
5. **I pgTAP**: uno nuovo, come app, coi controesempi del piano: la GUC accesa dall'app con l'id giusto e l'`UPDATE`
   diretto (si ferma); senza `registra_distinta` (`E_PERMESSO_NEGATO`, niente scritto); **due emittenti**: la riga
   di una distinta dell'altro (`E_RIGA_CONTABILE_NON_TROVATA`), una fattura dell'altro su una riga propria
   (`E_SCOPE_EMITTENTE`), e il movimento non nasce; col permesso registra e la GUC dopo è vuota. Ai tre pgTAP che
   chiamano il verbo (`test-posta-riga-tardiva-v1`, `test-righe-distinta-annullata-congelate-v1`,
   `test-fn-posta-contabile`) `dbops.fn_pgtap_concedi_azione(…, 'registra_distinta')`.
6. **Le guide**: `gestione-dei-pagamenti` «Chi resta indietro» (il permesso lo chiede anche il DB; il perimetro);
   `architettura-permessi-e-autorizzazioni` §7.4 (il contabile esce dalle porte aperte solo col giro 8: qui solo la
   tardiva). Il mirror del movimento è orfano: dettaglio interno, nel «Vedi anche» della guida dei pagamenti se D-S
   lo tocca.
7. **La richiesta al BE**: i test che chiamano il verbo con un operatore senza `registra_distinta` (Parte C, §4.5).

### 11.3 Una scelta per Tid

* **D-S, l'ordine dei trigger sul movimento.** **a** nello stesso giro: il guard di scope di `vendite_movimenti` si
  rimonta in `z10` (dopo il mirror), per funzione e con tutti i nomi storici (linee guida trigger, «Un trigger si
  rimonta per funzione»), col pgTAP che fissa l'ordine e un movimento costruito con la fattura di un altro emittente
  dentro una DEFINER · **b** il difetto resta dichiarato, e il verbo controlla la fattura all'ingresso (lo fa
  comunque, punto 2). ⭐ **a**: la rete di §4.3 («sotto resta la rete che c'è») è la premessa dei giri 9, 8 e 1-7, e
  per il movimento oggi non c'è. Gli scrittori sono due e INVOKER, e nessuna DEFINER senza utente scrive movimenti:
  con l'ordine giusto nessun percorso di oggi cambia esito (catalogo 2026-11-25). ✅ **Decisa da Tid il 2026-11-25: a.**

### 11.4 Le guide (`guide_coinvolte.py --oggetti` sui sei oggetti, 2026-11-25)

* `gestione-dei-pagamenti` «Chi resta indietro» e «Validare, e poi registrare»: **indietro** dopo il giro (dice
  «compare solo a chi ha `registra_distinta`», cioè l'endpoint; non dice che lo chiede il DB, né il perimetro). Si
  aggiorna nello stesso giro.
* `architettura-permessi-e-autorizzazioni` §7.2 (il guard di scope) e §7.4: **coerente**; §7.4 dice già che il
  contabile apre ancora con la sola GUC, e resta vero fino al giro 8.
* `processi-pgagent-funzionali`: descrive il guard di scope per i lavori del proprietario, **coerente**.
* Orfano: `pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga`, il mirror: è un dettaglio interno; con D-S
  **a** entra nel «Vedi anche» della guida dei pagamenti.

**Garanzie ritirate.** Nessuna. Il verbo smette di dipendere dalla RLS per il perimetro, e lo rimette all'ingresso
con la stessa risposta; il permesso è quello dell'endpoint. Con D-S **a** il guard del movimento comincia a
rifiutare una fattura fuori perimetro: è la garanzia che dichiarava di dare.

### 11.5 Il giro scritto — 2026-11-25

| File | Che cosa |
| --- | --- |
| `20_code/pagamenti/20261124-07-update-trgfn-righe-guard-distinta-finale-porta-proprietario` | il guard: la porta della quarta mossa chiede in più `fn_is_proprietario_tabella`; le altre mosse invariate; `COMMENT` riscritto al presente (§5d). Corpo dal catalogo (ultimo `20261103-07`) |
| `20_code/pagamenti/20261124-08-update-fn-posta-riga-tardiva-definer-guard-perimetro` | il verbo: `SECURITY DEFINER`, `search_path`; `fn_guard_azione(…, 'registra_distinta')` in prima riga; il perimetro all'ingresso (passo 2-bis: la distinta, `E_RIGA_CONTABILE_NON_TROVATA`; la fattura, `E_SCOPE_EMITTENTE`); la GUC spenta all'ingresso e svuotata anche in errore; firma e `RETURNS TABLE` ancorate, identiche al vivo; `COMMENT` al presente. Corpo dal catalogo (ultimo `20260918-40`) |
| `20_code/pagamenti/20261124-09-rimonta-guard-scope-movimenti-dopo-il-mirror` | D-S a: il guard di scope di `vendite_movimenti` rimontato come `trg_vendite_movimenti_z10_guard_emittente_scope_ins_upd`, tolti con `IF EXISTS` il nome storico e il nuovo; `COMMENT ON TRIGGER`. Non è un trigger di `ci_apply` (guardrail §11.5 verde) |
| `db/pgtap/pagamenti/test-porta-registrazione-tardiva-v1.sql` | nuovo, come app, plan 11: la forma, l'ordine dei guard del movimento (per funzione), senza `registra_distinta` (rifiuta, non scrive), la GUC sull'id giusto e l'`UPDATE` diretto (rifiutato), due emittenti (la riga di una distinta di B, la fattura di B su una riga di A: niente scritto), col permesso registra, GUC vuota |
| quattro pgTAP | `test-posta-riga-tardiva-v1` e `test-righe-distinta-annullata-congelate-v1`: `fn_pgtap_concedi_azione(…, 'registra_distinta')`; `script/test-permessi-funzioni-risoluzione` (24) e `script/test-permessi-trigger-guard-emittente` (5): il trigger del movimento col nome nuovo |
| guide | `gestione-dei-pagamenti` «Chi resta indietro» (il permesso chiesto anche dal DB, il perimetro, la porta), «Vedi anche» (il mirror e il guard di scope del movimento) |
| `manual/` | `fn_posta_riga_tardiva` (il permesso e il perimetro, la porta, i codici, i test), `trgfn_vendite_contabili_righe_guard_distinta_finale` (la porta col proprietario), `trgfn_vendite_movimenti_sync_contabile_from_riga` e `vendite_movimenti` (chi legge i riferimenti gira dopo) |

**La prova sullo scratch** (`prova_changeset.py`, owner, `ROLLBACK`; 2026-11-25). I tre changeSet insieme: estratto
eseguito per intero, catalogo identico dopo. Attributi dopo l'estratto (pgTAP di prova, 5/5): una firma sola,
argomenti, default e risultato identici al vivo; il verbo DEFINER col `search_path`, ACL invariata; il guard INVOKER
con un montaggio. Il pgTAP nuovo: 10/11, rosso il 6 per costruzione (da owner il proprietario apre la porta: si
vede solo come app). I 32 pgTAP di `pagamenti` e quelli che nominano movimento, verbo o porta: stesso esito senza e
con, salvo i quattro adeguati, verdi con. Presidi trasversali (`riferimenti-morti`, `security-definer-search-path`,
`comment-al-presente`, catalogo dei messaggi, `fn-utente-di-sessione`): invariati. Guardrail, preambolo e
pre-commit: verdi.

⚠️ **Il caso che il pgTAP non costruisce**: un movimento su una fattura fuori perimetro scritto da una DEFINER. L'app
non crea funzioni del proprietario, e il verbo lo ferma prima (8). Il guard del movimento lo presidia l'ordine (2).

✅ **Applicato da Tid il 2026-11-25**: `test-porta-registrazione-tardiva-v1` e i quattro adeguati verdi come app, 6
compreso; doc auto-generata rigenerata. ⚠️ La prima corsa come app ha trovato un difetto **del test**, non del giro: il
9 leggeva la riga di B nel contesto di A, e la RLS la nascondeva (`NULL` sull'intera stringa; da owner non si vede).
Ora la riga di B si legge nel contesto del suo operatore.

### 11.6 La richiesta al team BE/FE (dopo l'apply)

Chi cambia per primo: il DB. Nessuna firma cambia, nessuna GUC da togliere (il BE non la accende, §4.2).

* **I test che chiamano `pagamenti.fn_posta_riga_tardiva`** con un operatore senza `registra_distinta` ricevono
  `E_PERMESSO_NEGATO`: danno l'azione con `dbops.fn_pgtap_concedi_azione(<auth_user_id>, 'registra_distinta')`. La
  ricerca è del nome, non un elenco chiuso (§4.5, Parte C).
* **Il perimetro**: una riga di una distinta fuori perimetro risponde `E_RIGA_CONTABILE_NON_TROVATA` come prima (il
  404 non cambia); una fattura fuori perimetro risponde ora `E_SCOPE_EMITTENTE` dal verbo, dove prima arrivava dal
  guard della riga o dalla policy del movimento. Se un test o la mappatura degli errori dell'endpoint aspettava
  l'errore della policy, va allineato.
* **Il manuale BE** dell'endpoint `POST /pagamenti/righe/{id}/registra/`, se racconta chi può registrare.

**Guide verificate per il giro** (`guide_coinvolte.py --oggetti` sui quattro oggetti, 2026-11-25):
`gestione-dei-pagamenti` — **indietro**, aggiornata nello stesso giro; il mirror non più orfano.
`architettura-permessi-e-autorizzazioni` e `processi-pgagent-funzionali` — **coerenti**.

## 12. Il giro 11, la bolla di riconsegna — analisi e giro scritto del 2026-11-25

### 12.1 Che cosa c'è oggi (catalogo di dbdev, 2026-11-25)

* **Il verbo**, `vendite.fn_genera_ddt_riconsegna`: `INVOKER`, senza guard del permesso, senza `search_path`. Lo
  chiama il BE (`resi_repository.genera_ddt_riconsegna`, endpoint `ApiResoGeneraDdtRiconsegna`, §4.5) e, a DB, la
  sola fixture `dbops.fn_pgtap_crea_ddt_riconsegna`. Scrive la bolla, i suoi indirizzi, le righe, il ponte
  `resi_righe_riconsegne` e, se il reso è legato a un ordine, il fulfillment; poi proietta lo stato dell'ordine.
* **Il trigger**, `script.trgfn_righe_guard_articolo_ammesso`, building block montato su sette tabelle di righe; la
  porta la legge solo il montaggio `DDT_VENDITA` (`vendite.ddt_righe`). La porta è **già sulla riga**: la GUC
  `zeroerp.ddt_riconsegna` vale l'id del reso, e l'articolo dev'essere fra le righe di quel reso. Manca il
  proprietario: l'app accende la GUC con l'id di un suo reso e scrive diretta, su una bolla qualsiasi, una riga con un
  articolo che la bolla non ammette più (diventato solo componente, obsoleto, d'altra natura).
* **Il perimetro, oggi, lo fa la RLS.** Tutte le tabelle che il verbo legge e scrive hanno la policy dell'operatore
  (`vendite.resi` e `vendite.ddt` sulla colonna `emittente_fiscale_id`, le figlie risolte dal padre). Un reso fuori
  perimetro risponde `E_RESO_NOT_FOUND` (non si vede). Su `vendite.ddt` c'è anche la rete,
  `trg_ddt_z10_guard_emittente_scope_ins_upd` (`script.trgfn_guard_emittente_scope('fiscale', …)`), che legge l'utente
  di sessione e vale anche dentro una DEFINER; su `resi`, righe e ponti no.
* **Il permesso dell'endpoint** (§4.5, §4.5-bis): nessuna azione, il livello `TUTTO` sull'oggetto `vendite.reso` con la
  ricaduta sull'area. Non `conferma_reso`.

### 12.2 Che cosa si cambia

1. **Il verbo diventa `SECURITY DEFINER`** (`search_path` `pg_catalog, public, pg_temp`), con in prima riga
   `script.fn_utente_di_sessione` e `script.fn_guard_livello(v_utente, 'vendite', 'reso', 'TUTTO')`: la stessa forma
   dell'endpoint (oggetto, poi area), quindi nessun rifiuto nuovo. Firma e `RETURNS` ancorate come nell'ultimo
   changeSet (`20261114-54`), identiche al vivo.
2. **Il perimetro, una volta, sul reso.** La lettura del reso porta anche `r.emittente_fiscale_id`, la colonna che la
   policy di `vendite.resi` legge; fuori perimetro (`script.fn_check_user_emittente_scope`, la stessa del giro 9)
   risponde `E_RESO_NOT_FOUND`, come oggi, e **prima** dello stato (non dice se il reso d'altri è confermato). Tutto il
   resto discende dal reso; la bolla nuova prende l'azienda dalla bolla d'origine, e la giudica la rete di
   `vendite.ddt`. Nessun filtro ricopiato nelle query.
3. **La porta**: la GUC si spegne all'ingresso; il trigger chiede in più `fn_is_proprietario_tabella(TG_RELID)`.
   ⚠️ **Nessun blocco `EXCEPTION` che la svuoti in errore**, a differenza del giro 9: una GUC locale torna indietro da
   sola quando la transazione o la sottotransazione si annulla (provato sul catalogo il 2026-11-25: dentro un blocco
   `EXCEPTION` e con un `ROLLBACK TO SAVEPOINT` il valore torna quello di prima). Nel giro 9 il blocco è quindi
   ridondante, e costa una sottotransazione per chiamata: Tid lo fa togliere (§12.7).
4. **Nessuna primitiva da chiudere**: il verbo è l'unica strada e tiene l'`EXECUTE` all'app; niente in
   `v_fn_riservate`.
5. **I pgTAP**: uno nuovo, come app (sotto). I ventuno che chiamano il verbo o la fixture **non cambiano**: tutti
   costruiscono il reso con `dbops.fn_pgtap_crea_reso`, che concede `conferma_reso` e con essa l'area `vendite` al
   minimo, `TUTTO`, su cui l'oggetto ricade. Stesso esito senza e con il giro (§12.5).
6. **D-L non entra**: il caso «senza permesso» si costruisce con un override sull'oggetto `vendite.reso` a `LETTURA`
   (col tetto d'area vince il più restrittivo), scritto sul posto: è la prima occorrenza. Il builder del livello d'area
   resta per il giro 8 o 1-7.

### 12.3 Decisioni

Nessuna. Il guard è quello già fissato in §4.5-bis; la strada è la D-A **a**.

### 12.4 Le guide (`guide_coinvolte.py --oggetti` sui quattro oggetti, 2026-11-25)

* `gestione-ddt` (`vendite.ddt_righe`): **indietro**. Diceva «la riconsegna è esente» senza dire che l'esenzione vale
  solo dal verbo, né chi genera la riconsegna e su quale reso. Aggiornata: l'esenzione solo per le righe della
  generazione e gli articoli del reso, il livello `TUTTO` sul reso e il perimetro, il verbo e il guard nel «Vedi anche».
* `architettura-permessi-e-autorizzazioni` §7.4: **indietro** («i DDT di riconsegna si aprono ancora con la sola
  GUC»). Aggiornata: la riconsegna porta nella GUC l'id del reso; restano aperti il reset dei lotti e il contabile.
* `gestione-listini` (la tabella dei guard): **coerente**, non parla della porta.
* `gestione-preventivi`, `statistiche-del-planner` (`vendite.ddt_righe`): **coerenti**, non toccano la riconsegna.
* `pgtap-come-si-scrive-un-test` (la fixture `fn_pgtap_crea_ddt_riconsegna`): **coerente**, la fixture non cambia.
* Orfano: `vendite.fn_genera_ddt_riconsegna`. Non più: è nel «Vedi anche» di `gestione-ddt`.
* Rilancio sul diff (i due changeSet e il pgTAP, 2026-11-25): trenta guide, perché i corpi nominano i building block
  che usano (`fn_log_and_raise_error`, `fn_check_articolo_riga`, `fn_check_user_emittente_scope`, i builder pgTAP…).
  Il giro li usa senza cambiarli: tutte **coerenti**, salvo le due già aggiornate sopra.

**Garanzie ritirate.** Nessuna. Il verbo smette di dipendere dalla RLS per il perimetro e lo rimette all'ingresso con
la stessa risposta; il permesso è quello dell'endpoint; la porta si stringe.

### 12.5 Il giro scritto — 2026-11-25

| File | Che cosa |
| --- | --- |
| `20_code/script/20261124-10-update-trgfn-righe-guard-articolo-ammesso-porta-proprietario` | il guard: la porta della riconsegna chiede in più `fn_is_proprietario_tabella(TG_RELID)`; il resto invariato; `COMMENT` al presente. Corpo dal catalogo (ultimo `20261105-11`) |
| `20_code/vendite/20261124-11-update-fn-genera-ddt-riconsegna-definer-guard-perimetro` | il verbo: `SECURITY DEFINER`, `search_path`; `fn_guard_livello(…, 'vendite', 'reso', 'TUTTO')` in prima riga; la GUC spenta all'ingresso; il perimetro del reso (passo 2-bis, `E_RESO_NOT_FOUND`); firma e `RETURNS` ancorate; `COMMENT` al presente. Corpo dal catalogo (ultimo `20261114-54`) |
| `db/pgtap/vendite/test-porta-ddt-riconsegna-v1.sql` | nuovo, come app, plan 8: la forma; area `TUTTO` e oggetto `vendite.reso` a `LETTURA` (rifiuta, non scrive); la GUC sull'id del reso e la riga diretta con l'articolo diventato solo componente (rifiutata); due emittenti (il reso di B: `E_RESO_NOT_FOUND`, niente scritto, letto nel contesto di B); col permesso la bolla nasce con l'articolo del reso; GUC vuota dopo |
| guide | `gestione-ddt` (data, «Vedi anche», l'esenzione, chi genera la riconsegna), `architettura-permessi-e-autorizzazioni` §7.4 |
| `manual/` | `fn_genera_ddt_riconsegna` (DEFINER, «Chi la chiama, e su quale reso», la porta, nota di migrazione), `trgfn_righe_guard_articolo_ammesso` (la porta con il proprietario) |

**La prova sullo scratch** (`prova_changeset.py`, owner, `ROLLBACK`; 2026-11-25). I due changeSet insieme: estratto
eseguito per intero, catalogo identico dopo. Il pgTAP nuovo: con 7/8, rosso il 4 per costruzione (da owner il
proprietario apre la porta: si vede solo come app); senza 2/8. I ventuno pgTAP che nominano il verbo, la porta o la
fixture: stesso esito senza e con; i rossi già presenti (`test-ddt-righe-evase-dall-ordine-v1` 2,
`test-fn-partite-merce-chiusura-v1`, `test-fn-situazione-merce-ordine-chiusura-v1`, `test-vw-situazione-merce-ordine-v1`
1 ciascuno) sono di perimetro da owner, invariati. Presidi trasversali (`comment-al-presente`, `riferimenti-morti`,
`security-definer-search-path`, catalogo dei messaggi, `fn-utente-di-sessione`, `app-definer-dichiarate`,
`permessi-trigger-guard-emittente`): invariati. Pre-commit sui file nuovi: verde.

⚠️ La prima stesura del pgTAP costruiva le due aziende con due `fn_pgtap_crea_mondo_cliente`: con un contesto aperto
il builder riusa l'azienda di chi agisce, e le due erano la stessa (il 5 passava il perimetro). B ora nasce da
`fn_pgtap_crea_emittente_operatore`, e il suo mondo nel suo contesto.

✅ **Applicato da Tid il 2026-11-25**, insieme a `20261124-12` (§12.7): pgTAP come app verdi, `test-porta-ddt-riconsegna-v1`
compreso il 4; doc auto-generata rigenerata.

### 12.6 La richiesta al team BE/FE (dopo l'apply)

Chi cambia per primo: il DB. Nessuna firma cambia, nessuna GUC da togliere (il BE non la accende, §4.2).

* **I test che chiamano `vendite.fn_genera_ddt_riconsegna`** (o la fixture `dbops.fn_pgtap_crea_ddt_riconsegna`)
  con un operatore senza il livello `TUTTO` su `vendite.reso` (né sull'area `vendite`) ricevono `E_PERMESSO_NEGATO`.
  La ricerca è del nome, non un elenco chiuso: in §4.5, Parte C, il BE non ne aveva trovati (gli smoke dei resi passano
  dall'endpoint).
* **Il perimetro**: un reso di un'altra azienda risponde `E_RESO_NOT_FOUND` come prima (il 404 non cambia).
* **Il manuale BE** dell'endpoint di generazione della riconsegna, se racconta chi può generarla.

### 12.7 Il blocco `EXCEPTION` del giro 9 si toglie — 2026-11-25

✅ **Decisione di Tid, 2026-11-25**: si toglie. `20_code/pagamenti/20261124-12-update-fn-posta-riga-tardiva-senza-blocco-exception`:
le tre scritture di `pagamenti.fn_posta_riga_tardiva` tornano nel corpo, nello stesso ordine, senza il blocco che
svuotava la GUC e rilanciava; la porta si accende e si richiude come prima. Firma, `SECURITY DEFINER`, `search_path`,
permesso e perimetro identici al vivo; il `COMMENT` dice che in errore la porta la richiude il rollback. Corpo dal
catalogo (ultimo `20261124-08`), con il rollback al corpo di prima. Manuale `fn_posta_riga_tardiva` allineato.

**La prova sullo scratch** (2026-11-25): da solo e insieme al giro 11, estratto per intero e catalogo identico dopo.
`test-porta-registrazione-tardiva-v1` 10/11 senza e con (il 6 rosso per costruzione da owner),
`test-posta-riga-tardiva-v1` 19/19, `test-righe-distinta-annullata-congelate-v1` 22/22, `test-fn-posta-contabile` 19/19,
`comment-al-presente` e `security-definer-search-path` invariati.

⚠️ Che la GUC torni indietro in errore non lo fissa nessun pgTAP: proverebbe la semantica di PostgreSQL, non il
verbo. Il fatto è scritto qui e nel `COMMENT`; il test 11 della porta 9 fissa la GUC vuota dopo una chiamata buona.

Nessuna richiesta al BE: niente cambia per chi chiama.

## 13. Il giro 8, il fondo fattura — analisi del 2026-11-25

### 13.1 Che cosa c'è oggi (catalogo di dbdev, 2026-11-25)

* **La decisione che il giro rispetta** (D10-D11 di `brief-incassi-riconciliazione-rate-promemoria`, rilette): il fondo
  vale il residuo alla nascita e non insegue; `ESEGUITO` è un fatto e non si cancella mai; il reset cancella l'atto non
  eseguito e il giro successivo ne rifà uno nuovo. Il giro non cambia **che cosa** si cancella: cambia **come gira**.
* **La sede dei tre DELETE**, `vendite.fn_cancella_fondo_fattura`: `INVOKER`, senza guard, senza `search_path`. Legge
  l'atto (`FOR UPDATE`), chiede il motivo a `vendite.fn_check_fondo_cancellabile`, e cancella righe contabili, fondo
  applicato e atto, aprendo la porta con `SET LOCAL zeroerp.allow_contabile_riga_delete_override = 'on'`. Tre chiamanti,
  ciascuno col suo permesso:
  * il BE, endpoint `ApiFondoFatturaDelete` (azione `governa_fondo_fattura`);
  * `pagamenti.fn_annulla_sistemazione` (`INVOKER`), che il BE chiama dall'endpoint `ApiSistemazioneAnnulla` (livello
    `TUTTO` sull'**area** `pagamenti`, senza oggetto, §4.5);
  * `vendite.fn_reset_fondi_fattura` (`INVOKER`), nella catena del reset del lotto (giro 1-7).
* **Il trigger**, `pagamenti.trgfn_vendite_contabili_righe_guard_contenuto`, ramo `DELETE`: la porta è un
  **interruttore** (`on`/`true`/`1`), per tutte le righe, senza il proprietario. Oggi l'app la accende e cancella
  qualunque riga sotto una distinta GENERATA o chiusa.
* **Il criterio**, `vendite.fn_check_fondo_cancellabile`: con `zeroerp.maintenance_reset_lotto_draft` accesa salta il
  controllo della figlia congelata (§3-ter.3). Oggi l'app accende quella GUC e cancella il fondo di una figlia già
  congelata, dall'endpoint o diretta.
* **Il perimetro, oggi, lo fa la RLS**: l'atto (`fatture_fondi_fattura_source`) e la sistemazione si vedono se
  l'emittente del loro `emittente_soggetto_ruolo_id` è nel perimetro; fuori rispondono `E_FONDO_NON_TROVATO` e
  `E_SISTEMAZIONE_NON_TROVATA` (no-leak). Su `vendite_contabili_righe` c'è anche la rete di scope.

### 13.2 Che cosa si cambia

1. **La primitiva**: i tre DELETE e il criterio passano a una funzione nuova, `vendite.fn_applica_cancellazione_fondo_fattura`
   (`SECURITY DEFINER`, nessun guard del permesso: la gemella di `fn_applica_user_emittenti_scope` del giro 10;
   senza `EXECUTE` all'app, in `v_fn_riservate`, D-T **b**). Rimette
   il perimetro **una volta**, sull'atto: fuori risponde `E_FONDO_NON_TROVATO`, come oggi. Accende la porta **sulla
   riga**: la GUC vale l'id dell'atto, non `on`.
2. **Il verbo pubblico**, `vendite.fn_cancella_fondo_fattura` (stessa firma: il BE non cambia): `SECURITY DEFINER`, in
   prima riga `fn_guard_azione(…, 'governa_fondo_fattura')`, spegne all'ingresso le due GUC (la porta 8 e quella del reset
   del lotto, che dentro il verbo farebbe saltare la figlia congelata), poi chiama la primitiva.
3. **`fn_annulla_sistemazione`**: `SECURITY DEFINER`, il guard del livello `TUTTO` sull'area `pagamenti` (D-U), il
   perimetro della sistemazione all'ingresso (`E_SISTEMAZIONE_NON_TROVATA`, come oggi), le due GUC spente, la primitiva
   al posto del verbo pubblico: chi annulla una sistemazione non deve avere anche `governa_fondo_fattura`.
4. **Il trigger**: il ramo `DELETE` apre se la GUC vale `OLD.fondo_source_id` **e** chi scrive è il proprietario.
5. **`fn_reset_fondi_fattura`** chiama la primitiva invece del verbo pubblico, e diventa anch'essa una primitiva chiusa:
   la chiamano solo i verbi DEFINER del reset del lotto, che nascono nello stesso giro (D-T **b**, §13.5).
6. **I pgTAP**: uno nuovo, come app (la porta con la GUC accesa dall'app: si ferma, con `on` e con l'id giusto; senza
   `governa_fondo_fattura` e senza il livello d'area: `E_PERMESSO_NEGATO`; due emittenti: l'atto e la sistemazione
   dell'altro non ci sono; la GUC del reset accesa dall'app non fa più cancellare il fondo di una figlia congelata dal
   verbo). Nasce `dbops.fn_pgtap_concedi_livello_area` (D-L **a**) e le quattro copie `pg_temp.livello_area` si ritirano
   nello stesso giro. Si adeguano `test-righe-contabili-eliminazione-v1` (il 27 apriva la porta da sé: diventa il
   controesempio) e il cleanup di `test-fondi-fattura-governo` (la porta non si apre più; lo fa il `ROLLBACK`); gli altri
   quattro che chiamano verbo o sistemazione ricevono l'azione o il livello dal builder.
7. **Le guide**: `gestione-dei-pagamenti` (il fondo e la sistemazione, chi può), `fatturazione` (il criterio),
   `architettura-permessi-e-autorizzazioni` §7.4 (il contabile esce dalle porte aperte). Il verbo è orfano: entra nel
   «Vedi anche» di `gestione-dei-pagamenti`.
8. **La richiesta al BE**: `CancellaFondoFatturaBindingTests` (§4.5, Parte C) e i test che annullano una sistemazione
   senza il livello d'area.

### 13.3 Due scelte per Tid

* **D-T, la primitiva fino al giro 1-7.** La primitiva la chiamano tre strade, e una, il reset del lotto, gira ancora
  `INVOKER` fino al giro 1-7: se la primitiva perde ora l'`EXECUTE` all'app, il reset si rompe.
  **a** la primitiva tiene l'`EXECUTE` all'app fino al giro 1-7, dichiarata come debito di un giro, col perimetro
  dentro; il giro 1-7 la mette in `v_fn_riservate`. Fino ad allora l'app può chiamarla diretta senza
  `governa_fondo_fattura` (come oggi) e con la GUC del reset accesa saltare la figlia congelata (come oggi); la porta
  del DELETE diretto si chiude subito · **b** i giri 8 e 1-7 si fanno insieme, in un giro solo. ⭐ **a**: il giro 8
  chiude subito le due strade dirette (la porta e il verbo) e non peggiora niente; la chiusura completa è il giro 1-7,
  che va comunque fatto e tocca già la primitiva.
  ✅ **Decisa da Tid il 2026-11-25: b.** Nessun debito di un giro: la primitiva nasce già chiusa, e il giro 8 si fa
  insieme al giro 1-7 (§13.5).
* **D-U, il livello sull'area senza oggetto** (§4.5-bis, punto 2). L'endpoint di `fn_annulla_sistemazione` chiede
  `TUTTO` sull'area `pagamenti`; `fn_guard_livello` vuole un oggetto, e nessun BB lo dice per la sola area.
  **a** il guard sul posto con `script.fn_resolve_livello_area` (gate di contesto e SUPER_ADMIN già dentro), stesso
  codice e stessa forma del rifiuto di `fn_guard_livello`: è la prima occorrenza, alla seconda diventa un BB
  (`fn_guard_livello_area`) · **b** si sceglie un oggetto di `pagamenti` che la sistemazione rappresenta e si passa a
  `fn_guard_livello`: cambia ciò che il BE controlla (un override d'oggetto vincerebbe sull'area), quindi va chiesto al
  BE. ⭐ **a**: è ciò che l'endpoint fa oggi, senza rifiuti nuovi.
  ✅ **Decisa da Tid il 2026-11-25: a.** Il guard sta nel verbo, con lo stesso rifiuto di `fn_guard_livello`; se nel
  giro 1-7 serve una seconda volta (il passaggio senza azione ricade sul livello dell'area `vendite`, §4.5-bis punto
  3), nasce lì il BB `fn_guard_livello_area` e il guard sul posto si ritira nello stesso giro (regola del 2).

### 13.4 Le guide (`guide_coinvolte.py --oggetti` sui sei oggetti, 2026-11-25)

* `gestione-dei-pagamenti` (la sistemazione, il guard del contenuto, l'atto, il reset): **indietro dopo il giro**,
  si aggiorna nello stesso giro.
* `fatturazione` (il criterio come predicato): **coerente** oggi; dopo il giro va detto che la GUC del reset non vale
  dai verbi pubblici.
* Orfano: `vendite.fn_cancella_fondo_fattura`, un concetto del dominio (il gesto «cancella il fondo»): entra nel «Vedi
  anche» di `gestione-dei-pagamenti`.

**Garanzie ritirate.** Nessuna: il perimetro passa dalla RLS al controllo all'ingresso con la stessa risposta; i
permessi sono quelli degli endpoint; due porte si stringono.

### 13.5 La parte 1-7 entra nel giro (D-T **b**) — analisi del 2026-11-25

Con D-T **b** il giro 8 non si scrive da solo: questa è l'analisi della parte 1-7, che prima stava solo nelle tabelle di
§4.3 e §4.5-bis. Lo sviluppo parte solo dopo le scelte di §13.7 e il via di Tid.

#### 13.5.1 Che cosa c'è oggi (catalogo di dbdev, 2026-11-25)

* **I quattro verbi d'ingresso** sono `INVOKER`, senza guard del permesso e senza `search_path`, e l'app li esegue:
  `fn_annulla_lotto_da_draft(bigint)`, `fn_riporta_lotto_a_draft(bigint)`, `fn_elimina_fattura_da_lotto(bigint, bigint)`,
  `fn_escludi_documento_da_giro(bigint, text, text)`. Il perimetro lo fa la RLS. Ognuno legge i suoi motivi da un
  criterio (`script.fn_check_lotto_annullabile`, `…_riportabile_a_draft`, `…_fattura_eliminabile_da_lotto`,
  `…_documento_escludibile_da_giro`), poi chiama la primitiva. `fn_escludi_documento_da_giro` chiama
  `fn_elimina_fattura_da_lotto` una volta per fattura del documento.
* **I due verbi del passaggio chiamano già un verbo DEFINER**: dopo la pulizia `fn_annulla_lotto_da_draft` e
  `fn_riporta_lotto_a_draft` scrivono lo stato fiscale con `vendite.fn_cambia_stato_lotto`, che è DEFINER. Quel verbo
  rimette il perimetro sul lotto (`fn_scope_ef_whitelist_via_lotto`, fuori risponde `E_LOTTO_NON_TROVATO`) e chiama
  `fn_guard_passaggio`. Il permesso del passaggio arriva quindi **dopo** la pulizia. Un rifiuto annulla tutto, perché la
  transazione è una sola, ma il lavoro si fa prima del guard. `fn_riporta_lotto_a_draft` su un lotto già in bozza non
  chiama `fn_cambia_stato_lotto`: il codice lo dice dal 2026-10-27 (`20261027-14`), «non c'è passaggio: si fa la
  pulizia e basta».
* **La matrice del lotto** (`config.stati_doc_fiscale_transizioni`, righe con `solo_fattura` falso): `DRAFT → ANNULLATA`
  manuale **senza azione** (Q-F2), `EMESSA → DRAFT` manuale con `numera_fatture_lotti` (Q-F1). Nessuna delle due ha un
  vincolo `tipo_lotto` nel `meta`.
* **La primitiva**, `vendite.fn_cleanup_fatture_by_ids(bigint[], uuid)`: `INVOKER`, l'app la esegue, a DB la chiamano
  solo i tre verbi. Accende la porta con `set_config('zeroerp.maintenance_reset_lotto_draft', 'on', true)` e **non la
  spegne**. ⚠️ Un `set_config` locale vale fino alla fine della **transazione**, non della funzione. Dopo la pulizia la
  porta resta aperta per il resto del verbo e per tutto ciò che il backend fa dopo nella stessa transazione. Dentro il
  verbo, la scrittura dello stato fiscale di `fn_cambia_stato_lotto` passa quindi con il guard di transizione del lotto
  (`trgfn_fatturazione_lotti_guard_stato`) **saltato**.
* **Il trigger delle porte 1-7: sette funzioni con la stessa lettura copiata.** Ognuna fa `current_setting(…)` e
  confronta con una lista di valori, ma le liste non sono uguali: quattro accettano anche `yes` (`guard_fatturato`,
  i due `guard_quantita_immutabile`, `fatturazione_lotti_guard_stato`, `commesse_guard_chiave_immutabile`), due no
  (`fattura_satellite_guard_congelamento`, `logs_guard_delete`). Le funzioni sono montate su dodici tabelle:
  `attivita_fatturabili` (2), `commesse`, `commesse_attivita`, `fatture`, `fatture_righe`, `fatture_indirizzi`,
  `fatture_scadenze`, `fatture_atti`, `fatturazione_lotti`, `fatturazione_lotti_log`, `fatture_log`. È la regola del 2
  già superata, e le copie hanno già cominciato a divergere.
* **Il criterio del fondo**, `fn_check_fondo_cancellabile`: con la porta del reset accesa salta il controllo della
  figlia congelata (§3-ter.3). Nella catena del reset la figlia è la fattura che si sta pulendo
  (`fn_reset_fondi_fattura` filtra `fattura_figlia_id = p_fattura_id`). I tre criteri d'ingresso la vogliono **pre-fiscale**
  (`script.fn_check_lotto_fatture_pre_fiscali`, e il criterio della fattura singola), e `DRAFT` ed `EMESSA` hanno
  `congela_fiscale` falso. Sul modello il ramo non cambia mai l'esito del reset. Apre invece la strada dell'app (§3-ter.3).
* **Il perimetro: lotto e fatture non sono legati per struttura.** `vendite.fatturazione_lotti_fatture` non ha né un
  vincolo né un trigger che chieda che la fattura sia dell'azienda del lotto. La sua RLS risolve l'emittente dal
  **lotto**, quella di `vendite.fatture` dalla **fattura**. La rete `trgfn_guard_emittente_scope` su `fatture` e
  `fatturazione_lotti` copre `INSERT` e `UPDATE`, non `DELETE`, e la pulizia è quasi tutta fatta di `DELETE`. «Le figlie
  seguono il padre» (§4.3, effetto 1) qui non è garantito dal modello.
* **Chi chiama, a DB** (corpi senza commenti e `pg_depend`): `fn_cleanup_fatture_by_ids` solo dai tre verbi;
  `fn_reset_fondi_fattura` solo dalla primitiva; `fn_check_fondo_cancellabile` solo da `fn_cancella_fondo_fattura` e da
  `fn_reset_fondi_fattura`; nessuna vista ne dipende. Dal BE nessuna delle quattro (§4.5).
* **L'utente tecnico**: nessun processo automatico raggiunge i verbi (§4.5-bis, Parte B chiusa col ritiro del task).
  Niente da dare al suo profilo.
* **I pgTAP, fatto datato del 2026-11-25** (non decide niente: ognuno si adegua per ciò che fa, non per quanti sono):
  sei aprono la porta da sé (`test-chiave-fattura-tre-specchi-v1`, `test-fondo-fattura-cancellazione`,
  `test-resolve-termini-livello-sorgente-v1`, `test-fattura-satelliti-lock-congelamento-v1`,
  `test-arrotondamento-ambito-idempotenza-v1`, `test-guard-quantita-immutabile-v1`); sette chiamano la primitiva
  diretta; una ventina chiamano i verbi.

#### 13.5.2 Che cosa si cambia

1. **I quattro verbi diventano `SECURITY DEFINER`** (`search_path` `pg_catalog, public, pg_temp`), con firma e `RETURNS`
   come al vivo: il BE non cambia. Ogni verbo spegne all'ingresso la GUC del reset (e la porta 8, D-T **b**). L'ordine
   è utente, parametri, **lotto nel perimetro** `FOR UPDATE`, **guard**, motivi, lock, primitiva.
   ⚠️ Per i due verbi del passaggio il guard non può stare nella prima riga: il permesso dipende dallo stato del lotto,
   quindi prima si legge il lotto. È lo stesso ordine di `fn_cambia_stato_lotto`. Fuori perimetro la risposta è
   `E_LOTTO_NON_TROVATO`, come oggi, prima di dire qualunque cosa sullo stato.
2. **Il guard di ognuno** (§4.5-bis):
   * `fn_elimina_fattura_da_lotto`, `fn_escludi_documento_da_giro`: `fn_guard_azione(…, 'reset_lotto_fattura_draft')`;
   * `fn_annulla_lotto_da_draft`: la riga `DRAFT → ANNULLATA` non ha azione, quindi il livello `TUTTO` sull'area `vendite`
     (D-X, §13.7);
   * `fn_riporta_lotto_a_draft`: da `EMESSA` l'azione della riga, `numera_fatture_lotti`; da `DRAFT` non c'è riga, e
     conta il livello `TUTTO` sull'area. La pulizia sul lotto già in bozza **resta** (decisione del 2026-10-27, scritta
     nel corpo del verbo; il BE la ammette): niente `E_DOC_GIA_NELLO_STATO`.
   * Il livello sull'area è la **seconda occorrenza** del guard di D-U (il primo è `fn_annulla_sistemazione`, giro 8).
     Nasce quindi il BB `script.fn_guard_livello_area(utente, area, livello)`, con lo stesso rifiuto di
     `fn_guard_livello`, e il giro 8 lo usa invece di scriverlo sul posto. Non resta nessuna copia da ritirare, perché
     il giro è uno solo.
3. **`fn_escludi_documento_da_giro` chiama il verbo pubblico** `fn_elimina_fattura_da_lotto`, come oggi: l'azione è la
   stessa, quindi un guard ripetuto per ogni fattura non nega niente di nuovo e non serve una primitiva in più.
4. **Il perimetro** si controlla sul lotto, e sulle fatture che il verbo tocca (D-Y, §13.7).
5. **La porta 1-7.** La lettura passa a un BB, `vendite.fn_porta_reset_lotto_aperta(p_tabella regclass)`: GUC accesa
   **e** `fn_is_proprietario_tabella(p_tabella)`. Le sette funzioni di trigger chiamano il BB, e le sette copie si
   ritirano nello stesso giro, compresa la divergenza su `yes`. La primitiva accende la GUC e la **spegne prima di
   uscire**: la porta resta aperta solo mentre la pulizia lavora. Così dopo la pulizia il guard di transizione giudica
   anche lo stato scritto da `fn_cambia_stato_lotto`. Le due righe sono ammesse, senza vincolo di `tipo_lotto`, e il
   fermo non si applica (`ANNULLATA` è abortito, `DRAFT` non congela). Che cosa porta la GUC (un interruttore o l'id
   della riga) è la D-W (§13.7).
6. **Le primitive chiuse** (`v_fn_riservate`, nelle tre sedi di §11.8): `fn_cleanup_fatture_by_ids`,
   `fn_reset_fondi_fattura`, `fn_applica_cancellazione_fondo_fattura` (§13.2) ~~e `fn_check_fondo_cancellabile`~~.
   ⚠️ Corretto scrivendo il giro (2026-11-25): il criterio **resta eseguibile**. Legge soltanto, e senza il ramo della
   GUC (D-Z a) non apre niente; chiuderlo non stringeva nessuna porta e rompeva i pgTAP che lo provano diretti.
   Nessuna delle tre ha un chiamante dal BE, né una vista che dipenda da lei. `fn_libera_attivita_fatturabili` e
   `fn_riporta_attivita_da_emettere` restano eseguibili: scrivono `attivita_fatturabili`, la cui porta, chiusa,
   ferma l'app. La seconda non ha chiamanti a DB, e la richiesta al BE chiede se ne ha dal BE.
7. **Il criterio del fondo**: il ramo della GUC del reset (D-Z, §13.7).
8. **I pgTAP**: un pgTAP nuovo, come app, per la parte 1-7. Prova la porta (la GUC accesa dall'app e una scrittura
   diretta su una tabella per funzione di trigger: si ferma), i quattro verbi senza il permesso (`E_PERMESSO_NEGATO`; per
   `fn_riporta_lotto_a_draft` sia da `EMESSA` senza `numera_fatture_lotti`, sia da `DRAFT` senza il livello d'area), due
   emittenti (il lotto dell'altro: `E_LOTTO_NON_TROVATO`, niente toccato), la GUC spenta dopo la pulizia e dopo il verbo,
   e il passaggio giudicato dal guard di transizione. Il builder `dbops.fn_pgtap_concedi_livello_area` di D-L nasce
   qui, e le quattro copie `pg_temp.livello_area` si ritirano. I pgTAP che aprono la porta da sé diventano controesempi,
   oppure passano dal verbo o dal seed. Quelli che chiamano la primitiva diretta passano dal verbo. Quelli che chiamano
   i verbi ricevono l'azione o il livello dal builder.
9. **Le guide** (§13.6) e **la richiesta al BE** (§13.8), una sola per tutto il giro 8 + 1-7.

### 13.6 Le guide (`guide_coinvolte.py --oggetti` sui quindici oggetti, 2026-11-25)

* `fatturazione` (`fn_annulla_lotto_da_draft`, `fn_check_fondo_cancellabile`, e nel testo `fn_riporta_lotto_a_draft`):
  **indietro dopo il giro**, e si aggiorna nello stesso giro. Descrive bene **che cosa** fa il reset, ma non chi può
  farlo: l'annullo col livello sull'area, il ritorno in bozza con `numera_fatture_lotti` da `EMESSA`, «togli» ed «escludi»
  con `reset_lotto_fattura_draft`. Non dice nemmeno che la porta del reset si apre solo dentro la pulizia. I tre verbi
  orfani (`fn_riporta_lotto_a_draft`, `fn_elimina_fattura_da_lotto`, `fn_escludi_documento_da_giro`) sono gesti del
  dominio: il «Vedi anche» è incompleto e li prende.
* `gestione-dei-pagamenti` (`fn_reset_fondi_fattura`): **coerente**; con D-Z **a** si toglie la riga sul bypass, se la
  guida la nomina (insieme a §13.4).
* `modello-documento-di-vendita` (`fn_guard_passaggio`): con D-X **a**, **indietro su un punto**. «Una riga senza azione
  chiede solo il permesso sul documento» resta vero. Va aggiunto che per il lotto quel permesso lo rifà anche il verbo,
  perché il verbo DEFINER non ha più la RLS dietro. Con D-X **b**, **contraddetta**: è un cambio di modello del
  passaggio.
* `architettura-permessi-e-autorizzazioni` §7.4: **indietro** dopo il giro. Il reset dei lotti esce dalle porte aperte e,
  insieme al contabile (§13.4), non resta nessuna porta del flusso con la sola GUC.
* Orfani: le sette funzioni di trigger della porta sono dettagli interni, e non serve una guida.

**Garanzie ritirate.** Nessuna sulle regole: le porte si stringono e i permessi sono quelli degli endpoint. Un fatto da
censire nel giro: dentro un verbo DEFINER `current_user` è il proprietario. Le colonne che i verbi timbrano con
`current_user` (`user_update` del lotto, `user_insert` dei log del fondo) diranno `zeroerp_owner` invece di `zeroerp_app`,
come in ogni verbo DEFINER di oggi (`fn_cambia_stato_lotto`, magazzino). Il giro cerca a DB chi legge quelle colonne
aspettandosi il ruolo dell'app, e la richiesta al BE chiede lo stesso.
✅ **Censimento a DB, 2026-11-25** (corpi senza commenti e viste, sul catalogo di dbdev): un solo lettore che confronta
quelle colonne, `dbops.fn_run_automations_seed_primo_impianto`, che riconosce come seed le righe con `user_insert` del
migratore. **Non ne dipende**: guarda solo le tabelle iscritte al seed di primo impianto
(`dbops.automazione_seed_primo_impianto`), e nessuna è scritta dai verbi del giro (lotti, fatture, log, fondi,
sistemazioni, righe contabili). Nessuna vista le confronta.

### 13.7 Quattro scelte per Tid

✅ **Decise da Tid il 2026-11-25: D-W a, D-X a, D-Y a, D-Z a.** Lo sviluppo non parte: aspetta il via.

* **D-W, che cosa porta la GUC del reset.** Con D-A **a** il piano vuole la GUC «sulla riga» in ogni porta (D-B decaduta,
  2026-11-23). Le sette funzioni di trigger della porta stanno però su dodici tabelle, e ognuna avrebbe la sua regola
  per risalire dalla riga alla fattura o al lotto: la fattura per i satelliti, `fattura_riga_id` o `lock_batch_id` per le attività, la commessa per le altre.
  In più la pulizia cancella il legame lotto ↔ fattura **prima** della fattura.
  **a** la GUC resta un interruttore, ma la porta apre solo col proprietario (il BB del punto 5) e per la sola durata
  della pulizia (la primitiva la spegne prima di uscire). Si scrive come eccezione dichiarata al «sulla riga» di D-A,
  e il motivo è che la porta la tiene il proprietario dentro una primitiva chiusa · **b** la GUC porta l'id del lotto,
  o l'elenco delle fatture, e ognuna delle sette funzioni di trigger risale dalla sua riga al lotto: sette regole
  nuove, e quella delle fatture va scritta prima che il legame sparisca.
  ⭐ **a**. «Sulla riga» serviva a limitare ciò che una porta aperta lascia passare. Qui la porta la apre solo il
  proprietario, solo dentro la primitiva, e si richiude prima che il verbo vada avanti: le sole scritture che vede sono
  quelle della pulizia. **b** aggiunge sette regole di risalita senza chiudere una strada in più.
  ✅ **Decisa da Tid il 2026-11-25: a.** È un'eccezione dichiarata al «sulla riga» di D-A, per la sola porta 1-7: la
  guida dei permessi §7.4 e `fatturazione` lo scrivono nel giro.
* **D-X, il passaggio senza azione** (§4.5-bis punto 3). Il BE, quando la riga non ha azione, ricade sul livello `TUTTO`
  dell'area `vendite`. `fn_guard_passaggio` invece passa («il permesso lo controlla il backend»).
  **a** la ricaduta si fa nei due verbi del lotto, col BB `fn_guard_livello_area` del punto 2 · **b** la ricaduta entra
  in `fn_guard_passaggio`, quindi vale per tutti i verbi di passaggio di tutti i documenti. È un cambio del modello del
  passaggio (Q-F2 di `work-done/2026/brief-modello-documento-vendita`, 2026-10-27; guida del modello §«L'azione si
  dichiara sulla riga»), e ogni verbo deve dire quale area chiede.
  ⭐ **a**: è ciò che fa l'endpoint, senza rifiuti nuovi e dentro il giro. **b** resta una domanda vera e va segnalata.
  Tutti i verbi di passaggio sono DEFINER, quindi una riga senza azione oggi non chiede niente a DB su nessun
  documento. È un tema trasversale e lo apre Tid, se vuole, fuori da questo brief.
  ✅ **Decisa da Tid il 2026-11-25: a.** La ricaduta sta nei due verbi del lotto, col BB `fn_guard_livello_area`.
  La strada **b** non è aperta qui.
* **D-Y, il perimetro delle fatture del lotto.** Il modello non lega la fattura all'azienda del lotto (§13.5.1), quindi
  controllare il solo lotto lascia aperta la fattura d'altri dentro un lotto proprio.
  **a** il verbo controlla il lotto e **ogni fattura che tocca**. `fn_elimina_fattura_da_lotto` controlla il lotto e la
  fattura (`fn_scope_ef_whitelist_via_fattura`); annullo e ritorno in bozza controllano il lotto e, con una sola query,
  tutte le sue fatture. Una fattura fuori perimetro risponde `E_LOTTO_NON_TROVATO`, fail-closed, senza dire che cosa
  c'è · **b** la regola diventa di struttura: un guard su `fatturazione_lotti_fatture` rifiuta la fattura d'un'altra
  azienda, e poi basta il lotto. È un cambio di modello che tocca chi scrive quel legame (la pipeline), quindi è un
  altro giro.
  ⭐ **a**: chiude il caso dentro il giro, con una query sola all'ingresso. **b** si può aprire dopo, e allora il
  controllo sulle fatture diventa ridondante ma non sbagliato.
  ✅ **Decisa da Tid il 2026-11-25: a.**
* **D-Z, il ramo della GUC nel criterio del fondo.** **a** si toglie: nel reset la figlia è la fattura che si pulisce,
  e i criteri d'ingresso la vogliono pre-fiscale, cioè non congelata. Il ramo non serve al reset e apre la strada
  dell'app. Il criterio resta uno solo per il reset e per il gesto, quindi il controllo si fa più stretto e non più
  largo · **b** resta, letto col BB della porta (quindi solo dal proprietario).
  ⭐ **a**: la ragione sta sul modello (la figlia di un reset è pre-fiscale per costruzione), non sul fatto che il caso
  oggi non capiti. Se un giorno il reset toccasse una figlia congelata, il fondo resterebbe e il log lo direbbe
  (`W_FONDO_FIGLIA_CONGELATA`). È il comportamento fail-closed che il criterio ha già per il gesto.
  ✅ **Decisa da Tid il 2026-11-25: a.** Il ramo si toglie, e il criterio non legge più la GUC del reset.

### 13.8 La richiesta al team BE/FE (dopo l'apply, una sola per il giro 8 + 1-7)

Si scrive nel giro, insieme a quella di §13.2 punto 8. Il contenuto:

* **Chi cambia per primo**: il DB. Nessuna firma cambia, nessuna GUC da togliere (§4.2).
* **I test che chiamano uno dei quattro verbi a DB reale** senza il permesso dell'endpoint ricevono `E_PERMESSO_NEGATO`
  (§4.5, Parte C: lo smoke `smoke-ritorno-lotto-a-draft.py` è SUPER_ADMIN e passa). La ricerca si fa sul nome, non su
  un elenco chiuso.
* **Il perimetro**: un lotto o una fattura di un'altra azienda risponde `E_LOTTO_NON_TROVATO`, come prima (il 404 non
  cambia).
* **`fn_riporta_attivita_da_emettere`**: se il BE la chiama, e da dove (a DB non ha chiamanti).
* **I lettori di `user_update` e `user_insert`** delle tabelle che i verbi scrivono, se qualcuno conta che valgano
  `zeroerp_app` (§13.6, «Garanzie ritirate»).
* **I manuali BE** degli endpoint del lotto, se raccontano chi può annullare, riportare in bozza, togliere o escludere.
  Uno già noto: `docs/it/backend/vendite/manual/api_fondi_fattura.md` (riga 116, 2026-11-25) descrive la cancellazione
  del fondo col meccanismo di prima. La ricerca resta del tema, non di un elenco chiuso.

### 13.9 Il giro scritto — 2026-11-25

Range `20261125-01` … `-30` dato da Tid. ⚠️ L'altra sessione DB ha preso `-23`, `-24` e `-25` dentro il range mentre
il giro si scriveva: qui `-01` … `-22` e `-26`; `-27` … `-30` liberati.

| File | Che cosa |
| --- | --- |
| `20_code/script/20261125-01-create-fn-guard-livello-area` | BB nuovo: il livello minimo su un'area, senza oggetto; gemello di `fn_guard_livello`, stesso rifiuto. Seconda occorrenza di D-U: lo usano la sistemazione e il passaggio del lotto |
| `20_code/vendite/20261125-02-create-fn-porta-reset-lotto-aperta` | BB nuovo: la porta del reset, GUC accesa **e** proprietario (D-W a: interruttore) |
| `20_code/vendite/20261125-03` … `-09` | le sette funzioni di trigger leggono la porta dal BB; le sette copie della lettura si ritirano, con la divergenza su `yes` |
| `20_code/vendite/20261125-10-update-fn-check-fondo-cancellabile-senza-porta-reset` | D-Z a: il ramo della GUC tolto; resta eseguibile |
| `20_code/vendite/20261125-11-create-fn-applica-cancellazione-fondo-fattura` | la primitiva del fondo: il corpo di prima, DEFINER, perimetro sull'atto, porta delle righe contabili sulla riga |
| `20_code/vendite/20261125-12-update-fn-cancella-fondo-fattura-definer-guard` | il verbo pubblico: DEFINER, `governa_fondo_fattura`, GUC spente, la primitiva |
| `20_code/pagamenti/20261125-13-update-trgfn-vendite-contabili-righe-guard-contenuto-porta-sulla-riga` | la porta 8: GUC = `OLD.fondo_source_id` **e** proprietario |
| `20_code/pagamenti/20261125-14-update-fn-annulla-sistemazione-definer-guard-perimetro` | DEFINER, TUTTO sull'area `pagamenti`, perimetro sull'atto, il fondo dalla primitiva |
| `20_code/vendite/20261125-15-update-fn-reset-fondi-fattura-dalla-primitiva` | i resettabili dalla primitiva |
| `20_code/vendite/20261125-16-update-fn-cleanup-fatture-by-ids-porta-solo-nella-pulizia` | la GUC si spegne prima di uscire |
| `20_code/vendite/20261125-17` … `-20` | i quattro verbi DEFINER: permesso, perimetro su lotto e fatture (D-Y a), GUC spente |
| `20_code/vendite/20261125-21-create-fn-guard-passaggio-lotto` | BB nuovo: l'azione della riga del passaggio, o TUTTO sull'area `vendite` (D-X a). La stessa regola nei due verbi del passaggio è la seconda occorrenza: locale al lotto, `fn_guard_passaggio` non cambia |
| `90_end/20261125-22-revoke-primitive-del-reset-e-del-fondo` | le tre primitive riservate; le altre due sedi di §11.8: `v_fn_riservate` del loop `20260205-41` e il provisioning |
| `20_code/dbops/20261125-26-create-fn-pgtap-concedi-livello-area` | D-L a: il builder del livello d'area; le quattro copie `pg_temp.livello_area` ritirate |
| `db/pgtap/vendite/test-porta-reset-lotto-e-fondo-v1.sql` | nuovo, come app, plan 23: forma, la porta (il BB, un `DELETE` diretto del log, il criterio su chi legge e chi accende la GUC), il permesso dei quattro verbi e del passaggio, due emittenti su lotto, atto e sistemazione, l'annullo col permesso e la GUC vuota dopo |

**Precisazioni scrivendo.** Una fattura fuori perimetro in «togli la fattura» risponde `E_FATTURA_NON_TROVATA`, la
risposta del criterio per la fattura che non esiste (D-Y a diceva `E_LOTTO_NON_TROVATO` in generale). Firme e risultati
dei nove oggetti vivi identici al vivo (prova delle firme, 18/18); `%TYPE` in firma, `RETURNS`, `DECLARE`, `COMMENT` e
`DROP` dove c'è la colonna (anche `v_tipo_lotto` del guard di stato).

**I pgTAP esistenti.** Quarantotto nominano verbi, primitive, criterio o GUC: provati uno per uno senza e con
l'estratto (fatto datato del 2026-11-25). Tredici cambiavano esito da owner: ricevono il permesso dell'endpoint dai
builder (`fn_pgtap_concedi_azione`, `fn_pgtap_concedi_livello_area`); `test-fondo-fattura-cancellazione` 11 diventa il
controesempio di D-Z; `test-righe-contabili-eliminazione-v1` 27 il controesempio della porta 8; il cleanup di
`test-fondi-fattura-governo` lascia il lavoro al `ROLLBACK` (plan 29); `test-cleanup-fattura-copertura-figlie-v1`
legge anche la primitiva; `test-reset-fattura-plafond-consumato-v1` 9 asserisce il `42501` della pulizia chiamata
dall'app. ✅ **Decisione di Tid, 2026-11-25: runner owner** per i file che, come app, usano strade che il giro chiude
(marcatore `pgtap-runner: owner` col motivo): la pulizia o il reset dei fondi chiamati diretti
(`test-billing-account-guard-parent`, `test-vw-dash-competenza-v1`, `test-annullo-commessa-rettifica-v1`,
`test-annulla-accredito-riga-reso-v1`, `test-fondi-fattura`, `test-fondo-fattura-eseguito`; già owner
`test-af-emessa-non-lockata-reset-e-riporto-v1`), il ramo della porta aperta (`test-guard-quantita-immutabile-v1`,
`test-fattura-satelliti-lock-congelamento-v1`), la fixture che cambia il termine di una commessa con attività
(`test-resolve-termini-livello-sorgente-v1`, `test-chiave-fattura-tre-specchi-v1`,
`test-arrotondamento-ambito-idempotenza-v1`). Il lato app lo prova il pgTAP nuovo.

**La prova sullo scratch** (`prova_changeset.py`, owner, `ROLLBACK`; 2026-11-25): i ventitré changeSet insieme, estratto
per intero, catalogo identico dopo. I quarantotto pgTAP e i quattro del builder: con l'estratto stesso esito di prima o
verdi, salvo i rossi da owner per costruzione: `test-porta-reset-lotto-e-fondo-v1` 3, 7, 8 (20/23),
`test-reset-fattura-plafond-consumato-v1` 9; quelli già rossi da owner prima (`test-chiudi-legame-con-prezzi-v1` 11,
`test-lotto-dell-azienda-v1` 6 e 9) invariati. Presidi trasversali (`comment-al-presente`, `riferimenti-morti`,
`security-definer-search-path`, `app-definer-dichiarate`, catalogo dei messaggi, `fn-utente-di-sessione`,
`permessi-trigger-guard-emittente`) invariati. Pre-commit sui file del giro: verde. ⚠️ La preCondition del `-22`
(«tre funzioni») sullo scratch legge due, perché si valuta prima dell'estratto: al migrate la primitiva c'è già.

⚠️ **La porta si prova sul BB, non funzione per funzione.** §13.5.2 punto 8 chiedeva una scrittura diretta per ogni
funzione di trigger. Il pgTAP nuovo prova la porta col BB (7), con una scrittura diretta sul log del lotto (8) e col
criterio sul codice (5-6: la GUC la legge solo il BB, la accende solo la pulizia). Le sette funzioni leggono la porta
solo dal BB, quindi un caso per funzione proverebbe sette volte la stessa riga. Il ramo «da proprietario passa» lo
provano i test marcati owner.

**Guide e `manual/`** (2026-11-25): cinque pagine nuove (la primitiva, il BB della porta, il guard del passaggio, il guard
d'area, il builder), venti aggiornate, altre sette con la frase stantia sulla porta o sul verbo del fondo
(`vendite_contabili_righe`, `fn_porta_manutenzione_aperta`, i due log, `fn_libera_attivita_fatturabili`,
`fn_riporta_attivita_da_emettere`, `trgfn_commesse_attivita_guard_prezzo_rettifica`). Le guide: `fatturazione` (chi
esce da un lotto, la porta del reset), `gestione-dei-pagamenti` (chi cancella un fondo e annulla una sistemazione),
`architettura-permessi-e-autorizzazioni` §7.4 e §10 (nessuna porta del flusso resta con la sola GUC; la porta del reset
come eccezione dichiarata), `modello-documento-di-vendita` (il lotto rifà il permesso sul documento),
`pgtap-come-si-scrive-un-test` (il builder). Esiti di §13.6: tutte e quattro **aggiornate** nel giro.

✅ **Applicato da Tid il 2026-11-25** (17:14, `databasechangelog` di dbdev: `-01` … `-21`, `-26`, poi `-22`), con la
doc auto-generata rigenerata. ✅ **pgTAP del giro come app verdi** (Tid, 2026-11-25): il nuovo, i tredici adeguati,
i dodici a runner owner, i quattro del builder. ✅ **Doc auto-generata rigenerata** una seconda volta, dopo le pagine
`manual/` (gli indici prendono il primo paragrafo dello Scopo). Restano il commit e la richiesta al BE (§13.8).

## Registro

| Data | Chi | Che cosa |
| --- | --- | --- |
| 2026-11-25 | DB | Commit su `dev/db-tid`: R-DB-K1 e R-DB-K4 (§4.9.6); al BE il passo 3j (§4.9.7) |
| 2026-11-25 | Tid | R-DB-K1 e R-DB-K4 applicati, pgTAP come app e `test-crea-primo-amministratore-v1` su dbdev verdi, doc auto-generata rigenerata (§4.9.6) |
| 2026-11-25 | DB | R-DB-K1 e R-DB-K4 scritti (§4.9.6): `20261125-30` (il BB degli indirizzi dell'operatore, regola del 2), `-31` (la madre dal BB), `-32` (il verbo), `E_PRIMO_AMMINISTRATORE_GIA_PRESENTE` (CONFLITTO_STATO, id 1539), i due seed di `tid` tolti, pgTAP nuovo 18/18 e `test-character-n` adeguato, guide e `manual/`. Trovati dalla prova: il PR pretende residenza e domicilio fiscale (il verbo li riceve in jsonb); lo scratch ha zero legami SUPER_ADMIN. La postcondizione di §4.9.2 non entra. Da applicare |
| 2026-11-25 | Tid | **D-K7 decisa: b** (il verbo si apre solo senza nessun legame SUPER_ADMIN) · **D-K8 decisa: a2** (i due seed di `tid` si tolgono) · il via, numeri `-30` … `-32` e id 1539 |
| 2026-11-25 | DB | R-DB-K1 e R-DB-K4, analisi (§4.9): il verbo DEFINER senza guard, chiuso dalla condizione e serializzato col lock sui legami; D-K7 (la condizione: proposta **b**, nessun legame SUPER_ADMIN, perché «nessuno senza scadenza» si riapre all'app sugli stati scoperti della nota `_ultimo-super-admin`); D-K8 (il ritiro dei due seed: proposta **a2**). Trovati: `20260309-01` non registrato da zero (la sua `preCondition` legge una tabella ritirata, `failOnError: false`), l'euristica di `20260419-95` che appoggia il SUPER_ADMIN sul soggetto di un altro dipendente. Nessun changeSet: si aspetta il via |
| 2026-11-25 | DB | Commit `e4bf00af69` e push su `dev/db-tid`: il giro 8 + 1-7 (i changeSet `-23` … `-25` e le modifiche anagrafiche dell'altra sessione esclusi) |
| 2026-11-25 | Tid | Giro 8 + 1-7: pgTAP come app verdi, doc auto-generata rigenerata dopo le pagine `manual/` (§13.9); al BE il 6e-septies (§13.8). Sul lato DB i giri delle porte del flusso sono chiusi tutti |
| 2026-11-25 | DB | Giro 8 + 1-7: guide e `manual/` (cinque nuove, ventisette aggiornate, cinque guide); trovato l'apply di Tid (17:14) sul `databasechangelog`; §13.9 chiusa con la copertura della porta dichiarata |
| 2026-11-25 | DB | Giro 8 + 1-7 scritto e provato (§13.9): `20261125-01` … `-22` e `-26`; pgTAP nuovo, tredici adeguati, dodici a runner owner (scelta di Tid), quattro copie `pg_temp.livello_area` ritirate; il criterio del fondo resta eseguibile (§13.5.2 punto 6 corretto); range: `-23` … `-25` presi dall'altra sessione |
| 2026-11-25 | Tid | Il via al giro 8 + 1-7; i pgTAP che usano le strade chiuse all'app vanno a runner owner |
| 2026-11-25 | Tid | Giro 8 + 1-7: **D-W a** (interruttore col proprietario, vivo solo nella pulizia), **D-X a** (la ricaduta sul livello d'area nei due verbi del lotto), **D-Y a** (il perimetro sul lotto e su ogni fattura toccata), **D-Z a** (il ramo della GUC nel criterio del fondo si toglie) (§13.7). Lo sviluppo non parte: aspetta il via |
| 2026-11-25 | DB | Giro 8 + 1-7, analisi della parte 1-7 (§13.5-§13.8): quattro verbi DEFINER col lotto nel perimetro prima del guard; trovato che la GUC del reset resta accesa fino alla fine della transazione (il guard di transizione del lotto oggi non giudica gli stati del reset), che le sette letture della porta divergono (`yes`), che lotto e fatture non sono legati per struttura alla stessa azienda e che il ramo della GUC nel criterio del fondo non serve al reset; il BB `fn_guard_livello_area` nasce qui (seconda occorrenza di D-U); D-W, D-X, D-Y, D-Z a Tid |
| 2026-11-25 | Tid | Giro 8: D-T **b** (i giri 8 e 1-7 in un giro solo, la primitiva del fondo nasce chiusa) e D-U **a** (il guard del livello d'area sul posto). Brief aggiornato: piano fuso, §13.3 chiusa, §13.5 l'analisi della parte 1-7 da fare; lo sviluppo non parte |
| 2026-11-25 | DB | Giro 8, analisi (§13): D10-D11 rilette; primitiva DEFINER dei tre DELETE col perimetro sull'atto e la porta sulla riga, verbo pubblico col guard di `governa_fondo_fattura`, `fn_annulla_sistemazione` DEFINER col livello d'area, la GUC del reset spenta dai verbi pubblici; D-T e D-U a Tid. Ordine deciso da Tid: giro 8, poi K1 e K4 insieme |
| 2026-11-25 | Tid | Giro 11 e `20261124-12` applicati, pgTAP come app verdi, doc auto-generata rigenerata (§12.5, §12.7); al BE il 6d-quinquies |
| 2026-11-25 | DB | `20261124-12` scritto e provato (§12.7): il blocco `EXCEPTION` ridondante tolto da `fn_posta_riga_tardiva`, decisione di Tid; manuale allineato |
| 2026-11-25 | DB | Giro 11 analizzato e scritto (§12): `20261124-10` (la porta col proprietario), `-11` (il verbo DEFINER col livello `TUTTO` su `vendite.reso` e il perimetro del reso all'ingresso); pgTAP nuovo, i ventuno esistenti invariati; guide `gestione-ddt` e §7.4 dei permessi, `manual/`; provato sullo scratch; richiesta al BE (§12.6). Trovato che il blocco `EXCEPTION` del giro 9 è ridondante (a Tid) |
| 2026-11-25 | DB | Commit e push su `dev/db-tid`: giro 9 (§11.5) |
| 2026-11-25 | Tid | Giro 9 applicato, pgTAP come app verdi dopo la correzione del test 9 (la riga di B letta nel contesto di B), doc auto-generata rigenerata (§11.5); al BE il 6c-quinquies |
| 2026-11-25 | DB | Giro 9 scritto e provato (§11.5): `20261124-07` (la porta col proprietario), `-08` (il verbo DEFINER col guard di `registra_distinta` e il perimetro all'ingresso), `-09` (D-S a, il guard di scope del movimento dopo il mirror); pgTAP nuovo, quattro adeguati, guida `gestione-dei-pagamenti` e `manual/`; richiesta al BE (§11.6) |
| 2026-11-25 | Tid | **D-S a** (§11.3) e il via al giro 9 |
| 2026-11-25 | DB | Giro 9, analisi (§11): D20-b riletta; verbo DEFINER col guard di `registra_distinta`, il perimetro della distinta all'ingresso (oggi lo dava la RLS), la fattura controllata; trovato il guard di scope del movimento che gira prima del mirror (muto dentro una DEFINER); D-S a Tid |
| 2026-11-25 | DB | Commit e push su `dev/db-tid`: giro 10 (§10.5), col giro 16 già committato |
| 2026-11-25 | Tid | Giro 10 applicato, pgTAP come app verdi, doc auto-generata rigenerata (§10.5); al BE il 6b-quinquies |
| 2026-11-25 | DB | Giro 10 scritto e provato (§10.5): `20261124-01` (la primitiva, GUC sull'`auth_user_id`), `-02` (il verbo DEFINER col guard del SUPER_ADMIN), `-03` (il provisioning dalla primitiva), `-04` (la porta: GUC sulla riga e proprietario), `-05` (il builder dei pgTAP), `-06` e le altre due sedi (la primitiva riservata); pgTAP nuovo, ventiquattro adeguati, guide e `manual/`; richiesta al BE (§10.6); giro 10-bis nel piano |
| 2026-11-24 | Tid | **D-O a, D-P a, D-Q a** (§10.3) e il via al giro 10 |
| 2026-11-24 | DB | Giro 10, analisi (§10): verbo DEFINER con `fn_guard_super_admin`, GUC sull'`auth_user_id`, nessun perimetro; l'`INSERT` diretto dell'app dà un'azienda senza guard; il provisioning chiama il verbo senza utente; dodici pgTAP aprono la porta da sé. D-O, D-P e D-Q a Tid |
| 2026-11-24 | Tid | Giro 16 applicato, pgTAP come app verdi (§9.4); al BE il 6a-quinquies |
| 2026-11-24 | DB | Giro 16 scritto e provato (§9.4): `20261123-98` (la porta: GUC sull'id del modello e proprietario; il seed dalla sessione del migratore), `-99` (il verbo DEFINER col guard), pgTAP nuovo, quattordici adeguati, guide e `manual/`; richiesta al BE (§9.5) |
| 2026-11-24 | Tid | **D-M a, D-N a** (§9.3) e il via al giro 16 |
| 2026-11-24 | DB | Giro 16, analisi (§9): verbo DEFINER col guard di `documenti_template_manage`, GUC sull'id del modello, il seed riconosciuto dalla sessione del migratore; undici pgTAP da dare l'azione; D-M e D-N a Tid |
| 2026-11-24 | Tid | **D-L decisa: a** (§4.5-bis): il builder del livello d'area nasce nel primo giro che lo usa, le quattro copie si ritirano lì |
| 2026-11-24 | DB | Passo 3e: la risposta 3d letta (§4.5-bis). Guard di ogni porta coi BB che ci sono, §4.3 corretta (porta 11 sul livello di `vendite.reso`, non `conferma_reso`), Parte B chiusa, builder dei test della Parte C; D-L a Tid; due punti per i giri 8 e 1-7 |
| 2026-11-24 | Tid | R-DB-I3 applicata, pgTAP come app verde (§4.8); al BE il passo 3n |
| 2026-11-24 | DB | R-DB-I3 scritta (§4.8, scelte di Tid: decisione intera, colonna): `distruttivo` sul registro, `auto_step_rollback` colonna con il `CHECK` sul `meta`, `fn_check_rollback_step_automatico`, pgTAP 14/14 sullo scratch, guida `fatturazione` e `manual/`; garanzia ritirata e richiesta al BE (3n) |
| 2026-11-24 | DB | ⚠️ R-DB-K3 ripristinata: il commit `359c556da1` della sessione anagrafiche aveva riscritto `codici_errore.csv` e `messaggi_errore.csv` dalla sua copia, senza le righe di K3 (il DB applicato le aveva già). Riapplicate le stesse sostituzioni, CSV controllati |
| 2026-11-24 | Tid | R-DB-K3 applicata, pgTAP verde (§4.7); al BE il passo 3k-bis |
| 2026-11-24 | DB | R-DB-K3 scritta (§4.7): `note`, causa e soluzione di `E_SCOPE_SENZA_UTENTE` coi due casi, il `messaggio` resta del trigger; corretta la `note` di `E_UI_CHIAMATA_NON_VALIDA`; al BE la rigenerazione di `error_policies_generated.py` (passo 3k-bis) |
| 2026-11-24 | DB (sessione anagrafiche) | §2: le porte che passano da `fn_porta_manutenzione_aperta`, lucchetti di colonna compresi, dichiarate fuori dal censimento a ragione (chiuse per l'app dal 2026-11-17); nessuna porta nuova |
| 2026-11-24 | BE | BB `utente_per_id` estratto (regola del 2, ok Tid, §4.7): sette sedi, il rifiuto resta del chiamante; presidio di sede unica |
| 2026-11-24 | BE | D-K5 **a**, D-K6 **a**, D-I.4 **a** (Tid) fatte (§4.7, §4.8): resolver sul BB dello scope, utente tecnico al motore documentale (ramo senza filtro di `get_fattura_testata` ritirato, `build_context` senza default), `auto_step_rollback` dalla pipeline; test provati a rovescio, uno sul DB vero; nota per R-DB-I3 sul patto del `jsonb` |
| 2026-11-24 | `/verifica` | §4.7: copia importata di `fetch_emittenti_scope_ids` in pagamenti (presidio nuovo), commenti e ripiego di `E_SCOPE_SENZA_UTENTE` allineati, gate dei prezzi fra i dichiarati; D-K5 e D-K6 a Tid · §4.8: verso del rollback nel diario riscritto (due test), manuali BE; D-I.4 a Tid |
| 2026-11-24 | Tid | **D-I.3 decisa: a** (§4.8): il flag «distruttivo, mai in auto-run» lo dichiara il DB; R-DB-I3 al DB (passo 3m), poi il runner (passo 3n) |
| 2026-11-24 | BE | Lato BE del ritiro di `reset_lotto_draft` fatto (§4.8): whitelist, handler, esclusione del runner tolta (ok Tid), test (il test 8 del runner provato a rovescio), manuali BE; 138 verdi con il guardrail sul DB vero. D-I.3 al DB (passo 3m) |
| 2026-11-24 | BE | `/arrivi-db` del ritiro di `reset_lotto_draft`: merge di `origin/dev/db-tid` sul ramo del BE, Registro fuso, testata riallineata (R-DB-K3/K4 nel «Riparte», «Da committare»); guardrail `test_pipeline_task_handler_guardrail` verde su dbdev |
| 2026-11-24 | `/verifica` | §4.7: R-DB-K4 al DB, i due changeSet che danno il SUPER_ADMIN a `auth_user id=1` (seconda strada rispetto a R-DB-K1, id cablati) |
| 2026-11-24 | `/verifica` | §4.7: tolto il default `None` da tre letture della fattura (arrivavano al ramo senza filtro di `get_fattura_testata`), da `fn_lotti_mensile` e dalle code dei resi; presidio sulle firme; guida dei permessi §6.3 allineata |
| 2026-11-24 | BE | Il `None` del perimetro si rifiuta (§4.7, ok Tid): tool AI contratti corretto, `E_SCOPE_SENZA_UTENTE` dal BB `fetch_emittenti_scope_ids`, liste di vendite senza default `None`; un solo `None` dichiarato (`get_fattura_testata`, motore documentale); R-DB-K3 al DB |
| 2026-11-24 | DB | Commit e push su `dev/db-tid`: il lato DB del ritiro di `reset_lotto_draft` e la pulizia della testata; al BE il suo lato (§4.8) |
| 2026-11-24 | Tid | `20261123-67` applicato su dbdev, `test-pipeline-processi-invariante-v1` verde 9/9 |
| 2026-11-24 | DB | Ritiro di `reset_lotto_draft` scritto (§4.8): quattro CSV, `DELETE` `20261123-67`, invariante test 8-9 sul `rollback`, guida `fatturazione` e manuali di `fatturazione_pipeline`, `pipeline_task_registry` e `azioni_processo`; provato sullo scratch (controesempio 7/9, stato finale 9/9). Da applicare |
| 2026-11-24 | Tid | **D-I.1 a** (il task si cancella) · **D-I.2 a** (l'azione spenta non si tocca); via allo sviluppo |
| 2026-11-24 | DB | Richiesta del BE sul ritiro di `reset_lotto_draft` analizzata (§4.8): righe e FK verificate su dbdev, nessuna corsa né figlia dell'azione; il presidio dell'invariante non guarda il `rollback`; D-I.1 e D-I.2 proposte a Tid; guida `fatturazione` e manuale di `fatturazione_pipeline` indietro |
| 2026-11-24 | DB | Testata e Registro ripuliti dopo il merge del BE (`4271a0dc69`): tolte le righe 5 e 6 doppie della tabella «Chi riparte», rimesse le quattro righe del Registro sul giro 12-13 e sui commit DB, «Riparte» riallineato |
| 2026-11-24 | Tid | **D-K decisa** (§4.7): il primo amministratore nasce da un verbo DB di primo impianto che si chiude alla nascita del primo SUPER_ADMIN (R-DB-K1), poi un comando BE; la porta di `fn_crea_operatore_v2` al piano dei giri (R-DB-K2) |
| 2026-11-24 | BE | D-J fatta (§4.7): bypass di `is_superuser` tolti nel BE, BB `super_admin_di_prova` (ok Tid), 129 classi di test dichiarate, test del bypass rovesciati; suite verde come la base |
| 2026-11-24 | Tid | **D-J decisa: a**, `is_superuser` non concede più niente; il lavoro BE parte subito (§4.7) |
| 2026-11-24 | Tid | **D-I decisa: il task `reset_lotto_draft` si ritira**, dopo la riverifica (nessun esecutore, né nel BE né a DB); prima il DB, poi il BE (§4.6). D-J proposta (§4.6) |
| 2026-11-24 | BE | Risposta alla richiesta 3d (§4.5): la tabella dei dieci verbi con le funzioni di decisione; due correzioni a §4.3 (`reset_lotto_draft` spenta, la riconsegna chiede il livello su `vendite.reso` e non `conferma_reso`); il superuser Django passa l'endpoint (decisione a Tid); nessun processo headless raggiunge i verbi, il task `reset_lotto_draft` non lo esegue nessun percorso; i test della Parte C che girano senza contesto o con l'utente tecnico senza profilo; le quattro primitive mai chiamate dal BE |
| 2026-11-24 | DB | Commit `969ea14566`: giro 12-13 (pgTAP, guida `gestione-ddt`, §8); merge di `origin/Tito-dev` (PR #228) e push su `dev/db-tid` |
| 2026-11-24 | Tid | Giro 12-13: `test-ddt-righe-evase-dall-ordine-v1` verde come app (§8) |
| 2026-11-24 | DB | Giro 12-13 scritto (§8): test 44-45 in `test-ddt-righe-evase-dall-ordine-v1`, guida `gestione-ddt` §15.3; nessun changeSet |
| 2026-11-24 | DB | Commit `64f00b35b1` e push su `dev/db-tid`: giri 1, 1-bis e 3 (`brief-db-revisione-anagrafiche` escluso: ha il lavoro in corso dell'altra sessione, e le due righe di qui ci restano) |
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
