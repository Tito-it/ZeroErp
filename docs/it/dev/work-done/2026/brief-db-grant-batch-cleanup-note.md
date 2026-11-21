# Brief BE → DB — il rollback automatico di step fallisce nel worker: manca un GRANT

> 🟢 **CHIUSO — 2026-08-04.** Grant applicato dal team DB, **controprova del §6
> eseguita e verde**: la stessa chiamata che sollevava «permesso negato»
> (`fn_elimina_fattura_da_lotto` dentro `system_process_context`) ora completa —
> `{'updated_attivita': 0, 'deleted_fatture': 1, 'deleted_righe': 1,
> 'riemesse_attivita': 0}`, in transazione con rollback, nessun dato toccato.
> `has_table_privilege('zeroerp_batch_fatturazione','vendite.note','DELETE')` →
> `true`.
>
> **Le due precisazioni del DB, e cosa ne facciamo:**
>
> 1. **Concesso solo `DELETE`, non `INSERT`** — e hanno ragione loro: nessun
>    percorso batch crea note. Verificato anche dal lato applicativo, che è
>    l'altra faccia della loro misura: i quattro service che girano su canale
>    batch (`fatturazione_giro_handler`, `fatturazione_numera_handler`,
>    `fatturazione_driver_service`, `stampa_coda_drainer_service`) non nominano
>    mai `NOTE_REPO_*` né `PartitionedNoteService`. Su un ruolo `BYPASSRLS` un
>    privilegio in più «già che ci siamo» è un costo, non una comodità.
> 2. **La causa non era quella che avevamo scritto.** Il §4.2 diceva «il
>    perimetro è rimasto indietro rispetto a una funzione che ha iniziato a
>    scrivere una tabella nuova». È peggio e più interessante: il perimetro una
>    riga per le note **ce l'aveva**, ma puntava a `vendite.note_fatture` — la
>    tabella del modello precedente all'unificazione, oggi a zero righe e senza
>    nessuno che la scriva. Un `GRANT` su una tabella morta non dà errore:
>    concede, e basta. **Quindi il presidio va progettato per vedere entrambe le
>    facce** — tabella scritta senza grant *e* grant su tabella che nessuno
>    scrive più — perché la seconda è quella che maschera la prima.
>
> **Una nona tabella che il nostro elenco non aveva**: `fatture_arrotondamenti_scope`.
> Il DB l'ha ricavata dal corpo vivo della funzione invece che dalla lista — ed
> è il metodo giusto, lo stesso che il §4.2 chiede di automatizzare. Il cleanup
> la usa in sola `UPDATE`, privilegio che il worker ha: nessun secondo buco.
>
> **Sul presidio (§4.2) siamo d'accordo con la loro divisione in due**, compresi
> i limiti che dichiarano in anticipo (SQL dinamico invisibile, raggiungibilità
> in batch da dichiarare a mano): un presidio con i limiti scritti è utile, uno
> che li nasconde dà falsa sicurezza. Resta slice loro, serve a tutti i ruoli
> batch e non solo alla fatturazione.
>
> ---

**Chi scrive:** BE (`dev/backend-tid`), 2026-08-04.
**A chi:** team DB (`dev/db-tid`).
**Cos'è:** `vendite.fn_cleanup_fatture_by_ids` cancella anche le note della fattura,
ma il ruolo dei **worker** non ha `DELETE` su `vendite.note`. Il percorso che ci
passa esiste ed è configurato: il **rollback automatico** della pipeline massiva.
**Come è emerso:** provando il binding della `fn_elimina_fattura_da_lotto` dal
canale di sistema, dopo la vostra slice 6-B. Non è un difetto introdotto da voi:
è un difetto **latente** che quella prova ha fatto affiorare.
**Correlati:** [fn_cleanup_fatture_by_ids](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids) ·
[piano-db-ritorno-lotto-a-draft](piano-db-ritorno-lotto-a-draft.md)

---

## 1. L'errore, testuale

```text
ProgrammingError: permesso negato per la tabella note
CONTEXT: istruzione SQL "DELETE FROM vendite.note
   WHERE target_tipo = 'FATTURA' AND target_riga_id = ANY(v_righe_ids)"
funzione PL/pgSQL vendite.fn_cleanup_fatture_by_ids
```

Riprodotto chiamando `fn_elimina_fattura_da_lotto` dentro
`system_process_context(alias='system_fatturazione')`, cioè esattamente il
contesto in cui girano i worker.

## 2. La misura

`has_table_privilege` sui due ruoli, per le tabelle che il cleanup tocca:

| Tabella | `zeroerp_app` (web) | `zeroerp_batch_fatturazione` (worker) |
| --- | --- | --- |
| `vendite.fatture` | ✅ | ✅ |
| `vendite.fatture_righe` | ✅ | ✅ |
| `vendite.fatture_log` | ✅ | ✅ |
| `vendite.fatture_riepiloghi_iva` | ✅ | ✅ |
| `vendite.fatture_scadenze` | ✅ | ✅ |
| `vendite.fatturazione_lotti_fatture` | ✅ | ✅ |
| `vendite.attivita_fatturabili` | ✅ | ✅ |
| `vendite.commesse_attivita` (UPDATE) | ✅ | ✅ |
| **`vendite.note` (DELETE)** | ✅ | 🔴 **NO** |
| **`vendite.note` (INSERT)** | ✅ | 🔴 **NO** |

Una tabella su nove. È il tipo di buco che non si vede finché non lo si attraversa.

⚠️ **Nota di metodo, per non ripetere il mio errore.**
`information_schema.table_privileges` mostra **solo i privilegi visibili al ruolo
della sessione**: interrogata dal web dice che l'unico grantee è `zeroerp_app`,
interrogata dal batch dice l'opposto. Sembrano due risposte in conflitto e sono
entrambe parziali. La misura sopra usa `has_table_privilege('<ruolo>', ...)`, che
risponde per qualunque ruolo.

## 3. Perché non è teorico: il percorso è configurato

`vendite.fatturazione_pipeline` id **3** («Pipeline massiva (EMESSA)», `MASSIVO`)
ha il rollback dichiarato a dato:

```json
[{"fase": "Reset lotto massivo a bozza", "task": "reset_lotto_draft",
  "params": {"implementation_key": "default"}}]
```

La catena completa:

```text
worker coda lavori  (ruolo zeroerp_batch_fatturazione)
  └─ fatturazione_giro_handler → run_lotto_pipeline
      └─ auto_step_rollback → execute_step(rollback=True)
          └─ task `reset_lotto_draft` → vendite.fn_annulla_lotto_da_draft
              └─ vendite.fn_cleanup_fatture_by_ids
                  └─ DELETE FROM vendite.note   🔴 permesso negato
```

E nessuna delle quattro funzioni della catena è `SECURITY DEFINER` (verificato su
`pg_proc.prosecdef`): il `DELETE` è valutato con i privilegi del **chiamante**,
cioè del ruolo del worker.

Dall'interfaccia lo stesso rollback funziona, perché lì il ruolo è `zeroerp_app`.
È la ragione per cui il difetto non si è mai visto: **il web copre il batch**.

## 4. Cosa chiediamo

1. **Il grant mancante**: `DELETE` (e `INSERT`, che manca insieme) su
   `vendite.note` al ruolo dei worker, allineandolo alle altre otto tabelle del
   cleanup.
2. **Una verifica di simmetria più larga di questo caso.** Il buco è nato perché
   i grant al ruolo batch sono stati concessi tabella per tabella, mentre le
   funzioni che il batch esegue evolvono: `fn_cleanup_fatture_by_ids` ha
   cominciato a cancellare le note **dopo** che i grant erano stati scritti.
   Un presidio — anche solo una vista `dbops` che confronti le tabelle scritte
   dalle funzioni eseguite in batch con i privilegi effettivi del ruolo — vale
   più del singolo grant. È lo stesso genere di debito che avete già annotato per
   le funzioni fantasma.

## 5. Cosa NON chiediamo

* **Nessun `SECURITY DEFINER` sul cleanup**: alzerebbe i privilegi di una
  funzione che cancella documenti per farla passare, invece di dare al chiamante
  i permessi che gli servono. È la scorciatoia sbagliata.
* **Nessuna modifica al BE**: il percorso applicativo è corretto: chiede al DB di
  fare una cosa che ha senso, ed è il DB a rifiutarla per una ragione che non
  riguarda il dominio.

## 6. Definizione di «fatto»

* [x] `has_table_privilege('zeroerp_batch_fatturazione', 'vendite.note', 'DELETE')` → `true`;
* [x] la chiamata che sollevava «permesso negato» completa dal canale
      `system_fatturazione` — provata in transazione con rollback il 2026-08-04;
* [x] presidio del §4.2 **deciso**: diviso in due dal team DB — il confronto fra
      le due liste gemelle del perimetro subito, la derivazione delle tabelle
      scritte dai corpi delle funzioni come slice a sé, valida per tutti i ruoli
      batch.
