# Estensioni PostgreSQL utilizzate in Zero ERP

> **Ultimo aggiornamento**: 25 ottobre 2026
>
> **Destinatari**: chi installa un server, chi scrive changeSet o funzioni che usano un'estensione
>
> **Vedi anche**:
>
> * [Installazione](/installazione) — quali pacchetti servono sul server e in che passo si creano le estensioni
> * [Introduzione a PostgreSQL](/postgresql/intro)

Le estensioni le crea il primo passo di Liquibase, da superuser (`changelog-provision-pre.yaml` e la
baseline): un'estensione nuova si aggiunge lì, non a mano su una macchina. La versione installata non
si scrive qui: si legge da `pg_extension` del database.

---

## Le estensioni

| Estensione | A che cosa serve nel progetto | Dove si vede |
| --- | --- | --- |
| `plpgsql` | il linguaggio di funzioni, procedure e trigger | ovunque |
| `btree_gist` | i vincoli di **esclusione** che mescolano `=` e sovrapposizione di intervalli (una sola versione valida per periodo) | i vincoli `ex_*_no_overlap` (listini, contratti, promozioni, sospensioni, template…) |
| `pg_trgm` | la ricerca testuale per somiglianza («contiene», prefisso) | gli indici GIN `gin_trgm_ops`, per esempio su `indirizzi_dettaglio.indirizzo_normalizzato`; regole in [Linee guida SQL §8.3](/linee-guida-sql#83-policy-di-ricerca-testuale-pg_trgm-e-fts) |
| `unaccent` | togliere gli accenti nella normalizzazione dei testi | `script.fn_norm_testo` |
| `postgis` | il tipo `geometry` e gli indici spaziali | le colonne di geolocalizzazione degli indirizzi (`civic_geoloc`, `street_geoloc`, `geoloc`) con indice GiST |
| [`dblink`](/postgresql/dblink) | il canale dei registri **fuori transazione**: una riga di log che sopravvive al rollback | errori, verbale dei job falliti, `tx_id` di sessione, audit delle automazioni |
| [`pgagent`](/postgresql/pgAgent) | lo schedulatore dei lavori a orario | schema `pgagent`; i lavori in [Processi pgAgent](/guide/processi-pgagent-funzionali) |
| `plpgsql_check` | il controllo statico delle funzioni (riferimenti a oggetti che non esistono più) | il guardrail dei riferimenti morti, in CI |
| `pgtap` | i test del database | `db/pgtap/`; la crea il passo della suite in CI e `scripts/ci-local.sh` sullo scratch, non Liquibase |

### Installate ma non usate dal codice

Al 25 ottobre 2026 nessuna funzione, vista, default o indice del progetto usa queste tre. Restano perché
le crea la baseline:

* **[`pgcrypto`](/postgresql/pgcrypto)**: gli UUID vengono da `uuidv7()` e `gen_random_uuid()`, che
  sono del motore; la cifratura dei segreti è applicativa (vedi la sua pagina).
* **`uuid-ossp`**: le sue funzioni (`uuid_generate_v*`) non compaiono in nessun oggetto.
* **`postgis_topology`**: nessun oggetto usa lo schema `topology`.

**Si tengono** (Tid, 25 ottobre 2026). Le crea la baseline della prima generazione, che non si tocca
(Linee guida SQL §11.11): un `DROP EXTENSION` in un changeSet nuovo le cancellerebbe subito dopo averle
create, su ogni database costruito da zero, e il pacchetto sul server servirebbe lo stesso. Se ne
riparla solo se un giorno si rifà la baseline. Se un lavoro nuovo ne ha bisogno, le usa.

### Installarle sul server

Il server deve avere i pacchetti di PostGIS (con `postgis_topology`), `plpgsql_check`, pgAgent e pgTAP;
le altre sono nel pacchetto `contrib` di PostgreSQL. Il dettaglio è nella guida di
[Installazione](/installazione), sezione «Le estensioni».

`pgagent` è l'unica che il changelog crea **solo se il pacchetto c'è** (`pg_available_extensions`): su
una macchina senza pgAgent l'installazione prosegue e i lavori a orario non esistono.

---
{% include-markdown "signature-core.md" %}
