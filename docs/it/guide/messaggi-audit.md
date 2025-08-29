# Overview del sistema di Audit Logging (`dbops.audit_log`)

---

## Scopo generale

Il sistema di **audit logging** implementato nello schema `dbops` fornisce una tracciabilità centralizzata di tutte le operazioni rilevanti che avvengono nel database Zero ERP. Grazie alla tabella [`dbops.audit_log`](/dbzero/dbops/funzioni/audit_log) e a un set di funzioni dedicate, è possibile registrare eventi, esiti e contesti applicativi in modo coerente e standardizzato.

## Componenti principali

### Tabella `audit_log`

* Contiene i record di log con informazioni su **utente**, **timestamp**, **operazione**, **stato** e **messaggi**.
* Supporta sia eventi puntuali che sessioni di lunga durata.
* Può essere interrogata per analisi di processo, auditing di sicurezza o debug di errori.

### Funzioni correlate

* **[`dbops.fn_audit_begin`](/dbzero/dbops/funzioni/fn_audit_begin)**: avvia una nuova sessione di audit.
* **[`dbops.fn_audit_end`](/dbzero/dbops/funzioni/fn_audit_end)**: chiude la sessione, registrando l’esito.
* **[`dbops.fn_audit_log_once`](/dbzero/dbops/funzioni/fn_audit_log_once)**: registra un singolo evento atomico senza sessione.

## Modalità di utilizzo

* **Automazioni batch**: usano `fn_audit_begin` all’avvio, loggano step intermedi e concludono con `fn_audit_end`.
* **Trigger e funzioni semplici**: possono usare `fn_audit_log_once` per registrare eventi isolati.
* **Gestione errori**: le funzioni di audit sono integrate con il sistema di logging centralizzato [`dbops.error_log`](/dbzero/dbops/tabelle/error_log), permettendo una diagnosi completa.

## Vantaggi

1. **Centralizzazione**: tutte le operazioni rilevanti convergono in un unico punto di tracciamento.
2. **Analisi storica**: possibile ricostruire il ciclo di vita di un processo.
3. **Flessibilità**: supporto a log sia atomici che session-based.
4. **Debug facilitato**: consente di identificare rapidamente errori e anomalie.

## Esempio pratico

* Durante una migrazione massiva:

  * `fn_audit_begin` registra l’inizio.
  * Gli step di import loggano eventuali anomalie con `fn_audit_log_once`.
  * `fn_audit_end` chiude la sessione, indicando se la migrazione è stata completata con successo o con errori.

---

Questo sistema costituisce la base per tutte le **automazioni di logging** nel progetto Zero ERP, garantendo tracciabilità, affidabilità e conformità alle best practice di auditing.

---
{% include-markdown "signature-core.md" %}
