## 📘 Documentazione Concettuale – Funzione `catalogo.trgfn_unita_misura_guard_tipo_update()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)
> • [catalogo.unita_misura_conversioni](/dbzero/catalogo/tabelle/unita_misura_conversioni)
> • [catalogo.uom_tipi](/dbzero/catalogo/tabelle/uom_tipi)
>
Approfondimento funzioni:
> • [catalogo.trgfn_uom_conversioni_guard_tipo](/dbzero/catalogo/funzioni/trgfn_uom_conversioni_guard_tipo)
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Chiude la **porta di servizio** del vincolo *same-type* sulle conversioni globali.

Il guard gemello `trgfn_uom_conversioni_guard_tipo` impedisce di creare una conversione fra
due UoM di tipologia diversa (peso ↔ lunghezza). Ma quel controllo guarda le UoM
**al momento in cui la conversione viene scritta**: se dopo si cambia il tipo di una delle
due, la conversione già esistente diventa retroattivamente illegale senza che nessuno se ne
accorga. Questa funzione toglie quella possibilità, bloccando il cambio di tipo su una UoM
già coinvolta in conversioni.

I due guard vanno letti **sempre insieme**: presi separatamente coprono metà regola ciascuno.

---

### Aggancio

Trigger `trg_unita_misura_a10_guard_tipo_uom_upd` — `BEFORE UPDATE OF tipo_uom_id`
su `catalogo.unita_misura`, `FOR EACH ROW`,
`WHEN (OLD.tipo_uom_id IS DISTINCT FROM NEW.tipo_uom_id)`.

---

### Regole applicate

1. Conta le righe di `catalogo.unita_misura_conversioni` in cui la UoM compare
   **da un lato o dall'altro** (`uom_from_id = NEW.id OR uom_to_id = NEW.id`).
2. Se il conteggio è `> 0`, blocca l'operazione.

Per cambiare il tipo di una UoM già usata bisogna quindi **prima rimuovere le conversioni
che la coinvolgono**: non esiste un percorso che le riconverta.

---

### ⚠️ La protezione dal falso positivo sta nel trigger, non nella funzione

Il corpo **non verifica che il tipo sia davvero cambiato**: se le conversioni collegate
esistono, solleva. A evitare che un `UPDATE` innocuo venga rifiutato è la clausola
`WHEN (OLD.tipo_uom_id IS DISTINCT FROM NEW.tipo_uom_id)` sul `CREATE TRIGGER`.

Chi riaggancia questa funzione a un nuovo trigger e omette la `WHEN` ottiene un guard che
rifiuta **qualunque** `UPDATE` di `tipo_uom_id`, compreso quello che riscrive lo stesso
valore — e la causa non si vede leggendo la funzione. Il `WHEN` va copiato insieme al resto.

---

### ⚠️ Debito: solleva `E_GENERICO`

L'errore viene registrato e sollevato con il codice **`E_GENERICO`**, non con un codice di
dominio dedicato. È fuori dalla convenzione di progetto (`E_{MODULO}_{TIPO}`) e ha due
conseguenze concrete:

* il backend non può mappare questa causa a uno stato HTTP e a un'azione UI specifici,
  perché il codice è lo stesso di qualunque altro errore generico;
* in `error_log` queste righe non sono distinguibili per codice: serve leggere il `context`
  JSONB (`uom_id`, `tipo_uom_old_id`, `tipo_uom_new_id`, `conversioni_collegate`) o il
  messaggio testuale.

Il messaggio passato come valore è *«Cambio tipo UoM non ammesso: la UoM partecipa a
conversioni globali»*. ⚠️ Chi cercasse i consumatori di questo errore partendo dal **testo**
non troverebbe nulla di utile: vanno cercati dal nome della funzione che lo solleva.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_GENERICO` | Cambio di `tipo_uom_id` su una UoM presente in almeno una riga di `unita_misura_conversioni` |

Sollevato via `script.fn_log_and_raise_error` con `area = 'catalogo'`.

---

{% include-markdown "signature-core.md" %}
