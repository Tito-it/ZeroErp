## Organizzati per funzionalità e responsabilità:
<table>
  <thead>
    <tr>
      <th>Schema</th>
      <th>Descrizione</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>anagrafiche</strong></td>
      <td>
        Contiene tutte le tabelle legate all'anagrafica soggetti (persone fisiche e giuridiche).
        <ul>
          <li>Esempi: <code>soggetti</code>, <code>indirizzi</code>, <code>contatti</code></li>
          <li>Usa identificatori UUID e naming coerente</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong>config</strong></td>
      <td>
        Contiene tabelle di configurazione parametrica e lookup.
        <ul>
          <li>Esempi: <code>stati</code>, <code>nazioni</code>, <code>contatti_ruoli</code></li>
          <li>Normalizzazione forte, spesso referenziate da altri schemi</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong>script</strong></td>
      <td>
        Logica applicativa (viste e funzioni) legate ai processi ERP.
        Favorisce riuso, mantenibilità e isolamento della logica.
        <ul>
          <li>Esempi: <code>vw_clienti_attivi</code>, <code>fn_calcolo_fattura()</code></li>
          <li>Include anche: <code>fn_get_stradario_by_indirizzo()</code>, etc.</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong>dbops</strong></td>
      <td>
        Strumenti DB per DBA (vista/funzioni tecniche, metadata, monitoring).
        <ul>
          <li>Esempi: <code>vw_function_list</code>, <code>fn_foreign_keys_info(text)</code></li>
          <li>Nessuna logica applicativa, solo strumenti per DBA e manutentori</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong>storico</strong></td>
      <td>
        Tabelle di audit/storico con versioning temporale dei dati. 
        Tutte le tabelle che richiedono "storicizzazione" saranno replicate qui
        <ul>
          <li>Esempi: <code>soggetti_storico</code>, <code>contratti_storico</code></li>
          <li>Usato per audit, confronto tra versioni, report du dati storici</li>
        </ul>
      </td>
    </tr>
  </tbody>
</table>

>

## Navigazione per schema

- [anagrafiche](dbzero/anagrafiche/index.md)  
- [config](dbzero/config/index.md)  
- [script](dbzero/script/index.md)  
- [dbops](dbzero/dbops/index.md)  
- [storico](dbzero/storico/index.md)  

> In ciascuna pagina di schema troverai un unico indice con le tabelle, le funzioni e le view corrispondenti.