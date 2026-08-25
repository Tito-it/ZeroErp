## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_or_create_fattura_header`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)   
> • [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)   
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)   
>
**Approfondimento funzioni:**
>
• [vendite.fn_build_fattura_key](/dbzero/vendite/funzioni/fn_build_fattura_key)   
>
### 🎯 Scopo Principale
(latest review 29-01-2026)  
La funzione **`vendite.fn_get_or_create_fattura_header()`** recupera o crea una
**testata fattura in bozza** a partire da una riga di `attivita_fatturabili`,
usando la chiave documento (`vendite.fn_build_fattura_key`) e collegandola al lotto.

---

### Regole principali

* La chiave documento include BA fattura, tipo doc, valuta, emittente, reseller, utility, registro.
* Lo stato iniziale della fattura è `DRAFT`.
* Se una fattura con la stessa chiave esiste già nel lotto, viene riutilizzata.
* La relazione lotto ↔ fattura è registrata in `fatturazione_lotti_fatture`.

---

### Output

Ritorna l’`id` della fattura (esistente o creata).

---

### Esempio

```sql
SELECT vendite.fn_get_or_create_fattura_header(
  p_lotto_id => 10,
  p_attivita_id => 12345
);
```

---


---

### 🔄 rev 2026-08-18 — natura e serie nel WHERE **e** nella INSERT

Brief: `brief-design-note-credito-resi` (slice **N3**). Gemello obbligatorio
della revisione di `fn_build_fattura_key`.

La chiave ha ora **undici** elementi. Due trappole, entrambe silenziose:

**1. Chiave che separa + lookup che non separa.** Il commento vivo di questa
funzione lo diceva già: *«se la chiave separa e il lookup no, le due metà si
annullano e le attività tornano nella stessa fattura»*. Per questo il `WHERE` si
tocca insieme alla chiave.

**2. Serie calcolata + INSERT che non la scrive.** `vendite.fatture.serie` **non
era mai stata scritta da questa INSERT**: restava `NULL` e
`fn_assign_numero_fattura` cadeva sul `serie_default` del registro. Se la chiave
la calcolasse e la `INSERT` non la scrivesse, la nota di credito prenderebbe **un
numero valido nella serie delle fatture** — cioè un difetto che non solleva nulla
e si scopre guardando un registro IVA.

Per questo la serie entra in **tre posti** nello stesso changeSet: il `WHERE` del
lookup, l'elenco colonne della `INSERT` e i suoi valori.

#### ⚠️ `IS NOT DISTINCT FROM` sulla serie, `=` sulla natura

La serie è **nullable** — anzi, con il sezionale proprio è `NULL` sempre. Con `=`
il `NULL` non combacia mai, quindi **ogni giro aprirebbe una fattura nuova** per
la totalità dei casi. È la stessa trappola già pagata tre volte in questo
progetto (reseller, modalità di pagamento, indice d'ambito): la serie è il
quarto elemento nullable.

La natura invece è `NOT NULL` su `fatture` e su `attivita_fatturabili`: `=` è
corretto, e un confronto permissivo nasconderebbe sotto un'uguaglianza un valore
che non può mancare. Per la stessa ragione entra nel guard di **completezza**
della chiave, accanto a `utility_id`; la serie no, perché `NULL` è il suo valore
normale.

---

### 🔄 rev 2026-08-25 — la data smette di essere un effetto collaterale

Brief: `brief-db-numerazione-data-documento-e-sequenza` (**DB-6**).

```diff
- VALUES (v_registro_id, current_date, ...)
+ VALUES (v_registro_id, v_data, ...)   -- fn_calcola_data_documento(...)
```

⛔ **Questa è l'unica riga in tutto il repo che scrive `vendite.fatture.data`.**
Verificato su `pg_proc`, su `backend/` e sulla doc auto-gen: nessun'altra
funzione, nessun endpoint, nessuna schermata. Cambiarla qui cambia il
comportamento **ovunque** — ed è anche il motivo per cui il difetto è rimasto
invisibile così a lungo: non c'era un secondo posto in cui vedere due
implementazioni divergenti.

#### I due danni che `current_date` faceva insieme

**1. Il momento sbagliato.** Era catturato alla **generazione della bozza**, cioè
giorni o settimane prima dell'atto fiscale. Se un lotto restava indietro, la sua
data restava indietro con lui. La data del documento è una *decisione* — per la
differita, tipicamente l'ultimo giorno del mese di competenza — non l'orario di
un batch.

**2. Il fuso sbagliato.** `current_date` segue il fuso **della sessione**, e la
sessione non è una sola: Django si connette in **UTC** (`USE_TZ` senza
`TIME_ZONE` in `DATABASES`), psql e pgAgent in `Europe/Rome`. Lo stesso oggetto,
chiamato da due canali, scriveva **due date diverse** — e ogni documento generato
fra la mezzanotte e le 02:00 locali portava **la data del giorno prima**.
📌 Misurato il 2026-08-25: **7 fatture su 18** avevano
`data <> (data_insert AT TIME ZONE 'Europe/Rome')::date`.

#### Da dove viene la data adesso

Da [`vendite.fn_calcola_data_documento`](/dbzero/vendite/funzioni/fn_calcola_data_documento),
a cui si passano il registro della chiave, la `competenza_mese` e la
`data_documento` del lotto. Qui non si decide niente: **si chiede**.

#### ⭐ Il lotto si legge DOPO il lookup, non in testa

Questa funzione gira una volta per **attività**, e nella stragrande maggioranza
dei giri esce subito perché la testata è già stata creata. Leggere il lotto in
testa avrebbe aggiunto una query per ogni attività di ogni lotto, per un valore
che serve solo alla prima.

#### ⚠️ Un controllo che prima non poteva esistere

`vendite.fatturazione_lotti` ha la RLS e questa funzione è `SECURITY INVOKER`: un
lotto fuori dal perimetro di chi opera si legge come «non c'è», e si esce con
`E_LOTTO_NON_TROVATO`. È **fail-closed** ed è la risposta giusta — non si crea una
testata dentro un lotto che non si può vedere.

📌 Prima il lotto non veniva letto affatto: un `p_lotto_id` sbagliato produceva
una **fattura orfana**, in silenzio.

---

{% include-markdown "signature-core.md" %}
