## 📘 Documentazione Concettuale – Funzione `catalogo.trgfn_uom_conversioni_guard_tipo()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [catalogo.unita_misura_conversioni](/dbzero/catalogo/tabelle/unita_misura_conversioni)
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)
> • [catalogo.uom_tipi](/dbzero/catalogo/tabelle/uom_tipi)
> • [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa)
>
Approfondimento funzioni:
> • [catalogo.trgfn_unita_misura_guard_tipo_update](/dbzero/catalogo/funzioni/trgfn_unita_misura_guard_tipo_update)
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Tiene `catalogo.unita_misura_conversioni` nel suo perimetro: **solo conversioni globali fra
UoM della stessa tipologia** (kg↔g, m↔cm). Una conversione peso→lunghezza non ha senso
universale, e ammetterla renderebbe ambiguo ogni calcolo che attraversa la tabella.

Le conversioni che *dipendono dall'articolo* — packaging, cartone da 12 pezzi, bancale —
non stanno qui: vivono in `catalogo.articoli_uom_operativa`, dove il fattore è per articolo.
Questo guard è ciò che tiene separati i due piani.

---

### Aggancio

Trigger `trg_uom_conversioni_a10_guard_tipo_ins_upd` — `BEFORE INSERT OR UPDATE OF
uom_from_id, uom_to_id` su `catalogo.unita_misura_conversioni`, `FOR EACH ROW`.

Il `UPDATE OF` limitato alle due colonne è voluto: cambiare il solo fattore di conversione
non tocca la tipologia e non richiede il controllo.

---

### Regole applicate

1. Risolve il tipo di `NEW.uom_from_id` e di `NEW.uom_to_id` (join
   `unita_misura → uom_tipi`).
2. Se **entrambi** i tipi sono risolti e sono distinti → blocca.
3. Se i tipi coincidono → passa.

---

### ⚠️ Se un tipo non è risolvibile, il guard lascia passare

Il ramo esplicito

```sql
IF v_from_tipo_id IS NULL OR v_to_tipo_id IS NULL THEN
  RETURN NEW;
END IF;
```

è **fail-open**: quando una delle due UoM non esiste, o esiste con `tipo_uom_id` nullo o
orfano, la conversione viene accettata senza controlli.

Non è una svista innocua: significa che il guard **non presidia i dati sporchi**, proprio il
caso in cui servirebbe di più. La rete che regge in quel punto è la FK verso
`catalogo.unita_misura` (che ferma una UoM inesistente); resta scoperta la UoM esistente con
tipologia mancante.

---

### ⚠️ Debito: solleva `E_GENERICO`

Come il guard gemello, l'errore usa il codice **`E_GENERICO`** invece di un codice di dominio
registrato. Il backend non può quindi distinguere questa causa da qualunque altro errore
generico, e in `error_log` le righe si separano solo guardando il `context` JSONB
(`uom_from_id`, `uom_to_id`, `tipo_from`, `tipo_to`).

Messaggio testuale: *«Conversione globale non ammessa tra UoM di tipologia diversa»*.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_GENERICO` | `uom_from_id` e `uom_to_id` hanno tipologie diverse, entrambe risolte |

Sollevato via `script.fn_log_and_raise_error` con `area = 'catalogo'`.

---

{% include-markdown "signature-core.md" %}
