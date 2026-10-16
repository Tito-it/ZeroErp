## 📘 Documentazione Concettuale – Funzioni `script.fn_ambiente_installazione()` e `script.fn_ambiente_dichiarato()`

> 👀 **Vedi anche**
>
> [dbops.installazione](/dbzero/dbops/manual/installazione) ·
> [dbops.vw_ambiente_non_dichiarato](/dbzero/dbops/manual/vw_ambiente_non_dichiarato)

### 🎯 Scopo
(16-10-2026 — brief `brief-db-processi-accensione-per-ambiente`)

**In che ambiente gira questa installazione?** `SVILUPPO` o `PRODUZIONE`.
Sono i due lettori di [dbops.installazione](/dbzero/dbops/manual/installazione):
chi ha bisogno dell'ambiente lo chiede qui, e da nessun'altra parte.

| Funzione | Per chi | Se l'ambiente manca |
| --- | --- | --- |
| `fn_ambiente_installazione()` | chi **decide** (la sveglia di un processo, il provisioning dei dati di prova) | errore `E_CONFIG_MANCANTE` |
| `fn_ambiente_dichiarato()` | chi **descrive** (il panorama dei processi, i presidi) | `NULL` |

### Regole

* Come `script.fn_fuso_operativo()`: **niente override** (un ambiente per
  utente o per azienda non ha senso) e **niente ripiego**. Un valore mancante
  non diventa «produzione per prudenza»: l'installazione va dichiarata.
* `NULL` di `fn_ambiente_dichiarato()` non è un valore di ripiego: vuol dire
  «non dichiarato». Chi decide non lo usa.
* `fn_ambiente_installazione()` compone `fn_ambiente_dichiarato()`: la lettura
  sta in un posto solo.

### Test

`db/pgtap/dbops/test-installazione-ambiente-v1.sql` (5, 12, 13).

---

{% include-markdown "signature-core.md" %}
