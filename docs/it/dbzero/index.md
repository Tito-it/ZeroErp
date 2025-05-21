# Database Zero ERP

👀 **Collegamenti rapidi** 

> 
> Database --> [Liquibase Setup & Workflow](../liquibase-setup-workflow.md).(Come eseguire e applicare le migrazioni)

> Database --> [Linee Guida SQL](../linee-guida-sql.md). (Best practice e convenzioni in Zero Erp)



Questa sezione documenta la struttura fisica del **Database Zero ERP**, implementato in PostgreSQL.  
Il database è suddiviso in più schemi, ognuno con responsabilità e oggetti (tabelle, funzioni, view) dedicati, per:

- Garantire isolamento e sicurezza tra domini  
- Facilitare manutenzione e evoluzione indipendente  
- Riflettere chiaramente l’organizzazione funzionale del sistema

🔗 **Diagramma ER**: [Visualizza il modello Entity-Relationship](../ER-diagram.md)

---

## Organizzazione per schema

| Schema         | Descrizione                                                                                     |
|----------------|-------------------------------------------------------------------------------------------------|
| **anagrafiche** | Dati anagrafici (soggetti, indirizzi, contatti) con chiavi UUID per entità core                |
| **config**      | Tabelle di lookup e parametri (stati, nazioni, tipi_contatti)                                  |
| **script**      | Logica applicativa: viste, funzioni PL/pgSQL legate ai processi ERP                             |
| **dbops**       | Strumenti DB: viste/funzioni tecniche per DBA, monitoring, metadata                             |
| **storico**     | Tabelle di audit/storico con versioning temporale dei dati                                      |
| **public**      | Oggetti generici e di supporto (test, compatibilità, default)                                   |
| **topology**    | Tabelle di topologia e relazioni strutturali (flussi di processo, mappatura delle entità)      |

---

## Navigazione per schema

- [anagrafiche](anagrafiche/index.md)  
- [config](config/index.md)  
- [script](script/index.md)  
- [dbops](dbops/index.md)  
- [storico](storico/index.md)  
- [public](public/index.md)  
- [topology](topology/index.md)  

> In ciascuna pagina di schema troverai un unico indice con le tabelle, le funzioni e le view corrispondenti.

---

> **Nota:**  
> I dettagli tecnici dei campi (tipi, constraint, indici) e delle definizioni di funzione vengono generati automaticamente via script CI, estraendoli da `information_schema` e dal catalogo PostgreSQL, in modo da mantenere sempre allineata la documentazione con il modello reale.

