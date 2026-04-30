## 📘 Documentazione Concettuale – Tabella `documenti.tipi_asset_documento`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [documenti.template_asset](/dbzero/documenti/tabelle/template_asset)  
>
### 🎯 Scopo Principale
(latest review 29-04-2026)
`documenti.tipi_asset_documento` definisce la tipologia funzionale degli asset
riusabili nei template documentali: logo, firma, immagine, PDF di supporto,
CSS e altre risorse statiche.

---

### Ruolo nel modello

* classifica gli asset caricati in `documenti.template_asset`;
* separa la natura funzionale dell'asset dal file fisico memorizzato;
* consente regole e filtri diversi per categorie di risorse documentali.

---

### Regole operative

* `codice` e `codice_interno` sono chiavi stabili di configurazione;
* il tipo asset non identifica il file binario ma il suo ruolo nel template;
* la disattivazione (`attivo = false`) impedisce nuovi utilizzi mantenendo
  leggibile lo storico esistente.

---

### Seed iniziale Fase A

| codice_interno | Descrizione |
|---|---|
| `LOGO` | Logo |
| `FIRMA` | Firma |
| `IMMAGINE` | Immagine |
| `PDF` | PDF |
| `CSS` | CSS |
| `ALTRO` | Altro |

---

### Uso tipico nel processo

* catalogazione di risorse caricabili per emittente;
* selezione controllata dell'asset in editor/configurazione template;
* base per future policy per MIME type, dimensioni e vincoli di impiego.

---

{% include-markdown "signature-core.md" %}
