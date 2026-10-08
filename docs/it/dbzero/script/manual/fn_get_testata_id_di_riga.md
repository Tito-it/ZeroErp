## 📘 Documentazione Concettuale – Funzione `script.fn_get_testata_id_di_riga`

> 👀 **Vedi anche**
>
> [script.fn_get_stato_testata_documento](/dbzero/script/funzioni/fn_get_stato_testata_documento) — il gemello: dalla testata allo stato
> [vendite.trgfn_doc_righe_lock_fuori_bozza](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza) — il building block che la chiama, a livello RIGA
> [vendite.contratti_righe_componenti](/dbzero/vendite/tabelle/contratti_righe_componenti) · [vendite.offerte_commerciali_eccezioni_componenti](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni_componenti) · [vendite.preventivi_righe_componenti](/dbzero/vendite/tabelle/preventivi_righe_componenti) · [vendite.ordini_righe_componenti](/dbzero/vendite/tabelle/ordini_righe_componenti) · [vendite.ddt_righe_componenti](/dbzero/vendite/tabelle/ddt_righe_componenti) · [vendite.resi_righe_rientri](/dbzero/vendite/tabelle/resi_righe_rientri) — le tabelle nipoti che la usano

---

### 🎯 Scopo Principale

**Rispondere a una domanda sola: di quale documento è questa riga?**

Le righe di un documento si toccano solo finché il documento è in bozza. Per le
righe la regola guarda la testata direttamente: la riga porta il suo
`contratto_id`, `offerta_id`, `ordine_id`… Ma alcune tabelle stanno **un livello
più sotto** — i componenti di una riga di kit, i rientri di una riga di reso —
e conoscono solo la **riga** a cui appartengono. Per sapere se il documento è
ancora in bozza bisogna prima risalire dalla riga alla testata: è questo passo
che la funzione fa.

```sql
-- il caso normale: la riga 812 di un contratto
SELECT script.fn_get_testata_id_di_riga('CONTRATTO', 812);
--  403

-- il caso che conta: la riga non c'è (cancellata insieme ai suoi figli)
SELECT script.fn_get_testata_id_di_riga('CONTRATTO', 999999999);
--  NULL
```

---

### Il contratto

| Esito | Significato |
| --- | --- |
| **un id** | la testata della riga (la colonna è obbligatoria su tutte le tabelle di righe) |
| **NULL** | la riga **non esiste**: è stata cancellata, e il figlio se ne va con lei, oppure l'id è sbagliato e la chiave esterna lo dirà |

Tipi ammessi, ciascuno con la **sua** tabella di righe:

| Tipo | Riga | Testata |
| --- | --- | --- |
| `CONTRATTO` | `vendite.contratti_righe` | `contratto_id` |
| `OFFERTA` | `vendite.offerte_commerciali_eccezioni` | `offerta_id` |
| `RESO` | `vendite.resi_righe` | `reso_id` |
| `PREVENTIVO` | `vendite.preventivi_righe` | `preventivo_id` |
| `ORDINE` | `vendite.ordini_righe` | `ordine_id` |
| `DDT` | `vendite.ddt_righe` | `ddt_id` |

Qualunque altro valore non è un dato sbagliato, è un **chiamante rotto**:
`E_DOC_TIPO_NON_GESTITO`, classe `TECNICO`, come per il gemello. Un tipo nuovo
si aggiunge quando nasce la prima tabella nipote che ne ha bisogno, non prima:
un ramo che nessuno chiama non lo prova nessuno.

---

### ⛔ Perché `SECURITY DEFINER`

Le tabelle di righe hanno la sicurezza per riga (RLS). Un controllo che leggesse
la riga con i permessi di chi sta lavorando, davanti a una riga che quella
persona **non può vedere**, otterrebbe «nessuna riga» e la scambierebbe per
«la riga non c'è più» — e lascerebbe passare proprio chi sta fuori perimetro. È
la stessa ragione del gemello `fn_get_stato_testata_documento`.

La funzione gira quindi coi diritti del suo **proprietario**, che è anche il
proprietario delle tabelle di righe (chi migra possiede entrambe: un pgTAP lo
verifica, perché è una coincidenza da sorvegliare, non una garanzia).

⚠️ Il perimetro è stretto apposta: legge **una colonna** di **una riga**, da un
elenco **chiuso** di sei tabelle scelto dal tipo di documento. Nessun nome di
tabella arriva dal chiamante e non c'è SQL costruito a runtime: una funzione con
privilegi che leggesse «la tabella che le dici» sarebbe una porta su tutto il
database.

---

### Chi la chiama

Solo `vendite.trgfn_doc_righe_lock_fuori_bozza`, quando è montato col quarto
argomento `'RIGA'` (dal 2026-10-05):

* `vendite.contratti_righe_componenti` — tipo `CONTRATTO`;
* `vendite.offerte_commerciali_eccezioni_componenti` — tipo `OFFERTA`;
* `vendite.resi_righe_rientri` — tipo `RESO`;
* dal 2026-10-08: `vendite.preventivi_righe_componenti` — tipo `PREVENTIVO`,
  `vendite.ordini_righe_componenti` — tipo `ORDINE`,
  `vendite.ddt_righe_componenti` — tipo `DDT`.

---

### Storia

* **2026-10-05** — nasce (`20261005-15`), con il livello RIGA del building block
  delle righe. Brief: `brief-db-righe-esclusione-solo-non-si-vende` (§8.2 B3).
  Presidio: `db/pgtap/vendite/test-righe-gemelle-secondo-giro-v1.sql` (test 5-7).
* **2026-10-08** — impara `PREVENTIVO`, `ORDINE` e `DDT` (`20261008-33`), per il
  lock dei componenti delle tre famiglie. Brief:
  `brief-db-righe-e-componenti-le-altre-famiglie` (§2.2). Presidio:
  `db/pgtap/vendite/test-righe-e-componenti-le-altre-famiglie-v1.sql` (test 1-2).
