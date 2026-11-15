# Guida — Configurazione, Personalizzazione e Responsività delle Liste

> **Ultimo aggiornamento**: 12 novembre 2026
>
> **Destinatari**: amministratori del sistema (SUPER_ADMIN), tenant admin
> con azioni `ui_preset_manage` / `ui_permesso_manage`, operatori finali
> che personalizzano la propria vista.
>
> **Vedi anche** — schemi DB:
>
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — registro liste configurabili
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — catalogo colonne per ogni lista
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — preset di colonne (sistema/ruolo/emittente)
> * [ui.lista_preset_colonna](/dbzero/ui/tabelle/lista_preset_colonna) — composizione di un preset
> * [ui.lista_colonna_permesso](/dbzero/ui/tabelle/lista_colonna_permesso) — permessi colonna per profilo accesso
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — preferenza personale dell'operatore
>
> **Vedi anche** — API e documentazione tecnica:
>
> * [API runtime liste](/backend/ui/manual/api_ui_liste) — endpoint che alimentano le liste lato operatore
> * [API admin personalizzazioni](/backend/ui/manual/api_ui_admin_personalizzazioni) — endpoint admin (preset, permessi, definizioni, colonne)

---

## 1. Cosa sono le personalizzazioni liste

In Zero ERP le liste (clienti, fornitori, articoli, contratti, ecc.)
non sono fisse. Ogni operatore ha esigenze diverse:

* l'**amministrativo** vuole vedere ragione sociale, partita IVA, codice fiscale, condizioni di pagamento
* il **commerciale** vuole vedere ragione sociale, contatto, ultima offerta, scadenza contratto
* il **tecnico** vuole vedere indirizzo, utility attive, stato impianto

Per questo Zero ERP permette di:

* **definire una volta** quali colonne sono disponibili per ogni lista
* **proporre default sensati** per ruolo aziendale o per emittente fiscale
* **lasciare libertà** all'operatore di personalizzare la propria vista (ordine colonne, larghezza, visibilità)

Tutto questo senza richiedere modifiche al codice o nuove release.

**Cosa troverai in questa guida:**

* I tre livelli del modello: catalogo, preset, preferenza utente
* Come l'admin tecnico registra una nuova lista o aggiunge una colonna
* Come l'admin operativo prepara preset e permessi colonna
* Come l'operatore finale personalizza la propria vista
* Come le liste si **adattano da sole allo spazio** (responsività) e chi decide quale colonna scende
* Permessi e visibilità: chi vede cosa
* Esempi pratici end-to-end

---

## 2. Le entità in gioco (linguaggio operativo)

Tre livelli, ognuno con un proprietario diverso:

| Livello | Entità | Chi lo gestisce | Aggiornamento |
| --- | --- | --- | --- |
| **Catalogo (sistema)** | `lista_definizione`, `lista_colonna` | SUPER_ADMIN tecnico | Raro — quando si aggiunge una nuova lista o un nuovo campo |
| **Preset (azienda)** | `lista_preset`, `lista_preset_colonna`, `lista_colonna_permesso` | Tenant admin | Occasionale — quando cambiano le esigenze di un ruolo o di un emittente |
| **Preferenza utente** | `lista_preferenza_utente` | Operatore finale | Quotidiano — ogni volta che l'operatore personalizza la propria vista |

### 2.1 Definizione lista (`lista_definizione`)

È la registrazione di una lista nel sistema. Identificata da un **codice
stabile** del tipo `<schema>.<entità>` (es. `anagrafiche.clienti`,
`vendite.contratti`, `catalogo.articoli`).

Contiene:

* il codice (chiave logica, non cambia tra ambienti)
* la descrizione visibile
* lo schema dati (es. `anagrafiche`)
* la **vista SQL** dalla quale la lista legge i dati (es. `vw_clienti_lista`)
* lo stato attivo/disattivo
* il **bollino «multi-emittente»** — dice se quella lista è stata collaudata per
  mostrare righe di **più emittenti insieme**. Nasce spento e non si accende
  dall'interfaccia: vedi §11.7

### 2.2 Colonna (`lista_colonna`)

Per ogni lista, l'insieme delle **colonne disponibili**. Ogni colonna ha:

* un codice tecnico (univoco nella lista)
* un'etichetta visibile (con chiave i18n opzionale per multilingua)
* il **tipo di colonna**:
  * `identificatore` → sempre visibile, non nascondibile (es. ragione sociale del cliente)
  * `informazione` → personalizzabile liberamente dall'operatore
  * `azione` → pulsanti/icone (modifica, dettaglio); non esportabili per definizione
* il **tipo di dato** (testo, numero, data, booleano, enumerato)
* il campo sorgente nella vista SQL (può essere vuoto per colonne
  composte calcolate lato frontend)
* parametri di layout (ordine, larghezza, **priorità di ritiro**,
  allineamento, gruppo) — la *priorità* governa la responsività: decide
  quale colonna scende per prima quando lo spazio si stringe (vedi §7)
* flag di comportamento (filtrabile, ordinabile, esportabile, ricercabile,
  sensibile)

### 2.3 Preset (`lista_preset` + `lista_preset_colonna`)

Una **configurazione preconfezionata** di colonne pensata per un
contesto. Tre ambiti possibili:

| Ambito | Quando usarlo | Esempio |
| --- | --- | --- |
| **Sistema** | Default applicato a tutti se nessun altro preset si applica | "Default sistema" — le 5 colonne base |
| **Ruolo** | Default per chi ha un certo profilo accesso | "Default amministrativo" — colonne fiscali in evidenza |
| **Emittente fiscale** | Default per gli operatori di una specifica azienda | "Default Acme S.p.A." — include codice cliente Acme |

Per ogni preset, la **composizione** definisce: quali colonne includere,
in che ordine, con quale larghezza, quali sono visibili di default e
quali sono "fissate" (sticky a sinistra, non scrollano).

Un solo preset può essere `is_default=true` per ogni combinazione
(lista, ambito, profilo, emittente). Il sistema lo applica
automaticamente al primo accesso dell'operatore alla lista.

### 2.4 Permesso colonna (`lista_colonna_permesso`)

Per ogni colonna di una lista, è possibile definire un **livello di
accesso** specifico per profilo accesso:

* `TUTTO` → la colonna è visibile e ordinabile come da preset
* `LETTURA` → la colonna è visibile ma non personalizzabile
* `BLOCCATO` → la colonna è completamente nascosta (non appare nemmeno nella modale di personalizzazione)

Esempio: per il profilo "Tecnico assistenza" la colonna `partita_iva`
del cliente può essere `BLOCCATO` (informazione fiscale non rilevante
per il loro lavoro).

### 2.5 Preferenza utente (`lista_preferenza_utente`)

La **personalizzazione che l'operatore salva** dalla modale "Personalizza
colonne". Memorizza:

* l'ordine delle colonne come l'ha disposto
* la visibilità (quali colonne nascoste rispetto al preset)
* la larghezza di ogni colonna
* le colonne "fissate"
* il riferimento al preset di partenza (per il badge "preset aggiornato"
  quando l'admin modifica il preset di base)

Una sola preferenza per coppia (utente, lista). Il salvataggio
sovrascrive la precedente.

---

## 3. La cascata di risoluzione

Quando l'operatore apre una lista, il sistema risolve in ordine:

1. **C'è una preferenza personale** salvata? → la usa
2. Altrimenti, **c'è un preset di default per il suo emittente fiscale**? → lo usa
3. Altrimenti, **c'è un preset di default per il suo ruolo**? → lo usa
4. Altrimenti, **c'è un preset di default di sistema**? → lo usa
5. Altrimenti, **catalogo grezzo**: tutte le colonne `informazione` visibili nell'ordine di catalogo

A ogni livello vengono applicati i **permessi colonna**: le colonne
`BLOCCATO` per il profilo dell'operatore vengono filtrate via, le
`LETTURA` perdono la possibilità di essere personalizzate.

---

## 4. Pagina admin operativa — `/config/personalizzazioni-liste`

Accessibile a **tenant admin** con azione di processo `ui_preset_manage`
oppure `ui_permesso_manage`, e a SUPER_ADMIN.

Header: **Select "Lista corrente"** — sceglie su quale lista
operare. Tutti i tab sotto si aggiornano di conseguenza.

### 4.1 Tab "Preset"

Lista dei preset configurati per la lista corrente. Per ogni preset si
vedono codice, descrizione, ambito (sistema/ruolo/emittente), riferimento
(profilo o emittente specifico), numero colonne configurate, flag
default, stato attivo.

**Operazioni disponibili**:

* **Nuovo preset**: drawer con codice, descrizione, ambito, riferimenti
  condizionali (profilo se ambito=ruolo, emittente se ambito=emittente
  fiscale), pagina dimensione default, flag is_default e attivo.
* **Modifica preset**: aggiorna i campi mutabili. L'ambito e i
  riferimenti sono immutabili dopo la creazione (per cambiarli si
  crea un nuovo preset).
* **Gestisci composizione**: sub-drawer per definire quali colonne
  includere, in che ordine, con quale larghezza, quali visibili e
  quali fissate. Sostituzione atomica (replace completo).
* **Elimina preset**: le preferenze utente che lo referenziavano
  perdono il riferimento ma sopravvivono (l'operatore lavorerà direttamente sul catalogo grezzo finché non sceglie un altro preset).

### 4.2 Tab "Permessi colonne"

Lista dei permessi colonna configurati per la lista corrente. Ogni
riga è una tripla (colonna × profilo accesso × livello accesso).

**Operazioni disponibili**:

* **Nuovo permesso / Modifica**: UPSERT su (colonna, profilo). Se la
  coppia esiste già, viene aggiornato il livello. Operazione idempotente.
* **Elimina permesso**: rimuove il vincolo, la colonna torna al comportamento di default (`TUTTO`).

**Regola pratica**: aggiungere permessi solo quando servono restrizioni.
L'assenza di un permesso = comportamento standard (la colonna è
disponibile a tutti). I permessi sono sempre **restrittivi**, mai
permissivi.

---

## 5. Pagina admin tecnica — `/amm-software/personalizzazioni-liste-tecniche`

Accessibile **solo a SUPER_ADMIN**. È la pagina di "amministrazione del
catalogo": qui si registrano nuove liste e si gestisce il catalogo
colonne. Operazione rara, tipicamente legata a un'evoluzione del
prodotto o all'aggiunta di una nuova area funzionale.

Due tab indipendenti.

### 5.1 Tab "Definizioni"

Registro completo delle liste configurabili nel sistema (incluse le
disattivate).

**Operazioni disponibili**:

* **Nuova definizione**: form con codice (`<schema>.<entità>`),
  descrizione, schema dati, **vista SQL** (nome di una view PostgreSQL
  che alimenta la lista), note, flag attivo.
* **Modifica definizione**: tutti i campi sono mutabili **tranne uno** — il
  bollino «multi-emittente», che il database rifiuta di far scrivere
  dall'applicazione (§11.7). Cambiare la vista SQL su una lista già in uso può
  rendere stale i campi sorgente delle colonne (la nuova vista deve esporre gli
  stessi attributi).
* **Disattiva (soft-disable)**: porta `attivo=false`. La lista
  scompare dal catalogo runtime ma le configurazioni esistenti
  (preset, colonne, preferenze) restano in DB.
* **Elimina definizione**: bloccato dal sistema se ci sono
  colonne, preset o preferenze utente associate. In quel caso, l'unica
  via è il **soft-disable**.

#### 5.1.1 Workflow "lista in fase di sviluppo"

Quando si registra una lista nuova la cui vista SQL non è ancora stata
creata in database (changeset Liquibase non ancora atterrato):

1. Crea il record con `attivo=false` (oppure lascia vuoto il campo "vista SQL")
2. Il sistema **non valida** l'esistenza della view in pg_catalog (il trigger di guard salta sulle liste disattive o senza vista)
3. Quando il team DB rilascia la view, attiva la lista (`attivo=true`) e la guard verifica l'esistenza della view

Questo permette di registrare la struttura senza dover sincronizzare con il deploy DDL.

### 5.2 Tab "Catalogo colonne"

Master-detail su `Lista corrente` (Select header). Mostra TUTTE le
colonne registrate per quella lista, attive e disattivate.

**Operazioni disponibili**:

* **Nuova colonna**: drawer con 3 sotto-tab:
  * **Generale**: codice, etichetta visibile, etichetta estesa (tooltip), chiave i18n (per traduzioni), tipo colonna, tipo dato, campo sorgente
  * **Comportamento**: filtrabile, ordinabile, esportabile, ricercabile full-text, sensibile, attivo
  * **Layout**: ordine default, larghezza default (px), allineamento (left/right/center), formato (tabella sotto), gruppo, ordine gruppo
* **Modifica colonna**: tutti i campi sono mutabili. Il `lista_id` è
  immutabile (per "spostare" una colonna da una lista all'altra,
  cancellala e ricreala).
* **Disattiva (soft-disable)**: imposta `attivo=false`. Colonna
  invisibile in runtime ma le preferenze utente che la referenziavano
  restano (verranno ignorate gracefully al primo render).
* **Elimina colonna**: bloccato dal sistema se ci sono preferenze
  utente che la referenziano (prevenzione di configurazioni stale
  silenziose). Il messaggio indica il numero di preferenze coinvolte;
  l'alternativa raccomandata è disattivare con `attivo=false`.

#### 5.2.0 I formati di resa (`formato`)

Il valore di `formato` sceglie il formatter con cui `<ListaConfigurabile>` rende
la cella (`CellaConfigurabile`), a meno che la view non fornisca uno slot
`cell-{codice}` suo:

| `formato` | Resa | Note |
|---|---|---|
| `date_short` | data nel locale dell'utente | per le colonne `tipo_dato = date` |
| `datetime`, `datetime_short` | data e ora | |
| `currency_eur` | importo in euro | |
| `number` | numero nel locale | |
| `percent_2` | numero a due decimali + ` %` | |
| `yesno` | etichetta **Sì / No** (building block `SiNoTag`); `null` resta vuoto | ⭐ **è la resa di un booleano in lista**: una colonna booleana è una riga di `ui.lista_colonna` con questo formato, non uno slot riscritto nella view. Un `tipo_dato = boolean` **senza** formato prende la stessa resa, così un booleano dimenticato non esce mai come `true`/`false` grezzi |
| *(vuoto)* | il valore com'è | |

#### 5.2.1 Vincoli automatici applicati dal sistema

* Le colonne di tipo `azione` non possono essere esportabili (vincolo
  CHECK del database). Se selezioni `azione`, il toggle "Esportabile"
  viene forzato a OFF e disabilitato.
* Le colonne con `campo_sorgente` valorizzato vengono validate contro
  la vista SQL della lista padre: il trigger blocca l'inserimento se
  l'attributo non esiste in `pg_catalog`. Le colonne con
  `campo_sorgente=NULL` (composite calcolate lato frontend) non sono
  validate.

### 5.3 Etichette e multilingua

Ogni colonna può avere due etichette:

* **etichetta** — testo letterale italiano, obbligatorio (fallback)
* **etichetta_i18n_key** — chiave i18n opzionale (es. `clienti.col_ragione_sociale`)

Il frontend risolve in cascata: `t(etichetta_i18n_key) || etichetta || codice`.
Se la chiave i18n esiste nei locales, vince; altrimenti si usa
l'etichetta letterale; altrimenti il codice tecnico (caso degenere).

---

## 6. Cosa fa l'operatore finale

L'operatore vede ogni lista personalizzabile con due affordance nella
toolbar:

* **Pulsante "Personalizza colonne"** — apre la modale di
  configurazione. Permette di:
  * mostrare/nascondere colonne (toggle, disabilitato sulle
    `identificatore` e `azione`)
  * riordinare con frecce ▲▼
  * cambiare la larghezza inline
  * fissare colonne a sinistra
  * resettare alla configurazione del preset di base
* **Badge "preset aggiornato"** — appare quando l'admin modifica il
  preset da cui partiva la preferenza dell'utente. CTA "Vedi novità"
  evidenzia le colonne aggiunte/modificate dopo il salvataggio
  dell'utente. Funzionalità prevista, in roadmap (vedi `_def.md` DEF-2).

### 6.1 Cosa NON può fare l'operatore

* Modificare i preset di sistema/ruolo/emittente (sono di responsabilità
  dell'admin)
* Vedere colonne che hanno permesso `BLOCCATO` per il suo profilo
  accesso (sono filtrate prima di arrivare al frontend)
* Personalizzare colonne con permesso `LETTURA` (vede il valore ma
  non può nascondere/riordinare)
* Esportare colonne `azione` o colonne marcate `esportabile=false`
  (anche se le ha rese visibili)

---

## 7. Liste responsive — adattamento automatico allo spazio

Una lista con molte colonne (i contratti ne hanno una dozzina) non sempre
entra nello schermo: basta aprire la sidebar di navigazione, o usare un
portatile o un tablet, e lo spazio si stringe. La vecchia soluzione era la
**barra di scorrimento orizzontale** — scomoda: per leggere lo stato di un
contratto dovevi trascinare la lista di lato.

Oggi le liste configurabili si **adattano da sole** allo spazio disponibile,
in tempo reale. Quando lo spazio non basta non compare lo scroll: la lista si
**compatta**, seguendo un ordine di priorità ben preciso.

### 7.1 I tre gradini di compattazione

Il sistema cerca di tenere visibili più dati possibile, agendo per gradini:

1. **Spazio sufficiente** → tutto normale: colonne affiancate, pulsanti azione
   (modifica, PDF, gestisci righe…) in fila.
2. **Spazio stretto** → i **pulsanti azione si raccolgono in un menù "⋮"**
   (kebab): un piccolo menù a tendina al posto di 3-4 iconcine. Recupera
   spazio **senza nascondere alcun dato**. È la prima mossa, perché un click
   in più sulle azioni dà meno fastidio di una colonna che sparisce.
3. **Spazio ancora insufficiente** → le **colonne meno importanti scendono**
   in una riga di dettaglio espandibile (la freccetta "›" a inizio riga).
   Nessun dato è perso: aprendo la freccetta vedi le colonne ritirate, con la
   stessa formattazione (un Tag di stato resta un Tag colorato).

Tutto è fluido: allargando di nuovo la finestra — o richiudendo la sidebar —
le colonne **ritornano** al loro posto.

### 7.2 Chi decide quale colonna scende? La priorità

Quando si arriva al terzo gradino, **quale** colonna scende per prima non è
casuale: lo decide un valore chiamato **priorità**, impostato per ogni colonna
nel catalogo (è il fratello di "ordine" e "larghezza" che già conosci dal §2.2).

Regola semplice: **priorità più bassa = scende per prima**. A parità di
priorità, scende prima la colonna più a destra.

Esempio sulla lista contratti — l'ordine con cui le colonne si ritirano man
mano che lo spazio cala:

| Ordine di ritiro | Colonna | Priorità |
| --- | --- | --- |
| 1ª a scendere | Data | 25 (bassa) |
| 2ª | Categoria cliente | 30 |
| 3ª | Codice account | 40 |
| poi… | Listino, Ambito, Valido dal/al, Utility, Id. fiscale | 45–75 |
| (quasi mai) | Stato | 90 (alta) |
| **mai** | Numero, Cliente, Azioni | — (identificatore / azione) |

Così le informazioni che servono sempre (numero, cliente, stato) restano
visibili fino all'ultimo, mentre quelle accessorie (data, categoria) scendono
per prime. Le colonne **identificatore** e **azione** (vedi §2.2) non scendono
**mai**: una lista contratti senza il numero, o senza i pulsanti, sarebbe
inutile.

### 7.3 Come cambiare l'ordine di ritiro

La priorità è un dato di catalogo, quindi si regola come gli altri attributi
della colonna (oggi via seed/changeset DB; in prospettiva dal drawer "Colonna"
della pagina tecnica, tab Layout — §5.2). Se vuoi che una colonna scenda prima
o dopo, le dai una priorità più bassa o più alta. Non serve toccare codice né
fare una release.

> **Importante**: la priorità è una **scelta di progetto** della lista, uguale
> per tutti gli operatori — non una preferenza personale. La personalizzazione
> individuale del §6 (quali colonne mostrare, in che ordine) agisce **prima**:
> il ritiro dinamico lavora poi sull'insieme di colonne effettivamente
> visibili per quell'operatore.

### 7.4 Il regalo per i dispositivi piccoli

Lo stesso meccanismo sistema "gratis" le liste su **tablet e mobile**: lì lo
spazio è poco per definizione, quindi le colonne si compattano e si raccolgono
nell'espansione in automatico. Non c'è un layout mobile separato da costruire e
mantenere: la lista è **una sola** e si adatta da sé.

### 7.5 Per chi sviluppa (in breve)

Il comportamento vive in **building block riusabili**: una nuova lista lo
eredita senza scrivere logica responsive.

* **`<ListaConfigurabile>`** — il componente che disegna la lista a partire
  dalla configurazione risolta dal backend; ospita il ritiro dinamico.
* **`useResponsiveColumns`** — il "cervello": misura lo spazio **reale** del
  contenitore (non la larghezza della finestra — così reagisce anche
  all'apertura della sidebar, che la finestra non vede) e decide compattazione
  e ritiro applicando le priorità di catalogo.
* **`useListaConfigurabilePage`** — lo "scheletro" della pagina lista (ricerca,
  paginazione, export, azioni di toolbar): il componente di dominio resta
  minimale, con solo i propri filtri e azioni di riga.

Dettagli tecnici e regole di stile: [standard frontend](/dev/frontend/frontend-standards)
(sezione "Ritiro dinamico colonne — `useResponsiveColumns`") e i cataloghi
building block [frontend](/dev/frontend/catalogo-building-block-frontend) e
[backend](/dev/backend/catalogo-building-block-backend).

---

## 8. Esempio end-to-end — Lista Clienti

Scenario: l'azienda ha un emittente fiscale "Acme S.p.A." e tre
profili accesso (Amministrativo, Commerciale, Tecnico). Vogliamo che:

* di default tutti vedano una vista standard
* l'amministrativo veda partita IVA in evidenza
* il tecnico non possa nemmeno vedere la partita IVA
* la lista usa la view SQL `vw_clienti_lista`

### Step 1 — SUPER_ADMIN registra la lista (una volta sola)

Pagina `/amm-software/personalizzazioni-liste-tecniche` → tab "Definizioni" → **Nuova**:

* Codice: `anagrafiche.clienti`
* Descrizione: "Clienti"
* Schema dati: `anagrafiche`
* Vista SQL: `vw_clienti_lista`
* Attivo: ✓

Già fatto via seed CSV in fase di rilascio del prodotto. La pagina
serve solo per varianti future (es. `anagrafiche.clienti:picker` per
un selettore in form fattura).

### Step 2 — SUPER_ADMIN registra le colonne (una volta sola)

Tab "Catalogo colonne" → seleziona "Clienti" nel Select header → per
ogni colonna **Nuova**:

| Codice | Etichetta | Tipo colonna | Tipo dato | Campo sorgente | Filtrabile | Ordine |
| --- | --- | --- | --- | --- | --- | --- |
| `ragione_sociale` | Ragione sociale | identificatore | string | `ragione_sociale` | ✓ | 10 |
| `partita_iva` | Partita IVA | informazione | string | `partita_iva` | ✓ | 20 |
| `codice_fiscale` | Codice fiscale | informazione | string | `codice_fiscale` | ✓ | 30 |
| `comune` | Comune | informazione | string | `comune` | ✓ | 40 |
| `stato` | Stato | informazione | enum | `stato` | ✓ | 50 |
| `azioni` | Azioni | azione | string | (vuoto) | ✗ | 99 |

Anche questo è tipicamente seedato via CSV. La UI serve per aggiunte
ad-hoc o evoluzioni.

### Step 3 — Tenant admin crea i preset

Pagina `/config/personalizzazioni-liste` → seleziona "Clienti" → tab "Preset":

**Preset "Default sistema"**:

* Codice: `default`, Descrizione: "Vista standard"
* Ambito: sistema, is_default: ✓
* Composizione: ragione_sociale, comune, stato (le tre più universali)

**Preset "Default amministrativo"**:

* Codice: `default-admin`, Descrizione: "Vista amministrativa"
* Ambito: ruolo, profilo: "Amministrativo", is_default: ✓
* Composizione: ragione_sociale, partita_iva, codice_fiscale, stato

### Step 4 — Tenant admin imposta i permessi

Tab "Permessi colonne":

* Colonna `partita_iva` × profilo "Tecnico" → livello `BLOCCATO`
* Colonna `codice_fiscale` × profilo "Tecnico" → livello `BLOCCATO`

I tecnici non vedono nemmeno questi campi nella modale di
personalizzazione, anche se volessero.

### Step 5 — L'operatore usa la lista

Mario (profilo "Amministrativo") apre `/anagrafiche/clienti`:

* Nessuna preferenza personale → cerca preset per emittente → assente
* Cerca preset per ruolo "Amministrativo" → trova "Default amministrativo"
* Applica permessi: nessuna restrizione per Amministrativo → vede tutto
* Visualizza: ragione_sociale, partita_iva, codice_fiscale, stato

Mario decide che gli serve anche `comune` e nasconde `codice_fiscale`.
Salva. Ora ha una sua preferenza personale.

Luca (profilo "Tecnico") apre la stessa lista:

* Nessuna preferenza personale → preset di sistema "Default sistema"
* Applica permessi: `partita_iva` e `codice_fiscale` sono `BLOCCATO`
  per Tecnico → filtrate prima di arrivare al frontend
* Visualizza: ragione_sociale, comune, stato. Nella modale di
  personalizzazione le colonne bloccate **non compaiono affatto**.

---

## 9. Permessi e visibilità — chi vede cosa

| Ruolo | Pagina admin operativa | Pagina admin tecnica | Personalizzazione personale |
| --- | --- | --- | --- |
| **SUPER_ADMIN** | ✓ (bypass) | ✓ | ✓ |
| **Tenant admin** con `ui_preset_manage` | ✓ (tab Preset) | ✗ | ✓ |
| **Tenant admin** con `ui_permesso_manage` | ✓ (tab Permessi) | ✗ | ✓ |
| **Operatore standard** | ✗ | ✗ | ✓ |

Le azioni di processo `ui_preset_manage` e `ui_permesso_manage` si
abilitano dalla pagina amministrazione profili reparto. Per default
nessun profilo le ha (la decisione è del tenant: chi vuole delegare
la gestione preset a un sotto-amministratore).

Il super-admin **bypassa** sempre tutti i check permessi: vede e
modifica tutto.

---

## 10. Casi d'uso comuni

### 10.1 Aggiungere una colonna a una lista esistente

1. SUPER_ADMIN: pagina tecnica → tab "Catalogo colonne" → **Nuova**
2. Compila i 3 sotto-tab (Generale / Comportamento / Layout)
3. Se il `campo_sorgente` non esiste nella vista SQL della lista, il
   sistema rifiuta. Coordinarsi col team DB per estendere la view.
4. La colonna è subito disponibile a tutti (nessun preset la include
   per default, ma l'operatore può aggiungerla manualmente dalla modale)
5. Opzionale: aggiornare i preset di base per includerla (admin operativo)

⚠️ **Per chi sviluppa: «la colonna esce dalla vista» non basta.** Prima di promettere una colonna
si apre il repository del backend che serve quella lista: se la sua lettura elenca i nomi delle
colonne invece di prenderle tutte, la colonna non esiste per il frontend finché il backend non la
aggiunge alla sua proiezione, e su una lista con una vista nessun controllo lo segnala (cella vuota,
nessun errore). La richiesta al backend nomina file e costante, e la riga di `ui.lista_colonna`
nasce spenta (vedi [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna)).

### 10.2 Nascondere una colonna sensibile per un profilo

1. Tenant admin: pagina operativa → tab "Permessi colonne" → **Nuovo**
2. Seleziona colonna + profilo accesso + livello `BLOCCATO`
3. Salva. Effetto immediato al prossimo refresh delle liste.

### 10.3 Creare una vista preconfigurata per un ruolo

1. Tenant admin: pagina operativa → tab "Preset" → **Nuovo**
2. Compila codice, descrizione, **ambito="ruolo"**, profilo target
3. Salva il preset (testata)
4. Apri "Gestisci composizione" → seleziona le colonne, riordina,
   imposta visibilità di default → Salva
5. Marca il preset come `is_default=true`. Sarà applicato
   automaticamente al primo accesso degli operatori con quel ruolo.

### 10.4 Disattivare temporaneamente una lista

1. SUPER_ADMIN: pagina tecnica → tab "Definizioni" → modifica la lista
2. Imposta `attivo=false` → Salva
3. La lista scompare dal runtime. Preset, colonne e preferenze
   sopravvivono in DB e tornano disponibili al riattivare.

### 10.5 Riallineare una preferenza dopo modifica del preset

Quando l'admin modifica un preset di base (aggiunge una colonna,
cambia l'ordine), gli utenti che hanno una preferenza salvata da quel
preset vedranno (in roadmap, DEF-2) un badge "Preset aggiornato" con
CTA "Vedi novità" che evidenzia le colonne aggiunte. L'utente può
adottare la modifica (un click) o ignorarla.

---

## 11. Comportamenti speciali e fallback

Alcune scelte di design pensate per evitare situazioni di blocco
all'utente o configurazioni stale silenziose.

### 11.1 Combo "Utility" — le utility ammesse per il ruolo emittente

La combo "Utility" presente nei drawer (clienti, contratti, preventivi,
filtri lista) è popolata da `/api/v1/core/lookup/utilities-per-emittente/`:
mostra le utility **ammesse per il ruolo emittente fiscale** nella matrice
utility/ruoli (`config.utilities_tipi_ruolo`), le stesse per ogni operatore.
Dove il drawer lavora per un ruolo preciso (per esempio il cliente), restano
quelle ammesse anche per quel ruolo.

⚠️ I **parametri di fatturazione** che l'amministratore imposta per un
emittente e una utility (fattura minima, arrotondamento del totale) **non**
decidono quali utility compaiono: sono facoltativi, e un'utility senza
parametri dedicati usa quelli di sistema.

L'eventuale parametro `DEFAULT_UTILITY` (catena
user → group → emittente → sistema) viene risolto su questo stesso insieme.

### 11.2 Workflow "lista in fase di sviluppo"

Il trigger `trgfn_ui_lista_definizione_a10_valida_vista_sql` valida
l'esistenza della vista SQL in `pg_catalog`, ma **salta** se:

* `attivo = false`, oppure
* `vista_sql IS NULL`

Questo permette al SUPER_ADMIN di registrare una lista in modalità
"draft" prima che il team DB abbia rilasciato la view. Una volta
deployata la view, basta editare il record (impostare la vista, attivare).

### 11.3 Cancellazioni protette dal sistema

Per evitare configurazioni stale silenziose, alcune cancellazioni
sono bloccate dal database e ribattute con messaggio parlante:

* **Cancellare una `lista_definizione` con colonne, preset o preferenze utente**: bloccato (FK RESTRICT). Messaggio: "Lista in uso da N utenti / colonne / preset, disattivala con `attivo=false`". L'admin sceglie tra disabilitare la lista (mantenendo le configurazioni) o ripulire prima i riferimenti.
* **Cancellare una `lista_colonna` referenziata da preferenze utente**: bloccato applicativamente (count su JSONB `configurazione->colonne`). Messaggio: "La colonna è in uso da N preferenze utente, disattivala con `attivo=false`".

In compenso, alcune cancellazioni sono **CASCADE intenzionali**:

* Cancellare una `lista_colonna` rimuove automaticamente i record
  collegati in `lista_preset_colonna` (composizione) e in
  `lista_colonna_permesso` (permessi).
* Cancellare un `lista_preset` rimuove la composizione (`lista_preset_colonna` CASCADE) ma le preferenze utente che lo referenziavano sopravvivono con `preset_base_id = NULL` (ON DELETE SET NULL): l'operatore continua a vedere la propria configurazione personale, indipendente dal preset originario.

### 11.4 Vincolo automatico — colonne `azione` non esportabili

Il database garantisce con CHECK constraint che le colonne di tipo
`azione` (pulsanti UI) non possano essere marcate `esportabile=true`.
Il drawer UX collabora: se selezioni `tipo_colonna='azione'` il toggle
"Esportabile" viene forzato a OFF e disabilitato. Vale anche se cambi
una colonna esistente da `informazione` a `azione`: il sistema riallinea
automaticamente il flag senza sollevare errori.

### 11.5 Etichette i18n con cascata fallback

La risoluzione frontend dell'etichetta colonna è sempre **safe**:

```text
t(etichetta_i18n_key) || etichetta || codice
```

* Se `etichetta_i18n_key` è valorizzata e la chiave esiste nei locales (it/en/...) → traduzione tradotta
* Altrimenti → l'etichetta letterale italiana (campo `etichetta`)
* Altrimenti → il codice tecnico (caso degenere, "guard" per evitare colonne senza header)

Così aggiungere un locale nuovo non richiede mai un'operazione DB —
basta aggiornare i file di traduzione.

### 11.6 Identificatori e azioni — sempre visibili

Le colonne con `tipo_colonna IN ('identificatore', 'azione')` non sono
nascondibili dall'operatore nella modale di personalizzazione (toggle
disabilitato con tooltip esplicativo). Servono per coerenza: una lista
clienti senza ragione sociale è inutile, e nascondere i pulsanti
modifica rompe l'usabilità.

L'admin può comunque marcare un'`identificatore` con permesso
`BLOCCATO` per un certo profilo: in quel caso la colonna scompare
**prima** di arrivare alla modale (filtro lato backend), non viene
nascosta lato UI.

---

### 11.7 Il bollino «multi-emittente» — un'etichetta che si guadagna

> 🔵 Oggi è **spento su tutte le liste**, ed è corretto che lo sia: sotto c'è
> scritto perché.

#### Il problema, in parole semplici

Un'azienda può fatturare sotto **più intestazioni** — chiamiamole *emittenti*.
Chi ha accesso a una sola di esse vede solo le proprie righe, e va benissimo.

Il caso delicato è l'altro: **chi ha accesso a più emittenti**. Costui apre una
lista e trova, mescolate nella stessa tabella, righe che appartengono a
intestazioni diverse — senza che niente glielo dica. Due documenti con lo stesso
numero, due clienti con lo stesso nome, un totale che somma cose che non si
sommano.

Non è un errore del programma: la lista sta mostrando esattamente ciò che
l'utente ha il diritto di vedere. È un errore di **lettura**, ed è il tipo
peggiore, perché chi lo commette non ha modo di accorgersene.

#### La cura, e perché non è «aggiungere una colonna»

La cura è ovvia: **mostrare l'emittente nella riga**. Il problema è un altro —
come si fa a sapere quali liste l'hanno già fatto e quali no, quando sono
decine?

Da qui il bollino. `multi_emittente` è una dichiarazione che la lista fa di sé:

> *«Io sono stata collaudata per mostrare più emittenti insieme: chi mi legge
> capisce di chi è ogni riga.»*

Finché il bollino è spento, il resto del sistema sa che quella lista **non** è
attrezzata, e può comportarsi di conseguenza.

#### ⭐ Il bollino si guadagna, non si mette

È il punto che tiene in piedi tutto il meccanismo, ed è il motivo per cui esiste
un controllo automatico.

Un'etichetta di collaudo che chiunque può appiccicare per far sparire un fastidio
non vale niente — anzi, è **peggio di niente**, perché da quel momento la lista
mescola emittenti *e dichiara di non farlo*. Quindi:

| | |
| --- | --- |
| **Il prezzo del biglietto** | una lista può dichiarare `multi_emittente` **solo se espone l'emittente in una sua colonna** |
| **Chi lo verifica** | `dbops.vw_liste_multi_emittente_non_certificate`, un controllo automatico che elenca le liste col bollino e senza la colonna |
| **Quanto deve valere** | **zero righe**, sempre. Una riga lì è un bollino senza collaudo dietro |

#### ⛔ Non si accende dall'interfaccia, e nemmeno via API

Il database ha un presidio che **rifiuta la scrittura** su questo campo a
chiunque non sia il processo di migrazione. Non è una questione di permessi
configurabili: non c'è nessun interruttore da aprire, e non esiste un profilo
abbastanza potente da farlo. Il tentativo si ferma con un errore esplicito.

La ragione è che un invariante con l'interruttore non è un invariante. Il campo
si dichiara nel **seed** delle liste, insieme al lavoro che lo giustifica, e
arriva insieme a quello.

> ⚠️ **Un limite dichiarato**: il presidio copre *questo* campo, non
> genericamente «i campi di sistema» di una lista. È una difesa stretta che
> tiene, scelta al posto di una larga che sulla carta copriva tutto e nella
> pratica non teneva.

#### Cosa vede chi sviluppa il frontend

Il bollino arriva nella configurazione della lista come una chiave in più,
`multi_emittente`. È **additiva**: chi non la legge non se ne accorge. Vale
`false` finché la lista non se l'è guadagnata.

#### Perché oggi è spento ovunque

Perché accenderlo prima che la colonna emittente sia effettivamente a video
aprirebbe esattamente la finestra che il bollino serve a chiudere: una lista che
*dichiara* di distinguere gli emittenti e non lo fa è peggio di una lista che
non dichiara niente.

Le liste si accendono **una per una**, quando la loro colonna mostra un nome su
dati veri.

#### Il verso opposto: la lista senza perimetro

Una lista dichiarata **senza** perimetro emittente (`perimetro_emittente = false`)
non espone colonne che dicono di chi è la riga: se una colonna attiva legge un
campo dell'emittente, la lista ha un perimetro ed è `multi_emittente`. Le righe
«di sistema» con l'emittente vuoto (preset, modelli standard) non la rendono
globale. Lo verifica `db/pgtap/ui/test-lista-definizione-perimetro-emittente-v1.sql`.

---

## 12. Roadmap — funzionalità in sviluppo

> **Nota**: questa sezione descrive funzionalità **previste**, con lo stato di
> ciascuna. Sono tracciate nel piano operativo interno con stato, sforzo e
> decisioni operative aperte; il riferimento `DEF-N` nei punti seguenti rimanda
> all'item del piano.
>
> ⚠️ **Uno stato scritto in una guida invecchia in silenzio, ed è già successo
> qui**: la §12.7 ha detto «4/13 liste migrate» per mesi dopo che l'estensione era
> diventata lo standard del frontend. Uno stato in questa sezione va **verificato
> contro il codice** prima di citarlo — una roadmap che dice «non c'è» di cose che
> ci sono è peggio di una sezione mancante, perché chi legge non ha modo di
> accorgersene.

### 12.1 Notifica "Preset aggiornato" (DEF-2)

> **Stato**: 🟡 Parziale — DB pronto, manca BE + FE. Sforzo S. **Da completare**.

Quando un admin modifica un preset di base, gli operatori che hanno
una preferenza salvata da quel preset vedranno un banner non intrusivo
*"La configurazione del tuo ruolo è stata aggiornata. Vedi novità?"*.
Click → modale personalizzazione con le colonne nuove evidenziate.

Il database ha già il meccanismo di tracciamento (snapshot
`preset_base_data_update` su `lista_preferenza_utente`, trigger di reset
automatico al cambio di preset). Manca: backend espone il flag
`preset_aggiornato` nella response config, frontend renderizza il
banner.

### 12.2 Export CSV/Excel con metadati filtri (DEF-1)

> **Stato**: 🟢 Done.

Le liste configurabili migrate al pattern `<ListaConfigurabile>` espongono
nella toolbar due azioni utility "Esporta CSV" e "Esporta Excel". Il
file generato include:

* solo le colonne `tipo_colonna='informazione'` e `'identificatore'`
  con `esportabile=true` (colonne `azione` e quelle marcate
  `esportabile=false` sono escluse automaticamente)
* l'ordine `ordine_default` del catalogo (non l'ordine personale
  dell'utente — l'export rispecchia la struttura registrata, non la
  preferenza personale)
* i filtri attualmente applicati alla lista (search, utility, stato,
  ecc.) — l'export rispetta sempre i filtri visibili
* metadati filtri allegati al file: in CSV come riga commentata
  prefissata `#` con JSON dei filtri; in Excel come foglio aggiuntivo
  "Filtri applicati" (chiave/valore)

**Hard cap 10.000 righe**: sopra questo limite l'API risponde 422 con
messaggio "Raffina i filtri e riprova". Pre-check via `count(*) over()`
nella query del repository: niente serializzazione di dataset oltre
soglia, errore immediato.

**File CSV con BOM UTF-8**: aprendo il file con doppio click su Windows
(Excel di default decodifica come Windows-1252), gli accenti italiani
sono preservati grazie al BOM. Costo: 3 byte. Tradeoff accettato.

**Estensione ad altre liste** (DEF-8): pattern minimal — ogni dominio
aggiunge un endpoint `GET /api/v1/<dominio>/<lista>/export/` di ~30
righe che riusa il proprio repository esistente e delega al renderer
generico `apps.ui.services.lista_export_service.ListaExportService`.
Lato FE 2 azioni `kind: 'utility'` nel `PageActionsBar` con il
composable riusabile `useFileDownload`.

### 12.3 Viste nominate multiple per utente (DEF-3)

> **Stato**: 🔴 Todo. Sforzo L. **Da completare**.

Oggi ogni operatore ha **una sola** preferenza per lista. La roadmap
prevede di poter salvare più viste nominate ("Clienti morosi",
"Clienti TOP", "Vista rapida") con switch rapido dalla toolbar.

Richiede schema migration su `lista_preferenza_utente` (aggiunta
colonne `nome` + `is_attiva`, sostituzione UNIQUE) e UI nuova
(`ListaViewSelect`).

### 12.4 Condivisione viste tra utenti (DEF-4)

> **Stato**: 🔴 Todo. Sforzo M. Dipende da DEF-3. **Da completare**.

Un team lead crea una vista personalizzata e la condivide con i
colleghi del reparto. I colleghi possono "adottarla" (copia personale
modificabile) o lasciare che si aggiorni automaticamente quando
l'autore la modifica.

### 12.5 Layout mobile / card list responsive (DEF-6)

> **Stato**: 🟢 In gran parte risolto dalla §7 (ritiro dinamico colonne). Card list dedicata: 🔴 non più prioritaria.

Su viewport stretto (mobile/tablet portrait) la lista resta usabile grazie al
**ritiro dinamico delle colonne** (§7): le colonne meno prioritarie scendono
nella riga di espansione e le azioni si raccolgono nel kebab, in automatico,
sulla stessa lista desktop. Non serve più un layout "card list" separato da
costruire e mantenere. Una vera modalità a card (una card per riga al posto
dell'espansione) resta un'opzione futura solo se emergesse un'esigenza
estetica; oggi non è prioritaria.

### 12.6 Colonne calcolate / composte (DEF-7 + DEF-10)

> **Stato**: 🔴 Todo per DEF-7, 🟡 Parziale per DEF-10. Sforzo L. **Da completare**.

Due pattern sovrapposti:

* **DEF-7 — Calcolate** (es. "giorni alla scadenza" = `CURRENT_DATE -
  data_scadenza`): nuovo `tipo_colonna='calcolata'` + `formula_client`
  che riferisce una funzione registrata in un `formulaRegistry` Vue.
* **DEF-10 — Composte** (es. `sosp_riatt` clienti che fonde
  `data_sospensione` + `data_riattivazione` in una resa custom):
  pattern già esistente come trick (`campo_sorgente=NULL` +
  `tipo_colonna='informazione'` + slot custom `cell-{codice}`),
  da formalizzare con flag dedicato.

Da decidere se fondere DEF-7+10 in un unico item con sotto-categorie
(`'calcolata'` vs `'composta'`) o tenerli distinti.

### 12.7 Estensione ad altre liste (DEF-8)

> **Stato**: ✅ **Superata come voce di roadmap** — non è più un'estensione da
> pianificare, è **lo standard**. Resta il debito dichiarato qui sotto.

⛔ **Oggi ogni lista si monta con `<ListaConfigurabile>`**: montare una `DataTable`
grezza in una view è l'**eccezione**, e va motivata in un commento sopra l'import.
La regola, le due sole eccezioni ammesse (le righe di un documento dentro il suo
master, e una tabella di anteprima dentro un dialog) e il registro di ciò che
ancora non la rispetta stanno in
[frontend-standards §«Regola zero della lista»](/dev/frontend/frontend-standards).
⚠️ **Nemmeno «è dentro un drawer» è un'eccezione**: una lista su un tab di drawer
si monta con `useDrawerTabLista` + `<DrawerTabLista>`.

**Che cosa è cambiato rispetto a questa voce.** Quando fu scritta, le liste servite
dal motore erano quattro e l'elenco qui sotto era la coda da smaltire —
`catalogo.articoli`, `vendite.preventivi`, `vendite.listini`,
`vendite.promo_articoli`, `vendite.approvazioni_prezzo`, `anagrafiche.indirizzi`,
`catalogo.unita_misura`, `pratiche`. **Sono tutte a catalogo**, e quante
definizioni porta `ui.lista_definizione` si legge dal seed
(`80_data/sql/ui/lista_definizione.csv`), non da questa pagina.

⭐ **La lezione che vale più dell'elenco**: una lista nuova **non richiede un
brief e non aspetta nessuno**. La sua configurazione è **dato, non DDL** — una
riga in `ui.lista_definizione` più N in `ui.lista_colonna`, create
dall'amministrazione in-app oppure con `scripts/gen_seed_lista.py`.

🔴 **Il debito che resta**, ed è dichiarato invece che dimenticato: la **matrice
slot/override** (editing inline, popolazione dal catalogo) oggi non ha una casa —
resta una `DataTable` grezza, col debito scritto nel
[piano di migrazione PrimeVue 5](/dev/work-in-progress/piano-migrazione-primevue-5)
§Gruppo B, insieme al criterio in tre domande e alla decisione ancora aperta.

### 12.8 Autocomplete chiavi i18n nel form colonna (DEF-9)

> **Stato**: 🔴 Todo. Sforzo S. **Da completare**.

Oggi nel drawer "Colonna" la chiave i18n è un campo testo libero. La
roadmap prevede un'API `GET /api/v1/core/i18n/keys?prefix=...` che
espone le chiavi presenti nei locales `it.json`/`en.json`, e il drawer
le offre con autocomplete. Riduce errori di battitura e drift.

---

## 13. Note finali

* **Le definizioni e le colonne hanno valore di catalogo**: il loro
  codice rimane stabile tra ambienti (dev → staging → produzione). Gli
  `id` numerici **non sono stabili**, usare sempre il codice come
  riferimento nei seed e nella documentazione.
* **I preset sono per-tenant**: ogni emittente fiscale può avere i
  suoi. Tipico setup multi-azienda: un preset di sistema generico +
  override per emittente quando serve.
* **Le preferenze utente sono inviolabili**: nessun admin può
  modificarle direttamente. L'admin può solo modificare il preset di
  base e sperare che l'utente "adotti la novità". Per forzare una
  ripulitura totale c'è il reset manuale dalla modale ("Reset alla
  configurazione di base").
* **Il pattern slot/override** vale ovunque: catalogo (sistema) + preset
  (azienda) + preferenza (utente). Ogni livello sovrascrive il
  precedente; un livello vuoto eredita dal precedente. Niente default
  hardcoded nel codice.

---
{% include-markdown "signature-core.md" %}
