# Brief DB — Una veste è utilizzabile se è accesa **e** nelle sue date: una regola, a DB

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-06. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§6), che **attende** la consegna DB.
> **Origine:** L-6 del
> [piano accessi](piano-be-fe-accessi-credenziale-e-vesti.md) §4.4 (A-7 dell'analisi
> accessi). Il piano diceva «si estrae un frammento comune» lato Python e «il lotto
> decide se la regola comune è quella di `fn_get_user_profile`». Facendo il lotto è
> emerso che la regola **c'è già a DB**, scritta in più sedi e non uguale, e che il
> Python ne ha una quarta. Un frammento Python sarebbe stato la quinta.
> **Stato (2026-10-07):** ✅ D-1…D-4 **decise da Tid**, rilette sulla premessa
> «niente produzione, solo sviluppo» (§3-bis); D-2 riaperta e chiusa sulla strada
> **(a)**. ✅ **Giro 1 applicato su dbdev** (§7, `20261007-01 → -15`, 12:09).
> ✅ §7.5 deciso da Tid: l'ultimo amministratore non scade, il batch accende.
> ✅ **Giro 2 applicato** (§8, `-16 → -22`; Tid, 2026-10-07): pgTAP senza regressioni.
> ✅ **Giri 1-2 DB chiusi.** ✅ **BE/FE fatto** (§9, 2026-10-07): test Django verdi
> sul DB vero. ✅ **Giro 3 DB applicato** (§10.4, `20261007-27`; Tid, 2026-10-07): la
> capability della data di fine nel dettaglio operatore, pgTAP verdi. ⏳ **BE/FE** (§10.3):
> spegne il campo «Valido al» col motivo; poi l'archiviazione.
> **Da leggere per primo:** §3-bis (le decisioni), §8 (il giro 2), §9 (il BE/FE), §10.4.

## 1. Il difetto, sul modello

`anagrafiche.identita_digitali` ha una finestra di validità (`valido_dal NOT NULL
DEFAULT CURRENT_DATE`, `valido_al` nullable, `chk_identita_digitali_date`). Il
modello dice quindi che una veste può essere **accesa ma fuori dalle sue date**:
non ancora valida, o scaduta.

Chi decide se una veste «vale» oggi dà quattro risposte diverse:

| Sede | Cosa guarda | Finestra |
| --- | --- | --- |
| **BE**, cinque punti (§5): login, ogni richiesta (`set_jwt_gucs`), refresh, secondo passo del secondo fattore, cambio password | solo `attivo` | ⛔ no |
| `script.fn_has_identita_attiva` → `fn_get_user_permissions_map`, `fn_get_permessi_effettivi_azioni` | `attivo` + finestra | ✅ |
| `script.fn_is_super_admin_account`, `fn_get_profili_accesso_applicabili` | `attivo` + finestra, **ricopiata** inline | ✅ |
| `anagrafiche.fn_sync_auth_user_is_active` (e il batch `fn_sync_auth_user_expired`) | `attivo` + finestra + **soggetto attivo** | ✅ (+1 condizione) |
| `script.fn_get_user_profile` (`/me/`, assistente AI) | `attivo` + finestra della veste **e** del rapporto (risorsa umana), coi codici `E_UTENTE_NON_ATTIVO` / `E_UTENTE_SCADUTO` | ✅ (+ rapporto) |
| `script.fn_scope_cliente_ownership`, `fn_scope_fornitore_ownership`, `fn_scope_ba_ownership[_via_fattura]`, `fn_scope_identita_processo` | solo `attivo` | ⛔ no |

Conseguenze, costruibili oggi senza aspettare un caso nei dati:

* **una veste scaduta ieri entra**: il login risponde 200 e ogni richiesta
  popola le GUC con la sua identità. A valle, però, la mappa dei permessi
  (`fn_has_identita_attiva`) la tratta come assente e `/me/` risponde
  `E_UTENTE_SCADUTO`. Un utente entra in un'applicazione che poi gli nega tutto,
  in modi diversi a seconda della pagina;
* per un **cliente portale o shop** è peggio: le funzioni di scope guardano solo
  `attivo`, quindi la veste scaduta **vede i suoi dati**;
* una veste con `valido_dal` **futuro** entra già oggi: il batch notturno guarda
  solo `valido_al` scaduto, e solo a livello credenziale (`is_active`), cioè
  quando **tutte** le vesti sono scadute. Con una veste scaduta e un'altra valida,
  la scaduta continua a entrare.

## 2. Il secondo difetto: per l'operatore le date sono due

Trovato verificando chi scrive le date (codice letto il 2026-10-06):

* alla creazione `anagrafiche.fn_crea_operatore_v2` passa **la stessa** finestra
  (`p_valido_dal`, `p_valido_al`) alla veste e alla risorsa umana;
* dopo, il drawer operatore modifica **solo** `risorse_umane.valido_al`
  (`AmmSoftwareRepository.update_operatore`), e «Disabilita» scrive
  `risorse_umane.valido_al = CURRENT_DATE`. La veste resta con le date della creazione.

⇒ Le due finestre divergono dal primo salvataggio. La data «Valido al» che
l'amministratore imposta nel drawer **non chiude l'accesso**: oggi perché nessuno
guarda le date al login, e domani neanche, se il controllo guardasse solo la
finestra della veste. L'unica sede che le guarda entrambe è
`fn_get_user_profile`, cioè `/me/`, a sessione già aperta.

## 3. Le decisioni proposte (⚠️ superate dalle decisioni di Tid: §3-bis)

| # | Domanda | Proposta |
| --- | --- | --- |
| D-1 | Dove sta la regola «veste utilizzabile»? | **A DB, in un building block per veste** (§4.1). Le copie DB della §1 la leggono da lì (regola del 2, ritirate nello stesso giro), e il BE la chiama nei suoi cinque punti invece di riscriverla. Il Python **non** calcola date: «oggi» è `CURRENT_DATE` del DB, come per tutte le altre sedi. |
| D-2 | Per una veste **OPERATORE**, quale finestra vale: quella della veste, quella del rapporto, o tutte e due? | **Tutte e due**: l'operatore entra se la veste è accesa e nelle sue date **e** il rapporto (risorsa umana della veste) è attivo e nelle sue date. È già la regola di `fn_get_user_profile`, che diventa una lettura del BB e non una seconda versione. Così la data del drawer chiude l'accesso senza riscrivere la veste a ogni salvataggio. L'alternativa (il drawer scrive anche la finestra della veste) tiene due copie dello stesso dato, una per tabella: la divergenza di §2 tornerebbe al primo scrittore che ne dimentica una. |
| D-3 | La condizione «soggetto attivo» di `fn_sync_auth_user_is_active`? | **Entra nel BB**, così nessuna sede perde una condizione che oggi applica. Se il team DB verifica dal contratto che è implicata dalle altre (oggi un soggetto non si spegne con soggetti_ruoli accesi, ma un soggetto_ruolo si spegne con una veste accesa: nessun trigger lo impedisce), la toglie dichiarandolo. |
| D-4 | Al login, una veste fuori dalle sue date che codice dà? | **Lo stesso di una veste spenta**: `E_VESTE_NON_ATTIVA` al login, `E_IDENTITA_NON_ATTIVA` (401) a richiesta, refresh rifiutato come una veste spenta. Nessun codice nuovo. Il login oggi non distingue nemmeno «spenta» da «assente», e la finestra è un'altra forma di «spenta». Se Tid vuole un messaggio che dica la data («il tuo accesso è scaduto il …»), il BB diventa una check con il motivo (§4.1, variante), da decidere ora e non dopo. |

## 3-bis. Le decisioni di Tid (2026-10-07)

Premessa di Tid: **non c'è produzione, solo sviluppo**. Si sceglie la forma
giusta, senza strati di compatibilità: niente funzioni ponte, niente codici tenuti
«per chi li legge ancora», niente bonifiche dei dati (quelli di sviluppo si
sistemano a mano).

| # | Decisione | Cosa cambia rispetto alla proposta |
| --- | --- | --- |
| D-1 | ✅ **A DB, un building block per veste.** Le copie si ritirano nello stesso giro; dove una firma vecchia serve solo a fare da ponte, si toglie invece di tenerla. | Niente. La premessa toglie solo i ponti. |
| D-2 | ✅ **(a): per l'OPERATORE contano veste e rapporto** (Tid, 2026-10-07, dopo la riapertura qui sotto). | Rivede la decisione del 12-09 su un punto: il rapporto torna nella regola, in una sede sola (il BB). |
| D-3 | ✅ **«Soggetto attivo» entra nel BB**, senza indagare se le altre condizioni lo implichino già. | Cade la verifica «se il team DB la trova implicata, la toglie»: costa più di quanto vale. |
| D-4 | ✅ **Un solo esito per «spenta» e «fuori date»**: `E_VESTE_NON_ATTIVA` al login, `E_IDENTITA_NON_ATTIVA` a richiesta, refresh rifiutato. Il BB è un `boolean`, non una check col motivo. **`E_UTENTE_SCADUTO` si ritira**, e con lui il gemello `E_UTENTE_NON_ATTIVO` (la data futura): anche `fn_get_user_profile` legge il BB, e un codice per le date la obbligherebbe a tenere la sua copia dei controlli. ⚠️ «Si ritira» = `obsoleto_dal`, non cancellazione: `dbops.error_log` punta a `messaggi_errore`, e le occorrenze storiche devono restare leggibili (guida Messaggi di Errore, «Ritirare un codice, non cancellarlo»). | La variante «check col motivo» cade. Il ritiro dei codici ha una ricaduta BE/FE (§6). |

### D-2 riaperta: contraddice la decisione del 12-09 (✅ chiusa: strada (a))

La proposta di D-2 («per l'operatore valgono **tutte e due** le finestre, veste e
rapporto») rimette la risorsa umana dentro la regola dell'accesso. Il 12-09 Tid
aveva deciso il contrario: *«tutto deve entrare in `identita_digitali`»*
([analisi-software-per-dati-morti](../work-done/analisi-software-per-dati-morti.md)
§2.1, changeSet `20260912-21`). La regola «rapporto scaduto ⇒ accesso spento» doveva
essere **assorbita** dalla `valido_al` della veste.

Quell'assorbimento però non è mai avvenuto nei produttori. Il drawer operatore
continua a scrivere `risorse_umane.valido_al` (`AmmSoftwareRepository.update_operatore`),
e la lista operatori mostra le date del rapporto. Dopo la creazione, nessuno scrive
la finestra della veste. Quindi dal 12-09 la data del drawer **non chiude niente**:
il batch notturno guarda solo la veste, e il login non guarda nessuna data.

Due strade, entrambe senza costi di migrazione (niente produzione):

* **(a) Il BB legge veste + rapporto per l'OPERATORE** (la proposta originaria).
  Il BE non cambia scrittore: la data del drawer chiude l'accesso, «Disabilita» e
  il reinvio continuano a funzionare come oggi. Rivede la decisione del 12-09 su un
  punto solo: la risorsa umana torna nella regola, ma in **una** sede (il BB), non
  nelle copie che il 12-09 aveva tolto.
* **(b) Conta solo la veste** (coerente col 12-09). Il drawer e la lista passano
  alle date della veste, e il rapporto resta un fatto HR che non tocca l'accesso.
  Ricadute BE/FE: `update_operatore`, la lista operatori, e l'attivazione dopo un
  reinvio, che deve riaprire una `valido_al` passata della veste (oggi riapre quella
  del rapporto), altrimenti la veste si riaccende già scaduta.

## 4. Richiesta

### 4.1 Il building block: `script.fn_veste_utilizzabile(p_identita_id bigint) → boolean`

Nome e forma li sceglie il team DB. Il contratto che serve al BE:

* `true` se la veste è utilizzabile **oggi**: `attivo`, `valido_dal <= CURRENT_DATE`,
  `valido_al IS NULL OR valido_al >= CURRENT_DATE` (estremi **compresi**, come in
  tutte le sedi attuali), più D-2 per `OPERATORE` e D-3;
* `false` per un id assente o `NULL` (fail-closed);
* `STABLE`. Possibilmente `LANGUAGE sql`, così da essere inlineabile: la
  chiama `set_jwt_gucs` a **ogni** richiesta autenticata;
* l'appartenenza della veste alla credenziale **resta** al chiamante (il BE filtra
  già `auth_user_id`): il BB risponde sulla veste, non sulla sessione.

Variante, solo se D-4 vuole il motivo: una check che restituisce il motivo
(`SPENTA`, `NON_ANCORA_VALIDA`, `SCADUTA`, `RAPPORTO_CHIUSO`, …; `NULL` = utilizzabile),
sulla forma di `fn_check_credenziale_bloccabile`, e il booleano come lettura di quella.

### 4.2 Le copie da ritirare nello stesso giro

| Sede | Cosa diventa |
| --- | --- |
| `script.fn_has_identita_attiva` | lettura del BB (resta la firma per credenziale + tipo: la usano le funzioni dei permessi) |
| `script.fn_is_super_admin_account`, `fn_get_profili_accesso_applicabili` | il predicato inline diventa il BB |
| `anagrafiche.fn_sync_auth_user_is_active` | `EXISTS` sul BB (D-3) |
| `script.fn_get_user_profile` | i guard sulle date restano dove sono **solo** se D-4 vuole i codici col motivo; altrimenti leggono il BB. Da decidere col §4.1 |
| `script.fn_scope_*` (§1, ultima riga) | **proposta**: anche loro il BB. Oggi ricevono l'identità dalla GUC, che il BE popolerà solo per una veste utilizzabile (§6), quindi non sono la prima linea; ma la regola è la stessa, e chi le chiama fuori dal giro HTTP (job, processi) oggi vede una veste scaduta come valida |

### 4.3 Prove (pgTAP, casi costruiti)

Per ogni caso si costruisce la veste, non si cerca nei dati: accesa e senza fine;
spenta; `valido_dal` domani; `valido_al` ieri; `valido_al` oggi (**utilizzabile**:
l'estremo è compreso); operatore con veste valida e rapporto chiuso ieri (D-2);
operatore con rapporto valido e veste scaduta; soggetto spento (D-3); id assente;
`NULL`. Più una prova che le sedi di §4.2 rispondano come il BB sugli stessi casi
(la divergenza è il difetto che il brief chiude).

## 5. Dove legge il BE, oggi (per il team DB: solo contesto)

| Punto | File | Lettura |
| --- | --- | --- |
| Login | `core/db/auth_repository.py` `find_identita_attiva_for_ruoli` | `attivo = true`, la prima veste fra i tipi della porta |
| Ogni richiesta | `core/api/jwt_audit_authentication.py` `set_jwt_gucs`, CTE `id_row` | `attivo = true` |
| Refresh | `core/api/auth_views.py` `_veste_accesa` | `get_identita_dettaglio(...)["attivo"]` |
| Secondo passo | `core/api/secondo_fattore_token_views.py` | idem |
| Cambio password | `core/api/change_password_view.py` | idem |

## 6. Dopo la consegna — lato BE/FE (attende)

> ⚠️ Riletta il 2026-10-07 dopo le decisioni: la forma DB è quella di §7.1. Il BB è
> `script.fn_veste_utilizzabile(identita_id)`; per il BE contano anche i punti
> aggiunti in fondo a questa sezione (codici ritirati, test Django, doc BE).

* **Una** lettura nel BE: il login aggiunge il BB al `WHERE` (fra le vesti della
  porta prende la prima **utilizzabile**: con una veste scaduta e un'altra valida
  della stessa porta, entra la valida); la CTE di `set_jwt_gucs` lo stesso;
  refresh, secondo passo e cambio password passano da un metodo solo di
  `AuthRepository` (oggi `_veste_accesa` e due copie di `get_identita_dettaglio` +
  `attivo`: regola del 2, si ritirano le copie).
* Il commento di `set_jwt_gucs` («una condizione nuova (L-6, A-7: validità) va in
  tutte e due») si chiude: la condizione sta in un posto.
* Prove sul DB vero (`test_login_credenziale_db`): veste scaduta → login
  `E_VESTE_NON_ATTIVA`; sessione aperta e veste che scade → la richiesta
  successiva è 401 e il refresh è rifiutato; scaduta + un'altra valida della
  stessa porta → entra la valida; operatore col rapporto chiuso dal drawer → non
  entra (D-2).
* FE: nessun cambiamento, se D-4 resta senza codici nuovi.
* Doc: `api_multi_veste_token.md`, guida `risorse-umane-e-accessi`, il piano
  accessi §4.4 (L-6) e §0 (A-7).
* ➕ (2026-10-07, dal lato DB) **I due codici delle date sono ritirati**
  (`E_UTENTE_NON_ATTIVO`, `E_UTENTE_SCADUTO`, `obsoleto_dal = 2026-10-07`):
  nessuna funzione li solleva più. Lato BE/FE restano da riallineare la voce di
  `LoginView.vue` (`E_UTENTE_SCADUTO → auth.account_expired`, e la gemella), i
  ripieghi in `error_messages_fallback.py`, le policy generate (si rigenerano), e
  `docs/it/backend/core/manual/api_user_profile.md` (due righe nominano ancora i
  tre codici: ora il profilo dà solo `E_UTENTE_DISABILITATO` per spenta **o** fuori
  date **o** rapporto chiuso).
* ➕ Il **testo** di `E_UTENTE_DISABILITATO` non cambia («Utente disabilitato: %s»);
  cambia solo la causa nel catalogo. Il ripiego BE resta valido.
* ➕ **Test Django sul DB vero**: censiti in sola lettura, creano a mano solo vesti
  cliente (shop/portale), che il rapporto non lo chiedono; gli operatori nascono
  dalla madre, con la risorsa umana. Nessuno dovrebbe cambiare esito, ma la corsa è
  del BE (D-2 vale anche per loro: un operatore senza rapporto non entra più).

## 7. Consegna DB (2026-10-07)

### 7.1 Il building block

`script.fn_veste_utilizzabile(p_identita_id anagrafiche.identita_digitali.id%TYPE) → boolean`
(`20261007-01`), `LANGUAGE sql BEGIN ATOMIC`, `STABLE`, `INVOKER`. Utilizzabile oggi =
veste accesa e nelle sue date (estremi compresi), soggetto attivo (D-3) e, per
l'**operatore umano** (`OPERATORE` con `tecnica = false`), rapporto attivo e nelle sue
date (D-2). `false` per id assente o `NULL`. Manuale:
`docs/it/dbzero/script/manual/fn_veste_utilizzabile.md`.

⭐ **Trovato scrivendolo: l'identità TECNICA non ha rapporto.** Le identità dei processi
automatici sono `OPERATORE` (la RLS lo pretende) ma `fn_crea_utente_tecnico` non crea una
risorsa umana. Una D-2 letta alla lettera («per l'OPERATORE anche il rapporto») avrebbe
spento tutti i processi. Il BB chiede il rapporto solo all'operatore umano.

⚠️ **Non inlineabile**, contrariamente a quanto chiedeva §4.1: un `EXISTS` è una
sotto-interrogazione, e il planner incorpora solo funzioni senza. Vale anche per le copie
di prima (anche loro `EXISTS`), quindi nessun peggioramento: `set_jwt_gucs` la chiama una
volta per richiesta.

### 7.2 Le copie ritirate (`20261007-02 → -15`)

Quattordici sedi, tutte con `CREATE OR REPLACE` a firma e `RETURNS` invariati (le BEGIN
ATOMIC che ne leggono qualcuna restano valide); corpi presi dal vivo e trasformati con
sostituzioni contate; rollback = corpo vivo di prima.

| # | Sede | Cosa cambia |
| --- | --- | --- |
| -02 | `script.fn_has_identita_attiva` | legge il BB (resta per credenziale + tipo) |
| -03 | `script.fn_is_super_admin_account` | idem |
| -04 | `script.fn_check_ultimo_super_admin_attivo` | idem, nei due blocchi |
| -05 | `script.fn_check_almeno_un_super_admin_attivo` | ⭐ **copia in più rispetto al §4.2**: guardava solo `attivo`, mentre la sorella -04 guardava la finestra. Le due funzioni dell'anti-lockout rispondevano su due regole |
| -06 | `script.fn_get_profili_accesso_applicabili` | tre rami; nel REPARTO cade `ru.attivo` (lo guarda il BB, con le date) |
| -07 | `script.fn_get_setup_status` | ⭐ copia in più: il conteggio degli operatori del banner |
| -08 | `anagrafiche.fn_sync_auth_user_is_active` | `EXISTS` sul BB |
| -09 | `anagrafiche.fn_sync_auth_user_expired` | candidati = credenziali accese con vesti ma nessuna utilizzabile (prima: `valido_al` della veste; con D-2 non avrebbe visto i rapporti scaduti) |
| -10 | `script.fn_get_user_profile` | sei guard e tre codici → un guard, `E_UTENTE_DISABILITATO`; «nessuna risorsa umana» (`E_ADMIN_VALIDAZIONE`) passa prima |
| -11…-14 | `fn_scope_cliente_ownership`, `fn_scope_fornitore_ownership`, `fn_scope_ba_ownership`, `fn_scope_ba_ownership_via_fattura` | `attivo` → BB: una veste cliente scaduta non vede più i suoi dati |
| -15 | `fn_scope_identita_processo` | il livello «identità viva» → BB |

**Lasciate fuori, perché dicono un'altra cosa** (censimento su `pg_proc`: ogni funzione che
legge `identita_digitali` con `attivo` o le date):
`fn_check_operatore_invitabile` (la veste è spenta **per costruzione**: chiede se la sua
finestra permette l'invito, non se vale oggi); `fn_get_uo_id_for_user` (risolve il reparto,
non decide un accesso); le madri e i guard che **scrivono** o proteggono lo stato
(`fn_crea_*`, `trgfn_*_guard_ultimo_super_admin`, `trgfn_risorse_umane_guard_identita_attiva`);
le fixture `dbops.fn_pgtap_*`.

### 7.3 I codici delle date

`E_UTENTE_NON_ATTIVO` ed `E_UTENTE_SCADUTO`: `obsoleto_dal = 2026-10-07` in
`codici_errore.csv`, con la nota del ritiro. Righe e messaggi restano (il diario). La causa
di `E_UTENTE_DISABILITATO` in `messaggi_errore.csv` dice ora «spenta o fuori dalle sue date,
oppure il rapporto non attivo o fuori date»; il testo non cambia. Niente changeSet: i due
CSV hanno già i loro mirror.

### 7.4 Prove (prima dell'apply, su `zeroerp_ci` come owner, in transazione ritirata)

* SQL **estratto** dai quindici YAML (`yaml.safe_load`), `ON_ERROR_STOP`; `plpgsql_check`
  sulle quattro plpgsql toccate: zero errori (solo avvisi di volatilità, che c'erano già:
  10 prima, 5 dopo su `fn_get_user_profile`).
* **pgTAP nuovo** `db/pgtap/script/test-fn-veste-utilizzabile-v1.sql`: **28/28**. Mutazione:
  con il BB ma le sedi vecchie, **9 rossi**, cioè il test vede la divergenza.
  ⚠️ D-3 (soggetto spento) **non ha un caso**: un soggetto con un `soggetto_ruolo` non
  si disattiva (guard generico dell'automazione ATTIVO, figlia senza `attivo`), quindi una
  veste accesa con soggetto spento non si costruisce. Dichiarato nel file.
* **Prima/dopo su 67 pgTAP censiti** (chi chiama le funzioni toccate, chi crea vesti a
  mano, chi nomina i codici): 64 uguali, 3 diversi. Uno solo nell'uuid di un rosso che
  c'era già (`test-identita-digitali-guard-coerenza`, indirizzo mancante). Due erano
  **regressioni vere della fixture**: `test-fn-scope-ef-whitelist` (7, 9) e
  `test-rls-fondi-fattura-source-functional` (3, 6, 8-11) costruivano una veste
  OPERATORE **senza risorsa umana**, stato che la madre non produce mai. Con D-2 non vale
  più. Corrette dando all'operatore il rapporto che la madre gli darebbe: ora verdi prima
  e dopo.
* ⚠️ **Censimento incompleto, trovato dalla corsa di Tid (2026-10-07, dopo l'apply)**:
  altri **sette** `rls/` hanno la stessa fixture (veste OPERATORE a mano, senza rapporto)
  e andavano rossi negli stessi casi in-scope: `commesse-ef-whitelist-write` (1, 4),
  `ddt-ef-whitelist-write`, `fatture-ef-whitelist-functional`, `fatture-satelliti-functional`,
  `ordini-multipolicy`, `preventivi-ef-whitelist-write`, `viste-fattura-invarianza`. Il
  censimento cercava chi **chiama** le funzioni toccate; questi passano dalle **policy**
  RLS, che le chiamano per loro. Corretti allo stesso modo. Censimento rifatto sul segno
  giusto (ogni pgTAP che fa `INSERT INTO anagrafiche.identita_digitali` di una veste
  OPERATORE accesa): sono questi nove, nessun altro.
* ✅ **Sistemazione definitiva (2026-10-07, dopo il verde di Tid sulla toppa).** La toppa
  (un `INSERT` di risorsa umana copiato nei nove file) è ritirata nello stesso giro.
  I nove file ora:
  * prendono l'operatore dalla **madre** con `dbops.fn_pgtap_crea_operatore_umano`
    (persona fisica completa, rapporto, veste accesa come all'invito accettato), invece
    di scrivere a mano `django.auth_user`, soggetto, `soggetto_ruolo` e veste;
  * gli danno l'emittente con la funzione di dominio `script.fn_change_user_emittenti_scope`,
    che sostituisce anche i `DELETE` + override + `INSERT` scritti a mano nei `set_op` di
    satelliti e fondi, e nella whitelist di viste-fattura;
  * dove serviva una veste spenta (fatture-ef `spento`, scope-ef idx 2), la spengono con un
    `UPDATE` dopo l'accensione, il percorso reale.
  ⭐ **Debito §22.4 chiuso in quattro file**: satelliti, preventivi, viste-fattura e
  scope-ef dichiaravano `pgtap-differiti: escluso` solo perché il soggetto fatto a mano
  restava senza indirizzo. Il builder lo consegna completo, quindi l'esenzione cade e
  torna `SET CONSTRAINTS ALL IMMEDIATE` in testa. In commesse, ddt e fondi cade il
  `SET CONSTRAINTS ALL DEFERRED` riaperto per l'operatore: da lì in poi restano
  `IMMEDIATE`. Guardrail del preambolo: verde.
  ⚠️ **Da guardare alla corsa**: con `IMMEDIATE` scattano subito i vincoli differiti che
  prima non scattavano mai (il `ROLLBACK` li saltava), anche sugli `UPDATE` no-op di
  commesse, ddt e preventivi. Un rosso lì è un guard vero che il file non esercitava,
  non una regressione della fixture. ⏳ Rilancio da Tid.
  Resta, fuori da questo cantiere: questi file **cercano** ancora nel DB il documento da
  collaudare (commessa, DDT, ordine, preventivo, fattura con `LIMIT 1`). Su `zeroerp_ci`
  costruito da zero finiscono nel soft-skip. La forma giusta è quella di
  `test-rls-resi-ef-whitelist-write` (mondi costruiti con `fn_pgtap_crea_emittente_operatore`
  e `fn_pgtap_crea_cliente_ba`): è del cantiere «fixture che costruiscono».
  ✅ **Fatto il 2026-10-07**:
  [brief-db-fixture-rls-documenti-costruiti](../work-done/brief-db-fixture-rls-documenti-costruiti.md)
  (tre giri, quattro builder nuovi, sette file che costruiscono il loro documento).
* **Presidi trasversali** prima/dopo (riferimenti morti, catalogo messaggi completo,
  rubinetto primo motivo, codici obsoleti, costanti citate…: 21 file): tutti uguali.
* Guardrail statici del repo: verdi.
* ⚠️ **Correzione di Tid (2026-10-07), prima dell'apply**: i corpi presi dal vivo con
  `pg_get_functiondef` avevano i `%TYPE` sciolti in tipi nudi (firma, `RETURNS TABLE`,
  `DECLARE`, firma del `COMMENT`). Riancorati in tutti e quattordici i changeSet, corpo
  nuovo **e** rollback; dove non c'è una colonna dietro (jsonb composti, conteggi,
  esiti di funzione, `django.auth_user.is_active` che in CI non esiste al `CREATE`) il
  tipo esplicito porta il perché accanto. Provato: nessun overload nuovo (i `%TYPE` si
  risolvono negli stessi tipi), pgTAP ancora 28/28, rollback eseguiti dopo il giro nella
  stessa transazione senza residui.
* Fatto datato (2026-10-07, dbdev, sola lettura): l'operatore che
  `fn_pgtap_set_contesto_operatore` sceglie (id 5) ha il rapporto attivo e senza fine,
  quindi la suite non cambia contesto. È una verifica, non una ragione del disegno.

⚠️ **Non provato prima dell'apply**: la corsa come `zeroerp_app` (il pgTAP nuovo non usa
RLS, quindi non dovrebbe cambiare), la baseline intera, e il passaggio dal driver di
Liquibase: per il `BEGIN ATOMIC` del `-01` il `COMMENT` sta in un secondo `- sql:`, come
vuole pgjdbc.

### 7.5 Punti aperti → ✅ decisi da Tid (2026-10-07), giro 2 (§8)

* ~~**Il tempo non scrive** (l'ultimo SUPER_ADMIN può scadere da solo).~~ ✅ Tid: **almeno
  un SUPER_ADMIN deve restare senza data di fine.** La garanzia si chiede sulla
  scrittura che mette la data, finché qualcuno che non scade c'è ancora. ⚠️ La
  proposta del giro 1 diceva che un guard sulla scrittura «copre solo metà del caso».
  Era vero per un guard che chiede «resta un amministratore attivo», non per uno che
  chiede «resta un amministratore **senza scadenza**»: con questa regola il calendario
  non può più svuotare il sistema.
* ~~**Il giorno in cui una veste diventa valida.**~~ ✅ Tid: **va risolto, la credenziale
  si accende.** Il batch notturno diventa simmetrico. Il nome resta (§8.2): la proposta
  del giro 1 di cambiarlo non serve.

## 8. Giro 2 DB (2026-10-07): l'amministratore che non scade, il batch che accende

> Il giro 1 (`20261007-01 → -15`) è **applicato su dbdev** (12:09, letto da
> `databasechangelog`) e i suoi file non si toccano più: tutto il giro 2 sta in
> changeSet nuovi, `-16 → -22`. ✅ **Applicato** (Tid, 2026-10-07), corsa pgTAP senza
> regressioni (dopo la correzione del presidio 26, §8.5).

### 8.1 L'amministratore che non scade (`-16 → -20`)

| # | Cosa |
| --- | --- |
| -16 | **BB** `script.fn_identita_super_admin_senza_scadenza(identita_id)`: binding e profilo `SUPER_ADMIN` attivi, `OPERATORE` utilizzabile oggi (`fn_veste_utilizzabile`), **nessuna data di fine** né sulla veste né sul rapporto, credenziale non bloccata. Binding, profili e credenziali non hanno date: la scadenza sta solo su veste e rapporto |
| -17 | `fn_check_ultimo_super_admin_attivo`: «l'unico SUPER_ADMIN senza scadenza», il BB chiesto due volte al posto del blocco di filtri ricopiato. La capability `can_disable` del drawer segue: un amministratore che ha già una data di fine si spegne liberamente |
| -18 | `fn_check_almeno_un_super_admin_attivo`: «esiste un SUPER_ADMIN senza scadenza». La ereditano i quattro guard che la chiamano (binding, veste, rapporto, credenziale bloccata) |
| -19 | guard sulla **veste**: oltre allo spegnimento ferma la data di fine messa e l'inizio spostato nel futuro. Trigger rifatto su `UPDATE` + `WHEN` delle tre colonne (linee guida trigger: si reagisce a un cambio di valore). Il variadico dell'errore passa vuoto ed esplicito, come nel guard sorello sulle credenziali |
| -20 | guard **nuovo sul rapporto** (`trgfn_risorse_umane_guard_ultimo_super_admin`): data di fine, inizio nel futuro, spegnimento, spostamento su un altro `soggetto_ruolo` del rapporto di un SUPER_ADMIN |

Si fermano solo le scritture che **riducono** la garanzia. Togliere una data di fine,
riaccendere, riaprire il rapporto (il reinvio dell'invito) passano sempre, anche su un
sistema già scoperto.

Messaggio di `E_PROFILO_ULTIMO_SUPER_ADMIN` riscritto in `messaggi_errore.csv`: «non
resterebbe nessun amministratore (SUPER_ADMIN) attivo e senza data di fine», con causa e
rimedio che nominano le due date.

Fatto datato (2026-10-07, dbdev, sola lettura): i due SUPER_ADMIN di dbdev non hanno date
di fine né sulla veste né sul rapporto, quindi la regola è già soddisfatta e l'apply non
blocca niente. È una verifica, non una ragione.

### 8.2 Il batch che accende (`-21`)

`anagrafiche.fn_sync_auth_user_expired` riallinea `is_active` **nei due versi**. I
candidati sono le credenziali con vesti il cui `is_active` differisce da «esiste una
veste utilizzabile oggi»; decide `fn_sync_auth_user_is_active`, come prima. Il nome resta
(pgAgent, command Django e repository BE lo chiamano); il ritorno conta le credenziali
riallineate, spente o accese.

### 8.3 Ricadute BE (in coda al §6)

* **Repository del batch** (`AnagraficheRepository.sync_auth_user_expired`): ricava già
  le credenziali toccate dalla **differenza simmetrica** prima/dopo, quindi le accese
  entrano da sole. Cambia solo il significato del numero: la variabile `disattivati` (e
  il testo del command `sync_auth_user_active`, se lo dice) diventa «riallineate».
* **Ripiego** di `E_PROFILO_ULTIMO_SUPER_ADMIN` in `error_messages_fallback.py`
  («Impossibile rimuovere l'ultimo super admin attivo.»): da riallineare al catalogo,
  **dopo** l'apply.
* **Drawer operatore**: salvare una data «Valido al» (rapporto) sull'ultimo SUPER_ADMIN
  senza scadenza ora risponde `E_PROFILO_ULTIMO_SUPER_ADMIN` (409, `CONFLITTO_STATO`).
  Il FE lo mostra come gli altri conflitti. Se si vuole il campo spento col motivo
  invece del 409, serve una capability: da chiedere.

### 8.4 Il COMMENT con gli apostrofi doppi (`-22`)

Le note «Rev 2026-10-07» del giro 1 sono state raddoppiate due volte: in dieci `COMMENT`
vivi si legge «e''» al posto di «e'». Il `-22` riscrive solo quei `COMMENT` (provato:
uguali al vivo carattere per carattere, salvo il raddoppio). I `COMMENT` di `-04`, `-05`
e `-09` li riscrivono `-17`, `-18` e `-21`.

### 8.5 Prove (prima dell'apply, su `zeroerp_ci`, in transazione ritirata)

Lo scratch non ha il giro 1, quindi ogni prova mette in testa `-01 → -15` e poi `-16 → -22`,
come un database ricostruito da zero.

* **pgTAP nuovo** `db/pgtap/anagrafiche/test-super-admin-senza-scadenza-v1.sql`:
  **16/16**. Mutazioni: senza i guard `-19`/`-20` vanno rossi i casi 6-9; senza il `-21`
  vanno rossi 14 e 16. Quindi il test vede tutti e due i difetti.
* `test-fn-veste-utilizzabile-v1`: **28/28**. Toccati due punti: il test 23 chiudeva il
  rapporto di un SUPER_ADMIN su un database senza altri amministratori (la CI), cosa che
  il `-20` ora ferma; un secondo amministratore senza scadenza tiene la garanzia. Il
  presidio 26 legge i corpi con `pg_get_function_sqlbody`, perché una `BEGIN ATOMIC` ha
  `prosrc` vuoto, e conta il BB `-16` al posto delle due check, che passano da lui.
* **Prima/dopo su 89 pgTAP**, censiti dalle **fixture e dalle scritture** (chi crea un
  SUPER_ADMIN, chi scrive date o `attivo` su veste e rapporto, chi blocca credenziali o
  tocca i binding, chi chiama le funzioni): **87 uguali**. I due diversi sono i due file
  qui sopra.
* ⚠️ **Rosso in CI dopo l'apply (2026-10-07), corretto**: `test-fn-veste-utilizzabile-v1`
  test 26. Il deparse di `pg_get_function_sqlbody` **omette lo schema quando è nel
  `search_path`**: come app (`script` nel `search_path`) il corpo del `-16` si legge
  `fn_veste_utilizzabile(`, da owner sullo scratch `script.fn_veste_utilizzabile(`. La
  prova pre-apply girava da owner ed era verde. Il presidio ora cerca il nome senza
  schema: 28/28 come app e come owner. Il codice non cambia.
* ⚠️ **Rosso trovato dalla corsa di Tid (2026-10-07, dopo il giro 3), corretto**: la
  riscrittura del messaggio di `E_PROFILO_ULTIMO_SUPER_ADMIN` (§8.1) rompeva quattro
  asserzioni che pinnavano la **frase** vecchia (`throws_like '%zero SUPER_ADMIN
  attivi%'`): `test-credenziale-blocco-admin-v1` (13), `test-credenziale-di-sistema-v1`
  (15), `test-profili-accesso-guard-ultimo-super-admin` (2, 3). Il censimento del giro 2
  cercava fixture e scrittori, non chi asseriva il **testo** del catalogo. Ora le quattro
  asserzioni pinnano il **codice** (`CONSTRAINT_NAME` di `fn_log_and_raise_error`, helper
  `pg_temp.codice_errore` come in `test-super-admin-senza-scadenza-v1`), che non cambia
  quando la frase si riscrive. Provati su `zeroerp_ci` da owner: 16/16, 3/3; il
  `di-sistema` dà 14/16 con i rossi 6 e 7, che c'erano già prima (ramo della sessione del
  migratore, D-1: da owner per costruzione), mentre il 15 torna verde. ⏳ Rilancio di Tid
  come app.
* `plpgsql_check` sulle tre plpgsql nuove o toccate: nessun messaggio. Il ritorno
  indietro del giro 2, eseguito dopo l'apply simulato, riporta esattamente allo stato del
  giro 1. Guardrail statici: verdi.
* ⚠️ Non provato: la corsa come `zeroerp_app` e la baseline intera (di Tid); il passaggio
  dal driver JDBC per il `BEGIN ATOMIC` del `-16`, che ha il `COMMENT` nel secondo
  `- sql:` come il `-01`, già applicato.

## 9. Consegna BE/FE (2026-10-07)

### 9.1 Una lettura nel BE (§6)

| Punto | Prima | Ora |
| --- | --- | --- |
| Login | `find_identita_attiva_for_ruoli`, `attivo = true` | `AuthRepository.find_veste_utilizzabile_per_ruoli`: `script.fn_veste_utilizzabile(id)` nel `WHERE`, fra le vesti della porta la prima **utilizzabile** |
| Ogni richiesta | CTE `id_row` di `set_jwt_gucs`, `attivo = true` | lo stesso BB nella CTE |
| Refresh | `_veste_accesa` → `get_identita_dettaglio` + `attivo` | `_veste_utilizzabile` → `AuthRepository.get_veste_utilizzabile` |
| Secondo passo | `get_identita_dettaglio` + `attivo` | `get_veste_utilizzabile` |
| Cambio password | `get_identita_dettaglio` + `attivo` | `get_veste_utilizzabile` |
| Ruolo della sessione senza GUC (fallback di `PermissionResolver.get_ruolo_applicativo`: command, chiamate non-HTTP) | `attivo = true`, `LIMIT 1` senza ordine | il BB nel `WHERE`, `ORDER BY id` come al login. ⚠️ Sfuggito al censimento del §5 e trovato in revisione (2026-10-07): con la GUC una veste scaduta non ha ruolo, col fallback ne aveva uno |

Le tre copie Python sono ritirate (regola del 2): `get_veste_utilizzabile` è la sola
domanda «questa veste vale ancora?» a sessione aperta, registrata nel catalogo BB
backend. Il commento di `set_jwt_gucs` che chiedeva di tenere allineate due sedi è
chiuso: la condizione sta nel BB SQL. `get_identita_dettaglio` resta, come **lettura**
per `/me/`. I due metodi del repository condividono la lista delle colonne
(`_SELECT_VESTE`). `find_identita_attiva_for_ruoli` è rinominato: il nome diceva
«attiva», e la regola non è più quella.

### 9.2 Codici, ripieghi, FE (§6 ➕, §8.3)

* **Policy generate** rigenerate dal catalogo: diff dei soli due codici ritirati
  (`E_UTENTE_NON_ATTIVO`, `E_UTENTE_SCADUTO` con `⚠️ RITIRATO il 2026-10-07`).
* **Ripieghi**: i due codici ritirati **restano** in `error_messages_fallback.py`, come
  gli altri ritirati (`CF_NON_VALIDO`…): un codice ritirato continua a risolvere,
  perché il diario ne ha le righe. `E_UTENTE_DISABILITATO` invariato (§6 ➕).
  `E_PROFILO_ULTIMO_SUPER_ADMIN` riallineato al catalogo («Operazione vietata: non
  resterebbe nessun amministratore (SUPER_ADMIN) attivo e senza data di fine.»).
* **FE**: `LoginView.vue` perde le due voci dei codici ritirati, e `it.json`/`en.json`
  le due chiavi rimaste senza lettori (`auth.account_not_active`,
  `auth.account_expired`). Nessun altro cambiamento: D-4 non introduce codici.
* **Batch** (§8.3): `AnagraficheRepository.sync_auth_user_expired` e il command
  `sync_auth_user_active` contano credenziali **riallineate** (spente o accese), non
  «disattivate»; la differenza simmetrica prima/dopo c'era già.
* **Drawer operatore** (§8.3): una data «Valido al» sull'ultimo SUPER_ADMIN senza
  scadenza passa già da `_run_or_raise_super_admin_guard` → 409
  `E_PROFILO_ULTIMO_SUPER_ADMIN`, col messaggio nuovo. Il campo spento col motivo
  è chiesto al DB nel §10 (Tid, 2026-10-07): la regola c'è già, ma la capability del
  drawer la produce `script.fn_get_operatore_detail`, e la sua terna manca.

### 9.3 Prove

* **Sul DB vero** (`test_login_credenziale_db`, casi costruiti in transazione annullata):
  * n. 14: un operatore entrato, anche cliente dello shop (la sua veste tiene accesa la
    credenziale, così il rifiuto che si vede è quello della veste). La veste operatore
    esce dalle sue date restando **accesa**: la richiesta successiva è 401
    `E_IDENTITA_NON_ATTIVA`, il refresh è rifiutato (401), il login nuovo è 403
    `E_VESTE_NON_ATTIVA`, la porta dello shop resta aperta;
  * n. 15: due vesti della porta portale, la più vecchia scaduta e l'altra valida:
    entra la valida (claim `identita_id` e `ruolo_applicativo` della valida);
  * n. 16 (D-2): il rapporto chiuso **dal drawer** (`PATCH` con `valido_al` ieri) e la
    veste ancora accesa: la porta admin è chiusa, quella dello shop aperta.
* Suite `core`, `amm_software`, `portale`, `shop`, `anagrafiche` sul DB vero:
  2489 test verdi (`ZEROERP_TEST_DB_E2E=1`). Nessun test esistente ha cambiato esito
  per D-2 (gli operatori dei test nascono dalla madre, col rapporto).
* Unitari allineati ai metodi nuovi (mock di `get_veste_utilizzabile` e
  `find_veste_utilizzabile_per_ruoli`; il test SQL del login pretende il BB e non più
  `attivo = true`). `ruff` e guard i18n puliti.
* ⚠️ **Non provato**: il 409 del drawer sull'ultimo SUPER_ADMIN senza scadenza sul DB
  vero (la prova chiede un database con un solo amministratore senza date); il
  collaudo a video.

### 9.4 Documentazione e chiusura

Aggiornati: `api_multi_veste_token.md` (la regola dal DB, §2-bis, §3, codici),
`api_user_profile.md` (un codice solo), la guida `risorse-umane-e-accessi` (chi legge la
regola, cache «riallineati»), il piano accessi (§0, A-7, L-6, §4.4), il catalogo BB
backend, PROJECT_CONTEXT. L'archiviazione aspetta il giro 3 (§10).

## 10. Giro 3 DB — la capability della data di fine (richiesta BE/FE, 2026-10-07)

> **A chi:** team DB (`dev/db-tid`); poi BE/FE (§10.3), che **attende**.
> **Decisione di Tid (2026-10-07):** il campo «Valido al» del drawer operatore si
> spegne col motivo, invece di lasciar arrivare il 409.

### 10.1 Il difetto

Dal giro 2 (`-19`, `-20`) mettere una data di fine all'ultimo SUPER_ADMIN senza
scadenza è rifiutato con `E_PROFILO_ULTIMO_SUPER_ADMIN`. Il drawer però non lo sa
prima: il campo «Valido al» (fine del **rapporto**) è acceso, l'amministratore
scrive una data, salva, e riceve un 409. È la regola di casa al contrario: **stato
⇒ controllo spento col motivo** (api.md §«Capability di riga»), e il 409 resta la
rete per la corsa fra due sessioni.

La regola **c'è già**, ed è una: `script.fn_check_ultimo_super_admin_attivo`, che
dal `-17` risponde anche per «dargli una data di fine» (lo dice il suo COMMENT).
Manca solo il **trasporto**: le capability del drawer le produce
`script.fn_get_operatore_detail`, a terne `can_<verbo>` / `<verbo>_reason` /
`<verbo>_reason_key`, **una chiave per verbo** (rev `20260927-02`). Per la data di
fine la terna non c'è.

⛔ Perché non la deriva il BE da `can_disable`: il codice del motivo sarebbe lo
stesso (`ULTIMO_SUPER_ADMIN`), ma la **chiave** la sceglierebbe il backend o il
client, e la frase deve dire **quale** gesto è spento. È la stessa ragione per cui
disable e demote hanno già due chiavi sulla stessa condizione.

### 10.2 Richiesta

In `script.fn_get_operatore_detail`, in coda al `RETURNS TABLE` come le chiavi del
`20260927-02` (nomi e forma li sceglie il team DB):

| Colonna | Valore |
| --- | --- |
| `can_set_valido_al` | `NOT ctx.is_last_sa` (la stessa condizione di `can_disable`) |
| `valido_al_reason` | `'ULTIMO_SUPER_ADMIN'` se `is_last_sa`, altrimenti `NULL` |
| `valido_al_reason_key` | `'amministrazione.operatori.valido_al_reason.ultimo_super_admin'` se `is_last_sa`, altrimenti `NULL` |

* Un amministratore che ha **già** una data di fine risponde `true` (il `-17` lo dice
  già: non è «senza scadenza»), e il campo resta modificabile anche per toglierla.
* Il COMMENT della funzione nomina la terna nuova accanto alle altre.
* Prova: il pgTAP della funzione (o quello del giro 2,
  `test-super-admin-senza-scadenza-v1`) costruisce l'ultimo SUPER_ADMIN senza
  scadenza → `false` col motivo e la chiave; un secondo amministratore senza
  scadenza → `true`, motivo e chiave `NULL`.
* ⚠️ Cambia il `RETURNS TABLE`: `DROP` + `CREATE`. Il BE legge le colonne per nome
  (`row_to_dict`), quindi una colonna in coda non rompe niente.

### 10.3 Dopo la consegna — lato BE/FE (attende)

* BE: `OperatoreDetail` (`amm_software/types.py`) prende la terna; nessuna logica.
* FE: `OperatoreDrawer.vue` spegne «Valido al» con `bloccoAttivo(…, 'valido_al',
  'can_set_valido_al')`, come l'interruttore; tooltip dalla chiave; chiave nuova in
  `it.json`/`en.json`; spec del drawer.
* ➕ Già fatto lato FE in questo giro (non aspetta il DB): le due frasi esistenti
  (`disabilita_reason`, `rimuovi_super_admin_reason`) dicevano «l'ultimo super admin
  **attivo**», che dal giro 2 non è più la regola: ora dicono «senza data di fine».

### 10.4 Consegna DB (2026-10-07) — ✅ applicata (Tid, 2026-10-07, pgTAP verdi)

> Il BE/FE (§10.3) non attende più: le tre colonne sono sul DB.

`20261007-27-update-fn-get-operatore-detail-capability-valido-al` (`20_code/script`).
Tre colonne in coda al `RETURNS TABLE` di `script.fn_get_operatore_detail`, con i nomi
chiesti al §10.2:

| Colonna | Valore |
| --- | --- |
| `can_set_valido_al` | `NOT ctx.is_last_sa` (la condizione di `can_disable`) |
| `valido_al_reason` | `ULTIMO_SUPER_ADMIN`, altrimenti `NULL` |
| `valido_al_reason_key` | `amministrazione.operatori.valido_al_reason.ultimo_super_admin`, altrimenti `NULL` |

* `DROP` + `CREATE` (il `RETURNS TABLE` cambia). Corpo vivo = `20261002-30` (md5 di
  `prosrc` uguale al vivo su dbdev e `zeroerp_ci`), patchato con sostituzioni contate.
  Firma e `RETURNS TABLE` erano già ancorati (`%TYPE`, `django.*` esplicito col perché),
  `SECURITY INVOKER` esplicito. Ritorno indietro: `DROP` + il corpo del `-30`.
* Il COMMENT della funzione e il commento nel corpo nominano la terna e la chiave.
  ⚠️ Per il FE: la chiave sta dentro un `CASE`, quindi `scripts/check_i18n_keys.py` **non
  la vede** (come le due sorelle di disable e demote). Va seminata in `it.json`/`en.json`
  dall'elenco qui sopra, non dal rosso del guard.
* Manuale aggiornato: `docs/it/dbzero/script/manual/fn_get_operatore_detail.md` (la terna,
  e la condizione detta «senza data di fine» invece di «attivo»).

**Prove** (prima dell'apply, su `zeroerp_ci` come owner, in transazione ritirata; lo
scratch ha già i giri 1-2, `-01 → -26`):

* SQL **estratto** dallo YAML (`yaml.safe_load`), `ON_ERROR_STOP`: una sola funzione con
  quel nome, firma `p_auth_user_id integer` invariata, `INVOKER`, `STABLE`; privilegi
  **uguali come insieme** (PUBLIC, owner, `zeroerp_app`, `zeroerp_batch_fatturazione`,
  dai default del proprietario: cambia solo l'ordine nell'array). `plpgsql_check`: zero
  messaggi. Ritorno indietro eseguito dopo: corpo, COMMENT e privilegi uguali al vivo.
* pgTAP `db/pgtap/script/test-fn-get-operatore-detail.sql`, **casi 8-10 nuovi** (plan
  7 → 10), sullo stato lasciato dal caso 7: con due SA senza scadenza la terna è
  `true`/`NULL`/`NULL` (anche per l'operatore non SA); il rapporto di uno riceve una data
  di fine (permesso) e l'altro, ora l'ultimo, risponde `false` + `ULTIMO_SUPER_ADMIN` +
  la chiave; quello con la data di fine risponde `true` con motivo e chiave `NULL`.
  **10/10** col `-27`; 7/7 e poi l'errore sulla colonna mancante col corpo di prima.
  Mutazione (`can_set_valido_al` sempre `true`): **rosso il 9**, quindi il test vede il
  difetto.
* Gli altri tre pgTAP che chiamano la funzione, prima/dopo: `test-credenziale-login-v1`
  22/22, `test-veste-operatore-spenta-v1` 12/12,
  `test-emittente-denominazione-da-soggetto-v1` 14/14, uguali.
* Guardrail statici del repo: verdi.
* ✅ Dopo l'apply (Tid, 2026-10-07): corsa pgTAP verde.

---
{% include-markdown "signature-core.md" %}
