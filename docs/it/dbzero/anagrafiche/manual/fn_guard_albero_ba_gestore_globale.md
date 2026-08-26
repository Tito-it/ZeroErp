## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_albero_ba_gestore_globale`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_guard_albero_ba_emittente](/dbzero/anagrafiche/manual/fn_guard_albero_ba_emittente)
>
Approfondimenti tabelle:
>
[anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account)

---
### 🎯 Scopo Principale
(latest review 18-08-26)

Presidia l'**unica operazione del sistema che puo' cambiare l'emittente di molti
billing account in una volta sola**: lo spostamento del gestore globale.

---

### Cos'e' il gestore globale

Molti billing account non hanno un'assegnazione esplicita a un emittente. Per
loro vale una regola di ripiego: **appartengono al gestore globale**, cioe'
all'emittente marcato come predefinito. Ce n'e' uno solo in tutto il sistema.

Spostare quel marchio da un emittente a un altro cambia proprietario a **tutti**
quelli senza assegnazione. In silenzio, e senza che nessuno abbia scritto un
emittente da nessuna parte.

---

### Cosa controlla, e cosa NON controlla

Si guardano **solo** i billing account senza assegnazione esplicita **che stanno
in un albero**. Il motivo e' preciso:

| Situazione | Cosa succede spostando il gestore globale |
| --- | --- |
| entrambi i lati senza assegnazione | si spostano **insieme**: l'albero resta sano ✅ |
| entrambi i lati assegnati | non si sposta nessuno dei due ✅ |
| **uno assegnato e uno no** | ⚠️ **solo questo si spacca** |

La condizione da presidiare e' quindi la **coppia mista**, non «esiste un
albero». Un controllo scritto largo bloccherebbe operazioni legittime, e una
funzione che infastidisce e' una funzione che qualcuno prima o poi disattiva.

---

### Impatto e Vantaggi

* costa quasi nulla nell'uso quotidiano: dall'interfaccia il gestore globale
  **non si sposta** (lo impediscono gia' un vincolo di unicita' e un controllo
  di quantita'), quindi il caso passa solo da un intervento deliberato sul
  database;
* e proprio per questo il valore e' alto: e' l'operazione rara, ampia e mai
  collaudata — quella in cui un errore e' silenzioso e grande.
---

### ⚠️ Una nota del 2026-08-26: adesso c'è un secondo cancello

Lo stesso movimento — spostare l'emittente generale — ha ora un controllo in più:
[`fn_guard_ba_gestore_globale_storia`](/dbzero/anagrafiche/manual/fn_guard_ba_gestore_globale_storia),
che lo vieta se **anche un solo** cliente non agganciato ha già fatture o
commesse. Su un'installazione che ha già fatturato, cioè quasi sempre.

Non è una duplicazione: questo chiede *«l'albero può diventare misto?»*, l'altro
*«c'è storia da proteggere?»*. Il secondo, di norma, risponde per primo.
