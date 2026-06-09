# push_preventivo_handler (Django)

## Scopo

Handler flusso `vendita.push_preventivo` — primo handler reale del motore
pratiche. Al passaggio del flusso `CONFERMA` in `IN_CORSO` spinge il preventivo
ACCETTATO in **commessa diretta** applicando la politica di fatturazione
(`IMMEDIATA`/`DIFFERITA`) presa dai `handler_params` del template, e porta la
commessa a `PRONTA_FATTURAZIONE`.

## Contesto

- File: `apps/vendite/handlers/push_preventivo_handler.py`.
- Registrato in `HANDLER_MAP` da `apps/vendite/apps.py:ready()` via
  `register_handler("vendita.push_preventivo", PushPreventivoHandler)` (import
  lazy per evitare la dipendenza `pratiche→vendite`).
- Invocato da `pratiche_service.avvia_flusso` → `dispatch_handler` quando il
  flusso `CONFERMA` (template con `handler_id`) passa a `IN_CORSO`.
- **Non reimplementa** il push: delega all'orchestratore esistente
  `pr_run_commesse_push_one` (regola del 2).

## Contratto

```python
def execute(self, flusso_id: int, pratica_id: int,
            meta: dict, handler_params: dict, user: str | None = None) -> dict
```

- `handler_params.modalita_fatturazione` ∈ `{IMMEDIATA, DIFFERITA}` (validato in
  codice; **nessuna** tabella `config.modalita_fatturazione`).
- `meta.preventivo_id` (int, obbligatorio).
- `meta.competenza_fatturazione` (date, obbligatorio solo per `DIFFERITA`).

## Comportamento (tutto in una transazione atomica)

1. valida `modalita_fatturazione` → `E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA`;
2. carica preventivo, verifica `ACCETTATO` → `E_VENDITA_PREVENTIVO_NON_ACCETTATO`;
3. risolve politica: `IMMEDIATA` → `fatturazione_immediata=true` + mese corrente;
   `DIFFERITA` → `false` + `meta.competenza_fatturazione`
   (`E_VENDITA_COMPETENZA_RICHIESTA` se assente);
4. idempotenza: commessa già agganciata → `E_VENDITA_PREVENTIVO_GIA_PUSHATO`;
5. **c7-2**: scrive `fatturazione_immediata`+`competenza_mese` sul preventivo
   (`update_preventivo`), poi `pr_run_commesse_push_one(sorgente_codice='PREVENTIVO')`;
6. `fn_approva_commessa_attivita` (righe → APPROVATA);
7. `fn_cambia_stato_commessa(..., 'PRONTA_FATTURAZIONE')` (guard DB: ≥1 riga
   APPROVATA+NON_EMESSA);
8. aggancio `pratiche_sorgenti`: preventivo `ROOT` (uid), commessa `COLLEGATO` (id);
9. preventivo → `EVASO` (transizione esplicita, senza swallow);
10. giornale `DOMINIO_COMMESSA_CREATA` + `DOMINIO_PREVENTIVO_EVASO`
    (`fn_log_evento_dominio`, `origine='HANDLER'`).

## Idempotenza e concorrenza

- `commesse_sorgenti` (UNIQUE) impedisce due commesse dallo stesso preventivo;
- `avvia_flusso` aggiorna lo stato del flusso (lock di riga) → due avvii
  concorrenti sullo stesso flusso si serializzano;
- difesa runtime: il check "preventivo `ACCETTATO`" protegge anche se i
  prerequisiti del flusso (guard BEFORE INSERT) fossero cambiati dopo la creazione.

## Limiti v1 (gap dichiarato §9)

- Destinazione **fissa = commessa diretta**: nessuno split per `natura_vendita`.
  Una riga `SERVIZIO_RICORRENTE` finisce in commessa senza blocco (il guard
  `E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA` non è ancora a DB).

## Dipendenze DB

- `vendite.fn_approva_commessa_attivita`, `vendite.fn_cambia_stato_commessa`
- `pratiche.fn_log_evento_dominio`
- pipeline push: `pr_run_commesse_push_one` → `fn_get_or_create_commessa` /
  `fn_upsert_commessa_attivita`
