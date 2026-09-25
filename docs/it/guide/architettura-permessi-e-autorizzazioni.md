# Guida — Architettura Permessi e Autorizzazioni

> **Ultimo aggiornamento**: 19 settembre 2026
>
> **Destinatari**: sviluppatori database, backend e analisti funzionali
>
> **Vedi anche** — schemi DB:
>
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — il ponte multi-veste: un account, piu' vesti attive
> * [config.profili_accesso](/dbzero/config/tabelle/profili_accesso) — i profili di accesso (REPARTO / PORTALE / AD_HOC / SUPER_ADMIN)
> * [config.profili_accesso_aree](/dbzero/config/tabelle/profili_accesso_aree) / [config.profili_accesso_azioni](/dbzero/config/tabelle/profili_accesso_azioni) — cosa concede un profilo
> * [config.profili_accesso_bindings](/dbzero/config/tabelle/profili_accesso_bindings) — a chi e' legato un profilo
> * [config.aree_funzionali](/dbzero/config/tabelle/aree_funzionali) / [config.azioni_processo](/dbzero/config/tabelle/azioni_processo) — il catalogo delle aree e delle azioni
> * [config.user_override_aree](/dbzero/config/tabelle/user_override_aree) / [config.user_override_oggetti](/dbzero/config/tabelle/user_override_oggetti) / [config.user_override_azioni](/dbzero/config/tabelle/user_override_azioni) — le eccezioni individuali
> * [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali) — il perimetro di emittenti dell'operatore
> * [config.scope_policy](/dbzero/config/tabelle/scope_policy) / [config.identita_scope_bindings](/dbzero/config/tabelle/identita_scope_bindings) — le policy di scope e i loro legami
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin) — il check di bypass
> * [script.fn_get_profili_accesso_applicabili](/dbzero/script/funzioni/fn_get_profili_accesso_applicabili) — i profili applicabili a un utente
> * [script.fn_resolve_livello_area](/dbzero/script/funzioni/fn_resolve_livello_area) / [script.fn_resolve_livello_oggetto](/dbzero/script/funzioni/fn_resolve_livello_oggetto) — la catena risolta lato DB
> * [script.fn_check_user_emittente_scope](/dbzero/script/funzioni/fn_check_user_emittente_scope) — la regola di scope emittente, sede unica
> * [script.fn_get_emittenti_scope_pk_ids](/dbzero/script/funzioni/fn_get_emittenti_scope_pk_ids) / [script.fn_get_emittenti_scope_sr_ids](/dbzero/script/funzioni/fn_get_emittenti_scope_sr_ids) — gli emittenti nel perimetro dell'utente
> * [script.trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope) — il write-guard di difesa in profondita'
>
> **Vedi anche** — guide correlate:
>
> * [Guida Soggetti & Ruoli Anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il prerequisito anagrafico
> * [Architettura Multi-Face Auth](/guide/architettura-multi-face-auth) — il modello delle vesti
> * [Contratto GUC `app.*`](/guide/contratto-guc-app) — i parametri di sessione PostgreSQL
> * [Risorse Umane e Accessi](/guide/risorse-umane-e-accessi) — il ciclo di vita degli operatori

---

## 1. Obiettivo

Definire un sistema di permessi per Zero ERP che sia:

- **scalabile** — nuovi moduli e azioni senza modifiche strutturali,
- **granulare** — controllo fino al singolo utente e singolo oggetto,
- **Circoscritto** — operativita' limitabile per emittente fiscale,
- **semplice da gestire** — pochi click per configurare un operatore,
- **coerente** — integrato con il modello soggetti/ruoli e schemi DB esistenti.

---

## 2. Concetti chiave

### 2.1 Area funzionale = Schema DB

Ogni schema del database corrisponde automaticamente a un'**area funzionale**.
Le API Django ereditano l'area dallo schema del model che servono.

| Schema DB     | Area funzionale | Esempi di oggetti                      |
| ------------- | --------------- | -------------------------------------- |
| `anagrafiche` | Anagrafiche     | soggetti, clienti, contatti, emittenti |
| `vendite`     | Vendite         | fatture, ordini, lotti                 |
| `acquisti`    | Acquisti        | ordini acquisto, DDT in ingresso       |
| `catalogo`    | Catalogo        | articoli, listini                      |
| `config`      | Configurazione  | parametri, tipi ruoli, qualifiche      |
| `contabilita` | Contabilita'    | movimenti, piano conti                 |
| `magazzino`   | Magazzino       | giacenze, movimenti magazzino          |
| `pagamenti`   | Pagamenti       | rimesse, incassi, scadenze             |
| `storico`     | Storico         | log, archivi                           |
| `core`        | Core            | funzioni dbops/scripts                 |

Questo mapping e' **automatico**: Django conosce lo schema di ogni model
dalla `Meta.db_table`. Nessuna configurazione manuale per il caso standard.

Un model puo' essere **riassegnato** a un'area diversa dal suo schema tramite
la tabella `config.area_model_overrides` (vedi sezione 4.3), ma si tratta
di un'eccezione rara.

### 2.2 Tre livelli di accesso per area

| Livello      | Significato                                    |
| ------------ | ---------------------------------------------- |
| **TUTTO**    | CRUD completo su tutti gli oggetti dell'area   |
| **LETTURA**  | Solo visualizzazione (`view_*`)                |
| **BLOCCATO** | Nessun accesso, l'area non e' nemmeno visibile |

Questi tre livelli coprono il **90% delle esigenze quotidiane** e rendono
la configurazione di un operatore immediata: una riga per area, un radio button.

### 2.3 Azioni di processo (permessi puntuali)

Oltre al CRUD esistono azioni che richiedono abilitazione esplicita,
indipendentemente dal livello sull'area. Anche avendo TUTTO su vendite,
un operatore potrebbe non poter eseguire azioni critiche.

Esempi:

| Azione                         | Area      | Descrizione                 |
| ------------------------------ | --------- | --------------------------- |
| `vendite.genera_fatture_lotti` | vendite   | Generazione massiva fatture |
| `vendite.genera_fattura`       | vendite   | Generazione singola fattura |
| `vendite.approva_fattura`      | vendite   | Approvazione fattura        |
| `vendite.emetti_fattura`       | vendite   | Emissione fattura           |
| `pagamenti.approva_rimessa`    | pagamenti | Approvazione rimessa        |

Le azioni nascono nel codice Django (`Meta.permissions`) e vengono registrate
automaticamente in `auth_permission`. La tabella `config.azioni_processo`
le elenca per renderle visibili e gestibili nell'interfaccia admin.

### 2.4 Ereditarieta' dal reparto

L'unita' organizzativa (reparto) definisce un **profilo di accesso di default**
che tutti gli operatori del reparto ereditano automaticamente.

**Scelta architetturale: ereditarieta', non template.**

Questo significa che:

- Modificando il profilo del reparto, **tutti gli operatori** del reparto
  vengono aggiornati automaticamente.
- Le eccezioni individuali (override per utente) hanno **sempre priorita'**
  sul profilo ereditato.
- Non serve manutenzione individuale quando cambia una policy aziendale.

> **ATTENZIONE:** modificare il profilo di un reparto ha impatto immediato
> su tutti gli operatori associati. Prima di cambiare il livello di un'area
> su un reparto con molti operatori, verificare che non ci siano conseguenze
> indesiderate. L'interfaccia di gestione dovrebbe mostrare il numero di
> operatori impattati prima di confermare la modifica.

---

## 3. Regola di risoluzione permessi

Quando un operatore tenta un'azione, il sistema risolve i permessi
seguendo una catena di priorita' a cascata. La regola generale e'
che il **livello piu' specifico prevale sempre su quello piu'
generale**, e in assenza di configurazione il default e' restrittivo.

Per l'accesso a un'area o a un singolo oggetto la catena e':

1. **Override individuale su singolo oggetto/model** — se esiste, il
   suo livello (`TUTTO`, `LETTURA` o `BLOCCATO`) vale e la risoluzione
   si ferma qui. E' la forma piu' fine ma anche la piu' rara, usata
   solo per eccezioni puntuali.
2. **Override individuale sull'area** — in assenza di override sul
   singolo oggetto, si applica l'eventuale override sull'area.
3. **Profilo del reparto** — se nemmeno l'area ha un override
   individuale, si applica il livello che il reparto di appartenenza
   ha per quell'area.
4. **Default sicuro** — se nessuna delle regole precedenti applica,
   l'accesso e' `BLOCCATO`.

Per le **azioni di processo** la risoluzione segue lo stesso principio
ma e' binaria (l'azione puo' essere solo concessa o negata):

1. **Override individuale sull'azione** — se esiste, il suo valore
   (grant o deny) vale.
2. **Profilo del reparto** — altrimenti si applica l'abilitazione
   dichiarata a livello di reparto.
3. **Default** — in assenza di configurazioni, l'azione e' negata.

> Il default e' sempre il piu' restrittivo: se non c'e' configurazione,
> l'accesso e' negato.

---

## 4. Modello dati

### 4.1 Tabella `config.aree_funzionali`

> Struttura completa: [aree_funzionali](/dbzero/config/tabelle/aree_funzionali)

Catalogo delle aree funzionali del sistema. Ogni riga mappa uno schema DB
a un'area logica con codice, descrizione e ordinamento per l'interfaccia.

**A cosa serve:** e' la tabella di riferimento per tutte le regole di accesso.
Quando si aggiunge un nuovo schema al sistema, basta inserire una riga qui
perche' l'area diventi configurabile nei profili reparto e negli override utente.

**Esempio di uso:** per ottenere l'elenco delle aree attive utilizzabili
nell'interfaccia di configurazione, si filtra per quelle contrassegnate come
attive e si ordina in base al campo di ordinamento per mantenere la
presentazione coerente fra maschere e menu.

### 4.2 Tabella `config.azioni_processo`

> Struttura completa: [azioni_processo](/dbzero/config/tabelle/azioni_processo)

Registro delle azioni di processo gestibili nell'interfaccia permessi.
Ogni azione e' collegata a un'area funzionale e al `codename` del permesso
Django corrispondente (`auth_permission`).

**A cosa serve:** rende visibili all'interfaccia di gestione le azioni definite
nel codice Django (`Meta.permissions`). Il flag `pericolosa` segnala le azioni
che richiedono conferma aggiuntiva (es. generazione massiva fatture).

**Esempio di uso:** per popolare una maschera di sole azioni pericolose
raggruppate per area, si interroga la tabella incrociata con
`aree_funzionali` e si filtra sul flag di pericolosita' oltre a quello
di attivazione. Il risultato tipico e' una lista ordinata per area e poi
per descrizione dell'azione.

### 4.3 Tabella `config.area_model_overrides`

> Struttura completa: [area_model_overrides](/dbzero/config/tabelle/area_model_overrides)

Override opzionale per riassegnare un model Django a un'area diversa dal suo
schema DB. Uso raro — serve solo quando la convenzione automatica
(schema = area) non e' corretta per un model specifico.

**Esempio di uso:** si supponga che il model `core.parametri_globali`,
per convenzione automatica mappato sull'area Core, debba essere
amministrato sotto l'area Configurazione. Si registra un override
indicando app label, nome del model e area di destinazione scelta dal
catalogo delle aree funzionali. Da quel momento la risoluzione permessi
per quel model usera' la nuova area.

### 4.4 Tabella `config.profili_accesso_aree`

> Struttura completa: [profili_accesso_aree](/dbzero/config/tabelle/profili_accesso_aree)

Cuore dell'ereditarieta': definisce il livello di accesso (`TUTTO`, `LETTURA`,
`BLOCCATO`) che ogni profilo (REPARTO, PORTALE, AD_HOC) ha su ciascuna
area funzionale. Per i profili di tipo REPARTO, tutti gli operatori del
reparto bound al profilo via `profili_accesso_bindings` ereditano
questi livelli automaticamente.

**Esempio di uso:** per il reparto Amministrazione, la configurazione
tipica prevede livello `TUTTO` sull'area Vendite (gli amministrativi
emettono fatture) e livello `LETTURA` sull'area Acquisti (possono
consultare ordini e DDT di ingresso ma non modificarli). Il profilo
REPARTO `REPARTO_AMM` (collegato all'unita organizzativa via
`profili_accesso_bindings.unita_organizzativa_id`) registra una riga
in `profili_accesso_aree` per ciascuna coppia profilo/area, e tutti gli
operatori del reparto ereditano automaticamente questi livelli senza
ulteriori configurazioni.

Quando serve rivedere il profilo completo di un reparto, si consulta
questa tabella filtrata per `profilo_accesso_id` e ordinata per area:
il risultato e' la "scheda permessi" del profilo, pronta per essere
mostrata in interfaccia o esportata in audit.

### 4.5 Tabella `config.profili_accesso_azioni`

> Struttura completa: [profili_accesso_azioni](/dbzero/config/tabelle/profili_accesso_azioni)

Azioni di processo abilitate a livello di profilo. Funziona in coppia con
`profili_accesso_aree`: il livello area controlla il CRUD, questa tabella
controlla le azioni puntuali.

**Esempio di uso:** per abilitare la generazione fatture al reparto
Amministrazione, si registra il profilo con riferimento al
`profilo_accesso_id` (REPARTO_AMM), all'azione identificata dal suo
codename Django (es. `genera_fattura`) e al flag di abilitazione. Da
quel momento tutti gli operatori del reparto vedranno il pulsante di
generazione attivo senza ulteriori override individuali.

### 4.6 Tabella `config.user_override_aree`

> Struttura completa: [user_override_aree](/dbzero/config/tabelle/user_override_aree)

Override individuale per utente su un'area funzionale. Sovrascrive il profilo
ereditato dal reparto. Supporta validita' temporale (`valido_dal`, `valido_al`)
per deleghe o restrizioni temporanee.

**Esempio di uso:** una delega temporanea per sostituire il responsabile
acquisti in ferie si registra come override individuale sull'area
Acquisti, livello `TUTTO`, con motivo esplicito (es. "Delega
sostituzione ferie responsabile acquisti") e validita' limitata al
periodo di assenza (es. dall'1 al 31 marzo). Superata la data di fine,
l'override decade automaticamente e l'utente torna al livello ereditato
dal reparto.

### 4.7 Tabella `config.user_override_oggetti`

> Struttura completa: [user_override_oggetti](/dbzero/config/tabelle/user_override_oggetti)

Override individuale per utente su un singolo model/oggetto. Sovrascrive sia
il profilo del reparto che l'override su area, offrendo il massimo livello
di granularita'.

**Esempio di uso:** un operatore junior dell'area Anagrafiche con
livello `TUTTO` generale, ma che non deve poter modificare i clienti,
riceve un override individuale sul model specifico `anagrafiche.clienti`
a livello `LETTURA`, con motivo descrittivo (es. "Operatore junior:
puo' vedere i clienti ma non modificarli"). L'override vale solo per
quel model: tutti gli altri model dell'area restano con il livello del
profilo del reparto.

### 4.8 Tabella `config.user_override_azioni`

> Struttura completa: [user_override_azioni](/dbzero/config/tabelle/user_override_azioni)

Override individuale per azioni di processo. Sovrascrive l'abilitazione
ereditata dal reparto. Utile per concedere o negare azioni specifiche
a singoli operatori.

**Esempio di uso:** se un operatore di un reparto a cui l'azione non e'
stata abilitata deve comunque poter approvare fatture, si registra un
override individuale sull'azione (identificata dal suo codename Django),
con abilitazione positiva e motivo (es. "Autorizzato dal responsabile
vendite"). Il motivo e' obbligatorio per audit: consente di tracciare
perche' e da chi l'eccezione e' stata concessa.

### 4.9 Tabella `config.user_emittenti_fiscali`

> Struttura completa: [user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali)

Ambito operativo: l'assegnazione fra operatore ed emittente fiscale e' **1-a-1**
(`UNIQUE (auth_user_id)`), e la regola e' **fail-closed**: se l'operatore non ha
righe **non vede nessun emittente** — la riga mancante e' un errore di
configurazione, non un permesso. L'unico attore legittimamente multi-emittente e'
il `SUPER_ADMIN`, che passa da `fn_is_super_admin` e non da questa tabella.

**Esempio di uso:** per abilitare un operatore sull'emittente 3, si registra la
sua riga con `auth_user_id` ed `emittente_fiscale_id`. Ogni tentativo di operare
su un emittente diverso viene bloccato: a livello di policy per le letture, e per
difesa in profondita' dai trigger DB sulle scritture.

Chi resta senza assegnazione si conta in `dbops.vw_operatori_senza_emittente`, che
**deve restare a zero righe**.

---

## 5. Separazione delle responsabilita'

| Livello                | Responsabilita'                                                    | Dove                                  |
| ---------------------- | ------------------------------------------------------------------ | ------------------------------------- |
| **Django/DRF**         | Autenticazione, enforcement permessi sulle API, filtering queryset | Permission classes, Mixins            |
| **DB (config/script)** | Source of truth per profili, aree, override, ambito emittente      | Tabelle config, ENUM, funzioni script |
| **DB (trigger)**       | Defense-in-depth: vincoli di coerenza, guard su ambito emittente   | Trigger sulle tabelle operative       |

Il flusso di una richiesta attraversa, nell'ordine, cinque passaggi:

1. **Autenticazione DRF** — validazione del token JWT e identificazione
   dell'utente.
2. **Permission class principale** — risolve il livello di accesso
   sull'area/oggetto richiesto consultando nell'ordine profilo del
   reparto, override sull'area e override sull'oggetto specifico.
3. **Permission class delle azioni** — per le azioni di processo,
   verifica l'abilitazione considerando reparto ed eventuali override
   individuali.
4. **Mixin di ambito emittente** — applica il filtro sul queryset in
   base alla whitelist `user_emittenti_fiscali`.
5. **View/Serializer** — esegue la logica applicativa; ogni eventuale
   tentativo di operare fuori perimetro viene intercettato come
   ulteriore difesa dai trigger DB al momento di INSERT/UPDATE.

---

## 6. Enforcement Django

> **L'enforcement non assume "un utente = un operatore interno".** Il sistema
> riconosce cinque vesti applicative (operatore, cliente portale, fornitore
> portale, cliente shop, api client) e determina la veste corrente dalla
> **sessione JWT** (claim `identita_id`). La risoluzione dei permessi e' la stessa
> per tutte le vesti, ma la **sorgente** del profilo di accesso cambia: reparto per
> gli operatori, profilo preset per portale e shop.
> Riferimento: [Architettura Multi-Face Auth](/guide/architettura-multi-face-auth).

### 6.1 Funzione di risoluzione permessi (cuore del sistema)

Il `PermissionResolver` e' il componente centrale lato backend che, dato
un utente autenticato (con identita attiva) e una richiesta, calcola il
livello di accesso effettivo seguendo la catena descritta in sezione 3.

**Ingressi del resolver:**

* `auth_user_id` (dalla richiesta autenticata)
* `identita_id` (dal JWT claim custom `identita_id`)
* `ruolo_applicativo` (dalla riga `identita_digitali` corrente)
* `area` o `azione` oggetto della verifica

La tripla `(auth_user_id, identita_id, ruolo_applicativo)` e' necessaria
perche' un `auth_user` puo' avere piu' identita attive in vesti diverse:
il resolver deve sapere per conto di **quale veste** si sta risolvendo.

**Cosa fa, in pratica:**

* **Mappa livello → verbi HTTP.** `TUTTO` ammette view/add/change/delete;
  `LETTURA` ammette solo view; `BLOCCATO` non ammette nulla. E' il
  traduttore fra la terminologia di business (livello di accesso) e i
  permessi tecnici Django.
* **Risoluzione del profilo di accesso.** Il resolver interroga l'helper
  DB `script.fn_get_profili_accesso_applicabili(auth_user_id)` che
  restituisce l'elenco dei `profili_accesso` applicabili, uniti da tre
  sorgenti in ordine di priorita' (dal piu' specifico al piu' generale):
  1. **Binding AD_HOC**: un profilo agganciato direttamente alla
     specifica `identita_digitale` (override massima priorita')
  2. **Binding per reparto**: profilo ereditato dall'unita' organizzativa
     (solo per OPERATORE; richiede catena `identita → risorsa_umana → UO`)
  3. **Binding per ruolo applicativo**: profilo di default della veste
     (es. `CLIENTE_PORTALE`, `FORNITORE_PORTALE`, `SHOP_CUSTOMER`; sulla
     veste `OPERATORE`, un profilo base per tutti gli operatori)

  Per i permessi da operatore contano solo i profili della veste
  `OPERATORE`: un operatore che e' anche cliente shop non porta nei suoi
  permessi il profilo della veste cliente. Per ogni area e azione vince il
  profilo di priorita' piu' bassa, e sotto una veste ce n'e' al massimo uno
  per priorita'. La regola sta in `script.fn_get_permessi_ereditati_aree` /
  `_azioni`, che servono sia i resolver sia la colonna «ereditato» del
  pannello permessi.
* **Risoluzione livello su area.** Prende il livello dal profilo piu'
  specifico applicabile (tabella `profili_accesso_aree`). Se esistono
  override individuali sull'area (`user_override_aree`), questi prevalgono
  rispettando la finestra temporale `valido_dal`/`valido_al`. Default
  sicuro: `BLOCCATO`.
* **Risoluzione livello su oggetto (model).** L'override sul singolo
  model (`user_override_oggetti`) prevale su quello sull'area: un
  operatore puo' avere `TUTTO` sull'area Anagrafiche ma `LETTURA` solo
  sul model `clienti`. Se non esiste override sul model, delega alla
  risoluzione sull'area.
* **Verifica azione di processo.** Prima gli override individuali
  sull'azione (`user_override_azioni`), poi la configurazione dal
  profilo (`profili_accesso_azioni`); in assenza di entrambi l'azione
  e' negata.
* **SUPER_ADMIN bypass.** Se l'identita dell'utente ha un binding al
  profilo `SUPER_ADMIN` (id 9100), la risoluzione restituisce `TUTTO`
  su ogni area e ogni azione senza consultare il resto della catena.
  L'helper `script.fn_is_super_admin(auth_user_id)` espone il check in
  un'unica query STABLE.

**Punti di attenzione:**

* Il resolver non distingue fra vesti nel meccanismo: la catena "override →
  profilo → default" e' identica per operatore e portale. Cio' che cambia
  e' la **sorgente del profilo** (reparto vs preset per ruolo applicativo
  vs ad-hoc).
* Ogni lettura rispetta la finestra temporale degli override: un
  override scaduto non viene applicato, e un override futuro non ha
  effetto fino alla sua data di inizio.
* Il resolver e' di sola lettura: non modifica mai le tabelle config.
  E' invocato ad ogni richiesta API; per questo le query sono ottimizzate
  con indici mirati, l'helper `fn_get_profili_accesso_applicabili`
  restituisce un set unificato, e la mappa finale permessi viene
  calcolata una sola volta per richiesta (cache per-request).

### 6.2 Permission class DRF

Sono previste tre permission class, una per ciascun namespace API, tutte
delegate allo stesso `PermissionResolver`:

* **`ZeroERPPermission`** — per `/api/admin/*` (operatori interni)
* **`PortaleBasePermission`** — per `/api/portale/*` (clienti, fornitori)
* **`ShopPermission`** — per `/api/shop/*` (shop customer + endpoint pubblici)

Nessuna contiene logica di business: delegano tutto al resolver e si
occupano solo di:

1. verificare che la **veste corrente** sia compatibile col namespace
   (es. `PortaleBasePermission` rifiuta un JWT con `ruolo_applicativo =
   OPERATORE`)
2. tradurre l'azione DRF in una richiesta di verifica area/azione

**Come funziona (comune a tutte e tre):**

* **Mapping azione DRF → verbo.** `list` e `retrieve` richiedono `view`,
  `create` richiede `add`, `update` e `partial_update` richiedono
  `change`, `destroy` richiede `delete`. Questo tipo di accesso e' poi
  confrontato con i verbi ammessi dal livello (TUTTO/LETTURA/BLOCCATO).
* **Superuser Django.** Se l'utente è superuser Django (`is_superuser =
  true`), viene ammesso direttamente senza consultare le tabelle config.
  Comportamento di sicurezza a monte, usato in pratica solo per
  amministrazione tecnica. **Nota:** `is_superuser` e' il flag Django,
  non il profilo `SUPER_ADMIN` di ZeroErp — sono concetti distinti.
* **Azioni custom.** Se la view dichiara un permesso esplicito per
  l'azione (es. route "genera-fatture" con `genera_fatture_permission
  = 'genera_fattura'`), la permission class chiama direttamente la
  verifica azione di processo.
* **Azioni CRUD standard.** Per le azioni CRUD si risale al model del
  queryset, si determina l'area funzionale (tramite `app_label`/
  `model_name`) e si consulta il livello effettivo. Il livello viene
  quindi tradotto in insieme dei verbi ammessi: se il verbo richiesto
  non e' nell'insieme, l'accesso e' negato.

**Determinazione dell'area di un model.** Per default, l'area coincide
con lo schema DB (uguale a `app_label` Django). Se per quel model
esiste un override in `area_model_overrides`, si usa l'area dichiarata
dall'override; questo copre i rari casi in cui la convenzione
automatica non e' corretta.

### 6.3 Ambito dati: whitelist EF per operatori, RLS per portale/shop

Il filtro "quali righe l'utente vede tra quelle dell'area" e' implementato
in modo **diverso per veste**, ma tramite un meccanismo unificato (scope
policy):

**Operatori interni.** `EmittenteFiscaleScopeMixin` applica la scope
policy `EF_WHITELIST` al queryset: la view dichiara il percorso del campo
emittente (es. `billing_account__emittente_fiscale`), il mixin legge
`user_emittenti_fiscali` e filtra. Se l'operatore non ha righe, il filtro non
lascia passare **niente**: e' fail-closed, e la riga mancante e' un errore di
configurazione (§4.9).

**Sul lato DB la stessa regola e' una policy RLS.** Per lo scope emittente degli
operatori le tabelle del perimetro hanno la RLS **attiva** (`ENABLE`, senza `FORCE`:
il proprietario delle tabelle e i batch restano fuori). Le policy sono **`FOR ALL`
con `WITH CHECK`**, non solo `FOR SELECT`: con la RLS attiva una scrittura che
nessuna policy permette viene negata, quindi senza `WITH CHECK` ogni INSERT o UPDATE
di un operatore sarebbe finito in deny-all. I batch girano come utente `postgres` e
sono esenti per costruzione. Su `billing_account` la policy di inserimento e'
**gate-only**: verifica i permessi, senza decidere il contenuto della riga.

**Un nome da non confondere.** `BA_OWNERSHIP` e `SELF_OWNERSHIP` sono la stessa
policy: il ruolo anagrafico `CL` e' condiviso fra `CLIENTE_PORTALE` e
`SHOP_CUSTOMER`, quindi tenerle unite evita due definizioni divergenti dello stesso
concetto.

**Clienti portale.** Applica la scope policy `BA_OWNERSHIP` (il cliente
vede solo i propri billing account) oppure `CLIENTE_OWNERSHIP` (per dati
legati al SR-CL direttamente). Il filtro non e' nel mixin: e' **nel DB
tramite Row Level Security** (cfr. §7.1 e §7.2 per la difesa DB e [Multi-Face
Auth §6](/guide/architettura-multi-face-auth#6-row-level-security-la-difesa-al-livello-giusto)
per il dettaglio). Il backend non filtra a mano: la policy RLS lo fa per
tutte le query.

**Fornitori portale.** Scope policy `FORNITORE_OWNERSHIP`, stesso
meccanismo RLS.

**Shop customer.** Scope policy `CLIENTE_OWNERSHIP` + filtro aggiuntivo
`canale_origine = 'SHOP'` dentro la policy RLS, cosi' il consumer B2C
non vede gli acquisti B2B della sua azienda.

**Superuser Django.** Non filtrato: vede sempre tutto, a tutela della
manutenzione tecnica.

L'effetto e' trasparente: la view non deve sapere dello scope — gli
basta (per operatori) dichiarare il campo emittente, e per portale/shop
non deve fare **nulla**, la RLS applica i filtri automaticamente a
ogni SELECT.

### 6.4 Propagazione identita al DB: JWT + GUC

Il middleware `JwtAuditAuthentication` propaga l'identita della sessione
JWT ai parametri di sessione PostgreSQL (GUC), in modo che i trigger DB
e le policy RLS possano sapere per conto di chi stanno eseguendo
un'operazione. Il middleware e' la "spia" che rende possibile
l'enforcement al livello piu' basso dello stack.

**GUC propagati:**

| GUC                       | Popolato da                                      | Usato da                                      |
| ------------------------- | ------------------------------------------------ | --------------------------------------------- |
| `app.current_user_id`     | `auth_user.id` del JWT                           | Trigger audit, retrocompatibilita'            |
| `app.current_identita_id` | Claim JWT `identita_id`                          | Policy RLS, scope policy                      |
| `app.ruolo_applicativo`   | `identita_digitali.ruolo_applicativo` della riga | Gate policy RLS, discriminazione portale/shop |
| `app.soggetto_ruolo_id`   | `identita_digitali.soggetto_ruolo_id` della riga | Helper scope (quando serve il SR dell'utente) |
| `app.jwt_user`            | Username Django                                  | Audit log legacy                              |

**Invariante tutto-o-niente.** I 3 GUC del multi-face
(`current_identita_id`, `ruolo_applicativo`, `soggetto_ruolo_id`) sono
popolati insieme o **nessuno**. Il middleware fail-closed con 401 se la
lettura da `identita_digitali` tramite `identita_id` del JWT fallisce.
Le policy RLS assumono tripla coerente o fail-closed. L'helper
`script.fn_current_identita_context()` esegue lettura fail-soft con
`NULLIF(current_setting(..., true), '')::tipo` e restituisce NULL-tuple
se la tripla non e' coerente.

**Come funziona, in pratica:**

* Ad ogni richiesta autenticata, prima dell'esecuzione della view, il
  middleware: (1) valida il JWT, (2) legge `identita_id` dal claim custom,
  (3) interroga `identita_digitali` per ricavare `ruolo_applicativo` e
  `soggetto_ruolo_id`, (4) imposta i 4 GUC sulla connessione corrente.
  Gli `SET LOCAL` sono scoperati a fine transazione — no pool pollution.
* Un JWT **senza** claim `identita_id` viene comunque tollerato: il middleware lo
  riconosce e deriva l'identita' da `auth_user_id`. E' la via di compatibilita' per
  i token emessi prima dell'introduzione del claim, e si esaurisce col refresh del
  token.
* I trigger DB e le policy RLS leggono i GUC per risalire all'utente,
  alla sua veste e al suo SR. Il contratto dei GUC e' centralizzato in
  una scheda dedicata: [Contratto GUC app.*](/guide/contratto-guc-app).

---

## 7. Defense-in-depth DB

Il database non replica l'enforcement di Django ma aggiunge guardie
che il backend non puo' garantire.

### 7.1 Funzione di verifica ambito emittente

> Struttura completa: [fn_check_user_emittente_scope](/dbzero/script/funzioni/fn_check_user_emittente_scope)

La funzione `script.fn_check_user_emittente_scope(p_auth_user_id, p_emittente_id)`
verifica se un utente e' autorizzato a operare su un dato emittente fiscale. E' la
**sede unica** della regola: la delegano sia il write-guard sia le policy RLS in
lettura, quindi correggerla qui la propaga a entrambi i lati.

I rami, nell'ordine:

1. **`p_auth_user_id` NULL** → `TRUE`: e' il caso dei job batch, che non agiscono
   per conto di un utente.
2. **Emittente non attivo** → `FALSE`.
3. **`SUPER_ADMIN`** → `TRUE`: e' l'unico punto in cui la selezione puo'
   restringere chi vede tutto.
4. **Nessuna riga** in `user_emittenti_fiscali` → `FALSE` (fail-closed, §4.9).
5. **Almeno una riga** → `TRUE` solo se l'emittente e' fra quelle elencate.

**Esempio di uso:** chiamando la funzione con l'identificativo dell'utente e quello
dell'emittente si ottiene `TRUE` o `FALSE` secondo i rami qui sopra. Il check e'
riutilizzabile da viste, report e altre funzioni DB che devono filtrare dati in
base all'ambito dell'utente corrente.

### 7.2 Trigger guard per ambito emittente

> Struttura completa: [trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope)

I trigger guard sulle tabelle operative (es. fatture, ordini) utilizzano
la funzione di verifica per impedire operazioni su emittenti non autorizzati.
Il trigger legge l'identificativo dell'utente corrente dal parametro di
sessione impostato dal middleware Django e blocca l'operazione se
l'utente non e' nell'ambito consentito.

**Esempio di uso — cosa succede in pratica:**

Si immagini un utente limitato agli emittenti 1 e 3 che tenti di
inserire una fattura per l'emittente 5, aggirando per errore il filtro
applicativo. Al momento della scrittura su `vendite.fatture`:

1. Il middleware Django ha gia' propagato nella sessione PostgreSQL
   l'identificativo dell'utente.
2. Il trigger guard `BEFORE INSERT` sulla tabella fatture legge quel
   parametro di sessione e chiama la funzione di verifica emittente
   con l'utente corrente e l'emittente richiesto.
3. La funzione risponde "non autorizzato".
4. Il trigger solleva un errore di autorizzazione e annulla la scrittura.

L'operazione viene quindi negata anche se il backend avesse un bug che
l'ha lasciata passare ai livelli superiori.

### 7.3 Funzioni di risoluzione permessi lato DB

Per scenari in cui il DB deve risolvere i permessi autonomamente (trigger guard,
funzioni di validazione), esistono funzioni SQL che replicano la catena di
risoluzione:

> [fn_resolve_livello_area](/dbzero/script/funzioni/fn_resolve_livello_area) — risolve il livello effettivo di un utente su un'area (override area -> profilo reparto -> BLOCCATO)

> [fn_resolve_livello_oggetto](/dbzero/script/funzioni/fn_resolve_livello_oggetto) — risolve il livello per un singolo model (override oggetto -> override area -> profilo reparto)

> [fn_check_azione_processo](/dbzero/script/funzioni/fn_check_azione_processo) — verifica se un'azione di processo e' abilitata per un utente

**Esempio di uso:** le funzioni si invocano passando l'identificativo
dell'utente e l'area o il codename dell'azione. La prima restituisce
la stringa del livello effettivo (`TUTTO`, `LETTURA`, `BLOCCATO`),
utile per stampe di audit o decisioni condizionali in altre
funzioni/trigger; la seconda restituisce un booleano per verificare
l'abilitazione di un'azione di processo. Entrambe applicano la stessa
catena del backend (override individuale → profilo reparto → default
sicuro), cosi' la regola resta unica indipendentemente dal livello
che la consulta.

---

## 8. Interfaccia di gestione (mockup concettuale)

### 8.1 Configurazione reparto

La schermata di configurazione di un reparto mostra in un'unica
maschera tutto cio' che gli operatori del reparto erediteranno.

L'intestazione indica il reparto (es. "Amministrazione") e il numero
di operatori attualmente associati, cosi' l'amministratore sa in
partenza l'impatto di ogni modifica.

Nella prima sezione viene mostrata la matrice **Aree funzionali x
Livello**: per ogni area (Anagrafiche, Vendite, Acquisti, Catalogo,
Configurazione, Contabilita', Magazzino, Pagamenti, Storico, Core)
l'amministratore seleziona uno tra `TUTTO`, `LETTURA` o `BLOCCATO`.
Una configurazione tipica del reparto Amministrazione puo' essere
`TUTTO` su Anagrafiche, Vendite e Pagamenti; `LETTURA` su Acquisti,
Catalogo, Contabilita' e Storico; `BLOCCATO` su Configurazione,
Magazzino e Core.

Nella seconda sezione compare l'elenco delle **Azioni di processo**
disponibili, ciascuna con un flag di abilitazione. Le azioni marcate
come pericolose (es. "Genera fatture da lotti") sono evidenziate
graficamente perche' meritano attenzione specifica: tipicamente
restano disabilitate a livello di reparto e vengono concesse solo
puntualmente come override a singoli operatori.

Al salvataggio viene mostrato esplicitamente il numero di operatori
che subiranno l'effetto della modifica (es. "Impatta 5 operatori"),
cosi' l'amministratore conferma consapevolmente una variazione che
ridistribuisce permessi a piu' persone.

### 8.2 Configurazione utente

La schermata di configurazione di un singolo operatore mostra sia cio'
che **eredita** dal reparto sia cio' che il reparto ha modificato
specificamente per lui.

L'intestazione riporta nome dell'utente, reparto di appartenenza e
l'emittente fiscale su cui puo' operare (es. "ACME S.r.l."). Se non ne ha
nessuno, l'assenza va mostrata come **configurazione mancante**, non come
"nessun limite": senza riga l'operatore non vede nessun emittente (§4.9).

La prima sezione e' la matrice **Aree x Livello**, identica per forma
a quella di reparto, ma con una distinzione visiva tra livello
ereditato e livello forzato da override. Ogni riga ha un pulsante
"override" che, attivato, consente di alzare o abbassare il livello
solo per quell'utente.

La sezione **Eccezioni oggetto** (opzionale) elenca gli override
individuali su singoli model. E' la forma di controllo piu' fine:
puo' lasciare un operatore con `TUTTO` sull'area Anagrafiche ma
riportarlo a `LETTURA` solo sul model `clienti`. Questa lista resta
vuota di default e cresce solo per casi giustificati.

La sezione **Azioni** ricalca la stessa logica: mostra le azioni
abilitate dal profilo del reparto e consente all'amministratore di
forzare eccezioni puntuali con pulsante "override" e motivo
descrittivo (obbligatorio per tracciabilita' audit).

---

## 9. Diagrammi ER

Il modello dati e' suddiviso in tre diagrammi per leggibilita'.

### 9.1 Profilo reparto — ereditarieta'

Il cuore del sistema: ogni reparto (`unita_organizzative`) ha un profilo
che definisce il livello di accesso per area e le azioni di processo abilitate.
Tutti gli operatori del reparto ereditano questo profilo automaticamente.

```mermaid
erDiagram
    unita_organizzative {
        int id PK
        varchar codice
        varchar descrizione
    }

    aree_funzionali {
        int id PK
        varchar codice
        varchar schema_db
    }

    azioni_processo {
        int id PK
        int area_id FK
        varchar permission_codename
        boolean pericolosa
    }

    profili_accesso {
        int id PK
        enum tipo "REPARTO|PORTALE|AD_HOC|SUPER_ADMIN"
        varchar codice UK
        varchar descrizione
        boolean attivo
    }

    profili_accesso_bindings {
        int id PK
        int profilo_accesso_id FK
        int unita_organizzativa_id FK "se tipo=REPARTO"
        enum ruolo_applicativo "se tipo=PORTALE"
        bigint identita_digitale_id FK "se tipo=AD_HOC"
        boolean attivo
    }

    profili_accesso_aree {
        int id PK
        int profilo_accesso_id FK
        int area_id FK
        enum livello
    }

    profili_accesso_azioni {
        int id PK
        int profilo_accesso_id FK
        int azione_id FK
        boolean abilitata
    }

    profili_accesso ||--o{ profili_accesso_bindings : "bind a UO/ruolo/identita"
    profili_accesso ||--o{ profili_accesso_aree : "livello per area"
    profili_accesso ||--o{ profili_accesso_azioni : "azioni abilitate"
    unita_organizzative ||--o{ profili_accesso_bindings : "profilo REPARTO"
    aree_funzionali ||--o{ profili_accesso_aree : "livello per area"
    azioni_processo ||--o{ profili_accesso_azioni : "abilitazione"
    aree_funzionali ||--o{ azioni_processo : "contiene"
```

### 9.2 Catena identita' e profilo di accesso

`auth_user` e' collegato al resto del modello tramite il bridge **generico**
`identita_digitali`: un `auth_user` puo' avere N identita attive, una per
`ruolo_applicativo`. Ogni identita si aggancia a un `soggetti_ruoli` (dipendente,
cliente, fornitore, shop customer). Il profilo di accesso si ottiene tramite
`profili_accesso_bindings`, che ammette tre modalita' di aggancio: diretta
all'identita (AD_HOC), per ruolo applicativo (preset portale/shop), per unita'
organizzativa (ereditarieta' reparto per operatori).

Il bridge non ha alternative: `risorse_umane_auth_user`, la tabella che teneva il
ponte "solo dipendenti", **non esiste in nessuna forma**. Tutti i lettori passano da
`identita_digitali` (`ruolo_applicativo = 'OPERATORE'` per gli operatori interni).

```mermaid
erDiagram
    auth_user {
        int id PK
        varchar username
        varchar email
        boolean is_superuser
        boolean is_active
    }

    identita_digitali {
        bigint id PK
        bigint soggetto_ruolo_id FK
        int auth_user_id FK
        enum ruolo_applicativo
        boolean attivo
        date valido_dal
        date valido_al
    }

    soggetti_ruoli {
        bigint id PK
        uuid soggetto_id FK
        int tipo_ruolo_id FK
    }

    risorse_umane {
        bigint id PK
        bigint soggetto_ruolo_id FK
        int qualifica_id FK
        int unita_organizzativa_id FK
    }

    unita_organizzative {
        int id PK
        varchar codice
    }

    profili_accesso {
        int id PK
        enum tipo
        varchar codice
    }

    profili_accesso_bindings {
        bigint id PK
        int profilo_accesso_id FK
        int unita_organizzativa_id FK
        bigint identita_digitale_id FK
        enum ruolo_applicativo
    }

    user_override_aree {
        bigint id PK
        int auth_user_id FK
        int area_id FK
        enum livello
        date valido_dal
        date valido_al
    }

    user_override_oggetti {
        bigint id PK
        int auth_user_id FK
        varchar app_label
        varchar model_name
        enum livello
    }

    user_override_azioni {
        bigint id PK
        int auth_user_id FK
        int azione_id FK
        boolean abilitata
    }

    auth_user ||--o{ identita_digitali : "ha N vesti"
    soggetti_ruoli ||--o{ identita_digitali : "veste su SR"
    soggetti_ruoli ||--o| risorse_umane : "se ruolo RIS_UMANA"
    risorse_umane }o--|| unita_organizzative : "appartiene a"

    profili_accesso ||--o{ profili_accesso_bindings : "assegnato da"
    identita_digitali ||--o{ profili_accesso_bindings : "binding AD_HOC"
    unita_organizzative ||--o{ profili_accesso_bindings : "binding reparto"

    auth_user ||--o{ user_override_aree : "override area"
    auth_user ||--o{ user_override_oggetti : "override oggetto"
    auth_user ||--o{ user_override_azioni : "override azione"
```

> **Lettura.** Per un operatore: `auth_user` → `identita_digitali(OPERATORE)`
> → `soggetti_ruoli(RIS_UMANA)` → `risorse_umane` → `unita_organizzative` →
> `profili_accesso_bindings(per UO)` → profilo reparto (diagramma 9.1). Se
> esistono override individuali sull'`auth_user`, hanno priorita' massima.
>
> Per un cliente portale: `auth_user` → `identita_digitali(CLIENTE_PORTALE)`
> → `profili_accesso_bindings(per ruolo_applicativo=CLIENTE_PORTALE)` →
> profilo preset `CLIENTE_PORTALE`. Nessuna catena verso `risorse_umane` ne'
> `unita_organizzative`: il portale non ha reparto.
>
> Per SUPER_ADMIN: `auth_user` → `identita_digitali(OPERATORE)` →
> `profili_accesso_bindings(AD_HOC, identita_digitale_id=X, profilo=9100)`.
> La presenza di questo binding scatena il bypass totale nel resolver
> (cfr. §6.1, helper `script.fn_is_super_admin`).

### 9.3 Ambito emittente fiscale e override model

Due meccanismi ortogonali: la whitelist emittenti fiscali limita
l'**ambito operativo** dell'utente, mentre `area_model_overrides`
riassegna un model a un'area diversa dal suo schema DB.

```mermaid
erDiagram
    auth_user {
        int id PK
        varchar username
    }

    user_emittenti_fiscali {
        bigint id PK
        int auth_user_id FK
        bigint emittente_fiscale_id FK
    }

    emittenti_fiscali {
        bigint id PK
        bigint soggetto_ruolo_id FK
    }

    aree_funzionali {
        int id PK
        varchar codice
        varchar schema_db
    }

    area_model_overrides {
        int id PK
        varchar app_label
        varchar model_name
        int area_id FK
    }

    auth_user ||--o{ user_emittenti_fiscali : "scope"
    emittenti_fiscali ||--o{ user_emittenti_fiscali : "limita a"
    aree_funzionali ||--o{ area_model_overrides : "riassegna"
```

> **Nota:** `user_emittenti_fiscali` e' l'assegnazione **1-a-1** fra operatore ed
> emittente (al massimo una riga per utente) ed e' **fail-closed** (§4.9): senza
> righe non si vede nessun emittente, e la riga mancante e' un errore di
> configurazione. Chi ne e' privo si conta in `dbops.vw_operatori_senza_emittente`,
> che **deve restare a zero righe**.
> `area_model_overrides` e' usata raramente, solo quando un model
> deve appartenere a un'area diversa dal suo schema.

---

## 10. Riepilogo architettura

**Modello capability:**

* **Aree funzionali** → `config.aree_funzionali` (schema DB = area, automatico)
* **Profili di accesso** → `config.profili_accesso` (tipo REPARTO / PORTALE / AD_HOC), contenitore capability generalizzato
* **Livello accesso area** → `config.profili_accesso_aree` (TUTTO / LETTURA / BLOCCATO per profilo)
* **Azioni di processo** → `config.azioni_processo` + `config.profili_accesso_azioni` (abilitate per profilo)
* **Assegnazione profilo** → `config.profili_accesso_bindings` con tre modalita' (AD_HOC / ruolo_applicativo / unita_organizzativa), priorita' AD_HOC > ruolo_applicativo > reparto

**Modello identita:**

* **Bridge identita** → `anagrafiche.identita_digitali` (1 auth_user ↔ N vesti attive), con `ruolo_applicativo` per ogni identita
* **Bypass SUPER_ADMIN** → binding AD_HOC al profilo `SUPER_ADMIN` (id 9100) + helper `script.fn_is_super_admin`; il resolver ritorna TUTTO su ogni area/azione
* **Propagazione identita** → `JwtAuditAuthentication` + JWT claim `identita_id`; popola GUC `app.current_identita_id`, `app.ruolo_applicativo`, `app.soggetto_ruolo_id` (tripla tutto-o-niente)

**Override individuali (invariati):**

* **Override utente area** → `config.user_override_aree`, sovrascrive profilo con validita' temporale
* **Override utente oggetto** → `config.user_override_oggetti`, sovrascrive area per singolo model
* **Override utente azione** → `config.user_override_azioni`, sovrascrive profilo per singola azione

**Scope dati:**

* **Ambito operatore** → `config.user_emittenti_fiscali` + scope policy `EF_WHITELIST`, **fail-closed**: senza righe non si vede nessun emittente
* **Ambito portale/shop** → `config.scope_policy` + policy `BA_OWNERSHIP` / `CLIENTE_OWNERSHIP` / `FORNITORE_OWNERSHIP` (RLS nativa PostgreSQL, no filtro manuale lato BE)

**Enforcement:**

* **Permission class API** → `ZeroERPPermission` (admin) / `PortaleBasePermission` (portale) / `ShopPermission` (shop), una per namespace
* **Ambito queryset operatore** → `EmittenteFiscaleScopeMixin` (mixin su ViewSet, applica EF_WHITELIST)
* **Defense-in-depth** → trigger DB + RLS policy + scope functions `script.fn_scope_*`; fail-closed su tripla GUC incoerente

---

## 11. Nota sulla scelta architetturale: ereditarieta'

Il sistema adotta il modello a **ereditarieta'** per i profili reparto.
Questa scelta:

**Semplifica la manutenzione:** un cambio di policy aziendale si applica
modificando il profilo del reparto, senza toccare i singoli utenti.

**Richiede attenzione:** modificare il profilo di un reparto ha impatto
immediato su tutti gli operatori associati. L'interfaccia deve sempre
mostrare il numero di operatori impattati prima di confermare modifiche.

**Preserva la flessibilita':** le eccezioni individuali (override) hanno
sempre priorita' sul profilo ereditato, permettendo personalizzazioni
puntuali senza compromettere il modello generale.

Questo pattern e' analogo al fallback per contesto gia' adottato nella
gestione contatti (default soggetto -> ruolo -> utility) e risulta
coerente con la filosofia di Zero ERP.

---

## 12. Evoluzioni future

- **Row-Level Security (RLS):** attiva per lo **scope emittente degli operatori** su
  fatture, scadenze, lotti, ordini, preventivi, contratti, offerte, documenti
  generati, pratiche e billing account. Per **portale e shop** le policy sono
  scritte ma **non ancora attive**: si accendono insieme alle rispettive API di
  dominio.
- **Permessi sotto-oggetti:** i model sono flat. La gerarchia padre/figlio (es.
  "TUTTO su cliente, BLOCCATO sugli indirizzi del cliente") e' un'evoluzione
  prevista, con UX ad albero, non ancora disponibile.
- **Ambito per unita' organizzativa sui dati:** limitare la visibilita' delle righe
  per reparto.
- **Workflow permissions:** stati avanzati (es. transizione BOZZA → EMESSA) come
  azioni di processo.
- **Audit trail permessi:** log storico delle modifiche ai profili e agli override.
- **Dashboard permessi operatore:** la vista riepilogativa "cosa puo' fare questo
  utente" e' coperta dall'endpoint dei permessi effettivi (§13); l'UX admin
  gerarchica arrivera' con i sotto-oggetti.

---

## 13. Diagnostica: cosa puo' fare questo utente

### 13.1 L'endpoint dei permessi effettivi

`/api/v1/core/users/{id}/permessi-effettivi/` restituisce la risoluzione completa per
l'utente indicato:

* `aree` — per ogni area funzionale attiva: `livello`, `azioni_consentite`,
  `has_profilo_reparto`;
* `modelli` — per ogni area, i model registrati in `config.area_model_overrides` con
  il livello oggetto risolto (`fn_resolve_livello_oggetto`: override esplicito o
  fallback sull'area).

Serve quando un operatore risulta `BLOCCATO` su un model specifico e bisogna
distinguere la causa: override oggetto, profilo dell'area, o configurazione assente.

### 13.2 L'audit degli override

`/permessi-audit/` traccia la timeline degli override. La storia vive nelle tabelle
dello schema `storico`, fra cui `storico.user_override_oggetti`.

### 13.3 Due difese che non si vedono a schermo

Spiegano rifiuti altrimenti incomprensibili, e vale la pena conoscerle prima di
diagnosticarli:

* **Anti-lockout sull'ultimo `SUPER_ADMIN`.** Il trigger
  `trgfn_profili_accesso_bindings_guard_ultimo_super_admin` impedisce di disattivare
  o eliminare l'ultimo binding `SUPER_ADMIN` attivo — errore
  `E_PROFILO_ULTIMO_SUPER_ADMIN`. Il sistema non resta senza amministratori
  raggiungibili.
* **Piu' vesti, un solo accesso.** Un `auth_user` puo' avere insieme un'identita'
  `OPERATORE` e una `CLIENTE_PORTALE` attive (es. un dipendente che e' anche cliente
  B2B della sua azienda). Il login resta possibile finche' **almeno una** veste e'
  utilizzabile: la veste disattivata viene bloccata dalle policy, senza spegnere
  l'account.

---

{% include-markdown "signature-core.md" %}
