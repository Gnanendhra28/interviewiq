# Document Storage Architecture & StorageProvider Abstraction

## 1. Abstract Storage Interface

Storage operations are abstracted behind the `StorageProvider` interface (`apps/api/app/core/storage/provider.py`), completely decoupling application logic from physical storage engines:

```
Application Use Cases
          │
          ▼
   StorageProvider
   ┌──────┴──────┐
   │             │
LocalStorage   GCSStorage
(Dev Environment) (Production GCP)
```

---

## 2. Environment Adapters

- **`LocalStorageProvider`**: Stores files under `./data/uploads` using safe normalized paths to prevent directory traversal. Used when `STORAGE_PROVIDER=local`.
- **`GCSStorageProvider`**: Stores objects in Google Cloud Storage private buckets using Workload Identity / runtime service account credentials. Generates short-lived 15-minute V4 signed URLs. Used when `STORAGE_PROVIDER=gcs`.

Configuration selection is explicit via `settings.STORAGE_PROVIDER`. Silent fallbacks are prohibited.

---

## 3. Malware Scanning & Security Integration Point

While production malware scanning (e.g. ClamAV or GCP VirusTotal integration) is configured out of-band, the storage layer provides an isolated quarantine pipeline point prior to Phase 5 background parsing.
