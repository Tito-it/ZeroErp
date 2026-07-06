## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_backlog_documenti`

> 👀 **Vedi anche**
>
[config.motivi_fermo](/dbzero/config/tabelle/motivi_fermo)
> [vw_dash_fatturazione_documenti](vw_dash_fatturazione_documenti.md)
> [vw_dash_backlog_riepilogo](vw_dash_backlog_riepilogo.md)

---
### 🎯 Scopo Principale
(latest review 06-07-2026)
**Lente 2 Backlog** (cruscotti fatturazione a due lenti): la lista dei
**non-collegati azionabili** — cosa è fermo prima della commessa, da quanto, e
cosa serve per sbloccarlo. L'asse **non è la competenza** (i fermi non ce
l'hanno): è l'**anzianità** (`data_riferimento`/`anzianita_giorni`) e
l'**azionabilità** (`classe` dalla lookup `config.motivi_fermo`).

---

### Semantica

| Aspetto | Regola |
|---------|--------|
| **Popolazione** | Le righe della union `vw_dash_fatturazione_documenti` con `motivo_fermo IS NOT NULL` e classe **non** `FISIOLOGICO` (regola unica DL-7, nessun caso speciale per area) |
| **`classe`** | Da `config.motivi_fermo` per `codice_interno = motivo_fermo`: `RECUPERABILE` 🟠 (lavoro interno, il numero che conta) · `ANOMALIA` 🔴 (da rivedere) · `SOLLECITO_CLIENTE` 🔵 (palla al cliente, filtro dedicato) |
| **Fail-visible (DB-3)** | LEFT JOIN + `COALESCE(classe, 'ANOMALIA')`: un motivo non mappato (o con lookup disattivata) **compare come anomalia**, non sparisce in silenzio |
| **Conseguenze DL-7** | Contratti: fuori (tutto 🟢 finché manca il push ricorrente) · Offerte: solo `FIGLIO_ABORTITO` 🔴 e `IN_ATTESA_ACCETTAZIONE` 🔵 · Preventivi/Ordini/Commesse: il loro 🟠 |
| **Anzianità (v1 proxy)** | `data_riferimento`: data documento (preventivi/ordini), emissione con fallback (offerte), mese della riga (contratti/commesse). `anzianita_giorni = CURRENT_DATE - data_riferimento` |
| `valore_fermo` / `unita_ferme` | `totale - transitato` (valore NULL per le aree a conteggi) |

---

### Esempio d'uso

```sql
-- Il lavoro di oggi: gli arretrati interni piu' vecchi.
SELECT area, codice, cliente_display, motivo_fermo, azione, anzianita_giorni
FROM vendite.vw_dash_backlog_documenti
WHERE classe = 'RECUPERABILE'
ORDER BY anzianita_giorni DESC;
```

---

### Note operative

* L'**ordinamento** per anzianità è responsabilità del BE (le viste non
  garantiscono ORDER).
* Scope ereditato dalla union: aree documentali via RLS, commesse via GUC
  fail-closed (senza GUC il ramo commesse è vuoto).
* **Nuovo `motivo_fermo`** = append al CSV seed della lookup **prima** di
  emetterlo da una vista; il pgTAP di coerenza (`test-vw-dash-backlog-v1.sql`
  test 4) diventa rosso se un codice emesso non è mappato.
* Il timestamp di transito (DL-5) **non serve qui**: gli elementi del backlog
  non sono ancora transitati — l'anzianità v1 resta sulla data documento.
* Test: `db/pgtap/vendite/test-vw-dash-backlog-v1.sql`.

---

{% include-markdown "signature-core.md" %}
