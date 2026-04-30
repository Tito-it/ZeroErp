## 📘 Documentazione Concettuale – Tabella `documenti.render_engine_documento`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni)  
>
### 🎯 Scopo Principale
(latest review 29-04-2026)
`documenti.render_engine_documento` definisce il catalogo dei motori di
rendering ammessi per la trasformazione del template in documento finale.

---

### Ruolo nel modello

* rende esplicita e configurabile la scelta del render engine per ogni
  versione pubblicabile di template;
* evita stringhe libere sparse nello schema e nel backend;
* abilita futura estensione a più motori senza cambiare il contratto dati
  delle versioni template.

---

### Regole operative

* `codice` e `codice_interno` devono restare stabili nel tempo;
* la tabella è un lookup tecnico-funzionale: non conserva configurazioni
  segrete o parametri runtime del motore;
* eventuali capability specifiche possono essere aggiunte nel `meta`.

---

### Seed iniziale Fase A

| codice_interno | Descrizione |
|---|---|
| `WEASYPRINT` | WeasyPrint |

---

{% include-markdown "signature-core.md" %}
