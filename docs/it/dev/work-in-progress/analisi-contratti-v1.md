# Analisi Contratti v1

> Area di analisi avanzata contratti — dashboard e filtri operativi
> per monitoraggio scadenze, rinnovi e pricing.
>
> Stato: **PIANIFICAZIONE** — nessuna implementazione avviata.
>
> Prerequisiti: F3-FE-05 (gestione contratti FE) completato.

---

## 1) Obiettivo

Fornire agli operatori e ai responsabili commerciali strumenti per:

- Monitorare contratti in scadenza con visione mensile/trimestrale
- Identificare contratti non rinnovati (gap di copertura)
- Analizzare distribuzioni pricing per categoria cliente
- Supportare il processo decisionale per rinnovi, rinegoziazioni e offerte

## 2) Funzionalita' previste

### 2.1 Contratti in scadenza — heatmap mensile

Vista calendario con conteggio contratti che scadono per mese.
Colori: verde (pochi), giallo (medio), rosso (molti). Click su mese →
apre lista filtrata.

**Query base:**
```sql
SELECT date_trunc('month', upper(validita)) AS mese_scadenza,
       COUNT(*) AS totale
  FROM vendite.contratti
 WHERE upper(validita) IS NOT NULL
   AND upper(validita) >= CURRENT_DATE
   AND stato_doc_contratto_id IN (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO')
 GROUP BY 1
 ORDER BY 1
```

### 2.2 Contratti non rinnovati

Un contratto e' "non rinnovato" se:
- `upper(validita)` e' nel passato (o entro N giorni)
- Non esiste un altro contratto per lo stesso `(billing_account_id, utility_id, ambito)`
  con `lower(validita)` che copre il giorno successivo

**Query base:**
```sql
SELECT c.*
  FROM vendite.contratti c
 WHERE upper(c.validita) <= CURRENT_DATE + interval '30 days'
   AND NOT EXISTS (
       SELECT 1 FROM vendite.contratti c2
        WHERE c2.billing_account_id = c.billing_account_id
          AND c2.utility_id = c.utility_id
          AND c2.ambito = c.ambito
          AND c2.id != c.id
          AND lower(c2.validita) <= upper(c.validita)
          AND (upper(c2.validita) IS NULL OR upper(c2.validita) > upper(c.validita))
   )
```

### 2.3 Distribuzione pricing per categoria

Tabella pivot: categoria_cliente × tipo_variazione → count + media valore_variazione.
Utile per capire se le politiche commerciali sono coerenti.

### 2.4 Export

Export CSV/Excel dei risultati filtrati (scadenze, non rinnovati, distribuzione).

## 3) Architettura proposta

### Backend

- Nuovi endpoint in `apps/vendite/api/views_analisi_contratti.py`
- Repository dedicato `apps/vendite/db/analisi_contratti_repository.py` con query aggregate
- Nessuna tabella nuova: solo query su `vendite.contratti` + JOIN esistenti

### Frontend

- Nuova view `AnalisiContrattiView.vue` sotto dominio Vendite
- Componenti: `ScadenzeHeatmap.vue`, `NonRinnovatiList.vue`, `PricingDistribuzione.vue`
- Voce menu sidebar: "Analisi contratti" (sotto Contratti)

## 4) Priorita' e dipendenze

| Feature | Priorita' | Dipende da |
|---|---|---|
| Filtro scadenza mese (lista) | **FATTO** — gia' implementato nella lista contratti | — |
| Heatmap scadenze | MEDIA | Endpoint aggregato |
| Non rinnovati | ALTA | Query EXISTS + definizione "rinnovo" |
| Distribuzione pricing | BASSA | Join categoria_cliente |
| Export | BASSA | Generazione CSV lato BE |

## 5) Decisioni aperte

1. **Definizione "rinnovo"**: un contratto e' rinnovato se esiste un successore con lo stesso
   `(BA, utility, ambito)` che copre il giorno dopo la scadenza? O serve un link esplicito
   (`parent_contratto_id`)?
2. **Orizzonte temporale**: i "non rinnovati" devono includere solo contratti scaduti o anche
   quelli in scadenza entro N giorni? Valore N configurabile?
3. **Permessi**: l'analisi e' visibile a tutti gli operatori o solo admin/responsabili?
4. **Performance**: le query aggregate su contratti con molti record potrebbero richiedere
   materialized view o cache. Da valutare volumi.
