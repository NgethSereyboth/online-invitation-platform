/* One boundary for all persistence. Replace LocalRepository with an API-backed
   implementation without changing editor or guest UI code. */
class LocalRepository {
  read(key, fallback = null) {
    try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
    catch { return fallback; }
  }
  write(key, value) { localStorage.setItem(key, JSON.stringify(value)); return value; }
  append(key, value) { const items = this.read(key, []); items.push(value); return this.write(key, items); }
  remove(key) { localStorage.removeItem(key); }
}

class IndexedAssetRepository {
  constructor() { this.dbName = 'sovan-invite-assets'; this.storeName = 'assets'; }
  open() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, 1);
      request.onupgradeneeded = () => request.result.createObjectStore(this.storeName, { keyPath: 'id' });
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
  async transaction(mode, action) {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(this.storeName, mode);
      const request = action(tx.objectStore(this.storeName));
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
      tx.oncomplete = () => db.close();
    });
  }
  put(asset) { return this.transaction('readwrite', store => store.put(asset)); }
  list() { return this.transaction('readonly', store => store.getAll()); }
  delete(id) { return this.transaction('readwrite', store => store.delete(id)); }
}

window.inviteStore = new LocalRepository();
window.assetStore = new IndexedAssetRepository();
