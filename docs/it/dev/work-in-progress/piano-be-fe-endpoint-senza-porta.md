# Piano BE/FE — Gli endpoint senza porta

> **Chi scrive:** backend/frontend (`dev/backend-tid`), 2026-09-11.
> **Origine:** `migliorie-generali-BE-FE-da-test-valutazione.md` §3 D7 — *dieci
> endpoint costruiti, documentati, e mai raggiunti da nessuna schermata*.
> **Decisione di Tid, 2026-09-11:** scrivere la risposta per tutti e dieci **e**
> aprire il cantiere della schermata email.
>
> **In una riga:** D7 non chiedeva di scrivere codice, chiedeva di **rispondere a
> una domanda** — *«questa la deve poter usare una persona?»* — perché finché la
> risposta non è scritta, un'API di servizio e una funzione finita senza porta si
> leggono uguali. Qui c'è la risposta per ciascuno (§1) e il piano per l'unica
> che cambia qualcosa a video (§2).
>
> **Stato al 2026-09-25** (dettaglio in §3):
>
> * ✅ **§1 la decisione**: chiusa il 2026-09-11.
> * ✅ **§2.4 il docstring**: corretto nello stesso giorno (`f6ff0d398`).
> * ⛔ **§2.3 la schermata**: **non iniziata**. Zero file in `frontend/src`
>   chiamano `/core/email/`.
> * ✅ **Scelta (a) di Tid, 2026-09-25** (§3.2): gli operatori vedono le mail
>   del loro perimetro, a partire dalla sola lista.
> * ⛔ **In attesa del DB**: la RLS applica solo l'emittente, non gli ambiti
>   `REPARTO`/`OPERATORE` che il modello dichiara (§3.3) ⇒
>   [brief-db-email-visibilita-per-ambito.md](brief-db-email-visibilita-per-ambito.md).

---

## 0. Il perimetro, riverificato

⚠️ **Non ho ricontato: ho ricontrollato.** Al 2026-09-11 tutti e dieci i
percorsi danno **zero file** in `frontend/src` — la misura di D7 (2026-09-09)
regge senza modifiche.

⛔ **È un limite inferiore, e va detto**: un confronto testuale non sa vedere le
famiglie cross-dominio (`/passaggi/`, `/note/`, `/indirizzi/`,
`/situazione-merce/`), che il frontend chiama col dominio **come parametro**
esattamente come il backend le costruisce con `build_passaggi_view` e
`make_note_views`. Quei dieci sono il residuo verificato uno per uno.

---

## 1. La risposta, per ciascuno

La domanda è una sola e la risposta è **una parola**: *persona* (una schermata
serve) oppure *servizio* (l'API vive per un'altra ragione, e non aspetta una
porta).

| # | Endpoint | Risposta | Perché |
| --- | --- | --- | --- |
| 1 | `GET /core/email/log/` | 👤 **persona** | L'operatore non vede le proprie mail; l'amministratore sì. Vedi §2 |
| 2 | `/core/email/outbox/` + `prepare` + `send` + `cancel` + allegati (**9 rotte**) | 👤 **persona** | Flusso completo e chiuso a chiave — bozza → allegati → invio/annullo — con service, repository e voce a catalogo BB. Vedi §2 |
| 3 | `GET /core/tracciamento/domini-task/` | 🔧 **servizio** | Legge `dbops.domini_task`: quali domini hanno un registry di pipeline. È **configurazione del motore**, non lavoro di una persona |
| 4 | `GET /core/tracciamento/task-registry/` | 🔧 **servizio** | Idem: il catalogo dei task per dominio |
| 5 | `GET /core/tracciamento/task-implementations/` | 🔧 **servizio** | Idem: quale handler Python implementa quale task. Serve a chi diagnostica un dispatch, e la diagnosi si fa dai log |
| 6 | `GET /core/tracciamento/job-summary/` | 🟡 **servizio, ma guardarlo** | Riepilogo dei job. ⚠️ Oggi la stessa domanda ha **due risposte migliori**: il pannello code (`tracciamento/coda-lavori/`, con una schermata) e il **digest dei presidi**, che dal 2026-09-11 la porta in casella. ⇒ Candidato al **ritiro**, non a una porta |
| 7 | `GET /core/users/{id}/permessi-effettivi/` | 🔧 **servizio** | Diagnostica della catena permessi su un utente. ⚠️ Ha un valore che il pannello profili non dà — *cosa risulta davvero*, non *cosa è stato assegnato* — ma è materiale da supporto |
| 8 | `GET /core/users/{id}/permessi-audit/` | 🔧 **servizio** | Idem, sul versante audit |
| 9 | `POST /vendite/commesse/push/run/` + `GET /push/{id}/` | 🔧 **servizio** | Il push da commessa è orchestrato dalla pipeline; questi due sono l'innesco manuale. L'operatore ci arriva dal cockpit, non da qui |
| 10 | `POST /vendite/.../rettifica-controllata/` | ⚠️ **persona, ma non adesso** | È l'**N6** dei listini: l'eccezione all'immutabilità di una versione ATTIVA. Ha senso solo con una schermata di listini che oggi non la offre ⇒ **cantiere suo**, dichiarato qui e non fatto |
| 11 | `POST /vendite/pipeline/run-until-done/` | 🔧 **servizio** | Il cockpit usa `fatturazione/run/` (non bloccante, via coda). Questo è la catena sincrona: utile a mano, sbagliato da esporre a video |
| 12 | `GET /anagrafiche/utilities/manual-lookup/` | 🔧 **servizio** | Lookup di servizio superato dai lookup ricchi (`billing-account/lookup/`, `istanze-utility/lookup/`). ⇒ Candidato al **ritiro** |
| 13 | `POST /shop/register/check-email/` | 🔧 **servizio, per ora** | Lo shop è a Stage D: la sua porta arriverà col checkout, non prima. Non è orfano, è **in anticipo** |

⭐ **Il conto che conta**: su tredici rotte, **due famiglie** (10 rotte) sono
funzioni finite senza porta, **due** sono candidate al ritiro, una è un cantiere
dichiarato, il resto è servizio legittimo. ⛔ *Prima di questa tabella si
leggevano tutte uguali* — ed è l'unica cosa che D7 chiedeva di cambiare.

### 1.1 ⚠️ Un difetto trovato scrivendo questa tabella

`EmailLogOperatoreListView` ha come docstring *«log email visibili
all'operatore (per **ambito/reparto**)»*, e passa a `list_logs(...)` **né
`ambito` né `unita_organizzativa_id`** — i due parametri che il repository
espone proprio per quello.

⭐ **Non è un buco di sicurezza, e l'ho verificato invece di dedurlo dal nome**:
`config.email_log` ha la **RLS attiva** con una policy che filtra per
`fn_scope_ef_whitelist(user, emittente_fiscale_id)`, e per l'ambito `SISTEMA`
pretende un super admin o lo scope del processo `send_pending_emails`. Il
cancello c'è, e lo tiene il database.

⛔ **È un difetto della frase**: lo scope che quella vista ha è per **emittente**,
non per reparto. Chi legge il docstring crede che un filtro esista, e non
esiste — è la stessa specie di difetto del campo dichiarato e mai letto. ⇒ Si
corregge la frase (§2.4), non si aggiunge il filtro: aggiungerlo sarebbe una
**seconda sede** dello scope, accanto a quella del database.

---

## 2. Il cantiere: le mail dell'operatore

### 2.1 Cosa manca davvero

| Pezzo | Stato |
| --- | --- |
| Endpoint | ✅ 10 rotte, tutte servite |
| Service | ✅ `EmailOutboxService` (`prepare_draft` · `add_attachment` · `confirm_and_send` · cancel), `EmailDispatchService` |
| Repository | ✅ `EmailRepository` |
| Scope dei dati | ✅ RLS su `config.email_log` — **non** da riscrivere lato applicativo |
| Chi entra | ⚠️ **dal 2026-09-12 solo chi ha l'area `config`** (LETTURA per leggere, TUTTO per spedire) — §3.1 |
| Configurazione di lista | ✅ `ui.lista_definizione` id **31** (`config.email_log`), già a catalogo dal 2026-08-01 |
| **Schermata** | ⛔ **zero** |

⭐ **Il pezzo che rende questo cantiere piccolo**: la lista a catalogo **esiste
già** e la usa la schermata admin (`EmailLogsListView`, `<ListaConfigurabile
codice="config.email_log">`). ⇒ **Non serve niente dal team DB**, e non serve
`gen_seed_lista.py`.

### 2.2 La scelta che va fatta una volta, e dichiarata

La schermata dell'operatore **riusa** il codice lista `config.email_log`.

* ⭐ **Perché riusare**: è la stessa tabella e sono le stesse colonne. Due
  definizioni identiche divergerebbero alla prima colonna aggiunta a una sola
  delle due.
* ⚠️ **Cosa comporta, e va saputo**: la preferenza colonne è chiavata su
  `(auth_user, lista_id)`, quindi **un amministratore che apre entrambe le
  schermate vede la propria personalizzazione in tutte e due**. È accettabile
  finché le colonne coincidono; il giorno in cui divergono si spezza in
  `config.email_log_operatore`, e quello sarà un seed di lista, non un brief.

### 2.3 Il lavoro, in ordine

1. **`frontend/src/core/api/` — il client**: `listEmailLogOperatore(params)` su
   `/core/email/log/`. ⚠️ I parametri sono quelli che la view già dichiara
   (`search`, `stato`, `pratica_id`, `data_da`, `data_a`, `limit`, `offset`) —
   ⛔ **offset-based**, non `page`: lo store deve usare `buildDocListParams`-like
   e non la convenzione page-based, o la seconda pagina non arriva.
2. **Lo store**: `createListaStore` con `parentField` assente — è una lista
   globale. ⛔ **Non** `createCrudStore`: l'operatore non crea né modifica un log,
   e un `create`/`update` che nessuno chiama è un contratto che non descrive
   niente.
3. **La view**: `useListaConfigurabilePage(store, {...})` +
   `<ListaConfigurabile codice="config.email_log">`, con il filtro data standard
   (`defaultFiltroDataDaString()`) e `EmailLogStatoSelect`, che **esiste già**.
4. **La rotta e la voce di menu**: `core/navigation.js`. ⚠️ **Non** sotto
   `amministrazione/`: quella cartella è il pannello dell'amministratore, e
   questa schermata esiste proprio perché la funzione non è sua.
5. **L'outbox**: seconda tranche, e **dopo** la lista. È un flusso a stati
   (bozza → allegati → invio) e vuole un drawer con `FormFooter`, non una lista.
   ⇒ Si apre quando la lista è in uso, così il flusso lo disegna chi l'ha vista.

### 2.4 Le due correzioni che vanno con questo lavoro

* **Il docstring di `EmailLogOperatoreListView`** (§1.1): dire che lo scope è per
  **emittente** e lo tiene la RLS. Una frase.
* **`api.md` §Endpoint attivi**: la famiglia `/core/email/` non è nominata
  nell'inventario. ⚠️ Va aggiunta **quando la schermata esiste**, non adesso:
  registrare una porta che non c'è è l'errore opposto a quello che stiamo
  chiudendo.

### 2.5 Cosa NON fa parte di questo cantiere

* ⛔ Aggiungere il filtro `ambito`/`unita_organizzativa_id` alla view: sarebbe
  una seconda sede dello scope (§1.1).
* ⛔ Toccare la schermata admin: le due convivono, e l'admin vede tutto **per
  disegno**.
* ⛔ Ritirare `job-summary` e `manual-lookup` insieme a questo lavoro: sono
  candidati al ritiro (§1), e un ritiro è una decisione sua — con la sua verifica
  che nessuno li chiami, frontend **e** tool dell'assistente AI.

---

## 3. Stato al 2026-09-25

### 3.1 Cosa è fatto, cosa no, cosa è cambiato sotto

| Voce | Stato | Dove |
| --- | --- | --- |
| §1 — la risposta per le tredici rotte | ✅ chiusa 2026-09-11 | `migliorie-generali-BE-FE-…` D7 (la decisione) |
| §2.4 — docstring di `EmailLogOperatoreListView` | ✅ corretto 2026-09-11, con il blocco «⛔ lo scope non sta qui» sopra la classe | `core/api/email_views.py` |
| §2.3 passi 1-4 — client, store, view, rotta/menu | ⛔ **non iniziati** (ricontrollato: nessun uso di `/core/email/` in `frontend/src`) | — |
| §2.3 passo 5 — outbox | ⛔ non iniziato (per piano, dopo la lista) | — |
| §2.4 — `/core/email/` in `api.md` | ⏸ in attesa della schermata, **per piano** | — |
| §2.5 — ritiro `job-summary`, `manual-lookup` | ⏸ non deciso: entrambe le rotte sono ancora registrate | `core/api/urls_v1.py`, `anagrafiche/api/urls.py` |
| §1 #10 — `rettifica-controllata` (N6) | ⏸ cantiere suo, non questo | — |

⛔ **Il fatto nuovo, successivo al piano**: con D15 (2026-09-12, `26a3c53f8`)
tutte e dieci le view di `/core/email/` hanno perso `skip_area_check`, che era
**muto**, e dichiarano l'area `config`. L'intestazione di `email_views.py`
dice che per tua decisione *non è un'API per tutti gli operatori*. Se un
giorno dovrà aprirsi oltre `config`, l'ordine è: prima un'azione di processo
a catalogo (`invia_email`), poi la schermata, **poi** lo skip. Mai il
contrario.

Le due schermate a confronto, oggi:

| | Schermata admin (esiste) | Schermata operatore (§2, da fare) |
| --- | --- | --- |
| Endpoint | `/amm-software/email-log/` | `/core/email/log/` |
| Chi entra | **solo super admin** (`AdminAPIView`) | chi ha l'area **`config`**, in LETTURA |
| Cosa vede | tutto | solo gli emittenti del proprio scope (RLS) |

⇒ La premessa del §1 (*«l'operatore non vede le proprie mail;
l'amministratore sì»*) era scritta con lo skip ancora dichiarato. Oggi la
schermata del §2 servirebbe a **chi ha `config` senza essere super admin**,
non all'operatore qualunque.

### 3.2 La decisione — ✅ (a), Tid 2026-09-25

La domanda che decide: *un operatore che non amministra deve poter controllare
se e quando è partita una mail?* Risposta di Tid: **sì**. Si parte dalla sola
lista.

* **(a) Aprire la porta.** ← **scelta** La schermata si fa, per gli operatori che non
  hanno `config`.
  * **La lista** (sola lettura): serve decidere **chi** la vede, cioè sotto
    quale area o quale permesso. Lo scope sui dati lo tiene già la RLS.
  * **L'outbox** (spedire): prima serve l'azione di processo `invia_email` a
    catalogo (brief al team DB), poi la schermata, poi l'apertura.
* **(b) Chiudere la porta.** Si riconosce che dopo D15 le mail sono una
  funzione di configurazione: il super admin ha già la sua schermata, e
  §2.3 non si fa. D7-schermata si chiude con questa motivazione; le dieci
  rotte `/core/email/` passano da *persona* a *servizio* nel §1, o diventano
  candidate al ritiro.

### 3.3 ⛔ Il prerequisito che la (a) ha fatto emergere

Il modello di `config.email_log` e `config.email_outbox` dichiara tre ambiti di
visibilità:

* `SISTEMA`: solo admin;
* `REPARTO`: solo il reparto;
* `OPERATORE`: solo chi l'ha creata.

Le due policy RLS applicano solo il primo. Per gli altri due guardano **solo
l'emittente**.

Finché al log entrava solo chi ha `config`, il buco non era raggiungibile. Con
la (a) sì: un operatore leggerebbe le mail `OPERATORE` di un collega dello
stesso emittente. Sull'outbox potrebbe anche **spedirne** la bozza.

⇒ ⛔ La correzione **non** va nella view: sarebbe la seconda sede del §1.1. Va
nelle policy:
[brief-db-email-visibilita-per-ambito.md](brief-db-email-visibilita-per-ambito.md)
(decisioni D-1 → D-4 ✅ prese da Tid il 2026-09-25; il lavoro è del team DB). Il §2.3 riparte quando quel brief è chiuso.
Allora resta una scelta BE: la sola **lista** può uscire dall'area `config`,
perché il perimetro lo porta tutto la RLS; l'**outbox** resta sotto `config`
fino all'azione `invia_email` (D15).

---

*Piano BE/FE, 2026-09-11; stato aggiornato il 2026-09-25. Le risposte del §1
sono decisioni prese con Tid quel giorno; il §2 è il cantiere che ne discende;
il §3 registra ciò che è cambiato dopo (D15). Stato in
`migliorie-generali-BE-FE-da-test-valutazione.md` §3 D7.*
