# Brief DB — Il pannello di configurazione scrive con un verbo

> **Chi scrive:** team DB (`dev/db-tid`), 2026-09-25. **A chi:** Tid (decisioni,
> §4), poi team DB e team backend/frontend (§6).
> **Origine:** decisione **D-3** di
> [brief-db-permesso-nel-verbo-di-scrittura.md](brief-db-permesso-nel-verbo-di-scrittura.md)
> (§7.1), con la **D-5** per la forma del permesso. È il secondo brief operativo
> del modello, dopo [brief-db-magazzino-verbi-con-permesso.md](brief-db-magazzino-verbi-con-permesso.md).
> **Stato: ✅ CHIUSO il 2026-09-28.** Tutte le parti sono fatte, applicate e
> committate. La D-P9 (`20260928-30`) è stata applicata su dbdev alle 11:48, e la
> corsa pgTAP di Tid non ha regressioni.
>
> **Stato al 2026-09-28:**
>
> | Parte | Stato |
> | --- | --- |
> | Decisioni | ✅ **D-P1 → D-P9 decise da Tid** (§4): D-P1…D-P5 sulla proposta del DB, D-P6 e D-P7 sulla proposta del backend (§4.1), D-P8 e D-P9 il 27 e il 28-09 |
> | DB | ✅ `20260925-29…-34` applicati e committati (`7f3208a58`). ✅ **D-P6 chiusa**, applicata il 2026-09-27 (00:34): pgTAP verdi, nessuna regressione. ✅ **Applicati su dbdev il 2026-09-27 (01:00), pgTAP verdi** (§6.1): `config.aree_funzionali` fuori dal pannello (D-P8), la funzione unica delle colonne scrivibili (`20260927-21`, `-22`) e il `CHECK (NOT pannello OR lookup)` (`20260927-20`). ✅ **D-P9 applicata il 2026-09-28** (§4.2): `90_end/20260928-30`, loop dei grant, provisioning, pgTAP. Nessuna regressione |
> | Backend | ✅ **Chiuso.** §6 committato in `e7dbbad73` (commit che nel messaggio cita il brief del blocco login): verbo, lista a DB, `REL_CONSENTITE` ritirata, area da `fn_area_di_oggetto`, 403 sull'oggetto nella forma della D-P7. §6.1 committato in `5bd689163` il 2026-09-28: il metadata legge `config.fn_pannello_colonne_scrivibili`, `_EXCLUDED_COLUMNS` ritirata |
> | Frontend | ✅ **Chiuso**, committato in `5bd689163` il 2026-09-28: registro `config-tables.js` ritirato (D-P5), il pannello legge `GET /core/config/tables/`; «Salva» spento in modifica quando il delta è vuoto |
>
> **In una riga:** il pannello «Gestione tabelle» scrive su 87 tabelle con SQL
> costruito nel backend, e chiede sempre il livello `TUTTO` sull'area
> Configurazione, qualunque sia la tabella. Qui diventa **un verbo DB** che
> controlla il livello sull'**oggetto** a cui la riga appartiene, e la lista delle
> tabelle ammesse diventa **un dato del DB** al posto della costante del backend.

---

## 1. Il punto di partenza — letto il 2026-09-25

Fatti datati, letti dal codice e dal catalogo di dbdev. Descrivono da dove si
parte: non decidono la forma.

### 1.1 Come scrive oggi il pannello

* **Due operazioni sole**: `INSERT` e `UPDATE` per `id`. Nessun `DELETE`: una riga
  si ritira con un `PATCH` su `attivo` o `obsoleto_dal`, che sono colonne come le
  altre (`core/db/config_crud_repository.py`, `create_record` e `update_record`).
* **Le colonne** si leggono da `information_schema`; ne sono escluse `data_insert`,
  `user_insert`, `data_update`, `user_update`, `tx_id`, `storicizza`, `uid`. La
  chiave è **sempre** `id` (`config_metadata_repository.py`).
* ⚠️ **Una chiave del payload che non è una colonna viene scartata in silenzio**, e
  un payload tutto sconosciuto diventa un `INSERT` che non fa niente (`{}`) o un
  «non trovato» sull'`UPDATE`.
* **Il nome della tabella** entra nell'SQL per interpolazione, dopo il controllo
  `rel in REL_CONSENTITE` nel service.
* **Il permesso**: le quattro view (`core/api/views_config_crud.py`) dichiarano
  `area_funzionale = "config"`; `POST` e `PATCH` chiedono `TUTTO` su **config**.

### 1.2 La lista ammessa

* `REL_CONSENTITE` (`core/db/dbops_repository.py`), **87 voci distinte**: 61 in `config`,
  le altre in `anagrafiche`, `catalogo`, `documenti`, `magazzino`, `pagamenti`,
  `pratiche`, `ui`, `vendite`.
* ⭐ **Serve a due cose**, e questo conta per il disegno:
  * è la whitelist del **lookup generico** (`dbops.fn_get_lookup_codici`), cioè le
    tendine di tutta l'applicazione;
  * è l'elenco delle tabelle del **pannello**, lette e scritte.
* Ne esiste una terza copia nel frontend, `frontend/src/core/config-tables.js`
  (il registro con le etichette), legata alla prima da un test Django.

### 1.3 Quello che il modello non sapeva

* ⛔ **Quasi nessuna tabella della lista ha un model Django**: il backend ne
  dichiara 15 in tutto, quasi tutti del sistema permessi. La D-5 voleva nominare
  l'oggetto con `app_label` + `model_name` «che il catalogo ha già»: per il
  pannello **non c'è**.
* ⭐ **Una convenzione però esiste**, ed è già in due sedi: la chiave
  `(schema, nome logico)`. È quella di `config.area_model_overrides` (per esempio
  `('anagrafiche', 'soggetto')`) e dei model riservati dell'interfaccia permessi
  (`('config', 'profili_accesso')`, `amm_software_repository.py`). L'area per
  default è il primo pezzo della chiave (area = schema, guida
  architettura-permessi §6.2).
* **Quattro tabelle della lista hanno la RLS attiva**: `magazzino.magazzini`,
  `magazzino.ubicazioni`, `pagamenti.enti_incasso`, `vendite.listini`. Due hanno
  anche il guard di perimetro sull'emittente (`magazzini`, `listini`). Le altre 83
  sono cataloghi senza perimetro.
* **Tredici tabelle della lista hanno anche endpoint propri** che scrivono con SQL
  diretto: fra le altre `magazzino.magazzini` e `ubicazioni` (piano del
  2026-09-21), `vendite.listini`, `ui.lista_definizione`, `pratiche.template_flussi`,
  `catalogo.unita_misura`, `config.email_account`.
* Nessun test Django esegue una scrittura vera del pannello sul DB.

## 2. Il problema, sul modello

1. **Il permesso guarda l'area sbagliata.** Chi ha `TUTTO` su Configurazione e
   `LETTURA` su Magazzino crea causali di magazzino dal pannello: il livello si
   chiede sull'area del **pannello**, non su quella della **riga**. È il difetto
   del §7.1 del brief del modello.
2. **Il DB non applica niente.** L'app ha `INSERT`/`UPDATE` su tutte le 87 tabelle.
3. **La lista vive nel backend**, in tre copie (costante, registro FE, test).

## 3. Il disegno proposto

### 3.1 La lista a DB: `config.tabelle_gestibili`

Una tabella di catalogo, un CSV in `80_data` (una tabella, un CSV):

| Colonna | Cosa dice |
| --- | --- |
| `id`, `codice` | la riga; `codice` = `schema.tabella` |
| `schema_tabella`, `nome_tabella` | la tabella fisica |
| `app_label`, `model_name` | **l'oggetto** a cui la riga appartiene (D-5), con la convenzione `(schema, nome logico)` del §1.3 — vedi D-P1 |
| `lookup` | la tabella serve al lookup generico (le tendine) |
| `pannello` | la tabella si gestisce dal pannello |
| `attivo`, audit | come ogni catalogo |

⭐ **Due capacità in una riga, non due liste.** Oggi la stessa costante vale per
tutte e due; una tabella può restare nelle tendine e uscire dal pannello (D-P2).

L'area **non è una colonna**: si ricava dall'oggetto (§3.2). Scriverla qui sarebbe
una seconda sede della regola «area di un oggetto».

Un presidio pgTAP lega la lista al catalogo: ogni riga esiste come tabella, ha
una colonna `id`, e **nessuna riga con `pannello = true` ha la RLS attiva**
(§3.4).

### 3.2 I due building block del permesso sull'oggetto

* **`script.fn_area_di_oggetto(p_app_label, p_model_name)`**, check pura: l'area
  da `area_model_overrides` se c'è un override, altrimenti `app_label` (area =
  schema). Oggi la stessa regola la fa **il backend**, in Python
  (`PermissionResolver.get_area_schema_db`, `core/services/permissions_resolver.py:310`):
  la sede diventa il DB, e il backend la chiama (richiesta al §6). Senza questo
  passo il verbo ne sarebbe una seconda copia.
* **`script.fn_guard_livello(p_auth_user_id, p_app_label, p_model_name, p_livello_minimo)`**,
  il gemello di `fn_guard_azione` previsto dalla D-2 e dalla D-5. Chiede a
  `fn_resolve_livello_oggetto` (override utente sull'oggetto, poi l'area, già col
  gate di contesto dal 24-09) e solleva `E_PERMESSO_NEGATO` se il livello è sotto
  il minimo, anche a utente `NULL`. INVOKER.

### 3.3 Il verbo: `config.fn_pannello_scrivi(p_tabella, p_id, p_dati)`

* `p_tabella` è il `codice` della lista, `p_id` NULL = inserimento, altrimenti
  modifica di quella riga; `p_dati` è un `jsonb`. Ritorna la riga scritta come
  `jsonb`, senza le colonne escluse.
* **SECURITY DEFINER del proprietario**, `search_path` bloccato (stampo dei verbi
  di magazzino).
* **Passo 0:** la tabella è nella lista con `pannello = true` e `attivo`,
  altrimenti rifiuto. **Passo 1:** `fn_guard_livello(utente, app_label,
  model_name, 'TUTTO')`, con l'oggetto **della riga di lista**.
* **Colonne:** quelle del catalogo meno le escluse (le stesse di oggi, più `id`).
  I valori li converte PostgreSQL (`jsonb_populate_record` sul tipo di riga),
  quindi date, numeri e `jsonb` hanno la conversione del DB, non quella del
  driver.
* **Chiavi sconosciute nel payload: rifiuto**, non scarto silenzioso (D-P3).
* I trigger delle tabelle (audit, `ATTIVO`, guard di codice, storico) scattano
  come oggi: il verbo non li sostituisce.
* Nessun `DELETE`, come oggi.

### 3.4 Il perimetro: perché la lista non ammette tabelle con RLS

Come DEFINER il verbo non vede la RLS. Per i verbi di magazzino il perimetro l'ha
rimesso il verbo stesso, con il predicato della policy nella `WHERE`. Un verbo
**generico** non può farlo: ogni tabella ha la sua policy, e ricopiarle nel verbo
sarebbe una seconda sede di ciascuna. ⇒ **Il pannello gestisce solo tabelle
senza perimetro**, e il verbo lo verifica al passo 0 (`relrowsecurity`), non si
fida della lista. Le quattro tabelle con RLS escono dal pannello (D-P2): hanno già
tutte endpoint propri.

### 3.5 La porta

* Si chiude **per dominio**, come deciso in D-3: l'app perde
  `INSERT`/`UPDATE`/`DELETE` sulle tabelle della lista dei domini che adottano il
  modello, oggi **`magazzino`**. Nel loop dei grant (`v_tabelle_sola_lettura_app`)
  e nel provisioning, non con un `REVOKE` in un changeSet.
* ⚠️ Delle tre tabelle di magazzino nella lista, **solo `causali`** resta nel
  pannello. `magazzini` e `ubicazioni` hanno RLS ed endpoint propri che scrivono
  con SQL diretto: chiuderle chiede i **loro** verbi, un lavoro del cantiere
  magazzino (D-P4).
* Le tabelle degli altri domini restano scrivibili anche direttamente finché il
  loro dominio non passa al modello. La lista a DB lo può dire: le tabelle
  «chiuse» sono quelle del loop.

## 4. Decisioni — di Tid

| # | Domanda | Proposta |
| --- | --- | --- |
| **D-P1** | Come si nomina l'**oggetto** di una tabella senza model Django (§1.3)? | ✅ **DECISA da Tid il 2026-09-25, sulla proposta:** **Con la convenzione che esiste già, `(schema, nome tabella)`**: `app_label = 'magazzino'`, `model_name = 'causali'`. È la chiave di `area_model_overrides` e dei model riservati; un override utente su quell'oggetto funziona senza niente di nuovo. Precisa la D-5 («la chiave che il catalogo ha già»): per il pannello la chiave c'è, ma è la convenzione, non il model |
| **D-P2** | Le quattro tabelle con RLS (`magazzini`, `ubicazioni`, `enti_incasso`, `listini`) | ✅ **DECISA da Tid il 2026-09-25, sulla proposta:** **Escono dal pannello e restano nelle tendine** (`pannello = false`, `lookup = true`). Il verbo generico non sa rimettere un perimetro senza ricopiare le policy (§3.4); tutte e quattro hanno già endpoint propri |
| **D-P3** | Una chiave del payload che non è una colonna | ✅ **DECISA da Tid il 2026-09-25, sulla proposta:** **Rifiuto** con un codice registrato, invece dello scarto silenzioso di oggi (AGENTS: non normalizzare in silenzio). Cambia il comportamento per un client che manda campi in più: da dire al frontend |
| **D-P4** | `magazzino.magazzini` e `ubicazioni`: chi li chiude | ✅ **DECISA da Tid il 2026-09-25, sulla proposta:** **Un brief a sé del cantiere magazzino**, con i loro verbi (perimetro come in `fn_posta_*`). Questo brief chiude solo `causali`. Finché non si fa, `magazzino` è un dominio **a metà** (§5 del modello), e la sua guida lo deve dire con l'elenco |
| **D-P5** | La terza copia della lista, `config-tables.js` nel frontend | ✅ **DECISA da Tid il 2026-09-25, sulla proposta:** **Si ritira** a favore della lista a DB, con le etichette dalle chiavi i18n per convenzione. Decisione da prendere col team FE: qui la si segnala. ⚠️ **Sospesa fino alla D-P6** (§4.1): ritirare il registro oggi metterebbe a video 19 tabelle che non devono stare nel pannello |
| **D-P6** | Le righe con `pannello = true` che il pannello non deve gestire (§4.1) | ✅ **DECISA da Tid il 2026-09-25 (sera), sulla proposta del backend:** **`pannello = false` su tutte e 19, `lookup` resta `true`.** Richiesta al team DB: si corregge il CSV `tabelle_gestibili.csv`, nessun changeSet di codice |
| **D-P7** | Il 403 del backend sull'**oggetto della riga**, quando l'oggetto dipende dall'URL (§4.1) | ✅ **DECISA da Tid il 2026-09-25 (sera), sulla proposta del backend:** **un aggancio nella catena di `ZeroERPPermission`**: la view dichiara come ricava l'oggetto dalla richiesta, e la catena chiede il livello su quell'oggetto al posto dell'area fissa. Vale per **scritture e letture** del pannello (`TUTTO` e `LETTURA` sull'oggetto). Senza richiesta — la valutazione sulla sola classe, come per i tool dell'assistente — nega. Lavoro del backend |
| **D-P8** | `config.aree_funzionali` nel pannello (§4.1) | ✅ **DECISA da Tid il 2026-09-27:** **esce dal pannello** (`pannello = false`, resta nelle tendine). La sua gestione va in un accesso riservato all'amministrazione (D-P9). Fatto nel CSV, §6.1 |
| **D-P9** | Dove e come si gestisce `config.aree_funzionali`, fuori dal pannello | ✅ **DECISA da Tid il 2026-09-28: strada A, sola lettura.** Nessuna modifica dall'applicazione: nome (`descrizione`) e ordine (`ordinamento`) si cambiano nel CSV, e il migrate successivo li porta ovunque. Il CSV resta l'unico padrone della tabella. Scartata la B (modifica di nome e ordine in `amm_software`, SUPER_ADMIN): verbo, endpoint e drawer, e il CSV declassato a valore iniziale, per un'operazione rara che il CSV fa già. Vedi §4.2 |

### 4.1 D-P6 e D-P7 — cosa ha trovato il backend (2026-09-25, sera)

**D-P6 — la lista del pannello è più larga di quella gestita.** Il CSV ha
`pannello = true` su 83 righe: è la copia di `REL_CONSENTITE`, cioè di ciò che il
backend **accettava** in scrittura, non di ciò che il pannello **mostra**. Il
registro del frontend ne mostra 65 (64 senza `pagamenti.enti_incasso`, che esce
per la D-P2). Le 19 in più, in due gruppi:

| Gruppo | Tabelle | Perché fuori dal pannello |
| --- | --- | --- |
| **Hanno una casa propria**, con endpoint che scrivono e il loro cancello | `config.profili_accesso` (`amm_software`, solo SUPER_ADMIN), `ui.lista_definizione` (`ui`, solo SUPER_ADMIN), `config.email_account` (credenziali SMTP, `email_repository`), `vendite.famiglie_documento` (`famiglie_repository`), `anagrafiche.categorie_clienti` (`categorie_clienti_repository`), `catalogo.uom_tipi` (`catalogo_repository`) | Il pannello sarebbe una **seconda strada** per scriverle, che salta il cancello della prima |
| **Vocabolari di sistema**, caricati dal seed in `80_data` e letti dal codice per codice | `config.esiti_flussi_pratiche`, `config.listini_tipologie`, `config.modi_approvvigionamento`, `config.nature_doc_fiscale`, `config.nature_vendita`, `config.registri_giornale`, `config.stati_doc_offerte`, `config.stati_fornitore`, `config.tipi_titolo_iva`, `documenti.render_engine_documento`, `documenti.tipi_asset_documento`, `documenti.tipi_documento_output`, `documenti.tipi_file_documento` | Li possiede il CSV: una modifica dal pannello cambierebbe un codice che il dominio interpreta, o sparirebbe al migrate successivo |

⛔ **Il caso che l'ha fatta emergere**: `config.profili_accesso` risolve sull'area
`config`. Oggi, e anche col verbo, chi ha `TUTTO` su Configurazione modifica i
**profili di permesso** con una chiamata diretta all'API del pannello, cioè si alza
i privilegi senza passare dal cancello SUPER_ADMIN di `amm_software`. Il frontend
lo nascondeva solo perché non elencava la tabella. È un difetto del modello, non
del verbo: il verbo applica fedelmente una lista sbagliata.

**Richiesta al team DB:** `pannello = false` sulle 19 righe nel CSV
`80_data/sql/config/tabelle_gestibili.csv`, e un presidio pgTAP che lo fissi almeno
per `config.profili_accesso` (la riga il cui errore alza i privilegi). Resteranno 64
righe nel pannello, le stesse del registro del frontend, che a quel punto si ritira
(D-P5).

✅ **Fatto dal team DB il 2026-09-27, applicato su dbdev lo stesso giorno (00:34, `RERAN`), pgTAP verdi senza regressioni.**

* **CSV**: le 19 righe hanno `lookup = true`, `pannello = false`. Il seed è il
  mirror `loadUpdateData` `20260925-30` (`runOnChange`, `validCheckSums: ANY`):
  al prossimo migrate riscrive le righe per `id`. Non serve un changeSet nuovo.
  Nel suo YAML è aggiornato solo il commento. Le 64 righe rimaste coincidono con
  le `rel` di `frontend/src/core/config-tables.js`, confrontate il 2026-09-27.
* **pgTAP**:
  * `config/test-pannello-porta-v1` passa a 8 test. Il 7 non ha più eccezioni:
    `ui.lista_definizione`, l'unica riga del pannello con un'area fuori catalogo,
    è uscita. L'8 è nuovo e fissa `config.profili_accesso` con `lookup` sì e
    `pannello` no.
  * `config/test-fn-pannello-scrivi-v1`: il 12 prima provava `ui.lista_definizione`,
    ora esce dal pannello. Al suo posto c'è il caso che ha fatto emergere la
    D-P6: con `TUTTO` su Configurazione, il verbo rifiuta `config.profili_accesso`
    già al passo 0 (`E_PANNELLO_TABELLA_NON_AMMESSA`).
  * Il caso «area fuori catalogo ⇒ negato» resta provato in
    `script/test-fn-guard-livello-v1` (11).
* **Prova** su `zeroerp_ci` da owner, in una transazione annullata, con il CSV
  caricato da `\copy` sulla tabella: porta 6/8 (il 3 e il 4 sono rossi da owner,
  come dichiarato nel file) e verbo 14/14. Dopo l'apply la corsa di Tid, come
  app, è verde. ⚠️ Non è stata fatta la controprova sul CSV vecchio, cioè vedere
  il 7, l'8 e il 12 andare in rosso. Resta vero per costruzione: nel CSV vecchio
  `profili_accesso` aveva `pannello = true`.
* **Pagina `manual/`** `config/manual/tabelle_gestibili.md`: nella sezione «Cosa
  non ci può stare» ci sono ora le due famiglie.
* ⚠️ **Al backend**, ora che è applicato: `GET /core/config/tables/` elenca 64 righe.
  Le 19 escono anche dalle **scritture** del pannello via API, non solo dalla
  vista. Da ricontrollare i test che contano le righe del pannello
  (`test_config_panel_registro_db`) e la pagina `docs/it/backend/core/manual/api_config_tables.md`.

✅ **Deciso il 2026-09-27 (D-P8)**: `config.aree_funzionali` era nel pannello, e
anche nel registro del frontend, sull'area `config`. È il catalogo delle aree su
cui poggiano i permessi, e chi aveva `TUTTO` su Configurazione poteva modificarlo.
Appartiene alla stessa famiglia di `profili_accesso`, quindi esce dal pannello. Dove
va la sua gestione è la D-P9.

**D-P7 — il 403 del backend.** Il §6 chiede che l'endpoint chieda «lo stesso
livello sulla stessa area» del verbo. Le quattro view del pannello dichiaravano
`area_funzionale = "config"` fisso, e la catena legge solo attributi di classe.
Scartata l'alternativa di un controllo nel corpo di POST e PATCH lasciando `config`
sulla classe: il backend chiederebbe `TUTTO` su Configurazione **e** sull'oggetto,
mentre il DB chiede solo l'oggetto — due regole per la stessa scrittura.

### 4.2 D-P9 — `config.aree_funzionali` in `amm_software`: cosa si può fare

Fatti letti dalla struttura il 2026-09-27:

* **Il seed possiede tutte le colonne.** `80_data/changelog/20260228-17` è un
  mirror `loadUpdateData` in `runOnChange`, e ricarica **ogni** colonna dal CSV,
  `descrizione` e `ordinamento` comprese, a ogni modifica del file. Una modifica
  fatta a mano da un'interfaccia sparirebbe al primo cambio del CSV.
* **`schema_db` è la chiave dei permessi.** `fn_resolve_livello_area` e
  `fn_area_di_oggetto` risolvono i livelli su quel valore, e per convenzione
  coincide con lo schema. Cambiarlo stacca profili e override di un'area intera.
* **Un'area nuova è un modulo nuovo**: nasce con il suo schema e con il suo
  codice, quindi nasce nel CSV, non da un'interfaccia. Lo stesso vale per il
  ritiro di un'area.
* Nessuno nel backend scrive `config.aree_funzionali`, fuori dal pannello di
  prima.

| Strada | Che cosa vuol dire | Costo |
| --- | --- | --- |
| **A — sola lettura** (proposta del DB) | In `amm_software` le aree si **vedono**: codice, descrizione, schema, profili che le usano. Non si modificano: le possiede il CSV. La porta si chiude: `zeroerp_app` perde `INSERT`/`UPDATE`/`DELETE` sulla tabella (loop `v_tabelle_sola_lettura_app` e provisioning, come `tabelle_gestibili`) | Lato DB un passo nel loop dei grant, più un pgTAP. Lato backend niente, oltre alla vista in sola lettura se la si vuole |
| **B — modifica di etichetta e ordine** | Il SUPER_ADMIN cambia `descrizione` e `ordinamento`, non `schema_db`, e non crea né cancella aree. Serve un verbo `fn_aree_funzionali_aggiorna` con `script.fn_guard_super_admin`. ⚠️ Le due colonne escono dall'elenco `columns` del mirror, altrimenti il CSV le riscrive, e il CSV diventa il valore iniziale e non più il padrone | Un changeSet di codice, la modifica del mirror, i pgTAP, un endpoint `amm_software` e il suo drawer |

⭐ **Proposta: A.** La B introduce un padrone in più per una tabella che oggi ne
ha uno solo, il CSV.
⚠️ **Correzione del 2026-09-28**: la prima stesura diceva che le etichette a
video passano dalle chiavi i18n. È falso per le aree: le schermate dei permessi
(`PermessiRiepilogoView`, `RepartoProfiloEditor`, `OperatorePermessiTab`)
mostrano `aree_funzionali.descrizione`. Un cambio di nome nel CSV quindi si vede
a video, ed è per questo che la A basta.

✅ **Decisa da Tid il 2026-09-28: A.**

**Richiesta al team DB (D-P9):**

1. `config.aree_funzionali` in sola lettura per l'app: `v_tabelle_sola_lettura_app`
   nel loop `20260205-41` più il blocco nel provisioning, come `tabelle_gestibili`
   (P-4). Un changeSet `90_end` di revoke sullo stampo di `20260925-34`.
2. Un pgTAP nella porta (`config/test-pannello-porta-v1` o uno suo): l'app non
   ha `INSERT`/`UPDATE`/`DELETE` sulla tabella.
3. Nella pagina `manual/` della tabella, una riga: si modifica solo dal CSV.

Al backend niente: nessuno scrive la tabella fuori dal pannello di prima (§4.2).

✅ **Fatto dal team DB il 2026-09-28, provato e applicato su dbdev (11:48); corsa pgTAP senza regressioni.**

| Pezzo | File | Cosa |
| --- | --- | --- |
| Forward | `90_end/20260928-30-revoke-app-scrittura-aree-funzionali` | All'app resta solo `SELECT` su `config.aree_funzionali`. Stampo di `20260925-34` |
| Loop | `90_end/ci_apply/20260205-41` | `config.aree_funzionali` in `v_tabelle_sola_lettura_app`, con la voce nell'intestazione |
| Provisioning | `scripts/sql/provision_db_roles.sql` | La riga entra nel blocco della porta del pannello, accanto a `causali` e `tabelle_gestibili` |
| pgTAP porta | `config/test-pannello-porta-v1` (da 9 a 11) | 10: sul catalogo, `SELECT` sì e scrittura no. 11: come app, `UPDATE … SET id = id WHERE false` dà `42501` |
| pgTAP censito | `config/test-permessi-strutture-base` (12-13 dell'elenco) | Erano l'unico scrittore della tabella come app: due `INSERT` duplicati che aspettavano `23505`. Dopo la chiusura avrebbero preso `42501`. ⛔ Il marcatore `owner` non era la risposta, perché la fixture scriveva dove l'app non scrive. Ora sono due `col_is_unique` su `codice` e `schema_db` |
| `manual/` | `config/manual/aree_funzionali.md` | Nuova sezione «Chi la scrive»: solo il CSV |

**Censo degli scrittori** (2026-09-28): il backend non scrive la tabella, e nemmeno
le funzioni e i trigger della doc auto-generata o dei `20_code`. Fra i pgTAP la
scriveva solo il file qui sopra.

**Prova** su `zeroerp_ci` da owner, con l'SQL estratto dal YAML e in una
transazione annullata:

* controprova senza il forward: il 10 e l'11 sono rossi. Il test vede il difetto;
* col forward la porta fa 8/11: il 10 è verde; il 3, il 4 e l'11 sono rossi da
  owner, come dichiarato nel file;
* `test-permessi-strutture-base` fa 22/22;
* dopo il `ROLLBACK` il privilegio dell'app su `zeroerp_ci` è invariato;
* guardrail statici verdi: `runOnChange`, ruolo batch, trigger di automazione,
  `preCondition`, letterali, preambolo pgTAP (debito `throws_ok` fermo a 117).

✅ **Applicato il 2026-09-28**: `20260928-30` è `EXECUTED` su dbdev, e l'app non ha
più `UPDATE` sulla tabella (letto sul catalogo). Corsa pgTAP di Tid senza regressioni.

## 5. I passi

| Passo | Stato |
| --- | --- |
| **P-0** | ✅ **2026-09-25.** Le 87 voci di `REL_CONSENTITE` esistono tutte e hanno `id`. L'`id` nasce identity in 86; ⚠️ **`vendite.stati_commessa` non ha default sull'`id`**: dal pannello non si inserisce, né prima né ora (il backend escludeva già `id`) — fatto dichiarato, non corretto. Due tabelle hanno già una chiave d'oggetto in `area_model_overrides`: `catalogo.unita_misura` coincide con la convenzione, **`vendite.listini` è `('vendite', 'listino')`** e il CSV usa quella. Chi scrive `magazzino.causali` come app: nessuno nel backend, un pgTAP al runner `owner` |
| **P-1** | ✅ Scritto. `00_schema/config/20260925-29-create-config-tabelle-gestibili`: `codice_interno` = `schema.tabella` (CHECK), oggetto con CHECK di forma, `lookup` e `pannello`, niente `attivo` (una riga con i due flag spenti è ritirata). `80_data/changelog/20260925-30-seed-tabelle-gestibili` + `80_data/sql/config/tabelle_gestibili.csv`: 87 righe, `lookup` tutte, `pannello` 83 (fuori le quattro con RLS) |
| **P-2** | ✅ Scritto. `20_code/script/20260925-31-create-fn-area-di-oggetto` (plpgsql, perché il presidio dei riferimenti morti vede solo il plpgsql) e `-32-create-fn-guard-livello`. ⛔ L'enum `livello_accesso` è ordinato `TUTTO < LETTURA < BLOCCATO`: il rifiuto è `livello > minimo`, pinnato nei due versi dal pgTAP |
| **P-3** | ✅ Scritto. `20_code/config/20260925-33-create-fn-pannello-scrivi`. **Nessuna funzione di lettura**: il backend legge la lista con un `SELECT`, che l'app ha. Quattro codici nuovi in `codici_errore.csv` e `messaggi_errore.csv` (id 1134…1137): `E_PANNELLO_TABELLA_NON_AMMESSA` (TECNICO), `E_PANNELLO_DATI_VUOTI`, `E_PANNELLO_CAMPO_NON_AMMESSO` (DATO_ERRATO, con `campo`), `E_PANNELLO_RIGA_NON_TROVATA` (NON_TROVATO) |
| **P-4** | ✅ Scritto. `90_end/20260925-34-revoke-app-scrittura-pannello-magazzino` + `v_tabelle_sola_lettura_app` nel loop `20260205-41` + blocco nel provisioning: in sola lettura per l'app **`magazzino.causali`** e **`config.tabelle_gestibili`** (la lista è una porta: il verbo scrive come proprietario su ogni tabella che vi compare) |
| **P-5** | ✅ Scritto e provato. `script/test-fn-guard-livello-v1` (12), `config/test-fn-pannello-scrivi-v1` (14), `config/test-pannello-porta-v1` (7). **Prova** su `zeroerp_ci` come proprietario, SQL estratto di `-29`, `-31…-34` più il CSV (con `\copy`: il `loadUpdateData` non è provato, la sua forma è quella del seed `20260919-09`) e i quattro codici, in transazione annullata: `plpgsql_check` a zero sulle tre funzioni; guard 12/12, verbo 14/14, porta 5/7 — rossi il 3 e il 4, veri solo come app (dichiarato nel file). Due difetti trovati nei test e corretti: `format('%s')` su un booleano scrive `t`; il 4 della porta, da proprietario, inseriva davvero una riga e sporcava il 6 (ora `WHERE false`). Guardrail statici verdi |
| **P-6** | ✅ Brief e pagine `manual/` (`tabelle_gestibili`, `fn_pannello_scrivi`, `fn_guard_livello`, `fn_area_di_oggetto`). ✅ **2026-09-28**: guida `architettura-permessi-e-autorizzazioni.md` (§7 riscritto: perimetro e permesso; §7.4 il verbo, §7.5 il pannello; §4.1, §5, §6.2, §10) e `PROJECT_CONTEXT` |

✅ **Tid:** apply su dbdev (19:16, codici compresi) e corsa col runner **verde**, come app (i due rossi «da owner» della porta sono verdi) — presidi trasversali compresi, presidi trasversali compresi (`test-riferimenti-morti-v1`; `test-rubinetto-primo-motivo-v1` non si sposta).

## 6. Ricadute sul backend e sul frontend

Stato al 2026-09-25 (sera). Dal 2026-09-27 risulta **committato** in `e7dbbad73` (arrivato su `dev/db-tid` col merge di `Tito-dev`).

| Richiesta | Stato |
| --- | --- |
| **Il repository del pannello chiama il verbo** al posto dell'SQL costruito; le mappe dei vincoli (`_mappe_vincoli`) restano | ✅ `ConfigCrudRepository.scrivi_record` → `config.fn_pannello_scrivi`; il payload arriva intero, i campi estranei li rifiuta il DB |
| **`REL_CONSENTITE` si ritira nello stesso giro**: lookup e pannello leggono la lista dal DB | ✅ BB `TabelleGestibiliRepository` (`core/db/tabelle_gestibili_repository.py`): `voce(rel)`, `rel_lookup()`, `voci_pannello()`. Le 87 voci verificate identiche alla costante prima di toglierla |
| **L'area di un oggetto la dà `script.fn_area_di_oggetto`** | ✅ `PermissionResolver.get_area_schema_db` la chiama: la query riscritta in Python è sparita |
| **Il 403 del backend resta**, sullo stesso livello e sulla stessa area del verbo | ✅ Forma **D-P7**: la view dichiara `oggetto_permesso_da_richiesta()` (il mixin del pannello, letto dalla lista), `ZeroERPPermission.valuta` chiede il livello su quell'oggetto, in lettura e in scrittura; `None` (rel fuori dal pannello) ricade sull'area della classe e il service risponde 400; valutata sulla sola classe nega (`OGGETTO_SENZA_RICHIESTA`). Attributo documentato in api.md |
| ⚠️ **Effetto voluto** (§7.1 del modello): chi ha `TUTTO` solo su Configurazione non scrive più le tabelle degli altri domini | ✅ Provato sul DB vero (riga sotto). Qualche profilo andrà rivisto; non siamo in produzione |
| **Test Django** che scrivano davvero sul DB dal pannello | ✅ `core/tests/db/test_pannello_verbo_db` (7, opt-in `ZEROERP_TEST_DB_E2E=1`): porta chiusa su `causali`, crea e modifica col verbo, campo rifiutato col suo nome, riga assente, tabella del solo lookup; e i **due punti di applicazione** sullo stesso operatore costruito — con `LETTURA` sull'oggetto `magazzino.causali` la catena lascia leggere e non scrivere, e il verbo rifiuta da solo con `E_PERMESSO_NEGATO`; con `TUTTO` passano entrambi. La catena, a resolver mockato: `core/tests/api/test_views_config_crud` (7) |
| **I codici nuovi** (`E_PANNELLO_*`) nel catalogo generato; `E_PANNELLO_RIGA_NON_TROVATA` al posto di `E_ANAG_NOT_FOUND` | ✅ Policy e ripieghi rigenerati; `E_PANNELLO_RIGA_NON_TROVATA` anche per il dettaglio. ⚠️ `test_error_policies_divergenza_db` è rosso per `E_SCRITTURA_IN_LETTURA`, che arriva dal commit DB `501c5bcc8` (brief-be-letture-in-transazione-sola-lettura) non ancora nel branch: si rigenera dopo il merge, non prima |
| ⚠️ **Il frontend non deve mandare campi in più** (D-P3) | ✅ Verificato: `GenericConfigDrawer` costruisce il payload solo dalle colonne del metadata, che esclude `id`, audit, generate e identity `ALWAYS` come il verbo. 🟡 **Aperto**: in modifica il drawer manda solo il delta, quindi «Salva» senza modifiche mandava `{}` → `E_PANNELLO_DATI_VUOTI`. ✅ **Chiuso il 2026-09-28**: in `GenericConfigDrawer` il delta è un `computed` letto da `canSave`, e in modifica «Salva» è spento finché il delta è vuoto |
| Le quattro tabelle con RLS **escono dal pannello** (D-P2) | ✅ `pagamenti.enti_incasso` tolta dal registro del frontend (le altre tre non c'erano); l'elenco del backend legge `pannello` |
| **Il registro del frontend si ritira** (D-P5) | ✅ **2026-09-28.** `frontend/src/core/config-tables.js` cancellato; `ConfigTablePanel` legge `GET /core/config/tables/` (`listConfigTables`), raggruppa per schema e ordina per etichetta. Il presidio `test_config_panel_registro_db` legge ora la lista a DB, e il suo test 1 (registro ⊂ pannello) non ha più oggetto: al suo posto il confronto metadata ↔ `fn_pannello_colonne_scrivibili` |
| ✅ **Richiesta al team DB (revisione del 2026-09-25): le colonne scrivibili in una sede** — **decisa da Tid il 2026-09-27, lato DB applicata (§6.1)**. ⏳ Al backend: il metadata legge la funzione, e `_EXCLUDED_COLUMNS` si ritira — ✅ **fatto il 2026-09-28** (§6.1) | Le colonne che il pannello non scrive stanno in **due** posti: la costante `c_escluse` (più generate e identity `ALWAYS`) dentro `config.fn_pannello_scrivi`, e `_EXCLUDED_COLUMNS` più lo stesso filtro in `config_metadata_repository`. Se divergono, il form offre un campo che il salvataggio respinge. Proposta: una funzione, per esempio `config.fn_pannello_colonne_scrivibili(p_tabella) → text[]`, che il verbo usa al passo 2 e il metadata legge; il backend ritira la sua costante nello stesso giro. Fino ad allora la doppia sede è dichiarata nel codice |
| ✅ **Richiesta al team DB (revisione del 2026-09-25): `pannello` implica `lookup`** — **decisa da Tid il 2026-09-27, applicata (§6.1)** | Il pannello elenca le righe col lookup generico, quindi una riga con `pannello = true` e `lookup = false` sarebbe un pannello che risponde 400. Oggi è vero solo per come è scritto il CSV: nessun `CHECK` lo impone. Proposta: `CHECK (NOT pannello OR lookup)` su `config.tabelle_gestibili` |

### 6.1 Il giro del 2026-09-27 — D-P8 e le due richieste del backend

Scritto dal team DB il 2026-09-27, **applicato su dbdev lo stesso giorno (01:00)**: `-20`, `-21` e `-22` in `EXECUTED`, il seed `20260925-30` in `RERAN`, 63 righe nel pannello. Corsa pgTAP di Tid verde.

| Pezzo | File | Cosa |
| --- | --- | --- |
| D-P8 | `80_data/sql/config/tabelle_gestibili.csv` | `config.aree_funzionali` passa a `pannello = false`. Nel pannello restano 63 righe. Mirror `20260925-30`, che ha solo il commento aggiornato |
| `CHECK` | `00_schema/config/20260927-20-alter-tabelle-gestibili-pannello-implica-lookup` | `chk_tabelle_gestibili_pannello_implica_lookup CHECK (NOT pannello OR lookup)`. Su un database da zero nasce prima del seed, che lo rispetta |
| Sede unica | `20_code/config/20260927-21-create-fn-pannello-colonne-scrivibili` | `config.fn_pannello_colonne_scrivibili(p_tabella) → text[]`: le colonne scrivibili nell'ordine della tabella, `NULL` fuori dal pannello. Check pura, `STABLE`, `INVOKER`, `EXECUTE` all'app |
| Il verbo | `20_code/config/20260927-22-update-fn-pannello-scrivi-colonne-in-una-sede` | Il passo 2 chiama la funzione, e la costante `c_escluse` esce. ⚠️ Il passo 4 ritorna **`id` più le colonne scrivibili**, cioè i campi del form. Prima ritornava «tutto tranne le escluse»: una colonna generata o identity `ALWAYS` diversa da `id` non torna più. Firma e codici sono invariati |
| pgTAP | `config/test-pannello-porta-v1` (9), nuovo `config/test-fn-pannello-colonne-scrivibili-v1` (7) | Porta: l'8 fissa anche `aree_funzionali`, il 9 fissa il `CHECK`. Nuovo: la regola, il «fuori dal pannello = `NULL`», il verbo che ritorna i campi del form e che non ha più la sua copia, la forma |
| `manual/` | `fn_pannello_colonne_scrivibili.md` (nuova), `fn_pannello_scrivi.md`, `tabelle_gestibili.md` | — |

**Prova** su `zeroerp_ci` da owner, in una transazione annullata, con l'SQL
estratto dai tre YAML e il CSV caricato da `\copy`:

* porta 7/9: il 3 e il 4 sono rossi da owner, come dichiarato nel file;
* verbo 14/14;
* colonne scrivibili 7/7;
* `plpgsql_check` a zero sulle due funzioni;
* ramo costruito a mano: una tabella in lista con una colonna generata e una
  identity `ALWAYS` dà solo `{codice,descrizione}`;
* il `CHECK` respinge una riga `pannello` senza `lookup`.

⚠️ **Al backend, ora che è applicato:**

1. `config_metadata_repository` legge le colonne da
   `config.fn_pannello_colonne_scrivibili(rel)`, più `id` come chiave. Nello
   stesso giro si ritirano `_EXCLUDED_COLUMNS` e il filtro su generate e
   identity. Il commento «DUE SEDI» diventa storia.
2. La risposta del salvataggio porta solo `id` e i campi del form (passo 4).
3. `GET /core/config/tables/` elenca 63 righe.

✅ **Fatto dal backend il 2026-09-28** (non committato). (1)
`config_metadata_repository` filtra `information_schema.columns` su `id` più
`config.fn_pannello_colonne_scrivibili(rel)`; ritirati `_EXCLUDED_COLUMNS` e il
filtro su generate e identity. (2) `test_pannello_verbo_db` 2 verifica che la
riga scritta porti esattamente `id` più le colonne della funzione. (3) Nessun
test conta le righe; il presidio del registro itera le righe `pannello` della
lista a DB. Nuovo presidio: `test_config_panel_registro_db` 1 confronta,
tabella per tabella e nell'ordine, il metadata con la funzione. Suite mirata
sul DB vero verde (39 test). Pagina `manual/api_config_tables.md` allineata.

✅ **Al frontend:** `config.aree_funzionali` è uscita dal registro
`config-tables.js` il 2026-09-27 (con la sua etichetta
`config_panel.tabelle.config.aree_funzionali`, rimasta orfana): il presidio
`test_config_panel_registro_db` test 1 è tornato verde.

---

## Registro

| Data | Chi | Cosa |
| --- | --- | --- |
| 2026-09-25 | DB | Brief scritto dalla D-3 del brief del modello. Emersi dalla struttura: la lista serve anche al lookup (due capacità), le tabelle del pannello non hanno model Django (D-P1), quattro hanno la RLS (D-P2) |
| 2026-09-25 | Tid | D-P1 → D-P5 decise, tutte sulla proposta («ok 5 si») |
| 2026-09-25 | DB | **P-0 → P-6 lato DB scritti e provati** (`20260925-29…-34`), non applicati. Emersi: `vendite.stati_commessa` senza default sull'`id`; `vendite.listini` ha già la chiave `('vendite','listino')`; `ui.lista_definizione` ha un'area non a catalogo (solo SUPER_ADMIN, coerente coi suoi endpoint); la lista stessa va chiusa all'app |
| 2026-09-25 | Tid | `-29…-34` applicati su dbdev (19:16), mirror dei codici compreso. Verificato: COMMENT vivi uguali ai file, 87 righe (83 nel pannello), porta chiusa su `causali` e sulla lista |
| 2026-09-25 | Tid | Corsa pgTAP: **test verdi**. Lato DB chiuso; resta il backend (§6) |
| 2026-09-25 | BE | Verificato su dbdev: `EXECUTE` dell'app sul verbo e su `fn_area_di_oggetto`, `causali` e la lista in sola lettura, `config.iva` ancora scrivibile. Trovate 19 righe `pannello = true` fuori dal pannello del frontend, fra cui `config.profili_accesso` (privilegi alzabili dal pannello) |
| 2026-09-25 | Tid | D-P6 decisa (le 19 escono dal pannello: richiesta al DB, §4.1) e D-P7 decisa (aggancio nella catena dei permessi, scritture e letture). D-P5 sospesa fino alla D-P6. Aperta la domanda su `config.aree_funzionali` |
| 2026-09-25 | BE | **§6 scritto, non committato** (working tree di `dev/backend-tid`). `REL_CONSENTITE` ritirata: lookup, metadata e pannello leggono `config.tabelle_gestibili` (BB `TabelleGestibiliRepository`; le 87 voci verificate identiche alla costante prima di toglierla). Il pannello scrive **solo** col verbo (`ConfigCrudRepository.scrivi_record`), payload intero: i campi estranei li rifiuta il DB. `PermissionResolver.get_area_schema_db` chiama `fn_area_di_oggetto` (copie tornate a una). `E_PANNELLO_RIGA_NON_TROVATA` anche per il dettaglio. Il metadata esclude colonne generate e identity `ALWAYS`, come il verbo. Policy rigenerata (i quattro `E_PANNELLO_*`) e ripieghi. FE: `pagamenti.enti_incasso` tolta dal registro (D-P2). ⚠️ Il 403 sull'oggetto e' un mixin nelle view (`_PermessoSullOggettoMixin`, `check_permissions`), scritto prima della D-P7: da riportare alla sua forma. Prove: `test_pannello_verbo_db`, `test_views_config_crud`, `test_config_panel_registro_db` |
| 2026-09-25 | BE | **D-P7 applicata** (non committato): `ZeroERPPermission.valuta` legge `oggetto_permesso_da_richiesta()` dalla view e chiede il livello su quell'oggetto, con l'area di `fn_area_di_oggetto`; `None` ricade sull'area della classe; sulla sola classe nega con `OGGETTO_SENZA_RICHIESTA`. Il mixin del pannello non sovrascrive piu' `check_permissions`: dichiara l'oggetto e basta. Prove: `test_views_config_crud` (la catena, resolver mockato) e, sul DB vero, `test_pannello_verbo_db` 6-7 — un operatore COSTRUITO con `LETTURA` sull'oggetto `magazzino.causali` legge e non scrive, e il verbo lo rifiuta da solo con `E_PERMESSO_NEGATO`; con `TUTTO` passano catena e verbo. Suite intera verde (5164); `test_error_policies_divergenza_db` rosso per `E_SCRITTURA_IN_LETTURA`, del commit DB `501c5bcc8` (altro brief, non ancora nel branch): atteso, non rigenerato |
| 2026-09-25 | BE | Brief riallineato: stato in testa per parte, §6 con lo stato di ogni richiesta. Verificato il frontend: il payload del drawer generico viene dal metadata (nessun campo estraneo); **aperto** il «Salva» senza modifiche, che ora è `E_PANNELLO_DATI_VUOTI` |
| 2026-09-25 | BE | Revisione critica del non committato. Corretti: `_find_user` ingoiava ogni eccezione (un guasto del DB diventava «nome inesistente» e saltava il controllo del blocco dell'admin: ora fail-closed, test 9h); rimosso `get_editable_column_names`, rimasto senza chiamanti; il test delle rel del frontend nominava due rel a mano, ora le legge dal sorgente (80). Due richieste nuove al DB nel §6: colonne scrivibili in una sede, `CHECK (NOT pannello OR lookup)` |
| 2026-09-27 | DB | Stato riallineato: backend del §6 committato (`e7dbbad73`). **D-P6 scritta**: 19 righe a `pannello = false` nel CSV (mirror `20260925-30`, niente changeSet nuovo), `test-pannello-porta-v1` a 8 (il 7 senza eccezioni, l'8 fissa `profili_accesso`), il 12 di `test-fn-pannello-scrivi-v1` riscritto su `profili_accesso`. Provati su `zeroerp_ci` da owner. Da applicare; poi si sblocca la D-P5 |
| 2026-09-27 | Tid | D-P6 applicata su dbdev (seed `20260925-30` `RERAN`, 00:34): 64 righe nel pannello. Corsa pgTAP verde, nessuna regressione. Lato DB restano tre punti aperti, nessuno bloccante: `config.aree_funzionali` nel pannello (§4.1), le colonne scrivibili in una sede sola e il `CHECK (NOT pannello OR lookup)` (§6) |
| 2026-09-27 | Tid | D-P8 decisa: `aree_funzionali` fuori dal pannello, gestione in un accesso di amministrazione (D-P9, aperta: sede proposta `amm_software`). Accettate le due richieste del backend: colonne scrivibili in una sede, `CHECK (NOT pannello OR lookup)` |
| 2026-09-27 | DB | Scritti e provati su `zeroerp_ci`, non applicati: CSV (`aree_funzionali`), `20260927-20` (`CHECK`), `-21` (`fn_pannello_colonne_scrivibili`), `-22` (verbo sulla sede unica). pgTAP: porta a 9, nuovo `test-fn-pannello-colonne-scrivibili-v1` (7). §6.1 e §4.2 (D-P9: proposta A, sola lettura) |
| 2026-09-27 | Tid | `20260927-20…-22` e il seed applicati su dbdev (01:00), pgTAP verdi. Lato DB resta solo la D-P9. Al backend: metadata dalla funzione unica, ritiro di `_EXCLUDED_COLUMNS`, forma della risposta. Al frontend: D-P5 e `aree_funzionali` |
| 2026-09-28 | Tid | **D-P9 decisa: A** (sola lettura, nome e ordine si cambiano nel CSV). Richiesta al team DB in §4.2. Corretta un'affermazione del §4.2: il nome delle aree a video viene dalla tabella, non dall'i18n |
| 2026-09-28 | BE/FE | §6.1 fatto: metadata dalla funzione unica, `_EXCLUDED_COLUMNS` ritirata, presidio metadata ↔ funzione. D-P5 fatta: `config-tables.js` ritirato, il pannello legge la lista dall'API. «Salva» vuoto chiuso. La chiave i18n di `aree_funzionali` era già stata tolta il 27-09. Test BE mirati (39) e FE (467) verdi, build verde. Non committato. Poi P-6: guida dei permessi e PROJECT_CONTEXT aggiornati. Resta solo la D-P9 |
| 2026-09-28 | BE/FE | Backend e frontend committati e pushati in `5bd689163`. La parte BE/FE è chiusa |
| 2026-09-28 | DB | **D-P9 scritta e provata** (§4.2): forward `90_end/20260928-30`, loop `20260205-41`, provisioning, `test-pannello-porta-v1` passato a 11 test, `test-permessi-strutture-base` 12-13 riscritti sul catalogo, pagina `manual/`. Da applicare. È l'ultimo pezzo del brief |
| 2026-09-28 | Tid | `20260928-30` applicato (11:48), pgTAP senza regressioni. **Brief chiuso**, spostato in `work-done/` |
