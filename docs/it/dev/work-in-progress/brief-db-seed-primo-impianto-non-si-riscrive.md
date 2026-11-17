# Brief DB — Il seed di primo impianto: la riga modificata dall'installazione non si riscrive

## ⏭️ Chi riparte — aggiornato al 2026-11-17 (brief scritto, analisi critica fatta, niente costruito)

**Riparte: Tid**, che rilegge il modello (§3), il meccanismo (§4, §5) **corretto dall'analisi critica (§12)** e
prende le decisioni Q1-Q11 (§9). Finché non dà il via non si scrive niente.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Il problema, la storia delle decisioni e il meccanismo proposto | §1-§7 | — |
| 1-bis | ✅ sessione DB | Analisi critica: V1 fatta (smentisce `RETURN NULL`), `DELETE_BLOCK` per tabella non basta, marcatore e diagnosi da rifare | §12 | 1 |
| 2 | Tid | Rilettura a mente lucida e decisioni Q1-Q11 | §9, §12 | 1-bis |
| 3 | sessione DB | Le verifiche V2-V5, prima di scrivere | §8 | 2 |
| 4 | sessione DB | Giro 1: la colonna marcatore, la regola d'automazione, il trigger, il blocco del `DELETE`, i pgTAP, §11.7 delle linee guida | §10 | 3 |
| 5 | Tid | `/verifica-db`, l'apply, i pgTAP, la doc auto-generata, il commit | — | 4 |
| 6 | team BE/FE | Le ricadute R1-R3 | §11 | 5 |
| 7 | chi chiude | Archiviazione in `work-done/`, con il rimando tolto dal registro dei residui | — | 5, 6 |

**Decisioni aperte di Tid:** Q1-Q11 (§9). **Da committare:** questo brief e il rimando nel registro dei residui.

**Brief vicini verificati (2026-11-17):** in `work-in-progress/` nessun brief tratta i mirror che
riscrivono un dato modificato da interfaccia. Le menzioni di `loadUpdateData` in
`brief-db-revisione-documenti`, `brief-db-provenienza-prezzo-segue-il-prezzo` e
`brief-incassi-riconciliazione-rate-promemoria` riguardano i loro CSV, non il meccanismo. Il registro
dei residui ha il caso di `famiglie_documento` (§7), e da lì rimanda a questo brief.

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
> scritto a mano»), e qualunque scrittura dell'app marcherebbe la riga, anche il test SMTP.

La proposta: una colonna per tabella dichiarata, per esempio `personalizzata_il timestamptz` (`NULL` = come il
seed l'ha lasciata), accesa dal trigger e mai dal CSV. Il CSV non la porta, quindi il mirror non la tocca. Il
nome è da decidere (Q2).

### 4.3 Chi è l'«app» e chi è il «migrate»

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
| `config.email_account` | **entra** | A parte `codice`/`codice_interno` (`SISTEMA`, che il codice cerca e che non cambia), la riga è tutta configurazione dell'installazione: host, porta, TLS/SSL, credenziali, mittente, risposta |
| `config.email_template` | **da valutare** (Q5) | I testi delle mail sono contenuto che l'installazione adatta. Va letto se il codice legge colonne del template come regole (segnaposto, codice) |
| `vendite.famiglie_documento` | **da valutare** (Q5) | L'operatore cambia il `codice` dal CRUD, ma la riga porta regole del software (formato, colonna serie, regole fiscali, anno nel numero) che il CSV deve poter cambiare. Il blocco per riga fermerebbe anche quelle: qui serve probabilmente un'altra forma, per esempio il `codice` fuori dal mirror con `type: SKIP` |

Il censimento completo (ogni mirror `runOnChange` su una tabella che l'app può scrivere) si fa nel giro 1,
leggendo la **struttura**: GRANT di `zeroerp_app`, `config.tabelle_gestibili.pannello`, endpoint che
scrivono. Ogni tabella trovata riceve una specie dichiarata.

## 8. Verifiche prima di scrivere

| # | Che cosa | Perché |
| --- | --- | --- |
| V1 | ✅ **Fatta il 2026-11-17 (§12.1).** Che SQL genera `loadUpdateData` su PostgreSQL | `UPDATE` e poi `IF not found THEN INSERT`, in un blocco `DO` (letto in `InsertOrUpdateGeneratorPostgres` di `tools/liquibase/5.0.4`). ⛔ L'ipotesi «in entrambi i casi `RETURN NULL` salta la riga» è **smentita**: va provato su una tabella di prova in `ROLLBACK` che `RETURN OLD` non produca l'`INSERT` |
| V2 | Che il trigger di audit e quello nuovo non si disturbino | ⚠️ Corretta da §12.1: con `RETURN OLD` l'ordine dei trigger `BEFORE` (alfabetico) **conta**. Il trigger nuovo scatta dopo l'audit, così ne butta via le modifiche. Si guardano anche i trigger `AFTER UPDATE` (storico), che vedrebbero un aggiornamento senza cambiamenti |
| V3 | Chi scrive oggi queste tabelle senza `app.jwt_user`: job, funzioni di dominio, provisioning | Verrebbero trattati come il migrate (§4.3) |
| V4 | ⚠️ Esito anticipato da §12.2: `DELETE_BLOCK` **non** copre il caso così com'è | Blocca ogni riga della tabella. Resta da verificare il bypass del `DELETE` forward-only di §11.2 sulla forma per riga |
| V5 | Se Liquibase mostra i `NOTICE` di PostgreSQL nell'output del migrate (§12.5) | Se non li mostra, Q3 decade e il segnale è solo la diagnosi |

## 9. Decisioni aperte di Tid

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
| Q10 | Quale scrittura dell'app marca la riga: ogni `UPDATE`, o solo quello che cambia colonne di configurazione? (§12.7) | Solo `NEW IS DISTINCT FROM OLD` sulle colonne di configurazione; `meta` e le colonne d'audit fuori |
| Q11 | Su `email_account` serve «aggiorna finché è intatta», o basta «inserisci se manca»? (§12.11) | La specie si argomenta su `email_template`; per `email_account` decide Tid |

## 10. Il giro 1 (dopo il via)

1. V2-V5 (§8), con gli esiti scritti qui (V1 fatta: §12.1).
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
