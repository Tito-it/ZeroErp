# **Architettura**

***In questa sezione descriviamo l'architettura del progetto Zero ERP, evidenziando i principali componenti software, i flussi di comunicazione e le integrazioni con il database e gli strumenti di migrazione.***

## Componenti principali

- **Backend:** Django (Python) – API REST e logica di business

- **Frontend:** Vue 3 – interfaccia utente single-page

- **Database:** PostgreSQL (schema-first, zero-erp schema)

- **Migrazioni:** Liquibase per versionare e applicare le modifiche allo schema

- **Cache / Broker:** Redis / RabbitMQ (opzionali, per code e sessioni)


## Versioni supportate
Tutti i componenti sono testati con le versioni indicate in:
[Versioni supportate](versioni-supportate.md).



## Flusso di richieste

- L'utente interagisce con il client Vue3

- Le chiamate HTTP arrivano alle API Django

- Le transazioni DB vengono gestite da Liquibase per le modifiche di schema

- Le query e gli aggiornamenti vengono eseguiti in PostgreSQL
 
---
{% include-markdown "signature-core.md" %}


