## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_articoli_guard_listino_se_composito`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — la tabella su cui il guard è montato
> * [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe) — le righe di listino che il guard interroga
>
> Approfondimento funzioni:
>
> * [script.fn_check_articolo_riga_su_contesto](/dbzero/script/funzioni/fn_check_articolo_riga_su_contesto) — il lato riga: il motivo `E_LISTINO_RIGA_COMPOSITO_VIETATO` della versione di listino
> * [script.trgfn_righe_guard_articolo_ammesso](/dbzero/script/funzioni/trgfn_righe_guard_articolo_ammesso) — il guard delle righe di listino che solleva quel motivo
> * [catalogo.trgfn_articoli_guard_struttura_se_usato](/dbzero/catalogo/funzioni/trgfn_articoli_guard_struttura_se_usato) — il guard «usato», che sulla stessa modifica scatta dopo questo
> * [catalogo.fn_articolo_righe_vive_non_ammesse](/dbzero/catalogo/funzioni/fn_articolo_righe_vive_non_ammesse) — la stessa regola, per la porta amministratore
>
> Guide:
>
> * [Gestione listini](/guide/gestione-listini) — un composito entra in listino come bundle

---

### 🎯 Scopo Principale

Impedisce che un articolo diventi composito se ha già righe attive in `vendite.listini_righe`.
Il prezzo di un composito è la somma dei suoi componenti: un prezzo diretto in listino, per un
composito, non ha senso.

È il lato articolo della regola «un composito non sta in listino come riga semplice». Il lato
riga è il motivo `E_LISTINO_RIGA_COMPOSITO_VIETATO` della check delle righe di listino: un
composito entra nella versione come bundle, coi prezzi dei componenti.

---

### Quando scatta

Il guard è `BEFORE UPDATE OF is_composito`, e giudica solo il passaggio da falso a vero. Se
l'articolo ha almeno una riga di listino attiva, in qualunque versione, il cambio è rifiutato.

Il passaggio inverso, da composito a semplice, non lo guarda: con una distinta in vigore lo
ferma `catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva`.

---

### Con il guard «usato» si sovrappone

Un articolo con righe di listino è già usato, e un articolo usato non cambia `is_composito`
(`catalogo.trgfn_articoli_guard_struttura_se_usato`). Fuori dalla porta amministratore questo
guard parla per primo solo perché i trigger scattano in ordine di nome; senza di lui, la stessa
modifica sarebbe rifiutata dal guard «usato».

Fa differenza solo dentro la porta amministratore (`catalogo.fn_articolo_correggi_struttura`),
che apre il guard «usato» ma non questo.

---

### ⚠️ Che cosa oggi non copre

* **Il rimedio che suggerisce non funziona.** Il dettaglio dell'errore dice di disattivare le
  righe di listino prima di rendere composito l'articolo. Ma una riga spenta conta ancora come
  uso: dopo la disattivazione il cambio è rifiutato dal guard «usato»
  (`E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE`).
* **Dentro la porta contraddice la regola delle righe vive.** Il guard conta le righe attive
  anche di una versione di listino `CHIUSA`. La porta amministratore, invece, per contratto
  rigiudica solo le righe vive, e una versione chiusa non blocca
  (`catalogo.fn_articolo_righe_vive_non_ammesse`). Una correzione a composito di un articolo che
  sta solo in versioni chiuse è rifiutata qui.
* **La regola è scritta tre volte.** Qui, nel motivo della check di riga e nella porta: le tre
  copie non dicono la stessa cosa.
* **L'errore non porta il `tx_id` della riga.**

---

### Codici errore

* `E_LISTINO_RIGA_COMPOSITO_VIETATO` — l'articolo diventa composito e ha almeno una riga attiva
  in un listino. Il messaggio porta il codice dell'articolo.

---

### Test

Nessun test pgTAP prova il lato articolo. Il lato riga lo prova
`db/pgtap/catalogo/test-listino-distinta-articolo-ammesso-v1.sql`: un composito è rifiutato
come riga semplice di una versione di listino, col motivo `COMPOSITO_COME_BUNDLE`.

---

### Note di migrazione

* 2026-05-13 — nasce, insieme a un guard sulle righe di listino che rifiutava i compositi.
* 2026-10-13 — quel guard sulle righe è ritirato: il lato riga diventa un motivo della check
  comune delle righe di documento (brief-db-articoli-ammessi-per-documento).

---

{% include-markdown "signature-core.md" %}
