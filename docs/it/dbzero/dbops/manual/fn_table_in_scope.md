## 📘 Documentazione Concettuale – Funzione `dbops.fn_table_in_scope`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — i filtri di tabella che la funzione legge
>
> Approfondimento funzioni:
>
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope) — il primo livello, gli schemi; questa funzione lavora dentro quelli
> * [dbops.fn_schema_match](/dbzero/dbops/funzioni/fn_schema_match) — il confronto del bersaglio di una regola, che si applica dopo
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — il framework che usa questo filtro

---

### 🎯 Scopo Principale

Dice se una tabella di uno schema rientra nell'ambito delle automazioni secondo i filtri di
tabella di `dbops.automation_scope`. È il secondo livello dell'ambito: gli schemi li decide
`fn_resolve_scope`, questa funzione decide quali tabelle di uno schema entrano.

La chiamano, in ogni giro, i runner `fn_run_automations_*` (storico, provisioning dello
storico, `tx_id`, audit, attivo, regola del periodo, blocco del `DELETE`, pulizia), i seed
delle automazioni e il censimento delle divergenze dei lock.

---

### Le regole, in ordine

1. **Nessuna tabella dell'ambito, o tabella vuota** → sì: senza elenco non c'è filtro.
2. **Nessuna riga per questo schema** → sì: per uno schema non elencato la decisione è del
   livello schema, non di questo.
3. **Una riga `*all` per lo schema** → sì, tutto lo schema.
4. **Altrimenti** → sì solo se il nome della tabella soddisfa il pattern `LIKE` di almeno una
   riga dello schema.

Il nome dello schema si confronta senza distinguere maiuscole e minuscole; il pattern di
tabella si applica così com'è, maiuscole comprese.

---

### ⚠️ Da sola non delimita niente

La regola 2 risponde «sì» per qualsiasi schema che non compare nell'ambito. Il filtro ha senso
solo **dentro** l'elenco degli schemi di `fn_resolve_scope`: è così che lo usano i runner, che
scorrono le tabelle degli schemi risolti e applicano questo filtro a ciascuna. Chiamata fuori
da quel giro, la funzione dice «in ambito» anche a una tabella di uno schema escluso.

---

### Test

* `db/pgtap/dbops/test-cleanup-framework.sql` — un ambito di `dbops` ristretto a tre tabelle
  di prova: la pulizia vede solo quelle.
* `db/pgtap/dbops/test-registri-dbops-scadenza-v1.sql` e
  `db/pgtap/dbops/test-idempotency-prenota-v1.sql` — i registri di `dbops` con una scadenza
  (`idempotency_keys`, `request_log`, `error_log`, `audit_log`) sono in ambito, quindi la
  pulizia li vede.
* `db/pgtap/script/test-trgfn-guard-date-validita-v1.sql` — il filtro fa parte del perimetro
  su cui si verifica il guard della regola del periodo.

---

{% include-markdown "signature-core.md" %}
