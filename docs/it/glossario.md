# 📖 Glossario sigle DevOps & Database

| Sigla        | Significato                       | Descrizione pratica in ZeroERP                                                                                                                        |
| ------------ | --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **PR**       | Pull Request                      | Richiesta di unione di modifiche in un branch principale. Permette la code review e la validazione prima del merge.                                   |
| **CI**       | Continuous Integration            | Integrazione continua: ogni commit/PR scatena workflow automatici (test, build, Liquibase validate, ecc.) per garantire che il codice resti coerente. |
| **CD**       | Continuous Delivery / Deployment  | Distribuzione continua: automatizza il rilascio in ambienti di staging o produzione, una volta che la CI ha avuto successo.                           |
| **Lint**     | Linter                            | Strumento che controlla lo stile e la qualità del codice (es. Python, YAML, SQL).                                                                     |
| **Pipeline** | DevOps Pipeline                   | Sequenza di job automatizzati (build, test, migrazioni DB, doc build) definiti in GitHub Actions o CI server.                                         |
| **Workflow** | GitHub Actions Workflow           | File YAML che descrive azioni automatiche da eseguire su eventi Git (push, PR, release).                                                              |
| **Job**      | Job CI/CD                         | Unità di lavoro nella pipeline (es. "setup DB", "run tests", "build docs").                                                                           |
| **Step**     | Step di Job                       | Comando o azione elementare all’interno di un job (es. `pip install`, `liquibase validate`).                                                          |
| **Runner**   | GitHub Runner                     | Ambiente (container/VM) che esegue i job della pipeline.                                                                                              |
| **Artifact** | Artifact                          | File prodotto dalla pipeline (es. build frontend, pacchetto docs) che può essere pubblicato o riutilizzato.                                           |
| **Cache**    | Build Cache                       | Meccanismo per riutilizzare dipendenze o build precedenti e velocizzare la CI.                                                                        |
| **PK**       | Primary Key                       | Chiave primaria di una tabella, identifica univocamente ogni record.                                                                                  |
| **FK**       | Foreign Key                       | Chiave esterna, mantiene l’integrità referenziale tra tabelle.                                                                                        |
| **GUC**      | Grand Unified Configuration       | Parametro personalizzato di PostgreSQL, utilizzato anche in ZeroERP per configurazioni dinamiche.                                                     |
| **DDL**      | Data Definition Language          | Comandi SQL che definiscono la struttura (CREATE, ALTER, DROP).                                                                                       |
| **DML**      | Data Manipulation Language        | Comandi SQL che manipolano i dati (INSERT, UPDATE, DELETE, SELECT).                                                                                   |
| **MVCC**     | Multi-Version Concurrency Control | Meccanismo di PostgreSQL che gestisce la concorrenza mantenendo più versioni delle righe.                                                             |
| **CTE**      | Common Table Expression           | Costrutto SQL (`WITH ...`) utile per query temporanee e leggibili.                                                                                    |
| **VIEW**     | Vista                             | Query salvata come oggetto DB, usata per semplificare accessi ai dati complessi.                                                                      |
| **SP / FN**  | Stored Procedure / Function       | Logica lato DB in PL/pgSQL o altri linguaggi.                                                                                                         |
| **TRG**      | Trigger                           | Meccanismo che esegue logica automatica a fronte di eventi su una tabella (INSERT/UPDATE/DELETE).                                                     |

---

✅ Questo glossario può essere esteso man mano che incontriamo altre sigle ricorrenti sia lato **DevOps** che **Database**.
