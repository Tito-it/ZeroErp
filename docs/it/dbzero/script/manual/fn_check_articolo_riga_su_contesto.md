## 📘 Documentazione Concettuale – Funzione `script.fn_check_articolo_riga_su_contesto`

> **Ultimo aggiornamento**: 9 novembre 2026

> 👀 **Vedi anche**
>
> [script.fn_check_articolo_riga](/dbzero/script/manual/fn_check_articolo_riga) — le regole, documento per documento
> [script.fn_articolo_riga_contesto](/dbzero/script/manual/fn_articolo_riga_contesto) — il contesto che riceve
> [catalogo.fn_articoli_ammessi](/dbzero/catalogo/funzioni/fn_articoli_ammessi) — il picker

### 🎯 Scopo Principale

(nasce 2026-10-14, brief-db-articoli-ammessi-per-documento, Lotto 4: A-2, D-6)

Sono **i motivi** della regola sugli articoli di una riga: per un articolo e un documento già
letto (il contesto di [script.fn_articolo_riga_contesto](/dbzero/script/manual/fn_articolo_riga_contesto)),
l'array ordinato dei motivi per cui l'articolo non può stare in quella riga. `[]` vuol dire
ammesso.

Le regole, il loro ordine, i codici e i valori sono quelli scritti in
[script.fn_check_articolo_riga](/dbzero/script/manual/fn_check_articolo_riga): questa funzione è
il suo corpo, staccato dalla lettura del documento. La firma di sempre la chiama dopo aver
costruito il contesto; il picker costruisce il contesto una volta e la chiama per ogni articolo
trovato. Una regola, due chiamanti (A-2).

---

### Note

* Il contesto si costruisce **solo** con `script.fn_articolo_riga_contesto`: la grammatica delle
  chiavi è quella. Un contesto senza documento solleva `E_PARAMETRO_INVALIDO`.
* `p_natura_vendita_id`: la natura congelata della riga, se il chiamante la passa; altrimenti
  quella dell'articolo, come per una riga che ancora non esiste.
* Articolo `NULL` o inesistente: nessun motivo, parla la FK.
* Qui è nato il documento `PROMO_ARTICOLO` (D-6): un solo componente non può avere una promo
  (`E_PROMO_ARTICOLO_SOLO_COMPONENTE`).
* Il kit senza una distinta da oggi in poi
  ([catalogo.fn_articolo_padre_di_distinta_da_oggi](/dbzero/catalogo/funzioni/fn_articolo_padre_di_distinta_da_oggi))
  è il motivo 2 di preventivo, ordine, bolla e di AGGIUNTA e OVERRIDE
  (`E_ARTICOLO_KIT_SENZA_COMPONENTI`). Nel corpo il motivo si costruisce una volta, e i due rami
  lo aggiungono ognuno al suo posto.
* ⭐ Rev 2026-11-03 (`20261103-17`, brief-db-addebito-trasporto-ordine §8.1): **ordine e bolla
  ammettono la merce e l'articolo-onere** (`causale_onere_id` valorizzato). Un servizio che non
  è un onere resta fuori con `E_RIGA_NATURA_NON_AMMESSA`. «È merce» è il building block
  [script.fn_natura_e_merce](/dbzero/script/funzioni/fn_natura_e_merce), sulla natura
  giudicata (quella congelata della riga, altrimenti quella dell'articolo). Che l'onere sia un
  addebito e non un bene lo garantisce l'articolo
  ([catalogo.trgfn_articoli_guard_onere_natura](/dbzero/catalogo/funzioni/trgfn_articoli_guard_onere_natura)).

---
{% include-markdown "signature-core.md" %}
