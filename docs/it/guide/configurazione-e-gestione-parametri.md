# 📗 Guida Tecnica – Configurazione e Gestione Parametri in Zero ERP

> 📋 **Destinatari:** sviluppatori database, sviluppatori backend

---

## 📌 Introduzione

Questa guida fornisce indicazioni dettagliate e best practices sulla gestione e configurazione dei parametri all’interno di Zero ERP, utilizzando due principali metodi:

* **Parametri Tabellari** ([`config.parameters`](/dbzero/config/tabelle/parameters) e [`config.parameter_overrides`](/dbzero/config/tabelle/parameter_overrides))
* **Parametri Personalizzati (GUC)** ([Parametri Personalizzati (GUC)](/parametri-personalizzati-(GUC)))

---

## 🚦 Quando Usare Parametri Tabellari o GUC?

* **Parametri Tabellari**: quando si vuole supportare override multipli (utente, sessione, funzione, tenant).
* **Parametri GUC**: quando si preferisce una configurazione più semplice e centralizzata a livello di database.

---

## 🗃️ Guida ai Parametri Tabellari

### ✅ Tabella `config.parameters`

* Definisce parametri globali con valori di default.
* Esempio di definizione:

| id | code       | default_value | description        |
| -- | ---------- | -------------- | ------------------ |
| 1  | lingua     | IT             | Lingua predefinita |
| 2  | stato_def | IT             | Stato predefinito  |

### ✅ Tabella `config.parameter_overrides`

* Permette override su più livelli (funzione, sessione, utente, tenant).
* Priorità override:

  1. Funzione
  2. Sessione
  3. Utente
  4. Tenant
  5. Default

### ✅ Funzione `script.fn_get_parameter_full`

* Centralizza la logica di recupero dei parametri e degli override.
* [Dettagli Funzione](/dbzero/script/funzioni/fn_get_parameter_full)

---

## 🔧 Gestione Parametri Personalizzati (GUC)

* Permettono una configurazione rapida tramite `SET` e `ALTER DATABASE`.
* Utili per configurazioni ambientali e impostazioni rapide di debug.
* [Dettagli su GUC](/parametri-personalizzati-(GUC))

### 📍 Esempio configurazione GUC:

```sql
ALTER DATABASE mydb SET myapp.default_language = 'it';
```

---

## 📚 Esempi di Utilizzo Reale

### 🧩 Recupero Parametro Tabellare

```sql
SELECT script.fn_get_parameter_full('stato_def');
```

### 🧩 Recupero Parametro GUC

```sql
SHOW myapp.default_language;
```

---

## 💡 Gestione dei parametri con riferimento a Foreign Key (es. `stato_id`)

### Problematica

I parametri che riferiscono a foreign key (es. `stato_id`) non devono usare direttamente gli ID numerici, che variano da ambiente a ambiente.

### Soluzione consigliata

Utilizzare sempre identificativi simbolici (come codici ISO) nei parametri tabellari, e risolverli dinamicamente:

#### ✅ Esempio di configurazione parametro:

| parametro  | valore default |
| ---------- | -------------- |
| stato_def | IT             |

#### ✅ Query dinamica per recuperare ID effettivo:

```sql
DECLARE
  v_stato_id INTEGER;
BEGIN
  SELECT id INTO v_stato_id
  FROM config.stati
  WHERE codice_iso2 = script.fn_get_parameter_full('stato_def');

  IF v_stato_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'business',
      'my_function',
      'STATO_ID_NOT_FOUND',
      jsonb_build_object('param_code', 'stato_def'),
      NULL::uuid,
      'stato_def'
    );
  END IF;

  INSERT INTO anagrafiche.soggetti (nome, stato_id)
  VALUES ('Nuovo Soggetto', v_stato_id);
END;
```

### 🛡️ Vantaggi

* **Portabilità**: non dipendente da ID numerici fissi.
* **Chiarezza e semplicità**: codici ISO leggibili e comprensibili.
* **Manutenibilità**: nessun aggiornamento massiccio necessario in caso di modifiche agli ID.

---

## 🔖 Conclusioni e Best Practices Finali

* Usare sempre simboli stabili (codici ISO, codici identificativi leggibili) nei parametri.
* Utilizzare sempre funzioni centralizzate (`script.fn_get_parameter_full`) per recuperare valori.
* Verificare documentazione e validare i parametri frequentemente per assicurare integrità e coerenza.

---

> 🧠 **“Configurare i parametri con simboli stabili e risolvere dinamicamente in runtime garantisce massima portabilità e flessibilità, semplificando la manutenzione e migliorando l’affidabilità del sistema.”**

---
{% include-markdown "signature-core.md" %}
