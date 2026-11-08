## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_tipo_doc_fiscale_id`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il tipo documento fiscale di default di ogni tipo di documento
> * [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale) — il vocabolario dei tipi documento fiscale
>
> Approfondimento funzioni:
>
> * [vendite.trgfn_attivita_fatturabili_normalize](/dbzero/vendite/funzioni/trgfn_attivita_fatturabili_normalize) — chi la chiama

---

### 🎯 Scopo Principale

La funzione **`vendite.fn_get_tipo_doc_fiscale_id`** risolve il tipo documento fiscale di
default di un tipo di documento d'origine, da `config.sorgenti.tipo_doc_fiscale_id`.

---

### Regola applicata

1. Il tipo di documento è obbligatorio: vuoto ⇒ `E_PARAMETRO_INVALIDO`.
2. Si usa `config.sorgenti.tipo_doc_fiscale_id` del tipo.
3. Se il tipo non lo dichiara (o non esiste) ⇒ errore bloccante `E_CODICE`.

Non c'è un ripiego sulla utility: il tipo documento di default è del catalogo dei tipi di
documento.

---

### Note operative

* La chiama la normalizzazione delle attività fatturabili quando l'attività arriva senza tipo
  documento fiscale. Il tipo di documento che passa è quello della **riga di commessa** da cui
  l'attività nasce (l'attività la punta con `commessa_attivita_id`, e la riga dice da quale
  documento nasce); la riga senza documento (onere, rettifica) prende il tipo `COMMESSA`.

---

### Note di migrazione

* 2026-11-07 — il tipo di documento lo dà la riga di commessa, non più la provenienza propria
  dell'attività fatturabile, che si ritira. La pagina diceva anche, a torto, che la funzione
  ripiegasse sul tipo documento della utility (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
