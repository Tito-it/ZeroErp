# Brief DB — Il seed di primo impianto: la riga modificata dall'installazione non si riscrive

## ⏭️ Chi riparte — aggiornato al 2026-11-20 (R5 committato, giro 3 di `ui` applicato)

**Riparte: il team BE/FE**, con le ricadute del giro 3 sulle tabelle di `ui` (R-UI1 … R-UI-sup, §16.15, passo
7-quater) e con la chiusura del passo 7 (§16.14). Il lato DB di questo brief è finito: il giro 3 (`20261119-01` …
`-05`) e la superficie `dbops.fn_seed_superficie` (`20261119-06` … `-08`) sono applicati su dbdev, i pgTAP sono verdi
(Tid, 2026-11-20) e la doc auto-generata è rigenerata. R5, R5-doc e R5-test del §16.16 sono fatti dal BE e committati
(2026-11-20, PR #167). Il `20261118-01`
(la porta di chiusura delle mail di sistema riceve `p_email_account_id`) è applicato su dbdev, il pgTAP
`config/test-fn-email-sistema` è verde (Tid, 2026-11-20), la doc auto-generata è rigenerata ed è committato.
Il giro 2 (`20261117-23` … `-28`) è applicato su dbdev, i pgTAP sono verdi (Tid, 2026-11-20), la doc auto-generata è
rigenerata ed è committato (2026-11-20, PR #162).
Il **team BE/FE** ha R2 subito e il resto sbloccato: la richiesta, con l'elenco chiuso dei file, è al
**§16.14**, che risponde alla domanda del BE «come legge l'app il segno nata dal seed», applica la Q24 (account e
template si spengono, non si cancellano) e sostituisce R1 e R3 del §15.12.
Il giro 1, `20261117-01` … `-22`, è applicato su dbdev e i pgTAP sono verdi (Tid, 2026-11-18). Lo stato del giro è al §16.12. Le verifiche sono al §16.8, il censimento
delle porte al §16.9, Q19 e Q20 decise da Tid il 2026-11-18 (§16.10). Per costruire si leggono **il §15 e il §16**:
il §16 corregge il §15 sul segno «nata dal seed» (decisione A, revoca di D5), e dove i due dicono altro vale il §16.
I §4-§14 sono la storia di come ci si è arrivati: le prime stesure, l'analisi critica e la verifica. Restano per non
ripercorrere le stesse strade.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Il problema, la storia delle decisioni, la prima stesura, l'analisi critica, la porta, la verifica | §1-§14 | — |
| 2 | ✅ sessione DB e Tid | Il progetto consolidato, con le decisioni Q10, Q11, D1-D9 | §15 | 1 |
| 2-bis | ✅ sessione DB e Tid | La seconda analisi critica: il segno «nata dal seed» passa al registro (decisione A) | §16 | 2 |
| 3 | Tid | ✅ Q17 e Q18, ✅ il via al giro 1 (2026-11-18) | §16.6 | 2-bis |
| 4 | ✅ sessione DB | Le verifiche V2, V5, V6, V6-bis, V8, V10, V11 (V7 dopo Q20) | §16.8, §16.9 | 3 |
| 4-bis | ✅ Tid | Q19 (le colonne di `email_template`) e Q20 (il perimetro della porta), 2026-11-18 | §16.10 | 4 |
| 5 | ✅ sessione DB | Il giro 1: changeSet `20261117-01` … `-21`, pgTAP, codici, doc; applicato su dbdev il 2026-11-18 | §16.12 | 4 |
| 5-bis | ✅ Tid e sessione DB | Q21 e Q22 decise; il `20261117-22`, il file owner dello stato legacy e i tre pgTAP alleggeriti | §16.13 | 5 |
| 6 | ✅ Tid e sessione DB | L'apply, i pgTAP verdi, la baseline B-7, la doc auto-generata, la riga `SISTEMA`, il commit (2026-11-18) | §16.12 | 5 |
| 6-bis | ✅ sessione DB, poi Tid | Le pagine `manual/` dei building block nuovi e dei lettori della porta (2026-11-18); ✅ la doc auto-generata rigenerata (2026-11-20) | §16.12 | 6 |
| 6-ter | ✅ sessione DB e Tid | La domanda del BE e la Q24: le viste del segno, solo disattivazione (giro 2, `20261117-23` … `-28`), pgTAP, pagine `manual/`, guida, provato sullo scratch; ✅ Q23 e Q24 decise (2026-11-19) | §16.14 | 6 |
| 6-quater | ✅ Tid e sessione DB | L'apply del giro 2 e i pgTAP verdi (Tid), la doc auto-generata, il commit (2026-11-20) | §16.14 | 6-ter |
| 6-quinquies | ✅ sessione DB e Tid | La richiesta del BE sul rilancio: il `20261118-01`, il pgTAP adeguato, la pagina `manual/`; l'apply e il pgTAP verde (Tid), la doc auto-generata, il commit (2026-11-20) | §16.16 | 6-quater |
| 7 | ✅ team BE/FE e Tid | R2, R1-BE, R1-BE-bis, R1-BE-ter, R3 e R-test del §16.14 (R4 ritirata dalla Q17): fatti e committati (2026-11-20, `185f7207a`; esito sotto la richiesta) | §16.14 | 6-quater |
| 7-bis | ✅ sessione DB e Tid | Il censimento delle tabelle di `ui`, chiesto dal brief `ui` (Q27, Tid 2026-11-20); QU1-QU4 decise; il giro 3 (`20261119-01` … `-05`) e la superficie QU3 (`-06` … `-08`) applicati, pgTAP verdi, doc auto-generata rigenerata (2026-11-20) | §16.15 | 6-quater |
| 7-ter | ✅ team BE/FE e Tid | R5, R5-doc e R5-test: il rilancio scrive l'account da cui la mail riparte; fatti, verdi e committati (2026-11-20) | §16.16 | 6-quinquies |
| 7-quater | ✅ team BE/FE, poi Tid | R-UI1, R-UI2, R-UI3, R-UI-test, R-UI-sup del giro 3 di `ui`: fatti e verdi (2026-11-20, esito sotto la tabella delle ricadute); ⏳ il commit | §16.15 | 7-bis |
| 8 | chi chiude | Archiviazione in `work-done/`, coi link dei residui riportati a `work-done/`. ✅ I residui sono già nel registro dei residui e in PROJECT_CONTEXT (2026-11-20): `famiglie_documento` resta aperta (la voce è aggiornata, il brief non l'ha iscritta: §7, giro suo), Q7 è una voce nuova (con R3 del §11 / R5 del §15.12). Q8 (il titolo) cade con la chiusura | — | 6-quinquies, 7, 7-ter, 7-quater |

**Decisioni di Tid del 2026-11-20:** ✅ V-2, strada (a): il rilancio batch risolve di nuovo l'account e il log lo segue (§16.16, il DB è fatto).
**Decisioni di Tid del 2026-11-19:** ✅ Q23 e ✅ Q24, solo disattivazione (§16.14). Rinviate fuori dal giro 1: Q7 (il ripristino) e Q8 (il titolo). **Da committare:** questo brief riallineato. **Committato il 2026-11-20:** R5, R5-doc e R5-test del BE (§16.16, l'esito sotto la richiesta; PR #167); il giro 3 di `ui` e la superficie QU3 (§16.15); il giro 2 (§16.14); poi il `20261118-01`, `config/test-fn-email-sistema.sql`, la pagina `manual/` di `config.email_log`, la doc auto-generata della funzione e questo brief (§16.16). **Committato il 2026-11-18:** il giro 1 (22 changeSet, il CSV nuovo, i CSV dei codici e dei presidi, il loop e il provisioning, 4 pgTAP nuovi e 26 adeguati, la baseline B-7, tre guide, le pagine `manual/`, la doc auto-generata) e questo brief.

**Brief vicini verificati (2026-11-17):** in `work-in-progress/` nessun brief tratta i mirror che
riscrivono un dato modificato da interfaccia. Le menzioni di `loadUpdateData` in
`brief-db-revisione-documenti`, `brief-db-provenienza-prezzo-segue-il-prezzo` e
`brief-incassi-riconciliazione-rate-promemoria` riguardano i loro CSV, non il meccanismo. Il registro
dei residui ha il caso di `famiglie_documento` (§7), e da lì rimanda a questo brief.
⚠️ Aggiornato il 2026-11-17: il brief della sessione BE «La porta di `script.trgfn_lock_columns` la apre ogni
sessione» toccava lo stesso oggetto della proposta (il bypass a variabile di sessione dei trigger d'automazione).
Tid l'ha cancellato e l'ha fuso qui: §13. La segnalazione d'origine è al §9 di `brief-db-revisione-documenti`.

---

## 1. Il problema

Un mirror `loadUpdateData` in `runOnChange` ricarica **ogni** colonna di **ogni** riga del CSV appena il
file cambia. Va bene se il dato è del software. Su una tabella che l'installazione configura
dall'interfaccia, il ritocco del CSV cancella la configurazione del cliente.

> **Il fatto (2026-11-17).** `config.email_account`, riga `SISTEMA`: Tid aveva impostato da interfaccia la
> configurazione SMTP corretta. Il 2026-11-12 `brief-db-nullvalue-vuoto-cinque-mirror` ha toccato
> `email_account.csv` per una ragione solo sintattica (il token `NULL`). Al migrate successivo il mirror
> `20260329-60` ha riscritto host, porta, utente, mittente e la password con i valori di esempio del CSV.

In produzione sarebbe un guasto grave: un ritocco qualsiasi del CSV, anche a righe che non
c'entrano, riporta i valori di esempio sulla configurazione del cliente, password compresa. Il caso
non dipende da quante tabelle siano così oggi. Il modello ammette una tabella seminata dal CSV **e**
scritta dall'app, e quella combinazione perde dati.

## 2. Che cosa era già stato deciso

È un completamento di decisioni esistenti, e non ne revoca nessuna.

| Dove | Che cosa dice | Rapporto con questo brief |
| --- | --- | --- |
| `linee-guida-sql.md` §11.7 (2026-09-02) | In `80_data` convivono due specie di seed: **catalogo** (il CSV comanda) e **macchina** (nessun seed: `context: dati_macchina`, o il CSV svuotato) | Manca la terza specie, «il CSV dà il valore iniziale, poi decide l'installazione». Questo brief la aggiunge |
| `work-done/brief-db-pannello-config-verbo-generico.md`, D-P9 (decisa il 2026-09-28) | Per `config.aree_funzionali` scelta la **A**: comanda il CSV, l'app è in sola lettura (`v_tabelle_sola_lettura_app`). Scartata la **B**: togliere colonne dal mirror, così che il CSV diventi «il valore iniziale e non più il padrone» | La A resta giusta per le tabelle di sistema. La B è l'idea di questo brief, scartata **per quella tabella**: non era mai stata esaminata come regola generale |
| `registro-residui-aperti.md` (2026-09-24) | Il mirror di `vendite.famiglie_documento` riscrive il `codice` che l'operatore cambia dal CRUD. «Da decidere col team DB» | Secondo caso dello stesso difetto. Per la regola del 2 serve un meccanismo comune, non una pezza per tabella |
| `linee-guida-sql.md` §11.2 | Una riga non più valida si spegne nel CSV e non si toglie | È la stessa regola che §5 applica alle righe dell'interfaccia |

**Vicolo cieco già noto:** togliere colonne dall'elenco `columns:` del mirror non basta. Liquibase mappa
dall'intestazione del CSV, e per non caricare una colonna serve `type: SKIP` (§11.2). Inoltre una colonna
saltata non avrebbe più un valore iniziale su un database nuovo.

## 3. Il modello: tre specie di seed

| Specie | Chi comanda | Comportamento del CSV | Che cosa può fare l'app |
| --- | --- | --- | --- |
| **di sistema** (catalogo, §11.7) | il software | riscrive a ogni modifica del file | niente, o solo le colonne che il CSV non porta: sola lettura, come la D-P9 |
| **⭐ di primo impianto** (nuova) | il software finché nessuno tocca la riga, poi l'installazione | inserisce le righe che mancano; aggiorna una riga solo finché l'installazione non l'ha modificata | modifica, spegne (`attivo = false`); **non cancella** |
| **dell'installazione** (macchina, §11.7) | l'installazione | nessun seed | tutto, secondo i suoi guard |

La regola della specie nuova: **chi ha toccato la riga per ultimo decide**. Una riga come il seed
l'ha lasciata segue il software. Una riga che l'installazione ha modificato è dell'installazione, e il CSV
non la riscrive più.

**Criterio d'ingresso, sul modello:** una tabella è di primo impianto se il codice non legge le sue colonne
come regole del software (a parte la chiave per cui la cerca, che resta ferma), e quindi **la riga intera
è configurazione dell'installazione**. Se una riga mescola colonne dell'installazione e regole del software,
il blocco per riga è sbagliato (§6, limite 1), e la tabella si tratta a parte (Q5).

## 4. Il meccanismo: un trigger che salta la riga personalizzata

> ⚠️ **Storia: i §4-§14 sono superati dal §15 (2026-11-17).** Il progetto da costruire è al §15; qui restano la
> prima stesura e le analisi che l'hanno corretta.

### 4.1 L'idea

> ⚠️ **Superato in parte da §12.1 (2026-11-17).** `RETURN NULL` non salta la riga: fa fallire il migrate. Il
> trigger deve restituire `OLD`, e allora l'ordine rispetto all'audit conta.

Un trigger `BEFORE UPDATE` sulle tabelle dichiarate:

- se la scrittura arriva dal **migrate** e la riga è **personalizzata**, la salta (`RETURN NULL`): la riga
  resta com'è e il mirror va avanti con le altre;
- se la scrittura arriva dall'**app**, la lascia passare e **marca** la riga come personalizzata;
- in ogni altro caso lascia passare.

Il mirror non cambia. `loadUpdateData` continua a fare il suo upsert, e sulle righe personalizzate
l'aggiornamento non avviene. Le righe nuove del CSV entrano come oggi: il trigger intercetta solo l'`UPDATE`.
Su un database nuovo nessuna riga è personalizzata, quindi il seed carica tutto.

### 4.2 Il marcatore: una colonna esplicita, non `user_update`

L'idea iniziale era usare `user_update = 'SEED'` come segno di «riga intatta». **Non regge**, ed è un fatto
letto dal corpo di `script.trgfn_audit_data_user_generic` (doc auto-generata del 2026-10-26).
L'automazione `AUDIT_UPDATE` riscrive `user_update` a **ogni** `UPDATE`, con `app.jwt_user` se c'è e
altrimenti con `CURRENT_USER`. Il primo migrate che ripassa sul CSV sostituisce `'SEED'` col ruolo del
migrate. E `CURRENT_USER` è anche quello di un job, di un `psql` del DBA o di uno script: non distingue il
software dall'installazione.

> ⚠️ **Da rivedere con §12.3 e §12.7 (2026-11-17):** la colonna per tabella contraddice il §4.5 («senza DDL
> scritto a mano»), e qualunque scrittura dell'app marcherebbe la riga, anche il test SMTP. ✅ Il secondo punto è
> deciso (Q10, Tid 2026-11-17): marca solo un cambio delle colonne di configurazione. La sede del marcatore resta Q2.

La proposta: una colonna per tabella dichiarata, per esempio `personalizzata_il timestamptz` (`NULL` = come il
seed l'ha lasciata), accesa dal trigger e mai dal CSV. Il CSV non la porta, quindi il mirror non la tocca. Il
nome è da decidere (Q2).

### 4.3 Chi è l'«app» e chi è il «migrate»

> ⚠️ **Il bypass si corregge con §13 (2026-11-17).** Lo «stampo di `DELETE_BLOCK`» è una variabile di sessione
> che anche l'app può accendere. Il bypass del trigger nuovo passa dal building block comune di §13.3.

- **App:** la stessa fonte dell'audit, cioè `app.jwt_user` valorizzato. Il middleware Django lo imposta per
  l'utente reale. Si riusa il criterio che esiste già: non se ne inventa un secondo.
- **Migrate:** tutto ciò che non è l'app. Il trigger salta la riga personalizzata **salvo** un GUC di bypass
  acceso, sullo stampo di `DELETE_BLOCK`. Il bypass serve al changeSet deliberato, per esempio una bonifica
  che deve correggere anche le righe personalizzate. Senza bypass, una correzione voluta del software non
  arriverebbe mai.
- Da verificare (V3): un job di dominio che scrive su queste tabelle senza `app.jwt_user` verrebbe trattato
  come il migrate. Va deciso se è corretto (Q4).

### 4.4 Il salto non è silenzioso

> ⚠️ **Da rivedere con §12.4 e §12.5 (2026-11-17):** la vista «che il CSV vorrebbe diverse» non si può
> costruire senza salvare il valore scartato, e il `NOTICE` probabilmente Liquibase non lo mostra.

In sviluppo cambi il CSV, lanci il migrate e la riga non cambia. Senza un segnale sembra un guasto. Il trigger
emette un `NOTICE` con tabella e chiave della riga saltata, e la riga resta leggibile in una vista di diagnosi
(«righe personalizzate che il CSV vorrebbe diverse»), sullo stampo delle `fn_*_divergenze` delle automazioni.
Quale delle due, o entrambe: Q3.

### 4.5 Dove si dichiara

Come regola del framework delle automazioni (`dbops.automation_rules_tbl`, guida `automazione-db.md`), sullo
stampo di `DELETE_BLOCK`: una riga per tabella, un runner che converge (crea il trigger dove manca, lo
rigenera, lo toglie se la riga è spenta) e una funzione di divergenze. Una tabella entra con una riga di CSV,
senza DDL scritto a mano. ⚠️ Il trigger nasce dal `ci_apply`, quindi vale §11.5: niente DDL né `preCondition`
su di lui nei changeSet.

## 5. La cancellazione: la riga si rende obsoleta, non si cancella

> ⚠️ **Superato in parte da §12.2 (2026-11-17).** `DELETE_BLOCK` blocca la tabella intera, ma su
> `email_account` e `email_template` l'app crea e cancella righe sue. Il blocco va per riga: solo le righe nate
> dal seed.

Se l'interfaccia cancella una riga di primo impianto, il mirror la **reinserisce** al migrate successivo, perché
per lui è una riga che manca. Quindi su queste tabelle il `DELETE` dall'app non deve esistere. La riga si
spegne (`attivo = false`), come §11.2 chiede già per il CSV.

Con il §4 le due cose si incastrano. Lo spegnimento è una modifica dell'app, quindi accende il marcatore. Il
migrate successivo salta la riga, il CSV non la riaccende, e la riga resta obsoleta.

**Come si chiude la porta del `DELETE`.** Ci sono due strade, e la scelta è Q6.

| Strada | Che cosa | Note |
| --- | --- | --- |
| **a — `DELETE_BLOCK`** (proposta) | Il blocco esiste già: `dbops.automation_delete_block`, trigger `BEFORE DELETE` su `script.trgfn_delete_block_by_guc`, bypass via GUC, runner che converge | Regola del 2: il building block c'è, si aggiunge una riga per tabella. Il bypass serve al `DELETE` forward-only di §11.2, l'unica eccezione al CSV |
| **b — privilegio** | `DELETE` tolto a `zeroerp_app` nel loop dei grant (§11.8), più il blocco nel provisioning | Ferma anche un endpoint scritto male prima di arrivare al trigger, ma è una postura in tre sedi da tenere allineate |

Le due non si escludono. La b aggiunge una difesa, non una regola diversa.

## 6. I limiti accettati

1. **Si blocca la riga intera, non la colonna.** Una volta personalizzata, la riga non riceve più nemmeno
   le colonne del software: `descrizione`, `meta`, una colonna nuova aggiunta domani al CSV. Per una tabella
   di primo impianto va bene, per il criterio di §3. Se domani il codice leggerà una colonna nuova, sulla riga
   personalizzata la troverà al default della tabella: la colonna nasce con un default sensato, oppure la
   porta un changeSet deliberato col bypass.
2. **Le tabelle di sistema restano fuori.** Vocabolari, `aree_funzionali`, i parametri di
   `70_dati_sistema`: lì il CSV deve continuare a comandare e l'app resta in sola lettura.
3. **Il ritorno al default non è automatico.** Una riga personalizzata torna a seguire il CSV solo se qualcuno
   spegne il marcatore. Se serve un'azione «ripristina il valore di fabbrica» dall'interfaccia, è Q7.

## 7. Le tabelle candidate

Si valutano sul criterio di §3, non su quante righe abbiano oggi.

| Tabella | Esito proposto | Perché |
| --- | --- | --- |
| `config.email_account` | **entra, solo inserimento** (Q11, Tid 2026-11-17) | Il CSV crea la riga `SISTEMA` se manca e poi non la aggiorna più, toccata o no: i suoi valori sono segnaposto che il software non ha ragione di correggere (§12.11). A parte `codice`/`codice_interno` (`SISTEMA`, che il codice cerca e che non cambia), la riga è tutta configurazione dell'installazione: host, porta, TLS/SSL, credenziali, mittente, risposta |
| `config.email_template` | **da valutare** (Q5) | I testi delle mail sono contenuto che l'installazione adatta. Va letto se il codice legge colonne del template come regole (segnaposto, codice) |
| `vendite.famiglie_documento` | **da valutare** (Q5) | L'operatore cambia il `codice` dal CRUD, ma la riga porta regole del software (formato, colonna serie, regole fiscali, anno nel numero) che il CSV deve poter cambiare. Il blocco per riga fermerebbe anche quelle: qui serve probabilmente un'altra forma, per esempio il `codice` fuori dal mirror con `type: SKIP` |

Il censimento completo (ogni mirror `runOnChange` su una tabella che l'app può scrivere) si fa nel giro 1,
leggendo la **struttura**: GRANT di `zeroerp_app`, `config.tabelle_gestibili.pannello`, endpoint che
scrivono. Ogni tabella trovata riceve una specie dichiarata.

**Le tabelle di `ui` (richiesta del [brief-db-revisione-ui](brief-db-revisione-ui.md), Q27, Tid 2026-11-20).** Il
censimento di questo meccanismo è la sede della decisione, e i giri del brief `ui` che toccano i CSV di `ui` partono
dopo. Sono mirror `runOnChange` (`loadUpdateData`) che l'app scrive dalle pagine admin:

| Tabella | Che cosa si sa già, dal brief `ui` |
| --- | --- |
| `ui.lista_definizione` | `ricerca_min_caratteri` è una regolazione dell'installazione (Q14 del brief `ui`): il mirror la riscrive. `codice`, `vista_sql`, `schema_dati` di una lista certificata, `multi_emittente` e `perimetro_emittente` sono del software (Q14) |
| `ui.lista_colonna` | `codice` immutabile (Q14 del brief `ui`); le altre colonne si leggono nel censimento |
| `ui.lista_preset` | La pagina admin scrive i preset; con Q26 del brief `ui` `is_default` esce dalla tabella e dal mirror |
| `ui.lista_preset_colonna` | La composizione del preset, scritta dalla pagina admin |

Fuori dal censimento: `ui.misure_pagina`, che l'app legge soltanto, e le cinque tabelle di catalogo delle dashboard,
in sola lettura per l'app dal giro 5 del brief `ui` (Q19), che nessun servizio scrive già oggi. Il censimento, con la
classificazione proposta e le decisioni QU1-QU4, è al §16.15.

## 8. Verifiche prima di scrivere

| # | Che cosa | Perché |
| --- | --- | --- |
| V1 | ✅ **Fatta il 2026-11-17 (§12.1).** Che SQL genera `loadUpdateData` su PostgreSQL | `UPDATE` e poi `IF not found THEN INSERT`, in un blocco `DO` (letto in `InsertOrUpdateGeneratorPostgres` di `tools/liquibase/5.0.4`). ⛔ L'ipotesi «in entrambi i casi `RETURN NULL` salta la riga» è **smentita**: va provato su una tabella di prova in `ROLLBACK` che `RETURN OLD` non produca l'`INSERT` |
| V2 | Che il trigger di audit e quello nuovo non si disturbino | ⚠️ Corretta da §12.1: con `RETURN OLD` l'ordine dei trigger `BEFORE` (alfabetico) **conta**. Il trigger nuovo scatta dopo l'audit, così ne butta via le modifiche. Si guardano anche i trigger `AFTER UPDATE` (storico), che vedrebbero un aggiornamento senza cambiamenti |
| V3 | Chi scrive oggi queste tabelle senza `app.jwt_user`: job, funzioni di dominio, provisioning | Verrebbero trattati come il migrate (§4.3) |
| V4 | ⚠️ Esito anticipato da §12.2: `DELETE_BLOCK` **non** copre il caso così com'è | Blocca ogni riga della tabella. Resta da verificare il bypass del `DELETE` forward-only di §11.2 sulla forma per riga |
| V5 | Se Liquibase mostra i `NOTICE` di PostgreSQL nell'output del migrate (§12.5) | Se non li mostra, Q3 decade e il segnale è solo la diagnosi |

## 9. Decisioni aperte di Tid

> ⚠️ **Riassorbite dal §15.10 (2026-11-17)**, che porta tutte le decisioni con la data. Restano qui per la storia.

| # | Domanda | Proposta |
| --- | --- | --- |
| Q1 | Il modello delle tre specie (§3), con la regola «chi ha toccato la riga per ultimo decide» | Sì: completa §11.7 e riprende la B della D-P9 come regola generale |
| Q2 | Il marcatore: nome e tipo della colonna (§4.2). ⚠️ Prima la sede: colonna per tabella o registro centrale (§12.3) | Registro centrale in `dbops` (§12.3); se Tid sceglie la colonna, `personalizzata_il timestamptz` |
| Q3 | Il segnale del salto: `NOTICE`, vista di diagnosi o entrambi (§4.4) | ⚠️ Dopo V5: la vista, che legge il valore scartato (§12.4); il `NOTICE` solo se Liquibase lo mostra |
| Q4 | Un job senza `app.jwt_user` che scrive una riga di primo impianto: marca o no? (§4.3) | Da decidere dopo V3 |
| Q5 | `email_template` e `famiglie_documento`: entrano, o hanno un'altra forma? (§7) | `email_account` subito; le altre due dopo la lettura del codice che le usa |
| Q6 | Il blocco del `DELETE`: `DELETE_BLOCK`, privilegio o entrambi (§5) | ⚠️ Corretta da §12.2: nessuna delle due così com'è, perché bloccano anche le righe dell'installazione. Blocco **per riga**, sulle sole righe nate dal seed |
| Q7 | Un'azione «ripristina il valore di fabbrica» (§6, limite 3) | Non nel giro 1: si apre se l'interfaccia la chiede. Con il valore scartato salvato (§12.4) diventa semplice |
| Q8 | Il titolo di questo brief | — |
| Q9 | Che cosa fa il bypass al marcatore: dopo una bonifica voluta la riga torna a seguire il CSV, o resta dell'installazione? (§12.6) | Resta dell'installazione: la bonifica corregge un valore, non restituisce la riga al software |
| Q10 | Quale scrittura dell'app marca la riga: ogni `UPDATE`, o solo quello che cambia colonne di configurazione? (§12.7) | ✅ **Decisa (Tid, 2026-11-17), come proposto:** solo `NEW IS DISTINCT FROM OLD` sulle colonne di configurazione; `meta` e le colonne d'audit fuori dal confronto. Quali colonne sono «di configurazione» si dichiara per tabella, nella regola d'automazione |
| Q11 | Su `email_account` serve «aggiorna finché è intatta», o basta «inserisci se manca»? (§12.11) | ✅ **Decisa (Tid, 2026-11-17): basta «inserisci se manca».** La specie di primo impianto si argomenta su `email_template`. La forma è Q12 |
| Q12 | Come si ottiene «inserisci se manca» su `email_account`, visto che `loadUpdateData` non ha una modalità «solo inserimento» (§12.12; premessa corretta in §14.5) | Una modalità della stessa regola d'automazione: «solo inserimento», in cui il trigger salta **ogni** `UPDATE` del migrate sulla tabella, marcata o no |
| Q13 | La porta di servizio dei trigger d'automazione: resta, si stringe, si stringe e si registra, si chiude? (§13) | **Si stringe e si registra**, in un building block solo per tutte le porte (§13.3) |

## 10. Il giro 1 (dopo il via)

> ⚠️ **Superato dal §15.8 (2026-11-17).** I punti 3-5 descrivono il meccanismo di §4-§5, prima dell'analisi
> critica.

1. V2-V5 (§8) e V6-V7 (§13.5), con gli esiti scritti qui (V1 fatta: §12.1).
1-bis. La porta di servizio comune (§13.6), prima del trigger nuovo che la usa.
2. La regola d'automazione nuova: funzione trigger generica, runner convergente, funzione di divergenze, la
   riga in `automation_rules_tbl`, la pagina `manual/`.
3. La colonna marcatore sulle tabelle che entrano (Q5).
4. `DELETE_BLOCK` sulle stesse tabelle (Q6).
5. pgTAP che **costruisce** il caso: riga modificata con `app.jwt_user` acceso, upsert del mirror simulato da
   `scripts/prova_changeset.py`, riga intatta; riga intatta, upsert, riga aggiornata; `DELETE` dall'app
   rifiutato; bypass che lascia passare.
6. `linee-guida-sql.md` §11.7: la terza specie, il criterio d'ingresso e il rimando alla regola; guida
   `automazione-db.md` e `gestione-mail.md` allineate.

## 11. Ricadute BE/FE (da passare al team quando il giro 1 è applicato)

> ⚠️ **Superato dal §15.12 (2026-11-17).**

| # | Che cosa | Dove |
| --- | --- | --- |
| R1 | Sulle tabelle di primo impianto, «elimina» diventa «disattiva»: il DB rifiuta il `DELETE` | pannello config, drawer degli account mail; l'elenco chiuso dei file si scrive dopo Q5 |
| R2 | Il codice d'errore del rifiuto entra nella tassonomia (api.md §Tassonomia errori) | backend |
| R3 | Facoltativo, dopo Q7: un segno «personalizzata» sulla riga e l'eventuale «ripristina» | frontend |

⚠️ R1 è da riscrivere dopo §12.2: «elimina» diventa «disattiva» **solo sulle righe nate dal seed**. Gli account
e i template creati dall'installazione restano cancellabili.

## 12. Analisi critica (2026-11-17)

Una rilettura del §4-§7 sul codice e sul DDL. Il modello delle tre specie (§3) regge. Il meccanismo, così come
è scritto, no: i punti 12.1 e 12.2 lo bloccano, i punti 12.3-12.6 sono incoerenze da risolvere prima di
scrivere, gli altri vanno precisati.

### 12.1 🔴 `RETURN NULL` fa fallire il migrate (V1)

Letto in `InsertOrUpdateGeneratorPostgres` del jar in uso (`tools/liquibase/5.0.4`): su PostgreSQL
`loadUpdateData` non genera `ON CONFLICT`, ma per ogni riga del CSV

```sql
DO $$ BEGIN UPDATE …; IF not found THEN INSERT …; END IF; END $$
```

Con `RETURN NULL` l'`UPDATE` non tocca righe, `not found` è vero, e l'`INSERT` con lo stesso `id` esce in chiave
duplicata. Il changeSet ha `failOnError: true`: il migrate si ferma.

La forma che regge è **`RETURN OLD`**: l'`UPDATE` riesce e riscrive i valori di prima, quindi `found` è vero e
l'`INSERT` non parte. Ha due conseguenze:

- l'ordine dei trigger `BEFORE` (alfabetico) **conta**. Il trigger nuovo deve scattare **dopo** l'audit, così
  restituendo `OLD` ne butta via le modifiche. Se scattasse prima, l'audit riceverebbe `OLD` come `NEW` e
  scriverebbe `user_update` = ruolo del migrate su una riga che non è cambiata. Il nome del trigger fa parte
  del progetto;
- i trigger `AFTER UPDATE` (storico, se la tabella ne ha) vedono comunque un aggiornamento, senza
  cambiamenti. Va visto se scrivono una riga di storia vuota.

La prova si fa con `scripts/prova_changeset.py`, su una tabella di prova, simulando il blocco `DO`.

### 12.2 🔴 `DELETE_BLOCK` blocca la tabella, non le righe del seed (§5, Q6)

`script.trgfn_delete_block_by_guc` rifiuta ogni `DELETE` senza bypass. Su `config.email_account` l'app **crea e
cancella** account suoi (quelli per reparto: `INSERT` e `DELETE` in `backend/apps/core/db/email_repository.py`),
e lo stesso fa su `config.email_template`. La tabella tiene righe di due specie: il seed (`SISTEMA`) e quelle
dell'installazione. Con la strada a non si cancellerebbe più nemmeno un account creato dall'utente; la strada b
(privilegio) ha lo stesso difetto.

Serve un blocco **per riga**: si rifiuta il `DELETE` della sola riga nata dal seed. Quel segno oggi non c'è:
`user_insert = 'SEED'` del CSV non sopravvive, perché l'audit all'`INSERT` lo sostituisce con `CURRENT_USER`
(la stessa ragione per cui §4.2 ha scartato `user_update`). Lo accende lo stesso trigger, all'`INSERT` senza
`app.jwt_user`.

⛔ Il building block `DELETE_BLOCK` quindi **non si riusa così com'è**: la regola del 2 invocata in Q6 non
regge. Si sceglie fra una variante per riga di `DELETE_BLOCK` e il blocco dentro la funzione trigger nuova (la
riga di seed ha già il trigger della specie: è la stessa regola, una sede).

### 12.3 🟠 Colonna per tabella contro «senza DDL scritto a mano» (§4.2 contro §4.5)

Il §4.5 vuole che una tabella entri con una riga di CSV. Il marcatore come colonna chiede invece un changeSet
in `00_schema` per ogni tabella che entra. Due strade:

- accettare il DDL per tabella, e correggere il §4.5;
- un **registro centrale** in `dbops` (tabella, `id` della riga, nata dal seed, personalizzata il, valore
  proposto dal CSV). Tiene insieme il marcatore, il segno di §12.2 e il valore di §12.4, e la tabella entra
  davvero con una riga di CSV. Il costo: una lettura in più nel trigger, e un'FK che non si può dichiarare.

Proposta: il registro. Decide Tid (Q2).

### 12.4 🟠 La vista «righe che il CSV vorrebbe diverse» non si costruisce (§4.4)

Il DB non legge il CSV. Le `fn_*_divergenze` delle automazioni confrontano due cose che stanno tutte e due nel
DB; qui la seconda non c'è. La vista si può fare solo se il trigger, quando salta, **salva il `NEW` scartato**
(`to_jsonb(NEW)`, nel registro di §12.3 o in una colonna). Con quello si hanno la diagnosi, il confronto
colonna per colonna e la base del «ripristina» di Q7.

### 12.5 🟠 Il `NOTICE` probabilmente non arriva a nessuno (Q3)

Liquibase non stampa di default gli avvisi che il driver JDBC raccoglie. Non è verificato: è V5. Se si
conferma, il segnale del salto è solo la vista di §12.4.

### 12.6 🟠 «Chi ha toccato per ultimo decide» non è la regola del trigger (§3)

Il meccanismo dice «una volta personalizzata, per sempre», salvo spegnere il marcatore. E non dice che cosa fa
il bypass al marcatore: dopo una bonifica voluta, la riga torna a seguire il CSV o resta dell'installazione? È
Q9. Il §3 va riscritto sulla regola vera: «una riga che l'installazione ha modificato è sua, finché non viene
restituita al software».

### 12.7 🟡 Ogni scrittura dell'app marca la riga

Anche quelle che non sono configurazione. Premere «Testa connessione» marca `SISTEMA`:
`update_account_last_test` scrive l'esito in `meta`. Lo stesso un salvataggio che non cambia niente. Proposta
(Q10): si marca solo se `NEW IS DISTINCT FROM OLD` sulle colonne di configurazione, con `meta` e le colonne
d'audit fuori dal confronto.

### 12.8 🟡 Che cosa vuol dire «c'è `app.jwt_user`» (V3, Q4)

Il backend imposta la GUC **a livello di sessione** (`set_config(…, false)` in
`backend/apps/core/api/jwt_audit_authentication.py`). Per il lato migrate non è un rischio: ha una connessione
sua e la GUC lì non c'è. Per il lato «è l'app», invece, la GUC dice «questa connessione è passata da una
richiesta autenticata», non «questa scrittura l'ha fatta un utente». V3 lo guarda insieme ai comandi che
scrivono fuori da una richiesta (`send_pending_emails`).

### 12.9 🟡 La D-P9 (§2)

La B della D-P9 era «togliere colonne dal mirror». Questo brief raggiunge lo stesso scopo (il CSV come valore
iniziale, non come padrone) con un altro meccanismo, il trigger. Riprende lo **scopo** della B, non la B.

### 12.10 🟡 Il dato di dbdev

La riga `SISTEMA` di dbdev è già stata sovrascritta (§1). Si ripristina a mano dall'interfaccia **dopo**
l'apply del giro 1: così la marca il trigger. Ripristinata prima, il primo ritocco del CSV la riscrive.

### 12.11 🟡 Su quale tabella si argomenta la specie

Il CSV di `email_account` porta segnaposto (`smtp.example.com`, `CONFIGURARE_PASSWORD_CRITTOGRAFATA`) che
ogni installazione deve sostituire e che il software non ha ragione di correggere. Per quella tabella il
compito «aggiorna finché è intatta» non porta niente: basterebbe «inserisci se manca». Quel compito ha senso
dove il software **migliora il contenuto** e il miglioramento deve arrivare a chi non l'ha toccato, come i testi
di `email_template`. Il brief giustifica il meccanismo intero con l'unico esempio in cui metà del meccanismo non
serve: l'argomento va scritto sul caso che lo regge (Q11).

✅ **Decisione di Tid (2026-11-17), Q11:** su `email_account` basta «inserisci se manca». La specie di primo
impianto, con il suo «aggiorna finché è intatta», si argomenta su `email_template`. Q10 decisa lo stesso
giorno, come proposta in §12.7.

### 12.12 La forma di «inserisci se manca» per una tabella con un mirror già esistente (Q12)

> ⚠️ **Premessa corretta da §14.5 (2026-11-17).** Un mirror `runOnChange` + `validCheckSums: ANY` si ritocca dopo
> il merge (§11.2). Il trigger resta necessario per un'altra ragione: `loadUpdateData` non ha una modalità «solo
> inserimento».

Il mirror `20260329-60` è `loadUpdateData` in `runOnChange`, ed è già mergiato: non si modifica (AGENTS,
«Mai modificare un changelog già mergiato»). Il suo `UPDATE` partirà quindi a ogni ritocco del CSV, e va
fermato dal DB, come per le righe personalizzate.

Proposta: la regola d'automazione della specie ha una **modalità** per tabella.

| Modalità | Il trigger, su un `UPDATE` del migrate | Tabelle |
| --- | --- | --- |
| **aggiorna finché è intatta** | `RETURN OLD` solo se la riga è marcata | `email_template`, se entra (Q5) |
| **solo inserimento** | `RETURN OLD` sempre: la riga si crea e non si riscrive più | `email_account` |

Così è un trigger solo, con un argomento, e non due meccanismi. Il bypass (§4.3) vale per tutte e due le
modalità. Il blocco del `DELETE` sulla riga nata dal seed (§12.2) serve anche in «solo inserimento»: la riga
`SISTEMA` cancellata dall'interfaccia tornerebbe al primo ritocco del CSV, con i segnaposto. In questa modalità
il marcatore non serve al salto; resta utile alla diagnosi e a Q7.

## 13. La porta di servizio dei trigger d'automazione (fusa qui il 2026-11-17)

> **Da dove viene.** La sessione BE ne aveva scritto un brief a parte, «La porta di `script.trgfn_lock_columns`
> la apre ogni sessione», chiudendo `brief-db-revisione-documenti` (§9 di quel brief: trovata il 2026-11-14
> verificando la Q9a; Tid il 2026-11-16 aveva deciso «un brief a parte, dopo i giri di `documenti`»). Il
> 2026-11-17 Tid l'ha cancellato e ha deciso di trattarlo qui, perché il §4.3 di questo brief costruiva un
> trigger nuovo con la stessa porta.

### 13.1 Il caso

I trigger d'automazione hanno una porta di servizio: se la sessione accende una variabile
`zeroerp.allow_*_override`, il trigger lascia passare senza controlli. È nata come uscita dichiarata per la
manutenzione (correggere un refuso su un codice appena creato, una bonifica forward-only di §11.2).

Ma è una variabile di **sessione**: chiunque la imposti, applicazione compresa, salta il blocco. Il modello dei
permessi dichiara di proteggere da un backend che **sbaglia**, non da uno manomesso
(`architettura-permessi-e-autorizzazioni.md` §7.4-7.5). Una porta aperta di proposito non è un errore del
backend, ma un `SET` di troppo in un servizio la attraversa senza rumore: nessun errore, nessuna traccia.

### 13.2 Non è una porta sola

Il brief d'origine parlava di `script.trgfn_lock_columns`. La stessa forma, `current_setting(<chiave>, true) =
'on'`, sta anche in `script.trgfn_delete_block_by_guc` (la chiave è l'argomento del trigger, una per tabella), e
il trigger nuovo di questo brief la avrebbe presa da lì. Le chiavi citate a git oggi (2026-11-17, fatto datato,
non ancora censito per sede): `allow_lock_columns_override`, `allow_user_emittente_delete_override`,
`allow_template_versione_pubblicazione_override`, `allow_template_versione_chiusura_override`,
`allow_contabile_riga_delete_override`, `allow_delete_logs`.

Il difetto è **uno**, nella forma della porta, non in un trigger. Per la regola del 2 la correzione è un
building block solo, e i controlli scritti in ciascuna funzione si ritirano nello stesso giro.

### 13.3 La proposta: la porta si stringe e si registra

Un building block in `script`, per esempio `script.fn_porta_servizio_aperta(p_chiave text) RETURNS boolean`,
che tutti i trigger chiamano al posto del loro `current_setting`:

1. **la porta non si apre per l'applicazione.** Vale `true` solo se la variabile è `on` **e** la sessione non è
   quella dell'app. Si guarda `session_user`, non `current_user`: dentro un verbo `SECURITY DEFINER`
   `current_user` è il proprietario, e l'app passerebbe. Il migrate, il proprietario e il DBA restano liberi
   come oggi;
2. **ogni passaggio lascia una traccia**: chiave, tabella, `id` della riga, operazione, `session_user`, istante.
   Per la porta del trigger del seed la traccia sta nel registro di §12.3 («riscritta col bypass»); per le altre
   nel diario che sceglie V7.

Il trigger del seed (§4.3) e il blocco del `DELETE` sulle righe nate dal seed (§12.2) usano lo stesso building
block: nessuna porta nuova con una forma sua.

### 13.4 Le strade scartate

| Strada | Perché no |
| --- | --- |
| **resta com'è**, dichiarata come limite | È proprio il difetto: un `SET` sbagliato del backend passa in silenzio. «Chi può fare `SET` può anche altro» vale per un backend manomesso, che il modello non copre; non per uno che sbaglia, che copre |
| **si stringe, senza registrare** | Ferma l'app, ma un passaggio voluto dal migrate su una riga di un cliente non lascia traccia: dopo una bonifica non si sa che cosa è stato forzato |
| **si chiude**: `ALTER TABLE … DISABLE TRIGGER` del proprietario, nella transazione | ⛔ I trigger sono generati da `ci_apply`: §11.5 vieta DDL su di loro nei changeSet. E il trigger spento ferma **tutti** i suoi controlli, non solo quello da forzare |

### 13.5 Verifiche prima di scrivere

| # | Che cosa | Perché |
| --- | --- | --- |
| V6 | **Il censimento di chi accende ogni porta**, per sede (changeSet, pgTAP, funzioni, backend) e **con quale ruolo di sessione** | Per ogni scrittore si deve sapere se la porta stretta lo lascia passare. ⚠️ Un pgTAP che accende la porta girando col ruolo dell'app diventa rosso: si capisce se sta provando la porta o la usa per costruire i dati, e si corregge |
| V6-bis | Come si riconosce «la sessione dell'app»: il ruolo di login del backend (`DB_USER`) è `zeroerp_app` o un suo membro? | Decide se il test è `session_user = …` o `pg_has_role(session_user, 'zeroerp_app', 'MEMBER')`. Va letto anche sullo scratch (`zeroerp_ruoli`) e in CI |
| V7 | Dove sta la traccia dei passaggi fuori dal seed: una tabella esistente di `dbops` o una nuova | Per volume: un trigger di riga registra una riga per ogni riga forzata; una bonifica larga ne scrive molte |

### 13.6 Che cosa entra nel giro 1

Il building block, i tre trigger che lo usano (`trgfn_lock_columns`, `trgfn_delete_block_by_guc` e il trigger
nuovo del seed), i pgTAP che **costruiscono** i due casi (porta accesa dalla sessione dell'app: rifiutata; porta
accesa dal proprietario: passa e lascia la traccia), e le pagine `manual/` dei building block. Le porte di
`documenti` (`allow_template_versione_*`) passano dal building block se il censimento V6 le trova nella stessa
forma; se sono controlli scritti dentro un verbo, entrano come seconda occorrenza e si ritirano nello stesso
giro.

## 14. Verifica del piano (2026-11-17)

> ⚠️ **Risolta nel §15 (2026-11-17).** Ogni punto qui sotto ha la sua risposta nel meccanismo corretto; Q14-Q16
> sono riassorbite nel §15.10.

Il modello (§3), `RETURN OLD` (§12.1), il blocco del `DELETE` per riga (§12.2) e la porta che si stringe (§13)
reggono. Il piano non è pronto per il via: §10 non è allineato, e i punti 14.2-14.4 cambiano il meccanismo.

### 14.1 🔴 Il giro 1 descrive ancora il meccanismo di prima

Il §10, la riga 4 della testata e la R1 di §11 non hanno ricevuto le correzioni di §12-§13:

- il punto 3 dice «la colonna marcatore», ma la proposta di Q2 è il registro centrale (§12.3);
- il punto 4 dice «`DELETE_BLOCK` sulle stesse tabelle», che §12.2 esclude;
- il punto 5 non costruisce i casi che contano: il blocco `DO` con `RETURN OLD` che non produce l'`INSERT` in
  chiave duplicata, l'ordine dei trigger (§14.2), la modalità «solo inserimento», il `DELETE` della sola riga di
  seed, la porta accesa dalla sessione dell'app. E `scripts/prova_changeset.py` prova un changeSet: dentro un
  pgTAP il blocco `DO` del mirror si scrive nel test.

### 14.2 🔴 «Dopo l'audit» lascia i guard davanti al trigger nuovo

Su `config.email_account` (doc auto-generata) i trigger `BEFORE UPDATE` in ordine di nome sono `a10_*_block_deact`
(due, su `email_log` e `email_outbox`), `a10_lock_columns` (`codice_interno`), `a15_codice_maiuscolo`, poi
`audit_data_user`. Un trigger nuovo dopo l'audit arriva quando i guard hanno già giudicato il `NEW` che lui butterà
via. Un CSV che spegne `SISTEMA`, o che cambia `codice_interno`, ferma il migrate su una riga che doveva solo essere
saltata. Il rosso compare sul mirror, che è la trappola già descritta in §11.2.

La strada opposta è un trigger che scatta **per primo** (per esempio `a00`) e restituisce `OLD`. I guard vedono
allora una riga che non cambia, e l'audit timbra `user_update`/`data_update` su una riga invariata. Il timbro
non conta se il marcatore sta nel registro (Q2), e conta se è una colonna. V2 si rifà su questa alternativa,
leggendo nel corpo di `script.trgfn_audit_data_user_generic` se timbra anche quando `NEW` non è distinto da `OLD`.
**Q14:** primo o ultimo.

### 14.3 🟠 Il building block che riconosce il migrate c'è già

`script.fn_is_proprietario_tabella(regclass)` dice se chi esegue è il proprietario della tabella. Lo usano oltre
dieci guard. `dbops.trgfn_emittente_modi_solo_migrazione` lo usa proprio per «si scrive solo dal migrate».
Magazzino (D-V1) e `documenti` (pubblicazione delle versioni) lo affiancano già alla GUC: la porta lì è già
stretta. Il §4.3 e il §13 non lo citano.

- §13.2-§13.4 vanno rivisti. «Resta com'è» non descrive tutte le porte, e il censimento V6 deve partire da queste.
- §13.3 usa `session_user` e il building block esistente usa `current_user`, di proposito: lascia passare i verbi
  `SECURITY DEFINER`. Le due regole dicono cose diverse, e non è una copia. Il brief deve però dire perché una porta
  di servizio vuole l'una e un guard di verbo l'altra, e scegliere se il building block nuovo affianca quello
  vecchio o lo estende.
- Per il trigger del seed, `current_user` non basta a riconoscere il migrate: una scrittura dell'app che passa da un
  verbo `DEFINER` (`config.fn_pannello_scrivi`) sembrerebbe il proprietario. Il criterio dell'app resta
  `app.jwt_user`. Il criterio del migrate si cerca fra `session_user` e il building block.

### 14.4 🟠 Lo scrittore terzo riceve «UPDATE 1» e non cambia niente

Il §4.3 divide gli scrittori in due: «l'app» e «tutto il resto, che è il migrate». Con `RETURN OLD` il resto
(un job, un `psql` del DBA, uno script) riceve un `UPDATE` riuscito che non ha scritto niente. In «solo
inserimento» capita a **ogni** sua scrittura sulla tabella. È una scrittura persa senza errore.

La proposta è di riconoscere il migrate **in positivo** (§14.3) e di rifiutare con un errore lo scrittore che non è
né l'app né il migrate, salvo la porta. Assorbe Q4. **Q15**.

### 14.5 🟡 Q12: la premessa è sbagliata, la conclusione regge

Il §12.12 dice che il mirror `20260329-60` non si modifica perché è mergiato. Il §11.2 dice il contrario: un mirror
`runOnChange` + `validCheckSums: ANY` si ritocca, ed è fatto apposta. Il trigger serve per un'altra ragione:
`loadUpdateData` non ha una modalità «solo inserimento», e `type: SKIP` lascia vuote le colonne `NOT NULL` su un
database nuovo (vicolo cieco di §2).

### 14.6 🟠 Le righe di seed che esistono già non sono «nate dal seed»

Il §12.2 accende il segno «nata dal seed» all'`INSERT` del migrate. `SISTEMA` esiste già su ogni database, quindi
non riceve il segno e il suo `DELETE` resta aperto, proprio dove serve chiuderlo. Il giro 1 deve accendere il segno
sulle righe esistenti.

Il criterio non può essere un `codice` scritto in un changeSet, né una `preCondition` sul contenuto di `80_data`
(§11.4). Il CSV porta `id` espliciti, e un CSV che porta il segno renderebbe il dato della sua sede. **Q16:** come
si riconosce una riga di seed già presente.

### 14.7 🟠 La finestra fra il migrate e il `ci_apply`

I trigger d'automazione nascono dal `ci_apply`: in CI alla seconda invocazione, sul migrate manuale la sera dal
pgagent (§11.5). Il mirror gira nel migrate. Una tabella che entra nella regola con un ritocco del suo CSV nello
stesso rilascio viene riscritta prima che il trigger esista. La regola d'ingresso va scritta: la riga della regola
d'automazione arriva in un rilascio **precedente** al primo ritocco del CSV, oppure il runner converge dentro il
migrate. Vale anche per `email_account` nel giro 1: il giro non tocca `email_account.csv`.

### 14.8 🟡 Il perimetro dipende da Q5

Con Q11 la modalità «aggiorna finché è intatta» ha un solo candidato, `email_template`, ancora aperto in Q5. Da lei
dipendono il valore scartato salvato (§12.4), la vista di diagnosi (Q3) e il ripristino (Q7). Q5 va decisa prima
di Q2, Q3 e Q7. Se `email_template` resta fuori, il giro 1 comprende la porta (§13), la modalità «solo inserimento»
e il blocco del `DELETE` per riga, e la modalità piena aspetta il suo primo caso. È un'osservazione sul modello,
non sul conteggio: senza una tabella che la usa, non c'è un caso da costruire nel pgTAP.

### 14.9 Rimasti da fare dal §12

- il §3 dice ancora «chi ha toccato la riga per ultimo decide»: §12.6 ne chiede la riscrittura, legata a Q9;
- `email_account` non ha trigger di storico. Il suo unico `AFTER UPDATE`, `child_requires_active_parent`, vede la
  riga com'era. Per questa tabella la seconda metà di V2 è chiusa; resta da fare per `email_template`.

| # | Domanda | Proposta |
| --- | --- | --- |
| Q14 | Il trigger del seed scatta per primo o per ultimo fra i `BEFORE UPDATE` (§14.2) | Per primo, se V2 conferma che il timbro dell'audit su una riga invariata è innocuo con il registro |
| Q15 | Lo scrittore che non è né l'app né il migrate: salto silenzioso o errore (§14.4) | Errore, con il migrate riconosciuto in positivo |
| Q16 | Come si accende il segno «nata dal seed» sulle righe che esistono già (§14.6) | Da proporre dopo Q2: dipende dalla sede del segno |

## 15. Il progetto (consolidato il 2026-11-17)

> **Questa è la sola sezione da leggere per costruire.** Tiene insieme il modello (§3), le correzioni dell'analisi
> critica (§12), la porta di servizio (§13), la verifica del piano (§14) e le decisioni di Tid del 2026-11-17
> (§15.10). Dove i §4-§14 dicono altro, vale questa.
>
> ⚠️ **Corretta dal §16 (2026-11-17)** sul segno «nata dal seed»: regole 6-8, §15.2, §15.3, §15.6, §15.7, D5,
> D5-bis, R2 e R4. L'elenco puntuale è al §16.3; dove i due dicono altro, vale il §16.

Fatti letti dalla struttura per scriverla:

- il corpo di `script.trgfn_audit_data_user_generic`: timbra `data_update` e `user_update` a **ogni** `UPDATE`,
  senza confronto con `OLD`, e `user_insert` all'`INSERT`, che poi non riscrive più. Ci scrive lo username Django
  (`app.jwt_user`) se c'è, altrimenti il ruolo (`CURRENT_USER`);
- i trigger delle due tabelle. Su `email_account` scattano `a10_*_block_deact` (due), `a10_lock_columns`
  (`codice_interno`), `a15_codice_maiuscolo` e l'audit. ~~Su `email_template` l'audit c'è solo all'`INSERT`~~
  ⚠️ corretto il 2026-11-17 (§16.5): su `email_template` l'audit c'è all'`INSERT` **e** all'`UPDATE`;
- `dbops.fn_sessione_del_migratore()`, `script.fn_is_proprietario_tabella`, `anagrafiche.fn_crea_auth_user`,
  `script.fn_categoria_accesso`, `dbops.vw_credenziali_da_sanare`;
- `email_repository.py` e `email_views.py`: l'app crea e cancella account e template suoi, cambia il `codice` del
  template e scrive `variabili_disponibili`;
- il SQL di `loadUpdateData` su PostgreSQL (§12.1): `UPDATE`, poi `INSERT` solo se l'`UPDATE` non ha trovato la
  riga.

### 15.1 Le regole

1. **Tre specie di seed** (§3): di sistema, **di primo impianto**, dell'installazione. Quella di primo impianto:
   il CSV crea la riga; dopo che l'installazione l'ha modificata, la riga è sua.
2. **Di default il blocco è per riga** (D9). La regola d'automazione della tabella non dichiara colonne: tutte
   quelle non libere sono dell'installazione. Una riga intatta segue il CSV; una riga personalizzata non riceve più
   niente dal CSV. Nessuna decisione colonna per colonna.
   Una tabella entra per riga solo se rispetta il criterio di §3: la riga è tutta configurazione
   dell'installazione, tranne la chiave con cui il codice la cerca, che deve essere già ferma per conto suo (per
   esempio `codice_interno` con `lock_columns`). Su una riga personalizzata non arriva più nemmeno una correzione
   del software: è il limite 1 del §6, accettato per queste tabelle.
3. **L'eccezione è il blocco per colonna**, per le righe **miste**, che portano insieme configurazione
   dell'installazione e regole del software. La regola elenca le colonne, tutte e due le classi (D8):
   - **dell'installazione**: il CSV la scrive finché la riga è intatta, e non la riscrive più dopo che
     l'installazione l'ha cambiata;
   - **del software**: la chiave con cui il codice cerca la riga e le regole che il codice legge. Il CSV la scrive
     sempre, e su una riga nata dal seed l'installazione non la può cambiare.

   Una colonna non libera che non sta in nessuno dei due elenchi è un difetto (§15.4).
   In tutte e due le forme le colonne **libere**, cioè `meta` e quelle d'audit, non sono protette da nessuno e non
   contano per «personalizzata».
4. **Chi scrive è il software o l'installazione**, e nient'altro. Il software è la sessione del migratore,
   cioè `dbops.fn_sessione_del_migratore()`: il ruolo di login è membro del proprietario di `dbops`, oppure è un
   superuser. Tutto il resto è l'installazione: l'app, con o senza `app.jwt_user`, un verbo `SECURITY DEFINER`
   chiamato dall'app, un job.
5. **Una riga è personalizzata** quando l'installazione ha cambiato almeno una colonna dell'installazione
   (`NEW IS DISTINCT FROM OLD` su quelle colonne). Resta personalizzata anche dopo una bonifica fatta con la porta.
6. ⚠️ **Revocata dal §16.2 (2026-11-17):** «nata dal seed» si legge dal registro, e `user_insert` si legge una volta
   sola, all'iscrizione della tabella. Testo di prima:
   **Una riga è nata dal seed** se il suo `user_insert` è `'SEED'` (caricata dal CSV prima che esistesse l'audit,
   come su un database nuovo), oppure se è il nome di un ruolo del migratore (caricata dal migrate con l'audit
   acceso). Vale sulle righe che esistono già, senza bonifiche.
7. **Una riga nata dal seed non si cancella**: si spegne (`attivo = false`). Le righe create dall'installazione si
   cancellano come oggi.
8. ⚠️ **Ridimensionata da Q17 (§16.6, Tid 2026-11-18):** resta solo il motivo `NOME_DI_RUOLO_DB` del presidio in
   `vw_credenziali_da_sanare`; il divieto in `fn_crea_auth_user` non nasce. Testo di prima:
   **Gli username dell'app e i ruoli del database sono disgiunti.** Nessuna credenziale può chiamarsi `SEED` o
   come un ruolo di `pg_roles`, senza distinguere maiuscole e minuscole. Vale per tutte e tre le categorie di
   accesso (`OPERATORE`, `ALTRO`, `SISTEMA`): la regola 6 si regge su questa.
9. **La porta di manutenzione** (`zeroerp.allow_*`) si apre solo dalla sessione del migratore e lascia una
   traccia. Le porte di verbo, quelle che un verbo `DEFINER` apre per sé, restano come sono (§15.5).

### 15.2 Il trigger

Una funzione sola, `script.trgfn_seed_primo_impianto()`, `BEFORE UPDATE OR DELETE`, per riga. Il trigger si chiama
`trg_<tabella>_a00_seed_primo_impianto` e scatta **per primo**. Le colonne le legge dalla regola d'automazione
della tabella. Nel blocco per riga (colonne non dichiarate) le colonne dell'installazione sono tutte quelle non
libere, e nessuna è del software: lo stesso codice serve le due forme, e le righe con «colonna del software» della
tabella qui sotto valgono solo per il blocco per colonna.

| Evento | Chi scrive | Che cosa fa |
| --- | --- | --- |
| `UPDATE` | il software, riga intatta | passa |
| `UPDATE` | il software, riga personalizzata | rimette in `NEW` le colonne dell'installazione da `OLD`, salva nel registro i valori scartati e alza un `WARNING` se ne ha scartato qualcuno; il resto passa |
| `UPDATE` | il software, porta aperta | passa tutto; registra il passaggio. La riga resta personalizzata |
| `UPDATE` | l'installazione, riga nata dal seed, cambia una colonna del software | errore |
| `UPDATE` | l'installazione, altrimenti | passa; se cambia una colonna dell'installazione, la riga diventa personalizzata nel registro |
| `DELETE` | chiunque, porta chiusa, riga nata dal seed | errore |
| `DELETE` | il software, porta aperta | passa e registra: è il `DELETE` forward-only di §11.2 |
| `DELETE` | riga dell'installazione | passa |

**«Solo inserimento»** non è un meccanismo a parte. È il blocco per riga in cui ogni riga nata dal seed conta
come personalizzata. Il CSV crea la
riga se manca e poi non le cambia più niente. La regola lo dichiara con un argomento (`SOLO_INSERIMENTO`).

**Perché il blocco `DO` del mirror non va in errore.** Il trigger restituisce `NEW` con le colonne rimesse a
posto, non `NULL`. L'`UPDATE` trova la riga, e l'`INSERT` non parte (§12.1).

**Perché per primo.** I guard che vengono dopo vedono i valori rimessi a posto: un valore scartato non può più
fermare il migrate. Il costo: l'audit timbra `data_update` e `user_update` col ruolo del migratore anche su una
riga in cui non è cambiato niente. Su queste tabelle `user_update` vuol dire «l'ultimo che ci è passato sopra». Lo
dice la pagina `manual/`, e «chi l'ha personalizzata» si legge dal registro.

### 15.3 Il registro

Una tabella in `dbops`, `dbops.seed_righe` (il nome si fissa nel giro), con una riga per `(tabella, riga_id)`:
quando la riga è stata personalizzata e da chi, gli ultimi valori scartati (`jsonb`, solo le colonne
dell'installazione) e quando, l'ultimo passaggio dalla porta e da chi. Una tabella entra senza DDL suo (§12.3).

Serve a tre cose: la diagnosi «righe in cui il CSV porta un valore diverso» (la funzione di divergenze della
regola la legge da qui), la traccia della porta e, in un giro futuro, il «ripristina il valore di fabbrica» (Q7).

~~«Nata dal seed» non si registra: si legge da `user_insert` (regola 6).~~ ⚠️ Revocato dal §16.2 (2026-11-17): il
registro tiene **solo le righe nate dal seed**, e la presenza della riga nel registro è il segno.

### 15.4 La dichiarazione di una tabella

È una regola del framework delle automazioni (`automazione-db.md`), con una riga per tabella: la tabella, la
modalità (`SOLO_INSERIMENTO` o no) e i due elenchi di colonne. Se gli elenchi sono vuoti (`NULL`) il blocco è per
riga (D9), se ci sono è per colonna e devono esserci tutti e due (D8). La regola ha un runner che converge e una
funzione di divergenze. Il trigger nasce dal `ci_apply`, quindi vale §11.5.

**Come si decide la forma.** Una volta per tabella, quando entra. La sessione DB legge la struttura e il codice che
la usa, e scrive nel brief se la riga è tutta dell'installazione (per riga) o mista (per colonna, con la
classificazione); Tid approva. Di default è per riga: la classificazione si fa solo per le righe miste.

**La colonna non classificata (D8), solo nel blocco per colonna.** La funzione di divergenze della regola
restituisce, per ogni tabella iscritta per colonna, le colonne che non sono libere e non stanno in nessuno dei due elenchi, e anche le colonne elencate che
la tabella non ha più. È un presidio a zero nel catalogo `dbops.presidi`. Il runner non rigenera il trigger di una
tabella che ha colonne non classificate: resta il trigger di prima, che continua a proteggere le colonne già
dichiarate, finché qualcuno non classifica quella nuova. Una colonna nuova non diventa mai, in silenzio, né del
software né dell'installazione.

| Tabella | Forma | Modalità | Colonne del software | Colonne dell'installazione |
| --- | --- | --- | --- | --- |
| `config.email_account` | **per riga** | `SOLO_INSERIMENTO` (Q11) | — (la chiave `codice_interno` è già ferma per `lock_columns`) | — (tutte le non libere) |
| `config.email_template` | **per colonna**: riga mista | piena | `codice`, `variabili_disponibili`; `lingua`, `unita_organizzativa_id`, `tipo_prestazione_id` da confermare (V10: fanno parte della `UNIQUE` con cui il codice risolve il template) | `oggetto`, `corpo_html`, `corpo_testo`, `attivo` |

`email_template` non può stare per riga: la chiave di ricerca `codice` non ha un lock suo, quindi l'installazione
potrebbe rinominarla e rompere l'invio, e le variabili nuove del software non arriverebbero sulle righe
personalizzate.

`vendite.famiglie_documento` ha la forma per colonna: il `codice` è dell'installazione e le regole del software. Entra
in un giro suo, con la lettura del codice che la usa.

**Strada scartata: «il CSV carica solo se la tabella è vuota»** (domanda di Tid, 2026-11-17). Nel progetto non
esiste: le forme che escludono una tabella dagli aggiornamenti sono la specie di macchina di §11.7 (`context:
dati_macchina`, o il CSV svuotato), che però non semina nemmeno un database nuovo. Un caricamento condizionato a
`count(*) = 0` è scartato perché decide sul **contenuto** della tabella, non sul modello:

- una riga creata dall'installazione prima del migrate (un account suo) fa saltare il seed per sempre;
- una tabella svuotata dall'installazione si ricarica tutta al primo ritocco del CSV, e le righe tornano in vita;
- «vuota» non vuol dire «mai seminata».

Il bisogno lo copre `SOLO_INSERIMENTO`. Su un database nuovo carica tutto; poi non aggiorna mai, decidendo riga per
riga e non sul conteggio. La riga di seed non si cancella, si spegne, quindi non torna in vita. Una riga aggiunta
dopo al CSV arriva sulle installazioni che non ce l'hanno.

**Regola d'ingresso (§14.7).** La riga della regola arriva in un rilascio **precedente** al primo ritocco del CSV
della tabella, perché il trigger nasce solo al `ci_apply`. Il giro che iscrive una tabella non tocca il suo CSV.

### 15.5 La porta di manutenzione

Le porte `zeroerp.*` sono di due specie:

| Specie | Chi la apre | Il controllo |
| --- | --- | --- |
| **di manutenzione** | il migratore a mano: bonifica, refuso, `DELETE` forward-only | GUC accesa **e** `dbops.fn_sessione_del_migratore()`; ogni passaggio lascia una traccia |
| **di verbo** | un verbo `DEFINER` che la apre per sé | GUC accesa **e** `script.fn_is_proprietario_tabella`, come oggi: il verbo chiamato dall'app deve passare |

Building block nuovo, solo per la prima specie: `script.fn_porta_manutenzione_aperta(p_chiave text, p_tabella
regclass) RETURNS boolean`. Controlla la GUC e la sessione del migratore e scrive la traccia: nel registro di
§15.3 per la porta del seed, altrove nel diario che sceglie V7. Ci passano il trigger del seed,
`script.trgfn_lock_columns` e `script.trgfn_delete_block_by_guc`, più le altre porte che il censimento V6 assegna a
questa specie. I controlli scritti dentro ciascuna si ritirano nello stesso giro.

### 15.6 Gli username vietati

| Sede | Che cosa fa |
| --- | --- |
| `anagrafiche.fn_crea_auth_user` | rifiuta uno username uguale a `SEED` o a un ruolo di `pg_roles`, senza distinguere maiuscole e minuscole. Codice d'errore nuovo |
| `dbops.vw_credenziali_da_sanare` | terzo motivo, `NOME_DI_RUOLO_DB`: trova le collisioni nate fuori dal verbo (`createsuperuser`, l'admin di Django) o da un ruolo creato dopo l'utente. Si sana rinominando la credenziale |

Un trigger su `django.auth_user` non nascerebbe su un'installazione nuova, perché Liquibase gira prima delle
migrazioni di Django. Un trigger su `CREATE ROLE` non esiste: gli event trigger non scattano sui ruoli. Il divieto
copre quindi la strada normale, e il presidio le altre.

«È un ruolo del migratore» lo chiedono ora in due: la sessione (regola 4) e `user_insert` (regola 6). Per la
regola del 2 la domanda si estrae in `dbops.fn_ruolo_del_migratore(p_ruolo name)`, e
`fn_sessione_del_migratore()` diventa la sua chiamata con `session_user`.

### 15.7 I pgTAP, che costruiscono i casi

Su una tabella di prova con il trigger, un guard e l'audit nell'ordine vero. Il blocco `DO` del mirror si scrive
nel test, e l'installazione si simula come fanno i test di `fn_sessione_del_migratore` (V8).

1. Software su una riga intatta: aggiornata. Su una riga personalizzata: le colonne dell'installazione restano, quelle
   del software si aggiornano, i valori scartati sono nel registro, e il blocco `DO` non va in chiave duplicata.
2. `SOLO_INSERIMENTO`: la riga che manca si inserisce, quella che c'è non cambia.
3. Un valore scartato che il guard rifiuterebbe non ferma il blocco `DO`: è la prova dell'ordine.
4. L'installazione che tocca solo `meta` non personalizza la riga.
5. L'installazione che cambia una colonna del software su una riga nata dal seed: errore. Sulla riga sua: passa.
6. `DELETE` di una riga nata dal seed: rifiutato, sia con `user_insert = 'SEED'` sia col nome del migratore.
   `DELETE` di una riga dell'installazione: passa.
7. La porta accesa dall'installazione resta chiusa. Accesa dal migratore si apre, la riga resta personalizzata e
   il passaggio è registrato.
8. ⚠️ Corretto da Q17 (2026-11-18): niente rifiuto in `fn_crea_auth_user`. Una collisione costruita a mano
   (username `SEED`, o uguale a un ruolo con maiuscole diverse) esce dal presidio.
9. Blocco per riga: su una riga personalizzata il software non cambia nessuna colonna non libera; su una
   riga intatta la aggiorna tutta.
10. Blocco per colonna: una colonna aggiunta alla tabella di prova e non classificata esce dalle divergenze, e il runner lascia il
   trigger di prima. Una colonna elencata e tolta dalla tabella esce anche lei.

⚠️ **Presidio, non prova:** il caso «verbo `DEFINER` chiamato dall'app» dipende da `session_user`. Se V8 trova che
i test esistenti non lo costruiscono, si dichiara con uno `skip()` motivato.

### 15.8 Il giro 1

1. Le verifiche di §15.9.
2. `dbops.fn_ruolo_del_migratore`, con `fn_sessione_del_migratore` riscritta sopra di lui.
3. `script.fn_porta_manutenzione_aperta`, con le porte di manutenzione censite da V6 che passano da lì.
4. Il registro `dbops.seed_righe`.
5. La funzione trigger, la regola d'automazione (runner, divergenze con le colonne non classificate, la riga nel
   catalogo dei presidi) e le due righe di §15.4.
6. Il motivo `NOME_DI_RUOLO_DB` del presidio. ⚠️ Il divieto in `fn_crea_auth_user` non nasce (Q17, 2026-11-18).
7. I codici d'errore nuovi nel catalogo: `DELETE` di una riga di seed, colonna del software cambiata
   dall'installazione. ⚠️ Lo username vietato esce (Q17, 2026-11-18): i codici sono due.
8. I pgTAP di §15.7.
9. La documentazione: `linee-guida-sql.md` §11.7 (la terza specie, le colonne, la regola d'ingresso),
   `automazione-db.md`, `gestione-mail.md` e le pagine `manual/` dei building block, con il significato di
   `user_update` su queste tabelle.

Dopo l'apply la riga `SISTEMA` di dbdev si ripristina a mano dall'interfaccia: è una scrittura dell'installazione
(§12.10).

### 15.9 Le verifiche prima di scrivere

| # | Che cosa | Stato |
| --- | --- | --- |
| V1 | Il SQL di `loadUpdateData` su PostgreSQL | ✅ §12.1 |
| V2 | Su una tabella di prova: il trigger `a00` che rimette le colonne fa vedere ai guard i valori rimessi, e l'audit timbra solo le sue colonne | da fare |
| V5 | Se l'output del migrate di Liquibase mostra il `WARNING`. Se non lo mostra, il segnale è solo la diagnosi del registro | da fare |
| V6 | Il censimento delle porte `zeroerp.*`: sede, chi le apre, con quale ruolo e la **specie** (§15.5) | da fare |
| V6-bis | Il ruolo di login dell'app (`zeroerp_app`) non è membro del proprietario di `dbops` su dbdev, sullo scratch e in CI | da fare |
| V7 | Dove sta la traccia delle porte di manutenzione fuori dal seed | dopo V6 |
| V8 | Come i test di `fn_sessione_del_migratore` simulano l'app (`test-totp-porta-v1.sql`, `test-sec-functions-owner-riservato-v1.sql`) | da fare |
| V9 | `email_template`: chi la scrive e quali colonne il codice legge come regole | ✅ §15.4 |
| V10 | Se `lingua`, `unita_organizzativa_id` e `tipo_prestazione_id` di `email_template` sono colonne del software (`config.fn_resolve_email_template`) | da fare |

V3 e V4 non servono più: V3 per la regola 4, V4 per la regola 7.

### 15.10 Le decisioni

| # | Decisione | Di Tid, il | Riassorbe |
| --- | --- | --- | --- |
| Q10 | Una riga diventa personalizzata solo se cambiano le colonne dell'installazione | 2026-11-17 | — |
| Q11 | `email_account`: basta «inserisci se manca» | 2026-11-17 | — |
| D1 | Il modello a tre specie, con la regola «la riga modificata dall'installazione è sua» | 2026-11-17 | Q1 |
| D2 | Blocco per **colonna**: ogni colonna è dell'installazione o del software. `email_template` entra; il `codice` delle righe di seed non si cambia più | 2026-11-17 | Q5, Q12, §6 limite 1 |
| D3 | Chi scrive si riconosce dal ruolo (sessione del migratore), non da `app.jwt_user` | 2026-11-17 | Q4, Q15 |
| D4 | Il trigger scatta per primo; su queste tabelle `user_update` dice «l'ultimo che ci è passato sopra» | 2026-11-17 | Q14 |
| D5 | ⚠️ **Revocata da D10 (2026-11-17).** «Nata dal seed» si legge da `user_insert` | 2026-11-17 | Q6, Q16 |
| D5-bis | ⚠️ **Ridimensionata da Q17 (§16.6, 2026-11-18):** resta solo il presidio. Username e ruoli del DB disgiunti: divieto in `fn_crea_auth_user` e presidio in `vw_credenziali_da_sanare` | 2026-11-17 | il limite di D5 |
| D6 | Dopo una bonifica con la porta la riga resta dell'installazione | 2026-11-17 | Q9 |
| D7 | Si stringono solo le porte di manutenzione, con un building block che registra | 2026-11-17 | Q13 |
| D8 | Nel blocco per colonna si elencano tutte e due le classi; una colonna non classificata è un presidio a zero e ferma la rigenerazione del trigger | 2026-11-17 | — |
| D9 | **Di default il blocco è per riga** (colonne non dichiarate); il blocco per colonna è l'eccezione per le righe miste. `email_account` per riga, `email_template` per colonna | 2026-11-17 | ridimensiona D2 |
| D10 | **«Nata dal seed» si registra** nel registro dal trigger, all'`INSERT` della sessione del migratore; le righe che esistono già le segna il runner all'iscrizione della tabella; una riga senza segno è dell'installazione (§16.2). Scartata la toppa su `user_insert` (§16.7) | 2026-11-17 | revoca D5 |

Decise dalla forma: Q2 (il registro), Q3 (`WARNING` più la diagnosi del registro). Rinviate: Q7 (il ripristino) e
Q8 (il titolo).

**Correzioni nate mentre si decideva**, scritte qui perché non si ripetano:

- `dbops.fn_sessione_del_migratore()` esisteva già. Il building block `fn_sessione_del_software` della prima
  stesura di questa sezione non nasce;
- la suddivisione degli accessi (`fn_categoria_accesso`) divide le credenziali dell'app e non separa gli username
  dai ruoli del DB: la regola 8 vale per tutte e tre le categorie;
- il presidio delle credenziali esisteva già: la collisione è un suo terzo motivo, non una vista nuova;
- il §12.12 diceva che il mirror non si può ritoccare: per §11.2 si può. Il trigger serve perché
  `loadUpdateData` non ha una modalità «solo inserimento».

### 15.11 I limiti dichiarati

1. Su queste tabelle `user_update` e `data_update` non dicono chi ha cambiato la riga (D4).
2. Il migratore che fa `SET ROLE` resta migratore: è il limite di `fn_sessione_del_migratore`.
3. Una collisione fra username e ruolo nata fuori dal verbo esiste finché il presidio non la segnala e qualcuno
   non la sana. Nel frattempo l'errore va dalla parte sicura: la riga non si cancella, ma nessun dato si perde.
4. Il migratore che fuori dal migrate aggiorna una colonna dell'installazione su una riga personalizzata non cambia
   niente e riceve un `WARNING`. Per correggerla davvero, apre la porta.
5. Una riga personalizzata torna a seguire il CSV solo togliendola dal registro. Un'azione dall'interfaccia è Q7.

### 15.12 Le ricadute BE/FE (dopo l'apply)

> ⚠️ **R1 e R3 superate dal §16.14 (2026-11-19).** R3 nominava due campi: dopo la Q19 le colonne del software dei
> template sono cinque, e l'elenco non sta nel backend, lo dà la vista del segno. R1 cade con la Q24: account e
> template non si cancellano più, nemmeno quelli dell'azienda, e la cancellazione esce dal backend. La richiesta da
> passare al team, con l'elenco chiuso dei file, è al §16.14.

Sostituiscono il §11.

| # | Che cosa | Dove |
| --- | --- | --- |
| R1 | Sulle righe nate dal seed «elimina» diventa «disattiva». Le righe create dall'installazione restano cancellabili | drawer degli account mail e dei template |
| R2 | I tre codici d'errore nuovi nella tassonomia (api.md §Tassonomia errori). ⚠️ Corretta da Q17 (2026-11-18): lo username vietato esce, i codici sono due | backend |
| R3 | Sulle righe di seed del template il `codice` e `variabili_disponibili` non si modificano: il campo è spento, col motivo | drawer dei template |
| R4 | Un validatore Django dello username con la regola 8, per `createsuperuser` e l'admin. ⚠️ **Ritirata da Q17 (2026-11-18):** non serve | backend |
| R5 | Facoltativo, dopo Q7: un segno «personalizzata» sulla riga e il «ripristina» | frontend |

L'elenco chiuso dei file lo scrive la sessione DB nel brief quando passa la richiesta al team, dopo l'apply.

## 16. Il segno «nata dal seed» sta nel registro (decisione A, 2026-11-17)

> **Da dove viene.** Una seconda analisi critica del §15, fatta il 2026-11-17 sul corpo di
> `script.trgfn_audit_data_user_generic`, su quello di `dbops.fn_sessione_del_migratore()` e sui trigger delle due
> tabelle (doc auto-generata). Ha trovato che la regola 6 (D5) non regge. Tid ha scelto la strada A, il segno nel
> registro, e ha scartato la toppa su `user_insert` (§16.7). Questa sezione corregge il §15: dove i due dicono altro,
> vale questa.

### 16.1 Perché la regola 6 non regge

La regola 7 («una riga nata dal seed non si cancella») si regge sul testo di `user_insert`, cioè su un'informazione
scritta nella riga stessa. I difetti sono quattro, e vengono tutti da lì:

1. **`user_insert` si riscrive.** L'audit lo imposta solo all'`INSERT`: su un `UPDATE` lascia passare il valore che
   arriva. Il §15.1, regola 3, mette le colonne d'audit fra quelle libere, che nessuno protegge. Un `UPDATE … SET
   user_insert = 'mario'` dall'app rende cancellabile `SISTEMA`; `SET user_insert = 'SEED'` rende intoccabile una
   riga dell'installazione.
2. **La domanda sul ruolo va in errore.** Su una riga dell'installazione `user_insert` è uno username Django.
   `pg_has_role('mario', …)` non risponde `false`: alza «role does not exist». Ogni `DELETE` di un account creato
   dall'utente fallirebbe.
3. **L'audit guarda `CURRENT_USER`, la regola 4 `session_user`.** Senza `app.jwt_user`, una riga inserita da un verbo
   `SECURITY DEFINER` chiamato da un job o da un comando ha `user_insert = zeroerp_owner`, un ruolo del migratore, e
   diventerebbe «nata dal seed». Due criteri diversi per la stessa domanda.
4. **Il significato dipende dai ruoli di oggi.** Un ruolo tolto o rinominato, o un dump/restore su un cluster con
   nomi diversi, toglie la protezione alla riga. La regola 8 (username e ruoli disgiunti, con R4) serviva solo a
   reggere la regola 6.

Uno in più, indipendente dal segno: **una riga creata dall'installazione è «intatta»**, perché la personalizzazione
nasce solo da un `UPDATE` (regola 5). Un `UPDATE` del software senza porta, per esempio una bonifica, la riscriverebbe
(§15.2, riga «il software, riga intatta: passa»).

### 16.2 La decisione: il segno nel registro

1. **Il registro tiene solo le righe nate dal seed.** `dbops.seed_righe` (§15.3) ha una riga per `(tabella, riga_id)`
   per ogni riga nata dal seed. La presenza della riga nel registro **è** il segno. Le colonne della
   personalizzazione, dei valori scartati e della porta restano come al §15.3.
2. **Il trigger segna la riga quando nasce.** `script.trgfn_seed_primo_impianto()` diventa `BEFORE INSERT OR UPDATE
   OR DELETE`. All'`INSERT`, se `dbops.fn_sessione_del_migratore()` è vero, registra la riga. Lo stesso criterio della
   regola 4, `session_user`: un verbo `DEFINER` chiamato dall'app non segna niente.
3. **Le righe che esistono già le segna il runner, una volta.** Il trigger nasce al `ci_apply`, dopo che il mirror
   ha caricato il CSV (§14.7), quindi il segno all'`INSERT` da solo non basta. Quando il runner **crea** il trigger
   su una tabella (non quando lo rigenera), registra le righe presenti con `user_insert = 'SEED'` o con il nome di
   un ruolo del migratore. È l'unica lettura di `user_insert`, ed è la risposta a Q16. Su un database nuovo, a quel
   momento ci sono solo le righe del CSV, con `user_insert = 'SEED'` perché anche l'audit nasce al `ci_apply`.
4. **Una riga senza segno è dell'installazione.** Il trigger la tratta come personalizzata: il software non la
   riscrive senza porta, e l'installazione la cancella come oggi.
5. **Il registro si scrive solo dal trigger.** La funzione trigger è `SECURITY DEFINER` (owner `zeroerp_owner`,
   `search_path` fissato) e l'app non riceve nessun `GRANT` su `dbops.seed_righe`. Una funzione trigger non si
   chiama direttamente, quindi l'app non può falsificare il registro. Dentro il trigger `session_user` riconosce
   ancora chi scrive; nessuna regola usa `current_user`.
6. **`dbops.fn_ruolo_del_migratore(p_ruolo name)` resta** (§15.6), per il runner e per
   `fn_sessione_del_migratore`. Cerca prima il nome in `pg_roles`: un nome che non è un ruolo vale `false`, non va in
   errore.

Che cosa chiude: il punto 1 (`user_insert` torna a essere solo audit), il 2 (nessuna domanda sui ruoli a ogni
`DELETE`), il 3 (si guarda la sessione), il 4 (il segno non dipende dai nomi dei ruoli) e la riga intatta
dell'installazione. Il costo: una scrittura nel registro all'`INSERT` del migratore, e un passaggio del runner
all'iscrizione di ogni tabella.

**Limite dichiarato.** Se la regola di una tabella si spegne e si riaccende, il runner ricrea il trigger e rifà la
lettura di `user_insert` sulle righe nate nel frattempo, con i difetti del §16.1 per quell'unico passaggio.

### 16.3 Che cosa cambia nel §15

| Dove | Prima | Ora |
| --- | --- | --- |
| §15.1, regola 6 | «nata dal seed» si legge da `user_insert` | si legge dal registro (§16.2) |
| §15.1, regola 8 | si regge la regola 6 | resta solo il presidio (Q17) |
| §15.2, eventi | `BEFORE UPDATE OR DELETE` | `BEFORE INSERT OR UPDATE OR DELETE`; riga nuova: «`INSERT`, il software: registra la riga come nata dal seed; l'installazione: passa» |
| §15.2, «il software, riga intatta» | passa su ogni riga intatta | passa solo su una riga nata dal seed e intatta; una riga senza segno è dell'installazione |
| §15.3 | «nata dal seed non si registra» | il registro tiene solo le righe nate dal seed; scritto solo dal trigger `DEFINER` |
| §15.4 | — | il runner, alla creazione del trigger, segna le righe presenti (§16.2, punto 3) |
| §15.6 | `fn_ruolo_del_migratore` con `pg_has_role` | prima la ricerca in `pg_roles` (§16.2, punto 6); solo il presidio, niente divieto (Q17) |
| §15.7, caso 6 | `DELETE` rifiutato con `user_insert = 'SEED'` o col nome del migratore | `DELETE` rifiutato su una riga segnata nel registro |
| §15.7, casi nuovi | — | (a) l'app che fa `UPDATE … user_insert` non sblocca niente; (b) una riga inserita da un verbo `DEFINER` chiamato dall'app è dell'installazione; (c) il runner segna le righe esistenti una volta, e alla rigenerazione non ripassa; (d) una riga dell'installazione mai modificata non la riscrive un `UPDATE` del software senza porta; (e) `fn_ruolo_del_migratore` su un nome che non è un ruolo: `false`, nessun errore |
| §15.8, giro 1 | punto 6 (divieto e presidio), punto 7 (tre codici) | solo il presidio, due codici (Q17) |
| §15.2, `UPDATE` del software in `SOLO_INSERIMENTO` | valori scartati nel registro e `WARNING` | niente valori scartati, tabella fuori dalla diagnosi (Q18); il `WARNING` resta (Q22, §16.13) |
| §15.7, caso 2 | la riga che c'è non cambia | e il registro non riceve valori scartati (Q18); parte il `WARNING` (Q22) |
| §15.10 | D5 | revocata da D10 |

### 16.4 Verifica nuova

| # | Che cosa | Stato |
| --- | --- | --- |
| V11 | Che cosa chiede `linee-guida-sql.md` a una funzione trigger `SECURITY DEFINER` (proprietario, `search_path`, `REVOKE` da `PUBLIC`), e se il progetto ne ha già una da prendere a modello | da fare |

### 16.5 Altri punti dell'analisi del 2026-11-17

1. **Un fatto corretto.** Il §15 diceva che su `email_template` l'audit c'è solo all'`INSERT`. La doc auto-generata
   lo dà anche all'`UPDATE` (`trg_email_template_audit_data_user_upd`). Il limite 1 del §15.11 vale anche per i
   template.
2. **`SOLO_INSERIMENTO` fa rumore.** Ogni riga di seed conta come personalizzata: a ogni ritocco del CSV il trigger
   scrive i valori scartati nel registro e alza un `WARNING`, e la diagnosi delle divergenze resta piena per
   `SISTEMA`. Se la diagnosi diventa un presidio a zero, è rosso per sempre. ✅ Q18, decisa il 2026-11-18: salto muto.
3. **Il §11.2 non vale più su queste tabelle.** Il CSV non spegne una riga personalizzata, e in `SOLO_INSERIMENTO`
   nessuna riga di seed: `attivo` è una colonna dell'installazione. Una riga di seed si ritira solo con la porta. Va
   scritto nei limiti (§15.11) e in `linee-guida-sql.md` §11.7.
4. **La chiave primaria fuori dagli elenchi.** Nel blocco per colonna di `email_template` (§15.4), `id` non sta in
   nessuno dei due elenchi: per D8 sarebbe una colonna non classificata. La PK si esclude per regola, come le colonne
   libere.
5. **Il registro orfano.** Il `DELETE` forward-only fatto con la porta (§15.2) toglie anche la riga del registro.
6. **Il nome della porta del seed** (`zeroerp.allow_…`) si fissa nel giro 1.

Verificato e che regge: l'ordine `a00` (i nomi veri sono `trg_<tabella>_a10_…` e `trg_<tabella>_audit_…`, quindi
`trg_<tabella>_a00_…` scatta per primo), `RETURN NEW` con le colonne rimesse da `OLD` (il blocco `DO` del mirror non
va in chiave duplicata), la strada scartata «carica solo se la tabella è vuota».

### 16.6 Le decisioni di Tid

✅ **Q17 e Q18 decise da Tid il 2026-11-18, come proposto.** Per Q17 vale la prima strada, solo il presidio; l'alternativa
(togliere anche il presidio) è scartata.

| # | Domanda | Proposta |
| --- | --- | --- |
| Q17 | Che cosa resta della regola 8 (username e ruoli disgiunti), ora che la regola 6 non si regge più su di lei | ✅ **Decisa:** resta solo il motivo `NOME_DI_RUOLO_DB` del presidio in `vw_credenziali_da_sanare`, perché una collisione conta solo all'iscrizione di una tabella (§16.2, punto 3). Escono il divieto in `fn_crea_auth_user`, il suo codice d'errore e R4. In alternativa si toglie anche il presidio e si scrive il limite: una collisione presente all'iscrizione fa «di seed» una riga dell'installazione, cioè l'errore va dalla parte sicura |
| Q18 | In `SOLO_INSERIMENTO` il salto del software scrive nel registro e alza il `WARNING`? (§16.5, punto 2) | ✅ **Decisa:** no. In `SOLO_INSERIMENTO` il salto è il comportamento atteso. Niente valori scartati e la tabella fuori dalla diagnosi delle divergenze. ⚠️ Il «niente `WARNING`» è rivisto dalla Q22 (§16.13): l'avviso resta |

### 16.7 Strada scartata: la toppa su `user_insert` (Tid, 2026-11-17)

Tenere D5 e correggere i sintomi: il trigger `a00` tiene fermo `user_insert`, e `fn_ruolo_del_migratore` cerca prima
in `pg_roles`. Chiude i punti 1 e 2 del §16.1, ma lascia aperti il 3 (`CURRENT_USER` dentro un verbo `DEFINER`) e il 4
(il significato che dipende dai ruoli), e tiene la regola 8 con R4 come vincolo fra domini. Scartata: corregge i
sintomi e lascia la causa, cioè un segno scritto dove l'app può scrivere.

### 16.8 Le verifiche del giro 1 (2026-11-18)

Tid ha dato il via il 2026-11-18, con i changeSet da `20261117-01`. Esiti, letti sul catalogo di dbdev e dello scratch
(`zeroerp_ruoli`), sui changelog, sui pgTAP e sul jar di Liquibase in uso:

| # | Esito |
| --- | --- |
| V2 | Non si prova a parte: è il caso 3 del §15.7, nel pgTAP. Per costruzione di PostgreSQL i `BEFORE` che vengono dopo `a00` ricevono il `NEW` già rimesso, e l'audit (`trg_<tabella>_audit_…`, dopo `a00` in ordine di nome) timbra solo le sue colonne |
| V5 | ✅ Letto in `liquibase-core` 5.0.4: l'opzione `liquibase.sql.showSqlWarnings` vale `TRUE` di default, e `JdbcExecutor.showSqlWarnings` passa gli `SQLWarning` del driver al log come `WARNING`. Il `WARNING` del trigger arriva nell'output del migrate; la conferma a video si ha al primo apply |
| V6 | ✅ Il censimento sta qui sotto, al §16.9 |
| V6-bis | ✅ `zeroerp_app` non è membro del proprietario di `dbops` (`zeroerp_owner`) né su dbdev né sullo scratch. In CI i test Django girano come `zeroerp_app` (`ci-validate.yaml`, passo «Django tests»); `DB_USER: zeroerp_owner` dell'env del job è quello di Liquibase. Il criterio `fn_sessione_del_migratore()` separa l'app dal migratore in tutti e tre gli ambienti |
| V7 | Dopo la decisione del §16.10: la traccia delle porte fuori dal seed |
| V8 | ✅ `test-totp-porta-v1` prova «l'app non è il migratore» girando **come app** (il runner di default): `session_user` non si simula. Ne segue che i casi del software (blocco `DO` del mirror, porta) e quelli dell'installazione stanno in **due file**: uno col runner di default, uno con `pgtap-runner: owner`, il cui motivo è che la scrittura del migratore non è raggiungibile dall'app. ⚠️ `test-sec-functions-owner-riservato-v1` (asserzione 12) cerca nel corpo di `fn_sessione_del_migratore` il testo `pg_has_role(session_user`: riscrivendola sopra `fn_ruolo_del_migratore` diventa rossa, e si adegua nello stesso giro |
| V10 | ✅ `config.fn_resolve_email_template` cerca la riga per `codice`, `unita_organizzativa_id`, `tipo_prestazione_id` e `lingua` (la stessa `UNIQUE NULLS NOT DISTINCT`), e le nove righe del CSV sono il ripiego di sistema (reparto e prestazione `NULL`, lingua `it`). Se l'installazione sposta una riga di seed su un reparto o su un'altra lingua, il ripiego sparisce come se avesse rinominato il codice: le tre colonne sono **del software**. Classificazione proposta, da approvare (§16.10): software `codice`, `unita_organizzativa_id`, `tipo_prestazione_id`, `lingua`, `variabili_disponibili`; installazione `oggetto`, `corpo_html`, `corpo_testo`, `attivo` |
| V11 | ✅ Il progetto ha già cinque funzioni trigger `SECURITY DEFINER` con `search_path` fissato (per esempio `vendite.trgfn_doc_guard_delete_solo_bozza`, `script.trgfn_sorgente_in_uscita`). `linee-guida-sql.md` §5 chiede la motivazione scritta e il `search_path` dichiarato nel `CREATE`, mai con `ALTER FUNCTION … SET` (§13.7) |

### 16.9 Il censimento delle porte (V6)

Letto il 2026-11-18 dal corpo vivo delle funzioni su dbdev, dai changelog, dai pgTAP e dal backend. Il backend **non
apre nessuna porta**. Le porte si dividono così:

**Di verbo** (una funzione la apre per sé e la richiude): `doc_cambio_stato`, `doc_ritira_legami`, `ddt_riconsegna`,
`ddt_riga_correggi_qta`, `ddt_riga_ritira_legame`, `listino_riga_rettifica`, `listino_versione_fine`,
`legame_distinta_chiudi`, `articolo_correggi_struttura`, `magazzino_posting_*`,
`allow_template_versione_pubblicazione_override`, `allow_user_emittente_delete_override`,
`allow_contabile_riga_delete_override`, `maintenance_reset_lotto_draft` (la apre `vendite.fn_cleanup_fatture_by_ids`),
`maintenance_indirizzi_dettaglio` (`dbops.fn_admin_merge_stradario`), `maintenance_toponomastica`
(`maintenance.proc_bump_toponomastica`). Per D7 restano come sono, anche quelle col prefisso `maintenance_`: il nome non
dice la specie, la dice chi la apre.

**Di manutenzione** (nessuna funzione la apre: solo il migratore a mano e i pgTAP):

| Porta | Chi la legge | pgTAP che la aprono, col runner di default (l'app) |
| --- | --- | --- |
| `zeroerp.allow_lock_columns_override` | `script.trgfn_lock_columns`, `script.trgfn_righe_natura_vendita` | 13 |
| `zeroerp.maintenance_ruoli_delete` (argomento di `DELETE_BLOCK`) | `script.trgfn_delete_block_by_guc` | 1 (`test-fn-disdetta-cliente`) |
| `zeroerp.maintenance_allow_delete_logs` | `vendite.trgfn_event_log_append_only`, `vendite.trgfn_logs_guard_delete` | 9 |
| `zeroerp.maintenance_allow_attivita_bypass` | `vendite.trgfn_attivita_fatturabili_guard_commessa` | 0 |

`allow_template_versione_chiusura_override` non ha più lettori nel catalogo vivo.

⚠️ **I pgTAP girano come app, e la porta stretta li fa diventare rossi.** I 23 file aprono la porta per costruire o
pulire i dati, non per provarla. Ognuno si legge: se apre la porta per pulire (`DELETE` di fixture in un test che
finisce in `ROLLBACK`), la pulizia si toglie, come è già stato fatto in `create-cliente.sql`; se apre la porta per
costruire uno stato che l'app non raggiunge, la fixture passa da un verbo o il file dichiara `pgtap-runner: owner` col
motivo. Le quattro porte e i sei lettori sono **una** regola (§13.2): per la regola del 2 passano tutti dal building
block nello stesso giro, oppure il giro si divide (§16.10).

### 16.10 Le decisioni prima di scrivere (Tid, 2026-11-18)

✅ **Q19 approvata come proposta; Q20 decisa per la strada A**: tutte e quattro le porte di manutenzione nel giro 1. La
strada dei due giri 1a/1b è scartata.

| # | Domanda | Proposta |
| --- | --- | --- |
| Q19 | Classificazione delle colonne di `email_template` (V10) | Come al V10: software `codice`, `unita_organizzativa_id`, `tipo_prestazione_id`, `lingua`, `variabili_disponibili`; installazione `oggetto`, `corpo_html`, `corpo_testo`, `attivo` |
| Q20 | Il perimetro della porta stretta nel giro 1 (§16.9) | **Tutte e quattro le porte di manutenzione** nel giro 1, con i sei lettori e i 23 pgTAP adeguati: è un difetto solo, e la regola del 2 vuole le copie ritirate nello stesso giro. In alternativa: giro 1a con il seed, la porta del seed e le due porte di `lock_columns` e `DELETE_BLOCK` (14 pgTAP); giro 1b con le due porte di `vendite` (9 pgTAP). Le due porte di `vendite` restano allora copie dichiarate fino al giro 1b |

### 16.11 Il piano del giro 1 (2026-11-18)

**Lo stampo.** La regola nuova si costruisce come `DELETE_BLOCK` (guida `automazione-db.md` §4.4): un registro proprio
con una riga per tabella, che porta l'interruttore (`enabled`) e il nome del trigger (`trigger_name`, risolto da
`dbops.fn_nome_oggetto_dichiarato` col template di default), un
runner che converge, una funzione di divergenze, la chiamata dentro `maintenance.proc_automations_lock_columns_job`
(convergenza del rilascio, `ci_ordine` 60, e giro notturno delle 21:10) e una rete `runAlways` in `90_end` che converge
a ogni migrate. Niente processo nuovo e niente job pgAgent nuovo. La rete di `90_end` fa nascere il trigger **alla
fine del primo migrate** anche su un database da zero, dopo `80_data`: le righe caricate dal CSV hanno ancora
`user_insert = 'SEED'` (l'audit nasce al `ci_apply`), e il runner le segna all'iscrizione (§16.2, punto 3).

**V7, la traccia delle porte.** Una sede sola per tutte le porte di manutenzione, quella del seed compresa: una tabella
nuova `dbops.porte_manutenzione_passaggi` (chiave, tabella, `id` della riga, operazione, `session_user`, istante), scritta
solo da `script.fn_porta_manutenzione_aperta`. Il §15.3 metteva «l'ultimo passaggio dalla porta» nel registro del seed:
con una sede sola il registro tiene il segno «nata dal seed», la personalizzazione e i valori scartati, e il passaggio
si legge dal diario. È la regola del 2 applicata alla traccia.

**I nomi.** La porta del seed: `zeroerp.allow_seed_primo_impianto_override`. Il trigger:
`trg_{table}_a00_seed_primo_impianto_ins_upd_dlt`. Il registro delle tabelle: `dbops.automazione_seed_primo_impianto`
(tabella, `solo_inserimento`, `colonne_software`, `colonne_installazione`, `enabled`, motivo). I codici: due per
l'operatore (`E_SEED_RIGA_NON_CANCELLABILE`, `E_SEED_COLONNA_DEL_SOFTWARE`) e uno tecnico del runner
(`E_SEED_PRIMO_IMPIANTO`, come `E_DELETE_BLOCK`).

**La postura.** `dbops.seed_righe` e `dbops.porte_manutenzione_passaggi` sono in sola lettura per l'app, nelle tre sedi
di `linee-guida-sql.md` §11.8 (il changeSet `90_end` che revoca subito, il loop dei grant di `ci_apply`, la fase `post`
del provisioning), con il loro pgTAP di postura.

| # | Fase | Che cosa |
| --- | --- | --- |
| 1 | `00_schema` | `dbops.seed_righe` |
| 2 | `00_schema` | `dbops.porte_manutenzione_passaggi` |
| 3 | `00_schema` | `dbops.automazione_seed_primo_impianto` |
| 4-5 | — | ⚠️ Ritirati il 2026-11-18: la regola non entra in `automation_rules_tbl` (vicolo cieco qui sotto) |
| 6 | `20_code` | `dbops.fn_ruolo_del_migratore` |
| 7 | `20_code` | `dbops.fn_sessione_del_migratore` sopra di lei |
| 8 | `20_code` | `script.fn_porta_manutenzione_aperta` |
| 9-14 | `20_code` | i sei lettori delle porte di manutenzione (§16.9) passano dal building block |
| 15 | `20_code` | `dbops.fn_seed_primo_impianto_argomenti`, la grammatica degli argomenti del trigger, letta dal trigger e dalle divergenze |
| 16 | `20_code` | `script.trgfn_seed_primo_impianto` |
| 17 | `20_code` | `dbops.fn_seed_primo_impianto_divergenze` |
| 18 | `20_code` | `dbops.fn_run_automations_seed_primo_impianto` |
| 19 | `20_code` | `maintenance.proc_automations_lock_columns_job` chiama anche il runner nuovo |
| 20 | `20_code` | `dbops.vw_credenziali_da_sanare`, motivo `NOME_DI_RUOLO_DB` |
| 21 | `80_data` | il registro delle tabelle, col suo CSV (le due righe del §15.4 con la classificazione di Q19) |
| 22 | `80_data` | i CSV esistenti: i tre codici in `codici_errore` e `messaggi_errore`, il presidio in `dbops.presidi` |
| 23 | `90_end` | la rete che converge a ogni migrate |
| 24 | `90_end` | la postura delle due tabelle nuove, più il loop di `ci_apply` e il provisioning |

**Vicolo cieco: la riga in `automation_rules_tbl` (2026-11-18).** La prima stesura del piano seguiva `CODICE_MAIUSCOLO`, con
una riga in `automation_rules_tbl`. Il vocabolario di `rule_type` è un `CHECK` nato in `90_end`
(`20261109-75`, mergiato) con l'elenco di oggi. Da zero la riga nuova entrerebbe in `80_data` e quel `90_end` la
rifiuterebbe all'`ADD CONSTRAINT`; su dbdev il vincolo c'è già e la rifiuterebbe in `80_data`. Allargare il vocabolario
non ha una fase che vada bene in tutti e due i casi (`linee-guida-sql.md` §11.14). `DELETE_BLOCK` e `GUARD utility` non
hanno riga in `automation_rules_tbl` per la stessa forma: il registro della regola porta già l'interruttore e il nome.

Poi i pgTAP (i due file nuovi del §15.7 con i casi del §16.3, la postura, `test-sec-functions-owner-riservato-v1`
adeguato, i 23 file del §16.9) e la documentazione (§15.8, punto 9).

### 16.12 Lo stato del giro 1 (2026-11-18)

**Scritti i changeSet `20261117-01` … `-21`** (la numerazione del §16.11 si è stretta: i passi 4-5 sono ritirati, e
`script.trgfn_righe_natura_vendita` non è un lettore della porta, la nomina solo nei commenti):

| ChangeSet | Che cosa |
| --- | --- |
| `-01` … `-03` | `dbops.seed_righe`, `dbops.porte_manutenzione_passaggi`, `dbops.automazione_seed_primo_impianto` |
| `-04`, `-05` | `dbops.fn_ruolo_del_migratore`; `dbops.fn_sessione_del_migratore` sopra di lei |
| `-06` | `script.fn_porta_manutenzione_aperta` |
| `-07` … `-11` | i cinque lettori delle porte di manutenzione: `script.trgfn_lock_columns`, `script.trgfn_delete_block_by_guc`, `vendite.trgfn_event_log_append_only`, `vendite.trgfn_logs_guard_delete` (la porta di verbo del reset del lotto resta com'è), `vendite.trgfn_attivita_fatturabili_guard_commessa` |
| `-12` … `-15` | la grammatica degli argomenti, la funzione trigger, le divergenze, il runner |
| `-16` | `maintenance.proc_automations_lock_columns_job` chiama anche il runner |
| `-17`, `-18` | `script.fn_credenziali_con_nome_di_ruolo` e il motivo `NOME_DI_RUOLO_DB` della vista |
| `-19` | il mirror di `dbops.automazione_seed_primo_impianto` (CSV nuovo, due righe) |
| `-20`, `-21` | la rete di `90_end`; la postura in sola lettura per l'app, con il loop di `ci_apply` e il provisioning |

**Che cosa cambia nei lettori, oltre alla porta stretta.** La porta si chiede nel punto in cui il controllo rifiuterebbe,
non in testa: il diario registra le righe forzate, non ogni scrittura a GUC accesa. Nei due guard dei log la retention
si guarda prima della porta (il risultato è lo stesso). «Accesa» vale `on`, `true` o `1` per tutte le porte; il guard
delle attività accettava anche le altre forme di `::boolean` e solo un superuser, ora la sessione del migratore.

**Provato** con `scripts/prova_changeset.py` sullo scratch, il 2026-11-18: l'estratto di tutti i changeSet SQL gira per
intero, e dopo il `ROLLBACK` il catalogo è identico. Il `loadUpdateData` del `-19`, che la prova non copre,
l'ha provato l'apply: le due colonne `text[]` di `email_template` arrivano dal CSV nella forma `{a,b}` come scritte, e
quelle di `email_account` restano `NULL`.

**Scritti anche (2026-11-18):**

* i codici `E_SEED_RIGA_NON_CANCELLABILE`, `E_SEED_COLONNA_DEL_SOFTWARE` (classe `CONFLITTO_STATO`, senza segnaposto) ed
  `E_SEED_PRIMO_IMPIANTO` (`TECNICO`, del runner), in coda a `codici_errore.csv` e `messaggi_errore.csv` (id 1514-1516);
* il terzo motivo nel testo del presidio delle credenziali (`presidi.csv`, `presidi_testi.csv`);
* i pgTAP nuovi: `config/test-seed-primo-impianto-installazione-v1` (24, come app), `dbops/test-seed-primo-impianto-software-v1`
  (26, `pgtap-runner: owner`), `dbops/test-seed-primo-impianto-postura-v1` (9, come app);
* `dbops/test-sec-functions-owner-riservato-v1`, asserzione 12: segue la domanda fino a `fn_ruolo_del_migratore`;
* la documentazione: `linee-guida-sql.md` §11.7 (tre specie, la specie di primo impianto), `automazione-db.md` §4.9 e «Le
  porte di manutenzione», `gestione-mail.md` (account e template restano dell'azienda).

**I pgTAP del §16.9: 22 file, non 23** (`create-cliente.sql` nomina la porta solo in un commento):

| Gruppo | File | Che cosa |
| --- | --- | --- |
| pulizia dei log prima del `ROLLBACK` | `test-fondi-fattura`, `test-fattura-utils-critical-termini`, `test-fondo-fattura-eseguito`, `test-posta-riga-tardiva-v1`, `test-contabile-validabile-v1`, `test-abbinamento-rata`, `test-fn-posta-contabile` | tolta la pulizia (il `ROLLBACK` basta), e con lei l'`ok(true, 'Cleanup completato')`: il `plan` scende di uno dove c'era |
| porta del lucchetto accesa «per sicurezza» | `test-billing-account-auto-link-ef`, `test-fn-resolve-emittente-for-user`, `test-fn-check-user-can-create-ba`, `test-trgfn-default-emittente-fiscale-v1`, `test-trgfn-preventivi-default-emittente-e-guard-coerenza`, `test-trgfn-documenti-default-valuta` | tolta la riga: nessuno di questi file scrive una colonna bloccata (letto sugli `UPDATE` contro le 114 tabelle col lucchetto) |
| provano la porta | `test-articoli-seed-uom-base-lock` (8), `test-event-log-append-only` (5), `test-logs-guard-delete` (4, 7) | come app la GUC accesa non apre più: le asserzioni dicono «rifiutato». Che il migratore apra lo prova il test del lato software |
| la porta per arrivare al `CHECK` | `test-uom-fattore-e-regole-v1` (19) | il `CHECK` della riga base si asserisce sulla sua esistenza: sull'`UPDATE` parla prima il lucchetto |
| pulizia con `DELETE_BLOCK` | `test-fn-disdetta-cliente` | tolta la pulizia finale; quella iniziale toglie gli avanzi delle versioni che committavano: su un database nuovo non trova righe, su dbdev gli avanzi eventuali si tolgono una volta a mano, dal migratore |
| lo stato legacy (Q21) | `test-fn-list-preventivi-da-pushare-natura-aware-v1` (3), `test-vw-preventivi-smistamento-v1` (5, e il pregresso nei contatori 1, 7, 8), `test-righe-natura-vendita-congelata-v1` (15) | la riga a natura `NULL` esce dai tre file, che restano come app; i suoi casi stanno in `vendite/test-righe-natura-vendita-legacy-v1` (5, `pgtap-runner: owner`), con in più il passaggio nel diario delle porte |

**Provato** con `scripts/prova_changeset.py` sullo scratch, con uno YAML d'appoggio fuori dal repo che carica le due righe
del registro e i tre codici (ciò che fanno all'apply il `-19` e i CSV):

* `test-seed-primo-impianto-software-v1`: 26 su 26;
* `test-seed-primo-impianto-installazione-v1` e `-postura-v1`, da proprietario: verdi le asserzioni di forma e i rifiuti che
  valgono per tutti; rosse per costruzione quelle che dipendono da chi scrive (il proprietario è il software). L'esito
  vero è la corsa come app, dopo l'apply;
* `test-logs-guard-delete`, `test-event-log-append-only`, `test-articoli-seed-uom-base-lock`, `test-uom-fattore-e-regole-v1`,
  `test-abbinamento-rata`, `test-sec-functions-owner-riservato-v1`: stessi esiti prima e dopo l'estratto (da proprietario la
  porta si apre, quindi le asserzioni «come app» sono rosse in tutte e due le corse);
* `test-fn-disdetta-cliente`: lo script non lo lancia (il file apre con un `DO` prima del `BEGIN`).

**Scostamenti dal §15, dichiarati:**

* il presidio a zero delle divergenze (D8) è il pgTAP (`test-seed-primo-impianto-installazione-v1`, asserzione 3), come
  per `DELETE_BLOCK`: il catalogo `dbops.presidi` elenca viste, e le divergenze sono una funzione;
* la traccia della porta del seed sta nel diario comune `dbops.porte_manutenzione_passaggi`, non nel registro (V7, §16.11).

**Applicato su dbdev il 2026-11-18 (Tid), `-01` … `-22`, pgTAP verdi.** Letto sul database dopo l'apply: la rete di `90_end`
non lascia divergenze (`dbops.fn_seed_primo_impianto_divergenze(NULL)` vuota); il runner ha iscritto le righe di seed già
presenti, 1 di `email_account` e 9 di `email_template` (`segnata_da = ISCRIZIONE`).

**Dopo l'apply (2026-11-18):**

* ✅ i pgTAP, verdi (Tid);
* ✅ la doc auto-generata (Tid);
* ✅ la baseline B-7 (`db/baseline-codici-errore-famiglie.tsv`), misurata come app in sola lettura e senza `--update`,
  uguale su dbdev e sullo scratch. I tre codici nuovi non entrano: la misura non ne legge famiglie note. Esce
  `E_DELETE_NOT_ALLOWED` (era `VALORE_ATTESO`, 4 punti): dal `-08` `script.trgfn_delete_block_by_guc` lo alza dopo la
  porta, non più dentro un `IF` sulla GUC, e la misura non lo classifica. È questo cantiere, non un altro. Dopo, il
  confronto dà zero accumuli, zero ristretti, zero rientri;
* ✅ la riga `SISTEMA` di dbdev: non serve ripristinarla. Porta già la configurazione vera, scritta dall'interfaccia il
  2026-11-17, e in solo inserimento il CSV non la riscrive più, intatta o no. Il §12.10 («ripristinata dopo l'apply, così
  la marca il trigger») valeva per la forma per riga, prima della Q11.
* ✅ le pagine `manual/` (2026-11-18), il punto 9 del piano (§15.11), che il giro aveva lasciato indietro:
  * nuove: `script.fn_porta_manutenzione_aperta`, `script.trgfn_seed_primo_impianto`,
    `script.fn_credenziali_con_nome_di_ruolo`, `dbops.fn_ruolo_del_migratore`,
    `dbops.fn_seed_primo_impianto_argomenti`, `dbops.fn_seed_primo_impianto_divergenze`,
    `dbops.fn_run_automations_seed_primo_impianto`, `dbops.seed_righe`, `dbops.automazione_seed_primo_impianto`,
    `dbops.porte_manutenzione_passaggi`;
  * aggiornate: `dbops.fn_sessione_del_migratore`, i cinque lettori della porta (`script.trgfn_lock_columns`,
    `script.trgfn_delete_block_by_guc`, `vendite.trgfn_event_log_append_only`, `vendite.trgfn_logs_guard_delete`,
    `vendite.trgfn_attivita_fatturabili_guard_commessa`), `dbops.automation_delete_block`,
    `maintenance.proc_automations_lock_columns_job`, `dbops.vw_credenziali_da_sanare`, `config.email_account`,
    `config.email_template`;
  * debito trovato e pagato: la pagina di `vendite.trgfn_event_log_append_only` descriveva il corpo di prima del
    2026-08-22 («nessuna porta», «nessun codice»), quella del job non nominava il runner del codice in maiuscolo.
    Riscritte sul corpo vivo;
  * ⚠️ la doc auto-generata è stata rigenerata **prima** delle pagine nuove: le pagine generate dei dieci oggetti nuovi
    non le includono finché non si rigenera.

**Limiti nuovi, dichiarati:**

* chi lancia come migratore un comando che scrive una colonna dell'installazione su una riga di seed in solo inserimento
  (per esempio `manage.py ricifra_campi_cifrati` con l'utente del migrate invece che con quello del backend) non scrive:
  dal `-22` lo dice un `WARNING`, non un errore (Q22). Oggi il comando gira con `.env.systemd`, cioè come app;
* il migratore che con la porta del lucchetto cambia `codice_interno` su una riga in solo inserimento lo vede rimesso
  da `OLD`: apre anche la porta del seed.

### 16.13 Le decisioni Q21 e Q22 (Tid, 2026-11-18)

✅ **Decise da Tid il 2026-11-18, come proposto.** Il giro 1 era già applicato su dbdev, quindi la Q22 non riscrive il
`-13`: entra come changeSet nuovo.

* **Q21** — `vendite/test-righe-natura-vendita-legacy-v1` (plan 5, `pgtap-runner: owner`): la natura scritta `NULL`
  dalla porta, il passaggio nel diario, il push su commessa, la vista righe, l'aggregata. I tre file d'origine restano come
  app, senza la riga legacy: `-da-pushare-natura-aware-v1` plan 3, `-smistamento-v1` plan 9 (tre righe, contatori scesi),
  `-congelata-v1` plan 14. Provati sullo scratch da proprietario: 5, 3, 9 e 14 su 14 verdi; la corsa come app dei tre è
  di Tid;
* **Q22** — `20_code/script/20261117-22-update-trgfn-seed-primo-impianto-warning-solo-inserimento`: in solo inserimento
  il salto alza il `WARNING`, senza scrivere il registro; il `COMMENT` della funzione lo dice; il rollback riporta il
  corpo del `-13`. Provato sullo scratch: l'estratto gira, il catalogo resta identico, e nel test del lato software
  (26 su 26) il `WARNING` su `config.email_account` compare solo con il `-22`. L'asserzione 9 dice «il registro resta
  pulito»; `automazione-db.md` §4.9 aggiornata;
* ✅ applicato su dbdev il 2026-11-18, pgTAP verdi (Tid). ⚠️ La doc auto-generata della funzione (il `COMMENT`) si
  rigenera con quella del giro.


| # | Domanda | Proposta (✅ approvata) |
| --- | --- | --- |
| Q21 | Tre pgTAP costruiscono una riga di documento con la natura di vendita `NULL`, lo stato delle righe legacy. L'app non lo raggiunge per nessuna strada (l'`INSERT` la eredita dall'articolo, la colonna è bloccata), e con la porta stretta lo costruisce solo il migratore. Come si prova? | **Si separa**: i casi della riga legacy escono dai tre file e vanno in un file `pgtap-runner: owner` per dominio, col motivo «lo stato si costruisce solo dalla manutenzione»; il resto dei tre file resta come app e continua a esercitare la RLS. Scartato: tutto il file `owner` (si perde la RLS anche sui casi che l'app raggiunge); un helper DEFINER che spegne il lucchetto (darebbe all'app una strada per scrivere la natura) |
| Q22 | In solo inserimento il salto del software è muto (Q18). Lo è anche per il migratore che scrive a mano, fuori dal mirror, e perde la scrittura senza saperlo | Il `WARNING` resta anche in solo inserimento; restano fuori i valori scartati nel registro e la diagnosi. Il rumore è un avviso nel log del migrate quando il CSV della tabella cambia, cioè di rado |

### 16.14 Come l'app legge «nata dal seed», e solo disattivazione (giro 2, 2026-11-19)

**La domanda del BE (2026-11-19).** «Come legge l'app il segno nata dal seed? Un LEFT JOIN su `dbops.seed_righe` in due
query, oppure una funzione o una vista del DB, che preferirei per la regola del 2.» Ordine proposto: R2, poi la
risposta, poi R1 e R3 insieme.

**La risposta: una vista per tabella, che il backend legge accanto alla tabella.** Il LEFT JOIN su `dbops.seed_righe`
si potrebbe fare (l'app ha `SELECT` dal `-21`), ma ricopia nel backend la chiave del registro (schema e tabella di
testo, l'id come testo) in quattro query. Soprattutto, a R3 il segno non basta: servono le colonne da spegnere, e dopo
la Q19 sono cinque, non le due che R3 nominava. Un elenco nel backend ripete il CSV della regola e diverge al primo
cambio. La vista dà le due cose dalle stesse funzioni che legge il guard.

#### Le decisioni di Tid (2026-11-19)

| # | Domanda | Decisione |
| --- | --- | --- |
| Q23 | La forma della risposta: la funzione per riga proposta in chat, o le superfici di riga del §12.5 di linee-guida-sql (il motivo di «elimina» in una vista, iscritta in `config.azioni_riga`) | ✅ La vista. Con la Q24 la parte su «elimina» cade: resta la vista, senza azione di riga |
| Q24 | Un account o un template dell'installazione che ha già spedito: «elimina» acceso, e il `DELETE` muore sulla FK `NO ACTION` di `email_log` / `email_outbox` | ✅ **Solo disattivazione.** Account e template non si cancellano, nemmeno quelli dell'azienda: si spengono. «La cancellazione potrebbe anche non esistere: l'importante è che sia disattivabile» |

**Che cosa ha scoperto la Q24.** Spegnere non era sempre possibile. La regola ATTIVO genera
`dbops.trgfn_prevent_deactivate_if_children` su ogni FK verso una tabella con `attivo`: su account e template ce n'erano
quattro, verso `email_log` ed `email_outbox`. Il log e la coda non hanno `attivo`, quindi conta ogni riga: un account o
un template che aveva spedito una volta **non si spegneva più** (`E_ATTIVO_BLOCK_CHILDREN_EXIST`), e non si cancellava
per la FK. Nessun gesto lo toglieva dall'uso. La forma c'è già, ed è la stessa delle stampe (`documenti_generati`,
eccezioni del 2026-11-14): la mail spedita è **storia**, la bozza è **provenienza**, e la FK si dichiara eccezione in
`dbops.automazione_attivo_eccezioni`. Il `require` che va via con lei scatta solo quando la riga nasce, e ripete i
risolutori (`config.fn_resolve_email_account` e `config.fn_resolve_email_template` leggono solo le righe accese).

#### I changeSet

| ChangeSet | Che cosa |
| --- | --- |
| `-23` | `dbops.fn_seed_riga(regclass, text)`: la voce del registro di una riga, nessuna riga = dell'installazione. Estratta dal guard (regola del 2) |
| `-24` | `dbops.fn_seed_colonne_del_software(regclass)`: le colonne del software dal **montaggio** del trigger, con la grammatica del guard; vuoto, mai `NULL` |
| `-25` | `script.trgfn_seed_primo_impianto`: la voce del registro da `fn_seed_riga`. Il resto del corpo è identico (rollback = il corpo vivo del `-22`) |
| `-26` | `config.vw_email_account_seed`: `email_account_id`, `nata_dal_seed`, `campi_del_software` |
| `-27` | `config.vw_email_template_seed`: `email_template_id` e le stesse due colonne |
| `-28` (`90_end`) | Provisiona subito su dbdev: `fn_run_automations_delete_block` su `config` e `fn_ritira_attivo_eccezioni()`. Da zero lo fa il `ci_apply` |
| CSV | `dbops/automation_delete_block_ruoli.csv`, righe 9 e 10: `config.email_account` e `config.email_template`, porta `zeroerp.maintenance_email_delete` |
| CSV | `dbops/automazione_attivo_eccezioni.csv`, quattro righe: `email_log` ed `email_outbox` verso `email_account_id` ed `email_template_id`, col motivo |
| CSV | `config/messaggi_errore.csv` e `config/codici_errore.csv`: la soluzione di `E_SEED_RIGA_NON_CANCELLABILE` non promette più che «le righe create dall'azienda si eliminano» |

* **I campi si leggono dal montaggio, non da `dbops.automazione_seed_primo_impianto`.** Il guard rifiuta coi suoi
  argomenti: la vista legge gli stessi, con la stessa funzione. Il campo è spento esattamente dove il guard rifiuta,
  anche nella finestra fra il migrate e il `ci_apply` (§14.7). Il nome è `campi_del_software` e non
  `non_editable_fields` (la forma delle capability dei documenti): la colonna non elenca i campi fermi per altre
  ragioni, come `codice_interno` degli account (`trgfn_lock_columns`), e un nome generico prometterebbe l'elenco intero.
* **Le colonne del software valgono per la tabella**: la vista le legge una volta; per riga si chiede solo se la riga
  è nata dal seed.
* **Il blocco della `DELETE` è il building block che c'era** (`dbops.automation_delete_block`, §4.4 di
  `automazione-db.md`): `BEFORE DELETE`, `E_DELETE_NOT_ALLOWED`, porta solo per il migratore. Sulla riga di seed parla
  prima il guard del seed (`a00` viene prima di `a10`), con `E_SEED_RIGA_NON_CANCELLABILE`. Il migratore che ritira
  un template di seed apre **due** porte, quella del seed e `zeroerp.maintenance_email_delete`.
* **Scartato** in questo giro, con la Q24: la check `script.fn_check_seed_riga_eliminabile` e le due righe di
  `config.azioni_riga` (`ELIMINA_EMAIL_ACCOUNT`, `ELIMINA_EMAIL_TEMPLATE`), scritte e mai applicate. Un'azione che
  non esiste non ha un motivo per essere spenta.

**Provato** con `scripts/prova_changeset.py` sullo scratch (2026-11-19), con uno YAML d'appoggio fuori dal repo che
carica le righe dei due registri: l'estratto gira per intero, catalogo identico dopo il `ROLLBACK`.

* `config/test-posta-solo-disattivazione-v1` (nuovo, plan 14, come app): 11 su 14 da proprietario. Il 3, il 5 e il 10
  sono rossi per costruzione: il template che il proprietario inserisce nasce dal seed. L'esito vero è la corsa come
  app, dopo l'apply. ⚠️ Sullo scratch `SISTEMA` non ha mail nello storico: il caso della Q24 (si spegne dopo aver
  spedito) lo prova il test 7 su dbdev, dove ne ha, e lo garantisce il test 2 (nessun trigger ATTIVO verso lo storico);
* `dbops/test-seed-primo-impianto-software-v1`: 27 su 27 (nuovo il 13: con la sola porta del seed la `DELETE` la
  ferma il blocco; il ritiro passa dalle due porte);
* `config/test-fn-resolve-email-template`: 12 su 12 (il test 9 spegne il livello 1 invece di cancellarlo);
* `config/test-fn-resolve-email-account`: 5 su 7 da proprietario; il 6 e il 7 sono rossi per costruzione (l'`UPDATE` del
  migratore su una tabella in solo inserimento si scarta). Il file torna a girare **come app**: il fixture cancellava
  `SISTEMA` e lo ricreava da proprietario, una strada che il giro 1 aveva già chiuso due volte. Ora aggiorna
  `SISTEMA` e lo spegne coi suoi figli;
* senza regressioni, stessi esiti prima e dopo: `config/test-seed-primo-impianto-installazione-v1` (gli 11 rossi da
  proprietario, per costruzione; il 18 ora si aspetta `E_DELETE_NOT_ALLOWED`), `dbops/test-automazione-attivo-eccezioni-v1`
  9 su 9, `dbops/test-delete-block-convergenza-v1` 18 su 18, `dbops/test-delete-block-audit-v1` 7 su 7,
  `config/test-azioni-riga-registro-v1` 8 su 8.

**Documentazione:** pagine `manual/` nuove di `dbops.fn_seed_riga`, `dbops.fn_seed_colonne_del_software`,
`config.vw_email_account_seed`, `config.vw_email_template_seed`; aggiornate `script.trgfn_seed_primo_impianto`,
`dbops.seed_righe`, `dbops.automazione_attivo_eccezioni` (le righe della posta), `dbops.automation_delete_block` (la
seconda famiglia); la guida `gestione-mail.md` (account e template si spengono, non si eliminano). La tabella degli
endpoint della guida la corregge il BE con R1-BE.

#### La richiesta al team BE/FE (sostituisce R1 e R3 del §15.12)

**Chi cambia per primo:** il DB (questo giro, da applicare). R2 non aspetta niente; il resto parte dopo l'apply.
⚠️ Corretto il 2026-11-19: il frontend **non ha** un pulsante «elimina» né sugli account né sui template (le API di
`frontend/src/amministrazione/api/amministrazione.js` non chiamano nessuna `DELETE`). La cancellazione esiste solo
nel backend.

| # | Che cosa | File |
| --- | --- | --- |
| R2 | I due codici nella tassonomia: `E_SEED_RIGA_NON_CANCELLABILE` ed `E_SEED_COLONNA_DEL_SOFTWARE`, classe `CONFLITTO_STATO`, senza segnaposti. `E_SEED_PRIMO_IMPIANTO` è del runner (`TECNICO`) e non arriva al backend. Con la rigenerazione dei messaggi arriva la soluzione corretta di `E_SEED_RIGA_NON_CANCELLABILE` | `docs/it/dev/api.md` §Tassonomia errori; i file generati dei messaggi (`backend/apps/core/services/error_messages_fallback.py`) |
| R1-BE | **Si toglie la cancellazione**: il `DELETE` sul dettaglio dell'account e del template, e i due metodi del repository. Dopo l'apply il DB la rifiuta sempre (`E_DELETE_NOT_ALLOWED`, oppure `E_SEED_RIGA_NON_CANCELLABILE` sulla riga di seed): un endpoint che risponde solo con un errore è un contratto falso | `backend/apps/amm_software/api/email_views.py` (`EmailAccountDetailView.delete`, `EmailTemplateDetailView.delete` e le docstring «DELETE: elimina»); `backend/apps/core/db/email_repository.py` (`delete_account`, `delete_template`); `backend/apps/amm_software/tests/api/test_email_views_fase6.py` (i casi `eliminazione`); `docs/it/backend/core/manual/api_email.md`; `docs/it/guide/gestione-mail.md` §Endpoint API (le due righe `GET/PATCH/DELETE`) |
| R1-BE-bis | Lista e dettaglio leggono la superficie con un `LEFT JOIN` su `<tabella>_id = id` ed espongono `nata_dal_seed` e `campi_del_software`. Nessun predicato sul registro e nessun elenco di colonne nel backend | `backend/apps/core/db/email_repository.py` (`list_accounts`, `get_account`, `list_templates`, `get_template`); `backend/apps/amm_software/api/email_views.py` (le quattro risposte); `docs/it/backend/core/manual/api_email.md` |
| R1-BE-ter | Alla conferma di una bozza la mail parte con l'account appena risolto (`account_di_invio`), ma il log scrive l'account della bozza (`email_account_id=outbox["email_account_id"]`). Il log deve dire con quale account la mail è partita: `account["id"]`. Prima il `require` sul log faceva fallire l'invio di una bozza il cui account era stato spento; dal `-28` il log lo accetta e direbbe il falso | `backend/apps/core/services/email_outbox_service.py` (`confirm_and_send`) |
| R3 | I campi in `campi_del_software` sono spenti nel form, col motivo: il testo lo sceglie il FE (il messaggio di `E_SEED_COLONNA_DEL_SOFTWARE` dice già perché). Sul template di seed oggi sono codice, reparto, tipo di prestazione, lingua e variabili disponibili; sugli account l'elenco è vuoto. Facoltativo: `nata_dal_seed` come segno «di sistema» sulla riga | `frontend/src/amministrazione/components/EmailTemplateDrawer.vue`, `EmailAccountDrawer.vue`; gli store `frontend/src/amministrazione/stores/emailTemplates.js` ed `emailAccounts.js` se tengono la forma della risposta |
| R-test | Un test del repository: una riga di seed porta il segno e i campi, una riga creata dal test no; un account che ha spedito si spegne | `backend/apps/core/tests/db/` (accanto ai test mail esistenti) |

Nessuna chiave i18n nuova: «elimina» non c'è, e il motivo dei campi spenti lo sceglie il FE.

**Esito del team BE/FE (2026-11-20).** Fatti e committati (`185f7207a`, 2026-11-20); riscontrati sul codice il
2026-11-20, all'arrivo del riallineamento del team DB.

- **R2**: `E_SEED_RIGA_NON_CANCELLABILE` ed `E_SEED_COLONNA_DEL_SOFTWARE` stanno nella policy generata
  (`error_policies_generated.py`, classe `CONFLITTO_STATO`) e nei messaggi di ripiego
  (`error_messages_fallback.py`), senza segnaposti. La tassonomia di `api.md` non elenca i singoli codici, ma
  li registra con la classe: non c'è una riga da aggiungere lì. In `docs/it/backend/core/manual/api_email.md`
  `E_SEED_COLONNA_DEL_SOFTWARE` sta nella tabella degli errori, `E_SEED_RIGA_NON_CANCELLABILE` nel testo sulla
  cancellazione (l'endpoint non esiste più: il codice arriva solo a chi scrive sul DB).
- **R1-BE**: il `DELETE` sul dettaglio di account e template non esiste più (405; le docstring di
  `email_views.py` dicono «Nessun DELETE … si spegne», Q24), e `delete_account` / `delete_template` sono tolti dal
  repository. In `api_email.md` e in `gestione-mail.md` resta solo il `DELETE` degli allegati, che non è di
  questo brief.
- **R1-BE-bis**: `list_accounts`, `get_account`, `list_templates` e `get_template` (`email_repository.py`) leggono
  `config.vw_email_account_seed` / `config.vw_email_template_seed` in `LEFT JOIN` sull'id ed espongono
  `nata_dal_seed` e `campi_del_software`; nessun elenco di colonne nel backend. Documentato in `api_email.md`.
- **R1-BE-ter**: in `confirm_and_send` (`email_outbox_service.py`) il log scrive l'account con cui la mail parte
  (`account_di_invio`, passato a `send_raw`), non quello della bozza. Adeguata insieme a R5 (§16.16).
- **R3**: `EmailAccountDrawer.vue` ed `EmailTemplateDrawer.vue` spengono i campi in `campi_del_software` col
  motivo e li tolgono dal PATCH (BB `campoDelSoftware` + `senzaCampiFermi`, gli stessi poi usati da R-UI-sup del
  §16.15); il segno «di sistema» compare sulle righe `nata_dal_seed`.
- **R-test**: `backend/apps/core/tests/db/test_email_seed_primo_impianto_db.py`, sul DB vero: il template e
  l'account di seed portano segno e campi, un campo del software non si modifica, account e template non si
  cancellano, un account che ha spedito si spegne.

### 16.15 Il censimento delle tabelle di `ui` (richiesta del brief `ui`, Q27, 2026-11-20)

Chiesto dal [brief-db-revisione-ui](brief-db-revisione-ui.md) (Q27, Tid 2026-11-20): le tabelle di catalogo di `ui`
sono mirror `runOnChange` (`loadUpdateData`) che l'app scrive dalle pagine admin, e i giri di quel brief che toccano i
CSV di `ui` partono dopo la loro iscrizione (linee-guida-sql §11.7: una tabella entra in un rilascio precedente al primo
ritocco del suo CSV). Letti la struttura (doc auto-generata del 2026-11-14) e il codice che le scrive
(`backend/apps/ui/db/ui_admin_repository.py`: INSERT, UPDATE e DELETE su tutte e quattro). Le domande sono le **QU1-QU4**,
numerate a parte per non confonderle con le Q di questo brief e di quello di `ui`.

**Chi scrive che cosa, oggi.** L'app aggiorna `codice`, `descrizione`, `schema_dati`, `vista_sql`, `note`, `attivo`
della definizione; tutte le colonne della colonna tranne `lista_id`; `codice`, `descrizione`, `is_default`,
`pagina_dimensione`, `ordinamento_default`, `filtri_default`, `attivo` del preset; la composizione la riscrive per intero
(DELETE + INSERT). Cancella definizioni, colonne e preset.

#### La classificazione proposta (QU1)

Tutte e tre per colonna: la riga è mista. Il criterio per le colonne del software è §11.7: la chiave di ricerca e le
regole che il codice legge.

| Tabella | Del software | Dell'installazione |
| --- | --- | --- |
| `ui.lista_definizione` | `codice`, `descrizione`, `schema_dati`, `vista_sql`, `multi_emittente`, `perimetro_emittente` | `note`, `attivo`, `ricerca_min_caratteri` |
| `ui.lista_colonna` | `lista_id`, `codice`, `campo_sorgente`, `tipo_colonna`, `tipo_dato`, `formato`, `filtrabile`, `ordinabile`, `ricercabile_full`, `sensibile`, `etichetta_i18n_key` | `etichetta`, `etichetta_estesa`, `larghezza_default`, `ordine_default`, `allineamento`, `gruppo`, `gruppo_ordine`, `esportabile`, `priorita`, `attivo` |
| `ui.lista_preset` | `lista_id`, `codice`, `ambito`, `profilo_accesso_id`, `emittente_fiscale_id` (e `is_default` finché Q26 del brief `ui` non lo ritira) | `descrizione`, `pagina_dimensione`, `ordinamento_default`, `filtri_default`, `attivo`, `contenuto_aggiornato_il` |

Le ragioni delle scelte non ovvie:

- `filtrabile`, `ordinabile`, `ricercabile_full` sono del software: dipendono dalla vista e dai suoi indici, e una
  ricerca accesa su un campo senza indice è un problema di prestazioni del software, non una preferenza;
- `sensibile` è del software: dice la natura del dato. La leva dell'installazione è `ui.lista_colonna_permesso`, che
  apre o chiude la colonna per profilo;
- `etichetta_i18n_key` è del software (la chiave della traduzione che il codice porta); `etichetta` è il testo, e
  l'installazione lo cambia;
- `contenuto_aggiornato_il` è dell'installazione: la sposta il trigger quando cambia il contenuto, e quando la sposta
  una scrittura dell'app la riga diventa personalizzata. È ciò che serve a QU2;
- `descrizione` della definizione è del software (il nome della lista nel catalogo), quella del preset
  dell'installazione (il nome che l'admin gli dà).

#### La composizione del preset (QU2)

`ui.lista_preset_colonna` non ha la colonna `id` (la chiave è `preset_id, colonna_id`), e il meccanismo identifica la
riga da `id`: così com'è non si iscrive. Senza regola, il mirror della composizione riscrive le righe di un preset che
l'installazione ha personalizzato.

- **(a)** La composizione segue il suo preset: un trigger sulla tabella figlia, nella sessione del migratore, non scrive
  né toglie le righe di un preset personalizzato (`dbops.fn_seed_riga` del preset); l'installazione la scrive
  liberamente, e la sua scrittura personalizza il preset attraverso `contenuto_aggiornato_il`. Una forma nuova del
  meccanismo («figlia»), dichiarata nel registro accanto a `RIGA`, `COLONNA` e `SOLO_INSERIMENTO`.
- **(b)** Una colonna `id` surrogata e la forma per riga: ogni riga della composizione si personalizza da sola, e il
  DELETE di una riga di seed è rifiutato. Il BE non può più riscrivere la composizione per intero.

**Raccomandata (a)**: la composizione è il contenuto del preset, non una riga con una vita sua, e la personalizzazione si
legge in un posto solo.

#### La cancellazione (QU3)

Una riga nata dal seed non si cancella (`E_SEED_RIGA_NON_CANCELLABILE`): si spegne. Oggi l'admin cancella definizioni,
colonne e preset, anche quelli del seed.

- **(a)** Vale la regola del meccanismo senza eccezioni: le righe di seed si spengono. Ricadute BE/FE: le tre
  cancellazioni rispondono `E_SEED_RIGA_NON_CANCELLABILE` sulle righe di seed; liste e dettagli espongono
  `nata_dal_seed` e `campi_del_software` come per la posta (R1-BE-bis, §16.14), e il FE spegne il cestino e i campi
  del software.
- **(b)** Un'eccezione per `ui`.

**Raccomandata (a)**. La superficie: due casi (posta e `ui`) fanno la seconda occorrenza, e le viste per tabella del
§16.14 diventano un building block che le genera o le sostituisce, deciso nel giro.

#### La sovrapposizione con Q14 del brief `ui` (QU4)

Una lista è «certificata» quando ha `multi_emittente = true`, che si accende solo dal seed. Con QU1, sulle righe di seed
`codice`, `schema_dati`, `vista_sql`, `multi_emittente` e `perimetro_emittente` sono del software, quindi l'app non li
cambia (`E_SEED_COLONNA_DEL_SOFTWARE`). È quasi la stessa regola di Q14 del brief `ui` («vista e schema dati di una lista
certificata solo dall'owner», codice immutabile, i due flag nel guard multi-emittente), ma Q14 vale anche sulle righe
create dall'app.

- **(a)** Q14 resta per ciò che il seed non copre: `codice` immutabile su ogni riga, `multi_emittente` e
  `perimetro_emittente` solo dal migratore su ogni riga. La regola «vista e schema dati di una lista certificata» si
  ritira, perché è il seed per colonna.
- **(b)** Q14 resta intera: sulle righe di seed i due guard rifiutano lo stesso UPDATE con due codici (scatta prima il
  seed, in fase a00).

**Raccomandata (a)**: due guard per la stessa regola sono la divergenza che la regola del 2 previene.

#### Fuori dal censimento

- `ui.misure_pagina`: l'app la legge soltanto;
- le cinque tabelle di catalogo delle dashboard: nessun servizio le scrive, e dal giro 5 del brief `ui` sono in sola
  lettura per l'app (Q19);
- `ui.lista_colonna_permesso`: non ha un CSV;
- le due preferenze: non hanno un CSV.

#### Le decisioni (Tid, 2026-11-20)

| # | Decisione |
| --- | --- |
| QU1 | ✅ La classificazione per colonna come proposta, per le tre tabelle |
| QU2 | ✅ (a): la composizione segue il suo preset, con la forma nuova «figlia» |
| QU3 | ✅ (a): le righe di seed si spengono, senza eccezioni; la superficie per il BE diventa un building block |
| QU4 | ✅ (a): di Q14 del brief `ui` restano `codice` immutabile e i due flag solo dal migratore, su ogni riga; «vista e schema dati di una lista certificata solo dall'owner» si ritira, perché la tiene il seed per colonna |

~~**Dopo le decisioni**, un giro di questo brief con i changeSet del range dato da Tid (`20261119-01` …): le righe del
registro, la forma «figlia» se QU2 è (a), la superficie per il BE, i pgTAP, e il provisioning dei runner su dbdev come al
`20261117-28`.~~ Superato dal giro 3 qui sotto: il provisioning non serve (la rete `20261117-20` è `runAlways` e monta
le tabelle nuove a ogni migrate), la superficie per il BE è un passo a parte.

#### QU5 — Come si riconoscono le righe di seed di `ui` (Tid, 2026-11-20)

Il runner iscrive alla nascita del trigger le righe con `user_insert = 'SEED'` o col nome di un ruolo del migratore. I
CSV di `ui` portavano `mctit`, che non è un ruolo: nessuna riga sarebbe stata iscritta, e il meccanismo non avrebbe
protetto niente, in silenzio. Il trigger d'audit riscrive `user_insert` all'INSERT (il ruolo che migra) ma non all'UPDATE,
quindi il ricarico del mirror scrive il valore del CSV. **Deciso:** `user_insert = SEED` nei CSV di
`lista_definizione`, `lista_colonna` e `lista_preset`, nello stesso rilascio dell'iscrizione. Il ricarico gira in
`80_data` prima della rete di `90_end`, che le iscrive. Costo accettato: su dbdev le modifiche fatte da admin alle righe
di seed di `ui` si riscrivono una volta (§11.7 chiede un rilascio prima; siamo in sviluppo).

#### Il giro 3: le tabelle di `ui` e la forma figlia (2026-11-20)

| ChangeSet / file | Che cosa |
| --- | --- |
| `20261119-01` (`00_schema/dbops`) | `tabella_padre` e `colonna_padre` nel registro, CHECK `chk_automazione_seed_primo_impianto_figlia` |
| `20261119-02` (`20_code/dbops`) | `fn_seed_primo_impianto_argomenti`: la forma `FIGLIA, <colonna>, <schema.tabella>`. Firma invariata: la legge anche `fn_seed_colonne_del_software` (`BEGIN ATOMIC`), che un cambio di `RETURNS TABLE` costringerebbe a ricreare con le due viste della posta. Colonna e padre il trigger li legge dagli argomenti già validati |
| `20261119-03` (`20_code/script`) | `trgfn_seed_primo_impianto`: il ramo FIGLIA |
| `20261119-04` (`20_code/dbops`) | `fn_seed_primo_impianto_divergenze`: argomenti FIGLIA, niente `SENZA_ID` per la figlia, `PADRE_NON_ISCRITTO` |
| `20261119-05` (`20_code/dbops`) | il runner: CREA su FIGLIA monta senza iscrizione; `PADRE_NON_ISCRITTO` è un salto con WARN |
| `80_data` | il loader `20261117-19` con le due colonne; righe 3-6 del CSV del registro; `user_insert = SEED` nei tre CSV di `ui` (QU5; il diff è solo quella cella) |
| pgTAP nuovi | `ui/test-seed-primo-impianto-ui-installazione-v1` (app, 18) e `ui/test-seed-primo-impianto-ui-software-v1` (owner, 16) |
| pgTAP adeguati | `ui/test-lista-definizione-multi-emittente-v1` (test 3), `ui/test-lista-definizione-perimetro-emittente-v1` (test 4), `script/test-fn-is-proprietario-tabella-v1` (test 6): provavano il guard multi-emittente su una lista del seed, dove ora rifiuta prima il seed. Passano a una lista creata dal test |

**Provato sullo scratch** (`scripts/prova_changeset.py`, i cinque changeSet più uno YAML di prova nello scratchpad che fa
ciò che fanno `80_data` e la rete: le righe del registro, `user_insert`, il runner). Estratto eseguito per intero,
catalogo identico dopo il ROLLBACK. Il test del software: 16 ok con l'estratto (senza, rosso e interrotto, come deve).
Quello dell'installazione gira come app e lo script corre da owner: da owner passano i quattro test strutturali
(montaggio, argomenti della figlia, divergenze di `ui` a zero, righe di seed riconosciute), e i sei rossi sono i casi che
il migratore può fare e l'app no. ✅ Applicato su dbdev e pgTAP verdi, i due nuovi come app e da owner e i tre
adeguati (Tid, 2026-11-20). ✅ La doc auto-generata delle cinque funzioni e del registro è rigenerata (2026-11-20).

**Un limite accettato, trovato rileggendo il giro.** Il trigger `z10` della composizione scatta anche sul DELETE. Quando
il software toglie una riga sotto un preset personalizzato (una colonna ritirata), la data del contenuto del preset la
sposta il migratore su una riga personalizzata: il seed la rimette da `OLD`, la scrive in `scartati` e alza un WARNING.
Effetto: la data non si sposta (il banner tace per quel ritiro, e la colonna ritirata il resolver la scarta comunque), e
in `scartati` resta una data che non viene dal CSV. Non rompe niente; se diventa rumore, la correzione sta nel trigger
`z10`, che dalla sessione del migratore non tocca un padre personalizzato.

**Restano aperti, e non stanno in questo giro:**

- ~~la **superficie per il BE** di QU3, in un passo a parte~~: fatta, vedi «La superficie» qui sotto;
- `is_default` sta fra le colonne del software di `ui.lista_preset`: il giro che lo ritira (Q26 del brief `ui`) lo
  toglie nello stesso changeSet anche dalla riga 5 del registro, altrimenti la tabella diventa `NON_CLASSIFICATA`;
- di Q14 del brief `ui` si ritira «vista e schema dati di una lista certificata solo dall'owner» (QU4): lo fa il giro 4
  di quel brief, che riapre il guard multi-emittente.

#### Ricadute BE/FE del giro 3 (passo 7-quater; il giro è applicato, ⏳ al team BE/FE)

Elenco chiuso. Dopo l'apply le righe di seed di `ui` si spengono e non si cancellano, e sulle righe di seed le colonne
del software non si cambiano.

| # | Che cosa | File |
| --- | --- | --- |
| R-UI1 | Le tre cancellazioni admin su una riga di seed rispondono `E_SEED_RIGA_NON_CANCELLABILE` (la riga si spegne). Il servizio mappa il codice; il gesto ordinario diventa lo spegnimento | `backend/apps/ui/db/ui_admin_repository.py` (`DELETE` su `lista_definizione` `:274`, `lista_colonna` `:518`, `lista_preset` `:687`) e i tre servizi `backend/apps/ui/services/lista_definizione_admin_service.py`, `lista_colonna_admin_service.py`, `lista_preset_admin_service.py` |
| R-UI2 | Gli UPDATE admin di una colonna del software su una riga di seed rispondono `E_SEED_COLONNA_DEL_SOFTWARE` (campo = la colonna): sulla definizione `codice`, `descrizione`, `schema_dati`, `vista_sql`; sulla colonna `codice`, `campo_sorgente`, `tipo_colonna`, `tipo_dato`, `formato`, `filtrabile`, `ordinabile`, `ricercabile_full`, `sensibile`, `etichetta_i18n_key`; sul preset `codice` e `is_default` | `backend/apps/ui/db/ui_admin_repository.py` (`_DEFINIZIONE_UPDATE_COLS`, `_COLONNA_UPDATE_COLS`, `_PRESET_UPDATE_COLS`) e i tre servizi |
| R-UI3 | `replace_preset_colonne` su un preset di seed lo personalizza (la data del contenuto si sposta): da lì il migrate non ne riscrive la composizione. Atteso, nessun cambio di codice; da sapere per i test BE che salvano un preset di sistema | `backend/apps/ui/db/ui_admin_repository.py:733` |
| R-UI-test | I test BE che cancellano o rinominano righe di seed di `ui` vanno su righe create dal test | `backend/apps/ui/tests/` |

| R-UI-sup | Liste e dettagli admin di definizioni, colonne e preset espongono `nata_dal_seed` e `campi_del_software`, letti da `dbops.fn_seed_superficie` (sotto) in `LEFT JOIN LATERAL`, con le colonne del software passate come sottoquery non correlata. Nessun elenco di colonne nel backend. Il FE spegne il cestino sulle righe nate dal seed e i campi in `campi_del_software`, col motivo (il testo lo sceglie il FE, come per la posta, R3 del §16.14) | `backend/apps/ui/db/ui_admin_repository.py` (le letture di lista e dettaglio delle tre tabelle); i drawer `ListaDefinizioneDrawer.vue`, `ListaColonnaDrawer.vue`, `ListaPresetDrawer.vue` e le loro tabelle |

La forma della lettura, per R-UI-sup (`<t>` è la tabella, `x` il suo alias):

```sql
LEFT JOIN LATERAL dbops.fn_seed_superficie(
    '<t>'::regclass, x.id::text,
    (SELECT dbops.fn_seed_colonne_del_software('<t>'::regclass))) seed ON true
```

**Esito del team BE/FE (2026-11-20).** Fatti, provati sul DB vero.

- **R-UI1, R-UI2**: nessun codice nel servizio. Il codice del guard arriva al client già tradotto
  dalla policy generata (409, con il campo acceso per `E_SEED_COLONNA_DEL_SOFTWARE`), attraverso i
  tre service admin; provato con una chiamata vera su una riga di seed di ciascuna tabella. Il
  presidio della giuntura è `backend/apps/ui/tests/db/test_seed_primo_impianto_ui_db.py`.
- **R-UI-sup**: le letture di lista e dettaglio delle tre tabelle (`ui_admin_repository.py`)
  portano `nata_dal_seed` e `campi_del_software` nella forma qui sopra (un helper del modulo,
  `_sql_superficie_seed`). Il FE spegne i campi in `campi_del_software` col motivo e li toglie dal
  PATCH (BB `campoDelSoftware` + `senzaCampiFermi`) nei tre drawer, e spegne il cestino sulle righe
  `nata_dal_seed` nei tre pannelli.
- **R-UI3**: nessun cambio, come atteso.
- **R-UI-test**: nessun test BE cancellava o rinominava righe di seed di `ui` (toccano `attivo` e
  `ricerca_min_caratteri`, colonne dell'installazione).
- ⚠️ **Domanda al team DB, nata qui**: la lista admin dei preset (`ui.lista_definizione`
  `ui.lista_preset`, id 58) ha ancora la colonna di catalogo `is_default` (`lista_colonna.csv`, riga
  id 665, accesa). Dal giro 1a di brief-db-revisione-ui il campo non esiste più: la colonna esce
  vuota. Va spenta o tolta dal CSV nel giro che lo ritira (il BE non la consegna più).

#### La superficie: `dbops.fn_seed_superficie` (QU3, 2026-11-20)

La regola delle superfici (nata dal seed; i campi del software solo sulle righe di seed; vuoto e mai NULL) era scritta in
ciascuna delle due viste della posta, e le liste admin di `ui` ne chiedevano altre tre. È la seconda occorrenza: un
building block, e le due viste si riscrivono sopra nello stesso giro.

| ChangeSet | Che cosa |
| --- | --- |
| `20261119-06` (`20_code/dbops`) | `dbops.fn_seed_superficie(p_tabella, p_riga_id, p_colonne_del_software)`: una riga, `nata_dal_seed` e `campi_del_software`. Compone `fn_seed_riga` e l'elenco ricevuto; non legge il montaggio |
| `20261119-07`, `-08` (`20_code/config`) | `config.vw_email_account_seed` e `config.vw_email_template_seed` sopra il building block: colonne, nomi e tipi identici (`CREATE OR REPLACE VIEW`), il BE della posta non cambia |

**Perché le colonne le passa il chiamante.** Non dipendono dalla riga (linee-guida-sql §13.2): una funzione che le
rilegge per riga rifarebbe la stessa lettura del montaggio per ogni riga della lista. Lettura e giudizio in due metà: il
chiamante legge una volta con `fn_seed_colonne_del_software` (InitPlan), la funzione giudica la riga. Le viste della posta
le leggevano già una volta, e così restano.

**Nessuna vista nuova per `ui`**: il BE chiama il building block nelle sue letture. Una vista per tabella sarebbe stata
la terza, la quarta e la quinta copia dello stesso adattatore.

**Provato sullo scratch** (`prova_changeset.py`, i tre changeSet). `test-posta-solo-disattivazione-v1`, che legge le due
viste, identico prima e dopo. `dbops/test-fn-seed-superficie-v1` (nuovo, 7 test, app): 6 ok da owner; il test 2 (una
lista creata dal test non è nata dal seed) da owner è rosso per costruzione, perché nella sessione del migratore la lista
nasce di seed. ✅ Applicato su dbdev, pgTAP verdi come app (Tid, 2026-11-20). ✅ La doc auto-generata è rigenerata
(2026-11-20).

### 16.16 Il rilancio scrive l'account da cui la mail riparte (richiesta del BE, decisione di Tid, 2026-11-20)

**La richiesta del BE (2026-11-20).** Dal giro 2 un account che ha spedito si spegne (Q24). `send_pending_emails`
riprende le mail in coda (`config.vw_email_in_coda`) con l'account scritto sul log, senza guardare `attivo`: una mail in
`RETRY`, o un `FAILED` ancora ripescabile, riparte da un account spento. La regola è quella di R1-BE-ter: il log dice
da dove la mail è partita. Quindi il rilancio risolve di nuovo l'account e il log lo segue. Sulle righe non di sistema
il backend lo scrive con l'`UPDATE` diretto. Sulle righe `SISTEMA` l'esito passa da `config.fn_chiudi_email_sistema`,
che scriveva solo stato, errore, `inviato_at` e tentativi.

**La decisione di Tid (2026-11-20):** il rilancio batch deve poter scrivere sul log l'account con cui la mail riparte.
Cambia per primo il DB.

#### La verifica sulle righe non di sistema

La domanda del BE: il processo del batch può aggiornare `email_account_id` sulle righe `REPARTO` e `OPERATORE`? **Sì**,
e non serve niente dal DB. Letto dal catalogo di dbdev il 2026-11-20, cioè dalla struttura:

* **grant:** `zeroerp_app` ha `UPDATE` sulla tabella e sulla colonna;
* **policy:** `rls_email_log_ambito` (`USING` e `WITH CHECK` uguali) non legge `email_account_id`. Il processo
  `send_pending_emails` (`script.fn_scope_identita_processo`) vede le righe `REPARTO` e `OPERATORE` delle aziende del suo
  perimetro, e le stesse righe passano il `WITH CHECK` dopo che l'account è cambiato;
* **trigger:** nessuno guarda la colonna. I due `require` attivo scattano su `UPDATE OF unita_organizzativa_id` e
  `UPDATE OF emittente_fiscale_id`, e la guardia dello scope emittente non cambia esito perché l'azienda resta quella.
  Il `require` verso l'account non c'è più dal giro 2: la FK è un'eccezione ATTIVO (§16.14).

#### Il changeSet `20261118-01` (numero dato da Tid)

`config.fn_chiudi_email_sistema` riceve un parametro in coda, `p_email_account_id`, `DEFAULT NULL`: `NULL` lascia la
colonna com'è, con lo stesso `COALESCE` di `inviato_at`. Le chiamate di oggi (backend a quattro argomenti, pgTAP a due o
quattro) non cambiano comportamento (linee-guida-sql §5f). La firma cambia, quindi DROP della firma vecchia e CREATE,
con gli attributi vivi ripetuti e l'`EXECUTE` all'applicazione ridato. Testata ri-ancorata con `%TYPE`, COMMENT
riscritto al presente. Il corpo viene dalla doc auto-generata, identica al vivo.

* ⛔ **Nessun controllo che l'account sia acceso.** L'account può spegnersi fra l'invio e la scrittura dell'esito, e la
  mail spedita è storia: per questo la FK del log è un'eccezione ATTIVO. La scelta di un account acceso è di
  `config.fn_resolve_email_account`: ripeterla nella porta di chiusura ne farebbe una seconda sede.
* ⛔ **Nessuna guardia propria sull'id inesistente.** Lo ferma la FK `fk_email_log_email_account` (`23503`), come in
  `config.fn_accoda_email_sistema`, che l'account lo riceve allo stesso modo. Un codice proprio avrebbe senso solo se
  lo avesse anche l'accodamento.
* L'account si scrive con ogni esito, non solo con `SENT`: anche un `RETRY` o un `FAILED` è un tentativo partito da
  quell'account.

**Provato** con `scripts/prova_changeset.py` sullo scratch (2026-11-20). L'estratto gira per intero, catalogo identico
dopo il `ROLLBACK`. `config/test-fn-email-sistema` (plan da 12 a 18) passa 18 su 18 con l'estratto. Senza l'estratto
passa 14 su 18: i 4 rossi sono i casi nuovi (12, 12-bis, 13-bis, 14). Gli attributi (`SECURITY DEFINER`, volatilità,
`PARALLEL`, `COST`, `search_path`, proprietario, privilegi) restano quelli del vivo: i privilegi sono le stesse tre voci,
in un altro ordine. Il presidio dei COMMENT e quello delle forme sono verdi sul file. I test nuovi:

* 11: una sola firma per nome;
* 12 e 12-bis: una mail di sistema accodata su un account **spento**, che il test costruisce, chiusa in `RETRY` con
  un account acceso. Il log porta quello acceso;
* 13 e 13-bis: la chiamata a quattro argomenti chiude ancora, e l'account resta com'era;
* 14: un account inesistente lo ferma la FK.

**Applicato** su dbdev da Tid il 2026-11-20, col pgTAP `config/test-fn-email-sistema` verde; resta una sola firma, a
cinque argomenti.

**Documentazione:** la pagina `manual/` di `config.email_log` (§«Ciclo di vita»: l'account segue l'invio) e la doc
auto-generata della funzione, rigenerata dopo l'apply.

#### La richiesta al team BE/FE (dopo l'apply del `20261118-01`)

**Chi cambia per primo:** il DB, con questo changeSet. Il backend parte dopo l'apply e, nell'attesa, non introduce
rimedi provvisori.

| # | Che cosa | File |
| --- | --- | --- |
| R5 | Il rilancio risolve l'account sul reparto del log quando quello scritto è spento (`config.fn_resolve_email_account`), spedisce con quello e scrive il nuovo id insieme all'esito: sulle righe `SISTEMA` come quinto argomento di `config.fn_chiudi_email_sistema` (`p_email_account_id`, `NULL` = lascia com'è), sulle altre nell'`UPDATE` diretto (la colonna entra nella whitelist delle colonne aggiornabili) | `backend/apps/core/management/commands/send_pending_emails.py`; `backend/apps/core/db/email_repository.py` (`update_log_stato`); `backend/apps/core/services/email_service.py` se passa da lì |
| R5-doc | La guida dice «per ogni email il command usa l'account SMTP originale (quello con cui l'email era stata preparata)»: dopo R5 non è più vero | `docs/it/guide/gestione-mail.md` §Coda email e retry |
| R5-test | Una mail di sistema e una di reparto accodate su un account spento: dopo il rilancio il log porta l'account risolto | `backend/apps/core/tests/db/test_email_porta_di_sistema.py`, `backend/apps/core/tests/services/` accanto ai test di `send_pending_emails` |

**Esito del BE (2026-11-20).** ✅ R5, R5-doc e R5-test fatti; da committare.

* `EmailRepository.update_log_stato` riceve `email_account_id` (`None` = lascia com'è): sulle righe `SISTEMA` è il
  quinto argomento di `config.fn_chiudi_email_sistema`, sulle altre un `COALESCE` nell'`UPDATE` diretto.
* `EmailDispatchService` lo passa con **ogni** esito (`SENT`, `FAILED`, `SIMULATA`, non configurato), anche alla
  prima spedizione, dove coincide con l'account scritto all'INSERT.
* `send_pending_emails` legge il log prima di scegliere l'account (`_account_del_rilancio`): quello del log se è
  acceso (`get_account_with_password` porta `attivo`), altrimenti `config.fn_resolve_email_account` sul reparto del
  log. ⚠️ Corretto nello stesso giro: il ripiego senza account sul log chiamava il risolutore **senza** il reparto.
* Non è servita un'altra richiesta al DB: il reparto lo porta già `EmailRepository.get_log`.
* `send_raw` non riceve più `email_account_id` a parte: il log prende `account["id"]`, l'account che spedisce.
  Prima lo stesso dato arrivava da due fonti, che un chiamante poteva far divergere (ok Tid, 2026-11-20).
* **Lettori censiti** di `email_log.email_account_id` (regola «Una garanzia ritirata si censisce in tutti i
  lettori», `.codex/AGENTS.md`): il rilancio (adeguato); la conferma della bozza (R1-BE-ter, già adeguata); il
  dettaglio e la lista del registro (`get_log`, `list_logs`) mostrano codice e mittente dell'account, e non dipendono
  dal fatto che sia acceso. Il test di connessione legge un account scelto dall'amministratore, non dal log.
* Test: `test_email_porta_di_sistema` 3 e 4 (DB vero, contesto del processo, sulle due porte) e
  `test_email_service` 26 e 27 (ogni esito del rilancio, e il log del primo invio, portano l'account). Guida `gestione-mail.md` §Coda email e retry.
