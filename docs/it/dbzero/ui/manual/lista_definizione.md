## 📘 Documentazione Concettuale – Tabella `ui.lista_definizione`

> **Ultimo aggiornamento**: 18 novembre 2026
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
>
> Approfondimento funzioni:
>
> * [ui.fn_lista_da_codice](/dbzero/ui/funzioni/fn_lista_da_codice) — la lista letta dal suo codice, sede unica
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — la configurazione della schermata
> * [ui.trgfn_ui_lista_definizione_a10_valida_vista_sql](/dbzero/ui/funzioni/trgfn_ui_lista_definizione_a10_valida_vista_sql) — la vista dichiarata esiste nel suo schema
> * [ui.trgfn_lista_definizione_guard_multi_emittente](/dbzero/ui/funzioni/trgfn_lista_definizione_guard_multi_emittente) — il contrassegno multi-emittente non lo scrive l'applicazione
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — una lista con colonne o preset accesi non si spegne
>
> Guide:
>
> * [Configurazione delle liste](/guide/configurazione-liste) — le liste configurabili raccontate a chi le usa

---

### 🎯 Scopo Principale

`ui.lista_definizione` è il catalogo delle liste configurabili: una riga per ogni schermata a elenco
che l'operatore può personalizzare (colonne, ordinamento, filtri, righe per pagina).

La riga dice come si chiama la lista, da quale vista legge i dati, se le sue righe appartengono a
un'azienda (emittente fiscale), se sa dire da quale azienda arriva ogni riga, e da quanti caratteri
parte la sua ricerca libera.

---

### Il codice è l'identificatore della lista

Frontend, backend, seed e test nominano una lista col suo `codice`, unico
(`uq_ui_lista_definizione_codice`), nella forma `<schema>.<entità>` o `<schema>.<entità>:<contesto>`
per le varianti (un selettore, un riquadro di cruscotto). L'`id` numerico cambia da un ambiente
all'altro e non si usa come riferimento.

La forma del codice è una convenzione: nessun vincolo la verifica, e nessun vincolo lega il prefisso
del codice a `schema_dati`.

---

### La vista dichiarata esiste, nel suo schema

`vista_sql` è il nome della relazione da cui la lista legge, cercata nello schema `schema_dati`: il
nome si scrive senza schema. Sono ammesse viste, viste materializzate e tabelle.

Il controllo lo fa [valida_vista_sql](/dbzero/ui/funzioni/trgfn_ui_lista_definizione_a10_valida_vista_sql)
quando la riga nasce e quando cambiano vista, schema o `attivo`; salta se la vista non è dichiarata o
se la lista è spenta, così una lista si può registrare prima che la sua vista esista, e la vista si
verifica quando la lista si accende.

Una lista senza `vista_sql` legge i dati da una funzione o da un repository del backend: il catalogo
non sa da dove, e le sue colonne non si verificano contro niente.

---

### ⭐ Due domande sull'azienda, due colonne

* `perimetro_emittente` dice la **natura del dato**: le righe di questa lista appartengono a
  un'azienda? Vale `true` per default; le liste globali (vocabolari, liste tecniche) lo dichiarano
  `false`.
* `multi_emittente` dice una **capacità della schermata**: la lista sa dire da quale azienda arriva
  ogni riga? Vale `false` per default: una lista nuova nasce non certificata.

Il backend lascia entrare senza scegliere un'azienda chi apre una lista che sa dirlo
(`multi_emittente`) oppure una lista che non ha niente da dire (`perimetro_emittente = false`). Una
lista senza perimetro non può dichiararsi multi-emittente: lo vieta
`chk_ui_lista_definizione_perimetro_coerente`.

Nessuna delle due è un permesso: non decidono che cosa un utente vede (lo decidono lo scope e la row
security delle tabelle di dominio), ma se la schermata è leggibile nella condizione in cui si apre.

Il contrassegno `multi_emittente` lo cambia solo il proprietario della tabella, cioè la migrazione:
dall'applicazione è rifiutato
([guard_multi_emittente](/dbzero/ui/funzioni/trgfn_lista_definizione_guard_multi_emittente)).
`perimetro_emittente` e `ricerca_min_caratteri` si dichiarano anch'essi nel seed, ma nessun trigger
lo impone (vedi sotto).

---

### La soglia della ricerca libera è della lista

`ricerca_min_caratteri` dice da quanti caratteri la ricerca libera filtra: sotto soglia il termine
non si applica. Le tabelle di configurazione a codici corti cercano da 1, gli archivi dalla soglia
di progetto, 3, che è il default. Il valore è obbligatorio e almeno 1
(`chk_ui_lista_definizione_ricerca_min_caratteri`), e i due lettori, la configurazione della
schermata e la ricerca del backend, lo prendono dalla stessa riga, attraverso
[fn_lista_da_codice](/dbzero/ui/funzioni/fn_lista_da_codice).

---

### ⚠️ Spegnere una lista chiede prima di spegnerne colonne e preset

Una lista spenta non esiste per chi la cerca: `fn_lista_da_codice` risponde
`E_UI_LISTA_NON_TROVATA`. Lo spegnimento però è bloccato finché la lista ha colonne o preset accesi
(`E_ATTIVO_BLOCK_CHILDREN_ACTIVE`, regola ATTIVO verso `lista_colonna` e `lista_preset`): per
spegnerla si spengono prima tutte le sue colonne e i suoi preset, e alla riaccensione ognuno va
riacceso a mano. Le preferenze degli utenti non bloccano: sono uno stato dell'utente, non un figlio
della lista.

Una lista non si cancella finché ha colonne, preset o preferenze: le tre FK sono senza azione, e il
rifiuto arriva come violazione di vincolo.

---

### ⚠️ Che cosa oggi non copre

* **Spegnere una lista non la sospende.** Il blocco verso colonne e preset obbliga a spegnerli tutti
  prima, e alla riaccensione non resta traccia di quali erano accesi. La guida descrive lo
  spegnimento della lista come un gesto unico, che lascia colonne e preset come sono.
* **`perimetro_emittente` lo scrive anche l'applicazione.** `zeroerp_app` ha UPDATE sulla tabella e
  nessun trigger sorveglia la colonna: portarla a `false` su una lista con dati di più aziende apre
  la schermata senza chiedere l'azienda, che è lo stesso effetto che il guard impedisce su
  `multi_emittente`. Lo stesso vale, con effetti minori, per `ricerca_min_caratteri`.
* **Il codice e la vista si cambiano sotto il contrassegno.** Il guard guarda solo
  `multi_emittente`: un UPDATE di `codice`, `vista_sql` o `schema_dati` di una lista certificata
  porta la certificazione su un'altra schermata o su un'altra vista. Il backend ammette il cambio di
  `codice`, `schema_dati` e `vista_sql` dalla pagina tecnica.
* **Cambiare vista non riverifica le colonne.** Il controllo delle colonne scatta quando si scrive
  una colonna, non quando la lista cambia vista o schema: le colonne vecchie restano, anche se la
  vista nuova non le ha. Le vede solo il presidio pgTAP del catalogo, sulle righe del seed.
* **Le tabelle partizionate non sono ammesse come sorgente.** Il controllo accetta viste, viste
  materializzate e tabelle semplici: una lista su una tabella partizionata è rifiutata.
* **La stringa vuota passa.** A differenza di `lista_colonna`, nessun vincolo rifiuta `''` su
  `vista_sql`, `note`, `descrizione` o `schema_dati`. Una `vista_sql` vuota su una lista spenta
  entra, e poi fa rifiutare ogni colonna con sorgente.

---

### Codici errore

* `E_UI_VISTA_SQL_NON_TROVATA` — la vista dichiarata non c'è nello schema della lista.
* `E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE` — l'applicazione scrive il contrassegno multi-emittente.
* `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` — spegnimento di una lista con colonne o preset accesi.
* `E_UI_LISTA_NON_TROVATA` — lettura di una lista assente o spenta, da `fn_lista_da_codice`.
* L'unicità del codice, il CHECK di coerenza fra le due colonne dell'azienda, quello della soglia e
  le FK verso la lista arrivano come violazione di vincolo, e il backend le traduce per nome.

---

### Test

* `db/pgtap/ui/test-lista-colonna-campo-sorgente-in-vista-v1.sql` — ogni lista accesa del catalogo ha
  la sua vista nel suo schema; una vista che esiste solo in un altro schema è rifiutata.
* `db/pgtap/ui/test-lista-definizione-multi-emittente-v1.sql` — l'applicazione non accende il
  contrassegno né crea una lista già accesa; l'elenco per nome delle liste certificate.
* `db/pgtap/ui/test-lista-definizione-perimetro-emittente-v1.sql` — il CHECK di coerenza, l'elenco
  per nome delle liste globali, una lista globale non mostra l'emittente per riga.
* `db/pgtap/ui/test-lista-ricerca-min-caratteri-v1.sql` — default, CHECK, i due lettori della soglia
  e l'elenco per nome delle liste che cercano da 1.
* `db/pgtap/script/test-fn-is-proprietario-tabella-v1.sql` — il guard del contrassegno rifiuta
  l'applicazione anche quando lo spegne.

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

---

{% include-markdown "signature-core.md" %}
