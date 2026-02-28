# Roadmap Fatturazione — Gap enterprise da colmare

> Promemoria di sviluppo derivato dalla review architetturale del 28/02/2026.
> Priorità ordinate per impatto sull'adozione in aziende medio-alte.

---

## 1. Ciclo di vita post-emissione

**Problema:** il flusso copre solo il forward (sorgente → fattura → SDI). Il 5-15% delle fatture ha un ciclo post-emissione che oggi non è documentato né strutturato.

**Da implementare:**

- Note di credito totali e parziali con legame alla fattura originale
- Rettifiche (fattura sostitutiva) con tracciamento della catena documentale
- Storno lotto: annullamento massivo pre-SDI vs gestione post-SDI (nota di credito obbligatoria)
- Stato documento esteso: aggiungere `STORNATA`, `RETTIFICATA`, `NOTA_CREDITO_EMESSA`
- Vincoli: una fattura INVIATA/accettata SDI non può essere stornata, solo creditata

**Impatto ER:**

- Relazione `fatture.fattura_riferimento_id` → fattura originale
- Tipo documento fiscale: `FATTURA`, `NOTA_CREDITO`, `NOTA_DEBITO`
- Possibile tabella `fatture_riferimenti` se una NC copre più fatture

---

## 2. Integrazione contabile

**Problema:** il flusso si ferma a INVIATA/SDI. La fattura deve generare scritture contabili, aggiornare il partitario e alimentare lo scadenzario.

**Da implementare:**

- Generazione automatica scritture contabili da fattura definitiva (o da evento DEFINITIVA nella pipeline)
- Mapping conti: articolo/servizio → conto ricavo, aliquota IVA → conto IVA, cliente → conto partitario
- Scadenzario: `fatture_scadenze` esiste ma non è nel flusso operativo — collegarlo alla pipeline come task post-DEFINITIVA
- Riconciliazione incassi: matching pagamento ↔ scadenza (almeno il modello dati)

**Scelta architetturale:**

- La generazione scritture può essere un task pipeline (step post-DEFINITIVA o post-INVIATA)
- Il mapping conti va in configurazione (tabella lookup), non hardcoded
- Valutare se la contabilità è un modulo separato che consuma eventi da `event_log` (disaccoppiamento) o se è integrato nella pipeline lotti

---

## 3. Multi-company e multi-esercizio

**Problema:** il modello parla di BA/utility/emittente ma non è chiaro il supporto per esercizi fiscali multipli aperti e consolidamento tra società.

**Da implementare:**

- Esercizio fiscale come entità esplicita (non solo `competenza_mese`)
- Supporto a due esercizi aperti contemporaneamente (chiusura esercizio precedente + operatività corrente)
- Numerazione fatture per esercizio/sezionale con reset annuale
- Perimetro commessa esteso: `(emittente, esercizio, BA, utility, competenza)`
- Se multi-company: isolamento dati per società con possibilità di query cross-company per consolidamento

**Attenzione:**

- La numerazione fiscale (DEFINITIVA) deve rispettare i vincoli di sequenzialità per sezionale/esercizio — questo è un requisito normativo italiano non negoziabile

---

## 4. Audit trail formale

**Problema:** l'event_log è ottimo per l'operatività ma non è sufficiente per compliance formale (revisori, SOX-like, certificazione bilancio).

**Da implementare:**

- Registrare `user_id` e `ruolo` su ogni evento (chi ha fatto cosa)
- Propagare `correlation_id` ai livelli mancanti:
  - `PipelineStepExecutor` → task_run
  - `CommessaPushOrchestrator` → eventi push
- Garantire non-ripudiabilità: trigger append-only già c'è, verificare che nessun path applicativo possa bypassarlo
- Retention policy: definire per quanto tempo conservare i log (normativa fiscale italiana: 10 anni per documenti fiscali)

**Quick win:**

- Aggiungere `user_id` a `fn_log_event()` — è una modifica piccola con impatto grande sulla tracciabilità

---

## 5. Dashboard operative

**Problema:** il modello dati è pronto per un'operatività sofisticata ma senza interfaccia il vantaggio si perde.

**Quando ci lavori, tenere presente:**

- **Vista lotti:** stato corrente, ultimo evento da `event_log`, task_run con tentativo ed esito, segnalazioni attive con severity — l'operatore deve capire in 5 secondi se un lotto è sano o ha problemi
- **Vista errori:** filtro per severity ERROR su event_log nelle ultime N ore, con link diretto al lotto/commessa coinvolto
- **Vista push:** esito ultimo run per sorgente (contatori created/updated/skipped/errors), handler in errore evidenziati
- **Azioni rapide:** rerun lotto in errore, reset a step precedente (con rollback), approvazione commessa — senza passare da API manuali

**Principio:** la dashboard non è un report, è uno strumento di governo. L'operatore deve poter agire, non solo guardare.

---

## 6. Alerting e monitoring produzione

**Problema:** i KPI sono definiti ma non c'è notifica automatica. Un lotto bloccato in ERRORE per ore è invisibile senza monitoring.

**Da implementare (anche minimale):**

- Query periodica su `event_log` con `severity = 'ERROR'` nelle ultime N ore
- Alert su lotti in `IN_ESECUZIONE` da più di X minuti (possibile stallo)
- Alert su push con percentuale errori sopra soglia
- Canale notifica: anche solo email o webhook — l'importante è che esista

**Approccio consigliato:**

- Job Django/cron leggero che interroga event_log e manda notifiche
- Non serve un sistema di monitoring esterno in prima battuta

---

## 7. Correlation_id — completamento propagazione

**Problema:** documentato onestamente nella guida, ma è un gap tecnico concreto che limita il debug e l'audit.

**Da fare:**

- Propagare `correlation_id` da `LottoPipelineRunner` a `PipelineStepExecutor`
- Propagare ai singoli `task_run` (fn_start/complete/fail_lotto_task_run)
- Generare `correlation_id` nel `CommessaPushOrchestrator` e propagarlo agli eventi push
- Risultato atteso: una singola query su `correlation_id` ricostruisce l'intera timeline di qualsiasi operazione

---

## 8. Flusso errore documentato (diagramma)

**Problema:** il flowchart principale resta happy-path. Con tutto il framework di gestione errori ora presente, manca una visualizzazione del flusso alternativo.

**Da fare:**

- Diagramma di stato del lotto: `DRAFT` → `IN_ESECUZIONE` → `COMPLETATO` | `ERRORE` → `rerun` / `reset`
- Diagramma di stato del task_run: `IN_ESECUZIONE` → `COMPLETATO` | `ERRORE` | `ANNULLATO`
- Evidenziare: dove il rollback è possibile, dove serve intervento manuale, dove il retry è automatico
- Formato: Mermaid `stateDiagram-v2`, coerente col resto della guida

---

## Ordine di attacco suggerito
 i P0 sono cose che puoi fare in poche ore e sbloccano molto, i P1 sono bloccanti per andare in produzione reale, i P2-P3 possono crescere incrementalmente.
| Priorità | Item                                 | Motivazione                                                     |
| -------- | ------------------------------------ | --------------------------------------------------------------- |
| **P0**   | Correlation_id completo (#7)         | Poco effort, abilita debug e audit su tutto il resto            |
| **P0**   | User_id su event_log (#4 quick win)  | Una riga di codice, impatto enorme                              |
| **P1**   | Note di credito (#1)                 | Bloccante per adozione — senza NC non si va in produzione reale |
| **P1**   | Scadenzario operativo (#2 parziale)  | `fatture_scadenze` esiste, va solo collegato al flusso          |
| **P2**   | Multi-esercizio (#3)                 | Necessario per il primo anno fiscale reale                      |
| **P2**   | Diagrammi di stato (#8)              | Aiuta lo sviluppo di tutto il resto                             |
| **P3**   | Integrazione contabile completa (#2) | Modulo separato, può crescere incrementalmente                  |
| **P3**   | Dashboard (#5)                       | Dipende da stabilità del modello dati sottostante               |
| **P3**   | Alerting (#6)                        | Utile ma non bloccante fino alla produzione                     |