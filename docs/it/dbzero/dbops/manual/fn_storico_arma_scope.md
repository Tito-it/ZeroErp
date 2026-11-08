## 📘 Documentazione Concettuale – Funzione `dbops.fn_storico_arma_scope`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.storico_scope_policy](/dbzero/dbops/tabelle/storico_scope_policy) — la mappa che decide se la shadow si arma
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — dove finiscono le azioni fatte e i salti
>
> Approfondimento funzioni:
>
> * [dbops.fn_storico_arma_scope_tutte](/dbzero/dbops/funzioni/fn_storico_arma_scope_tutte) — la applica a ogni madre col trigger di storico
> * [dbops.fn_ensure_storico_table](/dbzero/dbops/funzioni/fn_ensure_storico_table) — la chiama sulla shadow appena creata
> * [dbops.fn_storico_backfill_scope](/dbzero/dbops/funzioni/fn_storico_backfill_scope) — attribuisce le versioni già scritte, e completa il `NOT NULL` lasciato aperto qui
> * [script.fn_scope_ef_perimetro](/dbzero/script/funzioni/fn_scope_ef_perimetro) — il predicato della policy di lettura
> * [script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic) — il trigger che scrive le due colonne
>
> Guide:
>
> * [Storicizzazione delle tabelle](/guide/storicizzazione-tabelle) — la sezione «Di chi è una versione»

---

### 🎯 Scopo Principale

Porta la shadow `storico.<tabella>` di una madre alla forma dello scope congelato, aggiungendo solo
ciò che manca: le colonne di origine e di scope con il loro indice, la revoca del `DELETE`
all'applicazione e, se la mappa dice che la madre è protetta, la row level security con le sue tre
policy.

È la **sede unica** di quella forma: la usano sia il generatore, sulla shadow che nasce, sia la
convergenza, sulle shadow che ci sono già.

---

### Che cosa aggiunge

1. **`origine_schema`**, lo schema della madre da cui viene una versione. Il nome della shadow è il
   nome nudo della madre e due madri omonime scrivono nella stessa shadow: senza lo schema due
   documenti con lo stesso `id` si chiuderebbero a vicenda. Su una shadow vuota la colonna nasce
   `NOT NULL`; su una con versioni già scritte resta nullable finché il backfill non le attribuisce.
2. **`scope_emittente_fiscale_id`**, con indice: l'emittente della riga al momento della fotografia.
   Vuoto vuol dire madre non protetta, o versione precedente non attribuibile.
3. **La revoca del `DELETE`** a `zeroerp_app`: uno snapshot non si cancella, la retention è del
   proprietario. I privilegi di default lo darebbero a ogni shadow nuova; qui, dove la shadow
   converge, si toglie.
4. **Se la madre è protetta** (riga di mappa con modo diverso da `NESSUNO`): la row level security
   accesa e tre policy — una di lettura per la veste operatore sull'emittente congelato, e due di
   scrittura, inserimento e aggiornamento, senza filtro.

Le colonne nascono con il loro commento, scritto qui.

---

### ⭐ Perché le policy di scrittura non filtrano

La shadow la scrive il **trigger**, che gira come chi sta scrivendo la madre, cioè l'applicazione.
Con la row level security accesa e la sola policy di lettura, l'inserimento della versione verrebbe
rifiutato e l'aggiornamento che chiude la precedente toccherebbe zero righe **in silenzio**: la
storicizzazione si romperebbe, o peggio tacerebbe. Filtrare la scrittura non difende niente — la
madre ha già la sua RLS — e bloccherebbe le scritture di sistema. La RLS della shadow protegge la
**lettura**; la scrittura la governano i privilegi (inserimento e aggiornamento sì, `DELETE` no).

La policy di lettura calcola il perimetro dell'operatore una volta per istruzione e lo confronta,
riga per riga, con l'emittente congelato.

---

### ⛔ Aggiunge e non toglie

È una rete che converge, non una migrazione:

* non registra niente su una shadow già allineata;
* **non disarma mai**: una shadow condivisa fra una madre protetta e una `NESSUNO` resta armata, e
  una riga di mappa che torna a `NESSUNO` non spegne la RLS;
* una policy si crea **se manca il nome**: una policy che esiste già con un'espressione diversa non
  si riscrive. Cambiare la forma di una policy già armata vuole un changeSet che la riscriva.

---

### ⚠️ Lavora solo chi ha i privilegi del proprietario della shadow

`ALTER TABLE`, `CREATE POLICY` e `REVOKE` li fa il proprietario della tabella. La funzione procede
solo se l'utente corrente **ha i privilegi** del proprietario della shadow: è il proprietario, un
suo membro che ne eredita i privilegi (`INHERIT`), o un superuser. Il controllo è sui privilegi,
non sul nome del ruolo: chi ne porta il nome senza averne i privilegi non basta, e chi li ha senza
portarne il nome sì. Altrimenti scrive un `WARN` nell'audit, non fa niente e restituisce il salto. Non ferma il migrate. Le shadow di un altro proprietario le allinea
`scripts/sql/provision_storico_scope.sql`, da superuser, che ne riassegna anche la proprietà.

Dal momento in cui il generatore cede ogni shadow nuova al proprietario della madre, e i job girano
come il proprietario, il caso resta per un database in cui qualcuno abbia creato shadow da
amministratore.

---

### Che cosa restituisce

Un oggetto con la madre, la shadow, l'esito e le azioni fatte (o, in simulazione, quelle che farebbe).
Gli esiti sono quattro: `ALLINEATA` (ha fatto qualcosa), `GIA_ALLINEATA`, `SKIP_OWNER` (shadow di un
proprietario di cui l'utente corrente non ha i privilegi), `NO_SHADOW` (la madre non ha ancora una shadow: non è un errore). In simulazione
non scrive niente, nemmeno il `WARN` del salto.

---

### Test

* `db/pgtap/storico/test-storico-scope-congelato-v1.sql` — ogni shadow di una madre col trigger ha
  le due colonne; ogni shadow di una madre protetta ha la RLS e le tre policy, e nessuna shadow è
  armata se tutte le sue madri sono `NESSUNO`; la policy di lettura è quella del perimetro per
  istruzione; le policy di scrittura sono senza filtro; una shadow di prova nasce armata e il trigger
  scrive attraverso la RLS; l'applicazione non ha `DELETE` su nessuna shadow.

---

### Note di migrazione

* 2026-09-11 — nasce con lo scope congelato (`brief-db-rls-storico-scope-congelato`, §4b).
* 2026-10-18 — la policy di lettura passa a `script.fn_scope_ef_perimetro`, con il perimetro
  calcolato una volta per istruzione invece che per riga (D-3b-2); le policy già armate le ha
  riscritte un changeSet a parte, perché la funzione non le tocca.
* 2026-11-08 — il proprietario si riconosce dai privilegi (appartenenza con `INHERIT`, o superuser),
  non più dal nome del ruolo.

---

{% include-markdown "signature-core.md" %}
