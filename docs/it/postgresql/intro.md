# Introduzione a PostgreSQL

> **Ultimo aggiornamento**: 25 ottobre 2026
>
> **Destinatari**: chi si avvicina al database di Zero ERP e cerca da dove partire
>
> **Vedi anche**:
>
> * [Linee guida SQL](/linee-guida-sql) — le convenzioni di progetto (naming, chiavi, indici, RLS, changeSet)
> * Doc auto-generata dei singoli schemi (`dbzero/<schema>/…`) — il contratto di ogni tabella, indice e funzione

Zero ERP utilizza PostgreSQL, un database relazionale open-source potente e altamente estensibile, riconosciuto per robustezza, scalabilità e aderenza agli standard SQL. Zero ERP è un progetto **DB-first**: la logica di business sta nel database, Django la orchestra ed espone le API, Vue fa solo presentazione. Per questo l'integrità dei dati, le prestazioni e la flessibilità del database sono il centro del sistema.

La versione in uso non è scritta qui: si legge dalla configurazione dell'ambiente (vedi [Aggiornamento versione](/postgresql/aggiornamento-versione-postgresql)).

---

## Perché PostgreSQL?

* **Integrità e affidabilità**: garantisce consistenza e durabilità dei dati attraverso transazioni, vincoli e trigger.
* **Estendibilità**: supporta numerose estensioni, come `dblink` per le comunicazioni fra database e `pgcrypto` per la crittografia.
* **Prestazioni e scalabilità**: buone prestazioni anche con dataset grandi e carichi complessi, grazie agli indici avanzati e al query planner.
* **Sicurezza nel motore**: Row Level Security, ruoli e privilegi permettono di far rispettare i perimetri di accesso dal database stesso, non solo dall'applicazione.
* **Community e supporto**: ampia comunità di utenti e sviluppatori, documentazione estesa.

---

## Struttura della documentazione del database

Questa sezione comprende:

* [Aggiornamento versione](/postgresql/aggiornamento-versione-postgresql) — come si aggiorna il cluster PostgreSQL, in sviluppo o in produzione.
* [Parametri personalizzati (GUC)](/postgresql/parametri-personalizzati-(GUC)) — definizione, uso e gestione dei parametri applicativi di sessione.
* [Estensioni utilizzate](/postgresql/estensioni-utilizzate) — la panoramica delle estensioni adottate, con le pagine di dettaglio su [dblink](/postgresql/dblink), [pgAgent](/postgresql/pgAgent) e [pgcrypto](/postgresql/pgcrypto).
* [Row Level Security](/postgresql/row-level-security) — come funziona la RLS in PostgreSQL; le convenzioni di progetto stanno nelle linee guida SQL.

---

## Chiavi UNIQUE e valori NULL

Per lo standard SQL un `NULL` non è uguale a un altro `NULL`: un indice `UNIQUE` di default lascia passare due righe con gli stessi campi a `NULL`. Quando un campo opzionale fa parte dell'identità della riga (un indirizzo, l'ambito di un parametro, una chiave di raggruppamento), le righe che dovevano essere una convivono in silenzio.

La regola di progetto (`NULLS NOT DISTINCT` nell'indice, `IS NOT DISTINCT FROM` nel lookup, e gli altri punti in cui la chiave è scritta) sta nelle [Linee guida SQL §8.4-bis](/linee-guida-sql#84-bis-indici-unique-con-colonne-nullable).
