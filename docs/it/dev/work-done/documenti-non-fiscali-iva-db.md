# Documenti non fiscali - riepilogo IVA DB

> Stato: pilot `ORDINE_VENDITA` **COMPLETO end-to-end** (DB + BE + FE).
>
> - **DB CONSEGNATO** (2026-06-05, PR #785, commit `0aa6cdf07`): viste + funzione
>   totali + 2 trigger + pgTAP verde (esito in 12.10). Modello: totali in testata
>   via trigger (12.3, opzione b), non drop colonne.
> - **BE + FE ESEGUITI** (2026-06-05): riepilogo IVA nel drawer ordini + nel
>   context stampa, clone catena preventivi. Test BE verdi, build FE verde, review
>   critica passata (esito in 13.11). **Resta solo** il template HTML PDF (manuale,
>   13.8). Piano in 13, esito in 13.11.
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

La stessa mancanza e' stata considerata su:

- `OFFERTA_COMMERCIALE`;
- `CONTRATTO`;
- `ORDINE_VENDITA`.

Decisione di perimetro: procedere solo su `ORDINE_VENDITA`. `CONTRATTO` e
`OFFERTA_COMMERCIALE` ragionano su sorgenti righe diverse e non hanno oggi una
base fiscalmente normalizzata unica per un riepilogo IVA non ambiguo.

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
- `ORDINE_VENDITA`: in scope come pilot. Creare viste DB derivate dalle righe
  ordine attive, applicando la stessa formula dei preventivi: sommare gli
  imponibili delle righe con la stessa aliquota e calcolare l'IVA sul totale
  del gruppo, non sulla singola riga.
- `CONTRATTO`: fuori scope. Il documento usa preview/listino o righe native a
  seconda della modalita'; senza una sorgente righe fiscalmente normalizzata il
  riepilogo IVA sarebbe ambiguo.
- `OFFERTA_COMMERCIALE`: fuori scope. Il documento v1 mostra solo eccezioni,
  non l'offerta economica completa; un riepilogo IVA su sole eccezioni rischia
  di essere letto come totale IVA dell'offerta.

Conclusione operativa: implementare il riepilogo IVA DB solo per
`ORDINE_VENDITA`. Non creare viste di riepilogo IVA per `CONTRATTO` e
`OFFERTA_COMMERCIALE` finche' non cambia la loro semantica documentale o non
viene introdotta una sorgente righe normalizzata.

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

Gli ordini supportano componenti BoM in `vendite.ordini_righe_componenti`, e
anche i componenti hanno `iva_id`, `quantita`, `prezzo_unitario`, `attivo`.

Decisione per il pilot ordini: il riepilogo IVA usa **solo `ordini_righe`**.
I componenti non entrano direttamente nel riepilogo per evitare doppio conteggio:
il pattern BoM CASO A ricalcola il `prezzo_unitario` della riga padre dai figli
attivi, mentre l'IVA documentale resta sulla riga ordine. Se in futuro il
documento ordine dovesse esporre componenti come righe fiscalmente autonome, la
vista va riprogettata prima di cambiare il riepilogo.

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

Creare viste dedicate, ma solo per le sorgenti abilitate:

```text
vendite.vw_ordini_riepilogo_iva
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

Preferenza WIP: **Opzione A con normalizzazione esplicita per sorgente**,
applicata ora solo a `ORDINE_VENDITA`.

Motivo: le sorgenti non sono omogenee. Gli ordini hanno righe con IVA gia'
utilizzabili; contratti e offerte hanno modelli righe/listino diversi. Forzare
subito una funzione dispatcher rischia di nascondere decisioni ancora aperte su
listini, preview e righe documentali effettive.

## 8. Piano DB ordini

Questo piano riguarda solo `ORDINE_VENDITA`. Per `CONTRATTO` e
`OFFERTA_COMMERCIALE` resta una traccia futura separata, da riaprire solo dopo
aver definito una sorgente righe fiscalmente normalizzata.

### Fase 0 - Conferma semantica righe

Decisione gia' presa per il pilot:

- ordini: solo `ordini_righe` attive;
- componenti BoM: non sommati direttamente; contribuiscono solo tramite il
  prezzo ricalcolato della riga padre;
- contratti/offerte: fuori scope.

Esito atteso: una tabella decisionale "sorgente -> righe imponibili" con una
sola sorgente attiva (`ORDINE_VENDITA`).

### Fase 1 - Vista sorgente normalizzata

Creare una vista/funzione per ordini che espone righe imponibili a precisione
piena:

```text
vendite.vw_ordini_righe_iva_base
```

Questa vista deve gia' risolvere:

- righe attive;
- esclusioni;
- bundle/componenti secondo decisione Fase 0: solo padre ordine;
- prezzo effettivo;
- quantita effettiva;
- IVA effettiva;
- eventuale override aliquota da stato emittente.

### Fase 2 - Viste riepilogo IVA

Solo dopo la Fase 1, creare la vista finale:

```text
vendite.vw_ordini_riepilogo_iva
```

Questa vista applica solo aggregazione e rounding per aliquota, sul modello
preventivi.

### Fase 3 - Test pgTAP

Test minimi per ordini:

- nessuna riga attiva -> nessun riepilogo;
- due righe stessa IVA -> una riga riepilogo;
- due IVA diverse -> due righe riepilogo;
- caso centesimi: IVA calcolata sul totale gruppo, non per riga;
- righe inattive/escluse -> fuori dal riepilogo;
- componente BoM presente -> nessun doppio conteggio, perche' si somma solo la
  riga padre ordine;
- coerenza con totale testata quando la testata ha gia' totali.

Test specifico anti-regressione:

```text
due righe con stessa IVA e imponibili che producono differenza tra:
SUM(ROUND(riga, 2)) e ROUND(SUM(riga), 2)
```

Il test deve confermare che vince `ROUND(SUM(...), 2)`.

### Fase 4 - Backend successivo

Dopo il landing DB, aggiungere nel repository ordini:

```text
OrdiniRepository.list_riepilogo_iva(ordine_id)
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

Decisione ordini: per il riepilogo IVA si somma solo la riga padre
`ordini_righe`. I componenti sono dettaglio tecnico/prezzo del padre, non righe
IVA autonome del documento ordine.

### 9.2 IVA mancante su contratti/offerte righe principali

`contratti_righe` e `offerte_commerciali_eccezioni` non espongono `iva_id` sulla
riga principale. Se una riga senza componenti deve produrre IVA, la vista deve
risolvere l'IVA dall'articolo/listino/prezzo resolver oppure va introdotto uno
snapshot IVA.

Decisione: contratti/offerte fuori scope. La fonte autorevole dell'IVA per righe
contratto/offerta standalone va definita in un'analisi dedicata prima di
implementare un riepilogo.

### 9.3 Contratti preview senza IVA

`fn_contratto_righe_preview` e' la sorgente corretta per il documento contratto
A/B, ma oggi non sembra esporre una IVA normalizzata per ogni riga preview.

Decisione: fuori scope. Estendere la preview o creare una funzione parallela
resta requisito futuro, non parte del pilot ordini.

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

Procedere in modo incrementale con il riepilogo IVA solo per
`ORDINE_VENDITA`.

Motivi:

- `ORDINE_VENDITA` ha righe con `iva_id`, quantita, prezzo, sconto e stato
  `attivo`; la decisione bundle/componenti e' chiusa usando solo la riga padre;
- `CONTRATTO` non ha una sorgente righe fiscalmente uniforme tra modalita' A/B/C;
- `OFFERTA_COMMERCIALE` oggi stampa solo eccezioni, quindi un riepilogo IVA
  sarebbe semanticamente parziale;
- nessuno di questi documenti e' fiscale nel senso forte che giustifica uno
  snapshot IVA dedicato come per fatture o, per continuita' di processo,
  preventivi.

Sequenza consigliata:

1. creare `vendite.vw_ordini_righe_iva_base`;
2. creare `vendite.vw_ordini_riepilogo_iva`;
3. applicare la formula dei preventivi senza arrotondamento per riga;
4. aggiungere test pgTAP sui centesimi e sui componenti BoM;
5. cablare `OrdiniRepository.list_riepilogo_iva`;
6. aggiungere `riepilogo_iva` al context `ORDINE_VENDITA`.

La regola non negoziabile e' il rounding: prima totalizzazione per aliquota, poi
calcolo IVA sul gruppo, come nei preventivi.

## 11. Piano esecutivo DB - `ORDINE_VENDITA`

Obiettivo operativo: predisporre una vista DB da cui il backend possa estrarre
il riepilogo IVA di un ordine, replicando la logica fiscale gia' applicata ai
preventivi ma senza introdurre una tabella fisica `ordini_riepiloghi_iva`.

### 11.1 Oggetto DB da creare

Creare una migration Liquibase v2 in:

```text
db/changelog/migrations_v2/20_code/vendite/YYYYMMDD-NN-create-vw-ordini-riepilogo-iva-dettaglio-mctit.yaml
```

Oggetto:

```text
vendite.vw_ordini_riepilogo_iva_dettaglio
```

La vista deve essere il contratto DB letto dal backend. Shape consigliata,
allineata a `vw_preventivi_riepilogo_iva_dettaglio` dove applicabile:

```text
ordine_id
iva_id
iva_codice
iva_descrizione
iva_aliquota
natura_id          -- NULL per ordini, finche' non esiste snapshot natura
natura_codice      -- NULL per ordini
esigibilita        -- NULL per ordini
split_payment      -- NULL per ordini
imponibile
imposta
arrotondamento
totale_riga
```

Non serve un `id` tecnico persistente: il riepilogo e' derivato e la chiave
logica della riga e' `(ordine_id, iva_id, iva_aliquota)`.

### 11.2 Formula SQL da usare

La vista deve calcolare direttamente da `vendite.ordini_righe` attive:

```sql
WITH ordine_stato AS (
  SELECT
    o.id AS ordine_id,
    s.stato_id AS stato_emittente_id
  FROM vendite.ordini o
  LEFT JOIN anagrafiche.emittenti_fiscali ef
    ON ef.id = o.emittente_fiscale_id
  LEFT JOIN anagrafiche.soggetti_ruoli sr
    ON sr.id = ef.soggetto_ruolo_id
  LEFT JOIN anagrafiche.soggetti s
    ON s.id = sr.soggetto_id
),
righe AS (
  SELECT
    r.ordine_id,
    r.iva_id,
    CASE
      WHEN r.iva_id IS NOT NULL
      THEN config.fn_get_aliquota_iva(r.iva_id, os.stato_emittente_id)
      ELSE NULL::numeric
    END AS aliquota_effettiva,
    r.quantita * r.prezzo_unitario
      * (1 - COALESCE(r.sconto_perc, 0) / 100) AS imponibile_riga_full
  FROM vendite.ordini_righe r
  JOIN ordine_stato os
    ON os.ordine_id = r.ordine_id
  WHERE r.attivo IS TRUE
    AND r.quantita > 0
),
aggregati AS (
  SELECT
    ordine_id,
    iva_id,
    aliquota_effettiva,
    ROUND(SUM(imponibile_riga_full), 2) AS imponibile,
    ROUND(
      ROUND(SUM(imponibile_riga_full), 2)
      * COALESCE(aliquota_effettiva, 0) / 100,
      2
    ) AS imposta,
    SUM(imponibile_riga_full) - ROUND(SUM(imponibile_riga_full), 2)
      AS arrotondamento
  FROM righe
  GROUP BY ordine_id, iva_id, aliquota_effettiva
)
SELECT
  a.ordine_id,
  a.iva_id,
  i.codice AS iva_codice,
  i.descrizione AS iva_descrizione,
  a.aliquota_effettiva AS iva_aliquota,
  NULL::integer AS natura_id,
  NULL::text AS natura_codice,
  NULL::char(1) AS esigibilita,
  NULL::boolean AS split_payment,
  a.imponibile,
  a.imposta,
  a.arrotondamento,
  a.imponibile + a.imposta AS totale_riga
FROM aggregati a
LEFT JOIN config.iva i
  ON i.id = a.iva_id;
```

Regole da mantenere:

- non usare `ROUND(imponibile_riga_full, 2)` prima della `SUM`;
- calcolare `imposta` sull'imponibile aggregato e arrotondato del gruppo IVA;
- usare `config.fn_get_aliquota_iva(...)` come nei preventivi, per mantenere
  l'override aliquota da stato emittente;
- non sommare `ordini_righe_componenti`: i componenti alimentano il prezzo della
  riga padre tramite trigger, ma non sono righe IVA autonome nel riepilogo
  ordine;
- non filtrare silenziosamente righe con `iva_id IS NULL`: il `CASE` evita di
  invocare `config.fn_get_aliquota_iva(NULL, ...)`, ma la riga aggregata con
  IVA nulla resta visibile come problema dati/configurazione.

Se la RLS sugli ordini e' attiva nel perimetro interessato, creare la view con
`WITH (security_invoker=on)` seguendo il pattern delle viste lista recenti.

### 11.3 Test pgTAP

Creare un test dedicato, ad esempio:

```text
db/pgtap/vendite/test-vw-ordini-riepilogo-iva-dettaglio.sql
```

Casi minimi:

- ordine senza righe attive -> nessuna riga riepilogo;
- due righe attive con stessa IVA -> una sola riga riepilogo;
- due aliquote diverse -> due righe riepilogo;
- caso centesimi -> vince `ROUND(SUM(imponibile_riga_full), 2)`, non
  `SUM(ROUND(imponibile_riga_full, 2))`;
- riga inattiva esclusa;
- riga con componenti BoM -> nessun doppio conteggio, il riepilogo somma solo
  `ordini_righe`;
- override aliquota da stato emittente, se fixture disponibili.

### 11.4 Contratto backend

Dopo il landing DB, aggiungere in `OrdiniRepository`:

```python
def list_riepilogo_iva(self, ordine_id: int) -> list[dict[str, Any]]:
    ...
```

Query prevista:

```sql
SELECT ordine_id, iva_id, iva_codice, iva_descrizione,
       iva_aliquota, natura_id, natura_codice,
       esigibilita, split_payment,
       imponibile, imposta, arrotondamento, totale_riga
FROM vendite.vw_ordini_riepilogo_iva_dettaglio
WHERE ordine_id = %s
ORDER BY iva_aliquota NULLS LAST, iva_id NULLS LAST;
```

Poi il builder `ORDINE_VENDITA` aggiunge:

```python
"riepilogo_iva": self._repo.list_riepilogo_iva(sorgente_id)
```

Il backend deve solo leggere la view; nessun calcolo IVA in Python e nessuna
formula nei template.

## 12. Decisione 2026-06-05 - totalizzazione ordine via trigger (totali in testata) + riepilogo IVA live nel drawer

> Estensione richiesta da Tid dopo analisi delle due domande: (1) la scelta di
> NON storicizzare il riepilogo IVA dell'ordine (vista derivata vs tabella fisica
> dei preventivi); (2) mostrare nel drawer di gestione righe il riepilogo IVA
> aggiornato in tempo reale, come sui preventivi. L'analisi ha fatto emergere un
> nodo a monte (i totali di testata ordine non sono gestiti): le due cose si
> chiudono insieme.
>
> **Iter decisionale**: una prima ipotesi «tutto derivato» (drop colonne `*_tot`,
> totali calcolati in vista) e' stata **scartata dopo verifica dei consumer e del
> pattern di famiglia** (12.2bis). Decisione finale ratificata (Tid, 2026-06-05):
> **niente drop; vista riepilogo IVA come single source del breakdown + trigger di
> ricalcolo che persiste i totali in testata** (clone del pattern preventivi).

### 12.1 Esito verifica - i totali di testata ordine oggi NON sono gestiti

Verifica statica (doc dbzero + codice BE) su come `vendite.ordini` popola
`imponibile_tot`, `sconto_tot`, `iva_tot`, `totale_doc`:

- **non esiste** `vendite.fn_ricalcola_totali_ordine` (a differenza di
  `fn_ricalcola_totali_preventivo`);
- **non esiste** alcun trigger su `vendite.ordini_righe` che ricalcoli i totali di
  testata (i trigger presenti coprono check parent, qta-da-operativa, propagazione
  qta componenti, storico - nessun ricalcolo totali);
- il **service Python non calcola** i totali;
- il commento in `backend/apps/vendite/db/ordini_repository.py` dichiara «il
  ricalcolo totali e' gestito da trigger DB su ordini_righe» - **inaccurato**: quel
  trigger non c'e'.

Conseguenza: le colonne `*_tot` sono di fatto **NULL** in testata ordine; la vista
lista (`vw_ordini_lista`, legge `o.imponibile_tot/iva_tot/totale_doc/sconto_tot`
diretti dalla testata) le espone vuote, e il context builder PDF
(`ordine_document_context_builder.py`, blocco `"totali"`) propaga NULL.
**Va confermato sul DB di lavoro** prima del brief, ma il segnale e' netto. E' una
**lacuna di modello** (`feedback_bug_logici_modello`): le colonne esistono e i
consumer le leggono, ma nessuno le valorizza.

### 12.2 Principio dei preventivi da preservare (la single source, non la tabella)

Il valore del modello preventivi non e' la tabella fisica
`preventivi_riepiloghi_iva`, ma il fatto che **una sola funzione produce sia il
riepilogo IVA sia i totali di testata**: `fn_ricalcola_totali_preventivo` invoca
`fn_ricalcola_riepilogo_iva_preventivo` e poi **somma il riepilogo** per scrivere i
totali. Riepilogo e testata sono **coerenti per costruzione** (stessa fonte, stesso
rounding per gruppo aliquota). Un trigger statement-level
(`trgfn_preventivi_righe_ricalcola_totali`) lo invoca a ogni mutazione riga.

La tabella fisica preventivi si giustifica solo perche' il preventivo e' **sorgente
fiscale per processo** (-> fattura, consistenza al centesimo persistita nel tempo).
L'ordine non ha questo requisito (la sorgente fiscale e' la fattura a valle; lo
snapshot al momento della stampa e' gia' coperto dal context salvato in
`documenti_generati`, cfr. 9.5). Quindi: **niente tabella fisica del riepilogo**,
ma i **totali aggregati restano persistiti in testata** (denormalizzazione di
servizio), mantenuti coerenti dal trigger - esattamente come i preventivi.

### 12.2bis Perche' NON si droppano le colonne `*_tot` (verifica consumer + famiglia)

L'ipotesi iniziale «drop colonne, tutto derivato in vista» e' stata **scartata** su
base fattuale.

**Pattern della famiglia vendite** (verificato su tabelle + viste lista dbzero): tra
i documenti che HANNO totali, la denormalizzazione in testata e' la **norma al
100%**:

| Documento           | Totali in testata                                   | Ricalcolo                            | Vista lista                                  |
| ------------------- | --------------------------------------------------- | ------------------------------------ | -------------------------------------------- |
| Preventivi          | si (`totale_imponibile/iva/documento`)              | **trigger automatico** su righe      | legge la colonna                             |
| Fatture             | si (`imponibile_tot/imposta_tot/totale_doc`)        | esplicito (pipeline pre-numerazione) | legge la colonna                             |
| Ordini              | si (`imponibile_tot/sconto_tot/iva_tot/totale_doc`) | **mancante** (la lacuna 12.1)        | legge la colonna                             |
| Offerte / Contratti | **no**                                              | -                                    | - (modello listino+eccezioni, niente totali) |

Offerte/contratti non fanno testo (non hanno totali del tutto). Droppando, l'ordine
sarebbe **l'unico documento con totali senza totali in testata** - outlier. Inoltre
il manuale dbzero `manual/ordini.md` **documenta gia'** la persistenza: «i totali
sono memorizzati per prestazioni e confronti di audit».

**Consumer delle colonne `*_tot` ordine** (blast radius del drop):

- *Impatto reale*: `vw_ordini_lista` (legge `o.*_tot`), `OrdiniRepository`
  (whitelist `order_by=totale_doc` + `get_ordine`/`list_ordini`), context builder
  PDF (`testata.get("*_tot")`), catalogo `ui.lista_colonna` (`totale_doc` priorita'
  80, `imponibile_tot/iva_tot` opt-in). Il drop costringerebbe **tutti** questi a
  cambiare (vista lista da rifare con join, `order_by` da colonna a espressione
  derivata, ecc.).
- *Nessun impatto*: il **push a commessa** (`fn_list_ordini_da_pushare` +
  `HandlerOrdini`) lavora **sulle righe**, non sui totali; il **DDT** a valle
  (`vendite.ddt_ordini`) e' un link N:N con totali propri; il **FE** non legge i
  totali direttamente.

Tenere le colonne -> **blast radius zero** su quei consumer; basta aggiungere il
pezzo mancante (il trigger). Droppare comprava solo «niente colonne» (estetico),
contro il modello documentato e la famiglia. Decisione: **tenere e valorizzare**.

### 12.3 Decisione ratificata (Tid, 2026-06-05): totali in testata via trigger, clone preventivi

La **vista riepilogo IVA** e' la single source del breakdown per aliquota; i
**totali di testata restano colonne persistite**, valorizzate da un trigger che
**somma la vista** (mai una formula parallela). Modello = gemello dei preventivi,
ma **senza tabella fisica del riepilogo** (la vista ricalcola dalle righe al volo;
il trigger persiste solo i 3-4 totali aggregati in testata).

- **Nessun drop** di `imponibile_tot/sconto_tot/iva_tot/totale_doc`.
- Rounding **non negoziabile**: per gruppo aliquota (`ROUND(SUM(imponibile_riga))`
  poi imposta sul gruppo), mai per riga - identico ai preventivi.
- Coerenza per costruzione: testata, lista, PDF e pannello drawer derivano tutti
  dalla **stessa vista**.

### 12.4 Impatto DB (azione team DB -> brief su `dev/db-tid`)

Tutte azioni DB (DDL + viste + funzioni + trigger): brief al team DB, BE/FE
attendono la consegna (`feedback_db_actions_passaggio_team` +
`feedback_be_fe_attende_prerequisiti_db`).

1. **Vista sorgente normalizzata** `vendite.vw_ordini_righe_iva_base` (Fase 1, 8.x):
   righe attive `quantita > 0`, imponibile riga a precisione piena, IVA effettiva
   via `config.fn_get_aliquota_iva(iva_id, stato_emittente_id)`, **solo riga padre
   ordine** (componenti BoM esclusi - alimentano il prezzo del padre, non sono
   righe IVA autonome).
2. **Vista riepilogo IVA** `vendite.vw_ordini_riepilogo_iva_dettaglio` (11.1):
   aggregazione per aliquota con la formula 11.2, shape allineata a
   `vw_preventivi_riepilogo_iva_dettaglio` (natura/esigibilita/split = NULL per
   ordini). E' la single source del breakdown.
3. **Funzione `vendite.fn_ricalcola_totali_ordine(p_ordine_id)`** (NUOVA, clone di
   `fn_ricalcola_totali_preventivo`): **somma la vista riepilogo** e fa UPDATE di
   `imponibile_tot`, `iva_tot`, `totale_doc` sulla testata. Lo **sconto totale**
   non e' derivabile dalla sola somma imponibili (l'imponibile incorpora gia' lo
   sconto riga): la funzione calcola `sconto_tot = SUM(quantita*prezzo) - imponibile`
   (lordo - imponibile) dalle righe, per valorizzare anche quella colonna.
4. **Trigger statement-level su `vendite.ordini_righe`** (AFTER INS/UPD/DLT, clone
   di `trgfn_preventivi_righe_ricalcola_totali`) che invoca
   `fn_ricalcola_totali_ordine` per gli ordini coinvolti (UNION new/old su UPDATE).
   **Dettaglio fine**: l'aliquota effettiva dipende dallo stato dell'emittente
   (`fn_get_aliquota_iva`), quindi il ricalcolo deve scattare **anche su
   `UPDATE OF emittente_fiscale_id`** della testata `vendite.ordini`, non solo sulle
   righe (altrimenti cambiare emittente lascia l'IVA testata stantia). Verificare se
   i preventivi coprono gia' questo caso e replicare/estendere.
5. **`vw_ordini_lista` INVARIATA**: continua a leggere `o.*_tot` dalla testata, ora
   valorizzate dal trigger. Nessun refactor, nessun churn catalogo.
6. **Nessun drop colonne**, nessun DDL distruttivo.
7. **pgTAP**: vista riepilogo (nessuna riga -> nessun riepilogo; stessa IVA -> una
   riga; IVA diverse -> N righe; caso centesimi `ROUND(SUM)` vince su `SUM(ROUND)`;
   riga inattiva esclusa; componente BoM -> nessun doppio conteggio) **+** trigger
   totali (dopo INS/UPD/DLT riga la testata e' coerente con la somma del riepilogo;
   cambio emittente ricalcola l'IVA testata).

### 12.5 Impatto BE (a landing DB)

- `OrdiniRepository.list_riepilogo_iva(ordine_id)` (clone preventivi, lettura pura
  dalla vista - 11.4) per il pannello drawer e il PDF;
- `OrdiniRepository.get_ordine` / `list_ordini`: **invariati** - i totali restano
  colonne di testata/vista lista, gia' selezionate;
- context builder `ORDINE_VENDITA`: aggiungere solo `"riepilogo_iva"`; il blocco
  `"totali"` resta da `testata.get("*_tot")` (ora valorizzate) - **nessuna modifica
  alla derivazione totali**;
- **endpoint** `GET /api/v1/vendite/ordini/<id>/riepilogo-iva/`
  (`ApiOrdineRiepilogoIva`, clone di `ApiPreventivoRiepilogoIva`) per alimentare il
  pannello live nel drawer;
- nessun calcolo IVA/totali in Python (filosofia DB-first): il BE legge vista +
  colonne;
- **correggere** (rendere vero) il commento sul «trigger DB ricalcolo totali» in
  `ordini_repository.py`: ora il trigger esiste davvero.

### 12.6 Drawer FE - riepilogo IVA live (riuso BB, regola del 2)

- **Nessun componente nuovo**: `RiepilogoIvaTable.vue` e' gia' un BB generico in
  `src/core/components/` (cross-dominio, gia' usato dai preventivi). Si monta in
  `OrdiniDrawer` sotto le righe, gemello di `PreventiviDrawer`.
- **API/store**: `getRiepilogoIva(ordineId)` in `ordiniApi.js` + action
  `loadRiepilogoIva` nello store ordini + ref reactive nel drawer (clone 1:1
  preventivi).
- **Refresh live**: ricarica del riepilogo sull'evento `@changed` di
  `OrdiniRigheTable` (gia' presente la catena `changed -> loadDetail`). Dopo il save
  riga il trigger DB ha gia' aggiornato testata e la vista riflette le righe
  correnti -> riepilogo e totale documento freschi e coerenti.
- **Vincolo**: serve `effectiveOrdineId` (ordine gia' in BOZZA) -> coerente con
  l'auto-save BOZZA gia' adottato.
- **Coerenza UX**: pannello riepilogo e totale documento del drawer coincidono per
  costruzione, perche' entrambi derivano dalla stessa vista (12.3) - e' il motivo
  per cui 12.3 e 12.6 sono lo stesso lavoro.

### 12.7 La vista riepilogo IVA fa triplo servizio

Una sola vista alimenta: (a) il `riepilogo_iva` del PDF ordine e del pannello
drawer; (b) il pannello live nel drawer; (c) - via `fn_ricalcola_totali_ordine` -
i totali persistiti in testata (lista/detail/PDF). Single source piena, zero
formule duplicate, totali in testata come tutta la famiglia.

### 12.8 Sequenza aggiornata `ORDINE_VENDITA`

1. (DB) `vw_ordini_righe_iva_base` -> `vw_ordini_riepilogo_iva_dettaglio` ->
   `fn_ricalcola_totali_ordine` (somma la vista) -> trigger su `ordini_righe`
   (+ `UPDATE OF emittente_fiscale_id`); `vw_ordini_lista` **invariata**; pgTAP
   riepilogo + trigger totali.
2. (BE) repo `list_riepilogo_iva` + context builder `riepilogo_iva` + endpoint
   `riepilogo-iva`; `get_ordine`/totali invariati; correggere il commento repo.
3. (FE) `RiepilogoIvaTable` nel drawer + api/store + refresh su `@changed`.

Prerequisito DB (1) prima di BE (2) e FE (3).

### 12.9 Checklist esecutiva step-by-step

Usare questa checklist come ordine operativo. Ogni step deve essere chiuso e
validato prima di passare al successivo.

#### Step 0 - Verifica preliminare

- confermare su DB di lavoro che `vendite.ordini.imponibile_tot`,
  `sconto_tot`, `iva_tot`, `totale_doc` siano oggi non valorizzate o stantie;
- verificare trigger esistenti su `vendite.ordini_righe` e
  `vendite.ordini`, per evitare doppioni;
- confermare che `vendite.ordini_righe.iva_id`, `quantita`,
  `prezzo_unitario`, `sconto_perc`, `attivo` siano la sorgente corretta.

#### Step 1 - View base righe IVA ordine

Creare migration `20_code/vendite` per:

```text
vendite.vw_ordini_righe_iva_base
```

Regole:

- solo `ordini_righe` attive con `quantita > 0`;
- imponibile riga a precisione piena;
- aliquota effettiva via `config.fn_get_aliquota_iva(...)`;
- `CASE` su `iva_id IS NULL`, per non invocare la funzione con parametro nullo;
- nessun join diretto a `ordini_righe_componenti`;
- `WITH (security_invoker=on)` se coerente con RLS ordini.

#### Step 2 - View riepilogo IVA ordine

Creare migration `20_code/vendite` per:

```text
vendite.vw_ordini_riepilogo_iva_dettaglio
```

Regole:

- aggregare `vw_ordini_righe_iva_base` per `ordine_id`, `iva_id`,
  `aliquota_effettiva`;
- `imponibile = ROUND(SUM(imponibile_riga_full), 2)`;
- `imposta = ROUND(imponibile * aliquota_effettiva / 100, 2)`;
- `totale_riga = imponibile + imposta`;
- shape compatibile col BE e simile a `vw_preventivi_riepilogo_iva_dettaglio`.

#### Step 3 - Funzione totali testata ordine

Creare migration `20_code/vendite` per:

```text
vendite.fn_ricalcola_totali_ordine(
  p_ordine_id vendite.ordini.id%TYPE
)
```

Regole:

- usare `%TYPE` in firma, `RETURNS TABLE` e variabili `DECLARE`;
- guard: `p_ordine_id IS NULL OR p_ordine_id <= 0` deve sollevare errore;
- sommare la view riepilogo IVA per `imponibile_tot`, `iva_tot`,
  `totale_doc`;
- calcolare `sconto_tot` come lordo righe meno imponibile aggregato;
- aggiornare `vendite.ordini`;
- ritornare i totali aggiornati.

#### Step 4 - Trigger ricalcolo da righe ordine

Creare migration `20_code/vendite` per trigger function e trigger:

```text
vendite.trgfn_ordini_righe_ricalcola_totali()
trg_ordini_righe_z90_ricalcola_totali_ins
trg_ordini_righe_z90_ricalcola_totali_upd
trg_ordini_righe_z90_ricalcola_totali_dlt
```

Regole:

- clone del pattern `trgfn_preventivi_righe_ricalcola_totali`;
- statement-level con transition tables;
- ricalcolo per `DISTINCT ordine_id`;
- su UPDATE ricalcolare sia `old_rows` sia `new_rows`.

#### Step 5 - Trigger ricalcolo da testata ordine

Creare migration `20_code/vendite` per ricalcolo su cambio campi testata che
impattano l'aliquota effettiva o il perimetro fiscale:

```text
trg_ordini_z90_ricalcola_totali_upd
```

Regole:

- almeno `UPDATE OF emittente_fiscale_id`;
- valutare se includere anche altri campi testata che impattano la catena
  emittente/stato;
- invocare `vendite.fn_ricalcola_totali_ordine(NEW.id)`.

#### Step 6 - pgTAP DB

Creare test DB dedicati per:

- view riepilogo IVA;
- funzione totali;
- trigger su righe;
- trigger su cambio emittente.

Casi obbligatori:

- stessa IVA -> una riga riepilogo;
- IVA diverse -> piu' righe;
- caso centesimi `ROUND(SUM)` vs `SUM(ROUND)`;
- riga inattiva esclusa;
- componente BoM senza doppio conteggio;
- testata coerente dopo INSERT/UPDATE riga;
- trigger DELETE riga verificato strutturalmente: l'hard-delete di
  `vendite.ordini_righe` e' bloccato dal guard `trg_ordini_righe_a10_block_dlt`;
- testata ricalcolata dopo cambio emittente.

#### Step 7 - Validazione DB

Eseguire:

```text
cd db
../scripts/liquibase5.sh --defaultsFile=liquibase.properties validate
```

Non eseguire `update` senza conferma esplicita.

### 12.10 Attivita' DB svolte - chiusura esecutiva 2026-06-05

Esecuzione completata sul perimetro **solo DB**. BE e FE restano fuori scope di
questa tranche.

#### Migration create

Sono state create 5 migration in `db/changelog/migrations_v2/20_code/vendite`:

| Step | File | Oggetto |
| --- | --- | --- |
| 1 | `20260605-01-create-vw-ordini-righe-iva-base-mctit.yaml` | `vendite.vw_ordini_righe_iva_base` |
| 2 | `20260605-02-create-vw-ordini-riepilogo-iva-dettaglio-mctit.yaml` | `vendite.vw_ordini_riepilogo_iva_dettaglio` |
| 3 | `20260605-03-create-fn-ricalcola-totali-ordine-mctit.yaml` | `vendite.fn_ricalcola_totali_ordine(p_ordine_id)` |
| 4 | `20260605-04-create-trg-ordini-righe-ricalcola-totali-mctit.yaml` | trigger function e trigger `_z90_` su `vendite.ordini_righe` |
| 5 | `20260605-05-create-trg-ordini-ricalcola-totali-mctit.yaml` | trigger function e trigger `_z90_` su `vendite.ordini` |

#### Oggetti DB consegnati

- `vendite.vw_ordini_righe_iva_base`
  - righe ordine attive (`attivo IS TRUE`) e `quantita > 0`;
  - imponibile lordo, sconto e imponibile netto a precisione piena;
  - aliquota effettiva via `config.fn_get_aliquota_iva(iva_id, stato_emittente_id)`;
  - nessun join diretto a `vendite.ordini_righe_componenti`, per evitare doppio
    conteggio BoM.
- `vendite.vw_ordini_riepilogo_iva_dettaglio`
  - aggregazione per `ordine_id`, `iva_id`, `aliquota_effettiva`;
  - `imponibile = ROUND(SUM(imponibile_riga_full), 2)`;
  - `imposta = ROUND(imponibile * aliquota_effettiva / 100, 2)`;
  - nessun `id` tecnico derivato;
  - shape pronta per BE/PDF/drawer.
- `vendite.fn_ricalcola_totali_ordine`
  - firma, `RETURNS TABLE` e variabili allineate a `%TYPE`;
  - guard su `p_ordine_id IS NULL OR <= 0`;
  - aggiorna `vendite.ordini.imponibile_tot`, `sconto_tot`, `iva_tot`,
    `totale_doc`;
  - `sconto_tot = lordo righe arrotondato - imponibile aggregato`.
- `vendite.trgfn_ordini_righe_ricalcola_totali`
  - trigger statement-level con transition tables;
  - ricalcolo per `DISTINCT ordine_id`;
  - su UPDATE considera sia `old_rows` sia `new_rows`;
  - trigger DELETE registrato, ma il caso funzionale di hard-delete righe resta
    bloccato dal guard esistente `trg_ordini_righe_a10_block_dlt`.
- `vendite.trgfn_ordini_ricalcola_totali`
  - trigger `AFTER UPDATE OF emittente_fiscale_id`;
  - ricalcola la testata se cambia l'emittente fiscale, per riallineare eventuali
    override aliquota da stato emittente.

#### pgTAP

Creato test dedicato:

```text
db/pgtap/vendite/test-ordini-riepilogo-iva-totali.sql
```

Casi coperti:

- presenza delle due view e della funzione;
- presenza trigger su righe e testata;
- ordine senza righe -> totali zero;
- stessa IVA -> una sola riga riepilogo;
- IVA diverse -> piu' righe riepilogo;
- centesimi: `ROUND(SUM(...), 2)` e non `SUM(ROUND(..., 2))`;
- riga con `attivo = false` esclusa dal riepilogo;
- trigger UPDATE riga riallinea i totali testata;
- trigger DELETE verificato strutturalmente, perche' l'hard-delete di
  `vendite.ordini_righe` e' vietato dal guard `_a10_`;
- cambio `emittente_fiscale_id` ricalcola i totali;
- BoM senza doppio conteggio: la view base non legge
  `ordini_righe_componenti`;
- guard funzione su parametro nullo.

Esito test comunicato da shell DB:

```text
scripts/testpgtap.sh db/pgtap/vendite/test-ordini-riepilogo-iva-totali.sql
```

verde dopo gli aggiustamenti fixture:

- righe ordine create con `qta_operativa` e `uom_operativa_id`, coerenti col
  trigger `script.trgfn_qta_from_operativa`;
- caso DELETE convertito da test funzionale a verifica strutturale, perche'
  `vendite.ordini_righe` non ammette hard-delete.

#### Validazioni

Eseguite:

```text
git diff --check
cd db
../scripts/liquibase5.sh --defaultsFile=liquibase.properties validate
```

Esito: nessun errore di validazione Liquibase.

Non e' stato eseguito `liquibase update` in questa sessione senza conferma
esplicita.

#### Documentazione

Create/aggiornate le documentazioni manuali:

```text
docs/it/dbzero/vendite/manual/vw_ordini_righe_iva_base.md
docs/it/dbzero/vendite/manual/vw_ordini_riepilogo_iva_dettaglio.md
docs/it/dbzero/vendite/manual/fn_ricalcola_totali_ordine.md
docs/it/dbzero/vendite/manual/trgfn_ordini_righe_ricalcola_totali.md
docs/it/dbzero/vendite/manual/trgfn_ordini_ricalcola_totali.md
```

Sono stati inoltre generati/aggiornati i corrispondenti file di documentazione
tecnica DB (`views/`, `funzioni/`, indici/tabelle) tramite tooling docs.

#### Fuori scope di questa esecuzione DB

BE e FE non sono parte di questa esecuzione. Restano come note di impatto nei
punti 12.5 e 12.6, ma la checklist operativa qui si chiude con la validazione DB.

---

## 13. Piano di sviluppo BE + FE (post-consegna DB, 2026-06-05)

> Aggiornato dopo la consegna DB (12.10). Obiettivo: portare nel **drawer ordini**
> e nella **stampa PDF** un riepilogo IVA *simil-preventivi*, consumando gli oggetti
> DB gia' atterrati. Tutto **clone della catena preventivi** (regola del 2,
> `feedback_regola_del_2_estrai_bb`); zero logica fiscale in Python o nei template
> (DB-first). Branch `dev/backend-tid`.

### 13.0 Stato di partenza e prerequisiti

**Oggetti DB consegnati e utilizzabili** (12.10):

- `vendite.vw_ordini_riepilogo_iva_dettaglio` - breakdown per aliquota. **Shape
  identica a `vw_preventivi_riepilogo_iva_dettaglio`** salvo: chiave
  `ordine_id` (non `preventivo_id`) e **nessun `id` tecnico**, nessun
  `data_insert/_update`. Colonne: `ordine_id, iva_id, iva_codice, iva_descrizione,
  iva_aliquota, natura_id, natura_codice, esigibilita, split_payment, imponibile,
  imposta, arrotondamento, totale_riga`.
- `vendite.vw_ordini_righe_iva_base` - sorgente normalizzata (uso interno della
  funzione totali; il BE non la consuma direttamente).
- `vendite.fn_ricalcola_totali_ordine(p_ordine_id)` - scrive
  `imponibile_tot/sconto_tot/iva_tot/totale_doc` in `vendite.ordini`.
- trigger `_z90_` su `ordini_righe` (INS/UPD/DLT) e su `ordini`
  (`UPDATE OF emittente_fiscale_id`).

**Prerequisiti da chiudere PRIMA del BE** (azione DB / OK Tid - non li esegue il BE,
`feedback_db_actions_passaggio_team` + `feedback_be_fe_attende_prerequisiti_db`):

1. ✅ **Applicare le migration** al DB di lavoro — **FATTO** (Tid, 2026-06-05:
   «apply migration fatto, c'e' tutto»). Viste/funzione/trigger runtime disponibili.
2. ✅ **Backfill totali ordini esistenti** — **NON NECESSARIO** (Tid: un solo ordine
   di test). Resta valido per ambienti con storico ordini: ricalcolo una-tantum
   `SELECT vendite.fn_ricalcola_totali_ordine(id) FROM vendite.ordini`.

### 13.1 BE - Repository (`apps/vendite/db/ordini_repository.py`)

Clone di `PreventiviRepository.list_riepilogo_iva` (preventivi_repository.py:431-443):

- `list_riepilogo_iva(self, ordine_id: int) -> list[dict]` - lettura pura da
  `vendite.vw_ordini_riepilogo_iva_dettaglio WHERE ordine_id = %s`,
  `ORDER BY iva_aliquota NULLS LAST, iva_id NULLS LAST`.
- **Differenze dalla versione preventivi**: SELECT **senza `id`** (la vista ordini
  non lo espone) e `ordine_id` al posto di `preventivo_id`. Colonne selezionate:
  `ordine_id, iva_id, iva_codice, iva_descrizione, iva_aliquota, natura_id,
  natura_codice, esigibilita, split_payment, imponibile, imposta, arrotondamento,
  totale_riga`.
- Guard standard post-cursor (`rows_to_list`).
- **Correggere** il commento fuorviante in testa al repo («ricalcolo totali gestito
  da trigger DB»): ora e' **vero** (12.5) - aggiornare il testo, non rimuoverlo.
- `get_ordine` / `list_ordini`: **invariati** - i `*_tot` restano colonne di
  testata/vista lista, ora valorizzate dal trigger.

### 13.2 BE - Service (`apps/vendite/services/ordini_service.py`)

Wrapper sottile, clone di `preventivi_service.list_riepilogo_iva` (:263-265):

```text
def list_riepilogo_iva(ordine_id): return OrdiniRepository().list_riepilogo_iva(ordine_id)
```

### 13.3 BE - Endpoint (`apps/vendite/api/views_ordini.py` + `urls_ordini.py`)

Clone di `ApiPreventivoRiepilogoIva` (preventivi_views.py:763-788) +
rotta (preventivi_urls.py:137-141):

- `class ApiOrdineRiepilogoIva(DomainAPIView)`, `area_funzionale = "vendite"`
  (livello LETTURA), `@extend_schema` sul `get`.
- `GET /api/v1/vendite/ordini/<int:ordine_id>/riepilogo-iva/` ->
  `success_response(ordini_service.list_riepilogo_iva(ordine_id))`.
- nome rotta `vendite-ordini-riepilogo-iva`.

### 13.4 BE - Context builder PDF (`apps/vendite/services/ordine_document_context_builder.py`)

- aggiungere `"riepilogo_iva": self._repo.list_riepilogo_iva(sorgente_id)` al dict
  di `build_context` (clone preventivo_document_context_builder.py:84/92);
- **rimuovere il commento di confine v1** «niente riepilogo_iva ... (non esiste una
  vista IVA per ordini)»: ora la vista c'e';
- il blocco `"totali"` resta da `testata.get("*_tot")` (ora valorizzate dal
  trigger) - **nessuna modifica alla derivazione totali**.

### 13.5 BE - Test (`apps/vendite/tests/`)

- `test_ordini_api`: smoke route `riepilogo-iva` (auth/area) + shape della response;
- `test_ordine_document_context_builder`: il context include ora `riepilogo_iva`
  (mock repo che ritorna 1-2 gruppi aliquota);
- mock DB (regole CI AGENTS.md, niente DB reale);
- verde `./manage-test.sh apps.vendite.tests -v 2`.

### 13.6 FE - API + store (`src/vendite/ordini/`)

- `api/ordiniApi.js`: `getRiepilogoIva(ordineId)` -> `api.get('${BASE}/${id}/riepilogo-iva/')`
  (clone preventiviApi.js:104-111);
- `stores/ordini.js`: action `loadRiepilogoIva(ordineId)` (clone preventivi.js:169-172).

### 13.7 FE - Drawer con riepilogo IVA live (`OrdiniDrawer.vue`)

Clone del pattern preventivi (PreventiviDrawer.vue:1001-1003 + computed
`showRiepilogoIva` :137-139 + load :374-387). **Nessun componente nuovo**:
`RiepilogoIvaTable.vue` e' gia' BB generico in `src/core/components/`.

- ref `riepilogoIva = ref([])` + computed `showRiepilogoIva` (almeno 1 riga);
- montare `<RiepilogoIvaTable :items="riepilogoIva" :show-subtitle="true" />` sotto
  la sezione righe (con `<Divider/>`), nel tab Testata;
- `loadRiepilogoIva(targetId)` best-effort (catch -> `[]`) chiamata in `loadDetail`;
- **refresh live**: agganciare la ricarica all'evento `@changed` di
  `OrdiniRigheTable` (la catena `changed -> loadDetail` esiste gia' nello scheletro;
  **verificare** che `OrdiniRigheTable` emetta `changed` su save/delete riga e su
  modifica componenti, come `PreventiviRigheTable`);
- vincolo `effectiveOrdineId` (ordine gia' in BOZZA) - coerente con l'auto-save
  BOZZA gia' adottato. Build verde `./node_modules/.bin/vite build`.

### 13.8 Stampa PDF - estendere il template HTML (gestione manuale)

Aggiungere `riepilogo_iva` al context (13.4) **non** lo fa apparire nel PDF finche'
il **template HTML ordine** non lo renderizza. Il template e' gestione **manuale**
(come la sua creazione, 12.1.3): clonare la sezione «Riepilogo IVA» dal template
preventivo nel template `ORDINE_VENDITA`, ripubblicare la versione
(`fn_pubblica_template_documento_versione`). Passo di configurazione operativa, non
codice BE/FE.

### 13.9 Sequenza esecutiva

1. **(DB / OK Tid)** apply migration + backfill totali ordini esistenti (13.0).
2. **(BE)** repo `list_riepilogo_iva` + service + endpoint + context builder +
   test verdi. Commit.
3. **(FE)** api/store + `RiepilogoIvaTable` nel drawer + refresh `@changed` + build
   verde. Commit.
4. **(Config)** estendere + ripubblicare il template PDF ordine (13.8).
5. **Smoke**: drawer carica riepilogo, si aggiorna dopo add/del riga; totali testata
   coerenti col riepilogo; PDF rende la tabella IVA.

### 13.10 Punti di attenzione

- **Coerenza per costruzione** drawer/lista/PDF: tutti derivano dalla stessa vista
  e dalla stessa funzione (12.7) - nessuna formula FE/Python.
- **Ordini vecchi senza backfill** = totali NULL finche' non si tocca una riga: il
  backfill 13.0.2 e' la differenza tra «funziona sui nuovi» e «funziona su tutti».
- **`riga_nr`/righe inattive**: la vista base filtra `attivo IS TRUE AND quantita > 0`
  -> coerente col fatto che il riepilogo segue le righe effettive del documento.
- **Componenti BoM**: esclusi dal riepilogo per design (confluiti nel prezzo padre,
  12.10) - non aggiungere componenti al breakdown lato BE/FE.

### 13.11 Esito esecuzione BE + FE - 2026-06-05

Steps 13.1-13.7 **eseguiti** (branch `dev/backend-tid`). Test BE verdi, build FE
verde, review critica passata. Resta solo 13.8 (template PDF, manuale).

**Backend** (`apps/vendite/`):

- `db/ordini_repository.py` — `list_riepilogo_iva(ordine_id)`: lettura pura da
  `vw_ordini_riepilogo_iva_dettaglio` (SELECT senza `id`, chiave `ordine_id`).
- `services/ordini_service.py` — wrapper `list_riepilogo_iva`.
- `api/views_ordini.py` + `api/urls_ordini.py` — `ApiOrdineRiepilogoIva`
  (`GET /api/v1/vendite/ordini/<id>/riepilogo-iva/`, `area_funzionale='vendite'`,
  `@extend_schema`+`inline_serializer`, rotta `vendite-ordine-riepilogo-iva`).
- `services/ordine_document_context_builder.py` — aggiunto `riepilogo_iva` al
  context; rimosso il commento «confine v1 / niente vista IVA».
- Test: `tests/api/test_ordini_api.py` (smoke endpoint) +
  `tests/services/test_ordine_document_context_builder.py` (context include
  `riepilogo_iva`). **Suite vendite: 866 test verdi.**

**Frontend** (`src/vendite/ordini/` + BB core):

- `api/ordiniApi.js` — `getRiepilogoIva`.
- `stores/ordini.js` — action `loadRiepilogoIva` (store `userScoped`).
- `components/OrdiniDrawer.vue` — montato `RiepilogoIvaTable` (BB core, **zero
  componenti nuovi**) sotto le righe; ref + computed `showRiepilogoIva`; load in
  `loadDetail` + refresh live sull'evento `@changed` delle righe; reset in
  `resetForm`. **Build FE verde.**

**Fix da review critica**: `src/core/components/RiepilogoIvaTable.vue` usava
`data-key="id"`, ma la vista ordini non espone `id` → key duplicate PrimeVue con
≥2 aliquote. Rimosso `data-key` (tabella read-only → indice di riga): il BB e' ora
shape-agnostic (preventivi/ordini/fatture-future), nessuna regressione preventivi.

**Sicurezza** (verificata, nessuna modifica): l'endpoint e' protetto DB-side
(`security_invoker=on` sulle viste + RLS `rls_ordini_ef_whitelist` su
`vendite.ordini`); ordine fuori perimetro → lista vuota, nessun leak di importi.
Simmetrico al gemello `ApiPreventivoRiepilogoIva`.

**Doc API aggiornata**: `docs/it/backend/vendite/manual/api_ordini.md` (endpoint
`riepilogo-iva` + dipendenze DB viste/funzione/trigger).
