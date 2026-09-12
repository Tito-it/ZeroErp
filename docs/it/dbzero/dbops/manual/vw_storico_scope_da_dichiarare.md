## 📘 Documentazione Concettuale – View `dbops.vw_storico_scope_da_dichiarare`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[dbops.storico_scope_policy](/dbzero/dbops/manual/storico_scope_policy) ·
[dbops.presidi](/dbzero/dbops/manual/presidi)
>
Approfondimenti funzioni:
>
[dbops.fn_storico_risolvi_scope](/dbzero/dbops/manual/fn_storico_risolvi_scope) ·
[dbops.fn_storico_arma_scope](/dbzero/dbops/manual/fn_storico_arma_scope)
>
Guida: [Storicizzazione — Di chi è una versione](/guide/storicizzazione-tabelle)

---
### 🎯 Scopo Principale
(latest review 12-09-2026)

Mostra il **debito della mappa dello scope di storico**: le tabelle storicizzate
per cui nessuno ha ancora detto — o non dice più il vero — da dove si prende
l'emittente che protegge le loro versioni.

> ⚠️ Deve restare **vuota**. Non è un allarme di adesso: è la stessa domanda che
> il controllo automatico fa in CI, portata nel digest settimanale perché si
> veda anche su un database dove la CI non gira.

---

### ⭐ Perché serve, se c'è già il controllo automatico

Il controllo (`db/pgtap/dbops/test-storico-scope-policy-v1.sql`) gira in CI e
ferma una consegna sbagliata. Ma la mappa può invecchiare **senza nessuna
consegna**: una tabella entra in RLS con un cantiere di un altro dominio, una
tabella viene cancellata, la storicizzazione viene tolta. Il controllo se ne
accorge al primo build; il digest se ne accorge la prima settimana, su ogni
database — è la stessa forma di `vw_rls_perimetro_scoperto`.

---

### I tre motivi

| `motivo` | Che cosa dice | Come si chiude |
| --- | --- | --- |
| `SENZA_RIGA` | una tabella **col trigger di storico** non ha una riga nella mappa: nessuno l'ha ancora guardata | si aggiunge la riga al CSV `storico_scope_policy.csv`, col modo giusto — o `NESSUNO` con la ragione |
| `PROTETTA_NESSUNO` | la madre ha la **row level security accesa** ma la mappa dice `NESSUNO`: la sua storia è ancora aperta. La ragione dichiarata è nel `dettaglio` | si passa la riga al modo giusto (EF, SR, PADRE, BA) e la si riarma con `fn_storico_arma_scope` |
| `RIGA_SENZA_MADRE` | una riga di mappa non ha più una madre col trigger: tabella cancellata o storicizzazione tolta | si toglie la riga dal CSV **e** con un changeSet `DELETE` (il mirror non cancella) |

Il marcatore delle madri è il **trigger** (`trgfn_storico_generic`), non il nome
della tabella in `storico`; il confronto con la mappa passa per `to_regclass`, quindi
una riga scritta con maiuscole o spazi diversi non passa per «trovata».

---

### Che cosa NON compare

* le tabelle di `storico` che **non sono shadow** — `comune_trasformazioni` e
  `stradario_trasformazioni` sono i registri delle fusioni di comuni e vie, non
  hanno una madre col trigger e non hanno una riga di mappa: giusto così;
* una riga `NESSUNO` su una madre **senza** RLS: è la dichiarazione corretta,
  non un debito.

---

### Esempio d'uso

```sql
-- Deve tornare zero righe. Se no: motivo, madre, e nel dettaglio la ragione dichiarata.
SELECT motivo, madre, shadow, dettaglio
FROM dbops.vw_storico_scope_da_dichiarare
ORDER BY motivo, madre;
```

Presidio: i test 2, 4 e 5 di `test-storico-scope-policy-v1.sql` asseriscono gli
stessi tre motivi in CI; i test 29-32 provano che **questa vista dica il vero** su
casi costruiti (una madre temporanea col trigger, prima senza riga e poi in RLS
con riga `NESSUNO`; righe di prova come stantie) e che sia a catalogo. In
`dbops.presidi` con natura `ZERO`, cadenza `SETTIMANALE`, registro
`dbops.storico_scope_policy`.
Origine: `docs/it/dev/work-done/brief-db-rls-storico-scope-congelato.md` §4.2, §4c.

---

{% include-markdown "signature-core.md" %}
