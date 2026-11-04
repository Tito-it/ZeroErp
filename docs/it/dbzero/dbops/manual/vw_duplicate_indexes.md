## 📘 Documentazione Concettuale – Vista `dbops.vw_duplicate_indexes`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — gli schemi in cui la vista cerca
> * [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy) — da guardare prima di togliere un indice governato dall'automazione
>
> Approfondimento viste:
>
> * [dbops.vw_indici_ridondanti_prefisso](/dbzero/dbops/views/vw_indici_ridondanti_prefisso) — la sorella: la ridondanza per prefisso, che qui non si vede
> * [dbops.vw_fk_con_indice_missing_policy](/dbzero/dbops/views/vw_fk_con_indice_missing_policy) — gli indici dedicati alle chiavi esterne ancora senza policy
>
> Guide:
>
> * [Linee guida SQL — indici ridondanti](/linee-guida-sql#86-gestione-indici-ridondanti) — le due forme di ridondanza e come si rimuovono

---

### 🎯 Scopo Principale

Gli **indici duplicati esatti** degli schemi di `dbops.automation_scope`: gruppi di indici sulla
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
mettere il flag nella firma lo renderebbe invisibile. Il flag decide invece l'**ordine** del gruppo:
`indice_da_tenere` è sempre la UNIQUE, quando c'è; a parità, il più vecchio.

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
  vista per prefisso), un `DROP` secco viene annullato al primo `migrate`: prima si spegne il flag in
  `dbops.fk_index_policy`.
* `indici_da_droppare` non esclude gli indici che sostengono un vincolo né la `REPLICA IDENTITY`: fra
  due UNIQUE identiche può proporre di togliere quella che regge un vincolo. Prima di toglierlo si
  verifica che sia solo un acceleratore.

---

### Test

* `db/pgtap/dbops/test-indici-letture-trasversali-v1.sql`, test 10 — nessuno degli indici delle
  letture trasversali è un duplicato esatto.

---

### Note di migrazione

* 2026-07-27 — il raggruppamento passa dalla sola lista di colonne alla firma normalizzata. Prima la
  vista segnalava diciannove gruppi, di cui sedici falsi: GIN contro btree, UNIQUE parziali disgiunte,
  e indici con espressioni letti come indici a una colonna.
* 2026-09-01 — un UNIQUE con espressioni sostitutive del nullo su colonne obbligatorie, gemello di
  un altro UNIQUE, viene tolto a mano: è il caso di equivalenza che la vista non vede.

---

{% include-markdown "signature-core.md" %}
