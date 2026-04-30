## 📘 Documentazione Concettuale – Tabella `documenti.documenti_generati_file`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati)  
> • [documenti.tipi_file_documento](/dbzero/documenti/tabelle/tipi_file_documento)  
>
### 🎯 Scopo Principale
(latest review 29-04-2026)
`documenti.documenti_generati_file` conserva i **file persistiti** collegati a
un documento già generato, separando il record storico logico dalla
memorizzazione fisica del file.

---

### Ruolo nel processo

* registra dove si trova il file prodotto (`storage_key`);
* conserva metadati tecnici del file persistito;
* permette di estendere il modello a più file per documento senza cambiare la
  tabella storica principale.

---

### Regole operative

* l'unicità su `documento_generato_id + file_tipo_id` impedisce duplicati dello
  stesso ruolo file sul medesimo documento;
* `sha256` consente audit di integrità del file persistito;
* `ordinamento` prepara il modello a eventuali collezioni ordinate di file,
  anche se in Fase A non è ancora sfruttato pienamente.

---

### Perimetro Fase A

* un solo tipo file seedato: `PDF_FINALE`;
* un solo file atteso per documento generato;
* il modello resta già pronto per estensioni future come allegati tecnici,
  HTML sorgente, JSON di snapshot o artefatti derivati.

---

{% include-markdown "signature-core.md" %}
