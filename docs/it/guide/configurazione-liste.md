# Guida — Configurazione, Personalizzazione e Responsività delle Liste

> **Ultimo aggiornamento**: 22 novembre 2026
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
> * [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina) — le misure «righe per pagina» ammesse e i due default
> * [dbops.vw_liste_multi_emittente_non_certificate](/dbzero/dbops/views/vw_liste_multi_emittente_non_certificate) — le liste col bollino «multi-emittente» senza la colonna dell'emittente
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — la configurazione effettiva di una lista per un utente
> * [ui.fn_preset_di_base](/dbzero/ui/funzioni/fn_preset_di_base) — la scelta del preset di base, per liste e dashboard
> * [ui.fn_preset_aggiornato](/dbzero/ui/funzioni/fn_preset_aggiornato) — il banner «preset aggiornato»
> * [ui.fn_ordinamento_lista](/dbzero/ui/funzioni/fn_ordinamento_lista) — l'ordinamento con cui una lista parte, per un utente
> * [ui.fn_misura_lista](/dbzero/ui/funzioni/fn_misura_lista) — le righe per pagina di una lista, per un utente
> * [ui.trgfn_preferenza_guard_forma](/dbzero/ui/funzioni/trgfn_preferenza_guard_forma) — che cosa una preferenza può contenere
> * [ui.fn_lista_colonne_livello](/dbzero/ui/funzioni/fn_lista_colonne_livello) — il livello (`TUTTO`, `LETTURA`, `BLOCCATO`) di ogni colonna per un utente
> * [ui.trgfn_ui_lista_definizione_a10_valida_vista_sql](/dbzero/ui/funzioni/trgfn_ui_lista_definizione_a10_valida_vista_sql) — la vista della lista esiste
> * [ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente](/dbzero/ui/funzioni/trgfn_ui_lista_colonna_a10_valida_campo_sorgente) — il campo sorgente esiste nella vista
> * [ui.trgfn_lista_definizione_guard_dichiarazioni](/dbzero/ui/funzioni/trgfn_lista_definizione_guard_dichiarazioni) — il bollino «multi-emittente», il perimetro e la genealogia non si scrivono dall'applicazione
>
> **Vedi anche** — API e service backend:
>
> * [API runtime liste](/backend/ui/manual/api_ui_liste) — endpoint che alimentano le liste lato operatore
> * [API admin personalizzazioni](/backend/ui/manual/api_ui_admin_personalizzazioni) — endpoint admin (preset, permessi, definizioni, colonne)
> * [API export liste](/backend/ui/manual/api_export_liste) — export CSV/Excel delle liste configurabili
>
> **Vedi anche** — guide correlate:
>
> * [Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — profili d'accesso e azioni di processo
> * [Configurazione delle dashboard](/guide/configurazione-dashboard) — la gemella delle liste: la home a card
> * [Configurare il sistema senza perdere le modifiche agli aggiornamenti](/guide/configurazione-iniziale-e-aggiornamenti) — liste, colonne e preset proposti dal programma: che cosa si cambia, che cosa resta del programma, che cosa fa un aggiornamento

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
* **lasciare libertà** all'operatore di personalizzare la propria vista (quali colonne, in che ordine, con che larghezza, quante righe per pagina)

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
* la **vista SQL** dalla quale la lista legge i dati (es. `vw_clienti_lista`), cercata nello schema dati
* lo stato attivo/disattivo
* la **soglia della ricerca libera**: quanti caratteri servono prima che il termine digitato
  parta verso il server. È una proprietà della lista, uguale per tutti
* il **perimetro emittente** — dice se le righe della lista appartengono a un emittente
  (la maggior parte) o se la lista è un catalogo globale, dove la domanda «di quale
  emittente è questa riga» non si pone: vedi §11.6
* il **bollino «multi-emittente»** — dice se quella lista è stata collaudata per
  mostrare righe di **più emittenti insieme**. Nasce spento e non si accende
  dall'interfaccia: vedi §11.6
* la **genealogia dei documenti** — dice se il sistema unisce alle righe la colonna
  «Transito» (il documento più a valle nella catena). La dichiarano le liste dei
  documenti che la mostrano, e non si cambia dall'interfaccia: vedi §11.6

### 2.2 Colonna (`lista_colonna`)

Per ogni lista, l'insieme delle **colonne disponibili**. Ogni colonna ha:

* un codice tecnico (univoco nella lista)
* un'etichetta visibile, un'etichetta estesa (tooltip) e una chiave i18n opzionale per il multilingua (§5.3)
* il **tipo di colonna**:
  * `identificatore` → sempre visibile e fissata a sinistra, non nascondibile (es. il numero di un contratto)
  * `informazione` → personalizzabile liberamente dall'operatore
  * `azione` → pulsanti/icone (modifica, dettaglio); sempre visibile, senza campo sorgente e quindi non esportabile
* il **tipo di dato** (testo, numero, data, data e ora, booleano, enumerato)
* il campo sorgente e da dove si legge: nella vista SQL della lista (il caso
  normale), oppure nella **genealogia dei documenti** (la colonna «Transito»), che il
  sistema unisce alle righe solo sulle liste che lo dichiarano; vuoto per le colonne
  composte dal frontend (vedi §5.2.2)
* parametri di layout (ordine, larghezza, **priorità di ritiro**, allineamento,
  formato, gruppo) — la *priorità* governa la responsività: decide
  quale colonna scende per prima quando lo spazio si stringe (vedi §7)
* flag di comportamento (filtrabile, ordinabile, esportabile, ricercabile,
  **sensibile**). Una colonna `sensibile` non la vede **nessuno** finché un permesso
  colonna non la concede a un profilo (§2.4)

### 2.3 Preset (`lista_preset` + `lista_preset_colonna`)

Una **configurazione preconfezionata** di una lista pensata per un
contesto. Tre ambiti possibili:

| Ambito | Quando usarlo | Esempio |
| --- | --- | --- |
| **Ruolo** | Default per chi ha un certo profilo accesso | "Default amministrativo" — colonne fiscali in evidenza |
| **Emittente fiscale** | Default per gli operatori di una specifica azienda, quando il loro profilo non ha un preset di ruolo | "Default Acme S.p.A." — include codice cliente Acme |
| **Sistema** | Default applicato a tutti se nessun altro preset si applica | "Default sistema" — le 5 colonne base |

Un preset porta:

* la **composizione** delle colonne: quali includere, in che ordine, con quale
  larghezza, quali sono visibili di default e quali sono "fissate" (sticky a
  sinistra, non scrollano)
* l'**ordinamento** di partenza: da quali colonne la lista parte ordinata, e in che verso
* le **righe per pagina**, scelte fra le misure del catalogo (§2.6); vuoto vuol dire
  «la misura di default» per il tipo di lista

I **filtri** di partenza non sono del preset: li decide la schermata di ogni lista.

Ogni combinazione (lista, ambito, profilo, emittente) è un **posto**, e un posto ha
**un solo preset acceso**: è lo **standard** della lista per chi rientra in
quell'ambito (§3). Un preset vale se è acceso; i preset spenti non entrano nella
cascata e non occupano il posto.

Una nuova versione del preset si prepara **spenta**, come bozza accanto a quello in
uso. Per metterla al suo posto si spegne prima il preset vecchio e poi si accende la
bozza: accendere la bozza mentre il vecchio è ancora acceso è rifiutato.

### 2.4 Permesso colonna (`lista_colonna_permesso`)

Per ogni colonna di una lista, è possibile definire un **livello di
accesso** specifico per profilo accesso:

* `TUTTO` → la colonna è visibile, personalizzabile ed esportabile
* `LETTURA` → la colonna è visibile a video ma **non esce nell'export**
* `BLOCCATO` → la colonna è completamente nascosta: non arriva alla lista, non appare
  nella modale di personalizzazione, non esce nell'export e la ricerca libera non ci cerca

Senza permessi la colonna vale `TUTTO`, tranne le colonne `sensibile`, che senza un
permesso valgono `BLOCCATO`: per loro il permesso è un **lasciapassare** (si concede
`TUTTO` o `LETTURA` ai profili che devono vederle). Se più profili dell'operatore
danno un livello sulla stessa colonna, vince il profilo **più specifico** (un profilo
ad hoc prima di quello di reparto); a parità, il livello più restrittivo. La regola
ha una sede sola, [ui.fn_lista_colonne_livello](/dbzero/ui/funzioni/fn_lista_colonne_livello).

Esempio: per il profilo "Tecnico assistenza" la colonna `partita_iva`
del cliente può essere `BLOCCATO` (informazione fiscale non rilevante
per il loro lavoro).

### 2.5 Preferenza utente (`lista_preferenza_utente`)

La **personalizzazione che l'operatore salva** dalla modale "Personalizza
colonne". Conserva **solo ciò che l'operatore ha scelto**, chiave per chiave:

* le colonne: ordine, visibilità, larghezza
* le righe per pagina

L'ordinamento e i filtri **non si salvano**. Un clic sull'intestazione di una colonna riordina la
lista per la sessione; riaprendola, la lista riparte dall'ordinamento del preset. I filtri ripartono
da quelli che la schermata propone.

Che cosa una preferenza può contenere lo controlla il database al salvataggio: solo colonne della
lista, ciascuna una volta, e una misura del catalogo. Le regole sono nella scheda di
[ui.trgfn_preferenza_guard_forma](/dbzero/ui/funzioni/trgfn_preferenza_guard_forma).

Una chiave che l'operatore non ha toccato non si salva: continua a venire dal preset,
così una modifica del preset arriva anche a chi ha personalizzato altro. La
preferenza ricorda anche il preset di partenza, per il banner "preset aggiornato"
(§6) quando l'admin modifica il preset di base: la data del contenuto di quel preset
la registra il database a ogni salvataggio.

Una sola preferenza per coppia (utente, lista). Il salvataggio
sovrascrive la precedente; una preferenza senza più scelte si cancella, e l'operatore
torna allo standard.

### 2.6 Righe per pagina (`misure_pagina`)

Le misure che il selettore sotto ogni lista offre («righe per pagina») stanno in un
catalogo solo, insieme a due default: uno per le liste a pagina intera e uno per le
liste compatte nei drawer e nei dialog. Il catalogo ha sempre tutti e due i default.
Ogni lista dichiara di quale dei due tipi è, e quando né il preset né la preferenza
dicono la misura parte dal default del suo tipo: le righe di un documento, aperte in
un drawer, partono dalla misura compatta.

Preset e preferenze possono dichiarare solo una misura del catalogo, e la lista
risponde **sempre** una misura del catalogo. Quando una misura si toglie dal catalogo,
esce anche dalle preferenze che la usavano, e quegli operatori tornano allo standard.
Una misura non si cambia di valore: se ne aggiunge una nuova. Il dettaglio è in
[ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina).

La misura che l'operatore vede è anche quella con cui il programma serve la lista a chi
non dice quante righe vuole: la regola è una sola
([ui.fn_misura_pagina_risolta](/dbzero/ui/funzioni/fn_misura_pagina_risolta)).

---

## 3. La cascata di risoluzione

Quando l'operatore apre una lista, il sistema risolve **ogni scelta per conto suo** —
le colonne e le righe per pagina — prendendola dal primo livello che la contiene:

1. **La preferenza personale**, se l'operatore ha scelto quella chiave
2. Altrimenti, il **preset di base**: il primo preset acceso, in quest'ordine, che ha almeno
   una colonna attiva
   1. il preset del suo **ruolo** (fra più profili, quello più specifico), solo quando la
      sessione ha una veste: senza veste la cascata parte dall'emittente
   2. il preset del suo **emittente fiscale**, solo se l'emittente è attivo
   3. il preset di **sistema**

   Un preset senza colonne attive non conta, a nessun livello: la cascata passa al
   successivo, e da quel preset non prende nemmeno le righe per pagina o l'ordinamento.
3. Altrimenti, il **catalogo grezzo**: tutte le colonne attive, visibili, nell'ordine
   di catalogo, e la misura di default per il tipo di lista

Così una preferenza che tocca solo le colonne non congela le righe per pagina del preset.

L'**ordinamento di partenza** viene sempre dal preset di base, perché la preferenza non lo
porta; senza un preset che lo dica, la lista non ha un ordinamento di partenza. Dall'ordinamento del
preset si tolgono le colonne spente, quelle che non si possono ordinare e quelle che l'operatore
non può vedere (§2.4): una lista non si ordina per un dato nascosto.

Sopra qualunque livello valgono poi tre regole:

* le colonne aggiunte al catalogo dopo che preset o preferenza sono stati scritti
  entrano **in coda e spente**: l'operatore le trova nella modale e le accende se gli servono;
* le colonne `identificatore` e `azione` sono sempre visibili, e gli identificatori
  sempre fissati;
* i **permessi colonna** (§2.4): le colonne `BLOCCATO` per l'operatore vengono tolte,
  le `LETTURA` perdono l'export.

La sede della cascata è il database:
[ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config), che sceglie il
preset di base con [ui.fn_preset_di_base](/dbzero/ui/funzioni/fn_preset_di_base), la stessa
regola delle dashboard. Il preset di base scelto è nel risultato, e il backend lo salva con la
preferenza.

---

## 4. Pagina admin operativa — `/config/personalizzazioni-liste`

Accessibile a **tenant admin** con azione di processo `ui_preset_manage`
oppure `ui_permesso_manage`, e a SUPER_ADMIN. Ogni tab compare a chi ha
l'azione corrispondente.

Header: **Select "Lista corrente"** — sceglie su quale lista
operare. Tutti i tab sotto si aggiornano di conseguenza.

### 4.1 Tab "Preset"

Lista dei preset configurati per la lista corrente. Per ogni preset si
vedono codice, descrizione, ambito (sistema/ruolo/emittente), riferimento
(profilo o emittente specifico), numero colonne configurate, stato
attivo.

**Operazioni disponibili**:

* **Nuovo preset**: drawer con codice, descrizione, ambito, riferimenti
  condizionali (profilo se ambito=ruolo, emittente se ambito=emittente
  fiscale), righe per pagina (una misura del catalogo, o il default), flag
  attivo. Un preset nuovo per un posto che ne ha già uno acceso nasce spento (§2.3).
* **Modifica preset**: aggiorna i campi mutabili. La lista, l'ambito e i
  riferimenti sono immutabili dopo la creazione, e lo garantisce il database:
  per cambiarli si spegne il preset e se ne crea uno nuovo.
* **Gestisci composizione**: drawer dedicato per definire quali colonne
  includere, in che ordine (frecce ▲▼), con quale larghezza, quali visibili e
  quali fissate. Il salvataggio sostituisce la composizione intera in un colpo solo.
* **Elimina preset**: si cancella con la sua composizione. Le preferenze utente che
  lo avevano come base sopravvivono: le scelte dell'operatore restano, e ciò che
  l'operatore non ha scelto viene dal nuovo preset di base della cascata (§3).

### 4.2 Tab "Permessi colonne"

Lista dei permessi colonna configurati per la lista corrente. Ogni
riga è una tripla (colonna × profilo accesso × livello accesso).

**Operazioni disponibili**:

* **Nuovo permesso / Modifica**: UPSERT su (colonna, profilo). Se la
  coppia esiste già, viene aggiornato il livello. Operazione idempotente.
* **Elimina permesso**: rimuove il vincolo, la colonna torna al comportamento di
  default (`TUTTO`, oppure `BLOCCATO` se la colonna è `sensibile`).

**Regola pratica**: su una colonna normale si aggiunge un permesso solo quando serve
una restrizione; l'assenza di un permesso = la colonna è disponibile a tutti. Su una
colonna `sensibile` vale il contrario: il permesso è ciò che la apre. ⚠️ Fra più
profili dello stesso operatore vince il più specifico, non il più restrittivo: un
`TUTTO` su un profilo ad hoc apre una colonna che il profilo di reparto blocca.

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
  dello schema dati, che alimenta la lista), note, flag attivo.
* **Modifica definizione**: sono mutabili descrizione, vista SQL, schema, note, soglia
  della ricerca e stato. Non si cambiano il **codice**, che è la chiave con cui la
  schermata si cerca (per un codice sbagliato si spegne la lista e se ne crea un'altra),
  e le **dichiarazioni** della lista — il bollino «multi-emittente», il perimetro
  emittente e la genealogia dei documenti — che il database rifiuta di far scrivere
  dall'applicazione (§11.6). Cambiare la vista SQL di una lista accesa ricontrolla le
  colonne: se la vista nuova non ha il campo di una colonna, il cambio è rifiutato e il
  messaggio nomina le colonne da correggere o spegnere.
* **Disattiva (soft-disable)**: porta `attivo=false`. La lista scompare dal catalogo
  runtime, e con lei, sospese ma intatte, le sue colonne, i suoi preset e le
  preferenze degli utenti: alla riattivazione tutto torna com'era.
* **Elimina definizione**: bloccato dal sistema se ci sono
  colonne, preset o preferenze utente associate. In quel caso, l'unica
  via è il **soft-disable**.

#### 5.1.1 Workflow "lista in fase di sviluppo"

Quando si registra una lista nuova la cui vista SQL non è ancora stata
creata in database:

1. Si crea il record con il campo "vista SQL" vuoto, oppure con `attivo=false`:
   in questi due casi il sistema **non verifica** che la vista esista
2. Le colonne si possono registrare subito: il campo sorgente si verifica solo su una
   lista accesa con una vista indicata
3. Quando la vista è rilasciata, la si indica e si attiva la lista (`attivo=true`):
   all'accensione il sistema verifica la vista e le colonne già registrate, e rifiuta se
   una colonna ha un campo che la vista non ha. Da quel momento la verifica scatta a
   ogni scrittura

Questo permette di registrare la struttura senza dover sincronizzare con il deploy DDL.

### 5.2 Tab "Catalogo colonne"

Master-detail su `Lista corrente` (Select header). Mostra TUTTE le
colonne registrate per quella lista, attive e disattivate.

**Operazioni disponibili**:

* **Nuova colonna**: drawer con 3 sotto-tab:
  * **Generale**: codice, etichetta visibile, etichetta estesa (tooltip), chiave i18n (per traduzioni), tipo colonna, tipo dato, campo sorgente
  * **Comportamento**: filtrabile, ordinabile, esportabile, ricercabile full-text, sensibile, attivo
  * **Layout**: ordine default, larghezza default (px), allineamento (left/right/center), formato (tabella sotto), gruppo, ordine gruppo
* **Modifica colonna**: i campi del drawer sono mutabili, tranne il **codice**, che è
  la chiave con cui preferenze e preset ricordano la colonna (per un codice sbagliato si
  spegne la colonna e se ne crea un'altra). Anche il `lista_id` è immutabile (per
  "spostare" una colonna da una lista all'altra, cancellala e ricreala).
* **Disattiva (soft-disable)**: imposta `attivo=false`. Colonna
  invisibile in runtime; le preferenze utente che la citavano restano, e la colonna
  semplicemente non compare più.
* **Elimina colonna**: bloccato dal sistema se ci sono preferenze
  utente che la citano, o se la colonna sta nella composizione di un preset
  (prevenzione di configurazioni stale silenziose); l'alternativa raccomandata è
  disattivare con `attivo=false`. I permessi colonna se ne vanno con lei.

La **priorità di ritiro** (§7) non è nel drawer: si regola nel seed del catalogo.

#### 5.2.1 I formati di resa (`formato`)

Il valore di `formato` sceglie il formatter con cui `<ListaConfigurabile>` rende
la cella (`CellaConfigurabile`), a meno che la view non fornisca uno slot
`cell-{codice}` suo:

| `formato` | Resa | Note |
|---|---|---|
| `date_short` | data nel locale dell'utente | per le colonne `tipo_dato = date` |
| `datetime`, `datetime_short` | data e ora | le due sigle danno la stessa resa |
| `currency_eur` | importo in euro | |
| `currency_eur_6` | importo in euro a sei decimali | |
| `number` | numero nel locale | |
| `percent_2` | numero a due decimali + ` %` | il valore è già in percentuale |
| `yesno` | etichetta **Sì / No** (building block `SiNoTag`); `null` resta vuoto | ⭐ **è la resa di un booleano in lista**: una colonna booleana è una riga di `ui.lista_colonna` con questo formato, non uno slot riscritto nella view. Un `tipo_dato = boolean` **senza** formato prende la stessa resa, così un booleano dimenticato non esce mai come `true`/`false` grezzi |
| `natura_doc` | la natura del documento come tag (`NaturaDocTag`) | |
| *(vuoto o altro)* | il valore com'è | |

#### 5.2.2 Vincoli automatici e colonne composte

* Le colonne di tipo `azione` non hanno campo sorgente, e una colonna senza campo
  sorgente non è esportabile (vincoli del database, §11.4). Se selezioni `azione`, il
  toggle "Esportabile" viene forzato a OFF e disabilitato.
* Le colonne con `campo_sorgente` valorizzato vengono validate contro
  la vista SQL della lista padre, nel suo schema: il sistema rifiuta la scrittura se
  l'attributo non esiste. Le colonne senza campo sorgente non sono validate.
* Una colonna che legge dalla **genealogia dei documenti** sta solo su una lista che lo
  dichiara, e non è filtrabile, ordinabile né ricercabile: filtri, ordinamento e ricerca
  interrogano la vista, che quel campo non lo porta. Se una colonna perde il suo campo
  dopo (una vista cambiata da un aggiornamento), lo segnala il controllo automatico del
  catalogo delle liste.
* Una **colonna composta** — un valore che il frontend costruisce da più campi, come
  sospensione e riattivazione del cliente in una cella sola — è una colonna a catalogo
  con il campo sorgente vuoto, resa dallo slot `cell-{codice}` della view. Non ha un
  valore lato server, quindi si registra **non esportabile**. Se una colonna derivata
  deve essere ordinabile o esportabile, non è una composta: è una colonna che manca
  nella vista, e si chiede al team DB.

### 5.3 Etichette e multilingua

Ogni colonna può avere due etichette:

* **etichetta** — testo letterale italiano, obbligatorio (fallback)
* **etichetta_i18n_key** — chiave i18n opzionale (es. `anagrafiche.clienti.col_ragione_sociale`)

La risoluzione frontend dell'etichetta colonna è sempre **safe**:

```text
chiave i18n presente nei locales ? t(etichetta_i18n_key) : (etichetta || codice)
```

* Se `etichetta_i18n_key` è valorizzata e la chiave esiste nei locales (it/en/...) → la traduzione
* Altrimenti → l'etichetta letterale italiana (campo `etichetta`)
* Altrimenti → il codice tecnico (caso degenere, "guard" per evitare colonne senza header)

Così aggiungere un locale nuovo non richiede mai un'operazione DB —
basta aggiornare i file di traduzione. Le chiavi stanno sotto la radice dell'area
(`anagrafiche.clienti.col_*`, `vendite.contratti.col_*`) o sotto `common.*` se
trasversali.

---

## 6. Cosa fa l'operatore finale

L'operatore vede ogni lista personalizzabile con due affordance:

* **Pulsante "Personalizza colonne"** — apre la modale di
  configurazione. Permette di:
  * mostrare/nascondere colonne (toggle, disabilitato con tooltip sulle
    `identificatore` e `azione`)
  * riordinare con frecce ▲▼
  * cambiare la larghezza inline
  * scegliere le righe per pagina
  * ripristinare lo standard (la preferenza si cancella e torna il preset di base)

  Le colonne arrivate nel catalogo dopo l'ultimo salvataggio sono contate e
  segnalate come nuove. Quali colonne restano fissate a sinistra lo decidono il
  preset e il tipo di colonna, non la modale.
* **Intestazione delle colonne** — un clic ordina la lista per quella colonna. L'ordinamento vale
  per la sessione e non si salva: riaprendo la lista si riparte da quello del preset.
* **Banner "preset aggiornato"** — appare quando l'admin modifica il
  preset da cui partiva la preferenza dell'utente. "Vedi novità" apre la modale
  con le novità; "Ignora" lo nasconde finché il preset non cambia di nuovo.
  Se invece il preset di partenza non è più lo standard dell'utente (è stato spento,
  cancellato, o ne vale un altro), il sistema lo segnala con un esito suo, "preset
  di base cambiato", che propone di riallineare la preferenza al nuovo standard.

### 6.1 Cosa NON può fare l'operatore

* Modificare i preset di sistema/ruolo/emittente (sono di responsabilità
  dell'admin)
* Vedere colonne che hanno permesso `BLOCCATO` per il suo profilo
  accesso, o colonne `sensibile` che nessun suo profilo ha ricevuto (sono filtrate
  prima di arrivare al frontend)
* Nascondere le colonne `identificatore` e `azione`
* Esportare colonne `azione`, colonne marcate `esportabile=false` o colonne con
  permesso `LETTURA` (anche se le vede a video)

L'export rispecchia la vista dell'operatore: le colonne visibili, nel suo ordine, con
i filtri applicati (§10.6).

---

## 7. Liste responsive — adattamento automatico allo spazio

Una lista con molte colonne (i contratti ne hanno una dozzina) non sempre
entra nello schermo: basta aprire la sidebar di navigazione, o usare un
portatile o un tablet, e lo spazio si stringe.

Le liste configurabili si **adattano da sole** allo spazio disponibile,
in tempo reale. Quando lo spazio non basta non compare lo scroll orizzontale: la
lista si **compatta**, seguendo un ordine di priorità ben preciso.

### 7.1 I tre gradini di compattazione

Il sistema cerca di tenere visibili più dati possibile, agendo per gradini:

1. **Spazio sufficiente** → tutto normale: colonne affiancate, pulsanti azione
   (modifica, PDF, gestisci righe…) in fila.
2. **Spazio stretto** → i **pulsanti azione si raccolgono in un menù "⋮"**
   (kebab): un piccolo menù a tendina al posto di 3-4 iconcine. Recupera
   spazio **senza nascondere alcun dato**. È la prima mossa, perché un click
   in più sulle azioni dà meno fastidio di una colonna che sparisce.
3. **Spazio ancora insufficiente** → le **colonne meno importanti scendono**
   in una riga di dettaglio espandibile (la freccetta a inizio riga).
   Nessun dato è perso: aprendo la freccetta vedi le colonne ritirate, con la
   stessa formattazione (un Tag di stato resta un Tag colorato).

Tutto è fluido: allargando di nuovo la finestra — o richiudendo la sidebar —
le colonne **ritornano** al loro posto.

### 7.2 Chi decide quale colonna scende? La priorità

Quando si arriva al terzo gradino, **quale** colonna scende per prima non è
casuale: lo decide un valore chiamato **priorità**, impostato per ogni colonna
nel catalogo (è il fratello di "ordine" e "larghezza" che già conosci dal §2.2).

Regola semplice: **priorità più bassa = scende per prima** (una colonna senza
priorità dichiarata vale 50). A parità di priorità, scende prima la colonna più a
destra.

Un esempio sul modello della lista contratti — l'ordine con cui le colonne si
ritirano man mano che lo spazio cala (le priorità vere stanno nel catalogo della
lista):

| Ordine di ritiro | Colonna | Priorità |
| --- | --- | --- |
| 1ª a scendere | Data | 25 (bassa) |
| 2ª | Categoria cliente | 30 |
| 3ª | Codice account | 40 |
| poi… | Listino, Ambito, Valido dal/al, Utility, Id. fiscale | 45–75 |
| (quasi mai) | Stato, Cliente | 90–95 (alta) |
| **mai** | Numero, Azioni | — (identificatore / azione) |

Così le informazioni che servono sempre (numero, cliente, stato) restano
visibili fino all'ultimo, mentre quelle accessorie (data, categoria) scendono
per prime. Le colonne **identificatore**, **azione** e le colonne **fissate** non
scendono **mai**: una lista contratti senza il numero, o senza i pulsanti, sarebbe
inutile.

### 7.3 Come cambiare l'ordine di ritiro

La priorità è un dato di catalogo, uguale per tutti: si regola nel seed delle colonne
della lista (il drawer "Colonna" della pagina tecnica non la espone). Se vuoi che una
colonna scenda prima o dopo, le dai una priorità più bassa o più alta. Non serve
toccare codice frontend.

> **Importante**: la priorità è una **scelta di progetto** della lista, uguale
> per tutti gli operatori — non una preferenza personale. La personalizzazione
> individuale del §6 (quali colonne mostrare, in che ordine) agisce **prima**:
> il ritiro dinamico lavora poi sull'insieme di colonne effettivamente
> visibili per quell'operatore.

### 7.4 Dispositivi piccoli

Lo stesso meccanismo sistema le liste su **tablet e mobile**: lì lo spazio è poco
per definizione, quindi le colonne si compattano e si raccolgono nell'espansione in
automatico. Non c'è un layout mobile separato (niente "card list"): la lista è **una
sola** — tabella più kebab — e si adatta da sé.

### 7.5 Per chi sviluppa (in breve)

Il comportamento vive in **building block riusabili**: una nuova lista lo
eredita senza scrivere logica responsive.

* **`<ListaConfigurabile>`** — il componente che disegna la lista a partire
  dalla configurazione risolta dal backend; ospita il ritiro dinamico e il banner
  "preset aggiornato".
* **`useResponsiveColumns`** — il "cervello": misura lo spazio **reale** del
  contenitore (non la larghezza della finestra — così reagisce anche
  all'apertura della sidebar, che la finestra non vede) e decide compattazione
  e ritiro applicando le priorità di catalogo.
* **`useListaConfigurabilePage`** — lo "scheletro" della pagina lista (ricerca,
  paginazione, export, azioni di toolbar): il componente di dominio resta
  minimale, con solo i propri filtri e azioni di riga.
* **`useDrawerTabLista`** + **`<DrawerTabLista>`** — la stessa lista su un tab di
  drawer.

⛔ **Ogni lista si monta con `<ListaConfigurabile>`**: montare una `DataTable`
grezza in una view è l'**eccezione**, e va motivata in un commento sopra l'import.
Nemmeno «è dentro un drawer» è un'eccezione. Una lista nuova è **dato, non DDL**:
una riga in `ui.lista_definizione` più N in `ui.lista_colonna`, create
dall'amministrazione in-app oppure con `scripts/gen_seed_lista.py`.

Dettagli tecnici, le eccezioni ammesse e regole di stile:
[standard frontend](/dev/frontend/frontend-standards) (sezioni «Regola zero della
lista» e «Ritiro dinamico colonne — `useResponsiveColumns`») e i cataloghi
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
* Ambito: sistema, attivo: ✓
* Composizione: ragione_sociale, comune, stato (le tre più universali)

**Preset "Default amministrativo"**:

* Codice: `default-admin`, Descrizione: "Vista amministrativa"
* Ambito: ruolo, profilo: "Amministrativo", attivo: ✓
* Composizione: ragione_sociale, partita_iva, codice_fiscale, stato

### Step 4 — Tenant admin imposta i permessi

Tab "Permessi colonne":

* Colonna `partita_iva` × profilo "Tecnico" → livello `BLOCCATO`
* Colonna `codice_fiscale` × profilo "Tecnico" → livello `BLOCCATO`

I tecnici non vedono nemmeno questi campi nella modale di
personalizzazione, anche se volessero.

### Step 5 — L'operatore usa la lista

Mario (profilo "Amministrativo") apre `/anagrafiche/clienti`:

* Nessuna preferenza personale → cerca il preset per il ruolo "Amministrativo" → trova "Default amministrativo"
* Applica permessi: nessuna restrizione per Amministrativo → vede tutto
* Visualizza: ragione_sociale, partita_iva, codice_fiscale, stato (e, in coda e
  spente, le colonne del catalogo che il preset non elenca: le può accendere dalla modale)

Mario decide che gli serve anche `comune` e nasconde `codice_fiscale`.
Salva. Ora ha una sua preferenza personale **sulle colonne**: le righe per pagina e
l'ordinamento di partenza continuano a venire dal preset.

Luca (profilo "Tecnico") apre la stessa lista:

* Nessuna preferenza personale → nessun preset per il ruolo "Tecnico" → nessun preset
  per l'emittente Acme → preset di sistema "Default sistema"
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

Le azioni di processo `ui_preset_manage` e `ui_permesso_manage` si concedono a un
profilo come ogni altra azione di processo: la decisione è del tenant, che sceglie a
chi delegare la gestione di preset e permessi (vedi
[Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)).

Il super-admin **bypassa** i controlli sulle azioni: entra in entrambe le pagine e
modifica tutto. ⚠️ Il **livello di colonna** (§2.4) invece non ha eccezioni: lo
calcola il database sui profili di chi guarda, e una colonna `sensibile` senza un
permesso concesso a un suo profilo non la vede nemmeno il super-admin.

---

## 10. Casi d'uso comuni

### 10.1 Aggiungere una colonna a una lista esistente

1. SUPER_ADMIN: pagina tecnica → tab "Catalogo colonne" → **Nuova**
2. Compila i 3 sotto-tab (Generale / Comportamento / Layout)
3. Se il `campo_sorgente` non esiste nella vista SQL della lista, il
   sistema rifiuta. Coordinarsi col team DB per estendere la view.
4. La colonna è subito disponibile: nessun preset la include, ma la cascata la
   aggiunge in coda e spenta, e l'operatore la accende dalla modale (una colonna
   `sensibile` solo dopo il permesso, §2.4)
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
3. Salva. Effetto immediato al prossimo caricamento delle liste.

Se la colonna deve restare nascosta a **tutti tranne** alcuni profili, la si marca
`sensibile` nel catalogo e si concede `TUTTO` (o `LETTURA`) solo a quei profili.

### 10.3 Creare una vista preconfigurata per un ruolo

1. Tenant admin: pagina operativa → tab "Preset" → **Nuovo**
2. Compila codice, descrizione, **ambito="ruolo"**, profilo target
3. Salva il preset (testata)
4. Apri "Gestisci composizione" → seleziona le colonne, riordina,
   imposta visibilità di default → Salva
5. Accendi il preset (`attivo`). Diventa lo standard della lista per gli
   operatori con quel ruolo, e prevale su un preset di emittente (§3). Se il ruolo ha
   già un preset acceso per la lista, il nuovo si prepara spento, e per sostituirlo si
   spegne prima il vecchio (§2.3).

### 10.4 Disattivare temporaneamente una lista

1. SUPER_ADMIN: tab "Definizioni" → modifica la lista → `attivo=false` → Salva
2. La lista scompare dal runtime. Preset, colonne e preferenze restano come sono, accesi
   o spenti: alla riattivazione si riaccende la sola lista, e tutto torna com'era (se
   una colonna non trova più il suo campo nella vista, la riaccensione è rifiutata e il
   messaggio la nomina).

### 10.5 Riallineare una preferenza dopo modifica del preset

Quando l'admin modifica un preset di base (aggiunge una colonna,
cambia l'ordine), il banner "preset aggiornato" lo vedono gli utenti che hanno
personalizzato proprio quella parte: chi ha scelto le sue colonne lo vede quando
cambiano le colonne del preset, non quando cambiano solo le righe per pagina, che gli
arrivano già. Cambiare l'ordinamento di partenza non accende il banner a nessuno: la
lista parte subito col nuovo ordinamento. Le parti che l'utente non ha personalizzato
seguono il preset senza bisogno di nulla. "Vedi novità" apre la modale con le novità,
"Ignora" lo nasconde finché il preset non cambia di nuovo. Salvare un preset senza cambiarlo non accende
niente.

Quando invece il preset da cui l'utente era partito non è più il suo standard (l'admin
l'ha spento, l'ha cancellato, o ha acceso un preset che prevale), il sistema non parla di
"preset aggiornato" ma di "preset di base cambiato": l'utente può riallineare la
preferenza al nuovo standard. Salvare la preferenza è il riallineamento: da quel momento
il preset di partenza è quello nuovo. Il contratto dei due esiti è nella scheda di
[ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config).

### 10.6 Esportare una lista in CSV o Excel

Le liste configurabili espongono nella toolbar "Esporta CSV" ed "Esporta Excel".
Il file contiene:

* le colonne che l'operatore vede, nel suo ordine, tolte le colonne `azione`, quelle
  `esportabile=false` e quelle con permesso `LETTURA`
* le righe dei filtri applicati alla lista (ricerca, utility, stato, ecc.)
* i filtri stessi, allegati al file: nel CSV come prima riga commentata (`#`), in
  Excel come foglio "Filtri applicati"

Il CSV porta il BOM UTF-8, così aprendolo con un doppio click in Excel gli accenti
restano giusti. Sopra le **10.000 righe** l'export è rifiutato con il messaggio
«Raffina i filtri e riprova»: si stringono i filtri, non si alza il tetto. Il
contratto è in [API export liste](/backend/ui/manual/api_export_liste).

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

### 11.2 Cancellazioni protette dal sistema

Per evitare configurazioni stale silenziose, alcune cancellazioni
sono bloccate e ribattute con un messaggio che indica l'alternativa:

* **Cancellare una `lista_definizione` con colonne, preset o preferenze utente**: bloccato dal database. Il messaggio dice che la lista è in uso e invita a disattivarla con `attivo=false`. L'admin sceglie tra disabilitare la lista (mantenendo le configurazioni, §10.4) o ripulire prima i riferimenti.
* **Cancellare una `lista_colonna` citata da preferenze utente o dalla composizione di un preset**: bloccato. Il messaggio invita a disattivarla con `attivo=false`.

In compenso, alcune cancellazioni sono **a cascata intenzionali**:

* Cancellare una `lista_colonna` rimuove automaticamente i suoi permessi
  (`lista_colonna_permesso`).
* Cancellare un `lista_preset` rimuove la composizione (`lista_preset_colonna`) ma le
  preferenze utente che lo avevano come base sopravvivono, senza più il riferimento:
  l'operatore conserva le sue scelte, e il resto viene dal nuovo preset di base (§3).

### 11.3 Liste disattivate e figli attivi

Una lista spenta **sospende** le sue parti senza toccarle: colonne, preset e
preferenze utente restano com'erano, accesi o spenti, e tornano a valere quando la
lista si riaccende. Si possono anche preparare colonne e preset su una lista spenta,
prima di accenderla.

### 11.4 Vincoli automatici — azioni e colonne senza campo

Il database garantisce con due vincoli che le colonne di tipo `azione` (pulsanti UI)
non abbiano un campo sorgente, e che una colonna senza campo sorgente (un'azione, una
colonna composta) non sia esportabile: non ha un valore da esportare. Il drawer
collabora: se selezioni `tipo_colonna='azione'` il toggle "Esportabile" viene forzato
a OFF e disabilitato.

### 11.5 Identificatori e azioni — sempre visibili

Le colonne con `tipo_colonna IN ('identificatore', 'azione')` non sono
nascondibili dall'operatore nella modale di personalizzazione (toggle
disabilitato con tooltip esplicativo), e non scendono mai nella riga di dettaglio
(§7). Servono per coerenza: una lista clienti senza ragione sociale è inutile, e
nascondere i pulsanti modifica rompe l'usabilità.

L'admin può comunque marcare un'`identificatore` con permesso
`BLOCCATO` per un certo profilo: in quel caso la colonna scompare
**prima** di arrivare alla modale (filtro lato database), non viene
nascosta lato UI.

---

### 11.6 Il bollino «multi-emittente» — un'etichetta che si guadagna

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
attrezzata, e si comporta di conseguenza (vedi sotto).

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

Le liste si accendono **una per una**, quando la loro colonna mostra un nome su
dati veri: accenderlo prima che la colonna emittente sia a video aprirebbe
esattamente la finestra che il bollino serve a chiudere.

#### ⛔ Non si accende dall'interfaccia, e nemmeno via API

Il database ha un presidio che **rifiuta la scrittura** su questo campo a
chiunque non sia il processo di migrazione. Non è una questione di permessi
configurabili: non c'è nessun interruttore da aprire, e non esiste un profilo
abbastanza potente da farlo. Il tentativo si ferma con un errore esplicito.

La ragione è che un invariante con l'interruttore non è un invariante. Il campo
si dichiara nel **seed** delle liste, insieme al lavoro che lo giustifica, e
arriva insieme a quello.

Lo stesso presidio tiene le altre due dichiarazioni della lista, che dicono una
cosa del software e non una preferenza: il **perimetro emittente** (spegnerlo
aprirebbe la schermata senza chiedere l'azienda, lo stesso effetto del bollino) e la
**genealogia dei documenti** (la lista riceve la colonna «Transito»). Una lista nuova
creata dall'interfaccia nasce col perimetro, senza bollino e senza genealogia.

#### Che cosa succede a video

Il bollino arriva nella configurazione della lista come chiave `multi_emittente`, e
accanto il backend calcola la conclusione per **quell'utente**:
`richiede_scelta_emittente`. Vale `true` quando la lista ha un perimetro emittente,
non ha il bollino, e l'utente ne vede più di uno senza averne scelto uno: allora la
lista, invece delle righe, chiede di scegliere l'emittente. Il frontend non ricalcola
niente: legge la conclusione.

⚠️ Il bollino **non è un permesso**: non dice che cosa l'utente può vedere (lo decide
il suo perimetro), dice se la schermata è leggibile nella condizione in cui sta per
essere aperta.

#### Il verso opposto: la lista senza perimetro

Una lista dichiarata **senza** perimetro emittente (`perimetro_emittente = false`) —
un catalogo globale, come le famiglie di documento o le liste tecniche di
configurazione — non ha emittenti da dire: si apre senza scegliere l'emittente, e
non per questo vanta il bollino. Non espone colonne che dicono di chi è la riga: se
una colonna attiva legge un campo dell'emittente, la lista ha un perimetro. Le righe
«di sistema» con l'emittente vuoto (preset, modelli standard) non la rendono
globale. Una lista senza perimetro non può avere il bollino acceso (vincolo del
database).

---

## 12. Che cosa le liste oggi non fanno

Limiti dello stato attuale, perché chi legge non li cerchi nell'interfaccia:

* **Una sola personalizzazione per lista**: un operatore ha una preferenza per lista,
  non più viste nominate fra cui passare.
* **Nessuna condivisione**: una personalizzazione resta di chi l'ha fatta; per dare
  una vista a un gruppo si usa un preset di ruolo.
* **Niente colonne calcolate a dato**: un valore derivato è una colonna composta
  (§5.2.2) o una colonna della vista.
* **La priorità di ritiro non si regola dall'interfaccia** (§7.3).
* **La chiave i18n della colonna è un campo di testo libero**: il drawer non propone
  le chiavi esistenti.

---

## 13. Note finali

* **Le definizioni e le colonne hanno valore di catalogo**: il loro
  codice rimane stabile tra ambienti (dev → staging → produzione). Gli
  `id` numerici **non sono stabili**, usare sempre il codice come
  riferimento nei seed e nella documentazione.
* **I preset sono dell'azienda**: un preset di sistema generico, preset di ruolo per
  le esigenze dei reparti, e preset di emittente fiscale per gli operatori il cui
  ruolo non ha un preset proprio (il ruolo prevale, §3).
* **Le preferenze utente sono inviolabili**: nessun admin può
  modificarle direttamente. L'admin modifica il preset di base: le chiavi che
  l'utente non ha personalizzato lo seguono subito, per le altre c'è il banner
  "preset aggiornato". Per tornare allo standard c'è il ripristino dalla modale.
* **Il pattern slot/override** vale ovunque: catalogo (sistema) + preset
  (azienda) + preferenza (utente). Ogni livello sovrascrive il
  precedente chiave per chiave; un livello vuoto eredita dal precedente. Niente
  default hardcoded nel codice.

---
{% include-markdown "signature-core.md" %}
