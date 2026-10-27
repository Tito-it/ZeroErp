# push_preventivo_handler (Django)

## Scopo

Handler flusso `vendita.push_preventivo` — orchestratore **CONFERMA_VENDITA**,
primo handler reale del motore pratiche. Al passaggio del flusso `CONFERMA` in
`IN_CORSO` **smista per natura** le righe del preventivo `ACCETTATO` verso le
destinazioni operative (modello split, brief
[brief-preventivi-ordini.md](../../../dev/work-done/brief-preventivi-ordini.md)):

- righe **MERCE** (natura `destinazione_tipo='ORDINE_VENDITA'`) → **ordine DRAFT** via
  `fn_push_preventivo_a_ordine` (idempotenza di riga, BoM, snapshot prezzi);
- righe **SERVIZIO una-tantum** (`destinazione_tipo='COMMESSA'`) → **commessa
  diretta**, applicando la politica di fatturazione (`IMMEDIATA`/`DIFFERITA`) presa
  dai `handler_params`, e portandola a `PRONTA_FATTURAZIONE`;
- righe **RICORRENTI**: non entrano nel preventivo (bloccate a DB, D9).

Poi **evade** il preventivo solo se non resta residuo merce (gate EVASO, D6).

## Contesto

- File: `apps/vendite/handlers/push_preventivo_handler.py`.
- Registrato in `HANDLER_MAP` da `apps/vendite/apps.py:ready()` via
  `register_handler("vendita.push_preventivo", PushPreventivoHandler)` (import
  lazy per evitare la dipendenza `pratiche→vendite`).
- Invocato da `pratiche_service.avvia_flusso` → `dispatch_handler` quando il
  flusso `CONFERMA` (template con `handler_id`) passa a `IN_CORSO`.
- **Non reimplementa** i push: delega ai due rami esistenti —
  `pr_run_commesse_push_one` (servizi→commessa) e `fn_push_preventivo_a_ordine`
  (merce→ordine, via `PreventiviRepository.push_a_ordine`) — regola del 2.

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
2. risolve il preventivo dal **ROOT** della pratica (`pratiche_sorgenti`), verifica
   `ACCETTATO` → `E_VENDITA_PREVENTIVO_NON_ACCETTATO` (è anche l'**ancora di
   idempotenza**: a CONFERMA completata il preventivo è `EVASO` terminale → un
   ri-fire ricade qui);
3. **discovery per natura** (fn DB natura-aware): `preventivo_ha_residuo_ordine`
   (merce da smistare) + `count_righe_pushable` (servizi eleggibili, lista
   natura-aware = solo `COMMESSA`);
4. **guard idempotenza natura-completo**: se non resta **nulla** da smistare,
   distingue "già smistato" (esistono ordine/commessa pregressi →
   `E_VENDITA_PREVENTIVO_GIA_PUSHATO`) da "preventivo vuoto" (`E_PREV_NESSUNA_RIGA`);
5. **ramo MERCE** (se residuo): `push_a_ordine(preventivo_id, pratica_id)` →
   `fn_push_preventivo_a_ordine`. La fn DB copia solo le righe `ORDINE_VENDITA` (con la
   `data_consegna_richiesta_cliente` della riga; la confermata nasce `NULL`),
   scrive il link di riga e aggancia `pratiche_sorgenti` (preventivo `ROOT` +
   ordine `COLLEGATO`);
6. **ramo SERVIZI** (se `righe_commessa>0`): qui vive la **c7-2** — risolve la
   policy (`IMMEDIATA` → `true` + mese corrente; `DIFFERITA` → `false` +
   `meta.competenza_fatturazione`, `E_VENDITA_COMPETENZA_RICHIESTA` se assente,
   **richiesta solo se il ramo scatta**), scrive `fatturazione_immediata`+
   `competenza_mese` sul preventivo, poi
   `pr_run_commesse_push_one(sorgente_codice='PREVENTIVO')` →
   il ponte `fn_rendi_commessa_emittibile` (approva le righe di quell'invio e porta la
   commessa allo stato emittibile con la proiezione `fn_commessa_proietta_stato_emittibile`,
   non col verbo del passaggio manuale: C-2 di brief-modello-documento-vendita §14)
   → aggancio `pratiche_sorgenti` (preventivo `ROOT` + commessa `COLLEGATO`);
7. **gate EVASO (D6)**: preventivo → `EVASO` **solo se** `preventivo_ha_residuo_ordine`
   è falso (transizione esplicita, senza swallow);
8. giornale (`fn_log_evento_dominio`, `origine='HANDLER'`): un evento per artefatto
   prodotto — `DOMINIO_ORDINE_CREATO` / `DOMINIO_COMMESSA_CREATA` /
   `DOMINIO_PREVENTIVO_EVASO`.

Output: `{preventivo_id, ordine_id, commessa_id, modalita_fatturazione,
competenza_mese, evaso}` (`ordine_id`/`commessa_id` null quando il relativo ramo
non scatta).

## Idempotenza e concorrenza

- **Ancora vera**: la transizione terminale `ACCETTATO → EVASO` (un ri-fire cade
  sul guard `ACCETTATO` allo step 2) + l'**idempotenza di riga** a DB (ordine via
  `UNIQUE ordini_righe.preventivo_riga_id` → righe già allocate saltate, D5;
  commessa via `segment_key`). Un **dispatch parziale precedente è legittimo** (D5):
  i rami completano solo il residuo;
- `avvia_flusso` aggiorna lo stato del flusso (lock di riga) → due avvii
  concorrenti sullo stesso flusso si serializzano;
- difesa runtime: il check "preventivo `ACCETTATO`" protegge anche se i
  prerequisiti del flusso (guard BEFORE INSERT) fossero cambiati dopo la creazione.

## Note di modello

- **Split per natura attivo** (sostituisce la v1 "commessa diretta fissa"): la
  destinazione è derivata da `config.nature_vendita.destinazione_tipo`, congelata
  sulla riga. Le righe ricorrenti sono bloccate **all'inserimento** (D9,
  `E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA`), non entrano nel preventivo.
- L'ordine generato resta **DRAFT**: ha un ciclo proprio (ordine→DDT→fattura),
  confermato separatamente. Solo la **commessa** va a `PRONTA_FATTURAZIONE`.
- Commessa multi-sorgente (brief
  [brief-db-commesse-multi-sorgente.md](../../../dev/work-done/brief-db-commesse-multi-sorgente.md)):
  una commessa già pronta, portata da un'altra sorgente, il ponte non la ritenta.

## Dipendenze DB

- ramo merce: `vendite.fn_push_preventivo_a_ordine`,
  `vendite.fn_preventivo_ha_residuo_ordine`
- ramo servizi: `pr_run_commesse_push_one` → `fn_get_or_create_commessa` /
  `fn_upsert_commessa_attivita`; `vendite.fn_list_preventivi_da_pushare`
  (natura-aware); `vendite.fn_rendi_commessa_emittibile` (con
  `vendite.fn_commessa_proietta_stato_emittibile`)
- comune: `pratiche.fn_log_evento_dominio`, `vendite.fn_cambia_stato_preventivo`
