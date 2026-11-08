## 📘 Documentazione Concettuale – Funzione `catalogo.fn_articolo_usato`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — la regola «un articolo usato non cambia la sua struttura»
> * [dbops.lock_columns_conditional](/dbzero/dbops/tabelle/lock_columns_conditional) — le regole del form che chiamano questo predicato
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_articoli_guard_struttura_se_usato](/dbzero/catalogo/funzioni/trgfn_articoli_guard_struttura_se_usato) — il guard che legge questo predicato
> * [catalogo.fn_articolo_colonne_struttura](/dbzero/catalogo/funzioni/fn_articolo_colonne_struttura) — le colonne che il predicato spegne nel form

---

### 🎯 Scopo Principale

Dice se un articolo è usato: se compare in un documento, in un listino, in una commessa o in
magazzino, in qualunque stato. È il predicato unico della regola «un articolo usato non cambia
la sua struttura», e lo leggono il guard sull'articolo e il form.

Un id vuoto risponde falso.

---

### Che cosa conta come uso

Una riga in una tabella che punta all'articolo con una FK, **in qualunque stato**: anche chiusa,
annullata o con `attivo = false`. I documenti chiusi si rileggono (fatture, resi, giacenze), e
devono restare coerenti con l'articolo.

⭐ Le tabelle non sono elencate: si leggono da `pg_constraint` a ogni chiamata. Una tabella
nuova che punta all'articolo conta da sola come uso, senza toccare la funzione.

Si escludono, dichiarate nella funzione, le tabelle che sono anagrafica dell'articolo e non un
suo uso:

* `catalogo.articoli_componenti` — la distinta è struttura dell'articolo, e ha i suoi guard;
* `catalogo.articoli_uom_operativa` — le unità dell'articolo;
* `catalogo.note_articoli` — le note;
* `vendite.articoli_descrizioni_aggiuntive` — le descrizioni;
* `vendite.articolo_regole_fatturazione` — le regole di fatturazione dell'articolo;
* `anagrafiche.soggetti_titoli_iva_ambiti` — la configurazione fiscale.

---

### ⭐ Perché SECURITY DEFINER

Gli articoli sono unici per tutte le aziende (il catalogo non ha RLS), mentre i documenti hanno
la RLS per emittente. Letto con la RLS di chi modifica l'articolo, il predicato non vedrebbe i
documenti delle altre aziende, e un articolo usato da un'altra azienda risulterebbe libero.

La funzione restituisce solo un vero o falso: non rivela niente di quei documenti. Il
`search_path` è bloccato, e l'SQL dinamico usa solo la tabella e la colonna lette dal catalogo
di sistema, con l'id dell'articolo come parametro.

---

### ⚠️ Che cosa oggi non copre

La funzione considera solo le FK a una colonna, e confronta quella colonna con l'id
dell'articolo, senza guardare a quale colonna dell'articolo la FK punta.

* **Una FK verso un'altra chiave rompe il predicato.** Una FK verso `codice`, che il modello
  ammette, fa fallire la chiamata con un errore di tipo, e con lei il guard e il form.
* **Una FK composita è saltata in silenzio.** Una tabella che punta all'articolo con una chiave
  a più colonne non conta come uso: è l'opposto del «fail-closed» che il predicato promette.

---

### Test

* `db/pgtap/catalogo/test-articolo-usato-struttura-v1.sql` — un articolo appena costruito non è
  usato; in una riga di preventivo in bozza lo è; una riga spenta conta ancora; un preventivo di
  un'altra azienda conta lo stesso.
* `db/pgtap/catalogo/test-articolo-colonne-struttura-v1.sql` — le colonne che il predicato spegne
  nel form sono quelle che la porta amministratore riapre.

---

### Note di migrazione

* 2026-10-13 — nasce, insieme al guard «usato» (brief-db-articoli-ammessi-per-documento).

---

{% include-markdown "signature-core.md" %}
