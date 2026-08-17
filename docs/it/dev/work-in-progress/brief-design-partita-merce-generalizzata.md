# Brief di design — generalizzare la «partita»: dalla riga d'ordine alla riga di merce

> **Tipo**: brief di design · **Data**: 2026-08-17 · **Owner**: Tid ·
> **Stato**: 🟡 **APERTO** — decisione presa (opzione C), perimetro da chiudere
> con il team DB.
>
> **Cos'è**: oggi il conto della merce (`vendite.vw_contatore_merce`) esiste
> **solo** per la merce nata da una riga d'ordine. Tutto il resto — righe di DDT
> aggiunte a mano, e come si vedrà anche gli **articoli compositi** — è merce
> reale che il sistema muove, fattura, e di cui **non tiene il conto**.
>
> **Perché ora**: è il **prerequisito** di due cantieri già decisi. Farlo dopo
> significa rifarli.

---

## 🔢 L'ORDINE CON CUI ESEGUIRE I LAVORI COLLEGATI

Quattro cantieri nati fra il 2026-08-16 e il 2026-08-17. Tre sono in catena,
uno è indipendente.

| # | Cantiere | Brief | Perché in questa posizione |
| --- | --- | --- | --- |
| **1** | **Partita generalizzata** | **questo** | È la nozione su cui gli altri due poggiano. Cambiarla dopo obbliga a rifarli |
| **2** | Pannello «situazione merce» su ordine **e DDT** | [brief-design-situazione-merce-ordine.md](brief-design-situazione-merce-ordine.md) | Legge la partita. Fatto prima, mostrerebbe spedizioni miste con conti parziali **sul DDT**, dove l'incoerenza si vede a occhio |
| **3** | Nota di credito (emissione dell'accredito) | [brief-design-note-credito-resi.md](brief-design-note-credito-resi.md) | Attribuisce l'accredito **alla partita**. Scritta sulla chiave di oggi, andrebbe riscritta — e nel frattempo avrà emesso **documenti fiscali** |
| **—** | Righe DDT a prezzo zero | [brief-ddt-righe-senza-prezzo.md](brief-ddt-righe-senza-prezzo.md) | **Indipendente**: riguarda il pricing in inserimento, non la partita. Può procedere in parallelo e sblocca la validazione DL-28 |

⚠️ **La catena 1 → 2 → 3 non è una preferenza di comodo.** Il punto 3 produce
documenti fiscali: rifarlo significa riconciliare note di credito già emesse,
cioè la categoria di dato che meno si può correggere a posteriori.

---

## 1. Come funziona la partita oggi, letto dal codice

`vw_contatore_merce` compone tre grandezze e le àncora **tutte** alla riga
d'ordine:

```text
tenuti      = Σ ordini_righe_fulfillment.qta_evasa  −  Σ vw_resi_righe_effettive.quantita
fatturati   = Σ attivita_fatturabili.quantita  (solo tipo_movimento = 'NORMALE')
differenza  = tenuti − fatturati
```

E la chiusura è questa:

```sql
partite = (SELECT ordine_riga_id FROM ful) UNION (SELECT ordine_riga_id FROM res)
...
FROM partite p JOIN vendite.ordini_righe orr ON orr.id = p.ordine_riga_id
```

⭐ **La riga d'ordine non è un attributo della partita: è la partita.** Ciò che
non ha una riga d'ordine non compare come riga a conto zero — **non esiste**.

### Il passaggio che spiega tutto: come `fatturati` risale alla riga d'ordine

Le attività fatturabili non portano un `ordine_riga_id`: portano una
`segment_key`, e il contatore la interpreta:

```text
segment 'ORD:<uid>:R:<id>'  →  <id> È la riga d'ordine
segment 'DDT:<uid>:R:<id>'  →  <id> è una riga di DDT
                               →  JOIN ordini_righe_fulfillment ON ddt_riga_id
                               →  da lì si ricava la riga d'ordine
```

⚠️ **Ed è esattamente lì che la riga manuale cade.** Il suo segmento è
`DDT:…:R:<id>`, il `JOIN` sul fulfillment non trova nulla, e la riga **esce dal
conto senza errore**: fatturata, ma invisibile. Non è una dimenticanza — è la
conseguenza di aver scelto la riga d'ordine come chiave.

## 2. 🔴 La seconda falla, trovata scrivendo questo brief

L'ultima riga della vista:

```sql
WHERE NOT COALESCE(art.is_composito, false)
```

**Gli articoli compositi sono esclusi dal conto della merce.** Qualunque
spedizione di un composito — con o senza ordine — è merce che si muove e che il
contatore non vede.

Ne discende che **la merce senza partita non è un caso di nicchia**: sono almeno
tre famiglie.

| Famiglia | Perché fuori | Frequenza |
| --- | --- | --- |
| Righe di DDT aggiunte a mano | nessun fulfillment | il caso che ha aperto la questione |
| Articoli **compositi** | esclusi dalla vista per costruzione | **12 righe d'ordine su 107** (misurato 2026-08-17): l'11%, non un caso di nicchia |
| DDT **standalone** (senza ordine) | nessuna riga d'ordine a monte | `fn_list_ddt_da_pushare` li fattura da sempre, ramo standalone |

⚠️ **La terza riga è la più significativa**: un DDT standalone viene **fatturato**
(l'abbiamo verificato oggi, `DDT0000034`) e non ha **mai** avuto un conto della
merce. Non è una regressione introdotta: è un buco che c'è da sempre e che nessuno
aveva visto perché il contatore non era mai stato mostrato a nessuno.

## 3. Cosa serve (il «cosa», non il «come»)

**La partita deve diventare la riga di merce, e la riga d'ordine una delle sue
possibili origini.**

* ogni riga di **DDT** ha una partita, che esista o no una riga d'ordine a monte;
* quando l'origine c'è, il conto si aggrega **anche** per riga d'ordine — è la
  lettura che serve all'ordine, e non deve peggiorare;
* quando l'origine non c'è, la partita **esiste comunque** e il conto è quello
  della sola riga di merce;
* i **compositi** entrano nel conto, o la loro esclusione diventa una scelta
  **dichiarata** con la sua ragione — non una condizione ereditata.

### Cosa ne consegue a valle, e va garantito

1. **`vw_resi_da_accreditare`** oggi si aggancia a `ordine_riga_id`: deve poter
   attribuire un accredito anche a merce senza origine ordine. `resi_righe`
   ha già `ddt_riga_id` **NOT NULL** e `ordine_riga_id` **nullable** — la strada
   è già aperta nel dato (2 righe su 17 hanno l'ordine vuoto).
2. **`vw_resi_da_riconsegnare`**: stessa verifica.
3. **Il conto per riga d'ordine non deve cambiare valore** dove oggi esiste. È il
   collaudo più importante: la generalizzazione è a **parità** sui casi già
   coperti, altrimenti non è una generalizzazione ma un cambio di semantica.

## 4. Vincoli

1. **Nessuna doppia contabilizzazione.** Se una riga di merce ha origine ordine,
   il suo conto deve comparire **una volta**: nella partita di merce e
   nell'aggregato d'ordine, che sono due letture della stessa cosa, non due righe.
2. **A parità sui casi coperti** (§3.3): i valori di oggi restano.
3. **Il vocabolario dei movimenti resta** `NORMALE | RETTIFICA | ONERE`. Oggi
   `fatturati` conta i soli `NORMALE`: la rettifica della NC (§4 del brief NC)
   dovrà **abbassare** il conto, quindi il criterio va rivisto insieme al punto 3
   della catena — ma la decisione è di quel cantiere, non di questo.
4. **Niente sui verbi**: questo brief cambia una nozione e ciò che la legge, non
   ciò che la scrive.

## 5. Cosa NON serve

* **Nessun cambio alla chiave di aggregazione della fattura**
  (`fn_build_fattura_key`): riguarda su chi si fattura, non di quale merce si
  tiene il conto.
* **Nessun cambio a `ordini_righe_fulfillment`**: resta il legame fra riga di DDT
  e riga d'ordine quando esiste. La generalizzazione sta nel **non pretenderlo**.
* **Nessuna bonifica retroattiva** decisa qui: se le partite storiche senza
  origine vadano ricostruite è una domanda del §6.

## 6. Domande aperte — per il team DB

1. **Dove vive la partita**: una vista che generalizza `vw_contatore_merce`, o una
   tabella? Oggi è calcolata; se resta calcolata, la chiave «riga di merce» va
   derivata a ogni lettura.
2. **I compositi**: entrano o l'esclusione si dichiara? ✅ La misura c'è già —
   **12 righe d'ordine su 107** portano un articolo composito, e il contatore ha
   in tutto **12 partite**: l'ordine di grandezza dice che l'esclusione non è
   marginale. Resta la domanda di merito: il conto di un composito è quello del
   padre o dei componenti? Probabilmente è **la ragione per cui l'esclusione
   esiste**, e va riletta prima di toglierla — non è detto sia una dimenticanza.
3. **Retroattività**: le partite oggi inesistenti (DDT standalone, righe manuali,
   compositi) vanno ricostruite sullo storico o valgono dai prossimi documenti?
   ⚠️ Se non si ricostruiscono, il pannello del punto 2 mostrerà «nessun conto»
   su documenti vecchi, e va detto invece di sembrare un guasto.
4. **La riga manuale con l'articolo dell'ordine** (§7-bis del brief NC, caso
   «stesso articolo»): con la partita generalizzata smette di falsare i conti, ma
   resta **indistinguibile da un errore dell'operatore**. Serve ancora un
   avviso, o la generalizzazione basta?

## 7. Definizione di «fatto» (bozza)

* [ ] una riga di DDT **senza ordine a monte** ha un conto della merce
      (consegnato, fatturato, reso, saldo);
* [ ] una riga di DDT **aggiunta a mano** su un DDT da ordine ha lo stesso;
* [ ] i conti **per riga d'ordine** esistenti hanno gli **stessi valori** di
      prima (parità verificata su dati reali, non su fixture);
* [ ] un reso su merce senza origine ordine produce un accredito **calcolabile**;
* [ ] la sorte dei **compositi** è decisa e scritta;
* [ ] la **retroattività** è decisa e scritta.
