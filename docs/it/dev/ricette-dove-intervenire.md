# Ricette: dove intervenire per…

> **Ultimo aggiornamento**: 8 novembre 2026
>
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
4. **Backend.** Non ci sono serializer DRF: il campo entra in tre punti.
   - Il **repository** (`db/`) lo legge e lo scrive, e il `TypedDict` della riga in `types.py`
     lo dichiara: lo legge `mypy` in CI.
   - Il **contratto** del service: la chiave entra fra le ammesse
     (`PayloadValidator.solo_chiavi_ammesse`), letta col metodo del suo tipo
     (`optional_decimal`, `optional_enum`, `optional_bool`…, mai `bool(payload.get(...))`).
   - Il **dizionario dei tipi** dello schema OpenAPI del dominio (`schema_da_contratto`): una
     chiave del contratto senza tipo è un errore all'import.

   Vedi le [linee guida API](/dev/api) e il
   [Catalogo Building Block backend](/dev/backend/catalogo-building-block-backend)
   (`PayloadValidator`, `schema_da_contratto`).
5. **Frontend.** Il campo entra nel form del **drawer** e nel payload che lo store manda. Le
   etichette vanno in `it.json` **e** in `en.json`, nella radice dell'area del codice
   (`vendite.ordini.*`), perché la parità è controllata. Se il campo va **in lista**, la
   colonna non si scrive nel template: è una riga del catalogo `ui.lista_colonna` (un dato,
   creato in-app o con `scripts/gen_seed_lista.py`), e la vista della lista deve proiettarlo.
   Vedi gli [Standard frontend](/dev/frontend/frontend-standards) («Regola zero della lista»,
   «Multilingua») e il
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
5. **Etichette multilingua.** Le chiavi che il database emette (`label_key` e `reason_key`
   delle capability, il `meta` delle transizioni) vanno in `it.json` **e** in `en.json`,
   nella radice dell'area (`vendite.ordini.*`). ⚠️ Una chiave che non esiste non dà errore:
   a video si vede il testo mancante. Lo trova `scripts/check_i18n_keys.py`, che legge anche
   i seed del DB. Vedi gli [Standard frontend](/dev/frontend/frontend-standards)
   («Struttura chiavi»).
6. **Backend e frontend — chi nomina gli stati.** Il colore dello stato sta nella mappa della
   famiglia in `core/utils/severity.js`, letta dal `codice_interno` che arriva dal backend.
   ⚠️ Uno stato che manca nella mappa non dà errore: diventa grigio (`secondary`). Prima di
   chiudere si cercano i codici degli stati vicini nel backend e nel frontend: un ramo che li
   nomina (un filtro, un'etichetta, un controllo) **non** vede da solo lo stato nuovo. Il
   pulsante del passaggio, invece, non si tocca: arriva dalla capability (passo 4).

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
   colonne). Se il documento, o una sua riga, **nasce da** un altro documento, la provenienza
   usa le colonne del modello comune (`sorgente_tipo_id`, la chiave del documento,
   `sorgente_riga`), con il loro `CHECK` di forma e il guard unico: §6e delle linee guida e la
   guida [Sorgente polimorfa](/guide/sorgente-polimorfa).
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
7. **Backend.** L'app del dominio ha la struttura tipo di [api.md](/dev/api) («Struttura tipo
   per app»): `api/` (view e `urls_v1.py`), `services/` (orchestrazione), `db/` (repository
   che chiamano le funzioni del database), `types.py`, `tests/`.
   - Le view ereditano da `DomainAPIView` e dichiarano la loro `area_funzionale`. L'area deve
     esistere a catalogo (`config.aree_funzionali`, dal team DB), e un test confronta le aree
     delle view col catalogo.
   - Le scritture passano da `handle_post_json`. Un gesto irreversibile (emettere, numerare,
     registrare) chiede la `Idempotency-Key`.
   - Il contratto del payload si valida con `PayloadValidator`, e lo schema OpenAPI si legge
     dal contratto (`schema_da_contratto`), non si ricopia.
   - I codici d'errore nascono a catalogo (team DB) e arrivano al backend con
     `./manage-env.sh genera_error_policies`.
   - Test unitari (`SimpleTestCase`) più quelli sul DB vero (`richiedi_db_provvisto`) per la
     giuntura con le funzioni del database.
   - Ogni rotta nuova ha la sua pagina in `docs/it/backend/<dominio>/manual/`, e la copertura
     è controllata (`core/tests/test_copertura_doc_api.py`).

   Vedi le [linee guida API](/dev/api) («Checklist nuovo endpoint») e il
   [Catalogo Building Block backend](/dev/backend/catalogo-building-block-backend).
8. **Frontend.** La cartella del dominio (`api/`, `stores/`, `views/`, `components/`) segue la
   struttura degli [Standard frontend](/dev/frontend/frontend-standards).
   - La lista è una `<ListaConfigurabile codice="…">`: le colonne sono righe di catalogo
     (`ui.lista_definizione` e `ui.lista_colonna`), non una `DataTable` scritta a mano.
   - Il drawer è un drawer **autonomo**, apribile dalla lista e dagli altri drawer, con le
     azioni dalla capability (`DrawerActionsBar`) e la modalità sola lettura.
   - Le rotte vanno in `router/`, la voce di menu in `core/navigation.js`.
   - Ciò che il dominio aggiunge a `core` e ai motori (`pratiche`, `documenti`) si iscrive dal
     suo `iscrizioni.js`: `core/` non importa mai un dominio, e un dominio ne importa un altro
     solo nel verso delle FK («Confini fra domini»).
   - Il [Catalogo Building Block frontend](/dev/frontend/catalogo-building-block-frontend) si
     guarda prima di scrivere un componente.

> I domini del progetto si somigliano più nei nomi che nella forma: testate, macchine a stati e
> capability sono cresciute un cantiere alla volta. Si parte dal dominio più vicino e più
> recente e se ne segue la forma, invece di inventarne una nuova.

---

{% include-markdown "signature-core.md" %}
</content>
