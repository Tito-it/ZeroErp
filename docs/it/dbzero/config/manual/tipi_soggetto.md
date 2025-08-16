📘 Documentazione Concettuale – Tabella `config.tipi_soggetto`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:   
>
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio)      
> * Impatto su:  [`anagrafiche.soggetti` (colonna `tipo_soggetto`)](/dbzero/anagrafiche/tabelle/soggetti)
---

### 🎯 Scopo Principale

* Definire le **macro-tipologie** di soggetto (es. Persona Fisica, Persona Giuridica, Ente, ecc.)
* Separare la classificazione di alto livello dalla gestione dettagliata dei tipi soggetto (internazionale) tramite la tabella di dettaglio.

---

### 🔍 Problematiche Affrontate

1. **Verifica CF/P.IVA**: alcuni controlli formali (codice fiscale, partita IVA) dipendono dal tipo di soggetto. Centralizzare le macro‑tipologie consente di applicare regole diverse a seconda del contesto.
2. **Internazionalizzazione**: supportare soggetti di paesi diversi richiede descrizioni e regole specifiche. La distinzione macro/dettaglio migliora l’estendibilità.
3. **Refactoring di `anagrafiche.soggetti`**: la colonna `tipo_soggetto` passa da valore fisso (`F`, `G`, `X`) a chiave esterna verso `config.tipi_soggetto_dettaglio`, rendendo il modello più flessibile.

---

### 🔒 Vincoli e Audit

* **PK**: `tipi_soggetto_pkey` su `id` (VARCHAR(10)).
* **Trigger di auditing**: `trg_upd_overrides_audit_data_user` aggiorna automaticamente i campi `data_update` e `user_update` tramite `script.trgfn_upd_audit_data_user_generic()`.

---

### ⚙️ Meccanismo di Integrazione

1. **Popolamento**
   Inserire righe con codici standardizzati, es.:

   ```sql
   INSERT INTO config.tipi_soggetto(id, descrizione)
   VALUES
     ('PF', 'Persona Fisica'),
     ('PG', 'Persona Giuridica'),
     ('EN', 'Ente Pubblico');

   ```
3. **Estensione**
   La tabella `config.tipi_soggetto_dettaglio` conterrà i sotto-tipi o attributi specifici (nazione, categoria fiscale, ecc.).

---

### 💡 Vantaggi Operativi

* **Modularità**: separazione chiara tra tipologie di alto livello e dettagli, semplificando manutenzione e versioning.
* **Estendibilità internazionale**: aggiungere nuovi paesi o regole fiscali senza alterare la tabella principale dei soggetti.
* **Coerenza dei controlli**: applicare regole di validazione CF/P.IVA in base al tipo_soggetto_dettaglio associato, migliorando l’accuratezza.

> 🧠 **“Distinguere le macro-tipologie dai dettagli consente un’architettura più flessibile, pronta ad adattarsi a normative internazionali e a regole di validazione diverse.”**