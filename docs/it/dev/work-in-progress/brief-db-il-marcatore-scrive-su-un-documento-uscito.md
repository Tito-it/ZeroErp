# Brief DB — il marcatore del pull scrive su un documento uscito dal giro

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-08. **A chi:** team DB.
> **Cantieri che si incontrano:**
> [uscita-documento-dal-giro](../work-done/brief-db-uscita-documento-dal-giro.md)
> e [esito-gruppo-lotto](../work-done/brief-db-esito-gruppo-lotto.md).
>
> **In una riga:** `fn_segna_esito_gruppo_lotto` marca **tutti** i documenti di
> una commessa, compresi quelli `ESCLUSO`. Il trigger dell'uscita rifiuta — e fa
> bene — ma il rifiuto **abbatte il rilancio**. ⇒ Il verbo che esiste per far
> ripartire un lotto lo rende impossibile da rilanciare.

---

## 1. Come è nato

Collaudo a video di Tid, 2026-09-08. Lotto **`LTF-0010263`**: tolto dal giro
`ORDINE_VENDITA:01a06ce4-b46a-…` — **riuscito**, esito `ESCLUSO` con motivo e
timbro — e premuto **«Rilancia step»**.

```
E_PIPELINE · http 400 · request_id 22868c56-a57b-4ebf-9838-c18a2aea1ca9
```

---

## 2. Che cosa abbiamo analizzato

La catena, dai log applicativi:

| # | Chi | Che cosa succede |
| --- | --- | --- |
| 1 | `fn_emit_attivita_fatturabili_da_commessa` | commessa 34137 fallisce — **atteso**, è il guasto del collaudo, e il fan-out lo isola |
| 2 | `_marca_esito_gruppi` (BE) | annota il fallimento: `fn_segna_esito_gruppo_lotto(lotto, 'ERRORE', commessa_id => 34137)` |
| 3 | `fn_segna_esito_gruppo_lotto` | risolve commessa → documenti e fa l'upsert su **tutti**, compreso quello uscito |
| 4 | `trgfn_fatturazione_lotti_esiti_uscita` | rifiuta: `E_LOTTO_DOC_USCITA_IRREVERSIBILE` |
| 5 | — | l'eccezione **esce** dal marcatore e diventa `E_PIPELINE` 400 |

**Tre cose verificate, perché cambiano il perimetro del problema:**

1. ⭐ **Il rifiuto è corretto.** `ESCLUSO` è terminale (D-3). Non chiediamo di
   allentarlo: è il **tentativo** a non doverci essere.
2. ⚠️ **La premessa del codice a catalogo non regge più.**
   `E_LOTTO_DOC_USCITA_IRREVERSIBILE` è `TECNICO` perché *«qui ci arriva solo un
   UPDATE diretto: la madre chiede prima alla sua check»*. Qui a scrivere è il
   percorso normale del backend.
3. ⛔ **Non si aggira ripristinando la ROOT di 34137.** Il trigger guarda la
   **direzione**: se il pull riuscisse, il marcatore scriverebbe `COMPLETED` su
   quel documento e il rifiuto sarebbe identico. Il lotto è fermo nei due versi.

⛔ **Non è un caso di nicchia: è la linea principale.** Si toglie dal giro un
documento *perché* il suo pull fallisce; al rilancio quel pull fallisce ancora,
il marcatore riprova, il giro muore.

⚠️ **E nessun pgTAP poteva vederlo**: i presidi provano le funzioni una per una,
questo nasce dalla **sequenza**.

---

## 3. ⭐ La regola esiste già, in due posti su tre

Il `20260908-07` ha insegnato al **conteggio** a scartare le critiche di un
documento uscito — è la ragione per cui su `LTF-0010263` `evaluate_lotto_status`
dice `critical = 0` mentre la critica è ancora lì. Il **trigger** lo sa. Il
**marcatore** no.

⇒ *Un documento fuori dal giro non si marca, non si conta, non blocca.*

---

## 4. 🔵 Che cosa serve

**Che il marcatore non tenti di scrivere su un documento che ha già lasciato il
giro.**

⚠️ **E non lo filtriamo dal backend**: sarebbe la terza sede di una regola che il
database possiede già in due punti, e la terza è quella che diverge.

### Due cose da decidere nello stesso giro, non dopo

1. 🔵 **Distinguere i due zeri del marcatore.** Con lo scarto, una commessa il
   cui unico documento è uscito produrrà **zero righe marcate** — e il backend lì
   ha un avviso in servizio (`pull_commesse.esito_non_appeso`) che diventerebbe
   rumore su un caso legittimo. Ci serve separare «nessun documento appeso a
   questa commessa» (difetto) da «gli unici documenti sono usciti» (normale). La
   forma è vostra.
2. 🔵 **La segnalazione critica per documento.** Al rilancio il backend ne
   riscrive una per ogni documento della commessa fallita, compreso quello
   uscito. Non blocca — il conteggio la scarta — ma se ne accumula una a ogni
   rilancio su un documento che non è più in gioco. Va scartata anche lì, o è un
   fatto da registrare? È la D-6 vista dal lato di chi scrive.

---

## 5. Dove siamo intanto

`LTF-0010263` **non è rilanciabile**: l'unica via che il modello lascia è
annullare il lotto e rigenerare. ⚠️ Che è anche la misura di quanto pesa — il
verbo «togli dal giro» esiste per non dover annullare il lotto.

---

## 6. Risposta del team DB — 2026-09-09

### 6.1 ✅ La diagnosi regge tutta, verificata sugli oggetti vivi

| Affermazione | Esito |
| --- | --- |
| il marcatore fa l'upsert su **tutti** i documenti | ✅ la CTE `ammesse` filtrava solo per **perimetro**, mai per stato |
| il rifiuto del trigger è corretto | ✅ scatta solo su `OLD = 'ESCLUSO' AND NEW IS DISTINCT FROM OLD` |
| non si aggira ripristinando la ROOT | ✅ e per un motivo più forte: il trigger **non guarda il valore nuovo**, solo che cambi |
| «non è un caso di nicchia» | ✅ argomentato sul modello, non su un conteggio |

### 6.2 🔴 Il danno non era il documento uscito: era **tutta la commessa**

Il guard è `BEFORE ROW` e il marcatore fa **un solo**
`INSERT … ON CONFLICT DO UPDATE`. L'eccezione su una riga saltava l'**intero
statement**: restavano senza esito anche i documenti **sani** della stessa
commessa.

⇒ Ha una conseguenza diretta sulla forma del rimedio, ed è il motivo per cui il
filtro sta **dentro la CTE `ammesse`** e non in un controllo che precede: gli
altri devono passare. Un pre-check che solleva sposta il problema di due righe.

### 6.3 ⛔ `E_LOTTO_DOC_USCITA_IRREVERSIBILE` non si tocca — il §2.2 si chiude così

Il rilievo è giusto: la premessa del `TECNICO` («qui ci arriva solo un `UPDATE`
diretto») era smentita dai fatti. ⭐ Ma il rimedio la **ripristina**: tolto il
tentativo del marcatore, il trigger torna raggiungibile solo da un chiamante
rotto — che è esattamente ciò che `TECNICO` significa. Declassarlo a
`DATO_ERRATO` (400) farebbe sembrare un errore dell'operatore la violazione di
un invariante. **Nessun changeSet sul codice.**

### 6.4 ⛔ «Nessun pgTAP poteva vederlo» — no: nessuno lo **copriva**

La sequenza è scrivibile in pgTAP, e la fixture **esisteva già** in
`test-uscita-documento-dal-giro-v1.sql`: mancava la chiamata. *Un buco
dichiarato inevitabile è un buco che resta aperto.* Adesso c'è, ed è la
giuntura: **test 19 e 20**.

### 6.5 ⚠️ La regola è scritta a mano in quattro punti, e questo è il quinto

`'ESCLUSO'` è un letterale in `trg_…_a10_uscita`, `fn_escludi_documento_da_giro`,
`fn_check_documento_escludibile_da_giro` e `fn_get_lotto_segnalazioni_summary`.
Il §3 dice «in due posti su tre»: sono quattro, e il rimedio ne fa cinque.

⭐ **E lo stesso dominio tratta l'asse gemello nel modo opposto, di proposito**:
il confine pre-fiscale ha un flag (`config.stati_doc_fiscale.congela_fiscale`,
letto fail-closed) e il commento di `fn_check_documento_escludibile_da_giro`
scrive *«mai un elenco di stati scritto a mano»*. Qui non c'è catalogo:
`stato_esecuzione` è un `text` con un `CHECK` a cinque valori.

⇒ Farne un catalogo con un flag «fuori dal giro» tocca il `CHECK` e un seed: è
**un cantiere suo**, e mescolarlo a un difetto che blocca un lotto sarebbe
sbagliato. La quinta copia è **dichiarata nel changeSet**, non nascosta.

### 6.6 Consegnato

| | |
| --- | --- |
| `20260909-18-update-fn-segna-esito-gruppo-lotto-salta-usciti` | il filtro dentro `ammesse` |
| `20260909-20-update-fn-segna-esito-gruppo-lotto-tre-conteggi` | i tre conteggi di ritorno (§4.1) |
| `20260909-21-update-fn-log-pipeline-fase-niente-critiche-sugli-usciti` | su un documento uscito non si scrivono `W` e `C` (§4.2) |
| `20260909-22-update-fn-escludi-documento-da-giro-giornale-uscita` | l'uscita compare nel giornale, col suo motivo |
| `test-uscita-documento-dal-giro-v1.sql` **19-22** | la giuntura, il documento sano, il giornale dell'uscita, la critica che non si scrive |

✅ **Tutti applicati il 2026-09-09, pgTAP verdi.**

⭐ **Ogni test è stato visto diventare ROSSO**, e su una causa diversa:

| Test | Mutazione | Cosa dice |
| --- | --- | --- |
| **19** | senza il filtro | riproduce l'errore di produzione parola per parola: `P0001`, `E_LOTTO_DOC_USCITA_IRREVERSIBILE` |
| **20** | filtro **troppo largo** (smette di marcare tutto) | il 19 resta verde e si accende il 20 — è il rimedio sbagliato che nessun altro test vedrebbe |
| **21** | senza il `-22` | `NULL`: l'uscita non lascia traccia |
| **22** | senza il `-21` | `C,I` invece di `I`: la critica si riscrive |

✅ I tre `rollback` verificati: la firma del marcatore torna `integer`, e le altre due funzioni tornano quelle di prima.

### 6.7 ✅ Le due decisioni del §4, prese il 2026-09-09

⛔ **E i tre conteggi stanno in un changeSet SUO, non dentro il `-18`.** Il
`-18` era già **applicato**: riscriverne l'SQL cambia il checksum e ferma il
migrate con *«Validation Failed: 1 changesets check sum»* — successo davvero il
2026-09-09. *Un changeSet applicato non si riscrive: se ne fa un altro.* Il
`-18` è stato riportato all'SQL esatto che era stato applicato, e
`liquibase validate` conferma **«No validation errors found»**.

**§4.1 — i tre zeri.** `fn_segna_esito_gruppo_lotto` restituisce
`(marcati, usciti, fuori_perimetro)`. Sono **tre** e non due: oltre a «nessun
documento appeso» e «gli unici sono usciti» c'è — **da prima di questo
difetto** — «i documenti ci sono ma nessuno nel perimetro di questo lotto».
Un ritorno che ne distinguesse due su tre lascerebbe l'ambiguità dov'era.

🔴 **Cambia la firma, e il backend va adeguato nello stesso giro**:
`apps/vendite/db/pipeline_repository.py`, `segna_esito_gruppo_lotto()` (changeSet `-20`) —
`SELECT vendite.fn_…` diventa `SELECT * FROM vendite.fn_…` e legge tre colonne.
`if not marcati:` diventa: si avvisa **solo** quando tutti e tre sono zero, o
quando `fuori_perimetro > 0` (che è l'altro caso sospetto). ⚠️ Finché non è
fatto, quella chiamata rompe: `CREATE OR REPLACE` non sposta un `RETURNS`,
quindi il changeSet fa `DROP` e ricrea. Nessun chiamante dentro il database
(verificato su `pg_proc`: zero).

**§4.2 — la critica, e il giornale.** Decisione di Tid: la critica su un
documento uscito **non si scrive**; ma l'uscita, che è un fatto voluto e con
una motivazione obbligatoria, **deve comparire nel giornale**.

⇒ La regola è: **su un documento uscito non si scrivono `W` e `C`; le `I`
restano.**

* `W`/`C` dicono «qualcosa non va su questo documento»: su uno che è uscito è
  rumore, e qui si smette proprio di scriverlo;
* `I` è un **fatto** del giornale, e l'uscita stessa è un fatto.

⛔ **L'alternativa scartata, e vale scriverla**: «si ferma tutto sul documento
uscito» funziona solo se la riga dell'uscita viene scritta **prima** del
passaggio a `ESCLUSO` — cioè appendendo la traccia all'**ordine di due
istruzioni** dentro un'altra funzione. Il giorno che qualcuno le riordina, la
traccia sparisce **in silenzio**. La regola su `I`/`W`/`C` non ha quel punto
fragile.

⚠️ **Chiude il rubinetto, non ripulisce il pregresso**: le critiche già scritte
su documenti usciti restano dove sono, e il conteggio continua a scartarle.
Cancellare righe di giornale è un'altra decisione, e non è stata presa qui.
