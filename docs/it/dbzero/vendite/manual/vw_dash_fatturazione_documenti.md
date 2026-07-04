## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_fatturazione_documenti`

> 👀 **Vedi anche**
>
Resolver di area (rami della union):
>
[vw_dash_fatturazione_preventivi](vw_dash_fatturazione_preventivi.md)
> [vw_dash_fatturazione_ordini](vw_dash_fatturazione_ordini.md)
> [vw_dash_fatturazione_offerte](vw_dash_fatturazione_offerte.md)
> [vw_dash_fatturazione_contratti](vw_dash_fatturazione_contratti.md)
> [vw_dash_fatturazione_commesse](vw_dash_fatturazione_commesse.md)
>
Aggregata e brief:
>
[vw_dash_fatturazione_mensile](vw_dash_fatturazione_mensile.md)
> Brief autorevole: `docs/it/dev/work-in-progress/brief-design-dashboard-fatturazione.md`

---
### 🎯 Scopo Principale
(latest review 03-07-2026)
`vendite.vw_dash_fatturazione_documenti` è la fonte dati del **drill-down della
Dashboard Fatturazione**: una riga per **documento × mese di competenza** su tutte
e 5 le aree che portano alla fatturazione (`PREVENTIVI`, `ORDINI`, `OFFERTE`,
`CONTRATTI`, `COMMESSE`), con valore/unità **totali** vs **transitati** verso l'area
successiva e il **motivo** per cui un documento è fermo.

È una **proiezione read-only**: nessuno stato nuovo sui documenti — il transito è
derivato dai link che i push scrivono già (FK, `segment_key`, `stato_emissione`,
`sorgente_*`). `UNION ALL` dei 5 resolver di area (stesso layering della proiezione
stato dominio). Il backend consuma **solo** questa vista (drill-down fermi) e
l'aggregata mensile — mai i resolver singoli.

---

### 📑 Contratto colonne

| Campo | Significato |
|-------|-------------|
| `area` | `PREVENTIVI` / `ORDINI` / `OFFERTE` / `CONTRATTI` / `COMMESSE` |
| `competenza_mese` | 1° del mese; derivazione per area documentata nel resolver |
| `documento_id` / `documento_uid` / `codice` | Identità del documento (`uid::text` dove esiste, altrimenti `id::text`) |
| `emittente_fiscale_id` | Scope emittente (NULL per COMMESSE) |
| `emittente_soggetto_ruolo_id` | Solo COMMESSE (non in RLS: eventuale filtro applicativo a carico del BE) |
| `valore_totale` / `valore_transitato` | Euro **imponibile** (decisione D-4). **NULL** per le aree a conteggi v1: OFFERTE e CONTRATTI (decisioni D-2/D-3) |
| `unita_totali` / `unita_transitate` | Righe (preventivi/ordini), attività (commesse), 1/0 (offerte, contratti×mese) |
| `is_transitato` | Transito **completo** del documento nel mese |
| `is_abortito` | `esito = 'NEGATIVO'` (proiezione stato dominio D1) — fuori dal confronto totale/transitato |
| `motivo_fermo` | Vocabolario chiuso (sotto); NULL se transitato o abortito |
| `stato_codice_interno` / `stato_codice` / `fase` | Stato nativo (alias fedeli §6c) + fase D1 (NULL per COMMESSE) |
| `cliente_display` | Ragione sociale del cliente (nullable). Path **per-area** riusato dalle rispettive `vw_*_lista`: preventivi/offerte da `istanze_utilities → soggetti`; ordini da `soggetto_ruolo_id`; contratti/commesse da `billing_account → soggetto_ruolo → soggetti` |

---

### Vocabolario `motivo_fermo` (decodifica i18n lato FE)

| Codice | Area | Significato |
|--------|------|-------------|
| `DOC_BOZZA` | preventivi, ordini, offerte, contratti | Documento ancora in bozza |
| `IN_ATTESA_ACCETTAZIONE` | preventivi, offerte | Emesso, in attesa del cliente |
| `RIGA_RESIDUA` | preventivi | Accettato con righe non ancora smistate (residuo bi-ramo) |
| `PUSH_NON_ESEGUITO` / `PUSH_PARZIALE` | ordini | Confermato, push a commessa assente/parziale |
| `SENZA_FIGLIO` | offerte | Accettata, né contratto né ordine generato |
| `FIGLIO_ABORTITO` | offerte | Figlio generato ma annullato: la XOR permanente impedisce di rigenerarlo — serve una **revisione** dell'offerta |
| `CANONE_NON_GENERATO` | contratti | Nessuna attività EMESSA con sorgente CONTRATTO per quel mese |
| `ATTIVITA_NON_APPROVATA` / `ATTIVITA_NON_EMESSA` | commesse | Collo di bottiglia: approvazione vs emissione |

---

### Esempio d'uso

```sql
-- Elementi fermi di maggio 2026 nell'area preventivi (drill-down).
SELECT codice, valore_totale, valore_transitato, motivo_fermo, stato_codice
FROM vendite.vw_dash_fatturazione_documenti
WHERE area = 'PREVENTIVI'
  AND competenza_mese = DATE '2026-05-01'
  AND NOT is_abortito
  AND NOT is_transitato
ORDER BY valore_totale DESC NULLS LAST;
```

---

### Note operative

* **Predicato canonico del transito**: lo stesso delle funzioni di eligibilità al
  push (`fn_list_*_da_pushare`) — un'attività di commessa conta solo se
  `stato_emissione = 'EMESSA'`; una riga presente ma `NON_EMESSA` è ancora
  residua/ri-pushabile (upsert idempotente su `segment_key`) e risulta ferma sia
  nell'area sorgente sia in COMMESSE.
* **Regola-cardine abortiti**: i documenti con esito `NEGATIVO` escono dal confronto
  — se restassero nel totale, `totale = transitato` non tornerebbe mai (brief §3.3).
* **RLS**: la vista gira come invoker — lo scope emittente degli operatori su
  preventivi/ordini/offerte/contratti si applica automaticamente. L'area
  **COMMESSE è fuori RLS by design** (tabella di pipeline): lo scope è applicato
  **dentro** il resolver `vw_dash_fatturazione_commesse` via GUC, così che
  aggregata mensile e drill-down concordino (vedi quella scheda per il caveat
  fail-closed).
* Test: `db/pgtap/vendite/test-vw-dash-fatturazione-v1.sql`.

---

{% include-markdown "signature-core.md" %}
