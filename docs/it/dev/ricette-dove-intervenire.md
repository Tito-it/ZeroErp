# Ricette: dove intervenire per…

> Questa pagina risponde a una domanda pratica: *"devo fare X — dove metto le mani, e in
> quale ordine?"*. Per ogni attività comune trovi i **punti di intervento in sequenza**, dal
> database fino alla schermata. Non rifà le regole già scritte altrove: dove serve, rimanda
> alle guide di dettaglio.
>
> Filo conduttore: in Zero ERP si parte **dal database** (dove vive la logica) e si sale verso
> backend e frontend. Vedi anche [Architettura a colpo d'occhio](/architettura) e
> [Trappole: cosa non fare](/dev/trappole).

---

## Ricetta 1 — Aggiungere un campo a un'entità

Esempio tipico: aggiungere un campo (es. una valuta, una nota, un flag) a un documento esistente.

**Ordine di intervento:**

1. **Database — struttura.** Crea un nuovo file di migrazione Liquibase in `00_schema/` che
   aggiunge la colonna (`ALTER TABLE … ADD COLUMN …`). Un changeSet per file, con
   numerazione progressiva. Vedi [Liquibase Setup & Workflow](/liquibase-setup-workflow) e
   [Linee Guida SQL](/linee-guida-sql).
2. **Database — valore di default (se serve).** Se il campo deve avere un valore calcolato o
   ereditato, aggiungi una funzione/trigger in `20_code/`. Vedi
   [Linee Guida Trigger](/linee-guida-trigger).
3. **Database — dati esistenti (se serve).** Se le righe già presenti vanno valorizzate,
   aggiungi un backfill in `80_data/`.
4. **Backend.** Esponi il campo dove serve: nel repository (lettura/scrittura), nel serializer
   (input/output API) e, se entra in un processo, nel service. Vedi le [linee guida API](/dev/api)
   e il [Catalogo Building Block backend](/dev/backend/catalogo-building-block-backend).
5. **Frontend.** Aggiorna lo store del dominio (il campo nei dati caricati/salvati) e il
   componente che lo mostra — di solito il **drawer** di modifica. Vedi gli
   [Standard frontend](/dev/frontend/frontend-standards) e il
   [Catalogo Building Block frontend](/dev/frontend/catalogo-building-block-frontend).

> ⚠️ Se il campo nasconde una **regola** (es. "questo valore dipende da quell'altro"), la regola
> va nel database, non nel backend. Vedi [Trappole](/dev/trappole).

---

## Ricetta 2 — Aggiungere uno stato a una macchina a stati

Gli stati dei documenti (preventivi, offerte, contratti, fatture…) **non sono scritti nel
codice**: sono dati di configurazione. Aggiungere uno stato significa, nella maggior parte dei
casi, aggiungere righe di configurazione — non logica.

**Ordine di intervento:**

1. **Database — l'elenco degli stati.** Aggiungi il nuovo stato nella tabella di configurazione
   degli stati del documento (es. `config.stati_doc_offerte`, `config.stati_doc_contratti`),
   tramite un seed in `80_data/`.
2. **Database — i passaggi consentiti.** Aggiungi le transizioni permesse da/verso il nuovo
   stato nella tabella delle transizioni (es. `config.stati_doc_offerte_transizioni`). Senza
   questo, lo stato esiste ma non è raggiungibile.
3. **Etichette multilingua.** Aggiungi le etichette (label) dello stato perché venga mostrato
   correttamente all'utente.
4. **Frontend.** Di norma niente logica nuova: lo stato e i suoi passaggi arrivano dal
   database. Verifica solo che eventuali colori/icone associati allo stato siano previsti.

> Questo è il vantaggio del modello **data-driven**: un nuovo stato non richiede codice nuovo,
> solo configurazione. Vedi il [Glossario di dominio](/glossario/glossario-utility) per i
> termini (lotto, contratto, ecc.).

---

## Ricetta 3 — Creare un nuovo dominio "tracciato" da zero

Quando serve un nuovo tipo di documento/processo che segue la forma standard del progetto
(testata + righe, stati, giornale, drawer).

**Ordine di intervento:**

1. **Database — struttura.** In `00_schema/` crea le tabelle: la **testata** (master, chiave
   UUID) e le **righe** collegate. Aggiungi i campi di tracciabilità standard
   (chi/quando inserisce e modifica). Vedi [Linee Guida SQL](/linee-guida-sql).
2. **Database — stati.** Crea le tabelle/righe di configurazione per gli stati e le transizioni
   (vedi Ricetta 2): il ciclo di vita del documento è data-driven.
3. **Database — comportamento.** In `20_code/` aggiungi i trigger di tracciabilità/giornale e
   le funzioni che incapsulano le regole (creazione, passaggi di stato, calcoli). Vedi
   [Linee Guida Trigger](/linee-guida-trigger).
4. **Backend.** Crea l'app del dominio con la struttura standard: `api/` (le API), `services/`
   (orchestrazione), `db/` o `repositories/` (accesso ai dati e chiamata alle funzioni del
   database). Vedi le [linee guida API](/dev/api).
5. **Frontend.** Crea la cartella del dominio con lo store Pinia, la lista (toolbar + tabella) e
   il drawer di modifica, seguendo il layout unico del progetto. Registra il dominio nella
   navigazione centrale. Vedi gli [Standard frontend](/dev/frontend/frontend-standards).

> Tutti i domini del progetto seguono questa stessa forma: capirne uno bene aiuta a capirli
> tutti.

---

{% include-markdown "signature-core.md" %}
</content>
