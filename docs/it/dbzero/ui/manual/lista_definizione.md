## 📘 Documentazione Concettuale – Tabella `ui.lista_definizione`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — le colonne che la lista può mostrare
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — le configurazioni preconfezionate della lista
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — la configurazione personale di ogni utente
>
> Approfondimento viste:
>
> * [dbops.vw_liste_multi_emittente_non_certificate](/dbzero/dbops/views/vw_liste_multi_emittente_non_certificate) — le liste che si dicono multi-emittente senza la colonna dell'emittente
> * [dbops.vw_liste_colonne_campo_orfano](/dbzero/dbops/views/vw_liste_colonne_campo_orfano) — le colonne che leggono un campo che la sorgente non ha
>
> Approfondimento funzioni:
>
> * [ui.fn_lista_da_codice](/dbzero/ui/funzioni/fn_lista_da_codice) — la lista letta dal suo codice, sede unica
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — la configurazione della schermata
> * [ui.fn_lista_relazione_ha_attributo](/dbzero/ui/funzioni/fn_lista_relazione_ha_attributo) — la relazione di una lista ha il campo?
> * [ui.trgfn_ui_lista_definizione_a10_valida_vista_sql](/dbzero/ui/funzioni/trgfn_ui_lista_definizione_a10_valida_vista_sql) — la vista dichiarata esiste, e le colonne la trovano ancora
> * [ui.trgfn_lista_definizione_guard_dichiarazioni](/dbzero/ui/funzioni/trgfn_lista_definizione_guard_dichiarazioni) — le dichiarazioni della lista non le scrive l'applicazione
>
> Guide:
>
> * [Configurazione delle liste](/guide/configurazione-liste) — le liste configurabili raccontate a chi le usa

---

### 🎯 Scopo Principale

`ui.lista_definizione` è il catalogo delle liste configurabili: una riga per ogni schermata a elenco
che l'operatore può personalizzare (quali colonne, in che ordine, con che larghezza, e quante righe
per pagina).

La riga dice come si chiama la lista, da quale vista legge i dati, se le sue righe appartengono a
un'azienda (emittente fiscale), se sa dire da quale azienda arriva ogni riga, se riceve la genealogia
dei documenti e da quanti caratteri parte la sua ricerca libera.

---

### Il codice è l'identificatore della lista, e non si riscrive

Frontend, backend, seed, test e preferenze nominano una lista col suo `codice`, unico
(`uq_ui_lista_definizione_codice`), nella forma `<schema>.<entità>` o `<schema>.<entità>:<contesto>`
per le varianti (un selettore, un riquadro di cruscotto). L'`id` numerico cambia da un ambiente
all'altro e non si usa come riferimento.

Il codice non si cambia dopo la nascita, da nessuno: lo tiene un lucchetto di colonna
(`E_UI_LISTA_CODICE_IMMUTABILE`). Una lista col codice sbagliato si spegne e se ne crea un'altra. Il
seed lo riscrive uguale, e il lucchetto lo ammette.

La forma del codice è una convenzione: nessun vincolo la verifica, e nessun vincolo lega il prefisso
del codice a `schema_dati`. I testi della riga (`codice`, `descrizione`, `schema_dati`, `vista_sql`,
`note`) non sono mai la stringa vuota: l'assenza di un testo opzionale è `NULL`.

---

### La vista dichiarata esiste, nel suo schema

`vista_sql` è il nome della relazione da cui la lista legge, cercata nello schema `schema_dati`: il
nome si scrive senza schema. Sono ammesse viste, viste materializzate, tabelle e tabelle
partizionate. La domanda «la relazione esiste, e ha questo campo?» ha una sede sola,
[fn_lista_relazione_ha_attributo](/dbzero/ui/funzioni/fn_lista_relazione_ha_attributo).

Il controllo lo fa [valida_vista_sql](/dbzero/ui/funzioni/trgfn_ui_lista_definizione_a10_valida_vista_sql)
quando la riga nasce e quando cambiano vista, schema o `attivo`; salta se la vista non è dichiarata o
se la lista è spenta, così una lista si può registrare prima che la sua vista esista, e la vista si
verifica quando la lista si accende.

Una lista senza `vista_sql` legge i dati da una funzione o da un repository del backend: il catalogo
non sa da dove, e le sue colonne non si verificano contro niente.

---

### ⭐ Cambiare vista riverifica le colonne

Quando l'applicazione cambia la vista o lo schema di una lista accesa, o riaccende una lista spenta,
le colonne si riverificano contro la relazione: se una colonna che legge dalla vista, accesa o
spenta, ha un campo che la relazione non ha, il cambio è rifiutato (`E_UI_LISTA_COLONNE_ORFANE`), e
la frase nomina le colonne. Una lista spenta accoglie colonne senza verificarle: la verifica arriva
con la riaccensione.

Il migrate resta fuori da questa verifica: il CSV delle definizioni si carica prima di quello delle
colonne, e un cambio di vista fatto nel seed insieme alle colonne si fermerebbe a metà. Per il seed
giudicano il pgTAP del catalogo e il presidio
[vw_liste_colonne_campo_orfano](/dbzero/dbops/views/vw_liste_colonne_campo_orfano), che vede anche
ciò che nessun trigger di `ui` vede: una vista che perde una colonna con un DDL.

---

### ⭐ Le dichiarazioni della lista: le scrive solo il seed

Tre colonne dichiarano una cosa che solo il software sa, e non sono preferenze dell'installazione:

* `perimetro_emittente` dice la **natura del dato**: le righe di questa lista appartengono a
  un'azienda? Vale `true` per default; le liste globali (vocabolari, liste tecniche) lo dichiarano
  `false`.
* `multi_emittente` dice una **capacità della schermata**: la lista sa dire da quale azienda arriva
  ogni riga? Vale `false` per default: una lista nuova nasce non certificata.
* `legge_lineage` dice che il backend unisce alle righe della lista la **sintesi della genealogia
  dei documenti** (il «transito»): solo su una lista così una colonna può leggere un campo della
  lineage (vedi [lista_colonna](/dbzero/ui/tabelle/lista_colonna)). Vale `false` per default; la
  dichiarano le liste documentali che la mostrano.

Il backend lascia entrare senza scegliere un'azienda chi apre una lista che sa dirlo
(`multi_emittente`) oppure una lista che non ha niente da dire (`perimetro_emittente = false`). Una
lista senza perimetro non può dichiararsi multi-emittente: lo vieta
`chk_ui_lista_definizione_perimetro_coerente`. Nessuna delle due è un permesso: non decidono che
cosa un utente vede (lo decidono lo scope e la row security delle tabelle di dominio), ma se la
schermata è leggibile nella condizione in cui si apre.

Le tre le cambia solo il proprietario della tabella, cioè la migrazione dal CSV del seed, su ogni
riga, anche su quelle create dall'installazione
([guard_dichiarazioni](/dbzero/ui/funzioni/trgfn_lista_definizione_guard_dichiarazioni),
`E_UI_LISTA_DICHIARAZIONE_NON_SCRIVIBILE`). Una lista creata dall'applicazione nasce coi valori che
non promettono niente: perimetro acceso, non certificata, senza lineage.

---

### La soglia della ricerca libera è della lista

`ricerca_min_caratteri` dice da quanti caratteri la ricerca libera filtra: sotto soglia il termine
non si applica. Le tabelle di configurazione a codici corti cercano da 1, gli archivi dalla soglia
di progetto, 3, che è il default. Il valore è obbligatorio e almeno 1
(`chk_ui_lista_definizione_ricerca_min_caratteri`), e i due lettori, la configurazione della
schermata e la ricerca del backend, lo prendono dalla stessa riga, attraverso
[fn_lista_da_codice](/dbzero/ui/funzioni/fn_lista_da_codice). È una regolazione dell'installazione:
l'applicazione la scrive.

---

### Dove si mostra la lista: la sua misura di partenza

`uso_misura` dice dove la lista si mostra: `COMPATTA` in un drawer o in un dialog, `PAGINA` in una
pagina intera, che è il default. Il vocabolario è quello del catalogo delle misure
([misure_pagina](/dbzero/ui/tabelle/misure_pagina), l'enum `ui.uso_misura_pagina`): quando né la
preferenza dell'utente né il preset di base dicono quante righe per pagina, la lista risponde il
default del catalogo per il suo uso. Lo dichiara il CSV del seed, ed è una colonna del software:
sulle liste nate dal seed l'installazione non la cambia.

---

### ⭐ Spegnere una lista la sospende

Una lista spenta non esiste per chi la cerca: `fn_lista_da_codice` risponde
`E_UI_LISTA_NON_TROVATA`, e con lei non rispondono la configurazione della schermata e la ricerca
libera. Le sue colonne, i suoi preset e le preferenze degli utenti restano come sono: le FK verso la
lista sono fra le eccezioni della regola ATTIVO
([automazione_attivo_eccezioni](/dbzero/dbops/tabelle/automazione_attivo_eccezioni)), quindi né lo
spegnimento è bloccato dalle parti accese, né una parte accesa è rifiutata sotto una lista spenta.
Alla riaccensione tutto torna com'era, dopo la verifica delle colonne descritta sopra.

Una lista non si cancella finché ha colonne, preset o preferenze: le tre FK sono senza azione, e il
rifiuto arriva come violazione di vincolo. Il gesto ordinario è lo spegnimento.

---

### Codici errore

* `E_UI_VISTA_SQL_NON_TROVATA` — la vista dichiarata non c'è nello schema della lista.
* `E_UI_LISTA_COLONNE_ORFANE` — l'applicazione cambia vista o riaccende la lista, e una colonna
  resterebbe senza il suo campo.
* `E_UI_LISTA_DICHIARAZIONE_NON_SCRIVIBILE` — l'applicazione scrive una delle tre dichiarazioni.
* `E_UI_LISTA_CODICE_IMMUTABILE` — si riscrive il codice della lista.
* `E_UI_LISTA_NON_TROVATA` — lettura di una lista assente o spenta, da `fn_lista_da_codice`.
* L'unicità del codice, i CHECK «non vuoto», quello di coerenza fra le due colonne dell'azienda,
  quello della soglia e le FK verso la lista arrivano come violazione di vincolo, e il backend le
  traduce per nome.

---

### Test

* `db/pgtap/ui/test-ui-catalogo-liste-v1.sql` — la lista spenta sospende colonne e preset; le
  dichiarazioni rifiutate all'applicazione; il codice che non si riscrive; il cambio di vista e la
  riaccensione che lasciano una colonna orfana; la tabella partizionata; i testi vuoti.
* `db/pgtap/ui/test-lista-colonna-campo-sorgente-in-vista-v1.sql` — ogni lista accesa del catalogo ha
  la sua vista nel suo schema; una vista che esiste solo in un altro schema è rifiutata.
* `db/pgtap/ui/test-lista-definizione-multi-emittente-v1.sql` — l'applicazione non accende il
  contrassegno né crea una lista già accesa; l'elenco per nome delle liste certificate.
* `db/pgtap/ui/test-lista-definizione-perimetro-emittente-v1.sql` — il CHECK di coerenza, l'elenco
  per nome delle liste globali, una lista globale non mostra l'emittente per riga.
* `db/pgtap/ui/test-lista-ricerca-min-caratteri-v1.sql` — default, CHECK, i due lettori della soglia
  e l'elenco per nome delle liste che cercano da 1.
* `db/pgtap/script/test-fn-is-proprietario-tabella-v1.sql` — il guard delle dichiarazioni rifiuta
  l'applicazione anche quando spegne il contrassegno.
* `db/pgtap/ui/test-ui-misure-catalogo-e-uso-v1.sql` — l'uso dichiarato e il ripiego della misura
  sul suo default.
* `db/pgtap/ui/test-ui-nell-ambito-v1.sql` — le FK verso la lista fra le eccezioni ATTIVO.

Gli elenchi per nome valgono anche come regola: chi aggiunge o toglie dal seed una lista globale,
certificata o che cerca da 1 scrive il nome nel test nello stesso giro.

---

### Note di migrazione

* 2026-05-06 — nasce la tabella, col catalogo delle liste configurabili.
* 2026-08-18 — nasce `multi_emittente`, col guard che la toglie all'applicazione.
* 2026-09-02 — nasce `perimetro_emittente`; dal 2026-09-18 si dichiara nel CSV della tabella, non più
  in un CSV a parte.
* 2026-09-25 — nasce `ricerca_min_caratteri`.
* 2026-09-27 — la vista si cerca nel suo schema, non più per solo nome.
* 2026-11-21 — nasce `uso_misura`: la lista dichiara dove si mostra, e la misura ripiega sul default
  di quell'uso.
* 2026-11-21 — nasce `legge_lineage`; il guard delle dichiarazioni copre anche `perimetro_emittente`
  e prende il posto di quello del solo `multi_emittente` (`E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE` è
  ritirato); il codice ha il suo lucchetto; la lista spenta sospende colonne e preset invece di
  bloccare lo spegnimento; cambio di vista e riaccensione riverificano le colonne; ammesse le tabelle
  partizionate; i testi non sono mai vuoti.

---

{% include-markdown "signature-core.md" %}
