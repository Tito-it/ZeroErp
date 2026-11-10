## 📘 Documentazione Concettuale – Vista `dbops.vw_duplicate_indexes`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy) — da guardare prima di togliere un indice governato dall'automazione
>
> Approfondimento viste:
>
> * [dbops.vw_indici_ridondanti_prefisso](/dbzero/dbops/views/vw_indici_ridondanti_prefisso) — la sorella: la ridondanza per prefisso, che qui non si vede
>
> Approfondimento funzioni:
>
> * [dbops.fn_indici_schema_nell_ambito](/dbzero/dbops/funzioni/fn_indici_schema_nell_ambito) — gli schemi in cui la vista cerca
>
> Guide:
>
> * [Linee guida SQL — indici ridondanti](/linee-guida-sql#86-gestione-indici-ridondanti) — le due forme di ridondanza e come si rimuovono

---

### 🎯 Scopo Principale

Gli **indici duplicati esatti** degli schemi governati dalla politica degli indici
(`dbops.fn_indici_schema_nell_ambito`): gruppi di indici sulla
stessa tabella che, a parità di tutto ciò che conta, sono intercambiabili. Per ogni gruppo dice
quale tenere (`indice_da_tenere`) e quali togliere (`indici_da_droppare`).

Un indice di troppo costa una scrittura in più a ogni inserimento, modifica e cancellazione sulla
tabella, e lavoro di manutenzione che non ripaga mai.

---

### 🔑 Duplicato vuol dire «stessa definizione, nome a parte»

Il raggruppamento avviene per **firma**: la definizione dell'indice privata del nome, dei parametri
di storage e del tablespace. Resta tutto ciò che decide quali query l'indice sa servire: metodo,
colonne ed espressioni, classe di operatori, collation, ordinamento, trattamento dei nulli, colonne
`INCLUDE`, predicato. Due indici con la stessa firma sono equivalenti per definizione.

⭐ **Il flag UNIQUE sta fuori dalla firma, apposta.** Un btree non unico identico a una UNIQUE è
ridondante al cento per cento — la UNIQUE serve le stesse query e in più impone il vincolo — e
mettere il flag nella firma lo renderebbe invisibile. Il flag decide invece l'**ordine** del gruppo,
insieme ai vincoli (vedi sotto): a parità, si tiene il più vecchio.

---

### ⛔ Un indice che regge un vincolo non si propone per il `DROP`

Un indice regge un vincolo quando lo sostiene (una `UNIQUE` o un `EXCLUDE` dichiarati come
vincolo), quando una chiave esterna lo usa come riferito, o quando è la `REPLICA IDENTITY` della
tabella. Toglierlo vorrebbe dire togliere il vincolo, o romperlo.

L'ordine del gruppo è quindi: prima gli indici che reggono un vincolo, poi le UNIQUE, poi il più
vecchio. `indice_da_tenere` è il primo, e `indici_da_droppare` non contiene **mai** un indice di
vincolo, nemmeno quando nel gruppo ce n'è più d'uno: in quel caso propone solo gli altri, e un
gruppo fatto di soli indici di vincolo non propone niente. Un gruppo così resta visibile: dice che
due vincoli si sovrappongono, ed è una scelta di progetto, non una pulizia.

---

### ⚠️ Che cosa non è un duplicato

| Caso | Perché convivono |
| --- | --- |
| un GIN trigram e un btree sulla stessa colonna | servono query diverse: ricerca per sottostringa contro uguaglianza e ordinamento |
| due UNIQUE parziali con predicati disgiunti | ognuna vale su un sottoinsieme diverso di righe |
| due indici che differiscono per un'espressione | la firma confronta le espressioni, non le sole colonne sottostanti |

---

### ⛔ Che cosa questa vista non può vedere

* **La ridondanza per prefisso**: un indice su una colonna reso inutile da uno su quella colonna e
  un'altra. Non è un duplicato — le colonne differiscono — e nessun affinamento della firma lo
  catturerà mai: lo vede `dbops.vw_indici_ridondanti_prefisso`. Le due viste si usano insieme.
* **Gli indici uguali alla chiave primaria**: la chiave primaria non entra nel confronto, quindi un
  btree identico a lei non forma un gruppo qui. Lo vede la vista per prefisso, che ammette la chiave
  primaria come indice coprente.
* **L'equivalenza che dipende dai dati o dai vincoli**: due indici che si equivalgono solo perché le
  colonne sono obbligatorie (un'espressione che sostituisce il nullo su una colonna che nullo non è
  mai) hanno firme diverse e non compaiono.

---

### ⚠️ Prima di togliere un indice del gruppo

* Se l'indice è governato dall'automazione delle chiavi esterne (`origine = 'AUTOMAZIONE_FK'` nella
  vista per prefisso), un `DROP` secco viene annullato al primo `migrate` se la sua riga è
  `CON_INDICE`: la riga si porta a `SENZA_INDICE` nel CSV di `dbops.fk_index_policy`.

---

### Test

* `db/pgtap/dbops/test-indici-letture-trasversali-v1.sql`, test 10 — nessuno degli indici delle
  letture trasversali è un duplicato esatto.
* `db/pgtap/dbops/test-vw-duplicate-indexes-vincoli-v1.sql` — fra due UNIQUE identiche si tiene
  quella di vincolo anche se è nata dopo, e si propone l'altra; la replica identity si tiene; due
  indici di vincolo identici non danno proposte di `DROP`.

---

### Note di migrazione

* 2026-07-27 — il raggruppamento passa dalla sola lista di colonne alla firma normalizzata. Prima la
  vista segnalava diciannove gruppi, di cui sedici falsi: GIN contro btree, UNIQUE parziali disgiunte,
  e indici con espressioni letti come indici a una colonna.
* 2026-09-01 — un UNIQUE con espressioni sostitutive del nullo su colonne obbligatorie, gemello di
  un altro UNIQUE, viene tolto a mano: è il caso di equivalenza che la vista non vede.
* 2026-11-08 — gli indici che reggono un vincolo o la replica identity si tengono per primi e non
  si propongono mai per il `DROP`: prima la vista poteva proporre di togliere la UNIQUE di un vincolo.
* 2026-11-09 — il perimetro viene da `fn_indici_schema_nell_ambito`, il building block della politica
  degli indici, al posto della stessa lettura scritta in linea (`20261110-46`,
  brief-db-revisione-dbops, giro 10d). Il significato non cambia.

---

{% include-markdown "signature-core.md" %}
