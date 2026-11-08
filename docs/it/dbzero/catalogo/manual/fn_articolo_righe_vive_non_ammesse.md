## 📘 Documentazione Concettuale – Funzione `catalogo.fn_articolo_righe_vive_non_ammesse`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) — la versione di listino, viva finché non è chiusa
> * [vendite.promo_articoli](/dbzero/vendite/tabelle/promo_articoli) — la promo, viva finché il periodo non è finito
>
> Approfondimento funzioni:
>
> * [catalogo.fn_articolo_correggi_struttura](/dbzero/catalogo/funzioni/fn_articolo_correggi_struttura) — il verbo che la chiama prima e dopo la correzione
> * [script.fn_check_riga_documento_su_contesto](/dbzero/script/funzioni/fn_check_riga_documento_su_contesto) — la check della riga intera che giudica ogni riga
> * [script.fn_articolo_riga_contesto](/dbzero/script/funzioni/fn_articolo_riga_contesto) — il lato documento della check
> * [script.trgfn_righe_guard_articolo_ammesso](/dbzero/script/funzioni/trgfn_righe_guard_articolo_ammesso) — il guard di riga, montato sulle stesse sette tabelle

---

### 🎯 Scopo Principale

Elenca le righe vive di un articolo che la check delle righe di documento non ammette, ciascuna
col primo motivo. Una riga è viva se è attiva e il suo documento non è chiuso.

La legge la porta amministratore della struttura dell'articolo, prima e dopo la correzione.

---

### Che cosa restituisce

Una riga per ogni riga viva con un motivo: il documento (il codice di `config.tipi_entita`), la
testata, la riga e il primo motivo. Le righe ammesse non escono.

| Dove | Riga viva |
| --- | --- |
| preventivo, ordine, bolla, offerta, contratto | attiva, e la fase dello stato non è `CHIUSO` |
| versione di listino | attiva, e la versione non è `CHIUSA` |
| promo | attiva, e il periodo non è finito alla data operativa; testata e riga sono la promo stessa |

Sono le sette tabelle su cui è montato `script.trgfn_righe_guard_articolo_ammesso`. Un pgTAP
diventa rosso se il guard viene montato su una tabella che questa funzione non legge.

---

### La riga si giudica intera

Ogni riga passa da `script.fn_check_riga_documento_su_contesto`, con la natura e il tipo
d'eccezione della riga: il motivo può venire dall'articolo e, su offerta e contratto, anche
dall'erogazione e dalla fonte della quantità. Così una correzione della tipologia non porta una
riga fuori dal perimetro d'erogazione senza che nessuno se ne accorga.

La check è chiamata come per una riga che esiste già, non come una scelta nuova: un articolo
ritirato non rende non ammesse le righe che lo hanno già.

---

### Perché esiste una riga viva non ammessa

Il guard di riga giudica una riga quando nasce e quando cambia articolo (sul listino anche
quando cambia versione), non dopo. Una riga viva
può quindi essere non ammessa per strade che il modello prevede: una riga riaccesa, un'eccezione
`OVERRIDE` il cui articolo esce dalla versione in vigore del listino, un'`AGGIUNTA` il cui
articolo poi ci entra. Per questo il verbo di correzione confronta il prima col dopo, e rifiuta
solo le righe che la correzione rende non ammesse.

---

### Chi la chiama vede le sue righe

La funzione è SECURITY INVOKER: sotto RLS chi la chiama vede solo le righe delle sue aziende. Il
verbo di correzione, SECURITY DEFINER, la chiama su tutte.

---

### Test

* `db/pgtap/catalogo/test-articolo-correzione-righe-aperte-v1.sql` — la funzione legge tutte le
  tabelle dove è montato il guard di riga; una riga già non ammessa prima della correzione non
  la blocca.
* `db/pgtap/vendite/offerte_commerciali/test-righe-ammesse-ai-passi-e-annullo-v1.sql` — vede la
  riga d'offerta uscita dal perimetro d'erogazione.

---

### Note di migrazione

* 2026-10-18 — nasce, per la porta amministratore (brief-db-articoli-ammessi-per-documento).
* 2026-10-21 — la check è la riga intera, con l'erogazione su offerta e contratto: prima una
  correzione della tipologia poteva portare una riga fuori dal perimetro d'erogazione senza
  essere fermata (brief-db-offerta-emissione-ed-erogazione).

---

{% include-markdown "signature-core.md" %}
