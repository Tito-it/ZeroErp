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

🔗 **Diagramma ER**:

---

## Organizzazione per schema

{% include-markdown "it/schemidb.md" %}




> **Nota:**  
> I dettagli tecnici dei campi (tipi, constraint, indici) e delle definizioni di funzione vengono generati automaticamente via script CI, estraendoli da `information_schema` e dal catalogo PostgreSQL, in modo da mantenere sempre allineata la documentazione con il modello reale.

