# Glossario di dominio

> Questo glossario raccoglie i termini ricorrenti nella documentazione di Zero ERP.
> È diviso in due parti: i **termini del settore utility** (gas, energia elettrica, idrico)
> e i **termini di dominio ZeroERP** trasversali (ciclo vendite, processi, fatturazione).
> Per ciascun termine si fornisce il significato nel contesto del sistema.

---

## Termini del settore utility

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

## Termini di dominio ZeroERP

> Termini del ciclo vendite e dei processi, validi per tutti i settori (non solo utility).
> Dove esiste una guida dedicata, il termine vi rimanda per i dettagli.

| Termine | Significato |
| ------- | ----------- |
| **Pratica / Flusso** | In Zero ERP **ogni operazione è una pratica**: dall'inserimento di un nuovo cliente alla gestione di un reclamo, fino alla revisione di un contratto. La pratica segue passi prestabiliti che non si possono saltare; il **flusso** è il percorso che la pratica compie da inizio a fine. Vedi [Gestione Pratiche](/guide/gestione-pratiche). |
| **Commessa** | Il "raccoglitore" che mette insieme tutto ciò che sarà fatturato a un cliente. Preventivi, ordini, contratti, bolle e consumi confluiscono prima nella commessa e solo da lì si arriva alla fattura: non ci sono scorciatoie. Vedi [Gestione Commesse](/guide/gestione-commesse). |
| **Preventivo** | La proposta di prezzo iniziale fatta al cliente, con l'elenco di prodotti/servizi e il totale con IVA. Si può aggiornare creando nuove versioni (revisioni); resta valida l'ultima approvata. Vedi [Gestione Preventivi](/guide/gestione-preventivi). |
| **Offerta commerciale** | Una proposta commerciale formale al cliente. Quando viene accettata dà origine a **un solo contratto**. *(Termine ancora in fase di definizione: la documentazione di dettaglio è in lavorazione.)* |
| **Contratto** | L'accordo attivo con il cliente. Al momento dell'attivazione "fotografa" i prezzi del listino in vigore, così restano fissi anche se il listino cambia in seguito. Il sistema impedisce che esistano due contratti sovrapposti per lo stesso servizio. Vedi [Gestione Contratti](/guide/gestione-contratti). |
| **Listino** | L'insieme dei prezzi, organizzato per versioni nel tempo. Quando si calcola un prezzo, il sistema sceglie in ordine: prima eventuali promozioni, poi il prezzo concordato a contratto, infine il prezzo della categoria del cliente. Vedi [Gestione Listini e Pricing](/guide/gestione-listini). |
| **Emittente** | L'azienda che **emette** i documenti commerciali e le fatture. Quando si gestiscono più aziende, ogni operatore è collegato a una sola di esse. *(Da verificare rispetto alle modifiche in corso sul legame operatore–emittente.)* |
| **Emittente fiscale** | L'azienda a cui è intestato un documento ai fini fiscali (es. su un preventivo). Va sempre indicata nei documenti di vendita. *(Da validare.)* |
| **Fatturazione (pipeline)** | Il processo che, partendo da quanto raccolto nella commessa, produce le fatture, lavorandole a gruppi. Vedi [Fatturazione](/guide/fatturazione). |
| **Lotto** | Un gruppo di fatture elaborate insieme. Attraversa tre fasi: bozza, emessa e definitiva. Vedi [Fatturazione](/guide/fatturazione). |

---

{% include-markdown "signature-core.md" %}
