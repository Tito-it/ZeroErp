# Brief BE → DB — azioni disponibili del lotto di fatturazione (`fn_available_actions_lotto`)

> 🟢 **CHIUSO — 2026-08-04.** DB applicato e verde (risposta: §1 di
> [risposta-db-azioni-lista-lotto.md](risposta-db-azioni-lista-lotto.md)); BE/FE
> completati e **validati in-app da Tid** lo stesso giorno.
>
> **Consegnato lato BE/FE:**
>
> * `get_lotto` espone il blob capability (`VenditeRepository.get_available_actions_lotto`
>   → merge nel dettaglio **dopo** il cancello di scope, con fallback graceful se
>   il capability layer si rompe);
> * i 4 codici errore nuovi + `E_LOTTO_NON_TROVATO` registrati in `error_policies.py`
>   come **409**, non 400: chi li vede ha forzato un'azione che l'interfaccia
>   mostrava già disabilitata col motivo;
> * `LottoDrawer.vue` passa a `DrawerActionsBar` + `mapAvailableActionsToDrawerActions`:
>   **le cinque `computed` di stato sono sparite**, incluso il `!isDraft` che su un
>   lotto DEFINITIVA mostrava un pulsante destinato a fallire;
> * `LottiListView.vue` monta il kebab con i cinque verbi;
> * `useLottoAzioni` — conferme, chiamate, toast e permessi in **una sola sede**,
>   estratto alla seconda occorrenza (regola del 2, ok Tid).
>
> **Due scostamenti dal brief, entrambi motivati dal DB e accettati:**
>
> 1. **Niente capability per riga di lista** (§4.3 → §3.3 della risposta). Il kebab
>    propone i verbi plausibili per lo stato della riga e, **al click**, legge la
>    capability di quel lotto: se il DB dice no, l'operatore legge il motivo invece
>    di veder fallire l'azione. Una chiamata sola, pagata solo quando si agisce.
> 2. **`avanza_step` / `rilancia_step` restano gate del frontend** (§5 della
>    risposta): il loro verdetto vive nel runner Python e farne scendere metà
>    creerebbe la seconda copia della regola che questo lavoro elimina.
>
> **Correzione a quanto scritto qui sotto:** il ⚠️ del §3 su
> `fn_riporta_lotto_a_draft` («non risulta in migrations/pgtap/doc») **era
> sbagliato** — la funzione esiste dal 2026-08-03 (`20260803-08/-09/-12`). Il
> `grep` era stato fatto su un albero locale indietro di due merge DB. Il verbo
> esce quindi dalle capability **abilitato**. Il §6.1 della risposta ha ragione su
> tutti e tre i punti.
>
> **Un caso emerso dai dati reali**, non dal brief: con la regola storica «Avanza
> step» sarebbe comparso anche sui lotti DEFINITIVA — invisibile nel drawer di un
> lotto alla volta, evidente in una lista dove i chiusi sono la maggioranza. Ora
> l'avanzamento si propone solo da DRAFT.
>
> Il testo che segue è il brief originale, lasciato integro come richiesta in
> ingresso.
>
> ---

**Chi scrive:** BE/FE (`dev/backend-tid`), 2026-08-04.
**A chi:** team DB (`dev/db-tid`).
**Cos'è:** portare le azioni di governo del lotto **anche nella lista lotti**
(kebab di riga), oltre che nel drawer, con la regola «abilitate solo quando
sono davvero possibili». Per farlo chiediamo la stessa cosa che gli altri
**sette** domini hanno già: una funzione capability che dica, per un lotto,
**quali verbi sono disponibili e quali no, con il motivo**.
**Decisione presa da Tid** (2026-08-04): **sorgente unica a DB**, non gate
ricalcolati nel frontend. E le cinque azioni vanno **tutte** in lista, con
conferma — inclusi i distruttivi. (Cinque azioni = sei voci di capability:
«avanza» e «rilancia» condividono l'endpoint ma non le precondizioni.)
**Correlati:**
[fn_available_actions_commessa](/dbzero/script/funzioni/fn_available_actions_commessa) ·
[fn_available_actions_ddt](/dbzero/script/funzioni/fn_available_actions_ddt) ·
[stati_doc_fiscale_transizioni](/dbzero/config/tabelle/stati_doc_fiscale_transizioni) ·
[fn_annulla_lotto_da_draft](/dbzero/vendite/funzioni/fn_annulla_lotto_da_draft) ·
[fn_get_lotto_segnalazioni_summary](/dbzero/vendite/funzioni/fn_get_lotto_segnalazioni_summary) ·
[piano-db-ritorno-lotto-a-draft](piano-db-ritorno-lotto-a-draft.md)

---

## 1. Perché lo chiediamo (il precedente che vogliamo non ripetere)

Oggi le condizioni dei verbi del lotto vivono **come `computed` nel
frontend**, in [LottoDrawer.vue:107-121](../../../../frontend/src/vendite/components/LottoDrawer.vue#L107-L121):
`isDraft`, `isEmessa`, `isDefinitiva`, `isErrore`, `isInEsecuzione`.

Quel modello si è già rotto una volta: il 2026-07-31 Tid ha trovato in-app il
pulsante «Annulla lotto» **visibile da EMESSA in poi**, dove
`fn_annulla_lotto_da_draft` rifiuta con `E_PARAMETRO_INVALIDO` — un vicolo
cieco. È stato corretto aggiungendo un `v-if` in più, cioè **ricopiando in Vue
una precondizione che vive in PL/pgSQL**.

E c'è già la seconda occorrenza dello stesso difetto, ancora aperta: «Riporta a
bozza» è oggi gated con `!isDraft`, mentre le precondizioni vere (tipo lotto,
stato, nessuna fattura numerata) sono altre — su un lotto DEFINITIVA il
pulsante **c'è e fallisce**.

Duplicare quelle condizioni **anche nella lista** significherebbe tre copie
della stessa verità. Per questo la richiesta è a voi e non un lavoro FE.

---

## 2. Il principio

> **La UI non decide mai se un'azione è possibile: lo chiede al DB e lo rende.**

È esattamente il contratto che avete già scritto per la commessa il 2026-07-24
(`fn_check_commessa_chiudibile` / `_annullabile` usate **sia** dal guard di
transizione **sia** dalle capabilities), e che il `COMMENT` di
`fn_available_actions_commessa` formalizza così:

> «la presenza di un'azione in `available_actions` NON significa più eseguibile
> — i consumatori devono leggere `enabled`».

Chiediamo lo stesso, per il lotto.

---

## 3. I verbi e dove vive oggi la loro verità

| # | Verbo (UI) | Endpoint BE | Azione di processo | Precondizioni vere, oggi | Dove sono scritte |
| --- | --- | --- | --- | --- | --- |
| 1 | **Avanza step** | `POST /vendite/pipeline/run/` | `genera_fatture_lotti` | esiste uno step successivo per (tipo_lotto, utility, tipo_doc); **nessuna criticità attiva** (`blocks_next_step`); nessun job in esecuzione | [pipeline_runner.py:416-462](../../../../backend/apps/vendite/services/pipeline_runner.py#L416-L462) + `fn_get_lotto_segnalazioni_summary` |
| 2 | **Rilancia step (rerun)** | stesso endpoint | `genera_fatture_lotti` | **ammesso anche con criticità attive** (D-Q p.1: è la via d'uscita), purché sia il *rilancio dello stesso step* | idem, `is_rilancio_stesso_step` |
| 3 | **Rendi definitive** | `POST /vendite/fatturazione/lotti/<id>/numera/` | `numera_fatture_lotti` | lotto in **EMESSA** (gate fiscale I-7) | [pipeline_service.py:253-282](../../../../backend/apps/vendite/services/pipeline_service.py#L253-L282) |
| 4 | **Ristampa documenti** | `POST /vendite/fatturazione/lotti/<id>/ristampa/` | nessuna (stampa = lettura, I-4) | lotto in **DEFINITIVA** | [pipeline_service.py:284-300](../../../../backend/apps/vendite/services/pipeline_service.py#L284-L300) |
| 5 | **Annulla lotto** | `POST /vendite/lotti/<id>/reset-draft/` | `reset_lotto_draft` | stato **DRAFT**; **nessuna fattura oltre il pre-fiscale** (solo DRAFT/EMESSA); MASSIVO **o** GIORNALIERO | [fn_annulla_lotto_da_draft](/dbzero/vendite/funzioni/fn_annulla_lotto_da_draft) |
| 6 | **Riporta a bozza** | `POST /vendite/lotti/<id>/riporta-a-draft/` | `reset_lotto_draft` | 🔴 **da definire con la Fase 6**: matrice EMESSA→DRAFT `solo_lotto`, nessuna fattura numerata, tipo lotto | [piano-db-ritorno-lotto-a-draft](piano-db-ritorno-lotto-a-draft.md) §1, §4.5, punti C/D/F/G |

⚠️ **Segnalazione, non richiesta.** `vendite.fn_riporta_lotto_a_draft` è
chiamata dal BE ([pipeline_repository.py:2166-2171](../../../../backend/apps/vendite/db/pipeline_repository.py#L2166-L2171),
commit `6728e58cb`) ma **non risulta né in `migrations_v2` né in `db/pgtap` né
nella doc auto-generata**: l'endpoint è pronto e in attesa della vostra Fase 6.
Se è ancora così, il verbo #6 va esposto dalle capabilities come
`enabled: false` con motivo — non nascosto: l'operatore deve sapere che
l'uscita esiste e perché non è ancora percorribile.

---

## 4. Cosa chiediamo

### 4.1 — `script.fn_available_actions_lotto(p_lotto_id bigint) RETURNS jsonb`

`STABLE`, `SECURITY INVOKER`, `NULL` se il lotto non esiste (come le sorelle).
Contratto **identico** a `fn_available_actions_commessa`, così i building block
FE già esistenti (`useDrawerActions`, `DrawerActionsBar`, `useEntityCapabilities`)
la consumano senza adattatori:

```jsonc
{
  "available_actions": [
    {
      "key":              "avanza_step",       // action_key stabile, mai la label
      "target_state":     "EMESSA",            // null per i verbi non-transizione
      "label_key":        "vendite.lotti.avanza",
      "severity":         "primary",
      "icon":             "pi pi-forward",
      "requires_confirm": true,
      "outlined":         false,
      "enabled":          false,
      "reasons":          [ { "reason_key": "vendite.lotti.motivo_criticita",
                              "reason": "3 segnalazioni critiche attive" } ]
    }
  ],
  "can_change_state": true,     // solo sulle azioni ABILITATE (come commessa)
  "stato_codice":     "EMESSA", // stato_doc_fiscale.codice_interno del lotto
  "tipo_lotto":       "MASSIVO"
}
```

Le `key` che il FE si aspetta (le stesse dei verbi in §3): `avanza_step`,
`rilancia_step`, `numera`, `ristampa`, `annulla`, `riporta_a_draft`.
Se preferite un vocabolario diverso va bene: ditecelo e ci allineiamo noi —
purché sia **stabile** e viva a catalogo, non nel codice.

**Data-driven dove la matrice c'è già.** `config.stati_doc_fiscale_transizioni`
ha `stato_from_id`, `stato_to_id`, `ammesso`, `solo_lotto`, `meta jsonb`: i
verbi 3/5/6 sono transizioni e possono nascere da lì con `meta` popolato
(`action_key`, `label_key`, `severity`, `icon`, `requires_confirm`), esattamente
come `transizioni_stati_commessa`. I verbi 1/2/4 **non** sono transizioni della
matrice (avanzamento pipeline e ristampa): quelli li dovrete comporre nella
funzione. Se ritenete che vadano anch'essi dichiarati a dato, decidete voi
dove — è la parte su cui vi chiediamo la proposta, non una soluzione nostra.

### 4.2 — Le funzioni pure di check, riusate dai guard

Il valore del modello commessa non è il jsonb: è che `enabled` e il **guard che
solleva** leggono la **stessa** funzione. Chiediamo lo stesso per il lotto:

| Funzione pura (nomi indicativi) | Verdetto su | Chi la usa oltre le capabilities |
| --- | --- | --- |
| `script.fn_check_lotto_annullabile` | stato DRAFT + fatture tutte pre-fiscali | `fn_annulla_lotto_da_draft` (oggi solleva con logica propria) |
| `script.fn_check_lotto_riportabile_a_draft` | precondizioni Fase 6 | `fn_riporta_lotto_a_draft` (in arrivo) |
| `script.fn_check_lotto_numerabile` | stato EMESSA | step DEFINITIVA |
| `script.fn_check_lotto_avanzabile` | step successivo esistente + criticità + job | runner (oggi in Python) |

Ritorno `jsonb` array di motivi, vuoto `[]` = lecito — come
`fn_check_commessa_chiudibile`. **Se una di queste vi sembra ridondante o
scomponibile diversamente, decidete voi:** il vincolo che ci interessa è
*una sola* sede per ogni regola, non il numero di funzioni.

### 4.3 — Consumo per riga di lista

La lista lotti è paginata (default 25, cap 200) e useremo un
`LEFT JOIN LATERAL script.fn_available_actions_lotto(fl.id) ON TRUE` in
[vendite_repository.list_lotti](../../../../backend/apps/vendite/db/vendite_repository.py#L280-L375).
Serve quindi che la funzione sia `STABLE` e **ragionevole su ~200 chiamate**.
Se per voi il costo non regge (le `fn_check_*` toccano `fatture`,
`fatturazione_lotti_fatture`, `fatture_log`), diteci se preferite una variante
set-based `fn_available_actions_lotti(p_lotto_ids bigint[])`: la consumiamo noi
con una seconda query per pagina, nessun problema.

### 4.4 — Seed: riattivare la colonna «Azioni» della lista lotti

`ui.lista_colonna` id **216** (`lista_id = 12` → `vendite.lotti`, codice
`azioni`) ha `attivo = f`
([lista_colonna.csv:217](../../../../db/changelog/migrations_v2/80_data/sql/ui/lista_colonna.csv#L217)):
fu disattivata il 2026-07-31, quando l'unica azione di riga era «apri» ed è
diventata il click sulla riga. `fn_resolve_lista_config` filtra
`lc.attivo = TRUE`, quindi finché resta `f` lo slot `#actions` di
`<ListaConfigurabile>` **non viene proprio renderizzato** e nessun lavoro FE è
visibile.

Chiediamo `attivo = t`. Nient'altro cambia: `larghezza_default = 70`,
`ordine_default = 999`, `priorita = 100`, `esportabile = f` vanno già bene.

---

## 5. Cosa NON chiediamo

* **Nessun nuovo stato, nessuna nuova transizione**: le capabilities *leggono*
  la macchina, non la estendono. Se la Fase 6 aggiunge EMESSA→DRAFT, la funzione
  la espone da sé perché la prende dalla matrice.
* **Nessun permesso a DB**: i codename (`genera_fatture_lotti`,
  `numera_fatture_lotti`, `reset_lotto_draft`) restano gestiti dalla catena
  permessi esistente; il FE nasconde per permesso, il DB disabilita per stato.
  Sono due filtri ortogonali, come per la commessa (`permission` di
  `useDrawerActions` vs `enabled`/`reasons` del BE).
* **Nessuna modifica alle sei fn di mutazione**, se non l'eventuale rifattorizzazione
  interna del §4.2 per farle poggiare sulle `fn_check_*`.

---

## 6. Cosa fa il BE/FE (la nostra metà, a prerequisiti pronti)

1. **BE** — `get_lotto` espone il blob capability sul dettaglio (pattern
   `call_jsonb_fn` già usato da ordini/DDT/resi/commesse); `list_lotti` lo
   espone per riga.
2. **FE drawer** — [LottoDrawer.vue](../../../../frontend/src/vendite/components/LottoDrawer.vue)
   passa da sei `<Button>` con `v-if` fatti a mano a `DrawerActionsBar` +
   `mapAvailableActionsToDrawerActions`: le cinque `computed` di stato
   **spariscono**.
3. **FE lista** — [LottiListView.vue](../../../../frontend/src/vendite/views/LottiListView.vue)
   monta `<template #actions>` con `RowActionsMenu` costruito dallo stesso blob;
   azioni disabilitate con il `reason` a tooltip (decisione Tid sulla commessa:
   disabled + motivo, mai nascosto), conferma forte sui distruttivi.
4. **Test** — unit service sul mapping capability, smoke sui sei verbi.

Nessuno di questi quattro punti parte prima che §4.1 e §4.4 siano su
`Tito-dev` (memoria `feedback_be_fe_attende_prerequisiti_db`).

---

## 7. Definizione di «fatto»

* [x] `script.fn_available_actions_lotto` esiste, documentata in auto-gen, con
      `COMMENT` che dichiara il contratto `enabled` come per la commessa;
* [x] le `fn_check_*` del §4.2 sono la sede unica: le fn di mutazione non
      ricalcolano le stesse condizioni;
* [x] pgTAP: per ciascuno dei sei verbi, un caso «lecito» e un caso «rifiutato»
      che verifica **lo stesso verdetto** tra `fn_check_*` e la fn di mutazione;
* [x] `ui.lista_colonna` id 216 `attivo = t`;
* [x] risposta sul §4.3 (per-riga o set-based) e sul vocabolario delle `key`.

## 8. Domande aperte per voi

1. I verbi non-transizione (avanza/rilancia/ristampa) li volete **a dato**
   (una tabella tipo `vendite.lotto_azioni` con `meta`) o **cablati** nella
   funzione? Noi consumiamo l'uno o l'altro senza differenze.
2. `blocks_next_step` oggi è calcolato in Python
   ([lotto_segnalazioni_service.py:38-54](../../../../backend/apps/vendite/services/lotto_segnalazioni_service.py#L38-L54))
   sommando i conteggi di `fn_get_lotto_segnalazioni_summary`. Se la regola
   scende in `fn_check_lotto_avanzabile`, il runner Python dovrebbe leggere
   quella — così il gate del bottone e il gate dell'esecuzione **sono lo stesso
   codice**. Confermate che è la direzione giusta?
3. La distinzione avanza/rilancio (D-Q p.1: con criticità il rilancio dello
   stesso step resta lecito) la sa oggi solo il runner. La funzione capability
   può ricostruirla da `fatturazione_lotti_task_runs` + `stato_doc_fiscale_id`
   corrente, o preferite che il BE passi un parametro?
