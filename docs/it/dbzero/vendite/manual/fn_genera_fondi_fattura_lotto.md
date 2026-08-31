## 📘 Documentazione Concettuale – Funzione `vendite.fn_genera_fondi_fattura_lotto`

> 👀 **Vedi anche**
>
> **Su cosa si appoggia:**
>
> • [vendite.fn_get_scope_fatture_lotto](/dbzero/vendite/funzioni/fn_get_scope_fatture_lotto) — lo scope del lotto
> • [vendite.fn_genera_fondi_fattura_source](/dbzero/vendite/funzioni/fn_genera_fondi_fattura_source) — la generazione per chiave, **intatta**
>
> **La sorella:**
>
> • [vendite.fn_applica_fondi_lotto](/dbzero/vendite/funzioni/fn_applica_fondi_lotto)
>
> **Piano:** [brief-db-fondo-fattura-ricalcolo-e-governo](/dev/work-done/brief-db-fondo-fattura-ricalcolo-e-governo) §8.3 R-3

---

### 🎯 Scopo Principale
(latest review 15-08-2026)

**Un lotto, una chiamata.**

```text
prima:  SELECT vendite.fn_genera_fondi_fattura_source(s.…, %s)
        FROM (venti righe di SQL dello scope, in Python) s

dopo:   SELECT * FROM vendite.fn_genera_fondi_fattura_lotto(%s, %s)
```

Il backend smette di conoscere la forma dello scope e la pseudo-chiave a cinque
parametri: due cose di dominio che stavano in un repository.

**Ritorna** `fatture_count`, `chiavi_count`, `fondi_creati`.

---

### ⭐ Il guadagno che non si vedeva: una volta per CHIAVE, non per FATTURA

La query Python faceva `SELECT DISTINCT f.id, …`: con l'id in proiezione il
`DISTINCT` **non deduplica niente**. Ma la generazione non riceve una fattura —
riceve una **chiave**, e ogni chiamata riesamina tutte le sorgenti «di minimo»
di quella chiave.

```text
lotto con 500 fatture dello stesso emittente/utility/valuta

  prima:  500 chiamate → 500 scansioni identiche
                         di cui 499 non creano nulla (l'atto unico le blocca)
  dopo:     1 chiamata  →   1 scansione
```

⚠️ Non è un'ottimizzazione trovata a posteriori: è la conseguenza di aver messo
la chiave nel posto giusto. *Chi itera sulle fatture per passare una chiave sta
iterando sull'oggetto sbagliato.*

ℹ️ `chiavi_count` esiste per rendere questo **osservabile**: senza quel numero
«una volta per chiave» non è verificabile da un test.

---

### ⚠️ Prende il CODICE INTERNO, non l'id del tipo fondo

E la differenza è il punto di R-3: il parametro che arriva dalla configurazione
del task è `tipo_fondo_codice_interno`, **una stringa**. Con l'id il chiamante
dovrebbe fare **prima** una query di lookup — e «una `SELECT` per task», che è
il senso del passo, non si otterrebbe.

Il lookup (`attivo IS TRUE`, primo per id) sta dentro la funzione, e un codice
sconosciuto è `E_TIPO_FONDO_NOT_FOUND`.

> ⚠️ **Nessun `DEFAULT` sul parametro.** Il ripiego `'F_F_ADD_ACC'` lo risolve
> già il chiamante, e un default qui aprirebbe la strada all'ambiguità di
> overload che il progetto ha già pagato altrove.

---

### L'ordine del corpo, che non è casuale

1. **guard dei parametri** — lotto e codice, prima di leggere qualunque cosa;
2. **risoluzione del tipo fondo** — un codice sbagliato si scopre subito;
3. **scope + validazione** (dentro `fn_get_scope_fatture_lotto`);
4. **generazione set-based** sulle chiavi distinte.

🔴 I passi 3 e 4 in quest'ordine sono una garanzia, non un'abitudine: **la
validazione precede la scrittura**. Se una fattura del lotto ha lo scope
incompleto, nessun fondo viene creato — nemmeno per le fatture sane dello stesso
lotto. Il pgTAP lo verifica esplicitamente.

---

### ⚠️ Atomicità: una funzione = uno statement = una transazione

Il giro non può restare a metà **nemmeno se chiamato fuori dalla pipeline** —
dalla facciata single-step, o da un `psql`. Prima la garanzia dipendeva da come
il chiamante scriveva la query; adesso non dipende più da lui.

ℹ️ Sul giro di pipeline il parziale non era comunque possibile (`run_pipeline`
avvolge ogni step in `transaction.atomic()`): la motivazione originale di R-3
era sbagliata, e le due vere sono altre — questa e la utility, in
`fn_get_scope_fatture_lotto`.

---

### Cosa NON fa

Non decide **se** una fattura meriti un fondo: quello lo dice
[fn_fondo_fattura_proponibile](/dbzero/vendite/funzioni/fn_fondo_fattura_proponibile),
attraverso la generazione per chiave. Questa funzione porta soltanto il lotto
fino alla chiave — è **orchestrazione**, non una regola.

⛔ E non tocca `fn_genera_fondi_fattura_source`: la incapsula. Il passo è
puramente additivo, e le funzioni per-scope restano il mattone su cui si appoggia
(oltre che i soggetti dei pgTAP esistenti).

---

### Esempio d'uso

```sql
SELECT * FROM vendite.fn_genera_fondi_fattura_lotto(1234, 'F_F_ADD_ACC');
-- fatture_count | chiavi_count | fondi_creati
--            42 |            3 |            5
```

---

{% include-markdown "signature-core.md" %}
