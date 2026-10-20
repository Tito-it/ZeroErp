# API Fondi fattura — l'elenco dei casi che chiedono una persona

## Scopo

Espone l'elenco paginato dei fondi fattura su cui il giro automatico **si è
fermato**, e la decisione resta a un operatore.

```text
GET /api/v1/vendite/fondi-fattura/da-decidere/
      ?motivo=&order_by=&order_dir=&page=&page_size=
GET /api/v1/vendite/fondi-fattura/da-decidere/export/
      ?formato=csv|xlsx&motivo=&order_by=&order_dir=
```

## Contesto

Il fondo fattura era *«un numero ricalcolato che muove denaro»*: calcolato come
un saldo e riscritto a ogni giro, ma con l'effetto di un atto — assegnato a una
fattura figlia, ne cambia l'importo. Il cantiere DB
(`brief-db-fondo-fattura-ricalcolo-e-governo`) ha separato le due cose: il fondo
è ora un **atto**, scritto una volta con l'importo congelato e mai aggiornato;
il ricalcolo resta ma è diventato una **lettura**.

Ne discende che l'automatismo crea **solo dentro l'inviluppo** (sorgente
DEFINITIVA, dentro la banda delle due soglie, ancora capiente, importo
corrispondente al documento). Fuori da lì non fa niente — e questo endpoint è il
posto dove quel «niente» diventa visibile.

⭐ **L'elenco PRESENTA, non sana.** Nessuna di queste righe ha un gemello
automatico che la corregge: sanarle vorrebbe dire muovere denaro senza che
nessuno l'abbia deciso. È la stessa regola per cui non esiste un `ANNULLATO`
automatico come effetto di un pagamento — *se non ci si fida di un automatismo a
creare un fondo, tanto meno a cancellarlo*.

## Input

| Parametro | Tipo | Default | Note |
| --- | --- | --- | --- |
| `motivo` | enum | tutti | Whitelist **chiusa** dei quattro motivi (sotto). Fuori vocabolario → **400** `E_VENDITE_VALIDATION` |
| `order_by` | enum | `data` | `data`, `motivo`, `anno`, `numero`, `totale_a_pagare`, `importo_proposto`, `capienza_attuale`, `stato_atto`. Fuori whitelist → **400**. ⚠️ `stato_atto` (aggiunto il 2026-08-22) è valorizzato sul solo ramo `NON_PIU_CAPIENTE`: ordinarlo **separa i casi con un atto vivo da quelli senza**, e i vuoti vanno in coda su `desc` (`sql_order_direction`, che emette sempre i `NULLS` espliciti) |
| `order_dir` | `asc`/`desc` | `desc` | Le fatture più recenti prima. Altro valore → **400** |
| `page` | int | 1 | |
| `page_size` | int | 25 | max 200 |

### I quattro motivi

| Motivo | Cosa dice |
| --- | --- |
| `PROPOSTA_SENZA_ATTO` | la fattura **merita** un fondo e non ce l'ha. `importo_proposto` porta la proposta |
| `IMPORTO_NON_CORRISPONDENTE` | il residuo esiste ma **non assomiglia al documento** (segno diverso dal totale, o più grande in valore assoluto) e l'automatismo tace. Dove il giro sta zitto, l'elenco parla |
| `NON_PIU_CAPIENTE` | l'atto **esiste** ma la sorgente non lo regge più, e il giro lo scarta a ogni corsa. È l'unico ramo con le colonne dell'atto valorizzate |
| `UTILITY_NON_ATTRIBUIBILE` | è nella banda ma **senza `utility_id`**, quindi irraggiungibile da qualunque giro: il filtro è `=` e NULL non è uguale a niente |

⚠️ `CONFIGURAZIONE_INCOMPLETA`, quinto motivo previsto dal piano, **non esiste**:
dopo il CHECK `chk_emittenti_fiscali_utilities_soglie_coppia` una configurazione
a metà non è più salvabile, e *una riga di elenco che non può accadere insegna
una cosa falsa*.

## Output

Envelope paginato standard (`count`, `page`, `page_size`, `total_pages`,
`results`).

⚠️ **Le colonne non sono tutte sempre valorizzate, ed è la forma del dato, non
un buco**: quelle dell'atto (`fondo_source_id`, `origine`, `stato_atto`,
`importo_atto`, `atto_motivo`, `atto_data`) esistono **solo** su
`NON_PIU_CAPIENTE` — negli altri tre l'atto non c'è ancora, ed è il motivo per
cui la riga è nell'elenco. Simmetricamente `importo_proposto` esiste solo dove
una proposta c'è.

Le **etichette** dei motivi le mette il frontend con `labelOrCode` (fail-visible):
il backend spedisce il codice.

### Export (`/export/`)

Stessa lista, stessi filtri, stesso ordinamento — in CSV o XLSX. **Colonne,
ordine e visibilità vengono dalla configurazione dell'operatore** sul catalogo
`vendite.fondi_fattura_da_decidere` (BB `ListaExportService`), non da un elenco
scritto nella view: un file con colonne diverse da quelle a video sarebbe un
secondo elenco da riconciliare a mano.

| Cosa | Regola |
| --- | --- |
| `formato` | `csv` (default) o `xlsx`. ⚠️ **`formato`, non `format`**: quest'ultimo è magic per la content-negotiation DRF e intercetterebbe la chiamata prima della view |
| Righe | tetto `EXPORT_MAX_ROWS` (10.000). Il servizio chiede `max_rows + 1` per far **scattare** il guard invece di troncare in silenzio |
| Paginazione | **saltata**, non allargata: `max_rows` non passa dal validatore di pagina (tetto 200), che resta un guard d'interfaccia per tutte le liste del progetto |

## Regole

- **Sola lettura.** Nessun ricalcolo del fondo in Python, nessuna scrittura su
  `fatture_fondi_fattura_source` da un repository. Il BE **chiama e legge**: è
  DB-first, ed è anche l'unico modo di tenere la promessa dell'atto — un secondo
  posto che scrive un importo la annulla.
- **L'elenco non riscrive nessuna regola.** La proposta la dà
  `fn_fondo_fattura_proponibile` e la capienza `fn_check_fondo_fattura_capiente`
  — le **stesse** funzioni che usano generazione e applicazione — così l'elenco
  non può raccontare una cosa diversa da quello che il giro notturno fa.
- **Nessuna capability per riga**: le liste non chiamano
  `fn_available_actions_*` riga per riga. Il gate delle azioni lo farà il FE sui
  codici che la vista porta già in riga.
- **Vocabolario chiuso per costruzione**: i motivi sono letterali nei rami della
  UNION, nessun dato li produce. ⚠️ In PostgreSQL **non esiste un CHECK su una
  vista**: il presidio è il pgTAP che asserisce l'insieme dei motivi, più il test
  `test_motivi_allineati_alla_vista` che dichiara la copia lato BE.

## `DELETE /api/v1/vendite/fondi-fattura/<fondo_source_id>/`

Cancella un atto di fondo che **non è ancora diventato un fatto** — oppure
rifiuta, dicendo perché. BE-4, su `vendite.fn_cancella_fondo_fattura` (D-21).

⭐ **Il metodo dice il verbo.** `api.md` §Grammatica URL vieta di scriverlo nel
path: la rotta è la risorsa e la cancellazione è il `DELETE`. Non esiste un
`POST .../cancella/`.

| | |
| --- | --- |
| Permesso | `post_permission = governa_fondo_fattura` (azione di processo `pericolosa`, D-23). ⚠️ **Seminata non vuol dire concessa**: finché non è assegnata a un profilo resta chiusa per tutti tranne il super admin |
| Header | **`Idempotency-Key` obbligatoria**: il gesto è irreversibile, e un doppio invio riceverebbe altrimenti un errore per un'operazione riuscita |
| Corpo | vuoto — quello che serve è nel path |
| Risposta | `{status, fondo_source_id, deleted_righe, deleted_fondi, deleted_source}` |

### ⛔ A quale popolazione serve, e a quale NO

Serve al fondo **`AUTOMATICA` non più capiente** del ramo `NON_PIU_CAPIENTE`
dell'elenco «da decidere»: l'atto che il giro non riesce più ad applicare e che
nessuna sistemazione trattiene.

**Non** serve al riporto sbagliato. Quello si disfa annullando la sistemazione
che lo ha creato — `POST /api/v1/pagamenti/sistemazioni/{id}/annulla/`, che
esiste già — e se qualcuno prova a passare di qui il database rifiuta con
`E_FONDO_TRATTENUTO_DA_SISTEMAZIONE`, che **nomina quell'alternativa** invece di
dire «non si può».

### I rifiuti, e perché non c'è un elenco locale di codici

Il criterio sta in `vendite.fn_check_fondo_cancellabile`, che la madre legge
**una volta sola**:

| Motivo del predicato | Codice | HTTP |
| --- | --- | --- |
| `ATTO_NON_TROVATO` | `E_FONDO_NON_TROVATO` | **404** |
| `ATTO_ESEGUITO` · `RIGA_REGISTRATA` · `CONTABILE_CHIUSA` | `E_FONDO_NON_CANCELLABILE` (la `cause` distingue i tre) | **409** |
| `FIGLIA_CONGELATA` | `E_FONDO_FIGLIA_CONGELATA` | **409** |
| `SISTEMAZIONE_ATTIVA` | `E_FONDO_TRATTENUTO_DA_SISTEMAZIONE` | **409** |

⛔ **«Non esiste» e «non è tuo» danno la stessa risposta**, di proposito: la
tabella ha la row security, e distinguerle direbbe a chi è fuori perimetro che
quel fondo c'è.

⭐ **Il service usa `translate_db_errors` e non un elenco locale di codici
ammessi**, ed è una scelta: quel predicato ha **sei** motivi dove il piano ne
prevedeva quattro — due sono nati scrivendo il changeSet. Una copia del catalogo
in Python si sarebbe disallineata in silenzio proprio su quei due. Così invece un
codice nuovo arriva all'operatore com'è, col suo messaggio, la sua `soluzione` e
il suo **bersaglio** (la fattura — sorgente o figlia secondo il motivo).

### 🔴 Guard di canale

Il repository rifiuta la chiamata da un ruolo `BYPASSRLS`. È lo stesso presidio
dell'elenco, ma **pesa di più**: la madre è `SECURITY INVOKER` e si appoggia alla
row security accesa da D-20. Su un canale di sistema il perimetro emittente
sparisce, e qui non si *leggerebbe* l'atto di un altro emittente — lo si
**cancellerebbe**. ⚠️ Un conteggio non lo troverebbe: l'operazione riuscirebbe.

## Dipendenze DB

| Oggetto | Ruolo |
| --- | --- |
| `vendite.vw_fondi_fattura_da_decidere` | la vista letta (D-10) |
| `vendite.fn_fondo_fattura_proponibile` | la proposta, condivisa col giro |
| `vendite.fn_check_fondo_fattura_capiente` | la capienza, condivisa col giro |
| `vendite.fn_saldo_sorgente_fondo` | il residuo della sorgente |

🔴 **La vista è `security_invoker=on`**: il perimetro emittente lo applica la RLS
di `vendite.fatture` con l'identità della richiesta. Ne discendono due obblighi:

1. va letta con la **connessione dell'utente** — mai da un canale di sistema
   (`system_process_context`, ruolo `BYPASSRLS`), o l'elenco mostrerebbe i fondi
   di tutti gli emittenti;
2. il filtro applicativo (`auth_user_id` → scope SR nel repository) resta come
   **defense-in-depth** e si somma, com'è la convenzione del progetto.

⚠️ Il ramo `NON_PIU_CAPIENTE` parte da `fatture_fondi_fattura_source`, che **non
ha RLS**: è protetto dal JOIN INNER con `vendite.fatture`, non da un filtro
proprio.

> 🔴 **Vero oggi, ma è una scelta RIBALTATA — 2026-08-29 (G-2, decisione di
> Tid).** La riga descrive lo stato di fatto, non più il progetto: la row
> security su `fatture_fondi_fattura_source` **si accende** (passo **D-20**, le
> due policy `ef_whitelist` + `ba_ownership`), perché la premessa che la
> escludeva è scaduta. Quando fu scritta, l'unico accesso era **la lista**, e la
> lista ha davvero il `JOIN` davanti; oggi la tabella ha anche uno **scrittore in
> un altro schema** (`pagamenti.fn_conferma_sistemazione`) e, col gesto di D-21,
> avrà un accesso **per id** — e un id non ha nessun `JOIN` davanti.
> ⭐ Qui la policy è più semplice che sugli altri satelliti: `emittente_soggetto_ruolo_id`
> e `billing_account_id` sono **in colonna e NOT NULL**, quindi niente delega a
> `fn_scope_*_via_fattura`. Dettaglio in
> [brief-db-fondo-fattura-ricalcolo-e-governo.md](../../../dev/work-done/brief-db-fondo-fattura-ricalcolo-e-governo.md)
> §9.9. ✅ **APPLICATA il 2026-08-31** (changeSet `20260831-62`): verificato sul
> catalogo vivo — `relrowsecurity = true` e le **due** policy sulla tabella.
> ⛔ La frase qui sopra («non ha RLS») **non è più vera**: il ramo
> `NON_PIU_CAPIENTE` ha ora il suo filtro proprio, oltre al `JOIN` della vista.

## Note di migrazione

**Fatto** (BE-1…BE-3, BE-5 del piano §8.3):

| | Cosa |
| --- | --- |
| BE-2 | atomicità del giro fondi. ⚠️ **Perimetro misurato dal percorso reale**: sul giro di pipeline il parziale **non era possibile** — `run_pipeline` avvolge già ogni step in `transaction.atomic()`; l'esposizione valeva solo per la facciata single-step. Chiuso prima con uno statement set-based, poi **superato da R-3**: oggi è una chiamata alla madre DB per lotto |
| BE-3 | questo endpoint |
| BE-5 / R-1 | `error_policies_generated.py` rigenerato: i **cinque** codici `E_FONDO_*` hanno la loro classe, più il messaggio di ripiego in `error_messages_fallback.py` |
| R-2 | `chk_emittenti_fiscali_utilities_soglie_coppia` → `E_FONDO_SOGLIE_INCOMPLETE` via `map_integrity_error`. ⚠️ Difetto collaterale sanato: **ogni** violazione di quella tabella passava da `create_with_dedup` e usciva come «esiste già un record per questa coppia» — un messaggio non povero ma **falso** — e sul percorso di UPDATE non c'era traduzione affatto (500) |

**Non fatto, e perché** — entrambi aspettano il DB:

| | Cosa manca |
| --- | --- |
| ~~**BE-4** (atto manuale: `POST fondi-fattura/`, `POST fondi-fattura/<id>/annulla/`)~~ | ~~la **Fase D** non è applicata: `fn_crea_fondo_fattura_manuale` e `fn_annulla_fondo_fattura` non esistono, e l'azione di processo `governa_fondo_fattura` non è a catalogo. E comunque la porta va aperta **dopo** che `pagamenti` ha un processo rimborsi da cui chiamarla~~ 🔴 **SUPERATA il 2026-08-22, riscritta il 2026-08-31 — sbagliava sia i verbi sia l'attesa.** Vedi la riga sotto |
| ~~**BE-4** — ri-perimetrato~~ | ✅ **FATTO il 2026-08-31**, dopo l'apply di D-21/D-23. Documentato nella sezione «Cancellare un atto» qui sopra |
| ~~**Frontend** (le azioni di riga)~~ | ✅ **FATTE il 2026-08-31**: kebab `RowActionsMenu` sulla lista, voce «Cancella l'atto» gated su `governa_fondo_fattura`, conferma rossa. ⛔ Si disegna **solo dove c'è un atto** (`fondo_source_id != null`): un menu a zero voci promette un gesto che non c'è. ⚠️ Ha richiesto **anche** il seed della colonna `azioni` a catalogo (`tipo_colonna = 'azione'`): senza, lo slot `#actions` non rende niente e **non dà errore** |
| ~~**Frontend** (la lista)~~ | ✅ **FATTO il 2026-08-22**: **Vendite → Tool fatturazione**, primo tab (`ToolFatturazioneView.vue` + `FondiFatturaDaDecidereTab.vue`, store `fondiFatturaDaDecidere.js`). Lista configurabile standard: paginazione e ordinamento server-side, colonne personalizzabili, export CSV/XLSX, click di riga → `FatturaDrawer`. ⭐ Fino a quel giorno la lista **esisteva e non era raggiungibile**: vista, catalogo ed endpoint c'erano dal 15-08 e nessun `.vue` la montava — è la differenza fra i 47 codici a catalogo e le 46 liste nel registro `_LISTE` |
| ~~**R-3** (madre DB per lotto)~~ | ✅ **FATTA il 2026-08-15**, DB e BE. I due giri passano da `fn_genera_fondi_fattura_lotto` / `fn_applica_fondi_lotto` (firma col **codice interno** del tipo fondo): **una `SELECT` per task**, lookup e scope dentro il database. 🔴 Con lo spostamento i tre errori del giro sono passati da `ServiceError` Python a `DatabaseError`, e `_fail_task_run_safely` li appiattiva su `E_TASK`: chiuso leggendo il codice strutturato con `db_error_code` — vale per ogni task che delega a una funzione DB. Dettaglio: brief fondo fattura §8.3-bis (DB) e §8.3-ter (BE) |
