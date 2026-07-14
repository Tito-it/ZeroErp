## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_resi_gen_numero`

> 👀 [vendite.resi](/dbzero/vendite/tabelle/resi) · [config.sistema_codici](/dbzero/config/tabelle/sistema_codici) ·
> [vendite.trgfn_v_resi_protect_num](/dbzero/vendite/funzioni/trgfn_v_resi_protect_num) (immutabilità) ·
> [vendite.trgfn_ddt_gen_numero_emesso](/dbzero/vendite/funzioni/trgfn_ddt_gen_numero_emesso) (mirror)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

`BEFORE INSERT/UPDATE` su `vendite.resi`. Assegna `numero` **alla transizione a `CONFERMATO`** (NULL
in DRAFT → nessun buco fiscale da bozze scartate), **fuori** dal framework `sistema_codici` che
numera all'INSERT (riga `reso` con `usa_sequenza=false`). Formato da `sistema_codici`
(prefisso/separatore/lunghezza) + sequenza `vendite.resi_numero_seq`. Mirror del pattern fatture/DDT.
L'immutabilità è garantita da `trgfn_v_resi_protect_num`.
