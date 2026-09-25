# Brief DB — La credenziale: tentativi di login, blocco, cambio password obbligatorio, email unica

> **Tipo documento**: brief operativo **per il team DB** (`dev/db-tid`), con la
> ricaduta sul backend al §7.
>
> **Data**: 2026-09-24 · **Stato**: 🟢 **P-1 APPLICATO il 2026-09-25** (§11,
> `20260925-01…-25`). 🟢 **P-2 APPLICATO il 2026-09-25** (§12,
> `20260925-40…-50`, commit `acc6385d5`): corsa pgTAP di Tid **senza
> regressioni**. ⛔ **Il backend va allineato** (§7, §11.3, §12.4): la madre
> dell'operatore ha firma e ritorno nuovi, e il check dell'invito ha la regola
> rovesciata — finché non lo è, su dbdev la creazione dell'operatore dal
> pannello è rotta.
>
> **Da leggere per primo**: §12 (il P-2: cosa c'è, cosa è cambiato rispetto al
> disegno, porta e profili, cosa chiede al backend), poi §11 (il P-1) e §2.
>
> **Due lavori, in quest'ordine**: **P-1** login, blocco e cambio password
> (§2–§4); **P-2** email unica e riuso della credenziale (§5). Sono
> indipendenti nel codice, ma il P-2 cambia il modo in cui nascono le credenziali
> di cui il P-1 tiene lo stato: si fanno nello stesso cantiere.
>
> **Origine**: difetto M-4 di
> [analisi-be-difetti-emersi-verifica-doc-api-core.md](analisi-be-difetti-emersi-verifica-doc-api-core.md),
> diventato il cantiere
> [analisi-accessi-credenziale-e-vesti.md](analisi-accessi-credenziale-e-vesti.md).
> Decisioni di Tid del 2026-09-24:
>
> - **D-1**, *riletta il 2026-09-24 dopo l'analisi critica* — il blocco
>   **vero** di una credenziale è un **atto autorizzato** (un verbo dell'admin).
>   Le password sbagliate non bloccano il titolare: **frenano chi le prova**,
>   cioè la coppia *credenziale + provenienza*, e oltre un tetto per credenziale
>   **rallentano** senza mai chiudere. Tutto in una sede nostra, fuori da
>   `identita_digitali`;
> - **D-2** — un **reset password riuscito azzera i tentativi** della credenziale;
> - **D-7** — il **cambio password obbligatorio** (`deve_cambiare_password`) è
>   della credenziale, nella stessa sede;
> - **D-6** — **una persona, una credenziale**: la creazione dell'operatore
>   riusa la credenziale esistente per email, come già fa l'invito portale/shop;
> - **D-9** — portale e shop si entra con l'**email** (l'operatore col nome
>   utente): l'email diventa una chiave, quindi **unica senza distinguere
>   maiuscole e minuscole**;
> - **D-10** — `totp_obbligatorio` esce dalla veste (nessuno lo legge); il
>   TOTP, quando si farà, sarà della credenziale;
> - il rallentamento oltre il tetto è **un'attesa crescente**, tutta DB e
>   backend: niente captcha né altro controllo nel frontend, per ora.
>
> ⚠️ **La prima versione di questo brief** (stessa data) metteva contatore e
> blocco sulla sola credenziale. È stata **scartata**: chiunque conosca uno
> username poteva chiudere fuori il titolare per 15 minuti, e quelli di portale
> e shop sono generati dall'email, quindi indovinabili. Un blocco deciso da uno
> sconosciuto non è una protezione, è un'arma.

---

## 1. Com'è oggi (verificato sulla doc auto-generata, 2026-09-24)

| Oggetto | Cosa fa | Il difetto |
| --- | --- | --- |
| `script.fn_check_blocco_login(p_auth_user_id)` | legge `bloccato_fino_a` e fa l'auto-sblocco sulla riga `identita_digitali` con `ruolo_applicativo = 'OPERATORE'` | chi non ha quella riga non è mai bloccato |
| `script.fn_registra_tentativo_login(p_auth_user_id, p_successo)` | se non esiste una riga OPERATORE ritorna `{bloccato:false}` **senza contare**; altrimenti incrementa e blocca lì | le vesti portale/shop non contano; un operatore-cliente si blocca come operatore sbagliando sul portale |
| `anagrafiche.identita_digitali` | porta `tentativi_falliti`, `bloccato_fino_a`, `deve_cambiare_password` per **riga di veste** | lo stato di una cosa sola (la credenziale) è distribuito su N righe |
| `script.fn_get_user_profile`, `script.fn_get_operatore_detail` | leggono `deve_cambiare_password` dall'identità; la prima lo dichiara `anagrafiche.identita_digitali.deve_cambiare_password%TYPE` | da ripuntare; il `%TYPE` si rompe col `DROP COLUMN` |
| pgTAP | **nessun** test copre le due funzioni del login | — |

Il filtro `OPERATORE` è un **residuo**, non una scelta: le funzioni sono nate su
`risorse_umane_auth_user` (operatori per natura), e l'hotfix
`20260419-93/-94` ha spostato le scritture su `identita_digitali` tenendo il
perimetro di allora. ⚠️ I manual e i `COMMENT ON FUNCTION` delle due funzioni
citano ancora `risorse_umane_auth_user` / «post-cutover §13.3».

⭐ **Un costo nascosto della sede attuale.** Ogni password sbagliata è un
`UPDATE` su `identita_digitali`, quindi uno snapshot nello storico
(`z90_storico_upd_dlt`, `storicizza` a default `true`) e il passaggio da
`guard_coerenza`, `guard_ultimo_super_admin`, i due
`prevent_deactivate_if_children` e `sync_auth_user_active`. Lo stato volatile
di un login non è anagrafica della veste: anche questo dice che la sede è
sbagliata, prima ancora del filtro.

Il login del backend (`core/api/auth_views.py`) chiama il check **prima** di
verificare la password e registra l'esito **dopo**; un `VesteNonAttivaError`
(password giusta, porta sbagliata) non conta come fallimento. Resta così.

---

## 2. La forma decisa

Tre regole diverse, con tre sedi diverse:

| Regola | Chi la fa scattare | Cosa colpisce | Esito al login |
| --- | --- | --- | --- |
| **Freno sulla provenienza** | automatico, dopo N fallimenti consecutivi dalla stessa provenienza | la coppia *credenziale + provenienza*: chi sta provando | rifiuto temporaneo **da quella provenienza** (`E_UTENTE_BLOCCATO`) |
| **Attesa crescente sulla credenziale** | automatico, oltre un tetto di fallimenti consecutivi da qualunque provenienza | la credenziale, ma **solo rallentandola** | «riprova fra N secondi», con N limitato da un massimo |
| **Blocco della credenziale** | **un utente autorizzato**, con un verbo | la credenziale su tutte le porte | rifiuto finché qualcuno con il diritto non la sblocca |

⭐ Il perché, sul modello:

- la password è **una** e vale per tutte le porte (operatore, portale, shop): il
  conto non guarda la veste. **La provenienza non è una veste**, è la macchina
  da cui si prova;
- chi attacca da una macchina sua **non chiude fuori** il titolare, che entra
  dalla propria;
- l'attacco distribuito (molte provenienze, pochi tentativi ciascuna) si frena
  col tetto sulla credenziale, che **rallenta ma non chiude**: il titolare aspetta
  al massimo l'attesa massima fra un tentativo e l'altro, e ha sempre il reset
  (D-2). Possedere l'email è già un'autorizzazione;
- chiudere una credenziale è una **decisione**, e le decisioni hanno un autore.

### 2.1 La provenienza

- È l'**indirizzo IP del chiamante**, tipo `inet`, passato dal backend. Lo
  ricava il backend, anche dietro un proxy: è una sua responsabilità (§7).
- È **obbligatoria**: `NULL` non è un valore di chiave (una coppia con `NULL`
  non si incontra mai con sé stessa in un `UNIQUE`). Le funzioni rifiutano
  `NULL` con errore, non la trattano come «provenienza ignota».

### 2.2 Le sedi — proposta di forma, il team DB può affinarla

Il vincolo che conta: **un tentativo fallito non produce storico**, e il blocco
dell'admin ha un autore registrato.

**`<schema>.credenziali`** — 1:1 con `django.auth_user`. Schema a scelta del
team DB; il precedente è `config.auth_totp_device` (anche lui 1:1), con una
differenza voluta: qui la PK **è** `auth_user_id`, senza `id` surrogato.
⚠️ *Corretto in esecuzione (§11.2): le linee guida (§2-§4) vogliono la PK `id`
ed evitano le chiavi composte — `id` + `UNIQUE (auth_user_id)`, come
`auth_totp_device`; la figlia punta a `credenziali.id`.*

| Colonna | Note |
| --- | --- |
| `auth_user_id` | PK; FK verso `django.auth_user` con `ON DELETE CASCADE` (satellite puro) — ⚠️ nella forma di casa per le FK verso Django, sotto |
| `deve_cambiare_password` | D-7 |
| `fallimenti_consecutivi` | da qualunque provenienza, azzerati da un successo o da un reset |
| `ultimo_fallimento_at` | `timestamptz`; base dell'attesa crescente |
| `bloccata_at`, `bloccata_da`, `motivo_blocco` | blocco dell'admin; tutti `NULL` = non bloccata. `CHECK` di coerenza: o tutti valorizzati (motivo compreso) o nessuno. `bloccata_da` = `auth_user_id` di chi ha bloccato |
| audit standard | `data_insert`/`user_insert`/`data_update`/`user_update` (§7 linee guida) |

**`<schema>.credenziali_provenienze`** — una riga per coppia.

| Colonna | Note |
| --- | --- |
| `auth_user_id`, `provenienza` | PK composta; FK `ON DELETE CASCADE` verso `credenziali` |
| `tentativi_falliti` | consecutivi da questa provenienza |
| `bloccato_fino_a` | `timestamptz`, `NULL` = non frenata |
| `ultimo_fallimento_at` | `timestamptz` |
| `cleanup_at` | retention (§2.5) |
| audit standard | |

Per entrambe:

- **niente storicizzazione**: nessuna colonna `storicizza`, nessuna regola
  STORICO. Una riga di `credenziali` cambia a ogni fallimento: lo storico
  tornerebbe a registrare le password sbagliate. Se servirà la **storia** dei
  blocchi dell'admin, si scriverà in un registro di eventi, non nello storico
  della riga. Per ora bastano l'ultimo stato e l'autore;
- **niente RLS**: nessuno scope (§10.1 delle linee guida), e le due funzioni del
  login girano **prima** che esista un utente;
- ⚠️ **la FK verso `django.auth_user` non nasce con la tabella.** In CI
  Liquibase gira **prima** di `manage.py migrate`, quindi lì `django.auth_user`
  non esiste. La forma di casa (18 FK già così, ultima
  `90_end/20260921-02-fk-config-auth-totp-device-auth-user-id-django-auth-user`):
  changeSet in `90_end`, `preCondition` `tableExists` su `django.auth_user`,
  `onFail: MARK_RAN`, più la riga in `fk_index_policy_auth_user.csv`. Il prezzo,
  dichiarato: **in CI la FK non esiste**, e il test del `CASCADE` (§6, 21) salta
  dove manca, come `config/test-fk-auth-user-ponte-django-v1`. Per la stessa
  ragione le funzioni che nominano `django.*` sono `plpgsql` e **senza** `%TYPE`
  su colonne di Django;
- ⛔ **porta chiusa all'app** fin dalla nascita, come vuole il modello «una
  scrittura = un verbo» per i domini nuovi
  ([brief-db-permesso-nel-verbo-di-scrittura.md](brief-db-permesso-nel-verbo-di-scrittura.md),
  D-1): `zeroerp_app` non ha `INSERT`/`UPDATE`/`DELETE` né `SELECT` diretti.
  Legge e scrive **solo** attraverso le funzioni del §3, `SECURITY DEFINER` del
  proprietario. ⚠️ *Corretto in esecuzione (§11.2): il `SELECT` all'app
  **resta**. `fn_check_almeno_un_super_admin_attivo` è `LANGUAGE sql` e la
  chiamano trigger `INVOKER` che girano come l'app: senza `SELECT` i guard
  anti-lockout su identità e binding si romperebbero. Il modello del verbo
  chiude le scritture, non le letture; il backend legge comunque dalle funzioni.* Il loop dei grant di `ci_apply` non deve riaprirle (vedi
  linee-guida-sql §11.8, e quanto fatto per `magazzino.movimenti`).

### 2.3 La riga nasce alla prima scrittura

La riga **non** esiste per ogni credenziale: nasce alla prima scrittura. La sua
**assenza** vale «nessun tentativo, nessun freno, non bloccata, nessun obbligo
di cambio password».

- Una riga sempre presente chiederebbe di chiudere la seconda strada di
  creazione delle credenziali (`PortaleRepository.create_auth_user_portale`,
  backend), oppure un trigger su `django.auth_user`, cioè una dipendenza da una
  tabella governata dalle migration di Django. Nessuna delle due serve.
- ⛔ **Il valore dell'assenza sta in un posto solo** perché **nessuno fuori dal
  DB legge o scrive le tabelle**: lo leggono le funzioni del §3, e il
  backend chiede a loro. Se il backend facesse l'`INSERT … ON CONFLICT` da sé,
  la regola «assente = false» vivrebbe in due livelli.
- Le scritture sono **un'istruzione sola**
  (`INSERT … ON CONFLICT (…) DO UPDATE … RETURNING`): due primi fallimenti
  concorrenti su una riga assente non devono scontrarsi.

### 2.4 Le regole, per esteso

**Freno sulla provenienza** (parametri esistenti `login_max_tentativi_falliti` =
5, `login_blocco_minuti` = 15, globali come oggi):

- a ogni fallimento `tentativi_falliti + 1` sulla coppia; alla soglia,
  `bloccato_fino_a = now() + blocco`;
- **blocco scaduto = si riparte**: la coppia torna a zero. Lo fa **chiunque**
  incontri il blocco scaduto, sia il check sia la registrazione. Oggi lo fa solo
  il check: se la registrazione venisse chiamata senza passare dal check,
  troverebbe il contatore già alla soglia e frenerebbe di nuovo al primo errore.

**Attesa crescente sulla credenziale** (parametri nuovi, §9 D-B2):

- a ogni fallimento `fallimenti_consecutivi + 1`, `ultimo_fallimento_at = now()`;
- sotto il tetto, nessuna attesa;
- dal tetto in su, `attesa = LEAST(max, base × 2^(fallimenti_consecutivi − tetto))`;
  un tentativo arrivato prima di `ultimo_fallimento_at + attesa` è **rifiutato
  senza verificare la password e senza contare** (è il check, che viene prima
  della password);
- ⚠️ **limite da dichiarare, non da scoprire**: sotto un attacco distribuito
  **continuo** il titolare può trovare la finestra già consumata da un
  tentativo altrui, e aspettare più di una volta. Il rimedio è il reset (D-2).
  Un affinamento possibile (esentare le provenienze da cui la credenziale è già
  entrata con successo) **non** si chiede ora (§9 D-B4).

**Blocco dell'admin**: nessuna scadenza. Lo toglie solo il verbo di sblocco.
⛔ **Il reset password non lo toglie** (§9 D-B3): il reset dimostra il
possesso dell'email, non annulla la decisione di chi ha bloccato.

**Ordine del check al login** — il primo che scatta vince:

1. blocco dell'admin → codice nuovo, per esempio `E_CREDENZIALE_BLOCCATA`
   (non temporaneo: «contattare l'amministratore»);
2. freno sulla provenienza → `E_UTENTE_BLOCCATO` (esistente, invariato),
   con i minuti rimanenti;
3. attesa crescente → codice nuovo, per esempio `E_LOGIN_ATTESA`, con i
   secondi rimanenti.

I codici nuovi entrano in `codici_errore.csv` e `messaggi_errore.csv`, con la
classe `NON_PERMESSO` (403) di `E_UTENTE_BLOCCATO`. ⚠️ La prima stesura diceva
«per l'attesa, se c'è, quella del "troppe richieste"»: superata dalla nota qui
sotto.

⚠️ **Nota del backend (2026-09-24): per l'attesa NON un 429.** Due fatti,
verificati: (1) fra le dieci classi del catalogo **non ce n'è una** «troppe
richieste» (`error_policies.py`: 400, 409, 404, 500, 403, 422, 501, 401, 502 e
`AVVISO`); (2) il login del frontend (`LoginView.resolveLoginError`) intercetta
il **429 prima di leggere il codice** — è il throttle per IP — e mostrerebbe
«troppi tentativi» perdendo i secondi d'attesa. È la stessa trappola per cui
`E_UTENTE_BLOCCATO` è passato da 423 a **403** e non a 429 (api.md, «I tre
status con un solo uso»). ⇒ **`E_LOGIN_ATTESA` e `E_CREDENZIALE_BLOCCATA` con
la classe di `E_UTENTE_BLOCCATO`, `NON_PERMESSO` (403)**; il frontend li
riconosce per codice.

### 2.5 Retention delle provenienze

Ogni provenienza che sbaglia crea una riga, e quelle di chi non riprova più
restano. Serve una scadenza, con i **quattro pezzi** del framework di cleanup
(colonna `cleanup_at`, regola `CLEANUP_AT` con `base_ts_column =
ultimo_fallimento_at`, trigger alla nascita, e nessun guard sul `DELETE` che la
respinga). ⚠️ In più: la riga viene **aggiornata** a ogni fallimento, e il
trigger alla nascita non la rivede; il verbo di registrazione **ricalcola**
`cleanup_at` a ogni fallimento, leggendo il termine da
`dbops.fn_cleanup_at_params` (sede unica del TTL, nessun numero nel verbo).
TTL proposto: 1 giorno.

Un successo o un reset **cancellano** le righe di provenienza della credenziale:
non c'è niente da ricordare. ⚠️ *Corretto in esecuzione (§11.2): un **accesso
riuscito** cancella solo la coppia da cui si è entrati; il **reset** le cancella
tutte.*

---

## 3. Le funzioni

Tutte `SECURITY DEFINER` del proprietario, `search_path` fissato, `%TYPE` in
firma, `DECLARE` e `RETURNS` sulle colonne delle tabelle nuove. ⚠️ *In
esecuzione: `DEFINER` quelle che **scrivono**; `INVOKER` i lettori e i guard
(`fn_get_deve_cambiare_password`, `fn_guard_super_admin`, `fn_login_parametri`,
`fn_login_attesa_secondi`), perché l'app legge le tabelle (§11.2).*

### 3.1 Il login — senza identità di chi agisce

Girano **prima** del login: non c'è un utente da controllare, quindi non
passano da nessun guard di permesso (`fn_guard_azione`, `fn_guard_super_admin`). È un'eccezione **dichiarata**, con il
limite del §4.4 del brief sul permesso: proteggono da un backend che sbaglia
l'ordine delle chiamate, non da un backend compromesso.

| Funzione | Contratto |
| --- | --- |
| `fn_check_blocco_login(p_auth_user_id, p_provenienza)` | le tre verifiche del §2.4, in quell'ordine; `RETURNS void`, solleva |
| `fn_registra_tentativo_login(p_auth_user_id, p_provenienza, p_successo)` | successo → azzera (verbo sotto); fallimento → coppia + credenziale in un giro, `RETURNS jsonb` con i campi di oggi (`bloccato`, `minuti_rimanenti`, `tentativi`) **più** `attesa_secondi` |

⚠️ **La firma cambia** (serve la provenienza): è una funzione nuova per
Postgres, quindi la vecchia si fa `DROP`, non si lascia come overload. L'unico
chiamante è `AuthRepository` (§7). Nessun pgTAP la chiama oggi.

⛔ Nessun filtro su veste o `ruolo_applicativo`: il caso «credenziale senza
riga OPERATORE → non contare» sparisce. Una credenziale **senza nessuna
identità** conta anch'essa: la password c'è.

### 3.2 L'azzeramento dei tentativi (D-2)

`fn_azzera_tentativi_credenziale(p_auth_user_id)`: `fallimenti_consecutivi = 0`,
`ultimo_fallimento_at = NULL`, righe di provenienza cancellate. **Non** tocca il
blocco dell'admin né `deve_cambiare_password`.

**Una regola, tre chiamanti**: il ramo «successo» di
`fn_registra_tentativo_login`, il reset password riuscito (backend), e nessun
altro. ⚠️ *Corretto in esecuzione (§11.2): la firma è
`fn_azzera_tentativi_credenziale(p_auth_user_id, p_provenienza DEFAULT NULL)`.
Con la provenienza (accesso riuscito) cancella la **sola** coppia da cui si è
entrati: il freno sulla macchina di chi attacca resta, altrimenti ogni login del
titolare le regalerebbe tentativi nuovi. Senza (reset) le cancella tutte.* ⚠️ Non si riusa `fn_registra_tentativo_login(uid, …, true)` dal reset:
un reset non è un tentativo di login, e il nome mentirebbe nel giornale.

⚠️ **Nome**: nella prima versione era «sblocco». Ora «sblocca» è il verbo
dell'admin (§3.3): l'azzeramento si chiama con il suo nome, per non confondere
chi legge il backend.

### 3.3 Il blocco dell'admin — verbi con permesso

| Verbo | Contratto |
| --- | --- |
| `fn_blocca_credenziale(p_auth_user_id, p_motivo)` | prima riga `script.fn_guard_super_admin(<chi agisce>)` (D-B1); scrive `bloccata_at`/`bloccata_da`/`motivo_blocco`; `p_motivo` obbligatorio |
| `fn_sblocca_credenziale(p_auth_user_id)` | stessa prima riga; azzera i tre campi |

- Chi agisce si legge da `app.current_user_id`, come nei verbi di magazzino
  ([brief-db-magazzino-verbi-con-permesso.md](brief-db-magazzino-verbi-con-permesso.md) §2.1).
- ⭐ **Perché SUPER_ADMIN e non un'azione di processo** (D-B1): la gestione
  degli accessi oggi è `amm_software`, che **non è un'area** del catalogo: è
  un'app del backend, le sue view sono `AdminAPIView` e lasciano entrare solo
  i SUPER_ADMIN. Un'azione non avrebbe un'area a cui appartenere, e dal lato
  backend nessuno la leggerebbe (su `AdminAPIView` una `post_permission` non la
  valuta nessuno). Il verbo chiede quindi **la stessa regola della porta**. Se
  un giorno si vorrà delegare il blocco a chi non è SUPER_ADMIN, servirà un'area
  con la sua azione: sarà una decisione a parte.
- **Il building block `script.fn_guard_super_admin(p_auth_user_id)`** —
  nuovo, e la ragione è la regola del 2: oggi nessun verbo del DB rifiuta chi
  non è SUPER_ADMIN (la sola funzione che nega `fn_is_super_admin` è la fixture
  pgTAP `fn_pgtap_set_contesto_operatore`), e qui i verbi sono **due**. Stessa
  forma di `script.fn_guard_azione`: l'utente come parametro, la **regola** in
  `script.fn_is_super_admin` (la stessa del backend, già con il gate di
  contesto: fuori dalla veste OPERATORE risponde `false`), risposta no →
  `E_PERMESSO_NEGATO`, **anche a utente `NULL`** (fail-closed). Si registra nel
  catalogo dei building block del DB nello stesso giro.
- ⛔ **Anti-lockout**: bloccare l'ultimo SUPER_ADMIN raggiungibile chiude fuori
  il sistema. La regola ha già una sede,
  `script.fn_check_almeno_un_super_admin_attivo`, e il suo manual prevede
  proprio l'aggiunta di un gate come questo *«solo lì»*: la condizione
  «credenziale non bloccata dall'admin» entra **nella funzione**, e un guard
  `AFTER UPDATE` su `credenziali` la chiama come fanno quelli su
  `identita_digitali` e sui binding. Non un controllo scritto a parte nel verbo.
- Bloccare sé stessi: vale la stessa regola (l'anti-lockout copre il caso che
  conta); nessun divieto in più.

### 3.4 Il cambio password obbligatorio (D-7)

| Funzione | Contratto |
| --- | --- |
| `fn_get_deve_cambiare_password(p_auth_user_id)` | `STABLE`, `RETURNS boolean`; assenza della riga = `false` |
| `fn_imposta_deve_cambiare_password(p_auth_user_id, p_valore)` | upsert |

`fn_imposta_…` **non** passa da un guard di permesso: la chiamano l'invito
operatore (un admin), ma anche il cambio password, il reset e l'attivazione, che
girano come l'utente stesso o prima del login. Stesso limite dichiarato del §3.1.

⭐ **Regola del 2**: la lettura ha tre consumatori a DB (`fn_get_user_profile`,
`fn_get_operatore_detail`, e il backend attraverso questa funzione): il default
dell'assenza vive **solo** in `fn_get_deve_cambiare_password`, e gli altri due
la chiamano, con il nome del campo in uscita invariato. ⚠️ In
`fn_get_user_profile` il `%TYPE` sulla colonna di `identita_digitali` va tolto
nello stesso giro: dopo il `DROP COLUMN` la funzione si romperebbe alla prima
chiamata.

---

## 4. Le colonne escono da `identita_digitali`

`tentativi_falliti`, `bloccato_fino_a`, `deve_cambiare_password` **e
`totp_obbligatorio`** (D-10: nessuno lo legge) escono da
`anagrafiche.identita_digitali` **nello stesso cantiere** (non c'è produzione;
nessuna doppia sede nel modello).

**Migrazione dei valori** (dati di sviluppo; su un DB ricostruito da zero è a
vuoto, e va scritta in modo che lo sia):

- `deve_cambiare_password`: si crea la riga di `credenziali` **solo** dove
  l'OR sulle identità **attive** della credenziale è `true`. Le identità non
  attive (revocate, `DISABILITATO`) non contano: un `true` rimasto su una veste
  spenta non deve imporre il cambio alla credenziale;
- contatori e blocchi ripartono da zero.

**Ordine dei changeSet**: tabelle, funzioni, lettori ripuntati e migrazione dei
valori prima; il `DROP COLUMN` **per ultimo**, nel suo changeSet. ⚠️ *In
esecuzione (§11.3): a rompere il backend non è solo il `DROP`, ma già la firma
nuova delle due funzioni del login — il P-1 intero va applicato con la PR BE.* ⚠️ Su dbdev,
fra l'apply del `DROP` e l'allineamento del backend, il login si rompe:
`auth_repository` legge quelle colonne con SQL diretto. La PR DB e la PR backend
entrano **insieme** in `Tito-dev`.

---

## 5. L'email della credenziale e la creazione dell'operatore (P-2: D-6, D-9)

### 5.1 L'email è unica, senza distinguere maiuscole e minuscole (D-9)

Nessuna coppia di credenziali con la stessa email a meno delle maiuscole
(`lower(email)`). L'email diventa la chiave d'ingresso di portale e shop: due
credenziali con la stessa email renderebbero ambiguo il login e il reset.

- ⚠️ **«Email valorizzata» vuol dire `email <> ''`, non `IS NOT NULL`.** Nel
  modello di Django la colonna è `NOT NULL` e l'email mancante è la stringa
  vuota: un indice unico senza il filtro `WHERE email <> ''` farebbe collidere
  tutte le credenziali senza email (utenti tecnici, super admin creati da riga di
  comando).
- ⚠️ **Dove nasce il vincolo (D-B5): Liquibase, `90_end`, con `onFail:
  CONTINUE`** — non `MARK_RAN`, e non una migration Django. Nel progetto le
  migration Django **non esistono** (nessuna cartella `migrations/`, i model
  sono `managed = False`): il DDL ha una sede sola, Liquibase, e un indice non
  giustifica una seconda. Il vincolo è DDL, quindi è del team DB.
  ⭐ Perché `CONTINUE` e non la forma delle FK verso Django (`MARK_RAN`): se
  `django.auth_user` non c'è ancora, `MARK_RAN` segna il changeSet come eseguito
  e non ci torna più, quindi su un'installazione nuova l'indice **non
  nascerebbe mai**. Per una FK di contorno è un prezzo accettato; per l'unica
  garanzia di unicità no. `CONTINUE` salta senza segnare e riprova al migrate
  successivo (precedenti in casa: `90_end/ci_apply/20250627-31`, i template di
  `80_data`). Nel changeSet: `preConditions` `tableExists` su
  `django.auth_user` **e** «l'indice non esiste ancora», `onFail: CONTINUE`,
  `CREATE UNIQUE INDEX IF NOT EXISTS … (lower(email)) WHERE email <> ''`.
  ⚠️ Il prezzo che resta: **in CI l'indice non c'è**, perché lì Liquibase gira
  tutto prima di `manage.py migrate` (ci-validate: Liquibase alle righe 442-499,
  Django a 602, pgTAP a 776). Il test dell'indice salta con `skip()` motivato;
  **il guard di `fn_crea_auth_user` invece in CI si prova**, perché i pgTAP
  girano dopo Django.
- Prima del vincolo, un controllo sui dati di sviluppo per le coppie esistenti,
  da **sistemare a mano**, non con codice.
- `anagrafiche.fn_crea_auth_user` confronta l'email con `=` (distingue le
  maiuscole): il suo guard passa a `lower(…)`, così l'errore resta
  `E_ADMIN_EMAIL_DUPLICATA`, con il suo messaggio, invece di una violazione
  d'indice anonima.

### 5.2 La creazione dell'operatore riusa la credenziale (D-6)

Oggi la madre `anagrafiche.fn_crea_operatore_v2` chiama `fn_crea_auth_user`, che
rifiuta un'email già presente, mentre l'invito portale/shop cerca la credenziale
con `LOWER(email)` e la riusa. ⇒ Una persona che è prima cliente e poi operatore
finisce con due credenziali.

Si chiede che **la madre** (non il building block `fn_crea_auth_user`, che resta
«crea e basta») cerchi la credenziale per email e, se c'è, la **riusi**, senza
toccarne la password, aggiungendo la veste OPERATORE **non attiva**: la accende
l'invito (regola unica, analisi §4.2). La forma la sceglie il team DB.

⚠️ Tre ricadute che vanno **nello stesso giro**, o il riuso fa danni:

1. **La password scelta dall'admin viene ignorata** quando la credenziale esiste
   già: oggi `create_operatore` la passa obbligatoria (`p_password_hash`). Il
   contratto della madre deve dirlo (per esempio: ritorna anche «credenziale
   riusata sì/no»), e il backend smette di mostrare quella password come valida.
2. **L'invito operatore non deve più sovrascrivere la password** (A-1 dell'analisi,
   `invito_operatore_service.py:77-82`): con la credenziale riusata, la
   sovrascrittura chiuderebbe fuori la persona anche dal portale.
3. **L'attivazione operatore deve accendere la veste** (A-3): oggi non lo fa,
   perché la veste nasce già attiva. Con la veste che nasce spenta, senza questo
   passo l'operatore invitato non entra.

E un caso da rifiutare: la credenziale trovata ha **già** una veste OPERATORE
attiva (è già operatore, magari di un altro soggetto) → errore esplicito, non la
violazione dell'unique `(auth_user_id, ruolo_applicativo) WHERE attivo`.

---

## 6. Test (pgTAP) — casi costruiti, non popolazione

File nuovo: oggi nessun test copre queste funzioni. I soggetti e le credenziali
il test se li fabbrica. ⚠️ *In esecuzione i casi P-1 sono in quattro file
(§11.4); il test 1 «sola veste portale» è coperto da quello più forte, la
credenziale **senza nessuna identità**: il codice non legge più le vesti.*

**Freno sulla provenienza**

1. credenziale con la **sola** veste portale (o shop): N fallimenti da P1 →
   `fn_check_blocco_login(uid, P1)` solleva `E_UTENTE_BLOCCATO`;
2. ⭐ **stessa credenziale, P2**: dopo il freno su P1, da P2 il check passa. È il
   test che distingue questa forma dalla prima versione del brief;
3. credenziale con più identità (operatore + cliente portale): i fallimenti da
   P1 finiscono su **una** coppia, non sdoppiati per veste;
4. credenziale **senza nessuna identità**: conta anch'essa;
5. blocco scaduto → la coppia riparte da zero, sia passando dal check sia
   chiamando **direttamente** la registrazione;
6. `p_provenienza IS NULL` → errore.

**Attesa crescente**

7. fallimenti da provenienze tutte diverse, ciascuna sotto la soglia, fino al
   tetto: nessun freno di coppia, ma dal tetto in su il check chiede l'attesa
   (`E_LOGIN_ATTESA`);
8. l'attesa cresce e **si ferma al massimo**;
9. un tentativo rifiutato per attesa **non** incrementa i contatori.

**Azzeramento (D-2)**

10. successo → contatori della credenziale a zero, righe di provenienza
    cancellate;
11. `fn_azzera_tentativi_credenziale` → idem, e **non** tocca il blocco
    dell'admin né `deve_cambiare_password`.

**Blocco dell'admin**

12. chi agisce non è SUPER_ADMIN (e, a parte, chi agisce è `NULL`) →
    `fn_blocca_credenziale` e `fn_sblocca_credenziale` rifiutano con
    `E_PERMESSO_NEGATO`;
13. chi agisce è SUPER_ADMIN → bloccata: il check solleva `E_CREDENZIALE_BLOCCATA` da
    qualunque provenienza, anche dopo un azzeramento;
14. `fn_sblocca_credenziale` → il check passa;
15. bloccare l'ultimo SUPER_ADMIN → rifiutato dal guard anti-lockout;
16. motivo mancante → rifiutato (`CHECK`).

**Cambio password obbligatorio e lettori**

17. riga assente → `fn_get_deve_cambiare_password` = `false`;
18. `fn_imposta_…` su riga assente la crea; `fn_get_user_profile` e
    `fn_get_operatore_detail` leggono il valore dalla nuova sede.

**Struttura**

19. le quattro colonne **non** esistono più su `identita_digitali`;
20. `zeroerp_app` **non** ha privilegi diretti sulle due tabelle, e ha
    `EXECUTE` sulle funzioni del §3;
21. cancellare l'`auth_user` si porta via le righe (`CASCADE`) — `skip()`
    motivato dove la FK non esiste (CI, §2.2).

**Email e creazione dell'operatore (P-2)**

22. due credenziali con `Mario@x.it` e `mario@x.it`: la seconda è rifiutata
    (`skip()` motivato dove l'indice non c'è, cioè in CI: §5.1, D-B5);
23. due credenziali con email vuota (`''`): **entrambe** ammesse;
24. `fn_crea_auth_user` con un'email che differisce solo per le maiuscole →
    `E_ADMIN_EMAIL_DUPLICATA`;
25. creazione di un operatore su un'email che ha già una credenziale (cliente
    portale): nessuna credenziale nuova, password invariata, veste OPERATORE
    aggiunta **non attiva**;
26. stessa creazione, ma la credenziale ha già una veste OPERATORE attiva →
    rifiutata con il codice del §5.2.

---

## 7. Ricaduta sul backend (la faccio io dopo il changeSet)

- **Provenienza**: `check_blocco_login` e `registra_tentativo_login` passano
  l'IP del chiamante. Ricavarlo bene dietro un proxy (quali `X-Forwarded-For`
  fidarsi) è del backend.
- ⚠️ **`LoginRateThrottle`** (5 ogni 5 minuti **per IP**, su tutti gli utenti)
  resta: è una regola diversa, contro chi inonda di richieste l'endpoint, non
  contro chi prova una credenziale. Va scritto nella guida che sono due regole
  distinte, perché con i numeri di oggi (5 e 5) sembrano la stessa.
- Codici nuovi `E_CREDENZIALE_BLOCCATA`, `E_LOGIN_ATTESA`: mappatura della
  risposta e messaggi.
- `AuthRepository.get/set_deve_cambiare_password` diventano chiamate a
  `fn_get_deve_cambiare_password` / `fn_imposta_deve_cambiare_password`,
  **senza** `identita_id` (D-7) e **senza** SQL diretto: il login, il
  middleware, `apply_new_password` (cambio, reset, attivazione), l'invito
  operatore.
- Il reset password riuscito chiama `fn_azzera_tentativi_credenziale(uid)`
  **senza** provenienza (tutte le coppie). L'accesso riuscito non la chiama: ci
  pensa `fn_registra_tentativo_login(uid, provenienza, true)`.
- `fn_registra_tentativo_login` restituisce anche `attesa_secondi`; il check può
  rispondere `E_CREDENZIALE_BLOCCATA`, `E_UTENTE_BLOCCATO` (minuti nel contesto),
  `E_LOGIN_ATTESA` (secondi nel messaggio e nel contesto) ed
  `E_AUTH_CHIAMATA_NON_VALIDA` (provenienza mancante). Cinque codici nuovi in
  `codici_errore.csv` (§11.1): `error_policies_generated.py` e
  `error_messages_fallback.py` vanno rigenerati.
- Blocco dell'admin: endpoint in `amm_software` (`AdminAPIView`, cioè
  SUPER_ADMIN, la stessa regola del verbo: D-B1); al blocco, **blacklist di
  tutte le sessioni** della credenziale.
- Lettori di `identita_digitali` che perdono le colonne:
  `PortaleRepository.find_identita_portale` (`portale_repository.py:95`),
  `PortaleRepository.create_identita_portale`, `ProfileActivateShopView`,
  `invito_portale_service`; `IdentitaDigitale` (model) perde le **quattro**
  colonne (anche `totp_obbligatorio`, D-10).
- P-2: `create_operatore` gestisce la credenziale riusata; invito operatore
  senza sovrascrittura della password; attivazione operatore che accende la
  veste (§5.2); login e reset di portale e shop per email (D-9);
  l'indice unico sull'email lo crea il DB (D-B5, §5.1); al backend resta il
  controllo a mano delle coppie sui dati di sviluppo, **prima** che l'indice
  venga applicato.
- Test aggiornati.

## 8. Documentazione

✅ *Fatto il 2026-09-25 per la parte DB: manual di `config.credenziali` (il
modello, una sede sola), `config.credenziali_provenienze`, delle funzioni nuove e
riscritte, del guard; `identita_digitali.md` e il manual del guard sulle identità
riscritti. Resta al backend la guida `architettura-multi-face-auth.md` §3.1.*

- manual di `fn_check_blocco_login` e `fn_registra_tentativo_login`, e i loro
  `COMMENT ON FUNCTION`: da riscrivere; manual delle funzioni nuove;
- `anagrafiche/manual/identita_digitali.md` («lockout per-veste»): da riscrivere;
- `anagrafiche/manual/trgfn_identita_digitali_guard_ultimo_super_admin.md`
  (cita `bloccato_fino_a` come gate futuro): ora il gate è il blocco dell'admin;
- guida `architettura-multi-face-auth.md` §3.1 («lo stato di lockout è
  per-identità»): la riscrivo io con la ricaduta BE, con le tre regole del §2.

## 9. Decisioni di dettaglio — ✅ prese da Tid il 2026-09-24

| # | Domanda | Decisione |
| --- | --- | --- |
| **D-B1** | Chi può bloccare e sbloccare una credenziale | ✅ **Tid, 2026-09-24: SUPER_ADMIN** — la gestione accessi è `amm_software`, che non è un'area del catalogo ma una porta per soli SUPER_ADMIN; il verbo chiede la stessa regola, con il building block nuovo `script.fn_guard_super_admin` (§3.3). Nessuna area né azione nuova |
| **D-B2** | Valori dell'attesa crescente | ✅ **come proposto** — tetto 20 fallimenti consecutivi, base 2 s, massimo 60 s: parametri nuovi in `parameters.csv`, globali come gli altri due. ⚠️ *In esecuzione in un CSV dedicato, `parameters_login.csv` (id 57-59): `parameters.csv` è un mirror dormiente (vedi `20260825-12`)* |
| **D-B3** | Il reset password toglie anche il blocco dell'admin? | ✅ **come proposto** — **no** (§2.4) |
| **D-B4** | Esentare dall'attesa le provenienze da cui la credenziale è già entrata? | ✅ **come proposto** — non ora: aggiunge una memoria delle provenienze buone. Si riprende se il limite del §2.4 diventa un problema reale |
| **D-B5** | Dove nasce l'indice unico su `lower(email)` di `django.auth_user` | ✅ **Tid, 2026-09-24 — corretta la prima proposta** (migration Django): nel progetto non ne esistono, il DDL è solo Liquibase. ⇒ changeSet `90_end` con `onFail: CONTINUE`, lavoro del team DB (§5.1) |

## 10. Cosa non si chiede

- La disattivazione e riattivazione per veste (M-5, M-6, D-3 dell'analisi) e
  la veste che ricorda di essere stata revocata (D-4): è un altro lavoro, anche
  se nasce dallo stesso cantiere.
- La scrittura di `last_login` (D-8): è del backend.
- L'enumerazione delle credenziali (un codice di blocco esce solo per username
  o email esistenti): è così anche oggi, e con D-9 la chiave diventa l'email;
  da riprendere col backend.
- Captcha o altri controlli nel frontend (decisione del 2026-09-24).

## 11. Esecuzione del P-1 (2026-09-25)

### 11.1 Cosa c'è — applicato il 2026-09-25 (dbdev e scratch)

| Fase | ChangeSet | Cosa |
| --- | --- | --- |
| `00_schema/config` | `-01`, `-02` | `config.credenziali`, `config.credenziali_provenienze` |
| | `-03` | `deve_cambiare_password` = OR sulle identità **attive**, riga solo dove vale `true` |
| `20_code/script` | `-04`, `-05` | ⭐ `fn_login_parametri()` e `fn_login_attesa_secondi(…)`: building block nuovi (regola del 2, §11.2) |
| | `-06` | `fn_guard_super_admin` (D-B1) |
| | `-07`, `-08` | `fn_get_deve_cambiare_password`, `fn_imposta_deve_cambiare_password` |
| | `-09` | `fn_azzera_tentativi_credenziale(uid, provenienza DEFAULT NULL)` |
| | `-10`, `-11` | `fn_check_blocco_login(uid, provenienza)`, `fn_registra_tentativo_login(uid, provenienza, esito)` — DROP delle firme vecchie |
| | `-12`, `-13` | `fn_check_almeno_un_super_admin_attivo` **e** `fn_check_ultimo_super_admin_attivo` conoscono il blocco dell'admin |
| | `-14`, `-15` | `fn_blocca_credenziale`, `fn_sblocca_credenziale` |
| | `-16`, `-17` | `fn_get_user_profile`, `fn_get_operatore_detail` leggono il flag dalla credenziale |
| `20_code/config` | `-18` | guard anti-lockout sul blocco (`AFTER INSERT OR UPDATE OF bloccata_at`) |
| | `-19` | trigger alla nascita di `cleanup_at` sulle provenienze |
| `80_data` | `-20` | parametri 57-59 (`parameters_login.csv`, CSV dedicato) |
| | `-21` | policy indici delle tre FK (`fk_index_policy_credenziali.csv`, tutte `consentito=false`) |
| | *(CSV esistenti)* | 5 codici e messaggi (id 1122-1126): `E_AUTH_CHIAMATA_NON_VALIDA`, `E_CREDENZIALE_NON_TROVATA`, `E_CREDENZIALE_MOTIVO_OBBLIGATORIO`, `E_CREDENZIALE_BLOCCATA`, `E_LOGIN_ATTESA`; regola `CLEANUP_AT` id 21 (TTL 1 giorno) |
| `90_end` | `-22`, `-23` | FK verso `django.auth_user` (`auth_user_id` CASCADE, `bloccata_da` NO ACTION), `MARK_RAN` |
| | `-24` | la porta (+ loop `ci_apply/20260205-41` + `provision_db_roles.sql`) |
| | `-25` | ⛔ DROP delle quattro colonne da `identita_digitali` |

### 11.2 Cosa è cambiato rispetto al disegno, e perché

1. **PK `id` + `UNIQUE (auth_user_id)`** e figlia su `credenziale_id`: le linee
   guida (§2-§4) vogliono la surrogata ed evitano le chiavi composte.
2. **All'app resta il `SELECT`** (non «nessun privilegio»):
   `fn_check_almeno_un_super_admin_attivo` è `LANGUAGE sql` e la chiamano
   trigger `INVOKER` come l'app. Il modello del verbo chiude le scritture.
3. ⭐ **L'azzeramento ha un perimetro.** Trovato scrivendo il pgTAP: se un accesso
   riuscito cancellasse *tutte* le provenienze, il freno sulla macchina di chi
   attacca sparirebbe a ogni login del titolare. Accesso riuscito → la sola
   coppia; reset → tutte (la password è cambiata).
4. **Due building block in più** per la regola del 2: la lettura dei cinque
   parametri (`fn_login_parametri`, fail-loud: la versione di prima aveva
   `COALESCE(…, 5)` e `…, 15)`, il seed scritto una seconda volta nel codice) e la
   formula dell'attesa (`fn_login_attesa_secondi`), usate da check e registrazione.
5. **Anche `fn_check_ultimo_super_admin_attivo`** conosce il blocco: decide le
   capability del drawer Operatore, e se dissentisse dal guard il drawer
   offrirebbe «disabilita» che poi verrebbe rifiutato.
6. **`bloccata_da` con `ON DELETE NO ACTION`**: `SET NULL` violerebbe il CHECK
   «blocco tutto o niente», `CASCADE` toglierebbe lo stato di un'altra
   credenziale. Cancellare un admin che ha bloccato qualcuno è rifiutato finché
   il blocco c'è.
7. **I tre parametri nuovi con `storicizza = f`**, come i due fratelli (id 9, 10).

### 11.3 ⛔ Da applicare insieme alla PR del backend

Non solo il DROP (`-25`): già `-10` e `-11` tolgono le firme che il backend chiama
(`check_blocco_login(uid)`, `registra_tentativo_login(uid, esito)`). Applicato da
solo, il P-1 rompe il login su dbdev.

### 11.4 Come è stato provato (2026-09-25)

Sullo scratch `zeroerp_ci`, da owner, in transazioni ritirate: l'SQL **estratto**
dai 25 changeSet, in ordine di fase (i `loadUpdateData` e le
`addForeignKeyConstraint` resi in SQL equivalente; codici e messaggi inseriti come
righe nuove).

| Prova | Esito |
| --- | --- |
| DDL di tutti i changeSet | passa |
| `plpgsql_check` sulle 13 funzioni nuove o riscritte | 0 errori (12 avvisi «STABLE ma VOLATILE»: `fn_log_and_raise_error`, la stessa forma di `fn_get_user_profile`) |
| `config/test-credenziale-login-v1.sql` | 22/22 |
| `config/test-credenziale-blocco-admin-v1.sql` | 16/16 |
| `config/test-credenziali-porta-v1.sql` | 8/10 — ⚠️ i test 3-4 (`42501` come app) sono **rossi da owner per costruzione**: verdi solo come app |
| `config/test-credenziale-login-tempo-v1.sql` (marcato `owner`, motivo nel file) | 5/5 |
| 10 pgTAP esistenti che toccano le funzioni cambiate | identici asserzione per asserzione, con e senza il P-1 |
| cancello B-7 (famiglie dei codici) | verde: i codici nuovi hanno una famiglia sola; `E_CONFIG_MANCANTE` e `E_PERMESSO_NEGATO` restano nella loro |
| cancelli statici (runOnChange, letterali, timestamp, preCondition, trigger, grant batch, preambolo pgTAP) | verdi |

⚠️ **Non provato qui, resta a Tid**: la corsa pgTAP vera come app, e l'esito sul
database ricostruito (la porta nelle tre sedi, le FK `MARK_RAN`).

⚠️ **Il file `owner`** (`test-credenziale-login-tempo-v1.sql`): per provare «freno
scaduto» e «attesa trascorsa» la fixture deve retrodatare tabelle chiuse all'app.
Un helper `DEFINER` che lo facesse sarebbe chiamabile in esercizio e azzererebbe il
freno: meglio un test marcato che una porta aperta.

### 11.5 Trovato strada facendo, fuori perimetro

- ⚠️ **Storico di `config.parameters` rotto su un database ricostruito.** Il
  trigger `trg_parameters_z90_storico_upd_dlt` è montato con
  `trgfn_storico_generic('parameters_id')`, ma la colonna di `storico.parameters`
  è `parameter_id`: sullo scratch l'UPDATE di un parametro con `storicizza = t`
  (per esempio `SYSTEM_FUSO_ORARIO`, id 54) muore con `E_SNAPSHOT_CLOSE_ERROR`.
  Su dbdev lo stesso UPDATE passa. ➜ Analizzato in
  [brief-db-storico-colonna-fk-dei-trigger.md](brief-db-storico-colonna-fk-dei-trigger.md):
  il difetto tocca cinque tabelle, quattro anche su dbdev, ed è dbdev a essere
  fuori modello per `parameters`.
  ✅ *Presa in carico da un'altra sessione (Tid, 2026-09-25).*
- `fn_check_almeno_un_super_admin_attivo` non guarda `ruolo_applicativo =
  OPERATORE` né la finestra `valido_dal`/`valido_al`, che `fn_is_super_admin` e
  `fn_check_ultimo_super_admin_attivo` guardano: divergenza preesistente, non
  toccata.
- ⚠️ **Lo scratch ha il «ponte django» a metà, e
  `config/test-fk-auth-user-ponte-django-v1.sql` è rosso lì** (asserzioni 1 e
  2), non in CI. Il test si accende se esiste **almeno una** FK verso
  `django.auth_user`, e allora le pretende tutte. Sullo scratch, nato da zero, le
  18 FK storiche del ponte sono `MARK_RAN` (Liquibase girava prima di
  `manage.py migrate`) e non esistono; le due di questo cantiere (`-22`, `-23`)
  sono state applicate dopo, a tabella Django presente, e sono `EXECUTED`. Una
  sola FK accende il test, che trova 16 colonne scoperte. Misurato il
  2026-09-25 (fatto datato, non motivo):

  | Database | FK del ponte | Test |
  | --- | --- | --- |
  | CI, da zero | nessuna (tutte `MARK_RAN`, anche `-22`/`-23`) | 3 `skip` |
  | dbdev | tutte (23) | verde |
  | scratch | 1 di 17 sulle colonne del test | **rosso** |

  Non è un difetto del P-1 né del test (fa ciò per cui è scritto: «se una c'è e
  le altre no, è rosso»): è lo stato di una macchina. Rimedio proposto: sullo
  scratch togliere da `databasechangelog` le righe `MARK_RAN` del ponte e
  rilanciare il migrate, così le FK nascono come su dbdev. ⏳ Da fare (Tid).
- ❓ **La domanda di forma che c'è sotto — per Tid.** Con `onFail: MARK_RAN` una
  FK verso Django su un'**installazione nuova non nasce mai**: il changeSet si
  segna prima che la tabella esista e non si riprova. È la stessa ragione per cui
  l'indice sull'email (D-B5) usa `onFail: CONTINUE`, che salta senza segnare e
  riprova al migrate successivo. Da valutare se portare a `CONTINUE` tutte le FK
  del ponte (le 18 storiche e `-22`/`-23`): sarebbe un cambio della forma di
  casa, fuori da questo brief. I changeSet del P-1 restano nella forma di casa.

### 11.6 Cosa resta

- ✅ Tid: P-1 applicato (2026-09-25). ⏳ Corsa pgTAP; scratch da riallineare
  sul ponte (§11.5).
- Backend: §7.
- DB: il **P-2** (§5) → §12.
- ⛔ **P-2, trovato dalla corsa pgTAP del 2026-09-25: un operatore SUPER_ADMIN
  non si può più creare.** `20260925-42` fa nascere la veste OPERATORE spenta
  (`fn_crea_risorsa_umana_v2(…, p_attivo := false)`), ma la stessa funzione
  scrive il binding SUPER_ADMIN in `config.profili_accesso_bindings` con
  `attivo = true`, sempre. Il binding è figlio della veste, e la regola ATTIVO
  (`trgfn_child_requires_active_parent`, differita) lo rifiuta: *«Padre non
  attivo: figlio attivo non consentito»* (`E_ATTIVO_REQUIRE`).
  - **Non è un difetto del test**: la regola scatta al `COMMIT`, quindi muore
    anche la creazione dal pannello. Nel pgTAP scatta al
    `SET CONSTRAINTS ALL IMMEDIATE` di `dbops.fn_pgtap_crea_operatore_umano`.
  - Riprodotto il 2026-09-25 su dbdev come applicazione, in rollback: con
    `p_super_admin = false` l'operatore nasce, con `true` muore.
  - Tocca **ogni** pgTAP che costruisce un super admin con quell'helper:
    `config/test-credenziale-blocco-admin-v1`, `script/test-fn-get-operatore-detail`,
    `script/test-permessi-funzioni-risoluzione`,
    `script/test-fn-check-ultimo-super-admin-attivo`, `script/test-fn-is-super-admin`,
    `anagrafiche/test-billing-account-auto-link-ef`,
    `anagrafiche/test-guard-albero-ba-omogeneo-v1`.
  - ⛔ **Il rimedio NON è nell'helper.** Accendere la veste prima del
    `SET CONSTRAINTS ALL IMMEDIATE` farebbe tornare verdi i test e lascerebbe
    rotta la creazione vera.
  - ❓ **Decisione per Tid: che cosa diventa il binding di un invito.** (a) Nasce
    spento con la veste, e l'attivazione dell'invito accende veste **e** binding
    creati dall'invito. Ma una riattivazione generica non deve riaccendere un
    binding che un admin ha spento: serve distinguerli. (b) Il binding
    SUPER_ADMIN non nasce all'invito ma all'attivazione, e l'invito ne porta
    l'intenzione. (c) Il binding di una veste spenta è ammesso: vuol dire
    toccare la regola ATTIVO per quel figlio, e il binding di una veste spenta
    non concede niente solo se ogni lettore guarda anche la veste
    (`fn_is_super_admin` la guarda).
  - ✅ **Decisa da Tid il 2026-09-25: la (c), «sganciare porta e profili».**
    Scritta e provata in `20260925-46…-50`: §12.3.

## 12. Esecuzione del P-2 (2026-09-25)

### 12.1 Cosa c'è

| Fase | ChangeSet | Cosa | Stato |
| --- | --- | --- | --- |
| `20_code/script` | `-40` | ⭐ `fn_get_auth_user_id_for_email(p_email)`: la credenziale di un'email, **senza maiuscole**; email vuota → `NULL`; due credenziali con la stessa email → `E_CREDENZIALE_EMAIL_AMBIGUA` (building block, regola del 2) | applicato |
| `20_code/anagrafiche` | `-41` | `fn_crea_auth_user`: il guard dell'email chiede al building block (`E_ADMIN_EMAIL_DUPLICATA` invariato) | applicato |
| | `-42` | la madre `fn_crea_operatore_v2`: riusa la credenziale (D-6), veste OPERATORE **sempre spenta** (R-2), rifiuto `E_CREDENZIALE_GIA_OPERATORE`; `p_attivo` esce, ritorno `TABLE(auth_user_id, username, credenziale_riusata)` — `DROP` + `CREATE` | applicato |
| `20_code/script` | `-43` | `fn_check_operatore_invitabile` sulla regola unica (R-1, D-8): invitabile chi ha la veste **spenta**; via `last_login`, `is_active`, il ramo `DISABILITATO` morto | applicato |
| `20_code/dbops` | `-45` | il builder pgTAP legge la `TABLE` e fa il passo dell'attivazione (accende la veste) | applicato |
| `90_end` | `-44` | indice unico `ix_auth_user_email_lower_unique` su `lower(email)` `WHERE email <> ''`, `onFail: CONTINUE`; **ritira** `ix_auth_user_email_unique` (`20260401-20`, distingueva le maiuscole: contenuto nel nuovo) | applicato |
| `00_schema/dbops` | `-46` | registro `dbops.automazione_attivo_eccezioni` (§12.3) | applicato |
| `20_code/dbops` | `-47`, `-48` | `fn_ritira_attivo_eccezioni()`; il motore `fn_run_automations_attivo` salta le eccezioni e ritira | applicato |
| `80_data` | `-49` | mirror del registro, prima riga: binding → identità | applicato |
| `90_end` | `-50` | ritiro una tantum (su dbdev i trigger ci sono già) | applicato |
| *(CSV esistenti)* | — | codici 1130 `E_CREDENZIALE_EMAIL_AMBIGUA` (TECNICO), 1131 `E_CREDENZIALE_GIA_OPERATORE` (CONFLITTO_STATO) | applicati |

⚠️ La numerazione salta da `-27` a `-40`: dal `-26` in su lavorava in parallelo
il cantiere storico (`brief-db-storico-colonna-fk-dei-trigger`), e ho lasciato
`-28…-39` a lui.

### 12.2 Cosa è cambiato rispetto al disegno (§5), e perché

1. ⭐ **Dentro anche R-1 e R-2 del piano BE/FE.** Il §5.2 chiedeva la veste
   spenta **solo** sulla credenziale riusata. Ma il check dell'invito voleva
   la veste **attiva** e `is_active = true`: l'operatore riusato non sarebbe
   mai stato invitabile, e l'invito è l'unico modo di accenderlo. E due
   comportamenti a seconda che la credenziale esista già sono due cicli di
   vita, contro la regola unica decisa (analisi §4.2). Quindi: veste spenta
   **sempre** (R-2), check rovesciato (R-1). R-3 (lo username nel template
   dell'invito) resta al lotto L-4: tocca le variabili che passa il backend.
2. **Il rifiuto è su una veste OPERATORE attiva *o spenta***, non solo attiva.
   Con la veste che nasce spenta l'unique `WHERE attivo` alla creazione non
   scatta mai: il duplicato passerebbe e scoppierebbe all'attivazione. E una
   veste spenta è un invito pendente o un operatore disattivato: il rimedio è
   il reinvito (D-3). Le vesti `DISABILITATO` non contano (R-5 le ritira).
3. **I guard di username e password escono dalla madre**: erano copie di quelli
   di `fn_crea_auth_user`, e sulla credenziale riusata sarebbero sbagliati.
4. **Un building block per «la credenziale di un'email»**: la regola viveva in
   `fn_crea_auth_user` (con le maiuscole), nel backend (`portale_repository`,
   senza) e ora nella madre.
5. **L'indice ritira il suo predecessore** (`ix_auth_user_email_unique`, che
   nessuno citava), e ha una sola `preCondition` (la tabella): con
   `onFail: CONTINUE`, una seconda «l'indice non esiste» falsa lascerebbe il
   changeSet pendente per sempre. L'idempotenza la danno i `IF (NOT) EXISTS`.
6. **Le email doppie non si scelgono**: dove l'indice non c'è (CI), il building
   block solleva `E_CREDENZIALE_EMAIL_AMBIGUA` invece di prendere la prima.
7. `FOR UPDATE` sulla credenziale riusata, prima del controllo delle vesti: due
   creazioni sulla stessa persona si serializzano.

### 12.3 ⭐ Porta e profili (decisione di Tid, 2026-09-25)

**Il difetto.** Con la veste spenta, il binding SUPER_ADMIN nasceva attivo
sotto un'identità spenta, e l'automazione ATTIVO — che lega
`config.profili_accesso_bindings` a `anagrafiche.identita_digitali` in tutti e
due i versi — lo rifiutava al `COMMIT`. Trovato in due posti lo stesso giorno:
dalla prova pre-apply (`test-fn-get-operatore-detail`) e dalla corsa pgTAP di
Tid (§11.6). ⚠️ Non dipendeva da R-2: anche il P-2 letterale del brief ci
inciampava, sulla credenziale riusata. E con R-2 si sarebbe rotto anche
assegnare **un profilo qualsiasi** a un operatore che non ha ancora accettato
l'invito.

**La decisione.** La veste attiva dice se la porta è aperta; il binding dice
cosa si può fare dentro. Sono due domande, e i lettori dei permessi le chiedono
già entrambe (verificato sui corpi: `fn_is_super_admin`,
`fn_get_profili_accesso_applicabili`, `fn_check_almeno_un_super_admin_attivo`,
`fn_check_ultimo_super_admin_attivo`). Quindi la coppia **esce dall'ATTIVO**.
Guadagno collaterale: spegnere una veste non chiede più di spegnere prima i
profili, e il reinvito (D-3) la riaccende con i profili che aveva.

**La forma.** L'automazione non sapeva escludere una FK: il filtro esistente è
per tabella, e toglierebbe anche le coppie giuste di `profili_accesso_bindings`
(profili, unità organizzative). La guida lo diceva: rimettere un'esclusione per
FK è «ricreare la tabella **e** il `NOT EXISTS` nel cursor — un cantiere».

- `dbops.automazione_attivo_eccezioni` (`-46`): una FK per riga, **motivo
  obbligatorio**; seed dal CSV (`-49`);
- `dbops.fn_ritira_attivo_eccezioni()` (`-47`): toglie i trigger già generati,
  riconoscendoli per **funzione e argomenti** (i nomi sono hashati);
- il motore (`-48`) salta le coppie a registro e, in testa a ogni giro, chiama
  il ritiro: chi genera ritira;
- `90_end/-50` chiama il ritiro una volta, perché su dbdev il job delle
  automazioni gira solo la sera.

⚠️ **Non toccata**: la coppia gemella `identita_scope_bindings` →
`identita_digitali`. Ha lo stesso legame ma oggi nessuna funzione né vista la
legge o la scrive (solo il model Django e un backfill di aprile). Se diventerà
viva, la domanda è la stessa, e la risposta è una riga nel registro.

### 12.4 ⛔ Cosa chiede al backend (in aggiunta al §7)

Su dbdev `-40…-45` **sono già applicati**: finché il backend non è allineato,
la creazione dell'operatore dal pannello è rotta (passa `p_attivo`, legge un
`integer`), e l'invito operatore segue la regola nuova.

| # | Dove | Cosa |
| --- | --- | --- |
| B-1 | `amm_software_repository.crea_operatore` | senza `p_attivo`; `SELECT * FROM anagrafiche.fn_crea_operatore_v2(…)`; con `credenziale_riusata = true` la password dell'admin è **ignorata** e lo username è quello restituito: la risposta e l'`OperatoreDrawer` devono dirlo (§5.2 ricaduta 1) |
| B-2 | invito e attivazione operatore (L-3) | l'invito non sovrascrive la password (A-1); l'**attivazione accende la veste** (A-3): senza, l'operatore creato non entra mai. `fn_check_operatore_invitabile` risponde già con la regola nuova: `motivo` nuovo `Veste OPERATORE gia' attiva`; spariti `Utente ha gia' effettuato login`, `Identita OPERATORE non attiva`, `Utente disattivato (is_active=false)` — ⚠️ `core/tests/services/test_invito_operatore.py:96` usa il testo vecchio in un mock |
| B-3 | `PortaleRepository` (`portale_repository.py:114`) | la ricerca della credenziale per email chiama `script.fn_get_auth_user_id_for_email` invece di `LOWER(email) = LOWER(%s) LIMIT 1` (regola del 2; e il `LIMIT 1` sceglie a caso fra due credenziali) |
| B-4 | codici | `E_CREDENZIALE_GIA_OPERATORE` (409, `campo = email`), `E_CREDENZIALE_EMAIL_AMBIGUA` (500): rigenerare `error_policies_generated.py` ed `error_messages_fallback.py` |
| B-5 | `disabilita_operatore` | dopo `-50` spegnere una veste con binding attivi non è più respinto dal guard generico; l'ultimo SUPER_ADMIN lo protegge `E_PROFILO_ULTIMO_SUPER_ADMIN` |

### 12.5 Come è stato provato

Sullo scratch `zeroerp_ci`, da owner, in transazioni ritirate, con l'SQL
**estratto** dai changeSet (la riga del seed `-49` generata dal CSV).

| Prova | Esito |
| --- | --- |
| DDL `-40…-45` + codici (prima dell'apply di Tid) | passa; `plpgsql_check` 0 errori (avvisi: `STABLE` con `fn_log_and_raise_error`, come nel P-1; `v_ru_id` mai letto, preesistente) |
| DDL `-46…-50` | passa; il ritiro toglie **esattamente** i due trigger della coppia, al secondo giro 0; il motore vero su `config`/`anagrafiche` non li rigenera; `plpgsql_check` 0 errori |
| pgTAP nuovi: `test-credenziale-email-unica-v1` (9, uno saltato per ramo), `test-crea-operatore-riusa-credenziale-v1` (13), `test-automazione-attivo-eccezioni-v1` (8) | verdi |
| pgTAP adeguati: `test-fn-crea-operatore` (12), `test-risorse-umane-guard-identita-attiva-v1` (8), `test-fn-check-operatore-invitabile` (11, riscritto: costruisce il suo operatore), `test-fn-get-operatore-detail` (4), `test-fn-is-super-admin` (8), `test-profili-accesso-guard-ultimo-super-admin` (3) | verdi |
| pgTAP della tua lista §11.6 (super admin dal builder): `test-credenziale-blocco-admin-v1` (16), `test-permessi-funzioni-risoluzione` (34), `test-fn-check-ultimo-super-admin-attivo` (5), `test-billing-account-auto-link-ef` (4), `test-guard-albero-ba-omogeneo-v1` (12) | verdi dietro `-46…-50`, nessuna modifica |
| cancelli statici (runOnChange, letterali, preCondition, trigger, grant batch, timestamp, preambolo pgTAP) | verdi |

✅ **Dopo l'apply (Tid, 2026-09-25)**: `-40…-50` applicati su dbdev e scratch;
**corsa pgTAP senza regressioni**. ⚠️ Una correzione di Tid a
`test-automazione-attivo-eccezioni-v1` prima della corsa: il nome della tabella
si componeva con `tgrelid::regclass::text`, che dipende dal `search_path` — come
app, con `config` nel path, esce senza schema, e il test 4 era rosso (il 2 verde
per coincidenza). Nella prova da owner, senza `config` nel path, il difetto non
si vedeva: ora il nome si compone dal catalogo (`nspname || '.' || relname`).
⚠️ Resta il rosso **dello scratch** su `config/test-fk-auth-user-ponte-django-v1`:
non è del P-2 (nessun changeSet `-40…-50` tocca FK verso `django.auth_user`), è
il ponte a metà del §11.5.
⏳ Non ancora visti: il cancello B-7 (`codici-errore-baseline.sh`) e l'esito in
CI (soprattutto `-44`, che lì salta per costruzione).

**Due correzioni ai test dopo l'apply di `-40…-45`**, da errori miei nei file
(non nei changeSet): la forma testuale dell'indice nel test 5 di
`test-credenziale-email-unica-v1` (`pg_get_indexdef` chiude con `''::text)`),
e in `test-crea-operatore-riusa-credenziale-v1` la credenziale riletta nella
stessa istruzione che la scrive (snapshot di prima). Le versioni corrette sono
quelle verdi della tabella.

### 12.6 Cosa resta

- ✅ Tid: `-40…-50` applicati, corsa pgTAP senza regressioni (2026-09-25).
  ⏳ B-7; scratch da riallineare sul ponte django (§11.5).
- Backend: §7 e §12.4 (lotto L-3; R-3 con L-4).
- Guida `architettura-multi-face-auth` §3.1 (del backend, §8), con la veste che
  nasce spenta e porta/profili sganciati.

## Registro

| Data | Chi | Cosa |
| --- | --- | --- |
| 2026-09-24 | BE | Prima versione: contatore e blocco sulla credenziale (D-1, D-2, D-7) |
| 2026-09-24 | DB | Analisi critica: forma della riga da chiudere, backend senza SQL diretto sulla tabella, azzeramento in un posto solo, `%TYPE`, lettore mancante (`find_identita_portale`), storico e trigger di `identita_digitali` a ogni fallimento, blocco usabile da uno sconosciuto |
| 2026-09-24 | BE | Aggiunti D-6, D-9, D-10 (§2.5–§2.6 e test 9–10 della prima versione), su `Tito-dev` |
| 2026-09-24 | Tid | D-1 riletta: blocco vero solo come atto autorizzato; freno automatico sulla coppia credenziale + provenienza; oltre il tetto attesa crescente, solo DB e backend. Brief riscritto (§2–§8) |
| 2026-09-24 | DB | Fusione dopo il fast forward su `Tito-dev`: le aggiunte del BE entrano nella forma nuova come P-2 (§5), con tre correzioni — email vuota `''` e non `NULL`; indice su tabella Django che in CI non esisterebbe (D-B5); le tre ricadute del riuso (password dell'admin, sovrascrittura all'invito, attivazione che accende la veste). FK verso `django.auth_user` nella forma di casa (`90_end` + `MARK_RAN`) |
| 2026-09-24 | Tid | D-B1…D-B5 decise come proposto. D-B5: l'indice sull'email è una migration Django, quindi lavoro del backend (§7); il DB fa il guard di `fn_crea_auth_user` e i test |
| 2026-09-24 | Tid | ⚠️ D-B5 **corretta**: nessuna migration Django nel progetto, il DDL è Liquibase → `90_end` con `onFail: CONTINUE`, team DB. D-B1 riaperta: l'area indicata (`amm_software`) non è un'area del catalogo |
| 2026-09-24 | Tid | D-B1 decisa: blocco e sblocco solo da SUPER_ADMIN (la regola di `amm_software`); building block `fn_guard_super_admin`, per regola del 2 (due verbi) |
| 2026-09-24 | BE | §2.4: classe dei due codici nuovi `NON_PERMESSO` (403), non 429 — la classe non esiste e il login FE intercetta il 429 prima del codice |
| 2026-09-25 | DB | **P-1 scritto e provato** (§11): 25 changeSet `20260925-01…-25`, 4 pgTAP, manual. Correzioni al disegno: PK `id`, `SELECT` all'app, azzeramento per perimetro, due building block in più, anche `fn_check_ultimo_super_admin_attivo`, parametri `storicizza = f`. Non applicato |
| 2026-09-25 | Tid | P-1 applicato su dbdev e scratch. Sullo scratch `test-fk-auth-user-ponte-django-v1` rosso: ponte django a metà (§11.5), rimedio sulla macchina e domanda su `MARK_RAN` → `CONTINUE` |
| 2026-09-25 | DB | **P-2 scritto** (§12): `20260925-40…-45`, con dentro R-1 e R-2 del piano BE/FE (§12.2); codici 1130-1131; 2 pgTAP nuovi, 4 adeguati. Tid applica `-40…-45` durante la prova |
| 2026-09-25 | DB + Tid | Binding SUPER_ADMIN su veste spenta rifiutato dall'ATTIVO (trovato dalla prova pre-apply e dalla corsa di Tid, §11.6). Tid decide: **porta e profili si sganciano**. Scritti e provati `-46…-50` (registro delle eccezioni ATTIVO, ritiro per funzione e argomenti, motore, seed, ritiro una tantum); adeguati `test-fn-is-super-admin` (caso 6) e `test-profili-accesso-guard-ultimo-super-admin` (caso 3). Non applicati |
| 2026-09-25 | Tid | `-40…-50` applicati su dbdev e scratch; commit `acc6385d5`. Corretto `test-automazione-attivo-eccezioni-v1` (nome tabella da `regclass::text`, dipendente dal `search_path`). Corsa pgTAP **senza regressioni** (§12.5) |

---
{% include-markdown "signature-core.md" %}
