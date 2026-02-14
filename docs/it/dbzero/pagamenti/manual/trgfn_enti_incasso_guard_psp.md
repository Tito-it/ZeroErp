## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_enti_incasso_guard_psp`

### 🎯 Scopo Principale
Garantire la coerenza applicativa dei record `pagamenti.enti_incasso` quando il canale e` di tipo `PSP`.

### ✅ Regole applicate
- Se `NEW.tipo = 'PSP'`:
  - `NEW.soggetto_ruolo_id` e` obbligatorio.
  - Il ruolo deve essere di tipo `PSP` (`config.tipi_ruoli.codice_interno = 'PSP'`).
  - Deve esistere una riga attiva in `anagrafiche.psp` per quello stesso `soggetto_ruolo_id`.

### 🔁 Quando si attiva
- `BEFORE INSERT OR UPDATE` su `pagamenti.enti_incasso`.

### ⚠️ Error handling
- In caso di incoerenza usa `script.fn_log_and_raise_error(...)`.

{% include-markdown "signature-core.md" %}
