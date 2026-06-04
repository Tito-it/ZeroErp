# Documenti non fiscali - riepilogo IVA DB

> Stato: WIP - analisi critica e piano preliminare DB.
>
> Obiettivo: definire una base DB coerente per esporre il riepilogo IVA nei
> context dei documenti commerciali non fiscali generati dal motore
> `documenti`, senza introdurre calcoli fiscali in Python o nei template.

## 1. Contesto

Durante la compilazione del template PDF per `ORDINE_VENDITA` e' emersa una
differenza rispetto a `PREVENTIVO`: il context `PREVENTIVO` espone gia'
`riepilogo_iva`, mentre il context `ORDINE_VENDITA` no.

Il builder ordini dichiara esplicitamente il confine v1:

- le righe portano IVA per riga;
- la testata espone totali aggregati (`imponibile`, `iva`, `documento`);
- non esiste ancora una vista/funzione DB dedicata al breakdown IVA;
- il backend non deve calcolare il riepilogo in Python per non duplicare formule
  e arrotondamenti DB.

La stessa mancanza va analizzata su:

- `OFFERTA_COMMERCIALE`;
- `CONTRATTO`;
- `ORDINE_VENDITA`.

`PREVENTIVO` resta il riferimento tecnico da copiare come regola di calcolo,
non come scelta di persistenza.

## 2. Regola IVA da riusare: preventivi

La logica corretta e gia' implementata sui preventivi in:

- `vendite.fn_ricalcola_riepilogo_iva_preventivo`;
- `vendite.fn_ricalcola_totali_preventivo`;
- `vendite.preventivi_riepiloghi_iva`;
- `vendite.vw_preventivi_riepilogo_iva_dettaglio`.

Regola chiave:

```text
1. calcolare l'imponibile riga a precisione piena;
2. raggruppare le righe per IVA;
3. calcolare imponibile gruppo = ROUND(SUM(imponibile_riga_full), 2);
4. calcolare imposta gruppo = ROUND(imponibile_gruppo * aliquota / 100, 2);
5. sommare i gruppi IVA per ottenere i totali documento.
```

Questa regola e' intenzionale: l'IVA non va calcolata e arrotondata sulla singola
riga per poi sommare. L'arrotondamento per riga e' stato esplicitamente corretto
nei preventivi per evitare differenze di centesimi rispetto alle fatture.

Per i documenti non fiscali la stessa regola deve valere anche se il risultato
viene esposto tramite viste e non scritto in una tabella fisica.

## 3. Decisione WIP

Per i documenti commerciali non fiscali il riepilogo IVA e' un dato derivato
dalle righe documentali. Se non c'e' un requisito esplicito di snapshot fiscale,
va esposto tramite viste DB, non tramite nuove tabelle fisiche.

Decisione aggiornata:

- `PREVENTIVO`: non modificare in questo intervento; mantiene tabella
  `preventivi_riepiloghi_iva` per coerenza con il flusso preventivo -> fattura.
- `ORDINE_VENDITA`: sospeso. E' il candidato tecnicamente piu' vicino ai
  preventivi, ma va prima chiusa la semantica bundle/componenti per evitare
  doppio conteggio o riepiloghi parziali.
- `CONTRATTO`: sospeso. Il documento usa preview/listino o righe native a
  seconda della modalita'; senza una sorgente righe fiscalmente normalizzata il
  riepilogo IVA sarebbe ambiguo.
- `OFFERTA_COMMERCIALE`: sospeso. Il documento v1 mostra solo eccezioni, non
  l'offerta economica completa; un riepilogo IVA su sole eccezioni rischia di
  essere letto come totale IVA dell'offerta.

Conclusione operativa: per ora **non creare viste di riepilogo IVA** per
`ORDINE_VENDITA`, `CONTRATTO` e `OFFERTA_COMMERCIALE`. Questo documento conserva
l'analisi e il piano condizionale da usare se il requisito viene riaperto.

## 4. Analisi critica per sorgente

### 4.1 Preventivi

Il preventivo ha una gestione piu' forte:

- tabella fisica `vendite.preventivi_riepiloghi_iva`;
- funzione di ricalcolo dedicata;
- trigger/totali testata che dipendono dal riepilogo persistito;
- vista dettaglio per UI/backend.

Questa scelta e' coerente con il fatto che il preventivo puo' diventare sorgente
di fattura. Qui serve consistenza al centesimo tra preventivo e fattura emessa.

Conclusione: usare i preventivi come riferimento per la formula, non come
obbligo di creare tabelle fisiche anche per offerte/contratti/ordini.

### 4.2 Ordini vendita

`vendite.ordini_righe` contiene gia':

- `quantita`;
- `prezzo_unitario`;
- `sconto_perc`;
- `iva_id`;
- `attivo`.

Quindi il riepilogo IVA ordine puo' essere derivato direttamente dalle righe
attive:

```sql
imponibile_riga_full =
  quantita * prezzo_unitario * (1 - COALESCE(sconto_perc, 0) / 100)
```

Punto critico: gli ordini supportano componenti BoM in
`vendite.ordini_righe_componenti`, e anche i componenti hanno `iva_id`,
`quantita`, `prezzo_unitario`, `attivo`.

Serve decidere se il riepilogo IVA dell'ordine deve usare:

- solo `ordini_righe`, assumendo che il padre composito abbia gia' prezzo/IVA
  documentale completa;
- oppure una sorgente normalizzata che, per i bundle, includa i componenti
  esposti e non il padre per evitare doppio conteggio.

Questa decisione e' bloccante: una vista "semplice" su `ordini_righe` puo'
essere corretta per righe standalone ma sbagliata per bundle, se il prezzo
documentale vive sui componenti.

### 4.3 Contratti

Il builder `CONTRATTO` non usa sempre `contratti_righe` come righe stampabili:

- per modalita' A/B con listino usa `ContrattiRepository.list_righe_preview`,
  wrapper di `vendite.fn_contratto_righe_preview`;
- per modalita' C senza listino usa `contratti_righe`.

Quindi il riepilogo IVA del contratto non puo' essere una somma ingenua di
`contratti_righe`: rischierebbe di perdere le righe da listino mostrate nel
documento o di calcolare solo override/eccezioni.

Punto critico: `contratti_righe` non ha `iva_id` sulla riga principale, mentre
`contratti_righe_componenti` ha `iva_id`. La preview contratto restituisce
`prezzo_finale`, ma non espone oggi una colonna IVA per tutte le righe preview.

Conclusione: per i contratti serve prima una vista/funzione normalizzata delle
righe documentali fiscali, allineata alla preview esistente, poi il riepilogo
IVA si calcola sopra quella normalizzazione.

### 4.4 Offerte commerciali

Il builder `OFFERTA_COMMERCIALE` stampa oggi le eccezioni, non il listino
effettivo completo:

- `offerte_commerciali_eccezioni` e' mirror di `contratti_righe`;
- `offerte_commerciali_eccezioni_componenti` contiene componenti BoM con
  `iva_id`, `quantita`, `prezzo_unitario`, `attivo`;
- il push offerta -> contratto copia le eccezioni in `contratti_righe`.

Punto critico: come per i contratti, la riga eccezione principale non ha
`iva_id`, mentre i componenti si'. Inoltre un'offerta in modalita' A/B puo'
avere un listino di riferimento, ma il documento v1 mostra solo le eccezioni.

Conclusione: il riepilogo IVA offerta deve seguire esattamente le righe esposte
nel context documentale corrente. Se il documento mostra solo eccezioni, il
riepilogo non deve provare a ricostruire il listino completo, salvo cambio
esplicito di requisito.

## 5. Principio di progettazione

Separare due livelli:

1. **Vista sorgente righe imponibili**: una vista/funzione per sorgente che
   normalizza le righe fiscalmente rilevanti in una shape comune.
2. **Vista riepilogo IVA**: aggrega la vista sorgente per IVA applicando la
   stessa formula dei preventivi.

Questa separazione evita di copiare formule in tre viste diverse e rende
testabile il punto piu' delicato: quali righe entrano davvero nel calcolo.

Shape proposta per la sorgente normalizzata:

```text
sorgente_id
sorgente_codice
riga_id
riga_tipo              -- RIGA | COMPONENTE | PREVIEW_LISTINO | ECCEZIONE
iva_id
aliquota_effettiva
quantita
prezzo_unitario
sconto_percentuale
imponibile_riga_full
attivo
ordinamento
```

Shape proposta per il riepilogo:

```text
documento_id
iva_id
iva_codice
iva_descrizione
iva_aliquota
imponibile
imposta
totale
arrotondamento
ordinamento
```

`documento_id` puo' essere rinominato nelle viste fisiche
(`ordine_id`, `contratto_id`, `offerta_id`), ma il backend dovra' normalizzare
l'output dei repository.

## 6. Formula obbligatoria

La vista di riepilogo deve applicare la formula dei preventivi:

```sql
WITH righe AS (
  SELECT
    documento_id,
    iva_id,
    aliquota_effettiva,
    imponibile_riga_full
  FROM ...
  WHERE attivo IS TRUE
    AND quantita > 0
)
SELECT
  documento_id,
  iva_id,
  ROUND(SUM(imponibile_riga_full), 2) AS imponibile,
  ROUND(
    ROUND(SUM(imponibile_riga_full), 2)
    * COALESCE(aliquota_effettiva, 0) / 100,
    2
  ) AS imposta,
  SUM(imponibile_riga_full) - ROUND(SUM(imponibile_riga_full), 2)
    AS arrotondamento
FROM righe
GROUP BY documento_id, iva_id, aliquota_effettiva;
```

Note:

- il `ROUND` dell'imposta usa l'imponibile gia' arrotondato del gruppo;
- non va usato `ROUND(imponibile_riga_full, 2)` prima della `SUM`;
- se serve override aliquota da stato emittente, usare
  `config.fn_get_aliquota_iva(iva_id, stato_emittente_id)` come nei preventivi;
- le righe senza `iva_id` non vanno silenziate: vanno escluse solo se la
  semantica della sorgente lo prevede, altrimenti devono emergere come problema
  dati/configurazione.

## 7. Opzioni implementative

### Opzione A - viste separate per sorgente

Creare viste dedicate:

```text
vendite.vw_ordini_riepilogo_iva
vendite.vw_contratti_riepilogo_iva
vendite.vw_offerte_commerciali_riepilogo_iva
```

Vantaggi:

- leggibile;
- aderente alle differenze reali tra sorgenti;
- facile da consumare nei repository Django;
- piu' semplice da testare con casi mirati.

Svantaggi:

- possibile duplicazione della formula;
- rischio di divergenza se non si centralizza almeno la normalizzazione o un
  helper SQL comune.

### Opzione B - funzione unica parametrica

Creare una funzione:

```text
vendite.fn_list_riepilogo_iva_documento_non_fiscale(
  p_sorgente_codice text,
  p_sorgente_id bigint
)
```

Vantaggi:

- contratto unico;
- meno metodi repository;
- utile se si definisce una sorgente normalizzata comune.

Svantaggi:

- dispatcher piu' opaco;
- rischio di nascondere differenze importanti tra ordini, contratti e offerte;
- meno naturale da usare nelle viste e nei test DB.

### Preferenza iniziale

Preferenza WIP: **Opzione A con normalizzazione esplicita per sorgente**.

Motivo: le sorgenti non sono omogenee. Ordini, contratti e offerte hanno
modelli righe diversi; forzare subito una funzione dispatcher rischia di
nascondere decisioni ancora aperte su bundle, componenti, listini e righe
documentali effettive.

## 8. Piano DB condizionale

Questo piano non e' da eseguire ora. Serve come traccia tecnica se in futuro si
decide di aggiungere il riepilogo IVA a uno o piu' documenti non fiscali.

### Fase 0 - Conferma semantica righe

Definire per ogni sorgente quali righe entrano nel documento e quindi nel
riepilogo IVA:

- ordini: solo `ordini_righe` oppure componenti BoM quando presenti;
- contratti A/B: righe da `fn_contratto_righe_preview`, includendo IVA;
- contratti C: righe `contratti_righe` e componenti;
- offerte: solo eccezioni stampate nel context v1 oppure futuro listino completo.

Esito atteso: una tabella decisionale "sorgente -> righe imponibili".

### Fase 1 - Vista sorgente normalizzata

Solo dopo la Fase 0, creare una vista/funzione per sorgente che espone righe
imponibili a precisione piena:

```text
vendite.vw_ordini_righe_iva_base
vendite.vw_contratti_righe_iva_base
vendite.vw_offerte_commerciali_righe_iva_base
```

Queste viste devono gia' risolvere:

- righe attive;
- esclusioni;
- bundle/componenti;
- prezzo effettivo;
- quantita effettiva;
- IVA effettiva;
- eventuale override aliquota da stato emittente.

### Fase 2 - Viste riepilogo IVA

Solo dopo la Fase 1, creare le viste finali:

```text
vendite.vw_ordini_riepilogo_iva
vendite.vw_contratti_riepilogo_iva
vendite.vw_offerte_commerciali_riepilogo_iva
```

Queste viste applicano solo aggregazione e rounding per aliquota, sul modello
preventivi.

### Fase 3 - Test pgTAP

Test minimi per ogni sorgente:

- nessuna riga attiva -> nessun riepilogo;
- due righe stessa IVA -> una riga riepilogo;
- due IVA diverse -> due righe riepilogo;
- caso centesimi: IVA calcolata sul totale gruppo, non per riga;
- righe inattive/escluse -> fuori dal riepilogo;
- bundle/componenti -> nessun doppio conteggio;
- coerenza con totale testata quando la testata ha gia' totali.

Test specifico anti-regressione:

```text
due righe con stessa IVA e imponibili che producono differenza tra:
SUM(ROUND(riga, 2)) e ROUND(SUM(riga), 2)
```

Il test deve confermare che vince `ROUND(SUM(...), 2)`.

### Fase 4 - Backend successivo

Dopo un eventuale landing DB, aggiungere nei repository:

```text
OrdiniRepository.list_riepilogo_iva(ordine_id)
ContrattiRepository.list_riepilogo_iva(contratto_id)
OfferteRepository.list_riepilogo_iva(offerta_id)
```

Poi aggiornare i builder:

```python
"riepilogo_iva": self._repo.list_riepilogo_iva(sorgente_id)
```

I template devono continuare a presentare dati gia' pronti, senza calcolare.

## 9. Rischi e punti aperti

### 9.1 Rischio doppio conteggio bundle

Se una riga padre composita ha prezzo e IVA e i componenti hanno a loro volta
prezzo e IVA, sommare entrambi duplica imponibile e imposta.

Decisione richiesta: per ogni sorgente, stabilire se il documento fiscale
logico si basa sul padre, sui componenti esposti o su una preview gia' aggregata.

### 9.2 IVA mancante su contratti/offerte righe principali

`contratti_righe` e `offerte_commerciali_eccezioni` non espongono `iva_id` sulla
riga principale. Se una riga senza componenti deve produrre IVA, la vista deve
risolvere l'IVA dall'articolo/listino/prezzo resolver oppure va introdotto uno
snapshot IVA.

Decisione richiesta: confermare la fonte autorevole dell'IVA per righe
contratto/offerta standalone.

### 9.3 Contratti preview senza IVA

`fn_contratto_righe_preview` e' la sorgente corretta per il documento contratto
A/B, ma oggi non sembra esporre una IVA normalizzata per ogni riga preview.

Decisione richiesta: estendere la preview oppure creare una funzione parallela
dedicata al calcolo IVA.

### 9.4 Offerte in modalita' A/B

Il builder offerta v1 stampa solo eccezioni, non tutto il listino effettivo.
Un riepilogo IVA coerente col documento deve seguire questa scelta. Se si vuole
riepilogare l'intera offerta commerciale, prima va cambiata la semantica del
documento e creata una preview offerta analoga a quella contratti.

### 9.5 Snapshot vs vista

Per documenti non fiscali la vista e' sufficiente finche' il requisito e'
mostrare un dato derivato corrente. Se un documento generato deve conservare per
sempre il breakdown IVA esatto del momento di emissione, lo snapshot deve stare
nel context salvato da `documenti_generati`, non necessariamente in nuove tabelle
di riepilogo.

## 10. Raccomandazione

Non implementare ora il riepilogo IVA per i documenti non fiscali.

Motivi:

- `ORDINE_VENDITA` richiede una decisione preventiva su bundle/componenti;
- `CONTRATTO` non ha una sorgente righe fiscalmente uniforme tra modalita' A/B/C;
- `OFFERTA_COMMERCIALE` oggi stampa solo eccezioni, quindi un riepilogo IVA
  sarebbe semanticamente parziale;
- nessuno di questi documenti e' fiscale nel senso forte che giustifica uno
  snapshot IVA dedicato come per fatture o, per continuita' di processo,
  preventivi.

Se il requisito viene riaperto, procedere in modo incrementale:

1. chiudere prima la tabella decisionale "sorgente -> righe imponibili";
2. implementare una sola sorgente pilota;
3. applicare la formula dei preventivi senza arrotondamento per riga;
4. aggiungere test pgTAP sui centesimi e sui bundle;
5. cablare il backend solo dopo il landing DB.

La regola non negoziabile e' il rounding: prima totalizzazione per aliquota, poi
calcolo IVA sul gruppo, come nei preventivi.
