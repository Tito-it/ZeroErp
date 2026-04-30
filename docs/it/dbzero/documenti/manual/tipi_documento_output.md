## 📘 Documentazione Concettuale – Tabella `documenti.tipi_documento_output`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti)  
> • [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati)  
>
### 🎯 Scopo Principale
(latest review 29-04-2026)
`documenti.tipi_documento_output` definisce il catalogo dei **tipi di output**
producibili dal motore documentale. Serve a separare il "che cosa genero"
dalla sorgente applicativa e dal template usato per la resa PDF.

---

### Ruolo nel modello

* classifica il documento finale generato dal motore;
* viene referenziata sia dal contenitore logico del template sia dal registro
  storico dei documenti generati;
* stabilisce il perimetro funzionale del modulo documenti lato lookup e seed.

---

### Regole operative

* `codice` e `codice_interno` devono restare stabili per non rompere mapping
  backend, seed e integrazioni;
* la tabella segue il pattern lookup standard del progetto:
  `id / codice / codice_interno / descrizione / attivo / meta`;
* `attivo = false` disabilita nuovi utilizzi senza cancellare lo storico.

---

### Seed iniziale Fase A

| codice_interno | Descrizione |
|---|---|
| `PREVENTIVO` | Preventivo |

La Fase A parte volutamente con un solo consumatore reale: il documento
`PREVENTIVO`.

---

### Uso tipico nel processo

* filtro nella selezione del template corretto;
* classificazione del record storico in `documenti.documenti_generati`;
* alimentazione di lookup backend/UI per configurazioni documentali.

---

{% include-markdown "signature-core.md" %}
