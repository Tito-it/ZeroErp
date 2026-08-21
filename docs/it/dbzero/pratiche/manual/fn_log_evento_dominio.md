## 📘 Documentazione Concettuale – Funzione `pratiche.fn_log_evento_dominio()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [pratiche.giornale](/dbzero/pratiche/tabelle/giornale)
> • [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
>
Approfondimento funzioni:
> • [pratiche.trgfn_sospensioni_giornale_ins](/dbzero/pratiche/funzioni/trgfn_sospensioni_giornale_ins)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Canale controllato** perché gli handler applicativi possano scrivere un evento di dominio
(`DOMINIO_*`) sul giornale append-only della pratica — per esempio
`DOMINIO_COMMESSA_CREATA` o `DOMINIO_PREVENTIVO_EVASO` scritti da `vendita.push_preventivo`.

Esiste per **non lasciare che gli handler scrivano direttamente** su `pratiche.giornale`:
qui i parametri sono validati, l'origine è fissata a `'HANDLER'` e il `tx_id` è quello di
sessione, quindi l'evento resta correlabile alla transazione che l'ha prodotto.

Ritorna l'`id` della riga inserita.

---

### ⭐ La conformità del nome non la garantisce questa funzione

`fn_log_evento_dominio` **non verifica** che `p_tipo_evento` abbia la forma `DOMINIO_*`. A
farlo è il `CHECK chk_giornale_azione` sulla tabella, che ammette gli 11 eventi di motore
oppure qualunque codice nella forma `^DOMINIO_[A-Z][A-Z0-9_]*$`.

È una scelta, non una dimenticanza: la regola vive **sul dato**, quindi vale anche per chi
scrivesse sul giornale per un'altra strada.

⚠️ La conseguenza per il chiamante: un nome non conforme non produce un errore di dominio ma
una **violazione di CHECK** (SQLSTATE `23514`), senza codice `E_*` e senza riga in
`error_log`. Il messaggio parla di un vincolo, non di un evento sbagliato.

---

### `flusso_id` è opzionale — e il `NULL` significa qualcosa

Un evento può essere **della pratica** (`flusso_id` nullo) o **di una fase** (`flusso_id`
valorizzato). Il guard riflette la distinzione: `NULL` è ammesso, ma un valore `<= 0` no.

È lo stesso asse che i trigger delle sospensioni rendono esplicito nel `dettaglio` con il
campo `livello` (`PRATICA` / `FLUSSO`). ⚠️ Qui quel campo **non** viene aggiunto: chi legge il
giornale distingue i due livelli solo dalla presenza di `flusso_id`.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_PARAMETRO_INVALIDO` | `pratica_id` nullo o `<= 0`; `flusso_id` valorizzato ma `<= 0`; `tipo_evento` nullo o vuoto |

Tre guard distinti, tutti via `script.fn_log_and_raise_error` con `area = 'pratiche'`.

⚠️ Condividono lo **stesso codice**: per sapere quale parametro fosse sbagliato serve il
`context` JSONB, che riporta `param` e `valore`.

---

{% include-markdown "signature-core.md" %}
