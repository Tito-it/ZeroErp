## 📘 Documentazione Concettuale – Vista `magazzino.vw_costo_medio`

> 👀 **Vedi anche**
>
> • [magazzino.costo_medio](/dbzero/magazzino/tabelle/costo_medio)
> • [magazzino.vw_costo_medio_globale](/dbzero/magazzino/views/vw_costo_medio_globale)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Il **costo medio ponderato** per articolo × magazzino: `valore / qta`, calcolato al volo dagli
accumulatori di `magazzino.costo_medio`.

⭐ Il quoziente non è memorizzato apposta: tenere `valore` e `qta` separati permette di
aggiornare la media per incrementi successivi senza accumulare errori di arrotondamento. La
divisione si fa una volta sola, alla lettura.

---

### La divisione per zero restituisce `NULL`, non un errore

```sql
CASE WHEN qta <> 0 THEN valore / qta ELSE NULL END
```

Il caso è reale: `qta` arriva a zero quando tutto è stato scaricato, e `valore` può restare
diverso da zero per effetto degli arrotondamenti.

⚠️ Quel `NULL` significa **«costo non determinabile»**, non «costo zero» — e si propaga a
`vw_giacenza_valorizzata`, dove diventa un valore nullo. Trattarlo come zero in un totale è
l'errore da non fare.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
