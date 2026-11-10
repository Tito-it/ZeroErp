## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_limite_emissione_default`

> **Ultimo aggiornamento**: 9 novembre 2026

> 👀 **Vedi anche**
>
> [vendite.fn_get_pavimento_emissione](/dbzero/vendite/funzioni/fn_get_pavimento_emissione)
> [config.parameters](/dbzero/config/tabelle/parameters)
> [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa)
> [Configurazione e Gestione Parametri](/guide/configurazione-e-gestione-parametri)

---

### 🎯 Scopo Principale

**Il valore di un limite di emissione dal catalogo dei parametri, come numero.**

Serve i due codici che governano il termine di emissione, letti da
[`fn_get_pavimento_emissione`](/dbzero/vendite/funzioni/fn_get_pavimento_emissione)
quando il registro non dichiara un override suo:

```sql
SELECT vendite.fn_get_limite_emissione_default('VENDITE_LIMITE_EMISSIONE_IMMEDIATA_GIORNI');
SELECT vendite.fn_get_limite_emissione_default('VENDITE_LIMITE_EMISSIONE_DIFFERITA_GIORNO_MESE');
```

---

### ⭐ Perché esiste una funzione per due righe di lettura

La lettura di un limite dal catalogo serve **due volte**, e con **tre modi di
sbagliare identici**: parametro assente, valore vuoto, valore non numerico.
Una sede sola invece di due blocchi gemelli che possono divergere.

⛔ **NON è un lettore generico di parametri, e non va usata come tale.** È
*narrow* per dominio e per famiglia, apposta: il lettore canonico esiste già ed è
`script.fn_get_parameter_full`.

---

### ⛔ Legge il `default_value` NUDO, e la cascata di override si scavalca

`script.fn_get_parameter_full` risolve la cascata utente → categoria cliente →
gruppo → emittente → funzione → default. **Qui quella cascata sarebbe il difetto**: darebbe **allo stesso
documento** limiti diversi a seconda di **chi lo genera**, cioè esattamente la
classe di problema che il limite di emissione chiude.

L'unico asse di override ammesso è il **registro**
(`registri_fatturazione.limite_emissione_*`), che è un fatto del **sezionale** e
non di chi ci lavora.

⚠️ È la stessa scelta — e la stessa ragione — già scritta in
[`script.fn_data_operativa`](/dbzero/script/funzioni/fn_data_operativa) per il
fuso orario. **Se questa riga sparisse dai commenti, il prossimo la
«correggerebbe» verso il building block e riaprirebbe il buco.**

---

### ⛔ Fail-loud su tre condizioni

| condizione | perché è raggiungibile |
|---|---|
| parametro **assente** | il seed di `80_data` gira **dopo** `20_code`: fra le due fasi di un migrate il parametro non c'è ancora |
| valore **vuoto** | `config.parameters.default_value` è `NOT NULL` ma **non ha nessun `CHECK` di non-vuoto**, e a catalogo ci sono già parametri a stringa vuota |
| valore **non numerico** | è un campo `text`: ci si può scrivere qualunque cosa |

Tutte e tre con `E_CONFIG_MANCANTE`, perché a rimediare è sempre **chi
amministra la configurazione**; a distinguere i casi è la **frase**, che nel
secondo e terzo caso nomina anche il valore — l'unica cosa che dice dove sta
l'errore di battitura.

⛔ **Senza il controllo sul formato, il cast alzerebbe un `22P02` grezzo**: il
contratto «`P0001` + `CONSTRAINT` = errore di dominio» salterebbe e il guasto
arriverebbe al backend come **500 non tradotto**.

⚠️ **La regex ammette 1..4 cifre e non un numero qualunque**, e non è
pignoleria: limita al dominio di `smallint`, così un valore assurdo produce la
frase invece di un `22003` altrettanto grezzo.

---

### Note operative

* Guard di parametro: `p_code` obbligatorio e non vuoto
  (`E_VENDITE_CHIAMATA_NON_VALIDA`, `TECNICO`: un codice vuoto lo produce solo
  un chiamante rotto).
* `STABLE`, `SECURITY INVOKER`.
* Brief: `brief-db-limite-emissione-e-data-verificata` §11 DB-3.

---

{% include-markdown "signature-core.md" %}
