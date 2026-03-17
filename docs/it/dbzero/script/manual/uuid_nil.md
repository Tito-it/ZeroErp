## 📘 Documentazione Concettuale – Funzione `script.uuid_nil()`

La funzione **`script.uuid_nil()`** restituisce l’**UUID nil**, ovvero il valore composto da tutti zeri (`00000000-0000-0000-0000-000000000000`). Viene utilizzata come helper per rappresentare un UUID “vuoto” in trigger e funzioni, facilitando fallback controllati o valori di default in assenza di un identificativo valido.

---

### 🎯 Scopo Principale

* Fornire un valore UUID costante, composto interamente da zeri.
* Usato come **fallback** o **default** quando non è possibile generare o recuperare un UUID valido.

---

### Esempio di Utilizzo

```sql
-- Assegna l’UUID nil a una variabile
SELECT script.uuid_nil() AS nil_uuid;

-- Utilizzo in trigger o funzione come valore di fallback
NEW.tx_id := COALESCE(current_tx_id, script.uuid_nil());
```

---

> **“`script.uuid_nil()` è il modo più semplice e leggibile per ottenere un UUID ‘tutti zeri’ nel database.”**
