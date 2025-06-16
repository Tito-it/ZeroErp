## 📘 Documentazione Concettuale – Tabella `anagrafiche.soggetti`

>  👀 **Vedi anche** 
> Approfondimento Tabelle:   
>  - [anagrafiche.soggetti_ruoli](../soggetti_ruoli)   
>  - [anagrafiche.dati_societari](../dati_societari)   
>  - [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)    

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

- **`config.contatti_ruoli`**  
  - Il campo `contatto_ruolo_id` fa riferimento a `config.contatti_ruoli(id)`.  
  - I ruoli di contatto non possono essere eliminati se sono ancora in uso (`ON DELETE RESTRICT`); eventuali aggiornamenti si propagano (`ON UPDATE CASCADE`).

- **`config.stati`**  
  - Il campo `stato_id` fa riferimento a `config.stati(id)`.  
  - Uno stato non può essere eliminato se esistono soggetti associati (`ON DELETE RESTRICT`); modifiche di ID si propaghino (`ON UPDATE CASCADE`).

---

### 🚩 Regole di Validazione Condizionale

1. **Campo `tipo_soggetto`**  
   - Valori ammessi:  
     - `F` = Persona fisica  
     - `G` = Persona giuridica  
     - `X` = Persona fisica forzata (per codici fiscali “speciali” o enti particolari)

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

> 🧠 **“Un’Anagrafica Soggetti solida e coerente: controlli condizionali e campi generati assicurano dati puliti, ricercabili e univoci, senza dover ripetere informazioni in fase applicativa.”**