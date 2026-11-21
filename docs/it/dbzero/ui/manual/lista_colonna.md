## 📘 Documentazione Concettuale – Tabella `ui.lista_colonna`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — la lista a cui la colonna appartiene
> * [ui.lista_colonna_permesso](/dbzero/ui/tabelle/lista_colonna_permesso) — chi vede la colonna e chi la esporta
> * [ui.lista_preset_colonna](/dbzero/ui/tabelle/lista_preset_colonna) — la colonna dentro un preset
>
> Approfondimento viste:
>
> * [vendite.vw_documento_lineage_sintesi_colonne](/dbzero/vendite/views/vw_documento_lineage_sintesi_colonne) — le colonne della lineage, ammesse come sorgente su ogni lista
>
> Approfondimento funzioni:
>
> * [ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente](/dbzero/ui/funzioni/trgfn_ui_lista_colonna_a10_valida_campo_sorgente) — il campo sorgente esiste nella vista della lista
> * [ui.fn_lista_colonne_livello](/dbzero/ui/funzioni/fn_lista_colonne_livello) — il livello con cui un utente vede ogni colonna
> * [ui.fn_lista_colonne_ricerca_full](/dbzero/ui/funzioni/fn_lista_colonne_ricerca_full) — le colonne della ricerca libera
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — le colonne nella configurazione della schermata
>
> Guide:
>
> * [Configurazione delle liste](/guide/configurazione-liste) — colonne, priorità e ritiro dinamico

---

### 🎯 Scopo Principale

`ui.lista_colonna` è il catalogo delle colonne che ogni lista configurabile può mostrare: per
ciascuna l'etichetta, il campo della vista da cui legge, il tipo di dato e il formato, la posizione
e la larghezza di partenza, e che cosa se ne può fare (filtrare, ordinare, esportare, cercarci,
nasconderla).

---

### Il codice della colonna è la chiave delle preferenze

Una colonna si identifica col suo `codice`, unico nella lista (`uq_ui_lista_colonna_lista_codice`).
Le preferenze degli utenti e la composizione dei preset la ricordano per codice, nel JSONB della
configurazione: cambiare il codice di una colonna la fa sparire dalle preferenze salvate, che la
ritrovano come colonna nuova.

---

### Tre tipi di colonna

* `identificatore` — sempre visibile e fissata a sinistra: la ragione sociale, il numero del
  documento.
* `informazione` — l'operatore la mostra, la nasconde, la sposta e la allarga.
* `azione` — pulsanti e icone. È sempre visibile e non si esporta: lo impone
  `chk_ui_lista_colonna_azione_non_esportabile`.

Visibilità e fissaggio di identificatori e azioni li applica la configurazione della schermata
([fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config)), qualunque cosa dicano
preset e preferenze.

---

### Il campo sorgente esiste nella vista della lista

`campo_sorgente` è il nome della colonna della vista da cui la cella legge. Quando la colonna si
scrive, [valida_campo_sorgente](/dbzero/ui/funzioni/trgfn_ui_lista_colonna_a10_valida_campo_sorgente)
lo cerca nella vista della lista, nel suo schema; è ammesso anche un nome della sintesi della
lineage dei documenti, che il backend unisce alle righe della pagina. Il controllo salta per le
colonne `azione`, per quelle senza sorgente e per le liste senza vista dichiarata.

Una colonna senza sorgente (un'azione, una cella composta dal frontend) ha `campo_sorgente` NULL.

---

### ⛔ L'assenza è `NULL`, mai la stringa vuota

Su `campo_sorgente`, `etichetta_estesa`, `formato`, `gruppo` ed `etichetta_i18n_key` un valore che
manca è `NULL`: un CHECK per colonna rifiuta la stringa vuota e quella di soli spazi. Chi legge
scrive `campo_sorgente IS NOT NULL`, senza tollerare `''`. Nel CSV del seed una cella senza valore
porta il token `NULL`: una cella lasciata vuota, su una colonna di testo, diventa la stringa vuota,
che il vincolo rifiuta.

---

### Che cosa si può fare con la colonna

* `filtrabile`, `ordinabile`, `esportabile`, `ricercabile_full` dicono che cosa la lista ammette
  sulla colonna, qualunque sia la preferenza dell'utente. Valgono `true` i primi tre, `false` la
  ricerca libera.
* `sensibile` cambia il verso dei permessi: una colonna sensibile è nascosta a chi non ha un
  permesso esplicito, le altre sono visibili a chi non ha una restrizione
  ([lista_colonna_permesso](/dbzero/ui/tabelle/lista_colonna_permesso)).
* `etichetta_i18n_key` è la chiave di traduzione dell'etichetta; senza, il frontend mostra
  `etichetta`.
* `gruppo` e `gruppo_ordine` raggruppano le colonne nel pannello di personalizzazione; `formato`
  suggerisce al frontend la resa del valore.

⭐ Il flag `ordinabile` e l'elenco delle colonne su cui il backend ammette l'ordinamento sono una
modifica sola in due posti: si cambiano insieme, e `scripts/gen_seed_lista.py --verifica-ordinamento`
dice se sono allineati.

---

### Una colonna nuova nasce spenta finché il backend non la proietta

Su una lista senza `vista_sql` le celle le riempie il repository del backend. Una colonna nuova con
`campo_sorgente` su quella lista si semina spenta, e la accende il backend nello stesso commit in
cui comincia a proiettare la chiave: accesa prima, la cella sarebbe vuota. Le colonne senza sorgente
nascono accese.

Una colonna accesa chiede una lista accesa: lo verifica, a fine transazione, la regola ATTIVO verso
`lista_definizione` (`E_ATTIVO_PADRE_NON_ATTIVO`).

---

### Il ritiro dinamico segue la priorità

Quando la larghezza non basta, il componente di lista del frontend ritira le colonne in una riga di
espansione invece di far comparire la barra di scorrimento. Ogni colonna pesa la sua
`larghezza_default`; quando la somma supera lo spazio si ritirano prima le colonne a `priorita` più
bassa, a parità quella più a destra (`ordine_default`).

* Più alto vuol dire che resiste più a lungo; il default è 50, e `priorita` non è negativa
  (`chk_ui_lista_colonna_priorita_non_negativa`).
* Identificatori, azioni e colonne fissate non si ritirano mai, qualunque sia il valore.
* La priorità è un attributo del catalogo: preset e preferenze non la cambiano, e la configurazione
  della schermata la rilegge dalla colonna a ogni apertura.

---

### Cancellare una colonna

I permessi della colonna si cancellano con lei (FK con cascata). La presenza in un preset invece la
blocca: la FK di `lista_preset_colonna` verso la colonna è senza azione, e la cancellazione arriva
come violazione di vincolo. Le preferenze degli utenti non hanno FK: il backend conta da sé quelle
che nominano il codice e rifiuta la cancellazione se ce ne sono. Il rimedio, in tutti e due i casi,
è spegnere la colonna.

---

### La lista di una colonna che un preset nomina non cambia

Una riga di un preset nomina la colonna insieme alla lista del preset, e un vincolo composto chiede
che la colonna sia di quella lista. Il vincolo vale da tutti e due i lati: spostare su un'altra lista
una colonna che un preset nomina è rifiutato, come violazione di vincolo. La chiave che il vincolo
legge è l'unicità `uq_ui_lista_colonna_id_lista`, sulla coppia (colonna, lista).

---

### ⚠️ Che cosa oggi non copre

* **Una colonna `azione` può avere un campo sorgente, e nessuno lo verifica.** Il CHECK chiede solo
  che l'azione non sia esportabile; il controllo del campo sorgente salta per le azioni. Un'azione
  con un campo inesistente e `ricercabile_full` acceso entra nelle colonne della ricerca libera, e la
  ricerca interroga un campo che la vista non ha.
* **La sintesi della lineage vale per ogni lista.** Un nome della lineage dei documenti passa il
  controllo su qualunque lista, anche su una che non legge documenti, e il catalogo non sa dire
  quali colonne stanno nella vista e quali no: chi usa `campo_sorgente` per filtrare, ordinare o
  cercare interroga la vista anche per quelle. Il guard di `ui` dipende da una vista di `vendite`.
* **Il codice si cambia.** Nessun lucchetto ferma il `codice` di una colonna, che è la chiave delle
  preferenze e dei preset; il backend lo ammette fra i campi modificabili.
* **Le colonne non si riverificano quando la lista cambia vista**, né quando la vista perde una
  colonna: il controllo scatta solo quando si scrive la colonna. Le vede il presidio pgTAP del
  catalogo, sulle righe del seed.
* **Su una lista spenta con la vista non ancora creata, una colonna con sorgente non entra**: il
  controllo del campo non salta sulle liste spente, a differenza di quello della vista.

---

### Codici errore

* `E_UI_CAMPO_SORGENTE_NON_TROVATO` — il campo sorgente non è nella vista della lista né nella
  sintesi della lineage.
* `E_ATTIVO_PADRE_NON_ATTIVO` — una colonna accesa su una lista spenta, a fine transazione.
* L'unicità del codice nella lista, i CHECK dei testi non vuoti, dell'azione non esportabile e della
  priorità, e le FK arrivano come violazione di vincolo, e il backend le traduce per nome.

---

### Test

* `db/pgtap/ui/test-lista-colonna-campo-sorgente-in-vista-v1.sql` — ogni campo sorgente del catalogo
  sta nella sua vista o nella sintesi della lineage; un campo che esiste solo nell'omonima di un
  altro schema è rifiutato.
* `db/pgtap/ui/test-lista-colonna-testi-non-vuoti-v1.sql` — i cinque CHECK della stringa vuota.
* `db/pgtap/ui/test-fn-lista-colonne-ricerca-full-v1.sql` — attivo, `ricercabile_full`, `sensibile`
  e campo sorgente nella ricerca libera.
* `db/pgtap/vendite/test-colonne-lineage-liste-v1.sql` — le colonne della lineage sulle liste dei
  documenti.
* `db/pgtap/ui/test-ui-legami-preset-v1.sql` — la lista di una colonna che un preset nomina non
  cambia.

---

### Note di migrazione

* 2026-05-06 — nasce la tabella.
* 2026-09-27 — il campo sorgente si cerca nella vista del suo schema, non più per solo nome.
* 2026-10-11 — è ammesso come sorgente anche un nome della sintesi della lineage, uscito dalle viste
  di lista.
* 2026-11-12 — l'assenza di un testo è solo `NULL`: i cinque CHECK della stringa vuota.
* 2026-11-21 — l'unicità (colonna, lista), che il vincolo della composizione dei preset legge: la
  lista di una colonna citata da un preset non cambia più.

---

{% include-markdown "signature-core.md" %}
