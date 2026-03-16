# Introduzione a PostgreSQL

Zero ERP utilizza PostgreSQL, un database relazionale open-source potente e altamente estensibile, riconosciuto per robustezza, scalabilita' e aderenza agli standard SQL. La scelta di PostgreSQL risponde alle esigenze specifiche del progetto Zero ERP, dove e' fondamentale garantire integrita' dei dati, elevate prestazioni e flessibilita' nello sviluppo e nella gestione.

---

## Perche' PostgreSQL?

* **Integrita' e Affidabilita'**: PostgreSQL garantisce consistenza e durabilita' dei dati attraverso avanzati meccanismi di transazione e controllo dei vincoli.
* **Estendibilita'**: supporta numerose estensioni come `dblink` per comunicazioni inter-database e `pgcrypto` per sicurezza e crittografia.
* **Performance e Scalabilita'**: offre eccellenti prestazioni anche con dataset molto grandi e carichi di lavoro complessi, grazie a strumenti come gli indici avanzati e il query planner intelligente.
* **Community e Supporto**: ampia comunita' di utenti e sviluppatori, che offre documentazione estesa e risorse utili per supporto e manutenzione.

---

## Struttura della documentazione del Database

Questa sezione della documentazione include:

* **Installazione e configurazione iniziale**: dettagli operativi per configurare PostgreSQL in modo ottimale per Zero ERP.
* **Estensioni utilizzate**: panoramica delle estensioni PostgreSQL adottate, come `dblink`, `pgcrypto`, e altre.
* **Parametri personalizzati (GUC)**: guida alla definizione, utilizzo e gestione dei parametri applicativi personalizzati per adattare il database alle specifiche esigenze di Zero ERP.

Seguendo questa documentazione sara' possibile gestire al meglio PostgreSQL all'interno di Zero ERP, sfruttandone pienamente le potenzialita' e garantendo stabilita' e affidabilita' al sistema.

---

## Gestione delle chiavi UNIQUE con valori NULL in PostgreSQL

> ⚠️ **Nota tecnica importante — Best Practice Zero ERP**

In PostgreSQL, secondo lo **standard SQL ANSI**, un valore `NULL` *non e' considerato uguale ad un altro `NULL`*.
Questo significa che **gli indici `UNIQUE` non impediscono l'inserimento di piu' righe con gli stessi campi impostati a `NULL`**, poiche' tecnicamente si tratta di valori "sconosciuti" e quindi non confrontabili.

Questa regola e' corretta in molti scenari applicativi, ma puo' risultare **problematicamente permissiva** in casi, come Zero ERP, dove alcuni campi — anche se opzionali — concorrono alla **definizione univoca dell'entita'** (es. un indirizzo fisico normalizzato).

---

### Esempio reale dal progetto

Nel caso della tabella:

```text
anagrafiche.indirizzi_dettaglio
```

vogliamo garantire che **ogni indirizzo fisico** (stradario + civico + estensione + piano + interno, ecc.) sia rappresentato da **una sola riga univoca**.

Per ottenere correttamente questa unicita', e' stato definito un indice `UNIQUE` che normalizza i valori `NULL` tramite `COALESCE`:

```sql
CREATE UNIQUE INDEX ix_uq_indirizzi_dettaglio_norm
ON anagrafiche.indirizzi_dettaglio (
    stradario_id,
    COALESCE(civico, ''),
    COALESCE(estensione_civico, ''),
    COALESCE(palazzina, ''),
    COALESCE(scala, ''),
    COALESCE(piano, ''),
    COALESCE(interno, '')
);
```

In questo modo, due righe con tutti i campi strutturali identici (anche se valorizzati a `NULL`) vengono considerate effettivamente duplicate e la `UNIQUE` impedisce inserimenti incoerenti.

---

## Best Practice Zero ERP per gli indici UNIQUE

| Caso                                                      | Raccomandazione                             |
| --------------------------------------------------------- | ------------------------------------------- |
| Il campo e' facoltativo ma **non definisce l'identita'**   | Non includerlo nell'indice `UNIQUE`         |
| Il campo e' facoltativo ma **definisce l'identita' logica** | Includerlo nell'indice usando `COALESCE()`  |
| Il campo e' sempre valorizzato                             | Includerlo normalmente nell'indice `UNIQUE` |

> **Linea guida pratica**: ogni volta che si progettano vincoli `UNIQUE`, valutare se i campi opzionali concorrono all'identita' reale dell'oggetto.
> Se si' → usarli con `COALESCE` nella definizione dell'indice.

Questa regola e' essenziale per evitare **duplicazioni silenti** e garantire consistenza logica dei dati, specialmente in ambiti documentali, fiscalita', mapping geografico e gestione di indirizzi.

---

Questa best practice va tenuta presente anche nello sviluppo futuro di tabelle simili (es. contatti, localizzazioni, strutture gerarchiche e cicliche, configurazioni parametriche complesse, ecc.).
