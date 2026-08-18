## 📘 Documentazione Concettuale – Tabella `vendite.tipi_doc_fiscale_registri`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)  
> • [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)  
>
**Approfondimento funzioni:**
>
• [`vendite.fn_get_registro_id`](/dbzero/vendite/funzioni/fn_get_registro_id)
>
### 🎯 Scopo Principale
(latest review 27-01-2026)
La tabella **`vendite.tipi_doc_fiscale_registri`** definisce il mapping
**tipo documento fiscale → registro di fatturazione**, necessario per la
numerazione e la contabilizzazione dei documenti.

---

### Campi chiave

* `tipo_doc_fiscale_id` → tipo documento fiscale (FK).
* `registro_id` → registro di fatturazione associato (FK).
* `codice_interno` → codice di servizio del mapping (opzionale).

---

### Regole principali

* mapping **multiplo** per `tipo_doc_fiscale_id` verso registri diversi.
* la selezione del registro e` determinata da `vendite.fn_get_registro_id`.


---


---

### 🔄 rev 2026-08-18 — il mapping diventa `(tipo_doc, natura) → (registro, serie)`

Brief: `brief-design-note-credito-resi` (slice **N2**, §12.4-bis.3).

```text
PRIMA    (tipo_doc)          →  registro
ORA      (tipo_doc, natura)  →  (registro, serie)
```

Questa tabella **era già** la sede della domanda *«dato un tipo di documento, su
quale registro va?»*. La natura è la seconda metà della stessa domanda, non una
domanda nuova: per questo entra qui e non in una gerarchia a parte.

| Colonna nuova | Ruolo |
|---|---|
| `natura_doc_id` | `NOT NULL DEFAULT FATTURA` → le righe esistenti restano quelle che erano |
| `serie` | nullable: **override** del `serie_default` del registro. `NULL` = vale il default |

⚠️ **La `UNIQUE` è cambiata**, da `(tipo_doc_fiscale_id, registro_id)` a
`(tipo_doc_fiscale_id, natura_doc_id, registro_id)`. Senza, mappare fattura e
nota di credito sullo **stesso** registro con due serie diverse — che è l'altra
metà della scelta — sarebbe stato vietato da un vincolo che non sa della natura.
Il vincolo va allargato **prima** del seed, o il seed non entra.

#### ⭐ È qui che «registro proprio o serie dedicata?» diventa una riga di seed

| Se il seed dice… | Effetto |
|---|---|
| stesso `registro_id`, `serie = 'NC'` | serie a parte **dentro** il registro vendite |
| `registro_id` diverso | **sezionale proprio**, progressivo e `reset_policy` indipendenti |

Entrambe funzionano senza una riga di codice diversa, ed entrambe restano
cambiabili dopo. È la forma che il progetto usa per le scelte che appartengono
all'azienda e non allo sviluppatore — `tipi_reso.riapre_residuo`,
`causali_trasporto.fatturabile`: nessun `IF` cablato, si legge il flag.

⚠️ **`NOTA_DEBITO` non ha mapping**, ed è voluto: `fn_get_registro_id` risponde
`E_CONFIG_MANCANTE`. Nessuno ha ancora deciso su quale registro numerarla, e
ripiegare su quello delle fatture la emetterebbe nel posto sbagliato in silenzio.

---

{% include-markdown "signature-core.md" %}
