## 📘 Documentazione Concettuale – Tabella `utilities`

La tabella **`utilities`** costituisce il cuore modulare di Zero ERP: da qui si definiscono i settori funzionali dell’applicazione, sia quelli comuni a tutte le aziende sia le estensioni specifiche per ogni ramo di attività.

---

### 🎯 Scopo Principale

(latest revire 24-01-2026)
* **Definizione del settore**
  Tabella dove si definiscono i tipi di "utilities" a cui l’azienda è rivolta. Ogni record identifica un settore di business specifico: per esempio manifatturiero, gas o telecom.
* **Componente standard e specifica**
  Per ogni tipo di utility è prevista una parte core (funzionalità standard comuni a tutti i settori) e un modulo verticale specifico, progettato per risolvere le problematiche tipiche del settore.

---

### 🛠 Flessibilità e Configurabilità

* **Architettura modulare**
  Le funzionalità core (anagrafiche, preventivi, magazzino, fatturazione, reportistica, notifiche) costituiscono la base su cui si innestano i moduli verticali.
* **Estendibilità controllata**
  Per ogni nuovo settore (manifatturiero, gas, acqua, elettricità, fonia/telecom, ecc.) si sfruttano gli stessi schemi dati e servizi condivisi, evitando duplicazioni di codice e accelerando i tempi di sviluppo.
* **Configurazione dinamica**
  La definizione  di un record di `utilities` abilita  il modulo corrispondente senza intervenire sul codice, permettendo adattamenti rapidi alle esigenze aziendali.

---

### 🚀 Modalità “Base” e Settori Verticali

1. **Utility "Base"**

   * Servizi generali e trasversali:

     * **Anagrafiche** (clienti, fornitori)
     * **Preventivi**
     * **Magazzino**
     * **Fatturazione**
     * **Reportistica**
     * **Notifiche e log**
       Questi moduli rappresentano i processi fondamentali per ogni azienda.

2. **Settori Verticali**
   Moduli specifici attivabili a seconda del settore di business dell’azienda:

   * **Manifatturiero**: distinte base, cicli di produzione, tracciabilità materie prime
   * **Gas, Acqua, Elettricità**: letture contatori, bollettazione consumi, calcoli tariffazione
   * **Fonia / Telecom**: contratti, piani tariffari, fatturazione a consumo
   * **Altri**: logistica, retail, servizi professionali, ecc.

---

### 💡 Vantaggi Operativi

* **Deployment Light**
  Nessun deploy di codice richiesto per attivare o disattivare moduli: basta un update in tabella.
* **Sviluppo Accelerato**
  Le nuove verticalizzazioni si costruiscono sulle componenti esistenti, riducendo tempi e costi di realizzazione.
* **Manutenzione Semplificata**
  Tutte le regole di attivazione e configurazione dei moduli risiedono in un’unica tabella, evitando la dispersione in configurazioni multiple.

---

> 🧠 **"Una tabella per orchestrare l’intera suite funzionale di Zero ERP, dalla base comune alle specializzazioni verticali."**

---

### 🔗 Registro di fatturazione (fallback)

* `registro_id` (opzionale) definisce il **registro di default** per l’utility.
* Usato come **fallback** quando la sorgente non specifica un registro.
