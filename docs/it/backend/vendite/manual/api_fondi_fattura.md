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
| `page_size` | int | 50 | max 200 |

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
| **BE-4** (atto manuale: `POST fondi-fattura/`, `POST fondi-fattura/<id>/annulla/`) | la **Fase D** non è applicata: `fn_crea_fondo_fattura_manuale` e `fn_annulla_fondo_fattura` non esistono, e l'azione di processo `governa_fondo_fattura` non è a catalogo. E comunque la porta va aperta **dopo** che `pagamenti` ha un processo rimborsi da cui chiamarla |
| ~~**Frontend** (la lista)~~ | ✅ **FATTO il 2026-08-22**: **Vendite → Tool fatturazione**, primo tab (`ToolFatturazioneView.vue` + `FondiFatturaDaDecidereTab.vue`, store `fondiFatturaDaDecidere.js`). Lista configurabile standard: paginazione e ordinamento server-side, colonne personalizzabili, export CSV/XLSX, click di riga → `FatturaDrawer`. ⭐ Fino a quel giorno la lista **esisteva e non era raggiungibile**: vista, catalogo ed endpoint c'erano dal 15-08 e nessun `.vue` la montava — è la differenza fra i 47 codici a catalogo e le 46 liste nel registro `_LISTE` |
| ~~**R-3** (madre DB per lotto)~~ | ✅ **FATTA il 2026-08-15**, DB e BE. I due giri passano da `fn_genera_fondi_fattura_lotto` / `fn_applica_fondi_lotto` (firma col **codice interno** del tipo fondo): **una `SELECT` per task**, lookup e scope dentro il database. 🔴 Con lo spostamento i tre errori del giro sono passati da `ServiceError` Python a `DatabaseError`, e `_fail_task_run_safely` li appiattiva su `E_TASK`: chiuso leggendo il codice strutturato con `db_error_code` — vale per ogni task che delega a una funzione DB. Dettaglio: brief fondo fattura §8.3-bis (DB) e §8.3-ter (BE) |
