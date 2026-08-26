# Collaudo in-app · righe di DDT senza prezzo

> **Cos'è.** Il copione della validazione a video: si tiene aperto accanto
> all'applicazione e si spunta. Non è il brief — il *perché* di ogni scelta sta
> in [brief-ddt-righe-senza-prezzo.md](brief-ddt-righe-senza-prezzo.md); qui c'è
> solo **cosa fare, cosa deve succedere, e cosa fare se non succede**.
>
> **Perché esiste.** Il piano è chiuso: DB (slice A-D, 2026-08-19) e
> applicativo (BE-A→BE-D, FE-A→FE-E, stesso giorno) sono fatti e i test sono
> verdi. Ma **tre caselle** della definizione di «fatto» (§19 del brief) non le
> ha mai attraversate nessun test automatico, e sono proprio quelle che
> l'operatore vede: la **1** (articolo semplice senza prezzo), la **1-bis** (kit
> senza prezzo) e la **6** (ri-consegna standalone). Questo documento le chiude.
>
> **Stato**: da eseguire. **Ambiente**: sviluppo (`dbdev`). Preparato il
> 2026-08-21, con i dati misurati **quel giorno** in sola lettura.

---

## ⚠️ Cinque cose da sapere prima di cominciare

1. **Il punto di non ritorno è l'emissione** (prove 4 e 6). Un DDT emesso prende
   il numero dal trigger DB e **non torna in bozza**. Tutto quello che viene
   prima — righe, prezzi, causale — è modificabile e cancellabile.
2. **La causale, dopo l'emissione, non si cambia più** (slice B, `E_DDT_CAUSALE_IMMUTABILE`).
   Quindi **scegli la causale prima di emettere**: se emetti con VENDITA e poi
   volevi CONTO_VISIONE, l'unica strada è annullare il DDT e rifarlo.
3. **Nessun worker tocca questi documenti.** A differenza del collaudo nota di
   credito, qui non c'è niente che venga raccolto da un giro automatico: un DDT
   in bozza lasciato a metà resta lì e non fa danni.
4. ⚠️ **Il motivo del prezzo mancante non si vede a video** (F-7/DEC-8): viene
   **persistito** in `ddt_righe.meta`, ma nessuna schermata lo mostra oggi. La
   prova 2 lo verifica con una query, ed è voluto — la decisione era «non
   perderlo», non «mostrarlo ovunque».
5. **Se una prova fallisce, non aggiustare il dato**: annota cosa hai visto e
   passa alla successiva. Le prove sono indipendenti tranne la 6 e la 7, che
   riusano il DDT della 5.

---

## La materia: dati veri, misurati il 2026-08-21

Tutto quello che serve **esiste già** su `dbdev`. Non c'è niente da preparare.

### Il cliente

| BA      | codice        | ragione sociale          | perché questo                                                                                                                                                                              |
| ------- | ------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **155** | `BAC/0000042` | **Titini Michele Carlo** | ha il **contratto 198 in modalità C**, che è ciò che rende il caso riproducibile: su un contratto C un articolo non negoziato **non ha prezzo**, e non è un difetto dei dati — è la regola |

### Gli articoli

| codice                                 | tipo                                     | cosa fa il resolver per il BA 155                             | serve alla prova |
| -------------------------------------- | ---------------------------------------- | ------------------------------------------------------------- | ---------------- |
| **`ARC005474`**                        | semplice                                 | ⛔ **non risolve** → `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C` | 1, 2, 3, 4, 7    |
| **`ART_GUARD_COMP_20260115004105240`** | semplice                                 | ✅ risolve → **120,00**, origine `CONTRATTO_AGGIUNTA`          | 8 (controprova)  |
| **`art-comp-001`** («Test composito»)  | **kit, 3 componenti, tutti obbligatori** | ⛔ **nessuno dei tre** componenti risolve                      | 5, 6             |

⭐ `art-comp-001` è il caso più severo che ci sia: i tre componenti sono tutti
**obbligatori**, cioè quelli su cui il vecchio divieto era più duro. Se passa
questo, passa tutto.

⚠️ **Va bene qualunque articolo `ARC*`**: ne ho provati 25 e falliscono tutti e
25 con lo stesso codice. `ARC005474` è solo il primo in ordine alfabetico.

### Le causali (`config.causali_trasporto`)

| id    | codice                                                                               | `fatturabile`          |
| ----- | ------------------------------------------------------------------------------------ | ---------------------- |
| **1** | **VENDITA**                                                                          | ✅ `true` — **l'unica** |
| 2     | CONTO_VISIONE                                                                        | `false`                |
| 3     | RESO · 4 RIPARAZIONE · 5 CAMPIONATURA · 6 TRASFERIMENTO · 7 CONTO_LAVORO · 8 OMAGGIO | `false`                |

### I DDT già in bozza (se non vuoi crearne uno)

| id        | cliente                    | utility | causale      | righe |
| --------- | -------------------------- | ------- | ------------ | ----- |
| **15849** | 155 — Titini Michele Carlo | 5       | *(nessuna)*  | 1     |
| 15851     | 169                        | 5       | *(nessuna)*  | 1     |
| 15853     | 173                        | 5       | CAMPIONATURA | 1     |

📌 **Suggerimento d'ordine**: crea **un DDT nuovo** per il cliente
`BAC/0000042`, lascia la causale vuota, e usalo per le prove 1→4. È più pulito
che riusare il 15849, e ti lascia libero di annullarlo alla fine.

---

## Prove

### 1 · L'articolo senza prezzo **si carica** *(casella 1 — il cuore di tutto)*

**Dove**: `Vendite → DDT → Nuovo`. Cliente `BAC/0000042`, utility come da
default, **causale vuota**. Salva la bozza, poi apri le righe → **Nuova riga**.

**Cosa fare**: articolo **`ARC005474`**, quantità 1, IVA come proposta,
**il campo prezzo LASCIALO VUOTO**. Salva.

- [X] la riga **si salva** — compare il toast **verde** «Riga aggiunta»;
- [X] compare **anche** un toast **giallo** con il motivo, che parla di
      *contratto in modalità C / articolo non negoziato*;
- [X] ⛔ **nessun toast rosso**, e nessun messaggio «impossibile risolvere il
      prezzo listino»;
- [X] nella tabella righe, la colonna **Prezzo** mostra il tag grigio
      **«Senza prezzo»** — non una cella vuota;
- [X] la colonna **Importo** mostra **anch'essa** «Senza prezzo» — **non
      `0,00 €`**.

⚠️ **Se vedi `0,00 €` nell'importo**: è il difetto V-2 del brief tornato. Un
importo a zero su una riga senza prezzo fa tornare «giusto» il totale del
documento sommando quello che non c'è. Segnalalo.

⚠️ **Se arriva un toast rosso e la riga non si salva**: BE-A non è in esercizio
sull'ambiente. Controlla che il migrate sia stato applicato — la funzione
`vendite.fn_resolve_prezzo_listino_v2_esito` deve esistere e `zeroerp_app` deve
poterla eseguire.

### 2 · Il *perché* sopravvive al ricarico *(F-7 / DEC-8)*

**Dove**: chiudi il drawer del DDT, riaprilo, torna sulle righe.

- [X] la riga è ancora lì col tag **«Senza prezzo»**.

Il **motivo** però non è a video (punto 4 del preambolo): si verifica sul dato.
Query di sola lettura, sostituisci `<ddt_id>`:

```sql
SELECT id, riga_nr, prezzo_unitario,
       meta -> 'prezzo_resolver_context' ->> 'esito_codice' AS motivo
  FROM vendite.ddt_righe
 WHERE ddt_id = <ddt_id> AND attivo;
```

- [X] `prezzo_unitario` è **NULL**;
- [X] `motivo` vale **`E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C`**.

⚠️ **Se `motivo` è NULL** ma il prezzo manca: B7 non ha scritto. È il caso in
cui fra sei mesi qualcuno guarda quella riga e non sa dire se il prezzo fu
dimenticato o se non c'era.

### 3 · Con causale **fatturabile** l'emissione **blocca, e dice quale riga** *(casella 2)*

**Dove**: sulla testata dello stesso DDT, imposta la causale **VENDITA**. Salva.
Poi guarda il pulsante **Emetti**.

- [X] il pulsante **Emetti** è **disabilitato**;
- [X] passandoci sopra, il tooltip elenca i motivi e fra questi c'è quello sul
      **prezzo non risolvibile**, che **nomina la riga**;
- [X] se provi comunque, il DDT **non** passa a EMESSO.

⭐ **Questo è il momento storico della validazione**: il gate esiste dal
2026-07-18 e in un anno non è **mai** scattato su un documento reale — le 271
occorrenze nel diario erano tutte corse di pgTAP. Se lo vedi scattare adesso,
DL-28 è finalmente esercitato per intero.

### 4 · Con causale **non fatturabile** il DDT **esce** *(casella 3)*

**Dove**: stessa testata, cambia la causale in **CONTO_VISIONE**. Salva.

- [ ] il pulsante **Emetti** **si abilita** — e senza aver toccato il prezzo;
- [ ] emetti: il DDT passa a **EMESSO** e prende il **numero**;
- [ ] la riga resta **«Senza prezzo»**, non le è stato inventato uno zero.

Poi, la seconda metà della casella — che il documento resti **fuori** dal giro
della fatturazione:

- [ ] il pulsante **«Push a commessa»** è **disabilitato**, e il tooltip dice
      che è un documento di **solo trasporto**;
- [ ] in `Vendite → Cockpit fatturazione` (lente DDT) il documento **non
      compare**.

### 5 · La causale, dopo l'emissione, è **bloccata** *(casella 3-bis)*

**Dove**: sul DDT appena emesso, prova a modificare la testata.

- [ ] il campo **Causale di trasporto** è in **sola lettura** (tutta la testata
      lo è fuori dalla bozza).

ℹ️ **Non è un errore che non appaia il messaggio del DB.** Il guard
`E_DDT_CAUSALE_IMMUTABILE` sta a livello database e l'applicazione non lo
raggiunge, perché non espone la modifica. Il codice è comunque registrato nel
dizionario del backend (BE-C) proprio perché il giorno in cui quella porta si
aprisse il messaggio arrivi leggibile, invece di un 500 muto. **Qui si verifica
che la porta sia chiusa, non che l'allarme suoni.**

### 6 · Il **kit** viaggia senza prezzi *(casella 1-bis — il pezzo nuovo)*

**Dove**: **nuovo** DDT in bozza, cliente `BAC/0000042`, causale
**CONTO_VISIONE** *(mettila subito: il form guarda la causale della testata)*.
Righe → **Nuova riga** → articolo **`art-comp-001`**.

Si apre la **dialog dei componenti** (l'articolo è composito):

- [ ] i **tre** componenti (`componente`, `componente2`, `art 100`) hanno la
      colonna **Prezzo suggerito vuota** e accanto il **motivo**
      («Contratto 198 modalità C…»);
- [ ] ⭐ il pulsante **Conferma** è **ABILITATO** — è la cosa da guardare: prima
      del 2026-08-19 era disabilitato e il kit non si salvava;
- [ ] conferma **senza digitare nessun prezzo**, poi salva la riga;
- [ ] la riga kit compare con **«Senza prezzo»**;
- [ ] ⛔ **non** `0,00 €` — se il padre valesse zero sarebbe una **somma
      parziale** dei figli, il difetto che C2 esiste per impedire;
- [ ] apri il pannello componenti della riga: i tre componenti ci sono, con
      prezzo **assente** e **non** zero;
- [ ] **Emetti**: il DDT esce.

**Controprova, sulla stessa riga** — cambia la causale della testata in
**VENDITA** *(fallo **prima** di emettere: dopo non si può più)*:

- [ ] **Emetti** torna **disabilitato**, e il tooltip parla dei **componenti**
      non valorizzati.

⚠️ **Quel motivo sui componenti era un ramo morto**: fino al 2026-08-19 non
poteva scattare, perché la colonna era NOT NULL. Se lo vedi comparire, R-5 è
chiuso davvero.

### 7 · Ordini e preventivi **continuano a rifiutare** *(casella 4 — la controprova)*

⛔ **Questa prova serve a dimostrare che l'allentamento è del solo DDT.** Senza,
non si sa se abbiamo aperto una porta o buttato giù un muro.

**Dove**: `Vendite → Ordini → Nuovo`, stesso cliente `BAC/0000042`. Aggiungi una
riga con **`ARC005474`** e **prezzo vuoto**.

- [ ] arriva un **errore rosso**;
- [ ] la riga **NON** si salva;
- [ ] nessun tag «Senza prezzo» compare da nessuna parte.

Ripeti la stessa cosa su un **Preventivo**: stesso esito.

### 8 · Quando il prezzo c'è, non è cambiato niente *(non-regressione)*

**Dove**: sul DDT della prova 1, aggiungi una riga con
**`ART_GUARD_COMP_20260115004105240`**, prezzo **vuoto**.

- [ ] la riga si salva e il prezzo si compila da solo: **120,00**;
- [ ] **nessun** toast giallo;
- [ ] nessun tag «Senza prezzo».

⚠️ **Se il prezzo non si risolve**, guarda l'**unità di misura** scelta: la
misura sopra è sull'UoM **base** dell'articolo. Con un'altra UoM il prezzo può
legittimamente non esserci, e non sarebbe un difetto.

### 9 · La ri-consegna **standalone** *(casella 6 — la più lunga, falla per ultima)*

⚠️ **Va costruita**: misurato il 2026-08-21, sul DB **non esiste** oggi nessuna
riga di reso standalone — tutte le 12 righe di reso attive vengono da un ordine.
È la ragione per cui questo caso non si è mai visto, non la prova che non
esista.

**Costruzione** (ognuno di questi passi è già collaudato di suo):

1. DDT **creato da zero**, non da un ordine — è questo che lo rende
   *standalone*: cliente `BAC/0000042`, riga con **`ARC005474`** e **prezzo
   digitato a mano** (serve per poterlo emettere), causale **VENDITA**;
2. emettilo e portalo fino a **CONSEGNATO**;
3. fai un **reso** su quella riga;
4. dal reso, genera la **ri-consegna**.

**Cosa deve succedere sul DDT di ri-consegna generato:**

- [ ] il DDT esiste, con la riga di ri-consegna;
- [ ] la riga è **«Senza prezzo»** — il DB la genera valorizzando la quantità e
      non il prezzo, e **non c'è nessun ordine da cui ereditarlo**;
- [ ] ⭐ il drawer **si apre e si usa** senza errori: prima di questo lavoro il
      solo aprire e risalvare quella riga faceva scattare il resolver;
- [ ] con causale **VENDITA** l'emissione **blocca con il messaggio parlante**
      della prova 3 — invece di lasciare l'operatore davanti a un documento che
      non capisce perché non esce;
- [ ] digitando il prezzo a mano, il DDT **esce** normalmente.

---

## Verbale

| #   | Prova                                               | Casella §19 | Esito | Note |
| --- | --------------------------------------------------- | ----------- | ----- | ---- |
| 1   | Articolo semplice senza prezzo si carica            | **1**       | ⬜     |      |
| 2   | Il motivo sopravvive al ricarico                    | F-7         | ⬜     |      |
| 3   | Causale fatturabile → emissione blocca              | 2           | ⬜     |      |
| 4   | Causale non fatturabile → il DDT esce e resta fuori | 3           | ⬜     |      |
| 5   | Causale bloccata dopo l'emissione                   | 3-bis       | ⬜     |      |
| 6   | Il kit viaggia senza prezzi                         | **1-bis**   | ⬜     |      |
| 7   | Ordini e preventivi rifiutano ancora                | 4           | ⬜     |      |
| 8   | Prezzo risolto: nessuna regressione                 | —           | ⬜     |      |
| 9   | Ri-consegna standalone                              | **6**       | ⬜     |      |

**Chiuso il**: ______  **Da**: ______

> Quando le tre caselle in grassetto sono verdi, il brief
> `brief-ddt-righe-senza-prezzo.md` può passare in `work-done` e questo verbale
> con lui. Finché non lo sono, il lavoro è **scritto e testato**, non
> **validato** — e la differenza è precisamente quella che ha fatto emergere il
> changeSet `20260819-19`, che nessun collaudo di scrivania aveva previsto.
