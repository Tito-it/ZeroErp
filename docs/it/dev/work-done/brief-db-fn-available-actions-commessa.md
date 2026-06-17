# Brief DB — `fn_available_actions_commessa` + seed transizioni manuali

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> **Priorità**: 🟢 BASSA — governance ciclo di vita commessa (azioni di stato utente).
> **Data**: 2026-06-16 · **Stato**: ✅ **FATTO END-TO-END (2026-06-16)** — DB + BE.
>
> **DB** (pushato su `dev/db-tid`): `script.fn_available_actions_commessa`
> (mirror di `fn_available_actions_ordine`, ritorna `available_actions`/`can_change_state`/
> `can_edit_righe`/`is_emittibile`/`stato_codice`) + seed `meta.manuale=true` con UI hints
> completi (`action_key`/`label_key`/`severity`/`icon`/`requires_confirm`/`outlined`) su
> chiudi(4→5)/riapri(4→3)/annulla(da 1/2/3/4→6). Conforme al brief (+ arricchimento UI meta).
>
> **BE** (su `dev/backend-tid`): `CommesseRepository.get_capabilities`, `capabilities` in
> `ApiCommessaStato` GET, servizio `cambia_stato_commessa` (difesa applicativa: azione ∈
> `available_actions`), endpoint `POST /api/v1/vendite/commesse/<id>/stato/`, codice
> `E_COMMESSA_AZIONE_NON_AMMESSA` (409); 5 test, suite 958 verde. Vedi
> [api_commessa_stato.md](/backend/vendite/manual/api_commessa_stato).
>
> **Origine**: roadmap [analisi-commesse-stato-e-sviluppi.md](analisi-commesse-stato-e-sviluppi.md)
> §4.3 #4 / §8 #7. Oggi il ciclo di vita post-`PRONTA_FATTURAZIONE` non è governabile da
> interfaccia: la macchina a stati esiste ma **nessuna azione utente** è esposta e manca
> la funzione capability. Il **consumer BE attende questo brief** (vedi §5).

---

## 1. Contesto (cosa esiste già)

- Stato testata nella sola FK `stato_commessa_id` → `vendite.stati_commessa`
  (`BOZZA(1)→APERTA(2)→IN_ESECUZIONE(3)→PRONTA_FATTURAZIONE(4)→CHIUSA(5)`, `ANNULLATA(6)`),
  con flag governance `modificabile`/`emittibile`/`chiude_commessa`.
- Matrice [`vendite.transizioni_stati_commessa`](/dbzero/vendite/tabelle/transizioni_stati_commessa)
  (11 righe) + trigger `trgfn_commesse_guard_transizione` (valida la coppia, errore
  `E_COMMESSA_STATO_TRANSIZIONE_INVALIDA` 472; precondizione `→PRONTA` →
  `E_COMMESSA_NESSUNA_RIGA_APPROVATA` 473).
- Entrypoint `fn_cambia_stato_commessa(p_commessa_id, p_nuovo_stato, p_user)` (esiste):
  risolve codice→id, fa l'UPDATE, delega la validazione al trigger.
- **Pattern di riferimento** già implementato per gli altri documenti:
  `script.fn_available_actions_ordine` / `_offerta` / `_contratto` / `_preventivo`.

## 2. Problema

1. **Manca `script.fn_available_actions_commessa`**: il detail/stato API non può sapere
   *quali* azioni di stato siano ammesse per una commessa (per pilotare i pulsanti UI e i
   guard BE), a differenza di ordini/offerte/contratti/preventivi.
2. **Nessuna transizione marcata utente**: in `transizioni_stati_commessa` **tutte** le 11
   righe hanno `meta.manuale=false` (tutte automatiche, ponte push/emittibilità). Il guard
   non filtra su `manuale` (valida solo l'ammissibilità della coppia), quindi `manuale` è
   il discriminante naturale per decidere **cosa offrire all'utente** — ma oggi non offre
   nulla.

## 3. Cosa serve

### 3.1 Nuova funzione `script.fn_available_actions_commessa(p_commessa_id bigint) RETURNS jsonb`

Mirror del pattern `fn_available_actions_ordine` (stessa forma di ritorno, per coerenza
del consumer BE/FE):

- `available_actions`: array delle transizioni di stato **utente** ammesse dalla commessa
  corrente — derivate da `transizioni_stati_commessa` dove `stato_da_id = stato corrente`,
  `attivo`, **`meta.manuale = true`**; ogni voce con una `action_key` parlante (es.
  `chiudi` per →CHIUSA, `riapri` per PRONTA→IN_ESECUZIONE, `annulla` per →ANNULLATA) + lo
  `stato_a` codice;
- `can_change_state`: bool (≥1 transizione manuale ammessa);
- `can_edit_righe`: `stati_commessa.modificabile` dello stato corrente;
- (opz.) `can_emit` / `is_emittibile`: `stati_commessa.emittibile` (informativo);
- `reason` / `reason_key` per le azioni **non** ammesse quando utile (es.
  `COMMESSA_NON_PRONTA` per chiudi, `COMMESSA_TERMINALE` per stato 5/6), sullo stile dei
  `*_reason_key` di `fn_available_actions_ordine`;
- `stato_codice`: codice stato corrente.

Schema `script`, `SECURITY`/grant allineati alle sorelle `fn_available_actions_*`.

### 3.2 Seed `meta.manuale=true` sulle transizioni utente

Marcare come **manuali** (azione utente) le sole transizioni di governance del ciclo di
vita; lasciare automatiche (`manuale=false`) quelle del ponte push/emittibilità.
**Proposta** (da confermare lato modello):

| Transizione | id riga | manuale proposto | Razionale |
|---|---|---|---|
| PRONTA(4) → CHIUSA(5) | 10 | **true** | chiusura manuale commessa |
| PRONTA(4) → IN_ESECUZIONE(3) | 9 | **true** | riapertura (rimette in lavorazione) |
| BOZZA(1) → ANNULLATA(6) | 3 | **true** | annullo manuale |
| APERTA(2) → ANNULLATA(6) | 6 | **true** | annullo manuale |
| IN_ESECUZIONE(3) → ANNULLATA(6) | 8 | **true** | annullo manuale |
| PRONTA(4) → ANNULLATA(6) | 11 | **true** | annullo manuale |
| tutte le altre (→APERTA, →IN_ESECUZIONE da 2, →PRONTA) | 1,2,4,5,7 | false (invariato) | ponte automatico push/emittibilità |

> Da concordare: se l'annullo debba essere ammesso da **tutti** gli stati non terminali
> (come sopra) o ristretto; e se la riapertura PRONTA→IN_ESECUZIONE sia l'unico percorso
> di "sblocco". La matrice è data-driven: modificare i flag non tocca il guard.

## 4. Criterio di accettazione

- `SELECT script.fn_available_actions_commessa(<id>)` ritorna il jsonb con `available_actions`
  coerenti con la matrice (solo transizioni `manuale=true` dallo stato corrente),
  `can_change_state`, `can_edit_righe`, `stato_codice`.
- Commessa in `CHIUSA`/`ANNULLATA` (terminali) → `available_actions=[]`,
  `can_change_state=false`.
- `fn_cambia_stato_commessa` continua a validare via trigger (nessuna regressione).
- pgTAP: test su capability per stato + sul fatto che le transizioni automatiche NON
  compaiono tra le azioni utente.

## 5. Lato BE (a valle del DB — NON in questo brief)

Quando la fn esiste, il backend (separato, su `dev/backend-tid`):

- aggiunge `CommesseRepository.get_available_actions` (wrapper `call_jsonb_fn(
  "script.fn_available_actions_commessa", commessa_id)`) e arricchisce `fn_get_commessa_stato`
  / `ApiCommessaStato` con le capability (come per ordini);
- espone l'azione di stato utente `POST /api/v1/vendite/commesse/<id>/stato/`
  (`handle_post_json`, idempotency-key) → `commesse_service.cambia_stato_commessa` →
  `fn_cambia_stato_commessa`; il service rifiuta azioni non in `available_actions`
  (difesa applicativa oltre al guard DB).

Questi passi BE **attendono** l'applicazione del presente brief
([feedback BE attende prerequisiti DB]).
