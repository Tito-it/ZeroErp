## 📘 Documentazione Concettuale – Funzione `acquisti.fn_get_acquisti_note()`

> 👀 **Vedi anche**
>
> • [script.fn_get_note](/dbzero/script/funzioni/fn_get_note)
> • [acquisti.note](/dbzero/acquisti/tabelle/note)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Wrapper** su `script.fn_get_note` per la tabella `acquisti.note`. Il corpo è una riga:

```sql
SELECT * FROM script.fn_get_note('acquisti.note'::regclass, _target_tipo, _target_id, ...);
```

Non contiene logica propria. Esiste per non far passare a ogni chiamante il `regclass` della
partizione giusta — e perché ogni dominio abbia lo stesso verbo con lo stesso nome.

⭐ È il gemello esatto di `magazzino.fn_get_magazzino_note`: la stessa funzione parametrizzata
sulla tabella. Chi ne aggiunge uno per un dominio nuovo copia questa forma.

---

### I parametri

`_include_doc` e `_include_righe` decidono se raccogliere le note di testata, quelle di riga o
entrambe; `_only_visible` filtra quelle non visibili. I default (`true`, `true`, `true`) danno
il comportamento di stampa.

⚠️ Il `regclass` è **cablato nel corpo**: se un giorno le note di acquisti cambiassero
partizione, questa funzione va riscritta — non è configurabile dall'esterno.

---

{% include-markdown "it/dbzero/acquisti/_dominio-acquisti.md" %}

---

{% include-markdown "signature-core.md" %}
