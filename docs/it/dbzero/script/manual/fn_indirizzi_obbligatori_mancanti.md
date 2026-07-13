## 📘 Documentazione Concettuale – Funzione `script.fn_indirizzi_obbligatori_mancanti()`

> 👀 **Vedi anche**
>
> Tabelle:
> [config.tipi_indirizzi_allowed](/dbzero/config/tabelle/tipi_indirizzi_allowed)
> [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi)
>
> Consumatori:
> [vendite.trgfn_ddt_guard_indirizzi_obbligatori](/dbzero/vendite/funzioni/trgfn_ddt_guard_indirizzi_obbligatori)

---

### 🎯 Scopo Principale

(rev 2026-07-11)

Helper **puro** (nessun raise) per l'enforcement degli indirizzi obbligatori sui
documenti. Dato un **ambito** e l'array dei **tipi indirizzo già presenti** su un
documento, ritorna i `codice_interno` dei tipi marcati `obbligatorio = true` in
`config.tipi_indirizzi_allowed` che **mancano**.

```text
script.fn_indirizzi_obbligatori_mancanti(p_ambito text, p_tipi_presenti integer[])
  RETURNS text[]   -- STABLE
```

Ritorna un array vuoto (`ARRAY[]::text[]`) se non manca nulla.

---

### Perché un helper separato

Segue la convenzione `fn_check_*`/helper puro: **la regola vive qui, il raise nel
trigger di dominio**. Così la stessa logica è riusabile da ogni dominio documento:
oggi la usa `trgfn_ddt_guard_indirizzi_obbligatori` (ambito `DDT`, tipo `CON`);
domani potrà usarla il guard fatture (ambito `FATTURE`, tipo `FATT`) quando la
cascata verso fattura popolerà `fatture_indirizzi`.

---

### Logica

Seleziona da `config.tipi_indirizzi_allowed` (join `config.tipi_indirizzi`) le
righe con `ambito = p_ambito`, `attivo = true`, `obbligatorio = true` il cui
`tipo_indirizzo_id` **non** è in `p_tipi_presenti`, e ne aggrega i
`codice_interno` (ordinati).

---

### Casi d'uso

| Chiamata | Risultato |
|---|---|
| `('DDT', ARRAY[]::int[])` | `{CON}` (CON è obbligatorio su DDT) |
| `('DDT', ARRAY[<id CON>])` | `{}` |
| `('ORDINI', ...)` | `{}` (nessun obbligatorio su ORDINI) |

---

### Note operative

- Pura e `STABLE`: nessun effetto collaterale, safe in contesti di sola lettura.
- Il `NULL` in `p_tipi_presenti` è normalizzato ad array vuoto internamente.

---

{% include-markdown "signature-core.md" %}
