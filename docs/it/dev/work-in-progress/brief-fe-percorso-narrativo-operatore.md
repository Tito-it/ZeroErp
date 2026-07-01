# Brief FE — Il Percorso pratica da grafo-macchina a racconto operatore

> **Tipo**: brief FE (design → implementazione) · **Data**: 2026-07-01
> **Owner**: Tid · **Stato**: 🟠 proposto — da validare su PREVENTIVI prima di estendere.
>
> **Origine**: voce **V1** di
> [analisi-pratiche-valutazione-stato.md](analisi-pratiche-valutazione-stato.md)
> (Problema 1 — comprensibilità operatore), con **misura** delle superfici FE reali
> fatta il 2026-07-01. Principio guida ereditato da
> [analisi-uniformita-pratica-preventivi.md](analisi-uniformita-pratica-preventivi.md):
> *la pratica non deve divergere dal programma standalone.*
>
> **Documenti collegati**: [Guida Gestione Pratiche §Flusso](../../guide/gestione-pratiche.md#flusso),
> [Gestione Pratiche — Configurazione](../../guide/gestione-pratiche-configurazione.md).

---

## 1. Problema (misurato)

Il vocabolario da motore **trapela verso l'operatore**, in modo concentrato e
prevedibile, e **peggiora con la profondità**: la superficie d'ingresso è quasi pulita,
la vista che dovrebbe essere il *racconto* (il Percorso) è la più leaky. Scorecard con
evidenze puntuali:

| Superficie | Voto | Perdite principali |
|---|---|---|
| **"Le mie attività"** ([MieAttivitaPanel.vue](../../../../frontend/src/pratiche/components/MieAttivitaPanel.vue)) | 🟢 buono | Livelli coda tradotti in intento (`COMPETENZA → "Da prendere"`, `LIBERO → "Da assegnare"`). Unico neo: la barra dice *"attività"*, il contenuto sotto dice *"flusso"* → **due parole per la stessa cosa**. |
| **Coda lavoro** ([PraticheCodaLavoro.vue](../../../../frontend/src/pratiche/components/PraticheCodaLavoro.vue)) | 🟡 misto | Riga: **codice grezzo prima** della descrizione (`template_flusso_codice \|\| template_flusso_desc`, [L78](../../../../frontend/src/pratiche/components/PraticheCodaLavoro.vue#L78)); stato = codice (`stato_flusso_codice`, [L80](../../../../frontend/src/pratiche/components/PraticheCodaLavoro.vue#L80)); empty = *"Nessun **flusso** in coda"*. |
| **Percorso** ([PraticaPercorso.vue](../../../../frontend/src/pratiche/components/PraticaPercorso.vue)) | 🔴 il più leaky | **Titolo di ogni step = codice template grezzo** (`RICHIESTA_CLIENTE`…, [L124](../../../../frontend/src/pratiche/components/PraticaPercorso.vue#L124)); stato = `stato_codice_interno` ([L59-61](../../../../frontend/src/pratiche/components/PraticaPercorso.vue#L59-L61)); numero di **sequenza** (`#{{ step.sequenza }}`, [L120](../../../../frontend/src/pratiche/components/PraticaPercorso.vue#L120)); esito grezzo (*"Esito: POSITIVO"*, [L131-133](../../../../frontend/src/pratiche/components/PraticaPercorso.vue#L131-L133)); tooltip con la parola **"handler"** (`percorso_handler = "Step automatico (handler)"`). |
| **FlussoDrawer** ([FlussoDrawer.vue](../../../../frontend/src/pratiche/components/FlussoDrawer.vue)) | 🟠 testata leaky, corpo ok | Titolo *"**Esecuzione flusso** — APPROVAZIONE_CLIENTE"* ([L258-262](../../../../frontend/src/pratiche/components/FlussoDrawer.vue#L258-L262)), icona `pi-sitemap`; campo etichettato *"**Template**"* ([L289](../../../../frontend/src/pratiche/components/FlussoDrawer.vue#L289)); stato grezzo. **Corpo buono**: esiti umanizzati, "Reparto"/"Operatore" puliti, affordance *"Apri preventivo"*. |

**Il filo conduttore (rende il fix economico):** ogni tabella-vocabolario del motore ha
già una colonna **`descrizione`** pensata per l'occhio umano — verificato su
[`config.stati_flussi_pratiche`](../../dbzero/config/tabelle/stati_flussi_pratiche.md)
(`NOT NULL`), su `template_flussi.descrizione` (*"etichetta leggibile mostrata in UI"*) e
sulla nuova `config.esiti_flussi_pratiche.descrizione`. Il FE però renderizza
**`codice`/`codice_interno`** in posizione di titolo. **L'etichetta umana esiste nel dato
e non viene pescata.**

**La perdita più profonda (non lessicale):** anche traducendo ogni parola, resta il
problema vero — **il Percorso espone il modello di configurazione, non il compito.**
Mostra tutti gli step possibili, inclusi quelli *"Da creare"* (futuri) e i *"Rami chiusi"*
(bivio non preso), con i loro stati-macchina. È la mappa del template, non «cosa devo
fare adesso».

---

## 2. Principio

1. **L'operatore non deve mai vedere «il flusso».** *Flusso, template, prerequisito,
   sequenza, handler, direzione, modalità esito* sono plumbing: mai a video per un
   operatore. (Una modalità "tecnica/avanzata" per super-admin è ammessa — §6.)
2. **La vista è un racconto con un solo pulsante attivo.** «Sei qui → il prossimo passo è
   questo → [un pulsante]». Il grafo, i rami morti e gli stati-macchina restano nel
   motore, non a video.
3. **Uniformità con lo standalone.** Il pulsante attivo apre *le stesse schermate* che
   l'operatore già conosce (già vero per l'affordance "Apri documento"): la pratica
   *orchestra*, non reinventa.
4. **Nessuna logica di business nel FE.** Le regole (prerequisiti esito-aware,
   ripetibilità, rami) restano a DB con **errore parlante**; il FE non le duplica.

---

## 3. Il fix in due strati

### 3.1 Strato A — Lessico + fonte-dato (il 70% economico)

Chiude gran parte della perdita **lessicale** senza toccare il motore. Due mosse:

**(a) Renderizzare `descrizione`, non `codice`.** Superficie per superficie:

| Superficie | Oggi renderizza | Deve renderizzare | Dipendenza |
|---|---|---|---|
| Percorso — titolo step | `template_flusso_codice` | `template_flusso_descrizione` | display field già presente sul flusso (usato nel drawer); da esporre anche nel payload percorso |
| Percorso / Coda / Drawer — stato | `stato_codice_interno` / `stato_flusso_codice` | `stato_*_descrizione` | **BE**: esporre display field `stato_descrizione` dove manca |
| Percorso — esito | `step.esito` (grezzo) | `esito_descrizione` | **BE**: display field da `config.esiti_flussi_pratiche.descrizione` (data-driven: gli esiti di dominio non sono hardcodabili in i18n) |
| Coda — riga | codice-first | `descrizione`-first (invertire il fallback) | display field già disponibile |

**(b) i18n — togliere il gergo dalle superfici operatore:**

- `coda_vuota`: *"Nessun flusso in coda"* → *"Nessuna attività in coda"*;
- allineare a **una sola parola**: "attività" (non "flusso") ovunque l'operatore legga
  (`flusso_esecuzione`, `flusso_generico`, `flusso_avvia`, `flusso_col_template`,
  `percorso_handler`…);
- `flusso_col_template` *"Template"* → rimuovere dalla vista operatore (resta in modalità
  tecnica);
- `percorso_handler` *"Step automatico (handler)"* → *"Passo automatico"* (via l'"handler");
- valutare `pi-sitemap` → un'icona meno "organigramma" nel titolo del drawer.

> Nota: i **numeri di documento** (`PRA-0000216`, il numero preventivo) **restano**:
> gli operatori vivono coi numeri di documento; non sono gergo.

### 3.2 Strato B — La vista-racconto (il 30% strutturale) — **cuore del brief**

Il Percorso smette di essere la mappa del template e diventa il **viaggio della pratica**.

**Cosa nascondere** (resta nel motore, non a video per l'operatore):
- gli step **futuri "Da creare"** come card cliccabili in fila (il percorso condizionale
  non è ancora deciso: mostrarli tutti confonde);
- i **rami chiusi** (`RAMO_CHIUSO`): semplicemente non compaiono;
- gli **stati-macchina** grezzi e il **numero di sequenza**;
- la distinzione template/istanza (`flusso_id` null vs valorizzato): è un dettaglio
  implementativo.

**Cosa mostrare:**
- **un solo passo attivo**, in grande, con **una azione primaria** ("Fai il preventivo",
  "Conferma col cliente", "Avvia e completa") — riusando `modalita_esito` per collassare i
  click come già fa il motore;
- **dove si è nel viaggio**, in forma leggera e leggibile: passi *fatti* (✓, con la loro
  `descrizione`), passo *corrente*, e — se serve — «poi mancherà…» come **testo**, non come
  griglia di card cliccabili;
- il resto (esito registrato, chi è assegnato, tempi/SLA) come **contorno**, non come
  protagonista.

**Regole di comportamento invariate** (nessuna logica nel FE): cliccare qualcosa non
ancora percorribile continua a produrre l'**errore parlante del DB** (i prerequisiti
esito-aware restano l'unica fonte di verità); la ripetibilità di uno step continua a
venire dal flag `ripetibile_adesso` calcolato dal DB.

---

## 4. Sketch (prima → dopo)

**Oggi — Percorso = debugger:**

```text
Percorso
[#0 RICHIESTA_CLIENTE  (COMPLETATO)] → [#10 PREVENTIVAZIONE (IN_CORSO)] →
[#20 APPROVAZIONE_CLIENTE (Da creare)] → [#30 CONFERMA (Ramo chiuso)]
                                          Esito: POSITIVO   ⚡(handler)
```

**Dopo — Percorso = racconto:**

```text
Preventivo per Mario Rossi · PRA-0000216

  ✓ Richiesta registrata
  ▶ ADESSO: Fai il preventivo            [ Apri preventivo ]
    · poi: conferma col cliente, poi invio a valle

  (assegnato a te · reparto Commerciale · in tempo)
```

La stessa informazione, ma l'operatore legge **cosa ha fatto**, **cosa deve fare ora** e
**un pulsante** — non un grafo con stati-macchina e rami morti.

---

## 5. Deliverable FE (+ prerequisiti BE)

**BE (prerequisito, piccolo — display fields):**
- esporre nel payload del **percorso** e della **coda**: `*_descrizione` per template
  step, stato ed esito (leggendo le colonne `descrizione` già esistenti). Nessuna logica
  nuova: solo campi display.

**FE:**
- **B1** — `PraticaPercorso.vue`: riprogettazione vista-racconto (§3.2 + §4): un passo
  attivo + timeline leggera; rimozione card "Da creare"/"Ramo chiuso" dalla vista
  operatore; render `descrizione`.
- **B2** — `PraticheCodaLavoro.vue`: `descrizione`-first, stato via `descrizione`, empty
  "attività".
- **B3** — `FlussoDrawer.vue`: titolo senza "flusso"/codice grezzo (usare `descrizione` +
  contesto pratica), rimuovere il campo "Template" dalla vista operatore, stato via
  `descrizione`.
- **B4** — i18n `it.json`/`en.json`: unificare "attività", ripulire le chiavi gergo (§3.1b).
- **B5** — (opzionale) toggle **modalità tecnica** per super-admin che ri-espone codici,
  sequenza, stati-macchina, rami (§6).

---

## 6. Vincoli e non-obiettivi

- **Non si tocca il motore** (DB/trigger/macchina a stati). Solo FE + display fields BE.
- **Nessuna regola nel FE**: prerequisiti/ripetibilità/rami restano a DB (errore parlante).
- **Modalità tecnica ammessa**: per super-admin/diagnostica va bene ri-mostrare
  codici/sequenza/stati/rami — ma è **opt-in**, mai il default dell'operatore.
- **Non è l'ispettore di configurazione** (voce V4/V5 dell'analisi): questa è la vista
  *runtime* dell'operatore, non l'editor del workflow. Sono due lavori distinti.

---

## 7. Domande aperte (decisioni per l'owner)

1. **Quanto "viaggio" mostrare?** Solo il passo corrente, oppure una mini-timeline
   fatti/corrente/prossimi come **testo**? (Proposta: fatti + corrente + una riga "poi…".)
2. **Rami condizionali**: quando il percorso ha bivi, mostrare i passi futuri come incerti
   o ometterli finché non sono percorribili? (Proposta: ometterli; il DB decide.)
3. **Modalità tecnica**: serve già ora (B5) o si rimanda? (Proposta: rimandare; prima
   validare la vista operatore su PREVENTIVI.)

---

*Brief vivo: aggiornare lo stato in testa e la riga V1 di
[analisi-pratiche-valutazione-stato.md](analisi-pratiche-valutazione-stato.md) a chiusura.*
