## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_get_saldo_fattura`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)  
> • [pagamenti.centri_riscossione](/dbzero/pagamenti/tabelle/centri_riscossione)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
>
**Funzioni sorelle:**
>
• [pagamenti.fn_get_saldo_rata](/dbzero/pagamenti/funzioni/fn_get_saldo_rata)  
> • [pagamenti.fn_get_saldo_fattura_contabili](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura_contabili)  
>
### 🎯 Scopo Principale
(latest review 18-09-2026)  
La funzione **`pagamenti.fn_get_saldo_fattura()`** risponde a **tre domande
diverse su un documento**, e tenerle separate è il motivo per cui esiste:

| Colonna | Domanda a cui risponde |
| --- | --- |
| `saldo` | quanto manca ancora da **registrare** su questa fattura |
| `in_lavorazione` | quanto è già stato **dichiarato** e non ancora registrato |
| `incassato` | quanto di ciò che è registrato è **denaro davvero arrivato** |

---

### ⭐ Perché «incassato» non è «saldato»

Un movimento su un centro di riscossione **interno** — il fondo fattura, la
compensazione — **salda il documento**: il denaro si è mosso davvero, per
trasferimento. Ma **in banca non è entrato niente**.

Chi misura gli incassi sommando tutti i movimenti sta misurando un'altra cosa e
non lo sa. Da qui la terza colonna, che somma **solo** i movimenti il cui centro
è di cassa.

⚠️ Un movimento **senza centro** non entra in `incassato`: «canale non
dichiarato» non è «denaro arrivato», e su una misura di cassa si sta dalla parte
prudente.

⇒ **Regola d'uso**: qualunque colonna, badge o totale che dica «incassato» deve
dichiarare **quale dei due** è. «Questa fattura è a posto?» si risponde col
`saldo`; «quanto è entrato in banca?» con `incassato`.

---

### ⭐ `in_lavorazione` non è calcolato qui

Il **dichiarato** ha una sede sola, ed è
[`fn_get_saldo_fattura_contabili`](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura_contabili):
somma le righe contabili in stato *postabile* sotto una testata **non finale**.
Questa funzione gliela **chiede**, non la ricalcola.

Non è pignoleria: due formule per la stessa regola divergono al primo
aggiustamento, e sono numeri su cui qualcuno decide se sollecitare un cliente.
⚠️ La funzione del dichiarato **resta** anche perché espone `has_righe_postabili`,
che serve a `vendite.fn_saldo_sorgente_fondo` e che questa non dà.

⚠️ E `saldo` e `in_lavorazione` **non si sommano**: sono due stati diversi dello
stesso denaro (promesso / registrato), e sommarli fa perdere di vista quale si
sta guardando.

---

### Regole principali

* `p_fattura_id` obbligatorio (`> 0`); se manca o non è positivo l'errore è
  **tecnico**: quel valore non esce da nessuna interfaccia, lo produce un
  chiamante rotto.
* ⭐ `p_escludi_contabile_riga_id` (facoltativo, dal 18-09-2026): **«quanto c'era
  prima di me»**. Chi sta correggendo una riga contabile chiede il saldo del
  documento *senza* quella riga — altrimenti si confronterebbe con sé stesso e
  leggerebbe come «già dichiarato» l'importo che sta cambiando. La riga esclusa
  esce da **entrambi** i conti: dal dichiarato (è la delegata a toglierla, non
  una seconda esclusione scritta qui) e dal registrato (il movimento che quella
  riga ha scritto, se è già stata registrata). È la stessa forma e lo stesso
  parametro della sorella
  [`fn_get_saldo_rata`](/dbzero/pagamenti/funzioni/fn_get_saldo_rata): lo stesso
  nome deve rispondere alla stessa domanda su rata e documento. Se è fornito e
  non positivo, l'errore è tecnico come per il primo parametro.
* La fattura deve esistere. ⚠️ La tabella ha la **RLS**: «non esiste» e «non la
  vedi» danno lo **stesso** errore, per scelta — chi ha bisogno della differenza
  la chiede a una funzione che gira fuori dalla row security.
* Considera solo i movimenti `attivo = true`.
* ⚠️ Non è dichiarata `STABLE`: il ramo d'errore scrive nel registro degli
  errori, e promettere stabilità su una funzione che in un ramo scrive
  autorizzerebbe il planner a scelte che quel ramo non regge.

---

### Output

Ritorna **una** riga con:

* `saldo` (numeric) — residuo del documento
* `in_lavorazione` (numeric) — dichiarato non ancora registrato
* `incassato` (numeric) — cassa vera
* `has_movimenti` (boolean)

⭐ È la **stessa forma e lo stesso ordine** di
[`fn_get_saldo_rata`](/dbzero/pagamenti/funzioni/fn_get_saldo_rata): documento e
rata rispondono con lo stesso vocabolario, ed è la base su cui nascerà il saldo
**cliente**.

---

### Esempio d’uso

```sql
SELECT *
FROM pagamenti.fn_get_saldo_fattura(123);

-- Il pannello dei saldi mentre si corregge la riga contabile 4567:
-- i suoi 500 non compaiono fra gli «in lavorazione».
SELECT *
FROM pagamenti.fn_get_saldo_fattura(123, 4567);
```

---

### 🕘 Storia

* **18-09-2026** — `p_escludi_contabile_riga_id` (P-6 di
  `brief-db-distinta-ricerca-rate`): l'esclusione «prima di sé» esisteva solo
  sulla rata, e chi correggeva una riga **senza rata** (fondo fattura, riga
  manuale «fattura sì, rata no») leggeva un dichiarato che contava la riga
  stessa. Cambia la firma, quindi `DROP` + `CREATE` — e la vista
  `vw_eccedenze_da_sistemare`, che dipende dalla funzione, è stata ricreata
  identica nello stesso changeSet (`20260918-02`). Nessun numero cambia per chi
  chiama a un argomento.
* **25-08-2026** — da due colonne a quattro (S5-1 del cantiere incassi). Fino a
  qui la distinzione fra *registrato* e *incassato* esisteva sulla **rata** e non
  sul **documento**, cioè mancava proprio al livello che si guarda per primo.
  ⚠️ Nessun predicato preesistente è cambiato: `saldo` e `has_movimenti`
  rispondono esattamente come prima.
* **21-08-2026** — i due `E_GENERICO` passano ai codici registrati.
* **13-02-2026** — prima stesura.

---

{% include-markdown "signature-core.md" %}
