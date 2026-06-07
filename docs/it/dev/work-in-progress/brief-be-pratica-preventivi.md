# Brief BE — Pratica `PREVENTIVI` (handler `vendita.push_preventivo`)

> **Tipo documento**: brief backend (Django). Prerequisito: deliverable DB del
> [brief-db-pratica-preventivi.md](brief-db-pratica-preventivi.md) applicati
> (seed catalogo, `config.modalita_fatturazione`, `fn_log_evento_dominio`,
> GRANT, codici errore). Coerente con
> [feedback_be_fe_attende_prerequisiti_db]: **non** anticipare codice che dipende
> da oggetti DB non ancora consegnati.
>
> **Data**: 2026-06-06 · **Stato**: pronto, riscontri di codice risolti
>
> **Decisione di prodotto (Tid)**: politica immediata/differita **in
> configurazione** (`handler_params`), non scelta dall'operatore al runtime.

---

## 1. Obiettivo BE

Registrare il **primo handler reale** del motore pratiche
(`HANDLER_MAP` oggi vuoto) e cablarne il dispatch. L'handler
`vendita.push_preventivo`, al passaggio del flusso `CONFERMA` in `IN_CORSO`:

1. valida i propri `handler_params` (politica) — Contratto handler (D-f);
2. risolve la competenza secondo la politica;
3. **riusa il push esistente** preventivo→commessa applicando la politica;
4. aggancia la pratica al preventivo (ROOT) e alla commessa (COLLEGATO);
5. scrive gli eventi di dominio nel giornale;
6. porta il preventivo a `EVASO`.

**Principio guida** ([feedback_regola_del_2_estrai_bb], analisi §2.2): l'handler
**non reimplementa** il push — delega a `preventivi_service.push_a_commessa`
(già esistente). È un orchestratore sottile sopra il dominio.

---

## 2. Riscontri di codice (verificati)

| Elemento | Stato reale | File |
|---|---|---|
| `BaseFlussoHandler` (Protocol) `execute(flusso_id, pratica_id, meta, handler_params)->dict` | **Esiste** | `apps/pratiche/services/handler_registry.py:14` |
| `HANDLER_MAP` | **Esiste, vuoto** | `handler_registry.py:32` |
| `dispatch_handler(flusso_id)` (lookup handler_key + params, instanzia, `execute`) | **Esiste, NON auto-wired** | `apps/pratiche/services/pratiche_service.py:338` |
| Transizioni flusso (`avvia_flusso`, `completa_flusso`, `cambia_stato_flusso`) | **Esistono** | `pratiche_service.py:252-314` |
| `push_a_commessa(preventivo_id)` → `pr_run_commesse_push_one(sorgente_codice='PREVENTIVO', sorgente_uid)` | **Esiste** | `apps/vendite/services/preventivi_service.py`, `commesse_service.py` |
| Pattern RPC fn DB (`cursor.execute("SELECT vendite.fn_...(p_x => %s)")`) | **Esiste** | `apps/vendite/db/commesse_repository.py` |
| `log_evento_dominio` / scrittura giornale da Python | **ASSENTE** (solo trigger) | — |
| `apps/vendite/handlers/` | **NON esiste** (da creare) | — |
| `ErrorManager.require(cond, code=, message=)` → `ServiceError` → envelope DRF | **Esiste** | `apps/core/services/error_manager.py:19`, `service_errors.py` |
| `PayloadValidator` (whitelist chiavi, estrazione tipata) | **Esiste** | `apps/core/services/payload_helpers.py:60` |

---

## 3. Deliverable BE

### C1 — `apps/vendite/handlers/push_preventivo_handler.py`

Nuovo package `apps/vendite/handlers/` (oggi assente). Classe che implementa il
Protocol `BaseFlussoHandler`. Logica in §5. **Delega** il push a
`preventivi_service`, **non** chiama direttamente le fn commessa.

### C2 — Registrazione in `HANDLER_MAP`

`handler_registry.py`: `HANDLER_MAP["vendita.push_preventivo"] =
PushPreventivoHandler`. Primo handler reale → validare la firma del Protocol su
un caso vero.

> **Attenzione import cycle**: l'handler vive in `apps/vendite`, il registry in
> `apps/pratiche`. Per non creare dipendenza `pratiche→vendite`, registrare via
> **lazy import / registry pluggable** (es. `apps/vendite/apps.py:ready()` che
> popola `HANDLER_MAP`, oppure import differito dentro `get_handler`). Decidere
> il pattern in apertura: è il primo caso, fa giurisprudenza.

### C3 — Wiring del dispatch (oggi NON automatico)

`dispatch_handler` esiste ma **non** è invocato sul cambio stato. Serve il
trigger applicativo: quando il flusso `CONFERMA` entra in `IN_CORSO`, chiamare
`dispatch_handler(flusso_id)`. Due opzioni — **scegliere e dichiarare**:

- **(a)** dentro `avvia_flusso`/`cambia_stato_flusso`: se il nuovo stato è
  `IN_CORSO` e il template ha `handler_id`, invoca `dispatch_handler`. Automatico
  e uniforme per ogni futuro handler.
- **(b)** azione API esplicita "esegui handler" sul flusso, chiamata dalla UI.

> **Raccomandazione**: (a) — il dispatch automatico su `IN_CORSO` è il
> comportamento atteso dalla guida pratiche e rende il motore "configurabile per
> dati" senza UI dedicata. Da fare con guardia: solo se `handler_id` valorizzato.

### C4 — Validazione `handler_params` (D-f)

Validare con `ErrorManager.require` / `PayloadValidator`:
`modalita_fatturazione ∈ {IMMEDIATA, DIFFERITA}` (lookup su
`config.modalita_fatturazione`) → altrimenti
`E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA`. Mai `KeyError` grezzo.

### C5 — Wrapper scrittura giornale di dominio

Sopra la fn DB `pratiche.fn_log_evento_dominio` (deliverable DB B-NEW): metodo
repository `PraticheRepository.log_evento_dominio(pratica_id, flusso_id,
tipo_evento, meta)` + facade `pratiche_service.log_evento_dominio(...)`.
Chiamato dall'handler per `DOMINIO_COMMESSA_CREATA` e `DOMINIO_PREVENTIVO_EVASO`.

### C6 — Aggancio `pratiche_sorgenti` dal BE

Metodo repository che fa l'INSERT idempotente (`ON CONFLICT DO NOTHING` sulla
UNIQUE `(pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link)`):
- preventivo come `ROOT` (può già esistere se agganciato in `PREVENTIVAZIONE`);
- commessa come `COLLEGATO`.

### C7 — Riconciliazione politica sul percorso pratica (conseguenza decisione)

Il push esistente prende `fatturazione_immediata`/`competenza` dal preventivo.
Sul percorso pratica **la config è autorevole**. L'handler deve garantire che la
commessa riceva la politica da `handler_params`/`flussi.meta`, **non** dal valore
d'accettazione. Due strade — **da decidere (verifica BE)**:

- **(c7-1)** parametrizzare il push: estendere `push_a_commessa` /
  `pr_run_commesse_push_one` con `fatturazione_immediata` + `competenza_mese`
  espliciti che **sovrascrivono** la sorgente;
- **(c7-2)** l'handler scrive `fatturazione_immediata`/`competenza` sul
  preventivo **prima** del push, così la pipeline li propaga.

> **Verifica preliminare bloccante**: *dove* la pipeline legge oggi
> `fatturazione_immediata` e `competenza_mese` per il preventivo (colonna su
> `preventivi`/`preventivi_righe`? payload d'accettazione persistito dove?).
> Dalla risposta dipende se (c7-1) o (c7-2). **Raccomandazione**: (c7-1) —
> parametri espliciti evitano di mutare lo stato del preventivo come effetto
> collaterale e tengono l'handler l'unica fonte autorevole. Il default dei
> parametri resta "leggi dalla sorgente" per non rompere il push autonomo.

---

## 4. Idempotenza (riuso, non riscrittura)

L'idempotenza è **già garificata** a valle:
- `commesse_sorgenti` ha UNIQUE `(sorgente_tipo_id, sorgente_uid, ruolo_link)` →
  un preventivo non genera due commesse;
- la riga commessa è idempotente su `(commessa_id, segment_key)`.

L'handler aggiunge solo l'**errore semantico** `E_VENDITA_PREVENTIVO_GIA_PUSHATO`
quando il push è già avvenuto, in difesa-in-profondità:
- **strato alto**: prima del push, l'handler verifica nel giornale/sorgenti se
  `DOMINIO_COMMESSA_CREATA` è già presente per quel preventivo → se sì, non
  riprova e propaga l'errore parlante (Opzione 1 conservativa, §5.3.3 analisi);
- **strato basso**: la UNIQUE DB resta l'ultima linea.

> **Verifica BE**: l'orchestratore `pr_run_commesse_push_one` oggi *come* reagisce
> al ri-push (errore? no-op? report con 0 righe)? Se solleva una unique violation
> grezza, mapparla a `E_VENDITA_PREVENTIVO_GIA_PUSHATO` (vedi
> `map_integrity_error` / `ErrorManager`).

---

## 5. Pseudo-flow handler `vendita.push_preventivo`

Invocato da `dispatch_handler` quando `CONFERMA` entra in `IN_CORSO`.

```text
execute(flusso_id, pratica_id, meta, handler_params):

 1. modalita = handler_params["modalita_fatturazione"]
    require modalita in lookup(config.modalita_fatturazione)
        else E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA

 2. preventivo_id = meta["preventivo_id"]
    carica preventivo; verifica stato == ACCETTATO (id 4)

 3. competenza:
      IMMEDIATA → mese corrente; fatturazione_immediata = true
      DIFFERITA → meta["competenza_fatturazione"]
                  else E_VENDITA_COMPETENZA_RICHIESTA
                  fatturazione_immediata = false

 4. idempotenza alta: se giornale/sorgenti già ha COMMESSA per questo preventivo
        → E_VENDITA_PREVENTIVO_GIA_PUSHATO (no doppio push)

 5. push = preventivi_service.push_a_commessa(
              preventivo_id,
              fatturazione_immediata=<da step 3>,   # c7-1 (override config)
              competenza_mese=<da step 3>)
    # destinazione FISSA = commessa diretta (no split natura in questo brief)

 6. pratiche_sorgenti:
      upsert (pratica_id, PREVENTIVO, preventivo.uid, ROOT)   # idempotente
      upsert (pratica_id, COMMESSA,  commessa_id,   COLLEGATO)

 7. preventivo → EVASO (id 10)   # tutte le righe smistate (destinazione unica)

 8. giornale:
      log_evento_dominio(DOMINIO_COMMESSA_CREATA,
          meta={commessa_id, preventivo_id, competenza, modalita})
      log_evento_dominio(DOMINIO_PREVENTIVO_EVASO, meta={preventivo_id})

 9. return {commessa_id, preventivo_id, modalita, competenza}
```

A valle, senza altra logica: `fn_list_commesse_emittibili(p_competenza_mese)`
includerà la commessa nel lotto giusto (mese corrente per IMMEDIATA, mese scelto
per DIFFERITA) — **a condizione** che la commessa risulti emittibile (vedi
domanda DB V9: se serve un passo di approvazione, l'handler lo invoca tra 5 e 8).

---

## 6. Test (Django + smoke)

| ID | Test | Atteso |
|---|---|---|
| BE-T1 | dispatch su `CONFERMA` `IMMEDIATA`, preventivo ACCETTATO | commessa con `fatturazione_immediata=true`, righe `competenza_mese=mese corrente`; sorgenti agganciate; preventivo `EVASO` |
| BE-T2 | `DIFFERITA` con `meta.competenza_fatturazione` | commessa `fatturazione_immediata=false`, `competenza_mese=mese scelto` |
| BE-T3 | `DIFFERITA` senza competenza | `E_VENDITA_COMPETENZA_RICHIESTA`, nessuna commessa |
| BE-T4 | `handler_params.modalita_fatturazione` ignota | `E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA` |
| BE-T5 | doppio dispatch sullo stesso preventivo | seconda volta `E_VENDITA_PREVENTIVO_GIA_PUSHATO`, **nessuna** commessa duplicata |
| BE-T6 | giornale | `DOMINIO_COMMESSA_CREATA` + `DOMINIO_PREVENTIVO_EVASO` con meta corretto |
| BE-T7 | wiring dispatch | entrando in `IN_CORSO` su flusso con `handler_id`, l'handler parte; su flusso senza handler, no-op |
| BE-S1 | smoke E2E (idempotente, cleanup proattivo — [feedback_smoke_test_idempotenti]) | crea pratica → flussi → accetta preventivo → CONFERMA → commessa emittibile, pratica CHIUSA |

---

## 7. Domande aperte BE (prima del piano)

1. **C3**: dispatch automatico su `IN_CORSO` (a) vs azione esplicita (b)?
   (raccomandato a).
2. **C7**: override politica via parametri push (c7-1) vs scrittura su preventivo
   (c7-2)? Dipende da *dove* la pipeline legge `fatturazione_immediata`/
   `competenza` oggi (verifica preliminare).
3. **C2**: pattern di registrazione handler cross-app per evitare ciclo
   `pratiche→vendite` (lazy import in `vendite/apps.py:ready()`?).
4. **§4**: comportamento attuale dell'orchestratore sul ri-push (per il mapping
   a errore semantico).
5. **DB V9** (eredita dal brief DB): se la commessa necessita approvazione per
   diventare emittibile, l'handler deve invocare quella funzione (step 5–8).

---

*Brief BE — Pratica PREVENTIVI / handler vendita.push_preventivo — ZeroERP
(2026-06-06).*
