# Brief DB — Una veste è utilizzabile se è accesa **e** nelle sue date: una regola, a DB

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-06. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§6), che **attende** la consegna DB.
> **Origine:** L-6 del
> [piano accessi](piano-be-fe-accessi-credenziale-e-vesti.md) §4.4 (A-7 dell'analisi
> accessi). Il piano diceva «si estrae un frammento comune» lato Python e «il lotto
> decide se la regola comune è quella di `fn_get_user_profile`». Facendo il lotto è
> emerso che la regola **c'è già a DB**, scritta in più sedi e non uguale, e che il
> Python ne ha una quarta. Un frammento Python sarebbe stato la quinta.
> **Stato:** ⏳ decisioni D-1…D-4 (§3) **da confermare da Tid**; poi lato DB.

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

## 3. Le decisioni (⏳ da confermare da Tid)

| # | Domanda | Proposta |
| --- | --- | --- |
| D-1 | Dove sta la regola «veste utilizzabile»? | **A DB, in un building block per veste** (§4.1). Le copie DB della §1 la leggono da lì (regola del 2, ritirate nello stesso giro), e il BE la chiama nei suoi cinque punti invece di riscriverla. Il Python **non** calcola date: «oggi» è `CURRENT_DATE` del DB, come per tutte le altre sedi. |
| D-2 | Per una veste **OPERATORE**, quale finestra vale: quella della veste, quella del rapporto, o tutte e due? | **Tutte e due**: l'operatore entra se la veste è accesa e nelle sue date **e** il rapporto (risorsa umana della veste) è attivo e nelle sue date. È già la regola di `fn_get_user_profile`, che diventa una lettura del BB e non una seconda versione. Così la data del drawer chiude l'accesso senza riscrivere la veste a ogni salvataggio. L'alternativa (il drawer scrive anche la finestra della veste) tiene due copie dello stesso dato, una per tabella: la divergenza di §2 tornerebbe al primo scrittore che ne dimentica una. |
| D-3 | La condizione «soggetto attivo» di `fn_sync_auth_user_is_active`? | **Entra nel BB**, così nessuna sede perde una condizione che oggi applica. Se il team DB verifica dal contratto che è implicata dalle altre (oggi un soggetto non si spegne con soggetti_ruoli accesi, ma un soggetto_ruolo si spegne con una veste accesa: nessun trigger lo impedisce), la toglie dichiarandolo. |
| D-4 | Al login, una veste fuori dalle sue date che codice dà? | **Lo stesso di una veste spenta**: `E_VESTE_NON_ATTIVA` al login, `E_IDENTITA_NON_ATTIVA` (401) a richiesta, refresh rifiutato come una veste spenta. Nessun codice nuovo. Il login oggi non distingue nemmeno «spenta» da «assente», e la finestra è un'altra forma di «spenta». Se Tid vuole un messaggio che dica la data («il tuo accesso è scaduto il …»), il BB diventa una check con il motivo (§4.1, variante), da decidere ora e non dopo. |

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

---
{% include-markdown "signature-core.md" %}
