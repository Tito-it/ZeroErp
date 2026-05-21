# Guida — Configurazione e Personalizzazione delle Liste

> **Ultima revisione**: 10 maggio 2026 — Blocco F Fase 2 (DEF-5b) atterrato:
> CRUD `lista_definizione` + `lista_colonna` via UI per SUPER_ADMIN.
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
* parametri di layout (ordine, larghezza, allineamento, gruppo)
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
* **Modifica definizione**: tutti i campi sono mutabili. Cambiare la
  vista SQL su una lista già in uso può rendere stale i campi sorgente
  delle colonne (la nuova vista deve esporre gli stessi attributi).
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
  * **Layout**: ordine default, larghezza default (px), allineamento (left/right/center), formato (es. `date_short`, `currency_eur`), gruppo, ordine gruppo
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

## 7. Esempio end-to-end — Lista Clienti

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

## 8. Permessi e visibilità — chi vede cosa

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

## 9. Casi d'uso comuni

### 9.1 Aggiungere una colonna a una lista esistente

1. SUPER_ADMIN: pagina tecnica → tab "Catalogo colonne" → **Nuova**
2. Compila i 3 sotto-tab (Generale / Comportamento / Layout)
3. Se il `campo_sorgente` non esiste nella vista SQL della lista, il
   sistema rifiuta. Coordinarsi col team DB per estendere la view.
4. La colonna è subito disponibile a tutti (nessun preset la include
   per default, ma l'operatore può aggiungerla manualmente dalla modale)
5. Opzionale: aggiornare i preset di base per includerla (admin operativo)

### 9.2 Nascondere una colonna sensibile per un profilo

1. Tenant admin: pagina operativa → tab "Permessi colonne" → **Nuovo**
2. Seleziona colonna + profilo accesso + livello `BLOCCATO`
3. Salva. Effetto immediato al prossimo refresh delle liste.

### 9.3 Creare una vista preconfigurata per un ruolo

1. Tenant admin: pagina operativa → tab "Preset" → **Nuovo**
2. Compila codice, descrizione, **ambito="ruolo"**, profilo target
3. Salva il preset (testata)
4. Apri "Gestisci composizione" → seleziona le colonne, riordina,
   imposta visibilità di default → Salva
5. Marca il preset come `is_default=true`. Sarà applicato
   automaticamente al primo accesso degli operatori con quel ruolo.

### 9.4 Disattivare temporaneamente una lista

1. SUPER_ADMIN: pagina tecnica → tab "Definizioni" → modifica la lista
2. Imposta `attivo=false` → Salva
3. La lista scompare dal runtime. Preset, colonne e preferenze
   sopravvivono in DB e tornano disponibili al riattivare.

### 9.5 Riallineare una preferenza dopo modifica del preset

Quando l'admin modifica un preset di base (aggiunge una colonna,
cambia l'ordine), gli utenti che hanno una preferenza salvata da quel
preset vedranno (in roadmap, DEF-2) un badge "Preset aggiornato" con
CTA "Vedi novità" che evidenzia le colonne aggiunte. L'utente può
adottare la modifica (un click) o ignorarla.

---

## 10. Comportamenti speciali e fallback

Alcune scelte di design pensate per evitare situazioni di blocco
all'utente o configurazioni stale silenziose.

### 10.1 Combo "Utility" — fallback matrice vuota

La combo "Utility" presente nei drawer (clienti, contratti, preventivi,
filtri lista) è popolata da `/api/v1/core/lookup/utilities-per-emittente/`
con tre comportamenti distinti:

| Caso | Comportamento |
| --- | --- |
| Operatore con emittente fiscale + matrice `emittenti_fiscali_utilities` popolata | SOLO le utility configurate per il proprio emittente |
| Operatore con emittente fiscale + matrice **vuota** | **Fallback**: tutte le utility con ruolo EF (la combo non resta mai vuota) |
| Super-admin senza emittente | Tutte le utility con ruolo EF |

Il fallback evita il caso "operatore con emittente nuovo, matrice non
ancora configurata dall'admin → combo vuota → impossibile creare
clienti/contratti". La regola business resta: una volta popolata la
matrice, l'operatore vede solo le utility del proprio emittente.

L'eventuale parametro `DEFAULT_UTILITY` (catena
user → group → emittente → sistema) viene risolto sul set già filtrato:
l'operatore non riceve come default un'utility che non avrebbe potuto
selezionare.

### 10.2 Workflow "lista in fase di sviluppo"

Il trigger `trgfn_ui_lista_definizione_a10_valida_vista_sql` valida
l'esistenza della vista SQL in `pg_catalog`, ma **salta** se:

* `attivo = false`, oppure
* `vista_sql IS NULL`

Questo permette al SUPER_ADMIN di registrare una lista in modalità
"draft" prima che il team DB abbia rilasciato la view. Una volta
deployata la view, basta editare il record (impostare la vista, attivare).

### 10.3 Cancellazioni protette dal sistema

Per evitare configurazioni stale silenziose, alcune cancellazioni
sono bloccate dal database e ribattute con messaggio parlante:

* **Cancellare una `lista_definizione` con colonne, preset o preferenze utente**: bloccato (FK RESTRICT). Messaggio: "Lista in uso da N utenti / colonne / preset, disattivala con `attivo=false`". L'admin sceglie tra disabilitare la lista (mantenendo le configurazioni) o ripulire prima i riferimenti.
* **Cancellare una `lista_colonna` referenziata da preferenze utente**: bloccato applicativamente (count su JSONB `configurazione->colonne`). Messaggio: "La colonna è in uso da N preferenze utente, disattivala con `attivo=false`".

In compenso, alcune cancellazioni sono **CASCADE intenzionali**:

* Cancellare una `lista_colonna` rimuove automaticamente i record
  collegati in `lista_preset_colonna` (composizione) e in
  `lista_colonna_permesso` (permessi).
* Cancellare un `lista_preset` rimuove la composizione (`lista_preset_colonna` CASCADE) ma le preferenze utente che lo referenziavano sopravvivono con `preset_base_id = NULL` (ON DELETE SET NULL): l'operatore continua a vedere la propria configurazione personale, indipendente dal preset originario.

### 10.4 Vincolo automatico — colonne `azione` non esportabili

Il database garantisce con CHECK constraint che le colonne di tipo
`azione` (pulsanti UI) non possano essere marcate `esportabile=true`.
Il drawer UX collabora: se selezioni `tipo_colonna='azione'` il toggle
"Esportabile" viene forzato a OFF e disabilitato. Vale anche se cambi
una colonna esistente da `informazione` a `azione`: il sistema riallinea
automaticamente il flag senza sollevare errori.

### 10.5 Etichette i18n con cascata fallback

La risoluzione frontend dell'etichetta colonna è sempre **safe**:

```text
t(etichetta_i18n_key) || etichetta || codice
```

* Se `etichetta_i18n_key` è valorizzata e la chiave esiste nei locales (it/en/...) → traduzione tradotta
* Altrimenti → l'etichetta letterale italiana (campo `etichetta`)
* Altrimenti → il codice tecnico (caso degenere, "guard" per evitare colonne senza header)

Così aggiungere un locale nuovo non richiede mai un'operazione DB —
basta aggiornare i file di traduzione.

### 10.6 Identificatori e azioni — sempre visibili

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

## 11. Roadmap — funzionalità in sviluppo

> **Nota**: questa sezione descrive funzionalità **previste ma non
> ancora rilasciate**. Sono tracciate nel piano operativo
> interno con
> stato, sforzo e decisioni operative aperte. Il riferimento `DEF-N`
> nei punti seguenti rimanda all'item del piano.

### 11.1 Notifica "Preset aggiornato" (DEF-2)

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

### 11.2 Export CSV/Excel con metadati filtri (DEF-1)

> **Stato**: 🟢 Done — atterrata 2026-05-10 sulla lista clienti.

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

### 11.3 Viste nominate multiple per utente (DEF-3)

> **Stato**: 🔴 Todo. Sforzo L. **Da completare**.

Oggi ogni operatore ha **una sola** preferenza per lista. La roadmap
prevede di poter salvare più viste nominate ("Clienti morosi",
"Clienti TOP", "Vista rapida") con switch rapido dalla toolbar.

Richiede schema migration su `lista_preferenza_utente` (aggiunta
colonne `nome` + `is_attiva`, sostituzione UNIQUE) e UI nuova
(`ListaViewSelect`).

### 11.4 Condivisione viste tra utenti (DEF-4)

> **Stato**: 🔴 Todo. Sforzo M. Dipende da DEF-3. **Da completare**.

Un team lead crea una vista personalizzata e la condivide con i
colleghi del reparto. I colleghi possono "adottarla" (copia personale
modificabile) o lasciare che si aggiorni automaticamente quando
l'autore la modifica.

### 11.5 Layout mobile / card list responsive (DEF-6)

> **Stato**: 🔴 Todo. Sforzo M. **Da completare**.

Su viewport stretto (mobile/tablet portrait) una DataTable con 8+
colonne è inutilizzabile. La roadmap prevede una modalità "card list"
attivata automaticamente sotto un breakpoint configurabile. Mostra le
colonne `identificatore` + le prime N `informazione` come card
verticali; la personalizzazione resta solo a toggle visibilità (no
riordino drag&drop su touch).

### 11.6 Colonne calcolate / composte (DEF-7 + DEF-10)

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

### 11.7 Estensione ad altre liste (DEF-8)

> **Stato**: 🟡 Parziale — 1/13 liste migrate. Sforzo S per lista, incrementale. **Da completare**.

Solo `anagrafiche.clienti` è oggi servita dal motore di personalizzazione.
Per ogni altra lista del frontend serve: seed catalogo colonne, seed
preset di sistema, eventuali nuovi campi nel SELECT del repository,
refactor del componente Vue da `<DataTable>` statico a
`<ListaConfigurabile>`. Pattern rodato, tempi prevedibili.

Liste residue (in ordine di priorità suggerita):

1. `anagrafiche.fornitori` (gemello clienti, codice già rodato)
2. `catalogo.articoli` (lista molto frequente)
3. `vendite.contratti`, `vendite.preventivi`
4. `vendite.listini`, `vendite.promo-articoli`, `vendite.approvazioni-prezzo`
5. `anagrafiche.soggetti`, `anagrafiche.indirizzi`
6. `catalogo.unita-misura`
7. `pratiche` (dashboard 3 livelli, caso speciale)

### 11.8 Autocomplete chiavi i18n nel form colonna (DEF-9)

> **Stato**: 🔴 Todo. Sforzo S. **Da completare**.

Oggi nel drawer "Colonna" la chiave i18n è un campo testo libero. La
roadmap prevede un'API `GET /api/v1/core/i18n/keys?prefix=...` che
espone le chiavi presenti nei locales `it.json`/`en.json`, e il drawer
le offre con autocomplete. Riduce errori di battitura e drift.

---

## 12. Note finali

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
