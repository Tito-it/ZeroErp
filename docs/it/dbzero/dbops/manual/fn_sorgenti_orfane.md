## 📘 Documentazione Concettuale – Funzione `dbops.fn_sorgenti_orfane`

> 👀 **Vedi anche**
>
> • [dbops.vw_sorgenti_orfane](/dbzero/dbops/views/vw_sorgenti_orfane) — la vista che la espone (e la spiega)
> • [dbops.fn_sorgenti_orfane_perimetro](/dbzero/dbops/funzioni/fn_sorgenti_orfane_perimetro) — il perimetro
>
Guide: brief `brief-db-magazzino-lotto-2-motore` (§4.7)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

Per ogni tabella del perimetro e per ogni tipo di sorgente presente, fa un **anti-join
dinamico** verso il bersaglio dichiarato a catalogo (`config.sorgenti.target_table`) sulla
chiave che `key_selector` dichiara (`id` o `uid`), e ritorna le righe senza bersaglio:
tabella, id della riga, tipo e chiave di sorgente, bersaglio. Si scrive una volta perché il
bersaglio e la chiave stanno a catalogo. Il confronto è su testo: nel perimetro convivono
chiavi `uuid` e `text`.

Gira con i permessi del **proprietario** (`SECURITY DEFINER`, pin del `search_path`) e legge
soltanto (`STABLE`). Nomi di tabelle e colonne vengono dal catalogo, mai da un input.

---

### ⚠️ La forma del ciclo interno, e perché conta

Il ciclo che legge «quali tipi di sorgente ci sono in questa tabella» è una query
**dinamica** (`FOR … IN EXECUTE`), e il suo bersaglio sono **tre variabili tipizzate**
(`%TYPE` sulle colonne di `config.sorgenti`), non un `record`. Non è una scelta di stile:
un `record` riempito da SQL dinamico ha tupla **indeterminata** per `plpgsql_check`, e il
presidio dei riferimenti morti (`db/pgtap/dbops/test-riferimenti-morti-v1.sql`, che compila
ogni funzione) lo riferiva come difetto `REALE` (`55000: il record "v_s" non è stato ancora
assegnato`). Chi tocca questa funzione tiene la forma; la regola vale per ogni
`FOR … IN EXECUTE` del progetto.

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-25`).
* 2026-09-18 (pomeriggio) — `20260918-27`: il ciclo interno passa dal `record` ai tre
  scalari tipizzati, dopo il rosso del presidio dei riferimenti morti sul runner. Firma e
  comportamento invariati.

---

{% include-markdown "signature-core.md" %}
