# Glossario – Termini del dominio utility

> Questo glossario raccoglie i termini ricorrenti nella documentazione di Zero ERP
> relativi al settore utilities (gas, energia elettrica, idrico).
> Per ciascun termine si fornisce il significato nel contesto del sistema.

---

| Termine | Significato |
| ------- | ----------- |
| **PDP** | **Punto Di Prelievo** — rappresenta il contatore o allaccio fisico presso un indirizzo. Nel database corrisponde alla tabella `anagrafiche.pdp`. Per il gas si chiama anche PDR, per l'energia elettrica POD, ma nel sistema usiamo un'unica entita PDP indipendente dalla commodity. |
| **POD** | **Point Of Delivery** — codice identificativo nazionale per un punto di prelievo di energia elettrica (es. `IT001E12345678`). Nella pratica e un tipo specifico di PDP. |
| **PDR** | **Punto Di Riconsegna** — codice identificativo nazionale per un punto di prelievo gas (es. `12345678901234`). Nella pratica e un tipo specifico di PDP. |
| **Istanza (utility)** | Il ciclo tecnico-commerciale di un servizio su un indirizzo per un determinato soggetto. In pratica: quando un cliente sottoscrive un contratto gas su un certo indirizzo, nasce un'istanza. L'istanza non e il cliente: esiste prima del contratto e sopravvive alla sua chiusura come record storico. |
| **Billing Account (BA)** | L'account di fatturazione associato a un'istanza. Identifica *a chi fatturare* e *con quale codice*. Puo esistere gia in fase precontrattuale (prima che il cliente firmi). Supporta una gerarchia padre/figlio per aggregare la fatturazione di piu utenze. |
| **Cliente** | Il record che specializza un soggetto nel ruolo di cliente per una specifica istanza. Contiene le date di attivazione, chiusura, e il legame con il billing account. |
| **Soggetto** | Persona fisica o giuridica registrata nel sistema (tabella `anagrafiche.soggetti`). Un soggetto puo avere piu ruoli (cliente, fornitore, gestore) e piu istanze per utility diverse. |
| **Ruolo** | La funzione che un soggetto svolge nel sistema (es. CLIENTE, FORNITORE). Registrato in `anagrafiche.soggetti_ruoli`. Un soggetto ha un solo ruolo CLIENTE, anche se e intestatario di piu utenze. |
| **Subentro** | Passaggio di titolarita su un PDP: un cliente esce, un altro entra sullo stesso punto di prelievo. Il sistema chiude il cliente precedente, crea una nuova istanza per il nuovo intestatario e mantiene la catena storica. Sinonimo: *voltura*. |
| **Disdetta / Cessazione** | Chiusura del servizio senza subentro. Il cliente disdice, nessuno subentra, e il PDP torna disponibile per future attivazioni. Il billing account resta attivo fino alla chiusura di eventuali partite aperte (fatture finali, conguagli). |
| **Parent istanza** | L'istanza precedente nella catena di subentri sullo stesso PDP. Serve per tracciabilita storica e per la clonazione automatica dei dati catastali. |
| **Periodo** | L'intervallo temporale di validita commerciale di un cliente, calcolato automaticamente come `[data_attivazione, data_chiusura)`. Il vincolo di esclusione sul PDP impedisce che due clienti abbiano periodi sovrapposti sullo stesso punto di prelievo. |

---

{% include-markdown "signature-core.md" %}
