# Personalizzazioni liste — Sviluppi differiti

**Modulo:** UI / Presentazione
**Riferimento:** [sviluppo-personalizzazioni-liste.md](sviluppo-personalizzazioni-liste.md) — documento architetturale principale
**Stato:** backlog — non bloccante, da affrontare dopo il Blocco E del piano principale

Questo documento raccoglie le funzionalità previste nell'architettura ma escluse dall'implementazione iniziale. Sono differite perché non necessarie al funzionamento della personalizzazione di base, non dipendono da lavori in corso e possono essere aggiunte in modo incrementale senza riscrivere ciò che è già implementato.

---

## DEF-1 — Export CSV/Excel con metadati filtri

**Descrizione**
L'export di una lista deve generare un file (CSV o Excel) che includa non solo i dati visibili ma anche un riepilogo dei filtri attivi al momento dell'export. Senza questo, un CSV filtrato appare come una lista completa e chi lo riceve non può sapere che è un sottoinsieme.

**Comportamento atteso**
- In Excel: foglio aggiuntivo `Filtri applicati` con i criteri attivi (colonna, operatore, valore)
- In CSV: righe di intestazione commentate (es. `# Filtro: stato = ATTIVO`) prima dell'intestazione delle colonne
- Le colonne esportate seguono la stessa logica di `fn_resolve_lista_config`: no colonne `visibile:false`, no colonne `LETTURA`, no colonne `tipo_colonna = 'azione'`

**Dipendenze**
- Blocco E completato (prima lista reale funzionante)
- Formato `filtri_default` JSONB concordato (nota aperta §10 del documento principale)
- Libreria Python per generazione Excel (es. `openpyxl`) — da aggiungere a `backend/requirements.in` previo accordo

**Impatto**
- DB: nessuno
- Backend: nuovo endpoint `GET /api/v1/ui/liste/{codice}/export` (o parametro `?format=csv|xlsx` su endpoint esistente)
- Frontend: pulsante export nella toolbar `<ListaConfigurabile>`

---

## DEF-2 — Notifica "preset aggiornato"

**Descrizione**
Quando un admin modifica un preset di ruolo o di sistema, gli utenti che avevano salvato una preferenza basata su quel preset non vengono avvisati. Il campo `lista_preferenza_utente.preset_base_data_update` è già nel modello per supportare questo scenario.

**Comportamento atteso**
- Al `GET .../config`, **se** `preferenza.preset_base_id IS NOT NULL` **e** `lista_preset.data_update > lista_preferenza_utente.preset_base_data_update`, il JSONB di risposta include un flag aggiuntivo: `"preset_aggiornato": true`
- Il frontend mostra un banner non intrusivo: *"La configurazione di base del tuo ruolo è stata aggiornata. Vuoi vedere le novità?"* con due azioni: "Vedi novità" (apre la modale con le colonne nuove evidenziate) e "Ignora"
- Se l'utente preme "Vedi novità" e salva, `preset_base_data_update` viene aggiornato al valore corrente del preset

**Regola obbligatoria — `preset_base_id` può essere NULL**
Post landing DB-2 (FK `ON DELETE SET NULL`) + trigger `trg_ui_lista_preferenza_utente_z90_clear_preset_base_ts_upd` (atterrato 2026-05-07), se l'admin elimina il preset di base la preferenza utente sopravvive con `preset_base_id = NULL` e `preset_base_data_update = NULL`. In questo caso **il badge non va mostrato** — il preset di riferimento non esiste più, non c'è nulla con cui confrontare. Condizione completa BE/FE:

```js
const showPresetUpdatedBadge =
  preferenza.preset_base_id !== null &&
  preferenza.preset_base_data_update !== null &&
  presetCorrente.data_update > preferenza.preset_base_data_update;
```

**Dipendenze**
- Blocco D completato (componente Vue con modale personalizzazione)
- Accordo su UX della notifica (banner, toast, badge?)

**Impatto**
- DB: nessuno (campo già presente, trigger già landed)
- Backend: logica aggiuntiva in `ui_service.py` nel metodo che invoca `fn_resolve_lista_config` — guard `preset_base_id IS NOT NULL` prima del confronto timestamp
- Frontend: banner condizionale + stato "colonne nuove del preset" nella modale

---

## DEF-3 — Viste nominate multiple per utente

**Descrizione**
Oggi ogni utente ha una sola preferenza per lista (`UNIQUE (auth_user_id, lista_id)`). In futuro si potrebbe permettere di salvare più viste nominate — es. "Clienti morosi", "Clienti TOP 10", "Vista rapida" — e passare da una all'altra senza dover riconfigurare ogni volta.

**Comportamento atteso**
- Ogni vista nominata è un record distinto, con `nome VARCHAR` e `is_attiva BOOLEAN`
- La vista attiva è quella caricata all'apertura della lista
- L'utente può creare, rinominare, eliminare e attivare viste dalla modale
- Limite massimo ragionevole (es. 10 viste per lista per utente) per evitare proliferazione

**Impatto strutturale**
- Schema DB: modifica a `lista_preferenza_utente` — aggiungere colonne `nome`, `is_attiva`; rimuovere il `UNIQUE (auth_user_id, lista_id)` e sostituirlo con `UNIQUE (auth_user_id, lista_id, nome)` + UNIQUE INDEX su `is_attiva=TRUE` per coppia `(auth_user_id, lista_id)`
- Endpoint: `GET .../preferenze` (lista), `POST .../preferenze` (crea), `PUT .../preferenze/{id}` (aggiorna), `DELETE .../preferenze/{id}`
- Frontend: selector viste nella toolbar

**Nota**: questa è la modifica più invasiva tra quelle differite perché richiede una migration sulla tabella `lista_preferenza_utente` già popolata. Va pianificata attentamente o gestita con una migration che aggiunge le nuove colonne mantenendo i dati esistenti come vista `nome='Default'` con `is_attiva=TRUE`.

---

## DEF-4 — Condivisione viste tra utenti

**Descrizione**
Un utente (es. un team lead) crea una vista personalizzata per la sua lista e vuole condividerla con i colleghi del suo reparto, che possono usarla come punto di partenza.

**Comportamento atteso**
- Una vista può essere marcata come "pubblica nel reparto" (`visibile_reparto BOOLEAN`)
- Ogni utente può "adottare" una vista condivisa — crea una copia personale modificabile
- Le modifiche alla copia personale non impattano l'originale condivisa
- Solo l'autore (o un admin) può modificare o eliminare la vista condivisa originale

**Dipendenze**
- DEF-3 (viste nominate) è prerequisito — senza viste multiple non ha senso condividerle

**Impatto**
- DB: aggiungere `autore_auth_user_id`, `visibile_reparto`, `unita_organizzativa_id` a `lista_preferenza_utente`
- Backend: logica di visibilità e copia
- Frontend: sezione "Viste condivise" nella modale con possibilità di adottare

---

## DEF-5 — Admin UI per gestione preset e catalogo

> **Status 2026-05-07**: assorbito dal **Blocco F** del piano principale (§11.F del [WIP](sviluppo-personalizzazioni-liste.md)). Decisioni prese:
>
> - Split visibilita': tabelle tecniche (`lista_definizione`, `lista_colonna`) → `amm-software` SUPER_ADMIN; tabelle operative (`lista_preset`, `lista_preset_colonna`, `lista_colonna_permesso`) → `config` con azioni di processo `ui_preset_manage` / `ui_permesso_manage` (assegnabili a tenant admin).
> - Pattern UI: pagina condivisa con TabView lazy + tab condizionali ai permessi, master-detail su "Lista corrente" come header.
> - Fase 1 minimal: solo i 2 CRUD operativi. Le 2 tabelle tecniche restano gestite via seed CSV finche' non emerge esigenza concreta.
>
> Il piano dettagliato vive nel WIP principale. Questo paragrafo resta come storico — sara' rimosso quando il Blocco F atterra.

**Descrizione (storico)**
Oggi il catalogo (`lista_colonna`) e i preset (`lista_preset`, `lista_preset_colonna`) si gestiscono solo tramite seed CSV/Liquibase. In produzione, un amministratore di sistema deve poter creare nuovi preset di ruolo, modificare l'ordine e la visibilità di default delle colonne, senza richiedere un deploy.

**Comportamento atteso**
- Schermate admin (solo per `SUPER_ADMIN`):
  - Lista delle `lista_definizione` — con stato, view SQL associata, numero colonne
  - Dettaglio `lista_definizione` — gestione colonne catalogo (ordine, gruppo, tipo, larghezza, flag)
  - Gestione preset — crea/modifica/elimina preset per sistema/profilo/emittente
  - Gestione permessi colonne — assegna livelli di accesso per profilo
- Il catalogo (`lista_colonna`) resta modificabile solo da admin — non è personalizzazione utente

**Impatto**
- Backend: CRUD endpoint su `lista_definizione`, `lista_colonna`, `lista_preset`, `lista_preset_colonna`, `lista_colonna_permesso` — tutti protetti da verifica `SUPER_ADMIN`
- Frontend: nuova sezione in area amministrazione
- DB: nessuna modifica strutturale

---

## DEF-6 — Layout mobile e responsive

**Descrizione**
Il componente `<ListaConfigurabile>` è pensato per desktop. Su mobile, una tabella con 8+ colonne è inutilizzabile. Serve una modalità di visualizzazione alternativa (card list, accordion) che si attivi automaticamente su viewport piccolo.

**Comportamento atteso**
- Sotto una certa larghezza viewport (configurabile in `constants.js`), la lista passa a layout card
- Ogni card mostra le colonne marcate come `tipo_colonna = 'identificatore'` + le prime N colonne visibili
- Le azioni (kebab menu) sono sempre presenti
- La personalizzazione colonne su mobile è semplificata (solo toggle visibilità, no drag&drop)

**Impatto**
- Frontend: nuova modalità di rendering in `<ListaConfigurabile>` + CSS responsive
- DB/Backend: nessuno — la configurazione rimane la stessa, cambia solo la presentazione

---

## DEF-7 — Colonne calcolate lato client

**Descrizione**
Alcune informazioni utili non esistono come colonne nella view SQL ma si derivano da quelle presenti (es. "giorni alla scadenza" = `CURRENT_DATE - data_scadenza`). La struttura prevede `campo_sorgente = NULL` per colonne di tipo `azione` — lo stesso meccanismo potrebbe estendersi a colonne calcolate.

**Comportamento atteso**
- Un nuovo `tipo_colonna = 'calcolata'` con `campo_sorgente = NULL` e un campo aggiuntivo `formula_client VARCHAR` che specifica la chiave della funzione di calcolo registrata nel composable Vue
- Il catalogo definisce "esiste questa colonna calcolata con questa chiave"
- Il composable Vue mappa la chiave alla funzione JavaScript corrispondente
- Le colonne calcolate non sono esportabili (stesso comportamento di `azione`)

**Nota**: questo richiede un contratto frontend stabile per le formule. Da definire prima di implementare per evitare proliferazione di convenzioni ad hoc.

**Impatto**
- DB: aggiungere `tipo_colonna = 'calcolata'` al CHECK constraint, aggiungere colonna `formula_client VARCHAR(80)` a `lista_colonna`
- Frontend: registro formule nel composable `useListaConfig`
- Backend: nessuno

---

## DEF-8 — Seed catalogo per tutte le liste esistenti

**Descrizione**
Il Blocco E del piano principale copre solo la prima lista (`anagrafiche.clienti`). Tutte le altre liste esistenti nel frontend (fornitori, articoli, commesse, fatture, ordini, ecc.) devono ricevere il loro catalogo e preset di sistema.

**Approccio**
Questo non è un singolo sviluppo ma un'attività incrementale: ogni volta che una lista viene "migrata" da DataTable statico a `<ListaConfigurabile>`, si aggiungono i corrispondenti seed dati in `80_data/`.

Ordine suggerito per impatto e frequenza d'uso:
1. `anagrafiche.fornitori`
2. `catalogo.articoli`
3. `vendite.fatture`
4. `vendite.ordini`
5. `acquisti.ordini`
6. `commesse` (se presente)
7. Liste secondarie (scadenze, pagamenti, movimenti magazzino)

Per ogni lista: file CSV in `80_data/sql/ui/` + YAML changelog + migrazione componente Vue.

---

## Priorità suggerita per ripresa

| Priorità | Item | Dipende da |
|----------|------|------------|
| Alta | DEF-1 (export) | Blocco E completato |
| Alta | DEF-8 (seed altre liste) | Blocco E completato — lavoro incrementale |
| Media | DEF-2 (notifica preset aggiornato) | Blocco D completato |
| Media | DEF-5 (admin UI preset/catalogo) | Blocchi C+D completati |
| Bassa | DEF-3 (viste nominate) | Nessuna — ma richiede migration |
| Bassa | DEF-6 (mobile) | Blocco D completato |
| Bassa | DEF-4 (condivisione viste) | DEF-3 |
| Futura | DEF-7 (colonne calcolate) | Blocco D + accordo formula contract |
