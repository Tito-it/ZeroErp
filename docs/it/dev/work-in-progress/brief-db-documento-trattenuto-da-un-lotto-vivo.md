# Brief DB — un documento trattenuto da un lotto vivo

> **Destinatario:** team DB (`dev/db-tid`). Aperto il 2026-09-09.
>
> **In una riga:** in `DA_EMETTERE` compaiono documenti che un lotto **ancora
> vivo** sta trattenendo. L'operatore li vede, li conta e prova a prenderli; e
> le liste che generano un lotto nuovo **non li escludono**, quindi lo stesso
> documento può entrare in due giri.
>
> **Origine.** Analisi del backend, 2026-09-08, mentre cercava di sbarrare la
> riga a video — e la domanda che ha fermato tutto è stata: *«con quale dato?»*.
>
> **Correlati:** [brief-db-il-marcatore-scrive-su-un-documento-uscito](brief-db-il-marcatore-scrive-su-un-documento-uscito.md) ·
> [linee-guida-sql §12.5](../../linee-guida-sql.md) — le azioni per riga

---

## 1. ⭐ Perché non si risolve a video, ed è il punto migliore dell'analisi

La vista espone `ultimo_esito` e `ultimo_lotto_codice`. Sembra bastare. Non
basta, e il modo in cui non basta è istruttivo — misurato il 2026-09-08 su tre
documenti in `DA_EMETTERE`:

| Documento | `ultimo_esito` | lotto | stato del lotto | in realtà |
| --- | --- | --- | --- | --- |
| ORD0036003 | `COMPLETED` | LTF-0009960 | ANNULLATA | libero ✅ |
| ORD0036005 | `ERRORE` | LTF-0010331 | DRAFT | **trattenuto** 🔴 |
| ORD0036007 | `COMPLETED` | LTF-0010225 | ANNULLATA | libero ✅ |

⛔ Sbarrare la riga guardando `ultimo_esito` prenderebbe ORD0036005 **per il
valore giusto ma per caso**: gli altri due hanno `COMPLETED` e sono liberi, e un
`ERRORE` su un lotto annullato bloccherebbe un documento che invece si può
fatturare.

⭐ È il caso peggiore della regola zero — *la conclusione giusta appoggiata alla
cosa sbagliata* — e il fatto che sia stato visto **prima** di scriverci sopra il
frontend è la ragione per cui questo non diventa un difetto fra sei mesi.

⚠️ La tabella qui sopra è un **fatto datato**, non il motivo. Il motivo è sul
modello e sta in una riga: *il verdetto è «è trattenuto da un lotto VIVO?», e
lo stato del lotto la vista non lo porta.*

⇒ Ricavarlo a video sarebbe la **seconda sede** della regola «questo documento è
in gioco?».

## 2. ⭐ «Vivo» ha già un flag, e non è quello che sembra

`config.stati_doc_fiscale` porta tre assi distinti:

| stato | `is_abortito` | `congela_fiscale` | `chiude_lotto` |
| --- | :---: | :---: | :---: |
| DRAFT | f | f | f |
| EMESSA | f | f | f |
| ANNULLATA | **t** | t | f |
| DEFINITIVA | f | t | **t** |
| INVIATA · REGISTRATA | f | t | f |

⇒ «vivo» = **`NOT is_abortito`**, letto **fail-closed** (stato non risolvibile ⇒
trattenuto: non sapere in che stato è il giro non è un buon motivo per lasciarci
mettere le mani — è la stessa scelta di `fn_check_documento_escludibile_da_giro`).

⛔ **Mai `codice_interno <> 'ANNULLATA'`.**
⚠️ E **mai `congela_fiscale`**, che è l'asse più usato in questo dominio e su
ANNULLATA vale **true**: chi cercasse «il lotto è ancora in gioco» lì prenderebbe
la risposta sbagliata su una riga sola — quella che conta.

## 3. Le due decisioni, prese da Tid il 2026-09-09

| | Decisione | Perché |
| --- | --- | --- |
| **D-1** | La riga **resta visibile e spenta**, col motivo e il gesto verso il lotto; il **conteggio della card la esclude** | Una riga che sparisce non insegna niente all'operatore. Ma un conteggio è una **promessa su quanto lavoro si può prendere**, e oggi comprende lavoro che non si può prendere: è lui il difetto, non la riga |
| **D-2** | Chi costruisce un lotto nuovo **non** deve poter pescare un documento già trattenuto | La casella grigia a video non basta: il secondo giro lo prende da un'altra strada. La regola vale per la **macchina**, non solo per l'operatore. ⚠️ **Ma la strada non è quella che sembrava** — §3.1 |

### 3.1 ⭐ Il meccanismo esiste già — e non copre questo caso

> **Obiezione di Tid, 2026-09-09:** *«mentre è in esecuzione la lavorazione di un
> lotto i documenti associati risultano bloccati e non rifatturabili — il
> meccanismo non è simile?»*

Ed è vero, per metà. `script.fn_get_stato_push_segment` classifica già un
segmento in tre stati:

| | Significato |
| --- | --- |
| `LIBERA` | mai instradata in una commessa |
| `ALLOCATA` | instradata, non ancora emessa |
| `EMESSA` | tutte le sue attività sono emesse |

E le cinque `fn_list_*_da_pushare` pretendono `LIBERA`.

⇒ 🔴 **La prima stesura di questo brief voleva insegnare a quelle cinque una
regola che hanno già**: sarebbe stata una seconda sede, cioè il difetto che il
brief dichiara di voler evitare. Cancellata.

⭐ **Ma il buco resta, ed è su un'altra strada.** `da_pushare` porta
**sorgente → commessa**; un lotto nuovo si costruisce **commessa → lotto**, e
passa da `vendite.fn_list_emittibili_lane`, che filtra solo così:

```sql
AND ca.stato_emissione   = 'NON_EMESSA'
AND ca.stato_approvazione = 'APPROVATA'
```

Nessuno sguardo agli esiti dei lotti.

⭐⭐ **La frase che riassume tutto: il meccanismo che c'è misura l'ESITO del
lavoro, non il fatto che il lavoro sia IN CORSO.** `EMESSA` dice «è andato»,
`LIBERA` dice «non è mai partito». Manca la terza: **«è dentro un giro che non ha
ancora finito»**.

⇒ Ed è per questo che il caso si vede solo sul **fallimento**: quando il giro
riesce, la fattura nasce, `stato_emissione` diventa `EMESSA` e il documento
sparisce da solo — sono ORD0036003 e ORD0036007. Su ORD0036005 il pull è
**fallito**: niente fattura, quindi `NON_EMESSA`, quindi la lane lo riconta e un
secondo lotto se lo prende, mentre LTF-0010331 lo tiene ancora.

## 4. La forma — una sede sola, tre consumatori

⛔ **Il predicato non si scrive tre volte.** Vive in un oggetto solo; la vista di
riga, le liste e il conteggio lo **interrogano**.

| | Cosa |
| --- | --- |
| **la sede** | `vendite.vw_documenti_trattenuti_da_lotto` — un documento, il lotto che lo trattiene. `NOT is_abortito` fail-closed, e l'esito **non** `ESCLUSO`: un documento uscito dal giro non è trattenuto da niente |
| **la riga** | `vw_dash_competenza_gruppi` guadagna il verdetto: motivo + il lotto per il gesto. ⚠️ **Un verbo, una colonna con un nome che dice quale** (§12.5.4): `emissione_blocco_*`, non un `blocco_` generico che domani risponde a due domande |
| **il conteggio** | `vw_dash_competenza_gruppi_riepilogo` esclude i trattenuti — è il numero della card |
| **la lane** | `fn_list_emittibili_lane` esclude — è il lato **macchina** di D-2, e resta **una** funzione: le cinque `da_pushare` non si toccano (§3.1) |

### 4.1 ⭐ Una chiave sola, e il perché è la stessa correzione del §3.1

`vendite.fn_build_gruppo_fatturabile_key(sorgente_tipo_id, sorgente_uid,
commessa_id)` vuole **la commessa**. Finché il piano toccava le `da_pushare` —
che girano *prima* che una commessa esista — servivano **due** chiavi, e con
esse il rischio di costruirne una che somiglia a quella vera senza esserlo.

⇒ Caduto quel passo, tutti e tre i consumatori lavorano **dopo** la commessa
(dashboard, riepilogo e lane leggono `commesse_attivita`): la `gruppo_key` c'è
già, ed è l'unica chiave. ⭐ Una correzione di perimetro che toglie anche il
punto più fragile del disegno.

### 4.2 ⚠️ Il gesto è un `bersaglio`, non una frase

*«toglilo dal giro del lotto LTF-…»* fa ricopiare all'operatore un codice che
deve poi ritrovare a mano. Il lotto è una cosa identificabile: viaggia come
`{tipo: 'LOTTO', id}` e il frontend ci disegna **un gesto**
([linee-guida-sql §5](../../linee-guida-sql.md)). La frase dice *cosa* fare, il
bersaglio *ci porta*.

## 5. ⛔ Cosa NON si fa

* ⛔ **Non si decide da `ultimo_esito`**, nemmeno «per adesso»: risponde giusto
  per caso, ed è il difetto da cui il cantiere nasce;
* ⛔ **Non si scrive un elenco di stati**: il flag c'è, e questo dominio ha già
  cinque letterali `'ESCLUSO'` scritti a mano — non se ne aggiungono su un asse
  che un flag ce l'ha;
* ⛔ **Non si filtra nel frontend**: sarebbe la seconda sede della stessa regola;
* ⛔ **Non si toccano le cinque `fn_list_*_da_pushare`**: la regola lì c'è già
  (`LIBERA`), e insegnargliela di nuovo sarebbe la seconda sede — §3.1;
* ⛔ **Non si toglie la riga dalla lista** (D-1): sparire non spiega niente.

## 6. Il piano

| Passo | Cosa | Dove |
| --- | --- | --- |
| **T-1** | ✅ **FATTO E APPLICATO** il 2026-09-09 — `vendite.vw_documenti_trattenuti_da_lotto`, changeSet `20260909-23` | `20_code/vendite` |
| **T-2** | ✅ **FATTO** — changeSet `20260909-24`, insieme a T-3 | `20_code/vendite` |
| **T-3** | ✅ **FATTO** — stesso changeSet `20260909-24` | `20_code/vendite` |
| **T-4** | ✅ **FATTO** — changeSet `20260909-25` | `20_code/vendite` |
| **P-1** | ✅ **FATTO** — `test-documento-trattenuto-da-lotto-v1.sql`, plan 5, verde | `db/pgtap/vendite` |
| **P-2** | ✅ **FATTO** — `test-fn-list-emittibili-lane.sql`, test 14 e 15 | `db/pgtap/vendite` |

⚠️ **T-2 e T-3 vanno insieme**: la riga resta visibile e il numero la esclude —
consegnarne una sola lascia la card che dice una cosa e la lista un'altra.

## 7. Cosa resta al frontend

Riga non selezionabile, motivo sulla casella spenta, e il gesto «vai al lotto»
dal `bersaglio`. È lo stesso telaio della scheda Documenti del lotto.

⚠️ **Non tocca al DB**, ma va detto qui perché è la metà che si vede: un verdetto
che nessuno rende è un campo dichiarato e non letto, cioè peggio della sua
assenza (§12.5.5).

---

## 8. Stato — 2026-09-09

### 8.1 `T-1` — la sede unica (storico: il primo passo, quando ancora non cambiava niente a video)

| | |
| --- | --- |
| `20260909-23-create-vw-documenti-trattenuti-da-lotto` | la sede unica |
| `test-documento-trattenuto-da-lotto-v1.sql` (plan 5) | i cinque testimoni, **costruiti**, non cercati fra i lotti di oggi |

⛔ **E va detto forte: una vista che nessuno legge non cambia niente.** Oggi la
riga è ancora selezionabile, la card la conta ancora e la lane la offre ancora a
un secondo lotto. ⚠️ È esattamente la forma che §12.5.5 chiama peggiore
dell'assenza — *un campo dichiarato e non letto sembra presidiato*. Il cantiere è
a **uno su quattro**, non finito.

### 8.2 ⭐ Cosa la prova ha aggiunto al §1

Misurato il 2026-09-09 applicando il predicato: **3 documenti trattenuti**, tutti
dal lotto DRAFT `LTF-0010331`; i lotti annullati con esiti non esclusi
(`LTF-0009900`, `-0009901`, `-0009931`, `-0009960`) correttamente **non**
trattengono — e l'ultimo è proprio quello di ORD0036003.

🔴 **Ma due dei tre trattenuti hanno `ultimo_esito = COMPLETED`**, e questo
corregge il §1 in peggio. Lì si diceva che decidere dall'esito *bloccherebbe un
documento fatturabile*. È solo metà:

| | `ultimo_esito` direbbe | la verità |
| --- | --- | --- |
| `COMPLETED` su lotto **DRAFT** | libero | **trattenuto** |
| `ERRORE` su lotto **ANNULLATA** | bloccato | **libero** |

⇒ L'esito è muto in **entrambe** le direzioni: blocca documenti fatturabili **e**
lascia passare documenti che un giro vivo sta tenendo. I test 1 e 2 coprono i due
versi apposta — con uno solo, il presidio passerebbe su una regola che blocca
tutto o su una che non blocca mai.

### 8.3 ✅ Il perimetro DB è completo — tutto applicato il 2026-09-09, pgTAP verdi

| changeSet | Cosa | Stato |
| --- | --- | --- |
| `20260909-23` | la sede unica `vw_documenti_trattenuti_da_lotto` | ✅ applicato |
| `20260909-24` | le colonne `emissione_blocco_*` **e** il conteggio che le esclude | ✅ applicato |
| `20260909-25` | `fn_list_emittibili_lane` non ri-offre i trattenuti | ✅ applicato |

| pgTAP | Cosa prova |
| --- | --- |
| `test-documento-trattenuto-da-lotto-v1.sql` (5) | il predicato: vivo sì, annullato no, escluso no, senza stato **sì** (fail-closed), due lotti **due** righe |
| `test-vw-dash-competenza-v1.sql` **15-bis/ter/quater** | la riga si spegne e nomina il lotto · il conteggio la esclude e la dichiara · annullato il lotto torna libera |
| `test-fn-list-emittibili-lane.sql` **14-15** | non viene ri-offerta a un secondo giro · e torna offerta quando il lotto è annullato |

⭐ **Ogni coppia è un verso e il suo contrario**, e non è simmetria estetica: col
solo verso «blocca» passerebbe anche un predicato che blocca **qualunque**
documento con un esito — che è precisamente l'errore di `ultimo_esito`, e
lascerebbe il contenuto di un lotto annullato bloccato per sempre.

✅ **Provati per mutazione**: senza `T-4` il test 14 è rosso e il **15 resta
verde**, che è la prova che il filtro non blocca troppo.

### 8.4 ⚠️ Due difetti trovati costruendo, non rileggendo

1. 🔴 **Il conteggio andava con `FILTER`, non con una `WHERE`.** Filtrando le
   righe fuori, il **gruppo spariva** quando tutte le sue righe erano trattenute
   — cioè esattamente quando il numero serve — e con lui spariva
   `n_gruppi_trattenuti`, che stava lì per spiegare il calo. Il test `15-ter`
   leggeva `NULL` invece di `1`.
2. ⚠️ **Le due viste stanno in un changeSet solo.** Il ritorno indietro deve
   *togliere* colonne, e `CREATE OR REPLACE VIEW` non sa farlo: serve un `DROP`,
   che porta giù il riepilogo con sé. Separati, i due rollback non stavano in
   piedi da soli.

### 8.5 Cosa resta — e non è DB

Il frontend: riga non selezionabile, motivo dalla `reason_key`, gesto «vai al
lotto» dal `lotto_id`. ⚠️ Finché non arriva, i quattro campi sono **dichiarati e
non letti** — che §12.5.5 chiama peggiore della loro assenza, perché sembrano
presidiati. La `reason_key`
`vendite.emissione.blocco_reason.trattenuto_da_lotto` va nei `locales`, o è un
tooltip vuoto.

