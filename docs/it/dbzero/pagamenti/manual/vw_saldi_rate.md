## 📘 Documentazione Concettuale – Vista `pagamenti.vw_saldi_rate`

> 👀 **Vedi anche**
>
> • [pagamenti.fn_get_saldi_rate](/dbzero/pagamenti/funzioni/fn_get_saldi_rate) — **il nucleo**: la formula sta lì, questa vista non ne ha una sua
> • [vendite.vw_fatture_scadenze_lista](/dbzero/vendite/views/vw_fatture_scadenze_lista) — l'identità delle rate, da affiancare a questa per uno scadenzario
> • [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — la regola dei saldi, per chi non è tecnico

---

### 🎯 Scopo Principale

(rev 2026-09-17)

La **porta dello scadenzario**: il saldo di **tutte** le rate visibili in un
passaggio — `saldo · in_lavorazione · incassato · has_movimenti` per
`scadenza_id`. È il nucleo `fn_get_saldi_rate` chiamato con l'array di tutte le
rate (`ARRAY(SELECT id FROM vendite.fatture_scadenze)`, sotto RLS).

«Solo aperte» è un `WHERE`:

```sql
SELECT v.*, sr.saldo, sr.in_lavorazione, sr.incassato
  FROM vendite.vw_fatture_scadenze_lista v
  JOIN pagamenti.vw_saldi_rate sr ON sr.scadenza_id = v.scadenza_id
 WHERE sr.saldo <> 0
 ORDER BY v.data_scadenza;
```

### ⛔ Non è la porta del picker sulla pagina

Questa vista aggrega **tutto**: è il costo onesto dello scadenzario, non quello di
una pagina. Chi ha gli id della pagina chiama il nucleo con quell'array, che
scende negli indici. Chi ha una rata sola usa `fn_get_saldo_rata`.

### Regole principali

* `security_invoker=on`, da **ri-specificare** a ogni `CREATE OR REPLACE`: il
  nucleo legge tre tabelle con policy, e la vista non deve leggerle coi diritti
  del proprietario.
* Nessuna formula propria: cambiare il nucleo cambia anche questa vista, per
  costruzione (il pgTAP del nucleo lo asserisce, test 17).

{% include-markdown "signature-core.md" %}
