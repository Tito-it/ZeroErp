## 📘 Documentazione Concettuale – Tabella `ui.lista_colonna`

> **Ultimo aggiornamento**: 24 novembre 2026
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
> * [vendite.vw_documento_lineage_sintesi_colonne](/dbzero/vendite/views/vw_documento_lineage_sintesi_colonne) — le colonne della sintesi della lineage, che una colonna LINEAGE può leggere
> * [dbops.vw_liste_colonne_campo_orfano](/dbzero/dbops/views/vw_liste_colonne_campo_orfano) — le colonne che leggono un campo che la sorgente non ha
>
> Approfondimento funzioni:
>
> * [ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente](/dbzero/ui/funzioni/trgfn_ui_lista_colonna_a10_valida_campo_sorgente) — il campo sorgente esiste dove la colonna dice di leggerlo
> * [ui.fn_lista_relazione_ha_attributo](/dbzero/ui/funzioni/fn_lista_relazione_ha_attributo) — la relazione di una lista ha il campo?
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

### Il codice della colonna è la chiave delle preferenze, e non si riscrive

Una colonna si identifica col suo `codice`, unico nella lista (`uq_ui_lista_colonna_lista_codice`).
Le preferenze degli utenti e la composizione dei preset la ricordano per codice, nel JSONB della
configurazione: per questo il codice non si cambia dopo la nascita, da nessuno (lucchetto di colonna,
`E_UI_COLONNA_CODICE_IMMUTABILE`), e la colonna non cambia lista (lo stesso lucchetto, su `lista_id`).
Una colonna col codice sbagliato, o nella lista sbagliata, si spegne e se ne crea un'altra; il seed
li riscrive uguali, e il lucchetto lo ammette.

---

### Tre tipi di colonna

* `identificatore` — sempre visibile e fissata a sinistra: la ragione sociale, il numero del
  documento.
* `informazione` — l'operatore la mostra, la nasconde, la sposta e la allarga.
* `azione` — pulsanti e icone. È sempre visibile, non ha campo sorgente
  (`chk_ui_lista_colonna_azione_senza_campo`) e quindi non si esporta (vedi sotto).

Visibilità e fissaggio di identificatori e azioni li applica la configurazione della schermata
([fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config)), qualunque cosa dicano
preset e preferenze.

---

### ⭐ Il campo sorgente, e da dove si legge

`campo_sorgente` è il nome del campo da cui la cella legge, e `origine_campo` dice dove sta:

* `VISTA` (il default) — un attributo della relazione della lista, nel suo schema. Quando la colonna
  si scrive,
  [valida_campo_sorgente](/dbzero/ui/funzioni/trgfn_ui_lista_colonna_a10_valida_campo_sorgente) lo
  cerca lì, con [fn_lista_relazione_ha_attributo](/dbzero/ui/funzioni/fn_lista_relazione_ha_attributo).
  Il controllo salta per le liste senza vista dichiarata e per le liste spente: una lista spenta si
  verifica quando si riaccende, e allora un cambio di vista o una riaccensione che lascerebbero la
  colonna senza il campo sono rifiutati (vedi [lista_definizione](/dbzero/ui/tabelle/lista_definizione)).
* `LINEAGE` — una colonna della sintesi della genealogia dei documenti, che il backend unisce alle
  righe della pagina (il «transito»). La vista non la porta, quindi la colonna sta solo su una lista
  che dichiara `legge_lineage` (`E_UI_LINEAGE_NON_DICHIARATA`), e non è filtrabile, ordinabile né
  ricercabile (`chk_ui_lista_colonna_lineage_solo_mostrata`): filtro, ordinamento e ricerca
  interrogano la vista. Il nome lo verifica il presidio
  [vw_liste_colonne_campo_orfano](/dbzero/dbops/views/vw_liste_colonne_campo_orfano), non il guard:
  il catalogo delle liste non dipende da una vista di `vendite`.

Una colonna senza sorgente (un'azione, una cella composta dal frontend) ha `campo_sorgente` NULL, e
non si esporta: non ha un valore da esportare (`chk_ui_lista_colonna_senza_campo_non_esportabile`).

Dopo la scrittura della colonna nessun trigger vede la vista che perde un campo con un DDL: lo vede
il presidio, che confronta ogni lista accesa con la sua relazione.

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

---

### Dove va il vuoto quando la lista ordina

`vuoto_ordinato_come_massimo` dice dove stanno le righe con la cella vuota quando la lista ordina per
la colonna. `false`, il default, è la regola generale: il vuoto conta come il valore più piccolo, il
«non ancora» (il numero di una bozza, una data di evasione che non è arrivata). `true` lo dichiara la
colonna il cui vuoto vuol dire «senza fine», come una fine validità o una scadenza che non c'è: il
vuoto conta come il più grande, in qualunque verso. Il backend legge la dichiarazione dal catalogo e
la applica all'ordinamento della lista: non vale per i filtri.

* Ogni colonna accesa su `valido_al` la dichiara: è la convenzione di tutto il database, dove
  `valido_al` NULL vuol dire «aperto» (linee guida SQL §7b), e il test del catalogo la controlla.
  Anche quando la colonna di origine non può essere vuota: lì la dichiarazione non cambia niente.
* La dichiarazione è del dato, non di ciò che la lista permette: resta anche su una colonna che non
  si ordina, e torna utile se l'ordinamento si riaccende. Chiede invece un campo sorgente
  (`chk_ui_lista_colonna_vuoto_massimo_con_campo`): una colonna senza valore non ha un vuoto da
  ordinare.
* Si scrive solo dal seed del catalogo, come la priorità: il drawer delle colonne non la mostra.

---

⭐ Il flag `ordinabile` e l'elenco delle colonne su cui il backend ammette l'ordinamento sono una
modifica sola in due posti: si cambiano insieme, e `scripts/gen_seed_lista.py --verifica-ordinamento`
dice se sono allineati.

---

### Una colonna nuova nasce spenta finché il backend non la proietta

Su una lista senza `vista_sql` le celle le riempie il repository del backend. Una colonna nuova con
`campo_sorgente` su quella lista si semina spenta, e la accende il backend nello stesso commit in
cui comincia a proiettare la chiave: accesa prima, la cella sarebbe vuota. Le colonne senza sorgente
nascono accese.

Una colonna accesa sta anche su una lista spenta: la lista spenta sospende le sue colonne senza
toccarle, e la FK verso la lista è fra le eccezioni della regola ATTIVO.

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
come violazione di vincolo, e il rimedio è spegnere la colonna. Le preferenze degli utenti non
hanno FK: quando la colonna si cancella, la sua voce esce dalle preferenze della lista che la
nominano ([ui.trgfn_voce_ritira_dalle_preferenze](/dbzero/ui/funzioni/trgfn_voce_ritira_dalle_preferenze)),
e la persona continua a salvare le sue scelte. Se la colonna era l'unica voce della preferenza, le
colonne tornano a seguire il preset. ⚠️ Il backend oggi conta da sé le preferenze che nominano il
codice e rifiuta la cancellazione se ce ne sono: è una regola sua, che il database non chiede più.

---

### La lista di una colonna che un preset nomina non cambia

Una riga di un preset nomina la colonna insieme alla lista del preset, e un vincolo composto chiede
che la colonna sia di quella lista. Il vincolo vale da tutti e due i lati: spostare su un'altra lista
una colonna che un preset nomina è rifiutato. Prima ancora del vincolo parla il lucchetto di
`lista_id` (`E_UI_COLONNA_CODICE_IMMUTABILE`), che vale per ogni colonna: le preferenze la citano per
codice nella sua lista. La chiave che il vincolo legge è l'unicità `uq_ui_lista_colonna_id_lista`,
sulla coppia (colonna, lista).

---

### Codici errore

* `E_UI_CAMPO_SORGENTE_NON_TROVATO` — il campo di una colonna `VISTA` non è nella relazione della
  lista.
* `E_UI_LINEAGE_NON_DICHIARATA` — una colonna `LINEAGE` su una lista che non dichiara la lineage.
* `E_UI_COLONNA_CODICE_IMMUTABILE` — si riscrive il codice della colonna, o la si sposta su un'altra
  lista.
* L'unicità del codice nella lista, i CHECK dei testi non vuoti, dell'azione senza campo, della
  colonna senza campo non esportabile, della colonna della lineage, della priorità e del vuoto
  dichiarato senza campo, e le FK
  arrivano come violazione di vincolo, e il backend le traduce per nome.

---

### Test

* `db/pgtap/ui/test-lista-colonna-campo-sorgente-in-vista-v1.sql` — ogni campo sorgente del catalogo
  sta dove la colonna dice di leggerlo; un campo che esiste solo nell'omonima di un altro schema è
  rifiutato.
* `db/pgtap/ui/test-ui-catalogo-liste-v1.sql` — azione senza campo, composta non esportabile, la
  colonna della lineage, il codice che non si riscrive, la colonna accolta su una lista spenta, il
  presidio che vede il campo tolto con un DDL, il livello con la veste NULL.
* `db/pgtap/ui/test-lista-colonna-testi-non-vuoti-v1.sql` — i cinque CHECK della stringa vuota.
* `db/pgtap/ui/test-fn-lista-colonne-ricerca-full-v1.sql` — attivo, `ricercabile_full`, `sensibile`
  e campo sorgente nella ricerca libera.
* `db/pgtap/vendite/test-colonne-lineage-liste-v1.sql` — le colonne della lineage sulle liste dei
  documenti.
* `db/pgtap/ui/test-ui-legami-preset-v1.sql` — la lista di una colonna che un preset nomina non
  cambia.
* `db/pgtap/ui/test-lista-colonna-vuoto-ordinato-come-massimo-v1.sql` — il default, il vincolo del
  campo sorgente, le colonne dichiarate, la convenzione di `valido_al`.
* `db/pgtap/ui/test-ui-ritiro-voce-preferenze-v1.sql` — la colonna cancellata esce dalle preferenze
  della lista; la colonna non cambia lista.

---

### Note di migrazione

* 2026-05-06 — nasce la tabella.
* 2026-09-27 — il campo sorgente si cerca nella vista del suo schema, non più per solo nome.
* 2026-10-11 — è ammesso come sorgente anche un nome della sintesi della lineage, uscito dalle viste
  di lista.
* 2026-11-12 — l'assenza di un testo è solo `NULL`: i cinque CHECK della stringa vuota.
* 2026-11-21 — l'unicità (colonna, lista), che il vincolo della composizione dei preset legge: la
  lista di una colonna citata da un preset non cambia più.
* 2026-11-21 — nasce `origine_campo`: la lineage non è più ammessa per nome su ogni lista, ma solo
  sulle colonne `LINEAGE` delle liste che la dichiarano. Un'azione non ha campo, una colonna senza
  campo non si esporta (il CHECK delle azioni non esportabili si ritira, coperto dai due nuovi); il
  codice ha il suo lucchetto; una colonna sta accesa anche su una lista spenta.
* 2026-11-22 — la colonna cancellata esce dalle preferenze che la nominano (prima la preferenza restava
  con il codice, e il guard di forma ne rifiutava ogni salvataggio); anche la lista della colonna ha
  il suo lucchetto.

---

{% include-markdown "signature-core.md" %}
