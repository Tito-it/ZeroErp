# Brief DB — Dashboard fatturazione: escludere le attività di commessa annullate/rifiutate dai conteggi

> **Per**: team DB (`dev/db-tid`). · **Da**: backend/frontend agent. · **Priorità**: 🔴 ALTA
> (bug logico del modello: i numeri della dashboard mentiranno appena esiste
> un'attività annullata — memoria `feedback_bug_logici_modello`). · **Data**: 2026-07-04.
> **Origine**: analisi UI dashboard fatturazione con Tid — verifica di quali stati
> vengono esclusi dai conteggi.
> **Correlato**: `brief-design-dashboard-fatturazione.md` (design autorevole);
> `analisi-dash-pre-fatturazione.md` (analisi situazioni anomale, in corso);
> vista `vendite.vw_dash_fatturazione_commesse`; tabella `vendite.commesse_attivita`.
>
> ## ✅ Stato: DB APPLICATO (2026-07-04, migration `20260703-61`) — nessun intervento BE/FE
>
> * **Fix**: predicato "computabile" nel `WHERE` del resolver, simmetrico a
>   `orr.attivo IS TRUE` degli ordini:
>   `stato_emissione <> 'ANNULLATA' AND (stato_approvazione <> 'RIFIUTATA' OR stato_emissione = 'EMESSA')`.
> * **Decisione `RIFIUTATA` (Tid 2026-07-04): void terminale**, come `ANNULLATA` —
>   un rifiuto è pari a un documento `esito = NEGATIVO` nelle altre 4 aree. Eccezione
>   di sicurezza: `EMESSA + RIFIUTATA` (assi indipendenti nel CHECK) è già transitata
>   → **tenuta**, non persa. Dopo l'esclusione, `ATTIVITA_NON_APPROVATA` torna vero
>   solo per le BOZZA reali.
> * **Regressione zero**: oggi nessun percorso DB/BE scrive `ANNULLATA`/`RIFIUTATA`
>   su `commesse_attivita` (stati CHECK-validi ma dead); la `RIFIUTATA` NON è cablata
>   all'L3 (che rifiuta il *prezzo* su `preventivi_righe`/`contratti_righe`, non le
>   attività). Fix difensivo-in-avanti. Verificato su DB di test: con GUC impostata i
>   numeri commesse sono identici a prima (giugno 10 doc / 5718,10).
> * **Contratto colonne invariato** → `vw_dash_fatturazione_documenti`/`_mensile` e il
>   BE/FE **non cambiano** (nessun nuovo `motivo_fermo`: i void escono, non compaiono).
>   pgTAP → `plan(28)` (2080-06 EMESSA+ANNULLATA+RIFIUTATA → totale=solo EMESSA; mese
>   di sole void assente; edge `EMESSA+RIFIUTATA` tenuta).
>
> *Il testo sotto è il brief originale, conservato per traccia.*

---

## Contesto

Il resolver `vw_dash_fatturazione_commesse` calcola totale/transitato/fermo per commessa
× mese aggregando le righe `commesse_attivita`. Gli stati ammessi (da CHECK):

* `stato_emissione ∈ {NON_EMESSA, EMESSA, ANNULLATA}`
* `stato_approvazione ∈ {BOZZA, APPROVATA, RIFIUTATA}`

Oggi il resolver è così (estratto dalla view viva):

```sql
sum(COALESCE(ca.prezzo_snapshot,0) * ca.quantita)                                   AS valore_totale,
sum(...) FILTER (WHERE ca.stato_emissione = 'EMESSA')                               AS valore_transitato,
count(*)                                                                            AS unita_totali,
count(*) FILTER (WHERE ca.stato_emissione = 'EMESSA')                              AS unita_transitate,
count(*) = count(*) FILTER (WHERE ca.stato_emissione = 'EMESSA')                    AS is_transitato,
-- motivo_fermo:
--   ... count(*) FILTER (stato_emissione <> 'EMESSA' AND stato_approvazione <> 'APPROVATA') > 0
--       → 'ATTIVITA_NON_APPROVATA' ; ELSE 'ATTIVITA_NON_EMESSA'
```

## Problema — le attività annullate/rifiutate restano nel denominatore

`valore_totale` / `unita_totali` e il denominatore di `is_transitato` contano **tutte** le
attività, **senza escludere** `stato_emissione = 'ANNULLATA'` (né, da decidere,
`stato_approvazione = 'RIFIUTATA'`). Conseguenze su una commessa **viva** (testata non
ANNULLATA) che abbia anche solo un'attività annullata:

1. **Totale gonfiato**: il valore dell'attività annullata entra nel totale del mese.
2. **`is_transitato` falso in eterno**: `count(*) > count(EMESSA)` perché l'annullata non
   sarà mai EMESSA → la commessa risulta **ferma per sempre**, valore-fermo = valore
   dell'annullata, semaforo mese ⚠ che non si spegnerà mai.
3. **`motivo_fermo` fuorviante**: un'attività ANNULLATA (non-EMESSA) fa scattare
   `ATTIVITA_NON_APPROVATA` o `ATTIVITA_NON_EMESSA` — etichette che dicono "da lavorare",
   mentre è **void**: chi gestisce la dashboard la solleciterebbe a vuoto.

È l'esatto simmetrico di ciò che gli **ordini** già fanno bene: il resolver ordini conta
solo le righe `WHERE orr.attivo IS TRUE` (le righe annullate/inattive sono fuori dal
denominatore). Le commesse devono avere la stessa rete.

Nota: in sviluppo oggi non esistono attività ANNULLATA/RIFIUTATA (solo EMESSA/NON_EMESSA e
APPROVATA/BOZZA), quindi il bug è **latente** — scatterà al primo annullamento reale.

## Cosa serve

Escludere dal **denominatore** (totale, unità totali, e quindi da `is_transitato` e dal
valore-fermo) le attività **non computabili**, mantenendo il transitato = solo EMESSA:

* **`stato_emissione = 'ANNULLATA'` → ESCLUDERE** (void a livello emissione, caso chiaro,
  simmetrico a `orr.attivo = false`).
* **`stato_approvazione = 'RIFIUTATA'` → DA DECIDERE** (owner/design): è "void" (rifiuto
  definitivo → escludere come sopra) **oppure** "anomalia azionabile" (da ri-lavorare →
  tenerla nel totale ma con un `motivo_fermo` **dedicato e corretto**, es.
  `ATTIVITA_RIFIUTATA`, non `ATTIVITA_NON_APPROVATA` che significa "in attesa")? La scelta
  dipende dalla semantica di RIFIUTATA nel workflow prezzi L3 — vostra + Tid.

Inoltre, il vocabolario `motivo_fermo` non deve mai etichettare un void come "in attesa":
dopo l'esclusione, `ATTIVITA_NON_APPROVATA` deve restare vero **solo** per attività
realmente in attesa di approvazione (BOZZA), non annullate.

*Il come* (FILTER nel resolver, o predicato "attività computabile" riusabile) è vostra
scelta; l'importante è che valore/unità/transito/fermo/motivo siano coerenti.

## Criteri di accettazione

1. Una commessa viva con N attività di cui una `ANNULLATA`: `unita_totali` e `valore_totale`
   **non** includono l'annullata; se tutte le altre sono EMESSA → `is_transitato = true`,
   `n_fermi = 0`, semaforo verde.
2. La stessa attività annullata **non** compare nel drill-down fermi (non è "ferma": è void).
3. Semantica `RIFIUTATA` decisa ed esplicita (esclusa come void **oppure** ferma con motivo
   dedicato); nessun void etichettato `ATTIVITA_NON_APPROVATA`.
4. Nessuna regressione sul caso base (nessuna attività annullata/rifiutata → numeri identici
   a oggi).
5. pgTAP esteso: fixture commessa con 1 attività EMESSA + 1 ANNULLATA → totale/unità = solo
   la EMESSA, `is_transitato = true`; fixture con 1 RIFIUTATA → comportamento dell'opzione scelta.

## Fuori scope

* Commesse ANNULLATE a livello testata (già gestite: `is_abortito` sul `sc.codice_interno`).
* Le altre 4 aree (già escludono i void: `esito = NEGATIVO` a livello documento, `attivo` sulle righe ordine).
* Data/timestamp di transito per l'evidenza dei recuperi tardivi (asse diverso, vedi
  `analisi-dash-pre-fatturazione.md` §gap temporale).
