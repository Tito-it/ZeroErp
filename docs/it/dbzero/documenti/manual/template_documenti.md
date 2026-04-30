## 📘 Documentazione Concettuale – Tabella `documenti.template_documenti`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [documenti.tipi_documento_output](/dbzero/documenti/tabelle/tipi_documento_output)  
> • [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni)  
> • [config.sorgenti](/dbzero/config/manual/sorgenti)  
> • [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/manual/emittenti_fiscali)  
>
### 🎯 Scopo Principale
(latest review 29-04-2026)
`documenti.template_documenti` rappresenta il **contenitore logico** di un
template documentale. Non contiene ancora il contenuto renderizzabile del
template: definisce l'identità funzionale del template per tipo output,
sorgente applicativa ed emittente fiscale.

---

### Ruolo nel processo

* collega il tipo documento (`PREVENTIVO`, in Fase A) alla sorgente applicativa
  che ne richiede la generazione;
* isola il livello "anagrafico" del template dal suo versionamento;
* identifica il template di default da usare quando non viene richiesta una
  variante esplicita.

---

### Campi chiave (semantica)

* **Classificazione**: `tipo_documento_output_id`, `sorgente_tipo_id`,
  `emittente_fiscale_id`.
* **Identita` template**: `codice`, `codice_interno`, `descrizione`.
* **Contratto backend**: `context_builder_code`, `file_name_pattern`.
* **Selezione default**: `is_default`, `attivo`.

---

### Regole operative

* `codice_interno` è l'identità tecnica stabile del template; `codice` è il
  codice operativo leggibile;
* l'unicità è per `emittente_fiscale + sorgente + codice` e
  `emittente_fiscale + sorgente + codice_interno`;
* può esistere un solo template `is_default = true` e `attivo = true` per
  tripla `tipo_documento_output + sorgente + emittente`;
* `context_builder_code` identifica il builder backend che prepara il contesto
  dati per il render.

---

### Confine del modello

* il contenuto del template non vive qui ma in
  `documenti.template_documenti_versioni`;
* la tabella non storicizza le rese effettuate: quello storico vive in
  `documenti.documenti_generati`;
* la tabella non descrive i file asset: quelli sono nel catalogo
  `documenti.template_asset`.

---

### Uso tipico nel processo

1. il backend risolve `tipo output + sorgente + emittente`;
2. individua il template attivo/default;
3. seleziona la versione pubblicata valida alla data di riferimento;
4. costruisce il contesto tramite `context_builder_code`.

---

{% include-markdown "signature-core.md" %}
