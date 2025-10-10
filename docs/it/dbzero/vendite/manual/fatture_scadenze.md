## 📘 Documentazione Concettuale – Tabella `vendite.fatture_scadenze`

> 👀 **Vedi anche**
>
> **Approfondimenti tabelle:**
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)
> • [config.termini_pagamento](/dbzero/config/tabelle/termini_pagamento)

---

### 🎯 Scopo Principale

`vendite.fatture_scadenze` memorizza lo **schedule di pagamento** (rate/scadenze) della fattura come **snapshot** al momento dell’emissione, così da:

* rendere **deterministiche** stampe e flussi verso il gestionale contabile;
* gestire sia **pagamenti a rata unica** sia **piani rateali**;
* preservare la **storicità** anche se cambiano i termini di pagamento a catalogo.

---

### 🧭 Collocazione nel flusso

1. **Selezione termini**: dalla testata (`vendite.fatture`) si risolve il termine da `config.termini_pagamento` (con eventuali override a livello cliente/ordine/preventivo) e si snapshotta in fattura.
2. **Generazione rate**: il motore calcola date + importi secondo i parametri e inserisce le righe in `vendite.fatture_scadenze`, numerando `numero_rata` da 1.
3. **Output**: stampe, portale e integrazioni leggono da qui lo scadenziario della fattura.

---

### 🔑 Campi chiave (semantica)

* `fattura_id` → FK alla testata (`vendite.fatture`).
* `numero_rata` → progressivo **univoco per fattura** (vincolo `UNIQUE (fattura_id, numero_rata)`).
* `data_scadenza` → data di esigibilità della rata.
* `importo` → importo da saldare per la rata (≥ 0).
* `meta` → **estensioni JSONB** (es.: canale incasso, IBAN/appoggio, giorni tolleranza, note RID/SEPA, riferimento termini usati).

---

### 🔒 Vincoli e indici

* **PK**: `id` (identity).
* **FK**: `fattura_id` → `vendite.fatture(id)` (ON DELETE CASCADE).
* **CHECK**: `importo >= 0`.
* **UNIQUE**: `(fattura_id, numero_rata)` → impedisce duplicati di progressivo.
* **Indici**:

  * `ix_fatture_scadenze_data` su `data_scadenza` per scadenziari e reminder.


---

### 🧮 Linee guida di calcolo

* **Numero rate**: da `config.termini_pagamento.numero_rate`.
* **Date**: derivate da `tipo_offset` (G/M/F/N), `intervallo`, `primo_offset_giorni` e regole di fine mese.
* **Ripartizione importi**: secondo `ripartizione` (UGUALI/PROPORZIONALE/LIBERA) e **policy di arrotondamento** (`metodo`/`decimali`).
* **Coerenza**: la somma `Σ importo` deve corrispondere al `totale_doc` in testata (eventuali differenze minime vanno compensate sull’ultima rata).

---

### 🧪 Query utili

```sql
-- Piano rate di una fattura
SELECT numero_rata, data_scadenza, importo
FROM vendite.fatture_scadenze
WHERE fattura_id = :fattura_id
ORDER BY numero_rata;

-- Scadenziario per periodo
SELECT f.id AS fattura_id, s.numero_rata, s.data_scadenza, s.importo
FROM vendite.fatture_scadenze s
JOIN vendite.fatture f ON f.id = s.fattura_id
WHERE s.data_scadenza BETWEEN :dal AND :al
ORDER BY s.data_scadenza, f.id, s.numero_rata;
```

---

### ✅ Best practice operative

* **Idempotenza**: rigenera le scadenze con una procedura `DELETE + INSERT` per `fattura_id`.
* **Lock post‑numerazione**: opzionale trigger/policy per impedire modifiche dopo numerazione/contabilizzazione (salvo ruolo di audit).
* **Allineamento**: quando cambia `termini_pagamento`, non toccare fatture già emesse: si usa sempre lo **snapshot** salvato in testata.
* **`meta` strutturato**: salva riferimenti utili (es. `{ "termini_codice": "30-60-90", "iban": "IT.." }`).

---

### 👓 Ruolo nel sistema

`vendite.fatture_scadenze` è la **fonte unica** per la pianificazione dei pagamenti della fattura: minimale, storicizzata e collegata ai termini configurati. Abilita scadenziari, reminder, riconciliazione e export contabile in modo coerente e ripetibile.
