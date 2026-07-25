# Brief DB — Chiusura della ri-consegna: rendere DEFINITIVO un reso per ri-spedizione

> **Tipo**: brief operativo DB · **Target**: `dev/db-tid` · **Data**: 2026-07-25
> · **Owner**: Tid
> **Stato**: 🔴 **DA APPLICARE** — **nessuna domanda aperta**: le quattro scelte
> di progetto sono chiuse in §5 (ok Tid 2026-07-25). BE/FE in attesa dell'apply
> ([[feedback_be_fe_attende_prerequisiti_db]]).
> **Origine**: rilievo emerso validando la ri-spedizione su RESO0000150 /
> DDT0000338 — una ri-consegna parziale (o mai eseguita) lascia l'ordine
> **PARZIALMENTE_EVASO per sempre**, senza alcun modo in-app di chiuderla.
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]])
> → breaking secco, nessuna compat.

---

## 1. Scopo in una riga

Dare all'operatore un modo di dichiarare che una quota di merce resa **per
ri-consegna non tornerà al cliente**: il residuo ordine si chiude (EVASO) e
l'accredito su quella quota passa da facoltativo a **dovuto**.

## 2. Il buco

`fn_genera_ddt_riconsegna` è ri-eseguibile e gestisce bene il parziale: ri-spedisci
3 su 10, la riga resta in coda con residuo 7 e generi un altro DDT quando serve.
Ma **non esiste l'uscita opposta**. Se quei 7 non torneranno mai al cliente:

- `fn_ordine_ha_residuo_evasione` continua a contarli (addendo
  `fn_ordine_riga_qta_riconsegna`, che somma le righe reso `riapre_residuo`)
  → l'ordine resta **PARZIALMENTE_EVASO** a vita;
- la riga resta nell'elenco ri-spedizione, indistinguibile da una lavorabile;
- in `vw_resi_da_accreditare` l'accredito resta etichettato **FACOLTATIVA**,
  quindi l'operatore che lavora le dovute non lo vede mai.

A DB la riga si chiuderebbe disattivandola (`resi_righe.attivo`), ma il drawer
non espone l'edit righe su un reso CONFERMATO — e disattivare sarebbe comunque
sbagliato: cancellerebbe il fatto che la merce **è** rientrata.

## 3. La scoperta che rende il fix piccolo

**L'accredito è già in coda, e già del valore giusto.** Verificato in
`vw_contatore_merce`: la CTE `res` somma `vw_resi_righe_effettive` **senza
filtro sul tipo** →

```
tenuti = evaso − reso          (il reso è già sottratto, qualunque tipo)
differenza = tenuti − fatturati
coda accrediti = differenza < 0
```

Su ordine 10 / evaso 10 / fatturato 10 / reso 3 per ri-consegna: `tenuti = 7`,
`differenza = −3` → la riga **è già in `vw_resi_da_accreditare` con
`accredito_dovuto = 3`**, etichettata FACOLTATIVA. Se poi la ri-consegna
avviene, il fulfillment rialza `evaso` a 13 → `tenuti` torna 10 → `differenza 0`
→ la riga **esce da sola** dalla coda.

Conseguenza di progetto: **chiudere la ri-consegna non cambia nessun numero.**
Non tocca `tenuti`, non tocca l'importo dell'accredito, non crea documenti.
Cambia solo la **natura** della quota pendente: da «tornerà indietro» a
«definitiva». Il fix è quindi una dichiarazione, non un calcolo.

## 4. Proposta

### 4.1 Una tabella speculare al ponte delle ri-consegne

`vendite.resi_righe_rinunce` — gemella di `resi_righe_riconsegne`, che già
registra il lato consegnato:

| colonna | note |
| --- | --- |
| `resi_riga_id` | FK `vendite.resi_righe` |
| `qta` | unità **base**, coerente con `resi_righe_riconsegne.qta`; CHECK `> 0` |
| `motivo` | testo **facoltativo**, come `resi_righe.motivo` (vedi §5.3) |
| audit | `date_insert`/`user_insert`/… da policy |

**Perché una tabella e non una colonna** `qta_riconsegna_rinunciata` su
`resi_righe`: la rinuncia, come la ri-consegna, può essere **parziale e
ripetuta** (rinuncio a 3 oggi, ad altri 2 la settimana prossima). Una colonna
accumula il totale e perde chi/quando/perché di ogni evento; la tabella rende
la formula del residuo perfettamente simmetrica —

```
residuo = quantita − Σ riconsegnate − Σ rinunciate
```

— e rende la **reversibilità** (§5.1) la cancellazione di una riga, non
un'aritmetica all'indietro.

Regge il **parziale** senza casi speciali: 3 già ri-consegnati, 7 rinunciati,
la storia di entrambi resta leggibile.

### 4.2 Una riga sola nell'helper unico

```sql
-- fn_ordine_riga_qta_riconsegna: l'addendo reso scende della quota rinunciata
SELECT COALESCE(SUM(e.quantita - <Σ rinunce della riga>), 0) ...
```

È **il** punto: quella funzione è già dichiarata «single source per
`fn_ordine_ha_residuo_evasione` e `trgfn_ordini_ful_guard_consistenza`
(coerenza formula)». Sottraendo lì, il residuo si chiude **e** il guard
anti over-fulfillment resta coerente, senza toccare né l'uno né l'altro.
Se la modifica si facesse altrove, le due formule divergerebbero.

⚠️ `vw_resi_righe_effettive` (CONFERMATE + attive) è l'helper che la funzione
legge: la quota rinunciata va esposta lì, o sottratta risalendo a
`resi_righe_rinunce`. Da decidere in sede di scrittura — l'unico vincolo è che
resti **un solo** punto di sottrazione.

### 4.3 La funzione di chiusura

`vendite.fn_chiudi_riconsegna_reso(p_reso_id bigint, p_righe jsonb DEFAULT NULL)`
— speculare a `fn_genera_ddt_riconsegna`:

- guard: reso **CONFERMATO** (stesso gate della generazione);
- `p_righe = NULL` → rinuncia a **tutta** la copertura residua; altrimenti
  `[{resi_riga_id, qta}]` con `LEAST(richiesta, residuo)`, stessa semantica
  race-proof della generazione;
- errore se non c'è nulla da chiudere (`E_RESO_NESSUNA_RICONSEGNA_PENDENTE`,
  riuso);
- **ri-proiezione stato ordine** in coda, identica allo step 7 della generazione
  (`PARZIALMENTE_EVASO` / `EVASO`) — è ciò che chiude l'ordine.

### 4.4 L'etichetta della coda accrediti

`vw_resi_da_accreditare.etichetta` oggi è `CASE WHEN riapre_residuo THEN
'FACOLTATIVA' ELSE 'DOVUTA'`. Diventa **DOVUTA anche quando non resta
copertura ri-consegnabile**: la merce non torna, l'accredito non è più una
scelta. In pratica: `riapre_residuo AND residuo_riconsegna > 0` → FACOLTATIVA,
altrimenti DOVUTA. (Il caso «tutto ri-consegnato» non serve gestirlo qui: quelle
righe escono dalla coda da sole, §3.)

### 4.5 Perché NON cambiare il `tipo_reso` della riga

L'alternativa ovvia — flippare la riga da RESO_PER_RICONSEGNA ad A_CREDITO —
sembra più economica ma rompe il **parziale**: su 3 già ri-consegnati e 7
rinunciati, il flip toglie `riapre_residuo` all'intera riga, quindi i 3
fulfillment di ri-consegna già esistenti si ritrovano senza l'addendo che li
giustificava → `trgfn_ordini_ful_guard_consistenza` vede un over-fulfillment
retroattivo. E si perderebbe il fatto che quella merce era rientrata *per*
essere ri-consegnata.

## 5. Decisioni prese (ok Tid 2026-07-25)

### 5.1 Reversibile, con il gate NC progettato ma dormiente

`vendite.fn_riapri_riconsegna_reso(p_reso_id, p_righe)` simmetrica: cancella (o
disattiva) le rinunce e ri-proietta lo stato ordine, che torna
PARZIALMENTE_EVASO. Un errore di digitazione su un reso CONFERMATO deve avere
rimedio, come `fn_annulla_reso` lo dà alla conferma.

⚠️ Il gate corretto sarebbe «reversibile **finché la nota di credito non è
stata emessa**» — ma **il ramo NC non esiste ancora** (slice a sé; la coda
accrediti oggi la alimenta e basta). Quindi: nessun gate NC oggi, ma il punto
va **lasciato esplicito nel commento della funzione**, perché la slice NC dovrà
aggiungerlo. È l'unico modo per non ritrovarsi domani una riapertura che
sfalsa una NC già emessa ([[feedback_concentrico_no_yagni]]: il guard si
progetta per l'espansione, non si rinvia).

### 5.2 Audit: la tabella (§4.1), non la colonna

Decisa contestualmente alla struttura: rinunce parziali e ripetute, ognuna con
il suo chi/quando/perché, e reversibilità come cancellazione di riga.

### 5.3 Motivo facoltativo

Testo libero **nullable**, come `resi_righe.motivo` che già esiste sul reso: la
stessa forma per la stessa natura di informazione. Obbligatorio no — sarebbe
attrito su ogni chiusura, e il caso «il cliente non lo rivuole» è la norma, non
l'eccezione da giustificare. Quando la slice NC avrà bisogno di una
classificazione contabile, diventerà un lookup: il campo c'è già e si stringe,
mentre partire da un enum inventato oggi vincolerebbe a codici mai validati sul
campo.

### 5.4 Merce fisica: fuori perimetro, ma dichiarato

La quota rinunciata resta materialmente al fornitore. Senza modulo magazzino non
c'è nulla da movimentare, ma **va scritto nel `COMMENT ON FUNCTION`**: è
esattamente il tipo di conseguenza che sparisce dalla memoria del progetto e
riemerge come sorpresa quando il magazzino arriverà.

## 6. Verifica attesa

- Reso CONFERMATO con 10 resi per ri-consegna, 0 ri-spediti → `fn_chiudi_riconsegna_reso`
  senza righe → ordine passa a **EVASO**, riga fuori dall'elenco ri-spedizione,
  accredito in coda con etichetta **DOVUTA** e importo **invariato**.
- Parziale: 3 ri-spediti + 7 chiusi → ordine **EVASO**, `accredito_dovuto` invariato,
  nessun errore da `trgfn_ordini_ful_guard_consistenza`.
- Non-regressione: dopo una chiusura parziale, `fn_genera_ddt_riconsegna` sulla
  stessa riga **non** deve poter ri-spedire la quota rinunciata (il residuo la
  esclude → `E_RESO_NESSUNA_RICONSEGNA_PENDENTE`).
- **Reversibilità**: `fn_riapri_riconsegna_reso` sulla stessa riga → l'ordine
  torna PARZIALMENTE_EVASO, la riga ricompare in elenco ri-spedizione, l'etichetta
  in coda torna FACOLTATIVA. Round-trip chiudi→riapri = stato iniziale.
- pgTAP: la formula del residuo resta identica fra `fn_ordine_ha_residuo_evasione`
  e `trgfn_ordini_ful_guard_consistenza` (è l'invariante che l'helper unico esiste
  per proteggere), **e la simmetria** `quantita − Σ riconsegnate − Σ rinunciate`
  non va mai negativa (over-rinuncia rifiutata come l'over-ri-spedizione).

## 7. BE/FE a valle (dopo l'apply, non prima)

- Endpoint speculari a `genera-riconsegna`: POST `/vendite/resi/{id}/chiudi-riconsegna/`
  e POST `/vendite/resi/{id}/riapri-riconsegna/` (§5.1), con le policy dei codici
  errore nuovi in `error_policies.py`.
- FE: **stessa dialog** «DDT ri-spedizione» (`ResoRiconsegnaDialog`), stessa lista e
  stessa selezione, secondo esito nel footer — «Genera DDT» / «Rendi definitivo il
  reso». Due uscite della stessa attività in un posto solo, invece di una seconda
  dialog gemella. Conferma esplicita sul significato: *la merce non tornerà al
  cliente e l'accredito diventa dovuto*. Le righe già rinunciate restano visibili
  in elenco come consuntivo (colonna «rinunciata» accanto a «ri-consegnata»), con
  l'azione di riapertura sul kebab riga.
- La nota i18n `vendite.resi.riconsegna_nota_parziale` — già in app, spiega che il
  parziale non perde il resto — andrà estesa: il resto si può anche **chiudere**,
  non solo ri-spedire più tardi.
