# Brief DB — Guard: lo step SMISTAMENTO accetta solo l'esito di RAMO (bivio)

> ⛔ **SUPERATO / DEPRECATO (2026-07-02)** — assorbito e **corretto** dalla **Parte 1** di
> [brief-db-step-dominio-e-definizioni-versionate.md](brief-db-step-dominio-e-definizioni-versionate.md)
> (già **applicata + testata** dal team DB: `modalita_esito = 'DOMINIO'` + guard runtime
> `FLUSSI_ESITO_NON_AMMESSO`). Il brief unificato corregge un errore fattuale di questo
> documento: il percorso che accettava `POSITIVO` non è il generico `cambia_stato_flusso`
> ma il percorso mainstream `ApiPraticaFlussoStato` → `completa_flusso`. **Non attuare
> questo brief**: mantenuto solo come riferimento storico (link dal brief unificato).
> ⚠️ **ASSORBITO (2026-07-02)** nella **Parte 1** di
> [brief-db-step-dominio-e-definizioni-versionate.md](brief-db-step-dominio-e-definizioni-versionate.md),
> che contiene anche le **correzioni fattuali** emerse dall'analisi (il percorso scoperto è
> quello mainstream `completa_flusso`, non solo il generico; mitigazione solo FE ⇒ priorità
> alta; modello scelto: `modalita_esito = 'DOMINIO'`). Consumi BE/FE nel companion
> [brief-be-fe-step-dominio-e-definizioni-versionate.md](brief-be-fe-step-dominio-e-definizioni-versionate.md).
> Questo file resta come **storia dell'incidente `PRA-0000243`** — non usarlo come specifica.
>
> **Per**: team DB (`dev/db-tid`). · **Da**: backend/frontend agent. · **Priorità**: 🟠 media
> (bug logico del modello, oggi mitigato solo lato UI). · **Data**: 2026-07-02.
> **Origine**: analisi flusso PREVENTIVI→commessa su pratica reale `PRA-0000243`.
> Questo brief descrive **cosa serve** (l'invariante). Il **come** (trigger / fn /
> vincolo / marker sul template) è scelta del team DB.

---

## 1. Contesto e problema

Lo step **SMISTAMENTO** (`pratiche.template_flussi` id 9012, tipo prestazione 9004
PREVENTIVI) è un **bivio**: il suo esito NON è un verdetto scelto dall'operatore, ma è
**calcolato dal dominio** e determina il ramo del percorso:

- **`MERCE_PRESENTE`** (`config.esiti_flussi_pratiche` id 5, `is_verdetto=false`) → la
  pratica resta APERTA e diventano dovuti i flussi merce a valle **9013 CONFERMA_ORDINE**
  e **9014 INVIO_COMMESSA**;
- **`SOLO_SERVIZI`** (id 6, `is_verdetto=false`) → ramo morto, la pratica chiude.

L'esito corretto lo scrive **solo** il BB di dominio `vendite.completa_smistamento`
(calcola il ramo, verifica che non restino righe non smistate, completa lo step nella
stessa transazione).

**Cosa è successo su `PRA-0000243`**: lo step SMISTAMENTO (flusso id 543) è stato chiuso
con esito **`POSITIVO`** (un verdetto generico, `is_verdetto=true`) tramite il percorso
di completamento **generico** (`cambia_stato_flusso`). Effetto: il ramo merce non si è
attivato (9013/9014 mai comparsi), la pratica si è auto-chiusa, e ordine→commessa sono
stati completati **a mano fuori dalla pratica**.

**Perché i guard attuali non lo intercettano** (entrambi lato BE `pratiche_service`):

- `require_esito_selezionabile_operatore`: vieta di impostare **a mano** un esito di
  dominio (blocca MERCE_PRESENTE via percorso operatore). Non riguarda il caso opposto.
- `_require_esito_valido`: verifica solo che l'esito **esista** a vocabolario.

`POSITIVO` è un verdetto valido → passa entrambi. **Nessun guard verifica che lo step
SMISTAMENTO, che RICHIEDE un esito di ramo, non venga chiuso con un verdetto generico.**

**Mitigazione già in atto (UI)**: il `FlussoDrawer` ora sopprime il picker esito sullo
SMISTAMENTO e instrada il completamento su `completa_smistamento`. Quindi dalla UI il
problema non è più riproducibile. Questo brief chiede la **difesa in profondità
autoritativa a DB**, perché il percorso generico `cambia_stato_flusso` accetta ancora,
di per sé, un verdetto su quello step.

## 2. Cosa serve (invariante)

Il completamento di uno step **bivio** (esito calcolato dal dominio) deve essere
accettato **solo** con uno dei suoi **esiti di ramo** ammessi; ogni altro esito
(verdetto generico o esito non pertinente) va **rifiutato con errore parlante**,
qualunque sia il percorso di scrittura (dominio o generico).

Concretamente, per lo SMISTAMENTO:

- completamento con `MERCE_PRESENTE` o `SOLO_SERVIZI` → **ammesso**;
- completamento con `POSITIVO` / `NEGATIVO` / `PARZIALE` / `NON_APPLICABILE` o qualunque
  altro esito → **rifiutato**.

L'invariante deve valere anche se la scrittura arriva dal percorso generico
`cambia_stato_flusso`, non solo da `completa_smistamento`.

## 3. Ambito

- **Step interessato oggi**: SMISTAMENTO (9012), esiti di ramo MERCE_PRESENTE/SOLO_SERVIZI.
- **Generalità richiesta**: la soluzione dovrebbe essere **data-driven / estendibile**, non
  cablata sul solo `codice='SMISTAMENTO'`. Sono in arrivo altri step bivio con lo stesso
  schema (rollout offerte/ordini/contratti — cfr.
  `brief-db-proiezione-stato-dominio-rollout-offerte-ordini-contratti.md`), e ognuno avrà
  i propri esiti di ramo. Serve quindi un modo per **sapere quali esiti sono ammessi per
  quale step** (oggi questa relazione non è modellata: gli esiti sono un catalogo globale
  e non esiste una whitelist esiti-per-template). Se introdurre questo legame è troppo per
  ora, va bene una prima versione mirata allo SMISTAMENTO, **purché** l'estensione futura
  non richieda di riscrivere il meccanismo.

## 4. Criteri di accettazione

1. Completare lo step SMISTAMENTO con `POSITIVO` (o altro verdetto) via il percorso
   generico **fallisce** con errore parlante (codice del catalogo DB).
2. `vendite.completa_smistamento` continua a funzionare invariato su entrambi i rami
   (MERCE_PRESENTE e SOLO_SERVIZI).
3. Gli **altri** step (APPROVAZIONE_CLIENTE, CONFERMA_ORDINE, INVIO_COMMESSA, e in generale
   gli step NON-bivio) restano completabili con i loro verdetti come oggi: il guard non
   deve toccarli.
4. **Idempotenza preservata**: ri-completare uno step già terminale resta no-op (nessun
   errore spurio sul re-fire), coerente con `completa_step_pratica`.
5. pgTAP verdi + smoke del percorso PREVENTIVI end-to-end (smistamento merce → 9013/9014 →
   commessa) dentro la pratica.

## 5. Note / attenzioni

- **Non è un problema di dati**: `PRA-0000243` è già stata risolta a mano (ordine
  ORD0000140 confermato, commessa CMM-…-28fa41 creata). Nessuna migrazione dati richiesta;
  serve solo l'invariante a monte per i casi futuri.
- Il legame naturale dell'invariante è il **momento di completamento del flusso**
  (transizione a COMPLETATO con esito). Dove esattamente collocarlo è vostra scelta.
- Coordinamento BE: se scegliete un nuovo codice errore, segnalatelo così lo mappo nei
  marker `_KNOWN_DB_ERROR_MARKERS` di `pratiche_service` (traduzione in ServiceError
  parlante lato API).

## 6. Fuori scope (NON in questo brief)

- Il fix **UI** (soppressione picker + instradamento su `completa_smistamento`) è **già
  fatto** lato FE — non tocca il DB.
- La modellazione completa "esiti ammessi per step" come feature generale (whitelist
  esiti-per-template) è opzionale: se decidete di introdurla, può diventare un brief a sé;
  qui serve l'invariante, non necessariamente il modello completo.

---

*Brief DB — invariante di completamento per gli step bivio (esito di ramo calcolato dal
dominio). Caso concreto: SMISTAMENTO deve accettare solo MERCE_PRESENTE/SOLO_SERVIZI,
mai un verdetto generico. Difesa in profondità: la UI è già chiusa, manca il guard DB.*
