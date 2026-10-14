# Brief DB — La credenziale: tentativi di login, blocco, cambio password obbligatorio, email unica

> **Tipo documento**: brief operativo **per il team DB** (`dev/db-tid`), con la
> ricaduta sul backend al §7.
>
> **Data**: 2026-09-24 · **Stato**: ✅ **CHIUSO il 2026-09-27.** P-1, P-2,
> R-8, R-9, R-7, R-3 e §16 applicati e committati — P-1 `20260925-01…-25`
> (`f96d087d4`), P-2 `-40…-51` (`acc6385d5`, `64a1ad2f4`), R-8 `-52`
> (`48291b801`), R-9/R-7 `-53…-62` e i template R-3 (`7f3208a58`), §16
> `20260927-01`, `-02` (`e3d188dc0`); backend e frontend B-8…B-19, F-1…F-3 e la
> guida `architettura-multi-face-auth` §3.1 (`e7dbbad73`, `854ca3c2b`).
> ➜ **Scorporato** l'unico lavoro aperto, il §17 (i dati del dialog del
> consenso al riuso: B-6 a metà, B-20, F-4, più il controllo a video di F-3), in
> [brief-db-credenziale-per-email.md](brief-db-credenziale-per-email.md).
> La domanda sulle FK del ponte django (§11.5) è in `PROJECT_CONTEXT` § «Aperto —
> Media priorità».
> 🟢 Dopo lo scorporo il team DB ha fatto il lato DB del §17
> (`20260927-40`, `-41`, applicati il 2026-09-27): l'esecuzione (§17.4) è nel
> brief nuovo. Restano al backend e al frontend B-20 e F-4, là.
>
> **Due lavori, in quest'ordine**: **P-1** login, blocco e cambio password
> (§2–§4); **P-2** email unica e riuso della credenziale (§5). Sono
> indipendenti nel codice, ma il P-2 cambia il modo in cui nascono le credenziali
> di cui il P-1 tiene lo stato: si fanno nello stesso cantiere.
>
> **Origine**: difetto M-4 di
> [analisi-be-difetti-emersi-verifica-doc-api-core.md](../work-done/analisi-be-difetti-emersi-verifica-doc-api-core.md),
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
  rilanciare il migrate, così le FK nascono come su dbdev. ✅ Fatto (Tid,
  2026-09-25): scratch riallineato, test verde.
- ❓ **La domanda di forma che c'è sotto — per Tid.** Con `onFail: MARK_RAN` una
  FK verso Django su un'**installazione nuova non nasce mai**: il changeSet si
  segna prima che la tabella esista e non si riprova. È la stessa ragione per cui
  l'indice sull'email (D-B5) usa `onFail: CONTINUE`, che salta senza segnare e
  riprova al migrate successivo. Da valutare se portare a `CONTINUE` tutte le FK
  del ponte (le 18 storiche e `-22`/`-23`): sarebbe un cambio della forma di
  casa, fuori da questo brief. I changeSet del P-1 restano nella forma di casa.

### 11.6 Cosa resta

- ✅ Tid: P-1 applicato (2026-09-25); corsa pgTAP verde; scratch riallineato
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
| `20_code/anagrafiche` | `-51` | la madre: rifiuto `E_CREDENZIALE_ALTRA_PERSONA` dove la persona è provabile; consenso dichiarato `p_riusa_auth_user_id`, altrimenti `E_CREDENZIALE_DA_CONFERMARE` (§12.7). Il parametro è **in coda, `DEFAULT NULL`**: i 17 di prima restano identici. `DROP` + `CREATE` perché per PostgreSQL un parametro in più è un'altra funzione, e con la vecchia viva una chiamata per nome che lo omette sarebbe ambigua («la funzione non è unica») | applicato |
| *(CSV esistenti)* | — | codici 1132 `E_CREDENZIALE_ALTRA_PERSONA` (DATO_ERRATO), 1133 `E_CREDENZIALE_DA_CONFERMARE` (CONFLITTO_STATO) | applicati |
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
| B-6 | `crea_operatore` + `OperatoreDrawer` (§12.7, dopo `-51`) | la prima chiamata **senza** `p_riusa_auth_user_id`; su `E_CREDENZIALE_DA_CONFERMARE` il dialog mostra dal contesto `username` e `vesti` della credenziale trovata e, confermato, rimanda **con** `p_riusa_auth_user_id := <auth_user_id del contesto>`. `E_CREDENZIALE_ALTRA_PERSONA` (400, `campo = email`) non si conferma: si corregge l'email. Codici da rigenerare con gli altri (B-4) |
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
Il rosso **dello scratch** su `config/test-fk-auth-user-ponte-django-v1` non era
del P-2 (nessun changeSet `-40…-50` tocca FK verso `django.auth_user`), era il
ponte a metà del §11.5: ✅ scratch riallineato da Tid, test verde.
✅ **Cancello B-7 verde (2026-09-25, dopo l'apply di `-40…-51`)**: lo scatto
(`scripts/sql/codici_errore_famiglie_snapshot.sql`, in sola lettura come app) è
identico su scratch e dbdev, e contro la baseline committata dà **0 accumuli e
0 codici nati generici**. I codici del cantiere entrano con una famiglia sola:
`E_AUTH_CHIAMATA_NON_VALIDA` (`PARAMETRO`), `E_CREDENZIALE_MOTIVO_OBBLIGATORIO`
(`PARAMETRO`); `E_PERMESSO_NEGATO` diventa leggibile da `fn_guard_super_admin`
con la sola `PARAMETRO`. ⚠️ Blu da allineare (`--update`), **non di questo
cantiere**: nuovi a una famiglia `E_DATE_VALIDITA`, `E_DOC_PREZZO_PENDENTE`,
`E_DOC_PREZZO_RIFIUTATO`; ristretto `E_DELETE_NOT_ALLOWED` (perde `ENUM`);
rientrati `E_COMPONENTE_PREZZO_PENDENTE`, `E_DELETE_RIGA_DOC_NON_BOZZA` — dai
changeSet del 22-24 settembre, la baseline era ferma al 18. ✅ Baseline allineata
da Tid (2026-09-25).
⏳ Non ancora visto: l'esito in CI (soprattutto `-44`, che lì salta per
costruzione).

**Due correzioni ai test dopo l'apply di `-40…-45`**, da errori miei nei file
(non nei changeSet): la forma testuale dell'indice nel test 5 di
`test-credenziale-email-unica-v1` (`pg_get_indexdef` chiude con `''::text)`),
e in `test-crea-operatore-riusa-credenziale-v1` la credenziale riletta nella
stessa istruzione che la scrive (snapshot di prima). Le versioni corrette sono
quelle verdi della tabella.

### 12.7 ❓ Domanda del backend (2026-09-25): il riuso per sola email

**Il rilievo (BE).** La madre riusa la credenziale in base alla **sola email**, e
non controlla che il soggetto dell'operatore sia la persona delle vesti che
quella credenziale ha già. Un'email sbagliata collega la veste OPERATORE alla
credenziale di un altro. Prima l'email già in uso fermava tutto
(`E_ADMIN_EMAIL_DUPLICATA`); oggi resta l'avviso «credenziale riusata», che
arriva **dopo** la scrittura.

**Cosa il modello sa dire** (il guard di coerenza chiede alle vesti portale e
shop il solo ruolo `CL`: il cliente può essere una persona fisica o un'azienda):

| La credenziale trovata ha… | «Stessa persona?» |
| --- | --- |
| una veste su un soggetto **persona fisica** | decidibile: il soggetto dell'operatore dev'essere quello (flusso B) o avere lo stesso CF (flusso A) |
| solo vesti su un soggetto **azienda** | non decidibile: niente lega la credenziale a una persona fisica |
| nessuna veste | non decidibile |

⚠️ Nel primo caso il flusso A non arriva mai al riuso:
`fn_crea_soggetto_pf` rifiuta il CF già presente (`E_ADMIN_CF_DUPLICATO`). La
stessa persona si fa operatore solo col flusso B, sul suo soggetto; il riuso con
un soggetto **diverso** è quindi il caso sospetto per costruzione.

✅ **Decisa da Tid il 2026-09-25: entrambe le difese, a DB** (la
raccomandazione). Scritta in `20260925-51`, codici 1132-1133, pgTAP
`test-crea-operatore-riusa-credenziale-v1` casi 14-20; ricaduta sul backend in
§12.4 (B-6). ✅ **Applicata il 2026-09-25** su dbdev e scratch, corsa pgTAP di
Tid verde.

**Proposta DB** (così com'era stata scritta; la forma finale è sotto,
«In esecuzione»):

1. **rifiuto dove è provabile**: veste su un soggetto persona fisica diverso da
   quello dell'operatore → codice nuovo (per esempio
   `E_CREDENZIALE_ALTRA_PERSONA`);
2. **consenso esplicito nella madre** per i casi non decidibili:
   `p_riusa_credenziale boolean DEFAULT false`. Se la credenziale esiste e il
   parametro è `false` → rifiuto «da confermare», con username e vesti della
   credenziale nel contesto per il dialog; il frontend conferma e rimanda con
   `true`. ⭐ Il default torna a essere «fermarsi prima di scrivere», e la
   decisione sta nella stessa istruzione che scrive: nessuna distanza fra il
   controllo e la scrittura, come succederebbe con una conferma solo FE/BE.
   Esporre le vesti di un'altra credenziale è accettabile su una porta per soli
   SUPER_ADMIN.

Costo: un changeSet sulla madre (firma nuova: `DROP` + `CREATE`), uno o due
codici, un pgTAP; lato BE il dialog e il secondo invio (lotto L-3).

**In esecuzione (`-51`), cosa è cambiato rispetto alla proposta:**

1. ⭐ **Il consenso è un id, non un booleano**: `p_riusa_auth_user_id` =
   la credenziale che l'admin ha visto nel dialog, e la madre pretende che sia
   quella trovata (`NULL` se l'email è nuova). Un «sì» non dice *a cosa*;
   l'id sì, e una credenziale cambiata o sparita fra il dialog e l'invio ferma
   di nuovo. Stampo della dichiarazione di `pagamenti.fn_posta_contabile` (D13,
   `E_CONTABILE_DICHIARAZIONE_NON_CORRISPONDE`).
2. **L'ordine**: «già operatore» → «altra persona» (passo 1) → soggetto
   (passo 2: i rifiuti definitivi del flusso A, fra cui il CF già presente)
   → consenso (passo 2-bis). L'admin non conferma mai qualcosa che sarebbe
   rifiutato comunque.
3. **Classi**: `E_CREDENZIALE_ALTRA_PERSONA` è `DATO_ERRATO` (rimedia chi compila:
   l'email è sbagliata); `E_CREDENZIALE_DA_CONFERMARE` è `CONFLITTO_STATO` come la
   dichiarazione contabile. Il contesto del secondo porta `auth_user_id`,
   `username`, `vesti` (ruolo, attivo, denominazione del soggetto).
4. **Provato** sullo scratch con l'SQL estratto (`-40…-50` già applicati):
   `plpgsql_check` 0 errori; `test-crea-operatore-riusa-credenziale-v1` 20/20;
   `test-fn-crea-operatore` 12, `test-fn-check-operatore-invitabile` 11,
   `test-automazione-attivo-eccezioni-v1` 8,
   `test-risorse-umane-guard-identita-attiva-v1` 8,
   `test-fn-get-operatore-detail` 4, `test-fn-is-super-admin` 8 — verdi, senza
   modifiche (usano email nuove, o si fermano prima sul «già operatore»).
   Cancelli statici verdi. ⚠️ Nel pgTAP i casi di consenso nel flusso A
   chiedono la finestra differita: la madre crea il soggetto prima del
   controllo, e con `IMMEDIATE` parlerebbe il guard degli indirizzi (in
   esercizio scatta al `COMMIT`).

### 12.8 Le note del backend su `E_UTENTE_BLOCCATO` (R-8 del piano BE/FE)

**Le due note** (Registro, BE 2026-09-25; `piano-be-fe-accessi-credenziale-e-vesti`
§3.1 e R-8, approvata da Tid): (1) la frase è chiusa, quindi i minuti del freno
restano nel contesto e non arrivano a chi prova; (2) «Account temporaneamente
bloccato» descrive un blocco dell'account, mentre dal `-10` il freno riguarda la
sola coppia credenziale + provenienza, e da un'altra postazione si entra.

**Cosa è scritto** — `20260925-52` e il catalogo:

| Dove | Cosa |
| --- | --- |
| `20_code/script/20260925-52` | `fn_check_blocco_login`: il raise del freno passa i minuti come valore (`VARIADIC ARRAY[v_rimanenti::text]`), come quello di `E_LOGIN_ATTESA` passa i secondi. Corpo del `-10` dalla doc auto-gen, firma invariata (`CREATE OR REPLACE`) |
| `messaggi_errore.csv` (id 761) | «Troppi tentativi non riusciti da questa postazione: riprovare fra %s minuti.», con causa e soluzione nuove (prima vuote) |
| `codici_errore.csv` | la descrizione dice che il segnaposto sono i minuti |
| pgTAP `test-credenziale-login-v1` | test 3 con `throws_matching` su `riprovare fra [0-9]+ minuti`: un `%s` rimasto letterale sarebbe rosso (un `LIKE` lo lascerebbe passare) |
| `manual/fn_check_blocco_login` | riga del freno e Storia |

⚠️ **Rispetto al testo di R-8.** R-8 proponeva una frase chiusa («…accesso
sospeso per qualche minuto.»). Qui c'è la forma coi minuti, che il BE indicava
come alternativa («servirebbe un `%s`… se la si vuole»): è la forma che il §2.4
chiedeva dall'inizio («con i minuti rimanenti») ed è la stessa del gemello
`E_LOGIN_ATTESA`. ✅ Tid ha applicato il `-52` (2026-09-25): resta la forma coi
minuti.

⚠️ **Ordine con il messaggio.** Il `%s` entra da `80_data`, che gira dopo
`20_code`: il valore in più senza segnaposto è innocuo. L'ordine opposto (`%s`
senza valore) non alza `22023`: `fn_log_and_raise_error` salta `format()` e il
`%s` esce **letterale** (è il presidio 4 di `test-catalogo-messaggi-errore-completo`).

**Come è stato provato (2026-09-25).** Sullo scratch `zeroerp_ci`, da owner, in
transazioni ritirate, con l'SQL estratto dal `-52` e la riga 761 aggiornata come
la scrive il CSV: `plpgsql_check` 0 errori; `test-credenziale-login-v1` 22/22;
`test-catalogo-messaggi-errore-completo` 7/7. **Controprova**: messaggio nuovo
e funzione vecchia → test 3 rosso, con il `%s` letterale nel messaggio. Cancelli
statici verdi. B-7 non cambia: nessuna famiglia di condizione toccata.
✅ **Applicato da Tid il 2026-09-25, corsa pgTAP senza regressioni.**

**Cosa chiede a BE e FE** — ⏳ da fare ora che il `-52` è applicato (non prima:
il ripiego non va avanti al catalogo):

| # | Dove | Cosa |
| --- | --- | --- |
| B-8 | `error_messages_fallback.py` | rigenerare: il ripiego di `E_UTENTE_BLOCCATO` diventa la frase nuova |
| F-1 | `LoginView.resolveLoginError` | `E_UTENTE_BLOCCATO` passa da `ERROR_CODE_MAP` (chiave i18n) ai rifiuti che mostrano il `message` del DB, come `E_LOGIN_ATTESA`, con `auth.account_locked` come ripiego. Aggiornare il commento, che dice «frase chiusa» |

### 12.6 Cosa resta

- ✅ Tid: `-40…-51` e i codici applicati, corse pgTAP verdi (2026-09-25).
  ✅ B-7 verde (§12.5), baseline allineata; `-51` committato (`64a1ad2f4`);
  scratch riallineato sul ponte django (§11.5), tutti i test verdi.
- ❓ Aperta per Tid, fuori da questo brief: le FK del ponte django da
  `MARK_RAN` a `CONTINUE` (§11.5). ➜ Registrata in `PROJECT_CONTEXT` §
  «Aperto — Media priorità» alla chiusura (2026-09-27).
- ✅ DB: le due note del backend su `E_UTENTE_BLOCCATO` (R-8) → §12.8: `-52`
  applicato (Tid, 2026-09-25), nessuna regressione; committato (`48291b801`).
- ✅ DB: **R-9** (§14, `-53`, `-54`), **R-7** (§13, `-55…-62`) e **R-3** (§15,
  template) applicati su dbdev il 2026-09-25 e committati (`7f3208a58`).
- ✅ Backend: B-9…B-16 e F-2 committati (`e7dbbad73`).
- ✅ **DB: §16** — i motivi del dettaglio operatore diventano codici macchina
  con la chiave i18n. ✅ Decisioni di Tid (2026-09-27): `motivo` ritirato, nomi
  dei campi invariati con `_reason_key` accanto. `20260927-01`, `-02`
  ✅ applicati (Tid, 2026-09-27), test verdi (§16.3).
- ✅ Backend/Frontend: **B-17…B-19** e **F-3** (§16.4), 2026-09-27 (dettaglio
  nel Registro). ➜ Il controllo a video di F-3 (§16.4, ultima nota) è passato
  al brief scorporato del §17.
- ✅ Backend/Frontend: **B-8** e **F-1** (§12.8), 2026-09-27: ripiego senza
  `%s`, `E_UTENTE_BLOCCATO` fra i rifiuti che mostrano il `message` del DB;
  `test_login_credenziale_db` pinna i minuti nell'envelope vero.
- ✅ Guida `architettura-multi-face-auth` §3.1 (§8), 2026-09-27: una persona una
  credenziale, veste spenta, porta e profili sganciati; corretta la riga che
  dava il cambio password «acceso dall'invito» (smentita da A-1).
- 🟡 Backend/Frontend: **B-6** (§12.4) — il consenso al riuso (`-51`).
  ✅ 2026-09-27: `p_riusa_auth_user_id` va da view a madre, e
  `test_login_credenziale_db` (non più sospeso) prova i due tempi sul DB vero.
  ➜ Il dialog di conferma **aspetta il DB**: scorporato con il §17 in
  [brief-db-credenziale-per-email.md](brief-db-credenziale-per-email.md).
- ✅ DB: il §17 fatto dopo lo scorporo (`20260927-40`, `-41`, applicati il
  2026-09-27): esecuzione e decisione «nessun guard a DB» nel brief nuovo.

## 13. R-7 — La risposta del login non dice se il nome esiste (disegno, 2026-09-25)

**La richiesta** (`piano-be-fe-accessi-credenziale-e-vesti` §5 R-7, ✅ Tid): il
freno e l'attesa valgono per il **nome tentato**, esista o no. Oggi un nome
inesistente non conta nulla e risponde sempre 401, mentre uno esistente, dopo la
soglia, risponde 403 `E_UTENTE_BLOCCATO`: bastano sei password per sapere se
l'utente c'è. Il backend oggi chiama check e registrazione **solo** `if user:`
(`auth_views.py`), quindi anche il numero di chiamate al DB distingue i due casi.

### 13.1 ⭐ La chiave: la credenziale quando c'è, il nome quando non c'è

| Il nome tentato… | Chiave del freno e dell'attesa | Perché |
| --- | --- | --- |
| corrisponde a una credenziale | la **credenziale**, come oggi | l'attesa crescente deve sommare i tentativi da **tutti** i nomi della stessa credenziale (username, e con L-4 l'email): con la chiave sul nome, chi attacca avrebbe il doppio dei tentativi. Il blocco dell'admin è della credenziale |
| non corrisponde a niente | il **nome tentato** (il suo digest) | è l'unica cosa che c'è; stessa soglia, stesso tetto, stessi codici |

⚠️ **Il residuo, dichiarato.** Chi conosce due nomi della stessa persona (lo
username e l'email) e li prova entrambi vede i contatori sommarsi, dove per due
nomi inesistenti resterebbero separati: impara che i due nomi sono **la stessa
credenziale**. Per saperlo deve però già supporre che esistano entrambi. È
un'informazione molto più stretta di «il nome esiste», e l'alternativa (chiave
sempre sul nome) toglie l'attesa crescente sulla credenziale, che è la difesa
contro l'attacco distribuito. Proposta: **accettarlo e dichiararlo**, come
`E_CREDENZIALE_BLOCCATA` (punto (b) di R-7).

### 13.2 La forma

- **Stesse due funzioni, un parametro in più** (non due funzioni parallele):
  `fn_check_blocco_login(p_auth_user_id, p_nome_digest, p_provenienza)` e
  `fn_registra_tentativo_login(p_auth_user_id, p_nome_digest, p_provenienza,
  p_successo)`. Il backend le chiama **sempre**, con `p_auth_user_id` `NULL`
  quando il nome non trova niente: il DB sceglie la chiave, il backend non
  ramifica. Firma nuova ⇒ `DROP` + `CREATE`, e il backend si allinea nella
  stessa PR (come per il `-10`).
- **Due tabelle nuove**, gemelle di quelle della credenziale e senza legami con
  lei: `config.nomi_tentati` (digest `UNIQUE`, `fallimenti_consecutivi`,
  `ultimo_fallimento_at`, `cleanup_at`) e `config.nomi_tentati_provenienze`
  (FK `ON DELETE CASCADE`, `tentativi_falliti`, `bloccato_fino_a`,
  `ultimo_fallimento_at`, `cleanup_at`). Nessuna riga in `config.credenziali` per
  un nome che non è una credenziale (vincolo di R-7). Stessa postura della
  coppia di oggi: `SELECT` all'app, scrittura solo dalle DEFINER.
- ⭐ **Regola del 2: il calcolo non si copia.** Il passo del freno (tentativi +1,
  o 1 se il freno è scaduto; freno alla soglia) e la decisione del check oggi
  stanno scritti dentro le due funzioni. Con la seconda chiave diventerebbero due
  copie: si estraggono in building block **puri sui valori**
  (`fn_login_freno_passo`, accanto a `fn_login_attesa_secondi` che è già
  condiviso), e i due rami li chiamano. Un freno che cambia regola la cambia per
  le due chiavi insieme.
- **Retention**: le due tabelle nuove entrano nella regola `CLEANUP_AT` (la
  ricetta in quattro pezzi). Per `nomi_tentati` è nuova: la riga della
  credenziale è permanente, quella di un nome inesistente no, e scade
  dall'ultimo fallimento.
- **Successo**: un nome inesistente non entra mai, quindi niente azzeramento
  sul ramo del nome. Se più avanti quel nome diventa una credenziale, le righe
  del nome restano inerti fino alla loro scadenza: il lookup trova la
  credenziale e la chiave è quella.
- ⚠️ `E_CREDENZIALE_NON_TROVATA` di `fn_registra_tentativo_login` resta
  per un `p_auth_user_id` **valorizzato** e sbagliato (chiamata incoerente),
  mai per un nome inesistente: quel caso ora ha la sua strada.

### 13.3 Il digest: lo calcola il backend, in entrambi i casi di (a)

Qualunque sia la risposta al punto (a), **il nome in chiaro non entra nel DB**:
se il DB calcolasse l'hash, il nome passerebbe come parametro, nel contesto degli
errori (`fn_log_and_raise_error` registra il contesto) e nei log del server.
Quindi la firma DB è la stessa: `p_nome_digest bytea`, 32 byte, controllato in
lunghezza (`E_AUTH_CHIAMATA_NON_VALIDA` altrimenti). **(a) resta una decisione
tutta del backend**, e la raccomandazione è **HMAC-SHA256 con una chiave del
backend** (setting, mai nel DB): con l'hash semplice, una password digitata nel
campo username si ricava dal digest per forza bruta, perché le password umane
hanno poca entropia; con l'HMAC serve anche la chiave. Ruotare la chiave azzera
i contatori dei nomi inesistenti: è stato che dura minuti, niente si perde.

⛔ **La normalizzazione è quella del lookup** e vive nello stesso posto del
lookup (backend): oggi username esatto, con L-4 email senza maiuscole. Due
normalizzazioni diverse riaprirebbero l'oracolo (il nome esistente si
normalizza in un modo, quello inesistente in un altro).

### 13.4 Cosa chiederà al backend

| # | Cosa |
| --- | --- |
| B-9 | check e registrazione **sempre**, anche con `user` `None`, con il digest del nome normalizzato; niente più `if user:` attorno alle due chiamate |
| B-10 | il digest (HMAC con chiave da setting, se (a) va così) in **un** helper, lo stesso per operatore, portale e shop |
| B-11 | ⚠️ i log `security.login_blocked user=%s`, `security.login_locked user=%s`, `security.veste_non_attiva user=%s` scrivono **il nome tentato in chiaro**: è lo stesso rischio che R-7 toglie dal DB (una password digitata come username finisce nel log). Proposta: nei log lo `auth_user_id` quando c'è, altrimenti un prefisso del digest |
| B-12 | il tempo di risposta: il ramo del nome inesistente deve verificare comunque una password (Django lo fa già in `authenticate` con l'hasher di default); da confermare col test sul login vero |

### 13.5 Decisioni per Tid, prima dei changeSet

✅ **Tid, 2026-09-25: sì a tutte e quattro**, come proposte.

1. **La chiave doppia** del §13.1 (credenziale se c'è, nome se non c'è), con il
   residuo dichiarato. Proposta: sì.
2. **(a)**: HMAC con chiave del backend. Proposta: sì. Non cambia il DB, ma
   decide B-10.
3. **(b)**: `E_CREDENZIALE_BLOCCATA` rivela l'esistenza solo per una credenziale
   bloccata dall'admin: accettarlo e dichiararlo. Proposta: sì.
4. **La forma** del §13.2: stesse funzioni con il parametro in più, due tabelle
   gemelle, calcolo del freno estratto. Proposta: sì.

### 13.6 Esecuzione (2026-09-25)

| Fase | ChangeSet | Cosa |
| --- | --- | --- |
| `00_schema/config` | `-55` | `config.nomi_tentati`: digest (`bytea`, `UNIQUE`, `CHECK` 32 byte), fallimenti consecutivi, ultimo fallimento, `cleanup_at` |
| | `-56` | `config.nomi_tentati_provenienze`: la coppia nome + provenienza, gemella di `credenziali_provenienze`; FK `ON DELETE CASCADE` |
| `20_code/config` | `-57`, `-58` | trigger alla nascita della scadenza (`dbops.trgfn_cleanup_at_alla_nascita`) sulle due tabelle |
| `20_code/script` | `-59` | ⭐ `fn_login_freno_passo(tentativi, bloccato_fino_a, adesso, max, minuti)`: il passo del freno, puro sui valori, estratto dall'upsert del `-11` (regola del 2) |
| | `-60` | `fn_check_blocco_login(p_auth_user_id, p_nome_digest, p_provenienza)`: chiave doppia, una decisione. `DROP` della `(integer, inet)` |
| | `-61` | `fn_registra_tentativo_login(p_auth_user_id, p_nome_digest, p_provenienza, p_successo)`: due rami che chiamano il `-59`; un successo senza credenziale è una chiamata non valida. `DROP` della `(integer, inet, boolean)` |
| `80_data` | CSV | `automation_rules_tbl.csv` righe 22 (`nomi_tentati_provenienze`, TTL 1 giorno come la coppia della credenziale) e 23 (`nomi_tentati`, TTL 30 giorni); `fk_index_policy_credenziali.csv` la FK nuova, `consentito = f` (coperta dall'`UNIQUE`) |
| `90_end` | `-62` | la porta: all'app solo `SELECT` sulle due tabelle; stesse voci nel loop `ci_apply/20260205-41` e nel provisioning |

⚠️ **Il digest è obbligatorio anche con la credenziale** (e allora non si legge):
un check che lo pretendesse solo per i nomi inesistenti darebbe al backend un ramo
in più da tenere uguale.

⚠️ **Residuo della retention, dichiarato** (fatto datato, non motivo): dopo 30
giorni senza errori il conto di un nome inesistente riparte, quello di una
credenziale no (finché il titolare non entra). Per vederlo bisogna aspettare 30
giorni, e l'ingresso del titolare azzera comunque la credenziale in momenti che
chi attacca non conosce.

**pgTAP.**

- Nuovo `config/test-login-nome-inesistente-v1` (16): il passo del freno (1-4), il
  nome che conta senza righe in `config.credenziali` (5-8), ⭐ **la parità** (9: la
  stessa sequenza su una credenziale vera e su un nome inesistente dà gli stessi
  ritorni e lo stesso rifiuto), freno e attesa del nome (10-12), chiamate non
  valide (13-15), nome mai provato (16).
- Adeguati alla firma: `test-credenziale-login-v1` (test 21 conta anche le firme
  senza digest), `test-credenziale-blocco-admin-v1`, `test-credenziale-login-tempo-v1`,
  `test-credenziali-porta-v1` (casi 11-13 sulle gemelle; il 5 conta
  `fn_login_freno_passo`, il 9 i trigger nuovi).

**Come è stato provato (2026-09-25).** Scratch `zeroerp_ci`, da owner, SQL
estratto da `-55…-62` più le due regole come le scrive il CSV, transazioni
ritirate: `test-login-nome-inesistente-v1` 16/16, `test-credenziale-login-v1` 22/22,
`test-credenziale-blocco-admin-v1` 16/16, `test-credenziale-login-tempo-v1` 5/5,
`test-credenziali-porta-v1` 10/13 — ⚠️ i tre rossi (3, 4, 13) provano il `42501`
come app, e da owner sono rossi per costruzione (come nel §11.4). `plpgsql_check`
nessun messaggio sulle tre funzioni; una firma per nome; cancelli statici verdi.
✅ **Applicato su dbdev il 2026-09-25** (19:16), committato (`7f3208a58`).

⛔ **Si applica INSIEME alla PR del backend** (B-9, B-10): le due firme cambiano,
e applicato da solo il `-60`/`-61` rompe il login del backend su dbdev.

**Presidi trasversali da guardare nella corsa di Tid**: `test-riferimenti-morti-v1`
(compila ogni funzione), e il B-7 (i codici non cambiano: nessun codice nuovo).

## 14. R-9 — Il dettaglio operatore dice lo stato della veste (2026-09-25)

**La richiesta** (`piano-be-fe-accessi-credenziale-e-vesti` §5 R-9, dal lotto
L-3): il drawer non sa se la veste OPERATORE è accesa — `attivo` è della risorsa
umana, `is_active` della credenziale (derivato da tutte le vesti) — e per
distinguere «veste già attiva» dagli altri motivi del non invitabile dovrebbe
leggere il testo. E il `JOIN` sulla veste è senza filtro: con più vesti spente
il dettaglio esce in più righe.

**Trovato strada facendo.** Con più vesti spente `fn_check_operatore_invitabile`
rispondeva «invitabile», mentre l'invito del backend (`InvitoOperatoreService`)
ne pretende **una** e rifiuta («richiede intervento manuale»): la capability
offriva un pulsante che il verbo rifiutava. Capability e verbo devono dire la
stessa cosa (linee-guida-sql §12), quindi il ramo entra nella check.

| ChangeSet | Cosa |
| --- | --- |
| `20_code/script/20260925-53` | `fn_check_operatore_invitabile`: più di una veste OPERATORE (nessuna attiva) → non invitabile, motivo `Piu' vesti OPERATORE spente: serve un intervento manuale`. Contratto jsonb invariato |
| `20_code/script/20260925-54` | `fn_get_operatore_detail`: la veste è **una** (`LATERAL … LIMIT 1`): quella attiva — al più una, per `uq_identita_digitali_auth_user_ruolo_attivo` — altrimenti la spenta più recente (`data_insert`, poi `id`). Colonna nuova in coda **`veste_attiva`** = lo stato di quella veste, `NULL` senza veste. `RETURNS TABLE` cambiato ⇒ `DROP` + `CREATE`; privilegi dai default, come il `-42` |

**pgTAP**: `test-fn-check-operatore-invitabile` caso 12 (due vesti spente);
`test-fn-get-operatore-detail` casi 5-7 (`veste_attiva`; attiva + spenta → una
riga, l'attiva; due spente → una riga, `veste_attiva = false`, invito non
offerto). Le copie spente si fabbricano nel test.

**Come è stato provato (2026-09-25).** Scratch `zeroerp_ci`, da owner, SQL
estratto, transazioni ritirate: `test-fn-check-operatore-invitabile` 12/12,
`test-fn-get-operatore-detail` 7/7, e i tre pgTAP che leggono le due funzioni
(`test-crea-operatore-riusa-credenziale-v1` 20, `test-emittente-denominazione-da-soggetto-v1`
14, `test-credenziale-login-v1` 22) verdi senza modifiche. **Controprova** senza
i changeSet: caso 12 rosso, casi 5-7 muoiono su `veste_attiva` inesistente.
`plpgsql_check` nessun messaggio; cancelli statici verdi. Manual delle due
funzioni aggiornati. ✅ **Applicato su dbdev il 2026-09-25** (19:16), committato (`7f3208a58`).

**Cosa chiede al backend e al frontend** (dopo l'apply):

| # | Dove | Cosa |
| --- | --- | --- |
| B-13 | `amm_software/types.py` `OperatoreDetailRow` | il campo `veste_attiva: bool \| None` (il repository legge per nome: nessun'altra modifica) |
| F-2 | `OperatoreDrawer` | «veste già attiva» da `veste_attiva`, non dal testo di `invite_reason` |
| B-14 | `InvitoOperatoreService` | il rifiuto «più vesti spente» ora lo dice già la check (`can_invite = false`): il `require` resta come difesa, ma il pulsante non si offre più |

## 15. R-3 — I template d'invito: il nome utente e il flusso con un clic (2026-09-25)

**La richiesta** (`piano-be-fe-accessi-credenziale-e-vesti` §5 R-3, esteso in L-3):
l'invito operatore deve dire il **nome utente** (D-9); e i template
`INVITO_OPERATORE` e `INVITO_PORTALE` dicono sempre «imposta la password», anche
quando la credenziale ha già una password e l'attivazione è un clic (`is_cross`).
`INVITO_SHOP` dichiarava `is_cross` fra le variabili, ma il testo non lo usava.

**Il vincolo che decide la forma.** Il motore dei template
(`EmailDispatchService.render_template`) sostituisce `{{chiave}}` e basta: non ha
rami. Una variabile `is_cross` = «1»/«0» non può scegliere il testo. Le strade
erano tre: (a) un template per flusso, scelto dal backend; (b) la frase passata
come variabile dal backend (il testo delle email finirebbe nel codice);
(c) i condizionali nel motore (un linguaggio di template da mantenere). ⭐ Scelta
la (a): il testo resta dato, nel DB, e il backend sceglie solo **quale** codice.

| Dove | Cosa |
| --- | --- |
| `email_template.csv` id 1 `INVITO_OPERATORE` | «Il tuo nome utente è {{username}}» (html e testo); `username` fra le variabili |
| id 6 `INVITO_SHOP` | tolto `is_cross` dalle variabili: il testo non lo usa, e il ramo ora è un template |
| id 7-9 `INVITO_OPERATORE_CROSS`, `INVITO_PORTALE_CROSS`, `INVITO_SHOP_CROSS` | il flusso con un clic: «hai già un accesso, non serve una password nuova, entra con le credenziali che usi già». L'operatore riceve anche lo username |

Il CSV ha terminatori CRLF: le righe sono state riscritte una per una, le altre
sono intatte (verificato: la riserializzazione di ogni riga intatta è identica).

**Come è stato provato (2026-09-25).** Scratch, righe inserite come le scrive il
CSV, transazione ritirata: le variabili usate in oggetto, html e testo dei sei
template d'invito sono tutte fra le `variabili_disponibili`;
`test-fn-resolve-email-template` 11/11. ✅ **Applicato su dbdev il 2026-09-25** (19:16), committato (`7f3208a58`).

⛔ **Si applica insieme alla PR del backend.** Il motore lascia **letterale** un
segnaposto senza valore: finché il backend non passa `username`, l'invito
operatore mostrerebbe «{{username}}». I tre template `_CROSS` invece sono
additivi e non cambiano niente finché nessuno li sceglie.

**Cosa chiede al backend:**

| # | Dove | Cosa |
| --- | --- | --- |
| B-15 | `InvitoOperatoreService` | passare `username` (lo dà già `get_nomi_credenziale`) alle variabili dell'invito |
| B-16 | `PortaInvito` + `InvitoVesteService.spedisci` | un `template_cross` per porta, scelto quando `emissione.is_cross`; la variabile `is_cross` non serve più al testo |

## 16. I motivi del dettaglio operatore viaggiano come frasi (revisione del backend, 2026-09-25)

**Da dove viene.** Revisione critica del codice non committato di R-9: nel
drawer dell'operatore (`OperatoreDrawer.vue`, `inviteReason`) il frontend, quando
`veste_attiva` è vero, **sostituisce** il motivo del DB con un testo suo
(`amministrazione.accesso_gia_attivo`); negli altri casi mostra `invite_reason`
così come arriva.

### 16.1 Il problema, sul modello

`script.fn_get_operatore_detail` restituisce **tre** capability, e tutte e tre
portano il motivo come **frase italiana composta nel DB**, non come codice:

| Capability | Motivo | Da dove viene |
| --- | --- | --- |
| `can_invite` | `invite_reason` | `fn_check_operatore_invitabile` → `motivo` (6 frasi: «Utente non trovato», «Nessuna identita OPERATORE», «Veste OPERATORE gia' attiva», «Piu' vesti OPERATORE spente…», «Identita fuori finestra temporale», «Nessun indirizzo email configurato») |
| `can_disable` | `disable_reason` | letterale nel `CASE` di `fn_get_operatore_detail` («Ultimo SUPER_ADMIN attivo: disabilitarlo…») |
| `can_demote_super_admin` | `demote_reason` | letterale nel `CASE` di `fn_get_operatore_detail` («Ultimo SUPER_ADMIN attivo: la rimozione del binding…») |

È contro la regola del trasporto delle capability (api.md §«Capability di riga»,
linee-guida-sql §12): *il testo del motivo non viaggia mai nel payload; va un
codice macchina e la chiave i18n*. Le conseguenze:

1. **L'interfaccia inglese mostra frasi italiane**: i motivi non passano da
   `$t()`, e nessuno li può tradurre senza un changeSet.
2. **Il frontend traduce un caso solo, deducendolo.** Per «veste già attiva» non
   legge il motivo: guarda `veste_attiva` e ne ricava il testo. È una **seconda
   copia** della regola «veste attiva ⇒ non invitabile» fuori dalla sua sede.
   Oggi coincide col DB solo per l'**ordine** dei motivi (con la veste attiva le
   condizioni 1 e 2 sono per forza vere, quindi il primo motivo è il 3): se
   l'ordine cambiasse, a video comparirebbe un motivo diverso da quello del DB.
3. **Un client non può distinguere i motivi** se non confrontando stringhe
   italiane.

### 16.2 Cosa si chiede

**Al team DB:**

- `fn_check_operatore_invitabile`: accanto a `motivo` (o al suo posto, da
  decidere) un **codice macchina** per ogni condizione e la sua **chiave i18n**,
  nella forma di una famiglia già in servizio (api.md: `<flag>_reason` +
  `<flag>_reason_key`, famiglia 1);
- `fn_get_operatore_detail`: la stessa cosa per `invite_reason`,
  `disable_reason` e `demote_reason` — i letterali dei due `CASE` diventano codici;
- il pgTAP della funzione pinna i codici, non le frasi.

**Al backend / frontend, dopo il changeSet:**

- `OperatoreDrawer.vue`: **ritirare** il ramo `veste_attiva` di `inviteReason` e
  rendere i tre motivi con la chiave (`labelOrCode`: chiave mancante ⇒ si vede il
  codice, non un tooltip vuoto); le chiavi nuove in `it.json` e `en.json`;
- `OperatoreDetailRow` (`amm_software/types.py`): i campi nuovi.

✅ **Decise da Tid il 2026-09-27:** (1) `motivo` testuale **ritirato** nello
stesso giro, una sede sola; (2) i nomi dei campi del dettaglio **restano**
(`invite_reason`, `disable_reason`, `demote_reason` portano ora il codice) e
accanto nasce `<verbo>_reason_key`: si segue la famiglia già in servizio sulla
superficie, non se ne conia un'altra (api.md §Capability di riga).

### 16.3 Esecuzione (2026-09-27)

| Fase | ChangeSet | Cosa |
| --- | --- | --- |
| `20_code/script` | `20260927-01` | `fn_check_operatore_invitabile`: ritorna `{invitabile, reason, reason_key, email}`; **`motivo` ritirato**. Rami e ordine invariati (il primo motivo vince). Firma invariata: `CREATE OR REPLACE` |
| | `20260927-02` | `fn_get_operatore_detail`: `*_reason` porta il codice; tre colonne nuove **in coda** `invite_reason_key`, `disable_reason_key`, `demote_reason_key`. `RETURNS TABLE` cambiato ⇒ `DROP` + `CREATE`; privilegi dai default, come il `-54` |

**I codici e le chiavi.** Senza prefisso `E_`: sono motivi, non codici a
catalogo (linee-guida-sql §12.5.1). Nessun codice d'errore nuovo.

| Campo | `reason` | `reason_key` |
| --- | --- | --- |
| invito | `UTENTE_NON_TROVATO` | `amministrazione.operatori.invito_reason.utente_non_trovato` |
| | `SENZA_VESTE_OPERATORE` | `amministrazione.operatori.invito_reason.senza_veste_operatore` |
| | `VESTE_GIA_ATTIVA` | `amministrazione.operatori.invito_reason.veste_gia_attiva` |
| | `PIU_VESTI_SPENTE` | `amministrazione.operatori.invito_reason.piu_vesti_spente` |
| | `VESTE_FUORI_FINESTRA` | `amministrazione.operatori.invito_reason.veste_fuori_finestra` |
| | `SENZA_EMAIL` | `amministrazione.operatori.invito_reason.senza_email` |
| disabilita | `ULTIMO_SUPER_ADMIN` | `amministrazione.operatori.disabilita_reason.ultimo_super_admin` |
| rimuovi super admin | `ULTIMO_SUPER_ADMIN` | `amministrazione.operatori.rimuovi_super_admin_reason.ultimo_super_admin` |

Tre scelte da sapere:

- **Id `NULL`/≤ 0 e id inesistente danno lo stesso codice**
  (`UTENTE_NON_TROVATO`). Prima erano due frasi, ma per chi guarda è lo stesso
  caso: un id che non individua nessuno.
- **Disable e demote hanno lo stesso codice ma chiavi diverse**: la condizione
  è una, la frase dice **quale** azione non si può fare (linee-guida-sql §12.5.4).
- **Lo spazio `amministrazione.operatori.*`**, non `amministrazione.operatore.*`:
  nei locales `amministrazione.operatore` è già una foglia («Operatore») e non
  può avere figli.

⚠️ **Il presidio i18n ne vedrà sei su otto.** `scripts/check_i18n_keys.py`
trova le sei chiavi della check (scritte `'reason_key', '<chiave>'` sulla stessa
riga), **non** le due del dettaglio, che stanno dentro un `CASE`. L'elenco buono
è la tabella qui sopra, o il `COMMENT` delle due funzioni, non il rosso del
presidio.

**pgTAP.**

- `script/test-fn-check-operatore-invitabile` (plan 12 → **13**): i casi 1-5,
  9, 10, 12 pinnano `reason|reason_key` invece di frasi o `ILIKE`; il 6 anche i
  due `NULL` dell'invitabile; **nuovo 13**: la chiave `motivo` non esiste più,
  né nel rifiuto né nell'invitabile.
- `script/test-fn-get-operatore-detail` (plan 7): i casi 2, 3, 4, 7 pinnano
  codice e chiave; l'1 anche i `NULL` di disable e demote quando sono ammessi.

**Come è stato provato (2026-09-27).** Scratch `zeroerp_ci`, da owner, SQL
estratto da `-01` e `-02` dentro una transazione ritirata:
`test-fn-check-operatore-invitabile` 13/13, `test-fn-get-operatore-detail` 7/7.
I tre pgTAP che chiamano le due funzioni restano verdi e identici con e senza
i changeSet: `test-emittente-denominazione-da-soggetto-v1` 14,
`test-credenziale-login-v1` 22, `test-crea-operatore-riusa-credenziale-v1` 20.
**Controprova** senza i changeSet: nella check 9 rossi (tutti i casi che
pinnano un codice, più il 13), e il dettaglio non gira («la colonna
`disable_reason_key` non esiste»). `plpgsql_check`: nessun messaggio sulle due
funzioni. Cancelli statici verdi (`run_on_change`, `precondition_seed`,
`ddl_su_trigger_automazione`, `grant_ruolo_batch`, `sql_letterali`,
`timestamp_senza_fuso`, `pgtap_preambolo`). Definizioni sullo scratch
confrontate prima e dopo: invariate. Manual delle due funzioni aggiornati.
✅ **Applicato il 2026-09-27** da Tid (scratch `zeroerp_ci`: `EXECUTED` alle
00:17, letto da `databasechangelog`; dbdev: esito riferito da Tid), pgTAP verdi.

⛔ **Applicato prima della PR del backend e del frontend** (B-17…B-19, F-3):
il `-01` ha tolto `motivo`. Finché non arrivano, il rifiuto dell'invito
ripiega su «Operatore non invitabile.», e il drawer mostra un codice
(`VESTE_GIA_ATTIVA`…) al posto della frase, finché i locales non hanno le
chiavi.

**Presidi trasversali da guardare nella corsa di Tid**: `test-riferimenti-morti-v1`
(compila ogni funzione); il guardrail Django dei codici d'errore
(`test_error_codes_db_policy_guardrail`), che non deve vedere niente di nuovo
perché nessun motivo ha il prefisso `E_`.

### 16.4 Cosa chiede al backend e al frontend

| # | Dove | Cosa |
| --- | --- | --- |
| B-17 | `InvitoOperatoreService.invia_invito` | il rifiuto `E_INVITO` non usa più `check["motivo"]` come messaggio, perché quella chiave non esiste più. Il messaggio viene dal catalogo, e il `reason` (e la `reason_key`) viaggiano nel contesto dell'errore. Il ripiego di `_check_invitabile` (`{"invitabile": False, "motivo": …}`) prende la forma nuova. Test: `test_invito_operatore.py` (caso con `motivo="Veste OPERATORE gia' attiva"`) |
| B-18 | `amm_software/types.py` `OperatoreDetailRow` | i campi `invite_reason_key`, `disable_reason_key`, `demote_reason_key: str \| None`. Aggiornare la docstring, che dice «`invite_reason` è una stringa libera it-IT»: ora è un codice |
| B-19 | `AmmSoftwareService.disabilita_operatore` | il `detail` del rifiuto `E_PROFILO_ULTIMO_SUPER_ADMIN` non ricopia `disable_reason`, che adesso è un codice e non una spiegazione. Test: `test_amm_software_service.py` (mock con la frase) |
| F-3 | `OperatoreDrawer.vue` | **ritirare** il ramo `veste_attiva` di `inviteReason`: è la seconda copia della regola, giusta oggi solo per l'ordine dei motivi. Rendere i tre motivi dalla chiave con `labelOrCode` (chiave mancante ⇒ si vede il codice). Le **otto chiavi** della tabella del §16.3 in `it.json` e `en.json`; `amministrazione.accesso_gia_attivo` si ritira se non ha altri lettori |

⚠️ **Da verificare a video** (linee-guida-sql §12.5.5): oggi il drawer non
legge `disable_reason` né `demote_reason`, quindi il motivo di quei due pulsanti
spenti non arriva all'operatore. F-3 lo porta a video. Controllare che il tooltip
compaia davvero, perché nessun presidio lo vede.

## 17. Il dialog del consenso non ha i suoi dati (backend, 2026-09-27)

➜ **Scorporato il 2026-09-27** in
[brief-db-credenziale-per-email.md](brief-db-credenziale-per-email.md):
il problema (il contesto dell'errore non arriva al client), la richiesta al team
DB (una lettura della credenziale per email, che la madre riusa), B-20, F-4 e il
controllo a video di F-3. Quella è la sede, qui non si aggiorna più.

✅ Già fatto qui (2026-09-27): `riusa_auth_user_id` passa dalla view al
repository (`p_riusa_auth_user_id`), e `test_login_credenziale_db` prova i due
tempi sul DB vero.

⚠️ **Trovato strada facendo**, nello stesso test, che non girava finché era
sospeso: su una credenziale **senza altre vesti attive**, dopo la creazione
`is_active` è spento (è l'OR delle vesti) e il login risponde **401**, non il
403 `E_VESTE_NON_ATTIVA` che il test si aspettava. È il modello, non un
difetto: il test è corretto, con la ragione scritta.

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
| 2026-09-25 | BE → Tid | §12.7: il riuso per sola email può collegare la veste all'accesso di un'altra persona. Tid decide: rifiuto dove provabile + consenso a DB. Scritto e provato `-51` (consenso come dichiarazione dell'id), codici 1132-1133, pgTAP 14-20. Non applicato |
| 2026-09-25 | Tid | `-51` e codici 1132-1133 applicati su dbdev e scratch; test verdi. Lavoro DB del P-2 chiuso |
| 2026-09-25 | BE | §7 fatto per il P-1 (piano BE/FE §3.1-bis). Due note per il DB, nessuna urgente: `E_UTENTE_BLOCCATO` e' una frase chiusa, quindi i minuti del freno non arrivano all'operatore; e il testo «Account temporaneamente bloccato» ora descrive male un freno della sola provenienza |
| 2026-09-25 | DB | Cancello B-7 verde su scratch e dbdev: 0 accumuli, codici nuovi a una famiglia; sei blu di altri cantieri da allineare con `--update` (§12.5) |
| 2026-09-25 | Tid | Baseline B-7 allineata; scratch riallineato sul ponte django; tutti i test verdi. `-51` committato |
| 2026-09-25 | DB | R-8 (note del BE su `E_UTENTE_BLOCCATO`): scritto e provato `-52`, minuti nel messaggio e testo della postazione; pgTAP test 3 adeguato. Non applicato (§12.8) |
| 2026-09-25 | Tid | `-52` applicato su dbdev e scratch (forma coi minuti); corsa pgTAP senza regressioni. Resta a BE/FE: B-8, F-1 |
| 2026-09-25 | DB | R-7: disegno (§13) — chiave doppia (credenziale se c'è, digest del nome se non c'è), stesse due funzioni con un parametro, tabelle gemelle `nomi_tentati`, passo del freno estratto; il digest lo calcola il backend in ogni caso. Quattro decisioni per Tid |
| 2026-09-25 | Tid | R-7: sì alle quattro decisioni del §13.5. Ordine: R-9, R-7, R-3 |
| 2026-09-25 | DB | R-9 scritto e provato (§14): `-53` (più vesti spente → non invitabile, come il verbo del BE), `-54` (dettaglio su una veste, colonna `veste_attiva`). Non applicati |
| 2026-09-25 | Tid → DB | `%TYPE` dimenticati in firma, DECLARE e RETURNS TABLE di `-53`/`-54` (copiati dalla doc auto-gen, che li scioglie): ripristinati dall'ultimo YAML ancorato (`20260802-21`), `deve_cambiare_password` su `config.credenziali`; stesso controllo su `-59…-61`. Prove rifatte, verdi |
| 2026-09-25 | DB | R-7 scritto e provato (§13.6): `-55…-62`, due regole `CLEANUP_AT`, un pgTAP nuovo e quattro adeguati. Non applicato; da applicare con la PR del backend |
| 2026-09-25 | DB | R-3 (§15): `INVITO_OPERATORE` con lo username; tre template `_CROSS` per il flusso con un clic (il motore non ha rami: un template per flusso). Non applicato; con la PR del backend (B-15, B-16) |
| 2026-09-25 | BE | **B-9…B-16 scritti, non committati**, dopo l'apply delle 19:16 (che aveva rotto il login su dbdev: firme a due e tre argomenti tolte). B-9/B-10: il login chiama check e registrazione **sempre**, con `nome_tentato.digest_nome_tentato` (HMAC-SHA256, chiave da `SECRET_KEY` con sale proprio via `salted_hmac`, nessuna variabile d'ambiente nuova). ⭐ **Trovato strada facendo**: lo username si normalizzava in due modi — il serializer toglie gli spazi, il lookup no — e con « tid» blocco dell'admin, freno e attesa **non si controllavano** mentre `authenticate("tid")` faceva entrare. Ora il nome si legge dal campo del serializer (una normalizzazione sola, §13.3). B-11: nei log `user_id=` o un prefisso dell'impronta, mai il nome. B-12: `ModelBackend` verifica comunque una password (`check_password_with_timing_attack_mitigation`); le chiamate al DB sono le stesse nei due casi. B-13: `veste_attiva` nel tipo e nel drawer (F-2). B-14: nessun codice (la check lo dice gia'). B-15/B-16: `username` nell'invito operatore, `template_cross` per porta, `is_cross` tolto dalle variabili. Prove: `test_login_credenziale_db` (parita' del nome inesistente, spazi che non aggirano il freno, `veste_attiva` nel ciclo operatore), `test_template_invito_db` (ogni segnaposto dei sei template riceve un valore) |
| 2026-09-25 | BE | §16: i motivi del dettaglio operatore (`invite_reason`, `disable_reason`, `demote_reason`) viaggiano come frasi italiane; il drawer ne traduce uno solo deducendolo da `veste_attiva` (seconda copia della regola, giusta oggi solo per l'ordine dei motivi). Richiesta al DB: codici + chiavi i18n |
| 2026-09-26 | DB | Brief allineato ai commit: R-7, R-9, R-3 applicati e committati (`7f3208a58`), backend B-9…B-16 committato (`e7dbbad73`). Restano §16 (DB), B-8/F-1 e la guida multi-face (§12.6) |
| 2026-09-27 | Tid | §16: `motivo` ritirato; nomi dei campi invariati, `_reason_key` accanto |
| 2026-09-27 | DB | §16 scritto e provato (§16.3): `20260927-01` (check: `reason` + `reason_key`, `motivo` ritirato), `-02` (dettaglio: tre `_reason_key`, `DROP` + `CREATE`); due pgTAP adeguati (check plan 13). Manual aggiornati. Non applicato; con B-17…B-19 e F-3 (§16.4) |
| 2026-09-27 | Tid | `20260927-01`, `-02` applicati; pgTAP verdi. Lavoro DB del brief chiuso. Resta a BE/FE: B-17…B-19, F-3 (§16.4), B-8, F-1 (§12.8), guida multi-face (§8) |
| 2026-09-27 | BE | **B-17**: il rifiuto `E_INVITO_OPERATORE` prende il messaggio del catalogo (`ErrorPolicyRegistry`), `reason`/`reason_key` nel contesto; ripiego di `_check_invitabile` nella forma nuova. **B-18**: `invite_/disable_/demote_reason_key` in `OperatoreDetailRow`, docstring riscritta. **B-19**: il `detail` del rifiuto ultimo super admin non ricopia più il codice (va nel contesto). **B-8**: ripiego di `E_UTENTE_BLOCCATO` = frase del `-52` senza `%s`. Test: `test_invito_operatore`, `test_amm_software_service`, `test_login_credenziale_db` (+ i minuti nel `message` dell'envelope) verdi. Guida multi-face §3.1 e api.md (sesta famiglia di capability) |
| 2026-09-27 | BE | B-6, parte che non dipende dal DB: `riusa_auth_user_id` dalla view alla madre; test del consenso sbloccato e verde. Trovato: i dati del dialog stanno nel contesto dell'errore, che non arriva al client (§17). Tid sceglie la lettura a DB + dialog; richiesta al team DB al §17.2 |
| 2026-09-27 | FE | **F-3**: `OperatoreDrawer` rende i tre motivi col BB `bloccoMotivo` (prefissi `invite`/`disable`/`demote`), ritirato il ramo `veste_attiva`; i toggle «super admin» e «accesso attivo» spenti col motivo sotto quando `can_demote_super_admin`/`can_disable` sono falsi. Otto chiavi in `it.json`/`en.json`, ritirata `amministrazione.accesso_gia_attivo`. **F-1**: `E_UTENTE_BLOCCATO` in `MESSAGGIO_DB_CON_DATO`. `check_i18n_keys`, eslint e `npm run guards` verdi. ⚠️ Trovato: B-6 (consenso al riuso) mai fatto, §12.6 |
| 2026-09-27 | BE | **Chiuso.** Il §17 (dati del dialog del consenso: B-6 a metà, B-20, F-4) e il controllo a video di F-3 scorporati in `brief-db-credenziale-per-email.md`; la domanda sulle FK del ponte django (§11.5) registrata in `PROJECT_CONTEXT`. Brief spostato in `work-done/` |
| 2026-09-27 | Tid → DB | §17: nessun guard a DB sulla lettura della credenziale (il cancello è l'`AdminAPIView`). Scritti e provati `20260927-40` (`script.fn_get_credenziale_per_email`) e `-41` (la madre la legge, regola del 2), pgTAP `test-fn-get-credenziale-per-email-v1` (9), descrizione di `E_CREDENZIALE_DA_CONFERMARE`, manual (§17.4). Non applicati |
| 2026-09-27 | Tid | `20260927-40`, `-41` applicati; pgTAP verdi, nessuna regressione. Lavoro DB del §17 chiuso. Resta a BE/FE: B-20, F-4 (§17.3) |
| 2026-09-27 | BE | Merge con `Tito-dev`: le due righe qui sopra erano state scritte sul brief ancora in `work-in-progress/`. Il §17.4 (esecuzione DB) e la decisione «nessun guard a DB» sono spostati nel brief nuovo `brief-db-credenziale-per-email.md`; qui resta il rimando |

---
{% include-markdown "signature-core.md" %}
