## 📘 Documentazione Concettuale – Funzione `script.fn_sorgente_chiave_uuid()`

> 👀 **Vedi anche**
>
> **Gemella:** [script.fn_sorgente_chiave_id](/dbzero/script/funzioni/fn_sorgente_chiave_id)
> **Chi la chiama:** [pratiche.fn_stato_sorgente](/dbzero/pratiche/funzioni/fn_stato_sorgente) · [script.vw_pratica_doc_sorgente](/dbzero/script/views/vw_pratica_doc_sorgente) · [script.trgfn_guard_sorgente_polimorfa_testuale](/dbzero/script/funzioni/trgfn_guard_sorgente_polimorfa_testuale) · [vendite.fn_link_commessa_sorgente](/dbzero/vendite/funzioni/fn_link_commessa_sorgente) (dal 20261005-25: la stessa regola per chi salva la chiave) · [vendite.fn_get_sorgente_documento_ref](/dbzero/vendite/funzioni/fn_get_sorgente_documento_ref) · [script.fn_get_sorgente_emittente_sr_id](/dbzero/script/funzioni/fn_get_sorgente_emittente_sr_id) (dal 20261005-26)
> **Convenzione della chiave:** [config.sorgenti](/dbzero/config/tabelle/sorgenti) (`key_selector`)

---

### 🎯 Scopo Principale
(scritta il 05-10-2026)

Un documento collegato a una pratica è indicato da una chiave scritta come **testo**
(`pratiche_sorgenti.sorgente_uid`): l'uid per preventivi e offerte, l'id per gli altri
documenti. Questa funzione riporta quel testo al suo tipo **uuid**, per cercare il documento
sulla colonna `sorgente_chiave_uuid` di `script.vw_stato_sorgente`.

Perché serve: l'applicazione legge con la sicurezza per riga (RLS) attiva, e in quella
condizione un confronto fatto sul testo non può usare l'indice — il database rilegge tutti i
documenti. Il confronto sull'uuid usa l'indice.

| Testo in ingresso | Risultato |
| --- | --- |
| uuid scritto come lo scrive il database (minuscolo, con i trattini) | l'uuid |
| uuid in un'altra forma (maiuscolo, senza trattini, tra graffe) | NULL |
| un numero, o qualunque altra cosa | NULL |
| NULL | NULL |

Non solleva mai errori: «NULL» vuol dire solo «questa chiave non è un uuid».

⚠️ Le forme non canoniche danno NULL **di proposito**: il confronto sul testo, che questa
funzione sostituisce, non le trovava, e i due modi di cercare devono dare lo stesso
risultato.

Presidio: `db/pgtap/pratiche/test-proiezione-stato-sorgente.sql` casi 29-31.

{% include-markdown "signature-core.md" %}
