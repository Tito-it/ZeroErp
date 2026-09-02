## 📘 Documentazione Concettuale – Funzione `script.fn_check_famiglia_documento_struttura_modificabile`

> 👀 **Vedi anche**
>
> **Consumatori:**
>
> • [vendite.trgfn_famiglie_documento_guard_struttura](/dbzero/vendite/manual/trgfn_famiglie_documento_guard_struttura) — il guard, che la **chiama** e solleva il primo motivo
> • [vendite.vw_famiglie_documento_lista](/dbzero/vendite/manual/vw_famiglie_documento_lista) — la maschera, che tiene il gruppo di campi in sola lettura e dice **perché**
>
> **Sorgente:**
>
> • [vendite.famiglie_documento](/dbzero/vendite/manual/famiglie_documento)
> • [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)
>
> **Gemelle:**
>
> • [script.fn_check_famiglia_documento_disattivabile](/dbzero/script/manual/fn_check_famiglia_documento_disattivabile) — l'altro divieto sulla stessa riga
> • [script.fn_check_registro_forma_modificabile](/dbzero/script/manual/fn_check_registro_forma_modificabile) — lo stesso genere di divieto, un piano più sotto

---

### 🎯 Scopo Principale

*(rev 2026-09-01 — funzione nata il 2026-09-01)*

**Dice se si possono ancora cambiare le colonne che raccontano DOVE VIVE il
documento di una famiglia.** Ritorna `[]` se sì, altrimenti l'array ordinato dei
motivi — oggi uno solo.

Le colonne protette sono **cinque**: `schema_tabella`, `nome_tabella`,
`colonna_numero`, `colonna_billing_account`, `colonna_serie`.

---

### ⛔ Perché non sono colonne descrittive

Non descrivono la famiglia: **la fanno funzionare**. Le legge in SQL dinamico il
presidio sul cambio emittente del cliente, e le legge
`script.fn_check_registro_serie_ammessa` a ogni scrittura su un registro.

⭐ **Il caso peggiore è `colonna_serie` portata a NULL** su una famiglia che ce
l'aveva: da quel momento la serie risulta «non ammessa», e i registri che una
serie ce l'hanno restano con un contenitore del contatore che il documento non sa
più distinguere. Il contatore continua a contare, e **nessun vincolo se ne
accorge**.

---

### ⭐ Il predicato: «esiste un registro», non «esiste un numero»

È deliberatamente **più largo** di quello sulla forma del numero
(`fn_check_registro_forma_modificabile`, che chiede *«ha già consegnato un
numero?»*).

⇒ Un registro **appena nato** ha già copiato dentro di sé i default di questa
famiglia — prefisso e cifre — quindi la divergenza comincia **prima** del primo
documento.

⚠️ **E i registri spenti contano**: uno spento si riaccende, e si riaccende con la
forma che aveva.

---

### ⛔ `codice_interno` non è fra le cinque, ed è voluto

Lo presidia il **lock automatico** (`script.trgfn_lock_columns`, codice
`E_CODICE_NON_MODIFICABILE`), provisionato dal runner per la sola presenza della
colonna.

⚠️ Due presidi sulla stessa colonna con due messaggi diversi sono la cosa da non
fare: quale dei due parli dipenderebbe dall'ordine alfabetico dei trigger, cioè
da un dettaglio che nessuno ha scelto — e chi legge il primo messaggio non sa
dell'altro.

---

### ⚠️ Il nome della colonna toccata NON sta nella frase

Il messaggio a catalogo ha **due** segnaposti: la famiglia e il numero di
registri. Quale colonna sia stata toccata viaggia nel `context ->> 'campo'`, che è
il canale con cui il frontend accende l'input giusto.

⭐ È anche il motivo per cui questa verifica **non prende la colonna come
parametro**: la domanda a cui risponde è *«si può toccare la struttura?»*, ed è
quella che serve alla maschera per decidere se disabilitare l'intero gruppo di
campi.

---

### 📤 Cosa torna

| Chiave | Contenuto |
| --- | --- |
| `codice` | `E_FAMIGLIA_DOCUMENTO_CHIAVE_IMMUTABILE` — a catalogo, classe `CONFLITTO_STATO`. ⭐ Il nome segue la famiglia già a catalogo (`E_COMMESSA_CHIAVE_IMMUTABILE`) |
| `reason` | `HA_REGISTRI` |
| `reason_key` | `amministrazione.famiglie_documento.struttura_blocco.ha_registri` |
| `dettaglio` | `famiglia_id`, `codice_interno`, `registri` |
| `valori` | i due argomenti del messaggio: la famiglia e quanti registri la portano |

---

### ⚠️ Note operative

* **`SECURITY INVOKER`, ed è motivato**: legge solo `famiglie_documento` e
  `registri_fatturazione`, e **nessuna delle due ha la RLS**. ⛔ Qui non vale la
  ragione della gemella sulla disattivazione, che conta documenti in tabelle con
  la RLS attiva e per questo è `DEFINER`.
* **Famiglia inesistente**: si solleva `E_VENDITE_CHIAMATA_NON_VALIDA`, non `[]`.

---

*Piano: `brief-be-fe-crud-registri-di-numerazione`, sezione 11.5.*
