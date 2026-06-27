# Equipment catalog CSV

Import the catalog from **Equipment CSV** in the application. Required header:

```csv
profile_id,vendor,model,band_ghz,channel_bw_mhz,modulation,capacity_mbps,rx_threshold_dbm,tx_power_min_dbm,tx_power_max_dbm
VENDOR_MODEL_18_56_256QAM,Vendor,Model,18,56,256QAM,350,-68,-20,20
```

`profile_id` is the unique merge key. Importing an existing ID updates that profile; a new ID adds a profile. Numeric fields must contain plain numbers using a dot as decimal separator. Tx/Rx values are in dBm.
