## 📘 Documentazione Concettuale – Tabella `documenti.tipi_file_documento`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [documenti.documenti_generati_file](/dbzero/documenti/tabelle/documenti_generati_file)  
>
### 🎯 Scopo Principale
(latest review 29-04-2026)
`documenti.tipi_file_documento` definisce il catalogo dei **tipi di file
persistiti** a valle della generazione di un documento.

---

### Ruolo nel modello

* classifica ogni file fisico collegato a `documenti.documenti_generati`;
* distingue il ruolo archivistico del file prodotto dal contenuto logico del
  documento;
* prepara il modello a gestire allegati derivati oltre al PDF finale.

---

### Regole operative

* il tipo file appartiene al livello di persistenza, non al livello di
  template;
* `codice_interno` deve essere stabile, perché usato per guard e logiche
  applicative lato backend;
* nella Fase A il set attivo è volutamente minimale.

---

### Seed iniziale Fase A

| codice_interno | Descrizione |
|---|---|
| `PDF_FINALE` | PDF finale |

La Fase A supporta un solo file persistito per documento generato: il PDF
finale.

---

{% include-markdown "signature-core.md" %}
