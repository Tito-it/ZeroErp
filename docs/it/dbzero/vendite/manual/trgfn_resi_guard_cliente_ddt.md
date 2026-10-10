## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_resi_guard_cliente_ddt`

> 👀 **Vedi anche**
>
> [vendite.trgfn_ddt_guard_cliente_sorgente](/dbzero/vendite/funzioni/trgfn_ddt_guard_cliente_sorgente) — la stessa regola sulla bolla
> [vendite.trgfn_resi_guard_ddt_consegnato](/dbzero/vendite/funzioni/trgfn_resi_guard_ddt_consegnato) — il reso nasce solo da una bolla consegnata
> [vendite.trgfn_resi_normalize](/dbzero/vendite/funzioni/trgfn_resi_normalize) — chi copia dalla bolla billing account, utility e destinatario

---

### 🎯 Scopo Principale

**Un reso ha il cliente della bolla da cui nasce, anche quando la bolla non ne
ha uno.**

Il reso non nasce mai da solo: ha sempre una bolla d'origine. Il suo billing
account è quello della bolla, **vuoto compreso**: dal reso di una bolla di
conto lavoro, che non ha cliente, nasce un reso senza cliente.

Il guard gira quando il reso nasce e quando cambiano il suo billing account o
la sua sorgente, in qualunque stato. Se il cliente non è quello della bolla:
`E_DOC_CLIENTE_DIVERSO_DA_SORGENTE`.

Il reso non ha un blocco «fuori bozza» sul cliente: la sua bolla è consegnata,
quindi il cliente della bolla è già bloccato, e questo guard tiene il reso
uguale a lei. Un secondo blocco direbbe la stessa cosa due volte.

---

### 🔒 Una bolla che non si trova

Dal 10 ottobre 2026 (brief `brief-db-esecutivi-ba-coppia`, decisione di Tid)
una bolla d'origine dichiarata e **non trovata**, cioè inesistente o di
un'altra azienda, è un errore: `E_DOC_SORGENTE_NON_TROVATA`. Prima il guard
lasciava passare.

Quando il reso **nasce** parla prima `trgfn_resi_guard_ddt_consegnato`, che
una bolla non trovata la rifiuta come «non consegnata». Questo guard è
l'unico a guardare un reso **spostato** su un'altra bolla.

---

### 🧪 Test

`db/pgtap/vendite/test-esecutivi-ba-coppia-v1.sql`: test 21 (reso col cliente
di un'altra bolla), 35 (reso senza cliente da una bolla senza cliente), 37
(reso spostato su una bolla che non esiste).
