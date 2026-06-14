# Brief DB — pratica terminale: blocco modifiche e creazione flussi

**Area:** `pratiche` · **Tipo:** guard di integrità (difesa lato DB)
**Branch destinazione:** `dev/db-tid`
**Richiesto da:** backend agent (per conto di Tid) · **Data:** 2026-06-14

> Nota: questo brief descrive **cosa** deve garantire il DB, non **come**.
> La scelta implementativa (estendere i guard flussi esistenti o aggiungerne di
> nuovi, fasi, nomi oggetti, SQL) è competenza del team DB.

---

## 1. Contesto

Decisione di modello: una pratica in **stato terminale** (`CHIUSA`, `ANNULLATA`)
è conclusa e non deve essere più modificabile. La UI è già stata protetta
(scheda in sola lettura, percorso non cliccabile sugli step "da creare", drawer
flusso senza azioni). Serve la **difesa lato DB** perché una chiamata API diretta
o un batch non passi dalla protezione FE.

Stati terminali: nessuna transizione in uscita (verificato in
`config.transizioni_stati_pratiche`).

## 2. Cosa deve garantire il DB

Quando la **pratica padre** è in stato `CHIUSA` o `ANNULLATA`:

1. **Niente nuovi flussi**: deve essere rifiutata la creazione di un flusso
   (`pratiche.flussi`) agganciato a quella pratica.
2. **Niente transizioni di stato dei flussi**: deve essere rifiutato qualsiasi
   cambio di stato di un flusso esistente della pratica (es. avvio
   `DA_ESEGUIRE → IN_CORSO`, completamento `IN_CORSO → COMPLETATO`, ecc.).
3. **Niente modifica dei dati di flusso**: deve essere rifiutata la modifica dei
   campi di esecuzione del flusso (almeno `esito`, `note_esito`; valutare gli
   altri campi operativi).

In tutti i casi: errore **parlante** (messaggio in `config.messaggi_errore`,
codice dedicato es. `E_PRATICA_TERMINALE_*`), così che il backend possa
mapparlo a un messaggio utente chiaro come per gli altri guard.

## 3. Vincoli ed eccezioni da rispettare

- **Non rompere la transizione della pratica a terminale.** Se il passaggio di
  una pratica ad `ANNULLATA`/`CHIUSA` comporta una cascata sui flussi (es.
  chiusura/annullamento automatico dei flussi attivi), quella cascata "di
  sistema" deve restare permessa: il blocco riguarda le operazioni **successive**
  su una pratica già terminale, non l'atto stesso di renderla terminale.
- **Cascata flussi attivi all'annullamento (decisione di modello, da confermare).**
  Oggi annullare una pratica con flussi `DA_ESEGUIRE`/`IN_CORSO` li lascia attivi.
  Conseguenza concreta: quei flussi **continuano a comparire nella coda lavoro**
  (`fn_coda_lavoro_operatore` filtra solo per emittente, non per stato pratica) e
  un operatore potrebbe selezionarli ed eseguirli. Proposta: all'annullamento
  portare i flussi attivi a uno stato terminale coerente (annullato/chiuso), così
  spariscono dalla coda e l'incoerenza si chiude alla radice. Va concordato prima
  di implementare; in alternativa minima, `fn_coda_lavoro_operatore` deve
  **escludere i flussi di pratiche terminali**.
- Il guard di chiusura esistente (i flussi obbligatori devono essere completati
  prima di `CHIUSA`) resta valido e non va toccato.

## 4. Criteri di accettazione (comportamento atteso, test pgTAP)

1. Pratica `ANNULLATA`: tentativo di creare un nuovo flusso → **rifiutato** con errore parlante.
2. Pratica `ANNULLATA`: tentativo di avviare/completare un flusso esistente → **rifiutato**.
3. Pratica `ANNULLATA`: tentativo di modificare `esito`/`note_esito` di un flusso → **rifiutato**.
4. Stessi tre casi con pratica `CHIUSA` → **rifiutati**.
5. Regressione: su pratica `APERTA` creazione/avvio/completamento flussi → **consentiti** (comportamento attuale invariato).
6. Regressione: l'annullamento/chiusura di una pratica con eventuale cascata sui propri flussi → **consentito** (non bloccato dal nuovo guard).
7. Dopo l'annullamento di una pratica, i suoi flussi **non compaiono più nella coda lavoro** (`fn_coda_lavoro_operatore`) — sia che la cascata li chiuda, sia che la coda li escluda per stato pratica terminale.

## 5. Downstream lato BE (dopo consegna)

Nessuna modifica funzionale obbligatoria: il backend già intercetta gli errori DB
parlanti e li rimappa. Andrà aggiunto il mapping del/i nuovo/i codice/i errore in
`pratiche_service` (sulle stesse rotte di creazione/cambio stato flusso) per
restituire un messaggio utente coerente. FE già a posto.

## 6. Esito consegna (2026-06-14) — CHIUSO

DB consegnato (2 migration):

- `20260614-01` — `trgfn_flussi_guard_pratica_terminale`: blocca creazione/modifica
  flussi su pratica terminale. Codici `PRATICHE_TERMINALE_NUOVO_FLUSSO_BLOCCATO`
  (490) e `PRATICHE_TERMINALE_FLUSSO_NON_MODIFICABILE` (491).
- `20260614-02` — `fn_coda_lavoro_operatore`: esclude i flussi di pratiche
  terminali (definizione data-driven: stato senza transizioni in uscita). Scelta
  l'alternativa "coda esclude terminali" invece della cascata sui flussi
  all'annullamento → criterio di accettazione #7 soddisfatto.

BE: marker dei due codici in `_KNOWN_DB_ERROR_MARKERS` + wrapping
`avvia/completa/cambia_stato_flusso` (oltre a `crea_flusso`) con mapping parlante.
4 test aggiunti, suite pratiche verde.

FE: percorso + drawer flusso + scheda in sola lettura su pratica terminale; il
gap "coda lavoro" è chiuso a monte dall'esclusione DB.
