## 📘 Documentazione Concettuale – Tabella `anagrafiche.soggetti`

>  👀 **Vedi anche** 
>
> Approfondimento Tabelle:   
>
>  * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)   
>  * [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari)   
>  * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)    
>  * [config.titoli_cortesia](/dbzero/config/tabelle/titoli_cortesia)    
>  * [config.tipi_soggetto_dettaglio](/dbzero/config/tipi_soggetto_dettaglio)    
>  * [storico.soggetti](/dbzero/storico/tabelle/soggetti)   
>
> Approfondimento Funzioni:   
> 
>  * [anagrafiche.trgfn_soggetti_ins_upd_check_soggetto_contatti](/dbzero/anagrafiche/funzioni/trgfn_soggetti_ins_upd_check_soggetto_contatti)   
>  * [anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch](/dbzero/anagrafiche/funzioni/trgfn_soggetti_valida_cf_piva_dispatch)   
>  * [anagrafiche.trgfn_soggetti_ins_upd_genera_cdsoggetto](/dbzero/anagrafiche/funzioni/trgfn_soggetti_ins_upd_genera_cdsoggetto)   
>  * [anagrafiche.trgfn_dati_societari_ins_upd_check_tipo_soggetto](/dbzero/anagrafiche/funzioni/trgfn_dati_societari_ins_upd_check_tipo_soggetto) 
>  * [script.trgfn_upd_audit_data_user_generic](/dbzero/script/funzioni/trgfn_upd_audit_data_user_generic)   
>  * [script.trgfn_upd_dlt_storico_generic](/dbzero/script/funzioni/trgfn_upd_dlt_storico_generic)


Questa documentazione descrive le regole di progettazione e implementazione della tabella anagrafica **`anagrafiche.soggetti`** in Zero ERP, senza ripetere la struttura SQL automatica. Contiene informazioni su vincoli, campi generati e relazioni con altre tabelle.

---

### 🎯 Scopo Principale

- **Coerenza dei dati**  
  Garantire che ogni soggetto—persona fisica, giuridica o fisica forzata—sia identificato in modo univoco e validato secondo le regole aziendali.

- **Univocità basata su CF/P.IVA**  
  Utilizzare un campo generato (`id_fiscale_univoco_cf_piva`) che unisca codice fiscale e partita IVA per evitare duplicati all’interno dello stesso stato.

- **Ricerca semplificata**  
  Creare un campo generato (`ragione_sociale_completa`) che unisca automaticamente ragione sociale, cognome e nome, facilitando le query di ricerca testuale.

- **Dettagli societari**  
  Le informazioni dettagliate per le aziende vengono descritti nella tabella `anagrafiche.dati_societari` 

---

### 🔗 Collegamenti con Altre Tabelle

- **`config.comuni`**  
  - Il campo `comune_id` fa riferimento a `config.comuni(id)`.  
  - Se un comune viene eliminato, la cancellazione è vietata finché esistono riferimenti (`ON DELETE RESTRICT`).  
  - Se l’ID di un comune cambia, si propaga la modifica (`ON UPDATE CASCADE`).

- **`anagrafiche.contatti`**  
  - Il campo `default_contatto_id` fa riferimento a `anagrafiche.contatti(id)`.  
  - Ogni soggetto deve avere un contatto valido: la cancellazione di un contatto di default richiede una gestione manuale (`ON DELETE RESTRICT`).

- **`config.titoli_cortesia`**  
  - Il campo `titolo_cortesia_id` fa riferimento a `config.titoli_cortesia(id)`.  
  - I titoli cortesia non possono essere eliminati se sono ancora in uso (`ON DELETE RESTRICT`); eventuali aggiornamenti si propagano (`ON UPDATE CASCADE`).

- **`config.stati`**  
  - Il campo `stato_id` fa riferimento a `config.stati(id)`.  
  - Uno stato non può essere eliminato se esistono soggetti associati (`ON DELETE RESTRICT`); modifiche di ID si propaghino (`ON UPDATE CASCADE`).

---

### 🚩 Regole di Validazione Condizionale

1. **Campo `tipo_soggetto`**  
     Campo tipo_soggetto (DEPRECATA)
     * Nota: la colonna tipo_soggetto è stata rimossa ed è ora sostituita da tipo_soggetto_dettaglio_id

2. **Check su `sesso`**  
   - Valori ammessi:  
     - `M` (Maschio)  
     - `F` (Femmina)  
     - `S` (Soggetto generico)  
     - `X` (Non indicato)

3. **Vincolo di presenza di CF o P.IVA**  
   Almeno uno tra `codice_fiscale` o `partita_iva` deve essere valorizzato.

4. **Coerenza tra `tipo_soggetto` e campi anagrafici**  
   - Se `tipo_soggetto = 'F'`, devono essere presenti `nome`, `cognome` e `codice_fiscale`.  
   - Se `tipo_soggetto = 'G'`, devono essere presenti `ragione_sociale` e `partita_iva`.  
   - Se `tipo_soggetto = 'X'`, deve essere presente almeno `codice_fiscale`.

5. **Ulteriore coerenza per soggetti di tipo “X”**  
   Se `tipo_soggetto = 'X'`, deve esserci almeno `ragione_sociale` oppure entrambi `cognome` e `nome`.

---

### 🔍 Campi Generati e Indicizzazione

- **`id_fiscale_univoco_cf_piva`** (colonna generata)  
  - Definito come `COALESCE(codice_fiscale, partita_iva)`.  
  - Garantisce l’univocità del soggetto all’interno dello stesso stato.

- **`ragione_sociale_completa`** (colonna generata)  
  - Definito come `COALESCE(ragione_sociale, (cognome || ' ' || nome))`.  
  - Studiato per semplificare le ricerche testuali senza concatenare manualmente valori.

---

### 💡 Vantaggi Operativi

- **Univocità e integrità dei dati**  
  Grazie al campo generato `id_fiscale_univoco_cf_piva` abbinato a `stato_id`, si evita la duplicazione di soggetti con lo stesso CF o P.IVA per uno stesso stato.

- **Ricerca efficiente**  
  Il campo `ragione_sociale_completa` consente ricerche full-text immediate, sia per persone fisiche sia per aziende, migliorando le performance delle query.

- **Riduzione delle inconsistenze**  
  I vincoli condizionali su `tipo_soggetto`, `sesso` e CF/P.IVA catturano automaticamente eventuali inserimenti errati, riducendo la necessità di controlli manuali in fase applicativa.

- **Facilità di manutenzione**  
  Separando le informazioni “statiche” dall’anagrafica generica e sfruttando colonne generate, si evita di duplicare logiche di concatenamento o controlli sui dati, semplificando eventuali evoluzioni future.

---

### ⚙️ Implementazioni Aggiuntive

In questa sezione sono descritte le modifiche chiave apportate per allinearsi al nuovo modello dati, con dettaglio delle motivazioni e degli esempi di configurazione internazionale:

1. **Esigenza di accuratezza per CF/P.IVA e internazionalizzazione**
   Con la sola colonna `tipo_soggetto` non era possibile gestire formati e vincoli diversi per ogni paese. La nuova colonna `tipo_soggetto_dettaglio_id`, in relazione alla tabella di configurazione `config.tipi_soggetto_dettaglio`, permette di:

   * Applicare regole di validazione specifiche per codice fiscale e partita IVA in base allo Stato (`stato_iso2`).
   * Definire formati diversi (alfanumerico, numerico, lunghezza fissa) a livello di dettaglio di soggetto (privato, ditta individuale, società di capitali, ecc.).
   * Facilitare l’internazionalizzazione e futuri ampliamenti a nuovi paesi senza modificare lo schema principale.

2. \*\*Rimozione della colonna \*\***`tipo_soggetto`**

   ```sql
   ALTER TABLE anagrafiche.soggetti
     DROP COLUMN IF EXISTS tipo_soggetto;
   ```

3. \*\*Introduzione di \*\***`tipo_soggetto_dettaglio_id`**

   ```sql
   ALTER TABLE anagrafiche.soggetti
     ADD COLUMN tipo_soggetto_dettaglio_id BIGINT NOT NULL
       REFERENCES config.tipi_soggetto_dettaglio(id)
       ON UPDATE CASCADE
       ON DELETE RESTRICT;
   ```

4. **Vincoli e trigger aggiornati**

   * Il trigger di validazione CF/P.IVA (`trg_soggetti_ins_upd_valida_cf_piva`) ora utilizza `tipo_soggetto_dettaglio_id`.
   * È stato aggiunto il vincolo di FK:

   ```sql
   ALTER TABLE anagrafiche.soggetti
     ADD CONSTRAINT fk_soggetti_tipo_soggetto_dettaglio
       FOREIGN KEY (tipo_soggetto_dettaglio_id)
       REFERENCES config.tipi_soggetto_dettaglio(id)
       ON UPDATE CASCADE
       ON DELETE RESTRICT;
   ```


> 🧠 **“Un’Anagrafica Soggetti solida e coerente: controlli condizionali e campi generati assicurano dati puliti, ricercabili e univoci, senza dover ripetere informazioni in fase applicativa.”**