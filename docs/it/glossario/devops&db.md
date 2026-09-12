# 📖 Glossario sigle DevOps & Database

> Due parti: le **sigle** ricorrenti in CI/CD e database, e le **parole inglesi**
> che si incontrano leggendo il codice e i brief. Per ciascuna, il significato
> comune e come la si usa **in ZeroERP** — che a volte è più stretto.

---

## Sigle

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

## Parole inglesi che si incontrano nel codice

> Non sono sigle: sono termini di mestiere che restano in inglese negli
> identificatori e nei commenti. Qui c'è **cosa vogliono dire** e, soprattutto,
> **che cosa significano da noi** — perché in ZeroERP alcune hanno un uso più
> preciso di quello generale.

| Termine | Significato | Uso pratico in ZeroERP |
| ------- | ----------- | ---------------------- |
| **Façade** (o *facade*) | Letteralmente **facciata**: la parte davanti di un edificio. In programmazione è **la porta d'ingresso unica a una cosa complicata** — chi entra chiede quello che gli serve e non sa (né deve sapere) quante stanze ci sono dietro. | ⭐ Da noi ha un significato **stretto e definito**: è il **service che fa da porta a un dominio**. La convenzione sta in `.codex/AGENTS.md` — «`<schema>_service.py` — *Facade* per operazioni generiche». Chi chiama parla solo col service; quali repository interroghi, in che ordine e dentro quale transazione **non esce di lì**. ⛔ Non è un sinonimo di *interfaccia*: quella dichiara un contratto e non contiene codice, la façade contiene il codice che orchestra. |
| **Wrapper** | Letteralmente **involucro**, incarto. È un pezzo di codice sottile che **avvolge** qualcos'altro per renderlo più comodo, più sicuro o più uniforme da usare — senza cambiare ciò che c'è dentro. | Ricorre soprattutto fra Python e database: un metodo di repository che *avvolge* una funzione PL/pgSQL (`Wrapper su script.fn_audit_summary(...)`) esiste per dare **un punto solo** da cui la si chiama, con i controlli e la traduzione degli errori sempre uguali. ⚠️ Un wrapper che aggiunge **regole** non è più un wrapper: è logica, e va detto — se no qualcuno lo scavalca credendo di saltare solo un involucro. |
| **Fixture** | Letteralmente una cosa **fissata al suo posto** (`light fixture` = il lampadario avvitato al soffitto). Nei test è **la scenetta preparata apposta** perché il test abbia qualcosa su cui girare. | ⛔ Da noi la fixture **si fabbrica, non si trova**: il test si costruisce da solo i soggetti che gli servono (spesso con anni «impossibili» come `2080`, per non collidere con niente di reale). Un test che si appoggia ai dati già presenti prova **solo i casi che quella popolazione per caso contiene**, e su un database ricostruito da zero passa **a vuoto**. ⚠️ E un file che fallisce **nel fixture** non esegue nessuna verifica: la sua copertura vale **zero**, non «parziale» — ma da fuori sembra un test che c'è. |
| **Roster** | Letteralmente l'**elenco di chi c'è e di chi fa cosa**: l'organico, il turnario, la «rosa» di una squadra. ⚠️ Da non confondere con *roaster*, che è il **tostatore** del caffè. | È l'elenco dei **processi** con accanto chi li esegue e per quale emittente: `dbops.vw_processi_roster`. La «rosa» della macchina, insomma — chi è in squadra e cosa gli tocca. |

---

✅ Questo glossario può essere esteso man mano che incontriamo altre sigle o
parole ricorrenti sia lato **DevOps** che **Database**.
