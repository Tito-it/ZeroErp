## 📘 Documentazione Concettuale – Funzione `catalogo.fn_riattiva_articolo()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento trigger / funzioni correlate:
> [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children)
> [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent)
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

### 🎯 Scopo Principale

(latest review 28-04-2026)

`catalogo.fn_riattiva_articolo(p_articolo_id)` e' un **endpoint atomico DB**
per riattivare un articolo precedentemente disattivato. Esegue solo l'UPDATE
sul **padre** (articolo); i **figli** (righe `articoli_uom_operativa`,
`articoli_componenti` dove l'articolo e' componente, ecc.) restano nello
stato in cui erano: l'admin li riattiva esplicitamente in azioni successive.

E' la controparte semantica della disattivazione, che invece **non** e'
incapsulata in una fn -- resta UPDATE diretto, gia' coperto dal trigger
[`dbops.trgfn_prevent_deactivate_if_children`](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children)
che blocca la disattivazione se esistono figli attivi su 13+ relazioni
(`articoli_componenti`, `articoli_uom_operativa`, `attivita_fatturabili`,
`commesse_attivita`, `contratti_righe`, `fatture_righe`, `listini_righe`,
`ddt_righe`, `assets`, `inventari_righe`, ecc.).

---

### Pattern "padre prima, figli poi"

Coerente con il modello operatori (multi-face auth): la riattivazione del
padre **non cascadea** sui figli. Razionale:

* La disattivazione e' avvenuta in passato per una decisione di dominio
  (es. articolo obsoleto). Riattivare il padre **non** implica
  automaticamente che ogni figlio (UoM operative, righe BoM, regole
  fatturazione, ...) debba tornare attivo: l'admin valuta caso per caso.
* L'admin che riattiva un articolo dopo lungo tempo deve esplicitamente
  rivedere quali UoM operative ha senso riabilitare, quali listini
  rimettere in vigore, quali regole fatturazione applicare. La cascade
  automatica sarebbe un anti-pattern.
* Pattern simmetrico alla "chiusura" di altri domini (versioni listini,
  promo articoli, contratti) dove ogni transizione e' esplicita e
  conservativa.

---

### Firma

| Parametro | Tipo (`%TYPE`) | Significato |
|---|---|---|
| `p_articolo_id` | `articoli.id%TYPE` (uuid) | Articolo da riattivare. NULL -> raise `E_ARTICOLO_NOT_FOUND`. |
| **Ritorno** | `void` | Azione di dominio, non restituisce nulla. |

---

### Regole applicate

| Caso | Pre-condizione | Esito |
|---|---|---|
| Parametro NULL | `p_articolo_id IS NULL` | **Raise** `E_ARTICOLO_NOT_FOUND` |
| Articolo inesistente | `p_articolo_id` non in `catalogo.articoli` | **Raise** `E_ARTICOLO_NOT_FOUND` |
| Articolo disattivato | `attivo = false` | UPDATE -> `attivo = true`; nessun cambio sui figli |
| Articolo gia' attivo | `attivo = true` | **No-op silenzioso** (idempotente, niente raise, niente audit triggers spuri) |
| Parent inattivo (es. iva) | UPDATE blocked dal trigger `trgfn_child_requires_active_parent` | **Raise** `E_PARENT_INACTIVE` (codice esistente, propagato) |

---

### Logica operativa

1. **Guard parametro NULL** -> raise `E_ARTICOLO_NOT_FOUND` con contesto
   JSONB `{articolo_id: null}`.
2. **UPDATE filtrato**:
   ```sql
   UPDATE catalogo.articoli
      SET attivo = true
    WHERE id = p_articolo_id
      AND attivo = false
   ```
   La clausola `AND attivo = false` e' chiave: rende l'operazione
   **idempotente** senza scatenare audit triggers spuri (`data_update`,
   `user_update`, `tx_id_managed`) su righe gia' attive.
3. **`GET DIAGNOSTICS v_rows = ROW_COUNT`**.
4. **Se `v_rows = 0`**: due possibilita':
   * articolo gia' attivo -> no-op, return
   * articolo non esiste -> `EXISTS` test, raise `E_ARTICOLO_NOT_FOUND`
5. **Se `v_rows > 0`**: padre riattivato, fine.

I trigger di sistema (`audit_data_user_generic`, `tx_id_managed`,
`child_requires_active_parent`) gestiscono autonomamente audit, tx_id,
verifica che i parent (iva, gruppo, tipologia, spesa, listino_tipologia)
siano attivi. La fn non duplica nessuna di queste responsabilita'.

---

### Errori sollevati

| Codice | id | Quando |
|---|---|---|
| `E_ARTICOLO_NOT_FOUND` | 404 | parametro NULL oppure id non in `catalogo.articoli` |
| `E_PARENT_INACTIVE` (o equivalente) | (esistente) | propagato dal trigger `trgfn_child_requires_active_parent` se uno dei parent (iva/gruppo/tipologia/spesa/listino_tipologia) e' inattivo |

Tutti i raise passano da `script.fn_log_and_raise_error('database', 'fn_riattiva_articolo', ...)`
con contesto JSONB diagnostico (`articolo_id`).

---

### Esempi

**1) Riattiva articolo disattivato (caso d'uso tipico):**

```sql
SELECT catalogo.fn_riattiva_articolo('aaa...101'::uuid);
-- Esito: catalogo.articoli.attivo = true
-- Figli (articoli_uom_operativa, ecc.): nessun cambio
-- Ritorno: void
```

**2) Riattivazione idempotente (articolo gia' attivo):**

```sql
SELECT catalogo.fn_riattiva_articolo('aaa...101'::uuid);
-- Articolo gia' attivo
-- Esito: no-op, niente raise, niente audit spurio
-- Ritorno: void
```

**3) Articolo cancellato (FE stale):**

```sql
SELECT catalogo.fn_riattiva_articolo('00000000-0000-0000-0000-000000000999'::uuid);
-- ERROR: P0001 — Articolo non trovato: id=00000000-0000-0000-0000-000000000999.
```

**4) Parent inattivo:**

```sql
-- iva_id riferito dall'articolo e' stato disattivato.
SELECT catalogo.fn_riattiva_articolo('aaa...101'::uuid);
-- ERROR: trigger trgfn_child_requires_active_parent (catalogo.articoli)
-- segnala IVA inattivo.
```

**5) Disattivazione (azione opposta, NO fn dedicata):**

```sql
UPDATE catalogo.articoli
   SET attivo = false
 WHERE id = 'aaa...101'::uuid;
-- Se l'articolo ha figli attivi (es. una BoM dove e' componente) ->
-- ERROR: trigger trgfn_prevent_deactivate_if_children -> messaggio
-- "...presenti figli attivi che impediscono la disattivazione...".
-- L'admin disattiva prima i figli, poi il padre.
```

---

### Note operative

* **Nessun lock advisory**: l'UPDATE su PK lockata dal sistema e' sufficiente.
  Diversamente da [`fn_duplica_componente_versione`](/dbzero/catalogo/funzioni/fn_duplica_componente_versione)
  qui non c'e' EXCLUDE GIST in gioco e l'azione e' su una sola riga.
* **Nessun `SELECT FOR UPDATE` separato**: il filtro `WHERE attivo = false`
  nell'UPDATE basta a garantire l'idempotenza senza una select preliminare.
* **`EXISTS` solo nel ramo "0 rows"**: il check di esistenza viene fatto
  solo quando l'UPDATE non ha aggiornato nulla, evitando query ridondanti
  nel caso happy.
* **Niente cascade sui figli**: scelta di dominio. Se in futuro un caso
  d'uso richiederasse cascade automatica, andrebbe aperta una fn
  separata (`fn_riattiva_articolo_cascade`) per non rompere la semantica
  conservativa attuale.
* **Disattivazione resta UPDATE diretto**: niente `fn_disattiva_articolo`,
  perche' la guard cross-relazione e' gia' coperta dal trigger generico
  e non serve incapsulare. Il BE puo' fare `UPDATE catalogo.articoli SET
  attivo=false WHERE id=...` direttamente; un eventuale fail si propaga
  con messaggio user-friendly del trigger.

---

### Verifica e test

- pgTAP: `db/pgtap/catalogo/test-fn-riattiva-articolo-v1.sql` (`plan(6)`):
  trigger blocca disattivazione + fn riattiva padre + figli restano
  inattivi + NOT_FOUND su UUID casuale + idempotenza su gia' attivo.

---

{% include-markdown "signature-core.md" %}

---
