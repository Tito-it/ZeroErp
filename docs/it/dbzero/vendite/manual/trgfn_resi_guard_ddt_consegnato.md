## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_resi_guard_ddt_consegnato`

> 👀 [vendite.resi](/dbzero/vendite/tabelle/resi) · [vendite.ddt](/dbzero/vendite/tabelle/ddt) ·
> [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

`BEFORE INSERT` su `vendite.resi`. **«Non si rende ciò che non è stato consegnato»**: il reso è
ammesso solo se il DDT sorgente (risolto per `sorgente_uid`) è in stato **`CONSEGNATO`**
(`E_RESO_DDT_NON_CONSEGNATO`).

**Data-driven**: si applica solo alla sorgente `DDT_VENDITA` (l'unica di questa slice); una futura
sorgente `FATTURA` salta il guard. È la **difesa in profondità DB** al vincolo che il BE presidia
anche a livello applicativo.
