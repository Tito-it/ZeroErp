# Brief DB — chiusura pratica guidata dal workflow (auto + flusso di chiusura)

**Area:** `pratiche` · **Tipo:** modello chiusura + auto-transizione
**Branch destinazione:** `dev/db-tid`
**Richiesto da:** backend agent (per Tid) · **Data:** 2026-06-14

> Nota: il brief descrive **cosa** deve garantire il DB, non **come**.
> Scelta implementativa (trigger, attributo, fasi, SQL) a discrezione del team DB.

---

## 1. Contesto e decisione

Oggi la pratica si chiude con un'azione manuale dell'operatore ("Chiudi"), gated dal
guard `trg_pratiche_a10_guard_chiusura_flussi` (consente CHIUSA solo se nessun
flusso obbligatorio è ancora "bloccante", vedi `fn_check_chiusura_pratica`).

Decisione: la chiusura deve essere **guidata dal workflow**, non discrezionale. Modello
**misto**:

- **Senza flusso di chiusura** definito sul tipo prestazione → **auto-chiusura**: la
  pratica passa ad `APERTA → CHIUSA` da sola quando il percorso è concluso (tutti gli
  obbligatori completati, nessun bloccante — la stessa semantica di
  `fn_check_chiusura_pratica`).
- **Con flusso di chiusura** definito → la chiusura è determinata dal **completamento
  di quel flusso** (è lo step che "chiude" la pratica).

`Sospendi` e `Annulla` restano azioni manuali dell'operatore (interruzioni volontarie,
non dipendono dal completamento del percorso): non cambiano.

## 2. Cosa deve garantire il DB

1. **Marcatura "flusso di chiusura".** Serve poter indicare, a livello di tipo
   prestazione, che un determinato template flusso è quello che chiude la pratica
   (informazione oggi assente su `pratiche.template_flussi`). Al massimo uno per tipo
   prestazione.
2. **Auto-chiusura senza flusso di chiusura.** Quando il tipo prestazione NON ha un
   flusso di chiusura, al completamento di un flusso la pratica deve transitare
   automaticamente ad `APERTA → CHIUSA` se `fn_check_chiusura_pratica` non riporta più
   bloccanti (tutti gli obbligatori completati o non più percorribili).
3. **Chiusura via flusso di chiusura.** Quando il tipo prestazione HA un flusso di
   chiusura, la pratica deve transitare a `CHIUSA` al **completamento** di quel flusso.
4. In entrambi i casi la transizione automatica deve **rispettare i guard esistenti**
   (transizioni valide, `data` ecc.) e registrare nel giornale come una normale
   chiusura.

## 3. Vincoli ed eccezioni (da confermare con Tid dove indicato)

- **Auto-chiusura solo da `APERTA`.** Una pratica `SOSPESA` non si auto-chiude (è
  interrotta volontariamente); idem `BOZZA`/già terminale.
- **Flusso di chiusura vs altri obbligatori (da confermare).** Se è definito un flusso
  di chiusura ma restano altri obbligatori non completati al suo completamento: la
  pratica chiude lo stesso (il flusso di chiusura "ha l'ultima parola"), oppure la
  chiusura resta subordinata al completamento di tutti gli obbligatori? Proposta:
  il flusso di chiusura è ammesso/completabile solo quando il resto del percorso
  obbligatorio è concluso (coerente col guard attuale), così "chiude" senza scavalcare
  obbligatori pendenti.
- **Flussi non obbligatori ancora aperti.** Come oggi, non bloccano la chiusura (il
  guard ragiona sugli obbligatori). Resta così salvo diversa indicazione.
- Il guard di chiusura esistente resta valido (difesa contro chiusure premature).

## 4. Criteri di accettazione (comportamento atteso, test pgTAP)

1. Tipo prestazione **senza** flusso di chiusura: completato l'ultimo flusso
   obbligatorio → la pratica risulta `CHIUSA` automaticamente.
2. Tipo prestazione senza flusso di chiusura, con un obbligatorio ancora da fare:
   completato un flusso non finale → la pratica resta `APERTA`.
3. Tipo prestazione **con** flusso di chiusura: completato quel flusso → la pratica
   risulta `CHIUSA`.
4. Auto-chiusura **non** avviene su pratica `SOSPESA`.
5. La chiusura automatica registra l'evento nel giornale come la chiusura manuale
   odierna.
6. Regressione: il guard di chiusura prematura continua a impedire stati incoerenti.

## 5. Downstream (dopo consegna)

- **FE**: rimozione del pulsante manuale "Chiudi" dalla scheda pratica (la chiusura
  diventa data-driven); `Sospendi`/`Annulla` invariati.
- **BE**: nessuna logica di chiusura lato servizio (resta a DB); eventuale esposizione
  dell'attributo "flusso di chiusura" nelle API di configurazione template, se serve
  gestirlo da UI (da valutare separatamente).
