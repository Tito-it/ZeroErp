# Brief DB — L'area funzionale dell'assistente AI

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-11 → **riletto e corretto
> dal team DB il 2026-09-24** (registro in fondo). **A chi:** team DB (§4) e
> team backend (§5).
> **Origine:** `migliorie-generali-BE-FE-da-test-valutazione.md` §3 D5.
> **Decisione di Tid, 2026-09-11:** l'assistente AI **lo devono poter usare anche
> gli operatori**, non solo gli amministratori.
> **Decisione di Tid, 2026-09-24:** l'assistente **assume i privilegi con cui
> l'operatore è attivo, e nessuno di più**. `LETTURA` vuol dire «vedo i dati, non
> eseguo azioni» — e deve valere per l'AI come per la UI.
>
> **In una riga:** `AIQueryView` dichiara `area_funzionale = "ai_assistant"`, e
> quella chiave **non esiste** in `config.aree_funzionali`. La catena dei
> permessi fa il suo mestiere (fail-closed), e proprio per questo l'endpoint è
> raggiungibile **solo da un `SUPER_ADMIN`**: a nessun altro il permesso si può
> concedere, perché manca la riga a cui appenderlo.
>
> ⭐ **Stato al 2026-09-24:** §5.2 fatto (backend). §4 (DB) da fare; §5.3 lo
> aspetta.
>
> ⇒ **Al DB: una riga di catalogo** (§4).
> ⇒ **Al backend: una sola regola dei permessi per UI e AI, e un significato per
> i tre livelli dell'area `ai_assistant`** (§5). Senza questa parte, la riga del
> §4 darebbe agli amministratori un livello `LETTURA` che non funziona.

---

## 1. Il fatto, letto dalla struttura

`backend/apps/ai_assistant/api/views.py:77`

```python
class AIQueryView(DomainAPIView):
    area_funzionale = "ai_assistant"
```

Il catalogo è `config.aree_funzionali` (mirror
`80_data/sql/config/aree_funzionali.csv`, changeSet `20260228-17`), tredici
righe al 2026-09-24: `anagrafiche`, `vendite`, `acquisti`, `catalogo`,
`contabilita`, `magazzino`, `pagamenti`, `storico`, `config`, `core`,
`pratiche`, `documenti`, `strumenti`.

⛔ **`ai_assistant` non c'è.**

### 1.1 ⛔ La chiave è `schema_db`, non `codice`

`script.fn_resolve_livello_area(p_auth_user_id, p_area_schema_db)` — firma e
corpo dalla doc auto-generata — cerca l'area **sempre** con
`af.schema_db = p_area_schema_db`: nel ramo degli override utente e in quello
dei profili. `codice` e `codice_interno` non entrano nel confronto. Il backend lo
sa e lo scrive (`amm_software_repository.py`, «`fn_resolve_livello_area` matcha
sulla colonna `schema_db` (chiave tecnica), NON sul `codice`»).

Per un'area che il catalogo non nomina: nessun override, nessun profilo ⇒
**passo 5, `RETURN 'BLOCCATO'`**.

### 1.2 Il 403 punta nella direzione sbagliata

Non è un buco: è il suo opposto, ed è ciò che lo rende difficile da trovare. A un
operatore che non ha un profilo che copra l'area, `_set_deny_message` risponde
*«Il reparto non ha ancora un profilo permessi configurato»*. Il messaggio manda
a cercare nei profili di reparto, dove non c'è niente da sistemare: la verità è
«il permesso non esiste e nessuno può dartelo».

### 1.3 Le aree fuori catalogo: una nelle view, una nei tool

* Fra le nove aree che il backend dichiara nelle view (`area_funzionale = …`),
  `ai_assistant` è **l'unica** fuori catalogo.
* ⛔ Fra le aree che dichiarano **i tool dell'assistente** (`required_area`) ce
  n'è una seconda: `cerca_operatori` (`config_tools.py`) chiede
  `required_area="amm_software"`, che il catalogo non ha. Funziona come «solo
  `SUPER_ADMIN`» per lo **stesso** meccanismo descritto sopra: la riga che
  manca. Se è voluto, è voluto nel posto sbagliato; il §5.2 lo chiude senza
  bisogno di una riga nuova.

---

## 2. Perché adesso, se la funzione è spenta

Le rotte sono montate solo con `AI_ENABLED=1`, che di default vale `0`: a flag
spento l'app non è nemmeno in `INSTALLED_APPS`.

⛔ **«Oggi non capita mai» è uno degli argomenti che la Regola zero rifiuta per
nome.** Il giorno in cui la funzione si accende, si accende **rotta per tutti
tranne uno** — e in quel momento la diagnosi costa molto più di adesso, perché
il sintomo (§1.2) punta nella direzione sbagliata.

---

## 3. Le decisioni prese, e le strade che escludono

### 3.1 Come si concede l'assistente

| Strada | Cosa comporta |
| --- | --- |
| **Riga a catalogo** ⇐ **scelta** | L'assistente si concede per area come ogni altro dominio, dal pannello dei profili, coi tre livelli — ai quali il §5.3 dà un significato |
| Azione di processo (`usa_assistente_ai` in `config.azioni_processo`, letta da un `post_permission`) | Un interruttore sì/no: esprime «può usarlo», non «può usarlo solo per consultare». ⛔ Esclusa: la decisione del 2026-09-24 chiede proprio quella distinzione |
| `AdminAPIView` | Zero passaggi dal DB, ma l'assistente resta riservato a `SUPER_ADMIN`. ⛔ Esclusa dalla decisione del 2026-09-11 |

### 3.2 Cosa significa `LETTURA`, e dove è imposto oggi

`LETTURA` significa: **vedo i dati, non eseguo azioni** (inserimento, modifica,
cancellazione). Dove è imposto, letto dal codice il 2026-09-24:

| Livello | Cosa fa |
| --- | --- |
| Frontend | nasconde i pulsanti delle azioni — comodità, non protezione |
| **Backend** | ✅ **lo impone**: `ZeroERPPermission` traduce il metodo HTTP in un tipo di accesso (`POST` → `add`, …) e `LETTURA` concede solo `view`. Un `curl` in `LETTURA` riceve 403 |
| **DB** | ⛔ **niente**: nessuna policy e nessuna funzione confronta il livello. Il DB **calcola** il livello (`fn_resolve_livello_area`, `fn_check_azione_processo`); **lo applica** solo il backend. La RLS decide *quali righe* si vedono, non *cosa* ci si può fare |

⇒ Oggi la sola barriera fra un operatore in `LETTURA` e una scrittura è il
backend. Per l'AI questo è il punto del §5. Se la barriera debba stare **anche**
a DB è una domanda più grande, di tutto il sistema e non dell'assistente: è
fuori da questo brief (§8).

---

## 4. Cosa si chiede al DB — una riga

Nel mirror `80_data/sql/config/aree_funzionali.csv`:

| Colonna | Valore | Perché |
| --- | --- | --- |
| `id` | **14** | primo libero. Il catalogo si popola solo dal CSV (il backend lo legge e basta), quindi non serve riallineare la sequence |
| `schema_db` | `ai_assistant` | ⛔ **è la chiave** (§1.1): deve combaciare con la stringa di `AIQueryView.area_funzionale` e con quella che i tool passano al resolver |
| `codice` · `codice_interno` | `ai_assistant` | l'invariante presidiato dal pgTAP `test-permessi-strutture-base` è `schema_db = codice` per **tutte** le righe |
| `descrizione` | `Assistente AI` | è ciò che l'amministratore legge nel pannello dei profili |
| `attivo` | `t` | |
| `ordinamento` | **140** | dopo `strumenti` (130), che è l'ultima |
| audit | data del changeSet, `postgres` | come le righe sorelle |

### 4.1 `schema_db` è la chiave tecnica dell'area, non il nome di uno schema

Il `COMMENT` della tabella dice *«Ogni area corrisponde a uno schema DB; il
mapping area→schema è automatico (Django risolve l'area dal `db_table` del
model)»*, e la colonna `schema_db` dice *«Nome dello schema PostgreSQL
associato»*.

Il modello dice un'altra cosa, e la dice in tre posti:

* il resolver usa `schema_db` come **chiave** (§1.1);
* il pgTAP la vincola **uguale a `codice`**, non all'esistenza di uno schema;
* il backend ricava l'area in due modi: dal `db_table` del model quando la view
  ha un queryset, e **dall'attributo `area_funzionale`** quando non ce l'ha. Il
  secondo modo non passa da nessuno schema fisico.

⇒ Che `schema_db` coincida con uno schema reale è un **caso particolare**, non la
regola. `ai_assistant` non chiede un'eccezione: è una riga che il modello ammette
già. (Fatto datato, a margine: il 2026-09-11 un `LEFT JOIN` su `pg_namespace`
trovava già `core` e `strumenti` senza schema omonimo.)

**Si corregge anche la descrizione** — un `COMMENT ON TABLE` e un
`COMMENT ON COLUMN … schema_db`, quindi DDL, in `00_schema`. Il testo va scritto
sul modello, **senza elencare le aree** (un elenco dentro un commento è una sede
in più che nessuno aggiorna):

> *`schema_db`: chiave tecnica dell'area, con cui il backend e le funzioni di
> risoluzione dei permessi la identificano; uguale a `codice`. Coincide con uno
> schema fisico quando l'area ne ha uno.*

### 4.2 Cosa NON si chiede

* ⛔ **Nessuna azione di processo nuova.** Il perché è nel §5: ciò che l'AI può
  fare lo decide l'endpoint che ciascun tool rispecchia, con le sue azioni già a
  catalogo. (La versione precedente di questo brief diceva che ogni tool
  dichiara la propria azione: al 2026-09-24 la dichiara **uno** su diciotto,
  `cambia_stato_pratica`.)
* ⛔ **Nessun override, nessun profilo seminato.** Chi può usare l'assistente lo
  decide l'amministratore, dopo. La riga è la *possibilità* di decidere, non la
  decisione.
* ⛔ **Nessuna policy RLS nuova.** I tool leggono attraverso i service di
  dominio, sotto le stesse policy che presidiano le tabelle.

### 4.3 Emerso, non chiesto — decisione a Tid

`schema_db` è la chiave, ma il blocco sulle modifiche della tabella
(`trgfn_lock_columns`) protegge `codice_interno`, che nessuno usa per il
confronto. Rinominare `schema_db` di una riga scollega in silenzio override e
profili di quell'area. Proteggere anche `schema_db` è un changeSet a sé (il
trigger di lock si rigenera, non si modifica): **non** fa parte di questo brief.

---

## 5. Cosa si chiede al backend

### 5.1 Il problema: la stessa regola scritta due volte

I tool dell'AI non passano dagli endpoint REST: chiamano direttamente service e
repository. Quindi `ZeroERPPermission` non li vede, e i loro permessi sono
controllati da una **seconda copia** della regola, `is_tool_allowed_for_user`
(`tool_registry.py`). Ogni tool la alimenta con valori **scritti a mano**:
`required_area`, `required_level`, `required_action`.

Il controllo in sé è fatto bene: il catalogo offerto al modello è filtrato, e il
filtro viene **ripetuto al momento dell'esecuzione** e di nuovo alla conferma di
una scrittura. Il difetto è che le copie sono due, e al 2026-09-24 dicono già
cose diverse:

| Operazione | Endpoint della UI | Tool dell'AI |
| --- | --- | --- |
| cambio stato pratica | `ApiPraticaStato`: `post_permission = "cambia_stato_pratica"` ⇒ **solo l'azione** (con `<metodo>_permission` il livello d'area non si guarda) | area `TUTTO` **e** l'azione |
| elenco operatori | endpoint di amministrazione (`SUPER_ADMIN`) | `required_area="amm_software"`, area che non esiste (§1.3) |

⛔ E il caso che la decisione di Tid vuole escludere: un tool che **scrive**
dichiarato `required_level="LETTURA"` per svista scrive anche per un operatore in
sola lettura. Nessun livello lo ferma — non il backend, perché il valore
sbagliato è proprio il suo, e non il DB (§3.2).

### 5.2 Parte A — una regola sola per UI e AI

**Richiesta:** il permesso di un tool **non si dichiara, si deriva** dall'endpoint
che il tool rispecchia.

* Ogni tool dichiara **quale endpoint** (classe della view e metodo HTTP) fa la
  stessa cosa nella UI. Non dichiara più `required_area`, `required_level` né
  `required_action`.
* La decisione «questo utente può fare questa chiamata?» si **estrae** da
  `ZeroERPPermission.has_permission` in una funzione che prende l'utente, la
  classe della view e il metodo. La chiamano **tutti e due**: la classe dei
  permessi DRF e il filtro dei tool. È la regola del 2: la copia in
  `is_tool_allowed_for_user` si ritira **nello stesso giro**, non dopo.
* Si ottengono per costruzione, senza casi speciali: area dal model o da
  `area_funzionale`, `<metodo>_permission`, `SUPER_ADMIN`, ruolo disabilitato,
  override per oggetto. `cerca_operatori` che rispecchia l'endpoint di
  amministrazione diventa «solo `SUPER_ADMIN`» perché **lo è l'endpoint**, e
  `amm_software` sparisce.
* ⚠️ Un tool che non ha un endpoint gemello è l'eccezione: la si dichiara nel
  tool con il motivo scritto accanto, e il test del §5.4 la elenca per nome.

Restano com'erano: la blacklist `AI_DISABLED_TOOLS`, la conferma sulle scritture
e il doppio controllo al momento dell'esecuzione (che da adesso chiama la regola
unica).

⭐ Questa parte **non dipende dal DB**: si può fare subito.

#### 5.2.1 ✅ Fatto il 2026-09-24 (backend, `dev/backend-tid`)

* **La regola estratta.** `ZeroERPPermission.valuta` e `IsAdminZeroERP.valuta`
  decidono senza richiesta HTTP; `has_permission` le chiama e registra il
  diniego (log di sicurezza e messaggio del 403 invariati).
  `valuta_accesso_endpoint(user, view, method=…)` applica le
  `permission_classes` della view in AND come DRF, ed è **fail-closed** su una
  classe senza `valuta`. Registrata nel catalogo BB backend.
* **I tool legati al gemello.** `AITool` riceve `endpoint=EndpointGemello(view,
  metodo)`; `required_area`, `required_level` e `required_action` non esistono
  più. `is_tool_allowed_for_user` tiene la blacklist e poi chiama la regola
  unica: offer-time, execution-time e conferma passano tutti di lì.
* **I 18 gemelli**:

| Tool | Gemello |
| --- | --- |
| `cerca_pratiche` · `crea_pratica` | `ApiPraticheList` GET · POST |
| `dettaglio_pratica` | `ApiPraticaDetail` GET |
| `cerca_flussi_pratica` | `ApiPraticaFlussiList` GET |
| `cambia_stato_pratica` | `ApiPraticaStato` POST (`post_permission`) |
| `aggiungi_nota_pratica` | `ApiPraticaNoteList` POST |
| `cerca_soggetti` · `dettaglio_soggetto` | `SoggettiView` · `SoggettiDetailView` GET |
| `cerca_billing_account` | `BillingAccountLookupView` GET |
| `cerca_articoli` | `ApiArticoliLookup` GET |
| `cerca_operatori` | `OperatoriListView` GET (`AdminAPIView`) |
| `cerca_contratti` · `dettaglio_contratto` | `ApiContrattiList` · `ApiContrattoDetail` GET |
| `cerca_preventivi` · `dettaglio_preventivo` | `ApiPreventiviList` · `ApiPreventivoDetail` GET |
| `cerca_promo_articoli` | `PromoArticoliView` GET |
| `cerca_listini` | `ApiListiniList` GET |
| `cerca_documenti_generati` | `ApiPreventivoDocumentiList` GET |

* **Cosa cambia per l'operatore** — ogni riga è l'AI che si allinea alla UI, non
  una scelta nuova:
  * `cambia_stato_pratica`: prima area `TUTTO` **e** azione, ora **solo
    l'azione**, come `ApiPraticaStato`;
  * `cerca_articoli`, `cerca_billing_account`: prima `LETTURA` su
    `catalogo`/`anagrafiche`, ora i gemelli sono i **lookup cross-dominio**
    (`skip_area_check`): li usa ogni operatore attivo, come li usa ogni drawer
    della UI. ✅ **Decisione di Tid, 2026-09-25:** va bene così. All'AI basta
    ciò che vede la casella di ricerca dei form, e il gemello resta il lookup,
    non la lista del dominio;
  * `cerca_documenti_generati`: prima area `documenti`, ora `vendite`, l'area
    in cui è montata la lista documenti del preventivo;
  * `cerca_soggetti`, `dettaglio_soggetto`, `cerca_promo_articoli`: ora
    contano anche gli **override per oggetto** (`model_permission` del gemello);
  * `cerca_operatori`: sempre «solo `SUPER_ADMIN`», ora perché lo è
    l'endpoint. `amm_software` sparisce dal codice;
  * il superuser Django passa, come passa dalla UI.
* **Eccezioni senza gemello:** nessuna. `AITool` pretende un `endpoint`; un tool
  che non ne ha uno va deciso e scritto per nome in `_SENZA_GEMELLO`
  (`test_tool_endpoint_gemello.py`).
* **Presidio 2 del §5.4: ✅** — `test_tool_endpoint_gemello.py`: per ogni tool
  registrato, il gemello è una `APIView` che implementa il metodo, il metodo è
  traducibile, ogni permission class ha `valuta`, e la conferma dichiarata
  coincide con un gemello di scrittura.

✅ **Emerso e corretto il 2026-09-24 (su richiesta di Tid).** `cerca_billing_account`
passava al service le PK degli emittenti (`get_emittenti_pk_ids`), mentre il
gemello `BillingAccountLookupView` passa i soggetto-ruolo
(`get_emittenti_sr_ids`). È questo che vuole
`script.fn_check_ba_visible_for_emittenti`
(`fn_get_ba_emittente_sr_id(...) = ANY(p_emittente_ids)`): dall'AI un BA
legittimo spariva. Fuori perimetro non si usciva, perché la policy RLS `via_efba`
filtra comunque. Il difetto nasceva dalle **due copie** dello scope, e si
chiude togliendole (regola del 2, ok Tid 2026-09-25):
`BillingAccountService.search_lookup(user=…)` risolve lo scope da sé, coi
soggetto-ruolo, e view e tool passano solo l'utente. Il presidio
`test_billing_account_tool_scope.py` fa passare tool e view dallo stesso
resolver e pretende che arrivi al repository lo **stesso** scope.

### 5.3 Parte B — cosa significano i tre livelli dell'area `ai_assistant`

Con la regola unica, ciò che l'AI può fare su un dominio è già quello che può
fare l'operatore. Il livello su `ai_assistant` aggiunge un secondo filtro,
**più restrittivo**, sullo strumento stesso:

| Livello su `ai_assistant` | L'assistente può |
| --- | --- |
| `BLOCCATO` | niente: l'endpoint risponde 403 |
| `LETTURA` | **consultare**: solo i tool il cui endpoint gemello è una lettura |
| `TUTTO` | anche **agire**: i tool di scrittura, sempre con conferma |

⭐ In ogni caso vale **il più stretto dei due livelli**: quello su `ai_assistant`
e quello dell'operatore sul dominio del tool. Un operatore con `TUTTO` su
`pratiche` e `LETTURA` su `ai_assistant` crea pratiche dalla UI ma non tramite
l'assistente. Uno con `TUTTO` su `ai_assistant` e `LETTURA` su `pratiche` non ne
crea da nessuna parte.

Tre cose servono perché la tabella sia vera:

1. **L'ingresso chiede `view`, non `add`.** `AIQueryView` risponde a una `POST`,
   e oggi una `POST` chiede `add` ⇒ `LETTURA` darebbe 403 anche solo per fare una
   domanda. Una domanda all'assistente è una lettura: l'ingresso deve chiedere
   `view`. Si fa con un **meccanismo dichiarativo generale** in
   `ZeroERPPermission` (un attributo della view che dice quale tipo di accesso
   chiede il metodo), non con un caso speciale per questa view.
2. **«Questo tool scrive» si deriva, non si dichiara.** Lo dice il tipo di
   accesso che l'endpoint gemello richiede (qualunque cosa diversa da `view`, o
   un'azione di processo). Un flag scritto a mano sul tool ripeterebbe il difetto
   del §5.1.
3. ⭐ **Una lettura la garantisce il DB, non la dichiarazione.** Ogni tool il cui
   endpoint gemello è una lettura — e l'**anteprima** di ogni tool di scrittura,
   che non deve scrivere niente — gira dentro una transazione aperta con
   `SET TRANSACTION READ ONLY`. Se un tool classificato come lettura prova a
   scrivere, per errore di classificazione o per un service che scrive più di
   quanto dice, lo ferma **PostgreSQL** (`25006`), comprese le funzioni
   `SECURITY DEFINER`: è una regola della transazione, non del ruolo.
   * La sola lettura si imposta **per transazione, mai per sessione**: con
     `CONN_MAX_AGE` le connessioni si riusano, e un'impostazione di sessione
     passerebbe alla richiesta successiva.
   * Restano **fuori** dal blocco: l'`INSERT` in `dbops.ai_query_log` e
     l'esecuzione confermata di un tool di scrittura.
   * Verificato il 2026-09-24 che la lettura oggi non scrive sulla connessione
     della richiesta: il `tx_id` arriva via dblink (altra connessione),
     `request_log` si scrive dopo la risposta, `ATOMIC_REQUESTS` è spento.
   * È lo stesso meccanismo che il brief
     [brief-be-letture-in-transazione-sola-lettura.md](brief-be-letture-in-transazione-sola-lettura.md)
     estende a **tutte** le `GET`: se il backend lo realizza come building block,
     i tool lo **usano**, non ne scrivono una copia (regola del 2).

⚠️ La conferma di una scrittura passa anch'essa da `AIQueryView`: l'ingresso a
`view` la lascia entrare, e il filtro sul `TUTTO` di `ai_assistant` sta nel
controllo del tool, che viene ripetuto proprio al momento della conferma.

⛔ Questa parte **dipende dalla riga del §4**: fino ad allora l'area
`ai_assistant` vale `BLOCCATO` per tutti tranne `SUPER_ADMIN`.

### 5.4 I presìdi

1. **Aree dichiarate contro catalogo** — un test su DB provvisto
   (`richiedi_db_provvisto`) che raccoglie le `area_funzionale` **dalle view** e
   fallisce su una che non trova in `config.aree_funzionali.schema_db`
   (**`schema_db`**, non `codice`: §1.1). Dopo la parte A i tool non dichiarano
   più aree, quindi le view bastano. ⚠️ L'elenco si ricava dal codice, non da una
   lista scritta a mano.
2. **Ogni tool ha il suo endpoint** — un test che per ogni tool registrato
   verifica che l'endpoint gemello esista davvero, ed elenca **per nome** le
   eccezioni del §5.2.
3. **La semantica del §5.3, costruita e non trovata** — tre operatori
   **fabbricati** nel test, non presi dai dati: `LETTURA` su `ai_assistant` +
   `TUTTO` su `pratiche` (consulta, **non** crea); `TUTTO` + `LETTURA` (non crea);
   `TUTTO` + `TUTTO` (crea, previa conferma).
4. **Una lettura che scrive viene fermata dal DB** — un tool di prova,
   **fabbricato nel test** e classificato come lettura, che tenta un `INSERT`:
   deve fallire con `25006` e non lasciare righe. Lo stesso per l'anteprima di un
   tool di scrittura.

### 5.5 Da registrare alla chiusura

`api.md` §Endpoint attivi (l'app è citata con il difetto scritto accanto) e
`migliorie-generali-BE-FE-da-test-valutazione.md` §3 D5.

---

## 6. Come si verifica

**DB**, dopo la riga:

```sql
-- una riga, con la chiave giusta
SELECT id, codice, schema_db, attivo, ordinamento
  FROM config.aree_funzionali WHERE schema_db = 'ai_assistant';

-- un operatore senza concessioni resta BLOCCATO: è corretto
SELECT script.fn_resolve_livello_area(<auth_user_id>, 'ai_assistant');
```

⚠️ La seconda query non prova la chiusura da sola: `BLOCCATO` resta la risposta
giusta finché l'amministratore non concede un livello. La prova vera è la prima
query più l'area «Assistente AI» fra quelle assegnabili nel pannello dei profili.

**Backend:** i tre test del §5.4.

---

## 7. Perimetro e rischio

| | |
| --- | --- |
| **DB — righe** | 1 (un'aggiunta al CSV) |
| **DB — DDL** | i due `COMMENT` del §4.1 |
| **Backend** | §5: estrazione della regola, tool legati al loro endpoint, meccanismo «tipo di accesso per metodo», letture dei tool in transazione di sola lettura, quattro presìdi |
| **Rischio di regressione DB** | nessuna riga esistente cambia; gli invarianti del pgTAP `test-permessi-strutture-base` (almeno 13 righe attive, `schema_db = codice`, `ordinamento` positivo) valgono anche con la riga nuova |
| **Effetto a flag spento** | ⚠️ **non nullo**: il pannello dei profili elenca le aree con `attivo = true`, quindi «Assistente AI» compare fra le aree assegnabili (e come colonna nella matrice degli utenti) anche dove l'AI è spenta. Accettato: concedere un livello su una funzione spenta non apre niente |
| **Reversibile** | ⚠️ con `attivo = false` **solo finché nessuno la usa**: i trigger `block_deact` legati a `profili_accesso_aree` e `user_override_aree` bloccano la disattivazione appena un amministratore l'assegna |

---

## 8. Fuori da questo brief

* **Il livello imposto anche dal DB** (§3.2). Approfondito il 2026-09-24 e
  diviso in due, **per decisione di Tid**:
  * **Ogni `GET` in una transazione di sola lettura** — il DB garantisce che una
    lettura non scriva, per tutta la UI e non solo per l'AI. Fra le **prime
    cose** da fare, insieme a questo brief:
    [brief-be-letture-in-transazione-sola-lettura.md](brief-be-letture-in-transazione-sola-lettura.md).
  * **Il permesso controllato nel verbo di scrittura** — una scrittura passa
    solo da una funzione DB che controlla azione o livello: protegge anche da
    un backend che autorizza la scrittura sbagliata, che la sola lettura non
    copre. Cantiere di architettura, con decisioni aperte:
    [brief-db-permesso-nel-verbo-di-scrittura.md](brief-db-permesso-nel-verbo-di-scrittura.md).
  * ⛔ **Esclusa**: policy RLS di scrittura sul livello d'area. Una policy vede
    la tabella, non l'operazione — bloccherebbe l'operatore in `LETTURA` a cui è
    stata concessa un'azione — e le funzioni DEFINER la scavalcano. Il
    ragionamento completo è nel secondo brief, §3.
* **Da verificare (pgTAP):** in `test-permessi-strutture-base.sql` le due
  `INSERT` negative che provano i vincoli UNIQUE non passano un `id`. Se la
  sequence è ancora vergine, il `23505` scatta sulla **chiave primaria** e il
  test è verde per il vincolo sbagliato.

---

## Registro

| Data | Chi | Cosa |
| --- | --- | --- |
| 2026-09-11 | backend | Brief scritto; decisione di Tid «anche gli operatori» |
| 2026-09-24 | DB (rilettura critica) | Corretti: la chiave è `schema_db` (§1.1), il messaggio del 403 (§1.2), la seconda area fuori catalogo nei tool (§1.3), «ogni tool dichiara la sua azione» (§4.2), effetto a flag spento e reversibilità (§7), testo del `COMMENT` senza elenco (§4.1). Aggiunta la terza strada (§3.1) |
| 2026-09-24 | Tid | «L'AI assume solo i privilegi con cui l'operatore è attivo». ⇒ Aggiunto il §5 (parti A e B) come richiesta al backend; l'imposizione del livello a DB rinviata a un approfondimento (§8) |
| 2026-09-24 | Tid | Dopo l'approfondimento: le letture dei tool in transazione di sola lettura entrano qui (§5.3 punto 3, §5.4 punto 4); la stessa garanzia per tutte le `GET` e il permesso nel verbo vanno in due brief propri (§8), il primo fra le prime cose da fare |
| 2026-09-24 | backend | **§5.2 (parte A) fatta**, su decisione di Tid di procedere solo con quella: regola estratta (`valuta_accesso_endpoint`), 18 tool legati al gemello, `required_*` e `amm_software` ritirati, presidio 2 del §5.4. Resoconto e cambi di comportamento nel §5.2.1. Il DB **non** ha ancora eseguito il §4 (riga assente dal CSV su `dev/db-tid` e `main`): §5.3 e presìdi 1, 3, 4 restano in attesa |
| 2026-09-25 | Tid | Gemelli di `cerca_articoli` e `cerca_billing_account`: restano i lookup cross-dominio (§5.2.1). Corretto lo scope emittente di `cerca_billing_account` (PK → soggetto-ruolo), poi spostato nel service: view e tool passano l'utente (regola del 2, ok Tid) |
