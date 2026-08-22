# Brief BE/FE — posting contabile e abbinamento alla rata

> **Cos'è.** Il **piano di sviluppo backend e frontend** del cantiere
> «contabili di pagamento». Il terzo documento di una famiglia di tre, e i tre
> non si sovrappongono:
>
> | Documento | Che cosa contiene | Chi lo aggiorna |
> | --- | --- | --- |
> | [brief-incassi-riconciliazione-rate-promemoria.md](brief-incassi-riconciliazione-rate-promemoria.md) | le **decisioni di dominio** (D1…D15) col loro perché | chi decide (Tid) |
> | [brief-db-posting-e-abbinamento-rata.md](brief-db-posting-e-abbinamento-rata.md) | le **misure del terreno DB** e i passi, lotto per lotto | il team DB |
> | **questo** | che cosa si costruisce **sopra**: endpoint, service, repository, schermate | BE/FE |
>
> ⚠️ **Divisione del lavoro, per non far divergere tre sedi.** Una decisione di
> dominio si aggiorna **solo** nel brief madre; una misura del DB o un passo di
> migrazione **solo** nel piano DB; un contratto API o una schermata **solo
> qui**. Se una decisione cambia, si cambia là e qui si riporta il passo che ne
> discende — mai il contrario. Il cantiere fondi ha già pagato questa lezione
> (registro, notte 11): *due sedi sullo stesso argomento divergono al primo
> aggiornamento*.
>
> **Scritto il 2026-08-22**, rimisurando il terreno **BE e FE** contro il codice
> vivo (non contro i due brief, che sul lato applicativo dicono solo «è uno
> stub»).
>
> ⛔ **Niente è stato scritto.** Nessun endpoint, nessun componente, nessuna
> riga di Python o di Vue. Questo documento è un piano.
>
> 🔴 **E non è ancora eseguibile per intero**: il DB è al **lotto 3 di 7**
> (stato al 2026-08-22, comunicato da Tid). Tre slice su sette **si possono
> cominciare oggi**; le altre aspettano un lotto preciso, e §3 dice quale.
>
> ⭐ **Le domande aperte sono in §7**: nove, tutte con una mia proposta e col
> motivo per cui non decido io. Sono la prima cosa da chiudere.

---

## 0. In una pagina

| | Cosa | Dove |
| --- | --- | --- |
| ✅ **Già pronto, verificato** | `apps.pagamenti` è in `INSTALLED_APPS` · area funzionale `pagamenti` a catalogo (id 7) · dominio `pagamenti` già in `DOMAINS` del FE · i **21 codici errore** dei lotti 1-2 sono **già** in `error_policies_generated.py` (**BE-1 chiusa**) · i **quattro cataloghi** di `pagamenti` sono già nella whitelist della lookup generica · `fn_get_lookup_codici` **filtra già** `obsoleto_dal` (quindi `STORNATA` non compare in nessun menu a tendina) | §1.1 |
| 🔴 **Da zero** | `apps/pagamenti/api/urls.py` è `urlpatterns = []`, `views.py` è **una riga di commento**, non esiste `urls_v1.py` e **non è montato** in `zeroerp_backend/urls.py`. `frontend/src/pagamenti/` sono **due `.gitkeep`**, e `DOMAIN_MENUS['pagamenti']` è **`[]`**: il dominio esiste nella sidebar e non porta da nessuna parte | §1.2 |
| 🔴 **Il vincolo che governa tutto** | Il BE è **sottile per obbligo**, non per stile: il posting è **una sola `SELECT fn_posta_contabile(...)`**. Niente `transaction.atomic()` attorno a più scritture, niente orchestrazione Python (BE-2). E il FE **traduce l'esito in una frase** — il DB dice il fatto, chi parla con la persona decide come raccontarlo (Q-7) | §2 |
| 📋 **Il piano** | **Sette slice** BE/FE, agganciate ai lotti DB. **S0, S1, S2 partono oggi**; S3 aspetta il lotto 4, S4 il 5, S5 il 6, S6 il 7 | §3 |
| 🔌 **Il contratto** | 18 endpoint proposti, grammatica URL di `api.md` rispettata: nessun verbo dove basta il metodo, verbo solo per le azioni di dominio | §4 |
| 🎨 **Il frontend** | 5 schermate, 2 drawer, 1 pannello. **17 building block riusati**, **4 da estrarre** — e tre di questi quattro **non sono di `pagamenti`**: servono a `vendite` prima che a noi | §5 |
| 📮 **Al team DB** | **9 prerequisiti** che il piano DB non contiene, perché nascono dall'interfaccia e non dal modello: tre viste di lista, i seed `ui.lista_*`, una funzione di spezzatura riga, un lookup rate | §6 |
| ❓ **Domande aperte** | **Nove.** Le due che bloccano davvero sono **Q-1** (come viaggia sul filo HTTP un rifiuto *confermabile*) e **Q-2** (spezzare una riga è un verbo o due gesti) | §7 |

---

## 1. Il terreno, misurato il 2026-08-22

Misurato **sul codice**, non sui brief: i due documenti esistenti liquidano il
lato applicativo con «è uno stub», ed è vero, ma «stub» non dice **quanto** già
c'è intorno — e ce n'è più di quanto sembri.

### 1.1 ✅ Ciò che esiste già, e non va costruito

| Cosa | Dove, verificato | Perché conta |
| --- | --- | --- |
| App Django registrata | `zeroerp_backend/settings.py:123` — `'apps.pagamenti'` in `INSTALLED_APPS` | non serve creare l'app: serve **riempirla** |
| Area funzionale | `config/aree_funzionali.csv` riga 8 — id **7**, codice `pagamenti`, schema `pagamenti`, ordine 70 | `DomainAPIView.area_funzionale = "pagamenti"` funziona **da subito**: la catena permessi risolve |
| Azione di processo | `config/azioni_processo.csv` riga 6 — id **5**, `approva_rimessa`, area 7 | ⚠️ ma **D14-d l'ha lasciata orfana**: la forzatura non è più gated. Vedi **Q-5** |
| I 21 codici errore dei lotti 1-2 | tutti presenti in `apps/core/services/error_policies_generated.py` — verificati **uno per uno**, zero mancanti | ⭐ **BE-1 è chiusa.** Il piano DB la elenca ancora come richiesta aperta in due punti (§6.7 e §6.9): non lo è più |
| Whitelist della lookup generica | `apps/core/db/dbops_repository.py:104-108` — `pagamenti.centri_riscossione`, `enti_incasso`, `vendite_contabili_stati`, `vendite_contabili_righe_stati` | ⭐ i quattro menu a tendina di `pagamenti` **non richiedono nessun endpoint nuovo**: `GET /core/lookup/codici/?rel=pagamenti.…` risponde già. È la memoria `feedback_lookup_whitelist_first` applicata **prima** di sbagliare |
| Il filtro degli stati ritirati | `dbops.fn_get_lookup_codici`, riga 299 della doc auto-gen: `(t.obsoleto_dal IS NULL OR t.obsoleto_dal > CURRENT_DATE)` | ⭐ **`STORNATA` non comparirà in nessun menu**, e non perché qualcuno se lo ricorda: perché la lookup generica sa già leggere la colonna che il lotto 2 ha aggiunto. **Verificato, non dedotto** |
| Il dominio nella sidebar | `frontend/src/core/navigation.js:107` — `{ key: 'pagamenti', icon: NAV_ICONS.PAGAMENTI, to: '/pagamenti', schemaDb: 'pagamenti' }` | l'icona, la rotta radice e il legame con lo schema DB (per `useReadonlyMode`) ci sono già |
| La chiave i18n del dominio | `frontend/src/locales/it.json:213` — `"pagamenti": "Pagamenti"` | la voce di menu ha già il suo nome |

> ⭐ **Il conto di ciò che si risparmia è alto**: quattro lookup, ventuno codici
> errore con la loro classe, l'area a catalogo, l'icona e la rotta. La ragione
> per cui è così è che i cantieri DB hanno seminato **pensando all'interfaccia**
> — e il caso di `obsoleto_dal` letto dalla lookup generica è la prova che
> conviene misurare prima di stimare.

### 1.2 🔴 Ciò che è vuoto per davvero

| Cosa | Stato misurato |
| --- | --- |
| `backend/apps/pagamenti/api/urls.py` | `urlpatterns = []` — **due righe in tutto** |
| `backend/apps/pagamenti/api/views.py` | `# Create your views here.` — **una riga di commento** |
| `backend/apps/pagamenti/api/urls_v1.py` | **non esiste** |
| Montaggio in `zeroerp_backend/urls.py` | **assente**: nessun `path("api/v1/pagamenti/", …)`. Oggi `/api/v1/pagamenti/…` è un 404 secco |
| `backend/apps/pagamenti/{services,db}/` | esistono le cartelle con `__init__.py` e un `README.md`. **Zero moduli** |
| `backend/apps/pagamenti/models.py` | il commento di scaffolding di Django |
| `frontend/src/pagamenti/` | `components/.gitkeep` e `views/.gitkeep`. **Non esistono** `views/*.vue`, `stores/`, `api/` |
| `DOMAIN_MENUS['pagamenti']` | `frontend/src/core/navigation.js:190` — **`[]`**. Il dominio si apre e la sidebar è vuota |
| Rotte Vue del dominio | nessuna |
| `ui.lista_definizione` per `pagamenti` | **nessuna riga**: le 44 definizioni a catalogo sono di `anagrafiche`, `vendite`, `catalogo`, `config`, `documenti`, `pratiche`, `storico`, `dbops`. 🔴 Ogni lista nuova ha quindi un **prerequisito DB**, non solo FE |

### 1.3 ⚠️ Lo stato del DB al 2026-08-22, e che cosa ne discende per noi

| Lotto DB | Contenuto | Stato | Che cosa sblocca **qui** |
| --- | --- | --- | --- |
| **1** | il terreno (centri, `stato_id` NOT NULL, codici errore) | ✅ applicato 21/08 | la lookup dei centri, i messaggi parlanti |
| **2** | vocabolario, transizioni, sei guard, `origine`, `importo_dichiarato` | ✅ applicato 21/08 | ⭐ **tutta la gestione della distinta**: creare, compilare, validare, annullare |
| **3** | «il fondo si difende» (`ESEGUITO`, `fondo_source_id`, reset che cancella) | ✅ **chiuso** (Tid, 22/08) | niente di diretto: è la **difesa** che deve precedere il posting |
| **4** | ⭐ **la madre** `fn_posta_contabile` | 🔴 **da fare** | **la registrazione**. Senza, la slice 3 non esiste |
| **5** | la rata (`scadenza_id`, quadratura, forzatura, `fn_get_saldo_rata`) | 🔴 da fare | l'abbinamento **alla rata** e la forzatura del sovra-incasso |
| **6** | il perimetro (conto sull'ente, unicità, RLS in lettura) | 🔴 da fare | la coda «da abbinare» visibile **a chi deve** |
| **7** | le sistemazioni (vista eccedenze + registro + tre verbi) | 🔴 da fare | il giro rimborsi/riporti/compensazioni |

> 🔴 **La conseguenza operativa, e va detta in testa.** Il gesto che dà senso a
> tutto — «registra» — è nel lotto **4**, che non c'è. Quindi le prime tre slice
> BE/FE costruiscono un'interfaccia che sa **preparare** il lavoro e non sa
> ancora **chiuderlo**. ⚠️ **Non è tempo perso e non è un mezzo prodotto**: la
> distinta con le sue righe è già oggi l'unico modo di *vedere* ciò che il giro
> dei fondi fattura scrive da mesi senza che nessuno lo guardi. Ma va saputo
> prima di cominciare, perché cambia che cosa si può collaudare con Tid a
> fine slice.

---

## 2. I cinque vincoli che governano questo cantiere

Non sono buone pratiche generiche: sono **cinque decisioni già prese** che, se
si dimenticano, si pagano con del codice da buttare.

### 2.1 🔴 Il backend è sottile **per obbligo**

**BE-2 del piano DB**: il posting è **una sola `SELECT pagamenti.fn_posta_contabile(...)`**.

⛔ **Nessun `transaction.atomic()` attorno a più statement**, nessuna
orchestrazione Python, nessun ciclo che posta le righe una a una. L'atomicità è
**dentro la funzione** — e `api.md` §Atomicità dice esattamente questo per il
caso «l'operazione compone **solo** scritture DB»: *una sola `SELECT fn_madre(...)`
nel repository, atomica per costruzione*.

⚠️ Il guardrail AST `apps/core/tests/test_transaction_atomicity_guardrail.py`
gira in CI e vede il livello repository: un service che componesse due
`cursor.execute` di scrittura fallirebbe la build. **È una rete, non la
regola**: la regola è che quelle due scritture non devono esistere.

### 2.2 ⭐ Il database dice il **fatto**, il frontend racconta

**Q-7, chiusa da Tid il 21/08 (opzione B)**: `fn_posta_contabile` **non solleva**
quando non c'è niente da registrare. Risponde normalmente e dichiara l'esito
(`POSTATA` / `NULLA_DA_POSTARE`) dentro la ricevuta.

Ne discende una divisione di lavoro precisa, e vale **oltre il posting**:

| Livello | Che cosa fa |
| --- | --- |
| **DB** | dice che cosa è successo, con un vocabolario chiuso |
| **BE** | passa l'esito **senza interpretarlo**: non trasforma `NULLA_DA_POSTARE` in un 409, non lo inghiotte |
| **FE** | decide **la frase**: replay tecnico → silenzio; seconda pressione voluta → *«questa distinta è già registrata»* (**D3-c**) |

⛔ E il BE **non** deve «migliorare» l'esito: se lo trasformasse in un errore,
il database scriverebbe nel registro degli errori un errore che non è un errore
— che è la ragione esatta per cui Tid ha scelto l'opzione B.

### 2.3 🔴 La **coerenza** si rifiuta, la **capienza** si segnala

**D14-b**. E la seconda metà è quella che cambia l'interfaccia:

```text
«questa rata è di questa fattura?»      → 🔒 il DB RIFIUTA. Punto.
«c'è ancora spazio su questo documento?» → ⚠️ si SEGNALA, e l'operatore decide
```

La forma della segnalazione è **a due tempi** (D14-d):

```text
1° tentativo, senza dichiarazione
   → RIFIUTATO: «la fattura 2026/118 risulta già saldata. Confermi?»
2° tentativo, con la conferma
   → ACCETTATO, e sulla riga resta scritto che è stata forzata
```

⛔ **Nessun permesso, nessun pattern proponi/approva, un tempo solo.** Restano
il **flag** sulla riga e un **motivo facoltativo**.

🔴 **E qui c'è il primo problema vero di questo brief**: un rifiuto *confermabile*
esce dal DB come un errore qualunque, e il FE deve saperlo distinguere da un
errore vero. Come, è **Q-1**.

### 2.4 ⚠️ «Incassato» non è «postato», e la distinzione va nella **prima** misura

Limite di dominio del brief madre §4:

| Domanda | Che cosa si somma |
| --- | --- |
| «questa fattura è ancora da pagare?» | **tutti** i movimenti — il trasferimento la salda davvero |
| «quanto è **entrato in banca**?» | solo i centri di cassa: `is_fondo_fattura` e `is_compensazione` **esclusi** |

🔴 *«La distinzione va messa nella prima misura che si scrive, non aggiunta
dopo. Un cruscotto di incassato che somma tutto conta come denaro arrivato
qualcosa che è stato solo spostato, e l'errore non si vede: il numero è
plausibile e cresce nel verso giusto.»*

⇒ **Regola per questo cantiere**: qualunque colonna, badge o totale che dica
«incassato» **dichiara quale dei due è**, fin dalla prima riga di codice. Vedi
**Q-6**.

### 2.5 ⭐ La distinta manuale è **proprietà**, non risorsa contesa

**D12-a**: il raggruppamento della distinta manuale comprende **chi sta
lavorando**. Da cui:

- ⛔ **niente lock**, niente colonne di blocco, niente sblocco d'emergenza,
  niente polling di «chi tiene la chiave». Tid l'aveva chiesto; il modello lo ha
  reso inutile;
- ⛔ **niente permesso «si confermano solo le righe proprie»** — rientrerebbe
  dalla finestra la registrazione parziale che D3-a esclude dalla porta;
- ✅ resta la **dichiarazione** di D13 (`righe_attese` + `totale_atteso`) come
  **rete**, non come presidio principale: copre la stessa persona con due schede
  aperte e un frontend che lavora su dati vecchi.

---

## 3. Il piano — sette slice

Ogni slice è **collaudabile da sola** e dichiara **da quale lotto DB dipende**.
Le prime tre non aspettano niente.

```text
  DB lotto 2 ✅ ──▶ S0 telaio ──▶ S1 la distinta ──▶ S2 la riga e l'abbinamento
  DB lotto 4 🔴 ─────────────────────────────────▶ S3 la registrazione
  DB lotto 5 🔴 ─────────────────────────────────▶ S4 la rata e la capienza
  DB lotto 6 🔴 ─────────────────────────────────▶ S5 il perimetro e la coda
  DB lotto 7 🔴 ─────────────────────────────────▶ S6 le sistemazioni
```

### 3.0 S0 — Il telaio *(nessuna dipendenza: si parte oggi)*

Nessun valore di dominio. È ciò senza cui la slice 1 non si scrive.

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| **T-1** | `apps/pagamenti/api/urls_v1.py` + montaggio in `zeroerp_backend/urls.py` | BE | `path("api/v1/pagamenti/", include("apps.pagamenti.api.urls_v1"))`, subito **dopo** `pratiche` per stare nell'ordine dei domini |
| **T-2** | `apps/pagamenti/db/pagamenti_repository.py` | BE | Il repository **generico dello schema**, come prescrive la convenzione di naming di `AGENTS.md`: liste, letture, chiamate a `fn_*`. ⛔ **Non** un file per entità: distinte e righe stanno insieme finché non nasce un sottodominio con orchestrazione propria |
| **T-3** | `apps/pagamenti/services/pagamenti_service.py` | BE | La facciata. ⚠️ Il traduttore degli errori DB si prende da `make_db_errors_translator` (`payload_helpers`), **non** si riscrive |
| **T-4** | `apps/pagamenti/types.py` | BE | `TypedDict` delle righe DB (`DistintaRow`, `RigaContabileRow`, `RicevutaPosting`) |
| **T-5** | `frontend/src/pagamenti/{views,components,stores,api}/` | FE | Le quattro cartelle, allineate ai domini esistenti |
| **T-6** | `DOMAIN_MENUS['pagamenti']` + rotte | FE | Da `[]` alle voci della slice 1. ⚠️ Le rotte vanno con `meta` per `resolveTabLabel`/`resolveTabIcon` |
| **T-7** | Namespace i18n `pagamenti.*` in `it.json` e `en.json` | FE | ⚠️ **`check_i18n_keys.py` è un cancello CI**: una `label_key` seminata a DB senza la sua chiave nei locales **fa fallire la build**. È già successo al lotto 2, che per questo ha seminato le matrici con `{"manuale": false}` |
| **T-8** | `useReadonlyMode('pagamenti')` sulle viste | FE | Piramide permessi standard. Lo `schemaDb` è già in `DOMAINS` |

⭐ **Nessun endpoint di lookup da scrivere**: i quattro cataloghi sono già nella
whitelist (§1.1). Il FE usa `LookupSelect` con `rel="pagamenti.centri_riscossione"`.

### 3.1 S1 — La distinta *(dipende dal lotto DB 2: ✅ applicato)*

Il documento che raccoglie N importi arrivati insieme. Realizza **D12**, **D14-a-bis**
e mette in mano a una persona ciò che il giro dei fondi scrive da mesi al buio.

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| **D-1** | `GET /pagamenti/distinte/` — lista paginata | BE | 📮 **Prerequisito DB**: vista `pagamenti.vw_vendite_contabili_lista` + seed `ui.lista_definizione` e `lista_colonna` (§6). Filtri: stato, origine, centro, **data** (`data_contabile`, col floor standard di `defaultFiltroDataDa`) |
| **D-2** | `POST /pagamenti/distinte/` — apre una distinta manuale | BE | Una `SELECT fn_get_or_create_vendite_contabile(...)`, con `p_origine := 'MANUALE'` e `p_codice_stato_interno := 'BOZZA'`. ⭐ Il BE **non passa** l'operatore: lo mette la funzione (D12-a). ⚠️ `Idempotency-Key` obbligatoria |
| **D-3** | `GET /pagamenti/distinte/{id}/` — dettaglio | BE | Testata + totali derivati (somma righe, righe registrabili, scarto dal dichiarato) |
| **D-4** | `PATCH /pagamenti/distinte/{id}/` | BE | Solo i campi che una persona compila: `data_contabile`, `ente_incasso_id`, `importo_dichiarato`, `meta`. ⛔ **Non** lo stato: quello è un'azione |
| **D-5** | `POST /pagamenti/distinte/{id}/stato/` | BE | `{nuovo_stato: 'VALIDATA'\|'BOZZA'\|'ANNULLATA'}`. Un `UPDATE stato_id`, e i **quattro guard del lotto 2** fanno il resto — transizione ammessa, quadratura col dichiarato, riapertura solo se `MANUALE`, chiusura senza righe pronte |
| **D-6** | `DistinteListView.vue` | FE | `<ListaConfigurabile>` + `useListaConfigurabilePage` + `PageActionsBar`. Modello da copiare: `ApprovazioniPrezzoListView.vue` |
| **D-7** | `DistintaDrawer.vue` | FE | Testata + **master-detail inline** delle righe (`RigheMasterDetailTable`). ⚠️ `readonly` + `useInjectReadonly` **obbligatori** |
| **D-8** | Pannello «validazione» nel drawer | FE | Mostra dichiarato vs digitato e il **delta**, così l'errore si vede **prima** di premere. ⚠️ È un pannello-azione dentro un drawer che post-BOZZA è `.app-readonly` ⇒ **wrapper `app-escape` obbligatorio**: due bug bloccanti sono già stati trovati così |

⚠️ **Un'avvertenza sul contenuto di questa lista, oggi.** Le uniche distinte
esistenti sono **`GENERATA`** — le crea il sync dei fondi fattura, e nascono già
in `VALIDATA`. Quindi la prima cosa che la lista mostrerà a Tid **non è il
lavoro di nessuno**: è la contabilità interna dei fondi. È giusto che si veda
(§1.3), ma la schermata deve **dirlo** — la colonna `origine` non è un dettaglio
tecnico da nascondere, è *«l'informazione che serve a chi la guarda»* (D12-b-bis).

### 3.2 S2 — La riga e l'abbinamento *(dipende dal lotto DB 2: ✅ applicato)*

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| **R-1** | `GET/POST /pagamenti/distinte/{id}/righe/` | BE | Lista e creazione righe della distinta |
| **R-2** | `PATCH /pagamenti/righe/{id}/` | BE | I **fatti** (`importo`, le tre date, `riferimento_ente`) e le **decisioni** (`fattura_id`, `billing_account_id`, `motivo_sospeso`). ⚠️ D12-d: sull'`AUTOMATICA` i fatti saranno immutabili — il guard però arriva **con D6**, quindi oggi il BE non deve inventarselo |
| **R-3** | `POST /pagamenti/righe/{id}/stato/` | BE | Il percorso di D14-a. I guard del lotto 2 rifiutano ciò che non è ammesso, **compreso** `ABBINATA` senza fattura |
| **R-4** | 🔴 `POST /pagamenti/righe/{id}/spezza/` | BE | **Il gesto centrale di D1-bis** — 1.200 su una rata da 1.000 si risolve *spezzando*, non forzando. 📮 Richiede una **funzione DB che nessun lotto contiene**. Vedi **Q-2** |
| **R-5** | `FatturaLookup.vue` | FE | 🆕 Building block: autocomplete fattura cross-dominio. ⚠️ Vive in `vendite` ⇒ `skip_area_check = True` + scope nel repository (memoria `feedback_lookup_skip_area_check`): **mai** dare LETTURA su `vendite` a chi lavora gli incassi |
| **R-6** | Form riga dentro il drawer distinta | FE | `BillingAccountLookup` (esiste) + `FatturaLookup` (nuovo). ⚠️ Salvare l'`_obj` nel form per il restore dell'AutoComplete server-side |
| **R-7** | Azioni di riga | FE | `RowActionsMenu` + `MANAGE_ICONS.KEBAB`. ⛔ **Mai la matita**: la modifica è il click sulla riga |

### 3.3 S3 — La registrazione 🔴 *(aspetta il lotto DB 4)*

Il cuore. Fa esistere il primo `vendite_movimenti` del progetto, e da lì
`fn_get_saldo_fattura` **smette di mentire**.

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| **P-1** | `GET /pagamenti/distinte/{id}/anteprima-registrazione/` | BE | La **fotografia**: quante righe sono registrabili adesso, per che totale, quante restano indietro e perché. È ciò che l'operatore vede **prima** di premere, ed è ciò che poi **dichiara** |
| **P-2** | `POST /pagamenti/distinte/{id}/registra/` | BE | **Una sola** `SELECT fn_posta_contabile(id, righe_attese, totale_atteso)`. `Idempotency-Key` obbligatoria. ⛔ Nessun `atomic()`, nessun ciclo, nessuna lettura-poi-scrittura |
| **P-3** | La ricevuta risale intatta | BE | `{movimenti_creati, righe_postate, righe_saltate, totale_postato, esito}` dentro `success_response`. ⛔ Il BE **non** trasforma `NULLA_DA_POSTARE` in un errore (§2.2) |
| **P-4** | Pannello «Registra» nel drawer | FE | Mostra l'anteprima, chiede conferma, invia la dichiarazione. ⚠️ `app-escape` (il drawer post-BOZZA è readonly) |
| **P-5** | La frase sull'esito | FE | `POSTATA` → toast di successo coi numeri della ricevuta; `NULLA_DA_POSTARE` → **avviso**, non errore: *«questa distinta era già registrata»*. È D3-c, e la fa il FE |
| **P-6** | Il rifiuto della dichiarazione | FE | Se il DB risponde «ciò che vedi non è ciò che c'è», **non si riprova in automatico**: si ricarica l'anteprima e si mostra la differenza. Un retry cieco su un gesto irreversibile è la cosa peggiore che si possa costruire |

### 3.4 S4 — La rata e la capienza 🔴 *(aspetta il lotto DB 5)*

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| **A-1** | `scadenza_id` nel payload della riga | BE | Aggiunta al PATCH di R-2 |
| **A-2** | Lookup delle rate di una fattura | BE | 📮 Prerequisito: **non esiste una rotta scadenze**. Vedi **Q-8** |
| **A-3** | `GET /pagamenti/rate/{id}/saldo/` | BE | Sopra `fn_get_saldo_rata`. ⚠️ Deve **già** distinguere incassato da postato (§2.4) |
| **A-4** | `GET /pagamenti/rate/sovra-incassate/` | BE | **BE-5**. 📮 Prerequisito DB: la vista di S2-7. ⚠️ *«senza, la forzatura è un modo di nascondere denaro, non di registrarlo»* |
| **A-5** | La forzatura a due tempi | BE+FE | Il payload porta `forzatura_confermata` + `motivo` (facoltativo). Il primo tentativo **non** lo porta. Vedi **Q-1** per come il FE riconosce il rifiuto confermabile |
| **A-6** | `RateSovraIncassateListView.vue` | FE | Lista. 📮 Prerequisito: seed `ui.lista_*` |
| **A-7** | Selettore rata nel form riga | FE | Alimentato dalla fattura scelta; si azzera quando la fattura cambia. ⚠️ La rata resta **facoltativa** anche su `ABBINATA` — la riga del fondo fattura ha fattura sì e rata no |

### 3.5 S5 — Il perimetro e la coda 🔴 *(aspetta il lotto DB 6)*

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| **E-1** | Gestione `enti_incasso` | BE+FE | Drawer dedicato: ha JOIN (soggetto_ruolo, filiale, conto) quindi **non** è un pannello config generico. Il conto diventa obbligatorio per `tipo = BANCA` |
| **E-2** | Coda «da abbinare» | BE+FE | Lista cross-distinta delle righe `DA_ABBINARE` e `SOSPESA`. ⭐ Sono **due code per due persone diverse**: `DA_ABBINARE` = lavoro non ancora fatto, `SOSPESA` = lavoro fatto che ha trovato un ostacolo. Vedi **Q-4** |
| **E-3** | Riverifica di **tutte** le liste sotto RLS | BE | ⚠️ Memoria `feedback_rls_query_contesto_sistema`: **un conteggio fail-closed somiglia a un dato**. Una lista che si svuota dopo il lotto 6 non è «nessun risultato», è un perimetro che ha morso |

### 3.6 S6 — Le sistemazioni 🔴 *(aspetta il lotto DB 7)*

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| **S-1** | `GET /pagamenti/eccedenze/` | BE | Sopra `vw_eccedenze_da_sistemare`. ⭐ **Raggruppata per cliente**, non per documento: la compensazione ha senso solo a livello cliente |
| **S-2** | `POST /pagamenti/sistemazioni/` | BE | Registra la decisione: `RIPORTO` / `RIMBORSO` / `COMPENSAZIONE` |
| **S-3** | I tre verbi | BE | Riusano meccanismi esistenti — fondo `origine = MANUALE`, contabile a importi negativi, contabile di compensazione. ⭐ **Nessuna macchina nuova** |
| **S-4** | `EccedenzeView.vue` + drawer decisione | FE | La vista presenta, la persona decide, l'atto diventa un fatto |

📮 Con S-3 si chiude **BE-4** e si sblocca la **Fase D del cantiere fondi**,
ferma per scelta da agosto.

### 3.7 Cosa il cantiere BE/FE **non** fa, e perché

| Non fa | Perché |
| --- | --- |
| **Import del flusso bancario** (D6) | `enti_incasso` è a 0 righe: non esiste un canale da cui un file possa arrivare. E i due guard di immutabilità vanno **con** l'import: prima non hanno righe su cui agire |
| **Abbinamento automatico** (D4) | Una regola di match si tara sui casi veri. Con zero incassi si scriverebbe immaginandoli |
| **Portale clienti `GET /portale/scadenze/`** (§3.3) | Senza la slice 4 mostrerebbe il piano rate e basta, senza poter dire quali rate siano pagate — cioè l'unica domanda che il cliente si fa |
| **Scadenzario** (§3.4) | ⛔ Limite di dominio: *«non esiste uno stato di pagamento della rata; nessuna colonna scaduta/insoluta, nessuna colorazione di sollecito»*. Ogni sua colonna sarebbe falsa su una fattura già incassata |
| **Blocco `2.4 DatiPagamento`** (§3.2) | È il passo **2** dell'ordine di Tid, e appartiene al cantiere SDI |
| **Il riferimento `RF` ISO 11649** (§3.6) | È una **proposta**, non una decisione |

---

## 4. Il contratto API proposto

Grammatica di `api.md`: il metodo dice l'operazione, il path la risorsa, il
verbo compare **solo** per le azioni di dominio e come **ultimo** segmento.

| Slice | Metodo e path | Che cos'è | Idem-Key |
| --- | --- | --- | :---: |
| S1 | `GET /api/v1/pagamenti/distinte/` | lista paginata | — |
| S1 | `POST /api/v1/pagamenti/distinte/` | apre una distinta manuale | ✅ |
| S1 | `GET /api/v1/pagamenti/distinte/{id}/` | dettaglio + totali derivati | — |
| S1 | `PATCH /api/v1/pagamenti/distinte/{id}/` | campi compilabili | — |
| S1 | `POST /api/v1/pagamenti/distinte/{id}/stato/` | VALIDATA · BOZZA · ANNULLATA | ✅ |
| S2 | `GET /api/v1/pagamenti/distinte/{id}/righe/` | righe della distinta | — |
| S2 | `POST /api/v1/pagamenti/distinte/{id}/righe/` | nuova riga | ✅ |
| S2 | `PATCH /api/v1/pagamenti/righe/{id}/` | fatti + decisioni | — |
| S2 | `POST /api/v1/pagamenti/righe/{id}/stato/` | il percorso di D14-a | ✅ |
| S2 | `POST /api/v1/pagamenti/righe/{id}/spezza/` | 🔵 **Q-2** | ✅ |
| S3 | `GET /api/v1/pagamenti/distinte/{id}/anteprima-registrazione/` | la fotografia | — |
| S3 | `POST /api/v1/pagamenti/distinte/{id}/registra/` | ⭐ la madre | ✅ |
| S4 | `GET /api/v1/pagamenti/rate/{id}/saldo/` | saldo per rata | — |
| S4 | `GET /api/v1/pagamenti/rate/sovra-incassate/` | BE-5 | — |
| S4 | `GET /api/v1/vendite/fatture/{id}/scadenze/lookup/` | 🔵 **Q-8** — vive in `vendite` | — |
| S5 | `GET/POST/PATCH /api/v1/pagamenti/enti-incasso/…` | configurazione canali | ✅ su write |
| S5 | `GET /api/v1/pagamenti/righe/da-abbinare/` | la coda | — |
| S6 | `GET /api/v1/pagamenti/eccedenze/` · `POST /api/v1/pagamenti/sistemazioni/` | presenta · decide | ✅ su write |

**Note vincolanti:**

- ⛔ **niente `POST /distinte/crea/`, niente `PATCH /distinte/5/aggiorna/`**: il
  verbo è nel metodo HTTP;
- ✅ `registra`, `spezza`, `stato` sono **azioni di dominio**, e stanno come
  ultimo segmento — la stessa forma di `POST /pratiche/3/sospendi/`;
- ⚠️ **niente `?format=`** nei query param: collide con DRF e produce un 404
  silenzioso. Se servirà un export, il parametro si chiama `formato`;
- tutte le view estendono `DomainAPIView` con `area_funzionale = "pagamenti"`.
  ⛔ **Nessuna classe V1**: il pattern dual-class è eliminato dal marzo 2026;
- ogni metodo pubblico porta `@extend_schema`, o drf-spectacular fa rumore in CI.

---

## 5. Il frontend — schermate e building block

### 5.1 Le schermate

| Schermata | Slice | Forma |
| --- | --- | --- |
| **Distinte contabili** | S1 | `<ListaConfigurabile>` — paginatore in alto, filtri stato/origine/centro/data, click riga → drawer |
| **DistintaDrawer** | S1-S3 | Testata + master-detail righe + pannello validazione + pannello registrazione |
| **Da abbinare** | S5 | Coda di righe cross-distinta, due sotto-code (**Q-4**) |
| **Rate sovra-incassate** | S4 | Lista. Senza, la forzatura nasconde invece di registrare |
| **Eccedenze da sistemare** | S6 | Lista raggruppata **per cliente** + drawer decisione |

### 5.2 ✅ I 17 building block che si riusano

`ListaConfigurabile` · `useListaConfigurabilePage` · `useListaAzioni` ·
`PageActionsBar` · `RowActionsMenu` · `AppDrawer` · `FormFooter` ·
`DrawerActionsBar` · `AppDialog` · `RigheMasterDetailTable` · `LookupSelect` ·
`BillingAccountLookup` · `useReadonlyMode` · `useConfirmAction` ·
`useDrawerContentReady` · `createCrudStore` · `defaultFiltroDataDa`.

### 5.3 🆕 I quattro da estrarre — e tre non sono nostri

| BB | Dove vive | Perché |
| --- | --- | --- |
| `FatturaLookup.vue` | `core/components/` | Autocomplete fattura cross-dominio. ⭐ **Non è di `pagamenti`**: serve a chiunque debba puntare una fattura da un altro schema, ed è la seconda occorrenza dopo i lookup BA e istanze |
| `ScadenzaSelect.vue` | `core/components/` | Rate di una fattura. Gemello del precedente un piano più giù |
| `SaldoDocumentoPanel.vue` | `core/components/` | «Incassato / Postato / Residuo» — ⭐ da progettare **con** la distinzione di §2.4 dentro, non appesa dopo. Vedi **Q-6** |
| `useForzaturaConfermata.js` | `core/composables/` | Il doppio-tempo «rifiuto parlante → conferma → ripeti». ⚠️ Nasce building block **solo se** Q-1 sceglie la strada dell'`ui_action`: altrimenti sarebbe un elenco di codici cablato in un composable, cioè il difetto travestito da astrazione |

⚠️ **Sulla regola del 2**: nessuno dei quattro si estrae *prima* di averlo visto
funzionare una volta. Li dichiaro qui perché il piano li prevede, non perché si
scrivano il primo giorno — e per `useForzaturaConfermata` la seconda occorrenza
potrebbe non arrivare mai.

### 5.4 ⚠️ Le trappole già pagate, da non ripagare

| Trappola | Regola |
| --- | --- |
| `useApiHandler.execute()` su una action di store | ⛔ Solo per response **axios**. Le action di store sono già scartate: chiamata diretta |
| `if (result)` dopo il save di un drawer | ⛔ `if (result !== null)`: uno `0` legittimo verrebbe letto come fallimento |
| Pannello-azione dentro un drawer post-BOZZA | ⛔ Il contenuto è `.app-readonly` ⇒ **sempre** wrapper `app-escape` |
| Store Pinia con dati utente | ⛔ `userScoped: true`, o al logout i dati restano |
| Deep-link e freshness | ⛔ In `onActivated` **idempotente**, mai solo in `setup`/`onMounted`: con KeepAlive il secondo ingresso non rimonta |
| `watch(..., { immediate: true })` | ⛔ Le variabili che tocca devono **precederlo**: la TDZ in `setup` è silenziosa |
| Download di un file | ⛔ `useApiHandler` rompe i blob: bypass + toast manuali |
| `@` in una stringa i18n | ⛔ Va escapato: `{'@'}` |

---

## 6. 📮 I nove prerequisiti a carico del team DB

⛔ **Non li eseguo io** (memoria `feedback_db_actions_passaggio_team`): si
scrivono in un brief e si aspetta. Li elenco qui perché **non stanno nel piano
DB** — nascono dall'interfaccia, non dal modello, e senza di essi le slice
corrispondenti non partono.

| | Prerequisito | Serve a | Slice |
| --- | --- | --- | --- |
| **DB-1** | Vista `pagamenti.vw_vendite_contabili_lista` — testata + totali derivati + display fields per JOIN (centro, ente, stato, origine) | ⚠️ Memoria `feedback_display_fields_backend`: i display si fanno in JOIN, **mai** lookup client-side | S1 |
| **DB-2** | Seed `ui.lista_definizione` + `ui.lista_colonna` per `pagamenti.distinte` | `<ListaConfigurabile>` non funziona senza | S1 |
| **DB-3** | Vista + seed lista per **le righe da abbinare** | la coda operativa | S5 |
| **DB-4** | Vista + seed lista per **le rate sovra-incassate** (S2-7) | BE-5 | S4 |
| **DB-5** | 🔵 `pagamenti.fn_spezza_riga_contabile(...)` — **non è in nessun lotto** | il caso ordinario di D1-bis. Vedi **Q-2** | S2 |
| **DB-6** | 🔵 Lookup delle rate di una fattura — `vendite.fn_list_scadenze_fattura` o equivalente | **non esiste una rotta scadenze paginata**. Vedi **Q-8** | S4 |
| **DB-7** | 🔵 Un `ui_action` per i rifiuti **confermabili**, se Q-1 sceglie quella strada | il doppio-tempo della forzatura | S4 |
| **DB-8** | Vista + seed lista per le **eccedenze da sistemare** (S4-3) | il giro rimborsi | S6 |
| **DB-9** | Conferma che le liste restino leggibili **dopo** la RLS del lotto 6 | ⚠️ uno zero fail-closed somiglia a un dato | S5 |

⭐ **DB-1…DB-4 e DB-8 sono la stessa cosa cinque volte**: ogni lista di questo
cantiere costa una vista e due seed. Conviene chiederle **insieme**, non una per
slice — cinque brief separati al team DB sono cinque round-trip.

---

## 7. ❓ Domande aperte — le nove che ti chiedo

> Ognuna porta **la mia proposta** e **il motivo per cui non decido io**. Le
> prime due bloccano del codice; le altre sette orientano.

### 🔴 Q-1 · Come viaggia sul filo HTTP un rifiuto **confermabile**?

D14-d dice che il DB rifiuta il primo tentativo con un messaggio parlante e
accetta il secondo. Ma sul filo HTTP quel rifiuto è **un errore come tutti gli
altri**: esce con la sua classe (probabilmente `CONFLITTO_STATO` → 409) e il
frontend deve capire che stavolta non deve mostrare un banner rosso, ma un
dialogo *«confermi?»*.

Il vocabolario delle `ui_action` oggi ha cinque voci — `highlight_form_fields`
(126 usi), `show_error_banner` (34), `show_toast_error` (12),
`show_retry_dialog` (2), `show_info_banner` (1) — e nessuna dice *«chiedi
conferma e ripeti con la dichiarazione»*. `show_retry_dialog` è vicina ma
significa un'altra cosa: *riprova*, non *conferma di volerlo fare davvero*.

| | Strada | Costo | Rischio |
| --- | --- | --- | --- |
| **(a)** ⭐ | Una `ui_action` nuova, `confirm_and_retry`, sui codici confermabili | un override a catalogo + un ramo nel FE | nessuno: il FE riconosce la **classe di comportamento**, non i singoli codici |
| **(b)** | Il FE tiene l'elenco dei codici confermabili | zero, oggi | 🔴 al terzo codice qualcuno se ne dimentica, e un rifiuto confermabile diventa un errore secco: l'operatore resta **bloccato** su un caso che il dominio dichiara ammesso |
| **(c)** | Un endpoint di anteprima che dice **prima** cosa succederà, e il POST porta già la conferma | un GET in più per gesto | ⚠️ due verità che possono divergere fra l'anteprima e il POST — e sul posting è esattamente ciò che D13 esiste per evitare |

**La mia proposta: (a).** Il presidio sta nel catalogo, dove sta già tutto il
resto della semantica degli errori, e il FE resta cieco ai codici — che è la
proprietà che rende (b) fragile.

**Perché non decido io**: introduce una voce nuova nel vocabolario delle
`ui_action`, che è trasversale a tutto il prodotto, e tocca il confine
DB↔BE↔FE che hai presidiato di persona due volte in agosto.

---

### 🔴 Q-2 · Spezzare una riga: un verbo, o due gesti?

È il gesto **centrale** di D1-bis: arrivano 1.200 su una rata da 1.000, e la
strada preferibile *«quando un'altra destinazione esiste»* è spezzare — non
forzare.

Ma spezzare è **due scritture**: l'importo della riga esistente cala, e nasce
una riga nuova col residuo in `DA_ABBINARE`. La regola «una azione = una unità
atomica» dice che devono stare in **una** transazione, e la forma preferita per
sole-scritture-DB è **una funzione madre**. Che però **non è in nessun lotto**
del piano DB.

| | Strada | Nota |
| --- | --- | --- |
| **(a)** ⭐ | `fn_spezza_riga_contabile(p_riga_id, p_importo_da_staccare)` — DB-5 | il piano DB acquista un passo; la slice 2 acquista il suo gesto principale |
| **(b)** | Il FE fa due chiamate | ⛔ **Vietato**: due scritture non atomiche, e il guardrail AST in CI lo vedrebbe comunque |
| **(c)** | Si rimanda: nella slice 2 si forza soltanto | ⚠️ **Ribalta la preferenza di D1-bis**: l'eccedenza sparisce dentro una rata che non la giustifica, invece di restare denaro identificato |

**La mia proposta: (a)**, e la chiedo al team DB **insieme** a DB-1…DB-4, così
non è un round-trip in più.

**Perché non decido io**: aggiunge un passo a un piano DB che hai già
approvato, e cambia il perimetro del lotto 5 (o ne apre uno 5-bis).

---

### Q-3 · La distinta manuale nasce da un gesto, o dalla prima riga?

D12-a dice che è *«il lotto di lavoro di un operatore»*. Due modi di renderlo:

- **(a)** ⭐ l'operatore preme «Nuova distinta», la vede nascere, poi la riempie;
- **(b)** la distinta nasce **da sé** alla prima riga registrata — «la mia
  distinta di oggi» — e l'operatore non la apre mai esplicitamente.

**La mia proposta: (a).** (b) è più fedele alla metafora, ma un documento che
nasce senza che nessuno l'abbia chiesto è difficile da spiegare e impossibile da
annullare senza spiegare prima che esiste.

**Perché non decido io**: è una scelta di *come si lavora*, e la sai tu.

---

### Q-4 · «Da abbinare» e «sospese»: due code o una lista con un filtro?

D12-f dice che la differenza fra `DA_ABBINARE` e `SOSPESA` è **chi ha
guardato** — lavoro non ancora fatto contro lavoro fatto che ha trovato un
ostacolo — e le chiama *«due code per due persone diverse»*.

- **(a)** ⭐ due voci di menu distinte, due liste;
- **(b)** una lista sola con un filtro di stato in toolbar.

**La mia proposta: (a)**, perché «due persone diverse» è scritto nella decisione
e un filtro non separa due mestieri: li mette nello stesso posto e chiede a
ciascuno di ricordarsi di impostarlo.

⚠️ **Con un'avvertenza sul quando**: oggi le righe `DA_ABBINARE` **non
esistono** — l'unico scrittore è il sync dei fondi, che le crea già `ABBINATE`.
Quella coda si popola solo con l'import (D6). Quindi la costruirei nella **slice
5**, non nella 2. Confermi?

---

### Q-5 · `approva_rimessa` (azione id 5): si ritira, si riusa, o resta?

D14-d ha tolto il permesso dalla forzatura, e quell'azione era il candidato
naturale. Ora è a catalogo sull'area 7 e **nessuno la usa**.

| | Strada | Nota |
| --- | --- | --- |
| **(a)** ⭐ | Si **riusa** per la **registrazione**: `registra_distinta` è irreversibile, e un gesto irreversibile merita un cancello | ma il nome direbbe un'altra cosa: si ritira `approva_rimessa` e se ne conia una nuova |
| **(b)** | Si **ritira** e basta: il livello area `TUTTO` è sufficiente | meno pezzi; ma chiunque possa leggere e scrivere `pagamenti` può creare movimenti veri |
| **(c)** | Resta lì | ⛔ *«un catalogo pieno di righe irraggiungibili insegna cose false»* — è la lezione appena pagata con `STORNATA` |

**La mia proposta: (a)** — un'azione `registra_distinta`, e `approva_rimessa`
ritirata con `obsoleto_dal`. La registrazione è l'unico gesto di questo cantiere
che non si può disfare.

---

### Q-6 · Il saldo del documento: quanti numeri mostra, e dove?

Col lotto 4 `fn_get_saldo_fattura` diventa vera. Due domande insieme:

1. **Dove** — un pannello nel **drawer fattura** (accanto a `ScadenzeSintesi`),
   o resta dentro `pagamenti`? ⭐ Io lo metterei nel drawer fattura: è lì che
   qualcuno si chiede se è stata pagata.
2. **Quanti numeri** — §2.4 dice che «incassato» e «postato» sono cose diverse.
   Un numero solo è più leggibile; due sono più veri. ⭐ Io mostrerei **residuo**
   in grande (la domanda che uno si fa) e **entrato in banca** in piccolo, con la
   differenza spiegata a tooltip quando c'è.

**Perché non decido io**: è la faccia che il cantiere mostra a chi non lavora
negli incassi, ed è la prima cosa che si vede.

---

### Q-7 · La correzione: gesto guidato o mano libera?

D3-d: la correzione **non è un documento speciale**, è una contabile con importi
di segno opposto. Ma il gesto, nell'interfaccia, non c'è.

- **(a)** ⭐ un'azione «Correggi» su una distinta registrata, che apre una
  distinta nuova con le righe **di segno opposto già precompilate**;
- **(b)** l'operatore apre una distinta nuova e digita i negativi a mano.

**La mia proposta: (a)**, con **una raccomandazione sul nome**: si chiama
**correzione**, mai «storno». `STORNATA` è stata ritirata dal catalogo il 21/08 e
rimetterne la parola nell'interfaccia riaprirebbe una porta che il lotto 2 ha
chiuso.

⚠️ **E (a) non è gratis**: precompilare significa creare N righe in un colpo,
cioè di nuovo **una funzione madre** e non un ciclo nel service.

---

### Q-8 · Il lookup delle rate: dove vive?

Serve un `GET /vendite/fatture/{id}/scadenze/lookup/`: sta in `vendite`, lo
consuma `pagamenti`. È esattamente il caso già risolto per
`catalogo.articoli.uom` (pattern «lookup cross-dominio su sub-resource» in
`api.md`): endpoint separato con `skip_area_check = True`, così chi lavora gli
incassi **non** deve avere LETTURA su `vendite`.

**La mia proposta**: quel pattern, identico. E poiché §3.4 del brief madre dice
che *«non esiste una rotta scadenze paginata»*, colgo l'occasione — ma **solo**
per il lookup, **non** per lo scadenzario, che resta fuori perimetro.

**Perché chiedo**: apre un endpoint in `vendite` dentro un cantiere di
`pagamenti`, e vale la pena che tu lo sappia prima e non dopo.

---

### Q-9 · Quante liste mettiamo a piano, e in che ordine le chiediamo al DB?

Il piano ne prevede **cinque**: distinte (S1), da abbinare (S5), rate
sovra-incassate (S4), eccedenze (S6), e potenzialmente i movimenti registrati.
Ognuna costa una vista + due seed lato DB.

**La mia proposta**: chiedere al team DB **un solo brief con le prime tre**
(distinte, rate sovra-incassate, da abbinare) e rimandare le altre. Cinque
richieste separate sono cinque round-trip, e le ultime due dipendono da lotti
che non esistono ancora.

**Perché chiedo**: è una decisione di **carico sul team DB**, non mia.

---

## 8. Che cosa faccio appena rispondi

In quest'ordine, e la prima riga di codice arriva **dopo** il brief al team DB —
non prima, perché senza DB-1/DB-2 la lista non si può nemmeno provare.

1. **Brief al team DB** con DB-1…DB-4 (+ DB-5 e DB-6 se Q-2 e Q-8 vanno come
   propongo), su `dev/db-tid`;
2. **Slice 0** — il telaio: non dipende da nessun prerequisito, e mentre il DB
   lavora il dominio smette di essere due `.gitkeep`;
3. **Slice 1** — la distinta, appena arrivano vista e seed;
4. **Slice 2** — la riga e l'abbinamento;
5. poi si aspetta il **lotto DB 4** per la registrazione.

⚠️ **E una cosa che non farò senza dirtelo**: nessuna delle quattro estrazioni
di §5.3 al primo colpo. La regola del 2 vale anche quando il piano prevede
l'astrazione — si dichiara alla seconda occorrenza, non alla prima.

---

## 9. Dove guardare

| Cosa | Dove |
| --- | --- |
| Le decisioni di dominio (D1…D15) | [brief-incassi-riconciliazione-rate-promemoria.md](brief-incassi-riconciliazione-rate-promemoria.md) §2-bis e §3-bis |
| I passi DB, lotto per lotto | [brief-db-posting-e-abbinamento-rata.md](brief-db-posting-e-abbinamento-rata.md) §6 |
| Le linee guida API | [api.md](../api.md) — grammatica URL, base view, envelope, atomicità, tassonomia errori |
| Gli standard frontend | [frontend-standards.md](../frontend/frontend-standards.md) — pattern lista, drawer, readonly, i18n |
| I building block | [catalogo BE](../backend/catalogo-building-block-backend.md) · [catalogo FE](../frontend/catalogo-building-block-frontend.md) |
| Il modello pagamenti in prosa | [gestione-dei-pagamenti.md](../../guide/gestione-dei-pagamenti.md) |
| Un modello di lista da copiare | `frontend/src/vendite/views/ApprovazioniPrezzoListView.vue` |
| Un modello di view BE da copiare | `backend/apps/vendite/api/views_fondi_fattura.py` |

---

## 10. Registro delle revisioni

| Data | Cosa |
| --- | --- |
| 2026-08-22 | Stesura. Terreno BE/FE misurato **sul codice**, non sui brief. ⭐ **Sei cose risultano già fatte** e i due brief esistenti non lo sanno: **BE-1 è chiusa** (i 21 codici errore dei lotti 1-2 sono tutti in `error_policies_generated.py`, verificati uno per uno), i **quattro cataloghi** di `pagamenti` sono già nella whitelist della lookup generica, `fn_get_lookup_codici` **filtra già** `obsoleto_dal` — quindi `STORNATA` non comparirà in nessun menu senza che nessuno debba ricordarsene —, l'area funzionale è a catalogo, il dominio è già in `DOMAINS` e la sua chiave i18n esiste. 🔴 **Vuoto per davvero**: `urls_v1.py` non esiste e `/api/v1/pagamenti/` è un 404 secco, `views.py` è una riga di commento, `DOMAIN_MENUS['pagamenti']` è `[]`, e **nessuna** `ui.lista_definizione` è di `pagamenti` — da cui il fatto che pesa di più sul piano: **ogni lista di questo cantiere ha un prerequisito DB**, non solo FE. Piano in **sette slice** agganciate ai lotti DB: **S0-S2 partono oggi** (il lotto 2 basta), S3 aspetta il lotto 4 (la madre), S4 il 5, S5 il 6, S6 il 7. 🔴 **Due prerequisiti che il piano DB non contiene** perché nascono dall'interfaccia: la **spezzatura di una riga** (il gesto centrale di D1-bis, che è due scritture e quindi vuole una funzione madre) e il **lookup delle rate** (§3.4 del brief madre: non esiste una rotta scadenze). ⚠️ **E un problema di confine che non avevo previsto**: un rifiuto *confermabile* (la forzatura del sovra-incasso) esce sul filo HTTP come un errore qualunque, e il vocabolario delle `ui_action` — cinque voci — non ha una parola per «chiedi conferma e ripeti». Nove domande aperte in §7 |
