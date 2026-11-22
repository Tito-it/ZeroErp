## 📘 Documentazione Concettuale – Tabella `anagrafiche.soggetti_titoli_iva`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_titolo_iva](/dbzero/config/tabelle/tipi_titolo_iva) — di che specie è il titolo, e se ha un tetto
> * [anagrafiche.soggetti_titoli_iva_ambiti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_ambiti) — per che cosa vale un titolo ristretto
> * [anagrafiche.soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti) — il registro del plafond
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — a chi il titolo è presentato
> * [config.iva](/dbzero/config/tabelle/iva) — il codice che prende il posto di quello ordinario
> * [config.tipi_titolo_iva_tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_titolo_iva_tipi_soggetto_dettaglio) — quali titoli ammette ogni natura
>
> Approfondimento funzioni:
>
> * [vendite.fn_resolve_iva_riga](/dbzero/vendite/funzioni/fn_resolve_iva_riga) — il risolutore, che sceglie il titolo di una riga
> * [anagrafiche.fn_consuma_plafond_titolo_iva_righe](/dbzero/anagrafiche/funzioni/fn_consuma_plafond_titolo_iva_righe) — chi consuma il tetto
> * [anagrafiche.trgfn_soggetti_titoli_iva_guard_coerenza](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_guard_coerenza) — plafond e ambito coerenti col tipo
> * [anagrafiche.fn_check_titolo_iva_ambito](/dbzero/anagrafiche/funzioni/fn_check_titolo_iva_ambito) — l'ambito che sta in piedi
> * [anagrafiche.trgfn_soggetti_titoli_iva_guard_tipo_soggetto](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_guard_tipo_soggetto) — il titolo ammesso dalla natura
> * [anagrafiche.fn_check_cambio_natura_soggetto](/dbzero/anagrafiche/funzioni/fn_check_cambio_natura_soggetto) — la natura che cambia sotto un titolo
>
> Guide:
>
> * [Il risolutore IVA di riga](/guide/iva-risolutore-di-riga) — come un titolo cambia l'aliquota di una riga

---

### 🎯 Scopo Principale

`anagrafiche.soggetti_titoli_iva` registra i titoli per cui un soggetto non paga l'IVA ordinaria: una dichiarazione
d'intento, un uso industriale del gas, un'agevolazione per disabilità, la qualifica di cooperativa sociale. Ogni
riga è un documento con le sue date, il suo destinatario e il codice IVA che sostituisce quello ordinario.

---

### ⭐ Un titolo non è un flag: è un documento

L'aliquota ordinaria la decide la **merce** e il suo uso. Il cliente può solo **sostituirla**, e solo mostrando una
carta: un titolo ha una prova (protocollo, data di ricezione, riferimento), una data d'inizio e una di fine, dice a
chi è stato presentato e per che cosa vale. Registrato una volta, vale da solo su tutti i documenti finché è in
vigore, e nessuno lo digita più.

Non c'è un «codice IVA del cliente» né sul cliente né sul soggetto: un valore che vincerebbe su tutto perché
nessuno gli ha detto dove fermarsi.

---

### Il titolare è il soggetto, il destinatario è l'emittente

Il titolo **appartiene al soggetto**: è lui l'esportatore abituale, non un suo contratto. Un cliente con tre
forniture ha una dichiarazione, non tre.

Ma la dichiarazione si **presenta a un fornitore preciso**, con un protocollo e un importo suoi: lo stesso
esportatore che compra da due aziende del gruppo presenta due dichiarazioni, ognuna col suo plafond. Per questo la
riga porta anche l'emittente, ed è in tutte le chiavi: senza, i due plafond si consumerebbero da un contatore solo,
e lo si vedrebbe solo su un plafond esaurito prima del dovuto. Se chi scrive non nomina l'emittente, lo mette il
trigger dell'emittente predefinito, o la riga è rifiutata.

---

### L'ambito: «vale per tutto» oppure «vale per queste voci»

`ambito` è dichiarato, mai dedotto da una tabella vuota: `TUTTO` copre ogni riga di documento, `RISTRETTO` copre
solo ciò che dicono le righe di `anagrafiche.soggetti_titoli_iva_ambiti`.

Il titolo si valuta **riga per riga**: un'agevolazione limitata a due articoli, su un documento di dieci righe, dà
due righe agevolate e otto ordinarie.

Un titolo `RISTRETTO` senza righe di ambito non copre niente, ed è ammesso: si costruisce in due passi, prima il
titolo e poi le sue righe, e chi calcola l'IVA lo legge come «nessuna voce coperta», la direzione sicura.

---

### Due titoli uguali non convivono

Due titoli dello stesso soggetto, verso lo stesso emittente, dello stesso tipo e in periodi che si toccano sono
un'ambiguità: non c'è modo di dire quale si applica. La chiave passa però per l'ambito, che per i titoli ristretti
sta in una tabella figlia, e la divisione è dichiarata:

| Caso | Chi lo chiude |
| --- | --- |
| due titoli attivi che valgono per tutto | il vincolo di esclusione `ex_soggetti_titoli_iva_no_overlap` |
| due titoli ristretti che coprono lo stesso oggetto allo stesso livello | `anagrafiche.fn_check_titolo_iva_ambito`, chiamata dai due guard dell'ambito |

Titoli di **tipo diverso** convivono, e titoli ristretti su **livelli diversi** pure: quale vince su una riga
(articolo, poi categoria di merce, poi tutto) lo decide il risolutore.

---

### Il plafond, e perché il consumato è una somma

Solo alcuni tipi hanno un tetto che si consuma (`config.tipi_titolo_iva.ha_plafond`). Che il plafond ci sia se e
solo se il tipo lo prevede lo tiene `anagrafiche.trgfn_soggetti_titoli_iva_guard_coerenza`, sui due versi: un tetto
assente dove serve, e un tetto presente dove nessuno lo consumerebbe.

`imponibile_utilizzato` è memorizzato, ma è la **somma** del registro dei movimenti, e la scrive solo
l'accumulatore: ogni fattura ne consuma un pezzo, ogni nota di credito ne restituisce uno, ogni forzatura è una
riga col suo motivo, e una forzatura sbagliata si annulla con un'altra riga. Si memorizza l'usato e non il residuo
perché l'usato si confronta col fatturato; il residuo è aritmetica.

---

### ⛔ Un titolo con righe figlie non si spegne: si chiude

`attivo` passa a falso solo se il titolo non ha né righe di ambito né movimenti di plafond: con le une o con gli
altri la disattivazione è rifiutata (`E_ATTIVO_BLOCK_CHILDREN_EXIST`). Le righe di ambito si possono togliere; i
movimenti no, perché il registro non si cancella. Un titolo che ha consumato plafond quindi non si spegne mai: per
farlo finire si chiude `valido_al`. Per la stessa ragione la regola della natura ammessa guarda la data di fine e
non il solo `attivo`.

Il titolo regge solo su padri attivi: soggetto, emittente, tipo di titolo e codice IVA devono esserlo alla
conferma dell'operazione (`E_ATTIVO_PADRE_NON_ATTIVO`). Le date devono essere in ordine, la fine non prima
dell'inizio.

---

### Chi legge i titoli

* `vendite.fn_resolve_iva_riga`, il risolutore IVA di riga: dopo aver stabilito l'aliquota della merce guarda se il
  soggetto ha un titolo che la sostituisce **su quella riga**. Dice quale titolo vale, non consuma.
* `anagrafiche.fn_consuma_plafond_titolo_iva_righe`, che consuma il tetto quando una fattura diventa definitiva,
  sotto un lock sulla riga del titolo.
* `script.fn_check_annullo_movimento_titolo_iva` e `anagrafiche.vw_stiva_movimenti_dettaglio`, per l'annullo delle
  forzature.
* I controlli della natura ammessa: il guard sul titolo, il cambio di natura del soggetto, il ritiro di una riga
  della matrice.

---

### Chi può vederli

La tabella ha la RLS: una sessione con ruolo applicativo `OPERATORE` vede e scrive solo i titoli presentati a un
emittente del suo perimetro (tutti, se il perimetro è «tutti gli emittenti»); le sessioni degli altri ruoli
applicativi non ne vedono nessuno. Senza, l'elenco, protocolli e plafond compresi, sarebbe comune a tutte le
aziende, e una lista più lunga del vero non la mette in dubbio nessuno.

I controlli che devono vedere i titoli di tutti (il cambio di natura, il ritiro di matrice) passano da lettori
privilegiati che rispondono solo un numero o un sì, mai i dati di un titolo.

---

### ⛔ Due cose che sembrano IVA e non stanno qui

* **Lo split payment e la qualifica di pubblica amministrazione** non sono titoli: non cambiano l'aliquota. Lo
  split payment cambia chi versa l'imposta all'erario. Stanno su `anagrafiche.soggetti`.
* **L'aliquota ordinaria** la dicono la merce e il suo uso: articolo, catena del prezzo, tipo di utenza. Il
  cliente non entra in quella domanda.

---

### Codici errore

I codici che i trigger della tabella sollevano su una scrittura del titolo:

* `E_TITOLO_IVA_PLAFOND_MANCANTE`, `E_TITOLO_IVA_PLAFOND_NON_AMMESSO`, `E_TITOLO_IVA_AMBITO_NON_AMMESSO` —
  plafond e ambito incoerenti col tipo (`anagrafiche.trgfn_soggetti_titoli_iva_guard_coerenza`).
* `E_TITOLO_IVA_AMBITO_SOVRAPPOSTO` — un pareggio di ambito creato cambiando il titolo
  (`anagrafiche.trgfn_soggetti_titoli_iva_guard_ambito`).
* `E_TITOLO_IVA_NON_AMMESSO_PER_TIPO_SOGGETTO`, `E_DATO_FISCALE_SENZA_TIPO_SOGGETTO` — la natura del titolare
  (`anagrafiche.trgfn_soggetti_titoli_iva_guard_tipo_soggetto`).
* `E_ATTIVO_BLOCK_CHILDREN_EXIST` — la disattivazione di un titolo con righe figlie.
* `E_ATTIVO_PADRE_NON_ATTIVO` — un padre spento, alla conferma.

La sovrapposizione di due titoli che valgono per tutto è rifiutata dal vincolo di esclusione, con l'errore del
vincolo.

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-titoli-iva.sql` — i tipi e il loro tetto, plafond mancante o di troppo, la
  sovrapposizione dei titoli totali (e il periodo che non si sovrappone, che passa), l'ambito su un titolo totale,
  il pareggio e i livelli diversi che passano, il periodo allargato che fa scattare il guard, l'accumulatore e la
  nota di credito che restituisce.
* `db/pgtap/anagrafiche/test-soggetti-titoli-iva-due-emittenti.sql` — lo stesso soggetto verso due emittenti ha due
  plafond, e il consumo dell'uno non tocca l'altro.
* `db/pgtap/anagrafiche/test-soggetti-titoli-iva-tipo-soggetto-v1.sql` — la natura ammessa, sulle tre strade.

---

### Note di migrazione

* 2026-08-29 — nasce col suo ambito e il registro del plafond. Prende il posto di `anagrafiche.clienti.iva_id`, il
  codice IVA del cliente, che è stato tolto e non spostato sul soggetto.
* 2026-10-10 — nasce la regola della natura ammessa.
* 2026-11-14 — il controllo della natura che cambia passa ai motivi di `anagrafiche.fn_check_cambio_natura_soggetto`,
  che rifiuta anche per i titoli presentati ad altri emittenti.

---

{% include-markdown "it/dbzero/anagrafiche/_titolo-iva-per-natura.md" %}

---

{% include-markdown "signature-core.md" %}
