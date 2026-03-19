## 📘 Documentazione Concettuale – Tabella `vendite.tipi_fondi_fattura`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture_fondi_fattura](/dbzero/vendite/tabelle/fatture_fondi_fattura)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
>
### 🎯 Scopo Principale
(latest review 10-02-2026)  
`vendite.tipi_fondi_fattura` definisce il **catalogo delle tipologie di fondo fattura**
(addebiti/accrediti fatture precedenti, canone RAI, ecc.). Serve a normalizzare
i motivi di addebito/accredito extra rispetto alle righe standard.

---

### Campi chiave (semantica)

* **Identita`**: `codice`, `codice_interno`.
* **Descrizione**: testo leggibile in UI/report.
* **Governance**: `attivo`, `meta`, audit.

---

### Note operative

* Le tipologie sono riusate da `vendite.fatture_fondi_fattura`.
* Non rappresentano articoli: i fondi fattura sono **separati** dalle righe.

---

{% include-markdown "signature-core.md" %}
