## 📘 Documentazione Concettuale – Funzione `dbops.fn_admin_merge_comune`

> 👀 **Vedi anche**
>
> • [dbops.fn_admin_merge_stradario](/dbzero/dbops/funzioni/fn_admin_merge_stradario)
> • [config.comuni](/dbzero/config/tabelle/comuni)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Fonde due comuni**: sposta i riferimenti dal comune di origine a quello di destinazione e
registra l'evento come trasformazione amministrativa.

Serve a un fatto del mondo reale: i comuni si fondono, cambiano nome, vengono soppressi. Gli
indirizzi già registrati devono continuare a essere validi, e le ricerche sul comune nuovo
devono trovare anche ciò che era stato inserito col vecchio.

⭐ Scrive in `dbops.audit_log` **prima** di operare, e non dopo: se qualcosa fallisce a metà,
resta traccia del tentativo. Una fusione anagrafica tocca molte righe, e sapere che è stata
avviata è parte del poterla diagnosticare.

⚠️ È un'operazione **amministrativa e non reversibile** dall'applicazione: il prefisso
`fn_admin_` lo dichiara. Va eseguita sapendo che cosa tocca.

---

{% include-markdown "signature-core.md" %}
