# Pratiche — Configurazione e opzioni del workflow (appendice operativa)

> **Appendice** di [Gestione Pratiche e Workflow](gestione-pratiche.md). Mentre la
> guida descrive il **modello**, qui si raccoglie il **come configurarlo**: ricette
> operative per definire i workflow e le loro opzioni. Documento **vivo**: cresce con
> le funzionalità di configurazione che vengono aggiunte (vedi §7).

---

## 1. Anatomia di un workflow (sintesi)

Un workflow di pratica si configura su quattro livelli (dettaglio modello nella guida):

1. **Tipo prestazione** (`pratiche.tipi_prestazione`) — il "catalogo": cosa si può fare.
2. **Template flussi** (`pratiche.template_flussi`) — gli **step** previsti per quel tipo
   (uno per fase del workflow). È qui che vivono quasi tutte le opzioni descritte sotto.
3. **Prerequisiti** (`pratiche.template_flussi_prerequisiti`) — il **grafo**: quale step
   dipende da quale (e con quale esito richiesto).
4. **Automazioni** opzionali sullo step: **handler** Django (`handler_id`), **attività
   UI** (`azione_ui_id`), **handler di evento** (`template_flussi_handler_eventi`).

All'esecuzione, ogni template genera **flussi** (`pratiche.flussi`) dentro la pratica:
ogni flusso ha uno **stato** (DA_ESEGUIRE → IN_CORSO → COMPLETATO) e un **esito**
(POSITIVO / NEGATIVO / PARZIALE / NON_APPLICABILE) registrato alla chiusura.

> **Dove si configura oggi**: la definizione di tipi/template/prerequisiti avviene via
> **seed DB** (changeset Liquibase in `80_data/...`), non c'è ancora una UI di
> amministrazione del workflow. Le ricette sotto indicano i campi da valorizzare.

## 2. Creare un flusso (un template di step)

Un template-step è una riga di `pratiche.template_flussi`. Campi da impostare:

| Campo | Obbl. | Cosa controlla |
|---|---|---|
| `tipo_prestazione_id` | sì | A quale tipo prestazione appartiene lo step. |
| `codice` | sì | Identificativo dello step (univoco per tipo, es. `RICHIESTA_CLIENTE`). |
| `descrizione` | sì | Etichetta leggibile (mostrata in UI e nel giornale). |
| `sequenza` | — | Ordine logico (0, 10, 20…). L'ordine *effettivo* è dato dai prerequisiti. |
| `direzione` | — | `INTERNA` (default) / `ENTRATA` / `USCITA` — vedi §3 (vincola l'automatismo). |
| `obbligatorio` | — | `true` = deve completarsi per chiudere la pratica (se ancora percorribile). |
| `chiude_pratica` | — | `true` = "flusso di chiusura": al suo completamento la pratica passa a CHIUSA (max uno per tipo, implica `obbligatorio`). |
| `ripetibilita` | — | `SE_NON_POSITIVO` (default) / `MAI` / `SEMPRE` — se lo step può essere ri-istanziato nella stessa pratica. |
| `modalita_esito` | — | **Come si ottiene l'esito**: `MANUALE` / `AUTOMATICO` / `CONTESTUALE` — vedi §3. |
| `esito_default` | dipende | L'esito applicato/pre-selezionato; obbligatorio se `modalita_esito ≠ MANUALE`. |
| `handler_id` | — | NULL = step manuale; valorizzato = automazione di dominio Django (vedi §2.1). |
| `handler_params` | — | JSONB di parametri per l'handler (es. `{"modalita_fatturazione": "IMMEDIATA"}`). |
| `azione_ui_id` | — | Attività interattiva offerta dallo step (apre un drawer di dominio, vedi §2.2). |

Poi si collega lo step al **grafo** inserendo le righe in
`template_flussi_prerequisiti` (da quale step dipende, ed eventuale `esito_richiesto`),
e — se serve visibilità esterna — i **canali** in `template_flussi_canali`.

### 2.1 Step automatizzato da handler (`handler_id`)

Se lo step deve **eseguire logica di dominio** all'avvio (es. spingere un preventivo a
ordine/commessa), si associa un `handler_id` (catalogo `pratiche.handler_flussi`) la cui
chiave è mappata a una classe Python nel registry (`HANDLER_MAP`). All'avvio il motore
esegue l'handler e, su esito positivo dell'esecuzione, **completa lo step**
automaticamente con `esito_default` (fallback POSITIVO). Esempio: `CONFERMA` →
`vendita.push_preventivo`.

### 2.2 Step con attività UI (`azione_ui_id`)

Se lo step deve **aprire un drawer di dominio** (es. compilare il preventivo), si associa
una `azione_ui_id` (catalogo `pratiche.azioni_ui`, es. `APRI_PREVENTIVO`,
`APRI_OFFERTA`, `APRI_CONTRATTO`). Il frontend, tramite il registry delle attività UI,
apre il drawer corrispondente. È lo "specchio FE" dell'handler: l'handler fa lavoro
server-side, l'attività UI fa lavoro guidato dall'operatore.

## 3. Gestione dell'esito: le tre modalità (`modalita_esito`)

È l'opzione che decide **quanti passaggi** servono per chiudere uno step e **chi decide
l'esito**. Si imposta con la coppia `modalita_esito` + `esito_default` sul template.

### MANUALE (default) — due step

Comportamento storico: l'operatore **avvia** lo step (DA_ESEGUIRE → IN_CORSO), poi nel
drawer del flusso **sceglie l'esito** (select + note) e salva (IN_CORSO → COMPLETATO).

* **Due azioni** distinte. **Quando usarlo**: l'esito è un verdetto reale che matura nel
  tempo (es. l'attesa di una risposta esterna).
* `esito_default` non richiesto (resta NULL).

### AUTOMATICO — un click "Avvia e completa"

Lo step si avvia e si chiude **da solo** con `esito_default`, senza che l'operatore
scelga l'esito. In UI un'unica azione **"Avvia e completa"** porta DA_ESEGUIRE →
COMPLETATO.

* **Una azione, nessuna scelta di esito**. **Quando usarlo**: formalità interne il cui
  esito è scontato.
* `esito_default` **obbligatorio**.
* **Vincolo**: ammesso **solo** per step a `direzione = INTERNA`. Un esito automatico su
  uno step ENTRATA/USCITA equivarrebbe a *fabbricare* la risposta di una controparte
  esterna (guard DB, errore `TEMPLATE_FLUSSO_AUTOMATICO_SOLO_INTERNA`).
* Se lo step ha anche un `handler_id`, l'handler viene eseguito e la chiusura usa
  comunque `esito_default`.

### CONTESTUALE — avvio + esito in un'unica azione

L'operatore **registra l'esito contestualmente all'avvio**: il drawer mostra subito il
form esito con `esito_default` **pre-selezionato e modificabile**; un solo salvataggio
porta DA_ESEGUIRE → COMPLETATO con l'esito confermato.

* **Una azione, ma l'esito è confermato da un umano** (nessuna perdita di fedeltà).
* `esito_default` **obbligatorio** (è il valore pre-impostato).
* **Nessun vincolo di direzione**: valido anche su ENTRATA/USCITA (l'operatore conferma
  comunque un esito reale).

### Tabella riassuntiva

| Modalità | Azioni UI | Esito deciso da | `esito_default` | Vincolo direzione |
|---|---|---|---|---|
| `MANUALE` | 2 (Avvia → Completa) | operatore, a posteriori | non richiesto | nessuno |
| `AUTOMATICO` | 1 (Avvia e completa) | configurazione | obbligatorio | solo `INTERNA` |
| `CONTESTUALE` | 1 (Avvia + esito) | operatore, contestuale | obbligatorio | nessuno |

### Invarianti (guard DB, config-time)

Le due regole di coerenza sono verificate da un guard sul template (errori parlanti):

* `modalita_esito ≠ MANUALE` ⇒ `esito_default` valorizzato →
  `TEMPLATE_FLUSSO_ESITO_DEFAULT_OBBLIGATORIO` (494).
* `modalita_esito = AUTOMATICO` ⇒ `direzione = INTERNA` →
  `TEMPLATE_FLUSSO_AUTOMATICO_SOLO_INTERNA` (495).

Il guard runtime dell'esito al COMPLETATO (`FLUSSI_ESITO_OBBLIGATORIO`) resta la rete
fail-closed: nessuno step si chiude senza esito.

## 4. Esempio completo: le pratiche PREVENTIVI

Catena `RICHIESTA_CLIENTE → PREVENTIVAZIONE → APPROVAZIONE_CLIENTE → CONFERMA`:

| Step | direzione | automazione | `modalita_esito` | `esito_default` | Effetto operativo |
|---|---|---|---|---|---|
| `RICHIESTA_CLIENTE` | ENTRATA | — | `CONTESTUALE` | POSITIVO | L'operatore registra la richiesta e l'esito in un colpo. |
| `PREVENTIVAZIONE` | INTERNA | azione UI `APRI_PREVENTIVO` | `MANUALE` | — | Apre il drawer preventivo; il flusso si completa all'emissione del preventivo. |
| `APPROVAZIONE_CLIENTE` | ENTRATA | handler evento `vendita.accetta_preventivo` su COMPLETATO+POSITIVO | `CONTESTUALE` | POSITIVO | L'operatore conferma l'approvazione; il preventivo passa ad ACCETTATO. |
| `CONFERMA` | INTERNA | handler `vendita.push_preventivo` | `AUTOMATICO` | POSITIVO | Avvia e completa: spinge il preventivo a valle, chiude POSITIVO. |

Lettura: gli step verso il cliente gestiti internamente diventano **un click**
(CONTESTUALE), la conferma interna è **automatica**, mentre la preventivazione resta
guidata dall'attività UI e si chiude all'emissione.

## 5. Riferimento rapido — opzioni `template_flussi`

| Campo | Valori | Default | Note |
|---|---|---|---|
| `sequenza` | int | 0 | Ordine logico. |
| `direzione` | `INTERNA` / `ENTRATA` / `USCITA` | `INTERNA` | Rapporto con l'esterno; vincola `AUTOMATICO`. |
| `obbligatorio` | bool | false | Richiesto per chiudere la pratica. |
| `chiude_pratica` | bool | false | Flusso di chiusura (max 1/tipo, implica `obbligatorio`). |
| `ripetibilita` | `MAI` / `SE_NON_POSITIVO` / `SEMPRE` | `SE_NON_POSITIVO` | Ri-istanziabilità nella stessa pratica. |
| `modalita_esito` | `MANUALE` / `AUTOMATICO` / `CONTESTUALE` | `MANUALE` | Come si ottiene l'esito (§3). |
| `esito_default` | POSITIVO / NEGATIVO / PARZIALE / NON_APPLICABILE | NULL | Obbligatorio se `modalita_esito ≠ MANUALE`. |
| `handler_id` | FK `handler_flussi` | NULL | Automazione di dominio all'avvio. |
| `handler_params` | JSONB | `{}` | Parametri per l'handler. |
| `azione_ui_id` | FK `azioni_ui` | NULL | Attività UI (drawer di dominio). |

Riferimenti modello: [template_flussi](/dbzero/pratiche/tabelle/template_flussi) ·
[ciclo di vita del flusso](gestione-pratiche.md#flusso) ·
[API cambio stato flusso](/backend/pratiche/manual/api_flusso_stato).

## 6. Note operative

* Le configurazioni si applicano via **seed/upsert DB** (changeset Liquibase). Non
  esiste ancora una UI di amministrazione del workflow: aggiungere/modificare uno step
  significa intervenire sul seed di `template_flussi` (+ prerequisiti/canali) e
  ri-applicare.
* Le scelte di `modalita_esito`/`esito_default` sono **per template**: lo stesso step
  può essere MANUALE in un tipo prestazione e CONTESTUALE in un altro, se modellato così.

## 7. Aggancio di un documento versionato a una pratica (link parametrico)

> 🟠 **Convenzione proposta / in adozione** col primo consumatore (pratica PREVENTIVI) —
> non ancora a catalogo. Riferimento:
> [brief-db-pratica-preventivi-tipo-unico-flussi.md](../dev/work-done/brief-db-pratica-preventivi-tipo-unico-flussi.md).

Quando una pratica usa un **documento di dominio versionato** (es. un preventivo, che a ogni
revisione è una **nuova riga** con `uid`/`id` nuovi ma **stesso `numero`**), il legame ROOT in
`pratiche.pratiche_sorgenti` deve poter **seguire la versione viva** senza che `pratiche`
sappia cosa sia quel documento (direzione anelli: `pratiche` non legge `vendite`).

Convenzione (in `pratiche_sorgenti.meta`, niente nuove colonne):

```json
{
  "ref_stable_key": "PREV-100",   // identità STABILE (es. numero), non l'uid della singola revisione
  "follow_active": true            // true = segui la versione attiva; assente/false = pin alla versione agganciata
}
```

Regole:

* il **kind** non si ripete in `meta`: lo dà già `sorgente_tipo_id` (PREVENTIVO/…);
* la chiave del documento (per il preventivo `sorgente_uid`, il suo uid) resta quella dell'**entry-point**, la versione al momento dell'aggancio → tracciabilità;
* **chi risolve la versione viva è il dominio proprietario** (es. `vendite` via
  `vw_preventivi.is_attiva`), a **read-time**: il link resta fermo (nessun UPDATE/trigger).
  All'annullamento di una revisione la versione attiva torna da sola al predecessore.

> **Generalizzazione rinviata** (manifesto §7): la forma `meta` è generica per riuso futuro
> (es. revisione di contratto/offerta in pratica), ma il framework/registro generico si
> costruisce solo **dopo un 2° consumatore reale** — non ora.

## 8. Funzionalità di configurazione — stato e roadmap

| Funzionalità | Stato | Riferimento |
|---|---|---|
| Esito configurabile (MANUALE / AUTOMATICO / CONTESTUALE) | ✅ disponibile | §3 · [brief design](../dev/work-done/brief-design-esito-configurabile-flussi.md) |
| Attività UI da flusso (apri preventivo/offerta/contratto) | ✅ disponibile | §2.2 |
| Handler di dominio + handler di evento | ✅ disponibile | §2.1 · [Handler Django](gestione-pratiche.md#handler-django-registry-pattern) |
| Link parametrico a documento versionato (`meta.ref_stable_key`/`follow_active`) | 🟠 in adozione (1° consumatore: preventivi) | §7 |
| UI di amministrazione del workflow (no-seed) | ⏳ futuro | — |

> Aggiornare questa tabella e le sezioni §2–§3 a ogni nuova opzione di configurazione
> introdotta.

---
{% include-markdown "signature-core.md" %}
