# Brief DB — Azione di completamento del flusso (routing data-driven)

**Area:** `pratiche` · **Tipo:** catalogo + aggancio su template (mirror di `azioni_ui`)
**Branch destinazione:** `dev/db-tid`
**Richiesto da:** backend agent (per conto di Tid) · **Data:** 2026-06-15
**Stato:** 🔲 PROPOSTA, attende esecuzione DB

> Questo brief descrive **cosa** serve dal DB, **non come** (catalogo vs colonna,
> nomi, SQL = scelta del team DB). Le azioni DB non sono eseguite dal backend agent.

---

## 1. Contesto e problema

Alcuni step di flusso, al **completamento con esito**, non fanno solo un cambio
stato generico: innescano un'**azione di dominio in transazione**. Caso reale
oggi: il flusso `APPROVAZIONE_CLIENTE` di una pratica preventivo, completato
`POSITIVO`, deve **anche accettare il preventivo collegato** (M2 — endpoint
`vendite/preventivi/<id>/approvazione-flusso/`).

Oggi questo routing è **hardcoded nel FE** (`FlussoDrawer`: `if tipo_prestazione
inizia con PREVENTIVI && template = APPROVAZIONE_CLIENTE → endpoint M2; else
cambio stato generico`). Quando arriveranno **offerta e contratto** (stessa
forma: uno step di approvazione che accetta il documento collegato), ripetere
l'hardcoding sarebbe il debito che abbiamo appena eliminato per l'**apertura**
del drawer con `azioni_ui`. Serve il **gemello** per il **completamento**.

## 2. Cosa serve dal DB (simmetrico ad `azioni_ui`)

Un template di flusso deve poter **dichiarare** quale azione di completamento di
dominio si applica al suo passaggio a `COMPLETATO`, in modo che BE/FE instradino
il completamento all'endpoint giusto **per dati**, non per `if` sul codice:

1. Un **catalogo** di azioni di completamento (token risolto lato FE, es.
   `ACCETTA_PREVENTIVO`), esattamente come `pratiche.azioni_ui` lo è per
   l'apertura. Token non interpretato dal DB.
2. Un **aggancio opzionale** sul template (`pratiche.template_flussi`) verso quel
   catalogo. NULL = il completamento è il cambio stato generico standard
   (nessuna azione di dominio). Coerente con §5.8.2 (aggancio sempre opzionale).
3. **Seed** del solo consumatore reale oggi: `ACCETTA_PREVENTIVO` agganciato al
   template `APPROVAZIONE_CLIENTE` dei tipi prestazione PREVENTIVI (9002/9006 →
   verificare l'id dello step APPROVAZIONE_CLIENTE). Offerta/contratto entreranno
   nel catalogo quando nasceranno i loro flussi (stesso precedente di `azioni_ui`).

> Mirror esatto del lavoro già consegnato in
> [brief-db-ESECUZIONE-azione-ui-e-contesto-cliente.md](../work-done/brief-db-ESECUZIONE-azione-ui-e-contesto-cliente.md):
> stessa struttura (catalogo + FK nullable sul template), stessi trigger di audit,
> stessa filosofia "il template dichiara, il motore esegue per dati".

## 3. Cosa NON è richiesto

- Nessuna logica di dominio nel DB: l'azione di completamento è **eseguita dal
  BE/FE** (chiama l'endpoint di dominio già esistente, es. M2). Il DB fornisce
  solo il **token dichiarativo** sul template.
- Nessun trigger nuovo: l'accettazione del documento resta nell'endpoint di
  dominio esistente.

## 4. A valle (BE/FE — non DB, per contesto)

- **BE**: esporre `template_completa_azione_key` sul flusso (JOIN al catalogo),
  esattamente come già fatto per `template_azione_ui_key`
  ([pratiche_repository.py](../../../backend/apps/pratiche/db/pratiche_repository.py)).
- **FE**: registry `COMPLETION_REGISTRY[key] → fn(payload)` (gemello di
  `UI_ACTIVITY_REGISTRY`); `FlussoDrawer.onCompleta` instrada via registry se la
  chiave è presente, **altrimenti** cambio stato generico — sostituendo l'attuale
  `if isPreventivi && APPROVAZIONE_CLIENTE`. Niente regressione: finché la chiave
  non è seedata, il fallback hardcoded M2 resta; rimosso alla consegna del seed.

---

*Brief DB — azione di completamento flusso data-driven — ZeroERP (2026-06-15).
PROPOSTA. Sblocca la rimozione dell'ultimo hardcoding di routing nel FlussoDrawer.*
