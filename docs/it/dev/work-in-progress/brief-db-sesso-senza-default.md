# Brief DB — Il sesso di una persona fisica non si inventa

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-09; **rivisto** dalla sessione DB
> (`dev/db-tid`) lo stesso giorno, dopo l'analisi critica e le decisioni di Tid (§3).
> **A chi:** team DB, e team BE/FE per il §6.
> **Origine:** revisione del codice BE non committato del 2026-10-09; decisioni di Tid.
> **Stato:** ✅ **lato DB chiuso** (2026-10-09): changeSet `20261009-19` … `-31` **applicati** da
> Tid, corsa pgTAP **senza regressioni** (§7.3). **Da fare:** il §6 (team BE/FE) — fino ad
> allora il backend non crea persone fisiche (§7.4).

## 1. La regola (decisione di Tid, 2026-10-09)

Il sesso di una persona fisica lo **sceglie qualcuno che lo vede**. Il form a video può
**proporre** un valore, ma la proposta deve essere visibile; un sesso che nessuno ha visto non
si scrive. Se il dato serve e manca, la risposta è un **errore**, non un valore di comodo.

Il vocabolario ha tre valori, e `NULL` ne è un quarto con un significato suo:

| Valore | Significa | Chi lo scrive |
| --- | --- | --- |
| `M`, `F` | il sesso della persona | chi lo vede |
| `X` | **serve, ma non si può stabilire**: dati storici, CF esteri o non riconoscibili | chi lo vede, **esplicitamente** |
| `NULL` | **non serve** per questo soggetto | — |

⛔ `X` non è il nuovo default: una chiamata senza sesso resta un errore dove il sesso serve, e
nessuna funzione o script scrive `COALESCE(…, 'X')`. Un import che non conosce il sesso **passa**
`X`: è la risposta onesta al posto dell'`M` di oggi.

## 2. Che cosa dice oggi il DB (contratto, dalla doc auto-generata, 2026-10-09)

| Oggetto | Oggi | Effetto |
| --- | --- | --- |
| `anagrafiche.soggetti.sesso` | `character(1)`, nullable, **`DEFAULT 'M'`**, **nessun CHECK** | ogni `INSERT` che non nomina il sesso scrive un uomo; qualunque carattere è ammesso |
| `anagrafiche.fn_crea_soggetto_pf` | `p_sesso DEFAULT NULL`, poi `COALESCE(p_sesso, 'M')`; dettaglio **`PR` cablato**; **nessun `p_partita_iva`** | senza sesso crea un uomo; non sa creare una ditta individuale |
| `anagrafiche.fn_crea_operatore_v2` | **`p_sesso DEFAULT 'M'` in firma**, passato a `fn_crea_soggetto_pf` nel flusso A | un **secondo** default, indipendente dal `COALESCE`: toglierne uno solo non chiude niente |
| `anagrafiche.fn_crea_soggetto_pg` | non nomina `sesso` nell'`INSERT`; accetta **qualunque** dettaglio, anche `PR` e `DI` | ogni PG/ENC nasce `'M'` dal default di colonna; una PF può nascere senza nome, cognome e sesso |
| `dbops.fn_pgtap_crea_soggetto_pg` | scrive `sesso = 'S'` su una PG | valore fuori vocabolario |
| `dbops.fn_pgtap_crea_operatore_umano` | chiama `fn_crea_operatore_v2` senza sesso | eredita il default della firma |
| manual di `soggetti` | documenta un CHECK `M/F/S/X` **che non esiste** | doc che descrive un modello assente |
| manual di `fn_crea_soggetto_pf` | `p_sesso` non obbligatorio, default `'M'` | idem |

⛔ **La ditta individuale (DI) oggi non nasce mai come DI.** Il BE, per ogni natura PF, chiama
`fn_crea_soggetto_pf` (`SoggettiService.create_soggetto` → `_create_pf`), che scrive `PR` e
non riceve la partita IVA: chi sceglie «Ditta individuale» nel form ottiene un **privato**, e la
P.IVA va persa senza errore (un PR senza P.IVA è valido).

> **Che cos'è una DI.** Una sola persona con un'attività in proprio (l'idraulico, il negoziante
> con la P.IVA intestata a sé). Per la legge è una **persona fisica** con partita IVA, non una
> società: per questo sta sotto la natura PF, accanto al privato PR.

## 3. Le decisioni (Tid, 2026-10-09)

| # | Decisione |
| --- | --- |
| D1 | **Valori ammessi** `M`, `F`, `X`, o `NULL`. Un CHECK di riga: `sesso IS NULL OR sesso IN ('M','F','X')`. `S` esce dal vocabolario. |
| D2 | **Quando serve lo decide il dettaglio della natura**, in `config` e non nel codice: una colonna `sesso_policy` su `config.tipi_soggetto_dettaglio`, con tre stati, e un guard che la legge. |
| D3 | **Chi non è PF ha `sesso = NULL`**, imposto dal guard. I dati sporchi si **puliscono** (§4.4): sono dati di test, ma un vincolo nuovo non deve trovare righe che lo violano. |
| D4 | **La DI si corregge in questo brief**, niente brief a parte. Il dettaglio passato a `fn_crea_soggetto_pf` è **obbligatorio**, senza `DEFAULT` che riproduca il `PR` di prima (Tid, 2026-10-09: la natura non si inventa, come il sesso; prevale sulla regola generale «parametro nuovo in coda con default che riproduce il comportamento di prima»). Per la DI il sesso è **facoltativo**: si scrive o resta `NULL` (preferenza di Tid: `NULL`). Il motivo sul modello: il sesso serve quando il sistema tratta il soggetto **come persona** (operatore, risorsa umana, titolo di cortesia); una DI entra **come attività**, e nessun documento ne usa il sesso. Pretenderlo spingerebbe a scriverne uno a caso, cioè il difetto del §1. |
| D5 | **La coerenza CF ↔ sesso resta fuori**, per ora. (Il BE ha già `_valida_cf_congruenza`: se si riprende, si parte da lì.) |

La matrice che ne segue:

| Dettaglio | Natura | `sesso_policy` | `NULL` | `M`/`F`/`X` |
| --- | --- | --- | --- | --- |
| PR, privato | PF | `REQUIRED` | ⛔ rifiuto | ✅ |
| DI, ditta individuale | PF | `OPTIONAL` | ✅ | ✅ |
| SP, SC | PG | `NONE` | ✅ | ⛔ rifiuto |
| ENC | ENC | `NONE` | ✅ | ⛔ rifiuto |

## 4. Che cosa si chiede al team DB

### 4.1 Struttura

1. `config.tipi_soggetto_dettaglio.sesso_policy`, `NOT NULL`, valorizzata dal CSV di `80_data`
   (una tabella, un CSV) secondo la matrice del §3.
   **Il tipo (decisione di Tid, 2026-10-09, opzione B):** `config.dati_societari_policy_enum` ha già i
   valori `NONE`/`OPTIONAL`/`REQUIRED`, ma il nome parla dei dati societari, e il concetto
   («quanto è richiesto un dato, per natura») compare ora per la seconda volta. Si **estrae**
   un tipo generico (proposta di nome: `config.presenza_policy_enum`), e nello **stesso giro**
   (regola del 2):
   * `sesso_policy` nasce con il tipo nuovo;
   * `dati_societari_policy` si converte al tipo nuovo (stessi valori, i dati non cambiano);
   * si riallineano i lettori del vecchio tipo: il CHECK
     `chk_tipi_soggetto_dettaglio_piva_vs_policy`, le variabili dichiarate con il vecchio tipo
     in `trgfn_dati_societari_guard_tipo_soggetto` e
     `trgfn_soggetti_guard_dati_societari_required`, e la lettura della policy in
     `fn_crea_soggetto_pg` (censimento del 2026-10-09 dalla doc auto-generata, da rifare
     al momento dello sviluppo, anche sui pgTAP);
   * il vecchio tipo si **cancella**.
2. `anagrafiche.soggetti.sesso`: `DROP DEFAULT` e il CHECK di riga del D1.
3. Un guard `BEFORE INSERT OR UPDATE OF sesso, tipo_soggetto_dettaglio_id` su
   `anagrafiche.soggetti`, sullo stampo di `trgfn_soggetti_guard_cf_piva_obbligatori` (legge
   la policy dal dettaglio):
   * `REQUIRED` e `sesso IS NULL` → rifiuto;
   * `NONE` e `sesso IS NOT NULL` → rifiuto;
   * il ramo `UPDATE OF … tipo_soggetto_dettaglio_id` copre il cambio di natura (una PG che
     diventa PR deve portare il sesso; un PR che diventa PG deve lasciarlo).
   Due codici nuovi di classe `DATO_ERRATO`, `E_SESSO_OBBLIGATORIO` ed
   `E_SESSO_NON_AMMESSO` (ok Tid, 2026-10-09), più `E_SOGGETTO_CREAZIONE_NATURA_ERRATA`
   (classe `TECNICO`, §4.2: la funzione sbagliata la sceglie un chiamante rotto), registrati nei due registri, con `'campo','sesso'` nel contesto,
   così il form accende il campo. Il messaggio nomina il **dato** («Il sesso è obbligatorio
   per un privato»), non il parametro.
   ⚠️ Limite noto, ereditato dal guard su CF e P.IVA: con `tipo_soggetto_dettaglio_id` nullo
   il guard non può decidere e tace.

### 4.2 Funzioni

1. `fn_crea_soggetto_pf`:
   * togliere il `COALESCE(p_sesso, 'M')`: il sesso passa così com'è, e lo giudica il guard.
     **Nessun controllo sul sesso nel corpo**: la regola ha una sede sola;
   * in coda alla firma, `p_tipo_soggetto_dettaglio_id` (**obbligatorio**, guard nel corpo come
     gli altri) e `p_partita_iva`; rifiuto se il dettaglio non è di natura PF. Al posto del `PR`
     cablato si usa il dettaglio ricevuto; l'obbligo della P.IVA per la DI lo fa già
     `trgfn_soggetti_guard_cf_piva_obbligatori`;
   * la firma cambia: la vecchia va **eliminata** (altrimenti resta un overload con il `PR`
     cablato) e i chiamanti si censiscono (§4.3).
2. `fn_crea_operatore_v2`: `p_sesso DEFAULT NULL` in firma (con `CREATE OR REPLACE` il valore
   di default si può cambiare, non togliere); nel flusso A passa `PR` come dettaglio. Il rifiuto
   del sesso mancante arriva dal guard dentro `fn_crea_soggetto_pf`, cioè **prima** dello step
   2-bis del consenso, come vuole il commento della funzione.
3. `fn_crea_soggetto_pg`: rifiuta i dettagli di natura **PF**. Senza questo, la DI avrebbe due
   porte, e una senza nome, cognome e sesso.
4. I `COMMENT ON FUNCTION` dicono la regola nuova.

### 4.3 pgTAP e builder

Chiamano `fn_crea_soggetto_pf` o `fn_crea_operatore_v2` (censimento del 2026-10-09, da
rifare al momento dello sviluppo):

* `anagrafiche/`: `test-fn-crea-soggetto-pf`, `test-fn-crea-operatore`,
  `test-crea-operatore-riusa-credenziale-v1`, `test-identita-digitali-guard-coerenza`,
  `test-risorse-umane`, `test-risorse-umane-guard-identita-attiva-v1`,
  `test-fn-crea-risorsa-umana`, `test-fn-crea-risorsa-umana-gia-presente-v1`,
  `test-fn-crea-indirizzo-soggetto`, `test-fn-update-cliente-v1`, `test-emittenti-fiscali`;
* `script/`: `test-fn-guard-soggetto-pf-pura`, `test-fn-get-credenziale-per-email-v1`,
  `test-fn-check-operatore-invitabile`, `test-fn-scope-ef-whitelist`,
  `test-fn-get-soggetto-dati-and-user-profile`, `test-fn-is-super-admin`;
* `rls/`: `test-rls-fatture-satelliti-functional`, `test-rls-viste-fattura-invarianza`,
  `test-rls-preventivi-ef-whitelist-write`;
* `dbops/`: `test-automazione-attivo-eccezioni-v1`;
* builder: `dbops.fn_pgtap_crea_operatore_umano` (sesso da passare),
  `dbops.fn_pgtap_crea_soggetto_pg` (`'S'` → `NULL`).

⚠️ Oltre ai chiamanti delle funzioni, il guard tocca ogni `INSERT INTO anagrafiche.soggetti`
**diretto** di pgTAP e builder: un PR senza sesso, o una PG con un sesso, viene rifiutato.
Vanno censiti riga per riga (grep pgTAP prima di stringere un guard).

Casi nuovi da provare, ognuno **costruito** nel test:

* PR senza sesso → rifiuto; PR con `X` → accettato;
* DI senza sesso → accettato; DI con P.IVA da `fn_crea_soggetto_pf` → nasce **DI**, non PR;
* PG/ENC con un sesso → rifiuto;
* `'S'` (o un altro carattere fuori vocabolario) → rifiuto dal CHECK;
* `UPDATE` di natura da PG a PR senza sesso → rifiuto;
* `fn_crea_soggetto_pg` con un dettaglio PF → rifiuto;
* `fn_crea_operatore_v2` flusso A senza sesso → rifiuto, prima del consenso al riuso;
* la colonna `sesso_policy` coerente con la natura base (un PG con `REQUIRED` è un errore di
  configurazione: va valutato un CHECK o un presidio sul seed).

### 4.4 Pulizia dei dati

Un changeSet **idempotente**, prima del CHECK e del guard, che riporta le righe esistenti nel
modello **senza inventare valori**: diventa `NULL` solo ciò che il modello vieta.

* un valore fuori vocabolario (oggi `'S'`), su qualunque soggetto → `NULL`;
* un sesso su chi non è PF (PG, ENC; oggi `'M'` dal default) → `NULL`.

⛔ Un PR senza sesso **non** diventa `X` (rettifica del 2026-10-09 rispetto alla prima stesura):
sarebbe un valore scritto da un migrate, cioè da nessuno che l'ha visto. Il guard non giudica le
righe esistenti: lo fermerà quando qualcuno toccherà sesso o natura di quel soggetto, cioè quando
una persona lo vede. La natura si legge dalla natura **base** (`tipo_soggetto_id`): su dbdev
`sesso_policy` prende i suoi valori solo dal CSV, dopo.

Fotografa solo le righe di quel momento, ed è sufficiente: dopo il guard non ne nascono più di
sporche. Su un database ricostruito da zero non trova niente da fare.

### 4.5 Documentazione

* manual di `soggetti`: la sezione «Check su `sesso`» si riscrive (`M`/`F`/`X`, `NULL`,
  `sesso_policy`); via `S`.
* manual di `fn_crea_soggetto_pf` (dettaglio, P.IVA, sesso senza default), di
  `fn_crea_soggetto_pg` (rifiuta le PF) e di `tipi_soggetto_dettaglio` (`sesso_policy`, e
  `dati_societari_policy` sul tipo nuovo); ogni manual che nomina
  `dati_societari_policy_enum` passa al nome nuovo.
* guida [Soggetti e ruoli anagrafici](../../guide/soggetti-e-ruoli-anagrafici.md), §«Natura
  giuridica»: la tabella degli obblighi prende la colonna **Sesso**, e una riga spiega `X`
  contro `NULL`.

## 5. Lato BE/FE fatto il 2026-10-09 (prima della revisione)

* `SoggettiService._create_pf`: il sesso è obbligatorio (`E_ANAG_VALIDAZIONE`); tolto il
  `"M"` di ripiego. `SoggettiRepository.crea_soggetto_pf` lo vuole senza default.
* `AmmSoftwareService.create_operatore`: col soggetto nuovo (flusso A) il sesso è obbligatorio
  (`M`/`F`, `E_AMM_VALIDAZIONE` col campo); col soggetto esistente (flusso B) passa `NULL`.
  Tolta la costante `DEFAULT_SESSO`.
* Eliminato `AnagraficheCoreRepository` (un secondo wrapper di `fn_crea_soggetto_pf`, usato
  solo dai test, con `"IT"`/`"M"` cablati).
* Frontend: `SoggettoForm.vue` propone «M» nella select, a video; l'etichetta porta l'asterisco.

## 6. Che cosa si chiede al team BE/FE, dopo l'applicazione del §4

1. **Ritirare i controlli sul sesso** in `_create_pf` e in `create_operatore`: la regola sta
   nel guard, e il campo si accende dal canale `COLUMN`. In più, per la DI quel controllo
   sarebbe **sbagliato** (D4); e `create_operatore` accetta solo `M`/`F`, mentre `X` è ammesso.
2. `_create_pf` passa a `fn_crea_soggetto_pf` il **dettaglio scelto** e la **partita IVA**:
   è la correzione del difetto «la DI nasce PR» (§2).
3. Il form legge `sesso_policy` dal dettaglio scelto: asterisco solo con `REQUIRED`, campo
   vuoto ammesso con `OPTIONAL`, campo nascosto con `NONE`; la select offre anche `X`
   («non determinabile»). Con `OPTIONAL` il form **non** propone «M»: per una DI il valore
   onesto di partenza è il vuoto.

⚠️ Finché il §4 non è applicato, il default resta vivo per chi chiama le funzioni DB senza
passare dal backend (processi batch, script, builder di test), e la DI continua a nascere PR.

## 7. Stato del lavoro DB (2026-10-09)

### 7.1 ChangeSet

Numerati in successione a quelli del giorno (`-19` … `-31`); l'ordine è quello dell'autogen.

| # | Cartella | Cosa |
| --- | --- | --- |
| `-19` | `00_schema/config` | `config.presenza_policy_enum`; `dati_societari_policy` convertita (CHECK `piva_vs_policy` e default rimessi identici); colonna `sesso_policy NOT NULL DEFAULT 'NONE'` |
| `-20` | `20_code/anagrafiche` | `trgfn_dati_societari_guard_tipo_soggetto`: la policy segue la colonna (`%TYPE`), non il tipo |
| `-21` | `20_code/anagrafiche` | `trgfn_soggetti_guard_dati_societari_required`: idem |
| `-22` | `00_schema/config` | `DROP TYPE config.dati_societari_policy_enum` (preCondition: nessuna colonna e nessun corpo lo usa) |
| `-23` | `00_schema/anagrafiche` | pulizia (§4.4) |
| `-24` | `00_schema/anagrafiche` | `soggetti.sesso`: `DROP DEFAULT`, CHECK `chk_soggetti_sesso`, COMMENT |
| `-25` | `20_code/anagrafiche` | guard `trgfn_soggetti_guard_sesso_policy` + `trg_soggetti_a10_guard_sesso_policy_ins_upd` |
| `-26` | `20_code/anagrafiche` | `fn_crea_soggetto_pf`: dettaglio (obbligatorio) e P.IVA in coda; via `PR` cablato e `COALESCE(p_sesso,'M')`; DROP della firma vecchia |
| `-27` | `20_code/anagrafiche` | `fn_crea_operatore_v2`: `p_sesso DEFAULT NULL`; flusso A con natura `PR` esplicita |
| `-28` | `20_code/anagrafiche` | `fn_crea_soggetto_pg`: rifiuta una natura PF |
| `-29` | `20_code/dbops` | builder `fn_pgtap_crea_soggetto_pg`: sesso `NULL` invece di `'S'` |
| `-30` | `20_code/dbops` | builder `fn_pgtap_crea_operatore_umano`: `p_sesso := 'M'` esplicito |
| `-31` | `90_end` | CHECK `chk_tipi_soggetto_dettaglio_sesso_policy_natura`: solo una PF ha una policy diversa da `NONE` (dopo il mirror del CSV) |

`80_data`: colonna `sesso_policy` in `tipi_soggetto_dettaglio.csv` e nel suo mirror
`20250717-12`; tre righe in `codici_errore.csv` e `messaggi_errore.csv` (id 1229–1231).

Ogni funzione riscritta porta `%TYPE` in firma, `RETURNS`/`RETURNS TABLE`, `DECLARE` e `COMMENT`
dove una colonna esiste con lo stesso tipo (identità della firma invariata: una sola funzione per
nome, verificato); i tipi rimasti espliciti dicono perché. `SECURITY INVOKER` esplicito.

### 7.2 pgTAP

* **Nuovo:** `anagrafiche/test-soggetti-sesso-policy-v1.sql` (20 asserzioni): struttura dal
  catalogo, società, privato (anche il canale `COLUMN` = `sesso`), ditta individuale (nasce DI con
  la P.IVA), le porte delle due funzioni, l'operatore, il soggetto senza natura.
* **Adeguati** (chiamate e `INSERT` diretti): `test-fn-crea-soggetto-pf`, `test-fn-crea-operatore`,
  `test-crea-operatore-riusa-credenziale-v1`, `test-fn-crea-indirizzo-soggetto`,
  `test-fn-crea-risorsa-umana`, `test-risorse-umane`, `test-identita-digitali-guard-coerenza`,
  `test-dati-societari-policy`, `test-soggetti-guard-cf-piva-obbligatori`,
  `test-soggetti-indirizzi-required`, `test-soggetti-ruoli-guard-natura-ammessa`,
  `test-soggetti-ruoli-indirizzi-required` (la natura ora per nome, non «il primo id»),
  `create-soggetto-gestori`, `create-soggetto-bank-branches` (anagrafiche);
  `test-fn-guard-soggetto-pf-pura`, `test-fn-check-operatore-invitabile`,
  `test-fn-get-credenziale-per-email-v1` (script); `test-automazione-attivo-eccezioni-v1` (dbops).
* Gli altri file che nominano le funzioni lo fanno nei commenti, nel flusso B o passano già il
  sesso: invariati.

### 7.3 La prova (2026-10-09), e cosa non copre

Su `zeroerp_ci`, come `zeroerp`, **SQL estratto dagli YAML** (preCondition comprese) in
`BEGIN … ROLLBACK`, vincoli differiti come Liquibase, log via dblink spento; `80_data` simulato
(policy dal CSV, tre codici). Nessuna traccia lasciata (definizioni confrontate prima/dopo).

| Prova | Esito |
| --- | --- |
| i 13 changeSet in ordine di numero | passano; la preCondition del `-22` ha rifiutato un ordine sbagliato |
| 16 casi costruiti (rifiuti, DI, porte, CHECK) | 16/16 |
| `plpgsql_check` sulle 7 funzioni | 0 errori |
| identità delle firme | una funzione per nome; `p_sesso DEFAULT NULL` su `fn_crea_operatore_v2` |
| pulizia `-23` sulle righe **vere di dbdev** (come `zeroerp_app`, in `ROLLBACK`) | 164 righe a `NULL`, guard differiti superati; restano `M`, `F`, `NULL` |
| pgTAP nuovo | 20/20; **mutazione** (guard tolto, default `'M'` rimesso): 7 rossi |
| pgTAP adeguati, prima/dopo sugli stessi file | stessi ok in tutti; `create-soggetto-gestori` 2 rossi e `test-identita-digitali-guard-coerenza` 1 rosso **identici prima e dopo** (dati di fixture assenti sullo scratch) |
| guardrail statici (runOnChange, preCondition/seed, DDL su trigger, GRANT batch, v1, letterali, timestamp, preambolo pgTAP) | verdi |

⚠️ **Non coperto:** i pgTAP girati **da owner** (la RLS non c'è) e su `zeroerp_ci`, non su
dbdev; il loader Liquibase vero del CSV (simulato con `UPDATE`); i presidi trasversali che
contano su tutto il DB (`test-riferimenti-morti-v1`, `test-catalogo-messaggi-errore-completo`).
L'apply e la corsa del runner sono di Tid.

✅ **Apply e corsa del runner (Tid, 2026-10-09):** migrazione applicata, pgTAP senza
regressioni. Chiude i punti «non coperti» qui sopra: RLS (runner come applicazione), dbdev, loader
vero del CSV e presidi trasversali.

### 7.4 Ricadute fuori dal perimetro DB

* ⚠️ **Dopo l'apply il backend non crea più persone fisiche** finché il §6 non è fatto:
  `SoggettiRepository.crea_soggetto_pf` non passa il dettaglio, e la funzione lo pretende
  (`E_ADMIN_VALIDAZIONE`, «Tipo soggetto obbligatorio»). È la conseguenza voluta di D4.
* `apps/core/services/error_policies_generated.py` va rigenerato per i tre codici nuovi.
* Documentazione aggiornata nello stesso giro: manual di `soggetti`, `fn_crea_soggetto_pf`,
  `fn_crea_soggetto_pg`, `tipi_soggetto_dettaglio`; guida «Soggetti e ruoli», tabella degli
  obblighi con la colonna Sesso. ⚠️ Nella stessa tabella la guida diceva dati societari
  «vietati» per la DI e «obbligatori» per l'ENC; il CSV di catalogo dice `OPTIONAL` per
  entrambe: corretta la guida sul CSV.

