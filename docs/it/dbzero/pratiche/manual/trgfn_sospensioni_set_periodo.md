## 📘 Documentazione Concettuale – Funzione `pratiche.trgfn_sospensioni_set_periodo()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [pratiche.sospensioni](/dbzero/pratiche/tabelle/sospensioni)
>
Approfondimento funzioni:
> • [pratiche.trgfn_calcoli_tempo_set_periodo](/dbzero/pratiche/funzioni/trgfn_calcoli_tempo_set_periodo)
> • [pratiche.trgfn_sospensioni_giornale_ins](/dbzero/pratiche/funzioni/trgfn_sospensioni_giornale_ins)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Mantiene `periodo_sospensione` (`tstzrange`) come **proiezione derivata** delle due date
`data_inizio` / `data_fine`. Le date restano la sorgente di verità; il range esiste perché
PostgreSQL sa fare, su un range, cose che su due colonne separate non farebbe:
sovrapposizioni, contenimento, indici GiST.

Non è una colonna di comodo. È **la colonna su cui poggia il vincolo anti-overlap**:

```sql
ex_sospensioni_no_overlap
  USING gist (pratica_id, COALESCE(flusso_id, -1), periodo_sospensione)
```

Se il range smettesse di riflettere le date, l'anti-overlap smetterebbe di difendere il dato
vero — senza che nulla lo segnali.

---

### Aggancio

Trigger `trg_sospensioni_a20_set_periodo_ins_upd` — fase `_a20_`,
`BEFORE INSERT OR UPDATE OF data_inizio, data_fine` su `pratiche.sospensioni`.

---

### Regole applicate

```sql
NEW.periodo_sospensione := tstzrange(
    NEW.data_inizio,
    COALESCE(NEW.data_fine, 'infinity'::timestamptz),
    '[)'
);
```

* `data_inizio` è `NOT NULL` (default `now()`): l'estremo inferiore c'è sempre.
* `data_fine` nulla = **sospensione ancora attiva** → estremo superiore `infinity`.
* Bounds `'[)'`: inizio incluso, fine esclusa — la convenzione standard per intervalli
  contigui, quella che permette a due periodi consecutivi di toccarsi senza sovrapporsi.

Il valore eventualmente passato dal chiamante in `periodo_sospensione` viene **sempre
sovrascritto**: la colonna è derivata, non impostabile.

---

### ⚠️ Le date incoerenti falliscono qui, con un errore tecnico

Il trigger `BEFORE` gira **prima** dei CHECK di tabella. Ne seguono due comportamenti diversi
a seconda di come le date sono sbagliate:

| Caso | Chi parla | Errore |
|------|-----------|--------|
| `data_fine < data_inizio` | **il trigger** | `tstzrange` solleva SQLSTATE `22000` — *range lower bound must be less than or equal to range upper bound* |
| `data_fine = data_inizio` | il CHECK | `chk_sospensioni_data_fine` (`data_fine > data_inizio`, stretto) |

Nel primo caso il CHECK non arriva mai a esprimersi: l'utente riceve un messaggio interno
di PostgreSQL sui range, che **non nomina né la sospensione né le date**. Chi cerca la causa
partendo dal messaggio non trova il vincolo di dominio, perché non è stato lui a fermare
l'operazione.

---

### ⚠️ Il trigger non copre l'`UPDATE` della sola colonna derivata

L'aggancio è `UPDATE OF data_inizio, data_fine`. Un `UPDATE` che tocca **soltanto**
`periodo_sospensione` non lo fa scattare:

```sql
UPDATE pratiche.sospensioni SET periodo_sospensione = '[...)' WHERE id = :id;  -- non risincronizza
```

Il range scritto a mano resta, e da quel momento date e periodo divergono: l'anti-overlap
ragiona sul range falso, le query di dominio sulle date vere. In pratica non capita passando
dall'applicazione, ma è la strada da non prendere in una bonifica manuale — lì si aggiornano
**le date**, e il periodo si ricalcola da sé.

---

### Codici errore

Nessuno di dominio: la funzione non chiama `script.fn_log_and_raise_error`. Gli errori
possibili sono di PostgreSQL (`22000` sul range, violazione di CHECK o dell'EXCLUDE).

---

{% include-markdown "signature-core.md" %}
