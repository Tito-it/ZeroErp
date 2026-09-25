# Brief DB — Il pannello di configurazione scrive con un verbo

> **Chi scrive:** team DB (`dev/db-tid`), 2026-09-25. **A chi:** Tid (decisioni,
> §4), poi team DB e team backend/frontend (§6).
> **Origine:** decisione **D-3** di
> [brief-db-permesso-nel-verbo-di-scrittura.md](brief-db-permesso-nel-verbo-di-scrittura.md)
> (§7.1), con la **D-5** per la forma del permesso. È il secondo brief operativo
> del modello, dopo [brief-db-magazzino-verbi-con-permesso.md](../work-done/brief-db-magazzino-verbi-con-permesso.md).
> **Stato al 2026-09-25 (sera):**
>
> | Parte | Stato |
> | --- | --- |
> | Decisioni | ✅ **D-P1 → D-P7 decise da Tid** (§4): D-P1…D-P5 sulla proposta del DB, D-P6 e D-P7 sulla proposta del backend (§4.1) |
> | DB | ✅ `20260925-29…-34` applicati su dbdev (19:16), pgTAP verdi, committato (`7f3208a58`). 🔴 **Resta la D-P6**: 19 righe con `pannello = true` che non devono stare nel pannello, fra cui `config.profili_accesso` (§4.1) — **richiesta al team DB** |
> | Backend | ✅ **§6 fatto, non committato** (`dev/backend-tid`): verbo, lista a DB, `REL_CONSENTITE` ritirata, area da `fn_area_di_oggetto`, 403 sull'oggetto nella forma della D-P7. Suite verde (§6) |
> | Frontend | 🟡 **A metà** (§6): `enti_incasso` tolta dal registro (D-P2); il registro `config-tables.js` **resta** finché la D-P6 non è fatta (D-P5 sospesa); un punto aperto sul salvataggio senza modifiche |
> | Aperto | ❓ `config.aree_funzionali` nel pannello (§4.1) — da decidere |
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

❓ **Aperto, non deciso**: `config.aree_funzionali` è nel pannello (anche nel
registro del frontend) e sta sull'area `config`. È il catalogo delle aree su cui
poggiano i permessi: chi ha `TUTTO` su Configurazione può modificarlo. Da decidere
se appartenga alla stessa famiglia di `profili_accesso`.

**D-P7 — il 403 del backend.** Il §6 chiede che l'endpoint chieda «lo stesso
livello sulla stessa area» del verbo. Le quattro view del pannello dichiaravano
`area_funzionale = "config"` fisso, e la catena legge solo attributi di classe.
Scartata l'alternativa di un controllo nel corpo di POST e PATCH lasciando `config`
sulla classe: il backend chiederebbe `TUTTO` su Configurazione **e** sull'oggetto,
mentre il DB chiede solo l'oggetto — due regole per la stessa scrittura.

## 5. I passi

| Passo | Stato |
| --- | --- |
| **P-0** | ✅ **2026-09-25.** Le 87 voci di `REL_CONSENTITE` esistono tutte e hanno `id`. L'`id` nasce identity in 86; ⚠️ **`vendite.stati_commessa` non ha default sull'`id`**: dal pannello non si inserisce, né prima né ora (il backend escludeva già `id`) — fatto dichiarato, non corretto. Due tabelle hanno già una chiave d'oggetto in `area_model_overrides`: `catalogo.unita_misura` coincide con la convenzione, **`vendite.listini` è `('vendite', 'listino')`** e il CSV usa quella. Chi scrive `magazzino.causali` come app: nessuno nel backend, un pgTAP al runner `owner` |
| **P-1** | ✅ Scritto. `00_schema/config/20260925-29-create-config-tabelle-gestibili`: `codice_interno` = `schema.tabella` (CHECK), oggetto con CHECK di forma, `lookup` e `pannello`, niente `attivo` (una riga con i due flag spenti è ritirata). `80_data/changelog/20260925-30-seed-tabelle-gestibili` + `80_data/sql/config/tabelle_gestibili.csv`: 87 righe, `lookup` tutte, `pannello` 83 (fuori le quattro con RLS) |
| **P-2** | ✅ Scritto. `20_code/script/20260925-31-create-fn-area-di-oggetto` (plpgsql, perché il presidio dei riferimenti morti vede solo il plpgsql) e `-32-create-fn-guard-livello`. ⛔ L'enum `livello_accesso` è ordinato `TUTTO < LETTURA < BLOCCATO`: il rifiuto è `livello > minimo`, pinnato nei due versi dal pgTAP |
| **P-3** | ✅ Scritto. `20_code/config/20260925-33-create-fn-pannello-scrivi`. **Nessuna funzione di lettura**: il backend legge la lista con un `SELECT`, che l'app ha. Quattro codici nuovi in `codici_errore.csv` e `messaggi_errore.csv` (id 1134…1137): `E_PANNELLO_TABELLA_NON_AMMESSA` (TECNICO), `E_PANNELLO_DATI_VUOTI`, `E_PANNELLO_CAMPO_NON_AMMESSO` (DATO_ERRATO, con `campo`), `E_PANNELLO_RIGA_NON_TROVATA` (NON_TROVATO) |
| **P-4** | ✅ Scritto. `90_end/20260925-34-revoke-app-scrittura-pannello-magazzino` + `v_tabelle_sola_lettura_app` nel loop `20260205-41` + blocco nel provisioning: in sola lettura per l'app **`magazzino.causali`** e **`config.tabelle_gestibili`** (la lista è una porta: il verbo scrive come proprietario su ogni tabella che vi compare) |
| **P-5** | ✅ Scritto e provato. `script/test-fn-guard-livello-v1` (12), `config/test-fn-pannello-scrivi-v1` (14), `config/test-pannello-porta-v1` (7). **Prova** su `zeroerp_ci` come proprietario, SQL estratto di `-29`, `-31…-34` più il CSV (con `\copy`: il `loadUpdateData` non è provato, la sua forma è quella del seed `20260919-09`) e i quattro codici, in transazione annullata: `plpgsql_check` a zero sulle tre funzioni; guard 12/12, verbo 14/14, porta 5/7 — rossi il 3 e il 4, veri solo come app (dichiarato nel file). Due difetti trovati nei test e corretti: `format('%s')` su un booleano scrive `t`; il 4 della porta, da proprietario, inseriva davvero una riga e sporcava il 6 (ora `WHERE false`). Guardrail statici verdi |
| **P-6** | ✅ Brief e pagine `manual/` (`tabelle_gestibili`, `fn_pannello_scrivi`, `fn_guard_livello`, `fn_area_di_oggetto`). ⏳ La guida dei permessi e `PROJECT_CONTEXT` dopo l'apply |

✅ **Tid:** apply su dbdev (19:16, codici compresi) e corsa col runner **verde**, come app (i due rossi «da owner» della porta sono verdi) — presidi trasversali compresi, presidi trasversali compresi (`test-riferimenti-morti-v1`; `test-rubinetto-primo-motivo-v1` non si sposta).

## 6. Ricadute sul backend e sul frontend

Stato al 2026-09-25 (sera), tutto **non committato** su `dev/backend-tid`.

| Richiesta | Stato |
| --- | --- |
| **Il repository del pannello chiama il verbo** al posto dell'SQL costruito; le mappe dei vincoli (`_mappe_vincoli`) restano | ✅ `ConfigCrudRepository.scrivi_record` → `config.fn_pannello_scrivi`; il payload arriva intero, i campi estranei li rifiuta il DB |
| **`REL_CONSENTITE` si ritira nello stesso giro**: lookup e pannello leggono la lista dal DB | ✅ BB `TabelleGestibiliRepository` (`core/db/tabelle_gestibili_repository.py`): `voce(rel)`, `rel_lookup()`, `voci_pannello()`. Le 87 voci verificate identiche alla costante prima di toglierla |
| **L'area di un oggetto la dà `script.fn_area_di_oggetto`** | ✅ `PermissionResolver.get_area_schema_db` la chiama: la query riscritta in Python è sparita |
| **Il 403 del backend resta**, sullo stesso livello e sulla stessa area del verbo | ✅ Forma **D-P7**: la view dichiara `oggetto_permesso_da_richiesta()` (il mixin del pannello, letto dalla lista), `ZeroERPPermission.valuta` chiede il livello su quell'oggetto, in lettura e in scrittura; `None` (rel fuori dal pannello) ricade sull'area della classe e il service risponde 400; valutata sulla sola classe nega (`OGGETTO_SENZA_RICHIESTA`). Attributo documentato in api.md |
| ⚠️ **Effetto voluto** (§7.1 del modello): chi ha `TUTTO` solo su Configurazione non scrive più le tabelle degli altri domini | ✅ Provato sul DB vero (riga sotto). Qualche profilo andrà rivisto; non siamo in produzione |
| **Test Django** che scrivano davvero sul DB dal pannello | ✅ `core/tests/db/test_pannello_verbo_db` (7, opt-in `ZEROERP_TEST_DB_E2E=1`): porta chiusa su `causali`, crea e modifica col verbo, campo rifiutato col suo nome, riga assente, tabella del solo lookup; e i **due punti di applicazione** sullo stesso operatore costruito — con `LETTURA` sull'oggetto `magazzino.causali` la catena lascia leggere e non scrivere, e il verbo rifiuta da solo con `E_PERMESSO_NEGATO`; con `TUTTO` passano entrambi. La catena, a resolver mockato: `core/tests/api/test_views_config_crud` (7) |
| **I codici nuovi** (`E_PANNELLO_*`) nel catalogo generato; `E_PANNELLO_RIGA_NON_TROVATA` al posto di `E_ANAG_NOT_FOUND` | ✅ Policy e ripieghi rigenerati; `E_PANNELLO_RIGA_NON_TROVATA` anche per il dettaglio. ⚠️ `test_error_policies_divergenza_db` è rosso per `E_SCRITTURA_IN_LETTURA`, che arriva dal commit DB `501c5bcc8` (brief-be-letture-in-transazione-sola-lettura) non ancora nel branch: si rigenera dopo il merge, non prima |
| ⚠️ **Il frontend non deve mandare campi in più** (D-P3) | ✅ Verificato: `GenericConfigDrawer` costruisce il payload solo dalle colonne del metadata, che esclude `id`, audit, generate e identity `ALWAYS` come il verbo. 🟡 **Aperto**: in modifica il drawer manda solo il delta, quindi «Salva» senza modifiche manda `{}` → `E_PANNELLO_DATI_VUOTI` (prima era «Record non trovato»). Il drawer deve non chiamare, o spegnere «Salva», quando il delta è vuoto |
| Le quattro tabelle con RLS **escono dal pannello** (D-P2) | ✅ `pagamenti.enti_incasso` tolta dal registro del frontend (le altre tre non c'erano); l'elenco del backend legge `pannello` |
| **Il registro del frontend si ritira** (D-P5) | ⏸️ **Sospeso fino alla D-P6**: oggi `GET /core/config/tables/` elenca le 83 righe `pannello = true`, comprese le 19 che non devono esserci, e il registro è l'unico filtro a video. ⛔ Il filtro è solo a video: le scritture su quelle 19 dall'API passano finché il CSV non è corretto |
| 🔴 **Richiesta al team DB (revisione del 2026-09-25): le colonne scrivibili in una sede** | Le colonne che il pannello non scrive stanno in **due** posti: la costante `c_escluse` (più generate e identity `ALWAYS`) dentro `config.fn_pannello_scrivi`, e `_EXCLUDED_COLUMNS` più lo stesso filtro in `config_metadata_repository`. Se divergono, il form offre un campo che il salvataggio respinge. Proposta: una funzione, per esempio `config.fn_pannello_colonne_scrivibili(p_tabella) → text[]`, che il verbo usa al passo 2 e il metadata legge; il backend ritira la sua costante nello stesso giro. Fino ad allora la doppia sede è dichiarata nel codice |
| 🔴 **Richiesta al team DB (revisione del 2026-09-25): `pannello` implica `lookup`** | Il pannello elenca le righe col lookup generico, quindi una riga con `pannello = true` e `lookup = false` sarebbe un pannello che risponde 400. Oggi è vero solo per come è scritto il CSV: nessun `CHECK` lo impone. Proposta: `CHECK (NOT pannello OR lookup)` su `config.tabelle_gestibili` |

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
