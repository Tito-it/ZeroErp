## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_resi_normalize`

> 👀 [vendite.resi](/dbzero/vendite/tabelle/resi) · [vendite.ddt](/dbzero/vendite/tabelle/ddt) ·
> [vendite.trgfn_ddt_normalize](/dbzero/vendite/funzioni/trgfn_ddt_normalize) (mirror)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

`BEFORE INSERT/UPDATE` su `vendite.resi`. Normalizza la testata reso: (1) anno/data se il numero è
presente; (2) **eredita i denormalizzati dal DDT sorgente** — mirror nella forma di
`trgfn_ddt_normalize`, ma la **fonte è il DDT** (JOIN `vendite.ddt` su `uid = sorgente_uid`,
sorgente `DDT_VENDITA`): `billing_account_id`, `destinatario_soggetto_ruolo_id`, `utility_id`,
`valuta_id`, `emittente_fiscale_id`; (3) fallback emittente da `billing_account` (predisposizione
standalone, inerte in questa slice).

Firing prima del guard `z10` emittente-BA, così questo vede i valori **finali** risolti.
