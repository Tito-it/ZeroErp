## 📘 Documentazione Concettuale – Funzione `script.fn_doc_date_consegna_anteriori()`

> 👀 **Vedi anche**
>
> • [script.fn_data_consegna_ammessa](/dbzero/script/manual/fn_data_consegna_ammessa) — la regola, e perché esiste
> • [script.trgfn_doc_righe_guard_data_consegna](/dbzero/script/manual/trgfn_doc_righe_guard_data_consegna) e [script.trgfn_doc_testata_guard_data_consegna_righe](/dbzero/script/manual/trgfn_doc_testata_guard_data_consegna_righe) — i due guard che la leggono

---

### 🎯 Scopo Principale

(nata il 2026-10-13, dal collaudo)

**Quali date di consegna vengono prima della data del documento?** È il lettore
dei due guard, e risponde a due domande:

| Chiamata | Domanda |
| --- | --- |
| con la riga (`p_riga`, e `p_riga_prima` in un UPDATE) | le date di questa riga, che sto scrivendo, vengono prima della data della sua testata? |
| senza la riga, con `p_data_documento` | se la testata prende questa data, quali date delle sue righe attive restano prima? |

Zero righe = niente da dire. Altrimenti una riga per colonna fuori regola, con
la prima data fuori regola, la data del documento usata e la posizione della
colonna nell'elenco.

### ⭐ L'elenco delle date di consegna sta qui, e solo qui

| Documento | Righe | Date di consegna |
| --- | --- | --- |
| `ORDINE` | `vendite.ordini_righe` | `data_consegna_richiesta_cliente`, `data_consegna_confermata` |
| `PREVENTIVO` | `vendite.preventivi_righe` | `data_consegna_richiesta_cliente` |

Le due domande stanno in una funzione sola **perché entrambe devono sapere
quali colonne sono date di consegna**. Un elenco negli argomenti del trigger di
riga e un altro nel guard di testata divergerebbero alla prima colonna nuova, e
la regola si aggirerebbe dal lato dimenticato. Il presidio pgTAP (test 4)
controlla che i due guard non nominino nessuna colonna.

### 🧭 Quando una riga si giudica

* Una riga **spenta** non si giudica: non fa parte del documento.
* In un UPDATE si giudicano solo le date **cambiate** — tutte, se la riga torna
  attiva o cambia testata. Così una riga scritta prima della regola non blocca un
  UPDATE che non tocca le sue date: fuori bozza quelle date non si
  correggerebbero più, e il rifiuto sarebbe un vicolo cieco.

### ⛔ Perché SECURITY DEFINER

Testate e righe di ordini e preventivi hanno la RLS. Sotto quella di chi scrive,
una riga fuori perimetro sparirebbe dal conto del guard di testata, e una testata
non visibile spegnerebbe il guard di riga: il guard diventerebbe fail-open. È la
scelta di `script.fn_get_stato_testata_documento`. Restituisce solo colonne e
date, nessun dato del cliente.

Un selettore sconosciuto è un chiamante rotto: `E_DOC_TIPO_NON_GESTITO` (TECNICO).
