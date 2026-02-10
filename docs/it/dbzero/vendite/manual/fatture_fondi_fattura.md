## 📘 Documentazione Concettuale – Tabella `vendite.fatture_fondi_fattura`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.tipi_fondi_fattura](/dbzero/vendite/tabelle/tipi_fondi_fattura)  
>
---

### 🎯 Scopo Principale

(latest review 10-02-2026)  
`vendite.fatture_fondi_fattura` registra i **fondi fattura** collegati a una
fattura (addebiti/accrediti, canone RAI, ecc.).
I fondi sono **separati** dalle righe standard e contribuiscono al
`totale_a_pagare`.

---

### 🧱 Campi chiave (semantica)

* `fattura_id`: testata collegata.
* `riferimento_fattura_id`: fattura origine (opzionale).
* `tipo_fondo_fattura_id`: categoria fondo.
* `importo`: valore del fondo (positivo o negativo).
* `meta`: dettagli specifici (es. riferimento esterno).

---

### ✅ Note operative

* I fondi non partecipano al calcolo IVA.
* La somma dei fondi va inclusa in `totale_a_pagare`.

---

{% include-markdown "signature-core.md" %}
