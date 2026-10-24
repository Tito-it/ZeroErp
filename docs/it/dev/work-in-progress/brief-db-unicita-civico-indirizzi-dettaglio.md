# Brief DB — Un civico, una riga: l'unicità di `indirizzi_dettaglio` e il suo «trova o crea»

## ⏭️ Chi riparte — aggiornato al 2026-10-25

**Riparte: Tid**, con il via allo sviluppo. Tutte le decisioni del §4 (D1-D8) sono prese
(2026-10-25).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ team DB | Il problema, la prova, la storia delle decisioni, la proposta | §1-§4 | — |
| 2 | ✅ Tid | D1-D8 | §4 | 1 |
| 3 | **Tid** | Il via allo sviluppo | — | 2 |
| 4 | team DB | Giro 1: changeSet (BB, vincoli, guard, indice), pgTAP, guide | §5 | 3 |
| 5 | **Tid** | Apply su dbdev, corsa pgTAP come app | — | 4 |
| 6 | team FE | Il campo civico non accetta `0` né negativi | §6.1 | 3 |
| 7 | team BE | Il codice del duplicato in modifica arriva leggibile al drawer | §6.2 | 5 |
| 8 | team DB | Chiusura: tolti i «Limiti noti» dal manuale, archiviazione | §5.5 | 5, 6, 7 |

Decisioni aperte di Tid: nessuna (resta il via). Lavoro da committare: questo brief, e le pagine
già aggiornate nella stessa sessione (§7).

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-25. **A chi:** Tid; poi il team DB; il §6.1 al team FE, il §6.2 al team BE.
> **Origine:** revisione di `docs/it/postgresql/intro.md` (2026-10-24/25): l'esempio sull'indice di
> `indirizzi_dettaglio` non coincideva con l'indice vero, e la verifica ha trovato i difetti del §2.
> Tid, 2026-10-25: «direi di creare un apposito brief db».
> **Perimetro:** DB (`anagrafiche`: il BB `fn_get_or_create_indirizzo_dettaglio`, il vincolo sul civico,
> l'indice unico; pgTAP; guide). Ricaduta FE: il campo civico (§6.1). Ricaduta BE: il codice nuovo
> della modifica che collide (D6, §6.2); per il resto il service passa già i valori come li riceve, e
> dopo il giro il BB li accetta così.
> **Brief vicini verificati:** nessuno aperto sul tema. In `work-in-progress/` la tabella compare solo
> in elenchi di `valutazione-modello-di-dominio-db.md` e
> `analisi-critiche-modello-clienti-utilities-catasto-v2.md`, su altri argomenti.

---

## 1. Il problema, in parole semplici

`anagrafiche.indirizzi_dettaglio` deve avere **una riga per ogni indirizzo fisico**: via + numero civico
+ estensione + palazzina + scala + piano + interno. Tutti gli indirizzi dei soggetti, i PDP, i magazzini
e le unità catastali puntano a quella riga. Due righe per lo stesso indirizzo spezzano il dato: metà dei
documenti punta a una, metà all'altra.

Oggi l'unicità ha tre buchi:

* **A — civico senza numero.** Un indirizzo «SNC» (`civico` vuoto) non è coperto dall'indice: due righe
  identiche sulla stessa via convivono.
* **B — due modi di dire SNC.** `civico = 0` e `civico` vuoto diventano entrambi `SNC`, con lo stesso
  indirizzo leggibile, ma per l'indice sono due civici diversi.
* **C — il «trova o crea» non trova.** Se l'indirizzo esiste già e lo si ripassa con l'estensione `A`
  (salvata `/A`) o con l'interno in minuscolo, la funzione **restituisce NULL** invece dell'id. È il
  flusso normale del frontend: l'estensione si mostra e si rimanda **senza** la `/`.

---

## 2. La prova e la causa

**Prova del 2026-10-25** su dbdev, come `zeroerp_app`, in una transazione annullata (script nel
pgTAP del giro 1, §5.4):

| Caso | Esito |
| --- | --- |
| A — due `INSERT` con `civico NULL` e lo stesso dettaglio | entrambi passano; il BB, chiamato dopo, ne restituisce una senza errore |
| B — BB con `civico 0` accanto alle righe con `civico NULL` | riga nuova; tre righe con la stessa stringa `indirizzo_normalizzato` |
| C — BB due volte con estensione `A` e interno `zzprova2` | la prima crea (`/A`, `ZZPROVA2`), la seconda restituisce **NULL** |

**Le cause, sul modello:**

* **A.** L'indice `uq_indirizzi_dettaglio_norm` è su `stradario_id, civico, COALESCE(estensione_civico,
  '') … COALESCE(interno, '')`. `civico` è `integer` nullable ed entra **nudo**: senza `COALESCE` (la
  sentinella `''` non vale per un intero) e senza `NULLS NOT DISTINCT`. Il BB cerca con
  `civico IS NOT DISTINCT FROM` e quindi evita il doppione **in sequenza**. Due chiamate concorrenti
  passano entrambe la SELECT, entrambe inseriscono, e nessuna urta l'indice: il ramo `unique_violation`
  non scatta.
* **B.** `fn_build_indirizzo_normalizzato` scrive `civico_norm = 'SNC'` quando `civico IS NULL OR civico = 0`,
  ma né l'indice né il lookup sanno che `0` e `NULL` sono la stessa cosa. Non c'è un CHECK su `civico`
  (sono ammessi anche i negativi).
* **C.** Il trigger normalizza le colonne strutturali (`UPPER(BTRIM(…))`, prefisso `/` sull'estensione)
  **prima** di salvare. Il lookup del BB confronta invece i **parametri grezzi** coi valori salvati. Non
  trova la riga, l'`INSERT` normalizzato urta l'indice, e la ri-lettura dopo il `unique_violation` usa
  di nuovo i parametri grezzi e non trova niente: `RETURN v_id` con `v_id` NULL.
  `script.fn_check_indirizzo_duplicato` (il controllo duplicati del form) fa invece la cosa giusta:
  passa i parametri per `fn_build_indirizzo_normalizzato` prima di confrontare.

Fatto datato, non un motivo: al 2026-10-25 dbdev (284 righe, lette come app) non ha né `civico <= 0`, né
stringhe vuote nelle colonne strutturali, né gruppi gemelli secondo la chiave proposta al §4. I difetti
valgono sul modello comunque: il modello li ammette.

---

## 3. La storia delle decisioni

| Data | Dove | Cosa si è deciso |
| --- | --- | --- |
| prima del 2025-11-27 | baseline, `ix_uq_indirizzi_dettaglio_norm` | unicità sulle forme **normalizzate** (`via_norm`, `civico_norm`, …): copriva anche l'SNC (`civico_norm = 'SNC'`), ma dipendeva dal **nome** della via |
| 2025-11-27 | `20251127-01` e `20251127-01-1` | passaggio alla **chiave fisica**: `stradario_id` + colonne strutturali, «COALESCE per gestire i NULL». `civico` resta nudo: **il buco A nasce qui** |
| 2025-11-27 | `docs/it/postgresql/intro.md` | la best practice «campo opzionale che definisce l'identità → `COALESCE`», scritta per questo caso |
| 2026-03-13 | `20260313-12` (il BB) | lookup con `IS NOT DISTINCT FROM` sul civico e `COALESCE` sulle altre; il pattern SELECT → INSERT → ri-SELECT è **scelto apposta** invece di `ON CONFLICT` (commento nel corpo) |
| 2026-03-17 | `20260317-01` | `UPPER(BTRIM(…))` nel trigger: l'indice diventa case-insensitive «di fatto», sui valori normalizzati. Il lookup del BB non è stato allineato: **il buco C nasce qui** |
| 2026-10-07 | `20261007-70` | precedente di progetto: `config.parameter_overrides` passa a `NULLS NOT DISTINCT` (v5) per lo stesso difetto |
| 2026-10-25 | linee guida SQL §8.4-bis | la regola di progetto diventa `NULLS NOT DISTINCT`; la forma `COALESCE` resta come storica |

Conclusione: le proposte del §4 **completano** la decisione del 2025-11-27 (chiave fisica, NULL gestiti),
non la revocano. Restano ferme sia la chiave fisica sia il pattern SELECT → INSERT → ri-SELECT del BB.

---

## 4. Le decisioni

### D1 — Il BB cerca coi valori normalizzati ✅ (Tid, 2026-10-25: «ok»)

Il BB passa i parametri per `anagrafiche.fn_build_indirizzo_normalizzato`, la stessa funzione del
trigger e di `fn_check_indirizzo_duplicato` (regola del 2: una normalizzazione sola), e usa i valori `o_*`
sia nel lookup sia nella ri-lettura dopo il `unique_violation`. Il pattern resta SELECT → INSERT →
ri-SELECT. In più il BB solleva un errore se la ri-lettura non trova niente: un `NULL` restituito non
è più un esito possibile.

### D2 — Il civico `0` ✅ a (Tid, 2026-10-25: «d2a ok»)

Il significato lo dà chi scrive la colonna. Il frontend scrive il civico con un `InputNumber` senza
minimo; «senza numero civico» si esprime **lasciando vuoto il campo**. Non esiste un valore SNC
nell'estensione: l'estensione è la lettera o il `bis` (`/A`, `/BIS`), e `SNC` nasce solo dentro
`civico_norm`, calcolato.

Le strade possibili:

| | Cosa | Pro | Contro |
| --- | --- | --- | --- |
| ⭐ **a** (proposta) | **SNC = `civico` NULL, una sola forma.** `CHECK (civico IS NULL OR civico > 0)` sulla tabella; il campo FE non accetta `0` (§6.1) | un significato, una scrittura; l'indice, il lookup e la stringa normalizzata dicono la stessa cosa; un `0` è un errore visibile, non un valore plausibile | un `0` scritto a mano viene rifiutato invece di essere accolto |
| b | normalizzare `0` → `NULL` nel trigger (`fn_build_indirizzo_normalizzato`) | nessun rifiuto | una correzione silenziosa: il valore salvato non è quello scritto, e un `-5` resterebbe da decidere |
| c | `SNC` nell'estensione | — | mescola due cose: l'estensione qualifica un numero che c'è; e `civico_norm` già scrive `SNC` da sé |

Con **a**, `fn_build_indirizzo_normalizzato` smette di trattare `0` come caso a parte (resta solo `NULL`
→ `SNC`). Il CHECK prende un nome `ck_*` e il suo messaggio si registra come per gli altri CHECK di
tabella (da verificare nel giro 1).

### D3 — La forma dell'indice ✅ a (Tid, 2026-10-25: «d3a ok»)

| | Cosa | Pro | Contro |
| --- | --- | --- | --- |
| ⭐ **a** (proposta) | `uq_indirizzi_dettaglio_norm_v2` sulle **colonne nude** (`stradario_id, civico, estensione_civico, palazzina, scala, piano, interno`) **`NULLS NOT DISTINCT`**; la normalizzazione trasforma la stringa vuota in `NULL` (`NULLIF(UPPER(BTRIM(x)), '')`) | la regola del §8.4-bis; copre anche il civico; un `ON CONFLICT` sulle colonne usa l'indice senza ripetere espressioni. Il lookup del BB no: `IS NOT DISTINCT FROM` non è una condizione d'indice, e l'indice serve solo su `stradario_id` (il resto è filtro, su poche righe per via) | il `NULLIF` cambia la normalizzazione: oggi `''` e `NULL` sono la stessa chiave solo grazie al `COALESCE` |
| b | tenere la forma `COALESCE` e aggiungere `COALESCE(civico, 0)` | cambio minimo | richiede comunque D2-a (altrimenti `0` e `NULL` collidono per sentinella, non per regola); resta la forma storica |
| c | tornare alle forme normalizzate (`via_norm`, `civico_norm`, …) | copre SNC da sé | **revoca** la decisione del 2025-11-27 (chiave fisica, indipendente dal nome della via): sconsigliata |

Con **a**, il lookup del BB diventa `IS NOT DISTINCT FROM` su tutte le colonne, al posto dei `COALESCE`.
Il vecchio indice si toglie nello stesso changeSet del nuovo, per non lasciarne due.

### D4 — La via non risolta: errore ✅ a (Tid, 2026-10-25)

`fn_build_indirizzo_normalizzato` esce subito, con **tutti** gli `o_*` NULL, se non trova la via in
`script.vw_indirizzo_completo`. La vista lega stradario, comune, provincia, CAP e
`vw_stradario_esteso` con JOIN obbligatori: uno stradario presente in `config.stradario` può non
risolversi. Con D1 il lookup cercherebbe allora «via, nessun dettaglio» e restituirebbe la riga SNC
nuda di quella via: **un id sbagliato, senza errore**. Il BB, dopo la normalizzazione, solleva un
errore registrato se `o_via_norm` è NULL, prima del lookup. Scartata la ricaduta sui valori grezzi: due
modi di cercare, e l'`INSERT` fallirebbe comunque su `via_norm NOT NULL`.

### D5 — Riga trovata ma disattivata: il BB la riattiva ✅ a (Tid, 2026-10-25)

L'unicità copre anche le righe con `attivo = false`, e va bene così: un indirizzo fisico, una riga.
Il lookup non filtra `attivo`, e oggi il BB restituisce in silenzio l'id di una riga spenta. Con D5 il
BB la **riattiva** e ne restituisce l'id: chi usa di nuovo un indirizzo fisico lo rimette in uso, e
lo spegnimento era una conseguenza («nessuno lo usava»), non un divieto. Scartati l'errore (blocca
l'utente su un indirizzo vero) e lo stato di oggi (collegamento a una riga spenta).

### D6 — Modifica che collide: errore registrato ✅ a (Tid, 2026-10-25)

`update_indirizzo_dettaglio` (BE) modifica sul posto una riga condivisa da soggetti, PDP, magazzini.
Il significato resta **«correggo l'indirizzo per tutti»**. Se il valore nuovo coincide con un'altra
riga, il DB solleva un codice registrato che **nomina la riga esistente**, invece di un `23505` nudo;
l'indice resta la rete per le corse concorrenti. Precedente: `E_MAG_INVENTARIO_RIGA_POSIZIONE_DUPLICATA`.
Il codice si sceglie nel giro, dopo una ricerca nel registro. Scartate la fusione delle righe e il
«trasloco di uno solo»: la seconda è una domanda di modello (correzione per tutti contro cambio di
indirizzo di un proprietario) che resta **fuori** da questo brief e, se servirà, partirà dalla storia
delle decisioni.

### D7 — Le righe già presenti ✅ a (Tid, 2026-10-25)

* Le stringhe vuote nelle colonne strutturali si riscrivono **nel changeSet dell'indice**, subito prima
  del `CREATE INDEX`: non sono dati sbagliati, sono la stessa chiave scritta con la regola vecchia.
  L'`UPDATE` passa per i trigger della tabella (normalize, a10, storico z90): va preparato perché non
  lasci versioni inutili nello storico.
* Civico `<= 0`, valori di soli caratteri speciali (D8) e righe gemelle: **niente codice**. Se su una
  macchina il vincolo non si crea, le righe si correggono o si cancellano a mano (AGENTS, «bug di dati in
  sviluppo»). Fatto datato, non un motivo: al 2026-10-25 le righe presenti sono solo di test.

### D8 — Niente valori di soli caratteri speciali ✅ (Tid, 2026-10-25)

Proposta di Tid: un valore senza nemmeno una lettera o una cifra (`/`, `-`, `.`) non dice niente, e si
**rifiuta alla fonte** invece di correggerlo. Vale per le cinque colonne strutturali (estensione,
palazzina, scala, piano, interno), non solo per l'estensione: una scala `-` è lo stesso difetto.

* Sede: un CHECK di tabella per colonna, `col IS NULL OR col ~ '[[:alnum:]]'`, con messaggio registrato.
  Il CHECK vede il valore **dopo** il trigger: gli spazi da soli diventano NULL (D3-a) e passano,
  `/A`, `-1`, `BIS` passano, `/` da solo no.
* Stessa linea di D2-a: un valore senza senso è un errore visibile, non un valore da aggiustare.

---

## 5. Giro 1 — cosa si costruisce (dopo il via)

### 5.1 ChangeSet

Numerazione dal primo libero del giorno di sviluppo, un changeSet per file, DDL e corpi presi dalla
doc auto-generata:

L'ordine conta: l'autogen ordina per numero, quindi i numeri seguono la sequenza qui sotto.

1. `20_code` — `fn_build_indirizzo_normalizzato`: `NULLIF(…, '')` sulle colonne strutturali (D3-a) e il
   ramo `0` ritirato (D2-a). È l'unica sorgente: la usano trigger, BB e `fn_check_indirizzo_duplicato`.
2. `20_code` — `fn_get_or_create_indirizzo_dettaglio`: chiave dai valori `o_*` (D1), errore se
   `o_via_norm` è NULL (D4), lookup `IS NOT DISTINCT FROM`, riattivazione della riga spenta (D5),
   errore se la ri-lettura è vuota.
3. `20_code` — il guard della modifica che collide (D6), con il codice nuovo registrato.
4. `00_schema` — i CHECK: civico (D2-a) e soli caratteri speciali (D8).
5. `00_schema` — la riscrittura delle righe con `''` (D7, il trigger ricalcola, come fa
   `proc_bump_indirizzi_dettaglio`), poi l'indice `NULLS NOT DISTINCT` e il ritiro di
   `uq_indirizzi_dettaglio_norm` (D3-a).

Se su una macchina un CHECK o l'indice non si creano, le righe si sistemano a mano (D7): non si scrive
un fix software.

### 5.2 Censimento da fare nel giro

* Gli scrittori diretti della tabella: il builder `dbops.fn_pgtap_crea_indirizzo_dettaglio` e i pgTAP
  che fanno `INSERT` a mano (`test-indirizzi-istanza-cascata`, `test-create-pdp`,
  `create-gestore-indirizzo-res*`): nessuno deve scrivere `civico = 0` o stringhe vuote.
* Il ramo `UPDATE` del BE (`update_indirizzo_dettaglio`): modificare il civico di una riga esistente
  passa per lo stesso indice, e con D3-a anche lo SNC collide. Lo copre il guard di D6.
* Chi crea o modifica i dettagli con valori di soli caratteri speciali (D8): builder pgTAP e seed.
* `fn_check_indirizzo_duplicato`: dopo D2-a il suo `exact_match` (sulla stringa) e l'indice (sulle
  colonne) dicono la stessa cosa; verificarlo nel pgTAP.

### 5.3 Documentazione

* [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) §«Indirizzo dettaglio» e R7: la chiave e la
  forma dell'indice.
* Manuale `anagrafiche/manual/indirizzi_dettaglio`: tolto il riquadro «Limiti noti».
* Linee guida SQL §8.4-bis: nessun cambio di regola; se serve, questo caso come esempio.

### 5.4 pgTAP

Un file nuovo (o un'estensione di `test-fn-get-or-create-indirizzo-dettaglio.sql`) che **costruisce** i
casi qui sotto, senza appoggiarsi ai dati presenti:

* A: due civici SNC con lo stesso dettaglio → il secondo `INSERT` è rifiutato; il BB restituisce l'id esistente;
* B: `civico = 0` è rifiutato dal CHECK;
* C: BB con estensione `A` e interno minuscolo su una riga esistente → stesso id, mai NULL;
* D4: stradario che non si risolve nella vista, accanto a una riga SNC nuda della stessa via → errore,
  non l'id della riga SNC;
* D5: BB su una riga disattivata → stesso id, riga di nuovo `attivo`;
* D6: `UPDATE` che porta una riga sulla chiave di un'altra → il codice nuovo, non `23505`;
* D8: `/`, `-` da soli rifiutati; `/A`, `-1` accettati; spazi da soli → NULL;
* la clausola: l'indice è `NULLS NOT DISTINCT` (`pg_index.indnullsnotdistinct`), non solo il nome.

I pgTAP li lancia Tid.

### 5.5 Chiusura

Dopo l'apply e la corsa verde: riquadro «Limiti noti» tolto dal manuale, blocco «Chi riparte» chiuso,
brief in `work-done/`.

---

## 6. Richieste ai team FE e BE

### 6.1 Team FE

Il campo civico (`InputNumber` in `IndirizzoDrawer.vue` e `IndirizzoSoggettoForm.vue`) accetta oggi `0` e
i negativi. Con D2-a il DB li rifiuta: il campo prende `:min="1"`, e «senza numero civico» resta il campo
vuoto. Nessun altro cambio: l'estensione si può continuare a mandare senza `/`, la normalizza il DB.
I valori di soli caratteri speciali (D8) li rifiuta il DB con un messaggio registrato: nessuna
validazione da ricopiare nel form.

### 6.2 Team BE

Dopo l'apply: modificare un dettaglio sulla chiave di un'altra riga (D6) produce il codice nuovo, che
nomina la riga esistente. Verificare che arrivi al drawer come messaggio leggibile (policy generata
degli errori) e non come errore generico. Nessun cambio di service.

---

## 7. Già fatto in questa sessione (2026-10-24/25, da committare)

* `docs/it/postgresql/intro.md`: testata, elenco delle pagine, sezione UNIQUE ridotta a un rimando.
* `docs/it/linee-guida-sql.md` §8.4-bis «Indici UNIQUE con colonne nullable»: la regola, compreso il
  lookup che confronta i valori normalizzati.
* `docs/it/dbzero/anagrafiche/manual/indirizzi_dettaglio.md`: riscritto sulla struttura vera, con i
  «Limiti noti» datati.
