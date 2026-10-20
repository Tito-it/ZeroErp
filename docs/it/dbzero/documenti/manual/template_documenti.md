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
  `emittente_fiscale + sorgente + codice_interno`, con i NULL **non distinti**:
  fra i modelli standard (senza emittente) codice e codice interno sono unici
  per sorgente;
* può esistere un solo template `is_default = true` e `attivo = true` per
  tripla `tipo_documento_output + sorgente + emittente`, e un solo standard
  predefinito attivo per `tipo_documento_output + sorgente`;
* `context_builder_code` identifica il builder backend che prepara il contesto
  dati per il render.

---

### Il modello standard

(20-10-2026 — brief `brief-db-modelli-documento-standard`)

Un emittente nuovo non ha modelli suoi, e senza modelli non potrebbe emettere.
Per questo il sistema fornisce un **modello standard** per ogni tipo di
documento: una riga con `standard = true` e **senza emittente**
(`chk_template_documenti_standard_senza_emittente`: lo standard, e solo lo
standard, non ha emittente).

* **Fa da ripiego.** Si stampa con lo standard quando l'emittente non ha nessun
  modello suo che può stampare per quel documento (attivo, con una versione
  pubblicata valida oggi: la sola bozza non basta). Se ne ha, vale il suo
  predefinito, e senza predefinito la stampa si ferma (la regola è in
  [fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile)).
* **Lo scrivono solo il seed e i changeSet.** Dall'applicazione si legge e
  basta (`E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA`, guard
  `trg_template_documenti_a05_guard_standard_ins_upd_dlt`, che copre anche le
  versioni). Chi vuole un modello diverso lo **personalizza**: crea il modello
  del suo emittente partendo da una versione standard, e la versione nuova
  dichiara da dove è partita (`template_documenti_versioni.derivata_da_versione_id`).
* **Un'evoluzione ha una sede sola.** I changeSet che cambiano un modello
  scrivono sullo standard, trovato per `standard + tipo + sorgente +
  codice_interno`, non sulle copie degli emittenti. Quanto una copia è rimasta
  indietro lo dice
  [vw_template_personalizzati_scarto](/dbzero/documenti/views/vw_template_personalizzati_scarto).
* `standard` non cambia dopo la nascita (lock di colonna): un modello non
  diventa standard, e uno standard non diventa il modello di un emittente.
* Un documento generato con lo standard porta l'emittente del documento: la
  coerenza (`trgfn_documenti_generati_check_coerenza`, regola 4) ammette
  «stesso emittente, oppure modello standard».

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

1. il backend chiama `fn_risolvi_template_applicabile` con sorgente, emittente
   del documento e tipo output;
2. la funzione restituisce il template (dell'emittente o standard);
3. seleziona la versione pubblicata valida alla data di riferimento;
4. costruisce il contesto tramite `context_builder_code`.

---

{% include-markdown "signature-core.md" %}
