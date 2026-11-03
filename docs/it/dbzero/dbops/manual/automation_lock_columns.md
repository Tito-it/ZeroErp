## 📘 Documentazione Concettuale – Tabella `dbops.automation_lock_columns`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — la regola `LOCK_COLUMNS` che dice dove il lock si monta e con che nome
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — l'ambito: una tabella fuori ambito non riceve lock
> * [dbops.lock_columns_conditional](/dbzero/dbops/tabelle/lock_columns_conditional) — i lock che valgono solo in uno stato della riga
>
> Approfondimento funzioni:
>
> * [dbops.fn_lock_columns_divergenze](/dbzero/dbops/funzioni/fn_lock_columns_divergenze) — confronta il lock dichiarato qui con quello vivo
> * [dbops.fn_run_automations_lock_columns](/dbzero/dbops/funzioni/fn_run_automations_lock_columns) — porta il lock vivo a quello dichiarato
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — la funzione del trigger che rifiuta il cambio
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — il giro delle automazioni e le sue regole
> * [Linee guida SQL — 6b, la chiave naturale stabile](/linee-guida-sql#6b-riferimenti-esterni-a-tabelle-di-catalogo-chiave-naturale-stabile) — perché `codice_interno` è bloccato

---

### 🎯 Scopo Principale

Il registro delle colonne che, dopo la nascita della riga, **non si cambiano**: una riga per
colonna, con il codice errore che il rifiuto solleva. Il giro delle automazioni ne ricava un
trigger per tabella su `script.trgfn_lock_columns`.

`codice_interno` non si scrive qui: se la tabella ce l'ha, il lock lo prende sempre, con
`E_CODICE_NON_MODIFICABILE`. Qui stanno le colonne **in più** — un'identità scelta alla nascita
(il magazzino di un inventario, la catena di revisione di un'offerta), un dato che non deve
cambiare significato dopo l'uso (l'aliquota di un codice IVA).

---

### ⛔ Un lock di colonna si dichiara qui, non si scrive a mano

Il trigger lo calcola e lo monta solo il giro, a partire da questo registro. Un
`CREATE TRIGGER` su `script.trgfn_lock_columns` scritto in un changeSet sarebbe un secondo posto
che decide l'elenco delle colonne, e la prima convergenza lo riassorbe: lo toglie e lo ricrea col
nome e gli argomenti del registro.

Un lock che esiste come trigger scritto a mano e che il registro non nomina **ferma** il giro (vedi
sotto): prima di convergere va portato qui. Il censimento si fa sui changelog, non sul database
di sviluppo: un lock scritto a mano può mancare su uno e vivere sull'altro.

---

### Che cosa dice ogni riga

La chiave è (`target_schema`, `target_table`, `column_name`).

* `error_code` — il codice che il trigger solleva quando qualcuno cambia la colonna. ⛔ Dev'essere
  un codice **vivo** di `config.codici_errore`: una riga qui è un punto di chiamata differito, che
  non solleva niente finché il giro non monta il trigger e da allora lo solleva per sempre. Lo
  presidia il controllo (H) di `scripts/sql/guardrail_codice_errore_strutturato.sql`, in CI.
  ⚠️ Il default della colonna è `CODICE_NON_MODIFICABILE`, codice ritirato: una riga che non
  dichiara il codice lo riceve, e la ferma solo il guardrail. Il codice si scrive sempre.
* `exec_mode` — in quale giro il lock **nasce**: `AUTO` in ogni giro, `CI` solo nella convergenza
  del rilascio, `SCHEDULED` solo nel giro notturno. Una colonna già bloccata da un altro giro
  resta bloccata: altrimenti un giro toglierebbe ogni volta ciò che l'altro ha messo.
* `enabled` — vero: la colonna si blocca. Falso: è la **decisione** di togliere il blocco, e il
  giro lo toglie.
* `note` — il perché del lock, per chi legge.

Una riga su una colonna che la tabella non ha è ignorata. E il registro agisce solo sulle tabelle
dell'ambito coperte da una regola `LOCK_COLUMNS` attiva di `dbops.automation_rules_tbl`: su una
tabella che nessuna regola copre, le righe di qui non montano niente.

---

### ⚠️ Riga disattivata e riga mancante non sono la stessa cosa

* Una colonna con una riga `enabled = false` è un blocco che si toglie: la convergenza lo toglie
  senza fermarsi.
* Una colonna bloccata da un trigger vivo che il registro **non nomina affatto** è un lock nato
  fuori dal registro: toglierlo lo cancellerebbe in silenzio. Il giro si ferma con
  `E_LOCK_COLUMNS` prima di qualunque DDL, e nomina tutte le colonne in quella situazione. Il
  rimedio è una riga nel registro, attiva se il lock va tenuto, disattivata se va tolto.

---

### Cambiare una riga cambia il trigger al giro successivo

Il giro **converge**: confronta il lock vivo con quello dichiarato e lo rigenera quando
differisce. Un codice errore cambiato, una colonna aggiunta, una riga disattivata arrivano nel
trigger alla convergenza successiva: a ogni rilascio, nella passata `ci_apply`, e ogni sera col
processo `automations_lock_columns`. Non serve un changeSet che tolga e rimonti il trigger.

---

### Test

* `db/pgtap/dbops/test-lock-columns-convergenza.sql` — su tutto il database nessun lock diverge
  dal registro; una riga disattivata toglie il lock; una colonna aggiunta arriva nel trigger; una
  colonna non nominata ferma il giro; una riga di un altro `exec_mode` non toglie un lock già
  montato e non ne crea uno nuovo.
* Le prove dei singoli lock stanno coi domini: per esempio
  `db/pgtap/vendite/test-ordini-lock-cliente.sql` e
  `db/pgtap/vendite/offerte_commerciali/test-offerte-commerciali-codice-lock.sql`.

---

### Note di migrazione

* 2026-01-10 — nasce col runner dei lock di colonna.
* 2026-09-23 — entrano nel registro i lock scritti a mano nel 2025 e rimasti fuori
  (`catalogo.articoli.codice`, `config.sorgenti.categoria`, `config.iva`, `config.iva_stati`); il
  2026-09-26 quello di `vendite.fatture.natura_doc_id`. Lo stesso mese i trigger che portavano
  ancora negli argomenti il codice ritirato `CODICE_NON_MODIFICABILE` sono stati riallineati
  (`brief-db-codici-ritirati-negli-argomenti-dei-trigger`).
* 2026-09-26 — il giro converge invece di creare solo dove manca, e si ferma sulle colonne che il
  registro non nomina (`brief-db-lock-di-colonna-fuori-registro`). Prima un lock nato una volta
  non si riallineava più, e la funzione ritirata `fn_run_automations_drop_lock_trg` cancellava ogni
  sera anche i lock scritti a mano.

---

{% include-markdown "signature-core.md" %}
