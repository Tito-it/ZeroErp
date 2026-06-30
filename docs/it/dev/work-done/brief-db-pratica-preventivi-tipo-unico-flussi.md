# Brief DB — Pratica preventivi: tipo unico + nuova sequenza flussi + following revisione

> **Tipo**: brief DB (cosa serve, non come) · **Destinatario**: team DB (`dev/db-tid`)
> **Priorità**: 🟡 media · **Data**: 2026-06-29 · **Stato**: 🟢 **DB APPLICATO (2026-06-30)** —
> catalogo tipo unico `PREVENTIVI` (CSV runOnChange) + ritiro 9002/9003 via `obsoleto_dal`
> (`20260630-01/02`, vedi [brief-db-deprecabilita-catalogo-vs-istanze.md](brief-db-deprecabilita-catalogo-vs-istanze.md)); pgTAP `obsoleto_dal` **verde**. Resta BE (handler ramo merce, push commessa, filtro selezione). Vedi "Piano esecutivo".
>
> **Sorgente**: brief "Pratica preventivi: tipo unico + flussi conferma ordine + revisione"
> + analisi `analisi-uniformita-pratica-preventivi.md` (il *perché*).
> **Precedente già implementato**: [brief-db-pratica-preventivi.md](../work-done/brief-db-pratica-preventivi.md)
> (2 tipi 9002/9003, catena 4 flussi, motore prerequisiti esito-aware).
>
> Questo brief **riscrive** quel catalogo: tipo unico + sequenza a 6 flussi.

---

## 0. Principio guida (non negoziabile): direzione degli anelli

`pratiche` è **Anello 2 (motore generico)**: sa di "flussi / esiti / prerequisiti",
**non** sa cosa sia un preventivo, un ordine o la "merce". `vendite` (Anello 3) **usa**
`pratiche`; mai il contrario. Due dei tre obiettivi, se messi nel DB di `pratiche`,
forzerebbero `pratiche` a leggere `vendite` → **inversione vietata**. La regola sotto
sposta quella conoscenza dove deve stare (l'handler/layer `vendite`).

---

## 0bis. Verifica del modello (riscontri reali)

| Aspetto | Riscontro | Impatto |
|---|---|---|
| `tipi_prestazione` 9002/9003 | FK reale da `pratiche.tipo_prestazione_id` e `template_flussi.tipo_prestazione_id`; UNIQUE `(tipo, codice)` | Tipo unico = re-seed catalogo |
| Differenza 9002 vs 9003 | **solo** `handler_params.modalita_fatturazione` sul CONFERMA | Tolto il cablato, i due tipi sono identici |
| Prerequisiti esito-aware | ✅ già nel motore: `template_flussi_prerequisiti.esito_richiesto` + `fn_check_prerequisiti_flusso` (esiti: POSITIVO/NEGATIVO/PARZIALE/NON_APPLICABILE) | Catena lineare esito-aware = solo seed |
| `azioni_ui` | colonna `template_flussi.azione_ui_id` (FK) + registry FE; la join-table `template_flussi_azione_ui` è **stantia** | Seedare sulla **colonna**, non sulla join |
| Revisione preventivo | `fn_crea_revisione_preventivo` fa **INSERT** nuova riga: `id` e `uid` **nuovi**, `numero` **stabile** (immutabile, lock_columns), UNIQUE `(numero, rev)` | `uid` invecchia; `numero` è la chiave stabile |
| `is_attiva` | **derivata** in `vw_preventivi` (colonna droppata 2026-05-15), dipende da `stati_doc_preventivi.is_abortito` | Risoluzione rev attiva = competenza **vendite** |
| `pratiche_sorgenti` | `sorgente_uid` text = oggi l'`uid` per-revisione; `flusso_id` (ROOT per-flusso) + guard coerenza; **non immutabile** ma con UNIQUE | Cambiare *cosa* memorizza e *chi* risolve |
| Creazione flussi | ✅ **on-demand, per singolo flusso** (`pratiche_service.crea_flusso(template_flusso_id)`); **nessun** bulk alla nascita pratica; `trgfn_flussi_generazione` è solo generazione cross-pratica event-driven | 50/60 creabili solo quando servono, niente step-fantasma |
| Dati | **solo test, nessuna produzione** | Migrazione catalogo = re-seed/wipe, no conservazione storica |

---

## Obiettivo 1 — Tipo unico `PREVENTIVI` (re-seed, niente migrazione conservativa)

È la **conseguenza** dell'Obj 2: tolto `modalita_fatturazione` dal CONFERMA, i due tipi
diventano duplicati → si collassano in uno.

**Cosa serve**:
- **nuovo** tipo `PREVENTIVI` unico (decisione 2026-06-29: nuovo `codice_interno`, non ridenomina), risolto per `codice_interno`;
- **dati solo test** → si **ri-seeda pulito**: niente logica di deprecazione per
  preservare la storia (non c'è storia da preservare). Le pratiche di test sui vecchi
  tipi si possono cancellare/ricreare.

**⚠️ Scoperta in apply (2026-06-30): la disattivazione di un tipo NON è seed-abile.** Il
guard `dbops.trgfn_prevent_deactivate_if_children` blocca `UPDATE attivo=false` su
`tipi_prestazione` se esistono **figli attivi** in 5 tabelle (`email_template`,
`formule_tempo`, **`pratiche`**, `regole_generazione`, **`template_flussi`**); e
`template_flussi` è a sua volta guardato da `flussi` (le **istanze**), canali, ecc. Più,
l'**ordine dei loader** (tipi prima di template) impedisce di disattivare in-CSV. → La
deprecazione via `attivo=false` su test data con istanze attive **non passa**.

**Approccio adottato → seed ADDITIVO.** Il seed aggiunge solo il nuovo tipo `PREVENTIVI`
(9004) e il suo catalogo; **9002/9003 restano `attivo=t`** (nessuna disattivazione nel seed).
Il `loadUpdateData` è upsert: non cancella, quindi su DB fresco il catalogo è completo e su
`dbdev` esistente si aggiunge senza rompere.

**Ritiro dei vecchi tipi 9002/9003 — RISOLTO via `obsoleto_dal`** (2026-06-30, decisione P1 in
[brief-db-deprecabilita-catalogo-vs-istanze.md](brief-db-deprecabilita-catalogo-vs-istanze.md)):
non si disattiva (`attivo=false` romperebbe le pratiche esistenti ed è bloccato dal guard); si
marcano **obsoleti** con la nuova colonna `obsoleto_dal = oggi` (`20260630-01` aggiunge la
colonna a `tipi_prestazione`/`template_flussi`; `20260630-02` ritira 9002/9003 + i loro
template per `codice_interno`). `attivo` resta true → storia intatta, guard mai sfiorato.
La selezione-per-il-nuovo (BE) filtrerà `attivo AND (obsoleto_dal IS NULL OR obsoleto_dal >
CURRENT_DATE)` → i vecchi tipi non sono più offerti, il nuovo `PREVENTIVI` (9004) sì.

**Criterio di accettazione** (rivisto): esiste il tipo `PREVENTIVI` (9004) attivo col nuovo
catalogo (6 flussi); una pratica `PREVENTIVI` nuova si apre senza errori. Il ritiro di
9002/9003 (non più selezionabili) è un **passo di cleanup separato** (manuale o rebuild),
non un criterio del seed.

---

## Obiettivo 2 — Nuova sequenza a 6 flussi (DB) + ramo merce (handler vendite, NON DB)

Sequenza: `10 RICHIESTA_CLIENTE → 20 PREVENTIVAZIONE → 30 APPROVAZIONE_CLIENTE →
40 SMISTAMENTO → 50 CONFERMA_ORDINE → 60 INVIO_COMMESSA`.

**Cosa serve a DB (esprimibile subito, solo seed)**:
- seed dei 6 `template_flussi` del tipo unico, con **prerequisiti esito-aware lineari**
  (`esito_richiesto='POSITIVO'`) fino al 40; **50 e 60** con prerequisito **"SMISTAMENTO
  completato POSITIVO"**;
- 3 nuove righe `azioni_ui` (SMISTAMENTO, CONFERMA_ORDINE, INVIO_COMMESSA) agganciate via
  **colonna** `template_flussi.azione_ui_id` (come l'esistente APRI_PREVENTIVO su PREVENTIVAZIONE);
- **togliere** `handler_params.modalita_fatturazione` dal flusso di conferma (la modalità si
  sceglie all'accettazione e vive sul preventivo — fuori scope DB).

**Il "ramo merce" (50/60 solo se c'è ordine merce) NON è un prerequisito DB**: sapere "il
preventivo ha merce" significherebbe leggere `vendite.preventivi_righe` → inversione di anello.
Va gestito come **istanziazione condizionale dell'handler `vendite`**:
- i 6 flussi sono un **catalogo**; le istanze si creano **su richiesta**, non tutte alla nascita;
- l'handler SMISTAMENTO (vendite, che già fa lo split merce→ordine / servizi→commessa)
  **crea le istanze 50/60 solo quando ha generato un ordine merce**; se è tutto servizi,
  non le crea → non compaiono;
- il motore resta generico: mostra i flussi esistenti, con il prerequisito "50 richiede
  SMISTAMENTO POSITIVO".

**Prerequisito di design — ✅ CONFERMATO (2026-06-29)**: i flussi nascono **on-demand, uno
per uno** (`pratiche_service.crea_flusso(template_flusso_id)`); il motore **non auto-istanzia**
i template del tipo alla creazione pratica. Quindi 50/60 si creano solo quando l'handler li
crea → nessuno step piantato/incompletabile. Meccanica 50/60 quindi pienamente sostenibile.

**Criterio di accettazione**: una pratica `PREVENTIVI` espone i 6 step nell'ordine, con i
prerequisiti esito-aware; 50/60 **compaiono solo** quando lo SMISTAMENTO ha prodotto un
ordine merce; le azioni UI 40/50/60 aprono i rispettivi pannelli.

---

## Obiettivo 3 — Following revisione attiva (link per `numero`, risoluzione in `vendite`)

**Verificato**: `id`/`uid` cambiano a ogni revisione; `numero` è stabile e immutabile;
`is_attiva` è derivata in `vw_preventivi`. Far "inseguire" la rev attiva da `pratiche`
(vista/trigger lato pratiche) significherebbe leggere `vendite` → inversione.

**Cosa serve** (decisione 2026-06-29 — convenzione in `meta`, non nuova colonna):
- il legame ROOT memorizza l'identità **stabile** (`numero`) e un flag "segui la versione viva"
  in `pratiche_sorgenti.meta`, con questa **convenzione generica** (riusabile da altri domini):

  ```json
  {
    "ref_stable_key": "PREV-100",   // identità stabile (numero), non l'uid di revisione
    "follow_active": true            // true = segui la rev attiva; assente/false = pin alla rev agganciata
  }
  ```

  Il "kind" non si ripete in `meta`: lo dà già `sorgente_tipo_id` (PREVENTIVO/…).
  `sorgente_uid` resta l'uid dell'**entry-point** (revisione al momento dell'aggancio) → tracciabilità;
- "qual è la rev attiva di quel `numero`" la risolve **`vendite`** (proprietario di
  `vw_preventivi.is_attiva`), che può legittimamente leggere il link di pratiche;
- il link **resta fermo** (nessun UPDATE, nessun trigger): la risoluzione è a **read-time**.

**Perché `meta` e non una colonna**: è una convenzione cross-dominio **emergente** (1 solo caso
oggi) → JSONB finché la forma non è provata su ≥2 consumatori ([feedback_jsonb_vs_vocab_table_handler_params]);
niente ALTER su una forma vista una volta sola; `pratiche` resta generico (memorizza `meta`
opaco, interpreta `vendite`).

**Regalo gratis**: all'annullamento di una revisione, `is_attiva` torna da sola al
predecessore → il criterio "torna al predecessore" è soddisfatto **senza scrivere nulla**.

**Impatto DB**: lato `pratiche` **nessuna nuova struttura** (solo uso di `meta`). Eventuale
helper di risoluzione `numero`→rev attiva sta in schema **`vendite`**, non in `pratiche`.

### Generalizzazione (rinviata al 2° consumatore — manifesto §7)

La convenzione `meta` sopra è deliberatamente **generica** ("link parametrico a un'entità di
dominio versionata, usata dentro una pratica"): quando un 2° caso reale comparirà (es.
revisione di contratto/offerta dentro una pratica) **si incastra senza modifiche di schema**.
**Non** si costruisce ora un framework/registro generico né un dispatcher di risoluzione: si
astrae **dopo** il 2° consumatore (modello virtuoso `dbops.automazione_chiusura_scadenze`, non
l'errore di astrazione precoce di `pratiche`). Oggi la "genericità" è solo: (a) le chiavi
`meta` documentate qui + (b) la regola "la risoluzione della versione viva la fa il dominio
proprietario".

**Criterio di accettazione**: creata una revisione di un preventivo agganciato a una pratica,
"il preventivo della pratica" mostra la **nuova rev attiva**; annullata la revisione, mostra
di nuovo il predecessore — senza alcun aggiornamento del link.

---

## Riepilogo deliverable DB (solo ciò che è davvero DB-pratiche)

| ID | Oggetto | Tipo |
|---|---|---|
| D1 | Tipo unico `PREVENTIVI` (re-seed) + cleanup one-shot vecchi 9002/9003 | seed + cleanup |
| D2 | Seed 6 `template_flussi` + prerequisiti esito-aware (50/60 ← SMISTAMENTO POSITIVO) | seed |
| D3 | 3 `azioni_ui` (SMISTAMENTO/CONFERMA_ORDINE/INVIO_COMMESSA) via colonna `azione_ui_id` | seed |
| D4 | Rimozione `handler_params.modalita_fatturazione` dal CONFERMA | seed |
| D5 | ✅ **RISOLTO**: istanziazione flussi on-demand confermata (`crea_flusso` per singolo) — nessun lavoro | — |
| D6 | (eventuale) helper risoluzione numero→rev attiva **in schema `vendite`** | fn (vendite) |

> **Non DB-pratiche**: ramo merce (istanziazione handler vendite), following rev (risoluzione
> read-time vendite), scelta modalità all'accettazione (BE/FE). Vedi sotto.

## Piano esecutivo — IMPLEMENTATO a seed (2026-06-30)

**Modalità**: solo **edit dei CSV** già caricati da loader `loadUpdateData` **runOnChange**
(upsert per `id`) — **nessun nuovo changeset, nessun DDL**. Applicazione = prossimo `migrate`.

**Allocazione id** (blocco 9000 pratiche): tipo **9004**; `template_flussi` **9009–9014**;
prerequisiti **9007–9011**; `azioni_ui` **9002–9004**; satelliti `esito_config` /
`azione_ui` keyed per id template.

**Catalogo del tipo unico `PREVENTIVI` (9004)**:

| id | codice | seq | dir | obblig | esito | azione_ui | handler_id | prereq (POSITIVO) |
|---|---|---|---|---|---|---|---|---|
| 9009 | RICHIESTA_CLIENTE | 10 | ENTRATA | t | CONTESTUALE/POSITIVO | — | — | — |
| 9010 | PREVENTIVAZIONE | 20 | INTERNA | t | MANUALE | APRI_PREVENTIVO | — | ← 9009 |
| 9011 | APPROVAZIONE_CLIENTE | 30 | ENTRATA | t | CONTESTUALE/POSITIVO | — | — | ← 9010 |
| 9012 | SMISTAMENTO | 40 | INTERNA | t | MANUALE | SMISTAMENTO | — | ← 9011 |
| 9013 | CONFERMA_ORDINE | 50 | INTERNA | **f** | MANUALE | CONFERMA_ORDINE | — | ← 9012 |
| 9014 | INVIO_COMMESSA | 60 | INTERNA | **f** | MANUALE | INVIO_COMMESSA | — | ← 9012 |

Satelliti del catalogo (analoghi all'esistente): **canali** `WEB_CLIENTI` sui flussi ENTRATA
9009/9011; **event-handler** su 9011 (APPROVAZIONE) `COMPLETATO/POSITIVO → vendita.accetta_preventivo`
(handler 9002), come i vecchi 9003/9007.

Note di seed:
- **50/60 `obbligatorio=f`**: sono condizionali al ramo merce (una pratica tutto-servizi non
  li avrà — creati on-demand dall'handler); se fossero obbligatori bloccherebbero la chiusura.
- **`handler_id` vuoto** sui 6 template (come gli step non-CONFERMA esistenti). L'accettazione
  è wirata via **event-handler** (9011); il **push a commessa** (vecchio `vendita.push_preventivo`
  sul CONFERMA, qui rimosso) va ricollocato dal **BE** su INVIO_COMMESSA con contratto nuovo
  (modalità dal preventivo, non da `handler_params`). Nessun `modalita_fatturazione` cablato (D4).
- **Seed ADDITIVO**: 9002/9003 **restano attivi** (la disattivazione è bloccata dal guard
  `prevent_deactivate_if_children`, vedi Obiettivo 1). Il loro ritiro è cleanup manuale/rebuild,
  fuori dal seed.

**File toccati** (tutti `80_data/sql/pratiche/`): `tipi_prestazione.csv`, `template_flussi.csv`,
`template_flussi_prerequisiti.csv`, `template_flussi_esito_config.csv`, `azioni_ui.csv`,
`template_flussi_azione_ui.csv`, `template_flussi_canali.csv`, `template_flussi_handler_eventi.csv`.

**Resta a Tid (DB)**: `migrate` su `dev/db-tid` (ora additivo → passa) + verifica (una pratica
`PREVENTIVI`/9004 espone i 6 step coi prerequisiti). Ritiro di 9002/9003 = cleanup manuale o
rebuild quando comodo (test data). Eventuale pgTAP sul catalogo.

**Resta al BE** (vedi Fuori scope): handler SMISTAMENTO che crea 50/60 solo con ordine merce;
push a commessa su INVIO_COMMESSA (contratto modalità-da-preventivo); registrazione chiavi
azioni UI nel registry FE.

## Fuori scope (BE/FE)

- Handler SMISTAMENTO che crea 50/60 solo con ordine merce (BE vendite).
- Risoluzione "preventivo della pratica" per `numero`+`is_attiva` (BE vendite).
- Dialog accettazione con modalità+competenza sul preventivo (BE/FE, riusa path standalone).
- Registrazione chiavi azioni UI nel registry FE.

## Decisioni prese — nessuna domanda aperta bloccante

- **Obj 1** → tipo unico = **nuovo** `codice_interno` (2026-06-29).
- **Obj 3** → identità stabile + follow in **`pratiche_sorgenti.meta`** (convenzione
  `ref_stable_key` / `follow_active`), **non** nuova colonna (2026-06-29). Risoluzione rev
  attiva lato `vendite`.
- **D5** → flussi on-demand confermato (`pratiche_service.crea_flusso` per singolo template;
  nessun bulk alla nascita pratica). Meccanica 50/60 sostenibile.
- **Generalizzazione** → forma `meta` generica ora, framework rinviato al 2° consumatore.

Tutto verificato contro il codice: il brief è pronto per il piano esecutivo DB.
