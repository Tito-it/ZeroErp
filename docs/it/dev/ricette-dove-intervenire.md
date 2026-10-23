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
   [Linee Guida SQL](/linee-guida-sql). Le regole delle colonne stanno lì: `NOT NULL` dove il
   modello lo permette, un `numeric` nasce col CHECK «finito» (§7d), niente `character(n)`
   (§7e), `timestamptz` e mai `timestamp` nudo (§11.10). ⚠️ Se la colonna entra in un guard o
   in un trigger `UPDATE OF`, quel trigger va rivisto: non la vede da solo.
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

Gli stati dei documenti (preventivi, offerte, contratti, fatture…) sono **dati** di
configurazione, ma non tutte le famiglie hanno la stessa forma, e i passaggi di stato spesso
hanno **effetti** scritti nel codice. Aggiungere uno stato è quasi sempre configurazione **più**
una verifica del codice che reagisce ai passaggi.

**Ordine di intervento:**

1. **Database — capire la forma della famiglia.** Prima di scrivere, si guarda come quella
   famiglia tiene i suoi stati. Le forme sono quattro:
   - una tabella `config.transizioni_stati_*`;
   - una tabella di transizioni con colonne sue (es. `config.stati_doc_offerte_transizioni`);
   - un `CASE` in una funzione;
   - transizioni scritte negli `IF` di una madre.

   La forma si legge dalla doc auto-generata della tabella degli stati e del suo guard di
   transizione. Se la forma è una delle ultime due, lo stato nuovo **è** codice.
2. **Database — lo stato e i passaggi consentiti.** Stato e transizioni si aggiungono al CSV del
   loro seed in `80_data/`, mai con un `UPDATE` ([Linee Guida SQL](/linee-guida-sql) §11.2).
   Senza la transizione, lo stato esiste ma non è raggiungibile.
3. **Database — gli effetti del passaggio.** Le funzioni madri del cambio di stato (es.
   `fn_cambia_stato_ddt`) ramificano su coppie di stati: movimenti di magazzino, numerazione,
   blocchi della testata. Una riga di transizione nuova **non** aggancia da sola un effetto: si
   cercano i rami che nominano gli stati vicini e si decide se il nuovo ci entra.
4. **Database — le azioni proposte.** Il pulsante del passaggio nasce dalla check che la madre
   chiama (`fn_check_*` / `fn_available_actions_<dominio>`), non da una lista a parte
   ([Linee Guida SQL](/linee-guida-sql) §12). Un passaggio rifiutato solleva un codice errore
   registrato.
5. **Etichette multilingua.** Aggiungi le etichette (label) dello stato perché venga mostrato
   correttamente all'utente.
6. **Frontend.** Verifica che eventuali colori/icone associati allo stato siano previsti.

> Il modello è **data-driven** dove la famiglia lo è: lo stato è un dato, i suoi effetti spesso
> no. Vedi il [Glossario di dominio](/glossario/glossario-utility) per i termini (lotto,
> contratto, ecc.).

---

## Ricetta 3 — Creare un nuovo dominio "tracciato" da zero

Quando serve un nuovo tipo di documento/processo che segue la forma standard del progetto
(testata + righe, stati, giornale, drawer).

**Ordine di intervento:**

0. **Prima di scrivere.** Si cercano i brief aperti sullo stesso tema o sugli stessi oggetti
   (regola «un tema, un brief») e i building block già esistenti negli schemi `script` e
   `dbops`: spesso la «seconda occorrenza» è la propria, e la prima esiste già.
1. **Database — struttura.** In `00_schema/` crea le tabelle: la **testata** e le **righe**
   collegate. I documenti hanno `id bigint` interno più `uid uuid` stabile, come quelli
   esistenti (es. `vendite.ordini` nella doc auto-generata). L'emittente si nomina
   `emittente_soggetto_ruolo_id`, e il tipo di documento usa il vocabolario di
   `config.sorgenti`. Vedi [Linee Guida SQL](/linee-guida-sql) §2 e §7d-§7e (le regole delle
   colonne).
2. **Database — perimetro dei dati.** Le tabelle del documento stanno nel perimetro della RLS
   per emittente: policy sulla testata, e righe e satelliti dentro per legame. Il presidio
   `vw_rls_perimetro_scoperto` vede una tabella dimenticata. Lo storico si arma da solo. Vedi
   [Linee Guida SQL](/linee-guida-sql) §10 e la [trappola sul
   perimetro](/dev/trappole).
3. **Database — tracciabilità.** Audit, `tx_id`, storico, blocco colonne e `attivo` **non** si
   scrivono a mano: li applica per regola la passata `ci_apply` del framework delle automazioni.
   Si verifica che la tabella nuova ricada nelle regole. Vedi [Automazione DB](/guide/automazione-db).
4. **Database — stati.** Vedi la Ricetta 2, partendo da una forma esistente invece di
   inventarne una nuova.
5. **Database — comportamento.** In `20_code/` le regole stanno in funzioni **madri** atomiche
   ([Linee Guida SQL](/linee-guida-sql) §5b), con la check che alimenta sia il pulsante sia la
   madre (§12). Gli errori usano codici registrati, ciascuno col suo messaggio. Per i trigger:
   nome con la fase (che ne decide l'ordine) e attenzione a `UPDATE OF`
   ([Linee Guida Trigger](/linee-guida-trigger)).
6. **Database — test.** pgTAP che girano come applicazione e costruiscono il loro mondo coi
   builder di `dbops`. Vedi [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test).
7. **Backend.** Crea l'app del dominio con la struttura standard: `api/` (le API), `services/`
   (orchestrazione), `db/` o `repositories/` (accesso ai dati e chiamata alle funzioni del
   database). Vedi le [linee guida API](/dev/api).
8. **Frontend.** Crea la cartella del dominio con lo store Pinia, la lista (toolbar + tabella) e
   il drawer di modifica, seguendo il layout unico del progetto. Registra il dominio nella
   navigazione centrale. Vedi gli [Standard frontend](/dev/frontend/frontend-standards).

> I domini del progetto si somigliano più nei nomi che nella forma: testate, macchine a stati e
> capability sono cresciute un cantiere alla volta. Si parte dal dominio più vicino e più
> recente e se ne segue la forma, invece di inventarne una nuova.

---

{% include-markdown "signature-core.md" %}
</content>
