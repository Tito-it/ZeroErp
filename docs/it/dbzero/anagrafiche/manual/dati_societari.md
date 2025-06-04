## 📘 Documentazione Concettuale – Tabella `anagrafiche.dati_societari`

> 👀 **Vedi anche**  
> Approfondimento Tabelle:  
>  - [anagrafiche.soggetti](../soggetti)  
>  - [config.province](/dbzero/config/tabelle/province)

La tabella **`anagrafiche.dati_societari`** contiene i dati societari estesi per ciascun soggetto di tipo aziendale presente in **`anagrafiche.soggetti`**. Ogni riga rappresenta un insieme di informazioni obbligatorie e opzionali relative alla forma giuridica, capitale sociale, iscrizione REA, stato di liquidazione e modalità di fatturazione elettronica.

---

### 🎯 Scopo Principale

- **Estendere l’anagrafica generale**  
  I soggetti di tipo giuridico (aziende) hanno esigenze di memorizzazione di dati societari che non interessano le persone fisiche. Spostando queste informazioni in `dati_societari`, si mantiene la tabella `anagrafiche.soggetti` leggera e focalizzata sui campi anagrafici di base.

- **Gestione iscrizione REA e capitale sociale**  
  Memorizzare la provincia di iscrizione REA (`id_prov_iscri_rea` + `iscrizione_rea`) e il capitale sociale in Euro (`capitale_sociale`), dato fondamentale per valutazioni finanziarie e di business.

- **Informazioni su socio unico e liquidazione**  
  Tenere traccia degli stati societari tramite i campi enumerati `socio_unico` (se è “Socio Unico” o “Socio Multiplo”) e `liquidazione` (se la società è in liquidazione o meno).

- **Dati di fatturazione elettronica**  
  Conservare il codice SDI (`codice_sdi`) e la PEC dedicata (`pec_fatturazione`) utilizzati per l’invio di fatture elettroniche (B2B/B2C), oltre al “codice destinatario FE” (`destinatario_fe`).

---

### 🔗 Collegamenti con Altre Tabelle

- **`anagrafiche.soggetti`**  
  - Il campo `soggetto_id` (UUID) fa riferimento alla chiave primaria di `anagrafiche.soggetti(id)`.  
  - Vincolo `fk_soggetti_anagrafiche`:  
    - **ON UPDATE CASCADE** (se cambia l’ID del soggetto, si propaga)  
    - **ON DELETE CASCADE** (se un soggetto viene eliminato, si rimuovono automaticamente i suoi dati societari).  
  - Ogni soggetto di tipo “azienda” può avere **al massimo una** riga in `dati_societari` (vincolo di unicità `uq_ds_soggetto`).

- **`config.province`**  
  - Il campo `id_prov_iscri_rea` (integer) fa riferimento a `config.province(id)`.  
  - Vincolo `fk_province_config`:  
    - **ON UPDATE CASCADE** (se l’ID di una provincia cambia, si propaga)  
    - **ON DELETE RESTRICT** (non si può eliminare una provincia se esistono aziende iscritte lì).  
  - Il binomio (`id_prov_iscri_rea`, `iscrizione_rea`) è garantito unico da `uq_ds_prov_cea`, evitando duplicati di iscrizione REA nella stessa provincia.

---

### 🚩 Vincoli di Unicità e Integrità

- **Primary Key**  
  - `pk_dati_societari` su `id_dati_societari`, gestito da sequenza automatica.

- **Unicità dei campi di fatturazione**  
  - `uq_ds_codice_sdi` su `codice_sdi` (ogni codice SDI può appartenere a una sola azienda).  
  - `uq_ds_pec_fatt` su `pec_fatturazione` (ogni PEC di fatturazione è univoca).

- **Unicità iscrizione REA**  
  - `uq_ds_prov_cea` su (`id_prov_iscri_rea`, `iscrizione_rea`), garantendo che non esistano due aziende con la stessa iscrizione REA nella stessa provincia.

- **Vincolo `uq_ds_soggetto`**  
  - Assicura che ogni `soggetto_id` compaia al più una volta in `dati_societari`, evitando duplicati di scheda societaria.

---

### 🔍 Descrizione dei Campi Principali

- **`soggetto_id`**  
  Riferimento al soggetto (UUID) in `anagrafiche.soggetti`. Identifica in modo univoco l’azienda cui appartengono questi dati societari.

- **`forma_giuridica`**  
  Testo che indica la forma giuridica della società (es. “SRL”, “SPA”, “SNC”). È un campo obbligatorio.

- **`capitale_sociale`**  
  Valore numerico (precisione 15,2) che rappresenta il capitale sociale, espresso in Euro. Campo obbligatorio.

- **`id_prov_iscri_rea`**  
  Intero che indica la provincia di iscrizione al Registro delle Imprese (REA), collegato a `config.province(id)`.

- **`iscrizione_rea`**  
  Testo (fino a 30 caratteri) che indica il numero di iscrizione REA. Deve essere valorizzato ed è unito a `id_prov_iscri_rea` dal vincolo di unicità.

- **`socio_unico`**  
  Tipo enumerato `anagrafiche.socio_unico_enum`:  
  - `SU` = Socio Unico  
  - `SM` = Socio Multiplo  
  Valorizzato di default a `SU`.

- **`liquidazione`**  
  Tipo enumerato `anagrafiche.liquidazione_enum`:  
  - `LN` = Non in liquidazione (default)  
  - `LS` = In liquidazione  

- **`destinatario_fe`**  
  Testo fino a 10 caratteri che contiene il “codice destinatario” per la fatturazione elettronica. Campo obbligatorio (ad uso interno).

- **`pec_fatturazione`**  
  PEC (Testo fino a 100 caratteri) dedicata alla fatturazione elettronica. Deve essere univoca o valorizzata a `NULL` se non disponibile.

- **`codice_sdi`**  
  Testo fino a 10 caratteri che rappresenta il “codice SDI” per la fatturazione elettronica. Deve essere univoco o valorizzato a `NULL`.

- **`data_costituzione`**  
  Data di costituzione dell’azienda. Campo opzionale: può essere `NULL` se non disponibile.

---

### 💡 Vantaggi Operativi

- **Separazione dei dati societari dal resto**  
  Consolidando le informazioni strettamente legate alla natura giuridica e fiscale di un’azienda in una tabella dedicata, si migliora la coerenza e la manutenzione. La tabella `anagrafiche.soggetti` resta focalizzata su campi di base comuni a tutte le tipologie di soggetti.

- **Garanzia di unicità e integrità**  
  I vincoli di unicità su `codice_sdi`, `pec_fatturazione`, `iscrizione_rea` (assieme a `id_prov_iscri_rea`) e `soggetto_id` impediscono duplicazioni di dati critici, evitando errori nelle fasi di fatturazione e verifica anagrafica.

- **Tracciabilità della relazione soggetto → dati societari**  
  La cancellazione a cascata del soggetto rimuove automaticamente la scheda societaria associata, semplificando l’amministrazione dei dati e riducendo la possibilità di record orfani.

- **Supporto a processi di fatturazione elettronica**  
  Con `destinatario_fe`, `pec_fatturazione` e `codice_sdi`, la tabella fornisce tutte le informazioni necessarie per l’invio di fatture elettroniche conformi alle normative italiane.

---

> 🧠 **“Un’estensione dedicata ai dati societari, che valorizza la tabella anagrafica base separando informazioni fiscali, legali e di fatturazione in un unico punto, con regole di integrità che evitano inconsistenze.”**  