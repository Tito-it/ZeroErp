# Brief DB → BE/FE — L'area «Accessi» e la veste operatore spenta

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-02. **A chi:** team DB (`dev/db-tid`)
> per §3; poi BE/FE (§4, §5).
> **Origine:** revisione delle modifiche BE sul riuso della credenziale (D-6, «una persona, una
> credenziale») e discussione con Tid sulla lista operatori, 2026-10-02.
> **Stato:** ✅ **giro DB scritto, applicato su dbdev e pgTAP verdi (Tid, 2026-10-02; §7).** ⏳ Ora tocca
> al BE: **R-BE-a per primo** (§7.8). Il resto della testata qui sotto è del momento della scrittura. Tutte le richieste di §3
> (R-DB-1, R-DB-2, R-DB-A1, A2, A2-bis, A3) hanno il loro changeSet o seed. **Da leggere per
> primo: §7.11** (i passi di Tid, in ordine: prima dell'apply c'è una query da lanciare), poi
> §7.8 (BE) e §7.9 (FE). ⚠️ Dopo l'apply, «disabilita operatore» del BE fallisce finché il BE non
> smette di scrivere `DISABILITATO` (§7.8, R-BE-a): la finestra va tenuta corta.
> ~~Ordine suggerito al team DB: R-DB-1 per primo~~ (fatto in quest'ordine).
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

---

## 7. Risposta del team DB (2026-10-02, `dev/db-tid`)

> **Chi scrive:** sessione DB, 2026-10-02. **A chi:** Tid (§7.11), team BE (§7.8), team FE (§7.9).
> Niente è applicato né committato.

### 7.1 Esito, in una tabella

| # | Esito | Dove |
| --- | --- | --- |
| **R-DB-1** | ✅ la veste operatore si spegne con `attivo = false` e tiene il tipo. `DISABILITATO` resta nell'enum come voce **storica** e la tabella viva lo rifiuta (CHECK più guard). Le righe di oggi si convertono; una riga non riconducibile ferma il migrate e viene elencata | `20261002-22`, `-25`, `-26`, `-27`, `-28`, `-29`, `-30` |
| **R-DB-A1** | ✅ `script.fn_categoria_accesso(auth_user_id)` → `OPERATORE` / `SISTEMA` / `ALTRO`. La precedenza è stata decisa sul modello: **una credenziale non può essere insieme di una persona e di una macchina**. Lo impone un guard nuovo e lo controlla il presidio | `-20`, `-21`, `-23`, `-24` |
| **R-DB-A2** | ✅ `anagrafiche.vw_accessi_altri`; lo stato di una veste sta solo a DB (`script.fn_stato_veste`, A-7) | `-31`, `-32`, `-33` |
| **R-DB-A2-bis** | ✅ `anagrafiche.vw_accessi_sistema` | `-34` |
| **R-DB-2** | ✅ `dbops.vw_credenziali_da_sanare` più la sua riga nel catalogo `dbops.presidi` | `-35`, `presidi.csv` |
| **R-DB-A3** | ✅ le liste `anagrafiche.accessi_altri` (104) e `anagrafiche.accessi_sistema` (105) | `ui/lista_*.csv` |

Codici d'errore nuovi: `E_RUOLO_APPLICATIVO_RITIRATO` (TECNICO, id 1186) ed
`E_CREDENZIALE_PERSONA_E_SISTEMA` (DATO_ERRATO, id 1187). A `E_UTENTE_DISABILITATO` sono state
riscritte causa e soluzione, che nominavano `ruolo_sistema` e una vista ritirata.

### 7.2 R-DB-1 — la veste spenta tiene il tipo

**Il valore `DISABILITATO` nell'enum: resta.** È una scelta di modello: `storico.identita_digitali`
conserva le versioni passate delle vesti spente, con il tipo che avevano allora. Toglierlo dal tipo
vorrebbe dire riscrivere la storia, e anche ricreare le circa 30 funzioni che nominano
`config.ruolo_applicativo`. Quindi:

* **CHECK** `chk_identita_digitali_ruolo_non_ritirato` sulla tabella viva;
* il **guard di coerenza** lo rifiuta prima del CHECK, con `E_RUOLO_APPLICATIVO_RITIRATO` (un
  guard `BEFORE ROW` parla sempre prima di un CHECK). Esce in anticipo ormai solo su `API_CLIENT`,
  quindi **l'operatore spento viene controllato come quello acceso**, come chiedeva il brief;
* il `COMMENT` del tipo lo dichiara voce storica.

**La conversione** (`-25`, nello stesso changeSet del CHECK e prima di lui) ricava il tipo dalla
stessa struttura che il guard pretende:

* `tecnica` con soggetto_ruolo `PROC_AUTO` → OPERATORE;
* persona con una risorsa umana sul soggetto_ruolo → OPERATORE;
* in tutti e due i casi `attivo = false`. `DISABILITATO` voleva dire spenta: lasciare acceso
  un `attivo = true` incoerente avrebbe acceso un accesso che oggi non c'è.

⛔ Una riga che non rientra in nessuno dei due casi (V-4) **ferma il migrate e viene elencata**,
prima di toccarne qualunque altra. Su un DB costruito da zero la tabella a quel punto è vuota.

**Il censimento dei lettori** (doc auto-generata, 2026-10-02). Dopo R-DB-1 cambia significato
ogni lettore che filtra `ruolo_applicativo = 'OPERATORE'` **senza** guardare `attivo`: prima le
vesti spente dall'amministratore ne restavano fuori da sole, perché erano `DISABILITATO`. Su 35
oggetti:

* chi confrontava con `'DISABILITATO'` ora legge solo `attivo`:
  * `fn_sync_auth_user_is_active` (`-26`);
  * `fn_get_profili_accesso_applicabili`, due rami (`-27`);
  * `fn_get_user_profile` (`-29`);
* ⭐ **una regressione evitata.** `fn_get_user_profile` cercava la veste con un LEFT JOIN su
  (credenziale, OPERATORE) e un `SELECT INTO` senza ORDER BY. Con una credenziale riusata che ha
  una veste spenta e una accesa poteva prendere la spenta e rifiutare il login. La regola giusta,
  «l'accesa, altrimenti la spenta più recente», era già scritta in `fn_get_operatore_detail`.
  Ora sono due lettori, quindi è diventata il building block `script.fn_veste_di_riferimento`
  (`-28`) e la copia è stata ritirata (`-30`, regola del 2);
* gli altri filtrano già `attivo = true` (`fn_has_identita_attiva`, `fn_is_super_admin_account`,
  `fn_get_setup_status`, `fn_get_uo_id_for_user`, le viste dei processi…): sono immuni;
* `fn_totp_disabilita_device` nomina `TOTP_DISABILITATO`, che è un evento e non c'entra.

**Conseguenze, dichiarate.** Si leggono dal modello, ma vanno viste:

1. ⚠️ **Un operatore disattivato dall'amministratore diventa invitabile**, se ha una veste sola:
   `fn_check_operatore_invitabile` vede una veste OPERATORE spenta, e l'invito riapre una veste
   spenta (D-3). Prima era `SENZA_VESTE_OPERATORE`. ⇒ **Da confermare, Tid**: a video, sulla
   riga di un operatore disattivato compare «Invita». Riattivarlo con un invito vuol dire una
   password nuova. In alternativa resta «Riattiva».
2. `fn_crea_operatore_v2` con l'email di un operatore disattivato risponde
   `E_CREDENZIALE_GIA_OPERATORE`, invece di creare una seconda veste operatore sulla stessa
   credenziale. È ciò che il suo commento già prometteva («attiva o spenta»).
3. `fn_get_operatore_detail` mostra l'operatore disattivato **per intero**. Prima usciva con i
   campi vuoti, il difetto di §1.2.
4. `E_UTENTE_DISABILITATO`: il segnaposto ora è lo **username**, nei due rami che lo sollevano.
   Prima erano una frase intera, che il messaggio «Utente disabilitato: %s» ripeteva, e l'id della
   risorsa umana.

**Registrati, non aperti.** Nei corpi di `fn_crea_operatore_v2` e
`trgfn_identita_digitali_sync_auth_user_active` restano commenti che nominano DISABILITATO, senza
apici e quindi senza confronti. Non vale ricreare due funzioni per un commento: si correggono al
prossimo giro su di loro. Il pgTAP 12 di `test-veste-operatore-spenta-v1` presidia che nessuna
funzione confronti più col letterale citato.

### 7.3 R-DB-A1 — la categoria, una per credenziale

* `script.fn_veste_di_sistema(ruolo, tecnica)`: è il **predicato unico** «questa veste è di una
  macchina» (`API_CLIENT` oppure `tecnica`). Lo leggono la categoria, il guard e il presidio.
* `script.fn_categoria_accesso(auth_user_id)`: `SISTEMA` se c'è una veste di sistema, poi
  `OPERATORE` se c'è una veste OPERATORE, altrimenti `ALTRO`, comprese le credenziali senza vesti.
  **Contano anche le vesti spente**: una persona disattivata resta nel suo tab (V-3).
* **La precedenza, sul modello.** Il modello **non ammette** una credenziale insieme persona e
  macchina, per due ragioni:
  * una credenziale è una password sola per tutte le porte;
  * le sue azioni (blocco, secondo fattore) valgono per tutte le sue vesti: bloccare la persona
    fermerebbe il processo.

  Lo impone il guard `anagrafiche.trgfn_identita_digitali_guard_natura_credenziale`
  (`-23`/`-24`, BEFORE INSERT / UPDATE OF auth_user_id, ruolo_applicativo, tecnica), che risponde
  `E_CREDENZIALE_PERSONA_E_SISTEMA`. Le righe nate prima del guard, e una gara fra due transazioni,
  le segnala il presidio (§7.6). Per quelle sole righe, nel CASE `SISTEMA` vince su `OPERATORE`:
  il tab «Di sistema» è in sola lettura, e una credenziale che regge un processo non si blocca da
  una lista di persone.
* Nella forma di R-DB-1: `OPERATORE` = una veste OPERATORE non tecnica. La regola è scritta
  **una** volta.

### 7.4 R-DB-A2 — «Altri accessi», e lo stato di una veste

**`script.fn_stato_veste(identita_id)` → (`stato`, `token_scade_at`)** (A-7). La regola è
portata **com'era** nel BE (`portale_repository.stato_veste`):

| Stato | Quando |
| --- | --- |
| `ATTIVO` | veste accesa |
| `PENDING` | spenta, con un invito pendente, e l'email di quel token è partita (`invito_inviato_at >=` emissione) |
| `NON_SPEDITO` | spenta, con un invito pendente, ma l'email di quel token non è partita |
| `DISATTIVO` | spenta, nessun invito pendente |

`NESSUNO` non è uno stato di una veste, è l'assenza della riga: resta a chi cerca la veste.

⚠️ **Una differenza dal BE, dichiarata.** Il BE filtrava anche il **tipo** del token sui due della
porta. Qui no: il token di una veste si riconosce dall'`identita_id` nel meta, che oggi scrive
**solo** l'emissione di un invito (`InvitoVeste.emetti`, letto il 2026-10-02; il reset password
scrive `richiesto_da`). Ricopiare a DB la mappa delle porte sarebbe stata una seconda copia di una
costante del BE. Il punto da guardare: un token **non d'invito** che un giorno porti
`identita_id`.

**`script.fn_credenziali()`** è l'accessore plpgsql di `django.auth_user`. Senza, le credenziali
senza veste non si vedono, e una vista non può nominare `django.*`.

**`anagrafiche.vw_accessi_altri`** (`security_invoker`): una riga per credenziale `ALTRO`.

| Colonna | Note |
| --- | --- |
| `auth_user_id`, `username`, `email`, `nome`, `cognome` | stringhe vuote di Django rese NULL |
| `nome_visualizzato` | nome e cognome della credenziale, altrimenti lo username. ⚠️ Non il soggetto della veste: per un cliente azienda è l'azienda |
| `vesti` (jsonb) | una voce per veste, anche spenta: `identita_id`, `ruolo_applicativo`, `stato`, `attivo`, `valido_dal`, `valido_al`, `invito_inviato_at`, `token_scade_at`, `soggetto_id`, `soggetto_ruolo_id`, `soggetto`, **`cliente_ids` (array)**, `fornitore_id` |
| `vesti_elenco`, `soggetti_elenco` | testo, per filtro e ricerca |
| `nessun_accesso` | nessuna veste |
| `stato_accesso` | **riassunto per il filtro**: il migliore fra le vesti, `ATTIVO > PENDING > NON_SPEDITO > DISATTIVO`, `NESSUNO` senza vesti |
| `is_active` | il flag di Django |
| `secondo_fattore_stato` | da `fn_get_totp_device`, solo lo stato: `ASSENTE` / `DA_CONFERMARE` / `ATTIVO` |
| `secondo_fattore_obbligatorio` | da `fn_totp_obbligatorio` |
| `bloccata`, `bloccata_dal`, `motivo_blocco` | da `config.credenziali` |
| `ultimo_accesso` | `last_login` |

⚠️ **`cliente_ids` è un array, non un id.** `anagrafiche.clienti` non è unica su
`soggetto_ruolo_id` (un cliente per istanza utility): una veste cliente può avere più schede, e
sceglierne una vorrebbe dire scegliere per id. **Decisione aperta al FE**: con uno si apre quella
scheda; con più di uno, un elenco o la scheda del soggetto.

⚠️ La vista attraversa `anagrafiche.clienti`, che ha la RLS. Letta senza contesto, gli array
`cliente_ids` escono vuoti; le righe no.

### 7.5 R-DB-A2-bis — «Di sistema»

**`anagrafiche.vw_accessi_sistema`** (`security_invoker`): una riga per credenziale `SISTEMA`.

| Colonna | Note |
| --- | --- |
| `auth_user_id`, `username` | |
| `tipo` | `PROCESSO` se c'è una veste con `tecnica`, altrimenti `API_CLIENT`. Con tutte e due vince `PROCESSO`, che ha un processo da aprire |
| `vesti_elenco` | |
| `identita_attiva` | almeno una veste accesa |
| `processo_id`, `processo_codice`, `processo_descrizione`, `processo_attivo`, `legame_processo_attivo` | da `dbops.processi_identita`: al più uno, è UNIQUE sull'utente |
| `emittente_fiscale_id`, `emittente_codice`, `emittente_ragione_sociale` | da `config.user_emittenti_fiscali`: al più uno |
| `is_active`, `bloccata`, `bloccata_dal`, `motivo_blocco`, `ultimo_accesso` | |

Niente secondo fattore: su una macchina non ha senso (A-6).

### 7.6 R-DB-2 — il presidio

**`dbops.vw_credenziali_da_sanare`** (`auth_user_id`, `username`, `motivo`):

* `NESSUNA_VESTE` si legge da `vw_accessi_altri.nessun_accesso`, una regola sola come chiedeva il
  brief. Le credenziali con **sole vesti spente** non entrano (V-3);
* `PERSONA_E_SISTEMA` riporta le credenziali miste di §7.3.

Riga nel catalogo: `ZERO`, `SETTIMANALE`, `LIBERO`. Il conteggio non dipende dalla RLS, che tocca
solo gli array `cliente_ids`.

### 7.7 R-DB-A3 — le liste

**`anagrafiche.accessi_altri`** (104, vista `vw_accessi_altri`): `perimetro_emittente = false`,
perché una credenziale non appartiene a un'azienda, e `multi_emittente = false`.

* Colonne: nome, username, email (nascosta), accessi (`vesti_elenco`, il FE disegna i badge da
  `vesti`), stato, nessun accesso, soggetti collegati (nascosta), secondo fattore, secondo fattore
  obbligatorio (nascosta), bloccata, ultimo accesso, azioni.
* Filtrabili: nome, username, accessi, stato, nessun accesso, secondo fattore, obbligo, bloccata.
* Ordinabili: nome, username, stato, nessun accesso, secondo fattore, bloccata, ultimo accesso.

**`anagrafiche.accessi_sistema`** (105, vista `vw_accessi_sistema`): `perimetro_emittente = true`
e `multi_emittente = true`, come `anagrafiche.operatori`. Ogni utente tecnico lavora per **una**
azienda, e il super admin le vede tutte.

* Il biglietto multi-emittente è la colonna attiva `emittente_codice`.
* Colonne: username, tipo, processo, descrizione processo (nascosta), emittente, ragione sociale
  emittente (nascosta), attiva, bloccata, ultimo accesso. Nessuna colonna azioni (sola lettura).
* Filtrabili: username, tipo, processo, emittente, attiva, bloccata.

Allineati i due elenchi pgTAP: liste globali (`test-lista-definizione-perimetro-emittente-v1`
test 6) e liste multi-emittente (`test-lista-definizione-multi-emittente-v1` test 5). La soglia
di ricerca è 3, quindi niente da toccare nel terzo elenco.

### 7.8 Al team BE

| # | Cosa | Note |
| --- | --- | --- |
| **R-BE-a** ⛔ | `disabilita_operatore`, `riattiva_operatore`, `_set_identita_state`, `update_operatore(attivo=…)` smettono di scrivere `ruolo_applicativo`: spegnere vuol dire solo `attivo = false`. `count_admin_attivi` perde il secondo controllo | **Bloccante dall'apply**: chi scrive ancora `DISABILITATO` riceve `E_RUOLO_APPLICATIVO_RITIRATO` (TECNICO, 500) |
| **R-BE-b** | Categoria: il tab Operatori legge `script.fn_categoria_accesso(au.id) = 'OPERATORE'`. Si ritirano `_VESTE_OPERATORE` e `SOLO_VESTE_OPERATORE` | il riepilogo permessi uguale |
| **R-BE-c** | Stato accessi della scheda cliente e fornitore: dopo aver trovato la veste, `SELECT stato, token_scade_at FROM script.fn_stato_veste(%s)`. Si ritira `stato_veste` in `portale_repository`. `NESSUNO` (nessuna veste) resta del BE | A-7. Il filtro sul tipo del token cade: §7.4 |
| **R-BE-d** | `GET /amm-software/accessi/altri/` e `/sistema/` su `anagrafiche.vw_accessi_altri` e `vw_accessi_sistema`. La whitelist d'ordinamento è quella di §7.7; la mappa va in `WHITELIST_BE` di `scripts/gen_seed_lista.py` | ⚠️ Se la SELECT elenca le colonne invece di `v.*`, deve portarle tutte quelle di §7.4 e §7.5 |
| **R-BE-e** ⚠️ | Registrare le due liste nei test Django che leggono il seed: `test_perimetro_emittente_copertura` (`accessi_altri` è globale come le liste di amministrazione in `_ESENZIONI`; `accessi_sistema` ha perimetro, come `anagrafiche.operatori`) e la dichiarazione della ricerca full (`test_ricerca_full_seed`) | **Rossi dall'arrivo del seed DB** finché non è fatto: va nel primo passo del giro BE |
| **R-BE-f** | `E_CREDENZIALE_PERSONA_E_SISTEMA` può arrivare dall'invito portale e da `fn_crea_operatore_v2`, quando l'email è di un utente tecnico: è un DATO_ERRATO sull'email | se c'è un traduttore per `campo`, è `email` |
| **R-BE-g** | Rigenerare `error_policies_generated.py` (`manage.py genera_error_policies`): entrano `E_RUOLO_APPLICATIVO_RITIRATO` (TECNICO) ed `E_CREDENZIALE_PERSONA_E_SISTEMA` (DATO_ERRATO, banner di default: nessun override necessario) | `test_error_policies_divergenza_db` è rosso dall'apply finché non è fatto |
| — | blocca e sblocca: `script.fn_blocca_credenziale` e `fn_sblocca_credenziale` esistono già (§4) | nessun lavoro DB |

### 7.9 Al team FE

* **11 chiavi i18n nuove** (il seed le dichiara, `check_i18n_keys` le segnala):
  `amministrazione.accessi.col_bloccata`, `col_identita_attiva`, `col_nessun_accesso`,
  `col_processo`, `col_processo_descrizione`, `col_secondo_fattore`,
  `col_secondo_fattore_obbligatorio`, `col_soggetti`, `col_tipo`, `col_ultimo_accesso`,
  `col_vesti`.
* La colonna «Accessi» è legata a `vesti_elenco` per filtro e ricerca. I badge si disegnano con
  uno slot da `row.vesti`, una voce per veste con `ruolo_applicativo` e `stato`.
* Vocabolari da tradurre:
  * stati della veste: `ATTIVO` / `PENDING` / `NON_SPEDITO` / `DISATTIVO`, più `NESSUNO` per
    `stato_accesso`;
  * secondo fattore: `ASSENTE` / `DA_CONFERMARE` / `ATTIVO`;
  * tipo: `PROCESSO` / `API_CLIENT`.
* Tab «Di sistema»: il clic apre il drawer del processo con `processo_id`. È NULL per un
  `API_CLIENT`.
* `cliente_ids` è un array: decisione aperta, §7.4.
* `RUOLO_APPLICATIVO.DISABILITATO`: dopo R-BE-a non arriva più da nessuna veste. I suoi consumatori
  (router, login, store auth, drawer) si ritirano, come previsto in §5.

### 7.10 Le prove (2026-10-02)

dbdev non era raggiungibile dalla sessione. La prova si è fatta su un **cluster PostgreSQL 18
usa-e-getta**, con queste caratteristiche:

* tabelle stub minime;
* le funzioni da cui il giro dipende col **corpo vero** dalla doc auto-generata
  (`fn_guard_soggetto_ruolo`, `fn_get_totp_device`, `fn_get_auth_user_stato`,
  `fn_check_operatore_invitabile`, `trgfn_identita_digitali_sync_auth_user_active`);
* le cinque funzioni che il giro cambia nella loro versione **viva** di oggi;
* l'SQL dei 16 changeSet **estratto dagli YAML**, applicato in una transazione sola.

Esito:

* **24/24 verdi**. Coprono:
  * conversione e CHECK, e il CHECK da solo a guard spento: `23514`;
  * categoria per credenziale, guard sulla natura nei due versi;
  * ordine dei guard: la coerenza parla prima della natura;
  * le due viste, riga per riga;
  * stati della veste: `NON_SPEDITO`, poi `PENDING` a pari `now()`;
  * veste di riferimento e profilo: l'accesa con una spenta più recente, poi tutte spente;
  * dettaglio dell'operatore convertito;
  * presidio nei due motivi, con la categoria `SISTEMA` sulla credenziale mista.
* **Mutazione**: senza il trigger della natura diventano rossi i casi 6, 7, 8, 12 e 15.
* **Rollback** dei 16 changeSet in ordine inverso: passa, le funzioni nuove spariscono e
  `fn_sync` torna quella di oggi.
* **V-4**: una veste DISABILITATO senza tipo ricavabile ferma il migrate con l'elenco
  (`identita 50 (credenziale 5, soggetto_ruolo 4, tecnica f)`) e non tocca nessuna riga.
* Le colonne del seed delle liste esistono tutte nelle viste vere; gli ordinamenti di default
  anche.
* Guardrail statici verdi: run_on_change, precondition_seed, ddl su trigger, grant batch, letterali
  SQL, timestamp, preambolo pgTAP.

**Non coperto, e resta di Tid:**

* i dati veri di dbdev;
* la RLS come applicazione;
* `plpgsql_check` (test-riferimenti-morti);
* la corsa pgTAP (sotto).

pgTAP **nuovi**:

* `anagrafiche/test-veste-operatore-spenta-v1.sql` (12, come app);
* `anagrafiche/test-area-accessi-v1.sql` (17, owner: costruisce un utente tecnico, stesso
  criterio di `test-fn-scope-identita-processo`).

pgTAP **toccati**, perché scrivevano `DISABILITATO` che ora la tabella rifiuta:

* `test-crea-operatore-riusa-credenziale-v1`: la persona fisica è ora una veste SHOP_CUSTOMER
  sullo stesso soggetto;
* `test-fn-sync-auth-user-is-active-or` (4, 5);
* `test-sync-auth-user-is-active-multi-role` (9);
* `test-permessi-funzioni-risoluzione` (29, gli helper);
* `test-vw-processi-roster` (7: API_CLIENT);
* `test-fn-scope-ba-ownership-ruolo-aware` (4: API_CLIENT);
* i due elenchi delle liste.

Presidi trasversali da rilanciare:

* `dbops/test-riferimenti-morti-v1`;
* `dbops/test-catalogo-presidi-v1`;
* `rls/test-rls-viste-security-invoker`;
* `script/test-catalogo-messaggi-errore-completo`;
* `ui/test-lista-*`.

**Dopo l'apply, due rossi corretti (team DB, 2026-10-02).** Erano errori dei test, non del
database. Rilanciati da Tid: ✅ **verdi, nessuna regressione** nella corsa.

* `anagrafiche/test-area-accessi-v1.sql`, test 11: `concat_ws` scrive un booleano come `t`, e
  l'atteso era `true`. La vista era giusta. Corretto con `a.nessun_accesso::text`, la stessa forma
  del test 10.
* `rls/test-rls-clienti.sql`, fixture: l'identità SHOP_CUSTOMER nasceva sulla credenziale
  dell'operatore di `fn_pgtap_crea_emittente_operatore`, che è un **utente tecnico**. Il guard
  della natura (`trg_identita_digitali_a10_guard_natura_credenziale`) la rifiuta, ed è la regola
  di questo giro che fa il suo lavoro. Ora la veste shop ha un `auth_user` suo; il test 9
  (stesso proprietario, canali SHOP e ADMIN) è invariato.
  Censiti gli altri pgTAP che usano quell'operatore e creano una veste di persona
  (`test-fn-scope-ba-ownership`, `-ruolo-aware`, `test-fn-scope-ef-whitelist`,
  `test-rls-fatture-residuo`, `test-rls-fondi-fattura-source-functional`): si costruiscono già
  credenziali loro, e non hanno il problema.
* ⭐ Lezione: un guard nuovo sulla **natura** di una credenziale va censito anche sulle **fixture**
  che riusano la credenziale di un helper (`fn_pgtap_crea_emittente_operatore` dà un utente
  tecnico), non solo sui test che scrivono la colonna cambiata.

### 7.11 I passi di Tid, in quest'ordine

1. **Prima dell'apply, su dbdev**: le vesti DISABILITATO senza un tipo ricavabile (V-4). Sono
   quelle che fermerebbero `-25`, e vanno cancellate a mano:

   ```sql
   SELECT idg.id, idg.auth_user_id, idg.soggetto_ruolo_id, idg.tecnica
     FROM anagrafiche.identita_digitali idg
    WHERE idg.ruolo_applicativo = 'DISABILITATO'
      AND NOT ((idg.tecnica AND EXISTS (SELECT 1 FROM anagrafiche.soggetti_ruoli sr
                                          JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
                                         WHERE sr.id = idg.soggetto_ruolo_id
                                           AND tr.codice_interno = 'PROC_AUTO'))
            OR (NOT idg.tecnica AND EXISTS (SELECT 1 FROM anagrafiche.risorse_umane ru
                                             WHERE ru.soggetto_ruolo_id = idg.soggetto_ruolo_id)));
   ```

   ⚠️ L'`UPDATE` di conversione passa dai trigger della tabella. Su una riga DISABILITATO con
   `attivo = true` e legami di scope attivi, il blocco dei figli lo ferma, e lo dice: è voluto.
2. **Apply.** Le note del migrate dicono quante vesti sono state convertite.
3. **pgTAP**: i due nuovi, i toccati e i trasversali di §7.10.
4. **Subito dopo, R-BE-a**: fino ad allora «disabilita operatore» fallisce.
5. Confermare la conseguenza 1 di §7.2: l'operatore disattivato si può reinvitare.
