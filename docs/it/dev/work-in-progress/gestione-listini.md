# Gestione listini - analisi e decisioni operative (24-02-2026)

## 1) Obiettivo

Definire un modello listini/prezzi scalabile che supporti:

1. pricing standard (prezzo fisso/versionato),
2. pricing utilities (gas/energia/idrico) con evoluzione futura a formule/scaglioni,
3. integrazione piena con modello commessa v2,
4. rettifiche prezzi sia manuali che automatiche.

Documento di riferimento per decisioni DB prima dell'implementazione.

Riferimenti:

1. `docs/it/dev/work-in-progress/gestione-commesse-v2.md`
2. `docs/it/dbzero/catalogo/manual/articoli_componenti.md`
3. `docs/it/dbzero/catalogo/manual/articoli_uom_operativa.md`
4. `docs/it/dbzero/vendite/manual/ordini_righe.md`
5. `docs/it/dbzero/vendite/manual/preventivi_righe.md`

---

## 2) Stato attuale e gap

Stato attuale:

1. Esiste una base molto buona su articoli, componenti BoM e UoM operative.
2. Esistono snapshot di conversione quantita (`factor_to_base`) nelle righe documento.
3. Esiste in `config` una classificazione tariffaria (`tipi_tariffe_ee`) ma non un motore listini completo.

Gap principali:

1. manca una struttura listini/versioni righe prezzo,
2. manca un resolver prezzo deterministico con precedenze,
3. manca una gestione rettifiche prezzi post-emissione,
4. manca una base dati pronta per formule/scaglioni utilities.

---

## 3) Principi architetturali

1. Modello commessa v2 invariato: nessun bypass.
2. Prezzo risolto in modo deterministico e auditabile.
3. Emittente fiscale dimensione attiva gia in v1.
4. UoM non forzata unica per articolo in listino.
5. Rettifiche possibili sia manuali che automatiche, con stesso motore delta.
6. Formule/scaglioni previste ma non obbligatorie in v1.

---

## 4) Decisioni chiave con motivazione

### 4.1 Emittente fiscale attiva in v1

Decisione:

1. `emittente_soggetto_ruolo_id` entra subito tra le dimensioni prezzo.

Motivazione:

1. e' gia centrale nei flussi fatturazione,
2. evitarla ora crea ambiguita su prezzi/fiscalita perimetro,
3. evita rework su resolver e migrazioni successive.

### 4.2 UoM non unica per articolo

Decisione:

1. la chiave prezzo include `articolo_id + uom_id` (non solo articolo).

Motivazione:

1. `catalogo.articoli_uom_operativa` prevede piu UoM operative per articolo,
2. forzare UoM unica romperebbe casi reali (ore, confezioni, conversioni operative),
3. mantiene coerenza con snapshot `factor_to_base` dei documenti.

### 4.3 Rettifiche manuali e automatiche

Decisione:

1. doppio canale rettifica (`MANUALE`, `AUTOMATICA`) con pipeline unica delta.

Motivazione:

1. nella pratica servono entrambi i canali,
2. un solo motore evita divergenze di risultato tra processi umani e batch,
3. audit unico semplifica compliance e troubleshooting.

### 4.4 Formule utilities in fase successiva

Decisione:

1. v1 listini con prezzi fissi/versionati,
2. predisposizione strutturale per `FORMULA` e `SCAGLIONI` in v2.

Motivazione:

1. accelera go-live con rischio controllato,
2. evita bloccare il progetto su formula engine complesso,
3. mantiene estendibilita senza cambiare schema base.

### 4.5 Contesto non-utility esplicito

Decisione:

1. il dominio include anche casi non-utility con `utility_id = NULL` (servizi commerciali puri).

Motivazione:

1. ordini/preventivi non sono sempre legati a utility,
2. il resolver deve coprire esplicitamente questi casi, non solo il perimetro utility.

---

## 5) Modello dati proposto (v1)

### 5.1 Tabelle core

1. `vendite.listini`
   - anagrafica listino (codice, descrizione, dominio, attivo).
   - `dominio` valori v1 ammessi:
     - `UTILITY`
     - `COMMERCIO`
   - domini futuri possibili:
     - `INDUSTRIA` (e altri perimetri verticali)
2. `vendite.listini_versioni`
   - versionamento temporale (`valido_dal`, `valido_al`, priorita, stato).
3. `vendite.listini_righe`
   - prezzo per contesto dimensionale.
4. `vendite.listini_associazioni`
   - assegnazione listino a perimetri (BA/utility/emittente/altro).
   - include `priorita` (tie-break tra listini candidati nello stesso contesto).

Regola operativa:

1. `listini_associazioni` non e solo configurazione UI;
2. il resolver deve prima ricavare i listini candidati da questa tabella,
3. poi applicare la precedenza dimensionale su `listini_righe`.
4. se i listini candidati sono multipli, la scelta non e "per listino vincente", ma per miglior match di riga su tutto il set candidati.

### 5.2 Dimensioni riga listino (v1 attive)

1. `articolo_id` obbligatorio,
2. `uom_id` obbligatorio,
3. `periodo` tramite versione listino (`valido_dal/valido_al`),
4. `billing_account_id` opzionale,
5. `utility_id` opzionale,
6. `emittente_soggetto_ruolo_id` opzionale ma attiva.

### 5.3 Regole di unicita

1. no overlap temporale per stessa combinazione dimensionale nella stessa versione logica,
2. unique su chiave completa dimensionale + versione,
3. coerenza date (`valido_al > valido_dal` o null open-ended).

### 5.4 Policy precisione prezzo (v1)

Decisione operativa confermata:

1. fino a `attivita_fatturabili` (inclusa) il prezzo usa precisione alta `numeric(22,10)`;
2. in `fatture_righe` il prezzo di aggregazione/esposizione resta a `6` decimali;
3. il resolver listino e le funzioni di push/pull non devono introdurre arrotondamenti anticipati.

Motivazione:

1. nel dominio utilities (gas/energia/idrico) sono frequenti importi unitari molto piccoli;
2. mantenere `22,10` a monte evita perdita di informazione prima della fase fiscale;
3. l'arrotondamento a `6` decimali rimane confinato al layer righe fattura.

---

## 6) Resolver prezzo (deterministico)

Ordine precedenza proposto:

1. `BA + utility + emittente + articolo + uom`
2. `BA + utility + articolo + uom`
3. `BA + emittente + articolo + uom` (non-utility)
4. `BA + articolo + uom` (non-utility)
5. `utility + emittente + articolo + uom`
6. `utility + articolo + uom`
7. `articolo + uom` (fallback)

Firma minima funzione (da recepire in DB-L2):

1. `fn_resolve_prezzo_listino(...)` deve ricevere `p_data_riferimento` obbligatoria,
2. senza `p_data_riferimento` la funzione deve andare in errore esplicito.

Tie-break:

1. priorita associazione listino (`listini_associazioni.priorita`),
2. priorita versione listino,
3. data validita piu specifica/recente,
4. id stabile.

Comportamento se non trovato:

1. errore esplicito (no fallback silenzioso).

Comportamento se ambiguo:

1. se due match restano equivalenti dopo tutti i tie-break, errore esplicito `AMBIGUOUS_PRICE_MATCH`.

Motivazione:

1. prevedibilita operativa,
2. riduzione anomalie "prezzo inatteso",
3. facilita test automatici.

Decisione su multi-listino:

1. precedenza per specificita riga su tutti i listini candidati;
2. priorita listino usata solo come tie-break.

---

## 7) Integrazione con commessa v2

Su `commesse_attivita` (o equivalente operativo) salvare:

1. `listino_versione_id`,
2. `prezzo_snapshot`,
3. `prezzo_bloccato`,
4. `pricing_mode` (`FIXED` in v1; `FORMULA/SCAGLIONI` pronti per v2).

Motivazione:

1. rerun idempotente,
2. audit "perche quel prezzo",
3. supporto revisioni listino senza mutare storico.

### 7.1 Gerarchia prezzo documento vs listino

Decisione:

1. se su documento e presente override manuale prezzo, quello prevale sul listino;
2. in quel caso si salva:
   - `prezzo_snapshot = prezzo_documento`,
   - `prezzo_bloccato = TRUE`,
   - `listino_versione_id = versione risolta alla data` (se risolvibile, per audit comparativo),
   - riferimento motivazione override in `meta`;
3. se non c'e override manuale, il prezzo viene dal resolver listino.

Caso specifico: preventivo `LIBERO` modificato dopo push su commessa

Decisione:

1. se il preventivo e ancora `LIBERO` e il prezzo viene modificato post-push:
   - la riga `commesse_attivita` viene marcata `prezzo_da_riallineare = TRUE`,
   - il prezzo non viene aggiornato in modo silenzioso;
2. il riallineamento avviene su conferma esplicita (ricalcolo su conferma);
3. dopo conferma, si aggiorna `prezzo_snapshot` sulla commessa e si mantiene audit della revisione.
4. allineamento con commesse-v2:
   - non si introduce nuovo stato business di commessa,
   - si usa flag tecnico di riallineamento + log evento.

Motivazione:

1. evita drift tra documento e commessa,
2. evita aggiornamenti opachi in processi commerciali ancora aperti.

Caso non ammesso:

1. se il documento non e piu `LIBERO` (es. convertito/confermato), il prezzo documento non puo alterare la commessa gia consolidata.

Motivazione:

1. scenario vendita reale frequente,
2. evita mismatch tra promessa economica e fatturazione.

### 7.2 Propagazione `prezzo_bloccato` verso attivita_fatturabili

Decisione:

1. `prezzo_bloccato` deve essere propagato come snapshot anche su `attivita_fatturabili`;
2. lo step 1 pipeline fatturazione legge il flag direttamente su `attivita_fatturabili`;
3. `commessa_attivita` resta la sorgente di verita, ma la copia su attivita evita join pesanti e ambiguita runtime.
4. DB-L3 deve introdurre esplicitamente il campo `attivita_fatturabili.prezzo_bloccato`.

Motivazione:

1. semplifica e rende deterministico il controllo prezzi nello step di fatturazione,
2. riduce dipendenze runtime dal dominio commessa durante la fase fiscale.

---

## 8) Rettifiche prezzi (manuale + automatica)

### 8.1 Regola generale

1. nessuna riscrittura distruttiva di fatture emesse,
2. rettifica sempre tramite delta tracciato.

### 8.2 Flusso comune

1. rilevazione mismatch prezzo,
2. calcolo delta per perimetro (riga/documento/periodo),
3. emissione documento correttivo (attivita negativa/positiva, nota credito/debito secondo policy),
4. audit esito.

### 8.3 Rettifiche retroattive (fatture gia emesse)

Perimetro minimo di ricerca impatti:

1. righe emesse con `listino_versione_id` coinvolto,
2. `data_competenza` nel range temporale corretto,
3. combinazione dimensionale coerente (`articolo`, `uom`, `BA/utility/emittente`),
4. stato documento gia emesso/fatturato.

Regola:

1. nessun update della fattura storica,
2. solo emissione delta correttivo tracciato.

Trigger di avvio ricerca retroattive:

1. canale automatico:
   - su modifica retroattiva di `listini_versioni`/`listini_righe` viene aperto un job di analisi impatti;
2. canale manuale:
   - operatore puo avviare la stessa analisi su richiesta;
3. entrambi i canali usano lo stesso motore di ricerca impatti.

### 8.4 Canali di esecuzione

1. `MANUALE`: avvio operatore con conferma,
2. `AUTOMATICA`: job schedulato policy-driven.

Motivazione:

1. copre sia volumi piccoli sia utilities massive,
2. stesso algoritmo riduce divergenze.

---

## 9) Evoluzione v2 formule/scaglioni (non bloccante v1)

Predisposizione consigliata:

1. tabella regole formula separata da `listini_righe`,
2. tabella scaglioni separata per consumi/ore,
3. mapping di input formula (letture, fasce, indici, coefficenti),
4. output sempre normalizzato a `prezzo_snapshot` per commessa.

Motivazione:

1. separa complessita matematica dal core listino,
2. facilita test e rollback.

---

## 10) Roadmap DB proposta (pricing)

### DB-L1 Schema base listini

1. creare `listini`, `listini_versioni`, `listini_righe`, `listini_associazioni`,
2. vincoli base e no-overlap temporale.

### DB-L2 Resolver e funzione prezzo

1. funzione `fn_resolve_prezzo_listino(...)`,
2. funzione `fn_resolve_commessa_prezzi(lotto_id)` per analisi prezzi stantii nel perimetro lotto,
3. precedenze ufficiali implementate e testate.

Nota implementativa corrente:

1. finche` il layer `commesse_*` non e` introdotto (DB-L3), `fn_resolve_commessa_prezzi`
   opera come equivalente operativo su `attivita_fatturabili` del lotto.

### DB-L3 Integrazione commessa

1. campi snapshot pricing in `commesse_attivita`,
2. aggancio resolver in push/pull commessa,
3. introduzione `attivita_fatturabili.prezzo_bloccato` e propagazione nel pull da `commesse_attivita`.

### DB-L4 Rettifiche

1. funzioni delta e registri audit rettifica,
2. canali `MANUALE` e `AUTOMATICA`.

### DB-L5 Test pgtap

1. precedenze resolver,
2. no-overlap versioni,
3. snapshot commessa,
4. `AMBIGUOUS_PRICE_MATCH` su match equivalente cross-listino,
5. override documento con `prezzo_bloccato = TRUE`,
6. propagazione `prezzo_bloccato` su `attivita_fatturabili`,
7. trigger/job retroattivo su modifica `listini_versioni`/`listini_righe`,
8. rettifiche delta idempotenti.

---

## 11) Bloccanti da chiudere prima dello sviluppo

1. conferma finale precedenze resolver (inclusi casi non-utility),
2. conferma ruolo operativo `listini_associazioni` nel resolver,
3. conferma gerarchia prezzo documento override vs listino,
4. conferma `p_data_riferimento` obbligatoria nella funzione resolver,
5. conferma perimetro ricerca rettifiche retroattive,
6. conferma domini enum `pricing_mode` e canale rettifica,
7. conferma formato audit rettifica minimo,
8. conferma perimetro v1: solo `FIXED` attivo.
9. conferma strategia multi-listino: specificita riga cross-listino + tie-break priorita associazione.
10. definire regole operative di segmentazione listini per minimizzare collisioni `AMBIGUOUS_PRICE_MATCH` in produzione.

Gate pratico richiesto:

1. chiudere i punti 1, 2 e 3 prima di DB-L3;
2. punti 4-10 completabili entro DB-L4.

Nota:

1. il tema "da riallineare" si considera chiuso solo quando il flag tecnico e` definito nello schema DB; la sola descrizione testuale non e` sufficiente.

---

## 12) Cosa resta fuori da questa fase

1. formula engine completo utilities,
2. scaglioni avanzati multi-fascia,
3. simulazioni tariffarie previsionali.

Queste parti sono previste nella v2 pricing, non bloccano la partenza del modello.

---

## 13) Tracking avanzamento (checklist operativa)

### 13.1 DB-L1 Schema base listini

- [x] creare tabelle `listini`, `listini_versioni`, `listini_righe`, `listini_associazioni`
- [x] introdurre campo `listini_associazioni.priorita`
- [x] introdurre campo `listini.dominio` con valori v1 (`UTILITY`, `COMMERCIO`)
- [x] vincoli date e no-overlap versioni
- [x] pgtap DDL base verde

### 13.2 DB-L2 Resolver pricing

- [x] creare `fn_resolve_prezzo_listino(...)` con `p_data_riferimento` obbligatoria
- [x] implementare precedenze utility + non-utility
- [x] implementare tie-break multi-listino con `listini_associazioni.priorita`
- [x] errore `AMBIGUOUS_PRICE_MATCH` su pareggio totale
- [x] creare `fn_resolve_commessa_prezzi(lotto_id)`
- [x] pgtap resolver verde

### 13.3 DB-L3 Integrazione commessa

- [x] estendere `commesse_attivita` con `pricing_mode`
- [x] estendere `commesse_attivita` con `prezzo_da_riallineare`
- [x] estendere `attivita_fatturabili` con `prezzo_bloccato`
- [x] aggiornare `fn_emit_attivita_fatturabili_da_commessa` per propagare `prezzo_bloccato`
- [x] gestire override documento (`prezzo_bloccato=TRUE`, `listino_versione_id` audit)
- [x] pgtap integrazione commessa verde

### 13.4 DB-L4 Rettifiche

- [ ] implementare motore delta rettifiche
- [ ] canale manuale
- [ ] canale automatico su modifica retroattiva listino
- [ ] audit rettifiche
- [ ] pgtap rettifiche verde

### 13.5 Gate di chiusura DB

- [ ] tutti i test pgtap listini/commessa verdi
- [ ] ownership campi/funzioni allineata tra `gestione-listini.md` e `gestione-commesse-v2.md`
- [ ] chiusura bloccanti §11
