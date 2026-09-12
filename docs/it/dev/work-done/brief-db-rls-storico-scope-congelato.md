# Brief DB — Lo storico porta il proprio perimetro (e `audit_log` è un'altra domanda)

> Stato: ✅ **storico: APPLICATO l'11-09-2026 alle 19:54 (passi 1-7, §4b-§4d), pgTAP senza regressioni** — 37 shadow armate, 65.751 versioni attribuite. ✅ **§8 (`audit_log`): consegnato
> e applicato il 2026-09-11** (`-09`, `-20` in `databasechangelog` alle 12:42; postura
> viva verificata a catalogo). Il §8.4 originale sbagliava due volte: vedi §8.4.
> ✅ **§8.3 deciso: «No», registro tecnico** — cancello costruito (§8.6) e **applicato**. ✅ Tutte le domande aperte di §4d sono decise, costruite e **applicate**: `20260911-32/-33/-34`, `20260912-01…07` sono `EXECUTED` nel `databasechangelog` (ultimo giro **2026-09-12 00:30**, letto il 12-09). Doc scritta (§9). ✅ **pgTAP post-apply tutti verdi** (Tid, 12-09). ✅ **Consegna BE chiusa il 12-09** — e non come dicevano §4d e §9.3 (ripuntare alla shadow legacy): la timeline legge `storico.identita_digitali`, dove l'identità vive, e il label del bridge morto è ritirato. ⭐ **Decisione di Tid (12-09): la storia vecchia del bridge è sporcizia di test** — senza produzione non rappresenta niente — quindi la shadow `_legacy_` non si legge e si **droppa** (📮 team DB, §9.3). **Chiuso e spostato in `work-done/` il 2026-09-12.** ⏳ **Coda §10** (12-09 pomeriggio, decisione Tid: via anche la **madre** legacy): `20260912-08/-09/-10` **applicati alle 11:30, pgTAP senza regressioni** (Tid, 12-09). Finito.
> Origine: **D3** di
> [migliorie-generali-da-test-valutazione.md](migliorie-generali-da-test-valutazione.md).
> Eredita il §9 di
> [brief-db-perimetro-emittente-righe-documento.md](../work-done/brief-db-perimetro-emittente-righe-documento.md),
> **che su questo punto sbagliava due volte** — vedi §6.
>
> Stima: **≈ 3 giornate** per lo `storico`, metà delle quali disegno e presidio.
> ⚠️ **`dbops.audit_log` è dentro il perimetro di questo brief** (§8, richiesta di
> Tid) ma **non è una tabella di storico**: stessa famiglia di difetto, rimedio
> diverso — e la struttura dice che la domanda giusta non è «quale policy», ma
> *«questo registro deve poter contenere dati di dominio?»*.
> ⛔ **Il lavoro è UNO, non 120**: la forma delle tabelle di storico è uniforme e
> generata da `dbops.fn_ensure_storico_table`. Chi legge «120 tabelle» e stima di
> conseguenza sta stimando il problema sbagliato.

---

## 1. Il difetto, detto sul modello

> **Lo storico di una riga protetta è la stessa informazione della riga.**

`vendite.fatture` è protetta da due policy. Ogni sua **versione precedente** non
lo è. La storicizzazione è automatica e cattura lo snapshot **completo** della
riga: chi non può vedere una fattura può leggerne tutte le revisioni.

⇒ Il perimetro non è una proprietà del *dato corrente*: è una proprietà del
**fatto**. Se vale per la riga, vale per la sua storia.

⚠️ **E lo `storico` non entra nel criterio del presidio del perimetro**
(`dbops.vw_rls_perimetro_scoperto`): quelle tabelle sono **gemelle** delle madri,
non figlie — nessuna FK le lega, e il criterio guarda le FK. Non è una svista del
presidio: è che questo è un meccanismo **diverso**, e vuole una difesa sua.

---

## 2. La decisione portante: si CATTURA, non si deriva

> **Ogni tabella di storico porta il proprio scope in una colonna, valorizzata
> alla scrittura e mai più ricalcolata. La policy legge quella colonna.**

Tre ragioni, tutte sul **modello**. ⛔ Nessuna delle tre poggia su un conteggio di
righe: valgono su un database vuoto come su uno pieno.

### 2.1 Una riga di storico è un fatto DATATO, e il perimetro fa parte del fatto

Registra com'era una riga in un istante. La sua verità è quella di **allora**.

⇒ Se il perimetro si ricalcolasse a runtime risalendo alla madre **viva**, il
presente riscriverebbe la visibilità del passato: un documento che cambiasse
emittente cambierebbe **chi può leggere la propria storia**.
⭐ *Un archivio che cambia quando cambia il presente non è un archivio.*

### 2.2 Il modello AMMETTE la riga senza madre — per progetto, non per incidente

`dbops.fn_ensure_storico_table` **non genera la foreign key**, e lo dichiara nel
proprio codice:

> *«non si genera più la fk perché bloccerebbe la cancellazione delle righe della
> tabella e non è corretto»*

⇒ Una policy che risale alla madre ha un ramo **non determinabile per
contratto**. ⛔ E va gestito **anche se oggi quel ramo fosse vuoto**: zero
occorrenze non significa che il caso non esiste, significa che non c'è ancora un
controesempio.

### 2.3 Il dato è disponibile ESATTAMENTE quando serve

`script.trgfn_storico_generic` è montato `BEFORE UPDATE OR DELETE` e serializza
`to_jsonb(NEW)` / `to_jsonb(OLD)`: **quando scrive ha in mano la riga intera, e
la madre esiste ancora.**

⇒ Il perimetro è **catturabile** nel momento in cui è certo. Non c'è nessun
bisogno di ricostruirlo dopo, quando può non esserci più.

---

## 3. Perché una COLONNA e non lo snapshot JSONB

Lo snapshot contiene già i valori della riga, quindi la tentazione è leggere di
lì (`snapshot ->> 'emittente_soggetto_ruolo_id'`). ⛔ È la scelta peggiore delle
due, per tre ragioni **di progetto**:

| | |
| --- | --- |
| **Contratto contro serializzazione** | lo snapshot è *come* la riga è stata salvata, non *che cosa* la riga promette. Se cambia forma — una colonna rinominata, uno snapshot ridotto — la policy **si rompe in silenzio**, e il sintomo di una policy rotta è *vedere di più* |
| **Costo per riga** | una policy è valutata **per ogni riga letta**. Un `->>` con cast non usa indici: è un costo strutturale, non un dettaglio di tuning |
| **Il caso del satellite** | una riga di `fatture_righe` non ha l'emittente **nemmeno nello snapshot**, perché non ce l'ha la riga. Con la colonna il trigger risale una volta sola e congela; con il JSON non c'è niente da leggere |

---

## 4. La forma, in concreto

### 4.1 La colonna

Il generatore aggiunge a ogni tabella di storico **una** colonna di scope,
valorizzata dal trigger. ⚠️ Il nome e il tipo si decidono in fase di disegno, e
la domanda vera è **quante colonne servono**: gli assi di perimetro in uso oggi
sono l'**emittente** (per soggetto-ruolo o per emittente fiscale) e il **billing
account**. ⛔ Decidere «una colonna generica» o «una per asse» è la prima cosa da
fissare: cambiarla dopo significa rigenerare 120 tabelle.

### 4.2 La mappa: dove sta lo scope, per ogni madre

⚠️ `trgfn_storico_generic` è **generico** — non sa quale sia la colonna di scope
della madre che sta specchiando. ⇒ Serve una **mappa dichiarata**, nello stile di
`dbops.fk_index_policy`: per ogni tabella, *dove* si prende lo scope.

| Caso | Come si ricava |
| --- | --- |
| la madre porta la colonna (`vendite.fatture`, `vendite.commesse`) | **copia diretta** dalla riga che il trigger ha già in mano |
| la madre è un satellite (`vendite.fatture_righe`) | **risalita una volta sola**, alla scrittura, e si congela il risultato |
| la madre non è in RLS | **nessuno scope**: la tabella di storico non si arma, e la riga di mappa lo **dichiara** |

⭐ La mappa è anche il registro del debito: una tabella di storico senza riga di
mappa è una tabella che nessuno ha ancora guardato, e il presidio la deve vedere.

### 4.3 La policy

Una sola forma, generata: veste `OPERATORE`, `FOR SELECT`, sulla colonna di
scope. ⚠️ **`FOR SELECT` e non `FOR ALL`**: lo storico lo scrive il trigger, non
l'applicazione — e una `WITH CHECK` su una scrittura di sistema non difende
niente e può bloccare la storicizzazione.

---

## 4b. Passo 1 — il disegno, letto sulla struttura (2026-09-11)

> ✅ **Disegno DECISO il 2026-09-11** (D1-D4 in §4b.4, una domanda alla volta). ⛔ Nessun argomento qui sotto
> poggia su un conteggio di righe: dove compare un numero è un fatto di
> **catalogo** (tabelle, policy, colonne), datato, e non è la ragione.

### 4b.1 Che cosa il censimento ha smentito del §4

| Il §4 diceva | La struttura dice |
| --- | --- |
| «gli assi in uso sono l'emittente e il billing account» | Per la veste **OPERATORE** l'asse è **uno**: l'emittente. Le 130 policy si risolvono in 42 `fn_scope_*`, e tutte quelle a `app.current_user_id` finiscono nella canonica `fn_check_user_emittente_scope(auth_user_id, emittente_fiscale_id)`. Gli altri assi (`ba_ownership`, `cliente_ownership`, `shop`, `fornitore_ownership`) appartengono a vesti portale/shop, **che non leggono lo storico** |
| «la madre porta la colonna, oppure è un satellite» | Sono **quattro modi** di arrivare allo **stesso** fatto: colonna `emittente_fiscale_id` (EF); colonna `emittente_soggetto_ruolo_id` (SR, 1:1 con EF via `emittenti_fiscali.soggetto_ruolo_id`); **risalita** al padre, anche a più salti (`resi_righe_accrediti → resi_righe → resi`); e **via billing account** (`billing_account`, `clienti`, `attivita_consumi`): un BA ha **esattamente un** emittente (`UNIQUE (billing_account_id)` su `emittenti_fiscali_billing_account`, ripiego sul gestore globale), risolto da `script.fn_get_ba_emittente_sr_id`. ⚠️ Prima stesura sbagliata (2026-09-11): avevo letto «specifico-o-default» come una mappatura libera. Corretto da Tid: il legame è **bloccato** appena il BA ha una fattura, una commessa o un documento numerato (`trgfn_efba_guard_storia_emittente`) — è un fatto, con una **finestra di correzione** finché il BA non ha storia |
| «la storicizzazione è automatica» | È automatica **solo per le madri registrate** in `config.storico_set_storicizza`; le altre storicizzano *a richiesta* (il trigger spegne `storicizza` dopo una modifica). Fra le 37 madri in RLS con trigger, sei sono a richiesta (`fatture_righe`, `fatture_atti`, `fatture_indirizzi`, `fatture_riepiloghi_iva`, `fatturazione_lotti_esiti`, `sospensioni`). Non cambia il disegno dello scope; cambia cosa c'è da proteggere |
| «120 tabelle» | 121 madri col trigger, 121 shadow, **37** madri in RLS. Le altre 84 shadow specchiano madri **senza** RLS: la mappa le dichiara `NESSUNO`, e la policy non si arma |

### 4b.2 🔴 Due fatti del meccanismo che il disegno deve assorbire

1. **Cinque shadow sono condivise fra due schemi.** Il generatore battezza la shadow col **nome nudo** della madre: `acquisti.ddt` e `vendite.ddt` scrivono entrambe in `storico.ddt`, con la stessa colonna `ddt_id` e **nessun discriminatore di schema** (idem `ddt_righe`, `ordini`, `ordini_righe`, `ordini_righe_fulfillment`). Due `BIGSERIAL` indipendenti nella stessa colonna: il modello **ammette** che lo stesso `ddt_id` indichi due documenti diversi, e allora il trigger che chiude «lo snapshot aperto `WHERE ddt_id = $2`» chiude quello **dell'altro schema**. Per lo scope pesa due volte: nella stessa shadow una riga di `vendite` ha un emittente e una di `acquisti` no. ⇒ **La shadow deve sapere da quale schema viene la riga.**
2. **Il trigger fa `UPDATE` sulla shadow** (chiude `valid_to`), e gira come chi scrive la madre — cioè `zeroerp_app`. ⇒ Sullo `storico.*` l'app ha bisogno di `SELECT, INSERT, UPDATE`, **mai `DELETE`**. Corregge la nota lasciata in §8.4: la postura per schema da dichiarare nel loop `20260205-41` è «senza DELETE», non «append-only». ⚠️ E vale anche per `fn_grant_storico_shadows`, che oggi allinea la shadow **ai privilegi della madre** — DELETE compreso.

### 4b.3 Il disegno proposto

**D1 — Una colonna sola: `scope_emittente_fiscale_id bigint`**, nullable, indicizzata.
⭐ Per la veste OPERATORE l'asse è uno, e i quattro modi della mappa (EF, SR, PADRE, BA)
sono quattro **strade** verso lo stesso fatto, non quattro fatti: si risolvono alla
scrittura e si congela un valore solo, nella rappresentazione della canonica (EF).
⚠️ **La prima stesura proponeva due colonne** (EF + billing account) perché avevo letto
il legame BA→emittente come configurazione mutabile; Tid ha corretto: il BA ha un
emittente solo ed è bloccato appena ha storia. Resta un caso da decidere, la
**finestra di correzione**: un BA *senza* documenti può ancora cambiare emittente
(«un cliente può nascere sbagliato»). Le righe di storico scritte in quella finestra
— le versioni del BA, del cliente, i consumi — portano l'emittente **di allora**, cioè
quello sbagliato. Due letture possibili: (a) è la verità di allora, e resta (§2.1);
(b) il cambio è una **correzione**, e la funzione che sposta il BA ri-attribuisce anche
lo storico di quel BA — un `UPDATE` dello scope sulle shadow coinvolte, dentro la stessa
unità atomica. ⭐ Proposta: **(b)** — una correzione che non corregge l'archivio lascia
la storia di un cliente visibile a chi non c'entra, per sempre; ed è bounded per
costruzione, perché oltre la finestra il cambio è respinto.

**D2 — Un discriminatore di origine su ogni shadow**: `origine_schema text NOT NULL`, scritto dal trigger (`TG_TABLE_SCHEMA`), e la chiusura dello snapshot diventa `WHERE <fk> = $2 AND origine_schema = $3`. Uniforme su tutte le 121, nella **stessa** rigenerazione che aggiunge lo scope — decidere dopo costerebbe una seconda passata su 121 tabelle. ⚠️ L'alternativa «rinominare le cinque shadow in `acquisti_ddt`» rende irregolare il generatore e rompe i lettori del nome nudo.

**D3 — La mappa: `dbops.storico_scope_policy`**, nello stile di `fk_index_policy` e di `rls_perimetro_debito`, seed CSV in `80_data`:

| Colonna | Che cosa dice |
| --- | --- |
| `schema_tabella`, `nome_tabella` | la madre (chiave con lo schema: le cinque condivise hanno **due righe**) |
| `modo` | `EF` · `SR` · `PADRE` · `BA` · `NESSUNO` (CHECK) |
| `colonna` | per `EF`/`SR`/`BA`: la colonna della riga; per `PADRE`: la **FK** verso il padre |
| `padre_schema`, `padre_tabella` | per `PADRE`: dove continuare — la risoluzione è **ricorsiva** sulla mappa stessa |
| `ragione` | obbligatoria e lunga per `NESSUNO` (come `rls_perimetro_debito`): «la madre non è in RLS», «asse portale, lo storico non lo legge» |

Una funzione `dbops.fn_storico_risolvi_scope(schema, tabella, riga jsonb) → (ef_id, ba_id)` la legge alla scrittura; il trigger la chiama **una volta**, quando la madre esiste ancora (§2.3). ⭐ La mappa è anche il **presidio**: una madre col trigger e in RLS senza riga di mappa è un rosso; una riga `PADRE` il cui padre non ha riga è un rosso; una riga il cui `modo` contraddice il catalogo (dice `EF` ma la colonna non c'è) è un rosso.

**D4 — La policy, generata**: veste `OPERATORE`, `FOR SELECT`, una sola forma:
`script.fn_scope_ef_whitelist(uid, scope_emittente_fiscale_id)` — è lo stesso adapter
delle madri con colonna EF, quindi nessuna logica nuova. Con la colonna `NULL` la riga
**non si vede** (fail-closed), che è il verso giusto per una shadow armata. Si arma solo dove la mappa non dice `NESSUNO`. ⚠️ Sulle cinque shadow condivise: la riga di `acquisti` avrà scope `NULL` e sparirà agli operatori finché `acquisti` non entra in RLS con un asse suo — è la conseguenza onesta di D2, e va scritta nella riga di mappa.

### 4b.4 Che cosa resta di Tid

| | Decisione | Proposta |
| --- | --- | --- |
| D1 | la colonna è una (EF); resta la **finestra di correzione** del BA | ✅ **Deciso (Tid, 2026-09-11): (b)** — chi sposta il BA ri-attribuisce anche lo storico di quel BA, nella stessa unità atomica |
| D2 | discriminatore di schema sulle shadow | ✅ **Deciso (Tid, 2026-09-11): (a)** — `origine_schema` su ogni shadow, scritto dal trigger, chiusura dello snapshot per schema; nella stessa rigenerazione dello scope |
| D3 | forma della mappa | ✅ **Deciso (Tid, 2026-09-11): (a)** — `dbops.storico_scope_policy` + CSV, ricorsiva su `PADRE`, `ragione` obbligatoria su `NESSUNO`; la mappa è anche il presidio |
| D4 | quale veste legge lo storico | ✅ **Deciso (Tid, 2026-09-11): (a) solo `OPERATORE`** — una policy, una forma; portale e shop non vedono righe di storico, l'amministrazione passa dal bypass `SUPER_ADMIN` della canonica |

---

## 4c. Passo 2 — la mappa e chi la legge (consegnato l'11-09-2026)

| Cosa | Dove |
| --- | --- |
| Tabella `dbops.storico_scope_policy` — chiave (schema, tabella), `modo` `EF/SR/PADRE/BA/NESSUNO`, `colonna`, padre, `ragione` obbligatoria ≥ 40 su `NESSUNO`, **FK differita su se stessa** (un PADRE dichiarato deve avere la sua riga) | `00_schema/dbops/20260911-21-create-storico-scope-policy` |
| `dbops.fn_storico_risolvi_scope(schema, tabella, riga jsonb) → emittenti_fiscali.id` — ricorsiva su PADRE, `SECURITY DEFINER` del proprietario, `search_path` fissato, padre risolto con `to_regclass` e castato al tipo vero di `id`; non solleva mai tranne sul ciclo | `20_code/dbops/20260911-22-create-fn-storico-risolvi-scope` |
| Seed CSV, **121 righe generate dal catalogo** (modo dalla policy `ef_whitelist`, padre dalla FK reale): 37 protette (6 EF, 3 SR, 3 BA, 25 PADRE) + 84 `NESSUNO` con ragione | `80_data/sql/dbops/storico_scope_policy.csv` + `80_data/changelog/20260911-23-upsert-dbops-storico-scope-policy` |
| Codice `E_STORICO_SCOPE_CATENA_CICLICA` (TECNICO), messaggio id 1061 | `codici_errore.csv`, `messaggi_errore.csv` |
| pgTAP, 28 asserzioni: completezza della mappa (ogni madre col trigger ha riga; nessuna madre in RLS a `NESSUNO`; nessuna riga orfana), coerenza col catalogo (colonne, FK, `id` del padre, catene che terminano, ogni modo del CHECK ha il suo ramo), postura del resolver (DEFINER, search_path, proprietario dei padri in RLS, EXECUTE), comportamento **sui valori** e su tabelle temporanee (EF, SR, PADRE a due salti con tre tipi di `id`, FK nulla, padre sparito, NESSUNO, non mappata, ciclo, BA) | `db/pgtap/dbops/test-storico-scope-policy-v1.sql` |
| Manuali dei due oggetti; sezione *Di chi è una versione* nella guida della storicizzazione | `docs/it/dbzero/dbops/manual/`, `docs/it/guide/storicizzazione-tabelle.md` |

Prove (SQL estratto, `BEGIN … ROLLBACK`): tabella + funzione + CSV caricato, FK
differita che respinge un padre senza riga, resolver su tutti i rami, ciclo che
solleva `P0001`; pgTAP concatenato **28/28** (il 27 con le due righe dei codici
caricate nella stessa transazione). Sei guardrail statici verdi.

⚠️ **Lato BE**, come per ogni codice nuovo: `manage.py genera_error_policies` e la
frase di ripiego in `USER_MESSAGE_FALLBACK` — il cancello
`test_error_codes_db_policy_guardrail` lo ricorda.

### Trovato facendo il seed

* `anagrafiche._legacy_risorse_umane_auth_user` ha **due** trigger di storico
  (`_legacy_risorse_umane_auth_user_id` e `risorse_umane_auth_user_id`) che
  scrivono nella stessa shadow con due colonne FK diverse: ogni modifica produce
  due versioni. Difetto della legacy, non dello scope; registrato, non toccato.
* ✅ **Vista di presidio per il digest** — **deciso (a) da Tid il 12-09,
  costruita e applicata (00:30)**: `dbops.vw_storico_scope_da_dichiarare` (`20_code/dbops/20260912-06`,
  grant `90_end/20260912-07`, riga in `dbops.presidi` natura `ZERO`, cadenza
  `SETTIMANALE`, registro `dbops.storico_scope_policy`). Tre motivi: `SENZA_RIGA`
  (madre col trigger senza riga), `PROTETTA_NESSUNO` (madre in RLS dichiarata
  NESSUNO, con la ragione accanto), `RIGA_SENZA_MADRE` (riga stantia). Confronto
  per `to_regclass`, non per nome. Il pgTAP della mappa sale a **32**: i test 29-32
  provano che la vista dica il vero su casi **costruiti** (una madre temporanea
  col trigger: prima senza riga, poi in RLS con riga NESSUNO; le righe di prova
  come stantie) e che sia a catalogo. Oggi sul mondo vero è vuota.

---

## 4d. Passi 3-7 — la costruzione (applicata l'11-09-2026 alle 19:54)

| Cosa | Dove |
| --- | --- |
| **La primitiva** `dbops.fn_storico_arma_scope(schema, tabella, dry_run)` + `_tutte`: colonne `origine_schema` (NOT NULL se la shadow è vuota) e `scope_emittente_fiscale_id` con indice, `REVOKE DELETE` all'app, e — se la mappa dice protetta — RLS con `rls_sto_<tab>_ef_whitelist` (FOR SELECT, `fn_scope_ef_whitelist` sull'emittente congelato, veste OPERATORE) + `rls_sto_<tab>_trg_ins/upd` con `true`. Idempotente, non disarma mai, WARN dove il migratore non è proprietario | `20_code/dbops/20260911-24` |
| Il resolver con firma a `%TYPE` e il **ripiego sull'archivio del padre** (sotto) | `20_code/dbops/20260911-25` |
| Il **generatore** chiama la primitiva sulla shadow appena creata: nasce armata | `20_code/dbops/20260911-26` |
| One-shot `_tutte` sulle 121 esistenti, **prima** del trigger | `00_schema/storico/20260911-27` |
| **Il trigger**: `origine_schema` + scope (risolto una volta, su NEW e su OLD per la versione iniziale) nei due INSERT; chiusura `WHERE … AND (origine_schema = $3 OR origine_schema IS NULL)`; **preCondition HALT** «nessuna shadow senza le due colonne» | `20_code/script/20260911-28` |
| Convergenza `runAlways` in 90_end | `90_end/20260911-29` |
| **Backfill** `fn_storico_backfill_scope(_tutte)`: dallo snapshot; nelle shadow condivise attribuisce la versione alla madre di cui porta una chiave **esclusiva** (`jsonb_exists_any`, non l'operatore col punto interrogativo, che in Liquibase va scappato); NOT NULL quando nessuna riga resta NULL; residue contate a fine giro per shadow distinta | `20_code/dbops/20260911-30` + `90_end/20260911-31` |
| **Grant**: schema `storico` «senza DELETE» nell'elenco dichiarato del loop `20260205-41`, nel provisioning `provision_db_roles.sql`, e nella primitiva (i DEFAULT PRIVILEGES darebbero DELETE a ogni shadow nuova) | loop, provisioning, `-24` |
| **Provisioning da superuser** `scripts/sql/provision_storico_scope.sql`: riassegna al migratore le shadow di `postgres`, arma tutte, backfill | `scripts/sql/` |
| pgTAP `storico/test-storico-scope-congelato-v1` (22): struttura delle shadow vere; su madri **costruite** (due aziende, tre madri di prova, una omonima in `acquisti`, una figlia con FK a cascata): nasce armata, origine, scope A/B, NESSUNO → NULL, **collisione** (due versioni aperte, una per origine), chiusura, **DELETE a cascata** col ripiego, **congelato** (le versioni precedenti non seguono il cambio), lettura RLS (A vede A, non B, non NULL, non senza veste), il trigger **scrive attraverso la RLS**, nessun DELETE all'app | `db/pgtap/storico/` |
| Manuali (`fn_storico_arma_scope`, `fn_storico_backfill_scope`, note su generatore e trigger), guida storicizzazione, `provisioning-db-roles.md`, linee-guida §10.1 (lo storico non è più fuori dalla RLS) | `docs/` |

### ⭐ Aggiunta di disegno: il ripiego sull'archivio del padre (D5)

Trovata provando il backfill: 50 versioni di `fatture_scadenze` su 60 avevano la
fattura **sparita**, e il resolver rispondeva NULL. Ma non è solo pregresso: in un
`DELETE … CASCADE` il padre è **già cancellato** quando il trigger del figlio
scrive la versione finale — a runtime, ogni figlia di un documento cancellato
nascerebbe senza scope, cioè invisibile. ⇒ Il ramo `PADRE` del resolver, se il
padre non è vivo, legge la sua **ultima versione nello storico** (`storico.<padre>`,
colonna `STORICO_FK` con override, filtrata per origine) e continua da lì. ⭐
Leggere l'archivio del padre è leggere il **passato**: il §2.1 resta intatto. Con
il ripiego: 56 su 60 (le 4 restanti non hanno né padre né archivio). Test 14 del
pgTAP: DELETE a cascata → la figlia porta l'EF del padre letto dall'archivio.

### Prove (11-09, SQL estratto, `BEGIN … ROLLBACK`)

`_tutte`: 121 madri, 55 shadow allineate, **11 armate**, 66 saltate (`postgres`);
backfill **12.952 versioni, 0 residue**; `storico.ddt` già `NOT NULL`; scrittura
vera su `vendite.ddt` (EF) e `fatture_scadenze` (PADRE): versione nuova con
origine e scope giusti, precedente chiusa; generatore: shadow nuova con RLS, 3
policy, origine NOT NULL. pgTAP concatenato: **22/22 su `zeroerp_ci`** (tutto di
`zeroerp`), 19/22 su dev — rossi 2, 3, 22, cioè le 66 shadow di `postgres`, che
è esattamente ciò che il provisioning risolve. Sei guardrail statici verdi.

### ✅ Com'è andato l'apply (11-09-2026, dalla `databasechangelog` e dall'audit)

| Ora | Cosa |
| --- | --- |
| 19:40 | `-24`…`-27` applicati; `_tutte`: 121 madri, 55 allineate, 11 armate, **66 saltate** (di `postgres`) |
| — | `-28` **fermata** dalla preCondition: `Expected '0' got '66'` — come previsto |
| 19:50 | prima corsa del provisioning: `ALTER OWNER` di 68 shadow ✅, poi **`saltate_owner: 121`** — la primitiva agisce solo dove «proprietario = chi esegue», e chi eseguiva era `postgres`. Più un `:'var'` dentro un `DO`, che psql non interpola. Due correzioni allo script: `set_config` per il ruolo, **`SET ROLE` al migratore** prima di armare, backfill condizionale (la `-30` viene dopo la `-28`) |
| 19:54 | seconda corsa: `armate 37, allineate 66, saltate 0`; poi il migrate: `-28`, `-30`, `-29`, `-31` |
| 19:54 | backfill: **65.751 versioni, 0 residue**; tutte le 116 shadow con madre a `origine_schema NOT NULL`, anche le sei condivise |

Letto sulla struttura dopo l'apply: 120 shadow tutte di `titodb`; **37 armate** con
111 policy; `DELETE` dell'app revocato su 116 — restano le **4 orfane** (senza madre
col trigger: nessun passo le tocca). Il trigger vivo scrive origine e scope e
chiude per origine. pgTAP di Tid: nessuna regressione.

⚠️ Le due trappole del provisioning si vedevano **solo sul percorso vero**: il mio
dry-run da `titodb` era proprietario e sostituiva la variabile a mano. Memoria:
`reference_provisioning_da_superuser_set_role_al_migratore`.

### 🟠 Debiti registrati

* ✅ **Le shadow del job pgAgent nascevano di `postgres`** → **deciso (a), Tid
  11-09**: *l'archivio di una tabella è di chi possiede la tabella*. Il
  generatore, creata e **armata** la shadow (arma chi la crea, perché ne è
  proprietario), la **cede al proprietario della madre** — se chi crea può farlo
  (superuser o membro), altrimenti WARN. Vale identico su dev e in CI senza
  toccare il job. `20_code/dbops/20260911-34`; presidio: test 23 del pgTAP
  storico (ogni shadow ha il proprietario della madre). Scartate: (b) il job
  come migratore (password nella connessione, due configurazioni), (c) il
  provisioning nel calendario (cura il sintomo).
* Le versioni legacy **senza padre né archivio** (4 su `fatture_scadenze`, e
  simili altrove) restano a scope NULL: invisibili agli operatori, visibili
  all'amministrazione. Non ricostruibili: si lascia in chiaro.
* Correzione alla nota di §8.4: `fn_grant_storico_shadows` **non** concedeva
  DELETE; il DELETE dell'app sulle shadow veniva dal loop `20260205-41`, dal
  provisioning e dai DEFAULT PRIVILEGES. Ora tutte e tre le sedi lo negano.
* ✅ **Le «quattro shadow orfane»** — **decise da Tid l'11-09, costruite il 12**:
  «non teniamo sporcizia». Ma il censimento dei lettori ha corretto la mia
  classificazione, e la risposta è diversa per natura:
  · `storico.comune_trasformazioni` e `storico.stradario_trasformazioni` **non
    sono shadow**: sono i **registri delle fusioni** di comuni e vie, scritti da
    `fn_admin_merge_*` e letti da `script.fn_get_vie_discendenti` — vuote perché
    nessuna fusione è ancora avvenuta. **Restano.** Abitano nello schema sbagliato
    per il nome che portano: debito di *nome*, da valutare a parte, non sporcizia;
  · `storico.fatturazione_lotti_attivita` (dominio ritirato, 0 righe, zero
    lettori) → **DROP**, `00_schema/storico/20260912-02`;
  · `storico.risorse_umane_auth_user` (12 versioni di prima della rinomina della
    madre) → **DROP**, `00_schema/storico/20260912-03`. ✅ **Consegna al backend
    CHIUSA il 12-09**, e in modo diverso da come era scritta qui.
    `backend/apps/core/db/permissions_audit_repository.py`, `_USER_TABLES`,
    leggeva questa tabella nella timeline della storia dei permessi; ⚠️ il
    changeSet è passato alle 00:30 **prima** della modifica al backend (doveva
    essere il contrario), e per qualche ora l'endpoint su dev ha risposto
    **500** (`42P01`). La riga proponeva di ripuntare alla shadow legacy
    (`storico._legacy_risorse_umane_auth_user`, 12 versioni di prima della
    rinomina) tenendo il label. ⭐ **Non si è fatto così, per decisione di Tid**:
    quella storia sono **dati di test** di una tabella dismessa — senza
    produzione non rappresentano niente, e leggerli dalla timeline farebbe
    sembrare vivo un bridge morto. La tupla nuova è
    `("storico.identita_digitali", "identita_digitali")`: la shadow della
    tabella dove l'identità **vive** dal multi-face auth (ruolo applicativo,
    attivo, validità, blocco), con `auth_user_id` nello snapshot. Il label
    `risorse_umane_auth_user` è **ritirato** (chi lo filtra prende `400`:
    contratto rotto di proposito, non in produzione). Verificato il 12-09 con la
    chiamata **vera** sotto contesto operatore: niente `42P01`, 18 eventi per
    l'utente 1; `test_permissions_audit` 14/14; doc `api_permessi_audit.md`
    riscritta con le 8 tabelle e i label. `amm_software_repository.py` non la
    legge: passa dal catalogo `dbops.audit_sources`, dove la riga 5 è `attivo =
    f`. ⇒ **Nessun lettore resta**, e la shadow `_legacy_` è sporcizia:
    📮 **DROP al team DB** (§9.3), insieme alla riga 5 del catalogo che la
    nomina.
* ✅ **Il «doppio trigger» sulla legacy era un BLOCCO, non un doppione.**
  `trg_risorse_umane_auth_user_z90_storico_upd_dlt`, rimasto dal nome vecchio,
  scriveva nella shadow viva con la colonna `risorse_umane_auth_user_id`, che lì
  non esiste: con `storicizza = true` **ogni** UPDATE/DELETE su
  `_legacy_risorse_umane_auth_user` falliva (`E_SNAPSHOT_CLOSE_ERROR`, provato in
  ROLLBACK). Non si vedeva perché le 6 righe hanno `storicizza = false`.
  `DROP TRIGGER IF EXISTS` in `00_schema/anagrafiche/20260912-01` (la forma
  lecita di §11.5: in CI non nasce). Dopo, l'UPDATE scrive la versione nella
  shadow viva.
* Correzione alla nota di §8.4: `fn_grant_storico_shadows` **non** concedeva
  DELETE; il DELETE dell'app sulle shadow veniva dal loop `20260205-41`, dal
  provisioning e dai DEFAULT PRIVILEGES. Ora tutte e tre le sedi lo negano.
* **Quattro shadow ORFANE** (letto l'11-09 al primo fermo della `-28`): tabelle
  in `storico` senza una madre col trigger — `comune_trasformazioni`,
  `stradario_trasformazioni` (vuote, `titodb`), `fatturazione_lotti_attivita`
  e `risorse_umane_auth_user` (`postgres`; la madre della seconda oggi è
  `anagrafiche._legacy_risorse_umane_auth_user`). Nessun passo le tocca, perché
  il marcatore è il trigger: né colonne, né policy, né revoca del DELETE.
  ⚠️ `storico.risorse_umane_auth_user` la legge il backend (storia dei permessi):
  è una shadow viva con la madre rinominata, non un residuo. Da decidere: madre
  cancellata o storicizzazione tolta → si archivia o si cancella; madre
  rinominata → si riaggancia. Non deciso qui.

---

## 5. I passi, e il costo

| # | Passo | Stima |
| --- | --- | --- |
| 1 | **Il disegno**: quante colonne di scope, come si chiamano, la forma della mappa | ½ g — ⭐ **è la parte che conta** |
| 2 | ✅ **La mappa** (`dbops.storico_scope_policy` + seed) e **il resolver** (`dbops.fn_storico_risolvi_scope`) — consegnati l'11-09, §4c | ½ g |
| 3 | ✅ `dbops.fn_storico_arma_scope` (colonne, indice, REVOKE DELETE, RLS + 3 policy) chiamata dal generatore alla nascita e da `_tutte` sulle 121 esistenti — §4d | ½ g |
| 4 | ✅ `trgfn_storico_generic`: origine + scope in ogni versione, chiusura filtrata sull'origine; preCondition HALT «nessuna shadow senza le colonne» — §4d | ½ g |
| 5 | ✅ `dbops.fn_storico_backfill_scope(_tutte)`: dallo snapshot, con le chiavi esclusive per le shadow condivise, NOT NULL quando è vero — §4d | ½ g |
| 6 | ✅ **pgTAP** `storico/test-storico-scope-congelato-v1` (22) + `dbops/test-storico-scope-policy-v1` (28) — §4d | ½ g |
| 7 | ✅ **Grant**: `storico` senza DELETE per l'app nel loop `20260205-41`, nel provisioning e nella primitiva stessa (`fn_grant_storico_shadows` già non lo dava) — §4d | ¼ g |

⇒ **≈ 3 giornate.**

### ⛔ E si fa PRIMA che `acquisti` e `magazzino` crescano

Il §9 del brief del perimetro diceva il contrario — *«un generatore ha senso
quando le madri sono ferme»* — e **quell'argomento è rovesciato**: vale per un
lavoro **manuale** (120 policy a mano si rifanno a ogni tabella nuova), ma un
generatore **esiste proprio per assorbire le tabelle nuove**.

⇒ Farlo adesso significa che le tabelle di `acquisti` e `magazzino` **nascono
protette**. Farlo dopo significa un backfill più grande e, nel frattempo, uno
storico aperto **anche sui domini nuovi**.

---

## 6. ⛔ Le due cose che il §9 sbagliava, e perché sono scritte qui

Restano registrate perché sono il tipo di errore che **ferma o svia un cantiere**,
ed è già successo tre volte nel registro del perimetro (§11.12 e §11.18 di quel
brief): una *ragione* scritta male non viene riletta da nessuno.

1. **«Derivando lo scope dalla madre»** — è la formula che non regge (§2.1, §2.2).
2. **«Aspettare che le madri siano ferme»** — l'argomento giusto porta alla
   conclusione **opposta** (§5).

⚠️ **E una terza, di metodo, che riguarda come è nata questa analisi**: la prima
stesura portava come argomento il numero di righe orfane misurato sul database di
sviluppo. ⛔ È una fotografia, e *le decisioni non si prendono sui dati di test,
che possono non essere veritieri* (Tid, 2026-09-11). L'argomento vero è **2.2**:
il generatore non crea la FK **di proposito**, quindi il caso esiste nel modello
— e quel fatto vale identico su un database vuoto.

---

## 7. Cosa NON fare

* ⛔ **niente 120 policy scritte a mano**: nascerebbero disallineate, e la prima
  tabella nuova le renderebbe incomplete;
* ⛔ **niente scope letto dal JSONB** (§3);
* ⛔ **niente risalita a runtime alla madre** (§2.1, §2.2);
* ⛔ **niente `FOR ALL`** su una tabella che scrive solo il trigger (§4.3);
* ⛔ **non trattare `dbops.audit_log` come una tabella di storico** — è il §8, e
  la conclusione è che *non* si ripara con una policy di perimetro.

---

## 8. `dbops.audit_log` — stessa FAMIGLIA di difetto, rimedio DIVERSO

> Aggiunto su richiesta di Tid il 2026-09-11: *«dato che è della stessa forma»*.
> ⭐ La forma del **difetto** lo è — *il dato è protetto, la sua traccia no*. La
> forma del **rimedio** no, e applicargli il disegno dei §2-§4 sarebbe un errore.

### 8.1 Perché non è una tabella di storico

| | `storico.<tabella>` | `dbops.audit_log` |
| --- | --- | --- |
| Ha una **madre** | ✅ una per tabella, con la chiave in colonna | ⛔ **nessuna**: registra l'esecuzione di una *funzione*, non lo stato di una riga |
| Da dove viene lo scope | dalla riga che il trigger ha in mano | ⛔ da nessuna parte: **non esiste una riga da cui prenderlo** |
| Quante sono | 120, generate da un framework | **una**, scritta a mano |
| Chi la scrive | un trigger generico | **18 funzioni**, per la porta `dbops.fn_audit_log_once` |

⇒ Il meccanismo «cattura alla scrittura e congela» **non è trasportabile**: qui
non c'è una riga madre da cui catturare. Lo scope, se servisse, andrebbe
**passato da chi chiama** — cioè aggiunto alla firma della porta di scrittura e
valorizzato da diciotto chiamanti.

### 8.2 ⛔ E la premessa del D3 non regge sulla struttura

Il D3 dice che `params` e `result` contengono, *«per le funzioni di dominio, gli
argomenti e l'esito di operazioni su documenti protetti»*.

⛔ **Letto dal catalogo il 2026-09-11: nessuna funzione di dominio ci scrive.**
Delle 18 che nominano `audit_log`, **17 sono in `dbops`** e una in `script`
(`fn_audit_summary`, che è una lettura). Non ce n'è nessuna in `vendite`,
`anagrafiche`, `pagamenti`.
⇒ È il **registro delle automazioni e degli strumenti DBA**, e lo legge
`backend/apps/amm_software` — l'area di amministrazione, quella del `SUPER_ADMIN`.

⚠️ **Questo non cancella il problema, lo sposta**: la porta `fn_audit_log_once` è
aperta a chiunque, e niente nel modello impedisce che domani una funzione di
`vendite` ci scriva i propri parametri. *Zero occorrenze non significa che il
caso non esiste.* Ma cambia **quale** sia la domanda giusta.

### 8.3 La domanda che viene prima di qualunque policy

> **Questo registro deve poter contenere dati di dominio?**

| Risposta | Che cosa comporta |
| --- | --- |
| **No** — è un registro tecnico | ⭐ Il presidio giusto **non è una policy**: è un **cancello** che impedisce a una funzione di dominio di scriverci, nello stile dei guardrail CI già in servizio. Il rischio sparisce **alla fonte**, e non si paga un filtro per riga su un log |
| **Sì** | serve una colonna di scope **nella firma** di `fn_audit_log_once`, valorizzata dai chiamanti, e una policy che la legge. ⚠️ Con il ramo «riga senza scope» da decidere: un'automazione di manutenzione non ha emittente, e quelle righe sono la maggioranza per natura |

⛔ **In nessuno dei due casi la forma è quella dello storico**, ed è per questo
che sta in una sezione sua invece che nell'elenco delle tabelle da generare.

### 8.4 Il REVOKE — quello che si è potuto fare subito, e le due cose che questa sezione sbagliava

> ✅ **Consegnato il 2026-09-11.** Decisioni di Tid nello stesso giorno, prese sulla
> struttura letta e non sulle righe.

Il fatto di struttura resta vero: `zeroerp_app` aveva `SELECT, INSERT, UPDATE,
DELETE` su un registro che **legge l'amministrazione** e **scrivono le
automazioni**. E resta vera la frase: *un registro di audit modificabile da chi è
auditato non è un registro*. ⛔ **Ma la prima stesura di questa sezione sbagliava
due volte**, e le due cose sono scritte qui perché sono della stessa specie di
quelle del §6 — una ragione scritta male che avrebbe sviato il cantiere.

#### ⛔ Errore 1 — «privilegi che nessuno usa»: l'UPDATE è PREVISTO DAL DISEGNO

La guida `messaggi-audit` documenta la **modalità sessione**: `fn_audit_begin`
apre una riga `START`, `fn_audit_end` la chiude — con un
`UPDATE dbops.audit_log … WHERE id = p_id`. Tutte e tre le funzioni sono
`SECURITY INVOKER` e l'app aveva `EXECUTE`. Fanno UPDATE diretto anche le due
`fn_admin_merge_comune/stradario` (strumenti DBA). Letto sulla struttura il
2026-09-11: **nessuna delle tre ha un chiamante** — né nel DB, né nel backend, né
in pgAgent — ma il contratto scritto c'è, e «zero chiamanti» non è una ragione.

⇒ **La domanda giusta era di modello**: *l'applicazione deve poter chiudere una
sessione di audit?* **Decisione (Tid, 2026-09-11): no.** La modalità sessione è
**riservata a chi possiede la tabella** (migratore, job); l'app scrive con la sola
`fn_audit_log_once`. Corollario: se non può chiudere non deve poter aprire —
altrimenti lascia `START` orfane — quindi la coppia begin/end perde l'`EXECUTE`
per l'app. ⚠️ E le funzioni avevano `=X`: PUBLIC aveva EXECUTE, e revocare al solo
`zeroerp_app` non avrebbe tolto niente. Si revoca `FROM PUBLIC, zeroerp_app`.

Il `DELETE` invece **non lo fa nessuno**, da nessuna parte; e l'`INSERT` dell'app
**serve** — `fn_check_funzioni_riferimenti_morti` (guardrail, gira come app) e
`fn_apply_chiusura_scadenze` (handler `coda_lavori`) scrivono via `fn_audit_log_once`.

#### 🔴 Errore 2 — «è una riga di REVOKE»: quella riga viene CANCELLATA

`90_end/ci_apply/20260205-41-apply-runtime-grants-ci` è `runOnChange` e a ogni
passata `ci_apply` rifà `GRANT SELECT, INSERT, UPDATE, DELETE` a `zeroerp_app` su
tutte le tabelle di 14 schemi, `dbops` compreso, più `EXECUTE` su ogni funzione.
Un REVOKE in un changeSet normale sopravvive su dev fino al prossimo
`db-ci-apply` — e sembra funzionare, a lungo — e in CI viene annullato **nello
stesso build**. ⭐ Provato il 2026-09-11 in transazione ritirata: forward +
loop originale ⇒ `UPDATE, DELETE` tornano concessi e `zeroerp_app=X` riconcesso.

⇒ **Decisione (Tid, 2026-09-11): loop dichiarativo.** La postura più stretta si
dichiara **dentro** il loop — due elenchi in testa al blocco,
`v_registri_append_only` e `v_fn_riservate` — che da oggi concede a quei registri
solo `SELECT, INSERT` e revoca il resto a ogni passata. Più un changeSet `90_end`
forward che revoca subito, perché su dev `ci_apply` non gira da solo. Regola
scritta in [linee-guida-sql §11.8](../../linee-guida-sql.md) e in AGENTS.md.

#### ⭐ E non era un caso solo: `dbops.error_log` è della stessa classe

Stessa postura (`arwd`), stessa natura: nessuna funzione e nessun codice Python lo
aggiorna o cancella. **Decisione (Tid): incluso** — due registri, una regola, ed è il
secondo caso che giustifica l'elenco dichiarato.

#### Consegnato

| Cosa | Dove |
| --- | --- |
| REVOKE forward: `UPDATE, DELETE` su `audit_log`/`error_log`; `EXECUTE` su begin/end `FROM PUBLIC, zeroerp_app` | `90_end/20260911-09-revoke-app-update-delete-registri-audit` |
| Eccezione dichiarata nel loop dei grant | `90_end/ci_apply/20260205-41` (editato: è `runOnChange` + `validCheckSums: ANY`, il suo ciclo di vita) |
| Default di `executed_by` (vedi sotto) | `00_schema/dbops/20260911-20-alter-audit-log-executed-by-default` |
| pgTAP, 24 asserzioni: postura a catalogo (`has_*_privilege`, mai `role_table_grants`) + comportamento come app (`42501`) + la porta `fn_audit_log_once` aperta e firmata | `db/pgtap/dbops/test-registri-append-only-postura-v1.sql` |
| Guida *Chi può scrivere*, manuali dei cinque oggetti, §11.8 linee guida, AGENTS.md | `docs/it/guide/messaggi-audit.md`, `docs/it/dbzero/dbops/manual/*`, `linee-guida-sql.md`, `.codex/AGENTS.md` |

Prove fatte (2026-09-11, SQL **estratto** dagli YAML, in `BEGIN … ROLLBACK`):
forward ⇒ postura stretta; loop editato ⇒ **non riapre**; rollback ⇒ ripristina;
loop originale ⇒ riapre (controprova). pgTAP provato come app sullo stato
pre-apply: rosse esattamente le 13 asserzioni che i changeSet ribaltano, verdi le
altre 11. Sei guardrail statici verdi. ✅ **Applicato il 2026-09-11 alle 12:42**
(`20260911-09`, `20260911-20`); postura viva riletta a catalogo: `INSERT` sì,
`UPDATE`/`DELETE` no su entrambi, begin/end senza `=X` né app, default
`CURRENT_USER` funzione. ⚠️ Su dev il loop `20260205-41` non gira dal 2026-05-07:
la stretta la tiene il forward, l'eccezione nel loop si eserciterà in CI al
primo build.

#### 🔴 Trovato scrivendo il pgTAP: il registro non ha mai registrato CHI esegue

`executed_by` aveva come default la **stringa** `'CURRENT_USER'` — le virgolette
fanno la differenza fra la funzione e la parola — e nessuna porta di scrittura
la valorizza. Struttura: `pg_attrdef` → `'CURRENT_USER'::text`. Controesempio
sui dati di sviluppo: **3014 righe su 3014** con la parola. Un registro che non
sa dire chi è l'auditato non è un registro più di uno che si lascia riscrivere:
stessa domanda, altro lato. ⇒ `20260911-20` porta il default a `current_user`
(il **ruolo** di database, non l'operatore — quello viaggia nelle GUC e nel
`tx_id`). ⛔ Nessun backfill: il pregresso non si può ricostruire e resta
riconoscibile. Test 24 del pgTAP.

#### 🔴 Trovato dalla baseline CI, lo stesso giorno: il loop non era l'ultima parola

Il pgTAP `test-registri-append-only-postura-v1` era **verde su dev e rosso su
`zeroerp_ci`**. Letta la postura direttamente sul database CI (come `zeroerp`,
`has_table_privilege` / `proacl`): `UPDATE`/`DELETE` **concessi**, `EXECUTE` su
begin/end **concesso** — con `20260911-09` regolarmente `EXECUTED`. Chi riapriva?
**`scripts/sql/provision_db_roles.sql`**: gira come `postgres` **dopo**
`--contexts=ci_apply` sia in `ci-validate.yaml` sia in `ci-local.sh`, e fa
`GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA` e `GRANT EXECUTE
ON ALL FUNCTIONS IN SCHEMA` a `zeroerp_app`. Le sedi della postura non erano due
ma **tre**, e la terza — l'ultima a parlare — non sapeva niente dell'eccezione.
Su dev non si vede perché il provisioning non si rilancia dopo ogni migrate: è
la forma esatta del «verde su dev non dice nulla sulla CI».

⇒ Il provisioning porta ora la **stessa eccezione** (blocco «POSTURA DICHIARATA»
in coda ai `GRANT ON ALL`): `REVOKE UPDATE, DELETE` sui due registri, `REVOKE
EXECUTE … FROM PUBLIC, zeroerp_app` sulle due porte. Idempotente, salta gli
oggetti assenti. Provato come `zeroerp` su `zeroerp_ci` in transazione ritirata:
la postura torna quella che il test pretende. Il commento del loop `-41`, che
si dichiarava «l'unico posto che non può annullarla», è corretto. ⭐ Il pgTAP è
il presidio delle tre sedi, e ha morso il primo giorno: è il suo mestiere.
Regola: [[reference_grant_loop_ci_apply_annulla_grant_per_colonna]] aggiornata.

#### 🟠 Debiti registrati, non saldati qui

* ✅ **`fn_admin_merge_comune` / `fn_admin_merge_stradario`** — **deciso (a) da Tid
  il 12-09, costruito e applicato (00:30)**: passano dalla porta `fn_audit_log_once`, una chiamata a
  fine lavoro con esito, conteggio dei ripuntati e durata (`20_code/dbops/20260912-04`,
  `-05`; firma a `%TYPE`, identità invariata). Il corpo vecchio aveva **tre**
  difetti, non uno: status iniziale `'STARTED'` che il `CHECK` non ammette (la
  funzione falliva alla prima riga), `UPDATE` di chiusura che l'app non può più
  fare, riga `ERROR` annullata dal `RAISE`. Provato in ROLLBACK: fusione di due
  comuni, audit `OK` dalla porta, riga nel registro delle fusioni.
  ⏳ **Debito che resta**: le tre validazioni sollevano `RAISE EXCEPTION` in
  chiaro, senza codice registrato — da coniare (`E_MERGE_ORIGINE_UGUALE_DESTINAZIONE`
  `DATO_ERRATO`, `E_COMUNE_NON_TROVATO` / `E_STRADARIO_NON_TROVATO` `NON_TROVATO`)
  quando la funzione avrà un chiamante applicativo.
* **Le shadow `storico.*`** — ⚠️ riguarda i passi 2-6 di **questo** brief. Letto il
  2026-09-11: 120 shadow, **tutte** con `UPDATE` e `DELETE` per `zeroerp_app` (52
  possedute da `titodb`, via il loop; 68 da `postgres`, via provisioning /
  `fn_grant_storico_shadows`). Il §4.3 dice che lo storico *lo scrive il trigger,
  non l'applicazione*: la stessa domanda del §8.4 vale per tutte e 120, e la
  forma del rimedio è un'eccezione **per schema** nel loop, non un elenco.
  ✅ Verificato (§4b.2): `trgfn_storico_generic` **aggiorna** la riga precedente
  (`valid_to`), quindi all'app servono `INSERT` e `UPDATE`; da togliere è il solo
  `DELETE`. È il passo 7 della tabella §5.

### 8.5 Stima — aggiornata

| | |
| --- | --- |
| La **decisione** §8.3 | ✅ **«No»** (Tid, 2026-09-11): è il registro delle automazioni e degli strumenti DBA, letto dall'amministrazione. Nessun dato di dominio |
| Il REVOKE di §8.4 + eccezione nel loop + default `executed_by` + pgTAP + doc | ✅ **fatto** il 2026-09-11 — una giornata, non mezza: il resto era la premessa sbagliata |
| Il cancello (ramo «No») | ✅ **costruito** il 2026-09-11, §8.6 — un'ora, non mezza giornata: la forma dei presidi CANCELLO esisteva già |
| La colonna di scope (ramo «Sì») | ⛔ non si fa: ramo scartato dalla decisione |

### 8.6 Il cancello — costruito l'11-09-2026, applicato (`-32` alle 20:11, `-33` a seguire)

| Cosa | Dove |
| --- | --- |
| `dbops.vw_audit_log_scrittori_fuori_perimetro`: le funzioni che scrivono nel registro (DML diretto o via `fn_audit_log_once`/`begin`/`end`) e stanno **fuori dal perimetro dichiarato nella vista stessa**, `dbops` e `maintenance`. Sorgente letto senza i commenti; le letture non contano; le tre funzioni di audit escluse per nome. `security_invoker` | `20_code/dbops/20260911-32` |
| Riga in `dbops.presidi`, natura **CANCELLO**, `cadenza MAI`, `presidiato_da` il pgTAP | `80_data/sql/dbops/presidi.csv` |
| `GRANT SELECT` all'app (pgTAP e digest la leggono come app) | `90_end/20260911-33` |
| pgTAP, 6 asserzioni: vuota; gemello «esiste» (scrittori dentro il perimetro, stessa regex, senza passare dalla vista); il perimetro è {dbops, maintenance}; una funzione **costruita** in `pg_temp` che chiama la porta viene vista e classificata; la riga di catalogo c'è | `db/pgtap/dbops/test-audit-log-perimetro-scrittori-v1.sql` |

Provato in `ROLLBACK`: vista vuota oggi (19 scrittori, tutti in `dbops`), 6/6.
⭐ Il perimetro è il contratto: se un giorno `script` dovesse scrivere l'audit,
è un changeSet su questa vista, firmato — non una riga che passa in silenzio.

---

## 9. Stato finale (12-09-2026) e che cosa resta

### 9.1 Applicato — letto dal `databasechangelog` e dal catalogo

| ChangeSet | Cosa | Applicato |
| --- | --- | --- |
| `20260911-32`, `-33` | cancello su `dbops.audit_log`: `vw_audit_log_scrittori_fuori_perimetro` (CANCELLO a catalogo) + grant | 11-09 20:11 |
| `20260911-34` | il generatore cede la shadow al proprietario della madre | 12-09 00:04 |
| `20260912-01` | via il trigger stantio sulla madre legacy (bloccava ogni scrittura con `storicizza = true`) | 12-09 00:30 |
| `20260912-02` | via `storico.fatturazione_lotti_attivita` (dominio ritirato) | 12-09 00:30 |
| `20260912-03` | via `storico.risorse_umane_auth_user` — ✅ consegna BE chiusa il 12-09 su `storico.identita_digitali` (§4d) | 12-09 00:30 |
| `20260912-04`, `-05` | le due merge scrivono l'audit dalla porta | 12-09 00:30 |
| `20260912-06`, `-07` + `presidi.csv` | `vw_storico_scope_da_dichiarare` (ZERO, settimanale) + grant | 12-09 00:30 |

Verificato sul catalogo il 12-09: le due viste esistono, sono a catalogo in
`dbops.presidi` (`CANCELLO`/`MAI` e `ZERO`/`SETTIMANALE`) e **rispondono zero
righe**; le due shadow orfane e il trigger stantio non esistono più.

### 9.2 Documentazione scritta il 12-09

Manuali nuovi: `dbops/manual/vw_audit_log_scrittori_fuori_perimetro.md`,
`vw_storico_scope_da_dichiarare.md`. Aggiornati: `fn_admin_merge_comune.md`,
`fn_admin_merge_stradario.md` (⛔ dicevano *«scrive l'audit prima di operare»*:
falso da ieri, e il corpo vecchio non ha mai funzionato), `fn_ensure_storico_table.md`
(la cessione al proprietario della madre), `storico_scope_policy.md` (il digest).
Guide: `storicizzazione-tabelle.md` (le tre chiusure del 12-09, il generatore),
`messaggi-audit.md` (§«Chi può scrivere — le funzioni: il perimetro»).
⚠️ Le pagine auto-gen delle due viste e delle funzioni riviste le produce il
giro di generazione: i manuali esistono già, quindi la riga `include-markdown`
verrà scritta.

### 9.3 Che cosa resta, e di chi è

| | Cosa | Di chi |
| --- | --- | --- |
| ✅ | `permissions_audit_repository._USER_TABLES` → `storico.identita_digitali` (non la `_legacy_`: §4d, decisione Tid 12-09). Endpoint verificato con chiamata vera, test 14/14, doc riscritta | fatto (BE, 12-09) |
| 📮 | **DROP `storico._legacy_risorse_umane_auth_user`** (12 versioni di test di un bridge dismesso: sporcizia, decisione Tid 12-09) e **cancellazione della riga 5 di `dbops.audit_sources`** che la nomina (`attivo = f` è la dichiarazione della dismissione; a shadow droppata la riga non dichiara più niente). Nessun lettore nel backend: `permissions_audit_repository` legge `identita_digitali`, `amm_software_repository` legge il catalogo | **DB** — changeSet forward `00_schema/storico` + `80_data` (DELETE, l'unica eccezione al «si cambia dal CSV») |
| ✅ | pgTAP post-apply **tutti verdi** (Tid, 12-09): `dbops/test-audit-log-perimetro-scrittori-v1` (6), `dbops/test-storico-scope-policy-v1` (32), `storico/test-storico-scope-congelato-v1` (23), `dbops/test-catalogo-presidi-v1` | fatto |
| ⏳ | Commit dei file del 12-09 ancora non tracciati: `20260912-04…07`, `presidi.csv`, `test-storico-scope-policy-v1.sql`, questo brief, i manuali e le guide di §9.2 | **Tid** |
| 🟠 | Debito dichiarato: i tre codici errore delle validazioni delle merge (`E_MERGE_ORIGINE_UGUALE_DESTINAZIONE`, `E_COMUNE_NON_TROVATO`, `E_STRADARIO_NON_TROVATO`), da coniare quando le funzioni avranno un chiamante applicativo | DB, cantiere futuro |
| 🟠 | Debito di **nome**: `storico.comune_trasformazioni` e `storico.stradario_trasformazioni` sono registri, non shadow, e abitano nello schema che dice il contrario. Da valutare a parte | DB, decisione di Tid |
| 🟠 | Le versioni legacy senza padre né archivio (4 su `fatture_scadenze`, e simili altrove) restano a scope NULL: invisibili agli operatori, visibili all'amministrazione. Non ricostruibili: si lascia in chiaro | nessuno |

⇒ ✅ **Chiuso e spostato in `work-done/` il 2026-09-12**: la riga 🔴 è
chiusa, i pgTAP sono confermati, il perimetro DB è completo. Il 📮 e i tre 🟠
sono debiti **dichiarati con la loro sede**, non lavoro rimandato: il DROP
della shadow legacy è un changeSet del team DB, e non tiene aperto un brief il
cui perimetro era la RLS sullo storico.

---

## 10. Coda del 12-09 — la madre legacy del ponte utente↔risorsa umana

> Richiesta del team BE dopo la chiusura del §4d (PR #1567:
> `permissions_audit_repository._USER_TABLES` legge `storico.identita_digitali`,
> label `risorse_umane_auth_user` ritirato, 14/14). **Decisione Tid
> 12-09-2026**: *la storia del vecchio ponte è solo dati di test di una tabella
> dismessa — senza produzione è sporcizia, va tolta.* Stato: ✅ **APPLICATO il
> 12-09-2026 alle 11:30** (`-08`, `-09`, `-10` `EXECUTED`), **pgTAP senza
> regressioni** (Tid). Verificato sul catalogo: madre, shadow e le due trigger
> function non esistono; mappa, `audit_sources` e `storico_set_storicizza` senza
> le righe; `vw_storico_scope_da_dichiarare` e
> `vw_audit_log_scrittori_fuori_perimetro` a **zero**.

### 10.1 La domanda che il BE ha lasciato aperta: la madre

Il BE chiedeva il DROP della shadow `storico._legacy_risorse_umane_auth_user`
(**vuota**: le 12 versioni stavano nella vecchia, già via col `-03`) e il ritiro
della riga 5 di `dbops.audit_sources`, e segnalava che la **madre**
`anagrafiche._legacy_risorse_umane_auth_user` aveva ancora il trigger di
storico: a shadow droppata un UPDATE fallirebbe, e a `ci_apply` la shadow
potrebbe rinascere. Due strade: (a) via anche la madre; (b) madre disarmata.

**Letto sul catalogo (12-09)** — struttura, non conteggi: nessuna FK entrante,
nessuna vista dipendente, nessuna funzione viva che la nomina, nessun pgTAP né
codice backend la scrive; la verità vive in `identita_digitali` e il nome vecchio
è una vista. ⛔ **Ma non era inerte**: due FK `ON DELETE RESTRICT` verso
`risorse_umane` e `django.auth_user` (sei righe di test che bloccano la
cancellazione di sei persone e sei utenti vivi); `trgfn_…_sync_active` che
riscrive `auth_user.is_active`; e la colonna `storicizza`, che è il marcatore
con cui `fn_run_automations_storico_provision` sceglie le madri — ogni
`ci_apply` l'avrebbe ri-armata e le avrebbe ricreato la shadow. La strada (b)
avrebbe dovuto togliere trigger **e** colonna, lasciando sei righe, due RESTRICT
e sette trigger su una tabella che nessuno legge. Il drop fisico era già in
piano (`sviluppo-multi-face-da-completare` §2.9), parcheggiato «finché non in
produzione»: la decisione di Tid toglie quella ragione.
✅ **Deciso (Tid, 12-09): (a).**

### 10.2 Consegnato

| ChangeSet | Cosa |
| --- | --- |
| `00_schema/storico/20260912-08` | `DROP TABLE IF EXISTS storico._legacy_risorse_umane_auth_user` — in CI non nasce mai (le shadow le crea `ci_apply`, e la madre se ne va nella stessa corsa) |
| `80_data/changelog/20260912-09` | ritiro delle **quattro registrazioni**: riga 6 di `dbops.storico_scope_policy` (altrimenti `RIGA_SENZA_MADRE` nel digest — provato), riga 5 di `dbops.audit_sources` (già `attivo = f`, puntava a una tabella eliminata dal `-03`), le due righe di `config.storico_set_storicizza` (la legacy **e** il nome vecchio, stantio dal cutover: il job non lo toglie perché `to_regclass` risolve la **vista**). CSV `storico_scope_policy.csv` e `audit_sources.csv` allineati (i mirror non cancellano) |
| `90_end/20260912-10` | `DROP TABLE IF EXISTS anagrafiche._legacy_risorse_umane_auth_user` (cadono otto trigger e due FK; nessun `CASCADE`, perché niente dipende da lei) + `DROP FUNCTION` delle due trigger function montate solo lì (`guard_persona_fisica`, `sync_active`) — altrimenti orfane per il presidio dei riferimenti morti. `fn_sync_auth_user_is_active` resta: la usano `identita_digitali` e `risorse_umane` |
| pgTAP nuovo `anagrafiche/test-legacy-risorse-umane-auth-user-ritirata-v1` (9) | il ritiro regge, **anche dopo `ci_apply`**: madre, shadow nuova e vecchia, le due funzioni non esistono; la funzione condivisa e la vista sì; mappa e `storico_set_storicizza` senza righe. ⚠️ Non sta in `test-risorse-umane-auth-user-view`, che è in baseline `ERRORE_FIXTURE` su dev e CI: un'asserzione lì sarebbe muta |
| pgTAP `dbops/test-audit-sources-seed` 7 → **8** | test 8: nessuna riga `risorse_umane_auth_user`; il codice resta nell'`IN` del test 2 contro una reinserzione attiva |

🔴 **Perché il DROP della madre sta in `90_end` e non in `00_schema`.**
`90_end/20260429-19a` fa `ALTER TABLE … DROP COLUMN ruolo_sistema` su questa
tabella con `onFail: HALT` e la pretende **esistente**; è mergiato e senza
`validCheckSums`, quindi non si tocca. Su un database ricostruito da zero tutto
`90_end` gira **dopo** tutto `00_schema`: un DROP in `00_schema` sarebbe passato
su dev (la `-19a` ha già girato) e avrebbe fermato la CI su quel cancello. Quindi
il DROP ha un nome che in `includeAll` viene dopo la `-19a` e dopo i due
`runAlways` dello scope (`20260911-29`, `-31`: su una shadow assente rispondono
`NO_SHADOW`). È la stessa ragione per cui la `-19a` stessa stava in `90_end`.
⭐ Regola generale: **prima di ritirare un oggetto, cercare i changeSet di fase
successiva che lo pretendono esistente** — su dev hanno già girato e non si
vedono; su un database da zero girano dopo il DROP.

### 10.3 Prove (12-09, SQL **estratto** con `updateSQL` offline, `BEGIN … ROLLBACK`)

Quattro transazioni ritirate, ognuna con i tre changeSet e il corpo di un pgTAP:
`test-legacy-…-ritirata-v1` **9/9**, `test-audit-sources-seed` **8/8**,
`test-storico-scope-policy-v1` **32/32**, `test-storico-scope-congelato-v1`
**23/23**. Controprova: il test nuovo **senza** i changeSet è rosso esattamente
su 1, 2, 4, 5, 8, 9 (verde su 3, 6, 7, già veri); e con la sola madre droppata,
senza il `DELETE`, `vw_storico_scope_da_dichiarare` mostra
`RIGA_SENZA_MADRE | anagrafiche._legacy_risorse_umane_auth_user`. Sei guardrail
statici verdi. ⚠️ Prova da owner: la RLS non è esercitata — il giro vero è di Tid.

### 10.4 Documentazione

Cancellati i tre manuali degli oggetti ritirati
(`anagrafiche/manual/_legacy_risorse_umane_auth_user.md`,
`storico/manual/_legacy_risorse_umane_auth_user.md`,
`storico/manual/risorse_umane_auth_user.md` — quest'ultimo orfano dal `-03`).
Aggiornati: `anagrafiche/manual/risorse_umane_auth_user.md` (la sezione che
diceva *«trigger inerti perché non ci sono più writer»* — vero per i trigger,
falso per le FK, che agiscono quando si cancella il **padre**),
`identita_digitali.md`, guide `risorse-umane-e-accessi`,
`soggetti-e-ruoli-anagrafici`, `storicizzazione-tabelle`, e il piano
`sviluppo-multi-face-da-completare` §2.1/§2.9 (casella barrata). ⚠️ Le pagine
auto-gen `tabelle/_legacy_…` spariscono al prossimo giro di generazione.

### 10.5 Che cosa resta

| | Cosa | Di chi |
| --- | --- | --- |
| ✅ | Apply dei tre changeSet (12-09 11:30) e pgTAP senza regressioni — `anagrafiche/test-legacy-risorse-umane-auth-user-ritirata-v1` (9), `dbops/test-audit-sources-seed` (8), `dbops/test-storico-scope-policy-v1` (32), `storico/test-storico-scope-congelato-v1` (23); `vw_storico_scope_da_dichiarare` a zero | fatto (Tid) |
| ⏳ | Commit: tre YAML, due CSV, due pgTAP, manuali e guide di §10.4, questo brief | **Tid** |
| 🟠 | Resta il debito di **nome** del §9.3: `storico.comune_trasformazioni` e `storico.stradario_trasformazioni` sono registri, non shadow | decisione Tid |
| ✅ | **Il `-10` aveva lasciato un guard stantio sulla MADRE** — chiuso: `-11` `EXECUTED` il 12-09 alle 11:54, baseline pgTAP verde (Tid). (trovato il 12-09 pomeriggio): `trg_risorse_umane_a10_legacy_risorse_umane_auth_user_blo_feea48` su `anagrafiche.risorse_umane` nomina la figlia droppata e solleva `E_ATTIVO_BLOCK_FKCOL_NOT_FOUND` a ogni disattivazione di una risorsa umana (provato in ROLLBACK). Rimedio: `00_schema/anagrafiche/20260912-11` (`DROP TRIGGER IF EXISTS`, §11.5) + test 10 di `test-legacy-risorse-umane-auth-user-ritirata-v1`. ⚠️ Il censimento del §10.1 guardava `pg_proc`, viste, pgTAP e BE — non `pg_trigger` dei **padri**: un trigger sulla madre è un lettore della figlia. Dettaglio in [analisi-software-per-dati-morti.md](../work-in-progress/analisi-software-per-dati-morti.md) §2.1 | fatto |
| 🟡 | Lo **strato 2** della segnalazione BE — la vista `anagrafiche.risorse_umane_auth_user`, il nome vecchio con lettori vivi (4 funzioni, 3 punti BE + model, 9 pgTAP) — **non è di questo brief**: decisione e censimento in [analisi-software-per-dati-morti.md](../work-in-progress/analisi-software-per-dati-morti.md) §2.1 («via il nome», cantiere suo, BE prima). Tid ha delegato la decisione il 12-09 | cantiere futuro, BE → DB |

---

*Analisi 2026-09-11 — letture di **struttura** sul database `zeroerp`
(`pg_proc`, `pg_trigger`, `pg_class.relrowsecurity`, colonne delle tabelle di
storico). ⛔ Nessun conteggio di righe è usato come argomento. Stato finale
letto il 2026-09-12 dal `databasechangelog` e dal catalogo; coda §10 scritta il
12-09 pomeriggio.*
