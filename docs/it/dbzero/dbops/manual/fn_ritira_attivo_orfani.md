## 📘 Documentazione Concettuale – Funzione `dbops.fn_ritira_attivo_orfani`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_trigger_attivo_orfani](/dbzero/dbops/funzioni/fn_trigger_attivo_orfani) — il lettore unico degli orfani, da cui prende l'elenco
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — il motore che la chiama in testa a ogni giro
> * [dbops.fn_ritira_attivo_eccezioni](/dbzero/dbops/funzioni/fn_ritira_attivo_eccezioni) — il ritiro gemello, per le FK dichiarate eccezione
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §4.2, gli orfani

---

### 🎯 Scopo Principale

Toglie i trigger ATTIVO che nominano una tabella o una colonna che non esiste più, e restituisce
quanti ne ha tolti. L'elenco lo prende da `dbops.fn_trigger_attivo_orfani`: i motivi
`TABELLA_ASSENTE` e `COLONNA_ASSENTE`.

Chi elimina una tabella non deve ricordarsi dei block sui suoi padri: senza questo ritiro, un
block rimasto senza figlia rifiuterebbe ogni disattivazione del padre con
`E_ATTIVO_BLOCK_FKCOL_NOT_FOUND`.

---

### ⛔ Gli argomenti insufficienti restano

Un trigger con meno argomenti del minimo (`ARGOMENTI_INSUFFICIENTI`) non è un residuo: è un
errore di scrittura. Il ritiro non lo tocca, lo segnala il presidio e lo corregge una persona.

---

### Chi la chiama e quando trova qualcosa

`dbops.fn_run_automations_attivo`, in testa a ogni giro e solo fuori dal dry run, accanto a
`dbops.fn_ritira_attivo_eccezioni`: chi genera ritira anche i trigger rimasti senza figlia.

* In CI non trova niente: la passata `ci_apply` gira dopo i `DROP`, e il generatore non crea mai un
  orfano.
* Su un database di sviluppo pulisce al primo giro del job `automations_attivo`, o subito con la
  sua procedura lanciata a mano.

È un `DROP TRIGGER IF EXISTS` per trigger: rilanciarla è innocuo. Per ogni trigger tolto emette un
avviso con nome, tabella, motivo e dettaglio. È `SECURITY INVOKER`: la chiamano il migratore o il
job, proprietari delle tabelle.

---

### Test

* `db/pgtap/dbops/test-trigger-attivo-orfani-v1.sql` — il ritiro toglie i due orfani della
  fixture, lascia `ARGOMENTI_INSUFFICIENTI` e i trigger validi (compreso un require polimorfo senza
  FK), dopo il ritiro il padre si spegne, e il generatore lo chiama fuori dal dry run.

---

### Note di migrazione

* 2026-10-21 — nasce insieme al lettore degli orfani (`brief-be-utenti-di-sviluppo` §9.5): un
  `DROP TABLE` della figlia lasciava il block sul padre, e ogni disattivazione del padre si fermava.

---

{% include-markdown "signature-core.md" %}
