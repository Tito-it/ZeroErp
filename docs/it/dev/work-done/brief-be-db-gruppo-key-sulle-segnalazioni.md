# Brief BE → DB — la `gruppo_key` sulle segnalazioni, e i due pezzi che mancano

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-08.
> **A chi:** team DB (`dev/db-tid`).
> **Seguito di:** [brief-db-uscita-documento-dal-giro.md](../work-in-progress/brief-db-uscita-documento-dal-giro.md) §6.1.
>
> **In una riga — com'era all'apertura:** il verbo è consumato end-to-end e
> funziona, ma sulla corsia
> del **pull** non sblocca ancora niente — e il backend non può chiudere il
> §6.1 da solo, perché gli mancano **due** pezzi a database.
>
> 🟢 **CHIUSO e archiviato — 2026-09-08, stessa giornata** (decisione di Tid).
> ⚠️ **Che cosa chiude, esattamente:** le DUE richieste di questo brief — il
> parametro sul canale di scrittura (§3.1) e la conversione commessa →
> documenti chiamabile (§3.2). Il collaudo end-to-end del cantiere
> — due documenti rotti su quattro, il lotto che riparte **al secondo** —
> **non è qui**: è il §9 del brief padre, che resta aperto. ⛔ Distinguerli
> conta: qui si è provato che il proprietario ARRIVA e che il conteggio lo
> legge; là si prova che l'operatore, a video, vede il giro ripartire.
>
> 🟢 **Consegnato.** Il team DB ha consegnato entrambi i
> pezzi (`20260908-18` la conversione estratta, `-19` la madre che la **chiama**,
> `-20` `p_gruppo_key` su `fn_log_pipeline_fase`) e il backend ha scritto le tre
> righe del §6.1. **Catena provata sul database vero**, in transazione annullata e
> attraverso il codice del backend: segnalazione con proprietario →
> `lotto_critical_count = 1`; documento escluso → **0**, e la riga di
> segnalazione **resta** (non è stata ritirata: è il suo documento a non essere
> più in gioco).
>
> 🔴 **E un difetto trovato dalla chiamata vera, che nessun mock vedeva**: fuori
> dall'ORM psycopg 3 consegna i `jsonb` come **stringa**, e una stringa è
> iterabile — il ciclo «una riga per documento» ha girato una volta per
> CARATTERE, scrivendo **55 segnalazioni critiche** su un lotto, una per lettera
> della chiave, **senza nessun errore**. Rimediato con `jsonb_out` più il
> rifiuto esplicito di ciò che non è una lista (verso sicuro: si ripiega su
> «nessun proprietario», che blocca il giro, invece di inventargli documenti), e
> presidiato da due test che riproducono la forma che il driver consegna
> davvero.

---

## 1. Che cosa è già fatto, e funziona

Consegnato oggi sul ramo backend, provato sul database vero in transazione
annullata:

| | |
| --- | --- |
| Il verbo | `POST /api/v1/vendite/lotti/<id>/documenti/escludi/` (`Idempotency-Key`), una `SELECT` sola sulla madre — nessuna orchestrazione in Python, nessun predicato riscritto |
| Il permesso | **riusato** `reset_lotto_fattura_draft`: stesso potere della primitiva che il verbo COMPONE. Un codename nuovo direbbe che è un'altra facoltà |
| Il motivo del pulsante spento | in riga sulla lista documenti — `uscita_blocco_reason` / `_reason_key`, dalla `fn_check_*`, colonne che **nominano il verbo** (§12.5.4) |
| La conseguenza | `n_trascinati` in riga, calcolato **solo dove l'azione è viva**; la conferma lo nomina |
| L'uscita a video | `uscita_motivo` / `uscita_quando` / `uscita_da` in riga; `ESCLUSO` nel vocabolario BE/FE, con il suo colore |
| I quattro codici | policy rigenerata (nessuna classe mossa) + le quattro frasi di ripiego |

⚠️ **Correzione al brief precedente**: il §5.1 annuncia `uscita_il`, ma la
colonna vera è **`uscita_quando`** (doc auto-gen della tabella). Il backend
segue la colonna; il brief andrebbe corretto, perché è la prima cosa che legge
chi arriva dopo.

---

## 2. 🔴 Che cosa NON succede ancora, misurato

Lotto **LTF-0010003**, 2026-09-08, in transazione annullata:

```
segnalazioni critiche vive:  id=7811  gruppo_key=None  «Errore emissione commessa 34137»
documento ORDINE_VENDITA:01a06ce4… → ESCLUSO, motivo e timbro scritti, perimetro intatto (4 righe)
riepilogo PRIMA:  lotto_critical_count = 1
riepilogo DOPO:   lotto_critical_count = 1        ← il lotto NON riparte
```

L'unica segnalazione che blocca ha `gruppo_key = NULL`, cioè *«è del giro»* —
e per il §5.3 una segnalazione del giro **deve** fermare il giro. È corretto: il
difetto non è la regola, è che nessuno dichiara il proprietario.

---

## 3. Perché il backend non può chiuderlo da solo

Il §6.1 dice *«lo dichiara chi scrive»*, e il backend è d'accordo. Ma per farlo
gli servono due cose che oggi non ci sono.

### 3.1 La funzione che SCRIVE la riga non ha il parametro

`vendite.fn_log_pipeline_fase(p_lotto_id, p_stato_doc_fiscale_id, p_fase,
p_status, p_messaggio, p_meta, p_error_code)` è **l'unico** canale con cui il
backend scrive su `vendite.fatturazione_lotti_log`
(`PipelineErrorLogger.log_error` → `VenditePipelineRepository.log_pipeline_fase`).

⇒ Non ha `p_gruppo_key`. Il backend può sapere di chi è la segnalazione e non
avere dove metterlo.

🔵 **Chiediamo**: un parametro `p_gruppo_key text DEFAULT NULL` in coda.
⚠️ **In coda e con default**, per non rompere gli altri chiamanti — e perché il
`NULL` è già il valore che significa «è del giro», quindi il default dice il
vero.

### 3.2 La risoluzione «questa commessa quali documenti alimenta?» non è chiamabile

Il fallimento tipico del pull nasce in `_PullCommesseRunLogger.item_failed`, che
conosce **il `commessa_id`** e non la `gruppo_key`.

La conversione esiste già ed è provata — sta **dentro**
`vendite.fn_segna_esito_gruppo_lotto`:

```sql
SELECT DISTINCT vendite.fn_build_gruppo_fatturabile_key(
           ca.sorgente_tipo_id, ca.sorgente_uid, ca.commessa_id)
  FROM vendite.commesse_attivita ca
 WHERE ca.commessa_id = p_commessa_id
```
più la restrizione al perimetro del lotto, quando il lotto ne dichiara uno.

⛔ **Il backend non la riscrive in Python, ed è una scelta.** Ciò che si
copierebbe non è la costruzione della chiave — quella è già una funzione — ma
**da quale tabella si legge**, che è esattamente la parte fragile: la vista
`script.vw_lotto_documento_righe` porta scritto in testa che leggendo da
`attivita_fatturabili` invece che da `commesse_attivita` le corrispondenze col
perimetro erano **zero su quattro**. Una copia di quella scelta, il giorno che
si sposta, produce chiavi che non agganciano niente — **senza fallire**.

🔵 **Chiediamo**: estrarre quella risoluzione in una funzione di lettura, p.es.
`script.fn_gruppi_di_commessa_nel_lotto(p_lotto_id bigint, p_commessa_id bigint)
RETURNS jsonb` — array ordinato di `gruppo_key`, `[]` se nessuno — e farla
**chiamare** anche da `fn_segna_esito_gruppo_lotto`, così la sede resta una
(§12.5.2: *la madre non riscrive il predicato, lo chiama*).

⚠️ **È 1:N, e cambia la forma della consegna.** Una commessa può alimentare più
documenti — `fn_segna_esito_gruppo_lotto` infatti scrive N righe di esito. Quindi
un fallimento di pull produrrà **una segnalazione per documento**, non una sola
con una chiave scelta a caso: se la commessa ne alimenta tre e se ne dichiarasse
uno, gli altri due resterebbero bloccati per sempre e non togliibili.

---

## 4. Che cosa fa il backend appena i due pezzi ci sono

1. `PipelineErrorLogger.log_error` prende `gruppo_key` e lo passa alla funzione;
2. `_PullCommesseRunLogger.item_failed` chiede i gruppi della commessa nel lotto
   e scrive **una riga per gruppo**;
3. niente altro: il conteggio del §5.3 fa il resto da sé, e il verbo — che c'è
   già — comincia a sbloccare anche questa corsia.

⭐ **Un presidio che nasce gratis.** `_marca_esito_gruppi` logga già un avviso
quando `fn_segna_esito_gruppo_lotto` non marca nessun gruppo per una commessa.
È lo **stesso fatto** che `vendite.vw_segnalazioni_con_documento_ignoto` mostrerà
dall'altro lato: un `gruppo_key` che non corrisponde a nessun esito del lotto.
Le due cose vanno lette insieme il giorno dell'accensione.

---

## 5. Come si vede che è chiuso

### 5.1 ✅ Quello che chiude QUESTO brief — fatto

I due pezzi richiesti esistono e il backend li usa. Provato il 2026-09-08 sul
database vero, in transazione annullata e **attraverso il codice del backend**,
non con una `SELECT` scritta a mano:

| passo | `lotto_critical_count` |
| --- | --- |
| segnalazione con `gruppo_key` **NULL** | **1** — «è del giro», blocca |
| attribuita al documento rotto | **1** — attribuire non sblocca |
| documento **escluso** | **0** — il lotto riparte |

⭐ E la segnalazione **resta a video**, non ritirata: è il suo documento a non
essere più in gioco. Era l'intero punto del §6.1, ed è misurato.

⚠️ Il giro contava sul passaggio del §3.2 e ce l'ha: la conversione commessa →
documenti è **1:N**, quindi un fallimento di pull scrive **una riga per
documento** e non una sola con una chiave scelta fra le tante. Chi ne dichiarasse
uno lascerebbe gli altri bloccati per sempre, perché niente li nomina.

### 5.2 🔵 Quello che NON chiude qui — il §9 del brief padre

La prova a video — due documenti rotti su quattro, si escludono uno alla volta,
il lotto riparte **al secondo** e non prima, poi si rilancia lo step e la
segnalazione riscritta dal task **non** rimette in errore il lotto per un
documento che non ha più — appartiene al cantiere padre e **resta aperta lì**.

⛔ La distinzione non è formale. Qui si è provato che il proprietario **arriva**
e che il conteggio lo legge; là si prova che l'operatore **vede** il giro
ripartire. Un cantiere che chiude il primo e dichiara fatto il secondo è
esattamente il modo in cui un difetto osservato a video sopravvive a una
batteria di test verdi — che è la ragione per cui questo cantiere esiste.

---

## 6. §7 — che cosa serve ancora, e sono tre numeri piccoli

> ⚠️ **Queste richieste hanno cambiato casa il 2026-09-08**, quando questo brief
> è stato chiuso: erano ancora vive, e un documento archiviato non si rilegge.
> Vivono nel **§7-ter del brief padre**
> ([brief-db-uscita-documento-dal-giro](../work-in-progress/brief-db-uscita-documento-dal-giro.md)),
> insieme a una terza che qui non c'era — le due righe di `ui.lista_colonna` per
> la lista 47, senza cui il cancello dello slot `#actions` resta rosso.
> ⇒ Quello che segue resta come **ragionamento**, non come domanda aperta.
>
> Consegnate le due superfici che si potevano fare: la **scheda Critiche** (colonna
> del documento + azione di riga, spenta col motivo) e la **scheda Documenti**
> («Uscito dal giro» con motivo, autore e data). Restano tre cose, e due
> dipendono da voi.

### 6.1 🔵 Il riferimento leggibile accanto alla `gruppo_key`

Sulla scheda Critiche la colonna nuova mostra la **chiave grezza**
(`ORDINE_VENDITA:01a06ce4-…`), perché `fn_list_lotto_segnalazioni` espone
`gruppo_key` e non il riferimento.

⛔ Non l'abbiamo risolto lato backend: l'identità del gruppo si legge da
`vendite.vw_dash_competenza_gruppi` **agganciata al mese del lotto**, e
ricostruirla in SQL di repository sarebbe la seconda sede della stessa
regola — è la ragione per cui la lista dei documenti presi in carico ha un
test che vieta di spezzare la chiave.

🔵 **Chiediamo**: `riferimento` (e volendo `tipo_gruppo`) accanto a `gruppo_key`
nell'output della funzione, con la stessa `JOIN` che usa già la lista dei
documenti. ⚠️ `NULL` resta legittimo — il lavoro può essere uscito dal mese — e
il frontend ripiega sulla chiave, che è il comportamento già in casa.

### 6.2 🔵 Il numero del banner

Il §7 vuole *«Il giro è fermo per **N documenti su M**»* al posto di «N
segnalazioni bloccanti». **N non esiste**:
`vendite.fn_get_lotto_segnalazioni_summary` conta le **segnalazioni**
(`fatture_critical_count`, `lotto_critical_count`, …), non i **documenti
distinti** che ne hanno almeno una viva.

⛔ Non si deriva a video: la scheda è paginata, e la prima pagina non sa quanti
sono in tutto. Contarli lato frontend darebbe un numero che cambia scorrendo.

🔵 **Chiediamo**: un aggregato in più sul riepilogo — i documenti distinti con
almeno una critica viva. ⚠️ Con la `gruppo_key` ora valorizzata è un
`count(DISTINCT gruppo_key)` sullo stesso perimetro che il §5.3 già percorre;
M lo ha già il frontend (il totale della scheda Documenti).

### 6.3 ✅ Il gesto di massa — nostro, non vostro (fatto il 2026-09-08)

Era del backend/frontend, ed è consegnato: selezione sulla scheda Documenti + `run_fan_out` con
esito parziale, il pattern già in casa. Non serve niente da voi.

### 6.4 ⚠️ Una nota sull'ordinamento

La colonna nuova è seedata **non ordinabile**, e non è una scelta di comodo: la
whitelist di `p_order_by` in `fn_list_lotto_segnalazioni` non conosce
`gruppo_key`, e il cancello `test_liste_configurabili_seed` lo verifica leggendo
la doc auto-gen della funzione. Se il §6.1 porta anche `riferimento`, vale la
pena aggiungere entrambi alla whitelist nello stesso giro: raggruppare le
critiche per documento è esattamente come si legge questa scheda.
