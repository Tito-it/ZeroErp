# Brief DB → BE/FE — L'area «Accessi» e la veste operatore spenta

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-02. **A chi:** team DB (`dev/db-tid`)
> per §3; poi BE/FE (§4, §5).
> **Origine:** revisione delle modifiche BE sul riuso della credenziale (D-6, «una persona, una
> credenziale») e discussione con Tid sulla lista operatori, 2026-10-02.
> **Stato:** ⏳ decisioni prese (§2); da fare lato DB, poi BE/FE. Ordine suggerito al team DB:
> **R-DB-1 per primo** — cambia come si riconosce la veste operatore, su cui poggia la categoria
> di R-DB-A1.
> ℹ️ Questo brief assorbe, dal 2026-10-02, il brief «veste spenta e credenziali senza veste»
> (richieste R-DB-1 e R-DB-2), per non tenere due documenti sullo stesso cantiere.
>
> **In una riga:** due difetti dello stesso cantiere. (1) Chi è **solo** cliente o fornitore del
> portale o dello shop non si vede in nessuna lista, e le credenziali senza veste non le vede
> nessuno: la voce «Operatori» diventa l'area **«Accessi»**, con tre tab che insieme censiscono
> **tutte** le credenziali, ognuna in un tab solo. (2) La veste operatore spenta **perde il suo
> tipo** (`DISABILITATO` lo sovrascrive), mentre le altre vesti lo tengono: va spenta come le altre.

---

## 1. Il problema

### 1.1 Chi non sta in nessuna lista

Dal 2026-10-02 la lista operatori mostra solo chi ha la veste operatore (prima ci finivano anche i
clienti dello shop, con le colonne vuote). È corretto, ma lascia un buco: una credenziale che ha
**solo** vesti cliente o fornitore non compare in nessuna lista. Per sapere chi ha accesso al
portale o allo shop si aprono le schede dei clienti una per una. E una credenziale **senza alcuna
veste**, che prima restava in lista operatori come «caso da sanare», non la vede più nessuno.

### 1.2 Due modi di spegnere una veste (letto dalla struttura)

| Veste | Chi la spegne | Come |
| --- | --- | --- |
| CLIENTE_PORTALE, FORNITORE_PORTALE, SHOP_CUSTOMER | `InvitoPortaleService._disattiva_veste_common` → `portale_repository.disattiva_identita` | `attivo = false`. Il tipo **resta** |
| OPERATORE | `AmmSoftwareRepository.disabilita_operatore` / `update_operatore(attivo=False)` | `attivo = false` **e** `ruolo_applicativo = 'DISABILITATO'`. Il tipo **si perde** |

La riattivazione dell'operatore riscrive `ruolo_applicativo = 'OPERATORE'`: il tipo torna perché il
codice lo **sa** già, non perché il dato lo dica. Cosa costa oggi:

* **Il tipo si deduce.** Il BE riconosce la veste operatore con `EXISTS risorse_umane` sul ruolo
  dell'identità (`_VESTE_OPERATORE` in `amm_software_repository.py`, 2026-10-02), perché
  `ruolo_applicativo = 'OPERATORE'` non vede l'operatore spento. Fino a quel giorno lista operatori
  e riepilogo permessi lo cercavano proprio così, e un operatore disabilitato vi compariva con
  reparto e validità vuoti.
* **Doppio segnale per «spenta».** Chi chiede «questa veste è utilizzabile?» deve controllare due
  colonne: `attivo = true AND ruolo_applicativo <> 'DISABILITATO'`. Oggi lo fanno
  `anagrafiche.fn_sync_auth_user_is_active`, `script.fn_get_profili_accesso_applicabili` (due
  volte), `script.fn_get_user_profile` e, lato BE, `count_admin_attivi`. Una sola che dimentica il
  secondo controllo tratta da utilizzabile una veste spenta, o viceversa.
* **Il guard di coerenza esce in anticipo.** `trgfn_identita_digitali_guard_coerenza` non controlla
  niente su `DISABILITATO`: una veste spenta non dichiara più a quale mondo appartiene (persona con
  risorsa umana, processo, cliente), quindi il trigger non ha niente da verificare.

## 2. Decisioni di Tid (2026-10-02)

| # | Decisione |
| --- | --- |
| V-1 | La veste operatore si **spegne come le altre**: `attivo = false`, il tipo resta (R-DB-1) |
| V-2 | Un **presidio** segnala le credenziali senza alcuna veste (R-DB-2) |
| V-3 | Il presidio vale **solo** per le credenziali senza **nessuna** veste. Una credenziale con sole vesti spente è una persona disattivata, uno stato legittimo: **non** rientra (R-DB-2) |
| V-4 | Le righe `DISABILITATO` di oggi che non si riconducono a nessuna veste sono **dati di prova** del DB di sviluppo: si abbandonano, e si possono cancellare a mano su dbdev. Nessun ramo di conversione per loro (R-DB-1) |
| A-1 | La voce di menu «Operatori» diventa **«Accessi»**, con tre tab: **«Operatori»**, **«Altri accessi»**, **«Di sistema»** |
| A-2 | I tre tab sono una **partizione**: ogni credenziale sta in **uno solo**. «Operatori» = chi ha la veste operatore, anche con altre vesti (che restano badge della riga). «Altri accessi» = tutte le altre persone, comprese quelle **senza alcuna veste** (badge «Nessun accesso»). «Di sistema» = le macchine (A-6) |
| A-4 | In «Altri accessi»: **lettura più le azioni che riguardano la credenziale**. Le **vesti** non si gestiscono da qui: invito, reinvio e disattivazione restano nella scheda del cliente o del fornitore, che ne è il proprietario. Dalla riga si apre la scheda del soggetto collegato |
| A-5 | **Simmetria**: le azioni della credenziale (blocca, sblocca, secondo fattore) stanno anche nel tab «Operatori» |
| A-6 | Tab **«Di sistema»**: le credenziali delle macchine — gli utenti tecnici dei processi automatici (`tecnica`, creati da `fn_crea_utente_tecnico`) e la veste `API_CLIENT`. **Sola lettura**, con il link al processo: bloccare un utente di sistema fermerebbe un automatismo all'insaputa del pannello dei processi, che ne è il proprietario; il secondo fattore su una macchina non ha senso. Non duplica il drawer del processo (che mostra gli utenti di UN processo): è la vista d'insieme |
| A-7 | Lo **stato** di una veste (ATTIVA / INVITATA / SPENTA) si calcola **solo a DB**: lo usano la vista degli «Altri accessi» e lo stato accessi della scheda cliente/fornitore, che smette di calcolarlo nel BE (R-DB-A2) |

(A-3, «utenti tecnici fuori da tutti i tab», è stata superata da A-6.)

## 3. Richieste al team DB

### R-DB-1 — Spegnere la veste operatore come le altre: `attivo = false`, il tipo resta

* La veste operatore spenta resta `ruolo_applicativo = 'OPERATORE'` con `attivo = false`, come le
  vesti portale e shop. «È spenta» si legge **solo** da `attivo` (e dalla finestra di validità).
* `DISABILITATO` smette di essere uno **stato** di una veste. Se nel modello resta qualcosa che lo
  usa con un altro significato, lo si dichiara; altrimenti si ritira dall'enum
  `config.ruolo_applicativo` (decisione del team DB, da motivare sul modello).
* **Le righe che oggi hanno `DISABILITATO`**: il tipo vero si ricava dalla struttura (risorsa umana
  sul ruolo → OPERATORE; `tecnica` → OPERATORE tecnico).
* **Quelle che non si riconducono a nessuna veste** (V-4): sono dati di prova di dbdev, si cancellano
  a mano prima dell'apply — nessun changeSet, non sono seed. ⚠️ Sul modello, dopo R-DB-1 una veste
  senza tipo **non esiste**: il changeSet di conversione non le salta in silenzio, **si ferma** con
  un errore che le elenca. Così una riga del genere non sopravvive per sbaglio su un'altra
  macchina, e in CI (DB ricostruito da zero) il ramo non si incontra.
* Oggetti DB che oggi leggono o scrivono `DISABILITATO` (doc auto-generata, 2026-10-02):
  `anagrafiche.fn_crea_operatore_v2`, `anagrafiche.fn_sync_auth_user_is_active`,
  `anagrafiche.trgfn_identita_digitali_guard_coerenza`,
  `anagrafiche.trgfn_identita_digitali_sync_auth_user_active`,
  `script.fn_get_profili_accesso_applicabili`, `script.fn_get_user_profile`. Il guard di
  coerenza deve tornare a controllare **anche** la veste spenta.
* Codice d'errore: `E_UTENTE_DISABILITATO` (da `fn_get_user_profile`) continua a dire la stessa
  cosa all'utente; cambia solo da quale colonna nasce.
* pgTAP da costruire: un operatore spento resta `OPERATORE` con `attivo = false`; non è
  utilizzabile (`fn_sync_auth_user_is_active`, `fn_get_user_profile`); riattivato torna
  utilizzabile; il guard di coerenza rifiuta un operatore spento su un ruolo senza risorsa umana.

### R-DB-2 — Un presidio per le credenziali senza alcuna veste

* Dal 2026-10-02 la lista operatori e il riepilogo permessi mostrano **solo** chi ha la veste
  operatore. Una credenziale senza alcuna identità digitale, che prima vi compariva apposta come
  «caso da sanare» (commento di `ESCLUDI_UTENTI_TECNICI`), da allora non la mostra più nessuno.
* Con l'area «Accessi» avrà di nuovo un posto dove si **vede** (tab «Altri accessi», badge «Nessun
  accesso»). Il presidio resta comunque: la lista è dove si guarda, il presidio è chi avvisa.
* Richiesta: la sua riga nel catalogo `dbops.presidi`, così compare nel pallino della topbar. Per
  non avere due regole, il presidio legge la vista di R-DB-A2 (`nessun_accesso`) invece di una sua.
* Perimetro (V-3): **solo** le credenziali senza nessuna veste. Una credenziale con sole vesti spente
  è una persona disattivata, uno stato legittimo, e non rientra.
* pgTAP da costruire: una credenziale senza veste compare nel presidio; una con sole vesti spente no.

### R-DB-A1 — La regola della partizione, in un posto solo: una categoria per credenziale

La regola «questa credenziale ha la veste operatore» oggi sta nel BE (`_VESTE_OPERATORE`). Gli altri
due tab ne sono il complemento: se li scrivessero viste DB con predicati propri, ci sarebbero più
copie della stessa regola, e prima o poi una credenziale finirebbe in due tab, o in nessuno.

* Richiesta: la regola è una **classificazione**: ogni credenziale ha UNA categoria — `OPERATORE`,
  `SISTEMA`, `ALTRO` — calcolata da un solo oggetto DB (per esempio
  `script.fn_categoria_accesso(auth_user_id)`, o una vista che la espone). La usano le tre liste e il
  BE, che ritira `_VESTE_OPERATORE`. Una funzione che restituisce un valore solo rende la partizione
  vera **per costruzione**: nessuna credenziale in due tab, nessuna in nessuno.
* `SISTEMA` = identità con `tecnica` oppure veste `API_CLIENT`. ⚠️ La **precedenza** va dichiarata sul
  modello, non lasciata all'ordine di un `CASE`: per esempio una credenziale con la veste operatore
  **e** `API_CLIENT`, se il modello la ammette. Se non la ammette, lo si scrive (e lo si presidia).
* La forma dipende da R-DB-1. Oggi: risorsa umana sul ruolo. Dopo R-DB-1:
  `ruolo_applicativo = 'OPERATORE' AND NOT tecnica`. Va scritta **una** volta, nella forma del
  modello a quel punto.
* pgTAP da costruire: una credenziale per categoria (operatore persona, operatore spento, solo
  shop, nessuna veste, utente tecnico, `API_CLIENT`) e ognuna con la categoria attesa.

### R-DB-A2 — La vista degli «Altri accessi»

Una riga per credenziale di categoria `ALTRO` (R-DB-A1). Colonne:

| Colonna | Da dove |
| --- | --- |
| `auth_user_id`, `username`, `email`, nome visualizzato | `auth_user` e soggetto |
| `vesti` (jsonb, lista): per ogni veste il codice `ruolo_applicativo`, lo **stato** (`ATTIVA` / `INVITATA` / `SPENTA`, con la stessa regola dello stato accessi di `portale_repository`) e il soggetto collegato (cliente o fornitore, con l'id che serve al FE per aprirne la scheda) | `identita_digitali`, token d'invito |
| `nessun_accesso` (bool): nessuna veste | come sopra |
| secondo fattore: attivo, obbligatorio | tabelle del secondo fattore |
| blocco dell'amministratore: bloccata, dal, motivo | `config.credenziali` |
| `ultimo_accesso` | `auth_user.last_login` |

* ⭐ Lo **stato** di una veste (ATTIVA / INVITATA / SPENTA) si calcola **solo a DB** (A-7): una
  funzione o vista unica, letta da questa vista **e** dallo stato accessi della scheda cliente e
  fornitore. Oggi lo calcola il BE (`portale_repository.get_stato_accessi…`, con i casi PENDING /
  NON_SPEDITO / DISATTIVO / ATTIVO): la regola va portata a DB **com'è**, con i suoi stati, e i pgTAP
  ne costruiscono uno per stato.
* RLS e contesto: la vista si legge dall'area amministrazione (porta SUPER_ADMIN). Va verificato che
  in quel contesto restituisca tutte le righe: con RLS e senza contesto **zero righe non è un dato**.

### R-DB-A2-bis — La vista «Di sistema»

Una riga per credenziale di categoria `SISTEMA`: username, tipo (processo automatico / `API_CLIENT`),
il **processo** collegato (`dbops.processi_identita`) con l'emittente, l'attivo dell'identità, il
blocco, l'ultimo accesso. Il FE apre il drawer del processo dalla riga.

### R-DB-A3 — La configurazione delle liste

Seed delle liste configurabili `anagrafiche.accessi_altri` e `anagrafiche.accessi_sistema`
(`ui/lista*.csv`): colonne, ricerca (nome, username, email, soggetto; per il sistema anche processo
ed emittente), filtri (veste, stato, nessun accesso, bloccata, secondo fattore; per il sistema
processo e tipo).
Etichette con `etichetta_i18n_key`: le chiavi nuove vanno segnalate al FE (`check_i18n_keys`).

## 4. Ricadute BE (dopo §3)

* **Spegnimento (R-DB-1)**: `disabilita_operatore`, `riattiva_operatore` e `_set_identita_state`
  smettono di scrivere `ruolo_applicativo`; `count_admin_attivi` perde il secondo controllo.
* **Stato della veste (A-7)**: lo stato accessi della scheda cliente e fornitore
  (`portale_repository`) legge la regola DB e ritira il calcolo nel BE.
* **Categoria (R-DB-A1)**: `_VESTE_OPERATORE` e `SOLO_VESTE_OPERATORE` in
  `amm_software_repository.py` si ritirano in favore dell'oggetto DB.
* **Liste**: `GET /amm-software/accessi/altri/` e `GET /amm-software/accessi/sistema/`, porta
  `AdminAPIView`, sulle viste di R-DB-A2 e R-DB-A2-bis.
* **Le azioni della credenziale escono da `/operatori/`.** Il secondo fattore è un'azione della
  **credenziale**, non della veste operatore, ma oggi sta in `operatori/<id>/secondo-fattore/…`. Nuova
  sede unica `credenziali/<auth_user_id>/…`, usata dai tab «Operatori» e «Altri accessi». Le rotte
  vecchie si ritirano nello stesso giro (siamo in sviluppo: ammesso il breaking change).
* **Azioni della credenziale** (A-4, A-5):
  * secondo fattore: stato, obbligo, disattivazione (esistono, si spostano);
  * **blocca** (con motivo) e **sblocca**: le funzioni DB esistono (`script.fn_blocca_credenziale`,
    `script.fn_sblocca_credenziale`, guard SUPER_ADMIN), ma oggi nessun endpoint le espone.
* Nessun nuovo codice d'errore previsto.

## 5. Ricadute FE

* Menu: la voce `operatori` diventa `accessi` (`/amm-software/accessi`), tre tab con il tab nella
  query. Il link vecchio `/amm-software/operatori` porta al tab «Operatori»: niente link rotti.
* Tab «Operatori»: la lista di oggi; il badge «Disabilitato» (anche in `PermessiRiepilogoView`) si
  legge da `attivo`/`is_active` dopo R-DB-1, non dal ruolo. `RUOLO_APPLICATIVO.DISABILITATO` va
  cercato in tutti i suoi consumatori al momento del giro (router, login, store auth, drawer).
* Tab «Altri accessi»: `<ListaConfigurabile codice="anagrafiche.accessi_altri">`; vesti come badge con
  lo stato, `Nessun accesso` in evidenza; drawer in sola lettura con le azioni della credenziale e il
  link alla scheda del soggetto collegato.
* Tab «Di sistema»: `<ListaConfigurabile codice="anagrafiche.accessi_sistema">`, sola lettura, il
  clic sulla riga apre il drawer del processo automatico collegato.
* Regola del 2: il pannello del secondo fattore di oggi (`OperatoreSecondoFattore.vue`) diventa il
  pannello della **credenziale**, usato dal drawer operatore e da quello degli altri accessi. Lo
  stesso vale per il blocco.

## 6. Fuori perimetro, dichiarato

* Chi governa le vesti non cambia: l'operatore dall'amministrazione, cliente e fornitore dal loro
  drawer in anagrafiche (`views_invito_portale.py`), lo shop anche dal profilo portale, gli utenti
  di sistema dal pannello dei processi automatici.
