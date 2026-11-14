## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_resi_gen_numero`

> 👀 [vendite.resi](/dbzero/vendite/tabelle/resi) ·
> [vendite.registri_fatturazione](/dbzero/vendite/manual/registri_fatturazione) ·
> [vendite.fn_assegna_numero_documento](/dbzero/vendite/manual/fn_assegna_numero_documento) (i sei passi) ·
> [vendite.trgfn_v_resi_protect_num](/dbzero/vendite/funzioni/trgfn_v_resi_protect_num) (immutabilità) ·
> [vendite.trgfn_ddt_gen_numero_emesso](/dbzero/vendite/manual/trgfn_ddt_gen_numero_emesso) (stesso schema)

---

### 🎯 Scopo Principale

(rev 2026-08-31, sera)

`BEFORE INSERT/UPDATE` su `vendite.resi`. Assegna il `numero` **quando il reso entra nello stato di
emissione** del suo vocabolario (`config.stati_doc_reso.emissione`, oggi `CONFERMATO`): in bozza resta
vuoto, così una bozza scartata non consuma un numero.

---

### Qui resta il momento, il resto è altrove

⭐ I sei passi della numerazione — registro, anno, progressivo, formato,
composizione — stanno in
[`vendite.fn_assegna_numero_documento`](/dbzero/vendite/manual/fn_assegna_numero_documento),
condivisi con documenti di trasporto, ordini e commesse.

Quello che resta scritto qui è **quando**: la conferma. È l'unica cosa che
distingue questo documento dagli altri tre, ed è per questo che non è stata
centralizzata insieme al resto.

---

### ⚠️ Da dove viene la forma del numero

Dal **registro** — prefisso, suffisso e numero di cifre — in una lettura sola.

⛔ **Non da `config.sistema_codici`**: la riga `reso` è uscita da quel catalogo il
31 agosto 2026, insieme a quelle di documenti di trasporto, ordini e commesse. I
valori con cui un registro nasce stanno in
[`vendite.famiglie_documento`](/dbzero/vendite/manual/famiglie_documento).

⚠️ E la sequenza `vendite.resi_numero_seq` **non c'entra più niente**: il contatore
è `vendite.registri_fatturazione_progressivi`, per registro e per anno.

---

L'immutabilità dopo l'assegnazione è garantita da
[`vendite.trgfn_v_resi_protect_num`](/dbzero/vendite/funzioni/trgfn_v_resi_protect_num).

---

{% include-markdown "signature-core.md" %}
