# Sviluppo Rettifiche Prezzi — ZeroERP (WIP)

> Stato: **DA IMPLEMENTARE** (DB-L4 della roadmap pricing)
>
> Ultima revisione: aprile 2026
>
> Documento estratto da `sviluppo-listini.md` per isolare il perimetro rettifiche come fase autonoma.
>
> Prerequisiti:
>
> * Schema `vendite.listini*` operativo fino a DB-L3 (listini, versioni, righe, associazioni, resolver, integrazione commessa)
> * Pipeline fatturazione a lotti operativa (emissione fatture da `attivita_fatturabili`)
> * Campi tecnici `prezzo_bloccato` (su `commesse_attivita` e `attivita_fatturabili`) e `prezzo_da_riallineare` (su `commesse_attivita`) gia' in schema
>
> Riferimenti:
>
> * [sviluppo-listini.md](sviluppo-listini.md) — architettura pricing, resolver, integrazione commessa (documento padre)
> * [gestione-commesse-v2.md](../work-done/gestione-commesse-v2.md) — pipeline commesse e fatturazione
> * [fatturazione-modello-utilities-gas-ee-idrico.md](fatturazione-modello-utilities-gas-ee-idrico.md) — modello pricing utilities

---

## 1) Obiettivo

Gestire le **modifiche retroattive ai prezzi di listino** senza riscrivere documenti gia' emessi. Quando un prezzo viene corretto dopo che una o piu' fatture hanno gia' applicato il valore precedente, il sistema deve produrre **documenti correttivi delta** (note di credito/debito o attivita' negative/positive) tracciati in modo deterministico e idempotente.

Il motore serve sia scenari di correzione puntuale (operatore che corregge un errore) sia scenari massivi (job automatico che rileva un update retroattivo di `listini_versioni`/`listini_righe` e apre l'analisi di impatto su tutto il perimetro storico).

---

## 2) Principi

1. **Nessuna riscrittura distruttiva di fatture emesse**. Le fatture storiche restano immutate in `fatture` e `fatture_righe`.
2. **Rettifica sempre tramite delta tracciato**, con audit completo della modifica originale + dei documenti correttivi emessi.
3. **Motore unico** per canale manuale e automatico, per evitare divergenze di risultato tra processi umani e batch.
4. **Idempotenza**: rilanciare la stessa analisi produce lo stesso set di delta (no doppi conteggi).
5. **Confinamento al layer pricing**: il motore delta non deve conoscere dettagli di fatturazione fiscale, si appoggia su `attivita_fatturabili`.

---

## 3) Flusso comune (entrambi i canali)

Passi logici del motore, validi sia per canale manuale sia per canale automatico:

1. **Rilevazione mismatch prezzo**
   - confronto tra il nuovo prezzo risolto (via `fn_resolve_prezzo_listino`) e il prezzo gia' snapshottato su `attivita_fatturabili` (se `prezzo_bloccato = FALSE`)
2. **Calcolo delta per perimetro** (riga / documento / periodo)
   - perimetro puo' essere una singola riga, un intero documento o un intervallo temporale a seconda del trigger
3. **Emissione documento correttivo**
   - attivita' negativa/positiva se la riga non e' ancora fatturata
   - nota di credito/debito se la riga e' gia' in fattura emessa
   - la scelta tra i due canali segue policy documento (decisione aperta, vedi §6)
4. **Audit esito**
   - registrazione delta calcolato, riga sorgente, riga correttiva, motivo, canale, operatore/job

---

## 4) Rettifiche retroattive (fatture gia emesse)

### 4.1 Perimetro minimo di ricerca impatti

Una ricerca di impatti deve considerare:

1. righe emesse con `listino_versione_id` coinvolto nella modifica retroattiva,
2. `data_competenza` nel range temporale corretto (intersezione fra validita' versione e periodo di competenza riga),
3. combinazione dimensionale coerente (`articolo`, `uom`, `BA/utility/emittente`),
4. stato documento **gia' emesso/fatturato** (riga presente in `fatture_righe`, non solo in `attivita_fatturabili`).

### 4.2 Regola operativa

1. Nessun update della fattura storica.
2. Solo emissione di un delta correttivo tracciato.
3. Il delta deve essere **atomico rispetto all'analisi**: o si emettono tutti i delta del perimetro, o nessuno.

### 4.3 Trigger di avvio analisi

**Canale automatico**:

1. trigger su `UPDATE` retroattivo di `listini_versioni` o `listini_righe` (update che tocca periodi con fatturazione gia' emessa)
2. il trigger accoda un job di analisi impatti (non esegue in-line per evitare lock prolungati su transazione applicativa)
3. il job esegue il motore delta sul perimetro identificato

**Canale manuale**:

1. operatore avvia l'analisi da UI amministrativa indicando perimetro (riga, documento, periodo, combinazione dimensionale)
2. il motore restituisce il preview delta
3. operatore conferma → emissione documenti correttivi

Entrambi i canali usano lo stesso motore di ricerca impatti e lo stesso algoritmo delta: cambia solo l'innesco.

---

## 5) Canali di esecuzione (enum `canale_rettifica`)

| Canale | Innesco | Conferma | Uso tipico |
| --- | --- | --- | --- |
| `MANUALE` | Operatore da UI | Esplicita (preview → confirm) | Volumi piccoli, correzioni puntuali |
| `AUTOMATICA` | Job schedulato su modifica retroattiva listino | Policy-driven (soglie, perimetro) | Volumi massivi utilities |

**Motivazione**:

1. copre sia volumi piccoli sia utilities massive,
2. stesso algoritmo riduce divergenze di risultato,
3. audit unico semplifica compliance e troubleshooting.

---

## 6) Bloccanti da chiudere prima di avviare lo sviluppo

Aggiornati al aprile 2026. Sono i punti 7-10 della vecchia checklist `gestione-listini.md` §11, tutti ancora aperti:

1. [ ] **Perimetro ricerca rettifiche retroattive** — definire il comportamento esatto per:
   - finestra temporale massima di retroattivita' (es. "rettifiche ammesse solo entro N anni")
   - criterio di stop se il perimetro intercetta righe con `prezzo_bloccato = TRUE` (skippare? errore? emettere comunque?)
   - gestione righe con override manuale documento (escludere?)

2. [ ] **Formato audit rettifica minimo** — definire:
   - tabella/e dedicate (`vendite.rettifiche` + `vendite.rettifiche_righe`? oppure campi su `attivita_fatturabili`?)
   - campi minimi: id originale, id correttiva, delta, motivo, canale, operatore/job, timestamp, hash idempotenza
   - visibilita' e query di lettura (esposte a chi, con quali permessi)

3. [ ] **Perimetro v1: solo `FIXED` attivo** — formalizzare che:
   - rettifiche v1 agiscono solo su pricing in modalita' `FIXED`
   - `FORMULA` e `SCAGLIONI` (v2) avranno motore rettifica separato o esteso

4. [ ] **Regole operative di segmentazione listini** — definire linee guida per minimizzare le collisioni `AMBIGUOUS_PRICE_MATCH` in produzione (tema operativo, non DB). Deve essere chiuso prima di dare il via a modifiche retroattive su listini condivisi.

**Gate**: senza i punti 1 e 2 chiusi non si puo' avviare l'implementazione DB-L4. I punti 3 e 4 vanno chiusi entro il gate di chiusura.

---

## 7) Roadmap DB-L4 (proposta)

### 7.1 Schema base rettifiche

- [ ] tabella `vendite.rettifiche` (testata: id, canale, stato, operatore, data_avvio, data_conferma, perimetro_json, totale_delta)
- [ ] tabella `vendite.rettifiche_righe` (dettaglio: id, rettifica_id, attivita_fatturabile_origine_id, attivita_fatturabile_correttiva_id, delta, prezzo_vecchio, prezzo_nuovo, motivo)
- [ ] indici per lookup idempotenza (hash su `(attivita_fatturabile_origine_id, listino_versione_id_old, listino_versione_id_new)`)

### 7.2 Funzioni motore delta

- [ ] `fn_rettifiche_analizza_perimetro(...)` — analisi senza side-effect, restituisce preview delta
- [ ] `fn_rettifiche_conferma(rettifica_id)` — emette attivita' correttive e marca la rettifica come `CONFERMATA`
- [ ] `fn_rettifiche_trigger_automatico()` — funzione trigger su UPDATE retroattivo listini (accoda job senza eseguire in-line)

### 7.3 Canali

- [ ] canale manuale (endpoint backend + UI)
- [ ] canale automatico (job pgAgent + coda analisi)

### 7.4 Audit

- [ ] log su `dbops.audit_log` con categoria dedicata `RETTIFICA`
- [ ] visibilita' delle rettifiche da pagina dedicata (vendite → rettifiche)

### 7.5 Test pgtap

- [ ] perimetro ricerca impatti corretto
- [ ] delta calcolato correttamente su riga singola
- [ ] delta calcolato correttamente su perimetro multiplo
- [ ] idempotenza: rilancio stessa analisi non duplica delta
- [ ] trigger automatico su UPDATE retroattivo listini accoda job
- [ ] rispetto `prezzo_bloccato` secondo policy definita in §6.1
- [ ] audit completo su tutte le operazioni

---

## 8) Integrazione con backend/frontend

Una volta chiuso DB-L4, sara' necessario aggiungere:

### Backend (apps/vendite)

- [ ] `rettifiche_repository.py` — CRUD rettifiche, query di analisi perimetro, wrapper funzioni DB
- [ ] `rettifiche_service.py` — orchestrazione flussi manuale/automatico, validazione perimetro
- [ ] API views + urls (~6 endpoint: lista, dettaglio, avvia analisi, preview, conferma, annulla)
- [ ] test service + API (~20 test)
- [ ] job pgAgent di polling coda analisi automatica

### Frontend (vendite)

- [ ] API client `vendite/api/rettifiche.js`
- [ ] store Pinia `vendite/stores/rettifiche.js`
- [ ] `RettificheListView.vue` — lista rettifiche con filtri stato/canale/data
- [ ] `RettificaDrawer.vue` — dettaglio con righe delta e azioni conferma/annulla
- [ ] `AvviaRettificaManualeDialog.vue` — dialog per avvio canale manuale
- [ ] navigazione sidebar + routing (voce vendite → Rettifiche)
- [ ] i18n chiavi `rettifiche.*`

### Fuori scope v1

1. Formula engine completo utilities (v2)
2. Scaglioni avanzati multi-fascia (v2)
3. Rettifiche su modalita' `FORMULA`/`SCAGLIONI` (v2)

---

## 9) Gate di chiusura

- [ ] tutti i test pgtap rettifiche verdi
- [ ] motore delta idempotente verificato con stress test
- [ ] audit rettifiche completo e leggibile da UI
- [ ] documentazione API in `docs/it/backend/vendite/manual/`
- [ ] guida utente in `docs/it/guide/` (come si avvia una rettifica, come si interpreta un delta)

---

*Sviluppo Rettifiche Prezzi — ZeroERP (aprile 2026, estratto da sviluppo-listini)*
